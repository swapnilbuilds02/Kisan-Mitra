# Kisan Mitra phased implementation roadmap

**Status:** Phase 1 authorized and in progress since 2026-11-27; later phases remain planned.  
**Stage 2A authorization:** Plot and weather foundation source may proceed while Phase 1 verification gates stay open. The owner's latest instruction permits multiple plots for every eligible active Farmer; the earlier Pro-only plot gate in Phase 3 is superseded **for plot management only**. Agricultural advisory and subscription rules remain undecided. See [Stage 2A record](STAGE2A_PLOTS_WEATHER.md).  
**Stage 1F note:** The owner-approved login policy is mobile/password **or** mobile/OTP for all four roles. Backend source and frontend auth flows exist, but PostgreSQL, frontend build/device, consent, OTP delivery, and Git/CI verification gates remain open. The proposed agricultural intelligence preparation track is in [AGRICULTURAL_INTELLIGENCE_IMPLEMENTATION_PLAN.md](AGRICULTURAL_INTELLIGENCE_IMPLEMENTATION_PLAN.md); it does not change approved phase order or authorize live integrations.  
**Basis:** [2026-11-27 implementation audit](IMPLEMENTATION_AUDIT.md), [PRD](product-documentation/01_PRD_KISAN_MITRA.md), [technical architecture](product-documentation/02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md), [security specification](product-documentation/03_SECURITY_AND_ACCESS_KISAN_MITRA.md), [frontend specification](product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md), and [feature tickets](product-documentation/05_FEATURE_TICKET_LIST_KISAN_MITRA.md). This plan uses dependency order and priorities, not target dates. The older [roadmap](DEVELOPMENT_ROADMAP.md) remains the task-ID inventory; this file is the proposed execution order where those dependencies conflict.

## Rules for every phase

- Preserve the passing AI helper unit tests and current holding site while building the application. Do not expose mock-only AI helpers as production endpoints.
- Backend authorization and database isolation are mandatory even when the mobile/web UI hides a feature. All owner and partner mutations need auditable actor, target, reason, and before/after data.
- Keep external AI disabled until entitlement, consent, tenant-scoped approved knowledge, dosage safety, and cost controls are verified. A model allowlist alone is insufficient to guarantee free billing; verify the actual project tier and limits before live calls.
- Build schedule configuration (9-step) separately from knowledge ingestion/OCR/vector indexing (16-step). Publish neither without human approval.
- Maintain [TASK_COMPLETION_LOG.md](TASK_COMPLETION_LOG.md) after **each** task: name, description, implementation, files, tests/results, actual completion date, and status. A passing unit test alone does not mark a workflow complete.
- No deployment, paid integration, or **live database migration** is included in approval of this document; those actions follow the project's existing owner controls when their concrete implementation is ready. Disposable local/staging migrations are part of Phase 1 verification.

## Phase 0 — Resolve product and architecture decisions (P0, documentation only)

1. **Identity and access contract:** decide whether the product name changes to “Krushi Mitra AI” or only the artwork changes; define delegated Admin powers and required consent for sharing AI chats and sending data to Gemini. The four-role password-or-OTP login policy is approved.
2. **Commercial contract:** settle Free access to medicine/articles, the exact IST subscription expiry instant and renewal behavior, pending/complimentary payment rights, and the WhatsApp lead retry/dedup behavior.
3. **Data and schedule contract:** approve the 48-table candidate inventory or a reduced MVP schema; specify one primary plot invariant, relationship history visibility after unlink, daily call reservation/retry rule, and separate 9-step/16-step pipelines.
4. **Traceability repair:** align PRD, security, frontend, tickets, and test cases with the decisions. Remove contradictory dated milestone claims from the active plan and define acceptance scenarios by task ID.

**Exit gate:** one approved decision register and permission matrix, consistent MVP scope, and testable acceptance criteria. Unresolved choices remain visible in the task log; safe foundation work may proceed without guessing those choices.

## Phase 1 — Foundation and security skeleton (recommended first build phase, P0)

