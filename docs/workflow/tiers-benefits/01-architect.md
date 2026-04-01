# 01 — Architecture: Tier & Benefit CRUD + Maker-Checker APIs

> Phase: Architect (01)
> Date: 2026-04-01
> Input: 00-ba.md, brdQnA.md, brd-raw.md, session-memory.md
> Output feeds: 02-analyst.md

---

## Current State Summary

### Entity & Data Model

**MySQL (legacy, read-only from our perspective):**
- `program_slabs` table: `(id, org_id)` composite PK, `program_id`, `serial_number`, `name`, `description`, `created_on`, `metadata`. Unique key on `(org_id, program_id, serial_number)`. The `ProgramSlab` JPA entity maps to this.
- `program` table: contains `slab_upgrade_mode` (EAGER/DYNAMIC/LAZY), `slab_upgrade_stategy_id`, `slab_upgrade_rule_identifier`, `slab_upgrade_point_category_id`. The `Program` JPA entity has a `List<ProgramSlab>` and `List<Strategy>`.
- `strategies` table: `(id, org_id)` composite PK, `program_id`, `strategy_type_id`, `name`, `property_values` (serialized config), `owner` (LOYALTY/CAMPAIGN). Unique key on `(program_id, strategy_type_id, name)`. Strategy types include `SLAB_UPGRADE`, `SLAB_DOWNGRADE`, `POINT_ALLOCATION`, `POINT_EXPIRY`, etc.
- `customer_enrollment` table: `(id, org_id)` composite PK, `current_slab_id`, `slab_expiry_date`, `lifetime_purchases`, `visits`. This is where member-tier assignments live.
- `benefits_awarded_stats` table: awards ledger per customer, scoped by `(org_id, customer_id)`, with `benefit_type` enum, `context_type` (PROGRAM/PROMOTION), `context_identifier`.

**MongoDB (existing collections in `emf` database):**
- `org_configuration` — org-level ruleset config, managed by `OrgConfigDaoImpl`
- `unified_promotions` — maker-checker promotions, managed by `UnifiedPromotionDaoImpl` (read-only in EMF; primary owner is intouch-api-v3)
- All MongoDB DAOs extend `BaseMongoDaoImpl<T extends BaseMongoEntity>`, which uses `MongoDataSourceManager` for org-sharded connections and `MongoTemplateImpl` for CRUD operations.
- Database names in use: `emf`, `peb`. Collections are defined as constants in DAO interfaces.

### REST API Layer (pointsengine-emf)

- Controllers live in `com.capillary.shopbook.pointsengine.RESTEndpoint.controller.impl`.
- Use `@Controller` (not `@RestController`), generated from Swagger codegen. Implement API interfaces.
- `LoggerInterceptor` extracts `X-CAP-ORG-ID` header and sets `ShardContext` (ThreadLocal). This is the existing multi-tenancy threading pattern.
- Validation uses a `ValidatorFactory` pattern: factory returns a list of `PromotionValidator` implementations based on `ValidatorTypes` enum. Each validator implements a `validate()` method.
- `GlobalExceptionHandler` (`@RestControllerAdvice`) handles `MethodArgumentNotValidException`, `RequestValidationException`, and `RuntimeException`.
- Existing controllers: `ProgramsApiController`, `OrgConfigController`, `PromotionsController`, `MilestoneConfigController`, `BulkOrgConfigUpdateController`.

### Maker-Checker Reference (intouch-api-v3)

- `UnifiedPromotion` entity: `@Document(collection = "unified_promotions")`. Key fields: `objectId` (MongoDB `_id`), `unifiedPromotionId` (immutable business ID), `parentId` (links draft to active parent on edit), `version` (integer, starts at 1), `comments` (review comment, max 150 chars), `metadata.status` (PromotionStatus enum).
- `PromotionStatus` enum: `DRAFT, ACTIVE, PAUSED, PENDING_APPROVAL, STOPPED, SNAPSHOT, LIVE, UPCOMING, COMPLETED, PUBLISH_FAILED`.
- `StatusTransitionValidator`: `EnumMap<CurrentStatus, Set<PromotionAction>>` defining valid transitions. States: DRAFT -> SUBMIT_FOR_APPROVAL; PENDING_APPROVAL -> APPROVE, REJECT; ACTIVE -> PAUSE, STOP; PAUSED -> APPROVE (resume), STOP; STOPPED -> (terminal).
- `PromotionAction` enum: `SUBMIT_FOR_APPROVAL, APPROVE, REJECT, PAUSE, STOP, RESUME, REVOKE`. Has `getNormalizedAction()` (RESUME -> APPROVE, REVOKE -> REJECT).
- `UnifiedPromotionFacade.changePromotionStatus()`: annotated `@Lockable(key = "'lock_promotion_status_' + #orgId + '_' + #promotionId", ttl = 300000, acquireTime = 5000)`. Validates transition, then switches on normalized action.
- Approval flow for edits: active promotion -> SNAPSHOT, draft -> inherits parent's status (ACTIVE or PAUSED).
- `PromotionReviewRequest` DTO: `approvalStatus` (required), `comment` (max 150 chars).
- `@Lockable` is a custom annotation with `key` (SpEL), `ttl` (default 5000ms), `acquireTime` (default 500ms). Backed by a distributed lock (likely Redis).
- `UnifiedPromotionEditOrchestrator`: annotated `@Lockable` on `orchestrateEdits()`. Detects changes, applies edits to downstream systems (Points Engine rulesets), with rollback factory for failure recovery.

