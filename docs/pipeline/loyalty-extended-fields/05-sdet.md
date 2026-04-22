# SDET Phase Output — Loyalty Extended Fields CRUD (CAP-183124)
> Phase: 9 (SDET)
> Date: 2026-04-22
> Status: Complete — RED phase confirmed
> Ticket: CAP-183124

---

## Test Files Written

| # | File Path | Lines | Repo |
|---|-----------|-------|------|
| 1 | `intouch-api-v3/src/test/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionExtendedFieldsTest.java` | 366 | intouch-api-v3 |
| 2 | `emf-parent/pointsengine-emf-ut/src/test/java/com/capillary/shopbook/points/services/LoyaltyExtendedFieldServiceImplTest.java` | 462 | emf-parent |
| 3 | `intouch-api-v3/src/test/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldValidatorTest.java` | 373 | intouch-api-v3 |
| 4 | `intouch-api-v3/src/test/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/LoyaltyExtendedFieldControllerIT.java` | 616 | intouch-api-v3 |
| 5 | `intouch-api-v3/src/test/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/SubscriptionEFValidationIT.java` | 382 | intouch-api-v3 |

**Total: 5 files, 2,199 lines**

---

## Test Method Inventory (BT-EF Mapping)

### File 1: SubscriptionExtendedFieldsTest.java (Updated — BT-EF-01..06)
> Package: `com.capillary.intouchapiv3.unified.subscription`
> JUnit version: JUnit 5 (`@ExtendWith(MockitoExtension.class)`) — matches existing file

| Method | BT-EF | What it tests |
|--------|-------|---------------|
| `extendedField_efIdField_presentInModel()` | BT-EF-01 | `efId (Long)` field added to `ExtendedField`, builder `.efId()` compiles, value returned correctly |
| `extendedField_typeField_removedFromModel()` | BT-EF-02 | No field named "type" exists on `ExtendedField` (reflection check) |
| `extendedField_keyField_preserved()` | BT-EF-03 | `key (String)` field still present and settable |
| `extendedField_valueField_preserved()` | BT-EF-04 | `value (String)` field unchanged |
| `extendedField_deserialize_legacyDoc_efIdNull()` | BT-EF-05 | JSON `{type, key, value}` deserializes with `efId=null`, key/value intact (A-03) |
| `extendedFieldType_enum_deleted()` | BT-EF-06 | `ExtendedFieldType` class not loadable (ClassNotFoundException) |
| `shouldPersistExtendedFieldsOnCreate()` | — | Retained facade test; updated to use `efId` not `type` |
| `shouldOverwriteExtendedFieldsOnUpdateWhenProvided()` | — | Retained facade test; updated to use `efId` |
| `shouldPreserveExtendedFieldsWhenUpdateOmitsField()` | — | R-33 null-guard; updated to use `efId` |
| `shouldCarryExtendedFieldsIntoNewDraftFork()` | — | R-35 fork; updated to use `efId` |
| `shouldCopyExtendedFieldsOnDuplicate()` | — | R-35 duplicate; updated to use `efId` |
| `shouldAcceptMultipleExtendedFieldsWithEfIds()` | — | Multiple EF entries with distinct `efId`s |

**Changes from previous version (diff summary):**
- REMOVED: `import com.capillary.intouchapiv3.unified.subscription.enums.ExtendedFieldType;`
- REMOVED: All `.type(ExtendedFieldType.CUSTOMER_EXTENDED_FIELD)` and `.type(ExtendedFieldType.TXN_EXTENDED_FIELD)` builder calls
- REMOVED: All assertions on `.getType()` and `ExtendedFieldType` equality
- REMOVED: Long-count filter by `ExtendedFieldType` in BT-EF-06
- ADDED: `import com.fasterxml.jackson.databind.ObjectMapper;`
- ADDED: `private static final Long TEST_EF_ID = 1001L;`
- ADDED: 6 new test methods covering BT-EF-01 through BT-EF-06
- UPDATED: All existing facade tests to use `.efId(Long)` builder parameter

---

### File 2: LoyaltyExtendedFieldServiceImplTest.java (New — BT-EF-12, BT-EF-35..40)
> Package: `com.capillary.shopbook.points.services`
> JUnit version: JUnit 4 (`@RunWith(MockitoJUnitRunner.class)`) — matches emf-parent convention

