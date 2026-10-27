"""V3 extraction: the simplest possible product-mention extractor.

No stage enum, no field splitting, no domain vocabulary. The model reports what
the video says: brand, the product name as written, the status phrase as spoken,
price/date if present, and the supporting quote. Identity is deliberately left
to a later exact-match step.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.config import load_env
from tools.extract_daily_news import call_llm_json

load_env()

PROMPT = """你是模玩（拼装模型、成品机甲、可动人偶、特摄周边）资讯的信息提取器。
输入是 B 站模玩速报视频的字幕文本，口播里常有同音错别字，请结合上下文纠正名称，但不要改变产品身份。

背景常识：
- GK 是一种套件类型，不是厂牌，不要放进 brand。
- "新厂""某厂""某工作室""某博主""某经典老厂""不知名小厂""隔壁小厂"都不是品牌名：未具名时 brand 留空，不要把这类描述词填进 brand，也不要借用视频里其他厂的名字。
- KO 指第三方厂商对万代（或寿屋等）机体的翻模、放大、仿制、国服版本，常见厂牌：大班、高高、长龙、猛虎、神兽、天硕、爆闪、福风、真飞鸟、匠造方、高师傅、高甲厂、XT厂、波塞冬、胖虎、聚匠、野牛、HN、御膳房、模工坊、瘦虎、华夏、乐模汇、ELS。
  KO 机体的原型是万代 IP（牛高达、独角兽、菲尼克斯、巴巴托斯、脉冲…），但 brand 必须是做这台 KO 的厂，**不是万代**。
- 万代只用于明确是官方发布的情况：句中出现"万代/阿代/代哥/阿代叔/隔壁不知名小厂"且讲的是官方线（MGEX、RG、PGU、MGSD、MB、MR魂、SHF、真骨雕、解体匠机、30MM），或给出日元定价、日服/高达基地等官方渠道。
  反讽的"隔壁不知名小厂""某不知名小厂"仍指万代，不要因为带"小厂"就留空。
- 价格与品牌互相印证：几十元餐券 + 国产厂名 = 第三方 KO；两万日元级定价基本是万代官方。
- 规格词（MGEX、RG、PGU、MGSD、MB、MR魂、SHF…）只代表系列/比例，**不是品牌**；第三方厂同样会用这些规格名做 KO。
- 字幕是 OCR 产物，"7"常是"了"的误识（"更新7MGEX"=更新了 MGEX，"直接7"=直接了），按"了"理解，不要把 7 当成品牌或型号编号。
- "班爷""班叔""班班""大班叔叔"都指大班；"阿代""代哥""代哥"通常指万代（B社在官方语境下也指万代，但十元级 SDCS 这类低价品要怀疑是第三方）。
- 大林/大林模型 以配件包为主："大林配件包"里"配件包"是产品类型，brand 应为"大林"。
- 第X弹、第X系列属于批次/系列，放 line，不要放 variant。

每个条目输出：
- brand：厂商名，只填厂商；空则留空字符串
- line：产品线/规格/批次（MG、RG、PGU、MGSD、1比60拼装、超动骑兵系列、第二弹…），没有就留空
- product：产品基础名称（机体/角色/型号），只保留名词，不含版本词和动词
- variant：版本/配色/换色/限定/套装等修饰（电镀银、海涅配色、进阶装、PB限定、战损配件包…），没有就留空
- status：产品当前生命周期状态，只能取以下值之一
  rumor（传闻/爆料）、teaser（灰模/试模/剪影/官图）、announced（公布/解禁/登场）、
  preorder（预售/开订/定金/先行）、released（现货/大货/发售/上线）、
  reprint（再版/复刻）、discontinued（停产/停售）、unknown
- price：价格，只保留数字和单位，没有就留空
- detail：其他描述性信息（测评、延期、配件、玩法、价格波动、评价等），不要塞进上面任何字段
- evidence：支撑该条目的原文片段，不超过 40 字

规则：
1. 只提取具体产品，不提取品牌动态、市场评论、纯个人感受。
2. 同一产品在同一条文本里多次出现，合并成一条。
3. product 必须是纯名词短语，不含动词、感叹、状态词；版本/配色一律进 variant。
4. brand 与 product 边界要清楚：厂商名只出现在 brand，系列名只出现在 line。
5. status 只能从枚举里选；拿不准选 unknown。若本条只是延期/测评/价格变动，status 按产品当前阶段判断，
   判断不了选 unknown，不要用 reprint 代替"修复"。
6. 不确定就留空，不要猜测。
7. 福利/抽奖/掉落/赠品内容不是产品资讯：出现"掉落""模型掉落""抽奖""福利""赠送""开奖""上车""赏池""粉丝福利"等词的段落，
   整段不要提取（句中出现"万代"也一样）；"包含了 A、B、C"这种罗列通常是赠品清单，也不要拆成产品条目。
   "由 XX 带来 A、B、C 的模型掉落"这类用"带来"包装的赠品清单同样整段丢弃。
