"""Tests for the Qt-free PlaybackController (roadmap Phase 5)."""

import pytest

from app.video.playback import PlaybackController


def test_starts_paused() -> None:
    controller = PlaybackController(fps=30.0)

    assert controller.is_playing is False


def test_play_and_pause_toggle_state() -> None:
    controller = PlaybackController(fps=30.0)

    controller.play()
    assert controller.is_playing is True

    controller.pause()
    assert controller.is_playing is False


@pytest.mark.parametrize(
    ("fps", "expected_ms"),
    [
        (30.0, 33),
        (25.0, 40),
        (60.0, 17),
        (24.0, 42),
    ],
)
def test_frame_interval_matches_fps(fps: float, expected_ms: int) -> None:
    assert PlaybackController(fps=fps).frame_interval_ms == expected_ms


def test_non_positive_fps_falls_back_to_default() -> None:
    controller = PlaybackController(fps=0.0)

    assert controller.frame_interval_ms == 33  # 30 fps default


def test_frame_interval_is_at_least_one_millisecond() -> None:
    controller = PlaybackController(fps=100_000.0)

    assert controller.frame_interval_ms == 1
