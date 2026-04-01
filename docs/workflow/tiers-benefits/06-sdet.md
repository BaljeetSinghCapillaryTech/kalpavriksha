# 06 -- SDET: Test Plan & Automation Strategy

> Phase: SDET (06)
> Date: 2026-04-02
> Input: 04-qa.md, 05-developer.md, 03-designer.md, session-memory.md, GUARDRAILS.md
> Output feeds: 07-reviewer.md

---

## Summary

Test plan covering 215 QA scenarios across 17 unit test classes and 6 integration test classes. 178 scenarios are automated (unit + integration), 37 require manual or environment-specific execution. No production code is written in this phase -- all output is test planning, class structure, and CI commands.

---

## Cross-Reference: QA Scenarios vs Developer Implementation

### Gap Analysis

| QA Scenario | Status | Notes |
|-------------|--------|-------|
| `ReviewCommentValidatorTest` (C.3.2, C.3.3, C.3.7) | NO SEPARATE VALIDATOR | QA proposed a standalone `ReviewCommentValidatorTest`. Developer implemented reject-comment validation inline in `TierConfigService.review()` / `BenefitConfigService.review()`. Test coverage moves to `TierConfigServiceTest` and `BenefitConfigServiceTest`. Not a blocker -- functionality is implemented, just located differently. |
| A.2.2 / B.2.7 (maker-checker flag=false) | DEFERRED | Developer explicitly deferred maker-checker flag=false path ("always-on for this iteration"). These scenarios cannot be tested. |
| A.1.6 (filter by invalid status) | IMPLEMENTATION CLARIFICATION NEEDED | Developer does not document how invalid status filter is handled. Need to verify controller behavior -- likely Spring deserialization failure (400) or passthrough. |
| E.5 (tier references STOPPED benefit) | OPEN RISK | QA flagged this as needing clarification. `LinkedBenefitValidator` checks existence and same-program -- unclear if it also checks status. Must verify implementation before writing test. |
| H.3 (idempotency key expired after 5-min TTL) | MANUAL ONLY | Requires waiting > 5 minutes. Cannot be reliably automated in unit/integration tests without clock manipulation. |
| J.5/J.6 (empty/whitespace name) | ADJUSTED | QA says `@NotBlank` but Developer uses `@NotNull @Size(min=1)`. Whitespace-only ("   ") will PASS validation (Size counts chars, not trimmed). Flag as behavioral difference. |

### Blocker Assessment

**No blocking gaps found.** All critical scenarios from QA (CRUD, maker-checker lifecycle, versioning, cross-entity validation, distributed lock, idempotency) have corresponding implementations in the Developer output. The deferred maker-checker flag=false path was an intentional scope decision.

---

## Test Plan: Automated vs Manual Split

### Automated: 178 scenarios

| Layer | Test Location | Framework | Scenario Count |
|-------|--------------|-----------|----------------|
| Unit tests | `pointsengine-emf-ut/src/test/java/` | JUnit 4 + Mockito Inline 4.6.1 | 144 |
| Integration tests | `integration-test/src/test/java/` | JUnit 4 + Spring Test 4.3.30 + BaseIntegrationTest | 34 |

### Manual: 37 scenarios

| Category | Scenarios | Reason |
|----------|-----------|--------|
| Maker-checker flag=false | A.2.2, A.3.3, B.2.7 | Deferred from implementation |
| Idempotency TTL expiry | H.3 | Requires 5-min wait |
| Security/injection exploratory | I.1-I.8 | Best validated with manual exploratory testing or dedicated security scanner |
| Missing header behavior | F.4 | Depends on LoggerInterceptor error handling -- integration environment needed |
| Rate limiting | Not implemented | G-03.7 flagged as gap -- no endpoint rate limiting in scope |
| Concurrent create same name | J.15, G.1-G.3 | Partially automated in integration concurrency test; manual verification for true production-like race conditions |
| Full E2E multi-step | K.1-K.5 | Can be partially automated in integration tests; full E2E requires running service |

---

## Unit Test Classes (pointsengine-emf-ut)

All unit tests follow the established pattern:
- `@RunWith(MockitoJUnitRunner.class)`
- `@Mock` for dependencies, `@InjectMocks` for SUT
- `@Before` for common setup
- JUnit 4 assertions: `assertEquals`, `assertNotNull`, `assertTrue`, `assertFalse`
- Test naming: `test<MethodName>_<Scenario>`
- Package: `com.capillary.shopbook.pointsengine.RESTEndpoint` (matching source structure)

---

### UT-01: ConfigStatusTransitionValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.config`
**SUT**: `ConfigStatusTransitionValidator`
**QA Scenarios**: C.1.3-C.1.6, C.4.1-C.4.15

**Mock Setup**: None required -- pure enum/state-machine logic, no dependencies.

