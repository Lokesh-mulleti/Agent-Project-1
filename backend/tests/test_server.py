"""
Integration tests for FastAPI server endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.server import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "registered_tools" in data
    assert len(data["registered_tools"]) >= 5


def test_list_tools_endpoint():
    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    assert data["total_tools"] >= 5
    tool_names = [t["name"] for t in data["tools"]]
    assert "calculate" in tool_names
    assert "convert_currency" in tool_names
    assert "read_document" in tool_names
    assert "get_weather" in tool_names
    assert "search_web" in tool_names


def test_execute_tool_endpoint():
    res = client.post(
        "/api/tools/execute",
        json={"tool_name": "calculate", "arguments": {"expression": "25 * 4"}},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Result: 100" in data["result"]
    assert "duration_ms" in data


def test_upload_doc_endpoint():
    sample_content = b"Strategic Plan: Revenue grew by 50% reaching $100M. Crucial milestone achieved."
    files = {"file": ("strategy.txt", sample_content, "text/plain")}
    res = client.post("/api/upload-doc", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "analysis" in data
    assert data["filename"] == "strategy.txt"


def test_settings_get_and_post():
    res = client.get("/api/settings")
    assert res.status_code == 200

    post_res = client.post("/api/settings", json={"llm_provider": "mock", "temperature": 0.3})
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"
