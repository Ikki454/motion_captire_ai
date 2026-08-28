"""Tests for armature import and canonical-bone auto-mapping."""

import json
from pathlib import Path

import pytest

from app.models.skeleton import CanonicalBoneName
from app.retarget.armature_import import (
    ArmatureImportError,
    BoneGroup,
    attachment_points_for,
    auto_map,
    build_profile_document,
    detect_bone_groups,
    load_armature_dump,
    parse_armature_dump,
)

B = CanonicalBoneName

MIXAMO = [
    "mixamorig:Hips",
    "mixamorig:Spine",
    "mixamorig:Spine1",
    "mixamorig:Neck",
    "mixamorig:Head",
    "mixamorig:LeftShoulder",
    "mixamorig:LeftArm",
    "mixamorig:LeftForeArm",
    "mixamorig:LeftHand",
    "mixamorig:RightShoulder",
    "mixamorig:RightArm",
    "mixamorig:RightForeArm",
    "mixamorig:LeftUpLeg",
    "mixamorig:LeftLeg",
    "mixamorig:LeftFoot",
    "mixamorig:LeftToeBase",
    "mixamorig:RightUpLeg",
    "mixamorig:RightLeg",
    "mixamorig:RightFoot",
]
RIGIFY = [
    "spine",
    "spine.004",
    "neck",
    "head",
    "shoulder.L",
    "upper_arm.L",
    "forearm.L",
    "hand.L",
    "thigh.L",
    "shin.L",
    "foot.L",
    "shoulder.R",
    "upper_arm.R",
    "forearm.R",
    "thigh.R",
    "shin.R",
    "foot.R",
]
UNREAL = [
    "pelvis",
    "spine_01",
    "neck_01",
    "head",
    "clavicle_l",
    "upperarm_l",
    "lowerarm_l",
    "hand_l",
    "thigh_l",
    "calf_l",
    "foot_l",
    "clavicle_r",
    "upperarm_r",
    "lowerarm_r",
    "thigh_r",
    "calf_r",
    "foot_r",
]


def _dump_document(bones: list[str]) -> dict:
    return {
        "format": "mcap_armature",
        "version": 1,
        "armature_name": "rig",
        "bones": [{"name": name, "parent": None} for name in bones],
    }


# --- auto mapping ---------------------------------------------------------


@pytest.mark.parametrize(
    ("bones", "upper_arm", "lower_arm", "upper_leg", "lower_leg"),
    [
        (MIXAMO, "mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftUpLeg", "mixamorig:LeftLeg"),
        (RIGIFY, "upper_arm.L", "forearm.L", "thigh.L", "shin.L"),
        (UNREAL, "upperarm_l", "lowerarm_l", "thigh_l", "calf_l"),
    ],
    ids=["mixamo", "rigify", "unreal"],
)
def test_auto_map_handles_common_naming_conventions(
    bones: list[str],
    upper_arm: str,
    lower_arm: str,
    upper_leg: str,
    lower_leg: str,
) -> None:
    mapping = auto_map(bones)

    assert mapping[B.LEFT_UPPER_ARM] == upper_arm
    assert mapping[B.LEFT_LOWER_ARM] == lower_arm
    assert mapping[B.LEFT_UPPER_LEG] == upper_leg
    assert mapping[B.LEFT_LOWER_LEG] == lower_leg
    assert mapping[B.NECK] in bones
    assert mapping[B.HEAD] in bones


def test_auto_map_covers_both_sides_and_the_spine() -> None:
    mapping = auto_map(MIXAMO)

    assert mapping[B.RIGHT_UPPER_ARM] == "mixamorig:RightArm"
    assert mapping[B.RIGHT_FOOT] == "mixamorig:RightFoot"
    assert mapping[B.LEFT_CLAVICLE] == "mixamorig:LeftShoulder"
    assert mapping[B.SPINE] == "mixamorig:Spine"


def test_auto_map_ignores_hands_fingers_and_toes() -> None:
    mapped = set(auto_map(MIXAMO).values())

    assert "mixamorig:LeftHand" not in mapped
    assert "mixamorig:LeftToeBase" not in mapped


def test_auto_map_leaves_hips_unmapped_on_real_rigs() -> None:
    # Real rigs have no pelvis-to-thigh connector bone; that is expected.
    mapping = auto_map(MIXAMO)

    assert B.LEFT_HIP not in mapping
    assert B.RIGHT_HIP not in mapping


