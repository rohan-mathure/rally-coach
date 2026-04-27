import numpy as np
import cv2
from pipeline.utils.court_constants import ITF_CORNERS_FEET


class CourtHomography:
    def __init__(self, H: np.ndarray):
        self.H = H
        self.H_inv = np.linalg.inv(H)

    def pixel_to_court(self, px: float, py: float) -> tuple[float, float]:
        pt = np.array([[[px, py]]], dtype=np.float32)
        result = cv2.perspectiveTransform(pt, self.H)
        return float(result[0, 0, 0]), float(result[0, 0, 1])

    def court_to_pixel(self, cx: float, cy: float) -> tuple[float, float]:
        pt = np.array([[[cx, cy]]], dtype=np.float32)
        result = cv2.perspectiveTransform(pt, self.H_inv)
        return float(result[0, 0, 0]), float(result[0, 0, 1])

    def to_list(self) -> list[list[float]]:
        return self.H.tolist()

    @classmethod
    def from_list(cls, matrix: list[list[float]]) -> "CourtHomography":
        return cls(np.array(matrix, dtype=np.float64))
