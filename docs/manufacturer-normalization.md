# 厂家目录与厂家表：现状评估

> 结论：**现在用 `products.manufacturer` 字符串做厂家目录已经够用（已实现）；但长期要维护产品表，建议下一步做 `manufacturers` 表 + `products.manufacturer_id`。** 先做表、再回头做收藏集，比以后带着字符串到处补要省事。
>
> 2026-10-28 已直接在数据库合并两组别名：猛虎 → 猛虎模型（18 款）、瘦虎 → 瘦虎模型（2 款）；厂商字符串从 86 降到 84。B社 → 万代仍待确认。
>
> 同日把 33 个空产品线 + 3 个空字符串统一填成“未知”；现在 36 款产品线为“未知”，没有 NULL/空值。
>
> 不建议同时规范化产品线：产品线目前太杂，先把“厂家”这一层做稳。

## 一、现在数据长什么样

以 2026-10-28 合并后的库为准：

| 指标 | 数值 |
| --- | ---: |
| 产品 | 1254 |
| 厂商字符串 | 84（合并前 86） |
| 只出现 1 次（1 款产品）的厂商 | 35 |
| ≤2 款的厂商 | 42 |
| ≤5 款的厂商 | 55 |
| 前 6 个厂商的产品占比 | 61.5% |
| 产品线去重 | 90（含“未知”） |
| 没有产品线的产品 | 0（36 款已统一填“未知”） |

前几名：

```text
高高     302
大班     191
星动     112
集模社    66
摩动核    55
STAR     45
万代      43
星锋社    30
长龙      27
唯美      26
...
```

这组数据的含义：

- **厂家是真正的主维度**：头部 6 家占六成，长尾有 35 个“只有 1 款”的厂牌。收藏集也说过“XX 厂制霸”，厂家天然是入口。
- **产品线不是主维度**：全库 90 个产品线值（含“未知”）；同一厂家的产品线数量从 1 到 18 不等（高高 18、大班 7、星动 4、集模社 2、摩动核 9、万代只有 RG）。不适合像 78 动漫那样用“系列”做一级目录。
- **同厂异写（合并前）**：
  - 猛虎（5）/ 猛虎模型（13）→ **已于 2026-10-28 合并为 猛虎模型（18）**
  - 瘦虎（1）/ 瘦虎模型（1）→ **已于 2026-10-28 合并为 瘦虎模型（2）**
  - B社（1，SDCS 吉姆）很可能是万代，**仍待确认**。
- 其余相似名字（星动 / 星锋社 / 星原社，猛虎 / 胖虎 / 瘦虎，无限新星 / 无限维度）是不同厂牌，不要按“名字像”自动合并。

## 二、已经落地的厂家目录（前端）

当前 `/#directory` 已经是厂家优先：

- 首屏是 **84 张厂牌卡**：厂名、产品数、产品线数、前 3 个高频产品线；按产品数或厂名排序；可搜厂牌。
- 点厂牌进入厂牌页：面包屑“厂家目录 / 高高”，产品线 chips（全部 / HG00 / MG / RG…），产品网格/列表、搜索、录入。
- “全部产品”仍然保留，作为跨厂牌的备选入口。
- URL 支持 `#directory/<厂牌>`，浏览器前进/后退可用。

这一步**没有改表结构**，只按现有字符串分组；随后直接更新了 `products.manufacturer` 合并两组别名。也就是说：

- 目录能用了；
- 猛虎 / 瘦虎 已合并，B社 / 万代 仍分开；
- 厂家没有描述、国家、类型（官方/KO/原创）等元数据；
- 未来审核入库或外部导入仍可能再写出旧别名（没有别名映射/外键拦截）。

## 三、要不要做厂家表

### 结论

**值得做，而且建议在收藏集之前做。** 但分两步，不要一次把产品线也卷进来。

### 做了厂家表能解决什么

| 问题 | 厂家表怎么解决 |
| --- | --- |
| 同厂异写 | `manufacturer_aliases` 把 猛虎 / 猛虎模型 归到一个厂 |
| 厂牌页信息太少 | 描述、国家、类型（官方/KO/原创/GK）、排序、以后加 logo |
| 目录计数稳定 | 按 `manufacturer_id` 分组，不再怕改字/多空格 |
| 产品身份 | 查重从 `(manufacturer 字符串, kit_name)` 变成 `(manufacturer_id, kit_name)` |
| 审核入库 | 抽取的 `brand` 可以匹配到厂，避免每次新建一个错别字厂 |
| 收藏集 | “XX 厂制霸”直接按 `manufacturer_id` 定义，不用字符串 |
| 数据维护 | 后台可以改厂名、合并厂、加别名；产品跟着走 |

### 成本与风险

不是加一张表那么简单，`manufacturer` 现在是产品身份的一部分：

1. `products` 的查重、创建、更新、批量导入都用到 `manufacturer` 字符串。
2. `review_items.brand` 是原始抽取值，需要决定“保留原文 + 关联厂家”还是只存关联。
3. 后台管理、产品目录筛选、CSV 导出、前端表单都要改。
4. 合并厂牌要有明确的“保留哪个名字、哪些别名”的人工决定。
5. 历史数据要回填、校验；迁移不能自动猜 B社 = 万代。

### 推荐方案：厂家表 + 外键，不保留双份字符串

