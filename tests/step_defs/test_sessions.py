import sqlite3
import uuid
from datetime import datetime, timezone

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("sessions.feature")


@pytest.fixture
def ctx():
    return {}


@given("the database has 2 sessions")
def two_sessions_in_db(app_client, tmp_db_settings):
    conn = sqlite3.connect(str(tmp_db_settings.db_path))
    for i in range(2):
        conn.execute(
            "INSERT INTO sessions (session_id, filename, uploaded_at, status) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), f"video{i}.mp4", datetime.now(timezone.utc).isoformat(), "complete"),
        )
    conn.commit()
    conn.close()


@given(parsers.parse('a session "{session_id}" exists'))
def session_exists(session_id, app_client, tmp_db_settings):
    conn = sqlite3.connect(str(tmp_db_settings.db_path))
    conn.execute(
        "INSERT INTO sessions (session_id, filename, uploaded_at, status) VALUES (?, ?, ?, ?)",
        (session_id, "test.mp4", datetime.now(timezone.utc).isoformat(), "complete"),
    )
    conn.commit()
    conn.close()


@given("the sessions database is empty")
def sessions_db_empty():
    pass  # DB starts empty; app_client lifespan only creates tables


@when("I GET /api/sessions")
def get_sessions(app_client, ctx):
    ctx["response"] = app_client.get("/api/sessions")


@when(parsers.parse("I GET /api/sessions/{session_id}"))
def get_session(session_id, app_client, ctx):
    ctx["response"] = app_client.get(f"/api/sessions/{session_id}")


@when(parsers.parse('I POST calibrate for session "{session_id}" with 4 valid corners'))
def calibrate_session(session_id, app_client, ctx):
    corners = [[100.0, 400.0], [500.0, 400.0], [500.0, 100.0], [100.0, 100.0]]
    ctx["response"] = app_client.post(f"/api/sessions/{session_id}/calibrate", json=corners)


@then("the sessions response status is 200")
def sessions_status_200(ctx):
    assert ctx["response"].status_code == 200


@then("the sessions list has 2 items")
def sessions_list_2(ctx):
    assert len(ctx["response"].json()) == 2


@then("the session response status is 200")
def session_status_200(ctx):
    assert ctx["response"].status_code == 200


@then("the session response status is 404")
def session_status_404(ctx):
    assert ctx["response"].status_code == 404


@then(parsers.parse('the session response contains session_id "{session_id}"'))
def session_has_id(ctx, session_id):
    assert ctx["response"].json()["session_id"] == session_id


@then("the calibrate response status is 200")
def calibrate_status_200(ctx):
    assert ctx["response"].status_code == 200


@then('the calibrate response status field is "calibrated"')
def calibrate_status_calibrated(ctx):
    assert ctx["response"].json()["status"] == "calibrated"
