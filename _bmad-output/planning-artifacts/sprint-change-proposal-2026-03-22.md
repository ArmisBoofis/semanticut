# Sprint Change Proposal — semanticut

**Date:** 2026-03-22  
**Author:** Course Correction workflow (PM agent)  
**Recipient:** Armand  
**Mode:** Batch  
**Output language:** English (per `document_output_language`)

---

## Section 1: Issue Summary

### Problem statement

After marking **Story 2.1** (Admin can register videos for ingestion) as done, it became clear there was **no planned or implemented admin UI** to register videos: **registration is only possible via the API** (for example `POST /videos`). The **epics document** defines Story 2.1 acceptance criteria exclusively in terms of **API behavior**, so the implementation can be fully correct while still **failing an implicit expectation** that an admin would register videos through the **admin panel**.

### Context and discovery

- **Triggering story:** 2.1 — Admin can register videos for ingestion (`2-1-admin-can-register-videos-for-ingestion`, status: done).  
- **When / how:** Post-implementation review; expectation of an **upload / registration form** on the admin surface was not met.  
- **Evidence:**  
  - `epics.md` Story 2.1 AC: “When **I call an API endpoint** such as `POST /videos`…” — no AC for browser-based registration.  
  - `sprint-status.yaml`: 2.1 is **done**; Epic 2 is **in-progress** (2.2 in **review**).  
  - Architecture references `POST /videos` with uploaded file or path; **no conflict** with adding a UI that calls the same contract.

### Issue type (checklist 1.2)

**Primary:** *Misalignment between stakeholder expectation and written story scope* (implicit “admin panel upload” vs explicit “API-only” AC).  
**Secondary:** *UX / planning gap* — admin registration flow is less explicitly specified than the primary-page “select or upload” narrative in the UX spec.

---

## Section 2: Impact Analysis

### Epic impact

| Area | Assessment |
|------|------------|
| **Epic 2** | Still completable as planned. **Add one new story** for admin UI registration (upload form + wiring to existing API). No epic removal or redefinition. |
| **Story 2.1** | **Done** as written (API). **Do not reopen** unless you explicitly want AC rewritten for audit; optional **note** in epic that “API-only” was intentional in 2.1 and UI is covered by the new story. |
| **Story 2.2** (admin list, in review) | **Optional coordination:** if the admin page is being built now, **adding the upload section in the same layout** may reduce churn; otherwise the new story is a **follow-up** on the same route. |
| **Later epics (3, 4)** | **No structural change.** Epic 4 Story 4.4 (admin ingestion UI clarity) remains complementary; upload form **feeds** the same ingestion pipeline. |

### Story impact

- **New work:** One story (recommended ID: **2.5** in `epics.md`, slug `2-5-admin-can-register-videos-via-admin-ui`) — see Section 4.  
- **No rollback** of 2.1 required.

### Artifact conflicts

| Artifact | Conflict? | Action |
|----------|-------------|--------|
| **PRD** | None on goals | **Minor addition** under MVP / reviewer path: admin can register a video **without using curl** (supports NFR6 time-to-first-success). |
| **Epics** | Gap only | **Add Story 2.5**; optionally **one line** in Epic 2 blurb: register via **admin UI** as well as API. |
| **Architecture** | None | Already allows file upload via `POST /videos`. Document **multipart vs JSON** in implementation if not already fixed. |
| **UX** | Gap on admin surface | **Add** a short **Admin — register video** subsection: French UI, file input, label, submit, errors, loading — aligned with existing patterns (`IngestStatusPanel`, secondary buttons). |

### Technical impact

- **Frontend:** New form + client call to existing API (extend client if only raw `fetch` to `POST /videos` exists).  
- **Backend:** Only if API currently **does not** accept browser-friendly multipart upload from admin UI — then align contract once; otherwise **no** backend change.  
- **CI/CD / IaC:** N/A unless new env vars needed.

---

## Section 3: Recommended Approach

### Selected path: **Direct adjustment (Option 1)**

Add **one new story** and **light** PRD/UX/epic touch-ups. **No rollback.** **No MVP rescoping.**

| Option | Verdict | Notes |
|--------|---------|--------|
| **1 — Direct adjustment** | **Recommended** | Low effort, low risk; preserves completed 2.1; matches “not such a major change.” |
| **2 — Rollback** | **Not viable** | API implementation is the right foundation; reverting adds cost without benefit. |
| **3 — MVP review** | **Not needed** | MVP remains achievable; this closes a **delivery gap**, not a strategy change. |

### Effort, risk, timeline

- **Effort:** **Low–medium** (single feature slice: admin upload UI + validation + French strings).  
- **Risk:** **Low** (reuses API; main risks are file size, error handling, and CORS/multipart if any).  
- **Timeline:** **Small** slip if 2.2 is frozen without upload — otherwise bundle with admin page work.

### Scope classification

**Minor** — Development can implement directly from the new story + UX notes; **optional** PO/SM pass to order backlog (2.5 vs 2.2 follow-up).

---

## Section 4: Detailed Change Proposals

### 4.1 New story (Epics + sprint tracking)

**Story ID:** 2.5 (insert in `epics.md` after Story 2.4, before Epic 3)

**Title:** Admin can register videos via upload form on the admin page

**User story:**  
As an **admin**,  
I want to **register a new video for ingestion using an upload form on the admin page**,  
So that I can **run the demo without calling the HTTP API manually**.

