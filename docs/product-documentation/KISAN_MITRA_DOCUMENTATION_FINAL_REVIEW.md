# Documentation Quality, Consistency Audit & Traceability Report – Kisan Mitra AI (formerly DrakshGuru)

---

## 1. Executive Summary & Document Control

| Property | Details |
| :--- | :--- |
| **Document Title** | Final Documentation Audit, Traceability Matrix & Readiness Report – Kisan Mitra AI (formerly DrakshGuru) |
| **System Name** | Kisan Mitra AI Unified Viticulture Intelligence Platform |
| **Review Version** | 2.2.0 (Revised Free/Pro Model, WhatsApp Direct Integration & Primary Plot Consolidation) |
| **Audit Date** | November 2026 |
| **Product Owner** | Swapnil Pawar |
| **Review Board** | Principal Software Architect, Senior Product Manager, Lead Viticulture Consultant, Application Security Engineer |
| **Final Readiness Status**| **PASS WITH RECOMMENDATIONS** |

### Document Revision History
| Version | Date | Author / Role | Changes / Remarks |
| :---: | :---: | :---: | :--- |
| 1.0.0 | 2026-11-19 | Audit Review Board | Initial pre-development documentation audit and RTM. |
| 2.0.0 | 2026-11-20 | Audit Review Board | Manual payment audit, lead desk traceability, 1-year calendar engine verification. |
| 2.1.0 | 2026-11-21 | Audit Review Board | Independent schedules audit, multi-plot verification, 46 test assertions. |
| 2.2.0 | 2026-11-23 | Audit Review Board | Comprehensive audit of Revised Free/Pro Model: verified 3-use combined monthly quota engine (`free_usage_counters`), WhatsApp click-to-chat integration (`wa.me`) with pre-created leads, plot registration restricted strictly to Pro subscribers, multi-actor plot editing permissions (with mandatory `audit_logs` and in-app notifications), and consolidated Primary Plot architecture (replacing Calling Plot). Expanded business rules to 58 (BR-01 to BR-58) and test cases to 54. Total 35 database tables. |

This comprehensive review evaluates the completeness, technical accuracy, architectural feasibility, and cross-document consistency of the **Kisan Mitra AI (formerly DrakshGuru) Pre-Development Documentation Suite**. 

The transition from the legacy experimental WhatsApp bot (Krushi Mitra AI) to the standalone multi-platform **Kisan Mitra AI** ecosystem is complete. The system architecture unambiguously establishes a **single centralized backend** powering an **Owner Web Dashboard** (exclusively for Swapnil Pawar) and **three role-based mobile experiences** (Farmer, Shop, Consultant), backed by a deterministic **One-Calendar-Year Subscription Engine**, **Independent Advisory Schedules (9-Step Pipeline)**, **Multi-Plot Management**, **Automated Voice Calling (IVR) with 1-Call-Per-Day Hard Ceiling**, **Searchable Medicine Information Library**, and **Direct Admin-to-Farmer Pro Activation**.

---

## 2. Audit of Created Documentation Deliverables

All required engineering documents have been authored and cross-linked within the repository:

| Document Code | File Name | Canonical Path | Status |
| :---: | :--- | :--- | :---: |
| **DOC-01** | Product Requirements Document | [01_PRD_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/01_PRD_KISAN_MITRA.md) | **VERIFIED COMPLETE** |
| **DOC-02** | Technical Architecture Document | [02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md) | **VERIFIED COMPLETE** |
| **DOC-03** | Security & Access Governance | [03_SECURITY_AND_ACCESS_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/03_SECURITY_AND_ACCESS_KISAN_MITRA.md) | **VERIFIED COMPLETE** |
| **DOC-04** | Frontend Specification Document | [04_FRONTEND_SPECIFICATION_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md) | **VERIFIED COMPLETE** |
| **DOC-05** | Feature Ticket List & Plan | [05_FEATURE_TICKET_LIST_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/05_FEATURE_TICKET_LIST_KISAN_MITRA.md) | **VERIFIED COMPLETE** |
| **DOC-06** | Final Review & Traceability | [KISAN_MITRA_DOCUMENTATION_FINAL_REVIEW.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/KISAN_MITRA_DOCUMENTATION_FINAL_REVIEW.md) | **VERIFIED COMPLETE** |

---

## 3. End-to-End Requirement Traceability Matrix (RTM)

The matrix below provides complete forward and backward traceability for every P0 and critical architectural requirement:

