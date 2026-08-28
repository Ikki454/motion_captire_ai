"""Main application window for the AI Motion Capture app."""

from functools import partial
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.project_controller import ProjectController
from app.core.project_io import ProjectIOError
from app.core.tasks import CancelToken, TaskResult, TaskStatus
from app.models.pose import JointName, Vector3
from app.retarget.armature_import import ArmatureImportError
from app.retarget.rig_registry import RigProfileError
from app.ui.formatting import format_video_line, format_video_summary
from app.ui.sizing import fit_window_to_scroll_area
from app.ui.theme import apply_dark_theme
from app.ui.widgets.correction_panel import CorrectionPanel
from app.ui.widgets.custom_rig_dialog import CustomRigDialog
from app.ui.widgets.detector_panel import DetectorPanel
from app.ui.widgets.pipeline_section import PipelineSection
from app.ui.widgets.processing_panel import ProcessingPanel
from app.ui.widgets.reconstruction_panel import ReconstructionPanel
from app.ui.widgets.rig_panel import RigPanel
from app.ui.widgets.skeleton_panel import SkeletonPanel
from app.ui.widgets.timeline import Timeline
from app.ui.widgets.video_view import VideoView
from app.video.video_loader import VideoMetadata

_VIDEO_FILE_FILTER = "Video files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;All files (*)"


