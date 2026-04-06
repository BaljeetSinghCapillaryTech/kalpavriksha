---
feature_id: tier-crud
ticket: test_branch_v3
domain: loyalty-tiers
scope: E1 (Tier Intelligence) + E4 (API-First Contract) — backend only
epics:
  - id: E1
    name: Tier CRUD APIs
    stories: [US-1, US-2, US-3, US-4, US-5]
  - id: E4-MC
    name: Maker-Checker for Tiers
    stories: [US-6, US-7]
dependencies:
  - EntityType enum extension (intouch-api-v3)
  - RequestManagementFacade routing for TIER (intouch-api-v3)
  - ResponseWrapper + TargetGroupErrorAdvice (existing, reuse)
  - Thrift IDL for tier CRUD (emf-parent, new)
  - ProgramSlab entity modifications (emf-parent)
codebase_sources:
  controller_layer: /Users/baljeetsingh/IdeaProjects/intouch-api-v3
  service_layer: /Users/baljeetsingh/IdeaProjects/emf-parent
  reference_pattern: UnifiedPromotionController, UnifiedPromotionFacade, RequestManagementController
entities:
  existing:
    - name: ProgramSlab
      table: program_slabs
      repo: emf-parent
      changes: add active column (default 1), add status column
    - name: TierConfiguration
      type: DTO
      repo: emf-parent
      changes: none (reuse as-is for downgrade/renewal config)
    - name: EntityType
      type: enum
      repo: intouch-api-v3
      changes: add TIER value
  new:
    - name: TierController
      type: REST controller
      repo: intouch-api-v3
      package: com.capillary.intouchapiv3.resources
    - name: TierFacade
      type: facade/service
      repo: intouch-api-v3
    - name: TierRequest / TierResponse
      type: DTOs
      repo: intouch-api-v3
    - name: TierStatus
      type: enum
      values: [DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED]
      repo: intouch-api-v3
    - name: TierThriftService
      type: Thrift service
      repo: emf-parent
api_endpoints:
  - method: GET
    path: /v3/tiers
    description: List all tiers for a program
    response: ResponseWrapper<List<TierResponse>>
  - method: GET
    path: /v3/tiers/{tierId}
    description: Get single tier detail
    response: ResponseWrapper<TierResponse>
  - method: POST
    path: /v3/tiers
    description: Create new tier (DRAFT status)
    request: TierRequest
    response: ResponseWrapper<TierResponse>
    validation: field-level via Bean Validation + custom validators
  - method: PUT
    path: /v3/tiers/{tierId}
    description: Update tier configuration
    request: TierRequest
    response: ResponseWrapper<TierResponse>
    validation: field-level via Bean Validation + custom validators
  - method: DELETE
    path: /v3/tiers/{tierId}
    description: Soft delete (set active=0)
    response: ResponseWrapper<Void>
  - method: PUT
    path: /v3/requests/TIER/{tierId}/status
    description: Submit for approval / change status
    request: StatusChangeRequest
    response: ResponseWrapper<Void>
    note: reuses existing RequestManagementController
  - method: POST
    path: /v3/tiers/{tierId}/review
    description: Approve or reject tier
    request: TierReviewRequest (approvalStatus, comment)
    response: ResponseWrapper<TierResponse>
schema_changes:
  - table: program_slabs
    type: ALTER TABLE
    changes:
      - column: active
        type: TINYINT(1)
        default: 1
        nullable: false
      - column: status
        type: VARCHAR(30)
        default: "'ACTIVE'"
        nullable: false
        comment: "DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED"
status_lifecycle:
  transitions:
    - from: null
      to: DRAFT
      trigger: POST /tiers (create)
    - from: DRAFT
      to: PENDING_APPROVAL
      trigger: PUT /requests/TIER/{id}/status (SUBMIT_FOR_APPROVAL)
    - from: PENDING_APPROVAL
      to: ACTIVE
      trigger: POST /tiers/{id}/review (APPROVE)
    - from: PENDING_APPROVAL
      to: DRAFT
      trigger: POST /tiers/{id}/review (REJECT)
    - from: ACTIVE
      to: STOPPED
      trigger: PUT /requests/TIER/{id}/status (STOP)
validation_rules:
  - field: name
    rules: [NotBlank, MaxLength(100)]
  - field: eligibilityKpiType
    rules: [NotNull, MustMatchProgramKpiType]
  - field: eligibilityThreshold
    rules: [NotNull, Positive, MustBeHigherThanPreviousTier]
  - field: validityPeriod
    rules: [NotNull, Positive]
  - field: downgradeTarget
    rules: [ValidTierIdOrNull (null for base tier)]
  - field: description
    rules: [MaxLength(500)]
  - field: color
    rules: [ValidHexColor]
confidence_scores:
  overall: C5
  per_story:
    US-1: C6  # GET is straightforward, entities exist
    US-2: C6  # Single GET, straightforward
    US-3: C5  # Create requires validation logic, threshold checks
    US-4: C5  # Update with maker-checker integration
    US-5: C4  # Soft delete — member impact unclear
    US-6: C5  # Follows existing pattern but needs EntityType extension
    US-7: C5  # Follows existing review pattern
---
