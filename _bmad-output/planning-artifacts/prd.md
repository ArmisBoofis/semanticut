---
workflowType: prd
projectName: semanticut
userName: Armand
date: 2026-03-18
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-semanticut-2026-03-17.md
  - /Users/armand_malinvaud/Downloads/Mistral Home Assignment_ Small App Development-2.pdf
documentCounts:
  briefCount: 1
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 1
classification:
  projectType: web_app
  domain: general
  complexity: low_domain_high_technical
  projectContext: greenfield
---

# Product Requirements Document - semanticut

**Author:** Armand
**Date:** 2026-03-18

## Executive Summary

Semanticut is a proof-of-concept web application that lets a user jump directly to the right moment in a video by typing a natural-language description of what they remember. It is designed primarily for a Mistral reviewer and optimized to demonstrate an end-to-end, backend-heavy pipeline built with the official Mistral SDK and models: Voxtral transcription, semantic chunking, Mistral embeddings, and fast vector retrieval in PostgreSQL (`pgvector`), served through a FastAPI + Pydantic backend and a browser UI.

The product promise is: **“Come with a vague memory. Get a precise timestamp.”** For **quote-like queries**, the app should seek quickly and precisely to the correct timestamp. For **vague scene descriptions**, it should return a result that starts at the beginning of the relevant scene (avoiding “cutting a scene in half”), creating a better viewing experience and demonstrating UX-aware retrieval. **Retrieval** combines **macro/micro embeddings** with a **Mistral LLM** step that reads **shortlisted macro text**, infers **quote vs scene** intent (**scene** is the default when the query does not target a specific sentence word-for-word), returns a **verbatim anchor** from that text, and **refines** the jump with a **second embedding** over **micro** segments scoped to the selected macros.

### What Makes This Special

This POC is intentionally engineered to look and feel production-grade in the ways that matter for the demo: seamless integration of multiple Mistral technologies with optimizations that show understanding of the underlying tools, not just API wiring. The core differentiators are:
- Timestamp accuracy: precise seeking behavior for quoted/precise queries.
- Retrieval quality: strong semantic matching for fuzzy, conversational recollections.
- Architecture cleanliness: a clear, maintainable system with explicit boundaries (ingestion/transcription/chunking/indexing/query) and async execution for backend-heavy work.

The “why now” is that speech-to-text quality and the surrounding AI stack have matured to the point where processing large audio and searching large embedding indexes is no longer prohibitively costly or difficult—making this experience practical to ship.

## Project Classification

- Project Type: Web app (browser UI + API; separate backend and frontend)
- Domain: General (video search / productivity)
- Complexity: Low domain complexity; high technical complexity (transcription + embeddings + vector search; async backend-heavy processing)
- Project Context: Greenfield
- Hard constraints (scope): PostgreSQL + SQLAlchemy + Alembic; FastAPI + Pydantic; only Mistral models for transcription/GenAI/embeddings; Dockerfile + Docker Compose; async for transcription/indexing/vector search workloads.

## Success Criteria

### User Success

- Fast “search → jump” loop: from submitting a query to the video seeking and playing the result should be ≤ 10 seconds end-to-end.
- Quote precision: for quote-like queries (user remembers exact phrasing), the selected timestamp should be within ± 5 seconds of the correct moment.
- Vague memory behavior: for vague scene descriptions, results should:
  - Not cut sentences (seek points align to sentence or chunk boundaries that preserve sentence integrity).
  - Prefer returning the start of a coherent scene rather than mid-scene.
  - Stay close to the semantic match: the returned start timestamp should be within 30 seconds of the core similarity peak (best-matching region).

### Business Success

- Reviewer-ready reproducibility: a Mistral reviewer can run the app reliably on first try.
- Time-to-first-success: starting from repo checkout, the reviewer can get to “app running + short video ingested + first successful search/jump” in ≤ 10 minutes (assuming the uploaded video is short enough).

### Technical Success

- Async ingestion with progress: video ingestion (audio extraction → transcription → chunking → embedding → indexing) runs asynchronously and exposes a progress state the UI can display.
- Ingestion efficiency target: total ingestion time should be ≤ 50% of video duration for typical demo videos.
- Operational simplicity: runs via Dockerfile + Docker Compose, with required services (API, DB, UI) wired correctly.
- Constraint compliance: uses PostgreSQL + SQLAlchemy + Alembic, FastAPI + Pydantic, and only Mistral models for transcription / embeddings / gen-AI behavior.

### Measurable Outcomes

- Query latency: p95 “submit query → playback starts” ≤ 10 seconds (measured on a representative machine).
- Quote accuracy: on a small curated set of quote queries, timestamp error ≤ 5 seconds.
- Vague query coherence: on curated vague queries, returned timestamps:
  - Align to sentence boundaries, and
  - Are within 30 seconds of the best-matching region while tending to scene starts.
- Demo dataset fit: user selects a video to search within; typical demo videos are 20–30 minutes long.
- Ingestion SLA: ingestion completes in ≤ 0.5 × video duration, with visible progress states.

## Product Scope

### MVP - Minimum Viable Product

- Video selection: user selects a specific video to search within.
- Ingestion pipeline (async): upload video → async processing with progress → searchable index ready.
- Admin registration: an admin can register a video for ingestion **via the web UI** (admin page), not only via the API, so a reviewer can complete setup without HTTP tools.
- Search + jump: natural-language search over transcript using **multi-scale** indexing (**macro** + **micro** structure) with this **pipeline**: (1) run **hybrid retrieval** on macro text (**dense embeddings + BM25 lexical**) and fuse ranks with **RRF**; (2) keep the top macro candidates (default top 10) as **structured macro→micro context**; (3) send that context to a **Mistral LLM** that applies **quote vs scene** guidance (**scene** = default for vague queries; **quote** for exact wording) and returns a single best **micro start timestamp** (`start` float); (4) map that output to API seek fields (`start_ts`, `end_ts`, snippet) plus **macro context + highlighted micro span** for trust. **No secondary anchor re-vectorization loop** is required in the final decision path. Jump behavior should still target:
  - ≤ 10 seconds end-to-end (or documented trade-offs if the LLM step approaches the budget), and
  - Quote precision within ± 5 seconds where the query is quote-like.
- **Tunables (environment):** **macro** grouping target in **word**-like units (primary: **words**, or tokenizer units **close to words** — documented in architecture), hybrid retrieval configuration (**RRF** constant and macro context top-K), and any BM25/index tuning values used by the search layer.
- Search result presentation: after a match, the UI shows **macro-level transcript context** with the **fine / micro** span **visually highlighted** inside it — trust comes from **context + precise span**, not from a misleading similarity percentage alone (tiered or relative feedback per UX spec).
- Vague query “scene” handling: **scene-style** recall is the **default** when the query is not word-specific; the LLM should prefer **coherent** anchors (e.g. **start** of the relevant block or a **representative** line), subject to the **30 seconds** / boundary rules in success criteria.
- Deployment: one-command Docker Compose setup; migrations via Alembic; stable DB schema.

### Growth Features (Post-MVP)

- Better evaluation harness (more query sets, automatic scoring).
- Multiple result candidates / confidence indicators.
- Smarter scene boundary detection heuristics.
- Caching and performance optimizations for repeated queries.
- Improved UX polish (history, bookmarks, shareable timestamps).

### Vision (Future)

- Multi-video / library-wide search.
- Richer multimodal grounding (beyond speech-only).
- Integrations (e.g., meetings, lecture archives) and collaborative workflows.
- More advanced retrieval strategies and reranking.
