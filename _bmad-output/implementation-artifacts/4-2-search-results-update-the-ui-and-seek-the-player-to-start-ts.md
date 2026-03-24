# Story 4.2: Search results update the UI and seek the player to `start_ts`

Status: review

## Story

As a user,
I want successful search results to update the UI and control the video player to the returned timestamp,
so that I immediately see the part of the video that matches my query.

## Acceptance Criteria

1. Given I receive a successful search response containing `start_ts` and `end_ts`, when the result is rendered, then the video player seeks to `start_ts` and when the response includes macro context and highlight bounds (Story 3.3), the UI shows the full macro excerpt with the fine span highlighted, consistent with the UX spec, not a stale or partial snippet.
2. Given I have `start_ts`, when the player seek completes, then the UI indicates that playback is starting from the returned region (for example, “Lecture a partir de Xs” or `MM:SS` format).
3. Given the search response is missing `start_ts` (or it is invalid), when the UI attempts to render the result, then the UI does not crash and shows an error state indicating the result cannot be played.

## Tasks / Subtasks

- [x] Wire successful search result state to deterministic player seek (AC: 1, 2)
  - [x] Use the existing search success callback/state to trigger seek on the currently loaded video element.
  - [x] Ensure seek targets the latest successful result only (do not allow stale responses to override newer user actions).
  - [x] Show clear French post-seek feedback once seek completes.
- [x] Render full macro context with precise fine-span highlight (AC: 1)
  - [x] Prefer backend-provided `macro_context_text`, `match_start_offset`, `match_end_offset` when available.
  - [x] Keep fallback behavior safe when offsets are absent: render trusted snippet without misleading highlight.
  - [x] Prevent stale snippet rendering when a new request starts or when result belongs to an older query.
- [x] Harden invalid/missing timestamp behavior (AC: 3)
  - [x] Validate `start_ts` before attempting seek (number, finite, non-negative).
  - [x] If invalid/missing, keep UI stable and show French error copy with retry guidance.
  - [x] Do not break existing successful rendering paths (`text`, macro context, highlight).
- [x] Add automated regression tests (AC: 1, 2, 3)
  - [x] Test successful path: seek called with `start_ts`, UI reflects play-from feedback.
  - [x] Test macro+fine rendering with offset highlight bounds.
  - [x] Test invalid/missing `start_ts` path: no crash, no unsafe seek call, explicit user-facing error.

## Dev Notes

### Story context and dependencies

- This story builds directly on Story 4.1 search lifecycle hardening (loading, timeout, structured errors).
- It depends on Epic 3 search response contract stabilization (Story 3.3 multi-scale fields and normalized payload).
- Story 4.3 will rely on this story to guarantee deterministic result-to-player synchronization for repeated searches.

### Technical requirements (must follow)

- Keep existing API contract and endpoint:
  - `POST /videos/{video_id}/search` remains the only source for match payload.
  - Success payload compatibility: `start_ts`, `end_ts`, `text`, optional `macro_context_text`, `match_start_offset`, `match_end_offset`.
  - Error payload stays `{ "error": { code, message } }`.
- Player seek implementation should use browser-standard media behavior:
  - Set `HTMLMediaElement.currentTime = start_ts` for seek.
  - Use completion semantics from media events (for example `seeked`) to show "playing from" feedback when seek is done.
- Preserve "latest search wins" behavior introduced in 4.1:
  - Older responses must not overwrite newer result UI or player target.

### Architecture compliance guardrails

- No new backend endpoints or schema changes for this story.
- Keep frontend changes within existing primary-page search/player modules:
  - component-level state and existing helper utilities (`videoSearch`, string map, player component).
- Preserve naming conventions:
  - API payload fields in `snake_case`.
  - Components `PascalCase`; frontend utility exports `camelCase`.

### UX and localization guardrails

- French-only UI copy remains mandatory for all new user-facing messages.
- Reinforce trust-oriented UX from the UX spec:
  - success should show concrete playback anchor (timestamp text),
  - highlight should explain why the jump happened (macro context + fine span),
  - invalid timestamp should fail safely with actionable, non-technical messaging.
- Do not introduce misleading raw confidence percentages as the primary trust signal.

### File structure requirements

