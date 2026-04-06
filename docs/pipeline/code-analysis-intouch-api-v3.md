# Code Analysis: intouch-api-v3 — Tier CRUD API Reference

**Date**: 2026-04-06
**Purpose**: Research findings to guide building Tier CRUD APIs following the UnifiedPromotion pattern.
**Scope**: MongoDB-first architecture, DRAFT/PENDING → MongoDB, APPROVE syncs to MySQL via Thrift.

---

## Key Architectural Insights

1. **Two MongoDB namespaces**: The app has a "primary" Mongo (multi-tenant, org-sharded, for profiles/target-loyalty) and an "EMF Mongo" (org-sharded EMF database). `UnifiedPromotion` lives in EMF Mongo (`db=emf`, collection=`unified_promotions`). **TierDocument must also use EMF Mongo** — same `emfMongoTemplate`.

2. **Multi-tenant Mongo via tenant resolvers**: MongoDB is not a single connection. `EmfMongoTenantResolver` routes each request to the correct shard based on `OrgContext.getOrgId()` (a `ThreadLocal<Long>`). The org is set from the authenticated `IntouchUser` in the controller.

3. **Two-ID pattern**: `UnifiedPromotion` has two IDs:
   - `objectId` (MongoDB `_id`) — changes when a new versioned document is created.
   - `unifiedPromotionId` — immutable UUID generated at create time, stable across all versions/status changes. This is what the API client uses.
   - **Tier must follow the same pattern**: `_id` (MongoDB) + `tierId` (immutable, client-facing).

4. **Status lifecycle (PromotionStatus pattern)**: `DRAFT → PENDING_APPROVAL → ACTIVE/STOPPED → SNAPSHOT`. ACTIVE edits create a new DRAFT with `parentId` pointing to the ACTIVE doc. On APPROVE, ACTIVE → SNAPSHOT, DRAFT → ACTIVE.

5. **Thrift is called only on APPROVE**: For CREATE/UPDATE, data is written to MongoDB only. `PointsEngineRulesThriftService.createOrUpdatePromotionV3()` is called in the PUBLISH orchestration flow (triggered by the `/review` endpoint with `APPROVE`). Not during DRAFT save.

6. **No `APIMigrationInterceptor` concern for new paths**: The interceptor only redirects if a path matches a rule in `migrationRules` (loaded from MongoDB `MigrationRules` collection at startup). A new `/v3/tiers` path will not match any existing rule — it will pass through cleanly with no redirect. The interceptor runs on `/**` but exits safely if no matching rule found.

7. **Auth pattern**: `AbstractBaseAuthenticationToken` is injected as a method parameter (resolved by Spring Security context binding). `token.getIntouchUser().getOrgId()` gives the authenticated org ID. This is the single auth mechanism used by ALL controllers — no change needed for TierController.

8. **Response shape is standardized**: `ResponseWrapper<T>` with `data`, `errors` (`List<ApiError>`), and `warnings` (`List<ApiWarning>`). All controllers return this. All error handling flows through `TargetGroupErrorAdvice` (`@ControllerAdvice`).

9. **Validation is layered**: Bean Validation (`@Valid`, JSR-380) on DTOs + custom `@Service` validators called explicitly in the facade. Error messages are resolved from `.properties` files via `MessageResolverService`.

---

## 1. UnifiedPromotion Pattern Deep-Dive

### 1.1 UnifiedPromotionController

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/resources/UnifiedPromotionController.java`

**Base mapping**: `@RequestMapping("/v3/unifiedPromotions")`

**All endpoints**:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/` | Create promotion — `@Valid @RequestBody UnifiedPromotion` |
| `GET` | `/{promotionId}` | Get by `unifiedPromotionId`, query param `?status=ACTIVE` (default) |
| `PUT` | `/{promotionId}` | Update by `unifiedPromotionId` |
| `GET` | `/` | List with `@ModelAttribute UnifiedPromotionListRequest` + `@RequestParam Map<String, String> filters` |
| `POST` | `/{unifiedPromotionId}/review` | Approve/Reject — `@Valid @RequestBody PromotionReviewRequest` |
| `POST` | `/{promotionId}/bulk-claim-approve` | Bulk approve communication meta IDs |
| `POST` | `/enrol` | Enrol customer into promotion |
| `GET` | `/{promotionId}/stats` | Get promotion statistics |

