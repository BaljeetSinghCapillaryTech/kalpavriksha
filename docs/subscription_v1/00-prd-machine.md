---
feature_id: subscription-program-revamp
ticket: subscription_v1
domain: loyalty/subscriptions
version: 1.0
generated_from: 00-ba.md, 00-ba-machine.md

epics:
  - id: EP-01
    name: Subscription CRUD + Listing
    stories: [US-01, US-02]
    confidence: C5
    complexity: High
    depends_on: [EP-02]
    estimated_new_files: 8
    estimated_modified_files: 1

  - id: EP-02
    name: Generic Maker-Checker
    stories: [US-03]
    confidence: C4
    complexity: High
    depends_on: []
    estimated_new_files: 5
    estimated_modified_files: 0

  - id: EP-03
    name: Lifecycle & Enrollment
    stories: [US-04]
    confidence: C4
    complexity: High
    depends_on: [EP-01]
    estimated_new_files: 3
    estimated_modified_files: 2

  - id: EP-04
    name: API Contract Surface
    stories: [US-05]
    confidence: C5
    complexity: Medium
    depends_on: [EP-01, EP-02, EP-03]
    estimated_new_files: 4
    estimated_modified_files: 0

stories:
  - id: US-01
    name: Subscription Listing View
    epic: EP-01
    acceptance_criteria:
      - "[ ] GET /v3/subscriptions returns paginated list with stats"
      - "[ ] Header stats: Total, Active, Scheduled, Subscribers"
      - "[ ] Multi-select status filter"
      - "[ ] Case-insensitive search on name + description"
      - "[ ] Sorting on Subscribers, Last Modified, Name"
      - "[ ] Grouped view by group_tag"
      - "[ ] Benefits sub-query with tier indicator"
      - "[ ] Row actions: Edit, Duplicate, Deactivate, Archive"

  - id: US-02
    name: Subscription Create & Edit
    epic: EP-01
    acceptance_criteria:
      - "[ ] POST creates DRAFT in MongoDB with validation"
      - "[ ] PUT updates existing DRAFT"
      - "[ ] PUT on ACTIVE creates versioned DRAFT (maker-checker)"
      - "[ ] Structured field-level validation errors"
      - "[ ] Tier-based: linkedTierId required"
      - "[ ] Downgrade: downgradeTargetTierId required if enabled"
      - "[ ] Duplicate with (Copy) suffix"
      - "[ ] 3-level custom fields (META, LINK, DELINK)"
      - "[ ] Up to 5 reminders with days + channel"

  - id: US-03
    name: Generic Maker-Checker
    epic: EP-02
    acceptance_criteria:
      - "[ ] MakerCheckerEntity interface"
      - "[ ] MakerCheckerHooks interface with pluggable pre/post hooks"
      - "[ ] GenericMakerCheckerService with submitForApproval, approve, reject, listPending"
      - "[ ] State machine: DRAFT -> PENDING_APPROVAL -> ACTIVE / DRAFT"
      - "[ ] Edit-of-active: parentId + version pattern"
      - "[ ] Publish-on-approve: entity's onPublish hook writes to MySQL"
      - "[ ] Concurrent modification protection"

  - id: US-04
    name: Lifecycle Management
    epic: EP-03
    acceptance_criteria:
      - "[ ] 7-state lifecycle (Draft, PendingApproval, Scheduled, Active, Paused, Expired, Archived)"
      - "[ ] Valid transition enforcement"
      - "[ ] Pause/Resume actions"
      - "[ ] Archive (permanent, read-only)"
      - "[ ] Future-dated enrollment (PENDING state)"
      - "[ ] Nightly activation job"
      - "[ ] Atomic reschedule of PENDING enrollments"
      - "[ ] Tier downgrade on exit event"

  - id: US-05
    name: API Contract
    epic: EP-04
    acceptance_criteria:
      - "[ ] 9 configuration endpoints in /v3/subscriptions"
      - "[ ] 4 enrollment endpoints extended in v2/partnerProgram"
      - "[ ] All endpoints multi-tenant (orgId filtered)"
      - "[ ] Structured validation error responses"

