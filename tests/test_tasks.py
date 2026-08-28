"""Tests for the Qt-free TaskManager (roadmap Phase 7)."""

import threading
import time
from collections.abc import Iterator

import pytest
from PySide6.QtCore import QEventLoop, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from app.core.tasks import TaskManager, TaskResult, TaskStatus


@pytest.fixture
def task_manager() -> Iterator[TaskManager]:
    manager = TaskManager()
    try:
        yield manager
    finally:
        manager.shutdown()


def _run_and_wait(manager: TaskManager, job, **kwargs) -> TaskResult:
    done = threading.Event()
    box: dict[str, TaskResult] = {}

    def capture(result: TaskResult) -> None:
        box["result"] = result
        done.set()

    manager.submit(job, on_done=capture, **kwargs)
    assert done.wait(timeout=5)
    return box["result"]


def test_successful_job_returns_its_value(task_manager: TaskManager) -> None:
    result = _run_and_wait(task_manager, lambda token, report: 42)

    assert result.status is TaskStatus.SUCCEEDED
    assert result.value == 42


def test_job_exception_is_captured_as_failure(task_manager: TaskManager) -> None:
    def boom(token, report):
        raise ValueError("nope")

    result = _run_and_wait(task_manager, boom)

    assert result.status is TaskStatus.FAILED
    assert isinstance(result.error, ValueError)


def test_progress_reports_are_forwarded(task_manager: TaskManager) -> None:
    seen: list[tuple[int, int]] = []

    def job(token, report):
        for index in range(3):
            report(index + 1, 3)

    _run_and_wait(task_manager, job, on_progress=lambda d, t: seen.append((d, t)))

    assert seen == [(1, 3), (2, 3), (3, 3)]


def test_cancel_token_stops_a_cooperative_job(task_manager: TaskManager) -> None:
    started = threading.Event()
    done = threading.Event()
    box: dict[str, TaskResult] = {}

    def job(token, report):
        started.set()
        while not token.cancelled:
            time.sleep(0.005)
        return "stopped"

    def capture(result: TaskResult) -> None:
        box["result"] = result
        done.set()

    token = task_manager.submit(job, on_done=capture)
    assert started.wait(2)

    token.cancel()

    assert done.wait(2)
    assert box["result"].status is TaskStatus.CANCELLED


class _Bridge(QObject):
    progress = Signal(int, int)
    finished = Signal(object)


def test_callbacks_marshal_onto_the_qt_thread(
    qt_app: QApplication, task_manager: TaskManager
) -> None:
    bridge = _Bridge()
    progress: list[tuple[int, int]] = []
    status: list[TaskStatus] = []
    bridge.progress.connect(lambda d, t: progress.append((d, t)))
    bridge.finished.connect(lambda result: status.append(result.status))

    def job(token, report):
        report(1, 1)
        return "x"

    task_manager.submit(
        job, on_progress=bridge.progress.emit, on_done=bridge.finished.emit
    )

    loop = QEventLoop()
    QTimer.singleShot(300, loop.quit)
    loop.exec()

    assert progress == [(1, 1)]
    assert status == [TaskStatus.SUCCEEDED]
