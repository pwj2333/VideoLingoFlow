"""订阅接口（本地自用模式）。

付费相关接口（注册、找回密码、卡密验证、领取额度、设备绑定、购买链接）已全部移除。
这里只保留前端仍在调用的几个只读/无副作用入口，避免老前端构建产物 404：

- ``GET  /api/subscription/status``       本地状态：恒为已登录、不限量
- ``POST /api/subscription/refresh``      同 status（本地无云端可刷新）
- ``POST /api/subscription/quota-notice`` 本地不限量，恒不写通知
- ``GET  /api/subscription/links``        指向本项目仓库，不是购买页

账号登录/登出/改密统一走 ``/api/control/auth/*``（本地用户名密码，见 backend/api/control_plane.py）。
"""
from fastapi import APIRouter

from backend.auth.subscription_guard import get_subscription_guard

router = APIRouter()
# 兼容旧的装配方式：本地自用模式下两个名字指向同一个路由器
self_use_router = router

_REPO = "https://github.com/pwj2333/VideoLingoFlow"


@router.get("/status")
async def get_status():
    return get_subscription_guard().get_subscription_state()


@router.post("/refresh")
async def refresh_status():
    return get_subscription_guard().get_subscription_state()


@router.post("/quota-notice")
async def quota_notice():
    """本地自用模式不限额度，永远不写「额度已用完」通知。"""
    return {"notified": False, "state": get_subscription_guard().get_subscription_state()}


@router.get("/links")
async def get_links():
    return {"products": _REPO, "home": _REPO, "versions": f"{_REPO}/releases"}
