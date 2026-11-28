# Kisan Mitra — AI Agent Instructions

## Mandatory first step — read before making any change

Before implementing or modifying anything in this repository, you MUST:

1. **Read the project documentation** in `docs/`:
   - `docs/MASTER_PROJECT_SPEC.md` — consolidated vision, functional requirements, user roles, business policies, AI requirements, pending owner decisions (authoritative spec summary)
   - `docs/PROJECT_ARCHITECTURE.md` — implemented vs planned architecture, backend/mobile/web/database/AI components
   - `docs/PROJECT_STATUS.md` — phase-wise completion, completed/partial/pending features, verification status, current checkpoint
   - `docs/DECISION_LOG.md` — approved owner decisions, superseded requirements, unresolved contradictions, pending decisions
   - `docs/AI_HANDOVER.md` — last completed task, current task, next approved task, source locations, test baseline, Git status, known blockers, instructions for the next AI model
   - `docs/KNOWN_ISSUES.md` — security, verification, AI, Git, and branding issue register
   - `docs/BRANDING_STATUS.md` — unresolved visual branding, product naming, and colour palette concerns
   - `docs/AI_PROVIDER_EVALUATION.md` — FreeLLMAPI evaluation, provider eligibility matrix, proposed adapter (disabled by default)
   - `docs/SYSTEM_DESIGN_STANDARDS.md` — TRACEN concept mapping, rate limiting, caching, circuit breakers, idempotency, timeouts, retries, cron jobs
   - `docs/architecture-diagrams/README.md` — architecture diagram index (6 generated HTML diagrams)
   - `docs/PHASED_IMPLEMENTATION_ROADMAP.md` — approved execution order and phase gates
   - `docs/DEVELOPMENT_ROADMAP.md` — task-ID and dependency inventory
   - `docs/TASK_COMPLETION_LOG.md` — completed, in-progress, pending, and blocked tasks
   - `docs/IMPLEMENTATION_AUDIT.md` — code-verified status and gaps
   - `docs/EXTERNAL_ENGINEERING_REFERENCES.md` — external technical reference index (build-your-own-x, FreeLLMAPI, Archify)
   - `docs/INITIAL_TAKEOVER_REPORT.md` — current checkpoint and open items

2. **Verify the current checkpoint** against the actual source code:
   - Backend: `backend/app/`, `backend/migrations/`, `backend/tests/`
   - Mobile: `mobile/src/`, `mobile/App.tsx`
   - Web: `web/app/`, `web/lib/`
   - Architecture diagrams: `docs/architecture-diagrams/`
   - Do not trust completion reports blindly; confirm against source.

3. **Do not modify application functionality** during an initial takeover review unless explicitly authorized by the owner.

## External engineering reference repositories

Three curated technical reference repositories are available for engineering knowledge:

| Repository | Local Path | License | Index Doc |
|------------|-----------|---------|-----------|
| build-your-own-x | `D:\Kisan-Mitra-References\build-your-own-x` | CC0 (index) | `docs/EXTERNAL_ENGINEERING_REFERENCES.md` §L |
| FreeLLMAPI | `D:\Kisan-Mitra-References\freellmapi` | MIT | `docs/EXTERNAL_ENGINEERING_REFERENCES.md` §M |
| Archify | `D:\Kisan-Mitra-References\archify` | Apache-2.0 | `docs/EXTERNAL_ENGINEERING_REFERENCES.md` §N |

**Priority order:** Owner decisions > master spec > approved roadmap > existing code > official docs > external tutorials.

### Usage rules (all external references)

1. Owner decisions > master spec > approved roadmap > existing code > official docs > external tutorials.
2. External tutorials are supplementary knowledge only; they never override owner requirements.
3. Do not replace PostgreSQL, Redis, FastAPI, React Native, Next.js, or Gemini with educational implementations.
4. Do not build our own database, web server, or programming language unnecessarily.
5. Do not blindly copy tutorial code into production.
6. Verify each upstream tutorial license before reusing code.
7. Do not upload Kisan Mitra code, credentials, or farmer-facing knowledge base content to external services.
8. Do not execute downloaded scripts or install dependencies without reviewing them.
9. Do not load the entire external reference collection into the model context for every task; consult only relevant resources.
10. FreeLLMAPI is for personal experimentation only — not approved for production farmer-facing AI. Any adapter must be disabled by default (`FREELLAPI_ENABLED=false`).

## Strict development rules (never violate)

- Always follow the approved roadmap (`docs/PHASED_IMPLEMENTATION_ROADMAP.md`).
- Before creating a new module, search for existing implementations first.
- Never rebuild an existing working feature unnecessarily.
- Never create duplicate authentication systems, API endpoints, or database structures.
- Never replace approved architecture without owner authorization.
- Never delete files without understanding their purpose.
- Never remove security checks or tests to make the suite pass.
- Never invent agricultural recommendations, chemical dosages, business policies, or subscription prices.
- Never change approved branding without permission.
- Never expose confidential information or credentials.
- Never modify historical migrations without reviewing migration compatibility.
- Never perform destructive Git operations or force push.
- Never claim successful verification when tests were skipped.

## Task execution workflow (every task)

1. Read the roadmap and latest handover checkpoint.
2. Verify completed and incomplete work.
3. Inspect relevant existing source code.
4. Identify dependencies, risks, and security implications.
5. Prepare a focused implementation plan.
6. Obtain owner approval for significant architectural, security, business, or destructive changes.
7. Implement only the approved task.
8. Run relevant tests and validation checks.
9. Review the complete Git diff.
10. Update project documentation.
11. Create meaningful Git commits and safely push when authorized.
12. Update AI handover documentation with the latest checkpoint.

## Current checkpoint (as of takeover review)

- **Phase:** Phase 1 (Foundation and security skeleton) — IN PROGRESS, acceptance gates open
- **Last completed task:** P2-PLOT-001 Stage 2A (source implemented, PostgreSQL/mobile verification pending)
- **Next approved task:** Phase 1 gate closure (PostgreSQL/RLS/concurrency verification, frontend builds, OTP delivery, consent, Git sync) — then Phase 2
- **Stage 2B:** STOPPED — do not begin
- **Git:** writes blocked in this workspace (`.git/index.lock` permission denied); GitHub connectivity blocked
- **Blocked owner decisions:** DEC-001 (product name), DEC-002 (Free medicine/article access), DEC-003 (delegated Admin powers), DEC-004 (subscription expiry rules), DEC-005 (Gemini tier/terms)

## Test baseline

- `python -m pytest backend/tests -q` → 138 passed, 9 skipped (guarded PostgreSQL), 0 failed (local, 2026-11-27)
- PostgreSQL integration tests: NOT executed (no PostgreSQL server/driver available)
- Frontend builds: NOT executed (npm registry blocked, no node_modules)
