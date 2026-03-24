---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# semanticut - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for semanticut, decomposing the requirements from the PRD and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can select a specific video to search within.
FR2: The system ingests a video asynchronously (audio extraction → Voxtral transcription → semantic chunking → embeddings with Mistral models → indexing in PostgreSQL + pgvector) and exposes ingestion progress.
FR3: User can submit natural-language queries over the transcript, and the system seeks the video to the best-matching timestamp that satisfies the latency and accuracy constraints (implementation: **hybrid macro retrieval** with **dense + BM25 + RRF**, then **Mistral direct timestamp extraction** from structured macro→micro context — see Story **3.3**).
FR4: For vague, scene-style queries, the system returns a start timestamp that:
- Avoids cutting sentences (aligns to sentence/chunk boundaries), and
- Starts a coherent scene within 30 seconds of the similarity peak.
FR5: The app is runnable via a one-command Docker Compose setup, wiring FastAPI + Pydantic backend, PostgreSQL + SQLAlchemy + Alembic (with pgvector), and the web UI, with a stable DB schema.
FR6: The primary page only lists fully ingested videos that are available for search; partially ingested videos never appear there.
FR7: An admin page lists all videos (including those currently ingesting) with their ingestion status and allows the admin to remove videos.

### NonFunctional Requirements

NFR1: p95 “submit query → playback starts” latency ≤ 10 seconds on a representative machine.
NFR2: Video ingestion completes in ≤ 0.5 × video duration, with visible progress states.
NFR3: For quote-like queries, timestamp error is within ± 5 seconds of the true moment.
NFR4: For vague queries, returned timestamps:
- Are sentence-aligned, and
- Are within 30 seconds of the best-matching region, tending toward scene starts.
NFR5: Stack constraints: PostgreSQL + SQLAlchemy + Alembic; FastAPI + Pydantic; only Mistral models for transcription/embeddings/gen-AI; Dockerfile + Docker Compose; async for ingestion, indexing, and vector search workloads.
NFR6: Time-to-first-success: reviewer can go from repo checkout to “app running + short video ingested + first successful search/jump” in ≤ 10 minutes.
NFR7: Reliability and reproducibility sufficient for a Mistral reviewer running locally.

### Additional Requirements

- Use a FastAPI + Next.js + PostgreSQL + Docker Compose starter as the base, with monorepo-style layout (frontend + backend).
- Frontend stack: Next.js (App Router) + TypeScript + TailwindCSS, with hot reload and basic linting/formatting.
- Backend: FastAPI with async support, structured into clear modules for ingestion, search, and data access.
- Database schema includes at minimum:
  - `videos` table for video metadata (id, label, duration, storage path, timestamps).
  - `ingestion_jobs` table for job status, phases, progress %, timestamps, and errors.
  - `transcript_segments` table for text segments with `start_ts`, `end_ts`, and chunk metadata.
  - `embeddings` (table or vector column) holding vectors associated with segments.
- No extra caching layer beyond PostgreSQL/pgvector for MVP; all retrieval via pgvector queries.
- Ingestion modeled as explicit jobs with a `/videos/{video_id}/status` endpoint and polling-based progress reporting.
- Core API endpoints:
  - `POST /videos` – register and start ingestion for a video.
  - `GET /videos` – list videos and their ingestion status.
  - `GET /videos/{video_id}/status` – detailed ingestion status and progress.
  - `POST /videos/{video_id}/search` – accept a query string and return the best-matching segment for seek (`start_ts`, `end_ts`, fine-match text) plus **macro context** and highlight bounds when multi-scale indexing is active (see Story 3.3: **hybrid macro retrieval** + **Mistral direct timestamp extraction** from structured context); optional **tiered** match feedback instead of misleading raw percentages.
- Frontend has:
  - A primary page combining video selection from fully ingested videos, search form, and video player that seeks to returned timestamps.
  - An admin page listing all videos (including ingesting ones), their ingestion status, and controls to remove videos.
