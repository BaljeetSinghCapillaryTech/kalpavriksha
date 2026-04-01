# 02 — Impact Analysis: Tier & Benefit CRUD + Maker-Checker APIs

> Phase: Analyst (02)
> Date: 2026-04-01
> Input: 00-ba.md, 01-architect.md, brdQnA.md, session-memory.md, GUARDRAILS.md
> Output feeds: 03-designer.md

---

## Change Summary

### What is being added
1. **Two new MongoDB collections** (`tier_configs`, `benefit_configs`) in the `emf` database with full BRD-level configuration fields, versioning (parentId/version), and status lifecycle.
2. **Two new REST controllers** (`TierConfigController`, `BenefitConfigController`) under `/api/v1/tiers` and `/api/v1/benefits` in the `pointsengine-emf` module.
3. **Two new service classes** (`TierConfigService`, `BenefitConfigService`) with CRUD, status transition, and maker-checker review logic.
4. **Two new DAO classes** (`TierConfigDaoImpl`, `BenefitConfigDaoImpl`) extending `BaseMongoDaoImpl` in the `emf` module.
5. **Shared config-lifecycle components**: `ConfigStatus` enum, `ConfigAction` enum, `ConfigStatusTransitionValidator`, `@DistributedLock` annotation + AOP aspect.
6. **Shared config-common components**: `ConfigBaseDocument` (abstract base), request/response DTOs, `ConfigConflictException`.
7. **Validation infrastructure**: `TierValidatorFactory`, `BenefitValidatorFactory`, and ~10 individual business validators.
8. **Extension to `GlobalExceptionHandler`** for new exception types (409 Conflict, 422 Validation).

### What is being changed
- `GlobalExceptionHandler` — extended with new exception handlers.
- No existing code is modified. All changes are additive.

### What is NOT being changed (explicitly out of scope)
- MySQL tables (`program_slabs`, `strategies`, `customer_enrollment`) — no writes.
- EMF evaluation pipeline (`EMFThriftServiceImpl`, `SlabUpgradeService`, `SlabDowngradeService`) — no modifications.
- Existing MongoDB collections (`org_configuration`, `unified_promotions`, `moonknight`) — untouched.
- intouch-api-v3 codebase — no changes.

---

## Impact Map

### Directly Affected Modules/Files

| Module | File/Package | Change Type | Evidence |
|--------|-------------|-------------|----------|
| `emf` | `springdata/mongodb/model/config/` | NEW package | New `ConfigBaseDocument`, `TierConfig`, `BenefitConfig` classes extending `BaseMongoEntity` |
| `emf` | `springdata/mongodb/dao/` | NEW interfaces + impls | `TierConfigDao`, `BenefitConfigDao` interfaces; `TierConfigDaoImpl`, `BenefitConfigDaoImpl` extending `BaseMongoDaoImpl` |
| `emf` | `springdata/mongodb/enums/` | NEW package | `ConfigStatus`, `ConfigAction` enums |
| `pointsengine-emf` | `RESTEndpoint/controller/impl/` | NEW controllers | `TierConfigController`, `BenefitConfigController` alongside existing `ProgramsApiController`, `OrgConfigController` |
| `pointsengine-emf` | `RESTEndpoint/Service/impl/` | NEW services | `TierConfigService`, `BenefitConfigService` |
| `pointsengine-emf` | `RESTEndpoint/models/tier/` | NEW package | Tier request/response DTOs |
| `pointsengine-emf` | `RESTEndpoint/models/benefit/` | NEW package | Benefit request/response DTOs |
| `pointsengine-emf` | `RESTEndpoint/models/config/` | NEW package | Shared status/review DTOs |
| `pointsengine-emf` | `RESTEndpoint/validators/factory/` | NEW factories | `TierValidatorFactory`, `BenefitValidatorFactory` alongside existing `ValidatorFactory` |
| `pointsengine-emf` | `RESTEndpoint/validators/impl/tier/` | NEW package | 5 tier validators |
| `pointsengine-emf` | `RESTEndpoint/validators/impl/benefit/` | NEW package | 3 benefit validators |
| `pointsengine-emf` | `RESTEndpoint/Exceptions/handler/GlobalExceptionHandler.java` | EXTEND | Add handlers for `ConfigConflictException` (409) and config validation (422) |
| `pointsengine-emf` | `RESTEndpoint/Exceptions/` | NEW exception | `ConfigConflictException` |

