"""Run with: python scripts/check_workflow_persistence.py"""
import importlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory() as root:
    os.environ["YUNZHIAI_WORKFLOWS_DIR"] = str(Path(root) / "workflows")
    os.environ["YUNZHIAI_WORKFLOW_GROUPS_FILE"] = str(Path(root) / "workflow_groups.json")
    from backend.api import workflows

    files = list(Path(workflows.WORKFLOWS_DIR).glob("*.json"))
    assert files, "bundled workflows were not seeded"
    assert (Path(workflows.WORKFLOWS_DIR) / ".initialized").exists()
    files[0].unlink()
    importlib.reload(workflows)
    assert not files[0].exists(), "deleted workflow reappeared after restart"
    assert Path(workflows.WORKFLOW_GROUPS_FILE).exists()

print("workflow persistence checks passed")
