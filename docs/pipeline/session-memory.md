# Session Memory

> Artifacts path: docs/pipeline/
> Workflow started: Phase 0 / 2026-04-06
> Feature: tier-crud
> Ticket: test_branch_v3

---

## Domain Terminology
_Populated by BA from product docs and requirements. Use these terms consistently across all phases._

- **Tier** = UI/BRD-facing term for what the codebase calls **Slab** (backend entity: `ProgramSlab`, table: `program_slabs`). New code should use "Tier" in the API surface but may map to "Slab" internally. _(ProductEx)_
- **Slab** = internal/legacy backend term for Tier. `SlabUpgradeService`, `SlabDowngradeService`, `RenewSlabInstruction` are the current implementations. _(ProductEx)_
- **Benefits** = existing entity (table: `benefits`) with `promotionId` coupling. In BRD context, "Benefits as a Product" implies a new or migrated entity model. Name collision risk — verify before implementation. _(ProductEx)_
- **BenefitsType** = current enum with only `VOUCHER` and `POINTS` values. BRD proposes multiple new types. _(ProductEx)_
- **TierConfiguration** = existing DTO used for downgrade/renewal config, serialized via Gson. Contains `isDowngradeOnReturnEnabled`, `dailyDowngradeEnabled`, `slabConfigs`, `retainPoints`. _(ProductEx)_
- **Maker-checker** = approval workflow currently implemented for Promotions in `intouch-api-v3` (`RequestManagementController`, `ApprovalStatus` enum). Not yet wired for tier/benefit entities. _(ProductEx)_

## Codebase Behaviour
_What was found in the codebase and docs, and how it behaves/is set up. Updated by each phase._

- Tier upgrade: implemented via `SlabUpgradeService` + `UpgradeSlabActionImpl`. _(ProductEx)_
- Tier downgrade: implemented via `SlabDowngradeService` + `DowngradeSlabActionImpl`. Multiple date-calculator strategies exist (Cyclic, Fixed, FixedCustomerRegistration, SlabUpgradeBased). _(ProductEx)_
- Tier renewal: implemented via `RenewSlabInstructionImpl`. _(ProductEx)_
- Audit logs: `/audit/logs` endpoint in `ProgramsApi`. `SlabUpgradeAuditLogService`, `SlabDowngradeAuditLogService` in place. _(ProductEx)_
- Approval/maker-checker: `PUT /v3/requests/{entityType}/{entityId}/status` in `RequestManagementController` (intouch-api-v3). Supports `EntityType` + `PromotionStatus` today. _(ProductEx)_
- `TierConfigController.class` and `BenefitConfigController.class` exist as compiled artifacts in `pointsengine-emf/target/` — NO source code found. This is a blocking risk: prior CRUD implementation may exist in an uncommitted branch. _(ProductEx)_
- `Benefits.java` entity has `promotionId` as non-nullable FK — benefits are promotion-coupled today. _(ProductEx)_
- `BenefitsType` enum: only VOUCHER and POINTS. New types require schema/enum changes. _(ProductEx)_
- `ProgramSlab` entity has no status column — the tier status lifecycle (Active/Draft/Pending/Stopped) is a new concept requiring schema work. _(ProductEx)_
- Partner program tier sync is an active feature: `PartnerProgramTierSyncConfiguration`, `RenewTierBasedOnPartnerProgramActionImpl`, `UpgradeTierBasedOnPartnerProgramActionImpl`. New tier UI must not break these. _(ProductEx)_
- Official Capillary docs (docs.capillarytech.com) returned 404 for all tier/benefit-specific pages attempted. Docs coverage for this feature area is not accessible. _(ProductEx)_

