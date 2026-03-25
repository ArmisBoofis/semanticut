# Story 4.4: Admin page ingestion UI shows phases/progress clearly for all states

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As an admin,
I want the admin page to clearly show ingestion status (including running progress and failed reasons),
so that I can manage the demo video lifecycle confidently.

## Acceptance Criteria

1. **In-progress visibility (not completed): phase + overall progress**
   Given a video is not in the final `completed` state,
   when I view it on the admin page,
   then I see:
   - its ingestion status (badge),
   - a clear ingestion phase label (or a clear queued placeholder),
   - an overall progress indicator that is consistent with the API fields.

2. **Failed state: failed badge + concise error summary**
   Given a video ingestion fails (`ingestion_status = failed`),
   when I view the admin list,
   then the UI shows:
   - a failed state (badge),
   - a concise error summary suitable for a demo operator,
   - without exposing internal stack traces or raw backend error details in a user-hostile way.

3. **Completed state: status update + final progress state on next poll**
   Given ingestion completes (`ingestion_status = completed`),
   when the next admin poll occurs,
   then the admin page updates the row to `completed` and reflects the final progress state.

## Tasks / Subtasks

- [x] **Backend: extend list payload with failed details**
  - [x] Update `backend/app/schemas/video.py`:
    - Extend `VideoListItem` with:
      - `error_code: str | None = None`
      - `error_message: str | None = None`
  - [x] Update `backend/app/services/video_service.py` with helpers to fetch these values from `video.ingestion_job`:
    - e.g. `ingestion_error_code_for_video(video: Video) -> str | None`
    - e.g. `ingestion_error_message_for_video(video: Video) -> str | None`
  - [x] Update `backend/app/routers/videos.py` (`GET /videos`) to populate the new fields from the ingestion job relationship.
  - [x] Ensure list remains a **direct payload** array (no wrapper) and stays consistent with existing list fields (snake_case).

- [x] **Backend tests: list shape covers failed state**
  - [x] Update existing tests in `backend/tests/test_videos_api.py` so happy-path / phase-progress tests also assert:
    - `error_code is None`
    - `error_message is None`
  - [x] Add a new backend test that:
    - sets an `IngestionJob` to `status="failed"`
    - sets `error_code` and `error_message`
    - then calls `GET /videos`
    - and asserts the list item includes those fields for that video.

- [x] **Frontend: render phases + progress clearly for all states**
  - [x] Update `frontend/components/admin/AdminVideoList.tsx`:
    - Extend `VideoListItem` type to include `error_code` / `error_message`.
    - Update the table row rendering to handle:
      - `pending` (queued): show a deterministic queued/first-phase label and a clear overall progress indicator.
      - `running`: keep existing phase label + progress bar behavior.
      - `completed`: ensure the phase column is not ambiguous/blank; show a clear “completed” phase label and final progress state.
      - `failed`: ensure a failed row shows both the phase/progress (when available) and the required concise error summary.
  - [x] Do NOT switch admin polling strategy; keep the existing polling of `GET /api/videos` (8s) and rely on updated list payloads.

- [x] **Frontend: failed error summary must be demo-operator friendly and French-only**
  - [x] Add a French mapping from `error_code` to a concise summary message (prefer `error_code` over raw `error_message` if `error_message` is not guaranteed to be French).
  - [x] Ensure the UI never surfaces raw stack traces:
    - do not display backend stack traces directly
    - do not display long technical dumps
    - keep summaries short and action-oriented (e.g. “check configuration”, “file missing”, “transcription failed”).
  - [x] Add a fallback message for unknown or missing error codes.

- [x] **Frontend helpers: add unit tests for label/error mappings**
  - [x] Extend `frontend/lib/ingestionStatus.ts` with pure helper(s) for:
    - phase label for queued/completed if required (based on `ingestion_status` + `ingestion_phase`)
    - failed error summary for `error_code`
  - [x] Update `frontend/lib/ingestionStatus.test.ts` with unit tests for:
    - pending/running/completed/failed mapping
    - at least a couple of known `error_code` values
    - unknown/fallback behavior

- [x] **Regression checks**
  - [x] Ensure delete and registration flows still work unchanged:
    - `DeleteVideoConfirmDialog` behavior
    - `RegisterVideoForm` submit + refresh behavior
  - [x] Ensure the admin table still passes the `isVideoListPayload` guard and does not fail on extra fields.
  - [x] Ensure `AdminVideoList` continues to be robust to unexpected payload shapes (best-effort fallback messages in French).

## Dev Notes

### Story context and dependencies

- This story is an enhancement to the existing admin ingestion list UI created in:
  - `Story 2.2` (list with status + phase + progress)
  - `Story 2.4` (worker phases, progress_percent mapping, ingestion error persistence, status endpoint)
