# Story 3.1: Primary page lists only fully ingested videos

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a user,
I want the primary page to list only videos that are fully ingested and ready for search,
so that I can immediately run searches without encountering half-processed items.

## Acceptance Criteria

1. **Completed-only filtering:** Given videos exist across statuses (`pending`, `running`, `completed`, `failed`), when the user opens the primary page, then only videos with ingestion status `completed` are shown in the selectable/searchable list.
2. **Live readiness transition:** Given a video transitions from `running` to `completed`, when polling refreshes data on the primary page, then that video appears automatically without full-page reload.
3. **Clear empty state:** Given no `completed` videos exist, when the user opens the primary page, then the UI shows a clear French empty state explaining that no searchable videos are ready yet and guiding the user to admin ingestion.
4. **No accidental search on non-ready videos:** Given videos are not completed, when the user attempts to use search entry points, then UI keeps search disabled or unavailable until at least one completed video is available.

## Tasks / Subtasks

- [x] **Primary page foundation (frontend)**
  - [x] Replace current health-only home content in `frontend/app/page.tsx` with a primary page shell that keeps French copy and includes: page title, link to admin, searchable video list area, and empty state.
  - [x] Preserve backend health resilience behavior (`fetchBackendHealth`) while adding video readiness UI, so backend-down state still remains understandable.
- [x] **Video data retrieval and filtering**
  - [x] Reuse `GET /api/videos` route (`frontend/app/api/videos/route.ts`) for primary page data source.
  - [x] Filter client-side to `ingestion_status === "completed"` for this story (API contract remains unchanged).
  - [x] Poll every 5-10 seconds (8 seconds is already used in admin and is acceptable) to detect newly completed videos.
- [x] **UI states and French-only strings**
  - [x] Add centralized French strings in `frontend/lib/strings.ts` for primary video list heading, helper text, empty state, loading state, and unavailable/error state.
  - [x] Keep all user-visible copy in French (`fr-FR` requirement).
- [x] **Search gating behavior**
  - [x] Ensure any search trigger/control introduced on primary page is disabled/hidden until one completed video is present.
  - [x] If search UI is deferred to Story 3.2+, include explicit placeholder copy indicating search is available only for fully ingested videos.
- [x] **Tests**
  - [x] Add frontend unit tests for filtering and UI states (at minimum: mixed statuses only renders completed, empty state when none completed, transition after refresh).
  - [x] Keep existing backend tests unchanged; this story is frontend behavior on top of existing `/videos` response.

## Dev Notes

### Current implementation facts (do not guess)

- Home page currently only shows backend health status and admin link (`frontend/app/page.tsx`).
- `GET /api/videos` already proxies backend `GET /videos` with `cache: "no-store"` and structured upstream error mapping (`frontend/app/api/videos/route.ts`).
- Backend list endpoint returns `ingestion_status`, `ingestion_phase`, and `ingestion_progress_percent` per video (`backend/app/routers/videos.py`, `backend/app/schemas/video.py`).
- Admin list already uses polling + structured error handling and French status labels (`frontend/components/admin/AdminVideoList.tsx`, `frontend/lib/ingestionStatus.ts`).

### Architecture compliance

- Keep REST/API contract intact: success payloads direct, errors wrapped as `{ "error": { code, message } }`.
- Keep naming conventions: JSON fields in `snake_case`; frontend component names in `PascalCase`.
- Keep UI language French-only for user-visible copy; centralize strings in `frontend/lib/strings.ts`.
- Do not add new global store or caching layer; use local state and simple polling/fetch patterns.

### File structure requirements

- Primary implementation targets:
  - `frontend/app/page.tsx`
  - `frontend/lib/strings.ts`
  - `frontend/lib/ingestionStatus.ts` (reuse if status badges/labels are needed)
  - Optional new component if page grows:
    - `frontend/components/home/PrimaryReadyVideos.tsx`
- Keep backend untouched unless absolutely required by an implementation blocker (none identified for this story).

