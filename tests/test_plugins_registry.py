"""Tests for the generic BackendRegistry (roadmap Phase 6)."""

import pytest

from app.plugins.registry import BackendRegistry
from app.plugins.types import BackendAvailability, BackendEntry


def _entry(backend_id: str, *, available: bool, value: object = None) -> BackendEntry:
    return BackendEntry(
        backend_id=backend_id,
        display_name=backend_id.title(),
        factory=lambda: value,
        availability=(
            BackendAvailability.ok()
            if available
            else BackendAvailability.missing("dependency missing")
        ),
    )


def test_register_and_list_entries_sorted() -> None:
    registry = BackendRegistry("group")
    registry.register(_entry("zeta", available=True))
    registry.register(_entry("alpha", available=True))

    assert [e.backend_id for e in registry.entries()] == ["alpha", "zeta"]


def test_available_and_unavailable_are_partitioned() -> None:
    registry = BackendRegistry("group")
    registry.register(_entry("good", available=True))
    registry.register(_entry("bad", available=False))

    assert [e.backend_id for e in registry.available()] == ["good"]
    assert [e.backend_id for e in registry.unavailable()] == ["bad"]


def test_register_replaces_same_id() -> None:
    registry = BackendRegistry("group")
    registry.register(_entry("x", available=False))
    registry.register(_entry("x", available=True))

    assert len(registry.entries()) == 1
    assert registry.get("x").availability.available is True


def test_create_instantiates_available_backend() -> None:
    registry = BackendRegistry("group")
    registry.register(_entry("x", available=True, value="built"))

    assert registry.create("x") == "built"


def test_create_rejects_unavailable_backend() -> None:
    registry = BackendRegistry("group")
    registry.register(_entry("x", available=False))

    with pytest.raises(RuntimeError, match="not available"):
        registry.create("x")


def test_get_unknown_id_raises_key_error() -> None:
    registry = BackendRegistry("group")

    with pytest.raises(KeyError):
        registry.get("missing")


def test_discover_entry_points_is_safe_with_none_present() -> None:
    registry = BackendRegistry("motion_capture.nonexistent_group_xyz")

    registry.discover_entry_points()

    assert registry.entries() == []