### Key Observations

1. **No REST tier CRUD exists** — `ProgramsApiController` manages promotions and program configs, not tier/slab CRUD.
2. **MongoDB DAO pattern is well-established** — extending `BaseMongoDaoImpl`, using `MongoDataSourceManager` for org-sharded connections, constants for DB/collection names.
3. **OrgId threading is via header** — `X-CAP-ORG-ID` header -> `LoggerInterceptor` -> `ShardContext` (ThreadLocal). This is the pattern to follow.
4. **Validation uses factory pattern** — not Bean Validation. The factory returns ordered lists of validator implementations.
5. **The `@Lockable` annotation lives in intouch-api-v3** — it does not exist in emf-parent. We need our own distributed lock mechanism.

---

## Pattern Options Considered

| Pattern | What It Solves | Fit with Codebase | Tradeoffs | Recommended? |
|---------|---------------|-------------------|-----------|-------------|
| **Document-per-version (UnifiedPromotion pattern)** | Maker-checker with version history. Each edit creates a new document with parentId. Active -> SNAPSHOT on approval. | **High** — This is THE reference pattern in the org. Already proven in production for promotions. | Gain: consistency with existing codebase, proven at scale. Cost: query complexity (must filter by status, handle parent/child lookups). | **Yes** |
| **Single-document with embedded draft (shadow fields)** | Simpler model — one doc per tier, with `draft` subdocument holding pending changes. | **Low** — No precedent in codebase. UnifiedPromotion uses separate documents. | Gain: simpler queries, no parent/child linkage. Cost: breaks from established pattern, harder to track version history, concurrent edit detection is harder. | No |
| **Event Sourcing** | Full audit trail, temporal queries, replay. | **Low** — No event sourcing anywhere in the codebase. Massive complexity increase. | Gain: complete history. Cost: enormous complexity, no team experience, overkill for config management. | No |
| **CQRS (Command Query Responsibility Segregation)** | Separate read/write models for different query patterns. | **Low** — Not used in the codebase. The listing endpoints and write endpoints operate on the same MongoDB documents. | Gain: optimized reads. Cost: dual model maintenance, sync complexity. Not justified by traffic patterns (config management, not high-throughput). | No |
| **Strategy + Factory for validation** | Composable, ordered validation chains per operation type. | **High** — This is the exact pattern in `ValidatorFactory` for promotions. | Gain: consistency, extensibility. Cost: more classes than Bean Validation. But the codebase already does this. | **Yes** |
| **Bean Validation (JSR-380) for request DTOs** | Standard annotation-based validation on request objects. | **Medium** — `@Valid` is used on controller method params, `@NotNull`/`@Size` on UnifiedPromotion fields. But business validation uses factory pattern. | Gain: less boilerplate for simple field presence/format checks. Cost: cannot handle cross-field or cross-document validation (e.g., "downgrade target must reference existing tier"). | **Yes (layer 1 only)** |
| **Distributed locking via @Lockable-like annotation** | Prevent concurrent status changes on same entity. | **High** — Exact pattern used in intouch-api-v3. | Gain: proven pattern, clean annotation-driven API. Cost: need to implement the annotation + AOP aspect in emf-parent (or add as a shared library). Redis dependency. | **Yes** |

### Chosen Approach

1. **Document-per-version** (UnifiedPromotion pattern) for tier and benefit configs.
2. **Two-layer validation**: Bean Validation on DTOs for simple field checks (layer 1) + custom `TierValidatorFactory`/`BenefitValidatorFactory` returning ordered validator chains for business rules (layer 2). This matches both patterns found in the codebase.
3. **Distributed lock annotation** modeled on `@Lockable` for status change concurrency control.
4. **Status state machine** modeled on `StatusTransitionValidator` with `EnumMap<ConfigStatus, Set<ConfigAction>>`.

---

## Problem Statement

Program managers have no API to create, update, or manage tier and benefit configurations with approval workflows. The existing MySQL-based tier config has no CRUD REST API and no maker-checker. Benefits exist only as promotion side-effects with no standalone entity. This iteration builds the MongoDB-backed CRUD + maker-checker API layer in emf-parent, following the UnifiedPromotion pattern from intouch-api-v3.

---

## Scope

### In Scope
- MongoDB document model for `TierConfig` and `BenefitConfig` with full BRD fields
- REST controllers for Tier CRUD, Benefit CRUD, status transitions, and approval review
- Maker-checker lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE (approve) / DRAFT (reject); ACTIVE -> PAUSED -> ACTIVE (resume); ACTIVE/PAUSED -> STOPPED (terminal); SNAPSHOT (archived on edit approval)
- Validation at API layer (two-layer: Bean Validation + business validator chain)
- Multi-tenancy via `X-CAP-ORG-ID` header + `ShardContext`
- Distributed locking for status change concurrency
- Tier-benefit linkage as embedded references in TierConfig

