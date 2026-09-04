#!/usr/bin/env python3
"""聚合 outputs/ 下两个 season 的视频 CSV 并做标准化后处理。

处理内容（规则见 tools/normalize_rules.csv，可编辑后重跑）：
1. 厂商名对齐：ASR 转译变体统一为标准名（如 吉模社/吉摩社/极模社/万模会/叉叉模型 -> 集模社）。
2. 模型名对齐：同一机体的多种音译写法统一（如 翼端/一端/一段 -> 异端）。
3. 版本/配色拆分：合并了多个版本/配色的条目按枚举拆分为多行（描述性短语除外，见拆分例外）。
4. 回溯：输出带命中统计的转换表 mapping-table.csv 与待人工确认清单 review-pending.csv。

输出（outputs/normalized/）：
- products-season-4852205.csv      season-4852205 聚合表（按厂商排序）
- season-4951163/<厂牌或主题>.csv  season-4951163 按分P厂牌/主题分组输出（分组配置见
                                   tools/partition-4951163.csv；同一分P的条目始终在同一张表，
                                   多期合并如 大班-88 / 大班-66 / 高高-HG）
- mapping-table.csv                实际应用的转换表（原音译名 -> 标准化名 + 命中次数 + 依据）
- review-pending.csv               疑似未对齐但未自动处理的候选，供人工校验

用法：
    python3 tools/normalize_products.py
    python3 tools/normalize_products.py --rules tools/normalize_rules.csv --out-dir outputs/normalized
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ["厂商", "产品编号", "来源类型", "产品线", "模型名称", "版本/配色", "详情", "资料来源"]
SEASONS = ["season-4852205", "season-4951163"]

# 单字母空格序列合并（"A E U" -> "AEU"、"O O Q" -> "OOQ"、"H i r m" -> "Hirm"）
LETTER_SEQ = re.compile(r"\b([A-Za-z](?:[ \t]+[A-Za-z]\b)+)")


def normalize_text(s: str) -> str:
    s = s.strip()
    prev = None
    while prev != s:
        prev = s
        s = LETTER_SEQ.sub(lambda m: re.sub(r"[ \t]+", "", m.group(1)), s)
    return s


class Rule:
    __slots__ = ("rtype", "scope", "field", "pattern", "replacement", "note", "hits", "examples")

    def __init__(self, rtype, scope, field, pattern, replacement, note):
        self.rtype = rtype
        self.scope = scope
        self.field = field
        self.pattern = pattern
        self.replacement = replacement
        self.note = note
        self.hits = 0
        self.examples = []

    def record(self, ctx_desc):
        self.hits += 1
        if len(self.examples) < 3:
            self.examples.append(ctx_desc)


def load_rules(path):
    rules = []
    with open(path, encoding="utf-8-sig", newline="") as fp:
        for row in csv.DictReader(fp):
            rules.append(Rule(
                row["rule_type"].strip(),
                row["scope"].strip(),
                row["field"].strip(),
                row["pattern"].strip(),
                row["replacement"].strip(),
                (row.get("note") or "").strip(),
            ))
    return rules


def scope_match(rule: Rule, bv: str, mfg: str, model: str = "") -> bool:
    """作用域支持 & 组合（如 BV:xxx&模型:A;B）；模型: 可用分号分隔多个候选。"""
    for part in rule.scope.split("&"):
        part = part.strip()
        if not part or part == "全局":
            continue
        if part.startswith("BV:"):
            if bv != part[3:].strip():
                return False
        elif part.startswith("厂商:"):
            if mfg not in [x.strip() for x in part[3:].split(",")]:
                return False
        elif part.startswith("模型:"):
            if model not in [x.strip() for x in re.split(r"[;,:]", part[3:]) if x.strip()]:
                return False
        else:
            return False
    return True


def replace_word(text: str, pattern: str, replacement: str) -> str:
    """防过度替换：pattern 是 replacement 的子串时（如 巴托斯->巴巴托斯），
    先保护文本中已正确的 replacement 再替换，避免 巴巴托斯->巴巴巴托斯。"""
    if pattern in replacement:
        protected = text.replace(replacement, "\x00")
        protected = protected.replace(pattern, replacement)
        return protected.replace("\x00", replacement)
    return text.replace(pattern, replacement)


def apply_mfg_rules(row, bv, rules):
    """厂商映射：精确匹配。"""
    mfg = row["厂商"]
    for rule in rules:
        if rule.rtype != "厂商映射" or mfg != rule.pattern:
            continue
        if scope_match(rule, bv, mfg, row["模型名称"]):
            rule.record(f"{bv} {mfg}->{rule.replacement}")
            mfg = rule.replacement
    row["厂商"] = mfg
    return row


def apply_productline_rules(row, bv, rules):
    """产品线映射：精确匹配（如 熊猫模型产品线「元素」->「元祖」）。"""
    line = row["产品线"]
    for rule in rules:
        if rule.rtype != "产品线映射" or line != rule.pattern:
            continue
        if scope_match(rule, bv, row["厂商"], row["模型名称"]):
            rule.record(f"{bv} {row['厂商']}|{line}->{rule.replacement}")
            line = rule.replacement
    row["产品线"] = line
    return row


def apply_model_rules(row, bv, rules):
    """模型名映射：先精确（含厂商作用域），后词替换（按 pattern 长度降序），
    最后再补一轮精确匹配（处理词替换产物，如 风铃->风灵->风灵高达）。"""
    name = row["模型名称"]

    def exact_pass(n):
        for rule in rules:
            if rule.rtype != "模型名精确" or n != rule.pattern:
                continue
            if scope_match(rule, bv, row["厂商"], n):
                rule.record(f"{bv} {row['厂商']}|{n}->{rule.replacement}")
                n = rule.replacement
        return n

    name = exact_pass(name)
    word_rules = [r for r in rules if r.rtype == "模型名词替换"]
    for rule in sorted(word_rules, key=lambda r: -len(r.pattern)):
        if rule.pattern in name:
            new_name = replace_word(name, rule.pattern, rule.replacement)
            rule.record(f"{bv} {row['厂商']}|{name}->{new_name}")
            name = new_name
    name = exact_pass(name)
    row["模型名称"] = name
    return row


SPLIT_EXCEPTIONS = set()
PROMOTE_MAP = {}


def should_split(value: str) -> bool:
    return value in SPLIT_EXCEPTIONS


def split_versions(value: str):
    """按分隔符拆分版本/配色枚举；顿号/逗号优先，否则斜杠。"""
    if any(sep in value for sep in "、，,"):
        parts = re.split(r"[、，,]", value)
    elif "/" in value:
        parts = value.split("/")
    else:
        return [value]
    parts = [p.strip() for p in parts if p.strip()]
    return parts or [value]


def apply_version_rules(value: str, bv: str, mfg: str, model: str, rules):
    """版本值映射：先词替换，后精确清理（拆分后应用）。scope 可用 模型: 限定具体机体。"""
    for rule in sorted([r for r in rules if r.rtype == "版本值词替换"], key=lambda r: -len(r.pattern)):
        if rule.pattern in value:
            new_value = replace_word(value, rule.pattern, rule.replacement)
            rule.record(f"{bv} {mfg}|{value}->{new_value}")
            value = new_value
    for rule in rules:
        if rule.rtype != "版本值精确" or value != rule.pattern:
            continue
        if scope_match(rule, bv, mfg, model):
            rule.record(f"{bv} {mfg}|{value}->{rule.replacement}")
            value = rule.replacement
    return value


def apply_detail_rules(row, bv, rules):
    """详情词替换：人工校验确认的 ASR 误译（仅逐词替换，不改写其余原文）。"""
    for rule in sorted([r for r in rules if r.rtype == "详情词替换"], key=lambda r: -len(r.pattern)):
        if rule.pattern in row["详情"]:
            new_detail = replace_word(row["详情"], rule.pattern, rule.replacement)
            rule.record(f"{bv} {row['厂商']}|详情:{rule.pattern}->{rule.replacement}")
            row["详情"] = new_detail
    return row


# 待人工确认清单：(类别, 关键词, 匹配字段, 问题说明)；匹配字段：厂商/模型/版本
# 历批人工校验已全部落地到规则表，暂无新增待确认项
PENDING_SPECS = []


def collect_rows():
    """读取两个 season 的所有 CSV，保持 season 内按 BV/文件顺序。"""
    seasons = {}
    for season in SEASONS:
        rows = []
        pattern = os.path.join(ROOT, "outputs", season, "videos", "*", "csv", "*.csv")
        for path in sorted(glob.glob(pattern)):
            bv = os.path.basename(os.path.dirname(os.path.dirname(path)))
            with open(path, encoding="utf-8-sig", newline="") as fp:
                for i, r in enumerate(csv.DictReader(fp)):
                    r = {k: (v or "").strip() for k, v in r.items()}
                    r["_bv"] = bv
                    r["_src"] = os.path.basename(path)
                    r["_idx"] = i
                    rows.append(r)
        seasons[season] = rows
    return seasons


def process_season(rows, rules):
    out = []
    split_count = 0
    promote_count = 0
    for row in rows:
        bv = row["_bv"]
        # 1) 文本规范化
        for f in ("厂商", "产品线", "模型名称", "版本/配色"):
            row[f] = normalize_text(row[f])
        # 2) 厂商映射
        row = apply_mfg_rules(row, bv, rules)
        # 2.5) 产品线映射
        row = apply_productline_rules(row, bv, rules)
        # 3) 模型名映射
        row = apply_model_rules(row, bv, rules)
        # 3.5) 详情词替换
        row = apply_detail_rules(row, bv, rules)

        version = row["版本/配色"]
        base = {f: row[f] for f in FIELDS}
        base["_bv"] = bv

        # 4) 版本/配色拆分
        if version and not should_split(version):
            parts = split_versions(version)
            if len(parts) > 1:
                split_count += 1
                for p in parts:
                    new_row = dict(base)
                    new_row["_bv"] = bv
                    if p in PROMOTE_MAP:
                        # 混入版本枚举的独立型号，提升为独立产品行
                        rule = PROMOTE_MAP[p]
                        rule.record(f"{bv} {row['厂商']}|{row['模型名称']}|{p}->{rule.replacement}")
                        new_row["模型名称"] = rule.replacement
                        new_row["版本/配色"] = ""
                        promote_count += 1
                    else:
                        new_row["版本/配色"] = apply_version_rules(p, bv, row["厂商"], row["模型名称"], rules)
                    out.append(new_row)
                continue
            version = parts[0]

        if version:
            version = apply_version_rules(version, bv, row["厂商"], row["模型名称"], rules)
        base["版本/配色"] = version
        out.append(base)
    return out, split_count, promote_count


def write_csv(path, rows, header=FIELDS):
    with open(path, "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_partition(path):
    """读取分P分组配置：返回（表名->[(BV, 限定模型集合或None)]有序列表, BV->表名串）。
    第 4 列「限定模型」可选：分号分隔的模型名，用于同一分P内按模型拆表（如澄顺篇 F90 系列独立成表）；
    留空表示该 BV 的其余（未命中限定）行全部归入本表。"""
    groups = {}
    bv_tables = {}
    with open(path, encoding="utf-8-sig", newline="") as fp:
        for row in csv.DictReader(fp):
            table = row["输出表"].strip()
            bv = row["BV"].strip()
            if not table or not bv:
                continue
            models_raw = (row.get("限定模型") or "").strip()
            models = {m.strip() for m in models_raw.split(";") if m.strip()} or None
            if table not in groups:
                groups[table] = []
            groups[table].append((bv, models))
            bv_tables.setdefault(bv, [])
            if table not in bv_tables[bv]:
                bv_tables[bv].append(table)
    return groups, {bv: "+".join(ts) for bv, ts in bv_tables.items()}


def build_pending(rows_by_season, bv_table=None):
    pending = []
    for season, rows in rows_by_season.items():
        for row in rows:
            for category, keywords, match_field, advice in PENDING_SPECS:
                if match_field == "厂商":
                    hit = row["厂商"] in keywords
                elif match_field == "版本":
                    hit = any(k in row["版本/配色"] for k in keywords)
                else:
                    hit = any(k in row["模型名称"] for k in keywords)
                if hit:
                    pending.append({
                        "类别": category,
                        "season": season,
                        "输出表": (bv_table or {}).get(row["_bv"], f"products-{season}"),
                        "BV": row["_bv"],
                        "厂商": row["厂商"],
                        "模型名称": row["模型名称"],
                        "版本/配色": row["版本/配色"],
                        "问题说明": advice,
                    })
                    break
    return pending


def main():
    ap = argparse.ArgumentParser(description="聚合并标准化两个 season 的产品 CSV")
    ap.add_argument("--rules", default=os.path.join(ROOT, "tools", "normalize_rules.csv"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "outputs", "normalized"))
    args = ap.parse_args()

    rules = load_rules(args.rules)
    for rule in rules:
        if rule.rtype == "拆分例外":
            SPLIT_EXCEPTIONS.add(rule.pattern)
        elif rule.rtype == "版本值提升产品":
            PROMOTE_MAP[rule.pattern] = rule

    seasons = collect_rows()
    os.makedirs(args.out_dir, exist_ok=True)

    # season-4951163 的分P分组配置（同一分P不跨表；限定模型列可将同一分P内特定模型拆入另一表）
    partition_path = os.path.join(ROOT, "tools", "partition-4951163.csv")
    groups, bv_table = load_partition(partition_path)
    # BV -> [(表名, 限定模型集合或None)]，用于行级归属
    bv_entries = {}
    for table, entries in groups.items():
        for bv, models in entries:
            bv_entries.setdefault(bv, []).append((table, models))

    def table_of(row):
        for table, models in bv_entries.get(row["_bv"], []):
            if models is not None and row["模型名称"] in models:
                return table
        for table, models in bv_entries.get(row["_bv"], []):
            if models is None:
                return table
        return None

    total_in = total_out = 0
    processed = {}
    for season in SEASONS:
        rows = seasons[season]
        out, split_count, promote_count = process_season(rows, rules)
        processed[season] = out
        total_in += len(rows)
        total_out += len(out)
        if season == "season-4951163":
            missing = sorted({r["_bv"] for r in out if r["_bv"] not in bv_table})
            if missing:
                sys.exit(f"错误：以下分P未在 {partition_path} 登记分组：{missing}")
            group_dir = os.path.join(args.out_dir, "season-4951163")
            os.makedirs(group_dir, exist_ok=True)
            by_table = {}
            for r in out:
                t = table_of(r)
                if t is None:
                    sys.exit(f"错误：{r['_bv']} 的行「{r['模型名称']}」未匹配到分组（请检查限定模型列）")
                by_table.setdefault(t, []).append(r)
            for table, entries in groups.items():
                order = {(bv, i) for i, (bv, _) in enumerate(entries)}
                pos = {bv: i for i, (bv, _) in enumerate(entries)}
                # 组内按配置顺序（=期数/分P顺序）排列，同分P内保持视频原顺序（稳定排序）
                trows = sorted(by_table.get(table, []), key=lambda r: pos[r["_bv"]])
                tpath = os.path.join(group_dir, f"{table}.csv")
                write_csv(tpath, trows)
            print(f"[{season}] 输入 {len(rows)} 行 -> 输出 {len(out)} 行（拆分 {split_count} 行，提升型号 {promote_count} 行），"
                  f"按 {len(groups)} 张分组表输出")
            print(f"  -> {group_dir}/<厂牌或主题>.csv")
        else:
            # 其余 season 保持单表聚合，按厂商名重排（稳定排序：同厂商内保持原 BV/文件顺序）
            out.sort(key=lambda r: r["厂商"])
            out_path = os.path.join(args.out_dir, f"products-{season}.csv")
            write_csv(out_path, out)
            print(f"[{season}] 输入 {len(rows)} 行 -> 输出 {len(out)} 行（拆分 {split_count} 行，提升型号 {promote_count} 行）")
            print(f"  -> {out_path}")

    # 转换表（含命中统计，供回溯与校验）
    mapping_path = os.path.join(args.out_dir, "mapping-table.csv")
    with open(mapping_path, "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["规则类型", "字段", "作用域", "原音译名", "标准化名", "命中次数", "示例", "依据备注"])
        for rule in rules:
            if rule.rtype in ("拆分例外",):
                continue
            w.writerow([rule.rtype, rule.field, rule.scope, rule.pattern, rule.replacement,
                        rule.hits, "；".join(rule.examples), rule.note])
    print(f"  -> {mapping_path}")

    # 待人工确认清单
    pending = build_pending(processed, bv_table)
    pending_path = os.path.join(args.out_dir, "review-pending.csv")
    write_csv(pending_path, pending, header=["类别", "season", "输出表", "BV", "厂商", "模型名称", "版本/配色", "问题说明"])
    print(f"  -> {pending_path}（{len(pending)} 条待确认）")

    # 汇总报告
    used = [r for r in rules if r.hits > 0 and r.rtype not in ("拆分例外",)]
    unused = [r for r in rules if r.hits == 0 and r.rtype not in ("拆分例外",)]
    print(f"\n合计：{total_in} 行输入 -> {total_out} 行输出；"
          f"应用映射规则 {len(used)} 条，未命中规则 {len(unused)} 条")
    if unused:
        print("未命中规则（请检查 pattern 是否与数据一致）：")
        for r in unused:
            print(f"  - [{r.rtype}] {r.pattern} -> {r.replacement}")
    print(f"\nseason-4951163 按分P分组为 {len(groups)} 张表（同一分P不跨表）；"
          f"season-4852205 保持单表聚合，两个 season 内容不混并。")


if __name__ == "__main__":
    sys.exit(main())
