"""Find the newest video on a YouTube channel and persist watch state."""
from __future__ import annotations

import json
import os
import re
from typing import Callable, Optional

from backend.steps.base_step import BaseStep


def _state_root() -> str:
    return os.path.join(os.getenv("CONTROL_PLANE_DATA_ROOT", os.path.join(os.getcwd(), "data")), "youtube_watch_state")


def _safe_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")[:120] or "channel"


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
            url = f"https://www.youtube.com/@{url}/videos"
        options = {"quiet": True, "skip_download": True, "extract_flat": True, "playlistend": 1}
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
        channel = str(config.get("channel_url") or config.get("channel_name") or "").strip()
        trigger_url = str(config.get("trigger_url") or "").strip()
        if not channel and not trigger_url:
            raise ValueError("请填写 YouTube 频道名称或频道 URL")
        if callback:
            callback(10, "检查 YouTube 频道最新视频...")
        item = {"url": trigger_url, "video_id": "", "title": ""} if trigger_url else self._latest(channel)
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
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump({**item, "channel": channel}, fh, ensure_ascii=False, indent=2)
        if callback:
            callback(100, f"发现视频：{item['title'] or item['video_id']}")
        return {"artifacts": [], "outputs": {"url": item["url"], "video_id": item["video_id"], "title": item["title"], "is_new": str(is_new).lower()}}