### Indirectly Affected / Integration Points

| Component | How Affected | Risk Level |
|-----------|-------------|------------|
| `LoggerInterceptor` + `WebMvcConfig` | Must intercept new `/api/v1/tiers/**` and `/api/v1/benefits/**` paths. Currently intercepts all paths via `registry.addInterceptor(new LoggerInterceptor())` with no path restriction — **no change needed**. | LOW — verified: interceptor applies globally |
| `ShardContext` (ThreadLocal) | Reused as-is. New services call `ShardContext.get().getOrgId()` to extract orgId. | LOW — verified: pattern works for all existing controllers |
| `BaseMongoDaoImpl` | Reused as-is. New DAOs extend it, implement `getDataSourceManager()`, `getDatabase()`, `getCollection()`. | LOW — verified: 14 existing implementations follow same pattern |
| `MongoDataSourceManager` | Reused as-is. Provides org-sharded `MongoClient` instances. | LOW — verified: used by all MongoDB DAOs |
| `ApplicationCacheConfig` / Redis | New `@DistributedLock` will use Redis via `RedisCacheManager` or direct `RedisTemplate`. Redis is confirmed available: `redisson.properties` exists, `ApplicationCacheConfig` configures `JedisConnectionFactory` with Sentinel, `RedisCacheService` interface exists. | MEDIUM — new lock pattern, but infra is available |
| `GlobalExceptionHandler` | Extension required. Currently handles `MethodArgumentNotValidException` (400), `RequestValidationException` (400), `RuntimeException` (500). Needs new handlers for 409 and 422. | LOW — additive change only |
| EMF evaluation pipeline | **NOT affected in this iteration**. New MongoDB collections are disconnected from EMF rulesets. `SlabUpgradeService`, `SlabDowngradeService`, `PointsEngineSlabUpgradeInstructionExecutorImpl` etc. continue reading from MySQL `strategies` and `program_slabs` tables. | NONE — by design (no dual writes) |
| `UnifiedPromotionDaoImpl` | Not modified. Read-only DAO in EMF. Serves as reference pattern only. | NONE |

### Package Conflict Check

- `springdata/mongodb/model/` — existing contents: `BaseMongoEntity.java`, `moonknight/`, `unifiedpromotion/`, `filter/`, plus ~30 entity files. New `config/` package does NOT conflict. **Verified.**
- `springdata/mongodb/dao/` — existing contents: 22 DAO interfaces + `impl/` directory with 14 implementations. New `TierConfigDao`, `BenefitConfigDao` interfaces and implementations do NOT conflict. **Verified.**
- `RESTEndpoint/models/` — existing contents: ~50+ model classes + `enums/`, `moonknight/` subdirectories. New `tier/`, `benefit/`, `config/` subdirectories do NOT conflict. **Verified.**
- `RESTEndpoint/validators/` — existing contents: `factory/` (ValidatorFactory, ValidatorTypes, etc.), `impl/` (PromotionValidator implementations), `Interfaces/`. New `factory/TierValidatorFactory`, `factory/BenefitValidatorFactory`, `impl/tier/`, `impl/benefit/` do NOT conflict. **Verified.**
- `RESTEndpoint/controller/impl/` — existing controllers: `ProgramsApiController`, `OrgConfigController`, `OrgConfigExportController`, `BulkOrgConfigUpdateController`. New `TierConfigController`, `BenefitConfigController` do NOT conflict. **Verified.**

---

## Side Effects Analysis

### Behavioral Side Effects

1. **No EMF pipeline impact**: The new APIs write exclusively to MongoDB `tier_configs` and `benefit_configs` collections. The EMF evaluation engine reads from MySQL `program_slabs`, `strategies`, and `customer_enrollment`. These data paths are entirely disjoint. **No side effects on tier evaluation, point allocation, downgrade, renewal, or Kafka event publishing.**

