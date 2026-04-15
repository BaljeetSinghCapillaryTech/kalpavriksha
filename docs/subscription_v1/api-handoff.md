# API Contract — Subscription Programs (E3)

> **Artifacts path**: `docs/subscription_v1/`
> **Source phases read**: `00-ba.md`, `01-architect.md`, `03-designer.md`, `06-developer.md`, `session-memory.md`
> **Code-verified**: `SubscriptionFacade.java`, `SubscriptionProgram.java`, `SubscriptionController.java` (skeleton), `ResponseWrapper.java`, all enums
> **Date**: 2026-04-15
>
> **Implementation status**:
> - ✅ `SubscriptionFacade` — fully implemented, 39/39 tests GREEN
> - ✅ `SubscriptionProgram` (MongoDB document), all enums, all DTOs — implemented
> - ⚠️ `SubscriptionController` / `SubscriptionReviewController` — **controller wiring pending** (facade logic complete, HTTP routing not yet wired). Endpoint shapes are from designer spec and are final — a one-session task to wire.
>
> **Note for UI team**: You can start building mocks and integration tests against this contract now. The facade business logic is complete and battle-tested.

---

## Overview

Subscription Programs are membership offerings that brands create for their loyalty programs. A brand admin configures a subscription (name, duration, tier linkage, benefits, reminders) through a maker-checker workflow: the creator saves a **Draft**, submits for approval, and an approver publishes it to live. Live subscriptions can be paused, resumed, or archived. Members can enroll in Active subscriptions to receive benefits for the subscription duration.

---

## Project API Conventions

These conventions are sourced from `UnifiedPromotionController.java` and `ResponseWrapper.java` — the existing adjacent feature in the same codebase. All subscription endpoints follow the same conventions.

### Response Envelope

Every response (success and error) is wrapped in `ResponseWrapper<T>`:

```json
{
  "data": { /* T — see each endpoint */ },
  "errors": [
    { "code": 1001, "message": "Subscription not found" }
  ],
  "warnings": [
    { "message": "Non-fatal advisory" }
  ]
}
```

- On **success**: `data` is populated, `errors` is null
- On **error**: `data` is null, `errors` contains one or more error objects
- `warnings` may appear on success responses for non-fatal advisories

### Authentication