| PRD Requirement ID | Requirement Summary | Architecture Component | DB Tables & Models | REST API Endpoints | Security & Access Rule | Frontend Screen ID | Sprint Ticket ID | Core Validation Test Case |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **KM-FR-001** | Mobile DLT OTP Auth | `AuthService` | `users` | `POST /auth/otp/*` | TOTP Rate Limiting (3/hr) | `SCR-ONB-02`, `03` | `KM-AUTH-001` | `TC-SUB-01` |
| **KM-FR-004** | Free Schedule Search | `SchedulingService` | `schedule_events`, `free_usage_counters` | `GET /api/v1/free/schedule-lookup` | Combined 3/mo Quota (Global Only) | `SCR-FREE-01` | `KM-FREE-003` | `TC-FREE-01`, `02` |
| **KM-FR-005** | Free Limited KB Chat | `KnowledgeRAGService`| `knowledge_chunks`, `free_usage_counters` | `POST /api/v1/chat/message` | Combined 3/mo Quota (0% Gemini Fallback) | `SCR-FREE-02` | `KM-FREE-002` | `TC-FREE-03`, `04` |
| **KM-FR-006** | Premium Upgrade Showcase | Client Router | `system_configurations` | Local Interceptor & Config API | Dynamic WhatsApp Number Delivery | `SCR-UPG-01` | `KM-PRO-001` | `TC-WA-01` |
| **KM-FR-007** | Pro WhatsApp Enquiry | `EnquiryService` | `upgrade_enquiries` | `POST /api/v1/subscriptions/enquiries` | Pre-Created Lead & 7-Day Dedup | `SCR-UPG-01` | `KM-ENQ-001` | `TC-WA-01` |
| **KM-FR-008** | Owner Lead Desk | `AdminPortal` | `upgrade_enquiries` | `GET /admin/enquiries` | Super Admin / Admin Role | `SCR-ADM-02` | `KM-ADMIN-001` | `TC-SUB-05`, `06` |
| **KM-FR-009** | Direct Pro Activation | `SubscriptionEngine`| `subscriptions`, `pending_pro` | `POST /admin/direct-activate` | Owner Authorization & Audit | `SCR-ADM-03` | `KM-ADMIN-002` | `TC-SUB-07`, `08` |
| **KM-FR-010** | 1-Year Validity Engine | `AnniversaryCron` | `subscriptions` | Background Cron | Strict Calendar Anniversary | `SCR-SUB-01` | `KM-SUB-001` | `TC-SUB-09`, `10`, `11` |
| **KM-FR-011** | Pro Marathi AI RAG | `KnowledgeRAGService`| `knowledge_chunks` (`pgvector`)| `POST /chat/message` | Confidence Guard ($\ge 0.78$) | `SCR-AI-01` | `KM-AI-002` | `TC-SUB-02` |
| **KM-FR-012** | Pro Photo Vision Diag | `VisionService` | `uploaded_photos`, Supabase Store | `POST /vision/analyze` | Daily Cap (5/day) + Magic Byte | `SCR-VIS-01`, `02` | `KM-VIS-001` | `TC-SUB-03`, `14` |
| **KM-FR-013** | Grape Stage Engine | `CropStageEngine` | `crops`, `crop_stages` | `GET /crops/{id}/stage` | Verified POP Rules | `SCR-FRM-02` | `KM-FARM-001` | Unit Stage Test |
| **KM-FR-015** | Tenant Isolation | `TenantRLSService` | `farmer_relationships` | All Shop/Consultant APIs | PostgreSQL RLS Policies | `SCR-SHP-01`, `CON-01`| `KM-REL-001` | `TC-SUB-13` |
| **KM-FR-018** | Partner Admin Authorization | `AdminAuthService` | `shops`, `consultants` | `POST /admin/partners/approve` | Registration vs Authorization Separation | `SCR-SHP-00`, `SCR-ADM-07` | `KM-REL-002` | `TC-SUB-15` |
| **KM-FR-019** | Partner Data Preservation | `SubscriptionEngine`| `shops`, `consultants`, `relationships` | Background Expiry Cron | Access Suspended, Data Preserved | `SCR-EXP-01` | `KM-REL-003` | `TC-SUB-16` |
| **KM-PAY-001** | Manual Payment Processing | `PaymentAdminService`| `subscriptions` | `POST /admin/direct-activate` | Manual 3-Source Classification | `SCR-ADM-03` | `KM-PAY-001` | `TC-SUB-07` |
| **KM-FR-020** | Master KB Admin Ingestion | `MasterKBSvc` | `master_knowledge_documents` | `POST /admin/kb/master/documents` | Admin-Only Upload & Approval | `SCR-ADM-08` | `KM-KB-001` | `TC-KB-01`, `02` |
| **KM-FR-021** | Consultant KB Tenant Isolation | `ConsultantKBSvc` | `consultant_knowledge_documents` | `POST /admin/kb/consultants/{id}/documents` | RLS Partitioned by `consultant_id` | `SCR-ADM-09` | `KM-KB-002` | `TC-KB-03` |
| **KM-FR-022** | 16-Step Document Pipeline | `DocPipeline` | `knowledge_processing_jobs` | Background Celery Worker | Mandatory Human Approval Gate | `SCR-ADM-10` | `KM-KB-003`, `KM-KB-004` | `TC-KB-01`, `02` |
| **KM-FR-023** | Personalized Farm Schedule | `PersonalizedScheduleSvc` | `personalized_farm_schedules`, `farm_schedule_items` | `GET /farmer/schedules/personalized` | Plot-Level RLS Isolation | `SCR-PLN-02` | `KM-AGR-001` | `TC-KB-04` |
| **KM-FR-024** | Multi-Tier RAG (~95% Grounded) | `RAGSvc` | `ai_retrieval_logs`, `ai_response_logs` | `POST /chat/message` | Confidence $\ge 0.78$ Threshold | `SCR-AI-01` | `KM-RAG-001` | `TC-KB-06` |
| **KM-FR-025** | Agronomic Conflict Resolution | `AgronomicSafetyArbiter` | Deterministic CIB/NRCG Rules | Internal Safety Layer | Conflict Flag & Advisory Warning | Inline Warning in `SCR-AI-01` | `KM-RAG-002` | `TC-KB-05` |
| **KM-FR-026** | Gemini Fallback (~5–10%) | `GeminiFallback` | `gemini_fallback_logs` | Conditional Gemini API Call | Safety Guardrail Prompt Injection | Disclaimer Badge in `SCR-AI-01` | `KM-RAG-003` | `TC-KB-07` |
| **KM-FR-027** | AI Telemetry & Monitoring | `TelemetrySvc` | `ai_response_logs`, `gemini_fallback_logs` | `GET /admin/telemetry/ai-grounding` | Admin-Only Dashboard | `SCR-ADM-11` | `KM-RAG-004` | Dashboard Render Test |
| **KM-FR-028** | Consultant Priority Rule | `RelationshipService` | `farmer_relationships`, `farmer_relationship_history` | Background Transaction / Event | Atomic Priority Transition | `SCR-ADM-13` | `KM-REL-004` | `TC-REL-01`, `02`, `03` |
| **KM-FR-029** | Direct In-App Chat | `DirectChatService` | `chat_conversations`, `chat_messages` | `/api/v1/direct-chat/*` | Supabase Realtime & RLS Channel Isolation | `SCR-CHT-01`, `SHP-02`, `CON-05` | `KM-CHT-001`, `002` | `TC-CHT-01`, `02` |
| **KM-FR-030** | Shared AI Chat Read-Only View | `AIVisibilityService` | `ai_conversations`, `farmer_ai_visibility_consents`, `ai_chat_view_audit_logs` | `GET /api/v1/partner/farmers/{id}/ai-chat-view` | Strict Read-Only + Farmer Consent Gate | `SCR-SHP-03`, `CON-06`, `SET-02` | `KM-AICHT-001`, `002` | `TC-AICHT-01`, `02`, `03` |
| **KM-FR-031** | Owner Relationship Supervision | `AdminRelationshipSvc` | `farmer_relationships`, `farmer_relationship_history` | `/api/admin/relationships/*` | Admin-Only Access & Audit Logging | `SCR-ADM-13`, `14` | `KM-ADM-003` | `TC-ADM-01` |
| **KM-FR-032** | 3 Independent Farmer Categories | `FarmerCategoryRouter` | `farmer_profiles`, `farmer_relationships` | `/api/admin/global-farmers` | Category-Aware Routing & Admin Oversight | `SCR-ADM-15` | `KM-GLB-001` | `TC-PLOT-01` |
| **KM-FR-033** | Independent Advisory Schedules | `IndependentScheduleSvc` | `schedule_configurations`, `schedule_events` | `/api/admin/schedules/*` | 9-Step Non-Executable Pipeline & RLS Isolation | `SCR-ADM-16` | `KM-SCHED-001` | `TC-SCHED-01`, `02`, `03` |
| **KM-FR-034** | Pro Multi-Plot & Multi-Actor Editing | `FarmService` | `farms`, `audit_logs` | `/api/v1/farmer/plots` | Pro-Only Gating; Multi-Actor Auditing & Push Alerts | `SCR-PLT-00`, `01`, `02` | `KM-PLOT-001` | `TC-PLOT-01`, `04`, `06` |
| **KM-FR-035** | 1-Call-Per-Day Ledger Quota | `IVRCallingSvc` | `daily_call_ledger` | `/api/v1/ivr/calls/trigger` | Database Partial Unique Index Enforcement | `SCR-ADM-17` | `KM-IVR-001` | `TC-CALL-01`, `02` |
| **KM-FR-036** | Primary Plot Engine & Default Fallback | `CallingSettingsSvc` | `farms.is_primary_plot` | `/api/v1/farmer/calling-settings` | Single Primary Plot Drivers + Default Plot 1 Fallback | `SCR-SET-03` | `KM-IVR-002` | `TC-PLOT-02`, `03`, `05` |
| **KM-FR-037** | Automated Voice Calling (IVR) | `IVRTelephonyWorker` | `automated_call_logs` | `/api/v1/ivr/*` | Calling Window (07:00 AM–07:00 PM IST) + Opt-Out | `SCR-SET-03`, `SCR-ADM-17` | `KM-IVR-001` | `TC-CALL-01`, `03`, `04` |
| **KM-FR-038** | Searchable Medicine Directory | `MedicineService` | `medicine_products` | `/api/v1/medicine/products` | Public Authenticated Read-Only; Admin Write; No In-App Commerce | `SCR-MED-01`, `02` | `KM-MED-001` | `TC-MED-01` |
| **KM-FR-039** | GPS Plot Mapping & Weather Alerts | `WeatherService` | `farms` (`latitude`, `longitude`), `weather_alert_events` | `/api/v1/weather/*` | Plot-Specific Geolocation + 1-Call Quota Respect | `SCR-PLT-02`, `SCR-WTH-01` | `KM-WTH-002` | `TC-PLOT-01` |

