"""Read and write the ``project.mcap`` directory.

Layout::

    project.mcap/
      project.json                  schema_version, name, timestamps, video, analysis
      poses/
        raw/<track_id>.npz          points, visibility, world_points, frame_indices, timestamps
        raw/<track_id>.json         schema_version, schema_id, depth_source, has_world
        canonical/<track_id>.npz    positions, confidence, frame_indices, timestamps
        canonical/<track_id>.json   schema_version, joint_order
      rigs/<rig_id>.json            a copy of the custom rig profile in use

Every JSON file carries ``schema_version``. Loading a file written by a newer
version raises :class:`ProjectVersionError` rather than guessing.

``rigs/`` keeps a project self-contained: a project retargeted onto a custom
rig still opens on a machine whose user profile directory is empty. Only the
profile of the *current* retarget is copied.
"""

import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from app.core.project import MotionCaptureProject
from app.math.coordinates import CoordinateSpace
from app.math.rotations import Quaternion
from app.models.corrections import CorrectionLayer
from app.models.keypoints import RawPose
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence
from app.models.rig import RigClip
from app.models.skeleton import CANONICAL_SKELETON, CanonicalBoneName, SkeletonClip, SkeletonPose
from app.video.video_loader import VideoMetadata

PROJECT_SCHEMA_VERSION = 1

_PROJECT_FILE = "project.json"
_POSES_DIR = "poses"
_CORRECTIONS_DIR = "corrections"
_SKELETON_DIR = "skeleton"
_ANIMATION_DIR = "animation"

RIGS_DIR = "rigs"
"""Sub-directory holding copies of the custom rig profiles a project uses."""

_CANONICAL_JOINT_ORDER: tuple[str, ...] = tuple(joint.value for joint in JointName)
_CANONICAL_BONE_ORDER: tuple[str, ...] = tuple(
    name.value for name in CANONICAL_SKELETON.bone_names()
)


class ProjectIOError(Exception):
    """Base error for reading or writing a project."""


class ProjectFormatError(ProjectIOError):
    """The project directory is missing files or is malformed."""


class ProjectVersionError(ProjectIOError):
    """The project was written by a newer, unsupported version."""


@dataclass
class LoadedProject:
    """The result of :func:`load_project`."""

    project: MotionCaptureProject
    pose_sequence: PoseSequence | None
    corrections: dict[str, CorrectionLayer] = field(default_factory=dict)
    skeleton_clip: SkeletonClip | None = None
    rig_clip: RigClip | None = None


def save_project(
    project_dir: Path,
    project: MotionCaptureProject,
    pose_sequence: PoseSequence | None,
    *,
    detector_backend: str | None = None,
    corrections: Mapping[str, CorrectionLayer] | None = None,
    skeleton_clip: SkeletonClip | None = None,
    rig_clip: RigClip | None = None,
    rig_profile: Mapping[str, Any] | None = None,
) -> None:
    """Write ``project`` and its analysis (if any) to ``project_dir``.

    ``rig_profile`` is the custom rig-profile document to copy into
    ``rigs/`` so the project stays self-contained. Built-in profiles do
    not need copying and should not be passed.

    Raises:
        ProjectIOError: The project has no imported video.
    """

    metadata = project.video_metadata
    if metadata is None:
        raise ProjectIOError("cannot save a project without an imported video")

    project_dir.mkdir(parents=True, exist_ok=True)
    project_file = project_dir / _PROJECT_FILE

    now = datetime.now(UTC).isoformat()
    created = now
    if project_file.exists():
        created = _read_json(project_file).get("created", now)

    document: dict[str, Any] = {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "name": project.name,
        "created": created,
        "modified": now,
        "video": {
            "path": str(metadata.path),
            "frame_count": metadata.frame_count,
            "fps": metadata.fps,
            "width": metadata.width,
            "height": metadata.height,
        },
        "analysis": None,
        "active_track_id": None,
    }

    for regenerated in (
        _POSES_DIR,
        _CORRECTIONS_DIR,
        _SKELETON_DIR,
        _ANIMATION_DIR,
        RIGS_DIR,
    ):
        directory = project_dir / regenerated
        if directory.exists():
            shutil.rmtree(directory)

    if pose_sequence is not None:
        document["analysis"] = {
            "detector_backend": detector_backend,
            "frame_count": pose_sequence.frame_count,
            "fps": pose_sequence.fps,
            "width": pose_sequence.width,
            "height": pose_sequence.height,
        }
        document["active_track_id"] = pose_sequence.active_track_id
        _write_pose_sequence(project_dir / _POSES_DIR, pose_sequence)

    if corrections:
        _write_corrections(project_dir / _CORRECTIONS_DIR, corrections)

    if skeleton_clip is not None and skeleton_clip.poses:
        track_id = (
            pose_sequence.active_track_id
            if pose_sequence is not None
            else "person_0"
        )
        _write_skeleton_clip(
            project_dir / _SKELETON_DIR, track_id or "person_0", skeleton_clip
        )

    if rig_clip is not None and rig_clip.frame_indices:
        _write_rig_clip(project_dir / _ANIMATION_DIR, rig_clip)

    if rig_profile:
        _write_rig_profile(project_dir / RIGS_DIR, rig_profile)

    _write_json(project_file, document)


