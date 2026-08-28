"""End-to-end tests for retargeting via the UI (roadmap Phase 13)."""

from collections.abc import Callable
from pathlib import Path

from app.export.animation_export import import_animation
from app.plugins.registry import BackendRegistry
from app.ui.main_window import MainWindow

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]
WaitFor = Callable[..., bool]


def _skeleton_window(
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


def test_rig_panel_lists_bundled_rigs(make_main_window: MakeWindow) -> None:
    window = make_main_window()

    labels = [
        window.rig_panel.rig_combo.itemText(i)
        for i in range(window.rig_panel.rig_combo.count())
    ]

    assert "Mixamo" in labels
    # retargeting is disabled until a skeleton has been solved
    assert not window.rig_panel.retarget_button.isEnabled()


def test_retarget_reports_coverage(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _skeleton_window(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.rig_panel.rig_combo.setCurrentIndex(
        [
            window.rig_panel.rig_combo.itemData(i)
            for i in range(window.rig_panel.rig_combo.count())
        ].index("mixamo")
    )

    window.rig_panel.retarget_button.click()

    assert window.controller.rig_clip is not None
    assert window.controller.retargeted_rig_id == "mixamo"
    assert "mixamo" in window.rig_panel.status_label.text().lower()


def test_retarget_is_disabled_without_skeleton(make_main_window: MakeWindow) -> None:
    window = make_main_window()

    assert not window.rig_panel.retarget_button.isEnabled()

    window.rig_panel.retarget_button.click()
    assert window.controller.rig_clip is None


def test_export_after_retarget_embeds_the_bone_map(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _skeleton_window(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.controller.retarget("mixamo")

    path = tmp_path / "clip.mcapclip.json"
    window.export_animation(path)

    import json

    document = json.loads(path.read_text())
    assert document["bone_map"]["left_upper_arm"] == "mixamorig:LeftArm"
    # still a valid canonical mcapclip
    assert len(import_animation(path).poses) == len(window.controller.skeleton_clip.poses)


def test_rig_clip_survives_save_and_reopen(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _skeleton_window(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.controller.retarget("unity_humanoid")
    bones = window.controller.rig_clip.bone_count

    project_dir = tmp_path / "rig.mcap"
    window._save_project(project_dir)

    reopened = make_main_window(make_pose_registry())
    reopened.open_project(project_dir)

    assert reopened.controller.rig_clip is not None
    assert reopened.controller.retargeted_rig_id == "unity_humanoid"
    assert reopened.controller.rig_clip.bone_count == bones


def test_building_the_skeleton_again_drops_the_rig_clip(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _skeleton_window(
        make_main_window, make_pose_registry, wait_for, sample_video
    )
    window.controller.retarget("mixamo")
    assert window.controller.rig_clip is not None

    window.skeleton_panel.build_button.click()

    assert window.controller.rig_clip is None