def test_auto_map_never_reuses_the_same_rig_bone() -> None:
    mapping = auto_map(MIXAMO + RIGIFY + UNREAL)

    assert len(set(mapping.values())) == len(mapping)


def test_auto_map_on_unknown_names_returns_nothing() -> None:
    assert auto_map(["alpha", "beta", "gamma"]) == {}


def test_auto_map_is_deterministic() -> None:
    assert auto_map(MIXAMO) == auto_map(MIXAMO)


# --- dump parsing ---------------------------------------------------------


def test_parse_dump_reads_bone_names() -> None:
    dump = parse_armature_dump(_dump_document(["root", "spine"]))

    assert dump.bone_names == ("root", "spine")
    assert dump.armature_name == "rig"


def test_parse_dump_accepts_plain_string_bones() -> None:
    dump = parse_armature_dump(
        {"format": "mcap_armature", "version": 1, "bones": ["a", "b"]}
    )

    assert dump.bone_names == ("a", "b")


def test_parse_dump_rejects_a_foreign_file() -> None:
    with pytest.raises(ArmatureImportError, match="not an armature file"):
        parse_armature_dump({"format": "something_else", "version": 1, "bones": []})


def test_parse_dump_rejects_a_newer_version() -> None:
    document = _dump_document(["root"])
    document["version"] = 99

    with pytest.raises(ArmatureImportError, match="unsupported"):
        parse_armature_dump(document)


def test_parse_dump_rejects_an_empty_armature() -> None:
    with pytest.raises(ArmatureImportError, match="no bones"):
        parse_armature_dump(_dump_document([]))


def test_load_dump_reports_an_unreadable_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ArmatureImportError, match="cannot read"):
        load_armature_dump(path)


def test_load_dump_round_trips_a_written_file(tmp_path: Path) -> None:
    path = tmp_path / "rig.json"
    path.write_text(json.dumps(_dump_document(MIXAMO)), encoding="utf-8")

    dump = load_armature_dump(path)

    assert dump.bone_names == tuple(MIXAMO)
    assert dump.source == path


# --- profile building -----------------------------------------------------


def test_build_profile_document_is_loadable_by_the_registry() -> None:
    document = build_profile_document(
        "my_rig", "My Rig", auto_map(MIXAMO), unit_scale=0.01
    )

    assert document["rig_id"] == "my_rig"
    assert document["schema_version"] == 1
    assert document["unit_scale"] == 0.01
    assert document["bone_map"]["left_upper_arm"] == "mixamorig:LeftArm"


def test_build_profile_document_drops_blank_bone_names() -> None:
    document = build_profile_document(
        "r", "R", {B.SPINE: "spine", B.HEAD: "  ", B.NECK: ""}
    )

    assert document["bone_map"] == {"spine": "spine"}


# --- hierarchy: placing the hips ------------------------------------------

# A rig whose thighs hang off their own side bone, however it is spelled.
_SIDED_PELVIS_PARENTS = {
    "pelvis": None,
    "plevis.L": "pelvis",
    "thigh.L": "plevis.L",
    "plevis.R": "pelvis",
    "thigh.R": "plevis.R",
}
# A rig whose thighs share one pelvis bone (Mixamo, Unreal).
_SHARED_PELVIS_PARENTS = {
    "Hips": None,
    "LeftUpLeg": "Hips",
    "RightUpLeg": "Hips",
}


def test_dump_keeps_the_bone_hierarchy() -> None:
    document = {
        "format": "mcap_armature",
        "version": 1,
        "bones": [
            {"name": "root", "parent": None},
            {"name": "spine", "parent": "root"},
        ],
    }

    dump = parse_armature_dump(document)

    assert dump.parents == {"root": None, "spine": "root"}


def test_hips_are_placed_from_the_hierarchy_whatever_they_are_called() -> None:
    # "plevis" is a misspelling no name rule can match; the hierarchy can.
    mapping = auto_map(list(_SIDED_PELVIS_PARENTS), _SIDED_PELVIS_PARENTS)

    assert mapping[B.LEFT_HIP] == "plevis.L"
    assert mapping[B.RIGHT_HIP] == "plevis.R"


def test_a_pelvis_shared_by_both_legs_is_not_a_hip() -> None:
    mapping = auto_map(list(_SHARED_PELVIS_PARENTS), _SHARED_PELVIS_PARENTS)

    assert B.LEFT_HIP not in mapping
    assert B.RIGHT_HIP not in mapping
    assert "Hips" not in mapping.values()


