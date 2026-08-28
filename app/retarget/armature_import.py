"""Turn a target armature's bone names into a rig profile.

Two things live here:

* :func:`parse_armature_dump` reads the JSON the Blender add-on writes
  (``File > Export > Motion Capture Rig``) -- a plain list of bone names.
* :func:`auto_map` guesses which rig bone plays each canonical role, so
  the user only has to correct what the heuristic missed.

The guess is deliberately conservative: an unmatched canonical bone is
left out rather than mapped to something plausible-looking.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.models.skeleton import CanonicalBoneName

ARMATURE_DUMP_FORMAT = "mcap_armature"
ARMATURE_DUMP_VERSION = 1

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[^a-z0-9]+")

# Naming noise that carries no anatomical meaning.
_NOISE_TOKENS = frozenset(
    {"mixamorig", "def", "org", "mch", "ctrl", "ik", "fk", "bone", "rig", "armature"}
)
_LEFT_TOKENS = frozenset({"l", "left", "lft"})
_RIGHT_TOKENS = frozenset({"r", "right", "rgt"})

_L = CanonicalBoneName
# (needle, left bone, right bone, score) -- most specific first, first match
# wins. ``needle`` is matched against the name with all separators removed,
# so "LeftForeArm", "forearm.L" and "lowerarm_l" all reach the same rule.
_SIDED_RULES: tuple[tuple[str, CanonicalBoneName, CanonicalBoneName, int], ...] = (
    ("forearm", _L.LEFT_LOWER_ARM, _L.RIGHT_LOWER_ARM, 10),
    ("lowerarm", _L.LEFT_LOWER_ARM, _L.RIGHT_LOWER_ARM, 10),
    ("upperarm", _L.LEFT_UPPER_ARM, _L.RIGHT_UPPER_ARM, 10),
    ("uparm", _L.LEFT_UPPER_ARM, _L.RIGHT_UPPER_ARM, 10),
    ("elbow", _L.LEFT_LOWER_ARM, _L.RIGHT_LOWER_ARM, 6),
    ("upleg", _L.LEFT_UPPER_LEG, _L.RIGHT_UPPER_LEG, 10),
    ("upperleg", _L.LEFT_UPPER_LEG, _L.RIGHT_UPPER_LEG, 10),
    ("thigh", _L.LEFT_UPPER_LEG, _L.RIGHT_UPPER_LEG, 10),
    ("lowerleg", _L.LEFT_LOWER_LEG, _L.RIGHT_LOWER_LEG, 10),
    ("shin", _L.LEFT_LOWER_LEG, _L.RIGHT_LOWER_LEG, 10),
    ("calf", _L.LEFT_LOWER_LEG, _L.RIGHT_LOWER_LEG, 10),
    ("knee", _L.LEFT_LOWER_LEG, _L.RIGHT_LOWER_LEG, 6),
    ("clavicle", _L.LEFT_CLAVICLE, _L.RIGHT_CLAVICLE, 10),
    ("shoulder", _L.LEFT_CLAVICLE, _L.RIGHT_CLAVICLE, 8),
    ("collar", _L.LEFT_CLAVICLE, _L.RIGHT_CLAVICLE, 8),
    ("foot", _L.LEFT_FOOT, _L.RIGHT_FOOT, 10),
    ("ankle", _L.LEFT_FOOT, _L.RIGHT_FOOT, 8),
    ("hip", _L.LEFT_HIP, _L.RIGHT_HIP, 8),
    ("pelvis", _L.LEFT_HIP, _L.RIGHT_HIP, 8),
    # Bare "arm" / "leg" are last: Mixamo's LeftArm is the upper arm and
    # its LeftLeg is the lower leg, but only once the specific rules miss.
    ("arm", _L.LEFT_UPPER_ARM, _L.RIGHT_UPPER_ARM, 4),
    ("leg", _L.LEFT_LOWER_LEG, _L.RIGHT_LOWER_LEG, 4),
)
_CENTRE_RULES: tuple[tuple[str, CanonicalBoneName, int], ...] = (
    ("spine", _L.SPINE, 10),
    ("chest", _L.SPINE, 8),
    ("torso", _L.SPINE, 6),
    ("neck", _L.NECK, 10),
    ("head", _L.HEAD, 10),
    ("skull", _L.HEAD, 6),
)
# Bones that are never a canonical role, even though they contain a needle
# ("LeftHandIndex1" must not become a lower arm).
_EXCLUDED = ("hand", "finger", "thumb", "index", "middle", "ring", "pinky", "toe", "eye")


class ArmatureImportError(Exception):
    """The armature dump is missing, malformed or of an unsupported version."""


@dataclass(frozen=True)
class ArmatureDump:
    """The bones of a target armature, as exported from a DCC.

    ``parents`` maps a bone name to its parent's name (``None`` at the
    root). :func:`auto_map` uses it to place roles that naming alone
    cannot resolve.
    """

    armature_name: str
    bone_names: tuple[str, ...]
    up_axis: str = "Z"
    unit_scale: float = 1.0
    parents: dict[str, str | None] = field(default_factory=dict)
    source: Path | None = field(default=None, compare=False)


def parse_armature_dump(document: Any, source: Path | None = None) -> ArmatureDump:
    """Turn an armature-dump document into an :class:`ArmatureDump`.

    Raises:
        ArmatureImportError: Wrong format, newer version, or malformed.
    """

    if not isinstance(document, dict):
        raise ArmatureImportError("not an armature file")

    if document.get("format") != ARMATURE_DUMP_FORMAT:
        raise ArmatureImportError(
            f"not an armature file (format={document.get('format')!r})"
        )

    version = document.get("version")
    if not isinstance(version, int) or version > ARMATURE_DUMP_VERSION:
        raise ArmatureImportError(f"unsupported armature version {version!r}")

    try:
        raw_bones = document["bones"]
        names = tuple(
            str(bone["name"]) if isinstance(bone, dict) else str(bone)
            for bone in raw_bones
        )
        parents = {
            str(bone["name"]): (str(bone["parent"]) if bone.get("parent") else None)
            for bone in raw_bones
            if isinstance(bone, dict)
        }
    except (KeyError, TypeError) as error:
        raise ArmatureImportError(f"malformed armature file ({error})") from error

    if not names:
        raise ArmatureImportError("the armature has no bones")

    return ArmatureDump(
        armature_name=str(document.get("armature_name", "armature")),
        bone_names=names,
        up_axis=str(document.get("up_axis", "Z")),
        unit_scale=float(document.get("unit_scale", 1.0)),
        parents=parents,
        source=source,
    )


def load_armature_dump(path: Path) -> ArmatureDump:
    """Read an armature dump from ``path``.

    Raises:
        ArmatureImportError: The file cannot be read or is malformed.
    """

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArmatureImportError(f"cannot read {path.name}: {error}") from error

    return parse_armature_dump(document, source=path)


def auto_map(
    bone_names: tuple[str, ...] | list[str],
    parents: dict[str, str | None] | None = None,
) -> dict[CanonicalBoneName, str]:
    """Guess a canonical-bone to rig-bone mapping from ``bone_names``.

    Each rig bone is used at most once, and only confident matches are
    returned -- roles the heuristic cannot place are simply absent.

    When ``parents`` is given, a second pass places the hips from the
    hierarchy: the bone a thigh hangs off is the hip, whatever it is
    called. See :func:`_infer_hips_from_hierarchy`.
    """

    scored: dict[CanonicalBoneName, list[tuple[int, int, str]]] = {}

    for order, name in enumerate(bone_names):
        classified = _classify(name)
        if classified is None:
            continue
        canonical, score = classified
        scored.setdefault(canonical, []).append((-score, order, name))

    mapping: dict[CanonicalBoneName, str] = {}
    taken: set[str] = set()

    # Resolve in canonical order so the result is deterministic.
    for canonical in CanonicalBoneName:
        for _, _, name in sorted(scored.get(canonical, [])):
            if name not in taken:
                mapping[canonical] = name
                taken.add(name)
                break

    if parents:
        _infer_hips_from_hierarchy(mapping, taken, parents)

    return mapping


def _infer_hips_from_hierarchy(
    mapping: dict[CanonicalBoneName, str],
    taken: set[str],
    parents: dict[str, str | None],
) -> None:
    """Fill in the hips from the bone hierarchy, in place.

    A canonical hip is the bone between the pelvis and the upper leg, so
    it is the parent of whatever plays the upper-leg role -- regardless of
    what the rig calls it (``plevis.L``, ``pelvis_l``, ``hip.L``).

    Rigs without hip bones hang both thighs off one shared pelvis or root
    bone. Mapping that single bone to a side would be wrong, so when both
    thighs share a parent, neither hip is inferred.

    The armature root is refused outright: a hip always hangs off a pelvis
    or a spine, never off the top of the hierarchy. Without this a rig with
    only one leg modelled would slip past the shared-parent check.
    """

    sides = (
        (CanonicalBoneName.LEFT_UPPER_LEG, CanonicalBoneName.LEFT_HIP),
        (CanonicalBoneName.RIGHT_UPPER_LEG, CanonicalBoneName.RIGHT_HIP),
    )
    candidates: dict[CanonicalBoneName, str] = {}

    for upper_leg, hip in sides:
        if hip in mapping:
            continue
        thigh = mapping.get(upper_leg)
        if thigh is None:
            continue
        parent = parents.get(thigh)
        is_armature_root = parent is not None and parents.get(parent, "") is None
        if parent and not is_armature_root and parent not in taken:
            candidates[hip] = parent

    # A parent shared by both legs is the pelvis, not a hip.
    if len(set(candidates.values())) < len(candidates):
        return

    for hip, parent in candidates.items():
        mapping[hip] = parent
        taken.add(parent)


def build_profile_document(
    rig_id: str,
    display_name: str,
    bone_map: dict[CanonicalBoneName, str],
    *,
    unit_scale: float = 1.0,
    up_axis: str = "Y",
    attachment_points: dict[str, str] | None = None,
    bone_chains: dict[CanonicalBoneName, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Build a rig-profile document ready for ``RigRegistry.install_profile``.

    Empty rig-bone names are dropped, so an unfinished mapping still
    produces a valid (partial) profile. ``attachment_points`` is written
    only when it holds something.

    A role listed in ``bone_chains`` is written as a **list** of bones
    instead of one, and the retargeter splits its rotation between them.
    The chain is only honoured when its first bone still matches what
    ``bone_map`` holds for that role, so editing the primary by hand drops
    a stale chain rather than silently keeping it.
    """

    chains = bone_chains or {}
    entries: dict[str, Any] = {}

    for canonical, rig_bone in bone_map.items():
        if not rig_bone.strip():
            continue
        chain = chains.get(canonical)
        if chain and chain[0] == rig_bone:
            entries[canonical.value] = list(chain)
        else:
            entries[canonical.value] = rig_bone

    document: dict[str, Any] = {
        "schema_version": 1,
        "rig_id": rig_id,
        "display_name": display_name,
        "up_axis": up_axis,
        "unit_scale": unit_scale,
        "bone_map": entries,
    }

    kept = {
        slot: bone.strip()
        for slot, bone in (attachment_points or {}).items()
        if bone.strip()
    }
    if kept:
        document["attachment_points"] = kept

    return document


