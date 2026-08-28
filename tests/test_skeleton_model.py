"""Tests for the canonical skeleton definition (roadmap Phase 10)."""

import pytest

from app.math.vectors import length
from app.models.skeleton import CANONICAL_SKELETON, CanonicalBoneName


def test_bones_are_ordered_parent_first() -> None:
    seen: set[CanonicalBoneName] = set()

    for bone in CANONICAL_SKELETON.bones:
        if bone.parent is not None:
            assert bone.parent in seen, f"{bone.name} precedes its parent"
        seen.add(bone.name)


def test_every_bone_joint_has_a_rest_position() -> None:
    for bone in CANONICAL_SKELETON.bones:
        assert bone.parent_joint in CANONICAL_SKELETON.rest_positions
        assert bone.child_joint in CANONICAL_SKELETON.rest_positions


def test_rest_directions_are_unit_length() -> None:
    for bone in CANONICAL_SKELETON.bones:
        direction = CANONICAL_SKELETON.rest_direction(bone)
        assert length(direction) == pytest.approx(1.0, abs=1e-6)


def test_spine_rest_direction_points_up() -> None:
    spine = CANONICAL_SKELETON.bone(CanonicalBoneName.SPINE)
    direction = CANONICAL_SKELETON.rest_direction(spine)

    assert direction.y > 0.9  # canonical world is y-up


def test_bone_lookup_by_name() -> None:
    left_foot = CANONICAL_SKELETON.bone(CanonicalBoneName.LEFT_FOOT)

    assert left_foot.parent == CanonicalBoneName.LEFT_LOWER_LEG
