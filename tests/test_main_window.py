"""Smoke tests for the application shell."""

from app.ui.main_window import MainWindow


def test_window_has_expected_title(main_window: MainWindow) -> None:
    assert main_window.windowTitle() == "AI Motion Capture"


def test_window_exposes_import_button(main_window: MainWindow) -> None:
    assert main_window.import_button.text() == "Import Video"


def test_window_shows_no_video_loaded_status(main_window: MainWindow) -> None:
    assert "no video" in main_window.status_label.text().lower()