| Step | Layer | Work and existing task IDs | Verification / exit evidence |
| --- | --- | --- | --- |
| 1.1 | Tooling | Scaffold FastAPI, Expo/React Native, and Next.js workspaces; pin Python/Node dependencies, add reproducible local startup and CI. Preserve `backend/app/services/` and existing tests. `KM-FOUND-001` | Clean checkout installs, starts API/mobile/web shells, and runs 63 existing tests plus type/lint checks. |
| 1.2 | Database | Convert the approved schema subset into versioned, reversible PostgreSQL migrations: identities, farmer/partner profiles, relationship and audit foundations, subscriptions/configuration, and later feature tables only when required. Enable RLS with explicit deny-by-default policies and seed test identities. `KM-FOUND-001`, `KM-SEC-001` | Apply/rollback on a disposable DB; constraints, indexes, policy ownership, and backup/restore smoke checks pass. No live migration yet. |
| 1.3 | Backend | Add health/config endpoints, request validation, structured errors, JWT/session verification, role/entitlement middleware, and separate owner/admin privileges. Keep service-role credentials server-side. `KM-AUTH-001`, `KM-SEC-001` | Authenticated API tests reject missing/tampered tokens and wrong roles; negative tests prove no cross-tenant reads/writes. |
| 1.4 | Frontend | Add Marathi/English design tokens, mobile language/OTP/profile and role-routing shells, owner login/navigation shell, pending and expired partner screens. `KM-DS-001`, `KM-REL-001` (shell only) | Every role routes to the correct empty-state shell; Free never enters Pro/partner screens; accessibility and narrow Android layouts checked. |
| 1.5 | Integrations | Configure **sandbox or mocked** OTP delivery and Supabase/Redis adapters; define provider interfaces and secret injection. Do not activate paid SMS, external AI, or telephony. | Provider contract tests, secret scan, and disconnected/offline failure behavior pass. |
| 1.6 | Testing/documentation | Establish unit, API, migration, RLS, browser, and device test layers with fixture identities; record decisions and results in the task log. | CI is green; owner can review a demo of login, role routing, and denied access with no real farmer data. |

**Phase 1 outcome:** a secure, runnable but intentionally feature-light application skeleton. It is the earliest useful build because every later Free, Pro, Shop, Consultant, and Owner workflow depends on identity and data isolation.

## Phase 2 — Free value loop and owner-controlled conversion (P0)

The [farmer and partner relationship architecture proposal](PHASE2_FARMER_RELATIONSHIP_ARCHITECTURE_PROPOSAL.md) describes identity, direct Pro activation, and future partner links. Its Shop/Consultant relationship engine remains assigned to Phase 4 unless the owner approves a change to this sequence. The proposal is design only.

1. **Database/backend:** implement Global Schedule data, deterministic DAP lookup, and one atomic `free_usage_counters(user_id, IST_month)` ledger shared by schedule search and Global-KB-only text chat. Reject invalid/future dates before charging. `KM-FREE-002`, `KM-FREE-003`.
2. **Knowledge minimum:** ingest a small, owner-approved Global KB with citations and no external fallback for Free. Build approval-state and tenant boundaries before a public chat endpoint. `KM-AI-001` (limited baseline).
3. **Frontend:** Free Schedule Search, limited KB chat, remaining-uses badge, Pro intercept, and an accessible Marathi upgrade page with no public price. `KM-DS-001`, `KM-PRO-001`.
4. **Owner/backend/integration:** public owner-number config, pre-created/deduplicated enquiry, `wa.me` handoff, lead desk, manual payment classification, pending activation, anniversary subscription engine, and direct Pro activation. `KM-ADM-004`, `KM-ENQ-001`, `KM-ADMIN-001`, `KM-SUB-001`, `KM-ADMIN-002`, `KM-PAY-001`.
5. **Tests:** concurrency and IST month rollover; no quota charge on validation failures; no Gemini call for Free; lead-before-WhatsApp ordering and 7-day dedup; leap-day/early/lapsed renewal; direct activation and audit; owner/admin denial tests.

**Exit gate:** a farmer can onboard, use exactly three combined Free actions, enquire, and receive owner-activated Pro access in staging. No external AI or payment gateway is needed.

## Phase 3 — Pro plot, stage, and schedule core (P0)

1. **Database/backend:** Pro-only multi-plot CRUD; first active plot default; transactionally unique primary plot; audit and farmer notification for non-farmer edits. `KM-PLOT-001`, `KM-IVR-002`.
2. **Agronomy:** deterministic crop-stage/DAP engine, versioned Global Schedule binding, plot-specific daily timeline and planner; source and unit attribution on every advisory. `KM-FARM-001`, `KM-AGR-001` (Global baseline).
3. **Frontend:** post-activation plot setup, plot list/switcher, primary designation, stage and schedule screens, subscription status. `SCR-PLT-00/01/02`, `SCR-FRM-01/02`, `SCR-SET-03`.
4. **Tests:** free plot denial; concurrent primary switches; invalid pruning date; actor audit/notification; independent secondary-plot state; expiry preserving plots.

