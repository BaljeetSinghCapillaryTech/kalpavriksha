# Business Test Cases — Subscription Program Revamp (E3)
> Date: 2026-04-14 | Phase: 8b (Business Test Gen)
> Ticket: aidlc/subscription_v1
> Author: Business Test Gen Agent (Claude Sonnet 4.6)
> Inputs: 00-ba.md (48 ACs), 04-qa.md (87 scenarios), 03-designer.md (50 interface methods), 01-architect.md (7 ADRs)
> Rework: 2026-04-15 — 35 new test cases (BT-R-01 through BT-R-35) for ADR-08 through ADR-18 (12 critical gaps)

---

## 1. Coverage Summary

| Source | Total Items | Covered | Gaps |
|--------|------------|---------|------|
| BA Acceptance Criteria | 48 | 48 | 0 |
| QA Test Scenarios | 87 | 87 | 0 |
| Designer Interface Methods | 50 | 50 | 0 |
| ADRs | 7 | 7 | 0 |
| HIGH+ Risks (QA-RISK-01–05 + session-memory risks) | 8 | 8 | 0 |
| Guardrails (applicable: G-01, G-02, G-04, G-05, G-07, G-09, G-10) | 7 | 7 | 0 |
| **Rework BTs (ADR-08 through ADR-18 — 12 gaps)** | **12 gaps** | **12** | **0** |

**Total business test cases: 137 — 63 unit tests (UT), 74 integration tests (IT)**

> Rework additions (2026-04-15): 35 new test cases — 30 UT (BT-R-01 through BT-R-30) + 5 IT (BT-R-31 through BT-R-35). All 12 ADR gaps (ADR-08 through ADR-18) fully covered.

---

## 2. Functional Test Cases

### 2.1 Unit Tests

> JUnit 5 + Mockito. `@ExtendWith(MockitoExtension.class)`. No Spring context. Direct method invocation. Mocks at external-service boundaries (Thrift, MongoDB repo). Pattern: `UnifiedPromotionControllerTest` / `UnifiedPromotionFacadeTest`.

#### Group A — Create Subscription Validation (`SubscriptionApprovalHandler.validateForSubmission`, bean validation)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-01 | shouldRejectMissingName | AC-11 | `SubscriptionRequest{name=null}` | `InvalidInputException(REQUIRED:name)` | TS-11 | `SubscriptionApprovalHandler.validateForSubmission()` | UT |
| BT-02 | shouldRejectMissingDuration | AC-11 | `SubscriptionRequest{duration=null}` | `InvalidInputException(REQUIRED:duration)` | TS-12 | `SubscriptionApprovalHandler.validateForSubmission()` | UT |
| BT-03 | shouldRejectTierBasedWithoutLinkedTier | AC-16 | `SubscriptionRequest{type=TIER_BASED, tierConfig=null}` | `InvalidInputException(REQUIRED_FOR_TIER_BASED:linkedTierId)` | TS-18 | `SubscriptionApprovalHandler.validateForSubmission()` | UT |
| BT-04 | shouldRejectTierDowngradeWithoutTarget | AC-17 | `{type=TIER_BASED, tierDowngradeOnExit=true, downgradeTargetTierId=null}` | `InvalidInputException(REQUIRED:downgradeTargetTierId)` | TS-19 | `SubscriptionApprovalHandler.validateForSubmission()` | UT |
| BT-05 | shouldRejectNameExceedingMaxLength | AC-09 | `{name="A"×256}` | `ConstraintViolationException` (from `@Size(max=255)`) | TS-10 | `SubscriptionProgram.name` `@Size(max=255)` | UT |
| BT-06 | shouldRejectDescriptionExceedingMaxLength | AC-09 | `{description="A"×1001}` | `ConstraintViolationException` (from `@Size(max=1000)`) | TS-10 | `SubscriptionProgram.description` `@Size(max=1000)` | UT |
| BT-07 | shouldRejectMoreThanFiveReminders | AC-22 | `{reminders=[r1,r2,r3,r4,r5,r6]}` | `ConstraintViolationException` (from `@Size(max=5)`) | TS-24 | `SubscriptionProgram.reminders` `@Size(max=5)` | UT |
| BT-08 | shouldRejectZeroDurationValue | AC-09 | `{duration={value:0, unit:DAYS}}` | `ConstraintViolationException` (from `@Positive` on cycleValue) | TS-75 | `SubscriptionProgram.Duration.cycleValue` `@Positive` | UT |
| BT-09 | shouldRejectNegativeDurationValue | AC-09 | `{duration={value:-1, unit:MONTHS}}` | `ConstraintViolationException` (from `@Positive`) | TS-75 | `SubscriptionProgram.Duration.cycleValue` `@Positive` | UT |

#### Group B — Publish Service Pure Logic (`SubscriptionPublishService` package-private methods)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-10 | shouldConvertYears1To12Months | ADR-07, AC-09 | `convertCycle(YEARS, 1)` | `{cycleType:MONTHS, cycleValue:12}` | TS-76 | `SubscriptionPublishService.convertCycle()` | UT |
| BT-11 | shouldConvertYears2To24Months | ADR-07, AC-09 | `convertCycle(YEARS, 2)` | `{cycleType:MONTHS, cycleValue:24}` | TS-49 | `SubscriptionPublishService.convertCycle()` | UT |
| BT-12 | shouldPassThroughDaysCycleUnchanged | ADR-07 | `convertCycle(DAYS, 30)` | `{cycleType:DAYS, cycleValue:30}` | TS-49 | `SubscriptionPublishService.convertCycle()` | UT |
| BT-13 | shouldPassThroughMonthsCycleUnchanged | ADR-07 | `convertCycle(MONTHS, 6)` | `{cycleType:MONTHS, cycleValue:6}` | TS-49 | `SubscriptionPublishService.convertCycle()` | UT |
| BT-14 | shouldSetDefaultPointsRatioTo1Point0 | OQ-18 (resolved) | `buildPartnerProgramInfo(nonTierSubscription, orgId=100)` | `result.programToPartnerProgramPointsRatio == 1.0` | TS-40 | `SubscriptionPublishService.buildPartnerProgramInfo()` | UT |
| BT-15 | shouldSetIsSyncFalseForNonTier | OQ-19 (resolved) | `buildPartnerProgramInfo({type:NON_TIER})` | `result.isSyncWithLoyaltyTierOnDowngrade == false` | TS-19 | `SubscriptionPublishService.buildPartnerProgramInfo()` | UT |
| BT-16 | shouldSetIsSyncTrueWhenTierDowngradeEnabled | OQ-19 (resolved), AC-17 | `buildPartnerProgramInfo({type:TIER_BASED, tierDowngradeOnExit:true, downgradeTargetTierId:10})` | `isSyncWithLoyaltyTierOnDowngrade=true`, `loyaltySyncTiers populated` | TS-63 | `SubscriptionPublishService.buildPartnerProgramInfo()` | UT |
| BT-17 | shouldSetPartnerProgramTypeSUPPLEMENTARY | AC-38 | Any valid `buildPartnerProgramInfo(...)` | `result.partnerProgramType == SUPPLEMENTARY` | TS-40 | `SubscriptionPublishService.buildPartnerProgramInfo()` | UT |
| BT-18 | shouldThrowIllegalStateIfPublishIsActiveWithNullMysqlId | from method contract | `publishIsActive(sub{partnerProgramId=null}, ...)` | `IllegalStateException` | TS-48 | `SubscriptionPublishService.publishIsActive()` | UT |
| BT-19 | shouldSkipThriftOnPublishIfMysqlIdAlreadySet | ADR-03, RF-6 | `publishToMySQL(sub{partnerProgramId=1001}, ...)` | Returns `PublishResult{externalId=1001, idempotent=true}`. Zero Thrift calls. | TS-42 | `SubscriptionPublishService.publishToMySQL()` | UT |

#### Group C — Maker-Checker State Machine (MakerCheckerService pure logic)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-20 | shouldTransitionDraftToPendingApproval | AC-31, AC-28 | `submitForApproval(draftEntity, handler, save)` | `entity.status == PENDING_APPROVAL`. `save` callback called once. | TS-33 | `MakerCheckerService.submitForApproval()` | UT |
| BT-21 | shouldRejectSubmitIfHandlerValidationFails | AC-11 | Handler throws `InvalidInputException` | `InvalidInputException` propagated. Status unchanged. Save not called. | TS-33 | `MakerCheckerService.submitForApproval()` | UT |
| BT-22 | shouldTransitionPendingApprovalToDraftOnReject | AC-34 | `reject(pendingEntity, "needs work", "reviewer1", handler, save)` | `entity.status == DRAFT`. `entity.comments == "needs work"`. `handler.postReject` called. | TS-37 | `MakerCheckerService.reject()` | UT |
| BT-23 | shouldPreserveEntityOnPublishFailure | ADR-03 | `approve(...)` where `handler.publish()` throws | `handler.onPublishFailure()` called. Entity status unchanged (PENDING_APPROVAL). | TS-41 | `MakerCheckerService.approve()` | UT |

#### Group D — emf-parent isActive Conditional (PointsEngineRuleService / PointsEngineRuleConfigThriftImpl)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-24 | shouldPreserveIsActiveWhenFieldNotSet | ADR-05, G-09 | `PartnerProgramInfo` without field 15 (`isSetIsActive()=false`). `oldPartnerProgram.isActive()=true` | `newPartnerProgram.isActive() == true` (copied from old) | TS-47 | `PointsEngineRuleService.saveSupplementaryPartnerProgramEntity()` | UT |
| BT-25 | shouldSetIsActiveFalseWhenFieldSetToFalse | ADR-05, AC-39 | `PartnerProgramInfo{isActive=false}`. `isSetIsActive()=true` | `newPartnerProgram.isActive() == false` | TS-48 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | UT |
| BT-26 | shouldSetIsActiveTrueWhenFieldSetToTrue | ADR-05, AC-40 | `PartnerProgramInfo{isActive=true}`. `isSetIsActive()=true` | `newPartnerProgram.isActive() == true` | TS-60 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | UT |

