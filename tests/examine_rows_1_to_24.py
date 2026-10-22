import csv
from pathlib import Path

csv_path = Path("outputs/normalized/season-4951163/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for i in range(24):
    r = rows[i]
    print(f"{i+1:2d} | 厂商:{r['厂商']} | 编号:{r['产品编号']} | 来源:{r['来源类型']} | 产品线:{r['产品线']} | 模型名称:{r['模型名称']} | 版本:{r['版本/配色']}")
