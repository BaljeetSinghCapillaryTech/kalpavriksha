# Approach Log — tier-crud
> What was decided, why, and what the user provided

## User Inputs
| Input | Value | Why It Matters |
|-------|-------|---------------|
| Feature name | tier-crud | Scopes the pipeline — suggests tier CRUD operations focus |
| Ticket ID | test_branch_v3 | Git branch naming: raidlc/test_branch_v3 |
| Artifacts path | docs/pipeline/ | All generated documents stored here |
| BRD | Tiers_Benefits_PRD_v2_AiLed.docx.pdf (23 pages) | Source of truth for requirements — covers E1-E4 epics |
| Primary repo | emf-parent | Tier/slab entities, strategies, Thrift services |
| Secondary repo | intouch-api-v3 | REST API gateway, maker-checker workflows |
| UI screenshots | none | No UI extraction phase needed |
| Dashboard | yes | Live HTML dashboard updates after every phase |

## Decisions
_Format: Decision — Rationale — Phase_

### BA Q&A Decisions (Phase 1)

| # | Question | Options Presented | User's Decision | Rationale |
|---|----------|-------------------|-----------------|-----------|
| Q1 | Scope: all 4 epics or subset? | (a) All 4, (b) E1+E4, (c) E1 only, (d) other | **(b) E1+E4 backend only** | "just create Tier CRUD APIs and only backend implementation for now" — aiRa, comparison matrix, audit log, simulation all future |
| Q2 | Tier deletion/insertion constraints? | (a) Keep both, (b) relax insertion, (c) relax deletion, (d) both | **(c) Relax deletion — soft delete** | Add `active` flag (default 1) to program_slabs, set to 0 on delete. GET returns active only. |
| Q3 | Prior TierConfigController implementation? | (a) Existing branch, (b) stale artifacts, (c) investigate | **(b) Proceed fresh** | "controller layer should be in intouch-api-v3 just like UnifiedPromotion only the thrifts and later flows be there in emf-parent" |
| Q4 | CRUD operations in scope? | Listed 8 operations (5 CRUD + 3 deferred) | **Confirmed 5 CRUD ops** | APIs must return field-level errors — "as aiRa will use APIs in future so APIs should also have constraints like UI" |
| Q5 | Maker-checker in scope? + Tier status lifecycle? | (a) Simple, (b) with pause, (c) mirror promotion | **Maker-checker IN SCOPE + (a) Simple lifecycle** | "yes we have to include maker-checker... refer already present maker checker for UnifiedPromotion" |
| Q6 | "validate on return transaction" toggle? | (a) Include as-is, (b) exclude, (c) deprecate | **(a) Include as-is** | Backend logic exists, real business need, API completeness |

### Blocker Decisions (Phase 4)

| # | Blocker | Options | Decision | Rationale |
|---|---------|---------|----------|-----------|
| B-1 | EntityType/RequestManagementController coupling | (a) Separate endpoint, (b) generalize controller, (c) parallel method | **(a) Separate TierController endpoint** | "a is the safest option" — zero risk to promotions |
| B-2+B-3 | Soft-delete leakage + DRAFT in evaluation | (a) Filter queries, (b) manual DAO update, (c) separate table | **MongoDB-first architecture** | "use MongoDB implementation just like UnifiedPromotion to save TIER data along with config and Benefits data" — DRAFT in Mongo only, SQL on APPROVE only |
| B-4 | Evaluation logic unaffected claim | N/A | **Auto-resolved** | DRAFT tiers never enter program_slabs |
| H-1 | Threshold validation create vs update | N/A | **Neighbor-ordering validation** | "validation should exist for threshold" — thresholds in strategy tables, MongoDB holds config |
| H-2 | Tier creation ruleset orchestration | Direct EMF calls vs Thrift | **Thrift endpoints only** | "APPROVE should only call EMF Thrift endpoints not their internal methods" |
| H-3 | PartnerProgramTierSync references | N/A | **Add validation check** | "yes validation should be present" |
| GQ-1 | dailyDowngradeEnabled scope | Per-tier vs per-program | **Program-level** | "yes these are program level configs" |
| GQ-2 | Soft-deleted tier members | Leave in place vs force-migrate | **User must migrate first** | "end user will have to migrate all customers from that tier... add validations" |
| GQ-3 | Member count in GET | Include vs defer | **Include** | "member count should be present for Get tier info" |
| GQ-4 | PUT vs PATCH | Both vs PUT only | **PUT only** | "integrate PUT only like UnifiedPromotion" |

