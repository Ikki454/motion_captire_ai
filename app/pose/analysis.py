"""Run a pose detector over every frame of a video."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.models.pose_sequence import PersonTrack, PoseSequence
from app.pose.detector_base import PoseDetector
from app.pose.mapping import to_canonical
from app.video.frame_reader import FrameReader
from app.video.video_loader import VideoMetadata

_ACTIVE_TRACK_ID = "person_0"

ProgressCallback = Callable[[int, int], None]
CancelPredicate = Callable[[], bool]
DetectorFactory = Callable[[], PoseDetector]


def analyze_video(
    frame_reader: FrameReader,
    detector: PoseDetector,
    metadata: VideoMetadata,
    *,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelPredicate | None = None,
) -> PoseSequence:
    """Detect a pose in every frame and return the resulting sequence.

    Single-threaded. Frames with no detection are simply absent from the
    track (an explicit gap). If ``should_cancel`` starts returning
    ``True``, the partial sequence built so far is returned.
    """

    total = max(0, metadata.frame_count)
    fps = metadata.fps if metadata.fps > 0 else 0.0
    track = PersonTrack(track_id=_ACTIVE_TRACK_ID)
    counter = _Progress(total, on_progress)

    _detect_range(
        frame_reader, detector, track, threading.Lock(), (0, total), fps,
        counter, should_cancel,
    )

    return _sequence(metadata, total, track)


def analyze_video_parallel(
    video_path: Path,
    detector_factory: DetectorFactory,
    metadata: VideoMetadata,
    *,
    workers: int = 1,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelPredicate | None = None,
) -> PoseSequence:
    """Detect a pose in every frame, spreading the work over ``workers`` threads.

    Each worker opens its own :class:`FrameReader` and detector (built by
    ``detector_factory``) and handles a contiguous frame range; the results
    are merged into one track. Behaviour is identical to :func:`analyze_video`
    for ``workers == 1``.
    """

    total = max(0, metadata.frame_count)
    fps = metadata.fps if metadata.fps > 0 else 0.0
    worker_count = max(1, min(workers, total)) if total else 1

    track = PersonTrack(track_id=_ACTIVE_TRACK_ID)
    lock = threading.Lock()
    counter = _Progress(total, on_progress)

    def run_chunk(bounds: tuple[int, int]) -> None:
        reader = FrameReader(video_path)
        detector = detector_factory()
        try:
            _detect_range(
                reader, detector, track, lock, bounds, fps, counter, should_cancel
            )
        finally:
            detector.close()
            reader.close()

    chunks = _split_range(total, worker_count)

    if worker_count == 1:
        run_chunk(chunks[0])
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            list(pool.map(run_chunk, chunks))

    return _sequence(metadata, total, track)


def _detect_range(
    reader: FrameReader,
    detector: PoseDetector,
    track: PersonTrack,
    lock: threading.Lock,
    bounds: tuple[int, int],
    fps: float,
    counter: "_Progress",
    should_cancel: CancelPredicate | None,
) -> None:
    start, end = bounds

    for index in range(start, end):
        if should_cancel is not None and should_cancel():
            return

        frame = reader.read_frame(index)
        timestamp = index / fps if fps > 0 else 0.0
        raw = detector.detect(frame, index, timestamp)

        if raw is not None:
            with lock:
                track.raw_frames[index] = raw
                track.frames[index] = to_canonical(raw)
                if raw.depth_source != "none":
                    track.depth_source = raw.depth_source

        counter.tick()


def _split_range(total: int, parts: int) -> list[tuple[int, int]]:
    if total <= 0:
        return [(0, 0)]
    size, remainder = divmod(total, parts)
    bounds: list[tuple[int, int]] = []
    start = 0
    for part in range(parts):
        length = size + (1 if part < remainder else 0)
        bounds.append((start, start + length))
        start += length
    return bounds


def _sequence(
    metadata: VideoMetadata, total: int, track: PersonTrack
) -> PoseSequence:
    sequence = PoseSequence(
        video_path=metadata.path,
        frame_count=total,
        fps=metadata.fps,
        width=metadata.width,
        height=metadata.height,
    )
    sequence.add_track(track, make_active=True)
    return sequence


class _Progress:
    """Thread-safe progress counter."""

    def __init__(self, total: int, callback: ProgressCallback | None) -> None:
        self._total = total
        self._callback = callback
        self._done = 0
        self._lock = threading.Lock()

    def tick(self) -> None:
        if self._callback is None:
            return
        with self._lock:
            self._done += 1
            done = self._done
        self._callback(done, self._total)
