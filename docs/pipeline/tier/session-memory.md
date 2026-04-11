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

## Three-Way Gap Analysis (Phase 4 -- Codebase vs UI vs BRD)
**Category A -- In codebase but NOT in BA/PRD:**
- A-1: retainPoints (boolean on TierConfiguration) -- preserve in MongoDB doc _(Phase 4)_
- A-2: isDowngradeOnReturnEnabled -- BRD asks if this should be surfaced or deprecated. DECISION NEEDED. _(Phase 4)_
- A-3: isDowngradeOnPartnerProgramExpiryEnabled -- partner program concern, preserve in MongoDB doc _(Phase 4)_
- A-4: computationWindowStartValue/EndValue on TierDowngradePeriodConfig -- hidden config, preserve _(Phase 4)_
- A-5: minimumDuration on TierDowngradePeriodConfig -- hidden config, preserve _(Phase 4)_
- A-6: PeriodType enum (FIXED, SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC, FIXED_CUSTOMER_REGISTRATION) -- critical engine config, preserve _(Phase 4)_
- A-7: Per-slab notification templates (SMS, Email, WeChat, MobilePush with per-channel configs) -- UI shows free-text "Nudges" but codebase has detailed per-channel configs. MongoDB doc must store BOTH human-readable nudge AND channel configs. _(Phase 4)_
- A-8: expressionRelation (ArrayList<ArrayList<Integer>>) + customExpression -- how compound upgrade criteria stored. Maps to UI AND/OR pills. _(Phase 4)_
- A-9: AdditionalUpgradeCriteria -- secondary upgrade criteria with own thresholds, currentValueType, slabUpgradeMode, trackerId. Programs can have MULTIPLE criteria. _(Phase 4)_
- A-10: Program-level slab settings (slabUpgradePointCategoryID, slabUpgradeStrategy ID, slabUpgradeMode, slabUpgradeRuleIdentifier) -- apply to ALL tiers, not per-tier. Listing API may need to return as program context. _(Phase 4)_
- A-11: PartnerProgramSlabHistory -- historical audit records. Relevant for future change log (E1-US5). _(Phase 4)_
**Category B -- In UI but NOT in codebase or BA/PRD:**
- B-1: "Tier Settings" button -- unclear what it opens. May be program-level tier settings. _(Phase 4)_
- B-2: "Filter Tiers" button -- API needs filter support. PRD has ?status= only. _(Phase 4)_
- B-3: Per-benefit value-per-tier comparison -- tier listing needs to JOIN benefit data from promotions system. _(Phase 4)_
- B-4: "Manage benefits" navigation link -- UI concern, no API change. _(Phase 4)_
**Category C -- In BRD but NOT in codebase or UI:**
- C-1: Impact simulation -- out of scope, architecture supports via member count cache. _(Phase 4)_
- C-2: Focus Mode -- purely UI, no API change. _(Phase 4)_
- C-3: aiRa button -- out of scope (E3). _(Phase 4)_
- C-4: Dirty state tracking -- UI concern, API supports via DRAFT status. _(Phase 4)_

## Production Payload Analysis (Phase 5 -- from /loyalty/api/v1/strategy/tier-strategy/977)
- P-1 CRITICAL: pointsSaveData (allocations, redemptions, expirys) -- entire points strategy layer not in BA/PRD. Per-slab strategies with CSV values per tier. 13+ allocation strategies, 5+ redemption, 5+ expiry. MongoDB doc must store for round-trip fidelity. New tier listing API returns summary count, not full details. _(Phase 5)_
- P-2: CSV-per-slab pattern is pervasive. Every strategy property uses comma-separated values (position N = slab N). Creating a new slab requires extending EVERY strategy CSV. Handled by existing createSlabAndUpdateStrategies Thrift method + PointsEngineRuleService logic at line 3821. TierChangeApplier must pass correct strategy list. _(Phase 5)_
- P-3: upgrade section confirmed. current_value_type=CUMULATIVE_PURCHASES, threshold_value as array, secondary_criteria_enabled=false. Matches our model. _(Phase 5)_
- P-4: downgrade section has new fields: isFixedTypeWithoutYear (bool), renewalWindowType ("FIXED_DATE_BASED" -- different naming from PeriodType enum). condition="SLAB_UPGRADE" used as condition name. All must be preserved in MongoDB doc. _(Phase 5)_
- P-5: isAdvanceSetting (bool -- UI rendering hint) and addDefaultCommunication (bool -- auto-create notification templates) -- new flags not in BA. Store in MongoDB doc. _(Phase 5)_
- P-6: updatedViaNewUI flag on SlabInfo and StrategyInfo. New tier APIs must set updatedViaNewUI=true on all strategies they create/modify. _(Phase 5)_

