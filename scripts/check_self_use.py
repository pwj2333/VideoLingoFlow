"""Run with: python scripts/check_self_use.py"""

import os
import sys
from pathlib import Path

os.environ["YUNZHIAI_SELF_USE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.auth.subscription_guard import get_subscription_guard
from backend.control_plane import workflow_runtime
from backend.main import app
from fastapi.testclient import TestClient

state = get_subscription_guard().get_subscription_state()
assert state["self_use"] and state["can_create_task"] and state["can_execute_node"]
assert state["daily_limit"] is None and state["daily_node_limit"] is None
assert get_subscription_guard().consume_for_node()["can_execute_node"]
assert workflow_runtime is not None
routes = {route.path for route in app.routes}
assert "/api/subscription/status" in routes
assert "/api/subscription/register" not in routes
assert "/api/subscription/verify-card" not in routes
client = TestClient(app, base_url="http://127.0.0.1")
assert client.get("/api/subscription/status").json()["self_use"]
assert client.get("/api/public-info").json()["announcements"] == []
print("self-use check passed")
