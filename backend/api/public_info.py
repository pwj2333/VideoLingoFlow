"""公共信息接口（本地自用模式）。

原版会向云端拉取版本更新与运营公告；本地自用模式不联网，公告恒为空，
版本只报本地配置里的 version。GitHub Release 的更新检查另有入口
（``/api/github-update``，见 backend/api/github_update.py），与账号无关。
"""
from fastapi import APIRouter, HTTPException

from backend.auth.self_use_guard import SOFTWARE_CODE
from backend.config.config_manager import config

router = APIRouter(prefix="/api/public-info")

# 后端程序版本：取自配置 version（单一来源），缺省时回退内置值。
# 同时用于 OpenAPI 文档版本、/version 接口与 /api/public-info 的 local_version，
# 保证顶栏角标、About 页与接口文档展示同一个版本号。
APP_VERSION = str(config.get("version", "") or "2.0.0")


def _local_version() -> str:
    """本地版本：优先取配置 version，缺省回退到程序内置版本。"""
    return str(config.get("version", "") or APP_VERSION)


@router.get("")
async def get_public_info():
    return {
        "software_id": SOFTWARE_CODE,
        "local_version": _local_version(),
        "update": None,
        "announcements": [],
        "update_error": None,
        "announcement_error": None,
    }


@router.get("/announcements")
async def get_announcements():
    """本地自用模式没有运营公告，恒返回空列表。"""
    return {"announcements": [], "error": None}


@router.get("/version")
async def get_local_version():
    """本地版本信息（不访问网络，供顶栏版本角标即时展示）。"""
    return {
        "version": _local_version(),
        "api_version": APP_VERSION,
        "software_id": SOFTWARE_CODE,
    }


@router.get("/download-url")
async def get_download_url():
    raise HTTPException(status_code=404, detail="本地自用模式不提供云端下载，请从项目仓库自行获取")
