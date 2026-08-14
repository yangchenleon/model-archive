# 填写清单，而不是填写数据库

复制 [`templates/csv`](../templates/csv) 到 Git 忽略目录 `data/drafts/<批次名>/`。四份文件可以直接用 Excel、WPS 或 Numbers 打开。你只填写看得懂的内容，**不要填写 ID、外键、key 或任何内部编号**。

## 先填哪两份

第一轮只需填这两份：

1. `catalog_items.csv`：一行是一个可区分的发行版本。不同盒绘、配色、限定或编号，只有在你认为值得分开收藏时才分行。
2. `assets.csv`：一行是一组状态相同的实物。例如三盒都未拆、放同一位置，可填数量 `3`；只要状态或位置不同，就分行。

`collection_targets.csv` 和 `asset_events.csv` 可以先只保留表头。收藏归属、系列关系和历史事件后续由界面中的选择器/复选框维护，不必现在建立连接。

## 可选项的填写方式

| 字段 | 建议 |
| --- | --- |
| 来源类型 | `官方/正版`、`国模`、`KO/翻模`、`GK`、`第三方` 或 `待确认`。 |
| 当前状态 | `想买`、`已预订`、`待拼`、`拼装中`、`已拼`、`待出售`、`待置换`、`已出售`、`已退货`、`待确认`。 |
| 盒况 | `未拆`、`已拆`、`完整`、`缺件`、`待确认`。 |
| 资料可信度 | `记录`、`已核验`、`待核验`。 |

没有把握时留空，或者写 `待确认`。不要为了整齐而猜正式名称、厂商或比例。

## 导出当前清单

数据库已经有内容时，先导出一份可继续编辑的无 ID 清单：

```bash
docker compose exec api python -m app.scripts.export_csv /app/data/drafts/current_snapshot_friendly
```

## 导入

导入时，系统会根据厂商、产品线、名称、版本、比例和厂商编号匹配发行物；数据库 UUID、外键和内部导入标识全部由系统处理。

```bash
docker compose exec api python -m app.scripts.import_csv /app/data/drafts/current_snapshot_friendly
```

资产目前以“同一发行物 + 同一存放位置”为一组匹配。两盒同款但状态不同或需要逐盒管理时，先分行；更精细的逐盒关联会在界面版中处理。

## 日报如何继续写

使用 [`templates/daily-log.md`](../templates/daily-log.md) 记录新入库、完成拼装、出售/置换和收藏理由。不要在日报重复维护全量清单；需要追溯时，在 CSV 的 `来源备注` 中写日报文件名或日期即可。
