"""End-to-end UI tests for saving and opening a project (roadmap Phase 8)."""

from collections.abc import Callable
from pathlib import Path

from app.plugins.registry import BackendRegistry
from app.ui.main_window import MainWindow

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]
WaitFor = Callable[..., bool]


def test_save_then_open_restores_analysis(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    wait_for: WaitFor,
    sample_video: Path,
    tmp_path: Path,
) -> None:
    window = make_main_window(make_pose_registry(gap_every=4))
    window.load_video(str(sample_video))
    window.detector_panel.analyze_button.click()
    assert wait_for(lambda: window.controller.pose_sequence is not None)
    detected = window.controller.pose_sequence.active_track.detection_count

    project_dir = tmp_path / "session.mcap"
    window._save_project(project_dir)

    assert project_dir.is_dir()
    assert "saved project" in window.status_label.text().lower()

    reopened = make_main_window(make_pose_registry())
    reopened.open_project(project_dir)

    assert "opened project" in reopened.status_label.text().lower()
    assert reopened.controller.pose_sequence is not None
    assert reopened.controller.pose_sequence.active_track.detection_count == detected

    reopened.timeline.frame_spinbox.setValue(2)
    assert not reopened.video_view.pixmap().isNull()


def test_open_bad_directory_reports_error(
    make_main_window: MakeWindow, tmp_path: Path
) -> None:
    window = make_main_window()

    window.open_project(tmp_path / "not-a-project")

    assert "could not open project" in window.status_label.text().lower()


def test_save_without_video_reports_nothing_to_save(
    make_main_window: MakeWindow,
) -> None:
    window = make_main_window()

    window._on_save_project()

    assert "nothing to save" in window.status_label.text().lower()
