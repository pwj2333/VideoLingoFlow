"""qmhub（能力服务）客户端构造：密钥由用户自己配置。

原版靠软件账号登录后的 token 去云端自动申请 API Key，属于绑定云端的付费链路。
本地自用模式改为完全自配：

- 地址：``capability.base_url``（配置文件）或环境变量 ``QM_HUB_BASE_URL``
- 密钥：``capability.api_key``（配置文件，支持 ``secret://NAME`` 引用）或环境变量 ``QM_HUB_API_KEY``

两者都没填时抛出明确提示，让节点在界面上直接告诉用户去哪儿填，而不是提示「需要注册登录软件」。
"""
import os

from backend.config.config_manager import config


def _cfg(key: str, env: str) -> str:
    """先读配置文件（``secret://`` 由 config 层自动解引用），再回退环境变量。"""
    value = config.get(key, "")
    text = str(value or "").strip()
    if text:
        return text
    return os.environ.get(env, "").strip()


def get_base_url() -> str:
    return _cfg("capability.base_url", "QM_HUB_BASE_URL").rstrip("/")


def get_api_key() -> str:
    return _cfg("capability.api_key", "QM_HUB_API_KEY")


def ensure_api_key() -> str:
    """返回用户配置的能力服务密钥；未配置时抛出可读提示。"""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "未配置能力服务密钥：请在「全局设置 → 能力服务」填写 capability.api_key，"
            "或设置环境变量 QM_HUB_API_KEY"
        )
    return api_key


def build_qmhub_client():
    """构造 qmhub 客户端（地址与密钥均来自用户配置）。"""
    from backend.qmhub.client import QmHubClient

    base_url = get_base_url()
    if not base_url:
        raise RuntimeError(
            "未配置能力服务地址：请在「全局设置 → 能力服务」填写 capability.base_url，"
            "或设置环境变量 QM_HUB_BASE_URL"
        )
    return QmHubClient(api_key=ensure_api_key(), base_url=base_url)


def build_qmhub_client_with_retry():
    """与 :func:`build_qmhub_client` 等价。

    原版会在认证失败时清掉自动申请的 Key 重试一次；现在 Key 由用户自己填，
    重试没有意义（只会用同一个值再失败一次），因此直接构造。
    """
    return build_qmhub_client()


def build_mail_forwarding_client():
    """mail-forwarding 接口客户端：同样使用用户配置的密钥。"""
    return build_qmhub_client()
