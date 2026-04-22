# Business Test Case Listing — Loyalty Extended Fields CRUD (CAP-183124)
> Phase: 8b (Business Test Generator)
> Date: 2026-04-22
> Status: Complete
> Ticket: CAP-183124

---

## Traceability Matrix

| Test ID | Test Name | Story | AC Reference | Layer |
|---------|-----------|-------|--------------|-------|
| BT-EF-01 | extendedField_efIdField_presentInModel | EF-US-07 | efId (Long) added to ExtendedField model | Unit |
| BT-EF-02 | extendedField_typeField_removedFromModel | EF-US-07 | type field deleted; no ExtendedFieldType references | Unit |
| BT-EF-03 | extendedField_keyField_preserved | EF-US-07 | key (String) kept in final model | Unit |
| BT-EF-04 | extendedField_valueField_preserved | EF-US-07 | value (String) unchanged | Unit |
| BT-EF-05 | extendedField_deserialize_legacyDoc_efIdNull | EF-US-07 | Legacy {type,key,value} doc deserializes with efId=null, key/value intact | Unit |
| BT-EF-06 | extendedFieldType_enum_deleted | EF-US-07 | ExtendedFieldType.java does not compile / class removed | Unit |
| BT-EF-07 | createEFConfig_validString_returns201 | EF-US-01 | POST creates row, returns id | IT |
| BT-EF-08 | createEFConfig_duplicateName_returns409 | EF-US-01 | (org_id, program_id, scope, name) duplicate → 409 CONFLICT | IT |
| BT-EF-09 | createEFConfig_invalidScope_returns400 | EF-US-01 | scope not in allowed set → 400 | IT |
| BT-EF-10 | createEFConfig_invalidDataType_returns400 | EF-US-01 | data_type not in STRING/NUMBER/BOOLEAN/DATE → 400 | IT |
| BT-EF-11 | createEFConfig_defaultsActive_andTimestamps | EF-US-01 | is_active=true, created_on/updated_on populated UTC | IT |
| BT-EF-12 | createEFConfig_maxCountExceeded_returns400 | EF-US-01 | active EF count >= MAX → 400 (8009) | Unit |
| BT-EF-13 | createEFConfig_orgIdFromAuth_notBody | EF-US-01 | org_id sourced from auth context (G-07.1) | IT |
| BT-EF-14 | updateEFConfig_validNameChange_returns200 | EF-US-02 | PUT updates name; re-validates uniqueness | IT |
| BT-EF-15 | updateEFConfig_softDelete_returns200 | EF-US-02 | is_active=false sets soft-delete; 200 returned | IT |
| BT-EF-16 | updateEFConfig_softDeleteIdempotent_returns200 | EF-US-02 | is_active=false on already-inactive → 200 | IT |
| BT-EF-17 | updateEFConfig_notFound_returns404 | EF-US-02 | non-existent id → 404 NOT FOUND | IT |
| BT-EF-18 | updateEFConfig_wrongOrg_returns404 | EF-US-02 | valid id but wrong org_id → 404 (tenancy) | IT |
| BT-EF-19 | updateEFConfig_duplicateNameOnRename_returns409 | EF-US-02 | rename to existing name for same (org, prog, scope) → 409 | IT |
| BT-EF-20 | updateEFConfig_updatedOnRefreshed | EF-US-02 | last_updated_on advances on every successful PUT | IT |
| BT-EF-21 | listEFConfig_defaultReturnsActiveOnly | EF-US-03 | GET without includeInactive returns only is_active=1 | IT |
| BT-EF-22 | listEFConfig_includeInactiveTrue_returnsAll | EF-US-03 | includeInactive=true returns active + inactive | IT |
| BT-EF-23 | listEFConfig_scopeFilter_returnsMatchingOnly | EF-US-03 | ?scope=SUBSCRIPTION_META filters correctly | IT |
| BT-EF-24 | listEFConfig_emptyOrg_returns200EmptyList | EF-US-03 | no EF configs → 200 with empty list (not 404) | IT |
| BT-EF-25 | listEFConfig_pagination_respectsPageAndSize | EF-US-03 | page/size params respected; totalElements correct | IT |
| BT-EF-26 | validateEF_onSubscriptionCreate_knownKeyValid | EF-US-05 | key matches ACTIVE registry entry → accepted | IT |
| BT-EF-27 | validateEF_onSubscriptionCreate_unknownKey_returns400 | EF-US-05 | key not in ACTIVE registry → 400 unknown field | IT |
| BT-EF-28 | validateEF_onSubscriptionCreate_typeMismatch_returns400 | EF-US-05 | value fails data_type check → 400 type mismatch | IT |
| BT-EF-29 | validateEF_onSubscriptionCreate_mandatoryMissing_returns400 | EF-US-05 | mandatory EF absent from list → 400 | IT |
| BT-EF-30 | validateEF_onSubscriptionCreate_nullEFWithMandatory_returns400 | EF-US-05 | extendedFields=null with mandatory fields → 400 | IT |
| BT-EF-31 | validateEF_onSubscriptionCreate_validPersistedToMongo | EF-US-05 | valid EFs persisted in subscription_programs.extendedFields | IT |
| BT-EF-32 | validateEF_onSubscriptionUpdate_nullPreservesExisting | EF-US-06 | extendedFields=null on PUT → existing values preserved (R-33) | IT |
| BT-EF-33 | validateEF_onSubscriptionUpdate_emptyListClearsValues | EF-US-06 | extendedFields=[] on PUT → clears all EF values | IT |
| BT-EF-34 | validateEF_onSubscriptionUpdate_sameRulesAsCreate | EF-US-06 | PUT with EFs applies same validation as POST | IT |
| BT-EF-35 | serviceCreate_invalidOrgId_throwsEMFException8010 | EF-US-01 | orgId <= 0 → EMFException 8010 | Unit |
| BT-EF-36 | serviceCreate_blankName_throwsEMFException | EF-US-01 | blank name rejected at service layer | Unit |
| BT-EF-37 | serviceUpdate_notFound_throwsEMFException8001 | EF-US-02 | id not found → EMFException 8001 | Unit |
| BT-EF-38 | serviceUpdate_nameConflict_throwsEMFException8002 | EF-US-02 | name rename conflicts → EMFException 8002 | Unit |
| BT-EF-39 | serviceList_invalidOrgId_throwsEMFException8010 | EF-US-03 | orgId <= 0 on list → EMFException 8010 | Unit |
| BT-EF-40 | serviceList_nullScope_returnsAllScopes | EF-US-03 | scope=null → all scopes returned | Unit |
| BT-EF-41 | validatorTest_numberType_validAndInvalidValues | EF-US-05 | NUMBER: "42" valid; "abc" invalid | Unit |
| BT-EF-42 | validatorTest_booleanType_validAndInvalidValues | EF-US-05 | BOOLEAN: "true"/"false" valid; "yes" invalid | Unit |
| BT-EF-43 | validatorTest_dateType_validAndInvalidValues | EF-US-05 | DATE: ISO-8601 string valid; "22/04/2026" invalid | Unit |
| BT-EF-44 | validatorTest_stringType_anyValueValid | EF-US-05 | STRING: any non-null value passes | Unit |
| BT-EF-45 | createEFConfig_timestampsInUTC | EF-US-01 | created_on/updated_on returned as UTC ISO-8601 (G-01.1) | IT |

