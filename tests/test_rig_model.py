"""Tests for the rig data models (roadmap Phase 13)."""

from app.math.coordinates import CoordinateSpace
from app.math.rotations import Quaternion
from app.models.pose import Vector3
from app.models.rig import RetargetMap, Rig, RigClip
from app.models.skeleton import CanonicalBoneName


def test_retarget_map_lookups() -> None:
    retarget_map = RetargetMap(
        rig_id="r",
        bone_map={CanonicalBoneName.SPINE: "Hips"},
        rotation_offsets={CanonicalBoneName.SPINE: Quaternion(0.0, 1.0, 0.0, 0.0)},
    )

    assert retarget_map.rig_bone_for(CanonicalBoneName.SPINE) == "Hips"
    assert retarget_map.rig_bone_for(CanonicalBoneName.HEAD) is None
    assert retarget_map.offset_for(CanonicalBoneName.SPINE) == Quaternion(0.0, 1.0, 0.0, 0.0)
    assert retarget_map.offset_for(CanonicalBoneName.HEAD) == Quaternion.identity()


def test_rig_clip_counts_and_default_space() -> None:
    clip = RigClip(
        rig_id="r",
        fps=24.0,
        frame_range=(0, 1),
        frame_indices=[0, 1],
        bone_order=["Hips", "Head"],
        bone_curves={
            "Hips": [Quaternion.identity(), Quaternion.identity()],
            "Head": [Quaternion.identity(), Quaternion.identity()],
        },
        root_curve=[Vector3(0.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0)],
    )

    assert clip.bone_count == 2
    assert clip.frame_count == 2
    assert clip.space == CoordinateSpace.CANONICAL_WORLD


def test_rig_defaults() -> None:
    rig = Rig(rig_id="r", display_name="R")

    assert rig.up_axis == "Y"
    assert rig.unit_scale == 1.0
