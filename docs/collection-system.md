# 收藏集：人定范围 + 资产进度

> 已实现（2026-10-28）。最终口径：**产品级、只收录已录入的产品、不做占位、不做规则/候选、不设难度字段**。
>
> 基于库内数据：1254 个产品、0 台资产、84 个厂商、875 条审核记录。

## 结论先行

1. **收藏集 = 名字 + 描述 + 一张目标清单。清单就是范围，范围就是清单。**
2. **两张表**：`collections`（收藏集）+ `collection_items`（一个目标一行）。进度不落库，从 `assets` 派生。
3. **一个目标 = 一个已录入的产品**。不占位：目标缺口等产品表补录后再加入。
4. **拥有 = 该产品至少有一台 `state != 'sold'` 的资产；已拼 = 资产处于 `displayed / stored`，或 `built_on` 已填。**
5. **同款多台只算一次**；曾经拥有（已售）不算拥有，只做注脚。
6. **进度条三段**：已拼 / 已拥有未拼 / 缺口。清单只有三个筛选：**全部 / 已拥有 / 未拥有**。
7. **“完成”是派生徽章，不是 `status`。** `status` 只表达意图：构想 / 进行中 / 暂缓 / 放弃。
8. **不设难度字段**：难度、注意事项都写在 `description` 里。不做规则、候选、愿望单。

---

## 一、现状与边界

| 指标 | 数量 | 说明 |
| --- | ---: | --- |
| 产品 | 1254 | 一个产品 = 厂商 + 模型名（版本/配色在名称括号里） |
| 厂商 | 84 | `manufacturers` 表；已合并同厂异写，不做别名表 |
| 万代 | 43 | 全部是 RG，编号 `01`–`43` |
| 系列 `RG` | 110 | 其中 67 个是第三方（高高、大班、星动等） |
| 名称含“扎古” | 72 | 跨厂商、跨比例 |
| 名称含“夏亚” | 15 | 不含沙扎比、百式、夜莺等夏亚机体 |
| 资产 | 0 | 进度暂时都是 0，这是正常的 |

这组数字说明：目录既混杂又不完整。

- `product_line_id` 指向厂家自己的系列；`RG` 在多个厂家各是一条，不能当成全局唯一系列。
- 厂名已经规范化，但同一个“扎古/夏亚”仍会跨系列、跨比例。
- “夏亚全制霸”这种语义集合，靠名称关键词一定会漏。
- 万代 RG 只有 43 个，现实中的 RG 远不止这些。

因此：**范围只能由人一条条给，系统不猜。** 只给已经录入的产品；目录里没有的目标，等补录后再加。

旧迁移 `0003` 删除过 `collection_targets`：

```text
collection_targets(collection_name, catalog_item_id, decision, priority, reason, rule_version)
```

它没有收藏集实体、没有描述/状态/时间，`decision` 还把“想收/已拥有”混在一起。新设计拆成：**实体（collections）+ 目标（items）+ 派生进度（assets）**。

---

## 二、领域模型

```text
collections 1 ─── n collection_items n ─── 1 products 1 ─── n assets
     │                    │                                  │
   意图/描述/状态        目标（必须是已录入产品）             现实（拥有/已拼/已售）
     └────────────────────── 进度 = 读时连接 ──────────────────┘
```

| 概念 | 一行是什么 | 谁写 |
| --- | --- | --- |
| `collections` | 一个“我想收齐的套” | 人 |
| `collection_items` | 这个套里的一个目标 | 人 |
| `products` | 目录里的一个发行物 | 入库流程 / 后台 |
| `assets` | 我实际拥有的那一台 | 买入 / 登记 |
| 进度 | 目标 → 产品 → 资产 的连接结果 | 不存，读时算 |

关键点：

- **资产不挂 `collection_id`。** 一台 RG 夏亚扎古同时属于“RG 扎古全制霸”和“夏亚全制霸”；资产属于现实，不属于某个计划。
- **目标挂产品，不挂资产。** 目标是“要收哪一款”，资产是“已经有了几台”。同款两台不产生两个目标。
- **一个产品可以同时属于多个收藏集。**
- **收藏集不是标签。** 标签适合横向标记；收藏集还需要描述、状态、未完成目标、进度，标签撑不住。

