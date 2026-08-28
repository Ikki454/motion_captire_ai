"""Build the canonical skeleton from the analysed pose sequence."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class SkeletonPanel(QWidget):
    """A button to solve the canonical skeleton plus a result readout.

    Signal:
        build_requested(): the user asked to (re)build the skeleton.
    """

    build_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.build_button = QPushButton("Build skeleton")
        self.build_button.setEnabled(False)
        self.build_button.clicked.connect(self.build_requested)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(self.build_button)
        row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.status_label)

    def set_ready(self, ready: bool) -> None:
        """Enable building only once the sequence has been analysed."""

        self.build_button.setEnabled(ready)

    def set_status(self, message: str) -> None:
        """Show a one-line status message."""

        self.status_label.setText(message)