- Current admin list (`frontend/components/admin/AdminVideoList.tsx`) already displays `ingestion_status`, `ingestion_phase`, and `ingestion_progress_percent`, but it does not yet surface the failed reason required by Story 4.4.

### Technical requirements (must follow)

- **API naming and format:**
  - JSON fields must remain `snake_case`.
  - `GET /videos` must remain a direct array payload with direct item objects (no wrapper).
- **Success / error contract:**
  - This story extends success payloads; do not change the error wrapper shape for API failures (`{ "error": { code, message } }`).
- **Do not add new status endpoints as a first step:**
  - Prefer extending the existing list response (`GET /videos` proxied by `GET /api/videos`).
  - Adding a new `GET /videos/{id}/status` proxy is acceptable only if extending the list proves insufficient or too large for the UI needs.

### Architecture compliance guardrails

- Keep changes additive/minimal:
  - backend: add fields to `VideoListItem`
  - frontend: render those fields only where needed
- Avoid refactors of ingestion phases or worker orchestration for this story.

### UX and localization guardrails

- **French-only user-visible copy in the browser.**
  - Phase/status labels already come from `frontend/lib/ingestionStatus.ts` and are French.
  - Failed error summaries must be French and concise.
- **Honest progress:**
  - Avoid indeterminate fake progress.
  - If pending/queued does not expose progress_percent from the API, show a deterministic and truthful queued indicator (e.g. 0% + queued label), or show a clear “not started yet” message while keeping the table layout stable.
- **Accessibility:**
  - The list already uses `aria-live="polite"` on the table container.
  - For failed rows, render the error summary with an appropriate role (e.g. `role="alert"` for the message element) and keep it short.

### Ingestion phase and progress semantics (reference)

- Backend phase constants and overall progress mapping:
  - `extracting_audio` -> 0%
  - `transcribing` -> 20%
  - `chunking` -> 40%
  - `embedding` -> 60%
  - `indexing` -> 80%
  - `completed` sets 100%
  - `failed` leaves the last progress/phase values at failure time
- Backend status values:
  - `pending`, `running`, `completed`, `failed`, plus reserved `unknown`.

### File structure requirements

Expected primary touch points:
- Backend
  - `backend/app/schemas/video.py` (`VideoListItem`)
  - `backend/app/services/video_service.py` (new helper functions)
  - `backend/app/routers/videos.py` (`GET /videos`)
  - `backend/tests/test_videos_api.py` (new + updated assertions)
- Frontend
  - `frontend/components/admin/AdminVideoList.tsx` (failed summary + improved phase/progress rendering)
  - `frontend/lib/ingestionStatus.ts` (queued/completed phase labels and error summary mapping helpers)
  - `frontend/lib/ingestionStatus.test.ts` (unit tests)
  - `frontend/lib/strings.ts` (if adding any new French UI copy strings)

### Testing requirements

- Backend (pytest):
  - Ensure list items include the new fields for all states, with `None` values for non-failed items.
  - Ensure failed list items include `error_code` and `error_message`.
- Frontend (Vitest + RTL):
  - Prefer unit tests for pure mapping helpers (`ingestionStatus.ts`).
  - Optional: a lightweight rendering test for `AdminVideoList` by stubbing `fetch("/api/videos")` with a failed row payload and asserting the French error summary appears.

### Previous story intelligence (2.2 / 2.4 / 2.5 and Epic 4)

- The admin list already:
  - polls the list endpoint every ~8 seconds,
  - renders status badges and phase/progress,
  - uses French-only labels for status/phase.
- Epic 4 stories emphasize UX honesty and explicit state transitions; apply the same discipline here:
  - show failures clearly
  - avoid raw technical details
  - keep the polling-driven updates stable.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.4)
- `_bmad-output/planning-artifacts/architecture.md` (API contracts, ingestion job fields, localization rules)
- `_bmad-output/planning-artifacts/prd.md` (async ingestion progress + admin path)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (Ingestion transparency + failure UX)
- `_bmad-output/implementation-artifacts/2-2-admin-page-listing-all-videos-with-ingestion-status.md` (baseline list UI behavior)
- `_bmad-output/implementation-artifacts/2-4-asynchronous-ingestion-pipeline-for-registered-videos.md` (error persistence + status endpoint semantics)
- `backend/app/ingestion/phases.py` (phase -> progress mapping rule)
- `backend/app/services/ingestion_service.py` (where error_code/error_message are persisted)
- `frontend/components/admin/AdminVideoList.tsx` (current UI rendering; missing failed reasons)

## Questions / Assumptions

- Backend `error_message` values may not be guaranteed to be French. This story assumes the UI will present French summaries derived from `error_code` (or translate/sanitize `error_message` before rendering).
- If the team prefers to show `error_message` directly, confirm it is already French and concise for demo operators; otherwise implement `error_code` -> French summary mapping.

