from pathlib import Path

from pipeline.utils.video_io import VideoReader


def extract_metadata(video_path: Path) -> dict:
    with VideoReader(video_path) as reader:
        return {
            "fps": reader.fps,
            "total_frames": reader.total_frames,
            "width": reader.width,
            "height": reader.height,
        }
