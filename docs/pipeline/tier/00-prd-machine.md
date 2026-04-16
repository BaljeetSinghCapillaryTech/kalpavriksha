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
          - "Per-tier: basic details, eligibility, renewal, downgrade, benefits, memberCount"
          - "KPI summary: totalTiers, activeTiers, scheduledTiers, totalMembers"
          - "Cached memberCount (5-15 min refresh)"
          - "Status filter support"
          - "Draft/Pending from MongoDB, Active from MongoDB mirror"
      - id: US-2
        name: "Tier Creation"
        complexity: medium-high
        acceptance_criteria:
          - "POST /v3/tiers creates tier"
          - "Required: name, programId, eligibilityCriteriaType, eligibilityThreshold"
          - "MC enabled: -> DRAFT. MC disabled: -> ACTIVE + SQL sync"
          - "Auto serialNumber, name uniqueness, threshold ordering validation"
          - "Field-level validation errors (400 not 500)"
      - id: US-3
        name: "Tier Editing (Versioned)"
        complexity: high
        acceptance_criteria:
          - "PUT /v3/tiers/{tierId} updates tier"
          - "DRAFT: in-place update. ACTIVE: new DRAFT with parentId"
          - "On approval: new -> ACTIVE, old -> SNAPSHOT"
          - "One pending draft per ACTIVE tier"
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
---
