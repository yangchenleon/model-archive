# 在另一台主机部署并导入数据

> 适用：Docker Compose + PostgreSQL 16。本文以当前导出的
> `backups/model-archive-20261028.dump`（custom format，253 KB）为例。
> 目标主机只需要 Docker、Compose、代码和这个 dump；不需要把源主机的数据库目录拷过去。

## 0. 需要带到新主机的东西

| 东西 | 怎么过去 | 说明 |
| --- | --- | --- |
| 代码 | `git clone` 或打包拷贝 | 远端：`git@github.com:yangchenleon/model-archive.git` |
| `.env` | 手工复制（scp / 密码管理器） | **不在 git 里**，含数据库密码和 ASR/LLM key |
| 数据库 dump | scp / U 盘 / 内网传输 | `backups/model-archive-20261028.dump` |
| 校验文件 | 随 dump 一起 | `backups/model-archive-20261028.dump.sha256` |

当前 dump 的内容（已在本机恢复到临时库验证）：

```text
products        1254
review_items     875
assets             0
tags               0
collections        0
collection_items   0
alembic          0021_collections
```

> 资产/标签/收藏集是 0，是因为导出时还没有这些数据；导入后目录、审核队列是完整的。

---

## 1. 拿到代码

```bash
git clone git@github.com:yangchenleon/model-archive.git
cd model-archive
git log --oneline -1
```

如果新主机没有配 GitHub SSH key，用 HTTPS 克隆也可以：

```bash
git clone https://github.com/yangchenleon/model-archive.git
```

代码要和 dump 的迁移版本匹配：dump 的 `alembic_version` 是 `0021_collections`，
当前 `main` 已经包含到 `0021`。以后如果先拉代码后导旧 dump，API 启动时会自动
`alembic upgrade head` 补迁移。

---

## 2. 准备 `.env`

```bash
cp .env.example .env
```

编辑 `.env`，至少确认：

```dotenv
POSTGRES_DB=model_archive
POSTGRES_USER=model_archive
POSTGRES_PASSWORD=换成一个新密码
POSTGRES_PORT=15432
API_PORT=18000
ADMINER_PORT=18080
FRONTEND_PORT=5173

# 需要视频/LLM 管线时再填；只启动目录和收藏集可以留空
ASR_API_KEY=
ASR_BASE_URL=
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
```

要点：

- `.env` 不要提交，不要发到公开仓库。
- 如果新主机端口被占用，改 `API_PORT` / `FRONTEND_PORT` / `ADMINER_PORT` / `POSTGRES_PORT`。
- `POSTGRES_USER` / `POSTGRES_DB` 建议保持 `model_archive`，和 dump 里的对象名一致，少踩坑。
- `docker-compose.yml` 里的 `DATABASE_URL` 是用这些变量拼的，不需要另外改。

---

## 3. 校验 dump

Linux / WSL：

```bash
cd /path/to/model-archive
sha256sum -c backups/model-archive-20261028.dump.sha256
# 期望：backups/model-archive-20261028.dump: OK
```

Windows PowerShell：

```powershell
Get-FileHash .\backups\model-archive-20261028.dump -Algorithm SHA256
Get-Content .\backups\model-archive-20261028.dump.sha256
# 两个哈希应一致：429b2dbde0a89f4937916646d718d76534d0824fc20ffb00034d6da8253cdf75
```

> dump 是 custom format（`pg_dump -Fc`），不是纯 SQL 文本；用 `pg_restore` 导入，不要直接 `psql < file`。

---

## 4. 只启动数据库

```bash
docker compose up -d db
docker compose ps
```

等健康检查通过：

```bash
docker compose exec db pg_isready -U model_archive -d model_archive
# 期望：/var/run/postgresql:5432 - accepting connections
```

如果是**全新的主机/全新的 volume**，到这一步数据库是空的，直接进第 5 步。

---

## 5. 导入 dump

推荐用 `docker compose cp` 把文件送进容器，避免 Windows/PowerShell 的输入重定向差异：

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

- `--no-owner --no-acl`：dump 里没有绑定原主机的角色/权限，换用户名也能恢复。
- `--clean --if-exists`：重复导入时先删旧对象；空库导入也不会有问题。
- `pg_restore` 输出一些 `NOTICE` 是正常的；只要退出码是 0 即可。
- 如果目标库已有**不在 dump 里的多余表**，`--clean` 不会帮你删掉它们。要彻底干净，见第 8 节。

### 验证导入结果

```bash
docker compose exec db psql -U model_archive -d model_archive -c "
select
  (select count(*) from products)        as products,
  (select count(*) from review_items)    as review_items,
  (select count(*) from assets)          as assets,
  (select count(*) from tags)            as tags,
  (select count(*) from collections)     as collections,
  (select count(*) from collection_items) as collection_items,
  (select version_num from alembic_version) as alembic;
"
```

期望：

```text
 products | review_items | assets | tags | collections | collection_items |     alembic
----------+--------------+--------+------+-------------+------------------+------------------
     1254 |          875 |      0 |    0 |           0 |                0 | 0021_collections
```

---

## 6. 启动 API 和前端

```bash
docker compose up --build -d
docker compose ps
```

API 容器启动时会执行 `alembic upgrade head`。因为 dump 已经是 `0021_collections`，
这一步是 no-op；如果导入的是旧 dump，它会自动补迁移。

健康检查：

```bash
curl http://127.0.0.1:18000/health
# {"status":"ok"}
```

打开前端（端口取 `.env` 的 `FRONTEND_PORT`）：

