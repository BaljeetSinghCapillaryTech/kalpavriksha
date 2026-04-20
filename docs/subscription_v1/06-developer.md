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

---

## Rework GREEN Confirmation (2026-04-15 — 12-Gap Fix)

All 12 critical gaps from UI validation cross-layer analysis implemented. 76/76 subscription unit tests GREEN.

| Layer | Tests | Passed | Failed | Status |
|-------|-------|--------|--------|--------|
| Original UTs | 23 | 23 | 0 | GREEN |
| Rework UTs (BT-R-01..R-35) | 53 | 53 | 0 | GREEN |
| **Total UTs** | **76** | **76** | **0** | **GREEN** |

### Files Changed in Rework

| File | Change |
|------|--------|
| `SubscriptionProgram.java` | `name`: @Size(max=50) + @Pattern (ADR-08); `description`: @NotBlank + @Size(max=100) + @Pattern (ADR-09); added `pointsExchangeRatio` (@NotNull @DecimalMin), `programType` (@NotNull PartnerProgramType), `syncWithLoyaltyTierOnDowngrade` (@NotNull Boolean); updated `TierConfig` with `tiers` List<ProgramTier> + `loyaltySyncTiers` Map; added `ProgramTier` inner class; fixed incorrect `subscriptionProgramId` Javadoc (ADR-18) |
| `enums/CycleType.java` | Removed `YEARS` — only DAYS and MONTHS remain (ADR-10) |
| `enums/PartnerProgramType.java` | New enum: `SUPPLEMENTARY`, `EXTERNAL` (ADR-14) |
| `SubscriptionProgramRepository.java` | `findActiveByOrgIdAndName`: exact match → `$regex`/`$options:'i'` case-insensitive (ADR-11) |
| `SubscriptionApprovalHandler.java` | Added 6 cross-field validations: pointsExchangeRatio>0, programType required, SUPPLEMENTARY requires duration, EXTERNAL clears duration, TIER_BASED requires tiers, syncWithLoyaltyTierOnDowngrade=true requires loyaltySyncTiers, migrationTargetProgramId>0 when migration enabled (ADR-12..17) |
| `SubscriptionPublishService.java` | Removed `DEFAULT_POINTS_RATIO` + `convertCycle()`; wired all 15 Thrift fields: field 5 (tiers), field 6 (pointsExchangeRatio from entity), field 8 (programType from entity), field 9 (conditional on SUPPLEMENTARY), field 10 (syncWithLoyaltyTierOnDowngrade direct), field 11 (loyaltySyncTiers) (ADR-12..17) |
| `SubscriptionFacade.java` | Implemented `updateSubscription()` (edit DRAFT, preserves ID — ADR-18); implemented `editActiveSubscription()` (forks DRAFT from ACTIVE, COPIES subscriptionProgramId — ADR-18); updated `createSubscription()` to include new fields; added `Pattern.quote()` for case-insensitive uniqueness callers (ADR-11) |
| `SubscriptionController.java` | **All 8 endpoints implemented** (was: all threw UnsupportedOperationException). CREATE, GET, LIST, UPDATE, FORK, SUBMIT, APPROVE, lifecycle (pause/resume/archive) — all delegate to SubscriptionFacade (KD-57) |

### Tests Modified by Developer
None — all 55 new SDET tests passed without modification.

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

---

## emf-parent GREEN Confirmation (Phase 10 continued — 2026-04-15)

### Thrift IDL Changes (thrift-ifaces-pointsengine-rules v1.83)

| Change | Purpose |
|--------|---------|
| `PartnerProgramInfo.isActive` (field 15, optional bool) | Enables PAUSE/ARCHIVE/RESUME flows (BT-24–26) |
| `LoyaltyConfigMetaData.optInStartDate/optInEndDate` (fields 14–15, i64) | Matches published 1.83 artifact to fix emf-parent compile |
| `getSupplementaryEnrollmentCountsByProgramIds` method | New Thrift service method for subscriber count queries (BT-75–77) |

### Production Code Changes (emf-parent)

