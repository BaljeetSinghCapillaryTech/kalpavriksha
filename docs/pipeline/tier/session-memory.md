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
- Maker-Checker: Approval workflow. Uses Baljeet's generic `makechecker/` package (ApprovableEntity, ApprovableEntityHandler, MakerCheckerService<T>). Previously existed for UnifiedPromotion only. Tiers now integrate via TierApprovalHandler. _(BA)_

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
- Maker-checker framework migrated to Baljeet's generic `makechecker/` package: tiers plug into it via ApprovableEntityHandler<UnifiedTierConfig>, later benefits/change-log/simulation will too via same pattern. No custom makerchecker/ package (17 files deleted). _(BA — Q1, MIGRATION)_
- ~~Tier deletion is soft-delete via status field. Add `status` column to `program_slabs`.~~ SUPERSEDED by Rework #3: No SQL changes needed. MongoDB owns lifecycle. SQL only contains ACTIVE tiers. _(BA — Q2, superseded Rework #3)_
- ~~Status field is a SCHEMA CHANGE.~~ SUPERSEDED by Rework #3: ProgramSlab status column, findActiveByProgram(), and Flyway migration all removed from scope. Deferred to future tier retirement epic. _(BA — Q2, superseded Rework #3)_
- DUAL-STORAGE PATTERN: MongoDB for draft/pending tier configs, SQL for live tiers. Follows the exact same pattern as UnifiedPromotion in intouch-api-v3. Create/Edit saves to MongoDB. Maker-checker approval triggers sync to SQL (ProgramSlab + strategy configs). Listing API reads from MongoDB (all states) + SQL (live state). _(BA — Q3)_
- MongoDB tier document must use UI field names (Eligibility Criteria, Membership Duration, Upgrade Schedule, Downgrade Schedule, etc.) because AI simulation mode (E1-US6) will reference them later. _(BA — Q3)_
- VERIFIED PATTERN: UnifiedPromotion uses @Document(collection="unified_promotions"), PromotionStatus enum (DRAFT/PENDING_APPROVAL/ACTIVE/PAUSED/STOPPED/etc.), EntityOrchestrator with Transformer pattern to sync MongoDB->SQL on approval. EmfMongoDataSourceManager for sharded MongoDB access. _(BA — Q3)_
- Tier config status lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE. DRAFT -> DELETED (terminal, soft-delete). No PAUSED, no STOPPED, no RESUME status for tiers. Only DRAFT tiers can be deleted. Tier retirement (stopping ACTIVE tiers) deferred to future epic. _(BA — Q2+Q3, updated Rework #2)_
- Tier reordering NOT supported. serialNumber is immutable and auto-assigned. Any attempt to change serialNumber returns 400. _(Rework #2)_
- Tier deletion is DRAFT-only: DELETE /v3/tiers/{tierId} → sets status to DELETED. Returns 409 if not DRAFT. No MC flow needed (DRAFT is pre-approval). No member reassessment (DRAFT tiers have no members). _(Rework #2)_
- Member counts in tier listing: cached approach (option c). customer_enrollment table has current_slab_id but no GROUP BY count query exists. Table is hot (millions of evaluations/day). Use a periodic summary (refreshed every 5-15 min) stored in MongoDB tier doc or a small stats table. GET /tiers response includes cached counts. _(BA — Q4)_
- Maker-checker: FULL GENERIC FRAMEWORK (option a). ~~Build PendingChange entity/service, MakerCheckerService interface (submit/approve/reject), domain-specific ChangeApplier strategy.~~ SUPERSEDED by Rework #3.5: Use Baljeet's makechecker/ package with ApprovableEntity contract, ApprovableEntityHandler<T> strategy interface, MakerCheckerService<T extends ApprovableEntity>. Tiers = first consumer via TierApprovalHandler. Benefits, subscriptions, other entities plug in later. _(BA — Q5, MIGRATION)_
- Generic MC framework components (Baljeet's makechecker/ package): ApprovableEntity interface (entityType, status, timestamps), MakerCheckerService<T extends ApprovableEntity> (submit/approve/reject/list), ApprovableEntityHandler<T> strategy interface (per entity type — TierApprovalHandler implements it for UnifiedTierConfig). Change snapshots stored as part of entity state. _(BA — Q5, MIGRATION)_
- Tier editing: VERSIONED EDITS (option a, same as unified promotions). Editing an ACTIVE tier creates a new DRAFT MongoDB doc with parentId -> ACTIVE doc. ACTIVE stays live until DRAFT approved. On approval: new doc -> ACTIVE, old doc -> SNAPSHOT. Full rollback capability. Consistent with existing UnifiedPromotion.parentId pattern. _(BA — Q6)_
- Version lifecycle: CREATE -> DRAFT. SUBMIT -> PENDING_APPROVAL. APPROVE -> ACTIVE (old -> SNAPSHOT). REJECT -> back to DRAFT (promotion pattern, via TierApprovalHandler.revert() called by MakerCheckerService). EDIT ACTIVE -> new DRAFT with parentId. _(BA — Q6, updated Rework #3, MIGRATION)_
- API hosting: intouch-api-v3 serves tier CRUD REST APIs + MongoDB draft storage + maker-checker. On approval, syncs to emf-parent via Thrift (same as unified promotions). emf-parent owns core business logic, JPA entities, strategy configs. _(BA — Q7)_
- Call chain on approval: intouch-api-v3 REST -> TierFacade.handleApproval() -> MakerCheckerService<UnifiedTierConfig>.approve() -> TierApprovalHandler.postApprove() -> Thrift call -> emf-parent PointsEngineRuleService.createSlabAndUpdateStrategies() -> SQL write. _(BA — Q7, MIGRATION)_
- Exception types: InvalidInputException(400), NotFoundException(404), ConflictException(409), EMFThriftException(500) — all caught by TargetGroupErrorAdvice @ControllerAdvice. Never use IllegalArgumentException/IllegalStateException in REST-facing code. TierApprovalHandler and TierFacade throw these standard exceptions. _(Developer — Rework #4, MIGRATION)_
- Two-layer validation: Jakarta annotations on DTOs (field-level) + dedicated validator classes with error codes (9001-9009) + @Service business-rule validators (need DB access). Controllers are try-catch-free. _(Developer — Rework #4)_
- Error code range 9001-9009 for tier validation (aligned with api/prototype). Range 9010-9019 reserved for maker-checker. _(Developer — Rework #4)_
- Maker-checker: Tiers ALWAYS use maker-checker (no toggle). Create -> DRAFT, Submit -> PENDING_APPROVAL, Approve -> ACTIVE. No MC-disabled path for tiers. Integrated via Baljeet's generic makechecker/ package + TierApprovalHandler. _(BA — Q8, MIGRATION — Rework #3.5)_
- MIGRATION DECISION (Rework #3.5): Delete custom makerchecker/ package (17 files). Adopt Baljeet's generic makechecker/ framework (ApprovableEntity, ApprovableEntityHandler, MakerCheckerService<T>). Tiers are first consumer; benefits/subscriptions follow same pattern. Zero API changes; internal refactor only. _(2026-04-16)_

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
- P-2: CSV-per-slab pattern is pervasive. Every strategy property uses comma-separated values (position N = slab N). Creating a new slab requires extending EVERY strategy CSV. Handled by existing createSlabAndUpdateStrategies Thrift method + PointsEngineRuleService logic at line 3821. TierApprovalHandler.publish() must pass correct strategy list. _(Phase 5, MIGRATION)_
- P-3: upgrade section confirmed. current_value_type=CUMULATIVE_PURCHASES, threshold_value as array, secondary_criteria_enabled=false. Matches our model. _(Phase 5)_
- P-4: downgrade section has new fields: isFixedTypeWithoutYear (bool), renewalWindowType ("FIXED_DATE_BASED" -- different naming from PeriodType enum). condition="SLAB_UPGRADE" used as condition name. All must be preserved in MongoDB doc. _(Phase 5)_
- P-5: isAdvanceSetting (bool -- UI rendering hint) and addDefaultCommunication (bool -- auto-create notification templates) -- new flags not in BA. Store in MongoDB doc. _(Phase 5)_
- P-6: updatedViaNewUI flag on SlabInfo and StrategyInfo. New tier APIs must set updatedViaNewUI=true on all strategies they create/modify. _(Phase 5)_

## TierApprovalHandler Conversion Design (Phase 5 Deep Dive, MIGRATION — Rework #3.5)
- Strategy entity (SQL: strategies table): id, orgId, programId, name, description, strategyTypeId, propertyValues (JSON string), owner, createdOn _(Phase 5)_
- StrategyType IDs: 1=POINT_ALLOCATION, 2=SLAB_UPGRADE, 3=POINT_EXPIRY, 4=POINT_REDEMPTION_THRESHOLD, 5=SLAB_DOWNGRADE, 6=POINT_RETURN, 7=EXPIRY_REMINDER, 8=TRACKER, 9=POINT_EXPIRY_EXTENSION _(Phase 5)_
- CREATE new slab: Call createOrUpdateSlab(SlabInfo) via Thrift. Engine auto-extends all allocation/expiry CSV values with appended "0". TierApprovalHandler.publish() does NOT send strategy list for basic creation. _(Phase 5, MIGRATION)_
- UPDATE slab config: Call createSlabAndUpdateStrategies(SlabInfo, list<StrategyInfo>). TierApprovalHandler.publish() converts MongoDB config -> StrategyInfo list. _(Phase 5, MIGRATION)_
- Conversion: eligibility (TierEligibilityConfig) -> StrategyType 2 (SLAB_UPGRADE) propertyValues JSON {current_value_type, threshold_values CSV, expression_relation, slab_upgrade_mode, tracker_id, tracker_condition_id} _(Phase 5, updated Phase D)_
- Conversion: downgrade (TierDowngradeConfig) -> StrategyType 5 (SLAB_DOWNGRADE) propertyValues JSON = full TierConfiguration JSON {is_active, slabs[], dailyDowngradeEnabled, retainPoints, isDowngradeOnReturnEnabled, renewalConfirmation, reminders} _(Phase 5, updated Phase D)_
- Points strategies (allocation/redemption/expiry) NOT managed by tier CRUD. On new slab, engine auto-extends. On edit, existing values preserved. _(Phase 5)_
- Slab upgrade strategy property format: {current_value_type: "CUMULATIVE_PURCHASES", threshold_values: "2000,5000,12000"} -- CSV has N-1 values for N slabs (base slab has no threshold) _(Phase 5)_
- createOrUpdateSlab internally calls updateStrategiesForNewSlab which iterates all POINT_ALLOCATION and POINT_EXPIRY strategies and appends default values for the new slab position _(Phase 5)_
- SAGA FLOW: TierApprovalHandler implements preApprove() (validate), publish() (call Thrift), postApprove() (save MongoDB), onPublishFailure() (log + rethrow). All methods called by MakerCheckerService<UnifiedTierConfig>. Atomic Thrift: createSlabAndUpdateStrategies with ONLY SLAB_UPGRADE and SLAB_DOWNGRADE strategies. Engine auto-handles allocation/expiry CSV extension. _(Phase 5 validation, MIGRATION)_
- SAGA RISK: updateStrategiesForNewSlab only extends POINT_ALLOCATION(1) and POINT_EXPIRY(3). Does NOT extend POINT_REDEMPTION_THRESHOLD(4). Redemption CSVs may be mismatched after new slab creation. Existing engine may handle this gracefully or it may be a latent bug. Low risk for now -- redemption strategies typically use SLAB_INDEPENDENT type. _(Phase 5 validation)_

## Constraints
- Scope: Tier CRUD (List, Create, Edit, Delete) + integration with Baljeet's generic Maker-Checker framework (via ApprovableEntityHandler). NOT custom MC framework build. NOT change log, NOT simulation mode. _(BA — Q1, MIGRATION)_
- Scope limited to "Tiers CRUD" — subset of the full Tiers & Benefits BRD (Epic E1 primarily) _(Phase 0)_
- Tech stack: Java, Spring, Thrift, MySQL, MongoDB, Flyway, JUnit 4, Mockito _(Phase 0)_
- Four repos involved: emf-parent (entities/strategies), intouch-api-v3 (REST/maker-checker), peb (tier downgrade), Thrift (IDL definitions) _(Phase 0)_
- UI: Figma designs (AMJ - Loyalty Revamp, node 1508:20810) + 8 v0.app screenshots. 10 Figma frames downloaded to UI/figma-tiers/. _(Phase 0, updated 2026-04-14)_
- 7 ADRs documented: ADR-01 (dual-storage), ADR-02 (generic MC), ADR-03 (expand-then-contract), ADR-04 (versioned edits), ADR-05 (existing Thrift), ADR-06 (new programs only), ADR-07 (atomic Thrift call) _(Architect)_
- 3-layer implementation plan (updated post-migration): L1 TierApprovalHandler (ApprovableEntityHandler<UnifiedTierConfig> impl, SAGA pattern), L2 Tier CRUD (TierFacade, TierReviewController, TierRepository), L3 emf-parent changes (Thrift integration). Cache + monitoring via TierServiceImpl. _(Architect, MIGRATION)_
- API handoff v1.3: 13 endpoints total (4 tier CRUD + 1 MC submit + 2 MC approve/reject + 1 MC list pending + 1 tier detail + 1 MC config + 1 change detail + 2 tier-settings GET/PUT). All MC endpoints delegate to MakerCheckerService<UnifiedTierConfig> and TierApprovalHandler. No PAUSED status. Tier reorder not supported (serialNumber immutable). Idempotency-Key on POST /v3/tiers. _(Phase 7.5, updated Figma review + MIGRATION)_
- Production payload validation (program 977): 5 missing engineConfig fields discovered. Added: slabUpgradeMode (program-level, from upgrade.slab_upgrade_mode), downgradeEngineConfig.isActive (from downgrade.is_active), downgradeEngineConfig.conditionAlways (from downgrade.condition_always), downgradeEngineConfig.conditionValues (purchase/numVisits/points/trackerCount), downgradeEngineConfig.renewalOrderString. Full legacy-to-new mapping table added to api-handoff Section 16. _(Phase 7.5 — production validation)_
- criteriaType: new API uses SAME production enum values (CUMULATIVE_PURCHASES, CURRENT_POINTS, etc.). No conversion needed in TierApprovalHandler -- values pass through directly. Threshold format differs: production uses program-wide CSV array (N-1 values), our API uses per-tier individual values -- TierApprovalHandler joins/splits during sync. _(Phase 7.5, updated Phase 7-rework, MIGRATION)_
- MongoDB document schema: UnifiedTierConfig implements ApprovableEntity with 9 top-level sections (basicDetails, eligibility, validity, downgrade, nudges, benefitIds, memberStats, engineConfig, metadata) — field names engine-aligned per Phase D rework. Old names: eligibilityCriteria→eligibility, renewalConfig→validity, downgradeConfig→downgrade, nudges added. Model classes: TierEligibilityConfig, TierValidityConfig, TierDowngradeConfig, TierNudgesConfig, TierCondition, TierRenewalConfig. All use String types for enum-like fields (kpiType, upgradeType, target, periodType) matching prototype pattern. Status field (status: DRAFT/PENDING_APPROVAL/ACTIVE/SNAPSHOT) managed by ApprovableEntity contract. _(Architect, updated Phase D, MIGRATION)_
- ApprovableEntity generic contract (Baljeet's makechecker/): status (DRAFT/PENDING_APPROVAL/ACTIVE/SNAPSHOT), timestamps, userId fields. UnifiedTierConfig implements ApprovableEntity. Payload stored as entity state, not separate doc. _(Architect, MIGRATION)_
- Impact analysis: blast radius SMALL (2 modified in emf-parent, 0 in peb/Thrift). Full backward compatibility. _(Analyst)_
- GUARDRAILS attention: ~~G-01 (use Instant not Date)~~ OVERRIDDEN Rework #3 — use Date + @JsonFormat(XXX) to match promotion pattern, G-06.1 (add idempotency key for POST /tiers), G-07.3 (cron job tenant context) _(Analyst, updated Rework #3)_
- 8 risks catalogued: R1 CSV off-by-one (HIGH), R2 downgrade race (MEDIUM, mitigated), R3 strategy ID collision (MEDIUM), R4 member count index (MEDIUM), R5 timezone (MEDIUM), R6 idempotency (LOW), R7 cron tenant (LOW), R8 MC self-approval (LOW, product decision) _(Analyst)_
- Security: COMPLIANT with G-03. Auth via token, parameterized queries, no PII exposure. One product question: should MC prevent self-approval? _(Analyst)_
- Performance: Tier listing <200ms. Member count cache needs INDEX on customer_enrollment(org_id, program_id, current_slab_id, is_active). Separate Flyway migration. _(Analyst)_

## Risks & Concerns
- jdtls LSP: installed (v1.57.0, Java 23), running via /tmp/emf-parent symlink. Patched find_daemon_for_cwd for symlink resolution. _(Phase 0)_ -- Status: mitigated
- Registry repo has full decomposition on `raidlc/rtest123/epic-division` branch. _(Phase 0)_ -- Status: mitigated
- tier-category consumes Baljeet's makechecker/ package (generic ApprovableEntity framework) and audit-trail-framework (owner: anuj). makechecker/ status: available. audit-trail status: designed (not built yet). Will need mocks for audit-trail during development. _(Phase 0, MIGRATION)_ -- Status: MITIGATED (makechecker available), open (audit-trail)
- BLOCKER C-1: RESOLVED in Migration. Thrift methods ALREADY EXIST in pointsengine_rules.thrift: createSlabAndUpdateStrategies(programId, orgId, SlabInfo, list<StrategyInfo>, ...), getAllSlabs(programId, orgId, ...), createOrUpdateSlab(SlabInfo, orgId, ...). TierApprovalHandler.postApprove() calls these via PointsEngineRulesThriftService wrapper. NO new Thrift IDL change needed. _(Phase 5, MIGRATION)_ -- Status: RESOLVED
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
- [x] resolved: MC notification -- Baljeet's MakerCheckerService handles lifecycle notifications. TierApprovalHandler can register callbacks via NotificationHandler interface if needed. _(Phase 4 — GQ-5, MIGRATION)_
- [x] resolved: Benefits linkage -- store benefitIds only on tier doc. UI fetches benefit details separately. _(Phase 4 — GQ-4 override)_
- [x] resolved: No pagination for tier listing. Full list returned. Max 50 tiers validation cap. _(Phase 4 — GQ-1)_
- [x] resolved: NO bootstrap sync for existing programs. New tier CRUD is for NEW programs only. Old programs keep current system. _(Phase 4 — GQ-2 override)_
- [x] resolved: Versioned edit flow confirmed as Flow A. ACTIVE stays live until DRAFT approved. On approval: old->SNAPSHOT, new->ACTIVE. Zero downtime. _(Phase 4 — GQ-3)_
- [x] resolved: Change snapshot storage -- ApprovableEntity contract stores state in UnifiedTierConfig itself (full snapshot, not diff). No separate PendingChange collection needed. _(Phase 4 — GQ-6, MIGRATION)_
- [x] resolved: KPI "Scheduled" replaced with "Pending Approval". No goLiveDate concept for now. _(Phase 4 — C-5)_

## QA Findings (Phase 8)
- 89 test scenarios covering 52/52 acceptance criteria, 7/7 ADRs, 8 risks, 6 guardrail areas _(QA)_
- Most critical gap: No test infrastructure for MongoDB + Thrift integration tests in intouch-api-v3. SDET must establish embedded MongoDB + Thrift mock. _(QA)_
- ~45 existing test files in emf-parent + peb need regression runs after Flyway migration (ADR-03 expand-then-contract) _(QA)_
- 0 existing tier integration tests in intouch-api-v3 — all tests for tier CRUD and MC integration with Baljeet's framework are net-new _(QA, MIGRATION)_
- Edge cases flagged: concurrent serialNumber assignment, @Lockable for concurrent approvals, one-DRAFT-per-ACTIVE enforcement, engineConfig round-trip fidelity _(QA)_
- Business Test Gen (Phase 8b) complete: 141 business test cases (84 UT + 45 IT + 12 compliance) across 7 sections. Full traceability: 52/52 ACs, 89/89 QA scenarios, 16/16 designer interface methods, 7/7 ADRs, 8/8 risks, 8 guardrail areas. 7 coverage gaps documented (all deferred or SDET-addressable, no blockers). Artifact: 04b-business-tests.md _(Business Test Gen)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._

### Rework #1 — Minimize deviation from production patterns (2026-04-13)
**Trigger**: User feedback — ACTIVITY_BASED enum rename and conversion logic is unnecessary deviation from emf-parent codebase.
**Decision**: Use production enum values as-is (CUMULATIVE_PURCHASES, CURRENT_POINTS, etc.). No renaming, no conversion in TierApprovalHandler for criteriaType.
**Scope**: Phases 7-12 artifacts + Java source files (CriteriaType.java, TierApprovalHandlerTest.java).
**What changed**:
- CriteriaType enum: ACTIVITY_BASED → CUMULATIVE_PURCHASES (matches production)
- TierApprovalHandler: no criteriaType conversion step needed (values pass through directly)
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

### Rework #4 — Production-quality exception handling & validation standardization (2026-04-16)
**Trigger**: User review — code used IllegalArgumentException/IllegalStateException instead of codebase exception types, controllers had manual try-catch, no validator classes, no error codes.
**Scope**: All tier + maker-checker production and test files in intouch-api-v3.
**What changed**:
- **Exception types**: All `IllegalArgumentException` → `NotFoundException` (404) or `InvalidInputException` (400). All `IllegalStateException` → `ConflictException` (409, new class) or `InvalidInputException`. All `RuntimeException("Thrift...")` → `EMFThriftException`.
- **New class: ConflictException** — follows same pattern as InvalidInputException/NotFoundException. Added to TargetGroupErrorAdvice @ControllerAdvice mapping CONFLICT (409).
- **Controllers cleaned**: Removed ALL try-catch from TierController and TierReviewController. Clean delegation to facades. @ControllerAdvice handles all HTTP mapping.
- **Two-layer validation**: Jakarta annotations (@NotBlank, @Size, @Pattern) on BasicDetails DTO for field-level. New TierCreateRequestValidator + TierUpdateRequestValidator with error codes 9001-9009. TierValidationService slimmed to business-rule-only methods (name uniqueness, serial number, tier cap).
- **Error codes**: 9001=name required, 9002=name too long, 9003=desc too long, 9004=invalid color hex, 9005=end before start, 9006=programId required, 9007=invalid kpiType, 9008=negative threshold, 9009=invalid upgradeType.
- **Handler refactored**: TierApprovalHandler throws standard exceptions (no try-catch). SAGA methods (preApprove, publish, postApprove, onPublishFailure) propagate exceptions cleanly.
- **Test files updated**: TierValidationServiceTest, TierFacadeTest, TierApprovalHandlerTest — all assertions changed to match new exception types.
- **GUARDRAILS updated**: New G-13 (Exception Handling & Error Codes) with 4 sub-rules. Designer, Developer, Reviewer skills updated.
**What stayed the same**: Business logic, architecture, state machine, all other code.
**Impact**: Code now follows same exception/validation pattern as all other controllers in intouch-api-v3. 56 tests pass.

### Rework #3.5 — Migration to Baljeet's generic makechecker/ package (2026-04-16)
**Trigger**: Package availability — Baljeet completed generic makechecker/ framework. Custom 17-file makerchecker/ package deprecated.
**Decision**: Delete custom makerchecker/ package entirely. Integrate tiers into Baljeet's makechecker/ via ApprovableEntityHandler<UnifiedTierConfig>.
**Scope**: All makerchecker/ files + all references in tier CRUD code.
**What changed**:
- **Deleted**: Custom `intouch-api-v3/src/.../makerchecker/` directory (17 files): MakerCheckerService, MakerCheckerServiceImpl, MakerCheckerFacade, MakerCheckerController, TierChangeApplier, ChangeApplier, PendingChange, MakerCheckerConfig, isMakerCheckerEnabled(), etc.
- **New**: `TierApprovalHandler implements ApprovableEntityHandler<UnifiedTierConfig>` — single class with preApprove(), publish(), postApprove(), onPublishFailure(), revert() methods.
- **New**: `TierFacade.submitForApproval(tierId) → MakerCheckerService<UnifiedTierConfig>.submit()` and `TierFacade.handleApproval(tierId, approved) → MakerCheckerService.approve()`.
- **New**: `TierReviewController` (replaces MakerCheckerController) delegates to TierFacade.
- **SAGA pattern**: preApprove() validates, publish() calls Thrift (createSlabAndUpdateStrategies), postApprove() saves MongoDB, onPublishFailure() logs + rethrows.
- **Status always MC**: No isMakerCheckerEnabled toggle. Tiers always follow DRAFT→PENDING_APPROVAL→ACTIVE→SNAPSHOT lifecycle.
- **No PendingChange collection**: Change metadata stored in UnifiedTierConfig itself (requestedBy, reviewedBy, approvalTimestamp, etc., per ApprovableEntity contract).
- **ApprovableEntity contract**: Implemented by UnifiedTierConfig. Framework handles status, timestamps, user tracking.
**What stayed the same**: APIs, business logic, dual-storage pattern, MongoDB schema, Thrift integration, all other code.
**Impact**: Cleaner codebase (eliminates custom framework), instant extensibility for future entities (benefits, subscriptions), aligns with registry design.

### Rework #3 — Timezone alignment, rejection→DRAFT, remove ProgramSlab status (2026-04-16)
**Trigger**: User review — three corrections identified.
**Scope**: Model classes, MakerCheckerServiceImpl, TierApprovalHandler, design artifacts.
**What changed**:
- **Timezone**: All date/time fields changed from `Instant` (UTC "Z") to `Date` with `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")` — matches UnifiedPromotion pattern. Produces offsets like "+05:30" instead of "Z". Affected: BasicDetails, TierMetadata, UnifiedTierConfig, TierFacade, MakerCheckerService, all tests.
- **Rejection→DRAFT**: MC rejection now reverts entity to DRAFT (promotion pattern). MakerCheckerService wired with ApprovableEntityHandler registry. `reject()` calls `handler.revert()`. TierApprovalHandler.revert() sets tier status back to DRAFT. Refactored to full constructor injection (Spring best practice).
- **ProgramSlab status column REMOVED**: No SQL changes needed. SQL only contains ACTIVE tiers (synced via Thrift). No ACTIVE tier can be deleted. SlabInfo Thrift has no status field. Removed from: 03-designer.md Section 7, 01-architect.md Section 4.3, blocker-decisions.md HIGH #2, 01b-migrator.md (M-1, M-2). Deferred to future tier retirement epic.
- **GUARDRAILS note**: G-01 originally said "use Instant not Date" — OVERRIDDEN to match existing codebase pattern (promotions use Date + @JsonFormat). Consistency with existing patterns takes priority over Java modernity preference.
**What stayed the same**: State machine (already had REJECT→DRAFT), APIs, architecture, all other field structures.

### Rework #5 — Unified read surface, dual write paths, schema cleanup (2026-04-17)
**Trigger**: User rework spec — 9 coordinated changes to make the new tier system coexist with legacy tiers via a unified read surface, while keeping MC scoped to new-UI writes.
**Scope**: BA, HLD, LLD, BTG, migrator, cross-repo-trace, api-handoff. Forward cascade to SDET, Developer, Reviewer pending.
**Scoping doc**: `docs/pipeline/tier/rework-5-scope.md` (full decision record with worked examples).

**Locked decisions (summary — full detail in rework-5-scope.md):**

- **C-1 / ADR-06 REVERSED**: New API serves ALL tiers (legacy + new-UI-origin). "New programs only" restriction dropped. Read-only SQL→DTO converter bridges legacy SQL tiers into the new API's response shape. No bootstrap migration.

- **Q-1b / Dual write paths**: Old UI continues legacy direct-SQL writes (no MC). New UI routes through Mongo DRAFT → MC → Thrift → SQL. MC scope is "any write from new UI", regardless of whether the tier was originally created via old UI.
  - **Name collisions** on concurrent create: 3-layer defense — app-level check at DRAFT creation, re-check at approval, SQL `UNIQUE(program_id, name)` constraint as final backstop.
  - **DRAFT creation timing**: only on Save Draft click in new UI. Never on view/open.

- **Q-2a / Stale-block at approval**: DRAFTs capture a `meta.basisSqlSnapshot` at creation. Approval re-reads current SQL and blocks approval if drift detected. Approver is told why; must cancel or recreate DRAFT.
  - Drift-detection granularity (full-tier vs changed-fields) deferred to Designer — recommended conservative (any drift blocks).
  
- **Q-2b / SNAPSHOT audit-only**: Mongo SNAPSHOT docs are the approval audit record, not current state. SNAPSHOT is never updated by legacy writes. History UI labels each SNAPSHOT with `approvedAt`/`approvedBy` and flags drift if legacy writes followed.

- **Q-3 / Hybrid reads**: "LIVE tiers" (typo fix from original "LIVE promotions"). LIVE state ALWAYS from SQL — never from Mongo. GET response shape is an envelope: `{live: {...from SQL}, pendingDraft: {...from Mongo} | null}`. List avoids N+1 via two DB queries + in-memory join.
  - **Mongo indexes** on `UnifiedTierConfig`: Index 1 `(orgId, programId, status)`, Index 2 `(orgId, programId, slabId)`. Index 2 upgraded to unique partial for Q-9 enforcement.

- **Q-7 / Schema cleanup**:
  - Drop `nudges` from `UnifiedTierConfig` (standalone `Nudges` entity with own endpoints is untouched — engine `notificationConfig` stays).
  - Drop `benefitIds` (tiers have no knowledge of benefits).
  - Drop `updatedViaNewUI` flag.
  - Drop `basicDetails.startDate` / `basicDetails.endDate` + UI Duration column. `validity.startDate/endDate` stays (different semantic).
  - Rename `unifiedTierId` → `tierUniqueId` (pure rename, format unchanged, e.g. `"ut-977-004"`).
  - Hoist `basicDetails` and `metadata` to root — no wrapper objects. All tier fields live at top level of `UnifiedTierConfig`.

- **SQL `program_slabs` audit columns**: ADD `updatedBy`, `approvedBy`, `approvedAt`. NOT adding `createdBy`. Flyway migration in Rework #5 set.

- **Q-8 / Rename `sqlSlabId` → `slabId`**: Mechanical rename. After Q-7d hoist, lives at root (was `metadata.sqlSlabId`). Null for DRAFT of new tiers; populated once SQL write completes.

- **Q-9 / Single active DRAFT per tier**: Scope = per tier (different tiers in same program can each have their own draft). Enforcement = both layers — app-level pre-insert check (friendly error) + Mongo partial unique index on `(orgId, programId, slabId)` filtered to `status IN [DRAFT, PENDING_APPROVAL]` (race backstop). Reuses Q-3c Index 2 fields.

- **Q-6 / `parentId`**: Stores parent's `slabId` (SQL `program_slabs.id`). Parent must be LIVE (DRAFTs can't be parents). Self-ref prevented; cycle prevention deferred to Designer.

**What stayed the same**: dual-storage pattern, Baljeet's makechecker/ framework, SAGA flow, Thrift `createSlabAndUpdateStrategies`, Strategy conversion, timezone handling.

**Impact**:
- HLD: ADR-06 flipped; new ADRs for stale-block, envelope response, SNAPSHOT-audit-only, dual write paths, new index design.
- LLD: `UnifiedTierConfig` schema flattened (wrappers removed). New `meta.basisSqlSnapshot` field. `TierApprovalHandler.preApprove` gains drift-check. New SQL→DTO converter for legacy tiers.
- Migrator: Flyway migration for 3 new audit columns; Mongo index creation scripts (2 indexes + 1 partial unique index).
- Tests: Suspect-link triage per ISTQB — add BTs for dual-path write, drift-block at approval, SNAPSHOT labeling, envelope GET, single-active-draft enforcement (both layers), parentId validation, name-collision 3-layer defense.
- API handoff: GET endpoints return envelope shape. New error codes for drift-block and single-active-draft.

**Deferred to Designer (noted in LLD when rework cascades)**:
- Drift-detection granularity (full-tier vs changed-fields).
- `parentId` cycle prevention algorithm.
