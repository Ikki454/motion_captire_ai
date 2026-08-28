# Rig profile & armature dump — v1

Two small JSON formats that let the app retarget onto a rig it was not shipped
with. They are separate on purpose: the **armature dump** is a raw list of bone
names coming out of a DCC, the **rig profile** is the app's own description of a
target rig.

```
Blender armature ──(add-on export)──▶ armature dump ──(auto_map + review)──▶ rig profile
                                                       manual entry ────────▶
```

---

## 1. Rig profile

The unit of a target rig. Both the bundled profiles and every custom one use
this format — there is no second-class citizen.

- **Extension:** `.json`
- **Producer:** `app/retarget/armature_import.py` (`build_profile_document`), or hand-written
- **Consumer:** `app/retarget/rig_registry.py` (`RigRegistry`)
- **Locations, scanned in this order (later wins for the same `rig_id`):**
  1. `app/retarget/rig_profiles/` — bundled, read-only
  2. `~/.ai-motion-capture/rigs/` — the user's custom profiles
  3. `<project>.mcap/rigs/` — the copy a project carries, so it stays portable

| Key                | Type                        | Notes                                                     |
|--------------------|-----------------------------|-----------------------------------------------------------|
| `schema_version`   | `1`                         | a reader refuses a higher version                          |
| `rig_id`           | string                      | **required**, and the file's stem. `[a-z0-9_]+` only — it becomes a filename |
| `display_name`     | string                      | shown in the UI; defaults to `rig_id`                      |
| `bone_map`         | `{canonical: rig}`          | **required**. Canonical bone name → target rig bone name. Keys must be `CanonicalBoneName` values; unknown keys are an error |
| `rotation_offsets` | `{canonical: [w,x,y,z]}`    | *(optional)* rest-pose difference, applied as `offset · canonical_local` |
| `unit_scale`       | number                      | metres per rig unit; scales the **root translation**. Mixamo uses `0.01`. Default `1.0` |
| `up_axis`          | `"Y"` \| `"Z"`              | *(informational in v1)* recorded but not applied — the Y-up → Z-up conversion happens only in `blender_addon/conversion.py`. Default `"Y"` |
| `attachment_points`| `{slot: rig bone}`          | *(optional)* where extra bone chains hang off the rig. **Nothing drives these yet** — see below |

### `attachment_points`

The canonical skeleton has 17 bones. A game rig has far more — fingers, toes,
extra spine segments. Those cannot be mapped to a canonical role because
**no capture backend feeds them**: `PoseLandmarker` returns 33 body landmarks,
of which the hand gets only `wrist`, `index`, `pinky` and `thumb`.

Rather than pretend otherwise, the profile records *where such a chain attaches*:

```json
"attachment_points": { "left_hand": "hand.L", "right_hand": "hand.R" }
```

One entry stands in for a whole chain — `hand.L` reaches the fifteen finger bones
below it. Known slots are `left_hand` and `right_hand`. Slot names are **not**
validated: a later backend may add slots this version has never heard of, and an
older reader must not reject a profile over one.

`retarget_issues` reports these as *recorded but not driven*, so the gap is
visible rather than silent. MediaPipe does ship `HolisticLandmarker` and
`HandLandmarker`, so driving them is a matter of adding a backend and extending
the canonical skeleton — a separate piece of work.

A **partial** `bone_map` is valid and normal. Canonical bones with no entry are
simply left out of the `RigClip`, and `retarget_issues` reports them. Real rigs
have no `left_hip` / `right_hip` bone — the bundled Mixamo profile omits them too.

```json
{
  "schema_version": 1,
  "rig_id": "my_blender_rig",
  "display_name": "My Blender Rig",
  "up_axis": "Z",
  "unit_scale": 1.0,
  "bone_map": {
    "spine": "spine.001",
    "neck": "neck",
    "head": "head",
    "left_upper_arm": "upper_arm.L",
    "left_lower_arm": "forearm.L"
  }
}
```

### Errors

`RigProfileError` is raised for: a missing or newer `schema_version`, a missing
`bone_map`, a key that is not a canonical bone name, a `rig_id` that is unsafe as
a filename, and — on install — a `rig_id` that belongs to a bundled profile.

Listing is more forgiving than loading: a file with a readable `rig_id` appears in
the rig list even if the rest is malformed, and fails when actually loaded.

---

