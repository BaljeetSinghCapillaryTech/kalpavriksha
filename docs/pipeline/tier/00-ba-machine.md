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
  - "Response envelope: GET returns { live: ..., pendingDraft: ... | null } per tier."  # SUPERSEDED BY rework_6a_invariants — see below
  - "Two DB hits per list page: one SQL query + one Mongo query + in-memory join on slabId."

rework_6a_invariants:
  # 2026-04-22 — intouch-api-v3 wire-layer contract tightening + rename; engine unchanged (Q13)
  - "GET /v3/tiers/{tierId} envelope is FLAT: tier fields hoisted to root, status:'LIVE' discriminator, pendingDraft sub-block reserved at root (null when absent) for forward-compat dual-block (Q1/Q2/Q4)."
  - "Wire block rename: downgrade -> renewal on POST/PUT/GET. Field rename: downgrade.target -> renewal.downgradeTo (Figma-matching). Hard flip, no back-compat window — legacy 'downgrade' field returns 400 InvalidInputException (Q3/Q11)."
  - "reevaluateOnReturn + dailyEnabled + retainPoints + isDowngradeOnPartnerProgramDeLinkingEnabled are program-level (Class A). Rejected on per-tier POST/PUT with 400 InvalidInputException, error code 9011 (Q24 subsumes Q17; Phase 4 Q-OP-1)."
  - "kpiType, upgradeType, trackerId, trackerConditionId, additionalCriteria[], expressionRelation are program-level eligibility (Class B). Rejected on per-tier POST/PUT with 400 InvalidInputException, error code 9012 (Q24 subsumes Q18; Phase 4 Q-OP-1). validity.periodType and validity.periodValue are per-tier (per-slab engine storage: TierDowngradeSlabConfig.periodConfig) — accepted per-tier, NOT rejected (Phase 4 C-8 Option A)."
  - "Per-tier POST/PUT accepts NO nested advancedSettings envelope — write-narrow boundary (Q22)."
  - "Per-tier GET hoists all program-level fields read-wide onto the flattened envelope so UI paints wizard + advanced-settings from one call (Q24 read-wide)."
  - "validity.startDate dropped entirely for SLAB_UPGRADE-type tiers — never on wire, rejected on write (Q7)."
  - "FIXED-family validity duration computed downstream from existing startDate + periodValue — no new storage field (Q8). Read-side is null-safe for legacy tiers with missing periodValue (Phase 4 Q-OP-2)."
  - "Conditional duration requirement: FIXED-family periodType (FIXED, FIXED_CUSTOMER_REGISTRATION, FIXED_LAST_UPGRADE) on POST/PUT requires validity.periodValue present + non-null + positive integer. Missing/null/non-positive rejected 400 InvalidInputException, error code 9018 (Phase 4 Q-OP-2). SLAB_UPGRADE-family periodType (SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC) does NOT require periodValue — engine is event-driven."
  - "PeriodType enum scope: 6a handles SLAB_UPGRADE explicitly (REQ-21 drop + REQ-36 startDate reject). FIXED_CUSTOMER_REGISTRATION, FIXED_LAST_UPGRADE, SLAB_UPGRADE_CYCLIC are pass-through from Rework #5 — no new explicit wire-level handling (Phase 4 Q-OP-2 scope lock; partial resolution of contradictions.md C-12)."
  - "GET path filters conditions with value=='-1' (string-match) for both eligibility.conditions[] and renewal.conditions[]. POST/PUT rejects the same with 400 InvalidInputException, error code 9015 (Q9 — read/write lockstep; Phase 4 Q-OP-1)."
  - "renewal.criteriaType wire field: B1a lock preserved — only 'Same as eligibility' accepted; any other value rejected 400. renewal.expressionRelation + renewal.conditions[] must be null/empty on wire (Q26)."
  - "Doc-only rename: 'conditionsToSatisfy' (never in code) -> 'criteriaType' — matches TierRenewalConfig.java:57 (Q26)."
  - "Advanced-settings endpoint (GET|PUT|DELETE /api_gateway/loyalty/v1/programs/{programId}/advanced-settings) is OUT OF SCOPE in 6a — deferred to 6b. Deployed via api_gateway direct to pointsengine-emf/ProgramsApi.java (Q14, Q23)."
  - "FU-01 CANCELLED 2026-04-22: engine already supports multi-tracker via additionalUpgradeCriteriaList (ThresholdBasedSlabUpgradeStrategyImpl.java:51,229-239). Wire plumbing folds into 6b."
  - "No engine repo changes, no Thrift IDL change, no Flyway migration in 6a — wire-layer only in intouch-api-v3 (Q13)."