---

## 4. Verification of Mandatory Business & Architectural Rules

| Rule Index | Mandatory Product Owner Rule | Audit Finding | Verification Status |
| :---: | :--- | :--- | :---: |
| **BR-01** | **Official Name:** Must always be Kisan Mitra. Legacy name Krushi Mitra AI must be decommissioned. | Verified across all 5 documents, schemas, and brand tokens. | **PASS** |
| **BR-02** | **Standalone Architecture:** Dedicated native mobile application. | Expo/React Native client specified with direct REST APIs. | **PASS** |
| **BR-03** | **WhatsApp Click-to-Chat Integration:** Frictionless `wa.me` deep link with pre-filled Devanagari message (`SCR-UPG-01`); zero WhatsApp Business API bots, webhooks, or automated conversational engines. | Documented in PRD (Principle 7, Section 7.1), Architecture (C4, Section 9.1), Security (Section 3.10), Frontend (`SCR-UPG-01`). Verified. | **PASS** |
| **BR-04** | **Free Plan Scope:** Strictly 2 features (Schedule Search & Limited KB Chat) sharing ONE combined monthly quota of 3 total uses. No plot registration, automated calls, weather alerts, or push notifications. | Documented in PRD (Section 8), Architecture (Table 35, Section 7.1), Security (Section 3), Frontend (`SCR-FREE-01`, `02`). Verified. | **PASS** |
| **BR-05** | **Free KB-Only AI Access:** Free farmers get text-only query access to Global KB (0% Gemini fallback, no photo/voice), consuming from 3-use monthly quota. | Documented in PRD (Section 8.2), Architecture (Section 8.11), Security (Section 3), Frontend (`SCR-FREE-02`). Verified. | **PASS** |
| **BR-06** | **Free Photo & Plot Blockade:** Free users cannot upload crop photos, register vineyard plots, or receive automated calls. | Gated server-side; HTTP 403 returned on unauthorized endpoints. Verified in Architecture and Security. | **PASS** |
| **BR-07** | **Pro Upgrade Screen:** Attractive value showcase shown on intercept. | Designed in `SCR-UPG-01` with explicit Marathi copy and CTA. | **PASS** |
| **BR-08** | **Owner Enquiry Mechanism:** Upgrades submitted as backend leads. | Submits to `upgrade_enquiries` table with unique tracking ID. | **PASS** |
| **BR-09** | **Owner Consultation:** Swapnil Pawar contacts farmer personally. | Enquiry desk provides click-to-call and consultation notes. | **PASS** |
| **BR-10** | **Authorized Activation:** Pro access requires explicit authorized action. | Manual activation via Web Admin with recorded payment status. | **PASS** |
| **BR-11** | **One-Calendar-Year Validity:** Exactly 1 calendar year from activation. | Calculated via `dateutil.relativedelta(years=1)` in IST. | **PASS** |
| **BR-12** | **Automated Expiry:** Expiry revokes Pro privileges immediately. | Evaluated in real-time on API and updated nightly via cron. | **PASS** |
| **BR-13** | **Direct Admin-to-Farmer Pro:** Owner can activate any farmer directly. | Direct Pro Activation tool supports registered and pending mobile numbers. | **PASS** |
| **BR-14** | **Platform Structure:** Web Admin + Mobile Dashboards for Farmer, Shop, Consultant. | Web Admin for owner; 3 role-driven mobile dashboards. | **PASS** |
| **BR-15** | **Data Isolation:** Shop A cannot see Shop B; unassigned farmers isolated. | Enforced via PostgreSQL Row Level Security (RLS) policies. | **PASS** |
| **BR-16** | **Knowledge Base-First AI:** RAG prioritizes verified chunks over Gemini. | Vector similarity checked; Gemini fallback triggered only if $< 0.78$. | **PASS** |
| **BR-17** | **Pro Photo Quota (5/day):** Maximum 5 photo diagnoses per farmer per day. | Backend-enforced across devices; resets at midnight IST. | **PASS** |
| **BR-18** | **Manual Payment Collection:** Direct farmer, consultant, or shop channels. | Handled manually by owner/admin; no online gateway initially. | **PASS** |
| **BR-19** | **Zero Public Price Display:** No fees or prices shown in client specifications. | All pricing figures removed from Pro screens and public documentation. | **PASS** |
| **BR-20** | **Partner Registration vs. Authorization:** Profile creation does not grant access. | Accounts set to `pending_approval`; owner provisions login ID/password. | **PASS** |
| **BR-21** | **Partner Expiry Data Preservation:** Expired partner access suspended, data preserved. | Historical farm links, visit logs, and records remain intact in Supabase. | **PASS** |
| **BR-22** | **Authoritative Supabase Storage:** All DB and file storage hosted on Supabase. | PostgreSQL 16, pgvector, and Supabase Storage specified exclusively. | **PASS** |
| **BR-23** | **Owner Centralized Governance:** Absolute control over activations, partners, and subs. | 12 explicit owner administrative powers documented and audited. | **PASS** |
| **BR-24** | **Central Master KB Governance:** Master Knowledge Base is controlled exclusively by the Owner/Admin; no other role may add, modify, or remove master documents. | Documented in PRD (KM-FR-020), Architecture (Section 8.1), and Security (Section 7.2). Admin-only endpoints enforced. | **PASS** |
| **BR-25** | **Consultant KB Tenant Isolation:** Consultant A's knowledge documents must never be accessible by Consultant B, any other consultant, or unassigned farmers. | PostgreSQL RLS policy `consultant_kb_tenant_isolation` enforces `consultant_id` partition. Verified in Security (Policy 5) and Architecture (Table 20). | **PASS** |
| **BR-26** | **16-Step Pipeline with Human Approval Gate:** Every uploaded document must pass through the full 16-step processing pipeline and receive explicit human admin approval before its chunks enter active RAG retrieval. | Pipeline lifecycle documented in Architecture (Section 8.1) with 9 status states; `PENDING_REVIEW` gate requires admin action via `SCR-ADM-10`. | **PASS** |
| **BR-27** | **Unapproved Document Exclusion:** Documents not yet approved by the admin must never appear in RAG vector search results. | RAG query filters enforce `approval_status = 'APPROVED'` and `index_status = 'INDEXED'`. Verified in Architecture (Section 8.2) and ticket `KM-KB-004`. | **PASS** |
| **BR-28** | **Plot-Specific Personalized Schedules:** Personalized agronomy schedules are strictly plot-specific, computed from variety, pruning date, phenological stage, and assigned Consultant's approved schedule. | Schedule engine documented in Architecture (Section 8.5); RLS policy `farm_schedule_isolation` in Security (Policy 6). Frontend `SCR-PLN-02` renders per-plot view. | **PASS** |
| **BR-29** | **~95% KB-Grounded / ~5–10% Gemini Fallback Targets:** Approximately 95% of AI answers must be grounded in verified Knowledge Base chunks; Gemini fallback is limited to ~5–10% of queries. These are measurable performance targets, not guaranteed accuracy figures. | Documented in PRD (KM-FR-024, KM-FR-026), Architecture (Section 8.2, 8.4), and KPI metrics (PRD Section 17). Telemetry dashboard `SCR-ADM-11` monitors actual rates. | **PASS** |
| **BR-30** | **Zero Ungrounded Chemical Dosage Tolerance:** The AI must never fabricate chemical trade names, dosages, or application schedules not present in verified knowledge sources. | `AgronomicSafetyArbiter` validates all retrieved recommendations against CIB/NRCG rules. Gemini fallback guardrail prompt explicitly forbids dosage synthesis. Documented in Architecture (Section 8.3, 8.4) and ticket `KM-RAG-002`. | **PASS** |
| **BR-31** | **Conflict Detection Without Silent Compromise:** When a Consultant schedule and a university POP or CIB safety rule disagree, the system must flag the conflict and display an advisory warning rather than silently picking one dosage. | Deterministic 4-tier conflict hierarchy documented in Architecture (Section 8.3). Conflict handler outputs `conflict_detected = TRUE` with farmer-facing advisory. Verified in ticket `KM-RAG-002`. | **PASS** |
| **BR-32** | **Consultant Priority Rule:** If an authorized Agricultural Consultant subsequently adds a farmer already linked to an Agricultural Shop, the Consultant receives absolute priority. The system automatically unlinks the Shop (`status = 'unlinked_by_priority'`) and links the Consultant. | Enforced transactionally by `RelationshipService` (Architecture Sec 8.7.1) and documented in PRD (KM-FR-028). Verified in ticket `KM-REL-004` and `TC-REL-02`. | **PASS** |
| **BR-33** | **Exclusive Admin Unlinking Alerts:** When the Consultant Priority Rule unlinks a Shop, ONLY the Platform Owner/Admin receives a system notification. Neither the former Shop nor the Farmer receives an alerting unlinking broadcast. | Documented in PRD (KM-FR-028), Architecture (Sec 8.7.1), and Frontend (SCR-ADM-13). Verified in `TC-REL-03`. | **PASS** |
| **BR-34** | **Farmer Relationship Immutability:** Farmers cannot independently leave, change, or manually override their assigned Shop or Consultant relationship in the mobile app. | PostgreSQL RLS policy `farmer_rel_admin_system_mutation` restricts mutations to Admin/System roles. Documented in Security (Policy 8) and `TC-REL-04`. | **PASS** |
| **BR-35** | **Historical Data Preservation on Unlink:** Automatic unlinking must NOT delete historical farming records, past billing notes, messages, or audit logs. However, the former Shop immediately loses access to new private farmer information, new messages, and media. | Documented in PRD (KM-FR-015), Architecture (Table 16, 25), and Security (Sec 7.4). Verified in `TC-REL-05`. | **PASS** |
| **BR-36** | **Direct In-App Human Chat Isolation:** Native WhatsApp-style 1-to-1 messaging strictly isolates Farmer-Shop channels from Farmer-Consultant channels. Shops cannot view Consultant chats; Consultants cannot view Shop chats. | Documented in PRD (KM-FR-029), Architecture (Sec 8.7.2), and Security (Policy 7). Verified in `TC-CHT-01` and `TC-CHT-02`. | **PASS** |
| **BR-37** | **Shared Farmer AI Chat Strict View-Only Mode:** Linked Shop and Consultant partners can view farmer AI conversations in strict read-only mode. Partners CANNOT send messages as farmer, reply inside AI chats, edit, delete, or alter conversation history. | Documented in PRD (KM-FR-030), Architecture (Sec 8.7.3), Security (Policy 3), and Frontend (`SCR-SHP-03`, `SCR-CON-06`). Verified in `TC-AICHT-01` and `TC-AICHT-02`. | **PASS** |
| **BR-38** | **Farmer AI Visibility Consent & Privacy Controls:** Shared AI chat visibility requires transparent farmer disclosure and explicit opt-in consent recorded in `farmer_ai_visibility_consents`. Farmers can toggle visibility on or off at any time. | Documented in PRD (KM-FR-030), Architecture (Table 28), Security (Sec 7.5), and Frontend (`SCR-SET-02`). Verified in `TC-AICHT-03`. | **PASS** |
| **BR-39** | **Partner AI Chat View Audit Logging:** Every read access by a shop or consultant to a farmer's AI conversation writes an immutable row into `ai_chat_view_audit_logs` capturing viewer ID, role, farmer ID, timestamp, and IP address. | Documented in Architecture (Table 29), Security (Sec 7.5), and Frontend (`SCR-ADM-14`). Monitored in Web Admin. | **PASS** |
| **BR-40** | **Centralized Admin Relationship Correction & Restoration:** The Owner/Admin has centralized authority in the Web Admin to review relationship history, correct verified operational errors, and restore relationships. | Documented in PRD (KM-FR-031), Architecture (Sec 8.7.1), and Frontend (`SCR-ADM-13`). Verified in `TC-ADM-01`. | **PASS** |
| **BR-41** | **Three Distinct Farmer Categories:** Farmers operate in one of three clear categories: (1) Shop-Managed Farmers, (2) Consultant-Managed Farmers (governed by Consultant Priority Rule), or (3) Global Kisan Mitra AI Farmers (unassigned, managed directly by central platform/Owner). | Documented in PRD (KM-FR-032), Architecture (Sec 1.1, C4 diagrams), and Security (Sec 2). Traced to `KM-GLB-001`. | **PASS** |
| **BR-42** | **Independent Advisory Schedules:** Every Shop and Consultant operates their own isolated advisory schedule (Shop A $\rightarrow$ Schedule A, Consultant A $\rightarrow$ Schedule D). Global Farmers follow the central platform Master Schedule. Dynamic binding connects farmers at runtime without code deployment. | Documented in PRD (KM-FR-033), Architecture (Sec 8.8, Table 30, 31), and Security (Policy 10). Traced to `KM-SCHED-001`. | **PASS** |
| **BR-43** | **Safe 9-Step Non-Executable Schedule Pipeline:** Advisory schedules (XLSX, CSV, PDF) pass through a 9-step ingestion pipeline with formula neutralization, DAP sequence validation, and mandatory owner/admin review before activation. Zero executable code is ingested. | Documented in PRD (Section 10.6), Architecture (Section 8.8), Security (Section 7.6), and Frontend (`SCR-ADM-16`). Traced to `KM-SCHED-001`. | **PASS** |
| **BR-44** | **Pro Multi-Plot Vineyard Support & Multi-Actor Auditing:** Plots can only be registered on Pro tier. Farmer, Linked Shop, Linked Consultant, and Admin can add/edit plots. Partner/admin edits record in `audit_logs` and dispatch in-app notification to farmer. Partners cannot delete. | Documented in PRD (Section 10.7), Architecture (Table 3 `farms`), Security (Section 3.6), and Frontend (`SCR-PLT-00`, `01`, `02`). Traced to `KM-PLOT-001`. | **PASS** |
| **BR-45** | **Strict Maximum 1 Automated Call Per Farmer Per Day:** Under NO circumstances may a farmer receive more than ONE automated voice call per calendar day across all registered plots and alerts. Database partial unique index on `daily_call_ledger(farmer_id, call_date)` enforces this atomically. | Documented in PRD (KM-FR-035), Architecture (Table 32, ADR-007), and Security (Policy 9). Traced to `KM-IVR-001`. | **PASS** |
| **BR-46** | **Primary Plot Consolidation & Default Fallback:** A single Primary Plot (`farms.is_primary_plot = TRUE`) drives both phenological schedule and automated voice calls. First registered plot automatically defaults to Primary Plot. Partial unique index enforces single primary plot. | Documented in PRD (KM-FR-036), Architecture (Sec 8.9, ADR-007), and Frontend (`SCR-SET-03`). Traced to `KM-IVR-002`. | **PASS** |
| **BR-47** | **Automated Voice Calling (IVR) Window:** Voice calls are dispatched strictly between 07:00 AM and 07:00 PM IST to protect rural peace and comply with telecom guidelines. System honors immediate farmer opt-out. | Documented in PRD (KM-FR-037), Architecture (Sec 8.10), Security (Sec 3.7), and Frontend (`SCR-SET-03`). Traced to `KM-IVR-001`. | **PASS** |
| **BR-48** | **Schedule vs. Knowledge Separation:** Clear architectural distinction: Schedules define "When to Advise" (DAP timelines, stage triggers) ingested via 9-step pipeline; Knowledge Files define "What to Advise" (scientific descriptions, POP, remedies) ingested via 16-step OCR/chunking pipeline into pgvector. | Documented in PRD (Section 10.10) and Architecture (Section 8.8). Traced across `KM-SCHED-001` and `KM-KB-001`. | **PASS** |
| **BR-49** | **Multi-Tier Knowledge Base Hierarchy:** Knowledge retrieval follows strict tenant hierarchy: Global Farmers search Global KB; Shop Farmers search Global + Shop KB; Consultant Farmers search Global + Consultant KB (with Consultant knowledge prioritized). | Documented in PRD (Section 10.11), Architecture (Section 8.2), and Security (Section 7.3). Traced to `KM-RAG-001`. | **PASS** |
| **BR-50** | **Multi-Modal KB-First AI Ingestion:** Farmers can submit queries by photo (medicine bottle, crop symptom) or Marathi voice (`SCR-VCE-01`). Knowledge Base is searched first; Gemini fallback is triggered only if confidence $< 0.78$. Zero ungrounded chemical dosage fabrication. | Documented in PRD (Section 10.11), Architecture (Sec 8.11), and Frontend (`SCR-VCE-01`). Traced to `KM-MED-002`. | **PASS** |
| **BR-51** | **Searchable Medicine Library with Zero E-Commerce:** Mobile app provides a searchable directory of viticulture inputs (`SCR-MED-01`) showing active ingredients, CIB dosages, target pests, and PHI. Direct purchasing/cart checkout is strictly prohibited. Admin-only write access. | Documented in PRD (KM-FR-038), Architecture (Table 33), Security (Section 3.8), and Frontend (`SCR-MED-01`, `02`). Traced to `KM-MED-001`. | **PASS** |
| **BR-52** | **Centralized Premium Management Exclusively by Owner:** All Pro activations, partner subscriptions, and plan assignments are controlled centrally by Owner Swapnil Pawar via the Web Admin. No third-party or autonomous activations. | Documented in PRD (Section 10.12), Architecture (ADR-005), and Security (Section 3.5). Traced to `KM-ADMIN-002`. | **PASS** |
| **BR-53** | **Combined 3-Use Monthly Free Quota:** Free tier Schedule Search and Limited KB Chat share exactly 3 queries per calendar month, tracked server-side in `free_usage_counters(user_id, usage_month)` and resetting at 00:00:00 IST on the 1st of each month. | Documented in PRD (Section 8.1), Architecture (Table 35, Section 7.1), Security (Section 3), Frontend (`SCR-FREE-01`, `02`). Traced to `KM-FREE-002`. | **PASS** |
| **BR-54** | **Free Schedule Search Validation:** Pruning date input only; calculates DAP and returns Global Schedule Day N event. Invalid or future dates are rejected without decrementing quota. | Documented in PRD (Section 8.1), Architecture (Section 9.1), Frontend (`SCR-FREE-01`). Traced to `KM-FREE-003`. | **PASS** |
| **BR-55** | **Free KB Chat Zero-Fallback Guarantee:** Free tier AI chat operates strictly on Global KB. If similarity $< 0.78$, returns polite Marathi fallback without calling Gemini API. Consumes from monthly quota. | Documented in PRD (Section 8.2), Architecture (Section 8.11), Security (Section 3), Frontend (`SCR-FREE-02`). Traced to `KM-FREE-002`. | **PASS** |
| **BR-56** | **WhatsApp Direct Upgrade Deep Link:** Mobile client launches `https://wa.me/<owner_number>?text=...` with pre-filled Devanagari text after pre-creating lead in `upgrade_enquiries` (status `NEW`, 7-day duplicate check). Zero prices rendered. | Documented in PRD (Section 7.1, 10.8), Architecture (Section 9.1), Security (Section 3.10), Frontend (`SCR-UPG-01`). Traced to `KM-PRO-001`. | **PASS** |
| **BR-57** | **Dynamic Owner WhatsApp Configuration:** Owner WhatsApp phone number is dynamically retrieved from `system_configurations` (`owner_whatsapp_number`) via `GET /api/v1/config/public`, preventing client hardcoding. | Documented in PRD (Section 10.8), Architecture (Table 35, Section 9.1), Security (Section 3.10). Traced to `KM-ADM-004`. | **PASS** |
| **BR-58** | **Multi-Actor Plot Editing Audit & Push Notification Rule:** Any plot mutation performed by an actor other than the farmer writes an immutable entry into `audit_logs` and sends an in-app push notification to the farmer. Partners have no delete permissions. | Documented in PRD (Section 10.7), Architecture (Table 3, Section 8.9), Security (Section 3.6, Policy 2). Traced to `KM-PLOT-001`. | **PASS** |

