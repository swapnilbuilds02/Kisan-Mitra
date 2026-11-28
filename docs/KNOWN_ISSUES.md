# Kisan Mitra — Known Issues

**Status:** Register of known security, verification, and operational issues.  
**Evidence basis:** `[VERIFIED]` = confirmed against source; `[REPORTED]` = from previous model reports, not independently re-verified.  
**Rule:** Never remove security checks or tests to make the suite pass. Never claim successful verification when tests were skipped.

---

## 1. Security Issues

### ISS-SEC-001 — Database trust-boundary security concern (Stage 2A) [REPORTED]

**Description:** Migration `0009_farmer_plots` uses narrow migration-owned `SECURITY DEFINER` functions that take a Farmer subject argument supplied by the authenticated server. The runtime database role (`km_api`) can call these functions with a subject argument, so theft of that database credential would bypass API ownership checks. The design is **not** end-to-end RLS isolation.

**Impact:** A compromised `km_api` database credential could read/modify any Farmer's plot data, bypassing the API ownership gate.

**Location:** `backend/migrations/0009_farmer_plots.up.sql`, `backend/app/plots.py`, `docs/STAGE2A_PLOTS_WEATHER.md` (§Data and migration)

**Required remediation:** Stronger database-bound identity proof before treating plot access as end-to-end RLS-isolated. Do not expose the migration-owner/database credential to clients. Do not describe the current design as end-to-end RLS isolation.

**Status:** Open. Migration not executed on a real database, so RLS behavior unverified.

---

### ISS-SEC-002 — Logout revocation failure concern [REPORTED]

**Description:** Previous checkpoint flagged a logout revocation failure concern. Session revocation uses `PostgresSessionStore.revoke(session_id)` backed by PostgreSQL functions from migration 0002, but database behavior (restart persistence, replay-triggered user-wide revocation, concurrent revocation) is unverified.

**Impact:** A logged-out session may remain usable if revocation does not persist or is not checked on every request.

**Location:** `backend/app/postgres_auth.py`, `backend/app/main.py` (logout route), migration `0002_auth_state.up.sql`

**Required remediation:** Execute guarded PostgreSQL auth-state integration test; verify revocation persists across restarts and replay attempts trigger user-wide revocation.

**Status:** Open. Database unverified.

---

### ISS-SEC-003 — AI vision cache bypasses quota/disable check [VERIFIED — code review]

**Description:** Per `IMPLEMENTATION_AUDIT.md` (P0 finding), vision cache lookup precedes the usage/disable check and uses only the image hash as key. A cached result can bypass the emergency switch/quota, and the key omits user, tenant, description, and consent context.

**Impact:** Cached image results could be served after `AI_ENABLED=false` or after quota exhaustion, bypassing entitlement enforcement.

**Location:** `backend/app/services/ai_router.py` (`route_image`)

**Required remediation:** Move usage/disable check before cache lookup; include user/tenant/consent context in cache key; enforce quotas atomically.

**Status:** Open. Helper not wired to production routes yet.

---

### ISS-SEC-004 — AI guardrail is prompt-only [VERIFIED — code review]

**Description:** The AI guardrail is a system prompt plus an escalation-phrase check. It does not validate Gemini output against approved sources, dosage/PHI limits, or crop context.

**Impact:** Farmer-facing chemical advice could contain fabricated dosages if Gemini fallback is enabled before safety arbiter exists.

**Location:** `backend/app/services/ai_router.py` (`_guardrail`)

**Required remediation:** Build safety arbiter (`KM-RAG-002`) validating recommendations against CIB/NRCG rules; block fabricated dosages; require approved-source citations before enabling farmer-facing external AI.

**Status:** Open.

---

### ISS-SEC-005 — Usage limits are in-memory and non-atomic [VERIFIED — code review]