| Method | BT-EF | Error Code | What it tests |
|--------|-------|-----------|---------------|
| `serviceCreate_invalidOrgId_throwsEMFException8010()` | BT-EF-35 | 8010 | `orgId=0` → EMFException(8010) `EF_CONFIG_INVALID_ORG` |
| `serviceCreate_blankName_throwsEMFException()` | BT-EF-36 | — | `name="   "` (whitespace) → EMFException with message |
| `serviceCreate_maxCountExceeded_throwsEMFException8009()` | BT-EF-12 | 8009 | `countActive=10 >= 10` → EMFException(8009) `EF_CONFIG_MAX_COUNT_EXCEEDED` |
| `serviceUpdate_notFound_throwsEMFException8001()` | BT-EF-37 | 8001 | `findByPkIdAndPkOrgId` returns empty → EMFException(8001) |
| `serviceUpdate_nameConflict_throwsEMFException8002()` | BT-EF-38 | 8002 | `existsByPk...` returns true → EMFException(8002) |
| `serviceList_invalidOrgId_throwsEMFException8010()` | BT-EF-39 | 8010 | `list(-1, ...)` → EMFException(8010) |
| `serviceList_nullScope_returnsAllScopes()` | BT-EF-40 | — | `scope=null` → repo called with `null` scope; all scopes returned |
| `serviceUpdate_validRequest_updatesNameAndIsActive()` | — | — | Valid update: name and isActive changed; repo.save() called |
| `serviceList_activeOnly_returnsFilteredConfigs()` | — | — | `includeInactive=false` → repo called with `false` |
| `serviceList_includeInactive_returnsAll()` | — | — | `includeInactive=true` → both active+inactive returned |
| `serviceCreate_validRequest_savesEntityAndReturnsStruct()` | — | — | Happy path create: entity saved, Thrift struct returned with `id` |
| `serviceCreate_duplicateName_throwsEMFException_code8002()` | — | 8002 | `existsByPk...` returns true on create → EMFException(8002) |
| `serviceUpdate_immutableFieldChange_throwsEMFException_code8003()` | — | 8003 | Documents D-23 immutability boundary (enforced at DTO layer) |

---

### File 3: ExtendedFieldValidatorTest.java (New — BT-EF-41..44)
> Package: `com.capillary.intouchapiv3.unified.subscription.extendedfields`
> JUnit version: JUnit 5 (`@ExtendWith(MockitoExtension.class)`) — matches intouch-api-v3 convention

| Method | BT-EF | Error Code | What it tests |
|--------|-------|-----------|---------------|
| `validatorTest_numberType_validAndInvalidValues()` | BT-EF-41 | 8007 | NUMBER: "42" valid; "abc" → EF_VALIDATION_002 |
| `validatorTest_booleanType_validAndInvalidValues()` | BT-EF-42 | 8007 | BOOLEAN: "true"/"false" valid; "yes" → EF_VALIDATION_002 |
| `validatorTest_dateType_validAndInvalidValues()` | BT-EF-43 | 8007 | DATE: ISO-8601 valid; "dd/MM/yyyy" → EF_VALIDATION_002 |
| `validatorTest_stringType_anyValueValid()` | BT-EF-44 | — | STRING: any non-null value (including special chars) passes |
| `validate_allValid_noException()` | — | — | Happy path: all valid types, no exception thrown |
| `validate_unknownEfId_throwsValidationException_code8006()` | — | 8006 | efId not in active configs → EF_VALIDATION_001 |
| `validate_typeMismatch_number_throwsValidationException_code8007()` | — | 8007 | Non-numeric value for NUMBER → EF_VALIDATION_002 |
| `validate_missingMandatory_throwsValidationException_code8008()` | — | 8008 | Empty list + mandatory config → EF_VALIDATION_003 |
| `validate_inactiveEfId_throwsValidationException_code8006()` | — | 8006 | Inactive efId (not in active map) → EF_VALIDATION_001 |
| `validate_nullExtendedFields_noException()` | — | — | Empty list + no mandatory configs → no exception |
| `validate_emptyExtendedFields_withMandatory_throwsValidationException_code8008()` | — | 8008 | Empty list + mandatory field → EF_VALIDATION_003 (8008) |

---

