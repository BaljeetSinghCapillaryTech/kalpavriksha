---
feature_id: tiers-crud
domain: loyalty-tiers
ticket: raidlc/ai_tier

epics:
  - id: TIER-CRUD
    name: "Tier CRUD APIs"
    confidence: C6
    stories:
      - id: US-1
        name: "Tier Listing with Comparison Matrix"
        complexity: medium
        acceptance_criteria:
          - "GET /v3/tiers?programId={id} returns all tiers ordered by serialNumber"
          - "Per-tier: basic details (name/description/color/status/memberCount), eligibility (threshold per-tier + program-level read-wide hoist), renewal block (Rework #6a Q3 — renamed from downgrade), validity (periodType/periodValue; startDate FIXED-only)"
          - "KPI summary: totalTiers, activeTiers, scheduledTiers, totalMembers"
          - "Cached memberCount (5-15 min refresh)"
          - "Status filter support"
          - "LIVE from SQL (program_slabs); DRAFT/PENDING_APPROVAL from Mongo (Rework #5)"
          - "GET /v3/tiers/{tierId} envelope FLATTENED — tier fields at root, status:'LIVE' discriminator, pendingDraft sub-block reserved at root (Rework #6a Q1/Q2/Q4)"
          - "GET hoists program-level fields read-wide: kpiType/upgradeType/trackerId/trackerConditionId/additionalCriteria[]/expressionRelation/reevaluateOnReturn/dailyEnabled/retainPoints/isDowngradeOnPartnerProgramDeLinkingEnabled (Rework #6a Q24/Q20 — Phase 4 C-8 Option A: validity.periodType and validity.periodValue are per-slab in engine storage and NOT hoisted; they surface per-tier on the flat envelope)"
          - "SLAB_UPGRADE validity.startDate NEVER on wire (Rework #6a Q7)"
          - "FIXED duration computed from startDate+periodValue on read (Rework #6a Q8)"
          - "GET filters conditions with value=='-1' from eligibility.conditions[] and renewal.conditions[] (Rework #6a Q9)"
          - "No benefitIds, no nudges (Rework #5)"
      - id: US-2
        name: "Tier Creation"
        complexity: medium-high
        acceptance_criteria:
          - "POST /v3/tiers creates tier"
          - "Required: programId, name, eligibility.threshold (non-first tier). eligibilityCriteriaType NOT required (Rework #6a Q24 — moved to program-level advanced-settings)"
          - "Accepted fields (Figma wizard scope, Rework #6a Q20): name, description, color, programId, parentId, eligibility.threshold, validity.periodType, validity.periodValue, validity.startDate (FIXED-only), renewal.downgradeTo, renewal.criteriaType, renewal.conditions[]"
          - "MC enabled: -> DRAFT. MC disabled: -> ACTIVE + SQL sync"
          - "Auto serialNumber, name uniqueness, threshold ordering validation"
          - "Field-level validation errors (400 not 500). Error codes 9011-9020 (Rework #6a band; legacy 9001-9010 is Rework #4 validator — Phase 4 Q-OP-1)."
          - "REJECT 400 Class A booleans on wire, error code 9011: reevaluateOnReturn, dailyEnabled, retainPoints, isDowngradeOnPartnerProgramDeLinkingEnabled (Rework #6a Q24 subsumes Q17)"
          - "REJECT 400 Class B program-level eligibility fields on wire, error code 9012: kpiType, upgradeType, trackerId, trackerConditionId, additionalCriteria[], expressionRelation (Rework #6a Q24 subsumes Q18)"
          - "REJECT 400 legacy 'downgrade' field, error code 9013 (hard flip, Rework #6a Q11)"
          - "REJECT 400 nested 'advancedSettings' envelope, error code 9014 (Rework #6a Q22)"
          - "REJECT 400 value=='-1' in eligibility.conditions[] or renewal.conditions[], error code 9015 (Rework #6a Q9)"
          - "REJECT 400 validity.startDate for SLAB_UPGRADE-type, error code 9016 (Rework #6a Q7)"
          - "REJECT 400 renewal.criteriaType != 'Same as eligibility' or non-empty renewal.expressionRelation/conditions[], error code 9017 (Rework #6a Q26 — B1a lock)"
          - "REJECT 400 on POST when validity.periodType is FIXED-family (FIXED, FIXED_CUSTOMER_REGISTRATION, FIXED_LAST_UPGRADE) and validity.periodValue is missing/null/non-positive, error code 9018 (Phase 4 Q-OP-2)"
          - "Null/omitted renewal auto-filled to B1a default by TierRenewalNormalizer (Rework #5 R5-R4)"
      - id: US-3
        name: "Tier Editing (Versioned)"
        complexity: high
        acceptance_criteria:
          - "PUT /v3/tiers/{tierId} updates tier (partial update)"
          - "DRAFT: in-place update. LIVE tier via new UI: new Mongo DRAFT doc (Rework #5)"
          - "On approval: SQL updated in place; Mongo DRAFT -> SNAPSHOT (audit) (Rework #5)"
          - "One pending DRAFT/PENDING_APPROVAL per tier (Rework #5)"
          - "Editable fields (Rework #6a Q3/Q24): name, description, color, eligibility.threshold, validity.periodType, validity.periodValue, validity.startDate (FIXED-only), renewal.downgradeTo, renewal.criteriaType, renewal.conditions[]"
          - "Same REJECT 400 set as US-2 for legacy 'downgrade', Class A booleans, Class B eligibility (NOT validity — per C-8 Option A validity is per-tier), nested advancedSettings, value=='-1', SLAB_UPGRADE startDate, renewal.criteriaType non-B1a (Rework #6a Q3/Q7/Q9/Q11/Q22/Q24/Q26 — Q17/Q18 subsumed by Q24)"
          - "REJECT 400 on PUT when effective post-merge state has FIXED-family validity.periodType without validity.periodValue, error code 9018 (Phase 4 Q-OP-2; merge semantics — payload-only vs payload+stored — deferred to Designer Phase 7)"
      - id: US-4
        name: "Tier Deletion (DRAFT Only — Soft-Delete to DELETED)"
        complexity: low
        acceptance_criteria:
          - "DELETE /v3/tiers/{tierId} sets status=DELETED (DRAFT only)"
          - "409 Conflict if tier not in DRAFT status"
          - "No MC flow — DRAFT deletion is immediate"
          - "No member reassessment — DRAFT tiers have no members"
          - "Audit trail preserved in MongoDB"
        business_rules:
          - "Only DRAFT tiers can be deleted. No PAUSED or STOPPED states."
          - "Tier reordering NOT supported (serialNumber immutable)"
          - "Tier retirement (ACTIVE → STOPPED) deferred to future epic"

  - id: MC-FRAMEWORK
    name: "Generic Maker-Checker Framework"
    confidence: C5
    stories:
      - id: US-5
        name: "Submit for Approval"
        complexity: medium
        acceptance_criteria:
          - "POST /v3/tiers/{tierId}/submit accepts tier changes for approval"
          - "Creates approval request in MongoDB"
          - "Status -> PENDING_APPROVAL"
          - "Notification hook interface"
      - id: US-6
        name: "Approve/Reject"
        complexity: medium-high
        acceptance_criteria:
          - "POST /v3/tiers/{tierId}/approve"
          - "POST /v3/tiers/{tierId}/approvals (comment required)"
          - "Approve: TierApprovalHandler -> Thrift sync"
          - "Reject: -> DRAFT"
          - "GET /v3/approvals"
      - id: US-7
        name: "MC Toggle"
        complexity: low
        acceptance_criteria:
          - "isMakerCheckerEnabled(orgId, programId, entityType)"
          - "Org-level config"
          - "Disabled: immediate ACTIVE. Enabled: DRAFT flow"

