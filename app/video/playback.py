"""Playback timing and play/pause state for a video.

This module is deliberately free of Qt. :class:`PlaybackController` decides
*whether* playback is running and *how fast* frames should advance; it does
not own a timer and it does not read frames. The UI runs a ``QTimer`` at
:attr:`PlaybackController.frame_interval_ms` and asks the project controller
to advance on each tick.

Keeping this Qt-free reserves a clean seam: a future threaded / buffered
implementation can expose the same interface without changing callers.
"""

_DEFAULT_FPS = 30.0


class PlaybackController:
    """Track play/pause state and the frame interval derived from the FPS."""

    def __init__(self, fps: float) -> None:
        self._fps = fps if fps > 0 else _DEFAULT_FPS
        self._is_playing = False

    @property
    def is_playing(self) -> bool:
        """Return whether playback is currently running."""

        return self._is_playing

    @property
    def frame_interval_ms(self) -> int:
        """Return the delay between frames in milliseconds (at least 1)."""

        return max(1, round(1000.0 / self._fps))

    def play(self) -> None:
        """Start playback."""

        self._is_playing = True

    def pause(self) -> None:
        """Pause playback."""

        self._is_playing = False
