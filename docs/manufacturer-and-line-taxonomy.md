# 厂家与系列：分类、等级与管理

> 状态：已定稿并落地（2026-10-28，迁移 `0022_manufacturer_taxonomy`）。
>
> 最终口径：**分类只有 高达 / 国模 / KO；等级数字 1–3，数字越大越靠后；不做别名表；系列按厂家归属、平铺、不合并 HG/HGUC/HG GTO；审核/导入不自动建厂。**

## 一、最终口径

1. **厂家是主数据**
   - `manufacturers` 表；`products.manufacturer_id` 必填。
   - 改名只改一处，产品/审核记录通过外键跟随。
   - 有产品的厂家不能直接删，只能合并到另一个厂家。

2. **分类只有三个**
   - `gundam` 高达（目前只有万代）
   - `guomo` 国模
   - `ko` KO
   - `category = NULL` 表示“未分类”，不是第四类；后台单独筛选，逐步归位。

3. **等级 1–3，数字越大越靠后**
   - `tier` 只能 1/2/3，默认 3。
   - 一级 → 二级 → 三级；同级内再用 `sort_order`。
   - 等级/排序是后台的“隐藏排序”，前台不显示“一级/二级”徽章；分类会显示。

4. **不做别名表**
   - 有别名意味着名字写错了；错就改产品/厂家，不维护一张映射表。
   - 审核/导入按**精确名称**匹配；匹配不到就人工在「厂家管理」新建，刷新后重新匹配。
   - 之前的 猛虎 → 猛虎模型、瘦虎 → 瘦虎模型 已直接修数据。

5. **系列按厂家归属，平铺**
   - `product_lines`：`(manufacturer_id, name)` 唯一。
   - HG、HGUC、HG GTO 是**不同系列**，不合并、不做父子层级。
   - 删除系列 → 该系列下的产品 `product_line_id` 置 NULL，前台显示“未知”。
   - 产品改厂家时，如果原系列不属于新厂家，自动回到未知/要求重选。

6. **渠道不塞进系列**
   - 产品单独有 `release_channel`：`regular / pb / limited / event / other`，空 = 未知。
   - 渠道是封闭维度，不是 78dm 的“级别或分类”。例如 SEED 页面里的 `HG SEED HD`、`1/100 SEED` 是 line/规格，`网络限定` 才是 PB 渠道。
   - 不要做“系列 → 子系列 → 渠道”的树。

7. **作品/IP 是第三个正交维度**
   - `products.work` 可空，例如 `EVANGELION`、`勇者王`、`机动警察`、`SEED`。
   - 同一个 `RG` line 下可以有多个作品；不能把 EVA 拆成 `RG EVA` 新 line。
   - 不参与产品身份查重。

## 二、当前数据（迁移后）

| 指标 | 数值 |
| --- | ---: |
| 产品 | 1446 |
| 厂家 | 84 |
| 系列 | 157 |
| 系列为未知的产品 | 30 |
| 未分类厂家 | 0 |
| 系列名去重 | 84 |
| 已标注作品/IP | 18 |

初始分类/等级只填了明确点名的；其余 79 家后来已在后台归类，目前分类为 1 高达 / 21 国模 / 62 KO，未分类为 0：

| 厂家 | 分类 | 等级 |
| --- | --- | ---: |
| 万代 | 高达 | 1 |
| 摩动核 | 国模 | 1 |
| 和模线 | 国模 | 1 |
| 长龙 | KO | 1 |
| 猛虎模型 | KO | 1 |
| 其余 79 家 | 后台归类 | 已分类 |

B社仍是独立厂家；它是否并入万代，需要人工判断，系统不自动合并。

> 目录里原本有 17 组同厂商同名产品（37 行）。现在产品身份改为 `(manufacturer_id, product_line_id, kit_name)`：其中 16 组是“同名但不同系列”，按新规则是合法产品；只剩 **1 组同厂商同系列同名**：大班 / 88系列 / `MB 金异端 天·蜜娜`（编号 8804、8826）。`products` 目前没有数据库唯一约束，只由服务层阻止新增重复；这 1 组需要人工判断是否合并。

## 三、数据模型

```sql
manufacturers (
    id          uuid primary key,
    name        varchar(120) not null unique,
    category    varchar(16),          -- gundam / guomo / ko；null = 未分类
    tier        smallint not null default 3,  -- 1..3
    sort_order  integer not null default 0,
    description text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    check (category is null or category in ('gundam','guomo','ko')),
    check (tier between 1 and 3)
)

product_lines (
    id              uuid primary key,
    manufacturer_id uuid not null references manufacturers(id) on delete cascade,
    name            varchar(120) not null,
    sort_order      integer not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (manufacturer_id, name)
)

products (
    manufacturer_id uuid not null references manufacturers(id) on delete restrict,
    product_line_id uuid references product_lines(id) on delete set null,
    work varchar(120),           -- 作品/IP，例如 EVANGELION；可空
    release_channel varchar(16)  -- regular/pb/limited/event/other；可空
)

review_items (
    brand               varchar(120),  -- 原始抽取，保留审计
    line                varchar(120),  -- 原始抽取，保留审计
    manufacturer_id     uuid references manufacturers(id) on delete set null,
    product_line_id     uuid references product_lines(id) on delete set null
)
```

产品身份：