## Key Decisions
_Significant decisions and their rationale. Format: `- [decision]: [rationale] _(phase)_`_
- Scope is E1 (Tier Intelligence) + E4 (API-First Contract), backend only: user confirmed "tier-crud" means tier CRUD APIs only _(BA)_
- E2 (Benefits as Product), E3 (aiRa Config Layer) are OUT of scope: future epics _(BA)_
- aiRa integration is OUT of scope: future phase _(BA)_
- Comparison matrix UI is OUT of scope: backend APIs only, no frontend _(BA)_
- Audit/change log is OUT of scope: future scope _(BA)_
- Simulation mode is OUT of scope: future scope _(BA)_
- Maker-checker approval workflow is IN SCOPE: follow existing UnifiedPromotion maker-checker pattern in intouch-api-v3 _(BA)_
- Backend-only implementation: no Garuda/frontend work in this pipeline _(BA)_
- Tier deletion = soft delete: add `active` column (default 1) to `program_slabs`, set to 0 on delete. GET calls filter to active=1 only. _(BA)_
- Tier insertion between existing tiers: NOT relaxed — new tiers still added at top only (existing constraint kept). _(BA)_
- Stale TierConfigController.class in emf-parent/target: ignore, proceed fresh. Not prior work. _(BA)_
- Controller layer lives in intouch-api-v3 (same pattern as UnifiedPromotion): REST controllers, request/response DTOs, validation _(BA)_
- Thrift definitions + backend service logic lives in emf-parent: Thrift IDL, service implementations, DAO layer, entity persistence _(BA)_
- Architecture follows existing UnifiedPromotion pattern: intouch-api-v3 (REST) → Thrift → emf-parent (service/DAO) _(BA)_
- CRUD operations in scope: GET /tiers (list), GET /tiers/{id} (detail), POST /tiers (create), PUT/PATCH /tiers/{id} (update), DELETE /tiers/{id} (soft delete) _(BA)_
- APIs must return structured field-level validation errors (not generic 500s): future-proofing for aiRa consumption. Same validation in API as would be in UI. _(BA)_
- GET /tiers should return tier config only (no linked benefits info — benefits deferred to E2) _(BA)_
- Maker-checker IN SCOPE: tier create/update goes through approval workflow (same as UnifiedPromotion) _(BA)_
- Tier status lifecycle in MongoDB: DRAFT → PENDING_APPROVAL → ACTIVE → STOPPED. Rejected goes back to DRAFT. No PAUSED/LIVE/UPCOMING. _(BA)_
- Status column NOT needed in program_slabs SQL — only `active` column needed. Status lives in MongoDB only. SQL write only happens on APPROVE (= ACTIVE). Soft-delete sets active=0. _(Phase 4)_
- Simulation and changelog endpoints: deferred _(BA)_
- Maker-checker approver logic (who approves) is handled at UI/frontend level, NOT backend — same as UnifiedPromotion. Backend only handles status transitions (submit, approve, reject). No approver assignment or routing in API. _(BA)_
- BLOCKER B-1 resolved: Separate TierController endpoint for status changes (option a). Do NOT touch RequestManagementController. New `POST /v3/tiers/{tierId}/status` with own TierStatus enum. Zero risk to existing promotion flow. _(Phase 4)_
- BLOCKER B-2 + B-3 resolved: Use MongoDB (like UnifiedPromotion) to store tier documents. DRAFT/PENDING tiers live ONLY in MongoDB. On APPROVE, write to program_slabs (MySQL). Evaluation engine only reads program_slabs = only ACTIVE tiers. No existing query changes needed. _(Phase 4)_
- MongoDB tier document will hold full config + future benefits linkage (E2 extensible). Same pattern as UnifiedPromotion MongoDB storage. _(Phase 4)_
- Soft-delete (active flag) still needed in program_slabs for ACTIVE→STOPPED transition, but B-2 blast radius is massively reduced since only the CRUD API reads MongoDB, and evaluation reads MySQL. _(Phase 4)_
- BLOCKER B-4 auto-resolved: "evaluation logic unaffected" is now genuinely true — DRAFT tiers never enter program_slabs. _(Phase 4)_
- Threshold + tier config stored in strategy tables (strategy_types: SLAB_UPGRADE, SLAB_DOWNGRADE, etc.), NOT in program_slabs directly. MongoDB document holds full config including strategy data. On APPROVE, sync MongoDB doc → program_slabs + strategy tables. _(Phase 4)_
- Threshold validation on update: must check neighbor ordering (tier[n-1].threshold < new < tier[n+1].threshold). Validation runs against MongoDB docs. _(Phase 4)_
- On APPROVE: intouch-api-v3 calls EMF Thrift endpoints (NOT internal methods like BasicProgramCreator directly). Thrift endpoints handle ruleset/strategy creation + program_slabs write. Clean service boundary. _(Phase 4)_
- HIGH H-2 resolved: Tier creation orchestration handled by EMF via Thrift on APPROVE. CRUD API only writes MongoDB. _(Phase 4)_
- HIGH H-3 resolved: Soft-delete validation must also check PartnerProgramTierSyncConfiguration references. Return error with partner sync dependencies if any exist. _(Phase 4)_
- MongoDB tier document contains ALL slab info: name, description, color, metadata, serialNumber, threshold, strategy configs (upgrade/downgrade/renewal), TierConfiguration DTO fields, status. Complete representation. _(Phase 4)_
- Schema migration for `active` column: add to cc-stack-crm repo at `schema/dbmaster/warehouse/program_slabs.sql`. Third code repo for this pipeline. _(Phase 4)_
- No Flyway — schema managed via SQL DDL files in cc-stack-crm. ALTER TABLE script needed for existing deployments. _(Phase 4)_
- GQ-1 resolved: `dailyDowngradeEnabled`, `retainPoints` are program-level configs (TierConfiguration DTO). Stored in MongoDB doc as program-level fields, not per-tier. _(Phase 4)_
- GQ-2 resolved: Soft-delete requires user to migrate ALL members out of the tier FIRST. Validation: cannot soft-delete a tier that still has members. New validation query needed — must check indexes exist for performance. Simulation phase (future) will surface member count info to user. _(Phase 4)_
- GQ-3 resolved: Member count per tier included in GET /tiers response. Cross-service query needed — must check indexes for performance. _(Phase 4)_
- GQ-4 resolved: PUT only for updates, no PATCH. Same as UnifiedPromotion. _(Phase 4)_
- All new validation queries must use existing indexes. If new indexes needed, flag during implementation. _(Phase 4)_
- Soft-delete column should be `is_active` (not `active`) — matches convention in ~20 other tables in cc-stack-crm _(Phase 5)_
- `customer_enrollment` table is the member-tier mapping. Needs new index on `(org_id, program_id, current_slab_id, is_active)` for member count queries _(Phase 5)_
- MongoDB: must register TierRepository in `EmfMongoConfig.includeFilters` or it silently uses wrong database _(Phase 5)_
- Two MongoDB namespaces exist: primary (`mongoTemplate`) and EMF (`emfMongoTemplate`). Tier uses EMF namespace. _(Phase 5)_
- Thrift IDL (.thrift files) not in emf-parent repo — in dependency jar. Existing method `createOrUpdateSlab` confirmed. No `deactivateSlab` method exists — must be added. _(Phase 5)_
- SLAB_UPGRADE thresholds stored as CSV in strategies.property_values: `{"current_value_type":"CUMULATIVE_PURCHASES","threshold_values":"500,1000"}` _(Phase 5)_
- SLAB_DOWNGRADE config stored as full TierConfiguration JSON in strategies.property_values _(Phase 5)_
- `PeCustomerEnrollmentDao` has NO member-count-per-slab query — must be added _(Phase 5)_
- New member count query + customer_enrollment index needed for GET /tiers member count AND soft-delete validation (no members in tier) _(Phase 5)_
- 3 repos all require changes: intouch-api-v3 (~14 new + 2 modified), emf-parent (1-2 migrations + 4 modified), cc-stack-crm (2 DDL modifications) _(Phase 5)_
- HLD pattern: MongoDB-First with SQL Sync on Approval — mirrors UnifiedPromotion _(Phase 6)_
- 6 ADRs documented: ADR-01 MongoDB-first, ADR-02 separate TierController, ADR-03 TierStatus enum, ADR-04 Thrift boundary, ADR-05 is_active soft delete, ADR-06 member count cross-service _(Phase 6)_
- API endpoints: GET /v3/tiers, GET /v3/tiers/{id}, POST /v3/tiers, PUT /v3/tiers/{id}, DELETE /v3/tiers/{id}, POST /v3/tiers/{id}/status _(Phase 6)_
- MongoDB document: TierDocument with full tier config, strategy configs (upgrade/downgrade/renewal), status, version tracking _(Phase 6)_
- MySQL changes: ALTER TABLE program_slabs ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1; new index on customer_enrollment _(Phase 6)_
- 17-step implementation plan with build order and dependencies _(Phase 6)_
- Thrift: new deactivateSlab + getMemberCountBySlabIds methods needed _(Phase 6)_
- Migration strategy: no Flyway/Liquibase — raw SQL DDL files in cc-stack-crm; migrations applied manually per environment. DDL migrations must deploy BEFORE application code. _(Migrator)_
- MIG-01 (ADD COLUMN is_active to program_slabs): fully backward-compatible, DEFAULT 1, no expand-then-contract required, no backfill required. Existing rows all active by architecture guarantee (MongoDB-first). _(Migrator)_
- MIG-02 (CREATE INDEX idx_ce_slab_count on customer_enrollment): additive index, online DDL (MySQL 5.6+). Schedule during off-peak due to unknown table size. _(Migrator)_
- UNIQUE constraint on program_slabs (org_id, program_id, serial_number) — serial numbers of soft-deleted slabs remain reserved (no reuse). Architecture is already designed to add tiers at top only. Constraint stays intact. _(Migrator)_
- customer_enrollment already has is_active column (enrollment active flag, tinyint(1)). Proposed composite index uses existing columns — no structural table change needed. _(Migrator)_
- `PeProgramSlabDao` has exactly 3 JPQL queries that need `is_active=1` filter added: `findByProgram`, `findByProgramSlabNumber`, `findNumberOfSlabs` _(Analyst)_
- `InfoLookupService.getProgramSlabs()` delegates to `PeProgramSlabDao.findByProgram()` — transparent fix when DAO updated, but **cache eviction required on soft-delete** _(Analyst)_
- `cacheEvictHelper.evictProgramIdCache(orgId, programId)` called in `createOrUpdateSlab` (line 1686) — must also be called in `deactivateSlab` _(Analyst)_
- `getProgramSlabById()` uses generic `findById()` — no `is_active` filter. Soft-deleted slabs loadable by PK. Consider adding `findActiveById()` _(Analyst)_
- SLAB_UPGRADE `threshold_values` CSV has N-1 entries for N slabs, correlated by index. Soft-delete breaks mapping unless CSV is updated _(Analyst)_
- SLAB_DOWNGRADE `TierDowngradeStrategyConfiguration` JSON contains per-slab configs. Soft-delete leaves stale entries _(Analyst)_
- Thrift IDL for `PointsEngineRuleService` located at `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift` — 4th repo confirmed _(Phase 6a)_
- Thrift `SlabInfo` struct has: id, programId, serialNumber, name, description, colorCode, updatedViaNewUI — NO active/status field currently _(Phase 6a)_
- Existing slab Thrift methods: `getAllSlabs`, `createSlabAndUpdateStrategies`, `createOrUpdateSlab` — adding `deactivateSlab` + `getMemberCountPerSlab` is backward-compatible (new methods) _(Phase 6a)_
- R-1/R-2 RESOLVED: Evaluation engine (upgrades, downgrades, renewals) ONLY considers active tiers. DAO queries filtered by is_active=1, so strategy CSV/JSON with stale slab entries is harmless — evaluation skips soft-deleted slabs. No need to update strategy JSON on soft-delete. _(Phase 6a)_
- R-3 CONFIRMED: Cache MUST be purged in soft-delete API. `deactivateSlab` must call `cacheEvictHelper.evictProgramIdCache(orgId, programId)`. _(Phase 6a)_
- R-6 CONFIRMED: Rollback mechanism required for APPROVE flow (MongoDB→Thrift failure). Follow existing promotion rollback pattern. _(Phase 6a)_
- R-4 RESOLVED: Add new `findActiveById()` method in `PeProgramSlabDao` with `is_active=1` filter. Do NOT override generic `findById()`. Use `findActiveById()` in all tier-CRUD-relevant code paths (soft-delete validation, downgrade target check, partner sync check). _(Phase 6a)_
- R-7 RESOLVED: Accept serial number gaps on soft-delete. Soft-delete is reversible — user may reactivate tiers in future. No renumbering. UNIQUE constraint (org_id, program_id, serial_number) stays intact. _(Phase 6a)_
- R-8 RESOLVED: APPROVE flow must be transactional-like. If user retries after first request completes → return error "already processed". If retries during processing → return "request already processing". Check UnifiedPromotion approve flow for the concurrency/locking pattern used. _(Phase 6a)_
- PI-1 RESOLVED: KPI type (`currentValueType`) is IMMUTABLE per program. Enforce in `TierFacade.createTier()`: if other tiers exist for program, new tier's currentValueType must match. MySQL strategies table already enforces this consistency — MongoDB must match. _(Phase 6a)_
- MySQL version in production: 8.x — online DDL supported natively, no pt-online-schema-change needed _(Phase 6a)_
- customer_enrollment approximate size: 10–100 million rows. CREATE INDEX will take 10–60 minutes. Schedule off-peak with monitoring. MySQL 8 online DDL (ALGORITHM=INPLACE, LOCK=NONE) is safe. _(Phase 6a)_
- GET /tiers makes 2 calls (MongoDB + Thrift for member count) — acceptable for typical program sizes (<10 tiers) _(Analyst)_
- No `@Transactional` on `PointsEngineRuleConfigThriftImpl` slab methods — verify transaction management for `deactivateSlab` _(Analyst)_

