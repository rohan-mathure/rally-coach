from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline.stages.pose_analyzer import _get_model

# ---------------------------------------------------------------------------
# _get_model — download logic
# ---------------------------------------------------------------------------

class TestGetModel:
    def test_returns_existing_path_without_downloading(self, tmp_path):
        model = tmp_path / "pose_landmarker_lite.task"
        model.write_bytes(b"fake-model")

        with patch("pipeline.stages.pose_analyzer.urllib.request.urlretrieve") as mock_dl:
            result = _get_model(tmp_path)

        mock_dl.assert_not_called()
        assert result == model

    def test_downloads_when_model_missing(self, tmp_path):
        model = tmp_path / "pose_landmarker_lite.task"

        def _fake_download(url, dest):
            Path(dest).write_bytes(b"downloaded")

        with patch(
            "pipeline.stages.pose_analyzer.urllib.request.urlretrieve",
            side_effect=_fake_download,
        ) as mock_dl:
            result = _get_model(tmp_path)

        mock_dl.assert_called_once()
        assert result == model
        assert model.exists()

    def test_download_url_points_to_mediapipe_storage(self, tmp_path):
        captured = {}

        def _fake_download(url, dest):
            captured["url"] = url
            Path(dest).write_bytes(b"x")

        with patch(
            "pipeline.stages.pose_analyzer.urllib.request.urlretrieve",
            side_effect=_fake_download,
        ):
            _get_model(tmp_path)

        assert "storage.googleapis.com" in captured["url"]
        assert "pose_landmarker" in captured["url"]

    def test_creates_weights_dir_if_missing(self, tmp_path):
        weights_dir = tmp_path / "subdir" / "weights"
        assert not weights_dir.exists()

        def _fake_download(url, dest):
            Path(dest).write_bytes(b"x")

        with patch(
            "pipeline.stages.pose_analyzer.urllib.request.urlretrieve",
            side_effect=_fake_download,
        ):
            _get_model(weights_dir)

        assert weights_dir.exists()


# ---------------------------------------------------------------------------
# extract_poses — graceful degradation
# ---------------------------------------------------------------------------

def _make_shot(**kwargs):
    from app.models.shot import Shot
    defaults = dict(
        shot_id="s1",
        session_id="sess1",
        shot_number=1,
        start_frame=0,
        end_frame=60,
        contact_frame=30,
        start_time_sec=0.5,
        trajectory=[],
        pipeline_warnings=[],
        is_in=True,
        is_close_call=False,
        detection_gap_frames=0,
    )
    defaults.update(kwargs)
    return Shot(**defaults)


class TestExtractPosesGracefulDegradation:
    def test_returns_shots_unchanged_when_mediapipe_unavailable(self):
        from pipeline.stages.pose_analyzer import extract_poses

        shots = [_make_shot()]
        reader = MagicMock()

        with patch("builtins.__import__", side_effect=ImportError("no mediapipe")):
            # The try/except in extract_poses catches this
            pass

        # Simulate the except branch by patching mediapipe import inside the function
        with patch.dict("sys.modules", {"mediapipe": None}):
            result = extract_poses(shots, reader)

        assert result == shots

    def test_adds_pose_low_conf_warning_when_no_landmarks_found(self):
        """When landmarker returns no landmarks for every frame, warning is added."""
        from pipeline.stages.pose_analyzer import extract_poses

        shot = _make_shot()
        reader = MagicMock()
        reader.read_frame_range.return_value = []  # no frames to search

        mock_mp = MagicMock()
        mock_landmarker = MagicMock()
        mock_mp.tasks.vision.PoseLandmarker.create_from_options.return_value = mock_landmarker
        mock_mp.tasks.vision.PoseLandmarkerOptions = MagicMock()
        mock_mp.tasks.BaseOptions = MagicMock()
        mock_mp.tasks.vision.RunningMode.IMAGE = "IMAGE"
        mock_mp.Image = MagicMock()
        mock_mp.ImageFormat.SRGB = "SRGB"

        with patch("pipeline.stages.pose_analyzer._get_model", return_value=Path("/fake/model.task")), \
             patch.dict("sys.modules", {"mediapipe": mock_mp, "cv2": MagicMock()}), \
             patch("app.config.settings", MagicMock(weights_dir=Path("/fake"))):
            result = extract_poses([shot], reader)

        assert len(result) == 1
        assert "pose_low_conf" in result[0].pipeline_warnings

    def test_pose_low_conf_not_duplicated_if_already_present(self):
        """Running extract_poses twice does not duplicate the warning."""
        from pipeline.stages.pose_analyzer import extract_poses

        shot = _make_shot(pipeline_warnings=["pose_low_conf"])
        reader = MagicMock()
        reader.read_frame_range.return_value = []

        mock_mp = MagicMock()
        mock_landmarker = MagicMock()
        mock_mp.tasks.vision.PoseLandmarker.create_from_options.return_value = mock_landmarker
        mock_mp.tasks.vision.PoseLandmarkerOptions = MagicMock()
        mock_mp.tasks.BaseOptions = MagicMock()
        mock_mp.tasks.vision.RunningMode.IMAGE = "IMAGE"
        mock_mp.Image = MagicMock()
        mock_mp.ImageFormat.SRGB = "SRGB"

        with patch("pipeline.stages.pose_analyzer._get_model", return_value=Path("/fake/model.task")), \
             patch.dict("sys.modules", {"mediapipe": mock_mp, "cv2": MagicMock()}), \
             patch("app.config.settings", MagicMock(weights_dir=Path("/fake"))):
            result = extract_poses([shot], reader)

        assert result[0].pipeline_warnings.count("pose_low_conf") == 1
