"""Textual TUI for browsing the time capsule timeline.

Shows tracked files, commit history for each file, and diff previews."""

import os
import time
from pathlib import Path
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, ListView, ListItem, Static, RichLog, Label

from . import git_ops
from .store import TimelineStore


class CapsuleBrowser(App):
    """Textual TUI for browsing timecapsule snapshots."""

    CSS = """
    Screen {
        background: #0a0a0a;
    }

    #layout {
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 1;
        padding: 1;
        height: 100%;
    }

    #file-list-panel {
        border: solid #00ff88;
        padding: 0 1;
        background: #0d1a12;
    }

    #file-list-panel > Label {
        text-style: bold;
        color: #00ff88;
        height: 1;
        margin-bottom: 1;
    }

    #file-list {
        height: 100%;
    }

    #timeline-panel {
        column-span: 2;
        border: solid #ff8800;
        padding: 0 1;
        background: #1a0f05;
    }

    #timeline-panel > Label {
        text-style: bold;
        color: #ff8800;
        height: 1;
        margin-bottom: 1;
    }

    #timeline-list {
        height: 100%;
    }

    #diff-panel {
        column-span: 3;
        border: solid #444;
        padding: 0 1;
        background: #0a0a0a;
        height: 100%;
    }

    #diff-panel > Label {
        color: #888;
        height: 1;
        margin-bottom: 1;
    }

    RichLog {
        background: #0a0a0a;
    }

    ListView {
        background: #0d1a12;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:nth-child(even) {
        background: #0f1f15;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.store = TimelineStore()
        self.repo = git_ops.ensure_repo()
        self._selected_file: Optional[str] = None
        self._selected_commit: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="layout"):
            with Vertical(id="file-list-panel"):
                yield Label("📁 Tracked Files")
                yield ListView(id="file-list")
            with Vertical(id="timeline-panel"):
                yield Label("📜 Timeline")
                yield ListView(id="timeline-list")
            with Vertical(id="diff-panel"):
                yield Label("📄 Diff Preview")
                yield RichLog(id="diff-view", highlight=True, markup=False)
        yield Footer()

    def on_mount(self):
        self._populate_file_list()

    def _populate_file_list(self):
        files = self.store.get_all_files()
        lv = self.query_one("#file-list", ListView)
        lv.clear()
        for f in files:
            fp = f["filepath"]
            last_msg = f.get("last_message", "")[:60]
            label = f"{os.path.basename(fp)} — {last_msg}"
            lv.append(ListItem(Label(label)))
        if files:
            lv.index = 0
            self._on_file_selected(files[0]["filepath"])

    def _on_file_selected(self, filepath: str):
        self._selected_file = filepath
        self._populate_timeline(filepath)

    def _populate_timeline(self, filepath: str):
        commits = self.store.get_timeline(filepath)
        lv = self.query_one("#timeline-list", ListView)
        lv.clear()
        for c in commits:
            dt = time.strftime("%b %d %H:%M", time.localtime(c["timestamp"]))
            msg = c["message"][:70]
            label = f"[{dt}] {msg}"
            lv.append(ListItem(Label(f"  {label}")))
        if commits:
            lv.index = 0
            self._on_commit_selected(commits[0]["hexsha"])
        else:
            diff = self.query_one("#diff-view", RichLog)
            diff.clear()
            diff.write("(no commits yet for this file)")

    def _on_commit_selected(self, hexsha: str):
        self._selected_commit = hexsha
        diff = self.query_one("#diff-view", RichLog)
        diff.clear()

        if not self._selected_file:
            diff.write("(no file selected)")
            return

        # Show the file content at this commit
        content = git_ops.get_file_at_commit(self._selected_file, hexsha, self.repo)
        if content:
            diff.clear()
            for line in content.splitlines()[:100]:
                diff.write(line)
            if len(content.splitlines()) > 100:
                diff.write("[dim]... (truncated)[/]")
        else:
            diff.write("(file content not available)")

    @on(ListView.Selected, "#file-list")
    def file_selected(self, event: ListView.Selected):
        files = self.store.get_all_files()
        if event.list_view.index is not None and event.list_view.index < len(files):
            self._on_file_selected(files[event.list_view.index]["filepath"])

    @on(ListView.Selected, "#timeline-list")
    def commit_selected(self, event: ListView.Selected):
        if not self._selected_file:
            return
        commits = self.store.get_timeline(self._selected_file)
        if event.list_view.index is not None and event.list_view.index < len(commits):
            self._on_commit_selected(commits[event.list_view.index]["hexsha"])

    def action_refresh(self):
        self._populate_file_list()


def run_browser():
    app = CapsuleBrowser()
    app.run()
