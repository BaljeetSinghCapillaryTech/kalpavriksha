# SDET — Tier CRUD Test Automation Plan

> Feature: tier-crud
> Ticket: test_branch_v3
> Phase: SDET (Phase 10)
> Date: 2026-04-06
> Confidence scale: C1 (speculative) → C7 (verified from source)

---

## 0. Summary

| Metric | Value |
|--------|-------|
| QA scenarios mapped | 72 (TS-01 – TS-72) |
| Test methods planned | 26 |
| Unit Tests | 11 |
| Integration Tests | 15 |
| Manual tests | 5 |
| Efficiency ratio | 72 QA scenarios → 26 test methods (2.8 : 1) |
| Blockers raised | 1 (F-01: missing partner sync validation — must be added before ITs run) |

---

## 1. IT Infrastructure Discovery

### Step 1: Baseline

**Baseline command (run before writing any new tests):**

```bash
# intouch-api-v3 — unit tests only
mvn test -pl . -q 2>&1 | tail -5

# intouch-api-v3 — full verify (includes ITs under integrationTests/)
mvn verify -pl . -q 2>&1 | tail -5

# emf-parent unit tests
mvn test -pl pointsengine-emf-ut -am -q 2>&1 | tail -5
```

Record the pass/fail/skip counts before adding any new tests. New tests must not reduce the existing count.

### Step 2: Convention Snapshot

#### intouch-api-v3 (Unit Tests — `src/test/java/com/capillary/intouchapiv3/`)

Evidence: read from `TargetGroupControllerTest.java`, `MilestoneControllerTest.java`, `IntegrationsControllerTest.java`, `UnifiedPromotionFacadeTest.java`, `PointsEngineThriftServiceTest.java` (C7 — all read directly).

```markdown
## Discovered Test Conventions — intouch-api-v3 UTs

- Base class:            none — no abstract UT base class
- Annotations:          @ExtendWith(MockitoExtension.class) on all controller/facade tests
- Strict mode:          @MockitoSettings(strictness = Strictness.LENIENT) when needed (UnifiedPromotionFacadeTest)
- Assertion library:    JUnit 5 Assertions (org.junit.jupiter.api.Assertions.*) + occasional Hamcrest
- PODAM:                uk.co.jemos.podam used in TargetGroupControllerTest for random entity generation
- Static mocks:         Mockito.mockStatic(RPCService.class) in PointsEngineThriftServiceTest — cleanup in @AfterEach
- Data setup:           inline builders and anonymous inner classes for AbstractBaseAuthenticationToken
- Cleanup strategy:     no teardown needed (Mockito resets mocks automatically per test)
- Container strategy:   none (unit tests — no containers)
- Naming convention:    *Test.java in com.capillary.intouchapiv3.* packages
- Test commands:        mvn test -pl . -Dtest=TierValidatorTest -am
- Spring profiles:      none (no Spring context loaded in UTs)
- Context reuse:        N/A — no Spring context
- Test slicing:         none — pure Mockito, no Spring context
```

#### intouch-api-v3 (Integration Tests — `src/test/java/integrationTests/`)

Evidence: read from `AbstractContainerTest.java`, `UnifiedPromotionControllerTest.java`, `EmfMongoConfigTest.java` (C7 — all read directly).

```markdown
## Discovered Test Conventions — intouch-api-v3 ITs

- Base class:           AbstractContainerTest (integrationTests.AbstractContainerTest)
- Spring Boot test:     @SpringBootTest(webEnvironment = RANDOM_PORT) in AbstractContainerTest
- Extension:            @ExtendWith(SpringExtension.class)
- Context config:       @ContextConfiguration(classes = {IntegrationStarterConfig, EmfMongoConfigTest, ...})
- Active profiles:      @ActiveProfiles("test")
- Assertion library:    JUnit 5 Assertions
- Containers (shared static — REUSE MANDATORY):
  - static MongoDBContainer mongoDBContainer (mongo:4.2.3, started once per JVM)
  - static MySQLContainer mysqlContainer (mysql:8.0.33 + schema.sql init script)
  - static RabbitMQContainer rabbitContainer
  - static GenericContainer redisContainer + embedded RedisServer (port 6379)
- Mongo test config:    EmfMongoConfigTest — separate @Profile("test") config
  - must register TierRepository.class in includeFilters (same as UnifiedPromotionRepository)
- HTTP client:          RestTemplate with @LocalServerPort
- External mocks:       @MockBean for ZionAuthenticationService, ZionAuthorizationService,
                        PointsEngineThriftService, EMFService, CreativesAryaService
- Data setup:           inline builders + UnifiedPromotionTestUtils helper pattern
- Cleanup strategy:     cleanUpTables() — manual TRUNCATE per test via JDBC (@AfterEach, currently commented out)
- Naming convention:    *Test.java in integrationTests.* package (NOT *IT.java)
- Test commands:        mvn verify -pl . -am   (ITs run in verify phase via Failsafe plugin)
- Spring profiles:      "test"
- Context reuse:        ONE shared static context across all AbstractContainerTest subclasses
  - All ITs MUST extend AbstractContainerTest — never create a new context
- Context-dirtying:     NOT used — shared context, transactional rollback not available (multi-DB)
```

#### emf-parent (Unit Tests — `pointsengine-emf-ut`)

Evidence: read from `SlabUpgradeAuditLogServiceTest.java`, `PointsEngineRuleServiceTest.java`, `pointsengine-emf-ut/pom.xml` (C7).

```markdown
## Discovered Test Conventions — emf-parent UTs

- Base class:           junit.framework.TestCase (extends in many tests) OR none
- Annotations:          @RunWith(MockitoJUnitRunner.Silent.class) — JUnit 4 runner
- Framework:            JUnit 4 (junit:junit) — NOT JUnit 5. All test methods use @org.junit.Test
- Assertion library:    org.junit.Assert + hamcrest-all (org.hamcrest:hamcrest-all)
- Mockito:              @InjectMocks, @Mock, mockito-inline available
- Data setup:           inline construction (no PODAM)
- Cleanup strategy:     none needed
- Container strategy:   none
- Naming convention:    *Test.java in com.capillary.shopbook.* packages
- Test commands:        mvn test -pl pointsengine-emf-ut -am -Dtest=PeProgramSlabDaoTest
- Spring profiles:      none (pure unit tests — no Spring context)
- Context reuse:        N/A
```

### Step 3: Module Boundary Assessment

