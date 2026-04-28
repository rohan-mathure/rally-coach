import uuid

import numpy as np
from loguru import logger
from scipy.signal import savgol_filter

from app.models.shot import BallPosition, BounceEvent, Shot

MIN_SHOT_FRAMES = 18   # 0.3s at 60fps
MAX_SHOT_FRAMES = 180  # 3.0s at 60fps
VELOCITY_PEAK_THRESHOLD = 5.0  # px/frame — minimum speed increase to flag contact


def _compute_speed(positions: list[BallPosition]) -> np.ndarray:
    if len(positions) < 2:
        return np.zeros(len(positions))
    xs = np.array([p.x for p in positions])
    ys = np.array([p.y for p in positions])
    dx = np.diff(xs)
    dy = np.diff(ys)
    speeds = np.sqrt(dx**2 + dy**2)
    return np.concatenate([[speeds[0]], speeds])


def _find_contact_frames(positions: list[BallPosition]) -> list[int]:
    """Find frames where ball speed jumps sharply (racquet contact)."""
    if len(positions) < 5:
        return []
    speeds = _compute_speed(positions)
    smoothed = savgol_filter(speeds, window_length=min(9, len(speeds) - (len(speeds) % 2 == 0)), polyorder=2)
    contacts = []
    for i in range(2, len(smoothed) - 2):
        delta = smoothed[i] - smoothed[i - 2]
        if delta > VELOCITY_PEAK_THRESHOLD and smoothed[i] > smoothed[i + 1]:
            contacts.append(positions[i].frame_idx)
    return contacts


def segment_shots(
    positions: list[BallPosition],
    bounces: list[BounceEvent],
    fps: float,
    session_id: str,
) -> list[Shot]:
    if not positions:
        return []

    pos_by_frame: dict[int, BallPosition] = {p.frame_idx: p for p in positions}
    bounce_list = sorted(bounces, key=lambda b: b.frame_idx)

    # Build shot boundaries: between consecutive bounces
    if len(bounce_list) < 2:
        logger.warning("Shot segmenter: fewer than 2 bounces detected; cannot segment shots")
        return []

    shots: list[Shot] = []
    for i in range(len(bounce_list) - 1):
        start_frame = bounce_list[i].frame_idx
        end_frame = bounce_list[i + 1].frame_idx
        duration = end_frame - start_frame

        if not (MIN_SHOT_FRAMES <= duration <= MAX_SHOT_FRAMES):
            logger.debug(f"Shot segment {start_frame}-{end_frame} duration {duration} out of range; skipping")
            continue

        # Collect positions in this range (sample every 3 frames for storage)
        traj = [
            pos_by_frame[f]
            for f in range(start_frame, end_frame + 1)
            if f in pos_by_frame and (f - start_frame) % 3 == 0
        ]
        full_traj = [pos_by_frame[f] for f in range(start_frame, end_frame + 1) if f in pos_by_frame]

        contacts = _find_contact_frames(full_traj)
        contact_frame = contacts[0] if contacts else start_frame + duration // 4

        # Measure longest interpolation gap
        gap_frames = 0
        current_gap = 0
        for f in range(start_frame, end_frame + 1):
            if f in pos_by_frame and pos_by_frame[f].is_interpolated:
                current_gap += 1
                gap_frames = max(gap_frames, current_gap)
            else:
                current_gap = 0

        warnings = []
        if gap_frames > 8:
            warnings.append("long_detection_gap")

        bounce_event = bounce_list[i + 1]

        shots.append(Shot(
            shot_id=str(uuid.uuid4()),
            session_id=session_id,
            shot_number=len(shots) + 1,
            start_frame=start_frame,
            end_frame=end_frame,
            contact_frame=contact_frame,
            start_time_sec=contact_frame / fps,
            trajectory=traj,
            bounce=bounce_event,
            is_in=bounce_event.is_in,
            is_close_call=bounce_event.is_close_call,
            bounce_court_x=bounce_event.court_x,
            bounce_court_y=bounce_event.court_y,
            detection_gap_frames=gap_frames,
            pipeline_warnings=warnings,
        ))

    logger.info(f"Segmented {len(shots)} shots")
    return shots