**Key observations**:
- Auth token is `AbstractBaseAuthenticationToken token` — a method parameter injected by Spring Security
- `user.getOrgId()` is passed into every facade call — the controller does NOT touch `OrgContext` directly
- `HttpServletRequest request` is passed to facade methods (for audit/migration logging)
- Responses: `ResponseEntity<ResponseWrapper<T>>` uniformly
- The controller does not contain business logic — all delegated to `UnifiedPromotionFacade`

### 1.2 UnifiedPromotionFacade

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotionFacade.java`

**Package**: `com.capillary.intouchapiv3.unified.promotion`

**Injected beans**:
- `UnifiedPromotionRepository` — Spring Data MongoDB
- `EntityOrchestrator` — orchestrates Thrift/external entity creation (`@Autowired(required = false)`)
- `UnifiedPromotionValidatorService` — custom business validation
- `StatusTransitionValidator`
- `PointsEngineRulesThriftService` — Thrift client to EMF
- `PromotionDataReconstructor`
- `IndividualMilestoneProcessingService`

**CREATE flow** (`createUnifiedPromotion`):
1. Generate `unifiedPromotionId` (UUID, backend-generated, READ_ONLY in JSON)
2. Validate `promoIdentifer` uniqueness against existing DRAFT/ACTIVE/PAUSED/STOPPED/PENDING_APPROVAL
3. Set `orgId` from passed `orgId` parameter (not from document)
4. Default status to `DRAFT` if not provided
5. Generate activity IDs (UUID per activity)
6. Validate filter configs
7. Call `EntityOrchestrator.orchestrate(FlowType.CREATE)` — CREATE flow = validation only (journey creation if IMPORT/BROADCAST)
8. `promotionRepository.save(promotion)` — saves to MongoDB

**UPDATE flow** (`updateUnifiedPromotion`):
- If existing is DRAFT → update the DRAFT in place
- If existing is ACTIVE → create new versioned document with `parentId = existing.objectId`, `version = existing.version + 1`, status = DRAFT
- If existing is PAUSED → check for existing DRAFT; if found, update DRAFT; else create new versioned DRAFT

**REVIEW/APPROVE flow** (`reviewUnifiedPromotion`):
1. Find the PENDING_APPROVAL document by `unifiedPromotionId` + `orgId`
2. If APPROVE → `handlePromotionApproval()`:
   - If `parentId != null` (editing scenario): call `editOrchestrator.orchestrateEdits()` → calls Thrift to update existing EMF entities → ACTIVE → SNAPSHOT, DRAFT → ACTIVE
   - If no parentId (new scenario): call `EntityOrchestrator.orchestrate(FlowType.PUBLISH)` → calls Thrift `createOrUpdatePromotionV3()` + `publishPeConfig()` → status set to ACTIVE
3. If REJECT → status set back to DRAFT

**PENDING_APPROVAL transition** is not handled in `UnifiedPromotionFacade`. It is handled via `RequestManagementController` → `RequestManagementFacade` → `UnifiedPromotionFacade.changePromotionStatus()`.

### 1.3 UnifiedPromotion (MongoDB Document)

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotion.java`

**MongoDB annotations**: `@Document(collection = "unified_promotions")`

**Fields summary**:

| Field | Type | Notes |
|-------|------|-------|
| `objectId` | `String` | `@Id` — MongoDB `_id`, exposed as JSON `"id"` |
| `unifiedPromotionId` | `String` | `@JsonProperty(READ_ONLY)` — immutable, client-facing ID |
| `metadata` | `Metadata` | `@NotNull @Valid` — all core fields (name, orgId, status, dates, etc.) |
| `customerEnrolment` | `CustomerEnrolment` | `@Valid` |
| `activities` | `List<BaseActivity>` | `@Valid`, default `ArrayList` |
| `comments` | `String` | `@Size(max=150)` — review comment |
| `parentId` | `String` | Points to ACTIVE doc's objectId when this is a DRAFT created from ACTIVE |
| `parentDetails` | `ParentDetails` | Enriched at read time — not stored for GET responses |
| `version` | `Integer` | Default 1, incremented on ACTIVE update |
| `limits` | `List<Limit>` | `@Valid` |
| `liabilityOwnerSplitInfo` | `List<LiabilityOwnerSplitInfo>` | |
| `workflowMetadata` | `WorkflowMetadata` | `@Valid` |
| `communicationApprovalStatus` | `BulkClaimApproveResponse` | Read-only — managed by system |
| `journeyMetadata` | `JourneyMetadata` | `@JsonIgnore` — internal use only |
| `broadcastMetadata` | `BroadcastMetadata` | `@Valid` |
| `promotionSchedule` | `PromotionSchedule` | `@Valid` |

**Metadata sub-document** (key fields for TierDocument reference):
- `orgId` (Long) — set by system from auth context
- `status` (PromotionStatus enum) — stored as string in MongoDB
- `name` (@NotBlank), `description`, `startDate`, `endDate`, `promotionType`
- `promoIdentifer` — unique business identifier
- `promotionId` (int) — Points Engine ID (set during APPROVE)
- `createdOn`, `lastModifiedOn`, `createdBy`, `lastModifiedBy`
- `draftDetails` — enriched at read time (not persisted to child document)

### 1.4 UnifiedPromotionRepository

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotionRepository.java`

Extends `MongoRepository<UnifiedPromotion, String>` + `UnifiedPromotionRepositoryCustom`.

**Key query methods**:

```java
// Find by MongoDB doc ID + orgId
@Query("{'objectId': ?0, 'metadata.orgId': ?1}")
Optional<UnifiedPromotion> findByObjectIdAndOrgId(String objectId, Long orgId);

// Find by immutable ID + orgId + status (used for GET)
@Query("{'unifiedPromotionId': ?0, 'metadata.orgId': ?1, 'metadata.status': ?2}")
List<UnifiedPromotion> findByUnifiedPromotionIdAndOrgIdAndStatus(String unifiedPromotionId, Long orgId, PromotionStatus status);

// Find for UPDATE — only DRAFT/ACTIVE/PAUSED allowed
@Query("{'unifiedPromotionId': ?0, 'metadata.orgId': ?1, 'metadata.status': { $in: ['DRAFT', 'ACTIVE', 'PAUSED'] } }")
List<UnifiedPromotion> findAllByUnifiedPromotionIdAndOrgIdWithAllowedStatuses(String unifiedPromotionId, Long orgId);

// Find DRAFT by parent ID (check if draft exists for an ACTIVE)
@Query("{'parentId': ?0, 'metadata.orgId': ?1, 'metadata.status': 'DRAFT'}")
UnifiedPromotion findDraftByParentId(String parentId, Long orgId);

