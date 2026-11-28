# Kisan Mitra — AI Handover

**Purpose:** Sufficient information for another AI model to continue development without access to previous conversations.  
**Status:** Current as of takeover review (2026-11-28).  
**Mandatory:** The next model MUST read `AGENTS.md` and this file, then verify the checkpoint against actual source before making changes.

---

## 1. Project at a Glance

| Property | Value |
|----------|-------|
| Product | Kisan Mitra AI (formerly DrakshGuru); artwork reads "Krushi Mitra AI" — name conflict pending DEC-001 |
| Owner | Swapnil Pawar (jeeswapnil002@gmail.com) |
| Authorized repo | `https://github.com/swapnilbuilds02/Kisan-Mitra.git` (branch `main`, up to date with `origin/main`) |
| Working directory | `D:\Kisan Mitra APP` |
| External reference | `D:\Kisan-Mitra-References\build-your-own-x` (indexed in `docs/EXTERNAL_ENGINEERING_REFERENCES.md`) |
| Recovery evidence | `RECOVERY_WORKSPACE/` — do not `git add .` while this folder is inside the repo; preserve all recovery evidence |

---

## 2. Last Completed Task

**P2-PLOT-001 — Stage 2A Farmer plots and weather context** (source implemented 2026-11-27)

- Authenticated create/list/detail/update/select/archive/weather routes for active Farmers
- Farmer-only role gates; ownership-scoped plot repository
- Additive migration `0009_farmer_plots` (plot table, location/area constraints, one-selected-plot partial unique index, serialized selection/archive, audit events)
- Opt-in precise coordinates; injected weather provider protocol; per-Farmer/plot/location cache; stale/unavailable fallback (returns `unavailable`, no fabricated measurements)
- Mobile Farmer plot form and switcher; partner access fails closed
- **138 Python tests passed, 9 guarded PostgreSQL skipped, 0 failed** on 2026-11-27 `[REPORTED]`
- **Remaining:** PostgreSQL migration/RLS/concurrency verification, mobile type/build/device checks, live weather disabled (no provider configured)

Key files: `backend/app/main.py` (plot routes), `backend/app/plots.py`, `backend/app/weather.py`, `backend/migrations/0009_farmer_plots.{up,down}.sql`, `backend/tests/test_farmer_plots.py`, `backend/tests/test_postgres_plot_integration.py`, `mobile/src/` (plot manager), `docs/STAGE2A_PLOTS_WEATHER.md`.

---

## 3. Current Task

**Phase 1 gate closure** — acceptance gates are open. Work remaining:

| Gate | Required evidence | Blocker |
|------|-------------------|---------|
| PostgreSQL / RLS / concurrency verification | Run guarded integration tests (`test_postgres_*.py`) on a disposable `km_test_*` database | No PostgreSQL server, no `psycopg`, localhost:5432 closed (ENV-DB-001) |
| Frontend type checks & builds | `npm install`, `npm run typecheck`, `npm run build` (web), `npm run typecheck`, `npx expo config` (mobile) | npm registry HTTPS blocked; no `node_modules`; `tsc`/`next` not found (ENV-NPM-001) |
| Approved OTP delivery | Configure and test an approved SMS sender | No sender configured; live SMS unauthorized |
| Approved consent wording | Install approved consent document/version; migration 0006 fails closed until seeded | Owner decision (DEC-CONSENT-001) |
| Production key operations | Key provisioning, public-key distribution, rotation rehearsal | Not verified |
| Git synchronization | Commit and push reviewed diff | `.git/index.lock` permission denied; GitHub:443 unreachable |

---

## 4. Next Approved Task

After Phase 1 gates close: **Phase 2 — Free value loop and owner-controlled conversion.**

- Global Schedule data, deterministic DAP lookup, atomic `free_usage_counters(user_id, IST_month)` ledger shared by schedule search and Global-KB-only text chat
- Owner-assisted conversion: `upgrade_enquiries` lead, `wa.me` handoff, lead desk, manual payment classification, direct Pro activation, anniversary subscription engine
- Free Schedule Search, limited KB chat, remaining-uses badge, Pro intercept, Marathi upgrade page (no public price)
- Tests: concurrency, IST month rollover, no quota charge on validation failures, no Gemini for Free, lead-before-WhatsApp ordering, 7-day dedup, leap-day/early/lapsed renewal

**Do not start Stage 2B.** Do not implement Phase 2 until Phase 1 gates close and owner approves.

---

## 5. External Reference Artifacts (This Review)

| Artifact | Path | Key Finding |
|----------|------|-------------|
| AI Provider Evaluation | `docs/AI_PROVIDER_EVALUATION.md` | FreeLLMAPI evaluated (MIT, commit `abbdc52`); not suitable for production; adapter disabled by default |
| System Design Standards | `docs/SYSTEM_DESIGN_STANDARDS.md` | All 20 TRACEN concepts mapped to roadmap |
| Architecture Diagrams | `docs/architecture-diagrams/` | 6 HTML diagrams generated (4/6 pass all gates incl. browser-check) |
| External Eng References (updated) | `docs/EXTERNAL_ENGINEERING_REFERENCES.md` | Added FreeLLMAPI (§M) and Archify (§N) sections |
| AGENTS.md (updated) | `AGENTS.md` | References all authoritative documents |
| Branding Status | `docs/BRANDING_STATUS.md` | Name contradiction (DEC-001), colour palette contradiction, icon packaging unverified |


