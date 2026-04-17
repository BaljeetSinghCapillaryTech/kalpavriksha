# Code Analysis — intouch-api-v3

**Feature**: Benefit Category CRUD (CAP-185145)
**Phase**: 5 — Codebase Research
**Date**: 2026-04-18
**Repo path**: `/Users/anujgupta/IdeaProjects/intouch-api-v3-2/intouch-api-v3`
**Repo role**: REST API gateway — Spring Boot 3.2.2 / Java 17 — thin REST facade over EMF Thrift + MongoDB for UnifiedPromotion.

---

## Key Architectural Insights (Phase 4 Question Answers)

| # | Question | Answer | Confidence |
|---|----------|--------|------------|
| OQ-34 | Authz at Client boundary — who writes? | THREE auth paths. **KeyOnly** (API key in `X-CAP-API-KEY` + `X-CAP-API-ORG-ID` headers) is **GET-only** — hardcoded check at line 82 of `IntouchAuthenticationServiceImpl.java`: `if(!HttpMethod.GET.equals(token.getRequestType())) throw`. **BasicAndKey** (username+password or username+auth-key) can POST/PUT. **IntegrationsClient** (OAuth Bearer JWT) can POST/PUT. The `ResourceAccessAuthorizationFilter` delegates to Zion SDK for per-URI authorization and can be switched to blocking mode per org. The `@PreAuthorize("hasRole('ADMIN_USER')")` is used on exactly ONE endpoint (`/v3/admin/authenticate`). The `ROLE_KEY_USER` is assigned for API-key-only callers. **For new write endpoints (POST BenefitCategory), only BasicAndKey or OAuth flows apply** — KeyOnly is GET-only. No explicit "ROLE_WRITE_BENEFIT_CATEGORY" exists — the default gate is "authenticated + Zion AZ check on URI/method". | C7 |
| OQ-36 | Error envelope Thrift→REST mapping | `ResponseWrapper<T>` is the universal envelope (3 fields: `data`, `errors: List<ApiError>`, `warnings: List<ApiWarning>`). `ApiError` = `{Long code, String message}`. `ApiWarning` = `{String message}`. **No HTTP 409 Conflict class exists in the codebase** — the closest pattern is `InvalidInputException` → `TargetGroupErrorAdvice` → `HTTP 400 BAD_REQUEST`. Duplicate-name handling (e.g. `TARGET_LOYALTY.TARGET_GROUP_NAME_ALREADY_EXIST`) is mapped to HTTP 400, not 409. The `EMFThriftException` → `HTTP 500 INTERNAL_SERVER_ERROR`. A new `ConflictException` class must be **added** for the D-27/D-28 409 semantics required by BenefitCategory. | C7 |
| OQ-37 | Validation layer placement | **Dual-layer** is the established pattern. (1) REST layer: JSR-380 Bean Validation annotations on model fields (`@NotNull`, `@NotBlank`, `@Size`, `@Valid` cascade) + `@Validated` on controller `@RequestBody`. These are caught by `TargetGroupErrorAdvice.handleMethodArgumentNotValidException` → HTTP 400. Custom validators in `com.capillary.intouchapiv3.validators.*` (e.g., `@FutureOrPresentDate`, `@ValidOrgEntity`). (2) Facade/service layer: manual `InvalidInputException` throws for business-rule violations (`ALREADY_EXIST`, state transitions, immutable field changes). For BenefitCategory: null/blank name → REST Bean Validation (@NotBlank); active-duplicate check (D-28) → Facade service layer throw `InvalidInputException` (or new `ConflictException` if we want 409). | C7 |
| OQ-38 | JVM timezone in production | **NOT pinned explicitly**. Dockerfile CMD: `java -javaagent:... -Xms$XMS_VALUE -Xmx$XMX_VALUE $EXTRA_OPTIONS -jar *.jar` — no `-Duser.timezone` flag. No `spring.jackson.time-zone` in `application.properties`. No `TZ=` env var in Dockerfile. `TimeZoneUtil.java` uses `ZoneId.systemDefault()` throughout — it is JVM-TZ-dependent. **OQ-38 is NOT resolved by this repo's config** — the JVM default TZ is environment-dependent. D-24's requirement to force UTC in `Date ↔ i64` conversions is MANDATORY, not optional. | C7 |
| OQ-40 | ISO-8601 format pin at REST | **Partially pinned, not globally configured**. `spring.jackson` properties absent. The pattern `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")` is used **field-by-field** on DTOs (e.g., `CustomerPromotionV3Dto`, `EnrolmentDetailsDto`, `OptInDetailsDto`, `PromotionSchedule`, `JourneySchedule`). The `XXX` format produces timezone-offset-aware strings (e.g., `+05:30`) rather than UTC-`Z` suffix strings. `IntouchAuthenticationServiceImpl` uses `new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ")` for its own token format. **For BenefitCategory REST DTOs, the field-by-field `@JsonFormat` approach is the established pattern, with `XXX` offset. To get UTC `Z` suffix per G-01, use `timezone = "UTC"` in the `@JsonFormat` annotation: `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")`**. | C7 |