- Local-only, single-user deployment; no auth for MVP; services exposed via Docker Compose on localhost.
- Logging for API requests, ingestion phases, and search queries; no full monitoring stack.
- Naming and formatting rules:
  - DB tables: lowercase plural with underscores; columns in snake_case.
  - REST endpoints: plural nouns; path params and JSON fields in snake_case.
  - Backend: snake_case functions, PascalCase classes; frontend: PascalCase components, `useX` hooks, clear feature-based organization.
  - Success responses are direct payloads; errors are wrapped as `{ "error": { code, message } }`.
  - Time fields use seconds-from-start for `start_ts`/`end_ts`, ISO-8601 only when needed for wall-clock times.

### UX Design Requirements

**Authoritative UX document:** `_bmad-output/planning-artifacts/ux-design-specification.md` (supplementary: `ux-design-directions.html`, `ux-color-themes.html`). Implementation and QA should treat it as the source for flows, components, and reviewer-demo polish unless this epic doc explicitly narrows scope.

**MVP obligations called out there (and reflected in architecture):**
- **French-only product UI** in the browser, locale `fr-FR`, with centralized strings (see architecture “Localization & UI language”).
- **Primary vs admin:** user-facing search page lists only search-ready videos; admin page lists all videos (including ingesting), status/progress, and removal — matches FR6/FR7 as concrete UX rules on top of PRD MVP.
- **Interaction quality:** search → jump loop with visible feedback; ingestion honesty/progress; scene coherence (sentence boundaries, vague-query behavior) as specified in the PRD and expanded in the UX spec.

### FR Coverage Map

FR1: Epic 3 - Searchable Video Experience (Primary Page)  
FR2: Epic 2 - Video Registration & Ingestion Management (Admin)  
FR3: Epic 3 - Searchable Video Experience (Primary Page)  
FR4: Epic 3 - Searchable Video Experience (Primary Page)  
FR5: Epic 1 - Reviewer-Ready Environment & Stack Setup  
FR6: Epic 3 - Searchable Video Experience (Primary Page)  
FR7: Epic 2 - Video Registration & Ingestion Management (Admin)  

_Note: FR6 and FR7 are not separate PRD numbered requirements; they decompose PRD MVP “video selection” and async ingestion into explicit primary-page and admin behaviors._

## Epic List

### Epic 1: Reviewer-Ready Environment & Stack Setup

Enable a Mistral reviewer to clone the repo, run a single Docker Compose command, and access a working web UI backed by a FastAPI API and PostgreSQL (with pgvector) that are wired together correctly.

**FRs covered:** FR5

### Story 1.1: Set up initial project from starter template (Docker + pgvector)

As a reviewer,
I want to set up the initial project from the starter template and ensure Docker brings up PostgreSQL with pgvector and a simple health check,
So that the rest of the implementation can rely on a consistent, reproducible database environment.

**Acceptance Criteria:**

**Given** I have a fresh clone of the repo and the documented prerequisites
**When** I run `docker compose up` from the repo root (following the project’s Docker instructions)
**Then** Docker builds/starts successfully and there is a `db` service running PostgreSQL, reachable from inside the Docker network.

**Given** the `db` container is running  
**When** I connect from inside the `db` container or the `api` container (e.g. via `psql` or SQLAlchemy)  
**Then** the `pgvector` extension is installed and usable (e.g. `CREATE EXTENSION IF NOT EXISTS vector` succeeds).

**Given** the repo has a README or short setup note  
**When** I read the “Environment” / “Docker” section  
**Then** I see how to start the stack and know that `db` is expected to be running with pgvector.

### Story 1.2: Dockerized FastAPI backend wired to PostgreSQL

As a reviewer,
I want a Dockerized FastAPI service connected to the PostgreSQL database,
So that the API can successfully start up and talk to the database in a reproducible way.

**Acceptance Criteria:**

**Given** I run `docker compose up`  
**When** the services are healthy  
**Then** an `api` service is running FastAPI, exposed on a documented port (e.g. 8000 from host).

**Given** the `api` service has started  
**When** it initializes its DB connection using environment variables from Docker Compose  
**Then** it can successfully connect to the `db` service and perform at least a trivial query (e.g. `SELECT 1`), failing fast with a clear log message if DB is unreachable.

**Given** the stack is up  
**When** I hit a simple health endpoint (e.g. `GET /health` or `GET /`) from my browser or `curl`  
**Then** I receive a 200 response indicating the API is alive and connected to the database.

