# API Contract -- Subscription Programs (v3)

> Generated from AIDLC artifacts at /Users/baljeetsingh/IdeaProjects/kalpavriksha/docs/
> Source phases: 00-ba.md, 00-prd.md, 01-architect.md, 03-designer.md, session-memory.md
> Date: 2026-04-09
> Status: Design phase -- not yet implemented. Signatures from 03-designer.md. Implementation may differ slightly.

---

## Overview

Subscription Programs let program administrators create, configure, and manage subscription-based loyalty programs (e.g., "Gold Membership", "Premium Club") through a REST API. Each subscription has a lifecycle (Draft -> Active -> Paused -> Expired -> Archived), a maker-checker approval workflow, configurable pricing/duration, and can be linked to benefit IDs. This API surface is entirely new -- no existing v2 equivalents.

---

## Project API Conventions

These conventions apply to ALL endpoints below. They are inherited from the existing intouch-api-v3 codebase.

### Response Wrapper

Every response is wrapped in `ResponseWrapper<T>`:

```json
{
  "data": { ... },
  "errors": [
    { "code": 40001, "message": "Subscription name is required" }
  ],
  "warnings": [
    { "code": 30001, "message": "Subscription has no benefits linked" }
  ]
}
```

- `data`: the resource payload (null on error)
- `errors`: array of `ApiError` objects (empty on success)
- `warnings`: array of `ApiWarning` objects (may be present on success)

### Error Response Format

All 4xx and 5xx responses use the same wrapper. The `data` field is `null`. The `errors` array contains one or more error objects:

```json
{
  "data": null,
  "errors": [
    { "code": 40001, "message": "Human-readable error message" }
  ],
  "warnings": []
}
```

Error codes are longs (not strings). Each domain has its own range. Subscription error codes use the `SUBSCRIPTION.*` naming convention in documentation but numeric codes in the response.

### Pagination

Offset-based pagination using Spring Data `Pageable`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 0 | Zero-based page index |
| `size` | int | 20 | Number of items per page |

Paginated responses return:

```json
{
  "data": {
    "content": [ ... ],
    "totalElements": 42,
    "totalPages": 3,
    "number": 0,
    "size": 20,
    "first": true,
    "last": false,
    "empty": false
  },
  "errors": [],
  "warnings": []
}
```

### Naming Convention

- JSON field names: **camelCase** (matches Jackson default + existing codebase)
- URL paths: **kebab-case** for multi-word resources, singular nouns (e.g., `/v3/subscriptions`)

### Authentication

- Mechanism: Token-based, resolved via `AbstractBaseAuthenticationToken` in Spring Security
- Required: Every request must include a valid auth token (header format depends on deployment -- typically `Authorization: Bearer <token>`)
- Tenant context: The token carries the org identity. The backend extracts `orgId` and `userId` from the token. You do NOT pass orgId as a query parameter -- it is implicit from auth.
- Tenant isolation: A request can only see/modify subscriptions belonging to its own org. Accessing another org's subscription returns 404 (not 403).

### Content Type

- Request: `Content-Type: application/json`
- Response: `application/json`

---

## Resources

### Subscriptions

Base path: `/v3/subscriptions`

---

#### POST /v3/subscriptions

**Purpose**: Create a new subscription program in Draft status.

**Maps to**: E1-US1 (Create Subscription), AC-1.1 through AC-1.8

**Request Body**:

```json
{
  "metadata": {
    "name": "Gold Membership",
    "description": "Premium loyalty subscription with exclusive benefits",
    "programId": "prog_abc123"
  },
  "config": {
    "subscriptionType": "NON_TIER",
    "duration": {
      "value": 12,
      "unit": "MONTHS"
    },
    "price": {
      "amount": 99.99,
      "currency": "USD"
    },
    "linkedTierId": null,
    "restrictToOneActivePerMember": false,
    "expiryDate": null
  },
  "benefitIds": ["benefit_001", "benefit_002"],
  "reminders": [
    { "daysBefore": 30, "channel": "EMAIL" },
    { "daysBefore": 7, "channel": "SMS" }
  ],
  "customFields": {
    "meta": [101, 102],
    "link": [201],
    "delink": [],
    "pause": [],
    "resume": []
  },
  "migrateOnExpiry": {
    "enabled": false,
    "targetSubscriptionId": null
  },
  "tierDowngradeOnExit": {
    "enabled": false,
    "downgradeTargetTierId": null
  }
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `metadata.name` | string | Yes | Max 255 chars. Must be unique within programId + org. |
| `metadata.description` | string | No | Max 1000 chars. |
| `metadata.programId` | string | Yes | Must reference a valid loyalty program. **Immutable after creation.** |
| `config.subscriptionType` | enum | Yes | `TIER_BASED` or `NON_TIER` |
| `config.duration.value` | int | Yes | Positive integer |
| `config.duration.unit` | enum | Yes | `DAYS`, `MONTHS`, `YEARS` |
| `config.price.amount` | decimal | No | >= 0. If null, subscription is free. |
| `config.price.currency` | string | Conditional | Required if `price.amount` is provided. ISO 4217 code. |
| `config.linkedTierId` | string | Conditional | Required if `subscriptionType` = `TIER_BASED`. Must be null if `NON_TIER`. |
| `config.restrictToOneActivePerMember` | boolean | No | Default: false |
| `config.expiryDate` | datetime | No | ISO 8601 format: `yyyy-MM-dd'T'HH:mm:ssXXX` |
| `benefitIds` | string[] | No | Array of benefit IDs. No server-side validation (dummy IDs accepted). |
| `reminders` | object[] | No | Max 5 entries. Each: `daysBefore` (positive int) + `channel` (SMS/EMAIL/PUSH). |
| `customFields` | object | No | Field ID arrays per lifecycle event. |
| `migrateOnExpiry` | object | No | Migration config for expired subscriptions. |
| `tierDowngradeOnExit` | object | No | Tier downgrade config on exit. |

**Response -- Success** (HTTP 201 Created):

```json
{
  "data": {
    "id": "680a1b2c3d4e5f6a7b8c9d0e",
    "unifiedSubscriptionId": "a1b2c3d4e5f6a7b8c9d0e1f2",
    "metadata": {
      "name": "Gold Membership",
      "description": "Premium loyalty subscription with exclusive benefits",
      "programId": "prog_abc123",
      "orgId": 50672,
      "status": "DRAFT",
      "startDate": null,
      "endDate": null,
      "createdOn": "2026-04-09T10:30:00+05:30",
      "lastModifiedOn": "2026-04-09T10:30:00+05:30",
      "createdBy": 15043871,
      "lastModifiedBy": 15043871
    },
    "config": {
      "subscriptionType": "NON_TIER",
      "duration": { "value": 12, "unit": "MONTHS" },
      "price": { "amount": 99.99, "currency": "USD" },
      "linkedTierId": null,
      "restrictToOneActivePerMember": false,
      "expiryDate": null
    },
    "benefitIds": ["benefit_001", "benefit_002"],
    "reminders": [
      { "daysBefore": 30, "channel": "EMAIL" },
      { "daysBefore": 7, "channel": "SMS" }
    ],
    "customFields": {
      "meta": [101, 102], "link": [201], "delink": [], "pause": [], "resume": []
    },
    "migrateOnExpiry": { "enabled": false, "targetSubscriptionId": null },
    "tierDowngradeOnExit": { "enabled": false, "downgradeTargetTierId": null },
    "comments": null,
    "parentId": null,
    "version": 1,
    "partnerProgramId": null
  },
  "errors": [],
  "warnings": []
}
```

**Response -- Error Cases**:

| HTTP Status | Error Code | When | Example Message |
|-------------|------------|------|-----------------|
| 400 | `SUBSCRIPTION.NAME_DUPLICATE` | Name already exists for this programId + org | "Subscription name already exists for this program" |
| 400 | (validation) | Missing required field | "Name is required" / "Duration is required" |
| 400 | `SUBSCRIPTION.TIER_ID_REQUIRED` | TIER_BASED without linkedTierId | "Linked tier ID is required for TIER_BASED subscriptions" |
| 400 | `SUBSCRIPTION.REMINDERS_LIMIT` | More than 5 reminders | "Maximum 5 reminders allowed" |

**Notes**:
- `id` is the MongoDB ObjectId (used as path parameter in subsequent calls)
- `unifiedSubscriptionId` is a UUID generated server-side, immutable, used as the logical business ID
- `metadata.orgId`, `metadata.createdBy`, `metadata.lastModifiedBy`, `metadata.createdOn`, `metadata.lastModifiedOn` are set server-side from auth context -- do NOT send these in the request
- `metadata.status` is always `DRAFT` on create -- do NOT send this in the request
- `partnerProgramId` is null until the subscription is approved (set after Thrift call)

---

#### GET /v3/subscriptions/{objectId}

**Purpose**: Retrieve a single subscription by its MongoDB ObjectId.

**Maps to**: E1-US2 (Get Subscription), AC-2.1 through AC-2.3

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `objectId` | path | string | Yes | MongoDB ObjectId (the `id` field from create response) |

**Response -- Success** (HTTP 200 OK):

Same shape as the create response `data` object. Status may show derived values:
- If stored status is `ACTIVE` and `startDate > now`: response shows `"status": "SCHEDULED"`
- If stored status is `ACTIVE` and `endDate < now`: response shows `"status": "EXPIRED"`

**Response -- Error Cases**:

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 404 | `SUBSCRIPTION.NOT_FOUND` | ObjectId not found or belongs to different org |

**Notes**:
- SCHEDULED and EXPIRED are **derived at read time** -- they are not stored. The UI should treat them as display-only statuses.
- Another org's subscription returns 404 (not 403) for security.

---

#### GET /v3/subscriptions

**Purpose**: List subscriptions for the org, with optional filters.

**Maps to**: E1-US3 (List Subscriptions), AC-3.1 through AC-3.4

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `programId` | query | string | No | Filter by loyalty program ID |
| `status` | query | enum | No | Filter by status: `DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `PAUSED`, `EXPIRED`, `ARCHIVED` |
| `page` | query | int | No | Page index (default: 0) |
| `size` | query | int | No | Page size (default: 20) |

