"""Map a canonical :class:`SkeletonClip` onto a target rig (Level 2 -> Level 3)."""

from app.math.rotations import Quaternion
from app.math.vectors import scale
from app.models.rig import RetargetMap, Rig, RigClip
from app.models.skeleton import CanonicalBoneName, SkeletonClip


def retarget(
    skeleton_clip: SkeletonClip,
    rig: Rig,
    retarget_map: RetargetMap,
) -> RigClip:
    """Produce a :class:`RigClip` for ``rig`` from ``skeleton_clip``.

    Each canonical bone in ``retarget_map.bone_map`` contributes a rotation
    curve for the mapped rig bone: ``offset * canonical_local_rotation``.
    The root translation is scaled by ``rig.unit_scale``. Canonical bones
    that are not mapped are left out; rig bones with no canonical source
    keep their rest pose.
    """

    ordered_pairs: list[tuple[CanonicalBoneName, str]] = [
        (bone.name, retarget_map.bone_map[bone.name])
        for bone in skeleton_clip.skeleton.bones
        if bone.name in retarget_map.bone_map
    ]

    bone_order = [rig_name for _, rig_name in ordered_pairs]
    bone_curves: dict[str, list[Quaternion]] = {name: [] for name in bone_order}
    root_curve = []
    frame_indices = []

    for pose in skeleton_clip.poses:
        frame_indices.append(pose.frame_index)
        root_curve.append(scale(pose.root_translation, rig.unit_scale))

        for canonical_bone, rig_name in ordered_pairs:
            canonical_rotation = pose.bone_rotations.get(
                canonical_bone, Quaternion.identity()
            )
            offset = retarget_map.offset_for(canonical_bone)
            bone_curves[rig_name].append(offset.multiply(canonical_rotation))

    return RigClip(
        rig_id=rig.rig_id,
        fps=skeleton_clip.fps,
        frame_range=skeleton_clip.frame_range,
        frame_indices=frame_indices,
        bone_order=bone_order,
        bone_curves=bone_curves,
        root_curve=root_curve,
    )


def retarget_issues(
    skeleton_clip: SkeletonClip, retarget_map: RetargetMap, rig: Rig | None = None
) -> list[str]:
    """Return notes about what this retarget does and does not drive.

    Two different gaps, reported separately because they mean different
    things: a canonical bone the rig has no counterpart for (the mocap
    data exists but lands nowhere), and a rig attachment point no capture
    backend can feed yet (the bone exists but nothing drives it).
    """

    notes: list[str] = []

    unmapped = [
        bone.name.value
        for bone in skeleton_clip.skeleton.bones
        if bone.name not in retarget_map.bone_map
    ]

    if unmapped:
        notes.append(f"not mapped to the rig: {', '.join(unmapped)}")

    if rig is not None and rig.attachment_points:
        slots = ", ".join(slot for slot, _bone in rig.attachment_points)
        notes.append(
            f"recorded but not driven by any capture backend yet: {slots}"
        )

    return notes
