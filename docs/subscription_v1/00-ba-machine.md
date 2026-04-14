---
feature_id: subscription-program-revamp
ticket: subscription_v1
domain: loyalty/subscriptions
epic: E3 -- Subscription Programs
scope: E3-US1, E3-US2, E3-US4, E3-US5 (excluding E3-US3 aiRa)
out_of_scope:
  - E1 (Tier Intelligence)
  - E2 (Benefits as a Product)
  - E3-US3 (aiRa-Assisted Creation)
  - E4 (Benefit Categories)
  - Impact Simulation
  - Auditing
  - Maker-checker authorization per user level

entities:
  - name: SubscriptionProgram
    storage: MongoDB (subscription_programs collection) + MySQL (partner_programs) on publish
    new_entity: true (MongoDB collection)
    reuses_mysql: true (partner_programs, supplementary_membership_cycle_details, partner_program_tier_sync_configuration, supplementary_partner_program_expiry_reminder)
    key_fields:
      - subscriptionProgramId (immutable identifier)
      - metadata.orgId
      - metadata.programId
      - metadata.name
      - metadata.status (DRAFT/PENDING_APPROVAL/ACTIVE/PAUSED/SCHEDULED/EXPIRED/ARCHIVED)
      - metadata.subscriptionType (TIER_BASED/NON_TIER)
      - duration.cycleType (DAYS/MONTHS/YEARS)
      - duration.cycleValue
      - tierConfig.isTierBased
      - tierConfig.linkedTierId
      - tierConfig.tierDowngradeOnExit
      - tierConfig.downgradeTargetTierId
      - benefits[] (benefitId references)
      - reminders[] (daysBeforeExpiry, channel)
      - customFields.meta[] / .link[] / .delink[]
      - groupTag
      - parentId (maker-checker versioning)
      - version
  - name: PartnerProgram (existing MySQL)
    storage: MySQL warehouse.partner_programs
    new_entity: false
    key_fields: id, org_id, loyalty_program_id, type, name, description, is_active, is_tier_based, expiry_date
  - name: SupplementaryEnrollment (existing MySQL)
    storage: MySQL warehouse.supplementary_partner_program_enrollment
    new_entity: false
    key_fields: customer_id, partner_program_id, membership_start_date, membership_end_date, is_linked, is_active
  - name: GenericMakerChecker (new)
    storage: Embedded in entity MongoDB documents (parentId/version pattern)
    new_entity: true (shared package, not collection)
    key_concepts: state machine, parentId versioning, publish-on-approve hook

dependencies:
  - emf-parent: existing Thrift endpoint PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram
  - intouch-api-v3: new REST controllers, MongoDB repository, maker-checker package
  - api/prototype: Extended Fields model (EntityType may need new value for subscriptions)
  - cc-stack-crm: MySQL schema reference (read-only, no modifications)

repos_affected:
  - /Users/baljeetsingh/IdeaProjects/intouch-api-v3:
      new_files:
        - subscription/SubscriptionProgram.java (MongoDB @Document)
        - subscription/SubscriptionProgramRepository.java (MongoRepository)
        - subscription/SubscriptionProgramFacade.java
        - subscription/SubscriptionProgramResource.java (REST controller)
        - subscription/dto/* (request/response DTOs)
        - subscription/enums/SubscriptionStatus.java
        - subscription/enums/SubscriptionType.java
        - makechecker/GenericMakerCheckerService.java
        - makechecker/MakerCheckerEntity.java (interface)
        - makechecker/MakerCheckerHooks.java (interface for entity-specific hooks)
        - makechecker/StatusTransition.java
      modified_files:
        - config/EmfMongoConfig.java (may need new collection config)
  - /Users/baljeetsingh/IdeaProjects/emf-parent:
      modified_files:
        - PointsEngineRuleConfigThriftImpl.java (verify/extend for publish-on-approve)
        - PointsEngineRuleService.java (verify createOrUpdatePartnerProgram handles new fields)
  - /Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf:
      potentially_modified: PartnerProgramInfo thrift struct (if new fields needed)

user_stories:
  - id: US-01
    name: Subscription Listing View
    brd_ref: E3-US1
    acceptance_criteria: AC-01 through AC-08
    confidence: C5
    complexity: Medium
  - id: US-02
    name: Subscription Create & Edit
    brd_ref: E3-US2
    acceptance_criteria: AC-09 through AC-30
    confidence: C5
    complexity: High
  - id: US-03
    name: Generic Maker-Checker
    brd_ref: Cross-cutting
    acceptance_criteria: AC-31 through AC-38
    confidence: C4
    complexity: High
  - id: US-04
    name: Lifecycle Management
    brd_ref: E3-US4
    acceptance_criteria: AC-39 through AC-48
    confidence: C4
    complexity: High
  - id: US-05
    name: API Contract
    brd_ref: E3-US5
    acceptance_criteria: Defined by endpoint table
    confidence: C5
    complexity: Medium

key_decisions:
  - KD-04: E3 only scope
  - KD-07: Subscription programs ARE partner programs
  - KD-10: Generic maker-checker (reusable)
  - KD-11: MongoDB metadata + MySQL final data
  - KD-16: Price is Extended Field
  - KD-17: Reuse existing MySQL tier columns
  - KD-22: Clean-room maker-checker implementation
  - KD-25: Publish-on-approve pattern
---
