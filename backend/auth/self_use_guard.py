"""Local subscription state for a non-commercial, single-owner installation."""


class SelfUseGuard:
    def get_subscription_state(self, force_refresh=False):
        return {
            "software_id": "vlf3387",
            "self_use": True,
            "is_logged_in": True,
            "user_type": "subscribed",
            "user_info": {"username": "local-owner"},
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
        return {"ok": True, "message": "本地自用模式无需领取额度", "state": self.get_subscription_state()}

    def recover_usage(self):
        return None


_guard = SelfUseGuard()


def get_subscription_guard():
    return _guard


def start_limits_refresh():
    return None