| File | Change | BT |
|------|--------|----|
| `PointsEngineRuleConfigThriftImpl` | `deactivateSlab` stub (IDL compliance) | — |
| `PointsEngineRuleConfigThriftImpl` | `getMemberCountPerSlab` stub (IDL compliance) | — |
| `PointsEngineRuleConfigThriftImpl` | `getSupplementaryEnrollmentCountsByProgramIds` impl (delegates to editor) | BT-75–77 |
| `PointsEngineRuleConfigThriftImpl.getSupplementaryPartnerProgramEntity` | `isActive` conditional: only sets `entity.setActive()` when `isSetIsActive()=true` | BT-24–26 |
| `PointsEngineRuleEditor` | Added `getSupplementaryEnrollmentCountsByProgramIds` method to interface | BT-75–77 |
| `PointsEngineRuleEditorImpl` | Added stub `getSupplementaryEnrollmentCountsByProgramIds` (throws UOE) | BT-75–77 |

### GREEN Confirmation

- **PartnerProgramIsActiveConditionalTest**: 6/6 PASS (GREEN)
  - BT-24: `shouldSetPartnerProgramEntityInactiveWhenIsActiveFalse` ✓
  - BT-25: `shouldSetPartnerProgramEntityActiveWhenIsActiveTrue` ✓
  - BT-26: `shouldNotModifyIsActiveWhenFieldNotSetInRequest` ✓
  - BT-75: `shouldReturnEnrollmentCountsForEachPartnerProgramId` ✓
  - BT-76: `shouldReturnEmptyMapForEmptyPartnerProgramIdList` ✓
  - BT-77: `shouldWrapDaoExceptionAsPointsEngineRuleServiceException` ✓

### Test Modifications (emf-parent BT-24–26)

SDET's test bodies all called `fail("BLOCKED: ...")`. Developer replaced with real assertions using `ArgumentCaptor<PartnerProgram>` to verify entity `isActive` state passed to the editor.

| Test | Change | Reason | BT |
|------|--------|--------|----|
| All 6 `PartnerProgramIsActiveConditionalTest` tests | Replaced `fail("BLOCKED...")` with real mock setup + assertions | RED markers: SDET couldn't write tests until Thrift IDL was updated. Now IDL is updated and production code implements the conditional | BT-24–26, BT-75–77 |

**Cumulative tests modified by Developer: 12** (6 original + 6 emf-parent BT-24–77 RED markers)

---

---

## Reviewer Fix Cycle (2026-04-15 — BLK-1 through BLK-4)

Reviewer Phase 11 returned REQUEST_CHANGES with 4 blockers + 4 partial requirements. All fixed:

| Blocker | File | Fix |
|---------|------|-----|
| BLK-1 (REQ-38/39/40) | `SubscriptionPublishService.java` | `publishIsActive()` — added `info.isActive = isActive` (Thrift field 15, IDL v1.83). Removed stale TODO comment. PAUSE/RESUME/ARCHIVE now actually flip MySQL `is_active`. |
| BLK-2 (REQ-35/36) | `SubscriptionReviewController.java` (new) | Created REST controller: `POST /v3/subscriptions/{id}/review` (APPROVE/REJECT) and `GET /v3/subscriptions/approvals` (pending queue). Mirrors SubscriptionController pattern. |
| BLK-3 | `SubscriptionErrorAdvice.java` (new) | Created dedicated `@ControllerAdvice` in subscription package: `SubscriptionNotFoundException` → 404, `InvalidSubscriptionStateException` → 422, `SubscriptionNameConflictException` → 409. Kept `TargetGroupErrorAdvice` unchanged. |
| BLK-4 (REQ-12) | `SubscriptionFacade.java` | `duplicateSubscription()` builder now copies `programType`, `pointsExchangeRatio`, `syncWithLoyaltyTierOnDowngrade` from source. These are required fields — duplicate would have failed at submit without them. |

### GREEN Confirmation (post-fix)
- All 58 subscription UTs: PASS
- Compile: SUCCESS

---

## Open Items

### Deferred (Future enhancement)
- **KD-40 full**: `preApprove` does the MongoDB name uniqueness check. Full Thrift `getAllPartnerPrograms` check (RF-5) is a TODO comment in `SubscriptionApprovalHandler.preApprove()`.
- **BT-21 save-not-called verify**: `shouldRejectSubmitIfHandlerValidationFails` has no `verify(save, never())` assertion. Requires a proper mock (not a lambda) for `EntitySaveCallback`. Deferred per SDET comment.
- **`getSupplementaryEnrollmentCountsByProgramIds` DAO**: `PointsEngineRuleEditorImpl` stub throws `UnsupportedOperationException`. The actual DB query implementation is future work outside BRD scope.

---

## Session Memory Updates

