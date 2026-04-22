# Session Memory — Loyalty Extended Fields CRUD
> Feature: Loyalty Extended Fields CRUD
> Ticket: loyaltyExtendedFields (Jira: CAP-183124)
> Started: 2026-04-22
> Pipeline: feature-pipeline v1.0

---

## Domain Terminology

| Term | Definition |
|------|-----------|
| Extended Fields (EF) | Custom dynamic attributes that orgs define and store against Partner Program entities at different scopes |
| EF Config | Metadata/configuration for each extended field — stored in MySQL (`loyalty_extended_fields` table, `warehouse` DB) |
| EF Values | Actual field values per entity — stored in MongoDB (DEFERRED) |
| Scope | The entity level at which an EF is defined: ORG / PARTNER_PROGRAM / MEMBER / … |
| Data Type | The value type of the field: STRING / NUMBER / BOOLEAN / DATE |
| Soft-delete | Marking an EF as INACTIVE (status field) rather than physically removing the row |

---

## Codebase Behaviour

- [C7] `extended_fields` table in cc-stack-crm (meta DB) is owned by CDP team — stores platform-managed EF definitions for customer/transaction/lineitem entity types. Loyalty team does NOT own this. _(BA)_
- [C7] `loyalty_extended_fields` table does NOT yet exist in cc-stack-crm warehouse schema. Must be created at: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/`. _(BA)_
- [C7] `SubscriptionProgram.ExtendedField` inner class already exists in intouch-api-v3 (`{type: ExtendedFieldType, key: String, value: String}`) — stored in MongoDB `subscription_programs` collection. Model implemented but NO CRUD APIs or core business logic yet. _(BA)_
- [C7] `ExtendedFieldType` enum: CUSTOMER_EXTENDED_FIELD, TXN_EXTENDED_FIELD — currently used as discriminator for evaluation-time resolution mapping to CDP EFs. _(BA)_
- [C7] Tests BT-EF-01 through BT-EF-06 for SubscriptionProgram.extendedFields already written in intouch-api-v3. _(BA)_
- [C7] cc-stack-crm warehouse schema convention: CREATE TABLE files per table, `id` AUTO_INCREMENT PK, `org_id` for tenancy, `is_active` tinyint for soft-delete, `created_on` + `auto_update_time` for audit. Pattern from `custom_fields.sql`. _(BA)_
- [C6] intouch-api-v3 subscription module already handles EF persistence in SubscriptionFacade (create, update, fork, duplicate). _(BA)_
- [C7] Cross-repo trace complete: 4 repos mapped, 3 write paths + 2 read paths traced. Per-repo change inventory complete. _(Cross-Repo Tracer)_
- [C7] emf-parent module: pointsengine-emf confirmed as correct module for new LoyaltyExtendedField entity + service + DAO. JPA pattern: @EmbeddedId composite PK (id, org_id), @DataSourceSpecification(WAREHOUSE), @Transactional("warehouse"). _(Cross-Repo Tracer)_
- [C7] thrift-ifaces-emf: EMFService currently has 57 methods. New methods will be 58 (create), 59 (update), 60 (get list). _(Cross-Repo Tracer)_
- [C7] cc-stack-crm: No existing loyalty_*.sql files. New file: schema/dbmaster/warehouse/loyalty_extended_fields.sql. _(Cross-Repo Tracer)_
- [C7] `SubscriptionProgram.ExtendedField` inner class (intouch-api-v3:285-312): `{type: ExtendedFieldType, key: String, value: String}` — NO `@Field` annotation on any field. `@Field("key")` must be added to new `id: Long` field to preserve MongoDB document key name. _(Architect OQ-1)_
- [C7] `program_config_keys.sql` (cc-stack-crm seed_data/dbmaster/warehouse/): 47 existing rows, `REPLACE INTO` pattern, next ID=48 for `MAX_EF_COUNT_PER_PROGRAM`. Path: `seed_data/dbmaster/warehouse/program_config_keys.sql`. _(Architect OQ-2)_
- [C7] `custom_fields.sql` (cc-stack-crm): `created_on datetime NOT NULL`, `auto_update_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`. Pattern confirmed across partner_programs.sql and supplementary_membership_cycle_details.sql. `loyalty_extended_fields` intentionally deviates to TIMESTAMP for G-01.1. _(Architect OQ-3)_
- [C7] `OrgEntityLongPKBase`: exists in `com.capillary.commons.data`. `PointsRedemptionSummaryPK` constructor is `(final long id, final int orgId)` — `orgId` is `int` not `Long`. Cannot be used for `LoyaltyExtendedFieldPK` which needs `Long orgId`. _(Architect OQ-4)_
- [C7] `EmfPromotionThriftService` (intouch-api-v3): uses `RPCService.rpcClient(EMFService.Iface.class, "emf-thrift-service", 9199, 10000)` — this is the correct pattern for new `EmfExtendedFieldsThriftService`. _(Architect OQ-5)_
- [C7] `PointsEngineRulesThriftService` (intouch-api-v3): uses `PointsEngineRuleService.Iface.class` from `pointsengine_rules.thrift` (different IDL, different service). NOT a valid reference for EMF EF Thrift client. _(Architect OQ-5)_
- [C7] `SubscriptionErrorAdvice` (intouch-api-v3): `@ControllerAdvice(assignableTypes = {SubscriptionController.class, SubscriptionReviewController.class})`. Handlers: `SubscriptionNotFoundException→404`, `InvalidSubscriptionStateException→422`, `SubscriptionNameConflictException→409`, `EMFThriftException→500`. _(Architect OQ-6)_
- [C7] `ExceptionCodes.java` (emf-parent): highest existing code is 7007 (`EXTEND_TIER_EXPIRY_DATE_NOT_PERMITTED`). New EF-specific exception codes go in 8xxx range (8001-8010). _(Architect OQ-10)_
- [C6] `SubscriptionFacade` (intouch-api-v3) lines 343 and 385: extendedFields copied as-is during fork/duplicate without re-validation. EF ids are stable PKs; stale deactivated ids caught at next explicit subscription create/update event. Fail-open on fork/duplicate is acceptable. _(Architect OQ-9)_
- [C6] Existing emf.thrift `get*` methods use plain positional parameters (no `required` qualifier on fields). New EF Thrift methods intentionally use `required` on `orgId` fields to prevent zero-default multi-tenancy bypass. _(Architect OQ-7)_

---

## Key Decisions

| # | Decision | Rationale | Phase | Confidence |
|---|----------|-----------|-------|-----------|
| D-01 | MySQL for EF Config metadata (`loyalty_extended_fields` table, `warehouse` DB, path: `cc-stack-crm/schema/dbmaster/warehouse/`) | Strong consistency, easy joins with relational data | BRD | C7 |
| D-02 | MongoDB for EF Values — **DEFERRED** | Volume-based justification not yet met | BRD | C7 |
| D-03 | Single MongoDB collection strategy — **DEFERRED** | CDP-style per-scope collections deferred until volume justifies | BRD | C7 |
| D-04 | Audit Log integration — **DEFERRED** | No confirmed consumer use case; defer to next quarter | BRD | C7 |
| D-05 | EN enrichment with EF — **DESCOPED** | Removed from current release | BRD | C7 |
| D-06 | Schema in cc-stack-crm via CREATE TABLE (no Flyway/ALTER) | Project convention: PR merge deploys schema | Project convention | C7 |
| D-07 | Uniqueness constraint: (org_id, scope, name) enforced at DB + service layer | Prevent duplicate field definitions per org/scope | BRD | C6 |
| D-08 | `loyalty_extended_fields` is the PARENT registry; `SubscriptionProgram.ExtendedField` (MongoDB) stores child instances/values | User clarification — the EF config table governs what fields are allowed | User Q1 answer | C7 |
| D-09 | Scopes for `loyalty_extended_fields`: SUBSCRIPTION_META (program create/edit), SUBSCRIPTION_LINK (customer enrolled/linked), SUBSCRIPTION_DELINK (customer delinked/expired/lapsed). Extensible — PROMOTION/BENEFIT/BADGE etc. future, not this sprint. | User clarification | User Q3 answer | C7 |
| D-10 | Loyalty team needs its own EF table (`loyalty_extended_fields`) — does NOT use CDP's `extended_fields` table | CDP owns the meta DB table; loyalty team owns warehouse scope | User Q1 answer | C7 |
| D-11 | `ExtendedFieldType` enum (CUSTOMER_EXTENDED_FIELD, TXN_EXTENDED_FIELD) is WRONG — field is actually a `scope`, not a type. Must be removed and replaced with correct scope values: SUBSCRIPTION_META, SUBSCRIPTION_LINK, SUBSCRIPTION_DELINK | User clarification — incorrect naming from prior implementation | User Q2 answer | C7 |
| D-12 | `SubscriptionProgram.ExtendedField.type` field must be renamed to `scope` (or the enum renamed to reflect scope semantics) | Terminology alignment with `loyalty_extended_fields.scope` column | User Q2 answer | C7 |
| D-13 | Tests BT-EF-01 to BT-EF-06 reference CUSTOMER_EXTENDED_FIELD/TXN_EXTENDED_FIELD — these must be updated to use SUBSCRIPTION_META/SUBSCRIPTION_LINK/SUBSCRIPTION_DELINK | D-11 makes existing EF tests wrong | Derived from D-11 | C7 |
| D-14 | `loyalty_extended_fields` schema: use `is_active TINYINT(1) NOT NULL DEFAULT 1` instead of `status VARCHAR(20)` | Aligns with cc-stack-crm convention (custom_fields.sql pattern); BRD preference overridden by convention | GQ-01 answer | C7 |
| D-15 | Org-level max EF count stored in `program_config_key_values` table with default value = 10 | Reuses existing config infra; no separate table needed | GQ-02 answer | C7 |
| D-16 | DELETE idempotency: ACTIVE→INACTIVE returns 200/204; already-INACTIVE returns 200/204; never-existed returns 404 | Idempotent soft-delete is safer for retries; 404 only on genuine not-found | GQ-03 answer | C7 |
| D-17 | Validation caching (per org_id, scope) deferred — integrate based on actual usage data | Premature optimization; measure first | GQ-04 answer | C7 |
| D-18 | Deactivating an EF config does NOT affect existing subscription program values — only new events validate against active fields | Backward safety for existing data; consistent with soft-delete semantics | GQ-05 answer | C7 |
| D-19 | `data_type` can be `ENUM` in addition to STRING/NUMBER/BOOLEAN/DATE. When `data_type=ENUM`, allowed values must be provided at create time and stored; CRUD APIs handle allowed-values list. Validation checks submitted value is in allowed list. | User-defined enum flexibility | GQ-05 answer | C6 |
| D-20 | GET /v3/extendedfields/config must support `includeInactive` boolean query param (default false) in addition to `scope` and pagination | Makes deactivated fields discoverable for admin/audit without cluttering default list | GQ-05 answer | C7 |
| D-21 | ~~ENUM allowed values storage~~ — moot: ENUM removed from scope (D-22) | Superseded | OQ-06 | C7 |
| D-22 | ENUM data type is **out of scope**. Allowed data_type values: STRING / NUMBER / BOOLEAN / DATE only | Simpler for first release; ENUM complexity deferred | OQ-06 answer | C7 |
| D-23 | PUT `/v3/extendedfields/config/{id}` allows editing only: `name` (String) and `is_active` (boolean). All other fields (`scope`, `data_type`, `is_mandatory`, `default_value`) are **immutable after creation**. | Reversal of prior mutable fields: is_mandatory and default_value are now immutable | User clarification | C7 |
| D-24 | No separate DELETE endpoint. Soft-delete (is_active=false) achieved via PUT. EF-US-03 merged into EF-US-02. API surface: POST + PUT + GET only. | Simpler API — fewer endpoints, same capability | User clarification | C7 |
| D-25 | `name` is mutable via PUT. Since D-28 uses `efId` (FK) for validation — not name — renaming the EF config does not orphan MongoDB documents. Name is display-only. | efId stored in MongoDB, not name | C-28 answer | C7 |
| D-26 | Thrift struct fields stay `required` for non-nullable response fields. `orgId` removed from CREATE/UPDATE request structs (populated from auth context). Timestamps → `TIMESTAMP` type in MySQL. Add `updated_by VARCHAR(100)` column (user's refId). | required fields are correct for fields that will always be present | C-1 answer | C7 |
| D-27 | `SubscriptionProgram.ExtendedField.type` field is **deleted entirely** (not renamed). Scope is always `SUBSCRIPTION_META` for subscription programs — backend validates server-side. | scope implicit, always SUBSCRIPTION_META; EF-US-07 simplified | C-2/3 answer | C7 |
| D-28 | ~~`key` replaced by `id`~~ — **CORRECTED (2026-04-22 user input)**: `key: String` is **KEPT** (stores the field name e.g. "gender"). `efId: Long` is **ADDED** as FK to `loyalty_extended_fields.id`. Final model: `{efId: Long, key: String, value: String}`. Validation by `efId`. No `@Field` annotation needed — no rename. Old documents (`{type, key, value}`) deserialize with `efId=null`, key/value preserved. | key has semantic value (display + lookup trace); efId is the authoritative FK | User correction 2026-04-22 | C7 |
| D-29 | `loyalty_extended_fields` is **program-scoped**. Add `program_id BIGINT NOT NULL` column. Uniqueness key: `(org_id, program_id, scope, name)`. All CRUD APIs require `program_id`. Max EF count stored in `program_config_key_values` per `(org_id, program_id)`. | EF configs belong to a program, not just an org | C-6 answer | C7 |
| D-30 | Name uniqueness enforced regardless of `is_active`. DB unique key blocks name reuse even after deactivation. API contract 409: "already exists" (no `is_active` qualifier). Names are permanently unique per `(org_id, program_id, scope)`. | simpler, prevents confusion about reuse | C-7 answer | C7 |
| D-31 | Spring `@ControllerAdvice` (ErrorAdvice) added for this feature to map `EMFException` error codes → HTTP status codes (400/404/409/500). | standard Spring error handling pattern | CCC-4 answer | C7 |
| A-01 | Thrift struct fields strategy: `required` on non-nullable response fields; `required` on `orgId` in new methods to prevent zero-default multi-tenancy bypass (G-07). `optional` only on truly nullable fields. Deviation from blanket-optional practice documented as ADR-01. | Evidence: OQ-7 — existing get methods use plain positional params, no `required`; ADR-01 establishes intentional deviation for security | Architect | C6 |
| A-02 | Standalone `@Embeddable LoyaltyExtendedFieldPK` with `Long id` + `Long orgId` — does NOT extend `OrgEntityLongPKBase` because that base class uses `int orgId` in its constructor (confirmed `PointsRedemptionSummaryPK(long id, int orgId)` at PointsRedemptionSummary.java). | Evidence: OQ-4 — `OrgEntityLongPKBase` exists but int/Long mismatch. Standalone avoids cast unsafety. | Architect | C7 |
| A-03 | ~~`@Field("key")` annotation~~ — **CORRECTED (2026-04-22 user input)**: No `@Field` annotation needed. `key: String` stays as-is. `efId: Long` is a NEW field added to `SubscriptionProgram.ExtendedField`. Old documents deserialize with `efId=null` gracefully (no EF validation applied to old docs). ADR-03 is superseded. | key stays; efId is purely additive; no rename concern | User correction 2026-04-22 | C7 |
| A-04 | New `EmfExtendedFieldsThriftService` in intouch-api-v3 extends `EmfPromotionThriftService` pattern: `RPCService.rpcClient(EMFService.Iface.class, "emf-thrift-service", 9199, 10000)`. Does NOT follow `PointsEngineRulesThriftService` (which uses wrong `PointsEngineRuleService.Iface` from different IDL). | Evidence: OQ-5 — EmfPromotionThriftService.java confirmed `EMFService.Iface.class` pattern; PointsEngineRulesThriftService.java uses different Thrift IDL | Architect | C7 |
| A-05 | EF Validation uses eager fail-fast strategy: one Thrift call fetches all active EF configs for `(org_id, program_id, SUBSCRIPTION_META)`, then in-memory checks R-01 (mandatory fields present), R-02 (submitted ids are active configs), R-03 (data type coercion). Validates all fields before returning first error; stops after first type violation per field. | Evidence: OQ-8 — no getById needed; D-17 — caching deferred; max 10 EF configs per program makes one-call approach efficient | Architect | C5 |
| A-06 | Two-pronged ErrorAdvice: new `LoyaltyExtendedFieldErrorAdvice` (scoped to `LoyaltyExtendedFieldController`) handles EF Config endpoint errors; `ExtendedFieldValidationException` handler added to existing `SubscriptionErrorAdvice` (already scoped to SubscriptionController + SubscriptionReviewController). | Evidence: OQ-6 — SubscriptionErrorAdvice scoped annotation confirmed; D-31 (architect phase); following existing scoped @ControllerAdvice pattern | Architect | C6 |
| A-07 | `loyalty_extended_fields` audit columns use `TIMESTAMP` (not `DATETIME`): `created_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`, `updated_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`, plus `updated_by VARCHAR(100)`. Deviation from `custom_fields.sql` `datetime` convention; justified by G-01.1 (UTC compliance, D-26). | Evidence: OQ-3 — custom_fields.sql confirmed `datetime`; D-26 mandates TIMESTAMP for UTC | Architect | C6 |
| A-08 | No `getLoyaltyExtendedFieldById` Thrift method needed. The list call `getLoyaltyExtendedFieldConfigs(orgId, programId, scope)` returns max 10 results; EF validation resolves by id in-memory from that list. Adding a getById would add network round-trip overhead without benefit at current scale. | Evidence: OQ-8 — D-15 max 10 EF configs per program; A-05 one-call strategy makes getById redundant | Architect | C5 |

---

## Constraints

- **In-scope for current release**: MySQL schema (cc-stack-crm), EF Config CRUD APIs (V3 + EMF), EF Validation Framework, Org-level config. **Scope limited to SUBSCRIPTION_META only.**
- **Out of scope / Deferred**: SUBSCRIPTION_LINK, SUBSCRIPTION_DELINK (new MongoDB collection at customer level, separate future task), MongoDB generic `extended_field_values` collection, Audit Log, EN enrichment, History inline GET, sharding.
- **`scope` column type**: VARCHAR (not ENUM) — future scope values will grow too large for DB ENUM. Application-level validation enforces allowed values.
- **Schema convention**: cc-stack-crm uses direct CREATE TABLE edits — no ALTER TABLE or Flyway. PR merge deploys schema. Path: `schema/dbmaster/warehouse/`.
- **jdtls**: Running for emf-parent and intouch-api-v3; NOT running for cc-stack-crm (schema-only repo).
- **Table name**: `loyalty_extended_fields` in `warehouse` database.
- **`SubscriptionProgram.ExtendedField.type`**: Must be renamed to `scope` (String). Old `ExtendedFieldType` enum (CUSTOMER_EXTENDED_FIELD/TXN_EXTENDED_FIELD) is incorrect — must be removed. Tests BT-EF-01 to BT-EF-06 must be updated accordingly.
- **Call chain**: V3 REST Controller → V3 Facade → EMF via Thrift (new Thrift methods in `EMFService`) → EMF business logic + DAO → warehouse DB (`loyalty_extended_fields`). Thrift IDL: `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf/emf.thrift`. _(BA)_
- **emf-parent warehouse DB**: Confirmed — emf-parent has `warehouse-database.properties` → warehouse DB access exists. V3 has NO warehouse access (connects to `target_loyalty` only). _(BA)_
- **Existing Thrift**: `EMFService` already has `partnerProgramLinkingEvent`, `partnerProgramUpdateEvent`, `partnerProgramDeLinkingEvent` methods + `ExtendedFieldsData` struct (for event data — different from config). New Thrift structs + CRUD methods needed. _(BA)_
- **New Thrift methods needed** (preliminary): createLoyaltyExtendedFieldConfig, updateLoyaltyExtendedFieldConfig, deleteLoyaltyExtendedFieldConfig, getLoyaltyExtendedFieldConfigs — to be finalised in Architect phase. _(BA)_

---

## Open Questions

- [x] `status` column → resolved: use `is_active TINYINT(1) DEFAULT 1` per cc-stack-crm convention (D-14) _(GQ-01)_
- [x] Org-level max EF count → resolved: `program_config_key_values`, default=10 (D-15) _(GQ-02)_
- [x] DELETE idempotency → resolved: no DELETE endpoint; soft-delete via PUT is_active=false (D-16, D-24) _(GQ-03)_
- [x] Validation caching → resolved: deferred; integrate based on usage (D-17) _(GQ-04)_
- [x] Deactivation impact on existing values → resolved: existing values unaffected; new events validate against active only (D-18) _(GQ-05)_
- [x] ENUM allowed values storage → resolved: ENUM removed from scope entirely (D-22) _(OQ-06)_
- [ ] Error code/message format for validation failures — to be defined in Designer phase. _(BA)_
- [x] @Field annotation strategy for SubscriptionProgram.ExtendedField key→id rename in existing MongoDB documents → resolved: `@Field("key")` on new `id: Long` field; no MongoDB migration needed; old docs get `id=null` gracefully (A-03). _(Architect OQ-1)_
- [x] ProgramConfigKey seed data approach: how/where is MAX_EF_COUNT_PER_PROGRAM key seeded? → resolved: `seed_data/dbmaster/warehouse/program_config_keys.sql`, `REPLACE INTO`, ID=48, default value=10 (A-01, OQ-2). _(Architect OQ-2)_
- [x] Schema convention: custom_fields.sql uses DATETIME for created_on; D-26 says TIMESTAMP. Confirm for loyalty_extended_fields → resolved: `loyalty_extended_fields` uses TIMESTAMP intentionally per D-26/G-01.1 (A-07). _(Architect OQ-3)_
- [ ] BLOCKER (Architect): `required` orgId in Thrift methods — Thrift generated code treats `required` missing field as protocol exception, not business exception. Review Thrift `required` semantics against existing EMFService `required` usages before finalizing IDL. _(Architect ADR-01 residual risk)_
- [ ] INFO (Architect): Deployment order — EMF must deploy before V3 (new Thrift methods not yet available). Deployment runbook needed for Phase 12. _(Architect, M-07 inherited)_

---

## PRD Structure (Phase 1 output)

| Epic | Stories | Confidence | Complexity |
|------|---------|-----------|-----------|
| EF-EPIC-01: EF Config Registry CRUD | EF-US-01, EF-US-02, EF-US-03, EF-US-04 | C6 | Medium (US-01), Small (US-02/03/04) |
| EF-EPIC-02: EF Validation on Subscription Programs | EF-US-05, EF-US-06 | C5 | Medium |
| EF-EPIC-03: Model Correction | EF-US-07 | C7 | Small |

**Grooming questions for Phase 4 (Blocker Resolution)**:
- GQ-01: status column VARCHAR vs is_active tinyint (OQ-01)
- GQ-02: Org-level max EF count storage (OQ-02)
- GQ-03: DELETE idempotency: 200 or 409 on already-INACTIVE (OQ-04)
- GQ-04: Validation caching TTL per (org_id, scope) (NFR)
- GQ-05: When EF config deactivated, do existing subscription programs with that field value get affected? (OQ-05)

**New Thrift structs defined** (PRD): `LoyaltyExtendedFieldConfig`, `CreateLoyaltyExtendedFieldRequest`, `UpdateLoyaltyExtendedFieldRequest`, `LoyaltyExtendedFieldListResponse`
**New EMFService methods** (PRD): `createLoyaltyExtendedFieldConfig`, `updateLoyaltyExtendedFieldConfig`, `deleteLoyaltyExtendedFieldConfig`, `getLoyaltyExtendedFieldConfigs`
**thrift-ifaces-emf repo added**: `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf` (branch: aidlc/loyaltyExtendedFields)

---

## Risk Register

**CRITICAL risks — Architect must resolve in Phase 6:**
- [C-1] Thrift `required` fields in `LoyaltyExtendedFieldConfig` violate G-09.5; all struct fields should be `optional` _(Phase 2 Critic)_
- [C-2/C-3] MongoDB migration: `type`→`scope` rename leaves existing `subscription_programs` documents with `scope=null`. Fix: use `@Field("type")` annotation — no migration needed, Java field named `scope`, MongoDB key stays `type` _(Phase 2 Critic)_
- [C-4] Race condition: EF deactivated mid-subscription-create validation window; fail-open vs fail-closed not specified _(Phase 2 Critic)_
- [C-6] D-15 (`program_config_key_values`) is program-scoped (mandatory `program_id` FK), not org-scoped. Org-level EF count cannot be stored there without sentinel `program_id` convention + `ProgramConfigKey` seed data. C7 confidence rating on D-15 must be downgraded to C3. _(Phase 2 Analyst M-02, M-08)_
- [C-7] Uniqueness constraint `uq_org_scope_name (org_id, scope, name)` blocks ALL duplicates regardless of `is_active`. POST 409 condition says "already exists AND is_active=1" implying names are reusable after deactivation — DB prevents this. Schema and API contract are inconsistent. _(Phase 2 Critic)_
- [C-28] Name mutability (D-25) + uniqueness-as-lookup-key: renaming EF orphans all existing `subscription_programs` MongoDB docs referencing the old name. D-25 should be re-examined — recommend making `name` immutable and using a different display label field if editable naming is needed _(Phase 2 Critic)_

**HIGH risks — address in design phases:**
- [H-8] Backward compatibility break: any org that creates a mandatory EF causes ALL existing subscription-create callers without EF to receive 400. Needs migration/grace-period story _(Phase 2 Critic)_
- [H-11] `extendedFields: []` on PUT is a silent destructive clear — unintuitive distinction from `null`. Needs explicit product sign-off _(Phase 2 Critic)_
- [H-13] Story numbering inconsistency: BA uses EF-US-03=Deactivate (now removed), EF-US-04=List; PRD uses EF-US-02=Update+Deactivate, EF-US-03=List. **Fixed in BA during Phase 2.** _(Phase 2 Critic)_
- [H-12] R-03a (ENUM validation rule) was zombie remnant — **deleted from prd-machine during Phase 2** _(Phase 2 Critic)_
- [CCC-4] EMFException error codes not mapped to HTTP status codes — V3 will receive EMFException and produce 500 without an explicit mapping table _(Phase 2 Critic)_
- [M-01/M-04] `DATETIME` vs `TIMESTAMP` for audit columns; cc-stack-crm convention uses `auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` _(Phase 2 Analyst)_
- [M-07] Deployment order constraint: EMF must deploy before V3 calls new Thrift methods — not documented _(Phase 2 Analyst)_

**Codebase facts confirmed by Analyst (C7 evidence):**
- `SubscriptionProgram.ExtendedField` fields: `type: ExtendedFieldType`, `key: String`, `value: String` at lines 297-300 _(Phase 2 Analyst)_
- `ExtendedFieldType` enum: `CUSTOMER_EXTENDED_FIELD`, `TXN_EXTENDED_FIELD` — only 3 usages: SubscriptionProgram.java, ExtendedFieldType.java, SubscriptionExtendedFieldsTest.java _(Phase 2 Analyst)_
- BT-EF-05 description wrong: Javadoc says "NOT copied" but test asserts ARE copied — production code (SubscriptionFacade:385) copies EFs on duplicate _(Phase 2 Analyst)_
- `program_config_key_values` has mandatory `program_id` FK — org-level config needs sentinel or separate key _(Phase 2 Analyst)_
