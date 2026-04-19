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

**BLOCKER #1 — OQ-16 Consumer identity (2026-04-18)** _(Critic C-1 — top blocker; BA proposed EMF at C3, Principle 2 forbade proceeding on that)_
- **Question**: Who is the downstream system that READS the BenefitCategory/BenefitInstance config and applies benefits? BA's working hypothesis was "EMF tier event forest" at C3, but Phase 2 Gap Analyser V5 contradicted that — grep of `Benefits` in `emf/.../eventForestModel/` returns 0 files. Proceeding to Phase 6 on C3 evidence violates Principle 2 (reversibility threshold: irreversible design decisions need C4+).
- **Options presented**:
  1. **A — Pause** until product names the consumer explicitly
  2. **B — Scope-reduce** to pure internal registry (no consumer integration in this ticket at all; config-only with no enforcement path)
  3. **C — 2-day Phase 5 spike** in emf-parent to verify/refute EMF hypothesis, then resume
  4. **D — Name the consumer now** (user knows it)
  5. **Other**
- **User answer**: **Other — "Client will consume this flow, Thrift will [be] written in EMF and expose through intouch-api-v3"**
- **Interpretation**: The consumer is NOT another internal service in the loyalty stack (EMF, peb, etc.). It is an external **Client** (Capillary customer integration — merchant apps, SDKs, or direct API calls). The delivery chain is:
  ```
  External Client → intouch-api-v3 (REST endpoint) → EMF (Thrift RPC) → MySQL
  ```
- **Follow-up sub-question (W)**: What path do writes take vs reads?
  - **W1 — Same chain for reads + writes**: All CRUD = Client → REST → Thrift → DB (my recommendation — single transactional boundary in EMF)
  - **W2 — Reads via Thrift, writes via a different admin channel** (admin UI → intouch-api-v3 direct DB, reads via Thrift for Client)
  - **W3 — Writes inside EMF only (admin tooling), reads via Thrift→REST for Client**
- **User follow-up answer**: **W1** — All CRUD through the same chain
- **Decisions recorded**: **D-18** (consumer = external Client via Thrift→REST), **D-19** (W1 — EMF owns entire transactional boundary for reads + writes)
- **Cascading resolutions** (tracked in session-memory Open Questions):
  - ✅ OQ-16 resolved by D-18
  - ✅ OQ-27 resolved by D-18/D-19 → MySQL (Thrift-exposed loyalty entities are all MySQL per `SlabInfo`, `Benefits`, `ProgramSlab`; `UnifiedPromotion` MongoDB was tied to its maker-checker which is descoped)
  - ⚠ OQ-23 tentatively resolved by D-18 → Thrift `i32` parity forces `int(11)` + `OrgEntityIntegerPKBase`. Phase 5 to verify existing Thrift handler PK patterns (raise to C6+)
  - ⚠ OQ-17 partially resolved — definitely public Client-facing API (NOT internal plumbing). Remaining sub-question lifts to new BLOCKER #2 (admin UI in MVP, or API-only?)
- **New open questions introduced by this answer**:
  - **OQ-34**: Authz at the Client boundary — can an external Client WRITE these configs, or are writes admin-only and only reads are Client-facing?
  - **OQ-35**: Phase 5 action — identify an existing emf-parent Thrift handler to copy patterns from (org context, exception translation, transaction boundary)
  - **OQ-36**: Error envelope at the Thrift→REST boundary — how do Thrift exceptions map to `ResponseWrapper<T>` + HTTP codes?
  - **OQ-37**: Validation-layer placement — REST Bean Validation vs EMF handler vs both
- **Cross-repo impact pre-populated** in session-memory "Cross-Repo Coordination" table at C5-C6 confidence (Phase 5 to verify):
  - thrift-ifaces-pointsengine-rules: NEW IDL
  - emf-parent: NEW entities + DAOs + Thrift handler + migrations
  - intouch-api-v3: NEW REST controllers + Thrift client wrappers
  - cc-stack-crm: possibly NEW schema files (or emf-parent Flyway owns — Phase 5 to confirm)
- **Why this unlocks Phase 6**: Principle 2 passed — we now have C5+ on the consumer contract shape (RPC-over-Thrift with typed structs), which is what Phase 6 architecture needs to freeze. The "mystery consumer" risk is eliminated.

---

**BLOCKERS #2–5 (BATCH) — OQ-17, OQ-19, OQ-24, OQ-25, OQ-28 (2026-04-18)**

User supplied a single composite answer that resolved four blockers + one HIGH question in one sweep. Recorded as a batch:

- **BLOCKER #2 (OQ-17)** — Admin UI in MVP?
  - Options presented: (a) full admin UI, (b) API-only + Postman/internal tooling, (c) API + minimal admin console, (d) other
  - User initially chose `d`; after clarification menu (d1–d7), answered: **API-only MVP**
  - **Decision recorded**: D-20
  - Phase 3 stays skipped; `/api-handoff` doc produced post-Phase 7 as the UI team's contract
  
- **BLOCKER #3 (OQ-19)** — BenefitInstance redundant with tier_applicability?
  - User answer: rename `benefit_instance` table → `benefit_category_slab_mapping`
  - Interpretation: BenefitInstance as a pseudo-entity is dropped; it becomes an explicit **junction table** between `benefit_categories` and `program_slabs`. Redundant `tier_applicability` field on `benefit_categories` removed — junction IS the source of truth.
  - **Decision recorded**: D-21
  - Also resolves **OQ-28** (junction vs JSON) in the same stroke.
  
- **BLOCKER #4 (OQ-24)** — `tier_id` vs `slab_id`, entity-naming collision?
  - User answer: `slab_id` (not `tier_id`)
  - Consequence: Client-facing REST JSON will contain `slab_id`. `/api-handoff` will include a glossary mapping "slab" → "tier" for Client comprehension.
  - Entity naming: user kept `benefit_categories` table (implying `BenefitCategory` entity). Collision with legacy `Benefits` accepted, mitigated by C-14 (separate tables) + D-12 (strict coexistence) + separate package namespace.
  - **Decision recorded**: D-22
  
- **BLOCKER #5 (OQ-25)** — Audit column pattern?
  - User answer: `created_on`, `created_by`, `updated_on`, `updated_by`, `auto_update_time`
  - **Hybrid approach**: platform-native `_on` suffix retained (NOT `_at`); explicit `updated_on`/`updated_by` pair added (not present in any existing platform table — `promotions` is closest with only `last_updated_by`); `auto_update_time` kept as DB-level physical-touch safety net alongside app-managed `updated_on`.
  - **Decision recorded**: D-23
  - This is a mild deviation from both options in OQ-25 (not pure "match existing" and not pure "new 4-column"). Deliberate engineering judgment — the ADR in Phase 6 will document why.

- **Impact on constraints**:
  - C-10 → superseded by **C-10'** (junction table schema)
  - C-11 → superseded by **C-11'** (category schema without tier_applicability field)
  - C-22 → ✅ resolved (audit column pattern finalized)
  
- **Blockers remaining (7 of 12)**: OQ-26 (G-01 CRITICAL), OQ-18 (compliance), OQ-20 (scale), OQ-21 (cascade reactivation), OQ-22 (409 vs reactivate), OQ-29 (name uniqueness on soft-delete), OQ-30 (cache day-1 or defer).

- **Clarifications (all confirmed 2026-04-18)**:
  - ✅ **CLR-1**: Same 5 audit columns apply to `benefit_category_slab_mapping` (junction rows have their own creator/updater audit — per D-14 cascade + per-instance reactivation)
  - ✅ **CLR-2 (a)**: `tier_applicability` field is REMOVED from `benefit_categories`. Junction table `benefit_category_slab_mapping` is the sole source of truth for category↔slab applicability.
  - ✅ **CLR-3 (a)**: Entity name `BenefitCategory` retained. Collision with legacy `emf-parent.Benefits` mitigated by C-14 (separate tables) + D-12 (strict coexistence) + separate package namespace. Phase 11 Reviewer will verify no imports of legacy `Benefits` in new-feature classes.

---

**BLOCKER #6 — OQ-26 🔴 CRITICAL (2026-04-18)** _(G-01 Timezone vs G-12.2 Follow-existing-patterns tension)_
- **Question**: Timestamp Java type + DB column type for audit columns. `java.util.Date` + `@Temporal(TIMESTAMP)` + MySQL `datetime` (pattern-match — violates G-01.3) vs `java.time.Instant` + `TIMESTAMP` (G-01 compliant — type island)?
- **Options presented**: (a) pattern-match, (b) G-01 compliant, (c) hybrid at one boundary, (d) defer-with-TD, (e) other/escalate
- **User chose** (e) initially, then refined in e4 to: **"In Thrift: i64, intouch-api-v3: ISO date format, emf: SQL date format"**
- **Interpretation**: A three-boundary pattern — each layer uses its native form with conversion at two explicit boundaries:
  ```
  +---------------+   ISO-8601 UTC   +----------------+   i64 millis   +-------------+   DATETIME
  | Client (REST) | ---------------- | intouch-api-v3 | -------------- |  EMF Thrift | ------------
  +---------------+     JSON body    +----------------+  Thrift wire   +-------------+  MySQL column
                                             |                                  |
                                             '---- Jackson config ----'         '---- Calendar(UTC) ----'
                                               conversion boundary 1              conversion boundary 2
  ```
