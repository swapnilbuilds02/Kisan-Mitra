# Kisan Mitra — System Design Standards

**Status:** Engineering standards document. Maps TRACEN Vibe Coding Trail foundational concepts to the approved Kisan Mitra roadmap.  
**Source:** TRACEN Vibe Coding Trail (referenced in task; PDF not present in local references directory — concepts mapped from task list).  
**Rule:** Do not introduce Kubernetes, Kafka, unnecessary microservices, distributed transaction frameworks, or additional databases without demonstrated requirement and owner approval. Preserve the existing centralized backend architecture.

---

## 1. TRACEN Concept Mapping

All 20 concepts mapped to Kisan Mitra roadmap tasks, existing implementations, gaps, and priority.

| # | Concept | Definition | Existing Implementation | Current Gap | Roadmap Task | Proposed Improvement | Security | Performance | Complexity | Testing | Priority |
|---|---------|------------|------------------------|-------------|--------------|---------------------|----------|-------------|------------|---------|----------|
| 1 | Rate limiting | Caps requests per client/IP/key over a time window to prevent abuse | OTP rate limits (5 attempts/15min mobile+IP, 3 requests/hour) in `postgres_auth.py`; code-written, DB-unverified | No API-level rate limits on chat/vision endpoints; no per-user burst limits | `KM-SEC-001` (security hardening), `KM-AIRT-001` (usage controls) | Edge + application rate limits per user/role/endpoint; Redis-backed sliding windows | Prevents brute-force, quota exhaustion, DoS | Protects backend from overload | Low — add middleware | Load tests, burst tests, negative auth tests | **Now** (P0) |
| 2 | Caching | Stores computed results to reduce redundant work | In-memory usage counters (`usage_monitor.py`); weather in-process cache (`weather.py`) | No durable cache; no tenant-safe cache; no cache invalidation on consent revocation | `KM-AIRT-001`, `KM-VIS-001`, `KM-WTH-002` | Redis-backed tenant-scoped cache with TTL; consent-aware invalidation; cache key includes user/tenant/context | Prevents cross-tenant cache leakage; cache must respect `AI_ENABLED=false` | Reduces latency, lowers provider costs | Medium — cache invalidation complexity | Cache hit/miss tests, TTL tests, invalidation tests | **Now** (P0) |
| 3 | Load balancing | Distributes traffic across multiple backend instances | None — single FastAPI instance planned | No load balancer; no multi-instance deployment | None (Phase 7 operations) | Not required for Phase 1-2; single instance sufficient | N/A | N/A | High — unnecessary for current scale | N/A | **Unnecessary** |
| 4 | Reverse proxies | Server that forwards client requests to backend, often with TLS/termination | Cloudflare Edge (planned, not configured) | No reverse proxy deployed; no TLS termination | Phase 7 (release verification) | Cloudflare or Nginx reverse proxy with TLS, WAF rules, rate limiting at edge | Hides backend, enforces TLS, WAF protection | Offloads SSL, compression, buffering | Medium — infra config | TLS tests, header forwarding tests | **Later** (Phase 7) |
| 5 | API gateways | Single entry point that routes, authenticates, rate-limits, transforms requests | FastAPI app factory (`create_app`) with bearer token auth; role/state middleware | No dedicated gateway; no CORS/transformation layer; no API versioning strategy | `KM-FOUND-001`, `KM-AUTH-001` | API versioning (`/api/v1/`), CORS policy, request size limits, security headers | Central auth enforcement, input validation, CORS control | Adds slight latency; enables caching at gateway | Medium — gateway config | Auth tests, CORS tests, header tests | **Now** (P0) |
| 6 | CI/CD | Automated build, test, deploy pipelines | GitHub Actions workflow prepared (`.github/workflows/backend-foundation.yml`); never run | No CI execution; no frontend build jobs run; no deploy pipeline | Phase 1 gate closure | Run backend tests, PostgreSQL integration, web typecheck/build, mobile typecheck/expo config | Prevents broken code from merging; secret scanning | Faster feedback on regressions | Medium — workflow config | CI pipeline tests, workflow validation | **Now** (P0) |
| 7 | Docker | Containerized application packaging | None | No Dockerfile; no container builds | Phase 7 | Optional Dockerfile for backend; not required for MVP | Image scanning, no secrets in layers | Consistent dev/prod environments | Low — Dockerfile only | Build test, container start test | **Later** (Phase 7) |
| 8 | Kubernetes | Container orchestration platform | None | Not applicable | None | **Not authorized** — introduces unnecessary complexity | N/A | N/A | High | N/A | **Unnecessary** |
| 9 | Service discovery | Services locate each other dynamically | None — single backend, direct DB/Redis connections | Not needed for current architecture | None | Not required — centralized architecture | N/A | N/A | High — unnecessary | N/A | **Unnecessary** |
| 10 | Circuit breakers | Stops calling a failing service after threshold, allows recovery | None — FreeLLMAPI reference has cooldowns but not implemented in Kisan Mitra | No circuit breaker on Gemini or external provider calls | `KM-AIRT-001`, `KM-RAG-003` | Circuit breaker per external provider (Gemini, weather, SMS); open/half-open/closed states | Prevents cascade failures, protects provider quotas | Fails fast, preserves resources | Medium — state management | Circuit open/close tests, fallback tests | **Now** (P0) |
| 11 | Timeouts | Maximum wait time for a request/operation | None configured | No timeouts on external API calls; no DB query timeouts | `KM-AIRT-001` | Provider-specific timeouts (Gemini: 30s, weather: 10s, SMS: 15s); DB query timeouts | Prevents resource exhaustion from hanging requests | Predictable latency, prevents thread starvation | Low — config values | Timeout tests, mock slow provider tests | **Now** (P0) |
| 12 | Retries | Automatically re-attempt failed operations | None | No retry logic on external calls | `KM-AIRT-001` | Bounded retries (max 2-3) with idempotency keys; only for idempotent operations | Prevents duplicate charges, duplicate message sends | Improves reliability | Low — retry wrapper | Retry tests, idempotency tests | **Now** (P0) |
| 13 | Exponential backoff | Retry delay grows exponentially with jitter | None | No backoff logic | `KM-AIRT-001` | Exponential backoff + jitter for retries; respect `Retry-After` headers | Prevents thundering herd on provider recovery | Reduces provider pressure during outages | Low — config values | Backoff timing tests, jitter distribution tests | **Now** (P0) |
| 14 | Idempotency | Same request multiple times has same effect as once | None — no idempotency keys on activation/enquiry APIs | No idempotency on `/api/v1/subscriptions/enquiries`, `/api/admin/subscriptions/direct-activate` | `KM-PRO-001`, `KM-ADMIN-002` | Idempotency keys on state-changing endpoints; store processed keys with TTL | Prevents duplicate payments, duplicate lead creation | Slight storage overhead | Medium — key store, deduplication logic | Idempotency tests, duplicate-request tests | **Now** (P0) |
| 15 | Message queues + DLQ | Async message processing with dead-letter queue for failures | None | No message queue; no async processing | Phase 6 (workers, notifications) | Not required yet — synchronous API sufficient for MVP | N/A | N/A | Medium — unnecessary complexity | N/A | **Later** (Phase 6) |
| 16 | Pub/Sub | Publisher-subscriber messaging pattern | None | Not needed for current architecture | Phase 6 | Not required yet | N/A | N/A | Medium — unnecessary | N/A | **Later** (Phase 6) |
| 17 | Event-driven architecture | System reacts to events asynchronously | None | Not needed for current architecture | Phase 6 | Not required yet | N/A | N/A | Medium — unnecessary | N/A | **Later** (Phase 6) |
| 18 | Distributed transactions | ACID across multiple services/databases | None — single PostgreSQL database | Not needed — single DB gives ACID | None | **Not authorized** — single DB avoids distributed transactions | N/A | N/A | High — unnecessary | N/A | **Unnecessary** |
| 19 | Saga pattern | Long-running business process as sequence of local transactions with compensating actions | None | Not needed for MVP flows | Phase 2 (subscription activation) | Not required yet — direct DB transaction sufficient | N/A | N/A | Medium — unnecessary | N/A | **Later** (Phase 2) |
| 20 | Cron jobs | Scheduled background tasks | None | No scheduled jobs for subscription expiry, IVR calling, weather refresh | `KM-IVR-001`, `KM-WTH-002`, `KM-SUB-001` | Cron for: daily IVR call ledger, subscription expiry check, weather refresh; idempotent, single-instance execution | Prevents unauthorized calls after expiry | Ensures timely calls, accurate weather | Medium — scheduler, idempotency | Cron job tests, missed-run recovery, idempotency tests | **Later** (Phase 2/6) |

