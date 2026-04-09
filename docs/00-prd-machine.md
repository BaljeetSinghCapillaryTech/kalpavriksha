---
feature: Subscription-CRUD
ticket: aidlc-demo-v2
phase: 1
type: prd-machine
version: 1.0
date: 2026-04-09
epics:
  - id: E1
    name: Subscription CRUD
    stories: [E1-US1, E1-US2, E1-US3, E1-US4, E1-US5]
  - id: E2
    name: Lifecycle Management
    stories: [E2-US1, E2-US2, E2-US3, E2-US4, E2-US5, E2-US6]
  - id: E3
    name: Benefit Linking
    stories: [E3-US1, E3-US2, E3-US3]
  - id: E4
    name: Enrollment Operations
    stories: [E4-US1, E4-US2, E4-US3, E4-US4]
  - id: E5
    name: Approvals
    stories: [E5-US1]
---

# User Stories

## E1-US1: Create Subscription
- priority: P0
- api: POST /v3/subscriptions
- input: UnifiedSubscription JSON
- output: 201 Created with subscription document
- validations:
  - name: required, unique per org, max 255
  - duration.value: required, positive integer
  - duration.unit: required, enum (DAYS, MONTHS, YEARS)
  - subscriptionType: required, enum (TIER_BASED, NON_TIER)
  - price.amount: optional, >= 0 if provided
  - price.currency: required if price.amount provided, ISO 4217
  - linkedTierId: required if TIER_BASED, null if NON_TIER
  - reminders: max 5, each: daysBefore > 0, channel in (SMS, EMAIL, PUSH)
- acceptance_criteria: [AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7, AC-1.8]
- brd_mapping: AC-S 12, 13, 14, 15, 16, 21

## E1-US2: Get Subscription
- priority: P0
- api: GET /v3/subscriptions/{unifiedSubscriptionId}
- output: 200 with subscription document
- acceptance_criteria: [AC-2.1, AC-2.2, AC-2.3]

## E1-US3: List Subscriptions
- priority: P0
- api: GET /v3/subscriptions
- query_params: programId, status, page, size
- output: 200 with paginated list
- acceptance_criteria: [AC-3.1, AC-3.2, AC-3.3, AC-3.4]

## E1-US4: Update Subscription
- priority: P0
- api: PUT /v3/subscriptions/{unifiedSubscriptionId}
- input: UnifiedSubscription JSON
- behavior:
  - DRAFT: update in place
  - ACTIVE: create new DRAFT (version N+1, parentId -> ACTIVE)
  - PAUSED: same as ACTIVE
  - Other statuses: 400 error
- acceptance_criteria: [AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5, AC-4.6]
- brd_mapping: AC-S 23, 42

## E1-US5: Delete Subscription
- priority: P1
- api: DELETE /v3/subscriptions/{unifiedSubscriptionId}
- behavior: only DRAFT allowed, returns 204
- acceptance_criteria: [AC-5.1, AC-5.2]

## E2-US1: Submit for Approval
- priority: P0
- api: PUT /v3/requests/SUBSCRIPTION/{id}/status
- action: SUBMIT_FOR_APPROVAL
- transition: DRAFT -> PENDING_APPROVAL
- acceptance_criteria: [AC-6.1, AC-6.2]
- brd_mapping: AC-S 22

## E2-US2: Approve Subscription
- priority: P0
- api: PUT /v3/requests/SUBSCRIPTION/{id}/status
- action: APPROVE
- transition: PENDING_APPROVAL -> ACTIVE (or SCHEDULED if future start)
- side_effect: EMF Thrift call to create/update partner_programs MySQL record
- acceptance_criteria: [AC-7.1, AC-7.2, AC-7.3, AC-7.4]

## E2-US3: Reject Subscription
- priority: P0
- api: PUT /v3/requests/SUBSCRIPTION/{id}/status
- action: REJECT
- transition: PENDING_APPROVAL -> DRAFT
- acceptance_criteria: [AC-8.1, AC-8.2, AC-8.3]

## E2-US4: Pause Subscription
- priority: P0
- api: PUT /v3/requests/SUBSCRIPTION/{id}/status
- action: PAUSE
- transition: ACTIVE -> PAUSED
- acceptance_criteria: [AC-9.1, AC-9.2, AC-9.3, AC-9.4]
- brd_mapping: AC-S 33

