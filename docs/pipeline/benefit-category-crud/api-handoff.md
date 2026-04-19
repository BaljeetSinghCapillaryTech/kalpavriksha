# API Handoff — Benefit Category CRUD (CAP-185145)

> **Generated from**: `01-architect.md`, `03-designer.md`, `session-memory.md` (D-01..D-52), canonical controller + DTO source code
> **Source phases**: Architect (Phase 6), Designer (Phase 7), SDET (Phase 9), Developer (Phase 10)
> **Date**: 2026-04-19
> **Status**: Implemented — code-verified against `intouch-api-v3-2/intouch-api-v3` (commit `0ae66f606`)

---

## Overview

The Benefit Category CRUD feature (CAP-185145) lets admins create, read, update, activate, and deactivate **benefit categories** — program-scoped metadata that groups loyalty benefits into named buckets (e.g., "VIP Perks") and associates them with specific tier slabs. It is a net-new surface; it does not change any existing endpoints.

---

## Base Path and Versioning

- **Base path**: `/v3/benefitCategories`
- **Versioning**: path-based (`v3`)
- **Content-Type**: `application/json` (request and response)

---

## Authentication

| Endpoint | Required Auth |
|----------|---------------|
| `GET /v3/benefitCategories/{id}` | KeyOnly **or** BasicAndKey |
| `GET /v3/benefitCategories` | KeyOnly **or** BasicAndKey |
| `POST /v3/benefitCategories` | BasicAndKey |
| `PUT /v3/benefitCategories/{id}` | BasicAndKey |
| `POST /v3/benefitCategories/{id}/activate` | BasicAndKey |
| `POST /v3/benefitCategories/{id}/deactivate` | BasicAndKey |

**Required headers (all endpoints)**:
```
Authorization: Basic <base64(orgCode:apiKey)>   ← BasicAndKey
```
or
```
Authorization: Key <apiKey>   ← KeyOnly (read endpoints only)
```

`orgId` and `entityId` are extracted server-side from the auth token — the client does **not** supply them as request fields. No `@PreAuthorize('ADMIN_USER')` role gate in MVP.

---

## Response Envelope

All successful responses (except 204 No Content) are wrapped in:

```json
{
  "data": { ... },
  "errors": [],
  "warnings": []
}
```

Error responses (400, 409, 500) follow the same envelope with `data: null` and populated `errors`:

```json
{
  "data": null,
  "errors": [
    { "code": 400, "message": "BENEFIT_CATEGORY.SLAB_IDS_REQUIRED" }
  ],
  "warnings": []
}
```

> **Platform quirk (OQ-45)**: A 404 Not Found does **not** return HTTP 404. It returns **HTTP 200** with a non-empty `errors` array and `data: null`. See Error Codes table below.

---

## Endpoints

### 1. POST /v3/benefitCategories — Create

**Purpose**: Create a new benefit category for a loyalty program, attaching it to one or more tier slabs.

**Maps to**: BA US-1 (Create benefit category), AC-BC01 (category created with name + slabs), BT-001..BT-013.

#### Request

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `programId` | body | integer | **yes** | Loyalty program ID. Must be ≥ 1. |
| `name` | body | string | **yes** | Category name. Max 255 chars. Case-sensitive (D-47). |
| `slabIds` | body | integer[] | **yes** | Tier slab IDs to associate. Min 1 entry. All IDs must belong to the same program. |
| `categoryType` | body | string | no | Defaults to `"BENEFITS"` if omitted or null. Only valid value at v1: `"BENEFITS"`. |

**Request body**:
```json
{
  "programId": 5,
  "name": "VIP Perks",
  "slabIds": [1, 3, 5],
  "categoryType": "BENEFITS"
}
```

#### Response — 201 Created

