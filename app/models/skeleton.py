"""The rig-independent canonical skeleton: bone hierarchy, rest pose, clips."""

from dataclasses import dataclass, field
from enum import Enum

from app.math.coordinates import CoordinateSpace
from app.math.rotations import Quaternion
from app.math.vectors import normalize, subtract
from app.models.pose import JointName, Vector3


class CanonicalBoneName(str, Enum):
    """Canonical bone names -- never a target rig's bone names."""

    SPINE = "spine"
    NECK = "neck"
    HEAD = "head"

    LEFT_CLAVICLE = "left_clavicle"
    RIGHT_CLAVICLE = "right_clavicle"
    LEFT_UPPER_ARM = "left_upper_arm"
    LEFT_LOWER_ARM = "left_lower_arm"
    RIGHT_UPPER_ARM = "right_upper_arm"
    RIGHT_LOWER_ARM = "right_lower_arm"

    LEFT_HIP = "left_hip"
    RIGHT_HIP = "right_hip"
    LEFT_UPPER_LEG = "left_upper_leg"
    LEFT_LOWER_LEG = "left_lower_leg"
    LEFT_FOOT = "left_foot"
    RIGHT_UPPER_LEG = "right_upper_leg"
    RIGHT_LOWER_LEG = "right_lower_leg"
    RIGHT_FOOT = "right_foot"


@dataclass(frozen=True)
class BoneDefinition:
    """One bone: which joints span it and which bone it hangs from."""

    name: CanonicalBoneName
    parent: CanonicalBoneName | None
    parent_joint: JointName
    child_joint: JointName


@dataclass
class CanonicalSkeleton:
    """Bone hierarchy plus a rest (T-)pose in ``CANONICAL_WORLD``.

    ``bones`` is ordered so every bone appears after its parent.
    """

    bones: tuple[BoneDefinition, ...]
    rest_positions: dict[JointName, Vector3]

    def bone(self, name: CanonicalBoneName) -> BoneDefinition:
        """Return the definition of the bone called ``name``."""

        for definition in self.bones:
            if definition.name == name:
                return definition
        raise KeyError(name)

    def bone_names(self) -> tuple[CanonicalBoneName, ...]:
        """Return every bone name, parent-first."""

        return tuple(definition.name for definition in self.bones)

    def rest_direction(self, bone: BoneDefinition) -> Vector3:
        """Return the unit direction of ``bone`` in the rest pose."""

        return normalize(
            subtract(
                self.rest_positions[bone.child_joint],
                self.rest_positions[bone.parent_joint],
            )
        )


@dataclass
class SkeletonPose:
    """One frame of the canonical skeleton.

    ``bone_rotations`` are local (relative to the parent bone's rotation).
    ``root_translation`` is the pelvis position in ``CANONICAL_WORLD``.
    """

    frame_index: int
    bone_rotations: dict[CanonicalBoneName, Quaternion]
    root_translation: Vector3


@dataclass
class SkeletonClip:
    """A sequence of :class:`SkeletonPose` for one person."""

    skeleton: CanonicalSkeleton
    fps: float
    frame_range: tuple[int, int]
    bone_lengths: dict[CanonicalBoneName, float]
    poses: list[SkeletonPose] = field(default_factory=list)
    space: CoordinateSpace = CoordinateSpace.CANONICAL_WORLD


