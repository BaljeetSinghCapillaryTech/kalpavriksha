---
feature_id: tier-crud
ticket: test_branch_v3
domain: loyalty-tiers

epics:
  - id: E1
    name: Tier CRUD APIs
    confidence: C5
    complexity: medium
    stories:
      - id: US-1
        name: List Tiers
        endpoint: GET /v3/tiers
        confidence: C6
        acceptance_criteria:
          - [ ] Returns all active tiers for program
          - [ ] Full config in response (name, desc, color, KPI, threshold, validity, renewal, downgrade, status)
          - [ ] Ordered by hierarchy (base first)
          - [ ] Excludes soft-deleted by default
          - [ ] includeInactive=true query param shows all
          - [ ] ResponseWrapper format
      - id: US-2
        name: Get Single Tier
        endpoint: GET /v3/tiers/{tierId}
        confidence: C6
        acceptance_criteria:
          - [ ] Returns full tier config
          - [ ] 404 for non-existent or soft-deleted
      - id: US-3
        name: Create Tier
        endpoint: POST /v3/tiers
        confidence: C5
        acceptance_criteria:
          - [ ] Creates in DRAFT status
          - [ ] Field-level validation on required fields
          - [ ] KPI type must match program
          - [ ] Threshold must exceed highest existing tier
          - [ ] Added above highest tier
          - [ ] Structured error responses
      - id: US-4
        name: Update Tier
        endpoint: PUT /v3/tiers/{tierId}
        confidence: C5
        acceptance_criteria:
          - [ ] Same validation as create
          - [ ] Cannot change KPI type
          - [ ] Creates DRAFT version if maker-checker enabled
          - [ ] Rejects update if PENDING_APPROVAL
          - [ ] 404 for non-existent or soft-deleted
      - id: US-5
        name: Soft Delete Tier
        endpoint: DELETE /v3/tiers/{tierId}
        confidence: C4
        acceptance_criteria:
          - [ ] Sets active=0
          - [ ] Cannot delete base tier
          - [ ] Cannot delete if it is downgrade target of another active tier
          - [ ] Excluded from default GET
          - [ ] 404 if already deleted

  - id: E4-MC
    name: Maker-Checker for Tiers
    confidence: C5
    complexity: medium
    stories:
      - id: US-6
        name: Submit Tier for Approval
        endpoint: PUT /v3/requests/TIER/{tierId}/status
        confidence: C5
        acceptance_criteria:
          - [ ] DRAFT → PENDING_APPROVAL
          - [ ] Only DRAFT tiers can be submitted
          - [ ] Uses existing RequestManagementController
          - [ ] TIER added to EntityType enum
          - [ ] Notification to approver
      - id: US-7
        name: Approve / Reject Tier
        endpoint: POST /v3/tiers/{tierId}/review
        confidence: C5
        acceptance_criteria:
          - [ ] APPROVE: PENDING_APPROVAL → ACTIVE
          - [ ] REJECT: PENDING_APPROVAL → DRAFT with mandatory comment
          - [ ] Only PENDING_APPROVAL tiers
          - [ ] Follows UnifiedPromotion review pattern

build_order:
  - step: 1
    description: "Flyway migration: add active + status columns to program_slabs"
    repo: emf-parent
  - step: 2
    description: "Thrift IDL: TierCrudService with CRUD operations"
    repo: emf-parent
  - step: 3
    description: "EMF service + DAO: TierCrudServiceImpl"
    repo: emf-parent
  - step: 4
    description: "intouch-api-v3: TierController, TierFacade, DTOs"
    repo: intouch-api-v3
  - step: 5
    description: "Maker-checker: EntityType.TIER, RequestManagementFacade routing, review endpoint"
    repo: intouch-api-v3

new_files:
  intouch-api-v3:
    - src/main/java/com/capillary/intouchapiv3/resources/TierController.java
    - src/main/java/com/capillary/intouchapiv3/tier/TierFacade.java
    - src/main/java/com/capillary/intouchapiv3/tier/dto/TierRequest.java
    - src/main/java/com/capillary/intouchapiv3/tier/dto/TierResponse.java
    - src/main/java/com/capillary/intouchapiv3/tier/dto/TierReviewRequest.java
    - src/main/java/com/capillary/intouchapiv3/tier/enums/TierStatus.java
  emf-parent:
    - Thrift IDL for TierCrudService (location TBD in codebase research)
    - TierCrudServiceImpl (location TBD)
    - Flyway migration V__add_tier_status_active.sql

modified_files:
  intouch-api-v3:
    - EntityType.java (add TIER)
    - RequestManagementFacade.java (add TIER routing in changeStatus)
  emf-parent:
    - ProgramSlab.java (add active, status fields)

grooming_questions:
  - id: GQ-1
    question: "Are dailyDowngradeEnabled and retainPoints per-tier or per-program?"
    severity: SCOPE
    blocks: field list for TierRequest DTO
  - id: GQ-2
    question: "Soft-deleted tier members: leave in place or force-migrate?"
    severity: FEASIBILITY
    blocks: DELETE endpoint behaviour
  - id: GQ-3
    question: "Include member count in GET /tiers response?"
    severity: SCOPE
    blocks: response DTO design
  - id: GQ-4
    question: "Support PATCH for partial updates alongside PUT?"
    severity: SCOPE
    blocks: controller endpoint design
---