class MainWindow(QMainWindow):
    """Main application window."""

    # Emitted from the analysis worker thread; delivered on the UI thread.
    _analysis_progress = Signal(int, int)
    _analysis_finished = Signal(object)

    def __init__(self, controller: ProjectController | None = None) -> None:
        super().__init__()

        self._controller = controller or ProjectController()
        self._analysis_token: CancelToken | None = None
        self._pipeline_scroll: QScrollArea | None = None
        self._fitted = False

        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_tick)

        self._analysis_progress.connect(self._on_analysis_progress)
        self._analysis_finished.connect(self._on_analysis_finished)

        self.setWindowTitle("AI Motion Capture")
        self.resize(1280, 820)
        apply_dark_theme(self)

        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()
        self._update_pipeline_state()

    @property
    def controller(self) -> ProjectController:
        """Return the project controller backing this window."""

        return self._controller

    def _setup_ui(self) -> None:
        """Create the main user interface.

        Layout: a horizontal splitter with the video and its timeline on
        the left, and a scrollable column of numbered pipeline sections on
        the right. Transient messages go to the status bar.
        """

        self._create_widgets()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_video_pane())
        splitter.addWidget(self._build_pipeline_pane())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([680, 600])

        self.setCentralWidget(splitter)

        self.status_label = QLabel("No video loaded.")
        self.statusBar().addWidget(self.status_label)

    def _create_widgets(self) -> None:
        """Instantiate the widgets and connect their signals."""

        self.import_button = QPushButton("Import Video")
        self.import_button.clicked.connect(self._on_import_clicked)

        self.video_info_label = QLabel("")
        self.video_info_label.setObjectName("videoInfo")
        self.video_info_label.setWordWrap(True)

        self.video_view = VideoView()

        self.timeline = Timeline()
        self.timeline.frame_selected.connect(self._go_to_frame)
        self.timeline.play_toggled.connect(self._set_playing)
        self.timeline.stop_requested.connect(self._stop_playback)

        self.detector_panel = DetectorPanel()
        self.detector_panel.set_backends(
            self._controller.available_detectors(),
            self._controller.unavailable_detectors(),
        )
        self.detector_panel.detect_requested.connect(self._detect_current_frame)
        self.detector_panel.analyze_requested.connect(self._start_analysis)
        self.detector_panel.cancel_requested.connect(self._cancel_analysis)

        self.correction_panel = CorrectionPanel()
        self.correction_panel.edit_toggled.connect(self._on_edit_toggled)
        self.correction_panel.undo_requested.connect(self._undo_correction)
        self.correction_panel.redo_requested.connect(self._redo_correction)
        self.correction_panel.propagate_requested.connect(self._propagate_correction)
        self.correction_panel.clear_requested.connect(self._clear_correction)

        self.video_view.keypoint_selected.connect(self.correction_panel.set_selected_joint)
        self.video_view.keypoint_moved.connect(self._on_keypoint_moved)

        self.skeleton_panel = SkeletonPanel()
        self.skeleton_panel.build_requested.connect(self._build_skeleton)

        self.reconstruction_panel = ReconstructionPanel()
        self.reconstruction_panel.set_backends(
            self._controller.available_reconstructors()
        )
        self.reconstruction_panel.reconstruct_requested.connect(self._reconstruct_3d)

        self.processing_panel = ProcessingPanel()
        self.processing_panel.process_requested.connect(self._process_animation)

        self.rig_panel = RigPanel()
        self.rig_panel.set_rigs(self._controller.available_rigs())
        self.rig_panel.retarget_requested.connect(self._retarget)
        self.rig_panel.import_rig_requested.connect(self._on_import_rig)
        self.rig_panel.new_rig_requested.connect(self._on_new_rig)
        self.rig_panel.remove_rig_requested.connect(self._on_remove_rig)

    def _build_video_pane(self) -> QWidget:
        """Left pane: the frame view and the timeline below it."""

        pane = QWidget()
        pane.setMinimumWidth(320)

        layout = QVBoxLayout(pane)
        layout.setContentsMargins(8, 8, 4, 8)
        layout.addWidget(self.video_view, stretch=1)
        layout.addWidget(self.timeline)

        return pane

    def _build_pipeline_pane(self) -> QWidget:
        """Right pane: a scrollable column of numbered pipeline sections."""

        header = QHBoxLayout()
        header.addWidget(self.import_button)
        header.addWidget(self.video_info_label, stretch=1)

        self.section_detect = PipelineSection(1, "Detection", self.detector_panel)
        self.section_correct = PipelineSection(2, "Correction", self.correction_panel)
        self.section_3d = PipelineSection(
            3, "3D reconstruction", self.reconstruction_panel, optional=True
        )
        self.section_process = PipelineSection(
            4, "Processing", self.processing_panel, optional=True
        )
        self.section_skeleton = PipelineSection(5, "Skeleton", self.skeleton_panel)
        self.section_rig = PipelineSection(6, "Rig and export", self.rig_panel)

        self._sections = (
            self.section_detect,
            self.section_correct,
            self.section_3d,
            self.section_process,
            self.section_skeleton,
            self.section_rig,
        )

        inner = QWidget()
        column = QVBoxLayout(inner)
        column.setContentsMargins(4, 8, 8, 8)
        column.setSpacing(10)
        column.addLayout(header)
        for section in self._sections:
            column.addWidget(section)
        column.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        scroll.setMinimumWidth(420)
        self._pipeline_scroll = scroll

        return scroll

    def showEvent(self, event: QShowEvent) -> None:
        """Size the window so the pipeline column fits, the first time it shows."""

        super().showEvent(event)

        if not self._fitted and self._pipeline_scroll is not None:
            self._fitted = True
            fit_window_to_scroll_area(self, self._pipeline_scroll)

    def _setup_menu(self) -> None:
        """Create the File menu (open / save project)."""

        file_menu = self.menuBar().addMenu("File")

        self.open_project_action = file_menu.addAction("Open Project...")
        self.open_project_action.triggered.connect(self._on_open_project)

        self.save_project_action = file_menu.addAction("Save Project")
        self.save_project_action.triggered.connect(self._on_save_project)

        self.save_project_as_action = file_menu.addAction("Save Project As...")
        self.save_project_as_action.triggered.connect(self._on_save_project_as)

        file_menu.addSeparator()

        self.export_animation_action = file_menu.addAction("Export Animation...")
        self.export_animation_action.triggered.connect(self._on_export_animation)

        self.export_bvh_action = file_menu.addAction("Export BVH...")
        self.export_bvh_action.triggered.connect(self._on_export_bvh)

    def _setup_shortcuts(self) -> None:
        """Bind arrow keys to frame stepping and space to play / pause."""

        self.previous_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.previous_shortcut.activated.connect(partial(self._step_frames, -1))

        self.next_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.next_shortcut.activated.connect(partial(self._step_frames, 1))

        self.play_pause_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.play_pause_shortcut.activated.connect(self._toggle_play)

        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self._undo_correction)

        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self.redo_shortcut.activated.connect(self._redo_correction)

    def _toggle_play(self) -> None:
        """Toggle playback (space bar)."""

        if self._controller.has_video:
            self._set_playing(not self._controller.is_playing)

    def _show_video_metadata(self, metadata: VideoMetadata) -> None:
        """Put the compact summary on the header label, the full one in a tooltip."""

        self.video_info_label.setText(format_video_line(metadata))
        self.video_info_label.setToolTip(format_video_summary(metadata))

    def _update_pipeline_state(self) -> None:
        """Enable each step once its inputs exist and highlight the next one.

        This is UI feedback only -- every handler still guards itself.
        """

        controller = self._controller
        has_video = controller.has_video
        analysed = controller.pose_sequence is not None
        has_skeleton = controller.skeleton_clip is not None
        has_rig = controller.rig_clip is not None

        self.detector_panel.set_video_loaded(has_video)
        self.reconstruction_panel.set_ready(analysed)
        self.processing_panel.set_ready(analysed)
        self.skeleton_panel.set_ready(analysed)
        self.rig_panel.set_ready(has_skeleton)

        self.save_project_action.setEnabled(has_video)
        self.save_project_as_action.setEnabled(has_video)
        self.export_animation_action.setEnabled(has_skeleton)
        self.export_bvh_action.setEnabled(has_skeleton)

        self.section_detect.set_state(
            "done" if analysed else "active" if has_video else "pending",
            "" if analysed else "next" if has_video else "",
        )
        self.section_skeleton.set_state(
            "done" if has_skeleton else "active" if analysed else "pending",
            "next" if analysed and not has_skeleton else "",
        )
        self.section_rig.set_state(
            "done" if has_rig else "active" if has_skeleton else "pending",
            "next" if has_skeleton and not has_rig else "",
        )
        self.section_correct.set_state(
            "done" if controller.correction_count else "pending"
        )
        self.section_3d.set_state("done" if controller.reconstructed else "pending")
        self.section_process.set_state("done" if controller.processed else "pending")

    def _on_import_clicked(self) -> None:
        """Prompt for a video file and load the selected one."""

        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Video",
            "",
            _VIDEO_FILE_FILTER,
        )

        if not selected_path:
            return

        self.load_video(selected_path)

    def load_video(self, video_path: str) -> None:
        """Load ``video_path`` into the project and update the display.

        Errors are reported in the status label; they never propagate out
        of this method.
        """

        self._playback_timer.stop()

        try:
            metadata = self._controller.import_video(video_path)
        except (OSError, RuntimeError) as error:
            self.status_label.setText(f"Could not import video: {error}")
            self.video_info_label.clear()
            self.video_info_label.setToolTip("")
            self.video_view.clear_frame()
            self.timeline.reset()
            self._update_pipeline_state()
            return

        self.status_label.setText(f"Loaded: {metadata.path.name}")
        self._show_video_metadata(metadata)
        self.timeline.set_range(self._controller.frame_count)
        self._go_to_frame(0)
        self._update_pipeline_state()

    def _on_open_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Open Project", "")

        if directory:
            self.open_project(Path(directory))

    def open_project(self, project_dir: Path) -> None:
        """Load a project directory and update the display."""

        self._playback_timer.stop()

        try:
            self._controller.open_project(project_dir)
        except (OSError, RuntimeError, ProjectIOError) as error:
            self.status_label.setText(f"Could not open project: {error}")
            return

        metadata = self._controller.project.video_metadata
        self.status_label.setText(f"Opened project: {project_dir.name}")
        self._show_video_metadata(metadata)
        self.timeline.set_range(self._controller.frame_count)
        self._go_to_frame(0)
        self._update_pipeline_state()

        sequence = self._controller.pose_sequence
        if sequence is not None and sequence.active_track is not None:
            self.detector_panel.set_status(
                f"Loaded analysis - pose in "
                f"{sequence.active_track.detection_count} / "
                f"{sequence.frame_count} frames."
            )

    def _on_save_project(self) -> None:
        if not self._controller.has_video:
            self.status_label.setText("Nothing to save - import a video first.")
            return

        if self._controller.project.project_path is None:
            self._on_save_project_as()
            return

        self._save_project(self._controller.project.project_path)

    def _on_save_project_as(self) -> None:
        if not self._controller.has_video:
            self.status_label.setText("Nothing to save - import a video first.")
            return

        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            "project.mcap",
            "Motion capture project (*.mcap)",
        )

        if not path_str:
            return

        path = Path(path_str)
        if path.suffix != ".mcap":
            path = path.with_suffix(".mcap")

        self._save_project(path)

    def _save_project(self, project_dir: Path) -> None:
        """Save the project to ``project_dir`` and report the outcome."""

        try:
            self._controller.save_project(project_dir)
        except (OSError, ProjectIOError) as error:
            self.status_label.setText(f"Could not save project: {error}")
            return

        self.status_label.setText(f"Saved project: {project_dir.name}")

    def _on_export_animation(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export Animation",
            "animation.mcapclip.json",
            "Motion capture clip (*.mcapclip.json)",
        )

        if not path_str:
            return

        self.export_animation(Path(path_str))

    def export_animation(self, path: Path) -> None:
        """Export the solved skeleton clip and report the outcome.

        When a retarget is active, the file carries that rig's bone map.
        """

        rig_id = self._controller.retargeted_rig_id

        try:
            self._controller.export_animation(path, rig_id=rig_id)
        except (OSError, RuntimeError) as error:
            self.status_label.setText(f"Could not export animation: {error}")
            return

        suffix = f" (for {rig_id})" if rig_id else ""
        self.status_label.setText(f"Exported animation: {path.name}{suffix}")

    def _on_export_bvh(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export BVH", "animation.bvh", "BioVision Hierarchy (*.bvh)"
        )

        if not path_str:
            return

        self.export_bvh(Path(path_str))

    def export_bvh(self, path: Path) -> None:
        """Export the solved skeleton clip as BVH and report the outcome."""

        try:
            self._controller.export_bvh(path)
        except (OSError, RuntimeError) as error:
            self.status_label.setText(f"Could not export BVH: {error}")
            return

        self.status_label.setText(f"Exported BVH: {path.name}")

    def _go_to_frame(self, index: int) -> None:
        """Navigate to ``index`` and refresh the frame view and timeline.

        Manual navigation pauses playback.
        """

        if not self._controller.has_video:
            return

        if self._controller.is_playing:
            self._set_playing(False)

        try:
            frame = self._controller.go_to_frame(index)
        except (IndexError, RuntimeError):
            self.video_view.clear_frame()
            return

        self._display_frame(frame)

    def _step_frames(self, delta: int) -> None:
        """Move the current position by ``delta`` frames."""

        self._go_to_frame(self._controller.current_frame_index + delta)

    def _ensure_detector(self) -> bool:
        """Make sure the controller uses the panel's selected backend."""

        backend_id = self.detector_panel.current_backend_id()

        if backend_id is None:
            return False

        if self._controller.detector_backend_id == backend_id:
            return True

        try:
            self._controller.set_detector(backend_id)
        except (KeyError, RuntimeError, OSError) as error:
            self.detector_panel.set_status(f"Detector unavailable: {error}")
            return False

        return True

    def _detect_current_frame(self) -> None:
        """Run the selected detector on the current frame and show the pose."""

        if not self._controller.has_video or not self._ensure_detector():
            return

        if self._controller.is_playing:
            self._set_playing(False)

        try:
            pose = self._controller.detect_current_frame()
        except (RuntimeError, OSError) as error:
            self.video_view.set_pose(None)
            self.detector_panel.set_status(f"Detection failed: {error}")
            return

        self.video_view.set_pose(pose)

        if pose is None:
            self.detector_panel.set_status("No pose detected in this frame.")
        else:
            visible = sum(
                1 for joint in pose.joints.values() if joint.confidence > 0.0
            )
            self.detector_panel.set_status(
                f"Detected {visible} / {len(pose.joints)} keypoints."
            )

    def _start_analysis(self) -> None:
        """Detect a pose in every frame, in the background."""

        if not self._controller.has_video or not self._ensure_detector():
            return

        if self._controller.is_playing:
            self._set_playing(False)

        try:
            self._analysis_token = self._controller.analyze_video(
                on_progress=self._analysis_progress.emit,
                on_done=self._analysis_finished.emit,
            )
        except RuntimeError as error:
            self.detector_panel.set_status(f"Cannot analyze: {error}")
            return

        self.detector_panel.set_analysis_running(True)
        self.detector_panel.set_status("Analyzing video...")

    def _cancel_analysis(self) -> None:
        """Ask the running analysis to stop."""

        if self._analysis_token is not None:
            self._analysis_token.cancel()
            self.detector_panel.set_status("Cancelling analysis...")

    def _on_analysis_progress(self, done: int, total: int) -> None:
        self.detector_panel.set_analysis_progress(done, total)

    def _on_analysis_finished(self, result: TaskResult) -> None:
        self._analysis_token = None
        self.detector_panel.set_analysis_running(False)

        if result.status is TaskStatus.FAILED:
            self.detector_panel.set_status(f"Analysis failed: {result.error}")
            return

        sequence = self._controller.pose_sequence
        track = sequence.active_track if sequence is not None else None
        detected = track.detection_count if track is not None else 0
        total = sequence.frame_count if sequence is not None else 0

        if result.status is TaskStatus.CANCELLED:
            self.detector_panel.set_status(
                f"Analysis cancelled - {detected} / {total} frames done."
            )
        else:
            self.detector_panel.set_status(
                f"Analyzed {total} frames - pose found in {detected}."
            )

        self._update_pipeline_state()
        self._refresh_current_frame()

    def _set_playing(self, playing: bool) -> None:
        """Start or pause playback and keep the timer and button in sync."""

        if playing and self._controller.has_video:
            self._controller.play()
            self._playback_timer.start(self._controller.frame_interval_ms)
        else:
            self._controller.pause()
            self._playback_timer.stop()

        self.timeline.set_playing(self._controller.is_playing)

    def _stop_playback(self) -> None:
        """Stop playback and rewind to the first frame."""

        self._controller.stop()
        self._playback_timer.stop()
        self.timeline.set_playing(False)
        self._refresh_current_frame()

    def _on_playback_tick(self) -> None:
        """Advance one frame; stop the timer when playback ends."""

        frame = self._controller.advance_playback()

        if frame is None:
            self._playback_timer.stop()
            self.timeline.set_playing(False)
            return

        self._display_frame(frame)

    def _refresh_current_frame(self) -> None:
        """Re-read and display the current frame."""

        if not self._controller.has_video:
            return

        try:
            frame = self._controller.go_to_frame(self._controller.current_frame_index)
        except (IndexError, RuntimeError):
            self.video_view.clear_frame()
            return

        self._display_frame(frame)

    def _display_frame(self, frame: np.ndarray) -> None:
        """Show ``frame``, the effective pose overlay (if any), and the readout."""

        self.video_view.set_frame(frame)
        self.timeline.set_position(
            self._controller.current_frame_index,
            self._controller.current_timestamp,
        )

        if self._controller.pose_sequence is not None:
            self.video_view.set_pose(
                self._controller.effective_pose_at(
                    self._controller.current_frame_index
                )
            )

    def _on_edit_toggled(self, editing: bool) -> None:
        self.video_view.set_editable(editing)

    def _build_skeleton(self) -> None:
        try:
            clip = self._controller.build_skeleton()
        except RuntimeError as error:
            self.skeleton_panel.set_status(str(error))
            return

        issues = self._controller.skeleton_issues()
        summary = (
            f"Solved {len(clip.poses)} frames, {len(clip.bone_lengths)} bones"
        )

        if issues:
            self.skeleton_panel.set_status(
                f"{summary}. {len(issues)} issue(s): " + "; ".join(issues[:3])
            )
        else:
            self.skeleton_panel.set_status(f"{summary}. Validation OK.")

        self._update_pipeline_state()

    def _reconstruct_3d(self) -> None:
        backend_id = self.reconstruction_panel.current_backend_id()
        if backend_id is None:
            return

        try:
            sequence = self._controller.reconstruct_3d(backend_id)
        except (RuntimeError, OSError) as error:
            self.reconstruction_panel.set_status(str(error))
            return

        issues = self._controller.reconstruction_issues()
        frames = sequence.active_track.detection_count
        summary = f"Reconstructed {frames} frames ({backend_id})"
        self.reconstruction_panel.set_status(
            f"{summary}. {issues[0]}" if issues else f"{summary}. Looks plausible."
        )

        self._update_pipeline_state()

    def _process_animation(self) -> None:
        options = self.processing_panel.options()

        try:
            report = self._controller.process_animation(options)
        except RuntimeError as error:
            self.processing_panel.set_status(str(error))
            return

        if report.steps:
            detail = ", ".join(report.steps)
            if report.gaps_filled:
                detail += f" ({report.gaps_filled} gap frames)"
            self.processing_panel.set_status(f"Processed: {detail}.")
        else:
            self.processing_panel.set_status("Nothing selected to process.")

        self._update_pipeline_state()
        self._refresh_current_frame()

    def _retarget(self) -> None:
        rig_id = self.rig_panel.current_rig_id()
        if rig_id is None:
            return

        try:
            clip = self._controller.retarget(rig_id)
        except (RuntimeError, OSError) as error:
            self.rig_panel.set_status(str(error))
            return

        issues = self._controller.retarget_issues()
        summary = (
            f"Retargeted to {rig_id}: {clip.bone_count} bones, "
            f"{clip.frame_count} frames"
        )
        self.rig_panel.set_status(
            f"{summary}. {issues[0]}" if issues else f"{summary}. Full coverage."
        )

        self._update_pipeline_state()

    def _on_import_rig(self) -> None:
        """Load an exported armature, then review its mapping."""

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import Rig",
            "",
            "Motion capture rig (*.json);;All files (*)",
        )

        if not path_str:
            return

        try:
            dump, mapping, groups = self._controller.read_armature(Path(path_str))
        except ArmatureImportError as error:
            self.rig_panel.set_status(f"Could not read the rig: {error}")
            return

        self._edit_rig_profile(
            CustomRigDialog(
                bone_names=dump.bone_names,
                mapping=mapping,
                groups=groups,
                display_name=dump.armature_name,
                unit_scale=dump.unit_scale,
                parent=self,
            )
        )

    def _on_new_rig(self) -> None:
        """Create a rig profile by typing the bone names by hand."""

        self._edit_rig_profile(CustomRigDialog(parent=self))

    def _edit_rig_profile(self, dialog: CustomRigDialog) -> None:
        """Run ``dialog`` and install the profile it produces."""

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        rig_id = self._controller.unique_rig_id(dialog.name_edit.text())

        try:
            info = self._controller.add_rig_profile(dialog.document(rig_id))
        except RigProfileError as error:
            self.rig_panel.set_status(f"Could not save the rig: {error}")
            return

        self.rig_panel.set_rigs(self._controller.available_rigs())
        self.rig_panel.select_rig(info.rig_id)
        self.rig_panel.set_status(
            f"Added rig '{info.display_name}' - "
            f"{len(dialog.bone_map())} bone(s) mapped."
        )

    def _on_remove_rig(self) -> None:
        """Delete the selected custom rig profile."""

        rig_id = self.rig_panel.current_rig_id()
        if rig_id is None:
            return

        try:
            self._controller.remove_rig_profile(rig_id)
        except RigProfileError as error:
            self.rig_panel.set_status(f"Could not remove the rig: {error}")
            return

        self.rig_panel.set_rigs(self._controller.available_rigs())
        self.rig_panel.set_status(f"Removed rig '{rig_id}'.")
        self._update_pipeline_state()

    def _on_keypoint_moved(self, joint: JointName, position: Vector3) -> None:
        self._controller.correct_keypoint(joint, position)
        self._refresh_after_correction(f"Corrected {joint.value}")

    def _undo_correction(self) -> None:
        if not self._controller.can_undo:
            return
        self._controller.undo()
        self._refresh_after_correction("Undo")

    def _redo_correction(self) -> None:
        if not self._controller.can_redo:
            return
        self._controller.redo()
        self._refresh_after_correction("Redo")

    def _propagate_correction(self) -> None:
        joint = self.video_view.selected_joint
        if joint is None:
            return

        if self._controller.propagate_keypoint(joint):
            self._refresh_after_correction(f"Propagated {joint.value}")
        else:
            self.correction_panel.set_status(
                f"{joint.value}: needs corrections on at least two frames"
            )

    def _clear_correction(self) -> None:
        joint = self.video_view.selected_joint
        if joint is None:
            return
        self._controller.clear_keypoint(joint)
        self._refresh_after_correction(f"Cleared {joint.value}")

    def _refresh_after_correction(self, message: str) -> None:
        self._refresh_current_frame()
        self.correction_panel.set_undo_redo(
            can_undo=self._controller.can_undo,
            can_redo=self._controller.can_redo,
        )
        self.correction_panel.set_status(
            f"{message} - {self._controller.correction_count} correction(s)"
        )
        self._update_pipeline_state()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._playback_timer.stop()
        self._controller.close()
        super().closeEvent(event)