```sql
CREATE TABLE manufacturers (
    id          uuid PRIMARY KEY,
    name        varchar(120) NOT NULL UNIQUE,  -- 规范名，如“猛虎模型”
    kind        varchar(16),                   -- official / ko / third_party / gk / other
    country     varchar(32),                   -- 中国 / 日本 / ...
    description text,
    sort_order  integer NOT NULL DEFAULT 0,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_manufacturers_kind
        CHECK (kind IS NULL OR kind IN ('official','ko','third_party','gk','other'))
);

CREATE TABLE manufacturer_aliases (
    id              uuid PRIMARY KEY,
    manufacturer_id uuid NOT NULL REFERENCES manufacturers(id) ON DELETE CASCADE,
    alias           varchar(120) NOT NULL UNIQUE, -- 如“猛虎”“B社”
    created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE products
    ADD COLUMN manufacturer_id uuid REFERENCES manufacturers(id) ON DELETE RESTRICT;
-- 回填后 SET NOT NULL；产品身份改为 (manufacturer_id, kit_name)
```

- `products.manufacturer` 字符串**最终删掉**，只保留外键；API 读的时候 join 出 `manufacturer.name`。
- `review_items.brand` 保留原始抽取值（审计），另加 `manufacturer_id` 可空；新建产品时用它，映射时也可以补。
- `manufacturer_aliases.alias` 全局唯一，避免两个厂抢同一个别名。
- 删除厂家：如果还有产品，`RESTRICT` 拒绝；先合并/迁移产品。

### 不建议：只做“厂家字典”但产品仍存字符串

短期省事，但会出现两份事实：

- 字典改了名，产品字符串没改，目录按哪个显示？
- 别名匹配在每次查询时做，逻辑会散落在 API / 前端 / 导入器里。
- 收藏集按字符串还是字典 ID？
- 最后还是要做一次外键迁移，等于做两遍。

如果只是想让厂牌页先有描述，可以临时接受；但既然要“维护产品表”，建议一次做到外键。

## 四、落地顺序（建议）

### 第 1 步：先确认合并名单（人工）

合并名单（两组已执行，B社待定）：

| 现状 | 建议规范名 | 别名 |
| --- | --- | --- |
| 猛虎（5）+ 猛虎模型（13） | **已合并为 猛虎模型（18）** | 猛虎 |
| 瘦虎（1）+ 瘦虎模型（1） | **已合并为 瘦虎模型（2）** | 瘦虎 |
| B社（1，SDCS 吉姆） | 待确认；若确认是万代 | 合并到 **万代**，B社 作别名 |
| 星动 / 星锋社 / 星原社 | 保持三个独立厂牌 | 不合并 |
| 猛虎 / 胖虎 / 瘦虎 | 保持独立 | 不合并 |
| 无限新星 / 无限维度 | 保持独立 | 不合并 |

### 第 2 步：建表 + 回填（不删字符串）

1. 建 `manufacturers` / `manufacturer_aliases`。
2. 把 86 个 distinct `manufacturer` 插进去（去空格）。
3. 人工插入别名；先按上表处理 3 组。
4. `products.manufacturer_id` 可空；按“规范名 + 别名”回填。
5. 校验：每个产品都能落到一个 manufacturer；没有孤儿。

### 第 3 步：切换产品身份与接口

1. `(manufacturer_id, kit_name)` 查重；保留旧字符串列一段时间做对照。
2. `ProductRead.manufacturer` 改为 join 出来的规范名；`ProductCreate/Update` 接受 `manufacturer_id`（或“选厂 + 新建厂”的 UI）。
3. 后台管理增加“厂家管理”：新增、改名、加别名、合并（把产品移过去、删旧厂）。
4. 审核入库：`review_items` 加 `manufacturer_id`；新建产品时选厂/匹配 alias；原始 `brand` 继续保留。
5. 产品目录前端：厂家目录改为读 `/manufacturers` 的计数和元数据；`#directory/<slug>` 用 slug 或 id。
6. 导出 CSV：输出规范名；导入时按 alias 匹配。

### 第 4 步：删旧列、做收藏集

- 确认所有入口（API / 前端 / 导入器 / 测试）都用 `manufacturer_id` 后，删除 `products.manufacturer`。
- 收藏集的“XX 厂制霸”按 `manufacturer_id` 定义；产品目标仍然只指向已录入产品。

## 五、工作量估算

| 阶段 | 内容 | 估算 |
| --- | --- | --- |
| A | 前端厂家目录（已完成） | — |
| B | 厂家表 + 别名 + 回填 + 后台 CRUD | 0.5–1 天 |
| C | `manufacturer_id` 外键 + 产品 API/审核/前端切换 + 测试 | 1–2 天 |
| D | 厂家描述/类型/国家/排序等元数据 | 0.5 天 |
| E | 收藏集（按厂家 ID 定义范围） | 另算 |

> 数据量很小（86 厂、1254 产品），迁移本身不重；重的是把 `manufacturer` 从“字符串身份”改成“外键身份”的入口都找齐、测到。

## 六、一句话建议

**先上厂家目录 UI（已完成），然后做厂家表 + 外键，再回头做收藏集。**
产品线暂时保持自由文本，只在厂家页做 chips 筛选；等厂家这一层稳定后，再讨论产品线规范化。

相关文档：

- [collection-system.md](collection-system.md)：收藏集的范围与进度
- [architecture-design.md](architecture-design.md)：当前表结构
- [deploy-and-restore.md](deploy-and-restore.md)：迁移前后备份/恢复
