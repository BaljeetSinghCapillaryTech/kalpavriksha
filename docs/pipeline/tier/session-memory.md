# Session Memory

> Artifacts path: docs/pipeline/tier/
> Feature: Tiers CRUD (part of Tiers & Benefits epic)
> Ticket: raidlc/ai_tier
> Workflow started: Phase 0 / 2026-04-11

---

## Domain Terminology
- Slab: Internal codebase term for "tier". ProgramSlab = tier definition. PartnerProgramSlab = tier in a partner program. Slab and Tier are used interchangeably in the codebase. _(BA)_
- ProgramSlab: JPA entity (table: `program_slabs`). Fields: pk (composite: id+orgId), programId, serialNumber, name, description, createdOn, metadata. Note: NO status field, NO color field, NO eligibility config inline. _(BA)_
- PartnerProgramSlab: JPA entity (table: `partner_program_slabs`). Adds loyaltyProgramId, partnerProgramId. Used for multi-loyalty programs where partner programs map slabs to the main program's slabs. _(BA)_
- TierConfiguration: DTO (Gson-serialized JSON stored in metadata or strategy config). Contains: isActive, slabs (TierDowngradeSlabConfig[]), downgradeConfirmation, reminders, renewalConfirmation, retainPoints, isDowngradeOnReturnEnabled, dailyDowngradeEnabled, thresholdValues, currentValueType, trackerId, trackerConditionId. _(BA)_
- SlabUpgradeMode: Enum with EAGER (upgrade before awarding), DYNAMIC (during awarding), LAZY (after awarding). Controls when tier upgrade evaluates during transaction processing. _(BA)_
- TierDowngradeTarget: Enum with SINGLE (one tier below), THRESHOLD (to tier matching current eligibility), LOWEST (base tier). _(BA)_
- SlabAction: Thrift enum with UPGRADE, DOWNGRADE, RENEWAL, EXTEND_CURRENT_TIER_EXPIRY_DATE. _(BA)_
- Eligibility criteria types: Current Points, Lifetime Points, Lifetime Purchases, Tracker Value. Same criteria type must apply to all tiers in a program. _(BA)_
- Upgrade type: Issue Points Then Upgrade, Upgrade Then Issue Points, Issue-Upgrade-Then-Issue-Remaining. _(BA)_
- Renewal condition types: Any (N-1), All, Custom (AND/OR with parentheses). _(BA)_
- Maker-Checker: Approval workflow. Currently exists in intouch-api-v3 for UnifiedPromotion only (PromotionReviewRequest, ApprovalStatus). No tier maker-checker exists today. _(BA)_

## Codebase Behaviour
- ProgramSlab entity is minimal: id, name, description, serialNumber, metadata, createdOn. No status, no color, no eligibility. These are stored in separate strategy configurations (TierConfiguration JSON in metadata or org config). _(BA)_
- No REST API endpoints exist for tier CRUD in intouch-api-v3. Zero controllers/facades for tiers/slabs. All current tier operations go through Thrift (EMFThriftServiceImpl) or internal service calls. _(BA)_
- Tier downgrade logic is complex: TierDowngradeSlabConfig, TierDowngradeConditionConfig, TierDowngradePeriodConfig, TierDowngradeActionConfig, TierDowngradeAlertConfig -- all stored as Gson JSON. _(BA)_
- PEB (Points Engine Backend) handles bulk tier downgrade/reassessment: TierDowngradeBatchServiceImpl, TierReassessmentServiceImpl, various GapToUpgrade calculators. _(BA)_
- Slab upgrade strategies: SlabUpgradeStrategy (interface) -> SlabUpgradeStrategyImpl, ThresholdSlabUpgradeStrategy -> ThresholdBasedSlabUpgradeStrategyImpl. _(BA)_
- Thrift defines ManualSlabAdjustmentData (manual tier changes), CustomerTierTransitionDetails (transition events), TierChangeType (DOWNGRADE, RENEW). _(BA)_
- intouch-api-v3 has maker-checker for promotions (UnifiedPromotionController, ApprovalStatus enum) but NOT for tiers. _(BA)_
- Tiers cannot be inserted between existing tiers or deleted per docs. Must be created in order. _(BA)_

