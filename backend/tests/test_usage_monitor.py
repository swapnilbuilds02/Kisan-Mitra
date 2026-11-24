import pytest

from app.services.usage_monitor import (
    MESSAGE_AI_DISABLED,
    MESSAGE_DAILY_USER_LIMIT,
    MESSAGE_FREE_TIER_EXHAUSTED,
    MESSAGE_RATE_LIMITED,
    InMemoryUsageStore,
    UsageLimits,
    UsageMonitor,
)


def make_monitor(**limit_overrides) -> UsageMonitor:
    limits = UsageLimits(
        max_requests_per_day=limit_overrides.get("max_requests_per_day", 100),
        max_requests_per_user_per_day=limit_overrides.get(
            "max_requests_per_user_per_day", 5
        ),
        max_requests_per_user_per_minute=limit_overrides.get(
            "max_requests_per_user_per_minute", 3
        ),
        max_image_bytes=5 * 1024 * 1024,
        max_audio_seconds=60,
    )
    return UsageMonitor(store=InMemoryUsageStore(), limits=limits, ai_enabled=True)


class TestStore:
    def test_incr_and_get(self):
        store = InMemoryUsageStore()
        assert store.incr("k", 60.0) == 1
        assert store.incr("k", 60.0) == 2
        assert store.get("k") == 2

    def test_window_expiry(self):
        store = InMemoryUsageStore()
        store.incr("k", 0.0)
        import time

        time.sleep(0.01)
        assert store.get("k") == 0

    def test_snapshot_prefix(self):
        store = InMemoryUsageStore()
        store.incr("ai:day:x", 60.0)
        store.incr("other", 60.0)
        assert "ai:day:x" in store.snapshot_keys("ai:")
        assert "other" not in store.snapshot_keys("ai:")


class TestQuotas:
    def test_allows_within_limits(self):
        monitor = make_monitor()
        for _ in range(3):
            assert monitor.check_allowed("user-1") is None

    def test_per_minute_limit_blocks(self):
        monitor = make_monitor(max_requests_per_user_per_minute=3)
        for _ in range(3):
            assert monitor.check_allowed("user-1") is None
        message = monitor.check_allowed("user-1")
        assert message == MESSAGE_RATE_LIMITED

    def test_per_day_user_limit_blocks(self):
        monitor = make_monitor(
            max_requests_per_user_per_day=2, max_requests_per_user_per_minute=100
        )
        for _ in range(2):
            monitor.record_request("user-1", "text", "kb")
        message = monitor.check_allowed("user-1")
        assert message == MESSAGE_DAILY_USER_LIMIT

    def test_platform_day_limit_blocks_everyone(self):
        monitor = make_monitor(max_requests_per_day=2)
        monitor.record_request("u1", "text", "kb")
        monitor.record_request("u2", "text", "kb")
        assert monitor.check_allowed("u3") == MESSAGE_FREE_TIER_EXHAUSTED

    def test_user_limits_are_isolated(self):
        monitor = make_monitor(
            max_requests_per_user_per_day=1, max_requests_per_user_per_minute=10
        )
        monitor.record_request("user-1", "text", "kb")
        assert monitor.check_allowed("user-1") == MESSAGE_DAILY_USER_LIMIT
        assert monitor.check_allowed("user-2") is None

    def test_emergency_disable(self):
        monitor = make_monitor()
        monitor.set_ai_enabled(False)
        assert monitor.check_allowed("u1") == MESSAGE_AI_DISABLED
        monitor.set_ai_enabled(True)
        assert monitor.check_allowed("u1") is None

    def test_disabled_by_env_at_construction(self, monkeypatch):
        monkeypatch.setenv("AI_ENABLED", "false")
        monitor = UsageMonitor(limits=UsageLimits())
        assert monitor.ai_enabled is False
        assert monitor.check_allowed("u") == MESSAGE_AI_DISABLED


class TestStats:
    def test_records_by_type_and_provider(self):
        monitor = make_monitor()
        monitor.record_request("u1", "text", "kb")
        monitor.record_request("u2", "image", "gemini_free", prompt_tokens=1000, output_tokens=500)
        monitor.record_request("u3", "voice", "gemini_free", failed=True, rate_limited=True)

        stats = monitor.stats()
        assert stats.total_requests == 3
        assert stats.text_requests == 1
        assert stats.image_requests == 1
        assert stats.voice_requests == 1
        assert stats.kb_served == 1
        assert stats.gemini_calls == 2
        assert stats.failed_requests == 1
        assert stats.rate_limit_errors == 1
        assert stats.per_provider["kb"] == 1
        assert stats.per_provider["gemini_free"] == 2

    def test_estimated_savings_tracked_only_for_gemini(self):
        monitor = make_monitor()
        monitor.record_request("u1", "text", "kb")
        assert monitor.stats().estimated_savings_usd == 0.0

        monitor.record_request(
            "u2", "text", "gemini_free", prompt_tokens=1_000_000, output_tokens=1_000_000
        )
        savings = monitor.stats().estimated_savings_usd
        assert savings == pytest.approx(0.75 + 3.75)
        assert monitor.stats().estimated_paid_cost_usd == 0.0

    def test_usage_counters_increment_on_record(self):
        monitor = make_monitor(max_requests_per_user_per_day=5)
        for _ in range(5):
            monitor.record_request("u1", "text", "kb")
        assert monitor.check_allowed("u1") == MESSAGE_DAILY_USER_LIMIT