All endpoints require a valid Capillary session token. The platform extracts `orgId` (tenant) from the token automatically — the UI does **not** pass orgId in the request body.

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <session-token>` |

`orgId` and `userId` (createdBy/updatedBy) are always sourced from the token, not from request fields.

### Naming Conventions

- JSON field names: **camelCase**
- Timestamps: **UTC ISO-8601** (Java `Instant` serializes as `"2026-04-15T10:30:00Z"`)
- IDs: `subscriptionProgramId` is a UUID string; `objectId` is the MongoDB ObjectId string

### Content-Type

```
Content-Type: application/json
Accept: application/json
```

### Pagination

List endpoints use **offset-based pagination** with `page` (0-indexed) and `size` (default 20).

Response wraps a Spring `Page<T>` inside `data`:
```json
{
  "data": {
    "items": { /* Spring Page with content, totalElements, totalPages, etc. */ },
    "headerStats": { /* aggregate counts */ }
  }
}
```

### Error Format

```json
{
  "data": null,
  "errors": [
    { "code": 1001, "message": "Human-readable error description" }
  ],
  "warnings": null
}
```

> **Note**: Exact numeric error codes are not yet defined in the implementation (inferred from designer spec). Verify specific code values with backend before wiring up error-specific UI handling.

---

## Base URL and Versioning

| Property | Value |
|----------|-------|
| Base path | `/v3/subscriptions` |
| Versioning | Path-based (`/v3/`) |
| Content-Type | `application/json` |

---

## Resources

### Resource: Subscription Programs (CRUD + Lifecycle)

---

#### POST `/v3/subscriptions`

**Purpose**: Create a new subscription program as a **Draft**. No MySQL write happens — all data is saved to MongoDB only. The subscription enters the maker-checker workflow from here.

**Maps to**: E3-US2 (Create subscription), AC-09, AC-10, AC-27

**Request**: `POST /v3/subscriptions`

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `programId` | body | yes | Loyalty program ID (EMF `loyalty_program_id`) this subscription belongs to |
| `name` | body | yes | Subscription name. Max 255 chars. Must be unique per org (across all partner programs). |
| `description` | body | no | Max 1000 chars |
| `subscriptionType` | body | yes | `TIER_BASED` or `NON_TIER` |
| `duration` | body | yes | Duration object (see nested DTOs) |
| `expiry` | body | no | Optional program-level expiry settings |
| `settings` | body | no | Membership restriction settings |
| `tierConfig` | body | conditional | Required when `subscriptionType = TIER_BASED` |
| `reminders` | body | no | Up to 5 expiry reminders. Stored in MongoDB only — dispatched by PEB scheduler. |
| `customFields` | body | no | Custom fields at META / LINK / DELINK levels |
| `groupTag` | body | no | Free-text tag for grouped listing view |

**Request Body**:
```json
{
  "programId": 1,
  "name": "Gold Membership",
  "description": "Annual gold tier access with exclusive benefits",
  "subscriptionType": "TIER_BASED",
  "duration": {
    "cycleType": "MONTHS",
    "cycleValue": 12
  },
  "expiry": {
    "programExpiryDate": "2027-12-31T23:59:59Z",
    "migrateOnExpiry": "MIGRATE_TO_PROGRAM",
    "migrationTargetProgramId": 2
  },
  "settings": {
    "restrictToOneActivePerMember": true
  },
  "tierConfig": {
    "linkedTierId": 101,
    "tierDowngradeOnExit": true,
    "downgradeTargetTierId": 100
  },
  "reminders": [
    {
      "daysBeforeExpiry": 30,
      "channel": "EMAIL",
      "communicationProperties": {
        "templateId": "SUB_EXPIRY_30D"
      }
    },
    {
      "daysBeforeExpiry": 7,
      "channel": "SMS",
      "communicationProperties": {}
    }
  ],
  "customFields": {
    "meta": [
      { "extendedFieldId": 501, "name": "price" }
    ],
    "link": [],
    "delink": []
  },
  "groupTag": "premium-tier"
}
```

**Response — Success** (HTTP 201):
```json
{
  "data": {
    "objectId": "663a1f2e8b4c2d001f3e9a01",
    "subscriptionProgramId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "orgId": 1001,
    "programId": 1,
    "status": "DRAFT",
    "version": 1,
    "parentId": null,
    "mysqlPartnerProgramId": null,
    "name": "Gold Membership",
    "description": "Annual gold tier access with exclusive benefits",
    "subscriptionType": "TIER_BASED",
    "duration": { "cycleType": "MONTHS", "cycleValue": 12 },
    "expiry": {
      "programExpiryDate": "2027-12-31T23:59:59Z",
      "migrateOnExpiry": "MIGRATE_TO_PROGRAM",
      "migrationTargetProgramId": 2
    },
    "settings": { "restrictToOneActivePerMember": true },
    "tierConfig": {
      "linkedTierId": 101,
      "tierDowngradeOnExit": true,
      "downgradeTargetTierId": 100
    },
    "benefits": [],
    "reminders": [
      { "daysBeforeExpiry": 30, "channel": "EMAIL", "communicationProperties": { "templateId": "SUB_EXPIRY_30D" } }
    ],
    "customFields": { "meta": [{ "extendedFieldId": 501, "name": "price" }], "link": [], "delink": [] },
    "groupTag": "premium-tier",
    "workflowMetadata": null,
    "comments": null,
    "createdBy": "user-entity-id-from-token",
    "createdAt": "2026-04-15T10:00:00Z",
    "updatedBy": "user-entity-id-from-token",
    "updatedAt": "2026-04-15T10:00:00Z"
  },
  "errors": null,
  "warnings": null
}
```

**Response — Error Cases**:

| HTTP Status | When | Error Message Pattern |
|-------------|------|-----------------------|
| 409 | `name` conflicts with an existing DRAFT/PENDING/ACTIVE/PAUSED subscription in this org | `"Subscription name 'Gold Membership' already in use for org 1001"` |
| 400 | Missing required field (`name`, `subscriptionType`, `duration`, `programId`) | `"SUBSCRIPTION.NAME_REQUIRED"` / `"SUBSCRIPTION.DURATION_REQUIRED"` |
| 400 | `subscriptionType=TIER_BASED` but `tierConfig.linkedTierId` missing | `"SUBSCRIPTION.TIER_BASED_REQUIRES_LINKED_TIER"` (validation at submit-for-approval) |
| 400 | `cycleValue` ≤ 0 | `"SUBSCRIPTION.CYCLE_VALUE_POSITIVE"` |
| 400 | More than 5 reminders | `"SUBSCRIPTION.TOO_MANY_REMINDERS"` |

**Notes**:
- `subscriptionProgramId` (UUID) is the immutable business key — use this in all subsequent calls
- `objectId` is MongoDB internal — avoid exposing this in UI navigation
- `orgId` is populated from JWT token, never sent by the client
- `mysqlPartnerProgramId` is null until the subscription is Approved (MySQL write happens at approval)
- Name uniqueness is checked against MongoDB active statuses at create, and re-checked against MySQL at approval

---

#### GET `/v3/subscriptions/{subscriptionProgramId}`

**Purpose**: Retrieve the full detail of a single subscription program.

**Maps to**: E3-US1 detail view, RP-12

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `subscriptionProgramId` | path | yes | Business UUID from `subscriptionProgramId` field |

**Response — Success** (HTTP 200):

Same shape as the POST 201 response body above. All fields returned.

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Subscription not found for this `subscriptionProgramId` + `orgId` |

---

#### PUT `/v3/subscriptions/{subscriptionProgramId}`

**Purpose**: Update a subscription program.

- **DRAFT or PENDING_APPROVAL**: in-place update of the existing document
- **ACTIVE**: creates a new DRAFT document with `parentId` pointing to the ACTIVE document. The ACTIVE version stays live until the DRAFT is approved. Only one edit-in-flight is allowed at a time.

**Maps to**: E3-US2 (Edit), WP-2

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `subscriptionProgramId` | path | yes | Business UUID |
| *(body)* | body | yes | Same `SubscriptionRequest` shape as POST — all updatable fields |

**Response — Success** (HTTP 200): Full `SubscriptionResponse` of the updated or newly-created DRAFT document.

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Not found |
| 422 | Subscription is ARCHIVED or PAUSED (update not allowed) |
| 409 | An edit-in-flight DRAFT already exists for this ACTIVE subscription (parentId collision) |

---

#### GET `/v3/subscriptions`

**Purpose**: List all subscription programs for the authenticated org and loyalty program, with optional filters. Returns a page of summary items plus header stats (aggregate counts by status + total subscriber count).

**Maps to**: E3-US1 (Listing), AC-01, AC-03, AC-05, AC-06, RP-11

| Parameter | Location | Required | Default | Description |
|-----------|----------|----------|---------|-------------|
| `programId` | query | **yes** | — | Loyalty program ID to scope the listing |
| `status` | query | no | all | Filter by one or more statuses (repeatable: `?status=ACTIVE&status=DRAFT`) |
| `groupTag` | query | no | — | Filter by group tag |
| `search` | query | no | — | Text search on name (case-insensitive) |
| `sort` | query | no | `subscribers` | Sort field. Supported: `subscribers`, `name`, `updatedAt` |
| `page` | query | no | `0` | 0-indexed page number |
| `size` | query | no | `20` | Page size (max: [TBD — verify with backend]) |

**Response — Success** (HTTP 200):
```json
{
  "data": {
    "items": {
      "content": [
        {
          "subscriptionProgramId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
          "name": "Gold Membership",
          "description": "Annual gold tier access",
          "status": "ACTIVE",
          "benefitsCount": 3,
          "subscriberCount": 1250,
          "groupTag": "premium-tier",
          "updatedAt": "2026-04-15T10:00:00Z",
          "updatedBy": "admin-user-id",
          "mysqlPartnerProgramId": 42,
          "version": 2
        }
      ],
      "totalElements": 15,
      "totalPages": 1,
      "number": 0,
      "size": 20
    },
    "headerStats": {
      "totalSubscriptions": 15,
      "activeCount": 8,
      "pendingApprovalCount": 2,
      "draftCount": 3,
      "pausedCount": 1,
      "archivedCount": 1,
      "totalSubscribers": 4823
    }
  },
  "errors": null,
  "warnings": null
}
```

**Notes**:
- `subscriberCount` is fetched in bulk from MySQL via Thrift — non-null only for ACTIVE subscriptions with `mysqlPartnerProgramId`
- `headerStats.totalSubscribers` is the aggregate sum across all ACTIVE subscriptions for this org+program
- Subscriber counts are **cached** (Caffeine, 60s TTL) — may be up to 60 seconds stale
- `status` filter accepts multiple values in a single request

---

#### PUT `/v3/subscriptions/{subscriptionProgramId}/status`

**Purpose**: Trigger a lifecycle state transition on a subscription. Handles four actions: submit for approval, pause, resume, and archive.

**Maps to**: WP-3 (submit), WP-6 (pause), WP-7 (resume), WP-8 (archive)

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `subscriptionProgramId` | path | yes | Business UUID |
| `action` | body | yes | One of: `SUBMIT_FOR_APPROVAL`, `PAUSE`, `RESUME`, `ARCHIVE` |
| `comment` | body | no | Optional note (max 150 chars) |

**Request Body**:
```json
{
  "action": "SUBMIT_FOR_APPROVAL",
  "comment": "Ready for review"
}
```

**State machine rules**:

| Action | Allowed From Status | Result Status | MySQL write? |
|--------|--------------------|--------------------|------|
| `SUBMIT_FOR_APPROVAL` | `DRAFT` | `PENDING_APPROVAL` | No |
| `PAUSE` | `ACTIVE` | `PAUSED` | Yes (sets `is_active=false` via Thrift) |
| `RESUME` | `PAUSED` | `ACTIVE` | Yes (sets `is_active=true` via Thrift) |
| `ARCHIVE` | `DRAFT`, `ACTIVE`, `PAUSED` | `ARCHIVED` | Yes for ACTIVE/PAUSED (sets `is_active=false` via Thrift) |

**Response — Success** (HTTP 200): Full `SubscriptionResponse` with updated status.

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Subscription not found |
| 422 | Action not allowed in current status (e.g., PAUSE on a DRAFT) |
| 502 | Thrift call to MySQL failed during PAUSE/RESUME/ARCHIVE (subscription status NOT changed — retry safe) |

**Notes**:
- PAUSE/RESUME/ARCHIVE that touch MySQL are **dual-write**: Thrift call first, then MongoDB update. If Thrift fails, the HTTP call returns 502 and the subscription remains in its previous state — safe to retry.
- ARCHIVE is a **terminal state** — there is no un-archive. Existing member enrollments continue to their natural expiry date; new enrollments are blocked.

---

#### POST `/v3/subscriptions/{subscriptionProgramId}/duplicate`

**Purpose**: Create an instant copy of a subscription as a new Draft. Useful for creating variations of an approved program.

**Maps to**: AC-12, OQ-17

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `subscriptionProgramId` | path | yes | Source subscription UUID |

**No request body.**

**Response — Success** (HTTP 201): Full `SubscriptionResponse` for the new Draft. Fields reset on the copy:

| Field | Value in copy |
|-------|--------------|
| `subscriptionProgramId` | New UUID |
| `name` | `"<original name> (Copy)"` |
| `status` | `DRAFT` |
| `version` | `1` |
| `parentId` | `null` |
| `mysqlPartnerProgramId` | `null` |
| `createdAt` / `updatedAt` | Current timestamp |

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Source subscription not found |

---

### Resource: Benefits (Linkage)

Benefits are separate entities created elsewhere. Subscription endpoints handle only the linkage (associating an existing benefit ID to a subscription).

---

#### GET `/v3/subscriptions/{subscriptionProgramId}/benefits`

**Purpose**: List benefits currently linked to a subscription.

**Maps to**: AC-07

| Parameter | Location | Required |
|-----------|----------|----------|
| `subscriptionProgramId` | path | yes |

**Response — Success** (HTTP 200):
```json
{
  "data": [
    {
      "benefitId": 1001,
      "addedOn": "2026-04-15T10:00:00Z"
    },
    {
      "benefitId": 1002,
      "addedOn": "2026-04-15T11:30:00Z"
    }
  ],
  "errors": null,
  "warnings": null
}
```

---

#### POST `/v3/subscriptions/{subscriptionProgramId}/benefits`

**Purpose**: Link an existing benefit to a subscription. MongoDB-only — no MySQL write. Benefits can be linked at any status except ARCHIVED. A benefit can be linked to multiple subscriptions (M:N relationship).

**Maps to**: AC-21, WP-9, KD-36

| Parameter | Location | Required |
|-----------|----------|----------|
| `subscriptionProgramId` | path | yes |
| `benefitId` | body | yes |

**Request Body**:
```json
{
  "benefitId": 1003
}
```

**Response — Success** (HTTP 200): Full `SubscriptionResponse` with updated `benefits` array.

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Subscription not found |
| 422 | Benefit already linked to this subscription |
| 422 | Subscription is ARCHIVED |

---

#### DELETE `/v3/subscriptions/{subscriptionProgramId}/benefits/{benefitId}`

**Purpose**: Remove a benefit linkage from a subscription.

**Maps to**: AC-21, WP-10

| Parameter | Location | Required |
|-----------|----------|----------|
| `subscriptionProgramId` | path | yes |
| `benefitId` | path | yes |

**Response — Success** (HTTP 200): Full `SubscriptionResponse` with updated `benefits` array.

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Subscription not found, or `benefitId` was not linked |

---

### Resource: Approval Workflow

---

#### GET `/v3/subscriptions/approvals`

**Purpose**: List subscriptions that are in `PENDING_APPROVAL` status — the approver's review queue.

**Maps to**: AC-36

| Parameter | Location | Required | Default |
|-----------|----------|----------|---------|
| `programId` | query | yes | — |
| `page` | query | no | `0` |
| `size` | query | no | `20` |

**Response — Success** (HTTP 200):
```json
{
  "data": {
    "content": [
      {
        "subscriptionProgramId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "name": "Gold Membership",
        "status": "PENDING_APPROVAL",
        "benefitsCount": 2,
        "subscriberCount": null,
        "updatedAt": "2026-04-15T09:00:00Z",
        "updatedBy": "creator-user-id",
        "version": 1
      }
    ],
    "totalElements": 2,
    "totalPages": 1,
    "number": 0,
    "size": 20
  },
  "errors": null,
  "warnings": null
}
```

---

#### POST `/v3/subscriptions/{subscriptionProgramId}/approve`

**Purpose**: Approve or reject a subscription that is in `PENDING_APPROVAL`.

- **APPROVE**: triggers a SAGA — Thrift call writes the subscription to MySQL (`partner_programs` + `supplementary_membership_cycle_details` + tier config), then MongoDB status becomes `ACTIVE`.
- **REJECT**: subscription returns to `DRAFT`. Rejection comment stored. No MySQL write.

**Maps to**: AC-35, WP-4 (approve), WP-5 (reject)

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `subscriptionProgramId` | path | yes | Business UUID of the subscription |
| `approvalStatus` | body | yes | `"APPROVE"` or `"REJECT"` |
| `comment` | body | no | Approval/rejection comment. Max 150 chars. Stored in `comments` field on the subscription. |

**Request Body**:
```json
{
  "approvalStatus": "APPROVE",
  "comment": "Approved for Q2 launch"
}
```

**Response — Success** (HTTP 200): Full `SubscriptionResponse` with updated status (`ACTIVE` for approve, `DRAFT` for reject).

After **APPROVE** — key fields that change:
```json
{
  "status": "ACTIVE",
  "mysqlPartnerProgramId": 42,
  "workflowMetadata": {
    "submittedBy": "creator-user-id",
    "submittedAt": "2026-04-14T09:00:00Z",
    "reviewedBy": "approver-user-id",
    "reviewedAt": "2026-04-15T10:00:00Z"
  },
  "comments": "Approved for Q2 launch"
}
```

After **REJECT** — key fields that change:
```json
{
  "status": "DRAFT",
  "comments": "Missing tier linkage configuration"
}
```

**Response — Error Cases**:

| HTTP Status | When |
|-------------|------|
| 404 | Subscription not found |
| 422 | Subscription is not in `PENDING_APPROVAL` status |
| 400 | `approvalStatus` is missing or not `APPROVE`/`REJECT` |
| 502 | Thrift/MySQL write failed during APPROVE (subscription remains `PENDING_APPROVAL` — retry-safe) |

**Notes**:
- **Backend does not enforce approver identity.** Any authenticated user can call this endpoint. Access control is a UI responsibility (KD-09, KD-29).
- The approval SAGA is best-effort: Thrift write first → MongoDB update. If Thrift succeeds but MongoDB update fails (extremely rare), a retry of the same APPROVE call will detect `mysqlPartnerProgramId` is already set and skip the Thrift re-write (RF-6 idempotency).
- If the subscription being approved has a `parentId` (edit-of-ACTIVE), the old ACTIVE document becomes ARCHIVED and the new DRAFT becomes ACTIVE.

---

## Common Patterns

### Response Envelope

Always wrap both success and error:
```json
{
  "data": { ... },
  "errors": [ { "code": 1001, "message": "Subscription not found" } ],
  "warnings": []
}
```

### Error Handling

Global exception handler (`TargetGroupErrorAdvice`) maps exceptions to HTTP status:

| Exception | HTTP Status |
|-----------|-------------|
| `SubscriptionNotFoundException` | 404 |
| `InvalidSubscriptionStateException` | 422 |
| `SubscriptionNameConflictException` | 409 |
| `InvalidInputException` | 400 |
| `NotFoundException` | 404 |
| Validation failure (`@Valid` bean validation) | 400 |
| `EMFThriftException` (Thrift call failure) | 502 |

### Idempotency

- **Create** is not idempotent (generates a new UUID each call)
- **Approve** is idempotent — if `mysqlPartnerProgramId` is already set, the Thrift call is skipped and the existing MySQL record is reused (RF-6)
- **Pause / Resume / Archive** — if the Thrift call fails, the MongoDB status is NOT updated, making these safe to retry

### Optimistic Locking

`SubscriptionProgram` carries a `version` field (Spring Data MongoDB `@Version`). Concurrent edits to the same DRAFT will result in an `OptimisticLockingFailureException` → HTTP 409. The UI should refresh and re-apply changes on conflict.

---

## Enums and Constants

| Enum | Values | Used In |
|------|--------|---------|
| `SubscriptionStatus` | `DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `PAUSED`, `ARCHIVED` | `status` field on all responses; `status` query param on list |
| `SubscriptionType` | `TIER_BASED`, `NON_TIER` | `subscriptionType` on create/update request and response |
| `CycleType` | `DAYS`, `MONTHS`, `YEARS` | `duration.cycleType`. Note: `YEARS` is stored in MongoDB; converted to `MONTHS × 12` internally before MySQL write. UI may display YEARS as-is. |
| `MigrateOnExpiry` | `NONE`, `MIGRATE_TO_PROGRAM` | `expiry.migrateOnExpiry` |
| `ReminderChannel` | `SMS`, `EMAIL`, `PUSH` | `reminders[].channel` |
| `SubscriptionAction` | `SUBMIT_FOR_APPROVAL`, `PAUSE`, `RESUME`, `ARCHIVE` | `action` field in PUT `/status` request body |
| `ApprovalStatus` | `APPROVE`, `REJECT` | `approvalStatus` field in POST `/approve` request body |