**Test Methods (22)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidTransition_DraftToPendingApproval` | C.1.1 | Returns valid result |
| 2 | `testValidTransition_PendingApprovalToActive` | C.2.1 | Returns valid |
| 3 | `testValidTransition_PendingApprovalToDraft` | C.3.1 (reject) | Returns valid |
| 4 | `testValidTransition_ActiveToPaused` | C.4.2 | Returns valid |
| 5 | `testValidTransition_ActiveToStopped` | C.4.1 | Returns valid |
| 6 | `testValidTransition_PausedToActive` | C.4.3 | Returns valid |
| 7 | `testValidTransition_PausedToStopped` | C.4.10 | Returns valid |
| 8 | `testInvalidTransition_ActiveToPendingApproval` | C.4.12 | Returns error |
| 9 | `testInvalidTransition_DraftToActive` | C.4.13 | Returns error |
| 10 | `testInvalidTransition_DraftToPaused` | C.4.14 | Returns error |
| 11 | `testInvalidTransition_DraftToStopped` | C.4.15 | Returns error |
| 12 | `testInvalidTransition_StoppedToActive` | C.4.4 | Returns error |
| 13 | `testInvalidTransition_StoppedToPaused` | C.4.5 | Returns error |
| 14 | `testInvalidTransition_StoppedToPendingApproval` | C.4.6 | Returns error |
| 15 | `testInvalidTransition_SnapshotToAnything` | C.4.11 | All transitions from SNAPSHOT return error |
| 16 | `testInvalidTransition_ActiveToActive` | Self-transition | Returns error |
| 17 | `testInvalidTransition_ActiveToDraft` | Backward | Returns error |
| 18 | `testSubmitFromActive` | C.1.3 | Returns error |
| 19 | `testSubmitFromPendingApproval` | C.1.4 | Returns error |
| 20 | `testSubmitFromStopped` | C.1.5 | Returns error |
| 21 | `testSubmitFromSnapshot` | C.1.6 | Returns error |
| 22 | `testAllEnumValuesCovered` | G-02.7 | Every ConfigStatus has at least one valid or explicitly invalid transition defined |

**Key Assertions**:
- `ConfigValidationResult.isValid()` for valid transitions
- `ConfigValidationResult.getErrors().get(0).getCode()` equals `"INVALID_STATUS_TRANSITION"` for invalid

---

### UT-02: TierValidatorFactoryTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.factory`
**SUT**: `TierValidatorFactory`
**QA Scenarios**: Validator chain correctness

**Mock Setup**: All individual validators `@Mock`-ed. `@InjectMocks TierValidatorFactory`.

**Test Methods (4)**:

| # | Method | Assertion |
|---|--------|-----------|
| 1 | `testGetValidators_CreateTier` | Returns ordered list of [StatusEditableValidator, TierNameUniquenessValidator, EligibilityThresholdValidator, SerialNumberValidator, DowngradeTargetValidator, LinkedBenefitValidator] |
| 2 | `testGetValidators_UpdateTier` | Returns same set (or subset if different) |
| 3 | `testGetValidators_NullType` | Throws or returns empty list |
| 4 | `testValidatorOrder_CreateTier` | StatusEditable is first (fail-fast on non-editable status) |

---

### UT-03: BenefitValidatorFactoryTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.factory`
**SUT**: `BenefitValidatorFactory`

**Test Methods (3)**:

| # | Method | Assertion |
|---|--------|-----------|
| 1 | `testGetValidators_CreateBenefit` | Returns [StatusEditableValidator, BenefitNameUniquenessValidator, BenefitTypeParameterValidator, LinkedTierValidator] |
| 2 | `testGetValidators_UpdateBenefit` | Returns expected chain |
| 3 | `testValidatorOrder` | StatusEditable first |

---

### UT-04: TierNameUniquenessValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.tier`
**SUT**: `TierNameUniquenessValidator`
**QA Scenarios**: A.2.18, A.2.19, A.2.20

**Mock Setup**:
- `@Mock TierConfigDao tierConfigDao`
- Stub `tierConfigDao.count(orgId, filter)` to return 0 or 1

**Test Methods (5)**:

| # | Method | Scenario | Setup | Assertion |
|---|--------|----------|-------|-----------|
| 1 | `testValidate_UniqueNameInProgram` | A.2.19 | `count()` returns 0 | Valid result |
| 2 | `testValidate_DuplicateNameInSameProgram` | A.2.18 | `count()` returns 1 | Error: field="name", code="DUPLICATE" |
| 3 | `testValidate_DuplicateNameButSnapshot` | A.2.20 | `count()` returns 0 (filter excludes SNAPSHOT) | Valid result |
| 4 | `testValidate_SameNameDifferentProgram` | A.2.19 | `count()` returns 0 (orgId+programId scoped) | Valid result |
| 5 | `testValidate_SameNameOnUpdate_ExcludesSelf` | Update existing tier | `count()` returns 0 (filter excludes own ID) | Valid result |

---

### UT-05: EligibilityThresholdValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.tier`
**SUT**: `EligibilityThresholdValidator`
**QA Scenarios**: A.2.4, A.2.5, A.2.10, A.2.11, A.2.12, A.2.21, A.2.22

**Mock Setup**: None -- pure validation logic on TierConfig fields.

**Test Methods (9)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_MissingKpiType` | A.2.4 | Error on "eligibility.kpiType" |
| 2 | `testValidate_MissingThreshold` | A.2.5 | Error on "eligibility.threshold" |
| 3 | `testValidate_NegativeThreshold` | A.2.10 | Error: "must be positive" |
| 4 | `testValidate_ZeroThreshold` | A.2.11 | Error: "must be positive" |
| 5 | `testValidate_VeryLargeThreshold` | A.2.12 | Valid result |
| 6 | `testValidate_InvalidKpiType` | A.2.21 | Error on kpiType |
| 7 | `testValidate_CurrentPoints` | A.2.22 | Valid |
| 8 | `testValidate_LifetimePoints` | A.2.22 | Valid |
| 9 | `testValidate_LifetimePurchases` | A.2.22 | Valid |

---

### UT-06: DowngradeTargetValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.tier`
**SUT**: `DowngradeTargetValidator`
**QA Scenarios**: A.2.13, A.2.14, A.2.15

