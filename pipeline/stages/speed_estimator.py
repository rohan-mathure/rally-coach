import math
import numpy as np
from loguru import logger

from app.models.shot import Shot, BallPosition
from pipeline.models.homography import CourtHomography
from pipeline.utils.court_constants import COURT_LENGTH_FT

POST_CONTACT_FRAMES = 5
CAMERA_ANGLE_CORRECTION = 1.12   # compensates for perspective foreshortening
FEET_PER_MILE = 5280.0
SECONDS_PER_HOUR = 3600.0


def _baseline_pixel_length(homography: CourtHomography, frame_width: int, frame_height: int) -> float:
    """Approximate pixel length of court baseline using homography inverse."""
    # Near baseline corners in court coords
    from pipeline.utils.court_constants import SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT
    left_px = homography.court_to_pixel(-SINGLES_HALF_WIDTH_FT, 0.0)
    right_px = homography.court_to_pixel(SINGLES_HALF_WIDTH_FT, 0.0)
    return math.hypot(right_px[0] - left_px[0], right_px[1] - left_px[1])


def estimate_speeds(
    shots: list[Shot],
    fps: float,
    homography: CourtHomography | None,
    frame_width: int,
    frame_height: int,
) -> list[Shot]:
    if homography is not None:
        baseline_px = _baseline_pixel_length(homography, frame_width, frame_height)
        # Scale: court width = 27ft
        from pipeline.utils.court_constants import SINGLES_WIDTH_FT
        scale_ft_per_px = SINGLES_WIDTH_FT / baseline_px if baseline_px > 0 else None
    else:
        scale_ft_per_px = None

    updated = []
    for shot in shots:
        traj = shot.trajectory
        # Find positions just after contact
        post = [p for p in traj if p.frame_idx >= shot.contact_frame][:POST_CONTACT_FRAMES + 1]
        if len(post) < 2 or scale_ft_per_px is None:
            confidence = 0.0 if scale_ft_per_px is None else 0.3
            updated.append(shot.model_copy(update={"speed_confidence": confidence}))
            continue

        speeds_px_per_frame = []
        for i in range(1, len(post)):
            dx = post[i].x - post[i-1].x
            dy = post[i].y - post[i-1].y
            speeds_px_per_frame.append(math.hypot(dx, dy))

        if not speeds_px_per_frame:
            updated.append(shot)
            continue

        avg_px_per_frame = float(np.mean(speeds_px_per_frame))
        speed_ft_per_sec = avg_px_per_frame * scale_ft_per_px * fps * CAMERA_ANGLE_CORRECTION
        speed_mph = speed_ft_per_sec * SECONDS_PER_HOUR / FEET_PER_MILE

        # Confidence: lower if many interpolated frames, or if speed is physically implausible
        has_interpolated = any(p.is_interpolated for p in post)
        conf = 0.85 if not has_interpolated else 0.50
        if speed_mph > 160 or speed_mph < 5:  # physically implausible for tennis
            speed_mph = None
            conf = 0.0

        updated.append(shot.model_copy(update={
            "speed_mph": speed_mph,
            "speed_confidence": conf,
        }))

    return updated