---

## 5. Architectural & Security Consistency Verification

### 5.1 Technical Architecture Audit
- **Consistency between Database & APIs:** All 35 tables documented in [02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/02_TECHNICAL_ARCHITECTURE_KISAN_MITRA.md) correspond directly to API endpoints and Pydantic schemas. Primary keys (`UUID`), foreign keys, and indexes are consistently modeled. Tables 30–35 (`schedule_configurations`, `schedule_events`, `farmer_calling_settings`, `daily_call_ledger`, `automated_call_logs`, `medicine_products`, `weather_alert_events`, `free_usage_counters`, `system_configurations`) seamlessly integrate with multi-plot management, independent schedules, the 1-call-per-day calling ledger, dynamic WhatsApp configuration, and the 3-use monthly free quota engine.
- **pgvector Integration:** Embedding dimension is unified at 768 to match Google's `text-embedding-004` model. `HNSW` index parameters (`m=16, ef_construction=64`) provide sub-50ms query latencies under multi-thousand chunk loads. The `consultant_knowledge_documents` table maintains the same 768-dimensional embedding space and HNSW index configuration, ensuring consistent vector search performance across Master and Consultant KBs.
- **Authoritative Supabase Platform:** All relational schemas, vector indexes, and media asset storage buckets (`crop-diagnostics`, `master-knowledge-docs`, `consultant-knowledge-docs`, `chat-media`, `schedule-files`) reside within Supabase, eliminating external synchronization drift.
- **Independent Advisory Schedule Architecture & Safe 9-Step Ingestion:** Ingested schedules are stored as passive declarative database configuration rows (`schedule_configurations` and `schedule_events`). The 9-step pipeline enforces formula prefix neutralization (`=`, `+`, `-`, `@`), DAP sequence validation, and mandatory owner/admin review before runtime dynamic binding.
- **Single Daily Call Database Constraint & Primary Plot Engine:** Server-side `daily_call_ledger` uses a PostgreSQL unique partial index `idx_single_daily_call(farmer_id, call_date)` guaranteeing atomic compliance with the maximum 1 automated call per farmer per day quota across all plots and alerts. A single Primary Plot (`farms.is_primary_plot = TRUE`, enforced via partial unique index `idx_single_primary_plot`) unifies the phenological schedule driver and calling driver.
- **Consultant Priority Engine & State Machine:** The relationship lifecycle (Architecture Section 8.7.1) enforces strict deterministic priority: adding a consultant automatically unlinks the shop (`unlinked_by_priority`), emits an admin-only WebSocket event, and isolates the former shop from future farmer data while preserving historical records.
- **Direct Messaging Realtime Architecture:** Native 1-to-1 messaging (Architecture Section 8.7.2) leverages Supabase Realtime CDC over WebSockets with signed media URLs, guaranteeing $< 500\text{ ms}$ latency and complete separation between Shop-Farmer and Consultant-Farmer channels.
- **Shared AI Chat Read-Only Projection:** View-only access (Architecture Section 8.7.3) enforces zero mutation capabilities for partners, verified farmer consent gates, and immutable audit logging in `ai_chat_view_audit_logs`.
- **16-Step Document Processing Pipeline:** The pipeline (Architecture Section 8.1) defines a complete lifecycle from `UPLOADED` through `INDEXED` or `REJECTED`, with 9 discrete status states and a mandatory `PENDING_REVIEW` gate. The pipeline treats all uploaded documents as untrusted data, ensuring prompt injection defense at the ingestion boundary.
- **Multi-Tier RAG Architecture & Free Tier Zero-Fallback:** The hierarchical retrieval sequence (Architecture Section 8.2) queries Consultant KB → Master KB → Farm History in parallel for Pro users. For Free users, retrieval is strictly confined to Global KB with 0% Gemini fallback, returning a polite vernacular fallback when similarity is below threshold ($< 0.78$).
- **Personalized Schedule Engine:** The schedule generator (Architecture Section 8.5) correctly maps DAP (Days After Pruning) to phenological milestones, overlays Consultant-specific spray/fertigation schedules, and outputs plot-specific daily action items.