### Reinvention prevention guardrails

- Reuse existing `/api/videos` proxy and error parsing patterns from admin components; do not create duplicate fetch contracts.
- Reuse existing ingestion status label helpers from `frontend/lib/ingestionStatus.ts` when displaying statuses.
- Reuse existing admin polling interval approach unless there is a measurable UX reason to change.

### Regression prevention guardrails

- Do not expose non-completed videos on the primary page (core FR6 behavior).
- Do not regress current home-page access to admin route.
- Do not hard-code English copy in new components.
- Ensure empty/error/loading states remain explicit (no blank screens).

### Testing requirements

- Frontend tests should verify:
  - Mixed-status payload renders only completed videos.
  - Empty state appears with zero completed videos.
  - Error state appears when `/api/videos` fails.
  - Poll refresh can reveal a newly completed video.
- Optional backend test is not required for this story because filtering is view logic based on already-tested API fields.

### Latest technical notes

- Next.js App Router route handlers are not cached by default for non-GET, and `fetch(..., { cache: "no-store" })` remains the correct pattern for fresh polling data in GET proxy paths.
- FastAPI `response_model=list[...]` remains a strong boundary for list payload stability and field filtering; current `/videos` implementation already follows this pattern.

### Project context reference

- No `project-context.md` detected.
- Authoritative sources for this story:
  - `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.1)
  - `_bmad-output/planning-artifacts/architecture.md` (local state, French UI, API conventions)
  - `_bmad-output/planning-artifacts/ux-design-specification.md` (primary flow, state honesty, French-only UI)
  - `_bmad-output/planning-artifacts/prd.md` (FR6 + UX constraints)

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 3 / Story 3.1 acceptance criteria
- `_bmad-output/planning-artifacts/architecture.md` - frontend patterns, localization, API format
- `_bmad-output/planning-artifacts/ux-design-specification.md` - primary page behavior, French UI, empty states
- `_bmad-output/planning-artifacts/prd.md` - FR6 and success criteria context
- `frontend/app/page.tsx`
- `frontend/app/api/videos/route.ts`
- `frontend/lib/strings.ts`
- `frontend/components/admin/AdminVideoList.tsx`
- `backend/app/routers/videos.py`
- `backend/app/schemas/video.py`

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

- 2026-03-23: Implemented primary-page ready-videos client section with `/api/videos` polling (8s), completed-only filtering, and explicit loading/error/empty/search-gating French states.
- 2026-03-23: Added reusable payload/filter helpers in `frontend/lib/readyVideos.ts` and unit tests in `frontend/lib/readyVideos.test.ts`.
- 2026-03-23: Validations run: `npm test` (10 passed) and `npm run lint` (no warnings/errors) in `frontend/`.

### Completion Notes List

- Story context prepared for frontend implementation of completed-only filtering on primary page.
- Existing backend contracts already provide required status fields; no API change needed in this story.
- Polling + French copy + explicit empty/error states are mandatory to preserve UX and FR6 behavior.
- Home page now keeps backend health visibility while adding a primary ready-videos section that only renders videos with `ingestion_status: "completed"`.
- Search entry-point remains intentionally unavailable in this story with explicit French placeholder copy, and only appears as "coming soon" messaging once at least one ready video exists.
- Filtering logic and payload validation are centralized in `frontend/lib/readyVideos.ts` and covered by unit tests for mixed status filtering, empty-state behavior, and transition across refresh cycles.

### File List

- `_bmad-output/implementation-artifacts/3-1-primary-page-lists-only-fully-ingested-videos.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `frontend/app/page.tsx`
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/lib/readyVideos.ts`
- `frontend/lib/readyVideos.test.ts`
- `frontend/lib/strings.ts`

### Change Log

- 2026-03-23: Story 3.1 created with implementation guardrails, architecture/UX references, and ready-for-dev status.
- 2026-03-23: Implemented completed-only primary-page video listing with 8-second polling, French UI states, search gating placeholder, and frontend unit tests.
