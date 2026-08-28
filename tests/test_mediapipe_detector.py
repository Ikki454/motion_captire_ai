"""Tests for the MediaPipe pose backend (roadmap Phase 6).

Skipped unless the ``mediapipe`` extra is installed and the pose model has
been downloaded (``python -m app.pose.backends.mediapipe_model``).
"""

from collections.abc import Iterator

import numpy as np
import pytest

pytest.importorskip("mediapipe")

from app.pose.backends.mediapipe_detector import MediaPipeDetector
from app.pose.backends.mediapipe_model import default_model_path
from app.pose.schemas import MEDIAPIPE_POSE_SCHEMA_ID

pytestmark = pytest.mark.skipif(
    not default_model_path().exists(),
    reason="pose model not downloaded",
)


@pytest.fixture
def detector() -> Iterator[MediaPipeDetector]:
    instance = MediaPipeDetector()
    try:
        yield instance
    finally:
        instance.close()


def test_schema_and_capabilities(detector: MediaPipeDetector) -> None:
    assert detector.schema.schema_id == MEDIAPIPE_POSE_SCHEMA_ID
    assert detector.schema.keypoint_count == 33
    assert detector.capabilities.keypoint_count == 33
    assert detector.capabilities.multi_person is False
    assert detector.capabilities.gpu is True


def test_use_gpu_flag_is_accepted() -> None:
    # The GPU delegate may not be available on this platform; we only
    # check the constructor honours the keyword without a TypeError.
    try:
        detector = MediaPipeDetector(use_gpu=False)
    except RuntimeError:  # pragma: no cover - platform dependent
        return
    detector.close()


def test_blank_frame_yields_no_pose(detector: MediaPipeDetector) -> None:
    blank = np.full((240, 320, 3), 255, dtype=np.uint8)

    assert detector.detect(blank, 0, 0.0) is None


def test_detects_a_person(detector: MediaPipeDetector, person_image: np.ndarray) -> None:
    raw = detector.detect(person_image, 3, 0.5)

    assert raw is not None
    assert raw.schema_id == MEDIAPIPE_POSE_SCHEMA_ID
    assert raw.frame_index == 3
    assert raw.points.shape == (33, 2)
    assert raw.visibility.shape == (33,)
    # nose / shoulders should be confidently visible in a portrait
    assert raw.visibility[0] > 0.5


def test_missing_model_path_raises() -> None:
    with pytest.raises(FileNotFoundError):
        MediaPipeDetector(model_path="does/not/exist.task")
