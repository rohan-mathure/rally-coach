import math
from unittest.mock import patch

import numpy as np
import pytest

from pipeline.stages.court_detector import _cluster_lines, _deduplicate_lines, detect_court

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_line(angle_deg: float, length: int = 300) -> np.ndarray:
    """Create a single HoughLinesP result line at the given angle (degrees)."""
    rad = math.radians(angle_deg)
    x2 = int(length * math.cos(rad))
    y2 = int(length * math.sin(rad))
    return np.array([[0, 0, x2, y2]])


def _wrap(lines):
    """Wrap a list of [x1,y1,x2,y2] arrays into the shape HoughLinesP returns."""
    return np.array([[ln] for ln in lines])


# ---------------------------------------------------------------------------
# _cluster_lines — angle thresholds
# ---------------------------------------------------------------------------

class TestClusterLines:
    def test_zero_degrees_is_horizontal(self):
        h, v = _cluster_lines(_wrap([[0, 0, 300, 0]]))
        assert len(h) == 1
        assert len(v) == 0

    def test_180_degrees_is_horizontal(self):
        h, v = _cluster_lines(_wrap([[300, 0, 0, 0]]))
        assert len(h) == 1
        assert len(v) == 0

    def test_24_degrees_is_horizontal(self):
        line = _make_line(24)
        h, v = _cluster_lines(np.array([line]))
        assert len(h) == 1

    def test_90_degrees_is_vertical(self):
        h, v = _cluster_lines(_wrap([[100, 0, 100, 300]]))
        assert len(h) == 0
        assert len(v) == 1

    def test_50_degrees_is_vertical(self):
        line = _make_line(50)
        h, v = _cluster_lines(np.array([line]))
        assert len(v) == 1

    def test_130_degrees_is_vertical(self):
        line = _make_line(130)
        h, v = _cluster_lines(np.array([line]))
        assert len(v) == 1

    def test_35_degrees_is_discarded(self):
        """Angles between 25° and 45° are neither horizontal nor vertical."""
        line = _make_line(35)
        h, v = _cluster_lines(np.array([line]))
        assert len(h) == 0
        assert len(v) == 0

    def test_mixed_lines_split_correctly(self):
        lines = _wrap([
            [0, 0, 300, 0],   # 0° → horizontal
            [0, 0, 0, 300],   # 90° → vertical
            [0, 0, 100, 200], # ~63° → vertical (strictly inside 45–135)
        ])
        h, v = _cluster_lines(lines)
        assert len(h) == 1
        assert len(v) == 2

    def test_exactly_45_degrees_is_discarded(self):
        """The boundary 45° itself is excluded from both groups (strict inequality)."""
        line = _make_line(45)
        h, v = _cluster_lines(np.array([line]))
        assert len(h) == 0
        assert len(v) == 0


# ---------------------------------------------------------------------------
# _deduplicate_lines
# ---------------------------------------------------------------------------

class TestDeduplicateLines:
    def test_empty_input_returns_empty(self):
        assert _deduplicate_lines([]) == []

    def test_single_line_returned_unchanged(self):
        line = [0, 0, 300, 0]
        result = _deduplicate_lines([line])
        assert result == [line]

    def test_nearby_lines_merged_to_one(self):
        """Two lines whose midpoints are within 20px should collapse to one."""
        line_a = [0, 100, 300, 100]
        line_b = [0, 110, 300, 110]  # midpoint 10px away
        result = _deduplicate_lines([line_a, line_b])
        assert len(result) == 1

    def test_distant_lines_both_kept(self):
        line_a = [0, 100, 300, 100]
        line_b = [0, 200, 300, 200]  # midpoint 100px away
        result = _deduplicate_lines([line_a, line_b])
        assert len(result) == 2

    def test_custom_threshold_respected(self):
        line_a = [0, 100, 300, 100]
        line_b = [0, 130, 300, 130]  # 30px apart
        # With threshold=20 → kept separately; threshold=40 → merged
        assert len(_deduplicate_lines([line_a, line_b], threshold_px=20)) == 2
        assert len(_deduplicate_lines([line_a, line_b], threshold_px=40)) == 1


# ---------------------------------------------------------------------------
# detect_court — unit (mocked cv2)
# ---------------------------------------------------------------------------

class TestDetectCourtUnit:
    def test_returns_none_when_no_lines_found(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with patch("pipeline.stages.court_detector.cv2.HoughLinesP", return_value=None):
            h, ratio, _ = detect_court(frame)
        assert h is None
        assert ratio == 0.0

    def test_returns_none_when_too_few_lines(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Only 2 lines — below minimum of 4
        fake_lines = np.array([[[0, 0, 100, 0]], [[0, 50, 100, 50]]])
        with patch("pipeline.stages.court_detector.cv2.HoughLinesP", return_value=fake_lines):
            h, ratio, _ = detect_court(frame)
        assert h is None
        assert ratio == 0.0

    def test_returns_none_when_only_horizontal_lines(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # 6 horizontal lines, no verticals — insufficient vertical lines
        fake_lines = np.array([
            [[0, y, 640, y]] for y in [50, 100, 150, 200, 250, 300]
        ])
        with patch("pipeline.stages.court_detector.cv2.HoughLinesP", return_value=fake_lines):
            h, ratio, _ = detect_court(frame)
        assert h is None

    def test_diagnostic_frame_always_returned(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with patch("pipeline.stages.court_detector.cv2.HoughLinesP", return_value=None):
            _, _, diag = detect_court(frame)
        assert diag.shape == frame.shape


# ---------------------------------------------------------------------------
# detect_court — integration (real fixture, skipped when unavailable)
# ---------------------------------------------------------------------------

FIXTURE = pytest.importorskip  # marker-style skip defined per test below

@pytest.fixture(scope="module")
def sample_frame():
    fixture = (
        __import__("pathlib").Path(__file__).parent / "fixtures" / "sample_tennis.mp4"
    )
    if not fixture.exists():
        pytest.skip("sample_tennis.mp4 fixture not present — run scripts/create_fixture.sh")
    from pipeline.utils.video_io import VideoReader
    with VideoReader(fixture) as reader:
        frame = reader.read_frame(30)
    if frame is None:
        pytest.skip("Could not read frame 30 from fixture")
    return frame


def test_detect_court_on_real_frame_returns_tuple(sample_frame):
    h, ratio, diag = detect_court(sample_frame)
    # Whatever the result, the function must return the right types
    assert isinstance(ratio, float)
    assert 0.0 <= ratio <= 1.0
    assert diag.shape == sample_frame.shape


def test_detect_court_diagnostic_has_same_shape(sample_frame):
    _, _, diag = detect_court(sample_frame)
    assert diag.shape == sample_frame.shape
