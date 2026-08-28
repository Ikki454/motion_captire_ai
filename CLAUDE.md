# CLAUDE.md — AI Motion Capture Project

## Project

This project is a desktop application that converts human movement from video into skeletal animation that can be imported into Blender.

The application pipeline is:

Video
→ Video Analysis
→ Human Pose Detection
→ 2D / 3D Keypoints
→ Skeleton Retargeting
→ Animation Processing
→ Blender Export

## Main Technologies

* Python 3.12+
* PySide6 for the desktop interface
* OpenCV for video processing
* MediaPipe for the first pose detection prototype
* PyTorch for advanced AI models
* NumPy and SciPy for mathematical processing
* Blender Python API for Blender integration
* pytest for automated tests

## Architecture Rules

The project must use a modular architecture.

Do not put all logic in a single file.

Separate the project into:

* UI
* Video processing
* Pose detection
* Pose data
* Skeleton definitions
* Retargeting
* Animation processing
* Export
* Blender integration

## Important Rules

* Do not implement features that were not requested.
* Do not modify unrelated files.
* Before making a major architectural change, explain the change.
* Prefer simple and maintainable solutions.
* Avoid unnecessary dependencies.
* Use type hints.
* Write documentation for public classes and functions.
* Add tests for important mathematical functions.
* Keep UI logic separate from AI and animation logic.

## Development Workflow

Work on only one feature at a time.

For every feature:

1. Analyze the existing code.
2. Explain the implementation plan.
3. Identify the files that need modification.
4. Implement the feature.
5. Run tests.
6. Check for errors.
7. Summarize the changes.

## Do Not

* Do not rewrite the entire project without asking.
* Do not replace working systems unnecessarily.
* Do not create placeholder implementations unless explicitly requested.
* Do not silently change the data format.
* Do not mix Blender-specific code into the core application.

## Code Quality

* Follow PEP 8.
* Use descriptive names.
* Avoid global state.
* Keep functions focused.
* Prefer composition over unnecessary inheritance.
* Handle errors explicitly.

## Data Model

The application should use an internal, rig-independent skeleton representation.

AI keypoints must not directly depend on Blender bone names.

Use an intermediate representation:

AI Keypoints
→ Canonical Human Skeleton
→ Target Rig Mapping

This allows support for multiple skeletons and rigs.

## Performance

Video analysis must not block the user interface.

Long-running operations should run outside the main UI thread.

Design the architecture so that GPU acceleration can be added or improved later.

## Current Development Stage

Build the project incrementally.

Current priority:

1. Video import
2. Video playback
3. Frame extraction
4. 2D human pose detection
5. Display detected keypoints
6. Save pose data

Do not implement advanced 3D reconstruction until the 2D pipeline is stable.
