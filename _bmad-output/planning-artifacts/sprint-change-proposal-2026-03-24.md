# Sprint Change Proposal - Hybrid Macro Retrieval + Direct Timestamp Extraction

**Date:** 2026-03-24  
**Project:** semanticut  
**Trigger Story:** 3.3 - Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction  
**Mode:** Batch

## 1) Issue Summary

The current search pipeline uses a two-pass retrieval loop:
1) vector search over macro segments,
2) LLM anchor sentence generation,
3) re-embedding anchor,
4) micro vector search for final timestamp.

This approach introduces avoidable latency/complexity and weak lexical recall for exact names/acronyms. The requested correction is:
- replace macro retrieval with **Hybrid Search** (Dense + BM25 + RRF),
- pass structured macro->micro JSON context directly to the LLM,
- remove the secondary re-vectorization loop as decision logic,
- return a **single float timestamp** (`start`) as final output.

Evidence / constraints:
- PRD and Architecture currently describe a two-pass anchor-to-micro pattern.
- Story 3.3 currently encodes that same pattern in acceptance criteria.
- Existing implementation artifacts already indicate active work around macro/micro and anchor search, making this the right point to adjust before Epic 3 completion.

## 2) Impact Analysis

### Epic Impact

- **Epic 3** remains valid and in-progress.
- **Story 3.3** requires acceptance-criteria changes (core behavior change).
- **Stories 3.4 and 3.5** remain valid but should reference the new direct timestamp extraction behavior.
- No new epic required.

### Story Impact

- **Immediate:** Story 3.3 (major AC update).
- **Downstream alignment:** Story 3.4 and 3.5 (clarify dependency wording).
- **No impact:** Epics 1, 2, and Epic 4 story intent remain unchanged.

### Artifact Conflicts

- **PRD conflict:** MVP search pipeline description currently includes anchor re-embedding + micro vector stage as mandatory final selector.
- **Architecture conflict:** `/search` flow currently documents macro shortlist -> LLM verbatim anchor -> anchor embedding -> scoped micro vector search as the final retrieval logic.
- **UX conflict (minor):** search feedback text implies a two-pass micro-refinement mental model; should be reframed to context-based extraction and deterministic timestamp output.

### Technical Impact

- Backend search service logic must support:
  - BM25 lexical retrieval over `macro_text_content`,
  - Dense retrieval over same macro searchable text,
  - RRF fusion (`k=60` default),
  - Top-10 macro context packaging as structured JSON with child micro segments,
  - strict timestamp-only LLM output contract.
- Data model alignment needed for parent-child macro/micro schema guarantees.
- API response contract should keep `start_ts` compatibility while internally consuming single-float extractor output.

## 3) Recommended Approach

**Selected approach:** Option 1 - Direct Adjustment (Moderate scope)

Why this is the best path:
- Preserves MVP goal and current epic structure.
- Aligns better with latency target by removing an extra retrieval loop.
- Improves recall on proper nouns/jargon via lexical BM25.
- Fits current implementation trajectory without rollback.

Effort / risk / timeline:
- **Effort:** Medium
- **Risk:** Medium (prompt robustness + score-fusion tuning)
- **Timeline impact:** Low-to-moderate (primarily Story 3.3 rework and validation)

Alternatives considered:
- **Option 2 (Rollback):** Not justified; existing progress remains reusable.
- **Option 3 (MVP review/reduction):** Not needed; this is a refinement of retrieval strategy, not scope inflation.

## 4) Detailed Change Proposals

### A) Story Changes (Epics)

#### Story: 3.3 - Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction  
**Section:** Title + Acceptance Criteria

**OLD (intent):**
- Two-pass semantic search with LLM anchor generation, anchor re-embedding, then scoped micro vector search.

**NEW (proposed):**
- Rename story to: **"Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction"**
- Replace retrieval ACs with:
  1. Macro segments persist structured parent-child data (`macro_text_content`, `micro_segments[{micro_id,start,end,text}]`).
  2. Query handling uses hybrid retrieval at macro-level:
     - Dense embedding search on `macro_text_content`,
     - BM25 lexical search on `macro_text_content`,
     - RRF fusion with `score = 1/(rank_dense + k) + 1/(rank_bm25 + k)`, `k=60` default.
  3. Top 10 fused macros are serialized into JSON context containing micro segment `start` + `text` (and ids).
  4. LLM outputs only the exact float `start` timestamp of the best micro segment.
  5. Search pipeline returns a final seek timestamp from that float without secondary semantic retrieval loop.

**Rationale:**
- Meets objective (faster, simpler, lexically robust retrieval) while preserving macro/micro design value.

---

#### Story: 3.4 - Quote-precise seeking for exact-phrase queries  
**Section:** Dependency note

**OLD:**
- Depends on two-pass anchor->micro retrieval behavior.

**NEW:**
- Depends on hybrid macro retrieval + direct timestamp extraction behavior from structured context.

**Rationale:**
- Keeps quote-precision goal while matching the corrected Story 3.3 mechanism.

---

