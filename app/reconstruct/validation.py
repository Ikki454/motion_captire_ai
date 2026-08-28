"""Quality checks on a reconstructed 3D pose sequence."""

import statistics

from app.math.vectors import length, subtract
from app.models.pose_sequence import PoseSequence
from app.models.skeleton import CANONICAL_SKELETON, CanonicalBoneName, CanonicalSkeleton

_LENGTH_CV_THRESHOLD = 0.30
_SYMMETRY_RATIO = 1.35

_SYMMETRIC_PAIRS: tuple[tuple[CanonicalBoneName, CanonicalBoneName], ...] = (
    (CanonicalBoneName.LEFT_UPPER_ARM, CanonicalBoneName.RIGHT_UPPER_ARM),
    (CanonicalBoneName.LEFT_LOWER_ARM, CanonicalBoneName.RIGHT_LOWER_ARM),
    (CanonicalBoneName.LEFT_UPPER_LEG, CanonicalBoneName.RIGHT_UPPER_LEG),
    (CanonicalBoneName.LEFT_LOWER_LEG, CanonicalBoneName.RIGHT_LOWER_LEG),
)


def reconstruction_quality_report(
    pose_sequence: PoseSequence,
    skeleton: CanonicalSkeleton = CANONICAL_SKELETON,
) -> list[str]:
    """Flag unstable or asymmetric limb lengths in a 3D track."""

    track = pose_sequence.active_track
    if track is None:
        return ["pose sequence has no active track"]

    samples: dict[CanonicalBoneName, list[float]] = {
        bone.name: [] for bone in skeleton.bones
    }

    for pose in track.frames.values():
        for bone in skeleton.bones:
            parent = pose.joints.get(bone.parent_joint)
            child = pose.joints.get(bone.child_joint)
            if (
                parent is None
                or child is None
                or parent.confidence <= 0.0
                or child.confidence <= 0.0
            ):
                continue
            samples[bone.name].append(
                length(subtract(child.position, parent.position))
            )

    notes: list[str] = []
    medians: dict[CanonicalBoneName, float] = {}

    for name, values in samples.items():
        if len(values) < 3:
            continue
        mean = statistics.fmean(values)
        medians[name] = statistics.median(values)
        if mean > 0.0 and statistics.pstdev(values) / mean > _LENGTH_CV_THRESHOLD:
            notes.append(f"bone '{name.value}' length is unstable")

    for left, right in _SYMMETRIC_PAIRS:
        if left not in medians or right not in medians:
            continue
        low = min(medians[left], medians[right])
        high = max(medians[left], medians[right])
        if low > 0.0 and high / low > _SYMMETRY_RATIO:
            notes.append(
                f"{left.value} / {right.value} lengths differ by "
                f"{(high / low - 1) * 100:.0f}%"
            )

    return notes
