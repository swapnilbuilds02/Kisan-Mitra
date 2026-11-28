# Kisan Mitra — Master Project Specification

**Status:** Authoritative consolidated specification.  
**Source of truth:** This document links to and summarizes the detailed product documents in `docs/product-documentation/`; where this summary conflicts with a detailed product document, the detailed document governs until reconciled by owner decision.  
**Product owner:** Swapnil Pawar (jeeswapnil002@gmail.com)

---

## 1. Project Vision

Kisan Mitra AI is a Marathi-first agronomy platform for grape growers in Maharashtra, India (initial focus: Sangli, Tasgaon, Miraj, Solapur grape heartlands; primary crop: *Vitis vinifera* grapes). It puts an agronomy advisor in a farmer's pocket: daily crop schedules keyed to pruning date, AI diagnosis grounded in verified viticulture knowledge (never an unanchored oracle, never invents a chemical dosage), and a direct line to the shop or consultant the farmer already trusts.

The platform transitions from a legacy experimental WhatsApp chatbot (formerly Krushi Mitra AI / DrakshGuru) to a standalone multi-platform ecosystem:

- **Mobile app** (React Native/Expo): Farmer, Shop Partner, Agronomy Consultant
- **Owner web dashboard** (Next.js): Super Admin / Platform Admin exclusively
- **Backend** (FastAPI): single centralized API serving both clients

Four principles shape every decision:

| Principle | Meaning |
|-----------|---------|
| Knowledge base first | Answers come from verified viticulture documents. AI never acts as an unanchored oracle and never invents a chemical dosage. |
| The server decides | The mobile app has no authority over subscriptions or usage quotas. Every entitlement is checked on the backend. |
| Free by default | AI runs on free-tier models only. Hitting a limit degrades gracefully. It never escalates to a paid API. |
| Marathi first | Marathi UI, Marathi voice, Marathi messages. Voice uses on-device speech, so reading ability is not a barrier. |

---

## 2. Approved Functional Requirements

Detailed requirements live in the product documents; this section summarizes the approved functional scope.

### 2.1 User roles

| Role | Interface | Scope |
|------|-----------|-------|
| Farmer (Free) | Mobile app | Schedule Search (Global only) + Limited KB Chat (text, Global KB only, no Gemini). Combined 3 uses/month IST. No plots, no calls, no voice/photo, no partner chat. |
| Farmer (Pro) | Mobile app | Full Pro tier: multi-plot, personalized schedules, full AI with Gemini fallback, photo diagnosis (5/day), voice, weather, IVR (1 call/day), direct partner chat with consent. |
| Shop Partner | Mobile app only | Assigned Pro farmer management, plot create/update (audited, no delete), crop stages, direct chat. No web dashboard. Pending until approved. |
| Agronomy Consultant | Mobile app only | Assigned Pro vineyard management, prescriptions, field observations, direct chat. Consultant priority rule overrides shop link. Pending until approved. |
| Platform Admin | Web dashboard | Lead desk, farmer/global console, schedule/KB ingestion, IVR monitor, AI telemetry, partner approval. |
| Super Admin / Owner | Web dashboard | Swapnil Pawar. Unilateral Pro activation, complimentary access, partner provisioning, owner WhatsApp number config, full governance. |

### 2.2 Free vs Pro entitlements

Free tier (approved, PRD §8 / security matrix §3):

- Schedule Search: pruning date → DAP → Global Schedule entry. 1 use.
- Limited KB Chat: text only, Global KB only, zero Gemini fallback. 1 use.
- Combined quota: exactly 3 uses per calendar month, resetting 00:00 IST on the 1st. Server-side atomic. Reinstall/device switch never resets.
- Cannot register plots, receive IVR calls, use voice/photo/Gemini, or message partners.

Pro tier (unlocked by owner-assisted activation):

- Plot registration & multi-plot management (first plot = primary).
- Primary Plot drives both schedule and single daily IVR call.
- Full AI RAG chat (~95% grounded KB, ~5–10% Gemini free-tier fallback).
- Crop photo diagnosis capped at 5/day server-side.
- Ask by Photo / Ask by Voice (on-device Marathi STT/TTS).
- Hyperlocal weather & rain alerts.
- Direct in-app human chat with linked shop/consultant (consent-gated AI visibility).
- Medicine directory (CIB-approved dosages, PHI).
- Personalized daily farm planner.
- One automated Marathi call per farmer per day (07:00–19:00 IST).

### 2.3 Business policies

- **Conversion model:** Owner-assisted. Farmer taps WhatsApp `wa.me` deep link; app first creates an `upgrade_enquiries` lead (status `NEW`), then opens WhatsApp. Owner confirms manual payment and activates Pro via web dashboard.
- **Payment sources:** Direct from farmer, via consultant, or via shop. Manual only. No payment gateway, no WhatsApp Business API, no bots.
- **Pricing:** No fee amounts or numerical pricing displayed anywhere user-facing (Rule BR-19). Internal classifications: `Paid`, `Pending`, `Complimentary`.
- **Subscription:** Exactly one calendar year from activation date (anniversary engine, IST). Leap-year Feb-29 → next Feb 28. Early renewal extends from current expiry; lapsed renewal starts from new activation date.
- **Partner approval:** Shop/Consultant register via mobile → `PENDING_APPROVAL` → owner approves/provisions credentials → access granted. No self-approval or self-elevation.
- **Data preservation:** Expired/suspended partner accounts lose access but never lose data; relationships and history preserved.
- **Consent:** Farmer consent required before photos/voice/text leave the device to external AI; free-tier data-training disclosure. Approved consent document wording is an owner decision (not yet seeded).