- Primary expected touch points:
  - `frontend/components/home/PrimaryReadyVideos.tsx`
  - `frontend/components/home/SemanticVideoPlayer.tsx`
  - `frontend/lib/videoSearch.ts`
  - `frontend/lib/strings.ts`
  - `frontend/components/home/PrimaryReadyVideos.test.tsx`
  - `frontend/lib/videoSearch.test.ts`
- Prefer extending current modules instead of creating parallel abstractions for seek state.

### Testing requirements

- Add/extend frontend tests for:
  - successful seek invocation and post-seek feedback rendering,
  - macro context + highlight offsets rendering behavior,
  - invalid/missing `start_ts` defensive behavior.
- Regression checks:
  - loading/timeout/structured error behavior from 4.1 remains intact,
  - successful results still update player and transcript UI together.
- If local test execution is blocked, capture attempted command and blocker in Dev Agent Record.

### Previous story intelligence (4.1)

- Reuse the hardened request lifecycle and stale-request protection implemented in 4.1.
- Keep additive scoped changes over large refactors; preserve existing test style and file organization.
- Continue centralized French strings approach and avoid exposing backend error codes directly.

### Git intelligence summary (recent patterns)

- Recent work is highly incremental, with targeted changes + tests in existing search modules.
- Commits touching this area commonly update:
  - `frontend/components/home/PrimaryReadyVideos*`
  - `frontend/lib/videoSearch*`
  - `frontend/lib/strings.ts`
- Align implementation to this established pattern for consistency and low regression risk.

### Latest technical information

- `HTMLMediaElement.currentTime` and `seeked` event are broadly supported and provide reliable seek-completion signaling in modern browsers.
- `AbortSignal.timeout()` remains useful from 4.1 for request lifecycle, but browser differences can report timeout as `AbortError` in some cases; keep user messaging robust to both timeout-related abort names.

### Project context reference

- No `project-context.md` was discovered in this repository.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.2; Story 3.3 contract dependency)
- `_bmad-output/planning-artifacts/architecture.md` (API response shape, frontend state conventions, localization requirements)
- `_bmad-output/planning-artifacts/prd.md` (search-to-playback latency and trust outcomes)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (French-only UI, jump feedback, highlight trust model)
- `_bmad-output/implementation-artifacts/4-1-primary-page-search-interaction-shows-loading-and-handles-timeout-errors.md` (request lifecycle and error handling baseline)

## Dev Agent Record

### Agent Model Used

gpt-5.3-codex-low

### Debug Log References

- 2026-03-24: Created Story 4.2 context from epics, architecture, PRD, UX spec, Story 4.1, and recent git history.
- 2026-03-24: Added explicit guardrails for seek completion feedback, highlight rendering, and invalid timestamp hardening.
- 2026-03-24: Implemented deterministic seek completion handling via `seeked` callback and latest-seek key tracking.
- 2026-03-24: Extended payload parsing to support missing macro fields/offsets and added fallback-safe rendering.
- 2026-03-24: Added/updated regression tests for seek feedback timing, offset-less rendering, and invalid `start_ts`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story status set to `ready-for-dev`.
- Implementation scope constrained to existing frontend search/player modules with regression-focused test expectations.
- Implemented player seek completion feedback only after `seeked` event to avoid premature "play from" messaging.
- Hardened invalid/missing `start_ts` handling with explicit French unplayable-result message and no unsafe seek attempt.
- Preserved macro highlight when offsets exist; fallback now renders trusted non-highlighted context/snippet when offsets are absent.
- Verified with targeted test run: `npm test -- --run components/home/PrimaryReadyVideos.test.tsx lib/videoSearch.test.ts` (19 passing).

### File List

- `_bmad-output/implementation-artifacts/4-2-search-results-update-the-ui-and-seek-the-player-to-start-ts.md`
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/components/home/SemanticVideoPlayer.tsx`
- `frontend/lib/videoSearch.ts`
- `frontend/lib/strings.ts`
- `frontend/components/home/PrimaryReadyVideos.test.tsx`
- `frontend/lib/videoSearch.test.ts`

### Change Log

- 2026-03-24: Implemented deterministic result-to-player seeking with post-seek UX feedback, safe invalid timestamp handling, and regression tests for macro highlight fallback and seek timing.