def load_project(project_dir: Path) -> LoadedProject:
    """Read the project written at ``project_dir``.

    Raises:
        ProjectFormatError: The directory is missing files or malformed.
        ProjectVersionError: A file was written by a newer version.
    """

    project_file = project_dir / _PROJECT_FILE
    if not project_file.exists():
        raise ProjectFormatError(f"no {_PROJECT_FILE} in {project_dir}")

    document = _read_json(project_file)
    _check_version(document, "project")

    try:
        video = document["video"]
        metadata = VideoMetadata(
            path=Path(video["path"]),
            frame_count=int(video["frame_count"]),
            fps=float(video["fps"]),
            width=int(video["width"]),
            height=int(video["height"]),
        )
        project = MotionCaptureProject(
            name=document["name"],
            video_metadata=metadata,
            project_path=project_dir,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProjectFormatError(f"malformed {_PROJECT_FILE}: {error}") from error

    pose_sequence: PoseSequence | None = None
    analysis = document.get("analysis")
    if analysis is not None:
        pose_sequence = _read_pose_sequence(
            project_dir / _POSES_DIR,
            metadata,
            analysis,
            document.get("active_track_id"),
        )

    corrections = _read_corrections(project_dir / _CORRECTIONS_DIR)
    skeleton_clip = _read_skeleton_clip(
        project_dir / _SKELETON_DIR, document.get("active_track_id")
    )
    rig_clip = _read_rig_clip(project_dir / _ANIMATION_DIR)

    return LoadedProject(
        project=project,
        pose_sequence=pose_sequence,
        corrections=corrections,
        skeleton_clip=skeleton_clip,
        rig_clip=rig_clip,
    )


def _write_pose_sequence(poses_dir: Path, sequence: PoseSequence) -> None:
    raw_dir = poses_dir / "raw"
    canonical_dir = poses_dir / "canonical"
    raw_dir.mkdir(parents=True, exist_ok=True)
    canonical_dir.mkdir(parents=True, exist_ok=True)

    for track in sequence.tracks.values():
        _write_raw_track(raw_dir, track)
        _write_canonical_track(canonical_dir, track)


def _write_raw_track(raw_dir: Path, track: PersonTrack) -> None:
    indices = sorted(track.raw_frames)
    raws = [track.raw_frames[index] for index in indices]
    has_world = bool(raws) and all(raw.world_points is not None for raw in raws)

    arrays: dict[str, np.ndarray] = {
        "frame_indices": np.array(indices, dtype=np.int64),
    }
    if raws:
        arrays["timestamps"] = np.array([raw.timestamp for raw in raws], dtype=np.float64)
        arrays["person_indices"] = np.array(
            [raw.person_index for raw in raws], dtype=np.int64
        )
        arrays["points"] = np.stack(
            [np.asarray(raw.points, dtype=np.float64) for raw in raws]
        )
        arrays["visibility"] = np.stack(
            [np.asarray(raw.visibility, dtype=np.float64) for raw in raws]
        )
        if has_world:
            arrays["world_points"] = np.stack(
                [np.asarray(raw.world_points, dtype=np.float64) for raw in raws]
            )

    np.savez_compressed(raw_dir / f"{track.track_id}.npz", **arrays)
    _write_json(
        raw_dir / f"{track.track_id}.json",
        {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "track_id": track.track_id,
            "schema_id": raws[0].schema_id if raws else "",
            "depth_source": track.depth_source,
            "has_world": has_world,
        },
    )


def _write_canonical_track(canonical_dir: Path, track: PersonTrack) -> None:
    indices = sorted(track.frames)
    joint_count = len(_CANONICAL_JOINT_ORDER)

    positions = np.full((len(indices), joint_count, 3), np.nan, dtype=np.float64)
    confidence = np.zeros((len(indices), joint_count), dtype=np.float64)
    timestamps = np.zeros(len(indices), dtype=np.float64)

    for row, frame_index in enumerate(indices):
        frame = track.frames[frame_index]
        timestamps[row] = frame.timestamp
        for col, joint_value in enumerate(_CANONICAL_JOINT_ORDER):
            joint = frame.joints.get(JointName(joint_value))
            if joint is None:
                continue
            positions[row, col] = (
                joint.position.x,
                joint.position.y,
                joint.position.z,
            )
            confidence[row, col] = joint.confidence

    np.savez_compressed(
        canonical_dir / f"{track.track_id}.npz",
        frame_indices=np.array(indices, dtype=np.int64),
        timestamps=timestamps,
        positions=positions,
        confidence=confidence,
    )
    _write_json(
        canonical_dir / f"{track.track_id}.json",
        {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "track_id": track.track_id,
            "joint_order": list(_CANONICAL_JOINT_ORDER),
            "space": track.space.value,
        },
    )


def _read_pose_sequence(
    poses_dir: Path,
    metadata: VideoMetadata,
    analysis: dict[str, Any],
    active_track_id: str | None,
) -> PoseSequence:
    canonical_dir = poses_dir / "canonical"
    raw_dir = poses_dir / "raw"

    if not canonical_dir.is_dir():
        raise ProjectFormatError(f"missing {canonical_dir}")

    sequence = PoseSequence(
        video_path=metadata.path,
        frame_count=int(analysis.get("frame_count", metadata.frame_count)),
        fps=float(analysis.get("fps", metadata.fps)),
        width=int(analysis.get("width", metadata.width)),
        height=int(analysis.get("height", metadata.height)),
    )

    for canonical_json in sorted(canonical_dir.glob("*.json")):
        track = _read_track(canonical_json.stem, raw_dir, canonical_dir)
        sequence.add_track(track, make_active=track.track_id == active_track_id)

    if active_track_id in sequence.tracks:
        sequence.active_track_id = active_track_id

    return sequence


def _read_track(track_id: str, raw_dir: Path, canonical_dir: Path) -> PersonTrack:
    track = PersonTrack(track_id=track_id)

    canonical_meta = _read_json(canonical_dir / f"{track_id}.json")
    _check_version(canonical_meta, "canonical poses")
    joint_order = [JointName(value) for value in canonical_meta["joint_order"]]
    track.space = CoordinateSpace(
        canonical_meta.get("space", CoordinateSpace.IMAGE_PIXELS.value)
    )

    with np.load(canonical_dir / f"{track_id}.npz") as data:
        frame_indices = data["frame_indices"]
        timestamps = data["timestamps"]
        positions = data["positions"]
        confidence = data["confidence"]

    for row, frame_index in enumerate(frame_indices):
        joints = {
            joint_name: Joint(
                name=joint_name,
                position=Vector3(
                    float(positions[row, col, 0]),
                    float(positions[row, col, 1]),
                    float(positions[row, col, 2]),
                ),
                confidence=float(confidence[row, col]),
            )
            for col, joint_name in enumerate(joint_order)
        }
        track.frames[int(frame_index)] = PoseFrame(
            frame_index=int(frame_index),
            timestamp=float(timestamps[row]),
            joints=joints,
        )

    raw_json = raw_dir / f"{track_id}.json"
    if raw_json.exists():
        raw_meta = _read_json(raw_json)
        _check_version(raw_meta, "raw poses")
        track.depth_source = raw_meta.get("depth_source", "none")
        _read_raw_frames(track, raw_dir / f"{track_id}.npz", raw_meta)

    return track


def _read_raw_frames(track: PersonTrack, npz_path: Path, raw_meta: dict[str, Any]) -> None:
    if not npz_path.exists():
        return

    with np.load(npz_path) as data:
        frame_indices = data["frame_indices"]
        if frame_indices.size == 0:
            return
        timestamps = data["timestamps"]
        person_indices = data["person_indices"]
        points = data["points"]
        visibility = data["visibility"]
        world = data["world_points"] if "world_points" in data.files else None

    schema_id = raw_meta.get("schema_id", "")
    depth_source = raw_meta.get("depth_source", "none")

    for row, frame_index in enumerate(frame_indices):
        track.raw_frames[int(frame_index)] = RawPose(
            schema_id=schema_id,
            frame_index=int(frame_index),
            timestamp=float(timestamps[row]),
            person_index=int(person_indices[row]),
            points=np.asarray(points[row], dtype=np.float64),
            visibility=np.asarray(visibility[row], dtype=np.float64),
            world_points=(
                np.asarray(world[row], dtype=np.float64) if world is not None else None
            ),
            depth_source=depth_source,
        )


def _write_skeleton_clip(
    skeleton_dir: Path, track_id: str, clip: SkeletonClip
) -> None:
    skeleton_dir.mkdir(parents=True, exist_ok=True)
    bone_order = CANONICAL_SKELETON.bone_names()

    frame_indices = np.array([pose.frame_index for pose in clip.poses], dtype=np.int64)
    rotations = np.zeros((len(clip.poses), len(bone_order), 4), dtype=np.float64)
    root = np.zeros((len(clip.poses), 3), dtype=np.float64)

    for row, pose in enumerate(clip.poses):
        for col, bone_name in enumerate(bone_order):
            quaternion = pose.bone_rotations.get(bone_name, Quaternion.identity())
            rotations[row, col] = (
                quaternion.w,
                quaternion.x,
                quaternion.y,
                quaternion.z,
            )
        root[row] = (
            pose.root_translation.x,
            pose.root_translation.y,
            pose.root_translation.z,
        )

    np.savez_compressed(
        skeleton_dir / f"{track_id}.npz",
        frame_indices=frame_indices,
        rotations=rotations,
        root_translation=root,
    )
    _write_json(
        skeleton_dir / f"{track_id}.json",
        {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "track_id": track_id,
            "bone_order": list(_CANONICAL_BONE_ORDER),
            "bone_lengths": {
                name.value: value for name, value in clip.bone_lengths.items()
            },
            "fps": clip.fps,
            "frame_range": list(clip.frame_range),
        },
    )


def _read_skeleton_clip(
    skeleton_dir: Path, active_track_id: str | None
) -> SkeletonClip | None:
    if not skeleton_dir.is_dir():
        return None

    candidates = sorted(skeleton_dir.glob("*.json"))
    if not candidates:
        return None

    chosen = next(
        (path for path in candidates if path.stem == active_track_id),
        candidates[0],
    )
    document = _read_json(chosen)
    _check_version(document, "skeleton")

    if document.get("bone_order") != list(_CANONICAL_BONE_ORDER):
        raise ProjectFormatError("skeleton bone order does not match this version")

    with np.load(chosen.with_suffix(".npz")) as data:
        frame_indices = data["frame_indices"]
        rotations = data["rotations"]
        root = data["root_translation"]

    bone_order = CANONICAL_SKELETON.bone_names()
    poses: list[SkeletonPose] = []

    for row, frame_index in enumerate(frame_indices):
        bone_rotations = {
            bone_name: Quaternion(
                float(rotations[row, col, 0]),
                float(rotations[row, col, 1]),
                float(rotations[row, col, 2]),
                float(rotations[row, col, 3]),
            )
            for col, bone_name in enumerate(bone_order)
        }
        poses.append(
            SkeletonPose(
                frame_index=int(frame_index),
                bone_rotations=bone_rotations,
                root_translation=Vector3(
                    float(root[row, 0]), float(root[row, 1]), float(root[row, 2])
                ),
            )
        )

    bone_lengths = {
        CanonicalBoneName(name): float(value)
        for name, value in document.get("bone_lengths", {}).items()
    }
    frame_range_pair = document.get("frame_range", [0, 0])

    return SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=float(document.get("fps", 0.0)),
        frame_range=(int(frame_range_pair[0]), int(frame_range_pair[1])),
        bone_lengths=bone_lengths,
        poses=poses,
    )


