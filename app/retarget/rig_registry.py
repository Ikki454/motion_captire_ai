"""Discover, load and install rig profiles.

A rig profile is one JSON file describing both the target :class:`Rig` and
the :class:`RetargetMap` from the canonical skeleton to it. Bundled
profiles live in ``rig_profiles/``; user profiles live in
:func:`user_rig_dir` and a project may carry its own copies.

Directories are scanned in the order they are added, and a later
directory wins for a given ``rig_id``: bundled < user < project.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.math.rotations import Quaternion
from app.models.rig import RetargetMap, Rig
from app.models.skeleton import CanonicalBoneName

_BUNDLED_DIR = Path(__file__).resolve().parent / "rig_profiles"
_PROFILE_SCHEMA_VERSION = 1
_SLUG_PATTERN = re.compile(r"[^a-z0-9_]+")


class RigProfileError(Exception):
    """A rig profile file is missing, malformed or cannot be written."""


@dataclass(frozen=True)
class RigProfileInfo:
    """Lightweight description of an available rig profile."""

    rig_id: str
    display_name: str
    source: Path
    is_bundled: bool = False


def user_rig_dir() -> Path:
    """Return the per-user directory holding custom rig profiles."""

    return Path.home() / ".ai-motion-capture" / "rigs"


def slugify(text: str) -> str:
    """Turn a display name into a safe ``rig_id`` (lowercase, ``a-z0-9_``).

    Returns ``"rig"`` when nothing usable is left.
    """

    slug = _SLUG_PATTERN.sub("_", text.strip().lower()).strip("_")
    return slug or "rig"


class RigRegistry:
    """Holds the rig profiles found across a set of directories.

    ``install_dir`` is where :meth:`install_profile` writes; without one
    the registry is read-only.
    """

    def __init__(self, install_dir: Path | None = None) -> None:
        self._profiles: dict[str, RigProfileInfo] = {}
        self._directories: list[tuple[Path, bool]] = []
        self._install_dir = install_dir

    def add_directory(self, directory: Path, *, bundled: bool = False) -> None:
        """Register every ``*.json`` profile in ``directory`` (if it exists).

        The directory is remembered, so :meth:`reload` re-scans it.
        """

        self._directories.append((directory, bundled))
        self._scan(directory, bundled=bundled)

    def reload(self) -> None:
        """Re-scan every registered directory, picking up new files."""

        self._profiles.clear()
        for directory, bundled in self._directories:
            self._scan(directory, bundled=bundled)

    def available(self) -> list[RigProfileInfo]:
        """Return the known profiles, ordered by id."""

        return [self._profiles[key] for key in sorted(self._profiles)]

    def has(self, rig_id: str) -> bool:
        """Return whether ``rig_id`` is known."""

        return rig_id in self._profiles

    def info(self, rig_id: str) -> RigProfileInfo | None:
        """Return the description of ``rig_id``, or ``None``."""

        return self._profiles.get(rig_id)

    def is_bundled(self, rig_id: str) -> bool:
        """Return whether ``rig_id`` comes from the bundled profiles."""

        info = self._profiles.get(rig_id)
        return info is not None and info.is_bundled

    def document(self, rig_id: str) -> dict[str, Any]:
        """Return the raw JSON document behind ``rig_id``.

        Raises:
            RigProfileError: The id is unknown or the file cannot be read.
        """

        info = self._profiles.get(rig_id)
        if info is None:
            raise RigProfileError(f"unknown rig profile '{rig_id}'")

        try:
            return json.loads(info.source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RigProfileError(f"cannot read {info.source}: {error}") from error

    def load(self, rig_id: str) -> tuple[Rig, RetargetMap]:
        """Load the :class:`Rig` and :class:`RetargetMap` for ``rig_id``.

        Raises:
            RigProfileError: The id is unknown or the file is malformed.
        """

        info = self._profiles.get(rig_id)
        if info is None:
            raise RigProfileError(f"unknown rig profile '{rig_id}'")

        return _parse_profile(info.source)

    def install_profile(self, document: dict[str, Any]) -> RigProfileInfo:
        """Validate ``document`` and write it to the install directory.

        An existing profile with the same id is overwritten, unless it is
        a bundled one.

        Raises:
            RigProfileError: No install directory, the document is
                malformed, or the id belongs to a bundled profile.
        """

        if self._install_dir is None:
            raise RigProfileError("this registry cannot install profiles")

        rig_id = str(document.get("rig_id", "")).strip()
        if not rig_id or slugify(rig_id) != rig_id:
            raise RigProfileError(
                f"invalid rig id {rig_id!r} - use lowercase letters, digits and '_'"
            )

        if self.is_bundled(rig_id):
            raise RigProfileError(
                f"'{rig_id}' is a built-in profile - choose another name"
            )

        # Validate before touching the disk.
        _parse_document(dict(document), f"profile '{rig_id}'")

        try:
            self._install_dir.mkdir(parents=True, exist_ok=True)
            path = self._install_dir / f"{rig_id}.json"
            path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        except OSError as error:
            raise RigProfileError(f"cannot write the rig profile: {error}") from error

        self.reload()

        info = self._profiles.get(rig_id)
        if info is None:  # pragma: no cover - the file was just written
            raise RigProfileError(f"'{rig_id}' did not register after writing")

        return info

    def remove_profile(self, rig_id: str) -> None:
        """Delete a custom profile.

        Raises:
            RigProfileError: The id is unknown or bundled, or the file
                cannot be deleted.
        """

        info = self._profiles.get(rig_id)
        if info is None:
            raise RigProfileError(f"unknown rig profile '{rig_id}'")

        if info.is_bundled:
            raise RigProfileError(f"'{rig_id}' is a built-in profile and cannot be removed")

        try:
            info.source.unlink()
        except OSError as error:
            raise RigProfileError(f"cannot delete {info.source}: {error}") from error

        self.reload()

    def unique_rig_id(self, preferred: str) -> str:
        """Return ``preferred`` slugified, suffixed until it is unused."""

        base = slugify(preferred)
        candidate = base
        counter = 2

        while candidate in self._profiles:
            candidate = f"{base}_{counter}"
            counter += 1

        return candidate

    def _scan(self, directory: Path, *, bundled: bool) -> None:
        if not directory.is_dir():
            return

        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                rig_id = str(document["rig_id"])
                display_name = str(document.get("display_name", rig_id))
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                continue

            self._profiles[rig_id] = RigProfileInfo(
                rig_id=rig_id,
                display_name=display_name,
                source=path,
                is_bundled=bundled,
            )


def build_rig_registry(
    *extra_directories: Path, install_dir: Path | None = None
) -> RigRegistry:
    """Return a registry populated with bundled profiles plus any extras.

    Later directories win for a given ``rig_id``.
    """

    registry = RigRegistry(install_dir=install_dir)
    registry.add_directory(_BUNDLED_DIR, bundled=True)
    for directory in extra_directories:
        registry.add_directory(directory)
    return registry


def _parse_profile(path: Path) -> tuple[Rig, RetargetMap]:
    try:
        document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RigProfileError(f"cannot read {path}: {error}") from error

    return _parse_document(document, str(path))


def _parse_document(
    document: dict[str, Any], source_label: str
) -> tuple[Rig, RetargetMap]:
    """Turn a profile document into a :class:`Rig` / :class:`RetargetMap` pair."""

    version = document.get("schema_version")
    if not isinstance(version, int) or version > _PROFILE_SCHEMA_VERSION:
        raise RigProfileError(f"{source_label}: unsupported schema_version {version!r}")

    try:
        rig_id = str(document["rig_id"])
        raw_bone_map = document["bone_map"]

        # A value may be one bone or a run of them: a rig whose spine is
        # four segments plays one canonical role with all four.
        bone_map: dict[CanonicalBoneName, str] = {}
        bone_chains: dict[CanonicalBoneName, tuple[str, ...]] = {}

        for canonical, rig_bone in raw_bone_map.items():
            key = CanonicalBoneName(canonical)

            if isinstance(rig_bone, (list, tuple)):
                chain = tuple(str(name) for name in rig_bone if str(name).strip())
                if not chain:
                    continue
                bone_map[key] = chain[0]
                if len(chain) > 1:
                    bone_chains[key] = chain
            else:
                bone_map[key] = str(rig_bone)
        rotation_offsets = {
            CanonicalBoneName(canonical): Quaternion(
                float(values[0]),
                float(values[1]),
                float(values[2]),
                float(values[3]),
            )
            for canonical, values in document.get("rotation_offsets", {}).items()
        }
        # Slot names are free-form on purpose: a future capture backend may
        # add slots this version has never heard of, and an old reader must
        # not reject a profile because of one.
        attachment_points = tuple(
            (str(slot), str(bone))
            for slot, bone in sorted(document.get("attachment_points", {}).items())
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise RigProfileError(f"{source_label}: malformed profile ({error})") from error

    rig = Rig(
        rig_id=rig_id,
        display_name=str(document.get("display_name", rig_id)),
        up_axis=str(document.get("up_axis", "Y")),
        unit_scale=float(document.get("unit_scale", 1.0)),
        rig_bone_names=tuple(
            dict.fromkeys(
                name
                for canonical, primary in bone_map.items()
                for name in bone_chains.get(canonical, (primary,))
            )
        ),
        attachment_points=attachment_points,
    )
    retarget_map = RetargetMap(
        rig_id=rig_id,
        bone_map=bone_map,
        rotation_offsets=rotation_offsets,
        bone_chains=bone_chains,
    )
    return rig, retarget_map
