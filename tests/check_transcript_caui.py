from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tf = list((ROOT / "outputs" / "season-4951163" / "videos" / "BV1caui68EcR" / "transcript").glob("*.txt"))[0]
print(tf.read_text(encoding="utf-8"))
