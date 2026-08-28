"""Tests for the skeleton solver maths (roadmap Phase 10)."""

import math
from pathlib import Path

import pytest

from app.models.corrections import CorrectionLayer
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence
from app.models.skeleton import CanonicalBoneName
from app.skeleton.solver import solve_skeleton

# A plausible standing pose in image pixels (y grows downward).
_STANDING = {
    JointName.PELVIS: (100, 300),
    JointName.CHEST: (100, 200),
    JointName.NECK: (100, 160),
    JointName.HEAD: (100, 120),
    JointName.LEFT_SHOULDER: (130, 170),
    JointName.RIGHT_SHOULDER: (70, 170),
    JointName.LEFT_ELBOW: (170, 170),
    JointName.RIGHT_ELBOW: (30, 170),
    JointName.LEFT_WRIST: (210, 170),
    JointName.RIGHT_WRIST: (-10, 170),
    JointName.LEFT_HIP: (115, 300),
    JointName.RIGHT_HIP: (85, 300),
    JointName.LEFT_KNEE: (115, 400),
    JointName.RIGHT_KNEE: (85, 400),
    JointName.LEFT_ANKLE: (115, 500),
    JointName.RIGHT_ANKLE: (85, 500),
    JointName.LEFT_FOOT: (125, 510),
    JointName.RIGHT_FOOT: (75, 510),
}


def _frame(index: int, positions: dict[JointName, tuple[float, float]]) -> PoseFrame:
    joints = {
        name: Joint(name, Vector3(float(x), float(y)), 1.0)
        for name, (x, y) in positions.items()
    }
    return PoseFrame(index, index / 24.0, joints)


def _sequence(*frames: PoseFrame) -> PoseSequence:
    track = PersonTrack(track_id="person_0")
    for frame in frames:
        track.frames[frame.frame_index] = frame
    sequence = PoseSequence(
        video_path=Path("v.mp4"), frame_count=len(frames), fps=24.0, width=200, height=600
    )
    sequence.add_track(track, make_active=True)
    return sequence


def _angle(rotation) -> float:
    return 2 * math.acos(min(1.0, abs(rotation.w)))


def test_solves_every_analysed_frame() -> None:
    clip = solve_skeleton(_sequence(_frame(0, _STANDING), _frame(1, _STANDING)))

    assert len(clip.poses) == 2
    assert clip.frame_range == (0, 1)
    assert clip.fps == 24.0
    assert len(clip.bone_lengths) == len(clip.skeleton.bones)


def test_standing_pose_has_near_identity_rotations() -> None:
    clip = solve_skeleton(_sequence(_frame(0, _STANDING)))
    pose = clip.poses[0]

    for name in (
        CanonicalBoneName.SPINE,
        CanonicalBoneName.LEFT_UPPER_ARM,
        CanonicalBoneName.LEFT_UPPER_LEG,
    ):
        assert _angle(pose.bone_rotations[name]) < 0.3


def test_bent_forearm_gives_a_quarter_turn_local_rotation() -> None:
    bent = dict(_STANDING)
    bent[JointName.LEFT_WRIST] = (170, 220)  # forearm bends down 90 degrees

    clip = solve_skeleton(_sequence(_frame(0, bent)))
    forearm = clip.poses[0].bone_rotations[CanonicalBoneName.LEFT_LOWER_ARM]

    assert _angle(forearm) == pytest.approx(math.pi / 2, abs=0.05)


def test_missing_joint_yields_identity_rotation() -> None:
    partial = dict(_STANDING)
    frame = _frame(0, partial)
    frame.joints[JointName.LEFT_WRIST].confidence = 0.0

    clip = solve_skeleton(_sequence(frame))
    forearm = clip.poses[0].bone_rotations[CanonicalBoneName.LEFT_LOWER_ARM]

    assert _angle(forearm) == pytest.approx(0.0, abs=1e-6)
    assert clip.bone_lengths[CanonicalBoneName.LEFT_LOWER_ARM] == 0.0


def test_root_translation_is_pelvis_in_canonical_space() -> None:
    clip = solve_skeleton(_sequence(_frame(0, _STANDING)))
    root = clip.poses[0].root_translation

    assert (root.x, root.y, root.z) == (100.0, -300.0, 0.0)


def test_canonical_world_track_is_used_without_a_y_flip() -> None:
    from app.math.coordinates import CoordinateSpace

    sequence = _sequence(_frame(0, _STANDING))
    track = sequence.active_track
    track.space = CoordinateSpace.CANONICAL_WORLD

    clip = solve_skeleton(sequence)

    # Positions are taken as-is: root == pelvis with y NOT flipped.
    assert clip.poses[0].root_translation.y == 300.0


def test_corrections_feed_into_the_solve() -> None:
    layer = CorrectionLayer(track_id="person_0")
    layer.set(0, JointName.LEFT_WRIST, Vector3(170.0, 220.0, 0.0))

    clip = solve_skeleton(_sequence(_frame(0, _STANDING)), correction_layer=layer)
    forearm = clip.poses[0].bone_rotations[CanonicalBoneName.LEFT_LOWER_ARM]

    assert _angle(forearm) == pytest.approx(math.pi / 2, abs=0.05)