```json
{
  "data": {
    "id": 42,
    "orgId": 100,
    "programId": 5,
    "name": "VIP Perks",
    "categoryType": "BENEFITS",
    "slabIds": [1, 3, 5],
    "active": true,
    "createdOn": "2026-04-18T10:30:45+05:30",
    "createdBy": 7,
    "updatedOn": null,
    "updatedBy": null,
    "stateChanged": null
  },
  "errors": [],
  "warnings": []
}
```

#### Error Responses

| HTTP Status | Error Code | Condition |
|-------------|------------|-----------|
| 400 | `BENEFIT_CATEGORY.NAME_REQUIRED` | `name` is null or blank |
| 400 | `BENEFIT_CATEGORY.NAME_TOO_LONG` | `name` exceeds 255 characters |
| 400 | `BENEFIT_CATEGORY.PROGRAM_ID_REQUIRED` | `programId` is null |
| 400 | `BENEFIT_CATEGORY.PROGRAM_ID_INVALID` | `programId` < 1 |
| 400 | `BENEFIT_CATEGORY.SLAB_IDS_REQUIRED` | `slabIds` is null or empty list |
| 400 | `BENEFIT_CATEGORY.SLAB_ID_INVALID` | Any `slabId` in the list is < 1 |
| 409 | `BC_NAME_TAKEN_ACTIVE` | An active category with the same name exists in this `(orgId, programId)` (case-sensitive) |
| 409 | `BC_UNKNOWN_SLAB` | One or more `slabIds` do not exist for this org |
| 409 | `BC_CROSS_PROGRAM_SLAB` | One or more `slabIds` belong to a different program |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

#### Business Rules

- **Name uniqueness**: Case-sensitive byte comparison within `(orgId, programId, isActive=true)`. `"Gold Tier"` and `"gold tier"` are distinct and can coexist (D-47).
- **Slab validation**: All `slabIds` must belong to the caller's org AND to the specified `programId`. Wrong-org or wrong-program slabs both return `BC_UNKNOWN_SLAB` (same error path).
- **Duplicate slab IDs**: Silently de-duplicated server-side (insertion order preserved).
- **categoryType**: Only `"BENEFITS"` is a valid value. Unknown values are coerced to `"BENEFITS"`.

---

### 2. PUT /v3/benefitCategories/{id} — Update

**Purpose**: Update the name and/or slab associations of an existing active benefit category. Slab list is a full replacement — the server diffs current vs. new and soft-deletes removed slabs.

**Maps to**: BA US-3 (Update category name/slabs), AC-BC03, BT-028..BT-041.

#### Request

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `id` | path | integer | **yes** | ID of the category to update. |
| `name` | body | string | no | New name. Max 255 chars. Omit to leave unchanged. |
| `slabIds` | body | integer[] | **yes** | Full replacement slab list. Min 1 entry. |

**Request body**:
```json
{
  "name": "Platinum Perks",
  "slabIds": [1, 3, 7]
}
```

#### Response — 200 OK

Same shape as Create response (BenefitCategoryResponse), `stateChanged: null`.

```json
{
  "data": {
    "id": 42,
    "orgId": 100,
    "programId": 5,
    "name": "Platinum Perks",
    "categoryType": "BENEFITS",
    "slabIds": [1, 3, 7],
    "active": true,
    "createdOn": "2026-04-18T10:30:45+05:30",
    "createdBy": 7,
    "updatedOn": "2026-04-19T08:15:22+05:30",
    "updatedBy": 9,
    "stateChanged": null
  },
  "errors": [],
  "warnings": []
}
```

#### Error Responses

| HTTP Status | Error Code | Condition |
|-------------|------------|-----------|
| 400 | `BENEFIT_CATEGORY.NAME_TOO_LONG` | `name` exceeds 255 characters |
| 400 | `BENEFIT_CATEGORY.SLAB_IDS_REQUIRED` | `slabIds` is null or empty list `[]` |
| 400 | `BENEFIT_CATEGORY.SLAB_ID_INVALID` | Any `slabId` < 1 |
| **200 + errors** | `BC_NOT_FOUND` | Category does not exist for this org (platform quirk — HTTP 200, not 404) |
| 409 | `BC_INACTIVE_WRITE_FORBIDDEN` | Category is soft-deleted (`isActive=false`). Must reactivate first via `/activate`. |
| 409 | `BC_NAME_TAKEN_ACTIVE` | Another active category in the same program now holds this name |
| 409 | `BC_UNKNOWN_SLAB` / `BC_CROSS_PROGRAM_SLAB` | slab validation failed |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

