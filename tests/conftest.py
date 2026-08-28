"""Shared pytest fixtures."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.core.project_controller import ProjectController
from app.models.keypoints import KeypointSchema, RawPose
from app.plugins.registry import BackendRegistry
from app.plugins.types import BackendAvailability, BackendEntry
from app.pose.capabilities import DetectorCapabilities
from app.pose.detector_base import PoseDetector
from app.pose.schemas import MEDIAPIPE_POSE
from app.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    """Provide a single headless QApplication for the whole test session."""

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


@pytest.fixture
def rig_dir(tmp_path: Path) -> Path:
    """An isolated custom-rig directory, so tests never touch the real one."""

    return tmp_path / "user_rigs"


@pytest.fixture
def main_window(qt_app: QApplication, rig_dir: Path) -> Iterator[MainWindow]:
    """Provide a MainWindow that is closed (releasing its video) on teardown."""

    window = MainWindow(ProjectController(rig_dir=rig_dir))
    try:
        yield window
    finally:
        window.close()


@pytest.fixture
def wait_for(qt_app: QApplication) -> Callable[..., bool]:
    """Return a helper that spins the Qt event loop until a predicate holds."""

    def _wait(predicate: Callable[[], bool], timeout_ms: int = 4000) -> bool:
        loop = QEventLoop()
        ticker = QTimer()
        ticker.timeout.connect(loop.quit)
        ticker.start(20)

        elapsed = 0
        while not predicate() and elapsed < timeout_ms:
            loop.exec()
            elapsed += 20

        ticker.stop()
        return predicate()

    return _wait


class FakePoseDetector(PoseDetector):
    """A MediaPipe-shaped detector for tests -- no model, no dependencies."""

    def __init__(self, *, find_pose: bool = True, gap_every: int = 0) -> None:
        self._find_pose = find_pose
        self._gap_every = gap_every

    @property
    def schema(self) -> KeypointSchema:
        return MEDIAPIPE_POSE

    @property
    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(keypoint_count=33)

    def detect(
        self, frame: np.ndarray, frame_index: int, timestamp: float
    ) -> RawPose | None:
        if not self._find_pose:
            return None
        if self._gap_every and frame_index % self._gap_every == 0:
            return None

        return RawPose(
            schema_id=MEDIAPIPE_POSE.schema_id,
            frame_index=frame_index,
            timestamp=timestamp,
            person_index=0,
            points=np.tile((4.0, 5.0), (33, 1)),
            visibility=np.ones(33),
        )


@pytest.fixture
def make_pose_registry() -> Callable[..., BackendRegistry]:
    """Return a factory building a registry with one fake backend."""

    def _make(
        *, available: bool = True, find_pose: bool = True, gap_every: int = 0
    ) -> BackendRegistry:
        registry = BackendRegistry("test.pose_backends")
        registry.register(
            BackendEntry(
                backend_id="fake",
                display_name="Fake detector",
                factory=lambda: FakePoseDetector(
                    find_pose=find_pose, gap_every=gap_every
                ),
                availability=(
                    BackendAvailability.ok()
                    if available
                    else BackendAvailability.missing("test: disabled")
                ),
            )
        )
        return registry

    return _make


@pytest.fixture
def make_main_window(
    qt_app: QApplication, rig_dir: Path
) -> Iterator[Callable[..., MainWindow]]:
    """Return a factory for MainWindows; all are closed on teardown."""

    windows: list[MainWindow] = []

    def _make(registry: BackendRegistry | None = None) -> MainWindow:
        controller = ProjectController(pose_registry=registry, rig_dir=rig_dir)
        window = MainWindow(controller)
        windows.append(window)
        return window

    try:
        yield _make
    finally:
        for window in windows:
            window.close()


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    """Write a short, valid video file and return its path.

    Skips the test if the local OpenCV build cannot encode MJPG/AVI.
    """

    path = tmp_path / "sample.avi"
    fps = 24.0
    width, height = 64, 48
    frame_count = 12

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        writer.release()
        pytest.skip("OpenCV cannot encode MJPG/AVI in this environment")

    try:
        for index in range(frame_count):
            frame = np.full((height, width, 3), (index * 20) % 256, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()

    return path


@pytest.fixture
def corrupt_video(tmp_path: Path) -> Path:
    """Write a file that looks like a video but cannot be opened."""

    path = tmp_path / "broken.mp4"
    path.write_bytes(b"this is not a real video file")
    return path


@pytest.fixture
def person_image() -> np.ndarray:
    """Return a BGR photo of a real person (bundled with matplotlib).

    Skips the test when matplotlib is not installed.
    """

    matplotlib = pytest.importorskip("matplotlib")
    photo_path = Path(matplotlib.get_data_path()) / "sample_data" / "grace_hopper.jpg"
    image = cv2.imread(str(photo_path))

    if image is None:
        pytest.skip(f"could not read {photo_path}")

    return image


@pytest.fixture
def person_video(tmp_path: Path, person_image: np.ndarray) -> Path:
    """Write a short video whose frames are all a photo of a person."""

    height, width = person_image.shape[:2]
    path = tmp_path / "person.avi"

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        12.0,
        (width, height),
    )

    if not writer.isOpened():
        writer.release()
        pytest.skip("OpenCV cannot encode MJPG/AVI in this environment")

    try:
        for _ in range(6):
            writer.write(person_image)
    finally:
        writer.release()

    return path