---

## 三、范围：只加已录入的产品

### 3.1 两种加目标方式

1. **从目录选**：搜索产品，勾选加入。适合“夏亚全制霸”这种语义集合。
2. **筛选后批量选**：在弹窗里按厂商/系列/名称临时过滤，全选当前结果加入。适合“高高制霸”这种 302 款的大集合。

两种方式最终都落到同一张 `collection_items`，进度算法没有分支。

### 3.2 不占位

目标必须是 `products` 里已经存在的行，`collection_items.product_id` **NOT NULL**。

- 目录里还没录的机体，**等产品表补录后再加入**；收藏集里不会出现“没有产品链接的占位行”。
- 因此没有“未入库”数量、没有“关联产品”、没有“新建产品并关联”这些流程。
- 如果某个产品被删除（且没有资产引用），它的收藏集目标通过外键 `ON DELETE CASCADE` 一起删除；范围自然缩小。

### 3.3 不做规则、候选、难度

- **不保存筛选条件。** 弹窗里的过滤只是一次性的找产品工具，关掉就没了。
- **不生成候选。** 你觉得该加，就自己搜出来加。
- **不自动跟随目录。** 目录新增产品不会改变任何收藏集的 `total`；要加，手动加。
- **不做名称语义推断。** “夏亚”不会自动关联到沙扎比、百式、夜莺。
- **不设难度字段。** 难度、停产、海景、渠道，都写进 `description`；每条目标也可以写 `note`。

### 3.4 四个例子

| 收藏集 | 范围怎么落 | 说明 |
| --- | --- | --- |
| RG 扎古全制霸 | 手工选万代 RG 的 3 款扎古：`02` 夏亚扎古、`04` 量产扎古、`26` 强尼莱登扎古 | 以后出了新的 RG 扎古，想加再手动加 |
| 夏亚全制霸 | 手工跨线选：夏亚扎古、魔蟹、勇士、百式、沙扎比、夜莺…… | 名称含“夏亚”只有 15 款，不能靠关键词 |
| 高高制霸 | 加目标弹窗里临时过滤厂商=高高，全选 302 款，一次加入 | 过滤不保存；以后新增的高高产品手动补 |
| RG 通贩制霸 | 手工选当前万代 RG 的 43 款 | 目录没有“通贩”字段；需要时靠人挑 |

### 3.5 目标粒度

v1 采用**产品级**：一个目标 = 一个具体产品（含版本/配色）。

- “HG 夏亚扎古”和“RG 夏亚扎古”是两个目标。
- 如果以后想要“每个机体收一台，不限比例”，那需要引入“一个目标对应多个可接受产品”的分组；先不做，等真的需要再谈。

---

## 四、进度

### 4.1 定义

对一个收藏集的目标集合：

| 指标 | 定义 |
| --- | --- |
| `total` | 目标行数 |
| `owned` | 目标产品存在至少一台 `state != 'sold'` 的资产 |
| `built` | 目标产品存在未售资产，满足 `state in ('displayed','stored')` 或 `built_on IS NOT NULL` |
| `unbuilt` | `owned - built`（已拥有但还没拼/留盒） |
| `missing` | `total - owned` |
| `sold_only` | 有已售资产、但没有任何未售资产的目标数（`missing` 的子集，只做注脚） |
| `extra_copies` | 同一目标下未售资产数超过 1 的“多出来的台数”之和 |
| `percent` | `total > 0 ? round(owned * 100 / total, 1) : 0` |
| `completed` | `total > 0 && owned == total` |

注意：

- **多台不加分。** 同款买三台，`owned` 还是 1，`extra_copies` 是 2。
- **已售不算拥有。** 默认进度是“现在手里有没有”，不是“曾经有没有”。`sold_only` 只显示“另有 N 款已售出”。
- **没有 0/0 = 100%。** `total = 0` 时显示“未定义范围”。
- **完成是派生的**，不写 `status`；卖出一台后进度掉下来，徽章自动消失。
- **没有同步任务**：资产新建、状态变化、删除都会在下一次读取时反映；收藏集不缓存进度。