**Response -- Success** (HTTP 200 OK):

```json
{
  "data": {
    "content": [
      { "id": "...", "unifiedSubscriptionId": "...", "metadata": { ... }, "config": { ... }, ... },
      { "id": "...", "unifiedSubscriptionId": "...", "metadata": { ... }, "config": { ... }, ... }
    ],
    "totalElements": 42,
    "totalPages": 3,
    "number": 0,
    "size": 20,
    "first": true,
    "last": false,
    "empty": false
  },
  "errors": [],
  "warnings": []
}
```

**Notes**:
- When filtering by `status=ACTIVE`, results include only stored-ACTIVE subscriptions where startDate <= now AND (endDate is null OR endDate > now). SCHEDULED and EXPIRED subscriptions are NOT included in ACTIVE results.
- When filtering by `status=SCHEDULED`: returns stored-ACTIVE subscriptions where startDate > now.
- When filtering by `status=EXPIRED`: returns stored-ACTIVE subscriptions where endDate < now.

---

#### PUT /v3/subscriptions/{unifiedSubscriptionId}

**Purpose**: Update a subscription's configuration.

**Maps to**: E1-US4 (Update Subscription), AC-4.1 through AC-4.6

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `unifiedSubscriptionId` | path | string | Yes | The business UUID (not the ObjectId) |

**Request Body**: Same shape as POST (full subscription document). The `metadata.programId` field **must match** the existing value -- it cannot be changed.

**Response -- Success** (HTTP 200 OK):

Returns the updated subscription document. Behaviour depends on current status:

| Current Status | Behaviour |
|----------------|-----------|
| DRAFT | Updated in place. Same ObjectId returned. |
| ACTIVE | **Creates a new DRAFT document** with version N+1 and `parentId` pointing to the ACTIVE document's ObjectId. New ObjectId returned. |
| PAUSED | Same as ACTIVE -- creates versioned DRAFT. |
| PENDING_APPROVAL | Returns 400. |
| EXPIRED | Returns 400. |
| ARCHIVED | Returns 400. |

**Response -- Error Cases**:

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `SUBSCRIPTION.UPDATE_NOT_ALLOWED` | Status is PENDING_APPROVAL, EXPIRED, or ARCHIVED |
| 400 | `SUBSCRIPTION.PROGRAM_ID_IMMUTABLE` | Request changes programId |
| 400 | `SUBSCRIPTION.NAME_DUPLICATE` | New name conflicts with existing subscription in same programId |
| 404 | `SUBSCRIPTION.NOT_FOUND` | Subscription not found or different org |

**Notes**:
- When updating an ACTIVE subscription, the ACTIVE version remains unchanged and visible to users. The new DRAFT version must go through the approval workflow before it replaces the ACTIVE version.
- If a DRAFT already exists for an ACTIVE subscription (previous edit not yet approved), the existing DRAFT is updated -- no new document is created.