// Uniqueness check (excludes SNAPSHOT)
@Query("{ 'metadata.orgId': ?0, 'metadata.promoIdentifer': ?1, 'metadata.status': { $in: ['DRAFT', 'ACTIVE', 'PAUSED', 'STOPPED', 'PENDING_APPROVAL'] } }")
Optional<UnifiedPromotion> findByOrgIdAndPromoIdentifierExcludingSnapshot(Long orgId, String promoIdentifer);
```

**Indexes created at startup** (in `UnifiedPromotionRepositoryImpl.@PostConstruct`):
- `idx_id_orgId` — `_id + metadata.orgId`
- `idx_unifiedPromotionId_orgId_status` — `unifiedPromotionId + metadata.orgId + metadata.status`
- `idx_orgId_status_lastModified` — `metadata.orgId + metadata.status + metadata.lastModifiedOn DESC`
- `idx_orgId_status_dates` — `metadata.orgId + metadata.status + startDate + endDate`
- `idx_parentId_orgId_status` — sparse, for parent-child relationships
- `idx_orgId_promotionName_active_pending` — partial index on ACTIVE/PENDING_APPROVAL

### 1.5 MongoDB vs MySQL: What Goes Where

| Storage | Data | When |
|---------|------|------|
| **MongoDB (EMF)** | Full promotion document (all fields, DRAFT state, versions, metadata) | CREATE, UPDATE, status transitions |
| **MySQL (via Thrift to EMF)** | Points Engine promotion entity (`PromotionAndRulesetInfo`), rulesets, limits, liability splits | APPROVE only (PUBLISH flow) |

The promotion document in MongoDB is the source of truth for the API layer. MySQL/EMF is the downstream system that gets notified via Thrift only when a promotion is approved and needs to become ACTIVE.

### 1.6 APPROVE triggers Thrift

**Thrift service**: `PointsEngineRuleService.Iface` (host: `emf-thrift-service`, port: `9199`)

**Key Thrift methods called on APPROVE**:
1. `createOrUpdatePromotionV3(PromotionAndRulesetInfo, programId, orgId, lastModifiedBy, lastModifiedOn, serverRequestId)` — creates/updates the promotion in Points Engine
2. `publishPeConfig(PublishPeConfigParams, serverRequestId)` — makes the promotion live
3. `createOrUpdateLimit(LimitConfigData, ...)` — for limits
4. `createLiabilityOwnerSplit(List<LiabilityOwnerSplitInfo>, ...)` — for liability splits

---

## 2. MongoDB Setup

### 2.1 Primary MongoDB Config

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/config/MongoConfig.java`

- `@Primary` bean: `mongoTemplate` (backed by `IntouchMongoTenantResolver`)
- Routes `ProfileDao` and `TargetAudienceStatusLogDao` to this template
- Used for org-level profile data

### 2.2 EMF MongoDB Config — TierRepository Must Use This

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/config/EmfMongoConfig.java`

```java
@EnableMongoRepositories(
    basePackages = "com.capillary.intouchapiv3",
    mongoTemplateRef = "emfMongoTemplate",
    includeFilters = @ComponentScan.Filter(
        type = FilterType.ASSIGNABLE_TYPE,
        classes = {UnifiedPromotionRepository.class}  // Add TierRepository here
    )
)
```

- `emfMongoTemplate` backed by `EmfMongoTenantResolver` (routes to EMF shards by `OrgContext.getOrgId()`)
- **Database name in EMF Mongo**: `emf` (hardcoded in `UnifiedPromotionRepositoryImpl`: `DATABASE_NAME = "emf"`)
- TierRepository must be added to the `includeFilters` list in `EmfMongoConfig`

### 2.3 Tenant Resolver Mechanism

`EmfMongoTenantResolver` uses `OrgContext.getOrgId()` (a `ThreadLocal<Long>`) to select the correct MongoDB shard. The `OrgContext` is set by the authentication flow during request processing. This means every MongoDB operation implicitly scopes to the current org's shard.

### 2.4 MongoDB Document Annotations

Standard Spring Data MongoDB pattern:
```java
@Document(collection = "collection_name")
public class MyDocument {
    @Id
    private String objectId;  // Exposed as "id" in JSON via @JsonProperty("id")
    // ...
}
```

The `@Id` field maps to MongoDB `_id`. If null on save, MongoDB auto-generates an ObjectId string.

---

## 3. Thrift Client Setup

### 3.1 How Thrift Clients Work

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/services/thrift/PointsEngineRulesThriftService.java`

Pattern:
```java
private PointsEngineRuleService.Iface getClient() throws Exception {
    return RPCService.rpcClient(getIfaceClass(), "emf-thrift-service", 9199, 60000);
}
```

- Uses `com.capillary.commons.thrift.external.RPCService.rpcClient()` — a pooled Thrift client factory
- Service name: `"emf-thrift-service"` — DNS/service discovery name
- Port: `9199`
- Timeout: `60000ms` (60s)
- No Spring `@Bean` — clients are created on demand via static factory

### 3.2 Available Thrift Services

