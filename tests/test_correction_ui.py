"""End-to-end UI tests for manual keypoint correction (roadmap Phase 9)."""

from collections.abc import Callable
from pathlib import Path

from app.models.pose import JointName, Vector3
from app.plugins.registry import BackendRegistry
from app.ui.main_window import MainWindow

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]
WaitFor = Callable[..., bool]


def _analysed_window(
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


def _select_and_move(window: MainWindow, joint: JointName, position: Vector3) -> None:
    """Mimic the user clicking a joint (which selects it) and dragging it."""

    window.video_view._selected_joint = joint
    window.video_view.keypoint_selected.emit(joint)
    window.video_view.keypoint_moved.emit(joint, position)


def test_edit_toggle_enables_editing_on_the_video_view(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed_window(make_main_window, make_pose_registry, wait_for, sample_video)

    window.correction_panel.edit_toggle.click()

    assert window.video_view._editable is True


def test_moving_a_keypoint_records_an_undoable_correction(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed_window(make_main_window, make_pose_registry, wait_for, sample_video)
    window.timeline.frame_spinbox.setValue(3)

    _select_and_move(window, JointName.LEFT_WRIST, Vector3(99.0, 88.0, 0.0))

    assert window.controller.correction_count == 1
    pose = window.controller.effective_pose_at(3)
    assert pose.joints[JointName.LEFT_WRIST].position == Vector3(99.0, 88.0, 0.0)
    assert window.correction_panel.undo_button.isEnabled()

    window.correction_panel.undo_button.click()
    assert window.controller.correction_count == 0

    window.correction_panel.redo_button.click()
    assert window.controller.correction_count == 1


def test_propagate_fills_frames_between_two_corrected_keyframes(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed_window(make_main_window, make_pose_registry, wait_for, sample_video)

    window.timeline.frame_spinbox.setValue(2)
    _select_and_move(window, JointName.LEFT_WRIST, Vector3(0.0, 0.0, 0.0))
    window.timeline.frame_spinbox.setValue(6)
    _select_and_move(window, JointName.LEFT_WRIST, Vector3(40.0, 0.0, 0.0))

    window.correction_panel.propagate_button.click()

    pose = window.controller.effective_pose_at(4)
    assert pose.joints[JointName.LEFT_WRIST].position == Vector3(20.0, 0.0, 0.0)


def test_corrections_survive_save_and_reopen(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = _analysed_window(make_main_window, make_pose_registry, wait_for, sample_video)
    window.timeline.frame_spinbox.setValue(3)
    _select_and_move(window, JointName.RIGHT_ANKLE, Vector3(7.0, 8.0, 0.0))

    project_dir = tmp_path / "corr.mcap"
    window._save_project(project_dir)

    reopened = make_main_window(make_pose_registry())
    reopened.open_project(project_dir)

    pose = reopened.controller.effective_pose_at(3)
    assert pose.joints[JointName.RIGHT_ANKLE].position == Vector3(7.0, 8.0, 0.0)
