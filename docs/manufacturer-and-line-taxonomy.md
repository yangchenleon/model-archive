# 厂家与系列：分类、等级与后台管理方案

> 这一版先不动代码、不动数据库，只梳理需求、方案和需要拍板的点。
>
> 核心判断：**厂家表值得做；系列表也值得做，但必须是“按厂家归属的平铺系列”，不要做层级，也不要把渠道塞进系列。** 否则复杂度会失控。
>
> 数据备份按你的要求跳过；迁移用事务 + 分步加列/切列，避免一次性不可逆。

## 一、需求拆解

你说的其实是四件事，不要混成一件：

1. **厂家主数据**
   - 现在 `products.manufacturer` 是自由文本，84 个值。
   - 要变成 `manufacturers` 表 + `products.manufacturer_id`。
   - 同厂异写用别名解决；厂家删除/合并要可控。

2. **厂家分类 + 等级 + 隐藏排序**
   - 分类：官方 / 国模 / KO / GK / 其他。
   - 等级：一级国模、一级 KO……数字等级，个人排序，没有客观标准。
   - 隐藏排序：后台有排序权重，前台按“分类 → 等级 → 权重 → 产品数”排。
   - 这些都由后台动态调整。

3. **系列（产品线）表**
   - 现在 `products.product_line` 是自由文本，90 个值、185 个“厂家-系列”组合。
   - 要做 `product_lines` 表，让后台按厂家配置系列。
   - 范围外/空值 → 未知；删除系列 → 已绑定的产品回到未知。
   - **系列可能细分渠道**：这是另一个维度，不能塞进系列层级。

4. **后台管理**
   - 厂家管理：分类、等级、排序、别名、合并、删除。
   - 系列管理：按厂家增删改、看使用量、删除时回退未知。
   - 产品编辑：选厂家、选系列；审核入库也要能匹配。

## 二、现状数据（决定方案规模）

| 指标 | 数值 |
| --- | ---: |
| 产品 | 1254 |
| 厂家 | 84 |
| 厂家-系列组合 | 185 |
| 系列名去重 | 90（含“未知”） |
| 产品线为“未知”的产品 | 36 |
| 只有 1 款产品的厂家 | 35 |
| 前 6 厂家产品占比 | 61.5% |

系列名的分布很能说明问题：

- 跨厂家通用的：`HG`（13 个厂家）、`MG`（15 个）、`HGUC`（8 个）、`RG`（7 个）、`MGSD`（4 个）……
- 厂家专属的：`66系列` / `88系列`（大班）、`忠勇级` / `威远式`（摩动核）、`圆桌骑士团系列`（SNAA）、`金恩系列` / `扎古系列` / `厄运式系列`（幻影模型）……
- 还有 `放大RG`（6 个厂家）、`1/100`（3 个）、`TV-00` 这类既不是纯等级、也不是纯厂牌的标签。

结论：

- **厂家是稳定的主维度**，先做。
- **系列是“厂家内的标签”**，跨厂家并不完全一致；不要强行做全球统一层级。
- 90 个系列 / 185 个组合，人工治理一次是可行的；但不要指望自动合并。

## 三、方案对比

### 方案 A：只做厂家表，系列继续字符串

- 厂家表 + 分类/等级/排序 + 后台。
- `products.product_line` 暂时不动。
- 优点：最快，先解决“厂家看不过来”。
- 缺点：系列仍然是自由文本；后台不能配置系列；删除/改名不能级联；以后还要再迁一次。

### 方案 B：厂家表 + 按厂家归属的平铺系列表（推荐）

- `manufacturers` + `manufacturer_aliases`。
- `product_lines`：**每个厂家自己的系列**，平铺，无层级。
- `products.manufacturer_id` 必填；`products.product_line_id` 可空（空 = 未知）。
- 分类/等级/排序在厂家表。
- 渠道不放进系列表，以后单独加 `products.release_channel`。
- 优点：
  - 后台可以按厂家配置系列；
  - 删除某厂家的系列只影响这个厂家（安全）；
  - 系列改名，产品自动跟着改；
  - 删除系列 → 产品回到未知，符合你的要求。
