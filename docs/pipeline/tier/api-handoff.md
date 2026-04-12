# API Handoff -- Tiers CRUD + Maker-Checker

> For: UI Development Team (Garuda)
> Version: 1.1 (added: Get Tier Detail, MC Config, Change Detail, per-status Delete, Idempotency)
> Base URL: `https://{host}/v3`
> Auth: Bearer token in `Authorization` header
> Content-Type: `application/json`
> Date: 2026-04-11

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

Returns all tiers for a program with full configuration, KPI summary, and cached member counts.

**Query Parameters:**

| Param | Type | Required | Default | Example |
|-------|------|----------|---------|---------|
| programId | int | YES | - | `977` |
| status | string (comma-separated) | NO | all statuses | `ACTIVE,DRAFT` |
| includeInactive | boolean | NO | false | `true` |

**Example Request:**
```
GET /v3/tiers?programId=977&status=ACTIVE,DRAFT
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
      "lastMemberCountRefresh": "2026-04-11T12:00:00Z"
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
          "startDate": "2025-01-01T00:00:00Z",
          "endDate": null
        },
        "eligibilityCriteria": {
          "criteriaType": "ACTIVITY_BASED",
          "activities": [
            {
              "type": "Any Purchase",
              "operator": "ANY",
              "value": null,
              "unit": null
            }
          ],
          "activityRelation": "OR",
          "membershipDuration": "Indefinite",
          "upgradeSchedule": "Immediately when eligibility is met",
          "nudges": "Welcome email on joining",
          "secondaryCriteriaEnabled": false
        },
        "renewalConfig": {
          "renewalCriteriaType": "Same as eligibility",
          "renewalCondition": null,
          "renewalSchedule": null,
          "nudges": null
        },
        "downgradeConfig": {
          "downgradeTo": {
            "tierName": null,
            "type": "LOWEST"
          },
          "downgradeSchedule": "MONTH_END",
          "expiryReminders": "Inactivity warning at 18 months",
          "shouldDowngrade": false
        },
        "benefitIds": ["bf-001", "bf-007", "bf-012"],
        "memberStats": {
          "memberCount": 1245,
          "lastRefreshed": "2026-04-11T12:00:00Z"
        },
        "metadata": {
          "createdBy": "user-admin-01",
          "createdAt": "2025-01-01T00:00:00Z",
          "updatedBy": "user-admin-01",
          "updatedAt": "2025-01-01T00:00:00Z",
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
          "startDate": "2025-01-01T00:00:00Z",
          "endDate": "2025-12-31T23:59:59Z"
        },
        "eligibilityCriteria": {
          "criteriaType": "ACTIVITY_BASED",
          "activities": [
            {
              "type": "Spending",
              "operator": "GTE",
              "value": 550,
              "unit": "RM"
            },
            {
              "type": "Transactions",
              "operator": "GTE",
              "value": 2,
              "unit": "transactions within a year"
            }
          ],
          "activityRelation": "AND",
          "membershipDuration": "12 months",
          "upgradeSchedule": "Immediately when eligibility is met",
          "nudges": "Upgrade congratulations email",
          "secondaryCriteriaEnabled": false
        },
        "renewalConfig": {
          "renewalCriteriaType": "Same as eligibility criteria",
          "renewalCondition": {
            "activities": [
              {
                "type": "Spending",
                "operator": "GTE",
                "value": 550,
                "unit": "RM"
              },
              {
                "type": "Transactions",
                "operator": "GTE",
                "value": 2,
                "unit": "transactions within a year"
              }
            ],
            "activityRelation": "AND"
          },
          "renewalSchedule": "End of month when duration ends",
          "nudges": "Renewal reminder 30 days before expiry"
        },
        "downgradeConfig": {
          "downgradeTo": {
            "tierName": "Bronze",
            "type": "SINGLE"
          },
          "downgradeSchedule": "MONTH_END",
          "expiryReminders": "Downgrade warning at 60 days before expiry",
          "shouldDowngrade": true
        },
        "benefitIds": ["bf-002", "bf-005", "bf-008", "bf-013"],
        "memberStats": {
          "memberCount": 667,
          "lastRefreshed": "2026-04-11T12:00:00Z"
        },
        "metadata": {
          "createdBy": "user-admin-01",
          "createdAt": "2025-01-01T00:00:00Z",
          "updatedBy": "user-admin-01",
          "updatedAt": "2025-06-15T10:30:00Z",
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
          "startDate": "2025-01-01T00:00:00Z",
          "endDate": "2025-12-31T23:59:59Z"
        },
        "eligibilityCriteria": {
          "criteriaType": "ACTIVITY_BASED",
          "activities": [
            {
              "type": "Spending",
              "operator": "GTE",
              "value": 900,
              "unit": "RM"
            },
            {
              "type": "Transactions",
              "operator": "GTE",
              "value": 2,
              "unit": "transactions within a year"
            }
          ],
          "activityRelation": "AND",
          "membershipDuration": "12 months",
          "upgradeSchedule": "Immediately when eligibility is met",
          "nudges": "VIP welcome package notification",
          "secondaryCriteriaEnabled": false
        },
        "renewalConfig": {
          "renewalCriteriaType": "Same as eligibility criteria",
          "renewalCondition": {
            "activities": [
              {
                "type": "Spending",
                "operator": "GTE",
                "value": 900,
                "unit": "RM"
              },
              {
                "type": "Transactions",
                "operator": "GTE",
                "value": 2,
                "unit": "transactions within a year"
              }
            ],
            "activityRelation": "AND"
          },
          "renewalSchedule": "End of month when duration ends",
          "nudges": "VIP renewal reminder with exclusive preview"
        },
        "downgradeConfig": {
          "downgradeTo": {
            "tierName": "Silver",
            "type": "SINGLE"
          },
          "downgradeSchedule": "DAILY",
          "expiryReminders": "Premium retention offer 90 days before expiry",
          "shouldDowngrade": true
        },
        "benefitIds": ["bf-003", "bf-006", "bf-009", "bf-011", "bf-014"],
        "memberStats": {
          "memberCount": 234,
          "lastRefreshed": "2026-04-11T12:00:00Z"
        },
        "metadata": {
          "createdBy": "user-admin-01",
          "createdAt": "2025-01-01T00:00:00Z",
          "updatedBy": "user-admin-02",
          "updatedAt": "2025-09-20T14:45:00Z",
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
          "startDate": "2026-01-01T00:00:00Z",
          "endDate": "2026-12-31T23:59:59Z"
        },
        "eligibilityCriteria": {
          "criteriaType": "ACTIVITY_BASED",
          "activities": [
            {
              "type": "Spending",
              "operator": "GTE",
              "value": 2000,
              "unit": "RM"
            }
          ],
          "activityRelation": "AND",
          "membershipDuration": "12 months",
          "upgradeSchedule": "Immediately when eligibility is met",
          "nudges": "Platinum welcome call from relationship manager",
          "secondaryCriteriaEnabled": false
        },
        "renewalConfig": {
          "renewalCriteriaType": "Same as eligibility criteria",
          "renewalCondition": {
            "activities": [
              {
                "type": "Spending",
                "operator": "GTE",
                "value": 1500,
                "unit": "RM"
              }
            ],
            "activityRelation": "AND"
          },
          "renewalSchedule": "End of month when duration ends",
          "nudges": "Platinum renewal exclusive offer 45 days before expiry"
        },
        "downgradeConfig": {
          "downgradeTo": {
            "tierName": "Gold",
            "type": "SINGLE"
          },
          "downgradeSchedule": "MONTH_END",
          "expiryReminders": "Platinum retention personal call 90 days before expiry",
          "shouldDowngrade": true
        },
        "benefitIds": [],
        "memberStats": {
          "memberCount": 0,
          "lastRefreshed": null
        },
        "metadata": {
          "createdBy": "user-admin-02",
          "createdAt": "2026-04-11T10:00:00Z",
          "updatedBy": "user-admin-02",
          "updatedAt": "2026-04-11T10:00:00Z",
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
→ 400 Bad Request (missing programId)
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
→ 200 OK (empty program -- not 404)
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
      "startDate": "2025-01-01T00:00:00Z",
      "endDate": "2025-12-31T23:59:59Z"
    },
    "eligibilityCriteria": {
      "criteriaType": "ACTIVITY_BASED",
      "activities": [
        {
          "type": "Spending",
          "operator": "GTE",
          "value": 900,
          "unit": "RM"
        },
        {
          "type": "Transactions",
          "operator": "GTE",
          "value": 2,
          "unit": "transactions within a year"
        }
      ],
      "activityRelation": "AND",
      "membershipDuration": "12 months",
      "upgradeSchedule": "Immediately when eligibility is met",
      "nudges": "VIP welcome package notification",
      "secondaryCriteriaEnabled": false
    },
    "renewalConfig": {
      "renewalCriteriaType": "Same as eligibility criteria",
      "renewalCondition": {
        "activities": [
          {
            "type": "Spending",
            "operator": "GTE",
            "value": 900,
            "unit": "RM"
          },
          {
            "type": "Transactions",
            "operator": "GTE",
            "value": 2,
            "unit": "transactions within a year"
          }
        ],
        "activityRelation": "AND"
      },
      "renewalSchedule": "End of month when duration ends",
      "nudges": "VIP renewal reminder with exclusive preview"
    },
    "downgradeConfig": {
      "downgradeTo": {
        "tierName": "Silver",
        "type": "SINGLE"
      },
      "downgradeSchedule": "DAILY",
      "expiryReminders": "Premium retention offer 90 days before expiry",
      "shouldDowngrade": true
    },
    "benefitIds": ["bf-003", "bf-006", "bf-009", "bf-011", "bf-014"],
    "memberStats": {
      "memberCount": 234,
      "lastRefreshed": "2026-04-11T12:00:00Z"
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
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedBy": "user-admin-02",
      "updatedAt": "2025-09-20T14:45:00Z",
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
→ 404 Not Found
```
```json
{
  "data": null,
  "errors": [{ "code": 404, "message": "Tier not found" }],
  "warnings": null
}
```

