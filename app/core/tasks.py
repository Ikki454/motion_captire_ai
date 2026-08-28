"""Background task execution, kept free of Qt.

A :class:`TaskManager` runs callables on a small thread pool. Each callable
receives a :class:`CancelToken` and a progress reporter; results and
progress are delivered through plain callbacks invoked from the worker
thread. The UI marshals those callbacks onto its own thread (for example by
emitting Qt signals).

This reserves the seam from ``architecture.md`` section 8: the executor can
later become a process pool without changing callers.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from threading import Event
from typing import Any


class CancelToken:
    """A cooperative cancellation flag."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        """Request cancellation."""

        self._event.set()

    @property
    def cancelled(self) -> bool:
        """Return whether cancellation has been requested."""

        return self._event.is_set()


class TaskStatus(str, Enum):
    """Terminal state of a task."""

    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TaskResult:
    """The outcome of a task run."""

    status: TaskStatus
    value: Any = None
    error: Exception | None = None


ProgressReporter = Callable[[int, int], None]
TaskJob = Callable[["CancelToken", ProgressReporter], Any]


def _noop_progress(done: int, total: int) -> None:
    pass


class TaskManager:
    """Runs :data:`TaskJob` callables on a background thread pool."""

    def __init__(self, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="task"
        )

    def submit(
        self,
        job: TaskJob,
        *,
        on_progress: ProgressReporter | None = None,
        on_done: Callable[[TaskResult], None] | None = None,
    ) -> CancelToken:
        """Run ``job`` in the background and return its cancel token.

        ``on_progress`` and ``on_done`` are invoked from the worker thread.
        """

        token = CancelToken()
        reporter = on_progress or _noop_progress

        def _run() -> None:
            try:
                value = job(token, reporter)
            except Exception as error:  # noqa: BLE001 - surfaced via TaskResult
                result = TaskResult(TaskStatus.FAILED, error=error)
            else:
                status = (
                    TaskStatus.CANCELLED
                    if token.cancelled
                    else TaskStatus.SUCCEEDED
                )
                result = TaskResult(status, value=value)

            if on_done is not None:
                on_done(result)

        self._executor.submit(_run)
        return token

    def shutdown(self) -> None:
        """Stop accepting work and drop queued tasks."""

        self._executor.shutdown(wait=False, cancel_futures=True)
