"""Tests for the standalone Blender add-on (roadmap Phase 12).

Only the pure modules (``mcapclip``, ``conversion``) are exercised -- the
``bpy`` layer can only run inside Blender.
"""

import math
from pathlib import Path

import pytest

import blender_addon
from blender_addon.conversion import (
    canonical_to_blender_location,
    canonical_to_blender_quaternion,
    quaternion_multiply,
    rotate_vector,
)
from blender_addon.mcapclip import McapClipError, load_clip, parse_clip

_ADDON_DIR = Path(blender_addon.__file__).parent
_PURE_MODULES = ("mcapclip.py", "conversion.py", "armature_dump.py", "__init__.py")


# --- architecture rules ---------------------------------------------------


def test_no_addon_module_imports_the_app() -> None:
    for source in _ADDON_DIR.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "import app" not in text, source.name
        assert "from app" not in text, source.name


def test_pure_modules_do_not_import_blender() -> None:
    for name in _PURE_MODULES:
        text = (_ADDON_DIR / name).read_text(encoding="utf-8")
        assert "import bpy" not in text, name
        assert "mathutils" not in text, name


def test_addon_imports_without_blender() -> None:
    assert blender_addon.bl_info["category"] == "Import-Export"
    assert callable(blender_addon.register)


# --- coordinate conversion ---------------------------------------------------


def test_location_maps_y_up_to_z_up() -> None:
    assert canonical_to_blender_location(1.0, 2.0, 3.0) == (1.0, -3.0, 2.0)


def test_identity_rotation_stays_identity() -> None:
    converted = canonical_to_blender_quaternion(1.0, 0.0, 0.0, 0.0)

    assert converted == pytest.approx((1.0, 0.0, 0.0, 0.0))


def test_conversion_is_consistent_with_the_vector_map() -> None:
    # A 90 deg rotation about canonical Z takes canonical +X to +Y.
    half = math.sqrt(0.5)
    canonical_rotation = (half, 0.0, 0.0, half)
    blender_rotation = canonical_to_blender_quaternion(*canonical_rotation)

    # Rotating the blender image of +X should give the blender image of +Y.
    blender_x = canonical_to_blender_location(1.0, 0.0, 0.0)
    blender_y = canonical_to_blender_location(0.0, 1.0, 0.0)

    rotated = rotate_vector(blender_rotation, blender_x)
    assert rotated == pytest.approx(blender_y, abs=1e-9)


def test_quaternion_multiply_identity() -> None:
    q = (0.5, 0.5, 0.5, 0.5)
    assert quaternion_multiply((1.0, 0.0, 0.0, 0.0), q) == q


# --- file parsing (interop with the app's exporter) ------------------------


def _exported_file(tmp_path: Path) -> Path:
    from app.export.animation_export import export_animation
    from app.math.rotations import Quaternion
    from app.models.pose import Vector3
    from app.models.skeleton import CANONICAL_SKELETON, SkeletonClip, SkeletonPose

    bones = CANONICAL_SKELETON.bone_names()
    clip = SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=24.0,
        frame_range=(0, 2),
        bone_lengths={name: 1.0 for name in bones},
        poses=[
            SkeletonPose(
                frame_index=index,
                bone_rotations={name: Quaternion.identity() for name in bones},
                root_translation=Vector3(float(index), 1.0, 2.0),
            )
            for index in (0, 1, 2)
        ],
    )
    path = tmp_path / "clip.mcapclip.json"
    export_animation(clip, path, name="person_0")
    return path


def test_reads_a_file_produced_by_the_app(tmp_path: Path) -> None:
    clip = load_clip(_exported_file(tmp_path))

    assert clip.name == "person_0"
    assert clip.fps == 24.0
    assert clip.frame_range == (0, 2)
    assert clip.coordinate_space == "canonical_world"
    assert len(clip.frames) == 3
    assert clip.bones[0].parent is None
    assert clip.frames[1].root == (1.0, 1.0, 2.0)
    assert clip.frames[0].rotations[clip.bone_names[0]] == (1.0, 0.0, 0.0, 0.0)
    assert clip.bone_map is None


def test_reads_the_optional_bone_map(tmp_path: Path) -> None:
    from app.export.animation_export import export_animation
    from app.math.rotations import Quaternion
    from app.models.pose import Vector3
    from app.models.skeleton import CANONICAL_SKELETON, SkeletonClip, SkeletonPose

    bones = CANONICAL_SKELETON.bone_names()
    clip = SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=24.0,
        frame_range=(0, 0),
        bone_lengths={name: 1.0 for name in bones},
        poses=[
            SkeletonPose(
                frame_index=0,
                bone_rotations={name: Quaternion.identity() for name in bones},
                root_translation=Vector3(0.0, 0.0, 0.0),
            )
        ],
    )
    path = tmp_path / "clip.mcapclip.json"
    export_animation(clip, path, bone_map={"spine": "mixamorig:Spine1"})

    parsed = load_clip(path)
    assert parsed.bone_map == {"spine": "mixamorig:Spine1"}


def test_rejects_a_non_mcapclip_document() -> None:
    with pytest.raises(McapClipError, match="not an mcapclip"):
        parse_clip({"format": "bvh", "version": 1})


def test_rejects_a_newer_version() -> None:
    with pytest.raises(McapClipError, match="unsupported"):
        parse_clip({"format": "mcapclip", "version": 99})


def test_rejects_a_malformed_document() -> None:
    with pytest.raises(McapClipError, match="malformed"):
        parse_clip({"format": "mcapclip", "version": 1, "fps": 24.0})


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(McapClipError):
        load_clip(tmp_path / "nope.mcapclip.json")


# --- armature dump (feeds the app's "Import rig...") -------------------------


def test_dump_document_is_readable_by_the_app() -> None:
    from app.retarget.armature_import import auto_map, parse_armature_dump
    from blender_addon.armature_dump import build_dump_document

    document = build_dump_document(
        "Armature",
        [("Hips", None), ("Spine", "Hips"), ("LeftArm", "Spine")],
        up_axis="Z",
        unit_scale=1.0,
    )

    dump = parse_armature_dump(document)

    assert dump.armature_name == "Armature"
    assert dump.bone_names == ("Hips", "Spine", "LeftArm")
    assert dump.up_axis == "Z"
    assert auto_map(dump.bone_names)


def test_written_dump_round_trips_through_a_file(tmp_path: Path) -> None:
    from app.retarget.armature_import import load_armature_dump
    from blender_addon.armature_dump import build_dump_document, write_dump

    path = tmp_path / "rig.json"
    write_dump(path, build_dump_document("Rig", [("Spine", None)]))

    assert load_armature_dump(path).bone_names == ("Spine",)
