# API Handoff -- Tiers CRUD + Maker-Checker

> For: UI Development Team (Garuda)
> Version: 2.0 (v1.4 + Phase D: data model realigned with engine, 5 bug fixes, new field names)
> Base URL: `https://{host}/v3`
> Auth: Bearer token in `Authorization` header
> Content-Type: `application/json`
> Date: 2026-04-16

---

## Breaking Changes from v1.x

| v1.x Field | v2.0 Field | Why |
|------------|-----------|-----|
| `eligibilityCriteria` | `eligibility` | Aligned with prototype and engine |
| `eligibilityCriteria.criteriaType` (enum) | `eligibility.kpiType` (string) | Matches engine's `CurrentValueType` |
| `eligibilityCriteria.activities[]` | `eligibility.conditions[]` | Matches engine's condition model |
| `eligibilityCriteria.activityRelation` | `eligibility.expressionRelation` | Matches engine field name |
| `eligibilityCriteria.membershipDuration` (free text) | `validity.periodValue` (int, months) | Typed, engine-aligned |
| `eligibilityCriteria.upgradeSchedule` (free text) | `eligibility.upgradeType` (string enum) | `EAGER` / `DYNAMIC` / `LAZY` |
| `renewalConfig` | `validity` | Contains period + nested `renewal` |
| `downgradeConfig.downgradeTo.type` | `downgrade.target` | Flat string, not nested object |
| `downgradeConfig.downgradeSchedule` (enum) | `downgrade.dailyEnabled` (boolean) | Simpler, matches engine |
| `downgradeConfig.shouldDowngrade` | Removed | Use `downgrade` being non-null |
| `downgradeConfig.expiryReminders` (free text) | `nudges.expiryWarning` (string) | Structured nudges object |

**Default list behavior changed:** `GET /v3/tiers` without `status` filter now returns only live tiers (DRAFT, ACTIVE, PENDING_APPROVAL). DELETED and SNAPSHOT tiers are excluded by default. Pass `status=DELETED` explicitly to see them.

---

## Authentication

All endpoints require a valid Bearer token:

```
Authorization: Bearer <access_token>
```

The token carries `orgId`, `entityId` (user ID), and `tillName`. The `orgId` is extracted server-side -- you never need to pass it explicitly.

---

## Response Envelope

All responses use the standard `ResponseWrapper<T>`:

```json
{
  "data": { ... },
  "errors": null,
  "warnings": null
}
```

On error:
```json
{
  "data": null,
  "errors": [
    { "code": 400, "message": "Name is required" }
  ],
  "warnings": null
}
```

---

## 1. List Tiers

### `GET /v3/tiers`

Returns tiers for a program with full configuration, KPI summary, and cached member counts.

**Default behavior (no status filter):** Returns only **live** tiers -- DRAFT, ACTIVE, PENDING_APPROVAL. Excludes DELETED and SNAPSHOT.

**Query Parameters:**

| Param | Type | Required | Default | Example |
|-------|------|----------|---------|---------|
| programId | int | YES | - | `977` |
| status | string (comma-separated) | NO | `DRAFT,ACTIVE,PENDING_APPROVAL` | `ACTIVE,DRAFT` |

