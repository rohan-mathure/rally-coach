from pytest_bdd import given, scenarios, then, when

scenarios("shot_segmentation.feature")


def _make_bounces(frame_a, frame_b):
    from app.models.shot import BounceEvent
    return [
        BounceEvent(frame_idx=frame_a, pixel_x=320, pixel_y=350, court_x=0, court_y=10, is_in=True),
        BounceEvent(frame_idx=frame_b, pixel_x=320, pixel_y=350, court_x=0, court_y=68, is_in=True),
    ]


def _make_pos_range(start, end, is_interpolated=None):
    from app.models.shot import BallPosition
    interp = is_interpolated or {}
    return [
        BallPosition(
            frame_idx=i,
            x=320.0,
            y=300.0,
            confidence=0.9,
            is_interpolated=interp.get(i, False),
        )
        for i in range(start, end + 1)
    ]


@given("2 bounces at frames 10 and 60 and positions covering frames 0 to 70", target_fixture="seg_input")
def input_two_bounces():
    return _make_bounces(10, 60), _make_pos_range(0, 70)


@given("2 bounces at frames 10 and 15 and positions covering frames 0 to 20", target_fixture="seg_input")
def input_short_segment():
    return _make_bounces(10, 15), _make_pos_range(0, 20)


@given(
    "2 bounces at frames 10 and 60 and positions with 10 consecutive interpolated frames from 30",
    target_fixture="seg_input",
)
def input_with_gap():
    interp = {i: True for i in range(30, 40)}
    return _make_bounces(10, 60), _make_pos_range(0, 70, is_interpolated=interp)


@when("shot segmentation runs at 30 fps", target_fixture="shots")
def run_segmentation(seg_input):
    from pipeline.stages.shot_segmenter import segment_shots
    bounces, positions = seg_input
    return segment_shots(positions, bounces, fps=30.0, session_id="test-session")


@then("1 shot is returned")
def one_shot(shots):
    assert len(shots) == 1


@then("0 shots are returned")
def zero_shots(shots):
    assert len(shots) == 0


@then("the shot start_frame is 10 and end_frame is 60")
def shot_frames(shots):
    assert shots[0].start_frame == 10
    assert shots[0].end_frame == 60


@then('the shot pipeline_warnings contains "long_detection_gap"')
def shot_has_gap_warning(shots):
    assert "long_detection_gap" in shots[0].pipeline_warnings