---

## Subscription Lifecycle State Machine

```
                 ┌──────────────────────────┐
                 │                          │
CREATE ──► DRAFT ──► PENDING_APPROVAL ──► ACTIVE ──► PAUSED
                 │                    ▲      │          │
               REJECT                 │      │          │
               (→ DRAFT)           (APPROVE) │     RESUME
                                            │      (→ ACTIVE)
                                        ARCHIVE        │
                                       (terminal)   ARCHIVE
                                            │      (terminal)
                                            ▼
                                         ARCHIVED
```

**State transition rules**:

| From | Via | To |
|------|-----|-----|
| DRAFT | Submit for approval | PENDING_APPROVAL |
| PENDING_APPROVAL | Approve | ACTIVE |
| PENDING_APPROVAL | Reject | DRAFT |
| ACTIVE | Pause | PAUSED |
| ACTIVE | Archive | ARCHIVED |
| PAUSED | Resume | ACTIVE |
| PAUSED | Archive | ARCHIVED |
| DRAFT | Archive | ARCHIVED |
| ARCHIVED | *any* | ❌ terminal — no transitions out |

---

## Integration Notes

1. **Sequencing**: Create → (optionally link benefits) → Submit for Approval → Approve. Benefits can be linked/delinked at any time before ARCHIVE.