**Example Request:**
```
GET /v3/tiers?programId=977
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

**Example Response (200 OK):**
```json
{
  "data": {
    "summary": {
      "totalTiers": 4,
      "activeTiers": 3,
      "pendingApprovalTiers": 1,
      "totalMembers": 2135,
      "lastMemberCountRefresh": "2026-04-16T12:00:00+05:30"
    },
    "tiers": [
      {
        "objectId": "661a3f2e8b1c4d5e6f7a8b9c",
        "unifiedTierId": "ut-977-001",
        "programId": 977,
        "status": "ACTIVE",
        "parentId": null,
        "version": 1,
        "basicDetails": {
          "name": "Bronze",
          "description": "Entry level tier with basic benefits",
          "color": "#CD7F32",
          "serialNumber": 1,
          "startDate": "2025-01-01T00:00:00+05:30",
          "endDate": null
        },
        "eligibility": null,
        "validity": null,
        "downgrade": null,
        "nudges": null,
        "benefitIds": ["bf-001", "bf-007", "bf-012"],
        "memberStats": {
          "memberCount": 1245,
          "lastRefreshed": "2026-04-16T12:00:00+05:30"
        },
        "metadata": {
          "createdBy": "user-admin-01",
          "createdAt": "2025-01-01T00:00:00+05:30",
          "updatedBy": "user-admin-01",
          "updatedAt": "2025-01-01T00:00:00+05:30",
          "updatedViaNewUI": true,
          "sqlSlabId": 3848
        }
      },
      {
        "objectId": "661a3f2e8b1c4d5e6f7a8b9d",
        "unifiedTierId": "ut-977-002",
        "programId": 977,
        "status": "ACTIVE",
        "parentId": null,
        "version": 1,
        "basicDetails": {
          "name": "Silver",
          "description": "Mid-level tier with enhanced benefits",
          "color": "#C0C0C0",
          "serialNumber": 2,
          "startDate": "2025-01-01T00:00:00+05:30",
          "endDate": "2025-12-31T23:59:59+05:30"
        },
        "eligibility": {
          "kpiType": "LIFETIME_PURCHASES",
          "threshold": 550.0,
          "upgradeType": "LAZY",
          "expressionRelation": "AND",
          "conditions": [
            { "type": "PURCHASE", "value": "550", "trackerName": null },
            { "type": "VISITS", "value": "2", "trackerName": null }
          ]
        },
        "validity": {
          "periodType": "SLAB_UPGRADE",
          "periodValue": 12,
          "startDate": "2025-01-01T00:00:00+05:30",
          "endDate": "2025-12-31T23:59:59+05:30",
          "renewal": {
            "criteriaType": "Same as eligibility",
            "expressionRelation": "AND",
            "conditions": [
              { "type": "PURCHASE", "value": "550", "trackerName": null },
              { "type": "VISITS", "value": "2", "trackerName": null }
            ],
            "schedule": "End of month when duration ends"
          }
        },
        "downgrade": {
          "target": "SINGLE",
          "reevaluateOnReturn": false,
          "dailyEnabled": false,
          "conditions": [
            { "type": "PURCHASE", "value": "550", "trackerName": null }
          ]
        },
        "nudges": {
          "upgradeNotification": "Upgrade congratulations email",
          "renewalReminder": "Renewal reminder 30 days before expiry",
          "expiryWarning": "Downgrade warning at 60 days before expiry",
          "downgradeConfirmation": null
        },
        "benefitIds": ["bf-002", "bf-005", "bf-008", "bf-013"],
        "memberStats": {
          "memberCount": 667,
          "lastRefreshed": "2026-04-16T12:00:00+05:30"
        },
        "metadata": {
          "createdBy": "user-admin-01",
          "createdAt": "2025-01-01T00:00:00+05:30",
          "updatedBy": "user-admin-01",
          "updatedAt": "2025-06-15T10:30:00+05:30",
          "updatedViaNewUI": true,
          "sqlSlabId": 3849
        }
      },
      {
        "objectId": "661a3f2e8b1c4d5e6f7a8b9e",
        "unifiedTierId": "ut-977-003",
        "programId": 977,
        "status": "ACTIVE",
        "parentId": null,
        "version": 1,
        "basicDetails": {
          "name": "Gold",
          "description": "Premium tier with exclusive benefits",
          "color": "#FFD700",
          "serialNumber": 3,
          "startDate": "2025-01-01T00:00:00+05:30",
          "endDate": "2025-12-31T23:59:59+05:30"
        },
        "eligibility": {
          "kpiType": "LIFETIME_PURCHASES",
          "threshold": 900.0,
          "upgradeType": "LAZY",
          "expressionRelation": "AND",
          "conditions": [
            { "type": "PURCHASE", "value": "900", "trackerName": null },
            { "type": "VISITS", "value": "2", "trackerName": null }
          ]
        },
        "validity": {
          "periodType": "SLAB_UPGRADE",
          "periodValue": 12,
          "startDate": "2025-01-01T00:00:00+05:30",
          "endDate": "2025-12-31T23:59:59+05:30",
          "renewal": {
            "criteriaType": "Same as eligibility",
            "expressionRelation": "AND",
            "conditions": [
              { "type": "PURCHASE", "value": "900", "trackerName": null },
              { "type": "VISITS", "value": "2", "trackerName": null }
            ],
            "schedule": "End of month when duration ends"
          }
        },
        "downgrade": {
          "target": "SINGLE",
          "reevaluateOnReturn": false,
          "dailyEnabled": true,
          "conditions": [
            { "type": "PURCHASE", "value": "900", "trackerName": null }
          ]
        },
        "nudges": {
          "upgradeNotification": "VIP welcome package notification",
          "renewalReminder": "VIP renewal reminder with exclusive preview",
          "expiryWarning": "Premium retention offer 90 days before expiry",
          "downgradeConfirmation": null
        },
        "benefitIds": ["bf-003", "bf-006", "bf-009", "bf-011", "bf-014"],
        "memberStats": {
          "memberCount": 234,
          "lastRefreshed": "2026-04-16T12:00:00+05:30"
        },
        "metadata": {
          "createdBy": "user-admin-01",
          "createdAt": "2025-01-01T00:00:00+05:30",
          "updatedBy": "user-admin-02",
          "updatedAt": "2025-09-20T14:45:00+05:30",
          "updatedViaNewUI": true,
          "sqlSlabId": 3850
        }
      },
      {
        "objectId": "661b5a1f9c2d3e4f5a6b7c8d",
        "unifiedTierId": "ut-977-004",
        "programId": 977,
        "status": "DRAFT",
        "parentId": null,
        "version": 1,
        "basicDetails": {
          "name": "Platinum",
          "description": "Elite tier for top customers",
          "color": "#E5E4E2",
          "serialNumber": 4,
          "startDate": "2026-01-01T00:00:00+05:30",
          "endDate": "2026-12-31T23:59:59+05:30"
        },
        "eligibility": {
          "kpiType": "LIFETIME_PURCHASES",
          "threshold": 2000.0,
          "upgradeType": "LAZY",
          "expressionRelation": "AND",
          "conditions": [
            { "type": "PURCHASE", "value": "2000", "trackerName": null }
          ]
        },
        "validity": {
          "periodType": "SLAB_UPGRADE",
          "periodValue": 12,
          "startDate": "2026-01-01T00:00:00+05:30",
          "endDate": "2026-12-31T23:59:59+05:30",
          "renewal": {
            "criteriaType": "Same as eligibility",
            "expressionRelation": "AND",
            "conditions": [
              { "type": "PURCHASE", "value": "1500", "trackerName": null }
            ],
            "schedule": "End of month when duration ends"
          }
        },
        "downgrade": {
          "target": "SINGLE",
          "reevaluateOnReturn": false,
          "dailyEnabled": false,
          "conditions": [
            { "type": "PURCHASE", "value": "2000", "trackerName": null }
          ]
        },
        "nudges": {
          "upgradeNotification": "Platinum welcome call from relationship manager",
          "renewalReminder": "Platinum renewal exclusive offer 45 days before expiry",
          "expiryWarning": "Platinum retention personal call 90 days before expiry",
          "downgradeConfirmation": null
        },
        "benefitIds": [],
        "memberStats": {
          "memberCount": 0,
          "lastRefreshed": null
        },
        "metadata": {
          "createdBy": "user-admin-02",
          "createdAt": "2026-04-16T10:00:00+05:30",
          "updatedBy": "user-admin-02",
          "updatedAt": "2026-04-16T10:00:00+05:30",
          "updatedViaNewUI": true,
          "sqlSlabId": null
        }
      }
    ]
  },
  "errors": null,
  "warnings": null
}
```

**Error Responses:**

```
GET /v3/tiers
-> 400 Bad Request (missing programId)
```
```json
{
  "data": null,
  "errors": [{ "code": 400, "message": "programId is required" }],
  "warnings": null
}
```

```
GET /v3/tiers?programId=99999
-> 200 OK (empty program -- not 404)
```
```json
{
  "data": {
    "summary": { "totalTiers": 0, "activeTiers": 0, "pendingApprovalTiers": 0, "totalMembers": 0, "lastMemberCountRefresh": null },
    "tiers": []
  },
  "errors": null,
  "warnings": null
}
```

---

## 2. Get Tier Detail

### `GET /v3/tiers/{tierId}`

Returns the full tier document including `engineConfig` (hidden engine settings **not** included in the listing endpoint). Use this for edit form pre-fill and version comparison.

**Path Parameter:** `tierId` = the `objectId` or `unifiedTierId`

**Example Request:**
```
GET /v3/tiers/661a3f2e8b1c4d5e6f7a8b9e
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