## Constraints
_Technical, business, and regulatory constraints all phases must respect. Format: `- [constraint] _(phase)_`_
- LSP available: using jdtls for code traversal _(Phase 0)_
- Code repos: emf-parent (multi-module Maven), intouch-api-v3 (Spring MVC REST gateway) _(Phase 0)_
- No UI screenshots provided — no UI extraction phase needed _(Phase 0)_
- BRD covers 4 epics: E1 Tier Intelligence, E2 Benefits as Product, E3 aiRa Config Layer, E4 API-First Contract _(Phase 0)_
- Feature name is "tier-crud" — suggests focus on tier CRUD operations (E1 + E4 scope) _(Phase 0)_
- KPI type is immutable per program — set on first tier, all subsequent must match _(BA)_
- Eligibility threshold must be strictly increasing up the hierarchy _(BA)_
- Base tier cannot be soft-deleted _(BA)_
- Cannot soft-delete a tier that is another active tier's downgrade target _(BA)_
- UnifiedPromotion pattern: controller in intouch-api-v3, Thrift+service in emf-parent, ResponseWrapper for all responses, TargetGroupErrorAdvice for validation errors _(BA)_
- `deactivateSlab` must update SLAB_UPGRADE threshold CSV AND SLAB_DOWNGRADE JSON — cannot just set `is_active=0` in isolation _(Analyst)_
- APPROVE flow must be idempotent — retry after network timeout must not create duplicate MySQL slabs _(Analyst)_
- Thrift IDL changes require emf-parent deployed BEFORE intouch-api-v3 (deployment ordering constraint) _(Analyst)_
- New timestamp fields (createdOn, lastModifiedOn) in TierDocument/TierResponse must use `Instant`/`java.time`, not `java.util.Date` (G-01 compliance) _(Analyst)_

