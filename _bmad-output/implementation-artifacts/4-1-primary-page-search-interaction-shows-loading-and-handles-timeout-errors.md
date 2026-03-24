# Story 4.1: Primary page search interaction shows loading and handles timeout/errors

Status: review

## Story

As a user,
I want the primary page search interaction to show clear loading feedback and recover gracefully from errors,
so that the demo never feels "stuck" or confusing.

## Acceptance Criteria

1. Given I submit a query on the primary page, when the request is in flight, then the UI shows a visible loading state (spinner/disabled button) and prevents duplicate submits.
2. Given the search request takes too long or times out, when the timeout is reached, then the UI shows a friendly timeout message and offers a way to retry.
3. Given the backend returns a structured error (`{ "error": { code, message } }`), when the UI receives it, then the UI displays `message` (and optionally a short hint) instead of raw codes.

## Tasks / Subtasks

- [x] Implement in-flight search UX state and duplicate-submit protection (AC: 1)
  - [x] Ensure submit button enters loading/disabled state while request is active.
  - [x] Block Enter-key and click-based duplicate submits while `isSearching` is true.
  - [x] Surface a clear French loading string (for example `Recherche en cours...`) and keep the query input behavior consistent with current UX patterns.
- [x] Add deterministic search timeout handling on the primary page (AC: 2)
  - [x] Introduce request cancellation with `AbortSignal.timeout(...)` (or equivalent abort strategy) for search requests.
  - [x] Distinguish timeout from other failures and map timeout to a friendly French user message with explicit retry affordance.
  - [x] Ensure request cleanup on repeated searches/unmount so stale requests cannot leak state.
- [x] Map backend structured errors to user-friendly French UI feedback (AC: 3)
  - [x] Parse `{ error: { code, message } }` safely and display `message` (or a localized fallback) in the primary search surface.
  - [x] Never expose raw internal codes as the primary user-facing message.
  - [x] Keep compatibility with current success path (`start_ts`/seek flow) and avoid regressions in existing match rendering.
- [x] Add frontend test coverage for loading, timeout, and structured-error behaviors (AC: 1, 2, 3)
  - [x] Add/extend component or hook tests to verify disabled button + duplicate submit prevention during in-flight request.
  - [x] Add tests for timeout path and retry behavior.
  - [x] Add tests for structured backend error rendering.

## Dev Notes

### Story context and dependencies

- Epic 4 focuses on demo UX and reliability polish; this story is the gateway interaction quality for the primary search loop.
- Story 4.2 depends on stable search-state behavior from this story (clear loading lifecycle and resilient error handling before player seek updates).
- Existing backend search contract is already established in Epic 3; this story is primarily frontend interaction hardening.

### Technical requirements (must follow)

- Keep API contract unchanged and consume existing search endpoint shape:
  - `POST /videos/{video_id}/search` for request.
  - Success payload with `start_ts`, `end_ts`, `text` and optional macro/highlight fields.
  - Error payload in standard shape `{ "error": { code, message } }`.
- Use explicit timeout/cancellation for search requests in the frontend (modern pattern: `AbortSignal.timeout(...)`; fallback to `AbortController` if needed by runtime constraints).
- Preserve current "latest search wins" safety posture: stale or aborted responses must not override newer UI state.

### Architecture compliance guardrails

- Do not add new backend endpoints, schemas, or caching to satisfy this story.
- Preserve frontend architecture conventions:
  - Local component state or existing fetch hook patterns.
  - Explicit loading/error flags (`isSearching`, `error`) per architecture guidance.
- Keep naming conventions and payload field naming in `snake_case` for API interactions.

### UX and localization guardrails

- All user-visible copy must remain French-only in the UI.
- Keep feedback honest and action-oriented:
  - Loading must be visibly active (no silent freeze).
  - Timeout must clearly explain retry path.
  - Error must be concise and non-technical for user surface.
- Align with UX spec principles:
  - "Latency is part of UX": never leave dead air.
  - "Trust before sparkle": clear state transitions over decorative behavior.

### File structure requirements

