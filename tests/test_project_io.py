"""Tests for project.mcap persistence (roadmap Phase 8)."""

import json
from pathlib import Path

import numpy as np
import pytest

from app.core.project import MotionCaptureProject
from app.core.project_io import (
    ProjectFormatError,
    ProjectIOError,
    ProjectVersionError,
    load_project,
    save_project,
)
from app.models.corrections import CorrectionLayer
from app.models.keypoints import RawPose
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence
from app.models.rig import RigClip
from app.models.skeleton import CANONICAL_SKELETON, CanonicalBoneName, SkeletonClip, SkeletonPose
from app.pose.schemas import MEDIAPIPE_POSE_SCHEMA_ID
from app.video.video_loader import VideoMetadata


def _metadata(path: Path) -> VideoMetadata:
    return VideoMetadata(path=path, frame_count=10, fps=25.0, width=320, height=240)


def _raw(frame_index: int, *, with_world: bool) -> RawPose:
    return RawPose(
        schema_id=MEDIAPIPE_POSE_SCHEMA_ID,
        frame_index=frame_index,
        timestamp=frame_index / 25.0,
        person_index=0,
        points=np.full((33, 2), float(frame_index)),
        visibility=np.linspace(0.0, 1.0, 33),
        world_points=np.full((33, 3), 0.1 * frame_index) if with_world else None,
        depth_source="mediapipe_world" if with_world else "none",
    )


def _canonical(frame_index: int) -> PoseFrame:
    joints = {
        name: Joint(
            name=name,
            position=Vector3(float(index), float(index) + 0.5, 0.0),
            confidence=0.9,
        )
        for index, name in enumerate(JointName)
    }
    return PoseFrame(
        frame_index=frame_index, timestamp=frame_index / 25.0, joints=joints
    )


def _sequence(video_path: Path, *, with_world: bool = True) -> PoseSequence:
    track = PersonTrack(track_id="person_0", depth_source="none")
    for frame_index in (1, 2, 5):  # gaps at 0, 3, 4, 6..9
        track.raw_frames[frame_index] = _raw(frame_index, with_world=with_world)
        track.frames[frame_index] = _canonical(frame_index)
    if with_world:
        track.depth_source = "mediapipe_world"

    sequence = PoseSequence(
        video_path=video_path, frame_count=10, fps=25.0, width=320, height=240
    )
    sequence.add_track(track, make_active=True)
    return sequence


def _project(video_path: Path) -> MotionCaptureProject:
    return MotionCaptureProject(name="Test", video_metadata=_metadata(video_path))


