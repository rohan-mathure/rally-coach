import urllib.request
from pathlib import Path

import numpy as np
from loguru import logger

from app.models.shot import PoseLandmarks, Shot
from pipeline.utils.video_io import VideoReader

POSE_WINDOW = 30
_POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
_POSE_MODEL_FILENAME = "pose_landmarker_lite.task"


def _get_model(weights_dir: Path) -> Path:
    path = weights_dir / _POSE_MODEL_FILENAME
    if not path.exists():
        logger.info(f"Downloading pose landmarker model → {path}")
        weights_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_POSE_MODEL_URL, path)
        logger.info("Pose landmarker model downloaded")
    return path


def extract_poses(shots: list[Shot], reader: VideoReader) -> list[Shot]:
    try:
        import cv2
        import mediapipe as mp

        from app.config import settings

        model_path = _get_model(settings.weights_dir)
        landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(
            mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=0.5,
            )
        )
    except Exception as e:
        logger.warning(f"MediaPipe not available: {e}. Skipping pose extraction.")
        return shots

    updated = []
    for shot in shots:
        best_landmarks = None
        best_conf = 0.0
        best_frame_idx = shot.contact_frame

        search_start = max(0, shot.contact_frame - POSE_WINDOW)
        search_end = shot.contact_frame + POSE_WINDOW

        for frame_idx, frame in reader.read_frame_range(search_start, search_end):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if result.pose_landmarks:
                lms = result.pose_landmarks[0]
                avg_conf = float(np.mean([lm.visibility for lm in lms]))
                if avg_conf > best_conf:
                    best_conf = avg_conf
                    best_landmarks = lms
                    best_frame_idx = frame_idx

        if best_landmarks and best_conf >= 0.5:
            landmarks_data = [
                {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                for lm in best_landmarks
            ]

            # MediaPipe landmark indices: 15=left_wrist, 16=right_wrist, 23=left_hip, 24=right_hip
            left_wrist = best_landmarks[15]
            right_wrist = best_landmarks[16]
            left_hip = best_landmarks[23]
            right_hip = best_landmarks[24]
            hip_cx = (left_hip.x + right_hip.x) / 2
            hip_cy = (left_hip.y + right_hip.y) / 2
            dominant_wrist = (
                right_wrist if right_wrist.visibility >= left_wrist.visibility else left_wrist
            )

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

    landmarker.close()
    return updated
