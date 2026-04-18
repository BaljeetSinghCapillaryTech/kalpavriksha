# Session Memory — Benefit Category CRUD

> **Purpose**: Shared context across all pipeline phases. Updated INCREMENTALLY after every decision/finding — never batch at phase end.
> **Ticket**: CAP-185145
> **Feature**: Benefit Category CRUD
> **Started**: 2026-04-17
> **Branch**: `aidlc/CAP-185145` (across all 5 repos)

---

## Domain Terminology

_(Populated in Phase 1 — BA Deep-Dive)_

| Term | Definition | Source |
|------|------------|--------|
| Benefit Category | Metadata grouping record scoped to a Program. In MVP: holds name, single categoryType value (`BENEFITS`), tierApplicability, isActive. **No reward values, no trigger event.** | BRD §2 (narrowed by D-06/D-07/D-09) _(BA)_ |
| Benefit Instance | A pure (categoryId, tierId) association marking that a category is configured for a specific tier. **Carries NO value payload in MVP** — downstream systems read category+tier association and apply benefits per their own logic. | BRD §2 (narrowed by D-09) _(BA)_ |
| categoryType | Enum column on BenefitCategory. **MVP**: single value `BENEFITS`. Column retained for future extensibility. 9 types from BRD §3 (WELCOME_GIFT, EARN_POINTS, etc.) are deferred. | BRD §3 (narrowed by D-06) _(BA)_ |
| ~~triggerEvent~~ | ❌ **Not modelled in MVP.** Removed by D-07. Any trigger/event semantics live in the external system that reads the config. | — |
| tierApplicability | Array of tierIds indicating which tiers can have configured instances for this category. At least one required. | BRD §2 _(BA)_ |
| Program | Top-level container. A Program contains one or more Tiers. | BRD §2 _(BA)_ |
| Maker-Checker | Approval workflow: DRAFT → PENDING_APPROVAL → ACTIVE. Category creation and instance changes both go through it. | BRD §5 _(BA)_ |
| Matrix View | Benefits dashboard grid — categories as rows, tiers as columns, configured value or "Not configured" in each cell. | BRD AC-BC10 _(BA)_ |
| aiRa | Capillary's conversational AI assistant — maps natural-language intents to categoryType + prompts for value fields. | BRD §8 _(BA)_ |
| Maya | Primary persona — program manager configuring tiers/benefits. | BRD E1/E2 user stories _(BA)_ |
| Benefits (legacy) | Existing `Benefits` entity in emf-parent — promotions-backed, types VOUCHER/POINTS only. Distinct from the new BenefitCategory/BenefitInstance model. | emf-parent: `Benefits.java`, `benefits.sql` _(ProductEx)_ |
| promotion_id | Mandatory FK on the existing `benefits` table linking every benefit to a V3 Promotion. Planned to be decoupled in the new model. | `benefits.sql` NOT NULL constraint _(ProductEx)_ |
| ProgramSlab (the real "Tier") | **The entity the BRD calls "Tier" is physically `ProgramSlab` in table `program_slabs`** with composite PK `(id, org_id)` via `OrgEntityIntegerPKBase`. `SlabInfo` Thrift struct uses `i32`. The new feature's FK target is `program_slabs`, not a "tier" table. _(Phase 2)_ | `emf-parent/.../ProgramSlab.java`, `cc-stack-crm/.../program_slabs.sql`, `pointsengine_rules.thrift:352-361` |
| OrgEntityIntegerPKBase | **Platform standard** for composite PK in loyalty tables. Every comparable entity (`Benefits`, `ProgramSlab`, `PointCategory`, `PartnerProgramTierSyncConfiguration`) extends it. PK is `(int id, int org_id)`, NOT a standalone `long`. _(Phase 2)_ | `Benefits.java:16`, `ProgramSlab.java:39`, `PointCategory.java:32` |
| auto_update_time | **Platform audit pattern** — every table uses MySQL's `auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` instead of an explicit `updated_at` column. Only `promotions` has `last_updated_by`. NO table has `updated_at`/`updated_by`. _(Phase 2)_ | `benefits.sql`, `program_slabs.sql`, `promotions.sql`, etc. |

---

## Key Decisions

_(Populated incrementally — every decision made by the user during Q&A, blocker resolution, architecture approval, etc.)_