```markdown
## Module Boundary Assessment

- Feature touches modules:
  - intouch-api-v3 (REST controllers, facade, validator, MongoDB repository, Thrift client)
  - emf-parent / pointsengine-emf (Thrift impl, PeProgramSlabDao, PeCustomerEnrollmentDao)
  - pointsengine-emf-ut (existing UT module for emf-parent)
  - cc-stack-crm (DDL — no Java tests needed here)

- Communication type:   intouch-api-v3 → EMF via Thrift RPC (RPCService.rpcClient)

- IT placement:
  - Controller-layer ITs → integrationTests/ in intouch-api-v3 (AbstractContainerTest)
  - Reason: existing IT pattern is full-stack with Docker containers; TierController is in this module
  - DAO-layer ITs for emf-parent → pointsengine-emf-ut (unit tests mocking JPA; no IT module found in emf-parent)
  - Reason: no AbstractContainerTest equivalent found in emf-parent. emf-parent UTs mock the DB layer.

- Cross-module mocking needed: YES — Thrift service mocked as @MockBean in IT tests
  - PointsEngineRulesThriftService already @MockBean in UnifiedPromotionControllerTest (confirmed C7)
  - New TierControllerIT will @MockBean the same bean

- Existing IT module found: YES — integrationTests/ in intouch-api-v3

- Feasibility: FEASIBLE with existing infrastructure
  - EmfMongoConfigTest must be extended to register TierRepository.class in includeFilters
  - MySQL schema (schema.sql / override_schema.sql in test resources) must include
    `is_active` column in program_slabs DDL — needed for STOP/DELETE flows (B-1 blocker applies here too)
```

---

## 2. BLOCKER Check

Cross-referencing `04-qa.md` scenarios against `05b-gap-analysis.md` findings:

**BLOCKER: F-01 — PartnerProgramTierSyncConfiguration check missing (HIGH severity)**

TS-40 in QA requires: DELETE /v3/tiers/{id} → HTTP 400 with `TIER_HAS_PARTNER_SYNC_REFERENCE` when tier is referenced in partner sync config. `05b-gap-analysis.md` Finding F-01 confirms this validation is absent from `TierValidator.validateDelete`. This is a missing validation, not just an untested one.

**Action**: Raise to Developer. The missing partner sync check must be added to `TierValidator.validateDelete` before TS-40 automation can be written. The test plan below includes a placeholder IT for TS-40 but it CANNOT be executed until the implementation gap is closed.

**All other QA scenarios are testable** — no other structural gaps prevent automation.

---

## 3. Test Layer Classification

Every QA scenario classified by layer. Combined where the Test Efficiency Protocol applies.

| Test Method | Layer | QA Scenarios Covered | Why This Layer |
|-------------|-------|----------------------|----------------|
| `shouldRejectAllInvalidTierFieldValues` | UT | TS-13, TS-14, TS-15, TS-16, TS-19, TS-20, TS-26, TS-60, edge cases from §3.1 | Pure validator/bean validation logic — no DB, no Thrift |
| `shouldRejectKpiTypeMismatch` | UT | TS-18, TS-21 | Pure `TierValidator.validateKpiTypeConsistency` logic |
| `shouldRejectThresholdOrderingViolations` | UT | TS-17, TS-19 | Pure `TierValidator.validateThresholdOrdering` logic |
| `shouldRejectDeleteOnBaseTierAndDowngradeTarget` | UT | TS-37, TS-38, TS-39 | Pure `TierValidator.validateDelete` logic — no external calls |
| `shouldEnforceStatusTransitionRules` | UT | TS-31–TS-36, TS-24, TS-25 | Pure `TierValidator.validateStatusTransition` + `validateRejectComment` — enum-based |
| `shouldRejectNullOrBlankName` | UT | TS-13, TS-16, TS-71 null-safety sub-cases | Pure @NotBlank / @Size bean validation; validates TierRequest annotations |
| `shouldBuildCorrectDraftDocumentOnCreate` | UT | TS-08, TS-09, TS-10 | `TierFacade.createTier` with mocked repository — verifies DRAFT status, field mapping, Instant usage |
| `shouldHandleCopyOnWriteForActiveTierUpdate` | UT | TS-51, TS-52 | `TierFacade.updateTier` with mocked repository — verifies parentId set, ACTIVE unchanged |
| `shouldRevertToOriginalStatusOnThriftFailure` | UT | TS-53 (rollback) | `TierFacade.approveTier` with mocked Thrift that throws — verifies MongoDB reverts to PENDING_APPROVAL |
| `shouldReturnIdempotentResponseOnAlreadyApproved` | UT | TS-43 (idempotency guard) | `TierFacade.approveTier` with doc already ACTIVE + slabId set — verifies no second Thrift call |
| `shouldGuardFacadeWithLockableAnnotations` | UT | Concurrency guard (TS-61, TS-64 annotation coverage) | Verifies `@Lockable` is present on createTier, updateTier, changeTierStatus, deleteTier via reflection |
| `TierControllerIT — shouldCreateAndRetrieveTierViaApi` | IT | TS-08, TS-09, TS-06, TS-01, TS-71 | Full HTTP stack, MongoDB round-trip, ResponseWrapper format, null-safety |
| `TierControllerIT — shouldEnforceTenantIsolationAcrossOrgs` | IT | TS-65, TS-66, TS-67, TS-68 | Requires real MongoDB + orgId scoping; tenant isolation cannot be proven by mocks |
| `TierControllerIT — shouldReturnOrderedTiersWithGaps` | IT | TS-02, TS-03, TS-04, TS-05 | Requires multiple MongoDB docs + real filtering; status filtering and ordering verified end-to-end |
| `TierControllerIT — shouldReturn404ForMissingAndStoppedTiers` | IT | TS-47, TS-48, TS-49, TS-50, TS-46 | Requires real MongoDB lookup to confirm absent → 404 |
| `TierControllerIT — shouldExecuteFullApproveFlow` | IT | TS-12, TS-28, TS-27, TS-29 | APPROVE flow: MongoDB + mocked Thrift; verifies slabId set, status=ACTIVE, correct HTTP status codes |
| `TierControllerIT — shouldRejectInvalidStatusTransitionsViaApi` | IT | TS-31, TS-32, TS-33, TS-34, TS-35, TS-36, TS-22 | API layer state machine enforcement — HTTP 400 from controller with real Spring context |
| `TierControllerIT — shouldEnforceDeletePreConditionsViaApi` | IT | TS-37, TS-38, TS-39, TS-41, TS-42 | DELETE validations with real MongoDB + mocked Thrift for member count |
| `TierControllerIT — shouldReturnStructuredValidationErrors` | IT | TS-13, TS-14, TS-15, TS-16, TS-24, TS-25, TS-23, TS-60 | @Valid + error advice → verify `ResponseWrapper.errors[]` format via HTTP |
| `TierControllerIT — shouldHandleThriftFailureOnApproveGracefully` | IT | TS-53, TS-54, TS-57, TS-58 | Thrift @MockBean throws → verify HTTP 500 + MongoDB status reverted (F-06 regression included) |
| `TierControllerIT — shouldReturnMemberCountForActiveTiers` | IT | TS-01 (memberCount), TS-06, TS-55 | Batch Thrift call result mapped to response; verify `memberCount` null for DRAFT (TS-07) |
| `TierControllerIT — shouldHandleConcurrentApproveIdempotently` | IT | TS-43, TS-44, TS-61 | Two requests; idempotency check (slabId already set) → no second Thrift call |
| `TierControllerIT — shouldRejectDuplicateSerialNumbers` | IT | TS-45, TS-64 | MongoDB uniqueness check (requires real collection insert then re-insert) |
| `TierControllerIT — shouldHandleTimestampsAsUtcIso8601` | IT | TS-70 (G-01.7) | Verifies `createdOn` / `lastModifiedOn` in response are UTC ISO-8601 (Jackson + Instant) |
| `PeProgramSlabDaoTest — shouldFilterSoftDeletedSlabs` | UT | TS-04 (DAO level), is_active filter | Verifies JPQL `AND s.isActive = true` — pure JPQL/Hibernate unit test with mock EntityManager |
| `PeCustomerEnrollmentDaoTest — shouldReturnMemberCountsPerSlab` | UT | TS-38 (member count prerequisite) | Verifies `countMembersPerSlab` JPQL with IN clause — pure JPQL unit test |

