# Sprint Change Proposal — semanticut

**Date:** 2026-03-23  
**Author:** Correct Course workflow (Scrum Master)  
**Recipient:** Armand  
**Mode:** Batch  
**Output language:** English (per `document_output_language`)

---

## Section 1: Issue Summary

### Problem statement

After implementing **Story 3.2** (natural-language search → best-matching segment), **semantic retrieval quality** does not meet the intent of the PRD and epics: **relevance scores cluster at high values** (e.g. ~83% for queries that are not a good semantic match), and **ASR-sized segments are often too short** for embedding models to encode enough context. That undermines **trust** and makes **FR3 / FR4** (meaningful jump, scene coherence) hard to satisfy with a **single-pass** nearest-neighbor on micro-segments alone.

The product still needs **precise timestamps** (short segments are good for seek accuracy); the gap is **context for matching**, not timestamp granularity.

### Context and discovery

- **Triggering story:** 3.2 — Natural-language search returns best-matching segment (`3-2-natural-language-search-returns-best-matching-segment`, status: **review**).  
- **When / how:** Post-implementation review with real video (e.g. French speech); query vs snippet mismatch with **misleading confidence**.  
- **Issue type:** **Technical limitation discovered during implementation** — short segments + naive confidence mapping; **not** a stakeholder scope change.  
- **Evidence:**  
  - Example: query **“ananas”** returned an unrelated clause with **high displayed relevance**.  
  - Backend maps cosine distance to `confidence` with a linear formula; short texts produce **weakly discriminative** embeddings in high dimensions.  
  - Ingestion uses **one embedding per Mistral ASR segment** (`ingestion_service`); no **macro** layer for coarse search.

---

## Section 2: Impact Analysis

### Epic impact

| Area | Assessment |
|------|------------|
| **Epic 3** | Still the right home for **search UX and seek**. **New story 3.3** added for **multi-scale indexing + two-pass search + calibrated feedback**. Former stories **3.3 / 3.4** renumbered to **3.4 / 3.5** (quote-precision and scene coherence). |
| **Epic 2** | **No new epic.** Ingestion **already** owns chunking/embedding (`Story 2.4`); macro/micro persistence extends that pipeline — implement as part of **3.3** or coordinate in the same sprint (same PR). |
| **Epic 4** | Unchanged. Polish stories remain; **3.3** may **reduce** duplicate work if **4.2** assumed “good” snippets (clarify during implementation). |

### Story impact

| Story | Change |
|-------|--------|
| **3.2** | Remains **valid** as **wiring + contract** (search endpoint, UI, player). **Review** can close as **done** once PO accepts wiring; **quality bar** is explicitly **Story 3.3**. |
| **3.3** (new) | **Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction** — **backlog**, should be **next** in Epic 3 after 3.2 acceptance. |
| **3.4 / 3.5** (was 3.3 / 3.4) | **Depend on 3.3** for meaningful ±5s / scene tests; keep **backlog** until 3.3 is done or document **known limitations** in demo notes. |

### Artifact conflicts

| Artifact | Conflict? | Action |
|----------|------------|--------|
| **PRD** | Gap between “retrieval quality” promise and single-pass micro search | **Updated:** MVP bullet clarifies **multi-scale** (macro context, micro timestamps). |
| **Epics** | Missing story for hierarchical retrieval | **Updated:** New **Story 3.3**; **Quote / Scene** renumbered to **3.4 / 3.5**. |
| **Architecture** | Schema and cross-cutting chunking | **Updated:** `transcript_macro_segments` (or equivalent), two-pass retrieval note, cosine default. |
| **UX** | “No raw scores” vs UI showing **%** | **Updated:** prefer **tiers / relative** cues over misleading **percentages**. |
| **CI/CD, IaC** | None | **N/A** unless new migration volume triggers CI timeouts (unlikely). |

### Technical impact

- **Database:** New table (or columns) for **macro** segments + **FK** from micro segments; **Alembic** migration; **re-ingest** or migration path for existing videos.  
- **Backend:** `ingestion_service` builds macro units; `search_service` **coarse → fine** query; optional **confidence** schema change (float + `match_tier` enum or document tier mapping).  
- **Frontend:** Replace or supplement **“Pertinence: NN %”** with **tiered** or **relative** copy per UX.  
- **Stack:** **pgvector + cosine distance** retained unless evaluation says otherwise (per architecture).

---

## Section 3: Recommended Approach

### Selected path: **Direct adjustment (Option 1)**

Add **Story 3.3** and **align** PRD / architecture / UX. **No rollback** of 3.2 code unless you choose to strip features (not recommended). **No MVP rescoping** — this **fulfills** the original FR3/FR4 intent.

