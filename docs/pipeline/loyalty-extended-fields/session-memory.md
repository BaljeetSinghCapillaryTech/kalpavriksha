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

- [ ] `status` column in `loyalty_extended_fields`: BRD says `VARCHAR(20) ACTIVE/INACTIVE` but cc-stack-crm convention uses `is_active tinyint(1)`. Architect to decide. _(BA)_
- [ ] Org-level config (max EF count per org): BRD mentions as Task 3, Sprint 1-3. Needs Architect to determine storage (separate table or a config key in existing `program_config_key_values`). _(BA)_
- [ ] Error code/message format for validation failures — to be defined in Designer phase. _(BA)_

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

*(Populated as phases identify risks)*
