# Agricultural intelligence implementation plan

**Status:** Stage 1F architecture preparation, updated for authorized Stage 2A source work on 2026-11-27. No AI, embedding, or live weather provider is activated. Plot and weather foundation details are in [Stage 2A](STAGE2A_PLOTS_WEATHER.md). Other proposed components remain unimplemented.

## Existing evidence

| Component | Status | Repository evidence / next gap |
| --- | --- | --- |
| Knowledge-first AI routing | **Partial** | `backend/app/services/ai_router.py` has a `KnowledgeBase` protocol, threshold, text/image routing, escalation, and safety prompts. No authenticated production route, approved corpus, citations, or tenant-aware retrieval. |
| Gemini abstraction | **Partial** | `gemini_client.py` has provider selection and a free-tier guard. Actual account tier, rate limits, data terms, and live model compatibility have not been checked. No external calls are authorized. |
| Usage and cost controls | **Partial** | `usage_monitor.py` has local counters, limits, and a kill switch. Counters are not durable or transactionally reserved across instances. |
| Photo preprocessing | **Partial** | `image_pipeline.py` validates, resizes, and hashes images. Storage, privacy, entitlement, per-Farmer quotas, and real device flows are absent. |
| Farmer plots | **Source implemented, database unverified** | `0009_farmer_plots`, `backend/app/plots.py`, authenticated API routes, and mobile plot manager exist. PostgreSQL and mobile builds have not run. |
| Plot-specific weather context | **Partial** | `backend/app/weather.py` defines injected provider, plot/location-scoped in-process cache, stale labeling, and unavailable fallback. No live provider, durable cache, or real forecast validation. |
| Document ingestion/versioning | **Missing** | No PDF, Word, Excel, CSV, or text ingestion worker or approved-document lifecycle. |
| Hybrid RAG and consultant isolation | **Missing** | No persisted chunks, embeddings, scoped retrieval, reranking, or citation verifier. |
| Agricultural evaluation | **Missing** | No curated bilingual answer set, dosage safety gate, or expert review loop. |

## Proposed implementation order

1. **Independent Farmer plots.** Reuse `users`/Farmer profile identity. Add owner- and Farmer-authorized plot records with unique Farmer-scoped plot IDs, optional coarse location, crop, and one transactionally enforced primary plot. Do not require Shop or Consultant relationship. Plot permissions come from the later relationship engine, not plot ownership by a partner.
2. **Weather context.** Define a provider protocol returning source, observed/forecast time, units, location precision, expiry, and confidence. Use plot location only after consent; default to a coarse district forecast. Cache by provider, coarse location, time window, and units with stale-data labeling. On timeout or provider failure, show the last safe cached result with age or report unavailable. Never silently invent current weather.
3. **Approved knowledge lifecycle.** Accept PDF, DOCX, XLSX, CSV, and UTF-8 text through private storage; validate MIME and size, scan for malware, reject spreadsheet formulas/macros for processing, and preserve source checksums. Extract page/sheet/row references and metadata including crop, growth stage, region, language, author, effective date, and approval status. Keep immutable document versions and review events. No private Consultant file leaves the approved storage boundary.
4. **Chunking and indexing.** Split by headings, tables, pages, and semantic sections while preserving dosage units and provenance. Store chunk text, source offsets, approval version, scope (`global` or Consultant ID), language, and active/withdrawn state. Build PostgreSQL full-text indexes first. Evaluate pgvector in a disposable PostgreSQL environment; its official project supports exact search, HNSW/IVFFlat approximate indexes, and hybrid use with PostgreSQL full-text search. Measure recall and tenant filtering before selecting an approximate index. [pgvector project](https://github.com/pgvector/pgvector).
5. **Hybrid retrieval.** Apply authorization and approved-version filters **before** ranking. Combine keyword and semantic candidates, rerank a small bounded set, and return chunk-level citations with document title, version, page/row, and effective date. After relationship revocation, invalidate access to Consultant-private chunks and cached results immediately. Do not treat an embedding match alone as evidence.
6. **Knowledge-first answer service.** Extend the existing `AIRouter` instead of creating another engine. Prefer approved retrieved evidence. Permit Gemini only behind the existing kill switch, entitlement, consent, quota reservation, provider contract, and owner approval. Keep prompts and tool outputs scoped to the requesting Farmer/plot. Return Marathi or English based on stored preference; preserve source wording and units in both languages.
7. **Safety and evaluation.** Build a bilingual gold set from approved agronomy material and Consultant review. Score citation correctness, retrieval recall, plot relevance, uncertainty, language quality, and harmful dosage claims. Refuse pesticide names, mixtures, concentrations, and schedules when no approved source and explicit rule support them. Escalate uncertain or severe cases to a human; log a safe audit trace without private document content.

## Acceptance gates before any live provider

- PostgreSQL migrations, RLS, restricted-role reads, tenant isolation, and cache revocation pass on a disposable database.
- Consent, knowledge approval, retention, external processing, and Consultant-private visibility rules are owner-approved.
- Weather and Gemini provider accounts, current terms, model availability, quotas, and cost ceilings are verified for this project; no assumptions from generic provider pricing.
- Bilingual agronomy evaluation passes a reviewed threshold and adversarial pesticide/dosage tests. Human review is required for high-risk advice.
- No actual Farmer data or private Consultant knowledge is uploaded to an external service during prototype preparation.

**Recommended next isolated prototype:** build plot and weather-provider interfaces with fake adapters and agronomy evaluation fixtures, while Track A completes authentication verification and frontend builds. Do not apply Phase 2 migrations or activate live APIs in Stage 1F.
