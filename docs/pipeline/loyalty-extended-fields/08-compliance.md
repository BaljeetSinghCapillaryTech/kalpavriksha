# Compliance Gap Analysis — CAP-183124
> Date: 2026-04-22 | Phase: 10c | Analyst: /analyst --compliance

---

## Summary

| Dimension | Critical | High | Medium | Low | Score |
|-----------|----------|------|--------|-----|-------|
| D1: ADR Compliance | 1 | 0 | 0 | 0 | 7/8 ADRs PASS |
| D2: Decision Compliance | 0 | 0 | 1 | 1 | 11/13 checks PASS |
| D3: Guardrail Compliance | 0 | 1 | 0 | 0 | 4/5 checks PASS |
| D4: API Contract Drift | 0 | 0 | 0 | 0 | All endpoints match spec |
| D5: Structural Compliance | 0 | 0 | 0 | 0 | All packages correct |
| **Total** | **1** | **1** | **1** | **1** | |

---

## Findings (sorted by severity)

### CRITICAL

---

**GAP-01** | Dimension 1 | ADR-01 | CRITICAL
- **Rule**: ADR-01 states all _request_ struct fields must be `optional` for rolling deployment safety — to avoid `TProtocolException` during the window when EMF is deployed before V3 is on the new code. Quote: _"Use `optional` on all request struct parameters — including `orgId`, `programId`, `name`, `scope`."_
- **Evidence**: `emf.thrift:1562-1570` — `CreateLoyaltyExtendedFieldRequest` has fields 1–6 all marked `required`:
  ```thrift
  1: required i64    orgId
  2: required i64    programId
  3: required string name
  4: required string scope
  5: required string dataType
  6: required bool   isMandatory
  ```
  `UpdateLoyaltyExtendedFieldRequest:1579-1580` also has `id` and `orgId` as `required`.
- **Impact**: During rolling deployment (EMF deployed before V3 is updated), if V3 sends an old serialized struct that is missing any of these `required` fields, the Thrift transport layer throws `TProtocolException` before the application layer can handle it. This is exactly the risk ADR-01 was designed to prevent. The ADR explicitly rejected `required` on request fields for this operational safety reason.
- **Remediation**: Change all fields in `CreateLoyaltyExtendedFieldRequest` from `required` to `optional`. Change `id` and `orgId` in `UpdateLoyaltyExtendedFieldRequest` to `optional`. Add server-side null-guards in `EMFThriftServiceImpl` methods 58 and 59 (defensive check: if `orgId == null || orgId <= 0` then throw `EMFException(8010, ...)`). The response struct `LoyaltyExtendedFieldConfig` is correctly left with `required` on always-present fields.
- **Confidence**: C7 — ADR-01 text and IDL both read directly.

---

### HIGH

---

**GAP-02** | Dimension 3 | G-01.1 | HIGH
- **Rule**: G-01.1 prohibits `java.util.Date` and `new Date()` in new code. UTC-safe types (`Instant`, `LocalDateTime`, `ZonedDateTime`) must be used.
- **Evidence**:
  - `LoyaltyExtendedField.java:10`: `import java.util.Date;`
  - `LoyaltyExtendedField.java:50,54`: `@Temporal(TemporalType.TIMESTAMP) private Date createdOn;` and `private Date updatedOn;`
  - `LoyaltyExtendedField.java:106-113`: getters/setters returning `Date`
  - `LoyaltyExtendedField.java:134,135,146,147`: builder fields `private Date createdOn; private Date updatedOn;`
  - `LoyaltyExtendedFieldServiceImpl.java:23`: `import java.util.Date;`
  - `LoyaltyExtendedFieldServiceImpl.java:107`: `Date now = new Date();`
  - `LoyaltyExtendedFieldServiceImpl.java:167`: `entity.setUpdatedOn(new Date());`
  - The `SubscriptionFacade.java` (existing file, modified) also uses `new Date()` at lines 94 and 306 — but those are in pre-existing code, not new additions.
