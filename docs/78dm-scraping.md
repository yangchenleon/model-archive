# 78dm 抓取与导入

本文给另一个 agent 用：从 78dm 系列页抓取产品/封面，先落本地，再决定是否导入数据库。

## 1. 快速开始

前提：仓库根目录有可用的 78dm `_identity` cookie（本地文件 `78cookie2`，已 gitignore；不要提交）。

```bash
# 1) 抓产品元数据到本地（不写数据库）
.venv/bin/python tools/scrape_78dm.py \
  --url https://acg.78dm.net/ct/341672.html \
  --out imports/78dm/341672 \
  --delay 0.15 \
  --skip-images

# 2) 并发下载/续传封面
.venv/bin/python tools/download_78dm_images.py \
  --dir imports/78dm/341672 --workers 8

# 3) 预览导入（不修改数据库）
.venv/bin/python tests/import_78dm_rg.py

# 4) 确认后执行替换；会删除现有 万代/RG 产品
.venv/bin/python tests/import_78dm_rg.py --apply
```

当前示例 `341672` 是 `RG系列拼装模型`，共 235 款。

再抓 MG：

```bash
.venv/bin/python tools/scrape_78dm.py \
  --url https://acg.78dm.net/ct/2328.html \
  --out imports/78dm/2328 --skip-images

.venv/bin/python tests/import_78dm_mg.py           # dry run
.venv/bin/python tests/import_78dm_mg.py --apply   # replace MG/MGEX
```

`2328` 主页面只显示每个子分类的前 42 张卡，抓取器会继续抓所有子分类页；
最终 817 条原始记录，排除 15 条未商品化参考出品，导入 802 条（MG 794 + MGEX 8）。

## 2. Cookie

- `78cookie2` 里的 `_identity` 单独可用。
- `78cookie` 全量也可用。
- `78cookie3` 的 CORS cookie 单独不可用。
- 不带 cookie 时 78dm 返回 404。
- cookie 会过期（本次约 2026-11-05）；过期后重新从浏览器导出，不要写进代码或文档。
- `.gitignore` 已包含 `78cookie*`；`imports/` 也不进 git。

## 3. 目录结构

```text
78cookie2                  # 本地 cookie，gitignored
tools/
  scrape_78dm.py           # 系列页 -> products.json + 可选封面
  download_78dm_images.py  # 根据 products.json 并发下载封面
tests/
  import_78dm_rg.py        # 将 RG manifest 替换进 PostgreSQL（一次性任务）
  import_78dm_mg.py        # 将 MG/MGEX manifest 替换进 PostgreSQL（一次性任务）
  seed_review_queue.py     # 审核队列一次性种子
imports/78dm/<series-id>/
  series.json              # 系列信息、子分类、产品 URL 列表
  products.json            # 产品字段 + 本地封面相对路径
  images/<ct-id>.jpg|png|webp
```

`imports/` 是抓取产物，不进仓库。

## 4. 抓取器做了什么

`scrape_78dm.py`：

1. 读取 cookie（默认 `78cookie2`）。
2. 抓系列页，解析：
   - 标题、简称、厂商、简介
   - 子分类（`级别或分类`）名称、数量、链接
3. 逐个抓子分类页，拿完整产品卡片。
   - 78dm 主系列页只渲染每个子分类的前 42 张卡，不能只解析主页面。
4. 逐个抓单品页，解析右侧表格：
   - 厂商、系列、级别或分类、价格、名称、版本、编号
   - 发售时间、比例、人物名、材料种类、规格、玩具分类
5. 抓封面：单品页 `showImage(..., w1200h1200)` 优先；详情页大图兜底。
6. 写 `series.json`、`products.json`；可选下载封面。

支持参数：

```bash
--url URL           # 默认 341672
--out DIR           # 必填，相对仓库根目录
--cookie PATH       # 默认 78cookie2
--limit N           # 只抓前 N 个，调试用
--skip-images       # 先只抓元数据（推荐）
--delay SECONDS     # 单品页间隔，默认 0.25
```

## 5. products.json 字段

```json
{
  "id": "6371",
  "url": "https://acg.78dm.net/ct/6371.html",
  "name": "03 空战型强袭高达",
  "page_title": "RG 普通版 03 空战型强袭高达",
  "version": "普通版",
  "code": "RG03",
  "price": "2500日元",
  "release_date": "2011年4月30日",
  "scale": "1/144",
  "character": "GAT-X105 强袭高达...",
  "manufacturer": "万代",
  "series": "RG系列拼装模型",
  "source_category": "普通版",
  "line": "RG",
  "channel": "regular",
  "material": "塑料",
  "specification": "约130mm",
  "toy_category": "塑料拼装模型",
  "image_url": "https://...-w1200h1200",
  "image_file": "images/6371.jpg",
  "fields": { "原始表格字段": "..." }
}
```

`channel` 是推断值，不是 78dm 原字段：

- 普通版 → `regular`
- 网络限定版 → `pb`
- 其他限定版 → `limited`
- 参考出品/开发中 → 不入库；通用抓取器给 `None`，版本含“限定”则 `limited`
- 其他子分类按版本含“网络限定/网限/限定/普通版”推断，否则 `null`

`work` 不写入 manifest，由导入脚本按子分类填；万代未标注的作品默认 `高达`，非高达 IP 用明确映射。

- EVANGELION系列 → `EVANGELION`
- 勇者王系列 → `勇者王`
- 机动警察系列 → `机动警察`
- 其余（高达系）→ `NULL`，不要靠名字猜

