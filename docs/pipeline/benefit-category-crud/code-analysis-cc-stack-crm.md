# Code Analysis — cc-stack-crm

> Repo: /Users/anujgupta/IdeaProjects/cc-stack-crm
> Generated: Phase 5, 2026-04-18
> LSP: jdtls running (no Java source files in this repo — LSP not applicable)

---

## Verdict (headline)

**Involved in Benefit Category CRUD: PARTIAL** — (C6, evidence below)

**Clarification on "PARTIAL"**: cc-stack-crm has NO code paths today that read, write, route, or dispatch on `benefit_categories` or `benefit_category_slab_mapping` (those tables do not yet exist anywhere). However, cc-stack-crm IS the authoritative infrastructure/schema repository for the `warehouse` MySQL schema that houses the Benefit Category feature's FK target (`program_slabs`). One new set of SQL schema files (`benefit_categories.sql`, `benefit_category_slab_mapping.sql`) **must** be added here as part of this feature. Additionally, three cross-cutting registries in this repo (`org_mirroring_meta`, `cdc_source_table_info`, `org_mirroring_meta` seed data) would need new rows if the new tables are to participate in the same data-pipeline/mirroring workflows as their sibling tables (`program_slabs`, `benefits`).

---

## Key Findings

1. cc-stack-crm is a **pure infrastructure/DevOps/schema repository** — it contains zero Java source code, zero pom.xml/build.gradle, zero application logic. It is a Facets Cloud configuration repo for the Capillary platform cluster. Its primary relevant artefact is the MySQL schema DDL living under `schema/dbmaster/warehouse/`.

2. The `warehouse` MySQL schema (managed by this repo) is the physical home of `program_slabs` (the "Tier" table), `benefits`, `customer_benefit_tracking`, and related loyalty tables. **The new `benefit_categories` and `benefit_category_slab_mapping` tables belong in this same schema** — their DDL files belong in `schema/dbmaster/warehouse/`.

3. **Zero existing references** to `benefit_categories`, `benefit_category_slab_mapping`, or `BenefitCategory` exist anywhere in the 4,997 files of this repo. This is expected: the feature has not shipped yet. The feature branch `aidlc/CAP-185145` is checked out but has no diff from main (no work committed yet).

4. `program_slabs` is already registered in THREE cross-cutting seed-data registries: `org_mirroring_meta` (org bootstrapping), `cdc_source_table_info` (Reon CDC pipeline), and the reon_export `base_name` / `templates` tables. Whether the new tables should join these registries is a product decision — but the precedent pattern is unambiguous.

5. cc-stack-crm has **no application code** — it cannot "call" EMF Thrift or intouch-api-v3 REST. The question of Thrift client calls, REST client calls, JPA entities, Kafka consumers, and UI/presentation layer simply does not apply.

---

## 1. Repo Purpose

cc-stack-crm is a **Facets Cloud stack configuration repository** for the Capillary CRM platform cluster. It is not a Java microservice, not a CRM application, and not a UI backend. It contains:
- Infrastructure definitions for 318+ services deployed to Kubernetes (`service/instances/`)
- Aurora MySQL instance configurations (`aurora/instances/`) linking to schema directories
- MySQL DDL files for the `dbmaster` Aurora cluster under `schema/dbmaster/` — covering schemas: `warehouse`, `masters`, `user_management`, `luci`, `emf`, `target_loyalty`, `campaigns`, etc.
- Seed data SQL (`seed_data/`) for bootstrapping new org environments
- Kafka topics, Redis, Mongo, S3, Elasticsearch, Kinesis, and other cloud resource manifests
- A Python validation script (`validator/validate.py`) that validates Facets Cloud JSON configs against JSON schema

The `dbmaster` Aurora cluster hosts the `warehouse` schema — the physical MySQL home of all core loyalty tables including `program_slabs` (composite PK `(id, org_id)`), `benefits`, `customer_benefit_tracking`, `promotions`, and ~117 other tables.

**Relationship to EMF**: EMF (the Java application) reads/writes the `warehouse` schema at runtime. cc-stack-crm is purely the DDL/schema/infrastructure source-of-truth for that same database. They share a database but are separate concerns. cc-stack-crm does not contain any runtime application logic.

---

## 2. Benefits/Tier/Slab References Found

### Existing tables/entities (confirmed by direct file read):

