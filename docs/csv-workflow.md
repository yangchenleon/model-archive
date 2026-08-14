# 产品目录填写流程

复制 [`templates/csv/products-manual-template.csv`](../templates/csv/products-manual-template.csv) 到 Git 忽略目录 `imports/products.csv`，再用 Excel、WPS 或 Numbers 填写。原来的 [`templates/csv/products.csv`](../templates/csv/products.csv) 仍可使用，字段完全兼容。

当前只维护这一份文件。资产、愿望单、收藏分组和事件暂不填写，也不需要建立任何关联。

## 字段规则

| 字段 | 规则 |
| --- | --- |
| 厂商 | 自由文本，可空。 |
| 厂家编号 | 厂商用于识别产品的编号，可空；如同一产品有多个编号，按原资料填写。 |
| 来源类型 | 自由文本，可空。 |
| 模型名称 | 必填，先按盒名或常用名称记录。 |
| 版本/配色 | 可空。 |
| 详情 | 自由文本，可空；可记录套件内容、发售备注等。 |
| 资料来源 | 必填，填写这条资料来自哪里，例如官网、说明书、78动漫或个人收藏。 |

模板只有一行空白示例行，直接从第二行开始填写即可。不要修改第一行的列名。暂时无法确认的内容留空，不要为了凑字段填写猜测值。

旧的测试 CSV 如果没有 `详情`、`资料来源` 和 `厂家编号` 列，仍可使用 `--source 初始化测试` 导入；新的人工整理应优先填写模板中的全部适用字段。

## 导入

```bash
docker compose exec api python -m app.scripts.import_products_csv /app/imports/products.csv
```

系统不保存或对接原始日报、网页或其他资料文件；它们不属于当前产品目录范围。
