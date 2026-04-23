# API Contract — Tiers (v3)

> **For:** UI Development Team (Garuda)
> **Version:** 3.3 — rewritten 2026-04-23 (Q27 envelope→flat-entry pivot on GET path; write contract unchanged)
> **Base URL:** `https://{host}/v3`
> **Auth:** Bearer token in `Authorization` header
> **Content-Type:** `application/json`
> **Source phases:** `00-ba.md`, `01-architect.md`, `03-designer.md`, session-memory.md
> **Status:** Implemented and in QA. Every behavioural claim here is evidence-backed from code — file paths and line numbers are cited at the end of each section under **Evidence**.

> **Q27 pivot (2026-04-23) — GET path replaced:** The listing and detail GET endpoints now return a **flat `List<TierEntry>`** (see §5.1, §5.2, §6.11). Previously the list returned envelopes that paired SQL LIVE with a Mongo pending draft inside a single object; now each side is a separate entry in the list (same `slabId`, different `status`). The top-level `validity` block on GET responses has been renamed to `renewal`, and the nested `validity.renewal` sub-block has been dropped. The `summary` (KpiSummary) block has been removed from the list response. `TierStatus` now includes `REJECTED` as a first-class wire value. **Write contract (POST / PUT / DELETE / review endpoints) is unchanged in Q27.**

---

## Overview

Tier Programs let loyalty administrators create, configure, and publish tier structures (e.g., "Gold", "Platinum", "Diamond") through a REST API. Each tier has:

- A **dual-backed lifecycle**: `DRAFT` / `PENDING_APPROVAL` live in MongoDB (maker-checker workflow); `ACTIVE` tiers are published to MySQL `program_slabs` via a synchronous Thrift SAGA.
- A **maker-checker approval workflow** — makers create/edit drafts, reviewers approve or reject.
- A **flat `TierEntry` read model** (Q27) — one entry per state per slabId. LIVE entries come from SQL `program_slabs`; DRAFT / PENDING_APPROVAL / REJECTED entries come from MongoDB. Two entries sharing the same `slabId` = LIVE tier with an in-flight edit. UI consumes `List<TierEntry>`, not raw `UnifiedTierConfig` documents.
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

**Purpose:** List all tiers for a program as a **flat array of `TierEntry`**. When a slab has both a LIVE SQL row and a workflow-visible Mongo doc (DRAFT / PENDING_APPROVAL / REJECTED), **two separate entries** appear in the list sharing the same `slabId`.

**Maps to:** E1-US2 (List Tiers), AC-1.1 through AC-1.6

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `programId` | query | `int` | **Yes** | The loyalty program id |
| `status` | query | `List<TierStatus>` (CSV) | No | **See "Known behaviour" below — non-empty short-circuits to empty response.** Omit to get the default entry list. |

```http
GET /v3/tiers?programId=977
Authorization: Bearer <token>
```

### Response — Success (HTTP 200 OK)

Body: `ResponseWrapper<TierListResponse>` where `TierListResponse = { "tiers": List<TierEntry> }`.

```json
{
  "data": {
    "tiers": [
      {
        "status": "LIVE",
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
        "renewal": {
          "periodType": "FIXED",
          "periodValue": 12,
          "startDate": "2026-03-15T00:00:00+00:00",
          "endDate": null
        },
        "downgrade": {
          "target": "SINGLE",
          "reevaluateOnReturn": false,
          "dailyEnabled": false,
          "conditions": []
        },
        "meta": {
          "createdBy": "15043871",
          "createdAt": "2026-03-15T08:14:02+00:00",
          "updatedBy": "15043871",
          "updatedAt": "2026-03-15T08:14:02+00:00"
        }
      },
      {
        "status": "LIVE",
        "slabId": 3851,
        "name": "Platinum",
        "description": "Top tier",
        "color": "#E5E4E2",
        "serialNumber": 3,
        "tierStartDate": "2026-02-10T09:12:00+00:00",
        "eligibility": { "...": "..." },
        "renewal":     { "...": "..." },
        "downgrade":   { "...": "..." },
        "meta":        { "...": "..." }
      },
      {
        "status": "PENDING_APPROVAL",
        "slabId": 3851,
        "tierUniqueId": "ut-977-003",
        "name": "Platinum (revised)",
        "description": "Top tier — revised",
        "color": "#E5E4E2",
        "serialNumber": 3,
        "eligibility": { "...": "..." },
        "renewal":     { "...": "..." },
        "downgrade":   { "...": "..." },
        "meta": {
          "createdBy": "15043871",
          "createdAt": "2026-04-20T10:15:00+00:00",
          "updatedBy": "15043871",
          "updatedAt": "2026-04-20T10:15:00+00:00"
        }
      },
      {
        "status": "DRAFT",
        "tierUniqueId": "ut-977-004",
        "name": "Diamond",
        "description": "Brand new tier",
        "color": "#B9F2FF",
        "serialNumber": 4,
        "eligibility": { "...": "..." },
        "renewal":     { "...": "..." },
        "downgrade":   { "...": "..." },
        "meta": {
          "createdBy": "15043871",
          "createdAt": "2026-04-22T11:00:00+00:00",
          "updatedBy": "15043871",
          "updatedAt": "2026-04-22T11:00:00+00:00"
        }
      }
    ]
  },
  "errors": null,
  "warnings": null
}
```

