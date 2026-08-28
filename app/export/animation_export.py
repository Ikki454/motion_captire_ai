"""Read and write the ``mcapclip`` animation interchange format (v1).

An ``.mcapclip.json`` file carries a solved canonical :class:`SkeletonClip`
in ``CANONICAL_WORLD`` (y-up) coordinates. Converting to Blender's z-up
world happens later, in the Blender add-on -- not here.

Spec: ``docs/formats/mcapclip_v1.md``.
"""

import json
from pathlib import Path
from typing import Any

from app.math.coordinates import CoordinateSpace
from app.math.rotations import Quaternion
from app.models.pose import Vector3
from app.models.skeleton import (
    CANONICAL_SKELETON,
    CanonicalBoneName,
    SkeletonClip,
    SkeletonPose,
)

MCAPCLIP_FORMAT = "mcapclip"
MCAPCLIP_VERSION = 1

_BONE_ORDER: tuple[str, ...] = tuple(
    name.value for name in CANONICAL_SKELETON.bone_names()
)


class AnimationExportError(Exception):
    """The animation document is malformed or written by a newer version."""


def write_animation_document(
    clip: SkeletonClip,
    *,
    name: str = "",
    bone_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Serialize ``clip`` to an ``mcapclip`` v1 document.

    ``bone_map`` (canonical bone name -> target rig bone name) is written
    as an optional field a consumer may use to place rotations on a rig.
    """

    skeleton = clip.skeleton

    document: dict[str, Any] = {
        "format": MCAPCLIP_FORMAT,
        "version": MCAPCLIP_VERSION,
        "name": name,
        "coordinate_space": CoordinateSpace.CANONICAL_WORLD.value,
        "fps": clip.fps,
        "frame_range": list(clip.frame_range),
        "skeleton": {
            "bones": [
                {
                    "name": bone.name.value,
                    "parent": bone.parent.value if bone.parent is not None else None,
                    "parent_joint": bone.parent_joint.value,
                    "child_joint": bone.child_joint.value,
                    "rest_direction": _vector_to_list(
                        skeleton.rest_direction(bone)
                    ),
                }
                for bone in skeleton.bones
            ]
        },
        "bone_lengths": {
            bone_name.value: length
            for bone_name, length in clip.bone_lengths.items()
        },
        "frames": [
            {
                "frame": pose.frame_index,
                "root": _vector_to_list(pose.root_translation),
                "rotations": {
                    bone_name.value: _quaternion_to_list(
                        pose.bone_rotations.get(bone_name, Quaternion.identity())
                    )
                    for bone_name in CANONICAL_SKELETON.bone_names()
                },
            }
            for pose in clip.poses
        ],
    }

    if bone_map:
        document["bone_map"] = dict(bone_map)

    return document


def read_animation_document(document: dict[str, Any]) -> SkeletonClip:
    """Rebuild a :class:`SkeletonClip` from an ``mcapclip`` document.

    Raises:
        AnimationExportError: Wrong format, unsupported version, or the
            bone set does not match this build.
    """

    if document.get("format") != MCAPCLIP_FORMAT:
        raise AnimationExportError(
            f"not an {MCAPCLIP_FORMAT} document: {document.get('format')!r}"
        )

    version = document.get("version")
    if not isinstance(version, int) or version > MCAPCLIP_VERSION:
        raise AnimationExportError(
            f"unsupported mcapclip version {version} (this build reads "
            f"{MCAPCLIP_VERSION})"
        )

    try:
        bones = document["skeleton"]["bones"]
        bone_names = tuple(bone["name"] for bone in bones)
        if bone_names != _BONE_ORDER:
            raise AnimationExportError("mcapclip bone set does not match this build")

        fps = float(document["fps"])
        frame_range_pair = document["frame_range"]
        frame_range = (int(frame_range_pair[0]), int(frame_range_pair[1]))

        bone_lengths = {
            CanonicalBoneName(name): float(value)
            for name, value in document.get("bone_lengths", {}).items()
        }

        poses = [
            SkeletonPose(
                frame_index=int(frame["frame"]),
                bone_rotations={
                    CanonicalBoneName(bone_name): _list_to_quaternion(values)
                    for bone_name, values in frame["rotations"].items()
                },
                root_translation=_list_to_vector(frame["root"]),
            )
            for frame in document["frames"]
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise AnimationExportError(f"malformed mcapclip document: {error}") from error

    return SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=fps,
        frame_range=frame_range,
        bone_lengths=bone_lengths,
        poses=poses,
    )


def export_animation(
    clip: SkeletonClip,
    path: Path,
    *,
    name: str = "",
    bone_map: dict[str, str] | None = None,
) -> None:
    """Write ``clip`` to ``path`` as an ``mcapclip`` v1 file."""

    document = write_animation_document(clip, name=name, bone_map=bone_map)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def import_animation(path: Path) -> SkeletonClip:
    """Read an ``mcapclip`` file from ``path``.

    Raises:
        AnimationExportError: The file is missing, malformed, or unsupported.
    """

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AnimationExportError(f"cannot read {path}: {error}") from error

    return read_animation_document(document)


def _vector_to_list(vector: Vector3) -> list[float]:
    return [vector.x, vector.y, vector.z]


def _list_to_vector(values: list[float]) -> Vector3:
    return Vector3(float(values[0]), float(values[1]), float(values[2]))


def _quaternion_to_list(quaternion: Quaternion) -> list[float]:
    return [quaternion.w, quaternion.x, quaternion.y, quaternion.z]


def _list_to_quaternion(values: list[float]) -> Quaternion:
    return Quaternion(
        float(values[0]), float(values[1]), float(values[2]), float(values[3])
    )
