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

### Phase 6 (Architect) Decisions

_Pending._

### Phase 11 (Reviewer Gap Routing) Decisions

_Pending._

---

## Accepted Risks

_(If user chose [A] Accept during Phase 11 findings routing, logged here with reasoning.)_

| # | Finding | User Reasoning | Phase |
|---|---------|----------------|-------|