def _classify(name: str) -> tuple[CanonicalBoneName, int] | None:
    """Return the canonical role ``name`` plays plus a confidence score."""

    tokens, side = _tokenise(name)
    if not tokens:
        return None

    joined = "".join(tokens)

    if any(excluded in joined for excluded in _EXCLUDED):
        return None

    if side is not None:
        for needle, left, right, score in _SIDED_RULES:
            if needle in joined:
                return (left if side == "left" else right, score)
        return None

    for needle, canonical, score in _CENTRE_RULES:
        if needle in joined:
            return (canonical, score)

    return None


def _tokenise(name: str) -> tuple[list[str], str | None]:
    """Split a bone name into meaningful tokens plus its side, if any."""

    text = name.split(":")[-1]
    text = _CAMEL_BOUNDARY.sub("_", text).lower()

    tokens = [token for token in _SEPARATORS.split(text) if token]

    side: str | None = None
    kept: list[str] = []

    for token in tokens:
        if token in _NOISE_TOKENS or token.isdigit():
            continue
        if token in _LEFT_TOKENS:
            side = "left"
            continue
        if token in _RIGHT_TOKENS:
            side = "right"
            continue
        kept.append(token)

    return kept, side


# --- extra chains (fingers, toes, spine segments) --------------------------

# Slots a future capture backend could drive. Recorded in the rig profile now
# so the attachment point is already known when such a backend lands.
ATTACHMENT_SLOTS: tuple[tuple[str, str, CanonicalBoneName], ...] = (
    ("left_hand", "Left hand", CanonicalBoneName.LEFT_LOWER_ARM),
    ("right_hand", "Right hand", CanonicalBoneName.RIGHT_LOWER_ARM),
)
_FINGER_CHAIN_COUNT = 3