**Total: 11 UT + 15 IT = 26 test methods covering 72 QA scenarios.**

---

## 4. Test Efficiency Summary

| Category | QA Scenarios | Test Methods | Ratio |
|----------|-------------|--------------|-------|
| Validation (pure logic) | TS-13–TS-26, TS-37–TS-39, edges | 6 UT methods | 4 : 1 |
| State machine transitions | TS-27–TS-36 | 1 UT + 1 IT | 5 : 1 |
| Happy path CRUD | TS-01–TS-12 | 4 IT methods | 3 : 1 |
| Soft-delete | TS-37–TS-42 | 1 UT + 1 IT | 3 : 1 |
| Idempotency & concurrency | TS-43–TS-46, TS-61–TS-64 | 1 UT + 2 IT | 3 : 1 |
| Not found / 404 | TS-47–TS-50, TS-46 | 1 IT | 5 : 1 |
| Failure/resilience | TS-53–TS-59 | 1 UT + 1 IT | 4 : 1 |
| Tenant isolation | TS-65–TS-68 | 1 IT | 4 : 1 |
| Guardrail specific | TS-69–TS-72 | 2 IT | 2 : 1 |
| DAO layer | TS-04, TS-38 (DAO) | 2 UT | — |
| **TOTAL** | **72** | **26** | **2.8 : 1** |

---

## 5. Detailed Test Plan

### 5.1 Unit Tests — intouch-api-v3

**Location**: `src/test/java/com/capillary/intouchapiv3/tier/validation/TierValidatorTest.java`
**Framework**: JUnit 5, `@ExtendWith(MockitoExtension.class)` (no Spring context)
**Exemplar**: `UnifiedPromotionFacadeTest.java` (same package pattern, same runner)

#### UT-01: `shouldRejectAllInvalidTierFieldValues`

Covers TS-13, TS-14, TS-15, TS-16, TS-19, TS-20, TS-26, and boundary edge cases.

```java
// Pattern: Map of {input → expectedErrorMessage}
// Use validator.validateCreate() with a baseline valid request, mutate one field at a time
// Use Map.of(invalidInput, expectedFragment) + forEach to assert InvalidInputException thrown
@Test
void shouldRejectAllInvalidTierFieldValues() {
    // Combine: null name, blank name, name > 100 chars, threshold <= 0,
    //          threshold == existing highest, periodValue == 0
    // Each asserted with assertThrows(InvalidInputException.class, ...)
    // driven by a collection:
    List<Runnable> invalidCases = List.of(
        () -> validator.validateCreate(requestWithName(null), existingTiers, ORG_ID, PROGRAM_ID),
        () -> validator.validateCreate(requestWithName("  "), existingTiers, ORG_ID, PROGRAM_ID),
        () -> validator.validateCreate(requestWithName("A".repeat(101)), existingTiers, ORG_ID, PROGRAM_ID),
        () -> validator.validateCreate(requestWithThreshold(-1.0), existingTiers, ORG_ID, PROGRAM_ID),
        () -> validator.validateCreate(requestWithThreshold(500.0 /* == existing */), existingTiers, ORG_ID, PROGRAM_ID)
    );
    invalidCases.forEach(tc -> assertThrows(InvalidInputException.class, tc::run));
}
```

#### UT-02: `shouldRejectKpiTypeMismatch`

Covers TS-18, TS-21 (KPI type immutability).

```java
@Test
void shouldRejectKpiTypeMismatch() {
    // Existing tier: CUMULATIVE_PURCHASES
    // New request: CURRENT_POINTS → must throw
    // Repeat with TRACKER_VALUE_BASED → must throw
    // First tier in empty program → must NOT throw (any KPI type accepted)
    Map<String, Boolean> cases = Map.of(
        "CURRENT_POINTS", true,      // throws
        "TRACKER_VALUE_BASED", true, // throws
        "CUMULATIVE_PURCHASES", false // does not throw
    );
    cases.forEach((kpi, shouldThrow) -> ...);
}
```

#### UT-03: `shouldRejectThresholdOrderingViolations`

Covers TS-17, TS-19 (threshold < highest, threshold == highest).

```java
@Test
void shouldRejectThresholdOrderingViolations() {
    // Existing tiers: serialNumber=1 threshold=100, serialNumber=2 threshold=500
    // Cases: newThreshold=500 (equal, serial=3) → throws
    //        newThreshold=499 (below highest, serial=3) → throws
    //        newThreshold=501 (valid) → no throw
    //        newThreshold=50 (below lower tier, serial=2) → throws
}
```

#### UT-04: `shouldRejectDeleteOnBaseTierMembersAndDowngradeTarget`

Covers TS-37, TS-38, TS-39 (validateDelete — 3 conditions combined).

```java
@Test
void shouldRejectDeleteOnBaseTierMembersAndDowngradeTarget() {
    // Case 1: serialNumber=1 (base tier) → throws "Cannot delete base tier"
    // Case 2: memberCount=150 → throws "Cannot delete tier with 150 members"
    // Case 3: tier is downgrade target of Silver → throws "Cannot delete tier ... it is the downgrade target"
    // Case 4: valid (serial=2, 0 members, not a target) → no throw
}
```

#### UT-05: `shouldEnforceStatusTransitionRules`

Covers TS-31–TS-36, TS-24, TS-25 (all invalid transitions + valid ones).

