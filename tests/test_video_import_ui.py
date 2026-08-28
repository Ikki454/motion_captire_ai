"""UI-level tests for the video import flow (roadmap Phase 2 and 3)."""

from pathlib import Path

from app.ui.main_window import MainWindow


def test_load_video_updates_status_info_and_frame(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))

    assert "loaded" in main_window.status_label.text().lower()
    assert sample_video.name in main_window.status_label.text()

    info_text = main_window.video_info_label.text()
    assert sample_video.name in info_text
    assert "64×48" in info_text
    assert "fps" in info_text
    assert "frames" in info_text
    # the full multi-line summary is kept as a tooltip
    assert "Resolution:" in main_window.video_info_label.toolTip()

    assert main_window.controller.project.video_metadata is not None
    assert not main_window.video_view.pixmap().isNull()


def test_load_missing_video_shows_error_without_crashing(
    main_window: MainWindow, tmp_path: Path
) -> None:
    main_window.load_video(str(tmp_path / "missing.mp4"))

    assert "could not import" in main_window.status_label.text().lower()
    assert main_window.video_info_label.text() == ""
    assert main_window.video_view.pixmap().isNull()
    assert main_window.controller.project.video_metadata is None
