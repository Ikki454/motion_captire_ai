"""Level 0 pose data: detector-native keypoints."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class KeypointSchema:
    """Describes a named set of keypoints produced by a detector.

    ``connections`` lists index pairs to draw as skeleton segments.
    """

    schema_id: str
    landmark_names: tuple[str, ...]
    connections: tuple[tuple[int, int], ...]

    @property
    def keypoint_count(self) -> int:
        """Return the number of keypoints in this schema."""

        return len(self.landmark_names)


@dataclass
class RawPose:
    """One detector output for a single frame, in the detector's own schema.

    ``points`` holds pixel coordinates with shape ``(keypoint_count, 2)``.
    ``visibility`` holds a ``0..1`` score per keypoint with shape
    ``(keypoint_count,)``.

    ``world_points`` optionally holds detector-native 3D coordinates with
    shape ``(keypoint_count, 3)`` (e.g. MediaPipe world landmarks, in
    metres). ``depth_source`` records where that came from -- it is *not*
    treated as a final 3D reconstruction (see the roadmap, Phase 15).
    """

    schema_id: str
    frame_index: int
    timestamp: float
    person_index: int
    points: np.ndarray
    visibility: np.ndarray
    world_points: np.ndarray | None = None
    depth_source: str = "none"