**When to use:**
- **Edit form pre-fill**: Fetch full document before showing the edit screen. The listing endpoint strips `engineConfig`.
- **Version comparison**: When a DRAFT has a `parentId`, fetch both the DRAFT and the ACTIVE (parentId) to compute a diff client-side.
- **Admin detail view**: Show full configuration including engine settings.

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
    "startDate": "2026-01-01T00:00:00Z",
    "endDate": "2026-12-31T23:59:59Z"
  },
  "eligibilityCriteria": {
    "criteriaType": "ACTIVITY_BASED",
    "activities": [
      {
        "type": "Spending",
        "operator": "GTE",
        "value": 2000,
        "unit": "RM"
      }
    ],
    "activityRelation": "AND",
    "membershipDuration": "12 months",
    "upgradeSchedule": "Immediately when eligibility is met",
    "nudges": "Platinum welcome call from relationship manager",
    "secondaryCriteriaEnabled": false
  },
  "renewalConfig": {
    "renewalCriteriaType": "Same as eligibility criteria",
    "renewalCondition": {
      "activities": [
        {
          "type": "Spending",
          "operator": "GTE",
          "value": 1500,
          "unit": "RM"
        }
      ],
      "activityRelation": "AND"
    },
    "renewalSchedule": "End of month when duration ends",
    "nudges": "Platinum renewal exclusive offer 45 days before expiry"
  },
  "downgradeConfig": {
    "downgradeTo": {
      "tierName": "Gold",
      "type": "SINGLE"
    },
    "downgradeSchedule": "MONTH_END",
    "expiryReminders": "Platinum retention personal call 90 days before expiry",
    "shouldDowngrade": true
  },
  "benefitIds": []
}
```

**Notes:**
- `serialNumber` is auto-assigned (next in sequence). Do NOT send it.
- `status` is set by the server based on MC toggle. Do NOT send it.
- `unifiedTierId` is generated by the server. Do NOT send it.
- `color` must be a valid hex code (e.g., `#E5E4E2`).
- `programId` is required.
- `basicDetails.name` must be unique within the program.

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
      "startDate": "2026-01-01T00:00:00Z",
      "endDate": "2026-12-31T23:59:59Z"
    },
    "eligibilityCriteria": { "..." : "same as request" },
    "renewalConfig": { "..." : "same as request" },
    "downgradeConfig": { "..." : "same as request" },
    "benefitIds": [],
    "memberStats": { "memberCount": 0, "lastRefreshed": null },
    "metadata": {
      "createdBy": "user-admin-02",
      "createdAt": "2026-04-11T10:00:00Z",
      "updatedBy": "user-admin-02",
      "updatedAt": "2026-04-11T10:00:00Z",
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
→ 409 Conflict
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
→ 400 Bad Request
```
```json
{
  "data": null,
  "errors": [
    { "code": 400, "message": "basicDetails.name is required" },
    { "code": 400, "message": "eligibilityCriteria.criteriaType must match program criteria type (ACTIVITY_BASED)" }
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
  "eligibilityCriteria": {
    "activities": [
      {
        "type": "Spending",
        "operator": "GTE",
        "value": 1200,
        "unit": "RM"
      }
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
      "startDate": "2025-01-01T00:00:00Z",
      "endDate": "2025-12-31T23:59:59Z"
    },
    "eligibilityCriteria": {
      "criteriaType": "ACTIVITY_BASED",
      "activities": [
        {
          "type": "Spending",
          "operator": "GTE",
          "value": 1200,
          "unit": "RM"
        }
      ],
      "activityRelation": "AND",
      "membershipDuration": "12 months",
      "upgradeSchedule": "Immediately when eligibility is met",
      "nudges": "VIP welcome package notification",
      "secondaryCriteriaEnabled": false
    },
    "renewalConfig": { "..." : "inherited from ACTIVE version" },
    "downgradeConfig": { "..." : "inherited from ACTIVE version" },
    "benefitIds": ["bf-003", "bf-006", "bf-009", "bf-011", "bf-014"],
    "memberStats": { "memberCount": 234, "lastRefreshed": "2026-04-11T12:00:00Z" },
    "metadata": {
      "createdBy": "user-admin-02",
      "createdAt": "2026-04-11T14:00:00Z",
      "updatedBy": "user-admin-02",
      "updatedAt": "2026-04-11T14:00:00Z",
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

**Error: editing a STOPPED tier:**
```
PUT /v3/tiers/661a... (STOPPED tier)
→ 400 Bad Request
```
```json
{
  "data": null,
  "errors": [{ "code": 400, "message": "Cannot edit a tier in STOPPED status. Allowed transitions: none." }],
  "warnings": null
}
```

---

## 5. Delete Tier

### `DELETE /v3/tiers/{tierId}`

Soft-deletes a tier. Behavior depends on the tier's **current status** and the **MC toggle**:

| Current Status | MC Enabled | MC Disabled |
|----------------|-----------|-------------|
| **DRAFT** | Immediate removal (no MC gate -- tier was never live) | Immediate removal |
| **ACTIVE** | Creates PendingChange. Tier stays ACTIVE until approved. | Immediate STOPPED + SQL sync. |
| **PENDING_APPROVAL** | Not allowed (reject the pending change first) | Not allowed |
| **STOPPED / SNAPSHOT** | Not allowed (terminal states) | Not allowed |

**Example Request:**
```
DELETE /v3/tiers/661a3f2e8b1c4d5e6f7a8b9e
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

**Example Response (204 No Content, MC disabled):**
```
HTTP/1.1 204 No Content
```

**Example Response (200 OK, MC enabled -- PendingChange created):**
```json
{
  "data": {
    "objectId": "661d8c4b1e5f6a7b8c9d0e1f",
    "entityType": "TIER",
    "entityId": "ut-977-003",
    "changeType": "DELETE",
    "status": "PENDING_APPROVAL",
    "requestedBy": "user-admin-02",
    "requestedAt": "2026-04-11T15:00:00Z",
    "reviewedBy": null,
    "reviewedAt": null,
    "comment": null
  },
  "errors": null,
  "warnings": null
}
```

**Error: tier has PartnerProgramSlabs:**
```
DELETE /v3/tiers/661a... (has partner program refs)
→ 409 Conflict
```
```json
{
  "data": null,
  "errors": [{ "code": 409, "message": "Cannot stop tier 'Gold' -- it has 2 active partner program slab mappings. Remove them first." }],
  "warnings": null
}
```

**Error: cannot delete base tier with members:**
```
DELETE /v3/tiers/661a... (base tier, serialNumber=1, members=1245)
→ 409 Conflict
```
```json
{
  "data": null,
  "errors": [{ "code": 409, "message": "Cannot stop base tier 'Bronze' -- 1245 members are currently assigned to it." }],
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
    "requestedAt": "2026-04-11T11:00:00Z",
    "reviewedBy": null,
    "reviewedAt": null,
    "comment": null
  },
  "errors": null,
  "warnings": null
}
```

**Side effect:** The tier's status changes from DRAFT to PENDING_APPROVAL.

**Error: tier is not in DRAFT status:**
```json
{
  "data": null,
  "errors": [{ "code": 400, "message": "Tier is in ACTIVE status. Only DRAFT tiers can be submitted for approval." }],
  "warnings": null
}
```

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
    "requestedAt": "2026-04-11T11:00:00Z",
    "reviewedBy": "user-admin-01",
    "reviewedAt": "2026-04-11T13:30:00Z",
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

**Error: Thrift sync failed:**
```json
{
  "data": null,
  "errors": [{ "code": 500, "message": "Failed to sync tier to backend. Approval rolled back. Please retry." }],
  "warnings": null
}
```

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
    "orgId": 100458,
    "programId": 977,
    "entityType": "TIER",
    "entityId": "661c7b3a0d4e5f6a7b8c9d0e",
    "changeType": "UPDATE",
    "status": "REJECTED",
    "requestedBy": "user-admin-02",
    "requestedAt": "2026-04-11T14:00:00Z",
    "reviewedBy": "user-admin-01",
    "reviewedAt": "2026-04-11T15:00:00Z",
    "comment": "Gold threshold too low -- 1200 RM would overlap with Silver at 550 RM. Please increase to at least 1500 RM."
  },
  "errors": null,
  "warnings": null
}
```

**Side effect:** Tier status: PENDING_APPROVAL -> DRAFT (can be edited and re-submitted).

**Error: missing comment:**
```json
{
  "data": null,
  "errors": [{ "code": 400, "message": "Comment is required when rejecting a change" }],
  "warnings": null
}
```

---

## 9. List Pending Changes

### `GET /v3/maker-checker/pending`

Lists all pending changes awaiting approval.

**Query Parameters:**

| Param | Type | Required | Example |
|-------|------|----------|---------|
| entityType | string | NO | `TIER` |
| programId | int | NO | `977` |

**Example Request:**
```
GET /v3/maker-checker/pending?entityType=TIER&programId=977
```

**Example Response (200 OK):**
```json
{
  "data": [
    {
      "objectId": "661e9d5c2f6a7b8c9d0e1f2a",
      "orgId": 100458,
      "programId": 977,
      "entityType": "TIER",
      "entityId": "661b5a1f9c2d3e4f5a6b7c8d",
      "changeType": "CREATE",
      "status": "PENDING_APPROVAL",
      "requestedBy": "user-admin-02",
      "requestedAt": "2026-04-11T11:00:00Z",
      "reviewedBy": null,
      "reviewedAt": null,
      "comment": null
    }
  ],
  "errors": null,
  "warnings": null
}
```

**Empty result:**
```json
{
  "data": [],
  "errors": null,
  "warnings": null
}
```

---

## 10. Get Change Detail

### `GET /v3/maker-checker/{changeId}`

Returns the full pending change document including the embedded payload snapshot. The approver uses this to review what was changed before approving or rejecting.

**Path Parameter:** `changeId` = the PendingChange `objectId`

**Example Request:**
```
GET /v3/maker-checker/661e9d5c2f6a7b8c9d0e1f2a
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

**Example Response (200 OK -- CREATE change):**
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
    "payload": {
      "objectId": "661b5a1f9c2d3e4f5a6b7c8d",
      "unifiedTierId": "ut-977-004",
      "programId": 977,
      "status": "PENDING_APPROVAL",
      "parentId": null,
      "version": 1,
      "basicDetails": {
        "name": "Platinum",
        "description": "Elite tier for top customers",
        "color": "#E5E4E2",
        "serialNumber": 4,
        "startDate": "2026-01-01T00:00:00Z",
        "endDate": "2026-12-31T23:59:59Z"
      },
      "eligibilityCriteria": {
        "criteriaType": "ACTIVITY_BASED",
        "activities": [
          { "type": "Spending", "operator": "GTE", "value": 2000, "unit": "RM" }
        ],
        "activityRelation": "AND",
        "membershipDuration": "12 months",
        "upgradeSchedule": "Immediately when eligibility is met",
        "nudges": "Platinum welcome call from relationship manager",
        "secondaryCriteriaEnabled": false
      },
      "renewalConfig": { "..." : "full config" },
      "downgradeConfig": { "..." : "full config" },
      "benefitIds": [],
      "engineConfig": { "..." : "full engine config for round-trip" },
      "metadata": {
        "createdBy": "user-admin-02",
        "createdAt": "2026-04-11T10:00:00Z",
        "updatedBy": "user-admin-02",
        "updatedAt": "2026-04-11T10:00:00Z",
        "updatedViaNewUI": true,
        "sqlSlabId": null
      }
    },
    "requestedBy": "user-admin-02",
    "requestedAt": "2026-04-11T11:00:00Z",
    "reviewedBy": null,
    "reviewedAt": null,
    "comment": null
  },
  "errors": null,
  "warnings": null
}
```

**For UPDATE changes:** The `payload` contains the full NEW state of the tier. To show a diff, also fetch the current ACTIVE version via `GET /v3/tiers/{payload.parentId}` and compare client-side.

**For DELETE changes:** The `payload` contains the tier that will be stopped. The `changeType` is `"DELETE"`.

**Error Responses:**

```
GET /v3/maker-checker/nonexistent-id
→ 404 Not Found
```
```json
{
  "data": null,
  "errors": [{ "code": 404, "message": "Pending change not found" }],
  "warnings": null
}
```

---

## 11. Maker-Checker Toggle Status

### `GET /v3/maker-checker/config`

Returns whether maker-checker is enabled for a given program and entity type. Call this on page load to determine the save/submit flow in the UI.

**Query Parameters:**

| Param | Type | Required | Example |
|-------|------|----------|---------|
| programId | int | YES | `977` |
| entityType | string | YES | `TIER` |

**Example Request:**
```
GET /v3/maker-checker/config?programId=977&entityType=TIER
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

**Example Response (200 OK -- MC enabled):**
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

**Example Response (200 OK -- MC disabled):**
```json
{
  "data": {
    "programId": 977,
    "entityType": "TIER",
    "makerCheckerEnabled": false
  },
  "errors": null,
  "warnings": null
}
```

**UI behavior based on response:**

| `makerCheckerEnabled` | Create Flow | Edit Flow | Delete Flow |
|-----------------------|------------|-----------|-------------|
| `true` | Saves as DRAFT. Show "Submit for Approval" button. | Creates versioned DRAFT. Show "Submit for Approval". | Creates PendingChange. Approver must confirm. |
| `false` | Saves as ACTIVE immediately. Syncs to SQL. No approval step. | Applies edit immediately. Syncs to SQL. | Sets STOPPED immediately. No approval step. |

---

## 12. Complete Flow Example: Create + Submit + Approve

### Step 1: Create Platinum tier (MC enabled -- becomes DRAFT)
```
POST /v3/tiers
→ 201 Created, status: "DRAFT", objectId: "661b5a..."
```

### Step 2: Submit for approval
```
POST /v3/maker-checker/submit
Body: { "entityType": "TIER", "entityId": "661b5a..." }
→ 200 OK, changeId: "661e9d..."
```
Tier status changes: DRAFT -> PENDING_APPROVAL

### Step 3: Approve
```
POST /v3/maker-checker/661e9d.../approve
Body: { "comment": "Looks good" }
→ 200 OK
```
Tier status changes: PENDING_APPROVAL -> ACTIVE
SQL sync happens. `metadata.sqlSlabId` populated.

### Step 4: Verify in listing
```
GET /v3/tiers?programId=977
→ Platinum now appears with status: "ACTIVE" and sqlSlabId set
```

---

## 13. Complete Flow Example: Edit ACTIVE Tier (Versioned)

### Step 1: Edit Gold tier (ACTIVE, objectId: "661a...9e")
```
PUT /v3/tiers/661a...9e
Body: { "basicDetails": { "name": "Gold Plus" }, "eligibilityCriteria": { "activities": [{ "type": "Spending", "operator": "GTE", "value": 1200, "unit": "RM" }] } }
→ 200 OK, NEW objectId: "661c7b...", status: "DRAFT", parentId: "661a...9e"
```
The original Gold (objectId: "661a...9e") stays ACTIVE. A new DRAFT is created.

### Step 2: Listing shows BOTH
```
GET /v3/tiers?programId=977
→ Gold (ACTIVE, threshold 900) + Gold Plus (DRAFT, threshold 1200, parentId: 661a...9e)
```

### Step 3: Submit + Approve
```
POST /v3/maker-checker/submit + POST /v3/maker-checker/{id}/approve
```
Result: Gold Plus -> ACTIVE. Original Gold -> SNAPSHOT.

---

## 14. Complete Flow Example: Delete (Draft vs Active)

### Deleting a DRAFT tier (immediate -- no MC gate)
```
DELETE /v3/tiers/661b5a1f9c2d3e4f5a6b7c8d
→ 204 No Content
```
The DRAFT document is removed from MongoDB. No PendingChange is created because the tier was never live.

### Deleting an ACTIVE tier (MC enabled -- requires approval)
```
DELETE /v3/tiers/661a3f2e8b1c4d5e6f7a8b9e
→ 200 OK, PendingChange with changeType: "DELETE"
```
A PendingChange is created. The tier stays ACTIVE until the approver approves the stop.

### Deleting an ACTIVE tier (MC disabled -- immediate)
```
DELETE /v3/tiers/661a3f2e8b1c4d5e6f7a8b9e
→ 204 No Content
```
Status set to STOPPED immediately. SQL sync marks the slab as STOPPED.

---

## 15. Field Reference

### Activity Operators
| Operator | Meaning | Example |
|----------|---------|---------|
| `GTE` | Greater than or equal | Spending >= 550 RM |
| `LTE` | Less than or equal | Transactions <= 10 |
| `EQ` | Equal to | Visits = 5 |
| `ANY` | Any value (no threshold) | Any Purchase |

### Tier Statuses (for UI badge rendering)
| Status | Badge Color | User Can... |
|--------|------------|-------------|
| `DRAFT` | Grey | Edit, Submit, Delete |
| `PENDING_APPROVAL` | Amber | View (approver can Approve/Reject) |
| `ACTIVE` | Green | Edit (creates new version), Stop |
| `STOPPED` | Red | View only |
| `SNAPSHOT` | Dark grey | View only (archived version) |

### Downgrade Schedules
| Value | Meaning | Badge Color in UI |
|-------|---------|------------------|
| `MONTH_END` | Downgrade evaluated at end of month | Yellow |
| `DAILY` | Downgrade evaluated daily | Light yellow |

---

## 16. Legacy API Mapping Reference

The production legacy API (`/loyalty/api/v1/strategy/tier-strategy/{programId}`) uses a different data format. This table maps legacy fields to the new `/v3/tiers` API.

### Criteria Type Mapping

| Production (`upgrade.current_value_type`) | New API (`eligibilityCriteria.criteriaType`) |
|------------------------------------------|----------------------------------------------|
| `CUMULATIVE_PURCHASES` | `ACTIVITY_BASED` |
| `CURRENT_POINTS` | `CURRENT_POINTS` |
| `LIFETIME_POINTS` | `LIFETIME_POINTS` |
| `LIFETIME_PURCHASES` | `LIFETIME_PURCHASES` |
| `TRACKER_VALUE` | `TRACKER_VALUE` |

### Threshold Format

| Production | New API |
|-----------|---------|
| `upgrade.threshold_value: ["2000","5000","12000"]` — program-wide CSV array, N-1 values for N tiers (base tier has no threshold). Position = serialNumber - 2. | `eligibilityCriteria.activities[].value: 2000` — per-tier individual value. TierChangeApplier joins/splits during sync. |

### Downgrade Field Mapping

| Production (`downgrade.*`) | New API | Section |
|----------------------------|---------|---------|
| `is_active` | `engineConfig.downgradeEngineConfig.isActive` | engineConfig |
| `should_downgrade` | `downgradeConfig.shouldDowngrade` | downgradeConfig |
| `downgrade_to` ("LOWEST"/"SINGLE"/"THRESHOLD") | `downgradeConfig.downgradeTo.type` | downgradeConfig |
| `daily_downgrade_enabled: true` | `downgradeConfig.downgradeSchedule: "DAILY"` | downgradeConfig |
| `daily_downgrade_enabled: false` | `downgradeConfig.downgradeSchedule: "MONTH_END"` | downgradeConfig |
| `start_date` | `engineConfig.periodConfig.startDate` | engineConfig |
| `time_period` | `engineConfig.periodConfig.value` | engineConfig |
| `condition` ("SLAB_UPGRADE", etc.) | `engineConfig.periodConfig.type` | engineConfig |
| `condition_always` | `engineConfig.downgradeEngineConfig.conditionAlways` | engineConfig |
| `purchase`, `num_visits`, `points`, `tracker_count` | `engineConfig.downgradeEngineConfig.conditionValues.*` | engineConfig |
| `renewal_order_string` | `engineConfig.downgradeEngineConfig.renewalOrderString` | engineConfig |
| `expression_relation` | `engineConfig.expressionRelation` | engineConfig |
| `original_expression` | `engineConfig.customExpression` | engineConfig |
| `isFixedTypeWithoutYear` | `engineConfig.isFixedTypeWithoutYear` | engineConfig |
| `minimum_duration` | `engineConfig.periodConfig.minimumDuration` | engineConfig |
| `renewalWindowType` | `engineConfig.renewalWindowType` | engineConfig |
| `computationWindowStartValue` | `engineConfig.periodConfig.computationWindowStartValue` | engineConfig |
| `computationWindowEndValue` | `engineConfig.periodConfig.computationWindowEndValue` | engineConfig |

### Top-Level / Upgrade Mapping

| Production | New API | Section |
|-----------|---------|---------|
| `slabId` | `metadata.sqlSlabId` | metadata |
| `programId` (string) | `programId` (int) | top-level |
| `name` | `basicDetails.name` | basicDetails |
| `description` | `basicDetails.description` | basicDetails |
| `color` | `basicDetails.color` | basicDetails |
| `isAdvanceSetting` | `engineConfig.isAdvanceSetting` | engineConfig |
| `addDefaultCommunication` | `engineConfig.addDefaultCommunication` | engineConfig |
| `upgrade.slab_upgrade_mode` | `engineConfig.slabUpgradeMode` | engineConfig |
| `upgrade.secondary_criteria_enabled` | `eligibilityCriteria.secondaryCriteriaEnabled` | eligibilityCriteria |

### pointsSaveData (NOT in new API)

The production response includes `pointsSaveData` (allocations, redemptions, expirys). These are **NOT included** in the new `/v3/tiers` API by design:
- Points strategies are managed by the engine, not by tier CRUD.
- When a new slab is created via Thrift, the engine auto-extends all allocation/expiry CSVs.
- TierChangeApplier only sends SLAB_UPGRADE and SLAB_DOWNGRADE strategies.

### Type Differences

| Field | Production | New API | Note |
|-------|-----------|---------|------|
| `programId` | `"977"` (string) | `977` (int) | UI should handle both |
| `threshold_value` | `["2000"]` (string[]) | `2000` (number) | Per-tier number in new API |
| `time_period` | `"12"` (string) | `12` (number) | New API uses proper types |

---

## 17. Important Notes for UI Team

1. **`serialNumber` is auto-assigned and immutable.** Never send it in create/update. It determines tier ordering.
2. **`unifiedTierId` persists across versions.** When an ACTIVE tier is edited, the new DRAFT has the same `unifiedTierId` but a different `objectId`. Use `unifiedTierId` to track a tier's identity across versions.
3. **`parentId` indicates a versioned edit.** If a DRAFT has a non-null `parentId`, it is a pending edit of an ACTIVE tier. The `parentId` is the ACTIVE version's `objectId`.
4. **`sqlSlabId` is null for DRAFT tiers.** It is populated only after MC approval syncs to SQL. Use it to link to legacy systems if needed.
5. **Member counts are cached.** `memberStats.lastRefreshed` shows when the count was last updated (every ~10 minutes). Display it to set expectations.
6. **`engineConfig` is NOT returned in the listing response.** It is hidden engine config for round-trip fidelity. Only visible in the full tier detail endpoint (if needed later).
7. **All dates are ISO-8601 UTC.** Convert to user's timezone for display.
8. **The `benefitIds` array contains benefit ObjectIds.** Fetch benefit details via a separate `GET /v3/benefits/{benefitId}` endpoint (out of scope for this pipeline).
9. **Call `GET /v3/maker-checker/config` on page load** to determine whether to show MC flow (Submit for Approval) or direct-save flow.
10. **For version comparison (edit review):** Fetch DRAFT via `GET /v3/tiers/{draftId}` and ACTIVE via `GET /v3/tiers/{draft.parentId}`. Compute diff client-side.
11. **Deleting a DRAFT does NOT require MC approval.** It is removed immediately since it was never live.

---

## 18. Not In Scope (This Release)

These features are **not available** in the current API. Do not build UI for them.

| Feature | Reason | Future |
|---------|--------|--------|
| **Tier Reorder** | `serialNumber` is immutable and auto-assigned. Tiers cannot be reordered or inserted between existing tiers. | No current plan. |
| **Tier Settings** (program-level) | The "Tier Settings" button in the UI prototype maps to program-level slab settings (upgrade mode, point category, etc.). API not designed yet. | Will be designed in a future pipeline run. |
| **Version History / Diff** | SNAPSHOT documents are preserved in MongoDB when a version is replaced. A dedicated history endpoint is not built yet. | Architecture supports it. Planned for Change Log (E1-US5). |
| **Bulk Operations** | No batch create/update/delete. One tier at a time. | No current plan. |
| **Real-time Member Counts** | `memberStats.memberCount` is cached (refreshed every ~10 minutes via cron). No live query or manual refresh endpoint. | Cron-based. No on-demand refresh API. |