_REST_POSITIONS: dict[JointName, Vector3] = {
    JointName.PELVIS: Vector3(0.0, 0.0, 0.0),
    JointName.CHEST: Vector3(0.0, 2.2, 0.0),
    JointName.NECK: Vector3(0.0, 2.6, 0.0),
    JointName.HEAD: Vector3(0.0, 3.0, 0.0),
    JointName.LEFT_SHOULDER: Vector3(0.2, 2.5, 0.0),
    JointName.RIGHT_SHOULDER: Vector3(-0.2, 2.5, 0.0),
    JointName.LEFT_ELBOW: Vector3(1.0, 2.5, 0.0),
    JointName.RIGHT_ELBOW: Vector3(-1.0, 2.5, 0.0),
    JointName.LEFT_WRIST: Vector3(1.8, 2.5, 0.0),
    JointName.RIGHT_WRIST: Vector3(-1.8, 2.5, 0.0),
    JointName.LEFT_HIP: Vector3(0.15, 0.0, 0.0),
    JointName.RIGHT_HIP: Vector3(-0.15, 0.0, 0.0),
    JointName.LEFT_KNEE: Vector3(0.15, -1.1, 0.0),
    JointName.RIGHT_KNEE: Vector3(-0.15, -1.1, 0.0),
    JointName.LEFT_ANKLE: Vector3(0.15, -2.2, 0.0),
    JointName.RIGHT_ANKLE: Vector3(-0.15, -2.2, 0.0),
    JointName.LEFT_FOOT: Vector3(0.15, -2.3, 0.3),
    JointName.RIGHT_FOOT: Vector3(-0.15, -2.3, 0.3),
}

_BONES: tuple[BoneDefinition, ...] = (
    BoneDefinition(CanonicalBoneName.SPINE, None, JointName.PELVIS, JointName.CHEST),
    BoneDefinition(
        CanonicalBoneName.NECK, CanonicalBoneName.SPINE, JointName.CHEST, JointName.NECK
    ),
    BoneDefinition(
        CanonicalBoneName.HEAD, CanonicalBoneName.NECK, JointName.NECK, JointName.HEAD
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_CLAVICLE,
        CanonicalBoneName.SPINE,
        JointName.CHEST,
        JointName.LEFT_SHOULDER,
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_CLAVICLE,
        CanonicalBoneName.SPINE,
        JointName.CHEST,
        JointName.RIGHT_SHOULDER,
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_UPPER_ARM,
        CanonicalBoneName.LEFT_CLAVICLE,
        JointName.LEFT_SHOULDER,
        JointName.LEFT_ELBOW,
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_LOWER_ARM,
        CanonicalBoneName.LEFT_UPPER_ARM,
        JointName.LEFT_ELBOW,
        JointName.LEFT_WRIST,
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_UPPER_ARM,
        CanonicalBoneName.RIGHT_CLAVICLE,
        JointName.RIGHT_SHOULDER,
        JointName.RIGHT_ELBOW,
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_LOWER_ARM,
        CanonicalBoneName.RIGHT_UPPER_ARM,
        JointName.RIGHT_ELBOW,
        JointName.RIGHT_WRIST,
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_HIP, None, JointName.PELVIS, JointName.LEFT_HIP
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_HIP, None, JointName.PELVIS, JointName.RIGHT_HIP
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_UPPER_LEG,
        CanonicalBoneName.LEFT_HIP,
        JointName.LEFT_HIP,
        JointName.LEFT_KNEE,
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_LOWER_LEG,
        CanonicalBoneName.LEFT_UPPER_LEG,
        JointName.LEFT_KNEE,
        JointName.LEFT_ANKLE,
    ),
    BoneDefinition(
        CanonicalBoneName.LEFT_FOOT,
        CanonicalBoneName.LEFT_LOWER_LEG,
        JointName.LEFT_ANKLE,
        JointName.LEFT_FOOT,
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_UPPER_LEG,
        CanonicalBoneName.RIGHT_HIP,
        JointName.RIGHT_HIP,
        JointName.RIGHT_KNEE,
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_LOWER_LEG,
        CanonicalBoneName.RIGHT_UPPER_LEG,
        JointName.RIGHT_KNEE,
        JointName.RIGHT_ANKLE,
    ),
    BoneDefinition(
        CanonicalBoneName.RIGHT_FOOT,
        CanonicalBoneName.RIGHT_LOWER_LEG,
        JointName.RIGHT_ANKLE,
        JointName.RIGHT_FOOT,
    ),
)

CANONICAL_SKELETON = CanonicalSkeleton(bones=_BONES, rest_positions=_REST_POSITIONS)
