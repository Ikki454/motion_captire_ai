# Data Model

> Companion to [`architecture.md`](architecture.md). Describes the data representations at
> every pipeline level, the non-destructive editing model, coordinate conventions, and the
> on-disk `project.mcap/` schemas.
> Validated by the project owner on 2026-08-27.

This document is a specification. The dataclasses below are only implemented when their
phase in [`roadmap.md`](roadmap.md) is reached. Field lists are conceptual; exact names may
be refined during implementation, but any change to a **serialized** schema bumps its
`schema_version`.

---

## 1. Overview — Four Levels

```
L0  RawPose          detector-native keypoints (33 MediaPipe, 17 COCO, ...), 2D or pseudo-3D
      │                                        │ app.pose.mapping (KeypointMapping)
      ▼
L1  PoseFrame        canonical joint set, 2D or 3D positions + confidence
    PersonTrack        one person's L1 sequence over time
    PoseSequence        all tracks for a video
      │  + CorrectionLayer (sparse, non-destructive)   → effective pose (computed)
      │                                        │ app.skeleton.solver
      ▼
L2  SkeletonPose     canonical bone hierarchy: rotations (quaternion) + root translation
    SkeletonClip       a SkeletonPose sequence + bone lengths + fps        (rig-independent)
      │  + Rig + RetargetMap                   │ app.retarget.retargeter
      ▼
L3  RigClip          per-bone rotation curves named for the TARGET rig + root motion
      │                                        │ app.export
      ▼
    *.mcapclip.json  interchange file  →  blender_addon/importer.py
```

Each arrow is a stable, versioned boundary:

- **L0 → L1** is the *AI ↔ application* boundary. A new detector = new backend + new
  `KeypointMapping`. Nothing above L1 changes.
- **L2 → L3** is the *application ↔ rig* boundary. A new rig = new `Rig` profile + new
  `RetargetMap`. No code changes.

---

## 2. Coordinate Spaces

See [`architecture.md` §9](architecture.md). Summary:

| `CoordinateSpace`   | Dimensions | Origin / up            | Units    |
|---------------------|-----------|------------------------|----------|
| `IMAGE_PIXELS`      | 2D        | top-left, y-down       | pixels   |
| `IMAGE_NORMALIZED`  | 2D        | top-left, y-down       | 0..1     |
| `CANONICAL_WORLD`   | 3D        | right-handed, **Y-up** | ~metres  |
| `BLENDER_WORLD`     | 3D        | right-handed, **Z-up** | metres   |

Every `PersonTrack` and every serialized clip stores its space. Conversions are named
functions in `app.math.coordinates`; nothing converts silently.

---

## 3. Level 0 — Raw Detection

### `KeypointSchema` (`app.data.keypoints`)

Describes one keypoint set so detectors and mappings stay decoupled.

| Field          | Type                          | Notes                                             |
|----------------|-------------------------------|---------------------------------------------------|
| `id`           | `str`                         | e.g. `"mediapipe_pose_33"`, `"coco_17"`, `"canonical_v1"` |
| `names`        | `tuple[str, ...]`             | ordered keypoint identifiers                       |
| `edges`       | `tuple[tuple[int, int], ...]` | connectivity, for drawing and validation          |
| `dimensions`   | `2` or `3`                    | native output dimensionality                       |

Bundled schemas: `MEDIAPIPE_POSE_33`, `COCO_17`, `CANONICAL_V1`.

### `RawPose` (`app.data.keypoints`)

One detector output for one frame, in the detector's native schema. **Immutable once
written.**

| Field            | Type                    | Notes                                              |
|------------------|-------------------------|---------------------------------------------------|
| `schema_id`      | `str`                   | which `KeypointSchema`                             |
| `frame_index`    | `int`                   |                                                   |
| `timestamp`      | `float`                 | seconds                                            |
| `person_index`   | `int`                   | detector-local id within this frame (0 for single-person) |
| `points`         | `np.ndarray [K, 2 or 3]`| native coordinates                                 |
| `confidence`     | `np.ndarray [K]`        | 0..1 per keypoint                                  |
| `space`          | `CoordinateSpace`       | usually `IMAGE_PIXELS` or `IMAGE_NORMALIZED`       |
| `depth_source`   | `str`                   | `"none"`, `"mediapipe_world"`, `"reconstruction:<backend>"` |

`depth_source` lets us store MediaPipe world landmarks early *without* treating them as the
final 3D reconstruction (Decision 1).

---

## 4. Level 1 — Canonical Pose

### Canonical joint set (`app.data.pose.JointName`)

Current baseline (already in `app/models/pose.py`), used by Phases 6–9:

```
head
left_shoulder  right_shoulder
left_elbow     right_elbow
left_wrist     right_wrist
left_hip       right_hip
left_knee      right_knee
left_ankle     right_ankle
```