- 服务层查重使用 `(manufacturer_id, product_line_id, kit_name)`；同厂商同名但不同系列算不同产品，`product_line_id` 为 NULL 时单独一档。
- 系列不参与产品身份。
- 没有 `manufacturer_aliases` 表。

## 四、行为规则

| 操作 | 规则 |
| --- | --- |
| 新建厂家 | 名称必填、唯一；分类可空；等级默认 3；排序默认 0 |
| 改厂家 | 名称查重；分类/等级/排序/描述可改；产品自动跟随 |
| 合并厂家 A → B | 先查同名产品；有冲突则拒绝（先改名/去重）。无冲突时产品移到 B；A 的系列按名字合并到 B（同名复用，不同名移动）；审核记录关联移到 B；删除 A |
| 删除厂家 | 有产品 → 409，提示先合并；没有产品才允许删 |
| 新建系列 | 名称在该厂家内唯一；平铺 |
| 系列改名 | 产品自动显示新名 |
| 删除系列 | 产品 `product_line_id` 置 NULL，前台显示“未知” |
| 产品改厂家 | 原系列不属于新厂家 → 置 NULL（未知） |
| 新建/编辑产品 | 必须选厂家；系列可空（未知）；系列必须属于该厂家 |
| 审核入库 | 不自动建厂；按精确名称匹配，匹配不到人工去「厂家管理」新建，刷新页面再匹配 |
| 外部导入 | 同上；导入器应先查厂家/系列，拿不到 ID 就拒绝或留空，不要写入自由文本 |

## 五、后台管理

侧栏新增 **厂家管理**（`/#taxonomy`）：

- 左侧：84 家厂家，搜索 + 分类筛选；显示产品数、系列数、分类、等级。
- 右侧：
  - 名称、分类、等级（1–3）、同级隐藏排序、描述；
  - 保存、删除；
  - 合并到另一个厂家；
  - 系列列表：新增、改名、删除（显示每个系列的产品数）。
- 删除系列时提示“N 款产品回到未知”。

产品管理（`/#admin`）：

- 新增/编辑产品：厂商选择器支持搜索（84 家）；系列按厂家过滤，可留空为未知。
- 改厂商时系列自动重置，避免跨厂家错绑。

审核页（`/#review`）：

- 厂商选择器支持搜索；系列按厂家过滤。
- 抽取的 `brand` / `line` 仍显示原文；匹配不到时提示去厂家管理新建，刷新后再匹配。
- 没有自动建厂。

前台：

- 厂家目录按 分类 → 等级 → 隐藏排序 → 产品数 排序；分类显示徽章，等级不显示。
- 分类筛选：全部 / 高达 / 国模 / KO / 未分类。
- 厂家页的系列 chips 来自该厂家实际产品；未知显示“未知”。

## 六、API

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/manufacturers` | 列表 + 产品数/系列数；`category`、`q`、`limit` |
| POST | `/manufacturers` | 新建 |
| GET | `/manufacturers/{id}` | 详情 + 计数 |
| PATCH | `/manufacturers/{id}` | 改名/分类/等级/排序/描述 |
| DELETE | `/manufacturers/{id}` | 有产品时 409 |
| POST | `/manufacturers/{id}/merge` | body `{"target_id": "..."}` |
| GET | `/product-lines` | `manufacturer_id`、`q`、`limit` |
| POST | `/product-lines` | `manufacturer_id` + `name` |
| PATCH | `/product-lines/{id}` | 改名/排序 |
| DELETE | `/product-lines/{id}` | 产品回到未知 |

产品接口：

- `POST /products` / `PATCH /products/{id}` 使用 `manufacturer_id`（必填）和 `product_line_id`（可空）。
- 返回仍带 `manufacturer` / `product_line` 名称，便于前端显示。
- 审核创建：`POST /review/{id}/create` 使用 `manufacturer_id` / `product_line_id`。

## 七、迁移

`0022_manufacturer_taxonomy`：

1. 建 `manufacturers` / `product_lines`。
2. 从 `products.manufacturer` 去重建 84 家；种子分类/等级。
3. 从 `(manufacturer, product_line)` 去重建 162 个系列；“未知”不建行，留 NULL。
4. `products` 加 `manufacturer_id` / `product_line_id`，回填。
5. `review_items` 加可空外键，按原名/系列回填。
6. `products.manufacturer` / `product_line` 字符串列删除。
7. `manufacturer_id` 设 NOT NULL。

迁移是不可逆的（`downgrade` 直接报错）；没有做备份，靠事务和分步验证。

## 八、还需要人工做的

这些是后台运营，不是代码：

1. 厂家分类已完成；后续只需要微调等级/排序。
2. 157 个系列的清理：改名、删掉不用的系列、补齐 30 个“未知”产品。
3. B社是否并入万代（目前保留独立）。
4. 只剩 1 组同厂商同系列同名产品（大班 / 88系列 / `MB 金异端 天·蜜娜`，编号 8804、8826）需要人工判断是否合并；其余 16 组同名不同系列已按新规则合法。
5. `work` 目前只填了 18 条非高达 RG（EVANGELION 14、勇者王 3、机动警察 1）；高达系作品留空，等可靠来源再补。

## 九、明确不做

- 别名表：名字错了就改，不维护映射。
- 系列层级/父子：HG/HGUC/HG GTO 各算一条。
- 渠道树：不做；用 `products.release_channel` 单字段，固定枚举。
- 自动建厂/自动建系列：审核/导入只匹配，匹配不到人工建。
- 多分类标签：一家只有一个主分类。