## TierChangeApplier Conversion Design (Phase 5 Deep Dive)
- Strategy entity (SQL: strategies table): id, orgId, programId, name, description, strategyTypeId, propertyValues (JSON string), owner, createdOn _(Phase 5)_
- StrategyType IDs: 1=POINT_ALLOCATION, 2=SLAB_UPGRADE, 3=POINT_EXPIRY, 4=POINT_REDEMPTION_THRESHOLD, 5=SLAB_DOWNGRADE, 6=POINT_RETURN, 7=EXPIRY_REMINDER, 8=TRACKER, 9=POINT_EXPIRY_EXTENSION _(Phase 5)_
- CREATE new slab: Call createOrUpdateSlab(SlabInfo) via Thrift. Engine auto-extends all allocation/expiry CSV values with appended "0". TierChangeApplier does NOT send strategy list for basic creation. _(Phase 5)_
- UPDATE slab config: Call createSlabAndUpdateStrategies(SlabInfo, list<StrategyInfo>). TierChangeApplier converts MongoDB config -> StrategyInfo list. _(Phase 5)_
- Conversion: eligibilityCriteria -> StrategyType 2 (SLAB_UPGRADE) propertyValues JSON {current_value_type, threshold_values CSV, expression_relation, slab_upgrade_mode, tracker_id, tracker_condition_id} _(Phase 5)_
- Conversion: downgradeConfig -> StrategyType 5 (SLAB_DOWNGRADE) propertyValues JSON = full TierConfiguration JSON {is_active, slabs[], dailyDowngradeEnabled, retainPoints, isDowngradeOnReturnEnabled, renewalConfirmation, reminders} _(Phase 5)_
- Points strategies (allocation/redemption/expiry) NOT managed by tier CRUD. On new slab, engine auto-extends. On edit, existing values preserved. _(Phase 5)_
- Slab upgrade strategy property format: {current_value_type: "CUMULATIVE_PURCHASES", threshold_values: "2000,5000,12000"} -- CSV has N-1 values for N slabs (base slab has no threshold) _(Phase 5)_
- createOrUpdateSlab internally calls updateStrategiesForNewSlab which iterates all POINT_ALLOCATION and POINT_EXPIRY strategies and appends default values for the new slab position _(Phase 5)_
- FLOW 1 VALIDATED: Use createSlabAndUpdateStrategies as SINGLE atomic Thrift call. Pass ONLY SLAB_UPGRADE and SLAB_DOWNGRADE strategies. Engine auto-handles allocation/expiry CSV extension. Method order: update strategies FIRST, then create slab (which triggers CSV extension). All in one transaction. _(Phase 5 validation)_
- FLOW 1 RISK: updateStrategiesForNewSlab only extends POINT_ALLOCATION(1) and POINT_EXPIRY(3). Does NOT extend POINT_REDEMPTION_THRESHOLD(4). Redemption CSVs may be mismatched after new slab creation. Existing engine may handle this gracefully or it may be a latent bug. Low risk for now -- redemption strategies typically use SLAB_INDEPENDENT type. _(Phase 5 validation)_