The set will grow (`pelvis`, `spine`, `chest`, `neck`, `left_foot`/`right_foot`,
optionally hands) when Phase 10 (Canonical Skeleton) needs a full hierarchy. Additions bump
`CANONICAL_V1` → `CANONICAL_V2` and require the skeleton bone definitions in
`app/models/skeleton.py` to be reconciled (its `spine`/`chest`/`neck` bones currently
reference joints that do not exist yet).

### `Keypoint` (`app.data.pose`)

| Field        | Type              | Notes                                            |
|--------------|-------------------|--------------------------------------------------|
| `x`, `y`     | `float`           | always present                                   |
| `z`          | `float \| None`   | present only for 3D / pseudo-3D tracks           |
| `confidence` | `float`           | 0..1; `0.0` means "not detected"                 |

### `PoseFrame` (`app.data.pose`)

One person, one frame, canonical joints. Extends the existing dataclass.

| Field         | Type                          | Notes                                    |
|---------------|-------------------------------|------------------------------------------|
| `frame_index` | `int`                         |                                          |
| `timestamp`   | `float`                       | seconds                                  |
| `joints`      | `dict[JointName, Keypoint]`   | **every** canonical joint is a key; missing detections have `confidence = 0.0` |

Missing joints are represented explicitly — never dropped, never silently interpolated.

### `PersonTrack` (`app.data.pose`)

One person across the whole video (Decision 4 — the structure is multi-person even though
the v1 UI drives one track).

| Field           | Type                    | Notes                                              |
|-----------------|-------------------------|---------------------------------------------------|
| `track_id`      | `str`                   | stable id (`"person_0"`, ...)                      |
| `label`         | `str`                   | user-facing name, optional                         |
| `frames`        | `dict[int, PoseFrame]`  | L1 canonical; sparse by frame index; gaps = no detection |
| `raw_frames`    | `dict[int, RawPose]`    | *(implemented)* L0 detector output, aligned with `frames`; carries `world_points` |
| `depth_source`  | `str`                   | carried from the L0 raw frames (`reconstruction:<backend>` after a 3D lift) |
| `space`         | `CoordinateSpace`       | *(implemented, Phase 15)* `IMAGE_PIXELS` for analysis; `CANONICAL_WORLD` after 3D reconstruction. The solver branches on it. |
| `schema_id`, `is_3d`, `source_run_id` | — | planned; not on the class yet          |

### `PoseSequence` (`app.data.pose`)

Everything detected for one video.

| Field            | Type                        | Notes                                    |
|------------------|-----------------------------|------------------------------------------|
| `video_path`     | `Path`                      |                                          |
| `frame_count`    | `int`                       |                                          |
| `fps`            | `float`                     |                                          |
| `resolution`     | `tuple[int, int]`           | width, height                            |
| `tracks`         | `dict[str, PersonTrack]`    | one or more                              |
| `active_track_id`| `str \| None`               | the track the UI currently edits         |

---

## 5. Non-Destructive Editing — `CorrectionLayer`

Manual corrections (Phase 9) never overwrite detected data.

### `CorrectionLayer` (`app.models.corrections`) — *(implemented, Phase 9)*

| Field         | Type                                                      | Notes                                  |
|---------------|----------------------------------------------------------|----------------------------------------|
| `track_id`    | `str`                                                    | which `PersonTrack` it applies to      |
| `overrides`   | `dict[int, dict[JointName, Vector3]]`                    | sparse: `{frame_index: {joint: corrected position}}` |

Undo/redo lives in `app.core.commands` (`CommandStack` + `SetKeypointCorrection` /
`ClearKeypointCorrection` / `PropagateKeypointCorrection`), not an `edit_log`. The layer
is serialized to `corrections/<track_id>.json` (`schema_version`, `overrides`).

- **Effective pose** = detected `PoseFrame` with corrected joints substituted in. It is
  **computed on demand**, never written back into the `PersonTrack`.
- "Propagate a correction" is an explicit operation that writes several `overrides` entries
  (interpolating between corrected keyframes).
- Undo/redo (`app.core.commands`) records commands, not data snapshots; the immutability of
  L0/L1 detection makes this reliable.

---

## 6. Level 2 — Canonical Skeleton

> **Status (Phase 10):** `app/models/skeleton.py` implements `CanonicalBoneName` (17 bones),
> `BoneDefinition`, `CanonicalSkeleton` (+ `CANONICAL_SKELETON` T-pose), `SkeletonPose`,
> `SkeletonClip`. `app/skeleton/solver.py` produces a **2D-constrained** clip from image-plane
> poses (`shortest_arc` per bone, local rotations by hierarchy walk); real 3D reconstruction
> is Phase 15 and only needs to feed real `z`. `app/skeleton/validation.py` does the structural
> + bone-length-stability checks. Serialized to `skeleton/<track_id>.{npz,json}`.