### File 4: LoyaltyExtendedFieldControllerIT.java (New — BT-EF-07..25, BT-EF-45)
> Package: `com.capillary.intouchapiv3.unified.subscription.extendedfields`
> Extends: `integrationTests.AbstractContainerTest`
> JUnit version: JUnit 5 — matches AbstractContainerTest convention

| Method | BT-EF | HTTP | What it tests |
|--------|-------|------|---------------|
| `createEFConfig_validString_returns201()` | BT-EF-07 | 201 | POST valid STRING → 201, id in response |
| `createEFConfig_duplicateName_returns409()` | BT-EF-08 | 409 | Duplicate name → 409, code EF_CONFIG_DUPLICATE_NAME |
| `createEFConfig_invalidScope_returns400()` | BT-EF-09 | 400 | Invalid scope → 400, code EF_CONFIG_INVALID_SCOPE |
| `createEFConfig_invalidDataType_returns400()` | BT-EF-10 | 400 | data_type=ENUM → 400, code EF_CONFIG_INVALID_DATA_TYPE |
| `createEFConfig_defaultsActive_andTimestamps()` | BT-EF-11 | 201 | is_active=true default; timestamps populated |
| `createEFConfig_orgIdFromAuth_notBody()` | BT-EF-13 | 201 | orgId from auth token; facade.create() called with token orgId |
| `updateEFConfig_validNameChange_returns200()` | BT-EF-14 | 200 | PUT rename → 200, new name in response |
| `updateEFConfig_softDelete_returns200()` | BT-EF-15 | 200 | PUT is_active=false → 200, is_active=false in response |
| `updateEFConfig_softDeleteIdempotent_returns200()` | BT-EF-16 | 200 | PUT is_active=false on inactive → 200 (idempotent D-16) |
| `updateEFConfig_notFound_returns404()` | BT-EF-17 | 404 | Non-existent id → 404, code EF_CONFIG_NOT_FOUND |
| `updateEFConfig_wrongOrg_returns404()` | BT-EF-18 | 404 | Wrong org's EF id → 404 (not 403, no disclosure) |
| `updateEFConfig_duplicateNameOnRename_returns409()` | BT-EF-19 | 409 | Rename conflict → 409, code EF_CONFIG_DUPLICATE_NAME |
| `updateEFConfig_updatedOnRefreshed()` | BT-EF-20 | 200 | updated_on > created_on after successful PUT |
| `listEFConfig_defaultReturnsActiveOnly()` | BT-EF-21 | 200 | GET default → only active records (includeInactive=false) |
| `listEFConfig_includeInactiveTrue_returnsAll()` | BT-EF-22 | 200 | GET includeInactive=true → all records |
| `listEFConfig_scopeFilter_returnsMatchingOnly()` | BT-EF-23 | 200 | GET ?scope=SUBSCRIPTION_META → only matching |
| `listEFConfig_emptyOrg_returns200EmptyList()` | BT-EF-24 | 200 | No EFs → 200 with empty list (not 404) G-02.1 |
| `listEFConfig_pagination_respectsPageAndSize()` | BT-EF-25 | 200 | page=0&size=5 → 5 items, totalElements=15, totalPages=3 |
| `createEFConfig_timestampsInUTC()` | BT-EF-45 | 201 | created_on/updated_on match `yyyy-MM-dd'T'HH:mm:ss'Z'` pattern |
| `listEFConfig_crossTenantIsolation_returnsZeroResults()` | — | 200 | Cross-tenant: Org B gets 0 results for Org A's data |

---

### File 5: SubscriptionEFValidationIT.java (New — BT-EF-26..34)
> Package: `com.capillary.intouchapiv3.unified.subscription.extendedfields`
> Extends: `integrationTests.AbstractContainerTest`
> JUnit version: JUnit 5 — matches AbstractContainerTest convention