## E2-US5: Resume Subscription
- priority: P0
- api: PUT /v3/requests/SUBSCRIPTION/{id}/status
- action: RESUME
- transition: PAUSED -> ACTIVE
- acceptance_criteria: [AC-10.1, AC-10.2, AC-10.3]
- brd_mapping: AC-S 34

## E2-US6: Archive Subscription
- priority: P1
- api: PUT /v3/requests/SUBSCRIPTION/{id}/status
- action: ARCHIVE
- transition: DRAFT|ACTIVE|EXPIRED -> ARCHIVED (terminal)
- acceptance_criteria: [AC-11.1, AC-11.2, AC-11.3]

## E3-US1: Link Benefits
- priority: P0
- api: POST /v3/subscriptions/{id}/benefits
- input: {"benefitIds": ["id1", "id2"]}
- behavior: adds to benefitIds array, deduplicates, no validation against benefits service
- acceptance_criteria: [AC-12.1, AC-12.2, AC-12.3]
- brd_mapping: AC-S 43

## E3-US2: List Benefits
- priority: P0
- api: GET /v3/subscriptions/{id}/benefits
- output: {"benefitIds": [...]}
- acceptance_criteria: [AC-13.1]

## E3-US3: Unlink Benefits
- priority: P1
- api: DELETE /v3/subscriptions/{id}/benefits
- input: {"benefitIds": ["id1"]}
- behavior: removes from array, idempotent
- acceptance_criteria: [AC-14.1, AC-14.2]

## E4-US1: Enroll Member
- priority: P0
- api: POST /v3/subscriptions/{id}/enroll
- input: {customerId, membershipStartDate}
- backend: calls EMF partnerProgramLinkingEvent via Thrift
- acceptance_criteria: [AC-15.1, AC-15.2, AC-15.3, AC-15.4, AC-15.5, AC-15.6]
- brd_mapping: AC-S 35, 36, 37

## E4-US2: Unenroll Member
- priority: P0
- api: POST /v3/subscriptions/{id}/unenroll
- input: {customerId}
- backend: calls EMF partnerProgramDeLinkingEvent via Thrift
- acceptance_criteria: [AC-16.1, AC-16.2]
- brd_mapping: AC-S 39

## E4-US3: Update Enrollment
- priority: P1
- api: POST /v3/subscriptions/{id}/enrollments/update
- input: {customerId, action}
- backend: calls EMF partnerProgramUpdateEvent via Thrift
- acceptance_criteria: [AC-17.1, AC-17.2]

## E4-US4: List Enrollments
- priority: P1
- api: GET /v3/subscriptions/{id}/enrollments
- backend: calls EMF Thrift to fetch enrollment records
- acceptance_criteria: [AC-18.1]

## E5-US1: List Pending Approvals
- priority: P0
- api: GET /v3/subscriptions/approvals
- output: list of PENDING_APPROVAL subscriptions for org
- acceptance_criteria: [AC-19.1, AC-19.2]

# Epic Dependencies

```
E1 (CRUD) --> E2 (Lifecycle) --> E4 (Enrollment)
E1 (CRUD) --> E3 (Benefits)
E2 (Lifecycle) --> E5 (Approvals)
```

E1 must be built first (document model, repository, facade, controller).
E2 depends on E1 for status transitions.
E3 can be built in parallel with E2.
E4 depends on E2 (must check subscription status before allowing enrollment).
E5 depends on E2 (queries PENDING_APPROVAL status).

# Implementation Priority

| Phase | Stories | Rationale |
|-------|---------|-----------|
| 1 | E1-US1, E1-US2, E1-US3, E1-US4, E1-US5 | Core CRUD -- foundation for everything |
| 2 | E2-US1, E2-US2, E2-US3, E2-US4, E2-US5, E2-US6 | Lifecycle -- enables maker-checker and state management |
| 3 | E3-US1, E3-US2, E3-US3, E5-US1 | Benefits linking + approvals list (parallel) |
| 4 | E4-US1, E4-US2, E4-US3, E4-US4 | Enrollment -- requires ACTIVE subscriptions |
