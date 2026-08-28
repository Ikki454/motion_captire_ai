"""Playback and frame-navigation controls.

Phase 4 added step and jump-to-frame controls plus a position readout.
Phase 5 adds play / pause / stop. The UI redesign adds a scrubbing slider.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_EMPTY_POSITION_TEXT = "Frame -- / --"
_PLAY_TEXT = "Play"
_PAUSE_TEXT = "Pause"


@contextmanager
def _signals_blocked(widget: QWidget) -> Iterator[None]:
    """Temporarily block a widget's Qt signals."""

    was_blocked = widget.blockSignals(True)

    try:
        yield
    finally:
        widget.blockSignals(was_blocked)


class Timeline(QWidget):
    """Controls for playing a video and navigating it frame by frame.

    Signals:
        frame_selected(int): the user stepped or jumped to a frame index.
        play_toggled(bool): the user asked to start (True) or pause (False).
        stop_requested(): the user asked to stop and rewind.

    :meth:`set_position` and :meth:`set_playing` refresh the widget without
    emitting.
    """

    frame_selected = Signal(int)
    play_toggled = Signal(bool)
    stop_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self._frame_count = 0
        self._current_index = 0

        self.play_button = QPushButton(_PLAY_TEXT)
        self.play_button.setCheckable(True)
        self.play_button.setToolTip("Play / pause")
        self.play_button.toggled.connect(self._on_play_toggled)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Stop and rewind")
        self.stop_button.clicked.connect(self._on_stop_clicked)

        self.previous_button = QPushButton("\N{BLACK LEFT-POINTING TRIANGLE}")
        self.previous_button.setToolTip("Previous frame")
        self.previous_button.clicked.connect(self._on_previous_clicked)

        self.next_button = QPushButton("\N{BLACK RIGHT-POINTING TRIANGLE}")
        self.next_button.setToolTip("Next frame")
        self.next_button.clicked.connect(self._on_next_clicked)

        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setToolTip("Go to frame")
        self.frame_spinbox.valueChanged.connect(self._on_spinbox_changed)

        self.scrubber = QSlider(Qt.Orientation.Horizontal)
        self.scrubber.setToolTip("Scrub through the video")
        self.scrubber.setSingleStep(1)
        self.scrubber.setPageStep(10)
        self.scrubber.valueChanged.connect(self._on_scrubber_changed)

        self.position_label = QLabel(_EMPTY_POSITION_TEXT)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.previous_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.frame_spinbox)
        controls.addWidget(self.position_label)
        controls.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.scrubber)
        layout.addLayout(controls)

        self.reset()

    def reset(self) -> None:
        """Disable the controls and clear the readout (no video loaded)."""

        self._frame_count = 0
        self._current_index = 0
        self._set_controls_enabled(False)
        self.set_playing(False)

        with _signals_blocked(self.frame_spinbox):
            self.frame_spinbox.setRange(0, 0)
            self.frame_spinbox.setValue(0)

        with _signals_blocked(self.scrubber):
            self.scrubber.setRange(0, 0)
            self.scrubber.setValue(0)

        self.position_label.setText(_EMPTY_POSITION_TEXT)

    def set_range(self, frame_count: int) -> None:
        """Configure the controls for a video with ``frame_count`` frames.

        A non-positive count leaves the controls disabled (the container
        did not report a reliable frame count).
        """

        self._frame_count = max(0, frame_count)
        navigable = self._frame_count > 0

        self._set_controls_enabled(navigable)

        with _signals_blocked(self.frame_spinbox):
            self.frame_spinbox.setRange(0, max(0, self._frame_count - 1))
            self.frame_spinbox.setValue(0)

        with _signals_blocked(self.scrubber):
            self.scrubber.setRange(0, max(0, self._frame_count - 1))
            self.scrubber.setValue(0)

    def set_position(self, index: int, timestamp: float) -> None:
        """Refresh the readout to ``index`` / ``timestamp`` without emitting."""

        self._current_index = index

        with _signals_blocked(self.frame_spinbox):
            self.frame_spinbox.setValue(index)

        with _signals_blocked(self.scrubber):
            self.scrubber.setValue(index)

        if self._frame_count > 0:
            last = self._frame_count - 1
            self.position_label.setText(
                f"Frame {index} / {last}  ({timestamp:.2f} s)"
            )
        else:
            self.position_label.setText(f"Frame {index} / ?  ({timestamp:.2f} s)")

        self._update_button_state(index)

    def set_playing(self, playing: bool) -> None:
        """Refresh the play button to reflect ``playing`` without emitting."""

        with _signals_blocked(self.play_button):
            self.play_button.setChecked(playing)

        self.play_button.setText(_PAUSE_TEXT if playing else _PLAY_TEXT)

    def _on_play_toggled(self, checked: bool) -> None:
        self.play_button.setText(_PAUSE_TEXT if checked else _PLAY_TEXT)
        self.play_toggled.emit(checked)

    def _on_stop_clicked(self) -> None:
        self.stop_requested.emit()

    def _on_previous_clicked(self) -> None:
        self.frame_selected.emit(self._current_index - 1)

    def _on_next_clicked(self) -> None:
        self.frame_selected.emit(self._current_index + 1)

    def _on_spinbox_changed(self, value: int) -> None:
        self.frame_selected.emit(value)

    def _on_scrubber_changed(self, value: int) -> None:
        self.frame_selected.emit(value)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.previous_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.frame_spinbox.setEnabled(enabled)
        self.scrubber.setEnabled(enabled)

    def _update_button_state(self, index: int) -> None:
        if self._frame_count <= 0:
            return

        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < self._frame_count - 1)