### Story 1.3: Dockerized Next.js frontend wired into the stack

As a reviewer,
I want a Dockerized Next.js frontend that can be opened in the browser and reach the FastAPI backend,
So that I can verify the full stack wiring from a browser even before real features are implemented.

**Acceptance Criteria:**

**Given** I run `docker compose up`  
**When** the stack is healthy  
**Then** a `web` service is running Next.js, exposed on a documented port (e.g. 3000 from host), and I can load a basic page in the browser.

**Given** the `web` and `api` services are running  
**When** I open the main page  
**Then** the frontend successfully calls a basic backend endpoint (e.g. health check) and renders a simple status (e.g. “Backend: OK”) without CORS or network errors.

**Given** I am a new reviewer  
**When** I read the README “Getting Started / Running with Docker” section  
**Then** I see a single-copy-paste command (or very small set of commands) that takes me from clone → running stack → URL to visit, with notes about expected ports.

### Epic 2: Video Registration & Ingestion Management (Admin)
Enable an admin to register and remove videos (including **registering videos from the admin UI** via an upload form, in addition to API registration), trigger ingestion, and monitor ingestion status and progress for all videos from an admin page.
**FRs covered:** FR2, FR7

## Epic 2: Video Registration & Ingestion Management (Admin)

Enable an admin to register and remove videos (including **registering videos from the admin UI** via an upload form, in addition to API registration), trigger ingestion, and monitor ingestion status and progress for all videos from an admin page.

### Story 2.1: Admin can register videos for ingestion

As an admin,
I want to register a new video for ingestion,
So that the system can start preparing it for semantic search.

**Acceptance Criteria:**

**Given** the stack is running  
**When** I call an API endpoint such as `POST /videos` with minimal required metadata (for example, label and video file/path)  
**Then** a new video record is created and an ingestion job is created in a “pending” or “queued” state.

**Given** a video has been registered  
**When** I fetch the list of videos (for example, via `GET /videos`)  
**Then** the new video appears with an initial ingestion status (for example, `pending`).

**Given** error conditions such as invalid payload or unsupported media  
**When** I call `POST /videos`  
**Then** I get a structured error response using the standard `{ "error": { code, message } }` format.

### Story 2.2: Admin page listing all videos with ingestion status

As an admin,
I want an admin page that lists all videos and their ingestion status,
So that I can see what is being processed and what is ready for search.

**Acceptance Criteria:**

**Given** there are multiple videos in the system with different ingestion states (such as pending, running, completed, failed)  
**When** I open the admin page in the frontend  
**Then** I see a table or list of all videos (including ones still ingesting) with:
- Video label or identifier,  
- Current ingestion status,  
- A basic progress indicator such as percentage or phase name.

**Given** some videos are still ingesting  
**When** I stay on the admin page  
**Then** the ingestion status updates periodically via polling (for example, `GET /videos` or `GET /videos/{video_id}/status`) without requiring a full page reload.

**Given** incomplete ingestion jobs exist  
**When** I view them on the admin page  
**Then** each partially ingested video appears in the admin list with its current ingestion status and progress indicator.

### Story 2.3: Admin can remove videos and associated ingestion data

As an admin,
I want to remove a video and its associated ingestion data,
So that I can keep the system clean and avoid cluttering the demo environment.

**Acceptance Criteria:**

**Given** there is at least one video in the system  
**When** I use the admin UI to trigger a “remove” action on that video  
**Then** the frontend calls a dedicated API endpoint, such as `DELETE /videos/{video_id}`.

**Given** the delete request succeeds  
**When** I refresh the admin page or wait for the next poll  
**Then** the removed video no longer appears in the admin list, and its ingestion job and associated transcript or embedding records are no longer present or referenced.

**Given** the video was still ingesting when I requested deletion  
**When** the deletion completes  
**Then** any running ingestion for that video is cancelled or safely cleaned up, and the system responds with a clear success or error message to the admin.

### Story 2.4: Asynchronous ingestion pipeline for registered videos

As an admin,
I want a background ingestion pipeline that processes registered videos through audio extraction, transcription, chunking, embeddings, and indexing,
So that videos become searchable without blocking the UI and with clear status reporting.

**Acceptance Criteria:**