- **Decision recorded**: D-24
- **Why this beats the hybrid option (c) I proposed**: The user's framing decomposes "boundary" into TWO explicit points (REST↔Thrift and Thrift↔EMF) rather than one. `i64` at Thrift is language-neutral and wire-efficient. ISO-8601 at REST is the modern Client contract standard. Internal `Date` maintains join/query parity with `ProgramSlab`, `Benefits`, `Promotions`.
- **Residual risks flagged + new OQs**:
  - OQ-38 (HIGH): JVM default TZ in production — MUST be known before Phase 9. If IST, explicit UTC `Calendar`/`TimeZone` needed at conversions; if UTC, defaults work but G-01.7 multi-TZ tests still required.
  - OQ-39 (LOW): `i64` unit — **defaulted to milliseconds** (matches `Date.getTime()` + JS convention).
  - OQ-40 (LOW): ISO-8601 format variant — default pin `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`.
  - OQ-41 (LOW): Thrift field naming — `createdOn` vs `createdOnMillis`. Phase 5 to check existing IDL convention.
- **Phase 6 Architect action**: Produce ADR documenting the three-boundary pattern with justification, evidence of both guardrails honoured, and explicit conversion-point ownership.
- **Phase 9 QA/SDET action**: Multi-timezone integration tests per G-01.7 — test suite runs in UTC AND IST JVM TZ; all REST responses must be UTC-tagged regardless of JVM.
- **Constraints updated**: C-23 resolved; new C-23' records conversion ownership.

---

**BLOCKER #7 — OQ-18 (2026-04-18)** _(Maker-checker descope: compliance sign-off + schema reservation)_
- **Question**: D-05 descoped MC for MVP. Do we need product/compliance sign-off for that? Reserve a nullable `lifecycle_state` column now to avoid a future breaking migration?
- **Options presented**: (a) no sign-off, no reserve, (b) no sign-off, reserve column, (c) require sign-off, no reserve, (d) (c)+(b), (e) other
- **User answer**: **a** — No sign-off, no reserved column. Ship as-is.
- **Decision recorded**: D-25
- **Rationale captured**: C5 confidence that no current customer contract mandates MC at the benefit-category level (promotion-level MC is already handled by `UnifiedPromotion`). YAGNI honoured — speculative columns rejected. Future MC return is an acceptable migration.
- **Impact**:
  - No `lifecycle_state` column on either `benefit_categories` or `benefit_category_slab_mapping` (C-10', C-11' remain clean).
  - If MC is added in a future ticket, the migration will be: add column + backfill existing rows to `ACTIVE` + branch CRUD paths on column presence. Cost is one-time and scoped to that future ticket.
  - Phase 11 Reviewer should note this decision in the blueprint — "MC return requires a migration ticket, not in scope here".
- **No new OQs introduced.**

---

**BLOCKER #8 — OQ-20 (2026-04-18)** _(Scale envelope for NFR, cascade sizing, indexing, cache, replica decisions)_
- **Question**: Expected categories-per-program, slabs-per-category, cascade row count, read QPS, write QPS, and replica vs primary reads for Client?
- **Options presented**: (a) small, (b) medium, (c) large, (d) Phase 5/6 to research, (e) assumptions-with-post-launch-validation
- **User answer**: **a** — SMALL envelope
- **Decision recorded**: D-26
- **Numbers locked in** (assumptions, not commitments):
  - Categories/program: ≤50
  - Slab-mappings/category: ≤20
  - Cascade worst case: ≤1000 rows in one txn
  - Read QPS: <10 sustained
  - Write QPS: <1 sustained
  - Client reads: **primary** (no replica-read complexity)
- **Consequential simplifications**:
  - Cascade stays single-txn — no batched txns, no async cleanup
  - No cache day-1 (trivially resolves OQ-30 at this QPS)
  - No CQRS-lite / read-write split
  - Standard JPA indexes on `(org_id, program_id)` + `(org_id, slab_id)` suffice
  - 500ms P95 NFR likely very comfortable — Phase 5 to compare against legacy `/benefits` list SLA
- **Partial resolution of OQ-33**: PRD's "200 categories / 1000 instances" is superseded by SMALL envelope numbers. 500ms P95 baseline-check deferred to Phase 5.
- **Phase 9 SDET action**: Load test at 2x the envelope (100 cat/prog, 40 slab/cat, 2000 cascade) to verify headroom. Not GA blockers; flag if breached.

---

