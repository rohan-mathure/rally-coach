import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("upload.feature")


@pytest.fixture
def ctx():
    return {}


@given("a valid mp4 file exists on disk", target_fixture="video_path")
def valid_mp4(tmp_path):
    p = tmp_path / "test_video.mp4"
    p.write_bytes(b"fake mp4 content")
    return str(p)


@given("a txt file exists on disk", target_fixture="video_path")
def txt_file(tmp_path):
    p = tmp_path / "test.txt"
    p.write_bytes(b"not a video")
    return str(p)


@when("I POST to /api/sessions/from-path with that file path")
def post_from_path(video_path, app_client, ctx):
    ctx["response"] = app_client.post("/api/sessions/from-path", json={"path": video_path})


@when(parsers.parse('I POST to /api/sessions/from-path with path "{path}"'))
def post_from_missing_path(path, app_client, ctx):
    ctx["response"] = app_client.post("/api/sessions/from-path", json={"path": path})


@then("the upload response status is 201")
def upload_status_201(ctx):
    assert ctx["response"].status_code == 201


@then("the upload response status is 400")
def upload_status_400(ctx):
    assert ctx["response"].status_code == 400


@then("the upload response contains a session_id")
def upload_has_session_id(ctx):
    assert "session_id" in ctx["response"].json()


@then('the upload response status field is "queued"')
def upload_status_queued(ctx):
    assert ctx["response"].json()["status"] == "queued"
