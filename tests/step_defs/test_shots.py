import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("shots.feature")


@pytest.fixture
def ctx():
    return {}


@given("a session with 3 shots exists", target_fixture="shots_session_id")
def session_with_shots(seeded_shots):
    session_id, _ = seeded_shots
    return session_id


@when("I GET the shots for that session")
def get_shots(shots_session_id, app_client, ctx):
    ctx["response"] = app_client.get(f"/api/sessions/{shots_session_id}/shots")


@when("I GET the CSV export for that session")
def get_csv(shots_session_id, app_client, ctx):
    ctx["response"] = app_client.get(f"/api/sessions/{shots_session_id}/shots/csv")


@then("the shots response status is 200")
def shots_status_200(ctx):
    assert ctx["response"].status_code == 200


@then("the shots list has 3 items in shot_number order")
def shots_list_ordered(ctx):
    shots = ctx["response"].json()
    assert len(shots) == 3
    numbers = [s["shot_number"] for s in shots]
    assert numbers == sorted(numbers)


@then("the CSV response content-type is text/csv")
def csv_content_type(ctx):
    assert "text/csv" in ctx["response"].headers["content-type"]


@then('the CSV body contains the header "shot_number"')
def csv_has_header(ctx):
    first_line = ctx["response"].text.split("\n")[0]
    assert "shot_number" in first_line