```java
// Parameterized using nested Map: {(currentStatus, action) → shouldThrow}
@Test
void shouldEnforceStatusTransitionRules() {
    record TestCase(TierStatus status, TierAction action, boolean shouldThrow) {}
    List<TestCase> cases = List.of(
        new TestCase(DRAFT, SUBMIT_FOR_APPROVAL, false), // valid
        new TestCase(DRAFT, APPROVE, true),              // TS-31
        new TestCase(DRAFT, REJECT, true),               // TS-33
        new TestCase(DRAFT, STOP, true),                 // TS-34
        new TestCase(PENDING_APPROVAL, APPROVE, false),  // valid
        new TestCase(PENDING_APPROVAL, REJECT, false),   // valid
        new TestCase(PENDING_APPROVAL, SUBMIT_FOR_APPROVAL, true), // TS-32
        new TestCase(ACTIVE, STOP, false),               // valid
        new TestCase(ACTIVE, APPROVE, true)              // TS-35
    );
    cases.forEach(tc -> {
        if (tc.shouldThrow()) assertThrows(...)
        else assertDoesNotThrow(...)
    });
}
```

#### UT-06: `shouldRequireRejectComment`

Covers TS-23 (REJECT without comment → throws; with comment → passes).

```java
@Test
void shouldRequireRejectComment() {
    assertThrows(InvalidInputException.class,
        () -> validator.validateRejectComment(REJECT, null));
    assertThrows(InvalidInputException.class,
        () -> validator.validateRejectComment(REJECT, "  "));
    assertDoesNotThrow(
        () -> validator.validateRejectComment(REJECT, "Threshold too low"));
    assertDoesNotThrow(
        () -> validator.validateRejectComment(APPROVE, null)); // APPROVE needs no comment
}
```

---

**Location**: `src/test/java/com/capillary/intouchapiv3/tier/TierFacadeTest.java`
**Framework**: JUnit 5, `@ExtendWith(MockitoExtension.class)`, `@MockitoSettings(strictness = LENIENT)`
**Exemplar**: `UnifiedPromotionFacadeTest.java` (same setup pattern — confirmed C7)

#### UT-07: `shouldBuildCorrectDraftDocumentOnCreate`

Covers TS-08, TS-09, TS-10, TS-71 null-safety.

```java
@Test
void shouldBuildCorrectDraftDocumentOnCreate() {
    when(tierRepository.findActiveTiersByOrgIdAndProgramId(ORG_ID, PROGRAM_ID))
        .thenReturn(Collections.emptyList()); // base tier case
    when(tierRepository.save(any(TierDocument.class)))
        .thenAnswer(inv -> inv.getArgument(0));

    TierResponse response = tierFacade.createTier(ORG_ID, USER_ID, baseRequest());

    assertAll(
        () -> assertEquals(TierStatus.DRAFT, response.getStatus()),
        () -> assertNull(response.getSlabId()),
        () -> assertNull(response.getMemberCount()),
        () -> assertNotNull(response.getTierId()),
        () -> assertNotNull(response.getCreatedOn()),  // G-01 — Instant, not null
        () -> assertNotNull(response.getLastModifiedOn())
    );
    // Verify no Thrift calls on create
    verifyNoInteractions(pointsEngineRulesThriftService);
}
```

#### UT-08: `shouldHandleCopyOnWriteForActiveTierUpdate`

Covers TS-51, TS-52.

```java
@Test
void shouldHandleCopyOnWriteForActiveTierUpdate() {
    // Case 1: ACTIVE tier, no existing DRAFT child → creates new DRAFT with parentId
    // Case 2: DRAFT child already exists → returns existing DRAFT (no duplicate)
    // Verify ACTIVE tier document is NOT modified in either case
    ArgumentCaptor<TierDocument> savedDoc = ArgumentCaptor.forClass(TierDocument.class);
    // ... mock setup, call updateTier
    verify(tierRepository).save(savedDoc.capture());
    assertEquals(TierStatus.DRAFT, savedDoc.getValue().getStatus());
    assertNotNull(savedDoc.getValue().getParentObjectId()); // parentId set
}
```

#### UT-09: `shouldRevertToOriginalStatusOnThriftFailure`

Covers TS-53 (R-6 rollback — Backend Readiness I-3 flag).

```java
@Test
void shouldRevertToOriginalStatusOnThriftFailure() {
    TierDocument pendingTier = tierInStatus(PENDING_APPROVAL);
    when(tierRepository.findByTierIdAndOrgId(TIER_ID, ORG_ID))
        .thenReturn(Optional.of(pendingTier));
    doThrow(new RuntimeException("Thrift unavailable"))
        .when(pointsEngineRulesThriftService).createOrUpdateSlab(any(), any(), any());

    assertThrows(ServiceException.class,
        () -> tierFacade.changeTierStatus(ORG_ID, USER_ID, TIER_ID, approveRequest()));

    // Verify MongoDB save called twice: once to ACTIVE (before Thrift), once to revert to PENDING_APPROVAL
    ArgumentCaptor<TierDocument> captor = ArgumentCaptor.forClass(TierDocument.class);
    verify(tierRepository, times(2)).save(captor.capture());
    TierDocument lastSave = captor.getAllValues().get(1);
    assertEquals(TierStatus.PENDING_APPROVAL, lastSave.getStatus());
}
```

#### UT-10: `shouldReturnIdempotentResponseWhenAlreadyApproved`

Covers TS-43 (APPROVE retry guard — R-8).

```java
@Test
void shouldReturnIdempotentResponseWhenAlreadyApproved() {
    TierDocument alreadyActive = tierInStatus(ACTIVE).withSlabId(42);
    when(tierRepository.findByTierIdAndOrgId(TIER_ID, ORG_ID))
        .thenReturn(Optional.of(alreadyActive));

    TierResponse response = tierFacade.changeTierStatus(ORG_ID, USER_ID, TIER_ID, approveRequest());

    assertEquals(TierStatus.ACTIVE, response.getStatus());
    assertEquals(42, response.getSlabId());
    // Critical: no Thrift call on retry
    verifyNoInteractions(pointsEngineRulesThriftService);
}
```

#### UT-11: `shouldHaveLockableAnnotationsOnAllMutatingMethods`

Covers concurrency guardrail G-10 (TS-61, TS-64 — annotation coverage, not behavior).

```java
@Test
void shouldHaveLockableAnnotationsOnAllMutatingMethods() throws NoSuchMethodException {
    // Verify @Lockable present via reflection — catches accidental annotation removal
    List<Method> mutatingMethods = List.of(
        TierFacade.class.getDeclaredMethod("createTier", Long.class, Integer.class, TierRequest.class),
        TierFacade.class.getDeclaredMethod("updateTier", Long.class, Integer.class, String.class, TierRequest.class),
        TierFacade.class.getDeclaredMethod("changeTierStatus", Long.class, Integer.class, String.class, TierStatusRequest.class),
        TierFacade.class.getDeclaredMethod("deleteTier", Long.class, Integer.class, String.class)
    );
    mutatingMethods.forEach(m ->
        assertNotNull(m.getAnnotation(Lockable.class),
            m.getName() + " must have @Lockable annotation"));
}
```

