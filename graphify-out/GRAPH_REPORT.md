# Graph Report - motion_captire_ai  (2026-08-28)

## Corpus Check
- Corpus is ~46,777 words - fits in a single context window. You may not need a graph.

## Summary
- 1688 nodes · 4448 edges · 129 communities (96 shown, 33 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 496 edges (avg confidence: 0.93)
- Token cost: 46,777 input · 5,200 output

## Community Hubs (Navigation)
- Test Fixtures And Harness
- Project Persistence
- Video View Overlay
- BVH Export And Vector Math
- Frame Reading And Streaming
- Background Task Manager
- Rig Data Model
- Full Video Analysis
- Undo Redo Command Stack
- Keypoint Correction Layer
- MediaPipe Backend
- Quaternion Rotation Math
- Pose Detector Interface
- Blender Coordinate Conversion
- Animation Clip Export
- Blender Clip Parsing
- Keypoint Schema Mapping
- Timeline Widget Tests
- Controller Integration Tests
- Reconstruction Backends
- Application Shell
- Skeleton Retargeting
- Rig Registry Tests
- Blender Add-on Operators
- Armature Auto Mapping
- Pose Sequence Tracks
- Plugin Backend Registry
- Custom Rig Dialog
- Controller Rig Management
- Coordinate Space Conversion
- Detector Panel
- Animation Processing Tests
- UI Formatting And Theme
- Playback Controller
- BVH Export Tests
- Rig Panel Controls
- Trajectory Cleanup Passes
- MediaPipe 3D Lift
- Armature Import Tests
- Controller Playback State
- Timeline Scrub Controls
- Custom Rig UI Tests
- Correction Layer Tests
- Backend Availability Types
- Main Window Pipeline Wiring
- Skeleton Validation
- Rig Profile Installation
- Rig Profile Parsing
- Skeleton Solver Tests
- Main Window Export Actions
- Main Window Project Menu
- Correction Panel
- Reconstruction Panel
- Correction UI Tests
- Rig Profile Controller API
- World Landmark Lift
- Reconstruction Interface
- Main Window Detection Flow
- Pipeline Section Widget
- Main Window Frame Display
- Processing Panel
- Skeleton Panel
- Playback UI Tests
- Correction Commands
- Controller Skeleton Build
- Shortest Arc Rotation
- Reconstruction UI Tests
- Profile Document Building
- Navigation UI Tests
- Entry Point Discovery
- Pose Registry Tests
- Main Window Shortcuts
- Project Doctrine And Rules
- Rig Profile Slugging
- Main Window Menu Setup
- Sequential Frame Fast Path
- Frame Stream Buffer
- Data Model Levels
- Video Import UI Tests
- Controller Detector Setup
- Blender Armature Import
- Architecture Doctrine
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Controller Accessor
- Build Configuration

## God Nodes (most connected - your core abstractions)
1. `Vector3` - 139 edges
2. `ProjectController` - 137 edges
3. `MainWindow` - 128 edges
4. `JointName` - 117 edges
5. `CanonicalBoneName` - 61 edges
6. `Quaternion` - 59 edges
7. `PoseSequence` - 52 edges
8. `CorrectionLayer` - 49 edges
9. `PoseFrame` - 49 edges
10. `FrameReader` - 44 edges

## Surprising Connections (you probably didn't know these)
- `Schema Versioning` --references--> `save_project()`  [EXTRACTED]
  docs/data_model.md → app/core/project_io.py
- `Canonical World Space (Y-up)` --implements--> `CoordinateSpace`  [EXTRACTED]
  docs/architecture.md → app/math/coordinates.py
- `Partial Bone Map Is Valid` --implements--> `retarget_issues()`  [EXTRACTED]
  docs/formats/rig_profile_v1.md → app/retarget/retargeter.py
- `UI Redesign` --implements--> `MainWindow`  [EXTRACTED]
  docs/roadmap.md → app/ui/main_window.py
- `Non-Blocking UI` --references--> `FrameReader`  [INFERRED]
  docs/architecture.md → app/video/frame_reader.py

## Import Cycles
- 3-file cycle: `blender_addon/__init__.py -> blender_addon/ui.py -> blender_addon/importer.py -> blender_addon/__init__.py`

## Hyperedges (group relationships)
- **Four-Level Data Pipeline** — docs_data_model_level0_raw_pose, docs_data_model_level1_canonical_pose, docs_data_model_level2_skeleton_clip, docs_data_model_level3_rig_clip [EXTRACTED 1.00]
- **Custom Rig Authoring Flow** — docs_formats_rig_profile_v1_armature_dump, docs_formats_rig_profile_v1_auto_mapping, app_ui_widgets_custom_rig_dialog_customrigdialog, app_retarget_rig_registry_rigregistry_install_profile, docs_formats_rig_profile_v1_scan_precedence [EXTRACTED 1.00]
- **Rig Decoupling Principles** — claude_rig_independent_skeleton, docs_architecture_rig_name_independence, docs_formats_mcapclip_v1_embedded_bone_map, docs_formats_rig_profile_v1_profile [INFERRED 0.85]

## Communities (129 total, 33 thin omitted)

### Community 0 - "Test Fixtures And Harness"
Cohesion: 0.05
Nodes (100): corrupt_video(), main_window(), make_main_window(), make_pose_registry(), person_image(), person_video(), fixture, Path (+92 more)

### Community 1 - "Project Persistence"
Cohesion: 0.10
Nodes (59): Application-level orchestration for a motion capture project. The controller…, _check_version(), load_project(), LoadedProject, ProjectFormatError, ProjectIOError, ProjectVersionError, Any (+51 more)

### Community 2 - "Video View Overlay"
Cohesion: 0.08
Nodes (35): ndarray, QMouseEvent, Widget that displays a video frame with an editable pose overlay., Rescale the source frame to the widget size and draw the overlay., Return a copy of ``pixmap`` with the current pose drawn on it., Convert a BGR ``uint8`` frame into an RGB :class:`QPixmap`., Display one video frame with an optional, editable pose overlay.…, Show ``frame``, a BGR ``uint8`` array of shape ``(H, W, 3)``. A new frame… (+27 more)

### Community 3 - "BVH Export And Vector Math"
Cohesion: 0.10
Nodes (41): _bone_ending_at(), _build_tree(), _BvhJoint, _emit_joint(), _flatten(), Export a canonical :class:`SkeletonClip` to a BioVision Hierarchy (.bvh) file.…, _rest_segment(), _rotation_for() (+33 more)

### Community 4 - "Frame Reading And Streaming"
Cohesion: 0.08
Nodes (30): FrameReader, ndarray, Path, Self, Random-access frame reading for video files., Read individual frames from a video file by index. Frames are returned in…, Return the path of the open video file., Return the number of frames reported by the container. May be ``0`` when the… (+22 more)

### Community 5 - "Background Task Manager"
Cohesion: 0.08
Nodes (31): Run the selected detector over every frame in the background. ``on_progress``…, CancelToken, Enum, str, Background task execution, kept free of Qt. A :class:`TaskManager` runs…, Stop accepting work and drop queued tasks., A cooperative cancellation flag., Request cancellation. (+23 more)

### Community 6 - "Rig Data Model"
Cohesion: 0.10
Nodes (31): CoordinateSpace, str, The coordinate spaces pose data can live in., Quaternion, A unit quaternion in ``(w, x, y, z)`` order., Return whether the quaternion has unit norm., Target rig description, canonical-to-rig mapping, and the retargeted clip (L3)., A target armature, described independently of any file format. (+23 more)

### Community 7 - "Full Video Analysis"
Cohesion: 0.13
Nodes (33): analyze_video(), analyze_video_parallel(), _detect_range(), _Progress, Path, Run a pose detector over every frame of a video., Thread-safe progress counter., Detect a pose in every frame and return the resulting sequence. Single-… (+25 more)

### Community 8 - "Undo Redo Command Stack"
Cohesion: 0.09
Nodes (17): Command, CommandStack, ABC, Undo/redo command stack and the manual-correction commands. Kept free of Qt.…, Undo the action, restoring the previous state., A linear undo/redo history., Run ``command`` and push it onto the undo stack., Revert the most recent command. (+9 more)

### Community 9 - "Keypoint Correction Layer"
Cohesion: 0.09
Nodes (21): ClearKeypointCorrection, Remove the correction for one joint on one frame., CorrectionLayer, Sparse per-frame overrides of canonical joint positions for one track. The…, Return whether the layer holds no corrections., Record ``joint`` at ``position`` for ``frame_index``., Remove the correction for ``joint`` at ``frame_index``, if any., Return the corrected position for ``joint`` at ``frame_index``. (+13 more)

### Community 10 - "MediaPipe Backend"
Cohesion: 0.10
Nodes (23): KeypointSchema, Describes a named set of keypoints produced by a detector. ``connections``…, Return the number of keypoints in this schema., MediaPipeDetector, Path, MediaPipe Tasks pose detector (optional backend). Requires the ``mediapipe``…, Single-person 2D pose detection with MediaPipe's ``PoseLandmarker``. Pass…, default_model_path() (+15 more)

### Community 11 - "Quaternion Rotation Math"
Cohesion: 0.14
Nodes (25): _list_to_quaternion(), _list_to_vector(), _quaternion_to_list(), Read and write the ``mcapclip`` animation interchange format (v1). An…, _vector_to_list(), _any_perpendicular(), ndarray, Quaternion rotations, backed by :mod:`scipy.spatial.transform`.… (+17 more)

### Community 12 - "Pose Detector Interface"
Cohesion: 0.09
Nodes (17): DetectorCapabilities, Descriptive capabilities of a pose detector., What a pose detector can do, for display and validation., PoseDetector, ABC, ndarray, Abstract interface for pose detectors., Detect human pose keypoints in video frames. Implementations return Level 0… (+9 more)

### Community 13 - "Blender Coordinate Conversion"
Cohesion: 0.11
Nodes (23): build_dump_document(), Build the armature-dump document the desktop app imports. Standard library only…, Return the armature-dump document for ``bones``. Args: armature_name: The…, Write ``document`` to ``path`` as UTF-8 JSON., write_dump(), canonical_to_blender_location(), canonical_to_blender_quaternion(), quaternion_conjugate() (+15 more)

### Community 14 - "Animation Clip Export"
Cohesion: 0.17
Nodes (27): AnimationExportError, export_animation(), import_animation(), Any, Exception, Path, Write ``clip`` to ``path`` as an ``mcapclip`` v1 file., Read an ``mcapclip`` file from ``path``. Raises: AnimationExportError: The file… (+19 more)

### Community 15 - "Blender Clip Parsing"
Cohesion: 0.11
Nodes (26): ClipBone, ClipFrame, load_clip(), McapClipError, parse_clip(), ParsedClip, Exception, Path (+18 more)

### Community 16 - "Keypoint Schema Mapping"
Cohesion: 0.13
Nodes (21): Detect a pose in the current frame with the selected backend. Returns the…, Level 0 pose data: detector-native keypoints., One detector output for a single frame, in the detector's own schema.…, RawPose, ndarray, _blend(), mediapipe_to_canonical(), Convert detector-native keypoints (Level 0) to the canonical skeleton (Level… (+13 more)

### Community 17 - "Timeline Widget Tests"
Cohesion: 0.16
Nodes (20): Controls for playing a video and navigating it frame by frame. Signals:…, Timeline, QApplication, Tests for the Timeline navigation widget (roadmap Phase 4)., test_buttons_disable_at_bounds(), test_next_button_emits_incremented_index(), test_play_button_toggles_and_emits(), test_previous_button_emits_decremented_index() (+12 more)

### Community 18 - "Controller Integration Tests"
Cohesion: 0.19
Nodes (25): ProjectController, Coordinate operations on a single motion capture project., _analyse_synchronously(), Path, ProjectController tests: import, navigation, playback, persistence (Phase 8)., test_advance_playback_advances_one_frame_while_playing(), test_advance_playback_auto_pauses_at_end(), test_advance_playback_returns_none_when_paused() (+17 more)

### Community 19 - "Reconstruction Backends"
Cohesion: 0.11
Nodes (16): Return the pose-detection backends that can be used., Return the registered backends that cannot be used, with reasons., Return the usable 3D reconstruction backends., A generic registry of pluggable backends. Backends are registered explicitly by…, BackendEntry, Types for the generic backend registry., A registered backend: how to build it and whether it is usable., The registry of pose-detection backends. Call… (+8 more)

### Community 20 - "Application Shell"
Cohesion: 0.11
Nodes (12): main(), Application entry point., MainWindow, Main application window., Ask the running analysis to stop., Return the project controller backing this window., QCloseEvent, QMainWindow (+4 more)

### Community 21 - "Skeleton Retargeting"
Cohesion: 0.18
Nodes (22): Return the identity rotation., Return every bone name, parent-first., One frame of the canonical skeleton. ``bone_rotations`` are local (relative to…, A sequence of :class:`SkeletonPose` for one person., SkeletonClip, SkeletonPose, Produce a :class:`RigClip` for ``rig`` from ``skeleton_clip``. Each canonical…, Return notes about canonical bones the map does not cover. (+14 more)

### Community 22 - "Rig Registry Tests"
Cohesion: 0.24
Nodes (23): build_rig_registry(), Return a registry populated with bundled profiles plus any extras. Later…, _profile(), Path, Tests for rig-profile discovery and loading (roadmap Phase 13)., test_a_later_directory_wins_for_the_same_id(), test_bundled_profiles_are_available(), test_bundled_profiles_are_flagged_as_bundled() (+15 more)

### Community 23 - "Blender Add-on Operators"
Cohesion: 0.11
Nodes (19): _file_export_entry(), MCAP_OT_export_armature, Blender operator exporting the active armature's bone names. The resulting file…, Export the active armature's bones as a Motion Capture rig file., register(), unregister(), AI Mocap -- import a ``.mcapclip.json`` animation onto a Blender armature. This…, Register the add-on's Blender classes. (+11 more)

### Community 24 - "Armature Auto Mapping"
Cohesion: 0.14
Nodes (22): Read an armature exported from a DCC and guess its bone mapping. Returns: The…, ArmatureDump, ArmatureImportError, load_armature_dump(), parse_armature_dump(), Exception, Path, Read an armature dump from ``path``. Raises: ArmatureImportError: The file… (+14 more)

### Community 25 - "Pose Sequence Tracks"
Cohesion: 0.13
Nodes (15): PersonTrack, PoseSequence, One person's pose across a video. ``frames`` (Level 1, canonical) and…, Return whether a pose was detected at ``frame_index``., Return the sorted frame indices that have a detected pose., Return how many frames have a detected pose., All pose tracks detected for one video., Add ``track`` to the sequence, optionally making it the active one. (+7 more)

### Community 26 - "Plugin Backend Registry"
Cohesion: 0.13
Nodes (16): BackendRegistry, Holds the backend entries for one extension point., Add ``entry``, replacing any entry with the same id., Return the entry registered under ``backend_id``. Raises: KeyError: No backend…, Instantiate the backend ``backend_id`` through its factory. Raises: KeyError:…, Register backends advertised by installed packages. Each entry point must…, _entry(), Tests for the generic BackendRegistry (roadmap Phase 6). (+8 more)

### Community 27 - "Custom Rig Dialog"
Cohesion: 0.16
Nodes (14): CustomRigDialog, QWidget, Return the non-empty canonical to rig-bone mapping., Return the rig-profile document for ``rig_id``., Refuse to close while the profile is unusable., Edit a rig profile: its name, scale, and one rig bone per canonical bone. Args:…, QDialog, QApplication (+6 more)

### Community 28 - "Controller Rig Management"
Cohesion: 0.12
Nodes (8): ndarray, Return the frame at ``index`` from the imported video (BGR). This does not…, Navigate to ``index`` and return the frame there (BGR). ``index`` is clamped to…, Navigate by ``delta`` frames (clamped) and return the frame., Start playback, if a video is loaded., Pause playback and rewind to the first frame., Advance one frame during playback. Returns the next frame, or ``None`` when…, Release resources: cancel analysis, close the video and detector.

### Community 29 - "Coordinate Space Conversion"
Cohesion: 0.15
Nodes (15): image_to_canonical(), mediapipe_world_to_canonical(), Enum, Explicit conversions between the coordinate spaces used in the pipeline. See…, Map a 2D image-pixel point to ``CANONICAL_WORLD``. Image space has y growing…, Map a MediaPipe world landmark to ``CANONICAL_WORLD``. MediaPipe world…, Level 1 pose data across a whole video: person tracks and their sequence., _canonical_positions() (+7 more)

### Community 30 - "Detector Panel"
Cohesion: 0.12
Nodes (9): DetectorPanel, QWidget, Return the id of the selected backend, or ``None`` if none., Show a one-line status message., Enable detection only once a video is available., Toggle the panel between idle and 'analysis in progress'., Update the progress bar to ``done`` of ``total`` frames., Choose a pose-detection backend and run it on the frame or whole video.… (+1 more)

### Community 31 - "Animation Processing Tests"
Cohesion: 0.26
Nodes (17): process_sequence(), ProcessingOptions, ProcessingReport, What :func:`process_sequence` actually did., Which cleanup passes to run and with what parameters., Return a cleaned copy of ``pose_sequence`` plus a report. Manual corrections…, Run the enabled cleanup passes and use the result downstream. Processes the 3D…, Tests for the animation cleanup passes (roadmap Phase 14). (+9 more)

### Community 32 - "UI Formatting And Theme"
Cohesion: 0.15
Nodes (15): format_video_line(), format_video_summary(), Helpers that turn domain objects into display strings for the UI., Return a compact, single-line summary of a video for a header label. Args:…, Return a human-readable, one-item-per-line summary of a video. Args: metadata:…, Main application window for the AI Motion Capture app., apply_dark_theme(), QApplication (+7 more)

### Community 33 - "Playback Controller"
Cohesion: 0.14
Nodes (12): PlaybackController, Playback timing and play/pause state for a video. This module is deliberately…, Track play/pause state and the frame interval derived from the FPS., Return whether playback is currently running., Return the delay between frames in milliseconds (at least 1)., parametrize, Tests for the Qt-free PlaybackController (roadmap Phase 5)., test_frame_interval_is_at_least_one_millisecond() (+4 more)

### Community 34 - "BVH Export Tests"
Cohesion: 0.25
Nodes (17): _euler_zyx(), export_bvh(), Path, Write ``clip`` to ``path`` as a ``.bvh`` file., Return the full text of a BVH file for ``clip``., write_bvh_document(), _clip(), _lines() (+9 more)

### Community 35 - "Rig Panel Controls"
Cohesion: 0.14
Nodes (10): QWidget, Enable retargeting only once a skeleton has been solved., Return the selected rig id, or ``None``., Show a one-line status message., Choose a target rig and retarget the solved skeleton onto it. Signals:…, Populate the combo with the available rig profiles., Select ``rig_id`` in the combo, if it is listed., RigPanel (+2 more)

### Community 36 - "Trajectory Cleanup Passes"
Cohesion: 0.22
Nodes (15): _build_sequence(), _despike(), _fill_gaps(), _lock_feet(), _moving_average(), Enum, ndarray, str (+7 more)

### Community 37 - "MediaPipe 3D Lift"
Cohesion: 0.21
Nodes (13): MediaPipeWorldReconstruction, Turn stored MediaPipe world landmarks into a canonical 3D track., ndarray, Tests for 3D reconstruction backends (roadmap Phase 15)., _sequence(), test_axes_are_flipped_to_y_up(), test_can_reconstruct_requires_world_depth_data(), test_derived_joints_are_between_their_sources() (+5 more)

### Community 38 - "Armature Import Tests"
Cohesion: 0.19
Nodes (16): auto_map(), build_profile_document(), Any, Guess a canonical-bone to rig-bone mapping from ``bone_names``. Each rig bone…, Build a rig-profile document ready for ``RigRegistry.install_profile``. Empty…, parametrize, Tests for armature import and canonical-bone auto-mapping., test_auto_map_covers_both_sides_and_the_spine() (+8 more)

### Community 39 - "Controller Playback State"
Cohesion: 0.17
Nodes (7): Path, Load ``video_path`` and attach its metadata to the project. Also opens a…, Build the registry: bundled, then user profiles, then the project's., Write the solved skeleton clip to ``path`` as an ``mcapclip`` file. When…, Write the solved skeleton clip to ``path`` as a ``.bvh`` file. Raises:…, Save the project (and analysis) to ``project_dir``. With no argument, re-saves…, Load a project directory: its video and any stored analysis. Raises:…

### Community 40 - "Timeline Scrub Controls"
Cohesion: 0.14
Nodes (8): QWidget, Playback and frame-navigation controls. Phase 4 added step and jump-to-frame…, Disable the controls and clear the readout (no video loaded)., Configure the controls for a video with ``frame_count`` frames. A non-positive…, Refresh the readout to ``index`` / ``timestamp`` without emitting., Refresh the play button to reflect ``playing`` without emitting., Temporarily block a widget's Qt signals., _signals_blocked()

### Community 41 - "Custom Rig UI Tests"
Cohesion: 0.31
Nodes (15): _analysed_with_skeleton(), MakeRegistry, MakeWindow, Path, WaitFor, End-to-end tests for custom rig profiles (dialog, panel, persistence)., test_a_custom_rig_survives_save_and_reopen_elsewhere(), test_built_in_rigs_are_not_copied_into_the_project() (+7 more)

### Community 42 - "Correction Layer Tests"
Cohesion: 0.25
Nodes (13): effective_pose(), lerp_vector3(), Non-destructive manual corrections layered on top of detected poses., Linearly interpolate between two vectors (``t`` in ``[0, 1]``)., Merge ``detected`` with ``corrections`` into the pose actually shown. Corrected…, Joint, _detected(), Tests for the CorrectionLayer and effective-pose merge (roadmap Phase 9). (+5 more)

### Community 43 - "Backend Availability Types"
Cohesion: 0.28
Nodes (12): BackendAvailability, Whether a backend can be used, and why not when it cannot., Return an 'available' result., Return an 'unavailable' result carrying ``reason``., _mediapipe_availability(), _entry(), QApplication, Tests for the DetectorPanel widget (roadmap Phase 6). (+4 more)

### Community 44 - "Main Window Pipeline Wiring"
Cohesion: 0.13
Nodes (8): ndarray, Put the compact summary on the header label, the full one in a tooltip., Prompt for a video file and load the selected one., Load ``video_path`` into the project and update the display. Errors are…, Navigate to ``index`` and refresh the frame view and timeline. Manual…, Move the current position by ``delta`` frames., Advance one frame; stop the timer when playback ends., Show ``frame``, the effective pose overlay (if any), and the readout.

### Community 45 - "Skeleton Validation"
Cohesion: 0.27
Nodes (12): Return validation issues for the current skeleton clip., bone_length_report(), Return structural problems with ``clip`` (empty when it looks sound)., Flag bones whose measured length is unstable across frames. A rigid limb should…, validate_skeleton_clip(), _frame(), Tests for skeleton validation (roadmap Phase 10)., _sequence() (+4 more)

### Community 46 - "Rig Profile Installation"
Cohesion: 0.15
Nodes (11): Any, Exception, Return whether ``rig_id`` comes from the bundled profiles., Return the raw JSON document behind ``rig_id``. Raises: RigProfileError: The id…, Validate ``document`` and write it to the install directory. An existing…, A rig profile file is missing, malformed or cannot be written., Return the per-user directory holding custom rig profiles., RigProfileError (+3 more)

### Community 47 - "Rig Profile Parsing"
Cohesion: 0.20
Nodes (8): Path, Delete a custom profile. Raises: RigProfileError: The id is unknown or bundled,…, Holds the rig profiles found across a set of directories. ``install_dir`` is…, Register every ``*.json`` profile in ``directory`` (if it exists). The…, Re-scan every registered directory, picking up new files., Return whether ``rig_id`` is known., RigRegistry, test_empty_registry_lists_nothing()

### Community 48 - "Skeleton Solver Tests"
Cohesion: 0.42
Nodes (13): Solve bone rotations for every analysed frame of ``pose_sequence``. Frames with…, solve_skeleton(), _angle(), _frame(), Tests for the skeleton solver maths (roadmap Phase 10)., _sequence(), test_bent_forearm_gives_a_quarter_turn_local_rotation(), test_canonical_world_track_is_used_without_a_y_flip() (+5 more)

### Community 49 - "Main Window Export Actions"
Cohesion: 0.20
Nodes (5): Path, Load a project directory and update the display., Save the project to ``project_dir`` and report the outcome., Export the solved skeleton clip and report the outcome. When a retarget is…, Export the solved skeleton clip as BVH and report the outcome.

### Community 50 - "Main Window Project Menu"
Cohesion: 0.17
Nodes (4): Enable each step once its inputs exist and highlight the next one. This is UI…, Stop playback and rewind to the first frame., Re-read and display the current frame., Delete the selected custom rig profile.

### Community 51 - "Correction Panel"
Cohesion: 0.17
Nodes (7): CorrectionPanel, QWidget, Manual keypoint-correction controls., Toggle correction editing and drive undo/redo/propagate/clear. Signals:…, Enable joint-specific actions when a joint is selected., Reflect the command stack state on the undo/redo buttons., Show a one-line status message.

### Community 52 - "Reconstruction Panel"
Cohesion: 0.18
Nodes (7): QWidget, Choose a 3D reconstruction backend and run it. Signal: reconstruct_requested():…, Populate the combo with the available reconstruction backends., Enable reconstruction only once the sequence has been analysed., Return the selected backend id, or ``None``., Show a one-line status message., ReconstructionPanel

### Community 53 - "Correction UI Tests"
Cohesion: 0.45
Nodes (12): _analysed_window(), MakeRegistry, MakeWindow, Path, WaitFor, End-to-end UI tests for manual keypoint correction (roadmap Phase 9)., Mimic the user clicking a joint (which selects it) and dragging it., _select_and_move() (+4 more)

### Community 54 - "Rig Profile Controller API"
Cohesion: 0.17
Nodes (7): Return the rig profiles that can be retargeted to., Install a custom rig profile and make it selectable. Raises: RigProfileError:…, Lightweight description of an available rig profile., Return the known profiles, ordered by id., Return the description of ``rig_id``, or ``None``., RigProfileInfo, Retarget the canonical skeleton onto a chosen rig.

### Community 55 - "World Landmark Lift"
Cohesion: 0.21
Nodes (9): PoseFrame, Pose information for one video frame., Return the pose at ``frame_index``, or ``None`` when not detected., Return the active track's pose at ``frame_index``, if detected., _average(), _frame_from_world(), _lerp(), ndarray (+1 more)

### Community 56 - "Reconstruction Interface"
Cohesion: 0.17
Nodes (8): ABC, Lift a 2D pose sequence to a 3D ``CANONICAL_WORLD`` one., Return the stable id of this backend., Return the user-facing name of this backend., Return whether this backend has what it needs for ``pose_sequence``., Return a new sequence whose active track is in ``CANONICAL_WORLD``., ReconstructionBackend, Deferred 3D Reconstruction

### Community 57 - "Main Window Detection Flow"
Cohesion: 0.20
Nodes (6): QWidget, Instantiate the widgets and connect their signals., Left pane: the frame view and the timeline below it., Right pane: a scrollable column of numbered pipeline sections., Create the main user interface. Layout: a horizontal splitter with the video…, QLabel

### Community 58 - "Pipeline Section Widget"
Cohesion: 0.18
Nodes (8): PipelineSection, QWidget, A titled container for one step of the processing pipeline. Each section wraps…, Wrap ``body`` in a titled, state-aware card. Args: number: The step number…, Return the current visual state., Update the visual state and the trailing hint text., QFrame, SectionState

### Community 59 - "Main Window Frame Display"
Cohesion: 0.22
Nodes (5): Toggle playback (space bar)., Make sure the controller uses the panel's selected backend., Run the selected detector on the current frame and show the pose., Detect a pose in every frame, in the background., Start or pause playback and keep the timer and button in sync.

### Community 60 - "Processing Panel"
Cohesion: 0.20
Nodes (6): ProcessingPanel, QWidget, Choose which cleanup passes to run on the analysed sequence. Signal:…, Enable processing only once the sequence has been analysed., Return the :class:`ProcessingOptions` for the ticked passes., Show a one-line status message.

### Community 61 - "Skeleton Panel"
Cohesion: 0.20
Nodes (6): QWidget, Build the canonical skeleton from the analysed pose sequence., Enable building only once the sequence has been analysed., Show a one-line status message., A button to solve the canonical skeleton plus a result readout. Signal:…, SkeletonPanel

### Community 62 - "Playback UI Tests"
Cohesion: 0.33
Nodes (9): Path, End-to-end UI tests for video playback (roadmap Phase 5)., test_arrow_key_during_playback_pauses(), test_manual_navigation_pauses_playback(), test_play_button_second_click_pauses(), test_play_button_starts_playback_and_timer(), test_playback_auto_pauses_at_end(), test_playback_tick_advances_frame_and_readout() (+1 more)

### Community 63 - "Correction Commands"
Cohesion: 0.25
Nodes (4): PropagateKeypointCorrection, Interpolate one joint's corrections across its keyframe span. Fills every frame…, Return whether the command would change anything., test_propagate_needs_two_keyframes()

### Community 64 - "Controller Skeleton Build"
Cohesion: 0.28
Nodes (4): Move ``joint`` to ``position`` on the current frame (undoable)., Remove the correction for ``joint`` on the current frame (undoable)., Interpolate ``joint`` across its corrected keyframes (undoable). Returns…, Drop the reconstruction, processed sequence and derived clips.

### Community 65 - "Shortest Arc Rotation"
Cohesion: 0.28
Nodes (5): Build a :class:`Quaternion` from a SciPy :class:`Rotation`., Return the equivalent SciPy :class:`Rotation`., Return ``self * other`` (apply ``other`` first, then ``self``)., Return the inverse rotation., Rotation

### Community 66 - "Reconstruction UI Tests"
Cohesion: 0.47
Nodes (8): _analyse(), Path, WaitFor, End-to-end tests for 3D reconstruction via the UI (roadmap Phase 15). Uses the…, test_correcting_a_keypoint_drops_the_reconstruction(), test_overlay_stays_two_dimensional_after_reconstruction(), test_reconstruct_lists_a_backend(), test_reconstruct_then_build_uses_the_3d_track()

### Community 67 - "Profile Document Building"
Cohesion: 0.29
Nodes (6): _classify(), Turn a target armature's bone names into a rig profile. Two things live here: *…, Return the canonical role ``name`` plays plus a confidence score., Split a bone name into meaningful tokens plus its side, if any., _tokenise(), Review and edit the canonical-bone to rig-bone mapping of a custom rig.

### Community 68 - "Navigation UI Tests"
Cohesion: 0.36
Nodes (7): Path, End-to-end UI tests for frame navigation (roadmap Phase 4)., test_arrow_key_shortcuts_are_bound_and_navigate(), test_jump_via_spinbox(), test_navigation_disabled_before_any_video(), test_next_button_advances_frame_and_updates_readout(), test_previous_at_start_is_a_noop()

### Community 69 - "Entry Point Discovery"
Cohesion: 0.33
Nodes (3): Return every registered entry, ordered by id., Return the entries whose backend can be used., Return the entries whose backend cannot be used.

### Community 70 - "Pose Registry Tests"
Cohesion: 0.47
Nodes (5): build_pose_backend_registry(), Return a registry populated with built-in and discovered backends., Tests for the pose-backend registry (roadmap Phase 6)., test_mediapipe_entry_reports_availability_without_crashing(), test_registry_lists_the_mediapipe_backend()

### Community 71 - "Main Window Shortcuts"
Cohesion: 0.33
Nodes (3): Load an exported armature, then review its mapping., Create a rig profile by typing the bone names by hand., Run ``dialog`` and install the profile it produces.

### Community 72 - "Project Doctrine And Rules"
Cohesion: 0.33
Nodes (6): Incremental Development Workflow, Modular Architecture Rule, UI / AI Logic Separation, Architecture Decision Records, Lightweight Hexagonal Architecture, Seventeen-Phase Roadmap

### Community 73 - "Rig Profile Slugging"
Cohesion: 0.40
Nodes (4): Return ``preferred`` slugified, suffixed until it is unused., Turn a display name into a safe ``rig_id`` (lowercase, ``a-z0-9_``). Returns…, slugify(), test_slugify_makes_a_safe_id()

### Community 75 - "Sequential Frame Fast Path"
Cohesion: 0.40
Nodes (3): BaseException, TracebackType, Release the underlying video capture.

### Community 76 - "Frame Stream Buffer"
Cohesion: 0.40
Nodes (3): BaseException, TracebackType, Stop the worker thread and release the reader.

### Community 77 - "Data Model Levels"
Cohesion: 0.50
Nodes (5): Four-Level Data Pipeline, Level 0 - Raw Pose, Level 1 - Canonical Pose, Level 2 - Skeleton Clip, Level 3 - Rig Clip

### Community 78 - "Video Import UI Tests"
Cohesion: 0.50
Nodes (4): Path, UI-level tests for the video import flow (roadmap Phase 2 and 3)., test_load_missing_video_shows_error_without_crashing(), test_load_video_updates_status_info_and_frame()

### Community 80 - "Blender Armature Import"
Cohesion: 0.50
Nodes (3): apply_clip_to_armature(), Apply a parsed mcapclip onto a Blender armature. Imports ``bpy`` /…, Insert keyframes on ``armature`` from ``clip``; return bones touched. Canonical…

### Community 81 - "Architecture Doctrine"
Cohesion: 0.67
Nodes (3): Blender Code Isolation, Canonical World Space (Y-up), Y-up Interchange, Z-up at the Boundary

## Knowledge Gaps
- **2 isolated node(s):** `ai-motion-capture`, `Blender Add-on Installation`
  These have ≤1 connection - possible missing edges or undocumented components.
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ProjectController` connect `Controller Integration Tests` to `Test Fixtures And Harness`, `Project Persistence`, `Frame Reading And Streaming`, `Background Task Manager`, `Rig Data Model`, `Full Video Analysis`, `Undo Redo Command Stack`, `Keypoint Correction Layer`, `Quaternion Rotation Math`, `Pose Detector Interface`, `Keypoint Schema Mapping`, `Reconstruction Backends`, `Application Shell`, `Skeleton Retargeting`, `Armature Auto Mapping`, `Pose Sequence Tracks`, `Plugin Backend Registry`, `Controller Rig Management`, `Animation Processing Tests`, `UI Formatting And Theme`, `Playback Controller`, `Controller Playback State`, `Custom Rig UI Tests`, `Skeleton Validation`, `Rig Profile Installation`, `Rig Profile Parsing`, `Rig Profile Controller API`, `World Landmark Lift`, `Correction Commands`, `Controller Skeleton Build`, `Project Doctrine And Rules`, `Main Window Menu Setup`, `Controller Detector Setup`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`, `Controller Accessor`?**
  _High betweenness centrality (0.282) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Application Shell` to `Test Fixtures And Harness`, `Project Persistence`, `Video View Overlay`, `Background Task Manager`, `Keypoint Correction Layer`, `Quaternion Rotation Math`, `Timeline Widget Tests`, `Controller Integration Tests`, `Reconstruction Backends`, `Armature Auto Mapping`, `Plugin Backend Registry`, `Custom Rig Dialog`, `Detector Panel`, `UI Formatting And Theme`, `Rig Panel Controls`, `Custom Rig UI Tests`, `Main Window Pipeline Wiring`, `Rig Profile Installation`, `Main Window Export Actions`, `Main Window Project Menu`, `Correction Panel`, `Reconstruction Panel`, `Correction UI Tests`, `Main Window Detection Flow`, `Pipeline Section Widget`, `Main Window Frame Display`, `Processing Panel`, `Skeleton Panel`, `Playback UI Tests`, `Reconstruction UI Tests`, `Navigation UI Tests`, `Main Window Shortcuts`, `Main Window Menu Setup`, `Video Import UI Tests`?**
  _High betweenness centrality (0.211) - this node is a cross-community bridge._
- **Why does `Vector3` connect `Quaternion Rotation Math` to `Test Fixtures And Harness`, `Project Persistence`, `Video View Overlay`, `BVH Export And Vector Math`, `Rig Data Model`, `Undo Redo Command Stack`, `Keypoint Correction Layer`, `Blender Coordinate Conversion`, `Animation Clip Export`, `Keypoint Schema Mapping`, `Controller Integration Tests`, `Application Shell`, `Skeleton Retargeting`, `Coordinate Space Conversion`, `Animation Processing Tests`, `UI Formatting And Theme`, `BVH Export Tests`, `Trajectory Cleanup Passes`, `Correction Layer Tests`, `Skeleton Validation`, `Skeleton Solver Tests`, `Correction UI Tests`, `World Landmark Lift`, `Correction Commands`, `Controller Skeleton Build`, `Reconstruction UI Tests`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `Vector3` (e.g. with `PropagateKeypointCorrection` and `SetKeypointCorrection`) actually correct?**
  _`Vector3` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `ProjectController` (e.g. with `ProcessingOptions` and `ProcessingReport`) actually correct?**
  _`ProjectController` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `MainWindow` (e.g. with `ProjectController` and `ProjectIOError`) actually correct?**
  _`MainWindow` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 66 inferred relationships involving `JointName` (e.g. with `_build_sequence()` and `ClearKeypointCorrection`) actually correct?**
  _`JointName` has 66 INFERRED edges - model-reasoned connections that need verification._