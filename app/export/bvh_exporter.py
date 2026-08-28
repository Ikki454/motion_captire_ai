"""Export a canonical :class:`SkeletonClip` to a BioVision Hierarchy (.bvh) file.

BVH is a secondary format: Blender, Maya and MotionBuilder import it
natively, so no add-on is needed. The canonical skeleton *is* the rig here
-- BVH files are self-describing.

Both BVH and ``CANONICAL_WORLD`` are right-handed and Y-up, so no axis
conversion is applied. Rotations are written as intrinsic ``Z Y X`` Euler
angles in degrees; a particular importer may want a different order.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app.math.rotations import Quaternion
from app.math.vectors import length, normalize, scale, subtract
from app.models.pose import JointName, Vector3
from app.models.skeleton import (
    BoneDefinition,
    CanonicalBoneName,
    CanonicalSkeleton,
    SkeletonClip,
)

_ROOT_JOINT = JointName.PELVIS
_END_SITE_FRACTION = 0.35
_ROOT_CHANNELS = (
    "Xposition Yposition Zposition Zrotation Yrotation Xrotation"
)
_JOINT_CHANNELS = "Zrotation Yrotation Xrotation"


@dataclass
class _BvhJoint:
    joint: JointName
    offset: Vector3
    incoming_bone: BoneDefinition | None
    children: list["_BvhJoint"] = field(default_factory=list)
    end_site_offset: Vector3 | None = None


def export_bvh(clip: SkeletonClip, path: Path) -> None:
    """Write ``clip`` to ``path`` as a ``.bvh`` file."""

    path.write_text(write_bvh_document(clip), encoding="utf-8")


def write_bvh_document(clip: SkeletonClip) -> str:
    """Return the full text of a BVH file for ``clip``."""

    skeleton = clip.skeleton
    root = _build_tree(skeleton, clip, _ROOT_JOINT, parent=None)
    ordered = _flatten(root)

    lines: list[str] = ["HIERARCHY"]
    _emit_joint(root, lines, depth=0, is_root=True)

    lines.append("MOTION")
    lines.append(f"Frames: {len(clip.poses)}")
    frame_time = 1.0 / clip.fps if clip.fps > 0 else 0.0
    lines.append(f"Frame Time: {frame_time:.6f}")

    for pose in clip.poses:
        values: list[float] = [
            pose.root_translation.x,
            pose.root_translation.y,
            pose.root_translation.z,
        ]
        for node in ordered:
            values.extend(_euler_zyx(_rotation_for(node, pose.bone_rotations)))
        lines.append(" ".join(f"{value:.6f}" for value in values))

    return "\n".join(lines) + "\n"


def _build_tree(
    skeleton: CanonicalSkeleton,
    clip: SkeletonClip,
    joint: JointName,
    parent: JointName | None,
) -> _BvhJoint:
    incoming = _bone_ending_at(skeleton, joint)
    offset = (
        Vector3(0.0, 0.0, 0.0)
        if parent is None
        else _segment_vector(skeleton, clip, incoming)
    )
    node = _BvhJoint(joint=joint, offset=offset, incoming_bone=incoming)

    child_bones = [bone for bone in skeleton.bones if bone.parent_joint == joint]
    for bone in child_bones:
        node.children.append(
            _build_tree(skeleton, clip, bone.child_joint, parent=joint)
        )

    if not child_bones and incoming is not None:
        node.end_site_offset = scale(
            _segment_vector(skeleton, clip, incoming), _END_SITE_FRACTION
        )

    return node


def _bone_ending_at(
    skeleton: CanonicalSkeleton, joint: JointName
) -> BoneDefinition | None:
    for bone in skeleton.bones:
        if bone.child_joint == joint:
            return bone
    return None


def _segment_vector(
    skeleton: CanonicalSkeleton, clip: SkeletonClip, bone: BoneDefinition
) -> Vector3:
    measured = clip.bone_lengths.get(bone.name, 0.0)
    if measured <= 0.0:
        measured = length(
            subtract(
                skeleton.rest_positions[bone.child_joint],
                skeleton.rest_positions[bone.parent_joint],
            )
        )
    return scale(normalize(_rest_segment(skeleton, bone)), measured)


def _rest_segment(skeleton: CanonicalSkeleton, bone: BoneDefinition) -> Vector3:
    return subtract(
        skeleton.rest_positions[bone.child_joint],
        skeleton.rest_positions[bone.parent_joint],
    )


def _flatten(node: _BvhJoint) -> list[_BvhJoint]:
    ordered = [node]
    for child in node.children:
        ordered.extend(_flatten(child))
    return ordered


def _rotation_for(
    node: _BvhJoint,
    bone_rotations: Mapping[CanonicalBoneName, Quaternion],
) -> Quaternion:
    if node.incoming_bone is None:
        return Quaternion.identity()
    return bone_rotations.get(node.incoming_bone.name, Quaternion.identity())


def _euler_zyx(quaternion: Quaternion) -> tuple[float, float, float]:
    z, y, x = quaternion.to_rotation().as_euler("ZYX", degrees=True)
    return (float(z), float(y), float(x))


def _emit_joint(
    node: _BvhJoint, lines: list[str], depth: int, *, is_root: bool
) -> None:
    indent = "  " * depth
    label = "ROOT" if is_root else "JOINT"
    lines.append(f"{indent}{label} {node.joint.value}")
    lines.append(f"{indent}{{")

    inner = "  " * (depth + 1)
    lines.append(
        f"{inner}OFFSET {node.offset.x:.6f} {node.offset.y:.6f} {node.offset.z:.6f}"
    )
    channels = _ROOT_CHANNELS if is_root else _JOINT_CHANNELS
    channel_count = 6 if is_root else 3
    lines.append(f"{inner}CHANNELS {channel_count} {channels}")

    for child in node.children:
        _emit_joint(child, lines, depth + 1, is_root=False)

    if node.end_site_offset is not None:
        end = node.end_site_offset
        lines.append(f"{inner}End Site")
        lines.append(f"{inner}{{")
        lines.append(f"{inner}  OFFSET {end.x:.6f} {end.y:.6f} {end.z:.6f}")
        lines.append(f"{inner}}}")

    lines.append(f"{indent}}}")
