# Story 3.2: Natural-language search returns best-matching segment

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a user,
I want to enter a natural-language query and receive the best-matching transcript segment for the selected video,
so that I can quickly jump to the part I remember.

## Acceptance Criteria

1. **Search request wiring:** Given a fully ingested video is selected on the primary page, when the user submits a query, then the frontend calls `POST /videos/{video_id}/search` with the query text.
2. **Result contract usage:** Given the backend finds a match, when the API responds, then the response includes at least `start_ts`, `end_ts`, `text`, and `confidence`, and the UI displays snippet feedback while using timestamps for player control.
3. **Explicit no-match and error behavior:** Given search fails or no reasonable match is found, when the API responds, then the UI shows a clear French message (structured backend error or explicit no-match state) and never fails silently.
4. **Latency alignment:** Given demo-sized workload, when the user searches, then submit-to-seek-start behavior remains consistent with p95 target (<= 10 seconds, informal verification in story testing).

## Tasks / Subtasks

- [x] **Primary page search UX foundation**
  - [x] Extend `frontend/components/home/PrimaryReadyVideos.tsx` to include: selected ready video state, query input, submit button, loading state, and result/no-result/error states.
  - [x] Keep all product-facing copy in French via `frontend/lib/strings.ts` (no inline hard-coded strings).
- [x] **Search API proxy route**
  - [x] Add route handler `frontend/app/api/videos/[video_id]/search/route.ts` to proxy browser search requests to backend `POST /videos/{video_id}/search`.
  - [x] Preserve contract conventions: success returns direct payload; errors returned as `{ "error": { code, message } }`.
- [x] **Request/response typing and validation**
  - [x] Add a small search payload/response utility in `frontend/lib` (for example `videoSearch.ts`) to validate query body and guard response fields (`start_ts`, `end_ts`, `text`, `confidence`).
  - [x] Reuse existing parsing patterns from current primary/admin code instead of introducing a new error model style.
- [x] **Video player seek integration**
  - [x] Introduce a minimal home player component (for example `frontend/components/home/SemanticVideoPlayer.tsx`) or extend existing home rendering to support imperative seeking to `start_ts`.
  - [x] Ensure seek action is triggered on successful result and reflected in UI with a clear trust anchor message (e.g. "Lecture a partir de MM:SS").
- [x] **No-match and failure states**
  - [x] Handle two distinct cases in UI: explicit no-match (recoverable guidance) vs technical/API error (retry guidance).
  - [x] Keep UI behavior deterministic on repeated submits while one request is in flight (disable submit or cancel previous request consistently).
- [x] **Tests**
  - [x] Add unit tests for search payload/response guards in `frontend/lib`.
  - [x] Add component tests for key UI states: loading, success snippet/timestamp render, no-match, API error, and disabled submit when input is empty.

## Dev Notes

### Story scope and sequencing

- Story 3.1 already delivered ready-video filtering and polling in `PrimaryReadyVideos`; this story should build directly on that component rather than replacing it.
- Keep scope focused on "single best match" search to player seek. Multi-result ranking/history belongs to post-MVP flow.

### Existing implementation context (reuse, do not reinvent)

- Ready videos are already fetched from `GET /api/videos`, filtered by `filterCompletedVideos`, and polled every 8 seconds in `frontend/components/home/PrimaryReadyVideos.tsx`.
- French strings are centralized in `frontend/lib/strings.ts`; follow this pattern for all new search and feedback copy.
- Existing frontend error extraction already supports upstream `{ error: { message } }` and should be mirrored for search route handling.

### Architecture compliance guardrails

- Follow JSON/API naming conventions in snake_case (`start_ts`, `end_ts`, `video_id` in paths).
- Keep frontend patterns: PascalCase components, local component state, and simple fetch flow (no global state store).
- Keep success/error response contract shape aligned with architecture (`success` direct payload, `error` wrapped object).
- Preserve French-only browser UI (labels, loading, empty/no-match/error, button text).

### UX guardrails

- Respect the core loop: `video selection -> query submit -> visible searching state -> seek + playback`.
- Search must be gated by readiness: no selected completed video means submit is unavailable with clear helper text.
- No silent failures: every terminal request outcome must present explicit UI feedback.
- Favor calm, reviewer-grade feedback over decorative UI; trust comes from clear state transitions.

### API and data contract requirements

- Request body should minimally carry query text (existing backend contract may use `query` or `query_text`; verify current backend schema before final wiring).
- Expected success fields consumed by UI: `start_ts`, `end_ts`, `text`, `confidence`.
- Timestamps are seconds-from-start and should be treated as numeric values before formatting.

### Regression prevention guardrails