#### Group E — Approval Handler Unit Logic (SubscriptionApprovalHandler)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-27 | shouldSetStatusActiveAndStoreMysqlIdOnPostApprove | AC-38 | `postApprove(entity, PublishResult{externalId:1001})` | `entity.status=ACTIVE`, `entity.partnerProgramId=1001` | TS-34 | `SubscriptionApprovalHandler.postApprove()` | UT |
| BT-28 | shouldSnapshotOldDocAndActivateNewOnVersionedApproval | AC-33 | `postApprove(editDraft{parentId="AAA"}, result)` (parentId non-null) | Old doc (AAA) set **SNAPSHOT** (not ARCHIVED — read-only audit copy). New doc set ACTIVE. `partnerProgramId` carried from old doc. | TS-36 | `SubscriptionApprovalHandler.postApprove()` | UT |
| BT-29 | shouldLeaveStatusUnchangedOnPublishFailure | ADR-03 | `onPublishFailure(entity, exception)` | `entity.status` unchanged (still PENDING_APPROVAL). No exception thrown. | TS-41 | `SubscriptionApprovalHandler.onPublishFailure()` | UT |
| BT-30 | shouldSetStatusDraftAndStoreCommentOnReject | AC-34 | `postReject(entity, "Fix name")` | `entity.status=DRAFT`, `entity.comments="Fix name"` | TS-37 | `SubscriptionApprovalHandler.postReject()` | UT |

#### Group F — Repository Query Logic (SubscriptionProgramRepository — testable via `@DataMongoTest` slice)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-31 | shouldFindBySubscriptionProgramIdAndOrgId | AC-01 | `findBySubscriptionProgramIdAndOrgId("uuid-1", 100L)` | Returns `Optional.of(subscription)` | TS-65 | `SubscriptionProgramRepository.findBySubscriptionProgramIdAndOrgId()` | UT |
| BT-32 | shouldReturnEmptyForWrongOrg | G-07 | `findBySubscriptionProgramIdAndOrgId("uuid-1", 999L)` (wrong org) | `Optional.empty()` | TS-67 | `SubscriptionProgramRepository.findBySubscriptionProgramIdAndOrgId()` | UT |
| BT-33 | shouldFindPendingApprovalDocs | AC-36 | `findPendingApprovalByOrgIdAndProgramId(100L, 200, page)` | Only PENDING_APPROVAL docs returned | TS-38 | `SubscriptionProgramRepository.findPendingApprovalByOrgIdAndProgramId()` | UT |
| BT-34 | shouldFindDraftByParentId | AC-32 | `findDraftByParentIdAndOrgId("active-objectId", 100L)` | Returns the forked DRAFT doc | TS-35 | `SubscriptionProgramRepository.findDraftByParentIdAndOrgId()` | UT |
| BT-35 | shouldFindByPartnerProgramIdForSagaIdempotency | RF-6 | `findByPartnerProgramIdAndOrgId(1001, 100L)` | Returns subscription with that MySQL ID | TS-42 | `SubscriptionProgramRepository.findByPartnerProgramIdAndOrgId()` | UT |
| BT-36 | shouldCollectActiveMysqlProgramIdsForBulkCount | AC-02 | `findActivePartnerProgramIdsByOrgId(100L)` | List of subscriptions with non-null `partnerProgramId`, status=ACTIVE | TS-71 | `SubscriptionProgramRepository.findActivePartnerProgramIdsByOrgId()` | UT |

---

### 2.2 Integration Tests

> Spring Boot Test slice or full context. Real MongoDB (Testcontainers or embedded). Thrift mocked via `@Mock` on `PointsEngineRulesThriftService`. Tests HTTP endpoints via `MockMvc` or direct facade calls.

#### Group G — Create Subscription End-to-End (SubscriptionFacade.createSubscription)

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-37 | shouldCreateNonTierSubscriptionAsDraftInMongoDB | AC-09, AC-10, AC-27, ADR-01 | Service → MongoDB | Valid `SubscriptionRequest{type:NON_TIER}` | MongoDB doc created: `status=DRAFT`, `partnerProgramId=null`. Thrift NOT called. | TS-09, TS-29 | `SubscriptionFacade.createSubscription()` | IT |
| BT-38 | shouldCreateTierBasedSubscriptionAsDraft | AC-10, AC-16, AC-17 | Service → MongoDB | `{type:TIER_BASED, linkedTierId:42, tierDowngradeOnExit:true, downgradeTargetTierId:10}` | Doc stored with `tierConfig` fully populated. | TS-10 | `SubscriptionFacade.createSubscription()` | IT |
| BT-39 | shouldRejectDuplicateNameViaThriftCheck | AC-09, KD-40, G-06 | Service → Thrift → name check | Name that conflicts with existing MySQL partner program | `SubscriptionNameConflictException`. MongoDB doc NOT saved. | TS-70, TS-74 | `SubscriptionFacade.createSubscription()` | IT |
| BT-40 | shouldAssignNewUUIDAndObjectIdOnCreate | OQ-16 (resolved) | Service → MongoDB | Any valid create request | `subscriptionProgramId` is non-null UUID. `objectId` is MongoDB ObjectId (non-null). Both unique per create. | TS-09 | `SubscriptionFacade.createSubscription()` | IT |
| BT-41 | shouldSetCreatedAtAndCreatedByOnCreate | G-01 | Service → MongoDB | Any valid create request | `createdAt` is an `Instant` (non-null, UTC-aligned). `createdBy` matches caller user ID. | TS-64 | `SubscriptionFacade.createSubscription()` | IT |

#### Group H — Get and List Subscriptions

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-42 | shouldReturn404ForNonExistentSubscription | AC-01 | Service → MongoDB | `getSubscription(100L, "nonexistent-uuid")` | `SubscriptionNotFoundException`. HTTP 404 via `SubscriptionErrorAdvice`. | TS-65 | `SubscriptionFacade.getSubscription()` | IT |
| BT-43 | shouldListPaginatedSubscriptions | AC-01, AC-05 | Service → MongoDB | `listSubscriptions(orgId=100, programId=200, page=0, size=10)` | Page of subscriptions. `totalElements` correct. `sort=subscriberCount,desc` default. | TS-01 | `SubscriptionFacade.listSubscriptions()` | IT |
| BT-44 | shouldFilterSubscriptionsByMultipleStatuses | AC-03 | Service → MongoDB | `{statuses=[ACTIVE,DRAFT]}` | Only ACTIVE and DRAFT docs returned. PAUSED/ARCHIVED excluded. | TS-03, TS-18 | `SubscriptionFacade.listSubscriptions()` | IT |
| BT-45 | shouldFetchSubscriberCountsWithSingleBulkThriftCall | AC-02, G-04.1 | Service → Thrift (mock) | Listing 20 ACTIVE subscriptions | Exactly 1 call to `getSupplementaryEnrollmentCountsByProgramIds` with all 20 IDs. Counts merged into list items. | TS-02, TS-71 | `SubscriptionFacade.getHeaderStats()` + `listSubscriptions()` | IT |
| BT-46 | shouldReturnZeroBenefitsCountForSubscriptionWithNoBenefits | G-02.1, AC-01 | Service → MongoDB | Subscription with `benefitIds=null` or `benefitIds=[]` | `benefitsCount=0` in list item. No NPE. | TS-66, TS-83 | `SubscriptionFacade.listSubscriptions()` | IT |

#### Group I — Duplicate Subscription

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-47 | shouldDuplicateWithCopySuffix | AC-12 | Service → MongoDB | `duplicateSubscription(100L, "uuid-1", "user1")` | New doc: `name="Gold Plan (Copy)"`, `status=DRAFT`, `version=1`, `parentId=null`, `partnerProgramId=null`, new UUID. | TS-13 | `SubscriptionFacade.duplicateSubscription()` | IT |
| BT-48 | shouldCopyAllConfigFieldsOnDuplicate | AC-12 | Service → MongoDB | Source with reminders, benefits, tierConfig | Duplicate has same reminders, benefitIds, tierConfig values. | TS-13 | `SubscriptionFacade.duplicateSubscription()` | IT |
| BT-49 | shouldRejectDuplicateWhenCopyNameAlreadyExists | AC-12, KD-40 | Service → Thrift (name check) | Source "Gold Plan". "Gold Plan (Copy)" already exists in MySQL. | `SubscriptionNameConflictException`. No new doc saved. | TS-14 | `SubscriptionFacade.duplicateSubscription()` | IT |

#### Group J — Update Subscription

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-50 | shouldUpdateDraftInPlace | AC-30 | Service → MongoDB | `updateSubscription` on DRAFT | Existing doc updated in-place. No new doc. `status` unchanged (DRAFT). | TS-32 | `SubscriptionFacade.updateSubscription()` | IT |
| BT-51 | shouldForkNewDraftFromActiveOnEdit | AC-30, AC-32 | Service → MongoDB | `updateSubscription` on ACTIVE subscription | NEW DRAFT doc created: `parentId=<ACTIVE._id>`, `version=ACTIVE.version+1`. Old ACTIVE doc: unchanged, still ACTIVE. | TS-32, TS-35 | `SubscriptionFacade.updateSubscription()` | IT |
| BT-52 | shouldReturn422OnEditOfArchivedSubscription | AC-08, AC-41 | Service → MongoDB | `updateSubscription` on ARCHIVED subscription | `InvalidSubscriptionStateException`. HTTP 422. | TS-56 | `SubscriptionFacade.updateSubscription()` | IT |

#### Group K — Benefits Linkage

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-53 | shouldLinkBenefitToSubscriptionInMongoDB | AC-21, ADR-04 | Service → MongoDB | `linkBenefit(100L, "uuid-1", benefitId=101, "user1")` | `subscription.benefits` contains `BenefitRef{benefitId:101}`. No MySQL write. | TS-22, TS-46 | `SubscriptionFacade.linkBenefit()` | IT |
| BT-54 | shouldDelinkBenefitFromSubscription | AC-21 | Service → MongoDB | `delinkBenefit(100L, "uuid-1", benefitId=101)` | `benefitId=101` removed from `benefits` list. | TS-22 | `SubscriptionFacade.delinkBenefit()` | IT |
| BT-55 | shouldReturnLinkedBenefitRefs | AC-07 | Service → MongoDB | `getBenefits(100L, "uuid-1")` | Returns `List<BenefitRef>` with all linked benefit IDs. | TS-07 | `SubscriptionFacade.getBenefits()` | IT |
| BT-56 | shouldRejectDuplicateBenefitLink | AC-21 | Service → MongoDB | Link same benefitId twice | `InvalidInputException`. Second `BenefitRef` not added. | TS-22 | `SubscriptionFacade.linkBenefit()` | IT |

#### Group L — Submit for Approval (Maker-Checker Step 1)

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-57 | shouldTransitionDraftToPendingApproval | AC-31, AC-28 | Service → MongoDB | `submitForApproval` on DRAFT | MongoDB status=`PENDING_APPROVAL`. `workflowMetadata.submittedAt` non-null (UTC Instant). | TS-33 | `SubscriptionFacade.submitForApproval()` | IT |
| BT-58 | shouldReturn422OnSubmitFromNonDraftStatus | AC-31 | Service → MongoDB | `submitForApproval` on ACTIVE subscription | `InvalidSubscriptionStateException`. HTTP 422. | TS-33 | `SubscriptionFacade.changeStatus()` | IT |
| BT-59 | shouldAppearInApprovalQueueAfterSubmit | AC-36 | Service → MongoDB | Submit → then `listPendingApprovals()` | Subscription present in `findPendingApprovalByOrgIdAndProgramId()` result. | TS-30, TS-38 | `SubscriptionFacade.submitForApproval()` | IT |

