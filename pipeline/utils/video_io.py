from pathlib import Path
from typing import Generator
import cv2
import numpy as np


class VideoReader:
    def __init__(self, path: Path):
        self.path = path
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            raise ValueError(f"Cannot open video: {path}")

    @property
    def fps(self) -> float:
        return self._cap.get(cv2.CAP_PROP_FPS)

    @property
    def total_frames(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def width(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def frames(self) -> Generator[tuple[int, np.ndarray], None, None]:
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        idx = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
            yield idx, frame
            idx += 1

    def read_frame(self, frame_idx: int) -> np.ndarray | None:
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        return frame if ret else None

    def read_frame_range(self, start: int, end: int) -> Generator[tuple[int, np.ndarray], None, None]:
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        for idx in range(start, end):
            ret, frame = self._cap.read()
            if not ret:
                break
            yield idx, frame

    def close(self):
        self._cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
