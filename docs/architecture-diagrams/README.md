# Kisan Mitra — Architecture Diagrams

**Directory:** `docs/architecture-diagrams/`  
**Tool:** Archify v3.3.2 (Apache-2.0)  
**Reference:** `D:\Kisan-Mitra-References\archify` (commit `b42e7d7`)  
**Generated:** 2026-11-28  
**Status:** Source-backed interactive HTML diagrams. Every component labeled as implemented/verified, implemented/unverified, partial, planned, or blocked.

---

## Diagram Index

| # | Diagram | Type | File | Gates | Status |
|---|---------|------|------|-------|--------|
| 1 | Complete Current System Architecture | Architecture | `01-current-system-architecture.html` | validate ✓ · deliver ✓ · check ✓ · browser-check ⚠️ | Generated — browser-check limited by Windows temp cleanup (env) |
| 2 | Farmer Authentication & Account Claim | Sequence | `02-farmer-auth-sequence.html` | validate ✓ · deliver ✓ · check ✓ · browser-check ✓ | Verified |
| 3 | Database Trust Boundaries & Tenant Isolation | Architecture | `03-database-trust-boundaries.html` | validate ✓ · deliver ✓ · check ✓ · browser-check ✓ | Verified |
| 4 | Shop & Consultant Approval Lifecycle | Lifecycle | `04-partner-approval-lifecycle.html` | validate ✓ · deliver ✓ · check ✓ · browser-check ✓ | Verified |
| 5 | Admin Authentication & Authorization | Sequence | `05-admin-auth-sequence.html` | validate ✓ · deliver ✓ · check ✓ · browser-check ⚠️ | Generated — Chrome temp profile cleanup (env) |
| 6 | Implemented vs Planned Components | Tree | `06-implemented-vs-planned.html` | validate ✓ · deliver ✓ · check ✓ · browser-check ✓ | Verified |

**Gate key:** ✓ passed · ⚠️ HTML generated but browser-check limited by environment (Windows temp directory/Chrome cleanup), not a diagram defect.

---

## Component Status Labels

Every diagram node/edge carries one of these labels:

| Label | Meaning |
|-------|---------|
| **Implemented & verified** | Source present + tests pass locally |
| **Implemented · unverified** | Source present but not DB/front-end verified |
| **Partial** | Helper/code exists but not wired to production routes |
| **Planned** | Specified in docs; not implemented |
| **Blocked** | Environment or owner decision prevents progress |

---

## Remaining Diagrams (Pending)

Per the task directive, the following diagrams are specified but not yet generated. Generate only after the initial 6 are verified by the owner:

7. **Future knowledge ingestion pipeline** — Dataflow diagram (16-step KB ingestion)
8. **Future RAG and approved AI provider architecture** — Architecture diagram (RAG engine, safety arbiter, Gemini fallback gated)
9. **Future Free, trial and Pro subscription lifecycle** — Lifecycle diagram (subscription states, IST expiry)
10. **Current development roadmap and verification gates** — Workflow diagram (Phase 1 gates, CI, PostgreSQL, frontend builds)
11. **GitHub testing and release workflow** — Workflow diagram (CI jobs, PostgreSQL service, web/mobile checks)

---

## Source References

Each diagram's candidate JSON (`*.json`) is source-backed and links to:
- `backend/app/main.py` — FastAPI routes
- `backend/app/auth.py` — RS256 JWT, AuthWorkflow
- `backend/app/postgres_auth.py` — PostgreSQL session store
- `backend/app/farmer_onboarding.py` — Farmer onboarding
- `backend/app/partners.py` — Shop/Consultant store
- `backend/app/admin_provision.py` — Admin provisioning
- `backend/app/plots.py`, `backend/app/weather.py` — Farmer plots + weather
- `backend/migrations/0001_` through `0009_` — Schema migrations
- `docs/PROJECT_ARCHITECTURE.md` — Full architecture record
- `docs/PROJECT_STATUS.md` — Verification status
- `docs/KNOWN_ISSUES.md` — Security and verification issues

---

## Regeneration

To regenerate any diagram, edit its `*.json` candidate and run:

```bash
node <archify-path>/bin/archify.mjs finalize <type> <candidate.json> <output.html> --repo-root <repo-root> --quality showcase --json
```

Do not edit the `*.html` output directly — always edit the candidate JSON and rerun `finalize`.
