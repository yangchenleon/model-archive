# 产品抽取与对齐流程（当前标准）

这是嘟嘟模玩处理链的后半段：**字幕文本 → 产品条目 → 产品实体 → 时间线**。
前半段（下载、硬字幕 OCR）见 [doudou-ocr-pipeline.md](doudou-ocr-pipeline.md)。

设计原则只有一条：**能在抽取阶段标准化的，就不要留到对齐阶段用规则补救。**

- 抽取：字段化 + 枚举 + 通用常识，产出干净的结构
- 对齐：只做**确定性归一化 + 完全相等**，相似度只用来“发现可疑”，永远不自动合并
- 跨天归并的唯一人工入口：`alias.json`

## 1. 流程

```text
outputs/daily_reports/<日期>_<BV>/subtitles/<日期>_<BV>.json   （OCR 字幕）
        │  tools.extract_daily_products
        ▼
outputs/daily_reports/<日期>_<BV>/mentions.json               （每条 = 一个产品条目）
        │  tools.align_daily_products
        ▼
outputs/products/products.json / review.json                  （产品 + 时间线 / 待确认对）
        │  tools.render_product_timeline
        ▼
outputs/products/timeline.html                                （条目可展开，mention 行跳原视频秒数）
```

一期视频的源文件、字幕、抽取结果都在同一目录内；跨期汇总只在 `outputs/products/`。
人工维护的配置（别名表）放在仓库根 `config/`，不进 `outputs/`。

## 2. 抽取：字段与规则

一条条目的结构（各期目录下 `mentions.json` 的 `items[]`）：

```json
{
  "brand": "US模玩",
  "line": "1比60PG拼装",
  "product": "铁球波鲁",
  "variant": "",
  "status": "preorder",
  "price": "139",
  "detail": "全分件分色带钣喷涂装，带驾驶舱展开联动灯组…",
  "evidence": "US模玩带来的1比60PG铁球波鲁…预出139七月份内上线"
}
```

| 字段 | 约定 |
| --- | --- |
| `brand` | 只填厂商；`GK` 不是厂牌，“新厂/某厂”未具名时留空；“大林配件包”的品牌是“大林” |
| `line` | 规格/系列/批次：`MG`、`RG`、`1比60PG拼装`、`超动骑兵系列`、`第二弹` |
| `product` | 纯名词短语，不含动词、状态词、版本词 |
| `variant` | 版本/配色/换色/限定/套装：`彩透版`、`电镀银`、`PB限定`、`进阶装` |
| `status` | 枚举：`rumor / teaser / announced / preorder / released / reprint / discontinued / unknown` |
| `price` | 只保留数字和单位，没有就空 |
| `detail` | 其他描述（测评、延期、配件、玩法、价格波动、评价） |
| `evidence` | 原文片段，用于回溯与时间戳定位 |

prompt 里固定注入的通用常识：

1. `GK` 是套件类型，不是厂牌
2. “新厂/某厂/某博主/某经典老厂/不知名小厂”未具名 → `brand` 留空，不借别的厂名
3. 反讽的“隔壁不知名小厂/小厂/阿代/代哥”仍指万代；`B社` 在官方语境下也指万代
4. 大林以配件包为主，`大林配件包` 的品牌是“大林”
5. 第X弹/第X系列是批次，放 `line`
6. **KO/翻模/放大/国服版**：`brand` 是做它的第三方厂（大班/高高/长龙/猛虎/神兽/天硕/爆闪/福风/真飞鸟/匠造方/高师傅/高甲厂/XT厂/波塞冬/胖虎/聚匠/野牛/HN/御膳房/模工坊/瘦虎/华夏/乐模汇…），不是万代
7. 规格词（MGEX/RG/PGU/MGSD/MB）只进 `line`，不是品牌；第三方同样会用这些规格名做 KO
8. 无名 KO（“某博主公布KO版…”“国服KO版…”）→ `brand` 留空，不臆造
9. 同一段连续介绍、中间没有新厂名时沿用上一个厂（“你长龙叔叔带来放大 RG 福风牛…还更新 MGEX 黑金菲尼克斯”→ 两条都是长龙）
10. `evidence` 必须是字幕原文的连续片段；字幕 OCR 里的 `7` 常是“了”，按“了”理解

排除规则：

- 福利/抽奖/掉落/赏池/赠品段落整段不提取（“包含了 A、B、C”通常是赠品清单）
- 广告/带货/店铺引流不提取
- 纯市场评论、个人感受不提取
- 代码兜底（`clean_items`）：`evidence` 为空或命中“掉落/抽奖/福利/赠送/开奖/上车/赏池”的条目直接丢弃

## 3. 对齐：完全相等 + 确定性归一化

`tools/align_daily_products.py` 的匹配键：

```text
(normalize_brand(brand), norm(product), norm(variant))
```

归一化只做三件事（全部确定性、不涉及相似度）：

1. `norm`：NFKC、小写、去空格与标点
2. `normalize_brand`：剥掉“模型/模玩/工作室/工坊/科技/工业/玩具/公司/配件包”后缀
3. `normalize_product`：把误入 `product` 的规格词（`PG/RG/MG/HG/PGU/MGSD…`）移回 `line`

**没有相似度合并、没有前缀合并。** 同一产品的不同写法 = 不同产品，直到人工确认别名。

### 别名表

