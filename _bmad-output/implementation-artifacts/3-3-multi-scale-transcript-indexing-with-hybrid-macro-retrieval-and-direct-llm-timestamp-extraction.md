# Story 3.3: Multi-scale transcript indexing with hybrid macro retrieval and sentence-anchor LLM extraction

Status: in-progress

<!-- Course correction 2026-03-24: hybrid retrieval (dense + BM25 + RRF) and sentence-anchor extraction from structured macro->micro context, with lexical segment resolution. -->

## Story

As a user,
I want semantic search to match my query using enough spoken context while still jumping to a precise timestamp,
So that results feel relevant and trustworthy, not arbitrary or over-confident.

## Acceptance Criteria

1. **Macro + micro persistence:** Given a video completes ingestion successfully, when transcript segments are indexed for search, then the system persists **macro-level** units with **word-like** configurable target size (primary: **words**; **tokens** acceptable if documented and close to words) with embeddings for **phase-1** macro matching; and **micro-level** units preserve timestamp boundaries with a clear macro→micro mapping.

2. **Hybrid macro retrieval:** Given a query, when phase-1 runs, then the system runs both dense semantic retrieval and BM25 lexical retrieval on `macro_text_content`, then fuses rankings with RRF (`k=60` default) to produce a top macro candidate list.

3. **Structured context packaging (LLM input):** Given fused top macros, when context is prepared for the LLM, then the backend serializes macro->micro JSON that includes micro ids, `start`, `end`, and text snippets for deterministic timestamp selection.

4. **Sentence-anchor extraction (Mistral plain-text output):** Given the structured context, when phase-2 runs, then the **Mistral chat** model applies quote-vs-scene guidance and returns a short sentence anchor from provided context as **plain text** (quote-matching sentence for quote intent, scene-start sentence for scene intent), **not as structured JSON**; backend lexical resolution maps it to the final micro segment/timestamp, and no secondary anchor re-vectorization loop is used for the final selector.

5. **Trustworthy match feedback (UX):** Given a successful search response, when the UI communicates match quality, then it does **not** rely on misleading **numeric percentages**; it uses **tiered** or **relative** feedback per UX spec.

6. **Stack constraints:** Dense retrieval uses **PostgreSQL + pgvector** + **cosine** on normalized Mistral embeddings; lexical retrieval uses BM25 on macro text; final extraction uses **Mistral** chat only.

7. **Configuration:** **Macro word-like target**, macro context top-K, and **RRF** constant (plus any hybrid retrieval tuning knobs) are **environment-backed** and documented in architecture + `.env.example`.

8. **Macro context + fine highlight (UI):** Given a successful search, when the primary page shows the excerpt, then it shows **full macro** text with the **micro** span **highlighted** inside it.

## Tasks / Subtasks

### Done (baseline — pre course correction)

- [x] Schema & migration for `transcript_macro_segments`
- [x] Ingestion: macro groups + embeddings (char-based target in first iteration)
- [x] Search: macro top-N + fine micro without LLM
- [x] Frontend: macro block + highlight + tier labels
- [x] Tests: grouping, search plumbing

### Remaining (course correction 2026-03-24)

- [x] **Macro grouping:** Switch or add **word**-like target (configurable **words**; document token option); align `macro_grouping` + ingestion with PRD.
- [x] **Hybrid retrieval:** Implement dense + BM25 retrieval at macro level and RRF fusion (`k=60` default), with clear top-K packaging rules.
- [x] **Structured context:** Build stable macro->micro JSON payload contract for LLM consumption (ids, timestamps, text).
- [ ] **Mistral extraction path:** Enforce plain-text sentence-anchor output parsing/validation (no JSON-output contract) and deterministic fallback behavior.
- [ ] **Search pipeline:** Query -> hybrid retrieval -> context packaging -> LLM sentence-anchor extraction -> lexical segment resolution -> API response mapping (`start_ts` compatibility).
- [x] **Config / `.env.example`:** keep `TRANSCRIPT_MACRO_TARGET_WORDS` (or equivalent), add/update hybrid knobs (`SEARCH_MACRO_TOP_K`, `SEARCH_RRF_K`, BM25-related settings), and extractor model/tokens vars.
- [ ] **Tests:** Add/adjust tests for dense+BM25 fusion behavior, top-K context packaging, and plain-text sentence-anchor output validation plus lexical-resolution fallback.
- [x] **UX:** Confirm **Searching…** remains acceptable if LLM adds latency; French copy unchanged in principle.

## Dev Notes

### Course correction reference

- **`_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-24.md`**
- Updated: `prd.md`, `architecture.md`, `epics.md`, `ux-design-specification.md`

### Previous implementation notes (still useful)

- Macro table, existing dense retrieval, and current env wiring remain reusable; extend with BM25 + RRF + sentence-anchor extraction and lexical resolution.

## References

- `_bmad-output/planning-artifacts/epics.md` (Story 3.3)
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`

## Dev Agent Record

### Agent Model Used

Cursor agent (implementation pass 2026-03-23)

### Implementation Plan

- **Macro grouping:** `group_micros_into_macros_by_words` + `count_words`; ingestion uses `TRANSCRIPT_MACRO_TARGET_MODE` (`words` default, `chars` optional).
- **Search:** Hybrid macro retrieval (dense + BM25), RRF fusion, structured context payload (LLM input), then Mistral plain-text sentence-anchor extraction (LLM output) followed by lexical segment/timestamp resolution.
- **Config:** Env-backed settings for macro target size, context top-K, and RRF constant; keep compatibility aliases only if required by existing deployments.

### Completion Notes List

- **Armand:** Story **3.3** is reopened for the latest correction: align implementation to hybrid macro retrieval (dense + BM25 + RRF) and sentence-anchor LLM extraction for both quote and scene intents while preserving macro/micro trust UI behavior.
- **Dev Agent (2026-03-24):** Updated story contract to explicit hybrid retrieval + structured macro->micro JSON as LLM input and plain-text sentence-anchor as LLM output; implementation remains in progress for sentence-anchor extraction path and related tests.
- **Dev Agent (2026-03-24):** Implemented plain-text sentence-anchor extraction path and lexical segment resolution fallback in search pipeline; added/updated unit tests for plain-text anchor parsing and anchor-to-micro lexical matching.
- **Dev Agent (2026-03-24):** Validation blocked in this runtime because `pytest` is unavailable both on host and in the current API container image; tasks remain unchecked pending executable test environment.

### Change Log

- 2026-03-24: Course correction — docs updated; story reopened **in-progress** for hybrid retrieval + sentence-anchor extraction and lexical resolution.
- 2026-03-24: Story contract clarified (JSON as LLM input, plain-text sentence-anchor as LLM output); sentence-anchor implementation path and tests remain open; status set to **in-progress**.
- 2026-03-24: Added plain-text sentence-anchor extraction + lexical micro resolution in `search_service`; updated unit tests for new extraction contract and fallback behavior; test execution currently blocked by missing `pytest` runtime.
- 2026-03-23: Implemented LLM anchor + adaptive macro filtering + word macro targets; documented env vars; added tests.

### File List

- `backend/app/services/macro_grouping.py`
- `backend/app/config.py`
- `backend/app/services/ingestion_service.py`
- `backend/app/services/mistral_client.py`
- `backend/app/services/search_service.py`
- `backend/tests/test_macro_grouping.py`
- `backend/tests/test_search_adaptive.py`
- `backend/tests/test_search_anchor_llm.py`
- `.env.example`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/implementation-artifacts/3-3-multi-scale-transcript-indexing-with-hybrid-macro-retrieval-and-direct-llm-timestamp-extraction.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
