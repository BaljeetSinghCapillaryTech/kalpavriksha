# API Contract — Tiers (v3)

> **For:** UI Development Team (Garuda)
> **Version:** 3.2 — rewritten 2026-04-21 from live source under `intouch-api-v3/`
> **Base URL:** `https://{host}/v3`
> **Auth:** Bearer token in `Authorization` header
> **Content-Type:** `application/json`
> **Source phases:** `00-ba.md`, `01-architect.md`, `03-designer.md`, session-memory.md
> **Status:** Implemented and in QA. Every behavioural claim here is evidence-backed from code — file paths and line numbers are cited at the end of each section under **Evidence**.

---

## Overview

Tier Programs let loyalty administrators create, configure, and publish tier structures (e.g., "Gold", "Platinum", "Diamond") through a REST API. Each tier has:

- A **dual-backed lifecycle**: `DRAFT` / `PENDING_APPROVAL` live in MongoDB (maker-checker workflow); `ACTIVE` tiers are published to MySQL `program_slabs` via a synchronous Thrift SAGA.
- A **maker-checker approval workflow** — makers create/edit drafts, reviewers approve or reject.
- An **envelope read model** that pairs the SQL LIVE state with any Mongo-side pending edit on a per-slab basis. UI consumes envelopes, not raw documents.
- **Versioned drafts-of-active** — editing an ACTIVE tier creates a new DRAFT document (`parentId` → ACTIVE's `objectId`, `version++`), leaving the LIVE row untouched until approved.

---

## Project API Conventions

### Response Wrapper

Every response is wrapped in `ResponseWrapper<T>`:

```json
{
  "data":     { "...": "..." },
  "errors":   [ { "code": 40001, "message": "name is required" } ],
  "warnings": [ { "message": "some non-blocking note" } ]
}
```

| Field | Semantics |
|---|---|
| `data` | The resource payload (`null` on most error paths). One exception — drift 409 responses put a structured diff object in `data` too (see §5.7.1). |
| `errors` | Array of `ApiError { code: Long \| null, message: String }`. `code` is often `null` — do not pattern-match on specific numbers. |
| `warnings` | Array of `ApiWarning`. **No tier endpoint populates this today** (always `null`). |

**Error codes are typed `Long`, not strings.** Tier error codes are **not namespaced with string prefixes** — you will see either a numeric code resolved via `MessageSource`, or `null`. Pattern-match on `errors[0].message` where you need to disambiguate.

### Pagination

**Not used on any tier endpoint.** Tier list APIs return all results (bounded server-side by the 50-tier cap per program). If pagination becomes necessary, it will be an additive change on query params.

### Naming Convention

- JSON field names: `camelCase`
- URL paths: `kebab-case`, plural nouns (e.g., `/v3/tiers`)
- Enum values: `UPPER_SNAKE_CASE`

### Authentication

- **Mechanism:** Token-based, via `AbstractBaseAuthenticationToken` in Spring Security
- **Required:** Every request must include `Authorization: Bearer <token>`
- **Tenant context:** `orgId` and `userId` are extracted **server-side** from the token — **do NOT pass `orgId` as a query parameter**. Passing a different `orgId` from the client has no effect.
- **Tenant isolation:** A request can only see/modify tiers belonging to its own org. Accessing another org's tier returns **404** (not 403).
- **Reviewer identity:** on `/approve`, the reviewer's `tillName` is read from the token and stamped onto `meta.approvedBy` / `meta.rejectedBy`.

**Evidence:** `TierController.java` L56–L112; `TierReviewController.java` L41–L86.

### Content Type

- **Request:** `Content-Type: application/json`
- **Response:** `application/json` (always)
- **Malformed JSON bodies** return **HTTP 400** with body `errors[0].code = "COMMON.INVALID_INPUT"` (via `TargetGroupErrorAdvice.handleInvalidFormatException` L95–L101).

---

## Resources

### Tiers — Base path: `/v3/tiers`

| # | Method | Path | Handler |
|---|---|---|---|
| 1 | `GET`    | `/v3/tiers`                      | `TierController.listTiers` |
| 2 | `GET`    | `/v3/tiers/{tierId}`             | `TierController.getTierDetail` |
| 3 | `POST`   | `/v3/tiers`                      | `TierController.createTier` |
| 4 | `PUT`    | `/v3/tiers/{tierId}`             | `TierController.updateTier` |
| 5 | `DELETE` | `/v3/tiers/{tierId}`             | `TierController.deleteTier` |
| 6 | `POST`   | `/v3/tiers/{tierId}/submit`      | `TierReviewController.submitForApproval` |
| 7 | `POST`   | `/v3/tiers/{tierId}/approve`     | `TierReviewController.reviewTier` |
| 8 | `GET`    | `/v3/tiers/approvals`            | `TierReviewController.listPendingApprovals` |

**What does NOT exist:** no `/v3/tier-settings`, no `/v3/tier-config`, no dedicated "publish" endpoint. Publishing is a side-effect of approving (endpoint 7 with `approvalStatus = APPROVE`).

**Evidence:** `TierController.java` L43–L115; `TierReviewController.java` L25–L91.

---

## 5.1 `GET /v3/tiers` — List Tiers

**Purpose:** List all tiers for a program, returned as **envelopes** pairing SQL-LIVE state with Mongo workflow state.

**Maps to:** E1-US2 (List Tiers), AC-1.1 through AC-1.6

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `programId` | query | `int` | **Yes** | The loyalty program id |
| `status` | query | `List<TierStatus>` (CSV) | No | **See "Known behaviour" below — non-empty short-circuits to empty response.** Omit to get the normal envelope list. |

```http
GET /v3/tiers?programId=977
Authorization: Bearer <token>
```

### Response — Success (HTTP 200 OK)

Body: `ResponseWrapper<TierListResponse>`.

```json
{
  "data": {
    "summary": {
      "totalTiers": 3,
      "liveTiers": 2,
      "pendingApprovalTiers": 1,
      "totalMembers": 120345,
      "lastMemberCountRefresh": "2026-04-21T04:30:00+00:00"
    },
    "tiers": [
      {
        "slabId": 3850,
        "origin": "BOTH",
        "hasPendingDraft": false,
        "live": {
          "slabId": 3850,
          "name": "Gold",
          "description": "Premium tier",
          "color": "#FFD700",
          "serialNumber": 2,
          "tierStartDate": "2026-03-15T08:14:02+00:00",
          "eligibility": {
            "kpiType": "CURRENT_POINTS",
            "threshold": 5000,
            "upgradeType": "EAGER",
            "expressionRelation": "AND",
            "conditions": []
          },
          "validity": {
            "periodType": "MONTHS",
            "periodValue": 12,
            "startDate": "2026-03-15T00:00:00+00:00",
            "endDate": null,
            "renewal": {
              "criteriaType": "Same as eligibility",
              "expressionRelation": null,
              "conditions": null
            }
          },
          "downgrade": {
            "target": "SINGLE",
            "reevaluateOnReturn": false,
            "dailyEnabled": false,
            "conditions": []
          }
        }
      },
      {
        "slabId": 3851,
        "origin": "BOTH",
        "hasPendingDraft": true,
        "live": { "slabId": 3851, "name": "Platinum", "...": "..." },
        "pendingDraft": {
          "tierUniqueId": "ut-977-003",
          "draftStatus": "PENDING_APPROVAL",
          "name": "Platinum (revised)",
          "description": "...",
          "color": "#E5E4E2",
          "serialNumber": 3,
          "eligibility": { "...": "..." },
          "validity":    { "...": "..." },
          "downgrade":   { "...": "..." },
          "meta": {
            "createdBy": "15043871",
            "createdAt": "2026-04-20T10:15:00+00:00",
            "updatedBy": "15043871",
            "updatedAt": "2026-04-20T10:15:00+00:00"
          }
        }
      }
    ]
  },
  "errors": null,
  "warnings": null
}
```

### The Envelope Model (READ FIRST)

`tiers` is an array of `TierEnvelope`. Each envelope groups together what the user perceives as *one tier*:

```
TierEnvelope
├── slabId            (Long)       — the SQL anchor; null only in brand-new-DRAFT
├── origin            (enum)       — "BOTH" | "MONGO_ONLY" | "LEGACY_SQL_ONLY"
├── hasPendingDraft   (boolean)    — convenience flag; true iff pendingDraft != null
├── live              (TierView?)  — the SQL-sourced live state (may be absent)
└── pendingDraft      (TierView?)  — the Mongo-sourced pending edit (may be absent)
```

**Six scenarios the UI must handle:**

| # | `origin` | `live` | `pendingDraft` | `hasPendingDraft` | What it represents |
|---|---|---|---|:---:|---|
| 1 | `BOTH`            | present | absent  | false | LIVE tier, no pending edit |
| 2 | `MONGO_ONLY`      | absent  | present | true  | Brand-new DRAFT / PENDING (no SQL row yet) |
| 3 | `BOTH`            | present | present (`draftStatus=DRAFT`) | true | Edit-of-LIVE, maker editing |
| 4 | `BOTH`            | present | present (`draftStatus=PENDING_APPROVAL`) | true | Edit-of-LIVE, awaiting reviewer |
| 5 | `LEGACY_SQL_ONLY` | present | absent  | false | Legacy tier, no Mongo doc ever |
| 6 | *(not listed)*    | —       | —       | —     | `SNAPSHOT` / `DELETED` / `PUBLISH_FAILED` Mongo docs are filtered out |

Because of class-level `@JsonInclude(NON_NULL)`, **absent fields are not present on the wire.** Test `envelope.hasPendingDraft` and `envelope.live != null` — not `envelope.pendingDraft === null`.

### Response — Error Cases

| HTTP Status | When | Notes |
|---|---|---|
| `400` | `programId` not provided or non-numeric | Via global advice |
| `401` / `403` | Auth failure | Global advice |
| `500` | Unexpected | Fall-through |

### Known Behaviour — `status` query param short-circuits

`GET /v3/tiers?status=ACTIVE` (or any non-empty status list) returns an **empty envelope list with all-zero KPI summary**. This is by design: the method does not support filtering by status in its current form. **The UI should omit the `status` query param** and filter client-side if needed.

### Notes

- **Three sequential round-trips** (1 SQL + 2 Mongo) are assembled into envelopes. The list read is **non-transactional** — a writer concurrently publishing a tier can produce stale reads. A tier just published may be missing for one poll cycle; a just-deleted DRAFT may appear. UI must defensively handle "id from last list no longer exists" (a follow-up edit/approve may 404).
- **`totalMembers` can be `null`** — explicitly returned as `null` when any envelope is `LEGACY_SQL_ONLY`, because member counts live only on the Mongo side and silently returning 0 would be a lie. Render as `—` or `n/a`, not `0`.
- **`tierStartDate` is LIVE-only** — sourced exclusively from SQL `program_slabs.created_on`. Absent on `pendingDraft` (no SQL row yet); absent on `live` only if the backing emf-parent server predates Rework #3. Do NOT substitute a fallback (e.g., `new Date(0)`) when it is missing.

**Evidence:** `TierController.java` L52–L62; `TierFacade.listTiers` L131–L194 (status short-circuit at L132–L144); `TierEnvelope.java`; `TierEnvelopeBuilder.java` `build()` / `buildOne()`; `SqlTierConverter.toView`; `TierStrategyTransformer.fromStrategies` (uses `slab.isSetCreatedOn()` to distinguish unset from 0L epoch — BT-187 is the regression fence).

---

## 5.2 `GET /v3/tiers/{tierId}` — Get Tier Detail

**Purpose:** Retrieve a single tier as a `TierEnvelope`.

**Maps to:** E1-US3 (View Tier), AC-2.1 through AC-2.4

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | The Mongo `objectId` (preferred) **or** `tierUniqueId` (e.g. `"ut-977-003"`) |

```http
GET /v3/tiers/660a1b2c3d4e5f6a7b8c9d0e
Authorization: Bearer <token>
```

### Lookup rules

1. Try Mongo by `objectId`. If hit and status is `DRAFT` / `PENDING_APPROVAL` → return as `pendingDraft`. If hit and status is `ACTIVE` / `SNAPSHOT` / `DELETED` / `PUBLISH_FAILED` → look up the paired SQL LIVE row by `slabId`; if present return a LIVE-only envelope; otherwise **404**.
2. Try Mongo by `tierUniqueId`.
3. If `tierId` parses as a numeric `slabId` → **still 404** (see "Known behaviour" below).

### Response — Success (HTTP 200 OK)

Body: `ResponseWrapper<TierEnvelope>` (same envelope shape as list — one element).

```json
{
  "data": {
    "slabId": 3850,
    "origin": "BOTH",
    "hasPendingDraft": true,
    "live": {
      "slabId": 3850,
      "name": "Gold",
      "description": "Premium tier",
      "color": "#FFD700",
      "serialNumber": 2,
      "tierStartDate": "2026-03-15T08:14:02+00:00",
      "eligibility": { "kpiType": "CURRENT_POINTS", "threshold": 5000, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
      "validity":    { "periodType": "MONTHS", "periodValue": 12, "startDate": "2026-03-15T00:00:00+00:00", "endDate": null, "renewal": { "criteriaType": "Same as eligibility", "expressionRelation": null, "conditions": null } },
      "downgrade":   { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] }
    },
    "pendingDraft": {
      "tierUniqueId": "ut-977-002",
      "draftStatus": "DRAFT",
      "rejectionComment": "Threshold too aggressive — reduce to 4500",
      "name": "Gold (revised)",
      "description": "Premium tier — revised",
      "color": "#FFD700",
      "serialNumber": 2,
      "eligibility": { "kpiType": "CURRENT_POINTS", "threshold": 4500, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
      "validity":    { "periodType": "MONTHS", "periodValue": 12, "startDate": "2026-04-21T00:00:00+00:00", "endDate": null, "renewal": { "criteriaType": "Same as eligibility", "expressionRelation": null, "conditions": null } },
      "downgrade":   { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] },
      "meta": {
        "createdBy": "15043871",
        "createdAt": "2026-04-20T10:15:00+00:00",
        "updatedBy": "15043871",
        "updatedAt": "2026-04-21T08:14:02+00:00",
        "rejectedBy": "reviewer_till_01",
        "rejectedAt": "2026-04-20T14:22:00+00:00",
        "rejectionComment": "Threshold too aggressive — reduce to 4500"
      }
    }
  },
  "errors": null,
  "warnings": null
}
```

### Response — Error Cases

| HTTP Status | Error Code | When | Example Message |
|:---:|---|---|---|
| `404` | `404` | Tier not found OR belongs to different org OR `tierId` is a numeric slabId | `"Tier not found: 660a1b2c3d4e5f6a7b8c9d0e"` |
| `401` / `403` | — | Auth failure | — |
| `500` | — | Unexpected | Generic message |

**404 body** (local handler):

```json
{
  "data": null,
  "errors": [ { "code": 404, "message": "Tier not found: 660a1b2c3d4e5f6a7b8c9d0e" } ],
  "warnings": null
}
```

### Known Behaviour — Detail by numeric `slabId` returns 404

When `{tierId}` parses as a `Long`, the facade would need `programId` to resolve the SQL row via `SqlTierReader`, but the detail endpoint doesn't receive `programId`. Rather than guess, it returns 404. **To view a legacy SQL-only tier, fetch it through the list endpoint** which does receive `programId`.

### Notes

- `ConflictException → 409` is impossible on this endpoint (no conflict path).
- Unlike the review endpoints, this endpoint has a **local `@ExceptionHandler`** — 404 is a real 404 here.

**Evidence:** `TierController.java` L64–L76, L129–L135 (local NotFound handler); `TierFacade.getTierDetail` L328–L369 (numeric slabId 404 at L356–L365).

---

## 5.3 `POST /v3/tiers` — Create Tier

**Purpose:** Create a new tier in `DRAFT` status.

**Maps to:** E1-US1 (Create Tier), AC-3.1 through AC-3.9

### Request

**Headers** (optional):

| Header | Required | Description |
|---|:---:|---|
| `Idempotency-Key` | No | **Accepted but NOT honoured.** Read into a local variable, never used for dedup. Sending the same key twice creates two tiers. See Integration Notes. |

**Body — `TierCreateRequest`:**

```json
{
  "programId": 977,
  "name": "Gold",
  "description": "Premium tier",
  "color": "#FFD700",
  "eligibility": {
    "kpiType": "CURRENT_POINTS",
    "threshold": 5000,
    "upgradeType": "EAGER",
    "expressionRelation": "AND",
    "conditions": []
  },
  "validity": {
    "periodType": "MONTHS",
    "periodValue": 12,
    "startDate": "2026-04-21T00:00:00+00:00",
    "renewal": {
      "criteriaType": "Same as eligibility",
      "expressionRelation": null,
      "conditions": null
    }
  },
  "downgrade": {
    "target": "SINGLE",
    "reevaluateOnReturn": false,
    "dailyEnabled": false,
    "conditions": []
  }
}
```

### Request Field Validation

| Field | Type | Required | Validation |
|---|---|:---:|---|
| `programId` | `Integer` | **Yes** | JSR-303 `@NotNull`. |
| `name` | `String` | **Yes** | Non-blank. Max 100 chars. Must be unique within `programId` + `orgId` (across `DRAFT`, `ACTIVE`, `PENDING_APPROVAL`). |
| `description` | `String` | No | Max 500 chars. |
| `color` | `String` | No | Hex format `#RRGGBB` (regex `^#[0-9A-Fa-f]{6}$`). |
| `eligibility.kpiType` | enum | Yes (if `eligibility` sent) | One of `CURRENT_POINTS`, `LIFETIME_POINTS`, `LIFETIME_PURCHASES`, `TRACKER_VALUE`, `PURCHASE`, `VISITS`, `POINTS`, `TRACKER`. |
| `eligibility.threshold` | `Integer` | Yes (if `eligibility` sent) | `>= 0` (zero is accepted; only negatives rejected). |
| `eligibility.upgradeType` | enum | Yes (if `eligibility` sent) | One of `EAGER`, `DYNAMIC`, `LAZY`, `IMMEDIATE`, `SCHEDULED`. |
| `eligibility.expressionRelation` | enum | No | `AND` or `OR`. |
| `eligibility.conditions[]` | array | No | See §6.6 (TierCondition). |
| `validity.periodType` | `String` | No | Free-form; `"MONTHS"` is the canonical engine form. |
| `validity.periodValue` | `Integer` | No | Positive. |
| `validity.startDate` | ISO-8601 | No | Format `yyyy-MM-ddTHH:mm:ss+00:00` (see §10). |
| `validity.endDate` | — | — | **Never stored. Derived from `startDate + periodValue` at read time if needed.** Do not send. |
| `validity.renewal.criteriaType` | `String` | Yes (if `renewal` sent) | **Must be `"Same as eligibility"`.** Any other value → 400. If you omit `renewal` entirely, the server fills the default pre-save. |
| `downgrade.target` | enum | No | `SINGLE`, `THRESHOLD`, or `LOWEST`. |
| `downgrade.reevaluateOnReturn` | `boolean` | No | Default `false`. |
| `downgrade.dailyEnabled` | `boolean` | No | Default `false`. |
| `downgrade.conditions[]` | array | No | See §6.6. |

### Response — Success (HTTP 201 Created)

Body: `ResponseWrapper<UnifiedTierConfig>`. `status = DRAFT`, `version = 1`, `slabId = null`, `tierUniqueId = "ut-{programId}-{serial3d}"`.

```json
{
  "data": {
    "objectId": "660a1b2c3d4e5f6a7b8c9d0e",
    "tierUniqueId": "ut-977-002",
    "orgId": 50672,
    "programId": 977,
    "status": "DRAFT",
    "parentId": null,
    "version": 1,
    "slabId": null,
    "name": "Gold",
    "description": "Premium tier",
    "color": "#FFD700",
    "serialNumber": 2,
    "eligibility": {
      "kpiType": "CURRENT_POINTS",
      "threshold": 5000,
      "upgradeType": "EAGER",
      "expressionRelation": "AND",
      "conditions": []
    },
    "validity": {
      "periodType": "MONTHS",
      "periodValue": 12,
      "startDate": "2026-04-21T00:00:00+00:00",
      "endDate": null,
      "renewal": {
        "criteriaType": "Same as eligibility",
        "expressionRelation": null,
        "conditions": null
      }
    },
    "downgrade": {
      "target": "SINGLE",
      "reevaluateOnReturn": false,
      "dailyEnabled": false,
      "conditions": []
    },
    "memberStats": {
      "memberCount": 0,
      "lastRefreshed": null
    },
    "engineConfig": null,
    "meta": {
      "createdBy": "15043871",
      "createdAt": "2026-04-21T08:14:02+00:00",
      "updatedBy": "15043871",
      "updatedAt": "2026-04-21T08:14:02+00:00",
      "approvedBy": null,
      "approvedAt": null,
      "rejectedBy": null,
      "rejectedAt": null,
      "rejectionComment": null,
      "basisSqlSnapshot": null
    },
    "comments": null
  },
  "errors": null,
  "warnings": null
}
```

**Server-populated fields on the response (do NOT send in request):**

| Field | Source |
|---|---|
| `objectId` | Mongo-generated ObjectId (24-char hex) — primary handle for GET/PUT/DELETE/submit/approve |
| `tierUniqueId` | Server-generated, pattern `ut-{programId}-{serial3d}` (e.g. `ut-977-002`) |
| `orgId` | From auth token |
| `status` | Always `DRAFT` on create |
| `version` | Always `1` on create |
| `slabId` | Always `null` on create (populated after first APPROVE) |
| `serialNumber` | Server-assigned; immutable across edits |
| `memberStats` | Server-initialised `{ memberCount: 0, lastRefreshed: null }` |
| `meta.createdBy` / `createdAt` / `updatedBy` / `updatedAt` | Stamped from token + server clock |
| `validity.renewal` (if omitted) | Server fills the default `{ "Same as eligibility", null, null }` pre-save |

### Response — Error Cases

| HTTP Status | Error Code | When | Example Message |
|:---:|---|---|---|
| `400` | JSR-303 / `COMMON.INVALID_INPUT` | Missing `programId`, blank `name`, malformed JSON body | `"name is required"` |
| `400` | — | `TierCreateRequestValidator` rejection | See table below |
| `400` | — | Program already has 50 live tiers | `"Maximum tier limit (50) reached for this program"` |
| `409` | `409` | Name already in use for this program (across DRAFT / ACTIVE / PENDING_APPROVAL) | `"Tier name 'Gold' already exists in this program"` |
| `500` | — | Unexpected fall-through | `"Something went wrong, please try after sometime."` |

**Validator messages (exact strings from `TierCreateRequestValidator`):**

| Check | Thrown message |
|---|---|
| Body null | `"Request body is required"` |
| `programId` null | `"programId is required"` |
| `name` blank | `"name is required"` |
| `name` length > 100 | `"name must not exceed 100 characters"` |
| `description` length > 500 | `"description must not exceed 500 characters"` |
| `color` not `#RRGGBB` | `"color must be hex format #RRGGBB"` |
| `kpiType` not in allowed set | `"kpiType must be one of: [CURRENT_POINTS, LIFETIME_POINTS, LIFETIME_PURCHASES, TRACKER_VALUE, PURCHASE, VISITS, POINTS, TRACKER]"` |
| `threshold` < 0 | `"threshold must be positive"` *(zero is accepted; only negatives rejected)* |
| `upgradeType` not in allowed set | `"upgradeType must be one of: [EAGER, DYNAMIC, LAZY, IMMEDIATE, SCHEDULED]"` |

**Evidence:** `TierController.java` L78–L89; `TierCreateRequest.java`; `TierCreateRequestValidator.java` (L80–L82 for threshold-zero acceptance); `TierFacade.createTier` L226–L258; `TierValidationService.validateNameUniqueness` (409 path); `TierValidationService.assignNextSerialNumber` (50-tier cap).

---

## 5.4 `PUT /v3/tiers/{tierId}` — Update Tier

**Purpose:** Update a tier's configuration. Behaviour branches on current status.

**Maps to:** E1-US4 (Edit Tier), AC-4.1 through AC-4.7

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | Mongo `objectId` (preferred) or `tierUniqueId` |

**Body — `TierUpdateRequest`:** same shape as create, but **all fields are optional** (partial-update semantics). `programId` is NOT in the body — it cannot be changed.

```json
{
  "name": "Gold (revised)",
  "description": "Premium tier — revised copy",
  "color": "#E6B800",
  "eligibility": {
    "kpiType": "CURRENT_POINTS",
    "threshold": 4500,
    "upgradeType": "EAGER",
    "expressionRelation": "AND",
    "conditions": []
  }
}
```

### Behaviour by Current Status

| Current Status | Effect | Response |
|---|---|---|
| `DRAFT` | Update in place on the same Mongo doc. | `200 OK` with the updated doc (same `objectId`) |
| `PENDING_APPROVAL` | Update in place on the same Mongo doc. Technically allowed; UI maker seats should treat this as editing a locked draft and typically reject first. | `200 OK` with the updated doc |
| `ACTIVE` | **Creates a new versioned DRAFT** — `parentId` → ACTIVE's `objectId`, `version = parent.version + 1`, `slabId` carried over, `basisSqlSnapshot` captured from SQL for drift detection. The ACTIVE row is not modified. | `200 OK` with a NEW `objectId` (the draft) |
| `SNAPSHOT`, `DELETED`, `PUBLISH_FAILED` | Not allowed. | `409 Conflict` |

### Response — Success (HTTP 200 OK)

For an edit-of-ACTIVE, the response is the newly-created DRAFT with `parentId` pointing at the ACTIVE:

```json
{
  "data": {
    "objectId": "660a1b2c3d4e5f6a7b8c9d0f",
    "tierUniqueId": "ut-977-002",
    "orgId": 50672,
    "programId": 977,
    "status": "DRAFT",
    "parentId": "660a1b2c3d4e5f6a7b8c9d0e",
    "version": 2,
    "slabId": 3850,
    "name": "Gold (revised)",
    "description": "Premium tier — revised copy",
    "color": "#E6B800",
    "serialNumber": 2,
    "eligibility":  { "kpiType": "CURRENT_POINTS", "threshold": 4500, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
    "validity":     { "periodType": "MONTHS", "periodValue": 12, "startDate": "2026-03-15T00:00:00+00:00", "endDate": null, "renewal": { "criteriaType": "Same as eligibility", "expressionRelation": null, "conditions": null } },
    "downgrade":    { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] },
    "memberStats":  { "memberCount": 12034, "lastRefreshed": "2026-04-21T04:30:00+00:00" },
    "meta": {
      "createdBy": "15043871",
      "createdAt": "2026-04-21T09:10:00+00:00",
      "updatedBy": "15043871",
      "updatedAt": "2026-04-21T09:10:00+00:00",
      "basisSqlSnapshot": { "...": "<frozen SQL row at draft creation — server-internal, do not render>" }
    },
    "comments": null
  },
  "errors": null,
  "warnings": null
}
```

### Response — Error Cases

| HTTP Status | Error Code | When | Example Message |
|:---:|---|---|---|
| `400` | — | Validator failure — blank name, name > 100, description > 500, invalid color, invalid `kpiType` / `upgradeType`, `threshold < 0` | See validator table in §5.3 |
| `404` | `404` | Tier not found OR belongs to different org | `"Tier not found: {tierId}"` |
| `409` | `409` | Status is `SNAPSHOT`, `DELETED`, or `PUBLISH_FAILED` | `"Cannot edit a tier in SNAPSHOT status"` |
| `409` | `409` | Renaming collides with another tier in the same program | `"Tier name '<name>' already exists in this program"` |
| `401` / `403` | — | Auth | — |
| `500` | — | Unexpected | — |

### Notes

- **ACTIVE remains live during the edit.** The new DRAFT lives alongside the ACTIVE until it is submitted → approved. Only after APPROVE does the old ACTIVE become `SNAPSHOT` and the DRAFT become `ACTIVE`.
- **If a DRAFT already exists** for an ACTIVE subscription (a previous edit that wasn't yet approved), the existing DRAFT is **updated in place** — no new document is created.
- **`basisSqlSnapshot`** on the returned doc's `meta` is server-internal. It's the frozen SQL row at draft-creation time, used by `TierDriftChecker` at approval time. UI must not render it or diff against it.

**Evidence:** `TierController.java` L92–L103; `TierFacade.updateTier` L260–L282 (state switch at L270–L281); `TierDriftChecker`.

---

## 5.5 `DELETE /v3/tiers/{tierId}` — Delete Tier

**Purpose:** Soft-delete a DRAFT tier. Sets `status = DELETED` and stamps audit; the document is retained.

**Maps to:** E1-US5 (Delete Tier), AC-5.1, AC-5.2

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | Mongo `objectId` or `tierUniqueId` |

```http
DELETE /v3/tiers/660a1b2c3d4e5f6a7b8c9d0e
Authorization: Bearer <token>
```

### Response — Success (HTTP 204 No Content)

```json
{
  "data": null,
  "errors": null,
  "warnings": null
}
```

### Response — Error Cases

| HTTP Status | Error Code | When | Example Message |
|:---:|---|---|---|
| `404` | `404` | Tier not found | `"Tier not found: {tierId}"` |
| `409` | `409` | Status is not `DRAFT` | `"Only DRAFT tiers can be deleted. Tier 'Gold' is in ACTIVE status."` |

### Notes

- **Both original drafts** (`parentId = null`) **and versioned drafts-of-ACTIVE** (`parentId = <active's objectId>`) can be deleted.
- **Deleting a versioned draft discards the pending edit** — the ACTIVE version is unaffected.
- Soft-delete only. The document remains in Mongo with `status = DELETED` for audit. There is no hard-delete endpoint.

**Evidence:** `TierController.java` L105–L115; `TierFacade.deleteTier` L292–L309 (conflict check L299–L302).

---

## Tier Lifecycle — Review Endpoints

### 5.6 `POST /v3/tiers/{tierId}/submit` — Submit for Approval

**Purpose:** Transition a `DRAFT` tier to `PENDING_APPROVAL`.

**Maps to:** E2-US1 (Submit for Approval), AC-6.1, AC-6.2

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | Mongo `objectId` |

**Body:** none.

```http
POST /v3/tiers/660a1b2c3d4e5f6a7b8c9d0e/submit
Authorization: Bearer <token>
```

### Response — Success (HTTP 200 OK)

Body: `ResponseWrapper<UnifiedTierConfig>` — the transitioned document with `status = PENDING_APPROVAL`.

```json
{
  "data": {
    "objectId": "660a1b2c3d4e5f6a7b8c9d0e",
    "tierUniqueId": "ut-977-002",
    "orgId": 50672,
    "programId": 977,
    "status": "PENDING_APPROVAL",
    "parentId": null,
    "version": 1,
    "slabId": null,
    "name": "Gold",
    "description": "Premium tier",
    "color": "#FFD700",
    "serialNumber": 2,
    "eligibility": { "...": "..." },
    "validity":    { "...": "..." },
    "downgrade":   { "...": "..." },
    "meta": {
      "createdBy": "15043871",
      "createdAt": "2026-04-21T08:14:02+00:00",
      "updatedBy": "15043871",
      "updatedAt": "2026-04-21T09:20:00+00:00"
    },
    "comments": null
  },
  "errors": null,
  "warnings": null
}
```

### Response — Error Cases

| HTTP Status | When | Example Body |
|:---:|---|---|
| **`200`** *(yes, 200)* | **Tier not found — BUG. See Integration Note below.** The global advice returns HTTP 200 with an error object in `errors[0]` and `data = null`. | `{ "data": null, "errors": [{ "code": ..., "message": "Tier not found: {tierId}" }], "warnings": null }` |
| `409` | Tier is not in `DRAFT` status | `"Only DRAFT tiers can be submitted for approval. Tier is in ACTIVE status."` |
| `500` | Unexpected fall-through | — |

> ⚠️ **Integration Note — `NotFoundException` returns HTTP 200 on review endpoints.** `TierReviewController` has **no local `@ExceptionHandler`**, so it falls through to the global `TargetGroupErrorAdvice.handleNotFoundException` which returns HTTP 200 with the error on `errors[0]`. **UI MUST check `errors` even on HTTP 200** for `/submit` and `/approve`. `TierController` overrides this locally — GET/PUT/DELETE return proper 404s.

### Notes

- The `DRAFT → PENDING_APPROVAL` transition is **guarded at the Mongo query level** by `TierRepository.transitionDraftToPendingApproval` (atomic update with `WHERE status = DRAFT`). Concurrent submits lose cleanly — only one write succeeds.

**Evidence:** `TierReviewController.java` L38–L49; `TierFacade.submitForApproval` L389–L400; `TierRepository.transitionDraftToPendingApproval` L52–L54; `TargetGroupErrorAdvice.handleNotFoundException` L74–L77.

---

### 5.7 `POST /v3/tiers/{tierId}/approve` — Reviewer Decision

**Purpose:** Approve or reject a `PENDING_APPROVAL` tier. On APPROVE, runs the SAGA — drift check + name re-uniqueness → Thrift publish (`createSlabAndUpdateStrategies` with SLAB_UPGRADE + SLAB_DOWNGRADE strategies) → SQL write → status `ACTIVE`, stamp `slabId`.

**Maps to:** E2-US2 / E2-US3 (Approve / Reject), AC-7.1 through AC-8.3

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | Mongo `objectId` |

**Body — `Map<String, String>`:**

```json
{
  "approvalStatus": "APPROVE",
  "comment": "Reviewed and approved for Q2 launch"
}
```

| Field | Type | Required | Validation |
|---|---|:---:|---|
| `approvalStatus` | `String` | **Yes** | `"APPROVE"` or `"REJECT"` (case-insensitive). **Any other value → HTTP 500.** Validate on the client. |
| `comment` | `String` | No | Reviewer's note. Stamped onto `meta.rejectionComment` on REJECT. |

### Response — Success (HTTP 200 OK)

**On APPROVE** — tier transitions to `ACTIVE` with `slabId` populated. If this was an edit-of-ACTIVE (had `parentId`), the old ACTIVE row transitions to `SNAPSHOT`:

```json
{
  "data": {
    "objectId": "660a1b2c3d4e5f6a7b8c9d0e",
    "tierUniqueId": "ut-977-002",
    "orgId": 50672,
    "programId": 977,
    "status": "ACTIVE",
    "parentId": null,
    "version": 1,
    "slabId": 3850,
    "name": "Gold",
    "description": "Premium tier",
    "color": "#FFD700",
    "serialNumber": 2,
    "eligibility": { "...": "..." },
    "validity":    { "...": "..." },
    "downgrade":   { "...": "..." },
    "meta": {
      "createdBy": "15043871",
      "createdAt": "2026-04-21T08:14:02+00:00",
      "updatedBy": "reviewer_till_01",
      "updatedAt": "2026-04-21T09:30:00+00:00",
      "approvedBy": "reviewer_till_01",
      "approvedAt": "2026-04-21T09:30:00+00:00"
    },
    "comments": "Reviewed and approved for Q2 launch"
  },
  "errors": null,
  "warnings": null
}
```

**On REJECT** — tier transitions back to `DRAFT`; `rejectedBy`, `rejectedAt`, `rejectionComment` are stamped:

```json
{
  "data": {
    "objectId": "660a1b2c3d4e5f6a7b8c9d0e",
    "status": "DRAFT",
    "meta": {
      "updatedBy": "reviewer_till_01",
      "updatedAt": "2026-04-21T09:30:00+00:00",
      "rejectedBy": "reviewer_till_01",
      "rejectedAt": "2026-04-21T09:30:00+00:00",
      "rejectionComment": "Threshold too aggressive — reduce to 4500"
    },
    "comments": "Threshold too aggressive — reduce to 4500"
  },
  "errors": null,
  "warnings": null
}
```

### Response — Error Cases

| HTTP Status | When | Notes |
|:---:|---|---|
| **`200`** | Tier not found | Same NotFoundException quirk as §5.6. UI must check `errors` on 200. |
| `409` | Tier not in `PENDING_APPROVAL` | `"Only PENDING_APPROVAL tiers can be approved/rejected. Tier is in DRAFT status."` |
| `409` | **`APPROVAL_BLOCKED_DRIFT`** — SQL LIVE row drifted since draft's basis snapshot | Structured body — see §5.7.1 |
| `500` | `approvalStatus` is neither `APPROVE` nor `REJECT` | `IllegalArgumentException` → generic `"Something went wrong..."`. **Validate on the client.** |
| `500` | SAGA publish failure (Thrift RPC error) | Tier is transitioned to `PUBLISH_FAILED` and best-effort saved before the exception propagates. |

### 5.7.1 Drift Error Body (APPROVE only)

When `TierApprovalHandler.preApprove` detects that the LIVE SQL row has been modified since the draft's `basisSqlSnapshot` was captured, it throws `TierApprovalDriftException`. A dedicated `TierErrorAdvice` maps this to **HTTP 409** with a structured body — **note the diffs go into `data`, not `errors`**:

```json
{
  "data": {
    "code": "APPROVAL_BLOCKED_DRIFT",
    "diffs": [
      {
        "fieldPath": "eligibility.threshold",
        "basisValue": 5000,
        "currentValue": 5500
      },
      {
        "fieldPath": "validity.periodValue",
        "basisValue": 12,
        "currentValue": 6
      }
    ]
  },
  "errors": [
    { "code": null, "message": "Approval blocked: SQL LIVE state has drifted from the basis snapshot" }
  ],
  "warnings": null
}
```

**Special `fieldPath` marker** — `"row"` indicates row-level drift where field-wise diff is unavailable (e.g., SQL row deleted/recreated):

```json
{ "fieldPath": "row", "basisValue": null, "currentValue": null }
```

**UI should key off `data.code === "APPROVAL_BLOCKED_DRIFT"` and render `data.diffs`** — do not parse the message.

### Notes

- **On approving an edit-of-ACTIVE** (draft had `parentId`):
  - The old ACTIVE's status is set to `SNAPSHOT` (preserved for audit history — filtered out of envelope listings)
  - The DRAFT becomes the new ACTIVE
  - Thrift publish is called with the updated strategies
  - The response returns the newly-ACTIVE document with `parentId: null`
- **SAGA failure** transitions the tier to `PUBLISH_FAILED` (best-effort save) before HTTP 500 is returned. See Integration Notes.
- **`approvalStatus` is case-insensitive** — `"approve"` and `"APPROVE"` both work.

**Evidence:** `TierReviewController.java` L51–L74; `TierFacade.handleApproval` L412–L432 (action switch L423–L431, IllegalArgumentException at L430); `TierApprovalHandler.preApprove` / `postApprove`; `TierApprovalDriftException.java` (constant `CODE = "APPROVAL_BLOCKED_DRIFT"`); `TierErrorAdvice.java`; `FieldDiff.java`; `MakerCheckerService.approve` L58–L79 (catch block L64–L76 for SAGA failure).

---

### 5.8 `GET /v3/tiers/approvals` — Reviewer Queue

**Purpose:** List all tiers pending approval for the reviewer's org + program.

**Maps to:** E2-US4 (Pending Approvals Queue), AC-9.1, AC-9.2

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `programId` | query | `int` | **Yes** | The loyalty program id |

```http
GET /v3/tiers/approvals?programId=977
Authorization: Bearer <token>
```

### Response — Success (HTTP 200 OK)

Body: `ResponseWrapper<List<UnifiedTierConfig>>` — raw `UnifiedTierConfig` documents (**not envelopes** — this is the reviewer's raw queue).

```json
{
  "data": [
    {
      "objectId": "660a1b2c3d4e5f6a7b8c9d0e",
      "tierUniqueId": "ut-977-002",
      "orgId": 50672,
      "programId": 977,
      "status": "PENDING_APPROVAL",
      "parentId": null,
      "version": 1,
      "slabId": null,
      "name": "Gold",
      "description": "Premium tier",
      "color": "#FFD700",
      "serialNumber": 2,
      "eligibility": { "...": "..." },
      "validity":    { "...": "..." },
      "downgrade":   { "...": "..." },
      "meta": {
        "createdBy": "15043871",
        "createdAt": "2026-04-21T08:14:02+00:00",
        "updatedBy": "15043871",
        "updatedAt": "2026-04-21T09:20:00+00:00"
      }
    },
    {
      "objectId": "660a1b2c3d4e5f6a7b8c9d0f",
      "tierUniqueId": "ut-977-003",
      "status": "PENDING_APPROVAL",
      "parentId": "660a1b2c3d4e5f6a7b8c9d0a",
      "version": 2,
      "slabId": 3851,
      "name": "Platinum (revised)",
      "...": "..."
    }
  ],
  "errors": null,
  "warnings": null
}
```

### Response — Error Cases

| HTTP Status | When |
|:---:|---|
| `400` | `programId` missing or non-numeric |
| `401` / `403` | Auth |
| `500` | Unexpected |

### Notes

- Returns both **new tiers** (`parentId: null`) and **edits of active** (`parentId` → `objectId` of the ACTIVE being edited).
- UI can check `parentId` to distinguish: `null` → new tier pending first publish; non-null → edit pending re-publish.
- Response is **raw `UnifiedTierConfig`**, not envelopes — reviewer sees the proposed state directly. To see the current ACTIVE state for comparison, make a separate `GET /v3/tiers/{parentId}` call.
- Authorization for who can approve is **not enforced by the backend** — the UI layer handles reviewer roles.

**Evidence:** `TierReviewController.java` L81–L90; `TierFacade.listPendingApprovals` L437–L440.

---

## 6. Data Model

All types below live under `com.capillary.intouchapiv3.tier`.

### 6.0 Date & Timezone Contract (READ FIRST)

Every `Date` field on the wire is serialised as ISO-8601 with an **explicit `+00:00` offset**:

```
yyyy-MM-ddTHH:mm:ss+00:00
```

**Example:** `"createdAt": "2026-04-21T08:14:02+00:00"`

Implementation: all 7 tier `Date` fields use `@JsonSerialize(using = TierDateFormat.Serializer.class)`. The serializer uses `DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssxxx")` (lowercase `xxx` — renders `+00:00` literally for UTC; uppercase `XXX` would collapse to the `Z` shorthand, which this API does **not** emit).

**`Z` must NOT appear in any tier payload.** If you see it, it's a backend misconfiguration — file a ticket.

**Fields covered:** `TierView.tierStartDate`, `TierMeta.{createdAt, updatedAt, approvedAt, rejectedAt}`, `MemberStats.lastRefreshed`, `KpiSummary.lastMemberCountRefresh`. All uniform as of 2026-04-21.

**Evidence:** `TierDateFormat.java` (utility + serializer); `TierView.java` L63, `TierMeta.java` L27/L32/L37/L42, `MemberStats.java` L14, `KpiSummary.java` L27.

---

### 6.1 `UnifiedTierConfig` — Mongo document (create/update/approve response)

```json
{
  "objectId":       "660a1b2c3d4e5f6a7b8c9d0e",
  "tierUniqueId":   "ut-977-002",
  "orgId":          50672,
  "programId":      977,
  "status":         "DRAFT",
  "parentId":       null,
  "version":        1,
  "slabId":         null,
  "name":           "Gold",
  "description":    "Premium tier",
  "color":          "#FFD700",
  "serialNumber":   2,
  "eligibility":    { "...": "<TierEligibilityConfig — §6.4>" },
  "validity":       { "...": "<TierValidityConfig — §6.5>" },
  "downgrade":      { "...": "<TierDowngradeConfig — §6.7>" },
  "memberStats":    { "...": "<MemberStats — §6.9>" },
  "engineConfig":   null,
  "meta":           { "...": "<TierMeta — §6.3>" },
  "comments":       null
}
```

| Field | Type | Notes |
|---|---|---|
| `objectId` | `String` | Mongo `@Id` — the primary handle. Immutable. |
| `tierUniqueId` | `String` | Pattern `ut-{programId}-{serial3d}`, e.g. `ut-977-002`. Human-readable stable id. |
| `orgId` | `Long` | Tenant — server-populated from auth. |
| `programId` | `Integer` | Program scope. Immutable after create. |
| `status` | `TierStatus` | See §6.2. |
| `parentId` | `String?` | On versioned-drafts-of-ACTIVE, points at the ACTIVE's `objectId`. `null` on originals. |
| `version` | `Long` | Starts at 1; versioned-draft = `parent.version + 1`. |
| `slabId` | `Long?` | SQL linkage. `null` until first APPROVE publishes to `program_slabs`. |
| `name` | `String` | Max 100, `@NotBlank`. |
| `description` | `String?` | Max 500. |
| `color` | `String?` | Hex `#RRGGBB`. |
| `serialNumber` | `Integer` | Server-assigned on create, immutable. |
| `eligibility` | `TierEligibilityConfig` | See §6.4. |
| `validity` | `TierValidityConfig` | See §6.5. |
| `downgrade` | `TierDowngradeConfig` | See §6.7. |
| `memberStats` | `MemberStats` | `{ memberCount, lastRefreshed }`. |
| `engineConfig` | — | **Engine-internal.** UI must treat as opaque. Absent on `TierView`. |
| `meta` | `TierMeta` | Audit block — §6.3. |
| `comments` | `String?` | Reviewer comment trail (most recent). |

---

### 6.2 `TierStatus` (enum)

```
DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT, PUBLISH_FAILED
```

| Value | Meaning |
|---|---|
| `DRAFT` | Maker editing. Mutable via PUT. Can be submitted or deleted. |
| `PENDING_APPROVAL` | Awaiting reviewer. Mutable via PUT (edit-in-place) but UI maker seat should treat as locked. |
| `ACTIVE` | Published to SQL `program_slabs`. PUT creates a versioned-draft — ACTIVE row is not touched. |
| `DELETED` | Soft-deleted (DRAFT only). History retained. |
| `SNAPSHOT` | Historical copy left when a versioned-draft was approved. Never surfaces in envelopes. |
| `PUBLISH_FAILED` | SAGA failure state. Best-effort saved when Thrift publish fails. Not surfaced in envelope listings (filtered — see §5.1 envelope scenario 6). Recovery flow deferred to a later epic. |

---

### 6.3 `TierMeta` — Audit Block

```json
{
  "createdBy":         "15043871",
  "createdAt":         "2026-04-21T08:14:02+00:00",
  "updatedBy":         "15043871",
  "updatedAt":         "2026-04-21T09:20:00+00:00",
  "approvedBy":        "reviewer_till_01",
  "approvedAt":        "2026-04-21T09:30:00+00:00",
  "rejectedBy":        null,
  "rejectedAt":        null,
  "rejectionComment":  null,
  "basisSqlSnapshot":  null
}
```

| Field | Type | Notes |
|---|---|---|
| `createdBy` / `updatedBy` | `String` | User id stamped from auth token (`IntouchUser.getEntityId()` as string). |
| `createdAt` / `updatedAt` | ISO-8601 | See §6.0. |
| `approvedBy` / `approvedAt` | `String` / ISO-8601 | Reviewer's `tillName` + approve timestamp. `null` until first approve. |
| `rejectedBy` / `rejectedAt` | `String` / ISO-8601 | Reviewer's `tillName` + reject timestamp. `null` unless last reviewer action was REJECT. |
| `rejectionComment` | `String?` | Mirror of the reviewer's `comment` on last REJECT. |
| `basisSqlSnapshot` | `SqlTierRow?` | **Server-internal** — frozen SQL row captured when a versioned-draft-of-ACTIVE was created. Used by `TierDriftChecker` at approval time. UI must not render or diff against it. |

---

### 6.4 `TierEligibilityConfig`

```json
{
  "kpiType":            "CURRENT_POINTS",
  "threshold":          5000,
  "upgradeType":        "EAGER",
  "expressionRelation": "AND",
  "conditions":         []
}
```

| Field | Type | Allowed Values |
|---|---|---|
| `kpiType` | enum | `CURRENT_POINTS`, `LIFETIME_POINTS`, `LIFETIME_PURCHASES`, `TRACKER_VALUE`, `PURCHASE`, `VISITS`, `POINTS`, `TRACKER` |
| `threshold` | `Integer` | ≥ 0 (zero accepted; negatives rejected) |
| `upgradeType` | enum | `EAGER`, `DYNAMIC`, `LAZY`, `IMMEDIATE`, `SCHEDULED` |
| `expressionRelation` | enum | `AND`, `OR` |
| `conditions` | `TierCondition[]` | See §6.8 |

---

### 6.5 `TierValidityConfig`

```json
{
  "periodType":  "MONTHS",
  "periodValue": 12,
  "startDate":   "2026-04-21T00:00:00+00:00",
  "endDate":     null,
  "renewal":     {
    "criteriaType":       "Same as eligibility",
    "expressionRelation": null,
    "conditions":         null
  }
}
```

**Key rules:**
- `endDate` is **always `null` on responses**. It is derived as `startDate + periodValue` if the UI needs it.
- `renewal` is **never null on the wire** — if the client omits it on write, the server fills the default before persistence. On read, the SQL-sourced LIVE view and the Mongo DRAFT view surface identical renewal objects (keeps the drift-checker free of phantom false-positives).

---

### 6.6 `TierRenewalConfig` (inside `TierValidityConfig.renewal`)

```json
{
  "criteriaType":       "Same as eligibility",
  "expressionRelation": null,
  "conditions":         null
}
```

**Accept-only contract (as of 2026-04-21):**
- The server accepts **only** `criteriaType = "Same as eligibility"` on write.
- Any other value (including `"Active subscription"`, `"Custom"`, or any unrecognised string) → **HTTP 400** with the validator message listing allowed values.
- `expressionRelation` and `conditions` are reserved for future contracts and must be `null` today.
- Clients that omit `renewal` entirely are accepted — server fills the default pre-save.

**Why this restriction?** The engine has no storage slot for an explicit renewal rule. The tier engine implicitly fires renewal on every slab upgrade; locking the API to the one shape the engine semantically supports keeps the contract honest. Support for `"Custom"` renewal is an additive change that won't break clients on this contract.

**Dropped from v3.1:** `schedule` field (previously a free-text display string; the engine stripped it on write so it never reached SQL).

---

### 6.7 `TierDowngradeConfig`

```json
{
  "target":             "SINGLE",
  "reevaluateOnReturn": false,
  "dailyEnabled":       false,
  "conditions":         []
}
```

| Field | Type | Allowed Values |
|---|---|---|
| `target` | enum | `SINGLE`, `THRESHOLD`, `LOWEST` |
| `reevaluateOnReturn` | `boolean` | Default `false` |
| `dailyEnabled` | `boolean` | Default `false` |
| `conditions` | `TierCondition[]` | See §6.8 |

---

### 6.8 `TierCondition`

```json
{
  "type":        "PURCHASE",
  "value":       1000,
  "trackerName": null
}
```

| Field | Type | Notes |
|---|---|---|
| `type` | enum | `PURCHASE`, `VISITS`, `POINTS`, `TRACKER` |
| `value` | `Integer \| String` | Numeric threshold. Legacy engine writes may surface as string; the reader is defensive. |
| `trackerName` | `String?` | Only populated when `type = TRACKER`. |

---

### 6.9 `MemberStats`

```json
{
  "memberCount":   12034,
  "lastRefreshed": "2026-04-21T04:30:00+00:00"
}
```

| Field | Type | Notes |
|---|---|---|
| `memberCount` | `Integer` | Current enrolled member count. Initialised to 0 on create. |
| `lastRefreshed` | ISO-8601 | Last member-count refresh timestamp. Null until first refresh. |

---

### 6.10 `KpiSummary` (on list response)

```json
{
  "totalTiers":             4,
  "liveTiers":              3,
  "pendingApprovalTiers":   1,
  "totalMembers":           120345,
  "lastMemberCountRefresh": "2026-04-21T04:30:00+00:00"
}
```

| Field | Type | Notes |
|---|---|---|
| `totalTiers` | `Integer` | Count of envelopes in the response |
| `liveTiers` | `Integer` | Count of envelopes with a LIVE (SQL) side. Renamed from `activeTiers` in Rework #5. |
| `pendingApprovalTiers` | `Integer` | Count of envelopes with a `pendingDraft` whose `draftStatus = PENDING_APPROVAL` |
| `totalMembers` | `Integer?` | Sum of member counts across envelopes. **`null` when any envelope is `LEGACY_SQL_ONLY`** — member counts live on Mongo only; silently returning 0 would be a lie. Render `null` as `—` / `n/a`, not `0`. |
| `lastMemberCountRefresh` | ISO-8601? | Most recent `lastRefreshed` across all envelopes. |

---

### 6.11 `TierEnvelope` + `TierView` — the read shape

See §5.1 for the envelope model and the six scenarios. `TierView` is the flattened per-side payload inside `live` / `pendingDraft`. Class-level `@JsonInclude(NON_NULL)` on both.

**`TierView` differs from `UnifiedTierConfig` in these ways:**

| Field | On LIVE side | On pendingDraft side | Notes |
|---|:---:|:---:|---|
| `slabId` | present | absent | Also sits on the envelope itself |
| `tierUniqueId` | absent | present | Mongo-side stable id |
| `draftStatus` | absent | `DRAFT` or `PENDING_APPROVAL` | Only these two values surface here |
| `rejectionComment` | absent | present if last review was REJECT | |
| `name`, `description`, `color`, `serialNumber` | present | present | Shared fields |
| `tierStartDate` | present (backend ≥ R3) | absent | **LIVE-only**, sourced from SQL `program_slabs.created_on` |
| `eligibility`, `validity`, `downgrade` | present | present | |
| `meta` | present | present | `TierMeta` — audit |
| `engineConfig` | **absent** | **absent** | Engine internals are not exposed on reads |

---

## 7. Enums and Constants

| Enum | Values | Notes |
|---|---|---|
| `TierStatus` | `DRAFT`, `PENDING_APPROVAL`, `ACTIVE`, `DELETED`, `SNAPSHOT`, `PUBLISH_FAILED` | `SNAPSHOT` is internal — filtered from envelopes. `PUBLISH_FAILED` is a SAGA failure state. |
| `ApprovalAction` | `APPROVE`, `REJECT` | Used in `approvalStatus` body field on `/approve`. Case-insensitive. |
| `KpiType` | `CURRENT_POINTS`, `LIFETIME_POINTS`, `LIFETIME_PURCHASES`, `TRACKER_VALUE`, `PURCHASE`, `VISITS`, `POINTS`, `TRACKER` | `eligibility.kpiType` |
| `UpgradeType` | `EAGER`, `DYNAMIC`, `LAZY`, `IMMEDIATE`, `SCHEDULED` | `eligibility.upgradeType` |
| `ExpressionRelation` | `AND`, `OR` | `eligibility.expressionRelation` |
| `DowngradeTarget` | `SINGLE`, `THRESHOLD`, `LOWEST` | `downgrade.target` |
| `ConditionType` | `PURCHASE`, `VISITS`, `POINTS`, `TRACKER` | `TierCondition.type` |
| `TierOrigin` | `BOTH`, `MONGO_ONLY`, `LEGACY_SQL_ONLY` | `TierEnvelope.origin` |

---

## 8. Status Display Guide for UI

| Status | User-Facing Label | Colour Suggestion | Editable? | Deletable? | Notes |
|---|---|---|---|---|---|
| `DRAFT` | Draft | Gray | Yes (in-place) | Yes | Can submit for approval. May carry `rejectionComment` if a reviewer previously rejected it. |
| `PENDING_APPROVAL` | Pending Approval | Yellow / Amber | Technically yes (in-place) — UI should treat as locked | No | Can approve or reject |
| `ACTIVE` | Active | Green | Yes (creates versioned draft) | No | Live in SQL. Members enrolled. |
| `DELETED` | Deleted | Dark Gray | No | No | Soft-deleted; retained for audit. **Do not surface in UI lists.** |
| `SNAPSHOT` | (hidden) | — | No | No | Internal maker-checker history. **Do not display.** |
| `PUBLISH_FAILED` | (hidden today) | — | No | No | SAGA failure. Filtered from envelope listings. Recovery flow deferred. |

---

## 9. Status Lifecycle

```
              POST /v3/tiers
                   │
                   ▼
               ┌───────┐    PUT /v3/tiers/{id}    ┌──────────────┐
    delete ◄── │ DRAFT │◄───── (in-place) ────────│    DRAFT     │
    (soft)     └───┬───┘                          └──────────────┘
                   │
                   │ POST /v3/tiers/{id}/submit
                   ▼
          ┌─────────────────┐
          │ PENDING_APPROVAL│
          └────┬────────┬───┘
               │        │
        APPROVE│        │REJECT
         (SAGA)│        │
               ▼        ▼
          ┌────────┐ ┌───────┐
          │ ACTIVE │ │ DRAFT │  (meta.rejectionComment stamped)
          └────┬───┘ └───────┘
               │
 PUT           │  (versioned draft — parentId → ACTIVE, version++)
               │
               ▼
       ┌─────────────┐        approve      ┌──────────┐
       │ DRAFT v2+   │────── (SAGA) ──────▶│ ACTIVE v2│
       └─────────────┘                     └────┬─────┘
                                                │
                                                │ parent becomes…
                                                ▼
                                           ┌──────────┐
                                           │ SNAPSHOT │ (filtered from envelopes)
                                           └──────────┘

  SAGA publish failure on APPROVE:  ACTIVE-attempt ──▶ PUBLISH_FAILED
```

**Terminal statuses** for UI purposes: `DELETED`, `SNAPSHOT`. `PUBLISH_FAILED` is recoverable via a future retry path (not in v3.2).

**Evidence:** `TierFacade.updateTier` L270–L281 (state switch); `TierFacade.deleteTier` L292–L309 (conflict guard L299–L302); `TierFacade.submitForApproval` L389–L400; `MakerCheckerService.approve` L58–L79 (catch L64–L76); `TierApprovalHandler.postApprove` (parent → SNAPSHOT).

---

## 10. Integration Notes

Read every item — these are real behaviours the UI must handle.

### 10.1 `NotFoundException → HTTP 200` on review endpoints

`TargetGroupErrorAdvice.handleNotFoundException` (L74–L77) returns `HTTP 200` with the error on `errors[0]`. `TierController` overrides this locally → proper 404s for GET/PUT/DELETE. **`TierReviewController` does NOT override** → `/submit` and `/approve` return HTTP 200 with an `errors` payload when the `tierId` is wrong.

**UI MUST check `errors` on 200 for `/submit` and `/approve`.** Treat:
```json
{ "data": null, "errors": [ { "message": "Tier not found: ..." } ], "warnings": null }
```
as a not-found condition even on 200.

### 10.2 `GET /v3/tiers?status=…` returns an empty list

If `status` (non-empty list) is sent on list, the method short-circuits to `{ summary: all-zero, tiers: [] }`. **Omit the `status` query param** on `GET /v3/tiers`. Filter client-side on the envelope if needed.

### 10.3 `totalMembers` can be `null`

Explicitly `null` when any envelope in the result is `LEGACY_SQL_ONLY`, because member counts are Mongo-only. Render as `—` / `n/a`, not `0`.

### 10.4 `PUBLISH_FAILED` is a real status

If the Thrift publish during APPROVE fails, the tier is best-effort saved with `status = PUBLISH_FAILED` before the exception propagates (HTTP 500 with the generic message). **`PUBLISH_FAILED` tiers do not appear in list responses** — envelopes filter them out. They may be fetched by detail if a paired SQL row exists, otherwise are invisible. Recovery flow deferred.

### 10.5 Detail by numeric `slabId` returns 404

`GET /v3/tiers/{tierId}` with a purely numeric id returns 404 — the detail endpoint doesn't receive `programId`, which is required to resolve a legacy SQL-only tier by `slabId`. **To detail a legacy tier, fetch it through the list endpoint.**

### 10.6 Unknown `approvalStatus` is a 500, not a 400

`TierFacade.handleApproval` accepts only `"APPROVE"` / `"REJECT"` (case-insensitive). Any other value raises `IllegalArgumentException` — unmapped by the global advice, falls through to `genericExceptionHandler` → HTTP 500 with the generic `"Something went wrong..."` message. **Validate on the client before calling.**

### 10.7 Concurrency / race windows on list

`listTiers` runs three non-transactional round-trips (1 SQL + 2 Mongo). Observable races:
- A tier just published may be missing for one poll cycle.
- A newly-created DRAFT always appears (safe).
- A just-deleted DRAFT may appear; a subsequent edit/approve call on it will 404 (or 200 with errors on `/submit`-`/approve`). **UI must defensively handle "id from last list no longer exists".**

### 10.8 `rejectionComment` on a DRAFT envelope's `pendingDraft`

When a reviewer rejects, the tier transitions back to `DRAFT` and `meta.rejectionComment` is stamped. The next list poll surfaces the doc as `pendingDraft` with `draftStatus = DRAFT` and `rejectionComment` populated. **This is intentional** — the maker seat renders the rejection reason next to the editable draft.

### 10.9 `engineConfig` is on `UnifiedTierConfig` but NOT on `TierView`

`TierView` deliberately omits `engineConfig`. The list and detail endpoints (which return envelopes of `TierView`) never expose engine internals. **If you see `engineConfig` on a payload, you are looking at a create/update/approve response** (which returns `UnifiedTierConfig`), not a read response.

### 10.10 `basisSqlSnapshot` is server-internal

Exposed on `TierMeta` for debuggability but carries no UI meaning. It is a frozen SQL row used by `TierDriftChecker` at approval time. **Do not render it, do not diff against it from the client.**

### 10.11 `Idempotency-Key` header is reserved, not implemented

`POST /v3/tiers` accepts the header and silently drops it. **Do not rely on it for safe retry.** Use the 409-on-duplicate-name check as your retry guard.

### 10.12 Validator codes 9001–9010 are dead

Declared as `public static final int` constants in `TierCreateRequestValidator` but never passed to any `throw`. `errors[0].code` will be `null` or a `MessageSource`-resolved number — **never 9001–9010**. Pattern-match on `errors[0].message`, not on numeric codes.

### 10.13 APPROVE triggers a synchronous Thrift SAGA

APPROVE is not a pure Mongo status change. The SAGA:
1. Pre-approve: drift check (`TierDriftChecker`) + name re-uniqueness at org level
2. Thrift publish: `createSlabAndUpdateStrategies` with `SLAB_UPGRADE` and `SLAB_DOWNGRADE` strategies → MySQL `program_slabs` + `strategies`
3. Post-approve: status → ACTIVE, stamp `slabId`, transition old parent → SNAPSHOT

If step 2 fails → HTTP 500, tier → `PUBLISH_FAILED`. UI should offer a retry button; the tier can be resubmitted from `PUBLISH_FAILED` by deleting the failed doc and recreating (no in-place retry endpoint today).

### 10.14 Name uniqueness is per `programId`

Names must be unique within a `programId` + `orgId` combination — **not org-wide**. Two tiers in different programs can share a name. The UI should validate name uniqueness per program in its form validation. The server enforces the check at create time (409) and at approve time (409 again, at the org level in MySQL, which is stricter — rare to hit but possible).

### 10.15 `programId` is immutable

Once a tier is created with a `programId`, it cannot be changed. A tier belongs to exactly one loyalty program. `TierUpdateRequest` doesn't even carry `programId` — it is omitted from the DTO.

### 10.16 50-tier cap per program

`TierValidationService.assignNextSerialNumber` throws `InvalidInputException` when a program already has 50 live tiers. Message: `"Maximum tier limit (50) reached for this program"`. UI should surface this as a soft error on the create form.

### 10.17 No rate limits defined

No explicit rate limiting on tier endpoints. Standard platform-level rate limiting applies.

---

## 11. Error Handling — Global Advice Reference

Authoritative mapping from `TargetGroupErrorAdvice.java`:

| Exception | HTTP Status | `errors[0].code` | Notes |
|---|:---:|---|---|
| `NotFoundException` | **`200 OK`** | resolved | **§10.1 BUG.** Overridden to 404 locally by `TierController` for GET/PUT/DELETE; NOT overridden on review endpoints. |
| `InvalidInputException` | `400` | resolved | Validators throw this. |
| `ConflictException` | `409` | resolved | |
| `HttpMessageNotReadableException` | `400` | `COMMON.INVALID_INPUT` | Bad JSON body |
| `MethodArgumentNotValidException` | `400` | per-field resolver | `@Valid` on DTO. |
| `OperationFailedException` | `500` | resolved | |
| `EMFThriftException` | `500` | resolved | Downstream Thrift failure |
| `ServiceException` | `400` | resolved | |
| `ConstraintViolationException` | `400` | resolved | JSR-303 at service layer |
| `DataIntegrityViolationException` | `400` (body code `500`) | `500` | Legacy code/body mismatch — keep if observed |
| `AccessDeniedException` | `403` | resolved | |
| `BadCredentialsException` | `401` | resolved | |
| `TokenExpiredException` | `498` | resolved | |
| `TierApprovalDriftException` | `409` | — | Handled by `TierErrorAdvice` (not global). Structured body — §5.7.1. |
| `Throwable` (fall-through) | `500` | `"Something went wrong, please try after sometime."` | Generic handler — §10.6 |

---

## 12. Endpoint × Error Matrix (quick reference)

| Endpoint | 200 | 201 | 204 | 400 | 401/403 | 404 | 409 | 500 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `GET    /v3/tiers`                  | ✓ | | | param | ✓ | | | ✓ |
| `GET    /v3/tiers/{tierId}`         | ✓ | | | | ✓ | ✓ | | ✓ |
| `POST   /v3/tiers`                  | | ✓ | | validator + JSR-303 | ✓ | | name-dup, 50-cap | ✓ |
| `PUT    /v3/tiers/{tierId}`         | ✓ | | | validator | ✓ | ✓ | `SNAPSHOT`/`DELETED`, rename-dup | ✓ |
| `DELETE /v3/tiers/{tierId}`         | | | ✓ | | ✓ | ✓ | status ≠ `DRAFT` | ✓ |
| `POST   /v3/tiers/{id}/submit`      | ✓ *(incl. not-found — §10.1)* | | | | ✓ | | status ≠ `DRAFT` | ✓ |
| `POST   /v3/tiers/{id}/approve`     | ✓ *(incl. not-found — §10.1)* | | | | ✓ | | status ≠ `PENDING_APPROVAL`, **drift** | unknown action, SAGA failure |
| `GET    /v3/tiers/approvals`        | ✓ | | | param | ✓ | | | ✓ |

---

## 13. Feature → Endpoint Map

| Feature / User Story | Endpoint(s) | Behaviour |
|---|---|---|
| E1-US1: Create Tier | `POST /v3/tiers` | Returns 201 with full document |
| E1-US2: List Tiers | `GET /v3/tiers` | Envelopes per slab with KPI summary |
| E1-US3: View Tier | `GET /v3/tiers/{tierId}` | Single envelope |
| E1-US4: Edit Tier | `PUT /v3/tiers/{tierId}` | `DRAFT`/`PENDING_APPROVAL` in-place; `ACTIVE` creates versioned draft |
| E1-US5: Delete Tier | `DELETE /v3/tiers/{tierId}` | DRAFT only; soft-delete |
| E2-US1: Submit for Approval | `POST /v3/tiers/{tierId}/submit` | DRAFT → PENDING_APPROVAL |
| E2-US2: Approve | `POST /v3/tiers/{tierId}/approve` + `approvalStatus: APPROVE` | SAGA — Thrift publish → ACTIVE + `slabId` |
| E2-US3: Reject | `POST /v3/tiers/{tierId}/approve` + `approvalStatus: REJECT` | PENDING_APPROVAL → DRAFT + `rejectionComment` |
| E2-US4: Pending Approvals Queue | `GET /v3/tiers/approvals` | Raw `UnifiedTierConfig` list for the reviewer |

---

## 14. Date Format Reference

All date/datetime fields use ISO-8601 with an **explicit `+00:00` offset**:

```
yyyy-MM-ddTHH:mm:ss+00:00
```

Examples:
- `"2026-04-21T08:14:02+00:00"`
- `"2026-03-15T00:00:00+00:00"`

**Parse rules:**
- The UI **should send** dates in this exact form on create/update request bodies.
- The server **always returns** dates in this exact form on every response.
- `Z` shorthand must NOT appear in any tier payload. If seen, treat as a backend bug and file a ticket.
- Jackson's default `ObjectMapper` (with `JavaTimeModule` or the default `Date` handling) accepts both `Z` and numeric-offset forms on parse — so the UI's parse is tolerant if we ever slip up. The round-trip write-back from the server, however, is strict `+00:00`.

**Why `+00:00` not `Z`?** Consistency with the platform's canonical tier-date form. A single uniform format avoids confusing consumers that do string comparisons on the offset (some were parsing `Z` as a literal character). See `TierDateFormat.java` for the utility + serializer.

---

## 15. Key IDs Glossary

| Field | Format | Mutable | Where Used |
|---|---|:---:|---|
| `objectId` (`UnifiedTierConfig.objectId`) | MongoDB ObjectId (24-char hex, e.g. `660a1b2c3d4e5f6a7b8c9d0e`) | No | **Primary handle** — path param for `GET`/`PUT`/`DELETE`/`submit`/`approve` |
| `tierUniqueId` | String, pattern `ut-{programId}-{serial3d}`, e.g. `ut-977-002` | No | Also accepted as `{tierId}` path param for `GET`/`PUT`/`DELETE` (facade resolves both) |
| `slabId` | `Long` (MySQL `program_slabs.id`, e.g. `3850`) | No | SQL linkage. Populated **after** first APPROVE. `null` before. Sits on envelope AND on `TierView.live`. **Cannot be used directly as `{tierId}`** — §10.5. |
| `parentId` | MongoDB ObjectId | No | On versioned drafts-of-ACTIVE, points at the ACTIVE's `objectId`. `null` on originals. |
| `serialNumber` | `Integer`, assigned on create | No (immutable across edits) | Visible ordering handle on the UI — part of `tierUniqueId`. |
| `programId` | `Integer` | **No (immutable)** | Identifies the loyalty program this tier belongs to. Set at create. Cannot be changed via PUT. |
| `orgId` | `Long` | No | Set from auth token. Scopes all queries — tenant isolation. |

---

## 16. UI Handoff Checklist

1. **Consume `TierEnvelope`, not `UnifiedTierConfig`, as the read shape.** Tests that assumed flat documents from `GET /v3/tiers` (v2) need to be updated.
2. **Handle all six envelope scenarios** (§5.1). Never assume both `live` and `pendingDraft` are present; never assume only one is either.
3. **Check `errors[0]` on HTTP 200 responses from `/submit` and `/approve`.** Not-found returns 200 with an error object (§10.1).
4. **Omit the `status` query param on `GET /v3/tiers`** or you'll get an empty list (§10.2). Filter client-side if you need status subsets.
5. **Render `totalMembers === null` as `—` or `n/a`.** It is not zero (§10.3).
6. **Validate `approvalStatus` is `APPROVE` or `REJECT` on the client.** Anything else is a 500 (§10.6).
7. **On drift 409, render `data.diffs`, not `errors[0].message`.** The structured diff is the source of truth (§5.7.1).
8. **Store `objectId` as the primary tier handle.** `tierUniqueId` works too, but numeric `slabId` does not route correctly through the detail endpoint (§10.5).
9. **Do not send the `Idempotency-Key` header and expect dedup.** Use it as a client-side correlation id only (§10.11).
10. **Do not render `engineConfig` or `basisSqlSnapshot`.** These are engine internals leaked through the document, not part of the visible contract (§10.9, §10.10).
11. **Offer a retry UX on HTTP 500 during APPROVE.** The Thrift SAGA can fail transiently (§10.13).
12. **All dates on responses are `yyyy-MM-ddTHH:mm:ss+00:00`.** Never `Z`. Your parser should accept both defensively, but generate `+00:00` on outbound requests for consistency (§14).