## Risks & Concerns
_Flagged risks and concerns. Format: `- [risk] _(phase)_ — Status: open/mitigated`_
- BRD has 6 open questions in Section 12 (all status: Open) — must be resolved during BA phase _(Phase 0)_ — Status: open
- `TierConfigController` and `BenefitConfigController` compiled class files found without source — user confirmed: stale artifacts, proceed fresh _(ProductEx)_ — Status: **mitigated**
- `Benefits.java` entity is promotion-coupled (non-null `promotionId`) — "Benefits as a Product" (E2) requires data model migration _(ProductEx)_ — Status: open (E2 deferred)
- Tier status lifecycle (Active/Draft/Pending/Stopped) not in current `ProgramSlab` schema — requires new columns (active + status). Flyway migration needed. _(ProductEx)_ — Status: open (in scope)
- Maker-checker not wired for tier entity type — `RequestManagementController` works for promotions only today. EntityType.TIER + routing needed. _(ProductEx)_ — Status: open (in scope)
- `BenefitsType` enum only has VOUCHER/POINTS — new types require backward-compatible schema change _(ProductEx)_ — Status: open (E2 deferred)
- `RequestManagementController` return type is `ResponseWrapper<UnifiedPromotion>` — cannot reuse for TIER without generalizing _(Analyst)_ — Status: open (blocks maker-checker design)
- Tier creation involves rulesets/strategies orchestration (`BasicProgramCreator`) — CRUD API may need to handle this _(Analyst)_ — Status: open (blocks architecture)
- `PartnerProgramTierSyncConfiguration` references must be checked on soft delete — BA missed this _(Analyst)_ — Status: open (blocks soft delete design)
- No Flyway migration mechanism found — migration approach unclear _(Analyst)_ — Status: open (blocks schema migration)
- `program_slabs` UNIQUE constraint on `(org_id, program_id, serial_number)` conflicts with soft delete — serial number gaps _(Analyst)_ — Status: open (blocks soft delete design)
- [MIG-R-01] CREATE INDEX on customer_enrollment may lock table on old MySQL version — MySQL version in production unknown _(Migrator)_ — Status: open
- [MIG-R-02] Incorrect deploy order (application before DDL) will cause is_active=1 filter to fail on missing column _(Migrator)_ — Status: open — Mitigation: DDL before app deploy, enforced in pipeline
- [MIG-R-03] Member count query will run as full table scan if application deploys before MIG-02 index is created _(Migrator)_ — Status: open — Mitigation: deploy DDL first; non-critical (query still correct, just slower)
- [MIG-R-04] UNIQUE constraint (org_id, program_id, serial_number) — serial numbers of deleted slabs remain reserved. Architecture already handles this (add at top only). _(Migrator)_ — Status: mitigated
- [MIG-R-05] No migration tool — manual application across environments creates drift risk _(Migrator)_ — Status: open (process risk, future Flyway adoption recommended)
- [MIG-R-06] Rollback of MIG-01 (DROP COLUMN) while new code still runs causes column not found errors — must roll back app first _(Migrator)_ — Status: open — Mitigation: strict rollback sequencing
- R-1 CRITICAL: Soft-delete breaks SLAB_UPGRADE threshold CSV / slab list index mapping — evaluation engine may upgrade customers to wrong tiers _(Analyst)_ — Status: open
- R-2 HIGH: Soft-delete leaves stale slab entries in SLAB_DOWNGRADE strategy JSON — downgrade engine may target non-existent slab _(Analyst)_ — Status: open
- R-3 HIGH: `InfoLookupService` cache not evicted on soft-delete — evaluation engine sees deleted slabs until TTL expiry _(Analyst)_ — Status: open
- R-4 MEDIUM: `getProgramSlabById()` has no `is_active` filter — soft-deleted slabs loadable by direct PK lookup _(Analyst)_ — Status: open
- R-5 HIGH: Thrift IDL in separate repo — 4th repo modification needed, adds deployment complexity _(Analyst)_ — Status: open
- R-6 HIGH: MongoDB-MySQL divergence on APPROVE Thrift failure — must implement rollback _(Analyst)_ — Status: open
- R-8 MEDIUM: No idempotency on APPROVE — retry may create duplicate MySQL slab _(Analyst)_ — Status: open
- R-10 MEDIUM: No `@Transactional` on Thrift impl slab methods — partial failure risk in `deactivateSlab` _(Analyst)_ — Status: open

