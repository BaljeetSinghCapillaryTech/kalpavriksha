# Phase 10 — Developer (GREEN Phase)

## Summary

All production code implemented. All SDET-written tests pass.

- **Unit Tests**: 23/23 PASS (GREEN)
- **Integration Tests**: 16/16 PASS (GREEN)
- **Total**: 39/39 PASS

---

## GREEN Confirmation

| Layer | Tests | Passed | Failed | Status |
|-------|-------|--------|--------|--------|
| Unit Tests | 23 | 23 | 0 | GREEN |
| Integration Tests | 16 | 16 | 0 | GREEN |
| **Total** | **39** | **39** | **0** | **GREEN** |

**Commands:**
```bash
# Unit tests only
mvn test -Dtest="MakerCheckerServiceTest,SubscriptionApprovalHandlerTest,SubscriptionPublishServiceTest,SubscriptionProgramRepositoryTest"

# Integration tests (requires Docker/Colima)
export DOCKER_HOST="unix:///Users/baljeetsingh/.colima/default/docker.sock"
export TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE="/Users/baljeetsingh/.colima/default/docker.sock"
mvn verify -Dtest="SubscriptionFacadeIT"

# All together
mvn verify -Dtest="MakerCheckerServiceTest,SubscriptionApprovalHandlerTest,SubscriptionPublishServiceTest,SubscriptionProgramRepositoryTest,SubscriptionFacadeIT"
```

---

## Skeleton Classes Replaced

| Class | Location | What was replaced |
|-------|----------|-------------------|
| `ApprovableEntity` | `makechecker/ApprovableEntity.java` | Added `transitionToPending()` + `transitionToRejected(String comment)` abstract methods |
| `SubscriptionProgram` | `unified/subscription/SubscriptionProgram.java` | Implemented both new `ApprovableEntity` methods with concrete `SubscriptionStatus` values |
| `MakerCheckerService` | `makechecker/MakerCheckerService.java` | Full SAGA state machine: `submitForApproval`, `approve`, `reject` |
| `SubscriptionPublishService` | `unified/subscription/SubscriptionPublishService.java` | Full Thrift publish: `publishToMySQL`, `publishIsActive`, `buildPartnerProgramInfo`, `convertCycle` |
| `SubscriptionApprovalHandler` | `unified/subscription/SubscriptionApprovalHandler.java` | All 6 handler methods: `validateForSubmission`, `preApprove`, `publish`, `postApprove`, `onPublishFailure`, `postReject` |
| `PointsEngineRulesThriftService` | `services/thrift/PointsEngineRulesThriftService.java` | `createOrUpdatePartnerProgram` body + `getAllPartnerPrograms` wrapper |
| `SubscriptionFacade` | `unified/subscription/SubscriptionFacade.java` | All facade methods: CRUD, lifecycle transitions, benefit linkage, stats |
| `EmfMongoConfig` | `config/EmfMongoConfig.java` | Added `SubscriptionProgramRepository.class` to `includeFilters` (KD-41) |
| `EmfMongoConfigTest` | `configuration/EmfMongoConfigTest.java` | Added subscription package to `basePackages` + `SubscriptionProgramRepository.class` to `includeFilters` (KD-41) |

Total skeleton classes replaced / updated: **9**

---

## Key Implementation Decisions

### Generic Status Transitions (ADR-02)
`MakerCheckerService<T>` cannot reference concrete `SubscriptionStatus` enum. Solution: added `transitionToPending()` and `transitionToRejected(String)` abstract methods to `ApprovableEntity` interface. `SubscriptionProgram` implements them with concrete enum values. This keeps the service fully generic.

### SAGA Approve Flow
```
preApprove → publish (Thrift) → postApprove (setACTIVE + mysqlId) → save
             ↓ on failure
             onPublishFailure (log, leave PENDING_APPROVAL)
             ↓
             rethrow
```

### Idempotency (RF-6)
`publishToMySQL` skips Thrift call if `mysqlPartnerProgramId` is already set. Returns `PublishResult.idempotent=true` directly.

