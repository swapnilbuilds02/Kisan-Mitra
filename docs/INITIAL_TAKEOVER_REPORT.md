# Kisan Mitra — Initial Takeover Report

**Report date:** 2026-11-28  
**Prepared by:** Senior software architect / AI takeover (opencode)  
**Project:** Kisan Mitra AI (formerly DrakshGuru / Krushi Mitra AI)  
**Repository:** https://github.com/swapnilbuilds02/Kisan-Mitra.git (branch: main, up to date with origin/main)  
**Product owner:** Swapnil Pawar (jeeswapnil002@gmail.com)

---

## 1. Project Understanding

Kisan Mitra AI is a Marathi-first agronomy platform for grape growers in Maharashtra, India. It is a freemium multi-role platform comprising:

- **Mobile app** (React Native/Expo): Farmer, Shop Partner, Agronomy Consultant
- **Owner web dashboard** (Next.js): Super Admin / Platform Admin
- **FastAPI backend** with PostgreSQL 16 + pgvector, Redis, Supabase Storage
- **AI**: Google Gemini free tier behind a knowledge-base-first router (~95% grounded target)
- **Business model**: Free = Schedule Search + Limited KB Chat (3 combined uses/month IST); Pro = owner-activated 1-calendar-year subscription via WhatsApp `wa.me` lead → manual payment → direct admin activation

Core architecture:

```
Mobile app (Expo/React Native) ──┐
Owner web dashboard (Next.js) ───┴──> Cloudflare Edge ──> FastAPI backend ──> PostgreSQL 16 + pgvector (+ RLS)
                                                                ├──> Redis cache
                                                                ├──> Supabase Storage
                                                                ├──> Gemini free tier (AI)
                                                                └──> Weather, SMS, IVR, push integrations
```

Key source locations:
- `backend/app/main.py` — FastAPI app factory (auth, onboarding, partner, admin, plot routes)
- `backend/app/services/` — `ai_router.py`, `gemini_client.py`, `image_pipeline.py`, `usage_monitor.py` (partial AI helpers, not wired into production endpoints)
- `backend/migrations/0001_` through `0009_` — additive SQL migrations
- `mobile/src/auth/` — typed API client, auth screens, plot manager
- `web/app/`, `web/lib/server-auth.ts` — Next.js owner dashboard shells
- `site/holding/` — static holding site (not the owner dashboard)
- `brand/KISAN-MITRA-BRAND/` — owner-supplied "Krushi Mitra AI" artwork

---

## 2. Existing Architecture

### Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 with pgvector, Supabase, RLS |
| Cache | Redis 7.2 |
| Mobile | React Native with Expo, TypeScript |
| Owner dashboard | Next.js |
| AI | Google Gemini free tier behind a central router |
| Voice | On-device Marathi speech-to-text and text-to-speech |
| Weather | Open-Meteo and IMD |
| Notifications | Firebase Cloud Messaging |
| Edge | Cloudflare |

### AI answer flow (from README)

Question → Validate/compress → Knowledge base match (similarity ≥ 0.78?) → Answer from verified KB  
→ If no match: Pro plan + quota left? → Free-tier Gemini with guardrails → Answer with no invented dosage  
→ If no quota: Consultant escalation or Marathi retry message  
`AI_ENABLED=false` switch turns off every external AI call.

---

## 3. Completed Features (Source Implemented, Tests Pass Locally)

| Feature | Status | Evidence |
|---------|--------|----------|
| RS256 JWT token contract | Verified (local) | `backend/app/auth.py`, 95 tests pass |
| Farmer OTP claim + admin pre-registration | API tested, DB unverified | `backend/app/auth.py`, `identity.py` |
| Durable sessions & OTP limits | Code written, DB unverified | `backend/app/postgres_auth.py`, migration 0002 |
| Password login/recovery/change | Local API tested, DB unverified | `backend/app/passwords.py`, `credentials.py`, migrations 0004-0005 |
| Shop/Consultant application & approval | Local API tested, DB unverified | `backend/app/partners.py`, migration 0007 |
| Restricted Admin activation/password/OTP | Local API tested, DB unverified | `backend/app/admin_provision.py`, migration 0008 |
| Farmer profile onboarding & consent | Local API tested, DB unverified | `backend/app/farmer_onboarding.py`, migration 0006 |
| Farmer plots + weather context | Source implemented, DB/mobile unverified | `backend/app/plots.py`, `weather.py`, migration 0009 |
| AI cost controls (router, monitor, client, image pipeline) | Partial — pre-existing helpers | `backend/app/services/` |
| Branding (Krushi Mitra AI artwork) | Working tree only | `brand/KISAN-MITRA-BRAND/`, BRAND-001–004 |
| Holding website | Static files, not verified live | `site/holding/` |

