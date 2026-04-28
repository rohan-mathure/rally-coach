from pipeline.utils.court_constants import SINGLES_BOUNDS
from pipeline.utils.geometry import min_distance_to_polygon_boundary, point_in_polygon


def test_center_court_is_in():
    assert point_in_polygon((0.0, 39.0), SINGLES_BOUNDS) is True


def test_outside_baseline_is_out():
    assert point_in_polygon((0.0, 80.0), SINGLES_BOUNDS) is False


def test_outside_sideline_is_out():
    assert point_in_polygon((15.0, 39.0), SINGLES_BOUNDS) is False


def test_corner_is_in():
    assert point_in_polygon((-13.0, 1.0), SINGLES_BOUNDS) is True


def test_distance_near_baseline():
    # Point 1ft inside near baseline
    dist = min_distance_to_polygon_boundary((0.0, 1.0), SINGLES_BOUNDS)
    assert abs(dist - 1.0) < 0.01
