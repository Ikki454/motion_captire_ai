# Development Roadmap

> Revised 2026-08-27 to match the validated architecture
> ([`architecture.md` §13](architecture.md)). Key changes vs. the previous roadmap:
> - 3D reconstruction is **deferred** and becomes an interchangeable backend (Phase 15).
> - Export order is: internal format → animation export → Blender add-on → retargeting;
>   BVH is a **secondary** format (Phase 16).
> - Multi-person **data structures** land early (Phase 7); the UI stays single-person.
> - Concurrency (threads, buffering, GPU) is a **late** phase (Phase 17); the MVP is simple.

Work on **one phase at a time**. Do not implement a phase before it is requested. No
unrequested features, no placeholder implementations unless explicitly asked.

---

## Phase 1 — Application Shell  ✅ done 2026-08-27

- [x] Application starts (`uv run python -m app.main`)
- [x] Main window opens
- [x] Basic interface displayed
- [x] Headless smoke tests

## Phase 2 — Video Import  ← NEXT

- [ ] "Import Video" button opens a file-selection dialog
- [ ] `VideoLoader` extracts metadata (already implemented)
- [ ] Explicit error handling (missing file, unreadable/corrupt video) surfaced in the UI
- [ ] Display video information (path, resolution, FPS, frame count, duration)
- [ ] Store the loaded video on the `MotionCaptureProject`
- [ ] Tests: metadata display, error paths

## Phase 3 — Video Display

- [ ] `frame_reader` reads a frame by index
- [ ] Display the current frame in `video_view`
- [ ] Preserve aspect ratio on resize

## Phase 4 — Frame Navigation

- [ ] Step forward / backward one frame
- [ ] Jump to a specific frame
- [ ] Show the current frame index / timestamp

## Phase 5 — Video Playback  ✅ done 2026-08-27

- [x] Play / pause / stop
- [x] `QTimer` paced to the video FPS
- [x] Simple synchronous `PlaybackController` (Qt-free; UI owns the `QTimer` — architecture §8)

## Phase 6 — 2D Pose Detection  ✅ done 2026-08-27

- [x] `app.plugins.BackendRegistry` (manual + entry-point discovery, availability reporting)
- [x] `PoseDetector` interface emits Level 0 `RawPose`
- [x] First backend: MediaPipe (optional install, `uv sync --extra mediapipe`).
      MediaPipe 1.0 removed `solutions`; the backend uses the Tasks API and needs a
      model file — `python -m app.pose.backends.mediapipe_model` downloads it to `models/`.
- [x] Missing-backend state shown clearly in the detector panel
- [x] `KeypointMapping`: MediaPipe schema → canonical joints (Level 1)
- [x] Detect one person in the current frame (synchronous — full-video is Phase 7)
- [x] Draw the keypoint overlay on `video_view`
- [x] Tests: keypoint mapping, registry availability, real MediaPipe end-to-end

## Phase 7 — Full Video Analysis  ✅ done 2026-08-27

- [x] Run detection over all frames as a cancellable `Task` with progress
      (`app.core.tasks` — Qt-free `TaskManager` + `CancelToken`; `app.pose.analysis.analyze_video`)
- [x] Build `PoseSequence` → `PersonTrack` structures (multi-person capable; one track filled)
- [x] Handle missing detections as explicit gaps (sparse `PersonTrack.frames`)
- [x] Store MediaPipe world landmarks when available (`depth_source` tag) — raw, not canonicalised
- [x] Single active person in the UI (overlay follows navigation after analysis)

## Phase 8 — Pose Data Persistence  ✅ done 2026-08-27

- [x] `project.mcap/` directory format (`project.json`, `poses/raw/`, `poses/canonical/`)
- [x] Save / load raw (L0, `PersonTrack.raw_frames`) and canonical (L1) pose data
- [x] `schema_version` on every file; `ProjectVersionError` for newer versions
- [x] Recover a project after a crash: `File > Open Project` restores the analysis without re-running it

## Phase 9 — Manual Correction  ✅ done 2026-08-27

- [x] Select a keypoint (click on `VideoView`) — `set_editable`, `keypoint_selected`
- [x] Move a keypoint (drag); stored in the sparse `CorrectionLayer` (non-destructive)
- [x] Effective pose = detection ⊕ corrections, computed on demand (`effective_pose`)
- [x] Propagate / interpolate a correction across its keyframe span
- [x] Undo / redo via `app.core.commands` (Ctrl+Z / Ctrl+Y)
- [x] Save corrections to `corrections/<track_id>.json`

## Phase 10 — Canonical Skeleton  ✅ done 2026-08-27

- [x] Canonical joint set finalised (18 joints incl. pelvis/chest/neck/feet); schema `canonical_v2`
- [x] Bone hierarchy + T-pose rest pose (`CANONICAL_SKELETON`, 17 bones, parent-first)
- [x] `app.skeleton.solver`: 2D-constrained skeleton — bone rotations (local quaternions) + root;
      `app.math` created (`vectors`, `rotations` via SciPy, `coordinates`). Real 3D = Phase 15.