### 4.2 清单的三个筛选

只有三个：

- `all` 全部
- `owned` 已拥有（资产表中除 `sold` 的所有状态）
- `missing` 未拥有（包含只卖过、现在没有的）

不提供“未拼 / 未入库 / 已售”作为筛选；已拼/未拼只在进度条和行内状态里表达。

### 4.3 SQL 草图

```sql
WITH item AS (
  SELECT i.id, i.product_id,
         EXISTS (SELECT 1 FROM assets a
                 WHERE a.product_id = i.product_id AND a.state <> 'sold') AS owned,
         EXISTS (SELECT 1 FROM assets a
                 WHERE a.product_id = i.product_id
                   AND a.state <> 'sold'
                   AND (a.state IN ('displayed','stored') OR a.built_on IS NOT NULL)) AS built,
         EXISTS (SELECT 1 FROM assets a
                 WHERE a.product_id = i.product_id AND a.state = 'sold') AS sold
  FROM collection_items i
  WHERE i.collection_id = :collection_id
)
SELECT count(*)                              AS total,
       count(*) FILTER (WHERE owned)         AS owned,
       count(*) FILTER (WHERE built)         AS built,
       count(*) FILTER (WHERE NOT owned AND sold) AS sold_only
FROM item;
```

实现上为了简单，列表页一次读集合、一次读目标、一次按产品聚合资产，在 Python 里组装；当前规模足够快。

### 4.4 一个算例

“RG 扎古全制霸”有 3 个目标：

| 目标 | 产品 | 资产 | owned | built |
| --- | --- | --- | :---: | :---: |
| 夏亚专用扎古 II | RG 02 | 一台 `pending` | ✓ | ✗ |
| 量产型扎古 II | RG 04 | 一台 `displayed` | ✓ | ✓ |
| 强尼莱登专用扎古 II | RG 26 | 无 | ✗ | ✗ |

```text
total = 3, owned = 2, built = 1, unbuilt = 1, missing = 1
percent = 66.7%
进度条：[已拼 1][已拥有未拼 1][缺口 1]
```

---

## 五、数据模型

### 5.1 DDL

```sql
CREATE TABLE collections (
    id              uuid PRIMARY KEY,
    title           varchar(160) NOT NULL UNIQUE,
    description     text,
    status          varchar(16) NOT NULL DEFAULT 'active',
    started_on      date,
    target_on       date,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_collections_status
        CHECK (status IN ('planning', 'active', 'paused', 'abandoned'))
);

CREATE TABLE collection_items (
    id             uuid PRIMARY KEY,
    collection_id  uuid NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    product_id     uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    note           text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_collection_items_product UNIQUE (collection_id, product_id)
);

CREATE INDEX ix_collections_status ON collections(status);
CREATE INDEX ix_collection_items_collection_id ON collection_items(collection_id);
CREATE INDEX ix_collection_items_product_id ON collection_items(product_id);
```

迁移 `0021_collections`，`down_revision = '0020_tag_retirement'`。

### 5.2 `collections`

| 字段 | 含义 | 备注 |
| --- | --- | --- |
| `id` | UUID 主键 | 不对外暴露 |
| `title` | 收藏集名称 | 必填，唯一，去首尾空格 |
| `description` | 描述：为什么收、收哪些、难度和注意事项 | 纯文本，保留换行；难度也写这里 |
| `status` | `planning / active / paused / abandoned` | 只表达人的意图，不表示完成 |
| `started_on` | 人定义的开始日期 | 业务事实，可和 `created_at` 不同 |
| `target_on` | 期望完成日期 | 可空 |
| `created_at` | 建档时间 | 系统事实 |
| `updated_at` | 最近一次改动 | 加/删目标、改描述时由服务层触碰 |

### 5.3 `collection_items`

| 字段 | 含义 | 备注 |
| --- | --- | --- |
| `id` | UUID 主键 | |
| `collection_id` | 所属收藏集 | 级联删除 |
| `product_id` | 必须是已录入产品 | 产品删除时级联删除该目标 |
| `note` | 目标备注：等再版、预算、渠道 | 和资产备注分开：这里写“计划”，资产写“实物” |
| `created_at` | 加入时间 | 可用于“最近加入” |