2. **No impact on existing REST endpoints**: New controllers serve new URL paths (`/api/v1/tiers`, `/api/v1/benefits`). Existing promotion/org-config endpoints are untouched. The `LoggerInterceptor` applies globally and will intercept new paths without configuration change.

3. **MongoDB shard routing**: New collections use the same `emf` database name as existing collections (`org_configuration`, `unified_promotions`). The `MongoDataSourceManager` routes by orgId to the correct shard. Adding new collections to an existing database has no routing impact — **verified**: each DAO specifies its own collection name, and MongoDB creates collections lazily.

4. **Redis contention risk**: The `@DistributedLock` mechanism will use Redis for lock keys (`lock_tier_status_{orgId}_{tierId}`, `lock_benefit_status_{orgId}_{benefitId}`). The existing Redis usage in emf-parent is primarily for caching (`ApplicationCacheConfig` with named TTL regions). Lock keys occupy a different keyspace and have a 300s TTL. Risk of contention with existing cache operations is LOW, but the lock implementation must use a separate logical namespace or prefix to avoid collision with cache keys.

### Performance Side Effects

1. **MongoDB index creation**: 4 indexes on `tier_configs`, 5 indexes on `benefit_configs`. These are created on new collections and have ZERO impact on existing collection performance.

2. **Query patterns are well-indexed**: The Architect's proposed indexes cover all documented query paths:
   - List tiers by program: `{ orgId, programId, status, serialNumber }` — covered.
   - Lookup tier by tierId: `{ orgId, tierId, status }` — covered.
   - Name uniqueness: `{ orgId, programId, name, status }` — covered.
   - Benefit-tier linkage: `{ orgId, "linkedTiers.tierId" }` — covered.

3. **Pagination**: The Architect specifies offset/limit pagination following the existing `ProgramsApiController` pattern. For tier/benefit config (low-volume data — typically <50 tiers per program), offset pagination is acceptable. G-04.2 is satisfied.

4. **Cross-entity validation queries**: Creating a tier validates linked benefit IDs (queries `benefit_configs`); creating a benefit validates linked tier IDs (queries `tier_configs`). These are index-supported lookups per operation, not N+1 patterns. Acceptable for config CRUD traffic.

### Integration Side Effects

1. **No Kafka events published**: The new APIs do not publish any events. Downstream consumers (communications, analytics) are unaffected. When the future sync iteration connects MongoDB config changes to EMF, Kafka integration will be needed — but that is explicitly out of scope.

2. **No intouch-api-v3 interaction**: The new APIs are self-contained in emf-parent. No calls to or from intouch-api-v3. The `UnifiedPromotionDaoImpl` in emf-parent is read-only and unmodified.

---

## Security Considerations

### G-03 Compliance Check (CRITICAL)

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| G-03.1: No SQL concatenation | N/A | No SQL queries. All data access is via MongoDB DAO with `Filters` API (parameterized). |
| G-03.2: Input validation at service boundary | COMPLIANT | Two-layer validation: Bean Validation on DTOs + ValidatorFactory business rules. |
| G-03.3: Auth on every endpoint | RISK — see below | Architect states "Authorization handled at UI layer, not backend." This means the API endpoints themselves do NOT enforce who can approve vs. submit. |
| G-03.5: No sensitive data in logs | COMPLIANT (by design) | Tier/benefit config data is not PII. However, `createdBy`/`lastModifiedBy` fields may contain user identifiers — ensure these are not logged at INFO level. |
| G-03.7: Rate limiting | NOT ADDRESSED | No rate limiting specified for new endpoints. Config CRUD is low-volume, but a malicious actor could spam creates. |

### Specific Security Risks

1. **No server-side authorization (G-03.3 deviation)**: The BA decision states "Authorization for maker-checker handled at UI layer, not backend." This means any authenticated caller with a valid `X-CAP-ORG-ID` header can approve their own submissions. This is a **known trade-off** documented in Key Decisions, not an oversight. However, it is a G-03.3 deviation that should be explicitly acknowledged. **Severity: MEDIUM** — acceptable for internal-facing API in initial iteration, but must be addressed before any external exposure.

