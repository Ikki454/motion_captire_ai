"""Tests for 3D reconstruction backends (roadmap Phase 15)."""

from pathlib import Path

import numpy as np
import pytest

from app.math.coordinates import CoordinateSpace
from app.models.keypoints import RawPose
from app.models.pose import JointName
from app.models.pose_sequence import PersonTrack, PoseSequence
from app.pose.schemas import MEDIAPIPE_POSE_SCHEMA_ID
from app.reconstruct.backends import build_reconstruction_registry
from app.reconstruct.mediapipe_world import MediaPipeWorldReconstruction
from app.reconstruct.validation import reconstruction_quality_report


def _world_pose() -> np.ndarray:
    world = np.zeros((33, 3), dtype=np.float64)
    world[0] = (0.0, -0.6, 0.0)  # nose
    world[11] = (0.18, -0.45, 0.0)
    world[12] = (-0.18, -0.45, 0.0)
    world[13] = (0.45, -0.45, 0.0)
    world[14] = (-0.45, -0.45, 0.0)
    world[15] = (0.70, -0.45, 0.0)
    world[16] = (-0.70, -0.45, 0.0)
    world[23] = (0.10, 0.0, 0.0)
    world[24] = (-0.10, 0.0, 0.0)
    world[25] = (0.10, 0.45, 0.0)
    world[26] = (-0.10, 0.45, 0.0)
    world[27] = (0.10, 0.90, 0.0)
    world[28] = (-0.10, 0.90, 0.0)
    world[31] = (0.10, 0.95, 0.10)
    world[32] = (-0.10, 0.95, 0.10)
    return world


def _sequence(*, with_world: bool = True, depth: str = "mediapipe_world") -> PoseSequence:
    track = PersonTrack(track_id="person_0", depth_source=depth)
    for index in range(6):
        track.raw_frames[index] = RawPose(
            schema_id=MEDIAPIPE_POSE_SCHEMA_ID,
            frame_index=index,
            timestamp=index / 24.0,
            person_index=0,
            points=np.zeros((33, 2)),
            visibility=np.ones(33),
            world_points=_world_pose() if with_world else None,
            depth_source=depth,
        )
    sequence = PoseSequence(
        video_path=Path("v.mp4"), frame_count=6, fps=24.0, width=100, height=100
    )
    sequence.add_track(track, make_active=True)
    return sequence


def test_registry_lists_the_mediapipe_world_backend() -> None:
    ids = {entry.backend_id for entry in build_reconstruction_registry().available()}

    assert "mediapipe_world" in ids


def test_can_reconstruct_requires_world_depth_data() -> None:
    backend = MediaPipeWorldReconstruction()

    assert backend.can_reconstruct(_sequence()) is True
    assert backend.can_reconstruct(_sequence(with_world=False)) is False
    assert backend.can_reconstruct(_sequence(depth="none")) is False


def test_reconstruction_produces_a_canonical_world_track() -> None:
    result = MediaPipeWorldReconstruction().reconstruct(_sequence())

    track = result.active_track
    assert track.space is CoordinateSpace.CANONICAL_WORLD
    assert track.depth_source == "reconstruction:mediapipe_world"
    assert track.detection_count == 6
    assert set(track.frames[0].joints) == set(JointName)


def test_axes_are_flipped_to_y_up() -> None:
    track = MediaPipeWorldReconstruction().reconstruct(_sequence()).active_track

    # MediaPipe nose is at y = -0.6 (y down); canonical is y up.
    assert track.frames[0].joints[JointName.HEAD].position.y == pytest.approx(0.6)


def test_derived_joints_are_between_their_sources() -> None:
    joints = MediaPipeWorldReconstruction().reconstruct(_sequence()).active_track.frames[
        0
    ].joints

    assert joints[JointName.PELVIS].position.x == pytest.approx(0.0)
    assert joints[JointName.NECK].position.y == pytest.approx(0.45)


def test_quality_report_is_quiet_for_a_symmetric_figure() -> None:
    result = MediaPipeWorldReconstruction().reconstruct(_sequence())

    assert reconstruction_quality_report(result) == []


def test_quality_report_flags_limb_asymmetry() -> None:
    sequence = _sequence()
    for raw in sequence.active_track.raw_frames.values():
        raw.world_points[15] = (2.0, -0.45, 0.0)  # left wrist far out

    result = MediaPipeWorldReconstruction().reconstruct(sequence)
    notes = reconstruction_quality_report(result)

    assert any("lower_arm" in note for note in notes)