- 缺点：
  - `HG` 会在多个厂家各有一行（185 行而不是 90 行）；
  - 厂家合并时，系列也要合并/映射；
  - 跨厂家的“所有 HG”统计需要按系列名聚合，不能只靠一个全局 line_id。

### 方案 C：厂家表 + 全局系列表 + 层级 + 渠道表

- 一个全局 `product_lines(name, parent_id, channel_id, ...)`。
- 优点：最“规范”，适合做 78 动漫式的大全。
- 缺点：
  - 90 个系列要先决定父子关系（HG → HGUC → HG GTO？）；
  - 渠道和系列混在一起，删除一个全局系列会影响所有厂家；
  - 数据治理量最大，最容易做成一个没人维护的树。
- **不建议现在做。**

### 推荐

**方案 B。** 理由：

- 你现在的浏览方式是“先厂家，再系列”，不是“先系列，再厂家”；
- 删除系列的业务语义是“这个厂家的这个系列不要了”，不是“全库的 HG 都不要了”；
- 185 行系列是可控的，90 行全局反而会在删除时误伤。

## 四、推荐的数据模型

### 4.1 厂家

```sql
manufacturers (
    id          uuid primary key,
    name        varchar(120) not null unique,
    category    varchar(16),          -- official / guomo / ko / gk / other；null = 未分类
    tier        smallint,             -- 1..9；null = 未分级；1 = 一级
    sort_order  integer not null default 0,  -- 同级内隐藏排序
    description text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    check (category in ('official','guomo','ko','gk','other') or category is null),
    check (tier between 1 and 9 or tier is null)
)
```

- `category`：厂家只有一个主分类；以后要“多标签”再加关联表，不要一开始就多对多。
- `tier`：分类内的等级，数字越小越靠前；null = 未分级。
- `sort_order`：同级内排序；后台可改，前台不显示。
- 分类建议：
  - `official` 官方（万代等）
  - `guomo` 国模原创
  - `ko` KO / 翻模
  - `gk` GK / 树脂改件
  - `other` 其他（已知但不属于以上）
  - `null` 未分类
- 初始只填你明确说的：
  - 摩动核、和模线：`guomo`，tier 1
  - 长龙、猛虎模型：`ko`，tier 1
  - 万代：`official`，tier 1
  - 其余全部 `null`（未分类），后台再批量整理
- B社：先 `null`，确认是不是万代后再合并/归类。

### 4.2 厂家别名

```sql
manufacturer_aliases (
    id              uuid primary key,
    manufacturer_id uuid not null references manufacturers(id) on delete cascade,
    alias           varchar(120) not null unique,
    created_at      timestamptz not null default now()
)
```

用途：

- 审核入库/外部导入把 `B社`、`猛虎` 这类旧写法映射到规范厂家；
- 搜索时也能命中别名；
- 不作为前台主显示。

> 猛虎/瘦虎两组已经在产品表里合并；别名表仍建议保留，防止以后审核/导入再写出旧名。

### 4.3 系列（按厂家）

```sql
product_lines (
    id              uuid primary key,
    manufacturer_id uuid not null references manufacturers(id) on delete cascade,
    name            varchar(120) not null,
    sort_order      integer not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (manufacturer_id, name)
)
```

- **平铺，没有 parent_id。**
- 系列属于一个厂家；`(manufacturer_id, name)` 唯一。
- 删除系列：`products.product_line_id ON DELETE SET NULL` → 未知。
- 删除厂家：如果还有产品，`RESTRICT` 拒绝；先合并/迁移产品。厂家没有产品时，系列可以级联删除。
- 不在系列表里放渠道。渠道是产品的另一个字段。

### 4.4 产品

```sql
products (
    ...
    manufacturer_id uuid not null references manufacturers(id) on delete restrict,
    product_line_id uuid references product_lines(id) on delete set null,
    ...
)
-- 产品身份：(manufacturer_id, kit_name)
-- product_line_id 可空；空 = 未知
```

