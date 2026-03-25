# Story 4.3: Smooth seeking UX when users run repeated searches

Status: review

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a user,
I want repeated searches to update the player smoothly without inconsistent state,
so that the experience stays reliable during quick demo interactions.

## Acceptance Criteria

1. **Latest search wins end-to-end:** Given I run search A and then quickly submit search B, when search B returns, then the UI reflects search B results (snippet/highlight) and the video player seeks to B's `start_ts` (not A's).

2. **Seek-state is honest while the player seeks:** Given a successful search returns `start_ts` and the player is seeking, when the player is in-flight, then the UI shows an explicit "seeking" state (French), and it is cleared only after the seek completion for the latest active seek.

3. **No stale seek completion feedback:** Given the player is seeking for an earlier search, when a newer search starts and changes the active seek target, then any later `seeked` event for the older seek must not show the old "Lecture a partir de ..." feedback nor leave the UI in the older state.

## Tasks / Subtasks

- [x] Implement a deterministic "seeking" UI state (AC: 2)
  - [x] Add explicit UI state in the primary search component (example: `isSeeking` boolean).
  - [x] Show a French-only seeking indicator as soon as the latest successful search schedules a seek (after `seekToSeconds` is set, before `seeked` fires).
  - [x] Clear the seeking indicator only when the player's `seeked` event fires for the latest seek.
  - [x] Keep the existing playback label behavior from Story 4.2: show "Lecture a partir de MM:SS" only after seek completion.

- [x] Preserve latest-seek protection (AC: 1, 3)
  - [x] Reuse the existing `seekKey` / `latestSeekKeyRef` guardrails from Story 4.2 (do not replace with a new parallel mechanism).
  - [x] Ensure any seeking timeout / cleanup logic (if added) is also tied to the latest seek key, so stale timers cannot override newer state.
  - [x] On new search start, reset seeking UI state to avoid showing stale "Lecture a partir de ..." while the next seek is pending.

- [x] Add seeking robustness to avoid "stuck loading" (recommended guardrail)
  - [x] Add an optional seek timeout (example 6-10s) that clears `isSeeking` and shows a French error such as "Lecture impossible automatiquement" if `seeked` does not fire for the latest seek.
  - [x] The timeout error must not break search-to-results rendering; it should only affect the "seeking" indicator behavior.

