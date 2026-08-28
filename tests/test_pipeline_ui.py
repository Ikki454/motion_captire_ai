"""UI tests for the pipeline sidebar: step gating and the step indicator."""

from collections.abc import Callable
from pathlib import Path

from app.models.pose import JointName, Vector3
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


def test_sections_start_pending(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry
) -> None:
    window = make_main_window(make_pose_registry())

    assert [section.state for section in window._sections] == ["pending"] * 6
    assert not window.skeleton_panel.build_button.isEnabled()
    assert not window.processing_panel.process_button.isEnabled()


def test_loading_a_video_activates_detection(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry, sample_video: Path
) -> None:
    window = make_main_window(make_pose_registry())

    window.load_video(str(sample_video))

    assert window.section_detect.state == "active"
    assert window.detector_panel.analyze_button.isEnabled()
    assert window.skeleton_panel.build_button.isEnabled() is False


def test_pipeline_unlocks_step_by_step(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)

    assert window.section_detect.state == "done"
    assert window.section_skeleton.state == "active"
    assert window.skeleton_panel.build_button.isEnabled()

    window.skeleton_panel.build_button.click()

    assert window.section_skeleton.state == "done"
    assert window.section_rig.state == "active"
    assert window.rig_panel.retarget_button.isEnabled()

    window.rig_panel.retarget_button.click()

    assert window.section_rig.state == "done"


def test_export_actions_gate_on_the_skeleton(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)

    assert not window.export_animation_action.isEnabled()
    assert not window.export_bvh_action.isEnabled()

    window.skeleton_panel.build_button.click()

    assert window.export_animation_action.isEnabled()
    assert window.export_bvh_action.isEnabled()


def test_correcting_a_keypoint_relocks_downstream_steps(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)
    window.skeleton_panel.build_button.click()
    window.rig_panel.retarget_button.click()
    assert window.section_rig.state == "done"

    window.video_view.keypoint_moved.emit(JointName.LEFT_WRIST, Vector3(1.0, 2.0, 0.0))

    assert window.section_skeleton.state == "active"
    assert window.section_rig.state == "pending"
    assert not window.rig_panel.retarget_button.isEnabled()


def test_space_bar_toggles_playback(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))

    main_window.play_pause_shortcut.activated.emit()
    assert main_window.controller.is_playing is True

    main_window.play_pause_shortcut.activated.emit()
    assert main_window.controller.is_playing is False


def test_scrubber_navigates_frames(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))

    main_window.timeline.scrubber.setValue(4)

    assert main_window.controller.current_frame_index == 4
    assert "Frame 4 /" in main_window.timeline.position_label.text()