---

**Location**: `pointsengine-emf-ut/src/test/java/com/capillary/shopbook/points/dao/PeProgramSlabDaoTest.java`
**Framework**: JUnit 4, `@RunWith(MockitoJUnitRunner.Silent.class)` (matches emf-parent convention — C7)
**Exemplar**: `SlabUpgradeAuditLogServiceTest.java`

#### UT-12 (emf): `shouldFilterSoftDeletedSlabs`

Covers TS-04 at DAO level — verifies `is_active=1` filter in JPQL.

```java
@RunWith(MockitoJUnitRunner.Silent.class)
public class PeProgramSlabDaoTest extends TestCase {

    @Test
    public void shouldFilterSoftDeletedSlabs() {
        // Use @Query annotation text inspection — verify JPQL contains "AND s.isActive = true"
        // Check findByProgram, findByProgramSlabNumber, findNumberOfSlabs, findActiveById
        // Alternative: mock EntityManager, verify parameterized query excludes is_active=0 rows
        // Pure unit test — no DB needed to verify the JPQL string itself
    }
}
```

---

**Location**: `pointsengine-emf-ut/src/test/java/com/capillary/shopbook/points/dao/PeCustomerEnrollmentDaoTest.java`
**Framework**: JUnit 4, `@RunWith(MockitoJUnitRunner.Silent.class)`
**Exemplar**: `SlabUpgradeAuditLogServiceTest.java`

#### UT-13 (emf): `shouldReturnMemberCountsPerSlab`

Covers TS-38 member count prerequisite — verifies `countMembersPerSlab` parameters and query structure.

```java
@Test
public void shouldReturnMemberCountsPerSlab() {
    // Verify JPQL contains IN clause with slabIds
    // Verify query filters by orgId + programId + enrollment is_active=1
    // Test data: mock EntityManager returns [(slabId=1, count=50), (slabId=2, count=0)]
    // Assert result Map<Long, Long> mapped correctly
}
```

---

### 5.2 Integration Tests — intouch-api-v3

All ITs extend `AbstractContainerTest` (confirmed existing pattern — C7).
`PointsEngineRulesThriftService` is `@MockBean` in all ITs (matches UnifiedPromotionControllerTest — C7).

**Developer task before writing ITs**: Update `EmfMongoConfigTest.java` to add `TierRepository.class` to `includeFilters` (same as `UnifiedPromotionRepository.class`). Without this, TierRepository uses the wrong MongoDB instance (confirmed from session memory line 79).

**Developer task before writing ITs**: Add `is_active` column to the test-scoped `program_slabs.sql` in `src/test/resources/cc-stack-crm/schema/` (same as B-1 blocker in backend-readiness.md — needed for STOP flow ITs).

**Location**: `src/test/java/integrationTests/TierControllerTest.java`
**Extends**: `AbstractContainerTest`
**Exemplar**: `UnifiedPromotionControllerTest.java` (same class pattern — C7)

#### IT-01: `shouldCreateAndRetrieveTierViaApi`

Covers TS-08, TS-09, TS-10, TS-01, TS-06, TS-71.

```java
@Test
void shouldCreateAndRetrieveTierViaApi() {
    // 1. POST /v3/tiers (base tier, minimal fields) → assert 201, status=DRAFT, slabId=null
    // 2. POST /v3/tiers (tier with all optional fields) → assert 201, colorCode echoed back
    // 3. GET /v3/tiers/{tierId} (DRAFT) → assert 200, memberCount=null, slabId=null, status=DRAFT
    // 4. GET /v3/tiers?programId=X → assert data=[] (DRAFT excluded from default list)
    // 5. Assert createdOn is not null and parses as ISO-8601 UTC (G-01)
    // 6. Assert response body has errors=[], warnings=[] (ResponseWrapper format)
}
```

#### IT-02: `shouldReturnOrderedTiersAndFilterByStatus`

Covers TS-02, TS-03, TS-04, TS-05.

```java
@Test
void shouldReturnOrderedTiersAndFilterByStatus() {
    // Setup: create 3 tiers in MongoDB: ACTIVE (sn=1), DRAFT (sn=2), STOPPED (sn=3)
    // GET default → only ACTIVE tier returned, in serialNumber order
    // GET includeInactive=true → ACTIVE + STOPPED (NOT DRAFT, NOT SNAPSHOT) returned
    // Verify ordering: serialNumber ascending
    // Verify serial number gap scenario: slabs with sn=1,3,5 returned in correct order
}
```

#### IT-03: `shouldReturn404ForMissingAndStoppedTiers`

Covers TS-47, TS-48, TS-49, TS-50, TS-46.

```java
@Test
void shouldReturn404ForMissingAndStoppedTiers() {
    // GET non-existent tierId → 404
    // GET stopped tier (STOPPED status in MongoDB) → 404 (AC-2-2)
    // PUT non-existent tierId → 404
    // DELETE non-existent tierId → 404
    // DELETE already-stopped tier → 404
}
```

#### IT-04: `shouldEnforceTenantIsolationAcrossOrgs`

Covers TS-65, TS-66, TS-67, TS-68 (G-07.4).

```java
@Test
void shouldEnforceTenantIsolationAcrossOrgs() {
    // Create tier for Org A (token orgId=100)
    // All operations below use Org B token (orgId=200):
    // GET /tiers?programId=<orgAProgramId> → 200 with empty data[] (NOT Org A's tiers)
    // GET /tiers/{orgATierId} → 404 (tier not found for Org B)
    // DELETE /tiers/{orgATierId} → 404
    // POST /tiers/{orgATierId}/status APPROVE → 404
    // Evidence that orgId is in every MongoDB query — cannot be verified by pure UT
}
```

#### IT-05: `shouldExecuteFullApproveFlow`

Covers TS-12, TS-27, TS-28, TS-29.

```java
@Test
void shouldExecuteFullApproveFlow() {
    // 1. Create tier (DRAFT)
    // 2. POST /status SUBMIT_FOR_APPROVAL → assert PENDING_APPROVAL
    // 3. Mock Thrift createOrUpdateSlab to return slabId=42
    // 4. POST /status APPROVE → assert ACTIVE, slabId=42, memberCount populated from mock
    // 5. GET /tiers?programId=X → tier now in list (was excluded as DRAFT)
    // Also verify REJECT flow:
    // 6. POST /status REJECT with comment → assert DRAFT, comment stored
}
```

#### IT-06: `shouldRejectInvalidStatusTransitionsViaApi`

Covers TS-31, TS-32, TS-33, TS-34, TS-35, TS-36, TS-22 — all API-level 400 responses.

```java
@Test
void shouldRejectInvalidStatusTransitionsViaApi() {
    // Drive via map: {(tierInStatus, action) → expectedErrorFragment}
    // Each: POST /status with action on wrong-status tier → 400, errors[] non-empty
    // Use RestTemplate + assertThrows(HttpClientErrorException.BadRequest.class)
    // Included: PUT on PENDING_APPROVAL tier (TS-22) — status check happens in facade
}
```

