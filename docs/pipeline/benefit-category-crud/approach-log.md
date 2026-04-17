# Approach Log — Benefit Category CRUD

> **Purpose**: Every user decision with the question, options presented, and the reasoning behind the choice. This is the human-trail record.
> **Ticket**: CAP-185145

---

## User Inputs (Phase 0)

| Input | Value | Why It Matters |
|-------|-------|----------------|
| Feature name | Benefit Category CRUD | Scope — this pipeline targets the Category entity (parent of benefit instances), not benefit instances themselves |
| Ticket | CAP-185145 | Traceability — all artifacts and git commits tagged with this |
| BRD | `Tiers_Benefits_PRD_v3_Full.pdf` (v3, 47 pages) | Source of truth for product intent |
| Primary repo | kalpavriksha (current) | Pipeline orchestration home |
| Supporting repos | emf-parent, intouch-api-v3, cc-stack-crm, thrift-ifaces-pointsengine-rules | Expected cross-repo change surface — confirmed via BRD cross-repo nature of category config |
| UI source | v0.app URL (Benefits & Tiers prototype) | Visual reference for UX — drives Phase 3 UI extraction |
| Live Dashboard | yes | Enables real-time stakeholder visibility |

---

## Decisions Log

_(Populated incrementally as the user answers questions, resolves blockers, approves architecture, etc.)_

### Phase 1 (BA Deep-Dive) Decisions

**Q1 — Scope (2026-04-18)**
- **Question**: What's in scope? Category CRUD only, or also instance linking / aiRa / matrix view / subscription picker?
- **Options presented**:
  1. Category CRUD only
  2. Category CRUD + Instance linking
  3. + aiRa mapping
  4. + Matrix View + Subscription picker (everything)
  5. Other
- **Recommendation**: [1] or [2]
- **User answer**: **2** — Category CRUD + Instance linking
- **Out of scope**: aiRa mapping (AC-BC09), Matrix View (AC-BC10/11), Subscription benefit picker (AC-BC13)
- **In scope ACs**: AC-BC01, AC-BC02, AC-BC03, AC-BC07, AC-BC08, AC-BC12 + data model + category types + maker-checker workflow

**Q3 — Lifecycle state machine vs isActive flag (2026-04-18)** _(ProductEx PB-01 blocker)_
- **Question**: AC-BC01 has category created with lifecycle=DRAFT + is_active=true simultaneously. Are these separate concepts or should one replace the other?
- **Options presented**:
  1. Two fields (both coexist): lifecycle_state + is_active (my recommendation)
  2. One unified state enum (DRAFT/PENDING/ACTIVE/INACTIVE)
  3. Category has is_active only; approval lives in separate approval_request table
  4. Other
- **User answer**: **4 → A** — Descope maker-checker entirely for MVP. Single is_active flag. Immediate CRUD. Maker-checker in later phase.
- **Impact on scope**:
  - Removed from in-scope: AC-BC07 (Maker-Checker Category Creation), AC-BC08 (Maker-Checker Instance Change)
  - In-scope ACs now: AC-BC01, AC-BC02, AC-BC03, AC-BC12
  - Data model simplified: single `is_active` column, no `lifecycle_state`, no `approval_request` table
  - API: all mutations return final state immediately (no 202/pending responses)
  - Workflow diagrams simpler — no approval state machine
- **Downstream effect**: AC-BC01's phrasing ("DRAFT state" + "correct trigger event derived from categoryType") must be reinterpreted for MVP. BA will rewrite the AC to match the descoped behaviour.

**Q2 — isActive semantics vs "no instances = inactive" (2026-04-18)**
- **Question**: BRD has two "inactive" phrasings — isActive boolean field (§2) and "a category with no instances is considered Inactive" (§5 prose). Same concept or distinct states?
- **Options presented**:
  1. One state, derived (no isActive column; inactivity purely derived from instance count)
  2. Two distinct data states (isActive flag AND "zero instances" are separately meaningful)
  3. Explicit isActive only; §5 prose treated as descriptive, not a data state (recommended)
- **User answer**: **3** — Explicit isActive only
- **Impact on data model**: single `is_active` boolean column, default true. No derived state from instance count. UI may show "Not configured" hints for empty categories but that's presentation-layer only.
- **Note**: ProductEx's parallel review (PB-01) surfaced a THIRD axis — the DRAFT/PENDING_APPROVAL/ACTIVE lifecycle state machine from §5 maker-checker. That is a different axis from this Q2 (which was about the "no instances" phrasing only). Lifecycle state machine is addressed in Q3 next.

**Q4 — categoryType enum: closed vs open vs hybrid? (2026-04-18)** _(ProductEx PB-02 / OQ-3)_
- **Question**: BRD §3 lists 9 category types as "examples". Is this a closed enum, open config-driven set, or hybrid?
- **Options presented**:
  1. Closed — hardcoded 9-value Java enum (my recommendation)
  2. Open — `category_type` table, config-driven, JSON value schema per type
  3. Hybrid — closed enum + `CUSTOM` escape hatch
  4. Other / clarify
