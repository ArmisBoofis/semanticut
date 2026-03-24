stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-semanticut-2026-03-17.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
workflowType: 'architecture'
project_name: 'semanticut'
user_name: 'Armand'
date: '2026-03-18'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- Single-video selection and ingestion for semantic search.
- Async ingestion pipeline: audio extraction → Voxtral transcription → context-aware chunking → embedding with Mistral models → storage in PostgreSQL + pgvector.
- Natural-language search that:
  - Uses **hybrid macro retrieval** (**dense embeddings + BM25 lexical + RRF fusion**) to build top macro context, then sends structured macro→micro JSON context to a **Mistral LLM** that infers **quote vs scene** intent (**scene** = default when the query is vague and does not target specific wording).
  - For **quote-like** queries, returns a **verbatim quote anchor text** from shortlisted context, then resolves the final seek segment via lexical matching over micro candidates.
  - For **scene-like** queries, returns a **sentence anchor** representing the start of the requested scene from context.
  - Emits a normalized API result (`start_ts`, `end_ts`, snippet/context fields) regardless of internal extraction path.
  - For **vague scene** descriptions, jumps to a **coherent** anchor (often scene / block **start** or representative line) within 30 seconds of the similarity peak and aligned to sentence boundaries where possible.
- Web UI (e.g., Next.js) that lets the user select a video, observe ingestion progress, enter queries, and watch the player seek/play to the selected timestamp.
- FastAPI + Pydantic backend exposing ingestion, status, and search endpoints.
- Reviewer can go from repo checkout to first successful search-and-jump within about 10 minutes on a demo video.

**Non-Functional Requirements:**
- Query p95 latency (“search → playback”) ≤ 10 seconds.
- Ingestion time ≤ 0.5 × video duration, with visible progress status.
- Timestamp accuracy: ±5 seconds for quote-like queries.
- Scene coherence for vague queries: sentence-aligned, within 30 seconds of best-matching region, preferring scene starts.
- Architecture and tech constraints: FastAPI + Pydantic, PostgreSQL + SQLAlchemy + Alembic, only Mistral models for transcription/embeddings/Gen-AI, Dockerfile + Docker Compose for local deployment.
- Reliability and reproducibility suitable for a Mistral reviewer.

**Scale & Complexity:**
- Primary domain: backend-heavy web app with semantic search over video transcripts.
- Complexity level: low domain complexity, high technical complexity (async pipelines, vector search, retrieval calibration).
- Estimated architectural components:
  - Ingestion / background processing component.
  - Core FastAPI API service.
  - Data layer (PostgreSQL + pgvector with schema for videos, segments, embeddings, ingestion jobs).
  - Frontend web app for video playback and search experience.

### Technical Constraints & Dependencies

- Required stack: FastAPI + Pydantic, PostgreSQL + SQLAlchemy + Alembic, Docker + Docker Compose.
- AI dependencies: Mistral Voxtral for transcription and Mistral embeddings (and any Gen-AI behavior), with no other AI providers.
- Need for a background-execution mechanism compatible with the deployment model to run ingestion steps asynchronously.
- Database schema must support video metadata, transcript segments with timestamp boundaries, embeddings, and ingestion job status.

### Cross-Cutting Concerns Identified

- Async ingestion and progress tracking across API, DB, and UI layers.
- Performance of vector search and ingestion for demo-scale datasets.
- Chunking and scene-boundary strategy that balances UX coherence with retrieval accuracy; **multi-scale** indexing (macro + micro segments) so coarse semantic search uses enough context while micro timestamps stay precise.
- Basic observability (logs/metrics) for debugging ingestion and search behavior in a demo context.
- Clear modular boundaries so reviewers can easily understand and navigate the codebase.

## Starter Template Evaluation

### Primary Technology Domain

Full-stack web application (Next.js frontend + FastAPI backend) based on the project requirements analysis.

### Starter Options Considered

We evaluated modern starters that combine:

- Next.js + TypeScript for the web UI.
- FastAPI + PostgreSQL for the backend.
- Docker Compose for local development.
- A structure that can support a monorepo layout.

We selected a FastAPI + Next.js + PostgreSQL + Docker Compose starter as the base, then plan to apply:
- TailwindCSS for styling on the Next.js app.
- Prettier and linting configuration for consistent formatting.
- A monorepo layout (frontend + backend in a single repository) to keep boundaries explicit.

### Selected Starter: FastAPI + Next.js + PostgreSQL + Docker Compose template

**Rationale for Selection:**

