# Story 3.5: Scene-coherent seeking for vague queries

Status: review

## Story

As a user with a vague memory of a scene,
I want the app to jump to the start of a coherent scene near the best-matching region,
so that I avoid landing mid-sentence and the result feels natural for viewing.

## Acceptance Criteria

1. Given I submit a vague, scene-style query, when search completes, then returned `start_ts` is aligned to sentence/chunk boundaries (no mid-sentence cut) and within 30 seconds of the similarity peak region.
2. Given a curated set of vague demo queries, when results are played, then starts are scene-coherent (no jarring mid-sentence starts) and close to the semantically correct area for demo use.
3. Given edge cases (very short scenes, rapid topic shifts), when search runs, then behavior stays reasonable (no crashes, no egregiously broken timestamps) with acceptable demo limitations documented.

## Tasks / Subtasks

- [x] Enforce scene-intent extraction path for vague queries (AC: 1, 3)
  - [x] Ensure scene intent is the default when query is not quote-like.
  - [x] Ensure Mistral scene path returns a scene-start sentence anchor from structured macro->micro context.
  - [x] Keep deterministic lexical resolution and fallback behavior if extractor output is weak or missing.
- [x] Add coherence guardrails around selected timestamp (AC: 1, 3)
  - [x] Prevent mid-sentence starts by resolving to sentence/chunk boundary-aligned micro segment.
  - [x] Enforce "near similarity peak" behavior (within 30 seconds) with deterministic fallback if needed.
- [x] Add curated vague-query evaluation coverage (AC: 2, 3)
  - [x] Add fixture(s) for vague scene queries and expected target zones.
  - [x] Add repeatable assertions for boundary alignment and 30-second constraint.
- [x] Preserve API and UI contracts (AC: 1, 2)
  - [x] Continue returning normalized payload (`start_ts`, `end_ts`, `text`, macro highlight fields when available).
  - [x] Keep compatibility with current frontend seek + macro-highlight rendering flow.
- [x] Document known scene-boundary limitations and demo expectations (AC: 2, 3)
  - [x] Record limitations from ASR segmentation and rapid topic shifts.
  - [x] Keep user-facing trust model aligned with UX guidance (no misleading percentage-only confidence).

## Dev Notes

### Story context and dependencies

- Depends on Story `3.3` architecture (hybrid macro retrieval: dense + BM25 + RRF; structured macro->micro context; intent-aware Mistral extraction; lexical resolution).
- Builds after Story `3.4` quote-hardening work; this story focuses on the scene-default behavior for vague recall.
- Must preserve PRD/NFR expectations: coherent starts for vague queries and end-to-end demo usability.

### Technical requirements (must follow)

- Keep search pipeline contract in existing backend services:
  - `backend/app/services/search_service.py`
  - `backend/app/services/mistral_client.py`
- Maintain current stack constraints: FastAPI + Pydantic, PostgreSQL + pgvector, Mistral-only model usage.
- Scene path must be intent-aware and deterministic at output mapping:
  - LLM chooses scene-start sentence anchor from provided context.
  - Backend lexical resolver maps to final micro segment/timestamp.
  - Fallback path remains robust and never crashes.
- Keep response conventions unchanged:
  - Success as direct payload (snake_case).
  - Errors as `{ "error": { code, message } }`.

### Architecture compliance guardrails

- Do not add new retrieval services or caching layers.
- Reuse existing macro/micro indices and hybrid retrieval utilities.
- Keep environment-driven knobs for retrieval behavior and thresholds in config and `.env.example` when adding tunables.
- Preserve API naming and schema conventions from architecture (`snake_case`, plural REST resources).

### File structure requirements

- Implementation updates should remain in established locations:
  - `backend/app/services/` for search/mistral logic.
  - `backend/tests/` for behavior and regression tests.
  - `backend/tests/fixtures/` for curated vague query fixtures.
- Avoid introducing parallel scene-specific service modules unless unavoidable; extend current search pipeline.

### Testing requirements

- Add/adjust tests for:
  - Scene-default intent detection for vague queries.
  - Sentence/chunk boundary-aligned start timestamp behavior.
  - 30-second proximity guardrail from similarity peak.
  - Edge-case resilience (short scenes, rapid topic shifts, low-quality anchors).
- Add curated vague-query set checks suitable for repeatable local execution.
- If runtime tests cannot be executed in environment, include explicit execution notes and commands.

### Previous story intelligence (3.4)

- Quote-path contracts and lexical fallback were recently hardened; preserve those behaviors and avoid regressions while extending scene behavior.
- Existing tests/fixtures patterns in `backend/tests/fixtures/` should be reused for scene evaluation.
- Keep macro highlight response compatibility unchanged for frontend trust UX.

### Git intelligence summary (recent patterns)

- Follow recent incremental backend-search style and focused commits:
  - `fix: refining the LLM prompt for the final step of the search pipeline`
  - `feat: semantic search within transcript using hybrid approach (dense vector search + BM-25)`
  - `feat: Video ingestion pipeline`
- Prefer additive updates to current service boundaries with targeted tests over broad refactors.

### Latest technical information

- No required framework/library migration is needed for this story.
- Prioritize stability of the existing Mistral extraction contract and deterministic lexical mapping behavior.

### Project context reference

- No `project-context.md` file was discovered in this repository.

### References

- `_bmad-output/planning-artifacts/epics.md` (Story 3.5, Epic 3 context)
- `_bmad-output/planning-artifacts/architecture.md` (search contract, environment knobs, conventions)
- `_bmad-output/planning-artifacts/prd.md` (vague-query coherence and latency expectations)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (trust cues, coherence expectations, French UI policy)
- `_bmad-output/implementation-artifacts/3-4-quote-precise-seeking-for-exact-phrase-queries.md` (previous story learnings)

## Dev Agent Record

### Agent Model Used

gpt-5.3-codex-low

### Debug Log References

- 2026-03-24: Story context generated from epics, architecture, PRD, UX spec, previous Story 3.4, and recent git history.
- 2026-03-24: Implemented scene-default intent enforcement and near-peak timestamp guardrail in search pipeline.
- 2026-03-24: Added curated vague-scene fixture and deterministic tests for scene intent and 30-second guardrails.
- 2026-03-24: Could not run pytest locally because `pytest` is unavailable in the current environment (`python3 -m pytest` reports module missing).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Scene intent now defaults to `scene` for non-quote-like queries while preserving quote behavior for explicit verbatim requests.
- Added deterministic near-peak selection guardrail to keep returned starts within 30 seconds of the top similarity region.
- Updated Mistral prompt guidance to prefer scene-start anchors for scene intent.
- Added curated vague-scene fixture coverage and assertions for guardrail behavior.
- Validation command attempted: `python3 -m pytest tests/test_search_adaptive.py -q` (blocked by missing pytest module).

### File List

- `_bmad-output/implementation-artifacts/3-5-scene-coherent-seeking-for-vague-queries.md`
- `backend/app/services/search_service.py`
- `backend/app/services/mistral_client.py`
- `backend/tests/test_search_adaptive.py`
- `backend/tests/fixtures/vague_scene_set.json`

### Change Log

- 2026-03-24: Implemented scene-coherence improvements for vague queries (scene-default intent routing, near-peak fallback guardrail, curated vague-scene evaluation fixtures/tests) and moved story status to `review`.