def _write_rig_clip(animation_dir: Path, clip: RigClip) -> None:
    animation_dir.mkdir(parents=True, exist_ok=True)

    frame_count = len(clip.frame_indices)
    rotations = np.zeros((frame_count, len(clip.bone_order), 4), dtype=np.float64)
    root = np.zeros((frame_count, 3), dtype=np.float64)

    for col, bone_name in enumerate(clip.bone_order):
        for row, quaternion in enumerate(clip.bone_curves[bone_name]):
            rotations[row, col] = (
                quaternion.w,
                quaternion.x,
                quaternion.y,
                quaternion.z,
            )

    for row, translation in enumerate(clip.root_curve):
        root[row] = (translation.x, translation.y, translation.z)

    np.savez_compressed(
        animation_dir / f"{clip.rig_id}.npz",
        frame_indices=np.array(clip.frame_indices, dtype=np.int64),
        rotations=rotations,
        root_curve=root,
    )
    _write_json(
        animation_dir / f"{clip.rig_id}.json",
        {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "rig_id": clip.rig_id,
            "bone_order": list(clip.bone_order),
            "fps": clip.fps,
            "frame_range": list(clip.frame_range),
        },
    )


def _read_rig_clip(animation_dir: Path) -> RigClip | None:
    if not animation_dir.is_dir():
        return None

    candidates = sorted(animation_dir.glob("*.json"))
    if not candidates:
        return None

    document = _read_json(candidates[0])
    _check_version(document, "rig animation")

    bone_order = [str(name) for name in document["bone_order"]]

    with np.load(candidates[0].with_suffix(".npz")) as data:
        frame_indices = [int(index) for index in data["frame_indices"]]
        rotations = data["rotations"]
        root = data["root_curve"]

    bone_curves: dict[str, list[Quaternion]] = {}
    for col, bone_name in enumerate(bone_order):
        bone_curves[bone_name] = [
            Quaternion(
                float(rotations[row, col, 0]),
                float(rotations[row, col, 1]),
                float(rotations[row, col, 2]),
                float(rotations[row, col, 3]),
            )
            for row in range(len(frame_indices))
        ]

    root_curve = [
        Vector3(float(root[row, 0]), float(root[row, 1]), float(root[row, 2]))
        for row in range(len(frame_indices))
    ]
    frame_range_pair = document.get("frame_range", [0, 0])

    return RigClip(
        rig_id=str(document["rig_id"]),
        fps=float(document.get("fps", 0.0)),
        frame_range=(int(frame_range_pair[0]), int(frame_range_pair[1])),
        frame_indices=frame_indices,
        bone_order=bone_order,
        bone_curves=bone_curves,
        root_curve=root_curve,
    )