唯一约束 `(collection_id, product_id)`：同一个收藏集不能重复加同一个产品。

### 5.4 为什么没有这些字段/表

- **没有 `display_name` / `expected_code` / `product_id` 可空**：不占位，目标只能是已录入产品。
- **没有 `difficulty` / `difficulty_note`**：难度是描述的一部分；不做一个可排序但没人维护的枚举。
- **没有 `scope_filter`**：范围就是 `collection_items` 里那些行，再存一份筛选条件等于给范围造第二个事实来源。
- **没有进度表**：进度完全由 `assets` 推导，存一份就会漂移。
- **没有 `position`**：目标按系列 → 编号 → 名称展示；需要拖拽时再加。
- **没有收藏集事件表**：变化只有加/删目标、改元数据，`updated_at` + 当前清单足够回答。

---

## 六、API 设计

所有接口挂在 `/api/v1`。路由顺序：`/items/bulk`、`/items/bulk-remove` 必须声明在 `/items/{item_id}` 之前。

### 6.1 端点

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/collections` | 列表 + 每个集合的统计；支持 `status`、`q`、`limit` |
| `POST` | `/collections` | 新建 |
| `GET` | `/collections/{id}` | 详情 + 统计 |
| `PATCH` | `/collections/{id}` | 改标题/描述/状态/日期 |
| `DELETE` | `/collections/{id}` | 删集合（级联目标；不动产品/资产） |
| `GET` | `/collections/{id}/items` | 目标列表；`state=all/owned/missing`、`q`、分页 |
| `POST` | `/collections/{id}/items` | 加一个已录入产品 |
| `POST` | `/collections/{id}/items/bulk` | 批量加产品；已存在跳过，返回 `added/skipped` |
| `POST` | `/collections/{id}/items/bulk-remove` | 批量移除目标；只动清单 |
| `PATCH` | `/collections/{id}/items/{item_id}` | 改目标备注 |
| `DELETE` | `/collections/{id}/items/{item_id}` | 从范围移除 |
| `GET` | `/products/{id}/collections` | 产品详情页反查：属于哪些收藏集、是否已拥有 |

没有 `/candidates`、没有 `/scope`、没有占位目标相关接口。

### 6.2 响应形状

`GET /collections`：

```json
[
  {
    "id": "6f1c...",
    "title": "RG 扎古全制霸",
    "description": "万代 RG 的扎古系，只收通贩。难度：两款长期不再版。",
    "status": "active",
    "started_on": "2026-01-01",
    "target_on": null,
    "created_at": "2026-10-28T10:00:00+08:00",
    "updated_at": "2026-10-28T10:00:00+08:00",
    "stats": {
      "total": 3,
      "owned": 2,
      "built": 1,
      "unbuilt": 1,
      "missing": 1,
      "sold_only": 0,
      "extra_copies": 0,
      "percent": 66.7,
      "completed": false
    }
  }
]
```

`GET /collections/{id}/items`：

```json
{
  "total": 3,
  "items": [
    {
      "id": "a1...",
      "product_id": "b2...",
      "name": "MS-06S 夏亚专用扎古II",
      "manufacturer": "万代",
      "product_line": "RG",
      "product_code": "02",
      "note": null,
      "owned": true,
      "built": false,
      "sold_only": false,
      "asset_count": 1,
      "asset_states": ["pending"],
      "sold_count": 0
    }
  ]
}
```

加目标：

```json
{ "product_id": "b2..." }
```

批量加：

```json
{ "product_ids": ["b2...", "b3...", "b4..."] }
```

返回：

```json
{ "added": 2, "skipped": 1 }
```

批量移除：

```json
{ "item_ids": ["a1...", "a2..."] }
```

返回：

```json
{ "removed": 2 }
```

### 6.3 错误语义

| 场景 | 状态码 | 文案 |
| --- | --- | --- |
| 收藏集不存在 | 404 | 收藏集不存在 |
| 目标不存在 / 不属于该收藏集 | 404 | 目标不存在 |
| 产品不存在 | 404 | 产品不存在 |
| 标题重复 | 409 | 已存在同名收藏集 |
| 单条加目标，产品已在清单 | 409 | 该产品已在此收藏集中 |
| 标题为空 / status 非法 | 422 | 具体字段错误 |
| 批量里有未知产品 | 404 | 产品不存在：… |
| 单次批量超过 500 | 422 | 单次最多 500 条 |

批量加和单条加的区别是刻意的：单条重复报 409；批量全选时重复是正常现象，跳过并报告数量。

补充约定：

- `GET /collections/{id}/items` 的 `state` 只有 `all / owned / missing`；`q` 搜索名称、编号、厂商、系列；`limit` 默认 200、上限 500，`total` 是过滤后的总数。
- 条目响应的 `asset_count` 是**未售台数**，`sold_count` 是已售台数，`asset_states` 只列未售资产的状态。
- 排序：收藏集列表按 `updated_at` 倒序；目标列表按系列 → 编号 → 名称。

### 6.4 与资产页的闭环

不新增“标记完成”接口。收藏集里的“登记一台”就是一次普通的：

```http
POST /api/v1/assets
{ "product_id": "b2...", "state": "pending" }
```

批量登记复用：

```http
POST /api/v1/assets/bulk
{ "product_ids": ["b2...", "b3..."], "state": "pending" }
```

资产建好后，收藏集重新读详情，进度自然变化。只有一个事实来源。

---

## 七、前端设计

### 7.1 导航与路由

- 侧栏新增“收藏集”，图标 `Trophy`，位置在“我的资产”之后、“标签队列”之前。
- 路由沿用 hash：
  - `#collections` 列表
  - `#collections/<uuid>` 详情
