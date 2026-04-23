# Phase 11 Review — Loyalty Extended Fields CRUD (CAP-183124)
> Reviewer: Phase 11 (AIDLC pipeline)
> Date: 2026-04-23
> Feature: Loyalty Extended Fields CRUD
> Ticket: CAP-183124
> Status: Complete — 2 blockers identified

---

## Section 1: Build Verification

Build verification was performed externally prior to this review phase. Results as reported:

| Step | Command | Result |
|------|---------|--------|
| Compilation | `mvn compile` from `emf-parent` root | PASS — BUILD SUCCESS |
| Unit Tests | `mvn test -pl pointsengine-emf-ut -am` | PASS — 13 tests, 0 failures, 0 errors |
| Integration Tests | n/a — no ITs found for this feature | SKIPPED |

**Test class confirmed**: `LoyaltyExtendedFieldServiceImplTest.java` — 13 test methods, all passing.

**Build-fix cycles consumed**: 3/3
1. Circular dependency — `LoyaltyExtendedFieldService` interface moved from `pointsengine-emf` to `emf/api/service`
2. `EMFException` import corrected from `emf.api.exception` to `emf.api.external` (Thrift-generated class)
3. JDK 8 compatibility — `Set.of()`/`PageRequest.of()` replaced; JUnit 5 assertions replaced with JUnit 4; stale `InfoLookupService` mock removed

---

## Section 2: Requirements Traceability Matrix

### Epic 1 — EF Config Registry CRUD

| Req ID | Requirement | Implementation Evidence | Status | Confidence |
|--------|-------------|------------------------|--------|-----------|
| EF-US-01 | `POST /v3/extendedfields/config` creates EF config row | `LoyaltyExtendedFieldController.java:44` — `@PostMapping`; `LoyaltyExtendedFieldServiceImpl.create()` persists entity via `LoyaltyExtendedFieldRepository.save()` | PASS | C7 |
| EF-US-01 | (orgId, scope, name) uniqueness — 409 on duplicate | `LoyaltyExtendedFieldServiceImpl.java:101-105` — `existsByPkOrgIdAndProgramIdAndScopeAndName()` before save → throws `EMFException(8002)` | PASS | C7 |
| EF-US-01 | Invalid scope → 400 (8004) | `LoyaltyExtendedFieldServiceImpl.java:81-84` — `ALLOWED_SCOPES` check → `EMFException(EF_CONFIG_INVALID_SCOPE)` | PASS | C7 |
| EF-US-01 | Invalid data_type → 400 (8005) | `LoyaltyExtendedFieldServiceImpl.java:87-90` — `ALLOWED_DATA_TYPES` check → `EMFException(EF_CONFIG_INVALID_DATA_TYPE)` | PASS | C7 |
| EF-US-01 | `status` defaults to active | `LoyaltyExtendedField.java:44` — `boolean isActive = true` default | PASS | C7 |
| EF-US-01 | Returns created EF with `id` | `LoyaltyExtendedFieldServiceImpl.java:126-127` — `toThriftStruct(saved)` maps entity to `LoyaltyExtendedFieldConfig` including `id` | PASS | C7 |
| EF-US-01 | UTC timestamps populated | `LoyaltyExtendedFieldServiceImpl.java:108` — `Instant.now()` used; `toIsoUtc()` formats as ISO-8601 UTC string | PASS | C7 |
| EF-US-02 | `PUT /v3/extendedfields/config/{id}` — only `name` and `is_active` mutable | `UpdateExtendedFieldRequest.java` contains only `name` and `isActive`; no scope/dataType/isMandatory/defaultValue fields (D-23) | PASS | C7 |
| EF-US-02 | Name uniqueness re-validated on rename (excluding self) | `LoyaltyExtendedFieldServiceImpl.java:152-158` — checks `existsByPkOrgIdAnd…` only when new name != old name | PASS | C7 |
| EF-US-02 | `is_active=false` performs soft-delete | `LoyaltyExtendedFieldServiceImpl.java:162-164` — `entity.setActive(request.isIsActive())` | PASS | C7 |
| EF-US-02 | `is_active=false` on already-inactive → 200 (idempotent, D-16) | Same code path — sets the same value and saves without error check | PASS | C7 |
| EF-US-02 | Non-existent id/wrong org → 404 (8001) | `LoyaltyExtendedFieldServiceImpl.java:141-146` — `findByPkIdAndPkOrgId()` returns empty → `EMFException(8001)` | PASS | C7 |
| EF-US-02 | `last_updated_on` updated on successful PUT | `LoyaltyExtendedFieldServiceImpl.java:168` — `entity.setUpdatedOn(Instant.now())` | PASS | C7 |
| EF-US-03 | `GET /v3/extendedfields/config` returns paginated list for org | `LoyaltyExtendedFieldController.java:80` `@GetMapping`; `findByOrgIdAndProgramIdDynamic()` with pagination | PASS | C7 |
| EF-US-03 | `?scope=SUBSCRIPTION_META` filter | `LoyaltyExtendedFieldRepository.java:67` — `(:scope IS NULL OR ef.scope = :scope)` in JPQL | PASS | C7 |
| EF-US-03 | `?includeInactive=false` default | `LoyaltyExtendedFieldRepository.java:68` — `(:includeInactive = true OR ef.isActive = true)` in JPQL | PASS | C7 |
| EF-US-03 | Empty result → 200 not 404 | `list()` returns `LoyaltyExtendedFieldListResponse` with empty `configs` list; no 404 logic | PASS | C7 |

