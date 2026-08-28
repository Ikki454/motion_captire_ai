"""Tests for FrameReader random-access frame reading (roadmap Phase 3)."""

from pathlib import Path

import numpy as np
import pytest

from app.video.frame_reader import FrameReader


def test_reads_first_frame_with_expected_shape(sample_video: Path) -> None:
    with FrameReader(sample_video) as reader:
        frame = reader.read_frame(0)

    assert frame.shape == (48, 64, 3)
    assert frame.dtype == np.uint8


def test_reads_distinct_frames_by_index(sample_video: Path) -> None:
    with FrameReader(sample_video) as reader:
        first = reader.read_frame(0)
        later = reader.read_frame(5)

    assert first.shape == later.shape
    assert not np.array_equal(first, later)


def test_sequential_reads_match_seeking_reads(sample_video: Path) -> None:
    with FrameReader(sample_video) as sequential, FrameReader(sample_video) as seeking:
        for index in range(6):
            assert np.array_equal(
                sequential.read_frame(index), seeking.read_frame(index)
            )
        # a non-sequential jump still lands on the right frame
        assert np.array_equal(sequential.read_frame(2), seeking.read_frame(2))
        assert np.array_equal(sequential.read_frame(3), seeking.read_frame(3))


def test_negative_index_raises_index_error(sample_video: Path) -> None:
    with FrameReader(sample_video) as reader, pytest.raises(IndexError):
        reader.read_frame(-1)


def test_index_past_end_raises_index_error(sample_video: Path) -> None:
    with FrameReader(sample_video) as reader, pytest.raises(IndexError):
        reader.read_frame(reader.frame_count + 10)


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FrameReader(tmp_path / "nope.mp4")


def test_corrupt_file_raises_runtime_error(corrupt_video: Path) -> None:
    with pytest.raises(RuntimeError):
        FrameReader(corrupt_video)
