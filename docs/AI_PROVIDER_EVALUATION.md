# Kisan Mitra — AI Provider Evaluation

**Status:** Reference evaluation only. Not approved for production integration.  
**Upstream repository:** https://github.com/tashfeenahmed/freellmapi.git  
**Local path:** `D:\Kisan-Mitra-References\freellmapi`  
**Inspected revision:** `abbdc526d29301b14cedb51944967ff6dc522ea7` (commit `abbdc52 chore(desktop): release 0.16.51`)  
**License:** MIT (Copyright 2026 Tashfeen Ahmed)  
**Evaluation date:** 2026-11-28

---

## 1. FreeLLMAPI Overview

FreeLLMAPI is a self-hosted OpenAI-compatible gateway that stacks the free tiers of ~87 providers behind a single `freellmapi-…` bearer token. It is an Express proxy exposing `/v1/chat/completions` (plus `/v1/responses`, `/v1/messages`, `/v1/completions`, `/v1/embeddings`, `/v1/models`, media, and Anthropic Messages surfaces).

**Key capabilities relevant to evaluation:**

| Capability | Description | Relevance to Kisan Mitra |
|------------|-------------|--------------------------|
| Smart routing, six strategies | Thompson-sampling bandit scoring live reliability, speed, capability, headroom | Reference for routing design (not for copy) |
| Automatic failover | On 429/5xx, cools the key and retries the next model in chain (up to 20 attempts within wall-clock budget) | Reference for retry/circuit-breaker patterns |
| Per-key rate tracking | RPM/RPD/TPM/TPD counters per `(platform, model, key)` backed by SQLite | Reference for usage accounting |
| Self-updating model catalog | Signed catalog from freellmapi.co synced twice daily (free installs: monthly snapshot, 30-day delay) | Not applicable — Kisan Mitra uses fixed approved models |
| Encrypted key storage | AES-256-GCM in SQLite; decrypted in-memory per request | Reference for key handling patterns |
| Unified bearer token | Apps see one `freellmapi-…` token; provider keys stay server-side | Reference for API key proxy pattern |
| Prompt compression (opt-in) | Deduplication, tool-output filtering, JSON compaction, context trimming | Reference for cost-control patterns |
| Tool-call rescue | Plain-text tool calls rescued into structured `tool_calls` | Reference for tool-calling patterns |
| Fusion (multi-model synthesis) | Fans prompt to panel of models, judge model synthesizes one answer | Not applicable — cost-prohibitive for free tier |
| Image/video/speech generation | Routes across media-capable providers | Not applicable — Kisan Mitra uses Gemini Vision via own client |

**Architecture components:**
- Router: `server/src/services/router.ts` — picks model per request
- Rate-limit ledger: `server/src/services/ratelimit.ts` — sliding-window counters backed by SQLite
- Provider adapters: `server/src/providers/*.ts` — one file per provider, `Provider` base class
- Health service: `server/src/services/health.ts` — periodic probe
- Storage: SQLite (`better-sqlite3`) with AES-256-GCM envelope encryption
- Dashboard: React + Vite + shadcn/ui admin surface

---

## 2. Mandatory Restrictions (from task directive)

| Restriction | Rationale |
|-------------|-----------|
| **Not an approved multi-user commercial AI service** | FreeLLMAPI is documented as "personal experimentation and single-user tool"; binds `127.0.0.1` by default; no multi-tenant auth by design |
| **Do not assume advertised aggregate token capacity** | "10.1 billion tokens per month" is aggregate across 87 providers; no single user gets that; free tiers reset at UTC midnight and degrade through the day |
| **No account/key rotation to evade restrictions** | Explicitly prohibited; one account per provider is the rule of thumb |
| **No live inference or API account creation during this task** | Evaluation is documentation-only |
| **No proprietary code/credentials/farmer data sent to unapproved providers** | Security rule |
| **FreeLLMAPI adapter must be disabled by default** | Experimental only |
| **Do not create duplicate production AI router** | Kisan Mitra already has `AIRouter` in `backend/app/services/ai_router.py` |
| **Do not replace Gemini or modify knowledge-first architecture** | Approved architecture stands |
| **Authentication, entitlement, emergency-disable, quota checks must occur before cache hit or external request** | Kisan Mitra security principle |

