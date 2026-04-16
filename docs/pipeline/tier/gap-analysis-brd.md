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
| G-3 | **PeProgramSlabDao used in 7+ services.** Adding status filter affects: InfoLookupService (4 sites), PointsEngineRuleService (2 sites), PointsReturnService, ProgramCreationService, PointsEngineServiceManager (2 sites), BulkOrgConfigImportValidator. | grep PeProgramSlabDao | HIGH -- regression risk on core engine code. | Use expand-then-contract migration. Add new `findActiveByProgram()` method, migrate callers incrementally. |
| G-4 | **Threshold values stored in strategy CSV, not per-slab.** BA says "threshold > previous tier" but thresholds are a comma-separated string in strategy properties (`threshold_values`), not a field on ProgramSlab. Validation logic is more complex than implied. | ThresholdBasedSlabUpgradeStrategyImpl.java:164 | MEDIUM -- validation AC needs refinement. | Defer exact validation rules to HLD/LLD. The new MongoDB document WILL store per-tier thresholds, but the SQL sync must map back to the CSV strategy format. |
| G-5 | **EmfMongoDataSourceManager is sharded.** The promotion repo uses `emfMongoDataSourceManager.getAll()` to iterate all MongoDB shards for index creation. Tier documents must also handle multi-shard scenarios. | UnifiedPromotionRepositoryImpl.java:87-91 | MEDIUM -- affects MongoDB repository implementation. | Follow the same sharded MongoDB pattern as UnifiedPromotionRepository. |
| G-6 | **UnifiedPromotion has complex edit flow.** The promotion edit flow creates a child document with parentId and has `DraftDetails`, `ParentDetails` models, `UnifiedPromotionEditOrchestrator`, and `StatusTransitionValidator`. The BA mentions parentId but doesn't account for the full edit orchestration complexity. | UnifiedPromotionFacade.java imports | MEDIUM -- edit flow is more complex than described. | Study UnifiedPromotionEditOrchestrator in Phase 5 (codebase research) to understand the full pattern before designing the tier edit flow. |

## GUARDRAILS Compliance (Preliminary)

| Guardrail | Relevant? | Status |
|-----------|-----------|--------|
| G-01: Multi-timezone | Not directly (tier config is not time-zone sensitive) | N/A |
| G-03: Backward compatibility | YES -- adding status column must not break existing callers | NEEDS ATTENTION (C-3) |
| G-05: Expand-then-contract migrations | YES -- Flyway migration for status column | NEEDS ATTENTION (migration strategy) |
| G-07: Multi-tenancy | YES -- all queries must be scoped by orgId | CONFIRMED (existing pattern) |
| G-12: Idempotency | YES -- tier creation should be idempotent on retry | ADDRESSED in PRD NFRs |

---

## Summary

- **14 claims VERIFIED** (all C6-C7 with file-level evidence)
- **6 gaps FOUND** (1 blocker, 2 high, 3 medium)
- **Key blocker**: No Thrift method exists for tier config sync -- must be resolved before HLD
