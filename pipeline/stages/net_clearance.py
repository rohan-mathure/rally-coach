import numpy as np
from loguru import logger

from app.models.shot import Shot
from pipeline.models.homography import CourtHomography
from pipeline.utils.court_constants import HALF_COURT_FT, NET_HEIGHT_CENTER_FT


def compute_net_clearance(shots: list[Shot], homography: CourtHomography | None) -> list[Shot]:
    if homography is None:
        return shots

    # Net position in pixel coords
    net_left_px = homography.court_to_pixel(-13.5, HALF_COURT_FT)
    net_right_px = homography.court_to_pixel(13.5, HALF_COURT_FT)
    net_pixel_y = (net_left_px[1] + net_right_px[1]) / 2  # average net center y in pixels

    # Net top in pixel coords (net_height = 3ft above baseline level)
    # We compare ball position at net x to the net top pixel y
    net_top_left_px = homography.court_to_pixel(-13.5, HALF_COURT_FT)
    # Rough scale: court length in pixels
    far_base_px = homography.court_to_pixel(0.0, 78.0)
    near_base_px = homography.court_to_pixel(0.0, 0.0)
    court_length_px = abs(far_base_px[1] - near_base_px[1])
    if court_length_px < 1:
        return shots
    feet_per_px = 78.0 / court_length_px
    net_height_px = NET_HEIGHT_CENTER_FT / feet_per_px

    # Net top pixel y = net midpoint y - net_height in pixels (pixel y decreases upward)
    net_top_pixel_y = net_pixel_y - net_height_px

    updated = []
    for shot in shots:
        traj = shot.trajectory
        if len(traj) < 3:
            updated.append(shot)
            continue

        # Find ball position when it crosses the net (court_y ≈ HALF_COURT_FT)
        # Interpolate between trajectory points
        court_ys = []
        pixel_ys = []
        for p in traj:
            cx, cy = homography.pixel_to_court(p.x, p.y)
            court_ys.append(cy)
            pixel_ys.append(p.y)

        court_ys = np.array(court_ys)
        pixel_ys = np.array(pixel_ys)

        # Find where court_y crosses HALF_COURT_FT
        crossing_idx = None
        for i in range(len(court_ys) - 1):
            y0, y1 = court_ys[i], court_ys[i + 1]
            if (y0 - HALF_COURT_FT) * (y1 - HALF_COURT_FT) <= 0:
                crossing_idx = i
                break

        if crossing_idx is None:
            updated.append(shot)
            continue

        # Linear interpolation to get exact pixel y at net crossing
        y0, y1 = court_ys[crossing_idx], court_ys[crossing_idx + 1]
        py0, py1 = pixel_ys[crossing_idx], pixel_ys[crossing_idx + 1]
        denom = (y1 - y0)
        if abs(denom) < 1e-6:
            ball_y_at_net = py0
        else:
            t = (HALF_COURT_FT - y0) / denom
            ball_y_at_net = py0 + t * (py1 - py0)

        # Positive clearance = ball above net (pixel y < net_top_pixel_y)
        clearance_px = net_top_pixel_y - ball_y_at_net   # positive = cleared
        clearance_ft = clearance_px * feet_per_px
        clearance_inches = clearance_ft * 12.0
        cleared = clearance_inches > 0

        updated.append(shot.model_copy(update={
            "net_clearance_inches": round(clearance_inches, 1),
            "cleared_net": cleared,
        }))

    return updated