2. **Tenant isolation (G-07) — COMPLIANT**: 
   - OrgId sourced from `X-CAP-ORG-ID` header via `LoggerInterceptor` -> `ShardContext` (verified in source).
   - MongoDB queries scoped by orgId at both shard routing level (`MongoDataSourceManager.getDataSource(orgId)`) and query filter level.
   - Cross-entity validation (linked tier/benefit IDs) includes orgId in lookup queries — preventing cross-tenant reference injection.
   - **Verified**: `ShardContext` uses `int` orgId, `BaseMongoDaoImpl.getTemplate()` takes `Integer orgId`. Types are consistent.

3. **No injection risk on MongoDB queries**: The DAO pattern uses `com.mongodb.client.model.Filters` API which is parameterized. No string concatenation in query construction. The `Map<String, Object> parameters` field on tier/benefit configs stores arbitrary data — but this is written to MongoDB as a nested document, not interpolated into queries. **LOW risk**.

4. **Comment field (max 150 chars)**: The review comment is stored as a String. The Architect specifies `@Size(max = 150)` via Bean Validation. This prevents oversized input. HTML/script injection in comments is a display-layer concern (frontend), not a backend storage concern for MongoDB. **LOW risk**.

---

## Guardrail Compliance (CRITICAL Guardrails)

### G-01: Timezone & Date/Time (CRITICAL)

| Check | Status | Evidence |
|-------|--------|----------|
| G-01.1: Store timestamps in UTC | COMPLIANT | Architect specifies `createdOn: Instant`, `lastModifiedOn: Instant`. `Instant` is inherently UTC. |
| G-01.3: Use java.time | COMPLIANT | Document model uses `Instant`, not `java.util.Date`. |
| G-01.6: ISO-8601 in API | COMPLIANT | BA and Architect both specify ISO-8601 UTC timestamps. |

**Note**: The existing `program_slabs.created_on` is `datetime` (timezone-unaware MySQL). The new `TierConfig.createdOn` is `Instant` (UTC). No data sync between these, so no timezone mismatch risk in this iteration.

### G-03: Security (CRITICAL)

See Security Considerations section above. **No blockers. One documented deviation (G-03.3 — auth at UI layer).**

### G-07: Multi-Tenancy (CRITICAL)

| Check | Status | Evidence |
|-------|--------|----------|
| G-07.1: Every query includes tenant filter | COMPLIANT | All DAO methods take orgId parameter. `BaseMongoDaoImpl.getTemplate(orgId, ...)` routes to org-specific shard + all queries include orgId filter. |
| G-07.2: Tenant context at request boundary | COMPLIANT | `LoggerInterceptor` extracts `X-CAP-ORG-ID` -> `ShardContext.set(orgId)`. Verified in source: `LoggerInterceptor.java` line 44-48. |
| G-07.3: Background jobs carry tenant context | N/A | No background jobs in this iteration. All operations are synchronous REST. |
| G-07.4: Test tenant isolation | REQUIRED | Must be tested. Not a design issue but a test requirement. |
| G-07.5: Logs include org ID | COMPLIANT | `LoggerInterceptor` sets `MDC.put(EMFUtils.REQUEST_ORG_ID_MDC, orgId)`. All log lines include org context. |

---

## Risks

### R-01: Redis dependency for distributed locking (Severity: MEDIUM, Likelihood: LOW)

**Finding**: The `@DistributedLock` annotation requires Redis. Redis IS available in emf-parent (confirmed: `redisson.properties`, `ApplicationCacheConfig` with `JedisConnectionFactory`, `RedisCacheService` interface, `RedisCacheServiceImpl` class). However, the existing `LockManager` in intouch-api-v3 uses `RedisCacheManager.getCache()` + `putIfAbsent()` pattern — a non-blocking, non-reentrant lock using cache entries. This is NOT a true distributed lock (no atomic SET NX with TTL). 

**Impact**: The intouch-api-v3 `LockManager` implementation has a race condition window between `cache.get(key) == null` check and `cache.putIfAbsent(key, key)`. Under high concurrency, two threads could both pass the null check. The emf-parent implementation should use Redis `SET NX PX` (atomic set-if-not-exists with TTL) via `RedisTemplate` for correctness.

