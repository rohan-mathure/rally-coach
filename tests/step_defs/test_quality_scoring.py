import uuid

from pytest_bdd import given, scenarios, then, when

scenarios("quality_scoring.feature")


def _make_shot(**kwargs):
    from app.models.shot import Shot

    defaults = dict(
        shot_id=str(uuid.uuid4()),
        session_id="s1",
        shot_number=1,
        start_frame=0,
        end_frame=50,
        contact_frame=10,
        start_time_sec=0.0,
    )
    return Shot(**{**defaults, **kwargs})


@given(
    "a shot that is in bounds, cleared the net, landed deep, and has speed_mph 70",
    target_fixture="quality_shots",
)
def shot_high_quality():
    return [_make_shot(is_in=True, cleared_net=True, bounce_court_x=0.0, bounce_court_y=60.0, speed_mph=70.0)]


@given(
    "a shot that is out of bounds, did not clear the net, and has speed_mph 30",
    target_fixture="quality_shots",
)
def shot_low_quality():
    return [_make_shot(is_in=False, cleared_net=False, speed_mph=30.0)]


@given("3 shots with varying speeds 40 50 and 60 mph", target_fixture="quality_shots")
def shots_varying_speeds():
    return [
        _make_shot(shot_number=i + 1, speed_mph=float(spd), is_in=True)
        for i, spd in enumerate([40, 50, 60])
    ]


@when("quality scoring runs", target_fixture="scored_shots")
def run_quality_scoring(quality_shots):
    from pipeline.stages.shot_quality import compute_quality_scores

    return compute_quality_scores(quality_shots)


@then("the quality_score is at least 80")
def score_high(scored_shots):
    assert scored_shots[0].quality_score is not None
    assert scored_shots[0].quality_score >= 80


@then("the quality_score is at most 30")
def score_low(scored_shots):
    assert scored_shots[0].quality_score is not None
    assert scored_shots[0].quality_score <= 30


@then("all shots have a quality_score between 0 and 100")
def all_scores_valid(scored_shots):
    for shot in scored_shots:
        assert shot.quality_score is not None
        assert 0 <= shot.quality_score <= 100