- 产品线为空 → 前台显示“未知”，后台筛选“未归类”。
- 产品改厂家时：如果原系列不属于新厂家，必须重置为 `NULL` 或让用户重新选；后台要做校验。
- 产品线改名：产品自动跟着显示新名字，不需要批量更新。
- 产品身份不包含系列；系列只是分类，不参与查重。

### 4.5 审核记录

```sql
review_items (
    ...
    brand               varchar(120),  -- 保留原始抽取
    line                varchar(120),  -- 保留原始抽取
    manufacturer_id     uuid references manufacturers(id) on delete set null,
    product_line_id     uuid references product_lines(id) on delete set null,
    ...
)
```

- `brand` / `line` 原文保留，作为审计。
- 新增可空外键，用于“匹配到哪个厂家/系列”。
- 新建产品时，优先用匹配到的 `manufacturer_id` / `product_line_id`；匹配不到就留在未分类，不自动创建新厂家。

### 4.6 渠道（暂不做，但先留好边界）

渠道不是系列层级，不要做成 `series → channel` 的树。以后单独加：

```sql
products.release_channel varchar(16)  -- regular / limited / pb / event / other；null = 未知
```

这样以后“RG 通贩制霸”可以按 `product_line_id + release_channel` 过滤，而不是在系列表里塞“RG通贩”“RG限定”这种组合。

## 五、删除、合并与级联规则

| 操作 | 规则 |
| --- | --- |
| 改厂家名 | 只改 `manufacturers.name`，产品/审核记录通过外键自动显示新名 |
| 合并厂家 A → B | 把 A 的产品移到 B；A 的系列按名字映射到 B 的系列（同名复用，不同名新建）；A 的别名移到 B（冲突则手工处理）；删除 A |
| 删除厂家 | 有产品则 `RESTRICT` 拒绝；先合并/迁移。没有产品时可删除，系列/别名级联 |
| 删除系列 | `products.product_line_id` 置 NULL（未知），然后删除系列 |
| 系列改名 | 只改 `product_lines.name`；产品不动 |
| 产品改厂家 | 校验系列是否属于新厂家；不属于则置 NULL（未知）并提示 |
| 删除产品 | 不影响厂家/系列；现有审核记录退回逻辑不变 |
| 删除审核记录 | 不影响厂家/系列 |

## 六、后台管理

建议把现有“后台管理”（`/#admin`）扩成三个 tab：

### 6.1 厂家

- 列表：厂家名、分类、等级、隐藏排序、产品数、系列数、别名数。
- 筛选：分类（含“未分类”）、等级（含“未分级”）、搜索。
- 行内/批量编辑：分类、等级、排序。
- 操作：
  - 改名；
  - 别名管理；
  - 合并到另一个厂家（带预览：产品 N、系列 M、别名 K）；
  - 删除（有产品时禁用，提示先合并）。
- 排序：按分类 → 等级 → 排序 → 产品数；前台厂家目录用同一顺序。

### 6.2 系列

- 按厂家筛选；列表：系列名、产品数、排序。
- 新增/改名/删除；删除前提示“N 款产品会回到未知”。
- 支持把两个系列合并（产品移到目标系列）。
- 不建议做拖拽层级；`sort_order` 足够。

### 6.3 产品

- 产品编辑表单：厂家（必选）+ 系列（可选，按厂家过滤，含“未知”）+ 渠道（以后）。
- 改厂家时，系列自动清空/要求重选。
- 审核入库：品牌/系列字段匹配到厂家/系列；匹配不到时显示“未分类”，由人工选，不自动建厂家。

### 6.4 前台

- 厂家目录：按分类分组/筛选；分类内按等级/排序；等级默认不显示成“官方认证”之类的徽章，只影响顺序（“隐藏排序”）。
- 厂家页：只显示该厂家的系列 chips。
- 产品卡片/详情：显示厂家 + 系列（未知显示“未知”）。