rework_6a_req_delta:
  added:
    - REQ-19  # GET filters value=='-1' (Q9)
    - REQ-20  # GET read-wide hoist of program-level fields (Q24/Q20)
    - REQ-21  # SLAB_UPGRADE validity.startDate dropped on wire (Q7)
    - REQ-22  # FIXED duration computed from existing inputs (Q8)
    - REQ-33  # POST/PUT rejects Class A booleans (Q24 subsumes Q17)
    - REQ-34  # POST/PUT rejects Class B eligibility (Q24 subsumes Q18; validity per-tier per C-8 Option A)
    - REQ-35  # POST/PUT rejects value=='-1' (Q9)
    - REQ-36  # POST/PUT rejects validity.startDate for SLAB_UPGRADE (Q7)
    - REQ-37  # POST/PUT rejects nested advancedSettings (Q22)
    - REQ-38  # renewal.criteriaType B1a lock + doc rename (Q26)
    - REQ-55  # Cross-UI interaction AC (Rework #5 formalised)
    - REQ-56  # Conditional duration required for FIXED-family periodType (Phase 4 Q-OP-2)
  updated:
    - REQ-02  # GET envelope flattened (Q1/Q2/Q4)
    - REQ-05  # Per-tier READ body eligibility narrowed
    - REQ-07  # downgrade block renamed to renewal + downgradeTo (Q3/Q26)
    - REQ-22  # FIXED duration computation made null-safe for legacy tiers (Phase 4 Q-OP-2)
    - REQ-25  # eligibilityCriteriaType removed from required (Q24)
    - REQ-26  # Per-tier POST body narrowed to Figma wizard scope (Q3/Q7/Q22/Q24/Q26)
    - REQ-27  # Legacy 'downgrade' hard-flipped to 400 (Q11)
    - REQ-49  # PUT editable fields narrowed + renames applied (Q3/Q24)
  obsolete:
    - REQ-08  # Downgrade block AC (superseded by REQ-07 renewal block)

rework_6a_deferred_to_6b:
  endpoint: "GET|PUT|DELETE /api_gateway/loyalty/v1/programs/{programId}/advanced-settings"
  deployment: "api_gateway (nginx) -> pointsengine-emf/ProgramsApi.java direct. No intouch-api-v3 wrapping, no maker-checker, no Thrift IDL change."
  payload_fields:
    class_a_booleans:
      - reevaluateOnReturn
      - dailyEnabled
      - retainPoints
      - isDowngradeOnPartnerProgramDeLinkingEnabled
    program_level_eligibility:
      - kpiType
      - upgradeType
      - trackerId
      - trackerConditionId
      - additionalCriteria
      - expressionRelation
      - trackingPeriod
    # Phase 4 C-8 Option A (2026-04-22): validity.periodType + validity.periodValue are per-slab
    # in engine storage (TierDowngradeSlabConfig.periodConfig) — NOT in 6b advanced-settings.
    # They stay on per-tier POST/PUT /v3/tiers.
    program_level_validity:
      []  # empty — no program-level validity fields under Option A
      # renewal-extension mechanism (existing engine field; exact wire name tied to Q16 — surfaced in 6b if/when needed)
  excluded_from_payload:
    - isActive
    - downgradeConfirmation
    - renewalConfirmation
    - reminders
    - "validity.periodType (per-tier, per-slab storage)"
    - "validity.periodValue (per-tier, per-slab storage)"

