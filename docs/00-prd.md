# Product Requirements Document -- Subscription-CRUD

> Feature: Subscription Programs Configuration (E3)
> Ticket: aidlc-demo-v2
> Date: 2026-04-09
> Phase: 1 (PRD Generation)
> Source: BA analysis (00-ba.md) + Tiers & Benefits PRD v3

---

## 1. Overview

Build the backend REST API layer for subscription program management in the Garuda Loyalty Platform. This enables program administrators to create, configure, edit, and manage the lifecycle of subscription programs through a v3 API surface, with maker-checker approval workflows and benefit ID linking.

### 1.1 Success Criteria

- All subscription CRUD operations available via REST API
- 7-state lifecycle with validated transitions
- Maker-checker versioning: edit-of-active creates pending version
- Benefit IDs linkable to subscriptions
- Zero MySQL schema changes (MongoDB-first)
- Enrollment stays on existing v2 paths (out of scope per KD-16)

---

## 2. Epics and User Stories

### Epic 1: Subscription CRUD

**E1-US1: Create Subscription**

As a program administrator, I want to create a new subscription program via API, so that it is saved as a Draft in MongoDB and ready for configuration.

| Field | Rules |
|-------|-------|
| name | Required. Unique per org. Max 255 chars. |
| duration.value | Required. Positive integer. |
| duration.unit | Required. One of: DAYS, MONTHS, YEARS. |
| subscriptionType | Required. One of: TIER_BASED, NON_TIER. Default: NON_TIER. |
| price.amount | Optional. If provided, must be >= 0. If null, subscription is free. |
| price.currency | Required if price.amount is provided. ISO 4217 code. |
| linkedTierId | Required if subscriptionType = TIER_BASED. Must be null if NON_TIER. |
| benefitIds | Optional. Array of string IDs. No validation against benefits service (dummy objects). |
| reminders | Optional. Max 5 entries. Each: daysBefore (positive int) + channel (SMS/EMAIL/PUSH). |
| customFields | Optional. Object with meta/link/delink/pause/resume arrays of extended field IDs. |

Acceptance Criteria:
- AC-1.1: POST `/v3/subscriptions` with valid body returns 201 with subscription document including generated `unifiedSubscriptionId`
- AC-1.2: POST without name returns 400: `{field: "name", error: "REQUIRED", message: "Subscription name is required"}`
- AC-1.3: POST without duration returns 400 with structured field error
- AC-1.4: POST with subscriptionType=TIER_BASED and no linkedTierId returns 400
- AC-1.5: POST with subscriptionType=NON_TIER and a linkedTierId returns 400
- AC-1.6: Status defaults to DRAFT
- AC-1.7: `unifiedSubscriptionId` is a UUID, immutable after creation
- AC-1.8: Duplicate name within same org returns 409 CONFLICT

**E1-US2: Get Subscription**

As a program administrator, I want to retrieve a subscription by its ID, so that I can view its current configuration and status.

Acceptance Criteria:
- AC-2.1: GET `/v3/subscriptions/{unifiedSubscriptionId}` returns the subscription document
- AC-2.2: GET with invalid ID returns 404
- AC-2.3: GET for different org returns 404 (tenant isolation)

**E1-US3: List Subscriptions**

As a program administrator, I want to list subscriptions for my program, optionally filtered by status.

Acceptance Criteria:
- AC-3.1: GET `/v3/subscriptions?programId=X` returns paginated list
- AC-3.2: GET with `status=ACTIVE` returns only active subscriptions
- AC-3.3: Pagination via `page` and `size` query params (default: page=0, size=20)
- AC-3.4: Results sorted by lastModifiedOn descending

**E1-US4: Update Subscription**

As a program administrator, I want to update a subscription, so that I can modify its configuration.

Acceptance Criteria:
- AC-4.1: PUT `/v3/subscriptions/{id}` on a DRAFT subscription updates it in place
- AC-4.2: PUT on an ACTIVE subscription creates a new DRAFT document (version N+1) with parentId pointing to the ACTIVE document
- AC-4.3: PUT on a PAUSED subscription follows the same versioning as ACTIVE
- AC-4.4: PUT on PENDING_APPROVAL, EXPIRED, ARCHIVED returns 400 "Cannot update subscription in status: X"
- AC-4.5: The ACTIVE subscription remains unchanged until the new version is approved
- AC-4.6: If a DRAFT already exists for an ACTIVE subscription, PUT updates the existing DRAFT

**E1-US5: Delete Subscription**

As a program administrator, I want to delete a DRAFT subscription that has no enrollments.

Acceptance Criteria:
- AC-5.1: DELETE `/v3/subscriptions/{id}` on DRAFT returns 204
- AC-5.2: DELETE on non-DRAFT status returns 400 "Only DRAFT subscriptions can be deleted"

---

### Epic 2: Lifecycle Management

**E2-US1: Submit for Approval**

Acceptance Criteria:
- AC-6.1: PUT `/v3/requests/SUBSCRIPTION/{id}/status` with action=SUBMIT_FOR_APPROVAL changes status from DRAFT to PENDING_APPROVAL
- AC-6.2: Submit from non-DRAFT status returns 400 with allowed transitions