## 七、迁移顺序（不做备份，但分步降低风险）

### 第 1 步：建表 + 加可空外键

- 建 `manufacturers` / `manufacturer_aliases` / `product_lines`。
- 回填 84 个厂家；按你给的四家填分类/等级，其余 null。
- 按 `(manufacturer, product_line)` 建 185 个组合中除“未知”之外的系列（约 162 个）。
- `products` 加 `manufacturer_id`、`product_line_id`，暂时可空；回填。
- 先不删 `products.manufacturer` / `product_line` 字符串。

### 第 2 步：切换读写

- 产品 API/后台/审核页改为用 `manufacturer_id` / `product_line_id`。
- 写产品时同时写一份旧字符串（过渡期），或只写新外键、旧列留空。
- 验证：每个产品都有 manufacturer_id；product_line_id 为空的都是“未知”。

### 第 3 步：收口

- `products.manufacturer_id` 设为 NOT NULL。
- 删除 `products.manufacturer` / `product_line` 字符串列。
- 产品身份唯一约束改为 `(manufacturer_id, kit_name)`。
- 审核记录保留原始 `brand` / `line` 字符串，并加外键。

### 第 4 步：渠道（可选，后做）

- 加 `products.release_channel`；先全部 null/未知，后台慢慢填。
- 不要把它塞进 `product_lines`。

## 八、需要你拍板的点

按优先级：

1. **分类是单选还是多标签？**
   - 建议：厂家只有一个主分类（官方/国模/KO/GK/其他/未分类），以后需要再加 tags。

2. **分类枚举是否就这五类 + 未分类？**
   - `official / guomo / ko / gk / other / null`。
   - “国模”是否包括所有中国原创品牌？“KO”和“国模”会不会有重叠？需要定义。

3. **等级和排序是否只影响顺序、前台不显示？**
   - 建议：分类可见（可筛选），等级/排序后台可见、前台只影响顺序，不显示“一级/二级”徽章。
   - 如果你希望前台显示等级徽章，也可以，但那是另一种产品语言。

4. **系列是“按厂家归属”还是“全局字典”？**
   - 建议按厂家归属（方案 B），删除只影响该厂家；
   - 代价是 HG/RG 会在多个厂家重复。

5. **系列是否需要父子层级？**
   - 建议先平铺：HG、HGUC、HG GTO 各是一条；后台可以改名/合并。
   - 需要层级时再加 `parent_id`，不要现在做。

6. **渠道是否本期做？**
   - 建议本期不做，只留 `products.release_channel` 的设计边界；
   - 先治理厂家 + 系列，避免“系列/子系列/渠道”三层同时上。

7. **删除厂家怎么处理？**
   - 建议：有产品时禁止删除，只能“合并到另一个厂家”；
   - 没有产品时才允许删除。

8. **审核/导入遇到未知厂家/系列怎么办？**
   - 建议：厂家按别名匹配；匹配不到就留在“未分类”，由人工在后台选，不自动创建新厂家；
   - 系列匹配不到 → 未知，不自动建系列。

9. **初始分类/等级只填你点名的几家，其余留空？**
   - 建议：只填 摩动核、和模线（国模 T1）、长龙、猛虎模型（KO T1）、万代（官方 T1）；其余未分类。
   - 这样不会用我的猜测污染你的个人分级。

10. **旧字符串列什么时候删？**
    - 建议两步：先加外键并切换，再删字符串列；中间留一版回退空间。
    - 你说了不备份，那就更需要“先加列、后删列”，不要一步 drop。

## 九、一句话建议

**做方案 B：厂家表 + 分类/等级/隐藏排序 + 按厂家归属的平铺系列表 + 后台管理；渠道以后单独加，层级不做。**
这样能解决“厂家太多看不过来”和“系列太乱”的两层问题，又不会掉进“系列→子系列→渠道”的无限细分。

确认上面的 10 个点后，再开始建表和改后台；在那之前不动数据库。
