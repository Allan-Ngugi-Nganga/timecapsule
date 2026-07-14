"""Quick smoke test for timecapsule core."""

import os
import tempfile
from capsule.git_ops import ensure_repo, snapshot_file, get_timeline, _branch_name
from capsule.store import TimelineStore
from capsule.narrator import _template_message

# Test branch name generation
bn = _branch_name("C:/Users/ngugi/project/main.py")
print("Branch name:", bn)

# Test repo init
repo = ensure_repo()
print("Repo exists:", os.path.isdir(str(repo.git_dir)))

# Test snapshot
tmp = os.path.join(tempfile.gettempdir(), "capsule_test.txt")
with open(tmp, "w") as f:
    f.write("Hello, timecapsule!\n")

sha = snapshot_file(tmp, "Initial snapshot of test file", repo)
print("Snapshot 1:", sha)

# Second snapshot
with open(tmp, "a") as f:
    f.write("Second line added.\n")

with open(tmp, "r") as f:
    current = f.read()

# Read previous content (need to re-read before writing)
# Actually, let's just write the second version:
with open(tmp, "w") as f:
    f.write("Hello, timecapsule!\nSecond line added.\n")

sha2 = snapshot_file(tmp, "Added second line to test file", repo)
print("Snapshot 2:", sha2)

# Test template message
msg = _template_message(tmp, "+1 line")
print("Template msg:", msg)

# Test timeline
tl = get_timeline(tmp, repo)
print("Timeline entries:", len(tl))
for t in tl:
    h = t["hexsha"][:8]
    m = t["message"][:50]
    print(f"  {h} {m}")

# Test store
bn = _branch_name(tmp)
store = TimelineStore()
store.record_snapshot(tmp, sha or "abc123", "Test snapshot", bn)
print("Store count:", store.total_snapshots())

with open(tmp, "r") as f:
    final_content = f.read()
print("File content:\n", final_content)

os.remove(tmp)
print("OK")