@dataclass(frozen=True)
class BoneGroup:
    """A run of rig bones hanging off a mapped bone, kept out of the mapping.

    The canonical skeleton has no role for these -- fingers, toes, extra
    spine segments. They keep their rest pose on import. ``root`` is the
    single bone worth recording: attaching a future finger capture to
    ``hand.L`` is enough to reach all fifteen bones below it.
    """

    root: str
    members: tuple[str, ...]
    attaches_to: CanonicalBoneName
    kind: str = "chain"

    @property
    def is_fingers(self) -> bool:
        """Return whether this group looks like a set of finger chains."""

        return self.kind == "fingers"


def detect_bone_groups(
    bone_names: tuple[str, ...] | list[str],
    parents: dict[str, str | None],
    mapping: dict[CanonicalBoneName, str],
) -> list[BoneGroup]:
    """Group the bones no canonical role uses into the chains they form.

    A group starts at an unmapped bone whose parent *is* mapped, and holds
    that bone plus its descendants, stopping at any mapped bone (so a
    mapped neck below an unmapped spine segment starts its own subtree
    rather than being swallowed).

    Bones above the mapped skeleton -- a root or pelvis that mapped bones
    descend from -- are not grouped; they have no attachment point.
    """

    mapped_bones = set(mapping.values())
    role_of = {bone: canonical for canonical, bone in mapping.items()}
    children: dict[str, list[str]] = {}

    for bone in bone_names:
        parent = parents.get(bone)
        if parent is not None:
            children.setdefault(parent, []).append(bone)

    groups: list[BoneGroup] = []

    for bone in bone_names:
        parent = parents.get(bone)
        if bone in mapped_bones or parent not in mapped_bones:
            continue

        members = _collect_subtree(bone, children, mapped_bones)
        groups.append(
            BoneGroup(
                root=bone,
                members=members,
                attaches_to=role_of[parent],
                kind=_group_kind(bone, children),
            )
        )

    return groups


