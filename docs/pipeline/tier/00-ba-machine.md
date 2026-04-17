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
    decision: "Soft-delete via status in MongoDB only. Lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE. DRAFT -> DELETED (terminal). No PAUSED or STOPPED. No SQL status column (Rework #3 -- SQL only has ACTIVE tiers)."
    rationale: "Simplified lifecycle. Only DRAFT tiers can be deleted. Tier retirement (ACTIVE -> STOPPED) deferred to future epic."
    source: "BA Q2, Rework #2"
  - id: KD-03
    decision: "Dual-storage: MongoDB for draft/pending + audit SNAPSHOTs, SQL for live (SQL is single source of truth for LIVE). Rework #5 upheld dual-storage with sharpened boundaries."
    rationale: "Follows unified promotion pattern. SQL is always read for LIVE state; Mongo holds in-flight + audit only."
    source: "BA Q3, Rework #5 Q-3"
  - id: KD-04
    decision: "Cached member counts in listing response"
    rationale: "customer_enrollment is hot table, no existing count-by-slab query, periodic refresh sufficient"
    source: "BA Q4"
  - id: KD-05
    decision: "Full generic maker-checker framework (Baljeet's makechecker/ package — ApprovableEntity, ApprovableEntityHandler<T>, MakerCheckerService<T>, SAGA pattern)"
    rationale: "Layer 1 shared module. Tiers first consumer, benefits/subscriptions later"
    source: "BA Q5"
  - id: KD-06
    decision: "Versioned edits: editing a LIVE tier via new UI creates a NEW Mongo DRAFT doc. On approval, SQL is updated in place; Mongo doc transitions PENDING_APPROVAL -> SNAPSHOT (audit-only)."
    rationale: "Matches unified promotion pattern; SNAPSHOTs give audit trail without interfering with LIVE reads."
    source: "BA Q6, Rework #5 Q-1b + Q-2b"
  - id: KD-07
    decision: "APIs hosted in intouch-api-v3, sync to emf-parent via Thrift"
    rationale: "Same architecture as unified promotions"
    source: "BA Q7"
  - id: KD-08
    decision: "MC toggle per-program + per-entity-type — applies only to new-UI writes (Rework #5). Old UI writes always bypass MC and hit SQL directly via legacy endpoints."
    rationale: "Preserves legacy compatibility; MC is a new-UI feature."
    source: "BA Q8, Rework #5 Q-1b"
  - id: KD-09
    decision: "Rework #5: Unified read surface. New /v3/tiers API returns ALL tiers (legacy SQL-origin + new-UI-origin) via a read-only SQL->DTO converter for legacy. No bootstrap migration. ADR-06 reversed."
    rationale: "Both UIs must see both tier types. Avoids backfill and split-brain read behaviour."
    source: "Rework #5 Q-C1, Q-1a, Q-4, Q-5"
  - id: KD-10
    decision: "Rework #5: Dual write paths. Old UI -> legacy direct-SQL (no MC). New UI -> Mongo DRAFT -> MC -> Thrift -> SQL."
    rationale: "MC is a new-UI feature. Legacy endpoints are untouched; this is fully backward-compatible."
    source: "Rework #5 Q-1b"
  - id: KD-11
    decision: "Rework #5: Envelope response shape. GET returns { live: ..., pendingDraft: ... | null } per tier. LIVE from SQL; pendingDraft from Mongo (DRAFT/PENDING_APPROVAL only)."
    rationale: "Single round-trip for approval review. Bounded scale (~50 tiers/program). No N+1 reads."
    source: "Rework #5 Q-3b"
  - id: KD-12
    decision: "Rework #5: Drift detection at approval. DRAFTs capture meta.basisSqlSnapshot at creation. preApprove re-reads SQL; any drift blocks approval."
    rationale: "MC remains a meaningful gate even when old UI edits concurrently. Conservative policy: any drift blocks (revisit if frictional)."
    source: "Rework #5 Q-2a"
  - id: KD-13
    decision: "Rework #5: SNAPSHOT semantics = audit-only, write-once-at-approval, never reconciled with later legacy edits. Carries meta.approvedAt + meta.approvedBy."
    rationale: "SNAPSHOT is the approval audit record, not a mirror of SQL. History view surfaces drift visually via a caveat label."
    source: "Rework #5 Q-2b"
  - id: KD-14
    decision: "Rework #5: Single active DRAFT/PENDING_APPROVAL per tier (per-tier scope). Enforced by app-level pre-check + Mongo partial unique index on (orgId, programId, slabId) where status IN [DRAFT, PENDING_APPROVAL]."
    rationale: "Prevents concurrent conflicting DRAFTs. App check gives friendly error; DB index handles races."
    source: "Rework #5 Q-9a + Q-9b"
  - id: KD-15
    decision: "Rework #5: Name collision defense in 3 layers — app check at DRAFT creation, re-check at approval, SQL UNIQUE(program_id, name) backstop."
    rationale: "Race-safe without over-constraining. Old-UI creates during a pending DRAFT are caught at approval or by the SQL constraint."
    source: "Rework #5 Q-1b-i"
  - id: KD-16
    decision: "Rework #5: Schema cleanup — drop nudges, benefitIds, updatedViaNewUI, basicDetails.startDate/endDate. Hoist basicDetails + metadata to root of UnifiedTierConfig."
    rationale: "Reduce schema noise; align with UI. Tiers don't know about benefits (Benefits epic owns the link)."
    source: "Rework #5 Q-7"
  - id: KD-17
    decision: "Rework #5: Rename unifiedTierId -> tierUniqueId (mechanical). Rename metadata.sqlSlabId -> slabId (root-level after hoist). No functional change."
    rationale: "Clearer, shorter names. sqlSlabId is just the SQL program_slabs.id -> 'slabId' is accurate and shorter."
    source: "Rework #5 Q-7e + Q-8"
  - id: KD-18
    decision: "Rework #5: SQL program_slabs gains updatedBy, approvedBy, approvedAt columns. createdBy explicitly NOT added. Legacy writes set only updatedBy; MC-push writes set all three."
    rationale: "Minimal audit enrichment for both legacy and MC flows without forcing legacy writes to backfill createdBy."
    source: "Rework #5 (explicit user decision in Q-7b follow-up)"
  - id: KD-19
    decision: "Rework #5: parentId = parent tier's slabId (SQL program_slabs.id). Parent must be LIVE (not DRAFT/PENDING). Self-reference rejected. Cycle prevention flagged for LLD."
    rationale: "Works uniformly for legacy and new-UI-origin parents. No cross-store correlation needed."
    source: "Rework #5 Q-6"

