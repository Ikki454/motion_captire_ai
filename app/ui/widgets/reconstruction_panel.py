"""Lift the analysed 2D pose sequence to 3D with a chosen backend."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.plugins.types import BackendEntry


class ReconstructionPanel(QWidget):
    """Choose a 3D reconstruction backend and run it.

    Signal:
        reconstruct_requested(): the user asked to reconstruct.
    """

    reconstruct_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self._has_backends = False
        self._ready = False

        self.backend_combo = QComboBox()
        self.backend_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.backend_combo.setMinimumContentsLength(8)

        self.reconstruct_button = QPushButton("Reconstruct 3D")
        self.reconstruct_button.setEnabled(False)
        self.reconstruct_button.clicked.connect(self.reconstruct_requested)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(QLabel("3D:"))
        row.addWidget(self.backend_combo, stretch=1)
        row.addWidget(self.reconstruct_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.status_label)

    def set_backends(self, backends: list[BackendEntry]) -> None:
        """Populate the combo with the available reconstruction backends."""

        self.backend_combo.clear()
        for entry in backends:
            self.backend_combo.addItem(entry.display_name, entry.backend_id)

        self._has_backends = bool(backends)
        self._refresh_button()

    def set_ready(self, ready: bool) -> None:
        """Enable reconstruction only once the sequence has been analysed."""

        self._ready = ready
        self._refresh_button()

    def _refresh_button(self) -> None:
        self.reconstruct_button.setEnabled(self._has_backends and self._ready)

    def current_backend_id(self) -> str | None:
        """Return the selected backend id, or ``None``."""

        return self.backend_combo.currentData()

    def set_status(self, message: str) -> None:
        """Show a one-line status message."""

        self.status_label.setText(message)