## Key Decisions
- Branch name `raidlc/ai_tier` used across all repos _(Phase 0)_
- Thrift directory treated as read-only reference (not a git repo) _(Phase 0)_
- Multi-epic coordination enabled with registry at BaljeetSinghCapillaryTech/kalpavriksha _(Phase 0)_
- Epic name in registry: `tier-category` (mapped from "Tiers CRUD", covers E1-US1/US2/US3). Assigned to Ritwik (Layer 2). _(Phase 0)_
- Interface philosophy: Option A (Hybrid — Direct UI + aiRa) chosen per BRD recommendation _(Phase 0 — from BRD Section 5)_
- SCOPE: E1-US1 (Listing), E1-US2 (Creation), E1-US3 (Editing) + Tier Deletion (new user story, not in BRD). Plus generic maker-checker framework designed for extensibility (not tier-specific). Change Log (US5) and Simulation (US6) deferred but architecture must support them later. _(BA — Q1)_
- Maker-checker framework must be generic/shared: tiers plug into it, later benefits/change-log/simulation will too. This aligns with registry where maker-checker-framework is a shared module built by ritwik. _(BA — Q1)_
- Tier deletion is soft-delete via status field. Add `status` column to `program_slabs` with values: ACTIVE, DRAFT, STOPPED, DELETED. "Delete" = set status to STOPPED. All existing slab queries must be updated to filter by status. This also enables maker-checker lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE -> STOPPED. _(BA — Q2)_
- Status field is a SCHEMA CHANGE: new column on program_slabs table. Requires Flyway migration. Existing rows default to ACTIVE. All existing queries filtering program_slabs must add WHERE status = 'ACTIVE' (or appropriate filter). _(BA — Q2)_
- DUAL-STORAGE PATTERN: MongoDB for draft/pending tier configs, SQL for live tiers. Follows the exact same pattern as UnifiedPromotion in intouch-api-v3. Create/Edit saves to MongoDB. Maker-checker approval triggers sync to SQL (ProgramSlab + strategy configs). Listing API reads from MongoDB (all states) + SQL (live state). _(BA — Q3)_
- MongoDB tier document must use UI field names (Eligibility Criteria, Membership Duration, Upgrade Schedule, Downgrade Schedule, etc.) because AI simulation mode (E1-US6) will reference them later. _(BA — Q3)_
- VERIFIED PATTERN: UnifiedPromotion uses @Document(collection="unified_promotions"), PromotionStatus enum (DRAFT/PENDING_APPROVAL/ACTIVE/PAUSED/STOPPED/etc.), EntityOrchestrator with Transformer pattern to sync MongoDB->SQL on approval. EmfMongoDataSourceManager for sharded MongoDB access. _(BA — Q3)_
- Tier config status lifecycle (modeled on PromotionStatus): DRAFT -> PENDING_APPROVAL -> ACTIVE -> PAUSED -> STOPPED. DELETED is a soft-delete terminal state. _(BA — Q2+Q3)_
- Member counts in tier listing: cached approach (option c). customer_enrollment table has current_slab_id but no GROUP BY count query exists. Table is hot (millions of evaluations/day). Use a periodic summary (refreshed every 5-15 min) stored in MongoDB tier doc or a small stats table. GET /tiers response includes cached counts. _(BA — Q4)_
- Maker-checker: FULL GENERIC FRAMEWORK (option a). Build PendingChange entity/service, MakerCheckerService interface (submit/approve/reject), domain-specific ChangeApplier strategy. Tiers = first consumer. Benefits, subscriptions, other entities plug in later. This is Layer 1 shared module per registry. _(BA — Q5)_
- Generic MC framework components: PendingChange MongoDB doc (entityType, payload, requestedBy, status, reviewedBy, comment, timestamps), MakerCheckerService (submit/approve/reject/list), ChangeApplier<T> strategy interface (per entity type — TierChangeApplier is the first impl). _(BA — Q5)_
- Tier editing: VERSIONED EDITS (option a, same as unified promotions). Editing an ACTIVE tier creates a new DRAFT MongoDB doc with parentId -> ACTIVE doc. ACTIVE stays live until DRAFT approved. On approval: new doc -> ACTIVE, old doc -> SNAPSHOT. Full rollback capability. Consistent with existing UnifiedPromotion.parentId pattern. _(BA — Q6)_
- Version lifecycle: CREATE -> DRAFT. SUBMIT -> PENDING_APPROVAL. APPROVE -> ACTIVE (old -> SNAPSHOT). REJECT -> back to DRAFT. EDIT ACTIVE -> new DRAFT with parentId. STOP -> STOPPED (soft-delete). _(BA — Q6)_
- API hosting: intouch-api-v3 serves tier CRUD REST APIs + MongoDB draft storage + maker-checker. On approval, syncs to emf-parent via Thrift (same as unified promotions). emf-parent owns core business logic, JPA entities, strategy configs. _(BA — Q7)_
- Call chain on approval: intouch-api-v3 REST -> MakerCheckerService.approve() -> TierChangeApplier -> Thrift call -> emf-parent PointsEngineRuleService.createSlabAndUpdateStrategies() -> SQL write. _(BA — Q7)_
- Maker-checker toggle: per-program + per-entity-type granularity. isMakerCheckerEnabled(orgId, programId, entityType). When disabled: Create -> ACTIVE immediately, Edit -> applied immediately (no DRAFT/PENDING states). Config stored in org-level settings. _(BA — Q8)_

