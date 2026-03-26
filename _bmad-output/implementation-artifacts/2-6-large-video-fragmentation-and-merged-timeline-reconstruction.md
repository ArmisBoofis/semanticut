# Story 2.6: Large-video fragmentation and merged timeline reconstruction

Status: in-progress

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As an admin,
I want long videos to be automatically fragmented and reassembled into one transcript timeline,
so that ingestion succeeds past model size limits without breaking timestamp accuracy.

## Acceptance Criteria

1. **Fragment trigger and sizing:** Given a video duration is strictly greater than 30 minutes, when ingestion starts, then the system creates sequential fragments of maximum 30 minutes each, and the final fragment is shorter when a remainder exists.
2. **Exactly-30-min behavior:** Given a video duration is exactly 30 minutes, when ingestion starts, then fragmentation is not triggered and the existing single-pass transcription path is used.
3. **Global timestamp continuity:** Given fragment transcripts return per-fragment local timestamps, when merge/reconstruction runs, then each segment receives a cumulative offset equal to the sum of prior fragment durations, and persisted `start_ts` / `end_ts` are monotonic on the original full-video timeline.
4. **Failure correctness:** Given one fragment transcription fails, when job status is requested, then ingestion is marked `failed` (or retryable only if explicit retry policy exists), diagnostics are visible via existing safe error fields, and the video is not marked `completed` with a partial merged timeline.
5. **Search clock consistency:** Given a chunked ingestion (`>30 min`) completes successfully, when search runs for that video, then returned `start_ts` and `end_ts` refer to the original video clock with no timestamp reset at fragment boundaries.

## Tasks / Subtasks

- [x] **Fragment orchestration in ingestion pipeline** (AC: 1, 2)
  - [x] Add duration gate in worker pipeline: `duration_seconds > 1800` uses fragment mode, otherwise keep current single-pass mode.
  - [x] Create deterministic fragment plan (`index`, `start_offset_sec`, `duration_sec`) with max 1800 seconds and remainder handling.
  - [x] Keep path and naming safe under `VIDEO_STORAGE_ROOT` (reuse existing safe path rules; no traversal).
- [x] **Transcription flow for fragments** (AC: 1, 2, 4)
  - [x] Execute transcription fragment-by-fragment with explicit phase/progress updates compatible with Story 2.4 status model.
  - [x] Preserve deterministic ordering and stop the pipeline on first unrecoverable fragment error.
  - [x] Ensure failure path sets job status and error fields exactly once and prevents partial "completed" state.
- [x] **Merge + timestamp reconstruction** (AC: 3)
  - [x] Convert each fragment-local segment timestamp to global timestamp using cumulative prior-fragment duration offsets.
  - [x] Persist merged segments in original chronological order for the same `video_id`.
  - [x] Enforce monotonicity guard (at least non-decreasing `start_ts`, `end_ts >= start_ts`) before insert.
- [x] **Search compatibility verification** (AC: 5)
  - [x] Confirm existing search retrieval reads merged global timeline without codepath fork.
  - [x] Add regression test(s) proving returned seek values cross fragment boundaries without reset.
- [x] **Ops and observability updates** (AC: 1, 4)
  - [x] Add config/env knobs for fragmentation threshold and optional fragment overlap/behavior only if already supported by existing config pattern.
  - [x] Add structured logs for fragment plan and reconstruction summary (fragment count, merged segment count, min/max timestamps).
- [ ] **Tests** (AC: 1-5)
  - [x] Unit tests for fragment planning (29:59, 30:00, 30:01, multi-fragment with remainder).
  - [x] Unit tests for merge offset reconstruction and monotonic timestamp invariants.
  - [ ] Integration test for successful `>30 min` ingestion path producing global timeline.
  - [ ] Integration test for single fragment failure marking job failed and preventing completed status.
  - [ ] Search-level integration/regression asserting global-clock `start_ts` / `end_ts` after chunked ingest.

## Dev Notes

### Story foundation and business context

- This story implements FR8/NFR8 from planning artifacts: long videos must be fragmented only when strictly above 30 minutes, then reconstructed into one global timeline.
- It extends Story 2.4 async ingestion behavior; no new UI surface is required for MVP beyond truthful status/failure reporting already established.

### Current implementation baseline (from previous stories)

- Ingestion worker exists (`backend/app/worker.py`) and already processes pending jobs asynchronously (Story 2.4).
- `transcript_segments` persistence and status progression (`pending/running/completed/failed`, phase + progress + error fields) are already in place.
- `delete_video` / cancellation coordination already exists; fragment mode must remain compatible with cancellation and row-deletion checks.
- Search services already consume persisted segments/timestamps. This story must preserve that contract instead of introducing alternate timestamp semantics.

### Architecture compliance guardrails

- Keep API/data conventions from `architecture.md`: snake_case fields, direct success payloads, wrapped error object.
- Keep stack constraints: FastAPI + SQLAlchemy + PostgreSQL/pgvector + Mistral + Docker Compose.
- Do not introduce new storage systems, queues, or non-Mistral AI providers in this story.
- Keep French UI behavior untouched; this story is backend-heavy and should not add English strings to user-facing pages.

### Technical requirements (must-follow)