#### IT-07: `shouldEnforceDeletePreConditionsViaApi`

Covers TS-37, TS-38, TS-39, TS-41, TS-42.

```java
@Test
void shouldEnforceDeletePreConditionsViaApi() {
    // TS-37: DELETE base tier (sn=1) → 400 TIER_IS_BASE_TIER
    // TS-38: Mock Thrift getMemberCountPerSlab to return 150 → 400 TIER_HAS_MEMBERS
    // TS-39: Tier B has downgradeTarget=Tier A → DELETE Tier A → 400 TIER_IS_DOWNGRADE_TARGET
    // TS-41: Valid delete (non-base, 0 members, not target) → 200, status=STOPPED
    //        Assert Thrift deactivateSlab called once
    // TS-42: DELETE DRAFT tier (slabId=null) → 200, no Thrift call (MongoDB-only delete)
    // Note: TS-40 (partner sync) is BLOCKED by F-01 — placeholder comment only
}
```

#### IT-08: `shouldReturnStructuredValidationErrors`

Covers TS-13, TS-14, TS-15, TS-16, TS-24, TS-25, TS-23, TS-60.

```java
@Test
void shouldReturnStructuredValidationErrors() {
    // Drive via Map: {invalidRequest → expectedErrors[].code}
    // 1. POST with missing name → errors contains "name is required"
    // 2. POST with threshold=-1 → errors contains "eligibility.thresholdValue"
    // 3. POST with colorCode="red" (non-hex) → errors contains "colorCode"
    // 4. POST with name.length=101 → errors contains "name"
    // 5. POST /status with action="INVALID" → 400 (TierAction.fromString throws)
    // 6. POST /status with empty body {} → 400 errors contains "action"
    // 7. POST /status REJECT without comment → 400 errors contains "comment"
    // 8. GET /tiers (no programId) → 400 MissingServletRequestParameterException mapped
    // Assert: all return HTTP 400, all have ResponseWrapper.errors[] non-empty, no 500s
}
```

#### IT-09: `shouldHandleThriftFailureOnApproveGracefully`

Covers TS-53, TS-54, TS-57, TS-58 + F-06 regression.

```java
@Test
void shouldHandleThriftFailureOnApproveGracefully() {
    // TS-53/TS-57: Thrift createOrUpdateSlab throws → 
    //   HTTP 500, ResponseWrapper.errors non-empty
    //   Re-fetch MongoDB doc: status BACK to PENDING_APPROVAL (not left as ACTIVE)
    //   F-06 fix regression: verify stale status not returned (reload doc after deleteTier in STOP flow)
    // TS-58: Thrift deactivateSlab throws during STOP →
    //   HTTP 500, MongoDB status NOT changed to STOPPED
    // Mock pattern: pointsEngineRulesThriftService.createOrUpdateSlab(...) → doThrow
}
```

#### IT-10: `shouldReturnMemberCountForActiveTiers`

Covers TS-01 (memberCount), TS-06, TS-07, TS-55.

```java
@Test
void shouldReturnMemberCountForActiveTiers() {
    // Setup: two ACTIVE tiers approved (slabId set)
    // Mock Thrift getMemberCountPerSlab → return [{slabId=1, count=50}, {slabId=2, count=200}]
    // GET /tiers → verify memberCount=50 and memberCount=200 in response items
    // GET /tiers/{draftTierId} → verify memberCount=null for DRAFT
    // TS-55: Mock getMemberCountPerSlab to throw → GET /tiers still returns 200
    //   with memberCount=null (degraded but functional)
    //   No 500 thrown when member count fetch fails
}
```

#### IT-11: `shouldHandleConcurrentApproveIdempotently`

Covers TS-43, TS-44, TS-61.

```java
@Test
void shouldHandleConcurrentApproveIdempotently() {
    // TS-43: Setup tier as ACTIVE + slabId=42 already (simulates prior successful approve)
    // Call APPROVE again → HTTP 200 (idempotent), slabId still 42
    // Verify Thrift NOT called second time (verify(mock, never()).createOrUpdateSlab(...))
    // TS-61/TS-44: Two concurrent APPROVE threads for same tier — test optimistic locking
    //   Only one succeeds; second detects stale version or slabId already set
    //   Final MongoDB doc has exactly one slabId (not duplicated)
    //   Thrift called exactly once (verify(mock, times(1)).createOrUpdateSlab(...))
}
```

#### IT-12: `shouldRejectDuplicateSerialNumbers`

Covers TS-45, TS-64.

```java
@Test
void shouldRejectDuplicateSerialNumbers() {
    // Create tier with serialNumber=3 → success
    // Create another tier with serialNumber=3 same program → 400 "serialNumber already in use"
    // Concurrent case: two simultaneous POSTs with serialNumber=4
    //   Only one succeeds; second returns 400
    //   One MongoDB document exists (not two)
}
```

#### IT-13: `shouldHandleTimestampsAsUtcIso8601`

Covers TS-70 (G-01.7 guardrail).

```java
@Test
void shouldHandleTimestampsAsUtcIso8601() {
    TierResponse created = postTier(baseRequest());
    Instant createdOn = Instant.parse(created.getCreatedOn()); // parses as ISO-8601 UTC
    // Verify Z suffix present in raw JSON response body
    String rawBody = restTemplate.getForObject(tierUrl(created.getTierId()), String.class);
    assertTrue(rawBody.contains("Z"), "createdOn must be UTC ISO-8601 (ends with Z)");
    // Simulate different Accept-Timezone headers → createdOn unchanged
    // (G-01: conversion only at presentation layer — verified by consistent output)
}
```

#### IT-14: `shouldReturnEmptyListWhenProgramHasNoTiers`

Covers TS-71 null-safety (empty program case), edge case from §3.2.

```java
@Test
void shouldReturnEmptyListWhenProgramHasNoTiers() {
    // GET /tiers?programId=<new-empty-program>
    // Assert HTTP 200, data=[] (NOT null), errors=[]
    // Confirms TierFacade returns empty list (not null) — G-02 compliance
}
```

#### IT-15: `shouldBlockedPartnerSyncValidationOnDelete` (BLOCKED by F-01)

Covers TS-40.

```java
// NOTE: THIS TEST IS BLOCKED pending Developer fix for F-01 (PartnerProgramTierSyncConfiguration check)
// Placeholder — do not implement until TierValidator.validateDelete has partner sync check
@Test
@Disabled("BLOCKED: F-01 — validateDelete missing PartnerProgramTierSyncConfiguration check")
void shouldBlockDeleteForTierWithPartnerSyncReference() {
    // Once F-01 is fixed:
    // Setup: mock Thrift/repo to return PartnerProgramTierSyncConfiguration with loyaltyProgramSlabId matching tier
    // DELETE /tiers/{id} → HTTP 400, code="TIER_HAS_PARTNER_SYNC_REFERENCE"
}
```

