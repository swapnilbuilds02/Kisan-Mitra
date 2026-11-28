# External Engineering References — Kisan Mitra

## Purpose

This document indexes useful technical resources from the external reference repository
[codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x)
(local copy: `D:\Kisan-Mitra-References\build-your-own-x`) for use as engineering knowledge
during Kisan Mitra development.

This reference repository is **not** merged into the Kisan Mitra application. It is a
read-only learning reference. External resources must never override owner requirements,
the approved roadmap, or the master project specification.

## Source repository

| Property | Value |
|----------|-------|
| Name | build-your-own-x |
| URL | https://github.com/codecrafters-io/build-your-own-x |
| Local path | D:\Kisan-Mitra-References\build-your-own-x |
| License | CC0 (public domain waiver by CodeCrafters, Inc.) |
| Maintained by | CodeCrafters, Inc. |
| Origin | Started by Daniel Stefanovic |

The repository is a curated compilation of step-by-step guides for re-creating technologies
from scratch. Individual linked tutorials carry their own licenses; verify each upstream
license before reusing any code.

## Usage rules (mandatory)

1. **Owner decisions first.** Explicitly approved owner decisions take priority over every
   external resource.
2. **Master spec second.** The Kisan Mitra master project specification and approved
   roadmap take priority over external tutorials.
3. **Existing code third.** Existing source code and verified tests take priority over
   external tutorials.
4. **Official docs fourth.** Official technology documentation (FastAPI, PostgreSQL,
   pgvector, React Native, Expo, Next.js, Gemini, etc.) takes priority over tutorials.
5. **External tutorials last.** Use only as supplementary engineering knowledge.
6. **No production substitution.** Do not replace PostgreSQL, Redis, FastAPI, React Native,
   Next.js, or Gemini with educational implementations. Do not build our own database, web
   server, or programming language unnecessarily. Use existing production-grade technologies.
7. **No blind copying.** Do not blindly copy tutorial code into production. Review and adapt
   to our stack and security requirements.
8. **License verification.** Verify each upstream tutorial license before reusing code. Not all
   linked tutorials share the CC0 license of the index repository.
9. **No confidential upload.** Do not upload Kisan Mitra code, credentials, or farmer-facing
   agricultural knowledge base content to external services.
10. **No script execution.** Do not execute downloaded scripts or install dependencies without
    reviewing them.

## Relevant resources by category

### A. RAG, knowledge retrieval, embeddings, and vector search

These are most relevant to Phase 5 (Approved knowledge and safe AI), tasks `KM-KB-001` to
`KM-KB-004`, `KM-RAG-001` to `KM-RAG-004`, `KM-AI-001`, `KM-AI-002`.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| RAG for Document Search (LangChain) | https://github.com/langchain-ai/rag-from-scratch | Knowledge-base-first AI router, RAG engine, citations | `KM-RAG-001`, `KM-KB-001` to `KM-KB-004`, `KM-AI-001` | Document chunking, embedding, similarity search, retrieval-augmented generation, citation tracing | Reference for designing the RAG retrieval flow and citation structure; do not copy LangChain code into the FastAPI backend | Python; compatible with our Python backend | Verify langchain-ai repo license |
| LLM Evaluation Harness | https://machinelearningmastery.com/building-a-custom-llm-evaluation-harness-in-python-from-scratch/ | AI telemetry, safety evaluation, dosage safety gate | `KM-RAG-004`, `KM-RAG-002` (safety arbiter) | Test cases, evaluation runner, rule-based and LLM judges, hallucination detection | Reference for building the AI telemetry dashboard and adversarial dosage tests | Python | Review article terms before reuse |
| Build Your Own AI Model — LLM | https://github.com/rasbt/LLMs-from-scratch | Understanding LLM architecture and inference | `KM-AI-002`, `KM-RAG-003` (Gemini fallback) | Transformer architecture, token generation, attention, model inference | Internal knowledge only; understand how Gemini-style models produce output | Python | Verify rasbt repo license |
| Build Your Own AI Model — Reasoning Model | https://github.com/rasbt/reasoning-from-scratch | Inference-time scaling, GRPO, distillation | `KM-RAG-002` (safety arbiter), `KM-AI-002` | Reasoning model internals, inference-time compute | Internal knowledge for safety arbiter design | Python | Verify rasbt repo license |