---

## 2. Immediate Engineering Priorities (Phase 1 gate closure)

These concepts must be implemented before Phase 1 acceptance:

1. **Rate limiting** — API-level per-user/role/endpoint limits on `/api/v1/free/*`, `/api/v1/vision/*`, `/api/v1/auth/*`
2. **Caching** — Redis-backed tenant-safe cache with TTL and consent-aware invalidation
3. **API gateway** — API versioning, CORS, security headers, request size limits
4. **CI/CD** — Run GitHub Actions workflow; PostgreSQL integration; frontend builds
5. **Circuit breakers** — Per external provider (Gemini, weather, SMS)
6. **Timeouts** — Provider-specific and DB query timeouts
7. **Retries** — Bounded retries with idempotency keys for idempotent operations
8. **Exponential backoff + jitter** — Respect `Retry-After` headers; prevent thundering herd
9. **Idempotency** — Idempotency keys on lead creation and Pro activation endpoints
10. **Reproducible test environments** — Disposable PostgreSQL, dependency lockfiles

---

## 3. Future Engineering Priorities (Roadmap Phases 2–7)

| Phase | Concepts | Implementation |
|-------|----------|----------------|
| Phase 2 | Cron jobs, idempotency, retries, backoff | Subscription expiry cron, IVR daily call, idempotent lead creation |
| Phase 3 | Caching, circuit breakers | Weather cache, schedule cache, Gemini circuit breaker |
| Phase 4 | Message queues, pub/sub | Optional — chat notifications, partner event propagation |
| Phase 5 | Caching, rate limiting, timeouts | RAG result cache, embedding API rate limits, vision API timeouts |
| Phase 6 | Message queues, pub/sub, event-driven | Chat message delivery, notification events, weather alerts |
| Phase 7 | CI/CD, Docker, reverse proxy | Production CI pipeline, container images, Cloudflare/Nginx edge |

---

## 4. Standards Summary

| Standard | Rule |
|----------|------|
| **No Kubernetes** | Not authorized; introduces unnecessary complexity for centralized architecture |
| **No Kafka/message queues** | Not required for MVP; synchronous API sufficient |
| **No distributed transactions** | Single PostgreSQL database provides ACID; sagas not needed |
| **No additional databases** | PostgreSQL + Redis only; no vector DB separate from pgvector |
| **UTC storage, IST business time** | Store timestamps as UTC (`TIMESTAMPTZ`); business logic uses IST for quotas/expiry |
| **Idempotent scheduled jobs** | Prevent duplicate execution; use atomic state updates |
| **Atomic state transitions** | All quota, subscription, and call-ledger updates must be atomic |
| **Single backend architecture** | Preserve centralized FastAPI; no microservices split |
| **Circuit breaker before external call** | No external provider call without circuit breaker + timeout |
| **Auth before cache** | Authentication, entitlement, and emergency-disable checks must occur before any cache hit or external request returns |