dependencies:
  epic_order: [MC-FRAMEWORK, TIER-CRUD]
  note: "MC framework can be built first (Layer 1). Tier CRUD consumes it (Layer 2). Both can be built in parallel using interfaces."
  cross_epic:
    - from: TIER-CRUD
      to: MC-FRAMEWORK
      type: "consumes MakerCheckerService interface"
    - from: TIER-CRUD
      to: "audit-trail-framework (Anuj)"
      type: "future consumer (not this pipeline run)"

api_endpoints:
  - method: GET
    path: "/v3/tiers"
    params: "programId (required), status (optional filter), includeInactive (optional bool)"
    response: "TierListResponse {summary: KpiSummary, tiers: TierConfig[]}"
  - method: POST
    path: "/v3/tiers"
    body: "TierCreateRequest"
    response: "TierConfig"
  - method: PUT
    path: "/v3/tiers/{tierId}"
    body: "TierUpdateRequest"
    response: "TierConfig"
  - method: DELETE
    path: "/v3/tiers/{tierId}"
    response: "void (204) — DRAFT only. 409 if not DRAFT. Soft-delete to DELETED."
  - method: POST
    path: "/v3/tiers/{tierId}/submit"
    body: "TierApprovalRequest {changes}"
    response: "ApprovalRecord"
  - method: POST
    path: "/v3/tiers/{tierId}/approve"
    body: "ApprovalDecision {comment}"
    response: "ApprovalRecord"
  - method: POST
    path: "/v3/tiers/{tierId}/approvals"
    body: "RejectionRequest {comment (required)}"
    response: "ApprovalRecord"
  - method: GET
    path: "/v3/approvals"
    params: "entityType (optional), programId (optional)"
    response: "ApprovalRecord[]"

