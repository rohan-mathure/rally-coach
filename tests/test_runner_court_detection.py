"""Tests for _pick_best_homography — the multi-frame court detection helper."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pipeline.runner import _COURT_EARLY_EXIT_RATIO, _pick_best_homography


def _fake_reader(frame_map: dict[int, np.ndarray | None]):
    """Return a context-manager VideoReader mock that serves frames from frame_map."""
    reader = MagicMock()
    reader.read_frame.side_effect = lambda idx: frame_map.get(idx, None)
    reader.__enter__ = lambda s: reader
    reader.__exit__ = MagicMock(return_value=False)
    return reader


def _dummy_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


class TestPickBestHomography:
    def test_returns_none_when_all_ratios_below_threshold(self):
        """If every sampled frame has inlier_ratio < 0.6 → (None, best_ratio)."""
        frame = _dummy_frame()
        fake_h = MagicMock()

        with patch("pipeline.runner.VideoReader", return_value=_fake_reader({i: frame for i in range(1000)})), \
             patch("pipeline.runner.detect_court", return_value=(fake_h, 0.3, frame)):
            h, ratio = _pick_best_homography(Path("/fake.mp4"), total_frames=1000)

        assert h is None
        assert ratio == pytest.approx(0.3)

    def test_returns_homography_when_ratio_above_threshold(self):
        """If any frame yields ratio >= 0.6 the homography is returned."""
        frame = _dummy_frame()
        fake_h = MagicMock()

        with patch("pipeline.runner.VideoReader", return_value=_fake_reader({i: frame for i in range(1000)})), \
             patch("pipeline.runner.detect_court", return_value=(fake_h, 0.75, frame)):
            h, ratio = _pick_best_homography(Path("/fake.mp4"), total_frames=1000)

        assert h is fake_h
        assert ratio == pytest.approx(0.75)

    def test_best_ratio_wins_across_frames(self):
        """The frame with the highest inlier_ratio determines the returned homography."""
        frame = _dummy_frame()
        weak_h = MagicMock(name="weak")
        strong_h = MagicMock(name="strong")

        call_count = 0

        def _detect(f):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (weak_h, 0.65, frame)   # first frame: acceptable but weak
            return (strong_h, 0.85, frame)      # subsequent frames: better

        with patch("pipeline.runner.VideoReader", return_value=_fake_reader({i: frame for i in range(1000)})), \
             patch("pipeline.runner.detect_court", side_effect=_detect):
            h, ratio = _pick_best_homography(Path("/fake.mp4"), total_frames=1000)

        assert h is strong_h
        assert ratio == pytest.approx(0.85)

    def test_early_exit_when_ratio_exceeds_threshold(self):
        """Stops sampling once inlier_ratio >= _COURT_EARLY_EXIT_RATIO (0.9)."""
        frame = _dummy_frame()
        fake_h = MagicMock()
        detect_calls = []

        def _detect(f):
            detect_calls.append(f)
            return (fake_h, 0.95, frame)  # always excellent

        with patch("pipeline.runner.VideoReader", return_value=_fake_reader({i: frame for i in range(1000)})), \
             patch("pipeline.runner.detect_court", side_effect=_detect):
            h, ratio = _pick_best_homography(Path("/fake.mp4"), total_frames=1000)

        # Should stop after the first successful frame
        assert len(detect_calls) == 1
        assert ratio >= _COURT_EARLY_EXIT_RATIO

    def test_skips_unreadable_frames_gracefully(self):
        """Frames that return None (unreadable) are silently skipped."""
        frame = _dummy_frame()
        fake_h = MagicMock()
        # Only frame 60 is readable; all others return None
        reader = _fake_reader({60: frame})

        with patch("pipeline.runner.VideoReader", return_value=reader), \
             patch("pipeline.runner.detect_court", return_value=(fake_h, 0.8, frame)):
            h, ratio = _pick_best_homography(Path("/fake.mp4"), total_frames=1000)

        assert h is fake_h

    def test_deduplicates_sample_frame_numbers(self):
        """When total_frames produces duplicate sample indices they are tried only once."""
        frame = _dummy_frame()
        fake_h = MagicMock()
        read_calls: list[int] = []

        reader = MagicMock()
        # Track which frame numbers were requested
        reader.read_frame.side_effect = lambda idx: (read_calls.append(idx), frame)[1]
        reader.__enter__ = lambda s: reader
        reader.__exit__ = MagicMock(return_value=False)

        with patch("pipeline.runner.VideoReader", return_value=reader), \
             patch("pipeline.runner.detect_court", return_value=(fake_h, 0.5, frame)):
            # total_frames=600 → [30, 0, 60, 120, 300, 30, 60] → deduped → 5 unique
            _pick_best_homography(Path("/fake.mp4"), total_frames=600)

        assert len(read_calls) == len(set(read_calls)), "Each frame number should be read at most once"


# ---------------------------------------------------------------------------
# Integration test — real fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fixture_video():
    p = Path(__file__).parent / "fixtures" / "sample_tennis.mp4"
    if not p.exists():
        pytest.skip("sample_tennis.mp4 not present — run scripts/create_fixture.sh")
    return p


def test_pick_best_homography_on_real_video(fixture_video):
    h, ratio = _pick_best_homography(fixture_video, total_frames=18000)
    assert isinstance(ratio, float)
    assert 0.0 <= ratio <= 1.0
    # The function must not raise regardless of detection success
