"""Tests for the mcapclip animation interchange format (roadmap Phase 11)."""

import json
from pathlib import Path

import pytest

from app.export.animation_export import (
    MCAPCLIP_FORMAT,
    MCAPCLIP_VERSION,
    AnimationExportError,
    export_animation,
    import_animation,
    read_animation_document,
    write_animation_document,
)
from app.math.rotations import Quaternion, shortest_arc
from app.models.pose import Vector3
from app.models.skeleton import CANONICAL_SKELETON, CanonicalBoneName, SkeletonClip, SkeletonPose


def _clip() -> SkeletonClip:
    bones = CANONICAL_SKELETON.bone_names()
    spin = shortest_arc(Vector3(0.0, 1.0, 0.0), Vector3(0.3, 0.9, 0.0))

    poses = [
        SkeletonPose(
            frame_index=frame_index,
            bone_rotations={
                name: (spin if name == CanonicalBoneName.SPINE else Quaternion.identity())
                for name in bones
            },
            root_translation=Vector3(10.0 + frame_index, -5.0, 0.0),
        )
        for frame_index in (2, 3, 7)
    ]
    return SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=30.0,
        frame_range=(2, 7),
        bone_lengths={name: 1.0 + index * 0.1 for index, name in enumerate(bones)},
        poses=poses,
    )


def test_document_has_the_expected_header() -> None:
    document = write_animation_document(_clip(), name="person_0")

    assert document["format"] == MCAPCLIP_FORMAT
    assert document["version"] == MCAPCLIP_VERSION
    assert document["name"] == "person_0"
    assert document["coordinate_space"] == "canonical_world"
    assert document["fps"] == 30.0
    assert document["frame_range"] == [2, 7]
    assert len(document["skeleton"]["bones"]) == len(CANONICAL_SKELETON.bones)
    assert document["skeleton"]["bones"][0]["parent"] is None


def test_round_trip_through_a_document() -> None:
    original = _clip()

    restored = read_animation_document(write_animation_document(original))

    assert restored.fps == original.fps
    assert restored.frame_range == original.frame_range
    assert [pose.frame_index for pose in restored.poses] == [2, 3, 7]
    assert restored.bone_lengths[CanonicalBoneName.SPINE] == pytest.approx(1.0)

    posed = restored.poses[0].bone_rotations[CanonicalBoneName.SPINE]
    original_posed = original.poses[0].bone_rotations[CanonicalBoneName.SPINE]
    assert posed.w == pytest.approx(original_posed.w)
    assert posed.z == pytest.approx(original_posed.z)
    assert restored.poses[1].root_translation.x == pytest.approx(13.0)


def test_round_trip_through_a_file(tmp_path: Path) -> None:
    path = tmp_path / "clip.mcapclip.json"

    export_animation(_clip(), path, name="person_0")
    restored = import_animation(path)

    assert restored.frame_range == (2, 7)
    assert len(restored.poses) == 3


def test_wrong_format_is_rejected() -> None:
    with pytest.raises(AnimationExportError, match="not an"):
        read_animation_document({"format": "bvh", "version": 1})


def test_newer_version_is_rejected() -> None:
    document = write_animation_document(_clip())
    document["version"] = 99

    with pytest.raises(AnimationExportError, match="unsupported"):
        read_animation_document(document)


def test_mismatched_bone_set_is_rejected() -> None:
    document = write_animation_document(_clip())
    document["skeleton"]["bones"] = document["skeleton"]["bones"][:-1]

    with pytest.raises(AnimationExportError, match="bone set"):
        read_animation_document(document)


def test_malformed_document_is_rejected() -> None:
    document = write_animation_document(_clip())
    del document["frames"]

    with pytest.raises(AnimationExportError, match="malformed"):
        read_animation_document(document)


def test_import_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AnimationExportError):
        import_animation(tmp_path / "nope.mcapclip.json")


def test_file_is_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "clip.mcapclip.json"
    export_animation(_clip(), path)

    json.loads(path.read_text(encoding="utf-8"))


def test_optional_bone_map_round_trips_and_is_ignored_by_the_skeleton_reader() -> None:
    bone_map = {"spine": "mixamorig:Spine1", "head": "mixamorig:Head"}

    document = write_animation_document(_clip(), bone_map=bone_map)

    assert document["bone_map"] == bone_map
    # a canonical-skeleton reader still works and ignores the map
    restored = read_animation_document(document)
    assert restored.frame_range == (2, 7)


def test_no_bone_map_field_when_none_given() -> None:
    assert "bone_map" not in write_animation_document(_clip())