**Mock Setup**:
- `@Mock TierConfigDao tierConfigDao`

**Test Methods (4)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_TargetExists` | Happy path | Valid |
| 2 | `testValidate_TargetNotFound` | A.2.13 | Error: "downgrade.targetTierId not found" |
| 3 | `testValidate_TargetInDifferentProgram` | A.2.14 | Error: "cross-program reference" |
| 4 | `testValidate_TargetNone` | A.2.15 | Valid (no target = base tier) |

---

### UT-07: LinkedBenefitValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.tier`
**SUT**: `LinkedBenefitValidator`
**QA Scenarios**: A.2.16, A.2.17, A.2.34, A.2.35, E.1, E.4

**Mock Setup**:
- `@Mock BenefitConfigDao benefitConfigDao`

**Test Methods (6)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_BenefitExists` | Happy path | Valid |
| 2 | `testValidate_BenefitNotFound` | A.2.16, E.1 | Error per missing benefit |
| 3 | `testValidate_BenefitDifferentProgram` | A.2.17, E.4 | Error: "cross-program" |
| 4 | `testValidate_EmptyLinkedBenefits` | A.2.34 | Valid (empty list OK) |
| 5 | `testValidate_NullLinkedBenefits` | A.2.35 | Valid (null OK) |
| 6 | `testValidate_MultipleBenefits_OneMissing` | Mixed | Error only for missing one |

---

### UT-08: SerialNumberValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.tier`
**SUT**: `SerialNumberValidator`
**QA Scenarios**: A.2.8, A.3.9

**Mock Setup**:
- `@Mock TierConfigDao tierConfigDao`

**Test Methods (4)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_UniqueSerialNumber` | Happy path | Valid |
| 2 | `testValidate_DuplicateSerialNumber` | A.3.9 | Error on "serialNumber" |
| 3 | `testValidate_MissingSerialNumber` | A.2.8 | Error: REQUIRED |
| 4 | `testValidate_UpdateExcludesSelf` | Update scenario | Valid (excludes own ID) |

---

### UT-09: BenefitTypeParameterValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.benefit`
**SUT**: `BenefitTypeParameterValidator`
**QA Scenarios**: B.2.11-B.2.15, B.2.21

**Mock Setup**: None -- pure validation logic.

**Test Methods (10)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_PointsMultiplier_Valid` | B.2.1 | Valid |
| 2 | `testValidate_PointsMultiplier_Zero` | B.2.11 | Error: "multiplier must be > 0" |
| 3 | `testValidate_PointsMultiplier_Negative` | B.2.12 | Error |
| 4 | `testValidate_PointsMultiplier_MissingMultiplier` | B.2.13 | Error |
| 5 | `testValidate_FlatPointsAward_ZeroPoints` | B.2.14 | Error |
| 6 | `testValidate_FlatPointsAward_MissingPoints` | B.2.15 | Error |
| 7 | `testValidate_CouponIssuance_Valid` | B.2.3 | Valid |
| 8 | `testValidate_BadgeAward_Valid` | B.2.4 | Valid |
| 9 | `testValidate_FreeShipping_Valid` | B.2.5 | Valid |
| 10 | `testValidate_Custom_EmptyParams` | J.17 | Valid |

---

### UT-10: LinkedTierValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.benefit`
**SUT**: `LinkedTierValidator`
**QA Scenarios**: B.2.9, B.2.10, E.2, E.3

**Mock Setup**:
- `@Mock TierConfigDao tierConfigDao`

**Test Methods (5)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_TierExists` | Happy path | Valid |
| 2 | `testValidate_TierNotFound` | B.2.9, E.2 | Error |
| 3 | `testValidate_TierDifferentProgram` | B.2.10, E.3 | Error |
| 4 | `testValidate_NoLinkedTiers` | B.2.23 | Valid |
| 5 | `testValidate_MultipleTiers` | B.2.24 | Valid (all exist) |

---

### UT-11: BenefitNameUniquenessValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.benefit`
**SUT**: `BenefitNameUniquenessValidator`
**QA Scenarios**: B.2.8

**Mock Setup**:
- `@Mock BenefitConfigDao benefitConfigDao`

**Test Methods (3)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testValidate_UniqueName` | Happy path | Valid |
| 2 | `testValidate_DuplicateName` | B.2.8 | Error: "DUPLICATE" |
| 3 | `testValidate_UpdateExcludesSelf` | Update | Valid |

---

### UT-12: VersioningHelperTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
**SUT**: `VersioningHelper`
**QA Scenarios**: D.1-D.9

**Mock Setup**: None -- pure logic on ConfigBaseDocument fields.

**Test Methods (10)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testCreateDraftFromActive_NewDocument` | D.1 | New doc has parentId=active._id, version=active.version+1, status=DRAFT |
| 2 | `testCreateDraftFromActive_PreservesEntityId` | D.8 | entityId (tierId/benefitId) is copied, not regenerated |
| 3 | `testApproveNew_SetsActive` | C.2.1 | Status -> ACTIVE, parentId stays null |
| 4 | `testApproveEdit_DraftBecomesActive` | C.2.2 | Draft status -> ACTIVE |
| 5 | `testApproveEdit_ParentBecomesSnapshot` | C.2.2 | Parent status -> SNAPSHOT |
| 6 | `testReject_SetsBackToDraft` | C.3.1 | Status -> DRAFT |
| 7 | `testReject_PreservesParentIdAndVersion` | C.3.5, D.6 | parentId and version unchanged |
| 8 | `testReject_StoresComment` | C.3.1 | Comment field set |
| 9 | `testApproveEdit_VersionPersists` | D.7 | v3 draft has version=3, parentId=v2._id |
| 10 | `testEntityId_ImmutableAcrossVersions` | D.8, D.9 | entityId same across all versions |

