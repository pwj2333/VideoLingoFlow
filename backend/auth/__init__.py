"""认证与订阅模块包。"""
import os
import sys

from backend.binary_path import prepend_binary_path

prepend_binary_path("auth", __path__)

if os.getenv("YUNZHIAI_SELF_USE", "1") == "1":
    from . import self_use_guard

    # ponytail: This replaces Python imports of the subscription guard only;
    # external paid services still need their own credentials.
    sys.modules[f"{__name__}.subscription_guard"] = self_use_guard