### Out of Scope
- Writing to legacy MySQL strategy/program_slabs tables (no dual writes)
- Synchronizing new MongoDB configs with EMF evaluation pipeline
- Audit trail / change log
- Simulation / impact preview
- aiRa integration
- Frontend
- Notifications on approval events
- Custom fields for benefits

---

## Proposed Modules / Components

### 1. `tier-config` — Tier configuration domain
- `TierConfig` — MongoDB document model (collection: `tier_configs`, database: `emf`)
- `TierConfigDao` / `TierConfigDaoImpl` — DAO extending `BaseMongoDaoImpl<TierConfig>`
- `TierConfigService` — Business logic: create, update, list, status transitions
- `TierConfigController` — REST controller: `/api/v1/tiers`
- `TierValidatorFactory` — Returns ordered validator chain per operation type
- Individual validators: `TierNameUniquenessValidator`, `EligibilityThresholdValidator`, `DowngradeTargetValidator`, `SerialNumberValidator`, `LinkedBenefitValidator`

### 2. `benefit-config` — Benefit configuration domain
- `BenefitConfig` — MongoDB document model (collection: `benefit_configs`, database: `emf`)
- `BenefitConfigDao` / `BenefitConfigDaoImpl` — DAO extending `BaseMongoDaoImpl<BenefitConfig>`
- `BenefitConfigService` — Business logic: create, update, list, status transitions
- `BenefitConfigController` — REST controller: `/api/v1/benefits`
- `BenefitValidatorFactory` — Validator chain factory
- Individual validators: `BenefitNameUniquenessValidator`, `BenefitTypeParameterValidator`, `LinkedTierValidator`

### 3. `config-lifecycle` — Shared maker-checker and status management
- `ConfigStatus` enum: `DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, STOPPED, SNAPSHOT`
- `ConfigAction` enum: `SUBMIT_FOR_APPROVAL, APPROVE, REJECT, PAUSE, STOP, RESUME`
- `ConfigStatusTransitionValidator` — `EnumMap<ConfigStatus, Set<ConfigAction>>`
- `StatusChangeRequest` / `ReviewRequest` DTOs
- `@DistributedLock` annotation + AOP aspect (modeled on `@Lockable`)
- `VersioningHelper` — shared logic for parentId/version management

### 4. `config-common` — Shared utilities
- `ConfigBaseDocument` — abstract base class for TierConfig/BenefitConfig (orgId, programId, status, version, parentId, entityId, comments, timestamps, createdBy, lastModifiedBy)
- Response DTOs: `TierConfigResponse`, `BenefitConfigResponse`, `ValidationErrorResponse`
- `ConfigExceptionHandler` — extension to `GlobalExceptionHandler` for config-specific exceptions

---

## Dependencies Between Modules

```
tier-config ──────> config-lifecycle (status management, locking)
    │                       │
    │                       v
    │               config-common (base document, DTOs, exceptions)
    │                       ^
    v                       │
benefit-config ────> config-lifecycle
```

- `tier-config` depends on `config-lifecycle` and `config-common`
- `benefit-config` depends on `config-lifecycle` and `config-common`
- `tier-config` has a soft dependency on `benefit-config` (validates linked benefit IDs)
- `benefit-config` has a soft dependency on `tier-config` (validates linked tier IDs)
- Both integrate with existing `BaseMongoDaoImpl`, `MongoDataSourceManager`, `ShardContext`, `LoggerInterceptor`

---

## API Design Approach

### URL Structure

All endpoints are prefixed with `/api/v1` (per G-06.5: version APIs from day one).

**Tier endpoints:**
- `GET /api/v1/tiers?programId={programId}&status={status}&includeDraftDetails={bool}` — List tiers
- `POST /api/v1/tiers` — Create tier
- `PUT /api/v1/tiers/{tierId}` — Update tier (tierId is the immutable business ID, not the MongoDB ObjectId)
- `PUT /api/v1/tiers/{tierId}/status` — Submit for approval, pause, stop, resume
- `POST /api/v1/tiers/{tierId}/review` — Approve or reject
- `GET /api/v1/tiers/approvals?programId={programId}` — List pending approvals

**Benefit endpoints:**
- `GET /api/v1/benefits?programId={programId}&status={status}&type={type}&category={category}` — List benefits
- `POST /api/v1/benefits` — Create benefit
- `PUT /api/v1/benefits/{benefitId}` — Update benefit
- `PUT /api/v1/benefits/{benefitId}/status` — Submit for approval, pause, stop, resume
- `POST /api/v1/benefits/{benefitId}/review` — Approve or reject
- `GET /api/v1/benefits/approvals?programId={programId}` — List pending approvals

### Entry Point Pattern

Controllers are `@Controller` classes implementing generated API interfaces (following the existing `ProgramsApiController` pattern). Each endpoint:
1. Extracts orgId from `ShardContext` (set by `LoggerInterceptor` from `X-CAP-ORG-ID` header)
2. Validates request DTO via Bean Validation (`@Valid`)
3. Delegates to service layer for business validation + operation
4. Returns structured response or structured error (per G-06.3)

### Request/Response Style

- Synchronous REST (no async / queued operations needed for config CRUD)
- All write operations accept an idempotency key header (`X-Idempotency-Key`) per G-06.1
- Paginated list endpoints using offset/limit (following existing `ProgramsApiController` pattern) per G-04.2
- All timestamps in ISO-8601 UTC (per G-01.6)

