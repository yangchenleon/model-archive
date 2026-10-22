import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Read raw CSVs
caui_csv = ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "csv" / "【胶圈往事】盘点那些早期就领先于万代的KO类高达模型！.csv"
cob_csv = ROOT / "outputs" / "season-4951163" / "videos" / "BV1cob76FEdG" / "csv" / "盘点星动的独角兽换色大全！星动系列全盘点【第二期】.csv"

print("--- Raw BV1caui68EcR rows ---")
with open(caui_csv, "r", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        print(r)

print("\n--- Raw BV1cob76FEdG rows ---")
with open(cob_csv, "r", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        print(r)
