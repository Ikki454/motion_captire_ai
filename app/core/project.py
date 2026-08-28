from dataclasses import dataclass
from pathlib import Path

from app.video.video_loader import VideoMetadata


@dataclass
class MotionCaptureProject:
    """Represents an AI motion capture project."""

    name: str

    video_metadata: VideoMetadata | None = None

    project_path: Path | None = None