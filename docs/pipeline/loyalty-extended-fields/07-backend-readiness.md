# Backend Readiness Report — CAP-183124
> Date: 2026-04-22 | Phase: 10b

## Summary
PASS: 17 checks | WARN: 3 | FAIL: 2

---

## Results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1.1 | Every DAO query includes `org_id` in WHERE clause | PASS | `findByPkIdAndPkOrgId`, `existsByPkOrgIdAnd…`, `findByPkOrgIdAnd…`, `countActiveByOrgIdAnd…`, `findByOrgIdAndProgramIdDynamic` all bind `orgId` via `ef.pk.orgId = :orgId`. LoyaltyExtendedFieldRepository.java:33-75 |
| 1.2 | No query returns rows from a different org | PASS | Composite PK enforces (id, orgId) lookup; paginated query has hard `ef.pk.orgId = :orgId` filter. LoyaltyExtendedFieldRepository.java:64-75 |
| 1.3 | JPQL `@Query` for list endpoint correct (params bound, no injection risk) | PASS | All four params bound with `@Param`; no string concatenation in JPQL. LoyaltyExtendedFieldRepository.java:64-75 |
| 2.1 | Thrift field numbers sequential, no gaps or duplicates | PASS | `LoyaltyExtendedFieldConfig` 1-12, `CreateLoyaltyExtendedFieldRequest` 1-8, `UpdateLoyaltyExtendedFieldRequest` 1-5, `LoyaltyExtendedFieldListResponse` 1-4, service methods 1-6. emf.thrift:1542-1594 |
| 2.2 | `required` used only on response struct non-nullable fields | PASS | `LoyaltyExtendedFieldConfig`: 10 required (non-nullable DB cols), 2 optional (defaultValue, updatedBy). emf.thrift:1542-1554 |
| 2.3 | Request struct fields — ADR-01 deviation | WARN | ADR-01 explicitly permits `required` on orgId/programId/name/scope/dataType in `CreateLoyaltyExtendedFieldRequest` to prevent zero-default bypass. Residual risk noted in session-memory open questions: Thrift `required` missing field = protocol exception, not business exception. emf.thrift:1561-1569 |
| 2.4 | `LoyaltyExtendedFieldListResponse` includes pagination fields | PASS | `totalElements`, `page`, `size` all present. emf.thrift:1590-1594 |
| 2.5 | All 3 new EMFThriftServiceImpl methods have `@Override` + try-catch + delegate | PASS | `@Override` at lines 4282, 4305, 4329. Each has try-catch(EMFException) re-throw + catch(Exception) wrapped in `getEMFException(GENERIC, …)`. EMFThriftServiceImpl.java:4282-4345 |
| 3.1 | `ServiceImpl` implements every method in interface | PASS | Interface declares `create`, `update`, `list`; all three `@Override` present. LoyaltyExtendedFieldServiceImpl.java:64,129,177 |
| 3.2 | Method signatures identical (return type, params, throws) | PASS | Return types and throws clause match exactly between interface and impl. LoyaltyExtendedFieldService.java:25,36,45 vs LoyaltyExtendedFieldServiceImpl.java:65,129,177 |
| 3.3 | All 3 endpoints present in controller (POST, PUT /{id}, GET) | PASS | `@PostMapping`, `@PutMapping("/{id}")`, `@GetMapping` all present. LoyaltyExtendedFieldController.java:44,62,80 |
| 3.4 | orgId extracted from `token.getIntouchUser().getOrgId()` — never from body | PASS | All three controller methods call `token.getIntouchUser()` and pass `user.getOrgId()` to facade. LoyaltyExtendedFieldController.java:49,68,89 |
| 4.1 | All 8001-8009 error codes mapped to HTTP status codes | WARN | Codes 8001-8005, 8009, 8010 are mapped (7 codes). Codes **8006, 8007, 8008** (EF_VALIDATION_UNKNOWN_ID, TYPE_MISMATCH, MISSING_MANDATORY) are **NOT mapped** in `LoyaltyExtendedFieldErrorAdvice`. These validation codes are thrown from `ExtendedFieldValidator` as `ExtendedFieldValidationException` (not `EFThriftException`), so they flow through `SubscriptionErrorAdvice` instead — but this means no handler exists in `LoyaltyExtendedFieldErrorAdvice` for them. If validation errors somehow surface via the EF Config endpoints they will hit the `default → 500` branch. LoyaltyExtendedFieldErrorAdvice.java:44-63, ExceptionCodes.java:258-264 |
| 4.2 | 8001 mapped to 404 | PASS | `case 8001: return error(NOT_FOUND, …)`. LoyaltyExtendedFieldErrorAdvice.java:45-46 |
| 4.3 | Response body format consistent with existing V3 error format | WARN | `LoyaltyExtendedFieldErrorAdvice` returns `EFErrorResponse {code:String, message:String, field:String}`. Existing `SubscriptionErrorAdvice` returns `ResponseWrapper<String>` with `ApiError(Long code, String message)`. The formats are intentionally different (EFErrorResponse adds `field` for JSON path). This is documented in EFErrorResponse.java:9 but deviates from the V3 norm. UI team must be informed. EFErrorResponse.java:12-17, SubscriptionErrorAdvice.java:89-90 |
| 4.4 | Null request inputs guarded before NPE | PASS | `validateOrgId(request.getOrgId())` is first call in `create()` and `update()`; EMFThriftServiceImpl also guards `request == null` at lines 4286-4289, 4309-4312. LoyaltyExtendedFieldServiceImpl.java:69,133 |
| 4.5 | `orgId=0` treated as invalid (server-side null-guard) | PASS | `validateOrgId` throws EMFException(8010) when `orgId <= 0`. LoyaltyExtendedFieldServiceImpl.java:238-241 |
| 5.1 | `createLoyaltyExtendedFieldConfig` sets orgId from Thrift request (V3 populated from auth token) | PASS | Facade sets `thriftReq.setOrgId(orgId)` from auth token. LoyaltyExtendedFieldFacade.java:41 |
| 5.2 | `updateLoyaltyExtendedFieldConfig` fetches by `(id, orgId)` — cross-org update impossible | PASS | `repository.findByPkIdAndPkOrgId(request.getId(), request.getOrgId())`. LoyaltyExtendedFieldServiceImpl.java:141 |
| 5.3 | `getLoyaltyExtendedFieldConfigs` always filters by orgId | PASS | JPQL query has `ef.pk.orgId = :orgId` as mandatory filter. LoyaltyExtendedFieldRepository.java:65 |
| 6.1 | `java.util.Date` / `new Date()` in new code | FAIL | `LoyaltyExtendedFieldServiceImpl` imports `java.util.Date` (line 23) and calls `new Date()` at lines 107 and 167. Entity `LoyaltyExtendedField` also uses `java.util.Date` (line 10) with `@Temporal(TIMESTAMP)`. G-01.1 requires `java.time` types. Should use `Instant` or `LocalDateTime`. LoyaltyExtendedFieldServiceImpl.java:23,107,167; LoyaltyExtendedField.java:10,50,54 |
| 6.2 | `createdOn`/`updatedOn` in entity using `java.time` types | FAIL | Entity uses `java.util.Date` with `@Temporal(TemporalType.TIMESTAMP)` — NOT `java.time.Instant`. LoyaltyExtendedField.java:50-54 |
| 7.1 | Count-before-insert check present | PASS | `repository.countActiveByOrgIdAndProgramId(…)` called before save. LoyaltyExtendedFieldServiceImpl.java:93-97 |
| 7.2 | Falls back to default 10 if no per-program config entry | WARN | `resolveMaxEfCount` always returns `DEFAULT_MAX_EF_COUNT = 10`. It does NOT read from `program_config_key_values` (key_id=48, D-15). The stub comment says "Future: read from program_config_key_values" — this means the config infrastructure wired by the architect is never actually consulted. Per session memory D-15, this is acceptable for first release, but the `infoLookupService` is injected and unused. LoyaltyExtendedFieldServiceImpl.java:57-58,250-252 |
| 8.1 | Soft-delete idempotency: already-inactive → 200 without error | PASS | `if (request.isSetIsActive()) { entity.setActive(request.isIsActive()); }` — no guard against already-inactive; just sets the same value and saves. Returns 200. LoyaltyExtendedFieldServiceImpl.java:162-164 |
| 9.1 | Immutable fields absent from `UpdateExtendedFieldRequest` DTO | PASS | `UpdateExtendedFieldRequest` contains only `name: String` and `isActive: Boolean`. `scope`, `dataType`, `isMandatory`, `defaultValue` are absent. UpdateExtendedFieldRequest.java:14-21 |
| 10.1 | `extendedFieldValidator.validate()` called BEFORE MongoDB builder/save | PASS | Validate called at line 91 (create) and 301 (update), both before `repository.save(entity)`. SubscriptionFacade.java:91,301 |
| 10.2 | Null-guard: validate only when `extendedFields != null` (null = preserve per R-33) | PASS | Create: `!= null && !isEmpty()` at line 90. Update: `!= null` at line 299. SubscriptionFacade.java:90,299 |
| 10.3 | Fork/duplicate lines ~343 and ~385 untouched | PASS | Both fork (line 357) and duplicate (line 399) copy `extendedFields` as-is with null-coalesce to `List.of()`. No validator call. SubscriptionFacade.java:357,399 |

