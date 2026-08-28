"""End-to-end tests for the processing panel (roadmap Phase 14)."""

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
    *,
    gap_every: int = 0,
) -> MainWindow:
    window = make_main_window(make_pose_registry(gap_every=gap_every))
    window.load_video(str(sample_video))
    window.detector_panel.analyze_button.click()
    assert wait_for(lambda: window.controller.pose_sequence is not None)
    return window


def test_process_runs_selected_passes_and_reports(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(
        make_main_window, make_pose_registry, wait_for, sample_video, gap_every=4
    )
    window.processing_panel.fill_gaps_check.setChecked(True)
    window.processing_panel.smooth_check.setChecked(True)

    window.processing_panel.process_button.click()

    assert window.controller.processed is True
    text = window.processing_panel.status_label.text().lower()
    assert "filled gaps" in text
    assert "smoothed" in text


def test_processed_sequence_feeds_the_skeleton(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = _analysed(
        make_main_window, make_pose_registry, wait_for, sample_video, gap_every=4
    )
    window.processing_panel.fill_gaps_check.setChecked(True)
    window.processing_panel.process_button.click()

    window.skeleton_panel.build_button.click()

    assert window.controller.skeleton_clip is not None
    # a filled-gap frame now has a solved pose
    assert window.controller.effective_pose_at(4) is not None


def test_correcting_a_keypoint_drops_the_processed_sequence(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    from app.models.pose import JointName, Vector3

    window = _analysed(make_main_window, make_pose_registry, wait_for, sample_video)
    window.processing_panel.smooth_check.setChecked(True)
    window.processing_panel.process_button.click()
    assert window.controller.processed is True

    window.video_view.keypoint_moved.emit(JointName.LEFT_WRIST, Vector3(1.0, 2.0, 0.0))

    assert window.controller.processed is False


def test_process_is_disabled_without_analysis(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry
) -> None:
    window = make_main_window(make_pose_registry())

    assert not window.processing_panel.process_button.isEnabled()

    window.processing_panel.process_button.click()
    assert window.controller.processed is False
