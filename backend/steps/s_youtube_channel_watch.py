"""Find the newest video on a YouTube channel and persist watch state."""
from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
from urllib.parse import urlsplit, urlunsplit
from typing import Callable, Optional

from backend.steps.base_step import BaseStep


def _state_root() -> str:
    return os.path.join(os.getenv("CONTROL_PLANE_DATA_ROOT", os.path.join(os.getcwd(), "data")), "youtube_watch_state")


def _safe_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class S_YoutubeChannelWatch(BaseStep):
    step_id = "youtube_channel_watch"
    step_name = "YouTube频道监视"
    dependencies = []
    artifacts = []

    def check_artifact(self, task_dir: str) -> bool:
        return False

    def validate_inputs(self, task_dir: str) -> bool:
        return True

    def _latest(self, channel: str) -> dict:
        from yt_dlp import YoutubeDL

        url = channel.strip()
        if not url.startswith("http"):
            url = f"https://www.youtube.com/@{url.lstrip('@')}/videos"
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or parts.hostname not in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            raise ValueError("请使用 YouTube 频道 URL 或 @用户名")
        path = parts.path.rstrip("/")
        if re.fullmatch(r"/(?:@[^/]+|(?:channel|c|user)/[^/]+)", path):
            path += "/videos"
        if not path.endswith("/videos"):
            raise ValueError("请使用 YouTube 频道的视频列表地址")
        url = urlunsplit((parts.scheme, parts.netloc, path, "", ""))
        options = {"quiet": True, "skip_download": True, "extract_flat": True, "playlistend": 1, "socket_timeout": 20, "retries": 2}
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = [item for item in (info.get("entries") or []) if item]
        if not entries:
            raise ValueError("频道没有可用视频，或 YouTube 暂时无法访问")
        item = entries[0]
        video_id = str(item.get("id") or "").strip()
        if not video_id:
            raise ValueError("无法读取频道最新视频 ID")
        return {
            "video_id": video_id,
            "url": item.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
            "title": str(item.get("title") or ""),
        }

    def run(self, task_dir: str, callback: Optional[Callable] = None) -> dict:
        config = getattr(self, "_node_config", {}) or {}
        step_inputs = getattr(self, "_step_inputs", {}) or {}
        channel = str(config.get("channel_url") or config.get("channel_name") or "").strip()
        trigger_url = str(config.get("trigger_url") or "").strip()
        manual_url = str(step_inputs.get("url") or "").strip()
        if not channel and not trigger_url and not manual_url:
            raise ValueError("请填写 YouTube 频道名称或频道 URL")
        if callback:
            callback(10, "检查 YouTube 频道最新视频...")
        item = {"url": trigger_url or manual_url, "video_id": "", "title": ""} if (trigger_url or manual_url) else self._latest(channel)
        if trigger_url:
            match = re.search(r"[?&]v=([^&]+)|youtu\.be/([^/?]+)", trigger_url)
            item["video_id"] = next((part for part in match.groups() if part), "") if match else trigger_url
        key = _safe_key(channel or item["url"])
        os.makedirs(_state_root(), exist_ok=True)
        state_path = os.path.join(_state_root(), f"{key}.json")
        previous = {}
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                previous = json.load(fh)
        except (OSError, ValueError):
            pass
        is_new = item["video_id"] != previous.get("video_id") if item["video_id"] else True
        if config.get("only_new", True) and not is_new and not trigger_url:
            raise ValueError("频道没有新视频")
        _save_state(state_path, {**item, "channel": channel})
        if callback:
            callback(100, f"发现视频：{item['title'] or item['video_id']}")
        return {"artifacts": [], "outputs": {"url": item["url"], "video_id": item["video_id"], "title": item["title"], "is_new": str(is_new).lower()}}
