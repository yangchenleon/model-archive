import os
import time
from pathlib import Path

now = time.time()
root = Path(".")

print("Files modified in the last 30 minutes:")
exclude = {".git", ".venv", ".venv-tools", "__pycache__", "node_modules", "dist"}

for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in exclude]
    for f in filenames:
        p = Path(dirpath) / f
        try:
            mtime = p.stat().st_mtime
            if now - mtime < 1800:
                print(f"  {time.strftime('%H:%M:%S', time.localtime(mtime))} | {p}")
        except Exception:
            pass
