"""End-to-end UI tests for single-frame pose detection (roadmap Phase 6)."""

from collections.abc import Callable
from pathlib import Path

import pytest

from app.plugins.registry import BackendRegistry
from app.ui.main_window import MainWindow

MakeWindow = Callable[..., MainWindow]
MakeRegistry = Callable[..., BackendRegistry]


def test_detect_button_shows_overlay_and_keypoint_count(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    sample_video: Path,
) -> None:
    window = make_main_window(make_pose_registry())
    window.load_video(str(sample_video))
    plain = window.video_view.pixmap().toImage()

    window.detector_panel.detect_button.click()

    assert window.video_view.pixmap().toImage() != plain
    assert "18 / 18 keypoints" in window.detector_panel.status_label.text()


def test_navigation_clears_the_overlay(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    sample_video: Path,
) -> None:
    window = make_main_window(make_pose_registry())
    window.load_video(str(sample_video))
    window.detector_panel.detect_button.click()
    with_overlay = window.video_view.pixmap().toImage()

    window.timeline.next_button.click()

    assert window.video_view.pixmap().toImage() != with_overlay


def test_no_pose_reports_clearly(
    make_main_window: MakeWindow,
    make_pose_registry: MakeRegistry,
    sample_video: Path,
) -> None:
    window = make_main_window(make_pose_registry(find_pose=False))
    window.load_video(str(sample_video))

    window.detector_panel.detect_button.click()

    assert "no pose detected" in window.detector_panel.status_label.text().lower()


def test_unavailable_backend_disables_detection(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry
) -> None:
    window = make_main_window(make_pose_registry(available=False))

    assert not window.detector_panel.detect_button.isEnabled()
    assert "test: disabled" in window.detector_panel.status_label.text()


def test_detect_without_video_is_a_noop(
    make_main_window: MakeWindow, make_pose_registry: MakeRegistry
) -> None:
    window = make_main_window(make_pose_registry())

    window.detector_panel.detect_button.click()

    assert window.video_view.pixmap().isNull()


@pytest.mark.usefixtures("qt_app")
def test_real_mediapipe_end_to_end(person_video: Path) -> None:
    pytest.importorskip("mediapipe")

    from app.pose.backends.mediapipe_model import default_model_path

    if not default_model_path().exists():
        pytest.skip("pose model not downloaded")

    window = MainWindow()
    try:
        window.load_video(str(person_video))
        window.detector_panel.detect_button.click()
        status = window.detector_panel.status_label.text().lower()
        assert "keypoints" in status or "no pose" in status
    finally:
        window.close()