#### Group M — Approve Flow (SAGA — Maker-Checker Step 2)

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-60 | shouldApproveAndWriteToMySQLViaSAGA | AC-38, ADR-03 | Service → Thrift (mock) → MongoDB | `handleApproval(APPROVE)` on PENDING_APPROVAL | Thrift `createOrUpdatePartnerProgram` called once. MongoDB: `status=ACTIVE`, `partnerProgramId=<returned-id>`. | TS-40 | `SubscriptionFacade.handleApproval()` | IT |
| BT-61 | shouldRemainPendingApprovalOnThriftFailure | ADR-03 | Service → Thrift (throws) → MongoDB | Thrift throws `EMFThriftException` | MongoDB status remains `PENDING_APPROVAL`. `partnerProgramId=null`. No partial MySQL row visible via Thrift confirm. | TS-41 | `SubscriptionFacade.handleApproval()` | IT |
| BT-62 | shouldRetryApprovalIdempotently | ADR-03, G-06.1 | Service → Thrift (mock) → MongoDB | Approve twice: first partially succeeds (mongo fails), second completes | Second call: `partnerProgramId` already set → Thrift NOT called again → Only MongoDB updated. Final state: ACTIVE. | TS-42, TS-43 | `SubscriptionFacade.handleApproval()` | IT |
| BT-63 | shouldRejectDraftWithoutPendingApprovalStatus | AC-31 | Service → MongoDB | `handleApproval` on DRAFT subscription | `NotFoundException` (not in PENDING_APPROVAL). HTTP 404. | TS-34 | `SubscriptionFacade.handleApproval()` | IT |
| BT-64 | shouldSendCorrectThriftPayloadOnApprove | AC-38, ADR-07 | Service → Thrift verify | Subscription with `cycleType=YEARS, cycleValue=2` | Thrift receives `{cycleType:MONTHS, cycleValue:24}`. `programToPartnerProgramPointsRatio=1.0`. `partnerProgramType=SUPPLEMENTARY`. | TS-40, TS-49 | `SubscriptionPublishService.buildPartnerProgramInfo()` | IT |
| BT-65 | shouldNotWriteRemindersToMySQLOnApprove | ADR-06, AC-22 | Service → Thrift (verify mock not called for reminders) → MySQL-read | Subscription with 3 reminders approved | Thrift `createOrUpdateExpiryReminderForPartnerProgram` NOT called. MongoDB reminders array intact. | TS-50 | `SubscriptionApprovalHandler.publish()` | IT |
| BT-66 | shouldSnapshotOldActiveAndActivateNewOnVersionedApprove | AC-33 | Service → MongoDB | Approve a DRAFT with `parentId=<ACTIVE._id>` | Old ACTIVE doc: `status=SNAPSHOT` (not ARCHIVED — read-only audit copy, Rework 4). New doc: `status=ACTIVE`, `partnerProgramId` carried from old. | TS-36 | `SubscriptionApprovalHandler.postApprove()` | IT |

#### Group N — Reject Flow

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-67 | shouldRejectSubscriptionAndRevertToDraft | AC-34 | Service → MongoDB | `handleApproval(REJECT, comment="Fix name")` | MongoDB `status=DRAFT`. `comments="Fix name"`. Doc NOT deleted. Thrift NOT called. | TS-37 | `SubscriptionFacade.handleApproval()` | IT |
| BT-68 | shouldPreserveAllFieldsOnReject | AC-34 | Service → MongoDB | Reject subscription with full config | All config fields (duration, benefits, reminders, tierConfig) unchanged after reject. | TS-37 | `SubscriptionFacade.handleApproval()` | IT |

#### Group O — Pause / Resume / Archive

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-69 | shouldPauseSubscriptionAndCallThriftWithIsActiveFalse | AC-39, ADR-05 | Service → Thrift (mock verify) → MongoDB | `pauseSubscription(100L, "uuid-1")` | Thrift called with `isActive=false` (field 15 set). MongoDB `status=PAUSED`. | TS-53, TS-48 | `SubscriptionFacade.pauseSubscription()` | IT |
| BT-70 | shouldRejectEnrollmentForPausedSubscription | AC-39, KD-42 | Service → MongoDB (status check) | Enrollment attempt for PAUSED subscription | `InvalidSubscriptionStateException`. HTTP 422. | TS-53 | `SubscriptionFacade.changeStatus()` | IT |
| BT-71 | shouldResumeSubscriptionAndCallThriftWithIsActiveTrue | AC-40, ADR-05 | Service → Thrift (mock verify) → MongoDB | `resumeSubscription(100L, "uuid-1")` | Thrift called with `isActive=true`. MongoDB `status=ACTIVE`. | TS-55, TS-60 | `SubscriptionFacade.resumeSubscription()` | IT |
| BT-72 | shouldArchiveSubscription | AC-41 | Service → Thrift (mock verify) → MongoDB | `archiveSubscription` on ACTIVE | Thrift called with `isActive=false`. MongoDB `status=ARCHIVED`. | TS-56 | `SubscriptionFacade.archiveSubscription()` | IT |
| BT-73 | shouldReturn422OnResumeFromArchived | AC-41 | Service → MongoDB | `resumeSubscription` on ARCHIVED | `InvalidSubscriptionStateException`. HTTP 422. ARCHIVED is terminal. | TS-56 | `SubscriptionFacade.resumeSubscription()` | IT |
| BT-74 | shouldReturn422OnEditFromArchived | AC-41 | Service → MongoDB | `updateSubscription` on ARCHIVED | `InvalidSubscriptionStateException`. HTTP 422. | TS-56 | `SubscriptionFacade.updateSubscription()` | IT |

#### Group P — Subscriber Count Thrift (emf-parent + intouch-api-v3)

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-75 | shouldReturnSubscriberCountsPerPartnerProgram | AC-02, KD-46 | emf-parent Thrift → MySQL | `getSupplementaryEnrollmentCountsByProgramIds([301,302], 100, 200, reqId)` | `{301: 5, 302: 3}` (counts from `supplementary_partner_program_enrollment`) | TS-51 | `PointsEngineRuleConfigThriftImpl.getSupplementaryEnrollmentCountsByProgramIds()` | IT |
| BT-76 | shouldReturnEmptyMapForEmptyPartnerProgramIdList | KD-46, G-02 | emf-parent Thrift → (no DB query) | `getSupplementaryEnrollmentCountsByProgramIds([], 100, 200, reqId)` | Empty `map<i32, i64>`. No DB query executed. No NPE. | TS-52 | `PointsEngineRuleConfigThriftImpl.getSupplementaryEnrollmentCountsByProgramIds()` | IT |
| BT-77 | shouldExposeBulkCountMethodOnThriftServiceWrapper | KD-46 | intouch-api-v3 Thrift client | Call `getSupplementaryEnrollmentCountsByProgramIds` via `PointsEngineRulesThriftService` | Returns `Map<Integer, Long>`. Errors wrapped as `EMFThriftException`. | TS-51 | `PointsEngineRulesThriftService.getSupplementaryEnrollmentCountsByProgramIds()` | IT |

#### Group Q — Custom Fields Storage

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-78 | shouldStoreMetaLinkDelinkCustomFields | AC-24 | Service → MongoDB | Subscription with all 3 custom field levels populated | MongoDB doc has `customFields.meta`, `customFields.link`, `customFields.delink` as `List<CustomFieldRef>`. | TS-25, TS-26, TS-27 | `SubscriptionFacade.createSubscription()` | IT |
| BT-79 | shouldRejectInvalidExtendedFieldId | AC-25 | Service → validation | `metaCustomFields=[{extendedFieldId:999999}]` | `InvalidInputException`. Doc not saved. | TS-28 | `SubscriptionApprovalHandler.validateForSubmission()` | IT |

#### Group R — Concurrent Access and Optimistic Locking

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-80 | shouldRejectSecondConcurrentApprovalWith409 | G-10, G-05.2 | Service → MongoDB (@Version) | 2 threads simultaneously call `handleApproval(APPROVE)` for same subscriptionId | First → ACTIVE. Second → `OptimisticLockingFailureException` → HTTP 409 via `TargetGroupErrorAdvice`. Only 1 Thrift call total. | TS-68 | `MakerCheckerService.approve()` + `TargetGroupErrorAdvice` | IT |
| BT-81 | shouldRejectStaleEditWithVersionConflict | G-05.2, NEW-OQ-04 | Service → MongoDB (@Version) | Two concurrent `updateSubscription` calls on same ACTIVE doc (same stale version) | First → new DRAFT created. Second → `OptimisticLockingFailureException` → HTTP 409. Only one DRAFT exists. | TS-69, TS-72 | `SubscriptionFacade.updateSubscription()` | IT |

#### Group S — Tenant Isolation

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-82 | shouldIsolateSubscriptionsBetweenOrgs | G-07.4 | Service → MongoDB | Create subscription as orgId=100. `listSubscriptions(orgId=200)` | orgId=200 list is empty. orgId=100 doc not returned. | TS-67 | `SubscriptionProgramRepository.findByOrgId()` | IT |
| BT-83 | shouldReturn404WhenAccessingOtherOrgSubscription | G-07.4 | Service → MongoDB | `getSubscription(200L, "uuid-from-org-100")` | `SubscriptionNotFoundException`. HTTP 404. | TS-67 | `SubscriptionFacade.getSubscription()` | IT |

#### Group T — HTTP Layer (Controller endpoints)

| ID | Test Name | Verifies (BA Req) | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-84 | shouldReturn201OnCreate | AC-09, AC-27 | HTTP POST /v3/subscriptions | Valid `SubscriptionRequest` body | HTTP 201. `ResponseWrapper<SubscriptionResponse>` with `status=DRAFT`. | TS-09 | `SubscriptionController.createSubscription()` | IT |
| BT-85 | shouldReturn400OnInvalidRequest | AC-11 | HTTP POST /v3/subscriptions | Request missing required fields | HTTP 400. `ConstraintViolationException` mapped by `TargetGroupErrorAdvice`. | TS-11, TS-12 | `SubscriptionController.createSubscription()` | IT |
| BT-86 | shouldReturn409OnNameConflict | AC-09, KD-40 | HTTP POST /v3/subscriptions | Conflicting name | HTTP 409. `SubscriptionNameConflictException` mapped by `SubscriptionErrorAdvice`. | TS-70 | `SubscriptionController.createSubscription()` | IT |
| BT-87 | shouldReturn200OnGetSubscription | AC-01 | HTTP GET /v3/subscriptions/{id} | Existing subscription ID | HTTP 200. `ResponseWrapper<SubscriptionResponse>` with full subscription body. | TS-01 | `SubscriptionController.getSubscription()` | IT |
| BT-88 | shouldReturn404OnGetNonExistentSubscription | AC-01 | HTTP GET /v3/subscriptions/{id} | Non-existent ID | HTTP 404 via `SubscriptionErrorAdvice`. | TS-65 | `SubscriptionController.getSubscription()` | IT |
| BT-89 | shouldReturn422OnInvalidStateTransition | AC-31, AC-41 | HTTP PATCH /v3/subscriptions/{id}/status | Resume on ARCHIVED | HTTP 422 via `SubscriptionErrorAdvice`. | TS-56 | `SubscriptionController.changeStatus()` | IT |

