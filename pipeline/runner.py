import json
import statistics
from pathlib import Path

from loguru import logger

from app.config import settings
from app.database import get_db
from app.models.shot import Shot
from pipeline.stages.frame_extractor import extract_metadata
from pipeline.stages.court_detector import detect_court
from pipeline.stages.ball_tracker import track_balls
from pipeline.stages.bounce_detector import detect_bounces
from pipeline.stages.shot_segmenter import segment_shots
from pipeline.stages.pose_analyzer import extract_poses
from pipeline.stages.shot_classifier import classify_shots
from pipeline.stages.spin_analyzer import analyze_spin
from pipeline.stages.speed_estimator import estimate_speeds
from pipeline.stages.net_clearance import compute_net_clearance
from pipeline.stages.inout_classifier import classify_inout
from pipeline.stages.shot_quality import compute_quality_scores
from pipeline.stages.annotator import annotate_video
from pipeline.utils.video_io import VideoReader

COURT_REVALIDATE_INTERVAL = 300   # frames


async def _update_session(session_id: str, **kwargs) -> None:
    async with await get_db() as db:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [session_id]
        await db.execute(
            f"UPDATE sessions SET {set_clause} WHERE session_id = ?", values
        )
        await db.commit()


async def _save_shots(shots: list[Shot]) -> None:
    async with await get_db() as db:
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

    # Stage 1: metadata
    meta = extract_metadata(video_path)
    fps = meta["fps"] or 60.0
    await _update_session(session_id,
        fps=fps,
        total_frames=meta["total_frames"],
        width=meta["width"],
        height=meta["height"],
    )
    logger.info(f"Video: {meta['total_frames']} frames @ {fps}fps, {meta['width']}x{meta['height']}")

    # Stage 2: court detection on frame ~30
    homography = None
    with VideoReader(video_path) as reader:
        sample_frame = reader.read_frame(30) or reader.read_frame(0)

    if sample_frame is not None:
        homography, inlier_ratio, _ = detect_court(sample_frame)
        if inlier_ratio < 0.6:
            logger.warning(f"Court detection low confidence ({inlier_ratio:.2f}); proceeding without homography")
            homography = None
        else:
            logger.info(f"Court detected (inlier_ratio={inlier_ratio:.2f})")
            await _update_session(session_id, homography_matrix=json.dumps(homography.to_list()))

    # Stage 3: ball tracking (full video pass)
    logger.info("Stage 3: ball tracking...")
    with VideoReader(video_path) as reader:
        all_positions = track_balls(reader.frames(), fps=fps, weights_dir=settings.weights_dir)

    logger.info(f"Tracked {len(all_positions)} ball positions")

    if not all_positions:
        await _update_session(session_id, status="error", error_message="No ball detected in video")
        return

    # Stage 4: bounce detection
    logger.info("Stage 4: bounce detection...")
    bounces = detect_bounces(all_positions, homography, frame_height=meta["height"])

    # Stage 5: shot segmentation
    logger.info("Stage 5: shot segmentation...")
    shots = segment_shots(all_positions, bounces, fps=fps, session_id=session_id)

    if not shots:
        await _update_session(session_id, status="error", error_message="No shots detected")
        return

    # Stage 9 (speed) before spin so spin can use speed
    logger.info("Stage 9: speed estimation...")
    shots = estimate_speeds(shots, fps=fps, homography=homography,
                             frame_width=meta["width"], frame_height=meta["height"])

    # Stage 8: spin analysis (requires speed)
    logger.info("Stage 8: spin analysis...")
    shots = analyze_spin(shots, fps=fps)

    # Stage 10: net clearance
    logger.info("Stage 10: net clearance...")
    shots = compute_net_clearance(shots, homography)

    # Stage 11: in/out classification
    logger.info("Stage 11: in/out classification...")
    shots = classify_inout(shots, homography)

    # Stage 6+7: pose extraction + shot classification
    logger.info("Stage 6+7: pose + shot classification...")
    with VideoReader(video_path) as reader:
        shots = extract_poses(shots, reader)
    shots = classify_shots(shots, homography)

    # Stage 12: quality scores
    logger.info("Stage 12: quality scores...")
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

    # Stage 13: annotate video
    logger.info("Stage 13: annotating video...")
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
