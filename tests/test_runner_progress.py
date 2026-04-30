from unittest.mock import patch

import numpy as np

from pipeline.runner import _with_progress


def _fake_frames(n: int):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    return ((i, frame) for i in range(n))


def test_with_progress_yields_all_frames():
    result = list(_with_progress(_fake_frames(50), total=50, label="test"))
    assert len(result) == 50
    assert [idx for idx, _ in result] == list(range(50))


def test_with_progress_logs_at_10pct_intervals():
    with patch("pipeline.runner.logger") as mock_logger:
        list(_with_progress(_fake_frames(100), total=100, label="test"))
    calls = [call.args[0] for call in mock_logger.info.call_args_list]
    logged_frames = []
    for msg in calls:
        if msg.startswith("test: frame"):
            parts = msg.split()
            logged_frames.append(int(parts[2].split("/")[0]))
    assert logged_frames == list(range(10, 100, 10))


def test_with_progress_no_log_for_single_frame():
    with patch("pipeline.runner.logger") as mock_logger:
        list(_with_progress(_fake_frames(1), total=1, label="test"))
    progress_calls = [
        c for c in mock_logger.info.call_args_list if "frame" in (c.args[0] if c.args else "")
    ]
    assert len(progress_calls) == 0


def test_with_progress_label_appears_in_message():
    with patch("pipeline.runner.logger") as mock_logger:
        list(_with_progress(_fake_frames(100), total=100, label="Ball tracking"))
    calls = [call.args[0] for call in mock_logger.info.call_args_list]
    progress_calls = [m for m in calls if m.startswith("Ball tracking:")]
    assert len(progress_calls) > 0


def test_with_progress_empty_generator():
    with patch("pipeline.runner.logger"):
        result = list(_with_progress(_fake_frames(0), total=0, label="test"))
    assert result == []
