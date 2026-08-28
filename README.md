# AI Motion Capture

Desktop application for converting human movement from video into animation data usable in Blender.

## Current Status

Roadmap phases 1–17 complete, plus the UI redesign and custom rig profiles
(see `docs/roadmap.md`). 363 tests.

## Run

```
uv sync --extra mediapipe
uv run python -m app.pose.backends.mediapipe_model   # one-time: download the pose model
uv run python -m app.main
```

## Build

```
uv build
```

Produces `dist/ai_motion_capture-0.1.0-py3-none-any.whl` (+ sdist). Install it with
`pip install "ai_motion_capture-0.1.0-py3-none-any.whl[mediapipe]"`; it exposes the
`ai-motion-capture` / `ai-motion-capture-gui` launchers. The pose model is downloaded at
runtime (`python -m app.pose.backends.mediapipe_model`), not shipped.

The Blender add-on is packaged separately — zip `blender_addon/` and install it via
Blender > Preferences > Add-ons. It adds `File > Import > AI Mocap Clip` (apply an
animation to an armature) and `File > Export > AI Mocap Rig` (dump an armature's bone
names for the app's "Import rig..." action).

## Custom rigs

To retarget onto your own armature instead of the bundled `canonical` / `mixamo` /
`rigify` / `unity_humanoid` profiles:

1. In Blender, select the armature and use `File > Export > AI Mocap Rig`.
2. In the app, section 6 ("Rig and export") → **Import rig...** and pick that file.
   The bone mapping is guessed; correct any row in the dialog and save.

**New rig...** does the same without a file (type the bone names by hand). Custom
profiles are stored in `~/.ai-motion-capture/rigs/`, and the one a project uses is
copied into `<project>.mcap/rigs/` so the project stays portable. Format:
`docs/formats/rig_profile_v1.md`.

Bones the canonical skeleton has no role for — fingers, toes, extra spine segments —
are folded into chains and reported rather than listed one by one. A hand's finger
chains become a single **attachment point** you confirm once. Nothing drives those
bones today (the pose detector returns no finger data); they keep their rest pose on
import, and the retarget report says so explicitly.

## Main Goal

The application will:

1. Import a video.
2. Detect human body keypoints.
3. Track movement across frames.
4. Allow manual correction.
5. Convert pose data into skeletal animation.
6. Retarget animation to different rigs.
7. Export animation for Blender.

## Technology

* Python
* PySide6
* OpenCV
* NumPy
* MediaPipe
* PyTorch
* Blender Python API

## Pose detection (optional)

The MediaPipe pose backend is an optional install:

```
uv sync --extra mediapipe
uv run python -m app.pose.backends.mediapipe_model
```

The second command downloads the pose model to `models/`. Without the extra, the app
runs normally and the detector panel shows MediaPipe as unavailable.

## Development

The project is developed incrementally.

See:

* `CLAUDE.md`
* `docs/architecture.md`
* `docs/data_model.md`
* `docs/roadmap.md`