---

## 3. Evaluation Against Kisan Mitra Requirements

| Kisan Mitra Requirement | FreeLLMAPI Capability | Gap / Concern |
|-------------------------|----------------------|---------------|
| Multi-tenant farmer/shop/consultant isolation | **None** — single-user by design, no multi-tenant auth | Major gap; would require building tenant isolation on top |
| Role-based permissions | **None** — single dashboard account | Major gap |
| Subscription entitlement checks | **None** — no subscription/billing model | Major gap |
| Atomic usage accounting per `(user_id, IST_month)` | **Partial** — per-key RPM/RPD/TPM/TPD counters, but not per-user/per-month IST | Partial; different quota model |
| Emergency AI disable switch | **None** as a kill-switch; can disable providers individually | Gap; `AI_ENABLED=false` pattern not present |
| Provider/model allowlists | **Partial** — dashboard enables/disables providers and models | Partial; not integrated with Kisan Mitra auth |
| Strict budget limits | **Partial** — per-key rate tracking, monthly budget alerts | Partial; not tied to subscription |
| Timeouts, bounded retries, exponential backoff, circuit breakers | **Yes** — provider timeouts, cooldowns, failover chain | Good reference |
| Provider-specific audit metadata | **Partial** — `X-Routed-Via` header, analytics | Partial; not linked to Kisan Mitra audit logs |
| Agricultural knowledge citations | **None** — no RAG/citation system | Major gap |
| Dosage validation | **None** — no safety arbiter | Major gap |
| Consultant escalation | **None** | Major gap |
| Marathi and English support | **None** as a feature; depends on underlying model | Depends on provider model |

**Verdict:** FreeLLMAPI is **not suitable** for Kisan Mitra production farmer-facing AI. It is a single-user experimentation tool with no multi-tenancy, no subscription entitlement, no RAG, no dosage validation, and no consultant escalation. Integrating it would require building all of these on top, which duplicates Kisan Mitra's planned architecture.

---

## 4. Provider Eligibility Matrix

The matrix below is compiled from FreeLLMAPI's Terms of Service review (May 2026, in `docs/en/architecture/00-high-level-index.md#terms-of-service-review`) and provider documentation references. **Verified** = confirmed from FreeLLMAPI ToS review or official provider docs cited. **Unverified** = not independently confirmed for this project.