#### Business Rules

- **Inactive write forbidden**: PUT on a soft-deleted category returns 409 `BC_INACTIVE_WRITE_FORBIDDEN`. Use `POST /{id}/activate` to restore it first (ADR-002, D-27).
- **Diff-and-apply semantics**: The slab list is a full replacement. Slabs in the new list but not in current → added. Slabs in current but not in new list → soft-deleted. Slabs in both → unchanged. Previously removed slabs that are re-added get a **new** mapping row (the old soft-deleted row is NOT reactivated — it remains as audit history).
- **Last-write-wins**: No optimistic locking (ADR-001). Concurrent PUT calls on the same category can silently overwrite each other.

---

### 3. GET /v3/benefitCategories/{id} — Get Single

**Purpose**: Fetch a single benefit category by ID. By default returns only active categories. Pass `?includeInactive=true` to retrieve soft-deleted categories for audit purposes.

**Maps to**: BA US-2 (Read category), AC-BC02, BT-014..BT-019.

#### Request

| Parameter | Location | Type | Required | Default | Description |
|-----------|----------|------|----------|---------|-------------|
| `id` | path | integer | **yes** | — | Category ID. |
| `includeInactive` | query | boolean | no | `false` | `true` → returns the category even if soft-deleted. |

**Example requests**:
```
GET /v3/benefitCategories/42
GET /v3/benefitCategories/42?includeInactive=true
```

#### Response — 200 OK (category found)

Same shape as Create response.

```json
{
  "data": {
    "id": 42,
    "orgId": 100,
    "programId": 5,
    "name": "VIP Perks",
    "categoryType": "BENEFITS",
    "slabIds": [1, 3, 5],
    "active": true,
    "createdOn": "2026-04-18T10:30:45+05:30",
    "createdBy": 7,
    "updatedOn": null,
    "updatedBy": null,
    "stateChanged": null
  },
  "errors": [],
  "warnings": []
}
```

**Example: `?includeInactive=true` on a soft-deleted category**:
```json
{
  "data": {
    "id": 42,
    "orgId": 100,
    "programId": 5,
    "name": "VIP Perks",
    "categoryType": "BENEFITS",
    "slabIds": [],
    "active": false,
    "createdOn": "2026-04-18T10:30:45+05:30",
    "createdBy": 7,
    "updatedOn": "2026-04-19T11:00:00+05:30",
    "updatedBy": 9,
    "stateChanged": null
  },
  "errors": [],
  "warnings": []
}
```

#### Error Responses

| HTTP Status | Error Code | Condition |
|-------------|------------|-----------|
| **200 + errors** | `BC_NOT_FOUND` | ID does not exist for this org, OR category is soft-deleted and `includeInactive` was not `true` — platform quirk: HTTP 200 not 404 |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

#### Business Rules

- Default (`includeInactive=false` or param absent): returns 200 + `BC_NOT_FOUND` error for soft-deleted categories.
- `?includeInactive=true`: returns the full DTO even if `active: false`. `slabIds` will be `[]` (slab mappings are also soft-deleted on category deactivation).
- Tenant isolation is always enforced — the `orgId` from the auth token scopes the lookup.

---

### 4. GET /v3/benefitCategories — List (Paginated)

**Purpose**: List benefit categories for an org with optional filtering by program and active state. Results are paginated.

**Maps to**: BA US-4 (List/search categories), AC-BC04, BT-020..BT-027.

#### Request