## 6. 导入规则

`import_78dm_rg.py` 是**RG 专用、破坏性**导入：

- 只处理 `万代 / RG`。
- 默认 dry-run；`--apply` 才会：
  1. 找出当前 `万代 / RG` 产品；
  2. 把关联审核记录退回 `pending` 并清空产品/厂家/系列匹配；
  3. 删除这些产品；
  4. 插入 manifest 中 235 条。
- 当前 RG 没有资产/收藏集引用；如果以后有，直接删产品会被 FK 阻止，需要先迁走资产/目标。
- `kit_name` 去掉开头数字序号：`01 RX-78-2 高达` → `RX-78-2 高达`。
- `product_code` 去 `RG` 前缀：`RG01` → `01`。
- 万代通贩编号统一为数字（一次性整理，不是通用 API 规则）：`MG184` / `MG 80` / `RG01` → `184` / `80` / `01`。
  - 78dm 的普通版前 79 条名称没有 `MGxx` 前缀，且 code 列常为空；导入器按普通版顺序补 `01`–`79`。
  - 第 80 条起名称通常带 `MG80` 等前缀，优先从名称提取；78dm 的 code 列存在错号（如 `MG169` 被标成 `170`、`MG198` 被标成 `200`），不能盲信。
  - 非万代的产品编号（如 `MNP-XH01`）不是通贩序号，保持原样。
  - 限定版编号不强行数字化，按源数据保留。
- 编号缺失时：
  - 优先从 78dm 名称前缀补（`12 ...` → `12`）；
  - `陆战型高达` 源数据无编号，按普通版 44 款顺序补为 `44`（有注释，可人工改）。
- `release_date` 取**首个发售日期**；只有年月按当月 1 日，只有年份按 1 月 1 日。
- 再版/延期原文不丢，完整放在 `detail` 的“发售时间”里。
- 封面路径写入 `detail` 的“封面”，数据库暂无图片字段/对象存储。
- 所有 RG 保持 `line=RG`；EVA/勇者王/机动警察不拆 line。

### MG / MGEX

`2328` 的子分类是混维度的，导入器按以下规则处理：

- `line=MG`，`EXtreme` 单独 `line=MGEX`。
- `普通版` → `regular` + `edition=普通版`；`网络限定版` → `pb`。
- `其他限定版` / HD配色 / 官方豪华/特别 / 限定透明/电镀 / 水晶 / 彩色电镀 / 限量涂装 / 特殊武器配件 → `limited`。
- `一番赏` → `lottery`；`高达30周年透明配件版` / `竞赛奖品版` → `event`。
- 重力战线、一年战争 → `limited` + `work`；圣战士丹拜因、机动警察 → `regular` + `work`。
- 特殊武器配件：`edition=配件包`。
- 官方豪华版/特别版：`edition=豪华版/特别版`。
- HD配色、限定透明/电镀/水晶/彩色电镀、竞赛奖品、30周年、特别涂装：`edition` 用对应官方分类。
- `往期未商品化参考出品` 15 条不入库。
- 普通版的 edition 固定为 `普通版`；万代未标注的 work 固定为 `高达`。
- 同名不同版本：保留普通版原名，其他加 `（edition/分类）` 后缀，保证产品名唯一。
- `craft` 从 edition/名称提取单值工艺；不明确留空。

`import_78dm_mg.py` 默认 dry-run，`--apply` 会替换现有 `万代/MG` 和 `万代/MGEX`。

## 7. 验证

```bash
cd backend
../.venv/bin/python -m pytest tests -q

cd ../frontend
npm run build
```

数据库抽查：

```sql
select count(*) from products; -- 2243 (2026-10-30)
select l.name, count(*) from products p
join manufacturers m on m.id=p.manufacturer_id
join product_lines l on l.id=p.product_line_id
where m.name='万代' group by l.name;
-- MG 794 / MGEX 8 / RG 232

select count(*) filter (where release_date is not null) -- 1000
from products;
```

当前 RG 子分类：

```text
普通版 44 / 网络限定版 85 / 其他限定版 85
EVANGELION 14 / 勇者王 3 / 机动警察 1 / 参考出品 3
```

## 8. 常见问题

| 现象 | 处理 |
| --- | --- |
| 404 / 页面没有找到 | cookie 缺失或过期；换 `78cookie2`/重新导出 |
| 子分类产品数不对 | 不要只解析主系列页；抓每个子分类 URL |
| 图片下载慢/失败 | 先 `--skip-images` 抓元数据，再用并发下载器；可重跑续传 |
| 导入后 RG 数量不对 | 检查 manifest 是否为 235、是否误用了别的 series |
| 导入报 FK/资产引用 | 当前 RG 有资产或收藏集引用；先迁移，不要删 |
| 编号/日期缺失 | 源页为空；不要自动编造，按本文的 override 规则处理并留注释 |

## 9. 新增别的 78dm 系列

抓取器是通用的；导入器目前只支持 `万代 / RG`。新增系列时：

1. 用 `scrape_78dm.py` 抓新 URL 到新的 `imports/78dm/<id>/`；
2. 检查 `products.json` 的 `line/work/channel` 是否符合预期；
3. 复制/修改 `import_78dm_rg.py` 的厂家、line、work 映射和数量断言；
4. 先 dry-run，再 `--apply`；
5. 更新文档和 dump。