## Open Questions
_Unresolved questions. Format: `- [ ] [question] _(phase)_` or `- [x] resolved: answer _(phase)_`_
- [x] resolved: Scope is E1 + E4, backend only. No aiRa, no comparison matrix UI, no audit log, no simulation. _(BA)_
- [ ] Does the program context API exist or need to be built? (BRD Section 12, Q1) _(Phase 0)_ — OUT OF SCOPE (aiRa deferred)
- [ ] Is impact simulation real-time or queued? What is SLA? (BRD Section 12, Q2) _(Phase 0)_ — OUT OF SCOPE (simulation deferred)
- [ ] Maker-checker: per-user-role or per-program? Who configures approvers? (BRD Section 12, Q3) _(Phase 0)_ — IN SCOPE: follow UnifiedPromotion pattern
- [ ] Can a benefit be linked to multiple programs or scoped to one? (BRD Section 12, Q4) _(Phase 0)_ — OUT OF SCOPE (benefits deferred)
- [ ] Should aiRa handle multi-turn disambiguation? (BRD Section 12, Q5) _(Phase 0)_ — OUT OF SCOPE (aiRa deferred)
- [x] resolved: `isDowngradeOnReturnEnabled` included as-is in new tier CRUD API — backend logic already exists _(BA)_
- [x] resolved: Migration mechanism is manual SQL DDL in cc-stack-crm. No Flyway in emf-parent. cc-stack-crm DDL files are reference definitions only — ALTER scripts applied manually per environment. _(resolved by Migrator)_
- [ ] Does tier CRUD API need to create/update slab upgrade/downgrade/renewal rulesets, or is that managed separately? _(Analyst)_
- [ ] Should `RequestManagementController` be generalized for multi-entity support, or should tiers get a separate status change endpoint? _(Analyst)_
- [ ] What does `ProgramSlab.metadata` VARCHAR(30) store? Should it be exposed in tier CRUD API? _(Analyst)_
- [ ] Should soft delete validation also check `PartnerProgramTierSyncConfiguration` references? _(Analyst)_
- [x] resolved: Separate TierController endpoint for status changes. Do NOT touch RequestManagementController. _(resolved by Phase 4 B-1)_
- [x] resolved: `ProgramSlab.metadata` VARCHAR(30) stores `SlabMetaData` JSON (contains `colorCode`). Exposed in tier CRUD API as `colorCode` field. _(resolved by Analyst: code-analysis-emf-parent section 1, `getSlabThrift()` line 2178)_
- [x] resolved: Soft delete MUST check PartnerProgramTierSyncConfiguration references — included in HLD DELETE validations. _(resolved by Phase 4 H-3)_
- [ ] Should `deactivateSlab` update SLAB_UPGRADE threshold CSV and SLAB_DOWNGRADE JSON to remove the deleted slab's entries? _(Analyst)_
- [ ] Where is the Thrift IDL repo for PointsEngineRuleService? Is it accessible for adding new methods? _(Analyst)_
- [ ] When an existing tier's threshold is changed via PUT → APPROVE, does `createOrUpdateSlab` auto-update the SLAB_UPGRADE strategy threshold CSV? _(Analyst)_
- [ ] Should serial numbers be renumbered after soft-delete to maintain contiguous ordering for threshold array indexing? _(Analyst)_
- [ ] Should KPI type immutability (all tiers share same `currentValueType`) be enforced at API level during create? _(Analyst)_

