"""Target rig description, canonical-to-rig mapping, and the retargeted clip (L3)."""

from dataclasses import dataclass, field

from app.math.coordinates import CoordinateSpace
from app.math.rotations import Quaternion
from app.models.pose import Vector3
from app.models.skeleton import CanonicalBoneName


@dataclass(frozen=True)
class Rig:
    """A target armature, described independently of any file format.

    ``attachment_points`` records where extra bone chains hang off the
    rig -- the bone the fingers grow from, for instance. Nothing drives
    them yet; they are stored so a later capture backend knows where to
    attach without the user re-answering.
    """

    rig_id: str
    display_name: str
    up_axis: str = "Y"
    unit_scale: float = 1.0
    rig_bone_names: tuple[str, ...] = ()
    attachment_points: tuple[tuple[str, str], ...] = ()

    def attachment_point(self, slot: str) -> str | None:
        """Return the rig bone recorded for ``slot``, or ``None``."""

        return dict(self.attachment_points).get(slot)


@dataclass
class RetargetMap:
    """How canonical bones map onto a specific rig's bones.

    ``bone_map`` holds the *primary* rig bone per canonical role, which is
    what the exported ``bone_map`` and the coverage report use.
    ``bone_chains`` holds the full run when a role is played by several
    bones -- a four-segment spine where the canonical skeleton has one.
    """

    rig_id: str
    bone_map: dict[CanonicalBoneName, str] = field(default_factory=dict)
    rotation_offsets: dict[CanonicalBoneName, Quaternion] = field(default_factory=dict)
    bone_chains: dict[CanonicalBoneName, tuple[str, ...]] = field(default_factory=dict)

    def rig_bones_for(self, canonical: CanonicalBoneName) -> tuple[str, ...]:
        """Return every rig bone playing ``canonical``, primary first."""

        chain = self.bone_chains.get(canonical)
        if chain:
            return chain

        primary = self.bone_map.get(canonical)

        return (primary,) if primary else ()

    def rig_bone_for(self, canonical: CanonicalBoneName) -> str | None:
        """Return the rig bone name for ``canonical``, or ``None``."""

        return self.bone_map.get(canonical)

    def offset_for(self, canonical: CanonicalBoneName) -> Quaternion:
        """Return the rotation offset for ``canonical`` (identity by default)."""

        return self.rotation_offsets.get(canonical, Quaternion.identity())


@dataclass
class RigClip:
    """Level 3 -- per-bone rotation curves named for a specific target rig.

    Still in ``CANONICAL_WORLD``; the coordinate conversion to a DCC's world
    happens at that tool's boundary (e.g. the Blender add-on).
    """

    rig_id: str
    fps: float
    frame_range: tuple[int, int]
    frame_indices: list[int]
    bone_order: list[str]
    bone_curves: dict[str, list[Quaternion]]
    root_curve: list[Vector3]
    space: CoordinateSpace = CoordinateSpace.CANONICAL_WORLD

    @property
    def bone_count(self) -> int:
        """Return the number of rig bones with a rotation curve."""

        return len(self.bone_order)

    @property
    def frame_count(self) -> int:
        """Return the number of keyed frames."""

        return len(self.frame_indices)
