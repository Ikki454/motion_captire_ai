"""Application-level orchestration for a motion capture project.

The controller owns the :class:`MotionCaptureProject` and coordinates the
services that operate on it. UI code talks to this class instead of calling
video or pose services directly, which keeps UI logic separate from
processing logic.
"""

import os
from collections.abc import Callable
from pathlib import Path

import numpy as np

from app.animation.processing import ProcessingOptions, ProcessingReport, process_sequence
from app.core.commands import (
    ClearKeypointCorrection,
    CommandStack,
    PropagateKeypointCorrection,
    SetKeypointCorrection,
)
from app.core.project import MotionCaptureProject
from app.core.project_io import RIGS_DIR, ProjectIOError, load_project, save_project
from app.core.tasks import CancelToken, TaskManager, TaskResult, TaskStatus
from app.export.animation_export import export_animation
from app.export.bvh_exporter import export_bvh
from app.models.corrections import CorrectionLayer, effective_pose
from app.models.pose import JointName, PoseFrame, Vector3
from app.models.pose_sequence import PoseSequence
from app.models.rig import RigClip
from app.models.skeleton import SkeletonClip
from app.plugins.registry import BackendRegistry
from app.plugins.types import BackendEntry
from app.pose.analysis import analyze_video_parallel
from app.pose.detector_base import PoseDetector
from app.pose.mapping import to_canonical
from app.pose.registry import build_pose_backend_registry
from app.reconstruct.backends import build_reconstruction_registry
from app.reconstruct.validation import reconstruction_quality_report
from app.retarget.armature_import import (
    ArmatureDump,
    BoneGroup,
    auto_map,
    bone_chains_for,
    detect_bone_groups,
    load_armature_dump,
)
from app.retarget.retargeter import retarget as run_retarget
from app.retarget.retargeter import retarget_issues
from app.retarget.rig_registry import (
    RigProfileError,
    RigProfileInfo,
    RigRegistry,
    build_rig_registry,
    user_rig_dir,
)
from app.skeleton.solver import solve_skeleton
from app.skeleton.validation import bone_length_report, validate_skeleton_clip
from app.video.frame_reader import FrameReader
from app.video.frame_stream import FrameStream
from app.video.playback import PlaybackController
from app.video.video_loader import VideoLoader, VideoMetadata


