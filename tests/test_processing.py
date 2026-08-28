"""Tests for the animation cleanup passes (roadmap Phase 14)."""

from pathlib import Path

import numpy as np
import pytest

from app.animation.processing import ProcessingOptions, process_sequence
from app.models.corrections import CorrectionLayer
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence


def _sequence(
    frame_count: int,
    positions: dict[JointName, list[tuple[float, float]]],
    *,
    drop: dict[JointName, set[int]] | None = None,
) -> PoseSequence:
    drop = drop or {}
    track = PersonTrack(track_id="person_0")

    for frame_index in range(frame_count):
        joints: dict[JointName, Joint] = {}
        for joint_name, trajectory in positions.items():
            if frame_index in drop.get(joint_name, set()):
                continue
            x, y = trajectory[frame_index]
            joints[joint_name] = Joint(
                joint_name, Vector3(float(x), float(y), 0.0), 1.0
            )
        if joints:
            track.frames[frame_index] = PoseFrame(
                frame_index, frame_index / 24.0, joints
            )

    sequence = PoseSequence(
        video_path=Path("v.mp4"),
        frame_count=frame_count,
        fps=24.0,
        width=400,
        height=400,
    )
    sequence.add_track(track, make_active=True)
    return sequence


def _still(count: int, x: float, y: float) -> list[tuple[float, float]]:
    return [(x, y)] * count


def test_fill_gaps_interpolates_a_short_gap() -> None:
    trajectory = [(float(i * 10), 0.0) for i in range(10)]
    sequence = _sequence(
        10, {JointName.HEAD: trajectory}, drop={JointName.HEAD: {4, 5, 6}}
    )

    processed, report = process_sequence(
        sequence, ProcessingOptions(fill_gaps=True, max_gap=5)
    )

    track = processed.active_track
    assert report.gaps_filled == 3
    assert track.has_detection(5)
    assert track.frames[5].joints[JointName.HEAD].position.x == pytest.approx(50.0)
    assert track.frames[5].joints[JointName.HEAD].confidence == pytest.approx(0.5)


def test_fill_gaps_leaves_a_gap_longer_than_the_limit() -> None:
    trajectory = [(float(i), 0.0) for i in range(12)]
    sequence = _sequence(
        12, {JointName.HEAD: trajectory}, drop={JointName.HEAD: {3, 4, 5, 6, 7, 8}}
    )

    processed, _ = process_sequence(
        sequence, ProcessingOptions(fill_gaps=True, max_gap=3)
    )

    assert not processed.active_track.has_detection(5)


def test_despike_removes_an_outlier() -> None:
    trajectory = [(100.0, 0.0)] * 9
    trajectory[4] = (400.0, 0.0)  # a spike
    sequence = _sequence(9, {JointName.LEFT_WRIST: trajectory})

    processed, _ = process_sequence(sequence, ProcessingOptions(despike=True))

    assert processed.active_track.frames[4].joints[
        JointName.LEFT_WRIST
    ].position.x == pytest.approx(100.0)


def test_smooth_reduces_frame_to_frame_variation() -> None:
    rng = np.random.default_rng(0)
    base = np.linspace(0.0, 100.0, 40)
    noisy = base + rng.normal(0.0, 5.0, base.size)
    trajectory = [(float(v), 0.0) for v in noisy]
    sequence = _sequence(40, {JointName.LEFT_WRIST: trajectory})

    processed, _ = process_sequence(
        sequence, ProcessingOptions(smooth=True, smoothing_window=9)
    )

    smoothed = [
        processed.active_track.frames[i].joints[JointName.LEFT_WRIST].position.x
        for i in range(40)
    ]
    assert np.std(np.diff(smoothed)) < np.std(np.diff(noisy))


def test_foot_lock_pins_a_stationary_ankle() -> None:
    moving_ankle = [(80.0 + (0.2 if 3 <= i <= 12 else i * 3.0), 300.0) for i in range(16)]
    foot = [(x + 2.0, y + 10.0) for x, y in moving_ankle]
    sequence = _sequence(
        16,
        {
            JointName.LEFT_ANKLE: moving_ankle,
            JointName.LEFT_FOOT: foot,
        },
    )

    processed, _ = process_sequence(
        sequence, ProcessingOptions(foot_lock=True, foot_lock_threshold=1.0)
    )

    planted = [
        processed.active_track.frames[i].joints[JointName.LEFT_ANKLE].position.x
        for i in range(5, 12)
    ]
    assert max(planted) - min(planted) < 0.01


def test_corrections_are_baked_into_the_processed_sequence() -> None:
    sequence = _sequence(6, {JointName.LEFT_WRIST: _still(6, 10.0, 10.0)})
    layer = CorrectionLayer(track_id="person_0")
    layer.set(2, JointName.LEFT_WRIST, Vector3(99.0, 99.0, 0.0))

    processed, _ = process_sequence(sequence, ProcessingOptions(), layer)

    assert processed.active_track.frames[2].joints[
        JointName.LEFT_WRIST
    ].position.x == pytest.approx(99.0)


def test_no_options_reports_no_steps() -> None:
    sequence = _sequence(4, {JointName.HEAD: _still(4, 0.0, 0.0)})

    _, report = process_sequence(sequence, ProcessingOptions())

    assert report.steps == []
