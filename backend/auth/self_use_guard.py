"""本地自用模式的订阅状态：无付费、无额度、无云端校验。

本模块替换原先联网的 ``backend.auth.subscription_guard``（见 backend/auth/__init__.py），
所有额度检查一律放行，``daily_limit`` / ``daily_node_limit`` 恒为 None（表示不限量）。
账号信息来自本地 control-plane 用户表（见 [[local_account]]）。
"""

SOFTWARE_CODE = "yunzhiai"


def _local_user() -> dict:
    try:
        from backend.auth.local_account import current_username, default_credentials

        username = current_username() or default_credentials()[0]
    except Exception:
        username = "local"
    return {"username": username, "is_active": True}


class SelfUseGuard:
    def get_subscription_state(self, force_refresh=False):
        return {
            "software_id": SOFTWARE_CODE,
            "self_use": True,
            "is_logged_in": True,
            "user_type": "subscribed",
            "user_info": _local_user(),
            "entitlements": [],
            "active_entitlement": None,
            "daily_usage": 0,
            "daily_limit": None,
            "remaining_today": None,
            "daily_node_usage": 0,
            "daily_node_limit": None,
            "remaining_nodes_today": None,
            "can_create_task": True,
            "can_execute_node": True,
            "can_claim_quota": False,
            "claimable_count": 0,
            "links": {},
        }

    def check_task_allowed(self, count=1):
        return self.get_subscription_state()

    def check_node_allowed(self, count=1):
        return self.get_subscription_state()

    def consume_for_task(self, count=1, reason="run_task"):
        return self.get_subscription_state()

    def consume_for_node(self, count=1, reason="run_node"):
        return self.get_subscription_state()

    def claim_quota(self):
        return {"ok": True, "message": "本地自用模式不限量，无需领取额度", "state": self.get_subscription_state()}

    def recover_usage(self):
        return None


_guard = SelfUseGuard()


def get_subscription_guard():
    return _guard


def start_limits_refresh():
    """原版会后台拉取云端限额；本地自用模式无需联网，保留空实现供旧调用点使用。"""
    return None
