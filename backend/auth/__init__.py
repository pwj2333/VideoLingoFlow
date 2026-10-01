"""认证模块包（本地自用模式）。

本项目已改为本地自用：没有订阅、额度与付费校验。``backend.auth.subscription_guard``
一律指向本地实现 :mod:`backend.auth.self_use_guard`，即使 auth_binaries 里仍带着
联网版的编译产物也不会被加载（编译产物内部 import subscription_guard 时同样命中别名）。

需要调用第三方云服务的节点（能力服务、腾讯云 VOD 等）改为读用户自己填的密钥，
与软件账号无关，见 backend/qmhub/auth_helper.py 与 backend/utils/tencent_vod.py。
"""
import sys

from backend.binary_path import prepend_binary_path

prepend_binary_path("auth", __path__)

from . import self_use_guard  # noqa: E402

sys.modules[f"{__name__}.subscription_guard"] = self_use_guard
