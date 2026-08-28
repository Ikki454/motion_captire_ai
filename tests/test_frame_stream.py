"""Tests for the background frame stream (roadmap Phase 17)."""

import time
from pathlib import Path

from app.video.frame_reader import FrameReader
from app.video.frame_stream import FrameStream


def test_yields_frames_in_order_then_none(sample_video: Path) -> None:
    with FrameStream(FrameReader(sample_video), start_index=0, buffer_size=4) as stream:
        indices = []
        while True:
            item = stream.next_frame(timeout=2.0)
            if item is None:
                break
            index, frame = item
            indices.append(index)
            assert frame.shape[2] == 3

    with FrameReader(sample_video) as reader:
        assert indices == list(range(reader.frame_count))


def test_starts_from_the_requested_index(sample_video: Path) -> None:
    with FrameStream(FrameReader(sample_video), start_index=3) as stream:
        first = stream.next_frame(timeout=2.0)

    assert first is not None
    assert first[0] == 3


def test_close_stops_the_worker_thread(sample_video: Path) -> None:
    stream = FrameStream(FrameReader(sample_video), start_index=0, buffer_size=2)
    stream.next_frame(timeout=2.0)

    stream.close()
    time.sleep(0.05)

    assert not stream._thread.is_alive()


def test_starting_past_the_end_yields_none(sample_video: Path) -> None:
    with FrameReader(sample_video) as reader:
        past_end = reader.frame_count + 10

    with FrameStream(FrameReader(sample_video), start_index=past_end) as stream:
        assert stream.next_frame(timeout=2.0) is None
