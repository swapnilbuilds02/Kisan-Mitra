# Kisan Mitra AI – Free-Tier Image & Voice Implementation Report

---

## Document Control

| Property | Details |
| :--- | :--- |
| **Document Title** | AI Cost-Optimization Implementation Report (Stage B) |
| **Scope** | AI Image Analysis, AI Voice, Free-Tier Cost Controls |
| **Status** | Implemented and Verified (local); no deployment performed |
| **Classification** | Proprietary & Confidential |

> This report documents WHAT was built, WHY, HOW it can be verified, and WHAT remains. It contains no dates, deadlines, or schedule commitments.

---

## 1. Original AI Architecture

The repository contained **product documentation only** — no application code. The documented (planned) AI architecture was:

- **Backend:** Python FastAPI; all AI calls server-side; API keys in cloud secret managers.
- **Vision:** `POST /vision/analyze` → Gemini 1.5/2.0 Vision, Pro-only, 5 diagnoses/farmer/day.
- **Chat:** Knowledge Base first (similarity threshold 0.78) → Gemini fallback (~5–10% of responses).
- **Free tier:** Global KB only, zero Gemini calls, combined 3 uses/month quota.
- **Voice:** Ask by Voice (Marathi STT → RAG → TTS) with unspecified providers; Google Cloud TTS for outbound IVR.
- **Telemetry:** Designed tables `ai_retrieval_logs`, `ai_response_logs`, `gemini_fallback_logs`.

**Measured baseline cost:** not measurable — no live API traffic existed.

## 2. New Architecture (Implemented)

```
TEXT / VOICE TRANSCRIPT
  validate → usage check (emergency switch, platform/user/minute limits)
  → KB search (≥ 0.78 ⇒ answer, 0 external calls)
  → free-tier Gemini (only if KB insufficient AND configured)
  → guardrail → telemetry
  → on 429/error ⇒ Marathi message or consultant escalation (NEVER a paid model)

IMAGE
  magic-byte validation → size/dimension checks → resize ≤1024px + JPEG compress
  → SHA-256 hash → cache hit ⇒ reuse (no API call)
  → KB symptom match on user description (may answer without vision)
  → free-tier Gemini Vision → guardrail → cache
  → 429 ⇒ Marathi retry message; error ⇒ consultant escalation

SPEECH (device-native, $0)
  Android SpeechRecognizer (mr-IN) / iOS SFSpeechRecognizer
  → capability detection → editable transcript → existing router
  → TTS: Android TextToSpeech / iOS AVSpeechSynthesizer (mr-IN voice check)
  → unavailable ⇒ graceful typed-input / text-display fallback
```

Routing priority is configurable via `AI_PROVIDER_PRIORITY` (default `kb,gemini_free,consultant`).

## 3. Implemented Changes – Files Added

| File | Purpose |
| :--- | :--- |
| `backend/app/services/gemini_client.py` | Free-tier-only Gemini client; **model allowlist rejects any non-free model at initialization**; 429 → `FreeTierExhausted` (no paid retry path); 401/403 → `InvalidApiKey`; timeouts → `GeminiUnavailable`. |
| `backend/app/services/image_pipeline.py` | Magic-byte format validation (JPEG/PNG/WebP), 5 MB cap, min 64px, downscale to 1024px, JPEG re-encode, SHA-256 content hashing for cache keys. |
| `backend/app/services/usage_monitor.py` | Pluggable usage store (in-memory default, Redis-swappable); platform daily / per-user daily / per-minute limits; emergency `AI_ENABLED` switch; stats with provider counts, failures, rate-limit errors, estimated savings vs. paid baseline; Marathi user-facing messages. |
| `backend/app/services/ai_router.py` | Centralized router: KB-first, free Gemini second, consultant escalation last; vision result cache; guardrails (no dosage synthesis instructions, empty-response handling); request validation; telemetry counters on every path. |
| `mobile/src/services/nativeSpeech.ts` | Device-native Marathi STT/TTS: permission flow, capability detection (`mr-IN` support check), partial results, timeout handling, editable transcript support (`markEdited`), typed-input fallback on `language_unsupported`/`permission_denied`. |
| `.env.example` | Environment template; empty secret placeholders; free-tier model and limit defaults documented. |
| `docs/DEVELOPMENT_ROADMAP.md` | Dependency-ordered module/task structure (Modules 1–8, task IDs preserved, no dates). |
| `docs/AI_COST_OPTIMIZATION_REPORT.md` | This report. |
| `backend/tests/` (4 files, 63 tests) | Full test suite (below). |

