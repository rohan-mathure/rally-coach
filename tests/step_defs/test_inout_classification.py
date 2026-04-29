import uuid

from pytest_bdd import given, scenarios, then, when

scenarios("inout_classification.feature")


def _make_shot_with_bounce(court_x: float, court_y: float):
    from app.models.shot import BounceEvent, Shot

    bounce = BounceEvent(
        frame_idx=30,
        pixel_x=320.0,
        pixel_y=300.0,
        court_x=court_x,
        court_y=court_y,
        is_in=False,
        is_close_call=False,
    )
    return Shot(
        shot_id=str(uuid.uuid4()),
        session_id="s1",
        shot_number=1,
        start_frame=0,
        end_frame=50,
        contact_frame=10,
        start_time_sec=0.0,
        bounce=bounce,
        bounce_court_x=court_x,
        bounce_court_y=court_y,
    )


@given("a shot with a bounce at court position (0.0, 39.0)", target_fixture="inout_shot")
def shot_center_court():
    return _make_shot_with_bounce(0.0, 39.0)


@given("a shot with a bounce at court position (20.0, 39.0)", target_fixture="inout_shot")
def shot_outside_court():
    return _make_shot_with_bounce(20.0, 39.0)


@when("inout classification runs with valid homography", target_fixture="classified_shot")
def classify_with_homography(inout_shot, make_homography):
    from pipeline.stages.inout_classifier import classify_inout

    return classify_inout([inout_shot], make_homography)[0]


@when("inout classification runs with no homography", target_fixture="classified_shot")
def classify_no_homography(inout_shot):
    from pipeline.stages.inout_classifier import classify_inout

    return classify_inout([inout_shot], homography=None)[0]


@then("the shot is_in is True")
def shot_is_in(classified_shot):
    assert classified_shot.is_in is True


@then("the shot is_in is False")
def shot_is_out(classified_shot):
    assert classified_shot.is_in is False


@then("the shot is_close_call is False")
def shot_not_close(classified_shot):
    assert classified_shot.is_close_call is False


@then("the shot is returned unmodified")
def shot_unmodified(inout_shot, classified_shot):
    assert classified_shot.shot_id == inout_shot.shot_id
    assert classified_shot.bounce_court_x == inout_shot.bounce_court_x
    assert classified_shot.bounce_court_y == inout_shot.bounce_court_y