---

### UT-13: TierConfigServiceTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
**SUT**: `TierConfigService`
**QA Scenarios**: A.2.1, A.2.27, A.2.28, A.3.1-A.3.10, C.1.1, C.1.7-C.1.8, C.2.1-C.2.3, C.2.6-C.2.9, C.3.1-C.3.7, C.5.1, C.5.3-C.5.10

**Mock Setup**:
- `@Mock TierConfigDao tierConfigDao`
- `@Mock BenefitConfigDao benefitConfigDao` (for cross-entity in linked benefits)
- `@Mock TierValidatorFactory tierValidatorFactory`
- `@Mock VersioningHelper versioningHelper`
- `@Mock ConfigStatusTransitionValidator statusTransitionValidator`
- `@Mock IdempotencyKeyGuard idempotencyKeyGuard`
- `@Mock ConfigDiffComputer configDiffComputer`
- `@Mock ShardContext shardContext` (static mock via `MockedStatic`)

**Test Methods (30)**:

| # | Method | Scenario | Key Assertion |
|---|--------|----------|---------------|
| 1 | `testCreateTier_HappyPath` | A.2.1 | `tierConfigDao.save()` called, status=DRAFT, version=1 |
| 2 | `testCreateTier_ResponseFields` | A.2.27 | Response has tierId, version, status, createdOn |
| 3 | `testCreateTier_TimestampsUtc` | A.2.28, G-01 | `createdOn` is Instant (UTC) |
| 4 | `testCreateTier_ValidationFails` | A.2.36 | Throws ConfigValidationException, DAO not called |
| 5 | `testUpdateDraft_InPlace` | A.3.1 | `replace()` called on same document |
| 6 | `testUpdateActive_CreatesDraft` | A.3.2 | `versioningHelper.createDraftFromActive()` called |
| 7 | `testUpdateActive_ExistingDraft` | A.3.4 | Existing DRAFT updated, no new document |
| 8 | `testUpdate_PendingApproval` | A.3.5 | Throws ConfigConflictException |
| 9 | `testUpdate_Stopped` | A.3.6 | Throws ConfigConflictException |
| 10 | `testUpdate_Snapshot` | A.3.7 | Throws ConfigConflictException |
| 11 | `testUpdate_NotFound` | A.3.10 | Returns 404 / throws |
| 12 | `testSubmit_DraftToPending` | C.1.1 | Status updated to PENDING_APPROVAL |
| 13 | `testSubmit_WithReason` | C.1.7 | Comments field populated |
| 14 | `testSubmit_WithoutReason` | C.1.8 | Success, comments null |
| 15 | `testApproveNew` | C.2.1 | `versioningHelper.approveNew()` called |
| 16 | `testApproveEdit` | C.2.2 | Draft -> ACTIVE, parent -> SNAPSHOT |
| 17 | `testApproveWithComment` | C.2.3 | Comment stored |
| 18 | `testApprove_NonPending` | C.2.6 | Throws ConfigConflictException |
| 19 | `testApprove_Active` | C.2.7 | Throws ConfigConflictException |
| 20 | `testApprove_Stopped` | C.2.8 | Throws ConfigConflictException |
| 21 | `testApproveAndQuery` | C.2.9 | After approve, findOne returns ACTIVE |
| 22 | `testRejectWithComment` | C.3.1 | PENDING -> DRAFT, comment stored |
| 23 | `testReject_NoComment` | C.3.2 | Throws ConfigValidationException |
| 24 | `testReject_EmptyComment` | C.3.3 | Throws ConfigValidationException |
| 25 | `testReject_CommentMaxLength` | C.3.7 | 151 chars -> throws |
| 26 | `testReject_PreservesFields` | C.3.5 | parentId and version unchanged |
| 27 | `testListApprovals` | C.5.1 | Returns PENDING_APPROVAL tiers |
| 28 | `testListApprovals_IncludesDiff` | C.5.4 | ConfigDiffComputer called for edit approvals |
| 29 | `testListApprovals_OrgScoped` | C.5.9 | Query uses orgId from ShardContext |
| 30 | `testListApprovals_NoPending` | C.5.10 | Returns empty list |

---

### UT-14: BenefitConfigServiceTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
**SUT**: `BenefitConfigService`
**QA Scenarios**: B.2.1-B.2.25, B.3.1-B.3.8

**Mock Setup**: Mirror of TierConfigServiceTest with `BenefitConfigDao`, `BenefitValidatorFactory`, etc.

**Test Methods (18)**:

