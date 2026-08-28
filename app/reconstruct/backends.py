"""Interchangeable monocular 3D pose-reconstruction backends.

A backend turns a 2D (image-plane) pose sequence into one whose active
track is in ``CANONICAL_WORLD`` with real depth. Third-party backends can
be added via the ``motion_capture.reconstruction`` entry-point group.
"""

from abc import ABC, abstractmethod

from app.models.pose_sequence import PoseSequence
from app.plugins.registry import BackendRegistry
from app.plugins.types import BackendAvailability, BackendEntry

RECONSTRUCTION_GROUP = "motion_capture.reconstruction"


class ReconstructionBackend(ABC):
    """Lift a 2D pose sequence to a 3D ``CANONICAL_WORLD`` one."""

    @property
    @abstractmethod
    def backend_id(self) -> str:
        """Return the stable id of this backend."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return the user-facing name of this backend."""

    @abstractmethod
    def can_reconstruct(self, pose_sequence: PoseSequence) -> bool:
        """Return whether this backend has what it needs for ``pose_sequence``."""

    @abstractmethod
    def reconstruct(self, pose_sequence: PoseSequence) -> PoseSequence:
        """Return a new sequence whose active track is in ``CANONICAL_WORLD``."""


def _register_builtin(registry: BackendRegistry) -> None:
    from app.reconstruct.mediapipe_world import MediaPipeWorldReconstruction

    backend = MediaPipeWorldReconstruction()
    registry.register(
        BackendEntry(
            backend_id=backend.backend_id,
            display_name=backend.display_name,
            factory=MediaPipeWorldReconstruction,
            availability=BackendAvailability.ok(),
        )
    )


def build_reconstruction_registry() -> BackendRegistry:
    """Return a registry of the available reconstruction backends."""

    registry = BackendRegistry(RECONSTRUCTION_GROUP)
    _register_builtin(registry)
    registry.discover_entry_points()
    return registry
