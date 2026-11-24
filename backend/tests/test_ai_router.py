import io

import pytest
from PIL import Image

from app.services.ai_router import (
    AIRouter,
    InMemoryVisionCache,
    KBHit,
    RouteSource,
)
from app.services.gemini_client import (
    GeminiFreeTierClient,
    GeminiError,
    FreeTierExhausted,
    GeminiResponse,
)
from app.services.image_pipeline import process_image
from app.services.usage_monitor import (
    MESSAGE_AI_DISABLED,
    MESSAGE_FREE_TIER_EXHAUSTED,
    MESSAGE_RATE_LIMITED,
    InMemoryUsageStore,
    UsageLimits,
    UsageMonitor,
)


class FakeKB:
    def __init__(self, hits: dict[str, KBHit] | None = None):
        self.hits = hits or {}
        self.calls: list[str] = []

    def search(self, query: str) -> KBHit | None:
        self.calls.append(query)
        return self.hits.get(query)


class FakeGemini:
    def __init__(self, response=None, error: Exception | None = None, configured=True):
        self._response = response or GeminiResponse(
            text="छवीमध्ये डाऊनी मिल्ड्यू दिसतो.",
            prompt_tokens=100,
            output_tokens=50,
            model="gemini-3.8-flash",
        )
        self._error = error
        self._configured = configured
        self.text_calls: list[str] = []
        self.vision_calls: list[bytes] = []

    @property
    def is_configured(self) -> bool:
        return self._configured

    def generate_text(self, prompt, system_instruction=None, max_output_tokens=1024):
        self.text_calls.append(prompt)
        if self._error:
            raise self._error
        return self._response

    def generate_vision(self, image_bytes, mime_type, prompt, system_instruction=None, max_output_tokens=1024):
        self.vision_calls.append(image_bytes)
        if self._error:
            raise self._error
        return self._response


def make_image():
    buf = io.BytesIO()
    Image.new("RGB", (400, 400), (60, 120, 40)).save(buf, format="JPEG")
    return process_image(buf.getvalue())


def make_router(
    kb=None,
    gemini=None,
    limits=None,
    ai_enabled=True,
    cache=None,
    threshold=None,
) -> AIRouter:
    monitor = UsageMonitor(
        store=InMemoryUsageStore(),
        limits=limits
        or UsageLimits(
            max_requests_per_day=1000,
            max_requests_per_user_per_day=50,
            max_requests_per_user_per_minute=100,
            max_image_bytes=5 * 1024 * 1024,
            max_audio_seconds=60,
        ),
        ai_enabled=ai_enabled,
    )
    return AIRouter(
        knowledge_base=kb or FakeKB(),
        gemini=gemini,
        usage_monitor=monitor,
        vision_cache=cache or InMemoryVisionCache(),
        kb_threshold=threshold,
    )


class TestTextRouting:
    def test_kb_hit_skips_gemini_entirely(self):
        kb = FakeKB({"भुरी काय करावे?": KBHit(answer="नियंत्रण मार्गदर्शन", confidence=0.92)})
        gemini = FakeGemini()
        router = make_router(kb=kb, gemini=gemini)

        result = router.route_text("u1", "भुरी काय करावे?")

        assert result.source == RouteSource.KB
        assert result.answer == "नियंत्रण मार्गदर्शन"
        assert gemini.text_calls == []

    def test_low_confidence_kb_falls_through_to_free_gemini(self):
        kb = FakeKB({"q": KBHit(answer="अपुरी", confidence=0.40)})
        gemini = FakeGemini()
        router = make_router(kb=kb, gemini=gemini)

        result = router.route_text("u1", "q")

        assert result.source == RouteSource.GEMINI_FREE
        assert gemini.text_calls == ["q"]
        assert result.metadata.get("guarded") is True

    def test_no_gemini_configured_returns_polite_no_match(self):
        kb = FakeKB({"q": KBHit(answer="x", confidence=0.2)})
        router = make_router(kb=kb, gemini=None)

        result = router.route_text("u1", "q")

        assert result.source == RouteSource.NO_KB_MATCH
        assert "प्रो प्लॅन" in result.answer

    def test_free_tier_429_returns_marathi_message_not_paid(self):
        gemini = FakeGemini(error=FreeTierExhausted())
        router = make_router(kb=FakeKB({"q": None}), gemini=gemini)

        result = router.route_text("u1", "q")

        assert result.source == RouteSource.FREE_TIER_EXHAUSTED
        assert result.answer == MESSAGE_FREE_TIER_EXHAUSTED

    def test_gemini_error_degrades_to_no_match(self):
        gemini = FakeGemini(error=GeminiError("boom"))
        router = make_router(kb=FakeKB({"q": None}), gemini=gemini)

        result = router.route_text("u1", "q")
        assert result.source == RouteSource.NO_KB_MATCH

    def test_empty_query_rejected(self):
        router = make_router()
        assert router.route_text("u1", "   ").source == RouteSource.INVALID_REQUEST

    def test_oversized_query_rejected(self):
        router = make_router()
        result = router.route_text("u1", "क" * 2001)
        assert result.source == RouteSource.INVALID_REQUEST

    def test_quota_blocked_before_any_ai_call(self):
        gemini = FakeGemini()
        monitor = UsageMonitor(
            store=InMemoryUsageStore(),
            limits=UsageLimits(
                max_requests_per_day=1000,
                max_requests_per_user_per_day=0,
                max_requests_per_user_per_minute=100,
                max_image_bytes=1,
                max_audio_seconds=1,
            ),
            ai_enabled=True,
        )
        router = AIRouter(
            knowledge_base=FakeKB({"q": None}),
            gemini=gemini,
            usage_monitor=monitor,
        )
        result = router.route_text("u1", "q")
        assert result.source == RouteSource.QUOTA_BLOCKED
        assert gemini.text_calls == []

    def test_ai_disabled_short_circuits(self):
        gemini = FakeGemini()
        router = make_router(gemini=gemini, ai_enabled=False)
        result = router.route_text("u1", "प्रश्न")
        assert result.source == RouteSource.AI_DISABLED
        assert result.answer == MESSAGE_AI_DISABLED
        assert gemini.text_calls == []

    def test_rate_limit_returns_marathi_message(self):
        limits = UsageLimits(
            max_requests_per_day=1000,
            max_requests_per_user_per_day=100,
            max_requests_per_user_per_minute=1,
            max_image_bytes=1,
            max_audio_seconds=1,
        )
        gemini = FakeGemini()
        router = make_router(kb=FakeKB(), gemini=gemini, limits=limits)
        router.route_text("u1", "a")
        result = router.route_text("u1", "b")
        assert result.source == RouteSource.RATE_LIMITED
        assert result.answer == MESSAGE_RATE_LIMITED
        assert len(gemini.text_calls) == 1


