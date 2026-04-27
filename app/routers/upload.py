import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import get_db
from app.models.session import Session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


async def _save_session(session: Session) -> None:
    async with await get_db() as db:
        await db.execute(
            """INSERT INTO sessions
               (session_id, filename, uploaded_at, status)
               VALUES (?, ?, ?, ?)""",
            (session.session_id, session.filename,
             session.uploaded_at.isoformat(), session.status),
        )
        await db.commit()


async def _run_pipeline(session_id: str, video_path: Path) -> None:
    from pipeline.runner import run
    await run(session_id, video_path)


@router.post("", status_code=201)
async def upload_session(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")

    session_id = str(uuid.uuid4())
    dest = settings.uploads_dir / f"{session_id}{Path(file.filename or 'video.mp4').suffix}"

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    session = Session(
        session_id=session_id,
        filename=file.filename or dest.name,
        uploaded_at=datetime.now(timezone.utc),
        status="queued",
    )
    await _save_session(session)

    background_tasks.add_task(_run_pipeline, session_id, dest)

    return {"session_id": session_id, "status": "queued"}