schema_changes:
  # Rework #3: No status column. Rework #5: add audit columns (updatedBy, approvedBy, approvedAt).
  - table: program_slabs
    change: "Rework #5: ADD COLUMN updatedBy VARCHAR, approvedBy VARCHAR, approvedAt DATETIME. createdBy explicitly NOT added."
    migration: "Flyway forward + rollback — detailed in 01b-migrator.md"
    risk: "Nullable columns; backward-compatible. Legacy writes set updatedBy only. MC-push writes set all three."
    rework_source: "Rework #5"

new_mongodb_collections:
  - name: "unified_tier_configs"
    description: "Tier configuration documents (DRAFT, PENDING_APPROVAL, SNAPSHOT). After Rework #5: basicDetails + metadata hoisted to root; nudges/benefitIds/updatedViaNewUI dropped; unifiedTierId renamed to tierUniqueId; metadata.sqlSlabId renamed to slabId (root)."
    key_fields: ["orgId", "programId", "slabId", "status", "parentId", "tierUniqueId", "version"]
    indexes:
      - "(orgId, programId, status) — for list/approval queue queries"
      - "(orgId, programId, slabId) PARTIAL UNIQUE where status IN [DRAFT, PENDING_APPROVAL] — enforces single-active-draft per tier AND covers 'does tier X have a pending change?' lookups (Rework #5)"
  - name: "pending_changes"
    description: "Generic maker-checker pending change documents"
    key_fields: ["orgId", "entityType", "entityId", "status", "requestedBy", "reviewedBy"]

rework_5_invariants:
  - "SQL program_slabs is the single source of truth for LIVE tier state (both legacy and new-UI-origin tiers)."
  - "Old UI writes continue via legacy direct-SQL path; never gated by MC; never touch Mongo."
  - "New UI writes always go Mongo DRAFT -> MC -> Thrift -> SQL."
  - "DRAFTs capture meta.basisSqlSnapshot at creation; approval re-reads SQL and blocks on any drift."
  - "SNAPSHOT docs are audit-only, write-once-at-approval, never reconciled with later legacy edits."
  - "At most one DRAFT/PENDING_APPROVAL per tier (per-tier scope). Enforced by app check + Mongo partial unique index."
  - "Name uniqueness defended in 3 layers: app check at DRAFT creation, re-check at approval, SQL UNIQUE(program_id, name)."
  - "Response envelope: GET returns { live: ..., pendingDraft: ... | null } per tier."
  - "Two DB hits per list page: one SQL query + one Mongo query + in-memory join on slabId."
---