- [x] `app.skeleton.validation`: structural check + per-bone length-stability report
- [x] Tests: `shortest_arc` maths, bent-forearm → quarter turn, missing-joint → identity
- [x] Persisted to `skeleton/<track_id>.{npz,json}`; minimal "Build skeleton" UI

## Phase 11 — Animation Data Export  ✅ done 2026-08-27

- [x] Interchange format spec: [`docs/formats/mcapclip_v1.md`](formats/mcapclip_v1.md)
- [x] `app.export.animation_export`: `SkeletonClip` ⇄ `*.mcapclip.json` (canonical Y-up;
      Blender Z-up conversion is Phase 12). `AnimationExportError` on bad/newer files.
- [x] Round-trip tests (document + file); `ProjectController.export_animation`; File > Export Animation

## Phase 12 — Blender Add-on  ✅ done 2026-08-27

- [x] `blender_addon/` standalone package (`bl_info`, lazy `register`/`unregister`); imports
      only `bpy` + stdlib, never `app/`. Zip the folder to install in Blender.
- [x] `blender_addon/mcapclip.py` parses `*.mcapclip.json` (stdlib only); `McapClipError`
- [x] `blender_addon/importer.py` applies rotations to same-named pose bones + keyframes
      (rest-pose compensation / proper retargeting is Phase 13)
- [x] `blender_addon/conversion.py` — explicit Y-up → Z-up (`(x,y,z)→(x,-z,y)` + quaternion
      conjugation), a separate implementation from `app/math/coordinates.py` by design
- [x] Tests: pure modules only (parse a file the app exported, conversion consistency,
      architecture rules); the `bpy` layer is verified in Blender by hand

## Phase 13 — Rig Retargeting  ✅ done 2026-08-27

- [x] `Rig` / `RetargetMap` models + `app.retarget.rig_registry` (one JSON per profile)
- [x] Bundled profiles: `canonical`, `mixamo`, `rigify`, `unity_humanoid`
- [x] `app.retarget.retargeter.retarget`: `SkeletonClip` + `Rig` + `RetargetMap` → `RigClip`
      (`offset · canonical_local` per mapped bone; root × `unit_scale`)
- [x] Custom profiles: `build_rig_registry(*extra_dirs)` scans extra folders (a JSON dropped
      in works). A Blender armature-profile generator is a later nicety.
- [x] "Preview" = `RigPanel` coverage report (N/M bones mapped, unmapped list) — no 3D view
- [x] Export embeds the rig's `bone_map` in the mcapclip; the add-on applies it. Persisted
      to `animation/<rig_id>.{npz,json}`.
- [x] Tests: canonical rotation → same rotation on the mapped rig bone; offset; unit scale

## Phase 14 — Animation Processing  ✅ done 2026-08-27

- [x] Smoothing — `scipy.signal.savgol_filter` (or moving average) per joint trajectory
- [x] Jitter removal — median filter (`scipy.signal.medfilt`) spike rejection
- [x] Interpolate missing frames — linear per joint, gaps up to `max_gap`, marked conf 0.5
- [x] Foot-locking — pin ankle+foot to the median over near-stationary runs
- [x] Each pass is an opt-in flag in `ProcessingOptions`; `process_sequence` bakes corrections
      in and feeds the result to the skeleton solver. Transient (re-run, not persisted).
      One-Euro is a streaming filter — savgol covers the batch case; noted for later.

## Phase 15 — 3D Reconstruction Backend  ✅ done 2026-08-27

- [x] `ReconstructionBackend` ABC + `motion_capture.reconstruction` entry-point group
- [x] `MediaPipeWorldReconstruction` — lifts stored MediaPipe world landmarks to canonical 3D
      (no extra deps); a monocular-lift model can slot in behind the same interface later
- [x] Output track is `CANONICAL_WORLD`; `PersonTrack.space`, and the solver / bone-length
      report branch on it (no y-flip for 3D). The overlay stays 2D.
- [x] `app.reconstruct.validation` — limb-length stability + left/right symmetry
- [x] Rest of the pipeline unchanged: processing, skeleton solve, retarget, export all
      work on the 3D track

## Phase 16 — BVH Export  ✅ done 2026-08-27

- [x] `app.export.bvh_exporter`: canonical `SkeletonClip` → `.bvh` (HIERARCHY from the
      canonical skeleton, OFFSETs from measured `bone_lengths`, MOTION as `Z Y X` Euler degrees)
- [x] Native import path — Blender / Maya / MotionBuilder read BVH directly, no add-on
- [x] `ProjectController.export_bvh`; File > Export BVH; both BVH and CANONICAL_WORLD are
      Y-up so no axis conversion is needed

## Phase 17 — Performance & Concurrency  ✅ done 2026-08-27

- [x] `FrameReader` sequential fast path (no seek for in-order reads) + `app.video.frame_stream`
      — a background decode thread with a bounded buffer, used during playback behind
      `advance_playback` (its own `FrameReader`; torn down on pause/seek)