**Description:** `usage_monitor.py` defaults to process memory; check and increment are separate operations; day counters use a rolling 86,400-second TTL depending on host local time. No combined Free three-per-month IST quota or Pro five-photo-per-day entitlement.

**Impact:** Quota can be bypassed across instances or by timezone mismatch; no durable atomic ledger.

**Location:** `backend/app/services/usage_monitor.py` (`_ist_today`, counter logic)

**Required remediation:** Implement durable atomic `free_usage_counters(user_id, IST_month)` ledger with fixed-clock IST boundaries and concurrency-safe check-and-increment (`KM-FREE-002`).

**Status:** Open.

---

### ISS-SEC-006 — No live OTP sender or consent wording [VERIFIED]

**Description:** No approved SMS/OTP sender is configured. Migration 0006 seeds no approved consent document, so farmer onboarding completion fails closed until an operator installs an approved document/version.

**Impact:** OTP delivery and farmer onboarding cannot work in production until configured and approved.

**Location:** `backend/app/farmer_onboarding.py`, `backend/app/auth.py` (OTP provider interface), migration `0006_farmer_onboarding.up.sql`

**Required remediation:** Configure approved SMS sender; install approved consent document/version; owner approval of consent wording (DEC-CONSENT-001).

**Status:** Open. Owner decisions pending.

---

### ISS-SEC-007 — Production key provisioning/rotation unverified [REPORTED]

**Description:** RS256 issuance and public-key overlap for rotation are unit-tested with temporary in-memory keys, but operational key provisioning, public-key distribution, rotation timing, and revocation remain unverified. No private key is committed (correct).

**Impact:** Key rotation at deployment could invalidate existing tokens without a coordinated transition plan.

**Location:** `backend/app/auth.py`, `backend/tests/key_material.py`, `backend/tests/test_rs256_tokens.py`

**Required remediation:** Production key provisioning, public-key distribution, rotation rehearsal before deployment.

**Status:** Open.

---

## 2. Verification Issues

### ISS-VER-001 — PostgreSQL migrations/RLS/concurrency unverified [VERIFIED]

**Description:** All nine migrations (0001–0009) are prepared as SQL files but none have been executed on a real PostgreSQL database. Nine guarded integration tests are skipped because no PostgreSQL server, `psycopg` driver, or localhost:5432 is available.

**Impact:** Schema validity, constraint behavior, RLS enforcement, apply/rollback, and concurrency under the restricted `km_api` role are unproven.

**Required remediation:** Provision a dedicated disposable PostgreSQL 16 instance; set `KM_ALLOW_DISPOSABLE_DB_TESTS=YES` and `KM_TEST_DATABASE_URL`; run the guarded `test_postgres_*.py` files. See `docs/PHASE1_AUTH_DB_VERIFICATION.md`.

**Status:** Blocker ENV-DB-001.

---

### ISS-VER-002 — Frontend builds/type checks unverified [VERIFIED]

**Description:** npm registry HTTPS cannot connect (`EACCES`); no `node_modules`; `tsc` and `next` commands not found. Web and mobile type checks and the Next production build cannot run.

**Impact:** Mobile and web source may contain type errors or build failures that are undetected.

**Required remediation:** Restore npm registry access or provide an approved package cache; run `npm install`, `npm run typecheck`, `npm run build` (web), `npm run typecheck`, `npx expo config` (mobile).

**Status:** Blocker ENV-NPM-001.

---

### ISS-VER-003 — CI never run [VERIFIED]

**Description:** GitHub Actions workflow `.github/workflows/backend-foundation.yml` defines Python, PostgreSQL integration, web-check, and mobile-check jobs but has never been run from this working tree.

**Impact:** No CI evidence that the branch builds and tests pass in a clean environment.

**Required remediation:** Push reviewed branch and run workflow via `gh workflow run` or Actions UI once Git connectivity is restored.

**Status:** Blocker (Git connectivity).

---

## 3. AI / Cost Control Issues

### ISS-AI-001 — Durable atomic quota missing [VERIFIED — code review]