---

## 5. Relevant Source Locations

### Backend (`backend/`)
- `app/main.py` — FastAPI app factory; all auth, onboarding, partner, admin, plot routes
- `app/auth.py` — RS256 JWT, AuthWorkflow, OTP/password/login flows
- `app/identity.py` — IdentityStore, Actor, Role, normalize_mobile
- `app/postgres_auth.py` — PostgresSessionStore (durable sessions/OTP)
- `app/credentials.py` — PostgresCredentialStore (scrypt credentials)
- `app/passwords.py` — scrypt hashing/validation
- `app/farmer_onboarding.py` — Farmer registration/complete/profile/consent
- `app/partners.py` — Shop/Consultant store (registration, status, profile, decisions)
- `app/admin_provision.py` — Admin preparation/activation/reauth
- `app/plots.py` — PostgresPlotStore (create/list/get/update/select/archive)
- `app/weather.py` — WeatherContextService (injected provider, cache, stale/unavailable)
- `app/services/ai_router.py` — AIRouter (KB-first, Gemini fallback, escalation) [helper only]
- `app/services/gemini_client.py` — free-tier Gemini client [helper only]
- `app/services/image_pipeline.py` — image validation/resize/compression/hash [helper only]
- `app/services/usage_monitor.py` — in-memory quota/rate-limit monitor [helper only]

### Migrations (`backend/migrations/`)
- `0001_identity_foundation` — users, farmer_profiles, partner_profiles, audit_logs
- `0002_auth_state` — sessions, consumed refresh, OTP challenge/request, security events
- `0003_farmer_identity` — admin preparation, OTP claim functions
- `0004_password_credentials` — password credential table
- `0005_otp_recovery` — OTP purposes, identity binding, reset authorizations
- `0006_farmer_onboarding` — profile completion, onboarding authorization, consent records
- `0007_partner_applications` — Shop/Consultant applications, consents, decision history, session revocation
- `0008_admin_identity` — Admin provisioning, onboarding authorization, persistent Admin counters
- `0009_farmer_plots` — farmer_plots table, constraints, unique selection index

### Tests (`backend/tests/`)
- Unit: `test_api_foundation.py`, `test_auth_workflow.py`, `test_rs256_tokens.py`, `test_password_login.py`, `test_password_recovery.py`, `test_farmer_onboarding.py`, `test_partner_applications.py`, `test_admin_auth.py`, `test_farmer_plots.py`, `test_ai_router.py`, `test_gemini_client.py`, `test_image_pipeline.py`, `test_usage_monitor.py`
- Guarded PostgreSQL integration: `test_postgres_identity_integration.py`, `test_postgres_auth_integration.py`, `test_postgres_farmer_integration.py`, `test_postgres_password_integration.py`, `test_postgres_recovery_integration.py`, `test_postgres_onboarding_integration.py`, `test_postgres_partner_integration.py`, `test_postgres_admin_integration.py`, `test_postgres_plot_integration.py`
- Guard: `postgres_test_guard.py`, `test_postgres_test_guard.py`, `key_material.py`, `conftest.py`

### Mobile (`mobile/`)
- `src/auth/client.ts` — typed API client with Expo SecureStore refresh rotation
- `src/auth/` — auth screens (bilingual), `AuthScreen.tsx`
- Plot manager (Stage 2A source)
- `App.tsx`, `app.json`, `package.json`, `tsconfig.json`
- `src/services/nativeSpeech.ts` — native Marathi speech wrapper [native module not linked]

### Web (`web/`)
- `app/` — Next.js App Router (owner login, partner decisions, admin overview)
- `lib/server-auth.ts` — server auth, HttpOnly cookies, CSRF/origin checks, Admin reauth
- `package.json`, `tsconfig.json`, `next-env.d.ts`

### Docs (`docs/`)
- `PHASED_IMPLEMENTATION_ROADMAP.md` — approved execution order & gates
- `DEVELOPMENT_ROADMAP.md` — task-ID & dependency inventory
- `TASK_COMPLETION_LOG.md` — completed/in-progress/pending/blocked history
- `IMPLEMENTATION_AUDIT.md` — code-verified status & gaps
- `MASTER_PROJECT_SPEC.md` — consolidated vision, requirements, roles, policies
- `PROJECT_ARCHITECTURE.md` — implemented vs planned architecture
- `PROJECT_STATUS.md` — phase-wise completion & verification status
- `DECISION_LOG.md` — approved decisions, contradictions, pending decisions
- `KNOWN_ISSUES.md` — issue register
- `EXTERNAL_ENGINEERING_REFERENCES.md` — build-your-own-x index
- `INITIAL_TAKEOVER_REPORT.md` — full takeover report
- `product-documentation/` — PRD, architecture, security, frontend, feature tickets, final review
- `AGRICULTURAL_INTELLIGENCE_IMPLEMENTATION_PLAN.md` — AI track plan
- `STAGE2A_PLOTS_WEATHER.md` — Stage 2A record
- `brand/BRAND.md` — brand rules

