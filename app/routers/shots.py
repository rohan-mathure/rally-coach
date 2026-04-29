import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.database import get_db

router = APIRouter(prefix="/api/sessions", tags=["shots"])


@router.get("/{session_id}/shots")
async def list_shots(session_id: str):
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM shots WHERE session_id = ? ORDER BY shot_number",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()

    shots = []
    for row in rows:
        d = dict(row)
        for field in ("trajectory", "pipeline_warnings", "bounce", "pose"):
            if d.get(field):
                d[field] = json.loads(d[field])
        shots.append(d)
    return shots


@router.get("/{session_id}/shots/csv")
async def export_shots_csv(session_id: str):
    async with get_db() as db:
        async with db.execute(
            """SELECT shot_number, start_time_sec, shot_type, spin_type,
                      speed_mph, cleared_net, is_in, is_close_call,
                      quality_score, rpm_estimate, net_clearance_inches
               FROM shots WHERE session_id = ? ORDER BY shot_number""",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()

    headers = [
        "shot_number", "time_sec", "shot_type", "spin_type",
        "speed_mph", "cleared_net", "is_in", "is_close_call",
        "quality_score", "rpm_estimate", "net_clearance_inches",
    ]
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(v) if v is not None else "" for v in row))

    content = "\n".join(lines)

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{session_id}_shots.csv"'},
    )