- `App.vue` 用 hash 作为唯一路由源；产品抽屉点“所属收藏”跳详情。

### 7.2 收藏集列表

```text
┌ 收藏集 ──────────────────────────────────────────────── [+ 新建收藏集] ┐
│ 进行中 3    已制霸 1    目标 186    已拥有 92                         │
├────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────┐  ┌────────────────────────────┐        │
│ │ RG 扎古全制霸        进行中 │  │ 高高制霸            进行中 │        │
│ │ 万代 RG 的扎古系，只收通贩 │  │ 302 款，慢慢收             │        │
│ │ 2 / 3               66.7% │  │ 41 / 302            13.6% │        │
│ │ ████████████░░░░░░░░░░░░░ │  │ ██░░░░░░░░░░░░░░░░░░░░░░ │        │
│ │ 已拼 1  未拼 1  缺 1       │  │ 已拼 12  未拼 29  缺 261  │        │
│ │ 更新 10-28                │  │ 更新 10-27                │        │
│ └────────────────────────────┘  └────────────────────────────┘        │
└────────────────────────────────────────────────────────────────────────┘
```

- 卡片：标题 → 状态 → 描述（两行截断）→ 进度条 → 数字 → 更新/目标日期。
- `stats.completed` 为真时挂一个金色“已制霸”小徽章。
- 空列表：`Trophy` 图标 + “还没有收藏集。先建一个，再把想要的产品加进来。”
- 筛选：状态、搜索；排序：最近更新 / 进度 / 名称。
- 没有难度圆点。

### 7.3 收藏集详情

```text
← 收藏集
RG 扎古全制霸                                      [编辑] [删除]
万代 RG 的扎古系，只收通贩。难度：两款长期不再版。
进行中 · 2026-01-01 开始 · 更新 10-28

┌ 制霸进度 ──────────────────────────────────────────────────────┐
│ 2 / 3                                                  66.7%  │
│ ████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ ● 已拼 1     ● 已拥有未拼 1     ○ 缺口 1                       │
│ 还差 1 款。                                                     │
└────────────────────────────────────────────────────────────────┘

[全部 3]  [已拥有 2]  [未拥有 1]              搜索...  [+ 添加目标]
┌────────────────────────────────────────────────────────────────┐
│ ☐ MS-06S 夏亚专用扎古II   RG 02  万代·RG   已拼·展示           │
│ ☐ MS-06F 量产型扎古II     RG 04  万代·RG   已拥有·待拼 [登记]  │
│ ☐ MS-06R-2 强尼莱登...    RG 26  万代·RG   缺口        [登记]  │
└────────────────────────────────────────────────────────────────┘
```