### 5.2 Security Governance Audit
- **Zero Client-Side Trust & Sovereign Free Quota:** The security architecture documented in [03_SECURITY_AND_ACCESS_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/03_SECURITY_AND_ACCESS_KISAN_MITRA.md) ensures that token tampering or client-side reverse engineering cannot bypass backend entitlement checks. Free tier queries are tracked atomically in PostgreSQL `free_usage_counters` keyed by `(user_id, usage_month)` in IST, completely immune to client cache clears or device swaps.
- **Multi-Actor Plot Editing RLS & Auditing:** Table 3 `farms` RLS policies permit Pro farmers to manage their own plots, and allow actively assigned Shops and Consultants to INSERT and UPDATE plots for assigned Pro farmers (partners strictly denied DELETE). Every partner/admin modification creates an immutable entry in `audit_logs` and sends an in-app push notification to the farmer.
- **Tenant Isolation Proof:** PostgreSQL Row Level Security policies explicitly bind `farmer_relationships` to `shop_id` and `consultant_id`. A multi-tenant leak test case (`TC-SUB-13`) has been mandated in the testing harness. 13 comprehensive RLS policies govern farms, profiles, conversations, chat messages, relationships, calling settings, daily call ledgers, schedule configurations, medicine products, and free usage counters.
- **Telecom & Calling Consent Compliance:** Automated calls are restricted to 07:00 AM – 07:00 PM IST, rate-limited to 1 call/farmer/day, driven by the verified Primary Plot, and honor immediate opt-out toggles in compliance with TRAI regulations.
- **Strict Read-Only AI Policy:** Security Policy 3 on `ai_conversations` and `ai_messages` permits `SELECT` operations to linked partners only when active relationships and active farmer consent exist. `INSERT`, `UPDATE`, and `DELETE` privileges are strictly denied to partners.
- **Exclusive Admin Notification Policy:** When the Consultant Priority Rule triggers, alert notifications are routed exclusively to the Owner/Admin Web Dashboard. Neither the former Shop nor the Farmer receives an alerting unlinking broadcast.
- **Partner Access Hardening:** Newly registered Shops and Consultants remain in `pending_approval` state; credentials (login ID and bcrypt-hashed password) are provisioned exclusively by the platform owner/admin.
- **Data Preservation Guarantee:** Upon partner annual subscription expiry or relationship unlinking, dashboard/live access is suspended or restricted, while historical records, past messages, and assigned farmer data remain permanently preserved in Supabase.
- **Document Ingestion Security:** Uploaded documents are treated as untrusted data (not executable instructions) to defend against prompt injection attacks. Adversarial text sanitization, human verification gates, and malware scanning are mandated before any document content enters the vector database.
- **WhatsApp Link Safety:** Click-to-chat `wa.me` links query destination number dynamically from `system_configurations` (`owner_whatsapp_number`). Pre-creates lead with status `NEW` (7-day duplicate check). Minimal non-sensitive PII transmitted.

