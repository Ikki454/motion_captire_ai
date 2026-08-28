"""Apply a parsed mcapclip onto a Blender armature.

Imports ``bpy`` / ``mathutils`` -- only usable inside Blender.
"""

import bpy
from mathutils import Quaternion, Vector

from . import conversion
from .mcapclip import ParsedClip


def apply_clip_to_armature(
    armature: "bpy.types.Object",
    clip: ParsedClip,
    bone_map: dict[str, str] | None = None,
) -> int:
    """Insert keyframes on ``armature`` from ``clip``; return bones touched.

    Canonical bone rotations are applied to same-named pose bones (or via
    ``bone_map``). Rest-pose differences between the canonical skeleton and
    the target rig are **not** compensated here -- proper retargeting is a
    later feature. Canonical Y-up data is converted to Blender Z-up.
    """

    mapping = bone_map or {}
    pose_bones = armature.pose.bones
    touched: set[str] = set()

    armature.rotation_mode = "QUATERNION"

    for clip_frame in clip.frames:
        blender_location = conversion.canonical_to_blender_location(*clip_frame.root)
        armature.location = Vector(blender_location)
        armature.keyframe_insert("location", frame=clip_frame.frame)

        for bone_name, quaternion in clip_frame.rotations.items():
            target_name = mapping.get(bone_name, bone_name)
            pose_bone = pose_bones.get(target_name)
            if pose_bone is None:
                continue

            pose_bone.rotation_mode = "QUATERNION"
            pose_bone.rotation_quaternion = Quaternion(
                conversion.canonical_to_blender_quaternion(*quaternion)
            )
            pose_bone.keyframe_insert("rotation_quaternion", frame=clip_frame.frame)
            touched.add(target_name)

    scene = bpy.context.scene
    scene.frame_start = clip.frame_range[0]
    scene.frame_end = clip.frame_range[1]

    return len(touched)