**Test baseline**: `python -m pytest backend/tests -q` → **138 passed, 9 skipped (guarded PostgreSQL), 0 failed** on 2026-11-27.

---

## 4. Partially Implemented Features

| Feature | Gap |
|---------|-----|
| `KM-AIRT-001` Free-tier AI cost controls | Counters in-memory only, not durable/transactional; no consent, no telemetry persistence, no production gates |
| `KM-VIS-001` Crop photo vision | No authenticated Pro endpoint, no daily photo cap, no tenant-safe cache, no storage/consent |
| `KM-MED-002` Native Marathi voice/photo query | TypeScript wrapper exists; no native module, app integration, typed fallback UI, or device testing |
| PostgreSQL migrations/RLS/concurrency | All migrations prepared but **never executed** on a real database |

---

## 5. Pending Features (Not Started)

Per the phased implementation roadmap:

- **Phase 2** — Free value loop and owner-controlled conversion: Global Schedule, `free_usage_counters` IST ledger, owner conversion desk, lead-before-WhatsApp
- **Phase 3** — Pro plots, stage engine, Global schedule: crop stage/DAP engine, plot-specific daily timeline
- **Phase 4** — Partner governance and tenant relationships: Shop/Consultant approval, relationship engine, direct chat
- **Phase 5** — Approved knowledge and safe AI: 16-step knowledge ingestion, RAG engine, safety arbiter, Gemini fallback gated
- **Phase 6** — Advanced advisory and communication: 9-step schedules, chat/media, medicine directory, weather provider, IVR calling
- **Phase 7** — Release verification and operations: UAT, security scans, migration restore rehearsal, owner sign-off

**Stage 2B remains stopped.**

---

## 6. Current Security Concerns

1. **P0**: No authenticated route or database-backed entitlement exists end-to-end. No Free/Pro, partner approval, owner-only, plot, or tenant controls can be enforced end-to-end yet.
2. **P0**: Vision cache lookup precedes usage/disable check and uses only image hash — cached results can bypass the emergency switch/quota.
3. **P0**: AI guardrail is a prompt + escalation phrase check only — does not validate Gemini output against approved sources/dosage limits.
4. **P0**: Model allowlist does not prove zero billing — Gemini Free vs Paid tier eligibility depends on the project, not verified.
5. **P1**: Usage limits default to process memory; check/increment are separate operations; IST date calculation depends on host local time.
6. **Stage 2A API trust boundary**: Migration-owned functions take a Farmer subject argument; theft of the `km_api` database credential would bypass API ownership. Not end-to-end RLS isolation.
7. Logout revocation failure concern pending.
8. No approved live OTP sender or consent wording.

Sources: `docs/IMPLEMENTATION_AUDIT.md`, `docs/STAGE2A_PLOTS_WEATHER.md`, `docs/product-documentation/03_SECURITY_AND_ACCESS_KISAN_MITRA.md`.

---

## 7. Branding Status

- Owner-supplied artwork reads **"Krushi Mitra AI"**; repository/product copy still uses **"Kisan Mitra"**. Name conflict is **BLOCKED owner decision DEC-001**.
- Brand files replaced in working tree (BRAND-001 through BRAND-004): primary logo, variations, symbol, favicons, app icons, splash, colors.
- 142 obsolete PNG variants archived/removed; 57 recovered branding files retained.
- App icon packaging in a real Expo/iOS/Android build is **unverified** (no npm/node_modules, no builds).
- Frontend spec color palette (`#1B5E20` primary, `#F57F17` accent) **contradicts** brand guidelines (`#174C38` primary, `#34785A` secondary, `#C5A451` accent) — inconsistency to resolve.

Sources: `brand/BRAND.md`, `docs/product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md`, `README.md`.

---

## 8. Testing Status

| Check | Status |
|-------|--------|
| Python unit tests | 138 passed, 0 failed (local, no PostgreSQL) |
| PostgreSQL integration tests | 9 guarded tests skipped (no PostgreSQL server, no `psycopg`, localhost:5432 closed) |
| Frontend type checks/builds | Not run — npm registry HTTPS blocked (`EACCES`), no `node_modules`, `tsc`/`next` not found |
| Mobile device tests | Not run |
| CI (GitHub Actions) | Workflow prepared, never run from this working tree |

---

## 9. GitHub Status

