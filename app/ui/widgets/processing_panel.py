"""Opt-in animation cleanup controls."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.animation.processing import ProcessingOptions


class ProcessingPanel(QWidget):
    """Choose which cleanup passes to run on the analysed sequence.

    Signal:
        process_requested(): the user asked to (re)process.
    """

    process_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.fill_gaps_check = QCheckBox("Fill gaps")
        self.despike_check = QCheckBox("Despike")
        self.smooth_check = QCheckBox("Smooth")
        self.foot_lock_check = QCheckBox("Lock feet")

        self.process_button = QPushButton("Process")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.process_requested)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        checks = QHBoxLayout()
        checks.addWidget(self.fill_gaps_check)
        checks.addWidget(self.despike_check)
        checks.addWidget(self.smooth_check)
        checks.addWidget(self.foot_lock_check)
        checks.addStretch()

        actions = QHBoxLayout()
        actions.addWidget(self.process_button)
        actions.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(checks)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)

    def set_ready(self, ready: bool) -> None:
        """Enable processing only once the sequence has been analysed."""

        self.process_button.setEnabled(ready)

    def options(self) -> ProcessingOptions:
        """Return the :class:`ProcessingOptions` for the ticked passes."""

        return ProcessingOptions(
            fill_gaps=self.fill_gaps_check.isChecked(),
            despike=self.despike_check.isChecked(),
            smooth=self.smooth_check.isChecked(),
            foot_lock=self.foot_lock_check.isChecked(),
        )

    def set_status(self, message: str) -> None:
        """Show a one-line status message."""

        self.status_label.setText(message)