---

## Section 1 — REST Controller Patterns

### Canonical Package
All client-facing controllers live in:
- `com.capillary.intouchapiv3.resources` — primary controllers (v3 path)
- `com.capillary.intouchapiv3.resources.v3_1` — newer v3.1 controllers

### URL Versioning
- URL-path versioning. Active versions: `/v3/` (primary), `/v3.1/` (secondary for connected-orgs features).
- Internal endpoints: `/v3/internal/` (e.g., `InternalCustomerController` at `/v3/internal/customers`).
- New endpoints for BenefitCategory should use `/v3/benefitCategories` and `/v3/benefitCategorySlabMappings`.

### Canonical Controller Shape (C7)

```java
@RestController
@RequestMapping("/v3/<resource>")
@Slf4j
public class XyzController {
    @Autowired private XyzFacade xyzFacade;   // delegate to facade, NOT service directly

    @PostMapping(produces = "application/json")
    public ResponseEntity<ResponseWrapper<Xyz>> create(
            @Valid @RequestBody XyzRequest request,
            AbstractBaseAuthenticationToken token,
            HttpServletRequest httpRequest) {
        IntouchUser user = token.getIntouchUser();
        Xyz created = xyzFacade.create(user.getOrgId(), request, httpRequest);
        return new ResponseEntity<>(new ResponseWrapper<>(created, null, null), HttpStatus.CREATED);
    }
}
```

Key patterns observed (all verified C7):
- `@RestController` + `@RequestMapping("/v3/...")` — no base class or `@Controller`
- No `extends` base class on controllers
- `AbstractBaseAuthenticationToken token` as a method parameter (injected by Spring Security) — resolves via `AbstractBaseAuthenticationToken.getIntouchUser()` to get `IntouchUser`
- `user.getOrgId()` is the tenant scope — always `long`
- Returns `ResponseEntity<ResponseWrapper<T>>`
- No `@Valid` on class level; `@Valid` or `@Validated` per `@RequestBody` parameter
- `ResponseWrapper<T>` constructor: `new ResponseWrapper<>(data, errors, warnings)` — nulls for empty lists

### Client-facing vs. Admin-facing Distinction
- **No separate URL prefix or security bean for "admin"**. The only admin gate found is `@PreAuthorize("hasRole('ADMIN_USER')")` on one endpoint.
- `KeyOnly` auth callers get `isKeyBased=true` on `IntouchUser` and are limited to HTTP GET (enforced in `IntouchAuthenticationServiceImpl.validate(KeyOnlyAuthenticationToken)`).
- "Internal" controllers use `/v3/internal/` path prefix — but no security annotation difference was found; distinction is by convention only.

**Impact for BenefitCategory**: Write endpoints (POST, PATCH) will be accessible to any authenticated BasicAndKey or OAuth user. If write access is to be restricted to admins only, a `@PreAuthorize("hasRole('ADMIN_USER')")` or Zion AZ configuration change is needed. This is the unresolved core of **OQ-34** — confirm with product whether ANY authenticated Client can write, or only ADMIN_USER / specific Zion resource permission.

---

## Section 2 — REST ↔ Thrift Client Bridge

### Canonical Pattern (C7 — from `PointsEngineRulesThriftService`, `EmfDataManagerThriftService`, `EmfPromotionThriftService`)