## UI Findings (Phase 3)
- UI shows "Duration" per tier (start date + end date or Indefinite) -- NOT in BA/PRD. Likely maps to tier validity period. NEEDS field addition to MongoDB doc. _(Phase 3 — GAP-1)_
- UI shows compound activity conditions with AND/OR logic ("Spending >= RM 550 AND Min 2 transactions"). Condition model (operator, value, unit, relation) not defined in BA. _(Phase 3 — GAP-2)_
- "Membership Duration" (Eligibility section: "12 months"/"Indefinite") is DIFFERENT from "Duration" (Basic Details: date range). BA/PRD conflates these. _(Phase 3 — GAP-3)_
- Downgrade Schedule has two values: MONTH_END and DAILY, rendered as color-coded badges. _(Phase 3 — GAP-4)_
- Benefits on tier page are a cross-tier comparison matrix (benefit rows x tier columns). API response must be matrix-compatible. _(Phase 3 — GAP-5)_
- 21 per-tier fields identified; 3 missing from BA/PRD (duration, activityRelation, membershipDuration). _(Phase 3)_
- 4 KPI summary fields (totalTiers, activeTiers, scheduledTiers, totalMembers). "Scheduled" undefined. _(Phase 3)_
- 8 screens analyzed: 4 in scope (tier listing), 4 reference-only (benefits). _(Phase 3)_

## Constraints
- Scope: Tier CRUD (List, Create, Edit, Delete) + extensible Maker-Checker framework. NOT change log, NOT simulation mode. _(BA — Q1)_
- Scope limited to "Tiers CRUD" — subset of the full Tiers & Benefits BRD (Epic E1 primarily) _(Phase 0)_
- Tech stack: Java, Spring, Thrift, MySQL, MongoDB, Flyway, JUnit 4, Mockito _(Phase 0)_
- Four repos involved: emf-parent (entities/strategies), intouch-api-v3 (REST/maker-checker), peb (tier downgrade), Thrift (IDL definitions) _(Phase 0)_
- UI screenshots pending from user for v0.app tier management screens _(Phase 0)_

## Risks & Concerns
- jdtls LSP: installed (v1.57.0, Java 23), running via /tmp/emf-parent symlink. Patched find_daemon_for_cwd for symlink resolution. _(Phase 0)_ -- Status: mitigated
- Registry repo has full decomposition on `raidlc/rtest123/epic-division` branch. _(Phase 0)_ -- Status: mitigated
- tier-category consumes maker-checker-framework (owner: ritwik) and audit-trail-framework (owner: anuj). Both status: "designed" (not built yet). Will need mocks during development. _(Phase 0)_ -- Status: open
- BLOCKER C-1: No Thrift method exists in emf.thrift for tier config sync (createSlab/updateSlab). The approval flow (MongoDB->SQL via Thrift) has no existing transport. Must add new Thrift method or use alternative. _(Critic)_ -- Status: OPEN BLOCKER
- HIGH C-2: PartnerProgramSlab impact not addressed. Stopping a ProgramSlab could break partner program slab references. Need validation or cascade logic. _(Critic)_ -- Status: open
- HIGH C-3: PeProgramSlabDao used in 7+ services (InfoLookupService, PointsEngineRuleService, PointsReturnService, ProgramCreationService, PointsEngineServiceManager, BulkOrgConfigImportValidator). Adding status filter is high blast radius. Use expand-then-contract migration. _(Critic)_ -- Status: open
- MEDIUM C-4: Threshold validation oversimplified. Thresholds stored as CSV in strategy properties, not per-slab. AND/OR conditions possible. Exact validation rules deferred to HLD. _(Critic)_ -- Status: open
- MEDIUM G-5: MongoDB is sharded (EmfMongoDataSourceManager.getAll()). Tier repository must handle multi-shard scenarios like UnifiedPromotionRepository. _(Analyst)_ -- Status: open
- MEDIUM G-6: Edit flow is more complex than parentId alone. Promotions use DraftDetails, ParentDetails, UnifiedPromotionEditOrchestrator, StatusTransitionValidator. Need full pattern study. _(Analyst)_ -- Status: open

## Open Questions
- [x] resolved: UI screenshots provided (8 screenshots from v0.app). _(Phase 0)_
- [x] resolved: Registry has full decomposition at `raidlc/rtest123/epic-division`. Epic `tier-category` assigned to Ritwik. _(Phase 0)_
- [ ] BLOCKER: What transport mechanism for tier config sync on approval? New Thrift method needed, or alternative? _(Critic C-1)_
- [ ] What happens to PartnerProgramSlabs when a ProgramSlab is stopped? Block? Cascade? Warn? _(Critic C-2)_
- [ ] What is the exact Thrift method signature needed for the new tier sync operation? _(BA)_
- [ ] How should the member count cache be refreshed? _(BA)_
- [ ] Should MC notification use existing system or hook interface? _(BA)_
- [ ] Benefits linkage in listing: full config or just references? _(BA)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._