- **Impact**: `java.util.Date` is timezone-naive and error-prone. `new Date()` uses system clock with no explicit UTC guarantee. This contradicts G-01.1 and undermines the stated rationale for ADR-07 (TIMESTAMP for UTC compliance). The `toIsoUtc()` helper in `LoyaltyExtendedFieldServiceImpl` converts to UTC correctly at serialization time, but the field type itself is still `Date`.
- **Remediation**: Replace `java.util.Date` with `java.time.Instant` in `LoyaltyExtendedField.java` for `createdOn`/`updatedOn`. Use `@Column(columnDefinition = "TIMESTAMP")` and JPA's `@Convert` with `InstantConverter` (or Spring Data's built-in `Instant` support). Replace `new Date()` with `Instant.now()` in `LoyaltyExtendedFieldServiceImpl`. The `toIsoUtc(Date date)` helper should become `toIsoUtc(Instant instant)`.
- **Confidence**: C7 — imports and usages verified by direct file reads.

---

### MEDIUM

---

**GAP-03** | Dimension 2 | D-15 | MEDIUM
- **Rule**: D-15 states the org-level max EF count is stored in `program_config_key_values` with key_id=48 (`MAX_EF_COUNT_PER_PROGRAM`), allowing per-org overrides. The seed data (ID=48) has been written; the service should read from it.
- **Evidence**: `LoyaltyExtendedFieldServiceImpl.java:58`: `@Autowired private InfoLookupService infoLookupService;` — autowired but never used. `LoyaltyExtendedFieldServiceImpl.java:250-252`: `resolveMaxEfCount()` always returns `DEFAULT_MAX_EF_COUNT = 10`, never reading from `program_config_key_values`. The `infoLookupService` injection is dead code.
- **Impact**: Org-level EF count overrides stored in `program_config_key_values` are silently ignored. All programs are capped at 10 regardless of any per-org override configured. The `infoLookupService` field being injected but unused may cause a Spring autowire failure if the bean is not available in the test context.
- **Remediation**: Implement `resolveMaxEfCount(orgId, programId)` to call `infoLookupService.getAllValidProgramConfigKeys()` (or the equivalent) for key_id=48, returning the org/program-specific value if present and falling back to `DEFAULT_MAX_EF_COUNT`. Alternatively, remove the `infoLookupService` injection and add a TODO comment if this is intentionally deferred. Either way, the dead injection should be resolved.
- **Confidence**: C7 — both the unused injection and the hardcoded return are verified from direct file reads.

---

### LOW

---

**GAP-04** | Dimension 2 | D-29 | LOW
- **Rule**: D-29 states `program_id` is required in all API/Thrift calls. The `CreateExtendedFieldRequest` (REST DTO) must include `programId` as a required field.
- **Evidence**: `CreateExtendedFieldRequest.java:13`: `@NotNull(message = "programId must not be null") private Long programId;` — present and correctly annotated. PASS for REST DTO. However, at `SubscriptionFacade.java:81`, the `createSubscription` method accepts `Integer programId` (not `Long`), and at line 91 this `Integer` is passed to `extendedFieldValidator.validate(long orgId, long programId, ...)`. Java will auto-unbox `Integer` → `int` → widen to `long`, but if `programId` is `null` (it is declared as `Integer`, not a primitive), the unboxing throws a `NullPointerException` rather than a `400 Bad Request`.
- **Impact**: If `programId` is null when calling `createSubscription`, the auto-unbox on line 91 throws an unchecked `NullPointerException` which is not caught by `SubscriptionErrorAdvice` (no NPE handler), resulting in a 500 rather than a structured 400. This is a low-severity risk because `programId` should never be null in the calling path, but there is no null-guard.
- **Remediation**: Add a null-guard before line 91 in `SubscriptionFacade.createSubscription`: `if (programId == null) throw new IllegalArgumentException(...)`, or change the method parameter to `long programId` (primitive). Alternatively, call `validate(orgId, programId.longValue(), ...)` explicitly and add `Objects.requireNonNull(programId, "programId must not be null")` above.
- **Confidence**: C6 — Java auto-unbox behavior is well-defined; null path requires caller analysis.