**Mitigation**: Developer phase must implement `@DistributedLock` using `RedisTemplate.opsForValue().setIfAbsent(key, value, timeout, TimeUnit)` — NOT the `RedisCacheManager` pattern from intouch-api-v3.

### R-02: Orphaned MongoDB config documents (Severity: MEDIUM, Likelihood: MEDIUM)

**Finding**: The document-per-version pattern creates SNAPSHOT documents on every edit approval. Over time, these accumulate. The Architect does not specify a cleanup/archival strategy.

**Impact**: For actively managed programs with frequent config changes, the `tier_configs` and `benefit_configs` collections will grow with SNAPSHOT documents. MongoDB indexes include status in the filter, so query performance is not affected. But storage grows unboundedly.

**Mitigation**: Add a TTL index or periodic cleanup job for SNAPSHOT documents older than N days. Not blocking for initial iteration, but should be tracked.

### R-03: Circular validation dependency between tier and benefit services (Severity: LOW, Likelihood: HIGH)

**Finding**: The Architect notes a "soft dependency" between `tier-config` and `benefit-config`: tier creation validates linked benefit IDs (queries `benefit_configs`), and benefit creation validates linked tier IDs (queries `tier_configs`). This creates a circular service dependency.

**Impact**: Spring circular dependency injection if services reference each other directly. 

**Mitigation**: Use DAO-level cross-entity validation (inject DAOs, not services) or use `@Lazy` injection. The existing codebase does not have this pattern, so the Designer must define the dependency direction explicitly.

### R-04: `BaseMongoEntity` is empty — no common fields (Severity: LOW, Likelihood: HIGH)

**Finding**: `BaseMongoEntity` is an empty class (`implements Serializable` only). It provides no `_id`, `orgId`, or timestamp fields. The Architect proposes `ConfigBaseDocument extends BaseMongoEntity` with all common fields. This is correct but means the base class provides no reusable behavior.

**Impact**: None on correctness. The new `ConfigBaseDocument` must define all fields from scratch: `_id` (ObjectId), `orgId`, `programId`, `status`, `version`, `parentId`, `entityId`, `comments`, `createdOn`, `createdBy`, `lastModifiedOn`, `lastModifiedBy`.

**Mitigation**: None needed. This is consistent with how other entities in the codebase work (each defines its own fields).

### R-05: No idempotency key implementation defined (Severity: MEDIUM, Likelihood: MEDIUM)

**Finding**: The Architect specifies `X-Idempotency-Key` header per G-06.1 but defers the storage mechanism (Redis with TTL vs. MongoDB collection) to Designer/Developer. Without this, duplicate POST requests on retry could create duplicate DRAFT configs.

**Impact**: If a client retries a `POST /tiers` due to network timeout, two DRAFT tiers with different `tierId` UUIDs could be created.

**Mitigation**: Must be resolved in Designer phase. Recommend Redis with 5-minute TTL for simplicity (infrastructure is available).

### R-06: New controllers use @Controller vs @RestController ambiguity (Severity: LOW, Likelihood: MEDIUM)

**Finding**: Existing controllers use `@Controller` (implementing Swagger-generated API interfaces). The Architect's new controllers are hand-written (not Swagger-generated). The open question about `@Controller` vs `@RestController` is unresolved.

**Impact**: If `@Controller` is used without `@ResponseBody` on methods, Spring will attempt view resolution instead of JSON serialization. If `@RestController` is used, it works but deviates from existing pattern.

**Mitigation**: Use `@RestController` for new hand-written controllers. The existing `@Controller` pattern exists because those classes implement Swagger-generated interfaces that already have `@ResponseBody`. New controllers have no such constraint. Per G-12.2, follow the pattern's intent (return JSON), not the literal annotation.

### R-07: ShardContext orgId is `int`, not `long` (Severity: LOW, Likelihood: LOW)

**Finding**: `ShardContext` stores orgId as `int`. `BaseMongoDaoImpl.getTemplate()` takes `Integer orgId`. The Architect's document model specifies `orgId: Long`. If orgId values exceed `Integer.MAX_VALUE` (2.1 billion), there would be a truncation issue.