def test_hierarchy_never_overrides_a_named_hip() -> None:
    parents = {"pelvis": None, "hip.L": "pelvis", "thigh.L": "hip.L"}

    mapping = auto_map(list(parents), parents)

    assert mapping[B.LEFT_HIP] == "hip.L"


def test_auto_map_without_a_hierarchy_is_unchanged() -> None:
    assert B.LEFT_HIP not in auto_map(list(_SIDED_PELVIS_PARENTS))


def test_a_pelvis_named_bone_is_matched_by_name() -> None:
    mapping = auto_map(["pelvis_l", "pelvis_r"])

    assert mapping[B.LEFT_HIP] == "pelvis_l"
    assert mapping[B.RIGHT_HIP] == "pelvis_r"


# --- extra bone chains (fingers, toes) ------------------------------------

# A hand with five three-bone finger chains, plus a toe and a spine segment.
_RIG_WITH_EXTRAS = {
    "root": None,
    "spine.001": "root",
    "spine.002": "spine.001",
    "spine.003": "spine.002",
    "neck": "spine.003",
    "upper_arm.L": "spine.001",
    "forearm.L": "upper_arm.L",
    "hand.L": "forearm.L",
    "thigh.L": "root",
    "shin.L": "thigh.L",
    "foot.L": "shin.L",
    "toe.L": "foot.L",
}
for _finger in range(5):
    _RIG_WITH_EXTRAS[f"f{_finger}.a"] = "hand.L"
    _RIG_WITH_EXTRAS[f"f{_finger}.b"] = f"f{_finger}.a"


def _groups_of(parents: dict[str, str | None]) -> dict[str, BoneGroup]:
    names = list(parents)
    mapping = auto_map(names, parents)
    return {g.root: g for g in detect_bone_groups(names, parents, mapping)}


def test_a_hand_with_several_chains_is_detected_as_fingers() -> None:
    groups = _groups_of(_RIG_WITH_EXTRAS)

    hand = groups["hand.L"]
    assert hand.is_fingers
    assert hand.attaches_to == B.LEFT_LOWER_ARM
    # the hand itself plus 5 fingers x 2 bones
    assert len(hand.members) == 11


def test_a_single_bone_chain_is_not_fingers() -> None:
    groups = _groups_of(_RIG_WITH_EXTRAS)

    assert groups["toe.L"].kind == "chain"
    assert groups["toe.L"].members == ("toe.L",)
    assert groups["toe.L"].attaches_to == B.LEFT_FOOT


def test_a_group_stops_at_the_next_mapped_bone() -> None:
    # spine.002 -> spine.003 -> neck, and neck is mapped, so it is excluded.
    groups = _groups_of(_RIG_WITH_EXTRAS)

    assert groups["spine.002"].members == ("spine.002", "spine.003")


def test_bones_above_the_skeleton_are_not_grouped() -> None:
    groups = _groups_of(_RIG_WITH_EXTRAS)

    assert "root" not in groups


def test_every_bone_is_mapped_grouped_or_above_the_skeleton() -> None:
    names = list(_RIG_WITH_EXTRAS)
    mapping = auto_map(names, _RIG_WITH_EXTRAS)
    groups = detect_bone_groups(names, _RIG_WITH_EXTRAS, mapping)

    accounted = set(mapping.values())
    for group in groups:
        accounted.update(group.members)

    assert set(names) - accounted == {"root"}


def test_attachment_points_only_cover_finger_groups() -> None:
    names = list(_RIG_WITH_EXTRAS)
    mapping = auto_map(names, _RIG_WITH_EXTRAS)
    groups = detect_bone_groups(names, _RIG_WITH_EXTRAS, mapping)

    assert attachment_points_for(groups) == {"left_hand": "hand.L"}


def test_profile_document_carries_the_attachment_points() -> None:
    document = build_profile_document(
        "r", "R", {B.SPINE: "spine.001"}, attachment_points={"left_hand": "hand.L"}
    )

    assert document["attachment_points"] == {"left_hand": "hand.L"}


def test_profile_document_omits_empty_attachment_points() -> None:
    document = build_profile_document("r", "R", {B.SPINE: "s"}, attachment_points={})

    assert "attachment_points" not in document


def test_the_armature_root_is_never_taken_for_a_hip() -> None:
    # A one-legged rig slips past the shared-parent check; the root guard
    # is what stops "root" becoming a hip.
    parents = {"root": None, "thigh.L": "root", "shin.L": "thigh.L"}

    mapping = auto_map(list(parents), parents)

    assert B.LEFT_HIP not in mapping
    assert "root" not in mapping.values()
