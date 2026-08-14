# 产品目录填写流程

复制 [`templates/csv/products.csv`](../templates/csv/products.csv) 到 Git 忽略目录 `imports/products.csv`，再用 Excel、WPS 或 Numbers 填写。

当前只维护这一份文件。资产、愿望单、收藏分组和事件暂不填写，也不需要建立任何关联。

## 字段规则

| 字段 | 规则 |
| --- | --- |
| 厂商 | 必填，自由文本。 |
| 来源类型 | 必填：官方/正版、国模、KO/翻模、GK、第三方、待确认。 |
| 模型名称 | 必填，先按盒名或常用名称记录。 |
| 资料可信度 | 必填：记录、已核验、待核验。 |
| 详情 | 自由说明。可写命名疑问、盒绘差异或待核验原因。 |

没有把握的来源类型和资料状态，请显式写 `待确认`、`待核验`；不要留空让系统猜。

## 导入

```bash
docker compose exec api python -m app.scripts.import_products_csv /app/imports/products.csv
```

系统不保存或对接原始日报、网页或其他资料文件；它们不属于当前产品目录范围。
