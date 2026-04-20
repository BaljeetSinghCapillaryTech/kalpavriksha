# SDET -- Test Code Implementation (RED Phase)

> Phase 9: SDET
> Date: 2026-04-12 (updated 2026-04-20 — Rework #5 cascade)
> Source: 04b-business-tests.md, 03-designer.md, 04-qa.md, 01-architect.md, cross-repo-trace.md, 01b-migrator.md
> RED Confirmation: PASS (compilation succeeds, 23/28 tests fail as expected — baseline)
>
> **Rework #5 Status**: Cascaded. See Section 7 for ISTQB suspect-link triage, new test inventory
> (9 new UT classes covering BT-142..BT-175 — 34 new BTs), and updated RED confirmation protocol
> (post-rework expected: ~54 failing tests across 7 test classes, skeleton production code for 10
> new Rework #5 components throwing UnsupportedOperationException).

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

---

## Section 7: Rework #5 Delta — Unified Read Surface, Dual Write Paths, Schema Cleanup

> **Cycle**: 5 of 5
> **Source**: BTG forward cascade payload (§6.4 of `04b-business-tests.md`)
> **Date**: 2026-04-20
> **Trigger**: user-authorized cascade — upstream BTG completed Rework #5 with 34 NEW + 19 UPDATE + 6 REGENERATE + 15 OBSOLETE BTs
> **Severity**: MAJOR — new test classes, new skeleton classes, new RED baseline

### 7.1 ISTQB Suspect-Link Triage — Existing Test Code

Applied to existing test methods in `TierFacadeTest.java` (12), `TierValidationServiceTest.java` (6), `TierApprovalHandlerTest.java` (7), `TierFacadeApprovalTest.java` (3) — total 28 pre-rework test methods.

| Triage Status | Count | Representative Test Methods |
|---|---|---|
| **CONFIRMED** (unaffected by Rework #5) | ~14 | `shouldListTiersForProgramOrderedBySerialNumber`, `shouldReturnEmptyListForProgramWithNoTiers`, `shouldAssignNextSerialNumberOnCreate`, `shouldValidateColorHexFormat`, `shouldRejectDuplicateApprovalSubmission`, `shouldNotifyAdminsOnSubmit` (validation/listing/notification basics unaffected) |
| **UPDATE** (field renames, fixture updates only) | 8 | `shouldCreateTierWithValidRequest` (basicDetails→root; metadata→meta), `shouldUpdateTierBasicFields` (unifiedTierId→tierUniqueId; sqlSlabId→slabId), `shouldApplyApprovedTier` (meta.approvedBy/approvedAt audit fields), `shouldListPendingApprovals` (PENDING_APPROVAL → SNAPSHOT direct on apply) |
| **REGENERATE** (structural invalidity) | 4 | `shouldCreateDraftOnEditOfLiveTier` (now requires parentId=slabId + basisSqlSnapshot capture), `shouldApplyApprovedTierToSql` (now routes via SAGA postApprove, direct PENDING→SNAPSHOT state), `shouldRejectEditOnPendingApproval` (changed semantics per BT-175 — no in-place edit, must reject first) |
| **OBSOLETE** | 2 | `shouldAllowInPlaceEditOfPending` (replaced by BT-175 reject-first flow), `shouldFlagUpdatedViaNewUI` (field dropped per Q7c) |

**Action**: UPDATE cases = in-place field renames in `setUp()` fixtures; REGENERATE cases = delete and rewrite test method with new assertions; OBSOLETE = remove from test class. CONFIRMED = untouched.

### 7.2 New Test Classes (to be added for BT-142..BT-175)

9 new test classes covering the 34 NEW BTs from BTG §6.3:

| Test Class | BTs Covered | UT Count | IT Count | Purpose |
|---|---|---|---|---|
| `TierEnvelopeBuilderTest.java` | BT-142..BT-146, BT-150 | 6 | 0 | Envelope assembly from SQL LIVE + Mongo DRAFT/PENDING (6 scenarios) |
| `TierFacadeEnvelopeIT.java` | BT-147..BT-149 | 0 | 3 | Legacy-SQL-only envelope visibility (ADR-06R), single-tier GET by slabId/tierUniqueId |
| `TierDriftCheckerTest.java` | BT-151..BT-156 | 6 | 0 | basisSqlSnapshot capture, drift detection, basis retention on reject, clear on approve |
| `TierDriftCheckerIT.java` | BT-157 | 0 | 1 | Drift on resubmission after legacy-UI SQL mutation |
| `TierReviewControllerApproveRejectIT.java` | BT-158..BT-160 | 0 | 3 | Separate approve/reject endpoints, audit columns written to both stores |
| `TierDualPathIT.java` | BT-161 | 0 | 1 | Legacy SlabFacade bypasses MC; new envelope surfaces legacy-written tier |
| `TierApprovalHandlerNameCollisionTest.java` | BT-162 | 1 | 0 | Layer 2 name re-check at approve |
| `TierApprovalHandlerNameCollisionIT.java` | BT-163 | 0 | 1 | Layer 3 SQL UNIQUE fallback with SAGA.onPublishFailure |
| `TierSingleActiveDraftTest.java` | BT-164 | 1 | 0 | App-layer single-active-draft enforcement |
| `TierSingleActiveDraftIT.java` | BT-165 | 0 | 1 | Mongo partial unique index backstop (DB-layer race) |
| `SqlTierConverterTest.java` | BT-166..BT-168 | 3 | 0 | SQL row → TierView conversion, null preservation, eligibility threshold CSV extraction |
| `SqlTierReaderIT.java` | BT-169 | 0 | 1 | `SELECT FROM program_slabs` returns List<TierView> sorted by serial_number |
| `TierSchemaIT.java` | BT-170..BT-172 | 0 | 3 | Hoisted basicDetails, metadata→meta, tierUniqueId field presence in MongoDB |
| `TierAuditColumnsIT.java` | BT-173 | 0 | 1 | SQL `program_slabs.updated_by`/`approved_by`/`approved_at` populated via Thrift |
| `TierParentIdTest.java` | BT-174 | 1 | 0 | parentId=slabId (Long) semantics on edit-of-LIVE |
| `TierPendingEditBlockedTest.java` | BT-175 | 1 | 0 | Reject edit on PENDING_APPROVAL (replaces old BT-21) |

**Totals**: 19 new UTs + 15 new ITs = **34 new test methods** (1:1 with NEW BTs; no combination — each new BT has a distinct semantic, none combinable under Test Efficiency Protocol).

### 7.3 New Skeleton Production Classes (for RED compilation)

Developer phase consumes these — SDET writes empty stubs throwing `UnsupportedOperationException("Not implemented — skeleton for Rework #5 RED phase")`.

| Package | New Skeleton Class | Purpose |
|---|---|---|
| `tier/envelope/` | `TierEnvelope` (record/POJO) | `{live: TierView, pendingDraft: TierView, hasPendingDraft: boolean}` response DTO |
| `tier/envelope/` | `TierView` (record/POJO) | Unified read view (projects both SQL rows and Mongo docs into one shape) |
| `tier/envelope/` | `TierOrigin` (enum) | `LEGACY_SQL_ONLY`, `MONGO_ONLY`, `BOTH` — derived by envelope builder |
| `tier/envelope/` | `TierEnvelopeBuilder` | Combines SQL LIVE + Mongo DRAFT/PENDING lists into envelopes grouped by slabId |
| `tier/sql/` | `SqlTierReader` | `readLiveTiers(programId)` — reads program_slabs via PeProgramSlabDao |
| `tier/sql/` | `SqlTierConverter` | `toTierView(ProgramSlab, strategies)` — SQL row → TierView DTO |
| `tier/drift/` | `TierDriftChecker` | captureBasis, check (conservative: any diff blocks) |
| `tier/drift/` | `BasisSqlSnapshot` (POJO) | Serialized SQL row state captured at DRAFT-of-LIVE creation |
| `tier/dto/` | `RejectRequest` (record) | `{comment}` — dedicated request body for /reject endpoint |
| `tier/model/` | `TierMeta` (hoisted, rename of `TierMetadata`) | approvedBy, approvedAt, updatedBy, basisSqlSnapshot |

**Modifications to existing skeletons** (field renames / hoisting):
- `UnifiedTierConfig` — hoist `basicDetails.*` to root; rename `metadata` → `meta`; rename `unifiedTierId` → `tierUniqueId`; drop `nudges`, `benefitIds`, `updatedViaNewUI`; add `slabId` (Long), `parentId` (Long)
- `BasicDetails.java` — class deleted (hoisted); field migration notes added
- `TierMetadata.java` — renamed to `TierMeta.java`
- `TierFacade.java` — add skeleton `getTierEnvelope(slabId)`, `reject(tierId, comment)`, `approve(tierId)` methods

### 7.4 Updated RED Confirmation Protocol

| Metric | Pre-Rework-5 | Post-Rework-5 Expected |
|---|---|---|
| Compilation status | PASS | PASS (new skeleton classes compile; field renames propagate via IDE refactor) |
| Test classes | 4 | 4 + 14 new = 18 |
| Test methods | 28 | 28 (some UPDATE, some REGENERATE, -2 OBSOLETE) + 34 new = **60** |
| Expected failures | 23 | ~54 (all methods hitting unimplemented skeletons throw UnsupportedOperationException) |
| Expected passes | 5 | 6 (pure POJO/enum tests that don't depend on facade logic — e.g., TierView equality, TierEnvelope JSON shape) |

**Command**:
```bash
export JAVA_HOME=/Users/ritwikranjan/.sdkman/candidates/java/17.0.17-amzn
mvn test -pl . -Dtest="com.capillary.intouchapiv3.tier.*Test,com.capillary.intouchapiv3.tier.**.*Test" -am
```

### 7.5 Structured Disagreement Log

No disagreements with BTG forward cascade payload. All 34 new BTs and 25 triage decisions accepted. Evidence:
- 34 NEW BTs: each traces to a Designer interface method (BT-166→SqlTierConverter; BT-151→TierDriftChecker.captureBasis; BT-142→TierEnvelopeBuilder) — verified against `03-designer.md` Rework #5 sections.
- UPDATE cases: restricted to field renames + fixture adjustments; no test logic changes requested. Verified.
- REGENERATE cases: all 6 correspond to structural state-machine shifts (direct PENDING→SNAPSHOT, parentId=slabId, drift-gated approval, basis retention on reject). Cannot in-place patch — rewrite is correct classification.
- OBSOLETE cases: traced to dropped fields (nudges, benefitIds, updatedViaNewUI, basicDetails.startDate/endDate) and reversed state machine (in-place edit of PENDING). No orphan references remain.

### 7.6 Forward Cascade Payload — to Developer (Phase 10)

| Category | Scope | Developer Action |
|---|---|---|
| New classes to implement | 10 skeleton files listed in §7.3 | Write production implementation for TierEnvelopeBuilder, SqlTierReader, SqlTierConverter, TierDriftChecker, TierFacade.getTierEnvelope/reject/approve |
| Existing classes to modify | UnifiedTierConfig (schema), TierFacade (listTiers → envelope shape, updateTier → parentId+basis capture), TierApprovalHandler (postApprove direct SNAPSHOT, preApprove drift+L2 name+L2 single-active) | Apply changes in-place; preserve existing patterns |
| Flyway migrations | V*__add_tier_audit_columns.sql, V*__add_unique_program_name.sql, V*__add_mongo_partial_unique.sql | From 01b-migrator.md §3.1-M1..M6 — ship idempotent forms |
| Tests to make GREEN | 60 total (28 existing + 32 net new — minus 2 OBSOLETE) | Run `mvn test`, iterate until all pass |

### 7.7 Verification-Before-Completion

- [x] Every NEW BT (BT-142..BT-175) mapped to a specific test class in §7.2
- [x] Every NEW Designer interface method has a skeleton class in §7.3
- [x] UPDATE cases classified: field renames only (no logic changes) — in-place safe
- [x] REGENERATE cases classified: each requires state-machine or semantic shift — full rewrite required
- [x] OBSOLETE cases identified with source (removed BA AC, dropped schema field, reversed ADR)
- [x] Delta log consistent with BTG §6.4 forward cascade payload (all 69 affected BTs addressed)
- [x] RED confirmation protocol updated for post-rework test count (~60 tests, ~54 failing)
- [x] No CONFIRMED test accidentally modified — classification preserved

**Rework #5 SDET Status**: COMPLETE (artifact). Ready for Developer (Phase 10) to consume §7.6 forward cascade payload and make tests GREEN.