行内动作：

- **已拥有**：显示资产状态（待拼/收藏/展示/收纳）和台数。
- **缺口**：显示“登记一台”，创建 `pending` 资产。
- **备注**：行内输入，失焦保存；只写计划，不写实物。
- **移除**：勾选后批量移出，只动清单。
- **批量登记**：勾选多个缺口，一次 `POST /assets/bulk`。

没有“未入库”行、没有“候选补充”tab、没有难度。

### 7.4 进度条组件

`CollectionProgress.vue`，列表和详情复用。

```text
props: built, owned, total, height?
宽度百分比：built / total， (owned - built) / total， (total - owned) / total
```

- 深绿 `#1f6f5c`：已拼；浅绿 `#8fc7b4`：已拥有未拼；灰 `#e6e9e6`：缺口。
- 圆角 999px；`total = 0` 时整条虚线，不显示 0%。
- `role="progressbar"`，`aria-valuemin=0`、`aria-valuemax=total`、`aria-valuenow=owned`；`total = 0` 时不渲染 role。
- 完成时条全满，加“已制霸”徽章；不做撒花动画。

### 7.5 新建/编辑收藏集

表单字段：标题、状态、开始日期、目标日期、描述。

- 标题必填，重复 409 时提示。
- **难度不单独填**；写在描述里。
- 描述是纯文本，支持换行。

### 7.6 添加目标

一个对话框，只有“从产品目录”：

- 搜索/筛选（厂商、系列、名称），多选；
- 已在清单里的产品不显示；
- 提供“全选当前结果”；
- 单次上限 500；
- 没有占位 tab。

### 7.7 与产品目录/资产页的联动

- **产品抽屉**：显示“所属收藏”chips；点击跳转收藏集。
- **快速登记**：收藏集行内“登记一台” → `POST /assets` → toast 显示资产码 → 重新读收藏集。
- **批量登记**：缺口多选 → `POST /assets/bulk`。
- **资产页**：不反向显示收藏集，保持资产页只回答“我有什么”。

### 7.8 命名冲突

资产状态 `keep` 当前 UI 叫“收藏”（不打算拼，留盒）。新增“收藏集”后有歧义。

建议把 `keep` 的 UI 文案改为 **“留盒”**，状态码不变。代码和文档里的 `keep` 不动。

---

## 八、关键取舍

| 决策 | 备选 | 为什么选这个 |
| --- | --- | --- |
| 范围 = 显式清单 | 保存筛选、自动候选 | 范围是人的判断；目录补录会让进度无故变化；不做假智能 |
| 只加已录入产品 | 占位目标 | 目标必须能落到具体产品；缺口等目录补录 |
| 两张表 | 三张表（加进度表） | 进度可派生，存了会漂移；当前规模读时算足够快 |
| 目标挂产品 | 目标挂资产 | 同款多台只算一个目标；资产可以换手、卖出 |
| 资产不挂收藏集 | `assets.collection_id` | 一台可以同时属于多个收藏集 |
| 完成派生 | `status='completed'` | 卖出后进度应掉下来；状态只表达意图 |
| 不做难度字段 | `difficulty` + `difficulty_note` | 难度是描述的一部分；避免一个没人维护的枚举 |
| 三个筛选 | 未拼/未入库/已售 | 用户明确只看全部/已拥有/未拥有；其余在行内状态里表达 |
| 产品级粒度 | 机体级 | 先简单；分组以后再说 |
| 不存手工排序 | `position` + 拖拽 | 按系列/编号/名称已经够用 |
| 纯文本描述 | Markdown/富文本 | 项目没有 Markdown 渲染；纯文本够用 |
| 不做封面图 | 产品图/自定义封面 | 当前目录没有图片资源 |
| 单用户 | 多用户/权限 | 本地个人库 |

