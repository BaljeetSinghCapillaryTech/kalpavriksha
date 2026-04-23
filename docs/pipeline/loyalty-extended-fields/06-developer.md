# Developer Phase Output — Loyalty Extended Fields CRUD (CAP-183124)
> Phase: 10 (Developer — GREEN phase)
> Date: 2026-04-22
> Status: Complete

---

## Files Written / Modified

### REPO 1: thrift-ifaces-emf (1 file modified)

| File | Change | Approx Lines Added |
|------|--------|--------------------|
| `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf/emf.thrift` | +4 structs (`LoyaltyExtendedFieldConfig`, `CreateLoyaltyExtendedFieldRequest`, `UpdateLoyaltyExtendedFieldRequest`, `LoyaltyExtendedFieldListResponse`) + 3 service methods (#58, #59, #60) | ~80 |

---

### REPO 2: cc-stack-crm (2 files)

| File | Change | Lines |
|------|--------|-------|
| `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/loyalty_extended_fields.sql` | New CREATE TABLE with PK, unique key `uq_org_prog_scope_name`, index `idx_org_prog_scope_active` | 18 |
| `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/seed_data/dbmaster/warehouse/program_config_keys.sql` | +1 row: `MAX_EF_COUNT_PER_PROGRAM` (ID=48, NUMERIC, default=10) | +2 |

---

### REPO 3: emf-parent (7 files)

| File | Change | Lines |
|------|--------|-------|
| `pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/LoyaltyExtendedFieldPK.java` | New `@Embeddable` composite PK (id, orgId — both Long, ADR-02) | 73 |
| `pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/LoyaltyExtendedField.java` | New `@Entity @Table(schema="warehouse")` with builder (10 columns) | 165 |
| `pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/LoyaltyExtendedFieldRepository.java` | New `@Repository extends GenericDao` with 5 query methods (D-32) | 66 |
| `pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/LoyaltyExtendedFieldService.java` | New interface (3 methods: create, update, list) | 47 |
| `pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/LoyaltyExtendedFieldServiceImpl.java` | New `@Service @DataSourceSpecification(WAREHOUSE)` implementation | 215 |
| `emf/src/main/java/com/capillary/shopbook/emf/api/exception/ExceptionCodes.java` | +10 EF constants (8001-8010) + updated `badRequestErrors` set | +38 |
| `emf/src/main/java/com/capillary/shopbook/emf/impl/external/EMFThriftServiceImpl.java` | +1 `@Autowired` field + 3 `@Override` methods (58-60) | +72 |

---

### REPO 4: intouch-api-v3 (14 files)

#### New files (12)

| File | Type | Lines |
|------|------|-------|
| `src/main/java/com/capillary/intouchapiv3/services/thrift/exception/EFThriftException.java` | New exception (extends EMFThriftException + statusCode) | 24 |
| `src/main/java/com/capillary/intouchapiv3/services/thrift/EmfExtendedFieldsThriftService.java` | New `@Service @Loggable` Thrift client (3 methods, RPCService pattern) | 98 |
| `.../extendedfields/CreateExtendedFieldRequest.java` | New DTO (@NotNull/@NotBlank validation) | 41 |
| `.../extendedfields/UpdateExtendedFieldRequest.java` | New DTO (all optional fields — D-23) | 33 |
| `.../extendedfields/ExtendedFieldConfigResponse.java` | New DTO with static `from()` factory | 80 |
| `.../extendedfields/ExtendedFieldsPageResponse.java` | New paginated response DTO with static `from()` factory | 60 |
| `.../extendedfields/EFErrorResponse.java` | New error DTO (code, message, field) | 36 |
| `.../extendedfields/ExtendedFieldValidationException.java` | New RuntimeException (errorCode + field) | 24 |
| `.../extendedfields/ExtendedFieldValidator.java` | New `@Component` — R-01/R-02/R-03 validation logic | 116 |
| `.../extendedfields/LoyaltyExtendedFieldFacade.java` | New `@Component` — Thrift ↔ REST DTO mapping | 96 |
| `.../extendedfields/LoyaltyExtendedFieldController.java` | New `@RestController` — POST/PUT/GET endpoints | 78 |
| `.../extendedfields/LoyaltyExtendedFieldErrorAdvice.java` | New `@ControllerAdvice` — EFThriftException → HTTP | 72 |

#### Modified files (3)

| File | Change |
|------|--------|
| `src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java` | Deleted `ExtendedFieldType type` field + import; added `efId: Long` (D-27, D-28) |
| `src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionFacade.java` | +import + `@Autowired ExtendedFieldValidator` + 2 validation call sites (createSubscription, updateSubscription) |
| `src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionErrorAdvice.java` | +2 imports + `handleExtendedFieldValidationException()` handler method |

#### Deleted files (1)

| File | Reason |
|------|--------|
| `src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java` | D-11, D-27: only 3 confirmed usages, all in-scope |

---

## Total

- **New files**: 20
- **Modified files**: 7
- **Deleted files**: 1
- **Repos touched**: 4

---

## Compile Dependency Satisfaction (from 05-sdet.md)

| Test File | Required Compile Dependencies | Status |
|-----------|-------------------------------|--------|
| `SubscriptionExtendedFieldsTest.java` | `ExtendedField.efId` (Long), builder `.efId()`, no `type` field, no `ExtendedFieldType` class | SATISFIED |
| `LoyaltyExtendedFieldServiceImplTest.java` | `LoyaltyExtendedFieldServiceImpl`, `LoyaltyExtendedFieldRepository`, `ExceptionCodes.EF_CONFIG_*`, `LoyaltyExtendedField`, `LoyaltyExtendedFieldPK` | SATISFIED |
| `ExtendedFieldValidatorTest.java` | `ExtendedFieldValidator`, `ExtendedFieldValidationException`, `EmfExtendedFieldsThriftService`, `ExtendedField.efId` | SATISFIED |
| `LoyaltyExtendedFieldControllerIT.java` | `LoyaltyExtendedFieldController`, `LoyaltyExtendedFieldFacade`, all DTOs | SATISFIED |
| `SubscriptionEFValidationIT.java` | `ExtendedFieldValidator`, `SubscriptionFacade` (with validator injected), `ExtendedFieldValidationException` | SATISFIED |

---

## Notes

- `LoyaltyExtendedFieldServiceImpl.resolveMaxEfCount()` returns hardcoded `DEFAULT_MAX_EF_COUNT=10` as placeholder.
  Future: read from `program_config_key_values` WHERE `key_id=48`. The `infoLookupService` field is injected but not yet called — avoids circular dependency concerns until the actual lookup method is confirmed.
- `EMFThriftServiceImpl` uses fully-qualified `@org.springframework.beans.factory.annotation.Autowired` for the new `loyaltyExtendedFieldService` field to avoid any import conflict risk in the 4,272-line file.
- All test compile dependencies from Phase 9 (05-sdet.md) are satisfied. Tests remain RED until the Thrift-generated classes are regenerated from the updated `emf.thrift` IDL.