**Example Response (200 OK):**
```json
{
  "data": {
    "objectId": "661a3f2e8b1c4d5e6f7a8b9e",
    "unifiedTierId": "ut-977-003",
    "programId": 977,
    "status": "ACTIVE",
    "parentId": null,
    "version": 1,
    "basicDetails": {
      "name": "Gold",
      "description": "Premium tier with exclusive benefits",
      "color": "#FFD700",
      "serialNumber": 3,
      "startDate": "2025-01-01T00:00:00+05:30",
      "endDate": "2025-12-31T23:59:59+05:30"
    },
    "eligibility": {
      "kpiType": "LIFETIME_PURCHASES",
      "threshold": 900.0,
      "upgradeType": "LAZY",
      "expressionRelation": "AND",
      "conditions": [
        { "type": "PURCHASE", "value": "900", "trackerName": null },
        { "type": "VISITS", "value": "2", "trackerName": null }
      ]
    },
    "validity": {
      "periodType": "SLAB_UPGRADE",
      "periodValue": 12,
      "startDate": "2025-01-01T00:00:00+05:30",
      "endDate": "2025-12-31T23:59:59+05:30",
      "renewal": {
        "criteriaType": "Same as eligibility",
        "expressionRelation": "AND",
        "conditions": [
          { "type": "PURCHASE", "value": "900", "trackerName": null }
        ],
        "schedule": "End of month when duration ends"
      }
    },
    "downgrade": {
      "target": "SINGLE",
      "reevaluateOnReturn": false,
      "dailyEnabled": true,
      "conditions": [
        { "type": "PURCHASE", "value": "900", "trackerName": null }
      ]
    },
    "nudges": {
      "upgradeNotification": "VIP welcome package notification",
      "renewalReminder": "VIP renewal reminder with exclusive preview",
      "expiryWarning": "Premium retention offer 90 days before expiry",
      "downgradeConfirmation": null
    },
    "benefitIds": ["bf-003", "bf-006", "bf-009", "bf-011", "bf-014"],
    "memberStats": {
      "memberCount": 234,
      "lastRefreshed": "2026-04-16T12:00:00+05:30"
    },
    "engineConfig": {
      "retainPoints": true,
      "isDowngradeOnReturnEnabled": false,
      "isDowngradeOnPartnerProgramExpiryEnabled": false,
      "isAdvanceSetting": true,
      "addDefaultCommunication": false,
      "slabUpgradeMode": "LAZY",
      "periodConfig": {
        "type": "SLAB_UPGRADE",
        "value": 12,
        "unit": "NUM_MONTHS",
        "startDate": null,
        "computationWindowStartValue": 12,
        "computationWindowEndValue": 0,
        "minimumDuration": 0
      },
      "downgradeEngineConfig": {
        "isActive": true,
        "conditionAlways": true,
        "conditionValues": {
          "purchase": "",
          "numVisits": "",
          "points": "",
          "trackerCount": []
        },
        "renewalOrderString": ""
      },
      "expressionRelation": null,
      "customExpression": null,
      "isFixedTypeWithoutYear": false,
      "renewalWindowType": "FIXED_DATE_BASED",
      "notificationConfig": {
        "sms": null,
        "email": {
          "subject": "Your Gold Tier Status",
          "body": "...",
          "templateId": 12345,
          "senderId": "loyalty"
        },
        "weChat": null,
        "mobilePush": null
      }
    },
    "metadata": {
      "createdBy": "user-admin-01",
      "createdAt": "2025-01-01T00:00:00+05:30",
      "updatedBy": "user-admin-02",
      "updatedAt": "2025-09-20T14:45:00+05:30",
      "updatedViaNewUI": true,
      "sqlSlabId": 3850
    }
  },
  "errors": null,
  "warnings": null
}
```