### Error Response Shape

```json
{
  "status": {
    "success": false,
    "code": 422,
    "message": "Validation failed"
  },
  "errors": [
    {
      "field": "eligibilityThreshold",
      "code": "REQUIRED",
      "message": "Eligibility threshold is required"
    },
    {
      "field": "downgradeTo",
      "code": "INVALID_REFERENCE",
      "message": "Downgrade target tier 'abc-123' does not exist in this program"
    }
  ]
}
```

This follows the existing `InlineResponse400` pattern with `InlineResponse400Status` plus the field-level error array from BA requirements.

---

## Data and Persistence

### MongoDB Document: TierConfig

**Collection**: `tier_configs` in `emf` database.

```
TierConfig {
  _id: ObjectId                          // MongoDB auto-generated
  tierId: String (UUID)                  // Immutable business ID, persists across versions
  orgId: Long                            // Tenant isolation (per G-07)
  programId: Long                        // Program this tier belongs to
  
  // Versioning (UnifiedPromotion pattern)
  parentId: String                       // ObjectId of active parent (null for new tiers)
  version: Integer                       // Starts at 1, incremented on edit
  status: String                         // DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, STOPPED, SNAPSHOT
  comments: String                       // Review comment (max 150 chars)
  
  // Core tier fields
  name: String                           // Required, unique within program (non-SNAPSHOT)
  description: String
  color: String                          // Hex color code
  serialNumber: Integer                  // Tier rank/position in hierarchy
  
  // Eligibility
  eligibility: {
    kpiType: String                      // CURRENT_POINTS, LIFETIME_POINTS, LIFETIME_PURCHASES, TRACKER_VALUE
    threshold: BigDecimal                // Primary threshold (positive number)
    secondaryCriteria: [                 // Optional additional criteria
      { kpiType: String, threshold: BigDecimal }
    ]
  }
  
  // Validity
  validity: {
    type: String                         // FIXED_DURATION, REGISTRATION_DATE, FIXED_DATE
    periodInDays: Integer                // Duration in days (for FIXED_DURATION)
    fixedDate: Instant                   // For FIXED_DATE type
  }
  
  // Renewal
  renewal: {
    conditions: {
      retentionAmount: BigDecimal
      retentionPoints: BigDecimal
      retentionTracker: BigDecimal
      retentionVisits: Integer
    }
    schedule: String                     // e.g., "ANNUAL", "SEMI_ANNUAL"
    durationInDays: Integer
  }
  
  // Downgrade
  downgrade: {
    targetTierId: String                 // tierId of downgrade target, or "NONE" for base
    schedule: String                     // Downgrade evaluation schedule
    gracePeriodInDays: Integer
    validateOnReturnTransaction: Boolean // The toggle from BRD
  }
  
  // Upgrade
  upgrade: {
    mode: String                         // EAGER, DYNAMIC, LAZY (maps to SlabUpgradeMode)
    bonusPoints: BigDecimal              // Numeric bonus on upgrade
  }
  
  // Nudge / Communication (modeled as flexible structure pending product clarification)
  nudge: {
    enabled: Boolean
    reminderBeforeDays: [Integer]        // e.g., [30, 14, 7]
    templateReferences: {                // References to external communication templates
      sms: String
      email: String
      push: String
    }
  }
  
  // Linked benefits (stored as references with per-tier parameter overrides)
  linkedBenefits: [
    {
      benefitId: String                  // References BenefitConfig.benefitId
      parameters: Map<String, Object>    // Per-tier parameter overrides (e.g., {"multiplier": 3.0})
    }
  ]
  
  // Timestamps (per G-01.1: all UTC)
  createdOn: Instant
  createdBy: String
  lastModifiedOn: Instant
  lastModifiedBy: String
}
```

**Indexes:**
- `{ orgId: 1, programId: 1, tierId: 1, status: 1 }` — Primary query pattern (find tier by business ID with status filter)
- `{ orgId: 1, programId: 1, status: 1, serialNumber: 1 }` — List tiers for program ordered by rank
- `{ orgId: 1, tierId: 1, status: 1 }` — Lookup by tierId across programs (for validation)
- `{ orgId: 1, programId: 1, name: 1, status: 1 }` — Uniqueness validation (exclude SNAPSHOT)

### MongoDB Document: BenefitConfig

**Collection**: `benefit_configs` in `emf` database.

```
BenefitConfig {
  _id: ObjectId
  benefitId: String (UUID)               // Immutable business ID
  orgId: Long
  programId: Long
  
  // Versioning
  parentId: String
  version: Integer
  status: String
  comments: String
  
  // Core benefit fields
  name: String                           // Required, unique within program (non-SNAPSHOT)
  type: String                           // POINTS_MULTIPLIER, FLAT_POINTS_AWARD, COUPON_ISSUANCE, BADGE_AWARD, FREE_SHIPPING, CUSTOM
  category: String                       // EARNING, REDEMPTION, COUPON, BADGE, COMMUNICATION, CUSTOM
  triggerEvent: String                   // TIER_UPGRADE, TIER_RENEWAL, TRANSACTION, BIRTHDAY, MANUAL
  description: String
  
  // Type-specific parameters (flexible structure per benefit type)
  parameters: Map<String, Object>        // e.g., {"multiplier": 2.0} or {"points": 500}
  
  // Linked tiers
  linkedTiers: [
    {
      tierId: String                     // References TierConfig.tierId
      parameters: Map<String, Object>    // Per-tier parameter overrides
    }
  ]
  
  // Timestamps
  createdOn: Instant
  createdBy: String
  lastModifiedOn: Instant
  lastModifiedBy: String
}
```

