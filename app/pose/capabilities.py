"""Descriptive capabilities of a pose detector."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectorCapabilities:
    """What a pose detector can do, for display and validation."""

    keypoint_count: int
    is_3d: bool = False
    multi_person: bool = False
    gpu: bool = False