| Service Class | Endpoint | Purpose |
|--------------|----------|---------|
| `PointsEngineRulesThriftService` | `emf-thrift-service:9199` | Programs, promotions, limits, publish |
| `EmfPromotionThriftService` | `emf-thrift-service:9199` | Issue/earn promotion events |
| `PointsEngineThriftService` | (similar pattern) | Points engine operations |
| `RuleEngineThriftService` | (similar pattern) | Rule engine |
| `AudienceManagerThriftService` | (similar pattern) | Audience management |
| `IntouchApiThriftService` | (similar pattern) | General Intouch API |
| `EmfDataManagerThriftService` | (similar pattern) | EMF data manager |

### 3.3 Thrift Methods for Tiers/Slabs

**C3 confidence** — based on what's visible in `PointsEngineRulesThriftService`. The actual slab/tier Thrift methods must be confirmed by examining `PointsEngineRuleService.Iface` IDL (not in this repo). The following are **known** to be available:

- `getAllPrograms(int orgId)` → `List<ProgramInfo>`
- `getProgram(int programId, int orgId, String serverRequestId)` → `ProgramInfo`
- `createOrUpdatePromotionV3(PromotionAndRulesetInfo, programId, orgId, lastModifiedBy, lastModifiedOn, serverRequestId)` → `PromotionAndRulesetInfo`
- `publishPeConfig(PublishPeConfigParams, serverRequestId)` → `BoolRes`
- `createOrUpdateLimit(LimitConfigData, orgId, lastModifiedBy, lastModifiedOn, serverRequestId)` → `LimitConfigData`
- `validateLimitEntity(LimitConfigData, orgId, serverRequestId)` → `BoolRes`
- `createLiabilityOwnerSplit(int orgId, List<LiabilityOwnerSplitInfo>, serverRequestId)` → `List<LiabilityOwnerSplitInfo>`

**QUESTION FOR USER**: What are the specific Thrift method names for creating/updating tiers (slabs) in EMF? The `PointsEngineRuleService.Iface` IDL must be checked in the `emf-parent` or Thrift repo. Methods could be named `createOrUpdateSlab`, `updateTierConfig`, or similar — this is C2 until confirmed.

---

## 4. Validation Patterns

### 4.1 Bean Validation

The document model uses Jakarta Validation (`jakarta.validation`):
```java
@NotNull(message = "Metadata is required")
@Valid
private Metadata metadata;

@NotBlank(message = "Name is required")
@Size(max = 255, message = "Promotion name cannot exceed 255 characters")
private String name;
```

Annotation messages can be either:
1. **Direct text** — returned directly to the client (e.g., `"Metadata is required"`)
2. **Error keys** — looked up via `MessageResolverService` (e.g., `"TARGET_LOYALTY.INVALID_APPROVAL_STATUS"`)

The `TargetGroupErrorAdvice` handles `MethodArgumentNotValidException` and tries `resolverService.getMessage(defaultMessage)` — if the result is empty (no properties entry), it falls back to the raw annotation message.

### 4.2 Custom Validator Services

`UnifiedPromotionValidatorService` is a `@Component` called explicitly in the facade:
- `validatePromoIdentifierUniqueness(orgId, promoIdentifer, excludeId)` — checks MongoDB for duplicates
- `validateLoyaltyConfigMetaDataChanges(...)` — validates loyalty config
- `validatePromotionMetadataChanges(...)` — validates metadata
- `validatePromotionUpdate(promotion, validationTarget, effectiveStatus)` — update rules
- `validateFixedFrequencyCycleDurationsForPromotion(promotion)`

### 4.3 Error Code Pattern

Error codes defined in properties files under `src/main/resources/i18n/errors/`:
- `target_loyalty.properties` — error codes 310001–31xxxx
- `common.properties`
- `messages.properties`

**Pattern**:
```properties
TARGET_LOYALTY.SOME_ERROR.code = 310050
TARGET_LOYALTY.SOME_ERROR.message = Human-readable error message
```

Error resolution:
- `MessageResolverService.getCode("TARGET_LOYALTY.SOME_ERROR")` → `310050L`
- `MessageResolverService.getMessage("TARGET_LOYALTY.SOME_ERROR")` → `"Human-readable error message"`

The prefix (`TARGET_LOYALTY`, `COMMON`, etc.) maps to a specific `.properties` file via `fileNameMap` in `MessageResolverService`.