## 2. Armature dump

What the Blender add-on writes (`File > Export > AI Mocap Rig`). It carries bone
names only — no rest pose, no animation. The app turns it into a rig profile via
`auto_map` plus the review dialog.

- **Extension:** `.json`
- **Producer:** `blender_addon/armature_dump.py` (`build_dump_document`)
- **Consumer:** `app/retarget/armature_import.py` (`parse_armature_dump`)

| Key             | Type                | Notes                                          |
|-----------------|---------------------|------------------------------------------------|
| `format`        | `"mcap_armature"`   | rejected otherwise                              |
| `version`       | `1`                 | a reader refuses a higher version                |
| `armature_name` | string              | seeds the profile's `display_name`               |
| `up_axis`       | string              | `"Z"` from Blender                               |
| `unit_scale`    | number              | Blender's `scene.unit_settings.scale_length`     |
| `bones`         | array               | `{"name": str, "parent": str \| null}` objects. A plain array of strings is also accepted; `parent` feeds the hip inference below |

```json
{
  "format": "mcap_armature",
  "version": 1,
  "armature_name": "Armature",
  "up_axis": "Z",
  "unit_scale": 1.0,
  "bones": [
    {"name": "spine", "parent": null},
    {"name": "spine.001", "parent": "spine"}
  ]
}
```

### Auto-mapping

`auto_map` normalises each bone name (drops `mixamorig:` / `DEF-` / `ORG-` /
`MCH-` prefixes and digits, splits camelCase and separators, extracts the
`L`/`R` side) and matches it against an ordered rule table, most specific rule
first — so `LeftForeArm` reaches `forearm` before the bare `arm` rule.

Verified against three conventions, 15/17 bones each (the two misses are the
hips, which these rigs do not have):

| Convention | Example names                                 |
|------------|-----------------------------------------------|
| Mixamo     | `mixamorig:LeftForeArm`, `mixamorig:LeftUpLeg` |
| Rigify     | `upper_arm.L`, `shin.L`, `shoulder.L`          |
| Unreal     | `upperarm_l`, `calf_l`, `clavicle_l`           |

Hands, fingers, toes and eyes are deliberately skipped — the canonical skeleton
has no bones for them. The guess is conservative: an unmatched role is left
empty rather than filled with a plausible-looking bone, and each rig bone is
used at most once.

### Placing the hips from the hierarchy

Names alone cannot find `left_hip` / `right_hip`: rigs spell that bone
`pelvis.L`, `hip.L`, `plevis.L` (a common misspelling), or give it no name of
its own. So when the dump carries `parent` links, a second pass uses the
structure instead: **the canonical hip is the parent of whatever plays the
upper-leg role**, whatever it is called.

One guard makes this safe. A rig with no hip bones hangs both thighs off a
single shared pelvis or root; mapping that one bone to a side would be wrong.
So when both thighs share a parent, neither hip is inferred:

| Rig | `parent(left thigh)` | `parent(right thigh)` | Result |
|---|---|---|---|
| Sided pelvis | `plevis.L` | `plevis.R` | both hips placed |
| Mixamo, Unreal | `Hips` | `Hips` | neither placed, `Hips` left free |

A hip already matched by name is never overridden, and the armature root is
refused outright — a hip hangs off a pelvis or a spine, never off the top of the
hierarchy. (Without that second guard, a rig with a single leg modelled would
slip past the shared-parent check.) Without `parent` data the pass does not run,
so `auto_map(bone_names)` behaves exactly as before.

### Grouping the leftover chains

`detect_bone_groups(bone_names, parents, mapping)` folds every unmapped bone into
the chain it belongs to. A group starts at an unmapped bone whose parent *is*
mapped, and holds that bone plus its descendants, stopping at any mapped bone. A
group whose root has three or more child chains is classified as `fingers` and
becomes an attachment point; the rest are plain chains.

Bones *above* the mapped skeleton (an armature root, a pelvis every mapped bone
descends from) are not grouped — they have no attachment point.

On a real 56-bone metarig this accounts for every bone:

| | Count |
|---|---:|
| Mapped to a canonical role | 17 |
| In chains (`hand.L` 16, `hand.R` 16, `spine.002` 3, `toe.L` 1, `toe.R` 1) | 37 |
| Above the skeleton (`Root`, `plevis`) | 2 |
| **Total** | **56** |
