# 日报后处理：mention 抽取与产品对齐（v2）

本文描述字幕/转写之后的两段处理：**把一天的内容拆成原子 mention**，再**把跨天的 mention
归并成一个产品实体**。目标是产品目录「一个产品一条记录」，同时完整保留预热、公布、
预售、价格变动等状态变迁。

> 字幕获取见 [doudou-ocr-pipeline.md](doudou-ocr-pipeline.md)；这里从「已经有一段文本」开始。

## 1. 为什么要两层

旧版（v1）每条资讯只有一个自由文本 `news_type`，问题：

- 100 多种写法（`新品公布 / 预售开订`、`解禁`、`登场`…），无法当状态用
- 同一产品跨天出现时无法归并（名字/厂商常被 ASR 写错）
- 产品的“生命周期”被拆成互不相干的条目

v2 拆成两层：

```text
文本 ──抽取──> mention（一条提及 = 一次事件，带受控 stage/event + 时间戳）
                      │ 对齐（精确键 → 别名 → 模糊 → 人工复核）
                      ▼
              product（一个产品一条记录，内含完整时间线）
```

## 2. mention 结构

`tools/extract_daily_mentions.py` 输出 `outputs/daily_v2/mentions/<日期>_<BV>.json`：

```json
{
  "date": "20260701",
  "source": "ocr",
  "video_id": "BV125Th6UE8X",
  "mentions": [
    {
      "brand": "万象聚变",
      "line": "",
      "model_name": "流星",
      "variant": "",
      "scale": "拼装",
      "stage": "released",
      "stage_cue": "正式登场",
      "event": "none",
      "price": "",
      "release_date": "",
      "evidence": "首先万象聚变带来第二弹机体流星，终于更新",
      "confidence": 0.97,
      "source_time": {"start": 7.5, "end": 11.5},
      "source_url": "https://www.bilibili.com/video/BV125Th6UE8X?t=7"
    }
  ]
}
```

身份拆成四段，避免“名字挂着一堆后缀”：

| 字段 | 含义 | 例 |
| --- | --- | --- |
| `brand` | 厂商 | 瘦虎模型、摩动核 |
| `line` | 产品线/规格前缀 | MG、RG、PGU、超动骑兵系列 |
| `model_name` | 核心机体/角色 | 巴巴托斯天狼座 |
| `variant` | 版本/配色/限定/配件 | PB限定、海涅配色、战损配件包 |

### stage（生命周期，受控枚举）

`rumor → teaser → announced → preorder → released → reprint / discontinued`，另有 `unknown`。

### event（与 stage 正交，不推进阶段）

`none / info_update / price_change / delay / review / accessory / payment / expo / recall`

“价格跳水”记为 `stage=released, event=price_change`；“测评”只在明确“大货/现货”时才算
`released`，否则归 `announced + review`（媒体样件）。

### 时间戳

OCR 模式下用 `evidence` 在字幕 cues 里做子串/相似度匹配，回填 `source_time` 与带
`?t=` 的深链；ASR 模式没有 cue，就不带时间。

## 3. 对齐规则

`tools/align_daily_mentions.py`：

1. **品牌规范化**：去标点空格、剥掉「模型/模玩/工作室/工坊/科技」等后缀，再做模糊合并（≥0.85）；少量固定别名（SOPA/SUPA/SOFA 等）走 `BRAND_SEED`
2. **完整名 = name + variant**：变体参与产品名匹配；纯销售渠道后缀（PB限定/场限/特典/福袋…）不改变 SKU，匹配前剥掉
3. **名称归一化**：NFKC、去标点、去掉规格词（MG/RG/PGU/MGSD/1:100…），规格单独作为 `grade` 参与键
4. **精确键**：`(品牌, grade, 归一化完整名)`
5. **型号守卫**：两边都带型号/序号（`1型`、`2号机`、`Mk-II`、`ver.2`、`Ⅱ`）且不同 → 无论相似度多高都不合并
6. **前缀规则**：一方是另一方的前缀且只多 ≤4 字（如「诺姆」vs「诺姆量产机型」）→ 合并
7. **别名表**：`outputs/daily_v2/alias.json` 里人工确认的 `(品牌, 写法) -> 规范写法` 优先于上述规则
8. **模糊**：同品牌、grade 不冲突、完整名相似度 ≥0.90 → 自动合并；0.80–0.90 → 进 `review.json`
9. **配件/套装**：`variant` 含「配件包/套装/特典/外甲/改件/头雕/战损…」或 `event=accessory` → 视为独立 SKU，不并进本体
10. **阶段对账**：`reconcile_stage` 把“测评/开箱”但无“大货/现货”字样的 released 降回 announced；保留 `stage_raw` 供审计
11. **投影**：`current_stage` 取所有 `event=none` 提及里最靠后的阶段（单调，不回退）
12. **异常标记**：`stage_regression`（纯阶段提及倒退）、`price_before_release`、`same_day_variants`

输出：

```text
outputs/daily_v2/products.json   # 产品 + 时间线 + flags
outputs/daily_v2/review.json     # 0.80–0.90 的待人工确认对
outputs/daily_v2/summary.json    # 统计
```

## 4. 运行

```bash
# 1) 抽取（默认读 ASR；--source ocr 读 OCR 字幕并回填时间戳）
.venv-tools/bin/python -m tools.extract_daily_mentions \
  --source ocr --start-date 20260701 --end-date 20260710

# 2) 对齐
.venv-tools/bin/python -m tools.align_daily_mentions \
  --start-date 2026-07-01 --end-date 2026-07-10 \
  --output-dir outputs/daily_v2/ocr_align

# 3) 可视化（HTML 时间线）
.venv-tools/bin/python -m tools.render_mention_timeline \
  --products outputs/daily_v2/ocr_align/products.json \
  --output outputs/daily_v2/ocr_align/timeline.html
```

## 5. 实测（0823–0922 共 31 天，ASR 版）

- 232 条 mention → 194 个产品，26 个多提及产品覆盖 64 条提及
- 4 对待人工复核
- 代表案例：瘦虎 `MG 巴巴托斯天狼座` 6 次提及合并为 1 个产品
  （0823 预售 78 → 0910 现货 → 0916–0918 价格变动 → 0920 价格战），并自动标出一次
  `stage_regression`

## 6. 别名表

`outputs/daily_v2/alias.json` 记录人工确认的写法映射，对齐时**优先于**精确键与相似度：

```json
{
  "aliases": [
    {"brand": "魔火工作室", "from": "深渊骑士", "to": "深渊骑士天启", "note": "同款不同写法"}
  ],
  "negative": [
    {"brand": "XX", "from": "牛高达", "to": "牛高达2型", "note": "确认是两个 SKU"}
  ]
}
```

- `aliases`：命中后直接把写法规范化到 `to`，后续所有规则都按 `to` 走
- `negative`：确认「不是同一个」的对，防止相似度规则再次误合（当前实现保留字段，合并逻辑待接入）
- 目前表为空，需要人工从 `review.json` 确认后写入

## 7. 已知局限

- stage 判定依赖 prompt 与口播措辞，约 85–90% 准确，靠 `stage_cue` + 异常标记人工兜底
- 价格未做币种/格式归一（59.8、298、137500 日元混存字符串）
- 别名表目前只有加载逻辑，尚无「复核 → 写回」的交互流程
- `negative` 字段已预留，但相似度合并暂未消费它
- 同一天多个变体（如四种装备包）会并成一个产品，仅打 `same_day_variants` 标记
