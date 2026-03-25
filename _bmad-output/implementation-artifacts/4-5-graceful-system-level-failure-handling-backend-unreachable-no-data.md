# Story 4.5: Graceful system-level failure handling (backend unreachable / no data)

Status: ready-for-dev

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story
As a user or admin,
I want the app to handle “nothing is available” and “backend is unreachable” cleanly,
so that the demo doesn’t break presentation-wise.

## Acceptance Criteria
1. **Empty state when there is nothing to search / manage yet:**
   Given there are no registered videos yet
   When I open the primary page or admin page
   Then I see an explicit empty state message guiding the next action (e.g. “Ask an admin to ingest a video”).

2. **Friendly service unavailable when the backend cannot be reached:**
   Given the backend is unreachable (API not responding)
   When the UI tries to fetch data
   Then the UI shows a friendly “service unavailable” message and does not render broken placeholders.

## Tasks / Subtasks
- [x] Primary page (`PrimaryReadyVideos`) empty state UX
  - [x] When `GET /api/videos` yields an empty list (or no `ingestion_status="completed"` items), show `fr.homeReadyVideosEmpty`.
  - [x] Avoid rendering broken search/player placeholders; show `fr.homeSearchNoVideoSelected` in the search card.

- [x] Primary page load error UX for backend unreachable / non-OK responses
  - [x] On network errors (fetch throws), show `fr.homeReadyVideosError` and render an error element with `role="alert"`.
  - [x] On non-OK responses, extract `error.message` when present (from `{ "error": { code, message } }`); otherwise fall back to `fr.homeReadyVideosError`.

- [x] Backend health banner messaging on the Home page
  - [x] When server-side `/health` indicates unavailable (or fails), show `fr.backendUnavailable` in the backend status section.

- [x] Admin page (`AdminVideoList`) empty and load error states
  - [x] When `GET /api/videos` returns `[]`, show `fr.adminEmpty`.
  - [x] On fetch failures / non-OK responses / invalid payload shapes, show `fr.adminLoadError` and do not render the table.

- [ ] Testing coverage for Story 4.5 reliability states
  - [ ] Add/extend `frontend/components/home/PrimaryReadyVideos.test.tsx`:
    - [ ] empty list: `/api/videos` -> `[]` shows `fr.homeReadyVideosEmpty` and `fr.homeSearchNoVideoSelected`
    - [ ] network failure: fetch throws -> shows `fr.homeReadyVideosError`
    - [ ] optional: structured non-OK response (`{ error: { message } }`) displays that message (and never raw codes)
  - [ ] Add/extend tests for `frontend/components/admin/AdminVideoList.tsx` (empty list + load failure), if there is no existing admin coverage.

- [ ] Regression checks
  - [ ] Ensure existing search-to-playback tests still pass (loading, timeout, structured error, repeated searches).
  - [ ] Ensure the updated list payload fields (`error_code`, `error_message`) remain compatible with type guards and rendering.

## Dev Notes
### Story context and dependencies
- Epic 4 is about demo-ready UX and reliability; this story prevents the two “demo-breakers”:
  - “nothing is available” (empty list)
  - “backend is unreachable” (network failure / non-OK response while fetching list)
- This story builds on Epic 4’s reliability foundations:
  - Story 4.1 (structured errors + French-only error rendering)
  - Story 4.4 (admin list shape extension and French-only ingestion failure summaries)

### Technical requirements (must follow)
- API contract (keep unchanged)
  - `GET /videos` / `GET /api/videos` must remain a **direct** JSON array payload (no wrapper), even when empty: `[]`.
  - All API failures must keep the standard error wrapper: `{ "error": { code, message } }`.
- Client robustness
  - Never assume the videos payload is valid; use a type guard and show a fallback error if the payload shape is unexpected.
  - Catch fetch/network exceptions and show the friendly message; do not attempt to render undefined placeholders.

### Architecture compliance guardrails
- Do NOT add new backend endpoints specifically for this story.
- Keep changes additive and scoped to frontend “list fetch + state rendering” logic and tests.
- Preserve naming conventions:
  - JSON fields and schemas use `snake_case`
  - React components are `PascalCase`
  - helpers/utilities are `camelCase`

### UX and localization guardrails
- All user-visible copy in the browser must be French-only and come from `frontend/lib/strings.ts`:
  - Primary: `fr.homeReadyVideosEmpty`, `fr.homeReadyVideosError`
  - Backend banner: `fr.backendUnavailable`
  - Admin: `fr.adminEmpty`, `fr.adminLoadError`
- The “service unavailable” message must be friendly and action-oriented; never surface raw backend error codes as primary user-facing copy.

### File structure requirements
Primary touch points (and where tests should be added):
- `frontend/app/page.tsx` (backend health banner)
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/components/home/PrimaryReadyVideos.test.tsx`
- `frontend/components/admin/AdminVideoList.tsx`
- `frontend/lib/strings.ts`

### Testing requirements
- Use Vitest + React Testing Library (match existing test patterns).
- Minimum automated coverage:
  - Primary page empty state and backend unreachable/load failure state.
- Optional automated coverage:
  - Admin list empty state and load failure state.

### References
- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.5)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (French-only UX principles, empty/error messaging)
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/components/admin/AdminVideoList.tsx`
- `frontend/app/page.tsx`
- `frontend/lib/strings.ts`

## Questions / Assumptions
- Which string should be considered the canonical “service unavailable” message?
  - server-side banner uses `fr.backendUnavailable`
  - client-side list fetch failures use `fr.homeReadyVideosError` / `fr.adminLoadError`
  If you prefer one unified wording, confirm and we can align copy.
- Primary page uses `filterCompletedVideos` (only `ingestion_status="completed"`). The “empty state” therefore appears when there are no completed videos (even if ingestion is still running). This matches the current product wording (“video ready for search”). If you intended “no registered videos at all”, adjust the empty-state condition accordingly.