**Indexes:**
- `{ orgId: 1, programId: 1, benefitId: 1, status: 1 }` — Primary query pattern
- `{ orgId: 1, programId: 1, status: 1 }` — List benefits for program
- `{ orgId: 1, programId: 1, name: 1, status: 1 }` — Uniqueness validation
- `{ orgId: 1, programId: 1, type: 1, status: 1 }` — Filter by type
- `{ orgId: 1, "linkedTiers.tierId": 1 }` — Find benefits linked to a specific tier

### Read/Write Boundaries

- **Write path**: New REST APIs -> Service -> MongoDB DAO -> MongoDB (emf database)
- **No writes to MySQL**: New APIs do not touch `program_slabs`, `strategies`, or `customer_enrollment`. Legacy MySQL remains the source of truth for EMF evaluation until a future sync iteration.
- **Read path (list/get)**: REST APIs -> Service -> MongoDB DAO. For `includeDraftDetails`, service queries both ACTIVE and DRAFT documents and merges.
- **Cross-entity reads**: Tier creation/update validates linked benefit IDs by querying `benefit_configs`. Benefit creation/update validates linked tier IDs by querying `tier_configs`.

### How New MongoDB Configs Coexist with Legacy MySQL

The two data stores operate independently:
1. **MySQL strategy tables**: Continue to be the source of truth for EMF evaluation engine (`SlabUpgradeService`, `SlabDowngradeService`). No changes.
2. **MongoDB tier/benefit configs**: New config management layer. Initially disconnected from EMF evaluation.
3. **Future sync**: A subsequent iteration will build a sync mechanism (likely event-driven: on approval of a TierConfig change, publish a Kafka event that a sync service consumes to update MySQL strategy tables). This is explicitly out of scope per BA.
4. **No dual writes**: Per BA constraint. The new API writes only to MongoDB. No MySQL writes.

---

## Maker-Checker Lifecycle

### Status State Machine

```
                  +---------+
          create  |  DRAFT  |<--------+
          ------->|         |         |
                  +----+----+         | reject
                       |              |
            submit     |              |
                       v              |
                 +-----+-------+      |
                 |  PENDING    |------+
                 |  APPROVAL   |
                 +-----+-------+
                       |
              approve  |
                       v
                  +----+----+        +----------+
                  | ACTIVE  |------->| STOPPED  |
                  |         |        | (terminal)|
                  +----+----+        +----------+
                       |                   ^
                 pause |                   |
                       v                   |
                  +----+----+              |
                  | PAUSED  |--------------+
                  |         |----+
                  +---------+    | resume -> ACTIVE
                       ^---------+
```

On edit approval (parentId is not null):
- Active parent -> SNAPSHOT (archived)
- Draft child -> inherits parent's status (ACTIVE or PAUSED)

SNAPSHOT is terminal. STOPPED is terminal.

### Versioning Approach

Following the UnifiedPromotion pattern exactly:

1. **New entity creation**: `tierId = UUID.randomUUID()`, `version = 1`, `parentId = null`, `status = DRAFT` (when maker-checker on).
2. **Edit of DRAFT**: Update in-place. No version change.
3. **Edit of ACTIVE**: Create new document with `parentId = active._id`, `version = active.version + 1`, `status = DRAFT`, same `tierId`.
4. **Edit when DRAFT already exists for tierId**: Update existing draft in-place.
5. **Approval of new entity** (parentId null): `PENDING_APPROVAL -> ACTIVE`.
6. **Approval of edit** (parentId not null): Active parent -> `SNAPSHOT`, draft -> `ACTIVE` (or `PAUSED` if parent was paused).
7. **Rejection**: `PENDING_APPROVAL -> DRAFT`. Draft retains parentId and version for resubmission.

### Concurrency Control

- **Distributed lock**: `@DistributedLock(key = "'lock_tier_status_{orgId}_{tierId}'", ttl = 300000, acquireTime = 5000)` on status change methods. Requires Redis (same infrastructure used by `@Lockable` in intouch-api-v3).
- **Optimistic concurrency**: Not needed at MongoDB document level because the distributed lock serializes status changes. However, if Redis is unavailable, we fall back to MongoDB's atomic `findAndModify` with a `version` field check as a safety net.
- Per G-05.2 and G-10: the lock prevents race conditions; the version field provides a second line of defense.

---

## Validation Strategy

### Layer 1: Bean Validation (Request DTO)

Applied via `@Valid` on controller method parameters. Covers:
- `@NotNull`, `@NotBlank` on required fields (name, programId, eligibility.kpiType, etc.)
- `@Size` constraints (name length, comment max 150 chars)
- `@Pattern` for format validation (color hex code, enum values)
- Handled by existing `GlobalExceptionHandler` -> `MethodArgumentNotValidException` -> 400 response.

### Layer 2: Business Validation (Validator Factory)