```java
@Service
@Loggable
@Profile("!test")
public class XyzThriftService {

    private XyzService.Iface getClient() throws Exception {
        return RPCService.rpcClient(XyzService.Iface.class, "emf-thrift-service", 9199, 60000);
    }

    public ResultType doSomething(int orgId, int programId) throws Exception {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            return getClient().doSomethingRpc(orgId, programId, serverReqId);
        } catch (Exception e) {
            logger.error("Error... ServerReqId: " + serverReqId, e);
            throw new EMFThriftException("Error: " + e);
        }
    }
}
```

Key observations:
- **No connection pool / factory bean** — `RPCService.rpcClient(...)` is a static utility from `com.capillary.commons.thrift.external.RPCService`. It creates a client per call (or pools internally — not visible here).
- **Service name**: `"emf-thrift-service"` (Kubernetes service name).
- **Port**: `9199` for PointsEngineRules. Timeout: `60000ms` or `10000ms` depending on operation.
- **No retry logic in intouch-api-v3** — `PointsEngineRulesThriftService.publishPeConfig` is the only exception, checking `SocketTimeoutException` in the catch chain.
- **All exceptions bubble as `EMFThriftException`** — a `RuntimeException` wrapping the original message string. The `TargetGroupErrorAdvice` catches `EMFThriftException` → HTTP 500.
- **org/program params passed as `int`** via explicit `Math.toIntExact()` or direct cast `(int) orgId`.
- **`serverReqId`** is a correlating request ID via `CapRequestIdUtil.getRequestId()`.

### For BenefitCategory Thrift Service
New file location: `com.capillary.intouchapiv3.services.thrift.BenefitCategoryThriftService` following the exact same pattern.

The new Thrift Iface will be consumed via `RPCService.rpcClient(PointsEngineRuleService.Iface.class, "emf-thrift-service", 9199, 60000)` — SAME service, just new methods on the existing Iface (per thrift-ifaces analysis which confirmed benefits methods are already on PointsEngineRuleService).

---

## Section 3 — Maker-Checker Workflow

The existing MC pattern in intouch-api-v3 is implemented via `UnifiedPromotion` (MongoDB `@Document`). The flow is:

1. **State machine** lives in `PromotionStatus` enum: `DRAFT → PENDING_APPROVAL → ACTIVE → PAUSED/STOPPED`. State transitions validated in `UnifiedPromotionValidatorService.validatePromotionUpdate()`.
2. **Status change** endpoint: `PUT /v3/requests/{entityType}/{entityId}/status` (`RequestManagementController`) — a separate endpoint, not embedded in the resource controller. Takes `existingStatus` query param + `StatusChangeRequest` body containing the target `promotionStatus` + optional `reason`.
3. **Review endpoint**: `POST /v3/promotions/{id}/review` (`UnifiedPromotionController`) — approve or reject. `PromotionReviewRequest` body contains `ApprovalStatus`.
4. **Orchestration**: `EntityOrchestrator` + multiple `Transformer` implementations handle cross-entity coordination at ACTIVE-transition time (creates PE rules, target groups, limits via separate Thrift calls).
5. **MongoDB document**: `UnifiedPromotion` holds status + `parentId` for versioning when updating ACTIVE promotions.

**Implication for BenefitCategory (D-25)**: MC is NOT needed for MVP. The cost of adding it later:
- Add a `lifecycleState` column to `benefit_categories` (MySQL migration)
- Add a `RequestManagementController`-style status endpoint or reuse the existing one with a new `EntityType` enum value
- Add `StatusTransitionValidator` logic
- No MongoDB involvement needed (MySQL-backed, not MongoDB-backed)
- Estimated: ~1 sprint of incremental work, not a redesign

---

## Section 4 — Validation Layer (OQ-37)

**Pattern** (C7): Dual-layer, both active.

**Layer 1 — REST (Bean Validation)**:
- JSR-380 / Jakarta Validation annotations on model/DTO fields: `@NotNull`, `@NotBlank`, `@Size(max=255)`, `@Valid` (cascade)
- Custom validator annotations in `com.capillary.intouchapiv3.validators.*` (e.g., `@FutureOrPresentDate`, `@ValidOrgEntity`, `@UniqueStreakName`)
- `@Valid` or `@Validated` on `@RequestBody` in controller methods
- `TargetGroupErrorAdvice.handleMethodArgumentNotValidException` → extracts field errors → `ResponseWrapper<String>` with `ApiError` list → HTTP 400
- `TargetGroupErrorAdvice.handleConstraintViolationException` → same mapping → HTTP 400