**No files modified** — no pre-existing code existed.

## 4. APIs Used

| API | Purpose | Tier | Status |
| :--- | :--- | :--- | :--- |
| Google Gemini (`gemini-3.8-flash`) | Text fallback + vision (free-tier allowlisted models only) | **Free** | Implemented; requires backend `GEMINI_API_KEY` to activate |
| Android/iOS native speech | Marathi STT + TTS | **Free (device)** | Implemented (JS side; native module `KisanSpeech` still to be linked) |

**Not used:** Gemini Live API (free-tier data used for product improvement + session limits — rejected for production farmer data), Google Cloud TTS (paid; IVR unchanged), any paid LLM tier.

## 5. Verified Free-Tier Details (official sources, verified during Stage A)

- `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-4-hydrogen`, `gemini-2.5-flash-lite`: **free of charge**; RPM/TPM/RPD per project (read live in AI Studio, not fixed published numbers); **free-tier content may be used to improve Google products** (paid tier: no); available in India.
- Gemini 4 Carbon/Argon, 3.1 Pro: paid only → **blocked by allowlist**.
- Deprecation risk: Gemini 2.5 models route to 3.x from the announced cutoff → client pinned to 3.8-flash.
- Android `SpeechRecognizer` supports Marathi on most devices; **iOS Marathi support inconsistent** → capability check + typed fallback mandatory (implemented).
- Gemini Live: technically free on free tier but 15-min session/10-min connection limits and free-tier data training → **deliberately not implemented**.

## 6. Cost & Savings

- **Current estimated API expense: $0/month** — every code path either answers from the KB, uses device speech, or calls free-tier Gemini (which costs $0). Paid path does not exist in code.
- **Baseline comparison (hypothetical paid Flash tier):** implemented telemetry tracks `estimated_savings_usd` using $0.75/M input + $3.75/M output rates; `estimated_paid_cost_usd` is structurally pinned to 0.0.
- **Expected savings vs. a naive all-paid design:** ~100% at 100–500 farmers; 90–100% at 1,000; 70–85% at 5,000; 70–80% at 10,000 — subject to unpublished free-tier RPD, which must be measured live before scaling (see §11).
- Hosting/database/storage/telecom/SMS costs are **not** included; this work does not affect them.

## 7. Security Improvements

1. Model allowlist → impossible to accidentally call a billable model even with a billing-enabled key.
2. Keys backend-only; `.env.example` carries empty placeholders; repo scanned — **zero secrets found** (Google/OpenAI/JWT patterns).
3. Emergency kill switch (`AI_ENABLED=false`) disables all external AI while non-AI features keep running.
4. Rate limiting: platform/day, per-user/day, per-user/minute with Marathi limit messages.
5. No farmer photos/voice retained beyond processing: images hashed in-memory for cache; no persistent photo/voice storage introduced.
6. Consent/privacy UX (`KM-AICHT-002`) remains a documented dependency before production AI activation — **not yet implemented** (see §11).

## 8. Test Results

**63/63 passing** (`python -m pytest backend/tests`). TypeScript service type-checks clean (`tsc --strict`, react-native module stub).

| Suite | Count | Covers |
| :--- | :---: | :--- |
| `test_gemini_client.py` | 12 | Allowlist rejection of paid models, 429/401/500/timeout mapping, vision payload, system instruction |
| `test_image_pipeline.py` | 16 | JPEG/PNG accept, GIF/text reject, oversize reject, downscale, small-image reject, corrupt input, determinism of hashes, transparency handling |
| `test_usage_monitor.py` | 14 | Store windows, all quota types, platform cap, user isolation, emergency switch, env disable, stats/savings accounting |
| `test_ai_router.py` | 21 | KB-first (zero Gemini call), threshold fall-through, 429 → Marathi message, rate limit, AI-disabled, image cache (1 vision call for repeats), KB short-circuit on images, consultant escalation, audio routing, **no paid provider ever recorded** |