def _write_rig_profile(rigs_dir: Path, profile: Mapping[str, Any]) -> None:
    rig_id = str(profile.get("rig_id", "")).strip()
    if not rig_id:
        raise ProjectIOError("the rig profile to save has no rig_id")

    rigs_dir.mkdir(parents=True, exist_ok=True)
    _write_json(rigs_dir / f"{rig_id}.json", dict(profile))


def _write_corrections(
    corrections_dir: Path, corrections: Mapping[str, CorrectionLayer]
) -> None:
    written = False

    for track_id, layer in corrections.items():
        if layer.is_empty:
            continue

        written = True
        corrections_dir.mkdir(parents=True, exist_ok=True)
        overrides = {
            str(frame_index): {
                joint.value: [position.x, position.y, position.z]
                for joint, position in joints.items()
            }
            for frame_index, joints in sorted(layer.overrides.items())
            if joints
        }
        _write_json(
            corrections_dir / f"{track_id}.json",
            {
                "schema_version": PROJECT_SCHEMA_VERSION,
                "track_id": track_id,
                "overrides": overrides,
            },
        )

    if not written and corrections_dir.exists():
        shutil.rmtree(corrections_dir)


def _read_corrections(corrections_dir: Path) -> dict[str, CorrectionLayer]:
    if not corrections_dir.is_dir():
        return {}

    layers: dict[str, CorrectionLayer] = {}

    for correction_file in sorted(corrections_dir.glob("*.json")):
        document = _read_json(correction_file)
        _check_version(document, "corrections")

        track_id = document.get("track_id", correction_file.stem)
        layer = CorrectionLayer(track_id=track_id)

        for frame_key, joints in document.get("overrides", {}).items():
            for joint_value, coordinates in joints.items():
                layer.set(
                    int(frame_key),
                    JointName(joint_value),
                    Vector3(
                        float(coordinates[0]),
                        float(coordinates[1]),
                        float(coordinates[2]),
                    ),
                )

        layers[track_id] = layer

    return layers


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProjectFormatError(f"cannot read {path}: {error}") from error


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def _check_version(document: dict[str, Any], what: str) -> None:
    version = document.get("schema_version")

    if not isinstance(version, int):
        raise ProjectFormatError(f"{what}: missing or invalid schema_version")

    if version > PROJECT_SCHEMA_VERSION:
        raise ProjectVersionError(
            f"{what}: schema_version {version} is newer than supported "
            f"({PROJECT_SCHEMA_VERSION})"
        )