---

## Failures (must fix before Phase 11)

### FAIL 1 — `java.util.Date` used instead of `java.time` types (G-01.1, G-01.3)
**Files**:
- `LoyaltyExtendedFieldServiceImpl.java:23` — `import java.util.Date`
- `LoyaltyExtendedFieldServiceImpl.java:107` — `Date now = new Date()`
- `LoyaltyExtendedFieldServiceImpl.java:167` — `entity.setUpdatedOn(new Date())`
- `LoyaltyExtendedField.java:10` — `import java.util.Date`
- `LoyaltyExtendedField.java:50,54` — `@Temporal(TemporalType.TIMESTAMP) private Date createdOn/updatedOn`

**Fix required**: Replace `java.util.Date` with `java.time.Instant` in the entity. In the service, use `Instant.now()`. Update `toIsoUtc` helper accordingly (use `ISO_UTC.format(instant)` directly). Remove `@Temporal` annotations (not needed for `Instant` with Hibernate 5.x+ via `AttributeConverter`).

---

### FAIL 2 — Wrong exception codes thrown for `programId <= 0` and blank `name` in `create()`
**Files**:
- `LoyaltyExtendedFieldServiceImpl.java:71` — `programId <= 0` throws `EF_CONFIG_INVALID_ORG` (8010). Code 8010 is semantically "invalid orgId". Client receives a `400` but the error code/message misleadingly says "invalid org" for a programId violation.
- `LoyaltyExtendedFieldServiceImpl.java:75` — blank `name` throws `EF_CONFIG_INVALID_SCOPE` (8004). Code 8004 is "invalid scope". Client receives a `400` for an invalid name but with a scope error code.

