import json
from pathlib import Path
from typing import Generator

import numpy as np
from loguru import logger

from app.config import settings
from app.database import get_db
from app.models.shot import Shot
from pipeline.stages.annotator import annotate_video
from pipeline.stages.ball_tracker import track_balls
from pipeline.stages.bounce_detector import detect_bounces
from pipeline.stages.court_detector import detect_court
from pipeline.stages.frame_extractor import extract_metadata
from pipeline.stages.inout_classifier import classify_inout
from pipeline.stages.net_clearance import compute_net_clearance
from pipeline.stages.pose_analyzer import extract_poses
from pipeline.stages.shot_classifier import classify_shots
from pipeline.stages.shot_quality import compute_quality_scores
from pipeline.stages.shot_segmenter import segment_shots
from pipeline.stages.speed_estimator import estimate_speeds
from pipeline.stages.spin_analyzer import analyze_spin
from pipeline.utils.video_io import VideoReader

COURT_REVALIDATE_INTERVAL = 300   # frames
_COURT_MIN_INLIER_RATIO = 0.6
_COURT_EARLY_EXIT_RATIO = 0.9


def _pick_best_homography(
    video_path: Path,
    total_frames: int,
) -> tuple:
    """Sample several frames and return (homography, inlier_ratio) for the best one.

    Returns homography=None when the best ratio is below _COURT_MIN_INLIER_RATIO.
    """
    best_ratio = 0.0
    best_homography = None
    sample_frames = [30, 0, 60, 120, 300, total_frames // 20, total_frames // 10]
    with VideoReader(video_path) as reader:
        for frame_num in dict.fromkeys(sample_frames):  # deduplicate, preserve order
            frame = reader.read_frame(frame_num)
            if frame is None:
                continue
            h, ratio, _ = detect_court(frame)
            logger.debug(f"Court detection frame {frame_num}: inlier_ratio={ratio:.2f}")
            if ratio > best_ratio:
                best_ratio = ratio
                best_homography = h if ratio >= _COURT_MIN_INLIER_RATIO else None
            if best_ratio >= _COURT_EARLY_EXIT_RATIO:
                break
    return best_homography, best_ratio


def _with_progress(
    frames_gen: Generator[tuple[int, np.ndarray], None, None],
    total: int,
    label: str,
) -> Generator[tuple[int, np.ndarray], None, None]:
    log_every = max(1, total // 10)
    for idx, frame in frames_gen:
        if idx > 0 and idx % log_every == 0:
            pct = min(100, idx * 100 // total)
            logger.info(f"{label}: frame {idx}/{total} ({pct}%)")
        yield idx, frame


async def _update_session(session_id: str, **kwargs) -> None:
    async with get_db() as db:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [session_id]
        await db.execute(
            f"UPDATE sessions SET {set_clause} WHERE session_id = ?", values
        )
        await db.commit()


async def _save_shots(shots: list[Shot]) -> None:
    async with get_db() as db:
        for shot in shots:
            await db.execute("""
                INSERT OR REPLACE INTO shots (
                    shot_id, session_id, shot_number, start_frame, end_frame,
                    contact_frame, start_time_sec, shot_type, shot_type_confidence,
                    spin_type, spin_confidence, speed_mph, speed_confidence,
                    rpm_estimate, net_clearance_inches, cleared_net, is_in,
                    is_close_call, bounce_court_x, bounce_court_y, curvature_score,
                    quality_score, detection_gap_frames, pipeline_warnings,
                    trajectory, pose, bounce
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                shot.shot_id, shot.session_id, shot.shot_number,
                shot.start_frame, shot.end_frame, shot.contact_frame,
                shot.start_time_sec, shot.shot_type, shot.shot_type_confidence,
                shot.spin_type, shot.spin_confidence, shot.speed_mph,
                shot.speed_confidence, shot.rpm_estimate, shot.net_clearance_inches,
                int(shot.cleared_net) if shot.cleared_net is not None else None,
                int(shot.is_in) if shot.is_in is not None else None,
                int(shot.is_close_call), shot.bounce_court_x, shot.bounce_court_y,
                shot.curvature_score, shot.quality_score, shot.detection_gap_frames,
                json.dumps(shot.pipeline_warnings),
                json.dumps([p.model_dump() for p in shot.trajectory]),
                json.dumps(shot.pose.model_dump()) if shot.pose else None,
                json.dumps(shot.bounce.model_dump()) if shot.bounce else None,
            ))
        await db.commit()


async def run(session_id: str, video_path: Path) -> None:
    logger.info(f"Pipeline start: {session_id}")
    try:
        await _run_pipeline(session_id, video_path)
    except Exception as e:
        logger.exception(f"Pipeline failed for {session_id}: {e}")
        await _update_session(session_id, status="error", error_message=str(e))


async def _run_pipeline(session_id: str, video_path: Path) -> None:
    await _update_session(session_id, status="processing")

    # Stage 1/13: metadata
    logger.info("Stage 1/13: extracting metadata")
    meta = extract_metadata(video_path)
    fps = meta["fps"] or 60.0
    await _update_session(session_id,
        fps=fps,
        total_frames=meta["total_frames"],
        width=meta["width"],
        height=meta["height"],
    )
    logger.info(f"Stage 1/13: {meta['total_frames']} frames @ {fps}fps, {meta['width']}x{meta['height']}")

    # Stage 2/13: court detection — sample several frames and keep the best result
    logger.info("Stage 2/13: court detection")
    homography, best_inlier_ratio = _pick_best_homography(video_path, meta["total_frames"])
    if best_inlier_ratio < _COURT_MIN_INLIER_RATIO:
        logger.warning(
            f"Court detection low confidence ({best_inlier_ratio:.2f}); proceeding without homography"
        )
    else:
        logger.info(f"Stage 2/13: court detected (inlier_ratio={best_inlier_ratio:.2f})")
        await _update_session(session_id, homography_matrix=json.dumps(homography.to_list()))

    # Stage 3/13: ball tracking (full video pass)
    logger.info(f"Stage 3/13: ball tracking ({meta['total_frames']} frames)")
    with VideoReader(video_path) as reader:
        all_positions = track_balls(
            _with_progress(reader.frames(), total=meta["total_frames"], label="Stage 3/13"),
            fps=fps,
            weights_dir=settings.weights_dir,
        )

    logger.info(f"Stage 3/13: tracked {len(all_positions)} ball positions")

    real_detections = sum(1 for p in all_positions if not p.is_interpolated)
    if not all_positions or real_detections == 0:
        await _update_session(
            session_id, status="error",
            error_message="No ball detected — custom YOLO weights (yolov8n_tennis_ball.pt) are required for reliable detection",
        )
        return

    # Stage 4/13: bounce detection
    logger.info("Stage 4/13: bounce detection")
    bounces = detect_bounces(all_positions, homography, frame_height=meta["height"])
    logger.info(f"Stage 4/13: detected {len(bounces)} bounces")

    # Stage 5/13: shot segmentation
    logger.info("Stage 5/13: shot segmentation")
    shots = segment_shots(all_positions, bounces, fps=fps, session_id=session_id)

    if not shots:
        await _update_session(session_id, status="error", error_message="No shots detected")
        return

    logger.info(f"Stage 5/13: segmented {len(shots)} shots")

    # Stage 6/13: speed estimation (before spin so spin can use speed)
    logger.info("Stage 6/13: speed estimation")
    shots = estimate_speeds(shots, fps=fps, homography=homography,
                             frame_width=meta["width"], frame_height=meta["height"])

    # Stage 7/13: spin analysis (requires speed)
    logger.info("Stage 7/13: spin analysis")
    shots = analyze_spin(shots, fps=fps)

    # Stage 8/13: net clearance
    logger.info("Stage 8/13: net clearance")
    shots = compute_net_clearance(shots, homography)

    # Stage 9/13: in/out classification
    logger.info("Stage 9/13: in/out classification")
    shots = classify_inout(shots, homography)

    # Stage 10+11/13: pose extraction + shot classification
    logger.info("Stage 10+11/13: pose extraction + shot classification")
    with VideoReader(video_path) as reader:
        shots = extract_poses(shots, reader)
    shots = classify_shots(shots, homography)

    # Stage 12/13: quality scores
    logger.info("Stage 12/13: quality scores")
    shots = compute_quality_scores(shots)

    # Save shots to DB
    await _save_shots(shots)

    # Update session summary stats
    speeds = [s.speed_mph for s in shots if s.speed_mph is not None]
    qualities = [s.quality_score for s in shots if s.quality_score is not None]
    output_path = settings.processed_dir / f"{session_id}_annotated.mp4"

    await _update_session(session_id,
        total_shots=len(shots),
        avg_speed_mph=round(sum(speeds) / len(speeds), 1) if speeds else None,
        avg_quality_score=round(sum(qualities) / len(qualities), 1) if qualities else None,
    )

    # Stage 13/13: annotate video
    logger.info("Stage 13/13: annotating video")
    annotate_video(
        input_path=video_path,
        output_path=output_path,
        shots=shots,
        all_positions=all_positions,
        homography=homography,
        fps=fps,
    )

    await _update_session(session_id,
        status="complete",
        processed_video_path=str(output_path),
    )
    logger.info(f"Pipeline complete: {session_id} — {len(shots)} shots")