### Impact Analysis Decisions (Phase 6a)

| # | Question | Options Presented | User's Decision | Rationale |
|---|----------|-------------------|-----------------|-----------|
| R-1/R-2 | Strategy CSV/JSON stale after soft-delete — update or leave? | (a) Update strategy on delete, (b) Leave — evaluation uses active tiers only | **(b) No update needed** | "all upgrades, downgrades, renewals will happen after taking only active tiers in consideration" — DAO filters is_active=1, so stale strategy entries are harmless |
| R-3 | Cache purge on soft-delete? | Confirmed | **Yes — purge cache** | "cache should be purged in soft delete API" |
| R-5 | Thrift IDL repo location? | User provided path | **`/Users/baljeetsingh/IdeaProjects/thrifts`** | 4th repo confirmed. IDL file: `thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift` |
| R-6 | Rollback on APPROVE failure? | Confirmed | **Yes — rollback mechanism required** | "we have rollback setup for promotions as well" — follow same pattern |
| R-4 | `getProgramSlabById()` bypasses is_active filter | (a) Override findById, (b) New findActiveById | **(b) New `findActiveById()` method** | "create a new method with active check, check all the relevant places where it needs to be used for our epic" — don't touch generic DAO |
| R-7 | Serial number gaps after soft-delete | (a) Renumber, (b) Accept gaps | **(b) Accept gaps** | "soft delete later in future user might again make the tiers active" — reversible operation, serial numbers preserved for reactivation |
| R-8 | APPROVE idempotency — simple if-check or transactional? | (a) Simple if-check, (b) Transactional locking like promotions | **(b) Transactional-like flow** | "system should give an error like request already processing or already processed... check this in UnifiedPromotion how it works there" |
| PI-1 | KPI type immutability — enforce at API? | Confirmed | **Yes — enforce in TierFacade** | "definitely should be Immutable because currently mysql slab config stores in strategies table in property_values which has this consistency so same should be adhered in mongo end" |
| Q5 | MySQL version in production | N/A | **MySQL 8.x** | Online DDL natively supported |
| Q6 | customer_enrollment row count | N/A | **10–100 million** | CREATE INDEX: 10-60 min, schedule off-peak with monitoring |

### QA Resolution Decisions (Phase 8 → Before Phase 9)

| # | Question | Options | Decision | Rationale |
|---|---------|---------|----------|-----------|
| Q-QA-1 | GET /tiers/{id} for STOPPED tier — 404 or return? | (a) 404, (b) Return with status | **(b) Return with status=STOPPED** | "only truly deleted (is_active=0) returns 404" — STOPPED tiers remain visible in MongoDB |
| Q-QA-2 | Second PUT on ACTIVE with existing in-flight DRAFT? | (a) 409, (b) Edit existing DRAFT | **(b) Edit existing DRAFT** | "do not create a new Draft from ACTIVE doc, instead edit the existing DRAFT until that DRAFT published and become ACTIVE" |
| Q-QA-3 | POST idempotency — idempotency key header or edit lock? | (a) X-Idempotency-Key, (b) Edit lock | **(b) Edit lock like UnifiedPromotion** | "configure edit lock in code just like in UnifiedPromotion... same goes to create case" |
| Q-QA-4 | Rollback when Thrift OK but MongoDB fails? | (a) Compensating call, (b) Manual, (c) WAL | **(c) Write-ahead log pattern** | "we have to do that Write-ahead log pattern for two-phase commit" |
| Q-QA-5 | PUT on ACTIVE tier — copy-on-write or in-place? | (a) New DRAFT + parentObjectId, (b) In-place to PENDING | **(a) Copy-on-write with SNAPSHOT** | "Create a DRAFT then transition to PENDING_APPROVAL then to ACTIVE after making existing ACTIVE as SNAPSHOT by maintaining parentObjectId similar to the UnifiedPromotion flow itself" |
