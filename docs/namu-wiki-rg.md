# namu.wiki RG 数据源：抓取方式与数据特征

> 2026-11 整理。用途：给万代 RG 线做机号、发售批次、会场/限定分类的对照，补 78dm 的缺口。
> 原站内容按 **CC BY-NC-SA 2.0 KR** 授权，本地仅作个人资料库参考，不要公开分发。

## 1. 为什么用它

- 78dm 按「商品」收录，同一个套件的再版/换包装会合并成一条，日期塞在详情里。
- namu 的 RG 列表按**发售批次**拆行，并且把每条归进「通贩 / Premium Bandai / 会场 / 基地 / 其他限定」等小节，正好是库里 `release_channel` 需要的口径。
- 页面里还带机号（`RX-78-2`、`MS-06S`…），78dm 有一半条目没写机号。

## 2. 访问方式（这条最费劲）

直连 `namu.wiki` 会依次撞上三堵墙：

1. **DNS 污染**：本机把 `en.namu.wiki` / `namu.wiki` 解析成 `2a03:2880:…face:b00c` 这类假 IPv6。
2. **Cloudflare 硬封**：返回 `Sorry, you have been blocked`（不是 Turnstile 挑战页，`cf_clearance` 无效）。
3. 图片域名 `i.namu.wiki` 也走 Cloudflare。

实际可用的组合：

| 目标 | 方法 |
|---|---|
| 解析 | Cloudflare DoH（`https://cloudflare-dns.com/dns-query`）拿真实 A 记录 |
| 页面 | **Google 翻译代理** `https://en-namu-wiki.translate.goog/w/...`（英文镜像，本身是英文站） |
| 图片 | 直连 `i.namu.wiki` 可以，但必须带 `Referer: https://namu.wiki/` |

注意：

- 翻译代理对**韩文原站**（`namu-wiki.translate.goog`）不会翻译，拿回来仍是韩文；只有英文镜像可用。
- 翻译代理可能限流或失效，脚本带缓存和重试。

## 3. 工具与产物

```bash
.venv/bin/pip install beautifulsoup4 html2text

# 抓列表 + 所有产品页（含图片）
.venv/bin/python tools/namu_wiki_crawl.py --limit 0 --delay 0.05 --skip-existing

# 只抓文字
.venv/bin/python tools/namu_wiki_crawl.py --limit 0 --no-images
```

产物在 `outputs/knowledge/namu-rg/`：

```
outputs/knowledge/namu-rg/
├── README.md        使用说明
├── index.md         231 条列表（按 namu 分节，带本地链接）
├── manifest.json    wiki 路径 → slug / 标题
├── mapping.csv      namu 行 → 库内产品 的对照表（本目录的核心产物）
├── assets/          页面图片（webp，约 1600 张 / 24 MB）
└── pages/           72 篇页面（含每台机体的 RG 小节）
```

缓存在 `.tmp/namu-cache/`（可随时删，重跑会重新抓）。

## 4. 数据结构

列表页 18 个表，按小节分组：

```
2. regular edition            → regular
3. Special Edition/Set        → limited
4.1 Premium Bandai Limited    → pb
4.2 Event/Event Limited       → event
4.3 기타(其他)限定             → limited
4.4 GUNDAM FRONT TOKYO        → event
4.5 Gundam Base Limited       → base
4.6 GUNDAM SIDE-F Limited     → event
5.x EVA / 勇者王 / 机动警察     → 不定义渠道
```

每行字段：`商品名 | 机号 | 发售年月 | 价格 | 作品 | 备注`。

机体页（`pages/*.md`）的 `RG` 小节里，每条是一次发售，结构是表格：

```
brand | Real Grade
scale | 1/144
Release | November 21, 2013
price | 3,500 yen
link | [product page](bandai-hobby.net/item/973/)
review | Dalongnet(...), Gundam Holic(...)
```

## 5. 数据特征与坑

1. **名称是英文机翻，错得很随意**：`ale strike gundam`（Aile）、`New Gundam`（ν）、`geong`（Zeong）、`Tallgis`（Tallgeese）、`Esstray`（Astray）。只能当检索线索，**不能当展示名**。
2. **日期只到年月**（`20.06`），没有具体日；库里 78dm 有日的，只在年月不一致时才改。
3. **价格带税**，括号里是税前（`2,800 (2,500)`）；78dm 常记税前价，直接比会全部对不上。
4. **重名条目多**：`Unicorn Gundam Perfectibility` 出现两次（BD 同捆 / 基地版），只能靠日期+价格区分。
5. **列表会漏抽选/非卖品**：`campaign only` 的条目只写在机体页正文里，不进列表（例：海涅命运电镀、一番赏神高达）。
6. **图片是缩略图**（约 200px），原站放大走 JS 灯箱，没有大图直链；要盒绘用 78dm 的 640px。
7. **列表分类才是渠道口径**，不要按名称猜。`bilibili 独角兽` 在 4.2 Event，就归 `event`。

## 6. 映射表 `mapping.csv`

按 namu 列表顺序，一行一条：

| 列 | 含义 |
|---|---|
| `section` | namu 小节（决定渠道） |
| `namu_name` / `model` / `namu_date` / `namu_price` | namu 侧 |
| `db_name` / `db_78dm` | 库内展示名 / 78dm 原名 |
| `db_channel` / `section_channel` | 当前渠道 / 按小节应得渠道 |
| `match` | `exact` 精确别名 / `scoreN` 机号+价格+日期打分 / 空 = 未匹配 |

当前状态（2026-11-04）：

```
231 行 · 配对 227 · 渠道冲突 0
未匹配 4：2 条按约定跳过（未商品化企划、Psycho Frame），2 条不匹配（套装、矮星炮）
```

生成方式：`tools/namu_wiki_crawl.py` 抓取后，用库内 `aliases` 里追加的英文名做精确匹配，回退到「机号 + 价格集合 + 年月」打分。

## 7. 与 78dm 的关系

- 78dm 是**条目基线**：清单 235 条，库里 233 个 id，缺的只有 2 条「参考出品」（`423733/423734`，按约定不入库）。
- namu 是**分类与批次基线**：渠道、初回/再版拆分以它为准。
- 已知一次漏导：`97095 异端高达红色机 珍珠电镀Ver.` 从未入库（所有备份都搜不到），2026-11-04 已补，并挂上 78dm id。
- 建议每次 78dm 导入后跑一次 id 对账：`manifest - db_ids` 应为空（白名单两条参考出品）。