**E2-US2: Approve Subscription**

Acceptance Criteria:
- AC-7.1: APPROVE on PENDING_APPROVAL transitions to ACTIVE
- AC-7.2: On ACTIVE transition, EMF Thrift `createOrUpdatePartnerProgram` is called to create/update MySQL partner_programs record
- AC-7.3: If subscription has a future start date, status becomes SCHEDULED instead of ACTIVE
- AC-7.4: APPROVE on non-PENDING_APPROVAL returns 400

**E2-US3: Reject Subscription**

Acceptance Criteria:
- AC-8.1: REJECT on PENDING_APPROVAL transitions back to DRAFT
- AC-8.2: Review comment stored in `comments` field
- AC-8.3: REJECT on non-PENDING_APPROVAL returns 400

**E2-US4: Pause Subscription**

Acceptance Criteria:
- AC-9.1: PAUSE on ACTIVE transitions to PAUSED
- AC-9.2: New enrollments are blocked (enforced at enrollment API level)
- AC-9.3: Existing enrollments retain benefits (no change to MySQL enrollment records)
- AC-9.4: PAUSE on non-ACTIVE returns 400

**E2-US5: Resume Subscription**

Acceptance Criteria:
- AC-10.1: RESUME on PAUSED transitions to ACTIVE
- AC-10.2: New enrollments become permitted again
- AC-10.3: RESUME on non-PAUSED returns 400

**E2-US6: Archive Subscription**

Acceptance Criteria:
- AC-11.1: ARCHIVE transitions from DRAFT, ACTIVE, or EXPIRED to ARCHIVED
- AC-11.2: ARCHIVED is a terminal state -- no further transitions
- AC-11.3: Archived subscriptions are read-only

---

### Epic 3: Benefit Linking

**E3-US1: Link Benefits**

Acceptance Criteria:
- AC-12.1: POST `/v3/subscriptions/{id}/benefits` with `{"benefitIds": ["id1", "id2"]}` adds IDs to the subscription's benefitIds array
- AC-12.2: Duplicate IDs are silently deduplicated
- AC-12.3: No validation against a benefits service (dummy IDs accepted)

**E3-US2: List Benefits**

Acceptance Criteria:
- AC-13.1: GET `/v3/subscriptions/{id}/benefits` returns `{"benefitIds": ["id1", "id2"]}`

**E3-US3: Unlink Benefits**

Acceptance Criteria:
- AC-14.1: DELETE `/v3/subscriptions/{id}/benefits` with `{"benefitIds": ["id1"]}` removes specified IDs
- AC-14.2: Removing a non-existent ID is a no-op (idempotent)

---

### ~~Epic 4: Enrollment Operations~~ -- OUT OF SCOPE (KD-16)

> **Removed in Phase 4.** User decision: enrollment Thrift calls stay on existing v2 paths. v3 does NOT expose enroll/unenroll/update/list enrollment endpoints. E4-US1 through E4-US4 are deferred. See blocker-decisions.md BD-07.

---

### Epic 4: Approvals

**E4-US1: List Pending Approvals**

Acceptance Criteria:
- AC-15.1: GET `/v3/subscriptions/approvals` returns all subscriptions in PENDING_APPROVAL status for the org
- AC-15.2: Includes parent subscription details (if editing an ACTIVE subscription)

---

## 3. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| API response time (CRUD) | < 200ms p95 |
| API response time (Thrift write-back on ACTIVE) | < 500ms p95 |
| Concurrent requests | Handle 100 concurrent subscription create/update operations per org |
| Data isolation | Strict tenant isolation via orgId in all queries (MongoDB + MySQL) |
| Validation | Structured field-level error responses, never 500 for validation failures |
| Idempotency | Duplicate create with same name returns 409, not 500 |
| Backward compatibility | No changes to existing v2 APIs, MySQL schema, or Thrift IDL |

## 4. Dependencies

| Dependency | Type | Risk |
|-----------|------|------|
| EMF Thrift service availability | Runtime | ACTIVE transition write-back fails if EMF is down. Retry + circuit breaker recommended. |
| MongoDB (emfMongoTemplate) | Runtime | Subscription CRUD fails if MongoDB is down. |
| Multi-tenant MongoDB routing (EmfMongoTenantResolver) | Infrastructure | Must be configured for subscription collection. |

## 5. Out of Scope (Deferred)

| Item | When | Dependency |
|------|------|-----------|
| Reminder triggering | Future run | Comm-server integration |
| Custom field enforcement at enrollment | Future run | Extended fields validation |
| Simulation API | Future run | Enrollment analytics |
| SCHEDULED -> ACTIVE automatic transition | Future run | Scheduled job infrastructure |
| ACTIVE -> EXPIRED automatic transition | Future run | Scheduled job infrastructure |
| Tier downgrade on exit event | Future run | EMF event handling |
| Webhook/event firing | Future run | Event bus integration |
| Real benefit validation | E2/E4 pipeline run | Benefits service |
| Enrollment operations (enroll/unenroll/update/list) | Future run | KD-16: stays on existing v2 Thrift paths |

---

*Generated by PRD Generator (Phase 1) -- Subscription-CRUD Pipeline*