- [x] `app.pose.analysis.analyze_video_parallel` — the frame range is split over
      `min(4, cpu_count)` threads, each with its own reader + detector; merged into one track.
      Runs inside the existing `Task`; progress + cancel unchanged.
- [x] GPU: `DetectorCapabilities.gpu`; `MediaPipeDetector(use_gpu=...)` → GPU delegate
      (`registry.create("mediapipe", use_gpu=True)`). No UI toggle (platform-dependent).
- [x] Memory: `FrameReader` / `FrameStream` stream frames — the full video is never held.

---

## Post-roadmap

### UI redesign  ✅ done 2026-08-28

- [x] Two-pane `QSplitter`: video + timeline on the left, a scrollable column of
      numbered `PipelineSection` cards on the right.
- [x] Dark theme (`app/ui/theme.py`, one Qt style sheet).
- [x] Timeline scrub slider (`Timeline.scrubber`); space bar toggles play / pause.
- [x] Step gating: each step's action button is enabled only once its inputs exist
      (`MainWindow._update_pipeline_state`); the next required step's card is highlighted.
- [x] Transient messages moved to the `QMainWindow` status bar; the video summary is
      a one-line header (`format_video_line`) with the full details as a tooltip.

### Custom rig profiles  ✅ done 2026-08-28

Retarget onto a rig the app was not shipped with. Format spec:
[`formats/rig_profile_v1.md`](formats/rig_profile_v1.md).

- [x] `RigRegistry` gained `reload` / `install_profile` / `remove_profile` / `document`
      / `is_bundled` / `unique_rig_id`, plus `user_rig_dir()` (`~/.ai-motion-capture/rigs/`).
      Scan order bundled → user → project; a bundled id can be neither overwritten nor removed.
- [x] `app/retarget/armature_import.py` — reads the add-on's armature dump and guesses the
      `bone_map` (`auto_map`: 15/17 on Mixamo, Rigify and Unreal naming; hands/fingers/toes
      skipped; unmatched roles left empty rather than guessed).
- [x] `CustomRigDialog` — review/edit the 17 canonical rows, name, unit scale, up axis, with a
      live coverage count. Reached from `RigPanel` via "Import rig..." (from a file) and
      "New rig..." (type the names); "Remove" deletes a custom profile.
- [x] Blender add-on `File > Export > AI Mocap Rig` (`armature_export.py` + the stdlib-only
      `armature_dump.py`); add-on version 1.1.0. The `bpy` layer is verified in Blender by hand.
- [x] Persistence: `save_project` copies the active **custom** profile into
      `<project>.mcap/rigs/`, so the project retargets on a machine whose user directory is
      empty. Built-in profiles are not copied.
- [x] The canonical skeleton is untouched — a custom rig is a new target, not a new
      internal skeleton.

### Windows fit their content  /  hips from the hierarchy  ✅ done 2026-08-28

- [x] `app/ui/sizing.py` — `fitted_height` grows a window by the shortfall between its
      scroll viewport and its content, capped to the screen it is shown on. `MainWindow`
      and `CustomRigDialog` apply it on first show, so neither scrolls on a normal display.
- [x] `ArmatureDump` keeps the bone `parents`; `auto_map(bone_names, parents)` places the
      hips structurally (parent of the upper leg), guarded so a pelvis shared by both
      thighs is never mapped to a side. A real 56-bone Rigify-style metarig goes from
      15/17 to **17/17**, including a `plevis.L` misspelling no name rule could match.
- [x] `CustomRigDialog` accounts for every armature bone: N of M unmapped, listed in the
      label with the full set in a tooltip. Nothing is silently dropped.

### Rig-aware import: bone chains and attachment points  ✅ done 2026-08-28

The rig drives the **UI and the reporting**, not the capture — the canonical
skeleton and the detector are untouched, so keypoints still never depend on a rig's
bone names (`CLAUDE.md`, ADR 3).

- [x] `detect_bone_groups` folds unmapped bones into the chains they form, stopping at
      the next mapped bone; a root with 3+ child chains is classified as `fingers`.
      Bones above the mapped skeleton are left ungrouped.
- [x] `attachment_points` in the rig profile (`{slot: rig bone}`, slots not validated so a
      later backend can add its own). `Rig.attachment_points` + `attachment_point(slot)`.
- [x] `CustomRigDialog` shows one "Attachment points" row per finger group instead of
      thirty finger rows, and summarises the rest by chain
      ("39 of 56 keep their rest pose - 5 chain(s): hand.L (16), ...").
- [x] `retarget_issues(clip, map, rig)` now separates two different gaps: canonical bones
      the rig lacks, and attachment points **no capture backend drives yet**.
- [x] Second hip guard: the armature root can never be a hip (a one-legged rig used to
      slip past the shared-parent check).
- [x] Deliberately **not** done: driving the fingers. That needs a `HolisticLandmarker`
      backend plus finger bones in the canonical skeleton (17 → ~47), which would touch the
      solver, mcapclip, BVH export and every rig profile. MediaPipe 1.0.1 does ship
      `HolisticLandmarker` / `HandLandmarker`, so the path is open when wanted.