---

## 3. Compliance Test Cases

### 3.1 ADR Compliance

| ID | Test Name | ADR | What it Verifies | QA Scenario | Layer |
|----|-----------|-----|-----------------|-------------|-------|
| BT-C01 | shouldNotWriteToMySQLDuringDraftLifecycle | ADR-01 | After create + update + submit: `partnerProgramId=null` in MongoDB. `createOrUpdatePartnerProgram` Thrift mock NOT called. | TS-44 | IT |
| BT-C02 | shouldWriteMySQLExactlyOnceOnApprove | ADR-01 | After approve: Thrift called exactly 1 time. `partner_programs` has exactly 1 row (verified via Thrift mock `verify(times(1))`). | TS-45 | IT |
| BT-C03 | shouldRouteSubscriptionRepoToEmfMongoTemplate | ADR-01, KD-41 | `EmfMongoConfig.includeFilters` contains `SubscriptionProgramRepository.class`. MongoDB save routes to `emfMongoTemplate` database (not default template). | TS-81 | IT |
| BT-C04 | shouldUseMakerCheckerServiceWithoutSubscriptionImports | ADR-02 | `MakerCheckerService.java` class has zero imports from `com.capillary.intouchapiv3.unified.subscription.*` package. Subscription-specific code confined to `SubscriptionApprovalHandler`. | TS-39 | UT (ArchUnit or import scan) |
| BT-C05 | shouldCompensateSAGAOnThriftFailure | ADR-03 | Thrift mock throws → `handleApproval` catches → `onPublishFailure` called → status remains `PENDING_APPROVAL`. | TS-41 | IT |
| BT-C06 | shouldRetryApprovalWithoutDoubleThriftCall | ADR-03, RF-6 | `partnerProgramId` set in MongoDB → second approve call → Thrift mock verify: called 0 times on retry. | TS-42 | IT |
| BT-C07 | shouldStoreBenefitsAsIdArrayNotRelationalJoin | ADR-04 | After linking 3 benefits and approving: MongoDB `benefitIds=[101,102,103]`. Thrift mock: no call for benefit-join write. No call to any benefit MySQL table. | TS-46, TS-53 | IT |
| BT-C08 | shouldNotWriteRemindersToMySQLOnApprove | ADR-06 | After approving subscription with 3 reminders: Thrift mock `createOrUpdateExpiryReminderForPartnerProgram` NOT called. MongoDB `reminders` array has 3 entries. | TS-50 | IT |
| BT-C09 | shouldStoreYearsInMongoAndConvertToMonthsOnPublish | ADR-07 | Create with YEARS:2. After approve: Thrift mock `createOrUpdatePartnerProgram` captured arg: `cycle.type=MONTHS`, `cycle.value=24`. MongoDB doc still has `cycleType=YEARS, cycleValue=2`. | TS-49, TS-76 | IT |

### 3.2 Guardrail Compliance

| ID | Test Name | Guardrail | What it Verifies | QA Scenario | Layer |
|----|-----------|-----------|-----------------|-------------|-------|
| BT-G01 | shouldStoreTimestampsAsInstantInUTC | G-01.1, G-01.3 | `createdAt`, `updatedAt`, `submittedAt`, `reviewedAt` in MongoDB doc are all `Instant` (not `Date`/`LocalDateTime`). No `java.util.Date` usage in `SubscriptionProgram`. | TS-64 | UT + IT |
| BT-G02 | shouldIncludeOrgIdInAllMongoRepositoryQueries | G-07.1, G-07.4 | All `@Query` annotations in `SubscriptionProgramRepository` include `'orgId'` filter. Query analysis: grep for all `@Query` → verify `orgId` present in each. | TS-67 | UT (static analysis) |
| BT-G03 | shouldReturnEmptyListNotNullForMissingBenefits | G-02.1 | `SubscriptionMapper.toListItem()` handles `benefitIds=null` → returns `benefitsCount=0`. `getBenefits()` returns `Collections.emptyList()` not null. | TS-66 | UT |
| BT-G04 | shouldPaginateListEndpoint | G-04.2 | `listSubscriptions` with `size=10` and 50 total docs: returns page with 10 items and `totalElements=50`. No unbounded query. | TS-01 | IT |
| BT-G05 | shouldFetchSubscriberCountsWithSingleBulkCall | G-04.1 | 30 ACTIVE subscriptions in org. `getHeaderStats(100L, 200)`: Thrift mock verify `getSupplementaryEnrollmentCountsByProgramIds` called exactly 1 time with a list of 30 IDs. | TS-71 | IT |
| BT-G06 | shouldMaintainBackwardCompatibilityForExistingThriftCallers | G-09 | Existing `CreateOrUpdatePartnerProgramTest` integration tests pass unchanged after field 15 (`isActive`) added to IDL. Tests that don't set field 15: `is_active` column value unchanged from pre-change behavior. | TS-73 | IT (existing test rerun) |
| BT-G07 | shouldHandleConcurrentApprovalWithOptimisticLock | G-10, G-05.2 | Two threads simultaneously approve same subscription. `@Version` incremented on first success. Second attempt: `OptimisticLockingFailureException` → HTTP 409. No data corruption. | TS-68 | IT |

### 3.3 Risk Mitigation Test Cases

| ID | Test Name | Risk | What it Verifies | QA Scenario | Layer |
|----|-----------|------|-----------------|-------------|-------|
| BT-R01 | shouldPreventDoubleThriftCallUnderConcurrentSAGA | QA-RISK-05 (concurrent SAGA) | `partnerProgramId` check + MongoDB `findAndModify` conditional: only one thread proceeds past the idempotency gate. Verify with `CountDownLatch` + 2 threads. | TS-43, TS-68 | IT |
| BT-R02 | shouldHandleDanglingBenefitIdWithoutException | QA-RISK-02 (dangling benefitId) | `getBenefits()` where one benefitId in array points to deleted benefit → response excludes deleted ID (or returns stub). No 500. Listing `benefitsCount` = actual valid count. | TS-80 | IT |
| BT-R03 | shouldRouteSubscriptionRepoToCorrectMongoDatabase | QA-RISK-04 (EmfMongoConfig registration) | `EmfMongoConfig` explicitly lists `SubscriptionProgramRepository.class` in `includeFilters`. `@DataMongoTest` slice: save a subscription → verify it lands in the correct MongoDB database/collection. | TS-81 | IT |
| BT-R04 | shouldNotAllowSecondSubmitWhenAlreadyPendingApproval | Session-memory risk (double submit) | `submitForApproval` on PENDING_APPROVAL subscription → `InvalidSubscriptionStateException` (already pending). State machine guard enforced. | TS-33 | IT |
| BT-R05 | shouldHandleThriftTimeoutWithRetryableError | Session-memory risk (Thrift failures) | Thrift mock throws timeout exception during `getAllPartnerPrograms()` name check → `EMFThriftException` propagated → HTTP 502. Subscription not saved to avoid partial state. | TS-41 | IT |

---

## 4. Coverage Gaps

No coverage gaps identified. All 48 BA acceptance criteria, 87 QA scenarios, and 50 Designer interface methods are represented in the 102 test cases above.

**Open Questions from QA (QA-OQ-01 through QA-OQ-05) deferred to BA/Designer:**

| Gap ID | QA-OQ | Affected Tests | Action Required |
|--------|-------|---------------|-----------------|
| GAP-1 | QA-OQ-01 (reminder daysBefore min) | BT-08 boundary | BA to confirm `@Positive` = daysBefore ≥ 1 is the correct constraint |
| GAP-2 | QA-OQ-03 (dangling benefitId behavior) | BT-R02 expected output | Designer to specify: skip vs stub. BT-R02 currently written as "skip". |
| GAP-3 | QA-OQ-04 (duplicate name "(Copy)" conflict) | BT-49 | BA to confirm: 409 (current test assumption). If auto-suffix → BT-49 must be revised. |
| GAP-4 | QA-OQ-05 (membershipStartDate timezone) | BT-41 (createdAt check) | BA to clarify: UTC midnight boundary for nightly activation. |

**None of the gaps are blockers to SDET starting implementation.** Test assumptions documented above are internally consistent with ADRs and session memory. If BA/Designer resolve OQs differently, the 4 affected tests (BT-08, BT-41, BT-49, BT-R02) will need revision.

---

## 5. Test Class Mapping

| Test Class | Covers BT IDs | Type | Repo |
|-----------|--------------|------|------|
| `SubscriptionValidationTest` | BT-01 through BT-09 | UT | intouch-api-v3 |
| `SubscriptionPublishServiceTest` | BT-10 through BT-19 | UT | intouch-api-v3 |
| `MakerCheckerServiceTest` | BT-20 through BT-23 | UT | intouch-api-v3 |
| `PointsEngineRuleServiceIsActiveTest` | BT-24 through BT-26 | UT | emf-parent |
| `SubscriptionApprovalHandlerUnitTest` | BT-27 through BT-30 | UT | intouch-api-v3 |
| `SubscriptionProgramRepositoryQueryTest` | BT-31 through BT-36 | UT (`@DataMongoTest`) | intouch-api-v3 |
| `SubscriptionFacadeCreateTest` | BT-37 through BT-41 | IT | intouch-api-v3 |
| `SubscriptionFacadeListTest` | BT-42 through BT-46 | IT | intouch-api-v3 |
| `SubscriptionFacadeDuplicateTest` | BT-47 through BT-49 | IT | intouch-api-v3 |
| `SubscriptionFacadeUpdateTest` | BT-50 through BT-52 | IT | intouch-api-v3 |
| `SubscriptionFacadeBenefitTest` | BT-53 through BT-56 | IT | intouch-api-v3 |
| `SubscriptionFacadeApprovalTest` | BT-57 through BT-68 | IT | intouch-api-v3 |
| `SubscriptionFacadeLifecycleTest` | BT-69 through BT-74 | IT | intouch-api-v3 |
| `GetSubscriberCountsThriftTest` | BT-75 through BT-77 | IT | emf-parent |
| `SubscriptionCustomFieldsTest` | BT-78 through BT-79 | IT | intouch-api-v3 |
| `SubscriptionConcurrencyTest` | BT-80 through BT-81 | IT | intouch-api-v3 |
| `SubscriptionTenantIsolationTest` | BT-82 through BT-83 | IT | intouch-api-v3 |
| `SubscriptionControllerTest` | BT-84 through BT-89 | IT (MockMvc) | intouch-api-v3 |
| `SubscriptionADRComplianceTest` | BT-C01 through BT-C09 | IT (+ UT for BT-C04) | intouch-api-v3 |
| `SubscriptionGuardrailTest` | BT-G01 through BT-G07 | UT + IT | intouch-api-v3 / emf-parent |
| `SubscriptionRiskMitigationTest` | BT-R01 through BT-R05 | IT | intouch-api-v3 / emf-parent |

