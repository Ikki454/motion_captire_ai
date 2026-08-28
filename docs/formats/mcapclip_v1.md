# `mcapclip` interchange format — v1

The animation file the desktop app writes and the Blender add-on reads. One
file holds one solved canonical `SkeletonClip` for one person.

- **Extension:** `.mcapclip.json`
- **Encoding:** UTF-8 JSON
- **Producer:** `app/export/animation_export.py` (`export_animation`)
- **Consumer:** `blender_addon/` (Phase 12) — and `import_animation` for round-trips
- **Coordinate space:** `canonical_world` — **right-handed, Y-up** (X right, Y up, Z toward
  the viewer). The consumer converts to its own world. Nothing converts silently.
  `blender_addon/conversion.py` maps `(x, y, z) -> (x, -z, y)` (a +90° rotation about X) to
  reach Blender's Z-up world, and conjugates rotations by the same frame change.

## Top-level object

| Key                | Type              | Notes                                              |
|--------------------|-------------------|---------------------------------------------------|
| `format`           | `"mcapclip"`      | rejected otherwise                                 |
| `version`          | `1`               | a reader refuses a higher version                  |
| `name`             | string            | free label (usually the track id)                 |
| `coordinate_space` | `"canonical_world"` | informational; always this value in v1          |
| `fps`              | number            | frames per second of the source video             |
| `frame_range`      | `[int, int]`      | first and last solved frame index (inclusive)     |
| `skeleton`         | object            | see below                                          |
| `bone_lengths`     | `{bone: number}`  | median measured length per bone, canonical units  |
| `bone_map`         | `{canonical: rig}` \| absent | *(optional)* canonical bone name → target rig bone name. When present, a consumer places each bone's rotation on the mapped rig bone. |
| `frames`           | array             | one entry per solved frame                         |

## `skeleton.bones[]`

Ordered **parent-first**. Enough for a consumer to rebuild the hierarchy
without the app.

| Key             | Type                | Notes                                        |
|-----------------|---------------------|---------------------------------------------|
| `name`          | string              | canonical bone name                          |
| `parent`        | string \| `null`    | parent bone name; `null` for root bones      |
| `parent_joint`  | string              | canonical joint at the bone's base           |
| `child_joint`   | string              | canonical joint at the bone's tip            |
| `rest_direction`| `[x, y, z]`         | unit vector of the bone in the rest T-pose   |

## `frames[]`

| Key         | Type                       | Notes                                          |
|-------------|----------------------------|-----------------------------------------------|
| `frame`     | int                        | source video frame index                       |
| `root`      | `[x, y, z]`                | pelvis position in `canonical_world`           |
| `rotations` | `{bone: [w, x, y, z]}`     | **local** unit quaternion per bone (relative to the parent bone). Every bone in `skeleton.bones` is present. |

## Notes

- Rotations are the local delta from each bone's `rest_direction` to its posed
  direction, composed down the hierarchy (`world[bone] = world[parent] * local[bone]`).
- The v1 clip is **2D-constrained**: it is solved from image-plane poses, so
  rotations lie in the image plane after the y-up flip. A future 3D
  reconstruction fills real depth without changing this schema.
- Missing/occluded joints yield the identity rotation for the affected bone and
  a `bone_lengths` entry of `0`.