---

## Test Classes

### Existing Class — Updates Required (BT-EF-01..06)

**`SubscriptionExtendedFieldsTest.java`** (intouch-api-v3)

| BT-EF | Current test | Required change |
|-------|-------------|-----------------|
| BT-EF-01 | Tests `ExtendedField` model construction | Assert `efId` field (Long) is present and settable |
| BT-EF-02 | Tests `ExtendedField` model fields | Remove all `type` / `ExtendedFieldType` assertions; assert field is absent |
| BT-EF-03 | Tests `key` field on `ExtendedField` | No change needed to assertion; confirm `key` still present |
| BT-EF-04 | Tests `value` field on `ExtendedField` | No change needed; confirm `value` still present |
| BT-EF-05 | (New test in existing class) | Deserialize JSON `{"type":"CUSTOMER_EXTENDED_FIELD","key":"g","value":"f"}` → `efId=null`, `key="g"`, `value="f"` |
| BT-EF-06 | (New test in existing class) | Confirm `ExtendedFieldType` class cannot be referenced (compile-time deletion check via absence) |

---

### New Test Classes

#### `LoyaltyExtendedFieldServiceImplTest.java` (Unit — emf-parent)
Package: `com.capillary.shopbook.points.services`
Mocks: `LoyaltyExtendedFieldRepository`, `InfoLookupService`