---

#### DELETE /v3/subscriptions/{objectId}

**Purpose**: Delete a DRAFT subscription.

**Maps to**: E1-US5 (Delete Subscription), AC-5.1, AC-5.2

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `objectId` | path | string | Yes | MongoDB ObjectId |

**Response -- Success** (HTTP 204 No Content):

```json
{
  "data": null,
  "errors": [],
  "warnings": []
}
```

**Response -- Error Cases**:

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `SUBSCRIPTION.DELETE_NOT_ALLOWED` | Status is not DRAFT |
| 404 | `SUBSCRIPTION.NOT_FOUND` | Not found or different org |

**Notes**:
- Only original DRAFT subscriptions can be deleted (no parentId).
- Versioned DRAFTs (created by editing an ACTIVE subscription) can also be deleted -- this discards the pending edit.

---

### Subscription Lifecycle

#### PUT /v3/subscriptions/{objectId}/status

**Purpose**: Change the status of a subscription (submit for approval, approve, reject, pause, resume, archive).

**Maps to**: Epic 2 (Lifecycle Management), AC-6.1 through AC-11.3

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `objectId` | path | string | Yes | MongoDB ObjectId |
| `currentStatus` | query | enum | Yes | The status the UI believes the subscription is currently in (optimistic concurrency check) |

**Request Body**:

```json
{
  "action": "APPROVE",
  "reason": "Reviewed and approved for Q2 launch"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | One of: `SUBMIT_FOR_APPROVAL`, `APPROVE`, `REJECT`, `PAUSE`, `RESUME`, `ARCHIVE` |
| `reason` | string | No | Max 150 chars. Stored as `comments` on the subscription. Typically used for REJECT. |

**Valid Transitions**:

| Current Status | Allowed Actions | Result Status | Side Effects |
|----------------|-----------------|---------------|--------------|
| DRAFT | SUBMIT_FOR_APPROVAL | PENDING_APPROVAL | -- |
| DRAFT | ARCHIVE | ARCHIVED | -- |
| PENDING_APPROVAL | APPROVE | ACTIVE | Thrift call to MySQL (creates/updates partner_programs record with is_active=true) |
| PENDING_APPROVAL | REJECT | DRAFT | `reason` stored as `comments` |
| ACTIVE | PAUSE | PAUSED | Thrift call to MySQL (sets is_active=false) |
| ACTIVE | ARCHIVE | ARCHIVED | -- |
| PAUSED | RESUME | ACTIVE | Thrift call to MySQL (sets is_active=true) |
| EXPIRED (derived) | ARCHIVE | ARCHIVED | -- |

**Response -- Success** (HTTP 200 OK):

Returns the updated subscription document with the new status.

**Special case -- Approve an edit-of-active** (subscription has `parentId`):
When approving a DRAFT that has a `parentId`, the backend performs a swap:
1. The old ACTIVE version becomes `SNAPSHOT` (preserved for history)
2. The DRAFT becomes the new `ACTIVE`
3. Thrift is called with the updated subscription data

The response returns the newly-ACTIVE document.

**Response -- Error Cases**:

| HTTP Status | Error Code | When |
|-------------|------------|------|
| 400 | `SUBSCRIPTION.INVALID_TRANSITION` | Action not allowed from current status. Message includes allowed transitions. |
| 400 | `SUBSCRIPTION.NAME_CONFLICT_ORG` | On APPROVE: name conflicts at org level in MySQL (different from programId-scoped MongoDB check) |
| 404 | `SUBSCRIPTION.NOT_FOUND` | Not found or different org |
| 500 | `SUBSCRIPTION.PUBLISH_FAILED` | On APPROVE/PAUSE/RESUME: Thrift call to MySQL failed. Status is NOT changed. Safe to retry. |

**Notes**:
- `currentStatus` is a concurrency guard. If the subscription's actual status doesn't match `currentStatus`, the request fails with 400. This prevents race conditions where two users try to change status simultaneously.
- APPROVE, PAUSE, and RESUME trigger a **synchronous Thrift call** to the EMF service. If the call fails, the status change is rolled back. The UI should handle 500 with a retry option.
- EXPIRED is a **derived status** (not stored). To archive an expired subscription, send `currentStatus=EXPIRED` and `action=ARCHIVE`.

---

### Subscription Benefits

#### POST /v3/subscriptions/{objectId}/benefits

**Purpose**: Link benefit IDs to a subscription.

**Maps to**: E3-US1 (Link Benefits), AC-12.1 through AC-12.3

**Request Body**:

```json
["benefit_001", "benefit_002", "benefit_003"]
```

(Plain JSON array of string benefit IDs)

**Response -- Success** (HTTP 200 OK):

Returns the full subscription document with updated `benefitIds` array.

**Notes**:
- IDs are appended. Duplicates are silently deduplicated.
- No validation against a benefits service -- any string ID is accepted. When the benefits service is built (future epic), validation will be added.

---

#### GET /v3/subscriptions/{objectId}/benefits

**Purpose**: Get the list of benefit IDs linked to a subscription.

**Maps to**: E3-US2 (List Benefits), AC-13.1

**Response -- Success** (HTTP 200 OK):

```json
{
  "data": ["benefit_001", "benefit_002", "benefit_003"],
  "errors": [],
  "warnings": []
}
```

---

#### DELETE /v3/subscriptions/{objectId}/benefits

**Purpose**: Unlink benefit IDs from a subscription.

**Maps to**: E3-US3 (Unlink Benefits), AC-14.1, AC-14.2

**Request Body**:

```json
["benefit_002"]
```

**Response -- Success** (HTTP 200 OK):

Returns the full subscription document with updated `benefitIds` array.

**Notes**:
- Removing a non-existent ID is a no-op (idempotent). No error is returned.

---

### Approvals

#### GET /v3/subscriptions/approvals

**Purpose**: List all subscriptions pending approval for the org.

**Maps to**: E4-US1 (List Pending Approvals), AC-15.1, AC-15.2

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `page` | query | int | No | Page index (default: 0) |
| `size` | query | int | No | Page size (default: 20) |

**Response -- Success** (HTTP 200 OK):

Paginated list of subscriptions with `status = PENDING_APPROVAL`. Same pagination shape as the list endpoint.

**Notes**:
- Includes subscriptions that are new (no parentId) and subscriptions that are edits of active versions (have parentId).
- The UI can check the `parentId` field to determine if this is a new subscription or an edit.

---

## Enums and Constants

| Enum | Values | Used In |
|------|--------|---------|
| `SubscriptionStatus` | `DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `PAUSED`, `EXPIRED`, `ARCHIVED`, `SNAPSHOT`, `SCHEDULED` | `metadata.status` response field. SCHEDULED and EXPIRED are derived (not stored). SNAPSHOT is internal (maker-checker history). |
| `SubscriptionAction` | `SUBMIT_FOR_APPROVAL`, `APPROVE`, `REJECT`, `PAUSE`, `RESUME`, `ARCHIVE` | `action` field in status change request |
| `SubscriptionType` | `TIER_BASED`, `NON_TIER` | `config.subscriptionType` |
| `DurationUnit` | `DAYS`, `MONTHS`, `YEARS` | `config.duration.unit` |
| `ReminderChannel` | `SMS`, `EMAIL`, `PUSH` | `reminders[].channel` |

### Status Display Guide for UI

| Status | User-Facing Label | Color Suggestion | Editable? | Deletable? |
|--------|-------------------|------------------|-----------|------------|
| DRAFT | Draft | Gray | Yes (in-place) | Yes |
| PENDING_APPROVAL | Pending Approval | Yellow | No | No |
| ACTIVE | Active | Green | Yes (creates versioned draft) | No |
| SCHEDULED | Scheduled | Blue | No (edit the underlying ACTIVE) | No |
| PAUSED | Paused | Orange | Yes (creates versioned draft) | No |
| EXPIRED | Expired | Red | No | No |
| ARCHIVED | Archived | Dark Gray | No | No |
| SNAPSHOT | (hidden) | -- | No | No |

---

## Integration Notes

1. **Create before Approve**: A subscription must be created (POST) before it can go through the approval workflow. The sequence is: Create -> Submit for Approval -> Approve.

2. **Edit-of-Active Flow**: To modify an ACTIVE subscription, call PUT with its `unifiedSubscriptionId`. This creates a new DRAFT version. Submit that DRAFT for approval. On APPROVE, the old version becomes SNAPSHOT and the new version becomes ACTIVE.

