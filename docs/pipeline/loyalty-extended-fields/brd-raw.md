# Loyalty Extended Fields Implementation

**Extended Fields Implementation**

High-Level Design Document

*Version 1.0 | April 2026 | Capillary Technologies – Partner Platform*

| | |
|:-:|:-:|
| **Authors** | Shubham Jaiswal |
| **Reviewers** | Vishnu Viswanath, Kiran Pratap |
| **PRD** | Subscription Programs 2.0 |
| **Epic Jira** | **Custom Fields at Subscription Program Meta Level** CAP-183124 |

---

# 1. Overview

Extended Fields (EF) is a platform capability that allows organisations to define and store custom dynamic attributes against Partner Program entities at different scopes (org, partner program, member, etc.). This replaces the earlier 'Custom Fields' terminology and is designed for extensibility without schema migrations.

Key goals of this feature:

- Allow org admins to configure dynamic fields per scope via a self-serve API.
- Store field values efficiently in MongoDB (single collection strategy to start).
- Expose CRUD APIs from intouch-api-v3 and business logic implementation at the emf-parent layers for UI integration.
- Apply a centralised validation framework across all APIs that consume extended fields.
- Provide reporting support via source onboarding and dimensional modelling. **-> Deferred**

---

# 2. Architecture Decisions

**1. MySQL for EF Config (Metadata)** — Extended_Field_Config table in MySQL stores field metadata (name, data type, scope, constraints). Chosen for strong consistency and easy joins with existing relational data.

**2. MongoDB for EF Values** — A single Extended_Field_Values collection in EMF Mongo stores all field values across all scopes. Document-per-entity model with a map of field_name → value. Flexible schema avoids relational migrations as new fields are added. **-> Deferred**

**3. Single Collection Strategy** — All scopes share one MongoDB collection (filtered by scope + entity identifiers). CDP-style per-scope collections are deferred until volume justifies the split. **-> Deferred**

**4. Sharding Deferred** — EMF Mongo does not currently support sharding. Sharding will be revisited when volume metrics indicate the need. **-> Deferred**

**5. Audit Log via Audit Log Framework** — Historical audit of EF value changes will use the existing Audit Log Framework. Active integration is deferred to next quarter — no confirmed consumer use case exists today. **-> Deferred**

**6. History in EMF DB Tables** — For APIs that must return history inline (e.g., GET partner program), recent history rows are stored in EMF relational tables to avoid high-latency calls to the Audit Log service. **-> Deferred**

**7. Org-Level Config** — Optional org-level configuration (e.g., max EF count per org) can be defined to enforce guardrails. Implemented as a lightweight config entry per org.

**[DEFERRED]** Multiple MongoDB collections per scope (CDP pattern) — deferred until high volume.
**[DEFERRED]** MongoDB sharding — deferred until high volume.
**[DEFERRED]** Audit Log active integration — defer to next quarter if no confirmed use case.

---

# 3. Data Model

## 3.1 MySQL — loyalty_extended_fields, Database: warehouse

Stores metadata/configuration for each extended field. One row per field per scope.

| Column | Type | Description |
|:-:|:-:|:-:|
| id | BIGINT PK AI | Primary key |
| org_id | BIGINT | Organisation identifier |
| name | VARCHAR(100) | Field name — unique within scope + org |
| scope | VARCHAR(50) | Scope: ORG / PARTNER_PROGRAM / MEMBER … |
| data_type | VARCHAR(30) | STRING / NUMBER / BOOLEAN / DATE |
| is_mandatory | BOOLEAN | Whether the field is required |
| default_value | VARCHAR(255) | Optional default value |
| status | VARCHAR(20) | ACTIVE / INACTIVE |
| created_on | DATETIME | Record creation timestamp |
| last_updated_on | DATETIME | Last modification timestamp |

**[NOTE]** Uniqueness constraint: (org_id, scope, name) — enforced at DB + service layer.

## 3.2 MongoDB — extended_field_values (Collection) -> Deferred

Single collection in EMF Mongo. Each document represents one entity's extended field values.

```json
{
  "_id"        : ObjectId("..."),
  "org_id"     : 1001,
  "scope"      : "PARTNER_PROGRAM",
  "entity_id"  : "PP_456",
  "fields"     : {
    "tier_label"   : "Gold",
    "min_spend"    : 500,
    "is_exclusive" : true
  },
  "created_on" : ISODate("2026-04-01T00:00:00Z"),
  "updated_on" : ISODate("2026-04-15T10:00:00Z")
}
```

**[NOTE]** Index: (org_id, scope, entity_id) — primary lookup index.
**[DEFERRED]** Per-scope collections and sharding to be evaluated at scale.

---

# 4. API Design Overview

| Endpoint | Method | Description | Layer |
|:-:|:-:|:-:|:-:|
| /v3/extendedfields/config | POST | Create an extended field definition | V3 + EMF |
| /v3/extendedfields/config/{id} | PUT | Update an extended field definition | V3 + EMF |
| /v3/extendedfields/config/{id} | DELETE | Soft-delete an extended field | V3 + EMF |
| /v3/extendedfields/config | GET | List extended fields (filterable by scope) | V3 + EMF |
| /v3/extendedfields/values/{entity_id} | POST | Set/update EF values for an entity | V3 + EMF |
| /v3/extendedfields/values/{entity_id} | GET | Get EF values for an entity | V3 + EMF |
| Partner Program POST/PUT APIs | POST/PUT | Accept extended_fields map in request body | V3 / Thrift |
| Partner Program GET APIs | GET | Return extended_fields map in response | V3 / Thrift |

Validation rules applied in all APIs that accept extended fields:
- Data type of the provided value must match the registered data_type for that field.
- The field must be configured (active) for the given scope — else return 400 ERROR.
- Mandatory fields must be present when creating/updating an entity.

**[DESCOPED]** Event Notification (EN) enrichment with Extended Fields — descoped from current release.

---

# 5. Task Breakdown & Effort Estimate

## 5.1 Sprint 1–3: Core Extended Fields (3 Sprints)

| # | Task | Component / Repo | Dev (d) | QA (d) | Total (d) |
|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | Extended_Field_Config MySQL table schema design | cc-stack-crm (MySQL) | 1 | — | 1 |
| 2 | extended_field_values MongoDB collection setup + indexes | EMF Mongo | 1 | — | 1 |
| 3 | Org-level config for EF (e.g., max fields per org) | EMF / V3 | 1 | — | 1 |
| 4 | Extended Fields CRUD APIs (V3 + EMF) — Config endpoints | V3 + EMF | 3 | — | 3 |
| 5 | DAO layer for EF Values — add/update in MongoDB | EMF | 2 | — | 2 |
| 6 | EF Validation Framework (data type, scope existence check) | V3 + EMF | 3 | — | 3 |

**[NOTE]** Task 7 (Audit Log): Defer to next quarter if no confirmed consumer use case is identified in grooming.

---

# 7. Deferred & Descoped Decisions

| Item | Decision | Reason |
|:-:|:-:|:-:|
| Multiple Mongo collections per scope | **DEFERRED** | Revisit when volume warrants the split |
| EMF Mongo sharding | **DEFERRED** | EMF Mongo does not yet support sharding; revisit at scale |
| Audit Log active integration | **DEFERRED** | No confirmed consumer use case; defer to next quarter |
| EN enrichment with Extended Fields | **DESCOPED** | Removed from current release scope |
| History data in EMF tables (inline GET) | **DEFERRED** | Approach to be finalised during LLD phase |
