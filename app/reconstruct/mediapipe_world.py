"""Reconstruction backend using MediaPipe's world landmarks.

MediaPipe already estimates rough 3D world coordinates. This backend maps
those onto the canonical joints and into ``CANONICAL_WORLD`` -- a real,
if approximate, 3D track, without extra model dependencies. A proper
monocular-lift model can be added later behind the same interface.
"""

import numpy as np

from app.math.coordinates import CoordinateSpace, mediapipe_world_to_canonical
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence
from app.reconstruct.backends import ReconstructionBackend

_SOURCE_DEPTH = "mediapipe_world"
_OUTPUT_DEPTH = "reconstruction:mediapipe_world"

_DIRECT: dict[JointName, int] = {
    JointName.HEAD: 0,
    JointName.LEFT_SHOULDER: 11,
    JointName.RIGHT_SHOULDER: 12,
    JointName.LEFT_ELBOW: 13,
    JointName.RIGHT_ELBOW: 14,
    JointName.LEFT_WRIST: 15,
    JointName.RIGHT_WRIST: 16,
    JointName.LEFT_HIP: 23,
    JointName.RIGHT_HIP: 24,
    JointName.LEFT_KNEE: 25,
    JointName.RIGHT_KNEE: 26,
    JointName.LEFT_ANKLE: 27,
    JointName.RIGHT_ANKLE: 28,
    JointName.LEFT_FOOT: 31,
    JointName.RIGHT_FOOT: 32,
}


class MediaPipeWorldReconstruction(ReconstructionBackend):
    """Turn stored MediaPipe world landmarks into a canonical 3D track."""

    @property
    def backend_id(self) -> str:
        return "mediapipe_world"

    @property
    def display_name(self) -> str:
        return "MediaPipe world landmarks"

    def can_reconstruct(self, pose_sequence: PoseSequence) -> bool:
        track = pose_sequence.active_track
        return (
            track is not None
            and track.depth_source == _SOURCE_DEPTH
            and any(
                raw.world_points is not None for raw in track.raw_frames.values()
            )
        )

    def reconstruct(self, pose_sequence: PoseSequence) -> PoseSequence:
        track = pose_sequence.active_track
        if track is None:
            raise ValueError("pose sequence has no active track")

        new_track = PersonTrack(
            track_id=track.track_id,
            depth_source=_OUTPUT_DEPTH,
            space=CoordinateSpace.CANONICAL_WORLD,
        )

        for frame_index, raw in track.raw_frames.items():
            if raw.world_points is None:
                continue
            new_track.frames[frame_index] = _frame_from_world(
                frame_index,
                raw.timestamp,
                np.asarray(raw.world_points, dtype=np.float64),
            )

        result = PoseSequence(
            video_path=pose_sequence.video_path,
            frame_count=pose_sequence.frame_count,
            fps=pose_sequence.fps,
            width=pose_sequence.width,
            height=pose_sequence.height,
        )
        result.add_track(new_track, make_active=True)
        return result


def _frame_from_world(
    frame_index: int, timestamp: float, world: np.ndarray
) -> PoseFrame:
    joints: dict[JointName, Joint] = {}

    for joint_name, landmark_index in _DIRECT.items():
        x, y, z = world[landmark_index]
        joints[joint_name] = Joint(
            name=joint_name,
            position=mediapipe_world_to_canonical(float(x), float(y), float(z)),
            confidence=1.0,
        )

    pelvis = _average(joints[JointName.LEFT_HIP], joints[JointName.RIGHT_HIP])
    neck = _average(
        joints[JointName.LEFT_SHOULDER], joints[JointName.RIGHT_SHOULDER]
    )
    chest = _lerp(pelvis, neck, 0.7)

    joints[JointName.PELVIS] = Joint(JointName.PELVIS, pelvis, 1.0)
    joints[JointName.NECK] = Joint(JointName.NECK, neck, 1.0)
    joints[JointName.CHEST] = Joint(JointName.CHEST, chest, 1.0)

    return PoseFrame(frame_index=frame_index, timestamp=timestamp, joints=joints)


def _average(a: Joint, b: Joint) -> Vector3:
    return Vector3(
        (a.position.x + b.position.x) / 2,
        (a.position.y + b.position.y) / 2,
        (a.position.z + b.position.z) / 2,
    )


def _lerp(a: Vector3, b: Vector3, t: float) -> Vector3:
    return Vector3(
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t,
    )