| Parameter | Location | Type | Required | Default | Constraints | Description |
|-----------|----------|------|----------|---------|-------------|-------------|
| `programId` | query | integer | no | — | — | Filter to a specific program. |
| `isActive` | query | boolean | no | — (returns active only) | `true` or `false` | Filter by active state. Omit to return active categories only. |
| `page` | query | integer | no | `0` | ≥ 0 | 0-indexed page number. |
| `size` | query | integer | no | `20` | 1..100 | Page size. Values > 100 return HTTP 400. |

**Example requests**:
```
GET /v3/benefitCategories
GET /v3/benefitCategories?programId=5&isActive=true&page=0&size=20
GET /v3/benefitCategories?isActive=false&page=1&size=50
```

#### Response — 200 OK

```json
{
  "data": {
    "data": [
      {
        "id": 42,
        "orgId": 100,
        "programId": 5,
        "name": "VIP Perks",
        "categoryType": "BENEFITS",
        "slabIds": [1, 3, 5],
        "active": true,
        "createdOn": "2026-04-18T10:30:45+05:30",
        "createdBy": 7,
        "updatedOn": null,
        "updatedBy": null,
        "stateChanged": null
      }
    ],
    "page": 0,
    "size": 20,
    "total": 1
  },
  "errors": [],
  "warnings": []
}
```

> Note: The paginated payload (`data`, `page`, `size`, `total`) is nested inside `ResponseWrapper.data`.

#### Error Responses

| HTTP Status | Error Code | Condition |
|-------------|------------|-----------|
| 400 | `BC_PAGE_SIZE_EXCEEDED` | `size` > 100 |
| 400 | Platform `VALIDATION_FAILED` | `isActive` has an invalid value (e.g., `?isActive=foo`) — HTTP 200 with error envelope (platform quirk, D-48) |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

#### Business Rules

- Results are sorted **`ORDER BY created_on DESC, id DESC`** (newest first). Sort order is fixed — no sort param.
- `size` is capped at 100. The service throws `BC_PAGE_SIZE_EXCEEDED` (HTTP 400) if exceeded.
- Default page size is `20` (controller default in code). The design default in ADR-011 is `50` — use the controller code value (`20`) as canonical.
- Each category in the list includes its full `slabIds` (fetched in a single bulk query, no N+1).
- `isActive=foo` (invalid boolean string): `MethodArgumentTypeMismatchException` → HTTP 200 + `VALIDATION_FAILED` error code in envelope (D-48, platform convention).

---

### 5. POST /v3/benefitCategories/{id}/activate — Activate

**Purpose**: Reactivate a soft-deleted benefit category. Returns the full category DTO on a real state change; returns 204 No Content if the category was already active (idempotent).

**Maps to**: BA US-5 (Reactivate category), AC-BC06, BT-042..BT-050.

> **Note on HTTP verb**: The controller uses `@PostMapping` (not `@PatchMapping`). The design documents use `PATCH` in diagrams; the implemented code uses `POST`. Use `POST` in your HTTP client.

#### Request

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `id` | path | integer | **yes** | ID of the category to activate. |

No request body.

#### Response — 200 OK (state changed: was inactive → now active)

Returns full BenefitCategoryResponse with `stateChanged: true`.

```json
{
  "data": {
    "id": 42,
    "orgId": 100,
    "programId": 5,
    "name": "VIP Perks",
    "categoryType": "BENEFITS",
    "slabIds": [],
    "active": true,
    "createdOn": "2026-04-18T10:30:45+05:30",
    "createdBy": 7,
    "updatedOn": "2026-04-19T12:00:00+05:30",
    "updatedBy": 9,
    "stateChanged": true
  },
  "errors": [],
  "warnings": []
}
```

#### Response — 204 No Content (no-op: category was already active)

Empty body. No `ResponseWrapper`.

#### Error Responses

| HTTP Status | Error Code | Condition |
|-------------|------------|-----------|
| **200 + errors** | `BC_NOT_FOUND` | Category does not exist for this org (platform quirk) |
| 409 | `BC_NAME_TAKEN_ON_REACTIVATE` | A DIFFERENT active category in the same program now holds this category's name |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

