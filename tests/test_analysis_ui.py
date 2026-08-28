"""End-to-end UI tests for full-video analysis (roadmap Phase 7)."""

from collections.abc import Callable
from pathlib import Path

from app.plugins.registry import BackendRegistry
from app.ui.main_window import MainWindow

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]
WaitFor = Callable[..., bool]


def _analysis_done(window: MainWindow) -> bool:
    return (
        window.controller.pose_sequence is not None
        and window.detector_panel.progress_bar.isHidden()
    )


def test_analyze_runs_and_overlay_follows_navigation(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = make_main_window(make_pose_registry())
    window.load_video(str(sample_video))

    window.detector_panel.analyze_button.click()

    assert wait_for(lambda: _analysis_done(window))

    sequence = window.controller.pose_sequence
    assert sequence.active_track.detection_count == sequence.frame_count
    assert "pose found in" in window.detector_panel.status_label.text().lower()

    window.timeline.frame_spinbox.setValue(5)
    assert not window.video_view.pixmap().isNull()


def test_analyze_reports_gaps(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = make_main_window(make_pose_registry(gap_every=3))
    window.load_video(str(sample_video))

    window.detector_panel.analyze_button.click()
    assert wait_for(lambda: _analysis_done(window))

    sequence = window.controller.pose_sequence
    assert sequence.active_track.detection_count < sequence.frame_count
    assert not sequence.active_track.has_detection(0)


def test_analyze_progress_bar_shows_during_run(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
) -> None:
    window = make_main_window(make_pose_registry())
    window.load_video(str(sample_video))

    window.detector_panel.analyze_button.click()

    assert not window.detector_panel.progress_bar.isHidden()
    assert not window.detector_panel.cancel_button.isHidden()
    assert not window.detector_panel.analyze_button.isEnabled()

    assert wait_for(lambda: _analysis_done(window))

    assert window.detector_panel.progress_bar.isHidden()
    assert window.detector_panel.analyze_button.isEnabled()


def test_analyze_without_video_is_a_noop(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry
) -> None:
    window = make_main_window(make_pose_registry())

    window.detector_panel.analyze_button.click()

    assert window.controller.pose_sequence is None
    assert window.detector_panel.progress_bar.isHidden()