### B. Vector databases and embeddings

Relevant to Phase 5 (pgvector usage), `KM-RAG-001`, `KM-KB-001` to `KM-KB-004`.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Vector Database from Scratch | https://skyzh.github.io/vector-db-from-scratch/ | pgvector knowledge chunk storage, HNSW/IVF indexes | `KM-RAG-001`, `KM-KB-001` | Vector indexing, approximate nearest neighbor, cosine similarity, HNSW, IVFFlat | Reference for understanding pgvector index behavior and recall/tenant-filtering tradeoffs | Conceptual; we use production PostgreSQL + pgvector | Review site terms |
| Build a Vector Space Indexing Engine in Python | https://boyter.org/2010/08/build-vector-space-search-engine-python/ | Keyword + semantic hybrid retrieval baseline | `KM-RAG-001` | TF-IDF, vector space model, cosine ranking | Reference for hybrid keyword+semantic retrieval before pgvector ranking | Python | Review article terms |

### C. Document search and OCR

Relevant to Phase 5 knowledge ingestion (16-step pipeline), `KM-KB-003`, `KM-KB-004`.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Optical Character Recognition (OCR) | http://aosabook.org/en/500L/optical-character-recognition-ocr.html | Document ingestion OCR step | `KM-KB-003` | OCR pipeline, text extraction from scanned documents | Reference for the OCR stage of the 16-step ingestion pipeline | Conceptual | Review book terms |
| Neural Network OCR | https://web.archive.org/web/2012/http://www.codeproject.com/Articles/11285/Neural-Network-OCR | OCR for knowledge documents | `KM-KB-003` | Neural-network-based OCR | Reference only; we use production OCR tooling | C# (legacy) | Verify archive terms |

### D. Crop image recognition / computer vision

Relevant to Phase 5/6 vision, `KM-VIS-001`, `KM-MED-002`.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Building a Facial Recognition Pipeline with Deep Learning | https://hackernoon.com/building-a-facial-recognition-pipeline-with-deep-learning-in-tensorflow-66e7645015b8 | Crop photo diagnosis pipeline structure | `KM-VIS-001` | Image preprocessing, feature extraction, recognition pipeline, confidence scoring | Reference for structuring the image validation → inference → cache → escalation flow | Python/TensorFlow (legacy) | Review article terms |
| Developing a License Plate Recognition System with ML | https://medium.com/devcenter/developing-a-license-plate-recognition-system-with-machine-learning-in-python-787833569ccd | Image recognition concept reference | `KM-VIS-001` | ML-based visual recognition, training pipeline | Conceptual reference only | Python | Review article terms |
| An Introduction to Convolutional Neural Networks | https://victorzhou.com/blog/intro-to-cnns-part-1/ | CNN foundations for image diagnosis | `KM-VIS-001` | CNN architecture, image classification | Internal knowledge for understanding vision model behavior | Python | Review article terms |

### E. Database management

Relevant to Phase 1 (migrations, RLS), Phase 5 (pgvector), all schema work.

