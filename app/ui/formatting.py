"""Helpers that turn domain objects into display strings for the UI."""

from app.video.video_loader import VideoMetadata


def format_video_summary(metadata: VideoMetadata) -> str:
    """Return a human-readable, one-item-per-line summary of a video.

    Args:
        metadata: The video metadata to describe.

    Returns:
        A multi-line string listing file name, path, resolution, frame
        rate, frame count and duration.
    """

    return "\n".join(
        (
            f"File: {metadata.path.name}",
            f"Path: {metadata.path}",
            f"Resolution: {metadata.width} x {metadata.height}",
            f"Frame rate: {metadata.fps:.2f} fps",
            f"Frames: {metadata.frame_count}",
            f"Duration: {metadata.duration_seconds:.2f} s",
        )
    )


def format_video_line(metadata: VideoMetadata) -> str:
    """Return a compact, single-line summary of a video for a header label.

    Args:
        metadata: The video metadata to describe.

    Returns:
        One line: file name, resolution, frame rate, frame count and
        duration, separated by middots.
    """

    return "  ·  ".join(
        (
            metadata.path.name,
            f"{metadata.width}×{metadata.height}",
            f"{metadata.fps:.0f} fps",
            f"{metadata.frame_count} frames",
            f"{metadata.duration_seconds:.2f} s",
        )
    )