| Provider | Model | Auth | Verified Free-Tier Quota | Commercial Use | Geographic Availability | Vision | Marathi Performance | Embeddings | Data Retention / Training | Privacy Requirements | Billing Risk | Internal Experimentation | Commercial Use |
|----------|-------|------|-------------------------|----------------|------------------------|--------|---------------------|------------|-------------------------|---------------------|--------------|------------------------|----------------|
| Google Gemini | Gemini 3.x family | API key | Not verified for this project (DEC-005) | ⚠️ Caution — ToS narrows to "professional or business purposes" | Global | Yes | Unknown (depends on model) | Yes (text-embedding-004) | Per Google AI Terms | Google AI Terms of Service | Tier-dependent; 429 never triggers paid fallback | ✅ Approved (existing) | ❌ DEC-005 pending |
| Groq | Various (Llama, etc.) | API key | Not verified | ✅ Likely OK (GroqCloud ToS) | Global | Depends on model | Unknown | No | Per Groq Terms | GroqCloud Services Agreement | Low for experimentation | ✅ Suitable | ⚠️ Terms review needed |
| Cerebras | Various | API key | Not verified | ✅ Likely OK | Global | Depends on model | Unknown | No | Per Cerebras Terms | Cerebras Terms | Low for experimentation | ✅ Suitable | ⚠️ Terms review needed |
| Mistral | Various | API key | Not verified | ✅ Likely OK (personal/internal business) | Global | Depends on model | Unknown | Yes | Per Mistral Terms | Mistral API Terms | Low for experimentation | ✅ Suitable | ⚠️ Terms review needed |
| OpenRouter | Various (aggregator) | API key | Not verified | ✅ Likely OK (private single-user proxy) | Global | Depends on model | Unknown | Yes | Per OpenRouter Terms | OpenRouter ToS | Low for experimentation | ✅ Suitable | ⚠️ No-resale clause |
| Cloudflare Workers AI | Various | API key | Not verified | ⚠️ Ambiguous | Global (Cloudflare edge) | Depends on model | Unknown | Yes | Per Cloudflare Terms | Cloudflare Self-Serve Agreement | Low for experimentation | ✅ Suitable | ⚠️ Ambiguous ToS |
| NVIDIA NIM | Various | API key | Not verified | ⚠️ Caution — "evaluation only, not production" | Global | Depends on model | Unknown | Yes | Per NVIDIA Terms | NVIDIA NIM Trial ToS | Evaluation-only scope | ✅ Suitable (evaluation) | ❌ Not for production |
| Cohere | Various | API key | Not verified | ❌ Avoid — forbids "personal, family or household purposes" | Global | Depends on model | Unknown | Yes | Per Cohere Terms | Cohere Terms §14 | Not recommended | ❌ Avoid | ❌ Avoid |
| Zhipu | Various | API key | Not verified | ✅ Likely OK (personal/non-commercial research) | China-focused | Depends on model | Unknown | Yes | Per Zhipu Terms | Zhipu Platform Docs | Low for experimentation | ✅ Suitable | ⚠️ Research-only |
| Z.ai (api.z.ai) | Various | API key | Not verified | ⚠️ Caution — anti-traffic-redirect clause | Singapore/Global | Depends on model | Unknown | Yes | Per Z.ai Terms | Z.ai Terms §III.3(l) | Potential ToS conflict | ⚠️ Caution | ❌ Not recommended |
| Ollama Cloud | Various | API key | Not verified | ✅ Likely OK (free plan, 1 concurrent, 5-hour session) | Global | Depends on model | Unknown | Yes | Per Ollama Terms | Ollama Cloud Free Plan | Session caps | ✅ Suitable | ⚠️ Session limits |
| OVH AI Endpoints | Various | API key (anonymous documented) | Not verified | ✅ Likely OK (anonymous access documented) | Europe/Global | Depends on model | Unknown | Yes | Per OVH Terms | OVH Self-Serve Agreement | Caps may be introduced | ✅ Suitable | ⚠️ Caps may change |
| AI Horde | Various | API key (`0000000000` for anonymous) | Not verified | ✅ Likely OK (community commons, non-profit) | Global | Depends on model | Unknown | Yes | Per AI Horde Terms | AI Horde (Haidra non-profit) | Low queue priority | ✅ Suitable | ⚠️ Community resource |

**Key findings:**
- **Gemini** remains the only approved provider for Kisan Mitra (already integrated as `gemini_client.py`), but DEC-005 (project tier/terms verification) is pending.
- No provider in the matrix has verified commercial-use permission for a multi-user agricultural advisory platform in India without further terms review.
- **Cohere** should be avoided (ToS forbids personal/family/household use).
- **NVIDIA NIM** is evaluation-only, not production.

---

## 5. Potential Development Uses (non-production)

| Use | Viability | Notes |
|-----|-----------|-------|
| **A. Internal AI model experimentation** | ✅ Suitable | FreeLLMAPI can route experiments across providers for internal tool development. Must be disabled by default, no farmer data. |
| **B. OpenCode development assistance** | ⚠️ Conditional | Can route OpenCode through local FreeLLMAPI instance. No Kisan Mitra code/credentials should be sent. Developer's own provider keys only. |
| **C. Synthetic agricultural question benchmarking** | ⚠️ Conditional | Can generate synthetic Q/A pairs for testing RAG retrieval. No real farmer questions, no crop photos, no private consultant knowledge. |
| **D. Future approved farmer-facing provider integration** | ❌ Not approved | Would require DEC-005, multi-tenant isolation, entitlement, dosage validation, consultant escalation — none present in FreeLLMAPI. |

---

## 6. Proposed AI Adapter Architecture (Experimental, Disabled by Default)

If the owner approves experimental use, a `FreeLLMAPIProviderAdapter` would wrap FreeLLMAPI's OpenAI-compatible endpoint behind Kisan Mitra's existing `AIRouter`. It would **never** be a replacement for `gemini_client.py` or the knowledge-first router.

**Adapter design constraints (mandatory):**

