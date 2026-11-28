# Kisan Mitra — Project Status

**Status:** Current checkpoint record.  
**Evidence basis:** Verified facts marked `[VERIFIED]`; previous model reports marked `[REPORTED]` (not independently re-verified); proposed/planned marked `[PLANNED]`.

---

## 1. Current Development Checkpoint

| Item | Value |
|------|-------|
| Phase | Phase 1 — Foundation and security skeleton `[IN PROGRESS]` |
| Phase authorized | 2026-11-27 |
| Source progress | ~86% (planning estimate, not an acceptance result) |
| Acceptance gates | OPEN — PostgreSQL/RLS/concurrency verification, frontend builds, OTP delivery, consent, key operations, Git sync |
| Last completed task | P2-PLOT-001 Stage 2A (Farmer plots + weather context) — source implemented 2026-11-27 `[REPORTED]` |
| Next approved task | Phase 1 gate closure → then Phase 2 (Free value loop and owner-controlled conversion) |
| Stage 2B | STOPPED — do not begin `[OWNER DIRECTIVE]` |
| Overall project completion | ~22% by planned phase scope (planning estimate, not an acceptance result) `[REPORTED]` |

---

## 2. Phase-wise Progress

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 0 | Product/architecture decisions (identity, commercial, data, traceability) | Pending owner decisions DEC-001 to DEC-005 `[PENDING]` |
| Phase 1 | Foundation and security skeleton (auth, sessions, OTP, onboarding, partners, admin, plots, weather) | Source largely written; gates open `[IN PROGRESS]` |
| Phase 2 | Free value loop: Global Schedule, `free_usage_counters` IST ledger, owner conversion desk, lead-before-WhatsApp | `[PENDING]` |
| Phase 3 | Pro plots (superseded partially by Stage 2A), crop stage engine, Global Schedule, personalized schedules | `[PENDING]` |
| Phase 4 | Partner governance: Shop/Consultant approval, tenant relationships, direct chat | `[PENDING]` |
| Phase 5 | Approved knowledge: 16-step ingestion, RAG engine, safety arbiter, Gemini fallback gated | `[PENDING]` |
| Phase 6 | Schedules, chat/media, medicine directory, weather provider, IVR calling | `[PENDING]` |
| Phase 7 | Release verification: UAT, security scans, migration restore, owner sign-off | `[PENDING]` |

---

## 3. Completed Features

| Feature | Status | Evidence |
|---------|--------|----------|
| RS256 JWT token contract (issue/verify, issuer/audience, key IDs, algorithm denial) | Implemented + locally tested | `backend/app/auth.py`; 95 tests pass `[VERIFIED]` |
| Farmer OTP claim + admin pre-registration | API tested locally; DB unverified | `backend/app/auth.py`, `identity.py` `[REPORTED]` |
| Durable sessions & OTP limits | Code written; DB unverified | `backend/app/postgres_auth.py`, migration 0002 `[REPORTED]` |
| Password login / recovery / change | Local API tested; DB unverified | `backend/app/passwords.py`, `credentials.py`, migrations 0004–0005 `[REPORTED]` |
| Shop/Consultant application & approval | Local API tested; DB unverified | `backend/app/partners.py`, migration 0007 `[REPORTED]` |
| Restricted Admin activation / password / OTP | Local API tested; DB unverified | `backend/app/admin_provision.py`, migration 0008 `[REPORTED]` |
| Farmer profile onboarding & consent | Local API tested; DB unverified | `backend/app/farmer_onboarding.py`, migration 0006 `[REPORTED]` |
| Farmer plots + weather context (Stage 2A) | Source implemented; DB/mobile unverified | `backend/app/plots.py`, `weather.py`, migration 0009 `[REPORTED]` |
| AI cost controls (router, monitor, client, image pipeline) | Partial pre-existing helpers | `backend/app/services/` `[VERIFIED — files exist]` |
| Branding replacement (Krushi Mitra AI artwork) | Working tree only | `brand/KISAN-MITRA-BRAND/` `[VERIFIED — files exist]` |
| Holding website (static) | Files present; not verified live | `site/holding/` `[VERIFIED — files exist]` |

**Test baseline:** `python -m pytest backend/tests -q` → **138 passed, 9 skipped (guarded PostgreSQL), 0 failed** on 2026-11-27 `[VERIFIED]`.

---

## 4. Partially Implemented Features

| Feature | Gap |
|---------|-----|
| `KM-AIRT-001` Free-tier AI cost controls | Counters in-memory only; not durable/transactional; no consent, no telemetry persistence, no production gates |
| `KM-VIS-001` Crop photo vision | No authenticated Pro endpoint, no daily photo cap, no tenant-safe cache, no storage/consent |
| `KM-MED-002` Native Marathi voice/photo query | TypeScript wrapper exists; no native module, app integration, typed fallback UI, device testing |
| PostgreSQL migrations / RLS / concurrency | All migrations prepared but never executed on a real database |