**Restriction:** We use production PostgreSQL 16 + pgvector. These resources are for
understanding internals only; do not build a replacement database.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Let's Build a Simple Database | https://cstack.github.io/db_tutorial/ | Understanding database internals | `KM-FOUND-001` (migration/RLS design) | B+Tree, storage engine, query execution | Internal knowledge for schema and index design decisions | C (educational) | Review article terms |
| Build Your Own Database from Scratch: B+Tree to SQL | https://build-your-own.org/database/ | Database internals, indexing | `KM-FOUND-001`, `KM-RAG-001` | B+Tree indexes, SQL execution, storage | Internal knowledge for index and constraint decisions | Go (educational) | Review site terms |
| Mini-LSM: Build a Database Storage Engine in Rust | https://skyzh.github.io/mini-lsm/ | Storage engine concepts | `KM-FOUND-001` | LSM-tree, write-ahead log, compaction | Internal knowledge only | Rust (educational) | Review site terms |
| A Practical Guide to Building a Cost-Based Query Planner | https://github.com/tuannh982/query-planner-guide | Query planning, index selection | `KM-RAG-001` (retrieval performance) | Query planner, cost estimation, index selection | Internal knowledge for slow-query investigation | Conceptual/GitHub | Verify repo license |

### F. Redis and caching

Relevant to `usage_monitor.py` rate limits, `KM-AIRT-001`, session cache, weather cache.

**Restriction:** We use production Redis 7.2. These are for understanding caching patterns only.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Build Your Own Redis from Scratch | https://build-your-own.org/redis | Redis caching patterns, rate-limit counters | `KM-AIRT-001`, usage monitor | In-memory KV, TTL expiration, rate limiting, pub/sub | Reference for understanding Redis TTL-based quota counters and cache eviction | C++/Go (educational) | Review site terms |
| Build Your Own Redis from Scratch (alternative) | https://www.build-redis-from-scratch.dev/ | Redis protocol and caching | `KM-AIRT-001` | RESP protocol, KV store, expiration | Reference for cache key design and TTL behavior | Conceptual | Review site terms |
| Building a search engine using Redis and redis-py | http://www.dr-josiah.com/2010/07/building-search-engine-using-redis-and.html | Redis-backed search/caching patterns | `KM-AIRT-001`, weather cache | Redis data structures, caching, search indexing | Reference for Redis cache patterns | Python | Review article terms |

### G. LLM evaluation and AI safety

Relevant to Phase 5 safety gates, `KM-RAG-002`, `KM-RAG-004`, `KM-AI-002`.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| LLM Evaluation Harness | https://machinelearningmastery.com/building-a-custom-llm-evaluation-harness-in-python-from-scratch/ | AI telemetry, dosage safety, adversarial testing | `KM-RAG-002`, `KM-RAG-004` | Test cases, evaluation runner, LLM-as-judge, hallucination detection | Reference for bilingual agronomy evaluation set and dosage safety gate | Python | Review article terms |

### H. Backend architecture

Relevant to FastAPI backend design, authentication, authorization, API structure.

**Restriction:** We use production FastAPI. Do not build a replacement web server.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Implementing a RESTful Web API with Python & Flask | http://blog.luisrei.com/articles/flaskrest.html | REST API design patterns | `KM-FOUND-001`, `KM-AUTH-001` | REST endpoints, request validation, error responses | Reference for API structure and error handling conventions | Python/Flask (educational) | Review article terms |
| A Simple Web Server | http://aosabook.org/en/500L/a-simple-web-server.html | HTTP server fundamentals | `KM-FOUND-001` | HTTP request/response, routing, headers | Internal knowledge only | Python | Review book terms |

### I. Frontend development

Relevant to React Native/Expo mobile app and Next.js owner dashboard.

