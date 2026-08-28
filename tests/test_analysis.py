"""Tests for full-video analysis (roadmap Phase 7)."""

from pathlib import Path

import numpy as np

from app.models.keypoints import KeypointSchema, RawPose
from app.pose.analysis import analyze_video, analyze_video_parallel
from app.pose.capabilities import DetectorCapabilities
from app.pose.detector_base import PoseDetector
from app.pose.schemas import MEDIAPIPE_POSE
from app.video.frame_reader import FrameReader
from app.video.video_loader import VideoLoader


class _FakeDetector(PoseDetector):
    """Returns a pose on every frame except multiples of ``gap_every``."""

    def __init__(self, *, gap_every: int = 0, with_world: bool = False) -> None:
        self._gap_every = gap_every
        self._with_world = with_world

    @property
    def schema(self) -> KeypointSchema:
        return MEDIAPIPE_POSE

    @property
    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(keypoint_count=33)

    def detect(
        self, frame: np.ndarray, frame_index: int, timestamp: float
    ) -> RawPose | None:
        if self._gap_every and frame_index % self._gap_every == 0:
            return None

        points = np.tile((5.0, 6.0), (33, 1))
        visibility = np.ones(33)
        world = np.zeros((33, 3)) if self._with_world else None
        return RawPose(
            schema_id=MEDIAPIPE_POSE.schema_id,
            frame_index=frame_index,
            timestamp=timestamp,
            person_index=0,
            points=points,
            visibility=visibility,
            world_points=world,
            depth_source="mediapipe_world" if self._with_world else "none",
        )


def test_analyzes_every_frame(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequence = analyze_video(reader, _FakeDetector(), metadata)

    track = sequence.active_track
    assert sequence.frame_count == metadata.frame_count
    assert track.detection_count == metadata.frame_count
    assert track.detected_indices() == list(range(metadata.frame_count))


def test_missing_detections_are_gaps(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequence = analyze_video(reader, _FakeDetector(gap_every=3), metadata)

    track = sequence.active_track
    assert 0 not in track.frames
    assert 3 not in track.frames
    assert 1 in track.frames
    assert track.detection_count < metadata.frame_count


def test_progress_covers_all_frames(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)
    seen: list[tuple[int, int]] = []

    with FrameReader(sample_video) as reader:
        analyze_video(
            reader, _FakeDetector(), metadata, on_progress=lambda d, t: seen.append((d, t))
        )

    assert seen[0] == (1, metadata.frame_count)
    assert seen[-1] == (metadata.frame_count, metadata.frame_count)


def test_cancellation_returns_a_partial_sequence(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)
    processed = 0

    def should_cancel() -> bool:
        nonlocal processed
        processed += 1
        return processed > 4

    with FrameReader(sample_video) as reader:
        sequence = analyze_video(
            reader, _FakeDetector(), metadata, should_cancel=should_cancel
        )

    assert sequence.active_track.detection_count == 4


def test_raw_frames_retain_world_landmarks_and_tag(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequence = analyze_video(reader, _FakeDetector(with_world=True), metadata)

    track = sequence.active_track
    assert track.depth_source == "mediapipe_world"
    assert len(track.raw_frames) == metadata.frame_count
    assert track.raw_frames[0].world_points.shape == (33, 3)
    assert track.raw_frames[0].points.shape == (33, 2)


def test_raw_frames_have_no_world_when_detector_is_2d(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequence = analyze_video(reader, _FakeDetector(with_world=False), metadata)

    track = sequence.active_track
    assert track.raw_frames[0].world_points is None
    assert track.depth_source == "none"


def test_raw_and_canonical_frames_are_aligned(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequence = analyze_video(reader, _FakeDetector(gap_every=3), metadata)

    track = sequence.active_track
    assert sorted(track.raw_frames) == sorted(track.frames)


def test_parallel_analysis_matches_the_sequential_result(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequential = analyze_video(reader, _FakeDetector(gap_every=4), metadata)

    parallel = analyze_video_parallel(
        sample_video,
        lambda: _FakeDetector(gap_every=4),
        metadata,
        workers=3,
    )

    seq_track = sequential.active_track
    par_track = parallel.active_track
    assert sorted(par_track.frames) == sorted(seq_track.frames)
    assert par_track.detection_count == seq_track.detection_count


def test_parallel_analysis_reports_progress_for_every_frame(
    sample_video: Path,
) -> None:
    metadata = VideoLoader().load_metadata(sample_video)
    seen: list[tuple[int, int]] = []

    analyze_video_parallel(
        sample_video,
        _FakeDetector,
        metadata,
        workers=3,
        on_progress=lambda done, total: seen.append((done, total)),
    )

    assert len(seen) == metadata.frame_count
    assert max(done for done, _ in seen) == metadata.frame_count


def test_parallel_analysis_can_be_cancelled(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)
    processed = 0

    def should_cancel() -> bool:
        nonlocal processed
        processed += 1
        return processed > 6

    sequence = analyze_video_parallel(
        sample_video,
        _FakeDetector,
        metadata,
        workers=2,
        should_cancel=should_cancel,
    )

    assert sequence.active_track.detection_count < metadata.frame_count


def test_parallel_with_one_worker_equals_sequential(sample_video: Path) -> None:
    metadata = VideoLoader().load_metadata(sample_video)

    with FrameReader(sample_video) as reader:
        sequential = analyze_video(reader, _FakeDetector(), metadata)

    parallel = analyze_video_parallel(
        sample_video, _FakeDetector, metadata, workers=1
    )

    assert sorted(parallel.active_track.frames) == sorted(sequential.active_track.frames)