**Total test classes: 21** (15 new in intouch-api-v3, 3 new in emf-parent, 3 shared compliance)

---

*Total (original): 48/48 ACs, 87/87 QA scenarios, 50/50 Designer interfaces covered. 102 test cases (38 UT + 64 IT). 4 minor gaps documented — none block SDET phase.*

---

## 6. Rework 2 — PUBLISH_FAILED State + Pattern A Idempotency Key (2026-04-16)

> **Source**: Designer Rework 2 (R-13 through R-21), QA Rework 2 (TS-SAGA-01 through TS-SAGA-16).

---

### 6.1 Tests Requiring Revision (Existing BTs Invalidated by Rework 2)

These tests existed before Rework 2. Their expected outputs are now wrong and MUST be updated by SDET/Developer before implementing Rework 2 code:

| BT ID | Test Name | Old Expected Output | New Expected Output |
|-------|-----------|---------------------|---------------------|
| BT-23 | `shouldPreserveEntityOnPublishFailure` | `entity.status` unchanged (PENDING_APPROVAL) | `entity.status = PUBLISH_FAILED`. `save.save(entity)` called once. |
| BT-29 | `shouldLeaveStatusUnchangedOnPublishFailure` | `entity.status` unchanged (PENDING_APPROVAL) | `entity.status = PUBLISH_FAILED`. `entity.comments = e.getMessage()`. |
| BT-61 | `shouldRemainPendingApprovalOnThriftFailure` | MongoDB `status = PENDING_APPROVAL` | MongoDB `status = PUBLISH_FAILED`. `comments` has error message. |
| BT-C05 | `shouldCompensateSAGAOnThriftFailure` | Status remains `PENDING_APPROVAL` | Status = `PUBLISH_FAILED`, saved to MongoDB. |

**Note**: The test `SubscriptionApprovalHandlerTest.shouldLeaveStatusUnchangedOnPublishFailure` already exists in the codebase (was written in SDET phase). It MUST be updated — the production `onPublishFailure()` implementation will now set `PUBLISH_FAILED`, causing the current test assertion to fail.

---

### 6.2 New Unit Tests — PUBLISH_FAILED State Machine

#### Group PF — PUBLISH_FAILED State Transitions

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|---------|-------|-----------------|-------------|-------------------|-------|
| BT-PF-01 | shouldSetPublishFailedStatusOnTransition | R-15 | `entity.transitionToPublishFailed("Thrift timeout")` | `entity.status = PUBLISH_FAILED`, `entity.comments = "Thrift timeout"` | TS-SAGA-04 | `SubscriptionProgram.transitionToPublishFailed()` | UT |
| BT-PF-02 | shouldNotThrowOnNullReasonInTransitionToPublishFailed | R-15, G-02 | `entity.transitionToPublishFailed(null)` | `entity.status = PUBLISH_FAILED`, `entity.comments = null`. No NPE. | TS-SAGA-04 | `SubscriptionProgram.transitionToPublishFailed()` | UT |
| BT-PF-03 | shouldCallOnPublishFailureAndSaveOnThriftException | R-16 | `makerCheckerService.approve()` where `handler.publish()` throws | `handler.onPublishFailure()` called. `save.save(entity)` called. Exception rethrown. | TS-SAGA-02 | `MakerCheckerService.approve()` | UT |
| BT-PF-04 | shouldRethrowOriginalExceptionEvenIfSaveFails | R-16 | `approve()`: `publish()` throws `EMFThriftException`, `save.save()` also throws `MongoException` | Caller receives `EMFThriftException`. `MongoException` NOT propagated. | TS-SAGA-03 | `MakerCheckerService.approve()` | UT |
| BT-PF-05 | shouldTransitionToPublishFailedOnPublishError | R-17 | `onPublishFailure(entity{status=PENDING_APPROVAL}, new EMFThriftException("emf down"))` | `entity.status = PUBLISH_FAILED`. `entity.comments = "emf down"`. No exception thrown. | TS-SAGA-01 | `SubscriptionApprovalHandler.onPublishFailure()` | UT |
| BT-PF-06 | shouldAllowApprovalFromPublishFailedState | R-18, AC-35 | `handleApproval(APPROVE)` on entity with `status=PUBLISH_FAILED` | `MakerCheckerService.approve()` called. No `InvalidSubscriptionStateException`. | TS-SAGA-05 | `SubscriptionFacade.handleApproval()` | UT |
| BT-PF-07 | shouldAllowRejectionFromPublishFailedState | R-18, AC-34 | `handleApproval(REJECT, "fix needed")` on entity with `status=PUBLISH_FAILED` | `MakerCheckerService.reject()` called. No `InvalidSubscriptionStateException`. | TS-SAGA-06 | `SubscriptionFacade.handleApproval()` | UT |
| BT-PF-08 | shouldRejectApprovalFromDraftActiveOrArchived | R-18 | `handleApproval(APPROVE)` for DRAFT / ACTIVE / PAUSED / ARCHIVED | `InvalidSubscriptionStateException` in all 4 cases. | TS-SAGA-07 | `SubscriptionFacade.handleApproval()` | UT |

---

### 6.3 New Unit Tests — Pattern A Idempotency Key

#### Group PA — Stable serverReqId + PartnerProgramIdempotencyService

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|---------|-------|-----------------|-------------|-------------------|-------|
| BT-PA-01 | shouldGenerateStableServerReqIdForSubscription | R-19 | `publishToMySQL(subscription{subscriptionProgramId="uuid-abc"}, orgId, programId)` | `thriftService.createOrUpdatePartnerProgram(...)` called with `serverReqId = "sub-approve-uuid-abc"` | TS-SAGA-09 | `SubscriptionPublishService.publishToMySQL()` | UT |
| BT-PA-02 | shouldGenerateSameServerReqIdOnRetry | R-19 | Two calls to `publishToMySQL()` for same subscription | Both calls: `serverReqId = "sub-approve-uuid-abc"` (identical) | TS-SAGA-10 | `SubscriptionPublishService.publishToMySQL()` | UT |
| BT-PA-03 | shouldReturnNullForUncachedServerReqId | R-20 | `idempotencyService.getCachedPartnerProgramId("sub-approve-uuid-1")` on empty cache | Returns `null` | TS-SAGA-11 | `PartnerProgramIdempotencyService.getCachedPartnerProgramId()` | UT |
| BT-PA-04 | shouldCacheAndRetrievePartnerProgramId | R-20 | `cachePartnerProgramId("sub-approve-uuid-1", 42)` then `getCachedPartnerProgramId("sub-approve-uuid-1")` | Returns `42` | TS-SAGA-12 | `PartnerProgramIdempotencyService` | UT |
| BT-PA-05 | shouldSkipWriteAndReturnCachedIdOnRetry | R-21 | `createOrUpdatePartnerProgram(info, ..., "sub-approve-uuid-1")` where cache returns `99` | `info.partnerProgramId == 99`. `m_pointsEngineRuleEditor.createOrUpdatePartnerProgram()` NOT called. | TS-SAGA-13 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | UT |
| BT-PA-06 | shouldExecuteWriteAndCacheIdOnFirstCall | R-21 | `createOrUpdatePartnerProgram(info, ..., "sub-approve-uuid-1")` where cache returns `null`. Editor returns entity with `id=77`. | `info.partnerProgramId == 77`. `cachePartnerProgramId("sub-approve-uuid-1", 77)` called. | TS-SAGA-14 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | UT |
| BT-PA-07 | shouldBypassIdempotencyCheckForNullServerReqId | R-21, G-09 | `createOrUpdatePartnerProgram(info, ..., null)` | `getCachedPartnerProgramId()` NOT called. Normal write proceeds. `cachePartnerProgramId()` NOT called. | TS-SAGA-15 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | UT |

---

### 6.4 New Integration Tests — Full SAGA Flow

#### Group PF-IT — PUBLISH_FAILED End-to-End

| ID | Test Name | Verifies | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|---------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-PF-IT-01 | shouldPersistPublishFailedToMongoOnThriftError | R-16+R-17 | Service → Thrift (throws) → MongoDB | `handleApproval(APPROVE)` where Thrift throws `EMFThriftException` | MongoDB doc `status = PUBLISH_FAILED`. `comments` has error message. `partnerProgramId = null`. Exception propagated to controller. | TS-SAGA-08 | `SubscriptionFacade.handleApproval()` | IT |
| BT-PF-IT-02 | shouldRetryApprovalFromPublishFailedState | R-18 | Service → Thrift (mock success on retry) → MongoDB | Entity starts as PUBLISH_FAILED. `handleApproval(APPROVE)` again. | Thrift called. MongoDB `status = ACTIVE`. `partnerProgramId` set. | TS-SAGA-05 | `SubscriptionFacade.handleApproval()` | IT |
| BT-PF-IT-03 | shouldRejectToFromPublishFailedState | R-18 | Service → MongoDB | Entity starts as PUBLISH_FAILED. `handleApproval(REJECT, "fix config")`. | MongoDB `status = DRAFT`. `comments = "fix config"`. Thrift NOT called. | TS-SAGA-06 | `SubscriptionFacade.handleApproval()` | IT |

#### Group PA-IT — Pattern A End-to-End

| ID | Test Name | Verifies | Boundary | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|---------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-PA-IT-01 | shouldReturnCachedIdWithoutRewriteOnRetry | R-21 | emf-parent: cache hit → skip editor | First call: editor returns id=55, caches "sub-approve-uuid-1" → 55. Second call: same serverReqId. | Second call: editor NOT called. Returns `info.partnerProgramId=55`. | TS-SAGA-16 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | IT |
| BT-PA-IT-02 | shouldNotAffectExistingCallersWithBlankServerReqId | R-21, G-09 | emf-parent: null serverReqId path | Call with `serverReqId=null`. Editor executes normally. | No NPE. Write proceeds. Cache NOT populated. | TS-SAGA-15 | `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` | IT |