- [x] Update/extend frontend tests (AC: 2, 3)
  - [x] Extend `frontend/components/home/PrimaryReadyVideos.test.tsx` to assert the seeking indicator appears after a successful search response but before dispatching the media `seeked` event.
  - [x] Add a repeated-search test:
    - Run search A (successful response, but do NOT dispatch `seeked` yet).
    - Run search B (successful response).
    - Dispatch `seeked` once (representing the latest seek completing).
    - Assert that the playback feedback corresponds to B (`Lecture a partir de ...` for B's `start_ts`) and that stale completion from A does not appear.

## Dev Notes

### Story context and dependencies

- This story is a UX polish + reliability improvement over Story 4.2.
- Story 4.2 already established deterministic result-to-player seeking behavior and "latest search wins" protection.
- Story 4.3 focuses specifically on the user experience when multiple searches happen in quick succession, especially the seek-in-progress UI state and protection against stale seek completion feedback.

### Technical requirements (must follow)

- **Keep API contract unchanged:** no backend endpoints, schemas, or response shapes must change for this story.
- **Keep existing seek completion semantics:** continue using the player's media `seeked` event as the point where playback feedback can be shown (aligned with Story 4.2).
- **Use existing stale-request protection:** continue relying on request cancellation (`AbortController` / abort) and the existing latest-seek guardrails (`seekKey`, `latestSeekKeyRef`), rather than introducing a new selection mechanism.
- **Repeated-search behavior must remain deterministic:**
  - A newer search must not be overwritten by older in-flight requests.
  - A newer seek must not be overwritten by an older seek completion event.

### Architecture compliance guardrails

- **No new backend endpoints or DB work** for this story.
- Frontend changes should be limited to the primary page search/player modules:
  - component-level state for seeking indicator
  - localized French copy for the seeking indicator and any timeout/seek error message
- Naming conventions must stay consistent:
  - API fields in `snake_case`
  - React components in `PascalCase`
  - helpers/utilities exported as `camelCase`

### UX and localization guardrails

- All new user-visible copy must be **French-only** and should live in `frontend/lib/strings.ts` (centralized copy strategy).
- Seeking UI must be honest:
  - show seeking feedback while seek completion is pending
  - never show "Lecture a partir de ..." for a seek that is not the latest completed one
- Avoid implying guaranteed success where the seek completion event may not fire; if a timeout guardrail is added, message must be action-oriented and non-alarming.

### File structure requirements

- Primary expected touch points (adapt if code structure differs, but keep scope tight):
  - `frontend/components/home/PrimaryReadyVideos.tsx`
  - `frontend/components/home/SemanticVideoPlayer.tsx` (only if you need extra callbacks; prefer state-only changes in PrimaryReadyVideos)
  - `frontend/components/home/PrimaryReadyVideos.test.tsx`
  - `frontend/lib/strings.ts` (add seeking indicator strings)
- Prefer extending existing state and event wiring over refactors.

### Testing requirements

- Add/extend automated tests for:
  - seeking indicator shown after successful search response
  - seeking indicator cleared on `seeked` event
  - repeated-search scenario does not show stale playback feedback from earlier seek
- Regression checks:
  - do not break existing timeout and structured error behaviors from Story 4.1
  - do not break macro context + highlight rendering from Story 4.2

### Previous story intelligence (Story 4.2)

- Story 4.2 already uses:
  - `AbortController` / abort signaling to stop stale search responses
  - `seekKey` bumping to ensure repeated seeks (even to same `start_ts`) still execute
  - `latestSeekKeyRef` gating so only the latest seek completion updates "Lecture a partir de ..."
- This story should build on those mechanisms, not replace them.

### Git intelligence summary (recent patterns)

- Recent work in this area has been incremental and test-led, primarily in:
  - `frontend/components/home/PrimaryReadyVideos*`
  - `frontend/lib/videoSearch*`
- Follow the same approach: targeted UI state additions + RTL/Vitest regression tests.

### Latest technical information

- `HTMLMediaElement.currentTime` + `seeked` is a reliable cross-browser indicator for seek completion in modern browsers.
- However, some browser/media pipeline edge cases can cause missing `seeked` events; a short seeking timeout is a reasonable UX guardrail to prevent the UI from getting stuck.

### Project context reference

- No `project-context.md` file was discovered in this repository.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 4, Story 4.3)
- `_bmad-output/planning-artifacts/architecture.md` (frontend state conventions; French-only UX)
- `_bmad-output/planning-artifacts/prd.md` (search-to-playback loop + trust requirements)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (honest loading states; JumpFeedback trust model)
- `_bmad-output/implementation-artifacts/4-2-search-results-update-the-ui-and-seek-the-player-to-start-ts.md` (deterministic seek + stale completion protection baseline)
- `_bmad-output/implementation-artifacts/4-1-primary-page-search-interaction-shows-loading-and-handles-timeout-errors.md` (loading lifecycle + timeout UX baseline)

## Dev Agent Record

### Agent Model Used
gpt-5.4-nano

### Debug Log References
- 2026-03-25: Added deterministic seek-in-progress UI via `isSeeking` + French seeking indicator, displayed after `seekToSeconds` is scheduled and cleared on latest `seeked`.
- 2026-03-25: Preserved Story 4.2 latest-seek protection by using the existing `seekKey` / `latestSeekKeyRef` guardrails for both seeking UI and the seek-timeout guard.
- 2026-03-25: Added a guarded seek-timeout UX error that only affects the seeking indicator state (does not disrupt results rendering).
- 2026-03-25: Extended RTL tests (including repeated-search regression) and verified with `npm test` (vitest run).

### Completion Notes List
- Implemented the requested "seeking" UI state (`fr.homeSearchSeeking`) and ensured "Lecture à partir de ..." remains post-seek-only.
- Ensured stale seek completion cannot clear/alter the seeking UI by gating all seeking UI updates through the latest seek key.
- Added the optional seek-timeout guardrail (French: `Lecture impossible automatiquement...`) with latest-seek binding so stale timers cannot override newer state.

### File List
- `_bmad-output/implementation-artifacts/4-3-smooth-seeking-ux-when-users-run-repeated-searches.md`
- `frontend/components/home/PrimaryReadyVideos.tsx`
- `frontend/components/home/PrimaryReadyVideos.test.tsx`
- `frontend/lib/strings.ts`

### Change Log

- 2026-03-25: Implemented deterministic seek-in-progress UX with latest-seek guarding, plus seek-timeout UX error, and added repeated-search regression tests.

