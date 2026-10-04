"""Update the persisted AI science workflow defaults in place."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def patch(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    backup = path.with_suffix(path.suffix + ".bak-before-science-redesign")
    if not backup.exists():
        shutil.copy2(path, backup)
    data["description"] = "YouTube字幕按句生成中文旁白；每句配图时长跟随对应TTS；技术信息图风格；单语字幕清晰烧录。"
    for node in data.get("nodes", []):
        node_data = node.get("data") or {}
        config = node_data.setdefault("config", {})
        node_id = str(node.get("id") or "")
        node_type = node_data.get("nodeType")
        if node_type == "dub_task":
            config.update({
                "normalize_chinese_read_text": True,
                "speed_predict_reduce": True,
                "ai_read_tone": False,
                "ai_dialect_colloquial": False,
            })
        elif node_id == "script" and node_type == "llm_request":
            config["system_prompt"] = (
                "你是严谨的中文AI技术科普编剧。只根据输入字幕中明确出现或可合理概括的事实写作，"
                "不要虚构型号、价格、日期、性能和新闻；数字必须保留为可读中文表达。"
            )
            config["user_prompt"] = (
                "根据下面的YouTube字幕，创作恰好10段中文旁白。每段独占一行，每段约180至220个汉字，"
                "总时长约8至10分钟。第1段提出问题，第2至9段按逻辑解释，第10段总结。"
                "只输出10行旁白正文，不要标题、编号、项目符号、空行或画面说明。\n字幕：\n{input_text}"
            )
        elif node_id == "prompts" and node_type == "llm_request":
            config["system_prompt"] = "你是技术信息图提示词设计师，只输出严格JSON。"
            config["user_prompt"] = (
                "把10段旁白分别改写为10条对应的AI生图提示词，输出JSON对象，键名必须是p1到p10。"
                "每条提示词只描述对应段落的一个核心概念，保持同一套横向16:9技术信息图风格。"
                "白色或极浅色背景、模块化网格、圆角信息卡片、流程箭头、连接线、编号标题、"
                "低饱和蓝绿紫橙辅助色、扁平矢量、统一线性图标、现代SaaS技术文档感、留白充足。"
                "不要生成字幕、长段文字、随机字母、随机数字、Logo、水印或装饰性杂乱元素。"
                "只输出JSON，不要Markdown。\n旁白：\n{input_text}"
            )
        elif node_type == "image_gen" and node_id.startswith("image_"):
            config.update({
                "technical_infographic": True,
                "resolution": "2K",
                "aspect_ratio": "16:9",
                "negative_prompt": "photorealistic, cinematic dark background, gradients, glossy 3D, random text, gibberish, fake numbers, watermark, logo, clutter, tiny unreadable labels",
            })
        elif node_type == "add_track_media" and node_id.startswith("track_"):
            config.update({"duration_from_tts": True, "static_duration": 3})
            number = node_id.rsplit("_", 1)[-1]
            node_data["label"] = f"剪辑{number} 图片时长=对应段落配音"
        elif node_type == "merge_dub":
            # Keep image boundaries identical to the concatenated TTS WAVs.
            config["silence_interval"] = 0.0
        elif node_type == "merge_sub_video":
            config.update({
                "preset_id": "ai_science_clean",
                "dub_volume": 0.9,
                "mute_original": True,
            })
        elif node_type == "output":
            config["fileName"] = "AI科普视频"
    # The subtitle burner re-encodes the video, so pass the merged TTS WAV
    # explicitly to preserve narration in the final MP4.
    edges = data.setdefault("edges", [])
    added_audio_edge = False
    if not any(
        edge.get("source") == "dub_merge"
        and edge.get("target") == "burn"
        and edge.get("targetHandle") == "in-dub"
        for edge in edges
    ):
        edges.append({
            "id": "e_dub_merge_audio_burn_dub",
            "source": "dub_merge",
            "target": "burn",
            "sourceHandle": "out-audio",
            "targetHandle": "in-dub",
            "type": "smoothstep",
            "style": {"stroke": "#10b981", "strokeDasharray": "6 3"},
        })
        added_audio_edge = True
    if added_audio_edge:
        data["revision"] = int(data.get("revision", 0) or 0) + 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
