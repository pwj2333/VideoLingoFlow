"""Poll enabled YouTube watcher nodes and submit the saved workflow on new videos."""
from __future__ import annotations

import copy
import json
import os
import threading
import time

_stop = threading.Event()
_thread: threading.Thread | None = None
_last_checked: dict[str, float] = {}


def _workflows_dir() -> str:
    return os.getenv("YUNZHIAI_WORKFLOWS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "workflows"))


def _latest(channel: str) -> dict:
    from backend.steps.s_youtube_channel_watch import S_YoutubeChannelWatch
    return S_YoutubeChannelWatch()._latest(channel)


def _scan_once() -> None:
    from backend.control_plane.workflow_runtime import submit_workflow

    root = _workflows_dir()
    for filename in os.listdir(root) if os.path.isdir(root) else []:
        if not filename.endswith(".json"):
            continue
        path = os.path.join(root, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                workflow = json.load(fh)
        except (OSError, ValueError):
            continue
        if workflow.get("type") == "task":
            continue
        nodes = workflow.get("nodes") or []
        watchers = [n for n in nodes if (n.get("data") or {}).get("nodeType") == "youtube_channel_watch"]
        for watcher in watchers:
            config = (watcher.get("data") or {}).get("config") or {}
            if config.get("schedule_enabled") is not True or (watcher.get("data") or {}).get("disableExecute"):
                continue
            channel = str(config.get("channel_url") or config.get("channel_name") or "").strip()
            if not channel:
                continue
            try:
                from backend.steps.s_youtube_channel_watch import _safe_key, _state_root, _save_state
                interval = max(5, int(config.get("poll_interval_minutes", 30) or 30)) * 60
                watch_key = f"{filename}:{watcher['id']}:{channel}"
                state_path = os.path.join(_state_root(), f"schedule-{_safe_key(watch_key)}.json")
                previous = {}
                if os.path.exists(state_path):
                    with open(state_path, encoding="utf-8") as fh:
                        previous = json.load(fh)
                now = time.time()
                if now - max(previous.get("checked_at", 0), _last_checked.get(watch_key, 0)) < interval:
                    continue
                _last_checked[watch_key] = now
                item = _latest(channel)
                state = {"video_id": item["video_id"], "checked_at": now}
                # ponytail: one API scheduler; persisted state and submission
                # idempotency cover restarts. Multiple APIs need a DB lease.
                if item["video_id"] == previous.get("video_id") or (not previous and config.get("only_new", True)):
                    _save_state(state_path, state)
                    continue
                state_key = f"youtube:{os.path.splitext(filename)[0]}:{item['video_id']}"
                triggered = copy.deepcopy(workflow)
                for node in triggered.get("nodes", []):
                    if node.get("id") == watcher["id"]:
                        node.setdefault("data", {}).setdefault("config", {})["trigger_url"] = item["url"]
                        node["data"]["config"]["only_new"] = False
                submit_workflow(triggered, {"url": item["url"]}, mode="new", idempotency_scope=state_key)
                _save_state(state_path, state)
                print(f"[YouTubeWatch] submitted {item['video_id']} for {filename}", flush=True)
            except Exception as exc:
                # A channel may be private/rate limited; retry on the next poll.
                print(f"[YouTubeWatch] {filename}: {exc}", flush=True)


def _run() -> None:
    while not _stop.wait(60):
        try:
            _scan_once()
        except Exception as exc:
            print(f"[YouTubeWatch] scan failed: {exc}", flush=True)


def start_youtube_watch_scheduler() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_run, name="youtube-watch", daemon=True)
    _thread.start()


def stop_youtube_watch_scheduler() -> None:
    _stop.set()