#### Story: 3.5 - Scene-coherent seeking for vague queries  
**Section:** Dependency note

**OLD:**
- Depends on two-pass anchor->micro retrieval behavior.

**NEW:**
- Depends on hybrid macro retrieval + direct timestamp extraction behavior from structured context, with scene-coherent prompt instructions.

**Rationale:**
- Keeps scene-coherence objective while aligning to the new extraction path.

### B) PRD Modifications

#### File: `prd.md`  
**Section:** MVP search pipeline description

**OLD:**
- Macro ranking -> LLM anchor -> anchor embedding -> scoped micro vector search.

**NEW:**
- Hybrid macro retrieval (Dense + BM25 + RRF) -> top-K structured macro context -> LLM direct timestamp extraction (`start` float).
- Explicitly state: no secondary anchor re-vectorization loop in the final decision path.

**MVP impact:** No scope increase; quality/performance optimization within existing MVP.

### C) Architecture Modifications

#### File: `architecture.md`  
**Sections:** Data Architecture, API/Search flow, Search configuration

**OLD:**
- Two-pass semantic retrieval centered on anchor re-embedding over micro vectors.

**NEW:**
- Parent-child macro schema explicitly includes child micro segments with timestamps and text.
- Search flow:
  - dense macro retrieval,
  - BM25 macro retrieval,
  - RRF fusion,
  - top-10 context JSON,
  - strict timestamp-only LLM output.
- Config additions/clarifications:
  - RRF constant (`k`, default 60),
  - macro top-K default 10 for LLM context packaging,
  - BM25 index/search configuration notes.

**Ripple effects:**
- Search service contracts and tests update.
- Potential migration/index changes for lexical retrieval performance.

### D) UX Specification Modifications

#### File: `ux-design-specification.md`  
**Section:** Search feedback / trust communication

**OLD:**
- Emphasizes multi-stage micro refinement narrative.

**NEW:**
- Emphasize deterministic behavior: user query -> relevant context inspection -> direct timestamp extraction.
- Keep user-facing confidence communication non-numeric and concise.

**Rationale:**
- Avoid over-explaining backend stages while preserving trust and clarity.

## 5) Checklist Execution Record

### Section 1 - Trigger and Context
- **1.1** [x] Done - Trigger story identified (3.3)
- **1.2** [x] Done - Problem: failed/inefficient retrieval approach refinement
- **1.3** [x] Done - Evidence recorded from current PRD/Architecture/Epics mismatch with requested pipeline

### Section 2 - Epic Impact
- **2.1** [x] Done - Current epic still viable
- **2.2** [x] Done - Story-level modifications required
- **2.3** [x] Done - Future epic dependency review completed
- **2.4** [N/A] Skip - No new/obsolete epics required
- **2.5** [!] Action-needed - Reconfirm story sequencing after 3.3 update in sprint-status

### Section 3 - Artifact Conflicts
- **3.1** [x] Done - PRD conflict identified
- **3.2** [x] Done - Architecture conflict identified
- **3.3** [x] Done - UX wording alignment needed
- **3.4** [x] Done - Tests/docs pipeline notes impacted

### Section 4 - Path Forward
- **4.1** [x] Viable - Direct adjustment
- **4.2** [ ] Not viable - Rollback unnecessary
- **4.3** [ ] Not viable - MVP reduction unnecessary
- **4.4** [x] Done - Option 1 selected

### Section 5 - Proposal Components
- **5.1** [x] Done
- **5.2** [x] Done
- **5.3** [x] Done
- **5.4** [x] Done
- **5.5** [x] Done

### Section 6 - Final Review Readiness
- **6.1** [x] Done
- **6.2** [x] Done
- **6.3** [!] Action-needed - Pending explicit user approval
- **6.4** [!] Action-needed - Update `sprint-status.yaml` only after approval
- **6.5** [!] Action-needed - Confirm handoff and ownership after approval

## 6) Implementation Handoff

**Scope classification:** Moderate

### Handoff recipients and responsibilities

- **Development team**
  - Implement hybrid retrieval + direct timestamp extraction.
  - Ensure strict output parsing/validation for float-only LLM response.
  - Maintain API compatibility for frontend seek behavior.

- **Product Owner / Scrum Master**
  - Update Story 3.3/3.4/3.5 wording and acceptance criteria in epic artifacts.
  - Reconfirm sprint sequencing and status progression after merge.

- **QA**
  - Add/adjust tests for:
    - dense+BM25 fusion ranking behavior,
    - timestamp-only output validation,
    - quote/vague query benchmark behavior.

### Success criteria for implementation

1. Hybrid retrieval active with RRF fusion over macro candidates.
2. Top-10 macro structured context reaches LLM as JSON.
3. LLM returns parsable single float timestamp.
4. End-to-end search result seeks correctly without secondary re-vectorization loop.
5. Story docs and sprint tracking reflect approved corrected behavior.

---

## Review Gate

Please review this proposal and respond with:
- **Continue [c]** to proceed to approval gate, or
- **Edit [e]** to request changes in this proposal.