2. **Name uniqueness scope**: Subscription names must be unique per org across **all** partner program types (not just subscriptions). This is a MySQL `UNIQUE(org_id, name)` constraint. The backend validates at creation (MongoDB pre-check) and again at approval (Thrift MySQL check). If a conflict arises only at approval time, the subscription stays PENDING_APPROVAL and the approver sees an error.

3. **Reminders**: Reminders stored in MongoDB are **automatically dispatched** by PEB (Points Engine Backend) scheduler — no additional API call needed. UI only needs to write reminders on create/update; PEB handles delivery.

4. **Benefits**: Benefits must already exist before they can be linked. This API only manages the linkage — not benefit creation (that is a separate feature, E2, out of scope for this pipeline run).

5. **YEARS duration**: The UI may allow users to enter duration in years. The API accepts `cycleType: "YEARS"` — the backend converts to months internally. Display `YEARS` from responses as-is.

6. **Subscriber counts**: Present only for ACTIVE subscriptions in list views. Sourced from MySQL via Thrift batch call. Cached for 60 seconds. May be `null` for non-ACTIVE subscriptions.

7. **Edit-of-ACTIVE**: When a user edits an ACTIVE subscription, a new DRAFT is created (the ACTIVE stays live). The DRAFT has `parentId` set to the ACTIVE document's `objectId`. On approval, the ACTIVE becomes ARCHIVED and the DRAFT becomes the new ACTIVE. The UI should surface this "pending edit" state — check `parentId != null` on a DRAFT to indicate it is an edit of an existing live subscription.