### Epic 2 — EF Validation on Subscription Programs

| Req ID | Requirement | Implementation Evidence | Status | Confidence |
|--------|-------------|------------------------|--------|-----------|
| EF-US-05 | EF validation fires on `POST /v3/subscriptions` when extendedFields provided | `SubscriptionFacade.java:90-92` — validator called when `extendedFields != null && !isEmpty()` | PASS | C7 |
| EF-US-05 | `efId` must match active EF config (R-01) | `ExtendedFieldValidator.java:73-79` — configMap lookup by efId; throws `EF_VALIDATION_001` | PASS | C7 |
| EF-US-05 | Value data type validated (R-02) | `ExtendedFieldValidator.java:82-90` — `matchesDataType()` for STRING/NUMBER/BOOLEAN/DATE | PASS | C7 |
| EF-US-05 | All mandatory EF configs must be present (R-03) | `ExtendedFieldValidator.java:99-107` — mandatory configs checked against submitted efIds | PASS | C7 |
| EF-US-05 | **extendedFields=null with mandatory configs → 400** | `SubscriptionFacade.java:90` — condition is `!= null && !isEmpty()`. **NULL extendedFields SKIPS validation entirely.** Mandatory field enforcement is bypassed when extendedFields is omitted. Contradicts AC for EF-US-05 ("If extendedFields is null or omitted AND mandatory fields exist → 400") and TC-EF-05-03. | **FAIL** | C7 |
| EF-US-05 | Cross-tenant efId rejected (TC-EF-05-12) | Validator fetches configs for caller's `(orgId, programId)` — cross-org efId absent from configMap → EF_VALIDATION_001 | PASS | C7 |
| EF-US-06 | EF validation fires on `PUT /v3/subscriptions/{id}` when extendedFields non-null | `SubscriptionFacade.java:299-302` — validates when `extendedFields != null && programId != null` | PASS | C7 |
| EF-US-06 | `extendedFields=null` on PUT preserves existing values (R-33) | `SubscriptionFacade.java:299` — `if (request.getExtendedFields() != null && ...)` guard preserves existing | PASS | C7 |
| EF-US-06 | `extendedFields=[]` on PUT clears all EF values (explicit clear) | Empty list passes the `!= null` guard; validate() receives empty list; R-03 mandatory check runs; then `setExtendedFields([])` clears the field | PARTIAL | C5 |

Note on EF-US-06 empty list: if mandatory EF configs exist, submitting `[]` on PUT will trigger R-03 (missing mandatory) and return 400. The "clear all" behavior (TC-EF-06-02) only works when no mandatory configs are defined — which may not match product intent. This is a side effect of the same null/empty guard logic.

### Epic 3 — Model Correction

| Req ID | Requirement | Implementation Evidence | Status | Confidence |
|--------|-------------|------------------------|--------|-----------|
| EF-US-07 | `ExtendedFieldType` enum deleted | `enums/ExtendedFieldType.java` confirmed deleted per `06-developer.md`; no reference in `SubscriptionProgram.java` | PASS | C6 |
| EF-US-07 | `type` field removed from `SubscriptionProgram.ExtendedField` | `SubscriptionProgram.java:295-315` — no `type` field; `@ExtendedFieldType` import absent | PASS | C7 |
| EF-US-07 | `efId: Long` added to `SubscriptionProgram.ExtendedField` | `SubscriptionProgram.java:305` — `private Long efId;` confirmed | PASS | C7 |
| EF-US-07 | `key: String` kept in `ExtendedField` | `SubscriptionProgram.java` — `private String key` and `private String value` retained | PASS | C7 |
| EF-US-07 | Old MongoDB documents `{type,key,value}` deserialize with `efId=null` | No `@NotNull` on `efId`; additive field — Jackson deserializes to null gracefully (ADR-03) | PASS | C6 |