## Analyst (Compliance) Findings
_Key findings from gap-analysis-brd.md. Full details in that file._

- All 15 BA/PRD codebase claims verified: 11 confirmed, 4 partial, 0 contradicted _(Analyst)_
- `RequestManagementController.changeStatus()` returns `ResponseWrapper<UnifiedPromotion>` — cannot reuse as-is for tiers without generalizing return type _(Analyst)_
- `PromotionStatus` enum has 10 values (not just the 4 BA listed): includes PAUSED, SNAPSHOT, LIVE, UPCOMING, COMPLETED, PUBLISH_FAILED _(Analyst)_
- Tier creation today involves creating slab upgrade/downgrade/renewal rulesets via `BasicProgramCreator` — not just a ProgramSlab row insert _(Analyst)_
- `PartnerProgramTierSyncConfiguration` maps partner slabs to loyalty slabs — soft delete must check these references (BA missed this) _(Analyst)_
- No Flyway migration framework found in emf-parent — schema managed via SQL scripts in integration-test resources _(Analyst)_
- `ProgramSlab.metadata` VARCHAR(30) field exists but BA/PRD does not mention it _(Analyst)_
- `APIMigrationInterceptor` intercepts all `/v3/**` paths — new tier endpoints will be subject to migration rules _(Analyst)_
- `TierConfiguration` DTO has additional fields not enumerated in BA: `isDowngradeOnPartnerProgramDeLinkingEnabled`, `downgradeConfirmationConfig`, `renewalConfirmationConfig`, `reminders`, `thresholdValues`, `currentValueType`, `trackerId`, `trackerConditionId` _(Analyst)_
- `PeProgramSlabDao` already provides `findByProgram()`, `findByProgramSlabNumber()`, `findNumberOfSlabs()` — reusable for GET endpoints _(Analyst)_
- `program_slabs` has UNIQUE constraint on `(org_id, program_id, serial_number)` — soft delete leaves gaps in serial numbers _(Analyst)_
- ProgramSlab uses composite PK (`@EmbeddedId` with id + orgId) — all operations must include orgId _(Analyst)_