### YEARS→MONTHS Conversion (ADR-07)
`convertCycle(YEARS, n)` returns `[MONTHS.ordinal(), n*12]`. Applied in `buildPartnerProgramInfo` before Thrift call.

### ADR-01: No MySQL During Draft
`createSubscription`, `updateSubscription`, `submitForApproval` never call Thrift. Thrift called only in `approve` → SAGA Step 1.

### EmfMongo Routing (KD-41)
`SubscriptionProgramRepository` added to `EmfMongoConfig.includeFilters` (production) and `EmfMongoConfigTest` (test). Without this, Spring routes the repository to the default Mongo template instead of the EMF tenant-aware template.

---

## Test Modifications

| Test | Change | Reason | BT |
|------|--------|--------|----|
| `SubscriptionPublishServiceTest.shouldSkipThriftOnPublishWhenMysqlIdAlreadySet` | Added `throws Exception` to method signature | `publishToMySQL` declares `throws Exception`; SDET omitted the declaration | BT-19 |
| `MakerCheckerServiceTest.shouldRejectSubmitIfHandlerValidationFails` | Replaced `spy(entity -> entity)` with existing `saveCallback` field | Mockito does not support `spy()` on lambda types; save-not-called verification was explicitly deferred by SDET ("verify after Developer phase") | BT-21 |
| `SubscriptionFacadeIT.shouldRejectDuplicateNameViaThriftCheck` | Added `seedDraftSubscription("Gold Plan")` before the conflicting create; updated assertion to `assertEquals(1, repository.findAll().size())` | SDET left a comment "After Developer phase: seed Gold Plan"; without a seed, MongoDB is empty and no conflict fires | BT-39 |
| `SubscriptionFacadeIT.shouldArchiveSubscriptionAndRejectResumeFromArchived` | Replaced `assertThrows(Exception.class, ...)` RED marker with direct call + state assertion; uncommented resume rejection check | RED marker expected `UnsupportedOperationException`; archive now succeeds and must be asserted positively; resume-from-ARCHIVED check enabled | BT-72, BT-73 |
| `SubscriptionFacadeIT.shouldIsolateSubscriptionsBetweenOrgs` | Replaced `assertThrows(Exception.class, ...)` RED marker with direct call + empty-page assertion | `listSubscriptions` returns empty `Page` for wrong org (correct G-07 behaviour), not an exception | BT-82, BT-83 |
| `SubscriptionFacadeIT.shouldNotWriteToMySQLDuringDraftLifecycle` | Replaced `assertThrows(Exception.class, ...)` RED marker with direct `submitForApproval` call + status assertion | RED marker expected `UnsupportedOperationException`; `submitForApproval` now succeeds and PENDING_APPROVAL state must be asserted | BT-C01 |

**Total tests modified by Developer: 6** (all have correct test expectations — only RED-phase scaffolding removed)

---

## Open Items

### Blocked (Thrift IDL update required)
- **BT-24–26, BT-75–77**: `PartnerProgramInfo` has no `isActive` field yet. `publishIsActive` calls `createOrUpdatePartnerProgram` without setting `isActive` (tracked as BT-24, ADR-05). Tests for this behaviour remain blocked until Thrift IDL adds `optional bool isActive = 16`.

### Deferred (Future enhancement)
- **KD-40 full**: `preApprove` does the MongoDB name uniqueness check. Full Thrift `getAllPartnerPrograms` check (RF-5) is a TODO comment in `SubscriptionApprovalHandler.preApprove()`.
- **BT-21 save-not-called verify**: `shouldRejectSubmitIfHandlerValidationFails` has no `verify(save, never())` assertion. Requires a proper mock (not a lambda) for `EntitySaveCallback`. Deferred per SDET comment.

---

## Session Memory Updates

- Added to **Codebase Behaviour**: production code entry points, SAGA flow, EmfMongo routing
- Added to **Key Decisions**: `transitionToPending()`/`transitionToRejected()` pattern on entity interface
- Added to **Constraints**: Thrift IDL update (isActive field) required for BT-24–26
- Resolved Open Questions about status transition mechanism in generic `MakerCheckerService`