### Summary Counts

| Category | Count |
|----------|-------|
| Total requirements traced | 27 |
| PASS | 24 |
| FAIL | 1 |
| PARTIAL | 1 |
| Gaps routed to | Developer (Phase 10) |

---

## Section 3: Code Review

### 3.1 Architecture & Design Compliance

**emf-parent — LoyaltyExtendedFieldService interface** (`emf/src/main/java/com/capillary/shopbook/emf/api/service/LoyaltyExtendedFieldService.java`)

PASS (C7): Interface is in the correct module (`emf/api/service`) after the circular-dependency fix. Three methods (`create`, `update`, `list`) match the Thrift service method signatures exactly. Javadoc documents all thrown exception codes. Pattern consistent with other service interfaces in `emf/api/service`.

**emf-parent — LoyaltyExtendedFieldServiceImpl** (`pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/LoyaltyExtendedFieldServiceImpl.java`)

- PASS (C7): `@Service @DataSourceSpecification(WAREHOUSE) @Transactional(value="warehouse", REQUIRED)` annotations correct per codebase pattern.
- PASS (C7): All CRUD operations include `orgId` in every DB query — G-07.1 compliant.
- PASS (C7): Name uniqueness check D-30 correctly uses `existsByPkOrgIdAndProgramIdAndScopeAndName()` regardless of `is_active` value.
- PASS (C7): `validateOrgId()` throws `EMFException(8010)` for `orgId <= 0` — R-CT-05 mitigation in place.
- PASS (C7): `java.time.Instant` used for all timestamps; `DateTimeFormatter.withZone(ZoneOffset.UTC)` ensures UTC formatting — G-01.1 compliant.
- PASS (C7): Soft-delete idempotency (D-16) — `setActive(false)` on already-inactive entity simply saves the same value, returns 200.
- NOTE (C7): `resolveMaxEfCount()` is a hardcoded stub returning `DEFAULT_MAX_EF_COUNT=10`. Per 06-developer.md, this is intentional — the `program_config_key_values` lookup is deferred. The stub is documented with a `// Future:` comment. Importantly, the stale `InfoLookupService` injection was removed during build-fix cycle 3, so no dead injection remains.

**Non-blocking finding — EF_CONFIG_INVALID_INPUT (8011) error code usage in `create()`** (C7):
- `programId <= 0` at line 71 throws `EF_CONFIG_INVALID_INPUT` (8011)
- Blank `name` at line 75 throws `EF_CONFIG_INVALID_INPUT` (8011)

The backend-readiness phase (FAIL 2) identified these as throwing wrong codes. The current code in the reviewed file uses `EF_CONFIG_INVALID_INPUT` (8011) for both — which was the fix applied during build. Code 8011 is included in `badRequestErrors` set (`ExceptionCodes.java:31`), so the HTTP status mapping is correct (→ 400). The semantic clarity is adequate: "invalid input" is a reasonable umbrella for programId and name validation failures at this layer. This is a non-blocking improvement opportunity.

**emf-parent — LoyaltyExtendedField entity** (`pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/LoyaltyExtendedField.java`)

- PASS (C7): `@Entity @Table(name="loyalty_extended_fields", schema="warehouse")` matches schema SQL filename and database ownership.
- PASS (C7): `@EmbeddedId LoyaltyExtendedFieldPK pk` composite PK correctly implemented.
- PASS (C7): `java.time.Instant` used for `createdOn` and `updatedOn` — G-01.1 compliant. (The backend-readiness FAIL 1 regarding `java.util.Date` was fixed during the build-fix cycles; the reviewed file uses `Instant`.)
- PASS (C7): `@Column(name="created_on", updatable=false)` prevents accidental overwrite of creation timestamp.
- PASS (C7): Builder inner class implemented correctly; all fields covered.
- PASS (C7): `implements Serializable` with `serialVersionUID` — required for JPA `@Embeddable` PK classes.

**emf-parent — LoyaltyExtendedFieldRepository** (`pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/LoyaltyExtendedFieldRepository.java`)