| Option | Verdict | Notes |
|--------|---------|--------|
| **1 — Direct adjustment** | **Recommended** | Implements **macro + micro** two-pass search; fixes confidence **presentation**; moderate effort. |
| **2 — Rollback** | **Not viable** | Would discard working **search → seek** loop without fixing embeddings. |
| **3 — MVP review** | **Not needed** | MVP remains achievable; this is **core** POC value. |

### Effort, risk, timeline

- **Effort:** **Medium** (schema + ingestion + search + UI copy).  
- **Risk:** **Medium** — re-ingest for demo videos; tune macro size and top-N.  
- **Timeline:** **One sprint slice** for POC; quote/scene stories **3.4 / 3.5** follow.

---

## Section 4: Detailed Change Proposals

### Epics (`epics.md`)

- **Inserted** **Story 3.3: Multi-scale transcript indexing with hybrid macro retrieval and direct LLM timestamp extraction** (full AC in file).
- **Renumbered** former **3.3 → 3.4** (quote-precise), **3.4 → 3.5** (scene-coherent).

### PRD (`prd.md`)

- **MVP — Search + jump:** Clarified **multi-scale** indexing (macro semantic match, micro precise seek).
- **MVP — Result presentation:** Macro **context** on screen with the **fine / micro** span **highlighted** inside it; trust from **context + span**, not a misleading **%** alone.

### Architecture (`architecture.md`)

- **Data architecture:** `transcript_macro_segments` (or equivalent), micro `transcript_segments`, embeddings on both; **cosine** default.  
- **Cross-cutting:** Multi-scale indexing called out explicitly.
- **Search API:** Response includes **`macro_context_text`** and **offsets** (or equivalent) for the fine span so the UI can render **macro + highlight** without ambiguous client-side substring logic.

### UX (`ux-design-specification.md`)

- **Low confidence / scores:** Prefer **tiered** or **relative** cues over **numeric percentages** that imply false precision.
- **JumpFeedback / result:** After a match, show **full macro** transcript with **micro** span **highlighted**; **core loop** diagram updated to reflect this trust pattern.

### Sprint tracking (`sprint-status.yaml`)

- Added: `3-3-multi-scale-transcript-indexing-with-hybrid-macro-retrieval-and-direct-llm-timestamp-extraction: backlog`
- Renamed keys: `3-4-quote-...`, `3-5-scene-...` (former 3-3 / 3-4).

---

## Section 5: Implementation Handoff

| Classification | **Moderate** |
|----------------|--------------|
| **Rationale** | Touches **ingestion + search + DB + UI**; backlog and story order updated. |
| **Primary owner** | **Development** (implementation), **PO/SM** (accept 3.2, prioritize 3.3). |
| **Architect** | Optional review of **macro sizing** and **migration** strategy. |

### Success criteria

- [ ] Macro + micro rows persisted for newly ingested videos; path for existing DBs defined.  
- [ ] Search uses **two-pass** retrieval within p95 latency budget (informal).  
- [ ] UI does not present **misleading** high **%** for weak matches.  
- [ ] Primary search result shows **macro** context with **fine** span **highlighted** (per UX + PRD).  
- [ ] Planning artifacts (`epics`, PRD, architecture, UX, sprint-status) stay **consistent**.

---

## Section 6: Checklist execution log

| Section | Status |
|---------|--------|
| **1 — Trigger & context** | [x] Done — Story 3.2, technical limitation, evidence recorded |
| **2 — Epic impact** | [x] Done — Epic 3 extended; 3.4/3.5 renumbered |
| **3 — Artifacts** | [x] Done — PRD, architecture, UX updated |
| **4 — Path forward** | [x] Done — Option 1 selected |
| **5 — Proposal components** | [x] Done — This document |
| **6 — Final review** | [x] Done — `sprint-status.yaml` updated (checklist 6.4) |

---

## Approval

**Status:** **Approved** by Armand on **2026-03-23**.  
**Scope classification:** Moderate — backlog priority **3.3** next; coordinate ingestion + search + UI copy in implementation.

**Correct Course workflow complete, Armand.**

Next steps: **Accept or adjust Story 3.2** in review; pull **3.3** into **ready-for-dev**; implement multi-scale indexing and two-pass search before treating **3.4 / 3.5** as fully testable.

**Update (2026-03-24):** Further refinement — **LLM anchor selection**, **adaptive K**, **word-like** macro sizing — see [`sprint-change-proposal-2026-03-24-llm-anchor-search.md`](sprint-change-proposal-2026-03-24-llm-anchor-search.md).