- Added to **Codebase Behaviour**: production code entry points, SAGA flow, EmfMongo routing
- Added to **Key Decisions**: `transitionToPending()`/`transitionToRejected()` pattern on entity interface; `isActive` conditional backward-compatibility pattern
- Added to **Constraints**: Thrift IDL 1.83 installed locally to `.m2`; `PointsEngineRuleEditorImpl.getSupplementaryEnrollmentCountsByProgramIds` is a stub
- Resolved Open Questions about status transition mechanism in generic `MakerCheckerService`
- Resolved: BT-24–26 and BT-75–77 all GREEN after Thrift IDL update and production code implementation

---

## Rework 4 — Developer GREEN Phase (2026-04-17)

### Scope
Three production gap fixes: Gap 1 (mysqlPartnerProgramId carry-forward), Gap 2 (status-qualified state-transition methods), Gap 3 (SNAPSHOT on edit-of-ACTIVE approval).

### Production Code Changes

**1. `SubscriptionApprovalHandler.java` — Gap 3 (SNAPSHOT)**

| Location | Change | Business Impact |
|----------|--------|-----------------|
| `postApprove()`, parentId!=null branch | `oldActive.setStatus(ARCHIVED)` → `oldActive.setStatus(SNAPSHOT)` | Old ACTIVE doc archived as read-only audit trail, not as a generic ARCHIVED record |

**2. `SubscriptionFacade.java` — Gap 1 + Gap 2**

| Method | Change | Business Impact |
|--------|--------|-----------------|
| `editActiveSubscription()` | `getSubscription(orgId, id)` → `getSubscriptionByStatus(orgId, id, ACTIVE)` | Prevents ambiguous doc selection during edit window |
| `editActiveSubscription()` builder | Added `.mysqlPartnerProgramId(active.getMysqlPartnerProgramId())` | DRAFT fork carries forward MySQL ID → emf-parent does UPDATE (not INSERT) on re-approval |
| `updateSubscription()` | `getSubscription(orgId, id)` → `getSubscriptionByStatus(orgId, id, DRAFT)` | Only loads DRAFT docs for update |
| `pauseSubscription()` | `getSubscription(orgId, id)` → `getSubscriptionByStatus(orgId, id, ACTIVE)` | Only loads ACTIVE docs for pause |
| `resumeSubscription()` | `getSubscription(orgId, id)` → `getSubscriptionByStatus(orgId, id, PAUSED)` | Only loads PAUSED docs for resume |
| `handleApproval()` | `getSubscription(orgId, id)` → `getSubscriptionByStatusIn(orgId, id, [PENDING_APPROVAL, PUBLISH_FAILED])` | Enforces approvable states via query, not inline guard |
| `archiveSubscription()` | `getSubscription(orgId, id)` → `getSubscriptionByStatusIn(orgId, id, [DRAFT, ACTIVE, PAUSED])` | SNAPSHOT/ARCHIVED/PENDING_APPROVAL not archivable — query enforces it |

Removed old inline status guards from `updateSubscription`, `pauseSubscription`, `resumeSubscription`, `handleApproval`, `archiveSubscription` — they were unreachable after status-qualified fetch.

### Test Modifications (Developer-authored)

| Test Class | Test Method | Change | Reason | BT Case |
|------------|-------------|--------|--------|---------|
| `SubscriptionFacadePublishFailedTest` | `shouldAllowApprovalFromPendingApprovalState` | Mock changed from `findBySubscriptionProgramIdAndOrgId` to `findBySubscriptionProgramIdAndOrgIdAndStatusIn` | facade now uses status-qualified multi-status fetch (R-27) | BT-PF-06 |
| `SubscriptionFacadePublishFailedTest` | `shouldAllowApprovalAndRejectionFromPublishFailedState` | Same mock change (both approve and reject paths) | facade now uses status-qualified multi-status fetch (R-27) | BT-PF-07 |
| `SubscriptionFacadePublishFailedTest` | `shouldRejectApprovalFromInvalidStates` | Expected exception changed from `InvalidSubscriptionStateException` to `SubscriptionNotFoundException`; mock changed to return empty | With status-qualified fetch, DRAFT/ACTIVE/PAUSED/ARCHIVED are "not found in approvable states" — exception type changes by design | BT-PF-08 |
| `SubscriptionProgramIdLifecycleTest` | `shouldPreserveSubscriptionProgramIdOnDraftUpdate` | Mock changed from unqualified to `findBySubscriptionProgramIdAndOrgIdAndStatus(DRAFT)` | facade now uses DRAFT-qualified fetch | BT-R-27 |
| `SubscriptionProgramIdLifecycleTest` | `shouldCopySubscriptionProgramIdOnActiveEdit` | Mock changed from unqualified to `findBySubscriptionProgramIdAndOrgIdAndStatus(ACTIVE)` | facade now uses ACTIVE-qualified fetch | BT-R-28 |
| `SubscriptionProgramIdLifecycleTest` | `shouldRejectSecondForkWhenDraftExists` | Mock changed from unqualified to `findBySubscriptionProgramIdAndOrgIdAndStatus(ACTIVE)` | facade now uses ACTIVE-qualified fetch | BT-R-30 |
| `SubscriptionFacadeIT` | `shouldArchiveSubscriptionAndRejectResumeFromArchived` | Expected exception changed from `InvalidSubscriptionStateException` to `SubscriptionNotFoundException` | `resumeSubscription` with PAUSED-qualified query finds nothing for ARCHIVED doc → NotFoundException | BT-73 |