- PASS (C7): `extends GenericDao<LoyaltyExtendedField, LoyaltyExtendedFieldPK>` follows codebase DAO pattern.
- PASS (C7): `@Repository @Transactional(value="warehouse", SUPPORTS)` correct.
- PASS (C7): `findByPkIdAndPkOrgId(Long id, Long orgId)` — multi-tenancy enforced; cross-org read impossible.
- PASS (C7): `existsByPkOrgIdAndProgramIdAndScopeAndName()` — uniqueness check includes all 4 columns per D-30.
- PASS (C7): Dynamic JPQL query uses `@Param`-bound parameters exclusively — no string concatenation, no SQL injection risk (G-03).
- PASS (C7): `(:scope IS NULL OR ef.scope = :scope)` and `(:includeInactive = true OR ef.isActive = true)` — correct JPQL dynamic filter pattern.
- PASS (C7): `countActiveByOrgIdAndProgramId` counts only `isActive = true` — correctly excludes inactive from MAX_EF_COUNT limit.

**emf-parent — EMFThriftServiceImpl additions** (`emf/src/main/java/com/capillary/shopbook/emf/impl/external/EMFThriftServiceImpl.java:4272-4347`)

- PASS (C7): Three `@Override` methods for Thrift interface methods 58, 59, 60 with correct signatures.
- PASS (C7): `@MDCData` annotations for distributed tracing on each method.
- PASS (C7): `request == null` guard before delegation — prevents NPE for null Thrift requests.
- PASS (C7): Dual catch: `catch (EMFException ex) { throw ex; }` re-throws domain exceptions without wrapping; `catch (Exception ex)` wraps unexpected exceptions as `getEMFException(GENERIC, ...)`.
- PASS (C7): Fully-qualified `@org.springframework.beans.factory.annotation.Autowired` on `loyaltyExtendedFieldService` field — avoids import conflicts in the 4,272-line file.
- NOTE (C5): `@Trace(dispatcher=true)` annotation absent from the three new methods. The architect/designer phases specified this annotation for APM tracing. Existing EMF methods use it. Non-blocking but reduces observability.

**emf-parent — ExceptionCodes.java**

- PASS (C7): Error codes 8001–8011 added in sequence; code range confirmed free (highest prior code: 7007).
- PASS (C7): `badRequestErrors` set updated to include 8002–8011 (8001 omitted — maps to 404 via V3 advice).
- PASS (C7): New constant `EF_CONFIG_INVALID_INPUT = 8011` added correctly, included in `badRequestErrors`.
- NOTE (C7): The backend-readiness report identified that 8001 (`EF_CONFIG_NOT_FOUND`) is not in `badRequestErrors` — this is intentional and correct. The 404 mapping for 8001 is handled in `LoyaltyExtendedFieldErrorAdvice` in V3, not by `getHttpStatusCode()`.

### 3.2 intouch-api-v3 Code Review

**ExtendedFieldValidator** (`unified/subscription/extendedfields/ExtendedFieldValidator.java`)

- PASS (C7): Single Thrift call fetches all active configs (ADR-08/A-05) — O(1) network, O(N) in-memory where N≤10.
- PASS (C7): `R-01`, `R-02`, `R-03` validation in correct sequence per architect design.
- PASS (C7): `matchesDataType()` correctly handles STRING (always true), NUMBER (BigDecimal parse), BOOLEAN ("true"/"false" case-insensitive), DATE (ISO-8601 `yyyy-MM-dd` via `LocalDate.parse()`), unknown type (returns false — fail-safe).
- PASS (C7): Race condition (C-4) documented in class Javadoc — fail-open on snapshot is intentional and accepted.

**Non-blocking finding — `Map.of()` in ExtendedFieldValidator (C7)**:
`ExtendedFieldValidator.java:63` uses `Map.of()` which is a Java 9+ API. However, `intouch-api-v3/pom.xml` declares `<source>17</source> <target>17</target>` (Java 17 compilation target). This is NOT a JDK 8 compatibility issue for this repo — the build passed. `Map.of()` is valid here.

**SubscriptionFacade.java modifications**

- PASS (C7): `@Autowired ExtendedFieldValidator extendedFieldValidator` correctly injected.
- PASS (C7): Validation fires before MongoDB `repository.save()` at both create (line 91) and update (line 301).
- PASS (C7): Fork (line 357) and duplicate (line 399) copy EF ids without re-validation per OQ-9 decision.
- PASS (C7): Update path null-guard: `if (extendedFields != null && programId != null)` — preserves existing values when null (R-33).

