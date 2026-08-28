"""End-to-end UI tests for frame navigation (roadmap Phase 4)."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from app.ui.main_window import MainWindow


def test_next_button_advances_frame_and_updates_readout(
    main_window: MainWindow, sample_video: Path
) -> None:
    main_window.load_video(str(sample_video))
    assert main_window.controller.current_frame_index == 0

    main_window.timeline.next_button.click()

    assert main_window.controller.current_frame_index == 1
    assert "Frame 1 /" in main_window.timeline.position_label.text()
    assert not main_window.video_view.pixmap().isNull()


def test_jump_via_spinbox(main_window: MainWindow, sample_video: Path) -> None:
    main_window.load_video(str(sample_video))

    main_window.timeline.frame_spinbox.setValue(4)

    assert main_window.controller.current_frame_index == 4
    assert "Frame 4 /" in main_window.timeline.position_label.text()


def test_previous_at_start_is_a_noop(main_window: MainWindow, sample_video: Path) -> None:
    main_window.load_video(str(sample_video))

    main_window.timeline.previous_button.click()

    assert main_window.controller.current_frame_index == 0


def test_arrow_key_shortcuts_are_bound_and_navigate(
    main_window: MainWindow, sample_video: Path
) -> None:
    assert main_window.next_shortcut.key() == QKeySequence(Qt.Key.Key_Right)
    assert main_window.previous_shortcut.key() == QKeySequence(Qt.Key.Key_Left)

    main_window.load_video(str(sample_video))

    main_window.next_shortcut.activated.emit()
    main_window.next_shortcut.activated.emit()
    assert main_window.controller.current_frame_index == 2

    main_window.previous_shortcut.activated.emit()
    assert main_window.controller.current_frame_index == 1


def test_navigation_disabled_before_any_video(main_window: MainWindow) -> None:
    main_window.next_shortcut.activated.emit()

    assert main_window.controller.current_frame_index == 0
    assert not main_window.timeline.next_button.isEnabled()
