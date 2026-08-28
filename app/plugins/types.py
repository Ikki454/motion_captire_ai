"""Types for the generic backend registry."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BackendAvailability:
    """Whether a backend can be used, and why not when it cannot."""

    available: bool
    reason: str = ""

    @classmethod
    def ok(cls) -> "BackendAvailability":
        """Return an 'available' result."""

        return cls(available=True)

    @classmethod
    def missing(cls, reason: str) -> "BackendAvailability":
        """Return an 'unavailable' result carrying ``reason``."""

        return cls(available=False, reason=reason)


@dataclass
class BackendEntry:
    """A registered backend: how to build it and whether it is usable."""

    backend_id: str
    display_name: str
    factory: Callable[..., Any]
    availability: BackendAvailability
    metadata: dict[str, Any] = field(default_factory=dict)
