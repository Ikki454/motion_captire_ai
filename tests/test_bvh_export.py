"""Tests for BVH export (roadmap Phase 16)."""

from pathlib import Path

import pytest

from app.export.bvh_exporter import export_bvh, write_bvh_document
from app.math.rotations import Quaternion, shortest_arc
from app.models.pose import Vector3
from app.models.skeleton import (
    CANONICAL_SKELETON,
    CanonicalBoneName,
    SkeletonClip,
    SkeletonPose,
)

_NON_ROOT_JOINTS = 17  # 18 canonical joints minus the pelvis root


def _clip(**bone_rotations: Quaternion) -> SkeletonClip:
    bones = CANONICAL_SKELETON.bone_names()
    identity = Quaternion.identity()
    poses = [
        SkeletonPose(
            frame_index=index,
            bone_rotations={
                name: bone_rotations.get(name.value, identity) for name in bones
            },
            root_translation=Vector3(10.0, 20.0, 5.0),
        )
        for index in range(3)
    ]
    return SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=30.0,
        frame_range=(0, 2),
        bone_lengths={name: 1.5 for name in bones},
        poses=poses,
    )


def _lines(document: str) -> list[str]:
    return document.splitlines()


def test_hierarchy_structure() -> None:
    lines = _lines(write_bvh_document(_clip()))

    assert lines[0] == "HIERARCHY"
    assert any(line.strip() == "ROOT pelvis" for line in lines)
    assert sum(1 for line in lines if line.strip().startswith("JOINT")) == _NON_ROOT_JOINTS
    # leaves: head, both wrists, both feet
    assert sum(1 for line in lines if line.strip() == "End Site") == 5


def test_root_has_six_channels_others_three() -> None:
    lines = _lines(write_bvh_document(_clip()))
    channel_lines = [line.strip() for line in lines if line.strip().startswith("CHANNELS")]

    assert channel_lines[0].startswith("CHANNELS 6 Xposition")
    assert all(line.startswith("CHANNELS 3 Zrotation") for line in channel_lines[1:])


def test_motion_header_and_row_width() -> None:
    lines = _lines(write_bvh_document(_clip()))
    motion = lines.index("MOTION")

    assert lines[motion + 1] == "Frames: 3"
    assert lines[motion + 2] == "Frame Time: 0.033333"

    row = lines[motion + 3].split()
    assert len(row) == 6 + 3 * _NON_ROOT_JOINTS
    assert [float(v) for v in row[:3]] == [10.0, 20.0, 5.0]


def test_offsets_are_non_zero_for_real_bones() -> None:
    lines = _lines(write_bvh_document(_clip()))
    offset_lines = [line.strip() for line in lines if line.strip().startswith("OFFSET")]

    # the root offset is zero, but every other bone offset has a magnitude
    non_root = offset_lines[1:]
    assert non_root
    assert all(
        any(abs(float(v)) > 1e-6 for v in line.split()[1:]) for line in non_root
    )


def test_a_known_rotation_lands_in_the_right_joint_and_channel() -> None:
    bend = shortest_arc(Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))  # 90 about Z
    lines = _lines(write_bvh_document(_clip(left_upper_arm=bend)))
    motion = lines.index("MOTION")

    joint_order = ["pelvis"] + [
        line.split()[1]
        for line in lines[:motion]
        if line.strip().startswith("JOINT")
    ]
    # the LEFT_UPPER_ARM bone ends at the left_elbow joint
    elbow_index = joint_order.index("left_elbow")

    row = [float(v) for v in lines[motion + 3].split()]
    z, y, x = row[3 + elbow_index * 3 : 3 + elbow_index * 3 + 3]
    assert z == pytest.approx(90.0, abs=0.5)
    assert y == pytest.approx(0.0, abs=0.5)
    assert x == pytest.approx(0.0, abs=0.5)


def test_export_writes_a_file(tmp_path: Path) -> None:
    path = tmp_path / "clip.bvh"

    export_bvh(_clip(), path)

    text = path.read_text(encoding="utf-8")
    assert text.startswith("HIERARCHY")
    assert "MOTION" in text
    assert text.endswith("\n")


def test_missing_bone_length_falls_back_to_rest_proportions() -> None:
    clip = _clip()
    clip.bone_lengths[CanonicalBoneName.SPINE] = 0.0

    document = write_bvh_document(clip)

    # the chest joint (end of the spine bone) still gets a non-zero offset
    lines = _lines(document)
    chest_index = next(
        i for i, line in enumerate(lines) if line.strip() == "JOINT chest"
    )
    offset = lines[chest_index + 2].strip()
    assert offset.startswith("OFFSET")
    assert any(abs(float(v)) > 1e-6 for v in offset.split()[1:])
