from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from app.models.shot import BallPosition
from pipeline.models.kalman import KalmanBallTracker

MAX_GAP_FRAMES = 8
# Custom tennis ball model is purpose-trained → higher precision, stricter threshold.
# COCO sports-ball class is generic → lower threshold to catch weak detections.
CUSTOM_CONF_THRESHOLD = 0.35
COCO_CONF_THRESHOLD   = 0.20
SPORTS_BALL_CLASS = 32  # COCO class index for "sports ball"
MIN_DETECTION_RATE  = 0.001   # warn if fewer than 0.1% of frames have detections
MAX_DETECTION_RATE  = 0.80    # warn if more than 80% of frames have detections (likely false positives)


@dataclass
class TrackState:
    positions: list[BallPosition] = field(default_factory=list)
    kalman: KalmanBallTracker = field(default_factory=KalmanBallTracker)


def _load_model(weights_dir: Path) -> tuple:
    """Return (model, ball_class, conf_threshold)."""
    from ultralytics import YOLO

    custom = weights_dir / "yolov8n_tennis_ball.pt"
    if custom.exists():
        logger.info(f"Loading custom tennis ball model: {custom}")
        return YOLO(str(custom)), 0, CUSTOM_CONF_THRESHOLD
    logger.info("Custom weights not found; using YOLOv8n COCO (sports ball class)")
    return YOLO("yolov8n.pt"), SPORTS_BALL_CLASS, COCO_CONF_THRESHOLD


def track_balls(
    frames_iter,
    fps: float,
    weights_dir: Path,
) -> list[BallPosition]:
    """
    Run ball detection + Kalman filtering over all frames.
    frames_iter yields (frame_idx, np.ndarray).
    Returns list of BallPosition (one per frame, may be interpolated).
    """
    model, ball_class, conf_threshold = _load_model(weights_dir)
    tracker = KalmanBallTracker(fps=fps)
    positions: list[BallPosition] = []

    for frame_idx, frame in frames_iter:
        results = model(frame, verbose=False)[0]

        best_box = None
        best_conf = 0.0
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if cls == ball_class and conf > conf_threshold:
                if conf > best_conf:
                    best_conf = conf
                    best_box = box

        if best_box is not None:
            x1, y1, x2, y2 = best_box.xyxy[0].tolist()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            kx, ky, _, _ = tracker.update(cx, cy)
            positions.append(BallPosition(
                frame_idx=frame_idx,
                x=kx, y=ky,
                confidence=best_conf,
                is_interpolated=False,
            ))
        else:
            if tracker.is_initialized:
                kx, ky, _, _ = tracker.predict()
                # Only keep positions within the valid interpolation window.
                # Beyond MAX_GAP_FRAMES the Kalman is extrapolating a stale trajectory
                # which produces ghost positions that break bounce detection.
                if tracker.consecutive_misses <= MAX_GAP_FRAMES:
                    positions.append(BallPosition(
                        frame_idx=frame_idx,
                        x=kx, y=ky,
                        confidence=0.0,
                        is_interpolated=True,
                    ))
            # No ball and tracker not initialized → skip frame (no position recorded)

    real = sum(1 for p in positions if not p.is_interpolated)
    interp = len(positions) - real
    logger.info(f"Ball tracking complete: {real} real detections, {interp} interpolated positions")

    total_frames = frame_idx + 1 if positions or frame_idx else 1
    detection_rate = real / total_frames
    if detection_rate < MIN_DETECTION_RATE:
        logger.warning(
            f"Ball detection rate critically low ({real} detections / {total_frames} frames = "
            f"{detection_rate:.4%}). Custom weights are required for reliable tracking. "
            f"Place yolov8n_tennis_ball.pt in the weights directory."
        )
    elif detection_rate > MAX_DETECTION_RATE:
        logger.warning(
            f"Ball detection rate unusually high ({detection_rate:.1%}). "
            "Many detections may be false positives — results downstream may be unreliable."
        )

    return positions
