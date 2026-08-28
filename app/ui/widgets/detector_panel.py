"""Pose-detection backend selection, single-frame detection and full analysis."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.plugins.types import BackendEntry


class DetectorPanel(QWidget):
    """Choose a pose-detection backend and run it on the frame or whole video.

    Signals:
        detect_requested(): detect the current frame.
        analyze_requested(): detect every frame of the video.
        cancel_requested(): stop the running analysis.

    The chosen backend id is read with :meth:`current_backend_id`.
    """

    detect_requested = Signal()
    analyze_requested = Signal()
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self._video_loaded = False
        self._analysis_running = False

        self.backend_combo = QComboBox()
        self.backend_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.backend_combo.setMinimumContentsLength(8)

        self.detect_button = QPushButton("Detect current frame")
        self.detect_button.setEnabled(False)
        self.detect_button.clicked.connect(self._on_detect_clicked)

        self.analyze_button = QPushButton("Analyze video")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self._on_analyze_clicked)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("%v / %m frames")

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        chooser = QHBoxLayout()
        chooser.addWidget(QLabel("Detector:"))
        chooser.addWidget(self.backend_combo, stretch=1)

        actions = QHBoxLayout()
        actions.addWidget(self.detect_button)
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(chooser)
        layout.addLayout(actions)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

    def set_backends(
        self,
        available: list[BackendEntry],
        unavailable: list[BackendEntry],
    ) -> None:
        """Populate the combo with available backends and list the rest."""

        self.backend_combo.clear()
        for entry in available:
            self.backend_combo.addItem(entry.display_name, entry.backend_id)

        self._refresh_buttons()

        reasons = "; ".join(
            f"{entry.display_name}: {entry.availability.reason}"
            for entry in unavailable
        )

        if not available:
            self.status_label.setText(
                f"No pose-detection backend available. {reasons}".strip()
            )
        elif unavailable:
            self.status_label.setText(f"Unavailable - {reasons}")
        else:
            self.status_label.setText("")

    def current_backend_id(self) -> str | None:
        """Return the id of the selected backend, or ``None`` if none."""

        return self.backend_combo.currentData()

    def set_status(self, message: str) -> None:
        """Show a one-line status message."""

        self.status_label.setText(message)

    def set_video_loaded(self, loaded: bool) -> None:
        """Enable detection only once a video is available."""

        self._video_loaded = loaded
        self._refresh_buttons()

    def set_analysis_running(self, running: bool) -> None:
        """Toggle the panel between idle and 'analysis in progress'."""

        self._analysis_running = running
        self.progress_bar.setVisible(running)
        self.cancel_button.setVisible(running)
        self.backend_combo.setEnabled(not running)
        self._refresh_buttons()

        if running:
            self.progress_bar.setRange(0, 0)  # indeterminate until first tick

    def _refresh_buttons(self) -> None:
        ready = (
            self._has_backend() and self._video_loaded and not self._analysis_running
        )
        self.detect_button.setEnabled(ready)
        self.analyze_button.setEnabled(ready)

    def set_analysis_progress(self, done: int, total: int) -> None:
        """Update the progress bar to ``done`` of ``total`` frames."""

        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(done)

    def _has_backend(self) -> bool:
        return self.backend_combo.count() > 0

    def _on_detect_clicked(self) -> None:
        self.detect_requested.emit()

    def _on_analyze_clicked(self) -> None:
        self.analyze_requested.emit()

    def _on_cancel_clicked(self) -> None:
        self.cancel_requested.emit()
