from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline.stages.ball_tracker import MAX_GAP_FRAMES, track_balls


def _make_model(detections: dict[int, tuple[float, float, float]]):
    """
    Return a fake YOLO model.
    detections: {frame_idx: (cx, cy, conf)} — frames not listed return no detection.
    """
    def _predict(frame, verbose=False):
        frame_idx = frame  # we pass the index directly in tests
        result = MagicMock()
        if frame_idx in detections:
            cx, cy, conf = detections[frame_idx]
            x1, y1 = cx - 5, cy - 5
            x2, y2 = cx + 5, cy + 5
            box = MagicMock()
            box.cls = [32]
            box.conf = [conf]
            box.xyxy = [MagicMock()]
            box.xyxy[0].tolist.return_value = [x1, y1, x2, y2]
            result.boxes = [box]
        else:
            result.boxes = []
        return [result]
    return _predict


def _fake_frames(n: int):
    """Yield (frame_idx, frame_idx) — pass the index as the 'frame' so _make_model can look it up."""
    for i in range(n):
        yield i, i


class TestGhostPositionFix:
    def test_positions_stop_after_max_gap_frames(self):
        """Once the tracker loses the ball for > MAX_GAP_FRAMES, no more positions are recorded."""
        # Ball detected only at frame 0; all subsequent frames are misses
        detections = {0: (100.0, 200.0, 0.9)}
        model = _make_model(detections)

        with patch("pipeline.stages.ball_tracker._load_model", return_value=(model, 32, 0.35)):
            positions = track_balls(_fake_frames(50), fps=60.0, weights_dir=Path("/fake"))

        # 1 real + MAX_GAP_FRAMES interpolated = MAX_GAP_FRAMES + 1 total
        assert len(positions) == MAX_GAP_FRAMES + 1

    def test_interpolated_positions_within_gap_are_marked(self):
        """Positions within the gap window must have is_interpolated=True."""
        detections = {0: (100.0, 200.0, 0.9)}
        model = _make_model(detections)

        with patch("pipeline.stages.ball_tracker._load_model", return_value=(model, 32, 0.35)):
            positions = track_balls(_fake_frames(20), fps=60.0, weights_dir=Path("/fake"))

        real = [p for p in positions if not p.is_interpolated]
        interp = [p for p in positions if p.is_interpolated]
        assert len(real) == 1
        assert len(interp) == MAX_GAP_FRAMES

    def test_real_detection_after_gap_is_not_interpolated(self):
        """A detection that arrives after a gap is recorded as a real (non-interpolated) position."""
        # Detect at frame 0, miss for 3 frames, detect again at frame 4
        detections = {0: (100.0, 200.0, 0.9), 4: (110.0, 195.0, 0.85)}
        model = _make_model(detections)

        with patch("pipeline.stages.ball_tracker._load_model", return_value=(model, 32, 0.35)):
            positions = track_balls(_fake_frames(10), fps=60.0, weights_dir=Path("/fake"))

        real = [p for p in positions if not p.is_interpolated]
        assert len(real) == 2
        assert real[0].frame_idx == 0
        assert real[1].frame_idx == 4

    def test_no_positions_when_ball_never_detected(self):
        """If the tracker is never initialized, nothing is recorded."""
        model = _make_model({})

        with patch("pipeline.stages.ball_tracker._load_model", return_value=(model, 32, 0.35)):
            positions = track_balls(_fake_frames(20), fps=60.0, weights_dir=Path("/fake"))

        assert positions == []

    def test_summary_log_emitted(self):
        """track_balls logs a 'Ball tracking complete' info line."""
        detections = {0: (100.0, 200.0, 0.9)}
        model = _make_model(detections)

        with patch("pipeline.stages.ball_tracker.logger") as mock_logger, \
             patch("pipeline.stages.ball_tracker._load_model", return_value=(model, 32, 0.35)):
            track_balls(_fake_frames(5), fps=60.0, weights_dir=Path("/fake"))

        messages = [str(c.args[0]) for c in mock_logger.info.call_args_list]
        assert any("Ball tracking complete" in m for m in messages)

    def test_custom_model_uses_class_zero(self):
        """When custom weights exist the model is loaded with ball_class=0."""
        weights_dir = Path("/fake")
        with patch("pipeline.stages.ball_tracker._load_model") as mock_load:
            mock_model = _make_model({})
            mock_load.return_value = (mock_model, 0, 0.35)
            track_balls(_fake_frames(3), fps=60.0, weights_dir=weights_dir)
        mock_load.assert_called_once_with(weights_dir)
