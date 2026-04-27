import numpy as np
from filterpy.kalman import KalmanFilter


class KalmanBallTracker:
    """Constant-velocity Kalman filter tracking [x, y, vx, vy]."""

    def __init__(self, fps: float = 60.0):
        dt = 1.0 / fps
        self.kf = KalmanFilter(dim_x=4, dim_z=2)

        # State transition: x' = x + vx*dt, y' = y + vy*dt
        self.kf.F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1,  0],
            [0, 0, 0,  1],
        ], dtype=float)

        # Measurement: observe (x, y) only
        self.kf.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=float)

        self.kf.R *= 10        # measurement noise
        self.kf.Q *= 0.1       # process noise — trust model more than measurements
        self.kf.P *= 500       # initial uncertainty

        self._initialized = False
        self.consecutive_misses = 0

    def update(self, x: float, y: float) -> tuple[float, float, float, float]:
        """Feed a detection; return (x, y, vx, vy)."""
        if not self._initialized:
            self.kf.x = np.array([[x], [y], [0], [0]], dtype=float)
            self._initialized = True

        self.kf.predict()
        self.kf.update(np.array([[x], [y]]))
        self.consecutive_misses = 0
        return self._state()

    def predict(self) -> tuple[float, float, float, float]:
        """Advance one frame with no detection."""
        if not self._initialized:
            return (0.0, 0.0, 0.0, 0.0)
        self.kf.predict()
        self.consecutive_misses += 1
        return self._state()

    def _state(self) -> tuple[float, float, float, float]:
        s = self.kf.x.flatten()
        return float(s[0]), float(s[1]), float(s[2]), float(s[3])

    @property
    def is_initialized(self) -> bool:
        return self._initialized