**Layer 2 — Facade/Service (Business Rules)**:
- `InvalidInputException(messageKey)` thrown on business violations
- `TargetGroupErrorAdvice.handleInvalidInputException` → `error(BAD_REQUEST, e)` → HTTP 400
- `ServiceException` → HTTP 400 (via `handleServiceException`)
- Duplicate name check: throws `InvalidInputException("TARGET_LOYALTY.TARGET_GROUP_NAME_ALREADY_EXIST")` — mapped to HTTP 400, NOT 409

**Gap for BenefitCategory (D-27/D-28)**:
The codebase has **no HTTP 409 Conflict** handling pattern. D-27 requires 409 for PATCH `{is_active: true}` on deactivated rows; D-28 requires 409 for POST on active duplicate. A new `ConflictException` class must be added and wired into `TargetGroupErrorAdvice` (or a new `@ControllerAdvice`).

---

## Section 5 — Error Envelope (OQ-36)

### `ResponseWrapper<T>` (C7)
**File**: `/src/main/java/com/capillary/intouchapiv3/models/ResponseWrapper.java`

```java
public class ResponseWrapper<T> {
    private T data;
    private List<ApiError> errors;
    private List<ApiWarning> warnings;

    public static class ApiError {
        private Long code;
        private String message;
    }
    public static class ApiWarning {
        private final String message;
    }
}
```

**JSON wire format** (inferred from field names + Jackson default serialization):
```json
{
  "data": { ... } | null,
  "errors": [{"code": 400, "message": "..."}] | null,
  "warnings": [{"message": "..."}] | null
}
```

### `@ControllerAdvice` — `TargetGroupErrorAdvice` (C7)

**File**: `/src/main/java/com/capillary/intouchapiv3/exceptionResources/TargetGroupErrorAdvice.java`

Complete exception → HTTP status mapping:

| Exception Class | HTTP Status | Notes |
|----------------|-------------|-------|
| `BadCredentialsException` | 401 UNAUTHORIZED | Auth failures |
| `NoActiveTargetFoundException` | 200 OK (with warning!) | Domain-specific — returns warning not error |
| `LockManagerException` | 500 INTERNAL_SERVER_ERROR | Distributed lock failure |
| `NotFoundException` | 200 OK | **IMPORTANT**: 404 NOT found → HTTP 200 with error body |
| `InvalidInputException` | 400 BAD_REQUEST | Business validation failures |
| `HttpMessageNotReadableException` | 400 BAD_REQUEST | Malformed JSON |
| `MethodArgumentNotValidException` | 400 BAD_REQUEST | Bean Validation failures |
| `OperationFailedException` | 500 INTERNAL_SERVER_ERROR | Generic operation failure |
| `EMFThriftException` | 500 INTERNAL_SERVER_ERROR | Any Thrift call failure |
| `ServiceException` | 400 BAD_REQUEST | Service-layer errors |
| `FilterConfigValidationException` | 400 BAD_REQUEST | Promotion filter validation |
| `TargetMergeException` | 400 or 500 | Depends on errorKey |
| `ConstraintViolationException` | 400 BAD_REQUEST | Method param constraints |
| `DataIntegrityViolationException` | 400 BAD_REQUEST | DB constraint violation |
| `AccessDeniedException` | 403 FORBIDDEN | Spring Security |
| `ApiException` | passthrough code | Veyron API exceptions |
| `TokenExpiredException` | 498 | Custom token expiry code |
| `Throwable` (catch-all) | 500 INTERNAL_SERVER_ERROR | Generic fallback |

**CRITICAL finding**: `NotFoundException` maps to **HTTP 200** (not 404). This is unconventional. For BenefitCategory `GET /v3/benefitCategories/{id}` where id doesn't exist, we need to decide: follow platform convention (200 + error body) or introduce a new pattern (proper 404). **Recommend following convention** (200 with `errors: [{code: 404, message: "..."}]`) to avoid disruption, but flag for Phase 7 Designer.

**CRITICAL gap**: No `ConflictException` or HTTP 409 handler exists. Must be added for D-27/D-28.