**For Tier CRUD**: A new error namespace (e.g., `TIER`) or reuse of `TARGET_LOYALTY` is needed. Either:
- Add `"TIER"` to `fileNameMap` in `MessageResolverService` (requires code change)
- Use `TARGET_LOYALTY` namespace with new error codes (no code change required)

**QUESTION FOR USER**: Should Tier error codes use an existing namespace (`TARGET_LOYALTY`) or get a new namespace (`TIER`)? Adding a new namespace requires modifying `MessageResolverService.fileNameMap`.

---

## 5. Auth and Interceptors

### 5.1 Org Context Resolution

**Mechanism**: `AbstractBaseAuthenticationToken token` injected as a method parameter in the controller.

```java
IntouchUser user = token.getIntouchUser();
Long orgId = user.getOrgId();
```

`IntouchUser` contains: `orgId`, `entityId` (storeId/userId), `entityType`, `tillName`, `accessToken`.

Auth is validated by three providers (`BasicAndKeyAuthenticationProvider`, `KeyOnlyAuthenticationProvider`, `IntegrationsClientAuthenticationProvider`) — all set `OrgContext.setOrgId()` implicitly via the tenant resolver when MongoDB operations are executed.

**Headers used for auth**:
- `Authorization: Basic <base64(username:password)>` — with `X-CAP-API-AUTH-ORG-ID` and optionally `X-CAP-API-AUTH-KEY`
- Or API key only flow via `KeyOnlyAuthenticationFilter`

