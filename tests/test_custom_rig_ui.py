"""End-to-end tests for custom rig profiles (dialog, panel, persistence)."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from app.core.project_controller import ProjectController
from app.models.skeleton import CanonicalBoneName
from app.plugins.registry import BackendRegistry
from app.retarget.armature_import import ArmatureImportError, BoneGroup
from app.ui.main_window import MainWindow
from app.ui.widgets.custom_rig_dialog import CustomRigDialog

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]
WaitFor = Callable[..., bool]

B = CanonicalBoneName
_BONES = ["Hips", "Spine", "Neck", "Head", "LeftArm", "LeftForeArm"]


def _save_button(dialog: CustomRigDialog):
    return dialog.button_box.button(QDialogButtonBox.StandardButton.Save)


# --- the dialog -----------------------------------------------------------


def test_dialog_starts_invalid_and_reports_why(qt_app: QApplication) -> None:
    dialog = CustomRigDialog()

    assert not _save_button(dialog).isEnabled()
    assert "name" in dialog.coverage_label.text().lower()


def test_dialog_needs_a_name_and_at_least_one_bone(qt_app: QApplication) -> None:
    dialog = CustomRigDialog()

    dialog.name_edit.setText("My Rig")
    assert not _save_button(dialog).isEnabled()
    assert "map at least one bone" in dialog.coverage_label.text().lower()

    dialog._combos[B.SPINE].setCurrentText("spine")
    assert _save_button(dialog).isEnabled()
    assert "1 / 17 canonical bones mapped" in dialog.coverage_label.text()


def test_dialog_prefills_from_an_auto_mapping(qt_app: QApplication) -> None:
    dialog = CustomRigDialog(
        bone_names=_BONES,
        mapping={B.SPINE: "Spine", B.HEAD: "Head"},
        display_name="Imported",
    )

    assert dialog.name_edit.text() == "Imported"
    assert dialog.bone_map() == {B.SPINE: "Spine", B.HEAD: "Head"}
    assert "2 / 17 canonical bones mapped" in dialog.coverage_label.text()


def test_dialog_document_matches_the_edited_mapping(qt_app: QApplication) -> None:
    dialog = CustomRigDialog(bone_names=_BONES, display_name="My Rig")
    dialog._combos[B.SPINE].setCurrentText("Spine")
    dialog.unit_scale_spin.setValue(0.01)

    document = dialog.document("my_rig")

    assert document["rig_id"] == "my_rig"
    assert document["display_name"] == "My Rig"
    assert document["unit_scale"] == 0.01
    assert document["bone_map"] == {"spine": "Spine"}


def test_dialog_refuses_to_accept_while_invalid(qt_app: QApplication) -> None:
    dialog = CustomRigDialog()

    dialog.accept()

    assert dialog.result() != int(CustomRigDialog.DialogCode.Accepted)


# --- controller -----------------------------------------------------------


def test_controller_installs_and_lists_a_custom_rig(rig_dir: Path) -> None:
    controller = ProjectController(rig_dir=rig_dir)

    info = controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "my_rig",
            "display_name": "My Rig",
            "bone_map": {"spine": "Spine"},
        }
    )

    assert info.rig_id == "my_rig"
    assert controller.is_custom_rig("my_rig")
    assert not controller.is_custom_rig("mixamo")
    assert "my_rig" in {rig.rig_id for rig in controller.available_rigs()}


def test_controller_reads_an_armature_and_guesses_the_mapping(
    rig_dir: Path, tmp_path: Path
) -> None:
    path = tmp_path / "rig.json"
    path.write_text(
        json.dumps(
            {
                "format": "mcap_armature",
                "version": 1,
                "armature_name": "Armature",
                "bones": [{"name": name, "parent": None} for name in _BONES],
            }
        ),
        encoding="utf-8",
    )

    dump, mapping, groups = ProjectController(rig_dir=rig_dir).read_armature(path)

    assert dump.armature_name == "Armature"
    assert groups == []  # a flat bone list forms no chains
    assert mapping[B.LEFT_UPPER_ARM] == "LeftArm"
    assert mapping[B.LEFT_LOWER_ARM] == "LeftForeArm"


def test_removing_a_rig_clears_a_retarget_that_used_it(rig_dir: Path) -> None:
    controller = ProjectController(rig_dir=rig_dir)
    controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "my_rig",
            "display_name": "My Rig",
            "bone_map": {"spine": "Spine"},
        }
    )
    controller._retargeted_rig_id = "my_rig"

    controller.remove_rig_profile("my_rig")

    assert controller.retargeted_rig_id is None
    assert not controller.is_custom_rig("my_rig")


# --- the panel ------------------------------------------------------------


def test_panel_marks_custom_rigs_and_gates_removal(
    make_main_window: MakeWindow,
) -> None:
    window = make_main_window()

    assert not window.rig_panel.remove_rig_button.isEnabled()

    window.controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "my_rig",
            "display_name": "My Rig",
            "bone_map": {"spine": "Spine"},
        }
    )
    window.rig_panel.set_rigs(window.controller.available_rigs())
    window.rig_panel.select_rig("my_rig")

    assert window.rig_panel.current_rig_id() == "my_rig"
    assert window.rig_panel.remove_rig_button.isEnabled()

    window.rig_panel.select_rig("mixamo")
    assert not window.rig_panel.remove_rig_button.isEnabled()


def test_remove_button_deletes_the_profile(make_main_window: MakeWindow) -> None:
    window = make_main_window()
    window.controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "my_rig",
            "display_name": "My Rig",
            "bone_map": {"spine": "Spine"},
        }
    )
    window.rig_panel.set_rigs(window.controller.available_rigs())
    window.rig_panel.select_rig("my_rig")

    window.rig_panel.remove_rig_button.click()

    assert not window.controller.is_custom_rig("my_rig")
    assert window.rig_panel.rig_combo.findData("my_rig") == -1


def test_import_rejects_a_file_that_is_not_an_armature(
    make_main_window: MakeWindow, tmp_path: Path
) -> None:
    window = make_main_window()
    path = tmp_path / "not_a_rig.json"
    path.write_text('{"format": "something_else", "version": 1}', encoding="utf-8")

    with pytest.raises(ArmatureImportError, match="not an armature file"):
        window.controller.read_armature(path)


# --- retarget + persistence ----------------------------------------------


def _analysed_with_skeleton(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> MainWindow:
    window = make_main_window(make_pose_registry())
    window.load_video(str(sample_video))
    window.detector_panel.analyze_button.click()
    assert wait_for(lambda: window.controller.pose_sequence is not None)
    window.skeleton_panel.build_button.click()
    return window


def test_retarget_onto_a_custom_rig(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed_with_skeleton(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "my_rig",
            "display_name": "My Rig",
            "bone_map": {"spine": "Root", "head": "Skull"},
        }
    )
    window.rig_panel.set_rigs(window.controller.available_rigs())
    window.rig_panel.select_rig("my_rig")

    window.rig_panel.retarget_button.click()

    clip = window.controller.rig_clip
    assert clip is not None
    assert clip.rig_id == "my_rig"
    assert set(clip.bone_order) == {"Root", "Skull"}
    assert "not mapped to the rig" in window.rig_panel.status_label.text()


def test_a_custom_rig_survives_save_and_reopen_elsewhere(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _analysed_with_skeleton(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "my_rig",
            "display_name": "My Rig",
            "bone_map": {"spine": "Root"},
        }
    )
    window.controller.retarget("my_rig")

    project_dir = tmp_path / "custom.mcap"
    window._save_project(project_dir)

    assert (project_dir / "rigs" / "my_rig.json").exists()

    # A different machine: an empty user rig directory.
    elsewhere = ProjectController(rig_dir=tmp_path / "other_home")
    elsewhere.open_project(project_dir)

    try:
        assert "my_rig" in {rig.rig_id for rig in elsewhere.available_rigs()}
        elsewhere.build_skeleton()
        assert elsewhere.retarget("my_rig").bone_order == ["Root"]
    finally:
        elsewhere.close()


def test_built_in_rigs_are_not_copied_into_the_project(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _analysed_with_skeleton(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.controller.retarget("mixamo")

    project_dir = tmp_path / "builtin.mcap"
    window._save_project(project_dir)

    assert not (project_dir / "rigs").exists()


# --- every armature bone is accounted for ---------------------------------


def test_dialog_reports_bones_no_canonical_role_uses(qt_app: QApplication) -> None:
    dialog = CustomRigDialog(
        bone_names=_BONES, mapping={B.SPINE: "Spine"}, display_name="R"
    )

    assert dialog.unused_bones() == ["Hips", "Neck", "Head", "LeftArm", "LeftForeArm"]
    assert "5 of 6 rig bones keep their rest pose" in dialog.unused_label.text()
    # the full list is one hover away, so nothing is hidden
    assert "LeftForeArm" in dialog.unused_label.toolTip()


def test_dialog_unused_list_shrinks_as_rows_are_filled(qt_app: QApplication) -> None:
    dialog = CustomRigDialog(bone_names=_BONES, display_name="R")
    assert len(dialog.unused_bones()) == 6

    dialog._combos[B.NECK].setCurrentText("Neck")

    assert "Neck" not in dialog.unused_bones()
    assert "5 of 6 rig bones keep their rest pose" in dialog.unused_label.text()


def test_dialog_says_so_when_every_rig_bone_is_used(qt_app: QApplication) -> None:
    dialog = CustomRigDialog(
        bone_names=["Spine", "Neck"],
        mapping={B.SPINE: "Spine", B.NECK: "Neck"},
        display_name="R",
    )

    assert dialog.unused_bones() == []
    assert "All 2 rig bones are mapped." in dialog.unused_label.text()


def test_dialog_typed_by_hand_has_no_unused_list(qt_app: QApplication) -> None:
    dialog = CustomRigDialog(display_name="R")

    assert dialog.unused_label.text() == ""


# --- finger groups fold into one attachment row ---------------------------


def _hand_group() -> BoneGroup:
    return BoneGroup(
        root="hand.L",
        members=("hand.L", *(f"f{i}.{p}" for i in range(5) for p in "ab")),
        attaches_to=B.LEFT_LOWER_ARM,
        kind="fingers",
    )


def test_a_finger_group_becomes_one_row_not_eleven(qt_app: QApplication) -> None:
    group = _hand_group()
    dialog = CustomRigDialog(
        bone_names=[*group.members, "forearm.L"],
        mapping={B.LEFT_LOWER_ARM: "forearm.L"},
        groups=[group],
        display_name="R",
    )

    # one attachment row for the whole hand, and it defaults to its root
    assert list(dialog._attachment_combos) == ["left_hand"]
    assert dialog.attachment_points() == {"left_hand": "hand.L"}
    # the eleven finger bones did not become mapping rows
    assert len(dialog._combos) == len(CanonicalBoneName)


def test_the_attachment_point_reaches_the_saved_profile(qt_app: QApplication) -> None:
    group = _hand_group()
    dialog = CustomRigDialog(
        bone_names=[*group.members, "forearm.L"],
        mapping={B.LEFT_LOWER_ARM: "forearm.L"},
        groups=[group],
        display_name="R",
    )

    document = dialog.document("r")

    assert document["attachment_points"] == {"left_hand": "hand.L"}


def test_a_plain_chain_gets_no_attachment_row(qt_app: QApplication) -> None:
    toe = BoneGroup(
        root="toe.L", members=("toe.L",), attaches_to=B.LEFT_FOOT, kind="chain"
    )
    dialog = CustomRigDialog(
        bone_names=["foot.L", "toe.L"],
        mapping={B.LEFT_FOOT: "foot.L"},
        groups=[toe],
        display_name="R",
    )

    assert dialog._attachment_combos == {}
    assert dialog.attachment_points() == {}


def test_unmapped_bones_are_summarised_by_chain(qt_app: QApplication) -> None:
    group = _hand_group()
    dialog = CustomRigDialog(
        bone_names=[*group.members, "forearm.L"],
        mapping={B.LEFT_LOWER_ARM: "forearm.L"},
        groups=[group],
        display_name="R",
    )

    text = dialog.unused_label.text()
    assert "11 of 12 rig bones keep their rest pose" in text
    assert "hand.L (11)" in text


def test_a_retarget_reports_attachment_points_nothing_drives(rig_dir: Path) -> None:
    from app.models.skeleton import CANONICAL_SKELETON, SkeletonClip
    from app.retarget.retargeter import retarget_issues

    controller = ProjectController(rig_dir=rig_dir)
    controller.add_rig_profile(
        {
            "schema_version": 1,
            "rig_id": "handy",
            "display_name": "Handy",
            "bone_map": {bone.value: bone.value for bone in CanonicalBoneName},
            "attachment_points": {"left_hand": "hand.L"},
        }
    )
    rig, retarget_map = controller._rig_registry.load("handy")
    clip = SkeletonClip(
        skeleton=CANONICAL_SKELETON, fps=24.0, frame_range=(0, 0),
        bone_lengths={}, poses=[],
    )

    notes = retarget_issues(clip, retarget_map, rig)

    assert any("not driven by any capture backend yet" in note for note in notes)
    assert any("left_hand" in note for note in notes)
