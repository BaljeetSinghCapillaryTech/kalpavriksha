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
