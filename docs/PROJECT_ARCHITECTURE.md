# Kisan Mitra — Project Architecture

**Status:** Consolidated architecture record.  
**Distinction:** This document separates **implemented** (source present, tests pass locally) from **planned** (specified but not implemented). Do not treat planned architecture as running code.

---

## 1. Architecture Overview

One FastAPI backend serves two clients (mobile + owner web). PostgreSQL 16 with pgvector and Row Level Security is the system of record. Redis caches entitlements/sessions. Supabase Storage holds private files. Google Gemini free tier is the controlled AI fallback behind a knowledge-base-first router.

Planned data flow (from product architecture):

```
Clients (Mobile app + Owner web) ──> Cloudflare Edge ──> FastAPI backend
                                                    │
                                                    ├──> PostgreSQL 16 + pgvector (RLS)
                                                    ├──> Redis (cache/rate limits)
                                                    ├──> Supabase Storage (private files)
                                                    ├──> Gemini free tier (AI, gated)
                                                    └──> Weather, SMS, IVR, push integrations
```

All external connections above are **planned** unless noted as implemented.

---

## 2. Implemented vs Planned Components

### 2.1 Backend (Python 3.12, FastAPI)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| API app factory (`create_app`) | Implemented | `backend/app/main.py` | Shell with health, auth, onboarding, partner, admin, plot routes |
| RS256 JWT token service | Implemented | `backend/app/auth.py` | 2048-bit RSA, kid-indexed public ring, issuer/audience/time validation |
| Session store interface | Implemented (Postgres + fake) | `backend/app/postgres_auth.py`, `auth.py` | PostgreSQL functions from migration 0002; not DB-verified |
| OTP provider interface | Implemented (fake default) | `backend/app/auth.py` | No live SMS sender connected |
| Credential store (scrypt) | Implemented | `backend/app/passwords.py`, `credentials.py` | Salted scrypt, private credential table (migration 0004) |
| Farmer onboarding | Implemented (API tested) | `backend/app/farmer_onboarding.py` | Migration 0006; consent not seeded |
| Partner applications/store | Implemented (API tested) | `backend/app/partners.py` | Migration 0007 |
| Admin provisioning | Implemented (API tested) | `backend/app/admin_provision.py` | Migration 0008; no actual Owner identity created |
| Farmer plots + weather | Implemented (source) | `backend/app/plots.py`, `weather.py` | Migration 0009; weather returns `unavailable` (no live provider) |
| AI router | Implemented (helper only) | `backend/app/services/ai_router.py` | Not wired to production routes; KB-first protocol |
| Gemini client | Implemented (helper only) | `backend/app/services/gemini_client.py` | Free-tier guard; no live key/calls |
| Image pipeline | Implemented (helper only) | `backend/app/services/image_pipeline.py` | Magic-byte validation, resize, compression, SHA-256 hash |
| Usage monitor | Implemented (helper only) | `backend/app/services/usage_monitor.py` | In-memory counters only; not durable/transactional |
| Auth/middleware/entitlement | Partial | `backend/app/main.py` | Role/state lookup; no full entitlement engine |

**Planned (not implemented):** Full entitlement service, subscription engine, RAG engine, safety arbiter, knowledge ingestion worker, chat service, IVR calling service, weather provider adapter, notification service, workers.

### 2.2 Database (PostgreSQL 16 + pgvector)

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| Migrations 0001–0009 | Implemented (SQL files) | `backend/migrations/` | Additive, versioned; none executed on live database |
| RLS policies | Specified only | `docs/product-documentation/03_SECURITY_AND_ACCESS_KISAN_MITRA.md` (§5) | SQL examples in doc; not applied to a real DB |
| pgvector extension | Specified only | Architecture doc §6.12 | `vector(768)` for embeddings; not installed anywhere |
| Seed/test identities | Specified only | Roadmap Phase 1 §1.2 | Not executed |

### 2.3 Mobile (React Native / Expo, TypeScript)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Typed API client | Implemented | `mobile/src/auth/client.ts` | Uses Expo SecureStore for refresh |
| Auth screens | Implemented (source) | `mobile/src/auth/` | Bilingual auth/onboarding views |
| Plot manager | Implemented (source) | `mobile/src/` (Stage 2A) | Farmer plot form and switcher |
| Native Marathi speech | Implemented (wrapper only) | `mobile/src/services/nativeSpeech.ts` | `NativeModules.KisanSpeech` not linked |
| Expo/Next type checks & builds | Not run | — | npm registry blocked; no node_modules |
| Device packaging | Not run | — | No Expo/iOS/Android build exists |

### 2.4 Owner Website (Next.js)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Server auth (HttpOnly cookies, CSRF/origin) | Implemented (source) | `web/lib/server-auth.ts`, `web/app/` | Owner login/recovery, partner decision interface |
| Admin reauth (5-min RS256 token) | Implemented (source) | `web/app/` | Sensitive-decision protection |
| Type check & production build | Not run | — | npm blocked; `tsc`/`next` not found |
| Holding site (static, not owner dashboard) | Implemented (files) | `site/holding/` | Marathi/English pages; not verified live |