---

## Section 6 — Timestamp Serialization (D-24 verification)

### Jackson Configuration
- **No global `spring.jackson.*` properties** in `application.properties` — no `spring.jackson.time-zone`, no `spring.jackson.date-format`, no `spring.jackson.serialization.write-dates-as-timestamps`.
- **No `WebMvcConfigurer.extendMessageConverters` or `@Bean ObjectMapper` customizer** found.
- The `WebConfig` only adds `APIMigrationInterceptor` — no Jackson config.

### Field-Level @JsonFormat (C7)
The pattern used throughout is **field-level `@JsonFormat`**:
```java
@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")
private Date startDate;
```
- Pattern: `yyyy-MM-dd'T'HH:mm:ssXXX` — ISO-8601 with timezone offset (e.g., `2026-04-18T10:30:00+05:30`)
- **Uses `XXX` (offset like `+05:30`) not `'Z'` (fixed UTC)**
- No explicit `timezone = "UTC"` in any existing annotation — means Jackson uses JVM default timezone

### JVM TZ (OQ-38) — NOT RESOLVED
**Finding**: No `-Duser.timezone=UTC` in Dockerfile CMD. No `TZ` env var. `TimeZoneUtil.java` uses `ZoneId.systemDefault()` throughout. The `TimeZoneUtil.convertFromOrgToServerTimeZone` and `removeServerOffsetAndFormatISO` methods show org-TZ-aware conversion logic — but this applies to Promotion scheduling, not to Thrift timestamp marshaling.

**Production risk**: If JVM TZ is IST (as is common in India-hosted deployments), `Calendar.getInstance()` and `new Date()` operations produce IST-based timestamps, and `@JsonFormat` without explicit UTC will serialize dates as IST offset (`+05:30`).

**Recommendation for BenefitCategory DTOs**:
```java
@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")
private Date createdOn;
```
This pins UTC explicitly at the field level, independent of JVM TZ.

---

## Section 7 — Authentication & Authorization (OQ-34)

### Three Auth Flows (C7)

**Flow 1 — KeyOnly** (`KeyOnlyAuthenticationFilter`):
- Headers: `X-CAP-API-AUTH-ORG-ID` + `X-CAP-API-AUTH-KEY`
- Hardcoded to GET requests only (`HttpMethod.GET` check in `IntouchAuthenticationServiceImpl.validate(KeyOnlyAuthenticationToken)`)
- `IntouchUser.isKeyBased = true`
- `ResourceAccessAuthorizationFilter` skips Zion AZ for `isKeyBased=true` users (line 128)
- Role: `ROLE_KEY_USER`

**Flow 2 — BasicAndKey** (`BasicAndKeyAuthenticationFilter`):
- Headers: HTTP `Authorization: Basic base64(username:password)` or `Authorization: Basic base64(username:)` + `X-CAP-API-AUTH-KEY`
- Validates against Zion SDK
- `isKeyBased` = true when auth-key path (not password)
- Role: `ROLE_<entityType>` (e.g., `ROLE_TILL`, `ROLE_ADMIN_USER`)
- Supports GET, POST, PUT, DELETE
- `ResourceAccessAuthorizationFilter` applies Zion AZ for `TILL` or `STR_SERVER` entity types (not for key-based or non-TILL/STR_SERVER types)

**Flow 3 — IntegrationsClient / OAuth** (`IntegrationsClientAuthenticationFilter`):
- Headers: `Authorization: Bearer <JWT>` (OAuth token from `/v3/oauth/token/generate`)
- Validates via Zion SDK with `clientKey` extracted from JWT
- `IntouchUser.clientKey` is set; `isKeyBased` = false
- Zion AZ uses `AuthorizationIntegrationClientRequest` with `clientKey` + URI + HTTP method
- Supports full CRUD

### Client Identity → orgId
`IntouchUser.orgId` (long) is the tenant scope. Injected at authentication time from Zion response or request header. All controller methods extract `user.getOrgId()`.

### Authz for BenefitCategory Writes (OQ-34 resolution)
**Confirmed**: Write endpoints (POST, PATCH) will be callable by:
- BasicAndKey users (username+password or username+auth-key)
- OAuth/IntegrationsClient users

