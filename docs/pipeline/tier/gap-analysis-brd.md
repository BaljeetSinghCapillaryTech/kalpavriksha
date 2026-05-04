# Gap Analysis -- BRD/PRD Claims vs Codebase Reality

> Phase 2b: Analyst (compliance mode) verification
> Date: 2026-04-11

---

## Verified Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|-------------|---------|----------|
| V-1 | ProgramSlab has NO status field | ProgramSlab.java | CONFIRMED (C7) | grep for "status" returned zero results. Entity has: pk, program, programId, serialNumber, name, description, createdOn, metadata. |
| V-2 | ProgramSlab has NO color field | ProgramSlab.java | CONFIRMED (C7) | No color/colorCode field in entity. Color is in SlabMetaData (parsed from metadata JSON). |
| V-3 | NO tier REST APIs in intouch-api-v3 | resources/*.java, facades/*.java | CONFIRMED (C7) | grep for slab/Slab/tier/Tier in controllers and facades returned zero results (excluding promotion/milestone/journey). |
| V-4 | PeProgramSlabDao has no status filter | PeProgramSlabDao.java | CONFIRMED (C7) | grep for status/Status/active returned zero results. Three queries: findByProgram, findByProgramSlabNumber, findNumberOfSlabs -- none filter by status. |
| V-5 | createSlabAndUpdateStrategies creates slab AND updates strategies | PointsEngineRuleService.java:2304 | CONFIRMED (C7) | Method iterates strategyInfos -> createOrUpdateStrategy(), then calls createOrUpdateSlab(). Both operations in one method. |
| V-6 | SlabMetaData has colorCode field | SlabMetaData.java | CONFIRMED (C7) | Class has `private String colorCode` with getter, builder, Gson serialization. |
| V-7 | Maker-checker exists only for promotions | UnifiedPromotionFacade.java, ApprovalStatus.java | CONFIRMED (C7) | ApprovalStatus enum (APPROVE, REJECT) and PromotionReviewRequest are in unified/promotion package. No MC code elsewhere. |
| V-8 | UnifiedPromotion uses MongoDB @Document | UnifiedPromotion.java | CONFIRMED (C7) | `@Document(collection = "unified_promotions")` annotation present. Uses Spring Data MongoDB. |
| V-9 | PromotionStatus has DRAFT/PENDING_APPROVAL/ACTIVE lifecycle | PromotionStatus.java | CONFIRMED (C7) | Enum: DRAFT, ACTIVE, PAUSED, PENDING_APPROVAL, STOPPED, SNAPSHOT, LIVE, UPCOMING, COMPLETED, PUBLISH_FAILED. State diagram in comments. |
| V-10 | EntityOrchestrator uses Transformer pattern | EntityOrchestrator.java | CONFIRMED (C7) | Map of EntityType -> Transformer. Seven transformer types registered: BROADCAST_PROMOTION, PROMOTION, TARGET_GROUP, LIABILITY_OWNER_SPLIT, LIMIT, WORKFLOW, JOURNEY. |
| V-11 | CustomerEnrollment has current_slab_id FK to ProgramSlab | CustomerEnrollment.java:79-85 | CONFIRMED (C7) | `@JoinColumn(name = "current_slab_id")` with `@ManyToOne` to ProgramSlab. Also stores `currentSlabId` as int. |
| V-12 | SlabUpgradeMode has EAGER/DYNAMIC/LAZY | SlabUpgradeMode.java | CONFIRMED (C7) | Enum with three values and Javadoc explaining timing. |
| V-13 | TierDowngradeTarget has SINGLE/THRESHOLD/LOWEST | TierDowngradeSlabConfig.java | CONFIRMED (C7) | Inner enum `TierDowngradeTarget` with three values. |
| V-14 | Eligibility criteria types from docs | docs.capillarytech.com | CONFIRMED (C6) | Docs list: Current Points, Lifetime Points, Lifetime Purchases, Tracker Value. "The eligibility criteria type that you set for tier upgrade remains the same for all the subsequent tiers." |

## Gaps Found (BA/PRD missed or did not mention)

| # | Gap Description | Source | Impact | Recommendation |
|---|----------------|--------|--------|----------------|
| G-1 | **No Thrift method for tier config sync.** EMFService in emf.thrift has no createSlab/updateSlab/configureTier method. The BA assumes Thrift sync but no method exists. | emf.thrift search | BLOCKER -- the approval sync path (MongoDB -> SQL) has no existing transport. | Must either add a new Thrift method or use an alternative sync mechanism. Resolve in Phase 6. |
| G-2 | **PartnerProgramSlab not addressed.** PRD has no acceptance criteria for partner slab impact. | PartnerProgramSlab.java, PePartnerProgramSlabDao.java | ~~HIGH~~ LOW (Rework #2) -- Only DRAFT tiers can be deleted, and DRAFTs have no SQL record / no PartnerProgramSlab refs. Concern deferred to future tier retirement epic. | No action needed for current scope. Document for future tier retirement when ACTIVE tier stopping is implemented. |
| G-3 | ~~**PeProgramSlabDao used in 7+ services.** Adding status filter affects: InfoLookupService (4 sites), PointsEngineRuleService (2 sites), PointsReturnService, ProgramCreationService, PointsEngineServiceManager (2 sites), BulkOrgConfigImportValidator.~~ | grep PeProgramSlabDao | ~~HIGH~~ RESOLVED (Rework #3) -- No SQL changes. PeProgramSlabDao completely untouched. | ~~Use expand-then-contract migration. Add new `findActiveByProgram()` method, migrate callers incrementally.~~ **NOT NEEDED**: No status column, no findActiveByProgram(), no Flyway migration. Zero emf-parent entity/DAO changes. |
| G-4 | **Threshold values stored in strategy CSV, not per-slab.** BA says "threshold > previous tier" but thresholds are a comma-separated string in strategy properties (`threshold_values`), not a field on ProgramSlab. Validation logic is more complex than implied. | ThresholdBasedSlabUpgradeStrategyImpl.java:164 | MEDIUM -- validation AC needs refinement. | Defer exact validation rules to HLD/LLD. The new MongoDB document WILL store per-tier thresholds, but the SQL sync must map back to the CSV strategy format. |
| G-5 | **EmfMongoDataSourceManager is sharded.** The promotion repo uses `emfMongoDataSourceManager.getAll()` to iterate all MongoDB shards for index creation. Tier documents must also handle multi-shard scenarios. | UnifiedPromotionRepositoryImpl.java:87-91 | MEDIUM -- affects MongoDB repository implementation. | Follow the same sharded MongoDB pattern as UnifiedPromotionRepository. |
| G-6 | **UnifiedPromotion has complex edit flow.** The promotion edit flow creates a child document with parentId and has `DraftDetails`, `ParentDetails` models, `UnifiedPromotionEditOrchestrator`, and `StatusTransitionValidator`. The BA mentions parentId but doesn't account for the full edit orchestration complexity. | UnifiedPromotionFacade.java imports | MEDIUM -- edit flow is more complex than described. | Study UnifiedPromotionEditOrchestrator in Phase 5 (codebase research) to understand the full pattern before designing the tier edit flow. |

## GUARDRAILS Compliance (Preliminary)

| Guardrail | Relevant? | Status |
|-----------|-----------|--------|
| G-01: Multi-timezone | Not directly (tier config is not time-zone sensitive) | N/A |
| G-03: Backward compatibility | ~~YES -- adding status column must not break existing callers~~ No SQL changes (Rework #3). No backward compat concern. | ~~NEEDS ATTENTION (C-3)~~ RESOLVED |
| G-05: Expand-then-contract migrations | ~~YES -- Flyway migration for status column~~ No Flyway migration (Rework #3). | ~~NEEDS ATTENTION~~ NOT NEEDED |
| G-07: Multi-tenancy | YES -- all queries must be scoped by orgId | CONFIRMED (existing pattern) |
| G-12: Idempotency | YES -- tier creation should be idempotent on retry | ADDRESSED in PRD NFRs |

---

## Summary

- **14 claims VERIFIED** (all C6-C7 with file-level evidence)
- **6 gaps FOUND** (1 blocker, 2 high, 3 medium)
- **Key blocker**: No Thrift method exists for tier config sync -- must be resolved before HLD

---

## Rework Delta — Cycle 6a Compliance Verification (2026-04-22)

**Trigger**: Cascade from Phase 1 BA rework (Rework #6a)
**Verified REQs**: 18 (7 UPDATE + 11 NEW) + 1 OBSOLETE closure
**Scope lock**: Q13 — intouch-api-v3 only (6a)
**Model**: opus (claude-opus-4-7)
**Verification depth**: primary-source code reads (C6+) for every claim

### Existing Gap Analysis Triage

| Finding # | Prior Verdict | Current Status | Rationale |
|---|---|---|---|
| V-1 .. V-14 | CONFIRMED | UNCHANGED | Prior verified claims pre-date Rework #6a and are not in the 6a delta scope. No re-verification needed. |
| G-1 (Thrift sync) | BLOCKER | UNCHANGED (not 6a scope) | Rework #6a is wire-layer only (Q13). Thrift surface is inherited from Rework #5 resolution. Not touched in this delta. |
| G-2 (PartnerProgramSlab) | LOW (Rework #2) | UNCHANGED | Not in 6a scope. |
| G-3 (PeProgramSlabDao) | RESOLVED (Rework #3) | UNCHANGED | Not in 6a scope. |
| G-4 (threshold CSV) | MEDIUM | UNCHANGED — directly corroborated | Still true — `TierStrategyTransformer.applySlabUpgradeDelta` at :227-241 operates on the CSV format described in G-4. Q20 classification now formally documents this. |
| G-5 (sharded Mongo) | MEDIUM | UNCHANGED | Not in 6a scope. |
| G-6 (edit-flow complexity) | MEDIUM | UNCHANGED | Not in 6a scope. |

No prior finding points at a removed or updated 6a claim — the original gap analysis was generic (Rework #2/#3 era) and does not overlap with the 6a wire-contract delta.

### REQ Verification Matrix (6a delta)

| REQ | Claim | Code file:line | Verdict | Evidence |
|---|---|---|---|---|
| REQ-02 (UPD) | GET envelope flattens — hoist `live.*` to root, add `status:"LIVE"` discriminator, reserve `pendingDraft` at root | `intouch-api-v3/.../envelope/TierEnvelope.java:44-47`; `envelope/TierEnvelopeBuilder.java:115-125` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | Today `TierEnvelope` has `private TierView live` (:44) and `private TierView pendingDraft` (:47) — tier fields are NESTED under `live`, NOT hoisted to root. No `status` discriminator field on the envelope. Rework #6a requires a new flat shape. Precondition (current shape is nested `live`) verified C7. |
| REQ-05 (UPD) | Per-tier response root carries core fields; program-level eligibility moves to read-wide hoist (REQ-20) | `envelope/TierView.java:49-76` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | `TierView` today carries `name, description, color, serialNumber, eligibility, validity, downgrade` under a nested `live` block. Envelope flatten requires new shape. |
| REQ-07 (UPD) | `downgrade` block renamed to `renewal`; `downgrade.target` → `renewal.downgradeTo`; `reevaluateOnReturn`/`dailyEnabled` hoisted OUT | `model/TierDowngradeConfig.java:25-30`; `dto/TierCreateRequest.java:27`; `dto/TierUpdateRequest.java:22`; `UnifiedTierConfig.java:74` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | TODAY: `TierDowngradeConfig` exists with `private String target` (:26), `private boolean reevaluateOnReturn` (:27), `private boolean dailyEnabled` (:28), `private List<TierCondition> conditions` (:29). Referenced by `TierCreateRequest.downgrade` (:27), `TierUpdateRequest.downgrade` (:22), `UnifiedTierConfig.downgrade` (:74), `TierView.downgrade` (:69). 15 files reference `TierDowngradeConfig` in `src/main`. The rename is net-new. |
| REQ-08 (OBS) | `downgrade` block/AC marked obsolete | `model/TierDowngradeConfig.java`; `dto/TierCreateRequest.java:27`; `dto/TierUpdateRequest.java:22`; `UnifiedTierConfig.java:74`; `strategy/TierStrategyTransformer.java` (extensive) | **PARTIAL** (precondition HAS orphan references — not an error, expected in 6a scope) | Old wire shape `TierDowngradeConfig` with `target` field is WIDELY referenced in production code (9 main files, ~15 occurrences). REQ-08 OBSOLETE just marks the BA AC as replaced by REQ-07; it does NOT claim the code is already renamed. The code rename is the 6a implementation work. No orphan claim to refute. |
| REQ-19 (NEW) | GET filters `value == "-1"` from eligibility + renewal conditions (reverses the current "do NOT filter" comment) | `strategy/TierStrategyTransformer.java:826` | **UNVERIFIABLE-NET-NEW** (precondition VERIFIED C7) | Line 826 explicitly reads: `// UI can recognise and display the not-configured state; do NOT filter.` Current behaviour is documented as surfacing `-1` values unchanged. REQ-19 reverses this. Sentinel origin verified: `peb TierDowngradeSlabConfig.getPoints()` at line 128-132 returns `BigDecimal.valueOf(-1)` when `points == null`. |
| REQ-20 (NEW) | GET hoists program-level fields read-wide: `eligibility.kpiType/upgradeType/trackerId/trackerConditionId/additionalCriteria[]/expressionRelation`, `validity.periodType/periodValue`, `reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled` | `pointsengine-emf/.../ThresholdBasedSlabUpgradeStrategyImpl.java:44-51,229-239`; `pointsengine-emf/.../TierDowngradeStrategyConfiguration.java:28-38`; `pointsengine-emf/.../UpgradeCriteria.java:20-23` | **CONFIRMED (storage)** / **UNVERIFIABLE-NET-NEW (hoist behaviour)** | Q20 classification confirmed: `ThresholdBasedSlabUpgradeStrategyImpl.java:44` (`currentValueType`), :46 (`trackerId`), :47 (`trackerConditionId`), :51 (`ArrayList<AdditionalUpgradeCriteria> additionalUpgradeCriteriaList`) — all on the program-level strategy. `TierDowngradeStrategyConfiguration.java:31-38` carries the four Class A booleans. `UpgradeCriteria.java:20-23` confirms singular `currentValueType/trackerId/trackerConditionId` per entry; composition via multiple list entries. Hoist-on-read is net-new wire behaviour to build in 6a. |
| REQ-21 (NEW) | SLAB_UPGRADE-type tiers — `validity.startDate` never returned on wire | `model/TierValidityConfig.java:27`; `validation/TierEnumValidation.java:64-68` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | `TierValidityConfig.startDate` exists today (line 27: `private String startDate`). `SLAB_UPGRADE` is a recognised periodType (line 66 of `TierEnumValidation`). No current suppression logic for SLAB_UPGRADE + startDate combo in `extractValidityForSlab` (`TierStrategyTransformer.java:767-817`). REQ-21 is net-new read-path filter. |
| REQ-22 (NEW) | FIXED-type duration computed from existing `startDate + periodValue` — no new storage field | `model/TierValidityConfig.java:25-29` | **CONFIRMED (inputs exist)** / **UNVERIFIABLE-NET-NEW (computation)** | `TierValidityConfig` today has `periodType` (:25), `periodValue` (:26), `startDate` (:27), `endDate` (:28). `endDate` is noted as "always null on LIVE responses (Decision V6 — derived UI-side)" in the javadoc (:17-20). Computation of end-date on read is net-new. |
| REQ-25 (UPD) | Required per-tier fields: `programId`, `name`, `eligibility.threshold` (non-first) — `eligibilityCriteriaType` removed | `dto/TierCreateRequest.java:17-28`; `validation/TierCreateRequestValidator.java:42-56` | **CONFIRMED (precondition)** | Today `TierCreateRequest` has `programId`, `name`, `description`, `color`, `eligibility`, `validity`, `downgrade`. Validator enforces: `programId` required (:46), `name` required (:58-61). No `eligibilityCriteriaType` field exists on DTO today — the REQ-25 change narrows the documented required list but doesn't remove a DTO field (was never on DTO). |
| REQ-26 (UPD) | Per-tier accepted wire fields narrowed to Figma-wizard scope; renewal block replaces downgrade | `dto/TierCreateRequest.java:17-28`; `dto/TierUpdateRequest.java:14-23` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | Today the DTOs accept the broader Rework #5 shape (eligibility + validity + downgrade as full objects). Narrowing is the 6a implementation work. |
| REQ-27 (UPD) | Legacy `downgrade` field rejected 400 InvalidInputException on POST/PUT | `dto/TierCreateRequest.java:27`; `dto/TierUpdateRequest.java:22`; `validation/TierCreateRequestValidator.java`; `validation/TierUpdateRequestValidator.java` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | `downgrade` field is ACCEPTED today on both DTOs (:27 of create, :22 of update). `validate()` in create validator (:42-56) calls `TierEnumValidation.validateDowngrade(request.getDowngrade())` — the field is actively processed. REQ-27 is net-new reject. Hard-flip (Q11) removes accept. |
| REQ-33 (NEW) | Per-tier POST/PUT rejects Class A booleans: `reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled` | `model/TierDowngradeConfig.java:27-28`; `model/EngineConfig.java:12-14`; `strategy/TierStrategyTransformer.java:524-530` | **UNVERIFIABLE-NET-NEW** (precondition PARTIAL) | `reevaluateOnReturn` and `dailyEnabled` ARE on the wire today — nested in `TierDowngradeConfig` (:27-28). Reject would reverse current silent-accept behaviour; `applyProgramLevelBooleans` at `TierStrategyTransformer.java:524-530` actively writes them to engine. `retainPoints` is NOT on `TierCreateRequest`/`TierUpdateRequest`/`TierDowngradeConfig` — it exists only on `EngineConfig.java:12` (separate DTO not wired into create/update DTO), so reject has nothing to reject today (precondition FALSE for this specific field — flag below). `isDowngradeOnPartnerProgramDeLinkingEnabled` is only referenced in `TierStrategyTransformer.java` comments — NOT on per-tier write DTO today (same no-op concern). |
| REQ-34 (NEW) | Per-tier POST/PUT rejects Class B: `kpiType`, `upgradeType`, `trackerId`, `trackerConditionId`, `additionalCriteria[]`, `expressionRelation` | `model/TierEligibilityConfig.java:40-44`; `validation/TierEnumValidation.java:52-109` | **UNVERIFIABLE-NET-NEW** (precondition PARTIAL) | `kpiType` (:40), `upgradeType` (:42), `expressionRelation` (:43) ARE on `TierEligibilityConfig` today AND actively validated by `TierEnumValidation.validateEligibility` (:90-109). REQ-34 reverses current accept behaviour for these three. `trackerId`, `trackerConditionId`, `additionalCriteria[]` are NOT on `TierEligibilityConfig` — no field to reject today (precondition FALSE for these three — flag below). |
| REQ-35 (NEW) | Per-tier POST/PUT rejects `eligibility.conditions[].value == "-1"` or `renewal.conditions[].value == "-1"` | `validation/TierCreateRequestValidator.java`; `validation/TierUpdateRequestValidator.java`; `validation/TierEnumValidation.java` | **UNVERIFIABLE-NET-NEW** (precondition VERIFIED) | Grep for `"-1"` in `intouch-api-v3/.../tier` main source returned zero matches — no current rejection of `-1` sentinel on write. REQ-35 is purely new behaviour. Condition types validated in `TierEnumValidation.validateConditionTypes` (:145-159) but values are not filtered. |
| REQ-36 (NEW) | Per-tier POST/PUT rejects `validity.startDate` for SLAB_UPGRADE-type | `model/TierValidityConfig.java:27`; `validation/TierEnumValidation.java:117-126` | **UNVERIFIABLE-NET-NEW** (precondition VERIFIED) | `TierValidityConfig.startDate` (:27) and `TierValidityConfig.periodType` (:25) coexist on DTO. Current `TierEnumValidation.validateValidity` (:117-126) only checks `periodType` against VALID_PERIOD_TYPES — NO cross-field rule rejecting `startDate` when `periodType == SLAB_UPGRADE`. REQ-36 is net-new cross-field validation. |
| REQ-37 (NEW) | Per-tier POST/PUT rejects nested `advancedSettings` envelope | search of `intouch-api-v3/src/main` | **FLAG: precondition FALSE — no `advancedSettings` field exists on DTOs today** | Grep for `advancedSettings\|advanced_settings` in `intouch-api-v3/src/main` returned zero matches. Neither `TierCreateRequest` nor `TierUpdateRequest` has an `advancedSettings` field. Because Jackson by default REJECTS unknown fields only if `FAIL_ON_UNKNOWN_PROPERTIES=true` is configured, the reject either needs to (a) verify the global Jackson config behaviour or (b) be a no-op for the absent field. **MEDIUM severity**: REQ-37 as stated ("reject nested envelope") may already be no-op-satisfied if Jackson is strict; or it requires adding explicit validation. Needs clarification — this mirrors the flag noted in the instructions. |
| REQ-38 (NEW) | `renewal.criteriaType` locked to `"Same as eligibility"`; `conditions[]`/`expressionRelation` must be null/empty | `model/TierRenewalConfig.java:55-59`; `validation/TierRenewalValidation.java:27-54` | **CONFIRMED (PARTIAL — already enforced)** | B1a lock already in effect today. `TierRenewalConfig.CRITERIA_SAME_AS_ELIGIBILITY = "Same as eligibility"` at :55. `TierRenewalValidation.validate` at :37-52 throws `InvalidInputException` if `criteriaType != CRITERIA_SAME_AS_ELIGIBILITY`, `conditions` non-empty, or `expressionRelation != null`. Wired into both `TierCreateRequestValidator.validate` (:55 call to `TierRenewalValidation.validate(...)`) and `TierUpdateRequestValidator.validate` (:42). REQ-38 is re-confirmation of existing behaviour + doc-only rename from `conditionsToSatisfy` (never in code) → `criteriaType` (real field). No net-new logic needed for the lock itself. |
| REQ-49 (UPD) | PUT editable-fields list updated to renamed shape + program-level rejects | `dto/TierUpdateRequest.java:14-23`; `validation/TierUpdateRequestValidator.java:32-43` | **UNVERIFIABLE-NET-NEW** (precondition TRUE) | Today `TierUpdateRequest` accepts: `name`, `description`, `color`, `eligibility`, `validity`, `downgrade`. Validator processes each. PUT narrowing + renewal rename + program-level rejects are the 6a implementation work. |
| REQ-55 (NEW) | Old-UI edit during pending new-UI DRAFT — `basisSqlSnapshot` lag detected at approval | `drift/TierDriftChecker.java:1-50+`; `UnifiedTierConfig.java`; `TierApprovalHandler.java` | **CONFIRMED (precondition)** | `TierDriftChecker` is a pure-function comparator described as "detects drift between the SQL snapshot captured when a tier draft was authored (`basisSqlSnapshot`) and the current LIVE SQL state at approval time" (:10-13). Already wired into `TierApprovalHandler.preApprove` per javadoc (:15-17). REQ-55 is a formalization of an already-implemented mechanism — no net-new code required, documentation alignment only. |

### Q20 Storage Classification Verification

| Field (wire name) | BA claim for placement | Code evidence (file:line) | Verdict |
|---|---|---|---|
| `kpiType` | program-level (SlabUpgradeStrategy.propertyValues.current_value_type) | `ThresholdBasedSlabUpgradeStrategyImpl.java:44` (`private CurrentValueType currentValueType`); `TierStrategyTransformer.java:700-702` (read: top-level `current_value_type`) | **CONFIRMED C7** |
| `upgradeType` | program-level (SlabUpgradeStrategy.propertyValues.slab_upgrade_mode) | `TierStrategyTransformer.java:706-708` (read: top-level `slab_upgrade_mode`). Program-level scalar, mirrors v2 parity. | **CONFIRMED C7** |
| `trackerId` | program-level (SlabUpgradeStrategy.propertyValues) | `ThresholdBasedSlabUpgradeStrategyImpl.java:46` (`private long trackerId = -1`); `UpgradeCriteria.java:22` (`protected long trackerId = -1`) | **CONFIRMED C7** |
| `trackerConditionId` | program-level | `ThresholdBasedSlabUpgradeStrategyImpl.java:47`; `UpgradeCriteria.java:23` | **CONFIRMED C7** |
| `additionalCriteria[]` | program-level list | `ThresholdBasedSlabUpgradeStrategyImpl.java:51` (`ArrayList<AdditionalUpgradeCriteria> additionalUpgradeCriteriaList`); :229-239 (initialized from `propertiesMap.get("additional_upgrade_criteria")`, iterated at runtime) | **CONFIRMED C7** |
| `expressionRelation` (eligibility) | program-level | `ThresholdBasedSlabUpgradeStrategyImpl.java:69` (`private ArrayList<ArrayList<Integer>> expressionRelation`); :248-261 (parsed from `propertiesMap.get("expression_relation")`) | **CONFIRMED C7** |
| `threshold` (per-tier VALUE in program-level CSV) | program-level CSV slot, per-tier semantics | `TierStrategyTransformer.java:227-241` (`applySlabUpgradeDelta` mutates CSV); :710-725 (`extractEligibilityForSlab` reads CSV at index `serialNumber - 2`) | **CONFIRMED C7** |
| `reevaluateOnReturn` (Class A boolean) | program-level (TierDowngradeStrategyConfiguration) | `TierDowngradeStrategyConfiguration.java:31` (`@SerializedName("isDowngradeOnReturnEnabled") private boolean m_isDowngradeOnReturnEnabled`) | **CONFIRMED C7** |
| `dailyEnabled` (Class A boolean) | program-level | `TierDowngradeStrategyConfiguration.java:34` (`@SerializedName("dailyDowngradeEnabled") private boolean dailyDowngradeEnabled`) | **CONFIRMED C7** |
| `retainPoints` (Class A boolean) | program-level | `TierDowngradeStrategyConfiguration.java:28` (`@SerializedName("retainPoints") private boolean retainPoints`) | **CONFIRMED C7** |
| `isDowngradeOnPartnerProgramDeLinkingEnabled` (Class A boolean) | program-level | `TierDowngradeStrategyConfiguration.java:37` (`@SerializedName("isDowngradeOnPartnerProgramExpiryEnabled") private boolean isDowngradeOnPartnerProgramDeLinkingEnabled` — note JSON-key vs Java-field naming drift, flagged in session-memory Q13 as out-of-scope cleanup) | **CONFIRMED C7** |
| `periodType`, `periodValue` (validity) | per-tier in `TierDowngradeSlabConfig[].periodConfig`, but BA Q24 treats them as program-level for UI simplicity | `TierDowngradeSlabConfig.java:33-34` (`@SerializedName("periodConfig") private TierDowngradePeriodConfig m_periodConfig` — per-slab). BA Q10b treats periodType/periodValue as program-level payload. | **PARTIAL** — physically per-slab in engine (per-slab JSON entry), but BA treats as program-level for UI simplicity. This is a BA classification choice, not a code truth. Flag for architect review. |
| `downgradeTarget` / `target` (per-tier) | per-tier (slabs[].downgradeTarget) | `TierDowngradeSlabConfig.java:30-31`; `TierStrategyTransformer.java:576-580` (mapped per-slab) | **CONFIRMED C7** |

**Q20 VERDICT**: **STANDS** for all program-level Class A booleans and eligibility program-level fields. One clarification: `validity.periodType/periodValue` are physically per-slab in the engine (nested under `slabs[n].periodConfig`), but BA Q10b/Q24 classifies them as program-level for UI simplicity. This is an intentional UX-driven classification, not a code-truth error — but downstream phases (Architect, Developer) need to be aware that the hoist-on-read for `periodType/periodValue` will be reading PER-SLAB values from the first/primary slab entry, and the advanced-settings write will need to fan out across all per-slab periodConfig blocks.

### FU-01 Cancellation Verification

| Evidence | Expected (per BA) | Code reality | Verdict |
|---|---|---|---|
| `ThresholdBasedSlabUpgradeStrategyImpl.java:51` has `ArrayList<AdditionalUpgradeCriteria>` field | YES | `private ArrayList<AdditionalUpgradeCriteria> additionalUpgradeCriteriaList;` (line 51) | **CONFIRMED C7** |
| Runtime iterates the list (not just stores) | YES | Lines 229-239: `for (AdditionalUpgradeCriteria auc : additionalUpgradeCriteriaList) { auc.initializeCriteria(...); } upgradeCriteriaList.addAll(additionalUpgradeCriteriaList);` — initialized AND added to composite evaluation list. Lines 240-246: upgrade criteria iterated at runtime for `slabUpgradeModes`, `upgradeValueTypes`, tracker map. | **CONFIRMED C7** |
| `UpgradeCriteria.java` has singular fields | YES | Lines 20-23: `protected SlabUpgradeStrategy.CurrentValueType currentValueType; protected SlabUpgradeMode slabUpgradeMode; protected long trackerId = -1; protected long trackerConditionId = -1;` — all singular. List-composition is via multiple entries on `additionalUpgradeCriteriaList`. | **CONFIRMED C7** |
| `peb` is same engine layer (not separate with scalar-only model) | YES | `peb/src/main/java/com/capillary/shopbook/peb/impl/system/tierdowngrade/config/updated/` contains only `TierDowngrade*.java` config classes. No separate `SlabUpgradeStrategy.java` with scalar-only model exists in peb. `UpgradeCriteria.java` does NOT exist in peb (glob returned 0 matches). The `pointsengine-emf/.../UpgradeCriteria.java` is the sole authority. | **CONFIRMED C7** |

**FU-01 CANCELLATION VERDICT**: **STANDS**. All four cancellation-rationale claims are C7-verified in code. The engine genuinely supports multi-tracker composition today. REQ-34's defensive reject (Q5c) stands as the correct 6a wire-layer behaviour; 6b will wire the list-plumbing end-to-end via the advanced-settings endpoint. No Flyway migration needed.

### GUARDRAILS Compliance Check

| Guardrail | Relevant REQs | Verdict | Evidence |
|---|---|---|---|
| G-01 Timezone | REQ-22 (FIXED duration compute) | **PASS** | Read-path computation is wire-only; existing `TierStrategyTransformer.extractIsoOffsetUtc` (:101-150) already normalizes every shape to UTC (`ZoneOffset.UTC`, `TierDateFormat.FORMATTER`). New computation can reuse this. |
| G-03 Security | REQ-33, REQ-34, REQ-35, REQ-36, REQ-37 (reject-on-write) | **PASS** | Rejects throw `InvalidInputException` (existing exception type), caught by `TargetGroupErrorAdvice` global handler per G-13. No SQL concatenation introduced. |
| G-05 Data Integrity | all UPDATE REQs | **PASS** | No schema changes in 6a (Q13 confirmed). Existing `UNIQUE (program_id, name)` SQL backstop continues to apply. |
| G-06 API Design (no rename of existing fields in same version) | REQ-07, REQ-27 (hard-flip `downgrade`→`renewal`) | **FLAG (HIGH)** | G-06.2 says "Never remove or rename fields in existing API versions. Only add. Deprecate old fields in docs." Rework #6a hard-flips `downgrade` → `renewal` with no back-compat window (Q11). BA rationale (session-memory Q11): "v3 tier surface is pre-GA for the new UI (the only real consumer, which Capillary controls); Rework #5 already made breaking wire changes without deprecation windows." Justification exists but is a deliberate G-06.2 deviation. Raised as **MEDIUM severity** — BA has captured the reasoning; Architect/Reviewer should re-confirm ADR. |
| G-07 Multi-Tenancy | REQ-20 (read-wide hoist) | **PASS** (with caveat) | The hoist reads program-level strategy JSON via existing `getAllConfiguredStrategies(programId, orgId)` Thrift (per session-memory Q15) — scoped by org/program. No cross-tenant data leak introduced if the Thrift call enforces tenant boundaries (which it does via existing behaviour). Caveat: 6a is wire-layer only, so tenancy correctness depends entirely on the existing Thrift tenancy contract. |
| G-10 Concurrency | REQ-33/34/37 (reject during advanced-settings writer activity) | **N/A in 6a** | Advanced-settings writer is 6b-scoped. In 6a, the per-tier reject is purely a payload-validation predicate with no shared mutable state. No race possible with an endpoint that doesn't exist yet. |
| G-12 Security — no internal field names leak | REQ-33, REQ-34 (error messages) | **PASS with flag** | Error message template (session-memory Q17): *"`<field>` is a program-level setting; use `PUT /api_gateway/loyalty/v1/programs/{programId}/advanced-settings`. Omit from tier payload."* — discloses wire-field names (`reevaluateOnReturn` etc.), which are already client-documented API contract (not secrets). Acceptable per G-03.5 (no sensitive data — these are public API field names). Flag for Reviewer: ensure messages do not leak internal engine field names (`isDowngradeOnReturnEnabled`) — only wire names. |
| G-13 Exception types | all reject REQs | **PASS** | All reject REQs call for `InvalidInputException` (not `IllegalArgumentException`), matching the intouch-api-v3 `TargetGroupErrorAdvice` contract. Error codes per Phase 4 Q-OP-1: Rework #6a uses band **9011-9020** (distinct from legacy Rework #4 band 9001-9010, no silent contract break per C-9 resolution). Per-REQ allocations: 9011 REQ-33, 9012 REQ-34, 9013 REQ-27, 9014 REQ-37, 9015 REQ-35, 9016 REQ-36, 9017 REQ-38; 9018-9020 reserved. |

### Q13 Scope Lock Verification

| Check | Verdict | Evidence |
|---|---|---|
| No new Thrift method required | **HOLDS** | REQ-20 read-wide hoist uses existing `getAllConfiguredStrategies(programId, orgId)` (session-memory Q15, confirmed by `TierStrategyTransformer.fromStrategies`:948-995 which already consumes `List<StrategyInfo>`). No new Thrift IDL edit. |
| No new DB column, index, or Flyway migration | **HOLDS** | All 6a items operate on existing DTOs, validators, transformers. No SQL schema change. REQ-22 (computed end-date) explicitly says "no new storage field". |
| No pointsengine-emf / peb source change | **HOLDS** | Q20 classification is a READ of existing engine storage. Hoist happens in intouch-api-v3's `TierStrategyTransformer.extractEligibilityForSlab`/new extractors. No engine mutation. FU-01 CANCELLED removes the only candidate engine change. |
| No engine IDL edit | **HOLDS** | Zero changes to `Thrift/thrift-ifaces-*`. |

**Q13 SCOPE LOCK VERDICT**: **HOLDS**. All 18 changed REQs + REQ-08 OBSOLETE are implementable within intouch-api-v3 wire layer.

### Findings by Severity

**BLOCKER (0)**: None. All Q20/Q13/FU-01 preconditions verified.

**HIGH (0)**: None. (G-06.2 deprecation-window deviation flagged as MEDIUM with BA-captured rationale.)

**MEDIUM (3)**:
- **M-1 REQ-33 partial precondition**: `retainPoints` and `isDowngradeOnPartnerProgramDeLinkingEnabled` are NOT currently on the per-tier write DTO (`TierDowngradeConfig` / `TierCreateRequest` / `TierUpdateRequest`). The REQ-33 reject list includes these two fields, but there is nothing to reject today. Options: (a) REQ-33 is a forward-looking defence for future DTO shape; (b) remove these two from the REQ-33 list; (c) explicitly state the reject is "defensive no-op today but blocks future accidental accept". Flag for Designer to resolve before SDET writes the RED tests. _Evidence: `TierDowngradeConfig.java:25-30` (fields only: `target`, `reevaluateOnReturn`, `dailyEnabled`, `conditions`); `EngineConfig.java:12` (`retainPoints` exists but EngineConfig is NOT wired into any write DTO)._
- **M-2 REQ-34 partial precondition**: Same pattern. `kpiType`, `upgradeType`, `expressionRelation` ARE on `TierEligibilityConfig` today — reject reverses accept. But `trackerId`, `trackerConditionId`, `additionalCriteria[]` are NOT on `TierEligibilityConfig`. Same resolution options as M-1. _Evidence: `TierEligibilityConfig.java:40-44` (only `kpiType`, `threshold`, `upgradeType`, `expressionRelation`, `conditions` present; no `trackerId`/`additionalCriteria`)._
- **M-3 REQ-37 precondition FALSE today**: `advancedSettings` is nowhere in `intouch-api-v3/src/main` (verified by grep). The reject has no current field to reject. Options: (a) add explicit `@JsonProperty("advancedSettings")` field to DTO that always throws on set — this is the only way to reject a specific field name without affecting other unknowns; (b) rely on Jackson `FAIL_ON_UNKNOWN_PROPERTIES=true` behaviour (need to verify global config); (c) inspect raw JSON before bind. Needs Designer resolution. _Evidence: grep for `advancedSettings\|advanced_settings` in `intouch-api-v3/src/main` returned zero matches._

**LOW (2)**:
- **L-1 G-06.2 deviation**: Hard-flip `downgrade` → `renewal` without deprecation window. Rationale captured in session-memory Q11. Not a blocker; ADR-level decision.
- **L-2 periodType/periodValue classification nuance**: These are physically per-slab in engine (`TierDowngradeSlabConfig.m_periodConfig`) but BA Q10b treats them as program-level for UI simplicity. Read-wide hoist will need to pick a "canonical" slab's values (or validate they're uniform across slabs). Designer/Architect to clarify fan-out semantics for 6b write.

### Summary for Forward Cascade

- **REQs CONFIRMED against code**: 3 (REQ-38 lock already enforced; REQ-55 drift mechanism already wired; Q20 storage classification C7-verified across all 12 fields; FU-01 cancellation C7-verified across 4 evidence points)
- **REQs CONTRADICTED by code**: 0 (no BA claim is refuted by code)
- **REQs UNVERIFIABLE-NET-NEW (precondition verified TRUE)**: 13 (REQ-02, REQ-05, REQ-07, REQ-19, REQ-20 hoist, REQ-21, REQ-22 compute, REQ-25, REQ-26, REQ-27, REQ-35, REQ-36, REQ-49)
- **REQs with PARTIAL precondition (flag for Designer)**: 3 (REQ-33, REQ-34, REQ-37 — see M-1/M-2/M-3)
- **OBSOLETE marker**: REQ-08 (no orphan references that violate contract — existing `TierDowngradeConfig` references are exactly the rename surface area expected for the 6a implementation)
- **Q20 classification**: **STANDS** (periodType/periodValue nuance flagged as L-2, not a blocker)
- **FU-01 cancellation**: **STANDS** (C7-verified)
- **Q13 scope lock**: **HOLDS** (no REQ requires engine/Thrift/Flyway changes)

**Cascade signal to Architect**: Proceed with ADR for 6a wire-layer implementation. Pay particular attention to M-1, M-2, M-3 — the reject-field lists in REQ-33, REQ-34, REQ-37 include fields that do not exist on the current DTOs, so the implementation needs to clarify whether rejects are defensive-forward-looking or whether the REQ-lists should be trimmed. G-06.2 deviation (L-1) should be documented as an explicit ADR with BA-captured rationale.