## Constraints
- Scope: Tier CRUD (List, Create, Edit, Delete) + extensible Maker-Checker framework. NOT change log, NOT simulation mode. _(BA — Q1)_
- Scope limited to "Tiers CRUD" — subset of the full Tiers & Benefits BRD (Epic E1 primarily) _(Phase 0)_
- Tech stack: Java, Spring, Thrift, MySQL, MongoDB, Flyway, JUnit 4, Mockito _(Phase 0)_
- Four repos involved: emf-parent (entities/strategies), intouch-api-v3 (REST/maker-checker), peb (tier downgrade), Thrift (IDL definitions) _(Phase 0)_
- UI screenshots provided (8 files). _(Phase 0 -- updated)_
- 7 ADRs documented: ADR-01 (dual-storage), ADR-02 (generic MC), ADR-03 (expand-then-contract), ADR-04 (versioned edits), ADR-05 (existing Thrift), ADR-06 (new programs only), ADR-07 (atomic Thrift call) _(Architect)_
- 4-layer implementation plan: L1 MC Framework, L2 Tier CRUD, L3 emf-parent changes, L4 integration + cache _(Architect)_
- MongoDB document schema: UnifiedTierConfig with 8 top-level sections (basicDetails, eligibilityCriteria, renewalConfig, downgradeConfig, benefitIds, memberStats, engineConfig, metadata) _(Architect)_
- PendingChange generic schema: entityType, entityId, payload (full snapshot), status, requestedBy, reviewedBy _(Architect)_
- Impact analysis: blast radius SMALL (2 modified in emf-parent, 0 in peb/Thrift). Full backward compatibility. _(Analyst)_
- GUARDRAILS attention: G-01 (use Instant not Date in new code), G-06.1 (add idempotency key for POST /tiers), G-07.3 (cron job tenant context) _(Analyst)_
- 8 risks catalogued: R1 CSV off-by-one (HIGH), R2 downgrade race (MEDIUM, mitigated), R3 strategy ID collision (MEDIUM), R4 member count index (MEDIUM), R5 timezone (MEDIUM), R6 idempotency (LOW), R7 cron tenant (LOW), R8 MC self-approval (LOW, product decision) _(Analyst)_
- Security: COMPLIANT with G-03. Auth via token, parameterized queries, no PII exposure. One product question: should MC prevent self-approval? _(Analyst)_
- Performance: Tier listing <200ms. Member count cache needs INDEX on customer_enrollment(org_id, program_id, current_slab_id, is_active). Separate Flyway migration. _(Analyst)_

