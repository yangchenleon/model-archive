from pathlib import Path
import time

for p in sorted(Path("outputs/classified").glob("*.csv")):
    mtime = p.stat().st_mtime
    print(f"{time.strftime('%H:%M:%S', time.localtime(mtime))} | {p.name:25s} | size={p.stat().st_size}")
