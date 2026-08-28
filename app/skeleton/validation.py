"""Sanity checks on a solved :class:`SkeletonClip` and its source poses."""

import statistics

from app.math.coordinates import CoordinateSpace, image_to_canonical
from app.math.vectors import length, subtract
from app.models.corrections import CorrectionLayer, effective_pose
from app.models.pose import Vector3
from app.models.pose_sequence import PoseSequence
from app.models.skeleton import (
    CANONICAL_SKELETON,
    CanonicalSkeleton,
    SkeletonClip,
)

_LENGTH_CV_THRESHOLD = 0.30  # per-bone length coefficient of variation
_MIN_CONFIDENCE = 1e-6


def validate_skeleton_clip(clip: SkeletonClip) -> list[str]:
    """Return structural problems with ``clip`` (empty when it looks sound)."""

    issues: list[str] = []
    known_bones = set(clip.skeleton.bone_names())

    for definition in clip.skeleton.bones:
        if definition.parent is not None and definition.parent not in known_bones:
            issues.append(
                f"bone '{definition.name.value}' has unknown parent "
                f"'{definition.parent.value}'"
            )

    for name, bone_length in clip.bone_lengths.items():
        if bone_length <= 0.0:
            issues.append(f"bone '{name.value}' has no measured length")

    for pose in clip.poses:
        for name, rotation in pose.bone_rotations.items():
            if not rotation.is_unit():
                issues.append(
                    f"frame {pose.frame_index}: bone '{name.value}' rotation "
                    "is not a unit quaternion"
                )

    if not clip.poses:
        issues.append("clip has no solved frames")

    return issues


def bone_length_report(
    pose_sequence: PoseSequence,
    skeleton: CanonicalSkeleton = CANONICAL_SKELETON,
    correction_layer: CorrectionLayer | None = None,
) -> list[str]:
    """Flag bones whose measured length is unstable across frames.

    A rigid limb should keep a roughly constant length; large variation
    points at bad detections or heavy 2D foreshortening.
    """

    track = pose_sequence.active_track
    if track is None:
        return ["pose sequence has no active track"]

    samples: dict[str, list[float]] = {
        definition.name.value: [] for definition in skeleton.bones
    }

    def canonical(point: Vector3) -> Vector3:
        if track.space is CoordinateSpace.CANONICAL_WORLD:
            return point
        return image_to_canonical(point.x, point.y)

    for frame_index in sorted(track.frames):
        detected = track.pose_at(frame_index)
        corrections = (
            correction_layer.corrected_joints(frame_index)
            if correction_layer is not None
            else {}
        )
        merged = effective_pose(
            frame_index,
            detected.timestamp if detected else 0.0,
            detected,
            corrections,
        )
        if merged is None:
            continue

        for definition in skeleton.bones:
            parent = merged.joints.get(definition.parent_joint)
            child = merged.joints.get(definition.child_joint)
            if (
                parent is None
                or child is None
                or parent.confidence <= _MIN_CONFIDENCE
                or child.confidence <= _MIN_CONFIDENCE
            ):
                continue
            samples[definition.name.value].append(
                length(subtract(canonical(child.position), canonical(parent.position)))
            )

    notes: list[str] = []
    for bone_name, values in samples.items():
        if len(values) < 3:
            continue
        mean = statistics.fmean(values)
        if mean <= 0.0:
            continue
        cv = statistics.pstdev(values) / mean
        if cv > _LENGTH_CV_THRESHOLD:
            notes.append(f"bone '{bone_name}' length varies a lot (cv {cv:.2f})")

    return notes