**Key difference from listing:** This endpoint includes the `engineConfig` section -- hidden engine configurations preserved for round-trip fidelity. Do NOT display `engineConfig` in the UI. Preserve it on edit (send it back unchanged in the PUT body).

**Error Responses:**

```
GET /v3/tiers/nonexistent-id
-> 404 Not Found
```
```json
{
  "data": null,
  "errors": [{ "code": 404, "message": "Tier not found" }],
  "warnings": null
}
```

---

## 3. Create Tier

### `POST /v3/tiers`

Creates a new tier. If maker-checker is enabled, saves as DRAFT. If disabled, saves as ACTIVE and syncs to SQL immediately.

**Headers:**

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| Authorization | YES | Bearer token | `Bearer eyJhbGciOiJSUzI1NiJ9...` |
| Idempotency-Key | Recommended | Prevents duplicate tier creation on retry. Same key within 24 hours returns the original response. | `idem-tier-create-abc123` |

**Request Body:**

```json
{
  "programId": 977,
  "basicDetails": {
    "name": "Platinum",
    "description": "Elite tier for top customers",
    "color": "#E5E4E2",
    "startDate": "2026-01-01T00:00:00+05:30",
    "endDate": "2026-12-31T23:59:59+05:30"
  },
  "eligibility": {
    "kpiType": "LIFETIME_PURCHASES",
    "threshold": 2000.0,
    "upgradeType": "LAZY",
    "expressionRelation": "AND",
    "conditions": [
      { "type": "PURCHASE", "value": "2000" }
    ]
  },
  "validity": {
    "periodType": "SLAB_UPGRADE",
    "periodValue": 12,
    "renewal": {
      "criteriaType": "Same as eligibility",
      "expressionRelation": "AND",
      "conditions": [
        { "type": "PURCHASE", "value": "1500" }
      ],
      "schedule": "End of month when duration ends"
    }
  },
  "downgrade": {
    "target": "SINGLE",
    "reevaluateOnReturn": false,
    "dailyEnabled": false,
    "conditions": [
      { "type": "PURCHASE", "value": "2000" }
    ]
  },
  "nudges": {
    "upgradeNotification": "Platinum welcome call from relationship manager",
    "renewalReminder": "Platinum renewal exclusive offer 45 days before expiry",
    "expiryWarning": "Platinum retention personal call 90 days before expiry"
  },
  "benefitIds": []
}
```

**Notes:**
- `serialNumber` is auto-assigned (max existing + 1). Do NOT send it.
- `status` is set by the server based on MC toggle. Do NOT send it.
- `unifiedTierId` is generated by the server. Do NOT send it.
- `color` must be a valid hex code (e.g., `#E5E4E2`).
- `programId` is required.
- `basicDetails.name` must be unique within the program (among live tiers -- DELETED tier names can be reused).

**Example Response (201 Created, MC enabled -- saved as DRAFT):**

