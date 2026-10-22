import json
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SUMMARY_FILE = ROOT / "outputs" / "season-4951163" / "batch" / "summary.json"

with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
    summary = json.load(f)

# Update completed list with BV1caui68EcR (pos 48), BV1Hmbo6BELG (pos 49), BV1cob76FEdG (pos 50)
existing_completed = {item["video_id"]: item for item in summary.get("completed", [])}

new_entries = [
    {
        "position": 48,
        "video_id": "BV1caui68EcR",
        "title": "【胶圈往事】盘点那些早期就领先于万代的KO类高达模型！",
        "media": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "video" / "BV1caui68EcR.mp4"),
        "audio": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "audio" / "BV1caui68EcR.wav"),
        "transcript": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "transcript" / "BV1caui68EcR.json"),
        "transcript_txt": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "transcript" / "【胶圈往事】盘点那些早期就领先于万代的KO类高达模型！.txt"),
        "csv": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "csv" / "【胶圈往事】盘点那些早期就领先于万代的KO类高达模型！.csv")
    },
    {
        "position": 49,
        "video_id": "BV1Hmbo6BELG",
        "title": "传奇落幕？盘点星动出过的所有模型！【第一期】",
        "media": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1Hmbo6BELG" / "video" / "BV1Hmbo6BELG.mp4"),
        "audio": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1Hmbo6BELG" / "audio" / "BV1Hmbo6BELG.wav"),
        "transcript": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1Hmbo6BELG" / "transcript" / "BV1Hmbo6BELG.json"),
        "transcript_txt": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1Hmbo6BELG" / "transcript" / "传奇落幕？盘点星动出过的所有模型！【第一期】.txt"),
        "csv": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1Hmbo6BELG" / "csv" / "传奇落幕？盘点星动出过的所有模型！【第一期】.csv")
    },
    {
        "position": 50,
        "video_id": "BV1cob76FEdG",
        "title": "盘点星动的独角兽换色大全！星动系列全盘点【第二期】",
        "media": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1cob76FEdG" / "video" / "BV1cob76FEdG.mp4"),
        "audio": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1cob76FEdG" / "audio" / "BV1cob76FEdG.wav"),
        "transcript": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1cob76FEdG" / "transcript" / "BV1cob76FEdG.json"),
        "transcript_txt": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1cob76FEdG" / "transcript" / "盘点星动的独角兽换色大全！星动系列全盘点【第二期】.txt"),
        "csv": str(ROOT / "outputs" / "season-4951163" / "videos" / "BV1cob76FEdG" / "csv" / "盘点星动的独角兽换色大全！星动系列全盘点【第二期】.csv")
    }
]

for entry in new_entries:
    existing_completed[entry["video_id"]] = entry

# Also check Pos 1, 2, 3 in existing_dirs
from tools.pipeline import safe_filename
import glob

for pos, bv in [(1, "BV1bJXSYZE3z"), (2, "BV1U99QYKEMQ"), (3, "BV1wjXrYZES4")]:
    if bv not in existing_completed:
        vdir = ROOT / "outputs" / "season-4951163" / "videos" / bv
        csvs = list((vdir / "csv").glob("*.csv"))
        txts = list((vdir / "transcript").glob("*.txt"))
        if csvs and txts:
            title = txts[0].stem
            existing_completed[bv] = {
                "position": pos,
                "video_id": bv,
                "title": title,
                "media": str(vdir / "video" / f"{bv}.mp4"),
                "audio": str(vdir / "audio" / f"{bv}.wav"),
                "transcript": str(vdir / "transcript" / f"{bv}.json"),
                "transcript_txt": str(txts[0]),
                "csv": str(csvs[0])
            }

completed_list = sorted(existing_completed.values(), key=lambda x: x["position"])

summary["total"] = 50
summary["selected"] = 50
summary["completed"] = completed_list

with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"Summary updated! Total completed: {len(completed_list)}")