**BLOCKER — Mandatory EF enforcement bypassed when `extendedFields` is null on create** (C7):

`SubscriptionFacade.java:90`:
```java
if (programId != null && request.getExtendedFields() != null && !request.getExtendedFields().isEmpty()) {
    extendedFieldValidator.validate(orgId, programId, request.getExtendedFields());
}
```

When a caller omits `extendedFields` entirely (null), this condition is false and `validate()` is never called. The validator's R-03 mandatory check is therefore never executed. This means:
- A subscription can be created without providing mandatory EF values if the caller simply omits the `extendedFields` field.
- TC-EF-05-03 expects HTTP 400 when `extendedFields=null` and mandatory configs exist — this test will fail.
- AC for EF-US-05 states: "If `extendedFields` is `null` or omitted AND mandatory fields exist → `400`."

**Fix required**: The mandatory field check must run even when `extendedFields` is null. The validator needs to be called to at least check R-03 when mandatory configs exist. One correct approach:

```java
// Always validate when programId is known (mandatory check may apply even with null/empty EF list)
if (programId != null) {
    List<SubscriptionProgram.ExtendedField> efs =
        request.getExtendedFields() != null ? request.getExtendedFields() : Collections.emptyList();
    extendedFieldValidator.validate(orgId, programId, efs);
}
```

And in `ExtendedFieldValidator.validate()`, remove the null/empty short-circuit guard, or move it to only skip R-01/R-02 (not R-03) when the submitted list is empty.

**SubscriptionErrorAdvice.java modifications**

- PASS (C7): `@ExceptionHandler(ExtendedFieldValidationException.class)` handler added at line 77.
- PASS (C7): Returns `ResponseEntity<EFErrorResponse>` with error code and field path.

### 3.3 Guardrail Checks

| Guardrail | Check | Result | Evidence |
|-----------|-------|--------|----------|
| G-01 — No `java.util.Date` in new code | `LoyaltyExtendedField`, `LoyaltyExtendedFieldServiceImpl` | PASS | Both use `java.time.Instant`; `SubscriptionFacade` uses `new Date()` but that is pre-existing code not added by this feature |
| G-03 — SQL injection | JPQL `@Query` uses `@Param`-bound parameters; no string concatenation | PASS | `LoyaltyExtendedFieldRepository.java:64-75` |
| G-07 — Tenant isolation | `orgId` extracted from auth token in all 3 controller methods; every DB query includes `orgId` filter; `findByPkIdAndPkOrgId` prevents cross-org fetch | PASS | `LoyaltyExtendedFieldController.java:49,68,89`; `LoyaltyExtendedFieldRepository.java:33,41,47,54,65` |
| G-12 — No hallucinated APIs | All method calls verified against actual source (Thrift-generated class methods, Spring Data derived queries) | PASS | Compiler confirms — BUILD SUCCESS |

### 3.4 Additional Non-Blocking Findings

**NB-01 — `@Trace(dispatcher=true)` absent from new EMFThriftServiceImpl methods** (C5)

The architect phase and existing EMF method patterns include `@Trace(dispatcher=true)` for APM instrumentation (e.g., DataDog). The three new EF methods (createLoyaltyExtendedFieldConfig, updateLoyaltyExtendedFieldConfig, getLoyaltyExtendedFieldConfigs) only have `@Override` and `@MDCData`. Without `@Trace`, these methods will not appear as distinct spans in APM traces.

Recommendation: Add `@Trace(dispatcher=true)` to each of the three new methods before production deployment.

**NB-02 — `resolveMaxEfCount()` hardcoded stub** (C6)

`LoyaltyExtendedFieldServiceImpl.java:247-249` always returns 10. While the stub is documented and the `InfoLookupService` injection was removed (correct), the feature's D-15 requirement for org/program-level override via `program_config_key_values` is not implemented. The seed data for `MAX_EF_COUNT_PER_PROGRAM` (ID=48) was added to cc-stack-crm but is never consulted.

Status: Accepted as deferred per 06-developer.md. Must be tracked as a follow-up story before allowing orgs to configure custom limits.

**NB-03 — `UpdateExtendedFieldRequest` missing JSR-303 validation for `name` length** (C4)

`CreateExtendedFieldRequest` has `@Size(max=100)` on `name`. `UpdateExtendedFieldRequest` has no length constraint on its optional `name` field. A name longer than 100 chars would pass V3 validation, travel through Thrift, and fail at the DB `VARCHAR(100)` constraint — surfacing as an unhandled `DataIntegrityViolationException` rather than a clean 400.