---

## Passed Checks

### ADR Compliance (Dimension 1)

| Check | Status | Evidence |
|-------|--------|---------|
| ADR-02: `LoyaltyExtendedFieldPK` is standalone `@Embeddable`, does NOT extend `OrgEntityLongPKBase` | PASS | `LoyaltyExtendedFieldPK.java:14` — `@Embeddable public class LoyaltyExtendedFieldPK implements Serializable` with `Long id`, `Long orgId` directly |
| ADR-03: `SubscriptionProgram.ExtendedField` has `efId: Long` added, `key: String` kept, `type` deleted, no `@Field` | PASS | `SubscriptionProgram.java:305,312` — `private Long efId;`, `private String key;`; no `type` field; no `@Field` annotation |
| ADR-04: `EmfExtendedFieldsThriftService` uses `EMFService.Iface.class` | PASS | `EmfExtendedFieldsThriftService.java:99` — `RPCService.rpcClient(EMFService.Iface.class, "emf-thrift-service", 9199, 10000)` |
| ADR-05: EF Validation uses one Thrift call + in-memory fail-fast | PASS | `ExtendedFieldValidator.java:58-61` — single `getLoyaltyExtendedFieldConfigs` call; fail-fast loop at lines 69-91 |
| ADR-06: New `LoyaltyExtendedFieldErrorAdvice` for EF config; `SubscriptionErrorAdvice` extended for EF validation | PASS | `LoyaltyExtendedFieldErrorAdvice.java:23` — `@ControllerAdvice(assignableTypes={LoyaltyExtendedFieldController.class})`; `SubscriptionErrorAdvice.java:77` — `@ExceptionHandler(ExtendedFieldValidationException.class)` added |
| ADR-07: `loyalty_extended_fields.sql` uses `TIMESTAMP` for both audit columns | PASS | `loyalty_extended_fields.sql:11-12` — `created_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`, `updated_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` |
| ADR-08: No `getLoyaltyExtendedFieldById` method in `emf.thrift` — only methods 58, 59, 60 | PASS | `emf.thrift:1960-1991` — exactly 3 new methods; no getById method exists |

### Decision Compliance (Dimension 2)

| Check | Status | Evidence |
|-------|--------|---------|
| D-24: No DELETE endpoint | PASS | `LoyaltyExtendedFieldController.java` — `@PostMapping`, `@PutMapping("/{id}")`, `@GetMapping` only; no `@DeleteMapping` |
| D-27: `type` field completely deleted from `SubscriptionProgram.ExtendedField` | PASS | `SubscriptionProgram.java:299-316` — no `type` field; no `ExtendedFieldType` import in file |
| D-28: `efId: Long` present, `key: String` kept | PASS | `SubscriptionProgram.java:305,312` |
| D-29: `program_id` in schema AND `programId` required in `CreateExtendedFieldRequest` | PASS | `loyalty_extended_fields.sql:4`, `CreateExtendedFieldRequest.java:13` |
| D-30: Uniqueness check does NOT filter on `is_active` | PASS | `LoyaltyExtendedFieldServiceImpl.java:100-103` — `existsByPkOrgIdAndProgramIdAndScopeAndName` takes no `isActive` parameter; `LoyaltyExtendedFieldRepository.java:40-41` confirms the method signature has no is_active filter |
| D-31: `@ControllerAdvice` ErrorAdvice present for EF controller | PASS | `LoyaltyExtendedFieldErrorAdvice.java:23` |
| D-33: `ExtendedFieldValidationException` extends `RuntimeException` | PASS | `ExtendedFieldValidationException.java:9` — `public class ExtendedFieldValidationException extends RuntimeException` |

### Guardrail Compliance (Dimension 3)

