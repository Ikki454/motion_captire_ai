"""End-to-end tests for 3D reconstruction via the UI (roadmap Phase 15).

Uses the real MediaPipe backend (skipped without the model), because the
reconstruction backend needs stored world landmarks.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from app.ui.main_window import MainWindow

pytest.importorskip("mediapipe")

from app.pose.backends.mediapipe_model import default_model_path

pytestmark = pytest.mark.skipif(
    not default_model_path().exists(), reason="pose model not downloaded"
)

WaitFor = Callable[..., bool]


def _analyse(main_window: MainWindow, person_video: Path, wait_for: WaitFor) -> None:
    main_window.load_video(str(person_video))
    main_window.detector_panel.analyze_button.click()
    assert wait_for(lambda: main_window.controller.pose_sequence is not None)


def test_reconstruct_lists_a_backend(main_window: MainWindow) -> None:
    labels = [
        main_window.reconstruction_panel.backend_combo.itemText(i)
        for i in range(main_window.reconstruction_panel.backend_combo.count())
    ]

    assert any("MediaPipe" in label for label in labels)


def test_reconstruct_then_build_uses_the_3d_track(
    main_window: MainWindow, person_video: Path, wait_for: WaitFor
) -> None:
    _analyse(main_window, person_video, wait_for)

    main_window.reconstruction_panel.reconstruct_button.click()

    assert main_window.controller.reconstructed is True
    assert main_window.controller.reconstruction_backend_id == "mediapipe_world"
    assert (
        "reconstructed"
        in main_window.reconstruction_panel.status_label.text().lower()
    )

    main_window.skeleton_panel.build_button.click()
    clip = main_window.controller.skeleton_clip
    assert clip is not None
    positive = [value for value in clip.bone_lengths.values() if value > 0.0]
    # 3D track -> real-world bone lengths (metres), not hundreds of pixels
    assert positive and max(positive) < 5.0


def test_correcting_a_keypoint_drops_the_reconstruction(
    main_window: MainWindow, person_video: Path, wait_for: WaitFor
) -> None:
    from app.models.pose import JointName, Vector3

    _analyse(main_window, person_video, wait_for)
    main_window.reconstruction_panel.reconstruct_button.click()
    assert main_window.controller.reconstructed is True

    main_window.video_view.keypoint_moved.emit(
        JointName.LEFT_WRIST, Vector3(1.0, 2.0, 0.0)
    )

    assert main_window.controller.reconstructed is False


def test_overlay_stays_two_dimensional_after_reconstruction(
    main_window: MainWindow, person_video: Path, wait_for: WaitFor
) -> None:
    _analyse(main_window, person_video, wait_for)
    main_window.reconstruction_panel.reconstruct_button.click()

    pose = main_window.controller.effective_pose_at(0)
    assert pose is not None
    xs = [joint.position.x for joint in pose.joints.values() if joint.confidence > 0]
    # still image-pixel scale, not metres
    assert max(xs) > 5.0
