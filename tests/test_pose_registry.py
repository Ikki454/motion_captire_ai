"""Tests for the pose-backend registry (roadmap Phase 6)."""

from app.pose.registry import build_pose_backend_registry


def test_registry_lists_the_mediapipe_backend() -> None:
    registry = build_pose_backend_registry()

    ids = {entry.backend_id for entry in registry.entries()}

    assert "mediapipe" in ids


def test_mediapipe_entry_reports_availability_without_crashing() -> None:
    registry = build_pose_backend_registry()

    entry = registry.get("mediapipe")

    # Either usable, or unusable with a human-readable reason - never a crash.
    if entry.availability.available:
        assert entry.availability.reason == ""
    else:
        assert entry.availability.reason