- Matches the required stack: FastAPI backend, PostgreSQL database, and a Next.js frontend.
- Provides a production-inspired structure with clear separation between API and UI.
- Uses Docker Compose to run API, DB, and UI locally, aligning with the “reviewer-ready” Docker requirement.
- Reduces boilerplate by preconfiguring environment management, dependency wiring, and base project structure.

**Initialization Command:**

```bash
# Example approach:
# 1) Scaffold monorepo or repo root with FastAPI + Postgres + Docker Compose
# 2) Scaffold Next.js + TypeScript + Tailwind app in /frontend

# (Exact command to be finalized when we implement the starter)
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Backend in Python with FastAPI and async support.
- Frontend in TypeScript with React/Next.js.

**Styling Solution:**
- TailwindCSS for the Next.js frontend (configured or added during initialization).

**Build Tooling:**
- Next.js build system for the frontend.
- Standard Python packaging and dependency management for the backend.
- Docker and Docker Compose for multi-service orchestration.

**Testing Framework:**
- Ready to integrate Pytest for backend and Jest/React Testing Library (or similar) for frontend tests.

**Code Organization:**
- Separate application folders for frontend and backend within one repository.
- Clear API boundary between web client and FastAPI services.
- Database models and migrations co-located with the backend service.

**Development Experience:**
- Hot reloading for both frontend and backend.
- Single Docker Compose command to start API, DB, and UI locally.
- Prettier and linting configuration applied to the TypeScript frontend (and optionally Python formatting tools for the backend).

**Note:** Project initialization using this starter and commands should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Single-user, local-only deployment with no authentication; API bound to localhost inside Docker Compose.
- PostgreSQL + pgvector as the only data store, with schema for videos, ingestion jobs, transcript segments, and embeddings.
- RESTful JSON API between Next.js frontend and FastAPI backend, with polling-based ingestion status.

**Important Decisions (Shape Architecture):**
- Ingestion modeled as explicit jobs with status and progress, exposed via `/videos/{id}/status`.
- Transcript segments store both text and time boundaries; embeddings stored alongside or keyed by segments.
- Frontend built with Next.js + TypeScript + Tailwind, using simple data-fetching hooks and local state (no global store).
- Docker Compose used as the only orchestration mechanism for local reviewer runs.

**Deferred Decisions (Post-MVP):**
- Any authentication/authorization model (e.g., multi-user, roles).
- Additional caching layers beyond PostgreSQL (e.g., Redis or in-process caches).
- Real-time channels (WebSockets/SSE) for ingestion updates or collaborative features.

### Data Architecture

- Database: PostgreSQL with pgvector, managed via SQLAlchemy + Alembic migrations.
- Core tables and concerns:
  - `videos`: video metadata (id, label, duration, storage path, created_at).
  - `ingestion_jobs`: per-video ingestion jobs with status, phase, progress percentage, timestamps, and error fields.
  - `transcript_segments`: per-video **micro** segments with `start_ts`, `end_ts`, raw text, and chunking metadata (precise seek targets; typically aligned to ASR segment boundaries).
  - `transcript_macro_segments` (or equivalent): **macro** units grouping consecutive micro segments for **context-rich** embeddings used in **phase-1** macro retrieval; linked to child micro rows. **Macro size** is driven by a **configurable target in word-like units** (primary: **word count**; optional **token** counts if mapped to a tokenizer with **units close to words** — document the chosen unit in `Settings` / `.env.example`).
  - `embeddings`: vector representations associated with segments (either in a dedicated table or as a `vector` column on `transcript_segments` and macro tables); **cosine distance** on normalized Mistral vectors remains the default retrieval metric unless evaluation proves otherwise.
- No additional caching layer for search; all retrieval goes directly through pgvector queries over the embeddings.

### Authentication & Security

- No authentication for MVP: single-user, local-only POC intended for a reviewer running Docker Compose.
- Security posture is “local trusted environment”; no session or token handling.
- API services are exposed only on localhost via Docker Compose configuration.

### API & Communication Patterns

- Style: JSON REST over HTTP.
- Initial key endpoints:
  - `POST /videos`: register and start ingestion for a video (uploaded file or referenced local path).
  - `GET /videos`: list videos and their ingestion status.
  - `GET /videos/{id}/status`: detailed ingestion job status and progress.
  - `POST /videos/{id}/search`: accept a query string and return the best-matching segment for playback (`start_ts`, `end_ts`, fine-match `text`) plus **`macro_context_text`** (full coarse unit covering the result) and **character offsets** into that string for the fine span — so the client can render **macro block + highlighted micro** without guessing concatenation. **Server-side retrieval** implements: **(1)** dense macro retrieval on embeddings + BM25 lexical retrieval on macro text; **(2)** rank fusion via **RRF** (default `k=60`) and top-K context packaging (default 10 macros); **(3)** **Mistral chat** completion over structured macro→micro JSON context with instructions for **quote vs scene** behavior; **(4)** intent-aware extraction with a unified contract: both quote and scene paths return sentence anchors (quote match sentence vs scene-start sentence) that are resolved lexically to micro segments; **(5)** deterministic fallback and normalized response assembly including **tiered** `match_quality` / similar (no misleading raw % as primary trust).
- Frontend polls `GET /videos/{id}/status` on an interval while ingestion is running; no WebSockets/SSE.

### Frontend Architecture

- Framework: Next.js (App Router) with TypeScript and TailwindCSS.
- State management:
  - Local component state plus simple data-fetching hooks (e.g., `fetch`/SWR/React Query) rather than a global store.
  - One primary page that combines video selection, ingestion status, search, and playback.
- Routing is minimal (single main route, with optional video-id parameters later if needed).

### Localization & UI language

- **Product UI language:** French only for all user-visible strings in the browser (aligned with BMM `config.yaml` `product_ui_language` / `product_ui_locale` and with `ux-design-specification.md`).
- **Locale:** Use `fr-FR` for locale-aware formatting (dates, numbers, durations) where the UI displays them.
- **Implementation:** Use a centralized string strategy (for example `next-intl` with locale-scoped message files, or an equivalent Next.js i18n pattern) so copy is consistent, reviewable, and not hard-coded as mixed-language literals in components.
- **Authoritative UX:** Flows, components, primary vs admin surfaces, and visual/UX details live in `_bmad-output/planning-artifacts/ux-design-specification.md`, with supplementary references in `ux-design-directions.html` and `ux-color-themes.html`.

### Infrastructure & Deployment

- Deployment for POC is strictly local via Docker Compose, with three main services:
  - `api`: FastAPI backend.
  - `db`: PostgreSQL (with pgvector extension).
  - `web`: Next.js frontend.
- Environment configuration through `.env` / `.env.local` files (DB connection string, Mistral API key, ports).
- Basic structured logging for API requests, ingestion pipeline phases, and search queries; no full monitoring stack.

### Search & macro configuration (environment)

Tune without code changes (`backend/app/config.py` and `.env.example`):

- **Macro target size:** `TRANSCRIPT_MACRO_TARGET_MODE` (`words` default, `chars` optional), `TRANSCRIPT_MACRO_TARGET_WORDS`, `TRANSCRIPT_MACRO_TARGET_CHARS`.
- **Hybrid retrieval:** `SEARCH_MACRO_TOP_K` (context candidates sent to LLM), `SEARCH_RRF_K` (RRF constant; default 60), optional dense/BM25 weighting/tuning knobs as implemented.
- **Lexical retrieval:** BM25 index/search settings for `macro_text_content` (documented with backend search service configuration).
- **Mistral extractor:** `MISTRAL_ANCHOR_MODEL`, `MISTRAL_ANCHOR_MAX_TOKENS` (or equivalent extractor vars) for intent-aware chat completion with a unified sentence-anchor contract (quote-matching sentence for quote-like queries, scene-start sentence for scene-like queries).

### Decision Impact Analysis

**Implementation Sequence:**
- Initialize repo/monorepo with FastAPI + Postgres + Docker Compose and Next.js + TypeScript + Tailwind.
- Define database schema (videos, ingestion_jobs, transcript_segments, embeddings) and Alembic migrations.
- Implement ingestion pipeline and status endpoints (`/videos`, `/videos/{id}/status`).
- Implement search endpoint (`/videos/{id}/search`) over pgvector embeddings.
- Build frontend page that wires video selection, ingestion progress polling, search form, and video player seeking.

**Cross-Component Dependencies:**
- Ingestion and search depend on the agreed schema and pgvector configuration.
- Frontend behavior (polling, search UX, video seeking) depends on the API contracts and timestamp semantics.
- Docker Compose wiring must align services, ports, and env variables so the entire stack runs with a single command for reviewers.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
- Naming consistency across database tables/columns, API fields, and JSON responses.
- API endpoint shapes and success/error response formats.
- Frontend/backend file and symbol naming that future agents might otherwise diverge on.

### Naming Patterns

**Database Naming Conventions:**
- Tables use **lowercase plural with underscores**:
  - `videos`, `ingestion_jobs`, `transcript_segments`, `transcript_macro_segments` (or equivalent), `embeddings`.
- Columns use **snake_case**:
  - `video_id`, `start_ts`, `end_ts`, `ingestion_status`, `created_at`.
- Foreign keys use `<referenced_table>_id`:
  - `video_id` on `transcript_segments`, `ingestion_jobs`, and `embeddings`.

**API Naming Conventions:**
- REST endpoints are **plural nouns** with path parameters in `{snake_case}`:
  - `POST /videos`, `GET /videos`, `GET /videos/{video_id}/status`, `POST /videos/{video_id}/search`.
- Query parameters and JSON fields use **snake_case**:
  - `video_id`, `query_text`, `limit`, etc.

**Code Naming Conventions:**
- Backend (Python/FastAPI):
  - Functions and variables: `snake_case` (e.g., `create_video`, `run_ingestion_job`).
  - Classes: `PascalCase` (e.g., `Video`, `IngestionJob`, `TranscriptSegment`).
  - Modules/files: `snake_case.py` (e.g., `models.py`, `ingestion_service.py`).
- Frontend (Next.js + TypeScript):
  - React components: `PascalCase` files and exports (e.g., `VideoPlayer.tsx`, `SearchForm.tsx`).
  - Hooks: `useSomething` naming with files like `useVideoSearch.ts`.
  - Utilities: `camelCase` exported helpers in files like `videoSearch.ts`, `timeFormatting.ts`.

### Structure Patterns

**Project Organization:**
- Backend tests co-located or in a dedicated `tests/` tree, following the same module structure.
- Frontend components organized by feature (e.g., search, player) rather than by type-only folders, to keep related UI pieces together.
- Shared utilities grouped into clearly named modules (e.g., `ingestion`, `search`, `mistral_client`) rather than ad-hoc helper files.

**File Structure Patterns:**
- Configuration files (`settings`, `.env` loading, Docker config) live alongside the backend service, not scattered.
- Static frontend assets (e.g., icons, logos) live under a consistent `public/` or `assets/` path.
- Environment variables are documented once and used consistently across services.

### Format Patterns

**API Response Formats:**
- **Success responses** return a direct payload, without a wrapper:
  - Example search response (multi-scale; fine `text` is the micro span; `macro_context_text` is the full coarse unit for UI context):
    - `{ "start_ts": 123.45, "end_ts": 125.2, "text": "…fine micro snippet…", "macro_context_text": "…full macro transcript…", "match_start_offset": 42, "match_end_offset": 68, "confidence": 0.92 }`
  - Offsets are computed server-side on the exact `macro_context_text` string shipped in JSON (avoid ambiguous client substring search when micro text repeats). Optional fields may be omitted in legacy/single-scale fallbacks if documented.
- **Error responses** are wrapped with an `error` object:
  - `{ "error": { "code": "INGESTION_NOT_READY", "message": "Ingestion is still running for this video." } }`

**Data Exchange Formats:**
- JSON field naming uses **snake_case** consistently across backend and frontend.
- Times and timestamps are represented as:
  - Seconds from start of video for offsets (`start_ts`, `end_ts`), or
  - ISO 8601 strings for wall-clock times if needed in logs or metadata.
- Booleans use JSON `true`/`false`, no numeric stand-ins.

### Communication Patterns

**State Management Patterns (Frontend):**
- Local component state plus simple data-fetching hooks handle all UI state; no global state library is introduced for MVP.
- Loading and error states are explicit:
  - `isLoading`, `error` flags on hooks for ingestion status and search, surfaced directly into UI.

### Process Patterns

**Error Handling Patterns:**
- Backend:
  - Use structured exceptions mapped to HTTP status codes and the standard error shape (`{ "error": { code, message } }`).
  - Log internal details server-side; return concise, user-facing messages to the client.
- Frontend:
  - Display clear, short user-facing messages in **French** (per Localization & UI language), not raw error codes; tone and copy live in the UX spec / message catalogs.

**Loading State Patterns:**
- Use descriptive loading flags (`isIngesting`, `isSearching`) instead of generic `loading`.
- While ingestion is running, the UI:
  - Shows a progress indicator.
  - Polls `GET /videos/{video_id}/status` at a fixed interval.

### Enforcement Guidelines

**All AI Agents MUST:**
- Use snake_case for database columns and JSON fields, and lowercase plural names for tables and REST resources.
- Follow the established endpoint shapes and response formats, especially the direct payload success and wrapped error responses.
- Adhere to the agreed component, hook, and utility naming/file patterns on the frontend.

**Pattern Enforcement:**
- When adding or modifying endpoints, schemas, or components, check against this `architecture.md` section before introducing new naming or structural patterns.
- If a pattern change is necessary, update this document explicitly so future agents and contributors have a single source of truth.
