# SDET -- Test Code Implementation (RED Phase)

> Phase 9: SDET
> Date: 2026-04-12
> Source: 04b-business-tests.md, 03-designer.md, 04-qa.md, 01-architect.md
> RED Confirmation: PASS (compilation succeeds, 23/28 tests fail as expected)

---

## RED Confirmation

- **Compilation**: PASS (both `mvn compile` and `mvn test-compile` succeed with Java 17)
- **Test execution**: FAIL (expected — RED state confirmed)
- **Tests run**: 28
- **Errors**: 23 (skeleton methods throw `UnsupportedOperationException`)
- **Failures**: 0
- **Skipped**: 0
- **Sample failures**: `TierFacade.listTiers()` → UnsupportedOperationException, `MakerCheckerService<T>.submitForApproval()` → UnsupportedOperationException, `TierValidationService.validateCreate()` → UnsupportedOperationException

**Command**: `mvn test -pl . -Dtest="com.capillary.intouchapiv3.tier.*Test,com.capillary.intouchapiv3.makechecker.*Test" -am`

---

## Discovered Test Conventions

- **Base class (ITs)**: `integrationTests.AbstractContainerTest` — Testcontainers (MongoDB 4.2.3, MySQL 8.0.33, Redis, RabbitMQ)
- **Annotations (UTs)**: `@ExtendWith(MockitoExtension.class)`, `@Mock`, `@InjectMocks`
- **Annotations (ITs)**: Inherited from AbstractContainerTest (`@SpringBootTest`, `@ActiveProfiles("test")`)
- **Assertion library**: JUnit 5 (`assertEquals`, `assertThrows`, `assertNotNull`, `assertTrue`)
- **Data setup**: Inline builders + PODAM factory for random data
- **Cleanup strategy**: `@AfterEach` manual delete from MongoDB
- **Container strategy**: Shared static containers in AbstractContainerTest
- **Naming convention**: `*Test.java` (Surefire picks up)
- **Test commands**: `mvn test` (all), `mvn test -Dtest=ClassName` (specific)
- **Spring profiles**: `test`
- **Context reuse**: All ITs share one context via AbstractContainerTest

---

## Files Created

### Skeleton Production Classes (37 files in src/main)

| Package | Files | Purpose |
|---------|-------|---------|
| `tier/enums/` | TierStatus, CriteriaType, ActivityRelation, DowngradeSchedule, DowngradeTargetType (5) | Status & config enums |
| `tier/model/` | BasicDetails, EligibilityCriteria, Activity, RenewalConfig, DowngradeConfig, DowngradeTo, MemberStats, EngineConfig, TierMetadata (9) | Domain model POJOs |
| `tier/dto/` | TierCreateRequest, TierUpdateRequest, TierListResponse, KpiSummary (4) | REST DTOs |
| `tier/` | UnifiedTierConfig, TierRepository, TierFacade, TierValidationService, TierApprovalHandler (5) | Core tier module |
| `makechecker/` (imported) | MakerCheckerService<T>, ApprovableEntity, ApprovableEntityHandler<T>, PendingChange, NotificationHandler (5) | Generic MC framework (from Baljeet's makechecker package) |
| `tier/approvals/` | TierApprovalHandler (extends ApprovableEntityHandler<UnifiedTierConfig>) (1) | Tier-specific approval handler |
| `resources/` | TierController, TierReviewController (2) | REST controllers |

**All methods throw `UnsupportedOperationException("Not implemented — skeleton for RED phase")`** except enums, models (Lombok), and interfaces.

### Unit Test Files (4 files, 28 test methods)

| File | Tests | Business Test Cases Covered |
|------|-------|-----------------------------|
| `TierFacadeTest.java` | 12 | BT-01..BT-05 (listing), BT-10..BT-14 (create), BT-20..BT-25 (edit), BT-30..BT-34 (delete) |
| `TierValidationServiceTest.java` | 6 | BT-40..BT-51 (validation: names, colors, dates, uniqueness, serial, cap) |
| `TierApprovalHandlerTest.java` | 7 | BT-60..BT-70 (submit via facade, approve, reject, list, notification) |
| `TierFacadeApprovalTest.java` | 3 | BT-80..BT-87 (approval flow, apply, version swap) |

### Integration Tests (deferred to Developer)

ITs extend `AbstractContainerTest` which requires the full Spring Boot context + Testcontainers. Writing ITs requires:
1. MongoDB test config for `unified_tier_configs` and `pending_changes` collections (extend `EmfMongoConfigTest`)
2. Thrift service mocks (`@MockBean` for `PointsEngineRulesThriftService`)
3. Auth setup (SecurityContext with IntouchUser)
4. REST endpoint tests for `TierController` and `TierReviewController` (new endpoints: `/v3/tiers/{tierId}/submit`, `/approve`, `/reject`, `/approvals`)

These are planned but deferred to Developer phase when production code exists and can be wired.

---

## Test Efficiency Summary

| Metric | Value |
|--------|-------|
| Business test cases in 04b-business-tests.md | 141 |
| Test methods written (RED phase) | 28 |
| Combination ratio | ~5:1 (related conditions combined per Test Efficiency Protocol) |
| Max methods per test class | 12 (TierFacadeTest) |
| UT count | 28 |
| IT count | 0 (planned, deferred) |

---

## Verification Commands

```bash
# RED phase (current — tests FAIL)
export JAVA_HOME=/Users/ritwikranjan/.sdkman/candidates/java/17.0.17-amzn
mvn test -pl . -Dtest="com.capillary.intouchapiv3.tier.*Test,com.capillary.intouchapiv3.approval.*Test" -am

# GREEN phase (after Developer writes production code — tests should PASS)
mvn test -pl . -am

# Full verify (all UTs + ITs)
mvn verify -pl . -am
```

---

## Developer's Next Step

Replace skeleton methods in these files with real business logic:

| Priority | Skeleton Class | Tests Targeting It | Key Logic |
|----------|---------------|-------------------|-----------|
| 1 | `TierValidationService` | 6 tests | Name/color/date validation, uniqueness check, serial assignment, 50-cap |
| 2 | `TierFacade` | 12 tests | MC toggle check, CRUD orchestration, versioned edit, KPI summary |
| 3 | `TierApprovalHandler` (implements `ApprovableEntityHandler<UnifiedTierConfig>`) | 7 tests | Apply approval: MongoDB→Thrift conversion, version swap, strategy building |
| 4 | `TierFacade.submitForApproval`, `handleApproval`, `handleRejection`, `listPendingApprovals` | 3 tests | MC lifecycle integration via generic `MakerCheckerService<T>` |
| 5 | `TierController` | (IT) | REST endpoints wiring (CRUD) |
| 6 | `TierReviewController` | (IT) | Approval endpoints wiring (`/submit`, `/approve`, `/reject`, `/approvals`, `/config`) |