new_files:
  intouch_api_v3:
    controllers:
      - "src/main/java/com/capillary/intouchapiv3/resources/TierController.java"
      - "src/main/java/com/capillary/intouchapiv3/resources/MakerCheckerController.java"
    facades:
      - "src/main/java/com/capillary/intouchapiv3/tier/TierFacade.java"
      - "src/main/java/com/capillary/intouchapiv3/makerchecker/MakerCheckerFacade.java"
    models:
      - "src/main/java/com/capillary/intouchapiv3/tier/UnifiedTierConfig.java (MongoDB @Document)"
      - "src/main/java/com/capillary/intouchapiv3/tier/model/BasicDetails.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/model/EligibilityCriteria.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/model/RenewalConfig.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/model/DowngradeConfig.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/model/BenefitSummary.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/model/MemberStats.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/enums/TierStatus.java"
      - "src/main/java/com/capillary/intouchapiv3/makerchecker/PendingChange.java (MongoDB @Document)"
      - "src/main/java/com/capillary/intouchapiv3/makerchecker/enums/EntityType.java"
      - "src/main/java/com/capillary/intouchapiv3/makerchecker/enums/ChangeStatus.java"
    services:
      - "src/main/java/com/capillary/makechecker/MakerCheckerService.java (interface)"
      - "src/main/java/com/capillary/makechecker/MakerCheckerServiceImpl.java"
      - "src/main/java/com/capillary/makechecker/ApprovableEntityHandler.java (strategy interface)"
      - "src/main/java/com/capillary/intouchapiv3/tier/TierApprovalHandler.java (implements ApprovableEntityHandler)"
    repositories:
      - "src/main/java/com/capillary/intouchapiv3/tier/TierRepository.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/TierRepositoryImpl.java"
      - "src/main/java/com/capillary/makechecker/ApprovalRepository.java"
    dtos:
      - "src/main/java/com/capillary/intouchapiv3/tier/dto/TierCreateRequest.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/dto/TierUpdateRequest.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/dto/TierListResponse.java"
      - "src/main/java/com/capillary/intouchapiv3/tier/dto/KpiSummary.java"
      - "src/main/java/com/capillary/makechecker/dto/ApprovalRequest.java"
      - "src/main/java/com/capillary/makechecker/dto/ApprovalDecision.java"
    validation:
      - "src/main/java/com/capillary/intouchapiv3/tier/validation/TierValidationService.java"

modified_files:
  emf_parent:
    # Rework #3: No entity/DAO changes needed. SQL only has ACTIVE tiers.
    - "NONE -- ProgramSlab.java, PeProgramSlabDao.java, Flyway migration all removed from scope (Rework #3)"
  thrift:
    - "No IDL changes. Existing methods used via Java wrappers in intouch-api-v3 (ADR-05)."

ddl:
  # Rework #3: No SQL DDL changes needed.
  # ProgramSlab status column, findActiveByProgram(), Flyway migration all removed from scope.
  # SQL only contains ACTIVE tiers (synced via Thrift on approval).

grooming_questions:
  - id: GQ-1
    question: "Pagination for tier listing API?"
    context: "Programs typically have 3-7 tiers. Pagination may be unnecessary overhead."
  - id: GQ-2
    question: "When MC toggled ON, mirror existing ACTIVE tiers to MongoDB?"
    context: "Existing tiers only in SQL. MC flow expects MongoDB docs."
  - id: GQ-3
    question: "Multiple drafts per ACTIVE tier?"
    context: "What if user edits again while a draft is pending?"
  - id: GQ-4
    question: "Benefits linkage: full config or just references?"
    context: "Full config couples tier API to benefits data source."
  - id: GQ-5
    question: "Real notification or hook interface for MC?"
    context: "Hook is faster to build, real notification adds scope."
  - id: GQ-6
    question: "PendingChange stores full snapshot or diff?"
    context: "Snapshot is simpler, diff is more efficient for audit."
  - id: GQ-7
    question: "UX framing for Figma Step 2 'Qualifying conditions' under write-narrow/read-wide contract?"
    context: "Figma places these per-tier; Q20/Q22/Q24 lock them program-level. UI pre-fills from AC-14 read-wide hoist. UX must choose: (a) hide in per-tier create, (b) render read-only with deep-link to advanced-settings. Wire contract is locked — no per-tier override."
    owner: "[Product/Design/UI]"

