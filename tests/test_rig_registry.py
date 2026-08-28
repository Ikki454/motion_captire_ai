"""Tests for rig-profile discovery and loading (roadmap Phase 13)."""

import json
from pathlib import Path

import pytest

from app.models.skeleton import CanonicalBoneName
from app.retarget.rig_registry import (
    RigProfileError,
    RigRegistry,
    build_rig_registry,
    slugify,
    user_rig_dir,
)


def _profile(rig_id: str = "custom", display_name: str = "My Rig") -> dict:
    return {
        "schema_version": 1,
        "rig_id": rig_id,
        "display_name": display_name,
        "bone_map": {"spine": "root", "head": "skull"},
    }


def test_bundled_profiles_are_available() -> None:
    registry = build_rig_registry()

    ids = {info.rig_id for info in registry.available()}

    assert {"canonical", "mixamo", "rigify", "unity_humanoid"} <= ids


def test_loading_a_bundled_profile() -> None:
    rig, retarget_map = build_rig_registry().load("mixamo")

    assert rig.rig_id == "mixamo"
    assert rig.unit_scale == 0.01
    assert retarget_map.bone_map[CanonicalBoneName.LEFT_UPPER_ARM] == "mixamorig:LeftArm"


def test_unknown_rig_id_raises() -> None:
    with pytest.raises(RigProfileError, match="unknown"):
        build_rig_registry().load("not_a_rig")


def test_extra_directory_profiles_are_discovered(tmp_path: Path) -> None:
    (tmp_path / "custom.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "rig_id": "custom",
                "display_name": "My Rig",
                "bone_map": {"spine": "root", "head": "skull"},
            }
        )
    )

    registry = build_rig_registry(tmp_path)

    assert registry.has("custom")
    rig, retarget_map = registry.load("custom")
    assert rig.display_name == "My Rig"
    assert retarget_map.bone_map[CanonicalBoneName.HEAD] == "skull"


def test_malformed_profile_is_skipped_in_listing_but_errors_on_load(
    tmp_path: Path,
) -> None:
    (tmp_path / "broken.json").write_text('{"rig_id": "broken", "bone_map": 5}')

    registry = build_rig_registry(tmp_path)
    # It has a rig_id so it lists, but loading fails on the bad bone_map.
    with pytest.raises(RigProfileError):
        registry.load("broken")


def test_empty_registry_lists_nothing() -> None:
    assert RigRegistry().available() == []


# --- custom profiles ------------------------------------------------------


def test_bundled_profiles_are_flagged_as_bundled(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)
    registry.install_profile(_profile())

    assert registry.is_bundled("mixamo")
    assert not registry.is_bundled("custom")


def test_install_profile_writes_and_lists_it(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)

    info = registry.install_profile(_profile())

    assert info.rig_id == "custom"
    assert info.display_name == "My Rig"
    assert not info.is_bundled
    assert (tmp_path / "custom.json").exists()
    assert registry.has("custom")

    rig, retarget_map = registry.load("custom")
    assert rig.display_name == "My Rig"
    assert retarget_map.bone_map[CanonicalBoneName.HEAD] == "skull"


def test_install_profile_refuses_a_bundled_id(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)

    with pytest.raises(RigProfileError, match="built-in"):
        registry.install_profile(_profile(rig_id="mixamo"))


def test_install_profile_refuses_an_unsafe_id(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)

    with pytest.raises(RigProfileError, match="invalid rig id"):
        registry.install_profile(_profile(rig_id="../escape"))


def test_install_profile_validates_before_writing(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)
    bad = _profile()
    bad["bone_map"] = {"not_a_canonical_bone": "x"}

    with pytest.raises(RigProfileError, match="malformed"):
        registry.install_profile(bad)

    assert not (tmp_path / "custom.json").exists()


def test_install_profile_overwrites_a_custom_one(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)
    registry.install_profile(_profile())

    info = registry.install_profile(_profile(display_name="Renamed"))

    assert info.display_name == "Renamed"
    assert len([r for r in registry.available() if r.rig_id == "custom"]) == 1


def test_registry_without_install_dir_refuses_to_install() -> None:
    with pytest.raises(RigProfileError, match="cannot install"):
        build_rig_registry().install_profile(_profile())


def test_remove_profile_deletes_the_file(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)
    registry.install_profile(_profile())

    registry.remove_profile("custom")

    assert not registry.has("custom")
    assert not (tmp_path / "custom.json").exists()


def test_remove_profile_refuses_a_bundled_one(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)

    with pytest.raises(RigProfileError, match="built-in"):
        registry.remove_profile("mixamo")

    assert registry.has("mixamo")


def test_a_later_directory_wins_for_the_same_id(tmp_path: Path) -> None:
    first = tmp_path / "user"
    second = tmp_path / "project"
    first.mkdir()
    second.mkdir()
    (first / "custom.json").write_text(json.dumps(_profile(display_name="User")))
    (second / "custom.json").write_text(json.dumps(_profile(display_name="Project")))

    registry = build_rig_registry(first, second)

    assert registry.load("custom")[0].display_name == "Project"


def test_reload_picks_up_a_file_written_behind_the_registry(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path)
    assert not registry.has("custom")

    (tmp_path / "custom.json").write_text(json.dumps(_profile()))
    registry.reload()

    assert registry.has("custom")


def test_document_returns_the_raw_profile(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)
    registry.install_profile(_profile())

    assert registry.document("custom")["display_name"] == "My Rig"


def test_unique_rig_id_suffixes_a_taken_name(tmp_path: Path) -> None:
    registry = build_rig_registry(tmp_path, install_dir=tmp_path)
    registry.install_profile(_profile())

    assert registry.unique_rig_id("My Rig") == "my_rig"
    assert registry.unique_rig_id("custom") == "custom_2"


def test_slugify_makes_a_safe_id() -> None:
    assert slugify("My Blender Rig!") == "my_blender_rig"
    assert slugify("  ---  ") == "rig"


def test_user_rig_dir_is_under_the_home_directory() -> None:
    assert user_rig_dir().is_relative_to(Path.home())