rework_6a_error_codes:
  banding_locked_by: "Phase 4 Q-OP-1"
  legacy_band:
    range: "9001-9010"
    scope: "pre-existing Rework #4 partial-update validator range; untouched by 6a"
  rework_6a_band:
    range: "9011-9020"
    scope: "Rework #6a hard-flip reject band (C-7 Hybrid + Phase 4 Q-OP-1)"
    allocations:
      "9011":
        req: REQ-33
        reject_reason: "Class A program-level boolean on per-tier wire"
        q_lock: "Q24 (subsumes Q17)"
      "9012":
        req: REQ-34
        reject_reason: "Class B program-level eligibility on per-tier wire"
        q_lock: "Q24 (subsumes Q18); amended by C-8 Option A — validity per-tier, NOT rejected"
      "9013":
        req: REQ-27
        reject_reason: "Legacy `downgrade` field present"
        q_lock: "Q11 (hard-flip)"
      "9014":
        req: REQ-37
        reject_reason: "Nested `advancedSettings` envelope on per-tier wire"
        q_lock: "Q22 (write-narrow boundary)"
      "9015":
        req: REQ-35
        reject_reason: "`value == '-1'` sentinel on eligibility or renewal conditions"
        q_lock: "Q9 (read/write lockstep with REQ-19)"
      "9016":
        req: REQ-36
        reject_reason: "`validity.startDate` on SLAB_UPGRADE-type tier"
        q_lock: "Q7 (engine event-driven)"
      "9017":
        req: REQ-38
        reject_reason: "Non-B1a renewal contract violation (criteriaType != 'Same as eligibility' OR non-empty expressionRelation/conditions)"
        q_lock: "Q26 (B1a lock)"
      "9018":
        req: REQ-56
        reject_reason: "FIXED-family periodType (FIXED, FIXED_CUSTOMER_REGISTRATION, FIXED_LAST_UPGRADE) without required validity.periodValue"
        q_lock: "Phase 4 Q-OP-2 (scope lock + conditional duration)"
      "9019-9020":
        req: null
        reject_reason: "reserved for 6a runtime-discovered rejects"
        q_lock: null

rework_6a_q_lock_coverage:
  Q1: [REQ-02]            # Envelope flattens
  Q2: [REQ-02]            # live.* hoisted to root
  Q3: [REQ-07, REQ-26, REQ-27, REQ-49]  # downgrade -> renewal, target -> downgradeTo
  Q4: [REQ-02]            # pendingDraft reserved at root
  Q5c: [REQ-34]           # multi-tracker defensive reject (subsumed by Q24)
  Q7: [REQ-21, REQ-26, REQ-36]
  Q8: [REQ-22]
  Q9: [REQ-19, REQ-35]
  Q10a: ["OUT OF SCOPE 6a — deferred to 6b"]
  Q10b: ["OUT OF SCOPE 6a — deferred to 6b"]
  Q10c: [REQ-26, REQ-49]  # Per-tier renewal.conditions[]/downgradeTo/criteriaType STAY per-tier
  Q11: [REQ-27]           # Hard flip, no back-compat
  Q12: ["Mode 5 cascade — operational decision, not an AC"]
  Q13: ["Invariant in rework_6a_invariants — intouch-api-v3 only"]
  Q14: ["6a/6b split — operational decision, out-of-scope note in 00-ba.md Scope"]
  Q15: ["SUPERSEDED by Q23"]
  Q16: [REQ-26, REQ-49]   # periodType = UI 'when to validate tier's renewal conditions' — per-tier wire per C-8 Option A
  Q17: [REQ-33]           # Class A booleans rejected (SUBSUMED by Q24 — kept for grep traceability)
  Q18: [REQ-34]           # Class B rejected (SUBSUMED by Q24 — kept for grep traceability)
  Q20: [REQ-20, REQ-26]   # Engine storage classification
  Q22: [REQ-37]           # No nested advancedSettings
  Q23: ["OUT OF SCOPE 6a — deferred to 6b endpoint deployment"]
  Q24: [REQ-20, REQ-33, REQ-34]  # Strict asymmetric contract
  Q25: ["Advanced-settings dependency-free — subsumed by Q24; 6b scope"]
  Q26: [REQ-07, REQ-38]   # criteriaType lock + doc rename
  FU-01: ["CANCELLED 2026-04-22 — engine already supports. Wire plumbing folds into 6b. 6a defensive reject stands (REQ-34)."]
  Q-OP-1: [REQ-27, REQ-33, REQ-34, REQ-35, REQ-36, REQ-37, REQ-38, REQ-40]  # Error code rebanding 9011-9020 (Phase 4 Q-OP-1)
  Q-OP-2: [REQ-22, REQ-56]  # PeriodType scope lock + conditional duration required for FIXED family (Phase 4 Q-OP-2; partial resolution of contradictions.md C-12)
  Q-OP-3: ["BA §2.4 constraint 'new UI is sole consumer' — upgraded C5 → C6 via codebase audit across 16 repos (zero internal backend callers). Partial resolution of contradictions.md C-17; residual C5 flagged to Phase 11 Reviewer for deploy-time access-log scan. Evidence: q-op-3-consumer-audit.md."]
---
