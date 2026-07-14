"""Test daemon and renamed detection imports."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from capsule.daemon import main, watch, _rename_callback
from capsule.watcher import FileWatcher, _content_signature, _content_similarity

print("All imports OK")

# Quick similarity test
f1 = os.path.join(tempfile.gettempdir(), "test_a.py")
f2 = os.path.join(tempfile.gettempdir(), "test_b.py")
with open(f1, "w") as f:
    f.write("def hello():\n    print('hello')\n")
with open(f2, "w") as f:
    f.write("def hello():\n    print('hello world')\n")
sim = _content_similarity(f1, f2)
print(f"Similarity: {sim:.2%}")
os.remove(f1)
os.remove(f2)

print("OK")
