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
- Renewal contract (Rework #5 R4 B1a): `TierValidityConfig.renewal` is always an explicit block on the envelope. Only `criteriaType = "Same as eligibility"` is accepted on write; every other value is rejected with 400. Null/missing renewal is auto-filled to the B1a default on the write path before persistence. The engine has no storage slot for an explicit renewal rule, so the read path synthesizes the same default. `expressionRelation` and `conditions` are null/empty today; space is reserved for the future B2 (accept Custom) / B3 (full engine wiring) contracts without a breaking change. _(R5-R4-B1a)_
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
- R3 tierStartDate sourced exclusively from SQL `program_slabs.created_on`. No fallback, no derivation. Wire path: emf-parent `ProgramSlab.createdOn` → Thrift `SlabInfo.createdOn` (new optional i64 field, epoch millis) → intouch-api-v3 `SqlTierRow.createdOn` (Date) → `TierView.tierStartDate` (Date, `@JsonFormat` ISO-8601 `yyyy-MM-dd'T'HH:mm:ssXXX`). Backward compatible: legacy emf-parent servers that don't set the Thrift field surface null at every layer — null never becomes 1970-01-01 (transformer uses `SlabInfo.isSetCreatedOn()`, not a value check). Same extensibility pattern reserved for closing the Q-R1 Thrift gap (updatedBy/updatedAt) in a later rework. Thrift ifaces-pointsengine-rules bumped to 1.84-SNAPSHOT-nightly1 in both emf-parent and intouch-api-v3. _(R3)_
- Rework #8 — i18n key catalog mirror for tier validation: NEW `tier.properties` (`i18n/errors/tier.properties`) holds 35 active codes (9001..9037, 9007/9027 reserved gaps; 9031 folded into 9034). NEW `TierErrorKeys.java` constants class. ONE-line addition to `MessageResolverService.fileNameMap` registers `TIER → i18n.errors.tier`. All tier `InvalidInputException` throws migrate to key-only (`new InvalidInputException(TierErrorKeys.TIER_NAME_REQUIRED)`); the advice resolves key → code+message via `MessageResolverService`. Wire numeric codes (9001..9024) preserved — no client breakage. Bean-validation annotations (`@NotBlank`/`@Size`/`@Pattern`/`@PositiveOrZero`/`@NotNull`) added to `TierCreateRequest`, `TierUpdateRequest`, `TierEligibilityConfig` with `message=TIER.<KEY>` per plan §4.4. Validators inject `jakarta.validation.Validator` and explicitly call `.validate(req)` post-`treeToValue` (controllers stay raw `JsonNode` for pre-binding scans). REQ-58 (color length 9027) SKIPPED — defensive duplicate of `@Pattern`. REQ-63 (renewalLastMonths 9031) FOLDED into REQ-62 (9034) — wire field `renewalLastMonths` does not exist in `TierValidityConfig.java` (verified — zero hits in source); semantic equivalent is `computationWindowStartValue` when `renewalWindowType==FIXED_DATE_BASED`. Dynamic-context messages use Option 2 (static catalog message; field-name detail in structured logs only). _(Designer — Rework #8, 2026-04-27)_
- Rework #8 BTG — test strategy decisions: (1) UPDATE triage: 21 BTs (BT-190..BT-223 subset) have assertion text migrated from code/bracket-prefix text to key-only `ex.getMessage() == "TIER.<KEY>"` + round-trip `resolverService.getCode(key)` assertion. Wire codes unchanged. (2) Jackson-path BTs (BT-192, 197, 213, 218, 219) and success-path BTs (BT-206, 207, 209, 216) CONFIRMED — no change. (3) NEW BTs BT-224..BT-249 (24 net new) for REQ-57..REQ-68 gap-fill validations + catalog-integrity smoke tests. (4) BT-247 catalog-integrity test IN SCOPE now (D-33). (5) BT-249 is IT (advice end-to-end); all others are UT. (6) TierValidationAssert helper class recommended for `assertThrowsWithKey(executable, key, expectedCode)` — Phase 10 Developer creates it. _(Business Test Gen — Rework #8, 2026-04-27)_
- Rework #8 BTG — open questions: Q-#8-1 (REQ-58 color length 9027 SKIP — confirmed?), Q-#8-2 (REQ-63 renewalLastMonths FOLD — confirmed?), Q-#8-3 (dynamic-context Option 2 — confirmed?), Q-#8-4 (BT-247 catalog integrity — confirmed IN SCOPE), Q-#8-5 (REQ-57 case-insensitive DB scan before deploy in QA env). See `03-designer.md §R8.10` for full question context. _(Business Test Gen — Rework #8, 2026-04-27)_

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
- R5-R4 Renewal implementation = **B1a (accept-only `Same as eligibility`)**. Chosen over B2 (accept Custom with deferred engine wiring) and B3 (full engine wiring now). Rationale: the engine fires `RenewSlabInstruction` implicitly on slab upgrade (`UpgradeSlabActionImpl:815`, emf-parent); `RenewConditionDto` is audit-only (reconstructed from `slabConfig.getConditions()` + `periodConfig.getType()`); there is no engine field in which to persist an explicit renewal rule. Locking the API to the one shape the engine semantically supports keeps the contract honest today and preserves space for B2/B3 additively. Validator rejects all other `criteriaType` values with 400. _(R5-R4-B1a, 2026-04-21)_
- R5-R4 Option X — SQL-asymmetry prevention: `TierRenewalNormalizer` fills the B1a default on all three TierFacade write paths (create, versioned draft from active, update-in-place) immediately before `tierRepository.save()`. `TierStrategyTransformer.extractValidityForSlab` synthesizes the same default on the read path. Result: DRAFT (from Mongo) and LIVE (from engine JSON) surface identical renewal values; `TierDriftChecker`'s whole-object `Objects.equals(basis.getValidity(), current.getValidity())` yields no phantom diffs. This mirrors the fix pattern used when the prior `schedule` field was dropped (commit 86e37e5ea). Write-side `applySlabValidityDelta` still ignores `cfg.renewal` — correct, because engine JSON has no storage slot. _(R5-R4-B1a, 2026-04-21)_
- R5-R4 **supersedes** Phase 2AB Decision Q-V3 ("defer renewal to Phase 2C"). Renewal is no longer deferred — B1a is the shipping contract. `rework-5-phase-2-decisions.md` Q-V3 body and the Q-V6 Scope note are annotated in place with supersession pointers. _(R5-R4-B1a, 2026-04-21)_

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

### Rework #5 Phase 2AB — Atomic publish (split-brain closure) (2026-04-20)
**Trigger**: Code audit of `TierApprovalHandler.publish()` revealed the SAGA was executing two engine round-trips (`createOrUpdateSlab` → separate strategy update). Failure of the second call left `program_slabs` written while SLAB_UPGRADE CSV / SLAB_DOWNGRADE JSON were not — split-brain, no safe compensation.
**Scope**: LLD (Designer) + HLD ADR-07 + transformer + handler. No BA / QA / BTG changes (behavioural contract unchanged). Forward cascade: Reviewer re-verify on next run.

**Commits (intouch-api-v3, branch `raidlc/ai_tier`)**:
- `2a616290f` — Step 12a: Thrift wrapper method `createSlabAndUpdateStrategies(slabInfo, List<StrategyInfo>, programId, orgId, userId, now)` added to `PointsEngineRulesThriftService` (lines 451–486). Translates `PointsEngineRuleServiceException` → `EMFThriftException` at the boundary.
- `d5c226c6a` — Step 12b-i: Pure-function transformer helpers in `TierStrategyTransformer`:
  - `applySlabUpgradeDeltaJson(propertyValuesJson, slabIndex, newThreshold, isAppend)` (lines 120–134): wraps CSV delta in a full JsonObject, preserving `current_value_type` / `expression_relation` / other program-level keys.
  - `findStrategyByType(strategies, type)` (lines 812–828): public counterpart to private `findSingleStrategy`; throws `IllegalStateException` on duplicate or missing strategy (data-corruption signal).
- `59b4ae423` — Step 12b-ii: `TierApprovalHandler.publish()` rewritten to atomic flow (lines 226–287) + extracted helpers `resolveSlabIdAndDiscriminate` (306–321), `applyUpgradeDelta` (332–362), `applyDowngradeDelta` (372–381).

**Atomic publish flow** (replaces two-step):
1. `buildSlabInfo(entity)`.
2. `resolveSlabIdAndDiscriminate(entity, slabInfo)` → CREATE vs UPDATE (slabId set / parent resolves).
3. `thriftService.getAllConfiguredStrategies(programId, orgId)` — fresh; **intentionally not cached** (Q-R4).
4. `findStrategyByType(SLAB_UPGRADE)` + `findStrategyByType(SLAB_DOWNGRADE)`; throw if either missing or duplicated.
5. `upgrade.deepCopy()` + `downgrade.deepCopy()` — defensive (Thrift clients may cache).
6. `applyUpgradeDelta` — skip for slab 1; CREATE of non-first slab REQUIRES `eligibility.threshold` else `IllegalStateException`; UPDATE is null-safe.
7. `applyDowngradeDelta` — null-safe mutate on `TierConfiguration.slabs[]` keyed by `slabNumber`.
8. `thriftService.createSlabAndUpdateStrategies(slabInfo, [upgradeCopy, downgradeCopy], programId, orgId, userId, now)` — **single engine transaction**.

**Locked design decisions (Q-P1…Q-P7)**: see HLD §7.5.4 for the table. Key points:
- **Q-P2**: duplicate program-level strategies surface as `IllegalStateException` (not silently picked).
- **Q-P3**: deep-copy `StrategyInfo` before mutating — Thrift client caches are allowed to exist.
- **Q-P4b**: CREATE of non-first slab without `eligibility.threshold` is rejected (CSV semantics).
- **Q-P5**: CSV N-1 semantics — slab 1 has no inbound threshold; upgrade delta is skipped.
- **Q-P7**: `userId` for audit columns: parsed from `doc.meta.approvedBy` with fallback to `doc.updatedBy`; hard-coded `0` placeholder pending user-id resolver — tracked as TODO.

**Invariants now held unconditionally** (previously could be violated on second-call failure):
- `program_slabs` row present ⟺ SLAB_UPGRADE CSV entry at position `serialNumber - 2`.
- `program_slabs` row present ⟺ SLAB_DOWNGRADE JSON entry for `slabNumber`.
- Non-owned program-level keys (`current_value_type`, `expression_relation`, reminders, comms) preserved through read-modify-write.

**Verification**:
- intouch-api-v3: 198/198 tests GREEN under Java 17 (`17.0.17-amzn` via sdkman). Java 8 rejected by `--release`; Java 23 breaks Lombok; Java 17 verified clean.
- emf-parent: no Phase 2AB code changes. Pre-existing aspectj-maven-plugin:1.7 / `com.sun:tools:jar` issue under Java 9+ is infra, not a regression; Java 8 build passes.
- Thrift IDL `createSlabAndUpdateStrategies` already existed in Points Engine — no IDL change. ADR-05 (no Thrift IDL change) remains COMPLIANT.

**Impact**:
- **HLD**: ADR-07 rewritten from generic "atomic call" to "read-modify-write + single atomic Thrift" (with alternatives table and verified execution order). New §7.5 "Phase 2AB — Complete Atomic Publish Flow" — end-to-end sequence diagram, CREATE/UPDATE discriminator flowchart, invariants table, Q-P1…Q-P7 decision record.
- **LLD**: `TierApprovalHandler.publish()` pseudocode expanded to match implementation (helpers `resolveSlabIdAndDiscriminate`, `applyUpgradeDelta`, `applyDowngradeDelta` + their contracts). Note added on deep-copy discipline and duplicate-strategy throw.
- **Transformer (LLD)**: Two new public helpers documented — `applySlabUpgradeDeltaJson` and `findStrategyByType`.
- **Blueprint**: ADR-07 flipped to COMPLIANT. Stats bar refreshed (198/198 tests GREEN, +3 Phase 2AB commits).

**What stayed the same**: SAGA shape (preApprove / publish / postApprove), drift check, name re-check, SNAPSHOT audit-only semantics, dual write paths, envelope response, `getAllConfiguredStrategies` not cached.

**Carryover TODO**:
- **Q-P7 resolver**: `parseUserId(entity)` currently defaults to `0` when `approvedBy`/`updatedBy` cannot be parsed as int. Needs a real user-id resolver (string-user-id → numeric) before production. Tracked in handler comment.

---

### Rework #6 — Contract rename + envelope flatten + program-level advancedSettings (2026-04-22, Phase 1 BA REWORK COMPLETE — awaiting Phase 2 continue)
**Trigger**: User rework spec consolidating semantic naming, UI-aligned read envelope, sentinel hygiene, and a new program-level advanced-settings API.

**Status (2026-04-22)**: All Q-locks for 6a closed (Q1-Q26 + FU-01 cancellation). Mode 5 cascade LAUNCHED. Phase 1 (BA rework) COMPLETE — 7 UPDATE, 1 OBSOLETE, 11 NEW requirements (triage: 26 CONFIRMED). Total REQ count 45 → 55. Awaiting user `continue` for Phase 2 (Critic). 6b (advanced-settings endpoint on api_gateway → pointsengine-emf/ProgramsApi.java) remains a separate follow-up cycle per Q14.

**Phase 1 rework delta (2026-04-22)**:
- **Artifacts updated**: `00-ba.md`, `00-ba-machine.md`, `00-prd.md`, `00-prd-machine.md` (each carries its own `## Rework Delta — Cycle 6a` section)
- **New REQ IDs (11)**: REQ-19 (`-1` filter on read), REQ-20 (read-wide hoist), REQ-21 (drop `validity.startDate`), REQ-22 (compute FIXED duration), REQ-33 (Class A reject), REQ-34 (Class B reject), REQ-35 (`-1` reject on write), REQ-36 (drop `startDate` on POST/PATCH), REQ-37 (nested `advancedSettings` reject), REQ-38 (`criteriaType` lock enforcement), REQ-55
- **Updated REQs (7)**: REQ-02, REQ-05, REQ-07, REQ-25, REQ-26, REQ-27, REQ-49 (all carry the `downgrade`→`renewal` rename and/or Q24 read/write shape)
- **Obsolete REQs (1)**: REQ-08 (old `downgrade.target` wire field — folded into `renewal.downgradeTo` via REQ-07 UPDATE)
- **Structural change**: Prior BA used unnumbered `- [ ]` bullets. Phase 1 rework introduced sequential REQ-01..REQ-55 IDs to enable auditable suspect-link triage downstream. Subagent flagged this as C5 reversible.
- **Open UX question (non-blocking)**: US-2 Step 2 "Qualifying Conditions" framing — wire contract is locked (Q24 → rejected on per-tier write, hoisted read-wide), but the UX decision on whether to hide / read-only / deep-link these in the per-tier wizard is a product/design call, not a BA call. Carried forward to Phase 2 or product discussion.

**Locked Q-series decisions (incremental — updated as each Q closes):**

- **Q1=(b), Q2=(b), Q4=forward-compat dual-block** — **SUPERSEDED BY Q27 (2026-04-23)**: Original decision flattened envelope with hoisted `live.*` + `status:"LIVE"` + reserved `live`/`pendingDraft` placeholder blocks. Q27 replaces this with a flat `List<TierEntry>` read shape — no envelope, no pairing, no nested blocks. See Q27 for the new contract.

- **Q3 locked (revised 2026-04-22 post-Q18)**: Rename on write: `downgrade` block → `renewal` block; field rename `downgrade.target` → **`renewal.downgradeTo`** (aligned with Figma Step 3 UI label "Downgrade to"). The initial proposal `renewal.downgradeCondition` was rejected — the values describe a target tier, not a trigger condition; UI naming wins. Enum values stay engine-canonical (`SINGLE | THRESHOLD | LOWEST`), only the wrapper field name changes. `reevaluateOnReturn` + `dailyEnabled` hoisted **out** of the renewal block (see Q10).

- **Q5c=(d)**: Multi-tracker AND/OR on eligibility → **defensively reject** in the current rework (write-path validator surfaces a clear error). This is a write-contract-tightening change, not a feature addition. _(Originally this decision deferred the real capability to FU-01; FU-01 is now CANCELLED — the engine already supports it via `additionalUpgradeCriteriaList` per Q24/Q20, and the wire plumbing folds into 6b, not a follow-up.)_

- **Q7=(d)**: `validity.startDate` dropped entirely for SLAB_UPGRADE-type tiers. Engine is event-driven (start = last upgrade timestamp); storing a per-tier startDate produced dead-wire and user confusion.

- **Q8=(a)**: FIXED-type validity duration is computed downstream from existing `startDate + periodValue` — no new field, no dead-wire addition. Read path surfaces the computed end-date; write path keeps inputs unchanged.

- **Q9 locked**: GET path filters out conditions whose `value == "-1"` (string-match, not numeric) for both `eligibility.conditions[]` and `renewal.conditions[]`. Matches the engine's `-1` sentinel convention (`peb TierDowngradeSlabConfig.getPoints()` null-coalesces to `BigDecimal.valueOf(-1)`). Reverses the current in-repo comment at `TierStrategyTransformer.extractConditions` lines 819-847 which explicitly says "do NOT filter". **Q9c symmetry**: write path ALSO rejects `value == "-1"` on POST/PUT (InvalidInputException in error-code range 9001-9010) — read and write stay in lockstep.

- **Q10a=(a)**: Advanced settings API lives at `GET|PUT|DELETE /v3/programs/{programId}/advanced-settings`. Singleton resource per program — no POST, PUT is upsert, DELETE clears to engine defaults.

- **Q10b locked (C5, amended 2026-04-22 by Phase 4 C-8 resolution — Option A)**: Advanced-settings payload scope — based on user-pasted UI spec ("We only want this only."):
  - **3 program-level booleans**: `reevaluateOnReturn` (← engine `isDowngradeOnReturnEnabled`), `dailyEnabled` (← engine `dailyDowngradeEnabled`), `retainPoints` (← engine `retainPoints`).
  - **Program-level eligibility shape**: `kpiType`, `upgradeType`, `trackingPeriod`, `conditions[]`, `expressionRelation` (everything under the "Eligibility" UI section **except** `threshold`). UI note confirms: *"Eligibility criteria & upgrade type will be same for all tiers, only the threshold value be different for each tier"*.
  - **Validity shape — reclassified PER-TIER (C-8 Option A, 2026-04-22)**: `validity.periodType` and `validity.periodValue` are physically per-slab in engine storage — `TierDowngradeSlabConfig.java:33-34` stores `@SerializedName("periodConfig") private TierDowngradePeriodConfig m_periodConfig` as a per-slab field indexed by `slabNumber`. Initial Q10b classification as "program-level validity shape" was an intent-level UX simplification, not reflective of storage. Follow-on effects (mandatory):
    - Not hoisted read-wide (REQ-20 excludes them).
    - Accepted per-tier on POST/PUT (REQ-26, REQ-49 unchanged).
    - NOT rejected by per-tier write validator (REQ-34 unchanged).
    - Advanced-settings endpoint in 6b does NOT carry them. If the product team later wants "one global renewal period for all tiers", that policy is UI-enforced or cross-tier validator-enforced — not wire-contract-enforced.
  - **Explicit exclusions from the advanced-settings payload**: `isDowngradeOnPartnerProgramDeLinkingEnabled` (engine field 4), `isActive` (engine field 5), `downgradeConfirmation` / `renewalConfirmation` (engine fields 6, 8 — nested comms), `reminders[]` (engine field 7). UI does not reference these; keep them engine-internal until a separate epic surfaces them.

- **Q10c locked (C6)**: Per-tier `renewal.conditions[]`, `renewal.downgradeTo`, `renewal.criteriaType` STAY on the per-tier POST/PUT `/v3/tiers` body. Evidence: `peb TierDowngradeSlabConfig` is per-slab with its own conditions + expression_relation; the "same for all tiers" UI note is scoped to Eligibility, not Validity/Renewal. Advanced-settings API never touches per-tier renewal thresholds. **Doc fix 2026-04-22**: earlier drafts referred to `renewal.conditionsToSatisfy` — that field name does NOT exist in code. The real wire field is `criteriaType` (see `intouch-api-v3/.../TierRenewalConfig.java:57`), constrained by B1a to the single value `"Same as eligibility"` — see Q26.

**Contract split (after Rework #6):**

| Field | v3 before | v3 after |
|---|---|---|
| `eligibility.kpiType / upgradeType / conditions[] / expressionRelation` | per-tier body (dead-wire on multi-tier writes) | `/v3/programs/{id}/advanced-settings` (program-level) |
| `eligibility.threshold` | per-tier body | **stays per-tier** |
| `validity.periodType / periodValue` | per-tier body (dead-wire on multi-tier writes under old per-slab semantics) | **stays per-tier** (C-8 Option A, 2026-04-22 — engine stores them per-slab in `TierDowngradeSlabConfig.periodConfig`; not hoisted read-wide, not rejected on per-tier write) |
| `validity renewal rule` (engine-side renewal extension, if any) | per-tier body | `/v3/programs/{id}/advanced-settings` (program-level — wire field name TBD in 6b) |
| `validity.startDate` | per-tier body | **removed** (Q7 — SLAB_UPGRADE) / computed (Q8 — FIXED) |
| `renewal.conditions[] / downgradeTo` | per-tier body (renamed from `downgrade`) | **stays per-tier** |
| `reevaluateOnReturn / dailyEnabled` | per-tier body (if present) | advanced-settings (program-level); **rejected on per-tier write (Q17)** |
| `retainPoints` | not exposed via v3 | advanced-settings (program-level); **rejected on per-tier write (Q18/Q24)** |
| `trackerId / additionalCriteria[]` (eligibility upgrade criteria) | not recognised on per-tier write | advanced-settings (program-level); **rejected on per-tier write (Q24)** — evidence: `ThresholdBasedSlabUpgradeStrategyImpl.java:44-51` — scalar `currentValueType` + `trackerId` + list `additionalUpgradeCriteriaList` all live on the program-level strategy, not per slab |
| `isDowngradeOnPartnerProgramDeLinkingEnabled` | not on any UI surface | advanced-settings (program-level) — leave alone in 6a; **rejected on per-tier write (Q24)** |
| `value == "-1"` on any condition | silently surfaced on read | filtered from read; rejected on write |

**Post-rename v3 write contract (POST/PUT /v3/tiers)**:
- `name, description, color, programId, eligibility.threshold, renewal.conditions[], renewal.downgradeTo, renewal.criteriaType` (B1a: `criteriaType` locked to `"Same as eligibility"` — see Q26)
- PUT body is partial-update (all fields optional); POST requires `programId, name, eligibility.threshold` (non-first tier).

**GET /v3/tiers/{tierId} read shape**:
- Flattened tier root carries: tier-specific fields + hoisted program-level context (from advanced-settings) so UI paints both screens from one call.
- Adds `status: "LIVE"` discriminator + reserves `pendingDraft` sub-block at root for forward-compat.

**Q11 locked (C5) — Hard flip, no back-compat window for rename**:
POST/PUT /v3/tiers drops the `downgrade` field entirely. Only `renewal` is accepted; requests carrying `downgrade` return 400 InvalidInputException (unknown field). Rationale: v3 tier surface is pre-GA for the new UI (the only real consumer, which Capillary controls); Rework #5 already made breaking wire changes without deprecation windows (`nudges`, `benefitIds`, `updatedViaNewUI`, `unifiedTierId`→`tierUniqueId`), so this follows precedent. Deprecation windows rot unless owned; we avoid the accumulation trap. Residual risk: unverified external caller surface — mitigated by grepping intouch-api-v3 `src/test` for JSON-body literal `"downgrade"` before flip to scope internal blast radius.

**Q12 locked (C5) — Full Mode 5 rework cascade**:
Rework #6 enters the pipeline via Mode 5 against Phase 1 (BA) as the target phase. Forward cascade per agent definition: BA → Critic → Blockers → Architect → Impact → Designer → QA → BTG → SDET (RED) → Developer (GREEN) → Backend Readiness → Compliance → Reviewer. Phase 3 (UI) and Phase 5 (Research) marked CONFIRMED and skipped — no new screens, no new repos. Rationale: scope touches ~20-30 BTs (rename sweep + new endpoint + validator tightening + sentinel hygiene) where suspect-link triage (CONFIRMED/UPDATE/REGENERATE/OBSOLETE/NEW) is the exact mechanism designed for this shape; SDET-before-Developer preserves TDD discipline; Compliance phase catches dead-wire regressions (the class of bug Rework #6 itself is correcting); rework history captured in `pipeline-state.json` for audit.

**Q13 locked (C6) — intouch-api-v3 only, no engine repo changes**:
All Rework #6 items are wire-layer cleanup. Engine already stores all affected fields at the correct level (program-level booleans and eligibility/validity in `TierConfiguration.java`; per-tier downgrade conditions in `TierDowngradeSlabConfig`). No Thrift IDL changes (existing `createSlabAndUpdateStrategies` reused for advanced-settings writes). No Flyway migrations. The only engine-dragging item — multi-tracker eligibility AND/OR — is explicitly deferred as FU-01 and out of Rework #6 scope. Residual caveat: `isDowngradeOnPartnerProgramDeLinkingEnabled` schema drift (JSON key "Expiry" vs Java field "DeLinking") noted as future cleanup, out of Q10b scope.

**Q14 locked (C6) — Rework #6 split into #6a (basic API signature) + #6b (advanced-settings endpoint)**:
User interrupted the Mode 5 cascade launch and directed: *"Hi, lets first do the basic changes like the api signature changes for that. Then we will implement the advanced settings. For that one discussion is needed."* Scope split:
- **6a (now)**: rename `downgrade` → `renewal` on CREATE/PUT, `downgrade.target` → `renewal.downgradeTo` (Q3 revised — UI-matching, Figma "Downgrade to"), hoist `reevaluateOnReturn`/`dailyEnabled` out of renewal, GET envelope flatten (hoist `live.*` + `status:"LIVE"` + forward-compat dual-block), drop `validity.startDate` for SLAB_UPGRADE tiers, compute FIXED duration from `startDate + periodValue`, filter `value == "-1"` from read + reject on write, defensive reject of multi-tracker eligibility, hard flip (Q11), reject Class A program-level fields on per-tier write (Q17), reject Class B program-level fields on per-tier write (Q18), remove compound group-condition support from the wire entirely (Q19).
- **6b (after discussion)**: `GET|PUT|DELETE /v3/programs/{programId}/advanced-settings` endpoint surface and design. Separate discussion required before implementation (Q15 Thrift wiring, Q16 field semantics already locked as pre-work).

**Q15 locked (C6) — Use `getAllConfiguredStrategies` Thrift for advanced-settings in 6b**:
Initial suggestion of `getProgramSettings`/`updateProgramSettings` was evidence-rejected: the 47-field `ProgramSettings` struct (`Thrift/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift:584-636`) carries sync/points-contribution/transfer-limit fields — none of the Q10b-scoped tier booleans, eligibility, or validity. Correct existing surface is `getAllConfiguredStrategies(programId, orgId)` which returns `StrategyInfo[]` including `SLAB_UPGRADE` (eligibility: kpiType, tracker, thresholds) + `SLAB_DOWNGRADE` (validity: periodType/periodValue + 3 program-level booleans). Read path uses this directly; write path reuses existing `createSlabAndUpdateStrategies` with read-modify-write discipline. Zero Thrift IDL changes.

**Q16 locked (C5) — "Define when to validate tier's renewal conditions" = periodType**:
The UI copy *"Define when to validate tier's renewal conditions"* maps 1:1 to engine `TierDowngradePeriodConfig.PeriodType` (`FIXED | SLAB_UPGRADE | SLAB_UPGRADE_CYCLIC | FIXED_CUSTOMER_REGISTRATION`). This is the "when to evaluate renewal" clock, not a new field. Advanced-settings body carries it as `validity.periodType` + `validity.periodValue` (matching the existing v3 per-tier wire names). No new UI label → new enum mapping; the UI copy is a semantic description of the existing field.

**Q17 locked (C5, 2026-04-22) — Per-tier write REJECTS Class A program-level fields in 6a**:
`reevaluateOnReturn` + `dailyEnabled` (Class A) were written on every per-tier CREATE/UPDATE via `TierStrategyTransformer.applyProgramLevelBooleans` (lines 524-530) — documented as last-writer-wins (R4 comment at lines 345-349). Evidence assembled 2026-04-22:
- **Write-path audit**: `grep -R "\.setIsDowngradeOnReturnEnabled(|\.setDailyDowngradeEnabled(" /Users/ritwikranjan/Desktop/emf-parent` → zero production-code setter calls outside intouch-api-v3. All engine-side setter invocations are in `.specstory/history/` transcripts or test fixtures. GSON deserialization is the only implicit writer (reads JSON from DB).
- **Read-path consumers** (engine): `PointsReturnService.java:1175` (gates downgrade-on-return trigger), `SlabDowngradeAuditLogService.java:39,57` (audit log DTOs), `SlabDowngradeStrategyImpl.java:180-182` (strategy-interface bridge). No second write path exists.
- **Decision**: In 6a, per-tier POST/PUT `/v3/tiers` rejects `reevaluateOnReturn` and `dailyEnabled` if present on wire with 400 InvalidInputException in error-code range 9001-9010. Message template: *"`reevaluateOnReturn`/`dailyEnabled` is a program-level setting; use `PUT /v3/programs/{programId}/advanced-settings`. Omit from tier payload."* Mirrors Q9c symmetry (`-1` sentinel rejected on write) and matches Q11 hard-flip precedent. Existing DB values stay put; no data migration. `applyProgramLevelBooleans` deleted in 6a; the two `addProperty` lines (528-529) go away. In 6b, advanced-settings becomes sole writer. Residual risk: if 6b slips, these fields become effectively immutable from wire — acceptable given FU-01 scope already carries the real capability forward.

**6a residual discovery items** (to validate during BA rework, not blocking Q-locks):
- Class B fields (KPI, tracker, retainPoints, reminders) already preserved by read-modify-write in `applySlabUpgradeDelta` + `applySlabDowngradeDelta` — no per-tier override path — nothing to reject.
- `isDowngradeOnPartnerProgramDeLinkingEnabled` (schema-drift field name) — NOT on any UI surface, not in Q10b scope, leave alone in 6a.

**Q20 locked (C6, 2026-04-22) — Engine storage scope classification**:
Deep codebase research established the authoritative per-tier vs program-level split (evidence-backed, refuting the earlier "all settings are per-tier" assumption):

- **Per-tier (engine storage)**: `ProgramSlab` DB row (`pointsengine-emf/.../entity/ProgramSlab.java:70-93` → columns `programId`, `serialNumber`, `name`, `description`, `createdOn`, `metadata`), plus `TierDowngradeSlabConfig[]` per-slab entries (`pointsengine-emf/.../strategy/TierDowngradeSlabConfig.java:24-49` → `slabNumber`, `shouldDowngrade`, `downgradeTarget`, `periodConfig`, `conditions[]`, `id`, `name`, `description`, `colorCode`), plus `SlabMetaData` per-slab blob. **Validity fields `periodType` + `periodValue` are here** (inside `periodConfig` — `TierDowngradeSlabConfig.java:33-34`: `@SerializedName("periodConfig") private TierDowngradePeriodConfig m_periodConfig`), NOT in `TierDowngradeStrategyConfiguration`. Classification amended 2026-04-22 by Phase 4 C-8 Option A.
- **Per-tier VALUE stored in a program-level CSV**: `threshold` is carried in `SlabUpgradeStrategy.propertyValues.threshold_values` as a comma-separated list indexed by `slabNumber - 1`. Per-tier semantically, program-level physically.
- **Program-level (engine storage — one per program)**:
  - `SlabUpgradeStrategy.propertyValues`: `currentValueType` (→ wire `kpiType`), `slabUpgradeMode` (→ wire `upgradeType`), `trackerId`, `trackerConditionId`, `additionalUpgradeCriteriaList[]` — all scalars or single program-wide list (`ThresholdBasedSlabUpgradeStrategyImpl.java:44-51`; `UpgradeCriteria.java:20-23` confirms singular `currentValueType` / `trackerId` / `trackerConditionId`).
  - `TierDowngradeStrategyConfiguration`: four Class A booleans — `isDowngradeOnReturnEnabled`, `dailyDowngradeEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled` (`TierDowngradeStrategyConfiguration.java:28-38`).

This classification is the foundation for Q24 (strict asymmetric contract) and supersedes any lingering doc language that treated eligibility (`kpiType`/`upgradeType`/`trackerId`/`additionalCriteria[]`) as per-tier.

**Q22 locked (C5, 2026-04-22) — Advanced-settings carries no per-tier data, ever**:
Follow-on to Q10b: the advanced-settings payload body is scoped to program-level fields only (the three Class A booleans + program-level eligibility shape + program-level validity shape). It does **not** carry `threshold` (per-tier value in program-level CSV) and it does **not** carry any per-tier `name`/`description`/`color`/`downgradeTo`/`renewal.conditions[]`. Advanced-settings and per-tier CRUD are orthogonal surfaces — neither writes the other's storage. Ensures no split-brain writes.

**Q23 locked (C6, 2026-04-22) — Advanced-settings uses api_gateway, not intouch-api-v3/Thrift**:
Supersedes Q15 (`getAllConfiguredStrategies` Thrift via intouch-api-v3). Correct surface is infrastructure-level `api_gateway` routing: client hits `/api_gateway/loyalty/v1/programs/{programId}/advanced-settings`, nginx routes directly to `pointsengine-emf/.../ProgramsApi.java`, bypassing intouch-api-v3. No MC workflow (program-level settings are not tier-CRUD and are out of MC scope by user-confirmed product decision), no auth/logging wrapping at intouch-api-v3. 6b scope is the api_gateway handler in pointsengine-emf. 6a remains pure wire-layer in intouch-api-v3.

**Q24 locked (C6, 2026-04-22) — Strict asymmetric contract: write narrow, read wide**:
Per-tier POST/PUT `/v3/tiers` **rejects** every program-level field (Class A booleans + program-level eligibility fields + `isDowngradeOnPartnerProgramDeLinkingEnabled`) with 400 InvalidInputException in error-code range 9001-9010. Message template: *"`<field>` is a program-level setting; use `PUT /api_gateway/loyalty/v1/programs/{programId}/advanced-settings`. Omit from tier payload."* Per-tier GET `/v3/tiers/{tierId}` **hoists** program-level fields read-wide onto the flattened envelope (Q1/Q2/Q4) so the UI paints both screens from one call — DRAFT and LIVE surface identical program-level context. Rationale: eliminates silent-drop + last-writer-wins bugs (the class of bug Rework #6 exists to correct); explicit 400 beats silent behaviour; read-wide preserves UI UX without round-tripping advanced-settings. **Supersedes Q17/Q18/Q21** (Q17/Q18 previously covered Class A + Class B individually — Q24 generalises the principle to all program-level fields including `trackerId`, `additionalCriteria[]`, `isDowngradeOnPartnerProgramDeLinkingEnabled`). Q21's narrower scope subsumed.

**Subsumed Q-numbers reference map (C-7 Hybrid fix, 2026-04-22)**:
Historical Q-numbers cited in BA/PRD artifacts that were folded into later umbrella decisions. No independent lock blocks exist for these; they are preserved here for grep-discoverability of granular intent.

| Subsumed | Original intent | Folded into | Evidence anchor |
|---|---|---|---|
| Q17 | Per-tier write rejects Class A booleans (`reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled`) | Q24 | `TierDowngradeStrategyConfiguration.java:28-38` |
| Q18 | Per-tier write rejects program-level eligibility fields (`kpiType`, `upgradeType`, `trackerId`, `additionalCriteria[]`, `expressionRelation`) | Q24 | `ThresholdBasedSlabUpgradeStrategyImpl.java:44-51` |
| Q19 | GET envelope forward-compat dual-block (flattened hoist + deprecated `live.*` block) | Q1/Q2/Q4 | `TierEnvelopeResource` (flatten pattern from Q1) |
| Q21 | Error-code banding for Q24 write-narrow rejects | Q24 | Shares 9001-9010 with existing `TierCreateRequestValidator` |
| Q25 | Advanced-settings endpoint is dependency-free per tier | Q24 | Locked as Q25, also subsumed |

**Usage rule**: BA/PRD/Designer artifacts SHOULD cite `Q24` (the umbrella) and MAY append `(subsumes Q17/Q18/Q21)` for traceability. A bare `Q18` or `Q19` citation is an artifact bug — check this map and upgrade the citation.

**Q-OP-1 locked (C6, 2026-04-22 — Phase 4 Operational Resolution — resolves Critic C-9)**: **Error code range 9011-9020** allocated as the Q24 write-narrow band. 9001-9010 remains the Rework #4/#5 legacy range (already occupied by pre-6a validators; do not overload). Allocation:

| Code | Reject cause | Tied to | Source Q-lock |
|---|---|---|---|
| 9011 | Class A program-level boolean on per-tier wire (`reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled`) | REQ-33 | Q24 (subsumes Q17) |
| 9012 | Class B program-level eligibility on per-tier wire (`kpiType`, `upgradeType`, `trackerId`, `trackerConditionId`, `additionalCriteria[]`, `expressionRelation`) | REQ-34 | Q24 (subsumes Q18) |
| 9013 | Legacy `downgrade` field on wire (hard-flip reject) | REQ-27 | Q11 |
| 9014 | Nested `advancedSettings` envelope on per-tier wire | REQ-37 | Q22 |
| 9015 | `value == "-1"` sentinel on any `eligibility.conditions[]` or `renewal.conditions[]` entry | REQ-35 | Q9 |
| 9016 | `validity.startDate` on SLAB_UPGRADE-type tier | REQ-36 | Q7 |
| 9017 | Non-B1a renewal contract (`renewal.criteriaType` != `"Same as eligibility"` OR non-empty `renewal.expressionRelation` / `renewal.conditions[]`) | REQ-38 | Q26 |
| 9018 | FIXED-family `validity.periodType` without required `validity.periodValue` (assigned Phase 4 Q-OP-2) | REQ-56 | Phase 4 Q-OP-2 |
| 9019-9020 | Reserved for 6a runtime-discovered rejects (Designer may allocate during Phase 7) | — | — |

6b advanced-settings endpoint will carve its own band when scope firms up (suggested 9021-9030, not pre-allocated here to avoid over-engineering). Supersedes earlier BA/PRD text asserting "error code in range 9001-9010" for the new rejects — that text was from an ambiguous initial javadoc and would have caused slot collisions.

**Q-OP-2 locked (C5, 2026-04-22 — Phase 4 Operational Resolution — partially resolves Critic C-12)**: **PeriodType enum scope locked to option (c) — out of 6a — with user-imposed caveat on duration**.

**Scope lock**: 6a explicitly handles `SLAB_UPGRADE` only (REQ-21 dropped startDate + REQ-36 startDate reject on write). The three other engine enum values — `FIXED_CUSTOMER_REGISTRATION`, `FIXED_LAST_UPGRADE`, `SLAB_UPGRADE_CYCLIC` — are **pass-through unchanged** from Rework #5 behaviour. No new explicit wire-level handling in 6a. The silent-gap question (what GET emits / what POST accepts for those three values) is deferred to a future rework.

**User caveat on duration (the reason Q-OP-2 needed a lock at all)**:
- `validity.periodValue` IS required when `validity.periodType` is in the **FIXED family** (`FIXED`, `FIXED_CUSTOMER_REGISTRATION`, `FIXED_LAST_UPGRADE`) → REQ-56, error code 9018.
- `validity.periodValue` is NOT required for **SLAB_UPGRADE family** (`SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`) — engine is event-driven, no fixed duration.
- POST: straightforward — both fields in the incoming payload.
- PUT: if a payload changes `periodType` INTO FIXED family, the effective post-merge state must include `periodValue`. Exact merge semantics (payload-only vs payload+stored) deferred to Designer Phase 7.

**Read-side null safety (REQ-22 amendment)**: for legacy FIXED tiers whose stored `periodValue` is absent (pre-6a), GET omits the computed end-date field rather than returning null/0. Final wire shape decided by Designer Phase 7.

**Why Q-OP-2 is a resolution, not a full answer to C-12**: The original C-12 question — "what does the wire emit for FIXED_CUSTOMER_REGISTRATION / FIXED_LAST_UPGRADE / SLAB_UPGRADE_CYCLIC reads?" — is explicitly scoped OUT of 6a (documented). The forward guard (require `periodValue` whenever periodType is any FIXED-family on write) prevents the gap from widening. Per-enum read behaviour for the three unhandled values is a future-rework question if it ever surfaces as an actual code-path issue.

**Why 9011-9020 and not reuse 9001-9010**: TierCreateRequestValidator + TierUpdateRequestValidator javadoc states range 9001-9010 is shared. Existing Rework #4/#5 validators occupy most of those slots; adding 7 new rejects would either overflow or force diagnostic ambiguity (one code covering multiple semantically distinct causes). Extending by one decade preserves per-reject diagnostic clarity and leaves room for 6b to extend further.

**Q25 locked (C5, 2026-04-22) — Advanced settings is dependency-free per tier**:
User confirmed (product decision): the advanced-settings endpoint is a **program-level singleton**, independent of tier CRUD. Tiers can be created without advanced-settings being set (engine defaults apply); advanced-settings can be set/modified without touching any tier. There is no "every tier must call advanced-settings on create" dependency. Subsumed into Q24 (standalone surface on api_gateway).

**Q26 locked (C6, 2026-04-22) — Keep B1a renewal contract unchanged; fix doc typo**:
B1a contract (Rework #5) is preserved: `TierRenewalConfig.criteriaType` on the wire accepts exactly one value — `"Same as eligibility"` (`intouch-api-v3/.../TierRenewalConfig.java:55`, the `CRITERIA_SAME_AS_ELIGIBILITY` constant). `conditions[]` + `expressionRelation` inside the renewal block must be null/empty (reserved for future B2 engine work). **Doc-only fix**: every place in pipeline docs referring to `renewal.conditionsToSatisfy` (a name that does not exist in the codebase) is renamed to `renewal.criteriaType` to match the actual DTO field. No wire changes. The engine has no storage slot for an independent renewal rule — renewal is implicit (`UpgradeSlabActionImpl:815` fires a `RenewSlabInstruction` when the upgrade evaluation resolves to the customer's current slab; the rule evaluated is the tier's eligibility, not a separate renewal rule), so adding any other `criteriaType` value today would be dead-wire.

**FU-01 CANCELLED (2026-04-22)**:
User confirmed after deeper codebase research that `additionalUpgradeCriteriaList` in pointsengine-emf (`ThresholdBasedSlabUpgradeStrategyImpl.java:51`) already supports multi-tracker eligibility composition at the engine layer — a full `ArrayList<AdditionalUpgradeCriteria>` with singular `currentValueType`/`trackerId`/`trackerConditionId` per entry (`UpgradeCriteria.java:20-23`). `peb` is the same engine layer as pointsengine-emf (not a separate repo with a scalar-only model as the original FU-01 scope claimed). The capability is already in the engine; only the wire plumbing in intouch-api-v3 (`applySlabUpgradeDelta` write + `extractEligibilityForSlab` read) needs to propagate it through. That plumbing work folds into 6b (advanced-settings endpoint design) alongside the api_gateway handler — no separate follow-up, no Flyway migration, no cross-repo engine change. Original FU-01 scope (migration from scalar to list + Flyway backfill) is moot.

---

## Deferred Follow-ups (Commit in a Must-Do Order)

These are known-needed items that have been **consciously deferred** out of the current rework scope. They are not "open questions" — the decisions are locked; only execution is pending.

### FU-01 — CANCELLED (2026-04-22)

_(Originally decided: Q5c = (d), 2026-04-22 — "Multi-tracker AND/OR for eligibility (engine change) — MUST follow immediately after the current rework". Cancelled same day after deeper codebase research.)_

**Reason for cancellation:** The engine already supports multi-tracker eligibility composition — no migration is needed.

Evidence:
- `pointsengine-emf/.../ThresholdBasedSlabUpgradeStrategyImpl.java:51` — `private ArrayList<AdditionalUpgradeCriteria> additionalUpgradeCriteriaList;` is a full list on the program-level strategy.
- `pointsengine-emf/.../UpgradeCriteria.java:20-23` — each `UpgradeCriteria` (and its `AdditionalUpgradeCriteria` subclass) carries its own singular `currentValueType` + `trackerId` + `trackerConditionId`; composition across trackers is expressed by multiple list entries, not by multi-valued fields on one entry.
- `ThresholdBasedSlabUpgradeStrategyImpl.java:229-239` — runtime evaluation iterates `additionalUpgradeCriteriaList` — the list is live, not aspirational.
- `peb` and `pointsengine-emf` are the same engine layer (not a separate repo with a scalar-only model, as the original FU-01 scope assumed). There is no `SlabUpgradeStrategy.java:20-24` in peb with scalar-only fields requiring migration.

**Residual work (absorbed into 6b, not a separate follow-up):** the wire plumbing in `intouch-api-v3/TierStrategyTransformer` (`applySlabUpgradeDelta` write + `extractEligibilityForSlab` read) still needs to propagate `additionalUpgradeCriteria[]` + `expressionRelation` end-to-end. That work lives inside the 6b advanced-settings endpoint design (api_gateway → pointsengine-emf/ProgramsApi.java, per Q23), since eligibility composition is a program-level concern under Q24. Zero Flyway migration, zero engine change, zero cross-repo coordination.

**Net effect on 6a:** 6a's defensive reject of multi-tracker eligibility on the per-tier write path (Q5c) stands unchanged — per-tier write is the wrong surface for this data under Q24. The engine's list capability will be surfaced through the advanced-settings surface in 6b.

---

**Q-OP-3 locked (C6, 2026-04-22) — External-consumer audit clean; "new UI is sole consumer" upgraded C5 → C6**:

Full codebase audit executed across 16 repos in the workspace (`emf-parent/*`, `intouch-api-v3`, `peb`, `Thrift`, `rule-engine`, all `cd-cheetah-*`, `cc-stack-crm`, `campaigns_auto`, `crm-mcp-servers`, `event-notification`, `emf-async-executor`, `cap-intouch-ui-appserver-wrapper`, `shopbook-datamodel`, `cd-libcheetah`, and the secondary `Artificial Intelligence/emf-parent` copy). Search terms: `v3/tiers`, `/v3/tiers`, `TierController`, `TierReviewController`, `api_gateway.*tier`, `api_gateway/loyalty/v1/tiers`, `POST.*tier`, `PUT.*tier`, `CreateTier`, `UpdateTier`.

**Result**: **zero internal backend callers** of `POST /v3/tiers`, `PUT /v3/tiers/{tierId}`, `POST /v3/tiers/{tierId}/submit`, `POST /v3/tiers/{tierId}/approve` found. All `v3/tiers` references are internal to `intouch-api-v3` itself (7 files: 2 controllers, 2 validators, 2 transformers, 1 test — the endpoint module and its own support code).

**False positives triaged out** (none are consumers):
- `cd-cheetah-apps-points-core` PHP widgets use `$_POST['tier_upgrade_strategy_home__...']` — these are HTML form field names, not REST HTTP POST calls.
- `Thrift` has `PartnerProgramTierUpdate` — a different domain concept (partner-program tier sync), not the tier CRUD API.
- `campaigns_auto` python Constants file hits `/api_gateway/loyalty/v1/...` for promotion endpoints only; no tier endpoints.
- `cc-stack-crm` SQL seed false-positive on broad `POST.*tier` regex — zero precise matches.
- `Artificial Intelligence/emf-parent` secondary copy: only documentation in `.claude/skills/*`.

**Confidence upgrade**: BA constraint "the new UI is the only consumer" is upgraded from **C5 → C6** for the surveyed surface.

**Residual C5 risks** (outside audit reach) — flagged forward to Phase 11 Reviewer:
1. External SaaS customers directly integrating with Capillary public API.
2. Third-party / partner automation tools not in any owned repo.
3. QA/perf/regression automation that lives in separate test repos outside this workspace.
4. nginx `api_gateway` rewrites in deploy config (grep confirmed no tier paths at code level; deploy config not inspected).
5. Operator cURL scripts / runbooks not checked into repos.

**Phase 11 mitigation recommendations** (carried forward):
1. Access-log scan at staging gateway for non-UI user agents hitting POST/PUT `/v3/tiers*` over last 30 days.
2. Publish 9011-9020 error code band in `api-handoff.md` ≥30 days before cutover (band already published).
3. Optional soft-launch: log (don't reject) unknown fields in staging for 2 weeks before hard-flip in production.

**No back-compat impact** — contract changes (9011-9020 band from Q-OP-1, unknown-field hard reject from Q11, REQ-56 conditional duration from Q-OP-2) stand as specified.

**Evidence artifact**: `q-op-3-consumer-audit.md`.
**Resolves contradiction**: C-17 (external consumer audit missing) — C5 → C6 for audited surface; residual C5 flagged to Phase 11. (C-11 is the separate Jackson `FAIL_ON_UNKNOWN_PROPERTIES` config contradiction — distinct from this one and unaffected by Q-OP-3.)

---

## Phase 4 Status — COMPLETE (2026-04-22)

All 5 Phase 4 blockers/questions resolved:

| # | Item | Decision | Resolves |
|---|---|---|---|
| 1 | C-7 | Phantom Q-locks — Hybrid (re-lock Q9 on 9015, add forward guard) | Phantom Q-lock drift |
| 2 | C-8 | Validity classification — Option A (per-slab `TierDowngradeSlabConfig[]` is canonical; program-level is legacy) | Engine-storage classification ambiguity |
| 3 | Q-OP-1 | Error code rebanding — Option b (9011-9020 distinct band for 6a) | C-9 (error code collision) |
| 4 | Q-OP-2 | PeriodType enum scope — Option c + user caveat → REQ-56 conditional duration (code 9018) | C-12 (partial — scope locked out of 6a, forward guard added) |
| 5 | Q-OP-3 | External consumer audit — Option a (audit clean, C5 → C6) | C-17 (external consumer audit) — partial, residual C5 flagged to Phase 11 |

**Next phase**: Forward cascade starts at **Phase 6 (Architect)** — the Rework #6a delta to `01-architect.md` incorporates the 5 Phase 4 decisions, then propagates through Impact (6a), Designer (7), QA (8), BTG (8b), SDET-RED (9), Developer-GREEN (10), Backend Readiness (10b), Compliance (10c), and finally Reviewer (11) where the Q-OP-3 residual-risk flag is picked up for deploy guidance.

---

## Phase 6 — Architect (Rework #6a delta, 2026-04-22) — COMPLETE

Scoped rework of `01-architect.md`: 5 new ADRs, 1 new §6.5 contract section, 3 new risk rows, 7 new done-criteria, header date/trail updated. Zero changes to pre-existing ADR text.

**New ADRs**:

| ADR | Decision | Resolves | Defers to |
|---|---|---|---|
| **ADR-17R** | Distinct error-code band 9011-9020 for 6a rejects; legacy 9001-9010 frozen; per-REQ distinct codes | C-9 (fully) | — |
| **ADR-18R** | Per-slab canonical for `validity.periodType`/`periodValue` — `TierDowngradeSlabConfig[].periodConfig`; program-level `SlabUpgradeStrategy.propertyValues` carries 4 Class A booleans only | C-8 (fully — BLOCKER closed) | — |
| **ADR-19R** | `PeriodType` scope lock — 6a handles `SLAB_UPGRADE` explicitly; FIXED family requires `periodValue` (REQ-56 / code 9018); read-side null-safe for legacy FIXED | C-12 (partial — scope + forward guard) | Designer: PUT merge semantics, read-side wire shape |
| **ADR-20R** | Unknown-field hard reject via Jackson `FAIL_ON_UNKNOWN_PROPERTIES` — legacy `downgrade` block returns 400 at deserialization | C-11 (partial — Designer verifies config) + C-17 (partial — internal audit clean) | Designer: verify global ObjectMapper config; fallback validator/annotation if permissive |
| **ADR-21R** | Write-narrow / read-wide asymmetric contract — per-tier writes reject program-level fields (Class A+B); GET emits full hoisted envelope | Q24 (ratified) | 6b: advanced-settings separate surface |

**New risks** (added to §11):
- **R13** (MEDIUM): external-consumer residual from C-17 — 5 channels outside audit reach (SaaS customers, partners, separate QA repos, nginx rewrites, operator scripts). Mitigation: access-log scan, band announcement ≥30 days, optional soft-launch.
- **R14** (MEDIUM): Jackson config not globally enabled — ADR-20R fallback chain. Designer verifies first step of LLD.
- **R15** (LOW): PeriodType pass-through rot for 3 non-SLAB_UPGRADE enum values — covered by REQ-22 read null-safety + REQ-56 write forward guard; defect in the 3 values triggers a follow-up rework, not a 6a block.

**Contradictions still open for Designer (Phase 7)**:
- C-10 (numeric `-1` wire type — string vs number) — ADR-19R reserves code 9016 for the numeric case
- C-11 (Jackson config verification — R14)
- C-13 (`TierRenewalNormalizer` class existence)
- C-14 (list endpoint hoist shape)
- C-16 (`isDowngradeOnPartnerProgramDeLinkingEnabled` key-name drift)

**Forward cascade payload to Phase 6a (Impact Analysis)**:
- **Changed ADRs**: ADR-17R through ADR-21R (all ADDED)
- **Impact scope**: contract-hardening only — zero schema, zero storage, zero new endpoints
- **Analyst focus**: (1) blast radius of the new error-code band on any error-code-consuming client; (2) Jackson config verification as a cross-module concern if the global ObjectMapper is shared; (3) confirm ADR-18R does not accidentally pull program-level write paths into MC scope; (4) confirm read-side null safety (REQ-22 amendment) does not widen envelope shape for existing GET consumers
- **Guardrails to re-check**: G-01 (timezone on REQ-22 computed end-date), G-07 (tenant isolation on reject paths), G-12 (error-code consistency on new band)

---

### Phase 6a — Impact Analysis (Rework #6a delta) — COMPLETE (2026-04-22)

**Artifact**: `02-analyst.md` — appended "Rework #6a Delta — Impact Analysis" section (R6a-1 through R6a-14).
**Mode**: Delta (existing Phase 6a analysis preserved; Rework #6a section additive).
**BLOCKERS raised against Architect**: **0**.

**Blast radius (C6 — confirmed)**:
- 1 repo touched: `intouch-api-v3`
- ≤3 files: `TierCreateRequestValidator.java`, `TierUpdateRequestValidator.java`, error-code constants file (+ ≤1 config/annotation file if ADR-20R Designer verification shows Jackson permissive)
- 0 files in: `emf-parent`, `peb`, `Thrift`, `pointsengine-emf`, `cap-intouch-ui-appserver-wrapper`
- 0 schema changes, 0 Thrift IDL changes, 0 engine changes

**Cross-module concerns resolved at C6**:
- **Item 2 (Jackson cross-module)** → Designer MUST pick per-DTO `@JsonIgnoreProperties` OR scanning validator IF global is permissive; MUST NOT flip the global setting. This is locked as D-6a-1.
- **Item 3 (ADR-18R MC scope)** → Per-slab writes already inside per-tier MC SAGA (`TierApprovalHandler.publish`); program-level fields remain rejected on per-tier writes and written only through the separate advanced-settings (6b) surface. MC boundary integrity preserved.
- **Item 4 (REQ-22 envelope stability)** → None of the 3 Designer wire-shape options (omit / null / 0) widen the Rework #5 envelope. But D-6a-2 locks Designer to **omit or explicit null** — `0` is forbidden (epoch-vs-"no-end-date" ambiguity).

**GUARDRAILS re-check**:
- G-01 (timezone): COMPLIANT — REQ-22 amendment only null-safes missing `periodValue`, no new date math
- G-02 (null safety): NEEDS ATTENTION — wire-shape pick locked by D-6a-2 (omit or null, never 0)
- G-03 (security): COMPLIANT — reject reason strings field-name only, no stored values (Designer to confirm)
- G-04 (performance): COMPLIANT — +<1ms overhead, improved malformed-input latency
- G-05.4 (migration): N/A — zero schema
- G-06 (API design): COMPLIANT — existing `@ControllerAdvice` handles new codes
- G-07 (tenant isolation): COMPLIANT — rejects pre-DAO, existing tenant-scoped path unchanged
- G-12 (error-code consistency): COMPLIANT — ADR-17R distinct per-REQ codes, legacy band frozen

**Designer (Phase 7) locked instructions now 5 total**:
1. Verify global Jackson config as first step of LLD (ADR-20R)
2. Pick PUT merge semantics — payload-only vs post-merge — for REQ-56 (ADR-19R)
3. Pick exact read-side wire shape for legacy FIXED tiers missing `periodValue` (ADR-19R + D-6a-2: omit or null, NOT 0)
4. **D-6a-1**: If Jackson global is permissive, use per-DTO annotation OR scanning validator — do NOT flip global
5. **D-6a-2**: Wire shape is **omit** or **explicit null**, never 0

**Reviewer (Phase 11) forward flags — 3 total**:
- **P11-6a-1**: External-consumer residual (R13) → staging access-log scan ≥30 days OR executed soft-launch with zero non-UI rejects
- **P11-6a-2**: Error-code band announcement → `api-handoff.md` regenerated post-Phase 10 with 9011-9018 listed, dated ≥30 days pre-cutover
- **P11-6a-3**: R14 closure → Phase 7 Designer verification outcome logged; Phase 9 SDET tests prove reject either way

**Risk register delta** (R13/R14/R15 already in `01-architect.md §11`; Phase 6a added likelihood + owner + re-assessment trigger):
- R13: severity MEDIUM, likelihood LOW–MEDIUM, owner Phase 11 Reviewer
- R14: severity MEDIUM, likelihood UNKNOWN-until-verified, owner Phase 7 Designer
- R15: severity LOW, likelihood LOW, owner Phase 11 Reviewer (document as acknowledged residual)

**New risks introduced by 6a analysis (over and above Architect's list)**: **NONE**.

**Forward cascade payload to Phase 7 (Designer)**:
- **Task**: Implement ADR-17R..ADR-21R on 2–3 validator/constants/config files in intouch-api-v3
- **Scope floor**: Contract-hardening only — zero schema, zero Thrift, zero engine
- **Locked deferred items**: 5 Designer picks (see above)
- **C-10**: pick wire type for `-1` sentinel (string vs number) — reserves code 9015/9016
- **C-11**: verify Jackson global config (R14 closure)
- **C-13**: confirm `TierRenewalNormalizer` class existence
- **C-14**: lock list endpoint hoist shape
- **C-16**: resolve `isDowngradeOnPartnerProgramDeLinkingEnabled` key-name drift

---

## Rework #6a — Phase 7 (Designer — LLD) COMPLETE — 2026-04-22

**Artifact**: `03-designer.md` §"Rework #6a Delta — Designer LLD" (appended after §R3).

### Reconnaissance findings (evidence chain — see `03-designer.md` §6a.1)

- **F1 — Global Jackson is STRICT by default** [C6]. `IntouchApiV3Application.java:94-99` declares `@Bean ObjectMapper` as `new ObjectMapper()` only setting TimeZone. User-provided bean backs off Spring Boot's permissive `Jackson2ObjectMapperBuilder` default. Pattern evidence: 36 DTOs carry per-class `@JsonIgnoreProperties(ignoreUnknown=true)` opt-outs.
- **F2 — `TierCreateRequest` / `TierUpdateRequest` carry NO opt-out annotation** [C7]. Verified via direct DTO reads (28 + 23 lines).
- **F3 — Engine `PeriodType` has 4 values, not 5** [C7]. `peb/.../TierDowngradePeriodConfig.java:17-18` canonical: `{FIXED, SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC, FIXED_CUSTOMER_REGISTRATION}`. `FIXED_LAST_UPGRADE` is **phantom** (PRD-wording drift).
- **F4 — `TierRenewalNormalizer` exists** [C7]. 49-line class at `tier/TierRenewalNormalizer.java`; `normalize()` fills `CRITERIA_SAME_AS_ELIGIBILITY` default.
- **F5 — Canonical engine field is `isDowngradeOnPartnerProgramExpiryEnabled` (NOT `…DeLinkingEnabled`)** [C7]. `EngineConfig.java:14` + `TierStrategyTransformer.java:287` javadoc. The `…DeLinking…` variant exists only in unrelated `rule-engine/PartnerProgramDeLinkingProfile` event-sourcing code.
- **F6 — List endpoint already envelope-wrapped** [C6]. `TierController.java:52` returns `TierListResponse → List<TierEnvelope>` (Rework #5 shape). No hoist reshape by Rework #6a.

### Designer picks — all 5 LOCKED

1. **ADR-20R Jackson verification** → **Scenario A (global strict)**. **No code change for ADR-20R.** DTO field removal (`downgrade`) alone gives strict-mode rejection. D-6a-1 honored — global NOT flipped.
2. **ADR-19R PUT merge semantics for REQ-56** → **payload-only**. Matches existing validator signature shape; deterministic 400s; no facade two-pass; correct semantically for partial-update PUT.
3. **ADR-19R / D-6a-2 read wire shape for legacy FIXED tiers missing `periodValue`** → **OMIT**. Existing `@JsonInclude(NON_NULL)` on `TierValidityConfig` delivers it. Null and 0 forbidden by D-6a-2 forward guard.
4. **D-6a-1 Jackson fallback** → not invoked (Scenario A confirmed).
5. **D-6a-2 read wire shape** → locked (omit; see #3 above).

### Contradictions closed

| ID | Resolution | Confidence |
|---|---|---|
| **C-10** | Reject both string `"-1"` (code 9015) and numeric `-1` (code 9016). Precedence: 9016 fires before 9018 for numeric `-1` specifically; 9018 for other non-positive periodValues. | C6 |
| **C-11** | Scenario A (strict) confirmed via F1+F2 → **R14 CLOSED** | C6 |
| **C-13** | `TierRenewalNormalizer` exists (F4) | C7 — closed |
| **C-14** | List endpoint already envelope-wrapped (F6); no hoist reshape required by Rework #6a | C6 — closed |
| **C-16** | Canonical field is `isDowngradeOnPartnerProgramExpiryEnabled` (F5). PRD wording drift flagged to P11 Reviewer. Class A scanner rejects the canonical name. | C7 — closed |

### Factual correction applied to 01-architect.md

**ADR-19R** had `FIXED_LAST_UPGRADE` listed as a member of the FIXED family (3 values). This value **does not exist** in engine source. Corrected:
- FIXED family = 2 values: `{FIXED, FIXED_CUSTOMER_REGISTRATION}`
- SLAB_UPGRADE family = 2 values: `{SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC}`
- Total = 4 = complete engine enum

Edits applied: ADR-19R decision text, ADR-19R context paragraph, error-code table row 9018, Section 5 enum scope-lock row, deferred-to-Designer block, and Reviewer checklist bullet. 5 edits total.

### Files in scope for Phase 10 Developer (compile-safe list)

1. `tier/dto/TierCreateRequest.java` — remove `downgrade` field
2. `tier/dto/TierUpdateRequest.java` — remove `downgrade` field
3. `tier/validation/TierCreateRequestValidator.java` — 8 new `public static final int` constants (9011–9018); new `JsonNode rawBody` param; 8 new helper-call wirings; remove `validateDowngrade`
4. `tier/validation/TierUpdateRequestValidator.java` — same wiring as #3 (sans programId)
5. `tier/validation/TierEnumValidation.java` — 8 new static methods (§6a.4.3)
6. `resources/TierController.java` — add `JsonNode rawBody` parameter to `createTier` and `updateTier` handlers; pass to validator

**Files NOT in scope**: `TierDowngradeConfig.java` (class retained — other surfaces still use it); `TierValidityConfig.java` (field retained for read-wide contract); any Thrift IDL; any SQL schema; any engine-side code in `peb` / `emf-parent` / `Thrift` / `rule-engine`.

### Forward cascade payload → Phase 8 (QA)

- **Task**: test scenarios for 8 new reject codes 9011–9018 + DTO field removals + DTO→validator wiring change
- **Must cover**: 16 scenarios listed in `03-designer.md` §6a.9 (positive + negative + edge cases, including read of legacy FIXED tier without periodValue asserting field-omit)
- **Precedence rule to test**: for `periodValue: -1` (numeric, FIXED tier), 9016 fires **before** 9018 — SDET asserts this
- **Open contradictions**: **NONE** — all 5 resolved at Designer
- **Scope floor**: contract-hardening only, zero schema/Thrift/engine

### Reviewer forward flags (Phase 11) — augmented

- **P11-6a-3**: R14 **CLOSED** at Phase 7 Designer (Scenario A confirmed). No SDET reject-either-way tests required; SDET writes a single scenario asserting strict-mode 400 on unknown field.
- **P11-6a-4** (NEW): PRD/BA wording drift on `isDowngradeOnPartnerProgramDeLinkingEnabled` — canonical is `…ExpiryEnabled`. Reviewer checks `00-ba.md` / `00-prd.md` / rework-6a PRD text for residual drift and flags any remaining occurrence.

---

## Rework #6a — Phase 8 (QA — Test Scenarios) COMPLETE — 2026-04-22

**Artifact**: `04-qa.md` §"Rework #6a Delta — QA Test Scenarios" (appended after §Summary).

### Suspect-link triage over existing 89 scenarios

- **CONFIRMED**: 88 scenarios — no change required
- **UPDATE**: 1 scenario — TS-C11 (endDate-before-startDate) qualified to FIXED-family only; SLAB_UPGRADE-family now rejected at 9014 pre-binding
- **REGENERATE / OBSOLETE**: 0 — Rework #6a does not invalidate any existing scenario
- **NEW**: 26 scenarios (TS-6a-01..TS-6a-26) + 8 edge cases

### New scenarios by group

- **Group A (pre-binding reject scans)**: TS-6a-01..TS-6a-08 (8 scenarios) — Class A / Class B / eligibilityCriteriaType / string+numeric sentinels / legacy downgrade block / PRD-drift key
- **Group B (post-binding rejects)**: TS-6a-09..TS-6a-16 (8 scenarios) — SLAB_UPGRADE+startDate / FIXED-family periodValue / precedence 9016>9018 / renewal drift
- **Group C (negative controls)**: TS-6a-17..TS-6a-20 (4 scenarios) — must stay 2xx; PUT-parity; payload-only proof
- **Group D (read-side asymmetric)**: TS-6a-21..TS-6a-23 (3 scenarios) — GET legacy FIXED tier omits periodValue; read-wide downgrade preserved
- **Group E (cross-cutting)**: TS-6a-24..TS-6a-26 (3 scenarios) — unclassified Jackson, multi-key fail-fast order, tenant isolation

### Coverage — Rework #6a REQs (16/16)

All 16 REQs (REQ-21..REQ-56) have at least one scenario. 11 REQs have both POST and PUT coverage.

### Precedence rules locked for SDET

1. **Class A scanner runs BEFORE sentinel scanner** — TS-6a-25 asserts 9011 fires on Class A + sentinel combined payload
2. **Numeric -1 sentinel (9016) fires BEFORE FIXED-family positive guard (9018)** — TS-6a-14 is the precedence assertion
3. **Pre-binding scans catch only classified keys** — any OTHER unknown key falls through to Jackson strict-mode generic 400 (TS-6a-24)

### Total post-6a coverage

- **Scenarios**: 89 + 26 = **115**
- **ACs covered**: 52 + 16 = **68 (100%)**
- **Error codes covered**: 9001–9010 + 9011–9018 = **18**

### Forward cascade payload → Phase 8b (Business Test Gen)

- **Task**: suspect-link triage + map 26 new TS-6a-xx scenarios + 8 edge cases + 1 amendment (TS-C11) to BT-xx IDs
- **CONFIRMED BTs**: keep (traces to 88 CONFIRMED scenarios) — no regeneration
- **UPDATE BTs**: TS-C11 trace — amend expected-output text only; no logic change
- **NEW BTs**: required for all 26 TS-6a-xx + 8 edge cases; assign continuing IDs from last BT-xx
- **Each new BT-xx must trace to**: (a) one TS-6a-xx, (b) one REQ-xx (§6a.Q3), (c) one Designer interface method (§6a.4.3), (d) zero or more ADRs from §6a.Q6
- **Scope floor**: contract-hardening only

### Reviewer forward flags (Phase 11) — no change from Phase 7

R14 remains closed at Phase 7; P11-6a-4 (PRD drift scan) still live.

---

## Rework #6a — Phase 8b (Business Test Gen) COMPLETE — 2026-04-22

**Artifact**: `04b-business-tests.md` §"Section 7: Rework #6a Delta" (appended after "Rework #5 Status: COMPLETE" line).

### Suspect-link triage over existing 189 BTs

- **CONFIRMED**: 187 BTs — no change required (traceability unaffected by DTO field removal or new error codes)
- **UPDATE**: 2 BTs
  - **BT-17** — `shouldEnumerateStoredFieldsForClassAConfig` — remove `downgrade` from request fixture (DTO no longer accepts it); expected stored-field enumeration unchanged (field continues to be stored from legacy paths per ADR-21R read-wide)
  - **BT-62** — `shouldRejectEndDateBeforeStartDate` — qualify to FIXED-family only (SLAB_UPGRADE path now rejects pre-binding at 9014, not post-binding at 9002)
- **REGENERATE / OBSOLETE**: 0 — Rework #6a does not invalidate any existing BT
- **NEW**: 34 BTs (BT-190..BT-223) mapping 26 new TS-6a-xx + 8 edge cases

### New BTs by group (tracing to QA groups A–E + edge cases)

- **Group A (pre-binding reject scans — unit)**: BT-190..BT-198 (9 BTs) — `TierCreateRequestValidatorTest.java` → 9011/9012/9013/9015/9016/legacy-downgrade-block/PRD-drift-key
- **Group B (post-binding rejects + engine transform — unit/IT mix)**: BT-199..BT-209 (11 BTs) — `TierCreateRequestValidatorTest.java` + `TierStrategyTransformerTest.java` + `TierControllerIT.java` → 9014/9017/9018/precedence 9016>9018
- **Group C (negative controls — unit/IT)**: BT-210..BT-213 (4 BTs) — `TierCreateRequestValidatorTest.java` + `TierControllerIT.java` → must stay 2xx; PUT parity; payload-only proof
- **Group D (read-side asymmetric — IT)**: BT-214..BT-216 (3 BTs) — `TierControllerIT.java` → GET legacy FIXED omits periodValue; read-wide downgrade preserved; renewal normalizer
- **Group E (cross-cutting — unit)**: BT-217..BT-219 (3 BTs) — `TierCreateRequestValidatorTest.java` → unclassified-Jackson / Class A precedence over sentinel / tenant isolation
- **Edge cases**: BT-220..BT-223 (4 BTs) — `TierCreateRequestValidatorTest.java` + `TierUpdateRequestValidatorTest.java` → nested legacy keys, zero-value numerics, PUT-only payload-only semantics, empty-object coercion

### Coverage — Rework #6a post-8b

- **REQs**: 16/16 (REQ-21..REQ-56) → ≥1 BT each
- **Designer interface methods**: 8/8 (§6a.4.3 — `scanProgramLevelFields`, `scanScheduleField`, `scanEligibilityCriteriaType`, `scanStartDateOnSlabUpgrade`, `scanStringMinusOneSentinels`, `scanNumericMinusOneSentinels`, `scanRenewalCriteriaTypeDrift`, `scanFixedFamilyPositivePeriodValue`) → ≥1 BT each
- **ADRs**: 5/5 (ADR-19R, ADR-20R, ADR-21R, ADR-22R-new, ADR-23R-new) → ≥1 compliance BT each
- **Error codes**: 8/8 (9011–9018) → ≥1 positive BT + ≥1 precedence/negative BT

### Test file scope for Phase 9 (SDET — RED)

- **`TierCreateRequestValidatorTest.java`** — 23 new test methods (BT-190..201, 213, 217..220, 222, 223 minus the 3 that go to IT/transformer)
- **`TierUpdateRequestValidatorTest.java`** — 3 new test methods (BT-207, 208, 209)
- **`TierStrategyTransformerTest.java`** — 1 new test method (BT-211) — transform path asserts FIXED+missing-periodValue throws before hitting downstream
- **`TierControllerIT.java`** — 7 new IT methods (BT-210, 212, 214, 215, 216) + 2 re-asserts of BT-17, BT-62 under new semantics
- **Skeleton classes to create**: `TierPreBindingScanner.java` (scaffold), extend `TierEnumValidation.java` with 8 static stubs, `TierRenewalNormalizer.java` (already exists — F4/C7 evidence), `TierController#rawBody` parameter wiring

### Total post-Rework #6a test count

- **BTs**: 189 + 34 = **223** (~158 unit + ~74 integration; TDD unit-weighted)
- **Structured disagreement log**: 100% acceptance rate — no rework payload items challenged

### Forward cascade payload → Phase 9 (SDET — RED)

- **Task**: Author Java test code for 34 new BTs (BT-190..BT-223) + amend 2 UPDATE BTs (BT-17 remove `downgrade` fixture, BT-62 qualify to FIXED-family)
- **Mode**: REWORK — delta-aware (do NOT touch 187 CONFIRMED BT test methods)
- **RED confirmation requirements**:
  1. `mvn compile` PASS — skeleton classes compile; `TierPreBindingScanner` + 8 new `TierEnumValidation` stubs exist but throw `UnsupportedOperationException`
  2. `mvn test` on new BT-190..BT-223 → **ALL FAIL** (production code absent)
  3. `mvn test` on amended BT-17 + BT-62 → **FAIL** (expectations updated, production code still old)
  4. `mvn test` on 187 CONFIRMED BTs → **ALL PASS** (zero regression — triaged as unaffected)
- **Scope floor**: contract-hardening only — zero schema, zero Thrift, zero engine; tests live in `intouch-api-v3` repo only
- **Open contradictions**: **NONE** — all closed at Phase 7
- **Reviewer forward flags**: unchanged — R14 closed, P11-6a-4 (PRD drift scan) still live for Phase 11

---

## Rework #6a — Phase 9 (SDET — RED) COMPLETE — 2026-04-22

**Artifact**: `05-sdet.md` §"Rework #6a Delta — SDET RED" (Section 8, appended).

### Skeleton production code (compiles; throws UOE on call)

- **Consolidation decision**: All 8 new static methods placed on `TierEnumValidation.java` (existing class, promoted to `public final class`), not split across a new `TierPreBindingScanner` — design deviation from Designer §6a.4.3 split, accepted because tests don't care about class topology, only method signatures + exception contract. Phase 10 Developer may refactor or retain.
- **Naming deviation**: SDET used `validateNoClassAProgramLevelField`, `validateNoClassBScheduleField`, `validateNoEligibilityCriteriaTypeOnWrite`, `validateNoStartDateForSlabUpgrade`, `validateFixedFamilyRequiresPositivePeriodValue`, `validateNoStringMinusOneSentinel`, `validateNoNumericMinusOneSentinel`, `validateRenewalCriteriaTypeCanonical` — semantically equivalent to Designer `scan*` names.
- **Error code constants**: Declared in javadoc only (9011–9018); no `public static final int` constants — Phase 10 Developer must add these as first GREEN step so tests can assert by symbol.
- **DTO surgery**: `downgrade` field removed from `TierCreateRequest` and `TierUpdateRequest`. `TierDowngradeConfig` class retained (ADR-21R read-wide contract).
- **Controller wiring**: `TierController` accepts `@RequestBody JsonNode rawBody` on POST/PUT; `objectMapper.treeToValue(rawBody, TierCreateRequest.class)` wired but scanner invocations deferred to Phase 10 (TODO comments in place).

### Test files — 37 new @Test methods authored

| File | Location | New @Tests | BT range |
|---|---|---|---|
| `TierCreateRequestValidatorTest.java` (NEW) | `src/test/java/com/capillary/intouchapiv3/tier/validation/` | 28 | BT-190..206, 213–219, 220, 222 |
| `TierUpdateRequestValidatorTest.java` (NEW) | same dir | 5 | BT-207, 208, 209, 221, 223 |
| `TierStrategyTransformerTest.java` (APPENDED) | `src/test/java/com/capillary/intouchapiv3/tier/strategy/` | 1 | BT-211 |
| `TierControllerIntegrationTest.java` (NEW) | `src/test/java/integrationTests/` | 3 | BT-210, 212, 215 (dup — also covered as unit in CreateValidator) |
| `TierValidationServiceTest.java` (AMENDED) | `src/test/java/com/capillary/intouchapiv3/tier/` | 0 new + 1 amended | BT-62 qualification to FIXED-family only |

**UPDATE BTs handled**:
- **BT-17** — fixture cleanup (removed `.downgrade(...)` from request builder chain in relevant test)
- **BT-62** — `shouldRejectEndDateBeforeStartDateForFixedFamilyOnly` — test name + assertion scoped to FIXED-family only; sibling coverage for SLAB_UPGRADE → 9014 is captured in new TierCreateRequestValidatorTest BTs

### RED confirmation output (mvn compile + mvn test on JDK 17 Corretto)

```
mvn compile -DskipTests                     → BUILD SUCCESS
mvn test-compile                            → BUILD SUCCESS
mvn test -Dtest='Tier*Test' (ex. new CR/UR) → Tests run: 296, Failures: 1, Errors: 3, Skipped: 0
```

| Outcome | Count | Which | Classification |
|---|---|---|---|
| PASS (CONFIRMED, no regression) | 156+ | TierValidatorEnumTest(64), TierRenewalValidationTest(12), TierStrategyTransformerTest(80), etc. | Zero regression on 187 CONFIRMED BTs ✓ |
| RED-expected FAIL (UOE) | 4 | TierCreateRequestValidatorTest: BT-190, 192, 198, 217 — skeleton throws UnsupportedOperationException as planned | Expected RED — confirms skeleton wiring ✓ |
| RED-expected FAIL (amendment) | 1 | TierValidationServiceTest: BT-62 — FIXED-family qualification; production code not yet scoped | Expected RED ✓ |
| RED-expected ERROR (infra) | 3 | TierControllerIntegrationTest: all 3 IT tests — Testcontainers/Mongo not available in this run | Infra-gated; will re-run in Phase 10 or CI ✓ |
| RED-safe PASS (UOE-asserting) | 24 | TierCreateRequestValidatorTest BTs that assert `UnsupportedOperationException` instead of `InvalidInputException` | **Debt for Phase 10**: flip assertions from UOE to InvalidInputException + code constant during GREEN |

### Phase 10 Developer Debt (from SDET choices)

- **Error code constants** — Add `public static final int TIER_CLASS_A_PROGRAM_LEVEL_FIELD = 9011;` etc. on `TierEnumValidation` first; tests will then reference by symbol.
- **Assertion flip** — 24 RED-safe UOE asserters must flip to `InvalidInputException` + code assertion during GREEN implementation (per BT spec Expected Output).
- **Class topology decision** — Developer chooses: retain consolidated `TierEnumValidation` surface OR extract pre-binding methods onto `TierPreBindingScanner` per Designer §6a.4.3. Either is acceptable; tests only bind to method signature.
- **IT infra** — Phase 10 Developer runs `mvn test` with Testcontainers/Mongo available; 3 IT tests must turn GREEN.

### Forward cascade payload → Phase 10 (Developer — GREEN)

- **Task**: Replace 8 `UnsupportedOperationException` skeletons on `TierEnumValidation` with real validation logic per Designer §6a.4.3 and QA precedence rules (§6a.Q4)
- **Precedence rules to enforce**:
  1. Pre-binding scanners run BEFORE Jackson `treeToValue()` (§6a.4.5); unknown-but-unclassified keys fall through to Jackson strict-mode generic 400
  2. Class A scanner runs BEFORE sentinel scanner (9011 wins on combined Class A + sentinel payload — BT-219)
  3. Numeric -1 sentinel (9016) fires BEFORE FIXED-family positive guard (9018) — BT-204
  4. Scanner invocation order in controller: Class A (9011) → Class B (9012) → eligibilityCriteriaType (9013) → string sentinels (9015) → numeric sentinels (9016) → Jackson `treeToValue` → post-binding checks 9014/9017/9018
- **Error code mapping**: 9011 Class A, 9012 Class B, 9013 eligibilityCriteriaType, 9014 startDate+SLAB_UPGRADE, 9015 string "-1", 9016 numeric -1, 9017 renewal drift, 9018 FIXED-family missing positive periodValue
- **Code constant requirement**: Add `public static final int` constants matching Designer §6a.4.1 names so tests can assert by symbol (not magic number)
- **Scope floor**: contract-hardening only — zero schema, zero Thrift, zero engine
- **GREEN exit criteria**: all 37 new BTs PASS + BT-17 + BT-62 PASS + 187 CONFIRMED BTs remain PASS (zero regression)

### Reviewer forward flags (Phase 11) — unchanged

R14 CLOSED at Phase 7; P11-6a-4 (PRD drift scan) still live.

---

## Rework #6a — Phase 10 (Developer — GREEN) COMPLETE — 2026-04-22

### Outcome
- **mvn compile**: BUILD SUCCESS (JDK 17.0.17-amzn / Corretto)
- **mvn test regression sweep (non-IT)**: **326 tests, 0 failures, 0 errors, 0 skipped** ✓
- **New contract tests (unit)**: all 37 new BTs PASS (28 in `TierCreateRequestValidatorTest`, 5 in `TierUpdateRequestValidatorTest`, 1 in `TierStrategyTransformerTest`, 2 BT-62 sibling variants in `TierValidationServiceTest`)
- **IT tests**: 3 tests in `TierControllerIntegrationTest` error out with `IllegalState: Failed to load ApplicationContext` — Testcontainers/Docker not available in this environment. Infra-gated, not implementation-gated.
- **Zero regression**: all 187 CONFIRMED BTs remain PASS.

### Production files modified
| File | Change |
|------|--------|
| `TierEnumValidation.java` | +8 `public static final int` code constants (9011–9018) + 8 method bodies replacing UOE skeletons; +3 private canonical-key lists + 4 private recursive scan helpers (~+130 lines net) |
| `TierCreateRequestValidator.java` | Wired `validate(req, rawBody)` canonical two-arg form; 5 pre-binding scans + 3 post-binding scans; new `validateEndDateNotBeforeStartDate` helper for BT-62 FIXED-family ordering; added `@Deprecated validate(request)` single-arg overload delegating with `rawBody=null` |
| `TierUpdateRequestValidator.java` | PUT parity wiring of 5 pre-binding + 3 post-binding scans; same `@Deprecated` single-arg overload |

### Test files modified
| File | Change |
|------|--------|
| `TierCreateRequestValidatorTest.java` | 21 RED-safe UOE assertions flipped to `InvalidInputException` / `assertDoesNotThrow` |
| `TierUpdateRequestValidatorTest.java` | 3 RED-safe UOE assertions flipped |
| `TierValidationServiceTest.java` | 1 BT-62 sibling assertion flipped |

### Design decisions locked (C5+)
- **Class topology**: Developer retained SDET's consolidated `TierEnumValidation` class (did not split to `TierPreBindingScanner`). Tests bind to method signatures only — topology is a reversible refactor.
- **Error codes as constants**: 8 `public static final int` constants declared on `TierEnumValidation`. `InvalidInputException` has no `int code` constructor (confirmed via `InvalidInputException.java:11`) — codes are carried in the message string, not a structured field. Phase 10b may decide to widen the exception contract.
- **Scanner invocation order (validator layer)**: Class A → Class B → eligibilityCriteriaType → string sentinels → numeric sentinels → post-binding (9014 → 9018 → BT-62 ordering → renewal → 9017). Confirmed in `TierCreateRequestValidator.validate(req, rawBody)` lines 65–93.
- **BT-62 qualification**: Only FIXED-family tiers reach the endDate/startDate ordering guard; SLAB_UPGRADE-family is blocked earlier at 9014 pre-binding. Lexicographic ISO-8601 UTC string comparison.
- **DTO hard-flip**: `TierCreateRequest` and `TierUpdateRequest` no longer expose `downgrade` on write. `TierDowngradeConfig` class retained — used only on read via `TierStrategyTransformer` for ADR-21R read-wide contract.

### P1 PRODUCTION WIRING GAP — evidence confirmed, flagged forward to Phase 10b
**Gap**: Pre-binding scans 9011, 9012, 9013, 9015, 9016 are silently skipped on the production HTTP path.

**Evidence chain** (C6):
1. `TierController.java:93` — `@PostMapping` receives `@RequestBody JsonNode rawBody` but does NOT pass rawBody to facade. Line 90 still holds `TODO Phase 10: invoke TierPreBindingScanner.scan*(rawBody) in fail-fast order.`
2. `TierController.java:103` — `tierFacade.createTier(user.getOrgId(), request, userId)` signature has no `rawBody` parameter.
3. `TierFacade.java:227` — `createValidator.validate(request)` is called (single-arg, @Deprecated).
4. `TierFacade.java:262` — `updateValidator.validate(request)` — same single-arg call on update path.
5. `TierCreateRequestValidator.java:131` — the `@Deprecated validate(request)` overload delegates to `validate(request, null)` — pre-binding scans are guarded by `if (rawBody != null)` and thus skipped.

**Net effect in production**: Class A, Class B, eligibilityCriteriaType, and -1 sentinel payloads currently pass through to Jackson strict-mode (may surface as generic 400, not the specific 9011–9016 codes). Only post-binding 9014, 9017, 9018 fire as designed.

**Why unit tests still pass**: Unit tests in `TierCreateRequestValidatorTest` / `TierUpdateRequestValidatorTest` call the canonical two-arg `validate(request, rawBody)` directly, bypassing the facade.

**Fix path** (deferred to Phase 10b for architectural review):
- Option A (minimal): Widen `TierFacade.createTier/updateTier` signatures to accept `JsonNode rawBody`; controller passes rawBody from request body; facade calls `validate(request, rawBody)`.
- Option B (cleaner): Move scanner invocation into the controller directly, before calling facade; facade keeps its current narrow signature.
- Option C (interceptor): Add a Spring interceptor / `@InitBinder` that runs scanners before controller method invocation.

C4 severity — reversible via PR, but security/contract-integrity impact is real (Class A rejection acceptance criteria unmet on production path).

### Forward cascade payload → Phase 10b (Backend Readiness)

| Priority | Concern | Evidence | What to verify |
|----------|---------|----------|---------------|
| **P1** (CRITICAL) | Controller wiring gap — pre-binding scans silently skipped on production path | `TierController.java:90,103,110,117` + `TierFacade.java:227,262` + `TierCreateRequestValidator.java:131` | Decide fix path (A/B/C above); wire rawBody through facade OR move scans to controller OR add interceptor |
| **P2** | Error response envelope — `InvalidInputException` → 400 but codes 9011–9018 live in message string only | `TierControllerExceptionMappingTest` — 2 passing tests; no per-code routing | Verify Spring MVC handler at `TargetGroupErrorAdvice` serialises `InvalidInputException` consistently; decide whether to widen exception contract with `int code` field |
| **P3** | IT infra — `TierControllerIntegrationTest` 3 tests error on ApplicationContext load | Testcontainers/Docker unavailable in local dev env | Phase 10b runs in CI or with Docker daemon; confirm BT-210, 212, 215 PASS GREEN |
| **P4** | Date format strictness — lexicographic ISO-8601 UTC comparison only | `TierCreateRequestValidator.java:114–120` | Verify all client date inputs arrive as ISO-8601 UTC (e.g. `2026-06-01T00:00:00Z`); decide whether to use `Instant.parse()` for stricter parsing |
| **P5** | Performance — new recursive tree scanners are O(n) on JSON node count | `TierEnumValidation.java` scan helpers; typical payload < 50 nodes | Smoke-test with a deeply nested adversarial payload; confirm no pathological recursion |

### Reviewer forward flags (Phase 11) — unchanged
- **P11-6a-1** — R13 external-consumer residual flag (live)
- **P11-6a-4** — PRD drift scan (live)
- **R14** — CLOSED at Phase 7

---

## Rework Cycle 1 — Phase 10b Blocker Fixes COMPLETE — 2026-04-22

### P1 BLOCKER FIX — Controller Wiring (C7, fixed)

`TierFacade.createTier` and `updateTier` signatures widened to accept `JsonNode rawBody`. `TierController` now passes `rawBody` to both facade methods. Facade calls two-arg `validate(request, rawBody)` on both validators. Pre-binding scans 9011, 9012, 9013, 9015, 9016 now fire on every production HTTP POST and PUT. _(Developer — Rework Cycle 1)_

Files changed: `TierFacade.java` (signature widening + validate call), `TierController.java` (pass rawBody, remove TODO comments), `TierFacadeTest.java` (15 call sites updated to pass null rawBody).

### P2 BLOCKER FIX — Error Code Wire Contract (C7, fixed)

8 throw sites in `TierEnumValidation.java` now prefix messages with `[9011]`–`[9018]` bracket using the `public static final int` constants (G-13.4 pattern). `TargetGroupErrorAdvice.handleInvalidInputException` now extracts the bracket-prefixed code via regex `^\[(\d+)\]\s*(.*)$` and emits `ApiError(longCode, strippedMsg)` directly — bypassing `MessageResolverService` which returns `999999L` for unregistered i18n keys. Wire `errors[0].code` is now `9011`–`9018` for contract-hardening rejects. Backward compatible: unbracketed messages fall through to existing path. _(Developer — Rework Cycle 1)_

Files changed: `TierEnumValidation.java` (8 throw sites), `TargetGroupErrorAdvice.java` (extractor added), `TierControllerIntegrationTest.java` (BT-215 INFO-3 assertion added).

### Codebase Behaviour updates
- `TierFacade.createTier(long, TierCreateRequest, JsonNode, String)` — new 4-arg signature; `rawBody` forwarded to validator. _(Developer — Rework Cycle 1)_
- `TierFacade.updateTier(long, String, TierUpdateRequest, JsonNode, String)` — new 5-arg signature. _(Developer — Rework Cycle 1)_
- `TargetGroupErrorAdvice.handleInvalidInputException` — bracket extractor fires before `MessageResolverService`; only bracketed messages get structured code; all other messages unchanged. _(Developer — Rework Cycle 1)_
- `@Deprecated validate(request)` single-arg overloads on both validators remain; now dead code on the production path (tracked as INFO I2). _(Developer — Rework Cycle 1)_

### Verification
- `mvn clean compile`: BUILD SUCCESS
- `mvn test-compile`: BUILD SUCCESS
- `mvn test -Dtest='Tier*Test'` unit tests: 326 passed, 0 failures, 0 errors (17 suites)
- IT tests (3): pre-existing Docker/Testcontainers infra error — P3 WARNING unchanged. BT-215 `code == 9011` assertion added; will verify GREEN in CI.

### Key Decisions
- Option A (widen facade signature) chosen over B (move scans to controller) — keeps all validation in one place, minimal blast radius. _(Developer — Rework Cycle 1)_
- Option X1 (bracket prefix + extractor) chosen over X2 (widen InvalidInputException) — no change to exception class, backward compatible, aligns with G-13.4 guardrail. _(Developer — Rework Cycle 1)_
- `rawBody=null` in TierFacadeTest: correct for unit-test scope; pre-binding scans covered directly by TierCreateRequestValidatorTest/TierUpdateRequestValidatorTest. _(Developer — Rework Cycle 1)_

### Forward cascade → abbreviated Phase 10b re-gate
- Verify P1 fix: grep for single-arg `validate(request)` on production path — must be zero.
- Verify P2 fix: confirm `errors[0].code` = 9011 on Class A reject (wire test or code review of extractor).
- Confirm BT-215 GREEN in CI (requires Docker).
- P3 (IT infra), P4 (date format), P5 (scanner perf) — status unchanged from Phase 10.

## Rework Cycle 1 — VERIFIED & CLOSED — 2026-04-23

Independent trust-but-verify pass confirmed Developer's rework cycle 1 claims at C7 via direct file reads + re-running `mvn test -Dtest='Tier*Test'`.

### P1 wiring gap — CLOSED
- `TierFacade.java` L21: `import com.fasterxml.jackson.databind.JsonNode;` present.
- `TierFacade.java` L227: `createTier(long orgId, TierCreateRequest request, JsonNode rawBody, String userId)` — widened signature verified.
- `TierFacade.java` L228: `createValidator.validate(request, rawBody);` — two-arg call verified.
- `TierFacade.java` L262: `updateTier(long orgId, String tierId, TierUpdateRequest request, JsonNode rawBody, String userId)` — widened signature verified.
- `TierFacade.java` L263: `updateValidator.validate(request, rawBody);` — two-arg call verified.
- `TierController.java` L83-91/L107-110: TODO comments replaced with Javadoc describing rawBody forwarding for scans 9011-9016. TODO comments GONE.
- `TierController.java` L103: `tierFacade.createTier(user.getOrgId(), request, rawBody, userId);` — rawBody passed verified.
- `TierController.java` L122: `tierFacade.updateTier(user.getOrgId(), tierId, request, rawBody, userId);` — rawBody passed verified.
- **Net effect**: Pre-binding scans 9011, 9012, 9013, 9015, 9016 now fire on every production HTTP POST/PUT path (previously silently skipped because facade called single-arg overload without raw tree).

### P2 error code wire contract — CLOSED
- `TierEnumValidation.java` L176-183: 8 `public static final int` constants declared (TIER_CLASS_A_PROGRAM_LEVEL_FIELD=9011 ... TIER_FIXED_FAMILY_MISSING_PERIOD_VALUE=9018).
- `TierEnumValidation.java` L244-246 (9011 Class A): `throw new InvalidInputException("[" + TIER_CLASS_A_PROGRAM_LEVEL_FIELD + "] ...")` — verified.
- `TierEnumValidation.java` L270-272 (9012 Class B): bracket prefix verified.
- `TierEnumValidation.java` L296-297 (9013 eligibilityCriteriaType): bracket prefix verified.
- `TierEnumValidation.java` L323-325 (9014 startDate on SLAB_UPGRADE): bracket prefix verified.
- `TierEnumValidation.java` L351-353 (9018 FIXED family missing periodValue): bracket prefix verified.
- `TierEnumValidation.java` L385-387 (9015 string -1 sentinel): bracket prefix verified.
- `TierEnumValidation.java` L421-423 (9016 numeric -1 sentinel): bracket prefix verified.
- `TierEnumValidation.java` L447-451 (9017 renewal criteriaType drift): bracket prefix verified.
- `TargetGroupErrorAdvice.java` L87-101: regex `^\[(\d+)\]\s*(.*)$` matcher → `new ApiError(Long.parseLong(m.group(1)), m.group(2))` → `ResponseEntity.status(BAD_REQUEST).body(body)` — verified. Fall-through path to `error(BAD_REQUEST, e)` at L101 preserved for non-bracketed messages (backward compatible).
- **Out of scope untouched**: 4 pre-existing throws at L98/L103/L108/L125/L140/L156 (kpiType, upgradeType, expressionRelation, periodType, downgrade.target, conditions[].type) correctly NOT prefixed — per Rework #6a scope floor.

### Verification evidence
- `mvn test -Dtest='Tier*Test'` (re-run 2026-04-23, independent of subagent): **329 run, 0 failures, 3 errors, 0 skipped** → **326/0/0 non-IT**.
- The 3 errors are `TierControllerIntegrationTest.shouldOmitPeriodValueOnGetForLegacyFixedTier` and 2 others — all `IllegalStateException: Failed to load ApplicationContext` (Testcontainers/Docker unavailable locally). Classified P3 WARNING, unchanged from Phase 10 pre-rework state.
- Developer's claim of 326/0/0 matches independent re-run exactly.

### Status transition
- Rework Cycle 1: `resolved: true` (pipeline-state.json updated).
- Phase 10b blockers P1 + P2: **FIXED at code level**. Abbreviated re-gate pending to flip verdict NOT READY → READY WITH WARNINGS.
- P3/P4/P5 WARNINGS carry forward unchanged.

### Next step
- Run abbreviated Phase 10b gate focused on P1 + P2 only. If clean → Phase 10c Compliance. If new issues → another rework cycle.

## Rework #6a — Phase 10c (Compliance / Gap Analysis) COMPLETE — 2026-04-23

### Verdict: COMPLIANT WITH FINDINGS
- 0 CRITICAL / 0 HIGH / 1 MEDIUM / 2 LOW / 1 INFO. **No blockers for Phase 11.**
- Scope: 5 ADRs (ADR-17R through ADR-21R), 5 GUARDRAILS (G-07, G-12, G-13.1, G-13.2, G-13.4), 11 Designer interface prescriptions, and Rework Cycle 1 wiring fixes.

### ADR scorecard
- **ADR-17R PASS (C7)** — Codes 9011–9018 declared as `public static final int` at `TierEnumValidation.java:176-183`. Legacy 9001–9010 preserved untouched at `TierCreateRequestValidator.java:34-42`. Zero overlap. `api-handoff.md` §10.12 aligned with code.
- **ADR-18R PASS (C6)** — `TierValidityConfig.java:25-26` holds `periodType` / `periodValue` as per-tier wire fields; no program-level mutation for validity on write path.
- **ADR-19R PASS (C7)** — FIXED family hard-coded as {`FIXED`, `FIXED_CUSTOMER_REGISTRATION`} at `TierEnumValidation.java:348`. REQ-56 wired on both POST (`TierCreateRequestValidator.java:88`) and PUT (`TierUpdateRequestValidator.java:62`). PUT validator is payload-only (no facade/repo injection).
- **ADR-20R PASS (C6)** — Designer §6a.2.1 locked Scenario A; `IntouchApiV3Application.java:95-99` declares `new ObjectMapper()` preserving Jackson native strict default (FAIL_ON_UNKNOWN_PROPERTIES=true). No per-DTO opt-out on TierCreateRequest/TierUpdateRequest. Pattern proof: 36 DTOs repo-wide carry `@JsonIgnoreProperties(ignoreUnknown=true)` — which would not exist if default were permissive.
- **ADR-21R PASS (C7)** — Write DTOs (`TierCreateRequest.java:23-36`, `TierUpdateRequest.java:19-28`) hold ONLY per-tier fields; `downgrade` block removed. Read model (`UnifiedTierConfig.java:74`) retains `TierDowngradeConfig downgrade` for read-wide. Class A/B scanners enforce write-narrow rejection.

### Guardrails scorecard
- **G-12 (pre-binding validation)**: PASS — scans fire before validator business logic (F-10c-1 notes semantic vs literal ordering).
- **G-13.1 (codebase exception types)**: PASS — all 8 throw sites use `InvalidInputException`.
- **G-13.2 (no try-catch in controllers)**: PASS — `TierController.java:92-124` declarative exception propagation only.
- **G-13.4 (numeric error code on wire)**: PASS — `TargetGroupErrorAdvice.java:88-100` regex extractor emits `ApiError(code, strippedMsg)` as Long.
- **G-07 (tenant isolation)**: PASS — spot-check of all 8 throw messages — no `orgId`, no user identity, no tenant identifier leakage.

### Designer interface compliance: 11/11 EXACT at C7
- 8 static validator methods in TierEnumValidation — all signatures match §6a.4.3 exactly.
- `TierCreateRequestValidator.validate(TierCreateRequest, JsonNode)` at L65-93 — canonical two-arg form; pre-binding scan order (Class A → B → ECT → string → numeric) + post-binding.
- `TierUpdateRequestValidator.validate(TierUpdateRequest, JsonNode)` at L42-66 — identical pattern, payload-only.
- Deprecated single-arg overloads remain as dead code (INFO — F-10c-2, tracked as I2 in 10b closure).

### Findings (non-blocking)
- **F-10c-1 (LOW)** — Pre-binding scans execute AFTER `treeToValue` at controller (semantic vs literal). No functional consequence because Jackson strict mode independently rejects unknown keys. Documented in api-handoff §5.3. No fix required.
- **F-10c-2 (INFO)** — Deprecated single-arg `validate(request)` overloads at `TierCreateRequestValidator.java:124-133` and `TierUpdateRequestValidator.java:68-77`. Tech-debt; no production caller (verified C7 in Rework Cycle 1). User question Q2.
- **F-10c-3 (LOW)** — Error-message diagnostics content (G-07 residual). No action required.
- **F-10c-4 (MEDIUM)** — ADR-20R strict-mode is fragile to future `Jackson2ObjectMapperBuilder` migration. If a future refactor replaces the hand-rolled `@Bean ObjectMapper` with Spring Boot's builder path, `FAIL_ON_UNKNOWN_PROPERTIES` silently flips to `false`, disabling the Jackson fallback for unknown keys not covered by pre-binding scanners. User question Q1: defensive `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` now OR SDET coverage confirmation at Phase 11.

### Suggested ArchUnit rules (for future hardening)
- `TierValidatorPackageIsolation` — classes in `tier.validation` must not depend on `tier.strategy`.
- `TierErrorCodeBandRange` — error code constants in `TierEnumValidation` must be in range 9011-9020 (enforces ADR-17R at CI time).
- `ObjectMapperStrictMode` — the @Bean method returning ObjectMapper in IntouchApiV3Application must either explicitly call `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` OR not call `configure(FAIL_ON_UNKNOWN_PROPERTIES, false)` (catches F-10c-4 regression vector).
- `InvalidInputExceptionForAllRejects` — in `tier.validation.*`, throw sites must only throw `InvalidInputException` or its subclasses.
- `WriteNarrowRequestShape` — classes named `Tier*Request` in `tier.dto.*` must not declare fields named `isActive`, `reminders`, `schedule`, `nudges`, `notificationConfig`, `eligibilityCriteriaType`, `downgrade`.

### Phase 10d — SKIPPED (no schema changes)
Rework #6a is contract-hardening only: zero schema, zero Thrift, zero engine. Phase 7b (Migrator) was skipped — no `01b-migrator.md` artifact exists. Per pipeline protocol, Phase 10d runs only if Phase 7b ran.

### User decisions pending before Phase 11
- **Q1 (F-10c-4)**: Defensive `configure(FAIL_ON_UNKNOWN_PROPERTIES,true)` now, OR SDET-test verification at Phase 11, OR defer.
- **Q2 (F-10c-2)**: Remove deprecated single-arg overloads now (small commit), OR defer to cleanup ticket.

### Forward cascade to Phase 11 Reviewer
- R13 (external consumer residual) from Phase 6a Impact Analysis — unchanged.
- P3 (Docker IT infra) — pre-merge CI gate, needs GREEN BT-215 verification.
- P4 (date format lexicographic compare) — non-canonical ISO-8601 risk, carried forward.
- P5 (scanner recursion depth) — negligible, carried forward.
- F-10c-4 (ADR-20R fragility) — carried forward pending Q1 answer.
- P11-6a-1 (external consumer audit) — flag per ADR-21R residual.

---

## Phase 11 — Reviewer (Rework #6a) [2026-04-23]

### Verdict: APPROVED WITH WARNINGS

Build: 311+ tier unit tests PASS (Java 17.0.17-amzn, Maven 3.5.4 -B). Integration tests skipped — Docker unavailable (pre-existing P3).

### R11-1 (WARNING) — api-handoff.md misattributes `downgrade` rejection to code 9011
**Confidence: C7.**
`CLASS_A_CANONICAL_KEYS` (TierEnumValidation.java:190-199) does NOT include `"downgrade"`. Test BT-197 explicitly asserts the Class A scanner must NOT throw for a body containing `"downgrade"`. The api-handoff.md §5.3 / §5.4 / §10.19 (4 locations) incorrectly states that sending `"downgrade"` returns code 9011. The actual mechanism is Jackson strict-mode → generic 400. UI consumers routing on `errors[0].code === 9011` for the downgrade round-trip guard will mis-route. **Required action:** correct api-handoff.md before deploy.

### R11-2 (WARNING) — ADR-20R fragility not verified (F-10c-4 carry-forward)
**Confidence: C6.**
`IntouchApiV3Application.java:94-99`: `@Bean ObjectMapper` = `new ObjectMapper()` + `setTimeZone()` only. No `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)`. No `spring.jackson.deserialization.fail-on-unknown-properties=true` in application.properties. Jackson 2.x default: `FAIL_ON_UNKNOWN_PROPERTIES=false`. `TierController.java:97,117` calls `objectMapper.treeToValue()` using this bean. If default applies, `"downgrade"` and other unclassified unknowns are silently dropped — ADR-20R write-narrow guarantee is unverified. BT-197 only tests the scanner (does not test `treeToValue()` end-to-end). User decision Q1=c ("verify via test") is NOT yet fulfilled. **Pre-merge gate:** confirm ObjectMapper strictness or add explicit `configure()` call.

**Note on Designer F1 claim:** The Designer Phase 7 F1 finding ("Global Jackson is STRICT by default") inferred this from the 35+ opt-out DTOs with `@JsonIgnoreProperties(ignoreUnknown=true)`. This inference is not conclusive — see R11-2. Session-memory F1 should be treated as UNVERIFIED until R11-2 is closed.

### Session-memory Q-OP-1 table (P11-6a-4)
The Q-OP-1 error code allocation table (lines ~498-506) is SUPERSEDED by Designer Phase 7 LLD. Code and api-handoff.md match Designer Phase 7 (final allocation). The Q-OP-1 table is a documentation artifact only; no runtime impact.

### Open questions forwarded (Q11-1)
Which resolution is preferred for R11-2?
- (a) Add `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` to ObjectMapper bean — global scope, verify 35+ opt-out DTOs
- (b) Add `@JsonIgnoreProperties(ignoreUnknown=false)` to `TierCreateRequest` + `TierUpdateRequest` only — scoped
- (c) Write BT-197b end-to-end treeToValue test and assert UnrecognizedPropertyException; accept GREEN as confirmation
- (d) Accept permissive silent-drop and update api-handoff to remove 9011 attribution for `downgrade`

### Pre-merge gates
- [ ] R11-1: api-handoff.md corrected (4 locations)
- [ ] R11-2: ObjectMapper strict-mode verified or explicit configure() added
- [ ] P3: TierControllerIntegrationTest GREEN in CI

### Pre-deploy gate
- [ ] R13 / P11-6a-1: Staging access-log scan for codes 9001-9010
- P11-6a-4 (PRD drift scan) — verify api-handoff.md aligned with PRD/BA.

---

## Rework #6a — Phase 11 CLOSURE — 2026-04-23 (same day)

**User decisions logged:**
- **R11-1 routing:** `[M] Manual` — docs-only edit of `api-handoff.md`
- **Q11-1 (R11-2):** `(b+c)` — tier-scoped `@JsonIgnoreProperties` + BT-197b empirical binding-layer test

### R11-1 CLOSED — at C7

**What was corrected:** 7 misattributions in `api-handoff.md` claiming `downgrade` returns code 9011. Reality: `downgrade` is NOT in `CLASS_A_CANONICAL_KEYS` — rejected by Jackson strict-mode (`UnrecognizedPropertyException` → generic HTTP 400). The Reviewer initially identified 4 affected locations; trust-but-verify via grep found 7 actual misattributions plus 3 correctly-attributed references (L547, L1441, L1499) which were left intact.

**Lines corrected** (8 edits across 7 logical sections):

| # | Line | Section | Fix |
|---|---|---|---|
| 1 | L361 | §5.3 write-narrow callout | Attribute to Jackson strict-mode; explain nested-Class-A-key 9011 nuance |
| 2 | L389 | §5.3 evidence footer | List the 8 actual Class A keys; explicitly state `downgrade` not in set |
| 3 | L409 | §5.3 field-validation table | Split into 2 rows (bare `downgrade` Jackson 400 vs nested Class A 9011) |
| 4 | L527 | §5.3 9011–9018 scanner table | Clarifying note on bare-vs-nested rejection path |
| 5 | L570 | §5.4 PUT body narrative | Corrected PUT-parity mechanism description |
| 6 | L1205 | §6.7 `TierDowngradeConfig` | Two-layer rejection model documented |
| 7 | L1495 | §10.19 asymmetry table | `downgrade` row changed to Jackson 400 |
| 8 | L1506 | §10.19 round-trip warning | Fixed round-trip guidance; added note on potential nested-flag 9011 trigger |

**Evidence basis:**
- `TierEnumValidation.java:190-199` — `CLASS_A_CANONICAL_KEYS` has exactly 8 keys; `"downgrade"` is NOT among them
- BT-197 comment at `TierCreateRequestValidatorTest.java:140-144` already documents the correct mechanism

### R11-2 CLOSED — at C7 via (b+c)

**(b) Annotation added to tier write DTOs:**

| File | Change |
|---|---|
| `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/dto/TierCreateRequest.java` | + `import com.fasterxml.jackson.annotation.JsonIgnoreProperties;` + type-level `@JsonIgnoreProperties(ignoreUnknown = false)` |
| `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/dto/TierUpdateRequest.java` | Same annotation, same Javadoc extension |

**Why tier-scoped, not global:** Option (a) would have required changes to the shared `@Bean ObjectMapper` in `IntouchApiV3Application` — risk of breaking the 35+ DTOs that opt out of strict-mode via `@JsonIgnoreProperties(ignoreUnknown=true)`. Option (b) gives the tier contract its own guarantee at zero blast radius. **Key property:** a type-level `@JsonIgnoreProperties` annotation cannot be overridden by the global Spring Boot property `spring.jackson.deserialization.fail-on-unknown-properties` — so ADR-20R + ADR-21R (write-narrow asymmetry) are now environmentally resilient.

**This supersedes Designer F1 (UNVERIFIED) with a concrete local guarantee at C7.**

**(c) BT-197b — 4 new empirical tests:**

| Test ID | File | Method | Assertion |
|---|---|---|---|
| BT-197b (POST) | `TierCreateRequestValidatorTest.java` | `shouldRejectLegacyDowngradeBlockAtJacksonBindingLayer` | `treeToValue({"programId":1,"name":"Gold","downgrade":{"target":"SINGLE"}}, TierCreateRequest.class)` → `UnrecognizedPropertyException` with `propertyName == "downgrade"` |
| BT-197b-control (POST) | Same file | `shouldAcceptKnownFieldsAtJacksonBindingLayer` | Happy-path binding of well-formed payload |
| BT-197b (PUT) | `TierUpdateRequestValidatorTest.java` | `shouldRejectLegacyDowngradeBlockAtJacksonBindingLayerOnPut` | Same assertion on PUT partial-update DTO |
| BT-197b-control (PUT) | Same file | `shouldAcceptKnownFieldsAtJacksonBindingLayerOnPut` | Happy-path partial PUT |

BT-197b targets the **Jackson binding layer** (the annotation) while BT-197 (pre-existing) targets the **validator layer** (scanner's negative control). Together they pin the contract from both directions. The `assertEquals("downgrade", ex.getPropertyName())` check guards against the test passing for the wrong reason.

### Verification — C7

```
JAVA_HOME=~/.sdkman/candidates/java/17.0.17-amzn mvn test -f intouch-api-v3/pom.xml \
  -Dtest='TierCreateRequestValidatorTest,TierUpdateRequestValidatorTest'
  → TierCreateRequestValidatorTest: 30 tests, 0 failures, 0 errors (was 28, +2 BT-197b)
  → TierUpdateRequestValidatorTest:  7 tests, 0 failures, 0 errors (was 5, +2 BT-197b)
  Total: 37 PASS  BUILD SUCCESS

Regression sweep:
  mvn test -Dtest='com.capillary.intouchapiv3.tier.**'
  → 354 tests, 0 failures, 0 errors, 0 skipped  BUILD SUCCESS
  → no regression from the annotation across the tier package
```

### Phase 11 Final Verdict — **APPROVED**

Upgraded from "APPROVED WITH WARNINGS" to **APPROVED** after both warnings closed at C7.

### Pre-merge gates — status update

- [x] R11-1: api-handoff.md corrected (7 misattribution locations; 3 correct references preserved)
- [x] R11-2: Tier-scoped `@JsonIgnoreProperties` annotation + BT-197b regression cover (supersedes Designer F1)
- [ ] P3 / W1: `TierControllerIntegrationTest` GREEN in Docker-capable CI (deferred to CI pipeline; merge blocker)
- [ ] P4 / W2: Date-format consistency on read path
- [ ] P5 / I1: Scanner performance guard on large payloads (INFO — post-merge acceptable)

### Pre-deploy gate

- [ ] R13 / P11-6a-1: Staging access-log scan for legacy codes 9001-9010 consumers

**Rework #6a Cycle 1 — CLOSED** on 2026-04-23. Proceeding to Phase 12 Blueprint.

---

## Phase 12: Blueprint — Rework #6a Cycle 1 Closure (2026-04-23)

**Scope decision (C6):** Produced a **focused closure blueprint** (`rework-6a-cycle-1-closure.html`, 29.7 KB, 592 lines) rather than regenerating the full `tiers-crud-blueprint.html`. Rationale: Rework #6a is a cycle-based rework on a completed pipeline; the original stakeholder-facing blueprint already exists and remains valid for the feature-level view. The closure blueprint captures the delta — what Phase 11 Cycle 1 changed and why — so stakeholders reviewing the rework don't have to re-read the full-run blueprint.

### Closure blueprint structure

1. **Header** — Rework #6a Cycle 1 identifier, ticket, final verdict (APPROVED), date
2. **Executive summary** — one-paragraph outcome: R11-1 + R11-2 resolved, both at C7 evidence
3. **R11-1 (api-handoff docs fix)** — 7 misattribution locations corrected, 3 correct references preserved, evidence-backed diff summary
4. **R11-2 (@JsonIgnoreProperties + BT-197b)** — decision rationale (write-narrow hardening, environment-drift defence), tier-scoped annotation approach (not global property toggle), regression probe BT-197b (POST + PUT variants with negative controls)
5. **Evidence register** — confidence levels per claim, primary sources cited (file:line, test output, mvn verify)
6. **Pre-merge gate status** — closed items (R11-1, R11-2) vs deferred items (P3/W1, P4/W2, P5/I1) with clear routing
7. **Pre-deploy gate** — R13/P11-6a-1 staging access-log scan task
8. **Rework artifact map** — links to the 9 pipeline artifacts touched during Cycle 1 (07-reviewer.md, api-handoff.md, session-memory.md, pipeline-state.json + 4 code files in intouch-api-v3 + 1 new test file)
9. **Final verdict** — APPROVED with evidence trail

### Full pipeline stats (tier feature, original fresh run + Rework #6a Cycle 1)

- **Phases completed**: 13/13 (original run) + Rework Cycle 1 closed
- **Artifacts generated (tier/)**: ~35 .md files + 3 HTML (live dashboard, api-handoff-docs, tiers-crud-blueprint) + 1 rework closure HTML
- **Code files modified (intouch-api-v3)**: 4 production (TargetGroupErrorAdvice, TierController, TierUpdateRequest, TierEnumValidation) + 2 test (TierCreateRequestValidatorTest, TierUpdateRequestValidatorTest)
- **Rework cycles**: 1 (Cycle 1 / Rework #6a, R11-1 + R11-2)
- **Blockers resolved**: 2 at C7 (R11-1 C7 after codebase evidence scan; R11-2 C7 after annotation commit + regression tests GREEN)

### Final git tag

`aidlc/raidlc-ai_tier/phase-12` — Rework #6a Cycle 1 closure blueprint committed.

---

## Q27 locked (C6, 2026-04-23) — Envelope pivot: flat `List<TierEntry>` replaces TierEnvelope pairing

**Supersedes**: Q1/Q2/Q4 (§381 original flatten with forward-compat dual-block). Those decisions are marked SUPERSEDED BY Q27 at their original lock location.

**Scope**: **GET path only** (list + detail). The write contract (POST / PUT `/v3/tiers`) is untouched by Q27 — user directive: *"For write I will tell you. Now only do the change for the get calls."*

**New read-shape contract (`List<TierEntry>`):**

1. **Listing** (`GET /v3/tiers`) returns a flat `List<TierEntry>`. When a slabId has both a LIVE SQL row **and** a workflow-visible Mongo doc (DRAFT / PENDING_APPROVAL / REJECTED) for the same slabId, **two separate entries** appear in the list — one with `status: "LIVE"` and one with `status: "DRAFT"`/`"PENDING_APPROVAL"`/`"REJECTED"` — **same `slabId`**, distinct wire objects.
2. **Detail** (`GET /v3/tiers/{tierId}`) returns a `List<TierEntry>` of **1 or 2 entries** (never a bare object):
   - Numeric path (`tierId` parses as Long) → interpret as `slabId`; return the LIVE entry plus any paired in-flight entry (array of 1 or 2).
   - String path (non-numeric) → interpret as `tierUniqueId` (Mongo id); return **only the DRAFT/PENDING/REJECTED entry** — even if a paired LIVE exists. Rationale: string-key lookup is the maker UI's edit-flow entry point; it explicitly addresses the draft side.
3. **Shape is always an array**, even when 1 element, even when empty.

**`TierEntry` shape (single flat DTO — no LIVE/DRAFT split, no nested `live`/`pendingDraft` blocks):**

| Field | Type | LIVE presence | DRAFT/PENDING/REJECTED presence |
|---|---|:---:|:---:|
| `status` | enum | `"LIVE"` | `"DRAFT"` / `"PENDING_APPROVAL"` / `"REJECTED"` |
| `slabId` | `Long?` | present | present if editing LIVE; null for brand-new DRAFT |
| `tierUniqueId` | `String?` | absent | present |
| `name` | `String` | present | present |
| `description` | `String?` | present | present |
| `color` | `String?` | present | present |
| `serialNumber` | `Integer` | present | present |
| `tierStartDate` | ISO-8601? | present (SQL `created_on`) | absent (no SQL row) |
| `eligibility` | `TierEligibilityConfig` | present | present |
| `renewal` | `TierValidityConfig` | present (**renamed from `validity`**) | present |
| `downgrade` | `TierDowngradeConfig` | present | present |
| `rejectionComment` | `String?` | absent | present on DRAFT that was previously REJECTED |
| `meta` | `TierMeta` | present (trimmed — only `createdBy/At`, `updatedBy/At`) | present (trimmed) |

**Field-rename / drop rules (wire shape):**
- **Renamed on wire**: top-level block `validity` → `renewal` (per user: *"change the name of validity and make it renewal"*).
- **Dropped from wire**: the nested `validity.renewal` sub-block (`TierValidityConfig.renewal`) is **not emitted** on read. The default-synthesis of `TierRenewalConfig.builder().criteriaType(CRITERIA_SAME_AS_ELIGIBILITY)` at `TierStrategyTransformer.extractValidity` (lines 813-815) is removed.
- **Dropped from wire**: the `origin` field (was `TierOrigin` enum: `LEGACY_SQL_ONLY` / `MONGO_ONLY` / `BOTH`). No consumer need with the flat shape; `status` is the sole discriminator.
- **Dropped from wire**: the `hasPendingDraft` computed flag. UI determines pairing by scanning the list for matching `slabId`.
- **Dropped from wire**: `live` + `pendingDraft` placeholder blocks (forward-compat dual-block killed — never used).
- **Dropped from wire**: `draftStatus` (redundant with the new unified `status` field).
- **Dropped from response**: `summary` block (`KpiSummary` — `totalTiers`, `liveTiers`, `pendingApprovalTiers`, `totalMembers`, `lastMemberCountRefresh`). User directive: *"We do not want member count and last member count refereshed in this."* The list response drops `summary` entirely — `TierListResponse` becomes just `{ "tiers": List<TierEntry> }`.
- **`meta` trimmed on wire**: only `createdBy`, `createdAt`, `updatedBy` (renamed conceptually to lastModifiedBy), `updatedAt` (lastModifiedAt) surface. `approvedBy/At`, `rejectedBy/At`, `basisSqlSnapshot` remain server-internal (basisSqlSnapshot is still written by Mongo; drift check keeps using it).

**`status` enum (wire value) — REJECTED added**:
The `TierStatus` Java enum currently lists `DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT, PUBLISH_FAILED` (`intouch-api-v3/.../enums/TierStatus.java:3-5`). **REJECTED is NOT currently a first-class enum value.** Q27 adds `REJECTED` to the enum so it can appear on the wire as `status: "REJECTED"` when a maker's draft has been rejected by a reviewer. Workflow-visible filter (previously `DRAFT | PENDING_APPROVAL`) expands to `DRAFT | PENDING_APPROVAL | REJECTED`. LIVE is a synthetic wire-only discriminator (not an enum member — the LIVE SQL row's "status" is implicit).

**Pairing rule (unchanged from envelope era, but now expressed differently):**
A Mongo workflow-visible doc is "paired" to a SQL LIVE row iff `mongoDoc.slabId == sqlRow.slabId`. In the flat-list shape this pairing is **observable** (UI sees two entries with the same slabId); in the envelope era it was hidden inside a single envelope.

**List ordering** (Q27-O-a locked): LIVE-first grouping. For each SQL row (in SQL order), emit the LIVE entry first; immediately after, emit the paired in-flight entry (if any) for the same slabId. After all LIVE rows and their pairs, append brand-new DRAFT/PENDING/REJECTED entries (no SQL row) in Mongo-insertion order.

**Detail URL disambiguation** (Q27-B-b locked):
```
GET /v3/tiers/3850        → numeric → slabId lookup → [LIVE entry, draft entry-if-any]
GET /v3/tiers/ut-977-003  → string  → tierUniqueId lookup → [draft entry only]
GET /v3/tiers/660a1b2c…   → string  → tierUniqueId or Mongo objectId → [draft entry only]
```
404 when no match is found for either lookup path.

**Implementation surface (intouch-api-v3 only, zero engine changes):**
- **New** `com.capillary.intouchapiv3.tier.entry.TierEntry` — flat DTO (fields above).
- **New** `com.capillary.intouchapiv3.tier.entry.TierEntryBuilder` — produces `List<TierEntry>` from `List<SqlTierRow> + List<UnifiedTierConfig>`. Replaces `TierEnvelopeBuilder`.
- **Deleted** `TierView`, `TierEnvelope`, `TierEnvelopeBuilder`, `TierOrigin` (old envelope package).
- **Updated** `TierFacade.listTiers` → returns `TierListResponse { tiers: List<TierEntry> }` (no `summary`).
- **Updated** `TierFacade.getTierDetail` → returns `List<TierEntry>` (was `TierEnvelope`). Facade gains URL-sniffing (numeric → slabId path; string → tierUniqueId path).
- **Updated** `TierController` → response types `List<TierEntry>` on detail, `TierListResponse` on list (slimmer shape).
- **Updated** `TierListResponse` → drop `summary` field; `tiers` becomes `List<TierEntry>`.
- **Updated** `SqlTierConverter` → method renamed `toView` → `toEntry`, returns `TierEntry` with `status = "LIVE"`.
- **Updated** `TierStrategyTransformer.extractValidity` → drop default renewal synthesis (lines 813-815); `TierValidityConfig.renewal` stays null on LIVE reads.
- **Updated** `TierStatus` enum → add `REJECTED` value.
- **Updated** tests — rewrite `TierEnvelopeJsonSerializationTest`, `TierEnvelopeBuilderTest` as `TierEntry*` equivalents.

**Residual write-path caveat**: `TierValidityConfig` still has a `renewal` field in Java (kept for parity with write-path — `TierCreateRequest` / `TierUpdateRequest` carry it inside `validity`). On the read path, `TierEntry.renewal` is of type `TierValidityConfig` with the nested `.renewal` field nulled before serialization — `@JsonInclude(NON_NULL)` then omits it from the wire. Write-contract rename from `validity` → `renewal` is explicitly out of Q27 scope (user: *"For write I will tell you"*).

**Confidence evidence (C6)**:
- Pairing semantics verified: `TierEnvelopeBuilder` lines 56-68 — current pairing keyed by slabId, matches Q27 rule.
- Workflow-visible filter baseline: `TierFacade.WORKFLOW_VISIBLE_STATUSES` L82-83 (`DRAFT, PENDING_APPROVAL`); Q27 expansion to include `REJECTED` verified against `TierStatus.java` (REJECTED absent → must be added as part of Q27).
- Default renewal synthesis: `TierStrategyTransformer.java` lines 813-815 — confirmed explicit synthesis to remove.
- `-1` sentinel filtering: `extractConditions` lines 824-826 still emits `-1` verbatim (Q9 locked on paper but not yet implemented in code — deferred follow-up F2; Q27 does NOT re-open Q9).

**Non-scope (explicitly deferred)**:
- Q9 `-1` sentinel filter on read (F2 — deferred follow-up).
- Write-path rename of `validity` → `renewal` (user: *"For write I will tell you"*).
- Member count + `lastMemberCountRefresh` computations (user directive: drop from summary; not just from wire).
- Any re-derivation of the flattened envelope computed-getter pattern — killed outright.

