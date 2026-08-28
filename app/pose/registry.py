"""The registry of pose-detection backends.

Call :func:`build_pose_backend_registry` to get a populated registry: the
built-in backends plus any advertised by installed packages. Each backend's
availability reflects whether its optional dependencies (and model files)
are actually present.
"""

from app.plugins.registry import BackendRegistry
from app.plugins.types import BackendAvailability, BackendEntry

POSE_BACKEND_GROUP = "motion_capture.pose_backends"


def _mediapipe_availability() -> BackendAvailability:
    try:
        import mediapipe  # noqa: F401
    except ImportError:
        return BackendAvailability.missing(
            "mediapipe is not installed - run: uv sync --extra mediapipe"
        )

    from app.pose.backends.mediapipe_model import default_model_path

    if not default_model_path().exists():
        return BackendAvailability.missing(
            "pose model not downloaded - run: "
            "python -m app.pose.backends.mediapipe_model"
        )

    return BackendAvailability.ok()


def _register_builtin_backends(registry: BackendRegistry) -> None:
    from app.pose.backends.mediapipe_detector import MediaPipeDetector

    registry.register(
        BackendEntry(
            backend_id="mediapipe",
            display_name="MediaPipe Pose (2D, 1 person)",
            factory=MediaPipeDetector,
            availability=_mediapipe_availability(),
        )
    )


def build_pose_backend_registry() -> BackendRegistry:
    """Return a registry populated with built-in and discovered backends."""

    registry = BackendRegistry(POSE_BACKEND_GROUP)
    _register_builtin_backends(registry)
    registry.discover_entry_points()
    return registry