**Given** a video has been registered via `POST /videos`  
**When** the ingestion job starts  
**Then** it runs asynchronously (for example, in a background task or worker) and transitions through well-defined states such as `pending`, `running`, `completed`, and `failed`.

**Given** an ingestion job is running  
**When** I poll its status via an endpoint such as `GET /videos/{video_id}/status` or `GET /videos`  
**Then** I can see at least the current phase (for example, `transcribing`, `chunking`, `embedding`, `indexing`) and an overall progress indicator (such as percentage or phase-based step count).

**Given** ingestion completes successfully for a video  
**When** I fetch its status via `GET /videos/{video_id}/status` (or `GET /videos`)  
**Then** the video’s ingestion status becomes `completed` (search-ready)  
**And** transcript segments and embeddings created by the pipeline exist for that video so that subsequent search can operate on them.

**Given** ingestion fails at any step  
**When** I view the video in the admin list or status endpoint  
**Then** the ingestion status is `failed`, with a reason or error message logged server-side and a concise error state visible to the admin (for example, “Ingestion failed – see logs”).

### Story 2.5: Admin can register videos via upload form on the admin page

As an admin,
I want to register a new video for ingestion using an upload form on the admin page,
So that I can run the demo without calling the HTTP API manually.

**Acceptance Criteria:**

**Given** the stack is running and I am on the admin page  
**When** I choose a video file and provide required fields (for example, label) as required by the API and submit the form  
**Then** the client uses the same registration contract as Story 2.1 (for example `POST /videos` with the agreed payload — multipart or JSON per architecture)  
**And** I see loading feedback and success or structured error feedback in the UI.

**Given** I submit invalid or unsupported input  
**When** the API returns an error  
**Then** the admin UI shows a clear message using the standard `{ "error": { code, message } }` pattern surfaced in French for the user, without raw stack traces.

**Given** a video is registered successfully  
**When** I view the admin list of videos  
**Then** the new video appears with the same ingestion status behavior as for API-registered videos.

## Epic 3: Searchable Video Experience (Primary Page)
Enable a user to choose from fully ingested videos on the primary page, run natural-language searches, and jump the video player to precise or scene-coherent timestamps that satisfy the latency and accuracy constraints.
**FRs covered:** FR1, FR3, FR4, FR6

### Story 3.1: Primary page lists only fully ingested videos

As a user,
I want the primary page to list only videos that are fully ingested and ready for search,
So that I can immediately run searches without encountering half-processed items.

**Acceptance Criteria:**

**Given** there are videos with different ingestion states (pending, running, completed, failed)
**When** I open the primary page
**Then** I only see videos in the “completed” (search-ready) state.

**Given** a video transitions from running to completed
**When** the primary page refreshes or the status polling updates
**Then** the video becomes visible in the primary list without requiring a full page reload.

**Given** there are no fully ingested videos yet
**When** I open the primary page
**Then** I see a clear empty state (for example, “No searchable videos yet — ask an admin to ingest one”) instead of a blank or broken UI.

### Story 3.2: Natural-language search returns best-matching segment

As a user,
I want to enter a natural-language query and receive the best-matching transcript segment for the selected video,
So that I can quickly jump to the part I remember.

**Acceptance Criteria:**

**Given** I have selected a fully ingested video on the primary page
**When** I submit a query via the search input
**Then** the frontend calls `POST /videos/{video_id}/search` with the query text.

**Given** the backend finds a match
**When** the API responds
**Then** the response includes at least `start_ts`, `end_ts`, `text` snippet, and `confidence`
**And** the UI displays the snippet and uses `start_ts`/`end_ts` to control the player.

**Given** the backend cannot find a reasonable match or search fails
**When** the API responds
**Then** the error is surfaced either as a structured error object (`{ "error": { code, message } }`) shown to the user
**Or** as an explicit “no good match” UI state
**And** the UI never silently fails.

**Given** a typical demo-sized video and query workload
**When** I submit a search
**Then** the time from “submit query” to “player seek starts” is consistent with the p95 target (≤ 10 seconds, informally verified during testing).

### Story 3.3: Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction

As a user,
I want semantic search to match my query using enough spoken context while still jumping to a precise timestamp,
So that results feel relevant and trustworthy, not arbitrary or over-confident.