| Check | Status | Evidence |
|-------|--------|---------|
| G-03: No SQL concatenation; `@Query` uses named parameters | PASS | `LoyaltyExtendedFieldRepository.java:54-75` — all `@Query` JPQL uses `:orgId`, `:programId`, `:scope`, `:includeInactive` named params; no string concatenation |
| G-07.1: `orgId` extracted from auth token, never from request body | PASS | `LoyaltyExtendedFieldController.java:49` — `user.getOrgId()`; `CreateExtendedFieldRequest.java` has no `orgId` field |
| G-07.1: Every repository query includes orgId | PASS | All 5 query methods in `LoyaltyExtendedFieldRepository.java` include `orgId`/`pkOrgId` as a mandatory parameter |
| G-09.5: No new `required` fields on existing Thrift structs (only new structs) | PASS — with caveat | New structs are additions; no existing struct was modified. The GAP-01 issue concerns `required` on new request structs' fields (ADR-01 violation), not existing struct modification |

### API Contract Drift (Dimension 4)

| Endpoint | Spec | Implementation | Status |
|----------|------|----------------|--------|
| POST `/v3/extendedfields/config` → HTTP 201 | `01-architect.md` §3d | `LoyaltyExtendedFieldController.java:55` — `ResponseEntity.status(HttpStatus.CREATED).body(response)` | PASS |
| PUT `/v3/extendedfields/config/{id}` → accepts `{name, isActive}` only | `01-architect.md` D-23 | `UpdateExtendedFieldRequest.java` — `name` (String), `isActive` (Boolean) only | PASS |
| GET `/v3/extendedfields/config` → `programId`, `scope`, `includeInactive`, `page`, `size` params | `01-architect.md` D-20 | `LoyaltyExtendedFieldController.java:82-87` — all 5 params present with correct defaults | PASS |
| Thrift method #58 signature matches `LoyaltyExtendedFieldService.create()` | `03-designer.md` | `emf.thrift:1960-1962` matches `LoyaltyExtendedFieldService.java` `create(CreateLoyaltyExtendedFieldRequest)` | PASS |
| Thrift method #59 signature matches `LoyaltyExtendedFieldService.update()` | `03-designer.md` | `emf.thrift:1972-1974` matches `LoyaltyExtendedFieldService.java` `update(UpdateLoyaltyExtendedFieldRequest)` | PASS |
| Thrift method #60 signature matches `LoyaltyExtendedFieldService.list()` | `03-designer.md` | `emf.thrift:1984-1991` — 6 params (orgId, programId, scope, includeInactive, page, size) matches `list()` signature | PASS |

### Structural Compliance (Dimension 5)

| Check | Status | Evidence |
|-------|--------|---------|
| V3 new classes in `com.capillary.intouchapiv3.unified.subscription.extendedfields` | PASS | All 10 files in `/extendedfields/` directory confirmed |
| `EmfExtendedFieldsThriftService` in `com.capillary.intouchapiv3.services.thrift` | PASS | File path confirmed |
| EMF new classes in `com.capillary.shopbook.points.*` packages | PASS | Entity in `.entity`, repository in `.dao`, service in `.services` |
| `LoyaltyExtendedFieldRepository` in `dao` subpackage | PASS | `LoyaltyExtendedFieldRepository.java` in `pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/` |

---

## Risk Summary for Release Decision

| GAP | Severity | Block Release? | Fix Complexity |
|-----|----------|---------------|----------------|
| GAP-01: ADR-01 violation — request fields `required` in IDL | CRITICAL | YES — operational safety risk during rolling deploy | Low (IDL keyword change + 2 null-guards in EMFThriftServiceImpl) |
| GAP-02: G-01.1 violation — `java.util.Date`/`new Date()` in new entity + service | HIGH | Recommend YES — contradicts explicit guardrail and the stated UTC rationale for ADR-07 | Medium (field type change + JPA converter update) |
| GAP-03: D-15 `resolveMaxEfCount` always returns hardcoded 10; dead `infoLookupService` injection | MEDIUM | NO — functionally correct at default; dead injection is cosmetic | Low (either implement or remove injection) |
| GAP-04: Potential NPE on `Integer programId` auto-unbox in `SubscriptionFacade.createSubscription` | LOW | NO — null programId is prevented upstream by controller validation | Low (add null-guard) |

---

*Produced by /analyst --compliance (Phase 10c) — CAP-183124 — 2026-04-22*
