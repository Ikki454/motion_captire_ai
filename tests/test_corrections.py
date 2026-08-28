"""Tests for the CorrectionLayer and effective-pose merge (roadmap Phase 9)."""

import pytest

from app.models.corrections import CorrectionLayer, effective_pose, lerp_vector3
from app.models.pose import Joint, JointName, PoseFrame, Vector3


def _detected(**joints: Vector3) -> PoseFrame:
    return PoseFrame(
        frame_index=3,
        timestamp=0.12,
        joints={
            JointName[key.upper()]: Joint(
                name=JointName[key.upper()], position=position, confidence=0.8
            )
            for key, position in joints.items()
        },
    )


def test_set_get_and_clear() -> None:
    layer = CorrectionLayer(track_id="person_0")
    assert layer.is_empty

    layer.set(5, JointName.LEFT_WRIST, Vector3(10.0, 20.0, 0.0))
    assert not layer.is_empty
    assert layer.get(5, JointName.LEFT_WRIST) == Vector3(10.0, 20.0, 0.0)
    assert layer.correction_count == 1

    layer.clear(5, JointName.LEFT_WRIST)
    assert layer.get(5, JointName.LEFT_WRIST) is None
    assert layer.is_empty
    assert 5 not in layer.overrides


def test_keyframes_and_corrected_frames() -> None:
    layer = CorrectionLayer(track_id="person_0")
    layer.set(2, JointName.HEAD, Vector3(0.0, 0.0, 0.0))
    layer.set(9, JointName.HEAD, Vector3(0.0, 0.0, 0.0))
    layer.set(9, JointName.LEFT_KNEE, Vector3(0.0, 0.0, 0.0))

    assert layer.keyframes_for(JointName.HEAD) == [2, 9]
    assert layer.keyframes_for(JointName.LEFT_KNEE) == [9]
    assert layer.corrected_frames() == [2, 9]


def test_lerp_vector3_midpoint() -> None:
    result = lerp_vector3(Vector3(0.0, 0.0, 0.0), Vector3(10.0, 20.0, 4.0), 0.5)
    assert result == Vector3(5.0, 10.0, 2.0)


def test_effective_pose_overrides_a_detected_joint() -> None:
    detected = _detected(left_wrist=Vector3(1.0, 1.0, 0.0), head=Vector3(2.0, 2.0, 0.0))
    corrections = {JointName.LEFT_WRIST: Vector3(50.0, 60.0, 0.0)}

    pose = effective_pose(3, 0.12, detected, corrections)

    assert pose.joints[JointName.LEFT_WRIST].position == Vector3(50.0, 60.0, 0.0)
    assert pose.joints[JointName.LEFT_WRIST].confidence == 1.0
    assert pose.joints[JointName.HEAD].position == Vector3(2.0, 2.0, 0.0)
    assert pose.joints[JointName.HEAD].confidence == pytest.approx(0.8)


def test_effective_pose_adds_a_joint_the_detector_missed() -> None:
    detected = _detected(head=Vector3(2.0, 2.0, 0.0))
    corrections = {JointName.RIGHT_ANKLE: Vector3(9.0, 9.0, 0.0)}

    pose = effective_pose(3, 0.12, detected, corrections)

    assert pose.joints[JointName.RIGHT_ANKLE].position == Vector3(9.0, 9.0, 0.0)
    assert pose.joints[JointName.RIGHT_ANKLE].confidence == 1.0


def test_effective_pose_on_a_gap_frame_returns_only_corrections() -> None:
    corrections = {JointName.LEFT_HIP: Vector3(4.0, 4.0, 0.0)}

    pose = effective_pose(7, 0.28, None, corrections)

    assert pose is not None
    assert set(pose.joints) == {JointName.LEFT_HIP}
    assert pose.timestamp == pytest.approx(0.28)


def test_effective_pose_is_none_without_detection_or_correction() -> None:
    assert effective_pose(7, 0.28, None, {}) is None
