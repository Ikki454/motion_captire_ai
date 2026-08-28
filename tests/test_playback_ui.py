"""End-to-end UI tests for video playback (roadmap Phase 5)."""

from pathlib import Path

from app.ui.main_window import MainWindow


def test_play_button_starts_playback_and_timer(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))

    main_window.timeline.play_button.click()

    assert main_window.controller.is_playing is True
    assert main_window._playback_timer.isActive() is True
    assert main_window.timeline.play_button.isChecked() is True


def test_playback_tick_advances_frame_and_readout(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))
    main_window.timeline.play_button.click()

    main_window._on_playback_tick()

    assert main_window.controller.current_frame_index == 1
    assert "Frame 1 /" in main_window.timeline.position_label.text()
    assert not main_window.video_view.pixmap().isNull()


def test_play_button_second_click_pauses(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))

    main_window.timeline.play_button.click()
    main_window.timeline.play_button.click()

    assert main_window.controller.is_playing is False
    assert main_window._playback_timer.isActive() is False


def test_stop_rewinds_and_pauses(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))
    main_window.timeline.play_button.click()
    main_window._on_playback_tick()
    main_window._on_playback_tick()

    main_window.timeline.stop_button.click()

    assert main_window.controller.is_playing is False
    assert main_window.controller.current_frame_index == 0
    assert main_window._playback_timer.isActive() is False
    assert main_window.timeline.play_button.isChecked() is False


def test_playback_auto_pauses_at_end(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))
    last_index = main_window.controller.frame_count - 1
    main_window.timeline.frame_spinbox.setValue(last_index)
    main_window.timeline.play_button.click()

    main_window._on_playback_tick()

    assert main_window.controller.is_playing is False
    assert main_window._playback_timer.isActive() is False
    assert main_window.timeline.play_button.isChecked() is False
    assert main_window.controller.current_frame_index == last_index


def test_manual_navigation_pauses_playback(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))
    main_window.timeline.play_button.click()

    main_window.timeline.next_button.click()

    assert main_window.controller.is_playing is False
    assert main_window.controller.current_frame_index == 1


def test_arrow_key_during_playback_pauses(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))
    main_window.timeline.play_button.click()

    main_window.next_shortcut.activated.emit()

    assert main_window.controller.is_playing is False
    assert main_window.controller.current_frame_index == 1