**Acceptance Criteria:**

**Given** a video completes ingestion successfully  
**When** transcript segments are indexed for search  
**Then** the system persists **macro-level** units (longer text spans derived from consecutive ASR segments, with **configurable target size in word-like units** — primary: **words**; **tokens** allowed if documented and close to word granularity) with embeddings suitable for **phase-1** macro matching  
**And** **micro-level** units preserve original timestamp boundaries (or a defined parent/child mapping from macro to micro) so playback can seek to a **precise** `start_ts`/`end_ts`.

**Given** a fully ingested video and a natural-language query  
**When** the backend handles `POST /videos/{video_id}/search`  
**Then** retrieval uses: **(1)** hybrid macro retrieval on `macro_text_content` combining **dense** semantic ranking and **BM25** lexical ranking; **(2)** fuse rankings with **RRF** (configurable `k`, default 60) and keep top macro context entries (default top 10); **(3)** serialize structured macro→micro context (including micro ids, text, and start/end timestamps) for a **Mistral LLM** that infers **quote vs scene** intent and returns a **single float timestamp** (`start`) for the best micro segment; **(4)** map this deterministic output to seek fields and return snippet + **macro context + offsets** for highlight  
**And** end-to-end latency remains aligned with the PRD p95 target (≤ 10 seconds from submit to playback start) in informal demo testing, or trade-offs are documented.

**Given** a successful search response  
**When** the UI communicates match quality  
**Then** the experience does not rely on a **misleading numeric percentage** that clusters at high values for weak matches; it uses **tiered** or **relative** feedback (or omits raw scores) consistent with the UX spec’s guidance on confidence.

**Given** a successful search after multi-scale indexing (Story 3.3)  
**When** the primary page shows the transcript excerpt for the best match  
**Then** the UI displays the **full macro segment** (coarse retrieval context) as readable text **and** **highlights** the **fine / micro** segment (the exact span used for the seek timestamp) **inside** that macro text — so the user sees surrounding speech and which sub-passage was chosen.

**Given** stack constraints for the POC  
**When** implementing hybrid retrieval and LLM timestamp extraction  
**Then** **PostgreSQL + pgvector** with **cosine distance** on normalized Mistral embeddings is used for dense macro retrieval; lexical retrieval (BM25) is available for macro text; **Mistral** is used for the final timestamp extraction step per product constraint.

**Given** operators tune the system  
**When** they adjust environment variables  
**Then** they can change **macro word-like target size**, **RRF** constant, macro context **top-K**, and hybrid retrieval thresholds without code changes (documented in architecture and `.env.example`).

### Story 3.4: Quote-precise seeking for exact-phrase queries

As a user who remembers an exact quote,
I want the app to seek within ±5 seconds of the true quote timestamp,
So that I can jump precisely to the moment I recall.

_Note (depends on 3.3): **Quote** behavior is driven by the hybrid-retrieval context and **LLM** timestamp extraction path classifying **quote** intent from structured macro→micro evidence._

**Acceptance Criteria:**

**Given** I submit a quote-like query (for example, a short exact phrase from the transcript) for a demo video
**When** the search completes
**Then** the returned `start_ts` is within ±5 seconds of the true timestamp for that phrase (verified against a small curated set).

**Given** I run multiple quote queries from the curated set
**When** I test them manually during the demo
**Then** most results respect the ±5 second constraint in practice, with any known transcription/chunking limitations documented for the demo.

**Given** a quote query is impacted by transcription or chunking boundaries
**When** the search is executed
**Then** the system still returns a valid best-available segment
**And** the app does not crash.

### Story 3.5: Scene-coherent seeking for vague queries

As a user with a vague memory of a scene,
I want the app to jump to the start of a coherent scene near the best-matching region,
So that I avoid landing mid-sentence and the result feels natural for viewing.

_Note (depends on 3.3): **Scene** is the **default** when the query is **vague** and does not repeat specific wording; the **LLM** selects a coherent timestamp from structured context (often near scene start or representative passage)._

**Acceptance Criteria:**

**Given** I submit a vague, scene-style query
**When** the search completes
**Then** the returned `start_ts` is aligned to sentence or chunk boundaries (no mid-sentence cut)
**And** it is within 30 seconds of the similarity peak region for that query.

