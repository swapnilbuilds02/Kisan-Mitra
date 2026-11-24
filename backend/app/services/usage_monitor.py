"""AI usage monitoring, quotas, rate limits, and emergency controls.

Tracks per-user and platform-wide AI consumption so Free Tier limits are
never exceeded into paid billing. When a limit is hit the system returns a
user-friendly Marathi message and never escalates to a paid provider.

The store is pluggable: an in-memory implementation ships by default and a
Redis-backed implementation can be swapped in without changing callers.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Protocol

IST_OFFSET_SECONDS = 5 * 3600 + 30 * 60

MESSAGE_QUOTA_EXHAUSTED = (
    "या महिन्यात अधिकवापर पूर्ण झाला आहे. कृपया पुढील महिन्यात पुन्हा प्रयत्न करा "
    "किंवा प्रो प्लॅनसाठी WhatsApp वर चौकशी करा."
)
MESSAGE_RATE_LIMITED = (
    "सध्या अनेक विनंती प्रक्रिया केल्या जात आहेत. कृपया काही क्षणांनंतर पुन्हा प्रयत्न करा."
)
MESSAGE_AI_DISABLED = (
    "आत्ता AI सेवा काही काळासाठी बंद आहे. इतर सुविधा वापरणे चालू राहील."
)
MESSAGE_FREE_TIER_EXHAUSTED = (
    "आजचा AI वापर मर्यादा पूर्ण झाला आहे. कृपया उद्या पुन्हा प्रयत्न करा. "
    "आपल्या इतर माहितीसाठी कृषी मित्र ॲप वापरत राहा."
)
MESSAGE_DAILY_USER_LIMIT = (
    "आज आपली AI वापर मर्यादा पूर्ण झाली आहे. कृपया उद्या पुन्हा प्रयत्न करा."
)


class UsageStore(Protocol):
    def incr(self, key: str, window: float) -> int: ...
    def get(self, key: str) -> int: ...
    def snapshot_keys(self, prefix: str) -> dict[str, int]: ...


class InMemoryUsageStore:
    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def incr(self, key: str, window: float) -> int:
        now = time.monotonic()
        with self._lock:
            count, expires = self._counters.get(key, (0, 0.0))
            if now > expires:
                count, expires = 0, now + window
            count += 1
            self._counters[key] = (count, expires)
            return count

    def get(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            count, expires = self._counters.get(key, (0, 0.0))
            return count if now <= expires else 0

    def snapshot_keys(self, prefix: str) -> dict[str, int]:
        now = time.monotonic()
        with self._lock:
            return {
                key: count
                for key, (count, expires) in self._counters.items()
                if key.startswith(prefix) and now <= expires
            }


@dataclass(frozen=True)
class UsageLimits:
    max_requests_per_day: int = int(os.environ.get("AI_MAX_REQUESTS_PER_DAY", "5000"))
    max_requests_per_user_per_day: int = int(
        os.environ.get("AI_MAX_REQUESTS_PER_USER_PER_DAY", "50")
    )
    max_requests_per_user_per_minute: int = int(
        os.environ.get("AI_MAX_REQUESTS_PER_USER_PER_MINUTE", "6")
    )
    max_image_bytes: int = int(os.environ.get("AI_MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
    max_audio_seconds: int = int(os.environ.get("AI_MAX_AUDIO_SECONDS", "60"))


@dataclass
class UsageStats:
    total_requests: int = 0
    image_requests: int = 0
    voice_requests: int = 0
    text_requests: int = 0
    kb_served: int = 0
    gemini_calls: int = 0
    failed_requests: int = 0
    rate_limit_errors: int = 0
    estimated_paid_cost_usd: float = 0.0
    estimated_savings_usd: float = 0.0
    per_provider: dict[str, int] = field(default_factory=dict)


class UsageMonitor:
    def __init__(
        self,
        store: UsageStore | None = None,
        limits: UsageLimits | None = None,
        ai_enabled: bool | None = None,
    ) -> None:
        self._store = store if store is not None else InMemoryUsageStore()
        self._limits = limits if limits is not None else UsageLimits()
        if ai_enabled is None:
            env_flag = os.environ.get("AI_ENABLED", "true").strip().lower()
            ai_enabled = env_flag not in ("false", "0", "off", "no")
        self._ai_enabled = ai_enabled
        self._lock = threading.Lock()
        self._stats = UsageStats()
        self._daily_reset_key: str | None = None

    @property
    def limits(self) -> UsageLimits:
        return self._limits

    @property
    def ai_enabled(self) -> bool:
        return self._ai_enabled

    def set_ai_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._ai_enabled = enabled

    @staticmethod
    def _ist_today() -> str:
        ist = datetime.now(timezone.utc).timestamp() + IST_OFFSET_SECONDS
        return date.fromtimestamp(ist).isoformat()

    def _day_key(self, scope: str) -> str:
        return f"ai:day:{self._ist_today()}:{scope}"

    def check_allowed(self, user_id: str) -> str | None:
        """Return a Marathi block message, or None when the request may proceed."""
        if not self._ai_enabled:
            return MESSAGE_AI_DISABLED

        day_total = self._store.get(self._day_key("platform"))
        if day_total >= self._limits.max_requests_per_day:
            return MESSAGE_FREE_TIER_EXHAUSTED

        user_day_key = self._day_key(f"user:{user_id}")
        if self._store.get(user_day_key) >= self._limits.max_requests_per_user_per_day:
            return MESSAGE_DAILY_USER_LIMIT

        minute_count = self._store.incr(
            f"ai:minute:{user_id}:{int(time.time() // 60)}", 60.0
        )
        if minute_count > self._limits.max_requests_per_user_per_minute:
            return MESSAGE_RATE_LIMITED
        return None

    def record_request(
        self,
        user_id: str,
        request_type: str,
        provider: str,
        *,
        failed: bool = False,
        rate_limited: bool = False,
        prompt_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        with self._lock:
            self._stats.total_requests += 1
            if request_type == "image":
                self._stats.image_requests += 1
            elif request_type == "voice":
                self._stats.voice_requests += 1
            else:
                self._stats.text_requests += 1
            if provider == "kb":
                self._stats.kb_served += 1
            elif provider.startswith("gemini"):
                self._stats.gemini_calls += 1
            if failed:
                self._stats.failed_requests += 1
            if rate_limited:
                self._stats.rate_limit_errors += 1
            self._stats.per_provider[provider] = self._stats.per_provider.get(provider, 0) + 1
            if provider.startswith("gemini"):
                self._stats.estimated_paid_cost_usd += 0.0
                self._stats.estimated_savings_usd += _estimate_savings(
                    prompt_tokens, output_tokens
                )

        self._store.incr(self._day_key("platform"), 86400.0)
        self._store.incr(self._day_key(f"user:{user_id}"), 86400.0)

    def stats(self) -> UsageStats:
        with self._lock:
            return UsageStats(
                total_requests=self._stats.total_requests,
                image_requests=self._stats.image_requests,
                voice_requests=self._stats.voice_requests,
                text_requests=self._stats.text_requests,
                kb_served=self._stats.kb_served,
                gemini_calls=self._stats.gemini_calls,
                failed_requests=self._stats.failed_requests,
                rate_limit_errors=self._stats.rate_limit_errors,
                estimated_paid_cost_usd=self._stats.estimated_paid_cost_usd,
                estimated_savings_usd=self._stats.estimated_savings_usd,
                per_provider=dict(self._stats.per_provider),
            )


def _estimate_savings(prompt_tokens: int, output_tokens: int) -> float:
    """Savings vs. a hypothetical paid Flash-tier baseline (USD)."""
    input_rate = 0.75 / 1_000_000
    output_rate = 3.75 / 1_000_000
    return prompt_tokens * input_rate + output_tokens * output_rate
