import json

import httpx
import pytest

from app.services.gemini_client import (
    FREE_TIER_MODELS,
    GeminiError,
    GeminiFreeTierClient,
    FreeTierExhausted,
    InvalidApiKey,
    GeminiUnavailable,
)


def make_client(handler, model="gemini-3.8-flash", api_key="test-key"):
    transport = httpx.MockTransport(handler)
    return GeminiFreeTierClient(
        api_key=api_key, model=model, transport=transport
    )


def success_handler(request: httpx.Request) -> httpx.Response:
    body = {
        "candidates": [
            {"content": {"parts": [{"text": "नमस्कार"}]}},
        ],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
    }
    return httpx.Response(200, json=body)


class TestFreeTierGuardrails:
    def test_rejects_non_allowlisted_model(self):
        with pytest.raises(GeminiError, match="free-tier allowlist"):
            GeminiFreeTierClient(api_key="k", model="gemini-4-carbon")

    def test_default_model_is_free_tier(self):
        client = GeminiFreeTierClient(api_key="k")
        assert client.model in FREE_TIER_MODELS

    def test_missing_key_is_not_configured(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        client = GeminiFreeTierClient(api_key="")
        assert client.is_configured is False

    def test_429_raises_free_tier_exhausted_not_paid_fallback(self):
        def handler(request):
            return httpx.Response(429, json={"error": {"code": 429}})

        client = make_client(handler)
        with pytest.raises(FreeTierExhausted):
            client.generate_text("प्रश्न")

    def test_401_raises_invalid_api_key(self):
        def handler(request):
            return httpx.Response(401, json={})

        client = make_client(handler)
        with pytest.raises(InvalidApiKey):
            client.generate_text("प्रश्न")

    def test_500_raises_unavailable(self):
        def handler(request):
            return httpx.Response(500, json={})

        client = make_client(handler)
        with pytest.raises(GeminiUnavailable):
            client.generate_text("प्रश्न")

    def test_no_key_raises_invalid_api_key(self):
        client = GeminiFreeTierClient(api_key="")
        with pytest.raises(InvalidApiKey):
            client.generate_text("प्रश्न")


class TestGeneration:
    def test_successful_text_response(self):
        client = make_client(success_handler)
        result = client.generate_text("द्राक्षातील भुरी")
        assert result.text == "नमस्कार"
        assert result.prompt_tokens == 10
        assert result.output_tokens == 5
        assert result.model == "gemini-3.8-flash"

    def test_vision_request_sends_inline_image(self):
        seen = {}

        def handler(request):
            seen["body"] = json.loads(request.content)
            return success_handler(request)

        client = make_client(handler)
        client.generate_vision(b"\xff\xd8\xff\xdatabytes", "image/jpeg", "ओळखा")

        parts = seen["body"]["contents"][0]["parts"]
        assert parts[0]["inline_data"]["mime_type"] == "image/jpeg"
        assert "data" in parts[0]["inline_data"]
        assert parts[1]["text"] == "ओळखा"

    def test_system_instruction_included(self):
        seen = {}

        def handler(request):
            seen["body"] = json.loads(request.content)
            return success_handler(request)

        client = make_client(handler)
        client.generate_text("q", system_instruction="नियम")
        assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "नियम"

    def test_no_candidates_raises_unavailable(self):
        def handler(request):
            return httpx.Response(200, json={"candidates": []})

        client = make_client(handler)
        with pytest.raises(GeminiUnavailable):
            client.generate_text("q")

    def test_timeout_raises_unavailable(self):
        def handler(request):
            raise httpx.ConnectTimeout("boom")

        client = make_client(handler)
        with pytest.raises(GeminiUnavailable):
            client.generate_text("q")