**Restriction:** We use production React Native, Expo, and Next.js. Do not build replacement frameworks.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Build Your own Simplified AngularJS in 200 Lines | https://blog.mgechev.com/2015/03/09/build-learn-your-own-light-lightweight-angularjs/ | Frontend framework internals | `KM-DS-001` | Component model, data binding, templating | Internal knowledge for understanding reactive UI | JavaScript (educational) | Review article terms |
| Build your own React | https://pomb.us/build-your-own-react/ | React rendering model | `KM-DS-001`, mobile/web shells | Virtual DOM, reconciliation, component lifecycle | Internal knowledge for understanding React Native rendering | JavaScript | Verify repo license |
| WTF is JSX (Let's Build a JSX Renderer) | https://jasonformat.com/wtf-is-jsx/ | JSX/template rendering | `KM-DS-001` | Template rendering, virtual DOM | Internal knowledge only | JavaScript | Review article terms |

### J. Git and version control

Relevant to repository hygiene, commit practices, recovery evidence preservation.

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Write yourself a Git! | https://wyag.thb.lt/ | Git internals, commit objects, branching | All phases (Git workflow) | Git object model, commits, trees, refs | Reference for understanding commit/branch structure during recovery and handover | Python | Verify repo license |
| ugit: Learn Git Internals by Building Git Yourself | https://www.leshenko.net/p/ugit/ | Git internals | All phases | Git internals, packfiles, references | Reference for recovery evidence handling | Python | Review site terms |
| Gitlet | http://gitlet.maryrosecook.com/docs/gitlet.html | Git implementation concepts | All phases | Commit graph, branching, merging | Internal knowledge only | JavaScript | Review site terms |

### K. Testing and deployment

Relevant to CI workflow, test structure, deployment verification.

| Resource | URL | Related Kisan Mirza feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Continuous Integration System | http://aosabook.org/en/500L/a-continuous-integration-system.html | CI pipeline design | Phase 1 CI gates, `.github/workflows/backend-foundation.yml` | CI jobs, test automation, deployment pipelines | Reference for structuring the GitHub Actions workflow | Conceptual | Review book terms |

### L. Neural network foundations

Relevant to understanding AI model behavior (internal knowledge only).

| Resource | URL | Related Kisan Mitra feature | Roadmap task | Engineering concepts | Recommended application | Stack compatibility | License / notes |
|----------|-----|----------------------------|--------------|----------------------|-------------------------|---------------------|-----------------|
| Neural Networks: Zero to Hero | https://www.youtube.com/playlist?list=PLAqhIrjkxbuWI23v9cThsA9GvCAUhRvKZ | Understanding neural network training | `KM-AI-002`, `KM-RAG-003` | Backpropagation, training loops, neural network internals | Internal knowledge for understanding model behavior | Video | Review video terms |
| Build Deep Learning From Scratch | https://github.com/roiamiel1/Build-Deep-Learning-From-Scratch | Deep learning primitives | `KM-AI-002` | Autograd, layers, optimization | Internal knowledge only | Python | Verify repo license |

## Roadmap mapping summary

| Kisan Mitra phase | Primary reference categories | Most useful resources |
|-------------------|------------------------------|----------------------|
| Phase 1 — Foundation and security skeleton | Database, Backend, Git, Testing | Query planner guide, REST API design, Write yourself a Git, CI system |
| Phase 2 — Free value loop and conversion | Backend, Database | REST API design, database internals |
| Phase 3 — Pro plots, stage engine, schedule | Database | B+Tree index concepts, query planner |
| Phase 4 — Partner governance, relationships | Backend, Database | REST API design, RLS concepts (from spec, not external) |
| Phase 5 — Approved knowledge and safe AI | RAG, Vector DB, Document search, OCR, Vision, LLM eval, Neural network | RAG from scratch, Vector DB from scratch, OCR, Facial recognition pipeline, LLM Evaluation Harness |
| Phase 6 — Schedules, chat, medicine, weather, IVR | Backend, Redis, Database | Redis caching, REST API design |
| Phase 7 — Release verification | Testing, Deployment | CI system, test structure references |

## How to use this reference in development workflow

Before implementing each task (per the mandated workflow):

1. Read the approved roadmap (`docs/PHASED_IMPLEMENTATION_ROADMAP.md`).
2. Verify previously completed work (`docs/TASK_COMPLETION_LOG.md`).
3. Inspect relevant existing source code (`backend/app/`, `backend/migrations/`, `mobile/src/`, `web/app/`).
4. Identify the technical problem.
5. Consult relevant official documentation (FastAPI, PostgreSQL, pgvector, React Native, Expo, Next.js, Gemini).
6. Consult useful Build Your Own X resources from this index (only for the relevant category).
7. Prepare a focused implementation plan.
8. Implement the approved task.
9. Test and verify.
10. Update project documentation and AI handover.
11. Commit and safely push when authorized.

## M. FreeLLMAPI — Free LLM Provider Gateway (Reference Only)

**Status:** Evaluated, not approved for production integration.  
**Repository:** https://github.com/tashfeenahmed/freellmapi.git  
**Local path:** `D:\Kisan-Mitra-References\freellmapi`  
**Inspected revision:** `abbdc526d29301b14cedb51944967ff6dc522ea7`  
**License:** MIT (Copyright 2026 Tashfeen Ahmed)

FreeLLMAPI is a self-hosted OpenAI-compatible gateway that stacks the free tiers of ~87 providers behind a single bearer token. It includes provider adapters, rate-limit ledgers, automatic failover, encrypted key storage, and a self-updating model catalog.

**Key findings for Kisan Mitra:**
- **Not suitable for production farmer-facing AI** — documented as "personal experimentation and single-user tool"; no multi-tenant auth; no subscription entitlement; no RAG citations; no dosage validation; no consultant escalation
- **Do not assume advertised aggregate capacity** — "10.1 billion tokens/month" is aggregate across 87 providers; no single user gets that
- **No account/key rotation** to evade provider restrictions
- **No live inference or API account creation** during evaluation
- **Adapter must be disabled by default** if ever implemented (`FREELLAPI_ENABLED=false`)

Full evaluation: `docs/AI_PROVIDER_EVALUATION.md` — includes provider eligibility matrix, proposed adapter architecture (disabled by default), and license/security limitations.

---

## N. Archify — Interactive Architecture Diagram Generator

**Status:** Evaluated and used to generate architecture diagrams.  
**Repository:** https://github.com/tt-a1i/archify.git  
**Local path:** `D:\Kisan-Mitra-References\archify`  
**Inspected revision:** `b42e7d7fd769f47159b5894609b25201b4ce6064`  
**License:** Apache-2.0  
**Version:** 3.3.2  
**Node requirement:** >=18 (environment has Node v24.20.0)

Archify generates validated, interactive standalone HTML diagrams from JSON candidates. Supported types: architecture, workflow, sequence, dataflow, lifecycle, erd, class, tree, timeline, waterfall, explainer. Includes Code Analysis mode for repository health investigation.

**Generated diagrams:** `docs/architecture-diagrams/` — 6 diagrams (current system architecture, farmer auth sequence, database trust boundaries, partner approval lifecycle, admin auth sequence, implemented vs planned components). Index: `docs/architecture-diagrams/README.md`.

**Installation note:** Requires pnpm/npm for full skill installation. npm registry connectivity is blocked in this environment (ENV-NPM-001), so project-level skill installation via `npx skills add` could not be tested. The archify binary (`archify/archify/bin/archify.mjs`) was used directly to generate diagrams. Browser-check gate passes for 4/6 diagrams; 2 diagrams limited by Windows temp directory/Chrome cleanup (environment limitation, not diagram defect).

**Usage:** Edit `*.json` candidate files, run `node <archify-path>/bin/archify.mjs finalize <type> <candidate.json> <output.html> --repo-root <repo-root> --quality showcase --json`. Never edit HTML output directly.

---

## Limitations

- The index repository itself is CC0, but individual linked tutorials carry their own licenses. Verify each before reuse.
- Educational implementations are for concept learning only; never substitute for production-grade dependencies (PostgreSQL, Redis, FastAPI, React Native, Next.js, Gemini).
- Do not upload Kisan Mitra code, credentials, or farmer-facing knowledge base content to external services.
- Do not execute downloaded scripts or install dependencies without review.
- FreeLLMAPI disclaimer: "This project is for personal experimentation and learning, not production."
- Archify diagrams are visualization aids only; diagram validation does not replace security or source-code verification.
