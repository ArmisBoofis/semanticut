# Sprint Change Proposal - Quote-First Lexical Anchor for Precise Seeking

**Date:** 2026-03-24  
**Project:** semanticut  
**Trigger Story:** 3.4 - Quote-precise seeking for exact-phrase queries  
**Mode:** Batch  
**Goal Priority:** Preserve broader semantic recall first

## 1) Issue Summary

The current direct timestamp extraction path can return a timestamp that lands at the **end** of the relevant sentence. When that timestamp is mapped to the nearest segment boundary, playback may jump to the segment **after** the intended quote.

The proposed correction for quote-like queries is to switch the LLM output contract from numeric timestamp to a **verbatim quote anchor** (short sentence/span), then resolve the final timestamp via lexical matching against transcript text.

Evidence:
- Observed behavior: timestamp drift to end-of-sentence causes off-by-one segment selection.
- Known model behavior: LLMs are typically less reliable on precise numeric extraction than on short textual spans.
- Product priority for this correction: keep broad semantic recall as primary, improve precision by changing final anchoring method.

## 2) Impact Analysis

### Epic Impact

- **Epic 3** remains valid and in-progress.
- **Story 3.4** is the primary impacted story (acceptance criteria + implementation notes).
- **Story 3.3** remains valid as the retrieval backbone; only phase-2 extraction contract is refined for quote-like paths.
- **Story 3.5** remains valid (scene behavior can keep timestamp path, or optionally adopt quote-anchor fallback later).
- No new epic required.

### Story Impact

- **Immediate:** Story 3.4 (core AC refinement for precision).
- **Adjacent:** Story 3.3 wording should clarify that extractor output can be contractually different by intent path (quote vs scene), while preserving one final `start_ts` output to API clients.
- **No impact:** Epics 1, 2, and Epic 4 intent remain unchanged.

### Artifact Conflicts

- **PRD conflict (minor):** language currently assumes timestamp-only extractor output in final path.
- **Architecture conflict (minor):** search flow documents strict float output from extractor without quote-anchor variant.
- **UX conflict (none/low):** UX remains compatible since user still receives one seek result and highlighted context.

### Technical Impact

- Update quote pipeline to:
  1. keep hybrid macro retrieval (dense + BM25 + RRF),
  2. ask LLM for quote anchor text (not number) for quote-like intent,
  3. run lexical resolution over candidate micro segments (or local neighborhood) to find best segment hit,
  4. set `start_ts` from matched segment start (or controlled fallback if no exact lexical hit).
- Keep scene path unchanged to preserve recall-oriented behavior and latency balance.
- Maintain API compatibility (`start_ts`, `end_ts`, text, macro context/highlight).

## 3) Recommended Approach

**Selected approach:** Option 1 - Direct Adjustment (Moderate scope)

Why this path:
- Addresses observed precision defect directly.
- Reduces dependence on brittle numeric extraction from LLM.
- Preserves current semantic retrieval strengths and broad recall.
- Limits blast radius: targeted change in extraction + resolution stage.

Effort / risk / timeline:
- **Effort:** Medium
- **Risk:** Medium (quote normalization, fuzzy lexical matching thresholds, fallback policy)
- **Timeline impact:** Low-to-moderate (localized search pipeline and tests update)

Alternatives considered:
- **Keep timestamp-only extraction and adjust post-processing window:** weaker, still vulnerable to numeric drift.
- **Full rollback to prior sentence-first architecture for all queries:** unnecessary; risks degrading scene behavior and changing too much at once.

## 4) Detailed Change Proposals

### A) Story Changes (Epics)

#### Story: 3.4 - Quote-precise seeking for exact-phrase queries  
**Section:** Acceptance Criteria + dependency note

**OLD (intent):**
- Quote precision depends on direct timestamp float extraction.

**NEW (proposed):**
- For quote-like intent, extractor returns **verbatim quote anchor text** (short sentence/span).
- Backend resolves final target segment using lexical matching over shortlisted micro segments.
- Final seek timestamp is derived from resolved segment start, with deterministic fallback to best semantic candidate when lexical confidence is insufficient.
- Keep ±5s target unchanged.

**Rationale:**
- More robust anchoring method for quote precision while preserving existing retrieval strengths.

---

