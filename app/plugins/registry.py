"""A generic registry of pluggable backends.

Backends are registered explicitly by built-in modules, or discovered from
installed packages via entry points. A backend whose dependencies are
missing stays listed but is marked unavailable with a human-readable reason,
so the UI can show it greyed out instead of the application failing.
"""

from importlib import metadata

from app.plugins.types import BackendEntry


class BackendRegistry:
    """Holds the backend entries for one extension point."""

    def __init__(self, entry_point_group: str) -> None:
        self._entry_point_group = entry_point_group
        self._entries: dict[str, BackendEntry] = {}

    def register(self, entry: BackendEntry) -> None:
        """Add ``entry``, replacing any entry with the same id."""

        self._entries[entry.backend_id] = entry

    def entries(self) -> list[BackendEntry]:
        """Return every registered entry, ordered by id."""

        return [self._entries[key] for key in sorted(self._entries)]

    def available(self) -> list[BackendEntry]:
        """Return the entries whose backend can be used."""

        return [entry for entry in self.entries() if entry.availability.available]

    def unavailable(self) -> list[BackendEntry]:
        """Return the entries whose backend cannot be used."""

        return [entry for entry in self.entries() if not entry.availability.available]

    def get(self, backend_id: str) -> BackendEntry:
        """Return the entry registered under ``backend_id``.

        Raises:
            KeyError: No backend is registered under that id.
        """

        return self._entries[backend_id]

    def create(self, backend_id: str, **config: object) -> object:
        """Instantiate the backend ``backend_id`` through its factory.

        Raises:
            KeyError: No backend is registered under that id.
            RuntimeError: The backend is registered but not available.
        """

        entry = self._entries[backend_id]

        if not entry.availability.available:
            raise RuntimeError(
                f"Backend '{backend_id}' is not available: "
                f"{entry.availability.reason}"
            )

        return entry.factory(**config)

    def discover_entry_points(self) -> None:
        """Register backends advertised by installed packages.

        Each entry point must resolve to a ``register(registry)`` callable.
        Safe to call when no such entry points are installed.
        """

        for entry_point in metadata.entry_points(group=self._entry_point_group):
            register_backend = entry_point.load()
            register_backend(self)
