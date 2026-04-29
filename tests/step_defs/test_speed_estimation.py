import uuid

from pytest_bdd import given, scenarios, then, when

scenarios("speed_estimation.feature")


def _make_shot(px_per_frame: float):
    """Shot with 7 trajectory positions after contact_frame=10, moving px_per_frame in x."""
    from app.models.shot import BallPosition, Shot

    traj = [
        BallPosition(frame_idx=10 + i, x=100.0 + px_per_frame * i, y=300.0, confidence=0.9)
        for i in range(7)
    ]
    return Shot(
        shot_id=str(uuid.uuid4()),
        session_id="s1",
        shot_number=1,
        start_frame=0,
        end_frame=20,
        contact_frame=10,
        start_time_sec=0.33,
        trajectory=traj,
    )


@given(
    "a shot with 6 post-contact positions moving 10 pixels per frame",
    target_fixture="input_shot",
)
def shot_10px():
    return _make_shot(10.0)


@given(
    "a shot with 6 post-contact positions moving 5000 pixels per frame",
    target_fixture="input_shot",
)
def shot_5000px():
    return _make_shot(5000.0)


@when("speed estimation runs at 30 fps with valid homography", target_fixture="result_shot")
def estimate_with_homography(input_shot, make_homography):
    from pipeline.stages.speed_estimator import estimate_speeds

    return estimate_speeds(
        [input_shot], fps=30.0, homography=make_homography, frame_width=640, frame_height=480
    )[0]


@when("speed estimation runs at 30 fps with no homography", target_fixture="result_shot")
def estimate_no_homography(input_shot):
    from pipeline.stages.speed_estimator import estimate_speeds

    return estimate_speeds(
        [input_shot], fps=30.0, homography=None, frame_width=640, frame_height=480
    )[0]


@then("speed_mph is between 5 and 160")
def speed_in_range(result_shot):
    assert result_shot.speed_mph is not None
    assert 5 <= result_shot.speed_mph <= 160


@then("speed_confidence is greater than 0")
def speed_conf_positive(result_shot):
    assert result_shot.speed_confidence > 0


@then("speed_mph is None")
def speed_is_none(result_shot):
    assert result_shot.speed_mph is None


@then("speed_confidence is 0.0")
def speed_conf_zero(result_shot):
    assert result_shot.speed_confidence == 0.0