## Risks & Concerns
- jdtls LSP: installed (v1.57.0, Java 23), running via /tmp/emf-parent symlink. Patched find_daemon_for_cwd for symlink resolution. _(Phase 0)_ -- Status: mitigated
- Registry repo has full decomposition on `raidlc/rtest123/epic-division` branch. _(Phase 0)_ -- Status: mitigated
- tier-category consumes maker-checker-framework (owner: ritwik) and audit-trail-framework (owner: anuj). Both status: "designed" (not built yet). Will need mocks during development. _(Phase 0)_ -- Status: open
- BLOCKER C-1: REVISED in Phase 5. Thrift methods ALREADY EXIST in pointsengine_rules.thrift (NOT emf.thrift): createSlabAndUpdateStrategies(programId, orgId, SlabInfo, list<StrategyInfo>, ...), getAllSlabs(programId, orgId, ...), createOrUpdateSlab(SlabInfo, orgId, ...). PointsEngineRulesThriftService in intouch-api-v3 is the client but does NOT currently wrap slab methods. Fix: add wrapper methods to PointsEngineRulesThriftService. NO new Thrift IDL change needed for basic CRUD. May still need new method for status updates (STOPPED). _(Phase 5)_ -- Status: REVISED (simpler than thought)
- HIGH C-2: RESOLVED. Block stop if PartnerProgramSlabs exist (409 Conflict). Known limitation documented for Anuj's supplementary-partner-program epic to add cascade/management logic. _(Phase 4 — HIGH #1)_ -- Status: RESOLVED
- HIGH C-3: RESOLVED. Expand-then-contract migration. Add status column (DEFAULT 'ACTIVE'). Add NEW DAO method findActiveByProgram() with status filter. Do NOT modify existing findByProgram(). New tier listing API uses new method. Existing engine callers unchanged -- they see all slabs (correct for upgrade/downgrade serial number logic). Future phase audits existing callers. _(Phase 4 — HIGH #2)_ -- Status: RESOLVED
- MEDIUM C-4: Threshold validation oversimplified. Thresholds stored as CSV in strategy properties, not per-slab. AND/OR conditions possible. Exact validation rules deferred to HLD. _(Critic)_ -- Status: deferred to HLD
- MEDIUM G-5: MongoDB is sharded (EmfMongoDataSourceManager.getAll()). Tier repository must handle multi-shard scenarios like UnifiedPromotionRepository. _(Analyst)_ -- Status: noted for HLD
- MEDIUM G-6: Edit flow is more complex than parentId alone. Promotions use DraftDetails, ParentDetails, UnifiedPromotionEditOrchestrator, StatusTransitionValidator. Need full pattern study in Phase 5. _(Analyst)_ -- Status: noted for Phase 5
- A-2: isDowngradeOnReturnEnabled -- preserve in MongoDB doc as hidden config, don't surface in UI, pass through on Thrift sync. _(Phase 4 — SCOPE #2)_ -- Status: RESOLVED
- A-7: Notification templates -- store BOTH nudges text field (UI display) AND notificationConfig object (engine sync). Coexist independently. New tiers start with empty notificationConfig. Existing tiers populated from strategy config on sync. _(Phase 4 — SCOPE #3)_ -- Status: RESOLVED
- A-1,A-3-A-6,A-8-A-11: All preserved in MongoDB doc design. Hidden engine configs (retainPoints, partnerProgramExpiry, periodConfig, computationWindow, minimumDuration, PeriodType, expressionRelation, additionalCriteria, program-level slab settings) stored in the doc for round-trip fidelity. _(Phase 4)_ -- Status: RESOLVED
- GAP-1: Tier Duration (startDate/endDate) added to MongoDB doc. Maps to membership validity period. endDate=null means Indefinite. _(Phase 4 — SCOPE #1)_ -- Status: RESOLVED

## Open Questions
- [x] resolved: UI screenshots provided (8 screenshots from v0.app). _(Phase 0)_
- [x] resolved: Registry has full decomposition at `raidlc/rtest123/epic-division`. Epic `tier-category` assigned to Ritwik. _(Phase 0)_
- [x] resolved: New Thrift method configureTier() in emf.thrift. SQL write stays in emf-parent. _(Phase 4 — Blocker #1)_
- [x] resolved: Block stop (409 Conflict) if PartnerProgramSlabs exist. Cascade deferred to Anuj's SPP epic. _(Phase 4 — HIGH #1)_
- [x] resolved: Thrift method signature -- deferred to HLD (Phase 6). Method name: configureTier(). _(Phase 4)_
- [x] resolved: Member count cache -- scheduled job (cron) every 10 min. GROUP BY current_slab_id query -> writes to MongoDB tier docs. _(Phase 4 — GQ)_
- [x] resolved: MC notification -- hook interface only (NotificationHandler with onSubmit/onApprove/onReject). No-op default. _(Phase 4 — GQ-5)_
- [x] resolved: Benefits linkage -- store benefitIds only on tier doc. UI fetches benefit details separately. _(Phase 4 — GQ-4 override)_
- [x] resolved: No pagination for tier listing. Full list returned. Max 50 tiers validation cap. _(Phase 4 — GQ-1)_
- [x] resolved: NO bootstrap sync for existing programs. New tier CRUD is for NEW programs only. Old programs keep current system. _(Phase 4 — GQ-2 override)_
- [x] resolved: Versioned edit flow confirmed as Flow A. ACTIVE stays live until DRAFT approved. On approval: old->SNAPSHOT, new->ACTIVE. Zero downtime. _(Phase 4 — GQ-3)_
- [x] resolved: PendingChange stores full snapshot, not diff. _(Phase 4 — GQ-6)_
- [x] resolved: KPI "Scheduled" replaced with "Pending Approval". No goLiveDate concept for now. _(Phase 4 — C-5)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._