| # | Method | Scenario | Key Assertion |
|---|--------|----------|---------------|
| 1 | `testCreateBenefit_HappyPath` | B.2.1 | DRAFT, version=1 |
| 2 | `testCreateBenefit_AllTypes` | B.2.1-B.2.6 | Each BenefitType accepted |
| 3 | `testCreateBenefit_DuplicateName` | B.2.8 | ValidationException |
| 4 | `testCreateBenefit_MissingName` | B.2.16 | ValidationException |
| 5 | `testCreateBenefit_MissingType` | B.2.17 | ValidationException |
| 6 | `testCreateBenefit_MissingCategory` | B.2.18 | ValidationException |
| 7 | `testCreateBenefit_MissingTriggerEvent` | B.2.19 | ValidationException |
| 8 | `testCreateBenefit_MissingProgramId` | B.2.20 | ValidationException |
| 9 | `testCreateBenefit_InvalidType` | B.2.21 | ValidationException |
| 10 | `testCreateBenefit_ResponseFields` | B.2.22 | All fields present |
| 11 | `testCreateBenefit_ZeroLinkedTiers` | B.2.23 | Success |
| 12 | `testCreateBenefit_MultipleLinkedTiers` | B.2.24 | Success |
| 13 | `testUpdateDraft` | B.3.1 | In-place update |
| 14 | `testUpdateActive_CreatesDraft` | B.3.2 | New DRAFT with parentId |
| 15 | `testUpdateActive_ExistingDraft` | B.3.3 | Existing DRAFT updated |
| 16 | `testUpdate_PendingApproval` | B.3.4 | ConfigConflictException |
| 17 | `testUpdate_Stopped` | B.3.5 | ConfigConflictException |
| 18 | `testUpdate_Snapshot` | B.3.6 | ConfigConflictException |

---

### UT-15: DistributedLockAspectTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
**SUT**: `DistributedLockAspect`
**QA Scenarios**: G.4, G.5, G.6

**Mock Setup**:
- `@Mock RedisTemplate<String, String> redisTemplate`
- `@Mock ValueOperations<String, String> valueOperations`
- `@Mock ProceedingJoinPoint joinPoint`

**Test Methods (6)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testAcquireLock_Success` | Happy path | `setIfAbsent()` returns true, `joinPoint.proceed()` called |
| 2 | `testAcquireLock_AlreadyHeld` | G.4 | `setIfAbsent()` returns false, throws ConfigConflictException |
| 3 | `testLockReleased_AfterSuccess` | G.5 | `redisTemplate.delete(key)` called in finally |
| 4 | `testLockReleased_OnException` | G.6 | Exception thrown, `delete(key)` still called |
| 5 | `testLockKey_SpelEvaluation` | SpEL | Lock key correctly resolves `#orgId + ':' + #entityId` |
| 6 | `testExpire_CalledAfterSetIfAbsent` | Two-step pattern | `expire()` called with correct TTL after `setIfAbsent()` |

---

### UT-16: IdempotencyKeyGuardTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
**SUT**: `IdempotencyKeyGuard`
**QA Scenarios**: H.1, H.2, H.4, H.5

**Mock Setup**:
- `@Mock RedisTemplate<String, String> redisTemplate`
- `@Mock ValueOperations<String, String> valueOperations`

**Test Methods (5)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testCheck_NewKey` | H.2 | `setIfAbsent()` returns true -> proceed |
| 2 | `testCheck_DuplicateKey` | H.1 | `setIfAbsent()` returns false -> returns cached response / throws |
| 3 | `testCheck_NullKey` | No header | Proceeds without idempotency check |
| 4 | `testCheck_EmptyKey` | Empty header | Proceeds without idempotency check |
| 5 | `testTtl_SetTo5Minutes` | TTL verification | `expire()` called with 5 min / 300 seconds |

---

### UT-17: ConfigDiffComputerTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
**SUT**: `ConfigDiffComputer`
**QA Scenarios**: C.5.4, C.5.7, C.5.8

**Mock Setup**: None -- pure logic using Jackson ObjectMapper.

**Test Methods (7)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testComputeDiff_NameChanged` | Simple field change | FieldDiff("name", "Gold", "Platinum") |
| 2 | `testComputeDiff_ThresholdChanged` | Nested field change | FieldDiff("eligibility.threshold", "1000", "2000") |
| 3 | `testComputeDiff_NoDifference` | Identical documents | Empty diff list |
| 4 | `testComputeDiff_FieldAdded` | New field in draft | FieldDiff with old=null |
| 5 | `testComputeDiff_FieldRemoved` | Field null in draft | FieldDiff with new=null |
| 6 | `testComputeDiff_SystemFieldsExcluded` | _id, createdOn, lastModifiedOn differ | Not in diff result |
| 7 | `testComputeDiff_LinkedBenefitsChanged` | Array field change | Correct FieldDiff paths |

---

### UT-18: GlobalExceptionHandlerTest (Extend Existing)

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Exceptions`
**SUT**: `GlobalExceptionHandler`
**QA Scenarios**: New exception types

Add to existing test file:

| # | Method | Assertion |
|---|--------|-----------|
| 1 | `testHandleConfigConflictException` | Returns 409 CONFLICT with error message |
| 2 | `testHandleConfigValidationException` | Returns 422 with ConfigValidationResult body |
| 3 | `testHandleConfigValidationException_MultipleErrors` | Returns 422 with all field errors |

---

### UT-19: StatusEditableValidatorTest

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.config`
**SUT**: `StatusEditableValidator`
**QA Scenarios**: A.3.5-A.3.7, B.3.4-B.3.6