- **User answer**: **4 → e → "keep one enum for category Type BENEFITS for now and we don't need triggerEvent"**
- **Follow-up clarifying questions (I-1 to I-4)** and user answers:
  - **I-1 (awarding)**: **c** — Benefit awarding done by an **existing system** reading this config (no new awarding logic in MVP)
  - **I-2 (instance value shape)**: **e** — **No value at all.** Instance is pure (categoryId, tierId) association with no payload
  - **I-3 (BRD alignment)**: **yes** — BRD §3, §5.3, §5.4, and AC-BC01 trigger-derivation clause are deferred. BA doc will flag explicitly.
  - **I-4 (keep categoryType column?)**: **a** — Keep column for future extensibility (YAGNI accepted)
- **Decisions recorded**: D-06, D-07, D-08, D-09, D-10, D-11
- **Impact on scope & model**:
  - BenefitCategory = `(id, program_id, name, category_type='BENEFITS', tier_applicability, is_active, audit cols)`. No `trigger_event` column.
  - BenefitInstance = `(id, category_id, tier_id, is_active, audit cols)`. No `value`, `amount`, `points`, `voucher_template_id`, `json_config`, or `trigger_event` columns.
  - No event handlers, no trigger mapping, no per-type value schema, no type-specific validation logic.
  - Feature reduces to a **generic grouping + tier-association** service. Awarding is someone else's concern.
- **New risks/questions introduced**:
  - OQ-15: **Who consumes this config?** Phase 5 research must identify the reader (candidates: EMF tier event forest, peb, intouch-api-v3). They drive the API schema as a consumer.
  - Risk: If the downstream consumer needs fields we didn't model (e.g., a type discriminator beyond BENEFITS, or a hint field), the API may need a second iteration. Mitigated by Phase 5 confirming consumer identity before design-freeze.
  - Risk of ambiguity: With instance carrying no value, the term "Benefit Instance" barely describes a "benefit" — it's a category-tier association. UI copy may need adjustment.

**Q5 — Coexistence with existing `Benefits` entity (2026-04-18)** _(OQ-11 / ProductEx DT-01)_
- **Question**: Existing emf-parent `Benefits` (promotions-backed, VOUCHER/POINTS) vs new `BenefitCategory`/`BenefitInstance` (grouping, no value) — how do they relate?
- **Options presented**:
  1. Strict coexistence — separate, unrelated (my recommendation)
  2. Linked coexistence — new model groups old Benefits via FK
  3. New is authoritative; old is legacy to deprecate later
  4. Rename new entities to avoid the word "Benefit"
- **User answer**: **1** — Strict coexistence
- **Decision recorded**: D-12
- **Impact**:
  - Zero schema changes to existing `Benefits` table (see C-14)
  - New tables live in their own namespace (package + table naming TBD in Phase 7)
  - BA doc must include a Glossary section distinguishing the two concepts
  - UI copy/navigation distinguishes "Benefit Catalog" (new) from "Promotions" or legacy benefits screen (existing)
  - Reviewer (Phase 11) and Analyst compliance (Phase 10c) MUST check that no code imports or references the legacy `Benefits` entity from the new feature's classes

**Q6 — Delete semantics + cascade on deactivation (2026-04-18)** _(OQ-5 + OQ-9 / ProductEx MS-01 + PB-04)_
- **Question** (Part A — delete): Hard-delete or soft-delete only?
- **Options A**:
  1. Hard delete only
  2. Soft delete only (is_active=false)
  3. Both (soft-delete via PATCH, hard-delete via DELETE with guards)
  4. Soft delete for MVP, hard delete later if needed (my recommendation)
- **Question** (Part B — cascade): When category deactivated, what happens to instances?
- **Options B**:
  1. Auto-deactivate cascade (my recommendation)
  2. Block deactivation if any active instance
  3. Leave instances untouched (orphan behaviour)
  4. Warn+allow (UI confirmation, then cascade)
- **User answer**: **A2 + B1** — Soft delete only + Cascade deactivate
- **Decisions recorded**: D-13 (soft-delete only), D-14 (cascade deactivate)
- **Impact**:
  - No DELETE HTTP verb in the API (C-15)
  - Category deactivation = transactional cascade to all child instances (C-16)
  - Reactivation does NOT auto-reactivate instances — deliberate per-instance action (C-17)
  - Simpler than A4 in that even future hard-delete isn't on the roadmap yet
  - QA test scenarios needed: deactivate category with 0/1/N active instances, concurrent deactivation, reactivation behaviour
  - Data model: instances keep a `deactivated_at` or inherit from audit cols; no separate state machine

### Phase 4 (Blocker Resolution) Decisions

_Pending._

### Phase 6 (Architect) Decisions

_Pending._

### Phase 11 (Reviewer Gap Routing) Decisions

_Pending._

---

## Accepted Risks

_(If user chose [A] Accept during Phase 11 findings routing, logged here with reasoning.)_

| # | Finding | User Reasoning | Phase |
|---|---------|----------------|-------|