#### Business Rules

- **Slab mappings are NOT auto-reactivated** on activate (ADR-002). After activation, `slabIds` will be `[]`. Admin must issue a subsequent `PUT` to re-attach slabs.
- **Name collision on reactivation**: if an active category in the same program already uses this category's name, activation is blocked with 409 `BC_NAME_TAKEN_ON_REACTIVATE`. Admin must rename the conflicting active category first, then retry.
- **Idempotency (D-39)**: already-active → 204 No Content (no-op, no error).
- **`stateChanged` field**: Only populated (set to `true` or `false`) for the activate endpoint. All other endpoints return `stateChanged: null`. This field is the no-op sentinel — controller emits 204 when `stateChanged=false`.

---

### 6. POST /v3/benefitCategories/{id}/deactivate — Deactivate

**Purpose**: Soft-delete a benefit category. Cascades to all active slab mappings in the same transaction. Always returns 204 No Content (idempotent — deactivating an already-inactive category is a no-op).

**Maps to**: BA US-6 (Deactivate category), AC-BC05, BT-051..BT-056.

> **Note on HTTP verb**: The controller uses `@PostMapping` (not `@PatchMapping`). Use `POST`.

#### Request

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `id` | path | integer | **yes** | ID of the category to deactivate. |

No request body.

#### Response — 204 No Content

Always 204 on both state change and idempotent no-op. Empty body.

#### Error Responses

| HTTP Status | Error Code | Condition |
|-------------|------------|-----------|
| **200 + errors** | `BC_NOT_FOUND` | Category does not exist for this org (platform quirk) |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

#### Business Rules

- **Cascade**: All active slab mappings for this category are also soft-deleted in the **same database transaction** (ADR-004). After deactivation, `slabIds` becomes `[]`.
- **Idempotency**: already-inactive → 204 No Content (no error, no body).
- **Soft-delete only**: The row is never hard-deleted. Use `?includeInactive=true` on GET to retrieve the record for audit.

---

## Data Types

### BenefitCategoryCreateRequest

| Field | Type | Nullable | Required | Validation |
|-------|------|----------|----------|------------|
| `programId` | integer | no | **yes** | ≥ 1 |
| `name` | string | no | **yes** | Non-blank; max 255 chars |
| `slabIds` | integer[] | no | **yes** | Min 1 element; each element ≥ 1 |
| `categoryType` | string | yes | no | `"BENEFITS"` only; defaults to `"BENEFITS"` if null/absent |

### BenefitCategoryUpdateRequest

| Field | Type | Nullable | Required | Validation |
|-------|------|----------|----------|------------|
| `name` | string | yes | no | Max 255 chars if provided |
| `slabIds` | integer[] | no | **yes** | Min 1 element (D-46); each element ≥ 1 |

> `@JsonIgnoreProperties(ignoreUnknown = true)` — extra fields in the request body are silently ignored.

### BenefitCategoryResponse

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | integer | no | Auto-generated server-side |
| `orgId` | integer | no | Tenant ID from auth context |
| `programId` | integer | no | Loyalty program ID |
| `name` | string | no | Category name |
| `categoryType` | string | no | Always `"BENEFITS"` at v1 |
| `slabIds` | integer[] | no | Active slab IDs. Empty `[]` after deactivation |
| `active` | boolean | no | `true` = active; `false` = soft-deleted |
| `createdOn` | string (ISO-8601) | no | Format: `yyyy-MM-dd'T'HH:mm:ssXXX`, e.g. `"2026-04-18T10:30:45+05:30"` or `"2026-04-18T05:00:45Z"` |
| `createdBy` | integer | no | User entity ID of creator |
| `updatedOn` | string (ISO-8601) | yes | Null until first update |
| `updatedBy` | integer | yes | Null until first update |
| `stateChanged` | boolean | yes | **Only set by `/activate` endpoint.** `true` = state actually changed; `false` = no-op (already active). `null` for all other endpoints. |