**Not callable** by KeyOnly users (GET only).

**Admin-only restriction**: Only `AuthCheckController.getAdminstatus` uses `@PreAuthorize("hasRole('ADMIN_USER')")`. If writes need to be admin-only, add `@PreAuthorize("hasRole('ADMIN_USER')")` to write methods OR configure Zion AZ to block the new URIs for non-admin callers.

**Recommendation for Phase 6 Architect**: OQ-34 is now half-resolved — the mechanism is clear. Product must decide: can any authenticated Capillary Client `TILL`/`OAUTH` caller write BenefitCategory, or is it restricted to admin callers? This drives whether `@PreAuthorize` is needed.

---

## Section 8 — Package Structure

### Controllers
```
com.capillary.intouchapiv3.resources.*           -- v3 controllers
com.capillary.intouchapiv3.resources.v3_1.*      -- v3.1 controllers
com.capillary.intouchapiv3.oauth.controller.*    -- OAuth endpoints
```

**New BenefitCategory controller**: `com.capillary.intouchapiv3.resources.BenefitCategoryController`

### DTOs/Models
- Request/Response DTOs: `com.capillary.intouchapiv3.models.dtos.*` (grouped by domain: `promotion`, `user`, `master`, etc.)
- Model classes: `com.capillary.intouchapiv3.models.entities.*` (JPA entities for MySQL) and `com.capillary.intouchapiv3.unified.promotion.model.*` (MongoDB model)
- **Separate request and response DTOs** in the UnifiedPromotion domain (e.g., `UnifiedPromotionListRequest`, `PromotionReviewRequest`); in simpler controllers the domain object itself is returned directly

**New BenefitCategory DTOs**: `com.capillary.intouchapiv3.models.dtos.loyalty.BenefitCategoryRequest`, `BenefitCategoryResponse`, `BenefitCategorySlabMappingRequest`, `BenefitCategorySlabMappingResponse`

### Services
- Thrift client wrappers: `com.capillary.intouchapiv3.services.thrift.*`
- Facade layer: `com.capillary.intouchapiv3.facades.*` (or directly in `unified.promotion`)
- DAOs: `com.capillary.intouchapiv3.services.daoServices.*`

**New BenefitCategory Thrift client**: `com.capillary.intouchapiv3.services.thrift.BenefitCategoryThriftService`

**New BenefitCategory facade**: `com.capillary.intouchapiv3.facades.BenefitCategoryFacade`

---

## Section 9 — API Versioning

**Confirmed** (C7): URL-path versioning only. No header-based versioning found.

- `@RequestMapping("/v3/...")` — primary API surface (all loyalty entities)
- `@RequestMapping("/v3.1/...")` — connected-org extensions
- No v4 endpoints found.

**For BenefitCategory**: `/v3/benefitCategories` and `/v3/benefitCategorySlabMappings`

---

## Section 10 — Thrift Iface Import / Maven Coordination

### Confirmed Dependency Chain (C7)

**`pom.xml`** lists `thrift-ifaces-pointsengine-rules` as a **Maven artifact dependency**:
```xml
<dependency>
    <groupId>com.capillary.commons</groupId>
    <artifactId>thrift-ifaces-pointsengine-rules</artifactId>
    <version>1.83</version>
</dependency>
```

The Thrift-generated Java classes (`PointsEngineRuleService.Iface`, `ProgramInfo`, `PromotionAndRulesetInfo`, etc.) are consumed via this external JAR — not generated in-place.

### Coordination Requirement Confirmed (C7)
Adding new Thrift methods for BenefitCategory requires ALL of these in sequence:
1. **thrift-ifaces-pointsengine-rules**: Add new IDL structs/methods to `pointsengine_rules.thrift` → build + publish new version (e.g., `1.84`)
2. **emf-parent**: Implement the new methods on existing `PointsEngineRuleConfigThriftImpl` → bump thrift-ifaces dep to 1.84 → build + deploy
3. **intouch-api-v3**: Bump `<version>1.83</version>` → `1.84` in pom.xml, add `BenefitCategoryThriftService.java`, add `BenefitCategoryController.java`

This 3-way coordination is already the pattern for `PointsEngineRuleService` and `EMFService`.

---

## OQ-41 — Thrift Field Naming Convention

