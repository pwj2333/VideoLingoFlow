"""额度提醒（本地自用模式下为空实现）。

原版在节点额度耗尽时向通知中心写「请订阅」提醒。本地自用模式不限额度、不涉及付费，
因此两个函数一律什么都不做并返回 False。

保留模块与函数签名的原因：control_plane 的编译运行时（workflow_runtime）仍会在
捕获 402/403 时调用它们，删掉会导致 worker 执行节点时 ImportError。
"""

# 旧通知里用于跳转「用户和订阅」页的标记；该页面已删除，保留常量供旧调用点引用。
SUBSCRIPTION_LINK = "subscription"


def notify_quota_exhausted(state: dict | None = None) -> bool:
    return False


def notify_quota_file_locked() -> bool:
    return False
