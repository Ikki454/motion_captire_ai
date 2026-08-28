"""Retarget the canonical skeleton onto a chosen rig."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.retarget.rig_registry import RigProfileInfo


class RigPanel(QWidget):
    """Choose a target rig and retarget the solved skeleton onto it.

    Signals:
        retarget_requested(): the user asked to retarget.
        import_rig_requested(): add a rig from an exported armature file.
        new_rig_requested(): add a rig by typing its bone names.
        remove_rig_requested(): delete the selected custom rig profile.
    """

    retarget_requested = Signal()
    import_rig_requested = Signal()
    new_rig_requested = Signal()
    remove_rig_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self._has_rigs = False
        self._ready = False
        self._custom_ids: set[str] = set()

        self.rig_combo = QComboBox()
        self.rig_combo.currentIndexChanged.connect(self._on_rig_changed)
        self.rig_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.rig_combo.setMinimumContentsLength(8)

        self.retarget_button = QPushButton("Retarget")
        self.retarget_button.setEnabled(False)
        self.retarget_button.clicked.connect(self.retarget_requested)

        self.import_rig_button = QPushButton("Import rig...")
        self.import_rig_button.setToolTip(
            "Load an armature exported from Blender and map its bones"
        )
        self.import_rig_button.clicked.connect(self.import_rig_requested)

        self.new_rig_button = QPushButton("New rig...")
        self.new_rig_button.setToolTip("Type the target rig's bone names by hand")
        self.new_rig_button.clicked.connect(self.new_rig_requested)

        self.remove_rig_button = QPushButton("Remove")
        self.remove_rig_button.setToolTip("Delete the selected custom rig profile")
        self.remove_rig_button.setEnabled(False)
        self.remove_rig_button.clicked.connect(self.remove_rig_requested)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(QLabel("Rig:"))
        row.addWidget(self.rig_combo, stretch=1)
        row.addWidget(self.retarget_button)

        profile_row = QHBoxLayout()
        profile_row.addWidget(self.import_rig_button)
        profile_row.addWidget(self.new_rig_button)
        profile_row.addWidget(self.remove_rig_button)
        profile_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(profile_row)
        layout.addWidget(self.status_label)

    def set_rigs(self, rigs: list[RigProfileInfo]) -> None:
        """Populate the combo with the available rig profiles."""

        self.rig_combo.clear()
        self._custom_ids = {info.rig_id for info in rigs if not info.is_bundled}

        for info in rigs:
            label = info.display_name if info.is_bundled else f"{info.display_name} *"
            self.rig_combo.addItem(label, info.rig_id)

        self._has_rigs = bool(rigs)
        self._refresh_button()
        self._refresh_remove_button()

    def select_rig(self, rig_id: str) -> None:
        """Select ``rig_id`` in the combo, if it is listed."""

        index = self.rig_combo.findData(rig_id)
        if index >= 0:
            self.rig_combo.setCurrentIndex(index)

    def _refresh_remove_button(self) -> None:
        self.remove_rig_button.setEnabled(
            self.rig_combo.currentData() in self._custom_ids
        )

    def set_ready(self, ready: bool) -> None:
        """Enable retargeting only once a skeleton has been solved."""

        self._ready = ready
        self._refresh_button()

    def _refresh_button(self) -> None:
        self.retarget_button.setEnabled(self._has_rigs and self._ready)

    def _on_rig_changed(self, _index: int) -> None:
        self._refresh_remove_button()

    def current_rig_id(self) -> str | None:
        """Return the selected rig id, or ``None``."""

        return self.rig_combo.currentData()

    def set_status(self, message: str) -> None:
        """Show a one-line status message."""

        self.status_label.setText(message)