class ProjectController:
    """Coordinate operations on a single motion capture project."""

    def __init__(
        self,
        project: MotionCaptureProject | None = None,
        video_loader: VideoLoader | None = None,
        pose_registry: BackendRegistry | None = None,
        task_manager: TaskManager | None = None,
        rig_dir: Path | None = None,
    ) -> None:
        self._project = project or MotionCaptureProject(name="Untitled")
        self._video_loader = video_loader or VideoLoader()
        self._pose_registry = pose_registry or build_pose_backend_registry()
        self._task_manager = task_manager or TaskManager()
        self._frame_reader: FrameReader | None = None
        self._frame_stream: FrameStream | None = None
        self._current_frame_index = 0
        self._playback = PlaybackController(fps=0.0)
        self._analysis_workers = max(1, min(4, os.cpu_count() or 1))
        self._detector: PoseDetector | None = None
        self._detector_backend_id: str | None = None
        self._pose_sequence: PoseSequence | None = None
        self._active_analysis_token: CancelToken | None = None
        self._correction_layers: dict[str, CorrectionLayer] = {}
        self._commands = CommandStack()
        self._skeleton_clip: SkeletonClip | None = None
        self._user_rig_dir = rig_dir if rig_dir is not None else user_rig_dir()
        self._rig_registry = self._build_rig_registry()
        self._rig_clip: RigClip | None = None
        self._retargeted_rig_id: str | None = None
        self._processed_sequence: PoseSequence | None = None
        self._reconstruction_registry = build_reconstruction_registry()
        self._reconstructed_sequence: PoseSequence | None = None
        self._reconstruction_backend_id: str | None = None

    @property
    def project(self) -> MotionCaptureProject:
        """Return the project currently managed by the controller."""

        return self._project

    @property
    def has_video(self) -> bool:
        """Return whether a video is currently loaded."""

        return self._frame_reader is not None

    @property
    def frame_count(self) -> int:
        """Return the frame count of the imported video, or ``0`` if none."""

        metadata = self._project.video_metadata

        return metadata.frame_count if metadata is not None else 0

    @property
    def current_frame_index(self) -> int:
        """Return the index of the frame currently navigated to."""

        return self._current_frame_index

    @property
    def current_timestamp(self) -> float:
        """Return the timestamp in seconds of the current frame.

        Returns ``0.0`` when no video is loaded or the frame rate is
        unknown.
        """

        metadata = self._project.video_metadata

        if metadata is None or metadata.fps <= 0:
            return 0.0

        return self._current_frame_index / metadata.fps

    @property
    def is_playing(self) -> bool:
        """Return whether playback is currently running."""

        return self._playback.is_playing

    @property
    def frame_interval_ms(self) -> int:
        """Return the delay between frames in milliseconds during playback."""

        return self._playback.frame_interval_ms

    def import_video(self, video_path: str | Path) -> VideoMetadata:
        """Load ``video_path`` and attach its metadata to the project.

        Also opens a :class:`FrameReader` for the video so frames can be
        read via :meth:`read_frame`. A previously opened reader is closed.

        Args:
            video_path: Path to the video file to import.

        Returns:
            The extracted :class:`VideoMetadata`.

        Raises:
            FileNotFoundError: The file does not exist.
            RuntimeError: The file exists but cannot be opened as a video.
        """

        self._cancel_active_analysis()
        self._stop_frame_stream()

        metadata = self._video_loader.load_metadata(video_path)
        self._open_frame_reader(metadata.path)
        self._project.video_metadata = metadata
        self._current_frame_index = 0
        self._playback = PlaybackController(fps=metadata.fps)
        self._pose_sequence = None
        self._correction_layers = {}
        self._commands.clear()
        self._invalidate_downstream()
        return metadata

    def read_frame(self, index: int) -> np.ndarray:
        """Return the frame at ``index`` from the imported video (BGR).

        This does not change the current navigation position; use
        :meth:`go_to_frame` for that.

        Raises:
            RuntimeError: No video has been imported yet.
            IndexError: ``index`` is out of range.
        """

        if self._frame_reader is None:
            raise RuntimeError("No video has been imported")

        return self._frame_reader.read_frame(index)

    def go_to_frame(self, index: int) -> np.ndarray:
        """Navigate to ``index`` and return the frame there (BGR).

        ``index`` is clamped to ``[0, frame_count - 1]`` when the frame
        count is known, so navigating past either end is a no-op.

        Raises:
            RuntimeError: No video has been imported yet.
            IndexError: The frame could not be located.
        """

        if self._frame_reader is None:
            raise RuntimeError("No video has been imported")

        self._stop_frame_stream()  # a seek invalidates the prefetch buffer

        target = self._clamp_frame_index(index)
        frame = self._frame_reader.read_frame(target)
        self._current_frame_index = target
        return frame

    def step_frame(self, delta: int) -> np.ndarray:
        """Navigate by ``delta`` frames (clamped) and return the frame."""

        return self.go_to_frame(self._current_frame_index + delta)

    def play(self) -> None:
        """Start playback, if a video is loaded."""

        if self.has_video:
            self._playback.play()
            self._start_frame_stream()

    def pause(self) -> None:
        """Pause playback."""

        self._playback.pause()
        self._stop_frame_stream()

    def stop(self) -> None:
        """Pause playback and rewind to the first frame."""

        self._playback.pause()
        self._stop_frame_stream()
        self._current_frame_index = 0

    def _start_frame_stream(self) -> None:
        self._stop_frame_stream()

        metadata = self._project.video_metadata
        if metadata is None:
            return

        try:
            self._frame_stream = FrameStream(
                FrameReader(metadata.path), self._current_frame_index + 1
            )
        except (OSError, RuntimeError):
            self._frame_stream = None

    def _stop_frame_stream(self) -> None:
        if self._frame_stream is not None:
            self._frame_stream.close()
            self._frame_stream = None

    @property
    def detector_backend_id(self) -> str | None:
        """Return the id of the selected detector backend, if any."""

        return self._detector_backend_id

    def available_detectors(self) -> list[BackendEntry]:
        """Return the pose-detection backends that can be used."""

        return self._pose_registry.available()

    def unavailable_detectors(self) -> list[BackendEntry]:
        """Return the registered backends that cannot be used, with reasons."""

        return self._pose_registry.unavailable()

    def set_detector(self, backend_id: str) -> None:
        """Select and instantiate the pose-detection backend ``backend_id``.

        Raises:
            KeyError: No backend is registered under that id.
            RuntimeError: The backend is not available.
        """

        if self._detector is not None:
            self._detector.close()
            self._detector = None
            self._detector_backend_id = None

        self._detector = self._pose_registry.create(backend_id)
        self._detector_backend_id = backend_id

    def detect_current_frame(self) -> PoseFrame | None:
        """Detect a pose in the current frame with the selected backend.

        Returns the canonical :class:`PoseFrame`, or ``None`` when no pose
        is found.

        Raises:
            RuntimeError: No video imported, or no detector selected.
        """

        if self._frame_reader is None:
            raise RuntimeError("No video has been imported")

        if self._detector is None:
            raise RuntimeError("No detector selected")

        frame = self._frame_reader.read_frame(self._current_frame_index)
        raw = self._detector.detect(
            frame, self._current_frame_index, self.current_timestamp
        )

        if raw is None:
            return None

        return to_canonical(raw)

    @property
    def pose_sequence(self) -> PoseSequence | None:
        """Return the full-video analysis result, if one has been produced."""

        return self._pose_sequence

    def active_pose_at(self, frame_index: int) -> PoseFrame | None:
        """Return the detected pose for ``frame_index`` on the active track."""

        if self._pose_sequence is None:
            return None

        return self._pose_sequence.active_pose_at(frame_index)

    def effective_pose_at(self, frame_index: int) -> PoseFrame | None:
        """Return the pose actually shown: processed if available, else
        detection merged with manual corrections."""

        if self._processed_sequence is not None:
            return self._processed_sequence.active_pose_at(frame_index)

        if self._pose_sequence is None:
            return None

        track = self._pose_sequence.active_track
        if track is None:
            return None

        layer = self._correction_layers.get(track.track_id)
        corrections = layer.corrected_joints(frame_index) if layer is not None else {}

        return effective_pose(
            frame_index,
            self.current_timestamp,
            track.pose_at(frame_index),
            corrections,
        )

    @property
    def can_undo(self) -> bool:
        """Return whether there is a correction to undo."""

        return self._commands.can_undo

    @property
    def can_redo(self) -> bool:
        """Return whether there is an undone correction to redo."""

        return self._commands.can_redo

    @property
    def correction_count(self) -> int:
        """Return the number of corrections on the active track."""

        layer = self._active_correction_layer(create=False)
        return layer.correction_count if layer is not None else 0

    def correct_keypoint(self, joint: JointName, position: Vector3) -> None:
        """Move ``joint`` to ``position`` on the current frame (undoable)."""

        layer = self._active_correction_layer(create=True)
        if layer is None:
            return

        self._commands.do(
            SetKeypointCorrection(layer, self._current_frame_index, joint, position)
        )
        self._invalidate_downstream()

    def clear_keypoint(self, joint: JointName) -> None:
        """Remove the correction for ``joint`` on the current frame (undoable)."""

        layer = self._active_correction_layer(create=False)
        if layer is None or layer.get(self._current_frame_index, joint) is None:
            return

        self._commands.do(
            ClearKeypointCorrection(layer, self._current_frame_index, joint)
        )
        self._invalidate_downstream()

    def propagate_keypoint(self, joint: JointName) -> bool:
        """Interpolate ``joint`` across its corrected keyframes (undoable).

        Returns ``True`` when a propagation was applied.
        """

        layer = self._active_correction_layer(create=False)
        if layer is None:
            return False

        command = PropagateKeypointCorrection(layer, joint)
        if not command.is_effective:
            return False

        self._commands.do(command)
        self._invalidate_downstream()
        return True

    def undo(self) -> None:
        """Undo the most recent correction."""

        self._commands.undo()
        self._invalidate_downstream()

    def redo(self) -> None:
        """Redo the most recently undone correction."""

        self._commands.redo()
        self._invalidate_downstream()

    @property
    def skeleton_clip(self) -> SkeletonClip | None:
        """Return the last solved skeleton clip, if current."""

        return self._skeleton_clip

    @property
    def processed(self) -> bool:
        """Return whether a processed sequence is in effect."""

        return self._processed_sequence is not None

    def process_animation(self, options: ProcessingOptions) -> ProcessingReport:
        """Run the enabled cleanup passes and use the result downstream.

        Processes the 3D reconstruction when one is active, otherwise the
        analysed 2D sequence (with corrections baked in).

        Raises:
            RuntimeError: No analysis to process.
        """

        base = self._reconstructed_sequence or self._pose_sequence
        if base is None:
            raise RuntimeError("no analysis available - run detection first")

        layer = (
            None
            if self._reconstructed_sequence is not None
            else self._active_correction_layer(create=False)
        )
        self._processed_sequence, report = process_sequence(
            base, options, correction_layer=layer
        )
        self._skeleton_clip = None
        self._rig_clip = None
        self._retargeted_rig_id = None
        return report

    @property
    def reconstructed(self) -> bool:
        """Return whether a 3D reconstruction is in effect."""

        return self._reconstructed_sequence is not None

    @property
    def reconstruction_backend_id(self) -> str | None:
        """Return the id of the active reconstruction backend, if any."""

        return self._reconstruction_backend_id

    def available_reconstructors(self) -> list[BackendEntry]:
        """Return the usable 3D reconstruction backends."""

        return self._reconstruction_registry.available()

    def reconstruct_3d(self, backend_id: str) -> PoseSequence:
        """Lift the analysed sequence to 3D with ``backend_id``.

        Raises:
            RuntimeError: No analysis, or the backend has no usable data.
        """

        if self._pose_sequence is None:
            raise RuntimeError("no analysis available - run detection first")

        backend = self._reconstruction_registry.create(backend_id)

        if not backend.can_reconstruct(self._pose_sequence):
            raise RuntimeError(
                f"'{backend_id}' has no usable depth data for this analysis"
            )

        self._reconstructed_sequence = backend.reconstruct(self._pose_sequence)
        self._reconstruction_backend_id = backend_id
        self._processed_sequence = None
        self._skeleton_clip = None
        self._rig_clip = None
        self._retargeted_rig_id = None
        return self._reconstructed_sequence

    def reconstruction_issues(self) -> list[str]:
        """Return quality notes about the current 3D reconstruction."""

        if self._reconstructed_sequence is None:
            return []

        return reconstruction_quality_report(self._reconstructed_sequence)

    def build_skeleton(self) -> SkeletonClip:
        """Solve the canonical skeleton for the working sequence.

        Prefers the processed sequence, then the 3D reconstruction, then
        the analysed sequence (plus corrections in the last case).

        Raises:
            RuntimeError: No analysis to solve from.
        """

        if self._working_sequence is None:
            raise RuntimeError("no analysis available - run detection first")

        derived = (
            self._processed_sequence is not None
            or self._reconstructed_sequence is not None
        )
        layer = None if derived else self._active_correction_layer(create=False)

        self._skeleton_clip = solve_skeleton(
            self._working_sequence, correction_layer=layer
        )
        self._rig_clip = None
        self._retargeted_rig_id = None
        return self._skeleton_clip

    @property
    def _working_sequence(self) -> PoseSequence | None:
        return (
            self._processed_sequence
            or self._reconstructed_sequence
            or self._pose_sequence
        )

    @property
    def rig_clip(self) -> RigClip | None:
        """Return the retargeted clip, if one is current."""

        return self._rig_clip

    @property
    def retargeted_rig_id(self) -> str | None:
        """Return the id of the rig the current clip is retargeted to."""

        return self._retargeted_rig_id

    def available_rigs(self) -> list[RigProfileInfo]:
        """Return the rig profiles that can be retargeted to."""

        return self._rig_registry.available()

    def read_armature(
        self, path: Path
    ) -> tuple[ArmatureDump, dict, list[BoneGroup], dict]:
        """Read an armature exported from a DCC and work out its structure.

        Returns:
            The dump, a canonical-bone to rig-bone mapping covering the
            roles the heuristic could place confidently, the bone chains
            no canonical role uses (fingers, toes) so the UI can fold them
            into one row each, and the runs of bones that play a single
            canonical role (a multi-segment spine).

        Raises:
            ArmatureImportError: The file is missing or malformed.
        """

        dump = load_armature_dump(path)
        mapping = auto_map(dump.bone_names, dump.parents)
        groups = detect_bone_groups(dump.bone_names, dump.parents, mapping)
        chains = bone_chains_for(mapping, groups, dump.parents)
        # A promoted chain is part of its role now, not leftover.
        promoted = {bone for chain in chains.values() for bone in chain}
        groups = [
            group
            for group in groups
            if not set(group.members).issubset(promoted)
        ]
        return dump, mapping, groups, chains

    def add_rig_profile(self, document: dict) -> RigProfileInfo:
        """Install a custom rig profile and make it selectable.

        Raises:
            RigProfileError: The document is malformed or its id is taken
                by a built-in profile.
        """

        return self._rig_registry.install_profile(document)

    def remove_rig_profile(self, rig_id: str) -> None:
        """Delete a custom rig profile.

        Clears the current retarget when it used that profile.

        Raises:
            RigProfileError: The id is unknown or built in.
        """

        self._rig_registry.remove_profile(rig_id)

        if self._retargeted_rig_id == rig_id:
            self._rig_clip = None
            self._retargeted_rig_id = None

    def is_custom_rig(self, rig_id: str) -> bool:
        """Return whether ``rig_id`` is a user profile rather than built in."""

        return self._rig_registry.has(rig_id) and not self._rig_registry.is_bundled(
            rig_id
        )

    def unique_rig_id(self, preferred: str) -> str:
        """Return a rig id derived from ``preferred`` that is not yet taken."""

        return self._rig_registry.unique_rig_id(preferred)

    def _build_rig_registry(self, project_dir: Path | None = None) -> RigRegistry:
        """Build the registry: bundled, then user profiles, then the project's."""

        extras: list[Path] = [self._user_rig_dir]
        if project_dir is not None:
            extras.append(project_dir / RIGS_DIR)

        return build_rig_registry(*extras, install_dir=self._user_rig_dir)

    def retarget(self, rig_id: str) -> RigClip:
        """Retarget the solved skeleton onto ``rig_id``.

        Raises:
            RuntimeError: No skeleton has been built.
            RigProfileError: The rig id is unknown or its profile is bad.
        """

        if self._skeleton_clip is None:
            raise RuntimeError("build the skeleton before retargeting")

        rig, retarget_map = self._rig_registry.load(rig_id)
        self._rig_clip = run_retarget(self._skeleton_clip, rig, retarget_map)
        self._retargeted_rig_id = rig_id
        return self._rig_clip

    def retarget_issues(self) -> list[str]:
        """Return notes about the current retarget's coverage."""

        if self._skeleton_clip is None or self._retargeted_rig_id is None:
            return []

        rig, retarget_map = self._rig_registry.load(self._retargeted_rig_id)
        return retarget_issues(self._skeleton_clip, retarget_map, rig)

    def export_animation(self, path: Path, rig_id: str | None = None) -> None:
        """Write the solved skeleton clip to ``path`` as an ``mcapclip`` file.

        When ``rig_id`` is given, the file also carries that rig's
        canonical-to-rig bone map (the Blender add-on uses it directly).

        Raises:
            RuntimeError: No skeleton has been built.
        """

        if self._skeleton_clip is None:
            raise RuntimeError("no skeleton to export - build the skeleton first")

        track_id = ""
        if self._pose_sequence is not None and self._pose_sequence.active_track_id:
            track_id = self._pose_sequence.active_track_id

        bone_map = None
        if rig_id is not None:
            _, retarget_map = self._rig_registry.load(rig_id)
            bone_map = {
                canonical.value: rig_bone
                for canonical, rig_bone in retarget_map.bone_map.items()
            }

        export_animation(
            self._skeleton_clip, path, name=track_id, bone_map=bone_map
        )

    def export_bvh(self, path: Path) -> None:
        """Write the solved skeleton clip to ``path`` as a ``.bvh`` file.

        Raises:
            RuntimeError: No skeleton has been built.
        """

        if self._skeleton_clip is None:
            raise RuntimeError("no skeleton to export - build the skeleton first")

        export_bvh(self._skeleton_clip, path)

    def _invalidate_downstream(self) -> None:
        """Drop the reconstruction, processed sequence and derived clips."""

        self._reconstructed_sequence = None
        self._reconstruction_backend_id = None
        self._processed_sequence = None
        self._skeleton_clip = None
        self._rig_clip = None
        self._retargeted_rig_id = None

    def skeleton_issues(self) -> list[str]:
        """Return validation issues for the current skeleton clip."""

        if self._skeleton_clip is None:
            return []

        issues = validate_skeleton_clip(self._skeleton_clip)

        if self._pose_sequence is not None:
            layer = self._active_correction_layer(create=False)
            issues += bone_length_report(
                self._pose_sequence, correction_layer=layer
            )

        return issues

    def _active_correction_layer(self, *, create: bool) -> CorrectionLayer | None:
        if self._pose_sequence is None or self._pose_sequence.active_track is None:
            return None

        track_id = self._pose_sequence.active_track.track_id
        layer = self._correction_layers.get(track_id)

        if layer is None and create:
            layer = CorrectionLayer(track_id=track_id)
            self._correction_layers[track_id] = layer

        return layer

    def analyze_video(
        self,
        *,
        on_progress: Callable[[int, int], None] | None = None,
        on_done: Callable[[TaskResult], None] | None = None,
    ) -> CancelToken:
        """Run the selected detector over every frame in the background.

        ``on_progress`` and ``on_done`` are invoked from a worker thread.
        The resulting :class:`PoseSequence` (partial if cancelled) is stored
        on the controller before ``on_done`` runs.

        Raises:
            RuntimeError: No video imported, or no detector selected.
        """

        if self._frame_reader is None:
            raise RuntimeError("No video has been imported")

        if self._detector is None or self._detector_backend_id is None:
            raise RuntimeError("No detector selected")

        metadata = self._project.video_metadata
        if metadata is None:
            raise RuntimeError("No video metadata available")

        backend_id = self._detector_backend_id
        registry = self._pose_registry
        workers = self._analysis_workers

        def job(token: CancelToken, reporter: Callable[[int, int], None]) -> PoseSequence:
            return analyze_video_parallel(
                metadata.path,
                lambda: registry.create(backend_id),
                metadata,
                workers=workers,
                on_progress=reporter,
                should_cancel=lambda: token.cancelled,
            )

        def store_and_forward(result: TaskResult) -> None:
            if (
                result.status in (TaskStatus.SUCCEEDED, TaskStatus.CANCELLED)
                and result.value is not None
            ):
                self._pose_sequence = result.value
                self._correction_layers = {}
                self._commands.clear()
                self._invalidate_downstream()

            if on_done is not None:
                on_done(result)

        token = self._task_manager.submit(
            job, on_progress=on_progress, on_done=store_and_forward
        )
        self._active_analysis_token = token
        return token

    def save_project(self, project_dir: Path | None = None) -> Path:
        """Save the project (and analysis) to ``project_dir``.

        With no argument, re-saves to the project's existing path.

        Raises:
            ProjectIOError: No path available, or no video imported.
        """

        target = project_dir or self._project.project_path

        if target is None:
            raise ProjectIOError("no project path given and none is set")

        save_project(
            target,
            self._project,
            self._pose_sequence,
            detector_backend=self._detector_backend_id,
            corrections=self._correction_layers,
            skeleton_clip=self._skeleton_clip,
            rig_clip=self._rig_clip,
            rig_profile=self._custom_rig_profile(),
        )
        self._project.project_path = target
        # The project now carries its own rigs/ copy; scan it from here on.
        self._rig_registry = self._build_rig_registry(target)
        return target

    def _custom_rig_profile(self) -> dict | None:
        """Return the active retarget's profile document, if it is a custom one."""

        rig_id = self._retargeted_rig_id

        if rig_id is None or not self.is_custom_rig(rig_id):
            return None

        try:
            return self._rig_registry.document(rig_id)
        except RigProfileError:
            return None

    def open_project(self, project_dir: Path) -> None:
        """Load a project directory: its video and any stored analysis.

        Raises:
            ProjectIOError: The directory is malformed or a newer version.
            RuntimeError / OSError: The referenced video cannot be opened.
        """

        loaded = load_project(project_dir)

        video_metadata = loaded.project.video_metadata
        if video_metadata is None:
            raise ProjectIOError("project has no video reference")

        # Pick up any custom rig profile the project carries.
        self._rig_registry = self._build_rig_registry(project_dir)

        self._cancel_active_analysis()

        try:
            metadata = self._video_loader.load_metadata(video_metadata.path)
        except (OSError, RuntimeError) as error:
            raise ProjectIOError(
                f"video not available at {video_metadata.path}: {error}"
            ) from error

        self._open_frame_reader(metadata.path)
        self._project = loaded.project
        self._project.video_metadata = metadata
        self._project.project_path = project_dir
        self._current_frame_index = 0
        self._playback = PlaybackController(fps=metadata.fps)
        self._pose_sequence = loaded.pose_sequence
        self._correction_layers = dict(loaded.corrections)
        self._commands.clear()
        self._skeleton_clip = loaded.skeleton_clip
        self._rig_clip = loaded.rig_clip
        self._retargeted_rig_id = loaded.rig_clip.rig_id if loaded.rig_clip else None

    def advance_playback(self) -> np.ndarray | None:
        """Advance one frame during playback.

        Returns the next frame, or ``None`` when playback is not running or
        the end of the video has been reached. Playback is paused when the
        end is reached or a frame cannot be decoded.
        """

        if not self._playback.is_playing:
            return None

        if self._frame_stream is not None:
            item = self._frame_stream.next_frame()
            if item is None:
                self._playback.pause()
                self._stop_frame_stream()
                return None
            index, frame = item
            self._current_frame_index = index
            return frame

        next_index = self._current_frame_index + 1

        if self.frame_count > 0 and next_index >= self.frame_count:
            self._playback.pause()
            return None

        try:
            return self._read_without_stream(next_index)
        except (IndexError, RuntimeError):
            self._playback.pause()
            return None

    def _read_without_stream(self, index: int) -> np.ndarray:
        target = self._clamp_frame_index(index)
        frame = self._frame_reader.read_frame(target)
        self._current_frame_index = target
        return frame

    def close(self) -> None:
        """Release resources: cancel analysis, close the video and detector."""

        self._cancel_active_analysis()
        self._stop_frame_stream()
        self._task_manager.shutdown()

        if self._frame_reader is not None:
            self._frame_reader.close()
            self._frame_reader = None

        if self._detector is not None:
            self._detector.close()
            self._detector = None
            self._detector_backend_id = None

    def _cancel_active_analysis(self) -> None:
        if self._active_analysis_token is not None:
            self._active_analysis_token.cancel()
            self._active_analysis_token = None

    def _open_frame_reader(self, video_path: Path) -> None:
        if self._frame_reader is not None:
            self._frame_reader.close()

        self._frame_reader = FrameReader(video_path)

    def _clamp_frame_index(self, index: int) -> int:
        clamped = max(0, index)

        frame_count = self.frame_count

        if frame_count > 0:
            clamped = min(clamped, frame_count - 1)

        return clamped