8. 广告/带货/店铺引流（"XX 家上新""链接在橱窗"等）同样不提取。
9. 句子里点名了第三方厂（大班、高高、长龙、猛虎、神兽、天硕、爆闪、福风、真飞鸟、匠造方、高师傅、高甲厂、XT厂、波塞冬、胖虎、聚匠、野牛、HN、御膳房、模工坊、瘦虎、华夏、乐模汇…）时，
   brand 必须是这个厂；即使产品名带 MGEX/RG/PGU/MGSD/MB 等万代规格词，也不要因为机体原型是万代 IP 就写"万代"，规格词只进 line。
10. KO/翻模/放大/国服版本但没有点名厂商（"某博主公布KO版…""国服KO版…"）时，brand 留空，不要填"万代"，也不要借别的厂名。
11. 同一段连续介绍的多个产品，如果中间没有出现新的厂名，就沿用上一个厂；换到新段落或出现新厂名后再切换。
   例："你长龙叔叔带来放大RG福风牛…与此同时产能爆炸还更新MGEX黑金菲尼克斯" → 两条的 brand 都是长龙（后一条即使带 MGEX 也沿用长龙）；
   "MGSD大青椒刹帝利…由 Anubis 带来刹帝利格林炮改件" → 前者是万代，后者是 Anubis。
12. evidence 必须是字幕原文里的连续片段。如果找不到原文依据，说明该条目是凭常识补出来的，不要输出。
13. 输出前逐条自检：① evidence 能否在字幕原文中逐字找到？不能就删掉这一条；② 这一条是否来自掉落/抽奖/福利/赏池段落？是就删掉。

只返回纯 JSON：
{"items": [{"brand": "", "line": "", "product": "", "variant": "", "status": "unknown", "price": "", "detail": "", "evidence": ""}]}

视频日期：@@DATE@@
字幕文本：
@@TEXT@@
"""


def build_prompt(text: str, date: str) -> str:
    return PROMPT.replace("@@DATE@@", date).replace("@@TEXT@@", text)


# The prompt forbids giveaway segments, but the model still emits rows from
# "模型掉落" lists. A deterministic guard is cheaper than another prompt round:
# only 5 / 914 extractions ever matched, and all five were genuine giveaways.
GIVEAWAY = re.compile(r"掉落|抽奖|福利|赠送|开奖|上车|赏池")


def _near_giveaway(text: str, product: str) -> bool:
    """A product listed inside a giveaway sentence may quote only its own name,
    so check the short window right after the product name. Keep it tight: a
    giveaway list ends with "…的模型掉落" a few characters later, while a normal
    entry puts a price/release phrase there instead.
    """
    key = (product or "")[:4]
    if not key or not GIVEAWAY.search(text):
        return False
    position = text.find(key)
    if position < 0:
        return False
    return bool(GIVEAWAY.search(text[max(0, position - 20):position + 40]))


def clean_items(payload: dict[str, Any], text: str = "") -> list[dict[str, Any]]:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise RuntimeError(f"unexpected LLM payload: {str(payload)[:200]}")
    cleaned: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        evidence = str(raw.get("evidence") or "").strip()
        if not evidence or GIVEAWAY.search(evidence):
            continue
        brand = str(raw.get("brand") or "").strip()
        product = str(raw.get("product") or "").strip()
        if not brand or not product:
            continue
        if _near_giveaway(text, product):
            continue
        cleaned.append({
            "brand": brand,
            "line": str(raw.get("line") or "").strip(),
            "product": product,
            "variant": str(raw.get("variant") or "").strip(),
            "status": str(raw.get("status") or "unknown").strip().lower(),
            "price": str(raw.get("price") or "").strip(),
            "detail": str(raw.get("detail") or "").strip()[:200],
            "evidence": evidence[:120],
        })
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reports-dir", type=Path, default=Path("outputs/daily_reports"))
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    subs = sorted(
        p for p in args.reports_dir.glob("*/subtitles/*.json")
        if not p.name.startswith("_") and args.start_date <= p.parent.parent.name[:8] <= args.end_date
    )
    if args.limit:
        subs = subs[: args.limit]
    print(f"待提取 {len(subs)} 条", flush=True)

    for index, path in enumerate(subs, 1):
        folder = path.parent.parent
        date = folder.name[:8]
        out = folder / "mentions.json"
        if out.exists() and not args.force:
            print(f"[{index}/{len(subs)}] {path.stem} 已存在，跳过", flush=True)
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = payload.get("text", "").strip()
        cues = payload.get("cues") or []
        t0 = time.time()
        try:
            items = clean_items(call_llm_json(build_prompt(text, date), temperature=0.0), text)
        except Exception as exc:
            print(f"[{index}/{len(subs)}] {path.stem} FAILED: {str(exc)[:160]}", flush=True)
            continue
        for item in items:
            for cue in cues:
                if item["evidence"][:6] and item["evidence"][:6] in cue["text"]:
                    item["time"] = cue["start"]
                    break
        out.write_text(json.dumps({
            "date": date,
            "video_id": path.stem.split("_")[1],
            "items": items,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index}/{len(subs)}] {path.stem} {len(items)} 条 ({time.time() - t0:.0f}s)", flush=True)
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
