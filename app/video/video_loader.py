from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass(frozen=True)
class VideoMetadata:
    """Metadata describing a video file."""

    path: Path
    frame_count: int
    fps: float
    width: int
    height: int

    @property
    def duration_seconds(self) -> float:
        """Return video duration in seconds."""

        if self.fps <= 0:
            return 0.0

        return self.frame_count / self.fps


class VideoLoader:
    """Load video files and extract metadata."""

    def load_metadata(
        self,
        video_path: str | Path,
    ) -> VideoMetadata:

        path = Path(video_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Video file does not exist: {path}"
            )

        capture = cv2.VideoCapture(str(path))

        if not capture.isOpened():
            raise RuntimeError(
                f"Unable to open video: {path}"
            )

        try:
            frame_count = int(
                capture.get(cv2.CAP_PROP_FRAME_COUNT)
            )

            fps = float(
                capture.get(cv2.CAP_PROP_FPS)
            )

            width = int(
                capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            )

            height = int(
                capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            )

            return VideoMetadata(
                path=path,
                frame_count=frame_count,
                fps=fps,
                width=width,
                height=height,
            )

        finally:
            capture.release()