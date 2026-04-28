from app.models.shot import Shot
from pipeline.models.homography import CourtHomography
from pipeline.utils.court_constants import CLOSE_CALL_THRESHOLD_FT, SINGLES_BOUNDS
from pipeline.utils.geometry import min_distance_to_polygon_boundary, point_in_polygon


def classify_inout(shots: list[Shot], homography: CourtHomography | None) -> list[Shot]:
    """Re-classify bounce in/out using homography (already done in bounce_detector,
    but this stage provides a clean re-pass with the final calibrated homography)."""
    if homography is None:
        return shots

    updated = []
    for shot in shots:
        if shot.bounce is None:
            updated.append(shot)
            continue

        cx = shot.bounce_court_x
        cy = shot.bounce_court_y
        if cx is None or cy is None:
            updated.append(shot)
            continue

        is_in = point_in_polygon((cx, cy), SINGLES_BOUNDS)
        dist = min_distance_to_polygon_boundary((cx, cy), SINGLES_BOUNDS)
        is_close = dist < CLOSE_CALL_THRESHOLD_FT

        updated.append(shot.model_copy(update={
            "is_in": is_in,
            "is_close_call": is_close,
            "bounce": shot.bounce.model_copy(update={"is_in": is_in, "is_close_call": is_close}),
        }))

    return updated
