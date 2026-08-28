from dataclasses import dataclass
from enum import Enum


class JointName(str, Enum):
    """Canonical human joint names (schema ``canonical_v2``)."""

    PELVIS = "pelvis"
    CHEST = "chest"
    NECK = "neck"
    HEAD = "head"

    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"

    LEFT_ELBOW = "left_elbow"
    RIGHT_ELBOW = "right_elbow"

    LEFT_WRIST = "left_wrist"
    RIGHT_WRIST = "right_wrist"

    LEFT_HIP = "left_hip"
    RIGHT_HIP = "right_hip"

    LEFT_KNEE = "left_knee"
    RIGHT_KNEE = "right_knee"

    LEFT_ANKLE = "left_ankle"
    RIGHT_ANKLE = "right_ankle"

    LEFT_FOOT = "left_foot"
    RIGHT_FOOT = "right_foot"


@dataclass
class Vector3:
    """Three-dimensional vector."""

    x: float
    y: float
    z: float = 0.0


@dataclass
class Joint:
    """Detected body joint."""

    name: JointName
    position: Vector3
    confidence: float


@dataclass
class PoseFrame:
    """Pose information for one video frame."""

    frame_index: int
    timestamp: float
    joints: dict[JointName, Joint]


CANONICAL_CONNECTIONS: tuple[tuple[JointName, JointName], ...] = (
    (JointName.PELVIS, JointName.CHEST),
    (JointName.CHEST, JointName.NECK),
    (JointName.NECK, JointName.HEAD),
    (JointName.CHEST, JointName.LEFT_SHOULDER),
    (JointName.CHEST, JointName.RIGHT_SHOULDER),
    (JointName.LEFT_SHOULDER, JointName.LEFT_ELBOW),
    (JointName.LEFT_ELBOW, JointName.LEFT_WRIST),
    (JointName.RIGHT_SHOULDER, JointName.RIGHT_ELBOW),
    (JointName.RIGHT_ELBOW, JointName.RIGHT_WRIST),
    (JointName.PELVIS, JointName.LEFT_HIP),
    (JointName.PELVIS, JointName.RIGHT_HIP),
    (JointName.LEFT_HIP, JointName.LEFT_KNEE),
    (JointName.LEFT_KNEE, JointName.LEFT_ANKLE),
    (JointName.LEFT_ANKLE, JointName.LEFT_FOOT),
    (JointName.RIGHT_HIP, JointName.RIGHT_KNEE),
    (JointName.RIGHT_KNEE, JointName.RIGHT_ANKLE),
    (JointName.RIGHT_ANKLE, JointName.RIGHT_FOOT),
)
"""Canonical joint pairs to draw as skeleton segments."""
