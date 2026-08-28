"""Widget that displays a video frame with an editable pose overlay."""

import numpy as np
from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import QLabel, QSizePolicy

from app.models.pose import CANONICAL_CONNECTIONS, JointName, PoseFrame, Vector3

_PLACEHOLDER_TEXT = "No frame to display."
_BONE_COLOR = QColor(0, 200, 255)
_JOINT_COLOR = QColor(255, 80, 80)
_SELECTED_COLOR = QColor(255, 220, 0)
_JOINT_RADIUS = 4.0
_SELECTED_RADIUS = 6.0
_HIT_RADIUS = 12.0


class VideoView(QLabel):
    """Display one video frame with an optional, editable pose overlay.

    :meth:`set_frame` expects a **BGR** ``uint8`` array of shape
    ``(height, width, 3)``. :meth:`set_pose` overlays a canonical
    :class:`PoseFrame` whose joint positions are in the source frame's
    pixel coordinates. When :meth:`set_editable` is on, clicking a joint
    selects it (``keypoint_selected``) and dragging emits its new position
    (``keypoint_moved``).
    """

    keypoint_selected = Signal(object)  # JointName | None
    keypoint_moved = Signal(object, object)  # JointName, Vector3

    def __init__(self) -> None:
        super().__init__()

        self._source_pixmap: QPixmap | None = None
        self._source_size: tuple[int, int] | None = None
        self._last_scaled: QSize | None = None
        self._pose: PoseFrame | None = None

        self._editable = False
        self._selected_joint: JointName | None = None
        self._drag_joint: JointName | None = None
        self._drag_position: Vector3 | None = None

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)
        # The frame is rescaled to whatever space the layout gives us, so the
        # pixmap must not feed its size back into the layout as a size hint.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMouseTracking(True)
        self.setText(_PLACEHOLDER_TEXT)

    def set_frame(self, frame: np.ndarray) -> None:
        """Show ``frame``, a BGR ``uint8`` array of shape ``(H, W, 3)``.

        A new frame clears any previous pose overlay.
        """

        self._source_pixmap = self._pixmap_from_bgr(frame)
        self._source_size = (frame.shape[1], frame.shape[0])
        self._pose = None
        self._drag_joint = None
        self._drag_position = None
        self._render()

    def set_pose(self, pose: PoseFrame | None) -> None:
        """Overlay ``pose`` on the current frame, or clear the overlay."""

        self._pose = pose
        self._render()

    def set_editable(self, editable: bool) -> None:
        """Enable or disable click-to-select and drag-to-move on joints."""

        self._editable = editable
        if not editable:
            self._selected_joint = None
            self._drag_joint = None
            self._drag_position = None
        self._render()

    @property
    def selected_joint(self) -> JointName | None:
        """Return the currently selected joint, if any."""

        return self._selected_joint

    def clear_frame(self) -> None:
        """Remove the current frame and restore the placeholder text."""

        self._source_pixmap = None
        self._source_size = None
        self._last_scaled = None
        self._pose = None
        self._selected_joint = None
        self._drag_joint = None
        self._drag_position = None
        self.setText(_PLACEHOLDER_TEXT)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._can_edit():
            super().mousePressEvent(event)
            return

        joint = self._joint_at(event.position())
        self._selected_joint = joint

        if joint is not None:
            self._drag_joint = joint
            self._drag_position = self._pose.joints[joint].position

        self.keypoint_selected.emit(joint)
        self._render()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_joint is None:
            super().mouseMoveEvent(event)
            return

        source = self._widget_to_source(event.position())
        if source is not None:
            original_z = self._pose.joints[self._drag_joint].position.z
            self._drag_position = Vector3(source[0], source[1], original_z)
            self._render()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_joint is None:
            super().mouseReleaseEvent(event)
            return

        joint = self._drag_joint
        position = self._drag_position
        self._drag_joint = None
        self._drag_position = None
        self._render()

        if position is not None:
            self.keypoint_moved.emit(joint, position)

    def _can_edit(self) -> bool:
        return (
            self._editable
            and self._pose is not None
            and self._source_size is not None
            and self._last_scaled is not None
        )

    def _joint_at(self, widget_pos: QPointF) -> JointName | None:
        best: JointName | None = None
        best_distance = _HIT_RADIUS

        for joint_name, joint in self._pose.joints.items():
            if joint.confidence <= 0.0:
                continue
            point = self._source_to_widget(joint.position.x, joint.position.y)
            distance = (
                (point.x() - widget_pos.x()) ** 2 + (point.y() - widget_pos.y()) ** 2
            ) ** 0.5
            if distance < best_distance:
                best = joint_name
                best_distance = distance

        return best

    def _source_to_widget(self, x: float, y: float) -> QPointF:
        scaled = self._last_scaled
        offset_x = (self.width() - scaled.width()) / 2
        offset_y = (self.height() - scaled.height()) / 2
        k_x = scaled.width() / self._source_size[0]
        k_y = scaled.height() / self._source_size[1]
        return QPointF(x * k_x + offset_x, y * k_y + offset_y)

    def _widget_to_source(self, widget_pos: QPointF) -> tuple[float, float] | None:
        scaled = self._last_scaled
        if scaled is None or scaled.width() == 0 or self._source_size is None:
            return None

        offset_x = (self.width() - scaled.width()) / 2
        offset_y = (self.height() - scaled.height()) / 2
        source_width, source_height = self._source_size
        x = (widget_pos.x() - offset_x) * source_width / scaled.width()
        y = (widget_pos.y() - offset_y) * source_height / scaled.height()
        return (
            min(max(x, 0.0), float(source_width)),
            min(max(y, 0.0), float(source_height)),
        )

    def _render(self) -> None:
        """Rescale the source frame to the widget size and draw the overlay."""

        if self._source_pixmap is None:
            self._last_scaled = None
            return

        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._last_scaled = scaled.size()

        if self._pose is not None and self._source_size is not None:
            scaled = self._with_pose_overlay(scaled)

        self.setPixmap(scaled)

    def _with_pose_overlay(self, pixmap: QPixmap) -> QPixmap:
        """Return a copy of ``pixmap`` with the current pose drawn on it."""

        source_width, source_height = self._source_size
        scale_x = pixmap.width() / source_width
        scale_y = pixmap.height() / source_height
        pose = self._pose

        def position_of(joint_name: JointName) -> Vector3:
            if joint_name == self._drag_joint and self._drag_position is not None:
                return self._drag_position
            return pose.joints[joint_name].position

        def is_visible(joint_name: JointName) -> bool:
            joint = pose.joints.get(joint_name)
            return joint is not None and joint.confidence > 0.0

        def point(joint_name: JointName) -> QPointF:
            vector = position_of(joint_name)
            return QPointF(vector.x * scale_x, vector.y * scale_y)

        canvas = QPixmap(pixmap)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(_BONE_COLOR, 2))
        for start, end in CANONICAL_CONNECTIONS:
            if is_visible(start) and is_visible(end):
                painter.drawLine(point(start), point(end))

        for joint_name in JointName:
            if not is_visible(joint_name):
                continue
            selected = joint_name == self._selected_joint
            color = _SELECTED_COLOR if selected else _JOINT_COLOR
            radius = _SELECTED_RADIUS if selected else _JOINT_RADIUS
            painter.setPen(QPen(color, 2))
            painter.setBrush(color)
            painter.drawEllipse(point(joint_name), radius, radius)

        painter.end()
        return canvas

    @staticmethod
    def _pixmap_from_bgr(frame: np.ndarray) -> QPixmap:
        """Convert a BGR ``uint8`` frame into an RGB :class:`QPixmap`."""

        height, width = frame.shape[:2]
        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        image = QImage(
            rgb.tobytes(),
            width,
            height,
            3 * width,
            QImage.Format.Format_RGB888,
        )
        return QPixmap.fromImage(image.copy())
