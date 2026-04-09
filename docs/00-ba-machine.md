---
feature: Subscription-CRUD
ticket: aidlc-demo-v2
phase: 1
type: ba-machine
version: 1.0
date: 2026-04-09
scope:
  in:
    - E3-US2: Create & Edit Subscription Flow (API)
    - E3-US4: Subscription Lifecycle Management
    - E3-US5: API Contract for Subscriptions
    - Maker-Checker: Approval workflow
    - Benefit-Linking: Store benefit IDs
  out:
    - E3-US1: Listing View (UI)
    - E3-US3: aiRa Subscription Creation
    - E1: Tier Intelligence
    - E2: Benefits as a Product
    - E4: Benefit Categories
    - Simulation API
    - Context API (aiRa)
    - Webhook/event firing
    - Reminder triggering
    - Custom field enforcement at enrollment
---

# Entities

## UnifiedSubscription (NEW -- MongoDB)
- location: intouch-api-v3
- collection: unified_subscriptions
- storage: MongoDB (EmfMongoConfig, emfMongoTemplate)
- pattern: follows UnifiedPromotion @Document pattern
- fields:
  - objectId: String (MongoDB auto, @Id)
  - unifiedSubscriptionId: String (immutable UUID, generated on create)
  - metadata.name: String (required, unique per org)
  - metadata.description: String (optional)
  - metadata.orgId: Long (from auth context)
  - metadata.programId: String
  - metadata.status: SubscriptionStatus enum
  - metadata.createdOn: Date
  - metadata.lastModifiedOn: Date
  - metadata.createdBy: Long
  - metadata.lastModifiedBy: Long
  - subscriptionType: String (TIER_BASED | NON_TIER)
  - duration.value: Integer (required)
  - duration.unit: String (DAYS | MONTHS | YEARS)
  - price.amount: BigDecimal (optional, null = free)
  - price.currency: String (ISO 4217)
  - expiryDate: Date (optional)
  - restrictToOneActivePerMember: Boolean (default false)
  - migrateOnExpiry.enabled: Boolean
  - migrateOnExpiry.targetSubscriptionId: String
  - linkedTierId: String (required if TIER_BASED)
  - tierDowngradeOnExit.enabled: Boolean
  - tierDowngradeOnExit.downgradeTargetTierId: String
  - benefitIds: List<String> (plain ID references)
  - reminders: List<Reminder> (max 5, embedded)
  - customFields.meta: List<Long> (extended field IDs)
  - customFields.link: List<Long>
  - customFields.delink: List<Long>
  - customFields.pause: List<Long>
  - customFields.resume: List<Long>
  - parentId: String (maker-checker versioning)
  - version: Integer (starts 1)
  - comments: String (review comment)
  - groupTag: String (optional)

## SubscriptionStatus (NEW -- enum)
- location: intouch-api-v3
- values: DRAFT, PENDING_APPROVAL, SCHEDULED, ACTIVE, PAUSED, EXPIRED, ARCHIVED

## SubscriptionAction (NEW -- enum)
- location: intouch-api-v3
- values: SUBMIT_FOR_APPROVAL, APPROVE, REJECT, PAUSE, RESUME, ARCHIVE

## Reminder (NEW -- embedded object)
- fields:
  - daysBefore: Integer
  - channel: String (SMS | EMAIL | PUSH)

## CustomFieldConfig (NEW -- embedded object)
- fields:
  - meta: List<Long>
  - link: List<Long>
  - delink: List<Long>
  - pause: List<Long>
  - resume: List<Long>

## PartnerProgram (EXISTING -- MySQL, NO CHANGES)
- location: emf-parent/pointsengine-emf
- table: partner_programs
- note: Only updated via Thrift when subscription transitions to ACTIVE

## PartnerProgramEnrollment (EXISTING -- MySQL, NO CHANGES)
- location: emf-parent/pointsengine-emf
- table: partner_program_enrollment
- note: Managed via EMF Thrift (link/delink/update events)

## EntityType (EXISTING -- MODIFIED)
- location: intouch-api-v3
- file: com.capillary.intouchapiv3.unified.promotion.orchestration.EntityType
- change: Add SUBSCRIPTION value

## ExtendedField.EntityType (EXISTING -- MODIFIED)
- location: api/prototype
- file: com.capillary.api.v2.impl.bo.domain.extendedField.ExtendedField.EntityType
- change: Add PARTNER_PROGRAM value with collection name "partner_program_extended_fields"

# Services (NEW)

