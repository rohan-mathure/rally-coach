import numpy as np
import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("bounce_detection.feature")


@given("30 ball positions with constant y=300", target_fixture="positions")
def flat_positions(make_positions):
    return make_positions(30, ys=[300.0] * 30)


@given("40 ball positions forming a downward parabola peaking at frame 20", target_fixture="positions")
def parabolic_positions(make_positions):
    # y = a*(x-20)^2 + min_y where y(20)=400 is the bounce peak (max pixel y)
    # a = (400-100)/20^2 = 0.75,  y(0) = y(40) ≈ 100
    a = 0.75
    ys = [-a * (i - 20) ** 2 + 400 for i in range(40)]
    return make_positions(40, ys=ys)


@when("bounce detection runs with no homography and frame_height=600", target_fixture="bounces")
def run_bounce_detection(positions):
    from pipeline.stages.bounce_detector import detect_bounces
    return detect_bounces(positions, homography=None, frame_height=600)


@then("0 bounces are detected")
def no_bounces(bounces):
    assert len(bounces) == 0


@then("exactly 1 bounce is detected near frame 20")
def one_bounce_near_20(bounces):
    assert len(bounces) == 1
    assert abs(bounces[0].frame_idx - 20) <= 3