---

## 5. Pending Features (Not Started)

Phases 2–7 per `docs/PHASED_IMPLEMENTATION_ROADMAP.md` and `docs/DEVELOPMENT_ROADMAP.md`:

- Phase 2: Free loop, Global Schedule, quota ledger, owner conversion desk
- Phase 3: Pro plots, crop stage engine, personalized schedules
- Phase 4: Partner governance, tenant relationships, direct chat
- Phase 5: Knowledge ingestion (16-step), RAG engine, safety arbiter, Gemini fallback gated
- Phase 6: 9-step schedules, chat/media, medicine directory, weather provider, IVR calling
- Phase 7: Release verification, UAT, security scans, owner sign-off

---

## 6. Verification Status

| Check | Result |
|-------|--------|
| Python unit tests | 138 passed, 0 failed `[VERIFIED]` |
| PostgreSQL integration tests | 9 guarded skipped — no PostgreSQL server, no `psycopg` driver, localhost:5432 closed `[VERIFIED — skipped]` |
| Frontend type checks / builds | Not run — npm registry blocked (`EACCES`), no `node_modules`, `tsc`/`next` not found `[VERIFIED — not run]` |
| Mobile device tests | Not run |
| CI (GitHub Actions) | Workflow prepared; never run from this working tree `[VERIFIED — not run]` |
| Production key provisioning / rotation | Not verified `[VERIFIED — not run]` |
| Live OTP sender | Not configured `[VERIFIED — not run]` |
| Approved consent wording | Not seeded `[VERIFIED — not run]` |

---

## 7. Git / Synchronization Status

| Item | Status |
|------|--------|
| Remote | `https://github.com/swapnilbuilds02/Kisan-Mitra.git` (fetch + push) `[VERIFIED]` |
| Branch | `main`, up to date with `origin/main` (last commit `6c610e0`) `[VERIFIED]` |
| Git writes | BLOCKED — `.git/index.lock` creation denied (Permission denied) `[VERIFIED]` |
| GitHub connectivity | BLOCKED — `git ls-remote origin HEAD` cannot connect to `github.com:443` `[VERIFIED]` |
| Commits/pushes for Stage 1F/2A | None `[VERIFIED]` |
| Uncommitted working-tree changes | Significant (branding deletions/additions, backend source, migrations, tests, docs) `[VERIFIED]` |

---

## 8. Blocked Owner Decisions

| ID | Decision | Needed to unblock |
|----|----------|-------------------|
| DEC-001 | Product name: "Kisan Mitra" vs "Krushi Mitra AI" | UI copy, domain, app store, legal text |
| DEC-002 | Free medicine/articles access; quota consumption | API/screens/tests |
| DEC-003 | Delegated Admin permission matrix | Partner approval, Admin credentials |
| DEC-004 | Subscription expiry IST/UTC; failed IVR quota; former-partner visibility | Schema/worker implementation |
| DEC-005 | Gemini tier, quota, privacy, live model availability | External AI enablement |

---

## 9. Environment Blockers

| Blocker | Detail |
|---------|--------|
| ENV-DB-001 | Local PostgreSQL/`psycopg` unavailable; three migration/RLS integration tests skipped |
| ENV-NPM-001 | npm registry HTTPS cannot connect; web/mobile dependency fetches fail; no `node_modules` |

---

## 10. New Documentation & Artifacts (This Review)

| Artifact | Path | Status |
|----------|------|--------|
| Master Project Specification | `docs/MASTER_PROJECT_SPEC.md` | Created |
| Project Architecture | `docs/PROJECT_ARCHITECTURE.md` | Created |
| Project Status | `docs/PROJECT_STATUS.md` | Created |
| Decision Log | `docs/DECISION_LOG.md` | Created |
| AI Handover | `docs/AI_HANDOVER.md` | Created |
| Known Issues | `docs/KNOWN_ISSUES.md` | Created |
| AI Provider Evaluation | `docs/AI_PROVIDER_EVALUATION.md` | Created |
| System Design Standards | `docs/SYSTEM_DESIGN_STANDARDS.md` | Created |
| Branding Status | `docs/BRANDING_STATUS.md` | Created |
| External Eng References (updated) | `docs/EXTERNAL_ENGINEERING_REFERENCES.md` | Updated |
| AGENTS.md (updated) | `AGENTS.md` | Updated |
| Architecture Diagrams | `docs/architecture-diagrams/` | 6 HTML diagrams generated |
| Diagram Index | `docs/architecture-diagrams/README.md` | Created |

---

## 11. Known Issues

See `docs/KNOWN_ISSUES.md` for the full register (trust-boundary security concern, logout revocation, AI quota/cache, PostgreSQL verification, frontend build, GitHub sync, branding contradictions).
