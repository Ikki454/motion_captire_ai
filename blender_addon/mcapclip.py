"""Parse the ``mcapclip`` animation interchange format (v1).

Standard library only -- importable and testable without Blender. Mirrors
``app/export/animation_export.py`` on the reading side; the two are
deliberately independent implementations of the same on-disk contract
(``docs/formats/mcapclip_v1.md``).
"""

import json
from dataclasses import dataclass
from pathlib import Path

MCAPCLIP_FORMAT = "mcapclip"
SUPPORTED_VERSION = 1

Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


class McapClipError(Exception):
    """The mcapclip file is malformed or written by an unsupported version."""


@dataclass
class ClipBone:
    """One bone of the canonical skeleton described by the file."""

    name: str
    parent: str | None
    rest_direction: Vector3


@dataclass
class ClipFrame:
    """One posed frame: root translation and a local rotation per bone."""

    frame: int
    root: Vector3
    rotations: dict[str, Quaternion]


@dataclass
class ParsedClip:
    """A fully parsed ``mcapclip`` document."""

    name: str
    fps: float
    frame_range: tuple[int, int]
    coordinate_space: str
    bones: list[ClipBone]
    frames: list[ClipFrame]
    bone_map: dict[str, str] | None = None

    @property
    def bone_names(self) -> list[str]:
        """Return the bone names in file order (parent-first)."""

        return [bone.name for bone in self.bones]


def load_clip(path: str | Path) -> ParsedClip:
    """Read and parse the ``mcapclip`` file at ``path``."""

    file_path = Path(path)

    try:
        document = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise McapClipError(f"cannot read {file_path}: {error}") from error

    return parse_clip(document)


def parse_clip(document: object) -> ParsedClip:
    """Parse an already-decoded ``mcapclip`` document."""

    if not isinstance(document, dict) or document.get("format") != MCAPCLIP_FORMAT:
        raise McapClipError("not an mcapclip document")

    version = document.get("version")
    if not isinstance(version, int) or version > SUPPORTED_VERSION:
        raise McapClipError(f"unsupported mcapclip version {version!r}")

    try:
        bones = [
            ClipBone(
                name=str(bone["name"]),
                parent=bone["parent"],
                rest_direction=_vector3(bone["rest_direction"]),
            )
            for bone in document["skeleton"]["bones"]
        ]
        frames = [
            ClipFrame(
                frame=int(frame["frame"]),
                root=_vector3(frame["root"]),
                rotations={
                    str(name): _quaternion(values)
                    for name, values in frame["rotations"].items()
                },
            )
            for frame in document["frames"]
        ]
        frame_range = document["frame_range"]

        raw_bone_map = document.get("bone_map")
        bone_map = (
            {str(k): str(v) for k, v in raw_bone_map.items()}
            if isinstance(raw_bone_map, dict)
            else None
        )

        return ParsedClip(
            name=str(document.get("name", "")),
            fps=float(document["fps"]),
            frame_range=(int(frame_range[0]), int(frame_range[1])),
            coordinate_space=str(document.get("coordinate_space", "")),
            bones=bones,
            frames=frames,
            bone_map=bone_map,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise McapClipError(f"malformed mcapclip document: {error}") from error


def _vector3(values: list[float]) -> Vector3:
    x, y, z = values
    return (float(x), float(y), float(z))


def _quaternion(values: list[float]) -> Quaternion:
    w, x, y, z = values
    return (float(w), float(x), float(y), float(z))