| Method | BT-EF | HTTP | What it tests |
|--------|-------|------|---------------|
| `validateEF_onSubscriptionCreate_knownKeyValid()` | BT-EF-26 | 2xx | Valid efId + value → subscription created |
| `validateEF_onSubscriptionCreate_unknownKey_returns400()` | BT-EF-27 | 400 | efId not in active configs → 400 (8006) |
| `validateEF_onSubscriptionCreate_typeMismatch_returns400()` | BT-EF-28 | 400 | Non-numeric for NUMBER → 400 (8007) |
| `validateEF_onSubscriptionCreate_mandatoryMissing_returns400()` | BT-EF-29 | 400 | Empty list + mandatory EF → 400 (8008) |
| `validateEF_onSubscriptionCreate_nullEFWithMandatory_returns400()` | BT-EF-30 | 400 | No extendedFields key + mandatory EF → 400 |
| `validateEF_onSubscriptionCreate_validPersistedToMongo()` | BT-EF-31 | 2xx | Valid EFs persisted in MongoDB `extendedFields` |
| `validateEF_onSubscriptionUpdate_nullPreservesExisting()` | BT-EF-32 | 200 | Null EFs on PUT → existing values preserved (R-33) |
| `validateEF_onSubscriptionUpdate_emptyListClearsValues()` | BT-EF-33 | 200 | `extendedFields=[]` on PUT → EF values cleared |
| `validateEF_onSubscriptionUpdate_sameRulesAsCreate()` | BT-EF-34 | 400 | PUT with invalid EF → same 400 errors as POST |
| `validateEF_crossTenantEfId_returns400()` | — | 400 | Cross-tenant efId injection → 400 (8006) |

---

## Compile Dependencies — Production Classes Required by Phase 10

The following classes/methods do NOT yet exist. Tests will fail to compile until Phase 10 provides them.

### emf-parent (pointsengine-emf module)

| Class / Method | Required by | Notes |
|----------------|-------------|-------|
| `com.capillary.shopbook.points.services.LoyaltyExtendedFieldServiceImpl` | `LoyaltyExtendedFieldServiceImplTest` | Full class including `create()`, `update()`, `list()` |
| `com.capillary.shopbook.points.dao.LoyaltyExtendedFieldRepository` | `LoyaltyExtendedFieldServiceImplTest` | Interface with all 5 query methods |
| `com.capillary.shopbook.points.entity.LoyaltyExtendedField` | both service test + IT | Entity class with builder |
| `com.capillary.shopbook.points.entity.LoyaltyExtendedFieldPK` | both service test + IT | Embeddable composite PK |
| `ExceptionCodes.EF_CONFIG_NOT_FOUND` (8001) | `LoyaltyExtendedFieldServiceImplTest` | New constant in existing class |
| `ExceptionCodes.EF_CONFIG_DUPLICATE_NAME` (8002) | `LoyaltyExtendedFieldServiceImplTest` | New constant |
| `ExceptionCodes.EF_CONFIG_MAX_COUNT_EXCEEDED` (8009) | `LoyaltyExtendedFieldServiceImplTest` | New constant |
| `ExceptionCodes.EF_CONFIG_INVALID_ORG` (8010) | `LoyaltyExtendedFieldServiceImplTest` | New constant |
| `EMFThriftServiceImpl` methods 58-60 | (not directly tested in unit tests) | Wired via service |

### intouch-api-v3

| Class / Method | Required by | Notes |
|----------------|-------------|-------|
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldValidator` | `ExtendedFieldValidatorTest`, `SubscriptionEFValidationIT` | Full class with `validate()` method |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldValidationException` | `ExtendedFieldValidatorTest`, `SubscriptionEFValidationIT` | `getErrorCode()` method required |
| `com.capillary.intouchapiv3.services.thrift.EmfExtendedFieldsThriftService` | `ExtendedFieldValidatorTest`, `SubscriptionEFValidationIT`, `LoyaltyExtendedFieldControllerIT` | `getLoyaltyExtendedFieldConfigs()`, `createLoyaltyExtendedFieldConfig()`, `updateLoyaltyExtendedFieldConfig()` |
| `com.capillary.intouchapiv3.services.thrift.exception.EFThriftException` | `LoyaltyExtendedFieldControllerIT` | Constructor `(int statusCode, String message)` |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.LoyaltyExtendedFieldController` | `LoyaltyExtendedFieldControllerIT` | REST endpoints POST/PUT/GET |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.LoyaltyExtendedFieldFacade` | `LoyaltyExtendedFieldControllerIT` | `create()`, `update()`, `list()` |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.LoyaltyExtendedFieldErrorAdvice` | `LoyaltyExtendedFieldControllerIT` | HTTP status code mapping (8001→404, 8002→409, etc.) |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.CreateExtendedFieldRequest` | `LoyaltyExtendedFieldControllerIT` | DTO with all fields |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.UpdateExtendedFieldRequest` | `LoyaltyExtendedFieldControllerIT` | DTO with `name`, `isActive` |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldConfigResponse` | `LoyaltyExtendedFieldControllerIT` | DTO with all config fields |
| `com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldsPageResponse` | `LoyaltyExtendedFieldControllerIT` | Paginated response DTO |
| `SubscriptionProgram.ExtendedField.efId` (Long field) | All test files | `builder().efId(Long)` must compile |
| `SubscriptionProgram.ExtendedField.getEfId()` | All test files | Getter must return Long |
| `ExtendedFieldType` class deleted | `SubscriptionExtendedFieldsTest` | BT-EF-06 verifies ClassNotFoundException |
| `SubscriptionErrorAdvice` — handler for `ExtendedFieldValidationException` | `SubscriptionEFValidationIT` | Maps to 400 |
| `SubscriptionFacade` — `ExtendedFieldValidator.validate()` call hook | `SubscriptionEFValidationIT` | Phase 10 wiring |