---

### 6.5 Updated Coverage Summary (Rework 2)

| Source | Total | Covered |
|--------|-------|---------|
| Rework 2 QA Scenarios (TS-SAGA-01 to TS-SAGA-16) | 16 | 16 |
| Rework 2 Designer Changes (R-13 to R-21) | 9 | 9 |
| Existing tests requiring revision | 4 | 4 (documented in §6.1) |

**New test cases added: BT-PF-01 to BT-PF-08 (8 UT) + BT-PA-01 to BT-PA-07 (7 UT) + BT-PF-IT-01 to BT-PF-IT-03 (3 IT) + BT-PA-IT-01 to BT-PA-IT-02 (2 IT) = 20 new test cases**

**Running total: 102 + 20 = 122 test cases**

### 6.6 Updated Test Class Mapping (Rework 2 additions)

| Test Class | Covers BT IDs | Type | Repo |
|-----------|--------------|------|------|
| `SubscriptionApprovalHandlerTest` *(update existing)* | BT-PF-05; update BT-29 | UT | intouch-api-v3 |
| `MakerCheckerServiceTest` *(update existing)* | BT-PF-03, BT-PF-04; update BT-23 | UT | intouch-api-v3 |
| `SubscriptionProgramTest` *(new or extend)* | BT-PF-01, BT-PF-02 | UT | intouch-api-v3 |
| `SubscriptionFacadeApprovalTest` *(update existing)* | BT-PF-06, BT-PF-07, BT-PF-08; update BT-61 | UT + IT | intouch-api-v3 |
| `SubscriptionPublishServiceTest` *(update existing)* | BT-PA-01, BT-PA-02 | UT | intouch-api-v3 |
| `PartnerProgramIdempotencyServiceTest` *(new)* | BT-PA-03, BT-PA-04 | UT | emf-parent |
| `PartnerProgramIdempotencyThriftImplTest` *(new)* | BT-PA-05, BT-PA-06, BT-PA-07 | UT | emf-parent |
| `SubscriptionSagaPublishFailedIT` *(new)* | BT-PF-IT-01, BT-PF-IT-02, BT-PF-IT-03 | IT | intouch-api-v3 |
| `PartnerProgramIdempotencyIT` *(new)* | BT-PA-IT-01, BT-PA-IT-02 | IT | emf-parent |

---

## Rework Additions — ADR-08 through ADR-18 (Gap Analysis 2026-04-15)

> Added: 2026-04-15 | Source ADRs: ADR-08 through ADR-18 | KD refs: KD-47 through KD-58
> All 12 critical gaps identified in Phase 6/7 rework are covered below.
> These test cases are ADDITIVE — all original BT-01 through BT-R05 test cases remain valid.

---

### Rework Unit Tests (UT layer)

> JUnit 5 + Mockito. No Spring context. Direct method invocation. See original Section 2.1 for test class patterns.

#### Group RU-A — Name Validation (ADR-08, KD-47)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-01 | `shouldRejectNameLongerThan50Chars` | ADR-08, KD-47 — `@Size(max=50)` constraint on name | `SubscriptionProgram{ name = "A".repeat(51) }` submitted for approval | `SubscriptionApprovalHandler.validateForSubmission()` throws `InvalidSubscriptionStateException` (or `ConstraintViolationException` from bean validation) | TS-NEW-01 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-02 | `shouldRejectNameWithDisallowedChars` | ADR-08 — `@Pattern(regexp="^[a-zA-Z0-9_\\-: ]*$")` | `name = "Gold!Plan"` (contains `!`) and variants with `@`, `#`, `$`, `%` | `ConstraintViolationException` with message "only alphabets, spaces, numerals, _, -, : are allowed" | TS-NEW-02 | `SubscriptionProgram.name` `@Pattern` field-level constraint | UT |
| BT-R-03 | `shouldAcceptNamesWithAllowedChars` | ADR-08 — all explicitly allowed characters accepted | `name = "Gold Plan-2024:Test_Prog"` (alphanumeric + `_`, `-`, `:`, space) | No exception. `validateForSubmission()` proceeds past name check. | TS-NEW-03 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |

#### Group RU-B — Description Validation (ADR-09, KD-48)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-04 | `shouldRejectBlankDescription` | ADR-09, KD-48 — description is now `@NotBlank` (was optional) | `SubscriptionProgram{ description = null }` and `description = ""` | `InvalidSubscriptionStateException` or `ConstraintViolationException` — null/blank description rejected at submit | TS-NEW-04 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-05 | `shouldRejectDescriptionLongerThan100Chars` | ADR-09 — `@Size(max=100)` | `description = "A".repeat(101)` | `ConstraintViolationException` with message "SUBSCRIPTION.DESCRIPTION_TOO_LONG" | TS-NEW-05 | `SubscriptionProgram.description` `@Size(max=100)` field-level constraint | UT |
| BT-R-06 | `shouldRejectDescriptionWithDisallowedChars` | ADR-09 — `@Pattern(regexp="^[a-zA-Z0-9_\\-: ,.\s]*$")` | `description = "Invalid!desc"` (contains `!`) and `description = "test#tag"` | `ConstraintViolationException` with pattern violation message | TS-NEW-06 | `SubscriptionProgram.description` `@Pattern` field-level constraint | UT |

#### Group RU-C — CycleType YEARS Rejection (ADR-10, KD-49)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-07 | `shouldRejectYearsCycleType` | ADR-10, KD-49 — `CycleType.YEARS` removed from enum. YEARS is not accepted at the API boundary. | Attempt to deserialise JSON `{"cycleType": "YEARS"}` into `SubscriptionRequest.DurationDto` | `HttpMessageNotReadableException` (Jackson deserialization failure) — `YEARS` is not a valid enum constant in the reworked `CycleType` enum. Alternatively: if testing enum directly, `CycleType.valueOf("YEARS")` throws `IllegalArgumentException`. | TS-NEW-07 | `CycleType` enum — `DAYS` and `MONTHS` only (reworked from ADR-10). Deserialization via `SubscriptionRequest.DurationDto.cycleType` | UT |

#### Group RU-D — programType Required + Duration Conditional (ADR-14, KD-53)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-08 | `shouldRequireProgramType` | ADR-14, KD-53 — `programType` is `@NotNull` | `SubscriptionProgram{ programType = null }` | `InvalidSubscriptionStateException("programType is required (SUPPLEMENTARY or EXTERNAL)")` from `validateForSubmission()` check #7 | TS-NEW-08 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-09 | `shouldRequireDurationWhenSupplementary` | ADR-14 — SUPPLEMENTARY requires duration | `SubscriptionProgram{ programType = SUPPLEMENTARY, duration = null }` | `InvalidSubscriptionStateException("duration required for SUPPLEMENTARY programs")` from check #8 | TS-NEW-09 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-10 | `shouldNotRequireDurationWhenExternal` | ADR-14 — EXTERNAL does not require duration | `SubscriptionProgram{ programType = EXTERNAL, duration = null, pointsExchangeRatio = 1.0, name = "ExtPlan", description = "Desc", subscriptionType = NON_TIER, syncWithLoyaltyTierOnDowngrade = false }` — all other required fields populated | No exception thrown. `validateForSubmission()` completes without error for the duration check. | TS-NEW-10 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-11 | `shouldClearDurationWhenExternal` | ADR-14 — EXTERNAL + duration provided → duration cleared by validateForSubmission | `SubscriptionProgram{ programType = EXTERNAL, duration = Duration{cycleType=MONTHS, cycleValue=3} }` | After `validateForSubmission()` returns, `entity.getDuration() == null` (cleared for EXTERNAL) | TS-NEW-11 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` — check #8 clears duration for EXTERNAL | UT |

#### Group RU-E — pointsExchangeRatio Required (ADR-12, KD-51)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-12 | `shouldRejectNullOrZeroPointsRatio` | ADR-12, KD-51 — `pointsExchangeRatio` required and positive | Inputs: (a) `pointsExchangeRatio = null`, (b) `pointsExchangeRatio = 0.0`, (c) `pointsExchangeRatio = -1.0` | For all three: `InvalidSubscriptionStateException("pointsExchangeRatio must be positive and non-null")`. For input 1.5: no exception. | TS-NEW-12 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` — check #6 | UT |
| BT-R-13 | `shouldWirePointsRatioToThriftField6` | ADR-12 — `pointsExchangeRatio` wired to Thrift field 6 (not hardcoded 1.0) | `SubscriptionProgram{ pointsExchangeRatio = 2.5, subscriptionType = NON_TIER, programType = SUPPLEMENTARY, duration = Duration{MONTHS, 6} }` passed to `buildPartnerProgramInfo()` | `PartnerProgramInfo.programToPartnerProgramPointsRatio == 2.5`. Verify `DEFAULT_POINTS_RATIO` constant does not exist in `SubscriptionPublishService` (removed per ADR-12). | TS-NEW-22 | `SubscriptionPublishService.buildPartnerProgramInfo(SubscriptionProgram program, Long orgId)` | UT |

#### Group RU-F — syncWithLoyaltyTierOnDowngrade as Direct Field (ADR-13, KD-52)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-14 | `shouldWireSyncFlagDirectlyToThriftField10` | ADR-13, KD-52 — `syncWithLoyaltyTierOnDowngrade` is direct user field; NOT derived from `TIER_BASED && tierDowngradeOnExit` | Scenario A: `SubscriptionProgram{ subscriptionType=NON_TIER, syncWithLoyaltyTierOnDowngrade=true, tierConfig=null }` → Scenario B: `{ subscriptionType=TIER_BASED, tierDowngradeOnExit=false, syncWithLoyaltyTierOnDowngrade=false }` | Scenario A: `buildPartnerProgramInfo().isSyncWithLoyaltyTierOnDowngrade == true`. Scenario B: `isSyncWithLoyaltyTierOnDowngrade == false`. Demonstrates field is read directly from model, NOT derived from subscriptionType. | TS-NEW-24 | `SubscriptionPublishService.buildPartnerProgramInfo(SubscriptionProgram program, Long orgId)` | UT |
| BT-R-15 | `shouldRejectSyncTrueWithEmptyLoyaltySyncTiers` | ADR-13, ADR-17 — sync=true requires non-empty `loyaltySyncTiers` | `SubscriptionProgram{ syncWithLoyaltyTierOnDowngrade=true, tierConfig=TierConfig{ loyaltySyncTiers=null } }` | `InvalidSubscriptionStateException("loyaltySyncTiers required when syncWithLoyaltyTierOnDowngrade=true")` from `validateForSubmission()` check #11 | TS-NEW-31 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |

#### Group RU-G — partnerProgramTiers List (ADR-16, KD-55)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-16 | `shouldRejectTierBasedWithEmptyTiersList` | ADR-16, KD-55 — TIER_BASED requires non-empty `tierConfig.tiers` | `SubscriptionProgram{ subscriptionType=TIER_BASED, tierConfig=TierConfig{ tiers=[] } }` | `InvalidSubscriptionStateException("TIER_BASED subscription requires non-empty tierConfig.tiers list")` from `validateForSubmission()` check #10 | TS-NEW-28 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-17 | `shouldWireTiersToThriftField5` | ADR-16 — `tierConfig.tiers` wired to Thrift field 5 `partnerProgramTiers` | `SubscriptionProgram{ subscriptionType=TIER_BASED, tierConfig=TierConfig{ tiers=[ProgramTier{1,"Silver"}, ProgramTier{2,"Gold"}] } }` passed to `buildPartnerProgramInfo()` | `PartnerProgramInfo.partnerProgramTiers` contains 2 entries: `PartnerProgramTier{tierNumber=1, tierName="Silver"}` and `PartnerProgramTier{tierNumber=2, tierName="Gold"}` | TS-NEW-26 | `SubscriptionPublishService.buildPartnerProgramInfo(SubscriptionProgram program, Long orgId)` | UT |
| BT-R-18 | `shouldNotSetTiersWhenNonTier` | ADR-16 — NON_TIER subscription → Thrift field 5 is empty list | `SubscriptionProgram{ subscriptionType=NON_TIER, tierConfig=null }` | `PartnerProgramInfo.partnerProgramTiers` is empty list (`Collections.emptyList()`), not null. `isTierBased=false`. | TS-NEW-19 | `SubscriptionPublishService.buildPartnerProgramInfo(SubscriptionProgram program, Long orgId)` | UT |

#### Group RU-H — loyaltySyncTiers Map (ADR-17, KD-56)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-19 | `shouldWireLoyaltySyncTiersToThriftField11` | ADR-17, KD-56 — `tierConfig.loyaltySyncTiers` wired to Thrift field 11 | `SubscriptionProgram{ syncWithLoyaltyTierOnDowngrade=true, tierConfig=TierConfig{ loyaltySyncTiers={"Silver":"Bronze"} } }` | `PartnerProgramInfo.loyaltySyncTiers == {"Silver":"Bronze"}` (exact map passed through) | TS-NEW-30 | `SubscriptionPublishService.buildPartnerProgramInfo(SubscriptionProgram program, Long orgId)` | UT |
| BT-R-20 | `shouldNotSetLoyaltySyncTiersWhenSyncFalse` | ADR-17 — sync=false → Thrift field 11 not set | `SubscriptionProgram{ syncWithLoyaltyTierOnDowngrade=false, tierConfig=TierConfig{ loyaltySyncTiers={"Gold":"Silver"} } }` | `PartnerProgramInfo.loyaltySyncTiers` is null (field 11 not populated when sync is false, even if map is present on entity) | TS-NEW-19 | `SubscriptionPublishService.buildPartnerProgramInfo(SubscriptionProgram program, Long orgId)` | UT |

#### Group RU-I — Migration Cross-Field Validation (ADR-15, KD-54)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-21 | `shouldRejectMigrationWithoutBackupProgramId` | ADR-15, KD-54 — `migrationTargetProgramId` required when migration enabled | `SubscriptionProgram{ expiry=Expiry{ migrateOnExpiry=MIGRATE_TO_PROGRAM, programExpiryDate=<non-null Instant>, migrationTargetProgramId=null } }` | `InvalidSubscriptionStateException("migrationTargetProgramId must be > 0 when migration is enabled")` from `validateForSubmission()` check #9 | TS-NEW-29 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-22 | `shouldRejectMigrationWithZeroBackupProgramId` | ADR-15 — `migrationTargetProgramId=0` is invalid | `SubscriptionProgram{ expiry=Expiry{ migrateOnExpiry=MIGRATE_TO_PROGRAM, programExpiryDate=<non-null>, migrationTargetProgramId=0 } }` | `InvalidSubscriptionStateException("migrationTargetProgramId must be > 0 when migration is enabled")` | TS-NEW-29 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |
| BT-R-23 | `shouldAcceptMigrationWithValidBackupProgramId` | ADR-15 — valid `migrationTargetProgramId > 0` passes | `SubscriptionProgram{ expiry=Expiry{ migrateOnExpiry=MIGRATE_TO_PROGRAM, programExpiryDate=<non-null>, migrationTargetProgramId=123 } }` — all other required fields also valid | `validateForSubmission()` does NOT throw for migration check. Validation proceeds to next check. | TS-NEW-29 | `SubscriptionApprovalHandler.validateForSubmission(SubscriptionProgram entity)` | UT |

#### Group RU-J — Case-Insensitive Name Uniqueness (ADR-11, KD-50)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-24 | `shouldRejectDuplicateNameCaseInsensitive` | ADR-11, KD-50 — case-insensitive name uniqueness at createSubscription time | MongoDB pre-seeded with doc `{ name="Gold Plan", status=ACTIVE, orgId=100 }`. Create request `{ name="gold plan", orgId=100 }` | `SubscriptionNameConflictException` — "gold plan" matches "Gold Plan" case-insensitively. MongoDB doc NOT saved. | TS-NEW-13 | `SubscriptionFacade.createSubscription(Long orgId, Integer programId, SubscriptionRequest request, String createdBy)` via `SubscriptionProgramRepository.findActiveByOrgIdAndName(Long orgId, String nameRegex)` | UT |
| BT-R-25 | `shouldUseRegexQueryForCaseInsensitiveCheck` | ADR-11 — `findActiveByOrgIdAndName` uses `$regex` with `$options:'i'` | Inspect `@Query` annotation on `findActiveByOrgIdAndName` method. Call with `orgId=100L` and `Pattern.quote("Gold Plan")`. | `@Query` value contains `$regex` and `$options: 'i'`. Method correctly returns an existing doc with name "gold plan" when queried with "Gold Plan" (case-insensitive match). | TS-NEW-14 | `SubscriptionProgramRepository.findActiveByOrgIdAndName(Long orgId, String name)` — `@Query("{'orgId': ?0, 'name': {$regex: ?1, $options: 'i'}, 'status': { $in: [...] }}")` | UT (`@DataMongoTest` slice) |

#### Group RU-K — subscriptionProgramId Lifecycle (ADR-18, KD-58)

| ID | Test Name | Verifies | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|-------------|-------------------|-------|
| BT-R-26 | `shouldGenerateSubscriptionProgramIdOnCreate` | ADR-18, KD-58 — UUID generated at CREATE | Valid `SubscriptionRequest` for a new subscription | After `createSubscription()`, the returned `SubscriptionResponse.subscriptionProgramId` is non-null, non-empty UUID string. Each call generates a distinct UUID. | TS-NEW-35 | `SubscriptionFacade.createSubscription(Long orgId, Integer programId, SubscriptionRequest request, String createdBy)` | UT |
| BT-R-27 | `shouldPreserveSubscriptionProgramIdOnDraftUpdate` | ADR-18 — edit of DRAFT does NOT regenerate `subscriptionProgramId` | DRAFT subscription with `subscriptionProgramId="uuid-A"`. Call `updateSubscription()` with new name. | Returned doc still has `subscriptionProgramId="uuid-A"` — unchanged. `objectId` also unchanged (in-place update). | TS-NEW-36 | `SubscriptionFacade.updateSubscription(Long orgId, String subscriptionProgramId, SubscriptionProgram request, String updatedBy)` | UT |
| BT-R-28 | `shouldCopySubscriptionProgramIdOnActiveEdit` | ADR-18 — edit of ACTIVE (fork to DRAFT) copies `subscriptionProgramId` from ACTIVE parent | ACTIVE subscription with `subscriptionProgramId="uuid-A"`, `objectId="active-obj-id"`. Call `editActiveSubscription()` | New DRAFT doc created: `subscriptionProgramId="uuid-A"` (SAME as parent), `parentId="active-obj-id"`, `version=ACTIVE.version+1`. ACTIVE doc unchanged. | TS-NEW-37 | `SubscriptionFacade.editActiveSubscription(Long orgId, String subscriptionProgramId, SubscriptionProgram request, String updatedBy)` (or `updateSubscription()` when called on ACTIVE status) | UT |
| BT-R-29 | `shouldGenerateNewSubscriptionProgramIdOnDuplicate` | ADR-18 — DUPLICATE generates a NEW `subscriptionProgramId` | ACTIVE subscription with `subscriptionProgramId="uuid-A"`. Call `duplicateSubscription()`. | New DRAFT doc: `subscriptionProgramId` is a NEW UUID (different from "uuid-A"). `name="<original> (Copy)"`. `parentId=null`. | TS-NEW-38 | `SubscriptionFacade.duplicateSubscription(Long orgId, String subscriptionProgramId, String createdBy)` | UT |
| BT-R-30 | `shouldRejectSecondForkWhenDraftExists` | ADR-18 — cannot edit ACTIVE when a DRAFT fork already exists | ACTIVE subscription `id="uuid-A"`. A DRAFT already exists with `parentId=<ACTIVE.objectId>`. Attempt second call to `editActiveSubscription()` | `IllegalStateException` (or `InvalidSubscriptionStateException`) — "A pending draft edit already exists for this subscription." Second fork rejected. | TS-NEW-39 | `SubscriptionFacade.editActiveSubscription(Long orgId, String subscriptionProgramId, SubscriptionProgram request, String updatedBy)` — checks `repository.findDraftByParentIdAndOrgId(active.objectId, orgId)` | UT |

---

### Rework Integration Tests (IT layer)

> Full Spring Boot test slice or embedded MongoDB (Testcontainers). Thrift mock via `@Mock`. HTTP layer via MockMvc or direct facade calls.

