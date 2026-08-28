"""Tests for UI formatting helpers."""

from pathlib import Path

from app.ui.formatting import format_video_line, format_video_summary
from app.video.video_loader import VideoMetadata

_METADATA = VideoMetadata(
    path=Path("/videos/run.mp4"),
    frame_count=300,
    fps=30.0,
    width=1920,
    height=1080,
)


def test_format_video_summary_includes_key_fields() -> None:
    summary = format_video_summary(_METADATA)

    assert "run.mp4" in summary
    assert "1920 x 1080" in summary
    assert "30.00 fps" in summary
    assert "Frames: 300" in summary
    assert "10.00 s" in summary


def test_format_video_line_is_a_single_compact_line() -> None:
    line = format_video_line(_METADATA)

    assert "\n" not in line
    assert "run.mp4" in line
    assert "1920×1080" in line
    assert "30 fps" in line
    assert "300 frames" in line
    assert "10.00 s" in line
