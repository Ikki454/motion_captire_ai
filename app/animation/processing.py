"""Opt-in cleanup passes over a canonical pose sequence.

Each step (gap fill, despike, smooth, foot lock) is independent and
parameterised. :func:`process_sequence` applies the enabled ones in order
and bakes any manual corrections into the result.
"""

from dataclasses import dataclass, field
from enum import Enum
from itertools import pairwise

import numpy as np
from scipy.signal import medfilt, savgol_filter

from app.models.corrections import CorrectionLayer, effective_pose
from app.models.pose import Joint, JointName, PoseFrame, Vector3
from app.models.pose_sequence import PersonTrack, PoseSequence

_JOINT_ORDER: tuple[JointName, ...] = tuple(JointName)
_JOINT_INDEX: dict[JointName, int] = {name: i for i, name in enumerate(_JOINT_ORDER)}
_FOOT_CHAINS: tuple[tuple[JointName, ...], ...] = (
    (JointName.LEFT_ANKLE, JointName.LEFT_FOOT),
    (JointName.RIGHT_ANKLE, JointName.RIGHT_FOOT),
)


class SmoothingMethod(str, Enum):
    """How a joint trajectory is smoothed."""

    SAVITZKY_GOLAY = "savitzky_golay"
    MOVING_AVERAGE = "moving_average"


@dataclass
class ProcessingReport:
    """What :func:`process_sequence` actually did."""

    gaps_filled: int = 0
    steps: list[str] = field(default_factory=list)


@dataclass
class ProcessingOptions:
    """Which cleanup passes to run and with what parameters."""

    fill_gaps: bool = False
    max_gap: int = 5
    interpolated_confidence: float = 0.5

    despike: bool = False
    despike_window: int = 3

    smooth: bool = False
    smoothing_method: SmoothingMethod = SmoothingMethod.SAVITZKY_GOLAY
    smoothing_window: int = 7
    smoothing_polyorder: int = 2

    foot_lock: bool = False
    foot_lock_threshold: float = 2.0


def process_sequence(
    pose_sequence: PoseSequence,
    options: ProcessingOptions,
    correction_layer: CorrectionLayer | None = None,
) -> tuple[PoseSequence, ProcessingReport]:
    """Return a cleaned copy of ``pose_sequence`` plus a report.

    Manual corrections are applied first; the enabled passes then run on
    the corrected data.
    """

    track = pose_sequence.active_track
    if track is None:
        raise ValueError("pose sequence has no active track")

    frame_count = max(pose_sequence.frame_count, 0)
    joint_count = len(_JOINT_ORDER)

    positions = np.full((frame_count, joint_count, 3), np.nan, dtype=np.float64)
    confidence = np.zeros((frame_count, joint_count), dtype=np.float64)

    for frame_index in range(frame_count):
        corrections = (
            correction_layer.corrected_joints(frame_index)
            if correction_layer is not None
            else {}
        )
        merged = effective_pose(
            frame_index, 0.0, track.pose_at(frame_index), corrections
        )
        if merged is None:
            continue
        for joint_name, joint in merged.joints.items():
            column = _JOINT_INDEX[joint_name]
            positions[frame_index, column] = (
                joint.position.x,
                joint.position.y,
                joint.position.z,
            )
            confidence[frame_index, column] = joint.confidence

    report = ProcessingReport()

    if options.fill_gaps:
        report.gaps_filled = _fill_gaps(positions, confidence, options)
        report.steps.append("filled gaps")

    if options.despike:
        _despike(positions, confidence, options.despike_window)
        report.steps.append("despiked")

    if options.smooth:
        _smooth(positions, confidence, options)
        report.steps.append("smoothed")

    if options.foot_lock:
        _lock_feet(positions, confidence, options.foot_lock_threshold)
        report.steps.append("locked feet")

    processed = _build_sequence(pose_sequence, track, positions, confidence)
    return processed, report


def _valid_rows(confidence_column: np.ndarray) -> np.ndarray:
    return np.flatnonzero(confidence_column > 0.0)