`config/alias.json`（仓库根的配置目录，不放 `outputs/`）：

```json
{
  "aliases": [
    {"brand": "万代", "from": "强袭自由", "to": "强袭自由高达", "note": "同一产品"}
  ],
  "negative": [
    {"brand": "万代", "from": "炮装脉冲高达", "to": "空装脉冲高达", "note": "不同装备包"}
  ]
}
```

- `aliases`：确认同一产品 → 对齐时把写法归一
- `negative`：确认不同 SKU → **预留字段，当前代码尚未消费**，复核队列仍会提示，待 alias 工具一并实现

当前表里已有 24 条人工判断（同产品异写、OCR 错字、语序颠倒），
例如 `巴巴托斯狼祖宗 → 巴巴托斯狼王`、`卫塑玄甲 → 卫架玄甲`、
`牛高达/福风牛 → 福风牛高达`（龙虎模型）。纯相似但确属不同 SKU 的
（炮装/空装脉冲、忠勇级/晓勇级闻仲、菲尼克斯各配色、蓝异端/蓝异端 D 型）
没有写入，保持独立。

### 复核队列

`review.json` 列出**同品牌、名称相似度 ≥0.75** 的产品对，只做提示：

```json
{"kind": "look-alike", "score": 0.8,
 "left": {"id": "Q0039", "brand": "万代", "name": "强袭自由"},
 "right": {"id": "Q0053", "brand": "万代", "name": "强袭自由高达"}}
```

## 4. 运行

```bash
# 抽取（读各期目录的 subtitles/*.json，写回同期 mentions.json）
.venv-tools/bin/python -m tools.extract_daily_products \
  --start-date 20260823 --end-date 20260922

# 对齐（读各期 mentions.json，按日期过滤）
.venv-tools/bin/python -m tools.align_daily_products \
  --start-date 20260823 --end-date 20260922

# 可视化（条目级展开；默认全量，可用 --min-mentions 收窄）
.venv-tools/bin/python -m tools.render_product_timeline

# 回归：KO/第三方品牌归属（11 段真实字幕，全过才算通过）
.venv-tools/bin/python -m tools.eval_ko_prompt
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `--start-date/--end-date` | 抽取按视频日期过滤；对齐按条目日期过滤（`YYYYMMDD`） |
| `--force`（抽取） | 覆盖已有 `mentions.json` |
| `--min-mentions`（渲染） | 只画“提及次数 ≥N”的产品，默认 `1`（全量） |
| `--reports-dir` / `--alias-file` / `--output-dir` | 默认 `outputs/daily_reports` / `config/alias.json` / `outputs/products`，一般不用改 |

## 5. 实测结果

**2026-07-01 – 10-22（114 期，全量）**：880 条条目 → **785 个产品，多提及 59 个，复核 31 对**，
抽取 114/114 成功、无失败。KO 纠偏后 `万代` 条目由 77 降到 41，大班（22）、高高（20）、
长龙（16）、猛虎（12）等第三方厂各自独立成条；接入 24 条别名后产品 795 → 785、复核 61 → 31。

| 产品 | 提及 | 时间线特征 |
| --- | --- | --- |
| 万象聚变 · 流星 | 8 | 0701 首提到 9 月仍在返场，跨度最长 |
| 瘦虎模型 · 巴巴托斯天狼座 | 7 | 预售 78 → 大货 → 68 → 59.8 → 价格战 |
| 神兽模型 · 菲尼克斯 | 5 | MGEX 菲尼克斯 KO 系列多次换色 |
| 驭意堂 · 皓灵白帝 | 5 | 首曝 → 公布 → 测评 → 再度提及 |
| 摩动核 · 马超 | 4 | 7 月起持续更新 |
| 模笛 · 卫架玄甲 | 4 | 7 月底亮相后连续跟进 |

历史口径（旧目录结构下的记录）：0701–0710（9 期）75 → 73；0823–0922（31 期）234 → 217、
复核 25 对。全量重跑后同一时期数字会因 prompt 与抽取批次不同而略有出入。

复核队列以“真·不同 SKU”为主（`炮装脉冲` vs `空装脉冲`、`强袭自由` vs `非凡强袭自由`），
恰好证明不能走相似度自动合并。

## 6. 已知问题

| 问题 | 表现 | 处理 |
| --- | --- | --- |
| LLM 抽取消方差 | 同一段文本两次抽取，条目集合不完全一致（如 0703 漏掉一个产品） | 需要时抽两次取并集，或做完整性校验 |
| 价格噪声 | 0920 出现 `758`（应为 58/75.8） | 规则清洗或人工复核 |
| 产品名仍偶有动词 | `product` 偶尔带“更新/登场” | prompt 已约束，长尾存在 |
| 别名维护 | 全量 114 期产生 31 对待确认 | 需要 alias 小工具（list / confirm / reject） |
| 时间戳 | 依赖 `evidence` 在 cue 里命中 | 命中率约 90%，未命中的条目无 `?t=` 链接 |

## 7. 下一步

1. 做 `alias` 命令行：列复核对、确认/否定、写回 `config/alias.json`
2. 把剩下的 31 对过一遍，重跑对齐看产品数下降
3. 增量维护：新一期落盘后只跑 `--start-date/--end-date` 覆盖的区间，再全量对齐
4. 需要时再引入 `product_code`（厂商编号）强化身份键