- [ ] [Q-MIG-01] What MySQL version is running in production? Required to confirm CREATE INDEX syntax and online DDL support. _(Migrator)_
- [ ] [Q-MIG-02] Approximate row count of customer_enrollment in production? Required for MIG-02 duration estimate and tool choice (native vs pt-online-schema-change). _(Migrator)_
- [ ] [Q-MIG-03] Is there an existing manual DDL deployment runbook for cc-stack-crm? _(Migrator)_
- [ ] [Q-MIG-04] Are there any existing program_slabs rows that should be treated as inactive before migration runs? (Architecture guarantee says no, but prod state should be verified by DBA.) _(Migrator)_
- [x] resolved: Controller annotation pattern: `@RestController @RequestMapping("/v3/tiers")`, constructor injection with `@Autowired`, `AbstractBaseAuthenticationToken` param, `ResponseEntity<ResponseWrapper<T>>` returns. Discovered from `UnifiedPromotionController.java`. _(Designer)_
- [x] resolved: Facade annotation: `@Component` (not `@Service`). Field `@Autowired` injection. Pattern from `UnifiedPromotionFacade.java`. _(Designer)_
- [x] resolved: MongoDB Document pattern: `@Document(collection = "tiers")`, Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, `@Id String objectId`, `@JsonProperty("id")` alias, `@IgnoreGenerated`. Discovered from `UnifiedPromotion.java`. _(Designer)_
- [x] resolved: TierRepository extends `MongoRepository<TierDocument, String>`. Must be registered in `EmfMongoConfig.includeFilters` alongside `UnifiedPromotionRepository`. _(Designer)_
- [x] resolved: ProgramSlab entity adds `isActive boolean` with `@Basic @Column(name = "is_active")`, manual getter/setter (no Lombok). Uses `javax.persistence.*` (not `jakarta`). _(Designer)_
- [x] resolved: PeProgramSlabDao adds `isActive = true` filter to 3 existing queries + new `findActiveById(int id, int orgId)` returning `Optional<ProgramSlab>`. _(Designer)_
- [x] resolved: PeCustomerEnrollmentDao adds `countMembersPerSlab(@Param orgId, programId, slabIds)` returning `List<Object[]>` for GROUP BY JPQL. _(Designer)_
- [x] resolved: `deactivateSlab` in `PointsEngineRuleConfigThriftImpl` needs `@Transactional("warehouse")` (R-10). Cache eviction: `cacheEvictHelper.evictProgramIdCache(orgId, programId)`. _(Designer)_
- [x] resolved: Thrift IDL adds `MemberCountEntry` + `MemberCountPerSlabResponse` structs, plus `deactivateSlab` + `getMemberCountPerSlab` methods to `PointsEngineRuleService`. Backward-compatible (additive only). _(Designer)_
- [x] resolved: All new timestamp fields (TierDocument, TierResponse) use `java.time.Instant`. ProgramSlab entity keeps `java.util.Date` for JPA compatibility (G-01 compliant: Instant in API surface, Date only in legacy JPA layer). _(Designer)_
- [x] resolved: APPROVE idempotency: if `slabId` already set on TierDocument, return existing response without re-calling Thrift (R-8). _(Designer)_
- [x] resolved: APPROVE rollback: if Thrift fails, revert TierDocument status to PENDING_APPROVAL before propagating exception (R-6). _(Designer)_
- [x] resolved: Version field on TierDocument (`@Builder.Default Integer version = 1`) used for optimistic locking (G-10). APPROVE checks version before write to detect concurrent approval. _(Designer)_
- [x] resolved: `programId` passed to `deactivateSlab` (in addition to `slabId`) because cache eviction requires both. _(Designer)_