Applied in the service layer before persistence. Uses the existing `ValidatorFactory` pattern.

**TierValidatorFactory** returns validators for:
- `CREATE_TIER`: ProgramExistsValidator, TierNameUniquenessValidator, EligibilityKpiTypeValidator, EligibilityThresholdValidator, ValidityTypeValidator, DowngradeTargetValidator, UpgradeModeValidator, SerialNumberValidator, LinkedBenefitValidator
- `UPDATE_TIER`: Same chain plus StatusEditableValidator (rejects PENDING_APPROVAL, STOPPED, SNAPSHOT)
- `STATUS_CHANGE`: StatusTransitionValidator
- `REVIEW`: StatusIsAwaitingApproval + ReviewCommentValidator (mandatory on reject)

**BenefitValidatorFactory** returns validators for:
- `CREATE_BENEFIT`: ProgramExistsValidator, BenefitNameUniquenessValidator, BenefitTypeValidator, BenefitTypeParameterValidator, TriggerEventValidator, LinkedTierValidator
- `UPDATE_BENEFIT`: Same plus StatusEditableValidator
- `STATUS_CHANGE`: StatusTransitionValidator
- `REVIEW`: Same as tier

Each validator returns a `ValidationResult` with field-level errors. The service collects all errors and returns HTTP 422 with the full error list (not fail-fast on first error).

---

## Module/Package Structure within emf-parent

All new code lives in `pointsengine-emf` module, extending the existing REST endpoint structure:

```
pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/
├── RESTEndpoint/
│   ├── controller/
│   │   └── impl/
│   │       ├── TierConfigController.java          // NEW
│   │       └── BenefitConfigController.java       // NEW
│   ├── Service/
│   │   └── impl/
│   │       ├── TierConfigService.java             // NEW
│   │       └── BenefitConfigService.java          // NEW
│   ├── models/
│   │   ├── tier/                                  // NEW package
│   │   │   ├── TierConfigRequest.java
│   │   │   ├── TierConfigResponse.java
│   │   │   ├── TierEligibilityConfig.java
│   │   │   ├── TierValidityConfig.java
│   │   │   ├── TierRenewalConfig.java
│   │   │   ├── TierDowngradeConfig.java
│   │   │   ├── TierUpgradeConfig.java
│   │   │   ├── TierNudgeConfig.java
│   │   │   └── TierLinkedBenefit.java
│   │   ├── benefit/                               // NEW package
│   │   │   ├── BenefitConfigRequest.java
│   │   │   ├── BenefitConfigResponse.java
│   │   │   └── BenefitLinkedTier.java
│   │   └── config/                                // NEW package
│   │       ├── StatusChangeRequest.java
│   │       ├── ReviewRequest.java
│   │       └── ConfigValidationErrorResponse.java
│   ├── validators/
│   │   ├── factory/
│   │   │   ├── TierValidatorFactory.java          // NEW
│   │   │   └── BenefitValidatorFactory.java       // NEW
│   │   └── impl/
│   │       ├── tier/                              // NEW package
│   │       │   ├── TierNameUniquenessValidator.java
│   │       │   ├── EligibilityThresholdValidator.java
│   │       │   ├── DowngradeTargetValidator.java
│   │       │   ├── SerialNumberValidator.java
│   │       │   └── LinkedBenefitValidator.java
│   │       └── benefit/                           // NEW package
│   │           ├── BenefitNameUniquenessValidator.java
│   │           ├── BenefitTypeParameterValidator.java
│   │           └── LinkedTierValidator.java
│   └── Exceptions/
│       ├── handler/
│       │   └── GlobalExceptionHandler.java        // EXTEND
│       └── ConfigConflictException.java           // NEW (for 409)

emf/src/main/java/com/capillary/shopbook/springdata/mongodb/
├── model/
│   └── config/                                    // NEW package
│       ├── ConfigBaseDocument.java                // NEW - extends BaseMongoEntity
│       ├── TierConfig.java                        // NEW
│       └── BenefitConfig.java                     // NEW
├── dao/
│   ├── TierConfigDao.java                         // NEW interface
│   ├── BenefitConfigDao.java                      // NEW interface
│   └── impl/
│       ├── TierConfigDaoImpl.java                 // NEW
│       └── BenefitConfigDaoImpl.java              // NEW
└── enums/
    ├── ConfigStatus.java                          // NEW
    └── ConfigAction.java                          // NEW
```

### Rationale for Package Placement

- **Controllers, services, models, validators** go in `pointsengine-emf` under the existing `RESTEndpoint` structure — this is where all existing REST infrastructure lives.
- **MongoDB documents and DAOs** go in `emf` module under `springdata.mongodb` — this is where all existing MongoDB DAOs live (`OrgConfigDaoImpl`, `UnifiedPromotionDaoImpl`, etc.).
- New packages (`tier/`, `benefit/`, `config/`) keep the new code isolated without polluting existing namespaces.
- Per G-12.2: follows the project's existing patterns, not theoretical best practices.

---

## Multi-Tenancy Enforcement Pattern

Per G-07 (CRITICAL):