3. **Thrift Side Effects**: APPROVE, PAUSE, and RESUME trigger synchronous calls to the EMF backend service. If the Thrift call fails, the response is 500 and the status is NOT changed. The UI should offer a retry button for these operations.

4. **SCHEDULED and EXPIRED are display-only**: These statuses are computed from `startDate` and `endDate` at read time. You cannot filter the list endpoint by `status=SCHEDULED` to get only scheduled subscriptions [TBD -- filtering by derived status may be supported in a future release].

5. **Name Uniqueness Scope**: Names must be unique within a `programId` (not across the entire org). The UI should validate name uniqueness per program in its form validation, but the server enforces it.

6. **programId is Immutable**: Once a subscription is created with a `programId`, it cannot be changed. The UI should disable the program selector after creation.

7. **Optimistic Concurrency**: The `currentStatus` query parameter on the status change endpoint acts as a concurrency guard. Always send the status the UI last saw. If someone else changed the status in between, the request fails with 400.

8. **No Rate Limits**: No explicit rate limits are defined for this API. Standard platform-level rate limiting applies.

9. **File Uploads**: None. No file upload endpoints in this API.

10. **Real-time Updates**: No WebSocket or SSE endpoints. The UI should poll or refresh to see status changes made by other users.

---

## Feature-to-Endpoint Map

| Feature / User Story | Endpoint(s) | Notes |
|----------------------|-------------|-------|
| E1-US1: Create Subscription | POST /v3/subscriptions | Returns 201 with full document |
| E1-US2: Get Subscription | GET /v3/subscriptions/{objectId} | Derived status (SCHEDULED/EXPIRED) applied |
| E1-US3: List Subscriptions | GET /v3/subscriptions | Paginated, filterable by programId and status |
| E1-US4: Update Subscription | PUT /v3/subscriptions/{unifiedSubscriptionId} | DRAFT: in-place. ACTIVE/PAUSED: versioned draft. |
| E1-US5: Delete Subscription | DELETE /v3/subscriptions/{objectId} | DRAFT only |
| E2-US1: Submit for Approval | PUT /v3/subscriptions/{objectId}/status | action=SUBMIT_FOR_APPROVAL |
| E2-US2: Approve | PUT /v3/subscriptions/{objectId}/status | action=APPROVE. Triggers Thrift. |
| E2-US3: Reject | PUT /v3/subscriptions/{objectId}/status | action=REJECT. Stores reason as comments. |
| E2-US4: Pause | PUT /v3/subscriptions/{objectId}/status | action=PAUSE. Triggers Thrift (is_active=false). |
| E2-US5: Resume | PUT /v3/subscriptions/{objectId}/status | action=RESUME. Triggers Thrift (is_active=true). |
| E2-US6: Archive | PUT /v3/subscriptions/{objectId}/status | action=ARCHIVE. Terminal state. |
| E3-US1: Link Benefits | POST /v3/subscriptions/{objectId}/benefits | Appends, deduplicates |
| E3-US2: List Benefits | GET /v3/subscriptions/{objectId}/benefits | Returns benefitIds array |
| E3-US3: Unlink Benefits | DELETE /v3/subscriptions/{objectId}/benefits | Idempotent removal |
| E4-US1: List Pending Approvals | GET /v3/subscriptions/approvals | Paginated |

---

## Date Format Reference

All date/datetime fields use ISO 8601 with timezone offset:

```
yyyy-MM-dd'T'HH:mm:ssXXX
```

Example: `"2026-04-09T10:30:00+05:30"`

The UI should send dates in this format. The server returns dates in this format. Use `java.util.Date` compatible parsing (not `java.time.Instant`).

---

## Key IDs Glossary

| Field | Format | Mutable | Where Used |
|-------|--------|---------|------------|
| `id` (objectId) | MongoDB ObjectId (24-char hex) | No | Path parameter for GET, DELETE, status change, benefits |
| `unifiedSubscriptionId` | UUID (32-char hex, no hyphens) | No | Path parameter for PUT (update). Logical business ID. |
| `partnerProgramId` | Integer | No | Set server-side after first APPROVE. MySQL partner_programs.id. |
| `parentId` | MongoDB ObjectId | No | Points to ACTIVE version when this is a versioned DRAFT. Null for original drafts. |
| `metadata.programId` | String | No (immutable) | Loyalty program this subscription belongs to. Set at creation, cannot be changed. |