| File | Type | Relevance |
|------|------|-----------|
| `schema/dbmaster/warehouse/program_slabs.sql` | Schema DDL | The "Tier" table — FK target for `benefit_category_slab_mapping.slab_id`. Composite PK `(id, org_id)`, `int(11)`. Confirmed consistent with Phase 2 analysis. |
| `schema/dbmaster/warehouse/benefits.sql` | Schema DDL | Legacy `benefits` table. `benefit_type ENUM('POINTS','VOUCHER')`, NOT NULL `promotion_id`. Confirms D-12 (no change needed). |
| `schema/dbmaster/warehouse/customer_benefit_tracking.sql` | Schema DDL | Runtime tracking of legacy benefit cycles per customer. References `benefit_id INT`. Irrelevant to new feature. |
| `schema/dbmaster/warehouse/customer_benefit_tracking_log.sql` | Schema DDL | Audit log for benefit tracking. Irrelevant. |
| `schema/dbmaster/warehouse/benefits_awarded_stats.sql` | Schema DDL | Stats table with `benefit_type ENUM(...)` — types: REWARDS, COUPONS, BADGES, TIER_UPGRADE, TIER_DOWNGRADE, TIER_RENEWAL, etc. Does NOT include `BENEFIT_CATEGORY`. **No change needed** — this is a different axis (stats/event tracking, not category config). |
| `schema/dbmaster/warehouse/partner_program_slabs.sql` | Schema DDL | Partner program slabs. Irrelevant. |
| `schema/dbmaster/warehouse/partner_program_tier_sync_configuration.sql` | Schema DDL | Tier sync config. Pattern-match confirmation: follows composite PK `(id, org_id)` — same as all other tables. |
| `schema/dbmaster/warehouse/promotions_benefits_stats_summary.sql` | Schema DDL | `context_type ENUM('BENEFIT','PROMOTION')` — refers to legacy benefit stats. Irrelevant to new feature. |
| `schema/dbmaster/masters/seasonal_slabs.sql` | Schema DDL | Seasonal slabs (non-loyalty slab concept). Irrelevant. |
| `schema/dbmaster/user_management/slab_upgrade_log.sql` | Schema DDL | Slab upgrade log. Irrelevant. |

### BenefitCategory / benefit_category_slab_mapping: ZERO hits
- grep across all 2,479 SQL files: **0 matches** for `benefit_categor`, `BenefitCategory`, `benefit_category_slab`
- grep across all 4,997 non-git files: **0 matches**

This is C7 evidence (direct grep across exhaustively enumerated file set with zero exceptions).

---

## 3. Thrift/REST Client Calls to Loyalty Services

**Not applicable.** cc-stack-crm contains zero Java source files (confirmed: `find ... -name "*.java"` returned empty). It has no pom.xml, no build.gradle. It cannot import or call any Thrift client, EMF client, or REST client. The only code in the repo is `validator/validate.py` (a schema validation utility for Facets Cloud JSON configs).

The repo does contain a **Kubernetes Service definition** (`k8s_resource/instances/application/service/emf-thrift-service-external.json`) that defines an ExternalName service pointing to `emf-a.default.svc.cluster.local`. This is a K8s networking manifest, not an application-level call. It confirms that EMF's Thrift service is accessible cluster-wide but does not mean cc-stack-crm calls it.

---

## 4. Shared Database / JPA Entities

**cc-stack-crm manages the DDL for the same MySQL database that EMF reads/writes at runtime.** Specifically:
- Aurora instance `dbmaster` (config: `aurora/instances/dbmaster.json`) maps to `schema/dbmaster/` for DDL
- The `warehouse` schema under `dbmaster` is the physical home of `program_slabs`, `benefits`, and all loyalty tables
- The `dbmaster` Aurora cluster has k8s service names: `warehouse-db-mysql-master`, `intouch-db-mysql-master`, `luci-db-mysql-master`

This confirms that **the new `benefit_categories` and `benefit_category_slab_mapping` DDL files belong in `/schema/dbmaster/warehouse/`** in this repo, consistent with the existing pattern for all other loyalty tables.

cc-stack-crm has zero JPA entity files — it has no application runtime whatsoever.

---

## 5. Event Consumption

**Not applicable for runtime.** cc-stack-crm defines Kafka cluster configurations (`kafka/instances/`) and topic configs — it does not consume messages at runtime.

However, a notable data-pipeline finding: the `cdc_source_table_info.sql` seed data registers tables for Reon's CDC (Change Data Capture) pipeline. Current registrations include:

