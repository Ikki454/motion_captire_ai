"""Convert detector-native keypoints (Level 0) to the canonical skeleton (Level 1).

This module is the boundary between the AI system and the rest of the
application: a new detector needs a new entry here, and nothing above
:class:`PoseFrame` changes.
"""

from collections.abc import Callable

from app.models.keypoints import RawPose
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.pose.schemas import MEDIAPIPE_POSE_SCHEMA_ID

_DEFAULT_VISIBILITY_THRESHOLD = 0.5

# MediaPipe pose landmark index for the canonical joints it maps directly.
_MEDIAPIPE_DIRECT: dict[JointName, int] = {
    JointName.HEAD: 0,
    JointName.LEFT_SHOULDER: 11,
    JointName.RIGHT_SHOULDER: 12,
    JointName.LEFT_ELBOW: 13,
    JointName.RIGHT_ELBOW: 14,
    JointName.LEFT_WRIST: 15,
    JointName.RIGHT_WRIST: 16,
    JointName.LEFT_HIP: 23,
    JointName.RIGHT_HIP: 24,
    JointName.LEFT_KNEE: 25,
    JointName.RIGHT_KNEE: 26,
    JointName.LEFT_ANKLE: 27,
    JointName.RIGHT_ANKLE: 28,
    JointName.LEFT_FOOT: 31,
    JointName.RIGHT_FOOT: 32,
}


def _blend(a: Joint, b: Joint, weight: float, name: JointName) -> Joint:
    """Return a joint at ``a * (1 - weight) + b * weight``.

    Confidence is the minimum of the two sources.
    """

    return Joint(
        name=name,
        position=Vector3(
            x=a.position.x * (1 - weight) + b.position.x * weight,
            y=a.position.y * (1 - weight) + b.position.y * weight,
            z=a.position.z * (1 - weight) + b.position.z * weight,
        ),
        confidence=min(a.confidence, b.confidence),
    )


def mediapipe_to_canonical(
    raw: RawPose,
    visibility_threshold: float = _DEFAULT_VISIBILITY_THRESHOLD,
) -> PoseFrame:
    """Map a MediaPipe :class:`RawPose` to a canonical :class:`PoseFrame`.

    MediaPipe left/right names are anatomical (the subject's own left and
    right), matching the canonical joint names. Joints MediaPipe does not
    provide directly (``pelvis``, ``chest``, ``neck``) are derived from the
    hips and shoulders. Keypoints whose visibility is below
    ``visibility_threshold`` are kept but marked ``confidence = 0.0``.

    Raises:
        ValueError: ``raw`` is not in the MediaPipe pose schema.
    """

    if raw.schema_id != MEDIAPIPE_POSE_SCHEMA_ID:
        raise ValueError(
            f"Expected schema '{MEDIAPIPE_POSE_SCHEMA_ID}', got '{raw.schema_id}'"
        )

    joints: dict[JointName, Joint] = {}

    for joint_name, landmark_index in _MEDIAPIPE_DIRECT.items():
        x, y = raw.points[landmark_index]
        visibility = float(raw.visibility[landmark_index])
        confidence = visibility if visibility >= visibility_threshold else 0.0
        joints[joint_name] = Joint(
            name=joint_name,
            position=Vector3(x=float(x), y=float(y)),
            confidence=confidence,
        )

    pelvis = _blend(
        joints[JointName.LEFT_HIP], joints[JointName.RIGHT_HIP], 0.5, JointName.PELVIS
    )
    neck = _blend(
        joints[JointName.LEFT_SHOULDER],
        joints[JointName.RIGHT_SHOULDER],
        0.5,
        JointName.NECK,
    )
    chest = _blend(pelvis, neck, 0.7, JointName.CHEST)

    joints[JointName.PELVIS] = pelvis
    joints[JointName.NECK] = neck
    joints[JointName.CHEST] = chest

    return PoseFrame(
        frame_index=raw.frame_index,
        timestamp=raw.timestamp,
        joints=joints,
    )


_MAPPERS: dict[str, Callable[[RawPose], PoseFrame]] = {
    MEDIAPIPE_POSE_SCHEMA_ID: mediapipe_to_canonical,
}


def to_canonical(raw: RawPose) -> PoseFrame:
    """Map ``raw`` to a canonical :class:`PoseFrame`, dispatching on its schema.

    Raises:
        ValueError: No canonical mapping is registered for the schema.
    """

    try:
        mapper = _MAPPERS[raw.schema_id]
    except KeyError:
        raise ValueError(
            f"No canonical mapping for schema '{raw.schema_id}'"
        ) from None

    return mapper(raw)