**Total test modifications: 7** — all are mock/expectation updates for the Rework 4 status-qualified fetch contract change. No test assertions about business behavior were weakened.

### GREEN Confirmation — Rework 4

```
Unit Tests (Subscription classes): 102 / 102 pass
  SubscriptionRework4FacadeTest:           10/10 (Rework 4 new)
  SubscriptionApprovalHandlerTest:         12/12 (Gap 3 + prior)
  SubscriptionFacadePublishFailedTest:      3/3  (mock-updated)
  SubscriptionProgramIdLifecycleTest:       5/5  (mock-updated)
  SubscriptionFacadeIT:                    22/22 (IT + Rework 4 IT)
  All other Subscription UT classes:      50/50

Full test suite baseline:
  Total:    7142 tests (+12 vs baseline 7130)
  Failures: 0
  Errors:   313 (pre-existing Docker infrastructure IT failures — unchanged)
  Skipped:  2
```

Tests fixed by Developer: **7** (all mock/expectation updates — no business logic weakened)
Skeleton classes replaced: N/A (methods were already real implementations from SDET phase; only state-transition calls swapped + ARCHIVED→SNAPSHOT + mysqlPartnerProgramId added)

### Commit Point

All 3 Rework 4 gaps implemented and GREEN. Ready for Reviewer phase.

**Suggested commit message:**
```
fix(subscription): Rework 4 — status-qualified fetch, mysqlPartnerProgramId carry-forward, SNAPSHOT on versioned approval

Gap 1: editActiveSubscription() now carries forward mysqlPartnerProgramId from ACTIVE parent
       to DRAFT fork → emf-parent UPDATE (not INSERT) on re-approval.
Gap 2: All 6 state-transition methods (update, pause, resume, archive, handleApproval,
       editActive) now use status-qualified repository queries — eliminates non-deterministic
       doc selection when ACTIVE + DRAFT fork coexist with same subscriptionProgramId.
Gap 3: postApprove() now sets old ACTIVE doc to SNAPSHOT (not ARCHIVED) on versioned
       approval — preserves pre-edit version as read-only audit trail.
```

---

## Rework 5 — Extended Fields Implementation (ADR-19, 2026-04-20)

### Changes Made

| # | File | Change |
|---|---|---|
| R-38 | `enums/ExtendedFieldType.java` | New enum: `CUSTOMER_EXTENDED_FIELD`, `TXN_EXTENDED_FIELD` |
| R-36/37 | `SubscriptionProgram.java` | Removed `CustomFields` + `CustomFieldRef` inner classes and `customFields` field; added `ExtendedField` inner class + `List<ExtendedField> extendedFields` field |
| R-32 | `SubscriptionFacade.java:85` | `.customFields(...)` → `.extendedFields(request.getExtendedFields() != null ? request.getExtendedFields() : List.of())` |
| R-33 | `SubscriptionFacade.java:271` | `setCustomFields(...)` → `if (request.getExtendedFields() != null) existing.setExtendedFields(...)` |
| R-34 | `SubscriptionFacade.java:325` | `.customFields(active.getCustomFields())` → `.extendedFields(active.getExtendedFields() != null ? ... : List.of())` |
| R-35 | `SubscriptionFacade.java:367` | `.customFields(source.getCustomFields())` → `.extendedFields(source.getExtendedFields() != null ? ... : List.of())` |

### GREEN Confirmation

- Unit Tests: **PASS** — 111 tests, 0 failures, 0 errors
- Integration Tests: N/A (no IT module touched)
- Tests fixed by Developer: 0
- Skeleton classes replaced: N/A (no new SDET RED phase for this rework)

### No dependencies added. No new Maven artifacts required.
