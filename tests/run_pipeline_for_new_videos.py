import json
import os
import sys
from pathlib import Path

# Ensure root directory in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.config import load_env
from tools.pipeline import run

load_env()

SEASON_DIR = ROOT_DIR / "outputs" / "season-4951163"
VIDEOS_DIR = SEASON_DIR / "videos"

target_bvs = ["BV1caui68EcR", "BV1cob76FEdG"]

asr_model = os.getenv("ASR_MODEL", "qwen3-asr-flash")
llm_provider = os.getenv("LLM_PROVIDER", "openai")
llm_model = os.getenv("LLM_MODEL", "Qwen3.5-35B-A3B")
language = os.getenv("ASR_LANGUAGE", "zh")

results = []

for bv in target_bvs:
    url = f"https://www.bilibili.com/video/{bv}"
    work_dir = VIDEOS_DIR / bv
    print(f"\n==================== Processing {bv} ====================")
    print(f"URL: {url}")
    print(f"Work dir: {work_dir}")
    try:
        res = run(
            url=url,
            work_dir=work_dir,
            asr_model=asr_model,
            llm_provider=llm_provider,
            llm_model=llm_model,
            language=language,
            cookies=None,
        )
        print(f"Successfully processed {bv}:")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        results.append(res)
    except Exception as e:
        print(f"Error processing {bv}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

print("\n==================== Batch Finished ====================")
print(f"Total processed: {len(results)}/{len(target_bvs)}")
