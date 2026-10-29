# 审核入库流程

目标只有两个：维护 `products` 产品图鉴，以及用 `review_items` 作为人工入库闸门。
**不保留产品状态历史/时间线**——这是刻意选择，不是遗漏。

## 1. 边界

- `products` 是唯一的产品表：身份字段 + 当前价格（自由文本）。没有 `status` 字段。
- `review_items` 是审计队列：每条 mention 的来源（视频、秒数、证据）、抽取字段、
  以及人工处理结果。它回答“这条信息从哪来、怎么处理的”，不是产品历史。
- 没有 `product_events`。再版、价格曲线这类未来需求用专用表解决，不复活通用事件表。

## 2. 数据模型（迁移 `0022` 起）

`products`

```text
id, manufacturer_id, product_line_id(可空), work(可空), release_channel(可空),
product_code, kit_name, detail, source, price(自由文本), created_at
```

`review_items`

```text
id, source_key(unique), event_date, video_id, start_seconds,
brand, product, line, variant, status_raw, price_raw, detail, evidence,
manufacturer_id(可空), product_line_id(可空),
product_id, state, skip_reason, created_at, reviewed_at
```

- `state`：`pending / mapped / created / skipped`
- `skip_reason`：`later / ad / duplicate / invalid`
- `source_key` 唯一：重复导入同一批抽取结果不会产生重复队列项
- `status_raw` 只是抽取原文，不参与产品表；产品没有状态
- `brand` / `line` 保留抽取原文；`manufacturer_id` / `product_line_id` 是人工匹配结果
- 产品身份是 `(manufacturer_id, product_line_id, kit_name)`；系列参与身份，同厂商同名但不同系列算不同产品；未知系列是独立一档
- 渠道是产品属性：`regular / pb / limited / event / other`，空 = 未知；不参与产品身份
- `work` 是作品/IP（EVA、勇者王、机动警察、SEED…），可空，不参与产品身份；它与 line、渠道互相正交

## 3. 审核页

侧栏「入库审核」，一次一条，默认按 **厂商 → 产品 → 时间** 排序（可切时间/产品）。

- 左卡片：日期、厂商·产品、原视频内嵌播放（跳到 mention 秒数）、原文引句、
  抽取阶段/价格/系列；可改厂商（可搜索）、产品编号、产品名、系列、作品、渠道、价格
- 厂商选择器按名称搜索；匹配不到时提示去「厂家管理」新建，刷新页面后再匹配。
  **不在审核页自动建厂**。系列下拉只列当前厂家的系列，留空 = 未知
- 右侧：搜索现有产品（只读参考），选中后可「映射」
- 动作只有三种：
  1. **映射**：把这条 mention 关联到已有产品。只写 `review_items.product_id/state`，
     同时记录产品的 `manufacturer_id/product_line_id`，**不改产品任何字段**
  2. **新建**：按表单字段插入一条 `products`，并把 mention 标记为 `created`
  3. **跳过**：记录 `skip_reason`，不碰产品表
- 新建前会做一次精确查重：同一 `(manufacturer_id, product_line_id, kit_name)` 已存在时返回 409，
  提示改用「映射」。不同系列同名不算重复；名称/厂商的模糊写法（大小写、空格）不做自动归并；没有别名表
- 快捷键：`Enter` 映射、`N` 新建、`S` 跳过

## 4. 后台管理

侧栏「后台管理」（`/#admin`）：新增、编辑、删除产品；侧栏「厂家管理」（`/#taxonomy`）维护厂家和系列。

- **新增**：手工录入（来源默认“手动录入”）；必须选厂商，系列/作品/渠道可空；走
  `(manufacturer_id, product_line_id, kit_name)` 精确查重；同厂商同名但不同系列允许
- **查看/编辑**：点击表格行打开只读详情；只有行右侧的铅笔进入编辑。弹窗不响应背景点击，
  框选文字时鼠标划出弹窗不会误关，只能点 X / 取消 / 关闭
- **编辑**：只改 `products` 的字段；改名/换厂商时同样查重（排除自己）；换厂商时系列自动重置，避免跨厂家错绑
- **删除**：同一事务内把关联的 `review_items` 退回 `pending` 并清空 `product_id`，
  再删除产品；收藏集里的目标通过 `collection_items.product_id` 的 `ON DELETE CASCADE` 一起删除；
  如果产品仍被 `assets` 引用（RESTRICT），返回 409 且整笔回滚