**Description:** `KM-AIRT-001` free-tier cost controls exist as pre-existing helpers (router, model allowlist, in-memory monitor, unit tests) but durable atomic limits, consent, true billing-state verification, admin controls, telemetry persistence, and production gates are missing.

**Impact:** No guaranteed prevention of accidental paid billing or quota overrun in a multi-instance deployment.

**Location:** `backend/app/services/usage_monitor.py`, `ai_router.py`, `gemini_client.py`

**Required remediation:** Complete `KM-AIRT-001` before enabling any feature that calls external AI (`KM-RAG-003`, `KM-MED-002`).

**Status:** Open. Gated by roadmap dependency.

---

### ISS-AI-002 — Gemini tier/billing not verified [VERIFIED — report]

**Description:** The model allowlist does not prove zero billing: Google's same model has Free and Paid tiers, and eligibility/limits depend on the project. No live key or billing-state check was run. The AI cost report's absolute "$0/month" statement is a design assumption, not a verified guarantee.

**Impact:** Enabling Gemini fallback could incur unexpected charges if the project is on a paid tier or exceeds free quotas.

**Required remediation:** Verify Gemini project tier, quota, rate limits, and data terms (DEC-005) before any live call.

**Status:** Owner decision pending (DEC-005).

---

### ISS-AI-003 — No knowledge base or RAG implementation [VERIFIED]

**Description:** No persisted knowledge chunks, embeddings, scoped retrieval, reranking, citation verifier, or 16-step ingestion worker exists. The KB search is an injected `search(query)` protocol with no actor/tenant scope, approval-state filter, or citation contract.

**Impact:** No grounded AI answers can be served; `KM-AI-001`/`KM-AI-002` cannot be enabled.

**Required remediation:** Implement knowledge ingestion, chunking, pgvector indexing, hybrid retrieval, and safety arbiter (Phase 5).

**Status:** Not started.

---

## 4. Git / Synchronization Issues

### ISS-GIT-001 — Git writes blocked [VERIFIED]

**Description:** `.git/index.lock` creation is denied (Permission denied). The `.git` directory is read-only under the managed filesystem policy.

**Impact:** No commits can be created locally; no synchronization with GitHub.

**Required remediation:** Restore filesystem write access to `.git` or move work to a writable clone/worktree.

**Status:** Blocker.

---

### ISS-GIT-002 — GitHub connectivity blocked [VERIFIED]

**Description:** `git ls-remote origin HEAD` cannot connect to `github.com:443`.

**Impact:** No fetch, pull, or push to the authorized repository.

**Required remediation:** Restore HTTPS connectivity to GitHub port 443.

**Status:** Blocker.

---

### ISS-GIT-003 — Uncommitted working-tree changes [VERIFIED]

**Description:** Significant uncommitted changes exist: branding deletions/additions, new backend source (`backend/app/*.py`), migrations (`backend/migrations/`), tests (`backend/tests/`), docs, `web/`, `mobile/`. Modified tracked files: `.env.example`, `.gitignore`, `README.md`, `brand/BRAND.md`, `docs/DEVELOPMENT_ROADMAP.md`, `site/holding/README.md`.

**Impact:** Work is not persisted to version control; risk of loss if the working tree is reset.

**Required remediation:** Once Git write and connectivity are restored, review the full staged diff, preserve unrelated branding changes, verify author email, commit meaningful changes, and push without force.

**Status:** Pending.

---

## 5. Branding / Specification Issues

### ISS-BRAND-001 — Product name contradiction [VERIFIED]

**Description:** PRD and documentation review mandate "Kisan Mitra"; supplied primary artwork reads "Krushi Mitra AI".

**Impact:** Blocks final UI copy, domain, app-store, and legal text until owner decides (DEC-001).

**Location:** `docs/product-documentation/01_PRD_KISAN_MITRA.md`, `brand/KISAN-MITRA-BRAND/01-Primary-Logo/`, `brand/BRAND.md`

