from typing import Literal, Optional

from pydantic import BaseModel


class BallPosition(BaseModel):
    frame_idx: int
    x: float
    y: float
    confidence: float
    is_interpolated: bool = False


class BounceEvent(BaseModel):
    frame_idx: int
    pixel_x: float
    pixel_y: float
    court_x: float
    court_y: float
    is_in: bool
    is_close_call: bool = False


class PoseLandmarks(BaseModel):
    frame_idx: int
    landmarks: list[dict]
    dominant_wrist_x: float
    dominant_wrist_y: float
    hip_center_x: float
    hip_center_y: float


class Shot(BaseModel):
    shot_id: str
    session_id: str
    shot_number: int
    start_frame: int
    end_frame: int
    contact_frame: int
    start_time_sec: float
    trajectory: list[BallPosition] = []
    bounce: Optional[BounceEvent] = None
    shot_type: Literal["forehand", "backhand", "volley", "overhead", "unknown"] = "unknown"
    shot_type_confidence: float = 0.0
    spin_type: Literal["topspin", "underspin", "flat", "unknown"] = "unknown"
    spin_confidence: float = 0.0
    speed_mph: Optional[float] = None
    speed_confidence: float = 0.0
    rpm_estimate: Optional[float] = None
    net_clearance_inches: Optional[float] = None
    cleared_net: Optional[bool] = None
    is_in: Optional[bool] = None
    is_close_call: bool = False
    bounce_court_x: Optional[float] = None
    bounce_court_y: Optional[float] = None
    pose: Optional[PoseLandmarks] = None
    curvature_score: Optional[float] = None
    quality_score: Optional[float] = None
    detection_gap_frames: int = 0
    pipeline_warnings: list[str] = []