### 5.2 APIMigrationInterceptor

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/migration/APIMigrationInterceptor.java`

Registered for `/**` in `WebConfig`. Effect on new `/v3/tiers` endpoint:
- Runs `preHandle` for every request
- Only acts if `API_MIGRATION_ENABLED=TRUE` environment variable is set
- Looks up URI+method in `migrationRules` map (loaded from MongoDB `migration_rules` collection)
- `/v3/tiers` will NOT match any existing migration rule → interceptor runs but returns `true` immediately (no redirect, no mirroring)
- **Net effect**: Zero impact on TierController. The interceptor will log the request and exit normally.

### 5.3 Security Chain

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/config/HttpSecurityConfig.java`

```java
.requestMatchers("/**").authenticated()
```

All endpoints under `/**` require authentication. `/v3/tiers/**` will automatically be protected. No additional security configuration needed.

---

## 6. Package Structure

### 6.1 Where to Place TierController

**Pattern observed**: All controllers live in `com.capillary.intouchapiv3.resources`

```
src/main/java/com/capillary/intouchapiv3/resources/
├── UnifiedPromotionController.java       ← reference pattern
├── RequestManagementController.java
├── TargetGroupController.java
├── MilestoneController.java
└── TierController.java                   ← NEW — place here
```

### 6.2 Where to Place TierFacade

**Pattern observed**: Facade per domain feature lives alongside the document model in a feature package. BUT simpler facades live in `com.capillary.intouchapiv3.facades`.

**Option A** — alongside the domain model (like UnifiedPromotion):
```
com.capillary.intouchapiv3.tier/
├── Tier.java                     (MongoDB document)
├── TierFacade.java
├── TierRepository.java
├── TierRepositoryCustom.java
├── TierRepositoryImpl.java
└── enums/TierStatus.java
```

**Option B** — facades in shared package:
```
com.capillary.intouchapiv3.facades/
└── TierFacade.java
```

**Recommendation** (C5): Use Option A — feature package `com.capillary.intouchapiv3.tier` — consistent with how UnifiedPromotion is organized as a self-contained domain. The simpler facades in `facades/` (e.g., `RequestManagementFacade`) are routing/orchestration facades, not domain facades.

### 6.3 Where to Place DTOs

For UnifiedPromotion, DTOs live in `com.capillary.intouchapiv3.unified.promotion.dto`.

For Tier, use `com.capillary.intouchapiv3.tier.dto`.

### 6.4 Where to Place the MongoDB Document Model

The document model (`Tier.java`) belongs in the feature package: `com.capillary.intouchapiv3.tier.Tier`.

Sub-models live in `com.capillary.intouchapiv3.tier.model` (following `unified.promotion.model` pattern).

### 6.5 EmfMongoConfig Registration — Critical

`TierRepository` MUST be added to `EmfMongoConfig.includeFilters`:

```java
// EmfMongoConfig.java — ADD TierRepository to the filter
@EnableMongoRepositories(
    ...
    includeFilters = @ComponentScan.Filter(
        type = FilterType.ASSIGNABLE_TYPE,
        classes = {
            UnifiedPromotionRepository.class,
            TierRepository.class          // ADD THIS
        }
    )
)
```

Without this, `TierRepository` will pick up the primary `mongoTemplate` (wrong shard/DB).

---

## Summary: Building TierController — Exact Steps

1. **Create `com.capillary.intouchapiv3.tier` package**
2. **`Tier.java`**: `@Document(collection = "tiers")`, `@Id String objectId`, `String tierId` (UUID, READ_ONLY), `TierMetadata metadata` (orgId, name, status, etc.)
3. **`TierStatus.java` enum**: `DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED` (matches session-memory spec)
4. **`TierRepository.java`**: `extends MongoRepository<Tier, String>` + custom interface
5. **`TierRepositoryImpl.java`**: Custom queries + `@PostConstruct` for index creation using `emfMongoTemplate`
6. **Register in `EmfMongoConfig`**: Add `TierRepository.class` to `includeFilters`
7. **`TierFacade.java`**: Create/update/get/list/review logic following `UnifiedPromotionFacade` pattern
8. **`TierController.java`** in `resources/`: `@RequestMapping("/v3/tiers")`, inject `TierFacade`, use `AbstractBaseAuthenticationToken`
9. **Error codes**: Add to `target_loyalty.properties` (or new `tier.properties` if namespace is added)
10. **Thrift call on APPROVE**: Call appropriate slab/tier Thrift methods — requires confirmation of Thrift IDL

---

## Questions for User

1. **C2 — Thrift methods for tiers**: What are the specific Thrift method names in `PointsEngineRuleService.Iface` for creating/updating tier (slab) configuration? Need to inspect `emf-parent` Thrift IDL.

2. **C3 — Error code namespace**: Should Tier errors reuse `TARGET_LOYALTY` namespace (e.g., `TARGET_LOYALTY.TIER_NOT_FOUND`) or get a new namespace `TIER`? A new namespace requires modifying `MessageResolverService.fileNameMap`.

3. **C4 — Collection name in MongoDB**: Should the tier collection be named `"tiers"` or `"unified_tiers"` (to match the `"unified_promotions"` pattern)?

4. **C3 — TierStatus align with PromotionStatus**: The session-memory says `DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED`. But `PromotionStatus` also has `PAUSED`, `SNAPSHOT`, `PUBLISH_FAILED`. Should `TierStatus` be a strict subset? Can ACTIVE tiers be paused?

5. **C3 — Thrift for DRAFT vs ACTIVE tiers**: Does EMF/MySQL even have a concept of "tier draft"? Or does the draft lifecycle live entirely in MongoDB, with MySQL only seeing the final ACTIVE tier? (The promotion pattern implies MySQL only sees ACTIVE.)

---

## Assumptions Made (C5+)

- **C6**: `TierRepository` must use `emfMongoTemplate`, not `mongoTemplate`. Evidence: `UnifiedPromotionRepository` explicitly routes to EMF Mongo, and tiers are an EMF concept.
- **C6**: `APIMigrationInterceptor` will not affect `/v3/tiers` as long as no migration rule for that path exists. Evidence: interceptor only redirects on exact URI+method match from loaded rules.
- **C5**: The package structure for TierController should be `resources/TierController.java` and the domain under `com.capillary.intouchapiv3.tier/`. Evidence: all 6 existing controllers are in `resources/`, and the deep domain model for UnifiedPromotion lives in its own `unified.promotion` sub-package.
- **C5**: `AbstractBaseAuthenticationToken` injection as a method parameter will work for TierController without additional configuration. Evidence: all existing controllers use the same pattern with no per-controller security config.
