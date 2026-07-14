"""Watchdog-based file watcher with idle debounce.

Tracks per-file modification times. When a file hasn't been touched
for IDLE_SECONDS, fires a snapshot callback for that file."""

import os
import time
import threading
from pathlib import Path
from typing import Callable, Set

from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
from watchdog.observers import Observer

IDLE_SECONDS = 120  # 2 minutes of inactivity triggers a snapshot


class IdleTracker:
    """Per-file idle timer."""

    def __init__(self, idle_seconds: int = IDLE_SECONDS):
        self._idle_seconds = idle_seconds
        self._last_event: dict[str, float] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._pending: Set[str] = set()
        self._callback: Callable[[str], None] | None = None

    def set_callback(self, cb: Callable[[str], None]):
        self._callback = cb

    def touch(self, path: str):
        """Record a file modification event."""
        norm = os.path.normpath(path)
        with self._lock:
            self._last_event[norm] = time.monotonic()
            self._pending.add(norm)
        self._schedule_check()

    def _schedule_check(self):
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
        self._timer = threading.Timer(self._idle_seconds, self._check_idle)
        self._timer.daemon = True
        self._timer.start()

    def _check_idle(self):
        now = time.monotonic()
        ready: list[str] = []
        with self._lock:
            still_pending: Set[str] = set()
            for p in list(self._pending):
                last = self._last_event.get(p, 0)
                if now - last >= self._idle_seconds:
                    ready.append(p)
                else:
                    still_pending.add(p)
            self._pending = still_pending
        if self._callback:
            for p in ready:
                try:
                    self._callback(p)
                except Exception:
                    pass
        # Re-check if anything's still pending
        with self._lock:
            if self._pending:
                self._schedule_check()


class CapsuleEventHandler(FileSystemEventHandler):
    """Dispatches file changes to the idle tracker."""

    def __init__(self, tracker: IdleTracker, watch_extensions: set[str] | None = None):
        self.tracker = tracker
        self.watch_ext = watch_extensions or {".py", ".js", ".ts", ".rs", ".go", ".md",
                                               ".txt", ".json", ".yaml", ".toml", ".css",
                                               ".html", ".jsx", ".tsx", ".java", ".c", ".cpp",
                                               ".h", ".sh", ".ps1", ".bat", ".sql", ".rb",
                                               ".php", ".swift", ".kt", ".scala", ".zig"}

    def _should_watch(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in self.watch_ext and not os.path.basename(path).startswith(".")

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory and self._should_watch(event.src_path):
            self.tracker.touch(event.src_path)

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory and self._should_watch(event.src_path):
            self.tracker.touch(event.src_path)


class FileWatcher:
    """High-level watcher that monitors directories and fires snapshot callbacks."""

    def __init__(self, paths: list[str], snapshot_callback: Callable[[str], None],
                 idle_seconds: int = IDLE_SECONDS):
        self.paths = [os.path.abspath(p) for p in paths]
        self.tracker = IdleTracker(idle_seconds=idle_seconds)
        self.tracker.set_callback(snapshot_callback)
        self.handler = CapsuleEventHandler(self.tracker)
        self.observer = Observer()

    def start(self):
        for p in self.paths:
            if os.path.isdir(p):
                self.observer.schedule(self.handler, p, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join(timeout=5)
        if self.tracker._timer and self.tracker._timer.is_alive():
            self.tracker._timer.cancel()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
