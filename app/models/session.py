from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel


class Session(BaseModel):
    session_id: str
    filename: str
    uploaded_at: datetime
    status: Literal["queued", "processing", "complete", "error"] = "queued"
    error_message: Optional[str] = None
    fps: Optional[float] = None
    total_frames: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    total_shots: int = 0
    avg_speed_mph: Optional[float] = None
    avg_quality_score: Optional[float] = None
    homography_matrix: Optional[list[list[float]]] = None
    processed_video_path: Optional[str] = None