1. **Request boundary**: `LoggerInterceptor` extracts `X-CAP-ORG-ID` header -> `ShardContext.set(orgId)` (ThreadLocal). This already works for all existing controllers.
2. **DAO layer**: `BaseMongoDaoImpl.getTemplate(orgId, ...)` uses `MongoDataSourceManager.getDataSource(orgId)` to route to the correct MongoDB shard/connection. The orgId is passed explicitly to every DAO method.
3. **Document level**: Every `TierConfig` and `BenefitConfig` document has `orgId` as a first-class field. All queries include `orgId` in the filter.
4. **Service layer**: `TierConfigService` and `BenefitConfigService` extract orgId from `ShardContext.get()` and pass it to every DAO call. Never allow orgId to be taken from the request body.
5. **Cross-entity validation**: When validating linked tier/benefit IDs, the query always includes the current orgId — preventing cross-tenant reference injection.

This resolves the open question from BA: "How is orgId threaded through and validated in the new REST APIs?"

**Answer**: Via the existing `X-CAP-ORG-ID` header -> `LoggerInterceptor` -> `ShardContext` pattern. OrgId is extracted in the service layer from `ShardContext`, never from request body. All MongoDB queries are org-scoped both by shard routing (`MongoDataSourceManager`) and by explicit orgId filter in queries.

---

## ADRs (Architecture Decision Records)

### ADR-1: MongoDB Document-per-Version for Maker-Checker

**Decision**: Use the UnifiedPromotion document-per-version pattern (parentId + version + status) for both TierConfig and BenefitConfig.

**Alternatives considered**:
- Single document with embedded draft subdocument: Simpler queries but no codebase precedent. Version history is harder. Rejected.
- Event sourcing: Complete history but enormous complexity with no team experience. Rejected.

**Rationale**: Consistency with the only existing maker-checker implementation in the organization. The pattern is proven in production. The query complexity (filtering by status, parent/child lookups) is well-understood from the UnifiedPromotion implementation.

**Guardrail**: Per G-12.2 — follow the project's existing patterns.

### ADR-2: Two New MongoDB Collections (Not Embedding in Existing Tables)

**Decision**: Create `tier_configs` and `benefit_configs` collections in the `emf` MongoDB database. Do not write to MySQL `program_slabs` or `strategies` tables.

**Alternatives considered**:
- Write to existing MySQL tables and add approval columns: Would require schema migration on a critical production table. Breaks the "no dual writes" constraint from BA. Rejected.
- Use the existing `unified_promotions` collection with a type discriminator: Would overload a collection owned by intouch-api-v3. Different domain, different query patterns. Rejected.

**Rationale**: Clean separation. New collections are owned by emf-parent. No schema migration risk. MongoDB is already provisioned and used in emf-parent.

**Guardrail**: Per G-05.4 — backward-compatible migrations (we avoid the MySQL migration entirely). Per BA constraint — no dual writes.

### ADR-3: Distributed Lock for Status Changes

**Decision**: Implement a `@DistributedLock` annotation backed by Redis, modeled on intouch-api-v3's `@Lockable`. Lock key: `lock_{entity}_{orgId}_{entityId}`, TTL: 300 seconds, acquire timeout: 5 seconds.

**Alternatives considered**:
- MongoDB findAndModify with version check only: Works for single-document updates but does not prevent concurrent approval + edit race conditions across multiple documents (parent + child). Insufficient.
- Database-level pessimistic locking: MongoDB does not support traditional row-level locks across documents.

**Rationale**: The `@Lockable` pattern is proven in the same organization. Status changes involve multi-document operations (e.g., ACTIVE -> SNAPSHOT + DRAFT -> ACTIVE) that must be atomic at the business level. Distributed lock is the established solution.

**Guardrail**: Per G-10 — concurrency and thread safety. Per G-05.1 — multi-step mutations need transactional protection.

**Dependency**: Requires Redis. Must confirm Redis is available in the emf-parent deployment environment.

### ADR-4: Validation Factory Pattern Over Pure Bean Validation

**Decision**: Use Bean Validation for DTO field presence/format (layer 1) plus a `ValidatorFactory` returning ordered validator chains for business rules (layer 2).

**Alternatives considered**:
- Pure Bean Validation with custom constraint annotations: Works for simple cross-field validation but becomes unwieldy for cross-document validation (e.g., "downgrade target must reference existing tier").
- Pure programmatic validation in service methods: No pattern consistency. Hard to test in isolation.

**Rationale**: The `ValidatorFactory` pattern is already used in `pointsengine-emf` for promotion validation. Business validators (name uniqueness, reference integrity) require database queries that don't fit Bean Validation's annotation model. Keeping both layers provides best-of-both-worlds.

**Guardrail**: Per G-12.2 — follow the project's existing patterns. Per G-03.2 — validate and sanitize all input at the service boundary.

### ADR-5: API Uses "tier" Terminology, Internal Code Uses "slab" Only at Legacy Interfaces

**Decision**: External API paths, DTOs, and new MongoDB documents use "tier" terminology. Internal code uses "tier" for the new domain. "Slab" is only used when interfacing with existing EMF components (`ProgramSlab`, `SlabUpgradeMode`, etc.).

**Rationale**: The BA explicitly decided "API uses 'tier' externally." The new MongoDB documents are independent of the legacy `program_slabs` table. Using "tier" consistently in new code avoids confusion. The bridge to "slab" happens only at the (future) sync layer.

---