---

## 6. Test Baseline

| Check | Result |
|-------|--------|
| `python -m pytest backend/tests -q` | 138 passed, 9 skipped (guarded PostgreSQL), 0 failed (local, 2026-11-27) `[VERIFIED]` |
| `python -m compileall -q backend` | Passed `[VERIFIED]` |
| `git diff --check` | Passed `[VERIFIED]` |
| PostgreSQL integration tests | 9 skipped — no server/driver `[VERIFIED — not run]` |
| Frontend type checks / builds | Not run — npm blocked `[VERIFIED — not run]` |
| CI | Workflow prepared, never run `[VERIFIED — not run]` |

Integration test procedure (when PostgreSQL is available): set `KM_ALLOW_DISPOSABLE_DB_TESTS=YES` and `KM_TEST_DATABASE_URL` to a dedicated `km_test_*` database, then run the eight guarded `test_postgres_*.py` files. See `docs/PHASE1_AUTH_DB_VERIFICATION.md`.

---

## 7. Git Status

| Item | Status |
|------|--------|
| Remote | `https://github.com/swapnilbuilds02/Kisan-Mitra.git` |
| Branch | `main`, up to date with `origin/main` (last commit `6c610e0`) |
| Git writes | BLOCKED — `.git/index.lock` creation denied (Permission denied) |
| GitHub connectivity | BLOCKED — cannot connect to `github.com:443` |
| Commits/pushes pending | Yes — significant uncommitted changes (branding, backend, migrations, tests, docs) |
| Author | Swapnil <jeeswapnil002@gmail.com> |

**Do not** run `git add .` while `RECOVERY_WORKSPACE/` is inside the repo. Stage specific approved paths only. Do not force push. Do not commit secrets, `.env`, database dumps, or recovery scripts.

---

## 8. Known Blockers

| Blocker | Detail | Document |
|---------|--------|----------|
| ENV-DB-001 | No PostgreSQL server/driver; localhost:5432 closed | `KNOWN_ISSUES.md`, `PHASE1_AUTH_DB_VERIFICATION.md` |
| ENV-NPM-001 | npm registry HTTPS blocked; no `node_modules`; no frontend builds | `KNOWN_ISSUES.md`, `PHASE1_AUTH_DB_VERIFICATION.md` |
| Git write blocked | `.git/index.lock` permission denied | `KNOWN_ISSUES.md` |
| GitHub unreachable | Port 443 blocked | `KNOWN_ISSUES.md` |
| DEC-001 to DEC-005 | Five pending owner decisions | `DECISION_LOG.md`, `PROJECT_STATUS.md` |
| Stage 2B stopped | Owner directive — do not begin | `AGENTS.md`, `PHASED_IMPLEMENTATION_ROADMAP.md` |

---

## 9. Instructions for the Next AI Model

1. **Read first:** `AGENTS.md`, then this file (`AI_HANDOVER.md`), then `MASTER_PROJECT_SPEC.md`, `PROJECT_ARCHITECTURE.md`, `PROJECT_STATUS.md`, `DECISION_LOG.md`, `KNOWN_ISSUES.md`.
2. **Verify checkpoint:** Confirm the current phase, last completed task, and open gates against actual source in `backend/app/`, `backend/migrations/`, `backend/tests/`, `mobile/src/`, `web/app/`. Do not trust reports blindly.
3. **Follow the workflow:** Read roadmap → verify completed work → inspect source → identify problem → consult official docs → consult relevant `EXTERNAL_ENGINEERING_REFERENCES.md` resource → plan → implement → test → document → commit/push when authorized → update handover.
4. **Respect priorities:** Owner decisions > master spec > roadmap > existing code > official docs > external tutorials. External tutorials never override requirements.
5. **Do not:** replace PostgreSQL/Redis/FastAPI/React Native/Next.js/Git with educational implementations; blindly copy tutorial code; invent agricultural dosages/business policies/pricing; remove security checks or tests; modify historical migrations without review; perform destructive Git operations; force push; claim verification when tests were skipped.
6. **Git:** Stage specific paths only (never `git add .` while `RECOVERY_WORKSPACE/` is present). Do not commit secrets, `.env`, database dumps, recovery scripts, or credentials. Push only when Git write and GitHub connectivity are restored and authorized.
7. **Stage 2B is stopped.** Do not begin it. Phase 1 gates must close first; then Phase 2.
8. **Pending owner decisions (DEC-001 to DEC-005):** Do not assume approvals. If a task depends on a pending decision, flag it as blocked and wait for owner direction.
9. **Update `TASK_COMPLETION_LOG.md` after each task** (name, description, implementation, files, tests/results, actual completion date, status) and `AI_HANDOVER.md` with the latest checkpoint.
