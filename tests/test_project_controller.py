"""ProjectController tests: import, navigation, playback, persistence (Phase 8)."""

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from app.core.project import MotionCaptureProject
from app.core.project_controller import ProjectController
from app.core.project_io import ProjectIOError, save_project
from app.plugins.registry import BackendRegistry
from app.video.video_loader import VideoMetadata


def test_import_video_attaches_metadata_to_project(sample_video: Path) -> None:
    controller = ProjectController()

    metadata = controller.import_video(sample_video)

    assert controller.project.video_metadata is metadata
    assert metadata.path == sample_video
    assert metadata.frame_count > 0
    assert metadata.fps > 0
    assert metadata.width > 0
    assert metadata.height > 0


def test_import_missing_video_raises_and_leaves_project_untouched() -> None:
    controller = ProjectController()

    with pytest.raises(FileNotFoundError):
        controller.import_video("does/not/exist.mp4")

    assert controller.project.video_metadata is None


def test_import_corrupt_video_raises_runtime_error(corrupt_video: Path) -> None:
    controller = ProjectController()

    with pytest.raises(RuntimeError):
        controller.import_video(corrupt_video)

    assert controller.project.video_metadata is None


def test_current_frame_index_starts_at_zero_after_import(sample_video: Path) -> None:
    controller = ProjectController()

    controller.import_video(sample_video)

    assert controller.current_frame_index == 0
    assert controller.has_video is True


def test_go_to_frame_updates_index_and_returns_frame(sample_video: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)

    frame = controller.go_to_frame(3)

    assert controller.current_frame_index == 3
    assert frame.shape[2] == 3


def test_go_to_frame_clamps_to_valid_range(sample_video: Path) -> None:
    controller = ProjectController()
    metadata = controller.import_video(sample_video)

    controller.go_to_frame(10_000)
    assert controller.current_frame_index == metadata.frame_count - 1

    controller.go_to_frame(-5)
    assert controller.current_frame_index == 0


def test_step_frame_moves_and_clamps_at_both_ends(sample_video: Path) -> None:
    controller = ProjectController()
    metadata = controller.import_video(sample_video)

    controller.step_frame(2)
    controller.step_frame(1)
    assert controller.current_frame_index == 3

    controller.go_to_frame(0)
    controller.step_frame(-1)
    assert controller.current_frame_index == 0

    controller.go_to_frame(metadata.frame_count - 1)
    controller.step_frame(1)
    assert controller.current_frame_index == metadata.frame_count - 1


def test_current_timestamp_tracks_index_and_fps(sample_video: Path) -> None:
    controller = ProjectController()
    metadata = controller.import_video(sample_video)

    controller.go_to_frame(5)

    assert controller.current_timestamp == pytest.approx(5 / metadata.fps)


def test_navigation_before_import_raises_runtime_error() -> None:
    controller = ProjectController()

    assert controller.has_video is False

    with pytest.raises(RuntimeError):
        controller.go_to_frame(0)

    with pytest.raises(RuntimeError):
        controller.step_frame(1)


def test_playback_starts_paused_and_ignores_play_before_import() -> None:
    controller = ProjectController()

    assert controller.is_playing is False

    controller.play()

    assert controller.is_playing is False


def test_play_and_pause_after_import(sample_video: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)

    controller.play()
    assert controller.is_playing is True

    controller.pause()
    assert controller.is_playing is False


def test_frame_interval_reflects_video_fps(sample_video: Path) -> None:
    controller = ProjectController()
    metadata = controller.import_video(sample_video)

    assert controller.frame_interval_ms == max(1, round(1000.0 / metadata.fps))


def test_stop_pauses_and_rewinds(sample_video: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)
    controller.go_to_frame(4)
    controller.play()

    controller.stop()

    assert controller.is_playing is False
    assert controller.current_frame_index == 0


def test_advance_playback_returns_none_when_paused(sample_video: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)

    assert controller.advance_playback() is None


def test_advance_playback_advances_one_frame_while_playing(sample_video: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)
    controller.play()

    frame = controller.advance_playback()

    assert frame is not None
    assert controller.current_frame_index == 1


def test_advance_playback_auto_pauses_at_end(sample_video: Path) -> None:
    controller = ProjectController()
    metadata = controller.import_video(sample_video)
    controller.go_to_frame(metadata.frame_count - 1)
    controller.play()

    result = controller.advance_playback()

    assert result is None
    assert controller.is_playing is False
    assert controller.current_frame_index == metadata.frame_count - 1


def _analyse_synchronously(controller: ProjectController) -> None:
    done = threading.Event()
    controller.analyze_video(on_done=lambda result: done.set())
    assert done.wait(timeout=10)


def test_save_project_requires_a_path(sample_video: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)

    with pytest.raises(ProjectIOError):
        controller.save_project()

    controller.close()


def test_save_project_remembers_its_path(sample_video: Path, tmp_path: Path) -> None:
    controller = ProjectController()
    controller.import_video(sample_video)

    target = tmp_path / "a.mcap"
    controller.save_project(target)

    assert controller.project.project_path == target
    controller.save_project()  # no-arg re-save must not raise
    controller.close()


def test_save_then_reopen_restores_analysis(
    sample_video: Path,
    tmp_path: Path,
    make_pose_registry: Callable[..., BackendRegistry],
) -> None:
    controller = ProjectController(pose_registry=make_pose_registry(gap_every=4))
    controller.import_video(sample_video)
    controller.set_detector("fake")
    _analyse_synchronously(controller)
    detected = controller.pose_sequence.active_track.detection_count

    project_dir = tmp_path / "proj.mcap"
    controller.save_project(project_dir)
    controller.close()

    reopened = ProjectController(pose_registry=make_pose_registry())
    reopened.open_project(project_dir)

    assert reopened.has_video is True
    assert reopened.frame_count == controller.frame_count
    assert reopened.pose_sequence.active_track.detection_count == detected
    assert reopened.active_pose_at(1) is not None
    reopened.close()


def test_open_project_with_missing_video_raises(tmp_path: Path) -> None:
    metadata = VideoMetadata(
        path=tmp_path / "gone.mp4", frame_count=5, fps=10.0, width=16, height=16
    )
    save_project(
        tmp_path / "p.mcap",
        MotionCaptureProject(name="x", video_metadata=metadata),
        None,
    )

    controller = ProjectController()

    with pytest.raises(ProjectIOError):
        controller.open_project(tmp_path / "p.mcap")

    controller.close()
