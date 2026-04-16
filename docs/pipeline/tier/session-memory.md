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
- ~~Tier deletion is soft-delete via status field. Add `status` column to `program_slabs`.~~ SUPERSEDED by Rework #3: No SQL changes needed. MongoDB owns lifecycle. SQL only contains ACTIVE tiers. _(BA — Q2, superseded Rework #3)_
- ~~Status field is a SCHEMA CHANGE.~~ SUPERSEDED by Rework #3: ProgramSlab status column, findActiveByProgram(), and Flyway migration all removed from scope. Deferred to future tier retirement epic. _(BA — Q2, superseded Rework #3)_
- DUAL-STORAGE PATTERN: MongoDB for draft/pending tier configs, SQL for live tiers. Follows the exact same pattern as UnifiedPromotion in intouch-api-v3. Create/Edit saves to MongoDB. Maker-checker approval triggers sync to SQL (ProgramSlab + strategy configs). Listing API reads from MongoDB (all states) + SQL (live state). _(BA — Q3)_
- MongoDB tier document must use UI field names (Eligibility Criteria, Membership Duration, Upgrade Schedule, Downgrade Schedule, etc.) because AI simulation mode (E1-US6) will reference them later. _(BA — Q3)_
- VERIFIED PATTERN: UnifiedPromotion uses @Document(collection="unified_promotions"), PromotionStatus enum (DRAFT/PENDING_APPROVAL/ACTIVE/PAUSED/STOPPED/etc.), EntityOrchestrator with Transformer pattern to sync MongoDB->SQL on approval. EmfMongoDataSourceManager for sharded MongoDB access. _(BA — Q3)_
- Tier config status lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE. DRAFT -> DELETED (terminal, soft-delete). No PAUSED, no STOPPED, no RESUME status for tiers. Only DRAFT tiers can be deleted. Tier retirement (stopping ACTIVE tiers) deferred to future epic. _(BA — Q2+Q3, updated Rework #2)_
- Tier reordering NOT supported. serialNumber is immutable and auto-assigned. Any attempt to change serialNumber returns 400. _(Rework #2)_
- Tier deletion is DRAFT-only: DELETE /v3/tiers/{tierId} → sets status to DELETED. Returns 409 if not DRAFT. No MC flow needed (DRAFT is pre-approval). No member reassessment (DRAFT tiers have no members). _(Rework #2)_
- Member counts in tier listing: cached approach (option c). customer_enrollment table has current_slab_id but no GROUP BY count query exists. Table is hot (millions of evaluations/day). Use a periodic summary (refreshed every 5-15 min) stored in MongoDB tier doc or a small stats table. GET /tiers response includes cached counts. _(BA — Q4)_
- Maker-checker: FULL GENERIC FRAMEWORK (option a). Build PendingChange entity/service, MakerCheckerService interface (submit/approve/reject), domain-specific ChangeApplier strategy. Tiers = first consumer. Benefits, subscriptions, other entities plug in later. This is Layer 1 shared module per registry. _(BA — Q5)_
- Generic MC framework components: PendingChange MongoDB doc (entityType, payload, requestedBy, status, reviewedBy, comment, timestamps), MakerCheckerService (submit/approve/reject/list), ChangeApplier<T> strategy interface (per entity type — TierChangeApplier is the first impl). _(BA — Q5)_
- Tier editing: VERSIONED EDITS (option a, same as unified promotions). Editing an ACTIVE tier creates a new DRAFT MongoDB doc with parentId -> ACTIVE doc. ACTIVE stays live until DRAFT approved. On approval: new doc -> ACTIVE, old doc -> SNAPSHOT. Full rollback capability. Consistent with existing UnifiedPromotion.parentId pattern. _(BA — Q6)_
- Version lifecycle: CREATE -> DRAFT. SUBMIT -> PENDING_APPROVAL. APPROVE -> ACTIVE (old -> SNAPSHOT). REJECT -> back to DRAFT (promotion pattern, via ChangeApplier.revert()). EDIT ACTIVE -> new DRAFT with parentId. _(BA — Q6, updated Rework #3)_
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

## Figma Design Analysis (2026-04-14 -- replaces v0.app screenshots)
- Source: Figma file "AMJ - Loyalty Revamp" (node 1508:20810, "Tiers" section). 10 frames downloaded to UI/figma-tiers/. _(Figma)_
- 6 sections: Create tier Steps 1-5 + Tier homepage. Step 4 (Impact & Transition) NOT DESIGNED (duplicate of Step 3). _(Figma)_
- **Create wizard is 4-step**: 1. General, 2. Eligibility, 3. Validity & renewal, 4. Impact & Transition. _(Figma)_
- **Step 1 (General)**: Tier name, Tier number (user input -- OVERRIDDEN: keep auto-assigned serialNumber per our design), Description (optional), Tier colour (optional). _(Figma)_
- **Step 2 (Eligibility)**: Eligibility threshold (criteria dropdown + operator dropdown + value). Qualifying conditions (optional, group-based: Group condition N with + Add criteria / + Add group condition). _(Figma)_
- **Step 3 (Validity & renewal)**: Renewal conditions (criteria + operator + value), "If renewal criteria not met" dropdown, "Downgrade to" dropdown ("One tier below"). _(Figma)_
- **Step 5 (Tier program settings modal)**: Program-level config opened via "Configure >" link. Fields: Upgrade type (dropdown), Validity period (dropdown), Fixed duration (value + unit), 3 toggles (return transaction downgrade, daily expiry, extend points). _(Figma)_
- DECISION: Tier number stays auto-assigned (ignore Figma user input). _(Figma — user override)_
- DECISION: New `GET/PUT /v3/tier-settings` endpoint added for program-level config. _(Figma)_
- DECISION: startDate/endDate kept in API (confirmed by Figma homepage Duration column). _(Figma)_
- DECISION: Step 4 (Impact & Transition) skipped -- not designed. _(Figma)_
- DECISION: Partial saves (wizard steps) deferred. _(Figma)_
- Homepage shows cross-tier comparison table with tabs: Basic details, Eligibility criteria, Renewal criteria, Downgrade criteria, Benefits. Matches our TierListResponse structure. _(Figma)_
- API handoff updated to 13 endpoints (was 11): + GET /v3/tier-settings + PUT /v3/tier-settings. _(Figma)_

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
- Conversion: eligibility (TierEligibilityConfig) -> StrategyType 2 (SLAB_UPGRADE) propertyValues JSON {current_value_type, threshold_values CSV, expression_relation, slab_upgrade_mode, tracker_id, tracker_condition_id} _(Phase 5, updated Phase D)_
- Conversion: downgrade (TierDowngradeConfig) -> StrategyType 5 (SLAB_DOWNGRADE) propertyValues JSON = full TierConfiguration JSON {is_active, slabs[], dailyDowngradeEnabled, retainPoints, isDowngradeOnReturnEnabled, renewalConfirmation, reminders} _(Phase 5, updated Phase D)_
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
- UI: Figma designs (AMJ - Loyalty Revamp, node 1508:20810) + 8 v0.app screenshots. 10 Figma frames downloaded to UI/figma-tiers/. _(Phase 0, updated 2026-04-14)_
- 7 ADRs documented: ADR-01 (dual-storage), ADR-02 (generic MC), ADR-03 (expand-then-contract), ADR-04 (versioned edits), ADR-05 (existing Thrift), ADR-06 (new programs only), ADR-07 (atomic Thrift call) _(Architect)_
- 4-layer implementation plan: L1 MC Framework, L2 Tier CRUD, L3 emf-parent changes, L4 integration + cache _(Architect)_
- API handoff v1.2: 13 endpoints total (4 tier CRUD + 1 MC submit + 2 MC approve/reject + 1 MC list pending + 1 tier detail + 1 MC config + 1 change detail + 2 tier-settings GET/PUT). No PAUSED status. Tier reorder not supported (serialNumber immutable). Idempotency-Key on POST /v3/tiers. _(Phase 7.5, updated Figma review)_
- Production payload validation (program 977): 5 missing engineConfig fields discovered. Added: slabUpgradeMode (program-level, from upgrade.slab_upgrade_mode), downgradeEngineConfig.isActive (from downgrade.is_active), downgradeEngineConfig.conditionAlways (from downgrade.condition_always), downgradeEngineConfig.conditionValues (purchase/numVisits/points/trackerCount), downgradeEngineConfig.renewalOrderString. Full legacy-to-new mapping table added to api-handoff Section 16. _(Phase 7.5 — production validation)_
- criteriaType: new API uses SAME production enum values (CUMULATIVE_PURCHASES, CURRENT_POINTS, etc.). No conversion needed in TierChangeApplier -- values pass through directly. Threshold format differs: production uses program-wide CSV array (N-1 values), our API uses per-tier individual values -- TierChangeApplier joins/splits during sync. _(Phase 7.5, updated Phase 7-rework)_
- MongoDB document schema: UnifiedTierConfig with 9 top-level sections (basicDetails, eligibility, validity, downgrade, nudges, benefitIds, memberStats, engineConfig, metadata) — field names engine-aligned per Phase D rework. Old names: eligibilityCriteria→eligibility, renewalConfig→validity, downgradeConfig→downgrade, nudges added. Model classes: TierEligibilityConfig, TierValidityConfig, TierDowngradeConfig, TierNudgesConfig, TierCondition, TierRenewalConfig. All use String types for enum-like fields (kpiType, upgradeType, target, periodType) matching prototype pattern. _(Architect, updated Phase D)_
- PendingChange generic schema: entityType, entityId, payload (full snapshot), status, requestedBy, reviewedBy _(Architect)_
- Impact analysis: blast radius SMALL (2 modified in emf-parent, 0 in peb/Thrift). Full backward compatibility. _(Analyst)_
- GUARDRAILS attention: ~~G-01 (use Instant not Date)~~ OVERRIDDEN Rework #3 — use Date + @JsonFormat(XXX) to match promotion pattern, G-06.1 (add idempotency key for POST /tiers), G-07.3 (cron job tenant context) _(Analyst, updated Rework #3)_
- 8 risks catalogued: R1 CSV off-by-one (HIGH), R2 downgrade race (MEDIUM, mitigated), R3 strategy ID collision (MEDIUM), R4 member count index (MEDIUM), R5 timezone (MEDIUM), R6 idempotency (LOW), R7 cron tenant (LOW), R8 MC self-approval (LOW, product decision) _(Analyst)_
- Security: COMPLIANT with G-03. Auth via token, parameterized queries, no PII exposure. One product question: should MC prevent self-approval? _(Analyst)_
- Performance: Tier listing <200ms. Member count cache needs INDEX on customer_enrollment(org_id, program_id, current_slab_id, is_active). Separate Flyway migration. _(Analyst)_

## Risks & Concerns
- jdtls LSP: installed (v1.57.0, Java 23), running via /tmp/emf-parent symlink. Patched find_daemon_for_cwd for symlink resolution. _(Phase 0)_ -- Status: mitigated
- Registry repo has full decomposition on `raidlc/rtest123/epic-division` branch. _(Phase 0)_ -- Status: mitigated
- tier-category consumes maker-checker-framework (owner: ritwik) and audit-trail-framework (owner: anuj). Both status: "designed" (not built yet). Will need mocks during development. _(Phase 0)_ -- Status: open
- BLOCKER C-1: REVISED in Phase 5. Thrift methods ALREADY EXIST in pointsengine_rules.thrift (NOT emf.thrift): createSlabAndUpdateStrategies(programId, orgId, SlabInfo, list<StrategyInfo>, ...), getAllSlabs(programId, orgId, ...), createOrUpdateSlab(SlabInfo, orgId, ...). PointsEngineRulesThriftService in intouch-api-v3 is the client but does NOT currently wrap slab methods. Fix: add wrapper methods to PointsEngineRulesThriftService. NO new Thrift IDL change needed for basic CRUD. May still need new method for status updates (STOPPED). _(Phase 5)_ -- Status: REVISED (simpler than thought)
- HIGH C-2: RESOLVED. Block stop if PartnerProgramSlabs exist (409 Conflict). Known limitation documented for Anuj's supplementary-partner-program epic to add cascade/management logic. _(Phase 4 — HIGH #1)_ -- Status: RESOLVED
- ~~HIGH C-3: Expand-then-contract migration.~~ SUPERSEDED by Rework #3: No SQL changes needed. ProgramSlab status column removed from scope entirely. _(Phase 4 — HIGH #2, superseded Rework #3)_ -- Status: NOT NEEDED
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

## QA Findings (Phase 8)
- 89 test scenarios covering 52/52 acceptance criteria, 7/7 ADRs, 8 risks, 6 guardrail areas _(QA)_
- Most critical gap: No test infrastructure for MongoDB + Thrift integration tests in intouch-api-v3. SDET must establish embedded MongoDB + Thrift mock. _(QA)_
- ~45 existing test files in emf-parent + peb need regression runs after Flyway migration (ADR-03 expand-then-contract) _(QA)_
- 0 existing tier/MC tests in intouch-api-v3 — all tests for tier CRUD and MC framework are net-new _(QA)_
- Edge cases flagged: concurrent serialNumber assignment, @Lockable for concurrent approvals, one-DRAFT-per-ACTIVE enforcement, engineConfig round-trip fidelity _(QA)_
- Business Test Gen (Phase 8b) complete: 141 business test cases (84 UT + 45 IT + 12 compliance) across 7 sections. Full traceability: 52/52 ACs, 89/89 QA scenarios, 16/16 designer interface methods, 7/7 ADRs, 8/8 risks, 8 guardrail areas. 7 coverage gaps documented (all deferred or SDET-addressable, no blockers). Artifact: 04b-business-tests.md _(Business Test Gen)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._

### Rework #1 — Minimize deviation from production patterns (2026-04-13)
**Trigger**: User feedback — ACTIVITY_BASED enum rename and conversion logic is unnecessary deviation from emf-parent codebase.
**Decision**: Use production enum values as-is (CUMULATIVE_PURCHASES, CURRENT_POINTS, etc.). No renaming, no conversion in TierChangeApplier for criteriaType.
**Scope**: Phases 7-12 artifacts + Java source files (CriteriaType.java, TierChangeApplierTest.java).
**What changed**:
- CriteriaType enum: ACTIVITY_BASED → CUMULATIVE_PURCHASES (matches production)
- TierChangeApplier: no criteriaType conversion step needed (values pass through directly)
- BT-77: changed from conversion test to pass-through verification test
- Section 16 mapping table: now shows identity mapping (same values, no conversion)
- Per-tier threshold format KEPT (good UX improvement, user agreed)
- Downgrade UI/engineConfig split KEPT (helps UI team)
**What stayed the same**: Architecture, dual-storage, maker-checker, all other field structures.
**Impact**: Simpler code (less conversion logic), closer alignment with emf-parent patterns.

### Rework #2 — Lifecycle simplification + DRAFT-only deletion + no-reorder (2026-04-16)
**Trigger**: User clarification — PAUSED status not needed, deletion only for DRAFT tiers, reordering not allowed, tier retirement deferred.
**Decision**: Simplified status lifecycle. DELETED as terminal state for discarded DRAFTs (not STOPPED — different semantics from promotion pattern).
**Scope**: Phase 1 (BA+PRD) delta edits + forward cascade to downstream phases.
**What changed**:
- Status lifecycle: removed PAUSED, removed STOPPED, added DELETED (terminal, reachable from DRAFT only)
- US-4 (Deletion): DRAFT-only → DELETED. No MC flow. No member reassessment. 409 if not DRAFT.
- Explicit no-reorder business rule added. serialNumber immutable, 400 on change attempt.
- Tier retirement (stopping ACTIVE tiers) explicitly out of scope — future epic.
- US-2 (Tier Creation) stays IN SCOPE — this is the main goal.
**What stayed the same**: US-1 (Listing), US-2 (Creation), US-3 (Editing), US-5/6/7 (MC), dual-storage, architecture, all other field structures, communications (MongoDB hooks, no change).

### Rework #3 — Timezone alignment, rejection→DRAFT, remove ProgramSlab status (2026-04-16)
**Trigger**: User review — three corrections identified.
**Scope**: Model classes, MakerCheckerServiceImpl, TierChangeApplier, design artifacts.
**What changed**:
- **Timezone**: All date/time fields changed from `Instant` (UTC "Z") to `Date` with `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")` — matches UnifiedPromotion pattern. Produces offsets like "+05:30" instead of "Z". Affected: BasicDetails, TierMetadata, PendingChange, TierFacade, MakerCheckerServiceImpl, all tests.
- **Rejection→DRAFT**: MC rejection now reverts entity to DRAFT (promotion pattern). MakerCheckerServiceImpl wired with ChangeApplier registry. `reject()` calls `applier.revert()`. TierChangeApplier.revert() sets tier status back to DRAFT. Refactored to full constructor injection (Spring best practice).
- **ProgramSlab status column REMOVED**: No SQL changes needed. SQL only contains ACTIVE tiers (synced via Thrift). No ACTIVE tier can be deleted. SlabInfo Thrift has no status field. Removed from: 03-designer.md Section 7, 01-architect.md Section 4.3, blocker-decisions.md HIGH #2, 01b-migrator.md (M-1, M-2). Deferred to future tier retirement epic.
- **GUARDRAILS note**: G-01 originally said "use Instant not Date" — OVERRIDDEN to match existing codebase pattern (promotions use Date + @JsonFormat). Consistency with existing patterns takes priority over Java modernity preference.
**What stayed the same**: State machine (already had REJECT→DRAFT), APIs, architecture, all other field structures.