---

## 九、实施与验收

### 9.1 已落地

- 迁移 `0021_collections`
- `models.py`：`Collection` / `CollectionItem`
- `schemas.py`：收藏集、目标、统计、批量
- `services/collections.py`：范围、统计、批量、反查
- `api/collections.py`；`api/products.py` 增加所属收藏
- `frontend`：`CollectionsView` / `CollectionDetail` / `CollectionDialog` / `CollectionItemDialog` / `CollectionProgress`
- `tests/test_collections.py`；后端 31 tests 通过

### 9.2 验收场景

1. 新建“RG 扎古全制霸”，加入 3 个产品 → `0 / 3`，进度条全灰，缺口 3。
2. 给 RG 02 登记一台（`pending`）→ `1 / 3`，浅绿 1 格。
3. 把 RG 02 改成 `displayed` → `1 / 3`，深绿 1 格，`built=1`。
4. 再加一台 RG 02 → 进度不变，`extra_copies=1`。
5. 把 RG 02 卖出 → `0 / 3`，`sold_only=1`，进度条回灰。
6. 删除一个没有资产的产品 → 对应目标从收藏集消失，`total` 减 1。
7. 删除收藏集 → 产品、资产、标签都不受影响。
8. 批量加入 302 个“高高”产品 → `total=302`；再次全选加入 → `added=0, skipped=302`，不报错。
9. 清单筛选：全部 / 已拥有 / 未拥有 三个，数量与统计一致。
10. 已售产品不计入“已拥有”；重新买一台后回到“已拥有”。

### 9.3 测试清单

| 测试 | 断言 |
| --- | --- |
| 新建/改名/删除收藏集 | 201/200/200；标题重复 409；删除级联目标，不动产品/资产 |
| 加目标（产品） | 201；重复 409；未知产品 404 |
| 批量加 | 重复跳过；未知产品 404；上限 422 |
| 批量移除 / 单条移除 | 只删目标；产品/资产不变 |
| 进度：无资产 | `total=1, owned=0, missing=1` |
| 进度：pending | `owned=1, built=0` |
| 进度：displayed/stored | `owned=1, built=1` |
| 进度：sold | `owned=0, sold_only=1` |
| 进度：多台 | `owned=1, extra_copies=n-1` |
| 产品删除 | 无资产时级联删目标；有资产时 409 |
| 产品反查收藏集 | 返回所属集合与 `owned` |

---

## 十、后续可选

- **机体级分组**：一个目标对应多个可接受产品（HG/RG/MG 任意一款算完成）；现在产品级，等真的需要再谈。
- **愿望单**：独立建模，不塞进 `collection_items`。
- **进度历史/趋势图**：加 `collection_progress_snapshots`，由显式快照写入。
- **收藏集封面、分享图**。
- **手工拖拽排序**：加 `position`。
- **多用户/权限**：加 `owner_id`。
- **产品发行渠道**：给 `products` 加 `release_channel`（通贩/限定/会场），让“RG 通贩制霸”更容易筛；这是产品目录的事，不阻塞收藏集。
- **导出 CSV**：等有需求再加。

---

## 附：实现文件

```text
backend/
  alembic/versions/0021_collections.py
  app/models.py                 # Collection / CollectionItem
  app/schemas.py                # Collection* / CollectionItem*
  app/services/collections.py   # 范围与统计
  app/api/collections.py        # HTTP
  app/api/products.py           # 产品反查所属收藏集
  app/api/__init__.py           # 注册 router
  tests/test_collections.py
  tests/conftest.py             # 防污染表加 collections / collection_items
frontend/src/
  App.vue                       # 路由 + 页面切换
  collectionMeta.js             # 状态标签/日期格式
  components/SidebarNav.vue     # 侧栏入口
  components/CollectionsView.vue
  components/CollectionDetail.vue
  components/CollectionDialog.vue
  components/CollectionItemDialog.vue
  components/CollectionProgress.vue
  components/ProductDrawer.vue  # 所属收藏
docs/
  collection-system.md          # 本文
  architecture-design.md        # 表结构说明
README.md                       # 入口说明
```