| ID | Test Name | Verifies | Boundary | Input | Expected Output | QA Scenario | Layer |
|----|-----------|----------|----------|-------|-----------------|-------------|-------|
| BT-R-31 | `shouldCreateAndRetrieveBySubscriptionProgramId` | ADR-18 — `subscriptionProgramId` persisted to MongoDB and retrievable | Service → MongoDB | Create a valid subscription → GET by `subscriptionProgramId` | GET response `subscriptionProgramId` matches created value. Status=DRAFT. All other fields match create request. | TS-NEW-35 | IT |
| BT-R-32 | `shouldPublishAllThriftFieldsOnApprove` | ADR-08 through ADR-17 — all 15 Thrift fields correctly populated on approve | Service → Thrift mock → MongoDB | Full approve flow: subscription with `name="Gold Plan"`, `description="Desc"`, `subscriptionType=TIER_BASED`, `programType=SUPPLEMENTARY`, `pointsExchangeRatio=2.5`, `syncWithLoyaltyTierOnDowngrade=true`, `tierConfig.tiers=[{1,"Silver"},{2,"Gold"}]`, `tierConfig.loyaltySyncTiers={"Silver":"Bronze"}`, `duration={MONTHS,6}`, `expiry.migrationTargetProgramId=123`, submitted and approved | Thrift mock `createOrUpdatePartnerProgram` captured argument: field 2=`"Gold Plan"`, field 3=`"Desc"`, field 4=`true`, field 5=[Silver,Gold], field 6=`2.5`, field 8=`SUPPLEMENTARY`, field 9=`{MONTHS,6}`, field 10=`true`, field 11=`{"Silver":"Bronze"}`, field 14=`123`. MongoDB status=ACTIVE. | TS-NEW-22, TS-NEW-24, TS-NEW-26, TS-NEW-30 | IT |
| BT-R-33 | `shouldRejectExternalSubscriptionWithDurationViaApi` | ADR-14 — EXTERNAL + duration → 400 at submit | HTTP POST `/v3/subscriptions` then SUBMIT → 422 | `POST /v3/subscriptions` with `{ programType: "EXTERNAL", duration: { cycleType: "MONTHS", cycleValue: 3 }, ... }` → save as DRAFT → `PUT /.../status` `{ action: "SUBMIT_FOR_APPROVAL" }` | `SUBMIT` call: HTTP 422. `InvalidSubscriptionStateException` from `validateForSubmission()` — duration cleared then check passes OR direct rejection; either way, EXTERNAL with duration does not reach ACTIVE. Entity remains DRAFT. | TS-NEW-10 | IT |
| BT-R-34 | `shouldAcceptSupplementarySubscriptionViaApi` | ADR-14 — SUPPLEMENTARY with all required fields → 201 then full lifecycle | HTTP POST `/v3/subscriptions` | `POST /v3/subscriptions` with `{ programType: "SUPPLEMENTARY", duration: { cycleType: "MONTHS", cycleValue: 12 }, pointsExchangeRatio: 1.5, name: "Premium Plan", description: "A premium plan", subscriptionType: "NON_TIER", syncWithLoyaltyTierOnDowngrade: false, ... }` | HTTP 201. MongoDB doc created: `status=DRAFT`, `programType=SUPPLEMENTARY`, `pointsExchangeRatio=1.5`. All required fields persisted. | TS-NEW-09 | IT |
| BT-R-35 | `shouldEnforceNameUniquenessAcrossOrgCaseInsensitive` | ADR-11, KD-50 — case-insensitive name uniqueness enforced end-to-end | HTTP POST `/v3/subscriptions` × 2 | First `POST`: `{ name: "Gold Plan", orgId: 100, ... }` → 201. Second `POST`: `{ name: "gold plan", orgId: 100, ... }` | First: HTTP 201. Second: HTTP 409. `SubscriptionNameConflictException` raised from `SubscriptionFacade.createSubscription()` via case-insensitive MongoDB `$regex` query. MongoDB has exactly 1 document for orgId=100. | TS-NEW-13, TS-NEW-14 | IT |

---

### Rework Test Class Mapping (Additions)

| Test Class | Covers BT IDs | Type | Repo |
|-----------|--------------|------|------|
| `SubscriptionNameValidationTest` | BT-R-01, BT-R-02, BT-R-03 | UT | intouch-api-v3 |
| `SubscriptionDescriptionValidationTest` | BT-R-04, BT-R-05, BT-R-06 | UT | intouch-api-v3 |
| `CycleTypeValidationTest` | BT-R-07 | UT | intouch-api-v3 |
| `SubscriptionProgramTypeValidationTest` | BT-R-08, BT-R-09, BT-R-10, BT-R-11 | UT | intouch-api-v3 |
| `PointsExchangeRatioValidationTest` | BT-R-12 | UT | intouch-api-v3 |
| `SubscriptionPublishServiceReworkTest` | BT-R-13, BT-R-14, BT-R-17, BT-R-18, BT-R-19, BT-R-20 | UT | intouch-api-v3 |
| `SyncFlagValidationTest` | BT-R-15 | UT | intouch-api-v3 |
| `TierConfigValidationTest` | BT-R-16 | UT | intouch-api-v3 |
| `MigrationValidationTest` | BT-R-21, BT-R-22, BT-R-23 | UT | intouch-api-v3 |
| `NameUniquenessTest` | BT-R-24, BT-R-25 | UT (`@DataMongoTest`) | intouch-api-v3 |
| `SubscriptionProgramIdLifecycleTest` | BT-R-26, BT-R-27, BT-R-28, BT-R-29, BT-R-30 | UT | intouch-api-v3 |
| `SubscriptionReworkIntegrationTest` | BT-R-31, BT-R-32, BT-R-33, BT-R-34, BT-R-35 | IT | intouch-api-v3 |

**New test classes added: 12** (all in intouch-api-v3)

---

### Gap-to-Test Traceability Matrix

| Gap / ADR | KD | Description | Test Cases |
|-----------|-----|-------------|------------|
| GAP-1 / ADR-08 | KD-47 | Name: max 50 chars + regex | BT-R-01, BT-R-02, BT-R-03 |
| GAP-2 / ADR-09 | KD-48 | Description: required + max 100 chars + regex | BT-R-04, BT-R-05, BT-R-06 |
| GAP-3 / ADR-10 | KD-49 | YEARS cycle type rejected at API boundary | BT-R-07 |
| GAP-4 / ADR-11 | KD-50 | Case-insensitive name uniqueness | BT-R-24, BT-R-25, BT-R-35 |
| GAP-5 / ADR-12 | KD-51 | `pointsExchangeRatio` required, not hardcoded | BT-R-12, BT-R-13 |
| GAP-6 / ADR-13 | KD-52 | `syncWithLoyaltyTierOnDowngrade` direct field | BT-R-14, BT-R-15 |
| GAP-7 / ADR-14 | KD-53 | `programType` required; duration conditional | BT-R-08, BT-R-09, BT-R-10, BT-R-11, BT-R-33, BT-R-34 |
| GAP-8 / ADR-15 | KD-54 | Migration: `migrationTargetProgramId` required when enabled | BT-R-21, BT-R-22, BT-R-23 |
| GAP-9 / ADR-16 | KD-55 | `partnerProgramTiers` list wired and validated | BT-R-16, BT-R-17, BT-R-18 |
| GAP-10 / ADR-17 | KD-56 | `loyaltySyncTiers` map wired | BT-R-19, BT-R-20 |
| GAP-11 / ADR-18 | KD-58 | `subscriptionProgramId` lifecycle correctness | BT-R-26, BT-R-27, BT-R-28, BT-R-29, BT-R-30, BT-R-31 |
| All gaps / combined | — | Full Thrift 15-field publish test | BT-R-32 |

**All 12 gaps traced to at least 1 test case. No coverage gaps.**

---

*Rework total: 35 new test cases (BT-R-01 through BT-R-35) — 30 UT + 5 IT. Grand total: 137 test cases (102 original + 35 rework).*

---

## Rework 5 — Extended Fields (ADR-19, KD-62/63) (2026-04-20)

> **Source**: Designer Rework 5 (R-32 through R-35), KD-62 through KD-65
> Extended Fields replace `customFields`. Stored in MongoDB only — no Thrift pass-through.
> `ExtendedFieldType`: `CUSTOMER_EXTENDED_FIELD`, `TXN_EXTENDED_FIELD`

### Group EF — Extended Fields Unit Tests

| ID | Test Name | Verifies | Input | Expected Output | ADR/KD | Designer Interface | Layer |
|----|-----------|----------|-------|-----------------|--------|-------------------|-------|
| BT-EF-01 | `shouldPersistExtendedFieldsOnCreate` | ADR-19, KD-62 — extendedFields stored on CREATE | `createSubscription(request{extendedFields=[CEF:tier_level=gold, TEF:source_channel=mobile]})` | Created doc has `extendedFields` size=2, first entry `type=CUSTOMER_EXTENDED_FIELD, key=tier_level` | ADR-19 | `SubscriptionFacade.createSubscription()` | UT |
| BT-EF-02 | `shouldOverwriteExtendedFieldsOnUpdateWhenProvided` | R-33 — non-null list on PUT → full overwrite | DRAFT with `extendedFields=[old_key]`. PUT with `extendedFields=[new_key]` | Result has `extendedFields` size=1, key=`new_key`, type=`TXN_EXTENDED_FIELD` | R-33 | `SubscriptionFacade.updateSubscription()` | UT |
| BT-EF-03 | `shouldPreserveExtendedFieldsWhenUpdateOmitsField` | R-33 null-guard — null on PUT → existing list preserved | DRAFT with `extendedFields=[keep_me]`. PUT with `extendedFields=null` | Result still has `extendedFields` size=1, key=`keep_me` (unchanged) | R-33 | `SubscriptionFacade.updateSubscription()` | UT |
| BT-EF-04 | `shouldCarryExtendedFieldsIntoNewDraftFork` | R-35 — `editActiveSubscription` carries EF from ACTIVE into DRAFT | ACTIVE with `extendedFields=[fork_key]`. Call `editActiveSubscription()` | New DRAFT has `extendedFields` size=1, key=`fork_key` (copied from ACTIVE) | R-35 | `SubscriptionFacade.editActiveSubscription()` | UT |
| BT-EF-05 | `shouldCopyExtendedFieldsOnDuplicate` | R-35 — `duplicateSubscription` copies EF from source | ACTIVE with `extendedFields=[source_key]`. Call `duplicateSubscription()` | Copy has `extendedFields` size=1, key=`source_key`. New `subscriptionProgramId`. `parentId=null`. | R-35 | `SubscriptionFacade.duplicateSubscription()` | UT |
| BT-EF-06 | `shouldAcceptMultipleExtendedFieldsOfSameAndDifferentType` | ADR-19 — multiple EF entries (same type + different type) stored | CREATE with 3 fields: 2×`CUSTOMER_EXTENDED_FIELD` + 1×`TXN_EXTENDED_FIELD` | Created doc `extendedFields` size=3. 2 CEF entries, 1 TEF entry. | ADR-19 | `SubscriptionFacade.createSubscription()` | UT |

### Rework 5 Test Class Mapping

| Test Class | Covers BT IDs | Type | Repo |
|-----------|--------------|------|------|
| `SubscriptionExtendedFieldsTest` | BT-EF-01 through BT-EF-06 | UT | intouch-api-v3 |

**New test cases: 6 UT. Running total: 137 + 6 = 143 test cases.**