- BT-EF-12 `serviceCreate_maxCountExceeded_throwsEMFException8009`
- BT-EF-35 `serviceCreate_invalidOrgId_throwsEMFException8010`
- BT-EF-36 `serviceCreate_blankName_throwsEMFException`
- BT-EF-37 `serviceUpdate_notFound_throwsEMFException8001`
- BT-EF-38 `serviceUpdate_nameConflict_throwsEMFException8002`
- BT-EF-39 `serviceList_invalidOrgId_throwsEMFException8010`
- BT-EF-40 `serviceList_nullScope_returnsAllScopes`

#### `LoyaltyExtendedFieldControllerIT.java` (IT — intouch-api-v3)
Package: `com.capillary.intouchapiv3.subscriptions`
Uses: Spring MockMvc or RestAssured against real warehouse test DB

- BT-EF-07 `createEFConfig_validString_returns201`
- BT-EF-08 `createEFConfig_duplicateName_returns409`
- BT-EF-09 `createEFConfig_invalidScope_returns400`
- BT-EF-10 `createEFConfig_invalidDataType_returns400`
- BT-EF-11 `createEFConfig_defaultsActive_andTimestamps`
- BT-EF-13 `createEFConfig_orgIdFromAuth_notBody`
- BT-EF-14 `updateEFConfig_validNameChange_returns200`
- BT-EF-15 `updateEFConfig_softDelete_returns200`
- BT-EF-16 `updateEFConfig_softDeleteIdempotent_returns200`
- BT-EF-17 `updateEFConfig_notFound_returns404`
- BT-EF-18 `updateEFConfig_wrongOrg_returns404`
- BT-EF-19 `updateEFConfig_duplicateNameOnRename_returns409`
- BT-EF-20 `updateEFConfig_updatedOnRefreshed`
- BT-EF-21 `listEFConfig_defaultReturnsActiveOnly`
- BT-EF-22 `listEFConfig_includeInactiveTrue_returnsAll`
- BT-EF-23 `listEFConfig_scopeFilter_returnsMatchingOnly`
- BT-EF-24 `listEFConfig_emptyOrg_returns200EmptyList`
- BT-EF-25 `listEFConfig_pagination_respectsPageAndSize`
- BT-EF-45 `createEFConfig_timestampsInUTC`

#### `ExtendedFieldValidatorTest.java` (Unit — intouch-api-v3)
Package: `com.capillary.intouchapiv3.subscriptions.validation`
Mocks: `EmfExtendedFieldsThriftService`

- BT-EF-41 `validatorTest_numberType_validAndInvalidValues`
- BT-EF-42 `validatorTest_booleanType_validAndInvalidValues`
- BT-EF-43 `validatorTest_dateType_validAndInvalidValues`
- BT-EF-44 `validatorTest_stringType_anyValueValid`

#### `SubscriptionEFValidationIT.java` (IT — intouch-api-v3)
Package: `com.capillary.intouchapiv3.subscriptions`
Extends existing subscription IT infra; requires seeded `loyalty_extended_fields` rows

- BT-EF-26 `validateEF_onSubscriptionCreate_knownKeyValid`
- BT-EF-27 `validateEF_onSubscriptionCreate_unknownKey_returns400`
- BT-EF-28 `validateEF_onSubscriptionCreate_typeMismatch_returns400`
- BT-EF-29 `validateEF_onSubscriptionCreate_mandatoryMissing_returns400`
- BT-EF-30 `validateEF_onSubscriptionCreate_nullEFWithMandatory_returns400`
- BT-EF-31 `validateEF_onSubscriptionCreate_validPersistedToMongo`
- BT-EF-32 `validateEF_onSubscriptionUpdate_nullPreservesExisting`
- BT-EF-33 `validateEF_onSubscriptionUpdate_emptyListClearsValues`
- BT-EF-34 `validateEF_onSubscriptionUpdate_sameRulesAsCreate`

---

## Full Test List