> **Timestamp format (D-52)**: `yyyy-MM-dd'T'HH:mm:ssXXX` — RFC 3339, second precision, explicit timezone offset. This format is pending UI team sign-off (Q-SDET-08). If you prefer forced UTC (`...Z` always), raise it with the backend team — it is a one-annotation change.

### BenefitCategoryListPayload

Returned as `ResponseWrapper.data` on the list endpoint.

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `data` | BenefitCategoryResponse[] | no | Array of category objects for this page |
| `page` | integer | no | 0-indexed current page |
| `size` | integer | no | Requested page size |
| `total` | long | no | Total matching records (for pagination controls) |

---

## Error Codes Reference

| Error Code | HTTP Status | When Thrown |
|------------|-------------|-------------|
| `BENEFIT_CATEGORY.PROGRAM_ID_REQUIRED` | 400 | `programId` is null in Create |
| `BENEFIT_CATEGORY.PROGRAM_ID_INVALID` | 400 | `programId` < 1 in Create |
| `BENEFIT_CATEGORY.NAME_REQUIRED` | 400 | `name` is null or blank in Create |
| `BENEFIT_CATEGORY.NAME_TOO_LONG` | 400 | `name` > 255 chars in Create or Update |
| `BENEFIT_CATEGORY.SLAB_IDS_REQUIRED` | 400 | `slabIds` is null or empty in Create or Update |
| `BENEFIT_CATEGORY.SLAB_ID_INVALID` | 400 | Any slab ID in the list is < 1 |
| `BC_PAGE_SIZE_EXCEEDED` | 400 | List `?size` > 100 |
| `VALIDATION_FAILED` | **200** (platform quirk) | Invalid query param type, e.g. `?isActive=foo` |
| `BC_NOT_FOUND` | **200** (platform quirk) | Category ID not found in caller's org, or soft-deleted when `includeInactive` not set |
| `BC_NAME_TAKEN_ACTIVE` | 409 | Create/Update: active category with same name exists in same `(orgId, programId)` |
| `BC_NAME_TAKEN_ON_REACTIVATE` | 409 | Activate: a different active category now holds this name in same program |
| `BC_INACTIVE_WRITE_FORBIDDEN` | 409 | PUT on a soft-deleted category |
| `BC_UNKNOWN_SLAB` | 409 | Create/Update: one or more `slabIds` do not exist in this org |
| `BC_CROSS_PROGRAM_SLAB` | 409 | Create/Update: one or more `slabIds` belong to a different program |
| `INTERNAL_ERROR` | 500 | Unhandled server error |

> **Important**: `BC_NOT_FOUND` and `VALIDATION_FAILED` errors return HTTP **200** (not 404/400) due to a platform-wide convention in the `TargetGroupErrorAdvice`. Check the `errors[]` array even on 200 responses.

---

## Enums and Constants

| Enum / Constant | Values | Used In |
|-----------------|--------|---------|
| `categoryType` | `"BENEFITS"` | Create request, Update request, Response |
| `isActive` filter (List) | `true`, `false`, or omit | `?isActive` query param on List endpoint |
| `includeInactive` (Get Single) | `true`, `false` (default) | `?includeInactive` query param |
| Page defaults | page=0, size=20, max size=100 | List endpoint |

---

## Common Patterns

### Error Handling Pattern

```javascript
// Always check errors[] even on HTTP 200
async function callEndpoint(url, options) {
  const res = await fetch(url, options);
  const body = await res.json();
  
  if (res.status === 204) return null;  // no-op or deactivate
  
  if (body.errors && body.errors.length > 0) {
    // Handle BC_NOT_FOUND, VALIDATION_FAILED, etc. — even on HTTP 200
    throw new ApiError(body.errors[0].message, body.errors[0].code);
  }
  
  return body.data;
}
```

### Activate / Deactivate Flow