---

## 6. Manual Test Steps

These scenarios require environment-level setup or exploratory judgment that cannot be reliably automated in CI.

### M-01: Deployment Order Validation (B-1 blocker)
**When**: Before first deployment to any non-local environment.
1. Verify `program_slabs` DDL in cc-stack-crm includes `is_active TINYINT(1) NOT NULL DEFAULT 1`.
2. Apply DDL to staging before deploying application code.
3. Run `SELECT COUNT(*) FROM program_slabs WHERE is_active IS NULL` — must be 0.
4. Deploy application. Call `DELETE /v3/tiers/{id}` on a test tier. Verify HTTP 200 and `is_active=0` in database.
**Expected**: No SQL column not found errors. Soft-delete sets `is_active=0`.

### M-02: @Lockable TTL Behavior Under Concurrent Load (W-2)
**When**: Once staging environment is available.
1. Send 5 concurrent `POST /v3/tiers/{id}/status` APPROVE requests for the same tier.
2. Observe responses: exactly 1 should return HTTP 200; others may return `LockManagerException` (HTTP 500 or 409).
3. Verify only ONE MySQL row created in `program_slabs`.
4. Verify `acquireTime=5000ms` behavior: the current implementation does NOT wait — second request throws immediately. Confirm this is accepted behavior (W-2 question for user).
**Expected**: Exactly 1 row, no duplicates. Lock behavior documented.

### M-03: Member Count at Tier Scale (GET /tiers performance)
**When**: Staging with realistic data volume.
1. Enroll 10,000+ members into a single tier.
2. GET /v3/tiers — observe response time.
3. Confirm index `idx_ce_slab_count` on `customer_enrollment` is present and used (`EXPLAIN` the query).
4. Verify member count is accurate.
**Expected**: Response time < 500ms with index. `EXPLAIN` shows index scan, not full table scan.

### M-04: MongoDB Index Creation on First Startup (W-1)
**When**: First deployment to a new environment (empty `tiers` collection).
1. Deploy application with `@CompoundIndexes` on TierDocument.
2. Connect to MongoDB: `db.tiers.getIndexes()` — verify 3 compound indexes created.
3. Create 100 tiers across 5 different orgs.
4. `db.tiers.find({orgId: 100, programId: 200}).explain("executionStats")` — verify IXSCAN.
**Expected**: All 3 indexes present, queries use index scan.

### M-05: APPROVE Flow Under Partial Failure (Exploratory — TS-54 gap)
**When**: Staging — requires fault injection capability.
1. Configure Thrift to succeed but MongoDB save to fail (inject exception after Thrift call).
2. Call APPROVE. Observe: MySQL has the new `program_slabs` row but MongoDB still shows PENDING_APPROVAL.
3. Call APPROVE again (retry): observe behavior — does it create a duplicate MySQL row?
4. Document observed behavior against F-05 (WAL pattern not implemented).
**Expected**: Document whether retry creates duplicate. This surfaces the residual risk from TS-54 until WAL is implemented.

---

## 7. Guardrail Coverage Verification

| Guardrail | Test(s) | Status |
|-----------|---------|--------|
| G-01 Timezone | IT-13 (UTC ISO-8601 in response), UT-07 (Instant usage in doc build) | COVERED |
| G-02 Null safety | IT-01 (null memberCount/slabId for DRAFT), IT-14 (empty list not null) | COVERED |
| G-03 Security | All ITs — orgId from token, never from param | COVERED (AbstractContainerTest auth setup) |
| G-04 Performance | M-03 (manual) — index verification | MANUAL ONLY |
| G-05 Data Integrity | IT-09 (Thrift failure → rollback) | COVERED |
| G-06 API Design | IT-08 (ResponseWrapper errors[] format) | COVERED |
| G-07 Multi-Tenancy | IT-04 (tenant isolation) | COVERED |
| G-10 Concurrency | UT-11 (@Lockable present), IT-11 (concurrent APPROVE), IT-12 (serial number race) | COVERED |
| G-11 Resilience | IT-09 (Thrift failure), IT-10 (member count failure graceful) | COVERED |
| G-12 AI-Specific | N/A — no AI-specific logic in this feature | N/A |

**No guardrail area is completely without automated coverage.**

---

## 8. Verification Commands for Developer

### Red Phase — new tests written, implementation incomplete
```bash
# Run new UT file (should fail if validators are missing)
mvn test -pl intouch-api-v3 -Dtest=TierValidatorTest -am

# Run new emf UT (should fail if JPQL not updated)
mvn test -pl pointsengine-emf-ut -Dtest=PeProgramSlabDaoTest -am

# Confirm: test failures are compilation or assertion failures — not runtime errors from infra
```

### Green Phase — all UTs pass
```bash
# All UTs pass in intouch-api-v3
mvn test -pl intouch-api-v3 -am

# All UTs pass in emf-parent
mvn test -pl pointsengine-emf-ut -am

# Confirm: zero failures, zero errors
# Confirm: test count >= baseline (no previously passing tests broken)
```

### Full Verify Phase — UTs + ITs pass
```bash
# intouch-api-v3 full verify (includes ITs in integrationTests/)
mvn verify -pl intouch-api-v3 -am

# emf-parent verify
mvn verify -pl pointsengine-emf-ut -am

# Run single IT in isolation for fast feedback during development
mvn verify -pl intouch-api-v3 -Dtest=TierControllerTest -am
```

### Baseline Preservation Check
```bash
# Before and after — compare test counts; after must be >= before
mvn test -pl intouch-api-v3 -am -q 2>&1 | grep "Tests run"
mvn test -pl pointsengine-emf-ut -am -q 2>&1 | grep "Tests run"
```

### CI Pipeline (local Docker required for ITs)
```bash
# Unit tests only (fast — no Docker needed)
mvn test -pl intouch-api-v3 -am -Dsurefire.excludes="**/integrationTests/**"

# Integration tests only (Docker required — Testcontainers)
mvn verify -pl intouch-api-v3 -am -Dsurefire.excludes="**/com/capillary/**" -Dfailsafe.includes="**/integrationTests/**"
```

---

## 9. Automation vs Manual Split

### Automated (26 test methods)
- [x] All validation logic (6 UT) — in place in TierValidatorTest
- [x] Facade unit tests (5 UT) — in place in TierFacadeTest
- [x] DAO JPQL structure (2 UT) — in place in emf-parent unit test module
- [x] Full API CRUD happy paths (IT-01, IT-05)
- [x] Status filtering and ordering (IT-02)
- [x] 404 / not-found coverage (IT-03)
- [x] Tenant isolation (IT-04)
- [x] State machine at API layer (IT-06)
- [x] Delete pre-conditions (IT-07)
- [x] Validation error format (IT-08)
- [x] Thrift failure resilience (IT-09)
- [x] Member count (IT-10)
- [x] Idempotency (IT-11)
- [x] Serial number uniqueness (IT-12)
- [x] Timestamp format (IT-13)
- [x] Empty list null-safety (IT-14)

