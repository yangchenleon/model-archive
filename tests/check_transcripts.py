from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for bv in ["BV1caui68EcR", "BV1cob76FEdG"]:
    txt_files = list((ROOT / "outputs" / "season-4951163" / "videos" / bv / "transcript").glob("*.txt"))
    for tf in txt_files:
        print(f"\n==================== {bv} : {tf.name} ====================")
        content = tf.read_text(encoding="utf-8")
        print(content[:1500])
        print("...\n" + content[-1000:])
