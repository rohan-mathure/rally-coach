import subprocess
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from pipeline.stages.annotator import _try_reencode_h264, annotate_video

# ---------------------------------------------------------------------------
# _try_reencode_h264
# ---------------------------------------------------------------------------

def test_reencode_success_replaces_original(tmp_path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"original")
    tmp_encoded = tmp_path / "video.tmp.mp4"

    def _fake_run(cmd, **kwargs):
        tmp_encoded.write_bytes(b"h264encoded")

    with patch("pipeline.stages.annotator.subprocess.run", side_effect=_fake_run):
        _try_reencode_h264(src)

    assert src.read_bytes() == b"h264encoded"
    assert not tmp_encoded.exists()


def test_reencode_ffmpeg_not_found_keeps_original(tmp_path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"original")

    with patch("pipeline.stages.annotator.subprocess.run", side_effect=FileNotFoundError):
        _try_reencode_h264(src)

    assert src.read_bytes() == b"original"
    assert not (tmp_path / "video.tmp.mp4").exists()


def test_reencode_ffmpeg_error_keeps_original(tmp_path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"original")

    with patch(
        "pipeline.stages.annotator.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "ffmpeg"),
    ):
        _try_reencode_h264(src)

    assert src.read_bytes() == b"original"


def test_reencode_cleans_up_tmp_on_error(tmp_path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"original")
    tmp_encoded = tmp_path / "video.tmp.mp4"
    tmp_encoded.write_bytes(b"partial")

    with patch(
        "pipeline.stages.annotator.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "ffmpeg"),
    ):
        _try_reencode_h264(src)

    assert not tmp_encoded.exists()


def test_reencode_passes_correct_ffmpeg_args(tmp_path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"x")
    tmp_encoded = tmp_path / "video.tmp.mp4"

    captured = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        tmp_encoded.write_bytes(b"x")

    with patch("pipeline.stages.annotator.subprocess.run", side_effect=_fake_run):
        _try_reencode_h264(src)

    cmd = captured["cmd"]
    assert cmd[0] == "ffmpeg"
    assert str(src) in cmd
    assert str(tmp_encoded) in cmd
    assert "libx264" in cmd


# ---------------------------------------------------------------------------
# annotate_video — codec and temp-file behaviour
# ---------------------------------------------------------------------------

def _make_mock_cap(width=320, height=240, frames=0):
    """Return a mocked cv2.VideoCapture that yields `frames` blank frames."""
    cap = MagicMock()

    def _get(prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: width, cv2.CAP_PROP_FRAME_HEIGHT: height}.get(prop, 0)

    cap.get.side_effect = _get
    blank = np.zeros((height, width, 3), dtype=np.uint8)
    cap.read.side_effect = [(True, blank)] * frames + [(False, None)]
    return cap


def test_annotate_video_writes_to_mp4_path_not_avi(tmp_path):
    output = tmp_path / "out.mp4"

    with patch("pipeline.stages.annotator.cv2.VideoCapture", return_value=_make_mock_cap()) as _, \
         patch("pipeline.stages.annotator.cv2.VideoWriter") as mock_writer_cls, \
         patch("pipeline.stages.annotator.cv2.VideoWriter_fourcc", return_value=0), \
         patch("pipeline.stages.annotator._try_reencode_h264"):

        mock_writer_cls.return_value = MagicMock()
        annotate_video(tmp_path / "in.mp4", output, [], [], None, 30.0)

    written_path = mock_writer_cls.call_args[0][0]
    assert written_path == str(output)
    assert not written_path.endswith(".avi")


def test_annotate_video_uses_mp4v_codec(tmp_path):
    output = tmp_path / "out.mp4"

    with patch("pipeline.stages.annotator.cv2.VideoCapture", return_value=_make_mock_cap()), \
         patch("pipeline.stages.annotator.cv2.VideoWriter") as mock_writer_cls, \
         patch("pipeline.stages.annotator.cv2.VideoWriter_fourcc") as mock_fourcc, \
         patch("pipeline.stages.annotator._try_reencode_h264"):

        mock_writer_cls.return_value = MagicMock()
        mock_fourcc.return_value = 0x7634706D
        annotate_video(tmp_path / "in.mp4", output, [], [], None, 30.0)

    mock_fourcc.assert_called_once_with(*"mp4v")


def test_annotate_video_no_avi_temp_file_created(tmp_path):
    output = tmp_path / "out.mp4"

    with patch("pipeline.stages.annotator.cv2.VideoCapture", return_value=_make_mock_cap()), \
         patch("pipeline.stages.annotator.cv2.VideoWriter", return_value=MagicMock()), \
         patch("pipeline.stages.annotator.cv2.VideoWriter_fourcc", return_value=0), \
         patch("pipeline.stages.annotator._try_reencode_h264"):

        annotate_video(tmp_path / "in.mp4", output, [], [], None, 30.0)

    assert not (tmp_path / "out.avi").exists()


def test_annotate_video_calls_try_reencode(tmp_path):
    output = tmp_path / "out.mp4"

    with patch("pipeline.stages.annotator.cv2.VideoCapture", return_value=_make_mock_cap()), \
         patch("pipeline.stages.annotator.cv2.VideoWriter", return_value=MagicMock()), \
         patch("pipeline.stages.annotator.cv2.VideoWriter_fourcc", return_value=0), \
         patch("pipeline.stages.annotator._try_reencode_h264") as mock_encode:

        annotate_video(tmp_path / "in.mp4", output, [], [], None, 30.0)

    mock_encode.assert_called_once_with(output)