Recommendation: Add `@Size(max=100)` to `UpdateExtendedFieldRequest.name`.

**NB-04 — Error response format diverges from V3 convention** (C6)

`LoyaltyExtendedFieldErrorAdvice` returns `EFErrorResponse {code:String, message:String, field:String}` while all other V3 error advice returns `ResponseWrapper<String>`. This is intentional (EFErrorResponse adds a `field` path for detailed client error handling) but is inconsistent with the V3 API envelope. The UI team and API consumers must be informed of this divergence via the api-handoff artifact.

**NB-05 — `getHttpStatusCode()` in `ExceptionCodes` does not handle 8001 → 404** (C6)

`ExceptionCodes.getHttpStatusCode(8001)` falls through to the default `return HTTP_BAD_REQUEST_ERROR_CODE` (400) because 8001 is not in `badRequestErrors`. The 404 mapping relies entirely on `LoyaltyExtendedFieldErrorAdvice` reading `EMFThriftException.statusCode`. This is architecturally correct for V3-consumed errors, but if any other consumer calls `getHttpStatusCode(8001)` directly, they will receive 400 instead of 404. Low risk given 8001 is domain-specific, but document this as known behavior.

**NB-06 — `ExtendedFieldValidator` empty list and mandatory configs on subscription UPDATE** (C4)

When `extendedFields=[]` is submitted on PUT (TC-EF-06-02, explicit clear intent), `validate()` is called with an empty list. R-03 then checks all mandatory configs and throws `EF_VALIDATION_MISSING_MANDATORY` (8008) if any exist. This means it is impossible to clear `extendedFields` when mandatory configs are defined — the "explicit empty = clear" semantic (per BA and QA) is broken in the presence of mandatory fields.

Root cause: the same mandatory-check logic runs regardless of whether the caller intends to preserve vs clear. This requires product clarification on whether `extendedFields=[]` should bypass R-03 (special "clear" intent) or be treated as a normal validation pass.

---

## Section 4: BLOCKER Summary

### BLOCKER-R01 — Mandatory EF enforcement bypassed when `extendedFields` is null on subscription CREATE

**Severity**: HIGH  
**File**: `SubscriptionFacade.java:90`  
**Impact**: Subscription can be created without mandatory EF values by omitting the `extendedFields` field. Violates EF-US-05 AC, TC-EF-05-03 will fail.  
**Fix**: Separate null/empty EF validation from mandatory-field check. Always invoke validator for mandatory check; use empty list when `extendedFields` is null.

### BLOCKER-R02 — `extendedFields=[]` on PUT fails when mandatory configs exist (product spec ambiguity)

**Severity**: MEDIUM  
**File**: `ExtendedFieldValidator.java:99-107`, `SubscriptionFacade.java:299`  
**Impact**: TC-EF-06-02 ("empty list on PUT clears all EF values") fails when mandatory EF configs are defined — R-03 throws 8008. Product intent must be clarified: does `extendedFields=[]` bypass R-03 mandatory check as a "clear" signal?  
**Fix options**:
1. Treat `extendedFields=[]` on PUT as a "clear" signal — skip R-03 entirely; only run R-01/R-02 on submitted items (vacuously true for empty list).
2. Require product sign-off that "empty list clears" is only allowed when no mandatory configs exist (document as constraint).

---

## Section 5: Non-Blocking Findings Summary

| # | Finding | Severity | Recommendation |
|---|---------|----------|----------------|
| NB-01 | `@Trace(dispatcher=true)` absent from 3 new EMFThriftServiceImpl methods | Low | Add before production — improves APM observability |
| NB-02 | `resolveMaxEfCount()` hardcoded; `program_config_key_values` lookup not implemented | Medium | Track as follow-up story; seed data exists but unused |
| NB-03 | `UpdateExtendedFieldRequest.name` missing `@Size(max=100)` | Low | Add JSR-303 annotation to prevent DB constraint violation |
| NB-04 | EFErrorResponse format diverges from V3 ResponseWrapper convention | Info | Document in api-handoff artifact for UI team |
| NB-05 | `getHttpStatusCode(8001)` returns 400 not 404 in ExceptionCodes | Low | Document as known; V3 advice handles it correctly |
| NB-06 | `extendedFields=[]` on PUT fails R-03 when mandatory configs exist | Medium | Product clarification needed; then fix validator or document constraint |

---

*Phase 11 Reviewer — CAP-183124 — 2026-04-23*
