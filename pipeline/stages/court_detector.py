import math
import numpy as np
import cv2
from loguru import logger

from pipeline.models.homography import CourtHomography
from pipeline.utils.court_constants import ITF_CORNERS_FEET
from pipeline.utils.geometry import line_intersection


def _angle(line) -> float:
    x1, y1, x2, y2 = line
    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def _cluster_lines(lines: np.ndarray) -> tuple[list, list]:
    """Split detected lines into horizontal-ish and vertical-ish groups."""
    horizontal, vertical = [], []
    for line in lines:
        angle = abs(_angle(line[0])) % 180
        if angle < 30 or angle > 150:
            horizontal.append(line[0])
        elif 60 < angle < 120:
            vertical.append(line[0])
    return horizontal, vertical


def _deduplicate_lines(lines: list, threshold_px: int = 20) -> list:
    """Merge lines whose midpoints are within threshold_px of each other."""
    if not lines:
        return []
    kept = [lines[0]]
    for line in lines[1:]:
        x1, y1, x2, y2 = line
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        duplicate = False
        for k in kept:
            kx1, ky1, kx2, ky2 = k
            kmx, kmy = (kx1 + kx2) / 2, (ky1 + ky2) / 2
            if math.hypot(mx - kmx, my - kmy) < threshold_px:
                duplicate = True
                break
        if not duplicate:
            kept.append(line)
    return kept


def detect_court(frame: np.ndarray) -> tuple[CourtHomography | None, float, np.ndarray]:
    """
    Detect court lines in frame and compute homography.
    Returns (homography, inlier_ratio, diagnostic_frame).
    inlier_ratio=0 means detection failed.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=frame.shape[1] // 8,
        maxLineGap=20,
    )

    diagnostic = frame.copy()

    if lines is None or len(lines) < 4:
        logger.warning("Court detection: not enough Hough lines found")
        return None, 0.0, diagnostic

    horizontal, vertical = _cluster_lines(lines)
    horizontal = _deduplicate_lines(
        sorted(horizontal, key=lambda l: (l[1] + l[3]) / 2),
        threshold_px=frame.shape[0] // 20,
    )
    vertical = _deduplicate_lines(
        sorted(vertical, key=lambda l: (l[0] + l[2]) / 2),
        threshold_px=frame.shape[1] // 20,
    )

    logger.debug(f"Court detection: {len(horizontal)} horizontal, {len(vertical)} vertical lines")

    if len(horizontal) < 2 or len(vertical) < 2:
        logger.warning("Court detection: insufficient horizontal or vertical lines")
        return None, 0.0, diagnostic

    # Draw detected lines on diagnostic
    for line in horizontal[:4]:
        cv2.line(diagnostic, (line[0], line[1]), (line[2], line[3]), (0, 255, 0), 2)
    for line in vertical[:4]:
        cv2.line(diagnostic, (line[0], line[1]), (line[2], line[3]), (255, 0, 0), 2)

    # Use outermost horizontal (near/far baselines) and outermost vertical (sidelines)
    h_sorted = sorted(horizontal[:4], key=lambda l: (l[1] + l[3]) / 2)
    v_sorted = sorted(vertical[:4], key=lambda l: (l[0] + l[2]) / 2)

    near_baseline = h_sorted[0]
    far_baseline = h_sorted[-1]
    left_sideline = v_sorted[0]
    right_sideline = v_sorted[-1]

    def to_seg(l):
        return (l[0], l[1]), (l[2], l[3])

    corners = [
        line_intersection(*to_seg(near_baseline), *to_seg(left_sideline)),
        line_intersection(*to_seg(near_baseline), *to_seg(right_sideline)),
        line_intersection(*to_seg(far_baseline), *to_seg(right_sideline)),
        line_intersection(*to_seg(far_baseline), *to_seg(left_sideline)),
    ]

    if any(c is None for c in corners):
        logger.warning("Court detection: could not compute all 4 corner intersections")
        return None, 0.0, diagnostic

    src_pts = np.array([[c[0], c[1]] for c in corners], dtype=np.float32)
    dst_pts = np.array(ITF_CORNERS_FEET, dtype=np.float32)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        logger.warning("Court detection: findHomography failed")
        return None, 0.0, diagnostic

    inlier_ratio = float(mask.sum()) / len(mask) if mask is not None else 0.0

    # Draw corner dots on diagnostic
    for pt in src_pts:
        cv2.circle(diagnostic, (int(pt[0]), int(pt[1])), 8, (0, 0, 255), -1)

    return CourtHomography(H), inlier_ratio, diagnostic