```
BT-EF-01: extendedField_efIdField_presentInModel
  Class: SubscriptionExtendedFieldsTest
  Story: EF-US-07
  AC: SubscriptionProgram.ExtendedField.efId (Long) added — D-28
  Given: ExtendedField object instantiated
  When: efId is set via setter
  Then: efId is returned correctly; field is Long type
  Layer: Unit

BT-EF-02: extendedField_typeField_removedFromModel
  Class: SubscriptionExtendedFieldsTest
  Story: EF-US-07
  AC: type field deleted; ExtendedFieldType enum deleted — D-27
  Given: ExtendedField class definition
  When: inspecting fields
  Then: no field named "type"; no reference to ExtendedFieldType compiles
  Layer: Unit

BT-EF-03: extendedField_keyField_preserved
  Class: SubscriptionExtendedFieldsTest
  Story: EF-US-07
  AC: key (String) kept — D-28
  Given: ExtendedField object
  When: key is set to "gender"
  Then: getKey() returns "gender"
  Layer: Unit

BT-EF-04: extendedField_valueField_preserved
  Class: SubscriptionExtendedFieldsTest
  Story: EF-US-07
  AC: value (String) unchanged
  Given: ExtendedField object
  When: value is set to "M"
  Then: getValue() returns "M"
  Layer: Unit

BT-EF-05: extendedField_deserialize_legacyDoc_efIdNull
  Class: SubscriptionExtendedFieldsTest
  Story: EF-US-07
  AC: existing MongoDB docs with {type, key, value} deserialize with efId=null, key/value intact
  Given: JSON string '{"type":"CUSTOMER_EXTENDED_FIELD","key":"gender","value":"M"}'
  When: deserialized into ExtendedField via ObjectMapper
  Then: efId=null, key="gender", value="M" (no exception)
  Layer: Unit

BT-EF-06: extendedFieldType_enum_deleted
  Class: SubscriptionExtendedFieldsTest
  Story: EF-US-07
  AC: ExtendedFieldType enum class deleted — D-27
  Given: codebase after changes
  When: checking for class com.capillary.intouchapiv3...ExtendedFieldType
  Then: class does not exist; no remaining usages in the 3 confirmed call sites
  Layer: Unit

BT-EF-07: createEFConfig_validString_returns201
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: POST /v3/extendedfields/config creates row; returns id
  Given: org with no existing EF configs; valid auth token
  When: POST with {name:"tier_label", scope:"SUBSCRIPTION_META", data_type:"STRING", is_mandatory:false}
  Then: HTTP 201; response body contains id > 0; row exists in loyalty_extended_fields
  Layer: IT

BT-EF-08: createEFConfig_duplicateName_returns409
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: (org_id, program_id, scope, name) duplicate → 409 CONFLICT
  Given: EF config "tier_label" already exists for (org, program, scope)
  When: POST with same name, same org/program/scope
  Then: HTTP 409; error code EF_CONFIG_DUPLICATE_NAME (8002)
  Layer: IT

BT-EF-09: createEFConfig_invalidScope_returns400
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: scope not in allowed set → 400
  Given: valid auth
  When: POST with scope="SUBSCRIPTION_LINK" (deferred scope)
  Then: HTTP 400; error code EF_CONFIG_INVALID_SCOPE (8004)
  Layer: IT

BT-EF-10: createEFConfig_invalidDataType_returns400
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: data_type not in STRING/NUMBER/BOOLEAN/DATE → 400
  Given: valid auth
  When: POST with data_type="ENUM"
  Then: HTTP 400; error code EF_CONFIG_INVALID_DATA_TYPE (8005)
  Layer: IT

BT-EF-11: createEFConfig_defaultsActive_andTimestamps
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: is_active defaults to true; created_on and updated_on populated UTC
  Given: valid POST body (no is_active field)
  When: POST succeeds
  Then: response.is_active=true; created_on and updated_on are valid UTC ISO-8601 strings
  Layer: IT

BT-EF-12: serviceCreate_maxCountExceeded_throwsEMFException8009
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-01
  AC: active EF count >= MAX_EF_COUNT_PER_PROGRAM → rejected
  Given: repository.countActiveByOrgIdAndProgramId returns 10; max configured as 10
  When: create() called
  Then: EMFException with statusCode=8009 thrown
  Layer: Unit

BT-EF-13: createEFConfig_orgIdFromAuth_notBody
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: org_id sourced from auth context (G-07.1); body org_id ignored
  Given: auth token for org 100; request body contains org_id=999
  When: POST
  Then: row created with org_id=100 (from token); org_id=999 ignored
  Layer: IT

BT-EF-14: updateEFConfig_validNameChange_returns200
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: PUT updates name; uniqueness re-validated
  Given: EF config id=5 with name="old_name"
  When: PUT /v3/extendedfields/config/5 with {name:"new_name"}
  Then: HTTP 200; response.name="new_name"; DB row updated
  Layer: IT

BT-EF-15: updateEFConfig_softDelete_returns200
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: is_active=false performs soft-delete; no physical DELETE — D-24
  Given: active EF config id=5
  When: PUT with {is_active:false}
  Then: HTTP 200; response.is_active=false; row still exists in DB with is_active=0
  Layer: IT

BT-EF-16: updateEFConfig_softDeleteIdempotent_returns200
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: is_active=false on already-inactive → 200 (idempotent)
  Given: EF config id=5 already inactive (is_active=0)
  When: PUT with {is_active:false}
  Then: HTTP 200; no error
  Layer: IT

BT-EF-17: updateEFConfig_notFound_returns404
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: non-existent id → 404 NOT FOUND
  Given: id=99999 does not exist for caller's org
  When: PUT /v3/extendedfields/config/99999
  Then: HTTP 404; error code EF_CONFIG_NOT_FOUND (8001)
  Layer: IT

BT-EF-18: updateEFConfig_wrongOrg_returns404
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: valid id but wrong org_id → 404 (cross-tenancy guard)
  Given: EF config id=5 belongs to org 100; caller authenticated as org 200
  When: PUT /v3/extendedfields/config/5
  Then: HTTP 404 (not 403 — do not leak existence)
  Layer: IT

BT-EF-19: updateEFConfig_duplicateNameOnRename_returns409
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: rename to existing name in same (org, program, scope) → 409 — D-30
  Given: EF configs "alpha" and "beta" exist for same org/program/scope
  When: PUT on "alpha" with {name:"beta"}
  Then: HTTP 409; error code EF_CONFIG_DUPLICATE_NAME (8002)
  Layer: IT

BT-EF-20: updateEFConfig_updatedOnRefreshed
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-02
  AC: last_updated_on advances on every successful PUT
  Given: EF config created at T0; wait T1 > T0
  When: PUT with any valid change
  Then: response.updated_on > created_on
  Layer: IT

BT-EF-21: listEFConfig_defaultReturnsActiveOnly
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-03
  AC: GET without includeInactive returns only is_active=1 records
  Given: 3 active + 2 inactive EF configs for org/program
  When: GET /v3/extendedfields/config?program_id=5001 (no includeInactive param)
  Then: HTTP 200; content has 3 items; no inactive records
  Layer: IT

BT-EF-22: listEFConfig_includeInactiveTrue_returnsAll
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-03
  AC: includeInactive=true returns active + inactive
  Given: 3 active + 2 inactive EF configs
  When: GET with includeInactive=true
  Then: HTTP 200; content has 5 items
  Layer: IT

BT-EF-23: listEFConfig_scopeFilter_returnsMatchingOnly
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-03
  AC: ?scope=SUBSCRIPTION_META filters correctly
  Given: EFs exist for SUBSCRIPTION_META and (hypothetical) other scopes
  When: GET with ?scope=SUBSCRIPTION_META
  Then: only SUBSCRIPTION_META records returned
  Layer: IT

BT-EF-24: listEFConfig_emptyOrg_returns200EmptyList
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-03
  AC: no EF configs → 200 with empty list (not 404)
  Given: org with no EF configs
  When: GET /v3/extendedfields/config?program_id=5001
  Then: HTTP 200; content=[]; totalElements=0
  Layer: IT

BT-EF-25: listEFConfig_pagination_respectsPageAndSize
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-03
  AC: page/size params respected; totalElements correct (G-04.2)
  Given: 15 active EF configs
  When: GET with page=0&size=5
  Then: content has 5 items; totalElements=15; totalPages=3
  Layer: IT

BT-EF-26: validateEF_onSubscriptionCreate_knownKeyValid
  Class: SubscriptionEFValidationIT
  Story: EF-US-05
  AC: key matches ACTIVE registry entry → EF accepted and persisted
  Given: ACTIVE EF config {name:"tier_label", data_type:"STRING"} in registry
  When: POST /v3/subscriptions with extendedFields=[{scope:"SUBSCRIPTION_META", key:"tier_label", value:"Gold"}]
  Then: subscription created; EF persisted in MongoDB
  Layer: IT

BT-EF-27: validateEF_onSubscriptionCreate_unknownKey_returns400
  Class: SubscriptionEFValidationIT
  Story: EF-US-05
  AC: key not in ACTIVE registry → 400 unknown field
  Given: no EF config named "unknown_field" in registry
  When: POST /v3/subscriptions with extendedFields=[{key:"unknown_field", value:"X"}]
  Then: HTTP 400; error code EF_VALIDATION_UNKNOWN_ID (8006) or equivalent
  Layer: IT

BT-EF-28: validateEF_onSubscriptionCreate_typeMismatch_returns400
  Class: SubscriptionEFValidationIT
  Story: EF-US-05
  AC: value fails data_type check → 400 type mismatch
  Given: EF config {name:"discount_pct", data_type:"NUMBER"} in registry
  When: POST with extendedFields=[{key:"discount_pct", value:"not-a-number"}]
  Then: HTTP 400; error code EF_VALIDATION_TYPE_MISMATCH (8007)
  Layer: IT

BT-EF-29: validateEF_onSubscriptionCreate_mandatoryMissing_returns400
  Class: SubscriptionEFValidationIT
  Story: EF-US-05
  AC: mandatory EF absent from submitted list → 400
  Given: ACTIVE mandatory EF config {name:"customer_segment", is_mandatory:true}
  When: POST /v3/subscriptions with extendedFields=[] (empty, mandatory field absent)
  Then: HTTP 400; error code EF_VALIDATION_MISSING_MANDATORY (8008)
  Layer: IT

BT-EF-30: validateEF_onSubscriptionCreate_nullEFWithMandatory_returns400
  Class: SubscriptionEFValidationIT
  Story: EF-US-05
  AC: extendedFields=null AND mandatory fields exist → 400
  Given: ACTIVE mandatory EF config exists for org/program
  When: POST /v3/subscriptions with no extendedFields key in body
  Then: HTTP 400; mandatory field validation triggered
  Layer: IT

BT-EF-31: validateEF_onSubscriptionCreate_validPersistedToMongo
  Class: SubscriptionEFValidationIT
  Story: EF-US-05
  AC: valid EFs persisted in subscription_programs.extendedFields
  Given: valid registry entry {id:1, name:"tier_label", data_type:"STRING"}
  When: POST with {scope:"SUBSCRIPTION_META", key:"tier_label", value:"Gold"} → success
  Then: MongoDB document contains extendedFields:[{efId:1, key:"tier_label", value:"Gold"}]
  Layer: IT

BT-EF-32: validateEF_onSubscriptionUpdate_nullPreservesExisting
  Class: SubscriptionEFValidationIT
  Story: EF-US-06
  AC: extendedFields=null on PUT → preserve existing values (R-33 null-guard)
  Given: subscription with existing extendedFields=[{efId:1, key:"tier_label", value:"Gold"}]
  When: PUT /v3/subscriptions/{id} with no extendedFields key
  Then: existing extendedFields unchanged in MongoDB
  Layer: IT

BT-EF-33: validateEF_onSubscriptionUpdate_emptyListClearsValues
  Class: SubscriptionEFValidationIT
  Story: EF-US-06
  AC: extendedFields=[] on PUT → clear all EF values
  Given: subscription with existing extendedFields=[{efId:1, key:"tier_label", value:"Gold"}]
  When: PUT with extendedFields=[]
  Then: subscription_programs.extendedFields becomes []
  Layer: IT

BT-EF-34: validateEF_onSubscriptionUpdate_sameRulesAsCreate
  Class: SubscriptionEFValidationIT
  Story: EF-US-06
  AC: PUT with EFs applies same validation as POST (unknown key, type mismatch, mandatory)
  Given: ACTIVE EF registry
  When: PUT with invalid EF entry (unknown key)
  Then: HTTP 400 (same error codes as create path)
  Layer: IT

BT-EF-35: serviceCreate_invalidOrgId_throwsEMFException8010
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-01
  AC: orgId <= 0 → EMFException 8010 (R-CT-05)
  Given: CreateLoyaltyExtendedFieldRequest with orgId=0
  When: service.create() called
  Then: EMFException thrown with statusCode=8010
  Layer: Unit

BT-EF-36: serviceCreate_blankName_throwsEMFException
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-01
  AC: blank/empty name rejected at service layer
  Given: request with name="  " (whitespace)
  When: service.create() called
  Then: EMFException thrown
  Layer: Unit

BT-EF-37: serviceUpdate_notFound_throwsEMFException8001
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-02
  AC: id not found for (id, orgId) → EMFException 8001
  Given: repository.findByPkIdAndPkOrgId returns Optional.empty()
  When: service.update() called
  Then: EMFException with statusCode=8001
  Layer: Unit

BT-EF-38: serviceUpdate_nameConflict_throwsEMFException8002
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-02
  AC: rename to already-used name → EMFException 8002 — D-30
  Given: existing entity found; new name conflicts (existsByPk... returns true)
  When: service.update() with conflicting name
  Then: EMFException with statusCode=8002
  Layer: Unit

BT-EF-39: serviceList_invalidOrgId_throwsEMFException8010
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-03
  AC: orgId <= 0 on list → EMFException 8010
  Given: orgId = -1
  When: service.list(-1, 5001, null, false, 0, 20) called
  Then: EMFException with statusCode=8010
  Layer: Unit

BT-EF-40: serviceList_nullScope_returnsAllScopes
  Class: LoyaltyExtendedFieldServiceImplTest
  Story: EF-US-03
  AC: scope=null → repository called with null scope (all scopes returned)
  Given: repository returns page with mixed scopes
  When: service.list(100, 5001, null, false, 0, 20)
  Then: repository.findByOrgIdAndProgramIdDynamic called with scope=null; all returned
  Layer: Unit

BT-EF-41: validatorTest_numberType_validAndInvalidValues
  Class: ExtendedFieldValidatorTest
  Story: EF-US-05
  AC: NUMBER data_type: parseable numeric string valid; non-numeric invalid
  Given: EF config with data_type=NUMBER
  When: validate("42") and validate("abc")
  Then: "42" passes; "abc" throws validation error (8007)
  Layer: Unit

BT-EF-42: validatorTest_booleanType_validAndInvalidValues
  Class: ExtendedFieldValidatorTest
  Story: EF-US-05
  AC: BOOLEAN: "true"/"false" valid; "yes"/"1" invalid
  Given: EF config with data_type=BOOLEAN
  When: validate("true"), validate("false"), validate("yes")
  Then: "true" and "false" pass; "yes" throws validation error (8007)
  Layer: Unit

BT-EF-43: validatorTest_dateType_validAndInvalidValues
  Class: ExtendedFieldValidatorTest
  Story: EF-US-05
  AC: DATE: ISO-8601 string valid; "22/04/2026" (dd/MM/yyyy) invalid
  Given: EF config with data_type=DATE
  When: validate("2026-04-22") and validate("22/04/2026")
  Then: ISO-8601 passes; dd/MM/yyyy throws validation error (8007)
  Layer: Unit

BT-EF-44: validatorTest_stringType_anyValueValid
  Class: ExtendedFieldValidatorTest
  Story: EF-US-05
  AC: STRING: any non-null value is valid (no format constraint)
  Given: EF config with data_type=STRING
  When: validate("anything@#$%") and validate("")
  Then: both pass validation (STRING imposes no format)
  Layer: Unit

BT-EF-45: createEFConfig_timestampsInUTC
  Class: LoyaltyExtendedFieldControllerIT
  Story: EF-US-01
  AC: created_on and updated_on returned as UTC ISO-8601 strings (G-01.1, G-01.6)
  Given: valid POST body
  When: POST succeeds
  Then: response.created_on and response.updated_on match pattern yyyy-MM-dd'T'HH:mm:ss'Z'
  Layer: IT
```

---

## AC Coverage Summary

| Story | ACs | Tests |
|-------|-----|-------|
| EF-US-01 | POST creates row; duplicate 409; invalid scope 400; invalid data_type 400; status defaults ACTIVE; timestamps UTC; returns id; max count | BT-EF-07,08,09,10,11,12,13,35,36,45 |
| EF-US-02 | name/isActive mutable; immutable fields rejected; rename uniqueness; soft-delete; idempotent; 404 on wrong org/id; updatedOn refreshed | BT-EF-14,15,16,17,18,19,20,37,38 |
| EF-US-03 | returns all for org; scope filter; includeInactive; paginated; empty=200 | BT-EF-21,22,23,24,25,39,40 |
| EF-US-05 | key matches ACTIVE registry; value type check; mandatory enforced; null+mandatory=400; persisted to MongoDB | BT-EF-26,27,28,29,30,31,41,42,43,44 |
| EF-US-06 | null preserves existing (R-33); empty list clears; same validation rules | BT-EF-32,33,34 |
| EF-US-07 | efId added; type deleted; key kept; value kept; legacy doc backward compat; ExtendedFieldType deleted | BT-EF-01,02,03,04,05,06 |

**Total: 45 business tests** | Unit: 17 | IT: 28
