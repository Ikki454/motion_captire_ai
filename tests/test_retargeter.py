"""Tests for canonical -> rig retargeting (roadmap Phase 13)."""

import math

from app.math.rotations import Quaternion, shortest_arc
from app.models.pose import Vector3
from app.models.rig import RetargetMap, Rig
from app.models.skeleton import (
    CANONICAL_SKELETON,
    CanonicalBoneName,
    SkeletonClip,
    SkeletonPose,
)
from app.retarget.retargeter import retarget, retarget_issues


def _clip(**bone_rotations: Quaternion) -> SkeletonClip:
    bones = CANONICAL_SKELETON.bone_names()
    identity = Quaternion.identity()
    poses = [
        SkeletonPose(
            frame_index=index,
            bone_rotations={
                name: bone_rotations.get(name.value, identity) for name in bones
            },
            root_translation=Vector3(100.0, 200.0, 0.0),
        )
        for index in (0, 1)
    ]
    return SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=24.0,
        frame_range=(0, 1),
        bone_lengths={name: 1.0 for name in bones},
        poses=poses,
    )


def _rig(unit_scale: float = 1.0) -> tuple[Rig, RetargetMap]:
    rig = Rig(rig_id="test", display_name="Test", unit_scale=unit_scale)
    retarget_map = RetargetMap(
        rig_id="test",
        bone_map={
            CanonicalBoneName.SPINE: "Hips",
            CanonicalBoneName.LEFT_UPPER_ARM: "LeftArm",
            CanonicalBoneName.LEFT_LOWER_ARM: "LeftForeArm",
        },
    )
    return rig, retarget_map


def _angle(quaternion: Quaternion) -> float:
    return 2 * math.acos(min(1.0, abs(quaternion.w)))


def test_maps_canonical_rotation_onto_the_rig_bone() -> None:
    bend = shortest_arc(Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))
    rig, retarget_map = _rig()

    clip = retarget(_clip(left_upper_arm=bend), rig, retarget_map)

    assert clip.rig_id == "test"
    assert clip.bone_order == ["Hips", "LeftArm", "LeftForeArm"]
    assert clip.frame_count == 2
    assert _angle(clip.bone_curves["LeftArm"][0]) == math.pi / 2


def test_rotation_offset_is_pre_applied() -> None:
    offset = shortest_arc(Vector3(0.0, 1.0, 0.0), Vector3(1.0, 0.0, 0.0))
    rig, retarget_map = _rig()
    retarget_map.rotation_offsets[CanonicalBoneName.LEFT_UPPER_ARM] = offset

    clip = retarget(_clip(), rig, retarget_map)

    assert _angle(clip.bone_curves["LeftArm"][0]) == math.pi / 2


def test_root_translation_is_scaled_by_unit_scale() -> None:
    rig, retarget_map = _rig(unit_scale=0.01)

    clip = retarget(_clip(), rig, retarget_map)

    assert clip.root_curve[0] == Vector3(1.0, 2.0, 0.0)


def test_unmapped_bones_are_absent_and_reported() -> None:
    rig, retarget_map = _rig()

    clip = retarget(_clip(), rig, retarget_map)
    issues = retarget_issues(_clip(), retarget_map)

    assert "head" not in clip.bone_curves
    assert issues
    assert "head" in issues[0]


def test_full_coverage_reports_nothing() -> None:
    from app.retarget.rig_registry import build_rig_registry

    _, canonical_map = build_rig_registry().load("canonical")

    assert retarget_issues(_clip(), canonical_map) == []
