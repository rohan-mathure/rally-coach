export type SessionStatus = "queued" | "processing" | "complete" | "error";

export interface Session {
  session_id: string;
  filename: string;
  uploaded_at: string;
  status: SessionStatus;
  error_message?: string;
  fps?: number;
  total_frames?: number;
  width?: number;
  height?: number;
  total_shots: number;
  avg_speed_mph?: number;
  avg_quality_score?: number;
  homography_matrix?: number[][];
  processed_video_path?: string;
}

export interface BallPosition {
  frame_idx: number;
  x: number;
  y: number;
  confidence: number;
  is_interpolated: boolean;
}

export interface BounceEvent {
  frame_idx: number;
  pixel_x: number;
  pixel_y: number;
  court_x: number;
  court_y: number;
  is_in: boolean;
  is_close_call: boolean;
}

export type ShotType = "forehand" | "backhand" | "volley" | "overhead" | "unknown";
export type SpinType = "topspin" | "underspin" | "flat" | "unknown";

export interface Shot {
  shot_id: string;
  session_id: string;
  shot_number: number;
  start_frame: number;
  end_frame: number;
  contact_frame: number;
  start_time_sec: number;
  trajectory: BallPosition[];
  bounce?: BounceEvent;
  shot_type: ShotType;
  shot_type_confidence: number;
  spin_type: SpinType;
  spin_confidence: number;
  speed_mph?: number;
  speed_confidence: number;
  rpm_estimate?: number;
  net_clearance_inches?: number;
  cleared_net?: boolean | number;
  is_in?: boolean | number;
  is_close_call: boolean | number;
  bounce_court_x?: number;
  bounce_court_y?: number;
  curvature_score?: number;
  quality_score?: number;
  detection_gap_frames: number;
  pipeline_warnings: string[];
}
