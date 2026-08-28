"""Background sequential frame decoding into a bounded buffer.

Qt-free. Sits behind ``ProjectController.advance_playback``: during
playback the controller pulls frames from a :class:`FrameStream` instead
of decoding on the UI thread. The stream owns its own :class:`FrameReader`
(a ``cv2.VideoCapture`` must not be shared between threads).
"""

import queue
import threading
from types import TracebackType
from typing import Self

import numpy as np

from app.video.frame_reader import FrameReader

_END = object()


class FrameStream:
    """Decodes frames sequentially on a worker thread into a bounded queue."""

    def __init__(
        self,
        frame_reader: FrameReader,
        start_index: int,
        buffer_size: int = 30,
    ) -> None:
        self._reader = frame_reader
        self._queue: queue.Queue = queue.Queue(maxsize=max(1, buffer_size))
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._produce, args=(start_index,), daemon=True
        )
        self._thread.start()

    def next_frame(self, timeout: float = 1.0) -> tuple[int, np.ndarray] | None:
        """Return the next ``(index, frame)``, or ``None`` at end of video.

        Blocks up to ``timeout`` seconds waiting for the decoder.
        """

        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

        return None if item is _END else item

    def close(self) -> None:
        """Stop the worker thread and release the reader."""

        self._stop.set()
        try:  # unblock a producer waiting on a full queue
            self._queue.get_nowait()
        except queue.Empty:
            pass
        self._thread.join(timeout=1.0)
        self._reader.close()

    def _produce(self, start_index: int) -> None:
        index = start_index

        while not self._stop.is_set():
            try:
                frame = self._reader.read_frame(index)
            except (IndexError, RuntimeError):
                break

            while not self._stop.is_set():
                try:
                    self._queue.put((index, frame), timeout=0.2)
                    break
                except queue.Full:
                    continue
            index += 1

        try:
            self._queue.put(_END, timeout=0.2)
        except queue.Full:
            pass

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
