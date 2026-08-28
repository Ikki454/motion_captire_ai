"""Tests for the Timeline navigation widget (roadmap Phase 4)."""

from PySide6.QtWidgets import QApplication

from app.ui.widgets.timeline import Timeline


def test_starts_disabled_with_empty_readout(qt_app: QApplication) -> None:
    timeline = Timeline()

    assert not timeline.previous_button.isEnabled()
    assert not timeline.next_button.isEnabled()
    assert not timeline.frame_spinbox.isEnabled()
    assert "--" in timeline.position_label.text()


def test_set_range_enables_controls_and_sets_spinbox_bounds(qt_app: QApplication) -> None:
    timeline = Timeline()

    timeline.set_range(50)

    assert timeline.next_button.isEnabled()
    assert timeline.frame_spinbox.isEnabled()
    assert timeline.frame_spinbox.minimum() == 0
    assert timeline.frame_spinbox.maximum() == 49


def test_set_range_zero_keeps_controls_disabled(qt_app: QApplication) -> None:
    timeline = Timeline()

    timeline.set_range(0)

    assert not timeline.previous_button.isEnabled()
    assert not timeline.next_button.isEnabled()


def test_next_button_emits_incremented_index(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)
    timeline.set_position(10, 0.4)

    received: list[int] = []
    timeline.frame_selected.connect(received.append)

    timeline.next_button.click()

    assert received == [11]


def test_previous_button_emits_decremented_index(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)
    timeline.set_position(10, 0.4)

    received: list[int] = []
    timeline.frame_selected.connect(received.append)

    timeline.previous_button.click()

    assert received == [9]


def test_spinbox_change_emits_value(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[int] = []
    timeline.frame_selected.connect(received.append)

    timeline.frame_spinbox.setValue(20)

    assert received == [20]


def test_set_position_updates_readout_without_emitting(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[int] = []
    timeline.frame_selected.connect(received.append)

    timeline.set_position(30, 1.2)

    assert received == []
    assert "Frame 30 / 49" in timeline.position_label.text()
    assert "1.20 s" in timeline.position_label.text()


def test_buttons_disable_at_bounds(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(10)

    timeline.set_position(0, 0.0)
    assert not timeline.previous_button.isEnabled()
    assert timeline.next_button.isEnabled()

    timeline.set_position(9, 0.9)
    assert timeline.previous_button.isEnabled()
    assert not timeline.next_button.isEnabled()


def test_reset_after_range_restores_disabled_state(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)
    timeline.set_position(10, 0.4)

    timeline.reset()

    assert not timeline.next_button.isEnabled()
    assert not timeline.frame_spinbox.isEnabled()
    assert not timeline.play_button.isEnabled()
    assert not timeline.stop_button.isEnabled()
    assert "--" in timeline.position_label.text()


def test_play_button_toggles_and_emits(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[bool] = []
    timeline.play_toggled.connect(received.append)

    timeline.play_button.click()
    assert received == [True]
    assert timeline.play_button.text() == "Pause"

    timeline.play_button.click()
    assert received == [True, False]
    assert timeline.play_button.text() == "Play"


def test_stop_button_emits_stop_requested(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[int] = []
    timeline.stop_requested.connect(lambda: received.append(1))

    timeline.stop_button.click()

    assert received == [1]


def test_scrubber_range_follows_the_video(qt_app: QApplication) -> None:
    timeline = Timeline()

    timeline.set_range(50)

    assert timeline.scrubber.isEnabled()
    assert timeline.scrubber.minimum() == 0
    assert timeline.scrubber.maximum() == 49


def test_scrubber_move_emits_frame_selected(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[int] = []
    timeline.frame_selected.connect(received.append)

    timeline.scrubber.setValue(17)

    assert received == [17]


def test_set_position_moves_the_scrubber_without_emitting(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[int] = []
    timeline.frame_selected.connect(received.append)

    timeline.set_position(24, 0.8)

    assert received == []
    assert timeline.scrubber.value() == 24


def test_reset_disables_and_clears_the_scrubber(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)
    timeline.set_position(10, 0.4)

    timeline.reset()

    assert not timeline.scrubber.isEnabled()
    assert timeline.scrubber.value() == 0


def test_set_playing_updates_button_without_emitting(qt_app: QApplication) -> None:
    timeline = Timeline()
    timeline.set_range(50)

    received: list[bool] = []
    timeline.play_toggled.connect(received.append)

    timeline.set_playing(True)

    assert received == []
    assert timeline.play_button.isChecked()
    assert timeline.play_button.text() == "Pause"

    timeline.set_playing(False)
    assert not timeline.play_button.isChecked()
    assert timeline.play_button.text() == "Play"
