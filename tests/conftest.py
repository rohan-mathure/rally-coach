import sqlite3
import uuid
from datetime import datetime, timezone

import pytest


@pytest.fixture
def tmp_db_settings(tmp_path, monkeypatch):
    """Patches settings in all modules that import it. Returns Settings object."""
    import app.database
    import app.routers.upload
    from app.config import Settings

    new_settings = Settings(storage_dir=str(tmp_path))
    monkeypatch.setattr(app.database, "settings", new_settings)
    monkeypatch.setattr(app.routers.upload, "settings", new_settings)
    return new_settings


@pytest.fixture
def app_client(tmp_db_settings, monkeypatch):
    """Sync TestClient; ASGI lifespan runs init_db() on enter."""
    from starlette.testclient import TestClient

    import app.routers.upload

    async def _noop_pipeline(*args, **kwargs):
        pass

    monkeypatch.setattr(app.routers.upload, "_run_pipeline", _noop_pipeline)

    from app.main import app as fastapi_app

    with TestClient(app=fastapi_app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture
def seeded_session(app_client, tmp_db_settings):
    """One complete session row; returns session_id."""
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(tmp_db_settings.db_path))
    conn.execute(
        "INSERT INTO sessions (session_id, filename, uploaded_at, status) VALUES (?, ?, ?, ?)",
        (session_id, "test.mp4", datetime.now(timezone.utc).isoformat(), "complete"),
    )
    conn.commit()
    conn.close()
    return session_id


@pytest.fixture
def seeded_shots(seeded_session, tmp_db_settings):
    """Three shot rows; returns (session_id, [shot_ids])."""
    session_id = seeded_session
    shot_ids = []
    conn = sqlite3.connect(str(tmp_db_settings.db_path))
    for i in range(1, 4):
        shot_id = str(uuid.uuid4())
        shot_ids.append(shot_id)
        conn.execute(
            """INSERT INTO shots
               (shot_id, session_id, shot_number, start_frame, end_frame,
                contact_frame, start_time_sec)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (shot_id, session_id, i, i * 100, i * 100 + 50, i * 100 + 10, float(i)),
        )
    conn.commit()
    conn.close()
    return session_id, shot_ids


@pytest.fixture
def make_positions():
    """Factory: list[BallPosition] for given frame count, optional ys/xs/interpolation mask."""
    from app.models.shot import BallPosition

    def _factory(frames, ys=None, xs=None, is_interpolated=None):
        return [
            BallPosition(
                frame_idx=i,
                x=float(xs[i] if xs is not None else 320),
                y=float(ys[i] if ys is not None else 300),
                confidence=0.9,
                is_interpolated=bool(is_interpolated[i]) if is_interpolated is not None else False,
            )
            for i in range(frames)
        ]

    return _factory


@pytest.fixture
def make_homography():
    """CourtHomography from a clean pixel↔ITF-court mapping.

    pixel corners:  (80,450) (560,450) (560,50) (80,50)
    court corners: (-13.5,0) (13.5,0) (13.5,78) (-13.5,78)
    Baseline pixel width = 480 px  →  scale ≈ 0.05625 ft/px.
    """
    import cv2
    import numpy as np

    from pipeline.models.homography import CourtHomography

    src = np.array([[80, 450], [560, 450], [560, 50], [80, 50]], dtype=np.float32)
    dst = np.array([[-13.5, 0.0], [13.5, 0.0], [13.5, 78.0], [-13.5, 78.0]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    return CourtHomography(H)
