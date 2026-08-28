"""Random-access frame reading for video files."""

from pathlib import Path
from types import TracebackType
from typing import Self

import cv2
import numpy as np


class FrameReader:
    """Read individual frames from a video file by index.

    Frames are returned in OpenCV's native **BGR** channel order as a
    ``numpy.ndarray`` of shape ``(height, width, 3)`` and dtype ``uint8``.

    The underlying video capture stays open until :meth:`close` is called.
    The reader can be used as a context manager to close it automatically.
    """

    def __init__(self, video_path: str | Path) -> None:
        self._path = Path(video_path)

        if not self._path.exists():
            raise FileNotFoundError(f"Video file does not exist: {self._path}")

        self._capture = cv2.VideoCapture(str(self._path))

        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open video: {self._path}")

        self._frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self._next_position = 0

    @property
    def path(self) -> Path:
        """Return the path of the open video file."""

        return self._path

    @property
    def frame_count(self) -> int:
        """Return the number of frames reported by the container.

        May be ``0`` when the container does not expose a reliable count.
        """

        return self._frame_count

    def read_frame(self, index: int) -> np.ndarray:
        """Return the frame at ``index`` (0-based), in BGR order.

        Reading frames in order avoids the (slow) container seek: only a
        non-sequential ``index`` triggers ``CAP_PROP_POS_FRAMES``.

        Args:
            index: Zero-based frame position.

        Returns:
            The decoded frame as a ``(height, width, 3)`` ``uint8`` array.

        Raises:
            IndexError: ``index`` is negative or past the last frame.
            RuntimeError: The frame could not be decoded.
        """

        if index < 0 or (self._frame_count > 0 and index >= self._frame_count):
            raise IndexError(
                f"Frame index {index} out of range [0, {self._frame_count})"
            )

        if index != self._next_position:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, index)

        success, frame = self._capture.read()

        if not success or frame is None:
            self._next_position = -1  # force a seek on the next read
            raise RuntimeError(f"Failed to read frame {index} from {self._path}")

        self._next_position = index + 1
        return frame

    def close(self) -> None:
        """Release the underlying video capture."""

        self._capture.release()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