api_signatures:
  - method: GET
    path: /v3/subscriptions
    request: "programId: int, status: String[], search: String, sort: String, groupBy: String, page: int, size: int"
    response: "Page<SubscriptionProgramResponse>"
  - method: POST
    path: /v3/subscriptions
    request: SubscriptionProgramRequest
    response: SubscriptionProgramResponse
  - method: GET
    path: /v3/subscriptions/{id}
    request: "-"
    response: SubscriptionProgramResponse
  - method: PUT
    path: /v3/subscriptions/{id}
    request: SubscriptionProgramRequest
    response: SubscriptionProgramResponse
  - method: PUT
    path: /v3/subscriptions/{id}/status
    request: StatusChangeRequest
    response: SubscriptionProgramResponse
  - method: GET
    path: /v3/subscriptions/{id}/benefits
    request: "-"
    response: "List<BenefitReference>"
  - method: POST
    path: /v3/subscriptions/{id}/benefits
    request: BenefitLinkRequest
    response: SubscriptionProgramResponse
  - method: GET
    path: /v3/subscriptions/approvals
    request: "orgId: long"
    response: "List<SubscriptionProgramResponse>"
  - method: POST
    path: /v3/subscriptions/approvals
    request: "ReviewRequest (subscriptionId, approvalStatus, comment)"
    response: SubscriptionProgramResponse

file_tree:
  new_files:
    intouch-api-v3:
      - src/main/java/com/capillary/intouchapiv3/subscription/SubscriptionProgram.java
      - src/main/java/com/capillary/intouchapiv3/subscription/SubscriptionProgramRepository.java
      - src/main/java/com/capillary/intouchapiv3/subscription/SubscriptionProgramFacade.java
      - src/main/java/com/capillary/intouchapiv3/subscription/SubscriptionProgramResource.java
      - src/main/java/com/capillary/intouchapiv3/subscription/dto/SubscriptionProgramRequest.java
      - src/main/java/com/capillary/intouchapiv3/subscription/dto/SubscriptionProgramResponse.java
      - src/main/java/com/capillary/intouchapiv3/subscription/dto/StatusChangeRequest.java
      - src/main/java/com/capillary/intouchapiv3/subscription/dto/ReviewRequest.java
      - src/main/java/com/capillary/intouchapiv3/subscription/dto/BenefitLinkRequest.java
      - src/main/java/com/capillary/intouchapiv3/subscription/enums/SubscriptionStatus.java
      - src/main/java/com/capillary/intouchapiv3/subscription/enums/SubscriptionType.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/Duration.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/ExpiryConfig.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/TierConfig.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/Reminder.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/CustomFieldConfig.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/BenefitReference.java
      - src/main/java/com/capillary/intouchapiv3/subscription/model/SubscriptionMetadata.java
      - src/main/java/com/capillary/intouchapiv3/subscription/service/SubscriptionPublishService.java
      - src/main/java/com/capillary/intouchapiv3/subscription/validation/SubscriptionValidatorService.java
      - src/main/java/com/capillary/intouchapiv3/makechecker/MakerCheckerEntity.java
      - src/main/java/com/capillary/intouchapiv3/makechecker/MakerCheckerHooks.java
      - src/main/java/com/capillary/intouchapiv3/makechecker/GenericMakerCheckerService.java
      - src/main/java/com/capillary/intouchapiv3/makechecker/MakerCheckerStatus.java
      - src/main/java/com/capillary/intouchapiv3/makechecker/StatusTransition.java
  modified_files:
    intouch-api-v3:
      - src/main/java/com/capillary/intouchapiv3/config/EmfMongoConfig.java (new collection registration)
    emf-parent:
      - pointsengine-emf/src/main/java/.../PointsEngineRuleConfigThriftImpl.java (verify publish path)
      - pointsengine-emf/src/main/java/.../PointsEngineRuleService.java (verify createOrUpdatePartnerProgram)

ddl:
  new_tables: []
  altered_tables: []
  notes: "No MySQL schema changes. All new fields stored in MongoDB. Existing MySQL tables written on publish-on-approve via existing columns."

grooming_questions:
  - id: GQ-01
    question: "Maker-checker scope: per-program or global? How toggled?"
    category: SCOPE
    priority: BLOCKER
  - id: GQ-02
    question: "Benefit linkage: exclusive to one subscription or shareable?"
    category: SCOPE
    priority: BLOCKER
  - id: GQ-03
    question: "Extended Fields EntityType: Can we add SUBSCRIPTION to api/prototype?"
    category: FEASIBILITY
    priority: BLOCKER
  - id: GQ-04
    question: "Archived subscriptions with active enrollments: complete cycle or terminate?"
    category: SCOPE
    priority: HIGH
  - id: GQ-05
    question: "supplementary_membership_history action enum: need new values for PAUSED/RESUMED/ARCHIVED?"
    category: FEASIBILITY
    priority: HIGH
  - id: GQ-06
    question: "backup_partner_program_id vs migrate_on_expiry: same or different?"
    category: SCOPE
    priority: MEDIUM
  - id: GQ-07
    question: "Nightly activation job: existing infra or new cron needed?"
    category: FEASIBILITY
    priority: HIGH
  - id: GQ-08
    question: "Subscriber count in listing: live query or cached count?"
    category: FEASIBILITY
    priority: MEDIUM
---