- Do not regress Story 3.1 behavior:
  - completed-only video list on primary page,
  - explicit loading/error/empty states,
  - access path to `/admin`,
  - backend health visibility on `frontend/app/page.tsx`.
- Do not introduce English UI copy in any new home-search element.
- Do not create a second fetch source for ready videos; extend existing list state where possible.

### Testing requirements

- Frontend component tests should verify:
  - submit disabled for empty query or no selected video,
  - loading state while search request runs,
  - successful response renders snippet and timestamp feedback,
  - no-match state renders explicit guidance,
  - structured error response renders French error text,
  - repeated submit behavior is deterministic.
- Utility tests should verify robust parsing/guarding of search payloads and fallback handling for malformed responses.

### Previous story intelligence (3.1)

- Story 3.1 established:
  - polling and completed-only readiness logic,
  - centralized French copy discipline,
  - lightweight `frontend/lib` utility + tests pattern for data guards.
- Maintain this continuity to reduce integration risk and implementation churn.

### Git intelligence summary

- Recent commits indicate progression from backend ingestion to admin listing, with frontend home integration currently under active local changes.
- Preferred implementation style in repo is incremental feature layering (small utilities + focused component updates + tests), not broad refactors.

### Latest technical information

- Current Next.js App Router guidance remains compatible with explicit fresh fetch behavior for rapidly changing UI state (`cache: "no-store"` for polling/search-sensitive paths).
- FastAPI `response_model` remains the stable way to enforce outbound shape; frontend should not assume extra fields beyond documented response contract.

### Project context reference

- No `project-context.md` detected.
- Authoritative planning sources are:
  - `_bmad-output/planning-artifacts/epics.md` (Epic 3 / Story 3.2)
  - `_bmad-output/planning-artifacts/architecture.md` (API contracts, naming, frontend patterns, French UI)
  - `_bmad-output/planning-artifacts/ux-design-specification.md` (core search loop and state honesty)
  - `_bmad-output/planning-artifacts/prd.md` (FR3 and latency/accuracy constraints)

## References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/implementation-artifacts/3-1-primary-page-lists-only-fully-ingested-videos.md`
- `frontend/app/page.tsx`
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/lib/strings.ts`
- `frontend/lib/readyVideos.ts`

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

- 2026-03-23: Created Story 3.2 implementation context with architecture, UX, and previous-story continuity.

### Implementation Plan

- Backend: `VideoSearchRequest` / `VideoSearchMatchResponse`, `search_best_segment` via pgvector cosine distance + Mistral query embedding, `POST /videos/{video_id}/search`; `GET /videos/{video_id}/file` for HTML5 playback via Next proxy.
- Frontend: `videoSearch.ts` guards, `POST` + `GET` media proxy routes under `app/api/videos/[video_id]/`, `SemanticVideoPlayer` + `PrimaryReadyVideos` search loop, Vitest + Testing Library coverage.

### Completion Notes List

- Implemented end-to-end search from primary page: radio selection among completed videos, French-only copy, `POST` to `/api/videos/{id}/search` with `{ query }`, snippet + confidence + “Lecture à partir de MM:SS”, player seek with `seekKey` for repeated searches.
- Backend search returns `NO_MATCH` (404) when no segments or distance above threshold; Mistral embedding failures return `UPSTREAM_ERROR` (502). Media route streams backend file for `<video src>`.
- Tests: `frontend/lib/videoSearch.test.ts`, `frontend/components/home/PrimaryReadyVideos.test.tsx`; `npm test` and `npm run build` pass.
- Minor type fix: `RegisterVideoForm` error message variable typed as `string` for `setError` compatibility.

### File List

- `backend/app/schemas/video.py`
- `backend/app/services/search_service.py`
- `backend/app/services/video_service.py`
- `backend/app/routers/videos.py`
- `frontend/app/api/videos/[video_id]/search/route.ts`
- `frontend/app/api/videos/[video_id]/media/route.ts`
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/components/home/PrimaryReadyVideos.test.tsx`
- `frontend/components/home/SemanticVideoPlayer.tsx`
- `frontend/components/admin/RegisterVideoForm.tsx`
- `frontend/lib/videoSearch.ts`
- `frontend/lib/videoSearch.test.ts`
- `frontend/lib/strings.ts`
- `frontend/vitest.config.ts`
- `frontend/vitest.setup.ts`
- `frontend/package.json`
- `frontend/package-lock.json`
- `_bmad-output/implementation-artifacts/3-2-natural-language-search-returns-best-matching-segment.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-23: Story 3.2 context created and marked ready-for-dev.
- 2026-03-23: Implemented Story 3.2 (search UI, API proxy, backend search + file endpoints, tests); status set to review.