## SubscriptionController
- location: intouch-api-v3
- base_path: /v3/subscriptions
- endpoints:
  - POST /: createSubscription
  - GET /: listSubscriptions (query: orgId, programId, status, page, size)
  - GET /{id}: getSubscription
  - PUT /{id}: updateSubscription
  - PATCH /{id}: partialUpdateSubscription
  - DELETE /{id}: deleteSubscription (DRAFT only)
  - GET /{id}/benefits: listBenefits
  - POST /{id}/benefits: linkBenefits
  - DELETE /{id}/benefits: unlinkBenefits
  - POST /{id}/enroll: enrollMember (calls EMF Thrift)
  - POST /{id}/unenroll: unenrollMember (calls EMF Thrift)
  - POST /{id}/enrollments/update: updateEnrollment (calls EMF Thrift)
  - GET /{id}/enrollments: listEnrollments
  - GET /approvals: listPendingApprovals

## SubscriptionFacade
- location: intouch-api-v3
- dependencies: SubscriptionRepository, SubscriptionStatusTransitionValidator, EmfThriftService
- pattern: follows UnifiedPromotionFacade

## SubscriptionRepository
- location: intouch-api-v3
- extends: MongoRepository<UnifiedSubscription, String>
- routed_to: emfMongoTemplate (via EmfMongoConfig)

## SubscriptionStatusTransitionValidator
- location: intouch-api-v3
- pattern: follows StatusTransitionValidator (EnumMap-based)
- transitions: see lifecycle state machine in 00-ba.md section 7.2

# Modified Services

## RequestManagementFacade
- location: intouch-api-v3
- change: Add routing for EntityType.SUBSCRIPTION -> SubscriptionFacade.changeStatus()

## EmfMongoConfig
- location: intouch-api-v3
- change: Add SubscriptionRepository to includeFilters for emfMongoTemplate routing

# Cross-Repo Changes

| Repo | Files New | Files Modified | Confidence |
|------|----------|---------------|------------|
| intouch-api-v3 | ~10-15 (document, repo, facade, controller, validator, enums, DTOs) | ~3-4 (EntityType, RequestManagementFacade, EmfMongoConfig, RequestManagementController) | C6 |
| api/prototype | 0 | 1 (ExtendedField.EntityType -- add PARTNER_PROGRAM) | C7 |
| emf-parent | 0 | 0 | C7 |
| cc-stack-crm | 0 | 0 | C7 |
| thrifts | 0 | 0 | C7 |

# Key Decisions

| # | Decision | Phase |
|---|----------|-------|
| KD-04 | Scope: E3-US2 + E3-US4 + E3-US5 + maker-checker | BA Q1 |
| KD-05 | Keep codebase tier model (own slab hierarchy) | BA Q2 |
| KD-06 | Pricing via extended fields, not DB columns | BA Q3 |
| KD-07 | MongoDB-first architecture (ADR) | BA Q4 |
| KD-08 | Benefits as FK references only (ADR) | BA Q5 |
| KD-09 | Reminder + custom field config stored, triggering deferred | BA Q6 |
| KD-10 | v3 enrollment APIs calling EMF Thrift directly (ADR) | BA Q7 |

# Acceptance Criteria (In-Scope)

## Create & Edit (E3-US2 API)
- AC-S-12: POST /v3/subscriptions returns 400 if name or duration missing
- AC-S-13: NON_TIER subscriptions must have null linkedTierId
- AC-S-14: TIER_BASED subscriptions must have non-null linkedTierId
- AC-S-15: null price.amount treated as free
- AC-S-16: price stored as {amount, currency}
- AC-S-17/18/19: benefitIds array stored on document
- AC-S-20: reminders array stored on document (max 5)
- AC-S-21: POST with status=DRAFT saves without approval
- AC-S-22: SUBMIT_FOR_APPROVAL changes status to PENDING_APPROVAL
- AC-S-23: PUT on ACTIVE creates pending version (version N+1, DRAFT with parentId)

## Lifecycle (E3-US4)
- AC-S-33: PAUSE action blocks new enrollments, existing retain benefits
- AC-S-34: RESUME returns to ACTIVE, new enrollments permitted
- AC-S-35: Enroll with future membershipStartDate creates PENDING enrollment
- AC-S-36: Enroll with past date returns 400
- AC-S-37: Re-enroll with new future date atomically replaces PENDING
- AC-S-39: Unenroll on PENDING cancels enrollment

## API Contract (E3-US5)
- AC-S-41: POST /v3/subscriptions returns 400 with structured field-level errors
- AC-S-42: PUT on ACTIVE with maker-checker creates pending version
- AC-S-43: POST /v3/subscriptions/{id}/benefits links benefit IDs