#### Story: 3.3 - Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction  
**Section:** Acceptance Criteria (path clarification)

**OLD:**
- Extractor always returns strict float timestamp.

**NEW:**
- Clarify dual extraction contracts by intent:
  - **Quote-like:** return quote anchor text for lexical resolution.
  - **Scene-like (default):** return direct timestamp as currently implemented.
- API result remains normalized to final `start_ts`/`end_ts`.

**Rationale:**
- Keeps retrieval architecture stable while improving precision where the defect exists.

### B) PRD Modifications

#### File: `prd.md`  
**Section:** MVP search pipeline description

**OLD:**
- Final decision path described as timestamp-only extraction.

**NEW:**
- Add quote-path refinement: quote-like queries may use quote-anchor text + lexical segment resolution before final seek timestamp emission.
- Keep scene-default behavior and semantic recall commitments unchanged.

**MVP impact:** No scope increase; precision improvement within existing MVP goals.

### C) Architecture Modifications

#### File: `architecture.md`  
**Sections:** API/Search flow, extractor contract, fallback strategy

**OLD:**
- Single strict timestamp output contract for extractor.

**NEW:**
- Intent-aware extractor contract:
  - quote path -> anchor text output,
  - scene path -> timestamp output.
- Add lexical resolver stage for quote path (normalization + candidate scoring + fallback).
- Document deterministic fallback order and thresholding for no-hit/low-hit cases.

**Ripple effects:**
- Search service interfaces and parser validation logic.
- Additional tests for quote anchor matching and fallback consistency.

### D) UX Specification Modifications

#### File: `ux-design-specification.md`  
**Section:** Trust feedback patterns

**OLD:**
- Trust narrative centered on direct timestamp extraction.

**NEW:**
- Keep user-facing behavior unchanged; internally support quote-anchor lexical resolution for improved precision.
- Continue avoiding misleading numeric confidence percentages.

**Rationale:**
- No UX disruption needed; reliability improvement is mostly backend-facing.

## 5) Checklist Execution Record

### Section 1 - Trigger and Context
- **1.1** [x] Done - Trigger story identified (3.4, dependent on 3.3 pipeline)
- **1.2** [x] Done - Problem: timestamp drift to sentence end causes next-segment jumps
- **1.3** [x] Done - Evidence recorded from observed behavior and extractor limitations

### Section 2 - Epic Impact
- **2.1** [x] Done - Current epic remains viable
- **2.2** [x] Done - Story-level AC refinements required
- **2.3** [x] Done - Future epics unaffected
- **2.4** [N/A] Skip - No new/obsolete epics required
- **2.5** [x] Done - Epic order unchanged

### Section 3 - Artifact Conflicts
- **3.1** [x] Done - Minor PRD wording alignment needed
- **3.2** [x] Done - Minor architecture flow alignment needed
- **3.3** [N/A] Skip - No significant UX flow conflict
- **3.4** [x] Done - Tests/docs need updates

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
- **6.4** [!] Action-needed - Update sprint tracking artifacts after approval
- **6.5** [!] Action-needed - Confirm execution handoff after approval

## 6) Implementation Handoff

**Scope classification:** Moderate

### Handoff recipients and responsibilities

- **Development team**
  - Implement quote-anchor output path + lexical resolver in search pipeline.
  - Preserve scene-default timestamp path and API response compatibility.
  - Add deterministic fallback behavior for no lexical hit.

- **Product Owner / Scrum Master**
  - Update Story 3.4 (and clarifying note in 3.3) acceptance criteria in planning artifacts.
  - Reflect approved changes in sprint status tracking.

- **QA**
  - Add tests for:
    - quote-anchor extraction contract,
    - lexical matching robustness (exact + near match),
    - fallback behavior when quote anchor is absent or noisy.

### Success criteria for implementation

1. Quote-like queries resolve to intended segment without systematic next-segment drift.
2. Scene-style queries maintain current recall-oriented behavior.
3. API contract remains stable for frontend seek/play flow.
4. Precision on curated quote set improves or remains within ±5s target with fewer off-by-one jumps.
5. Planning and sprint artifacts reflect approved correction.

---

## Review Gate

Please review this proposal and respond with:
- **Continue [c]** to proceed to approval gate, or
- **Edit [e]** to request changes.
