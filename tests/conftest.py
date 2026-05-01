"""
Test fixtures and configuration.
"""

import os
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["OPENROUTER_API_KEY"] = "sk-or-test-key-for-testing-purposes-only-12345"
os.environ["SERVER_API_KEY"] = "test-server-api-key-12345"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://testorigin.com"
os.environ["RATE_LIMIT"] = "100/minute"

from main import app
import app.dependencies as deps


@pytest.fixture(autouse=True)
def setup_app_state():
    """Initialize app_start_time so /health works without running lifespan."""
    deps.app_start_time = datetime.now()
    yield


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    return "test-server-api-key-12345"


@pytest.fixture
def invalid_api_key():
    return "invalid-api-key"


@pytest.fixture
def mock_openrouter(monkeypatch):
    """Stub out app.openrouter_client.send_chat_completion with a canned response.

    Returns the captured-kwargs dict so tests can assert on outgoing payload.
    """
    captured: dict = {}

    def _stub(**kwargs):
        captured.clear()
        captured.update(kwargs)
        return {
            "id": "gen-test",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": '{"result": "test output"}'},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

    import app.openrouter_client as orc
    monkeypatch.setattr(orc, "send_chat_completion", _stub)
    return captured


@pytest.fixture
def sample_generate_request():
    """Sample valid generate request."""
    return {
        "user_prompt": "Hello, world!",
        "user_prompt_type": "text",
        "thinking_level": "high",
    }