### 2.4 Agricultural AI requirements

- **Router:** Single `AIRouter`. Knowledge base first (similarity ≥ 0.78), free Gemini second, consultant escalation last.
- **Guardrails:** No fabricated chemical dosages, active ingredients, or spray tank mixes. All pesticide/fungicide recommendations adhere to KB context and CIB/NRCG safety limits. Mandatory PHI precaution on synthetic fungicides. Refuse unapproved chemical cocktails.
- **Kill switch:** `AI_ENABLED=false` turns off every external AI call at once; non-AI features stay up.
- **Tier guarantee:** Free-tier models only; 429 never triggers paid fallback. Model allowlist does not by itself prove zero billing — actual Gemini project tier/quota must be verified (DEC-005).
- **Citation:** Grounded answers cite KB chunks with document title, version, page/row, effective date.
- **Consent + quota:** External AI calls require entitlement, consent, quota reservation, and owner approval.

Sources: `docs/product-documentation/01_PRD_KISAN_MITRA.md`, `02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md`, `03_SECURITY_AND_ACCESS_KISAN_MITRA.md`, `docs/AGRICULTURAL_INTELLIGENCE_IMPLEMENTATION_PLAN.md`.

---

## 3. Business Policies Summary

| Policy | Rule | Status |
|--------|------|--------|
| Name | "Kisan Mitra AI" (PRD) vs artwork "Krushi Mitra AI" | DEC-001 pending |
| Free medicine/articles access | PRD restricts; security/frontend grant access | DEC-002 pending |
| Login method | Mobile/password OR mobile/OTP for all four roles | Approved 2026-11-27 |
| Delegated Admin powers | Not settled | DEC-003 pending |
| Subscription expiry | IST vs UTC; Feb-29; early/lapsed renewal | DEC-004 pending |
| Gemini tier/terms | Not verified for this project | DEC-005 pending |
| WhatsApp architecture | `wa.me` click-to-chat only; no Business API/bots | Approved (BR-03, BR-19) |
| Plot gating | Stage 2A: all eligible active farmers may manage plots (supersedes Pro-only gate for plot mgmt only) | Approved for plot mgmt; subscription rules undecided |

---

## 4. Pending Owner Decisions

| ID | Decision | Blocker |
|----|----------|---------|
| DEC-001 | Product/app-store/domain/legal name: "Kisan Mitra" vs "Krushi Mitra AI" | UI copy, domain, app store, legal text |
| DEC-002 | Free visibility of medicine/articles; whether access consumes quota | API/screens/tests |
| DEC-003 | Delegated Admin permission matrix | Partner approval, Admin credentials |
| DEC-004 | Exact IST expiry instant, failed IVR call quota, former-partner historical visibility | Schema/worker implementation |
| DEC-005 | Gemini project tier, quota, privacy terms, live model availability | External AI enablement |

Do not invent owner approvals. Only the login policy and plot-management supersession are approved; all others above are pending.

---

## 5. Document Relationships

| Document | Covers | Path |
|----------|--------|------|
| Product Requirements | Users, features, business rules | `docs/product-documentation/01_PRD_KISAN_MITRA.md` |
| Technical Architecture | System design, schema, API, ADRs | `docs/product-documentation/02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md` |
| Security & Access | Roles, RLS, entitlements | `docs/product-documentation/03_SECURITY_AND_ACCESS_KISAN_MITRA.md` |
| Frontend Specification | Screens and navigation | `docs/product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` |
| Feature Tickets | Engineering tickets & acceptance | `docs/product-documentation/05_FEATURE_TICKET_LIST_KISAN_MITRA.md` |
| Documentation Final Review | Audit of doc set | `docs/product-documentation/KISAN_MITRA_DOCUMENTATION_FINAL_REVIEW.md` |
| Phased Roadmap | Prioritized build order & gates | `docs/PHASED_IMPLEMENTATION_ROADMAP.md` |
| Development Roadmap | Task-ID & dependency inventory | `docs/DEVELOPMENT_ROADMAP.md` |
| Task Completion Log | Completed/in-progress/pending/blocked | `docs/TASK_COMPLETION_LOG.md` |
| Implementation Audit | Code-verified status & gaps | `docs/IMPLEMENTATION_AUDIT.md` |
| AI Cost Optimization | Free-tier AI architecture & limits | `docs/AI_COST_OPTIMIZATION_REPORT.md` |
| AI Implementation Plan | Agricultural intelligence track | `docs/AGRICULTURAL_INTELLIGENCE_IMPLEMENTATION_PLAN.md` |
| External Eng References | build-your-own-x index | `docs/EXTERNAL_ENGINEERING_REFERENCES.md` |
| Brand Rules | Logo, color, usage | `brand/BRAND.md` |
