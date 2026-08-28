"""Turn a canonical keypoint sequence into a hierarchical skeleton clip.

A track in ``IMAGE_PIXELS`` space gives a **2D-constrained** skeleton
(bone rotations lie in the image plane after the y-up conversion). A track
already in ``CANONICAL_WORLD`` (e.g. from a 3D reconstruction backend) is
used as-is, giving real 3D bone rotations from the same code.
"""

import statistics

from app.math.coordinates import CoordinateSpace, image_to_canonical
from app.math.rotations import Quaternion, shortest_arc
from app.math.vectors import length, normalize, subtract
from app.models.corrections import CorrectionLayer, effective_pose
from app.models.pose import JointName, PoseFrame, Vector3
from app.models.pose_sequence import PoseSequence
from app.models.skeleton import (
    CANONICAL_SKELETON,
    BoneDefinition,
    CanonicalBoneName,
    CanonicalSkeleton,
    SkeletonClip,
    SkeletonPose,
)

_MIN_CONFIDENCE = 1e-6


def solve_skeleton(
    pose_sequence: PoseSequence,
    skeleton: CanonicalSkeleton = CANONICAL_SKELETON,
    correction_layer: CorrectionLayer | None = None,
) -> SkeletonClip:
    """Solve bone rotations for every analysed frame of ``pose_sequence``.

    Frames with no effective pose are skipped. Within a frame, a bone whose
    parent or child joint is missing gets the identity rotation.
    """

    track = pose_sequence.active_track
    if track is None:
        raise ValueError("pose sequence has no active track")

    frame_indices = sorted(track.frames)
    poses: list[SkeletonPose] = []
    length_samples: dict[CanonicalBoneName, list[float]] = {
        definition.name: [] for definition in skeleton.bones
    }

    for frame_index in frame_indices:
        detected = track.pose_at(frame_index)
        corrections = (
            correction_layer.corrected_joints(frame_index)
            if correction_layer is not None
            else {}
        )
        merged = effective_pose(
            frame_index, detected.timestamp if detected else 0.0, detected, corrections
        )
        if merged is None:
            continue

        canonical = _canonical_positions(merged, track.space)
        poses.append(
            _solve_frame(frame_index, skeleton, canonical, merged, length_samples)
        )

    bone_lengths = {
        name: statistics.median(samples) if samples else 0.0
        for name, samples in length_samples.items()
    }

    frame_range = (
        (frame_indices[0], frame_indices[-1]) if frame_indices else (0, 0)
    )

    return SkeletonClip(
        skeleton=skeleton,
        fps=pose_sequence.fps,
        frame_range=frame_range,
        bone_lengths=bone_lengths,
        poses=poses,
    )


def _canonical_positions(
    pose: PoseFrame, space: CoordinateSpace
) -> dict[JointName, Vector3]:
    if space is CoordinateSpace.CANONICAL_WORLD:
        return {name: joint.position for name, joint in pose.joints.items()}

    return {
        name: image_to_canonical(joint.position.x, joint.position.y)
        for name, joint in pose.joints.items()
    }


def _solve_frame(
    frame_index: int,
    skeleton: CanonicalSkeleton,
    canonical: dict[JointName, Vector3],
    pose: PoseFrame,
    length_samples: dict[CanonicalBoneName, list[float]],
) -> SkeletonPose:
    world_rotations: dict[CanonicalBoneName, Quaternion] = {}
    local_rotations: dict[CanonicalBoneName, Quaternion] = {}

    for bone in skeleton.bones:
        world = _world_rotation(bone, skeleton, canonical, pose)
        world_rotations[bone.name] = world

        parent_world = (
            world_rotations[bone.parent]
            if bone.parent is not None
            else Quaternion.identity()
        )
        local_rotations[bone.name] = parent_world.inverse().multiply(world)

        if _bone_measurable(bone, pose):
            length_samples[bone.name].append(
                length(
                    subtract(
                        canonical[bone.child_joint], canonical[bone.parent_joint]
                    )
                )
            )

    root = canonical.get(JointName.PELVIS, Vector3(0.0, 0.0, 0.0))

    return SkeletonPose(
        frame_index=frame_index,
        bone_rotations=local_rotations,
        root_translation=root,
    )


def _bone_measurable(bone: BoneDefinition, pose: PoseFrame) -> bool:
    parent = pose.joints.get(bone.parent_joint)
    child = pose.joints.get(bone.child_joint)
    return (
        parent is not None
        and child is not None
        and parent.confidence > _MIN_CONFIDENCE
        and child.confidence > _MIN_CONFIDENCE
    )


def _world_rotation(
    bone: BoneDefinition,
    skeleton: CanonicalSkeleton,
    canonical: dict[JointName, Vector3],
    pose: PoseFrame,
) -> Quaternion:
    if not _bone_measurable(bone, pose):
        return Quaternion.identity()

    current = normalize(
        subtract(canonical[bone.child_joint], canonical[bone.parent_joint])
    )
    if length(current) < 0.5:
        return Quaternion.identity()

    return shortest_arc(skeleton.rest_direction(bone), current)
