# 产品目录填写流程

复制 [`templates/csv/products-manual-template.csv`](../templates/csv/products-manual-template.csv) 到 Git 忽略目录 `imports/products.csv`，再用 Excel、WPS 或 Numbers 填写。原来的 [`templates/csv/products.csv`](../templates/csv/products.csv) 仍可使用，字段完全兼容。

当前只维护这一份文件。资产、愿望单、收藏分组和事件暂不填写，也不需要建立任何关联。

## 字段规则

| 字段 | 规则 |
| --- | --- |
| 厂商 | 自由文本，可空。 |
| 来源类型 | 自由文本，可空。 |
| 模型名称 | 必填，先按盒名或常用名称记录。 |
| 版本/配色 | 可空。 |

模板只有一行空白示例行，直接从第二行开始填写即可。不要修改第一行的列名，也不要添加编号、详情、资料来源等列；这些内容由系统或后续整理流程处理。暂时无法确认的内容留空，不要为了凑字段填写猜测值。

本批产品的 `detail` 留空，`source` 由导入命令统一写入，不需要出现在 CSV 中。

## 导入

```bash
docker compose exec api python -m app.scripts.import_products_csv /app/imports/products.csv --source 初始化测试
```

系统不保存或对接原始日报、网页或其他资料文件；它们不属于当前产品目录范围。
