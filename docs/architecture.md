# Architecture

> Reference plan for the AI Motion Capture desktop application.
> Validated by the project owner on 2026-08-27 (see [§13, Architecture Decisions](#13-architecture-decisions-adr)).
> This document is the **target**. Implementation is incremental and phase-gated by
> [`roadmap.md`](roadmap.md); a module described here is only built when its phase is reached.

See also: [`data_model.md`](data_model.md) for the detailed data representations and on-disk schemas.

---

## 1. Purpose & Scope

The application converts human movement in a video into skeletal animation that can be
imported into Blender. The pipeline is:

```
Video
  → Video Processing
  → Pose Detection            (interchangeable AI backend)
  → Pose Data                 (2D or 3D coordinates, one or more person tracks)
  → Canonical Skeleton        (rig-independent, hierarchical)
  → [Future] 3D Reconstruction (interchangeable backend)
  → Animation Processing
  → Rig Retargeting           (data-driven rig profiles)
  → Animation Export
  → Blender Add-on
```

---

## 2. Guiding Principles

- **Lightweight hexagonal architecture.** A pure-Python domain (data + algorithms) with no
  Qt, no heavy OpenCV logic, and no Blender. Technical concerns (UI, AI backends, Blender)
  are adapters around that core.
- **Intermediate representations.** `AI keypoints → canonical human skeleton → target rig
  mapping`. Nothing above the detector depends on a specific AI model; nothing below the
  canonical skeleton depends on a specific rig's bone names.
- **Interchangeable backends from day one.** AI pose detection and (later) 3D reconstruction
  are plugins behind stable interfaces. Swapping them must not require touching the rest of
  the application. The plugin system is designed now; it is not coded until its phase.
- **Rig independence.** The application never hard-codes a particular rig's bone names.
  Rigs are described by data profiles.
- **The UI never blocks — and starts simple.** The MVP may run operations synchronously
  where the pause is acceptable. The architecture reserves clean seams so threading,
  frame buffering, and background decoding can be added later without a redesign.
- **Explicit everything.** Explicit error types, explicit coordinate conversions, explicit
  schema versions. No silent data-format or coordinate changes.
- **Incremental.** One feature at a time. No unrequested features. No placeholder
  implementations unless explicitly requested.

---

## 3. Layered Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  UI LAYER            app.ui                                           │
│  PySide6 widgets + view models. Talks to the core via signals and    │
│  view models only. Never imports cv2 / mediapipe / torch / bpy.      │
└───────────────────────────────▲──────────────────────────────────────┘
                                │  view models, Qt signals, commands
┌───────────────────────────────┴──────────────────────────────────────┐
│  ORCHESTRATION LAYER   app.core                                       │
│  AppContext (dependency container), Project, Pipeline, TaskManager,   │
│  undo/redo stack, settings, project I/O.                             │
│  The only place that knows the order of the pipeline.               │
└───────────────────────────────▲──────────────────────────────────────┘
                                │  plain function / class calls
┌───────────────────────────────┴──────────────────────────────────────┐
│  DOMAIN LAYER   — pure Python, unit-testable without a UI            │
│                                                                      │
│  app.math      general math: vectors, rotations, filters,           │
│                interpolation, coordinate-space conversions           │
│  app.data      domain models: RawPose, PoseFrame, PersonTrack,       │
│                PoseSequence, CorrectionLayer, CanonicalSkeleton,     │
│                SkeletonClip, Rig, RetargetMap, RigClip               │
│  app.video     decoding, frame access, simple playback controller    │
│  app.pose      detector interface + registry + keypoint mapping      │
│  app.skeleton  canonical-skeleton solver + validation                │
│  app.retarget  canonical skeleton → target rig                       │
│  app.animation signal processing on animation curves                 │
│  app.export    serializers: project, animation interchange, BVH      │
│  app.plugins   generic backend registry + discovery                  │
└──────────────▲───────────────────────────────────▲──────────────────┘
               │ interfaces (ABC) + lazy imports    │  file-based only
┌──────────────┴──────────────────┐  ┌──────────────┴──────────────────┐
│  AI BACKENDS (optional installs)│  │  BLENDER ADD-ON                 │
│  app.pose.backends.*            │  │  blender_addon/  (separate pkg) │
│  mediapipe / onnx / mmpose /... │  │  imports only `bpy`.           │
│  heavy deps behind extras       │  │  never imports app/.           │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

---

## 4. Dependency Rules

These are enforced by convention and by a dedicated architecture test (see §12).

| Module            | May import                                                                 | Must **never** import                                        |
|-------------------|---------------------------------------------------------------------------|-------------------------------------------------------------|
| `app.ui`          | `app.core`, `app.data`, PySide6                                          | `cv2`, `mediapipe`, `torch`, `app.pose.backends.*`, `bpy`  |
| `app.core`        | `app.data`, `app.math`, `app.video`, `app.pose`, `app.skeleton`, `app.retarget`, `app.animation`, `app.export`, `app.plugins` | `PySide6`, `bpy`                                            |
| `app.math`        | `numpy`, `scipy`                                                         | Qt, `cv2`, AI libs, `bpy`, `app.data`                      |
| `app.data`        | `numpy`, `app.math`                                                     | Qt, `cv2`, AI libs, `bpy`                                  |
| `app.video`       | `numpy`, `cv2`, `app.data`                                              | Qt, AI libs, `bpy`                                         |
| `app.pose`        | `app.data`, `app.math`, `app.plugins`, `numpy`                         | Qt, `bpy`, concrete AI libs (only `backends.*` may)        |
| `app.pose.backends.*` | its own AI lib (lazy import), `app.data`, `app.pose`                | Qt, `bpy`                                                  |
| `app.skeleton`    | `app.data`, `app.math`                                                 | Qt, `cv2`, AI libs, `bpy`                                  |
| `app.retarget`    | `app.data`, `app.math`                                                 | Qt, `cv2`, AI libs, **`bpy`**                              |
| `app.animation`   | `app.data`, `app.math`, `scipy`                                        | Qt, `cv2`, AI libs, `bpy`                                  |
| `app.export`      | `app.data`, `app.math`                                                 | Qt, `cv2`, AI libs, **`bpy`**                              |
| `blender_addon`   | `bpy`, Python stdlib                                                    | anything under `app/`                                      |

**Rationale for the AI / Blender bans:** the AI system must be swappable without touching
the core, and Blender-specific code must never leak into the application (both are explicit
rules in `CLAUDE.md`).

---

## 5. Module Map

The current code (`app/main.py`, `app/ui/`, `app/video/video_loader.py`, `app/models/`,
`app/pose/detector_base.py`, `app/core/project.py`) evolves into this layout. Nothing is
thrown away; `app/models/` is renamed to `app/data/`.

```
app/
  main.py                       # entry point (exists)

  core/
    app_context.py              # dependency container: settings + registries + task manager
    project.py                  # MotionCaptureProject (extends the existing dataclass)
    project_io.py               # load/save project.mcap, schema versioning + migrations
    settings.py                 # settings dataclasses, loaded from a user TOML
    tasks.py                    # Task / TaskManager: progress + cancellation abstraction
    pipeline.py                 # orchestrates video → pose → skeleton → retarget → export
    commands.py                 # undo/redo stack (Command pattern)

  math/                         # general mathematics — NO domain types live here
    vectors.py                  # vector helpers on top of numpy
    rotations.py                # quaternions, SLERP, euler<->quat (scipy Rotation)
    filters.py                  # One-Euro, Savitzky-Golay, Butterworth (scipy.signal)
    interpolation.py            # linear / cubic / SLERP curve interpolation
    coordinates.py              # named, explicit coordinate-space conversions

  data/                         # domain models — pure, immutable-by-default, no Qt/Blender
    keypoints.py                # KeypointSchema, RawPose                       (Level 0)
    pose.py                     # Keypoint, PoseFrame, PersonTrack, PoseSequence (Level 1)
    corrections.py              # CorrectionLayer (sparse, non-destructive edits)
    skeleton.py                 # CanonicalSkeleton, BoneDefinition, SkeletonPose,
    #                             SkeletonClip                                   (Level 2)
    rig.py                      # Rig (target armature profile), RetargetMap
    animation.py                # RigClip, animation curves                      (Level 3)

  video/
    video_loader.py             # metadata extraction (exists)
    frame_reader.py             # sequential + random access to frames
    playback.py                 # PlaybackController — simple/synchronous for the MVP,
    #                             seams reserved for threading + buffering later

  pose/
    detector_base.py            # PoseDetector ABC (exists — evolves to emit Level 0)
    capabilities.py             # DetectorCapabilities: 2d/3d, multi-person, gpu, keypoint count
    registry.py                 # pose-backend registry built on app.plugins
    mapping.py                  # KeypointMapping: native schema → canonical joints
    backends/
      __init__.py
      mediapipe_detector.py     # optional install (extra "mediapipe")
      # onnx_detector.py, mmpose_detector.py, ...

  plugins/                      # generic extension infrastructure
    types.py                    # BackendMetadata, BackendAvailability
    registry.py                 # BackendRegistry: manual + entry-point discovery,
    #                             records unavailable backends with a reason string

  skeleton/
    solver.py                   # PoseSequence (L1) → SkeletonClip (L2): joint angles / IK
    validation.py               # bone-length consistency, connectivity checks

  retarget/
    retargeter.py               # SkeletonClip + Rig + RetargetMap → RigClip (L3)
    rig_registry.py             # discovers rig profiles (bundled + user + project dirs),
    #                             installs / removes user profiles
    armature_import.py          # armature dump -> guessed canonical->rig bone mapping
    rig_profiles/               # bundled data profiles (JSON)
      canonical.json
      mixamo.json
      rigify.json
      unity_humanoid.json

  animation/
    processing.py               # smoothing, jitter removal, gap interpolation, foot-lock

  export/
    project_export.py           # write/read the project.mcap directory
    animation_export.py         # canonical-skeleton animation → interchange file (.mcapclip.json)
    blender_json_exporter.py    # applies the coordinate conversion at the Blender boundary
    bvh_exporter.py             # SkeletonClip -> .bvh (Phase 16)

  ui/
    main_window.py              # window shell: video/timeline splitter + pipeline sidebar,
    #                             menu, shortcuts, step gating, status bar
    theme.py                    # the dark Qt style sheet + apply_dark_theme()
    sizing.py                   # size a window to its content, capped to the screen
    formatting.py               # domain objects -> display strings
    widgets/
      video_view.py             # frame display, aspect ratio, editable keypoint overlay
      timeline.py               # scrub slider, play/pause/stop, step, frame readout
      pipeline_section.py       # numbered, state-aware card wrapping one step's panel
      custom_rig_dialog.py      # review/edit a custom rig's canonical->rig bone mapping
      detector_panel.py         # choose AI backend, detect frame / analyze video
      correction_panel.py       # edit toggle, undo/redo, propagate/clear
      reconstruction_panel.py   # choose a 3D backend + run it
      processing_panel.py       # opt-in cleanup passes
      skeleton_panel.py         # build the canonical skeleton
      rig_panel.py              # choose rig profile + review mapping coverage

blender_addon/                  # standalone Blender add-on — NEVER imported by app/
  __init__.py                   # bl_info, register / unregister
  importer.py                   # read .mcapclip.json, keyframe a target armature
  armature_export.py            # optional: dump an armature's metadata -> rig profile JSON

tests/                          # mirrors app/, priority on data / math / mapping / solver / retarget / export
docs/
  architecture.md               # this file
  data_model.md                 # data representations + on-disk schemas
  roadmap.md                    # phased plan
  formats/                      # written when the corresponding phase is reached
    mcapclip_v1.md              # Blender interchange format spec (Phase 11)
```

---

## 6. Module Responsibilities

| Module          | Responsibility                                                                                   | Knows about                            |
|-----------------|------------------------------------------------------------------------------------------------|----------------------------------------|
| `app.ui`        | Windows, widgets, view models, user interaction. No processing logic.                          | `app.core`, `app.data`                 |
| `app.core`      | Application state, project lifecycle, pipeline order, background tasks, undo/redo, settings.    | the whole domain layer                 |
| `app.math`      | Reusable mathematics: vectors, quaternions (`Quaternion`, `shortest_arc`, SciPy-backed), explicit coordinate-space conversions. *(implemented Phase 10)* | numpy, scipy, `app.models.pose` (for `Vector3`) |
| `app.data`      | Data structures for every pipeline level (L0–L3), plus the correction layer. No algorithms beyond trivial accessors. | numpy, `app.math`      |
| `app.video`     | Open videos, read metadata, read frames (sequential + random), drive playback.                 | `cv2`, `app.data`                      |
| `app.pose`      | The detector interface, backend registry, and native→canonical keypoint mapping.               | `app.data`, `app.plugins`              |
| `app.pose.backends` | Concrete detectors adapting a specific AI library to the `PoseDetector` interface.          | one AI library each                    |
| `app.plugins`   | Generic registry: register backends manually or via entry points; report availability.         | Python stdlib                          |
| `app.skeleton`  | Turn canonical keypoint sequences into a hierarchical skeleton clip (bone rotations).          | `app.data`, `app.math`                 |
| `app.retarget`  | Map a canonical skeleton clip onto a target rig using a data-driven profile + mapping.          | `app.data`, `app.math`                 |
| `app.animation` | *(Phase 14)* Opt-in cleanup passes on an L1 pose sequence: gap fill (linear), despike (median), smooth (savgol / moving average), foot-lock. `process_sequence` bakes corrections in and returns a new `PoseSequence`; transient (not persisted). | `app.data`, `app.math`, `scipy` |
| `app.export`    | Produce interchange files from a `SkeletonClip`: `animation_export` (`mcapclip` v1, canonical Y-up, optional `bone_map`) and `bvh_exporter` (`.bvh`, native import, no add-on). *(Phases 11, 16)* | `app.data`, `app.math`, `scipy` |
| `blender_addon` | Read an interchange file and apply it to a Blender armature. Fully separate program.            | `bpy` only                             |

---

## 7. Extension System (Plugins / Backends)

Two extension points are first-class citizens: **AI pose detection** and (later) **3D
reconstruction**. **Rig support** is an extension point too, but rigs are *data*, not code.

> **Status (Phase 15):** both extension points are live. Pose detection: `app.plugins.BackendRegistry`,
> `PoseDetector` → `RawPose`, `app.pose.mapping`, MediaPipe backend. 3D reconstruction:
> `app.reconstruct.ReconstructionBackend` + `build_reconstruction_registry()` (group
> `motion_capture.reconstruction`), with a `MediaPipeWorldReconstruction` backend that lifts
> stored world landmarks to a `CANONICAL_WORLD` track.
>
> **Status (Phase 6):** `app.plugins.BackendRegistry`, the `PoseDetector` → `RawPose`
> interface, `app.pose.mapping`, and the MediaPipe backend are implemented.
> `KeypointSchema` / `RawPose` currently live in `app/models/` (they move to `app/data/`
> at the rename). MediaPipe 1.0 dropped the `solutions` API, so the backend uses the
> Tasks `PoseLandmarker`, which needs a `.task` model file downloaded via
> `python -m app.pose.backends.mediapipe_model` (stored in `models/`, outside the app package).

### 7.1 Code backends — `app.plugins`

`BackendRegistry` maps a string id to a `BackendEntry(factory, metadata, availability)`:

- **Built-in backends** register themselves explicitly at import time.
- **Third-party backends** are discovered through Python entry points, so an external
  package can add a detector without modifying this repository:
  - group `motion_capture.pose_backends` → `PoseDetector` factories
  - group `motion_capture.reconstruction` → 3D reconstruction factories (future)
- **Availability.** When a backend's dependencies fail to import, the registry keeps the
  entry but marks it `available = False` with a human-readable reason
  (`"mediapipe is not installed — run: uv sync --extra mediapipe"`). The UI lists
  unavailable backends greyed out with that reason. The core never crashes because an
  optional backend is missing.

### 7.2 The `PoseDetector` interface (evolution of the current ABC)

The existing `app/pose/detector_base.py` returns a canonical `PoseFrame` directly. It
evolves so the detector emits its **native** keypoints (Level 0) and a separate,
model-independent mapping converts to canonical (Level 1):

| Member                              | Purpose                                                                 |
|-------------------------------------|------------------------------------------------------------------------|
| `schema: KeypointSchema`            | which keypoint set this detector produces (e.g. MediaPipe 33, COCO 17) |
| `capabilities: DetectorCapabilities`| 2D/3D, multi-person, GPU support, keypoint count                        |
| `detect(frame, index, timestamp) -> RawPose \| None` | single-frame detection (Level 0)                       |
| `detect_batch(frames) -> Iterable[RawPose \| None]`  | batch hook; default loops over `detect`               |
| `close()`                           | release model resources                                                |

`app.pose.mapping` holds one `KeypointMapping` per source schema → canonical joints. The
pipeline runs: `detector.detect → RawPose → KeypointMapping → PoseFrame`. Adding a detector
means: one file in `backends/`, one `KeypointSchema` if new, one `KeypointMapping`, one
registration line. Nothing else changes.

### 7.3 Rig profiles — data, discovered not coded

A `Rig` describes a target armature: bone names, hierarchy, rest orientation, up/forward
axes, unit scale. A `RetargetMap` maps **canonical bone → rig bone(s)** with per-bone
rotation offsets and axis remaps. Both are JSON files discovered from:

1. bundled `app/retarget/rig_profiles/` (canonical, Mixamo, Rigify, Unity Humanoid),
2. the user profile directory `~/.ai-motion-capture/rigs/`,
3. the current `project.mcap/rigs/` (the copy that keeps a project portable),

scanned in that order, a later directory winning for the same `rig_id`. A profile is
authored by hand, typed into `CustomRigDialog`, or derived from an armature exported by
`blender_addon/armature_export.py` and auto-mapped by `app/retarget/armature_import.py`.

Supporting a new rig is a data task: drop in a profile + a mapping. **No code path ever
references a specific rig's bone names.** Format: [`formats/rig_profile_v1.md`](formats/rig_profile_v1.md).

---

## 8. Concurrency & Performance Strategy

Simple by default; concurrency added at known seams. Phase 17 filled several of these in.

| Concern                         | Now                                                       | Further room                                                        |
|---------------------------------|----------------------------------------------------------|--------------------------------------------------------------------|
| Video playback                  | `PlaybackController` (Qt-free) holds play/pause state; during playback `ProjectController` runs an `app.video.frame_stream.FrameStream` — a background decode thread + bounded queue with its own `FrameReader` — and `advance_playback` pops from it. Falls back to on-demand read. *(Phase 17)* | tune buffer size; decode-ahead during scrubbing |
| Frame-by-frame navigation       | random-access `FrameReader` with a **sequential fast path** (no container seek for in-order reads) *(Phase 17)* | a decoded-frame LRU cache for back-and-forth |
| Full-video analysis (detection) | `analyze_video_parallel` splits the frame range over `min(4, cpu_count)` threads (each its own `FrameReader` + detector), merged into one track; runs inside the `Task`. Sequential `analyze_video` kept. *(Phase 17)* | `ProcessPoolExecutor` for pure-Python detectors |
| Retargeting / processing / export | same `TaskManager`                                     | unchanged                                                          |
| GPU acceleration                | `DetectorCapabilities.gpu`; `MediaPipeDetector(use_gpu=...)` selects the GPU delegate — reachable via `registry.create("mediapipe", use_gpu=True)`. No UI toggle. *(Phase 17)* | expose per-backend GPU choice in the detector panel |

`app.core.tasks` is **Qt-free**: `TaskManager.submit(job, on_progress, on_done)` runs `job`
on a thread pool and invokes the callbacks *from the worker thread*; the UI marshals them
onto its thread by emitting Qt signals (`MainWindow._analysis_progress/_finished`).
`CancelToken` is a cooperative flag; jobs check it between units of work. The UI stays
responsive. This is the single place where the executor strategy can change.

---

## 9. Coordinate Systems

| Space                 | Handedness / up | Units    | Used by                                    |
|-----------------------|-----------------|----------|--------------------------------------------|
| `IMAGE_PIXELS`        | 2D, origin top-left, y-down | pixels | raw 2D detections, on-screen overlay        |
| `IMAGE_NORMALIZED`    | 2D, 0..1        | fraction | some detectors (e.g. MediaPipe image landmarks) |
| `CANONICAL_WORLD`     | **right-handed, Y-up** | metres (approx.) | canonical keypoints (3D), skeleton clip, retargeting |
| `BLENDER_WORLD`       | right-handed, **Z-up** | metres | **only** at the export boundary and inside the add-on |

Rules:

- Internal 3D data is always `CANONICAL_WORLD` (right-handed, Y-up).
- The **only** conversion to `BLENDER_WORLD` happens in `app.export.blender_json_exporter`
  (and mirrored in `blender_addon/importer.py`), by calling a **named** function in
  `app.math.coordinates` (e.g. `canonical_to_blender(...)`).
- Every `PersonTrack` and every serialized clip records its `CoordinateSpace` explicitly.
- **No module silently converts coordinates.** A function that changes space is named for
  it and documented.

---

## 10. Blender Integration Boundary

- `blender_addon/` is a **separate Python package** with its own `bl_info`. It imports only
  `bpy` and the Python standard library. It never imports anything under `app/`.
- The application never imports `bpy`.
- Communication is **strictly file-based**: the app writes an interchange file
  (`*.mcapclip.json`, spec in `docs/formats/mcapclip_v1.md`); the add-on reads it and
  inserts keyframes on an armature the user selects.
  *(Phase 12: `blender_addon/` implemented. Pure modules `mcapclip.py` / `conversion.py`
  are stdlib-only and unit-tested; `importer.py` / `ui.py` need Blender. The Y-up → Z-up
  conversion is a separate implementation from `app/math/coordinates.py`, by design.)*
- Export order of formats (validated):
  1. stable internal project format,
  2. animation-data interchange file,
  3. Blender add-on that imports it,
  4. retargeting onto a selected rig,
  5. BVH as a **secondary** export later.

---

## 11. Project Format

During development the project is a **directory**, not an archive (better for debugging,
large files, and recovery):

```
project.mcap/
  project.json        # schema_version, name, timestamps, source video ref, settings,
  #                     active person, selected detector backend id + config
  video/              # optional local copy / thumbnail; project.json may reference an external path
  poses/              # raw (L0) and canonical (L1) pose data — see data_model.md
  corrections/        # sparse, non-destructive CorrectionLayer per track set
  cache/              # regenerable artifacts (decoded frames, previews); safe to delete
```

`skeleton/`, `animation/`, and `export/` subdirectories are added by their phases. Every
JSON file carries a `schema_version`; `app.core.project_io` owns explicit migration
functions and refuses to load an unknown newer version. A single-file archive format for
sharing may be added later.

Full layout and file schemas: [`data_model.md` §9](data_model.md).

---

## 12. Testing & Quality

| Test target                                   | Priority | Why                                            |
|-----------------------------------------------|----------|------------------------------------------------|
| `app.math.*`                                  | high     | required by `CLAUDE.md`; foundation of everything |
| `app.pose.mapping` (native → canonical)       | high     | guarantees detectors are interchangeable       |
| `app.skeleton.solver` (keypoints → bone angles) | high   | critical maths, missing-joint edge cases       |
| `app.retarget.retargeter`                     | high     | rotation correctness on reference rigs         |
| `app.export.*`                                | medium   | round-trip tests (write → read → compare)      |
| `app.video`                                   | medium   | against a tiny fixture video                   |
| architecture test                             | medium   | asserts the §4 dependency rules (e.g. `app.ui` never imports `cv2`) |
| `app.ui`                                      | low      | headless smoke tests (`QT_QPA_PLATFORM=offscreen`) — already in place |

Commands are unchanged: `uv run pytest`, `uv run ruff check .`,
`uv run python -m app.main`.

---

## 13. Architecture Decisions (ADR)

Validated by the project owner on 2026-08-27.

| #  | Decision | Consequence for the architecture |
|----|----------|----------------------------------|
| 1  | **3D-ready, 2D-first.** The MVP pipeline is mostly 2D. MediaPipe pseudo-3D / depth may be stored and tested early but is not the final 3D solution. Real 3D reconstruction is an interchangeable backend. | `Keypoint` stores optional `z`; `PersonTrack` records `2d`/`3d` and a `depth_source` tag. 3D reconstruction is a plugin group; the architecture does not depend on MediaPipe. |
| 2  | **Export priority:** internal format → animation-data export → Blender add-on → retargeting → BVH later. | Roadmap reordered. BVH exporter is a late, secondary module. Flexibility and custom-rig support come first. |
| 3  | **Rig priority:** internal canonical skeleton → Mixamo → Rigify → Unity Humanoid → custom Blender rigs. Never depend on a rig's bone names. | Bundled rig profiles in that order. `RetargetMap` indirection is mandatory; no bone name literals in code. |
| 4  | **Multi-person data, single-person UI (v1).** | `PoseSequence` contains `PersonTrack[1..N]` from the start. The MVP UI operates on one active track. |
| 5  | **Optional AI dependencies.** Core runs without MediaPipe / PyTorch / MMPose. Backends install separately. The app detects a missing backend clearly. | Heavy deps are `uv` extras. `BackendRegistry` reports availability + reason. Core imports zero AI libraries. |
| 6  | **Rename `app.models` → `app.data`. Keep maths separate in top-level `app.math`** (not `app.data.math`). | Two distinct packages: `app.data` (domain types), `app.math` (general functions). |
| 7  | **OpenCV-based `PlaybackController`, simple first.** No multi-thread/buffer architecture yet; only reserve the seam. | §8. MVP playback is synchronous/on-demand behind an interface that a threaded implementation can later replace. |
| 8  | **Canonical coordinates: right-handed, Y-up.** Convert to Blender Z-up only at the export boundary, explicitly and documented. | §9. All conversions are named functions in `app.math.coordinates`; every track/clip records its space. |
| 9  | **Project is a directory (`project.mcap/`) during development.** Archive format later. | §11. `app.core.project_io` reads/writes the directory; schema-versioned JSON. |
| 10 | **SciPy is a core dependency.** For interpolation, smoothing, rotation maths, signal processing. | `app.math` and `app.animation` build on `scipy`. Added to `pyproject.toml` core deps. |
| 11 | **Plugin/backend system designed up front, coded later.** | `app.plugins` package + entry-point groups defined here; implemented in Phase 6 (detectors) and Phase 15 (3D). |

---

## 14. Dependencies

```
[project] dependencies      = numpy, scipy, opencv-contrib-python, PySide6
[project.optional-dependencies]
  mediapipe = ["mediapipe>=1.0"]   # first 2D detection backend (Tasks API + model file)
  onnx      = ["onnxruntime"]      # ONNX-based detectors (future)
  torch     = ["torch"]            # advanced models / future 3D
[dependency-groups] dev     = pytest, ruff
```

The core never imports an optional dependency. `uv sync --extra mediapipe` enables the
first detector backend; then `python -m app.pose.backends.mediapipe_model` fetches its
model. `opencv-contrib-python` (a superset of `opencv-python`) is used because MediaPipe
depends on it — avoids two conflicting `cv2` installs.