```json
{
  "data": {
    "objectId": "661b5a1f9c2d3e4f5a6b7c8d",
    "unifiedTierId": "ut-977-004",
    "programId": 977,
    "status": "DRAFT",
    "parentId": null,
    "version": 1,
    "basicDetails": {
      "name": "Platinum",
      "description": "Elite tier for top customers",
      "color": "#E5E4E2",
      "serialNumber": 4,
      "startDate": "2026-01-01T00:00:00+05:30",
      "endDate": "2026-12-31T23:59:59+05:30"
    },
    "eligibility": { "...": "same as request" },
    "validity": { "...": "same as request" },
    "downgrade": { "...": "same as request" },
    "nudges": { "...": "same as request" },
    "benefitIds": [],
    "memberStats": { "memberCount": 0, "lastRefreshed": null },
    "metadata": {
      "createdBy": "user-admin-02",
      "createdAt": "2026-04-16T10:00:00+05:30",
      "updatedBy": "user-admin-02",
      "updatedAt": "2026-04-16T10:00:00+05:30",
      "updatedViaNewUI": true,
      "sqlSlabId": null
    }
  },
  "errors": null,
  "warnings": null
}
```

**Error Responses:**

```
POST /v3/tiers (duplicate name)
-> 409 Conflict
```
```json
{
  "data": null,
  "errors": [{ "code": 409, "message": "A tier with name 'Gold' already exists in program 977" }],
  "warnings": null
}
```

```
POST /v3/tiers (validation error)
-> 400 Bad Request
```
```json
{
  "data": null,
  "errors": [
    { "code": 400, "message": "basicDetails.name is required" }
  ],
  "warnings": null
}
```

---

## 4. Update Tier

### `PUT /v3/tiers/{tierId}`

Updates an existing tier. If the tier is ACTIVE, creates a new DRAFT version (the ACTIVE stays live).

**Path Parameter:** `tierId` = the `objectId` or `unifiedTierId`

**Request Body (partial update -- send only changed fields):**

```json
{
  "basicDetails": {
    "name": "Gold Plus",
    "description": "Enhanced premium tier",
    "color": "#DAA520"
  },
  "eligibility": {
    "kpiType": "LIFETIME_PURCHASES",
    "threshold": 1200.0,
    "upgradeType": "LAZY",
    "conditions": [
      { "type": "PURCHASE", "value": "1200" }
    ]
  }
}
```

**Example Response (200 OK, editing an ACTIVE tier -- new DRAFT created):**

```json
{
  "data": {
    "objectId": "661c7b3a0d4e5f6a7b8c9d0e",
    "unifiedTierId": "ut-977-003",
    "programId": 977,
    "status": "DRAFT",
    "parentId": "661a3f2e8b1c4d5e6f7a8b9e",
    "version": 2,
    "basicDetails": {
      "name": "Gold Plus",
      "description": "Enhanced premium tier",
      "color": "#DAA520",
      "serialNumber": 3,
      "startDate": "2025-01-01T00:00:00+05:30",
      "endDate": "2025-12-31T23:59:59+05:30"
    },
    "eligibility": {
      "kpiType": "LIFETIME_PURCHASES",
      "threshold": 1200.0,
      "upgradeType": "LAZY",
      "conditions": [
        { "type": "PURCHASE", "value": "1200" }
      ]
    },
    "validity": { "...": "inherited from ACTIVE version" },
    "downgrade": { "...": "inherited from ACTIVE version" },
    "nudges": { "...": "inherited from ACTIVE version" },
    "benefitIds": ["bf-003", "bf-006", "bf-009", "bf-011", "bf-014"],
    "memberStats": { "memberCount": 234, "lastRefreshed": "2026-04-16T12:00:00+05:30" },
    "metadata": {
      "createdBy": "user-admin-02",
      "createdAt": "2026-04-16T14:00:00+05:30",
      "updatedBy": "user-admin-02",
      "updatedAt": "2026-04-16T14:00:00+05:30",
      "updatedViaNewUI": true,
      "sqlSlabId": null
    }
  },
  "errors": null,
  "warnings": [{ "message": "This is a versioned edit. The ACTIVE tier (Gold) remains live. Submit this draft for approval to replace it." }]
}
```

**Key behaviors:**
- Editing a **DRAFT**: updates in place (same objectId)
- Editing an **ACTIVE**: creates NEW document with `parentId` pointing to ACTIVE. Returns the new DRAFT.
- Editing a **PENDING_APPROVAL**: updates in place
- `serialNumber` cannot be changed (immutable)
- If a DRAFT already exists for this ACTIVE tier, the existing DRAFT is updated (one DRAFT per ACTIVE)
- **Name uniqueness is enforced on rename** -- changing a tier's name to one already used by another live tier returns 409.

---

## 5. Delete Tier

### `DELETE /v3/tiers/{tierId}`

Soft-deletes a tier by setting status to DELETED. Only **DRAFT** tiers can be deleted. Returns 409 if the tier is in any other status. No maker-checker gate -- deletion is immediate and does not create a PendingChange.

| Current Status | Result |
|----------------|--------|
| **DRAFT** | Status set to DELETED (soft-delete, audit trail preserved). |
| **ACTIVE / PENDING_APPROVAL / SNAPSHOT** | 409 Conflict -- cannot delete a non-DRAFT tier. |

> **Tier retirement (stopping ACTIVE tiers):** Out of scope for this release. Planned as a future epic.
> **Name reuse:** After a tier is DELETED, its name can be reused for new tiers.

