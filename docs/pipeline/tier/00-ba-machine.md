---
feature_id: tiers-crud
domain: loyalty-tiers
ticket: raidlc/ai_tier
brd_source: "Tiers_Benefits_PRD_v2_AiLed New.docx"
brd_sections:
  - "E1-US1: Tier Listing with Comparison Matrix"
  - "E1-US2: Tier Creation"
  - "E1-US3: Tier Editing"
  - "E1-US4: Maker-Checker Approval Workflow (framework only)"
scope: "Tier CRUD (List, Create, Edit, Delete) + Generic Maker-Checker Framework"
epics:
  - id: TIER-CRUD
    name: "Tier CRUD APIs"
    user_stories: [US-1, US-2, US-3, US-4]
    confidence: C6
  - id: MC-FRAMEWORK
    name: "Generic Maker-Checker Framework"
    user_stories: [US-5, US-6, US-7]
    confidence: C5
dependencies:
  - emf-parent (core entities, strategies, Thrift services)
  - intouch-api-v3 (REST controllers, MongoDB, approval flow)
  - Thrift IDL (sync protocol between intouch-api-v3 and emf-parent)
codebase_sources:
  emf_parent:
    entities:
      - ProgramSlab: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramSlab.java"
      - PartnerProgramSlab: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PartnerProgramSlab.java"
      - CustomerEnrollment: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/CustomerEnrollment.java"
    dtos:
      - TierConfiguration: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/dto/TierConfiguration.java"
      - TierDowngradeSlabConfig: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/TierDowngradeSlabConfig.java"
      - SlabMetaData: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/config/model/SlabMetaData.java"
    enums:
      - SlabUpgradeMode: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/SlabUpgradeMode.java"
      - SlabChangeSource: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/SlabChangeSource.java"
    daos:
      - PeProgramSlabDao: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeProgramSlabDao.java"
      - PeCustomerEnrollmentDao: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeCustomerEnrollmentDao.java"
    services:
      - PointsEngineRuleService_createSlabAndUpdateStrategies: "pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/PointsEngineRuleService.java:2304"
    strategies:
      - SlabUpgradeStrategy: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/api/strategy/SlabUpgradeStrategy.java"
      - SlabUpgradeStrategyImpl: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/SlabUpgradeStrategyImpl.java"
      - ThresholdBasedSlabUpgradeStrategyImpl: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/strategy/ThresholdBasedSlabUpgradeStrategyImpl.java"
      - SlabDowngradeStrategy: "pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/api/strategy/SlabDowngradeStrategy.java"
  intouch_api_v3:
    existing_pattern:
      - UnifiedPromotion: "src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotion.java"
      - UnifiedPromotionFacade: "src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotionFacade.java"
      - UnifiedPromotionRepository: "src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotionRepository.java"
      - EntityOrchestrator: "src/main/java/com/capillary/intouchapiv3/unified/promotion/orchestration/EntityOrchestrator.java"
      - PromotionStatus: "src/main/java/com/capillary/intouchapiv3/unified/promotion/enums/PromotionStatus.java"
      - EmfMongoDataSourceManager: "src/main/java/com/capillary/intouchapiv3/entityManagers/EmfMongoDataSourceManager.java"
    new_tier_apis: "NONE exist today -- all new"
  thrift:
    - emf_thrift: "/Users/ritwikranjan/Desktop/emf-parent/Thrift/thrift-ifaces-emf/emf.thrift"
    - ManualSlabAdjustmentData: "emf.thrift (struct)"
    - CustomerTierTransitionDetails: "emf.thrift (struct)"
    - SlabAction: "emf.thrift (enum: UPGRADE, DOWNGRADE, RENEWAL, EXTEND_CURRENT_TIER_EXPIRY_DATE)"
    - TierChangeType: "emf.thrift (enum: DOWNGRADE, RENEW)"
  peb:
    - TierDowngradeBatchServiceImpl: "src/main/java/com/capillary/shopbook/peb/impl/services/impl/TierDowngradeBatchServiceImpl.java"
    - TierReassessmentServiceImpl: "src/main/java/com/capillary/shopbook/peb/impl/services/impl/TierReassessmentServiceImpl.java"

key_decisions:
  - id: KD-01
    decision: "Scope is E1-US1/US2/US3 + Tier Deletion + Generic MC Framework"
    rationale: "Focused delivery with extensible architecture for future epics"
    source: "BA Q1"
  - id: KD-02
    decision: "Soft-delete via status column on program_slabs. Lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE. DRAFT -> DELETED (terminal). No PAUSED or STOPPED."
    rationale: "Simplified lifecycle. Only DRAFT tiers can be deleted. Tier retirement (ACTIVE -> STOPPED) deferred to future epic."
    source: "BA Q2, Rework #2"
  - id: KD-03
    decision: "Dual-storage: MongoDB for draft/pending, SQL for live"
    rationale: "Follows unified promotion pattern. MongoDB stores full config doc, SQL stores engine-readable entities"
    source: "BA Q3"
  - id: KD-04
    decision: "Cached member counts in listing response"
    rationale: "customer_enrollment is hot table, no existing count-by-slab query, periodic refresh sufficient"
    source: "BA Q4"
  - id: KD-05
    decision: "Full generic maker-checker framework"
    rationale: "Layer 1 shared module. Tiers first consumer, benefits/subscriptions later"
    source: "BA Q5"
  - id: KD-06
    decision: "Versioned edits (parentId pattern from UnifiedPromotion)"
    rationale: "Full rollback, consistent with existing codebase pattern"
    source: "BA Q6"
  - id: KD-07
    decision: "APIs hosted in intouch-api-v3, sync to emf-parent via Thrift"
    rationale: "Same architecture as unified promotions"
    source: "BA Q7"
  - id: KD-08
    decision: "MC toggle per-program + per-entity-type"
    rationale: "Generic framework needs entity-type granularity"
    source: "BA Q8"

schema_changes:
  - table: program_slabs
    change: "ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'"
    migration: "Flyway V-next. Expand-then-contract. Existing rows default to ACTIVE."
    risk: "All existing queries on program_slabs must add status filter."

new_mongodb_collections:
  - name: "unified_tier_configs"
    description: "Full tier configuration documents (draft, pending, active mirror)"
    key_fields: ["orgId", "programId", "tierId", "status", "parentId", "version"]
  - name: "pending_changes"
    description: "Generic maker-checker pending change documents"
    key_fields: ["orgId", "entityType", "entityId", "status", "requestedBy", "reviewedBy"]
---
