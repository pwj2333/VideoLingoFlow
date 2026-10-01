"""本地自用模式的账号来源：复用 control-plane 的本地用户表，不联网。

本模块只做两件事：
1. 启动时确保存在一个可登录的本地管理员（默认 admin / admin123456，可用环境变量覆盖）；
2. 向订阅状态接口提供「当前本地账号名」，让界面显示真实用户名而不是「游客」。

密码只以 bcrypt 哈希形式存在 control-plane 数据库里，配置文件和日志都不落明文。
登录/登出/改密走 ``/api/control/auth/*``（见 backend/api/control_plane.py）。
"""

import os

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123456"
DEFAULT_DISPLAY_NAME = "本地用户"


def default_credentials() -> tuple[str, str, str]:
    """默认本地账号。可用 YUNZHIAI_LOCAL_USER / YUNZHIAI_LOCAL_PASSWORD 覆盖。"""
    username = (os.getenv("YUNZHIAI_LOCAL_USER", "") or DEFAULT_USERNAME).strip() or DEFAULT_USERNAME
    password = os.getenv("YUNZHIAI_LOCAL_PASSWORD", "") or DEFAULT_PASSWORD
    display = (os.getenv("YUNZHIAI_LOCAL_DISPLAY_NAME", "") or DEFAULT_DISPLAY_NAME).strip() or DEFAULT_DISPLAY_NAME
    return username, password, display


def ensure_local_admin() -> dict:
    """确保本地存在一个管理员账号；已存在时不改动密码。

    返回 ``{"created": bool, "username": str}``；数据库不可用时返回 created=False 并吞掉异常，
    不让启动流程因为账号初始化失败而中断。
    """
    username, password, display = default_credentials()
    try:
        from sqlalchemy import select

        from backend.control_plane.database import session_scope
        from backend.control_plane.models import Role, User, UserRole
        from backend.control_plane.security import password_hash

        with session_scope() as db:
            if db.scalar(select(User.id).limit(1)):
                return {"created": False, "username": current_username() or username}
            admin_role = db.scalar(select(Role).where(Role.name == "admin"))
            roles = []
            if admin_role is None:
                admin_role = Role(name="admin")
                roles.append(admin_role)
            for name in ("editor", "viewer"):
                if db.scalar(select(Role.id).where(Role.name == name)) is None:
                    roles.append(Role(name=name))
            user = User(username=username, display_name=display, password_hash=password_hash(password))
            db.add_all([*roles, user])
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))
            return {"created": True, "username": username}
    except Exception:
        return {"created": False, "username": username}


def current_username() -> str:
    """本地第一个启用的账号名；取不到时返回空字符串。"""
    try:
        from sqlalchemy import select

        from backend.control_plane.database import session_scope
        from backend.control_plane.models import User

        with session_scope() as db:
            return db.scalar(select(User.username).where(User.is_active.is_(True)).order_by(User.created_at).limit(1)) or ""
    except Exception:
        return ""