class TestImageRouting:
    def test_kb_description_hit_avoids_vision_call(self):
        kb = FakeKB({"माझ्या बागेत पाने पडत आहेत": KBHit(answer="कवकनाशक मार्ग", confidence=0.95)})
        gemini = FakeGemini()
        router = make_router(kb=kb, gemini=gemini)
        image = make_image()

        result = router.route_image(
            "u1", image, user_description="माझ्या बागेत पाने पडत आहेत"
        )

        assert result.source == RouteSource.KB
        assert gemini.vision_calls == []

    def test_vision_called_when_kb_insufficient(self):
        gemini = FakeGemini()
        router = make_router(kb=FakeKB(), gemini=gemini)
        image = make_image()

        result = router.route_image("u1", image)

        assert result.source == RouteSource.GEMINI_FREE
        assert len(gemini.vision_calls) == 1

    def test_identical_image_served_from_cache(self):
        gemini = FakeGemini()
        router = make_router(kb=FakeKB(), gemini=gemini)
        image = make_image()

        first = router.route_image("u1", image)
        second = router.route_image("u2", image)

        assert first.source == RouteSource.GEMINI_FREE
        assert second.source == RouteSource.GEMINI_FREE
        assert second.answer == first.answer
        assert len(gemini.vision_calls) == 1

    def test_vision_429_returns_free_tier_message(self):
        gemini = FakeGemini(error=FreeTierExhausted())
        router = make_router(kb=FakeKB(), gemini=gemini)
        image = make_image()

        result = router.route_image("u1", image)
        assert result.source == RouteSource.FREE_TIER_EXHAUSTED
        assert result.answer == MESSAGE_FREE_TIER_EXHAUSTED

    def test_vision_error_escalates_to_consultant(self):
        gemini = FakeGemini(error=GeminiError("fail"))
        router = make_router(kb=FakeKB(), gemini=gemini)
        image = make_image()

        result = router.route_image("u1", image)
        assert result.source == RouteSource.CONSULTANT_ESCALATION
        assert result.escalate_to_consultant is True

    def test_none_image_rejected(self):
        router = make_router()
        result = router.route_image("u1", None)
        assert result.source == RouteSource.INVALID_REQUEST

    def test_unconfigured_gemini_escalates(self):
        router = make_router(kb=FakeKB(), gemini=None)
        result = router.route_image("u1", make_image())
        assert result.source == RouteSource.CONSULTANT_ESCALATION


class TestAudioRouting:
    def test_empty_transcript_rejected(self):
        router = make_router()
        result = router.route_audio("u1", "")
        assert result.source == RouteSource.INVALID_REQUEST

    def test_transcript_routed_as_text(self):
        kb = FakeKB({"डाऊनी साठी काय?" : KBHit(answer="उत्तर", confidence=0.9)})
        router = make_router(kb=kb)
        result = router.route_audio("u1", "डाऊनी साठी काय?")
        assert result.source == RouteSource.KB


class TestNoPaidFallback:
    def test_router_never_records_paid_provider(self):
        gemini = FakeGemini()
        router = make_router(kb=FakeKB({"q": None}), gemini=gemini)
        router.route_text("u1", "q")
        router.route_image("u1", make_image())
        router.route_audio("u1", "नमस्कार")

        stats = router.usage_monitor.stats()
        for provider in stats.per_provider:
            assert provider in ("kb", "gemini_free", "escalation")
        assert stats.estimated_paid_cost_usd == 0.0

    def test_429_never_retries_with_paid_model(self):
        gemini = FakeGemini(error=FreeTierExhausted())
        router = make_router(kb=FakeKB({"q": None}), gemini=gemini)
        router.route_text("u1", "q")
        router.route_text("u2", "q")

        assert len(gemini.text_calls) == 2

        stats = router.usage_monitor.stats()
        assert stats.rate_limit_errors == 2
        for provider in stats.per_provider:
            assert provider in ("kb", "gemini_free", "escalation")
