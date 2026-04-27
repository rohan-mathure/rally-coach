import statistics
from app.models.shot import Shot
from pipeline.utils.court_constants import COURT_LENGTH_FT, SINGLES_HALF_WIDTH_FT

# Target zone: deep 25% of opponent's half (between service line and baseline)
TARGET_Y_MIN = COURT_LENGTH_FT * 0.625   # ~48.75 ft
TARGET_Y_MAX = COURT_LENGTH_FT           # 78 ft


def _depth_score(court_x: float | None, court_y: float | None) -> float:
    if court_x is None or court_y is None:
        return 0.0
    # Normalize court_y position: 1.0 if in target zone, partial credit otherwise
    if TARGET_Y_MIN <= court_y <= TARGET_Y_MAX:
        return 1.0
    elif COURT_LENGTH_FT / 2 < court_y < TARGET_Y_MIN:
        # In opponent's half but not deep — partial credit
        depth_in_half = (court_y - COURT_LENGTH_FT / 2) / (TARGET_Y_MIN - COURT_LENGTH_FT / 2)
        return depth_in_half * 0.5
    return 0.0


def compute_quality_scores(shots: list[Shot]) -> list[Shot]:
    # Need session avg speed for normalization
    speeds = [s.speed_mph for s in shots if s.speed_mph is not None]
    avg_speed = statistics.mean(speeds) if speeds else 60.0

    updated = []
    for shot in shots:
        w_in = 40.0
        w_net = 25.0
        w_depth = 25.0
        w_speed = 10.0

        is_in_score = 1.0 if shot.is_in else 0.0
        net_score = 1.0 if shot.cleared_net else (0.0 if shot.cleared_net is False else 0.5)
        depth = _depth_score(shot.bounce_court_x, shot.bounce_court_y)
        speed_score = min(1.0, (shot.speed_mph or 0.0) / avg_speed)

        quality = w_in * is_in_score + w_net * net_score + w_depth * depth + w_speed * speed_score
        updated.append(shot.model_copy(update={"quality_score": round(quality, 1)}))

    return updated
