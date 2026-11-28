# Kisan Mitra — Decision Log

**Status:** Register of explicitly approved owner decisions, superseded requirements, unresolved contradictions, and pending decisions.  
**Rule:** Do not invent owner approvals. Only decisions marked "APPROVED" are authorized. Decisions marked "PENDING" require owner sign-off before implementation depends on them.

---

## 1. Explicitly Approved Owner Decisions

| ID | Decision | Approved | Scope / Notes | Source |
|----|----------|----------|---------------|--------|
| DEC-AUTH-001 | Login method: mobile/password **or** mobile/OTP for all four roles (Farmer, Shop, Consultant, Owner/Admin). Stronger optional Admin factors remain a recommendation, not mandatory MFA. | 2026-11-27 | Applies to all roles eventually; Farmer path active; other roles await provisioning gates. | `docs/PHASE1_AUTH_POLICY_PROPOSAL.md`, `docs/TASK_COMPLETION_LOG.md` |
| DEC-PLOT-001 | Every eligible active Farmer may manage multiple own plots (Stage 2A). Supersedes the older Pro-only plot gate **for plot management only**. Agricultural advisory and subscription rules remain undecided. | 2026-11-27 | Plot management only; not a blanket Pro gate removal. | `docs/PHASED_IMPLEMENTATION_ROADMAP.md` (line 4), `docs/STAGE2A_PLOTS_WEATHER.md` |
| DEC-RS256-001 | Replace HS256 signing with RS256 asymmetric token architecture (2048-bit min, kid-indexed public ring, issuer `https://api.kisanmitra.in`). Old HS256 tokens invalid at deployment. | 2026-11-27 | Local code/test contract; production key provisioning/rotation gate pending. | `docs/TASK_COMPLETION_LOG.md` (P1-RS-006), `backend/app/auth.py` |
| DEC-SUB-001 | Subscription validity: exactly one calendar year from activation date, IST, stored as TIMESTAMPTZ. Leap-year Feb-29 → next Feb 28. Early renewal extends from current expiry; lapsed renewal starts from new activation date. | Specified in PRD/architecture | Schema-level rule; not yet implemented in migrations. | `docs/product-documentation/01_PRD_KISAN_MITRA.md` §10.1 |
| DEC-WA-001 | WhatsApp architecture: `wa.me` click-to-chat deep link only; zero WhatsApp Business API, zero bots, zero auto-responders. Owner number dynamic from `system_configurations`. | Specified in PRD/security | Pre-created `upgrade_enquiries` lead (status `NEW`) before launching WhatsApp; 7-day duplicate suppression. | `docs/product-documentation/01_PRD_KISAN_MITRA.md` §7.1, `03_SECURITY_AND_ACCESS_KISAN_MITRA.md` §3.10 |
| DEC-AI-001 | Free-tier AI only; `AI_ENABLED=false` master kill switch; 429 never triggers paid fallback; knowledge base first (similarity ≥ 0.78); no invented dosage. | Specified in PRD/README | Actual Gemini project tier not verified (DEC-005 pending). | `README.md` §Features, `03_SECURITY_AND_ACCESS_KISAN_MITRA.md` §7 |

---

## 2. Superseded Requirements

| ID | Superseded requirement | Replaced by | Approval | Notes |
|----|------------------------|-------------|----------|-------|
| SUP-PLOT-001 | Pro-only plot registration gate (Phase 3 roadmap) | Stage 2A: all eligible active farmers may manage plots (plot management only) | DEC-PLOT-001 | Subscription/advisory rules remain undecided; this is **not** a blanket Pro gate removal. |
| SUP-CALLING-001 | Separate "Calling Plot" concept | Consolidated "Primary Plot" (`farms.is_primary_plot`) drives both schedule and IVR call; first-added plot defaults to Primary | PRD v2.2.0 §2.2 / §10.7 | Eliminates duplicate calling-plot concept. |

---

## 3. Unresolved Contradictions (specification vs specification)

These are cross-document conflicts that must be reconciled by owner decision before dependent implementation.