### Thrift-generated (emf.thrift compilation)

| Class | Source | Required by |
|-------|--------|-------------|
| `LoyaltyExtendedFieldConfig` | Thrift-generated from emf.thrift | All test files |
| `LoyaltyExtendedFieldListResponse` | Thrift-generated from emf.thrift | ExtendedFieldValidatorTest, SubscriptionEFValidationIT |
| `CreateLoyaltyExtendedFieldRequest` | Thrift-generated | LoyaltyExtendedFieldServiceImplTest |
| `UpdateLoyaltyExtendedFieldRequest` | Thrift-generated | LoyaltyExtendedFieldServiceImplTest |

---

## RED Phase Confirmation

**These tests will fail to compile AND fail at runtime until Phase 10 production code is written.**

Compile failures (expected):
- `LoyaltyExtendedFieldServiceImpl` class not found
- `LoyaltyExtendedFieldRepository` interface not found
- `ExtendedFieldValidator` class not found
- `ExtendedFieldValidationException` class not found
- `EmfExtendedFieldsThriftService` class not found
- `EFThriftException` class not found
- `LoyaltyExtendedFieldController` / `LoyaltyExtendedFieldFacade` / DTOs not found
- `ExceptionCodes.EF_CONFIG_*` constants not found (8001-8010 range)
- `SubscriptionProgram.ExtendedField.efId` field not found (builder `.efId()` won't compile)
- `ExtendedFieldType` deletion — BT-EF-06 asserts `ClassNotFoundException`, which will only pass after the class is deleted in Phase 10

Runtime failures (once compiled):
- All tests hitting non-existent production implementations

This is **intentional and correct** for the RED phase of TDD (Chicago/Detroit school). Phase 10 (`/developer`) writes production code to make these tests GREEN.

---

## JUnit Version Conventions

| Repo | JUnit version used | Evidence |
|------|-------------------|---------|
| intouch-api-v3 | JUnit 5 (`@ExtendWith`) | `SubscriptionExtendedFieldsTest.java`, `SubscriptionFacadeIT.java` |
| emf-parent (pointsengine-emf-ut) | JUnit 4 (`@RunWith`) | `CurrencyExpiryServiceImplTest.java`, all existing service tests |

Tests written accordingly: intouch-api-v3 tests use `@ExtendWith(MockitoExtension.class)`; emf-parent test uses `@RunWith(MockitoJUnitRunner.class)`.

---

## Coverage

- BT-EF-01 through BT-EF-06: covered in `SubscriptionExtendedFieldsTest.java` (6 new methods + 6 updated facade tests)
- BT-EF-07 through BT-EF-25, BT-EF-45: covered in `LoyaltyExtendedFieldControllerIT.java` (20 methods)
- BT-EF-26 through BT-EF-34: covered in `SubscriptionEFValidationIT.java` (9 methods + 1 cross-tenant)
- BT-EF-35 through BT-EF-40, BT-EF-12: covered in `LoyaltyExtendedFieldServiceImplTest.java` (13 methods)
- BT-EF-41 through BT-EF-44: covered in `ExtendedFieldValidatorTest.java` (11 methods)

**Total business tests covered: BT-EF-01 through BT-EF-45 (all 45)**
**Additional non-BT test methods: 14** (service happy paths, cross-tenant guard, cross-cutting validation)
**Grand total test methods: ~59 across 5 files**
