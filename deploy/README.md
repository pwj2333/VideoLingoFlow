# 集群基线

## GitHub Actions 一键发布与部署

`.github/workflows/docker-release.yml` 会在 `main` 推送时构建 CPU Docker 镜像并发布到 GHCR。也可以在 Actions 页面手动运行工作流并勾选 `deploy`，通过 SSH 执行服务器更新。

服务器首次部署前，在目标目录准备 `.env`（可由 `deploy/.env.example` 复制），并在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置：

| Secret | 说明 |
| --- | --- |
| `SERVER_HOST` | 服务器地址 |
| `SERVER_USER` | SSH 用户 |
| `SERVER_SSH_KEY` | SSH 私钥 |
| `SERVER_PORT` | SSH 端口，可选，默认 22 |
| `SERVER_APP_DIR` | 服务器上的项目目录 |
| `GHCR_USERNAME` | 可读取 GHCR 私有镜像的账号 |
| `GHCR_TOKEN` | 该账号的 GHCR read:packages token |

工作流默认构建 CPU 镜像，适合无 NVIDIA Container Toolkit 的服务器。需要 GPU 时，把工作流中的 `TORCH_INDEX=cpu` 改为 `cu128`，并按下文启用 Compose 的 GPU 资源配置。

1. 复制 `deploy/.env.example` 到仓库根目录的 `.env` 并填写随机密码：
   ```bash
   cp deploy/.env.example .env
   ```
2. 准备 `deploy/tls/fullchain.pem` 和 `deploy/tls/privkey.pem`，具体策略见 `deploy/TLS.md`。
3. 选择 PyTorch 构建变体（编辑 `.env` 的 `TORCH_INDEX`）：
   - `cu128`（默认）：GPU 版，运行时需宿主装好 NVIDIA 驱动 + Container Toolkit，并在 `docker-compose.yml` 的 `api`/`worker` 服务下取消 `# deploy.resources` 注释以启用 `--gpus all`。
   - `cpu`：纯 CPU 版，镜像更小，无 GPU 推理能力。
4. 构建应用镜像：
   ```bash
   docker compose -f deploy/docker-compose.yml --env-file .env build api
   # 或显式指定变体：
   docker compose -f deploy/docker-compose.yml --env-file .env build --build-arg TORCH_INDEX=cpu api
   ```
5. 启动控制平面依赖：`docker compose -f deploy/docker-compose.yml --env-file .env up -d postgres redis minio`。
6. 执行版本化迁移：`docker compose -f deploy/docker-compose.yml --env-file .env run --rm --no-deps api alembic upgrade head`。
7. 启动 API、worker 和反向代理：`docker compose -f deploy/docker-compose.yml --env-file .env up -d api worker proxy`。
8. 通过 `https://<host>/api/health/live` 检查进程存活，通过 `https://<host>/api/health/ready` 检查 PostgreSQL schema、Redis、MinIO 和 worker 就绪状态。

数据库 schema 的唯一初始化和升级入口为 `docker compose -f deploy/docker-compose.yml --env-file .env run --rm --no-deps api alembic upgrade head`。该命令仅迁移控制平面 PostgreSQL schema；API 启动时保留 VoiceForge 本地兼容数据库初始化。

## 镜像设计说明（`deploy/api.Dockerfile`）

- **基座统一为 `python:3.12-slim`**，不区分 CUDA 基础镜像。GPU 支持通过 PyTorch `cu128` wheel 自带的 CUDA 运行库实现，运行时 `--gpus all` 即可启用；CPU 版用 `cpu` wheel。切换仅由 `TORCH_INDEX` 决定，避免维护多套镜像。
- **多阶段**：`frontend` 阶段用 Node 20 构建 `frontend/dist`，运行时仅拷产物，不带入 `node_modules`。
- **系统依赖**：`ffmpeg`（业务逻辑大量 `subprocess` 调用）、Playwright Chromium 运行库、字体与 GUI 库（`opencv`/OCR 字幕渲染）。
- **`python` 软链**：业务以 `python -m yt_dlp` 子进程方式调用，镜像建立 `/usr/local/bin/python -> python3`。
- **持久化 volume**：`/app/data`（任务数据）、`/app/_model_cache`（HF 模型缓存，避免重复下载）、`/app/temp`（预览视频）、`/app/voiceforge_data`（VoiceForge 数据）均挂 named volume。
- **健康检查**：镜像内置 `HEALTHCHECK` 探 `/api/health/ready`；compose 另用 `python` 软链做存活检查。
- 体积大头为 PyTorch（cu128 ~1.8GB）+ Playwright Chromium（~150MB），属正常；可用 `dive` 检查层冗余。

## 注意事项

- 该镜像**不运行** `backend/manager.py`（那是 Windows 本地的进程管理器，端口 18001）。集群模式由 compose 直接拉起 `uvicorn`（api）与 `celery worker`（worker），`main.py` 自带启动期迁移与接口加载兜底。
- 首次启动会下载 AI 模型到 `/app/_model_cache`（首次较慢，之后因 volume 持久化而加速）。
- 业务若用到浏览器自动化（Playwright/CloakBrowser），镜像已预装 Chromium。

