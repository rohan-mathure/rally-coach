import math

import numpy as np

from app.models.shot import Shot

# Magnus effect constants (tennis ball)
BALL_MASS_KG = 0.057
BALL_RADIUS_M = 0.033
AIR_DENSITY = 1.2        # kg/m³
LIFT_COEFFICIENT = 0.5   # C_L for tennis ball (empirical)

TOPSPIN_THRESHOLD = -0.15
UNDERSPIN_THRESHOLD = 0.15
MIN_SPEED_MPH = 30.0     # don't attempt spin below this speed
MIN_TRAJ_POINTS = 8


def _mph_to_ms(mph: float) -> float:
    return mph * 0.44704


def analyze_spin(shots: list[Shot], fps: float) -> list[Shot]:
    updated = []
    for shot in shots:
        traj = shot.trajectory
        if len(traj) < MIN_TRAJ_POINTS:
            updated.append(shot)
            continue

        if shot.speed_mph is not None and shot.speed_mph < MIN_SPEED_MPH:
            updated.append(shot.model_copy(update={"spin_type": "unknown", "spin_confidence": 0.0}))
            continue

        xs = np.array([p.x for p in traj])
        ys = np.array([p.y for p in traj])
        ts = np.array([p.frame_idx / fps for p in traj])
        ts = ts - ts[0]   # normalize to start at 0

        # Fit parabola to y vs t (gravity baseline)
        try:
            coeffs = np.polyfit(ts, ys, 2)
            y_fit = np.polyval(coeffs, ts)
            residuals = ys - y_fit
        except np.linalg.LinAlgError:
            updated.append(shot)
            continue

        traj_length = math.hypot(xs[-1] - xs[0], ys[-1] - ys[0])
        if traj_length < 1e-3:
            updated.append(shot)
            continue

        curvature_score = float(np.mean(residuals)) / traj_length

        # Classify spin
        if curvature_score < TOPSPIN_THRESHOLD:
            spin_type = "topspin"
            spin_conf = min(0.95, 0.5 + abs(curvature_score) * 2)
        elif curvature_score > UNDERSPIN_THRESHOLD:
            spin_type = "underspin"
            spin_conf = min(0.95, 0.5 + abs(curvature_score) * 2)
        else:
            spin_type = "flat"
            spin_conf = 0.7

        # RPM estimate via Magnus model
        rpm_estimate = None
        if shot.speed_mph is not None and shot.speed_mph >= MIN_SPEED_MPH:
            v_ms = _mph_to_ms(shot.speed_mph)
            # Approximate Magnus force from vertical curvature deviation
            # F = m * Δa where Δa is the extra vertical acceleration
            delta_a = 2 * coeffs[0] / (fps ** 2)  # second derivative of parabola → px/s²
            # Convert px acceleration to m/s² using a rough scale (ball at ~39ft = 12m)
            # This is very approximate; scale calibration improves accuracy
            scale_rough = 12.0 / max(abs(ys[-1] - ys[0]), 50)
            f_magnus = abs(delta_a * scale_rough * BALL_MASS_KG)
            denom = LIFT_COEFFICIENT * AIR_DENSITY * math.pi * BALL_RADIUS_M**2 * v_ms
            if denom > 1e-6:
                omega = f_magnus / denom
                rpm_estimate = omega * 60 / (2 * math.pi)
                rpm_estimate = max(0.0, min(rpm_estimate, 8000.0))  # physical bounds

        updated.append(shot.model_copy(update={
            "spin_type": spin_type,
            "spin_confidence": spin_conf,
            "curvature_score": curvature_score,
            "rpm_estimate": rpm_estimate,
        }))

    return updated