**Impact**: Extremely unlikely — org IDs are typically small integers. But the type mismatch between the document model (`Long`) and the infrastructure (`int`/`Integer`) must be handled consistently.

**Mitigation**: Use `Integer` for orgId in the document model to match the existing infrastructure, OR cast safely in the DAO layer. Designer phase should resolve.

---

## Verified vs Assumed Impacts

### Verified (with codebase evidence)

- [x] `BaseMongoDaoImpl` can be extended as-is — 14 existing implementations confirm the pattern
- [x] `MongoDataSourceManager` supports new collections in `emf` database — existing DAOs use same database name
- [x] `ShardContext` + `LoggerInterceptor` provide orgId threading for new controllers — source code verified
- [x] `GlobalExceptionHandler` is extensible — `@RestControllerAdvice` applies to all controllers
- [x] Redis is available in emf-parent — `redisson.properties`, `ApplicationCacheConfig`, `RedisCacheService` confirmed
- [x] No package name conflicts with proposed new packages — directory listings verified
- [x] `WebMvcConfig` interceptor registration applies globally — no path filtering, new paths auto-intercepted
- [x] Existing `ValidatorFactory` pattern is replicable for new domain — source code reviewed
- [x] `LockManager` (intouch-api-v3) implementation uses `RedisCacheManager` cache entry pattern — source code reviewed
- [x] `customer_enrollment` and `program_slabs` schemas confirmed from cc-stack-crm SQL files

### Assumed (not verified due to LSP unavailability)

- [ ] Spring component scanning in `pointsengine-emf` will pick up new `@Component`/`@Controller` classes — assumed based on existing scan config but XML-based scan (`spring-rest-endpoint-config.xml`) may need package additions
- [ ] MongoDB driver version supports all proposed query patterns — assumed compatible
- [ ] `@Valid` + Bean Validation JSR-380 annotations are on the classpath — `@Valid` is used on existing controllers, but the specific annotations (`@NotBlank`, `@Pattern`) need the `javax.validation` or `jakarta.validation` dependency
- [ ] `RedisTemplate` bean is available for direct use — `RedisCacheManager` is configured, but whether `RedisTemplate` is exposed as a bean needs verification

---

## Product Requirements Verification

### Requirements Fulfilment Table

| User Story | Requirement | Architect Coverage | Status |
|------------|-------------|-------------------|--------|
| US-1: List Tiers | GET /tiers with programId, status filter, includeDraftDetails, ordered by serialNumber | Fully addressed: endpoint defined, indexes cover query, draft enrichment specified | FULFILLED |
| US-2: Create Tier | POST /tiers with all BRD fields, maker-checker draft creation, structured validation | Fully addressed: TierConfig document model has all fields, two-layer validation, DRAFT status on create | FULFILLED |
| US-3: Update Tier | PUT /tiers/{tierId} with draft-on-edit of ACTIVE, in-place update of DRAFT, conflict on PENDING_APPROVAL | Fully addressed: versioning approach matches UnifiedPromotion pattern exactly | FULFILLED |
| US-4: List Benefits | GET /benefits with programId, status/type/category/triggerEvent filters | Fully addressed: endpoint defined, indexes cover filters | FULFILLED |
| US-5: Create Benefit | POST /benefits with all BRD fields, type-specific parameter validation | Fully addressed: BenefitConfig model has all fields, BenefitTypeParameterValidator handles type-specific rules | FULFILLED |
| US-6: Update Benefit | PUT /benefits/{benefitId} with same draft pattern as tiers | Fully addressed: follows same versioning approach | FULFILLED |
| US-7: Submit for Approval | PUT /{entity}/{id}/status with PENDING_APPROVAL transition, distributed lock | Fully addressed: status endpoint with ConfigStatusTransitionValidator, @DistributedLock | FULFILLED |
| US-8: Approve | POST /{entity}/{id}/review with APPROVE action, parent->SNAPSHOT, draft->ACTIVE | Fully addressed: approval flow detailed in versioning approach section | FULFILLED |
| US-9: Reject | POST /{entity}/{id}/review with REJECT action, mandatory comment | Fully addressed: ReviewCommentValidator enforces mandatory comment on reject | FULFILLED |
| US-10: Stop/Pause | PUT /{entity}/{id}/status with STOPPED/PAUSED transitions | Fully addressed: state machine includes ACTIVE->PAUSED, PAUSED->ACTIVE, ACTIVE/PAUSED->STOPPED | FULFILLED |
| US-11: List Pending Approvals | GET /{entity}/approvals?programId with full config + diff + parent details | Partially addressed: endpoint defined, but diff computation (old vs new values) is not detailed in Architect doc | PARTIAL |