**Status:** Owner decision pending (DEC-001).

---

### ISS-BRAND-002 — Color palette contradiction [VERIFIED]

**Description:** Brand guidelines (`brand/BRAND.md`): Deep Forest `#174C38` primary, Agricultural Green `#34785A` secondary, Harvest Gold `#C5A451` accent (<5%). Frontend spec (`04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` §1.1): Primary Green `#1B5E20`, Harvest Gold `#F57F17`.

**Impact:** Inconsistent design tokens between brand rules and frontend specification.

**Location:** `brand/BRAND.md` §Colours; `04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` §1.1

**Status:** Open — needs reconciliation.

---

### ISS-BRAND-003 — App icon packaging unverified [REPORTED]

**Description:** App icon and splash assets exist (1024×1024 masters resolved), but no Expo/iOS/Android build exists, so launcher packaging and device rendering are unverified.

**Status:** Open — pending mobile build (ENV-NPM-001).

---

## 6. Other Previously Identified Issues

| ID | Summary | Status |
|----|---------|--------|
| ISS-SCHEMA-001 | Schema table count conflict (24 vs 35 vs 48 `CREATE TABLE` statements) | Open (CON-003) |
| ISS-KM-AIRT-001 | `KM-AIRT-001` dependency conflict in older roadmap | Open (CON-005) |
| ISS-KM-AICHT-001 | `KM-AICHT-001` self-referential dependency | Open (CON-006) |
| ISS-SCHEDULE-001 | Schedule vs 16-step knowledge pipeline confusion | Open (CON-007) |
| ISS-MED-002 | Native Marathi voice/photo query: no native module, app integration, typed fallback UI, device testing | Open (partial) |
| ISS-VIS-001 | Crop photo vision: no authenticated Pro endpoint, daily cap, tenant-safe cache, storage/consent | Open (partial) |
| ISS-HOLDING-001 | Holding-site production notes disagree (Vercel snapshot vs nothing deployed); `vercel.json` disallows scripts while `_headers` permits them | Open — verify actual host before site changes |

---

## 7. New Issues from External Reference Review

| ID | Summary | Status |
|----|---------|--------|
| ISS-ENV-NPM-002 | npm registry blocked; Archify project-level skill installation via `npx skills add` could not be tested | Open — ENV-NPM-001 |
| ISS-ENV-WIN-001 | Archify browser-check fails on 2/6 diagrams due to Windows temp directory cleanup (EPERM) and Chrome process not exiting | Open — environment limitation; HTML artifacts valid |
| ISS-FREELLAPI-001 | FreeLLMAPI is single-user only — no multi-tenant auth, no subscription entitlement, no RAG, no dosage validation | Open — not suitable for production; adapter would be disabled by default |
| ISS-FREELLAPI-002 | FreeLLMAPI aggregate "10.1B tokens/month" is not available to any single user; free tiers degrade through the day | Open — do not assume capacity |
| ISS-ARCHIFY-001 | Archify PDF installation guide (`Archify_Installation_Guide (1).pdf`) not present in local references directory | Open — documentation referenced but not available |
| ISS-TRACEN-001 | TRACEN Vibe Coding Trail PDF not present in local references directory | Open — concepts mapped from task list instead of PDF |

---

## 8. Issue Triaging Guidance

- **P0 security issues** (ISS-SEC-001 to ISS-SEC-005): Must be resolved before any farmer-facing feature is enabled or any production deployment.
- **Verification blockers** (ISS-VER-001 to ISS-VER-003): Must be resolved before Phase 1 gate closure.
- **AI gating** (ISS-AI-001 to ISS-AI-003): `KM-AIRT-001` must be complete before any external AI call is enabled in any environment.
- **Git blockers** (ISS-GIT-001 to ISS-GIT-003): Must be resolved before work can be persisted and synchronized.