rework_6a:
  date: "2026-04-22"
  target_phase: 1
  mode: "Mode 5 full cascade"
  scope: "intouch-api-v3 wire layer only (Q13)"
  severity: MODERATE
  q_locks_applied:
    - Q1: "GET envelope flattens — live.* hoisted to root"
    - Q2: "status:'LIVE' discriminator"
    - Q3: "downgrade -> renewal; downgrade.target -> renewal.downgradeTo (Figma-matching)"
    - Q4: "pendingDraft reserved at root (forward-compat dual-block)"
    - Q5c: "Defensive reject multi-tracker eligibility on per-tier wire (subsumed by Q24)"
    - Q7: "Drop validity.startDate for SLAB_UPGRADE (read + write)"
    - Q8: "Compute FIXED duration from startDate + periodValue (no new field)"
    - Q9: "Filter value=='-1' on read; reject on write (error code 9015 per Phase 4 Q-OP-1)"
    - Q10a: "OUT OF SCOPE 6a (deferred to 6b)"
    - Q10b: "OUT OF SCOPE 6a (deferred to 6b)"
    - Q10c: "Per-tier renewal.conditions[]/downgradeTo/criteriaType STAY per-tier"
    - Q11: "Hard flip — legacy 'downgrade' field returns 400"
    - Q12: "Mode 5 full cascade from Phase 1"
    - Q13: "intouch-api-v3 only — no engine changes"
    - Q14: "6a + 6b split"
    - Q15: "SUPERSEDED by Q23"
    - Q16: "periodType = UI 'when to validate tier's renewal conditions'"
    - Q17: "Per-tier POST/PUT rejects Class A booleans (SUBSUMED by Q24)"
    - Q18: "Per-tier POST/PUT rejects Class B eligibility (SUBSUMED by Q24; validity per-tier per C-8 Option A — NOT rejected)"
    - Q20: "Engine storage classification — per-tier vs program-level"
    - Q22: "No nested advancedSettings on per-tier write (write-narrow)"
    - Q23: "Advanced-settings via api_gateway direct to pointsengine-emf/ProgramsApi (no intouch-api-v3 wrapping)"
    - Q24: "Strict asymmetric contract — write-narrow / read-wide"
    - Q25: "Advanced-settings dependency-free (subsumed by Q24)"
    - Q26: "renewal.criteriaType B1a lock + doc rename from 'conditionsToSatisfy'"
    - Q-OP-1: "Phase 4 — error code rebanding to 9011-9020 (legacy 9001-9010 untouched)"
    - Q-OP-2: "Phase 4 — PeriodType enum scope lock (c) + conditional duration required for FIXED-family (error code 9018)"
  fu01_status: "CANCELLED 2026-04-22 — engine already supports multi-tracker via additionalUpgradeCriteriaList. Wire plumbing folds into 6b."
  new_acs:
    US-1: [AC-13, AC-14, AC-15, AC-16, AC-17]
    US-2: [AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18]
    US-3: [AC-10, AC-11, AC-12, AC-13, AC-14, AC-16]
  obsolete_acs:
    US-1: [AC-5, AC-6]  # AC-5 (downgrade block) replaced by AC-4 renewal; AC-6 (benefits) removed Rework #5
  updated_acs:
    US-1: [AC-3, AC-4, AC-10]
    US-2: [AC-2, AC-3, AC-8, AC-9]
    US-3: [AC-3, AC-6, AC-7, AC-15]
  deferred_to_6b:
    endpoint: "GET|PUT|DELETE /api_gateway/loyalty/v1/programs/{programId}/advanced-settings"
    deployment: "api_gateway (nginx) -> pointsengine-emf/ProgramsApi.java direct. No intouch-api-v3 wrapping, no MC, no Thrift IDL change."
  forward_cascade:
    executed: [1]
    pending: [2, 4, 6, "6a", 7, 8, "8b", 9, 10, "10b", "10c", 11]
    skipped: [3, 5]
    skipped_reason: "Phase 3 (UI) + Phase 5 (Research) CONFIRMED — no new screens, no new repos"
---