| # | Contradiction | Documents involved | Blocker | Status |
|---|---------------|-------------------|---------|--------|
| CON-001 | Product name: PRD and documentation review mandate "Kisan Mitra"; supplied primary artwork reads "Krushi Mitra AI" | PRD §1 / final review vs `brand/KISAN-MITRA-BRAND/01-Primary-Logo/` | DEC-001 | PENDING — blocks UI copy, domain, app-store, legal text |
| CON-002 | Free access to medicine/articles: PRD §8.1 restricts Free to Schedule Search + Limited KB Chat; security matrix (§3) and frontend spec (§1.1) grant Free read access to knowledge base and medicine directory | PRD §8.1 vs `03_SECURITY_AND_ACCESS_KISAN_MITRA.md` §3.8 vs `04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` | DEC-002 | PENDING — blocks API/screens/tests |
| CON-003 | Schema table count: architecture §6 says 24 tables; final review says 35; architecture document contains 48 `CREATE TABLE` statements | `02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md` vs `KISAN_MITRA_DOCUMENTATION_FINAL_REVIEW.md` | None assigned | OPEN — normalize to a single executable schema and count before Phase 2 |
| CON-004 | Color palette: brand guidelines (`#174C38` Deep Forest primary, `#34785A` secondary, `#C5A451` accent) vs frontend spec (`#1B5E20` primary green, `#F57F17` Harvest Gold accent) | `brand/BRAND.md` vs `04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` §1.1 | None assigned | OPEN — blocks frontend design tokens |
| CON-005 | `KM-AIRT-001` dependency: older roadmap makes AI cost controls depend on AI features while requiring cost controls before external AI is enabled | `DEVELOPMENT_ROADMAP.md` vs `PHASED_IMPLEMENTATION_ROADMAP.md` | None assigned | OPEN — use phased roadmap dependency order |
| CON-006 | `KM-AICHT-001` self-reference: listed as depending on itself in dependency chain | `DEVELOPMENT_ROADMAP.md` Module 7 | None assigned | OPEN — correct dependency |
| CON-007 | Schedule vs knowledge ingestion pipeline: one PRD journey describes a consultant schedule going through the 16-step knowledge pipeline; architecture specifies a separate 9-step schedule pipeline | `01_PRD_KISAN_MITRA.md` vs `02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md` | None assigned | OPEN — preserve separation; correct acceptance tests |

---

## 4. Pending Business and Technical Decisions

| ID | Decision | Needed to unblock | Status |
|----|----------|-------------------|--------|
| DEC-001 | Product/app-store/domain/legal name: "Kisan Mitra" vs "Krushi Mitra AI" | UI copy, domain, app-store, legal text frozen | PENDING — owner decision |
| DEC-002 | Free visibility of medicine/articles; whether Free access consumes quota | API screens, frontend, tests | PENDING — owner decision |
| DEC-003 | Delegated Admin permission matrix (what delegated admins can/cannot do vs Super Admin) | Partner approval, Admin credential provisioning | PARTIALLY RESOLVED — login policy approved; permission decision pending |
| DEC-004 | Exact subscription expiry instant (IST vs UTC), failed IVR call quota consumption, former-partner historical message visibility | Schema state-transition and timestamp rules; worker implementation | PENDING — owner decision |
| DEC-005 | Gemini project tier, quota, privacy terms, data terms, actual live model availability for this account | External AI enablement, farmer-facing consent | PENDING — external state + owner decision |
| DEC-CONSENT-001 | Approved consent document wording and version (farmer AI-visibility consent, external-model processing disclosure, free-tier data-training disclosure) | Farmer onboarding completion (migration 0006 seeds nothing; fails closed until document installed) | PENDING — owner decision |
| DEC-SCHEMA-001 | Normalize single executable schema and table count (resolve CON-003) | Phase 2 migrations | PENDING — engineering decision with owner awareness |

---

## 5. Decisions Explicitly NOT Made

The following are recorded so no future model assumes approval:

- No payment gateway or WhatsApp Business API integration is approved (explicitly prohibited: BR-03, BR-19, PRD §7.1).
- No live external AI call (Gemini) is authorized until DEC-005 and consent gates pass.
- No production database migration is approved to run (disposable local/staging only).
- No deployment, paid integration, or live database migration is included in Phase 1 roadmap approval.
- No actual Owner account has been provisioned in the repository.
- No frontend (mobile/web) build has been verified.
- No branding change (logo, color, name) beyond the working-tree replacement is approved as deployed.