8. **Approval latency**: The APPROVE action triggers a synchronous Thrift call to MySQL. This may take up to a few seconds. Display a loading indicator and handle 502 gracefully (with a retry prompt).

---

## Feature-to-Endpoint Map

| Feature / User Story | Endpoint(s) | Notes |
|----------------------|-------------|-------|
| Create a new subscription | `POST /v3/subscriptions` | Creates DRAFT |
| View subscription details | `GET /v3/subscriptions/{id}` | Returns full document |
| Edit a subscription | `PUT /v3/subscriptions/{id}` | In-place for DRAFT; new DRAFT for ACTIVE |
| List subscriptions with filters | `GET /v3/subscriptions?programId=1` | Status filter, groupTag, search, sort |
| View listing header stats | `GET /v3/subscriptions?programId=1` | `headerStats` included in list response |
| Duplicate a subscription | `POST /v3/subscriptions/{id}/duplicate` | Creates new DRAFT copy |
| Submit for approval | `PUT /v3/subscriptions/{id}/status` body: `{action: "SUBMIT_FOR_APPROVAL"}` | DRAFT → PENDING_APPROVAL |
| Pause an active subscription | `PUT /v3/subscriptions/{id}/status` body: `{action: "PAUSE"}` | ACTIVE → PAUSED + MySQL deactivated |
| Resume a paused subscription | `PUT /v3/subscriptions/{id}/status` body: `{action: "RESUME"}` | PAUSED → ACTIVE + MySQL activated |
| Archive a subscription | `PUT /v3/subscriptions/{id}/status` body: `{action: "ARCHIVE"}` | ACTIVE/PAUSED/DRAFT → ARCHIVED |
| Approver: view pending queue | `GET /v3/subscriptions/approvals?programId=1` | PENDING_APPROVAL docs only |
| Approver: approve subscription | `POST /v3/subscriptions/{id}/approve` body: `{approvalStatus: "APPROVE"}` | Triggers MySQL write SAGA |
| Approver: reject submission | `POST /v3/subscriptions/{id}/approve` body: `{approvalStatus: "REJECT"}` | Returns to DRAFT |
| Link benefit to subscription | `POST /v3/subscriptions/{id}/benefits` | MongoDB only |
| Remove benefit linkage | `DELETE /v3/subscriptions/{id}/benefits/{benefitId}` | MongoDB only |
| View linked benefits | `GET /v3/subscriptions/{id}/benefits` | Returns list of `{benefitId, addedOn}` |