### `BoneDefinition` / `CanonicalSkeleton` (`app.data.skeleton`)

Extends the existing `app/models/skeleton.py`.

- `CanonicalSkeleton`: ordered `BoneDefinition`s, parent/child relationships, a rest pose
  (T-pose) with default bone directions, and the joint→bone association.
- Rig-independent. Bone names are `CanonicalBoneName`, never a target rig's names.

### `SkeletonPose` (`app.data.skeleton`)

One frame of the skeleton.

| Field              | Type                                  | Notes                                |
|--------------------|---------------------------------------|--------------------------------------|
| `frame_index`      | `int`                                 |                                      |
| `bone_rotations`   | `dict[CanonicalBoneName, Quaternion]` | local rotation relative to parent    |
| `root_translation` | `Vector3`                             | pelvis/root position, `CANONICAL_WORLD` |

### `SkeletonClip` (`app.data.skeleton`)

| Field           | Type                              | Notes                                       |
|-----------------|-----------------------------------|---------------------------------------------|
| `skeleton`      | `CanonicalSkeleton`               | the definition these poses animate          |
| `fps`           | `float`                           |                                             |
| `frame_range`   | `tuple[int, int]`                 |                                             |
| `bone_lengths`  | `dict[CanonicalBoneName, float]`  | solved per subject, constant over the clip  |
| `poses`         | `list[SkeletonPose]`              | dense over `frame_range`                     |
| `space`         | `CoordinateSpace`                 | `CANONICAL_WORLD`                            |

Produced by `app.skeleton.solver` from a `PersonTrack` (+ its effective corrections).
For 2D-only input the solver produces a 2D-constrained skeleton; full 3D bone rotations
require a 3D track (MediaPipe world landmarks or a reconstruction backend).

---

## 7. Rig Description & Mapping

> **Status (Phase 13):** `app/models/rig.py` implements `Rig`, `RetargetMap`, `RigClip`.
> `app/retarget/rig_registry.py` discovers one-JSON-per-profile rigs (bundled `canonical`,
> `mixamo`, `rigify`, `unity_humanoid`, plus extra dirs). `app/retarget/retargeter.py`
> maps `SkeletonClip` → `RigClip` (`offset · canonical_local` per mapped bone, root ×
> `unit_scale`). `RigClip` persists to `animation/<rig_id>.{npz,json}`; export embeds the
> `bone_map` in the mcapclip file. Full rest-pose compensation needs real rig data and is
> a later refinement.
>
> **Custom rigs (post-roadmap):** the same profile format is now user-extensible — see
> [`formats/rig_profile_v1.md`](formats/rig_profile_v1.md). Profiles are scanned from
> bundled → `~/.ai-motion-capture/rigs/` → `<project>.mcap/rigs/` (later wins).
> `RigRegistry.install_profile` / `remove_profile` manage user profiles;
> `app/retarget/armature_import.py` turns a Blender-exported armature dump into a
> guessed `bone_map` that the user reviews in `CustomRigDialog`. The canonical skeleton
> itself is unchanged — a custom rig is a new **target**, not a new internal skeleton.

### `Rig` (`app.data.rig`) — a data profile, see `app/retarget/rig_profiles/*.json`

| Field            | Type                          | Notes                                          |
|------------------|-------------------------------|-----------------------------------------------|
| `id`             | `str`                         | `"mixamo"`, `"rigify"`, `"unity_humanoid"`, ... |
| `bones`          | `list[RigBone]`               | name, parent, rest orientation, roll           |
| `up_axis`        | `str`                         | e.g. `"Y"` or `"Z"`                            |
| `forward_axis`   | `str`                         |                                               |
| `unit_scale`     | `float`                       | metres per rig unit                            |
| `space`          | `CoordinateSpace`             | the rig's native space                         |

### `RetargetMap` (`app.data.rig`)

| Field              | Type                                             | Notes                              |
|--------------------|------------------------------------------------|-------------------------------------|
| `rig_id`           | `str`                                          |                                     |
| `bone_map`         | `dict[CanonicalBoneName, str]`                 | canonical bone → rig bone name      |
| `rotation_offsets` | `dict[CanonicalBoneName, Quaternion]`          | rest-pose difference compensation   |
| `axis_remap`       | `dict[CanonicalBoneName, str]`                 | optional per-bone axis swap         |
| `constraints`      | `dict[CanonicalBoneName, list[str]]`           | e.g. `["no_twist"]`, `["hinge"]`    |

---

## 8. Level 3 — Rig Animation

### `RigClip` (`app.data.animation`)

Output of `app.retarget.retargeter` — the last representation before serialization.