```text
http://<新主机IP>:5173
```

页面：

- 产品目录：应看到 1254 条
- 入库审核：875 条记录
- 我的资产 / 标签队列 / 收藏集：0 条，属于正常
- Adminer：`http://<新主机IP>:18082`，server 填 `db`

---

## 7. 只导数据、不替换结构（可选）

如果目标库**已经**是同一个迁移版本、只想覆盖数据：

```bash
docker compose cp backups/model-archive-20261028.dump db:/tmp/model_archive.dump
docker compose exec db pg_restore \
  -U model_archive -d model_archive \
  --no-owner --no-acl --data-only \
  /tmp/model_archive.dump
docker compose exec db rm -f /tmp/model_archive.dump
```

一般不需要这样做；第 5 节的全量 restore 更简单、更可重复。

---

## 8. 重新导入 / 回到干净状态

如果目标库已经有脏数据，想从 dump 完全重来：

```bash
# 警告：-v 会删除 postgres_data volume，确认里面没有要保留的东西
docker compose down -v
docker compose up -d db
docker compose exec db pg_isready -U model_archive -d model_archive

docker compose cp backups/model-archive-20261028.dump db:/tmp/model_archive.dump
docker compose exec db pg_restore \
  -U model_archive -d model_archive \
  --no-owner --no-acl --clean --if-exists \
  /tmp/model_archive.dump
docker compose exec db rm -f /tmp/model_archive.dump

docker compose up --build -d
```

---

## 9. 不用 Compose 的 db（外部 PostgreSQL）

如果新主机已有 PostgreSQL 16：

1. 建库建用户（名字可以不同）。
2. 用 `pg_restore` 导入：

```bash
pg_restore \
  -h 127.0.0.1 -p 5432 -U model_archive -d model_archive \
  --no-owner --no-acl --clean --if-exists \
  backups/model-archive-20261028.dump
```

3. 把 API 的数据库地址指向外部库。注意 `docker-compose.yml` 当前是在 `api.environment`
   里用 `POSTGRES_*` 拼 `DATABASE_URL` 的，所以只改 `.env` 的 `DATABASE_URL` 不会生效：

   - 要么改 `docker-compose.yml` 里 `api.environment.DATABASE_URL`；
   - 要么不用 compose 的 api，直接在本机跑：

```bash
export DATABASE_URL=postgresql+psycopg://model_archive:密码@127.0.0.1:5432/model_archive
cd backend
../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. 使用外部库时，`docker compose` 里的 `db` 服务和 `api.depends_on: db` 需要去掉/覆盖。
5. 前端仍可在 `frontend/` 里 `npm run dev`，把 `VITE_API_PROXY_TARGET` 指向 API。

> 跨大版本 PostgreSQL 时，`pg_restore` 版本尽量不低于 dump 的版本（本 dump 是 16.15）。
> 最稳的是目标也使用 `postgres:16-alpine`。

---

## 10. 以后从源主机重新导出

源主机（本机）以后有新数据时：

```bash
cd /path/to/model-archive

# 文件名按日期改，下面用 20261101 作为例子
pg_dump -Fc -Z 9 --no-owner --no-acl \
  -f backups/model-archive-20261101.dump \
  "postgresql://model_archive:密码@localhost:15432/model_archive"

sha256sum backups/model-archive-20261101.dump \
  > backups/model-archive-20261101.dump.sha256

pg_restore -l backups/model-archive-20261101.dump | head
```

- `backups/` 已在 `.gitignore` 里，dump 不会进仓库。
- 文件名建议带日期，例如 `model-archive-20261101.dump`。
- 导出前确认迁移已到最新：`alembic current`。
- dump 含产品目录和审核证据，不含 `.env` 里的 key；仍按私有数据保管。

---

## 11. 常见问题

| 现象 | 处理 |
| --- | --- |
| `permission denied` 读 dump | 用 `docker compose cp`，不要用容器挂载路径猜 |
| `role "model_archive" does not exist` | restore 加 `--no-owner`，或先建角色 |
| `database "model_archive" does not exist` | 确认 `.env` 的 `POSTGRES_DB`，并 `docker compose up -d db` 让它创建 |
| `relation "products" already exists` | 加 `--clean --if-exists`，或按第 8 节清空 volume |
| API 起不来 | `docker compose logs -f api`，先看数据库健康检查和迁移报错 |
| 前端能开但接口 404/502 | 确认 `api` 容器在跑，前端是通过 compose 的代理访问 `/api` |
| 端口冲突 | 改 `.env` 的 `API_PORT` / `FRONTEND_PORT` / `ADMINER_PORT` / `POSTGRES_PORT` |
| 导入后数量不对 | 重跑第 5 节验证 SQL；确认导入的是正确的 dump 文件 |

---

## 12. 最短流程（TL;DR）

```bash
# 目标主机：先把 dump 和 .sha256 放进 backups/，再执行
git clone git@github.com:yangchenleon/model-archive.git
cd model-archive
cp .env.example .env
# 编辑 .env：密码、端口、需要的 key

docker compose up -d db
docker compose exec db pg_isready -U model_archive -d model_archive

docker compose cp backups/model-archive-20261028.dump db:/tmp/model_archive.dump
docker compose exec db pg_restore -U model_archive -d model_archive \
  --no-owner --no-acl --clean --if-exists /tmp/model_archive.dump

docker compose up --build -d
curl http://127.0.0.1:18000/health
# 打开 http://<主机IP>:5173
```
