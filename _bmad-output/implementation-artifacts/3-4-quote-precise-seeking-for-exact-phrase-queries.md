# Story 3.4: Quote-precise seeking for exact-phrase queries

Status: in-progress

## Story

As a user who remembers an exact quote,  
I want the app to seek within +-5 seconds of the true quote timestamp,  
so that I can jump precisely to the moment I recall.

## Acceptance Criteria

1. Given I submit a quote-like query (short exact phrase from transcript) for a demo video, when the search completes, then returned `start_ts` is within +-5 seconds of the true phrase timestamp on a curated quote set.
2. Given I run multiple curated quote queries manually, when results are reviewed, then most results satisfy the +-5s target in practice and known ASR/chunking limits are documented.
3. Given quote queries are affected by ASR/chunk boundaries, when search executes, then the system still returns a valid best-available segment and the app does not crash.

## Tasks / Subtasks

- [ ] Finalize quote-path extraction contract in search pipeline (AC: 1, 3)
  - [ ] Ensure quote intent uses sentence-anchor output from Mistral and lexical micro-segment resolution on shortlisted context.
  - [ ] Keep deterministic fallback path when extractor output is empty/invalid.
- [ ] Implement curated quote evaluation flow (AC: 1, 2)
  - [ ] Add a small curated quote set fixture (query, expected timestamp, tolerance metadata).
  - [ ] Add a repeatable check (test or script) asserting `abs(returned_start_ts - expected_ts) <= 5`.
- [ ] Harden API response behavior for degraded quote matches (AC: 3)
  - [ ] Always return normalized payload or structured error shape, never unhandled exceptions.
  - [ ] Preserve compatibility with current frontend `start_ts`/`end_ts`/text rendering contract.
- [ ] Validate demo behavior and update implementation notes (AC: 2)
  - [ ] Document known limitations due to transcription quality and chunk boundaries.
  - [ ] Capture practical pass-rate evidence for curated quote set.

## Dev Notes

### Story context and dependencies

- This story depends on Story `3.3` (hybrid macro retrieval + intent-aware sentence-anchor extraction).
- Scope is quote precision only; scene-coherence behavior remains Story `3.5`.
- Keep PRD NFR alignment: p95 submit->playback target <=10s while adding quote-precision validation.

### Technical guardrails (must follow)

- Retrieval stack remains: dense macro retrieval + BM25 + RRF over macro context, then Mistral extraction over structured macro->micro context.
- For quote-like intent, anchor selection must prioritize verbatim/near-verbatim sentence evidence from shortlisted context before final lexical micro resolution.
- Do not introduce new vector DB/cache services; keep PostgreSQL + pgvector stack.
- Use existing backend module boundaries (`services/search_service.py`, `services/mistral_client.py`, related config in `config.py` and `.env.example`).
- Preserve API conventions: snake_case fields, direct success payload, wrapped error object `{ "error": { code, message } }`.

### File structure requirements

- Backend changes should remain under existing service/test paths:
  - `backend/app/services/` for search/extraction logic.
  - `backend/tests/` for quote precision and fallback coverage.
  - Optional fixture data in existing test fixture conventions.
- Avoid creating parallel "quote search" service unless required; extend current search pipeline implementation from Story `3.3`.

### Testing requirements

- Add or update unit tests for:
  - Quote-intent anchor extraction parsing/validation.
  - Lexical resolution preferring quote-accurate micro segment.
  - Deterministic fallback when quote anchor extraction is weak.
- Add curated quote-set validation asserting +-5 seconds tolerance.
- If runtime test execution is unavailable in environment, leave explicit execution note and exact command for local/container run.

### Previous story intelligence (3.3)

- Existing macro/micro indexing and hybrid retrieval are already in place; leverage them instead of re-implementing retrieval stages.
- Story `3.3` notes indicate plain-text sentence-anchor extraction path and lexical fallback were recently added; Story `3.4` should harden quote precision specifically and verify behavior against curated quotes.
- Prior risk noted: test runtime availability (`pytest`) can block validation; plan validation path early.

### Git intelligence (recent patterns)

- Recent commits focus on search pipeline refinement and hybrid retrieval; follow the same incremental style:
  - `fix: refining the LLM prompt for the final step of the search pipeline`
  - `feat: semantic search within transcript using hybrid approach (dense vector search + BM-25)`
- Maintain additive changes with tight tests over service-layer behavior.

### Latest technical information

- No mandatory library migration is required for this story. Favor current project dependencies and contracts already codified in architecture/PRD.
- Keep Mistral extractor prompt/output contract stable and explicit for quote intent to avoid brittle regressions.

### Project structure notes

- Respect architecture localization rule: frontend user-facing text remains French; backend internals/tests can stay English.
- Keep all environment tunables documented in `.env.example` when adding quote-evaluation toggles or thresholds.

### References

- `_bmad-output/planning-artifacts/epics.md` (Story 3.4, Epic 3 context)
- `_bmad-output/planning-artifacts/architecture.md` (search pipeline, API conventions, environment knobs)
- `_bmad-output/planning-artifacts/prd.md` (NFR3 +-5s precision, latency expectations)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (trustworthy search feedback, French UI)
- `_bmad-output/implementation-artifacts/3-3-multi-scale-transcript-indexing-with-hybrid-macro-retrieval-and-direct-llm-timestamp-extraction.md` (prior implementation learnings)

## Dev Agent Record

### Agent Model Used

gpt-5.3-codex-low

### Debug Log References

- 2026-03-24: Updated search pipeline to consume quote/scene-aware sentence-anchor JSON output from Mistral and keep deterministic fallback to top shortlisted micro segment when extraction is empty/invalid.
- 2026-03-24: Hardened macro highlight offset handling to return best-effort offsets instead of throwing internal errors on macro/micro text mismatch.
- 2026-03-24: Added curated quote fixture plus repeatable tolerance assertions (`<= 5s`) in unit tests.
- 2026-03-24: Validation blocked in current runtime (`pytest` command missing and `python -m pytest` has no installed module).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Dev Agent (2026-03-24): Implemented quote-intent aware anchor extraction contract in pipeline and deterministic degraded fallback behavior for empty/invalid extractor output.
- Dev Agent (2026-03-24): Added curated quote precision fixture and repeatable tolerance checks validating `abs(returned_start_ts - expected_ts) <= 5`.
- Dev Agent (2026-03-24): Could not execute tests in this environment because `pytest` is unavailable; tasks remain unchecked pending executable test runtime.

### Change Log

- 2026-03-24: Started implementation for Story 3.4 (status moved to `in-progress`), added quote-intent anchor contract wiring, degraded-path hardening, and curated quote precision tests/fixtures.

### File List

- `_bmad-output/implementation-artifacts/3-4-quote-precise-seeking-for-exact-phrase-queries.md`
- `backend/app/services/mistral_client.py`
- `backend/app/services/search_service.py`
- `backend/tests/test_search_anchor_llm.py`
- `backend/tests/test_search_adaptive.py`
- `backend/tests/fixtures/quote_precision_set.json`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
