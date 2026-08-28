"""A titled container for one step of the processing pipeline.

Each section wraps a panel widget with a numbered badge, a title and an
optional hint ("next"). The visual state ("pending" / "active" / "done")
is exposed as a Qt property so the style sheet can react to it.
"""

from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

SectionState = Literal["pending", "active", "done"]


class PipelineSection(QFrame):
    """Wrap ``body`` in a titled, state-aware card.

    Args:
        number: The step number shown in the badge.
        title: The step name.
        body: The panel widget for this step.
        optional: When true, the title is annotated as optional.
    """

    def __init__(
        self,
        number: int,
        title: str,
        body: QWidget,
        *,
        optional: bool = False,
    ) -> None:
        super().__init__()

        self.setFrameShape(QFrame.Shape.NoFrame)

        self._state: SectionState = "pending"
        self.setProperty("state", self._state)

        self._badge = QLabel(str(number))
        self._badge.setObjectName("sectionBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFixedSize(20, 20)

        label = f"{title}  ·  optional" if optional else title
        self._title = QLabel(label)
        self._title.setObjectName("sectionTitle")

        self._hint = QLabel("")
        self._hint.setObjectName("sectionHint")

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self._badge)
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._hint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(body)

    @property
    def state(self) -> SectionState:
        """Return the current visual state."""

        return self._state

    def set_state(self, state: SectionState, hint: str = "") -> None:
        """Update the visual state and the trailing hint text."""

        self._state = state
        self.setProperty("state", state)
        self._hint.setText(hint)

        # Re-evaluate the style sheet against the new property value.
        self.style().unpolish(self)
        self.style().polish(self)
