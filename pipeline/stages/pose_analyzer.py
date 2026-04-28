import numpy as np
from loguru import logger

from app.models.shot import PoseLandmarks, Shot
from pipeline.utils.video_io import VideoReader

POSE_WINDOW = 30  # frames either side of contact to search


def extract_poses(shots: list[Shot], reader: VideoReader) -> list[Shot]:
    try:
        import mediapipe as mp
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=0.5,
        )
    except Exception as e:
        logger.warning(f"MediaPipe not available: {e}. Skipping pose extraction.")
        return shots

    updated = []
    for shot in shots:
        best_result = None
        best_conf = 0.0
        best_frame_idx = shot.contact_frame

        search_start = max(0, shot.contact_frame - POSE_WINDOW)
        search_end = shot.contact_frame + POSE_WINDOW

        for frame_idx, frame in reader.read_frame_range(search_start, search_end):
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)
            if result.pose_landmarks:
                visibilities = [lm.visibility for lm in result.pose_landmarks.landmark]
                avg_conf = float(np.mean(visibilities))
                if avg_conf > best_conf:
                    best_conf = avg_conf
                    best_result = result
                    best_frame_idx = frame_idx

        if best_result and best_conf >= 0.5:
            lms = best_result.pose_landmarks.landmark
            landmarks_data = [
                {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                for lm in lms
            ]

            # MediaPipe landmark indices:
            # 15=left_wrist, 16=right_wrist, 23=left_hip, 24=right_hip
            left_wrist = lms[15]
            right_wrist = lms[16]
            left_hip = lms[23]
            right_hip = lms[24]
            hip_cx = (left_hip.x + right_hip.x) / 2
            hip_cy = (left_hip.y + right_hip.y) / 2

            # Dominant wrist = whichever is more visible and extended
            dominant_wrist = right_wrist if right_wrist.visibility >= left_wrist.visibility else left_wrist

            shot = shot.model_copy(update={
                "pose": PoseLandmarks(
                    frame_idx=best_frame_idx,
                    landmarks=landmarks_data,
                    dominant_wrist_x=dominant_wrist.x,
                    dominant_wrist_y=dominant_wrist.y,
                    hip_center_x=hip_cx,
                    hip_center_y=hip_cy,
                )
            })
        else:
            warnings = list(shot.pipeline_warnings)
            if "pose_low_conf" not in warnings:
                warnings.append("pose_low_conf")
            shot = shot.model_copy(update={"pipeline_warnings": warnings})

        updated.append(shot)

    pose.close()
    return updated
