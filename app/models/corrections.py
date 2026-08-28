"""Non-destructive manual corrections layered on top of detected poses."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.models.pose import Joint, JointName, PoseFrame, Vector3

_CORRECTED_CONFIDENCE = 1.0


@dataclass
class CorrectionLayer:
    """Sparse per-frame overrides of canonical joint positions for one track.

    The detected poses are never modified: the effective pose is computed on
    demand from ``detected`` plus these overrides.
    """

    track_id: str
    overrides: dict[int, dict[JointName, Vector3]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Return whether the layer holds no corrections."""

        return not any(self.overrides.values())

    def set(self, frame_index: int, joint: JointName, position: Vector3) -> None:
        """Record ``joint`` at ``position`` for ``frame_index``."""

        self.overrides.setdefault(frame_index, {})[joint] = position

    def clear(self, frame_index: int, joint: JointName) -> None:
        """Remove the correction for ``joint`` at ``frame_index``, if any."""

        frame = self.overrides.get(frame_index)
        if frame is None:
            return
        frame.pop(joint, None)
        if not frame:
            del self.overrides[frame_index]

    def get(self, frame_index: int, joint: JointName) -> Vector3 | None:
        """Return the corrected position for ``joint`` at ``frame_index``."""

        return self.overrides.get(frame_index, {}).get(joint)

    def corrected_joints(self, frame_index: int) -> dict[JointName, Vector3]:
        """Return all corrected joint positions for ``frame_index``."""

        return dict(self.overrides.get(frame_index, {}))

    def corrected_frames(self) -> list[int]:
        """Return the sorted frame indices that carry any correction."""

        return sorted(index for index, joints in self.overrides.items() if joints)

    def keyframes_for(self, joint: JointName) -> list[int]:
        """Return the sorted frame indices where ``joint`` is corrected."""

        return sorted(
            index for index, joints in self.overrides.items() if joint in joints
        )

    @property
    def correction_count(self) -> int:
        """Return the total number of ``(frame, joint)`` corrections."""

        return sum(len(joints) for joints in self.overrides.values())


def lerp_vector3(start: Vector3, end: Vector3, t: float) -> Vector3:
    """Linearly interpolate between two vectors (``t`` in ``[0, 1]``)."""

    return Vector3(
        x=start.x + (end.x - start.x) * t,
        y=start.y + (end.y - start.y) * t,
        z=start.z + (end.z - start.z) * t,
    )


def effective_pose(
    frame_index: int,
    timestamp: float,
    detected: PoseFrame | None,
    corrections: Mapping[JointName, Vector3],
) -> PoseFrame | None:
    """Merge ``detected`` with ``corrections`` into the pose actually shown.

    Corrected joints take the corrected position and confidence ``1.0``.
    Returns ``None`` only when there is neither a detection nor a
    correction for the frame.
    """

    if detected is None and not corrections:
        return None

    joints: dict[JointName, Joint] = {}

    if detected is not None:
        joints = {
            name: Joint(name=joint.name, position=joint.position, confidence=joint.confidence)
            for name, joint in detected.joints.items()
        }

    for name, position in corrections.items():
        joints[name] = Joint(
            name=name, position=position, confidence=_CORRECTED_CONFIDENCE
        )

    return PoseFrame(
        frame_index=frame_index,
        timestamp=detected.timestamp if detected is not None else timestamp,
        joints=joints,
    )