Existing callers pass i64 epoch millis as `long lastModifiedOn` to `createOrUpdatePromotionV3`:
```java
PromotionAndRulesetInfo response = getClient().createOrUpdatePromotionV3(
    promotionAndRulesetInfo, programId, orgId, lastModifiedBy, lastModifiedOn, serverRequestId);
```
Bare field names are used (no `_millis` or `_epoch` suffix). **Convention = bare field names** — `createdOn`, `updatedOn` (not `createdOnMillis`). Phase 6 Architect/Phase 7 Designer should follow this.

---

## QUESTIONS FOR USER (New from Phase 5)

| # | Question | Severity | Source |
|---|----------|----------|--------|
| OQ-34 (partially resolved) | Can ANY authenticated Client `TILL`/OAuth caller WRITE BenefitCategory, or must it be restricted to `ADMIN_USER`? The mechanism is clear (`@PreAuthorize` or Zion AZ config). Product decision needed. | HIGH | ResourceAccessAuthorizationFilter pattern |
| OQ-36 (partially resolved) | `NotFoundException` in intouch-api-v3 maps to HTTP 200 (not 404). For `GET /v3/benefitCategories/{id}` where id not found, do we follow this platform convention (200 + error body) or introduce proper 404? | MEDIUM | TargetGroupErrorAdvice line 77 |
| NEW-OQ-44 | No HTTP 409 handler exists in `TargetGroupErrorAdvice`. For D-27 (reactivate → 409) and D-28 (duplicate active name → 409): should we add a new `ConflictException` class + `@ExceptionHandler` for 409? Or downgrade to 400 to match existing platform convention? | HIGH | Gap — 409 not in `TargetGroupErrorAdvice` |
| OQ-38 (confirmed unresolved) | JVM TZ is NOT pinned to UTC in Dockerfile or application.properties. D-24's requirement for explicit UTC conversion is **mandatory**. Is it safe to assume prod JVM TZ is UTC (to determine blast radius of existing date bugs)? Or is IST confirmed? | HIGH | Dockerfile + application.properties |

---

## ASSUMPTIONS

| # | Assumption | Confidence |
|---|------------|------------|
| A-1 | New BenefitCategory Thrift methods will live on the existing `PointsEngineRuleService.Iface` in `thrift-ifaces-pointsengine-rules` (not a new service), following the `BenefitsConfigData` precedent. | C7 — confirmed by thrift-ifaces analysis |
| A-2 | The `RPCService.rpcClient()` in `capillary-commons:1.27` handles connection pooling / multiplexed transport internally. No explicit pool config needed in intouch-api-v3. | C5 — class is in external JAR, not readable here |
| A-3 | `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")` is the correct annotation to produce UTC ISO-8601 on new BenefitCategory DTOs. | C6 — consistent with Jackson docs + `XXX` pattern in existing code |

---

## Files Referenced