**Fix required**: Either (a) introduce a new `EF_CONFIG_INVALID_PROGRAM` (8011) for programId validation and `EF_CONFIG_INVALID_NAME` (8012) for blank name, or (b) reuse a generic 400 code (e.g. 8003 `EF_CONFIG_IMMUTABLE_UPDATE` is also inappropriate — use a new code). Minimum viable fix: add constants to `ExceptionCodes.java` and update the two throw sites.

---

## Warnings (address before release)

### WARN 1 — ADR-01 residual risk: `required` on Thrift request struct fields
Thrift `required` on `CreateLoyaltyExtendedFieldRequest` fields (orgId, programId, name, scope, dataType) means a missing field produces a Thrift protocol exception rather than an EMFException with a business status code. This was accepted as ADR-01 but the open question in session memory remains unresolved. emf.thrift:1561-1567. **Mitigation**: document expected protocol exception handling in V3 `EmfExtendedFieldsThriftService` catch block.

### WARN 2 — Error response body format diverges from V3 convention
`LoyaltyExtendedFieldErrorAdvice` returns `EFErrorResponse {code:String, message:String, field:String}` while all other V3 error advice returns `ResponseWrapper<String>`. This is intentional (EFErrorResponse adds a `field` path) but will require UI team alignment and may break generic error parsing clients. EFErrorResponse.java:12-17. **Mitigation**: communicate the different format in `/api-handoff` artifact.

### WARN 3 — `resolveMaxEfCount` always returns hardcoded 10; `infoLookupService` injected but unused
`LoyaltyExtendedFieldServiceImpl.java:57-58` injects `InfoLookupService` but it is never called. `resolveMaxEfCount` never consults `program_config_key_values` (key_id=48). Per D-15 the per-program override was explicitly planned. The unused injection is dead code that will confuse future developers and may cause unexpected Spring startup failure if `InfoLookupService` is not in context. LoyaltyExtendedFieldServiceImpl.java:57-58,250-252. **Mitigation**: remove the `infoLookupService` injection until D-15 is implemented, or implement it now.
