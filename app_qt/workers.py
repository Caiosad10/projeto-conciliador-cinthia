# app_qt/workers.py — QThread robusta (failed sempre emitido; sem thread órfã)
from __future__ import annotations

import inspect
import traceback
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)


class WorkerRunnable(QRunnable):
    def __init__(self, fn: Callable, args, kwargs, signals: WorkerSignals):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._sig = signals
        self.setAutoDelete(True)

    def run(self):
        try:
            try:
                params = inspect.signature(self._fn).parameters
                has_pb = "progress_cb" in params
            except (TypeError, ValueError):
                has_pb = False
            if has_pb:
                res = self._fn(*self._args, **self._kwargs,
                               progress_cb=self._sig.progress.emit)
            else:
                res = self._fn(*self._args, **self._kwargs)
            self._sig.finished.emit(res)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            try:
                self._sig.failed.emit(f"{type(e).__name__}: {e}")
            except Exception:
                pass


def run_in_thread(parent, fn: Callable, on_ok, on_err=None,
                  on_progress=None, *args, **kwargs):
    """Roda fn no pool global; callbacks executam na thread da UI via Signal."""
    sig = WorkerSignals(parent)
    if on_ok is not None:
        sig.finished.connect(on_ok)
    else:
        sig.finished.connect(lambda _o: None)
    if on_err:
        sig.failed.connect(on_err)
    else:
        sig.failed.connect(lambda m: print(f"[worker] {m}"))
    if on_progress:
        sig.progress.connect(on_progress)
    QThreadPool.globalInstance().start(WorkerRunnable(fn, args, kwargs, sig))
    return sig


class LegacyWorker(QObject):
    """Mantido p/ compat: mesma API antiga baseada em QThread explícita."""

    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._thread: QThread | None = None

    def run(self):
        try:
            try:
                has_pb = "progress_cb" in inspect.signature(self._fn).parameters
            except (TypeError, ValueError):
                has_pb = False
            if has_pb:
                res = self._fn(*self._args, **self._kwargs,
                               progress_cb=self.progress.emit)
            else:
                res = self._fn(*self._args, **self._kwargs)
            self.finished.emit(res)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.failed.emit(f"{type(e).__name__}: {e}")

