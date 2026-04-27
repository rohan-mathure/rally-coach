import numpy as np
from scipy.signal import savgol_filter, argrelmin
from loguru import logger

from app.models.shot import BallPosition, BounceEvent
from pipeline.models.homography import CourtHomography
from pipeline.utils.court_constants import COURT_LENGTH_FT

VELOCITY_REVERSAL_THRESHOLD = 2.0   # pixels/frame
COURT_SURFACE_TOLERANCE_FT = 3.0    # how close to ground plane the bounce must be


def detect_bounces(
    positions: list[BallPosition],
    homography: CourtHomography | None,
    frame_height: int,
) -> list[BounceEvent]:
    if len(positions) < 15:
        return []

    frames = np.array([p.frame_idx for p in positions])
    ys = np.array([p.y for p in positions])  # pixel y increases downward

    # Smooth y trajectory
    window = min(11, len(ys) - (1 if len(ys) % 2 == 0 else 0))
    if window < 5:
        return []
    smoothed = savgol_filter(ys, window_length=window, polyorder=3)

    # Local maxima in pixel-y = local minima in visual height = potential bounces
    # (pixel y increases downward, so a bounce is a local max in ys)
    peaks = argrelmin(-smoothed, order=5)[0]  # local maxima

    bounces: list[BounceEvent] = []
    for idx in peaks:
        pos = positions[idx]

        # Validate: velocity direction reversal
        if idx < 2 or idx >= len(positions) - 2:
            continue
        vy_before = smoothed[idx] - smoothed[idx - 2]
        vy_after = smoothed[idx + 2] - smoothed[idx]
        if not (vy_before > VELOCITY_REVERSAL_THRESHOLD and vy_after < -VELOCITY_REVERSAL_THRESHOLD):
            continue

        # Validate: ball near court surface via homography
        is_in = False
        court_x, court_y = 0.0, 0.0
        is_close = False
        if homography is not None:
            cx, cy = homography.pixel_to_court(pos.x, pos.y)
            court_x, court_y = cx, cy
            # Ball should be between baselines and close to ground plane
            if 0 <= court_y <= COURT_LENGTH_FT:
                from pipeline.utils.court_constants import SINGLES_BOUNDS, CLOSE_CALL_THRESHOLD_FT
                from pipeline.utils.geometry import point_in_polygon, min_distance_to_polygon_boundary
                is_in = point_in_polygon((cx, cy), SINGLES_BOUNDS)
                dist = min_distance_to_polygon_boundary((cx, cy), SINGLES_BOUNDS)
                is_close = dist < CLOSE_CALL_THRESHOLD_FT
        else:
            # Rough: bounce near lower 20% of frame
            if pos.y > frame_height * 0.5:
                is_in = True  # assume in if no homography

        bounces.append(BounceEvent(
            frame_idx=pos.frame_idx,
            pixel_x=pos.x,
            pixel_y=pos.y,
            court_x=court_x,
            court_y=court_y,
            is_in=is_in,
            is_close_call=is_close,
        ))

    logger.debug(f"Bounce detector found {len(bounces)} bounces")
    return bounces