- Primary expected touch points (adapt to exact current code organization):
  - `frontend/...` search form / primary page component hosting query submit.
  - Existing frontend API client/helper for `POST /videos/{video_id}/search`.
  - Frontend tests near existing search UI or hooks.
- Avoid introducing parallel search state managers if existing components/hooks can be extended.

### Testing requirements

- Add/extend automated frontend tests for:
  - In-flight loading state and duplicate-submit prevention.
  - Timeout handling with user-visible retry path.
  - Structured backend error rendering (`error.message` shown to user).
- Regression checks:
  - Successful response still flows into current seek/update behavior.
  - Repeated searches do not leave UI stuck in loading/error state.
- If test tooling cannot run in current environment, document attempted commands and blocker details in Dev Agent Record.

### Previous story intelligence (3.5)

- Preserve normalized payload compatibility already reinforced in Story 3.5 (`start_ts`, `end_ts`, snippet/context fields).
- Keep trust-oriented UX direction from Story 3.5: avoid misleading confidence-centric messaging; favor clear action feedback.
- Continue additive, focused changes in current service/component boundaries rather than broad refactors.

### Git intelligence summary (recent patterns)

- Recent commits show iterative, scoped delivery around search quality and ingestion:
  - `fix: refining the LLM prompt for the final step of the search pipeline`
  - `feat: semantic search within transcript using hybrid approach (dense vector search + BM-25)`
  - `feat: Video ingestion pipeline`
- Follow same pattern: minimal-surface UX hardening + targeted tests.

### Latest technical information

- Frontend timeout handling: `AbortSignal.timeout()` is broadly available in modern runtimes and cleanly distinguishes timeout from manual abort (`TimeoutError` vs `AbortError`), making it suitable for resilient search UX.
- FastAPI error handling supports structured JSON in exception details; frontend should continue relying on backend-provided `error.message` and local French fallback copy when missing.

### Project context reference

- No `project-context.md` file was discovered in this repository.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.1)
- `_bmad-output/planning-artifacts/architecture.md` (error format, frontend loading/error conventions, API contract)
- `_bmad-output/planning-artifacts/prd.md` (latency/trust requirements)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (French-only UI, loading/timeout/error UX principles)
- `_bmad-output/implementation-artifacts/3-5-scene-coherent-seeking-for-vague-queries.md` (previous story learnings and compatibility guardrails)

## Dev Agent Record

### Agent Model Used

gpt-5.3-codex-low

### Debug Log References

- 2026-03-24: Created Story 4.1 context from epics, architecture, PRD, UX spec, Story 3.5, and recent git history.
- 2026-03-24: Added technical guardrails for timeout cancellation, duplicate-submit prevention, and structured error rendering.
- 2026-03-24: Implemented frontend loading/timeout/retry hardening on primary search flow with stale request cancellation safety.
- 2026-03-24: Added/extended tests for duplicate-submit protection, timeout + retry UX, and structured error fallback behavior.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story is optimized for frontend implementation reliability with explicit UX, localization, and regression guardrails.
- Story status set to `ready-for-dev`.
- Implemented deterministic search timeout cancellation with explicit timeout message and retry button in French-only UI copy.
- Preserved latest-search-wins behavior by aborting prior requests and preventing stale request state leaks on repeated searches and unmount.
- Hardened structured error extraction to avoid exposing internal all-caps error codes as user-facing messages.
- Verified success path compatibility (`start_ts` seek flow and match rendering) with passing component tests.
- Test command executed successfully: `pnpm --dir frontend test -- components/home/PrimaryReadyVideos.test.tsx lib/videoSearch.test.ts`.

### File List

- `_bmad-output/implementation-artifacts/4-1-primary-page-search-interaction-shows-loading-and-handles-timeout-errors.md`
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/components/home/PrimaryReadyVideos.test.tsx`
- `frontend/lib/videoSearch.ts`
- `frontend/lib/videoSearch.test.ts`
- `frontend/lib/strings.ts`

## Change Log

- 2026-03-24: Implemented Story 4.1 primary search loading state hardening, timeout + retry UX, structured error fallback handling, and frontend regression tests; status moved to `review`.