**Exit gate:** Pro farmers can manage plots and see deterministic, approved Global guidance without generative AI.

## Phase 4 — Partner governance and tenant relationships (P0)

1. **Backend/database:** Shop and Consultant application/approval, credentials, independent annual subscriptions, suspension without deletion, active relationship constraints, consultant-priority transaction, history and restoration. `KM-REL-001/002/003/004/005`, `KM-ADM-003`, `KM-GLB-001`.
2. **Frontend:** pending/expired screens, assigned-farmer dashboards, linked plot views and edits, owner partner desk, relationship supervision, global-farmer console.
3. **Integrations:** event/push notices only to the documented recipients; no farmer/former-shop alarm on consultant-priority unlink.
4. **Tests:** Shop A versus Shop B, Consultant A versus B, unassigned global farmers, post-unlink new-data denial, historical preservation, partner plot delete denial, owner-only restoration, expiry/renewal.

**Exit gate:** all four roles have usable, isolated core workflows; an expired or unapproved partner cannot access farmer data.

## Phase 5 — Approved knowledge and safe AI (P1; external calls gated)

1. **Database/integrations:** private file storage; 16-step knowledge ingestion, OCR, malware/type checks, dosage approval, versioning, pgvector indexes, scoped retrieval. `KM-KB-001/002/003/004`, `KM-RAG-001`.
2. **Backend safety:** deterministic source citations and CIB/NRCG rule checks; context-safe cache keys; atomic persistent quotas; image validation and Pro five-photo/day limit; no output dosage absent approved evidence. Fix the audited cache/kill-switch and timezone issues before connecting routes. `KM-RAG-002`, `KM-VIS-001`, `KM-AIRT-001`.
3. **Consent and external AI:** distinct farmer controls for partner AI-view consent and external-model processing; verify Gemini project tier, model availability, rate limits, and data terms. Only then enable controlled Pro fallback and telemetry, with a hard disable switch. `KM-AICHT-002`, `KM-AI-002`, `KM-RAG-003/004`.
4. **Frontend/mobile:** Pro chat, citations and uncertainty state, photo diagnosis, typed fallback; link/test native Marathi speech on physical devices. `KM-MED-002` (voice/photo query component).
5. **Tests:** poison documents, conflicting dosages, no-source refusals, tenant-specific retrieval, cache isolation, 429/disabled behavior, concurrent quotas, real-image/device/provider contract checks. No live farmer data until privacy and safety gates pass.

**Exit gate:** AI advice is approved-source grounded, tenant isolated, consented, auditable, and operationally bounded. The ~95% grounded and ~5–10% fallback figures remain measured targets, not assumed guarantees.

## Phase 6 — Advanced advisory and communication (P1)

1. **Schedules:** 9-step passive schedule upload/review/versioning for Global/Shop/Consultant; partner-specific binding and consultant overrides. `KM-SCHED-001`, `KM-AGR-002`.
2. **Human collaboration:** isolated one-to-one chat, private signed media, consented read-only AI conversation projection, view audit, and immediate unlink revocation. `KM-CHT-001/002`, `KM-AICHT-001`.
3. **Reference tools:** approved medicine directory and source/PHI cards; reconcile Free visibility decision. `KM-MED-001`.
4. **Weather and calling:** optional plot GPS, forecast provider, opt-in/out, primary-plot IVR, one-call-per-IST-day database ledger, retries and push fallback. `KM-WTH-002`, `KM-IVR-001`.
5. **Tests:** schedule formula/macro rejection, tenant binding, chat/media isolation, AI-read-only denial, weather missing-GPS fallback, concurrent call attempts, retries, opt-out and expiry.

## Phase 7 — Release verification and operations (P0 before launch)

1. Run full regression, 85% branch-coverage target for business logic, SAST/dependency scans, migration and restore rehearsal, accessibility/localization review, low-connectivity and physical-device tests. `KM-SEC-001`, `KM-UAT-001`.
2. Verify current hosting, CSP, caching, OG images, app icons, privacy copy, domain and release targets. The Vercel documentation describes an older snapshot; do not infer current production state from repository files.
3. Demonstrate all four role journeys, negative permission tests, subscription/calendar boundaries, provider failures, and audit trails on staging with test data. Record owner sign-off and release evidence in the permanent log.

**Release gate:** verified staging behavior and explicit owner approval for a concrete deployment. No planned date is implied.