**Mock Setup**: None -- pure logic on ConfigStatus.

**Test Methods (6)**:

| # | Method | Assertion |
|---|--------|-----------|
| 1 | `testValidate_DraftIsEditable` | Valid |
| 2 | `testValidate_ActiveIsEditable` | Valid (creates draft) |
| 3 | `testValidate_PendingApprovalNotEditable` | Error |
| 4 | `testValidate_StoppedNotEditable` | Error |
| 5 | `testValidate_SnapshotNotEditable` | Error |
| 6 | `testValidate_PausedIsEditable` | Clarify -- if PAUSED tiers can be edited |

---

## Integration Test Classes (integration-test)

All integration tests follow:
- `extends BaseIntegrationTest`
- `@RunWith(SpringJUnit4ClassRunner.class)`
- `@ContextConfiguration(classes = {IntegrationStarterConfig.class})`
- Real MongoDB via test infrastructure
- `@After` cleanup via `orgConfigManager.resetConfigToFirstSnapshot()`

---

### IT-01: TierConfigControllerTest

**Package**: `com.capillary.shopbook.test.emf.config`
**QA Scenarios**: A.1.1-A.1.13, A.2.1, A.2.27, K.1, K.2

**Setup**:
- Set `ShardContext` with test orgId
- Create test program in MongoDB
- Use `MockMvc` or direct controller invocation

**Test Methods (12)**:

| # | Method | Scenario |
|---|--------|----------|
| 1 | `testListTiers_HappyPath` | A.1.1: 3 tiers returned ordered by serialNumber |
| 2 | `testListTiers_FilterByStatus` | A.1.4, A.1.5: status filter works |
| 3 | `testListTiers_Pagination` | A.1.10, A.1.11: offset/limit respected |
| 4 | `testListTiers_EmptyProgram` | A.1.9: empty list, not null |
| 5 | `testListTiers_SnapshotExcluded` | A.1.12: SNAPSHOT not in default results |
| 6 | `testListTiers_IncludeDraftDetails` | A.1.7, A.1.8: draftDetails populated/null |
| 7 | `testListTiers_TimestampsIso8601` | A.1.13, G-01.6: UTC ISO-8601 format |
| 8 | `testCreateTier_FullIntegration` | A.2.1: POST -> verify in DB |
| 9 | `testCreateTier_BeanValidation` | A.2.3-A.2.8: missing required fields -> 422 |
| 10 | `testFullLifecycle_NewTier` | K.1: create -> submit -> approve |
| 11 | `testFullLifecycle_EditTier` | K.2: active -> edit -> submit -> approve -> verify SNAPSHOT |
| 12 | `testFullLifecycle_RejectResubmit` | K.3: reject -> edit -> resubmit -> approve |

---

### IT-02: BenefitConfigControllerTest

**Package**: `com.capillary.shopbook.test.emf.config`
**QA Scenarios**: B.1.1-B.1.11, B.2.1, K.4

**Test Methods (8)**:

| # | Method | Scenario |
|---|--------|----------|
| 1 | `testListBenefits_HappyPath` | B.1.1 |
| 2 | `testListBenefits_FilterByType` | B.1.5 |
| 3 | `testListBenefits_FilterByCategory` | B.1.6 |
| 4 | `testListBenefits_FilterByLinkedTierId` | B.1.8 |
| 5 | `testListBenefits_CombinedFilters` | B.1.11 |
| 6 | `testListBenefits_EmptyProgram` | B.1.10 |
| 7 | `testCreateBenefit_FullIntegration` | B.2.1 |
| 8 | `testFullLifecycle_Benefit` | K.4: create -> submit -> approve -> pause -> resume -> stop |

---

### IT-03: TierConfigDaoImplTest

**Package**: `com.capillary.shopbook.test.emf.config`
**QA Scenarios**: DAO layer verification

**Test Methods (8)**:

| # | Method | Assertion |
|---|--------|-----------|
| 1 | `testSave_AndFindOne` | Roundtrip save/retrieve |
| 2 | `testFind_WithFilter` | Bson filter correctly applied |
| 3 | `testFind_WithPagination` | Offset/limit work |
| 4 | `testReplace_UpdatesDocument` | Existing doc replaced |
| 5 | `testCount_ByProgramId` | Count matches |
| 6 | `testUpdate_StatusField` | Partial update works |
| 7 | `testIndexes_Exist` | @PostConstruct created compound indexes |
| 8 | `testFind_OrgIdScoped` | Query with orgId=100 does not return orgId=200 data |

---

### IT-04: BenefitConfigDaoImplTest

**Package**: `com.capillary.shopbook.test.emf.config`
**QA Scenarios**: DAO layer verification

**Test Methods (7)**: Mirror of TierConfigDaoImplTest for benefits, plus:

| # | Method | Assertion |
|---|--------|-----------|
| 1-6 | (same as IT-03 pattern) | Basic CRUD operations |
| 7 | `testFind_ByLinkedTierId` | Index on `linkedTiers.tierId` works |

---

### IT-05: TierBenefitTenantIsolationTest (G-07.4, G-11.8)

**Package**: `com.capillary.shopbook.test.emf.config`
**QA Scenarios**: F.1-F.6, E.6

**Test Methods (7)**:

| # | Method | Scenario | Assertion |
|---|--------|----------|-----------|
| 1 | `testTier_CreateOrgA_QueryOrgB` | F.1 | Org B query returns empty |
| 2 | `testBenefit_CreateOrgA_QueryOrgB` | F.2 | Org B query returns empty |
| 3 | `testCrossOrgTierReference` | F.3, E.6 | Validation error (tier not found) |
| 4 | `testApprovals_OrgScoped` | F.5 | Org B sees no approvals from org A |
| 5 | `testStatusChange_OrgScoped` | F.6 | Org B cannot change org A tier status |
| 6 | `testTierDao_OrgIdFilter` | G-07.1 | DAO query always includes orgId |
| 7 | `testBenefitDao_OrgIdFilter` | G-07.1 | Same for benefit DAO |

---

### IT-06: TierConfigConcurrencyTest (G-10, G-11.5)

**Package**: `com.capillary.shopbook.test.emf.config`
**QA Scenarios**: G.1-G.6

**Test Methods (4)**:

| # | Method | Scenario | Setup | Assertion |
|---|--------|----------|-------|-----------|
| 1 | `testConcurrentApprove` | G.1 | ExecutorService 2 threads, CountDownLatch | One 200, one 409 |
| 2 | `testConcurrentSubmit` | G.2 | Same pattern | One succeeds |
| 3 | `testLockReleasedAfterCompletion` | G.5 | Approve, then immediately submit new change | Second op succeeds |
| 4 | `testLockReleasedOnException` | G.6 | Force failure mid-approval | Subsequent op succeeds |

---

## Guardrail-Specific Test Coverage Mapping

| Guardrail | Test Coverage | Test Class(es) |
|-----------|--------------|-----------------|
| **G-01.7** (Multi-timezone) | Timestamps stored as `Instant.now()` (UTC). Verify serialization as ISO-8601 with Z suffix. | IT-01 (testListTiers_TimestampsIso8601), UT-13 (testCreateTier_TimestampsUtc) |
| **G-02.7** (Default case in switch) | All ConfigStatus enum values covered in state machine. | UT-01 (testAllEnumValuesCovered) |
| **G-06.1** (Idempotency) | POST create endpoints check X-Idempotency-Key. | UT-16 (full class), H.1-H.5 |
| **G-07.4** (Tenant isolation) | Create as org A, query as org B, assert empty. | IT-05 (full class), F.1-F.6 |
| **G-10** (Concurrent access) | Distributed lock on status change/review. Concurrent threads test. | UT-15 (full class), IT-06 (full class) |
| **G-11.5** (Concurrent access test) | CountDownLatch + ExecutorService pattern. | IT-06 |
| **G-11.6** (Failure scenarios) | Lock released on exception, Redis unavailable handling. | UT-15 (testLockReleased_OnException) |
| **G-11.7** (Timezone 3+ zones) | Not directly applicable -- no timezone-dependent business logic. All storage is UTC Instant. Verify serialization only. | IT-01 (testListTiers_TimestampsIso8601) |
| **G-11.8** (Tenant isolation) | Same as G-07.4. | IT-05 |
| **G-12.7** (Tests test behavior) | All service tests assert business outcomes (status changes, document state), not just mock verification. | All UT classes |

### Guardrail Gaps (No Automated Coverage)

| Guardrail | Gap | Reason |
|-----------|-----|--------|
| G-03.7 (Rate limiting) | No rate limiting implemented on config endpoints | Out of scope -- internal APIs |
| G-11.6 (Redis down scenario) | Redis connection failure not tested | Requires infrastructure mocking (Testcontainers with Redis shutdown) -- recommend as follow-up |
| G-01.7 (IST/NPT/Eastern offsets) | No timezone-specific business logic to test | Tier/benefit configs store UTC Instants only; presentation-layer conversion is not in scope |

---

## CI/Local Run Commands

### Unit Tests

```bash
# Run all new tier/benefit config unit tests
mvn test -pl emf-parent/pointsengine-emf-ut \
  -Dtest="ConfigStatusTransitionValidatorTest,TierValidatorFactoryTest,BenefitValidatorFactoryTest,TierNameUniquenessValidatorTest,EligibilityThresholdValidatorTest,DowngradeTargetValidatorTest,LinkedBenefitValidatorTest,SerialNumberValidatorTest,BenefitTypeParameterValidatorTest,LinkedTierValidatorTest,BenefitNameUniquenessValidatorTest,VersioningHelperTest,TierConfigServiceTest,BenefitConfigServiceTest,DistributedLockAspectTest,IdempotencyKeyGuardTest,ConfigDiffComputerTest,StatusEditableValidatorTest" \
  -am

# Run only validator tests
mvn test -pl emf-parent/pointsengine-emf-ut \
  -Dtest="*ValidatorTest,*ValidatorFactoryTest" \
  -am

# Run only service tests
mvn test -pl emf-parent/pointsengine-emf-ut \
  -Dtest="TierConfigServiceTest,BenefitConfigServiceTest" \
  -am
```

### Integration Tests

```bash
# Run all new config integration tests
mvn test -pl emf-parent/integration-test \
  -Dtest="TierConfigControllerTest,BenefitConfigControllerTest,TierConfigDaoImplTest,BenefitConfigDaoImplTest,TierBenefitTenantIsolationTest,TierConfigConcurrencyTest" \
  -am

# Run tenant isolation test only
mvn test -pl emf-parent/integration-test \
  -Dtest="TierBenefitTenantIsolationTest" \
  -am
```