1. **Disabled by default** — feature flag `FREELLAPI_ENABLED=false`; never enabled in production without owner approval
2. **Authentication first** — Kisan Mitra JWT/session validation before adapter is consulted
3. **Entitlement check** — Pro subscription and AI quota verified before any request reaches FreeLLMAPI
4. **Consent check** — Farmer consent for external AI processing verified before request
5. **Emergency disable** — `AI_ENABLED=false` short-circuits before adapter; FreeLLMAPI also disabled
6. **Provider/model allowlist** — only explicitly approved models on the allowlist; no automatic fallback across all providers
7. **Atomic usage accounting** — Kisan Mitra's `free_usage_counters` (durable, IST-month) takes precedence; FreeLLMAPI's internal counters are supplementary only
8. **Budget limits** — strict per-user, per-day, per-month caps below FreeLLMAPI's provider caps
9. **Timeouts, bounded retries, exponential backoff + jitter, circuit breakers** — Kisan Mitra's own wrapper, not FreeLLMAPI's
10. **Audit metadata** — record `routed_via`, `provider`, `model`, `latency_ms`, `tokens`, `cache_hit` in `ai_response_logs` / `gemini_fallback_logs`
11. **Knowledge citations** — adapter must not bypass KB-first; RAG context must be prepended to prompt
12. **Dosage validation** — safety arbiter (`KM-RAG-002`) validates output before return
13. **Consultant escalation** — below-threshold or unsafe responses escalate, never fall through to another free provider
14. **Marathi and English support** — depends on underlying model; adapter must not claim language support it doesn't have
15. **No embedding mixing** — if embeddings are used, must not mix incompatible models in the same `pgvector` index without versioning and re-indexing plan

**Adapter flow:**

```
Farmer Request
    │
    ▼
[1] Auth: JWT valid + session active
    │
    ▼
[2] Entitlement: Pro tier + AI quota remaining (atomic)
    │
    ▼
[3] Consent: Farmer approved external AI processing
    │
    ▼
[4] Emergency disable: AI_ENABLED=false short-circuits
    │
    ▼
[5] KB-first: RAG retrieval (similarity ≥ 0.78) → answer from KB
    │
    ▼
[6] If below threshold: FreeLLMAPI adapter (if enabled + allowlisted)
    │
    ▼
[7] Safety arbiter: dosage validation, CIB/NRCG checks
    │
    ▼
[8] Return answer with citations + audit log
```

**Files affected (proposed, not implemented):**
- `backend/app/services/freellmapi_adapter.py` (new, disabled by default)
- `backend/app/main.py` (route registration, gated by feature flag)
- `.env.example` (add `FREELLAPI_ENABLED`, `FREELLAPI_BASE_URL`, `FREELLAPI_API_KEY` placeholders)

---

## 7. License and Security Limitations

| Item | Detail |
|------|--------|
| License | MIT — permissive, allows modification and commercial use of the code itself |
| Upstream terms | Each provider's ToS still applies when traffic is proxied; user is responsible for compliance |
| Security model | Single-user, trusted-network; binds `127.0.0.1` by default; no multi-tenant auth |
| SLA | None — free tiers, no uptime guarantee |
| Key storage | AES-256-GCM in SQLite; `ENCRYPTION_KEY` must be protected |
| Supply chain | npm package; verify before install (npm registry currently blocked in this environment) |
| Data flow | Requests go from local machine to upstream providers; prompts/completions not seen by catalog server |
| Kisan Mitra compatibility | Would add a Node.js dependency to a Python backend; architectural mismatch |

---

## 8. Recommendation

**Do not integrate FreeLLMAPI into Kisan Mitra production.** It is a single-user experimentation tool that lacks multi-tenancy, subscription entitlement, RAG citations, dosage validation, consultant escalation, and Marathi-language guarantees. All of these are core Kisan Mitra requirements.

**Permissible uses (documentation, no code):**
- Internal engineering reference for routing, retry, circuit-breaker, and rate-limit patterns
- Optional local experimentation by developers with their own provider keys (no Kisan Mitra code/data)
- Synthetic question generation for RAG benchmarking (no real farmer data)

**If owner approves future evaluation:** Create the disabled-by-default adapter described in §6, gated behind `FREELLAPI_ENABLED=false`, with all mandatory constraints enforced before any external request.
