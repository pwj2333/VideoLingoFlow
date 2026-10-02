"""Run with: python scripts/check_llm_setup.py"""
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.config_manager import ConfigManager
from backend.llm import direct_router


with tempfile.TemporaryDirectory() as root:
    config_path = Path(root) / "config.yaml"
    with patch("backend.config.config_manager.RUNTIME_CONFIG_PATH", str(config_path)):
        first = ConfigManager()
        assert first.get("llm.use_router") is False
        first.set("llm.step_models.default_model", "demo-model")
        assert ConfigManager().get("llm.step_models.default_model") == "demo-model"

    db_path = Path(root) / "router.db"
    with patch.object(direct_router, "_DB_PATH", db_path):
        try:
            direct_router._get_conn()
        except direct_router.DirectRouterError as exc:
            assert "尚未配置" in str(exc)
        else:
            raise AssertionError("missing router DB was accepted")
        assert not db_path.exists()

        sqlite3.connect(db_path).close()
        try:
            direct_router._get_conn()
        except direct_router.DirectRouterError as exc:
            assert "未初始化" in str(exc)
        else:
            raise AssertionError("empty router DB was accepted")

print("LLM setup checks passed")