| # | Decision | Rationale | Phase | Date |
|---|----------|-----------|-------|------|
| D-01 | Use Superpowers plugin for TDD/brainstorming/parallel-agent workflows | Required by pipeline design | Phase 0 | 2026-04-17 |
| D-02 | Live dashboard enabled | User opted in | Phase 0 | 2026-04-17 |
| D-03 | **Scope**: Category entity CRUD (create, read, update, deactivate, list) + Benefit Instance creation/linking to tiers. aiRa mapping, Matrix View, and Subscription linkage are OUT of scope for this run. | User answered Q1 — "2" | Phase 1 | 2026-04-18 |
| D-04 | **isActive semantics**: `isActive` is a single explicit boolean admin-controlled flag. The BRD §5 prose "a category with no instances is considered Inactive" is treated as descriptive only — NOT a distinct data state. A category with zero instances is still `isActive: true` if created. "Not configured" hints in UI are a presentation concern. | User answered Q2 — "3" | Phase 1 | 2026-04-18 |
| D-05 | **Maker-checker DESCOPED for MVP**. No DRAFT / PENDING_APPROVAL / ACTIVE lifecycle state machine. CRUD operations are immediate — no approval gate. Only `is_active` boolean governs usability. Approval workflow to be added in a later phase/ticket. | User answered Q3 — "4" → "A" | Phase 1 | 2026-04-18 |
| D-06 | **Single categoryType value for MVP**: `BENEFITS`. The 9 types in BRD §3 (WELCOME_GIFT, EARN_POINTS, TIER_BADGE, etc.) are NOT modelled. Column retained as enum (future-proof), populated as BENEFITS for every row today. Multi-type support is future work. | User answered Q4 — "4" → "e" → "keep one enum BENEFITS, drop triggerEvent" | Phase 1 | 2026-04-18 |
| D-07 | **`triggerEvent` field dropped entirely** from both Category and Instance models. No trigger-mapping table from BRD §5.3. No event-derived-from-type logic. | User answered Q4 clarification | Phase 1 | 2026-04-18 |
| D-08 | **Benefit awarding is external** — this system stores config only. An existing system (TBD in Phase 5 — likely EMF tier event forest / TierRenewedHelper etc.) reads this config and applies benefits. No new awarding/calculation logic in MVP. | User answered I-1 → "c" | Phase 1 | 2026-04-18 |
| D-09 | **BenefitInstance carries NO value payload**. Pure (categoryId, tierId) association row + lifecycle metadata (isActive, createdAt, createdBy). No amount, points, voucherTemplateId, text, or JSON config. | User answered I-2 → "e" | Phase 1 | 2026-04-18 |
| D-10 | `categoryType` column kept even though only one value today (YAGNI accepted — future extension without schema change). | User answered I-4 → "a" | Phase 1 | 2026-04-18 |
| D-11 | BRD sections §3 (9 type definitions), §5.3 (trigger mapping), §5.4 (value constraints per type), and parts of AC-BC01 ("correct trigger event derived from categoryType") are **out of scope / deferred** for MVP. BA document will flag these explicitly. | User answered I-3 → "yes" | Phase 1 | 2026-04-18 |
| D-12 | **Strict coexistence with legacy `Benefits` entity.** New `BenefitCategory`/`BenefitInstance` live alongside existing `emf-parent Benefits` in separate tables, packages, service layer. No FK linking them. Glossary in BA doc will spell out the distinction. Unification (if ever) is a future epic. | User answered Q5 — "1" | Phase 1 | 2026-04-18 |
| D-13 | **Soft-delete only for MVP.** No hard-delete endpoint. Removal semantics = `is_active=false` via PATCH. Deactivated categories/instances remain in DB for audit/history. Hard-delete may be added later if operational need emerges. | User answered Q6 — "A2" | Phase 1 | 2026-04-18 |
| D-14 | **Cascade deactivation on category.** When a category's `is_active` flips to false, all child instances' `is_active` flip to false in the same DB transaction. No block-on-active-instances behaviour. Reactivating a category does NOT auto-reactivate instances — those must be re-enabled explicitly (reactivation is a deliberate act per instance). | User answered Q6 — "B1" | Phase 1 | 2026-04-18 |
| D-15 | **Uniqueness**: `categoryName` is unique per-Program, enforced by DB constraint `UNIQUE (program_id, name)`. Tighter boundary than existing `benefits (org_id, name)`. | User confirmed Q7 | Phase 1 | 2026-04-18 |
| D-16 | **Multi-tenancy**: New tables carry both `org_id` (platform-wide tenant isolation) and `program_id` (feature scope). Both indexed. Auth middleware injects org context. | User confirmed Q7 | Phase 1 | 2026-04-18 |
| D-17 | **Phase 3 (UI Requirements Extraction) SKIPPED.** Rationale: (a) v0.app prototype predates Phase 1 scope simplification and likely contains screens/fields now out-of-scope (Matrix View, aiRa, per-type values, subscription picker); (b) UI-embedded design questions (cascade warning, reactivation asymmetry, 409-vs-reactivate) require product decisions in Phase 4, not extraction from a pre-descoped prototype; (c) Phase 4 may resolve OQ-17 to "ship as internal plumbing, no UI" — in which case Phase 3 would have been wasted; (d) If UI is kept, we'll produce an `/api-handoff` document after Phase 7 (Designer) so the UI team designs against a frozen contract rather than we reverse-engineer requirements from an early prototype. | User answer "3" to Phase 3 options | Phase 3 | 2026-04-18 |
| D-18 | **Consumer identity = external Client via Thrift→REST chain.** The consumer of this config is an external Capillary Client (customer integration). Delivery chain: `Client → intouch-api-v3 (REST) → EMF (Thrift RPC) → MySQL`. EMF owns the handler + persistence. intouch-api-v3 is a thin REST facade on top of a new Thrift service defined in `thrift-ifaces-pointsengine-rules` and implemented in emf-parent. This resolves OQ-16 (consumer identity) and cascades to OQ-23 (forces Thrift-compatible PK — `i32` parity via `OrgEntityIntegerPKBase`) and OQ-27 (MySQL, not MongoDB — Thrift-exposed loyalty entities are all MySQL-backed per `SlabInfo`, `Benefits`, `ProgramSlab` precedent). | User answered Phase 4 BLOCKER #1 — "other: Client will consume this flow, Thrift will [be] written in EMF and expose through intouch-api-v3" | Phase 4 | 2026-04-18 |
| D-19 | **Write + Read path (W1)**: ALL CRUD operations (both reads AND writes) go through the same chain: `Client → intouch-api-v3 (REST) → EMF (Thrift) → MySQL`. EMF owns the entire transactional boundary — cascade deactivation (D-14/C-16) happens inside the EMF Thrift handler, not at the REST layer. The REST layer in intouch-api-v3 is a request-translator + auth-context-injector only. This means: (i) new Thrift IDL defines read + write RPCs; (ii) EMF exposes handlers for both; (iii) transaction boundary + `@Transactional` annotation lives in emf-parent service layer; (iv) cache (if any — OQ-30) lives in EMF; (v) tenancy enforcement (G-07) happens at Thrift-handler entry via org context passed from intouch-api-v3 `IntouchUser.orgId`. | User answered BLOCKER #1 follow-up — "W1" (same chain for reads and writes) | Phase 4 | 2026-04-18 |
| D-20 | **API-only MVP (BLOCKER #2 / OQ-17)**. No admin UI in this ticket. Client-facing REST endpoints + internal admin writes via Postman / admin tooling. Phase 3 remains skipped. `/api-handoff` document will be produced post-Phase 7 as the frozen contract spec for a follow-up UI ticket. | User answer to BLOCKER #2 | Phase 4 | 2026-04-18 |
| D-21 | **Rename `BenefitInstance` → `BenefitCategorySlabMapping` (BLOCKER #3 / OQ-19 + OQ-28)**. Entity: `BenefitCategorySlabMapping`. Table: `benefit_category_slab_mapping`. This is explicitly a **junction table** between `benefit_categories` and `program_slabs`. The old concept of `BenefitInstance` as a pseudo-entity is dropped — no separate `tier_applicability` JSON/array column on `benefit_categories`; the junction table IS the source of truth for category↔slab applicability. Consumer queries "which categories apply to slab X" via this junction (fast index on slab_id). | User explicit rename | Phase 4 | 2026-04-18 |
| D-22 | **FK column name = `slab_id` (BLOCKER #4 / OQ-24)**. Repo-consistent naming — matches `program_slabs` table + `SlabInfo` Thrift struct + `ProgramSlab` entity. NOT `tier_id` (public-facing alternative). Consequence: Client-facing REST JSON will literally contain `slab_id` — a glossary entry in the `/api-handoff` doc will map "slab" → "tier" for Client comprehension. Entity naming: `BenefitCategory` retained despite collision risk with legacy `Benefits` (mitigated by separate package + strict coexistence C-14 + D-12). | User answer | Phase 4 | 2026-04-18 |
| D-23 ⚠ | **Audit column pattern — HYBRID (BLOCKER #5 / OQ-25)**. Both `benefit_categories` and `benefit_category_slab_mapping` carry: `created_on` + `created_by` + `updated_on` + `updated_by` + `auto_update_time`. Uses platform-native `_on` suffix (NOT `_at`), uses explicit `updated_on`/`updated_by` pair (new to this feature — no existing table has both), keeps `auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` as DB-level safety net. Note: `auto_update_time` and `updated_on` intentionally coexist — `updated_on` is app-managed (logical change timestamp), `auto_update_time` is DB-managed (physical touch timestamp); they will differ if migrations/cron touch rows without business changes. **AMENDED by D-30**: type of `created_by`/`updated_by` = `int` / `INT(11)` / `i32` (NOT VARCHAR). | User answer; amended by D-30 | Phase 4 | 2026-04-18 |
| D-24 | **Timestamp representation — THREE-BOUNDARY PATTERN (BLOCKER #6 / OQ-26 / G-01 vs G-12.2)**. Each layer uses its native form with explicit conversion at the two boundaries: (1) **EMF entity + MySQL** — `java.util.Date` + `@Temporal(TemporalType.TIMESTAMP)` + MySQL `DATETIME` column (pattern-match `Benefits`, `ProgramSlab`, `Promotions` — G-12.2 respected internally); (2) **Thrift IDL** — `i64` (epoch **milliseconds**, matching `Date.getTime()` and JS convention); `optional i64` for nullable fields like `updated_on`; (3) **REST (intouch-api-v3)** — ISO-8601 UTC strings (e.g., `"2026-04-18T10:30:00.000Z"`) in JSON — G-01-compliant external contract. **Conversion boundaries**: (i) EMF Thrift handler: `Date ↔ i64 millis` — MUST use UTC explicitly (e.g., `Calendar.getInstance(TimeZone.getTimeZone("UTC"))`); (ii) intouch-api-v3 REST layer: `i64 ↔ ISO-8601 string` via Jackson config. Three representations accepted as engineering cost to honour both guardrails on respective sides. G-01 ADR in Phase 6 documents this pattern + the JVM-TZ risk mitigation. | User answer "e4: In Thrift i64, intouch-api-v3 ISO date, emf SQL date" | Phase 4 | 2026-04-18 |
| D-25 | **Maker-checker descope stands; no lifecycle_state column reserved (BLOCKER #7 / OQ-18)**. No product-side compliance sign-off required. Schema ships without a reserved `lifecycle_state` column. If maker-checker is later required (customer contract or new feature), accept the one-time migration cost (add column + backfill existing rows to ACTIVE + branch code paths). Confidence that no current customer contract mandates MC for benefit categories (as distinct from promotion-level MC already handled by `UnifiedPromotion`) is C5 per user. YAGNI honoured — no speculative columns. | User answered BLOCKER #7 — "a" | Phase 4 | 2026-04-18 |
| D-26 | **Scale envelope = SMALL (BLOCKER #8 / OQ-20)**. Assumptions for Phase 6 architecture + Phase 9 testing: ≤50 categories per program, ≤20 slab-mappings per category, ≤1000 rows in worst-case cascade transaction, <10 QPS sustained reads, <1 QPS writes. **Primary reads** for Client (no replica read lag concerns). Implications: (i) single-txn cascade deactivate is safe (1000 rows well within InnoDB limits); (ii) no cache needed day-1 — defer OQ-30; (iii) no CQRS-lite / read-write split; (iv) standard JPA indexing on `(org_id, program_id)` + `(org_id, slab_id)` sufficient; (v) NFR-1 500ms P95 likely conservative for this load — Phase 5 to compare against legacy `/benefits` list SLA (OQ-33). **Commitment vs assumption**: These are **assumptions** for design purposes. Post-launch telemetry may refine; SLOs logged for re-measurement 90 days after GA. | User answered BLOCKER #8 — "a" | Phase 4 | 2026-04-18 |
| D-27 | **Deactivation is ONE-WAY in MVP (BLOCKER #9 / OQ-21 / resolves C-17)**. No reactivation path exists. Once `is_active` flips to `false` on either a category or a mapping, it STAYS false forever. To "re-enable" a category, admin must POST a new category (name-reuse depends on OQ-29 outcome); to "re-enable" a specific mapping, admin must POST a new mapping row on a currently-active category. Old deactivated rows remain as historical/audit artifacts indefinitely. **API consequence**: PATCH `{is_active: true}` on any deactivated row returns **409 Conflict** with explanatory message — deactivation is terminal. Only `{is_active: false}` is a valid PATCH body for the is_active field. **Cascade deactivation (D-14) still holds** — it's the only cascade; there is no "cascade reactivation" to debate. **Supersedes C-17**. | User answered BLOCKER #9 — "e1" | Phase 4 | 2026-04-18 |
| D-28 | **Uniqueness enforcement = APPLICATION layer, not DB (BLOCKER #10 / OQ-22 + BLOCKER #11 / OQ-29)**. Neither `benefit_categories` nor `benefit_category_slab_mapping` carries a DB-level UNIQUE constraint on business keys. The service layer validates on every POST: (1) for a category, reject with **409 Conflict** iff an **active** row exists with the same `(program_id, name, org_id)` — inactive rows are ignored; (2) for a mapping, reject with **409 Conflict** iff an **active** row exists with the same `(category_id, slab_id, org_id)` — inactive rows are ignored. **Consequence**: same name can be reused after soft-delete; same (cat, slab) mapping can be re-created after soft-delete. Multiple deactivated rows with the same business key accumulate as audit history (acceptable at D-26 SMALL scale). **Supersedes C-18, amends D-15**. | User answered "e5: don't make uniqueness at DB level, handle in the validation" | Phase 4 | 2026-04-18 |
| D-29 | **Category name is reusable after soft-delete (BLOCKER #11 / OQ-29)**. Admin can create a new category with a name that matches a previously-deactivated category within the same program. The deactivated row is preserved as audit history; the new row gets a new PK and a clean audit trail. Validation at POST-time: "any ACTIVE row with this (program_id, name, org_id)?" — if no, allow create. Name collision only blocks between active rows. | User explicit answer | Phase 4 | 2026-04-18 |
| D-30 | **`createdBy` / `updatedBy` type = `int` across all three layers (Q-T-01 / RF-3 resolved; amends D-23 type wording)**. Java entity: `private int createdBy` / `private int updatedBy` (Integer for nullable `updatedBy`). MySQL: `created_by INT(11) NOT NULL`, `updated_by INT(11) NULL`. Thrift IDL: `i32 createdBy`, `optional i32 updatedBy`. This matches the platform pattern (e.g. `emf-parent/Benefits.java:createdBy` is `int`) and avoids cross-layer translation. Username/display-name audit readability is NOT part of this schema — if ever required, resolved via a separate user-lookup join at the read layer. **Supersedes D-23's VARCHAR wording** — everything else in D-23 (column names, `auto_update_time` coexistence, `_on` suffix) stands. | User answer — Q-T-01 option (a), platform-consistent int type | Phase 5 (pre-Phase-6 resolutions) | 2026-04-18 |
| D-31 | **HTTP 409 handler added in `intouch-api-v3` (OQ-44 / RF-2 resolved)**. NEW class `ConflictException` in `intouch-api-v3/.../exceptionResources/` package (pattern-match existing exception classes). NEW `@ExceptionHandler(ConflictException.class)` in `TargetGroupErrorAdvice` returning `HttpStatus.CONFLICT` + `ResponseWrapper.error(409, code, message)`. **Thrift-side contract**: EMF handler throws `PointsEngineRuleServiceException` with `statusCode=409` for both (a) D-27 reactivation attempts (PATCH `{is_active: true}` on deactivated row) and (b) D-28 active-duplicate POST scenarios. Facade layer in intouch-api-v3 catches the Thrift exception, checks `statusCode == 409`, and rethrows as `ConflictException`, which the `TargetGroupErrorAdvice` then maps to HTTP 409. This is the **only** new HTTP status code introduced; all other error paths reuse the existing `ValidationException→400` + `NotFoundException→200` (platform quirk — OQ-45 accepts this) + `Throwable→500` mappings. | User answer — OQ-44 option (a), add ConflictException + 409 handler | Phase 5 (pre-Phase-6 resolutions) | 2026-04-18 |
| D-32 | **cc-stack-crm ↔ emf-parent sync is via git submodule (OQ-46 / RF-5 partially resolved)**. Evidence (C7): `emf-parent/.gitmodules` declares `cc-stack-crm` at path `integration-test/src/test/resources/cc-stack-crm` tracking branch `master`. Dev workflow: (1) raise PR in `cc-stack-crm` repo with new DDL files; (2) on that branch, in `emf-parent` bump the submodule pointer to the feature branch HEAD; (3) emf-parent CI runs integration tests against the pointed commit; (4) SonarQube tracks coverage; (5) once cc-stack-crm PR merges to `master`, the submodule pointer in emf-parent is re-pointed to the merged commit. **Release order**: cc-stack-crm PR merges FIRST, emf-parent code release SECOND (matches RF-1 deployment sequence). **Residual uncertainty (C5)**: exact production-Aurora-schema apply mechanism (Facets Cloud auto-sync vs DBA script) — deferred to Phase 12 Blueprint deployment runbook (Q-CRM-1 / RF-5 remainder). | User free-text answer — submodule workflow description | Phase 5 (pre-Phase-6 resolutions) | 2026-04-18 |
| D-33 | **No optimistic locking — last-write-wins on BenefitCategory updates (pre-HLD ADR commit #1)**. No `@Version` column on `benefit_categories` entity. No `version` field in Create/Update request DTO. Concurrent admin writes silently overwrite each other. **Rationale**: at D-26 SMALL scale (≤20 slabs/cat, low admin change rate, admin UI with typically one editor at a time), the probability of concurrent writes colliding is negligible in practice; JPA optimistic-lock infrastructure adds DDL column + DTO field + client round-trip ceremony for a race window that won't materialize. **Guardrail deviation**: G-10 (concurrency) marked as **accepted deviation** — this must be documented as an ADR in 01-architect.md with evidence and review-trigger ("revisit if admin QPS ever >10/sec per tenant" or "revisit if multi-editor Admin UI is introduced"). **Impact on downstream phases**: Phase 7 Designer MUST NOT add `@Version`; Phase 8 QA scenarios QA-34/QA-35 (stale-version / concurrent-update) are formally OUT OF SCOPE — replaced by an explicit note "last-write-wins accepted; no concurrency test needed". **Confidence**: C6 — user decision, scale justified, guardrail exception explicitly acknowledged. | User choice C on pre-HLD ADR-01 prompt | Phase 5→6 (pre-HLD) | 2026-04-18 |
| D-34 | **Reactivation path — dedicated `PATCH /v3/benefitCategories/{id}/activate` endpoint (pre-HLD ADR commit #2)**. US-6 (P1) remains IN SCOPE. New endpoint mirrors the deactivate verb (to be confirmed as symmetric in D-36). **Behaviour**: (a) flips `isActive=false → true` on the category row; (b) **does NOT auto-reactivate cascaded slab-mappings** — admin must re-map explicitly via the mapping surface (D-35 will decide the exact UX). (c) Returns `204 No Content` or the category DTO on success (Phase 6 /architect will decide). (d) Returns `404` if category doesn't exist. (e) Returns `409` if the name is now in use by another ACTIVE category (D-28 uniqueness-among-active rule applies at reactivation). (f) Returns `409` idempotency: calling activate on an already-active category → already-in-target-state response (behaviour to be frozen by /architect: 204 vs 409). **D-27 amendment**: D-27 ("deactivation is terminal — any mutation on inactive = 409") is **REWORDED** to: *"updates via PUT/DELETE on inactive category return 409; reactivation via the dedicated PATCH /activate endpoint is the explicit and only allowed state-change on an inactive category"*. **Downstream phase obligations**: Phase 6 /architect writes an ADR for this with flow diagram + the idempotency semantics; Phase 7 Designer adds a `activateBenefitCategory(orgId, categoryId, actorUserId)` facade method + Thrift handler + REST controller; Phase 8 QA adds scenarios QA-NN (happy reactivation), QA-NN+1 (reactivate already-active → idempotency), QA-NN+2 (reactivate when name taken by another active category → 409), QA-NN+3 (reactivate non-existent → 404). **Thrift IDL impact**: +1 method `activateBenefitCategory`. **Confidence**: C6 — user decision, architecturally clean, mirror of deactivation path. | User choice A on pre-HLD ADR-02 prompt | Phase 5→6 (pre-HLD) | 2026-04-18 |
| D-35 | **REST surface granularity — slabIds embedded in parent BenefitCategory DTO; server-side diff-and-apply sync; NO separate mapping endpoints (pre-HLD ADR commit #3)**. Create/Update request DTO carries `slabIds: List<Integer>` (required, min 1 on Create; full desired state on Update). Server diffs `incomingSlabIds` against existing active `benefit_category_slab_mapping` rows and applies: INSERT new mappings, soft-delete removed mappings (existing `is_active` column, set `false`). Join table `benefit_category_slab_mapping` still exists for FK integrity + historical audit, but is **NOT exposed** as a REST sub-resource. **Endpoint count**: 5 on `/v3/benefitCategories` (POST create, PUT update, GET by id, GET list, PATCH /activate, PATCH /deactivate) — exactly matching decision 4's symmetric PATCH verbs (to be confirmed in D-36). **Safety from D-33**: no optimistic lock accepted → concurrent name+slab edits merge at last-write-wins; this is by design and documented. **Validation on slabIds**: Layer 1 (Bean Validation) — `@NotNull @Size(min=1)` on Create, `@NotNull` only on Update (min=1 enforced at facade — you can't have a category with zero active mappings); `List<@Positive Integer>` element constraint. Layer 2 (facade) — silent dedup via `LinkedHashSet<>(slabIds)` to tolerate duplicate client input; cross-check against `ProgramSlab` existence per org+program (rejects non-existent or wrong-program slabIds with HTTP 409). **Re-add semantics**: re-adding a previously-unmapped slabId INSERTs a new mapping row (does NOT reactivate the soft-deleted row) — old and new rows coexist, only the newest `is_active=true` row is authoritative. **Cascade-deactivate symmetry**: when `PATCH /{id}/deactivate` is called, all active mappings soft-delete in the same transaction (D-06 preserved); when `PATCH /{id}/activate` is called, mappings do NOT auto-reactivate (D-34 clause b). **Downstream phase obligations**: Phase 6 /architect writes an ADR for this with flow diagrams (create path, update diff-apply path, cascade-deactivate path); Phase 7 Designer produces `syncSlabMappings(categoryId, newIdSet)` facade pseudocode + bulk DAO methods (`findMissingIdsForProgram`, `softDeleteAllByCategoryId`); Phase 8 QA exercises dedup, cross-program rejection, re-add-as-insert, GET-returns-active-only. **Thrift IDL impact**: +0 mapping-specific methods; `createBenefitCategory` and `updateBenefitCategory` struct grows a `list<i32> slabIds` field. **Confidence**: C6 — user decision; aligned with D-33 concurrency posture; reduces cross-repo fan-out; matches Maya persona mental model from 00-ba.md. | User choice B on pre-HLD ADR-03 prompt | Phase 5→6 (pre-HLD) | 2026-04-18 |
| D-36 | **Deactivation verb — `PATCH /v3/benefitCategories/{id}/deactivate` (pre-HLD ADR commit #4)**. Symmetric mirror of D-34's `PATCH /{id}/activate`. **Rationale**: (a) soft-delete semantics (D-06) are not accurately conveyed by the REST `DELETE` verb — the row survives with `is_active=false`; (b) state-transition sub-paths (`/activate`, `/deactivate`) form an obvious pair that any API consumer can pattern-match without reading extensive docs; (c) avoids bending PUT semantics (option C rejected — PUT is for updates, not state flips); (d) the tiny "REST purity" cost of using PATCH-on-sub-path is easily defended in the ADR. **Behaviour**: (a) flips `isActive=true → false` on the category row; (b) cascades to all active `benefit_category_slab_mapping` rows (D-06 preserved — soft-delete in same transaction via bulk UPDATE); (c) returns `204 No Content` on success (Phase 6 /architect confirms); (d) `404` if category doesn't exist; (e) idempotency on already-deactivated: Phase 6 decides between `204` (idempotent no-op) vs `409` (explicit error) — default posture is `204` unless /architect argues otherwise. **Thrift IDL impact**: `deactivateBenefitCategory(orgId, categoryId, actorUserId)` method — mirrors `activateBenefitCategory`. **Rejected alternatives**: `DELETE /{id}` (semantically misleading for soft-delete — creates a "why is the row still there?" class of future bugs); `PUT {isActive:false}` (bends PUT, asymmetric with D-34 reactivation). **D-27 alignment**: fully consistent — PUT on inactive still = 409 (can't edit name/slabs of deactivated category); deactivation is its own explicit verb; reactivation is its own explicit verb (D-34). **Downstream phase obligations**: Phase 6 /architect writes an ADR for this with the verb choice rationale + cascade-deactivate flow diagram; Phase 7 Designer adds `deactivateBenefitCategory` facade method with bulk cascade soft-delete SQL + Thrift handler stub + REST controller `@PatchMapping("/{id}/deactivate")`; Phase 8 QA exercises happy deactivate, already-deactivated idempotency (per /architect's choice), cascade verification (mappings → inactive), 404 on non-existent. **Confidence**: C6 — user decision; clean REST semantic; symmetric with D-34. | User choice A on pre-HLD ADR-04 prompt | Phase 5→6 (pre-HLD) | 2026-04-18 |
| D-37 | **Authorization on benefit-category writes = BasicAndKey; NO admin-only gate in MVP (resolves Phase 6 gate Q1)**. All 6 `/v3/benefitCategories` endpoints accept any authenticated caller presenting a valid BasicAndKey (Basic auth + org API key) — same pattern as legacy `UnifiedPromotionController`, `TargetGroupController`, and `/benefits` endpoints. No `@PreAuthorize('ADMIN_USER')` or similar role-based gate. Admin-only enforcement is explicitly deferred as a future layered concern (separate epic). **Amends ADR-010** — no wording change; user confirmation that ADR-010 default posture stands. **Phase 7 Designer obligation**: `BenefitCategoriesV3Controller` uses the same `@SecuredResource` / `@BasicAndKey` annotations as `UnifiedPromotionController` (whichever pattern the codebase uses — Designer verifies). **Phase 8 QA obligation**: no role-based authz scenarios needed; orgId-scoping IT (via `@OrgContext`) covers the multi-tenant enforcement path. **Confidence**: C6 — matches Architect recommendation B; user-confirmed. | User choice B on Phase 6 gate Q1 | Phase 6→7 gate | 2026-04-18 |
| D-38 | **Uniqueness-among-active race posture — ACCEPT at D-26 SMALL scale; no advisory lock, no partial unique index (resolves Phase 6 gate Q2 — OVERRIDES ADR-012 default)**. The race window between `SELECT check_active_duplicate → INSERT new row` for `(org_id, program_id, name)` on a currently-active category is left unmitigated. **Rationale**: (a) D-33 philosophy (accept small-scale risk if ceremony > probable harm) applied consistently; (b) D-26 admin-write QPS <1/s → collision probability is vanishingly small; (c) advisory-lock ceremony (`GET_LOCK` + 2s timeout + new error code `BC_NAME_LOCK_TIMEOUT`) adds MySQL-level complexity and a new failure mode for a race that is unlikely to materialize; (d) if incidents occur post-GA, revisit with either `GET_LOCK` or partial unique index (requires Aurora ≥ 8.0.13 — Q4/D-40 deferred). **Amends ADR-012** — strike the "GET_LOCK('bc:...', 2)" mechanism from the HLD; replace with: "app-layer check only; race accepted at D-26 scale; revisit-triggers: admin QPS >5/sec OR ≥1 real duplicate-name incident in production". **Phase 7 Designer obligation**: `BenefitCategoryFacade.create()` does `dao.findActiveByNameAndOrgAndProgram()` → if exists, throw `ConflictException(BC_NAME_TAKEN)`; else proceed to INSERT. No `GET_LOCK` call. No `BC_NAME_LOCK_TIMEOUT` error code. **Phase 8 QA obligation**: no advisory-lock timeout scenarios; add explicit note in test plan that the SELECT→INSERT race is **accepted** per D-38 and not asserted. **Risk register update**: R-03 (uniqueness race) severity lowered from HIGH to MEDIUM with explicit accepted-deviation flag + revisit-trigger (same shape as R-01 LWW). **Confidence**: C6 — user decision, internally consistent with D-33 philosophy. | User choice B on Phase 6 gate Q2 | Phase 6→7 gate | 2026-04-18 |
| D-39 | **`PATCH /v3/benefitCategories/{id}/activate` response = 200 OK + `BenefitCategoryResponse` DTO on success (resolves Phase 6 gate Q3 — OVERRIDES ADR-006 symmetric 204 default)**. On happy reactivation, response body contains the full post-activation category DTO (id, name, orgId, programId, isActive=true, slabIds, createdBy, createdOn, updatedBy, updatedOn). Saves the client a GET round-trip to refresh admin UI state. **Asymmetry note**: `PATCH /deactivate` stays at 204 per ADR-006 (D-36 semantics — no useful client state to convey). Asymmetry is DELIBERATE and documented: activation needs refreshed state because admin will typically continue editing; deactivation is typically a "mark and move on" operation. **Amends ADR-006**: (i) `/activate` happy path = 200 + DTO; (ii) `/deactivate` happy path = 204; (iii) idempotency on already-active `/activate` still = 204 No Content (Architect decision stands — no state change, no DTO to return); (iv) idempotency on already-deactivated `/deactivate` still = 204. **Phase 7 Designer obligation**: `BenefitCategoryFacade.activate()` returns `Optional<BenefitCategoryResponse>` (empty on idempotent no-op, populated on state change); controller maps empty → 204, populated → 200 + body. Thrift method `activateBenefitCategory` returns the updated struct (not `void`) — **Thrift IDL change**: `BenefitCategory activateBenefitCategory(orgId, categoryId, actorUserId)` with the same struct shape as `getBenefitCategory`. **Phase 8 QA obligation**: assert 200 + DTO on happy activation; assert 204 on idempotent already-active; assert 204 on happy/idempotent deactivation. **Confidence**: C6 — user decision; asymmetry trade-off (UX win vs spec purity) explicitly acknowledged. | User choice B on Phase 6 gate Q3 | Phase 6→7 gate | 2026-04-18 |
| D-40 | **Production Aurora MySQL version confirmation = DEFERRED to Phase 12 Blueprint deployment runbook (resolves Phase 6 gate Q4)**. User does not know the production Aurora version with certainty. Non-blocking for Phase 7 Designer because D-38 (accept-the-race) removes the advisory-lock vs partial-unique-index decision from the critical path — neither mechanism is needed in MVP. **Phase 12 obligation**: deployment runbook includes a step "confirm Aurora MySQL version ≥ 8.0.13 to keep partial-unique-index as a viable remediation if D-38 revisit-trigger fires post-GA; if version < 8.0.13, document `GET_LOCK` as the only fallback option". **Amends ADR-012** — strike the entire advisory-lock mechanism; replace with an accepted-deviation marker referencing D-38; add a "Future Remediation" note listing partial unique index (if Aurora ≥ 8.0.13, per Q4) or `GET_LOCK` (if Aurora < 8.0.13) as options, but do NOT implement either in MVP. **Confidence**: C6 — deferred decision, acceptable because D-38 upstream removed the blocker. | User choice C on Phase 6 gate Q4 | Phase 6→7 gate | 2026-04-18 |

---

## Constraints

_(Populated in Phase 1 and updated as Phase 6/7 add architectural constraints)_

| # | Constraint | Source | Why |
|---|------------|--------|-----|
| C-01 | Java / Spring / Thrift / MySQL stack (existing) | Project context | Platform standard |
| C-02 | 5 repos involved: emf-parent, intouch-api-v3, cc-stack-crm, thrift-ifaces-pointsengine-rules, kalpavriksha | User input | Feature spans these |
| C-03 | Category is metadata only — holds NO reward values. Instances carry values. | BRD §2 | Shapes data model — category table has no amount/points columns |
| C-04 | categoryName must be unique per Program (not global) | BRD §2 + AC-BC02 | Enforcement level: likely DB constraint + service validation |
| ~~C-05~~ | ~~Maker-Checker: new Category → PENDING_APPROVAL~~ | ~~BRD §5 + AC-BC07~~ | ❌ **REMOVED by D-05** — maker-checker descoped from MVP |
| ~~C-06~~ | ~~Dual "inactive" semantics~~ | — | ❌ **REMOVED by D-04** — single is_active flag only |
| C-08 | Data model: single `is_active` boolean flag. NO lifecycle state column. NO approval_request table. | D-05 | Simplifies MVP; add back when maker-checker returns |
| C-09 | All CRUD operations on Categories and Instances are IMMEDIATE (no approval gate) | D-05 | API responds with final state; no pending/approval intermediate |
| ~~C-07~~ | ~~Instance creation must have all required value fields populated before activation~~ | — | ❌ **REMOVED by D-09** — instances carry no value payload |
| ~~C-10~~ | ~~BenefitInstance schema…~~ | — | ❌ **SUPERSEDED by C-10'** — see below |
| C-10' | **`benefit_category_slab_mapping` schema** (junction table) (D-21): `(id INT(11) PK, org_id INT NOT NULL, benefit_category_id INT(11) FK, slab_id INT(11) FK, is_active TINYINT(1) NOT NULL DEFAULT 1, created_on DATETIME NOT NULL, created_by VARCHAR(...) NOT NULL, updated_on DATETIME, updated_by VARCHAR(...), auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)`. Composite PK candidate via `OrgEntityIntegerPKBase` pending Phase 5 confirmation (OQ-23). Unique `(benefit_category_id, slab_id, org_id)` to prevent duplicate mappings. NO value/amount/points/text columns. | D-09, D-21, D-22, D-23 | Junction table form; audit columns finalized |
| ~~C-11~~ | ~~BenefitCategory schema…~~ | — | ❌ **SUPERSEDED by C-11'** — see below |
| C-11' | **`benefit_categories` schema** (D-21, D-22, D-23): `(id INT(11) PK, org_id INT NOT NULL, program_id INT(11) FK, name VARCHAR(...) NOT NULL, category_type ENUM('BENEFITS') NOT NULL DEFAULT 'BENEFITS', is_active TINYINT(1) NOT NULL DEFAULT 1, created_on DATETIME NOT NULL, created_by VARCHAR(...) NOT NULL, updated_on DATETIME, updated_by VARCHAR(...), auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)`. **NO `tier_applicability` column** — junction table `benefit_category_slab_mapping` is the source of truth. NO `trigger_event` column (D-07). Composite PK candidate via `OrgEntityIntegerPKBase` pending Phase 5 confirmation (OQ-23). | D-06, D-07, D-10, D-21, D-22, D-23 | Category schema finalized; junction replaces tier_applicability field |
| C-12 | Benefit awarding logic is OUT OF SCOPE. This feature produces config only; an external reader (identified in Phase 5) applies the benefits. | D-08 | Establishes clean boundary — no event handlers, calculators, or strategy classes in this feature |
| C-13 | BRD §3 (9 category types), §5.3 (trigger mapping), §5.4 (value constraints per type), AC-BC01 trigger-derivation requirement are DEFERRED. Must be explicitly called out in the BA doc as "not in scope — see future ticket". | D-11 | Prevents silent scope creep during design/dev |
| C-14 | New entities must NOT add FKs or columns to the existing `Benefits` table in emf-parent. Zero schema changes to legacy. New tables live in their own namespace (package + table prefix TBD). | D-12 | Strict coexistence — zero blast radius on legacy |
| C-15 | API MUST NOT expose a DELETE verb for categories or instances in MVP. Removal is via PATCH `{is_active: false}` only. | D-13 | Soft-delete semantics enforced at API layer |
| C-16 | Deactivation flow MUST be transactional. Flipping category `is_active=false` and cascading all child instances to `is_active=false` happens in a single DB transaction. Failure at any step rolls back the whole operation. | D-14 | Consistency requirement — no half-deactivated state |
| ~~C-17~~ | ~~Reactivation of a category does NOT auto-reactivate its instances…~~ | — | ❌ **SUPERSEDED by D-27** — no reactivation path exists in MVP; the question of "does reactivation cascade" is moot |
| C-17' | **Deactivation is terminal.** PATCH `{is_active: true}` on ANY deactivated row (category or mapping) returns **409 Conflict**. To restore functionality, admin POSTs a NEW row. Old deactivated rows remain as historical audit artifacts. | D-27 | One-way semantics simplify API + eliminate cascade-reactivation ambiguity |
| ~~C-18~~ | ~~DB constraint: UNIQUE (program_id, name) on benefit_category table…~~ | — | ❌ **SUPERSEDED by C-18'** — user chose app-level validation only, no DB UNIQUE |
| C-18' | **No DB-level UNIQUE** on either `benefit_categories` or `benefit_category_slab_mapping`. Uniqueness enforced at service layer on POST only, scoped to **active rows**: `benefit_categories` rejects (409) if an active row exists with same `(program_id, name, org_id)`; `benefit_category_slab_mapping` rejects (409) if an active row exists with same `(category_id, slab_id, org_id)`. Inactive rows do not block re-creation. | D-28 | App-level validation; DB accepts accumulation of deactivated duplicates |
| C-19 | Both `benefit_category` and `benefit_instance` tables carry `org_id BIGINT NOT NULL` + `program_id BIGINT NOT NULL`. Tenant-isolated queries always scope by `org_id` from auth context. | D-16 | Tenancy + feature scope |
| C-20 ⚠ | **CONTRADICTION WITH C-10/C-11**: BA data model uses `long` PK + `BIGINT org_id`. Codebase pattern is `int(11)` + `OrgEntityIntegerPKBase` composite PK. Thrift IDL uses `i32`. **Must resolve Q-GAP-1 in Phase 4 before Phase 7.** | Phase 2 Gap Analyser G-1 | Pattern mismatch — breaks Thrift RPC, `OrgEntityIntegerPKBase` reuse, join parity |
| C-21 ⚠ | **CONTRADICTION WITH BRD/BA**: BA refers to "Tier table" — no such table exists. Entity is `ProgramSlab`, table `program_slabs`, composite PK `(id, org_id)`. FK target needs `(slab_id, org_id)` composite. **Must resolve Q-GAP-2 in Phase 4.** | Phase 2 Gap Analyser V8/G-2 | Domain terminology collision |
| ~~C-22~~ | ~~CONTRADICTION WITH C-10/C-11: BA requires updated_at…~~ | — | ✅ **RESOLVED by D-23** — hybrid pattern: `created_on`/`created_by`/`updated_on`/`updated_by`/`auto_update_time`. Platform `_on` suffix retained; explicit `updated_*` pair added. |
| ~~C-23~~ | ~~G-01 TENSION: Platform uses java.util.Date…~~ | — | ✅ **RESOLVED by D-24** — three-boundary pattern: Date+DATETIME internal (G-12.2), i64 millis at Thrift, ISO-8601 UTC at REST (G-01 at external contract). |
| C-23' | **Three-boundary timestamp pattern (D-24)**. Conversion ownership: EMF Thrift handler owns `Date ↔ i64` (MUST use explicit UTC TimeZone — not JVM default); intouch-api-v3 owns `i64 ↔ ISO-8601` (Jackson config). All timestamp I/O must be tested across ≥2 timezones per G-01.7. JVM default TZ should be UTC in production — if it's IST, conversion MUST force UTC explicitly. | D-24 | Locks conversion ownership before Phase 6 |
| C-24 ⚠ | **Consumer integration is net-new code**: PRD §9 "EMF integration LOW risk" is wrong. Grep for `Benefits` in `emf/.../eventForestModel/` returns 0 — EMF helpers emit tier events; they do not read benefit config today. Any consumption is new code. | Phase 2 Gap Analyser V5 | Dependency risk level understated |
| C-25 | No Hibernate `@Filter`/`@FilterDef` for `org_id` enforcement found in emf-parent. G-07.1 enforcement is by convention (every DAO manually adds `WHERE org_id = ?`). New feature must either prescribe a repository base class / JPA specification, or add a cross-tenant integration test (G-11.8) to catch regressions. | Phase 2 Gap Analyser G-5 | Multi-tenancy enforcement mechanism must be explicit |
| C-26 | `UnifiedPromotion` (the most recent similar admin-config entity) is **MongoDB-backed**, not MySQL. Persistence choice is per-entity. Cascade-in-txn (D-14) is much easier in MySQL. Q-GAP-5 surfaces this. | Phase 2 Gap Analyser G-9 | Persistence-store choice must be explicit (default MySQL) |

---

## Codebase Behaviour

_(Populated in Phase 5 — Codebase Research. One row per repo.)_

| Repo | Key Findings | Files/Patterns | Confidence |
|------|--------------|----------------|------------|
| emf-parent | No `BenefitCategory` or `BenefitInstance` entity exists. Existing `Benefits` entity uses int PK + org_id composite. `BenefitsType` enum is `{VOUCHER, POINTS}` only. EMF handles tier events via event forest (TierRenewedHelper, TierUpgradeHelper) but these helpers do NOT read benefit config today — only emit events. **Consumer integration would be net-new code, not a "small hook".** **Phase 5 additions**: Canonical handler template = `PointsEngineRuleConfigThriftImpl` with `@ExposedCall(thriftName="pointsengine-rules")` + `@Override @Trace @MDCData(orgId="#orgId", requestId="#serverReqId")` annotations; delegation pattern through `PointsEngineRuleEditorImpl → PointsEngineRuleService`. Transaction boundary = `@Transactional(value="warehouse")` + `@DataSourceSpecification(schemaType=WAREHOUSE)`. Multi-tenancy = `ShardContext.set(orgId)` ThreadLocal, by convention (NO `@Filter`/`@Where`/`@FilterDef`). Exception mapping: `ValidationException→400`, `Exception→500` via `PointsEngineRuleServiceException.setStatusCode(int)`. NO Flyway V-files in repo — schema DDLs pulled from `integration-test/.../cc-stack-crm/schema/dbmaster/warehouse/` for IT. No JVM TZ pinning in Dockerfile. Current Thrift IDL dep = `thrift-ifaces-pointsengine-rules:1.83`. `StrategyType.Type` / `BenefitsType` / `BenefitsAwardedStats.BenefitType` enums confirmed NOT to require BENEFIT_CATEGORY additions. | `pointsengine-emf/src/.../Benefits.java`, `BenefitsType.java`, `TierRenewedHelper.java`, `TierUpgradeHelper.java`, `PointsEngineRuleConfigThriftImpl.java`, `PointsEngineRuleEditorImpl.java`, `ExposedCallAspect.java:98` (ShardContext.set), `BenefitsDao.java:23-28`, `PeProgramSlabDao.java:26`, `StrategyType.java`, `BenefitsType.java`, `code-analysis-emf-parent.md` | C7 _(Phase 2 Analyst + Phase 5 Research)_ |
| intouch-api-v3 | `benefits.sql` schema: `promotion_id NOT NULL` — all existing benefits are promotions-backed. Legacy `Benefits` has NO maker-checker — that flow lives in `UnifiedPromotion` (MongoDB `@Document`) driven by `PromotionStatus` enum. `IntouchUser` carries `long orgId` as Principal — auth injects org context. `ResponseWrapper<T>` is the common error envelope. **Phase 5 additions**: Thrift-client pattern = `RPCService.rpcClient(XyzService.Iface.class, "emf-thrift-service", 9199, 60000)` — exact template in `PointsEngineRulesThriftService.java:43-44`. REST controller pattern = `@RestController @RequestMapping("/v3/...")` returning `ResponseEntity<ResponseWrapper<T>>` (see `MilestoneController`, `TargetGroupController`). Three auth flows: KeyOnly (GET-only), BasicAndKey (writes), IntegrationsClient (OAuth). Only `/v3/admin/authenticate` is `@PreAuthorize("hasRole('ADMIN_USER')")` — all other endpoints authenticate-only. Exception→HTTP mapping in `TargetGroupErrorAdvice` = `ValidationException→400`, `NotFoundException→HTTP 200` (platform quirk), `Throwable→500`. **NO HTTP 409 handler exists** — must be added for D-27/D-28 (NEW-OQ-44). Current Thrift IDL dep = `thrift-ifaces-pointsengine-rules:1.83` — must bump to 1.84. No JVM TZ pinning. `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone="UTC")` is field-level convention. `EntityType` enum has 8 values (PROMOTION, TARGET_GROUP, STREAK, LIMIT, LIABILITY_OWNER_SPLIT, WORKFLOW, JOURNEY, BROADCAST_PROMOTION) — no BENEFIT_CATEGORY needed (maker-checker bypassed per D-25). | `src/test/resources/.../benefits.sql`, `UnifiedPromotion.java:40`, `PromotionStatus.java:7-17`, `IntouchUser.java:24`, `RequestManagementController.java:44-47`, `PointsEngineRulesThriftService.java:43-44`, `MilestoneController.java`, `TargetGroupController.java`, `TargetGroupErrorAdvice.java`, `EntityType.java`, `ResourceAccessAuthorizationFilter.java`, `AuthCheckController.java`, `code-analysis-intouch-api-v3.md` | C7 _(Phase 2 Analyst + Phase 5 Research)_ |
| cc-stack-crm | `program_slabs.sql` — this is the physical "Tier" table. Composite PK `(id, org_id)`. FK into it requires composite `(slab_id, org_id)`, not single-column. Multiple other schemas (`points_categories.sql`, `customer_benefit_tracking.sql`, `partner_program_tier_sync_configuration.sql`) all follow the same composite-PK pattern. ALL tables use `datetime` columns, `created_on` naming, `auto_update_time TIMESTAMP ON UPDATE`. **Phase 5 additions**: Repo is PARTIAL involvement — schema/DDL only, ZERO Java files, no `pom.xml`, no Thrift calls. It is a Facets-platform stack config repo (`features.json` confirms). The warehouse schema home is `/schema/dbmaster/warehouse/`. `grep -r benefit_category` across all 4,997 non-git files returns 0 matches. `benefits_awarded_stats.benefit_type` ENUM does NOT include BENEFIT_CATEGORY. For MVP: 0 modifications needed to existing files; 2 NEW DDL files required (`benefit_categories.sql`, `benefit_category_slab_mapping.sql`). `org_mirroring_meta` and `cdc_source_table_info` are post-MVP concerns (not required — same pattern as legacy `benefits` table). DDL application mechanism to production warehouse is AMBIGUOUS (Facets Cloud auto-sync vs manual DBA vs emf-parent Flyway) — see RF-5 / Q-CRM-1 / A-CRM-4. | `program_slabs.sql`, `points_categories.sql`, `customer_benefit_tracking.sql`, `partner_program_tier_sync_configuration.sql`, `promotions.sql`, `benefits_awarded_stats.sql`, `features.json`, `code-analysis-cc-stack-crm.md` | C7 _(Phase 2 Analyst + Phase 5 Research)_ |
| thrift-ifaces-pointsengine-rules | `SlabInfo` struct uses `i32 id` + `i32 programId` + `i32 serialNumber`. Confirms platform `int` PK pattern extends through the Thrift boundary. Using `long` on new tables would require explicit translation or IDL changes. **Phase 5 additions**: Single-IDL, single-service repo — `pointsengine_rules.thrift` defines ONE `PointsEngineRuleService` service with ~60 methods and one shared `PointsEngineRuleServiceException {1: required string errorMessage; 2: optional i32 statusCode}` exception struct (statusCode field is HTTP-analogue). Recommendation (C7): ADD the 8 new BC methods to the existing service — do NOT create a new service. Existing CRUD template = `BenefitsConfigData` CRUD at lines 1276-1282 (`createOrUpdateBenefits`, `getConfiguredBenefits`, `getBenefitsById`, `getAllConfiguredBenefits`). Bare `createdOn`/`updatedOn` field names in this IDL (no `_millis` suffix; `_millis`/`*InMillis` is a different convention in `emf.thrift`). Current Maven version = `1.84-SNAPSHOT`; latest release tag = `v1.83`. Zero name-collision risk — grep of all 8 proposed method names returns 0 matches. Proposed struct set: `enum BenefitCategoryType`, `struct BenefitCategoryDto`, `struct BenefitCategorySlabMappingDto`, `struct BenefitCategoryFilter`. Type conflict flagged: Q-T-01 (`createdBy` → int in EMF entities vs VARCHAR per D-23 intent — must resolve in Phase 6). | `pointsengine_rules.thrift:352-361` (SlabInfo), `pointsengine_rules.thrift:1276-1282` (Benefits template), `pom.xml:version=1.84-SNAPSHOT`, `code-analysis-thrift-ifaces.md` | C7 _(Phase 2 Analyst + Phase 5 Research)_ |
| kalpavriksha | Docs-only repo — no Java source, no `pom.xml` for application code. Purely the pipeline documentation host. 0 code changes for this feature. | — | C7 _(Phase 5 Research)_ |

---

## Open Questions

_(Populated incrementally. Resolved questions move to Key Decisions.)_

| # | Question | Asked By | Status |
|---|----------|----------|--------|
| OQ-1 | What's in scope for this feature? CRUD of Category entity only, or also Instance creation, aiRa mapping, Matrix View, Subscription linkage? | BA Phase 1 | ✅ resolved — D-03: (a) + (b), i.e., Category CRUD + Instance linking |
| OQ-2 | BRD has THREE axes around "state" of a category: (A) isActive boolean §2, (B) DRAFT/PENDING_APPROVAL/ACTIVE lifecycle §5+AC-BC01, (C) "no instances = Inactive" functional §5 prose. | BA Phase 1 | ✅ partial: axis C resolved by D-04 (ignore prose). Axis A vs B still open → Q3. |
| OQ-3 | Are the 9 categoryTypes a fixed (closed) enum or open/extensible? → **ProductEx PB-02**. | BA Phase 1 | ✅ resolved by D-06 — neither; single value `BENEFITS` for MVP, rest deferred |
| OQ-4 | AC-BC04, AC-BC05, AC-BC06 missing from BRD numbering. Intentional gap or content missing? | BA Phase 1 | open — defer to final review |
| OQ-5 | Does "delete" exist for categories? BRD has isActive=false (soft-delete) but no hard-delete spec. → **ProductEx MS-01** (overlaps DU-03). | BA Phase 1 | ✅ resolved by D-13 — soft-delete only, no DELETE verb in MVP |
| OQ-6 | categoryName uniqueness per-Program or per-Organization? | BA Phase 1 | ✅ resolved by D-15 — per-Program (program_id, name) |
| OQ-7 | Category UPDATE maker-checked, or only CREATE + instance changes? | BA Phase 1 | ✅ resolved by D-05 — no maker-checker in MVP |
| OQ-8 | When category is PENDING_APPROVAL, can instances be drafted? BRD §5 vs AC-BC03 appear to contradict. → **ProductEx PB-03**. | BA Phase 1 | ✅ resolved by D-05 — moot, no PENDING_APPROVAL state |
| OQ-13 | Maker-checker timeout behaviour (72hr auto-reject, withdrawable, notifications). → **ProductEx MS-02**. | BA Phase 1 | ✅ resolved by D-05 — deferred to when maker-checker returns |
| OQ-9 | What happens to running instances when parent category is deactivated (mid-cycle)? → **ProductEx PB-04**. | BA Phase 1 | ✅ resolved by D-14 — cascade deactivate in same txn |
| OQ-10 | EARN_POINTS — multiplier vs points-per-currency — how does it flow to EMF Points Engine? → **ProductEx PB-05**. | BA Phase 1 | ✅ resolved by D-08, D-09 — moot; instance carries no value, awarding is external |
| OQ-15 | **Which existing system READS this config and applies benefits?** Candidates: EMF tier event forest (TierRenewedHelper, TierUpgradeHelper), peb (Points Engine Backend), intouch-api-v3 workflows, or a new consumer TBD. Must be confirmed in Phase 5 research — affects API schema (they're the consumer) and integration contract. | D-08 | ✅ **resolved by D-18** — Consumer is an **external Capillary Client** (not an internal system). Config is exposed via intouch-api-v3 REST + EMF Thrift. Awarding logic lives on the Client side. |
| OQ-11 | Naming collision: new "Benefit Category" vs existing emf-parent `Benefits` entity. → **ProductEx DT-01**. | BA Phase 1 | ✅ resolved by D-12 — strict coexistence, separate packages/tables, glossary clarification |
| OQ-12 | BRD-internal Epic numbering conflict: E2 (Benefits as a Product) vs E4 (Benefit Categories). Which Jira epic does CAP-185145 belong to? → **ProductEx DT-02**. | BA Phase 1 | open — low risk for engineering, ask for record |
| OQ-14 | Multi-tenancy — orgId vs programId boundary. Existing pattern is orgId per ProductEx C6. | BA Phase 1 | ✅ resolved by D-16 — both on new tables; scoped queries via auth context |
| OQ-16 | **C-1 (Critic)**: Consumer identity unknown. Options: (a) pause until product names it, (b) scope-reduce to internal registry only, (c) 2-day Phase 5 spike in emf-parent to verify/refute EMF hypothesis. Action of proceeding to Phase 6 on C3 evidence requires C4+. | Phase 2 Critic | ✅ **resolved by D-18** — Consumer = external Client via intouch-api-v3 REST → EMF Thrift → MySQL |
| OQ-17 | **C-2**: Is it acceptable to ship CAP-185145 as pure internal plumbing (no UI, no loyalty-engine integration) until FU-1/2/3 land? | Phase 2 Critic | ✅ **resolved by D-18 + D-20** — NOT internal plumbing (public Client-facing API); API-only MVP (no admin UI); admin writes via Postman/internal tooling until follow-up UI ticket. |
| OQ-18 | **C-3**: Compliance sign-off required for descoping maker-checker? Any customer org with contractual requirement? Should schema reserve a nullable `lifecycle_state` column to avoid future breaking change? | Phase 2 Critic | ✅ **resolved by D-25** — no sign-off required, no reserved column. YAGNI honoured. Accept future migration cost if MC returns. |
| OQ-19 | **C-4**: Post-D-09, BenefitInstance is `(category_id, tier_id, is_active)` — semantically redundant with `tier_applicability`. Pick: (a) drop BenefitInstance in MVP, use only tier_applicability, (b) keep both and make tier_applicability updates cascade to instances. | Phase 2 Critic | ✅ **resolved by D-21** — neither (a) nor (b): `BenefitInstance` concept dropped; renamed to `BenefitCategorySlabMapping` explicit junction table. `tier_applicability` field REMOVED from `benefit_categories` (junction IS the source of truth). |
| OQ-20 | **C-5**: Expected p95/p99 instances-per-category count? Row-count cap for cascade? Consumer reads from replica or primary (affects consistency after cascade)? | Phase 2 Critic | ✅ **resolved by D-26** — SMALL envelope: ≤50 cat/prog, ≤20 slab/cat, ≤1k cascade, <10 QPS read, <1 QPS write, primary reads. |
| OQ-21 | **C-6**: At category reactivation: (a) no cascade (current D-14), (b) cascade reactivation, (c) admin-choice UI. Recommend (c). | Phase 2 Critic | ✅ **resolved by D-27** — no reactivation path exists; question is moot. To restore, admin POSTs a new category/mapping. |
| OQ-22 | **C-7 (AC-BC03' clause 3)**: POST for existing-but-inactive (category, tier) — reactivate (200) or 409 + Location header requiring PATCH? Must pick before Phase 6. | Phase 2 Critic | ✅ **resolved by D-28** — POST creates a NEW mapping row (new PK, is_active=true). Inactive rows for same (cat, slab) are treated as history; don't block the new POST. 409 only returned if an ACTIVE row already exists. |
| OQ-23 | **Q-GAP-1 / ProductEx CF-01 / BE-01 / Critic C-8**: PK type — `int(11)` + `OrgEntityIntegerPKBase` composite (pattern-match, recommended) or `long` standalone (BA's proposal)? | Phase 2 Gap Analyser | ⚠ **tentatively resolved by D-18** — Thrift IDL uses `i32` across loyalty structs (`SlabInfo`, etc.); exposing new entity over Thrift forces `int(11)` + `OrgEntityIntegerPKBase` for parity. Final confirmation after Phase 5 reviews handler patterns. |
| OQ-24 | **Q-GAP-2 / Critic C-12**: Naming — `tier_id` (public) or `slab_id` (repo-consistent) for FK column? Entity naming — `BenefitCategory` risks collision with legacy `Benefits`; alternative `LoyaltyBenefitCategory`/`BenefitConfig`? | Phase 2 Gap Analyser | ✅ **resolved by D-22** — FK = `slab_id` (repo-consistent). Entity = `BenefitCategory` retained; collision mitigated by C-14 (separate tables) + D-12 (strict coexistence) + separate package. |
| OQ-25 | **Q-GAP-3**: Audit columns — adopt new 4-column pattern (`created_at`, `created_by`, `updated_at`, `updated_by`) or match existing (`created_on`, `created_by`, `last_updated_by`, implicit `auto_update_time`)? BA's `updated_at`/`updated_by` doesn't exist anywhere in code. | Phase 2 Gap Analyser | ✅ **resolved by D-23** — hybrid: `created_on`/`created_by`/`updated_on`/`updated_by`/`auto_update_time`. |
| OQ-26 | **Q-GAP-4 (CRITICAL)**: Timestamps — `java.util.Date` (pattern-match platform, violates G-01.3) or `Instant` (G-01 compliant, creates type island)? | Phase 2 Gap Analyser | ✅ **resolved by D-24** — three-boundary pattern: `Date`+`DATETIME` (EMF), `i64` millis (Thrift), ISO-8601 UTC (REST). G-01 honoured at external contract; G-12.2 honoured internally; conversion at two explicit boundaries. |
| OQ-27 | **Q-GAP-5**: MySQL (matches tenancy/cascade/UNIQUE, recommended) or MongoDB (matches `UnifiedPromotion`)? | Phase 2 Gap Analyser | ✅ **resolved by D-18/D-19** — MySQL. Thrift-exposed loyalty entities are all MySQL (`ProgramSlab`, `Benefits`, `PointCategory`). `UnifiedPromotion` MongoDB is driven by its maker-checker flow which was descoped (D-05). Cascade-in-txn (C-16) is also cleaner in MySQL. |
| OQ-28 | **Q-GAP-6 / Critic C-10**: `tier_applicability` storage — JSON column or junction table `benefit_category_slab_applicability`? Junction preferred for consumer query by tier. | Phase 2 Gap Analyser | ✅ **resolved by D-21** — junction table `benefit_category_slab_mapping` (IS the "BenefitInstance" rename; no redundant `tier_applicability` field on categories). |
| OQ-29 | **Q-GAP-7 / Critic C-9**: Name uniqueness on soft-delete — block reuse (default, matches legacy `benefits`) or free it? Also: max length, trim, case sensitivity, empty/NULL handling. | Phase 2 Gap Analyser | ✅ **resolved by D-28/D-29** — Name reuse ALLOWED after soft-delete. Uniqueness only among active rows, enforced at app layer, no DB constraint. Max-length/trim/case/empty still for Designer to finalize in Phase 7 (LOW — style-normalization). |
| OQ-30 | **Q-GAP-8**: Cache on day 1 or defer? Default defer; revisit when consumer load measured. | Phase 2 Gap Analyser | ✅ **trivially resolved by D-26** — SMALL envelope (<10 QPS read) means no cache day-1. Revisit if prod telemetry shows hot-path. |
| OQ-31 | **Critic C-13**: ProductEx BE-05 (promotion_id on legacy) treated as resolved by D-08/D-09 — but if eventual consumer needs to issue vouchers/points, it must create promotions on-the-fly or bypass. Revisit in Phase 5 after consumer identified. | Phase 2 Critic | Tied to OQ-16 |
| OQ-32 | **Critic C-14 / OQ-4 reopened**: Actually chase AC-BC04/05/06 missing from BRD (5-minute email) rather than defer indefinitely. | Phase 2 Critic | LOW but deterministic |
| OQ-33 | **Critic C-15**: NFR-1 numbers (500ms P95, 200 categories, 1000 instances) have no baseline. Align with existing `/benefits` list SLA or provide evidence. | Phase 2 Critic | ⚠ partially resolved by D-26 — smaller envelope (≤50 cat, ≤20 slab/cat) supersedes PRD numbers. 500ms P95 still needs baseline check vs legacy `/benefits` list SLA in Phase 5. |
| OQ-34 | **Authz at the Client boundary (from D-18/D-19)**: An external Client can WRITE these configs? Or are writes admin-only (internal tooling/Postman) and only reads are Client-facing? If Client-write, what role/scope/API-key permission gates it (needs intouch-api-v3 auth layer decision)? | Phase 4 | HIGH — affects REST auth interceptor + API contract surface |
| OQ-35 | **Existing Thrift handler template verification**: Phase 5 must identify an existing emf-parent Thrift handler (e.g., `SlabService` / `BenefitsService`) that exposes CRUD over a `MultiplexedProcessor`, and copy its patterns: org context propagation, exception translation, transaction boundary, error codes. Phase 7 Designer depends on this template. | Phase 4 → Phase 5 action | HIGH — template determines Designer output |
| OQ-36 | **Error envelope across Thrift→REST boundary**: Thrift throws typed exceptions (e.g., `TApplicationException`, custom `*FaultException`). intouch-api-v3 uses `ResponseWrapper<T>` with HTTP status codes. What's the mapping? Pattern-match existing `RequestManagementController` or define new? (409 on name-dupe, 404 on category-not-found, etc.) | Phase 4 → Phase 7 action | MEDIUM — affects Designer exception hierarchy |
| OQ-37 | **Validation layer placement**: With REST→Thrift chain, validations can live at (a) REST controller via Bean Validation on DTOs (fail-fast, client gets 400 without RPC hop), (b) EMF Thrift handler (authoritative, re-validated even for non-REST consumers), (c) both (defensive, DRY pain). Default: (c) — shallow validation at REST (null/empty/range), authoritative validation in EMF handler. Confirm in Phase 7. | Phase 4 → Phase 7 action | MEDIUM — affects G-03 coverage + Designer pattern choice |
| OQ-38 | **JVM default timezone in production** — is it UTC or IST (or per-DC mixed)? Phase 5 action — confirm via ops/config inspection. If IST, EMF Thrift handler MUST explicitly force UTC for every `Date ↔ i64` conversion (D-24). If UTC, default conversions work but tests must still cover the IST case per G-01.7. | Phase 4 → Phase 5 action | HIGH — D-24 correctness depends on this |
| OQ-39 | **Thrift `i64` timestamp unit** — seconds (Unix) or milliseconds (`Date.getTime()`, JS default)? **Default: milliseconds** — matches `Date.getTime()` zero-cost conversion + JS Client parity. Phase 7 Designer confirms in Thrift IDL field doc comments. | Phase 4 → Phase 7 | LOW — one-line ADR decision |
| OQ-40 | **ISO-8601 format variant at REST** — Jackson default is `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` (UTC suffix Z, millisecond precision). Accept default or pin explicitly in `ObjectMapper` config? **Default: pin explicitly** — avoids Jackson-version drift. Phase 7 Designer specifies. | Phase 4 → Phase 7 | LOW — config decision |
| OQ-41 | **Thrift field naming for timestamps** — `createdOn` vs `createdOnMillis` vs `createdOnEpoch`? Convention check: some existing Capillary Thrift IDLs use bare field names with i64, others use `_millis` suffix for clarity. Phase 5 identifies convention in existing IDLs; Phase 7 Designer picks. | Phase 4 → Phase 5/7 | LOW |
| OQ-42 ⚠ | **Race-condition risk on app-level uniqueness (from D-28)**: Two concurrent POSTs on the same (program_id, name) can both pass the "no active duplicate" check before either commits, resulting in two active rows. At D-26 SMALL scale (<1 QPS writes) the probability is near-zero, but G-10.5 (race-free write paths) formally requires a mitigation. Options for Phase 7 Designer: (i) `SELECT … FOR UPDATE` on the category row during validation — weak because there's no row yet; (ii) `GET_LOCK('benefit_category_{program_id}_{name_hash}')` MySQL advisory lock, released at txn end; (iii) Accept the race as residual risk at this scale, log for prod monitoring; (iv) Revisit and add a partial unique index on `(program_id, name) WHERE is_active=true` if option (iii) triggers an incident. Default recommendation: (ii) advisory lock — deterministic, low overhead, no schema change. | From D-28 | HIGH in principle, LOW at D-26 scale — for Phase 7 Designer |
| OQ-43 | **String normalization for category name (Phase 7 Designer)**: max length (VARCHAR(120)? 255?), trim whitespace at validation, case-sensitive or case-insensitive equality for uniqueness check (D-28), empty string vs NULL handling, Unicode normalization (NFC) for emoji/accents. Follow platform convention from `benefits.name` or `promotions.name`. | From D-28/D-29 | LOW — Phase 7 Designer |
| OQ-44 | **[Cross-repo] HTTP 409 handler in `TargetGroupErrorAdvice`** — add new `ConflictException` class + `@ExceptionHandler(ConflictException.class)` returning HTTP 409? Or downgrade all D-27/D-28 409 scenarios to HTTP 400 to match existing platform convention? `TargetGroupErrorAdvice` currently has NO 409 handler. | Phase 5 (intouch-api-v3 analysis + RF-2) | ✅ **resolved by D-31** — add `ConflictException` + `@ExceptionHandler` → HTTP 409. EMF throws `PointsEngineRuleServiceException.setStatusCode(409)`; Facade rethrows as `ConflictException`. |
| OQ-45 | **[Cross-repo] `NotFoundException` maps to HTTP 200 in `TargetGroupErrorAdvice`** — for `GET /v3/benefitCategories/{id}` not-found: follow platform convention (200 + error body) or introduce HTTP 404? Confirm with product/API consumer team. | Phase 5 (intouch-api-v3 analysis + RF-8) | MEDIUM — API contract decision |
| OQ-46 | **[Cross-repo] Schema sync between cc-stack-crm and emf-parent integration-test resources** — emf-parent ITs pull schema DDL from `integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/`. New DDL files for `benefit_categories` + `benefit_category_slab_mapping` must be added BOTH in cc-stack-crm AND copied/synced into emf-parent's integration-test resources. Is there a sync script or manual copy? Who is responsible for keeping them consistent? | Phase 5 (emf-parent analysis §6) | ✅ **resolved by D-32** — cc-stack-crm is a git submodule of emf-parent (`.gitmodules` verified C7). Dev workflow: PR in cc-stack-crm → bump submodule pointer in emf-parent branch → IT run. Release order: cc-stack-crm merges first, emf-parent second. Residual: prod Aurora apply mechanism → Phase 12 runbook. |
| OQ-47 | **[Thrift handler sizing]** `PointsEngineRuleConfigThriftImpl` already implements both `PointsEngineRuleService.Iface` AND `StrategyProcessor`. Adding 8 new methods expands this class further. Phase 6 Architect: is it better to create a new `BenefitCategoryThriftImpl` handler with `@ExposedCall(thriftName="pointsengine-rules")` registered separately, or keep adding methods to the existing large class? Separation improves maintainability but deviates from current pattern. | Phase 5 (emf-parent OQ-35 resolution) | LOW — maintainability |
| OQ-48 | **[Cross-layer naming]** Proposed Thrift method `getMappingsByCategory` is named differently from the proposed REST operation `getBenefitCategorySlabMappings`. Phase 7 Designer must align naming across all 3 layers (REST path, Thrift method name, Java method name) consistently. | Phase 5 (cross-repo-trace) | LOW — naming consistency |
| OQ-49 | **[REST endpoint design]** `deactivateBenefitCategory` — distinct PATCH `/v3/benefitCategories/{id}/deactivate` path (explicit about D-27 one-way semantics) OR PATCH `/v3/benefitCategories/{id}` with `{is_active: false}` body (more REST-conventional)? Phase 7 Designer to decide and document in `/api-handoff`. | Phase 5 (cross-repo-trace RF/D-27) | MEDIUM — API shape |
| Q-T-01 | **[Data-type 3-layer conflict — Phase 6 MUST RESOLVE]** `createdBy` type conflicts across three layers: (1) `emf-parent/Benefits.java:createdBy` is `int`; (2) D-23 blocker decision declares schema `created_by VARCHAR(...)`; (3) thrift-ifaces recommendation says `string createdBy` for audit clarity. | Phase 5 (thrift-ifaces + cross-repo RF-3) | ✅ **resolved by D-30** — aligned on `int` / `INT(11)` / `i32`. D-23's VARCHAR wording superseded. |
| Q-T-02 | **[Thrift struct extension]** Consider extending a common `AuditTrackedClass`-style struct for the shared audit fields rather than duplicating `i64 createdOn`/`i64 updatedOn`/`createdBy`/`updatedBy` on every new DTO. | Phase 5 (thrift-ifaces analysis) | LOW — code hygiene |
| Q-T-03 | **[Denormalized field]** Should the `BenefitCategorySlabMappingDto` carry a denormalized `programId` to help consumers scope/filter without a second fetch? | Phase 5 (thrift-ifaces analysis) | LOW — API ergonomics |
| Q-CRM-1 | **[Data-pipeline registry]** `org_mirroring_meta.sql` — should `benefit_categories` and `benefit_category_slab_mapping` be added for org-mirroring? Pattern-match says no (legacy `benefits` is also absent), but product team should confirm no mirroring requirement. | Phase 5 (cc-stack-crm analysis) | LOW — post-MVP |
| Q-CRM-2 | **[CDC pipeline]** `cdc_source_table_info.sql` — register new tables for Change Data Capture? Post-MVP concern. | Phase 5 (cc-stack-crm analysis) | LOW — post-MVP |

---

## Standing Architectural Decisions (Project-Level)

_(Pulled from CLAUDE.md — Architectural Decisions table. Do not duplicate here; reference only.)_

See: `.claude/CLAUDE.md` → "Architectural Decisions (Standing — Project-Level)"

---

## Per-Feature ADRs

_(Populated in Phase 6 — Architect. Each row links to the full ADR in `01-architect.md`.)_

| ADR | Title | Status | Phase |
|-----|-------|--------|-------|
| ADR-001 | No optimistic locking on BenefitCategory (last-write-wins) — from D-33 | Accepted (frozen) | 6 |
| ADR-002 | Reactivation via dedicated `PATCH /v3/benefitCategories/{id}/activate` — from D-34 | Accepted (frozen) | 6 |
| ADR-003 | `slabIds` embedded in parent DTO; server-side diff-and-apply; NO mapping sub-resource — from D-35 | Accepted (frozen) | 6 |
| ADR-004 | Deactivation verb `PATCH /v3/benefitCategories/{id}/deactivate` with cascade — from D-36 | Accepted (frozen) | 6 |
| ADR-005 | Thrift handler assignment — extend existing `PointsEngineRuleConfigThriftImpl` (no new handler class) | Accepted (C7) | 6 |
| ADR-006 | Idempotency response codes — `204 No Content` for already-active activate AND already-inactive deactivate | Accepted (C6) | 6 |
| ADR-007 | Data model — column types, audit columns, indexes, NO `version` column, NO DB UNIQUE, logical FKs only | Accepted (C7) | 6 |
| ADR-008 | Timestamp three-boundary pattern (carry-forward of D-24) — Date+DATETIME (EMF) / i64 millis (Thrift) / ISO-8601 UTC (REST) | Accepted (C6) | 6 |
| ADR-009 | Error contract — new `ConflictException → 409` in intouch-api-v3; specific error codes per 409/400 path | Accepted (C7) | 6 |
| ADR-010 | Authorization — GETs on KeyOnly/BasicAndKey; writes on BasicAndKey; no `@PreAuthorize('ADMIN_USER')` gate in MVP | Accepted pending Q1 (C5) | 6 |
| ADR-011 | Pagination — offset-based `?page=&size=&isActive=&programId=`; default size 50 max 100 | Accepted (C5) | 6 |
| ADR-012 | Uniqueness race mitigation — app-level check + MySQL `GET_LOCK` advisory lock; partial unique index fallback on MySQL ≥ 8.0.13 | Accepted pending Q2 (C4) | 6 |
| ADR-013 | Deployment sequence — cc-stack-crm → thrift-ifaces → emf-parent → intouch-api-v3 | Accepted (C7) | 6 |

---

## Risk Register

_(Populated in Phase 6a — Impact Analysis.)_

| # | Risk | Severity | Mitigation | Phase |
|---|------|----------|------------|-------|

---

## Guardrails Referenced

_(As phases reference specific guardrails from `.claude/skills/GUARDRAILS.md`.)_

| Guardrail | Phase Referenced | Context |
|-----------|------------------|---------|
| G-01 (Timezone) | Phase 2, Phase 4 | **RESOLVED by D-24** — three-boundary pattern: Date+DATETIME internal (accept G-12.2 parity), i64 millis at Thrift, ISO-8601 UTC at REST (G-01 at external contract). Residual OQ-38 (JVM default TZ in prod) + G-01.7 multi-TZ tests required in Phase 9. |
| G-07 (Multi-Tenancy) | Phase 2 | **CRITICAL** — G-07.1 requires framework-level enforcement; platform uses by-convention. See C-25 / OQ-to-Phase-7. |
| G-03 (Security) | Phase 2 | WARN — Bean Validation on DTOs must be prescribed by Designer. |
| G-05 (Data Integrity) | Phase 2 | WARN — G-05.2 optimistic locking absent; race on name-create needs explicit 409 contract (Gap G-7). |
| G-12 (AI-specific) | Phase 2 | PASS — Gap analysis IS the "read before write" pattern. G-01 tension flagged. |

---

## Cross-Repo Coordination

_(Populated in Phase 5 — Cross-Repo Tracer. Verified via direct code reads across all 5 repos. See `cross-repo-trace.md` §5 + §7 for evidence.)_

| Repo | New Files | Modified Files | Reason | Confidence |
|------|-----------|----------------|--------|------------|
| thrift-ifaces-pointsengine-rules | 0 new files | 1 modified: `pointsengine_rules.thrift` (add `enum BenefitCategoryType`, `struct BenefitCategoryDto`/`BenefitCategorySlabMappingDto`/`BenefitCategoryFilter`, 8 new methods on existing `PointsEngineRuleService`). 1 modified: `pom.xml` (1.84-SNAPSHOT → 1.84 release). | Single-IDL, single-service repo — add methods to existing service (NOT new service); all loyalty CRUD multiplexed through `PointsEngineRuleService`. | C7 _(Phase 5 verified)_ |
| emf-parent | 6+ new Java files: `BenefitCategory.java` entity, `BenefitCategorySlabMapping.java` entity, `BenefitCategoryDao.java`, `BenefitCategorySlabMappingDao.java`, `BenefitCategoryService.java`, plus 2 new DDL snapshots in `integration-test/.../cc-stack-crm/schema/dbmaster/warehouse/`. | 2 modified: `PointsEngineRuleConfigThriftImpl.java` (add 8 `@Override @Trace @MDCData` handler methods), `PointsEngineRuleEditorImpl.java` (add 8 delegation methods). Plus `pom.xml` bump 1.83 → 1.84. | Owns entity + handler + transactional boundary + cascade logic (C-16). Canonical template verified = `PointsEngineRuleConfigThriftImpl` + `ExposedCallAspect` ShardContext propagation. | C6 _(Phase 5 verified)_ |
| intouch-api-v3 | 9 new files: `BenefitCategoryController.java`, `BenefitCategorySlabMappingController.java`, `BenefitCategoryFacade.java`, `BenefitCategoryThriftService.java`, `BenefitCategoryRequest.java` + `BenefitCategoryResponse.java` + `BenefitCategorySlabMappingRequest.java` + `BenefitCategorySlabMappingResponse.java` DTOs, `ConflictException.java` (NEW — required by D-27/D-28 per OQ-44). | 2 modified: `TargetGroupErrorAdvice.java` (add `@ExceptionHandler(ConflictException.class) → HTTP 409`), `pom.xml` (1.83 → 1.84). | Thin REST facade — translates HTTP↔Thrift via `RPCService.rpcClient("emf-thrift-service", 9199, 60000)`, injects `IntouchUser.orgId`, applies Bean Validation, converts `i64 millis ↔ ISO-8601 UTC` via `@JsonFormat`. | C6 _(Phase 5 verified)_ |
| cc-stack-crm | 2 new DDL files: `schema/dbmaster/warehouse/benefit_categories.sql`, `schema/dbmaster/warehouse/benefit_category_slab_mapping.sql`. | 0 modified for MVP. | DDL home confirmed (`features.json` + `/schema/dbmaster/warehouse/` convention). No Java/Thrift/dispatcher registrations in this repo. `org_mirroring_meta`/`cdc_source_table_info` are post-MVP (Q-CRM-1/2). Production DDL application mechanism ambiguous — see RF-5. | C6 _(Phase 5 verified)_ |
| kalpavriksha | 0 code files (docs only) | 0 code files | Pipeline documentation host only — no Java source, no pom.xml. | C7 _(Phase 5 verified)_ |

### Red Flags (from cross-repo-trace.md §6)

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| RF-1 | Thrift IDL version deployment sequencing: publish `thrift-ifaces:1.84` → deploy `emf-parent` → deploy `intouch-api-v3`. Wrong order causes `TApplicationException: unknown method`. | CRITICAL | Enforce deployment sequence; consider feature flags for zero-downtime. |
| RF-2 | ~~`TargetGroupErrorAdvice` has NO HTTP 409 handler — D-27/D-28 need one.~~ | ✅ RESOLVED | **D-31**: Add `ConflictException` + `@ExceptionHandler` → HTTP 409. EMF throws `PointsEngineRuleServiceException.setStatusCode(409)`; Facade rethrows. |
| RF-3 | ~~`createdBy` type conflict: int (EMF entities) vs VARCHAR (D-23 schema) vs string (IDL proposal).~~ | ✅ RESOLVED | **D-30**: aligned `int` / `INT(11)` / `i32` across all three layers. D-23 VARCHAR wording superseded. |
| RF-4 | Admin-only vs open writes — no `@PreAuthorize` distinction in current codebase except `/v3/admin/authenticate`. | HIGH | Phase 6 Architect decision (OQ-34). |
| RF-5 | DDL migration execution mechanism — **dev/IT mechanism resolved (D-32: git submodule)**; production Aurora apply mechanism still ambiguous. | LOW (dev) / MEDIUM (prod) | **D-32 (partial)**: dev = submodule + IT; prod = Phase 12 deployment runbook (Q-CRM-1 / A-CRM-4 remainder). |
| RF-6 | ShardContext multi-tenancy by convention only — no `@Filter` / `@Where` safety net. | MEDIUM | Prescribe base-DAO pattern + cross-tenant IT (G-11.8 pattern). |
| RF-7 | JVM TZ not pinned — residual risk for any `SimpleDateFormat` use. | LOW (with D-24 `Date.getTime()`) | D-24 avoids format-based ops. OQ-38 still open — confirm prod TZ. |
| RF-8 | `NotFoundException → HTTP 200` (platform quirk) on GET-by-id. | LOW | Follow platform convention; document in `/api-handoff`. (OQ-45) |
| RF-9 | Thrift method name collision check — 0 matches for all 8 proposed method names in existing IDL. | LOW | N/A — no collision. |

---

## Architect Phase 6 — Additions

**New Codebase Behaviour findings**:
- `PointsEngineRuleConfigThriftImpl` is the canonical CRUD Thrift handler template — C7, evidence `code-analysis-emf-parent.md` §2 + `PointsEngineRuleConfigThriftImpl.java`. New 6 methods attach here (ADR-005). _(Architect)_
- `PointsEngineRuleService` uses class-level `@Transactional(value="warehouse", propagation=Propagation.REQUIRED)` — all new service methods (create/update/activate/deactivate/syncSlabMappings) inherit this. _(Architect)_
- Cascade-deactivate is a single-shot bulk UPDATE `SET is_active=false WHERE category_id=? AND org_id=? AND is_active=true` within the same `@Transactional(warehouse)` boundary — safe at D-26 scale (≤20 mappings/cat). _(Architect)_

**New Key Decisions** (beyond frozen ADR-001..004):
- ADR-005: Attach new Thrift methods to existing `PointsEngineRuleConfigThriftImpl` — no new handler class. _(Architect)_
- ADR-006: Idempotency response `204 No Content` for both "activate already-active" and "deactivate already-inactive". _(Architect)_
- ADR-007: Schema indexes: `(org_id, program_id)` + `(org_id, program_id, is_active)` on `benefit_categories`; `(org_id, benefit_category_id, is_active)` + `(org_id, slab_id, is_active)` on `benefit_category_slab_mapping`. NO declared FK. _(Architect)_
- ADR-009: Error codes defined — `BC_NAME_TAKEN_ACTIVE`, `BC_CROSS_PROGRAM_SLAB`, `BC_UNKNOWN_SLAB`, `BC_INACTIVE_WRITE_FORBIDDEN`, `BC_NAME_TAKEN_ON_REACTIVATE`, `BC_NOT_FOUND`, `BC_PAGE_SIZE_EXCEEDED`, `BC_NAME_LOCK_TIMEOUT`. _(Architect)_
- ADR-010: Writes require `BasicAndKey`; GETs accept `KeyOnly` or `BasicAndKey`; no `@PreAuthorize('ADMIN_USER')` unless product opts in (Q1). _(Architect)_
- ADR-011: GET list defaults `size=50`, max `100`, fixed `ORDER BY created_on DESC, id DESC`. _(Architect)_
- ADR-012: Advisory lock `GET_LOCK('bc_uniq_{orgId}_{programId}_{md5(name)}', 2)` around uniqueness check-then-insert; timeout exceeds → 409 `BC_NAME_LOCK_TIMEOUT`. _(Architect)_
- ADR-013: Deployment order cc-stack-crm (DDL) → thrift-ifaces (IDL v1.84) → emf-parent → intouch-api-v3. _(Architect)_
- Thrift method count: 6 total (`createBenefitCategory`, `updateBenefitCategory`, `getBenefitCategory`, `listBenefitCategories`, `activateBenefitCategory`, `deactivateBenefitCategory`) — supersedes earlier "8 new methods" count from Phase 5 cross-repo trace (ADR-003 subsumed mapping CRUD into parent DTO). _(Architect)_

**New Constraints**:
- C-27: NO `version` column on either table; NO `@Version` on entities; NO `version` in DTO — propagates from ADR-001. _(Architect)_
- C-28: Every DAO method takes `orgId` as explicit parameter (G-07.1 mitigation). Cross-tenant IT mandatory in Phase 9 (G-11.8). _(Architect)_
- C-29: Cascade-deactivate MUST be executed in the same `@Transactional(warehouse)` boundary as the parent `is_active=false` update. _(Architect)_
- C-30: GET list MUST use bulk mapping fetch (`findActiveSlabIdsForCategories(orgId, List<Integer>)`) — NO N+1 (G-04.1). _(Architect)_
- C-31: All `Date ↔ i64` conversions in the EMF Thrift handler MUST use explicit UTC TimeZone (not JVM default). OQ-38 still open for prod TZ confirmation. _(Architect)_

**New Open Questions for Phase 7 (Designer)** — all numbered Q7-01..Q7-10 as listed in `01-architect.md` §12:
- [ ] Q7-01: Name normalization (trim, case sensitivity, max length, empty/NULL, NFC). _(Architect)_
- [ ] Q7-02: Advisory-lock key hashing format (md5 length vs MySQL lock-name limit). _(Architect)_
- [ ] Q7-03: Facade class name (`BenefitCategoryFacade` vs `BenefitCategoryService` — platform naming). _(Architect)_
- [ ] Q7-04: Controller package path (`resources` vs `controllers` convention). _(Architect)_
- [ ] Q7-05: GET list wrapper shape (pagination fields inside `ResponseWrapper.data` or alongside). _(Architect)_
- [ ] Q7-06: Thrift field naming — bare `createdOn` (recommended, pointsengine_rules.thrift convention) vs `*InMillis` (emf.thrift convention). _(Architect)_
- [ ] Q7-07: Activate-flow response body `204` vs `200 + dto`. _(Architect)_
- [ ] Q7-08: Cross-tenant IT fixture strategy (Testcontainers multi-org vs H2). _(Architect)_
- [ ] Q7-09: Aurora MySQL version ≥ 8.0.13 for partial unique index fallback. _(Architect)_
- [ ] Q7-10: Audit-column write mechanism (manual `new Date()` in service vs `@PrePersist`/`@PreUpdate` — recommend manual per platform). _(Architect)_

**New User-facing Questions (block Phase 7 until resolved)**:
- [x] Q1: ✅ **resolved by D-37** — BasicAndKey only, no admin-only gate in MVP (CONFIRMS ADR-010).
- [x] Q2: ✅ **resolved by D-38** — accept the race at D-26 scale; no advisory lock, no partial unique index (OVERRIDES ADR-012).
- [x] Q3: ✅ **resolved by D-39** — asymmetric: `PATCH /activate` = 200 + DTO on state change / 204 on idempotent; `PATCH /deactivate` = 204 always (OVERRIDES ADR-006 symmetric default).
- [x] Q4: ✅ **resolved by D-40** — Aurora MySQL version confirmation deferred to Phase 12 Blueprint runbook.

---

## Designer Phase 7 — Additions

**New Codebase Behaviour findings** (from Designer Step 0 pattern discovery):
- `Benefits.java` (emf-parent) is the canonical JPA entity exemplar — hand-written getters/setters, `extends OrgEntityIntegerPKBase`, `@Embeddable` PK inner class, `@Temporal(TemporalType.TIMESTAMP)` on Date fields. Designer prescribes same pattern for `BenefitCategory` + `BenefitCategorySlabMapping`. _(Designer P-01)_
- `BenefitsDao` (emf-parent) is the DAO exemplar — extends platform base DAO, takes `orgId` as explicit parameter on every method (C-28 upheld). _(Designer P-02)_
- `PointsEngineRuleConfigThriftImpl.createOrUpdateBenefit` is the Thrift handler error-mapping exemplar — wraps business exceptions in `PointsEngineRuleServiceException` with `statusCode` set. Designer prescribes same wrapper pattern for all 6 BC handlers with `statusCode=409` for conflict errors. _(Designer P-03)_
- `PointsEngineRuleService.createOrUpdateSlab` is the transactional service exemplar — `@Transactional(value="warehouse")` + `@DataSourceSpecification(schemaType=WAREHOUSE)` at class level. _(Designer P-04)_
- `TargetGroupController` is the REST controller exemplar — `@RestController @RequestMapping("/v3/...")` + `ResponseEntity<ResponseWrapper<T>>` return type + `@Valid` on request body. _(Designer P-05)_
- `TargetGroupErrorAdvice` is the exception-mapping exemplar — Designer prescribes adding `@ExceptionHandler(ConflictException.class)` → 409 (D-31 reified). _(Designer P-06)_
- 17 patterns P-01..P-17 fully prescribed with file:line citations in `03-designer.md` §D. _(Designer)_

**Type Inventory Decisions** (frozen by Designer, ready for SDET RED):
- **IDL additions (Thrift repo)**: `enum BenefitCategoryType`, `struct BenefitCategoryDto`, `struct BenefitCategoryFilter`, `struct BenefitCategoryListResponse`, 6 methods on `PointsEngineRuleService`. Pom bump `1.83 → 1.84`. _(Designer §A)_
- **emf-parent NEW (9 files)**: `BenefitCategory` + inner `@Embeddable` PK, `BenefitCategorySlabMapping` + inner PK, `BenefitCategoryType` enum, `BenefitCategoryDao`, `BenefitCategorySlabMappingDao`, `CategorySlabTuple` bulk-fetch tuple, 2 Flyway DDL files. _(Designer §A)_
- **emf-parent MODIFIED (5 files)**: `PointsEngineRuleConfigThriftImpl` (+6 handlers), `PointsEngineRuleEditorImpl` (+6 editor methods), `PointsEngineRuleService` (+6 `@Transactional(warehouse)` methods), `pom.xml` (Thrift IDL bump), `.gitmodules` (cc-stack-crm submodule bump). _(Designer §A)_
- **intouch-api-v3 NEW (7 files)**: `BenefitCategoriesV3Controller`, `BenefitCategoryFacade`, `ConflictException`, 4 DTOs (`CreateRequest`, `UpdateRequest`, `Response`, `ListPayload`). _(Designer §A)_
- **intouch-api-v3 MODIFIED (2 files)**: `TargetGroupErrorAdvice` (+409 handler), `pom.xml`. _(Designer §A)_
- **cc-stack-crm NEW (2 files)**: DDL files for `benefit_categories` and `benefit_category_slab_mapping`. _(Designer §A)_

**Facade Contract Decisions** (resolves Architect open questions Q7-03, Q7-04, Q7-07 per D-39):
- Facade class suffix = `Facade` (not `Service` in intouch-api-v3 — distinguishes from emf-parent's Service layer). Package = standard `facade` or nearest exemplar. _(Designer §F resolves Q7-03)_
- Controller package = `resources` (matches platform convention per code-analysis-intouch-api-v3). _(Designer §F resolves Q7-04)_
- `BenefitCategoryFacade.activate()` returns `Optional<BenefitCategoryResponse>` — empty on idempotent no-op (→204), populated on state change (→200+DTO). _(Designer §F — per D-39)_
- `BenefitCategoryFacade.deactivate()` returns `void` — controller always returns 204. _(Designer §F — per D-39)_

**Service/DAO Behaviour Decisions**:
- Pre-insert uniqueness check = `dao.findActiveByNameAndOrgAndProgram(orgId, programId, name.trim())`. NO `GET_LOCK` — D-38 accepted-race posture. _(Designer §B — reifies D-38)_
- Slab-existence validation: bulk `ProgramSlabDao.findMissingIdsForProgram(orgId, programId, Set<Integer>)` — if non-empty, throw `ConflictException(BC_UNKNOWN_SLAB)` with the offender list. _(Designer §B — O(1) DB round-trip)_
- Cross-program slab check: `ProgramSlab.programId != category.programId` → `ConflictException(BC_CROSS_PROGRAM_SLAB)`. _(Designer §B)_
- `syncSlabMappings(categoryId, newIdSet)` = 3-step diff-and-apply: (1) `findActiveSlabIdsForCategory` → current active set; (2) compute INSERT = new − current, SOFT-DELETE = current − new; (3) bulk INSERT + bulk UPDATE `SET is_active=false WHERE id IN (...)`. All within parent service method's `@Transactional(warehouse)`. _(Designer §B — reifies D-35)_
- Idempotent-dedup: `LinkedHashSet<>(request.slabIds())` at facade entry drops duplicates silently (preserves insertion order for deterministic testing). _(Designer §F resolves D-35 dedup clause)_

**Error Mapping Frozen** (per ADR-009, D-31, D-38):
- `BC_NAME_TAKEN_ACTIVE` → 409 (D-28 active-duplicate). _(Designer §E)_
- `BC_CROSS_PROGRAM_SLAB` → 409 (slab belongs to different program). _(Designer §E)_
- `BC_UNKNOWN_SLAB` → 409 (slab doesn't exist in org). _(Designer §E)_
- `BC_INACTIVE_WRITE_FORBIDDEN` → 409 (PUT on soft-deleted category per D-27 amendment). _(Designer §E)_
- `BC_NAME_TAKEN_ON_REACTIVATE` → 409 (reactivate when name now taken by another active category per D-34 clause e). _(Designer §E)_
- `BC_NOT_FOUND` → 404 (category doesn't exist or wrong org). _(Designer §E)_
- `BC_PAGE_SIZE_EXCEEDED` → 400 (list request size > 100 per ADR-011). _(Designer §E)_
- ~~`BC_NAME_LOCK_TIMEOUT`~~ **STRICKEN** per D-38 — no advisory lock, no lock timeout error. _(Designer §E aligned with D-38)_

**New Constraints**:
- C-35: All new JPA entities use hand-written getters/setters (NOT Lombok) — matches platform convention. Q7-14 flagged as Designer assumption pending user confirmation. _(Designer)_
- C-36: DTO↔Thrift mapper classes live in intouch-api-v3 facade package (`*Mapper` suffix) — NOT in IDL repo. Q7-15 flagged as Designer assumption pending user confirmation. _(Designer)_
- C-37: `created_on` / `updated_on` set via manual `new Date()` in service methods (NOT `@PrePersist`/`@PreUpdate`) — matches platform convention. Resolves Architect Q7-10. _(Designer P-12)_
- C-38: All timestamp fields in Thrift IDL use bare names (`createdOn`, `updatedOn`) — NOT `*InMillis` suffix. Resolves Architect Q7-06. _(Designer P-13)_

**Designer Open Questions** (to be resolved before Phase 8 QA — Q7-11..Q7-15):
- [ ] Q7-11: Does `PeProgramSlabDao` already have a batch-existence method (e.g., `findMissingIdsForProgram` or similar)? If not, Designer adds a new method on `PeProgramSlabDao`. _(Confidence C4 — need to verify)_
- [ ] Q7-12: GET by id — return active-only or active+inactive (i.e., can admin fetch a soft-deleted category for audit purposes)? Designer's C4 assumption: active-only by default, `?includeInactive=true` query param for audit. _(Confidence C4 — product decision)_
- [ ] Q7-13: Activate no-op signalling — Designer's C5 assumption is `stateChanged` field on `BenefitCategoryResponse` DTO to let controller distinguish state-change vs idempotent. Alternative: facade returns `Optional` and controller uses presence/absence. Designer prefers Optional (cleaner contract). _(Confidence C5 — needs user confirm)_
- [ ] Q7-14: Entity boilerplate — hand-written getters/setters (platform convention, Designer's C5 default) vs Lombok `@Getter @Setter`. _(Confidence C5 — style preference)_
- [ ] Q7-15: DTO↔Thrift mapper class placement — intouch-api-v3 facade package `*Mapper` (Designer's C5 default) vs shared utility package. _(Confidence C5 — style preference)_

**Phase 7 Artifact**: `03-designer.md` (1230 lines, 7 sections A–G + appendix, 17 patterns P-01..P-17, 26 new types + 8 modified types inventoried, full compile-safe signatures).

**Phase 7 Confidence**: RED-phase readiness = **true**. Every interface signature is compile-safe; SDET Phase 9 can import the types, generate skeletons throwing `UnsupportedOperationException`, and write failing tests. Designer open questions Q7-11..Q7-15 impact Phase 10 bodies/IDL details only, NOT RED-phase test scaffolding.

---

## Designer Phase 7 — Question Resolutions (2026-04-18)

User answered all 5 Designer open questions as `Q7:C, Q12:A, Q13:A, Q14:A, Q15:A`. Details in §18 of `03-designer.md`. New decisions below.

**Designer Open Questions — all now RESOLVED**:
- [x] Q7-11 → **D-41**: **C** — Reuse existing `PeProgramSlabDao.findByProgram(orgId, programId)` + in-memory Set ops. NO cross-repo DAO modification. Justified by D-26 SMALL-scale envelope (≤10 slabs typical, hard cap small). Service layer:
  ```java
  Set<Integer> existing = programSlabDao.findByProgram(orgId, programId).stream()
                             .map(ps -> ps.getPk().getId()).collect(toSet());
  Set<Integer> missing = new HashSet<>(candidateSlabIds); missing.removeAll(existing);
  if (!missing.isEmpty()) throw BC_UNKNOWN_SLAB(missing);
  ```
  Evidence C7: `pointsengine-emf/.../PeProgramSlabDao.java:27` has only `findByProgram(orgId, programId) → List<ProgramSlab>`; no batch-existence variant.
- [x] Q7-12 → **D-42**: **A** (user OVERRIDES Designer recommendation B). `GET /v3/benefitCategories/{id}` supports `?includeInactive=true` audit query param. Default (`false`) returns active-only (404 on soft-deleted). Opt-in (`true`) returns any state. DAO split: `findByOrgIdAndId` (any state) + `findActiveByOrgIdAndId` (active only; used by default GET AND all mutation paths per D-27).
- [x] Q7-13 → **D-43**: **A** — `BenefitCategoryDto` Thrift struct field 12 `optional bool stateChanged = true`. On idempotent no-op, EMF returns DTO with `stateChanged=false`; facade detects this → `Optional.empty()` → controller emits 204. On state change, DTO populated → 200 + wrapper.
- [x] Q7-14 → **D-44**: **A** — split convention. JPA entities hand-written (match `Benefits.java` P-01 exemplar; JPA providers can be sensitive to Lombok on `@Embeddable` PK). DTOs in intouch-api-v3 use Lombok `@Getter @Setter` (grep evidence: 305 files in intouch-api-v3 use `@Getter`/`@Setter`).
- [x] Q7-15 → **D-45**: **A** — dedicated `BenefitCategoryResponseMapper` in `com.capillary.intouchapiv3.facade.benefitCategory.mapper` subpackage. `@Component`, stateless, SDET-unit-testable in isolation. Exemplar: `intouch-api-v3/.../unified/promotion/mapper/CustomerPromotionResponseMapper.java`.

**New Key Decisions (D-41..D-45)** — appended to the Key Decisions table:

| # | Decision | Rationale | Phase | Date |
|---|----------|-----------|-------|------|
| D-41 | **Reuse existing `PeProgramSlabDao.findByProgram(orgId, programId)` + in-memory Set ops for slab existence/cross-program validation (Q7-11=C)**. NO cross-repo DAO modification. Service layer iterates/collects into a Set<Integer> and subtracts the candidate list to find missing slabIds; wrong-program slabs naturally fall out of the in-memory set (same BC_UNKNOWN_SLAB error path). Supersedes A7-13 which assumed we would need to add a new DAO method. | D-26 SMALL-scale envelope makes in-memory filtering negligible (~5-10 rows typical per program); avoids cross-repo blast radius | Phase 7→8 gate | 2026-04-18 |
| D-42 | **GET /{id} supports `?includeInactive=true` audit query param (Q7-12=A — OVERRIDES Designer rec B)**. Default active-only (404 on soft-deleted). Opt-in returns any state. Two DAO methods on `BenefitCategoryDao`: `findByOrgIdAndId` (any state) + `findActiveByOrgIdAndId` (active only; also used by all mutation paths per D-27). Thrift IDL `getBenefitCategory` gains optional `bool includeInactive=false` parameter. | Richer API surface supports audit access without requiring a follow-up endpoint; user explicitly preferred this over YAGNI active-only-always. | Phase 7→8 gate | 2026-04-18 |
| D-43 | **Activate no-op signalling via `BenefitCategoryDto.stateChanged` field (Q7-13=A)**. Thrift struct `BenefitCategoryDto` field 12 = `optional bool stateChanged = true`. On idempotent already-active, EMF returns the DTO populated EXCEPT `stateChanged=false`; facade sees that and returns `Optional.empty()` → controller emits 204 No Content. On true state change, `stateChanged=true` (default) → facade returns populated Optional → 200 + wrapper. | Least-invasive option: HTTP 304 is not idiomatic on PATCH (rejected b); null return violates Thrift `required` return semantics (rejected c); sentinel field is explicit and single-method-scoped. | Phase 7→8 gate | 2026-04-18 |
| D-44 | **DTO/Entity boilerplate split (Q7-14=A)**. JPA entities (emf-parent: `BenefitCategory`, `BenefitCategorySlabMapping`, inner `@Embeddable` PK classes) use HAND-WRITTEN getters/setters/equals/hashCode per P-01 `Benefits.java` exemplar. REST DTOs (intouch-api-v3: `BenefitCategoryCreateRequest`, `*UpdateRequest`, `*Response`, `*ListPayload`) use Lombok `@Getter @Setter` per established intouch-api-v3 pattern (grep evidence: 305 Lombok files in repo). | JPA providers can be sensitive to Lombok on `@Embeddable` PK classes (equality/hash contract); DTOs are plain POJOs where Lombok is platform convention. | Phase 7→8 gate | 2026-04-18 |
| D-45 | **Dedicated mapper class in `mapper/` subpackage (Q7-15=A)**. NEW class `BenefitCategoryResponseMapper` in `com.capillary.intouchapiv3.facade.benefitCategory.mapper`. `@Component`, stateless; owns Thrift DTO ↔ REST response DTO, REST request DTOs → Thrift DTO, list unwrap/rewrap, plus static helpers `millisToDate` / `dateToMillis` (ADR-008 UTC conversion). SDET-unit-testable without Spring context. Exemplar verified: `intouch-api-v3/.../unified/promotion/mapper/CustomerPromotionResponseMapper.java`. Supersedes C-36's tentative location (was "facade package with `*Mapper` suffix"). | Dedicated stateless mapper is SDET-preferred (clean isolated unit test for mapping rules incl. UTC timestamp conversion); established platform pattern. | Phase 7→8 gate | 2026-04-18 |

**Constraint updates**:
- ~~C-35~~ **AMENDED** (Q7-14 resolved via split): C-35 now reads "**emf-parent JPA entities** use hand-written getters/setters/equals/hashCode (matches `Benefits.java` P-01). intouch-api-v3 DTOs use Lombok `@Getter @Setter` per D-44." Supersedes prior wording.
- ~~C-36~~ **AMENDED** (Q7-15 resolved): C-36 now reads "DTO↔Thrift mapper lives in dedicated `com.capillary.intouchapiv3.facade.benefitCategory.mapper` subpackage as `BenefitCategoryResponseMapper` per D-45. Exemplar `CustomerPromotionResponseMapper`." Supersedes prior wording.
- **C-39 (NEW)**: `GET /v3/benefitCategories/{id}` MUST accept `?includeInactive=true` query parameter. When absent or `false`, soft-deleted categories return 404. When `true`, soft-deleted categories return 200 with `isActive=false` in the body. Audit path is read-only and does NOT bypass tenant `orgId` scoping (G-07). Source: D-42.

**Downstream phase obligations (resolved)**:
- Phase 8 (QA): include scenarios for `?includeInactive=true` audit path (200 + inactive DTO) vs default path (404 on inactive); mapper unit tests; `stateChanged=false` → 204 idempotency.
- Phase 9 (SDET, RED): test files for `BenefitCategoryResponseMapper` in isolation; `?includeInactive=true` integration test branching; two-DAO-method wiring (`findByOrgIdAndId` vs `findActiveByOrgIdAndId`); activate idempotency assertions on `stateChanged`.
- Phase 10 (Dev, GREEN): implement in-memory Set op for D-41 slab validation; implement mapper in `mapper/` subpackage; implement `stateChanged` flip in activate service method.

---

## QA Phase 8 — Additions

**Phase 8 Artifact**: `04-qa.md` (77 scenarios across 6 operations + 9 edge cases + 8 guardrail tests + 4 audit trail tests; 47 P0 / 23 P1 / 7 P2; 1,102 lines, ~48KB).

**New Risks & Concerns**:
- [risk] `BC_BAD_ACTIVE_FILTER` (400 on invalid `?isActive=foo` value) is implied by Designer Assumption A7-07 but the error code string is not confirmed in ADR-009. SDET needs this string before Phase 9. _(QA)_ — Status: open
- [risk] `NotFoundException → HTTP 200` platform quirk (OQ-45): 10+ QA scenarios assert HTTP 200 + error body for "not found". If product fixes this to HTTP 404 in a concurrent ticket, all these assertions will break. _(QA)_ — Status: open
- [risk] `BenefitCategoryUpdateRequest.slabIds` allows empty list (`[]`) based on `@NotNull` without `@Size(min=1)` in Designer §F.8. If product requires "at least one active slab at all times" for an active category, this is a gap. _(QA)_ — Status: open

**New Open Questions**:
- [ ] Q8-01: Is empty `slabIds` on PUT allowed (clears all mappings) or rejected with 400? _(QA)_
- [ ] Q8-02: Is name uniqueness check case-sensitive or case-insensitive? _(QA)_
- [ ] Q8-03: Confirm `BC_BAD_ACTIVE_FILTER` error code string for `?isActive=foo` validation error. _(QA)_

**Resolved from QA analysis**:
- [x] D-38 (accepted race) — documented in QA-061/QA-073 as non-asserting behaviour scenarios. _(resolved by QA)_
- [x] D-39 (asymmetric activate) — covered by QA-047 (200+DTO on state change) and QA-048 (204 on no-op). _(resolved by QA)_
- [x] D-43 (stateChanged field) — QA-048 asserts 204 No Content on already-active activate with `stateChanged=false`. _(resolved by QA)_
- [x] D-42 (?includeInactive) — QA-017 (default active-only 404) and QA-018 (audit path 200+inactive DTO) cover both branches. _(resolved by QA)_

**Key QA Scenario IDs by operation** (for cross-reference in SDET/Developer phases):
- CREATE: QA-001..QA-013
- GET-BY-ID: QA-014..QA-019
- LIST: QA-020..QA-027
- UPDATE: QA-028..QA-041
- ACTIVATE: QA-042..QA-050 + QA-065
- DEACTIVATE: QA-051..QA-056
- Edge Cases: QA-057..QA-065
- Guardrail Tests: QA-066..QA-073
- Audit Trail: QA-074..QA-077

**Phase 8 Confidence**: C6 — all scenarios anchored to source decisions D-01..D-45, ADR-001..013, and AC-BC01'..AC-BC12 with traceability matrix. Three open questions (Q8-01..Q8-03) at C4 need resolution before Phase 9 SDET writes assertions for those areas.

**Phase 7 Artifact updated**: `03-designer.md` — in-place amendments to §A, §B.3, §F.6/F.6a/F.7/F.8/F.10; new §18 Post-LLD Amendments section documenting D-41..D-45 + C-39; §G.1 questions marked RESOLVED; §G.2 A7-13 struck.

**Phase 7 Confidence (updated)**: RED-phase readiness still **true**. All amendments preserve compile-safety. SDET Phase 9 can proceed.

## QA Phase 8 — Question Resolutions (2026-04-18)

### Key Decisions (D-46..D-48)

| # | Decision | Source | Phase | Date |
|---|---|---|---|---|
| D-46 | **`BenefitCategoryUpdateRequest.slabIds` requires `@Size(min=1)` (Q8-01=b — matches orchestrator reco)**. Empty list `[]` on PUT is rejected at Bean Validation with HTTP 200 + platform `VALIDATION_FAILED` envelope (OQ-45 quirk). Symmetric with CreateRequest; a benefit category with zero active slab mappings is semantically meaningless. Admin wanting to "clear all slabs" must `PATCH /{id}/deactivate` the entire category instead — the soft-delete path cascades mapping soft-delete per D-06. **Designer §F.8 artifact**: `@Size(min=1)` annotation added to Update request slabIds field. **Service layer simplification**: no longer needs to handle "empty incoming set → soft-delete all active mappings" edge case in `syncSlabMappings()`. **Phase 8 QA obligation**: QA-032 amended — was "empty slabIds permitted, 200 OK" (P1), is now "empty slabIds rejected 400" (P0). **Phase 9 SDET obligation**: add Bean Validation unit test asserting `@Size(min=1)` rejection with correct field path in envelope. **Confidence**: C6 — user decision, consistent with D-35 Create validation, Phase 8 QA assumption A8-01 superseded. | User choice b on Phase 8 Q8-01 | Phase 8→8b | 2026-04-18 |
| D-47 | **Name uniqueness check is CASE-SENSITIVE (Q8-02=a — USER OVERRIDE of orchestrator reco b)**. `"Gold Tier"` and `"gold tier"` coexist as distinct active categories within same `(orgId, programId)`. **Rationale**: (a) backward compatibility with loyalty platform byte-comparison convention (no `LOWER()` in existing queries per A7-06); (b) avoids a DDL change to add a functional unique index on `LOWER(name)` — which would require Aurora/MySQL version check (Q4/D-40 deferred); (c) preserves admin ability to disambiguate legacy data via casing if ever needed; (d) if case-insensitivity becomes a product requirement post-GA, adding `LOWER()` is a straightforward forward migration with no breaking impact on existing data. **Designer code impact: ZERO** — DAO query `findActiveByNameAndOrgAndProgram(orgId, programId, name)` already uses `name = ?` without `LOWER()`; unique index on `benefit_categories (org_id, program_id, name)` remains byte-comparison. **Promotes A8-02 (C5 assumption) → D-47 (C6 decision)** — no longer a soft assumption. **Phase 8 QA obligation**: QA-004 amended with case-sensitivity note; **QA-004b** NEW — "POST with `name:'gold tier'` succeeds 201 when `'Gold Tier'` exists active in same program". **Phase 9 SDET obligation**: SDET implements QA-004b alongside QA-004. **Risk note**: if a product team member raises "VIP Perks vs vip perks collision" as a support ticket post-GA, revisit-trigger → migration to case-insensitive index (single ALTER + backfill-dedupe pass). **Confidence**: C6 — user decision, code already aligns, revisit path clear. | User choice a on Phase 8 Q8-02 (override of reco b) | Phase 8→8b | 2026-04-18 |
| D-48 | **`?isActive=foo` (invalid filter value) uses platform `VALIDATION_FAILED`, no bespoke `BC_*` code (Q8-03=c — matches orchestrator reco)**. Spring MVC's `@RequestParam` type coercion on `boolean isActive` field fails with a `MethodArgumentTypeMismatchException` for unrecognised values (`"foo"`, `"yes"`, `"1"` outside true/false). `TargetGroupErrorAdvice` platform exception handler already maps this to the standard `VALIDATION_FAILED` code in the `ResponseWrapper.errors[]` envelope — no new code needed. **Rationale**: YAGNI; exactly one filter param with one failure mode; existing platform infrastructure handles it cleanly. **ADR-009 amendment (Phase 11 Reviewer)**: error taxonomy row for `BC_BAD_ACTIVE_FILTER` removed; replaced with "invalid `isActive` value → platform standard `VALIDATION_FAILED` via `TargetGroupErrorAdvice`". **Phase 8 QA obligation**: Error Coverage Matrix (§11) row for `BC_BAD_ACTIVE_FILTER` removed; `VALIDATION_FAILED` row added referencing new QA-022b. **Phase 9 SDET obligation**: add QA-022b — "`GET /v3/benefitCategories?isActive=foo` → HTTP 200 + `VALIDATION_FAILED` code with field path `isActive`". **Phase 10 Developer obligation**: no new error code constant; controller just declares `@RequestParam(required=false) Boolean isActive` and lets Spring's converter throw. **Confidence**: C6 — user decision; reuses existing platform pattern; no new code footprint. | User choice c on Phase 8 Q8-03 | Phase 8→8b | 2026-04-18 |

### Constraint Amendments (2026-04-18 — Phase 8 resolution)

- **C-40 (NEW)**: `BenefitCategoryUpdateRequest.slabIds` MUST carry `@Size(min=1)` (not just `@NotNull`) — symmetric with CreateRequest (per D-46). Enforced at Bean Validation layer before service logic runs.

### Superseded Assumptions

- **A8-01 (Phase 8 QA C5 assumption — "empty slabIds on PUT permitted")**: SUPERSEDED by D-46. No longer a soft assumption; Designer §F.8 amended; QA-032 expectation flipped from "200 state change" to "400 Bean Validation reject".

### Promoted Assumptions

- **A8-02 (Phase 8 QA C5 assumption — "name uniqueness case-sensitive")**: PROMOTED to D-47 (C6 decision) via user confirmation. No code change — DAO query already byte-comparison; DDL index already byte-comparison.

### Downstream Phase Obligations

- **Phase 8b Business Test Gen**: map all 79 scenarios (77 original + QA-004b case-distinct + QA-022b platform validation) → BT-xx traceability matrix. Use D-46..D-48 as additional hard-constraint inputs alongside D-01..D-45.
- **Phase 9 SDET RED**: implement 79 scenarios + mapper unit tests + `@Size(min=1)` Bean Validation UT + `VALIDATION_FAILED` platform integration UT.
- **Phase 10 Developer**: apply `@Size(min=1)` on UpdateRequest.slabIds (single-line change); no new error code constants for `BC_BAD_ACTIVE_FILTER` (D-48).
- **Phase 11 Reviewer**: amend ADR-009 error taxonomy (strike `BC_BAD_ACTIVE_FILTER`; note platform `VALIDATION_FAILED` used instead).

---

## Business Test Gen Phase 8b — Additions

**Phase 8b Artifact**: `04b-business-tests.md` (101 BT cases + 6 guardrail BT-G tests; 7 sections; full traceability matrix BA→Designer→QA→BT).

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total BT cases | 101 (BT-001..BT-101) + 6 guardrail (BT-G01a, BT-G01b, BT-G05, BT-G07a, BT-G07b, BT-G10) |
| Unit Tests (UT) | 28 — Bean Validation, mapper, ArchUnit structural checks |
| Integration Tests (IT) | 73 — HTTP/DB/Thrift flows with Testcontainers |
| P0 (smoke) | 52 |
| P1 (regression) | 33 |
| P2 (edge/compliance) | 16 |

### BT Case Ranges by Operation

| Operation | BT Range | Count |
|-----------|----------|-------|
| CREATE | BT-001..BT-013 | 13 |
| GET-BY-ID | BT-014..BT-019 | 6 |
| LIST | BT-020..BT-027 + BT-022b | 9 |
| UPDATE | BT-028..BT-041 | 14 |
| ACTIVATE | BT-042..BT-050 | 9 |
| DEACTIVATE | BT-051..BT-056 | 6 |
| EDGE CASES | BT-057..BT-063 | 7 |
| INTEGRATION (cross-boundary) | BT-064..BT-079 | 16 |
| COMPLIANCE (ADR/Decision/Guardrail) | BT-080..BT-101 + BT-G01a/b/G05/G07a/b/G10 | 22+6=28 |

### New Key Decisions (test strategy)

| # | Decision | Rationale | Phase | Date |
|---|----------|-----------|-------|------|
| test-01 | **Business test classification: 28 UTs for pure logic + 73 ITs for all HTTP/DB/Thrift interactions**. UTs cover Bean Validation (field-level constraints, null/size guards), mapper (`BenefitCategoryResponseMapper` — millis↔UTC string, Thrift→REST, REST→Thrift), and ArchUnit structural checks (`@Transactional(warehouse)` + `orgId` parameter convention). ITs use Testcontainers for all DB + Thrift assertions. | Platform Thrift RPC chain requires a real MySQL container for meaningful integration assertions. Testcontainers mandatory per G-11.3. Pure logic in mapper/validators is test-free without container overhead. | Phase 8b | 2026-04-18 |
| test-02 | **D-43 stateChanged sentinel — tested in BT-047 and BT-048 independently**. BT-047 asserts `stateChanged=true` path: `PATCH /activate` on inactive category → 200 + full DTO. BT-048 asserts `stateChanged=false` path: `PATCH /activate` on already-active category → 204 No Content with empty body. Facade `Optional.empty()` branch must be tested separately from Thrift struct field inspection. | The two branches exercise structurally different code paths: one returns a populated DTO, the other returns empty. A single happy-path test would leave the idempotency branch unexercised at the IT level. | Phase 8b | 2026-04-18 |
| test-03 | **D-47 case-sensitive uniqueness — BT-004b added as explicit mandatory case alongside BT-004 (collision)**. BT-004 asserts POST with existing `name="Gold Tier"` in same program → 409. BT-004b asserts POST with `name="gold tier"` when `"Gold Tier"` already active in same program → 201 Created. These are distinct test cases with opposite expected outcomes. | Case-sensitive uniqueness (D-47, user override) allows casing variants to coexist; a test asserting only collision would leave this user override unvalidated. BT-004b is the only test that proves the byte-comparison semantics are operative. | Phase 8b | 2026-04-18 |

### Coverage Verification (all dimensions 100%)

| Coverage Dimension | Covered | Total |
|--------------------|---------|-------|
| In-scope ACs (AC-BC01'..AC-BC12) | 4 | 4 |
| Error codes (BC_NAME_TAKEN_ACTIVE, BC_CROSS_PROGRAM_SLAB, BC_UNKNOWN_SLAB, BC_INACTIVE_WRITE_FORBIDDEN, BC_NAME_TAKEN_ON_REACTIVATE, BC_NOT_FOUND, BC_PAGE_SIZE_EXCEEDED, VALIDATION_FAILED, BC_DEACTIVATED_ALREADY, BC_ACTIVATED_ALREADY, server error) | 11 | 11 |
| ADRs (ADR-001..ADR-013) | 13 | 13 |
| Frozen Decisions (D-33..D-48) | 16 | 16 |
| Guardrails (G-01/G-05/G-07/G-10) | 4 | 4 |
| QA Scenarios (QA-001..QA-077 + QA-004b + QA-022b) | 79 | 79 |

### Mandatory Coverage (Critical Rules from SKILL.md — all satisfied)

| Decision | Mandatory BT | Status |
|----------|-------------|--------|
| D-47 (case-sensitive uniqueness) | BT-004b — case-distinct name POST succeeds when other casing active | COVERED |
| D-48 (VALIDATION_FAILED for bad isActive) | BT-022b — `?isActive=foo` → HTTP 200 + VALIDATION_FAILED | COVERED |
| D-46 (UpdateRequest.slabIds @Size(min=1)) | BT-032 (IT: empty list → 400) + BT-101 (UT: Bean Validation constraint) | COVERED |
| D-42 (includeInactive paths) | BT-017 (active-only default → 404 on inactive) + BT-018 (includeInactive=true → 200+inactive DTO) | COVERED |
| D-39 + D-43 (asymmetric activate) | BT-047 (stateChanged=true → 200+DTO) + BT-048 (stateChanged=false → 204) | COVERED |
| D-35 (diff-apply cases) | BT-029 (add new slabs), BT-030 (remove slabs), BT-031 (replace full set), BT-033 (re-add previously removed = INSERT not reactivate) | COVERED |

### New Open Questions

- [ ] Q-BT-01: Does emf-parent IT harness support direct Thrift embedded server for BT-067 (Thrift contract roundtrip test)? If not, BT-067 must be implemented as a REST-to-DB end-to-end IT without direct Thrift assertion. _(Business Test Gen)_
- [ ] Q-BT-02: Timezone test isolation — confirm `TimeZone.setDefault()` calls in BT-G01b (IST timezone shift) run in a single-threaded context to avoid polluting parallel test threads. JUnit 5 parallel execution or Surefire fork-per-test may be required for isolation. _(Business Test Gen)_

### Resolved Questions

- [x] **Q8-01 (D-46)**: Empty `slabIds` on PUT rejected → BT-032 asserts 400 Bean Validation failure. _(resolved entering Phase 8b)_
- [x] **Q8-02 (D-47)**: Case-sensitive name uniqueness → BT-004b added (case-distinct name permitted). _(resolved entering Phase 8b)_
- [x] **Q8-03 (D-48)**: `VALIDATION_FAILED` for bad `isActive` filter → BT-022b added. _(resolved entering Phase 8b)_

### Downstream Phase Obligations

- **Phase 9 SDET RED**: Implement ALL 107 BT cases (101 numbered + 6 BT-G) as JUnit 4 test methods. Write all as RED-first (assertions before production code). UTs run without Spring context; ITs use Testcontainers for MySQL. Priority execution order: P0 (52) → P1 (33) → P2 (16) per §6 Priority Summary in `04b-business-tests.md`.
- **Phase 10 Developer GREEN**: Make all 107 RED tests pass. No extra tests unless gap found during implementation.
- **Phase 11 Reviewer**: Verify BT→QA→Designer→BA traceability closure. Check BT-G guardrail tests have explicit assertion evidence.

**Phase 8b Confidence**: C6 — 100% coverage on all 6 dimensions verified mechanically; all 79 QA scenarios traced to BT; all 6 SKILL.md critical rules satisfied with named BT IDs.

---

## SDET Phase 9 — Additions (2026-04-18)

**Phase 9 Artifact**: `05-sdet.md` (RED gate artifact — rewritten after salvage operation; 8 sections, full BT coverage map, 7 technical decisions, 6 Mermaid diagrams).

### Salvage Operation — Post-Subagent Corrections

The Phase 9 subagent landed code with four defects; all fixed before commit/tag:

1. **Shade-plugin hack in `thrift-ifaces-pointsengine-rules/pom.xml`** — subagent bypassed the IDL change by adding `maven-shade-plugin` to merge 1.83 classes into 1.84 jar. Reverted via `git checkout -- pom.xml`. Root cause: 1.84-SNAPSHOT already contains 1.83 via backmerge commit `24af9d7`; shading would cause duplicate classes. **TD-SDET-01 REJECTED.**
2. **Missing Thrift IDL additions** — `pointsengine_rules.thrift` had ZERO BenefitCategory struct/enum/service additions. Fixed by hand-adding 109 lines (3 structs, 1 enum, 6 service methods) in commit `22176fd`.
3. **Broken companion interface reference** — emf-parent `PointsEngineRuleConfigThriftImpl` had `implements ... PointsEngineRuleServiceBenefitCategoryMethods` but the interface file did not exist. Removed from `implements` clause; IDL-generated `Iface` now covers the 6 methods.
4. **Wrong Thrift naming convention** — subagent used `actorUserId` + omitted `serverReqId`. Renamed `actorUserId` → `tillId` across 5 files (matches existing `getProgramByTill` lines 557/1096). Added `string serverReqId` as last param on all 6 IDL methods and `String serverReqId` + `@MDCData(requestId="#serverReqId")` on all 6 emf-parent handler methods. Tests pass positional args → no assertion changes.
5. **Stale `@JsonFormat(timezone="UTC")`** on `BenefitCategoryResponse` → changed to `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")` on `createdOn` + `updatedOn` (RFC 3339, second precision, explicit offset). **D-45 revised** (TD-SDET-07).

### RED Gate Status (corrected)

| Repo | Compile | Tests | Confidence |
|------|---------|-------|-----------|
| `thrift-ifaces-pointsengine-rules:1.84-SNAPSHOT` | IDL contracts added (109 lines); `mvn generate-sources` not run locally | n/a | C6 (syntactic; codegen verifies in CI) |
| `intouch-api-v3` (canonical: `intouch-api-v3-2/intouch-api-v3`) | BUILD SUCCESS | 36 run / **1 FAIL + 7 ERRORS = 8 RED** / 28 PASS (structural) | C7 |
| `cc-stack-crm` | DDL only — no build step | Applied via Flyway seed in CI | C6 |
| `emf-parent / pointsengine-emf` | Not verified locally (pre-existing AspectJ 1.7 + Java 17 + missing `com.capillary.shopbook.nrules.*` — see TD-SDET-05) | Not runnable locally | C5 (structural review; CI verifies on push) |

**Phase 9 gate**: READY FOR PHASE 10. intouch-api-v3 RED confirmed C7 (1 failure + 7 errors on behavioural skeletons). emf-parent deferred to CI due to pre-existing env constraint (not introduced by this feature).

### Files Created/Modified (corrected)

**thrift-ifaces-pointsengine-rules** (commit `22176fd`):
- MODIFIED `pointsengine_rules.thrift` — +109 lines (3 structs + 1 enum + 6 service methods with `tillId` + `serverReqId`)
- `pom.xml` — **unchanged** (shade-plugin hack reverted)

**emf-parent / pointsengine-emf** (commit `0b298c3216`, 15 files / +992 insertions):
- NEW `src/main/java/.../benefitcategory/BenefitCategory.java` (JPA entity)
- NEW `src/main/java/.../benefitcategory/BenefitCategorySlabMapping.java` (JPA entity)
- NEW `src/main/java/.../benefitcategory/BenefitCategoryType.java` (Java enum)
- NEW `src/main/java/.../benefitcategory/dao/BenefitCategoryDao.java`
- NEW `src/main/java/.../benefitcategory/dao/BenefitCategorySlabMappingDao.java`
- MODIFIED `src/main/.../editor/PointsEngineRuleEditorImpl.java` — 6 RED skeletons; `actorUserId` → `tillId` on 4 methods
- MODIFIED `src/main/.../external/PointsEngineRuleConfigThriftImpl.java` — 6 RED skeletons; removed broken companion interface; `actorUserId` → `tillId`; `String serverReqId` param + `@MDCData(requestId="#serverReqId")` + `@Trace` on all 6
- MODIFIED `src/main/.../services/PointsEngineRuleService.java` — `actorUserId` → `tillId` on 4 methods
- MODIFIED `pom.xml` — JUnit 5 + Mockito 4.11.0 test deps
- NEW `src/test/.../benefitcategory/BenefitCategoryComplianceTest.java` (6 structural tests — GREEN)
- NEW `src/test/.../benefitcategory/PointsEngineRuleServiceBenefitCategoryRedTest.java` (6 tests; uses `REQ_ID = "red-test-req-id"` constant; concrete `PointsEngineRuleConfigThriftImpl` field type)
- NEW `integration-test/.../db/warehouse/benefit_categories.sql`
- NEW `integration-test/.../db/warehouse/benefit_category_slab_mapping.sql`

**intouch-api-v3-2/intouch-api-v3** (commit `13d62c487`, 13 files / +1119 insertions):
- NEW `src/main/.../models/exceptions/ConflictException.java`
- MODIFIED `src/main/.../exceptionResources/TargetGroupErrorAdvice.java` (+409 handler)
- NEW DTOs under `src/main/.../models/dtos/benefitcategory/`: `BenefitCategoryCreateRequest`, `BenefitCategoryUpdateRequest`, `BenefitCategoryResponse` (with `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` on `createdOn` + `updatedOn`), `BenefitCategoryListPayload`, `BenefitCategoryResponseMapper`
- NEW `src/main/.../facades/BenefitCategoryFacade.java` — 6 stubs throw `UnsupportedOperationException`; **signature uses `tillId`** (not `actorUserId`) on 4 methods
- NEW `src/main/.../resources/BenefitCategoriesV3Controller.java` (`@RestController`, 6 endpoints, no `@DeleteMapping`)
- MODIFIED `pom.xml` — `thrift-ifaces-pointsengine-rules` `1.76` → `1.84-SNAPSHOT`
- NEW tests: `BenefitCategoryDtoValidationTest` (20 GREEN), `BenefitCategoryFacadeRedTest` (10: 8 RED / 2 GREEN), `BenefitCategoryExceptionAdviceTest` (6 GREEN)

**cc-stack-crm** (commit `699bbef63`, 2 files / +40 lines):
- NEW `db/.../benefit_categories.sql` (warehouse DDL)
- NEW `db/.../benefit_category_slab_mapping.sql` (warehouse DDL)

### Technical Decisions (SDET phase — corrected)

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| TD-SDET-01 | ~~Shade plugin merges 1.83 into 1.84 jar~~ | ~~Original claim: 1.84 missing 200+ 1.83 classes.~~ **Root cause was wrong** — 1.84-SNAPSHOT already has 1.83 via backmerge commit `24af9d7`. Shading would cause duplicate classes. | **REJECTED / REVERTED** |
| TD-SDET-02 | Lombok runtime reflection test — use generated methods not `isAnnotationPresent(Getter.class)` | Lombok annotations have CLASS retention, stripped at runtime | ACCEPTED |
| TD-SDET-03 | Mockito `lenient().when()` in `@BeforeEach` for `BenefitCategoryExceptionAdviceTest` | Strict Mockito throws `UnnecessaryStubbingException` when tests don't invoke advice | ACCEPTED |
| TD-SDET-04 | Facade RED tests use behavioural assertions (not `assertThrows`) | `assertThrows(UnsupportedOperationException)` PASSES with stubs — wrong RED semantics | ACCEPTED |
| TD-SDET-05 | emf-parent not buildable offline | Pre-existing AspectJ tools.jar + Java 17 + missing `nrules.*` deps; NOT introduced by this feature | NOTED (blocker is pre-existing) |
| **TD-SDET-06** | **Naming: `tillId` + `serverReqId`** across IDL + all handler/service/editor methods | Matches pre-existing PE convention (`getProgramByTill` line 557/1096); `serverReqId` mandatory for MDC / tracing across every PE service method | ACCEPTED |
| **TD-SDET-07** | **D-45 revised**: `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")` in place of `@JsonFormat(timezone = "UTC")` on `BenefitCategoryResponse.createdOn/updatedOn` | ISO-8601 RFC 3339 compliant; second precision; explicit offset (`+05:30` or `Z`) — clearer for UI consumers than forced UTC conversion | NEEDS UI team confirmation (flagged for Phase 11) |

### Naming Convention (amended)

| Field | Old (subagent draft) | New (frozen) | Location |
|-------|----------------------|--------------|----------|
| Authenticated-user identifier | `actorUserId` | **`tillId`** | IDL methods, emf-parent handler/service/editor, intouch-api-v3 Facade (4 write-path methods) |
| Request correlation id | *(missing)* | **`serverReqId`** | All 6 IDL methods + 6 emf-parent handler methods (as last param, `@MDCData(requestId="#serverReqId")`) |

### BT Coverage: Phase 9 vs Deferred (unchanged)

- **Phase 9 tests cover**: BT-001, BT-004 (partial), BT-008..BT-013, BT-014, BT-018, BT-020, BT-023, BT-028, BT-032..BT-034, BT-045, BT-053, BT-057..BT-059, BT-072, BT-080, BT-082, BT-084, BT-086, BT-091, BT-093..BT-094, BT-096..BT-101 = **34 / 101**
- **Deferred to Phase 10 ITs**: 67 / 101 — all cross-repo write/read paths and Thrift contract round-trips

### Open Questions (Phase 9 outputs)

- [ ] **Q-BT-01** (inherited): emf-parent IT harness support for embedded Thrift server (BT-067) — fallback to REST→DB end-to-end IT documented; decision in Phase 10
- [ ] **Q-BT-02** (inherited): timezone test isolation — SDET defaulted to Surefire fork-per-test plan; confirmation in Phase 10
- [ ] **Q-SDET-08** (new): UI team confirmation of D-45 revised format (`yyyy-MM-dd'T'HH:mm:ssXXX`) — surface in Phase 11 `/api-handoff`
- [ ] **Q-SDET-09** (new): `BenefitCategoriesV3Controller` currently passes `user.getEntityId()` as `tillId`; upgrade to `user.getTillId()` if that accessor exists on the platform `User` model — Phase 10 to confirm

### Commits + Tags (cross-repo)

| Repo | Commit | Lines | Tag |
|------|--------|-------|-----|
| `thrift-ifaces-pointsengine-rules` | `22176fd` | +109 | `aidlc/CAP-185145/phase-09` |
| `emf-parent` | `0b298c3216` | 15 files / +992 | `aidlc/CAP-185145/phase-09` |
| `intouch-api-v3-2/intouch-api-v3` | `13d62c487` | 13 files / +1119 | `aidlc/CAP-185145/phase-09` |
| `cc-stack-crm` | `699bbef63` | 2 files / +40 | `aidlc/CAP-185145/phase-09` |

### Downstream Phase Obligations

- **Phase 10 Developer GREEN**: implement all 6 `BenefitCategoryFacade` methods; implement `BenefitCategoryEditor` bodies in emf-parent; replace all `UnsupportedOperationException` stubs; add Testcontainers ITs for deferred 67 BTs; confirm Thrift codegen produces handler stubs; confirm D-45 revised format with UI team; consider `tillId` accessor upgrade on controller.
- All 28 structural/compliance tests in intouch-api-v3 MUST remain GREEN after Phase 10.
- Phase 11 Reviewer: verify `tillId`/`serverReqId` consistency across all 4 repos; flag D-45 revision for product/UX sign-off.

**Phase 9 Confidence**: C6 overall (intouch-api-v3 RED confirmed C7; emf-parent + thrift-ifaces + cc-stack DDL verified structurally at C6 — local compile/codegen deferred to CI per TD-SDET-05).
