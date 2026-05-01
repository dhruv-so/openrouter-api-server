"""
API endpoint tests.
"""

import json

import pytest


class TestHealthEndpoint:
    """Health check endpoint."""

    def test_health_check_success(self, client):
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "model" in data
        assert "version" in data

    def test_health_check_no_auth_required(self, client):
        response = client.get("/health")
        assert response.status_code == 200


class TestGenerateEndpoint:
    """Generate endpoint."""

    def test_generate_requires_auth(self, client, sample_generate_request):
        response = client.post("/generate", json=sample_generate_request)
        assert response.status_code == 403

    def test_generate_with_valid_request(self, client, sample_generate_request, valid_api_key, mock_openrouter):
        response = client.post(
            "/generate",
            json=sample_generate_request,
            headers={"X-API-Key": valid_api_key},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["input_tokens"] == 10
        assert body["output_tokens"] == 20
        assert body["total_tokens"] == 30

    def test_generate_with_missing_prompt(self, client, valid_api_key):
        response = client.post(
            "/generate",
            json={},
            headers={"X-API-Key": valid_api_key},
        )
        assert response.status_code == 422

    def test_generate_with_system_prompt(self, client, valid_api_key, mock_openrouter):
        request_data = {
            "user_prompt": "Hello",
            "system_prompt": "You are a helpful assistant",
            "system_prompt_type": "text",
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key},
        )
        assert response.status_code == 200
        # System prompt should be the first message in the outgoing payload
        messages = mock_openrouter["messages"]
        assert messages[0] == {"role": "system", "content": "You are a helpful assistant"}
        assert messages[1]["role"] == "user"

    def test_generate_with_json_schema_returns_dict(self, client, valid_api_key, mock_openrouter):
        request_data = {
            "user_prompt": "Generate a person",
            "json_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name", "age"],
            },
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key},
        )
        assert response.status_code == 200
        body = response.json()
        # Stub content is `{"result":"test output"}`; with schema set, route json.loads it.
        assert isinstance(body["output"], dict)
        # Outgoing response_format should wrap the schema
        rf = mock_openrouter["response_format"]
        assert rf["type"] == "json_schema"
        assert rf["json_schema"]["strict"] is True
        assert rf["json_schema"]["schema"]["required"] == ["name", "age"]

    def test_generate_returns_string_when_no_schema_and_content_not_json(
        self, client, valid_api_key, monkeypatch
    ):
        """Plain-text upstream content should pass through as a string when no schema."""
        def _stub(**kwargs):
            return {
                "choices": [{"message": {"content": "Hello there!"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
        import app.openrouter_client as orc
        monkeypatch.setattr(orc, "send_chat_completion", _stub)

        response = client.post(
            "/generate",
            json={"user_prompt": "say hi"},
            headers={"X-API-Key": "test-server-api-key-12345"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["output"] == "Hello there!"

    def test_generate_with_model_selection(self, client, valid_api_key, mock_openrouter):
        for model in ["gemini-3-pro-preview", "gemini-3-flash-preview"]:
            response = client.post(
                "/generate",
                json={"user_prompt": "Hello", "model": model},
                headers={"X-API-Key": valid_api_key},
            )
            assert response.status_code == 200

    def test_model_slug_remapped_to_openrouter_namespace(self, client, valid_api_key, mock_openrouter):
        client.post(
            "/generate",
            json={"user_prompt": "hi", "model": "gemini-3-flash-preview"},
            headers={"X-API-Key": valid_api_key},
        )
        assert mock_openrouter["model"] == "google/gemini-3-flash-preview"

    def test_thinking_level_uppercase_normalized_to_lowercase_effort(
        self, client, valid_api_key, mock_openrouter
    ):
        client.post(
            "/generate",
            json={"user_prompt": "hi", "thinking_level": "HIGH"},
            headers={"X-API-Key": valid_api_key},
        )
        assert mock_openrouter["reasoning"] == {"effort": "high"}

    def test_thinking_level_medium_for_flash_passes_through(
        self, client, valid_api_key, mock_openrouter
    ):
        client.post(
            "/generate",
            json={
                "user_prompt": "hi",
                "model": "gemini-3-flash-preview",
                "thinking_level": "medium",
            },
            headers={"X-API-Key": valid_api_key},
        )
        assert mock_openrouter["reasoning"] == {"effort": "medium"}

    def test_thinking_level_minimal_for_pro_logs_warning_but_passes_through(
        self, client, valid_api_key, mock_openrouter, caplog
    ):
        """Pro doesn't support 'minimal'; server forwards anyway (OpenRouter remaps)."""
        with caplog.at_level("WARNING"):
            client.post(
                "/generate",
                json={
                    "user_prompt": "hi",
                    "model": "gemini-3-pro-preview",
                    "thinking_level": "minimal",
                },
                headers={"X-API-Key": valid_api_key},
            )
        assert mock_openrouter["reasoning"] == {"effort": "minimal"}
        assert any("not officially supported" in rec.message for rec in caplog.records)

    def test_pro_public_alias_remaps_to_3_1_pro_slug(self, client, valid_api_key, mock_openrouter):
        """Public 'gemini-3-pro-preview' is an alias that routes to 3.1 Pro upstream."""
        client.post(
            "/generate",
            json={"user_prompt": "hi", "model": "gemini-3-pro-preview"},
            headers={"X-API-Key": valid_api_key},
        )
        assert mock_openrouter["model"] == "google/gemini-3.1-pro-preview"

    def test_flash_lite_31_slug_passthrough(self, client, valid_api_key, mock_openrouter):
        client.post(
            "/generate",
            json={"user_prompt": "hi", "model": "gemini-3.1-flash-lite-preview"},
            headers={"X-API-Key": valid_api_key},
        )
        assert mock_openrouter["model"] == "google/gemini-3.1-flash-lite-preview"


class TestImagePayloadAssembly:
    """Verify outgoing message shape when images are supplied."""

    def test_image_payload_assembled_as_data_uri_with_detail_high(
        self, client, valid_api_key, mock_openrouter, monkeypatch
    ):
        # Patch the SSRF-checked image loader so we don't fetch remotely.
        def _fake_load(url):
            return b"\x89PNG\r\n\x1a\nfake-bytes", "image/png"

        import app.routes.generate as gen_route
        monkeypatch.setattr(gen_route, "load_image_from_url", _fake_load)

        client.post(
            "/generate",
            json={
                "user_prompt": "describe",
                "image_urls": ["https://example.com/x.png"],
            },
            headers={"X-API-Key": valid_api_key},
        )

        messages = mock_openrouter["messages"]
        # System absent → user is messages[0]
        user_msg = messages[0]
        assert user_msg["role"] == "user"
        content = user_msg["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["detail"] == "high"
        assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
        assert content[-1] == {"type": "text", "text": "describe"}


class TestErrorHandling:
    """Error handling."""

    def test_404_for_unknown_endpoint(self, client):
        response = client.get("/unknown")
        assert response.status_code == 404

    def test_405_for_wrong_method(self, client):
        response = client.get("/generate")
        assert response.status_code == 405

    def test_error_messages_dont_expose_internals(self, client, valid_api_key):
        request_data = {
            "user_prompt": "http://invalid-url-that-will-fail",
            "user_prompt_type": "file",
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key},
        )

        if response.status_code >= 400:
            error_detail = response.json().get("detail", "")
            assert "Traceback" not in error_detail
            assert 'File "' not in error_detail
            assert "/app/" not in error_detail


class TestTokenExtraction:
    """Unit tests for the generalized token extraction helper."""

    def test_handles_openai_dict_keys(self):
        from app.utils.tokens import extract_token_counts
        usage = {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33}
        assert extract_token_counts(usage) == (11, 22, 33)

    def test_handles_legacy_attribute_object(self):
        from app.utils.tokens import extract_token_counts

        class U:
            prompt_token_count = 7
            candidates_token_count = 8
            total_token_count = 15

        assert extract_token_counts(U()) == (7, 8, 15)

    def test_handles_none(self):
        from app.utils.tokens import extract_token_counts
        assert extract_token_counts(None) == (0, 0, 0)
