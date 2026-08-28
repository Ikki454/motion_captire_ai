"""Tests for the VideoView widget (Phase 3 display, Phase 6 overlay, Phase 9 editing)."""

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.ui.widgets.video_view import VideoView


def _solid_frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def _pose(confidence: float = 1.0) -> PoseFrame:
    joints = {
        name: Joint(
            name=name,
            position=Vector3(x=10.0 + index * 3, y=10.0 + index * 2),
            confidence=confidence,
        )
        for index, name in enumerate(JointName)
    }
    return PoseFrame(frame_index=0, timestamp=0.0, joints=joints)


def _mouse(kind: QEvent.Type, x: float, y: float) -> QMouseEvent:
    point = QPointF(x, y)
    return QMouseEvent(
        kind,
        point,
        point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def test_set_frame_displays_a_pixmap(qt_app: QApplication) -> None:
    view = VideoView()
    view.resize(320, 240)

    view.set_frame(_solid_frame(64, 48))

    assert not view.pixmap().isNull()
    assert view.pixmap().width() <= view.width()
    assert view.pixmap().height() <= view.height()


def test_preserves_aspect_ratio_when_widget_ratio_differs(qt_app: QApplication) -> None:
    view = VideoView()
    view.resize(400, 200)  # 2:1, wider than the 4:3 frame

    view.set_frame(_solid_frame(64, 48))

    pixmap = view.pixmap()
    displayed_ratio = pixmap.width() / pixmap.height()
    assert abs(displayed_ratio - (64 / 48)) < 0.05


def test_clear_frame_restores_placeholder(qt_app: QApplication) -> None:
    view = VideoView()
    view.set_frame(_solid_frame(64, 48))

    view.clear_frame()

    assert view.pixmap().isNull()
    assert view.text() == "No frame to display."


def test_set_pose_changes_the_displayed_pixmap(qt_app: QApplication) -> None:
    view = VideoView()
    view.resize(320, 240)
    view.set_frame(_solid_frame(64, 48))
    without_pose = view.pixmap().toImage()

    view.set_pose(_pose())

    assert view.pixmap().toImage() != without_pose


def test_new_frame_clears_the_previous_overlay(qt_app: QApplication) -> None:
    view = VideoView()
    view.resize(320, 240)
    view.set_frame(_solid_frame(64, 48))
    view.set_pose(_pose())
    with_pose = view.pixmap().toImage()

    view.set_frame(_solid_frame(64, 48))

    assert view.pixmap().toImage() != with_pose


def test_set_pose_none_removes_overlay(qt_app: QApplication) -> None:
    view = VideoView()
    view.resize(320, 240)
    view.set_frame(_solid_frame(64, 48))
    plain = view.pixmap().toImage()

    view.set_pose(_pose())
    view.set_pose(None)

    assert view.pixmap().toImage() == plain


def test_zero_confidence_joints_are_not_drawn(qt_app: QApplication) -> None:
    view = VideoView()
    view.resize(320, 240)
    view.set_frame(_solid_frame(64, 48))
    plain = view.pixmap().toImage()

    view.set_pose(_pose(confidence=0.0))

    assert view.pixmap().toImage() == plain


def _editable_view() -> VideoView:
    view = VideoView()
    view.resize(64, 48)  # 1:1 with the frame -> widget coords == source coords
    view.set_frame(_solid_frame(64, 48))
    view.set_pose(_pose())
    view.set_editable(True)
    return view


_FIRST_JOINT = next(iter(JointName))  # index 0 -> position (10, 10) in _pose()


def test_click_selects_the_nearest_joint(qt_app: QApplication) -> None:
    view = _editable_view()
    selected: list[object] = []
    view.keypoint_selected.connect(selected.append)

    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 11, 11))

    assert view.selected_joint == _FIRST_JOINT
    assert selected == [_FIRST_JOINT]


def test_click_on_empty_space_clears_selection(qt_app: QApplication) -> None:
    view = _editable_view()
    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 11, 11))

    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 62, 3))

    assert view.selected_joint is None


def test_drag_emits_keypoint_moved_with_new_position(qt_app: QApplication) -> None:
    view = _editable_view()
    moves: list[tuple[JointName, Vector3]] = []
    view.keypoint_moved.connect(lambda joint, pos: moves.append((joint, pos)))

    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 10, 10))
    view.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 40, 25))
    view.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 40, 25))

    assert len(moves) == 1
    joint, position = moves[0]
    assert joint == _FIRST_JOINT
    assert position.x == pytest.approx(40.0, abs=1.0)
    assert position.y == pytest.approx(25.0, abs=1.0)


def test_editing_disabled_ignores_clicks(qt_app: QApplication) -> None:
    view = _editable_view()
    view.set_editable(False)

    view.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 10, 10))

    assert view.selected_joint is None