**Given** a curated set of vague demo queries
**When** I play the results
**Then** the video starts at scene/coherent boundaries (no obviously jarring mid-sentence starts) and feels close enough to the semantically correct area for the demo.

**Given** edge cases such as very short scenes or rapid topic shifts
**When** I run the search
**Then** the behavior remains reasonable (no crashes, no egregiously broken timestamps), and the limitation is acceptable for demo expectations.

### Epic 4: Demo-Ready UX & Reliability
Polish the UX and operational behavior so the app feels coherent and reliable for a live reviewer demo, focusing on clear feedback, sensible empty/error states, and smooth search→jump interactions (without building a formal evaluation harness).
**FRs covered:** (supports all FRs indirectly; no new FRs)

### Story 4.1: Primary page search interaction shows loading and handles timeout/errors

As a user,
I want the primary page search interaction to show clear loading feedback and recover gracefully from errors,
So that the demo never feels “stuck” or confusing.

**Acceptance Criteria:**

**Given** I submit a query on the primary page
**When** the request is in flight
**Then** the UI shows a visible loading state (spinner/disabled button) and prevents duplicate submits.

**Given** the search request takes too long or times out
**When** the timeout is reached
**Then** the UI shows a friendly timeout message and offers a way to retry.

**Given** the backend returns a structured error (`{ "error": { code, message } }`)
**When** the UI receives it
**Then** the UI displays `message` (and optionally a short hint) instead of raw codes.

### Story 4.2: Search results update the UI and seek the player to `start_ts`

As a user,
I want successful search results to update the UI and control the video player to the returned timestamp,
So that I immediately see the part of the video that matches my query.

**Acceptance Criteria:**

**Given** I receive a successful search response containing `start_ts` and `end_ts`
**When** the result is rendered
**Then** the video player seeks to `start_ts`
**And** when the response includes **macro context** and highlight bounds (Story **3.3**), the UI shows the **full macro** excerpt with the **fine** span **highlighted**, consistent with the UX spec — not a stale or partial snippet.

**Given** I have `start_ts`
**When** the player seek completes
**Then** the UI indicates that playback is starting from the returned region (e.g. “Playing from Xs”).

**Given** the search response is missing `start_ts` (or it is invalid)
**When** the UI attempts to render the result
**Then** the UI does not crash and shows an error state indicating the result cannot be played.

### Story 4.3: Smooth seeking UX when users run repeated searches

As a user,
I want repeated searches to update the player smoothly without inconsistent state,
So that the experience stays reliable during quick demo interactions.

**Acceptance Criteria:**

**Given** I run search A and then quickly submit search B
**When** search B returns
**Then** the UI reflects search B’s results (not search A’s) and the player seeks to B’s `start_ts`.

**Given** the player is currently seeking
**When** a new result is selected
**Then** the UI shows an updated seeking/loading indicator rather than leaving the UI in a previous state.

### Story 4.4: Admin page ingestion UI shows phases/progress clearly for all states

As an admin,
I want the admin page to clearly show ingestion status (including running progress and failed reasons),
So that I can manage the demo video lifecycle confidently.

**Acceptance Criteria:**

**Given** a video is in-progress (not completed)
**When** I view the admin page
**Then** I see its current ingestion phase and an overall progress indicator.

**Given** a video ingestion fails
**When** I view it in the admin list
**Then** the UI shows a failed state and a concise error summary (without exposing internal stack traces).

**Given** ingestion completes
**When** the next poll occurs
**Then** the admin page updates the status to “completed” (and reflects any final progress state).

### Story 4.5: Graceful system-level failure handling (backend unreachable / no data)

As a user or admin,
I want the app to handle “nothing is available” and “backend is unreachable” cleanly,
So that the demo doesn’t break presentation-wise.

**Acceptance Criteria:**

**Given** there are no registered videos yet
**When** I open the primary page or admin page
**Then** I see an explicit empty state message guiding the next action (e.g. “Ask an admin to ingest a video”).

**Given** the backend is unreachable (API not responding)
**When** the UI tries to fetch data
**Then** the UI shows a friendly “service unavailable” message and does not render broken placeholders.

