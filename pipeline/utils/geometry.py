import numpy as np


def line_intersection(p1, p2, p3, p4):
    """Return intersection point of line (p1,p2) and (p3,p4), or None if parallel."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    """Ray-casting algorithm. polygon is list of [x,y] vertices."""
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_distance_to_segment(point, seg_start, seg_end) -> float:
    """Minimum distance from point to a line segment."""
    p = np.array(point, dtype=float)
    a = np.array(seg_start, dtype=float)
    b = np.array(seg_end, dtype=float)
    ab = b - a
    if np.dot(ab, ab) < 1e-10:
        return float(np.linalg.norm(p - a))
    t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))


def min_distance_to_polygon_boundary(point: tuple, polygon: list[list[float]]) -> float:
    """Minimum distance from point to any edge of the polygon."""
    n = len(polygon)
    min_d = float("inf")
    for i in range(n):
        d = point_distance_to_segment(point, polygon[i], polygon[(i + 1) % n])
        if d < min_d:
            min_d = d
    return min_d