```
POST /{id}/activate
  → 200 + DTO      (was inactive, now active; stateChanged=true)
  → 204            (was already active; no-op)
  → 200 + errors   (not found, platform quirk)
  → 409            (name collision on reactivation)

POST /{id}/deactivate
  → 204            (always — both state change and no-op)
  → 200 + errors   (not found, platform quirk)
```

### Pagination

Offset-based. To page through results:
```
GET /v3/benefitCategories?programId=5&page=0&size=20   ← first page
GET /v3/benefitCategories?programId=5&page=1&size=20   ← second page
```
Use `total` in the response to calculate total pages: `Math.ceil(total / size)`.

### Slab Updates (Full Replacement)

PUT always requires the full desired slab set. To add slab `7` to a category currently associated with `[1, 3]`:
```json
{ "slabIds": [1, 3, 7] }
```
Not:
```json
{ "slabIds": [7] }
```
Sending only `[7]` would remove slabs `1` and `3`.

---

## Open Items for UI Team

| # | Item | Impact |
|---|------|--------|
| OQ-38 | **Timezone on date fields**: JVM default timezone in production not yet confirmed. Date fields are serialized with an explicit offset (e.g., `+05:30`) per the `@JsonFormat` pattern, so the UI will see the correct offset — but if production JVM is not in IST, the offset will differ. No action needed unless you see unexpected timezone shifts. |
| Q-SDET-08 | **Date format confirmation**: Current format is `yyyy-MM-dd'T'HH:mm:ssXXX` (second precision, explicit offset). If your frontend tooling requires millisecond precision or forced `Z` suffix, flag it — the backend can change `@JsonFormat` with no structural impact. |
| OQ-45 | **404 returns HTTP 200**: `BC_NOT_FOUND` (and all not-found conditions) return HTTP 200 + error envelope, not HTTP 404. This is a platform-wide convention. Your error handler must check `errors[]` on all 200 responses. |
| `stateChanged` field | Only populated on the activate endpoint. For all other endpoints it is `null`. Do not use it as an `isActive` alias. |
| `active` vs `isActive` | The JSON field name in `BenefitCategoryResponse` is `active` (not `isActive`). This matches the Lombok `@Getter` naming for `boolean active` (no `is` prefix in JSON). Verify with backend if your deserialization expects `isActive`. |

---

## Traceability

| User Story | Acceptance Criterion | Endpoint(s) | BT Cases |
|------------|---------------------|-------------|----------|
| US-1: Admin creates a benefit category | AC-BC01: category saved with name + slabs | `POST /v3/benefitCategories` | BT-001..BT-013 |
| US-2: Admin reads a benefit category | AC-BC02: category retrieved by ID | `GET /v3/benefitCategories/{id}` | BT-014..BT-019 |
| US-3: Admin updates a benefit category | AC-BC03: name and slab list updated | `PUT /v3/benefitCategories/{id}` | BT-028..BT-041 |
| US-4: Admin lists/searches categories | AC-BC04: paginated list with filters | `GET /v3/benefitCategories` | BT-020..BT-027, BT-022b |
| US-5: Admin reactivates a category | AC-BC06: soft-deleted category restored | `POST /v3/benefitCategories/{id}/activate` | BT-042..BT-050 |
| US-6: Admin deactivates a category | AC-BC05: category soft-deleted, slab mappings cascade | `POST /v3/benefitCategories/{id}/deactivate` | BT-051..BT-056 |

---

## Architectural Notes (for context only)

- **No sub-resource for slabs**: the slab junction table is not exposed as a REST endpoint. Slabs are managed entirely via the `slabIds` field on Create and Update.
- **No optimistic locking**: no `version` field in requests or responses. Concurrent writes on the same category are last-write-wins (ADR-001).
- **Deployment sequence**: DDL must be applied before the backend service starts. If the backend is not yet deployed, all endpoints return 5xx.
- **Soft-delete is permanent from PUT/DELETE**: only the dedicated `/activate` endpoint can reverse a deactivation.
