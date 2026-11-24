"""Centralized AI request router.

Routing priority (configurable, defaults below):
1. Knowledge Base   – answer directly when verified content matches.
2. Free Gemini      – only when visual/language analysis is genuinely needed.
3. Consultant escalation – for uncertain or serious agricultural cases.
4. Graceful failure – Marathi user message; never an automatic paid API call.

Flow: validate → KB search → decide → quota check → minimal external call →
guardrail validation → telemetry → response.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol

from .gemini_client import (
    GeminiFreeTierClient,
    GeminiError,
    GeminiResponse,
    FreeTierExhausted,
)
from .usage_monitor import UsageMonitor

KB_SIMILARITY_THRESHOLD = 0.78
IMAGE_PROMPT = (
    "तुम्ही एक द्राक्ष शेती तज्ज्ञ आहात. दिलेल्या पानाच्या/मोज्याच्या छवीवरून "
    "दिसणारे रोग, किडी, पोषण दोष किंवा इतर समस्या ओळखा. "
    "खालील नियम पाळा:\n"
    "1. फक्त छवीतून दिसणारे प्रमाण म्हणून सांगा; प्रमाणित व शंका अशी वेगळी करा.\n"
    "2. कोणत्याही औषधाचे नाव, प्रमाण किंवा फवारणीचे अनुपात स्वतः तयार करू नका.\n"
    "3. अपुरी माहिती असल्यास पुढील प्रश्न विचारा.\n"
    "4. गंभीर किंवा अनिश्चित अवस्था असल्यास सल्लागारांकडे पाठवण्याचा सूचना द्या.\n"
    "5. मराठीत उत्तर द्या."
)
TEXT_SYSTEM_PROMPT = (
    "तुम्ही किसान मित्र शेती सल्लागार आहात. फक्त दिलेल्या माहितीवर आधारित उत्तर द्या. "
    "रसायनांची नावे, प्रमाण किंवा फवारणी अनुपात स्वतः तयार करू नका. "
    "माहिती नसल्यास स्पष्टपणे सांगा. उत्तर मराठीत द्या."
)


class RequestType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "voice"


class RouteSource(str, Enum):
    KB = "kb"
    GEMINI_FREE = "gemini_free"
    CONSULTANT_ESCALATION = "consultant_escalation"
    QUOTA_BLOCKED = "quota_blocked"
    RATE_LIMITED = "rate_limited"
    AI_DISABLED = "ai_disabled"
    FREE_TIER_EXHAUSTED = "free_tier_exhausted"
    NO_KB_MATCH = "no_kb_match"
    INVALID_REQUEST = "invalid_request"
    ERROR = "error"


@dataclass(frozen=True)
class KBHit:
    answer: str
    confidence: float
    source: str = "kb"


@dataclass(frozen=True)
class RouteResult:
    source: RouteSource
    answer: str
    confidence: float | None = None
    escalate_to_consultant: bool = False
    request_id: str | None = None
    prompt_tokens: int = 0
    output_tokens: int = 0
    metadata: dict = field(default_factory=dict)


class KnowledgeBase(Protocol):
    def search(self, query: str) -> KBHit | None: ...


class VisionCache(Protocol):
    def get(self, content_hash: str) -> RouteResult | None: ...
    def set(self, content_hash: str, result: RouteResult) -> None: ...


class InMemoryVisionCache:
    def __init__(self, max_entries: int = 512) -> None:
        self._max = max_entries
        self._data: dict[str, RouteResult] = {}

    def get(self, content_hash: str) -> RouteResult | None:
        return self._data.get(content_hash)

    def set(self, content_hash: str, result: RouteResult) -> None:
        if len(self._data) >= self._max:
            oldest = next(iter(self._data))
            del self._data[oldest]
        self._data[content_hash] = result


class AIRouter:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        gemini: GeminiFreeTierClient | None = None,
        usage_monitor: UsageMonitor | None = None,
        vision_cache: VisionCache | None = None,
        kb_threshold: float | None = None,
        provider_priority: list[str] | None = None,
    ) -> None:
        self._kb = knowledge_base
        self._gemini = gemini
        self._usage = usage_monitor if usage_monitor is not None else UsageMonitor()
        self._vision_cache = vision_cache if vision_cache is not None else InMemoryVisionCache()
        env_threshold = os.environ.get("AI_KB_THRESHOLD")
        if kb_threshold is not None:
            self._kb_threshold = kb_threshold
        elif env_threshold:
            self._kb_threshold = float(env_threshold)
        else:
            self._kb_threshold = KB_SIMILARITY_THRESHOLD
        priority = provider_priority or os.environ.get(
            "AI_PROVIDER_PRIORITY", "kb,gemini_free,consultant"
        ).split(",")
        self._priority = [p.strip() for p in priority if p.strip()]

    @property
    def usage_monitor(self) -> UsageMonitor:
        return self._usage

    def route_text(self, user_id: str, query: str) -> RouteResult:
        query = (query or "").strip()
        if not query:
            return RouteResult(
                source=RouteSource.INVALID_REQUEST,
                answer="कृपया प्रश्न लिहा किंवा बोला.",
            )
        if len(query) > 2000:
            return RouteResult(
                source=RouteSource.INVALID_REQUEST,
                answer="प्रश्न खूप मोठा आहे. कृपया थोडक्यात विचारा.",
            )

        blocked = self._usage.check_allowed(user_id)
        if blocked is not None:
            return self._blocked_result(blocked)

        kb_hit = self._kb.search(query)
        if kb_hit is not None and kb_hit.confidence >= self._kb_threshold:
            self._usage.record_request(user_id, "text", "kb")
            return RouteResult(
                source=RouteSource.KB,
                answer=kb_hit.answer,
                confidence=kb_hit.confidence,
            )

        if "kb" not in self._priority or "gemini_free" not in self._priority:
            return self._no_match(user_id, kb_hit)

        return self._call_gemini_text(user_id, query, kb_hit)

    def route_image(
        self,
        user_id: str,
        processed_image,
        user_description: str = "",
    ) -> RouteResult:
        if processed_image is None:
            return RouteResult(
                source=RouteSource.INVALID_REQUEST,
                answer="छवी प्रक्रिया करता आली नाही. कृपया वेगळी छवी निवडा.",
            )

        cached = self._vision_cache.get(processed_image.content_hash)
        if cached is not None:
            return cached

        blocked = self._usage.check_allowed(user_id)
        if blocked is not None:
            return self._blocked_result(blocked)

        if user_description:
            kb_hit = self._kb.search(user_description)
            if kb_hit is not None and kb_hit.confidence >= self._kb_threshold:
                result = RouteResult(
                    source=RouteSource.KB,
                    answer=kb_hit.answer,
                    confidence=kb_hit.confidence,
                    metadata={"image_cached": True},
                )
                self._usage.record_request(user_id, "image", "kb")
                self._vision_cache.set(processed_image.content_hash, result)
                return result

        if self._gemini is None or not self._gemini.is_configured:
            return self._escalate(
                user_id,
                "छवीवरील माहिती आत्ता उपलब्ध नाही. कृपया तज्ज्ञांशी संपर्क साधा.",
            )

        try:
            response = self._gemini.generate_vision(
                image_bytes=processed_image.data,
                mime_type=processed_image.mime_type,
                prompt=IMAGE_PROMPT,
                system_instruction=TEXT_SYSTEM_PROMPT,
            )
        except FreeTierExhausted:
            self._usage.record_request(
                user_id, "image", "gemini_free", rate_limited=True
            )
            return RouteResult(
                source=RouteSource.FREE_TIER_EXHAUSTED,
                answer=_free_tier_message(),
            )
        except GeminiError:
            self._usage.record_request(
                user_id, "image", "gemini_free", failed=True
            )
            return self._escalate(
                user_id,
                "छवी विश्लेषण असफल झाले. कृपया पुन्हा प्रयत्न करा किंवा सल्लागारांशी संपर्क साधा.",
            )

        result = self._guardrail(
            response,
            user_id=user_id,
            request_type="image",
            fallback=RouteSource.GEMINI_FREE,
        )
        self._vision_cache.set(processed_image.content_hash, result)
        return result

    def route_audio(self, user_id: str, transcript: str) -> RouteResult:
        if not (transcript or "").strip():
            return RouteResult(
                source=RouteSource.INVALID_REQUEST,
                answer="आवाज ओळखला नाही. कृपया पुन्हा बोला किंवा लिहून विचारा.",
            )
        return self.route_text(user_id, transcript)

    def _call_gemini_text(
        self, user_id: str, query: str, kb_hit: KBHit | None
    ) -> RouteResult:
        if self._gemini is None or not self._gemini.is_configured:
            return self._no_match(user_id, kb_hit)
        try:
            response = self._gemini.generate_text(
                prompt=query,
                system_instruction=TEXT_SYSTEM_PROMPT,
            )
        except FreeTierExhausted:
            self._usage.record_request(
                user_id, "text", "gemini_free", rate_limited=True
            )
            return RouteResult(
                source=RouteSource.FREE_TIER_EXHAUSTED,
                answer=_free_tier_message(),
            )
        except GeminiError:
            self._usage.record_request(user_id, "text", "gemini_free", failed=True)
            return self._no_match(user_id, kb_hit)

        return self._guardrail(
            response,
            user_id=user_id,
            request_type="text",
            fallback=RouteSource.GEMINI_FREE,
        )

    def _guardrail(
        self,
        response: GeminiResponse,
        *,
        user_id: str,
        request_type: str,
        fallback: RouteSource,
    ) -> RouteResult:
        answer = (response.text or "").strip()
        if not answer:
            self._usage.record_request(
                user_id, request_type, "gemini_free", failed=True
            )
            return self._escalate(
                user_id, "सध्या योग्य उत्तर मिळू शकले नाही. सल्लागारांशी संपर्क साधा."
            )

        self._usage.record_request(
            user_id,
            request_type,
            "gemini_free",
            prompt_tokens=response.prompt_tokens,
            output_tokens=response.output_tokens,
        )
        escalate = bool(
            re.search(
                r"सल्लागारांशी संपर्क|सल्लागारांकडे|consultant",
                answer,
                re.IGNORECASE,
            )
        )
        return RouteResult(
            source=fallback,
            answer=answer,
            confidence=None,
            escalate_to_consultant=escalate,
            prompt_tokens=response.prompt_tokens,
            output_tokens=response.output_tokens,
            metadata={"model": response.model, "guarded": True},
        )

    def _no_match(self, user_id: str, kb_hit: KBHit | None) -> RouteResult:
        self._usage.record_request(user_id, "text", "kb")
        return RouteResult(
            source=RouteSource.NO_KB_MATCH,
            answer=(
                "या प्रश्नाबाबत अधिकृत माहिती उपलब्ध नाही. सविस्तर माहितीसाठी "
                "प्रो प्लॅन अपग्रेड करा किंवा तज्ज्ञांशी संपर्क साधा."
            ),
            confidence=kb_hit.confidence if kb_hit else None,
        )

    def _escalate(self, user_id: str, answer: str) -> RouteResult:
        self._usage.record_request(user_id, "text", "escalation", failed=True)
        return RouteResult(
            source=RouteSource.CONSULTANT_ESCALATION,
            answer=answer,
            escalate_to_consultant=True,
        )

    def _blocked_result(self, message: str) -> RouteResult:
        if message == _ai_disabled_message():
            return RouteResult(source=RouteSource.AI_DISABLED, answer=message)
        if message == _rate_limited_message():
            return RouteResult(source=RouteSource.RATE_LIMITED, answer=message)
        return RouteResult(source=RouteSource.QUOTA_BLOCKED, answer=message)


def _free_tier_message() -> str:
    from .usage_monitor import MESSAGE_FREE_TIER_EXHAUSTED

    return MESSAGE_FREE_TIER_EXHAUSTED


def _ai_disabled_message() -> str:
    from .usage_monitor import MESSAGE_AI_DISABLED

    return MESSAGE_AI_DISABLED


def _rate_limited_message() -> str:
    from .usage_monitor import MESSAGE_RATE_LIMITED

    return MESSAGE_RATE_LIMITED


def stable_request_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