### Full Suite (Existing + New)

```bash
# Compile all and run full unit test suite (verifies no regressions)
mvn test -pl emf-parent/pointsengine-emf-ut -am

# Full integration test suite
mvn test -pl emf-parent/integration-test -am
```

---

## Manual Test Steps

### M-01: Maker-Checker Flag=False Path (A.2.2, A.3.3, B.2.7)

> **Status**: Cannot test -- implementation deferred.

1. When flag=false path is implemented:
   - POST /api/v1/tiers with maker-checker disabled for program
   - **Expected**: Status=ACTIVE directly (no DRAFT)
   - PUT /api/v1/tiers/{id} on ACTIVE with flag=false
   - **Expected**: In-place update of ACTIVE document

### M-02: Idempotency Key TTL Expiry (H.3)

1. POST /api/v1/tiers with `X-Idempotency-Key: test-key-ttl`
2. **Expected**: 201 Created
3. Wait > 5 minutes
4. POST /api/v1/tiers with same `X-Idempotency-Key: test-key-ttl`
5. **Expected**: 201 Created (new tier, not duplicate response)
6. Verify 2 distinct tier documents in MongoDB

### M-03: Missing X-CAP-ORG-ID Header (F.4)

1. Send GET /api/v1/tiers?programId=P1 without X-CAP-ORG-ID header
2. **Expected**: Error response (likely 400 or 500 depending on LoggerInterceptor null handling)
3. Verify no data leak -- response must not contain any tier data

### M-04: Security Exploratory Testing (I.1-I.8)

1. **NoSQL injection in name**: POST /tiers with `name: {"$gt": ""}` -- verify stored as literal string
2. **NoSQL injection in filter**: GET /tiers?status={"$ne": null} -- verify 400 or treated as literal
3. **XSS in name**: POST /tiers with `name: "<script>alert(1)</script>"` -- verify stored as-is (no execution risk on backend)
4. **Long input**: POST /tiers with `name: <10000 chars>` -- verify 422 from @Size validation
5. **Comment injection**: POST /tiers/{id}/review with comment containing newlines, special chars -- verify @Size(max=150) enforcement

### M-05: Whitespace-Only Name (J.5, J.6)

1. POST /api/v1/tiers with `name: "   "` (3 spaces)
2. **Expected behavior under current implementation**: 201 Created (passes @NotNull @Size(min=1))
3. **Note**: This is a behavioral difference from QA expectation (@NotBlank). If trimmed-empty names should be rejected, a custom validator or @Pattern annotation is needed.
4. POST /api/v1/tiers with `name: ""`
5. **Expected**: 422 from @Size(min=1)

### M-06: Concurrent Create with Same Name (J.15)

1. Use 2 parallel HTTP clients or curl commands
2. Both POST /api/v1/tiers with `name: "Gold"` simultaneously
3. **Expected**: One succeeds (201), one gets 422 (duplicate name)
4. **Risk**: Both may succeed if uniqueness is application-level only (no DB unique index on name). Verify MongoDB index includes name uniqueness constraint.

### M-07: Full E2E Multi-Step (K.1-K.5)

1. **K.1**: POST create tier -> verify DRAFT -> PUT status PENDING_APPROVAL -> POST review APPROVE -> GET verify ACTIVE
2. **K.2**: Start with ACTIVE v1 -> PUT update (creates DRAFT v2) -> submit -> approve -> verify v1 is SNAPSHOT, v2 is ACTIVE
3. **K.3**: DRAFT -> submit -> reject (with comment) -> PUT update -> resubmit -> approve -> verify ACTIVE
4. **K.4**: Create benefit -> submit -> approve -> pause -> resume -> stop -> verify STOPPED is terminal
5. **K.5**: Create Tier A and Tier B both as DRAFT -> submit both -> approve A -> approve B independently

---

## Test Data Factories

For consistency across tests, create shared test data builders:

### TierConfigTestBuilder

```java
// Location: pointsengine-emf-ut/.../config/TierConfigTestBuilder.java
public class TierConfigTestBuilder {
    public static TierConfig defaultDraft(Integer orgId, String programId) {
        TierConfig tc = new TierConfig();
        tc.setOrgId(orgId);
        tc.setProgramId(programId);
        tc.setEntityId(UUID.randomUUID().toString());
        tc.setName("Gold");
        tc.setSerialNumber(1);
        tc.setStatus(ConfigStatus.DRAFT);
        tc.setVersion(1);
        // ... set required sub-objects (eligibility, validity, downgrade)
        return tc;
    }
    // Variants: defaultActive(), defaultPending(), withLinkedBenefits(), etc.
}
```

### BenefitConfigTestBuilder

```java
// Same pattern for BenefitConfig
public class BenefitConfigTestBuilder {
    public static BenefitConfig defaultDraft(Integer orgId, String programId) { ... }
}
```

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| New unit test classes | 19 (17 new + 2 extended) |
| New integration test classes | 6 |
| Total automated test methods | ~178 |
| Manual test procedures | 7 (covering 37 scenarios) |
| QA scenarios mapped to automated | 178/215 (83%) |
| QA scenarios requiring manual | 37/215 (17%) |
| Guardrails with automated coverage | 9/12 |
| Guardrails without coverage (justified) | 3 (G-03.7 not implemented, G-01.7/G-11.7 not applicable) |
| Blockers | 0 |