- **排序**：点击表头可按厂商 / 产品 / 编号 / 系列 / 价格 / 入库时间排序，再点切换升降序
- **关联审核记录**：编辑时列出该产品关联的 mention（日期、处理状态、厂商、产品、原视频链接）
- **导出 CSV**：按当前搜索/排序导出产品字段（厂商/系列导出名称），可直接留档或再导入
- 没有事件/时间线编辑

「厂家管理」：

- 名称、分类（高达/国模/KO/未分类）、等级 1–3、同级隐藏排序、描述
- 合并到其他厂家；有产品时不能直接删
- 系列列表：新增、改名、删除；删除系列后，已绑定的产品回到未知

## 5. API

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| POST | `/api/v1/products` | 手工新增产品（需 `manufacturer_id`；同厂商同系列同名返回 409） |
| GET | `/api/v1/products?release_channel=pb` | 按渠道筛选（可选） |
| POST | `/api/v1/products/bulk` | 批量新增（全成全败，单次 ≤500 条） |
| GET | `/api/v1/products/{id}/review-items` | 该产品关联的审核记录 |
| GET | `/api/v1/manufacturers` | 厂家列表（`category` / `q` / `limit`） |
| POST | `/api/v1/manufacturers` | 新建厂家 |
| PATCH | `/api/v1/manufacturers/{id}` | 分类/等级/排序/改名 |
| DELETE | `/api/v1/manufacturers/{id}` | 有产品时 409 |
| POST | `/api/v1/manufacturers/{id}/merge` | 合并厂家，body `{"target_id": "..."}` |
| GET | `/api/v1/product-lines?manufacturer_id=...` | 某厂家的系列 |
| POST | `/api/v1/product-lines` | 新建系列 |
| PATCH | `/api/v1/product-lines/{id}` | 系列改名/排序 |
| DELETE | `/api/v1/product-lines/{id}` | 删除系列，产品回到未知 |
| GET | `/api/v1/review/stats` | 队列计数（含 skipped / later） |
| GET | `/api/v1/review/items?state=pending&sort=brand` | 待审列表（`q` 搜索、分页） |
| POST | `/api/v1/review/{id}/map` | 关联到已有产品，body `{"product_id": "..."}` |
| POST | `/api/v1/review/{id}/create` | 新建产品，body 需 `manufacturer_id`，可选 `product_line_id` / `work` / `release_channel` |
| POST | `/api/v1/review/{id}/skip` | 跳过，body `{"reason": "later"}` |
| POST | `/api/v1/review/{id}/reset` | 退回待审（清空 product_id / skip_reason / 厂家/系列匹配） |
| PATCH | `/api/v1/products/{id}` | 编辑产品字段（改名/换厂商查重） |
| DELETE | `/api/v1/products/{id}` | 删除产品，关联审核记录退回待审，收藏集目标级联删除 |
| GET | `/api/v1/media/{video_id}?date=YYYYMMDD` | 本地视频（Range） |

## 6. 运行

```bash
docker compose up -d api frontend
.venv-tools/bin/python -m tools.seed_review_queue   # 幂等，可重复执行
# 打开 http://127.0.0.1:5173/#review（或 .env 里的 FRONTEND_PORT）
```

项目**不再内置 CSV/Excel 导入器**。CSV、表格或爬虫数据由外部工具自行解析、校验成
产品字段后，先查 `manufacturers` / `product_lines` 拿 ID，再调用
`POST /api/v1/products`（单条）或 `POST /api/v1/products/bulk`（批量）写入；本项目只对字段做基础校验
（名称/厂商必填、系列归属、同厂商同系列同名查重）。**导入器不要自动建厂**，匹配不到就留给人工处理。

## 7. 未来缺口怎么接

- **再版**：先当作一个新产品条目（名称里带“再版”），或在需要时加
  `product_releases(product_id, released_on, label, price)`。不要为此恢复通用事件表。
- **价格曲线**：加 `price_history(product_id, observed_on, price, source)`。
  `review_items.price_raw + event_date` 可以作为回填来源。
- **产品状态**：真需要“现在处于什么阶段”时，加一个 `products.status` 单字段即可，
  不需要时间线；历史仍然不是需求。
- **通用历史**：`review_items` 按 `product_id + event_date` 回放就是原始审计记录，
  需要展示时再建视图。

## 8. 已知取舍

1. 映射不会更新产品字段（价格/编号改不了），修正走后台管理
2. 查重只做 `(manufacturer_id, product_line_id, kit_name)` 精确匹配；不同厂商或不同系列同名算不同产品；没有别名/模糊归并；渠道不参与查重
3. 删产品会退回审核记录，但已经删除的 mention 不会回到队列
4. 队列按 mention 组织，同一产品的多条 mention 仍会分别出现；重复内容靠跳过处理
