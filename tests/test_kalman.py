from pipeline.models.kalman import KalmanBallTracker


def test_init_and_update():
    tracker = KalmanBallTracker(fps=60.0)
    assert not tracker.is_initialized

    x, y, vx, vy = tracker.update(100.0, 200.0)
    assert tracker.is_initialized
    assert abs(x - 100.0) < 5
    assert abs(y - 200.0) < 5


def test_prediction_after_gap():
    tracker = KalmanBallTracker(fps=60.0)
    tracker.update(100.0, 100.0)
    tracker.update(110.0, 105.0)

    # Predict a few frames
    for _ in range(5):
        x, y, vx, vy = tracker.predict()

    assert tracker.consecutive_misses == 5
    # Kalman velocity estimate converges slowly from 2 samples.
    # Assert direction is correct (positive vx) and position advanced from start.
    assert vx > 0
    assert x > 100.0
