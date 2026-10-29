# 架构设计（当前收束版）

## 当前目标

产品目录、资产/标签、收藏集三块已经落地。产品是可区分的发行物；资产是实际拥有的那一台；
收藏集是一张人定的、只指向已录入产品的目标清单。

不在当前范围：愿望单、原始 Markdown 或网页资料归档、拼装事件、图片、爬虫、多用户。

## 当前数据表

### `products`

产品目录主数据。一个产品由厂商、系列、模型名称和版本/配色描述；是否因配色或版本拆成不同产品，由目录规则决定。

`products` 只存**固有身份 + 当前价格**；不保存状态、公布/发售时间，也没有事件表。审核入库流程见 [review-workflow.md](review-workflow.md)。

关键字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 内部 UUID 主键，不对用户暴露。 |
| `manufacturer_id` | → `manufacturers`，必填；产品身份的一半。 |
| `product_line_id` | → `product_lines`，可空；空 = 未知。系列不参与身份。 |
| `product_code` | 自由文本，可空；厂商给产品的市场编号。 |
| `kit_name` | 产品识别信息，模型名称必填；版本/配色以括号并入名称。 |
| `price` | 当前价格，自由文本（`78`、`68元`、`22000日元`、`299-398`），不拆数值/币种。 |
| `detail` | 自由补充说明，可空。 |
| `source` | 资料来源；新 CSV 由人工填写，旧测试数据使用“初始化测试”。 |
| `created_at` | 入库时间，只记录插入；没有 `updated_at`。 |

### `manufacturers` 与 `product_lines`

- `manufacturers`：规范厂名、分类（`gundam / guomo / ko`，空 = 未分类）、等级（1–3，数字越大越靠后）、同级隐藏排序、描述。
- `product_lines`：**按厂家归属的平铺系列**，`(manufacturer_id, name)` 唯一；HG、HGUC、HG GTO 是不同系列，不做层级。删除系列 → 产品 `product_line_id` 置 NULL（未知）。
- 没有别名表：名字错了就改，不做映射。
- 后台入口：`/#taxonomy`（厂家管理）。设计见 [manufacturer-and-line-taxonomy.md](manufacturer-and-line-taxonomy.md)。

### `review_items`

审核入库的审计队列：每条抽取 mention 的来源（视频、秒数、evidence）、抽取字段和处理结果
（`pending / mapped / created / skipped`）。`mapped` 只记录“这条 mention 属于哪个产品”，
不修改产品；产品字段修正走后端管理页。

`brand` / `line` 保留原始抽取值；另加可空的 `manufacturer_id` / `product_line_id` 记录匹配结果。审核新建产品时使用这两个 ID，**不自动创建厂家**。

### `assets`、`tags` 与 `asset_state_changes`

资产按“一台一份”记录：`assets` 保存状态与买入/拼装/卖出的事实字段，`tags` 保存物理贴纸（一张贴纸＝一个袋，
每张独立随机码），`asset_state_changes` 只审计状态变动。资产卖出时，其 tags 写入 `retired_at`：离开打印队列，
不能重打/加袋，但行保留为历史。设计取舍（为什么没有通用事件表）见
[asset-and-labels.md](asset-and-labels.md)。

`asset_events` 已删除：`rating` 只属于拼装、`amount` 只属于买卖，挂在同一个 `kind` 上会让每行带着一堆
永远为空的列。资产生命周期是线性的，买、拼、卖各发生一次，所以它们是列而不是行。

### `collections` 与 `collection_items`

收藏集是“人定的产品清单”：`collections` 存标题、描述、状态、日期，`collection_items` 存一个**已录入产品**
和一条目标备注。目标不允许占位，`product_id` 非空；产品删除时目标级联删除。进度不落库，由 `assets` 派生：
已售不算拥有，同款多台只算一次。设计见 [collection-system.md](collection-system.md)。

## 已删除的设计

`collection_targets` 已删除，旧模型没有收藏集实体、没有描述/状态，还把“想收/已拥有”混在一个枚举里。
收藏集现在按 `collections + collection_items` 重新建模，见 [collection-system.md](collection-system.md)。
愿望单仍是独立功能。

## 代码结构

```text
backend/app/
  main.py      组装：注册路由、把领域错误映射成 HTTP 状态码
  api/         URL 与入参：products / review / assets / tags / collections / manufacturers / media
  services/    规则：重复判定、状态迁移与审计、标签作废、收藏集范围与统计、厂家/系列
  models.py    表
  schemas.py   出入参
```

规则和 HTTP 分离：services 抛 `NotFound / Conflict / Invalid`，`main.py` 里一个 handler
统一映射成 404 / 409 / 422；路由只负责解析参数和拼查询。这样同一套规则可以被多个入口
（单条、批量、将来的 CLI 导入器）复用，不需要复制一遍判断。

## 写入原则

1. 产品只通过 API 写入：`POST /api/v1/products`（单条）或 `/api/v1/products/bulk`（批量，全成全败）；前端后台管理也是调用这两个接口。
2. 每条必须提供模型名称、厂商 `manufacturer_id` 与资料来源；系列 `product_line_id` 可空（未知）。
3. 同厂商、同系列、同名视为同一产品，返回 409；查重键是 `(manufacturer_id, product_line_id, kit_name)`。同厂商同名但不同系列允许，未知系列单独一档。改名/合并走后台管理。
4. 项目不解析 CSV/Excel；外部工具负责把格式适配成上述接口的 JSON 字段，并先查厂家/系列 ID。
5. UUID、外键、内部兼容字段不出现在对外的展示字段里；响应仍带厂家/系列名称。

## 下一阶段

资产、标签、收藏集已落地（`/#inventory`、`/#labels`、`/#collections`），产品目录已改为厂家优先
（`/#directory`），厂家/系列分类与后台管理也已落地（`/#taxonomy`，迁移 `0022`）。下一步是后台数据治理：
把 79 家未分类厂家归到 高达/国模/KO，清理 162 个系列，并处理仅剩的 1 组同厂商同系列同名产品。

位置尚未固定，所以**不做**容器/摆放模型；等“某个箱子固定放某几台、并且要按位置找东西”时再加，
用已有的 `assets.id` 关联，标签不用重贴。

愿望单仍是独立功能，在需要时单独建模。收藏集已按“人定范围、产品级目标、从资产派生进度”落地，见
[collection-system.md](collection-system.md)。
