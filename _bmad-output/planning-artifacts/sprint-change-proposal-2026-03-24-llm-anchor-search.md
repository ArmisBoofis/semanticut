# Sprint Change Proposal — semanticut (search strategy refinement)

**Date:** 2026-03-24  
**Author:** Correct Course (PM / SM alignment)  
**Recipient:** Armand  
**Mode:** Batch  
**Output language:** English (per `document_output_language`)

**Supersedes / extends:** [Sprint Change Proposal 2026-03-23](sprint-change-proposal-2026-03-23.md) (multi-scale indexing + two-pass search). Implementation of Story **3.3** is in **review**; retrieval quality feedback motivates a **strategy refinement** without removing macro/micro embeddings.

---

## Section 1: Issue Summary

### Problem statement

Testing of search (post Story **3.2** / **3.3**) shows that **coarse macro → fine micro vector match** alone is **not satisfying enough**: a single winning macro is too brittle, and **quote-like** vs **vague scene-like** queries need **different landing behavior** (precise line vs coherent scene start). Numeric similarity on short spans remains a weak trust signal.

### Desired outcome

Keep **macro** and **micro** segments **with embeddings**, but change the **search orchestration**:

1. **Embed** the user query → **rank macro segments** → retain an **adaptively filtered** set of macros (**up to K_max**), **excluding** candidates that are **clearly irrelevant** by score / gap rules (not “always exactly K”).
2. Pass the **text** covered by those macros to a **Mistral LLM** with a **prompt engineered** to:
   - Treat **scene** as the **default** when the query is **vague** and does **not** target a specific sentence word-for-word (seek a **natural** anchor—often the **start** of the relevant moment or a **representative** sentence).
   - Treat **quote** when the user **targets exact wording** (anchor the **precise** sentence/phrase).
   - **Reject** or flag when provided chunks are **not** good enough to answer (complements adaptive macro filtering).
3. From the LLM output, take a **verbatim** anchor string (from supplied text only), **embed** it, then run **vector search on micro segments** **restricted** to micro rows under the **retained** macro(s), and **snap** playback to the winning micro segment.

**Configuration (environment):** **macro chunking** target in **word**-like units (words or tokenizer units close to words), and **K_max** (maximum macros after phase 1), plus **documented** thresholds for **adaptive** filtering.

### Context

- **Triggering work:** Story **3.3** — *Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction* (status **review** at time of change).
- **Issue type:** **Technical / product refinement** during implementation validation — not a scope cut.
- **Stack:** Still **Mistral-only** for embeddings and LLM; **PostgreSQL + pgvector** for vector stages.

---

## Section 2: Impact Analysis

### Epic impact

| Area | Assessment |
|------|------------|
| **Epic 3** | Remains the locus of search behavior. Story **3.3** **scope expands** (LLM step + adaptive K + word-based macro tuning); **3.4** / **3.5** stay valid as **QA / acceptance** for quote vs scene behavior, now **aligned** with the LLM intent layer. |
| **Epic 2** | Ingestion still owns macro/micro build; **macro grouping** switches emphasis to **word**-like targets (see architecture). |
| **Epic 4** | **4.1** (search loading) should assume **slightly longer** “searching” windows (embedding + LLM + second embedding); copy may mention **active** analysis without exposing internals. |

### Story impact

| Story | Change |
|-------|--------|
| **3.3** | **Not done** until LLM anchor + adaptive K + env knobs are implemented and accepted; **review → in-progress** until then. |
| **3.4** | **Clarified:** quote precision is driven by **LLM “quote” intent** + micro search from **anchor embedding**, plus existing ±5s demo criteria. |
| **3.5** | **Clarified:** **scene** = **default vague** query path in the LLM; coherent start / boundaries as in PRD. |

### Artifact conflicts resolved

| Artifact | Action |
|----------|--------|
| **PRD** | MVP search bullet updated to describe **LLM-assisted anchor** + **adaptive K**. |
| **Architecture** | Search pipeline, **env** parameters, optional **response** hints (`match_quality`, future `no_match` from LLM). |
| **Epics** | Story **3.3** acceptance criteria rewritten. |
| **UX** | Core loop notes: search wait may include **LLM**; trust still **macro + highlight**, not raw %. |
| **Implementation story 3.3** | Tasks appended for LLM, adaptive logic, word-based macro config. |

---

## Section 3: Recommended Approach

**Path:** **Direct adjustment** — extend **3.3** implementation; **no rollback** of macro/micro schema; **re-tune** prompts and thresholds in testing.

| Dimension | Notes |
|-----------|--------|
| **Effort** | **Medium** — new Mistral **chat** path, prompt versioning, adaptive K logic, tests. |
| **Risk** | **Medium** — LLM latency and **verbatim** enforcement; mitigate with **structured output** and **no-match** handling. |
| **Privacy / data** | Transcript text sent to Mistral **as already** for transcription/embeddings; document in reviewer notes if needed. |

---

## Section 4: Checklist

| Item | Status |
|------|--------|
| PRD updated | [x] |
| Architecture updated | [x] |
| Epics Story 3.3 updated | [x] |
| UX spec updated | [x] |
| Implementation story 3.3 updated | [x] |
| `sprint-status.yaml` (3.3 → in-progress) | [x] |

---

## Section 5: Approval

**Status:** **Documents synced** — **Armand** may mark **approved** when satisfied.

**Next implementation steps:** Implement LLM anchor step + adaptive macro selection + micro restricted search; keep **French** UI and **tiered** match feedback; document **env** in `.env.example` and `architecture.md`.
