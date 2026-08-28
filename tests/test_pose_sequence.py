"""Tests for PersonTrack / PoseSequence (roadmap Phase 7)."""

from pathlib import Path

from app.models.pose import JointName, PoseFrame
from app.models.pose_sequence import PersonTrack, PoseSequence


def _pose(frame_index: int) -> PoseFrame:
    return PoseFrame(frame_index=frame_index, timestamp=0.0, joints={})


def test_track_reports_detections_and_gaps() -> None:
    track = PersonTrack(track_id="person_0")
    track.frames[1] = _pose(1)
    track.frames[4] = _pose(4)

    assert track.detection_count == 2
    assert track.detected_indices() == [1, 4]
    assert track.has_detection(1) is True
    assert track.has_detection(2) is False
    assert track.pose_at(2) is None
    assert track.pose_at(4).frame_index == 4


def test_sequence_add_track_sets_active_by_default() -> None:
    sequence = PoseSequence(
        video_path=Path("v.mp4"), frame_count=10, fps=24.0, width=64, height=48
    )
    track = PersonTrack(track_id="person_0")

    sequence.add_track(track)

    assert sequence.active_track_id == "person_0"
    assert sequence.active_track is track


def test_sequence_second_track_does_not_steal_active() -> None:
    sequence = PoseSequence(
        video_path=Path("v.mp4"), frame_count=10, fps=24.0, width=64, height=48
    )
    sequence.add_track(PersonTrack(track_id="person_0"))
    sequence.add_track(PersonTrack(track_id="person_1"))

    assert sequence.active_track_id == "person_0"
    assert set(sequence.tracks) == {"person_0", "person_1"}


def test_sequence_active_pose_at_reads_active_track() -> None:
    sequence = PoseSequence(
        video_path=Path("v.mp4"), frame_count=10, fps=24.0, width=64, height=48
    )
    track = PersonTrack(track_id="person_0")
    track.frames[3] = PoseFrame(
        frame_index=3, timestamp=0.1, joints=dict.fromkeys(JointName)
    )
    sequence.add_track(track)

    assert sequence.active_pose_at(3) is not None
    assert sequence.active_pose_at(2) is None
