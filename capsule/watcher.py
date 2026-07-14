"""Watchdog-based file watcher with idle debounce.

Tracks per-file modification times. When a file hasn't been touched
for IDLE_SECONDS, fires a snapshot callback for that file."""

import hashlib
import os
import time
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Optional, Set

from watchdog.events import (FileSystemEventHandler, FileModifiedEvent,
                              FileCreatedEvent, FileDeletedEvent,
                              FileMovedEvent)
from watchdog.observers import Observer

IDLE_SECONDS = 120  # 2 minutes of inactivity triggers a snapshot
RENAME_WINDOW = 5  # seconds to remember deleted files for rename matching
RENAME_SIMILARITY = 0.8  # 80% content similarity threshold for rename detection


def _content_signature(filepath: str) -> tuple[int, Optional[str]]:
    """Compute size and a fast content hash for similarity comparison."""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        size = len(data)
        # MinHash-like: hash first 1KB and last 1KB (fast, non-cryptographic)
        sample = data[:1024] + data[-1024:] if size > 2048 else data
        sig = hashlib.md5(sample).hexdigest()
        return size, sig
    except Exception:
        return 0, None


def _hash_content(content: str) -> str:
    """Hash string content for comparison."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _content_similarity(path_a: str, path_b: str) -> float:
    """Estimate content similarity between two files (0.0 to 1.0).
    Fast approach: compare MD5 of first + last KB.
    """
    size_a, sig_a = _content_signature(path_a)
    size_b, sig_b = _content_signature(path_b)
    if sig_a is None or sig_b is None:
        return 0.0
    if size_a == 0 and size_b == 0:
        return 1.0
    # Size ratio
    if size_a > 0 and size_b > 0:
        ratio = min(size_a, size_b) / max(size_a, size_b)
    else:
        ratio = 0.0
    # Signature match
    sig_match = 1.0 if sig_a == sig_b else 0.0
    # Weighted: 30% size similarity, 70% signature match
    return 0.3 * ratio + 0.7 * sig_match


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
    """Dispatches file changes to the idle tracker, with rename detection."""

    def __init__(self, tracker: IdleTracker, rename_callback: Callable[[str, str], None] | None = None,
                 watch_extensions: set[str] | None = None):
        self.tracker = tracker
        self.rename_callback = rename_callback
        self.watch_ext = watch_extensions or {".py", ".js", ".ts", ".rs", ".go", ".md",
                                               ".txt", ".json", ".yaml", ".toml", ".css",
                                               ".html", ".jsx", ".tsx", ".java", ".c", ".cpp",
                                               ".h", ".sh", ".ps1", ".bat", ".sql", ".rb",
                                               ".php", ".swift", ".kt", ".scala", ".zig"}
        # Track recently deleted files: {path: (timestamp, signature)}
        self._deleted: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._lock = threading.Lock()

    def _should_watch(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in self.watch_ext and not os.path.basename(path).startswith(".")

    def _match_rename(self, new_path: str) -> Optional[str]:
        """Check if a new file matches a recently deleted one by content."""
        now = time.monotonic()
        with self._lock:
            # Purge expired entries
            expired = [p for p, (ts, _) in self._deleted.items()
                       if now - ts > RENAME_WINDOW]
            for p in expired:
                del self._deleted[p]

            best_match = None
            best_score = RENAME_SIMILARITY

            for old_path, (_, old_sig) in self._deleted.items():
                if not os.path.isfile(new_path):
                    continue
                # Quick size check first
                sig = _content_signature(new_path)
                if sig[1] is None:
                    continue
                # Compare signatures (fast, no full file read)
                score = _content_similarity(new_path, old_path) if os.path.isfile(old_path) else 0.0
                # Use stored signature if original file gone
                if not os.path.isfile(old_path):
                    new_sig = _content_signature(new_path)[1]
                    if new_sig and new_sig == old_sig:
                        score = 0.9
                if score > best_score:
                    best_score = score
                    best_match = old_path

            if best_match:
                del self._deleted[best_match]

        return best_match

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory and self._should_watch(event.src_path):
            self.tracker.touch(event.src_path)

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory and self._should_watch(event.src_path):
            # Check for rename
            old_path = self._match_rename(event.src_path)
            if old_path and self.rename_callback:
                self.rename_callback(old_path, event.src_path)
            self.tracker.touch(event.src_path)

    def on_deleted(self, event: FileDeletedEvent):
        if not event.is_directory and self._should_watch(event.src_path):
            sig = _content_signature(event.src_path)[1]
            if sig:
                with self._lock:
                    self._deleted[event.src_path] = (time.monotonic(), sig)

    def on_moved(self, event: FileMovedEvent):
        if not event.is_directory:
            if self._should_watch(event.dest_path):
                # Direct rename — fire callback immediately
                if self.rename_callback and self._should_watch(event.src_path):
                    self.rename_callback(event.src_path, event.dest_path)
                self.tracker.touch(event.dest_path)


class FileWatcher:
    """High-level watcher that monitors directories and fires snapshot callbacks."""

    def __init__(self, paths: list[str], snapshot_callback: Callable[[str], None],
                 rename_callback: Callable[[str, str], None] | None = None,
                 idle_seconds: int = IDLE_SECONDS):
        self.paths = [os.path.abspath(p) for p in paths]
        self.tracker = IdleTracker(idle_seconds=idle_seconds)
        self.tracker.set_callback(snapshot_callback)
        self.handler = CapsuleEventHandler(self.tracker, rename_callback=rename_callback)
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
