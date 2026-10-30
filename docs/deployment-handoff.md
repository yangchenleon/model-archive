# 部署交接（2026-10-30）

本文是当前这一版数据与部署流程的**一页交接文档**。更细的故障排查见
[deploy-and-restore.md](deploy-and-restore.md)。

## 1. 代码与数据

| 项目 | 值 |
| --- | --- |
| 代码仓库 | `git@github.com:yangchenleon/model-archive.git` |
| 当前提交 | 本文件生成时 `b243a91`；以 `git log --oneline -1` 为准 |
| dump | `backups/model-archive-20261028.dump` |
| dump 大小 | 391 KB |
| dump SHA256 | `92fd7c7ba61d6aed1492d5b328a2ea1cf5e805d3e000f92a66ac84210ac62473` |
| 数据库迁移 | `0026_edition_craft` |
| 产品 | 2243 |
| 万代 | MG 794 / MGEX 8 / RG 232 |
| 审核记录 | 875 |
| 资产 | 139（全部 pending） |
| 标签 | 1 |
| 收藏集 | 1 个，16 个收藏项 |
| 厂家 | 84 |
| 系列 | 156 |

> dump 包含当前库里的 139 条 pending 资产。如果不是预期数据，先清理再重新导出，
> 否则会原样带到新主机。

## 2. 新主机需要什么

- Docker + Docker Compose
- Git
- 本仓库代码
- `.env`（不在 git 里，手工复制）
- `backups/model-archive-20261028.dump`
- `backups/model-archive-20261028.dump.sha256`

不需要：

- 78dm cookie
- `imports/78dm` 抓取数据
- 源主机的 PostgreSQL 数据目录
- 图片/对象存储配置

## 3. 准备代码和环境

```bash
git clone git@github.com:yangchenleon/model-archive.git
cd model-archive
git log --oneline -1
# 记录当前提交；本文生成时为 b243a91

cp .env.example .env
```

编辑 `.env`：

```dotenv
POSTGRES_DB=model_archive
POSTGRES_USER=model_archive
POSTGRES_PASSWORD=换成一个新密码

POSTGRES_PORT=15432
API_PORT=18000
ADMINER_PORT=18080
FRONTEND_PORT=5173
```

只部署产品目录/收藏集时，`ASR_*`、`LLM_*` 可以留空；需要视频/LLM 管线再填。

## 4. 校验并导入 dump

```bash
sha256sum -c backups/model-archive-20261028.dump.sha256
# backups/model-archive-20261028.dump: OK
```

Windows PowerShell：

```powershell
Get-FileHash .\backups\model-archive-20261028.dump -Algorithm SHA256
# 应为 92fd7c7...
```

启动数据库：

```bash
docker compose up -d db
docker compose exec db pg_isready -U model_archive -d model_archive
```

导入：

```bash
docker compose cp backups/model-archive-20261028.dump db:/tmp/model_archive.dump

docker compose exec db pg_restore \
  -U model_archive \
  -d model_archive \
  --no-owner --no-acl \
  --clean --if-exists \
  /tmp/model_archive.dump

docker compose exec db rm -f /tmp/model_archive.dump
```

说明：

- dump 是 custom format，必须用 `pg_restore`，不要 `psql < file`。
- `--no-owner --no-acl` 允许换数据库用户名恢复。
- `--clean --if-exists` 支持重复导入。
- `NOTICE` 可以忽略，退出码为 0 即可。

## 5. 启动 API 和前端

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:18000/health
# {"status":"ok"}
```

API 启动时会执行 `alembic upgrade head`；dump 已经是 `0026_edition_craft`，
正常情况下是 no-op。

## 6. 访问

Compose 默认只绑定 `127.0.0.1`。从其他机器访问，推荐 SSH 隧道：

```bash
ssh -L 5173:127.0.0.1:5173 \
    -L 18000:127.0.0.1:18000 \
    user@新主机
```

然后本机打开：

- 前端：<http://127.0.0.1:5173>
- API 文档：<http://127.0.0.1:18000/docs>
- Adminer：<http://127.0.0.1:18080>（server 填 `db`）

如果确实要局域网直接访问，需要去掉 `docker-compose.yml` 端口前的
`127.0.0.1:`，并自行加防火墙/反向代理。

## 7. 导入后验证

```bash
docker compose exec db psql -U model_archive -d model_archive -c "
select
  (select count(*) from products) products,
  (select count(*) from review_items) review_items,
  (select count(*) from assets) assets,
  (select count(*) from tags) tags,
  (select count(*) from collections) collections,
  (select count(*) from collection_items) collection_items,
  (select count(*) from manufacturers) manufacturers,
  (select count(*) from product_lines) product_lines,
  (select version_num from alembic_version) alembic;
"
```

期望：

```text
 products | review_items | assets | tags | collections | collection_items | manufacturers | product_lines |          alembic
----------+--------------+--------+------+-------------+------------------+---------------+---------------+----------------------------
     2243 |          875 |    139 |    1 |           1 |               16 |            84 |           156 | 0026_edition_craft
```

页面检查：

- 产品目录应有 2243 条
- 万代筛选：MG 794、MGEX 8、RG 232
- 入库审核：875 条
- 我的资产：139 条 pending
- 标签队列：1 条
- 收藏集：1 个，16 项

## 8. 配置项说明

### `.env`

- 必须：`POSTGRES_*`、`POSTGRES_PASSWORD`
- 端口：`API_PORT`、`FRONTEND_PORT`、`ADMINER_PORT`、`POSTGRES_PORT`
- 可选：`ASR_API_KEY`、`ASR_BASE_URL`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`
- `.env` 不提交、不公开

### 数据库

- 使用 compose 内置 PostgreSQL 16 时，`DATABASE_URL` 由 `POSTGRES_*` 自动拼。
- 使用外部 PostgreSQL 时，改 `docker-compose.yml` 里 `api.environment.DATABASE_URL`，
  或直接在本机跑 API，见 [deploy-and-restore.md](deploy-and-restore.md) 第 9 节。
- 不要执行 `docker compose down -v`，除非确认要删除整个数据库 volume。

### 产品数据

- 通贩编号数字化是**当前万代数据的一次性整理**，不是通用 API 规则。
- 非万代编号（如 `MNP-XH01`）保持原样。
- 限定版编号不强制数字化。
- MG 普通版编号已补齐 01–225；RG 普通版 01–44。
- 图片不在 dump/对象存储里；没有额外图片服务需要配置。

## 9. 以后重新导出

```bash
cd /path/to/model-archive

pg_dump -Fc -Z 9 --no-owner --no-acl \
  -f backups/model-archive-20261101.dump \
  "postgresql://model_archive:密码@localhost:15432/model_archive"

sha256sum backups/model-archive-20261101.dump \
  > backups/model-archive-20261101.dump.sha256
```

导出前建议确认：

```bash
cd backend
../.venv/bin/alembic current
```

如果只想导数据、保留目标结构，见
[deploy-and-restore.md](deploy-and-restore.md) 第 7 节。
