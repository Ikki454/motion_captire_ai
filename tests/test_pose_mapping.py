"""Tests for keypoint mapping L0 -> L1 (roadmap Phase 6)."""

import numpy as np
import pytest

from app.models.keypoints import RawPose
from app.models.pose import JointName
from app.pose.mapping import mediapipe_to_canonical, to_canonical
from app.pose.schemas import MEDIAPIPE_POSE_SCHEMA_ID


def _mediapipe_raw(visibility_value: float = 1.0) -> RawPose:
    # 33 landmarks; give each a distinct pixel coordinate so mapping is checkable.
    points = np.array([(i * 10.0, i * 5.0) for i in range(33)], dtype=np.float64)
    visibility = np.full(33, visibility_value, dtype=np.float64)
    return RawPose(
        schema_id=MEDIAPIPE_POSE_SCHEMA_ID,
        frame_index=7,
        timestamp=0.25,
        person_index=0,
        points=points,
        visibility=visibility,
    )


def test_maps_all_canonical_joints_with_expected_indices() -> None:
    pose = mediapipe_to_canonical(_mediapipe_raw())

    assert set(pose.joints) == set(JointName)
    assert pose.frame_index == 7
    assert pose.timestamp == 0.25

    # HEAD <- MediaPipe landmark 0, LEFT_SHOULDER <- 11, RIGHT_ANKLE <- 28
    assert pose.joints[JointName.HEAD].position.x == 0.0
    assert pose.joints[JointName.LEFT_SHOULDER].position.x == 110.0
    assert pose.joints[JointName.RIGHT_ANKLE].position.x == 280.0


def test_low_visibility_keypoints_kept_with_zero_confidence() -> None:
    pose = mediapipe_to_canonical(_mediapipe_raw(visibility_value=0.2))

    assert set(pose.joints) == set(JointName)
    assert all(joint.confidence == 0.0 for joint in pose.joints.values())


def test_visibility_threshold_is_configurable() -> None:
    raw = _mediapipe_raw(visibility_value=0.4)

    strict = mediapipe_to_canonical(raw, visibility_threshold=0.5)
    lenient = mediapipe_to_canonical(raw, visibility_threshold=0.3)

    assert strict.joints[JointName.HEAD].confidence == 0.0
    assert lenient.joints[JointName.HEAD].confidence == pytest.approx(0.4)


def test_wrong_schema_raises_value_error() -> None:
    raw = _mediapipe_raw()
    raw.schema_id = "coco_17"

    with pytest.raises(ValueError, match="schema"):
        mediapipe_to_canonical(raw)


def test_to_canonical_dispatches_on_schema() -> None:
    pose = to_canonical(_mediapipe_raw())

    assert set(pose.joints) == set(JointName)


def test_to_canonical_unknown_schema_raises() -> None:
    raw = _mediapipe_raw()
    raw.schema_id = "unknown_schema"

    with pytest.raises(ValueError, match="No canonical mapping"):
        to_canonical(raw)
