"""腾讯云 VOD 上传：密钥由用户自己配置，不经过任何软件账号或代理服务。

原版的上传函数在闭源的 ``backend.auth.cloud_auth_service`` 里，用软件账号换取云端代签名，
属于绑定云端的链路。本地自用模式改为直接用用户自己的腾讯云子账号密钥调用官方 SDK。

配置位置（任一即可，配置文件优先）：

``backend/config/config.yaml``::

    tencent_vod:
      secret_id: "secret://TENCENT_SECRET_ID"   # 也可直接写明文
      secret_key: "secret://TENCENT_SECRET_KEY"
      region: "ap-guangzhou"                    # 可选，默认 ap-guangzhou
      sub_app_id: 0                             # 可选，子应用；0 表示主应用
      procedure: ""                             # 可选，上传后触发的任务流名

环境变量：``TENCENT_SECRET_ID`` / ``TENCENT_SECRET_KEY`` / ``TENCENT_VOD_REGION`` /
``TENCENT_VOD_SUB_APP_ID`` / ``TENCENT_VOD_PROCEDURE``。

依赖 ``vod-python-sdk`` 与 ``tencentcloud-sdk-python-vod``（已在 backend/requirements.txt 中）。
"""
import os
from typing import Any

from backend.config.config_manager import config

DEFAULT_REGION = "ap-guangzhou"


def _setting(cfg_key: str, env_key: str, default: str = "") -> str:
    """配置文件优先（``secret://`` 由 config 层解引用），回退环境变量，再回退默认值。"""
    value = str(config.get(cfg_key, "") or "").strip()
    if value:
        return value
    return os.environ.get(env_key, "").strip() or default


def _credentials() -> tuple[str, str]:
    secret_id = _setting("tencent_vod.secret_id", "TENCENT_SECRET_ID")
    secret_key = _setting("tencent_vod.secret_key", "TENCENT_SECRET_KEY")
    if not secret_id or not secret_key:
        raise RuntimeError(
            "未配置腾讯云 VOD 密钥：请在 backend/config/config.yaml 的 tencent_vod 段填写 "
            "secret_id / secret_key，或设置环境变量 TENCENT_SECRET_ID / TENCENT_SECRET_KEY。"
            "密钥在腾讯云控制台「访问管理 → API 密钥管理」创建，建议使用仅授权 VOD 的子账号。"
        )
    return secret_id, secret_key


def _sub_app_id() -> int:
    raw = _setting("tencent_vod.sub_app_id", "TENCENT_VOD_SUB_APP_ID", "0")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _region() -> str:
    return _setting("tencent_vod.region", "TENCENT_VOD_REGION", DEFAULT_REGION)


def _upload(media_path: str) -> tuple[str, str]:
    """上传文件到 VOD，返回 ``(file_id, media_url)``。"""
    from qcloud_vod.model import VodUploadRequest
    from qcloud_vod.vod_upload_client import VodUploadClient

    secret_id, secret_key = _credentials()
    client = VodUploadClient(secret_id, secret_key)

    request = VodUploadRequest()
    request.MediaFilePath = media_path
    sub_app_id = _sub_app_id()
    if sub_app_id:
        request.SubAppId = sub_app_id
    procedure = _setting("tencent_vod.procedure", "TENCENT_VOD_PROCEDURE")
    if procedure:
        request.Procedure = procedure

    response = client.upload(_region(), request)
    file_id = getattr(response, "FileId", "") or ""
    media_url = getattr(response, "MediaUrl", "") or ""
    if not file_id:
        raise RuntimeError("腾讯云 VOD 上传失败：未返回 FileId")
    return file_id, media_url


def _describe(file_id: str) -> dict[str, Any]:
    """查询媒体详情；失败时返回空字典（上传本身已成功，不因查询失败阻断流程）。"""
    try:
        import json

        from tencentcloud.common import credential
        from tencentcloud.vod.v20180717 import models, vod_client

        secret_id, secret_key = _credentials()
        client = vod_client.VodClient(credential.Credential(secret_id, secret_key), _region())
        request = models.DescribeMediaInfosRequest()
        payload: dict[str, Any] = {"FileIds": [file_id], "Filters": ["basicInfo", "metaData"]}
        sub_app_id = _sub_app_id()
        if sub_app_id:
            payload["SubAppId"] = sub_app_id
        request.from_json_string(json.dumps(payload))
        body = json.loads(client.DescribeMediaInfos(request).to_json_string())
        infos = body.get("MediaInfoSet") or []
        return infos[0] if infos else {}
    except Exception:
        return {}


def _meta_from_info(info: dict[str, Any]) -> dict[str, Any]:
    """把 VOD 的 MetaData 整理成下游节点需要的 ``meta_data``（duration/width/height 等）。"""
    meta = info.get("MetaData") or {}
    return {
        "duration": float(meta.get("Duration") or 0),
        "width": int(meta.get("Width") or 0),
        "height": int(meta.get("Height") or 0),
        "bitrate": int(meta.get("Bitrate") or 0),
        "size": int(meta.get("Size") or 0),
        "container": meta.get("Container") or "",
        "rotate": meta.get("Rotate") or 0,
        "raw": meta,
    }


def upload_to_tencent_vod_with_details(media_path: str) -> dict[str, Any]:
    """上传媒体到腾讯云 VOD 并返回 URL + 媒体详情。

    返回结构与原闭源实现保持一致，供 ``s_media_to_url`` 直接使用::

        {"url", "file_id", "media_name", "category", "media_type",
         "storage_region", "create_time", "duration", "meta_data"}
    """
    if not media_path or not os.path.isfile(media_path):
        raise FileNotFoundError(f"待上传文件不存在: {media_path}")

    file_id, media_url = _upload(media_path)
    info = _describe(file_id)
    basic = info.get("BasicInfo") or {}
    meta = _meta_from_info(info)

    return {
        "url": basic.get("MediaUrl") or media_url,
        "file_id": file_id,
        "media_name": basic.get("Name") or os.path.splitext(os.path.basename(media_path))[0],
        "category": basic.get("Type") or "",
        "media_type": basic.get("Type") or "",
        "storage_region": basic.get("StorageRegion") or _region(),
        "create_time": basic.get("CreateTime") or "",
        "duration": meta["duration"],
        "meta_data": meta,
    }
