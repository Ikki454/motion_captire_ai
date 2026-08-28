"""Tests for skeleton validation (roadmap Phase 10)."""

from pathlib import Path

from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence
from app.skeleton.solver import solve_skeleton
from app.skeleton.validation import bone_length_report, validate_skeleton_clip

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
        video_path=Path("v.mp4"),
        frame_count=len(frames),
        fps=24.0,
        width=200,
        height=600,
    )
    sequence.add_track(track, make_active=True)
    return sequence


def test_a_clean_solve_has_no_structural_issues() -> None:
    clip = solve_skeleton(_sequence(_frame(0, _STANDING), _frame(1, _STANDING)))

    assert validate_skeleton_clip(clip) == []


def test_empty_clip_is_flagged() -> None:
    sequence = _sequence()

    clip = solve_skeleton(sequence)

    assert any("no solved frames" in issue for issue in validate_skeleton_clip(clip))


def test_bone_length_report_flags_a_wildly_varying_limb() -> None:
    stretched = dict(_STANDING)
    stretched[JointName.LEFT_WRIST] = (400, 170)  # forearm several times longer
    frames = [
        _frame(0, _STANDING),
        _frame(1, _STANDING),
        _frame(2, stretched),
        _frame(3, stretched),
    ]

    notes = bone_length_report(_sequence(*frames))

    assert any("left_lower_arm" in note for note in notes)


def test_bone_length_report_is_quiet_for_a_rigid_pose() -> None:
    frames = [_frame(index, _STANDING) for index in range(4)]

    assert bone_length_report(_sequence(*frames)) == []
