"""Free-tier-only Gemini API client.

Strict guarantees:
- Uses only free-tier-eligible models (pinned via GEMINI_MODEL).
- Never switches to a paid model or paid path when limits are hit.
- Raises FreeTierExhausted on 429 so callers can degrade gracefully.
- API key is read from the environment and must never ship to clients.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import Enum

import httpx

DEFAULT_MODEL = "gemini-3.8-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
FREE_TIER_MODELS = frozenset(
    {
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-4-hydrogen",
        "gemini-2.5-flash-lite",
    }
)


class GeminiError(Exception):
    """Base error for the Gemini free-tier client."""


class FreeTierExhausted(GeminiError):
    """Free-tier rate limit (HTTP 429) reached. Never auto-upgrade to paid."""


class InvalidApiKey(GeminiError):
    """API key rejected (HTTP 401/403)."""


class GeminiUnavailable(GeminiError):
    """Timeout, network failure, or unexpected server error."""


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"


@dataclass(frozen=True)
class GeminiResponse:
    text: str
    prompt_tokens: int
    output_tokens: int
    model: str
    cached: bool = False


class GeminiFreeTierClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self._model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        if self._model not in FREE_TIER_MODELS:
            raise GeminiError(
                f"Model '{self._model}' is not on the verified free-tier allowlist. "
                "Refusing to call a potentially billable model."
            )
        self._timeout = timeout_seconds
        self._transport = transport

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
    ) -> GeminiResponse:
        parts: list[dict] = [{"text": prompt}]
        return self._generate(parts, system_instruction, max_output_tokens)

    def generate_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
    ) -> GeminiResponse:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        parts: list[dict] = [
            {"inline_data": {"mime_type": mime_type, "data": encoded}},
            {"text": prompt},
        ]
        return self._generate(parts, system_instruction, max_output_tokens)

    def _generate(
        self,
        parts: list[dict],
        system_instruction: str | None,
        max_output_tokens: int,
    ) -> GeminiResponse:
        if not self._api_key:
            raise InvalidApiKey("GEMINI_API_KEY is not configured.")

        payload: dict = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{GEMINI_BASE_URL}/models/{self._model}:generateContent"
        headers = {"x-goog-api-key": self._api_key}

        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise GeminiUnavailable("Gemini request timed out.") from exc
        except httpx.HTTPError as exc:
            raise GeminiUnavailable("Gemini request failed.") from exc

        if response.status_code == 429:
            raise FreeTierExhausted("Free-tier rate limit reached.")
        if response.status_code in (401, 403):
            raise InvalidApiKey("Gemini API key rejected.")
        if response.status_code >= 500:
            raise GeminiUnavailable("Gemini server error.")
        if response.status_code != 200:
            raise GeminiUnavailable(f"Gemini returned HTTP {response.status_code}.")

        data = response.json()
        return self._parse_response(data)

    def _parse_response(self, data: dict) -> GeminiResponse:
        candidates = data.get("candidates") or []
        if not candidates:
            raise GeminiUnavailable("Gemini returned no candidates.")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if "text" in part)
        usage = data.get("usageMetadata") or {}
        return GeminiResponse(
            text=text,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
            model=self._model,
        )
