"""LLM-powered narrator that generates narrative commit messages from diffs.

Uses Ollama if available (qwen2.5-coder:1.5b or similar small model).
Gracefully falls back to structural template messages if Ollama is not running."""

import os
import subprocess
import time
import json
from pathlib import Path
from typing import Optional


def _check_ollama() -> bool:
    """Check if Ollama is available and running."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def _ollama_generate(model: str, prompt: str, timeout: int = 30) -> Optional[str]:
    """Generate text using Ollama's API."""
    import urllib.request
    import urllib.error

    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 128,
            "temperature": 0.7,
        }
    }).encode()

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "").strip()
    except Exception:
        return None


# Template message generators (fallback when no LLM available)

def get_active_window_title() -> Optional[str]:
    """Get the title of the currently active window.
    Uses pygetwindow (cross-platform). Returns None if unavailable.
    """
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            return active.title
    except Exception:
        pass
    return None


SNAPSHOT_TEMPLATES = [
    "Modified {filename}",
    "Updated {filename}",
    "Edited {filename}",
    "Changes to {filename}",
    "Work in progress on {filename}",
]


def _template_message(filepath: str, diff: str) -> str:
    """Generate a structural commit message from the diff."""
    import random

    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()

    # Count changes roughly
    lines_added = len([l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")])
    lines_removed = len([l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")])

    if lines_added == 0 and lines_removed == 0:
        return f"Saved {filename} (no substantive changes detected)"

    # File-type specific templates
    lang_map = {
        ".py": "Python",
        ".js": "JavaScript", ".jsx": "JSX", ".ts": "TypeScript", ".tsx": "TSX",
        ".rs": "Rust", ".go": "Go", ".java": "Java",
        ".md": "Markdown", ".txt": "text",
        ".css": "CSS", ".html": "HTML",
        ".json": "JSON", ".yaml": "YAML", ".toml": "TOML",
    }
    lang = lang_map.get(ext, "code")

    if lines_added > 0 and lines_removed > 0:
        return f"Modified {filename}: +{lines_added}/-{lines_removed} lines in {lang} file"
    elif lines_added > 0:
        return f"Added {lines_added} lines to {filename} ({lang})"
    elif lines_removed > 0:
        return f"Removed {lines_removed} lines from {filename} ({lang})"

    return f"Updated {filename}"


def generate_message(filepath: str, current_content: str,
                     previous_content: Optional[str] = None,
                     previous_message: Optional[str] = None,
                     window_title: Optional[str] = None,
                     model: str = "qwen2.5-coder:1.5b") -> str:
    """Generate a narrative commit message for a file change.

    Uses Ollama if available; falls back to template messages.

    Args:
        filepath: Absolute path to the file.
        current_content: The file's current contents.
        previous_content: The file's contents at last snapshot (if any).
        previous_message: The previous commit message (for continuity).
        window_title: Title of the active window when the snapshot was taken.
        model: Ollama model to use.

    Returns:
        A commit message string.
    """
    filename = os.path.basename(filepath)

    # If no previous version, it's a first snapshot
    if previous_content is None:
        msg = f"Initial snapshot of {filename}"
        if window_title:
            msg += f" — working in {window_title}"
        return msg

    # Generate a simple diff summary
    diff_lines = []
    current_lines = current_content.splitlines(keepends=True)
    prev_lines = previous_content.splitlines(keepends=True)

    # Simple line-by-line diff (not as sophisticated as real git diff, but fast)
    import difflib
    diff = list(difflib.unified_diff(prev_lines, current_lines,
                                     fromfile=f"a/{filename}", tofile=f"b/{filename}",
                                     n=3))

    # Build a compact diff string
    diff_text = "".join(diff[:80])  # cap at 80 lines

    # Template fallback
    template_msg = _template_message(filepath, diff_text)

    # Try Ollama if available
    if not _check_ollama():
        return template_msg

    # Build a prompt for the LLM
    context_parts = []
    if previous_message and previous_message != template_msg:
        context_parts.append(f"Previous change: {previous_message}")
    if window_title:
        context_parts.append(f"Active window: {window_title}")

    context = " ".join(context_parts)
    if context:
        context = f"Context: {context}"

    ext = os.path.splitext(filename)[1].lower()

    prompt = f"""You are a thoughtful developer's digital diary.
Given the following code diff and context, write a single sentence that describes WHY the changes were made, in a personal, reflective style. Do NOT list what changed; explain the reason as if you were the developer.

File: {filename} ({ext})
{context}

Diff:
```diff
{diff_text[:2000]}
```

Write one sentence explaining why you made these changes:"""

    llm_message = _ollama_generate(model, prompt)
    if llm_message and len(llm_message) > 10:
        return llm_message[:200]  # cap length

    return template_msg