## Business Rules and Validation — Invariants

### Tier Invariants

| Rule | Violation Response | Where Validated |
|------|-------------------|-----------------|
| Tier name unique within program (excluding SNAPSHOT status) | 422: `DUPLICATE_NAME` | TierNameUniquenessValidator |
| Eligibility threshold > 0 | 422: `INVALID_THRESHOLD` | EligibilityThresholdValidator |
| KPI type must be CURRENT_POINTS, LIFETIME_POINTS, LIFETIME_PURCHASES, or TRACKER_VALUE | 422: `INVALID_KPI_TYPE` | Bean Validation @Pattern |
| Validity type must be FIXED_DURATION, REGISTRATION_DATE, or FIXED_DATE | 422: `INVALID_VALIDITY_TYPE` | Bean Validation @Pattern |
| Upgrade mode must be EAGER, DYNAMIC, or LAZY | 422: `INVALID_UPGRADE_MODE` | Bean Validation @Pattern |
| Downgrade target must reference existing tier in same program, or "NONE" | 422: `INVALID_REFERENCE` | DowngradeTargetValidator |
| Linked benefit IDs must reference active/draft benefits in same program | 422: `INVALID_REFERENCE` | LinkedBenefitValidator |
| serialNumber must not create gaps or conflicts in program hierarchy | 422: `SERIAL_NUMBER_CONFLICT` | SerialNumberValidator |
| Cannot edit PENDING_APPROVAL, STOPPED, or SNAPSHOT tiers | 409: `CONFLICT` | StatusEditableValidator |
| Status transitions must follow state machine | 409: `INVALID_TRANSITION` | ConfigStatusTransitionValidator |
| Rejection comment is mandatory | 422: `COMMENT_REQUIRED` | ReviewCommentValidator |

### Benefit Invariants

| Rule | Violation Response | Where Validated |
|------|-------------------|-----------------|
| Benefit name unique within program (excluding SNAPSHOT) | 422: `DUPLICATE_NAME` | BenefitNameUniquenessValidator |
| Type must be valid enum value | 422: `INVALID_TYPE` | Bean Validation |
| Type-specific parameters must be present and valid (e.g., POINTS_MULTIPLIER needs `multiplier` > 0) | 422: `INVALID_PARAMETERS` | BenefitTypeParameterValidator |
| Linked tier IDs must reference existing tiers in same program | 422: `INVALID_REFERENCE` | LinkedTierValidator |
| Cannot edit PENDING_APPROVAL, STOPPED, or SNAPSHOT benefits | 409: `CONFLICT` | StatusEditableValidator |
| Benefit scoped to one program | 422: `CROSS_PROGRAM_REFERENCE` | Bean Validation (programId is required, validated at creation) |

---

## Open Questions / Decisions

1. **Redis availability in emf-parent**: Is Redis available in the emf-parent deployment environment for distributed locking? If not, we need an alternative (MongoDB-based locking or advisory locks). — owner: Infrastructure
2. **What happens to members in a STOPPED tier?**: Carried forward from BA. The new API only manages config documents; member-level impact is a separate concern for the EMF evaluation integration iteration. For now, STOPPED means the tier config is frozen — no further edits allowed. Member behavior is unchanged until sync with EMF is built.
3. **Upgrade bonus — numeric or benefit reference?**: Modeled as `bonusPoints: BigDecimal` per BA assumption. If product decides it should reference a BenefitConfig entity, the schema change is backward-compatible (add a `bonusBenefitId` field alongside).
4. **Nudge/communication config exact fields**: Modeled as a flexible structure (`enabled`, `reminderBeforeDays[]`, `templateReferences`). Needs product team confirmation before Analyst locks the schema.
5. **Multiple pending drafts for different tiers**: Per the UnifiedPromotion pattern, each tier can independently have one pending draft. There is no program-level lock — multiple tiers can be in PENDING_APPROVAL simultaneously. This mirrors how multiple promotions can be pending simultaneously.
6. **Maker-checker bypass path**: When config flag is `false`, create/update operations set status directly to ACTIVE. The service checks the flag and skips the draft step. Flag is a hardcoded boolean property initially.
7. **Idempotency key implementation**: Need to decide on storage (Redis with TTL? MongoDB collection?). The key prevents duplicate creates on retry. This is a detail for the Designer/Developer phases.

---

## Done Criteria

- [ ] `TierConfig` and `BenefitConfig` MongoDB documents defined with all BRD fields
- [ ] DAO layer extending `BaseMongoDaoImpl` with proper org-scoped queries
- [ ] REST controllers for all CRUD + status + review endpoints
- [ ] Two-layer validation (Bean Validation + validator factory chain)
- [ ] Status state machine with `ConfigStatusTransitionValidator`
- [ ] Distributed lock on status change operations
- [ ] Maker-checker lifecycle (DRAFT -> PENDING_APPROVAL -> ACTIVE with parentId versioning)
- [ ] Multi-tenancy enforcement via `X-CAP-ORG-ID` + `ShardContext`
- [ ] Structured error responses (field-level, 422 for validation, 409 for conflicts)
- [ ] Paginated list endpoints
- [ ] All timestamps in UTC ISO-8601
- [ ] No writes to legacy MySQL tables
- [ ] API versioned at `/api/v1`
