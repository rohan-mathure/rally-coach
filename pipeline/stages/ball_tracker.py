from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from loguru import logger

from app.models.shot import BallPosition
from pipeline.models.kalman import KalmanBallTracker

MAX_GAP_FRAMES = 8
DETECTION_CONFIDENCE_THRESHOLD = 0.35
SPORTS_BALL_CLASS = 32  # COCO class index for "sports ball"


@dataclass
class TrackState:
    positions: list[BallPosition] = field(default_factory=list)
    kalman: KalmanBallTracker = field(default_factory=KalmanBallTracker)


def _load_model(weights_dir: Path):
    from ultralytics import YOLO

    custom = weights_dir / "yolov8n_tennis_ball.pt"
    if custom.exists():
        logger.info(f"Loading custom tennis ball model: {custom}")
        return YOLO(str(custom))
    logger.info("Custom weights not found; using YOLOv8n COCO (sports ball class)")
    return YOLO("yolov8n.pt")


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
    model = _load_model(weights_dir)
    tracker = KalmanBallTracker(fps=fps)
    positions: list[BallPosition] = []

    for frame_idx, frame in frames_iter:
        results = model(frame, verbose=False)[0]

        best_box = None
        best_conf = 0.0
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            if cls == SPORTS_BALL_CLASS and conf > DETECTION_CONFIDENCE_THRESHOLD:
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
                is_interp = tracker.consecutive_misses <= MAX_GAP_FRAMES
                positions.append(BallPosition(
                    frame_idx=frame_idx,
                    x=kx, y=ky,
                    confidence=0.0,
                    is_interpolated=is_interp,
                ))
            # No ball and tracker not initialized → skip frame (no position recorded)

    return positions