- Fragment trigger is **strictly** `duration > 1800` seconds (not `>=`).
- Fragment boundaries must be deterministic and contiguous; no gaps and no overlap unless overlap is an explicit existing pattern in code.
- Reconstruction offset formula:
  - For fragment `i`, `global_start = local_start + sum(duration(fragment[j]) for j < i)`.
  - Same for `global_end`.
- Persisted merged order must preserve chronological playback semantics and enable existing retrieval logic unchanged.
- If any fragment fails:
  - mark job failed,
  - keep diagnostic fields consistent with current error model,
  - do not set completed and do not expose partial merged timeline as final output.

### Suggested file touch points

- `backend/app/services/ingestion_service.py` (fragment planning, orchestration, merge/reconstruction).
- `backend/app/worker.py` (phase sequencing and failure handling if worker-level updates are needed).
- `backend/app/config.py` and `.env.example` (only if new fragmentation knobs are added).
- `backend/tests/test_ingestion_phases.py` and/or new ingestion service test module.
- `backend/tests/test_videos_api.py` and/or search integration tests tied to merged timeline behavior.

### Testing requirements and Definition of Done signals

- Red-green-refactor is expected for dev-story execution.
- Required coverage for this story:
  - planning boundaries around 1800 seconds,
  - offset reconstruction invariants,
  - failure atomicity (no false completed state),
  - search timestamp continuity after chunked ingest.
- Full backend regression suite must pass after implementation; no breakage to existing Story 2.4/2.5 tests.

### Previous story intelligence (2.5 and 2.4)

- Story 2.5 reinforced shared file-system contract between `api` and `worker` for video paths; fragment artifacts must remain under the same safe root rules.
- Story 2.4 established status-phase and error reporting conventions and worker polling model; reuse these patterns rather than inventing new job-state semantics.
- Keep compatibility with cancellation/deletion behavior introduced around Story 2.3/2.4.

### Git intelligence summary (recent patterns)

- Recent commits emphasize incremental refinements and keeping behavior stable (`fix:` commits after feature additions).
- Prefer narrowly scoped changes with explicit tests over broad pipeline rewrites.

### Latest technical notes (for implementation decisions)

- FastAPI/Starlette upload stack remains `python-multipart` based; no change required by this story, but keep worker/API file contract unchanged.
- FFmpeg segmentation should favor deterministic segment plans and explicit timestamp reconstruction in application logic (do not rely solely on muxer timestamp flags as the source of truth).

### Project context reference

- No `project-context.md` detected in repository.
- Authoritative context sources are:
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
  - `_bmad-output/implementation-artifacts/2-4-asynchronous-ingestion-pipeline-for-registered-videos.md`
  - `_bmad-output/implementation-artifacts/2-5-admin-can-register-videos-via-admin-ui-upload-form.md`

## References

- `_bmad-output/planning-artifacts/epics.md` - Story 2.6 acceptance criteria
- `_bmad-output/planning-artifacts/prd.md` - FR8/NFR8 and ingestion expectations
- `_bmad-output/planning-artifacts/architecture.md` - Data/API conventions and stack constraints
- `_bmad-output/planning-artifacts/ux-design-specification.md` - state honesty and progress behavior
- `_bmad-output/implementation-artifacts/2-4-asynchronous-ingestion-pipeline-for-registered-videos.md` - worker/status baseline
- `_bmad-output/implementation-artifacts/2-5-admin-can-register-videos-via-admin-ui-upload-form.md` - path and storage contract continuity

## Dev Agent Record

### Agent Model Used

GPT-5.3 Codex (Cursor)

### Debug Log References

- 2026-03-26: Implemented fragment mode in `ingestion_service` with deterministic plan generation, per-fragment transcription, global timestamp reconstruction, and monotonicity guard.
- 2026-03-26: Added config knob `INGESTION_FRAGMENT_MAX_SECONDS` and documented it in `.env.example`.
- 2026-03-26: Added unit tests in `backend/tests/test_ingestion_fragmentation.py` for planning boundaries and merge invariants.
- 2026-03-26: Validation note: local environment lacks `pytest` module, so runtime test execution could not be completed in this session.

### Completion Notes List

- Created story context for 2.6 with implementation guardrails for fragment planning, reconstruction invariants, failure atomicity, and search timestamp continuity.
- Added test-focused subtasks targeting boundary conditions and regression prevention for existing ingestion/search flows.
- Included architecture, previous story intelligence, and recent git pattern guidance to minimize implementation drift.
- Implemented strict fragment trigger (`duration > threshold`) with deterministic contiguous fragment plan generation.
- Implemented fragment-by-fragment audio extraction/transcription and hard-stop behavior on unrecoverable fragment failures.
- Implemented global timestamp reconstruction from fragment-local timestamps, with monotonicity checks before persistence.
- Added structured logs for fragment plan and merge summary metrics.
- Added unit tests covering 29:59/30:00/30:01 boundaries, multi-fragment remainder handling, global offset merge, and non-monotonic guard behavior.

### File List

- `_bmad-output/implementation-artifacts/2-6-large-video-fragmentation-and-merged-timeline-reconstruction.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `.env.example`
- `backend/app/config.py`
- `backend/app/services/ingestion_service.py`
- `backend/tests/test_ingestion_fragmentation.py`

### Change Log

- 2026-03-26: Created Story 2.6 file with comprehensive developer context and ready-for-dev status.
- 2026-03-26: Implemented fragmentation orchestration, timestamp reconstruction, and unit tests; story remains in-progress pending integration/regression tests.
