"""Review and edit the canonical-bone to rig-bone mapping of a custom rig."""

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.models.skeleton import CanonicalBoneName
from app.retarget.armature_import import (
    ATTACHMENT_SLOTS,
    BoneGroup,
    build_profile_document,
)
from app.ui.sizing import fit_window_to_scroll_area

_NO_BONE = ""
_HINT = (
    "Leave a row empty when the rig has no such bone. Bones the canonical "
    "skeleton has no source for - fingers, toes, the root - stay unmapped "
    "and keep their rest pose on import."
)


class CustomRigDialog(QDialog):
    """Edit a rig profile: its name, scale, and one rig bone per canonical bone.

    Args:
        bone_names: The target armature's bone names. Empty means the user
            types the names by hand.
        mapping: Pre-filled canonical to rig-bone mapping (e.g. from
            :func:`app.retarget.armature_import.auto_map`).
        groups: Bone chains no canonical role uses (fingers, toes). A
            finger group becomes one attachment row instead of thirty
            useless mapping rows.
        display_name: Initial human-readable rig name.
    """

    def __init__(
        self,
        *,
        bone_names: tuple[str, ...] | list[str] = (),
        mapping: dict[CanonicalBoneName, str] | None = None,
        groups: list[BoneGroup] | None = None,
        display_name: str = "",
        unit_scale: float = 1.0,
        up_axis: str = "Y",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._bone_names = tuple(bone_names)
        self._groups = list(groups or [])
        self._combos: dict[CanonicalBoneName, QComboBox] = {}
        self._attachment_combos: dict[str, QComboBox] = {}
        self._scroll: QScrollArea | None = None
        self._fitted = False

        self.setWindowTitle("Custom rig")
        self.resize(520, 640)

        self.name_edit = QLineEdit(display_name)
        self.name_edit.setPlaceholderText("My Blender rig")
        self.name_edit.textChanged.connect(self._refresh)

        self.unit_scale_spin = QDoubleSpinBox()
        self.unit_scale_spin.setDecimals(4)
        self.unit_scale_spin.setRange(0.0001, 1000.0)
        self.unit_scale_spin.setValue(unit_scale)
        self.unit_scale_spin.setToolTip("Metres per rig unit (Mixamo uses 0.01)")

        self.up_axis_combo = QComboBox()
        self.up_axis_combo.addItems(["Y", "Z"])
        self.up_axis_combo.setCurrentText(up_axis if up_axis in ("Y", "Z") else "Y")

        form = QFormLayout()
        form.addRow("Name:", self.name_edit)
        form.addRow("Unit scale:", self.unit_scale_spin)
        form.addRow("Up axis:", self.up_axis_combo)

        hint = QLabel(_HINT)
        hint.setWordWrap(True)

        self.coverage_label = QLabel("")
        self.coverage_label.setWordWrap(True)

        self.unused_label = QLabel("")
        self.unused_label.setObjectName("videoInfo")
        self.unused_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(self._build_mapping_area(mapping or {}), stretch=1)
        layout.addWidget(self.coverage_label)
        layout.addWidget(self.unused_label)
        layout.addWidget(self.button_box)

        self._refresh()

    def _build_mapping_area(self, mapping: dict[CanonicalBoneName, str]) -> QWidget:
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setColumnStretch(1, 1)

        row = 0

        for canonical in CanonicalBoneName:
            combo = self._make_bone_combo(mapping.get(canonical, _NO_BONE))
            self._combos[canonical] = combo
            grid.addWidget(QLabel(canonical.value), row, 0)
            grid.addWidget(combo, row, 1)
            row += 1

        row = self._add_attachment_rows(grid, row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        self._scroll = scroll
        return scroll

    def _make_bone_combo(self, current: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(10)
        combo.addItem(_NO_BONE)
        combo.addItems(self._bone_names)
        combo.setCurrentText(current)
        combo.currentTextChanged.connect(self._refresh)
        return combo

    def _add_attachment_rows(self, grid: QGridLayout, row: int) -> int:
        """Add one row per finger group instead of a row per finger bone."""

        finger_roots = {
            group.attaches_to: group for group in self._groups if group.is_fingers
        }
        offered = [
            (slot, label, finger_roots[role])
            for slot, label, role in ATTACHMENT_SLOTS
            if role in finger_roots
        ]

        if not offered:
            return row

        header = QLabel("Attachment points")
        header.setStyleSheet("font-weight: bold;")
        grid.addWidget(header, row, 0, 1, 2)
        row += 1

        for slot, label, group in offered:
            caption = QLabel(f"{label} ({len(group.members)} bones)")
            caption.setToolTip(
                "Nothing drives these yet - recorded so a later finger "
                "capture knows where to attach."
            )
            combo = self._make_bone_combo(group.root)
            self._attachment_combos[slot] = combo
            grid.addWidget(caption, row, 0)
            grid.addWidget(combo, row, 1)
            row += 1

        return row

    def attachment_points(self) -> dict[str, str]:
        """Return the ``slot -> rig bone`` map the user settled on."""

        return {
            slot: combo.currentText().strip()
            for slot, combo in self._attachment_combos.items()
            if combo.currentText().strip()
        }

    def showEvent(self, event: QShowEvent) -> None:
        """Size the dialog to its rows the first time it is shown."""

        super().showEvent(event)

        if not self._fitted and self._scroll is not None:
            self._fitted = True
            fit_window_to_scroll_area(self, self._scroll)

    def bone_map(self) -> dict[CanonicalBoneName, str]:
        """Return the non-empty canonical to rig-bone mapping."""

        return {
            canonical: combo.currentText().strip()
            for canonical, combo in self._combos.items()
            if combo.currentText().strip()
        }

    def document(self, rig_id: str) -> dict:
        """Return the rig-profile document for ``rig_id``."""

        return build_profile_document(
            rig_id,
            self.name_edit.text().strip() or rig_id,
            self.bone_map(),
            unit_scale=self.unit_scale_spin.value(),
            up_axis=self.up_axis_combo.currentText(),
            attachment_points=self.attachment_points(),
        )

    def accept(self) -> None:
        """Refuse to close while the profile is unusable."""

        if not self._is_valid():
            return
        super().accept()

    def _is_valid(self) -> bool:
        return bool(self.name_edit.text().strip()) and bool(self.bone_map())

    def unused_bones(self) -> list[str]:
        """Return the armature bones no canonical role is using."""

        used = set(self.bone_map().values())

        return [name for name in self._bone_names if name not in used]

    def _refresh(self) -> None:
        mapped = len(self.bone_map())
        total = len(CanonicalBoneName)

        if not self.name_edit.text().strip():
            message = "Give the rig a name."
        elif not mapped:
            message = "Map at least one bone."
        else:
            message = f"{mapped} / {total} canonical bones mapped."

        self.coverage_label.setText(message)
        self._refresh_unused()
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            self._is_valid()
        )

    def _refresh_unused(self) -> None:
        """Account for every armature bone, so none is silently dropped."""

        if not self._bone_names:
            self.unused_label.clear()
            self.unused_label.setToolTip("")
            return

        unused = self.unused_bones()
        total = len(self._bone_names)

        if not unused:
            self.unused_label.setText(f"All {total} rig bones are mapped.")
            self.unused_label.setToolTip("")
            return

        self.unused_label.setText(
            f"{len(unused)} of {total} rig bones keep their rest pose"
            f"{self._group_summary(unused)}"
        )
        self.unused_label.setToolTip("\n".join(unused))

    def _group_summary(self, unused: list[str]) -> str:
        """Describe the unmapped bones by the chains they form.

        Naming the chains ("hand.L (16)") beats listing six arbitrary bone
        names: it says *what* is left out, not just how much.
        """

        grouped = [
            group
            for group in self._groups
            if any(member in unused for member in group.members)
        ]

        if not grouped:
            preview = ", ".join(unused[:6])
            more = f" (+{len(unused) - 6} more)" if len(unused) > 6 else ""
            return f": {preview}{more}"

        counted = sum(len(group.members) for group in grouped)
        parts = ", ".join(f"{group.root} ({len(group.members)})" for group in grouped)
        loose = len(unused) - counted
        tail = f", plus {loose} above the skeleton" if loose > 0 else ""

        return f" - {len(grouped)} chain(s): {parts}{tail}"
