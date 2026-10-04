"""Add valid science workflow connections without replacing user configuration."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


def patch_data(data: dict) -> bool:
    before = copy.deepcopy(data)
    nodes = data.setdefault("nodes", [])
    edges = data.setdefault("edges", [])
    by_id = {node["id"]: node for node in nodes}
    if not all(key in by_id for key in ("source", "download", "burn", "final")):
        raise ValueError("workflow must contain source, download, burn, and final")
    for node_id, node_type, anchor, offset, label, config in (
        ("youtube_watch", "youtube_channel_watch", "source", -490, "YouTube频道定时任务", {
            "channel_name": "", "channel_url": "", "schedule_enabled": False,
            "poll_interval_minutes": 30, "only_new": True, "trigger_url": "",
        }),
        ("bilibili_publish", "video_publish", "final", 500, "自动上传B站", {
            "account_ids": [], "title": "AI科普视频", "description": "",
            "tags": "AI,人工智能,科技科普", "is_original": True,
            "publish_mode": "publish", "schedule_enabled": False,
            "schedule_time": "", "declaration": "ai_generated",
        }),
    ):
        if node_id not in by_id:
            position = by_id[anchor].get("position") or {}
            node = {"id": node_id, "type": "workflow",
                    "position": {"x": position.get("x", 0) + offset, "y": position.get("y", 0)},
                    "data": {"nodeType": node_type, "label": label, "config": config}}
            nodes.append(node)
            by_id[node_id] = node
        elif by_id[node_id]["data"]["nodeType"] != node_type:
            raise ValueError(f"{node_id} has an unexpected node type")
    # Output nodes are terminal: connect the burned MP4 to both output and publish.
    edges[:] = [e for e in edges if not (
        (e.get("source") == "source" and e.get("target") == "download") or
        (e.get("source") == "final" and e.get("target") == "bilibili_publish"))]
    for source, target in (("source", "youtube_watch"), ("youtube_watch", "download"), ("burn", "bilibili_publish")):
        port = "video" if source == "burn" else "url"
        handles = {"source": source, "target": target, "sourceHandle": f"out-{port}", "targetHandle": f"in-{port}"}
        if not any(all(edge.get(k) == v for k, v in handles.items()) for edge in edges):
            edges.append({"id": f"e_{source}_{port}_{target}_{port}", "type": "smoothstep", **handles})
    return before != data


def patch(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if patch_data(data):
        data["revision"] = int(data.get("revision", 0) or 0) + 1
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: ensure_science_workflow_nodes.py WORKFLOW_JSON")
    patch(Path(sys.argv[1]))
