# 手机接入与实物图（Tailscale + 对象存储）

> 2026-11-18 落地第 1 期。目标场景：站在柜子/箱子前，用手机给**这一台**拍实物图，
> 存进 `assets` 对应的记录里。全程只有一条额外通道：Tailscale 把本机的 15174 代理到 tailnet，
> 不改 `docker-compose.yml` 里的 `127.0.0.1` 绑定。

## 一、为什么不是「把端口开出去」

`docker-compose.yml` 里每个端口都显式绑 `127.0.0.1`，这是有意的。放开到 `0.0.0.0` 之前必须知道：
**这个应用没有鉴权**——没有登录、没有 token、没有权限模型。谁连上端口谁就能删产品、改状态、传文件。

因此三条路，按推荐顺序：

| 方式 | 是否改 compose | 认证 | 适用 |
| --- | --- | --- | --- |
| **Tailscale + `tailscale serve`**（推荐） | 不需要 | 设备级（tailnet） | 手机/平板/外出 |
| 局域网直连 | 需要：端口改 `0.0.0.0`、Vite 加 `server.host` | **无**，靠路由器和防火墙 | 只有你完全信任的 WiFi |
| SSH 隧道 | 不需要 | SSH 密钥 | 偶尔用、能忍受命令行 |

## 二、Tailscale + `tailscale serve`（已确认可行）

`tailscale serve` 从**本机 loopback** 取流量再转发到 tailnet，并自动签 HTTPS 证书。
好处有三个：不用改 compose 的绑定、不用暴露局域网、**有了 HTTPS**（后面 `getUserMedia` 才可用）。

前提：WSL2 里 `systemd` 已在运行（本机 `/etc/wsl.conf` 有 `systemd=true`，PID 1 就是 systemd）。

```bash
# 1. 在 WSL 里装（需要 sudo 密码，所以这一步由你来执行）
curl -fsSL https://tailscale.com/install.sh | sh

# 2. 登录（浏览器打开它给的链接，手机/电脑装 Tailscale 并登录同一账号）
sudo tailscale up

# 3. 只把前端端口挂到 tailnet（HTTPS 自动证书）
sudo tailscale serve --bg 15174

# 4. 查看实际地址
tailscale serve status
```

手机打开 `https://<机器名>.<tailnet>.ts.net` 即可。**只需要一个端口**：`/api` 由 Vite 的
proxy（`VITE_API_PROXY_TARGET`）转发到 API 容器，API 和 Adminer 不必暴露。

要点：

- `tailscale serve` 是**只读代理**，不会把服务暴露给整个局域网；撤销用 `sudo tailscale serve reset`。
- 建议在 Tailscale 后台把 ACL 限制成「只有我的设备能访问这台机器」——这就是这个应用目前的全部鉴权。
- 电脑睡眠/关机时手机自然打不开，这是本地资料库的固有属性，不是配置问题。
- 如果换到 Windows 宿主机跑 Tailscale，**不要**期待它连上 `127.0.0.1` 绑定：那种情况必须把端口改成
  `0.0.0.0`（或 `127.0.0.1` 以外的地址），并且用防火墙限定只有 Tailscale 网段可访问。

## 三、拍照这件事的技术前提

| 做法 | 需要 HTTPS | 说明 |
| --- | --- | --- |
| `<input type="file" accept="image/*" capture="environment">` | **不需要** | 点一下调起系统相机，拍完回传。资产抽屉用的就是这条路 |
| `getUserMedia`（页面内实时取景、连拍） | **需要** | 第 3 期扫码直拍如果要做取景器才需要 |

所以第 1 期在纯 HTTP 的局域网下也能用；只有走到「页面内取景」时才必须走 `tailscale serve` 的 HTTPS。

## 四、图片放在哪

- 图片字节存在**对象存储**（S3 API），第 1 期用 compose 里的 `objects` 服务（Garage）。
- 数据库只存 `asset_photos` 元数据（尺寸、字节数、对象键），所以 `pg_dump` 不会变成几十 GB。
- 后端只认 S3 接口，换 MinIO / SeaweedFS / Cloudflare R2 只改 `S3_ENDPOINT_URL` + 密钥：

```bash
PHOTO_STORAGE=s3              # 测试用 fs，本地目录
S3_ENDPOINT_URL=http://objects:3900
S3_BUCKET=model-archive-photos
S3_ACCESS_KEY=GK...           # Garage: "GK" + 24 位 hex
S3_SECRET_KEY=...             # 64 位 hex
```

> **MinIO 说明**：`minio/minio` 上游仓库已归档（2026-04 停止更新）。已发布的二进制仍可用，
> 但新部署没有理由选它；Garage 与 SeaweedFS 都是活跃的 S3 兼容替代。
> 代码不依赖任何一家，所以这个选择随时可以改。

## 五、手机上的实际流程（第 1 期）

```text
我的资产 (/#inventory) → 点某一台 → 抽屉「实物图」→ 拍照 / 选图 → 已保存照片
```

- 列表页会在品名左边显示 34px 缩略图，方便一眼核对是不是同一盒。
- 上传即转码：EXIF 方向会被摆正，长边 1920 原图 + 400 缩略图，PNG 透明底铺白。
- 同一张图重复上传是幂等的（对象键是内容哈希），两台资产用同一张图只存一份。
- 删除：删行之后，若没有别的行引用同一个对象才删对象；Garage 的实际块文件由后台 GC 回收，
  所以硬盘空间不会立刻下降，这是 S3 语义，不是泄漏。

## 六、备份与恢复（从一条线变成两条线）

以前只有 `pg_dump` 一条线，现在**必须两份一起**才算完整：

```bash
# 数据库
docker compose exec -T db pg_dump -U model_archive -d model_archive -Fc > backups/db.dump
# 图片对象（docker volume）
docker run --rm -v model-archive_garage_data:/data -v "$PWD/backups":/backup alpine \
  tar czf /backup/garage_data.tar.gz -C /data .
```

恢复顺序：先 DB 后对象（`asset_photos` 行指向对象键，反过来会有一段时间图片 404）。
详见 [deploy-and-restore.md](deploy-and-restore.md)。