def test_save_creates_the_expected_layout(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(project_dir, _project(video), _sequence(video), detector_backend="mediapipe")

    assert (project_dir / "project.json").is_file()
    assert (project_dir / "poses" / "raw" / "person_0.npz").is_file()
    assert (project_dir / "poses" / "raw" / "person_0.json").is_file()
    assert (project_dir / "poses" / "canonical" / "person_0.npz").is_file()


def test_round_trip_preserves_analysis(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"
    original = _sequence(video, with_world=True)

    save_project(project_dir, _project(video), original, detector_backend="mediapipe")
    loaded = load_project(project_dir)

    assert loaded.project.name == "Test"
    assert loaded.project.project_path == project_dir

    sequence = loaded.pose_sequence
    assert sequence is not None
    assert sequence.frame_count == 10
    assert sequence.active_track_id == "person_0"

    track = sequence.active_track
    assert track.detected_indices() == [1, 2, 5]
    assert track.depth_source == "mediapipe_world"

    pose = track.pose_at(2)
    assert pose.timestamp == pytest.approx(2 / 25.0)
    knee = pose.joints[JointName.LEFT_KNEE]
    original_knee = original.active_track.frames[2].joints[JointName.LEFT_KNEE]
    assert knee.position.x == pytest.approx(original_knee.position.x)
    assert knee.confidence == pytest.approx(0.9)

    raw = track.raw_frames[5]
    assert raw.points.shape == (33, 2)
    assert raw.world_points.shape == (33, 3)
    assert raw.world_points[0, 0] == pytest.approx(0.5)


def test_round_trip_without_world_landmarks(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(project_dir, _project(video), _sequence(video, with_world=False))
    track = load_project(project_dir).pose_sequence.active_track

    assert track.raw_frames[1].world_points is None
    assert track.depth_source == "none"


def test_round_trip_preserves_corrections(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    layer = CorrectionLayer(track_id="person_0")
    layer.set(2, JointName.LEFT_WRIST, Vector3(11.0, 22.0, 0.0))
    layer.set(5, JointName.LEFT_WRIST, Vector3(33.0, 44.0, 0.0))

    save_project(
        project_dir,
        _project(video),
        _sequence(video),
        corrections={"person_0": layer},
    )
    loaded = load_project(project_dir)

    restored = loaded.corrections["person_0"]
    assert restored.get(2, JointName.LEFT_WRIST) == Vector3(11.0, 22.0, 0.0)
    assert restored.keyframes_for(JointName.LEFT_WRIST) == [2, 5]


def _skeleton_clip() -> SkeletonClip:
    from app.math.rotations import Quaternion

    bones = CANONICAL_SKELETON.bone_names()
    poses = [
        SkeletonPose(
            frame_index=frame_index,
            bone_rotations={name: Quaternion.identity() for name in bones},
            root_translation=Vector3(float(frame_index), 1.0, 0.0),
        )
        for frame_index in (1, 2, 5)
    ]
    return SkeletonClip(
        skeleton=CANONICAL_SKELETON,
        fps=25.0,
        frame_range=(1, 5),
        bone_lengths={name: 1.5 for name in bones},
        poses=poses,
    )


def test_round_trip_preserves_the_skeleton_clip(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(
        project_dir,
        _project(video),
        _sequence(video),
        skeleton_clip=_skeleton_clip(),
    )
    restored = load_project(project_dir).skeleton_clip

    assert restored is not None
    assert [pose.frame_index for pose in restored.poses] == [1, 2, 5]
    assert restored.frame_range == (1, 5)
    assert restored.bone_lengths[CanonicalBoneName.SPINE] == 1.5
    assert restored.poses[2].root_translation.x == 5.0


def _rig_clip() -> RigClip:
    from app.math.rotations import Quaternion

    return RigClip(
        rig_id="mixamo",
        fps=30.0,
        frame_range=(1, 5),
        frame_indices=[1, 2, 5],
        bone_order=["mixamorig:Spine1", "mixamorig:LeftArm"],
        bone_curves={
            "mixamorig:Spine1": [Quaternion.identity()] * 3,
            "mixamorig:LeftArm": [Quaternion(0.7071, 0.0, 0.0, 0.7071)] * 3,
        },
        root_curve=[Vector3(1.0, 2.0, 3.0)] * 3,
    )


def test_round_trip_preserves_the_rig_clip(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(
        project_dir, _project(video), _sequence(video), rig_clip=_rig_clip()
    )
    restored = load_project(project_dir).rig_clip

    assert restored is not None
    assert restored.rig_id == "mixamo"
    assert restored.bone_order == ["mixamorig:Spine1", "mixamorig:LeftArm"]
    assert restored.frame_indices == [1, 2, 5]
    assert restored.bone_curves["mixamorig:LeftArm"][0].w == pytest.approx(0.7071)
    assert restored.root_curve[0] == Vector3(1.0, 2.0, 3.0)


def test_empty_corrections_are_not_written(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(
        project_dir,
        _project(video),
        _sequence(video),
        corrections={"person_0": CorrectionLayer(track_id="person_0")},
    )

    assert not (project_dir / "corrections").exists()
    assert load_project(project_dir).corrections == {}


def test_save_without_analysis_still_round_trips(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(project_dir, _project(video), None)
    loaded = load_project(project_dir)

    assert loaded.pose_sequence is None
    assert loaded.project.video_metadata.frame_count == 10


def test_re_save_keeps_created_timestamp(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    video = tmp_path / "clip.mp4"

    save_project(project_dir, _project(video), None)
    created = json.loads((project_dir / "project.json").read_text())["created"]

    save_project(project_dir, _project(video), None)
    document = json.loads((project_dir / "project.json").read_text())

    assert document["created"] == created


def test_save_without_video_raises(tmp_path: Path) -> None:
    with pytest.raises(ProjectIOError):
        save_project(tmp_path / "p.mcap", MotionCaptureProject(name="x"), None)


def test_load_missing_directory_raises_format_error(tmp_path: Path) -> None:
    with pytest.raises(ProjectFormatError):
        load_project(tmp_path / "nope.mcap")


def test_load_newer_version_raises_version_error(tmp_path: Path) -> None:
    project_dir = tmp_path / "p.mcap"
    save_project(project_dir, _project(tmp_path / "clip.mp4"), None)

    document = json.loads((project_dir / "project.json").read_text())
    document["schema_version"] = 999
    (project_dir / "project.json").write_text(json.dumps(document))

    with pytest.raises(ProjectVersionError):
        load_project(project_dir)
