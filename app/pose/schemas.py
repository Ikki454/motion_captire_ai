"""Keypoint schemas used by the pose pipeline."""

from app.models.keypoints import KeypointSchema
from app.models.pose import CANONICAL_CONNECTIONS, JointName

MEDIAPIPE_POSE_SCHEMA_ID = "mediapipe_pose_33"
CANONICAL_SCHEMA_ID = "canonical_v1"

_MEDIAPIPE_POSE_LANDMARK_NAMES: tuple[str, ...] = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)

# Torso and limb segments, enough for an overlay preview.
_MEDIAPIPE_POSE_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (24, 26),
    (26, 28),
)

MEDIAPIPE_POSE = KeypointSchema(
    schema_id=MEDIAPIPE_POSE_SCHEMA_ID,
    landmark_names=_MEDIAPIPE_POSE_LANDMARK_NAMES,
    connections=_MEDIAPIPE_POSE_CONNECTIONS,
)

_CANONICAL_NAMES: tuple[str, ...] = tuple(joint.value for joint in JointName)
_CANONICAL_INDEX: dict[str, int] = {
    name: index for index, name in enumerate(_CANONICAL_NAMES)
}
_CANONICAL_CONNECTIONS_IDX: tuple[tuple[int, int], ...] = tuple(
    (_CANONICAL_INDEX[start.value], _CANONICAL_INDEX[end.value])
    for start, end in CANONICAL_CONNECTIONS
)

CANONICAL = KeypointSchema(
    schema_id=CANONICAL_SCHEMA_ID,
    landmark_names=_CANONICAL_NAMES,
    connections=_CANONICAL_CONNECTIONS_IDX,
)
