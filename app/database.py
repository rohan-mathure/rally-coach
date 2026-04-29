from contextlib import asynccontextmanager

import aiosqlite

from app.config import settings


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                error_message TEXT,
                fps REAL,
                total_frames INTEGER,
                width INTEGER,
                height INTEGER,
                total_shots INTEGER DEFAULT 0,
                avg_speed_mph REAL,
                avg_quality_score REAL,
                homography_matrix TEXT,
                processed_video_path TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shots (
                shot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                shot_number INTEGER NOT NULL,
                start_frame INTEGER,
                end_frame INTEGER,
                contact_frame INTEGER,
                start_time_sec REAL,
                shot_type TEXT DEFAULT 'unknown',
                shot_type_confidence REAL DEFAULT 0.0,
                spin_type TEXT DEFAULT 'unknown',
                spin_confidence REAL DEFAULT 0.0,
                speed_mph REAL,
                speed_confidence REAL DEFAULT 0.0,
                rpm_estimate REAL,
                net_clearance_inches REAL,
                cleared_net INTEGER,
                is_in INTEGER,
                is_close_call INTEGER DEFAULT 0,
                bounce_court_x REAL,
                bounce_court_y REAL,
                curvature_score REAL,
                quality_score REAL,
                detection_gap_frames INTEGER DEFAULT 0,
                pipeline_warnings TEXT DEFAULT '[]',
                trajectory TEXT DEFAULT '[]',
                pose TEXT,
                bounce TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        await db.commit()