**Acceptance criteria (draft):**

**Given** the stack is running and I am on the **admin** page  
**When** I choose a video file (and provide required fields such as **label**, if required by the API) and submit the form  
**Then** the client calls the same registration flow as Story 2.1 (e.g. `POST /videos` with the agreed payload — multipart or JSON per architecture)  
**And** I see **loading** and **success or structured error** feedback (`{ "error": { code, message } }`) in the UI.

**Given** I submit invalid or unsupported input  
**When** the API returns an error  
**Then** the admin UI shows a **clear message** without raw stack traces.

**Given** a video is registered successfully  
**When** I view the admin list (Story 2.2)  
**Then** the new video appears with appropriate **ingestion status** (as for API-registered videos).

**Rationale:** Captures the missing **admin UI** explicitly without rewriting 2.1 history.

---

### 4.2 PRD (incremental edit)

**Section:** MVP — Minimum Viable Product (or Success / Reviewer path)

**Proposed addition (one short bullet):**

- **Admin registration:** An admin can **register** a video for ingestion **via the web UI** (admin page), not only via API, so a reviewer can complete **clone → up → ingest → search** without HTTP tools.

**Rationale:** Aligns PRD with **NFR6** (time-to-first-success) and removes ambiguity.

---

### 4.3 Epic 2 overview (one line)

**Current:** “Enable an admin to register and remove videos…”

**Proposed tweak:** Same sentence, add: “…**including registering videos from the admin UI (upload form)** in addition to API registration where applicable.”

---

### 4.4 UX specification (new subsection)

**Location:** After primary-page / ingest journey material, add **“Admin — video registration”**:

- **French** copy for labels, buttons, errors, `aria-label`s.  
- **Controls:** file input (or drag-and-drop optional), label field if required, primary submit, disabled state during request.  
- **Feedback:** inline / `Alert` for API errors; respect existing error wrapper pattern.  
- **Placement:** same **admin** route as the video list (Story 2.2) — top or clear section above the table.

---

### 4.5 Architecture (if needed)

Only if implementation discovers a mismatch:

- Confirm **`POST /videos`** contract for **browser uploads** (e.g. `multipart/form-data` vs JSON + path).  
- Document the chosen approach in the relevant API section.

---

## Section 5: Implementation Handoff

| Role | Responsibility |
|------|----------------|
| **Development** | Implement Story 2.5; wire to `POST /videos`; French strings; tests as per project norms. |
| **PO / SM** | Add story to `epics.md` and `sprint-status.yaml`; order **2.5** relative to **2.2** (in review) — parallel or next. |
| **PM** | Optional PRD one-liner; no epic replan beyond this proposal. |

**Success criteria**

- Admin can register a video **only from the browser** on the admin page, end-to-end.  
- Existing API-based registration **still** works.  
- No regression on ingestion pipeline or listing.

---

## Checklist execution log (batch)

### Section 1 — Trigger and context

| ID | Item | Status |
|----|------|--------|
| 1.1 | Triggering story: **2.1** | Done |
| 1.2 | Problem type: expectation vs written AC + planning gap | Done |
| 1.3 | Evidence: epics AC, sprint status, architecture | Done |

### Section 2 — Epic impact

| ID | Item | Status |
|----|------|--------|
| 2.1 | Epic 2 completable with additions | Done |
| 2.2 | Modify scope: **add story**; optional epic blurb | Done |
| 2.3 | Future epics: **no change** | Done |
| 2.4 | No obsolete epics; **one new story** | Done |
| 2.5 | Priority: implement **2.5** near admin work (**2.2**) | Done |

### Section 3 — Artifacts

| ID | Item | Status |
|----|------|--------|
| 3.1 | PRD: **minor add** | Done |
| 3.2 | Architecture: **verify** upload contract | Done (action if gap found) |
| 3.3 | UX: **add admin registration** | Done |
| 3.4 | Secondary: tests for form; **optional** E2E | Done |

### Section 4 — Path forward

| ID | Item | Status |
|----|------|--------|
| 4.1 | Direct adjustment: **Viable** (Low / Low) | Done |
| 4.2 | Rollback: **Not viable** | Done |
| 4.3 | MVP review: **Not required** | N/A |
| 4.4 | Selected: **Option 1** | Done |

### Section 5 — Proposal components

| ID | Item | Status |
|----|------|--------|
| 5.1–5.5 | Issue summary, impacts, path, MVP, handoff | Done |

### Section 6 — Final review

| ID | Item | Status |
|----|------|--------|
| 6.1–6.3 | User approval | **Done** (2026-03-22) |
| 6.4 | `sprint-status.yaml` + `epics.md` + `prd.md` + `ux-design-specification.md` | **Done** |
| 6.5 | Handoff: dev implements Story **2.5** | **Done** |

---

## Sprint status YAML (applied)

Entry added under `development_status` (Epic 2):

```yaml
  2-5-admin-can-register-videos-via-admin-ui-upload-form: backlog
```

---

## Approval record

- **Approved by:** Armand  
- **Date:** 2026-03-22  
- **Artifacts updated:** `sprint-status.yaml`, `epics.md` (Story 2.5 + Epic 2 blurb), `prd.md` (MVP bullet), `ux-design-specification.md` (Admin — video registration).

---

_End of Sprint Change Proposal — 2026-03-22_
