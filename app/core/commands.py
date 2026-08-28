"""Undo/redo command stack and the manual-correction commands.

Kept free of Qt. Commands capture the state they replace so that
:meth:`Command.revert` restores it exactly.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from app.models.corrections import CorrectionLayer, lerp_vector3
from app.models.pose import JointName, Vector3


class Command(ABC):
    """A reversible action."""

    label: str = "action"

    @abstractmethod
    def apply(self) -> None:
        """Perform the action."""

    @abstractmethod
    def revert(self) -> None:
        """Undo the action, restoring the previous state."""


class CommandStack:
    """A linear undo/redo history."""

    def __init__(self, on_change: Callable[[], None] | None = None) -> None:
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self._on_change = on_change

    def do(self, command: Command) -> None:
        """Run ``command`` and push it onto the undo stack."""

        command.apply()
        self._undo.append(command)
        self._redo.clear()
        self._notify()

    def undo(self) -> None:
        """Revert the most recent command."""

        if not self._undo:
            return
        command = self._undo.pop()
        command.revert()
        self._redo.append(command)
        self._notify()

    def redo(self) -> None:
        """Re-apply the most recently undone command."""

        if not self._redo:
            return
        command = self._redo.pop()
        command.apply()
        self._undo.append(command)
        self._notify()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def clear(self) -> None:
        """Drop all history."""

        self._undo.clear()
        self._redo.clear()
        self._notify()

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change()


class SetKeypointCorrection(Command):
    """Set (or replace) the correction for one joint on one frame."""

    def __init__(
        self,
        layer: CorrectionLayer,
        frame_index: int,
        joint: JointName,
        position: Vector3,
    ) -> None:
        self.label = f"move {joint.value}"
        self._layer = layer
        self._frame_index = frame_index
        self._joint = joint
        self._new = position
        self._old = layer.get(frame_index, joint)

    def apply(self) -> None:
        self._layer.set(self._frame_index, self._joint, self._new)

    def revert(self) -> None:
        if self._old is None:
            self._layer.clear(self._frame_index, self._joint)
        else:
            self._layer.set(self._frame_index, self._joint, self._old)


class ClearKeypointCorrection(Command):
    """Remove the correction for one joint on one frame."""

    def __init__(
        self, layer: CorrectionLayer, frame_index: int, joint: JointName
    ) -> None:
        self.label = f"clear {joint.value}"
        self._layer = layer
        self._frame_index = frame_index
        self._joint = joint
        self._old = layer.get(frame_index, joint)

    def apply(self) -> None:
        self._layer.clear(self._frame_index, self._joint)

    def revert(self) -> None:
        if self._old is not None:
            self._layer.set(self._frame_index, self._joint, self._old)


class PropagateKeypointCorrection(Command):
    """Interpolate one joint's corrections across its keyframe span.

    Fills every frame between the first and last corrected keyframe for the
    joint by linearly interpolating between consecutive keyframes.
    """

    def __init__(self, layer: CorrectionLayer, joint: JointName) -> None:
        self.label = f"propagate {joint.value}"
        self._layer = layer
        self._joint = joint
        self._keyframes = layer.keyframes_for(joint)
        self._new: dict[int, Vector3] = {}
        self._old: dict[int, Vector3 | None] = {}

        if len(self._keyframes) >= 2:
            self._plan()

    @property
    def is_effective(self) -> bool:
        """Return whether the command would change anything."""

        return bool(self._new)

    def _plan(self) -> None:
        for left, right in zip(self._keyframes, self._keyframes[1:], strict=False):
            start = self._layer.get(left, self._joint)
            end = self._layer.get(right, self._joint)
            span = right - left
            for frame_index in range(left + 1, right):
                t = (frame_index - left) / span
                self._new[frame_index] = lerp_vector3(start, end, t)
                self._old[frame_index] = self._layer.get(frame_index, self._joint)

    def apply(self) -> None:
        for frame_index, position in self._new.items():
            self._layer.set(frame_index, self._joint, position)

    def revert(self) -> None:
        for frame_index, previous in self._old.items():
            if previous is None:
                self._layer.clear(frame_index, self._joint)
            else:
                self._layer.set(frame_index, self._joint, previous)
