import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger

from app.models.shot import Shot, BallPosition
from pipeline.models.homography import CourtHomography

TRAIL_LENGTH = 15
BALL_COLOR = (0, 215, 255)      # yellow
TRAIL_COLOR = (0, 165, 255)
IN_COLOR = (0, 200, 0)
OUT_COLOR = (0, 0, 220)
CLOSE_COLOR = (0, 165, 255)
NET_COLOR = (200, 200, 200)
COURT_LINE_COLOR = (180, 180, 180)


def _draw_hud(frame: np.ndarray, shot: Shot, fps: float) -> None:
    lines = [
        f"Shot #{shot.shot_number}",
        f"Type: {shot.shot_type}",
        f"Spin: {shot.spin_type}",
        f"Speed: {shot.speed_mph:.0f} mph" if shot.speed_mph else "Speed: --",
        f"Q: {shot.quality_score:.0f}" if shot.quality_score else "Q: --",
    ]
    y = 30
    for line in lines:
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        y += 22


def _draw_court_overlay(frame: np.ndarray, homography: CourtHomography) -> None:
    from pipeline.utils.court_constants import (
        SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT, HALF_COURT_FT,
        SERVICE_LINE_Y_NEAR, SERVICE_LINE_FROM_NET_FT
    )
    lines_ft = [
        # baselines
        [(-SINGLES_HALF_WIDTH_FT, 0), (SINGLES_HALF_WIDTH_FT, 0)],
        [(-SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT), (SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT)],
        # sidelines
        [(-SINGLES_HALF_WIDTH_FT, 0), (-SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT)],
        [(SINGLES_HALF_WIDTH_FT, 0), (SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT)],
        # net
        [(-SINGLES_HALF_WIDTH_FT, HALF_COURT_FT), (SINGLES_HALF_WIDTH_FT, HALF_COURT_FT)],
        # service lines
        [(-SINGLES_HALF_WIDTH_FT, SERVICE_LINE_Y_NEAR), (SINGLES_HALF_WIDTH_FT, SERVICE_LINE_Y_NEAR)],
        [(-SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT - SERVICE_LINE_FROM_NET_FT),
         (SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT - SERVICE_LINE_FROM_NET_FT)],
        # center service line
        [(0, HALF_COURT_FT), (0, SERVICE_LINE_Y_NEAR)],
    ]
    overlay = frame.copy()
    for (cx1, cy1), (cx2, cy2) in lines_ft:
        px1, py1 = homography.court_to_pixel(cx1, cy1)
        px2, py2 = homography.court_to_pixel(cx2, cy2)
        cv2.line(overlay, (int(px1), int(py1)), (int(px2), int(py2)), COURT_LINE_COLOR, 1)
    cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)


def annotate_video(
    input_path: Path,
    output_path: Path,
    shots: list[Shot],
    all_positions: list[BallPosition],
    homography: Optional[CourtHomography],
    fps: float,
) -> None:
    cap = cv2.VideoCapture(str(input_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tmp_path = output_path.with_suffix(".avi")
    writer = cv2.VideoWriter(str(tmp_path), cv2.VideoWriter_fourcc(*"XVID"), fps, (width, height))

    # Index shots by frame range for O(1) lookup
    shot_by_frame: dict[int, Shot] = {}
    for shot in shots:
        for f in range(shot.start_frame, shot.end_frame + 1):
            shot_by_frame[f] = shot

    pos_by_frame: dict[int, BallPosition] = {p.frame_idx: p for p in all_positions}
    bounce_frames: dict[int, tuple] = {}
    for shot in shots:
        if shot.bounce:
            bounce_frames[shot.bounce.frame_idx] = (
                int(shot.bounce.pixel_x), int(shot.bounce.pixel_y),
                shot.bounce.is_in, shot.bounce.is_close_call,
            )

    frame_idx = 0
    recent_positions: list[BallPosition] = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if homography:
            _draw_court_overlay(frame, homography)

        # Maintain trail
        if frame_idx in pos_by_frame:
            recent_positions.append(pos_by_frame[frame_idx])
            if len(recent_positions) > TRAIL_LENGTH:
                recent_positions.pop(0)

        # Draw trail
        for i, pos in enumerate(recent_positions[:-1]):
            alpha = int(80 + 170 * (i / max(len(recent_positions) - 1, 1)))
            color = (TRAIL_COLOR[0], TRAIL_COLOR[1], min(255, alpha))
            cv2.circle(frame, (int(pos.x), int(pos.y)), 3, TRAIL_COLOR, -1)

        # Draw current ball
        if frame_idx in pos_by_frame:
            pos = pos_by_frame[frame_idx]
            if pos.is_interpolated:
                cv2.circle(frame, (int(pos.x), int(pos.y)), 6, BALL_COLOR, 1)
            else:
                cv2.circle(frame, (int(pos.x), int(pos.y)), 6, BALL_COLOR, -1)

        # Draw bounce
        if frame_idx in bounce_frames:
            bx, by, is_in, is_close = bounce_frames[frame_idx]
            color = CLOSE_COLOR if is_close else (IN_COLOR if is_in else OUT_COLOR)
            cv2.circle(frame, (bx, by), 10, color, -1)
            cv2.putText(frame, "IN" if is_in else "OUT", (bx + 12, by),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Draw HUD for current shot
        if frame_idx in shot_by_frame:
            _draw_hud(frame, shot_by_frame[frame_idx], fps)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    # Re-encode to H.264 MP4 for browser compatibility
    _reencode_h264(tmp_path, output_path)
    tmp_path.unlink(missing_ok=True)
    logger.info(f"Annotated video saved: {output_path}")


def _reencode_h264(src: Path, dst: Path) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-vcodec", "libx264", "-crf", "23",
             "-preset", "fast", "-movflags", "+faststart", str(dst)],
            check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"ffmpeg re-encode failed: {e}. Copying AVI as fallback.")
        import shutil
        shutil.copy(src, dst.with_suffix(".avi"))
