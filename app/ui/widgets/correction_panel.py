"""Manual keypoint-correction controls."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.models.pose import JointName


class CorrectionPanel(QWidget):
    """Toggle correction editing and drive undo/redo/propagate/clear.

    Signals:
        edit_toggled(bool): the user turned keypoint editing on/off.
        undo_requested() / redo_requested()
        propagate_requested(): interpolate the selected joint across its keyframes.
        clear_requested(): drop the selected joint's correction on this frame.
    """

    edit_toggled = Signal(bool)
    undo_requested = Signal()
    redo_requested = Signal()
    propagate_requested = Signal()
    clear_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.edit_toggle = QPushButton("Edit keypoints")
        self.edit_toggle.setCheckable(True)
        self.edit_toggle.toggled.connect(self._on_edit_toggled)

        self.undo_button = QPushButton("Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.undo_requested)

        self.redo_button = QPushButton("Redo")
        self.redo_button.setEnabled(False)
        self.redo_button.clicked.connect(self.redo_requested)

        self.propagate_button = QPushButton("Propagate")
        self.propagate_button.setToolTip(
            "Interpolate the selected joint between its corrected frames"
        )
        self.propagate_button.setEnabled(False)
        self.propagate_button.clicked.connect(self.propagate_requested)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setToolTip("Remove the selected joint's correction here")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_requested)

        self.status_label = QLabel("")

        toggle_row = QHBoxLayout()
        toggle_row.addWidget(self.edit_toggle)
        toggle_row.addStretch()

        actions = QHBoxLayout()
        actions.addWidget(self.undo_button)
        actions.addWidget(self.redo_button)
        actions.addWidget(self.propagate_button)
        actions.addWidget(self.clear_button)
        actions.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toggle_row)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)

    def set_selected_joint(self, joint: JointName | None) -> None:
        """Enable joint-specific actions when a joint is selected."""

        has_joint = joint is not None
        self.propagate_button.setEnabled(has_joint)
        self.clear_button.setEnabled(has_joint)

        if joint is None:
            self.status_label.setText("")
        else:
            self.status_label.setText(f"Selected: {joint.value}")

    def set_undo_redo(self, *, can_undo: bool, can_redo: bool) -> None:
        """Reflect the command stack state on the undo/redo buttons."""

        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def set_status(self, message: str) -> None:
        """Show a one-line status message."""

        self.status_label.setText(message)

    def _on_edit_toggled(self, checked: bool) -> None:
        self.edit_toggle.setText("Editing keypoints" if checked else "Edit keypoints")
        if not checked:
            self.set_selected_joint(None)
        self.edit_toggled.emit(checked)
