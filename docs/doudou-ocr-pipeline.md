# 嘟嘟模玩 · 字幕 OCR 处理流程

面向 UP 主「嘟嘟模玩」（B 站 mid `290901588`）的处理约定。该 UP 的视频为横屏
1920×1080，底部烧录白色黑边硬字幕，因此可以用画面字幕 OCR 替代 ASR：文本更准，
并且每条字幕自带时间戳，可直接映射回原视频时间点。

> 本文只覆盖「视频 → 字幕文本/时间戳」这一段。后续的产品抽取与对齐见
> [product-pipeline.md](product-pipeline.md)。

## 1. 流程总览

```text
选定当天速报
   └─ tools/download_daily_videos.py   → outputs/daily_reports/<日期>_<BV>/video/*.mp4
        └─ tools/ocr_subtitles.py      → outputs/daily_reports/<日期>_<BV>/subtitles/<日期>_<BV>.json
             └─ tools.ocr_subtitles --check → outputs/daily_reports/_qa.json（可疑行清单）
```

一期视频的所有派生物都留在该期目录内；只有人工维护的配置放在仓库根的
`config/`，不放进 `outputs/`。音频、ASR 文本和 `daily_report.json` 属于已废弃的
ASR 链路，不再保留。

## 2. 工具与参数

### 2.1 下载

```bash
.venv-tools/bin/python -m tools.download_daily_videos \
  --start-date 2026-09-18 --end-date 2026-10-22 \
  --interval 10 \
  --manifest outputs/daily_download_manifest.json
```

- 按天用 `tools.filter_daily_videos` 的打分选出一条速报，下载到
  `outputs/daily_reports/<YYYYMMDD>_<BV>/video/`
- 依赖 `yt-dlp`，**必须保持较新版本**（2026-07 的版本拉空间列表会 412）
- 下载质量：`bv*+ba/b`，1080P AV1 + AAC；1080P 高码率需要大会员 cookies，非必需

### 2.2 字幕 OCR

```bash
.venv-tools/bin/python -m tools.ocr_subtitles \
  --start-date 20260701 --end-date 20261022     # 不传 --video 即批量
```

结果写回各期目录的 `subtitles/`，已存在的文件跳过，所以整批可重复执行；单条视频用
`--video <期目录>/video/<BV>.mp4`，默认输出到同一期目录。

默认参数（已写死在工具里，无需每次传）：

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `--mode` | `det` | 检测框 + 整行并集识别；`band`/`rows` 已证明质量不达标 |
| `--fps` | `4` | 4fps 采样，时间戳精度 0.25s |
| `--threshold` | `0.04` | 白字掩码帧差阈值，见 §3 |
| 裁剪带 | `0.72–0.98` | 覆盖单行与两行字幕 |
| 签名 | 白字掩码 96×12 | 只比较白字区域，忽略背景运动 |
| 行聚类 | y 容差 40px + 横向间距 ≤120px | 防止左右两列卡片被并成一行 |
| 保留条件 | 中心 ±5%、高度 ≥40px、宽高比 ≥1.2、白色占比 ≥0.2 | 剔除表格/卡片/模型字 |
| 边缘过滤 | 中心 x ∈ [0.15, 0.85]（单框） | 剔除贴边图形 |

识别后处理（`postprocess`）：

| 规则 | 说明 |
| --- | --- |
| `X长大陆 → 酋长大陆` | 「酋」字形易误识 |
| `7 → 了` | 仅当前后是汉字/标点且后面不是单位（月/日/元/折…） |
| `终干 → 终于`、`处干 → 处于` | 字体连笔 |
| `查接 → 直接`、`哪介 → 哪个` | 字形 |
| `眞 → 真` | 繁体字形 |
| `。，→，`、`，，→，`、`。。→。` | 标点重复 |

### 2.3 质检

```bash
.venv-tools/bin/python -m tools.ocr_subtitles --check --check-limit 40
```

输出 `_qa.json`（写在各批次根目录 `outputs/daily_reports/_qa.json`），按「低置信 / 过短 / 无汉字 / 符号噪声 / 生僻字 / 重复字符」
列出可疑行。当前全库水平：114 条视频、平均置信 0.977、可疑行约 0.6%。

### 2.4 排除名单

`config/excluded.json` 列出不参与 OCR 的目录（当前为空）：

```json
[]
```

批量任务会自动跳过名单中的目录。加入名单前先确认源视频本身选错了还是只是没有字幕：
选错片子应当重新下载替换，而不是排除（见 §4 #10）。