```
(161,'warehouse','program_slabs','id','MYSQL','2021-08-24 12:34:56'),
(188,'warehouse','benefits','id','MYSQL','2021-12-02 12:34:56'),
(189,'warehouse','customer_benefit_tracking','id','MYSQL','2021-12-02 12:34:56'),
(190,'warehouse','customer_benefit_tracking_log','id','MYSQL','2021-12-02 12:34:56'),
```

`benefit_categories` and `benefit_category_slab_mapping` are NOT currently registered (as expected — they don't exist yet). Whether they should be registered for CDC is a product/data decision. If the platform needs analytics/reporting on benefit category configuration changes via Reon, new rows would be added here.

---

## 6. Generic Dispatchers / Enums

No Java enums. The only relevant schema-level enums are in existing SQL DDL files:
- `benefits.benefit_type ENUM('POINTS','VOUCHER')` — legacy, no change needed
- `benefits_awarded_stats.benefit_type ENUM('REWARDS','COUPONS','BADGES','TIER_UPGRADE',...)` — stats tracking, not category config, no change needed

No `CategoryType` or `EntityType` enum columns exist in any schema that would need a new `BENEFIT_CATEGORY` value.

---

## 7. UI / Presentation Layer

cc-stack-crm is not a UI. It defines Kubernetes deployments for UI applications (there are entries like `aira-admin-dashboard-ui.json`, `intouch-api-a.json` in `service/instances/`) but does not contain their source code. Per D-20 (API-only MVP), no UI changes are in scope anyway.

---

## Change Inventory for this Feature

### NEW files anticipated:
- `/schema/dbmaster/warehouse/benefit_categories.sql` — DDL for new `benefit_categories` table (C6)
- `/schema/dbmaster/warehouse/benefit_category_slab_mapping.sql` — DDL for new junction table (C6)

### MODIFIED files anticipated:
- `/seed_data/bootorgdb/camunda/org_mirroring_meta.sql` — **CONDITIONAL (C4)**. Currently registers `program_slabs` (line 139) for org mirroring. If Capillary's org-provisioning workflow needs to mirror benefit category config to new orgs, new rows for `benefit_categories` and `benefit_category_slab_mapping` must be added here. Whether these tables need org-mirroring is product-dependent: `program_slabs` is mirrored because it's seeded at org creation; `benefits` is NOT currently in this file (confirmed: no `benefits` row in `org_mirroring_meta`). Since benefit categories are created by admins post-org-setup, they likely do NOT need org-mirroring. **Confidence: C4 — verify with platform/DevOps team.**
- `/seed_data/reon/reon_workflow_manager/cdc_source_table_info.sql` — **CONDITIONAL (C3)**. Registers tables for Reon CDC streaming. `program_slabs`, `benefits`, `customer_benefit_tracking` are all registered. If analytics/reporting on benefit categories is needed via Reon, new rows required. MVP is API-only (D-20); Reon analytics on benefit categories is likely deferred. **Confidence: C3 — out of scope for MVP.**

### Justification for "none" on modifications (for MVP):
The `org_mirroring_meta` and `cdc_source_table_info` registries are **data pipelines** for analytics and org-provisioning, not for the operational API serving the Client. The Client reads benefit categories via the `Client → intouch-api-v3 → EMF → MySQL` chain (D-18/D-19). None of the data pipeline registrations are needed for the API-only MVP to function correctly. They become relevant only when analytics dashboards or new-org provisioning workflows need to include benefit category data — which is post-MVP scope.

---

## QUESTIONS FOR USER (confidence < C5)

**Q-CRM-1** (C4 — needs verification): Does the Capillary org-provisioning/org-mirroring workflow (managed via `bootorgdb.camunda.org_mirroring_meta`) need to include `benefit_categories` and `benefit_category_slab_mapping` in the mirrored table set? Precedent: `program_slabs` IS mirrored (line 139 of seed), `benefits` is NOT. Benefit categories are admin-created post-org-setup, so mirroring is likely NOT needed — but the platform/DevOps team should confirm before Phase 9 (testing new org provisioning).

**Q-CRM-2** (C3 — post-MVP): Should `benefit_categories` and `benefit_category_slab_mapping` be registered in `cdc_source_table_info` for Reon CDC analytics? This is irrelevant for MVP (API-only, D-20) but will come up in the follow-up analytics/reporting story.

---

## ASSUMPTIONS MADE (C5+ that user should verify)

**A-CRM-1** (C6): The new SQL DDL files (`benefit_categories.sql`, `benefit_category_slab_mapping.sql`) should be placed in `schema/dbmaster/warehouse/` — same directory as `program_slabs.sql`, `benefits.sql`, and all other loyalty tables. Evidence: `aurora/instances/dbmaster.json` explicitly maps `schema_dir: "schema/dbmaster"` and all existing loyalty DDL follows this path.

**A-CRM-2** (C7): cc-stack-crm is a pure infrastructure/schema repository with zero application runtime code. No Thrift clients, no REST clients, no JPA entities, no event consumers, no Spring beans. Confirmed by: no `.java` files, no `pom.xml`, no `build.gradle`, validator only contains a Python JSON-schema validator. This is NOT a Java microservice — it is a Facets Cloud cluster config repository.

**A-CRM-3** (C6): The `benefit_categories` and `benefit_category_slab_mapping` DDL must follow the schema patterns already in `schema/dbmaster/warehouse/`: composite PK `(id, org_id)`, `int(11)` columns for ids, `datetime` for timestamps named `created_on`, `auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`. All 117 existing warehouse DDL files follow this pattern without exception.

**A-CRM-4** (C5): cc-stack-crm does NOT own Flyway migrations. EMF-parent likely owns its own migration runner (Flyway/Liquibase) and the DDL in cc-stack-crm may be a declarative schema registry (for bootstrapping / Facets-managed schema sync) rather than the migration source. The team should confirm whether EMF-parent's Flyway migrations are the authoritative change vehicle (likely yes, per Phase 4 D-18/D-19 architecture) and cc-stack-crm's DDL files are a **parallel documentation artifact** kept in sync. This affects release ordering: EMF Flyway migration runs first; cc-stack-crm DDL file update is a documentation/tooling sync.

**CROSS-REFERENCE WITH emf-parent ANALYSIS**: The emf-parent analysis found NO Flyway `V{n}__*.sql` numbered files in emf-parent itself. Schema DDLs live in `emf-parent/integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/`. This aligns with A-CRM-4: cc-stack-crm IS the authoritative schema source. Phase 6 Architect must clarify the migration execution mechanism — is it:
(a) Flyway in emf-parent pointing to cc-stack-crm SQL files?
(b) Facets Cloud platform tool that syncs cc-stack-crm schema to the Aurora cluster?
(c) Manual DBA application with cc-stack-crm as a record-of-truth?

---

## Files Referenced

- `/Users/anujgupta/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/program_slabs.sql` — FK target table DDL, composite PK `(id INT, org_id INT)` confirmed
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/benefits.sql` — Legacy benefits DDL, confirms `ENUM('POINTS','VOUCHER')`, no change needed
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/customer_benefit_tracking.sql` — Runtime tracking, `benefit_id INT FK`, no change needed
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/benefits_awarded_stats.sql` — Stats `benefit_type` enum, no `BENEFIT_CATEGORY` entry, no change needed
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/partner_program_tier_sync_configuration.sql` — Pattern-match for composite PK `(id, org_id)`
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/seed_data/bootorgdb/camunda/org_mirroring_meta.sql` — Org mirroring registry; `program_slabs` present at line 139, `benefits` absent; new tables status = C4 question
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/seed_data/reon/reon_workflow_manager/cdc_source_table_info.sql` — Reon CDC registry; `program_slabs` + `benefits` + `customer_benefit_tracking*` registered; new tables = post-MVP
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/aurora/instances/dbmaster.json` — Confirms `schema_dir: "schema/dbmaster"` → DDL placement for new files
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/schema/bootorgdb/camunda/org_mirroring_meta.sql` — DDL of the mirroring registry table itself
- `/Users/anujgupta/IdeaProjects/cc-stack-crm/features.json` — Confirms repo is a Facets stack config repo, not a Java application

---

**Summary**: cc-stack-crm is the schema/DDL home for the `warehouse` MySQL database. Two new DDL files must be created here (`benefit_categories.sql`, `benefit_category_slab_mapping.sql` in `schema/dbmaster/warehouse/`); no existing files require modification for the API-only MVP; the three data-pipeline registry files (`org_mirroring_meta`, `cdc_source_table_info`, reon_export templates) are post-MVP concerns that require product/data team input. The repo contains no application code, no Thrift calls, no JPA entities — it is purely a schema/infra definition repository.
