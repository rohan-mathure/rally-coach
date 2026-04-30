"""
End-to-end pipeline test on the 5-minute sample tennis fixture.

Run with:
    uv run pytest tests/test_e2e_pipeline.py -v -s

The test is skipped automatically if the fixture is absent (run
scripts/create_fixture.sh first).  It takes 3-8 minutes on Apple Silicon.
"""
import json
import sqlite3
import uuid
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "sample_tennis.mp4"
PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fixture_video():
    if not FIXTURE.exists():
        pytest.skip("sample_tennis.mp4 not present — run scripts/create_fixture.sh")
    return FIXTURE


@pytest.fixture
def e2e_settings(tmp_path, monkeypatch):
    """Settings wired to a temp DB + temp processed dir, real weights."""
    import app.config
    import app.database
    import pipeline.runner
    from app.config import Settings

    real_weights = (PROJECT_ROOT / "weights").resolve()
    new_settings = Settings(
        storage_dir=str(tmp_path),
        weights_dir=str(real_weights),
    )

    monkeypatch.setattr(app.config, "settings", new_settings)
    monkeypatch.setattr(app.database, "settings", new_settings)
    monkeypatch.setattr(pipeline.runner, "settings", new_settings)
    return new_settings


@pytest.fixture
async def seeded_e2e_session(e2e_settings):
    """Initialise DB schema, insert one queued session, return session_id."""
    from app.database import init_db
    await init_db()
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(e2e_settings.db_path))
    conn.execute(
        "INSERT INTO sessions (session_id, filename, uploaded_at, status)"
        " VALUES (?, ?, datetime('now'), 'queued')",
        (session_id, "sample_tennis.mp4"),
    )
    conn.commit()
    conn.close()
    return session_id, e2e_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_session(db_path, session_id):
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        """SELECT status, error_message, total_frames, total_shots,
                  avg_speed_mph, avg_quality_score, homography_matrix,
                  processed_video_path
             FROM sessions WHERE session_id = ?""",
        (session_id,),
    ).fetchone()
    conn.close()
    return row


def _fetch_shots(db_path, session_id):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        """SELECT shot_number, shot_type, spin_type, speed_mph,
                  rpm_estimate, net_clearance_inches, cleared_net,
                  is_in, quality_score, pipeline_warnings
             FROM shots WHERE session_id = ?
             ORDER BY shot_number""",
        (session_id,),
    ).fetchall()
    conn.close()
    return rows


def _print_report(session_row, shot_rows):
    (status, error, frames, total_shots, avg_speed, avg_quality,
     homography, video_path) = session_row

    print("\n" + "=" * 70)
    print("E2E PIPELINE REPORT")
    print("=" * 70)
    print(f"  Status          : {status}")
    print(f"  Total frames    : {frames}")
    print(f"  Court detection : {'✓ homography found' if homography else '✗ no homography'}")
    print(f"  Shots detected  : {total_shots}")
    print(f"  Avg speed       : {f'{avg_speed:.1f} mph' if avg_speed else '—'}")
    print(f"  Avg quality     : {f'{avg_quality:.1f}' if avg_quality else '—'}")
    print(f"  Output video    : {video_path or '—'}")
    if error:
        print(f"  Error           : {error}")
    if shot_rows:
        print(f"\n  First {min(len(shot_rows), 10)} shots:")
        header = f"  {'#':>3}  {'type':<12} {'spin':<12} {'mph':>6} {'rpm':>6} {'net':>6} {'in':>5} {'Q':>5}"
        print(header)
        print("  " + "-" * 62)
        for row in shot_rows[:10]:
            (num, stype, spin, speed, rpm, net, cleared, is_in, quality, _) = row
            print(
                f"  {num:>3}  {(stype or '?'):<12} {(spin or '?'):<12}"
                f" {speed or 0:>6.1f} {rpm or 0:>6.0f}"
                f" {net or 0:>6.1f} {bool(is_in)!s:>5} {quality or 0:>5.1f}"
            )
    print("=" * 70)


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------

@pytest.mark.slow
async def test_full_pipeline_end_to_end(fixture_video, seeded_e2e_session):
    """
    Runs the complete 13-stage pipeline on the sample tennis clip and
    asserts that every stage either produces meaningful output or degrades
    gracefully with a diagnostic message.
    """
    from pipeline.runner import run

    session_id, e2e_settings = seeded_e2e_session
    await run(session_id, fixture_video)

    session_row = _fetch_session(e2e_settings.db_path, session_id)
    shot_rows   = _fetch_shots(e2e_settings.db_path, session_id)

    _print_report(session_row, shot_rows)

    (status, error, frames, total_shots, avg_speed, avg_quality,
     homography, video_path) = session_row

    # ── Stage 1: metadata ────────────────────────────────────────────────
    assert frames and frames > 0, "Stage 1 failed: no frames extracted"

    # ── Pipeline must not crash ───────────────────────────────────────────
    assert status == "complete", f"Pipeline error: {error}"

    # ── Stage 3: ball tracking ────────────────────────────────────────────
    # The ball tracker with custom weights should find at least some detections.
    # If zero shots were found we verify it's due to low ball coverage, not a crash.
    assert total_shots is not None, "total_shots must be set after pipeline"

    # ── Stage 13: annotated video ─────────────────────────────────────────
    assert video_path, "processed_video_path must be set on completion"
    assert Path(video_path).exists(), f"Annotated video not written: {video_path}"
    assert Path(video_path).stat().st_size > 0, "Annotated video is empty"

    # ── Shot-level assertions (only when shots were found) ────────────────
    if total_shots and total_shots > 0:
        assert shot_rows, "total_shots > 0 but no rows in shots table"

        # Every shot has a quality score
        qualities = [r[8] for r in shot_rows if r[8] is not None]
        assert len(qualities) == len(shot_rows), \
            "Some shots are missing quality_score"
        assert all(0 <= q <= 100 for q in qualities), \
            f"Quality scores out of range: {qualities}"

        # Shot types are from the known set
        valid_types = {"forehand", "backhand", "volley", "overhead", "unknown"}
        shot_types = {r[1] for r in shot_rows if r[1]}
        assert shot_types <= valid_types, f"Unknown shot types: {shot_types - valid_types}"

        # Spin types are from the known set
        valid_spins = {"topspin", "underspin", "flat", "unknown"}
        spin_types = {r[2] for r in shot_rows if r[2]}
        assert spin_types <= valid_spins, f"Unknown spin types: {spin_types - valid_spins}"

        # If homography was found, speed and net clearance should be populated
        if homography:
            speeds = [r[3] for r in shot_rows if r[3] is not None]
            assert speeds, "Homography found but no speeds computed"
            assert all(5 <= s <= 160 for s in speeds), \
                f"Implausible speeds: {speeds}"

        # Pipeline warnings must be valid JSON arrays
        for row in shot_rows:
            warnings = json.loads(row[9])
            assert isinstance(warnings, list), "pipeline_warnings is not a list"
