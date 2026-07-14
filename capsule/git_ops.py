"""Git operations for timecapsule.

Manages a dedicated hidden repository at ~/.capsule/timecapsule.git.
Each tracked file gets its own orphan branch named after its canonical path.
This keeps the user's real .git untouched and makes cleanup trivial.

Uses git command-line calls for low-level operations since gitpython's
LooseObjectDB doesn't handle bare repo blob creation well across versions."""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import git

CAPSULE_DIR = Path.home() / ".capsule"
REPO_PATH = CAPSULE_DIR / "timecapsule"


def _branch_name(filepath: str) -> str:
    """Derive a branch name from a file path.

    Converts a path like:
      C:/Users/ngugi/project/main.py
    to:
      home-ngugi-project-main-py (safe for git refs).
    """
    abs_path = os.path.normpath(os.path.abspath(filepath))
    parts = []
    for p in Path(abs_path).parts:
        if ":" in p:
            continue
        sanitized = re.sub(r"[^\w-]", "-", p.lower().strip("-"))
        if sanitized:
            parts.append(sanitized)
    name = "-".join(parts)
    return name[:250]


def _git(*args: str, env: Optional[dict] = None, _input: Optional[str] = None) -> str:
    """Run a git command in the timecapsule repo."""
    cmd = ["git", "--git-dir", str(REPO_PATH)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, input=_input,
        env={**os.environ, **(env or {})},
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def ensure_repo() -> git.Repo:
    """Create and return the timecapsule bare repository."""
    CAPSULE_DIR.mkdir(parents=True, exist_ok=True)
    if not (REPO_PATH / "HEAD").exists():
        repo = git.Repo.init(str(REPO_PATH), bare=True)
    else:
        repo = git.Repo(str(REPO_PATH))
    return repo


def snapshot_file(filepath: str, message: str, repo: git.Repo) -> Optional[str]:
    """Snapshot a file's current state into its orphan branch.

    Creates a tree object from the file and commits it as a new root
    commit on the file's orphan branch. If the branch already exists,
    the commit becomes a child of the previous tip.

    Returns the commit hexsha or None on failure.
    """
    abs_path = os.path.normpath(os.path.abspath(filepath))
    if not os.path.isfile(abs_path):
        return None

    branch = _branch_name(abs_path)
    rel_path = os.path.basename(abs_path)

    # Create blob via hash-object
    blob_hash = _git("hash-object", "-w", abs_path)

    # Create tree with the blob
    # git mktree expects: mode SP type SP hash TAB path
    tree_input = f"100644 blob {blob_hash}\t{rel_path}\n"
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write(tree_input)
        tree_path = f.name

    try:
        tree_hash = _git("mktree", "--missing", _input=open(tree_path, "r").read())
    finally:
        os.unlink(tree_path)

    # Get parent commit if branch exists
    parent = None
    try:
        parent = _git("rev-parse", f"refs/heads/{branch}")
    except RuntimeError:
        pass

    # Create commit
    env = {
        "GIT_AUTHOR_NAME": "timecapsule",
        "GIT_AUTHOR_EMAIL": "capsule@localhost",
        "GIT_COMMITTER_NAME": "timecapsule",
        "GIT_COMMITTER_EMAIL": "capsule@localhost",
    }

    commit_args = ["commit-tree", tree_hash, "-m", message]
    if parent:
        commit_args.extend(["-p", parent])

    commit_hash = _git(*commit_args, env=env)

    # Update branch ref
    _git("update-ref", f"refs/heads/{branch}", commit_hash)

    return commit_hash


def get_timeline(filepath: str, repo: git.Repo, max_count: int = 50) -> list[dict]:
    """Get the commit history for a file's branch.

    Returns list of {hexsha, message, committed_datetime, author}.
    """
    branch = _branch_name(filepath)
    try:
        commits = list(repo.iter_commits(branch, max_count=max_count))
    except (ValueError, git.BadName):
        return []

    results = []
    for c in commits:
        results.append({
            "hexsha": c.hexsha,
            "message": c.message.strip(),
            "committed_datetime": c.committed_datetime.isoformat(),
            "committed_timestamp": c.committed_datetime.timestamp(),
            "author": str(c.author),
        })
    return results


def get_file_at_commit(filepath: str, commit_hexsha: str, repo: git.Repo) -> Optional[str]:
    """Retrieve file contents at a given commit."""
    branch = _branch_name(filepath)
    rel_path = os.path.basename(filepath)
    try:
        return repo.git.show(f"{commit_hexsha}:{rel_path}")
    except git.GitCommandError:
        return None


def list_tracked_files(repo: git.Repo) -> list[str]:
    """List all files that have been snapshot (by their branch names)."""
    refs = repo.git.for_each_ref("refs/heads/", format="%(refname:short)").splitlines()
    return [r for r in refs if r.strip()]