## 3. 阈值取舍（实测数据）

对 0701（33 条 / 639 字）与 0711（39 条 / 745 字）逐阈值对比，**不启用跳帧兜底**：

| 阈值 | 0701 | 0711 | OCR 调用 |
| --- | --- | --- | --- |
| 0.03 | 33 / 639 ✅ | 39 / 744 ✅ | 124 / 189 |
| **0.04** | **33 / 639 ✅** | **39 / 744 ✅** | **87 / 130** |
| 0.05 | 33 / 639 ✅ | 38 / 733 ❌ | 66 / 104 |
| 0.06 | 32 / 625 ❌ | 38 / 733 ❌ | 53 / 82 |
| 0.07 | 27 / 569 ❌ | 36 / 700 ❌ | 41 / 66 |

结论：**0.04 是不丢句的最大阈值**；再往上开始丢字幕。曾用 0.08 跑全量，导致
0701 从 33 条掉到 26 条（约 -13%），已废弃。

若将来视频风格变化（字幕淡入更慢），先按上表在这两条基准视频上回归，再调。

## 4. 踩坑记录

| # | 问题 | 原因 | 处理 |
| --- | --- | --- | --- |
| 1 | 空间列表 412 | yt-dlp 版本过旧 | 升级到 2026.10+ |
| 2 | 字幕只有半句/两行串行 | 固定带 + 只识别，两行被切 | 改用 `det` 模式，整行并集识别 |
| 3 | det 每帧 2–5 秒 | 默认配置把宽幅带按短边 736 放大到约 5000px | `limit_side_len=736, limit_type=max` |
| 4 | 批量越跑越慢 | 每个视频重建 RapidOCR，泄漏约 370MB | 整批复用同一个引擎 |
| 5 | 表格左右两列被并成一行 | 行聚类只看 y | 增加横向间距 ≤120px |
| 6 | 卡片/表格文字混入 | 与字幕同为白字 | 中心 ±5% + 高度 ≥40 + 宽高比 |
| 7 | 动画帧出现 `YAY-O`/`PFAR` | 装饰字与字幕同框 | 逐帧多数投票 + 合并保留较早文本 |
| 8 | 右/左边缘图形 `STUPiO`/`CnIDio` | 贴边图形 | 中心 x ∈ [0.15, 0.85] |
| 9 | 数字 7 与「了」混淆 | 字体把「了」写成 7 | 上下文规则（单位除外） |
| 10 | 竖屏视频全是乱码（0708） | 当天选片选成了单品种草视频（`BV1HzM36RENn`，1080×1920 无字幕） | 换成当天速报 `BV1NtMa6XEFE`（1920×1080，82.9s）重下重跑，旧目录归档到 `backups/replaced/`，`excluded.json` 清空 |
| 11 | `弹匣` 读成 `弹画`、`目前` 读成 `自前`（0708） | 字形相近，后处理没覆盖 | 未加规则：`自前` 会误伤「来自前方」等词；这类单字误识逐帧核对即可 |

## 5. 重跑清单

```bash
# 1. 确认排除名单
cat config/excluded.json

# 2. 批量 OCR（默认 det / 4fps / 0.04）
.venv-tools/bin/python -m tools.ocr_subtitles --start-date 20260101 --end-date 20991231

# 3. 质检
.venv-tools/bin/python -m tools.ocr_subtitles --check --check-limit 40

# 4. 抽查错片：按每分钟字数排序，明显偏低者回看源视频
```

耗时参考：约 **90 秒/条**（4fps、0.04、单条 100–150 秒视频），114 条约 2.5–3 小时。

## 6. 产物

```text
outputs/daily_reports/
  <YYYYMMDD>_<BV>/
    video/*.mp4                # 源视频 + yt-dlp 元数据
    subtitles/<YYYYMMDD>_<BV>.json  # OCR：cues: [{start, end, text, score}]
  _qa.json                     # 质检报告（全批汇总）
config/
  excluded.json                # 不参与 OCR 的目录
```

单条 JSON 结构：

```json
{
  "video": "...mp4",
  "mode": "det",
  "fps": 4.0,
  "crop": [0.72, 0.98],
  "frames": 483,
  "ocr_calls": 87,
  "cue_count": 33,
  "cues": [{"start": 3.0, "end": 5.0, "text": "胶圈更新是没有瓶颈了吗", "score": 0.98}],
  "text": "胶圈更新是没有瓶颈了吗，每天都能给我钱包来那么一下，…"
}
```