def _fill_gaps(
    positions: np.ndarray, confidence: np.ndarray, options: ProcessingOptions
) -> int:
    filled = 0

    for column in range(positions.shape[1]):
        known = _valid_rows(confidence[:, column])
        if known.size < 2:
            continue

        for start, end in pairwise(known):
            gap = int(end - start - 1)
            if gap <= 0 or gap > options.max_gap:
                continue

            for axis in range(3):
                positions[start + 1 : end, column, axis] = np.interp(
                    np.arange(start + 1, end),
                    (start, end),
                    (positions[start, column, axis], positions[end, column, axis]),
                )
            confidence[start + 1 : end, column] = options.interpolated_confidence
            filled += gap

    return filled


def _despike(
    positions: np.ndarray, confidence: np.ndarray, window: int
) -> None:
    kernel = window if window % 2 == 1 else window + 1

    for column in range(positions.shape[1]):
        rows = _valid_rows(confidence[:, column])
        if rows.size < kernel:
            continue
        for axis in range(3):
            positions[rows, column, axis] = medfilt(
                positions[rows, column, axis], kernel_size=kernel
            )


def _smooth(
    positions: np.ndarray, confidence: np.ndarray, options: ProcessingOptions
) -> None:
    for column in range(positions.shape[1]):
        rows = _valid_rows(confidence[:, column])
        if rows.size < 3:
            continue

        window = min(options.smoothing_window, rows.size)
        if window % 2 == 0:
            window -= 1
        if window < 3:
            continue

        for axis in range(3):
            series = positions[rows, column, axis]
            if options.smoothing_method is SmoothingMethod.MOVING_AVERAGE:
                positions[rows, column, axis] = _moving_average(series, window)
            else:
                polyorder = min(options.smoothing_polyorder, window - 1)
                positions[rows, column, axis] = savgol_filter(
                    series, window, polyorder
                )


def _moving_average(series: np.ndarray, window: int) -> np.ndarray:
    padded = np.pad(series, window // 2, mode="edge")
    kernel = np.ones(window) / window
    return np.convolve(padded, kernel, mode="valid")[: series.size]


def _lock_feet(
    positions: np.ndarray, confidence: np.ndarray, threshold: float
) -> None:
    for chain in _FOOT_CHAINS:
        anchor = _JOINT_INDEX[chain[0]]
        rows = _valid_rows(confidence[:, anchor])
        if rows.size < 3:
            continue

        speeds = np.linalg.norm(
            np.diff(positions[rows, anchor, :2], axis=0), axis=1
        )
        planted = np.concatenate(([False], speeds < threshold))

        for run_start, run_end in _runs(planted):
            span = rows[run_start:run_end]
            for joint_name in chain:
                column = _JOINT_INDEX[joint_name]
                if np.all(confidence[span, column] > 0.0):
                    median = np.median(positions[span, column, :], axis=0)
                    positions[span, column, :] = median


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None

    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index))
            start = None

    if start is not None:
        runs.append((start, len(mask)))

    return [run for run in runs if run[1] - run[0] >= 2]


def _build_sequence(
    source: PoseSequence,
    track: PersonTrack,
    positions: np.ndarray,
    confidence: np.ndarray,
) -> PoseSequence:
    fps = source.fps if source.fps > 0 else 0.0
    new_track = PersonTrack(track_id=track.track_id, depth_source=track.depth_source)

    for frame_index in range(positions.shape[0]):
        joints: dict[JointName, Joint] = {}
        for column, joint_name in enumerate(_JOINT_ORDER):
            if confidence[frame_index, column] <= 0.0:
                continue
            point = positions[frame_index, column]
            if np.isnan(point).any():
                continue
            joints[joint_name] = Joint(
                name=joint_name,
                position=Vector3(float(point[0]), float(point[1]), float(point[2])),
                confidence=float(confidence[frame_index, column]),
            )
        if joints:
            timestamp = frame_index / fps if fps > 0 else 0.0
            new_track.frames[frame_index] = PoseFrame(
                frame_index=frame_index, timestamp=timestamp, joints=joints
            )

    processed = PoseSequence(
        video_path=source.video_path,
        frame_count=source.frame_count,
        fps=source.fps,
        width=source.width,
        height=source.height,
    )
    processed.add_track(new_track, make_active=True)
    return processed