- Remote: `https://github.com/swapnilbuilds02/Kisan-Mitra.git` (fetch + push)
- Branch: `main`, up to date with `origin/main` (last commit `6c610e0`)
- **Git writes blocked**: `.git/index.lock` creation denied (Permission denied) — sandbox read-only `.git`
- **GitHub connectivity blocked**: `git ls-remote origin HEAD` cannot connect to `github.com:443`
- **No commits or pushes** for Stage 1F / Stage 2A work
- Working tree has significant uncommitted changes (branding deletions/additions, new backend source, migrations, tests, docs)
- Modified tracked files: `.env.example`, `.gitignore`, `README.md`, `brand/BRAND.md`, `docs/DEVELOPMENT_ROADMAP.md`, `site/holding/README.md`

---

## 10. Documentation Gaps

Required permanent AI handover docs **do not exist**:

| Document | Status |
|----------|--------|
| `AGENTS.md` | **Missing** (mandatory for all future AI models) |
| `docs/MASTER_PROJECT_SPEC.md` | **Missing** |
| `docs/PROJECT_ARCHITECTURE.md` | **Missing** (architecture exists only in product-documentation/) |
| `docs/PROJECT_STATUS.md` | **Missing** |
| `docs/DEVELOPMENT_ROADMAP.md` | Exists (task-ID inventory) |
| `docs/TASK_COMPLETION_LOG.md` | Exists |
| `docs/DECISION_LOG.md` | **Missing** |
| `docs/AI_HANDOVER.md` | **Missing** |
| `docs/KNOWN_ISSUES.md` | **Missing** |

---

## 11. Roadmap Contradictions

| # | Contradiction | Blocker ID |
|---|---------------|------------|
| 1 | PRD mandates "Kisan Mitra"; supplied artwork reads "Krushi Mitra AI" | DEC-001 |
| 2 | Free access to medicine/articles: PRD §8.1 restricts Free; security matrix and frontend grant Free access | DEC-002 |
| 3 | Schema count: architecture says 24 tables, review says 35, document has 48 `CREATE TABLE` statements | — |
| 4 | Color palette: brand guidelines vs frontend spec | — |
| 5 | `KM-AIRT-001` dependency: older roadmap makes it depend on AI features while requiring it before external AI | — |
| 6 | `KM-AICHT-001`: contains a self-reference in dependency chain | — |
| 7 | Plot gating: Stage 2A owner authorization supersedes Pro-only plot gate for plot management only; subscription rules undecided | — |

---

## 12. Pending Owner Decisions

| ID | Decision | Blocker |
|----|----------|---------|
| DEC-001 | Product name: "Kisan Mitra" vs "Krushi Mitra AI" | Blocks UI copy, domain, app-store, legal text |
| DEC-002 | Free visibility of medicine/articles; quota consumption | Blocks API/screens/tests |
| DEC-003 | Delegated Admin permission matrix | Blocks partner approval, Admin credentials |
| DEC-004 | Subscription expiry IST/UTC; failed IVR call quota; former-partner visibility | Blocks schema/worker implementation |
| DEC-005 | Gemini project tier, quota, privacy terms, live model availability | Blocks external AI |

---

## 13. Current Checkpoint

| Item | Value |
|------|-------|
| Phase | Phase 1 (Foundation and security skeleton) — authorized 2026-11-27, IN PROGRESS (~86% source progress, acceptance gates open) |
| Last completed task | P2-PLOT-001 Stage 2A (source implemented 2026-11-27) — PostgreSQL and mobile verification pending |
| Current incomplete task | Phase 1 verification gates (PostgreSQL/RLS/concurrency, frontend builds, OTP delivery, consent, key operations, Git sync) |
| Next approved roadmap task | Phase 2 (Free value loop and owner-controlled conversion) — after Phase 1 gates close |
| Stage 2B | Stopped — do not begin |

---

## 14. Recommended Next Task

Do not begin implementation yet. Immediate priority:

1. Understand the entire existing project — **done**
2. Read the approved roadmap — **done**
3. Verify actual completed work — **done** (source exists but DB/frontend verification pending)
4. Establish the current checkpoint — **done** (this report)
5. Inspect pending branding concerns — name contradiction (DEC-001), color palette contradiction — **need owner decision**
6. Verify Git status and synchronization — **blocked** (`.git/index.lock` permission denied, no GitHub connectivity)
7. Establish the permanent AI handover system — create `AGENTS.md`, `docs/AI_HANDOVER.md`, `docs/KNOWN_ISSUES.md`, `docs/DECISION_LOG.md`, `docs/MASTER_PROJECT_SPEC.md`, `docs/PROJECT_ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`
8. Identify the correct next approved task — Phase 1 gate closure before Phase 2

**No application functionality should be modified during this initial takeover review.** Owner approval is required before beginning significant implementation.