| Field             | Type                                   | Notes                                          |
|-------------------|----------------------------------------|-----------------------------------------------|
| `rig_id`          | `str`                                  |                                               |
| `fps`             | `float`                                |                                               |
| `frame_range`     | `tuple[int, int]`                      |                                               |
| `bone_curves`     | `dict[str, RotationCurve]`             | keyed by **rig** bone name; quaternion keyframes |
| `root_curve`      | `TranslationCurve`                     | root motion                                    |
| `space`           | `CoordinateSpace`                      | still `CANONICAL_WORLD` here                   |

`RigClip` stays in `CANONICAL_WORLD`. The conversion to `BLENDER_WORLD` happens **only** in
`app.export.blender_json_exporter`, and is mirrored by `blender_addon/importer.py`.

---

## 9. On-Disk Schemas — `project.mcap/`

> **Status (Phase 8):** `app.core.project_io` implements a first cut. Per-track (not
> per-run) files, keyed by `track_id`. Raw L0 is retained in memory on
> `PersonTrack.raw_frames` during analysis, so it can be written faithfully. The stored
> canonical L1 is written explicitly (not re-derived on load), so a future mapping change
> does not alter existing projects. `corrections/`, `skeleton/`, `animation/`, `export/`,
> `cache/` and the `video/` copy are not written yet.

```
project.mcap/                     (implemented in Phase 8: project.json + poses/)
  project.json
  video/
    source.<ext>            # optional local copy; project.json may point to an external path
    thumbnail.png
  poses/
    raw/
      <track_id>.npz         # L0: points [F,K,2], visibility [F,K], world_points [F,K,3]?,
      #                         frame_indices [F], timestamps [F], person_indices [F]
      <track_id>.json         # schema_version, schema_id, depth_source, has_world
    canonical/
      <track_id>.npz         # L1: positions [F,J,3], confidence [F,J], frame_indices, timestamps
      <track_id>.json         # schema_version, joint_order
  corrections/
    <trackset_id>.json      # CorrectionLayer (sparse) + edit_log
  skeleton/                 # added in Phase 10
    <trackset_id>.npz       # L2: bone_rotations [F, B, 4], root_translation [F, 3]
    <trackset_id>.json      # skeleton ref, bone_lengths, fps, frame_range
  animation/                # added in Phase 13
    <rig_id>.json / .npz    # L3 RigClip per target rig
  export/                   # written on demand, not part of save (Phase 11+)
    <name>.mcapclip.json    # mcapclip v1 interchange file (see docs/formats/mcapclip_v1.md)
    <name>.bvh              # BioVision Hierarchy (Phase 16) — native import, no add-on
  cache/                    # regenerable; safe to delete at any time
```

### `project.json`

| Key                 | Notes                                                          |
|---------------------|--------------------------------------------------------------|
| `schema_version`    | integer; bumped on any breaking change                         |
| `name`              | project name                                                   |
| `created`, `modified` | ISO-8601 timestamps                                          |
| `video`             | `{path, external: bool, frame_count, fps, width, height}`      |
| `detector`          | `{backend_id, config}` — last-used detection backend           |
| `active_track_id`   | the track the UI edits                                         |
| `settings`          | project-scoped overrides of app settings                       |

### `poses/raw/<run_id>.json`

`{schema_version, run_id, backend_id, backend_version, params, schema_id, space, depth_source, timestamp, frame_range, person_count}`

### `poses/canonical/<trackset_id>.json`

`{schema_version, trackset_id, source_run_id, schema_id ("canonical_vN"), space, is_3d, depth_source, tracks: [{track_id, label, frame_indices}]}`

### Versioning rules

- Every JSON file carries `schema_version`.
- `app.core.project_io` owns explicit `migrate_<artifact>_vN_to_vN+1` functions.
- Loading a **newer** unknown version is a hard error, never a best-effort guess.
- `.npz` arrays are described by their sibling `.json`; array shape/dtype changes bump the
  version too.

---

## 10. Data Invariants

1. **L0 raw detection is immutable** once written to `poses/raw/`.
2. **L1 canonical frames contain the full canonical joint set**; undetected joints have
   `confidence == 0.0` and are never removed.
3. **Corrections are a separate sparse layer.** Effective pose = L1 ⊕ `CorrectionLayer`,
   computed on demand, never written back into the track.
4. **Missing frames are gaps, not zeros.** A `PersonTrack` simply has no entry for an
   undetected frame; filling gaps is an explicit `app.animation` step.
5. **Coordinate space is always recorded**, never assumed from context.
6. **Rotations are unit quaternions** `(w, x, y, z)` in `CANONICAL_WORLD` until the export
   boundary.
7. **No canonical or L2/L3 structure references a target rig's bone names** except through
   a `RetargetMap`.
