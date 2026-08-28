"""Tests for the DetectorPanel widget (roadmap Phase 6)."""

from PySide6.QtWidgets import QApplication

from app.plugins.types import BackendAvailability, BackendEntry
from app.ui.widgets.detector_panel import DetectorPanel


def _entry(backend_id: str, availability: BackendAvailability) -> BackendEntry:
    return BackendEntry(
        backend_id=backend_id,
        display_name=backend_id.title(),
        factory=lambda: None,
        availability=availability,
    )


def test_available_backends_populate_combo_and_enable_button(qt_app: QApplication) -> None:
    panel = DetectorPanel()

    panel.set_backends([_entry("mediapipe", BackendAvailability.ok())], [])
    assert panel.current_backend_id() == "mediapipe"

    # detection stays disabled until a video is loaded
    assert not panel.detect_button.isEnabled()
    panel.set_video_loaded(True)
    assert panel.detect_button.isEnabled()


def test_unavailable_backend_reason_is_shown(qt_app: QApplication) -> None:
    panel = DetectorPanel()

    panel.set_backends(
        [],
        [_entry("mediapipe", BackendAvailability.missing("not installed"))],
    )

    assert not panel.detect_button.isEnabled()
    assert panel.current_backend_id() is None
    assert "not installed" in panel.status_label.text()


def test_detect_button_emits_detect_requested(qt_app: QApplication) -> None:
    panel = DetectorPanel()
    panel.set_backends([_entry("mediapipe", BackendAvailability.ok())], [])
    panel.set_video_loaded(True)

    received: list[int] = []
    panel.detect_requested.connect(lambda: received.append(1))

    panel.detect_button.click()

    assert received == [1]


def test_set_status_updates_label(qt_app: QApplication) -> None:
    panel = DetectorPanel()

    panel.set_status("Detected 13 / 13 keypoints.")

    assert panel.status_label.text() == "Detected 13 / 13 keypoints."