**Example Request:**
```
DELETE /v3/tiers/661b5a1f9c2d3e4f5a6b7c8d
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

**Example Response (204 No Content -- DRAFT deleted):**
```
HTTP/1.1 204 No Content
```

**Error: tier is not in DRAFT status:**
```
DELETE /v3/tiers/661a3f2e8b1c4d5e6f7a8b9e (ACTIVE tier)
-> 409 Conflict
```
```json
{
  "data": null,
  "errors": [{ "code": 409, "message": "Only DRAFT tiers can be deleted. Tier 'Gold' is in ACTIVE status." }],
  "warnings": null
}
```

---

## 6. Submit for Approval

### `POST /v3/maker-checker/submit`

Submits a DRAFT tier (or other entity) for maker-checker approval.

**Request Body:**
```json
{
  "entityType": "TIER",
  "entityId": "661b5a1f9c2d3e4f5a6b7c8d"
}
```

**Example Response (200 OK):**
```json
{
  "data": {
    "objectId": "661e9d5c2f6a7b8c9d0e1f2a",
    "orgId": 100458,
    "programId": 977,
    "entityType": "TIER",
    "entityId": "661b5a1f9c2d3e4f5a6b7c8d",
    "changeType": "CREATE",
    "status": "PENDING_APPROVAL",
    "requestedBy": "user-admin-02",
    "requestedAt": "2026-04-16T11:00:00+05:30",
    "reviewedBy": null,
    "reviewedAt": null,
    "comment": null
  },
  "errors": null,
  "warnings": null
}
```

**Side effect:** The tier's status changes from DRAFT to PENDING_APPROVAL.

---

## 7. Approve Change

### `POST /v3/maker-checker/{changeId}/approve`

Approves a pending change. Triggers TierChangeApplier to sync MongoDB to SQL via Thrift.

**Path Parameter:** `changeId` = the PendingChange `objectId`

**Request Body:**
```json
{
  "comment": "Approved. Platinum tier config looks good."
}
```

**Example Response (200 OK):**
```json
{
  "data": {
    "objectId": "661e9d5c2f6a7b8c9d0e1f2a",
    "orgId": 100458,
    "programId": 977,
    "entityType": "TIER",
    "entityId": "661b5a1f9c2d3e4f5a6b7c8d",
    "changeType": "CREATE",
    "status": "APPROVED",
    "requestedBy": "user-admin-02",
    "requestedAt": "2026-04-16T11:00:00+05:30",
    "reviewedBy": "user-admin-01",
    "reviewedAt": "2026-04-16T13:30:00+05:30",
    "comment": "Approved. Platinum tier config looks good."
  },
  "errors": null,
  "warnings": null
}
```

**Side effects:**
- Tier status: PENDING_APPROVAL -> ACTIVE
- SQL: ProgramSlab created + strategies updated via Thrift
- `metadata.sqlSlabId` populated with the MySQL ID
- If versioned edit: old ACTIVE -> SNAPSHOT, new doc -> ACTIVE

---

## 8. Reject Change

### `POST /v3/maker-checker/{changeId}/reject`

Rejects a pending change. Comment is required.

**Request Body:**
```json
{
  "comment": "Gold threshold too low -- 1200 RM would overlap with Silver at 550 RM. Please increase to at least 1500 RM."
}
```

**Example Response (200 OK):**
```json
{
  "data": {
    "objectId": "661e9d5c2f6a7b8c9d0e1f2a",
    "status": "REJECTED",
    "reviewedBy": "user-admin-01",
    "reviewedAt": "2026-04-16T15:00:00+05:30",
    "comment": "Gold threshold too low -- 1200 RM would overlap with Silver at 550 RM. Please increase to at least 1500 RM."
  },
  "errors": null,
  "warnings": null
}
```

**Side effect:** Tier status: PENDING_APPROVAL -> DRAFT (can be edited and re-submitted).

---

## 9. List Pending Changes

### `GET /v3/maker-checker/pending`

Lists all pending changes awaiting approval.

**Query Parameters:**

| Param | Type | Required | Example |
|-------|------|----------|---------|
| entityType | string | NO | `TIER` |
| programId | int | NO | `977` |

---

## 10. Get Change Detail

### `GET /v3/maker-checker/{changeId}`

Returns the full pending change document including the embedded payload snapshot.

---

## 11. Maker-Checker Config

### `GET /v3/maker-checker/config`

Returns whether maker-checker is enabled for a given program and entity type.

**Query Parameters:**

| Param | Type | Required | Example |
|-------|------|----------|---------|
| programId | int | YES | `977` |
| entityType | string | YES | `TIER` |

**Example Response (200 OK):**
```json
{
  "data": {
    "programId": 977,
    "entityType": "TIER",
    "makerCheckerEnabled": true
  },
  "errors": null,
  "warnings": null
}
```

### `PUT /v3/maker-checker/config`

Toggles maker-checker on/off for a program and entity type. Stored in MongoDB (`maker_checker_configs` collection).

**Request Body:**
```json
{
  "programId": 977,
  "entityType": "TIER",
  "enabled": true
}
```

**UI behavior based on MC config:**

| `makerCheckerEnabled` | Create Flow | Edit Flow | Delete Flow |
|-----------------------|------------|-----------|-------------|
| `true` | Saves as DRAFT. Show "Submit for Approval" button. | Creates versioned DRAFT. Show "Submit for Approval". | DRAFT-only. Immediate removal. No MC gate. |
| `false` | Saves as ACTIVE immediately. Syncs to SQL. No approval step. | Applies edit immediately. Syncs to SQL. | DRAFT-only. Immediate removal. No approval step. |

---

## 12. Tier Program Settings

### `GET /v3/tier-settings`

Returns program-level tier configuration. These settings apply to **all tiers** in the program.

**Query Parameters:**

| Param | Type | Required | Example |
|-------|------|----------|---------|
| programId | int | YES | `977` |

**Example Response (200 OK):**
```json
{
  "data": {
    "programId": 977,
    "upgradeType": "LAZY",
    "validityPeriod": "SLAB_UPGRADE",
    "fixedDuration": {
      "value": null,
      "unit": "MONTHS"
    },
    "isDowngradeOnReturnEnabled": true,
    "dailyDowngradeEnabled": true,
    "retainPoints": true
  },
  "errors": null,
  "warnings": null
}
```

### `PUT /v3/tier-settings`

Updates program-level tier configuration.

---

## 13. Field Reference

### Eligibility — `eligibility` object

| Field | Type | Required | Values | Engine Mapping |
|-------|------|----------|--------|----------------|
| `kpiType` | string | YES (for non-base tier) | `CURRENT_POINTS`, `LIFETIME_POINTS`, `LIFETIME_PURCHASES`, `TRACKER_VALUE` | `CurrentValueType` enum |
| `threshold` | double | YES (for non-base tier) | Positive number | `threshold_value` CSV (per slab position) |
| `upgradeType` | string | YES | `EAGER`, `DYNAMIC`, `LAZY` | `SlabUpgradeMode` enum |
| `expressionRelation` | string | NO | `AND`, `OR` | `expression_relation` |
| `conditions` | array | NO | List of `TierCondition` | Mapped to strategy conditions |

### Upgrade Type Labels for UI

| API Value | UI Display Label |
|-----------|-----------------|
| `LAZY` | Issue points and then upgrade to next tier |
| `EAGER` | Upgrade then issue points |
| `DYNAMIC` | Issue points, upgrade, then issue remaining |

### Validity — `validity` object

| Field | Type | Required | Values | Engine Mapping |
|-------|------|----------|--------|----------------|
| `periodType` | string | YES | `FIXED`, `SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`, `FIXED_CUSTOMER_REGISTRATION` | `PeriodType` in downgrade strategy |
| `periodValue` | int | YES | Duration in months | `time_period` (integer, not string) |
| `startDate` | string | NO | ISO-8601, computed on read | `start_date` |
| `endDate` | string | NO | ISO-8601 or null | Derived |
| `renewal` | object | NO | Nested `TierRenewalConfig` | Mapped to renewal conditions |

### Validity Period Labels for UI

| API Value | UI Display Label |
|-----------|-----------------|
| `SLAB_UPGRADE` | Until tier upgrade or fixed duration |
| `FIXED` | Fixed duration only |
| `FIXED_CUSTOMER_REGISTRATION` | Fixed from customer registration date |
| `SLAB_UPGRADE_CYCLIC` | Cyclic from tier upgrade date |

### Renewal — `validity.renewal` object

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `criteriaType` | string | NO | `"Same as eligibility"`, `"Active subscription"` |
| `expressionRelation` | string | NO | `AND`, `OR` |
| `conditions` | array | NO | List of `TierCondition` |
| `schedule` | string | NO | Display text for renewal schedule |

### Downgrade — `downgrade` object

| Field | Type | Required | Values | Engine Mapping |
|-------|------|----------|--------|----------------|
| `target` | string | YES | `SINGLE`, `THRESHOLD`, `LOWEST` | `TierDowngradeTarget` enum |
| `reevaluateOnReturn` | boolean | NO | | `isDowngradeOnReturnEnabled` |
| `dailyEnabled` | boolean | NO | | `dailyDowngradeEnabled` |
| `conditions` | array | NO | List of `TierCondition` | Per-slab downgrade conditions |

### Downgrade Target Labels for UI

| API Value | UI Display Label |
|-----------|-----------------|
| `SINGLE` | Downgrade to the next lower tier |
| `THRESHOLD` | Downgrade to tier matching current threshold |
| `LOWEST` | Downgrade to base tier |

### TierCondition

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `type` | string | YES | `PURCHASE`, `VISITS`, `POINTS`, `TRACKER` |
| `value` | string | YES | Threshold value as string |
| `trackerName` | string | Only if type=TRACKER | Tracker identifier |

### Nudges — `nudges` object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `upgradeNotification` | string | NO | Message/template for upgrade notification |
| `renewalReminder` | string | NO | Message/template for renewal reminder |
| `expiryWarning` | string | NO | Message/template for expiry warning |
| `downgradeConfirmation` | string | NO | Message/template for downgrade confirmation |

### Tier Statuses (for UI badge rendering)

| Status | Badge Color | User Can... |
|--------|------------|-------------|
| `DRAFT` | Grey | Edit, Submit, Delete |
| `PENDING_APPROVAL` | Amber | View (approver can Approve/Reject) |
| `ACTIVE` | Green | Edit (creates new version) |
| `DELETED` | Red | View only (terminal -- reached from DRAFT only) |
| `SNAPSHOT` | Dark grey | View only (archived version) |

---

## 14. Complete Flow Example: Create + Submit + Approve

### Step 1: Create Platinum tier (MC enabled -- becomes DRAFT)
```
POST /v3/tiers
-> 201 Created, status: "DRAFT", objectId: "661b5a..."
```

### Step 2: Submit for approval
```
POST /v3/maker-checker/submit
Body: { "entityType": "TIER", "entityId": "661b5a..." }
-> 200 OK, changeId: "661e9d..."
```
Tier status changes: DRAFT -> PENDING_APPROVAL

### Step 3: Approve
```
POST /v3/maker-checker/661e9d.../approve
Body: { "comment": "Looks good" }
-> 200 OK
```
Tier status changes: PENDING_APPROVAL -> ACTIVE
SQL sync happens. `metadata.sqlSlabId` populated.

### Step 4: Verify in listing
```
GET /v3/tiers?programId=977
-> Platinum now appears with status: "ACTIVE" and sqlSlabId set
```

---

## 15. Complete Flow Example: Edit ACTIVE Tier (Versioned)

### Step 1: Edit Gold tier (ACTIVE, objectId: "661a...9e")
```
PUT /v3/tiers/661a...9e
Body: { "basicDetails": { "name": "Gold Plus" }, "eligibility": { "threshold": 1200.0, "conditions": [{ "type": "PURCHASE", "value": "1200" }] } }
-> 200 OK, NEW objectId: "661c7b...", status: "DRAFT", parentId: "661a...9e"
```
The original Gold (objectId: "661a...9e") stays ACTIVE. A new DRAFT is created.

### Step 2: Listing shows BOTH
```
GET /v3/tiers?programId=977
-> Gold (ACTIVE, threshold 900) + Gold Plus (DRAFT, threshold 1200, parentId: 661a...9e)
```

### Step 3: Submit + Approve
Result: Gold Plus -> ACTIVE. Original Gold -> SNAPSHOT (excluded from default listing).

---

## 16. Complete Flow Example: Delete (DRAFT only)

### Deleting a DRAFT tier (immediate -- no MC gate)
```
DELETE /v3/tiers/661b5a1f9c2d3e4f5a6b7c8d
-> 204 No Content
```
The DRAFT document status is set to DELETED. No PendingChange is created. The tier name can be reused.

---

## 17. Important Notes for UI Team

1. **`serialNumber` is auto-assigned and immutable.** Never send it in create/update. It determines tier ordering.
2. **`unifiedTierId` persists across versions.** When an ACTIVE tier is edited, the new DRAFT has the same `unifiedTierId` but a different `objectId`. Use `unifiedTierId` to track a tier's identity across versions.
3. **`parentId` indicates a versioned edit.** If a DRAFT has a non-null `parentId`, it is a pending edit of an ACTIVE tier.
4. **`sqlSlabId` is null for DRAFT tiers.** Populated only after MC approval syncs to SQL.
5. **Member counts are cached.** `memberStats.lastRefreshed` shows when the count was last updated.
6. **`engineConfig` is NOT returned in the listing response.** Only visible in the full tier detail endpoint.
7. **All dates are ISO-8601 with timezone offset** (e.g., `+05:30`).
8. **Call `GET /v3/maker-checker/config` on page load** to determine MC vs direct-save flow.
9. **Default list excludes DELETED and SNAPSHOT.** Pass `status=DELETED` explicitly to see deleted tiers.
10. **Name uniqueness is enforced among live tiers.** DELETED tier names can be reused.
11. **Only DRAFT tiers can be deleted.** ACTIVE tier retirement is out of scope.
12. **Base tier (serialNumber=1):** Typically has `eligibility: null` (no threshold -- everyone starts here).
13. **`TierCondition.value` is a string**, not a number. This allows flexible values (e.g., tracker expressions). Parse to number for numeric display.

---

## 18. Not In Scope (This Release)

| Feature | Reason | Future |
|---------|--------|--------|
| **Tier Reorder** | `serialNumber` is immutable. | No current plan. |
| **Tier Settings** (program-level) | API designed but not implemented yet. | Next sprint. |
| **Version History / Diff** | SNAPSHOT documents preserved. No dedicated endpoint. | Planned for Change Log. |
| **Bulk Operations** | One tier at a time. | No current plan. |
| **Real-time Member Counts** | Cached, refreshed periodically. | No on-demand refresh API. |
