import json

from fastapi import APIRouter, HTTPException

from app.database import get_db

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("homography_matrix"):
        d["homography_matrix"] = json.loads(d["homography_matrix"])
    return d


@router.get("")
async def list_sessions():
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM sessions ORDER BY uploaded_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/{session_id}")
async def get_session(session_id: str):
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return _row_to_dict(row)


@router.post("/{session_id}/calibrate")
async def manual_calibrate(session_id: str, corners: list[list[float]]):
    """Accept 4 pixel corners [top-left, top-right, bottom-right, bottom-left]
    and recompute homography manually."""
    if len(corners) != 4 or any(len(c) != 2 for c in corners):
        raise HTTPException(status_code=400, detail="Provide exactly 4 [x,y] corners")

    import cv2
    import numpy as np

    from pipeline.utils.court_constants import ITF_CORNERS_FEET

    src = np.array(corners, dtype=np.float32)
    dst = np.array(ITF_CORNERS_FEET, dtype=np.float32)
    H, _ = cv2.findHomography(src, dst)

    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET homography_matrix = ? WHERE session_id = ?",
            (json.dumps(H.tolist()), session_id),
        )
        await db.commit()
    return {"status": "calibrated"}