### Product Boundary Check

1. **Tier-Benefit bidirectional linkage**: The Architect models `TierConfig.linkedBenefits[]` (tier references benefits) and `BenefitConfig.linkedTiers[]` (benefit references tiers). This is bidirectional as required by the BA. **COMPLIANT.**

2. **Status lifecycle completeness**: `ConfigStatus` enum includes DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, STOPPED, SNAPSHOT. State machine covers all transitions from BA US-10 AC-6. **COMPLIANT.**

3. **All BRD tier config fields represented**: Eligibility (kpiType, threshold, secondaryCriteria), Validity (type, periodInDays, fixedDate), Renewal (conditions with all retention metrics, schedule, duration), Downgrade (targetTierId, schedule, gracePeriod, validateOnReturnTransaction), Upgrade (mode, bonusPoints), Nudge (enabled, reminderBeforeDays, templateReferences), Core (name, description, color, serialNumber). **COMPLIANT.**

4. **Structured validation errors**: Error response shape defined with field-level errors array, HTTP 422 for validation, 409 for conflicts. **COMPLIANT.**

5. **Multi-tenancy on all endpoints**: OrgId sourced from header via ShardContext, never from request body. All queries org-scoped. **COMPLIANT.**

### Product-Level Issues

1. **US-11 diff computation not specified**: The BA requires "the diff against the parent (for edits -- old value vs new value)" in the approvals listing. The Architect defines the endpoint but does not specify how the diff is computed or what the diff response shape looks like. This is a gap that the Designer must address. **Severity: LOW** — not a blocker, can be resolved in Designer phase.

2. **Benefit trigger event validation gap**: The BA specifies trigger events (TIER_UPGRADE, TIER_RENEWAL, TRANSACTION, BIRTHDAY, MANUAL) and the Architect includes `TriggerEventValidator`. However, the brdQnA (PB-5) notes that BIRTHDAY and MANUAL triggers may not exist in the current platform. Since this iteration only stores configuration (no EMF integration), storing these enum values is safe. But the Designer should flag that not all trigger events are wirable today. **Severity: LOW** — informational, no design change needed.

---

## CRITICAL Guardrail Violations

**None found.** The Architect's solution is compliant with all CRITICAL guardrails (G-01, G-03, G-07, G-12). The G-03.3 deviation (auth at UI layer) is a documented, intentional decision — not an oversight.

---

## Blockers

**None.** No architectural changes are required. All issues identified are resolvable in the Designer or Developer phases.

---

## Recommendations for Designer Phase

1. **Resolve @Controller vs @RestController**: Use `@RestController` for new hand-written controllers.
2. **Define diff computation strategy for US-11**: Specify how to compute field-level diffs between PENDING_APPROVAL document and its ACTIVE parent.
3. **Specify @DistributedLock implementation**: Use `RedisTemplate.opsForValue().setIfAbsent()` with TTL — NOT the `RedisCacheManager` cache-entry pattern from intouch-api-v3's `LockManager`.
4. **Resolve orgId type**: Use `Integer` (not `Long`) in document model to match `ShardContext` and `BaseMongoDaoImpl` signatures.
5. **Define circular dependency resolution**: Tier validates benefits, benefits validate tiers. Use DAO-level injection (not service-level) for cross-entity lookups.
6. **Verify Spring component scan**: Check `spring-rest-endpoint-config.xml` to ensure new packages are within scan scope.
7. **Define idempotency key mechanism**: Recommend Redis SET NX with 5-minute TTL, checked in a controller-level interceptor or service-layer guard.
8. **Add SNAPSHOT cleanup strategy**: Define TTL or archival policy for version history documents.