## Constraints
_(continued from above — Designer additions)_
- `TierDocument` timestamps must use `java.time.Instant`, not `java.util.Date`. ProgramSlab entity uses `java.util.Date` (legacy JPA — do not change). _(Designer)_
- `TierRepository` MUST appear in `EmfMongoConfig.includeFilters` or it silently uses wrong MongoDB. _(Designer)_
- `deactivateSlab` Thrift impl MUST be `@Transactional("warehouse")` — multiple DAO writes. _(Designer)_
- `deactivateSlab` MUST call `cacheEvictHelper.evictProgramIdCache(orgId, programId)` — same as `createOrUpdateSlab`. _(Designer)_
- `findActiveById()` is a NEW method in `PeProgramSlabDao` — do NOT override the generic `findById()`. _(Designer)_
- Thrift IDL changes in thrifts repo must be compiled and jar updated in emf-parent pom.xml before emf-parent code compiles. _(Designer)_
- `PointsEngineRulesThriftService` adds `createOrUpdateSlab`, `deactivateSlab`, `getMemberCountPerSlab` wrapper methods — no changes to any other method in that class. _(Designer)_

## Open Questions
_(continued — Designer additions)_
- [ ] Q-D1: `PeCustomerEnrollmentDao.countMembersPerSlab()` — does `GenericDao` support `List<Object[]>` JPQL return, or must `nativeQuery = true` be used? _(Designer)_
- [ ] Q-D2: `deactivateSlab` — exact algorithm for rebuilding SLAB_UPGRADE threshold CSV after removing one entry. Must be verified against `ThresholdBasedSlabUpgradeStrategyImpl`. _(Designer)_
- [ ] Q-D3: Does `PointsEngineRuleEditor.createOrUpdateSlab()` auto-update SLAB_UPGRADE CSV on threshold change? Unresolved A-2 from Analyst. _(Designer)_
- [ ] Q-D4: Confirm `@Transactional("warehouse")` is the correct transaction manager name for `deactivateSlab` in emf-parent. _(Designer)_
- [ ] Q-D5: For PUT on ACTIVE tier — copy-on-write (new DRAFT with parentId) or in-place update to PENDING_APPROVAL? _(Designer)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._