| File | Purpose |
|------|---------|
| `/src/main/java/com/capillary/intouchapiv3/resources/MilestoneController.java` | Canonical controller shape — `@RestController`, `/v3/milestones`, `AbstractBaseAuthenticationToken` pattern |
| `/src/main/java/com/capillary/intouchapiv3/resources/UnifiedPromotionController.java` | Full CRUD controller pattern — `@Valid`, `ResponseWrapper`, error mapping |
| `/src/main/java/com/capillary/intouchapiv3/resources/RequestManagementController.java` | MC status-change endpoint pattern |
| `/src/main/java/com/capillary/intouchapiv3/resources/TargetGroupController.java` | GET/POST/PUT pattern with facade delegation |
| `/src/main/java/com/capillary/intouchapiv3/resources/AuthCheckController.java` | `@PreAuthorize("hasRole('ADMIN_USER')")` — only admin-gated endpoint |
| `/src/main/java/com/capillary/intouchapiv3/resources/InternalCustomerController.java` | `/v3/internal/` prefix pattern |
| `/src/main/java/com/capillary/intouchapiv3/models/ResponseWrapper.java` | Full `ResponseWrapper<T>` class — `{data, errors, warnings}` |
| `/src/main/java/com/capillary/intouchapiv3/exceptionResources/TargetGroupErrorAdvice.java` | `@ControllerAdvice` — complete exception→HTTP mapping |
| `/src/main/java/com/capillary/intouchapiv3/auth/IntouchUser.java` | Principal — `{entityId, orgId, entityType, tillName, isKeyBased, clientKey}` |
| `/src/main/java/com/capillary/intouchapiv3/auth/AbstractBaseAuthenticationToken.java` | Token base class — `getIntouchUser()` |
| `/src/main/java/com/capillary/intouchapiv3/auth/filter/BasicAndKeyAuthenticationFilter.java` | `X-CAP-API-AUTH-KEY` + Basic auth flow |
| `/src/main/java/com/capillary/intouchapiv3/auth/filter/KeyOnlyAuthenticationFilter.java` | `X-CAP-API-AUTH-KEY` only flow — GET only |
| `/src/main/java/com/capillary/intouchapiv3/auth/filter/ResourceAccessAuthorizationFilter.java` | Zion AZ filter — `@AuthorizationOverride`, `isKeyBased` bypass |
| `/src/main/java/com/capillary/intouchapiv3/auth/provider/KeyOnlyAuthenticationProvider.java` | `ROLE_KEY_USER` assignment |
| `/src/main/java/com/capillary/intouchapiv3/auth/provider/BasicAndKeyAuthenticationProvider.java` | `ROLE_<entityType>` assignment |
| `/src/main/java/com/capillary/intouchapiv3/auth/service/impl/IntouchAuthenticationServiceImpl.java` | GET-only enforcement for KeyOnly; `yyyy-MM-dd'T'HH:mm:ss.SSSZ` date format in auth |
| `/src/main/java/com/capillary/intouchapiv3/config/HttpSecurityConfig.java` | Filter chain — `BasicAndKey`, `KeyOnly`, `IntegrationsClient` order; all `/**` authenticated |
| `/src/main/java/com/capillary/intouchapiv3/services/thrift/PointsEngineRulesThriftService.java` | Canonical Thrift client pattern — `RPCService.rpcClient(Iface, "emf-thrift-service", 9199, timeout)` |
| `/src/main/java/com/capillary/intouchapiv3/services/thrift/EmfDataManagerThriftService.java` | Minimal Thrift client example — port 9199, 10s timeout |
| `/src/main/java/com/capillary/intouchapiv3/services/thrift/EmfPromotionThriftService.java` | EMFService Thrift client — same port/pattern |
| `/src/main/java/com/capillary/intouchapiv3/services/thrift/exception/EMFThriftException.java` | `EMFThriftException extends RuntimeException` — wraps Thrift failures |
| `/src/main/java/com/capillary/intouchapiv3/unified/promotion/enums/PromotionStatus.java` | MC lifecycle states: `DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, STOPPED` |
| `/src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotion.java` | MongoDB `@Document` — MC-capable entity model |
| `/src/main/java/com/capillary/intouchapiv3/utils/TimeZoneUtil.java` | `ZoneId.systemDefault()` — JVM-TZ dependent, no UTC pin |
| `/src/main/java/com/capillary/intouchapiv3/validators/FutureOrPresentDate.java` | Custom validator annotation pattern |
| `/src/main/resources/application.properties` | No `spring.jackson.*` properties — no global Jackson date config |
| `Dockerfile` | No `-Duser.timezone=UTC` — JVM TZ unconfirmed |
| `pom.xml` | `thrift-ifaces-pointsengine-rules:1.83` as Maven dep — version bump required for new IDL |

---

**Summary**: Complete code analysis of intouch-api-v3 delivered. Key findings: (1) Thrift client via `RPCService.rpcClient(Iface, "emf-thrift-service", 9199, timeout)` with `EMFThriftException` wrapping; (2) `ResponseWrapper<T>{data, errors, warnings}` is the universal envelope; (3) HTTP 409 Conflict is NOT handled and must be added for D-27/D-28; (4) NotFoundException maps to HTTP 200 (platform quirk); (5) `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` is the field-level pattern (not UTC-pinned — must add `timezone="UTC"` for BenefitCategory DTOs); (6) JVM TZ is NOT pinned to UTC anywhere in this repo; (7) OQ-34 authz mechanism confirmed (KeyOnly=GET-only, writes require BasicAndKey or OAuth), but product must decide admin-only vs. any-authenticated-caller.
