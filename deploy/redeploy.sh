#!/usr/bin/env bash
# 一键重新部署：拉最新镜像 -> 起依赖服务 -> 跑数据库迁移 -> 重启应用服务 -> 清理旧镜像
# 用法：在服务器上，deploy/ 目录下执行  ./redeploy.sh
set -euo pipefail
cd "$(dirname "$0")"

docker compose --env-file .env pull api worker voiceforge-worker
docker compose --env-file .env up -d postgres redis minio
docker compose --env-file .env run --rm --no-deps api alembic upgrade head
docker compose --env-file .env up -d api worker voiceforge-worker proxy
docker image prune -f

echo "部署完成，当前服务状态："
docker compose --env-file .env ps