### 2.5 AI / Knowledge (planned, partially implemented)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Knowledge-base-first router | Partial | `backend/app/services/ai_router.py` | Helper only; no authenticated route, approved corpus, tenant-aware retrieval |
| RAG engine | Missing | — | No persisted chunks, embeddings, scoped retrieval, citations |
| 16-step knowledge ingestion | Missing | — | No PDF/DOCX/XLSX/CSV worker, no approval lifecycle |
| Safety arbiter / conflict resolution | Missing | — | No CIB/NRCG rule checks, no dosage validation |
| Gemini fallback (gated) | Partial | `gemini_client.py` | Free-tier guard only; no live call, no tier verification |
| AI telemetry | Missing | — | No `ai_response_logs`, `gemini_fallback_logs` persistence |

### 2.6 Integrations (all planned, none live)

| Integration | Status | Notes |
|-------------|--------|-------|
| Gemini API | Planned (free tier only) | No live key; tier not verified (DEC-005) |
| SMS / OTP (DLT) | Planned | No sender configured |
| Push (FCM) | Planned | Not configured |
| Weather (Open-Meteo / IMD) | Planned | Stage 2A returns `unavailable`; no live provider |
| IVR / telephony | Planned | Not configured |
| Supabase Storage | Planned | Not wired |
| FreeLLMAPI (experimental adapter) | Planned (disabled by default) | Not suitable for production — see `docs/AI_PROVIDER_EVALUATION.md`; `FREELLAPI_ENABLED=false` |

---

## 2.7 AI Provider Evaluation

See `docs/AI_PROVIDER_EVALUATION.md` for:
- FreeLLMAPI repository evaluation (MIT license, commit `abbdc52`)
- Provider eligibility matrix (commercial use, privacy, Marathi, vision, embeddings, billing risk)
- Proposed adapter architecture (disabled by default, all mandatory constraints)
- License and security limitations

---

## 3. Technology Stack (implemented vs planned)

| Layer | Selected (planned) | Implemented today |
|-------|-------------------|-------------------|
| Backend | Python 3.12 + FastAPI + Pydantic v2 | FastAPI shell only (no DB-backed routes live) |
| Database | PostgreSQL 16 + pgvector (Supabase) | Migration SQL files only; no DB applied |
| Cache | Redis 7.2 | Not connected |
| Storage | Supabase Storage | Not wired |
| Mobile | React Native / Expo SDK 58, TypeScript | Source shells; no build |
| Web dashboard | Next.js 14 App Router + Tailwind | Source shells; no build |
| AI | Google Gemini free tier | Client helper only; no live calls |
| Vector | pgvector HNSW/IVFFlat | Not installed |
| SMS/OTP | DLT-compliant gateway | No sender |
| Push | Firebase Cloud Messaging | Not configured |
| Weather | Open-Meteo / IMD | Not connected |
| IVR | Exotel/Twilio (planned) | Not connected |
| Edge | Cloudflare | Not configured |

---

## 4. Schema Summary (planned)

The approved schema is defined in `docs/product-documentation/02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md` (§6). Key tables:

`users`, `farmer_profiles`, `farms` (plots), `crops`, `crop_stages`, `farm_activities`, `subscription_plans`, `plan_entitlements`, `subscriptions`, `upgrade_enquiries`, `pending_pro_activations`, `knowledge_documents`/`knowledge_chunks`, `ai_conversations`/`ai_messages`, `uploaded_photos`, `shops`, `consultants`, `farmer_relationships`, `audit_logs`, `daily_usage_records`, `master_knowledge_documents`, `consultant_knowledge_documents`, `knowledge_document_versions`, `knowledge_approval_records`, `knowledge_processing_jobs`, `personalized_farm_schedules`, `farm_schedule_items`, `schedule_revisions`, `farm_observations`, `recommendation_sources`, `ai_retrieval_logs`, `ai_response_logs`, `gemini_fallback_logs`, `farmer_relationship_history`, `chat_conversations`, `chat_messages`, `schedule_configurations`, `schedule_events`, `medicine_products`, `weather_alert_events`, `farmer_calling_settings`, `daily_call_ledger`, `system_configurations`.

Note: Document counts conflict (architecture §6 says 24 tables, final review says 35, document contains 48 `CREATE TABLE` statements). Normalize to a single executable schema before Phase 2 (see DECISION_LOG).

---

## 5. Security Architecture (planned / partially implemented)

- RS256 JWT (15-min access, 30-day refresh with rotation) — implemented at code level, DB-unverified.
- Server-side role/tier lookup on every request (not trusted from token claims) — implemented.
- PostgreSQL RLS with deny-by-default — specified in security doc; not applied to a real DB.
- Fail-closed default adapters — implemented.
- No secrets in client bundles — verified by source scan (0 PEM/key/token patterns found).
- OTP rate limits (5 attempts/15min mobile+IP, 3 requests/hour) — code-written, DB-unverified.
- Admin reauthentication (5-min RS256 proof) for sensitive decisions — implemented at route level.

**Known gap (Stage 2A):** Migration-owned functions take a Farmer subject argument; theft of the `km_api` database credential would bypass API ownership. Not end-to-end RLS isolation. See `docs/KNOWN_ISSUES.md`.
