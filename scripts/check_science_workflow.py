"""Run with: python scripts/check_science_workflow.py"""
import copy
import json
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pysubs2
from backend.steps.s_merge_dub import S_MergeDub
from backend.utils.ass_wrapper import srt_to_ass
from backend.utils.subtitle_style_service import package_subtitles_to_ass
from backend.workflow_validation import normalize_workflow
from backend.services import youtube_watch_scheduler as scheduler
from scripts.ensure_science_workflow_nodes import patch_data


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    srt = root / "test.srt"
    spoken = "人工智能模型通过训练学习规律" * 25 + "。下一句话讲解 Fable 5.5。"
    S_MergeDub._write_srt([{"text": spoken}], str(srt), [(3, 83)])
    events = pysubs2.load(str(srt))
    assert len(events) > 3
    assert events[0].start == 3000 and events[-1].end == 83000
    assert all(e.end > e.start and len(e.text.split(r"\N")) <= 2 for e in events)
    assert all(a.end == b.start for a, b in zip(events, events[1:]))
    assert "5.5" in "".join(e.text for e in events)
    srt.write_text("1\n00:00:03,000 --> 00:01:23,000\n" + "人工智能" * 70 + "\n第二行\n第三行\n", encoding="utf-8")
    ass = root / "test.ass"
    srt_to_ass(str(srt), {"fontSize": 38, "marginL": 220, "marginR": 220}, str(ass), max_lines=2)
    events = pysubs2.load(str(ass))
    assert len(events) > 1 and events.info["WrapStyle"] == "2"
    assert events[0].start == 3000 and events[-1].end == 83000
    assert all(e.end > e.start and len(e.text.split(r"\N")) <= 2 and e.text.startswith(r"{\q2}") for e in events)
    assert all(a.end == b.start for a, b in zip(events, events[1:]))
    assert "".join(re.sub(r"\{[^}]*\}", "", e.text).replace(r"\N", "") for e in events) == "人工智能" * 70 + "第二行第三行"
    packaged = package_subtitles_to_ass(str(srt), str(ass), preset_id="ai_science_clean", force_bilingual=False, max_lines=2)
    assert packaged["mode"] == "single"
    assert all(len(e.text.split(r"\N")) <= 2 for e in pysubs2.load(str(ass)))

    workflow = {"id": "science", "type": "user", "nodes": [
        {"id": node_id, "data": {"nodeType": node_type, "config": {}}, "position": {"x": 0, "y": 0}}
        for node_id, node_type in (("source", "input"), ("download", "platform_download"), ("burn", "merge_sub_video"), ("final", "output"))
    ], "edges": []}
    assert patch_data(workflow)
    watcher = next(n for n in workflow["nodes"] if n["id"] == "youtube_watch")
    publisher = next(n for n in workflow["nodes"] if n["id"] == "bilibili_publish")
    watcher["data"]["config"]["channel_name"] = "@example"
    publisher["data"]["config"]["account_ids"] = ["chosen-account"]
    before = copy.deepcopy(workflow)
    assert not patch_data(workflow) and workflow == before
    normalized, _, removed = normalize_workflow(workflow)
    assert removed == 0 and normalized["edges"] == workflow["edges"]

    watcher["data"]["config"]["schedule_enabled"] = True
    workflow_file = root / "science.json"
    workflow_file.write_text(json.dumps(workflow), encoding="utf-8")
    scheduler._last_checked.clear()
    item = {"video_id": "first", "url": "https://www.youtube.com/watch?v=first"}
    with patch.object(scheduler, "_workflows_dir", return_value=directory), \
         patch("backend.steps.s_youtube_channel_watch._state_root", return_value=str(root / "state")), \
         patch.object(scheduler, "_latest", side_effect=lambda _: dict(item)), \
         patch("backend.control_plane.workflow_runtime.submit_workflow", create=True) as submit, \
         patch.object(scheduler.time, "time", return_value=10000) as now:
        watcher["data"]["disableExecute"] = True
        workflow_file.write_text(json.dumps(workflow), encoding="utf-8")
        scheduler._scan_once()
        assert not (root / "state").exists()
        watcher["data"]["disableExecute"] = False
        workflow_file.write_text(json.dumps(workflow), encoding="utf-8")
        scheduler._scan_once()
        submit.assert_not_called()  # only_new starts by recording a baseline.
        now.return_value += 2000
        item.update(video_id="second", url="https://www.youtube.com/watch?v=second")
        scheduler._scan_once()
        assert submit.call_count == 1
        assert next(n for n in submit.call_args.args[0]["nodes"] if n["id"] == "youtube_watch")["data"]["config"]["trigger_url"] == item["url"]
        scheduler._last_checked.clear()  # simulate an API restart
        scheduler._scan_once()
        now.return_value += 2000
        scheduler._scan_once()
        assert submit.call_count == 1
        now.return_value += 2000
        item["video_id"] = "third"
        submit.side_effect = RuntimeError("submission failed")
        scheduler._scan_once()
        submit.side_effect = None
        now.return_value += 2000
        scheduler._scan_once()
        assert submit.call_count == 3

print("PASS: subtitle timing, two-line ASS, config preservation, valid edges, persistent watcher and retry")
