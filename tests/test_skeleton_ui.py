"""End-to-end tests for building the skeleton (roadmap Phase 10)."""

from collections.abc import Callable
from pathlib import Path

from app.plugins.registry import BackendRegistry
from app.ui.main_window import MainWindow

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]
WaitFor = Callable[..., bool]


def _analysed(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> MainWindow:
    window = make_main_window(make_pose_registry())
    window.load_video(str(sample_video))
    window.detector_panel.analyze_button.click()
    assert wait_for(lambda: window.controller.pose_sequence is not None)
    return window


def test_build_skeleton_reports_bones_and_validation(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)

    window.skeleton_panel.build_button.click()

    clip = window.controller.skeleton_clip
    assert clip is not None
    assert len(clip.poses) == clip.frame_range[1] - clip.frame_range[0] + 1
    assert "bones" in window.skeleton_panel.status_label.text().lower()


def test_build_skeleton_is_disabled_without_analysis(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry
) -> None:
    window = make_main_window(make_pose_registry())

    assert not window.skeleton_panel.build_button.isEnabled()

    window.skeleton_panel.build_button.click()
    assert window.controller.skeleton_clip is None


def test_skeleton_survives_save_and_reopen(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)
    window.skeleton_panel.build_button.click()
    solved_frames = len(window.controller.skeleton_clip.poses)

    project_dir = tmp_path / "skel.mcap"
    window._save_project(project_dir)

    reopened = make_main_window(make_pose_registry())
    reopened.open_project(project_dir)

    assert reopened.controller.skeleton_clip is not None
    assert len(reopened.controller.skeleton_clip.poses) == solved_frames


def test_export_animation_writes_a_readable_clip(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    from app.export.animation_export import import_animation

    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)
    window.skeleton_panel.build_button.click()
    solved = len(window.controller.skeleton_clip.poses)

    path = tmp_path / "clip.mcapclip.json"
    window.export_animation(path)

    assert "exported animation" in window.status_label.text().lower()
    restored = import_animation(path)
    assert len(restored.poses) == solved


def test_export_bvh_writes_a_valid_file(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)
    window.skeleton_panel.build_button.click()

    path = tmp_path / "clip.bvh"
    window.export_bvh(path)

    assert "exported bvh" in window.status_label.text().lower()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("HIERARCHY")
    assert "ROOT pelvis" in text
    assert "MOTION" in text


def test_export_bvh_without_a_skeleton_reports_it(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry, tmp_path: Path
) -> None:
    window = make_main_window(make_pose_registry())

    window.export_bvh(tmp_path / "x.bvh")

    assert "could not export bvh" in window.status_label.text().lower()
    assert not (tmp_path / "x.bvh").exists()


def test_export_animation_without_a_skeleton_reports_it(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry, tmp_path: Path
) -> None:
    window = make_main_window(make_pose_registry())

    window.export_animation(tmp_path / "clip.mcapclip.json")

    assert "could not export" in window.status_label.text().lower()
    assert not (tmp_path / "clip.mcapclip.json").exists()


def test_correcting_a_keypoint_invalidates_the_skeleton(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)
    window.skeleton_panel.build_button.click()
    assert window.controller.skeleton_clip is not None

    from app.models.pose import JointName, Vector3

    window.video_view.keypoint_moved.emit(JointName.LEFT_WRIST, Vector3(1.0, 2.0, 0.0))

    assert window.controller.skeleton_clip is None