**Not yet executed** (documented in §11): Phase 9 real-world tests requiring live devices/API — real grape leaf images, Marathi voice on physical Android/iOS hardware, live Gemini key, unauthorized-request tests through FastAPI middleware (middleware not yet built).

## 9. Limitations and Risks

1. **No live API key tested** — Gemini client verified against mocked transports only; first live call must be checked against the actual AI Studio rate limits for the project.
2. **Free-tier RPD unpublished** — capacity claims for ≥1,000 farmers are estimates until measured in AI Studio.
3. **Native speech module pending** — `nativeSpeech.ts` calls `NativeModules.KisanSpeech`, which requires the native Android/iOS implementation (or a compatible community package) to be linked in the Expo dev build.
4. **Consent UI not built** — required before sending farmer photos/voice to Google under free-tier data-improvement terms.
5. **Repo has no application scaffold yet** — services are structured as a package (`app.services`) ready to drop into the FastAPI backend from `KM-FOUND-001`; no API routes, auth middleware, or DB wiring exist yet.
6. **iOS Marathi STT** may be unavailable → typed fallback implemented, but accuracy must be field-tested (`KM-UAT-001`).

## 10. Remaining Work (dependency-ordered, no schedule implied)

1. `KM-FOUND-001` monorepo/backend scaffold — mount `app.services` into FastAPI routes.
2. `KM-AIRT-001` remainder: Redis-backed usage store, admin endpoints for stats/switch, persistence of telemetry to `ai_response_logs`/`gemini_fallback_logs`.
3. Native `KisanSpeech` module (Android `SpeechRecognizer`/`TextToSpeech`, iOS `SFSpeechRecognizer`/`AVSpeechSynthesizer`) or vetted community equivalent.
4. `KM-AICHT-002` farmer privacy consent UI with free-tier data-training disclosure.
5. Phase 9 live test matrix (real images, on-device Marathi voice, live quota/429 behavior, auth-protected routes).
6. Wire vision endpoint (`KM-VIS-001`) and chat endpoint (`KM-AI-002`) to `AIRouter`.

## 11. Deployment Instructions

**No deployment was performed (no approval requested or given).** When authorized:

1. Provision backend environment; copy `.env.example` → `.env`; set `GEMINI_API_KEY` in the secret manager only (never in the repo or mobile bundle).
2. Keep `AI_ENABLED=false` during rollout; enable after the live smoke test passes.
3. Confirm project tier is **Free** in AI Studio and record actual RPM/RPD values into the limits configuration.
4. Run `python -m pytest backend/tests` in CI.
5. Release the mobile build with the native speech module linked; verify `mr-IN` availability on the physical test-device matrix.
6. Activate only after consent UI (`KM-AICHT-002`) ships.

## 12. Cost Comparison Summary (AI API only)

| Farmers | Paid-baseline estimate / month | Free-first architecture / month | Savings |
| --- | --- | --- | --- |
| 100 | $8–12 | **$0** | ~100% |
| 500 | $40–60 | **$0** (watch RPD) | ~100% |
| 1,000 | $80–120 | **$0** if within measured RPD | ~90–100% |
| 5,000 | $400–600 | $50–150 if overflow confirmed (owner approval required) | ~70–85% |
| 10,000 | $800–1,200 | $150–400 + multi-project quota design | ~70–80% |

*Method: ~1,200 input/400 output tokens per chat call; ~800 image tokens per vision call; 30% Pro activation; 2 vision + 3 fallback calls per active Pro per day. Excludes hosting, database, storage, telecom, SMS. Savings are not claimed as 100% beyond 1,000 farmers because free-tier daily request limits are unpublished and must be measured.*
