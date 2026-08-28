"""Abstract interface for pose detectors."""

from abc import ABC, abstractmethod

import numpy as np

from app.models.keypoints import KeypointSchema, RawPose
from app.pose.capabilities import DetectorCapabilities


class PoseDetector(ABC):
    """Detect human pose keypoints in video frames.

    Implementations return Level 0 :class:`RawPose` data in their own
    keypoint schema. Converting to the canonical skeleton is the job of
    :mod:`app.pose.mapping`, which keeps detectors interchangeable.
    """

    @property
    @abstractmethod
    def schema(self) -> KeypointSchema:
        """Return the keypoint schema this detector produces."""

    @property
    @abstractmethod
    def capabilities(self) -> DetectorCapabilities:
        """Return this detector's capabilities."""

    @abstractmethod
    def detect(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
    ) -> RawPose | None:
        """Detect one person's pose in ``frame`` (BGR, ``uint8``).

        Returns ``None`` when no pose is found.
        """

    def close(self) -> None:
        """Release any resources held by the detector."""