def _collect_subtree(
    root: str, children: dict[str, list[str]], mapped_bones: set[str]
) -> tuple[str, ...]:
    """Return ``root`` and its descendants, not crossing a mapped bone."""

    collected: list[str] = []
    pending = [root]

    while pending:
        bone = pending.pop(0)
        collected.append(bone)
        pending.extend(
            child for child in children.get(bone, ()) if child not in mapped_bones
        )

    return tuple(collected)


def _group_kind(root: str, children: dict[str, list[str]]) -> str:
    """Classify a group: several chains off one bone look like fingers."""

    if len(children.get(root, ())) >= _FINGER_CHAIN_COUNT:
        return "fingers"

    return "chain"


# Canonical roles a rig may legitimately spell as a run of bones. A spine
# is the common case: rigs give it several segments, the canonical skeleton
# has one. Limbs are not here -- a rig with two forearm bones is a twist
# setup, and splitting a rotation across a twist bone is wrong.
_CHAINABLE_ROLES = frozenset({CanonicalBoneName.SPINE, CanonicalBoneName.NECK})


def bone_chains_for(
    mapping: dict[CanonicalBoneName, str],
    groups: list[BoneGroup],
    parents: dict[str, str | None],
) -> dict[CanonicalBoneName, tuple[str, ...]]:
    """Extend chainable roles with the straight run of bones above them.

    A rig whose spine is ``spine.001..004`` maps only ``spine.001`` by name;
    the other three land in a group. They are the same anatomical spine, so
    they join the role and share its rotation rather than staying rigid.

    Only a **straight** run qualifies: a group that branches is a set of
    separate chains (fingers), not one longer bone.
    """

    chains: dict[CanonicalBoneName, tuple[str, ...]] = {}

    for group in groups:
        role = group.attaches_to
        primary = mapping.get(role)

        if role not in _CHAINABLE_ROLES or primary is None:
            continue
        if group.is_fingers or not _is_straight_run(group, parents):
            continue

        chains[role] = (primary, *group.members)

    return chains


def _is_straight_run(group: BoneGroup, parents: dict[str, str | None]) -> bool:
    """Return whether a group is one unbranched line of bones.

    A branching group is several chains sharing a parent -- fingers off a
    hand, or a strap rig -- not one anatomical bone split into segments.
    Splitting a rotation across those would twist them apart.
    """

    members = set(group.members)
    child_counts = Counter(
        parents.get(member) for member in group.members if parents.get(member) in members
    )

    return all(count <= 1 for count in child_counts.values())


def attachment_points_for(groups: list[BoneGroup]) -> dict[str, str]:
    """Return the ``slot -> rig bone`` map for the finger groups found."""

    by_role = {
        group.attaches_to: group.root for group in groups if group.is_fingers
    }

    return {
        slot: by_role[role] for slot, _label, role in ATTACHMENT_SLOTS if role in by_role
    }