> **Key change from v3.2 (Rework #6a):** the previous **envelope** model (pairing SQL-LIVE with a pending draft inside one object, with hoisted fields + nested `live`/`pendingDraft` blocks) is gone. In Q27 (2026-04-23) each side is its own entry. Two entries with the same `slabId` means "LIVE tier with an in-flight edit" — the UI groups them client-side by `slabId`.

### The Entry Model (READ FIRST)

`tiers` is an array of `TierEntry`. **Each entry is one side** of what the user perceives as a tier. Pairing is expressed by two entries sharing a `slabId`.

```
TierEntry
├── status          (String)   — "LIVE" | "DRAFT" | "PENDING_APPROVAL" | "REJECTED"
├── slabId          (Long?)    — SQL anchor; present on LIVE; present on DRAFT/PENDING/REJECTED
│                                iff the draft is editing a LIVE tier; null for brand-new drafts
├── tierUniqueId    (String?)  — Mongo-side stable id; absent on LIVE, present on DRAFT/PENDING/REJECTED
├── name            (String)   ┐
├── description     (String?)  │
├── color           (String?)  ├── tier-facing fields
├── serialNumber    (Integer)  │
├── tierStartDate   (Date?)    │   LIVE-only (SQL program_slabs.created_on)
├── eligibility     (obj)      │
├── renewal         (obj)      │   ← renamed from `validity` in Q27
├── downgrade       (obj)      ┘   read-only (rejected on POST/PUT — see §10.19)
├── rejectionComment (String?) — present on a DRAFT whose last review action was REJECT
└── meta            (obj)      — trimmed audit: createdBy/At, updatedBy/At only
```

**Four `status` values the UI must handle:**

| `status` wire value | `slabId` | `tierUniqueId` | `tierStartDate` | Source | What it represents |
|---|:---:|:---:|:---:|---|---|
| `LIVE`             | present  | absent   | present  | SQL `program_slabs` | The currently-running tier |
| `DRAFT`            | present or null | present | absent | Mongo DRAFT doc | Maker is editing (new or edit-of-LIVE) |
| `PENDING_APPROVAL` | present or null | present | absent | Mongo PENDING_APPROVAL doc | Submitted; awaiting reviewer |
| `REJECTED`         | present or null | present | absent | Mongo REJECTED doc | Reviewer rejected; maker can re-edit |

**Pairing semantics (client-side):**

- Entries with the same `slabId` are the **two sides of the same tier** — the LIVE (`status: "LIVE"`) and an in-flight edit (`DRAFT` / `PENDING_APPROVAL` / `REJECTED`).
- A `status: "DRAFT"` entry with `slabId: null` is a **brand-new draft** — a tier that has never been LIVE.
- A `status: "LIVE"` entry **never** has a paired sibling if there is no in-flight edit.
- Ordering: the list groups each LIVE row immediately followed by its in-flight edit (if any). Brand-new drafts tail the list in Mongo-insertion order.

Because of class-level `@JsonInclude(NON_NULL)`, **absent fields are not present on the wire.** UI should test by key presence, not by `field === null`.

### Response — Error Cases

| HTTP Status | When | Notes |
|---|---|---|
| `400` | `programId` not provided or non-numeric | Via global advice |
| `401` / `403` | Auth failure | Global advice |
| `500` | Unexpected | Fall-through |

### Known Behaviour — `status` query param short-circuits

`GET /v3/tiers?status=ACTIVE` (or any non-empty status list) returns an **empty `tiers` array**. This is by design: the method does not support filtering by status in its current form. **The UI should omit the `status` query param** and filter client-side if needed.

### Notes

- **Three sequential round-trips** (1 SQL + 2 Mongo) feed the flat list. The list read is **non-transactional** — a writer concurrently publishing a tier can produce stale reads. A tier just published may be missing for one poll cycle; a just-deleted DRAFT may appear. UI must defensively handle "id from last list no longer exists" (a follow-up edit/approve may 404).
- **`tierStartDate` is LIVE-only** — sourced exclusively from SQL `program_slabs.created_on`. Absent on DRAFT/PENDING/REJECTED entries (no SQL row yet); absent on a LIVE entry only if the backing emf-parent server predates Rework #3. Do NOT substitute a fallback (e.g., `new Date(0)`) when it is missing.
- **No `summary` block** — `TierListResponse` no longer carries `KpiSummary` (dropped in Q27). Count of tiers, live-count, pending-count, member totals are all UI-computed if needed.
- **No `origin` field** — the old `TierOrigin` enum (`LEGACY_SQL_ONLY` / `MONGO_ONLY` / `BOTH`) has been removed in Q27. `status` is now the sole discriminator.
- **No `live` / `pendingDraft` nested blocks** — the old forward-compat dual-block pattern is gone. Each side is its own entry.

**Evidence:** `TierController.java` (Q27 signatures); `TierFacade.listTiers` (new builder call, no KpiSummary); `TierEntryBuilder.build()` (two-pass: LIVE entries then in-flight entries grouped by slabId, brand-new drafts tail); `SqlTierConverter.toEntry()` (LIVE side → TierEntry with `status = "LIVE"`, invokes `stripNestedRenewal` to drop `validity.renewal` from the wire without mutating the server-side `TierValidityConfig`); `TierStrategyTransformer.extractValidity` still synthesizes the default `renewal` server-side (L813-815) for round-trip symmetry with normalized DRAFT — the Q27 wire-drop is a read-side concern handled at the converter boundary.

---

## 5.2 `GET /v3/tiers/{tierId}` — Get Tier Detail

**Purpose:** Retrieve a single tier view as a **`List<TierEntry>` of 1 or 2 entries** (Q27 pivot — the old `TierEnvelope` is gone).

**Maps to:** E1-US3 (View Tier), AC-2.1 through AC-2.4

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | Either a **numeric `slabId`** (e.g. `"3850"`) **or** a **Mongo `tierUniqueId`** (e.g. `"ut-977-003"`). Legacy Mongo `objectId` is not supported by the new endpoint — use `tierUniqueId`. |

```http
GET /v3/tiers/3850
Authorization: Bearer <token>
```

### URL Disambiguation (Q27-B-b — locked)

The facade decides between two lookup modes based on whether `{tierId}` parses as a `Long`:

| `{tierId}` shape | Lookup mode | What you get back |
|---|---|---|
| **Numeric** (parses as `Long`) | **slabId lookup.** Resolve the SQL LIVE row by `slabId`, then pair it with any workflow-visible Mongo doc whose `slabId` matches (status ∈ `DRAFT` / `PENDING_APPROVAL` / `REJECTED`). | Array of **1 entry** (LIVE only) **or 2 entries** (LIVE + paired in-flight), same slabId on both. |
| **String** (doesn't parse) | **tierUniqueId lookup.** Resolve the Mongo doc by `tierUniqueId`. No pairing — even if the doc points at a LIVE slabId, only the draft entry is returned. | Array of **1 entry** (the draft, status ∈ `DRAFT` / `PENDING_APPROVAL` / `REJECTED`). |

**Why tierUniqueId returns draft-only:** the UI uses `tierUniqueId` when it already has a LIVE row on screen and wants to fetch *just* the in-flight revision. Returning the LIVE again would duplicate data the UI already has. To get the pair, call with the numeric `slabId` instead.

### Response — Success (HTTP 200 OK)

Body: `ResponseWrapper<List<TierEntry>>`.

**Example A — numeric `slabId` path (edit-of-LIVE, array of 2):**

```http
GET /v3/tiers/3850
```

```json
{
  "data": [
    {
      "status": "LIVE",
      "slabId": 3850,
      "tierUniqueId": null,
      "name": "Gold",
      "description": "Premium tier",
      "color": "#FFD700",
      "serialNumber": 2,
      "tierStartDate": "2026-03-15T08:14:02+00:00",
      "eligibility": { "kpiType": "CURRENT_POINTS", "threshold": 5000, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
      "renewal":     { "periodType": "FIXED", "periodValue": 12, "startDate": "2026-03-15T00:00:00+00:00", "endDate": null },
      "downgrade":   { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] }
    },
    {
      "status": "DRAFT",
      "slabId": 3850,
      "tierUniqueId": "ut-977-002",
      "name": "Gold (revised)",
      "description": "Premium tier — revised",
      "color": "#FFD700",
      "serialNumber": 2,
      "eligibility": { "kpiType": "CURRENT_POINTS", "threshold": 4500, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
      "renewal":     { "periodType": "FIXED", "periodValue": 12, "startDate": "2026-04-21T00:00:00+00:00", "endDate": null },
      "downgrade":   { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] },
      "rejectionComment": null,
      "meta": {
        "createdBy": "15043871",
        "createdAt": "2026-04-20T10:15:00+00:00",
        "updatedBy": "15043871",
        "updatedAt": "2026-04-21T08:14:02+00:00"
      }
    }
  ],
  "errors": null,
  "warnings": null
}
```

**Example B — `tierUniqueId` path (draft-only, array of 1):**

```http
GET /v3/tiers/ut-977-002
```

```json
{
  "data": [
    {
      "status": "DRAFT",
      "slabId": 3850,
      "tierUniqueId": "ut-977-002",
      "name": "Gold (revised)",
      "description": "Premium tier — revised",
      "color": "#FFD700",
      "serialNumber": 2,
      "eligibility": { "kpiType": "CURRENT_POINTS", "threshold": 4500, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
      "renewal":     { "periodType": "FIXED", "periodValue": 12, "startDate": "2026-04-21T00:00:00+00:00", "endDate": null },
      "downgrade":   { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] },
      "rejectionComment": null,
      "meta": {
        "createdBy": "15043871",
        "createdAt": "2026-04-20T10:15:00+00:00",
        "updatedBy": "15043871",
        "updatedAt": "2026-04-21T08:14:02+00:00"
      }
    }
  ],
  "errors": null,
  "warnings": null
}
```

**Example C — brand-new DRAFT via `tierUniqueId` (array of 1, `slabId: null`):**

```http
GET /v3/tiers/ut-977-003
```

```json
{
  "data": [
    {
      "status": "DRAFT",
      "slabId": null,
      "tierUniqueId": "ut-977-003",
      "name": "Diamond",
      "description": "New top tier",
      "color": "#B9F2FF",
      "serialNumber": 4,
      "eligibility": { "kpiType": "CURRENT_POINTS", "threshold": 20000, "upgradeType": "EAGER", "expressionRelation": "AND", "conditions": [] },
      "renewal":     { "periodType": "FIXED", "periodValue": 12, "startDate": "2026-05-01T00:00:00+00:00", "endDate": null },
      "downgrade":   { "target": "SINGLE", "reevaluateOnReturn": false, "dailyEnabled": false, "conditions": [] },
      "rejectionComment": null,
      "meta": {
        "createdBy": "15043871",
        "createdAt": "2026-04-22T09:00:00+00:00",
        "updatedBy": "15043871",
        "updatedAt": "2026-04-22T09:00:00+00:00"
      }
    }
  ],
  "errors": null,
  "warnings": null
}
```

### Ordering within the Array

When both LIVE and an in-flight draft exist for the same slabId (numeric path, array of 2), the **LIVE entry is returned first**, followed by the paired in-flight entry (Q27-O-a). Callers may rely on this order.

### Response — Error Cases

| HTTP Status | Error Code | When | Example Message |
|:---:|---|---|---|
| `404` | `404` | Numeric path: `slabId` not found for this org's programs. String path: `tierUniqueId` not found in Mongo (or not workflow-visible). Cross-org access. | `"Tier not found: 3850"` |
| `401` / `403` | — | Auth failure | — |
| `500` | — | Unexpected | Generic message |

**404 body** (local handler):

```json
{
  "data": null,
  "errors": [ { "code": 404, "message": "Tier not found: 3850" } ],
  "warnings": null
}
```

### Notes

- `ConflictException → 409` is impossible on this endpoint (no conflict path).
- Unlike the review endpoints, this endpoint has a **local `@ExceptionHandler`** — 404 is a real 404 here.
- The array shape is **always** an array — even for a single entry. UI callers should iterate / destructure; there is no single-object response variant.
- `tierUniqueId` is `null` on LIVE entries that have no paired Mongo side (legacy SQL-only tiers). On DRAFT entries `tierUniqueId` is always populated.
- `slabId` is `null` only on brand-new DRAFT entries (Example C). On LIVE entries and on edit-of-LIVE drafts `slabId` is always populated.

**Evidence:** `TierController.java` (getTierDetail — response type `ResponseWrapper<List<TierEntry>>`, local NotFound handler); `TierFacade.getTierDetail` (Q27-B-b URL sniffing: `Long.parseLong` try/catch → slabId lookup, else tierUniqueId lookup); `TierEntryBuilder.buildOne` (pairs SQL row + Mongo doc into 1 or 2 entries); `TierEntryBuilder.buildDraftOnly` (tierUniqueId path — no pairing).

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

> **Write-narrow contract (Rework #6a — ADR-21R):** `downgrade` is **not accepted on write**. The field was removed from `TierCreateRequest` in Rework #6a (Q11 hard-flip). Downgrade configuration is engine-derived at APPROVE time and is only present on **read** responses (see §6.7, §10.19). Sending `downgrade` on POST is **rejected by Jackson strict-mode deserialization** as an unknown property (generic HTTP 400) — `downgrade` is **NOT** in `CLASS_A_CANONICAL_KEYS`, so the 9011 scanner does not target it. The 9011 Class A scanner targets the 8 program-level orchestration flags only (`isActive`, `reminders`, `downgradeConfirmation`, `renewalConfirmation`, `retainPoints`, `dailyDowngradeEnabled`, `isDowngradeOnReturnEnabled`, `isDowngradeOnPartnerProgramExpiryEnabled`). If those flags appear nested inside a `downgrade` object they WILL trigger 9011 via the recursive scanner — but the bare `downgrade` key itself is Jackson-rejected.

> **Rework #7 Commit 1 addition (2026-04-23) — Per-tier engine-backed renewal fields:** The following fields on `validity.renewal` are now accepted on write and map to engine `TierDowngradeSlabConfig` per-slab storage:
> - `downgradeTo` (String, enum `SINGLE`/`THRESHOLD`/`LOWEST`) — engine `slab.downgradeTarget`. Runtime consumer: `peb BaseCalculatorBuilder:182-201` switch on this value to pick per-slab calculator bean.
> - `shouldDowngrade` (Boolean, optional) — engine `slab.shouldDowngrade`. When `false`, the engine does not auto-downgrade this tier.
> - `conditions[]` (List of `TierCondition`) — maps per-element to engine `slab.conditions.{purchase,numVisits,points,tracker[]}`. Previously reserved / forced null — now active.
> - `expressionRelation` (**String — DNF boolean expression**) — e.g. `"(PURCHASE AND VISITS) OR POINTS"`. Parsed and serialised to the engine's bracket format (`"[[purchase,numVisits],[points]]"`) at APPROVE. Previously reserved / forced null — now active. See §6.6 for grammar and §10.20 for the serialisation rules.
>
> All four fields are **optional**. POSTs without them behave identically to before Rework #7 (SLAB_DOWNGRADE strategy left untouched at APPROVE). `criteriaType` lock from Q26 B1a is preserved — still only `"Same as eligibility"` accepted (code 9017 otherwise). See §6.6 for full field details and §10.20 for the synthesis wiring.

**Minimal canonical shape (backward-compatible — no new fields):**

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
    "periodType": "FIXED",
    "periodValue": 12,
    "startDate": "2026-04-21T00:00:00+00:00",
    "renewal": {
      "criteriaType": "Same as eligibility"
    }
  }
}
```

**Rich shape with Rework #7 per-tier renewal fields:**

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
    "periodType": "FIXED",
    "periodValue": 12,
    "startDate": "2026-04-21T00:00:00+00:00",
    "renewalWindowType": "CUSTOM_PERIOD",
    "computationWindowStartValue": 3,
    "computationWindowEndValue": 12,
    "minimumDuration": 6,
    "renewal": {
      "criteriaType": "Same as eligibility",
      "downgradeTo": "SINGLE",
      "shouldDowngrade": true,
      "expressionRelation": "(PURCHASE AND VISITS) OR POINTS OR (TRACKER AND POINTS)",
      "conditions": [
        { "type": "PURCHASE", "value": "2000" },
        { "type": "VISITS",   "value": "3"    },
        { "type": "POINTS",   "value": "1500" },
        { "type": "TRACKER",  "value": "10",  "trackerName": "store_visits_q1" }
      ]
    }
  }
}
```

The `expressionRelation` above reads as *(PURCHASE AND VISITS) OR POINTS OR (TRACKER AND POINTS)* — the customer renews if **any** of: (a) they've spent ≥ 2000 AND visited ≥ 3 times, (b) they've earned ≥ 1500 points, or (c) the tracker `store_visits_q1` ≥ 10 AND they've earned ≥ 1500 points. See §6.6 for the grammar.

The advanced validity fields (Rework #7 Commit 3): `renewalWindowType=CUSTOM_PERIOD` with `computationWindowStartValue=3` + `computationWindowEndValue=12` means "evaluate the renewal conditions over months 3 through 12 before the evaluation date". `minimumDuration=6` floors the tier duration — engine won't downgrade before 6 months elapse regardless of renewal-rule outcome.

**Evidence:** `TierCreateRequest.java` — no `downgrade` field, no getter/setter; the DTO class is annotated **`@JsonIgnoreProperties(ignoreUnknown = false)`** (Rework #6a R11-2 — tier-scoped annotation, NOT the global `spring.jackson.deserialization.fail-on-unknown-properties` flag, so environment drift cannot silently loosen this contract) so any unknown root-level key (including a bare `downgrade` object) fails binding with `UnrecognizedPropertyException` → HTTP 400 generic. `TierEnumValidation.CLASS_A_CANONICAL_KEYS` (see `TierEnumValidation.java:190–199`) lists exactly **8** program-level orchestration keys — `isActive`, `reminders`, `downgradeConfirmation`, `renewalConfirmation`, `retainPoints`, `dailyDowngradeEnabled`, `isDowngradeOnReturnEnabled`, `isDowngradeOnPartnerProgramExpiryEnabled`. The bare key `downgrade` is **NOT** in this set — it is rejected by Jackson, not by the 9011 scanner. **Regression cover:** `TierCreateRequestValidatorTest.shouldRejectLegacyDowngradeBlockAtJacksonBindingLayer()` (BT-197b POST) empirically verifies the rejection and asserts `ex.getPropertyName() == "downgrade"`; `shouldAcceptKnownFieldsAtJacksonBindingLayer()` is the negative control. **Rework #7:** `TierRenewalConfig.java` carries the four new per-tier fields; `TierStrategyTransformer.synthesiseDowngradeFromRenewal` bridges `validity.renewal.*` → engine `TierDowngradeSlabConfig` per-slab fields at APPROVE time via `TierApprovalHandler.applyDowngradeDelta`. Regression cover: BT-198..BT-210 (`TierRenewalValidationTest` + `TierStrategyTransformerTest`).

### Request Field Validation

| Field | Type | Required | Validation |
|---|---|:---:|---|
| `programId` | `Integer` | **Yes** | JSR-303 `@NotNull`. |
| `name` | `String` | **Yes** | Non-blank. Max 100 chars. Must be unique within `programId` + `orgId` (across `DRAFT`, `ACTIVE`, `PENDING_APPROVAL`). |
| `description` | `String` | No | Max 500 chars. |
| `color` | `String` | No | Hex format `#RRGGBB` (regex `^#[0-9A-Fa-f]{6}$`). |
| `eligibility.kpiType` | enum | Yes (if `eligibility` sent) | One of `CURRENT_POINTS`, `CUMULATIVE_POINTS`, `CUMULATIVE_PURCHASES`, `TRACKER_VALUE_BASED`. Matches engine `SlabUpgradeStrategy.CurrentValueType` (writes to `SLAB_UPGRADE.propertyValues.current_value_type`). |
| `eligibility.threshold` | `Integer` | Yes (if `eligibility` sent) | `>= 0` (zero is accepted; only negatives rejected). |
| `eligibility.upgradeType` | enum | Yes (if `eligibility` sent) | One of `EAGER`, `DYNAMIC`, `LAZY`. Matches engine `SlabUpgradeMode`. |
| `eligibility.expressionRelation` | enum | No | `AND` or `OR`. |
| `eligibility.conditions[].type` | enum | No | One of `PURCHASE`, `VISITS`, `POINTS`, `TRACKER`. See §6.8 (TierCondition). |
| `validity.periodType` | enum | No | One of `FIXED`, `SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`, `FIXED_CUSTOMER_REGISTRATION`. Matches engine `TierDowngradePeriodConfig.PeriodType`. See §6.5 for semantics. |
| `validity.periodValue` | `Integer` | No | Positive. |
| `validity.startDate` | ISO-8601 | No | Format `yyyy-MM-ddTHH:mm:ss+00:00` (see §10). |
| `validity.endDate` | — | — | **Never stored. Derived from `startDate + periodValue` at read time if needed.** Do not send. |
| `validity.renewal.criteriaType` | `String` | Yes (if `renewal` sent) | **Must be `"Same as eligibility"`.** Any other value → 400 with code **9017**. If you omit `renewal` entirely, the server fills the default pre-save. |
| `validity.renewal.downgradeTo` | `String` enum | No (Rework #7) | Must be one of `SINGLE`/`THRESHOLD`/`LOWEST`. Maps to engine `TierDowngradeSlabConfig.downgradeTarget` per-slab. Invalid value → **9019**. |
| `validity.renewal.shouldDowngrade` | `Boolean` | No (Rework #7) | Boxed Boolean — null omits the field (engine keeps prior value), explicit `false` disables auto-downgrade for this tier. Maps to engine `slab.shouldDowngrade`. |
| `validity.renewal.expressionRelation` | `String` (DNF boolean) | No (Rework #7) | e.g. `"PURCHASE AND VISITS"`, `"PURCHASE OR VISITS OR POINTS"`, `"(PURCHASE AND VISITS) OR POINTS"`. Grammar: `group (OR group)*`, `group = '(' kpi (AND kpi)* ')' \| kpi (AND kpi)*`, `kpi ∈ {PURCHASE,VISITS,POINTS,TRACKER}`. Strict parens when mixing AND+OR at top level. Case-insensitive. Serialised to engine bracket format. Invalid → **9021**. |
| `validity.renewal.conditions[]` | `TierCondition[]` | No (Rework #7) | Each element: `{type, value, trackerName?}`. Types `PURCHASE`/`VISITS`/`POINTS`/`TRACKER`. Maps to engine `slab.conditions.{purchase,numVisits,points,tracker[]}`. Every KPI referenced in `expressionRelation` must be present here. **Multi-tracker rejected** (≥2 `TRACKER` entries) → **9020** (Q5c symmetry). |
| `validity.renewalWindowType` | `String` enum | No (Rework #7 Commit 3) | One of `FIXED_DATE_BASED`, `LAST_CALENDAR_YEAR`, `CUSTOM_PERIOD`. Engine canonical `TierDowngradePeriodConfig.RenewalWindowType`. Defines how `computationWindow*` offsets are interpreted. Invalid → **9022**. |
| `validity.computationWindowStartValue` | `Integer` (months) | No (Rework #7 Commit 3) | Back-offset for evaluation window START. ≥ 0. **Requires** `renewalWindowType` (atomic coupling — inert without it, code **9023**). Negative → **9024**. |
| `validity.computationWindowEndValue` | `Integer` (months) | No (Rework #7 Commit 3) | Back-offset for evaluation window END. ≥ 0. **Requires** `renewalWindowType` (atomic coupling — code **9023**). Negative → **9024**. |
| `validity.minimumDuration` | `Integer` (months) | No (Rework #7 Commit 3) | Minimum tier duration — engine refuses downgrade if computed end < `now + minimumDuration months`. Standalone (no coupling to `renewalWindowType`). ≥ 0. Negative → **9024**. |
| `downgrade` (bare key) | — | **Rejected on write** | Jackson strict-mode — `UnrecognizedPropertyException` → **HTTP 400** (generic, not 9011). `downgrade` is NOT in `CLASS_A_CANONICAL_KEYS`. See §10.19 write-narrow / read-wide asymmetry. |
| `downgrade.*` (nested Class A keys) | — | **Rejected on write** | If the nested object carries any of the 8 Class A orchestration keys (`isActive`, `reminders`, `downgradeConfirmation`, `renewalConfirmation`, `retainPoints`, `dailyDowngradeEnabled`, `isDowngradeOnReturnEnabled`, `isDowngradeOnPartnerProgramExpiryEnabled`), the recursive pre-binding scanner catches them first → code **9011**. |

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
      "periodType": "FIXED",
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

**Validator messages (exact strings from `TierCreateRequestValidator` + `TierEnumValidation`):**

Post-binding checks (validator sees deserialised DTO):

| Check | Thrown message |
|---|---|
| Body null | `"Request body is required"` |
| `programId` null | `"programId is required"` |
| `name` blank | `"name is required"` |
| `name` length > 100 | `"name must not exceed 100 characters"` |
| `description` length > 500 | `"description must not exceed 500 characters"` |
| `color` not `#RRGGBB` | `"color must be hex format #RRGGBB"` |
| `kpiType` not in allowed set | `"kpiType must be one of: [CURRENT_POINTS, CUMULATIVE_POINTS, CUMULATIVE_PURCHASES, TRACKER_VALUE_BASED]"` |
| `threshold` < 0 | `"threshold must be positive"` *(zero is accepted; only negatives rejected)* |
| `upgradeType` not in allowed set | `"upgradeType must be one of: [EAGER, DYNAMIC, LAZY]"` |
| `expressionRelation` not in allowed set | `"expressionRelation must be one of: [AND, OR]"` |
| `periodType` not in allowed set | `"periodType must be one of: [FIXED, SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC, FIXED_CUSTOMER_REGISTRATION]"` |
| `conditions[].type` not in allowed set | `"eligibility.conditions[].type must be one of: [PURCHASE, VISITS, POINTS, TRACKER] (got: <value>)"` |

Rework #6a contract-hardening codes (9011–9018) — evidence: `TierEnumValidation.java` constants + `TierCreateRequestValidator.java:65–93`:

| Code | Scope | Trigger | Stage |
|:----:|-------|---------|-------|
| **9011** | Class A program-level field | Any of `isActive`, `reminders`, `downgradeConfirmation`, `renewalConfirmation`, `retainPoints`, `dailyDowngradeEnabled`, `isDowngradeOnReturnEnabled`, `isDowngradeOnPartnerProgramExpiryEnabled` present at any nesting level. **Note:** the bare `downgrade` key itself is **not** covered by 9011 — it is Jackson-rejected (generic 400). Nested Class A keys inside a `downgrade` object DO trigger 9011 via the recursive scan. | Pre-binding — recursive scan |
| **9012** | Class B schedule field | Root-level `schedule`, `nudges`, or `notificationConfig` present | Pre-binding — root-level scan |
| **9013** | `eligibilityCriteriaType` on write | Key `eligibilityCriteriaType` present at any nesting level | Pre-binding — recursive scan |
| **9014** | `startDate` on SLAB_UPGRADE family | `periodType` ∈ {`SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`} AND `startDate` not null | Post-binding |
| **9015** | String `"-1"` sentinel | Field `programId`, `periodValue`, or `threshold` carries text value `"-1"` at any nesting level | Pre-binding — recursive scan |
| **9016** | Numeric `-1` sentinel | Field `programId`, `periodValue`, or `threshold` carries numeric value `-1` at any nesting level; fires BEFORE 9018 post-binding guard | Pre-binding — recursive scan |
| **9017** | Renewal `criteriaType` drift | `renewal.criteriaType` non-null AND not exactly `"Same as eligibility"` | Post-binding |
| **9018** | FIXED-family missing positive `periodValue` | `periodType` ∈ {`FIXED`, `FIXED_CUSTOMER_REGISTRATION`} AND (`periodValue` null OR ≤ 0); SLAB_UPGRADE family is NOT checked | Post-binding |
| **9019** | Invalid `renewal.downgradeTo` | `renewal.downgradeTo` non-null AND not in {`SINGLE`, `THRESHOLD`, `LOWEST`}. Engine canonical `TierDowngradeSlabConfig.downgradeTarget`. Rework #7. | Post-binding |
| **9020** | Multi-tracker renewal | `renewal.conditions[]` contains ≥ 2 entries with `type=TRACKER`. Q5c eligibility symmetry — multi-tracker renewal deferred pending follow-up epic. Rework #7. | Post-binding |
| **9021** | Invalid `renewal.expressionRelation` DNF | Grammar error (unknown KPI token, unknown operator, unbalanced parens, ambiguous AND+OR at top level without parens), OR the expression references a KPI not present in `renewal.conditions[]`. Rework #7. | Post-binding |
| **9022** | Invalid `validity.renewalWindowType` | `validity.renewalWindowType` non-null AND not in {`FIXED_DATE_BASED`, `LAST_CALENDAR_YEAR`, `CUSTOM_PERIOD`}. Engine canonical `TierDowngradePeriodConfig.RenewalWindowType`. Rework #7 Commit 3. | Post-binding |
| **9023** | `validity.computationWindow*` without `renewalWindowType` | Any of `validity.computationWindowStartValue` / `computationWindowEndValue` is set but `validity.renewalWindowType` is null — the offsets are inert on the engine without a window type (`TierDowngradeDateHelper:35-37`). Rework #7 Commit 3. | Post-binding |
| **9024** | Negative numeric `validity.*` | Any of `validity.computationWindowStartValue` / `computationWindowEndValue` / `minimumDuration` is negative. Rework #7 Commit 3. | Post-binding |

**Precedence rules** (evidence: `TierCreateRequestValidator.java:65–93`):
1. Pre-binding scans run BEFORE Jackson `treeToValue()`; unknown-but-unclassified keys fall through to Jackson strict-mode generic 400.
2. Scan order: **Class A (9011) → Class B (9012) → eligibilityCriteriaType (9013) → string sentinel (9015) → numeric sentinel (9016) → Jackson deserialise → post-binding 9014 → 9018 → BT-62 endDate ordering → renewal → 9017.**
3. Class A wins over sentinel on a combined payload (Class A scanner runs first).
4. Numeric `-1` (9016) fires BEFORE FIXED-family positive guard (9018) — `periodValue: -1` surfaces 9016, not 9018.

**Error body shape** (Rework Cycle 1 P1+P2 fix — codes 9011–9018 now appear on `errors[0].code`):

```json
{
  "data": null,
  "errors": [{ "code": 9011, "message": "Class A program-level field 'dailyDowngradeEnabled' is not allowed on per-tier write (use program config)" }],
  "warnings": null
}
```

For contract-hardening rejects (9011–9018): `errors[0].code` carries the numeric 4-digit code; `errors[0].message` is the descriptive text with the `[9011]` bracket prefix stripped. The bracket-prefix extractor in `TargetGroupErrorAdvice.handleInvalidInputException` performs the extraction — no `[901x]` text will appear in the wire `message` field. Evidence: `TargetGroupErrorAdvice.java` (bracket-extractor added Rework Cycle 1), `TierEnumValidation.java` (8 throw sites prefixed with `[9011]`–`[9018]`), `TierFacade.java` (widened signatures pass `rawBody` to validator).

**Evidence:** `TierController.java:92–105` (raw `JsonNode rawBody` binding + `objectMapper.treeToValue`); `TierCreateRequest.java` (no `downgrade` field); `TierCreateRequestValidator.java:65–93` (scan order); `TierEnumValidation.java` (8 constants + recursive scanners); `TierFacade.createTier` L226–L258; `TierValidationService.validateNameUniqueness` (409); `TierValidationService.assignNextSerialNumber` (50-cap).

---

## 5.4 `PUT /v3/tiers/{tierId}` — Update Tier

**Purpose:** Update a tier's configuration. Behaviour branches on current status.

**Maps to:** E1-US4 (Edit Tier), AC-4.1 through AC-4.7

### Request

| Parameter | Location | Type | Required | Description |
|---|---|---|:---:|---|
| `tierId` | path | `String` | **Yes** | Mongo `objectId` (preferred) or `tierUniqueId` |

**Body — `TierUpdateRequest`:** same shape as create, but **all fields are optional** (partial-update semantics). `programId` is NOT in the body — it cannot be changed. Same write-narrow contract as POST — `downgrade` is not accepted (rejected by Jackson strict-mode as an unknown property → generic HTTP 400; `downgrade` is NOT a Class A key and is NOT handled by code 9011). See §5.3 for the full 9011–9018 scanner table; the update validator wires the same pre-binding + post-binding scans in parity.

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

**Evidence:** `TierUpdateRequest.java` — no `downgrade` field; class annotated **`@JsonIgnoreProperties(ignoreUnknown = false)`** (Rework #6a R11-2 — tier-scoped annotation for PUT parity with POST; NOT the global `spring.jackson.deserialization.fail-on-unknown-properties` flag). `TierUpdateRequestValidator.java` wires the same 5 pre-binding + 3 post-binding scans as `TierCreateRequestValidator`. **Regression cover:** `TierUpdateRequestValidatorTest.shouldRejectLegacyDowngradeBlockAtJacksonBindingLayerOnPut()` (BT-197b PUT variant) empirically verifies the rejection on PUT round-trip vectors (GET → PUT same envelope); `shouldAcceptKnownFieldsAtJacksonBindingLayerOnPut()` is the negative control.

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
    "validity":     { "periodType": "FIXED", "periodValue": 12, "startDate": "2026-03-15T00:00:00+00:00", "endDate": null, "renewal": { "criteriaType": "Same as eligibility", "expressionRelation": null, "conditions": null } },
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
| `400` | **9011–9018** | Rework #6a contract-hardening rejects (Class A, Class B, `eligibilityCriteriaType`, `-1` sentinels, SLAB_UPGRADE `startDate`, FIXED missing `periodValue`, renewal drift) | See 9011–9018 code table in §5.3 |
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
  - The old ACTIVE's status is set to `SNAPSHOT` (preserved for audit history — filtered out of GET responses)
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

**Fields covered:** `TierEntry.tierStartDate`, `TierMeta.{createdAt, updatedAt, approvedAt, rejectedAt}`, `MemberStats.lastRefreshed`. All uniform as of 2026-04-21. (`KpiSummary.lastMemberCountRefresh` applied historically; `KpiSummary` is removed in Q27.)

**Evidence:** `TierDateFormat.java` (utility + serializer); `TierEntry.java` (tierStartDate serializer), `TierMeta.java` L27/L32/L37/L42, `MemberStats.java` L14.

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
| `engineConfig` | — | **Engine-internal.** UI must treat as opaque. Absent on `TierEntry` (GET responses). |
| `meta` | `TierMeta` | Audit block — §6.3. |
| `comments` | `String?` | Reviewer comment trail (most recent). |

---

### 6.2 `TierStatus` (enum)

```
DRAFT, PENDING_APPROVAL, REJECTED, ACTIVE, DELETED, SNAPSHOT, PUBLISH_FAILED
```

| Value | Wire? | Meaning |
|---|:---:|---|
| `LIVE` | ✅ (synthetic, read-only) | Synthetic wire value emitted on the `status` field of an entry built from a SQL `program_slabs` row. **Not** a member of the Java `TierStatus` enum — it is produced as a string literal by `TierEntryBuilder` / `SqlTierConverter.toEntry()` and has no corresponding stored state. |
| `DRAFT` | ✅ | Maker editing. Mutable via PUT. Can be submitted or deleted. Surfaces in the GET listing / detail arrays. |
| `PENDING_APPROVAL` | ✅ | Awaiting reviewer. Mutable via PUT (edit-in-place) but UI maker seat should treat as locked. Surfaces in the GET listing / detail arrays. |
| `REJECTED` | ✅ | Reviewer rejected the submission. The maker's doc is sent back with `rejectionComment` populated. First-class wire value (Q27/RJ-a). Surfaces in the GET listing / detail arrays so the maker can see and re-edit. |
| `ACTIVE` | ❌ | Server-internal only. Published to SQL `program_slabs`. On the wire the corresponding entry shows `status = "LIVE"` (built from the SQL row, not the Mongo ACTIVE doc). PUT creates a versioned-draft — ACTIVE row is not touched. |
| `DELETED` | ❌ | Soft-deleted. History retained. Filtered from GET responses. |
| `SNAPSHOT` | ❌ | Historical copy left when a versioned-draft was approved. Filtered from GET responses (use approval history endpoint). |
| `PUBLISH_FAILED` | ❌ | SAGA failure state. Best-effort saved when Thrift publish fails. Filtered from GET responses. Recovery flow deferred to a later epic. |

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
| `kpiType` | enum | `CURRENT_POINTS`, `CUMULATIVE_POINTS`, `CUMULATIVE_PURCHASES`, `TRACKER_VALUE_BASED` — matches engine `SlabUpgradeStrategy.CurrentValueType`. Writes to `SLAB_UPGRADE.propertyValues.current_value_type`. |
| `threshold` | `Integer` | ≥ 0 (zero accepted; negatives rejected) |
| `upgradeType` | enum | `EAGER`, `DYNAMIC`, `LAZY` — matches engine `SlabUpgradeMode` |
| `expressionRelation` | enum | `AND`, `OR` |
| `conditions` | `TierCondition[]` | See §6.8 |

---

### 6.5 `TierValidityConfig` on write — flattened `renewal` view on GET

> **Q27 wire rename (2026-04-23) + Rework #7 Commit 2 flatten (2026-04-23):** on **GET** responses this block is emitted as **`renewal`** at the tier-entry root (not `validity`). On write, clients continue to send it nested under `validity`. The GET read shape is a **flat** `TierRenewalView` that merges the period fields (from `TierValidityConfig`) and the renewal-trigger fields (from the nested `TierRenewalConfig`) into one block — no `renewal.renewal` nesting.

**On write (POST/PUT):** clients send the block under the key **`validity`** with the nested `renewal` sub-object (unchanged).

**On read (GET):** a single flat **`renewal`** block at the tier-entry root carries everything — period config, `criteriaType`, and Rework #7 renewal-trigger fields (`downgradeTo`, `shouldDowngrade`, `expressionRelation`, `conditions[]`).

```json
// GET read-side shape (on a TierEntry) — Rework #7 Commit 2 flattened view
// + Commit 3 advanced validity fields
{
  "renewal": {
    "periodType": "FIXED",
    "periodValue": 12,
    "renewalWindowType": "CUSTOM_PERIOD",
    "computationWindowStartValue": 3,
    "computationWindowEndValue": 12,
    "minimumDuration": 6,
    "criteriaType": "Same as eligibility",
    "downgradeTo": "SINGLE",
    "shouldDowngrade": true,
    "expressionRelation": "(PURCHASE AND VISITS) OR POINTS",
    "conditions": [
      { "type": "PURCHASE", "value": "2000" },
      { "type": "VISITS",   "value": "3"    },
      { "type": "POINTS",   "value": "1500" }
    ]
  }
}
```

```json
// POST/PUT write-side shape (inside the request body, unchanged — nested)
{
  "validity": {
    "periodType":  "FIXED",
    "periodValue": 12,
    "startDate":   "2026-04-21T00:00:00+00:00",
    "endDate":     null,
    "renewal":     {
      "criteriaType":       "Same as eligibility",
      "downgradeTo":        "SINGLE",
      "shouldDowngrade":    true,
      "expressionRelation": "(PURCHASE AND VISITS) OR POINTS",
      "conditions":         [ ... ]
    }
  }
}
```

| Field | Type | Allowed Values | Wire visibility |
|---|---|---|---|
| `periodType` | enum | `FIXED`, `SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`, `FIXED_CUSTOMER_REGISTRATION` — matches engine `TierDowngradePeriodConfig.PeriodType`. See semantics below. | Write + GET |
| `periodValue` | `Integer` | Positive integer; units are **months** regardless of `periodType`. | Write + GET |
| `startDate` | ISO-8601 | Validity period start. | **Write only** — stripped on GET (available as `tierStartDate` at tier-entry root) |
| `endDate` | — | Always `null` on responses (see key rules). | Never on GET (Decision V6) |
| `criteriaType` | `String` | Locked to `"Same as eligibility"` (Q26 B1a). | Write (nested under `renewal`) + GET (flattened) |
| `downgradeTo` | enum | `SINGLE`, `THRESHOLD`, `LOWEST`. Rework #7 Commit 1. | Write (nested under `renewal`) + GET (flattened) |
| `shouldDowngrade` | `Boolean` | Boxed — null omits field. Rework #7 Commit 1. | Write (nested under `renewal`) + GET (flattened) |
| `expressionRelation` | `String` (DNF) | DNF boolean — see §6.6. Rework #7 Commit 1. | Write (nested under `renewal`) + GET (flattened) |
| `conditions` | `TierCondition[]` | See §6.8 + §6.6. Rework #7 Commit 1. | Write (nested under `renewal`) + GET (flattened) |
| `renewalWindowType` | `String` enum | `FIXED_DATE_BASED` / `LAST_CALENDAR_YEAR` / `CUSTOM_PERIOD`. Engine `TierDowngradePeriodConfig.RenewalWindowType`. Rework #7 Commit 3. Invalid → 9022. | Write + GET |
| `computationWindowStartValue` | `Integer` (months) | Back-offset for window START. ≥ 0. Requires `renewalWindowType` (9023). Rework #7 Commit 3. | Write + GET |
| `computationWindowEndValue` | `Integer` (months) | Back-offset for window END. ≥ 0. Requires `renewalWindowType` (9023). Rework #7 Commit 3. | Write + GET |
| `minimumDuration` | `Integer` (months) | Minimum tier duration floor. ≥ 0. Standalone (no `renewalWindowType` coupling). Rework #7 Commit 3. | Write + GET |

**periodType semantics:**
- `FIXED` — validity lasts for `periodValue` months starting at `startDate`. The most common choice for a classic "expires after N months" tier.
- `SLAB_UPGRADE` — validity is tied to the slab-upgrade lifecycle: the tier stays valid as long as the member remains eligible under the upgrade KPI. No hard expiry date. Expect this on legacy tiers that were written directly through the engine (e.g. tiers 4006/4007 in sample programs).
- `SLAB_UPGRADE_CYCLIC` — cyclic variant of `SLAB_UPGRADE`: validity extends on each qualifying upgrade event, effectively renewing the window on every KPI trigger.
- `FIXED_CUSTOMER_REGISTRATION` — `FIXED` but anchored to the member's **registration date** rather than tier-join date. Used when the program requires uniform cohort-based validity windows.

> `periodType` is a **validity-strategy enum**, not an event. A `SLAB_UPGRADE` value on read does not mean "an upgrade just happened" — it means "validity is governed by the slab-upgrade rule." This is the contract whether the tier came from a v3 write or was written pre-v3 directly to the engine.

**Key rules:**
- `endDate` is **always `null` on responses**. It is derived as `startDate + periodValue` if the UI needs it.
- On **GET**, the `renewal` block is a flat `TierRenewalView` (Rework #7 Commit 2). No `renewal.renewal` nesting — all fields surfaced at the same level.
- On **write** (POST/PUT), the `renewal` sub-object stays nested under `validity`. If the client omits it, the server fills the default (`criteriaType = "Same as eligibility"`) before persistence.
- **Slab 1 (base tier) has no validity block.** The engine treats slab 1 as the always-valid entry state, so `renewal` is absent on GET entries for it — don't mistake the absence for a drift.
- **Precedence on GET** — when a renewal-trigger field could be sourced from either the Mongo-doc nested renewal (maker's POST intent) or the engine-derived `TierDowngradeSlabConfig` (LIVE tiers), the nested renewal wins. Engine is the fallback for LIVE entries where the nested renewal was synthesised with only the B1a default.

---

### 6.6 `TierRenewalConfig` — write-only (not emitted on GET)

```json
{
  "criteriaType":       "Same as eligibility",
  "downgradeTo":        "SINGLE",
  "shouldDowngrade":    true,
  "expressionRelation": "(PURCHASE AND VISITS) OR POINTS OR (TRACKER AND POINTS)",
  "conditions": [
    { "type": "PURCHASE", "value": "2000" },
    { "type": "VISITS",   "value": "3"    },
    { "type": "POINTS",   "value": "1500" },
    { "type": "TRACKER",  "value": "10",  "trackerName": "store_visits_q1" }
  ]
}
```

> **Q27 GET drop (2026-04-23):** this nested block is **not emitted on GET responses**. The Java field `TierValidityConfig.renewal` is preserved on the server (the write path still uses it, and persistence still stores it) but is nulled out before serialisation on the read path so that `@JsonInclude(NON_NULL)` omits it from the wire. See §6.5 for the GET shape.

| Field | Type | Required | Allowed values | Engine mapping |
|---|---|:---:|---|---|
| `criteriaType` | `String` | Yes (if `renewal` sent) | **`"Same as eligibility"` only** (Q26 B1a lock preserved) | Wire-only marker — engine has no slot. Any drift → **9017**. |
| `downgradeTo` | `String` enum | No (Rework #7) | `SINGLE` / `THRESHOLD` / `LOWEST` | `TierDowngradeSlabConfig.downgradeTarget` per-slab. Runtime consumer: `peb BaseCalculatorBuilder:182-201`. Invalid value → **9019**. |
| `shouldDowngrade` | `Boolean` | No (Rework #7) | `true` / `false` (boxed — null omits) | `TierDowngradeSlabConfig.shouldDowngrade` per-slab. `false` disables auto-downgrade for this tier. |
| `expressionRelation` | `String` (DNF boolean) | No (Rework #7) | Grammar: `group (OR group)*`, `group = '(' kpi (AND kpi)* ')' \| kpi (AND kpi)*`. KPI ∈ `{PURCHASE,VISITS,POINTS,TRACKER}`. Strict parens when mixing AND+OR at top level. Case-insensitive on write; canonicalised to uppercase on read. | `slab.conditions.expression_relation` (engine bracket format — `"[[purchase,numVisits],[points]]"` — serialised via `TierRenewalExpressionParser`). Runtime consumer: `TrackerService:236-237`. |
| `conditions[].type` | `String` enum | No (Rework #7) | `PURCHASE` / `VISITS` / `POINTS` / `TRACKER` | Per-element — `PURCHASE`→`slab.conditions.purchase`, `VISITS`→`numVisits`, `POINTS`→`points`, `TRACKER`→`slab.conditions.tracker[]` entry. |
| `conditions[].value` | `String` (numeric) | No | ≥ 0 | Integer after parse. |
| `conditions[].trackerName` | `String` | Only when `type=TRACKER` | — | `slab.conditions.tracker[].name`. |

**Rework #7 Commit 1 (2026-04-23) — Per-tier engine-backed renewal fields:**
`downgradeTo`, `shouldDowngrade`, `expressionRelation`, and `conditions[]` are now accepted on write and wired to the engine's per-slab `TierDowngradeSlabConfig` via `TierStrategyTransformer.synthesiseDowngradeFromRenewal` at APPROVE time. See §10.20 for the wiring details.

**Multi-tracker rejection (9020):** `conditions[]` may contain at most one entry with `type=TRACKER` — mirrors Q5c eligibility multi-tracker rejection. Follow-up epic will lift both at once.

**Criteria-type lock (Q26 B1a preserved):** The engine still has no storage slot for an alternate `criteriaType` value. Renewal fires implicitly via `UpgradeSlabActionImpl:815` whenever upgrade evaluation resolves to the customer's current slab. `"Same as eligibility"` remains the only accepted value.

**Dropped from v3.1:** `schedule` field (previously a free-text display string; the engine stripped it on write so it never reached SQL).

---

### 6.7 `TierDowngradeConfig` — **read-only on the tier contract**

> **Rework #6a (ADR-21R) — write-narrow / read-wide:** `TierDowngradeConfig` appears on **GET** responses (List, Detail, Submit, Approve, Approvals queue) but is **rejected on POST/PUT**. The bare `downgrade` key is rejected by Jackson strict-mode deserialization (generic HTTP 400; `downgrade` is NOT in `CLASS_A_CANONICAL_KEYS`). If the nested object carries any of the 8 Class A orchestration flags, the recursive pre-binding scanner catches them first → code **9011**. See §5.3 (error code table), §10.19 (asymmetry explained), and §6.11 (envelope model) for the read-side contract. Class retained as `TierDowngradeConfig.java` — used only by `TierStrategyTransformer` on the read path.

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

**Population source:** Derived by `TierStrategyTransformer` from the engine's `SLAB_DOWNGRADE` strategy row (MySQL `strategies` table) at read time. For legacy SQL-only tiers (LIVE entries with no paired Mongo doc), this is synthesised from `program_slabs` + `program_downgrade_config`. For Mongo-origin draft entries, the stored value is echoed unchanged (may be `null` pre-approval).

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

### 6.10 `KpiSummary` — **REMOVED (Q27, 2026-04-23)**

> The `summary` block (count + member aggregation) is **dropped from the list response** in the Q27 pivot. The GET listing body is now simply `{ "tiers": TierEntry[] }` with no KPI envelope around it — counts and member totals move to a dedicated endpoint (or are computed client-side from the flat list). The Java class `KpiSummary` and the facade method `computeTotalMembers()` are deleted. This eliminates the longstanding ambiguity where `totalMembers = null` (for `LEGACY_SQL_ONLY`) had to be rendered as `—` by every consumer.

---

### 6.11 `TierEntry` — the read shape (replaces `TierEnvelope` + `TierView`)

> **Q27 pivot (2026-04-23):** the paired-envelope model (one `TierEnvelope` per `slabId`, with `live` + `pendingDraft` sub-blocks and a computed flatten) is **replaced** by a flat entry. The GET listing returns `List<TierEntry>` — up to **two entries per `slabId`**, one per state (LIVE and in-flight). Pairing is done by the UI using the shared `slabId` field. See §5.1 for the listing contract and §5.2 for the detail contract.

A `TierEntry` is a single flat record. There is no `live` / `pendingDraft` wrapper, no `origin`, no `hasPendingDraft`. The `status` field identifies which state this entry represents; entries for the same logical tier share a `slabId`.

**Shape (JSON wire):**

```json
{
  "status":           "LIVE",                  // see §6.2 — LIVE | DRAFT | PENDING_APPROVAL | REJECTED
  "slabId":           3850,                    // null only for brand-new DRAFTs (no SQL row yet)
  "tierUniqueId":     null,                    // null on LIVE-only entries; populated on every draft entry
  "name":             "Gold",
  "description":      "Premium tier",
  "color":            "#FFD700",
  "serialNumber":     2,
  "tierStartDate":    "2026-03-15T08:14:02+00:00",  // LIVE entries only (SQL program_slabs.created_on)
  "eligibility":      { "...": "see §6.4" },
  "renewal":          { "...": "see §6.5 (GET shape — periodType / periodValue / startDate / endDate)" },
  "downgrade":        { "...": "see §6.7 (read-only)" },
  "rejectionComment": null,                    // populated only on REJECTED entries
  "meta":             { "...": "see §6.3 — createdBy/At + updatedBy/At only on the wire" }
}
```

**Field reference:**

| Field | Type | Wire behaviour |
|---|---|---|
| `status` | `String` | `"LIVE"` on SQL-origin entries (synthetic marker); `"DRAFT"` / `"PENDING_APPROVAL"` / `"REJECTED"` on Mongo-origin entries. Always present. |
| `slabId` | `Long?` | The SQL `program_slabs.id`. Non-null on LIVE entries and on edit-of-LIVE draft entries. **Null** on brand-new DRAFT entries (no SQL row yet). Used by UI to pair two entries of the same tier. |
| `tierUniqueId` | `String?` | Mongo-side stable id. **Null** on LIVE entries that have no paired Mongo doc (legacy SQL-only tiers). Non-null on every Mongo-origin entry (DRAFT / PENDING_APPROVAL / REJECTED). |
| `name`, `description`, `color`, `serialNumber` | shared | Always present. |
| `tierStartDate` | ISO-8601? | **LIVE entries only.** Serialised via `TierDateFormat.Serializer`. Absent on draft entries. |
| `eligibility` | `TierEligibilityConfig` | See §6.4. |
| `renewal` | `TierValidityConfig` flat | See §6.5. Wire key is `renewal`; the nested `renewal` sub-block (the old `TierRenewalConfig`) is suppressed on GET. Absent on slab 1. |
| `downgrade` | `TierDowngradeConfig` | See §6.7 — read-only, rejected on write. |
| `rejectionComment` | `String?` | Populated only when `status = REJECTED` (and the maker is viewing the bounce-back). Absent otherwise. |
| `meta` | `TierMeta` | Wire trimmed to `createdBy` / `createdAt` / `updatedBy` / `updatedAt` only (M-b lock). Server-internal fields (e.g. `basisSqlSnapshot`, rejection audit) are preserved in Java but not serialised. |

**Removed from the earlier envelope contract (Q27 drops):**
- `TierEnvelope` class — deleted.
- `TierView` class — deleted (fields folded into `TierEntry`).
- `TierOrigin` enum (`BOTH` / `MONGO_ONLY` / `LEGACY_SQL_ONLY`) — deleted. Origin is no longer surfaced on the wire; callers infer it from `status` + `slabId` + `tierUniqueId` presence.
- `hasPendingDraft` convenience flag — deleted. Callers detect pairing by grouping entries on `slabId`.
- `live` / `pendingDraft` sub-blocks — deleted. No more nested read shape.
- `draftStatus` field — deleted. Folded into the single `status` discriminator.

**Pairing inference rule (for UI):**

Group entries by `slabId`. For a given `slabId`:
- **1 LIVE entry** → LIVE only (scenario: published tier with no in-flight edit).
- **1 LIVE + 1 draft entry (same `slabId`)** → edit-of-LIVE. Draft's `status` tells you what stage (`DRAFT` / `PENDING_APPROVAL` / `REJECTED`).
- **1 draft entry with `slabId = null`** → brand-new DRAFT (no LIVE row yet). Identify it by the null `slabId`; pair it within the UI using `tierUniqueId` if needed.
- **2 draft entries with the same `slabId`** → should never happen post-F-15 (partial unique index enforces at most one in-flight doc per slabId). The defensive behaviour in `TierEntryBuilder` is "last one wins on the pending side"; log a server warning.

**Implementing classes:** `TierEntry.java` (new — package `com.capillary.intouchapiv3.tier.entry`), `TierEntryBuilder.java` (new — same package), `SqlTierConverter.toEntry()` (renamed from `toView()`).

---

## 7. Enums and Constants

| Enum | Values | Notes |
|---|---|---|
| `TierStatus` | `DRAFT`, `PENDING_APPROVAL`, `REJECTED`, `ACTIVE`, `DELETED`, `SNAPSHOT`, `PUBLISH_FAILED` | On the wire (GET): `"LIVE"` (synthetic — SQL rows), `"DRAFT"`, `"PENDING_APPROVAL"`, `"REJECTED"`. `ACTIVE` is server-internal — SQL rows surface as `"LIVE"`. `DELETED` / `SNAPSHOT` / `PUBLISH_FAILED` are filtered from GET. See §6.2. |
| `ApprovalAction` | `APPROVE`, `REJECT` | Used in `approvalStatus` body field on `/approve`. Case-insensitive. |
| `KpiType` | `CURRENT_POINTS`, `CUMULATIVE_POINTS`, `CUMULATIVE_PURCHASES`, `TRACKER_VALUE_BASED` | `eligibility.kpiType`. Engine canonical: `SlabUpgradeStrategy.CurrentValueType`. |
| `UpgradeType` | `EAGER`, `DYNAMIC`, `LAZY` | `eligibility.upgradeType`. Engine canonical: `SlabUpgradeMode`. |
| `PeriodType` | `FIXED`, `SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`, `FIXED_CUSTOMER_REGISTRATION` | `renewal.periodType` on GET (`validity.periodType` on write). Engine canonical: `TierDowngradePeriodConfig.PeriodType`. See §6.5 for semantics. |
| `ExpressionRelation` | `AND`, `OR` | `eligibility.expressionRelation` |
| `DowngradeTarget` | `SINGLE`, `THRESHOLD`, `LOWEST` | `downgrade.target` on **read** responses only (see §6.7, §10.19 — rejected on write). Engine canonical: `TierDowngradeTarget`. |
| `ConditionType` | `PURCHASE`, `VISITS`, `POINTS`, `TRACKER` | `TierCondition.type`. Used in `eligibility.conditions[]` (write + read) and `downgrade.conditions[]` (**read-only**). |
| ~~`TierOrigin`~~ | — | **Removed (Q27).** The enum and the `origin` wire field are deleted; callers infer origin from `status` + `slabId`/`tierUniqueId` presence. |

---

## 8. Status Display Guide for UI

| Status | User-Facing Label | Colour Suggestion | Editable? | Deletable? | Notes |
|---|---|---|---|---|---|
| `DRAFT` | Draft | Gray | Yes (in-place) | Yes | Can submit for approval. May carry `rejectionComment` if a reviewer previously rejected it. |
| `PENDING_APPROVAL` | Pending Approval | Yellow / Amber | Technically yes (in-place) — UI should treat as locked | No | Can approve or reject |
| `ACTIVE` | Active | Green | Yes (creates versioned draft) | No | Live in SQL. Members enrolled. |
| `DELETED` | Deleted | Dark Gray | No | No | Soft-deleted; retained for audit. **Do not surface in UI lists.** |
| `SNAPSHOT` | (hidden) | — | No | No | Internal maker-checker history. **Do not display.** |
| `PUBLISH_FAILED` | (hidden today) | — | No | No | SAGA failure. Filtered from GET responses. Recovery flow deferred. |

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
                                           │ SNAPSHOT │ (filtered from GET responses)
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

If `status` (non-empty list) is sent on list, the method short-circuits to `{ tiers: [] }`. **Omit the `status` query param** on `GET /v3/tiers`. Filter client-side on the entries by their `status` field (`"LIVE"` / `"DRAFT"` / `"PENDING_APPROVAL"` / `"REJECTED"`) if needed.

### 10.3 ~~`totalMembers` can be `null`~~ **(removed — Q27)**

> This note applied to the old `KpiSummary.totalMembers` field on the list response. The summary block was dropped in Q27; there is no longer a `totalMembers` on the wire. If the UI needs a member count it will come from a dedicated endpoint (not yet defined).

### 10.4 `PUBLISH_FAILED` is a real status

If the Thrift publish during APPROVE fails, the tier is best-effort saved with `status = PUBLISH_FAILED` before the exception propagates (HTTP 500 with the generic message). **`PUBLISH_FAILED` tiers do not appear in list or detail responses** — the `TierEntryBuilder.isWorkflowVisible` filter excludes them. They may resurface once recovery flow ships (deferred).

### 10.5 Detail by numeric `slabId` now supported

> **Q27 reversal (2026-04-23):** this previously noted "numeric slabId returns 404". Under the Q27 contract the detail endpoint now **does** accept numeric paths — see §5.2. Numeric `{tierId}` resolves to an array of 1 LIVE entry (or 1 LIVE + 1 paired in-flight entry). 404 is returned only when the `slabId` is not found for the caller's org. String `tierUniqueId` is also accepted and returns a draft-only array of 1.

### 10.6 Unknown `approvalStatus` is a 500, not a 400

`TierFacade.handleApproval` accepts only `"APPROVE"` / `"REJECT"` (case-insensitive). Any other value raises `IllegalArgumentException` — unmapped by the global advice, falls through to `genericExceptionHandler` → HTTP 500 with the generic `"Something went wrong..."` message. **Validate on the client before calling.**

### 10.7 Concurrency / race windows on list

`listTiers` runs three non-transactional round-trips (1 SQL + 2 Mongo). Observable races:
- A tier just published may be missing for one poll cycle.
- A newly-created DRAFT always appears (safe).
- A just-deleted DRAFT may appear; a subsequent edit/approve call on it will 404 (or 200 with errors on `/submit`-`/approve`). **UI must defensively handle "id from last list no longer exists".**

### 10.8 `rejectionComment` on a REJECTED entry

> **Q27 update (2026-04-23):** under the old envelope contract the bounce-back doc was demoted to `DRAFT` with `rejectionComment` stamped on the pendingDraft side. Under the Q27 contract a rejected doc surfaces as its own entry with **`status = "REJECTED"`** and a populated `rejectionComment` field. The maker seat renders the rejection reason on that entry; when the maker re-edits, the server transitions the doc back through `DRAFT` (existing write flow — unchanged).

### 10.9 `engineConfig` is on `UnifiedTierConfig` but NOT on `TierEntry`

`TierEntry` deliberately omits `engineConfig`. The list and detail endpoints (which return `List<TierEntry>`) never expose engine internals. **If you see `engineConfig` on a payload, you are looking at a create/update/approve response** (which returns `UnifiedTierConfig`), not a read response.

### 10.10 `basisSqlSnapshot` is server-internal

Exposed on `TierMeta` for debuggability but carries no UI meaning. It is a frozen SQL row used by `TierDriftChecker` at approval time. **Do not render it, do not diff against it from the client.**

### 10.11 `Idempotency-Key` header is reserved, not implemented

`POST /v3/tiers` accepts the header and silently drops it. **Do not rely on it for safe retry.** Use the 409-on-duplicate-name check as your retry guard.

### 10.12 Validator codes 9001–9010 are dead; 9011–9018 emit on both `code` and `message`

**Codes 9001–9010** — declared as `public static final int` constants in `TierCreateRequestValidator` but never passed to any `throw`. `errors[0].code` will be `null` — **never 9001–9010**.

**Codes 9011–9018** (Rework #6a contract-hardening, active after Rework Cycle 1 P1+P2 fix):

- `errors[0].code` — the numeric 4-digit code (e.g. `9011`). Wire shape is `Long` (per `ResponseWrapper.ApiError`). Match on this field for programmatic routing.
- `errors[0].message` — the descriptive text with the `[9011]`–`[9018]` bracket prefix **stripped**. Example: `"Class A program-level field 'dailyDowngradeEnabled' is not allowed on per-tier write (use program config)"`.

**Implementation:** `TierEnumValidation.java` throw sites embed `[901x]` as a bracket prefix in the message string. `TargetGroupErrorAdvice.handleInvalidInputException` extracts the numeric code via regex `^\[(\d+)\]\s*(.*)$` and constructs `ApiError(code, strippedMsg)` directly — bypassing `MessageResolverService` (which returns `999999` for unregistered i18n keys).

**UI guidance:** Use `errors[0].code` for programmatic error routing. `errors[0].message` is the human-readable description (bracket-stripped). For codes 9001–9010: `errors[0].code` is `null`; match on `errors[0].message` content if needed.

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

### 10.18 `eligibility.expressionRelation` is a dormant reserved slot

The `eligibility.expressionRelation` field on the request/response shape is **declared but never used** in the current backend. It is reserved for a future compound-condition feature that was deferred.

| Aspect | Behaviour today | Evidence |
|---|---|---|
| On `POST` / `PUT` request body | Accepted, deserialised, then **silently dropped** — no validator checks it, no transformer reads it, no persistence layer uses it for logic. | Zero matches for `getExpressionRelation()` / `setExpressionRelation` / `.expressionRelation(` in the tier write path (`TierStrategyTransformer`, `TierCreateRequestValidator`, `TierUpdateRequestValidator`, `TierFacade`). |
| On `GET` LIVE entry (SQL-origin) | Always `null` → **omitted** from wire via `@JsonInclude(NON_NULL)`. `TierStrategyTransformer.extractEligibilityForSlab` does not populate it — the engine has no per-tier source. | `TierEligibilityConfig.java` class Javadoc (L19–24); `TierStrategyTransformer.java` Javadoc on `extractEligibilityForSlab`. |
| On `GET` DRAFT response (Mongo origin) | Echoes whatever the maker originally sent on `POST` / `PUT` — Mongo persists the DTO as-is. Carries no semantic meaning end-to-end. | Mongo `@Document` round-trip; no read-side consumer. |

**UI guidance:**

- **Don't render `eligibility.expressionRelation`** — treat it as absent. On LIVE tiers it will not be on the wire at all; on DRAFT tiers any stored value is stale / unprocessed.
- **Don't send it** on create/update — it will be silently dropped. If the field appears in a form today, hide it until the backend advertises support.
- **Contrast with `renewal.expressionRelation`** — that sister field is actively **rejected** on write by `TierRenewalValidation` (non-null → 400 with `"renewal.expressionRelation must be null — reserved for a future engine-side renewal rule (Rework #5 B1a)"`). The eligibility-side field has no such guard today; this asymmetry is tracked for a future hardening pass.
- **Engine-internal `EngineConfig.expressionRelation`** is a completely separate field (type `List<List<Integer>>` — a condition-grouping matrix used inside the engine). Not on `TierEntry`; not UI-facing; not related to this slot.

### 10.19 Write-narrow / Read-wide asymmetry — `downgrade` and engine-derived fields (Rework #6a ADR-21R)

The tier contract is **asymmetric** between write and read:

| Field | POST / PUT (write) | GET (read) |
|-------|-------------------|-----------|
| `downgrade` (`TierDowngradeConfig`) | **Rejected** — Jackson strict-mode `UnrecognizedPropertyException` → **HTTP 400 (generic, not 9011)**. `downgrade` is NOT in `CLASS_A_CANONICAL_KEYS`. Nested Class A keys inside a `downgrade` object trigger 9011 via recursive scan. | **Present** — derived from engine strategies at APPROVE time, surfaced via `TierStrategyTransformer` |
| `eligibilityCriteriaType` | **Rejected** — code **9013** | May be present on legacy SQL-origin reads |
| `validity.periodValue` for SLAB_UPGRADE family | Not required (event-driven) | May be present on read (engine-populated) |
| `validity.startDate` for SLAB_UPGRADE family | **Rejected** — code **9014** | May be present on read for FIXED family only |
| Class A program-level keys (reminders, retainPoints, isDowngradeOnReturnEnabled, etc.) | **Rejected** — code **9011** | Not on `TierEntry` (live at `EngineConfig` / program-level) |

**Rationale (ADR-21R):** Tier-scoped writes must not carry program-level orchestration flags or engine-derived state. The engine owns downgrade behaviour; the tier write path is a thin DRAFT-intent. Read responses remain wide to keep the UI's rendering code stable — the UI continues to render the full entry shape (including `downgrade`) regardless of whether it was written through this API or seeded from engine sync.

**Why this matters for the UI:**
- On **write** forms, the downgrade panel must be a **no-op** — do not include the `downgrade` object in the POST/PUT body. If a maker edits downgrade settings in the UI, that edit surfaces through a separate program-level endpoint (not the tier endpoint).
- On **read**, `downgrade` remains populated on `UnifiedTierConfig` and `TierEntry` (§6.7) — the UI's existing render code stays unchanged.
- A **round-trip** of a GET response back to POST/PUT will **fail with HTTP 400** — Jackson strict-mode rejects the bare `downgrade` key as an unknown property (`UnrecognizedPropertyException`). The error code is a generic 400, **not** 9011. Strip the `downgrade` key client-side before round-tripping. (If the engine ever surfaces `downgrade.isActive` or any other Class A flag on a read, the recursive pre-binding scanner would additionally trigger code 9011 — but today the engine does not surface those keys on reads.)

**Evidence:** `TierCreateRequest.java` / `TierUpdateRequest.java` — no `downgrade` field; both DTO classes annotated **`@JsonIgnoreProperties(ignoreUnknown = false)`** (Rework #6a R11-2 — tier-scoped annotation on the write DTOs; read DTOs `TierListResponse.java` and (historically) `KpiSummary.java` were deliberately NOT annotated so new engine-derived read-side fields can roll in without breaking the UI. Q27: `KpiSummary.java` is deleted; `TierListResponse.java` now wraps only `List<TierEntry>`. `TierEntry.java` is also not annotated). This is NOT the global `spring.jackson.deserialization.fail-on-unknown-properties` flag — tier-scoped annotation defends against environment drift in the global Spring Boot setting. `TierDowngradeConfig.java` retained for read; `TierStrategyTransformer` populates downgrade on read; `TierEnumValidation.CLASS_A_CANONICAL_KEYS` enumerates the rejected keys. **Regression cover (BT-197b, POST + PUT):** `TierCreateRequestValidatorTest.shouldRejectLegacyDowngradeBlockAtJacksonBindingLayer()` and `TierUpdateRequestValidatorTest.shouldRejectLegacyDowngradeBlockAtJacksonBindingLayerOnPut()` empirically verify the binding-layer rejection on both verbs with negative controls.

---

### 10.20 Per-tier renewal-backed downgrade synthesis (Rework #7 Commit 1 — 2026-04-23)

`downgrade` remains rejected on write (§10.19), but the engine's per-slab downgrade configuration — `TierDowngradeSlabConfig` (pointsengine-emf) — is now reachable via `validity.renewal.*`.

**Wire ↔ Engine mapping (APPROVE-time):**

| Wire path (`validity.renewal.*`) | Engine field (`TierDowngradeSlabConfig.*`) | Runtime consumer |
|---|---|---|
| `downgradeTo` (`SINGLE`/`THRESHOLD`/`LOWEST`) | `downgradeTarget` (enum) | `peb BaseCalculatorBuilder:182-201` — switch picks per-slab calculator bean |
| `shouldDowngrade` (Boolean) | `shouldDowngrade` (boolean) | `AbstractTierDowngradeCalculator` gate |
| `conditions[].type=PURCHASE, value=N` | `conditions.purchase` (int) | `AbstractTierDowngradeCalculator:357-397` |
| `conditions[].type=VISITS, value=N` | `conditions.numVisits` (int) | same |
| `conditions[].type=POINTS, value=N` | `conditions.points` (int) | same |
| `conditions[].type=TRACKER, value=N, trackerName=X` | `conditions.tracker[]` entry (`{name: X, trackedValue: N}`) | `AbstractTierDowngradeCalculator:397` |
| `expressionRelation` (DNF string — `"(PURCHASE AND VISITS) OR POINTS"`) | `conditions.expression_relation` (engine bracket format — `"[[purchase,numVisits],[points]]"`) | `TrackerService:236-237` — engine parses via `PointsEngineUtils.parseExpressionRelation`; runtime evaluates OR-of-AND |

**DNF grammar for `renewal.expressionRelation`:**

```
expression := group ( 'OR' group )*
group      := '(' and_group ')'  |  and_group
and_group  := kpi ( 'AND' kpi )*
kpi        := 'PURCHASE' | 'VISITS' | 'POINTS' | 'TRACKER'
```

Rules:
1. Strict parens when mixing AND + OR at the top level — `"PURCHASE AND VISITS OR POINTS"` rejected as ambiguous; write `"(PURCHASE AND VISITS) OR POINTS"` or `"PURCHASE AND (VISITS OR POINTS)"`.
2. Case-insensitive on write; canonicalised to uppercase on read.
3. Every KPI token must correspond to a type in `renewal.conditions[]`.
4. Empty-string / null `expressionRelation` → no expression written to engine.

**Serialisation — wire DNF ↔ engine bracket format** (via `TierRenewalExpressionParser`):

| Wire DNF | Engine bracket |
|---|---|
| `"PURCHASE AND VISITS"` | `"[[purchase,numVisits]]"` |
| `"PURCHASE OR VISITS OR POINTS"` | `"[[purchase],[numVisits],[points]]"` |
| `"(PURCHASE AND VISITS) OR POINTS"` | `"[[purchase,numVisits],[points]]"` |
| `"(PURCHASE AND VISITS) OR POINTS OR (TRACKER AND POINTS)"` | `"[[purchase,numVisits],[points],[1,points]]"` |

Wire-KPI → engine-name mapping: `PURCHASE→purchase`, `VISITS→numVisits`, `POINTS→points`, `TRACKER→"1"` (1-based tracker index; multi-tracker rejected at 9020).

**Canonical output on read** (for wire round-trip stability):
- Single group with single KPI → bare KPI (no parens)
- Single group with multiple KPIs → AND-list (no outer parens)
- Multiple single-KPI groups → OR-list (no parens)
- Multi-group with any multi-KPI group → multi-KPI groups get parens; singleton groups don't

**Synthesis flow:**
1. POST `/v3/tiers` arrives with `validity.renewal.downgradeTo` / `.conditions[]` / `.expressionRelation` (DNF string) / `.shouldDowngrade`.
2. `TierCreateRequestValidator` + `TierRenewalValidation` accept the shape — `expressionRelation` parsed by `TierRenewalExpressionParser` (grammar + KPI enum + referential check against `conditions[]`); rejects with code 9021 on any violation. Multi-tracker rejected at 9020. Downgrade-to enum rejected at 9019.
3. `TierFacade.createTier` persists the DRAFT to Mongo — `TierRenewalConfig` fields round-trip through standard Spring Data serialization, carrying the DNF string verbatim.
4. On SUBMIT → APPROVE, `TierApprovalHandler.applyDowngradeDelta` checks `entity.getDowngrade()`. Pre-Rework #7 this was always null (since Q11 hard-flip removed `downgrade` from the write DTO). Rework #7 adds a fallback: if `entity.getDowngrade()` is null, call `TierStrategyTransformer.synthesiseDowngradeFromRenewal(entity.getValidity().getRenewal())` and use the synthesised `TierDowngradeConfig`.
5. `TierStrategyTransformer.buildConditionsObject` calls `TierRenewalExpressionParser.toEngineBracket(...)` to translate the DNF string to the engine's bracket format, then writes it as `slabs[n].conditions.expression_relation` alongside `slabs[n].downgradeTarget`, `slabs[n].shouldDowngrade`, `slabs[n].conditions.{purchase, numVisits, points, tracker[]}`.
6. **Rework #7 Commit 2 (2026-04-23):** `TierApprovalHandler.applyValidityDelta` — newly activated alongside `applyDowngradeDelta` — writes the draft's `validity.{periodType, periodValue, startDate}` into the engine's `slabs[n].periodConfig`. This closes the pre-existing per-slab validity dead-wire gap (the validator accepted these fields and they were persisted to Mongo, but pre-Commit-2 they never reached the engine at APPROVE). The overlay uses **null-as-preserve** semantics — a null field on the DRAFT leaves the engine-side value intact (safe for edit-of-LIVE / versioned PUT where the DRAFT may carry only a subset). `applySlabValidityDelta` is permissive on APPEND — creates a bare slab entry if `applyDowngradeDelta` was a no-op. UPDATE path includes a legacy-gap recovery — retries as APPEND if the engine-side slab lacks `periodConfig` (legacy tier that predates Commit 2).
7. **Rework #7 Commit 3 (2026-04-23):** four additional per-tier engine-backed validity fields (`renewalWindowType`, `computationWindowStartValue`, `computationWindowEndValue`, `minimumDuration`) are now accepted on the write path and carried through the same `applyValidityDelta` flow. They write to `slabs[n].periodConfig.{renewalWindowType, computationWindowStartValue, computationWindowEndValue, minimumDuration}` with the same null-as-preserve semantics. Runtime consumers: `peb TierDowngradeDateHelper:33-66` (window type + offsets govern evaluation-window date math) + every downgrade date calculator (`FixedTierDowngradeDateCalculator`, `CyclicTierDowngradeDateCalculator`, `SlabUpgradeBasedTierDowngradeDateCalculator`, `FixedCustomerRegistrationTierDowngradeDateCalculator` — all enforce `minimumDuration`). Atomic coupling: `computationWindow*` requires `renewalWindowType` (code 9023) — offsets are inert on the engine without a window type.
8. Atomic Thrift publish via `createSlabAndUpdateStrategies` — engine picks up the per-slab fields and uses them at runtime for downgrade-calculator dispatch, renewal evaluation, renewal-window date math, minimum-duration floor enforcement, and downgrade-date calculation.

**What does NOT happen (safety):**
- If `validity.renewal` is null, or carries only `criteriaType`, `synthesiseDowngradeFromRenewal` returns null and the SLAB_DOWNGRADE strategy is left byte-untouched — pre-Rework #7 no-op behaviour for POSTs without any of the new fields.
- Program-level booleans (`reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, etc.) are still rejected (9011) on per-tier write — unchanged by Rework #7.
- `downgrade` block at the root is still rejected by Jackson strict-mode (generic 400) — unchanged.

**Read path:** engine JSON → wire surfaces `downgrade.target`, `downgrade.shouldDowngrade` (when set), `downgrade.conditions[]` via `TierStrategyTransformer.extractDowngradeForSlab`. The `downgrade` block on GET responses (§6.7) continues to carry these fields — unchanged for UI consumers. Rework #7 additionally surfaces `shouldDowngrade` and `expressionRelation` on this block when present on the engine side (round-trip symmetry).

**Regression cover:**
- `TierRenewalValidationTest` — 51 tests covering BT-197 through BT-212 (incl. BT-198 downgradeTo enum, BT-199 shouldDowngrade both-values, BT-200 per-type conditions with DNF, BT-201 single TRACKER, BT-202 full envelope with DNF, BT-203 backward-compat canonical shape, BT-211 DNF grammar acceptance suite covering 12 valid shapes, BT-212 DNF rejection suite covering 8 invalid shapes with code 9021, plus 9019 / 9020 negative cases)
- `TierStrategyTransformerTest` — 93 tests incl. BT-204 through BT-215 (incl. synthesis-copies-all-fields, synthesis-returns-null-when-no-engine-fields, shouldDowngrade round-trip, DNF-AND serialises to `"[[a,b]]"` round-trip, DNF-OR serialises to `"[[a],[b]]"` round-trip, mixed DNF with canonical parens, three-group DNF with TRACKER reference, lowercase input canonicalised to uppercase, malformed engine expression surfaces as null, null-expression-relation-omitted, pre-Rework-7-shape-unchanged); plus Rework #7 Commit 2 additions — APPEND on missing slab creates a bare entry with periodConfig (permissive isAppend semantics)
- `TierApprovalHandlerTest` — 31 tests incl. Rework #7 Commit 2 BT-221 through BT-224 (writeValidityPeriodConfigToEngineOnCreate, updateExistingPeriodConfigOnVersionedEdit with null-as-preserve + engine-field preservation, leaveEnginePeriodConfigUntouchedWhenDraftHasNoValidity, recoverLegacyTierMissingPeriodConfigByRetryingAsAppendOnUpdate)
- `TierValidatorEnumTest` — 84 tests incl. Rework #7 Commit 3 BT-225 through BT-230 (all 3 canonical renewalWindowType values accepted, phantom values rejected with 9022, atomic-coupling rejections for computationWindowStart/End without renewalWindowType at 9023, negative-value rejections on all 3 numeric fields at 9024, minimumDuration accepted standalone, zero accepted on all numeric fields)
- `TierStrategyTransformerTest` — 97 tests incl. Rework #7 Commit 3 BT-231 through BT-234 (advanced fields serialise to engine periodConfig on APPEND, extractValidityForSlab surfaces them on read, null-as-preserve on UPDATE with partial field sets, CREATE with only core fields doesn't write null-valued advanced fields)
- `SqlTierConverterTest` — 22 tests incl. BT-235 (flat TierRenewalView on GET surfaces all 4 advanced fields alongside the existing period + renewal-trigger fields)
- Total: 486 tests in `tier/**` — 0 failures, 0 errors (+27 vs Commit 2 baseline of 459)

**Evidence:** `TierRenewalConfig.java` (new fields — `downgradeTo`, `shouldDowngrade`, DNF `expressionRelation`, `conditions[]`) · `TierDowngradeConfig.java` (synthesis-only Boolean shouldDowngrade + DNF expressionRelation fields) · `TierEnumValidation.java` (9019/9020/9021 error codes + `validateRenewalDowngradeTo` + `validateRenewalConditionsAndExpression` + `validateRenewalExpressionRelation`) · `TierRenewalValidation.java` (loosened B1a to permit engine-backed conditions/expressionRelation while preserving criteriaType lock) · `TierRenewalExpressionParser.java` (new — DNF tokeniser + parser + wire↔engine-bracket bridge + canonical formatter) · `TierStrategyTransformer.java:synthesiseDowngradeFromRenewal` (wire → engine adapter) · `TierStrategyTransformer.buildConditionsObject` (serialises DNF to engine bracket format via parser) · `TierStrategyTransformer.extractDowngradeForSlab` (reverses engine bracket → wire DNF with canonical output) · `TierApprovalHandler.java:applyDowngradeDelta` (fallback synthesis when `entity.getDowngrade()` is null).

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
| `POST   /v3/tiers`                  | | ✓ | | validator + JSR-303 + **9011–9018** (§5.3) | ✓ | | name-dup, 50-cap | ✓ |
| `PUT    /v3/tiers/{tierId}`         | ✓ | | | validator + **9011–9018** (§5.3) | ✓ | ✓ | `SNAPSHOT`/`DELETED`, rename-dup | ✓ |
| `DELETE /v3/tiers/{tierId}`         | | | ✓ | | ✓ | ✓ | status ≠ `DRAFT` | ✓ |
| `POST   /v3/tiers/{id}/submit`      | ✓ *(incl. not-found — §10.1)* | | | | ✓ | | status ≠ `DRAFT` | ✓ |
| `POST   /v3/tiers/{id}/approve`     | ✓ *(incl. not-found — §10.1)* | | | | ✓ | | status ≠ `PENDING_APPROVAL`, **drift** | unknown action, SAGA failure |
| `GET    /v3/tiers/approvals`        | ✓ | | | param | ✓ | | | ✓ |

---

## 13. Feature → Endpoint Map

| Feature / User Story | Endpoint(s) | Behaviour |
|---|---|---|
| E1-US1: Create Tier | `POST /v3/tiers` | Returns 201 with full document |
| E1-US2: List Tiers | `GET /v3/tiers` | Flat `List<TierEntry>` (up to 2 entries per slabId — LIVE + in-flight). No KPI summary (Q27). |
| E1-US3: View Tier | `GET /v3/tiers/{tierId}` | Array of 1 or 2 `TierEntry` — numeric path returns LIVE + paired in-flight; string path returns draft only (Q27). |
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
| `slabId` | `Long` (MySQL `program_slabs.id`, e.g. `3850`) | No | SQL linkage. Populated **after** first APPROVE. `null` before. Sits on each `TierEntry` — the shared `slabId` is how UI pairs a LIVE entry with its in-flight draft entry (Q27). **Accepted as numeric `{tierId}` on detail** — returns an array of 1 or 2 entries (§5.2). |
| `parentId` | MongoDB ObjectId | No | On versioned drafts-of-ACTIVE, points at the ACTIVE's `objectId`. `null` on originals. |
| `serialNumber` | `Integer`, assigned on create | No (immutable across edits) | Visible ordering handle on the UI — part of `tierUniqueId`. |
| `programId` | `Integer` | **No (immutable)** | Identifies the loyalty program this tier belongs to. Set at create. Cannot be changed via PUT. |
| `orgId` | `Long` | No | Set from auth token. Scopes all queries — tenant isolation. |

---

## 16. UI Handoff Checklist

1. **Consume `TierEntry` (flat), not `UnifiedTierConfig` or `TierEnvelope`, as the read shape.** Q27 replaced the envelope pairing with a flat `List<TierEntry>`. Tests that assumed envelopes with `live`/`pendingDraft` blocks or `origin` — or flat `UnifiedTierConfig` documents from v2 — must be updated.
2. **Pair entries client-side by shared `slabId`.** Two entries with the same `slabId` = LIVE tier with an in-flight edit. One entry with `slabId = null` = brand-new DRAFT. Use the `status` field to identify the state (`"LIVE"` / `"DRAFT"` / `"PENDING_APPROVAL"` / `"REJECTED"`). See §5.1, §6.11.
3. **Check `errors[0]` on HTTP 200 responses from `/submit` and `/approve`.** Not-found returns 200 with an error object (§10.1).
4. **Omit the `status` query param on `GET /v3/tiers`** or you'll get an empty list (§10.2). Filter client-side on each entry's `status` field if you need subsets.
5. **Compute counts (total tiers, live count, pending count) client-side.** The old `KpiSummary` block is gone (§10.3). Iterate the flat list.
6. **Validate `approvalStatus` is `APPROVE` or `REJECT` on the client.** Anything else is a 500 (§10.6).
7. **On drift 409, render `data.diffs`, not `errors[0].message`.** The structured diff is the source of truth (§5.7.1).
8. **Choose the right detail path.** `GET /v3/tiers/{slabId}` (numeric) returns an array of 1 or 2 entries (LIVE ± paired in-flight). `GET /v3/tiers/{tierUniqueId}` (string) returns a single-element array containing only the draft. See §5.2.
9. **Do not send the `Idempotency-Key` header and expect dedup.** Use it as a client-side correlation id only (§10.11).
10. **Do not render `engineConfig` or `basisSqlSnapshot`.** These are engine internals leaked through the document, not part of the visible contract (§10.9, §10.10).
11. **Offer a retry UX on HTTP 500 during APPROVE.** The Thrift SAGA can fail transiently (§10.13).
12. **All dates on responses are `yyyy-MM-ddTHH:mm:ss+00:00`.** Never `Z`. Your parser should accept both defensively, but generate `+00:00` on outbound requests for consistency (§14).
13. **Read-side field key for validity is `renewal`.** On the write side (POST/PUT body) send the block under `validity` (unchanged). On GET responses the same block is emitted as `renewal` at the tier-entry root, and the nested `renewal` sub-object (the old `TierRenewalConfig`) is suppressed. See §6.5.
