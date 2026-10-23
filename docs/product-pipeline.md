# 产品抽取与对齐流程（当前标准）

这是嘟嘟模玩处理链的后半段：**字幕文本 → 产品条目 → 产品实体 → 时间线**。
前半段（下载、硬字幕 OCR）见 [doudou-ocr-pipeline.md](doudou-ocr-pipeline.md)。

设计原则只有一条：**能在抽取阶段标准化的，就不要留到对齐阶段用规则补救。**

- 抽取：字段化 + 枚举 + 通用常识，产出干净的结构
- 对齐：只做**确定性归一化 + 完全相等**，相似度只用来“发现可疑”，永远不自动合并
- 跨天归并的唯一人工入口：`alias.json`

## 1. 流程

```text
outputs/daily_v2/subtitles/<日期>_<BV>.json      （OCR 字幕）
        │  tools.extract_daily_products
        ▼
outputs/daily_v2/v3/mentions/<日期>_<BV>.json    （每条 = 一个产品条目）
        │  tools.align_daily_products
        ▼
products.json / review.json                       （产品 + 时间线 / 待确认对）
        │  tools.render_product_timeline
        ▼
timeline.html                                     （可点圆点跳原视频）
```

## 2. 抽取：字段与规则

一条条目的结构（`v3/mentions/*.json` 的 `items[]`）：

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
2. “新厂/某厂/某工作室”未具名 → `brand` 留空
3. “B社/代哥/万代”是同一厂商
4. 大林以配件包为主，`大林配件包` 的品牌是“大林”
5. 第X弹/第X系列是批次，放 `line`

排除规则：

- 福利/抽奖/掉落/赠品段落整段不提取（“包含了 A、B、C”通常是赠品清单）
- 广告/带货/店铺引流不提取
- 纯市场评论、个人感受不提取

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

`outputs/daily_v2/alias.json`：

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
- `negative`：确认不同 SKU → 复核队列不再重复提示

### 复核队列

`review.json` 列出**同品牌、名称相似度 ≥0.75** 的产品对，只做提示：

```json
{"kind": "look-alike", "score": 0.8,
 "left": {"id": "Q0039", "brand": "万代", "name": "强袭自由"},
 "right": {"id": "Q0053", "brand": "万代", "name": "强袭自由高达"}}
```

## 4. 运行

```bash
# 抽取（读 OCR 字幕；默认输出 outputs/daily_v2/v3/mentions）
.venv-tools/bin/python -m tools.extract_daily_products \
  --start-date 20260823 --end-date 20260922

# 对齐（读取上面的 mentions，按日期过滤）
.venv-tools/bin/python -m tools.align_daily_products \
  --mentions-dir outputs/daily_v2/v3/mentions \
  --output-dir outputs/daily_v2/v3_31d \
  --start-date 20260823 --end-date 20260922

# 可视化
.venv-tools/bin/python -m tools.render_product_timeline \
  --products outputs/daily_v2/v3_31d/products.json \
  --output outputs/daily_v2/v3_31d/timeline.html \
  --min-mentions 2
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `--start-date/--end-date` | 抽取按视频日期过滤；对齐按条目日期过滤（`YYYYMMDD`） |
| `--force`（抽取） | 覆盖已有 mention 文件 |
| `--min-mentions`（渲染） | 只画“提及次数 ≥N”的产品，`1` 表示全量 |

## 5. 实测结果

**0701–0710（9 条）**：75 条条目 → 73 个产品，多提及 1 个，复核 0 对。

**0823–0922（31 条）**：234 条条目 → **217 个产品，多提及 7 个，复核 25 对**。

| 产品 | 提及 | 时间线特征 |
| --- | --- | --- |
| 瘦虎模型 · 巴巴托斯天狼座 | 7 | 预售 78 → 大货 → 68 → 59.8 → 价格战 |
| 万象聚变 · 流星 | 4 | 登场 → 解禁 → 测评 → 再登场 |
| US模玩 · 鲨鱼波鲁 | 3 | 0920 前后连续更新 |
| 华夏模型 · 巴巴托斯天狼座 | 3 | 与瘦虎同款不同厂，保持独立 |
| 迪雷克 · 翠鸟 | 3 | 官图 → 亮相 → 大货 |

复核队列以“真·不同 SKU”为主（`炮装脉冲` vs `空装脉冲`、`强袭自由` vs `非凡强袭自由`），
恰好证明不能走相似度自动合并。

## 6. 已知问题

| 问题 | 表现 | 处理 |
| --- | --- | --- |
| LLM 抽取消方差 | 同一段文本两次抽取，条目集合不完全一致（如 0703 漏掉一个产品） | 需要时抽两次取并集，或做完整性校验 |
| 价格噪声 | 0920 出现 `758`（应为 58/75.8） | 规则清洗或人工复核 |
| 产品名仍偶有动词 | `product` 偶尔带“更新/登场” | prompt 已约束，长尾存在 |
| 别名维护 | 31 天产生 25 对待确认 | 需要 alias 小工具（list / confirm / reject） |
| 时间戳 | 依赖 `evidence` 在 cue 里命中 | 命中率约 90%，未命中的条目无 `?t=` 链接 |

## 7. 下一步

1. 做 `alias` 命令行：列复核对、确认/否定、写回 `alias.json`
2. 把 25 对过一遍，重跑对齐看产品数下降
3. 全量 113 天跑一轮，形成完整产品目录
4. 需要时再引入 `product_code`（厂商编号）强化身份键