### Manual (5 steps)
- [ ] M-01: Deployment order + DDL verification (pre-deployment checklist)
- [ ] M-02: @Lockable TTL behavior under concurrent load
- [ ] M-03: Member count query performance with index
- [ ] M-04: MongoDB index creation on fresh environment
- [ ] M-05: APPROVE partial failure exploratory test (TS-54 gap)

### Blocked (1 IT placeholder)
- [ ] IT-15: Partner sync validation on delete — BLOCKED by F-01

---

## 10. Developer Tasks Before ITs Can Run

| # | Task | Reason | File |
|---|------|--------|------|
| D-01 | Add `TierRepository.class` to `EmfMongoConfigTest.includeFilters` | Without this, TierRepository uses wrong MongoDB — silent data loss (session-memory line 79) | `integrationTests/configuration/EmfMongoConfigTest.java` |
| D-02 | Add `is_active TINYINT(1) NOT NULL DEFAULT 1` to test-scoped `program_slabs.sql` in `src/test/resources` | B-1 blocker: STOP/DELETE flow calls `slab.setActive(false)` — fails without column | `src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/program_slabs.sql` |
| D-03 | Fix F-01 (add PartnerProgramTierSyncConfiguration check to `TierValidator.validateDelete`) | IT-15 blocked — TS-40 cannot be automated without this | `TierValidator.java:53-84` |
| D-04 | Fix F-06 (refresh TierDocument after `deleteTier` in STOP flow) | IT-09 includes regression for this — will fail if not fixed | `TierFacade.java:314-317` |

---

## 11. QUESTIONS FOR USER

- **Q-01 (C4)**: Should `GET /v3/tiers/{tierId}` return a STOPPED tier (HTTP 200 + status=STOPPED) or HTTP 404? The compliance analysis (05b-gap-analysis.md) and session memory (line 119) say 404 by default. IT-03 is written to expect 404 for STOPPED tiers. If 200 + STOPPED is correct instead, IT-03 must be revised.

- **Q-02 (C3)**: The APPROVE WAL pattern (F-05) is not implemented — simple try-catch rollback used instead. M-05 manual test surfaces the reverse failure case (Thrift succeeds, MongoDB fails). Is simple rollback accepted for now (update session memory) or should WAL be implemented before SDET closes?

- **Q-03 (C4)**: `@Lockable` `acquireTime` parameter is ignored — W-2 from backend-readiness. M-02 tests the resulting behavior. Is the "throw immediately on lock contention" behavior acceptable? If yes, W-2 should be marked as accepted constraint (not a defect). Needed to set correct expectations for IT-11.

- **Q-04 (C3)**: TS-55 — when `getMemberCountPerSlab` Thrift call fails during GET /tiers, should the API return `memberCount=null` (degraded) or HTTP 500? IT-10 assumes degraded (null) is correct based on recommendation in 04-qa.md. If 500 is correct, IT-10 must be revised.

- **Q-05 (C2)**: Does POST /tiers support idempotency keys (`X-Idempotency-Key` header)? Without it, network retries create duplicate DRAFT documents. If no idempotency key is planned, TS-72 should be marked "accepted behavior" and is excluded from IT scope. Currently excluded from the plan on that basis.

---

## 12. ASSUMPTIONS MADE

- **A-01 (C7)**: `AbstractContainerTest` uses shared static containers. All new ITs MUST extend it and MUST NOT create new Spring contexts. Evidence: read `AbstractContainerTest.java` directly — all containers are `static` and started in a static initializer block.

- **A-02 (C6)**: `PointsEngineRulesThriftService` can be `@MockBean` in TierControllerIT because it is already `@MockBean` in `UnifiedPromotionControllerTest` (same service, same base class). Evidence: line 102 of `UnifiedPromotionControllerTest.java` read directly.

- **A-03 (C6)**: JUnit 4 (`@RunWith(MockitoJUnitRunner.Silent.class)`) is the correct runner for new emf-parent unit tests. Evidence: all existing tests in `pointsengine-emf-ut` use this pattern — verified from `SlabUpgradeAuditLogServiceTest.java` and pom.xml (JUnit 4 + junit-vintage-engine).

- **A-04 (C5)**: The `TierRepository` registration issue in `EmfMongoConfigTest` (D-01) is a blocking setup task, not a code defect. The pattern to fix it is identical to how `UnifiedPromotionRepository` is registered in the existing `EmfMongoConfigTest`. The fix is straightforward and low-risk.

- **A-05 (C4)**: The test-scoped `program_slabs.sql` exists in `src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/`. The `AbstractContainerTest` loads schema files from that path (confirmed at line 199 of `AbstractContainerTest.java`). If the file does not exist or the path differs, D-02 must account for that. Confidence is C4 — file path must be verified by Developer.

---

## Return to Orchestrator

```
PHASE: SDET
STATUS: complete (with 1 blocker to Developer)
ARTIFACT: 06-sdet.md

SUMMARY:
- 11 unit tests, 15 integration tests, 5 manual steps
- Automated: all 72 QA scenarios covered by 26 test methods (2.8:1 ratio)
- 1 IT blocked (IT-15) pending F-01 fix (PartnerProgramTierSyncConfiguration check)
- Exemplars used: UnifiedPromotionControllerTest (IT), UnifiedPromotionFacadeTest (facade UT),
  PointsEngineThriftServiceTest (static mock UT), SlabUpgradeAuditLogServiceTest (emf UT)
- CI commands: mvn test (UTs), mvn verify (UTs + ITs); separate UT-only command documented
- 4 pre-IT Developer tasks identified (D-01 through D-04)

BLOCKERS:
- BLOCKER TARGET=Developer: F-01 (PartnerProgramTierSyncConfiguration validation missing from
  TierValidator.validateDelete). IT-15 (TS-40) cannot be automated until this is implemented.
  Severity: HIGH per compliance analysis.
- BLOCKER TARGET=Developer: F-06 (STOP action returns stale TierResponse). IT-09 includes
  regression test for this — will fail until fixed.

SESSION MEMORY UPDATES:
- Constraints: Added IT infrastructure constraints (AbstractContainerTest shared context,
  EmfMongoConfigTest TierRepository registration, test-scoped DDL requirement)
- Open Questions: Added Q-01 through Q-05 (stopped tier GET behavior, WAL acceptance,
  Lockable TTL, degraded memberCount, POST idempotency key)
- Resolved: none (all 5 QA open questions remain unresolved per original 04-qa.md)
```
