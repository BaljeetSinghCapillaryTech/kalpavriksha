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

## Open Questions
_Unresolved questions. Format: `- [ ] [question] _(phase)_` or `- [x] resolved: answer _(phase)_`_
- [x] resolved: Scope is E1 + E4, backend only. No aiRa, no comparison matrix UI, no audit log, no simulation. _(BA)_
- [ ] Does the program context API exist or need to be built? (BRD Section 12, Q1) _(Phase 0)_ — OUT OF SCOPE (aiRa deferred)
- [ ] Is impact simulation real-time or queued? What is SLA? (BRD Section 12, Q2) _(Phase 0)_ — OUT OF SCOPE (simulation deferred)
- [ ] Maker-checker: per-user-role or per-program? Who configures approvers? (BRD Section 12, Q3) _(Phase 0)_ — IN SCOPE: follow UnifiedPromotion pattern
- [ ] Can a benefit be linked to multiple programs or scoped to one? (BRD Section 12, Q4) _(Phase 0)_ — OUT OF SCOPE (benefits deferred)
- [ ] Should aiRa handle multi-turn disambiguation? (BRD Section 12, Q5) _(Phase 0)_ — OUT OF SCOPE (aiRa deferred)
- [x] resolved: `isDowngradeOnReturnEnabled` included as-is in new tier CRUD API — backend logic already exists _(BA)_
- [ ] What is the actual migration mechanism for emf-parent schema changes? No Flyway found. _(Analyst)_
- [ ] Does tier CRUD API need to create/update slab upgrade/downgrade/renewal rulesets, or is that managed separately? _(Analyst)_
- [ ] Should `RequestManagementController` be generalized for multi-entity support, or should tiers get a separate status change endpoint? _(Analyst)_
- [ ] What does `ProgramSlab.metadata` VARCHAR(30) store? Should it be exposed in tier CRUD API? _(Analyst)_
- [ ] Should soft delete validation also check `PartnerProgramTierSyncConfiguration` references? _(Analyst)_

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

## Rework Log
_Tracks re-run cycles to detect unresolved loops._