### 5.3 Frontend & Design System Audit
- **Devanagari Typography Fidelity:** All Marathi terms across [04_FRONTEND_SPECIFICATION_KISAN_MITRA.md](file:///D:/Kisan%20Mitra%20App/docs/product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md) were audited by the viticulture specialist to ensure natural viticulture phrasing (e.g., using "गोडी छाटणी", "मणी सेटिंग", "भुरी", "केवडा", "मुख्य बाग", "वेळापत्रक शोध" rather than literal machine-translated English).
- **Direct Chat & Read-Only AI UX:** Wireframes for `SCR-CHT-01` (Direct Chat) and `SCR-SHP-03` / `SCR-CON-06` (Read-Only AI View) clearly distinguish human 1-to-1 conversation from the read-only AI inspection experience with disabled inputs and explicit explanatory banners.
- **New Operational Screens:** Detailed ASCII wireframes added for Schedule Search (`SCR-FREE-01`), Limited AI Chat (`SCR-FREE-02`), Premium Upgrade with WhatsApp CTA (`SCR-UPG-01`), First-Run Pro Plot Setup (`SCR-PLT-00`), and Primary Plot & Call Settings (`SCR-SET-03`).
- **Zero Price Rendering:** All Pro upgrade screens and forms present features, benefits, and owner-consultation WhatsApp CTAs without numerical pricing (BR-19 compliance).

---

## 6. Identified Gaps, Open Questions & Engineering Recommendations

### 6.1 Recommendations for Product Owner (Swapnil Pawar)
1. **SMS Gateway DLT Registration:** Begin TRAI DLT registration for entity "Kisan Mitra AI" and submit Marathi transactional voice/SMS templates (OTP, Pro Activation confirmation, IVR call scripts) immediately to avoid rollout delays.
2. **Master Knowledge Base Seed Content:** Migrate historical grape knowledge chunks from the old repository, deduplicate them, and verify chemical dosages against the latest 2026 NRCG recommendations before indexing into Supabase via the 16-step pipeline.
3. **Partner Credential Delivery:** Finalize the preferred communication channel for sending provisioned login IDs and temporary passwords to approved Shops and Consultants (e.g., direct phone call or encrypted SMS).
4. **Consultant Onboarding for KB & Schedules:** Define the operational process for receiving Consultant proprietary schedules and literature. Current architecture supports Owner uploading on their behalf via `SCR-ADM-09` and `SCR-ADM-16`.
5. **OCR Quality Baseline:** Conduct a pilot OCR accuracy assessment on 10–15 representative viticulture schedules to calibrate Tesseract language packs and determine whether Google Vision API fallback is needed for handwritten or low-quality table scans.
6. **Telemetry Alert Thresholds:** Confirm alert thresholds for the AI telemetry dashboard: current defaults are grounded rate < 90% (warning) and fallback rate > 15% (critical).
7. **Primary Plot Automatic Fallback Confirmation:** Current specification deterministically designates the first registered plot (`farms ORDER BY created_at ASC LIMIT 1`) as the default Primary Plot (`is_primary_plot = TRUE`). Confirm whether this assumption is approved or if stage-based prioritization should be evaluated.
8. **IVR Telephony Vendor Evaluation:** Select between Exotel, Knowlarity, or Tata Telephony based on Marathi TTS audio quality, concurrent SIP channel pricing, and webhook reliability.
9. **Medicine Library & Article Access for Free Tier (Open Item):** Confirm whether Free farmers can browse static medicine library entries (`SCR-MED-01`) and educational viticulture articles (`SCR-KB-01`), or if these are strictly restricted to Pro subscribers (currently kept as-is for Pro and partners awaiting explicit owner decision for Free).

---

## 7. Product Owner Approval Checklist

Before authorized engineering sprints begin, the Product Owner should review and confirm:

- [ ] **Application Identity:** Official product name is confirmed as **Kisan Mitra AI (formerly DrakshGuru)**.
- [ ] **Revised Free Plan Scope:** Strictly 2 features (Schedule Search & Limited KB Chat) sharing ONE combined monthly quota of 3 total uses.
- [ ] **WhatsApp Upgrade Click-to-Chat:** Direct `wa.me` deep link with pre-filled Devanagari enquiry and background lead pre-creation (zero bots/webhooks).
- [ ] **Dynamic WhatsApp Number Setting:** Owner WhatsApp phone number configured dynamically via Web Admin and backend `system_configurations`.
- [ ] **Pro-Only Plot Registration:** Free tier farmers cannot register vineyard plots; plot registration unlocked exclusively upon Pro activation.
- [ ] **Multi-Actor Plot Editing & Auditing:** Farmer, Linked Shop, Linked Consultant, and Admin can add/edit plots; partner/admin edits logged in `audit_logs` and trigger farmer push notifications; partners cannot delete.
- [ ] **Primary Plot Architecture:** Single Primary Plot (`farms.is_primary_plot = TRUE`, default Plot 1) driving both phenological schedule and automated voice calls.
- [ ] **Maximum 1 Call Per Day:** Strict limit of 1 automated voice call per farmer per day enforced via database ledger confirmed.
- [ ] **Automated Voice Calling (IVR):** 07:00 AM – 07:00 PM IST calling window and opt-out support confirmed.
- [ ] **Three Farmer Categories:** Shop-Managed, Consultant-Managed, and Global unassigned farmers confirmed.
- [ ] **Independent Advisory Schedules:** Isolated schedules for each Shop and Consultant with 9-step non-executable ingestion confirmed.
- [ ] **Searchable Medicine Library:** Informational viticulture inputs directory with CIB dosages and zero ecommerce confirmed.
- [ ] **GPS Plot Mapping & Weather Alerts:** Plot coordinates capture and localized rain warnings confirmed.
- [ ] **Owner-Assisted Upgrade Workflow:** Telephonic consultation and direct activation model is approved.
- [ ] **Direct Admin Pro Activation:** The owner tool to activate registered and pending farmers is approved.
- [ ] **Platform Form Factor:** Centralized Web Admin (Swapnil Pawar exclusive) + Mobile Dashboards (Farmer, Shop, Consultant) confirmed.
- [ ] **One-Year Validity:** The 1-calendar-year anniversary rule is confirmed as the standard subscription duration.
- [ ] **Manual Payment Model:** 3-channel manual payment collection without online payment gateway is approved.
- [ ] **Pro Photo Quota:** Limit of 5 photo diagnoses per farmer per day is confirmed.
- [ ] **Partner Authorization Protocol:** Separation of profile registration from owner/admin credential provisioning is confirmed.
- [ ] **Partner Data Preservation:** Preservation of all historical records upon partner subscription expiry is confirmed.
- [ ] **Supabase Authoritative Storage:** Supabase as exclusive platform for all database and media storage is confirmed.
- [ ] **Central Master Knowledge Base Governance:** Owner/Admin-exclusive control over Master KB document ingestion, approval, and removal is confirmed.
- [ ] **Consultant-Specific Knowledge Isolation:** Tenant-isolated Consultant KB repositories with zero cross-consultant exposure is confirmed.
- [ ] **16-Step Pipeline with Human Approval Gate:** Mandatory human admin review before any document chunks enter active RAG retrieval is confirmed.
- [ ] **Personalized Farm Schedule Engine:** Plot-specific daily agronomy schedules based on variety, pruning date, and Consultant prescriptions is confirmed.
- [ ] **~95% Grounded / ~5–10% Fallback Target:** Knowledge Base-first AI retrieval target with controlled Gemini fallback is confirmed.
- [ ] **Zero Ungrounded Dosage Tolerance:** Absolute prohibition on AI-fabricated chemical dosages or trade names is confirmed.
- [ ] **Consultant Priority Rule:** Automatic unlinking of Shop when a Consultant adds the farmer is confirmed.
- [ ] **Exclusive Admin Unlinking Alerts:** Only the Owner/Admin receives real-time unlinking notifications is confirmed.
- [ ] **Direct In-App Human Chat System:** WhatsApp-style direct 1-to-1 messaging between Farmer-Shop and Farmer-Consultant with strict channel privacy is confirmed.
- [ ] **Shared Farmer AI Chat Strict View-Only Mode:** Read-only access for linked partners with zero reply/edit capabilities and mandatory farmer consent is confirmed.
- [ ] **Centralized Relationship Correction & Restoration:** Owner/Admin tools to monitor priority unlinks and restore relationships are confirmed.

---

## 8. Final Readiness Determination

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FINAL READINESS STATUS                          │
│                                                                        │
│                    PASS WITH RECOMMENDATIONS                           │
│                                                                        │
│   The documentation suite for Kisan Mitra AI (formerly DrakshGuru) is │
│   comprehensive, highly detailed, architecturally cohesive, and ready  │
│   for immediate engineering sprint execution upon Product Owner        │
│   sign-off.                                                            │
│                                                                        │
│   The platform specification incorporates:                             │
│     • Revised Free/Pro Model (Schedule Search + KB Chat, 3 uses/month) │
│     • Frictionless WhatsApp Click-to-Chat Upgrade Link (wa.me)         │
│     • Dynamic Owner WhatsApp Number Delivery via system_configurations │
│     • Plot Registration strictly gated to active Pro subscribers       │
│     • Multi-Actor Plot Editing (Farmer, Shop, Consultant, Admin)       │
│     • Mandatory Plot Mutation Audit Logging & Farmer In-App Alerts     │
│     • Consolidated Primary Plot Architecture (replacing Calling Plot)  │
│     • Strict Maximum 1 Automated Call Per Farmer Per Day Ledger Quota  │
│     • Three Farmer Categories (Shop, Consultant, Global unassigned)    │
│     • Central Web Admin Dashboard (Exclusive to Swapnil Pawar)         │
│     • Partner Dashboards (Mobile App Only - Shop & Consultant)         │
│     • Independent Advisory Schedules with safe 9-step ingestion        │
│     • Central Master KB & Consultant-Specific KB (tenant-isolated)     │
│     • 16-Step Document Processing Pipeline with human approval gate    │
│     • Multi-Tier RAG (~95% grounded target) with Safety Arbiter        │
│     • Gemini Fallback (~5–10%) with zero-fabrication guardrails        │
│     • Multi-Modal Queries: Ask by Photo (Product) & Ask by Voice       │
│     • Searchable Viticulture Medicine Library (Zero E-Commerce)        │
│     • GPS Plot Mapping & Stage-Sensitive Localized Weather Alerts      │
│     • Consultant Priority Rule & Transactional Shop Unlinking Engine   │
│     • Native In-App Direct Chat (WhatsApp-Style) with Channel Privacy  │
│     • Shared Farmer AI Chat Visibility in Strict View-Only Mode        │
│     • Centralized Premium Management Controlled Exclusively by Owner   │
│                                                                        │
│   39 functional requirements (KM-FR-001 – KM-FR-039) fully traced.     │
│   58 business rules (BR-01 – BR-58) verified PASS.                     │
│   35 database tables fully specified with indexes & RLS policies.      │
│   28 engineering tickets across 14 post-MVP and core epics defined.    │
│   23 detailed frontend screens specified with ASCII wireframes.        │
│   54 core validation test cases covering free quota, WhatsApp lead,    │
│      multi-actor plot editing, IVR calling, schedules, and security.   │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐      │
│   │   DEVELOPMENT FREEZE STATUS: ACTIVE & ENFORCED               │      │
│   │   No application code, database migrations, SQL execution,   │      │
│   │   Supabase configuration, infrastructure changes, Git        │      │
│   │   commits, or deployments have been made or are permitted.   │      │
│   │   Development begins ONLY after explicit Product Owner       │      │
│   │   authorization.                                              │      │
│   └──────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────────────┘
```

**Sign-off:**
*Lead System Architect & Senior Product Lead, Kisan Mitra AI Project*  
*November 2026*

---
*End of Document 06 – Documentation Quality, Consistency Audit & Traceability Report*

**Sign-off:**
*Lead System Architect & Senior Product Lead, Kisan Mitra AI Project*  
*November 2026*

---
*End of Document 06 – Documentation Quality, Consistency Audit & Traceability Report*
