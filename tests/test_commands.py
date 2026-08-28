"""Tests for the command stack and correction commands (roadmap Phase 9)."""

from app.core.commands import (
    ClearKeypointCorrection,
    Command,
    CommandStack,
    PropagateKeypointCorrection,
    SetKeypointCorrection,
)
from app.models.corrections import CorrectionLayer
from app.models.pose import JointName, Vector3


class _Counter(Command):
    def __init__(self) -> None:
        self.value = 0

    def apply(self) -> None:
        self.value += 1

    def revert(self) -> None:
        self.value -= 1


def test_stack_do_undo_redo() -> None:
    changes: list[int] = []
    stack = CommandStack(on_change=lambda: changes.append(1))
    command = _Counter()

    stack.do(command)
    assert command.value == 1
    assert stack.can_undo and not stack.can_redo

    stack.undo()
    assert command.value == 0
    assert not stack.can_undo and stack.can_redo

    stack.redo()
    assert command.value == 1
    assert len(changes) == 3


def test_do_clears_the_redo_stack() -> None:
    stack = CommandStack()
    first, second = _Counter(), _Counter()

    stack.do(first)
    stack.undo()
    stack.do(second)

    assert not stack.can_redo


def test_set_keypoint_correction_is_reversible() -> None:
    layer = CorrectionLayer(track_id="person_0")
    stack = CommandStack()

    stack.do(SetKeypointCorrection(layer, 4, JointName.LEFT_WRIST, Vector3(1.0, 2.0, 0.0)))
    assert layer.get(4, JointName.LEFT_WRIST) == Vector3(1.0, 2.0, 0.0)

    stack.do(SetKeypointCorrection(layer, 4, JointName.LEFT_WRIST, Vector3(9.0, 9.0, 0.0)))
    assert layer.get(4, JointName.LEFT_WRIST) == Vector3(9.0, 9.0, 0.0)

    stack.undo()
    assert layer.get(4, JointName.LEFT_WRIST) == Vector3(1.0, 2.0, 0.0)

    stack.undo()
    assert layer.get(4, JointName.LEFT_WRIST) is None


def test_clear_keypoint_correction_is_reversible() -> None:
    layer = CorrectionLayer(track_id="person_0")
    layer.set(4, JointName.HEAD, Vector3(1.0, 1.0, 0.0))
    stack = CommandStack()

    stack.do(ClearKeypointCorrection(layer, 4, JointName.HEAD))
    assert layer.get(4, JointName.HEAD) is None

    stack.undo()
    assert layer.get(4, JointName.HEAD) == Vector3(1.0, 1.0, 0.0)


def test_propagate_interpolates_between_keyframes() -> None:
    layer = CorrectionLayer(track_id="person_0")
    layer.set(0, JointName.LEFT_WRIST, Vector3(0.0, 0.0, 0.0))
    layer.set(4, JointName.LEFT_WRIST, Vector3(40.0, 0.0, 0.0))
    stack = CommandStack()

    command = PropagateKeypointCorrection(layer, JointName.LEFT_WRIST)
    assert command.is_effective
    stack.do(command)

    assert layer.get(2, JointName.LEFT_WRIST) == Vector3(20.0, 0.0, 0.0)
    assert layer.keyframes_for(JointName.LEFT_WRIST) == [0, 1, 2, 3, 4]

    stack.undo()
    assert layer.keyframes_for(JointName.LEFT_WRIST) == [0, 4]


def test_propagate_needs_two_keyframes() -> None:
    layer = CorrectionLayer(track_id="person_0")
    layer.set(0, JointName.LEFT_WRIST, Vector3(0.0, 0.0, 0.0))

    command = PropagateKeypointCorrection(layer, JointName.LEFT_WRIST)

    assert not command.is_effective
