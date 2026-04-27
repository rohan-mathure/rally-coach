from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.database import get_db

router = APIRouter(prefix="/api/sessions", tags=["video"])


@router.get("/{session_id}/video")
async def get_video(session_id: str):
    async with await get_db() as db:
        async with db.execute(
            "SELECT processed_video_path, status FROM sessions WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row["status"] != "complete":
        raise HTTPException(status_code=202, detail="Video not ready yet")

    path = Path(row["processed_video_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Processed video file missing")

    return FileResponse(path, media_type="video/mp4")
