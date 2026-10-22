import json
import os
import sys

# Ensure root directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.download_bilibili import _yt_dlp, _run

target_bvs = ["BV1caui68EcR", "BV1cob76FEdG"]

for bv in target_bvs:
    url = f"https://www.bilibili.com/video/{bv}"
    cmd = _yt_dlp() + ["--dump-single-json", "--skip-download", url]
    out = _run(cmd).stdout
    data = json.loads(out)
    print(f"BV: {bv}")
    print(f"Title: {data.get('title')}")
    print(f"Upload Date: {data.get('upload_date')}")
    print(f"Duration: {data.get('duration')}s")
    print(f"Description: {data.get('description')}")
    print("=" * 60)