**BLOCKER #9 — OQ-21 (2026-04-18)** _(Cascade asymmetry — does reactivate cascade?)_
- **Question**: D-14 cascade-deactivates mappings when category deactivates. On reactivate, cascade too? Per-mapping admin re-enable? Admin-choice? Smart-restore by provenance?
- **Options presented**: (a) no cascade on reactivate, (b) cascade reactivate, (c) selective cascade via `deactivation_source`, (d) admin-choice via query param, (e) other/reframe
- **User chose** (e) → `e1`: **No reactivation at all in MVP. Deactivation is one-way.**
- **Decision recorded**: D-27
- **Interpretation**: The elegant answer — rather than debating HOW reactivation cascades, we simply eliminate the reactivation path. Deactivation is terminal. To "restore", admin creates a new category / new mapping. Old rows stay as audit history.
- **Why this is clean**:
  - Eliminates the asymmetric-UX debate entirely (there's no direction to compare).
  - Eliminates the "silent re-enable" compliance risk (option b) without adding a provenance column (option c).
  - YAGNI-compliant — if a future ticket adds reactivation, they design it properly with full requirements.
  - Audit story is strong — deactivated rows are immutable historical records.
- **API-level consequences**:
  - `PATCH /categories/:id {is_active: true}` on a deactivated row → **409 Conflict** (explanatory message: "Deactivation is terminal in MVP. POST a new category.")
  - `PATCH /mappings/:id {is_active: true}` on a deactivated row → **409 Conflict** (same message, for mappings).
  - Only `{is_active: false}` is a valid PATCH body for is_active.
- **Downstream effects on remaining blockers**:
  - **BLOCKER #10 (OQ-22)**: Reframed. Under D-27, "POST on existing-inactive (category, slab)" must create a NEW mapping row (because PATCH reactivation doesn't exist). The question becomes about UNIQUE constraint shape on the junction.
  - **BLOCKER #11 (OQ-29)**: Now higher stakes. If admin deactivates category "Silver Tier Benefits", can they later create a new category with the same name? This decision directly gates e1's usability.
- **Constraints updated**: C-17 superseded → C-17' (deactivation is terminal).
- **Supersedes / deletes**: C-17 (reactivation-does-not-cascade) is moot — there is no reactivation.

---

**BLOCKERS #10 + #11 (BATCH) — OQ-22 + OQ-29 (2026-04-18)** _(junction uniqueness + category name reuse after soft-delete)_

User answered both in one statement: **"e5: don't make uniqueness at DB level, handle in the validation, once category deactivated (is_active→false) treat as soft-delete, user can able to make same name category if they want"**

- **BLOCKER #10 (OQ-22)** — POST semantics when an inactive mapping exists for (cat, slab):
  - Options presented: (a) new row + composite UNIQUE incl. is_active, (b) history table, (c) versioning column, (d) go to OQ-29 first, (e) other/reframe
  - User reframed (e5): **No DB UNIQUE at all**. App-layer validation on every POST. Active-row-only uniqueness.
  - **Decision recorded**: D-28
  
- **BLOCKER #11 (OQ-29)** — Category name reuse after soft-delete:
  - Options usually: (block reuse, match legacy `benefits`) vs (allow reuse)
  - User explicit answer: **allow reuse** ("user can make same name category if they want")
  - **Decision recorded**: D-29

- **Unified mechanism**:
  - Neither `benefit_categories` nor `benefit_category_slab_mapping` has DB-level UNIQUE on business keys.
  - Service-layer validation on POST:
    - Category: reject 409 iff ACTIVE row exists with `(program_id, name, org_id)`.
    - Mapping: reject 409 iff ACTIVE row exists with `(category_id, slab_id, org_id)`.
  - Inactive rows are invisible to uniqueness checks — they accumulate as audit history.
  - Admin can re-use a name after deactivation; admin can re-add a mapping after deactivation; all via fresh POST creating new rows with new PKs.
  - Matches "deactivation is terminal" (D-27) spirit — old rows stay dead; new rows are genuinely new.

- **Trade-off / risk captured**:
  - Classic race condition risk: two concurrent POSTs can both pass validation → two active rows exist. At D-26 SMALL scale (<1 QPS writes), probability is effectively zero per hour. Formally flagged as **OQ-42** with Phase 7 Designer recommendation: **MySQL advisory lock** (`GET_LOCK('benefit_category_{program_id}_{name_hash}')`) at POST entry, released on txn end — deterministic, low overhead, no schema change.
  - Historical row accumulation: deactivated rows stay forever. At SMALL scale (<20 mappings/cat, ≤50 cat/prog, low write QPS), noise is negligible. If future telemetry shows accumulation pain, add a nightly archival job.
  - GUARDRAILS tension: G-05.3 "constraints at DB level" — user's decision deliberately relaxes this. Architect ADR in Phase 6 must document: "At D-26 SMALL scale, app-layer validation is acceptable; DB UNIQUE would conflict with D-28's soft-delete reuse semantics without partial-index complexity."

- **Constraints updated**:
  - C-18 → superseded by **C-18'** (no DB UNIQUE; app validates active-only)
  - D-15 amended — "per-Program" holds but scoped to active rows, app-enforced

- **New OQs surfaced** (Phase 7 Designer actions, non-blocking for Phase 6):
  - **OQ-42**: Race-condition mitigation (advisory lock recommended)
  - **OQ-43**: String normalization for `name` (length, trim, case sensitivity, Unicode)

- **Downstream simplification**: 
  - No partial index gymnastics, no generated columns, no composite UNIQUE with `is_active`. Migration stays a simple CREATE TABLE per D-23 schema.
  - Thrift IDL stays minimal — no `force: optional` semantics needed around UNIQUE reads.

### Phase 5 → 6 Transition: Pre-Phase-6 Resolutions

After Phase 5 (Codebase Research + Cross-Repo Tracing) completed, three HIGH-severity blocking items were pre-resolved in a single interactive Q&A round to unblock Phase 6 (Architect).

---

**Q-1 (Q-T-01 — `createdBy` type 3-layer conflict)**

- **Question asked**: Cross-repo-trace flagged a 3-layer type conflict for `createdBy` / `updatedBy`:
  - Java entity pattern in EMF (`Benefits.java:createdBy` is `int`)
  - D-23 blocker decision declared schema `created_by VARCHAR(...)`
  - thrift-ifaces analysis recommended `string createdBy` for audit readability
  Mixing these causes runtime Hibernate failure (INT column ↔ VARCHAR type) or mandatory handler translation (`i32` ↔ `string`). Must align before Phase 7 Designer.

- **Options presented**:
  - (a) **Platform-consistent** — align on `int` / `INT(11)` / `i32`. Matches existing `Benefits.createdBy` pattern. Username readability via join at read layer if needed.
  - (b) **Audit-readable** — align on `String` / `VARCHAR(120)` / `string`. Username written directly, no join. Breaks pattern.
  - (c) **Split concerns** — keep numeric `created_by_id` + add denormalized `created_by_username VARCHAR(120)`. Adds column, keeps both.

- **User's choice**: **(a)** — platform-consistent `int`.

- **Decision recorded**: **D-30** — `createdBy` / `updatedBy` = `int` / `INT(11)` / `i32` across all three layers. D-23's VARCHAR wording is amended (superseded on type specification; all other D-23 details — column names, `auto_update_time`, `_on` suffix — stand).

- **Status**: Q-T-01 RESOLVED ✅ (was HIGH blocker). RF-3 MITIGATED.

---

**Q-2 (OQ-44 — HTTP 409 handler in `TargetGroupErrorAdvice`)**

- **Question asked**: `TargetGroupErrorAdvice` currently has NO HTTP 409 handler. D-27 (reactivation → 409) and D-28 (active duplicate POST → 409) both require one. Options: add a new `ConflictException` + handler, OR downgrade 409 scenarios to HTTP 400 to match existing platform convention (where `ValidationException → 400`).

- **Options presented**:
  - (a) **Add `ConflictException` + `@ExceptionHandler` → HTTP 409**. Requires EMF handler to throw `PointsEngineRuleServiceException.setStatusCode(409)`; Facade catches, inspects `statusCode`, rethrows as `ConflictException`.
  - (b) **Downgrade to HTTP 400**. Reuse `ValidationException`. Loses REST semantic precision — client cannot distinguish a malformed payload from a business-rule conflict.
  - (c) **Use existing exception hierarchy** if one exists. (None found in Phase 5 analysis.)

- **User's choice**: **(a)** — add `ConflictException` + 409 handler.

- **Decision recorded**: **D-31** — NEW `ConflictException` class in `intouch-api-v3/.../exceptionResources/`; NEW `@ExceptionHandler(ConflictException.class)` in `TargetGroupErrorAdvice` → `HttpStatus.CONFLICT` + `ResponseWrapper.error(409, code, message)`. EMF handler throws `PointsEngineRuleServiceException` with `statusCode=409` for D-27 and D-28 paths; Facade maps.

- **Status**: OQ-44 RESOLVED ✅ (was HIGH blocker). RF-2 MITIGATED.

---

**Q-3 (OQ-46 — cc-stack-crm ↔ emf-parent DDL sync mechanism)**

- **Question asked**: emf-parent integration tests pull schema DDL from `integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/`. Both new DDL files (`benefit_categories.sql`, `benefit_category_slab_mapping.sql`) must exist in BOTH repos (cc-stack-crm authoritative + emf-parent IT resources). What keeps them in sync — manual copy, sync script, or something else? Who owns keeping them consistent?

- **Options presented**:
  - (a) **Tell directly** — user explains the mechanism in free text.
  - (b) **Manual copy** — we adopt a convention: PR touches both repos, reviewers check diff parity.
  - (c) **Sync script** — we propose a small script; user confirms/rejects.

- **User's choice**: **(a)** — free-text answer. User explained: "this is a different module, we raise PR, then it will release before code release, and in EMF this module is added as submodule; we generally run IT and SonarQube coverage will track the coverage; so when we raise PR in submodule we will go to that branch in emf-parent and pull it and run the IT test cases."

- **Verification performed (C7)**: Read `/Users/anujgupta/IdeaProjects/emf-parent/.gitmodules`:
  ```
  [submodule "cc-stack-crm"]
      path = integration-test/src/test/resources/cc-stack-crm
      url = https://github.com/Capillary/cc-stack-crm.git
      branch = master
  ```
  User's claim confirmed by primary source.

- **Decision recorded**: **D-32** — cc-stack-crm is a git submodule of emf-parent. Dev workflow: (1) PR in cc-stack-crm with new DDL → (2) bump submodule pointer to feature branch in emf-parent → (3) IT run + SonarQube coverage → (4) on cc-stack-crm merge to master, re-point submodule to merged commit. Release order: cc-stack-crm merges FIRST, emf-parent code release SECOND (aligns with RF-1 deployment sequence).

- **Residual uncertainty (C5)**: Exact production Aurora schema apply mechanism (Facets Cloud auto-sync vs DBA script vs manual) is NOT resolved by the submodule workflow — that only covers dev + IT. Deferred to Phase 12 Blueprint deployment runbook (Q-CRM-1 and A-CRM-4 remain open for prod apply).

- **Status**: OQ-46 RESOLVED ✅ (dev/IT path). RF-5 PARTIALLY MITIGATED (prod apply still open, now LOW severity for dev / MEDIUM for prod).

---

**Pre-Phase-6 Resolution Summary**

| # | Item | Severity | Resolution | Decision | Blocks Phase 6? |
|---|------|----------|------------|----------|-----------------|
| Q-T-01 | createdBy type conflict | HIGH | Platform-consistent `int`/`INT(11)`/`i32` | D-30 | ✅ NO (resolved) |
| OQ-44 | HTTP 409 handler | HIGH | Add `ConflictException` + 409 handler | D-31 | ✅ NO (resolved) |
| OQ-46 | cc-stack-crm DDL sync | HIGH | Git submodule workflow (verified C7) | D-32 | ✅ NO (resolved; prod apply → Phase 12) |

All Phase-6-blocking items cleared. Proceeding to Phase 6 (HLD — Architect).

### Phase 5 → 6 Pre-HLD ADR Commits (2026-04-18)

> **Context**: Rework cycle 2 (Phase 6 → Phase 5) surfaced that Phase 8 QA found 2 BLOCKER-level design gaps that traced back to HLD choices `/architect` had made on its own without explicit user sign-off. User asked to **freeze the contentious architectural choices upfront as ADRs** before re-spawning `/architect`, so that the fresh HLD is designed _around_ the user's decisions rather than the reverse. Four questions asked, four ADRs recorded (D-33..D-36). `/architect` will be launched with these as **frozen, non-debatable inputs**.

---

**Q-33 — Optimistic-Lock Stance (Pre-HLD ADR #1, 2026-04-18)**

- **Question**: Phase 8 QA flagged OQ-QA-04 — Request DTO has no `version: Long` field, so client cannot send the version back to server, so `@Version` (if added on entity) is useless. Should HLD mandate an optimistic-lock stance?
- **Options presented**:
  - (A) **Mandate `@Version`** — add `version BIGINT NOT NULL DEFAULT 0` column, `@Version Long version` on `BenefitCategory` entity, `version: Long` on Update request DTO, 409 on stale version. Pure per G-10.
  - (B) **Add `@Version` + derive from GET** — entity has it, client fetches via GET-before-PUT, server validates. Less ceremony for client, still G-10 compliant.
  - (C) **Skip optimistic lock entirely** — accept last-write-wins; document as accepted deviation from G-10. Safe at D-26 SMALL scale (low admin QPS).
- **Recommendation**: **(C)** — rationale: at D-26 SMALL scale, admin QPS is low, multi-editor collision probability is negligible; optimistic-lock ceremony adds DDL + DTO field + client round-trip for a race window that won't materialize.
- **User answer**: **C** — No optimistic locking, last-write-wins, accept G-10 deviation.
- **Decision recorded**: **D-33** — no `@Version`, no `version` DTO field, G-10 documented as **accepted deviation** in ADR-001 with revisit-trigger.
- **Downstream impact**:
  - Phase 7 Designer MUST NOT add `@Version`
  - Phase 8 QA scenarios QA-34/QA-35 (stale-version, concurrent-update) are formally OUT OF SCOPE — replaced by "last-write-wins accepted; no concurrency test required" note
  - Phase 6 `/architect` writes ADR-001 with evidence and review-trigger (admin QPS >10/sec per tenant OR multi-editor Admin UI introduced)
- **Confidence**: C6 — user decision with explicit guardrail deviation acknowledgment.

---

**Q-34 — Reactivation Path (Pre-HLD ADR #2, 2026-04-18)**

- **Question**: Phase 8 QA flagged OQ-QA-01 — US-6 (P1) requires reactivating a deactivated category, but D-27 says "deactivation is terminal — any mutation on inactive = 409". These contradict. How should HLD resolve?
- **Options presented**:
  - (A) **Dedicated `PATCH /v3/benefitCategories/{id}/activate` endpoint** — US-6 IN SCOPE; mirrors deactivation verb; D-27 amended to "PUT/DELETE on inactive = 409, explicit reactivation via dedicated PATCH is the only allowed state-change".
  - (B) **Descope US-6** — keep D-27 terminal; any reactivation requires new category creation; simpler data model; US-6 kicks to later epic.
  - (C) **Use `PUT` with `isActive: true`** — reuses PUT endpoint; bends PUT semantics (usually for full-resource updates, not state flips).
- **Recommendation**: **(A)** — rationale: US-6 is P1 per PRD; dedicated PATCH is clean REST semantic; symmetric with potential deactivate verb; avoids bending PUT.
- **User answer**: **A** — Dedicated `PATCH /{id}/activate`.
- **Decision recorded**: **D-34** — new endpoint; does NOT auto-reactivate cascaded slab-mappings (admin re-maps explicitly); 404 on non-existent; 409 on name-taken-by-another-active; idempotency (204 vs 409) deferred to `/architect`; Thrift IDL +1 method `activateBenefitCategory`.
- **D-27 amendment**: REWORDED — "updates via PUT/DELETE on inactive category return 409; reactivation via dedicated PATCH /activate endpoint is the explicit and only allowed state-change on an inactive category"
- **Downstream impact**:
  - Phase 6 `/architect` writes ADR-002 with flow diagram + idempotency semantics
  - Phase 7 Designer adds `activateBenefitCategory(orgId, categoryId, actorUserId)` facade + Thrift handler + REST controller
  - Phase 8 QA adds scenarios: happy reactivation, idempotency, name-taken 409, non-existent 404
- **Confidence**: C6 — user decision, clean semantic, restores US-6 to in-scope.

---

**Q-35 — REST Surface Granularity (Pre-HLD ADR #3, 2026-04-18)**

- **Question**: Phase 7 v1.1 had drifted to split mapping management into a separate `/v3/benefitCategorySlabMappings` REST resource. Phase 8 QA found this inflated the test surface with no clear UX benefit. What should HLD choose for Create/Update?
- **Options presented**:
  - (A) **Separate mapping endpoints** — `POST /benefitCategorySlabMappings`, `DELETE /benefitCategorySlabMappings/{id}` ; clean DDD but more endpoints, more test surface, admin UI must orchestrate multiple calls.
  - (B) **Embed `slabIds` in parent DTO; server diff-and-apply** — Create/Update request carries `slabIds: List<Integer>` (full desired state); server diffs against current active mappings, INSERT new, soft-delete removed. Single transaction, single endpoint call from client.
  - (C) **Hybrid** — embed on Create only, separate endpoints for subsequent mapping edits.
- **Recommendation**: **(B)** — rationale: matches Maya persona mental model from 00-ba.md ("I edit category, I pick slabs, I save"); single-endpoint UX; reduces test surface and cross-repo fan-out; aligns with D-33 no-optimistic-lock posture (simpler concurrency story).
- **User answer**: **B** — Embed `slabIds`, server-side diff-and-apply.
- **Decision recorded**: **D-35** — 5 endpoints on `/v3/benefitCategories`: POST (create), PUT (update), GET by id, GET list, PATCH /{id}/activate (PATCH /{id}/deactivate confirmed in D-36). Validation: Layer 1 `@NotNull @Size(min=1)` on Create, `@NotNull` only on Update (min=1 enforced at facade); Layer 2 silent dedup via `LinkedHashSet<>(slabIds)`; cross-check against `ProgramSlab` existence per org+program (non-existent or wrong-program → 409).
- **Re-add semantics**: re-adding a previously-unmapped slabId INSERTs new mapping row (does NOT reactivate soft-deleted row); newest `is_active=true` row is authoritative.
- **Cascade-deactivate**: on `PATCH /{id}/deactivate`, all active mappings soft-delete in same transaction (D-06 preserved). On `PATCH /{id}/activate`, mappings do NOT auto-reactivate (D-34 clause b).
- **Downstream impact**:
  - Phase 6 `/architect` writes ADR-003 with flow diagrams (create, update-diff-apply, cascade-deactivate)
  - Phase 7 Designer produces `syncSlabMappings(categoryId, newIdSet)` facade pseudocode + bulk DAO methods (`findMissingIdsForProgram`, `softDeleteAllByCategoryId`)
  - Phase 8 QA exercises dedup, cross-program rejection, re-add-as-insert, GET-returns-active-only
- **Thrift IDL impact**: +0 mapping-specific methods; `createBenefitCategory` and `updateBenefitCategory` structs grow a `list<i32> slabIds` field.
- **Confidence**: C6 — user decision, aligned with D-33 concurrency posture, reduces cross-repo fan-out.

---

**Q-36 — Deactivation Verb (Pre-HLD ADR #4, 2026-04-18)**

- **Question**: Phase 7 v1.1 used `DELETE /{id}` for deactivation; Phase 8 QA noted this is semantically misleading for soft-delete (row survives). HLD must pick a verb.
- **Options presented**:
  - (A) **`PATCH /v3/benefitCategories/{id}/deactivate`** — symmetric mirror of D-34's `/activate`; explicit state-transition sub-path; PATCH correctly conveys "state change" not "erase".
  - (B) **`DELETE /{id}` with soft-delete behaviour** — standard REST verb; conventional but semantically misleading (DELETE implies row removal); creates "why is the row still there?" class of future bugs.
  - (C) **`PUT /{id}` with `isActive: false` in body** — reuses PUT; bends PUT semantics (PUT is for updates, not state flips); asymmetric with D-34 reactivation.
- **Recommendation**: **(A)** — rationale: symmetric with D-34 `/activate`; accurately conveys soft-delete semantics; state-transition sub-paths form an obvious pair any API consumer can pattern-match; tiny "REST purity" cost easily defended in ADR.
- **User answer**: **A** — `PATCH /{id}/deactivate`.
- **Decision recorded**: **D-36** — PATCH endpoint; flips `isActive=true → false`; cascades to all active mappings (D-06 preserved — soft-delete in same transaction via bulk UPDATE); returns 204 on success; 404 on non-existent; idempotency on already-deactivated deferred to `/architect` (default: 204 no-op unless argued otherwise).
- **D-27 alignment**: fully consistent — PUT on inactive still = 409; deactivation is own explicit verb; reactivation is own explicit verb (D-34).
- **Thrift IDL impact**: `deactivateBenefitCategory(orgId, categoryId, actorUserId)` method — mirrors `activateBenefitCategory`.
- **Downstream impact**:
  - Phase 6 `/architect` writes ADR-004 with verb choice rationale + cascade-deactivate flow diagram
  - Phase 7 Designer adds `deactivateBenefitCategory` facade with bulk cascade soft-delete SQL + Thrift handler stub + REST controller `@PatchMapping("/{id}/deactivate")`
  - Phase 8 QA exercises happy deactivate, already-deactivated idempotency (per /architect's choice), cascade verification (mappings → inactive), 404 on non-existent
- **Confidence**: C6 — user decision, clean REST semantic, symmetric with D-34.

---

**Pre-HLD ADR Commit Summary**

| # | Question | User Choice | Decision | Confidence | Freezes for Phase 6 |
|---|----------|-------------|----------|-----------|---------------------|
| 1 | Optimistic-lock stance | C (no lock) | D-33 | C6 | No `@Version`; accept G-10 deviation |
| 2 | Reactivation path | A (PATCH /{id}/activate) | D-34 | C6 | US-6 in scope; D-27 reworded |
| 3 | REST surface granularity | B (embed slabIds, diff-and-apply) | D-35 | C6 | 5 endpoints; `syncSlabMappings` pattern |
| 4 | Deactivation verb | A (PATCH /{id}/deactivate) | D-36 | C6 | Symmetric with /activate; DELETE rejected |

**Constraint on `/architect`**: D-33..D-36 are **non-debatable inputs**. `/architect` incorporates them verbatim as ADR-001..ADR-004 in `01-architect.md`, writes supporting flow diagrams, and designs the remainder of HLD _around_ these fixed choices (not over them).

### Phase 6 (Architect) Decisions — Gate Questions Resolved (2026-04-18)

Architect produced `01-architect.md` (1012 lines, 13 ADRs — 4 frozen D-33..D-36 incorporated verbatim + 9 new). Architect flagged 4 user-sign-off questions that had to be answered before Phase 7 could proceed. User answered: **Q1:B, Q2:B, Q3:B, Q4:C**. Two of the four (Q2, Q3) OVERRIDE the Architect's default — ADR-006 and ADR-012 amended in-place.

---

**Q-37 — Authorization on benefit-category writes (Phase 6 gate Q1, 2026-04-18)**

- **Question**: Admin-only gate via `@PreAuthorize('ADMIN_USER')` or any authenticated BasicAndKey caller?
- **Options presented**:
  - (A) `@PreAuthorize('ADMIN_USER')` — admin-only gate, stricter
  - (B) Any authenticated BasicAndKey caller — pattern-matches legacy `/benefits`, `UnifiedPromotionController`, `TargetGroupController` (Architect recommendation)
  - (C) Other (feature-flag + role check, etc.)
- **Recommendation**: **(B)** — consistent with existing v3 conventions; admin-only layerable later as a separate epic.
- **User answer**: **B** — confirms platform-default BasicAndKey.
- **Decision recorded**: **D-37** — no admin-only gate in MVP. ADR-010 CONFIRMED unchanged; confidence upgraded C5 → C6.
- **Downstream impact**:
  - Phase 7 Designer: `BenefitCategoriesV3Controller` uses `@BasicAndKey` on writes, `@KeyOnly OR @BasicAndKey` on reads. No `@PreAuthorize`.
  - Phase 8 QA: No role-based authz scenarios; orgId-scoping IT (cross-tenant) covers the multi-tenant path.
- **Confidence**: C6 (user confirmed default).

---

**Q-38 — Uniqueness-race mitigation (Phase 6 gate Q2, 2026-04-18)**

- **Question**: How should the `SELECT check_active_duplicate → INSERT new row` race for `(org_id, program_id, name)` be mitigated?
- **Options presented**:
  - (A) MySQL `GET_LOCK('bc:{orgId}:{programId}:{name}', 2)` advisory lock — 2s timeout → 409 `BC_NAME_LOCK_TIMEOUT`. (ADR-012 default, C4)
  - (B) Accept the race at D-26 SMALL scale; monitor; revisit only if incidents occur
  - (C) Partial unique index — requires Aurora MySQL ≥ 8.0.13 (conditional on Q4)
- **Recommendation**: Architect ADR-012 default was **(A)** but **(B)** defensible if consistent with D-33 philosophy.
- **User answer**: **B** — accept the race. OVERRIDES ADR-012 default.
- **Decision recorded**: **D-38** — no advisory lock, no partial unique index, no `BC_NAME_LOCK_TIMEOUT` error code in MVP. App-layer check only. Revisit triggers: (a) admin QPS >5/sec sustained; (b) ≥1 real duplicate-name incident in production logs; (c) product requires strict uniqueness guarantee.
- **Rationale** (user-aligned with D-33): D-26 admin-write QPS <1/s → collision probability vanishingly small; advisory-lock ceremony adds MySQL-level complexity and a new failure mode for a race unlikely to materialize; consistent with accepted-deviation philosophy of D-33.
- **Downstream impact**:
  - **ADR-012 AMENDED** — advisory lock mechanism stricken from HLD; replaced with app-layer check + accepted-deviation marker.
  - **Create flow Mermaid (§5.1)** — `GET_LOCK`/`RELEASE_LOCK` steps removed; note added.
  - **API table (§8)** — `BC_NAME_LOCK_TIMEOUT` stripped from POST error codes.
  - **Risk Register** — R-03 severity lowered HIGH → MEDIUM with explicit accepted-deviation flag. Summary now: 2 CRITICAL / 2 HIGH / 5 MEDIUM / 3 LOW.
  - **Guardrail Matrix** — G-10.5 changed from "mitigated via advisory lock" to "accepted deviation with revisit-triggers".
  - Phase 7 Designer: `BenefitCategoryFacade.create()` = simple `findActiveByName → INSERT`; no `GET_LOCK`.
  - Phase 8 QA: No advisory-lock timeout scenarios; explicit note "SELECT→INSERT race accepted per D-38; not asserted".
- **Confidence**: C6 — internally consistent with D-33.

---

**Q-39 — `/activate` response body (Phase 6 gate Q3, 2026-04-18)**

- **Question**: `PATCH /activate` happy response — 204 No Content (symmetric with `/deactivate`) or 200 + `BenefitCategoryResponse` DTO (client convenience)?
- **Options presented**:
  - (A) 204 No Content — symmetric with `/deactivate` (ADR-006 default)
  - (B) 200 OK + DTO — saves client a GET round-trip; asymmetric
- **Recommendation**: Architect ADR-006 default was **(A)** for symmetry.
- **User answer**: **B** — 200 + DTO on activate. OVERRIDES ADR-006 default. Deliberate asymmetry.
- **Decision recorded**: **D-39** — `/activate` happy = 200 + DTO; `/deactivate` happy = 204; both idempotency paths = 204.
- **Rationale**: Activation typically precedes further admin edits — returning DTO avoids mandatory second GET. Deactivation is typically terminal — no meaningful post-state to show. Idempotency collapses to 204 on both (no state change).
- **Downstream impact**:
  - **ADR-006 AMENDED** — asymmetric happy path; idempotent paths unchanged.
  - **API table (§8)** — Row 5 (`/activate`) response updated.
  - **Thrift IDL** — `activateBenefitCategory` returns `BenefitCategory` struct (not `void`); `deactivateBenefitCategory` remains `void`.
  - **Facade signature** — `activate()` returns `Optional<BenefitCategoryResponse>`; empty → 204, populated → 200+body.
  - Phase 8 QA: Assert 200+DTO on happy activate; 204 on idempotent already-active; 204 on happy/idempotent deactivate.
- **Confidence**: C6 — asymmetry trade-off explicitly acknowledged.

---

**Q-40 — Aurora MySQL version confirmation (Phase 6 gate Q4, 2026-04-18)**

- **Question**: Production Aurora MySQL version — ≥ 8.0.13 or below? Needed for ADR-012 partial-unique-index fallback viability.
- **Options presented**:
  - (A) ≥ 8.0.13 — partial unique index is a usable future fallback
  - (B) < 8.0.13 — only advisory lock or app-layer check available
  - (C) Don't know — defer to Phase 12 Blueprint deployment runbook
- **Recommendation**: Non-blocking for Phase 7 regardless; answer C acceptable.
- **User answer**: **C** — deferred to Phase 12.
- **Decision recorded**: **D-40** — Phase 12 deployment runbook confirms Aurora version. ADR-012 "Future Remediation" note kept; partial unique index option conditional on version check.
- **Why non-blocking**: D-38 (accept the race) upstream removed advisory-lock vs partial-index decision from critical path. MVP doesn't use either mechanism.
- **Downstream impact**:
  - Phase 7: None.
  - Phase 12: Blueprint runbook step — "confirm Aurora MySQL version ≥ 8.0.13 to preserve partial-unique-index remediation option".
- **Confidence**: C6 — acceptable deferral.

---

**Phase 6 Gate Resolution Summary**

| # | Question | User Choice | Decision | Deviation from Architect Default? | Confidence |
|---|----------|-------------|----------|-----------------------------------|-----------|
| Q1 | Authz admin-only vs BasicAndKey | B | D-37 | No — confirms default | C6 |
| Q2 | Uniqueness-race mitigation | B | D-38 | **YES — overrides ADR-012 default (A)** | C6 |
| Q3 | `/activate` response body | B | D-39 | **YES — overrides ADR-006 default (A)** | C6 |
| Q4 | Aurora MySQL version | C | D-40 | No — acceptable deferral | C6 |

**2 of 4 overrides**: D-38 and D-39 represent the user's independent judgment — D-38 extends D-33 philosophy (accept small-scale risk); D-39 trades symmetry for client UX. Both amendments are surgically applied in-place to `01-architect.md`.

### Phase 7 (Designer) Decisions

Designer ran as opus subagent, ~568s, 24 tool uses. Produced `03-designer.md` (1230 lines, 7 sections + appendix). Step 0 Codebase Pattern Discovery strictly applied — 17 patterns P-01..P-17 anchored to file:line exemplars.

**Architect Phase-6 open questions resolved by Designer** (no user input required — pure codebase research):

| Q | Resolution | Evidence Anchor | Confidence |
|---|-----------|-----------------|-----------|
| Q7-03 Facade class name | `BenefitCategoryFacade` (intouch-api-v3 convention) | code-analysis-intouch-api-v3 | C5 |
| Q7-04 Controller package | `resources` | code-analysis-intouch-api-v3 | C5 |
| Q7-05 List wrapper | `BenefitCategoryListPayload` inside `ResponseWrapper.data` | `ResponseWrapper<T>` platform convention | C5 |
| Q7-06 Thrift timestamp names | bare `createdOn`/`updatedOn` (NOT `*InMillis`) | `pointsengine_rules.thrift` convention | C6 |
| Q7-07 Activate response | superseded by D-39 — 200+DTO on state change / 204 idempotent | D-39 | C6 |
| Q7-10 Audit timestamp write | manual `new Date()` in service (NOT `@PrePersist`) | `Benefits.java` + platform convention | C6 |
| Q7-01 Name normalization (partial) | `.trim()` + case-sensitive; max length TBD Phase 8 | Platform convention | C5 (partial) |

**Architect Phase-6 questions moot**:
- Q7-02 (advisory-lock key hashing) — killed by D-38 (no lock)
- Q7-08 (IT fixture strategy) — Phase 9 SDET concern
- Q7-09 (Aurora version) — deferred by D-40

**Designer assumptions flagged** (13 at C5, listed in §G of `03-designer.md` — mostly style-level, ready for user review at or before Phase 10): facade suffix, controller package, list payload naming, bare Thrift timestamps, manual Date, `.trim()`+case-sensitive, `isActive=all` sentinel, `Math.toIntExact` cast, 204 on idempotent activate, filter carries orgId, FK column name, `ConflictException(code, message)` ctor, `PeProgramSlabDao` batch method addition.

**New Designer open questions Q7-11..Q7-15** (to be resolved before Phase 10 Developer; non-blocking for Phase 9 SDET RED):

| Q | Question | Designer Default | Confidence |
|---|----------|------------------|-----------|
| Q7-11 | Does `PeProgramSlabDao.findMissingIdsForProgram` already exist? | Add new method if absent | C4 — needs verification |
| Q7-12 | GET by id — active-only or active+inactive | Active-only; `?includeInactive=true` for audit | C4 — product decision |
| Q7-13 | Activate no-op signalling | `Optional<BenefitCategoryResponse>` at Facade | C5 — Designer prefers |
| Q7-14 | Entity boilerplate | Hand-written getters/setters (no Lombok) | C5 — style |
| Q7-15 | DTO↔Thrift mapper placement | intouch-api-v3 facade package `*Mapper` | C5 — style |

**New constraints**: C-35 (hand-written entity boilerplate), C-36 (mapper class placement), C-37 (manual `new Date()` — resolves Q7-10), C-38 (bare Thrift timestamp names — resolves Q7-06).

**Hard-constraint honour verification** (all 8 pre-Designer frozen decisions reified in signatures):
- D-33 → no `@Version` column on either entity
- D-34 + D-36 → dedicated `/activate` + `/deactivate` endpoints
- D-35 → `slabIds: List<Integer>` on Create/Update requests + `syncSlabMappings` pseudocode
- D-37 → no `@PreAuthorize` annotations; `@SecuredResource` + BasicAndKey only
- D-38 → `BenefitCategoryFacade.create` does `findActiveByNameAndOrgAndProgram → INSERT` only; no `GET_LOCK`
- D-39 → Facade returns `Optional<BenefitCategoryResponse>`; Thrift IDL: `activateBenefitCategory` returns struct (not void); deactivate returns void
- D-40 → no Aurora version dependency in Designer output

**RED-phase readiness**: true. SDET Phase 9 can generate skeleton production classes + failing tests directly from `03-designer.md` §F compile-safe signatures.

**Pause point for user review**: Q7-11..Q7-15 don't block Phase 9 SDET RED. Recommend: proceed to Phase 8 (QA) and Phase 9 (SDET) in sequence; present Q7-11..Q7-15 to user for decision before Phase 10 Developer starts writing production bodies.

### Phase 7 Designer Question Resolutions (2026-04-18)

User input: `resolve Q7-NN` → `Q7:C, Q12:A, Q13:A, Q14:A, Q15:A`.

Each resolution below records: the question, evidence gathered before presenting options, options table, orchestrator recommendation with rationale, user answer, match-with-recommendation flag, resulting decision ID, and amendments.

---

#### Q7-11 — `PeProgramSlabDao` — batch-existence method?

**Question**: Does `PeProgramSlabDao` already expose a batch "given a set of candidate slabIds, return which exist for this (orgId, programId)" method? If not, add one on that DAO as [MODIFIED].

**Evidence gathered (before asking user)**:
- Read `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeProgramSlabDao.java` — confirmed only 3 methods exist:
  - `findByProgram(int orgId, int programId) → List<ProgramSlab>` — returns ALL slabs
  - `findByProgramSlabNumber(int orgId, int programId, int serial) → ProgramSlab`
  - `findNumberOfSlabs(int orgId, int programId) → Long`
  - **NO batch-existence variant**. Evidence C7.
- Cross-referenced D-26 (SMALL-scale envelope: ≤10 slabs typical, hard cap small).

**Options presented**:

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A** | Add new DAO method `findMissingIdsForProgram(orgId, programId, List<Integer> candidates) → List<Integer>` via JPQL `IN (:candidates)` | Single DB round-trip; O(candidates) memory | Cross-repo modification; more surface area to test |
| **B** | Use Spring Data derived query `findByPkOrgIdAndProgramPkIdAndPkIdIn(...)` | No custom @Query | Still cross-repo modification |
| **C** | Reuse existing `findByProgram` + in-memory Set ops | Zero cross-repo modification; reuses proven method | Transfers N slabs (≤ hard cap, typically ≤10) instead of O(candidates); still O(1) round-trip |

**Orchestrator recommendation**: **C**.

**Rationale**: D-26 SMALL-scale envelope makes in-memory filtering negligible. Avoids cross-repo blast radius. If future programs ever exceed 100 slabs, revisit with A or B.

**User answer**: **C**.
**Match with recommendation**: ✅ Match.
**Decision ID**: **D-41**.

**Amendments to 03-designer.md**: §B.1 create-slab-validation pseudocode rewritten to use `findByProgram` + `Set<Integer>` subtraction; §G.2 A7-13 struck; §A.2 DAO row 14 unchanged.

---

#### Q7-12 — GET /{id}: active-only vs active+inactive?

**Question**: For `GET /v3/benefitCategories/{id}`, does the endpoint return (a) active-only by default with `?includeInactive=true` opt-in, (b) active-only always (no query param), or (c) active+inactive always?

**Evidence gathered**:
- D-27 (writes on inactive forbidden — 409), D-28 (uniqueness among active), D-26 (SMALL scale). None directly answer the GET visibility question.
- ADR-010/D-37 (auth): no role-based gate; any authenticated caller can GET. An audit path would be accessible to any admin with API key.
- Designer's §G.1 C4 default: active+inactive on GET; active-only for mutations.

**Options presented**:

| Option | Default | Audit path | YAGNI verdict |
|--------|---------|-----------|----------------|
| **A** | Active-only | `?includeInactive=true` opt-in | Richer; supports audit without new endpoint later |
| **B** | Active-only always | Not supported; add endpoint later if needed | Simplest; MVP-posture |
| **C** | Active+inactive always | N/A | Exposes soft-deleted as first-class |

**Orchestrator recommendation**: **B** (active-only always, no query param).

**Rationale**: YAGNI at D-26 SMALL scale. No audit requirement surfaced in BRD/PRD. Opt-in can be added later as additive non-breaking change.

**User answer**: **A**.
**Match with recommendation**: ❌ **OVERRIDE**. User preferred the richer API surface. Inferred reasoning: audit access is a likely operational need; deferring to a future ticket introduces friction for support teams.
**Decision ID**: **D-42**.

**Amendments to 03-designer.md**:
- §B.3 → controller `get()` gains `@RequestParam includeInactive` (default false); facade `get(orgId, id, includeInactive)`; Thrift IDL `getBenefitCategory` gains optional `bool includeInactive = false` (field 3); DAO split into `findByOrgIdAndId` (any state) + `findActiveByOrgIdAndId` (active only).
- §F.3 service, §F.5 handler, §F.6 facade, §F.7 controller, §F.10 IDL signatures all updated.
- **Mutation paths unchanged** — update/activate/deactivate still use `findActiveByOrgIdAndId` per D-27.
- New constraint **C-39** captures the rule.

---

#### Q7-13 — Activate idempotent no-op signalling?

**Question**: How does EMF signal "no state change" on `activateBenefitCategory` so the facade can return `Optional.empty()` → controller emits 204?

**Options presented**:

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A** | `BenefitCategoryDto.stateChanged: bool` field (Thrift field 12, `optional bool stateChanged = true`). EMF sets false on no-op; facade detects → `Optional.empty()`. | Single-return-type Thrift method; explicit sentinel; default-true keeps future clients working. | Field used only by this one method. |
| **B** | EMF throws `PointsEngineRuleServiceException(statusCode=304, errorMessage="ALREADY_ACTIVE")`. Facade catches → `Optional.empty()`. | Reuses exception infrastructure. | HTTP 304 is not idiomatic on PATCH; conflates success-no-op with error-like path. |
| **C** | EMF returns `null`. Facade checks `result == null` → `Optional.empty()`. | Minimal surface area. | Violates Thrift `required` return semantics — `BenefitCategoryDto` is declared non-nullable in Thrift Java generation. |

**Orchestrator recommendation**: **A**.

**Rationale**: Least-invasive while preserving Thrift contract correctness. Clean additive IDL change.

**User answer**: **A**.
**Match with recommendation**: ✅ Match.
**Decision ID**: **D-43**.

**Amendments to 03-designer.md**: §F.10 IDL already contains `12: optional bool stateChanged = true`; §B.5 already describes the sentinel. Confirmed authoritative — no further edits needed.

---

#### Q7-14 — Entity/DTO boilerplate: hand-written vs Lombok?

**Question**: Should JPA entities (emf-parent) and/or REST DTOs (intouch-api-v3) use Lombok `@Getter @Setter`, or hand-written getters/setters?

**Evidence gathered**:
- `grep -l "@Getter\|@Setter" <intouch-api-v3>` → **305 files** use Lombok. Established platform pattern.
- Inspection of `Benefits.java` + other emf-parent JPA entities → **0 Lombok annotations**. Hand-written is the emf-parent JPA convention.
- Known JPA-provider concern: Lombok on `@Embeddable` PK classes has historically caused equality/hash contract issues.

**Options presented**:

| Option | JPA entities (emf-parent) | REST DTOs (intouch-api-v3) | Rationale |
|--------|---------------------------|----------------------------|-----------|
| **A** | Hand-written | Lombok | Split convention — matches each repo's established platform pattern. Safest for JPA `@Embeddable` PKs. |
| **B** | Lombok | Lombok | Uniform Lombok; less code. Deviates from emf-parent JPA convention. |
| **C** | Hand-written | Hand-written | Uniform hand-written; deviates from 305-file intouch-api-v3 precedent. Most verbose. |

**Orchestrator recommendation**: **A**.

**Rationale**: Each repo's established pattern preserved. JPA stays safely hand-written around `@Embeddable` PK contract. DTOs leverage existing 305-file Lombok precedent.

**User answer**: **A**.
**Match with recommendation**: ✅ Match.
**Decision ID**: **D-44**.

**Amendments to 03-designer.md**:
- §A.3 rows 22-25 → annotations column lists `@Getter @Setter` (Lombok — D-44).
- §F.8 DTO code block → `import lombok.Getter; import lombok.Setter;`; each DTO class annotated `@Getter @Setter`; "// getters + setters" comments dropped.
- emf-parent entities (§A.2 rows 8-12, §F.2) unchanged — stays hand-written per P-01.
- Constraint **C-35** amended in session-memory to reflect the split convention.

---

#### Q7-15 — DTO↔Thrift mapper placement?

**Question**: Where does the DTO↔Thrift mapper class live? Options: (a) dedicated `mapper/` subpackage with `@Component` class, (b) inline static methods on facade, (c) facade package with `*Mapper` suffix.

**Evidence gathered**:
- Located existing platform exemplar: `intouch-api-v3/.../unified/promotion/mapper/CustomerPromotionResponseMapper.java` — dedicated mapper in `mapper/` subpackage, `@Component`, stateless.
- Designer's C5 default was "dedicated `*Mapper` in facade package" (option C — close but wrong package).

**Options presented**:

| Option | Location | SDET-testability | Pattern match |
|--------|----------|------------------|---------------|
| **A** | Dedicated `com.capillary.intouchapiv3.facade.benefitCategory.mapper.BenefitCategoryResponseMapper` | Excellent — unit-testable without Spring context | Matches `CustomerPromotionResponseMapper` exemplar |
| **B** | Inline static methods on `BenefitCategoryFacade` | Poor — facade has RPC wiring; mapping is hard to unit-test independently | No exemplar |
| **C** | `com.capillary.intouchapiv3.facade.benefitCategory.BenefitCategoryMapper` (facade package, not sub-package) | Good | Matches Designer's earlier default but NOT the verified exemplar |

**Orchestrator recommendation**: **A**.

**Rationale**: Exemplar match (`CustomerPromotionResponseMapper`) is the current platform pattern. Clean isolated unit test for UTC timestamp conversion (ADR-008), critical for multi-timezone requirements (G-01.7).

**User answer**: **A**.
**Match with recommendation**: ✅ Match.
**Decision ID**: **D-45**.

**Amendments to 03-designer.md**:
- §A.3 → NEW row 27a for `BenefitCategoryResponseMapper` in `mapper/` subpackage.
- §A.5 summary: 26 → 27 new artifacts.
- §F.6 facade constructor comment updated to reference dedicated mapper.
- NEW §F.6a: mapper class contract with full method signatures (toResponse, toCreateDto, toUpdateDto, toListPayload, millisToDate, dateToMillis helpers).
- Constraint **C-36** amended in session-memory to reflect dedicated `mapper/` subpackage.

---

### Phase 7 Gap Routing Decisions (Designer questions)

None applicable — all 5 questions went directly to user for explicit decision. No "accept risk" paths taken.

### Phase 11 (Reviewer Gap Routing) Decisions

_Pending._

---

## Accepted Risks

_(If user chose [A] Accept during Phase 11 findings routing, logged here with reasoning.)_

| # | Finding | User Reasoning | Phase |
|---|---------|----------------|-------|

## Phase 8 QA Question Resolutions (2026-04-18)

Protocol: Phase 8 QA subagent produced 77 scenarios + 3 open questions (Q8-01..Q8-03) + 4 C5+ assumptions (A8-01..A8-04). Orchestrator presented the 3 questions with evidence-gathered options and recommendations. User answered in batch `Q8-01: b, Q8-02: a, Q8-03: c`.

---

### Q8-01 — Empty slabIds on PUT: allowed (clears mappings) or rejected with 400?

**Evidence gathered**:
- Designer §F.8 `BenefitCategoryUpdateRequest.slabIds` annotated `@NotNull` without `@Size(min=1)` (asymmetric with CreateRequest which has `@Size(min=1)`)
- BA/PRD do not explicitly call out "category must have ≥1 slab" invariant
- D-35 (HLD) diff-and-apply behaviour would technically permit "diff to empty set → soft-delete all"
- QA-032 was originally written to document the permissive behaviour

**Options presented**:
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| a | Allow empty (current DTO annotations) | Admin can temporarily zero out a category | A category with 0 slabs is semantically meaningless; divergent from Create |
| b | Reject 400 (add `@Size(min=1)`) | Symmetric with Create; enforces invariant | Admin cannot "clear slabs" via PUT — must use `PATCH /deactivate` |
| c | Reject 409 (`BC_EMPTY_MAPPING` code) | Explicit business rule violation | Yet another error code; adds complexity |

**Orchestrator recommendation**: **(b) Reject 400** — semantic integrity + validation symmetry + simpler service logic.

**User answer**: **b — Reject with 400** ✅ Matches recommendation.

**Decision ID**: **D-46**

**Amendments applied**:
- `03-designer.md` §A.3 row 23 — annotation updated to `@NotNull @Size(min=1)` on UpdateRequest.slabIds
- `03-designer.md` §F.8 — code block updated with `@Size(min=1)` and D-46 comment
- `03-designer.md` §19.1 — new subsection documenting D-46
- `04-qa.md` QA-032 — expected behaviour flipped from "200 state change" to "HTTP 200 + VALIDATION_FAILED envelope" (platform quirk OQ-45); priority bumped P1 → P0
- Session memory — C-40 (NEW) added as constraint; A8-01 superseded

---

### Q8-02 — Name uniqueness: case-sensitive or case-insensitive?

**Evidence gathered**:
- Designer A7-06 (C5 assumption): case-sensitive; no `LOWER()` wrapper in DAO query
- Current query: `findActiveByNameAndOrgAndProgram(orgId, programId, name)` uses `name = ?`
- Unique index on `benefit_categories (org_id, program_id, name)` is byte-comparison (default MySQL collation)
- BA/PRD user stories do not specify casing convention for category names
- Aurora/MySQL functional index on `LOWER(name)` requires version check (Q4/D-40 deferred)

**Options presented**:
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| a | Case-sensitive (current) | Zero code change; matches Designer; defers Aurora version check | "VIP" vs "vip" subtle dupes possible — admin UX friction |
| b | Case-insensitive (LOWER wrapper) | Cleaner admin UX; prevents confusion | Requires DDL change (`ALTER TABLE ... LOWER(name)` index); Aurora version check needed; larger scope |

**Orchestrator recommendation**: **(b) Case-insensitive** — admin UX priority for user-facing names.

**User answer**: **a — Case-sensitive** ⚠ **OVERRIDE of orchestrator recommendation b**.

**Inferred rationale (user did not state)**:
- Backward compatibility with loyalty platform byte-comparison convention across the codebase
- Keeps ticket scope narrow (no DDL, no Aurora version dependency)
- If case-insensitivity becomes a product requirement post-GA, forward migration (ALTER INDEX + backfill-dedupe) is straightforward
- Loyalty admins are typically more disciplined with their naming than generic CRUD consumers

**Decision ID**: **D-47**

**Amendments applied**:
- `03-designer.md` §19.2 — new subsection documenting D-47 (user override)
- `04-qa.md` QA-004 — case-sensitivity note added; SDET triggered to add QA-004b (case-distinct dup succeeds 201)
- Session memory — A8-02 promoted from C5 assumption to C6 decision D-47
- No code changes needed — DAO query and index already case-sensitive

**Revisit trigger** (logged in session memory): if admin support team raises ≥1 "subtle-case duplicate name" ticket post-GA, migrate to case-insensitive index in a follow-up ticket.

---

### Q8-03 — Error code for `?isActive=foo` invalid filter value?

**Evidence gathered**:
- A7-07 (Designer C5 assumption): HTTP 400 with `BC_BAD_ACTIVE_FILTER` code — but the exact string was never confirmed
- ADR-009 (HLD error taxonomy): no row for this scenario
- `TargetGroupErrorAdvice` platform exception handler exists and maps `MethodArgumentTypeMismatchException` → `VALIDATION_FAILED` envelope
- Spring MVC's `@RequestParam` boolean coercion throws `MethodArgumentTypeMismatchException` for non-`true`/`false` values

**Options presented**:
| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| a | `BC_BAD_ACTIVE_FILTER` (bespoke) | Descriptive, follows BC_* convention | Yet another error constant; YAGNI |
| b | `BC_INVALID_QUERY_PARAM` (generic) | Reusable for future filters | Still bespoke; no current reuse need |
| c | Platform `VALIDATION_FAILED` (reuse `TargetGroupErrorAdvice`) | No new code; leverages existing infra | Error code less descriptive |

**Orchestrator recommendation**: **(c) Reuse platform `VALIDATION_FAILED`** — YAGNI; only one filter, one failure mode.

**User answer**: **c — Platform `VALIDATION_FAILED`** ✅ Matches recommendation.

**Decision ID**: **D-48**

**Amendments applied**:
- `03-designer.md` §19.3 — new subsection documenting D-48
- `03-designer.md` §E (error taxonomy) — Phase 11 Reviewer task to strike `BC_BAD_ACTIVE_FILTER`; note platform `VALIDATION_FAILED` used
- `04-qa.md` §11 Error Coverage Matrix — `BC_BAD_ACTIVE_FILTER` row replaced with `VALIDATION_FAILED` row referencing QA-022b
- `04-qa.md` §13 — new QA-022b scenario ("?isActive=foo → VALIDATION_FAILED") seeded for SDET Phase 9
- ADR-009 amendment deferred to Phase 11 Reviewer per standard pipeline protocol
- Phase 10 Developer: no new error code constant needed; controller declares `@RequestParam(required=false) Boolean isActive` and lets Spring converter throw

---

### Summary

| Q# | Answer | Decision | Match Reco? |
|----|--------|----------|-------------|
| Q8-01 | b | D-46 | ✅ Matched |
| Q8-02 | a | D-47 | ⚠ Override |
| Q8-03 | c | D-48 | ✅ Matched |

**Impact on scenario count**: 77 → **79** (added QA-004b case-distinct dup, QA-022b platform validation).
**Impact on priority distribution**: 47 P0 → **48 P0** (QA-032 bumped P1→P0); 23 P1 → **23 P1** (QA-032 out, QA-004b in); 7 P2 → **8 P2** (QA-022b added).

---

## Phase 10b — Backend Readiness Findings (2026-04-19)

Audit verdict: **NOT READY** — 3 HIGH blockers surfaced; 29 PASS · 6 WARN · 3 FAIL. User triaged all three blockers as **[M] Manual** — will fix outside the pipeline. Pipeline proceeds to Phase 10c on the user's directive.

| ID | Severity | Finding | Anchor | Routing | Status |
|---|---|---|---|---|---|
| B1 | HIGH | Production DDL missing `idx_bc_org_program_name` index; every D-60 name-reservation lookup full-scans the (org, program) partition | `cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql:16` | **[M] Manual** | pending user fix |
| B2 | HIGH | Production DDL uses bare `CREATE TABLE`; re-deploy / rollback-forward will fail with "table already exists". IT DDL already uses `IF NOT EXISTS` | `benefit_categories.sql:3`, `benefit_category_slab_mapping.sql:3` | **[M] Manual** | pending user fix |
| B3 | HIGH | `BenefitCategoryResponse.active` serializes as JSON `"active"`; API contract + Thrift DTO use `"isActive"`. UI consumers silently receive null | `intouch-api-v3 .../BenefitCategoryResponse.java:27` | **[M] Manual** | pending user fix |

**Rationale for Manual over Re-run**: user chose to fix all three outside the pipeline rather than spawn another Developer round. All three are 1-line changes with clear evidence; no design ambiguity. Tracked as outstanding items for Phase 11 Reviewer verification.

---

## Phase 10c — Compliance Findings (2026-04-19)

Audit found **0 FAIL · 1 HIGH · 2 MEDIUM · 1 WARN** (+42 PASS, 5 accepted-deviations). User routed per-finding:

| ID | Severity | Finding | Routing | Status |
|---|---|---|---|---|
| F-01 | HIGH | `/activate` + `/deactivate` use `@PostMapping` not `@PatchMapping` (ADR-002 / ADR-004 specify PATCH; PATCH callers will 405) | **[A] Accept** | **D-61 — accepted deviation** |
| F-02 | MEDIUM | `BenefitCategoryResponseMapper` in `models.dtos.benefitcategory` not mandated `facade.benefitCategory.mapper` (D-45 / C-36) | **[M] Manual** | pending user fix |
| F-03 | MEDIUM | Silent 200-clamp instead of `BC_PAGE_SIZE_EXCEEDED` throw at `size > 100` (ADR-011) | **[R] Re-run (partial)** | service-side throw landed (emf-parent M6 `5caa9a9362`); controller `@Max(100)` gate **not applied** per user directive "don't change listBenefitCategories" → service-layer throw only fires for direct Thrift callers with size > 100, REST path unchanged — **D-62** |
| F-04 | WARN | Absent `?isActive` defaults to all-states instead of active-only (D-42 / D-48 intent drift) | **[M] Manual** | pending user fix |

### New decisions

- **D-61 (accepted deviation — F-01)**: `/activate` + `/deactivate` stay on `@PostMapping`. REST clients calling PATCH will receive HTTP 405. Accepted on user directive; Thrift path is the production consumer, REST is aiRa-only. Revisit trigger: any REST client requires PATCH semantics. Confidence C6.
- **D-62 (partial fix — F-03)**: emf-parent service layer throws `BC_PAGE_SIZE_EXCEEDED` (HTTP 400) when `size > 100`; controller has no `@Max(100)` gate per user directive. REST callers unaffected in normal operation (default `size=20`); direct Thrift callers are now bounded. Confidence C5 on API contract, C6 on Thrift boundary.

### Outstanding for Phase 11 Reviewer

- F-02 mapper package (manual)
- F-04 isActive default drift (manual)
- (inherited) Phase 10b B1 / B2 / B3 (manual)

Five items total queued for Reviewer verification.

---

## Phase 11 (Reviewer) Routing

**Verdict**: APPROVED WITH WARNINGS — 1 blocker · 5 warnings · 4 notes

**Routing decisions (user, 2026-04-19)**:

| Finding | Severity | Category | Routing | Reasoning |
|---------|----------|----------|---------|-----------|
| R-01 | BLOCKER | Code Quality | **[M] Manual** | User will remove/deprecate dead `findActiveByProgramAndNameExceptId` DAO method outside pipeline. Not called anywhere at present — risk is latent, not active. |
| R-02 | WARNING | Code Quality | **[M] Manual** | Trivial unused-import cleanup (`jakarta.validation.constraints.Max` in `BenefitCategoryCreateRequest.java:7`) — left over from reverted F-03 controller gate. User handles. |
| R-03 | WARNING | Requirements | **[A] Accept** → **D-63** | `validateSlabsBelongToProgram` returns 400 not 409 (ADR-009). Accept the 400 semantics — slab ownership mismatch is a client-input error, 400 is defensible. ADR-009 to be re-noted in final blueprint. |
| R-05 | WARNING | Security (G-01) | **[A] Accept** | Linked to OQ-38 (JVM timezone policy still open project-wide). Response DTO `@JsonFormat` without explicit `timezone="UTC"` accepted as a project-level question, not feature-specific. |
| R-06 | WARNING | Documentation | **[A] Accept** | `java.util.Date` in response DTO already accepted per D-24. No change. Will re-note in ADR-008 via Phase 12 blueprint. |

**New decisions recorded**:
- **D-63**: `validateSlabsBelongToProgram` returns **HTTP 400** (not 409 as ADR-009 suggested). Slab ownership mismatch is a client-input validation error; 400 is semantically correct. ADR-009 will be annotated in the Phase 12 blueprint.

**No Developer rework cycle triggered.** All items routed to Manual or Accept. Phase 11 closes.

**Outstanding Manual items after Phase 11** (8 total, user-owned):
- From Phase 10b: B1 (idx_bc_org_program_name), B2 (Flyway migration), B3 (@JsonProperty isActive)
- From Phase 10c: F-02 (verb semantics doc), F-04 (isActive default reconciliation)
- From Phase 11: R-01 (dead DAO method), R-02 (unused import)

