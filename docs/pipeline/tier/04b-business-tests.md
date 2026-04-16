# Business Test Cases -- Tiers CRUD + Generic Maker-Checker

> Phase 8b: Business Test Gen
> Date: 2026-04-12
> Source: 00-ba.md (52 ACs, 7 user stories), 04-qa.md (89 scenarios), 03-designer.md (interfaces), 01-architect.md (7 ADRs), 02-analyst.md (8 risks), ui-requirements.md, GUARDRAILS.md
> Confidence: C5 (full traceability chain established across all input artifacts; some edge-case test names may adjust during SDET)

---

## Section 1: Coverage Summary

| Artifact | Total | Covered by Business Tests | Coverage |
|----------|-------|---------------------------|----------|
| BA Acceptance Criteria | 52 | 52 | 100% |
| QA Test Scenarios | 89 | 89 | 100% |
| Designer Interface Methods | 16 (4 TierFacade + 5 MakerCheckerService + 2 TierChangeApplier + 5 TierValidationService) | 16 | 100% |
| ADRs | 7 (ADR-01 through ADR-07) | 7 | 100% |
| Risks | 8 (R1-R8) | 8 | 100% |
| Guardrail Areas | 8 (G-01.7, G-02.3, G-02.7, G-03.1, G-06.1, G-07.4, G-10, G-05.4) | 8 | 100% |

### Test Case Counts

| Category | UT | IT | Total |
|----------|----|----|-------|
| TierFacade -- Listing | 8 | 5 | 13 |
| TierFacade -- Creation | 10 | 5 | 15 |
| TierFacade -- Update | 10 | 4 | 14 |
| TierFacade -- Deletion | 7 | 3 | 10 |
| MakerCheckerService | 12 | 4 | 16 |
| TierValidationService | 14 | 0 | 14 |
| TierChangeApplier | 10 | 4 | 14 |
| ADR Compliance | 4 | 8 | 12 |
| Guardrail Compliance | 5 | 7 | 12 |
| Risk Mitigation | 4 | 5 | 9 |
| **Total** | **84** | **45** | **129** |

---

## Section 2: Functional Test Cases (Unit Tests)

### 2.1 TierFacade -- Listing

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-01 | shouldReturnAllTiersForProgramOrderedBySerialNumber | US1-AC1, US1-AC10 | orgId=100, programId=977, statusFilter=null | TierListResponse with tiers sorted by serialNumber ASC | TS-L01, TS-L10 | TierFacade.listTiers(orgId, programId, statusFilter) | UT |
| BT-02 | shouldReturnEmptyListWhenNoTiersExist | US1-AC1 | orgId=100, programId=99999 | TierListResponse with empty tiers list, KPI summary all zeros | TS-L02 | TierFacade.listTiers | UT |
| BT-03 | shouldIncludeAllConfigSectionsPerTier | US1-AC2, US1-AC3, US1-AC4, US1-AC5 | orgId=100, programId=977 | Each tier has non-null basicDetails, eligibilityCriteria, renewalConfig, downgradeConfig | TS-L03 | TierFacade.listTiers | UT |
| BT-04 | shouldReturnBenefitIdsNotFullBenefitObjects | US1-AC6 | orgId=100, programId=977 (tiers with benefitIds) | benefitIds is List of String ObjectIds, not full benefit documents | TS-L04 | TierFacade.listTiers | UT |
| BT-05 | shouldComputeAccurateKpiSummary | US1-AC7 | orgId=100, programId=977 (3 ACTIVE, 1 DRAFT, 1 PENDING_APPROVAL) | summary: totalTiers=5, activeTiers=3, pendingApprovalTiers=1, totalMembers=sum of cached counts | TS-L05 | TierFacade.listTiers | UT |
| BT-06 | shouldReturnCachedMemberCountWithLastRefreshed | US1-AC8 | Tier doc with memberStats.memberCount=1245, lastRefreshed=2026-04-12T10:00:00Z | memberStats present with both fields, no live DB query | TS-L06, TS-L07 | TierFacade.listTiers | UT |
| BT-07 | shouldFilterTiersByStatus | US1-AC9 | statusFilter=[ACTIVE] | Only ACTIVE tiers returned; DRAFT, PENDING_APPROVAL, DELETED excluded | TS-L08 | TierFacade.listTiers | UT |
| BT-08 | shouldFilterByMultipleStatuses | US1-AC9 | statusFilter=[ACTIVE, DRAFT] | Both ACTIVE and DRAFT returned; DELETED excluded | TS-L09 | TierFacade.listTiers | UT |

### 2.2 TierFacade -- Creation

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-09 | shouldCreateDraftTierWhenMCEnabled | US2-AC1, US2-AC5 | Valid TierCreateRequest, MC enabled | UnifiedTierConfig with status=DRAFT, objectId generated, serialNumber auto-assigned | TS-C01 | TierFacade.createTier(orgId, request, userId) | UT |
| BT-10 | shouldCreateActiveTierAndSyncWhenMCDisabled | US2-AC1, US2-AC6 | Valid TierCreateRequest, MC disabled | UnifiedTierConfig with status=ACTIVE, sqlSlabId populated | TS-C02 | TierFacade.createTier | UT |
| BT-11 | shouldAutoAssignSerialNumberAsMaxPlusOne | US2-AC7 | Program with 3 existing tiers (serialNumbers 1,2,3) | New tier gets serialNumber=4 | TS-C08 | TierFacade.createTier | UT |
| BT-12 | shouldCreateTierWithOnlyRequiredFields | US2-AC2, US2-AC3 | name + programId + eligibilityCriteriaType + eligibilityThreshold, all optional fields null | 201, optional fields null/default, no error | TS-C05 | TierFacade.createTier | UT |
| BT-13 | shouldRejectCreationWhenRequiredFieldMissing | US2-AC2, US2-AC8 | TierCreateRequest without basicDetails.name | Validation error: "basicDetails.name is required" | TS-C03 | TierFacade.createTier | UT |
| BT-14 | shouldRejectCreationWhenProgramIdMissing | US2-AC2, US2-AC8 | TierCreateRequest without programId | Validation error: "programId is required" | TS-C04 | TierFacade.createTier | UT |
| BT-15 | shouldRejectDuplicateNameWithinProgram | US2-AC4 | name="Gold" in program that already has "Gold" | 409 Conflict: "A tier with name 'Gold' already exists" | TS-C06 | TierFacade.createTier (delegates to TierValidationService) | UT |
| BT-16 | shouldAllowDuplicateNameAcrossPrograms | US2-AC4 | name="Gold" in programId=978, "Gold" exists in programId=977 | 201 created successfully | TS-C07 | TierFacade.createTier | UT |
| BT-17 | shouldStoreMongoDocWithUIFieldNames | US2-AC9 | Valid TierCreateRequest with eligibilityCriteria | MongoDB doc fields use UI names: "eligibilityCriteria", "renewalConfig", "downgradeConfig" | TS-C09 | TierFacade.createTier | UT |
| BT-18 | shouldReturnOriginalResponseOnDuplicateIdempotencyKey | US2-AC1 | Same Idempotency-Key sent twice | Second call returns original response, no duplicate tier created | TS-C09 | TierFacade.createTier | UT |

### 2.3 TierFacade -- Update

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-19 | shouldUpdateDraftTierInPlace | US3-AC1, US3-AC2 | PUT tierId=draftId, updated name | Same objectId returned, name updated | TS-E01 | TierFacade.updateTier(orgId, tierId, request, userId) | UT |
| BT-20 | shouldCreateVersionedDraftWhenEditingActiveTier | US3-AC3 | PUT tierId=activeId, updated description | NEW objectId, status=DRAFT, parentId=activeId, version=2 | TS-E02 | TierFacade.updateTier | UT |
| BT-21 | shouldUpdatePendingApprovalTierInPlace | US3-AC4 | PUT tierId=pendingId, updated color | Same objectId, updated in place | TS-E03 | TierFacade.updateTier | UT |
| BT-22 | shouldRejectEditOnDeletedTier | US3-AC5 | PUT tierId=deletedId | 400: "Cannot edit a tier in DELETED status" | TS-E04 | TierFacade.updateTier | UT |
| BT-23 | shouldPreserveSerialNumberOnEdit | US3-AC6 | PUT with serialNumber=1 on tier with serialNumber=3 | serialNumber remains 3 in response (field ignored) | TS-E05 | TierFacade.updateTier | UT |
| BT-24 | shouldReturnValidationErrorsOnInvalidEdit | US3-AC7 | PUT with invalid eligibilityCriteria | 400, field-level validation errors | TS-E06 | TierFacade.updateTier | UT |
| BT-25 | shouldEnforceOneDraftPerActiveTier | US3-AC3 | Edit same ACTIVE tier twice | Second edit updates existing DRAFT, does not create another | TS-E09 | TierFacade.updateTier | UT |
| BT-26 | shouldPreserveEngineConfigOnRoundTrip | US3-AC5 | PUT with full body including engineConfig | engineConfig values preserved unchanged in saved doc | TS-E10 | TierFacade.updateTier | UT |
| BT-27 | shouldRejectEditOnSnapshotTier | US3-AC5 | PUT tierId=snapshotId | 400: "Cannot edit a tier in SNAPSHOT status" | EC-33 | TierFacade.updateTier | UT |
| BT-28 | shouldKeepActiveTierLiveDuringPendingEdit | US3-AC3, US3-AC8 | Create versioned DRAFT from ACTIVE | GET listing shows ACTIVE (original) + DRAFT (edit) as separate docs | TS-E08 | TierFacade.updateTier + TierFacade.listTiers | UT |

### 2.4 TierFacade -- Deletion

> **Rework #2**: Deletion is DRAFT-only → DELETED. No MC flow. No STOPPED status. No member reassessment. BT-29/30/31/33/34 are OBSOLETE. BT-32 is the primary happy path (updated). BT-35 updated to cover all non-DRAFT statuses with 409.

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-29 | ~~shouldSoftDeleteActiveTierWhenMCDisabled~~ | ~~US4-AC1, US4-AC2, US4-AC4~~ | ~~DELETE tierId=activeId, MC disabled~~ | ~~Status set to STOPPED in MongoDB + SQL~~ | ~~TS-D01~~ | ~~TierFacade.deleteTier~~ | **OBSOLETE** — ACTIVE deletion out of scope (Rework #2) |
| BT-30 | ~~shouldCreatePendingChangeForDeleteWhenMCEnabled~~ | ~~US4-AC1, US4-AC3~~ | ~~DELETE tierId=activeId, MC enabled~~ | ~~PendingChange created with changeType=DELETE~~ | ~~TS-D02~~ | ~~TierFacade.deleteTier~~ | **OBSOLETE** — no MC flow for deletion (Rework #2) |
| BT-31 | ~~shouldBlockDeleteOfBaseTierWithMembers~~ | ~~US4-AC5~~ | ~~DELETE tier with serialNumber=1, memberCount>0~~ | ~~409: "Cannot stop base tier 'Bronze' -- N members assigned"~~ | ~~TS-D03~~ | ~~TierFacade.deleteTier~~ | **OBSOLETE** — no member reassessment on DRAFT delete (Rework #2) |
| BT-32 | shouldTransitionDraftTierToDeleted | US4-AC1 | DELETE tierId=draftId | 204 No Content, tier status set to DELETED in MongoDB. No SQL change. No MC gate. | TS-D04 | TierFacade.deleteTier(orgId, tierId, userId) | UT |
| BT-33 | ~~shouldFlagMembersForReassessmentOnDelete~~ | ~~US4-AC7~~ | ~~DELETE ACTIVE tier, MC disabled~~ | ~~Members in that tier flagged for PEB reassessment~~ | ~~TS-D05~~ | ~~TierFacade.deleteTier~~ | **OBSOLETE** — no reassessment on DRAFT-only deletion (Rework #2) |
| BT-34 | ~~shouldBlockDeleteWhenPartnerProgramSlabsExist~~ | ~~US4-AC1~~ | ~~DELETE tier referenced by PartnerProgramSlabs~~ | ~~409: "Cannot stop tier -- has active partner program slab mappings"~~ | ~~TS-D06~~ | ~~TierFacade.deleteTier~~ | **OBSOLETE** — only DRAFT tiers deleted; DRAFT has no partner slab references (Rework #2) |
| BT-35 | shouldReturn409WhenDeletingNonDraftTier | US4-AC4 | DELETE tierId=activeId (or PENDING_APPROVAL, SNAPSHOT) | 409: "Tier cannot be deleted. Only DRAFT tiers can be deleted." | TS-D07 | TierFacade.deleteTier | UT |

### 2.5 MakerCheckerService -- Submit

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-36 | shouldSubmitDraftTierForApproval | US5-AC1, US5-AC3 | entityType=TIER, entityId=draftId | PendingChange created, tier status -> PENDING_APPROVAL | TS-S01 | MakerCheckerService.submit(orgId, entityType, entityId, changeType, payload, requestedBy) | UT |
| BT-37 | shouldAcceptNonTierEntityType | US5-AC2 | entityType=BENEFIT, entityId=benefitId | PendingChange created (generic framework accepts any EntityType) | TS-S02 | MakerCheckerService.submit | UT |
| BT-38 | shouldRecordRequestedByAndTimestampAndPayload | US5-AC4 | Submit with userId="user-123" | PendingChange has requestedBy="user-123", requestedAt=now, payload=full snapshot | TS-S03 | MakerCheckerService.submit | UT |
| BT-39 | shouldInvokeNotificationHandlerOnSubmit | US5-AC5 | Submit a tier | NotificationHandler.onSubmit invoked (no-op default, no error) | TS-S04 | MakerCheckerService.submit (via NotificationHandler) | UT |
| BT-40 | shouldRejectSubmitOnActiveTier | US5-AC3 | Submit an ACTIVE tier | 400: "Tier is in ACTIVE status. Only DRAFT tiers can be submitted." | TS-S05 | MakerCheckerService.submit | UT |
| BT-41 | shouldRejectSubmitOnNonExistentEntity | US5-AC1 | Submit with invalid entityId | 404: entity not found | TS-S06 | MakerCheckerService.submit | UT |
| BT-42 | shouldRejectSubmitOnAlreadyPendingTier | US5-AC3 | Submit on PENDING_APPROVAL tier | 400: "Tier is already pending approval" | TS-S07 | MakerCheckerService.submit | UT |

### 2.6 MakerCheckerService -- Approve/Reject

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-43 | shouldApproveCreateChangeAndTransitionToActive | US6-AC1, US6-AC4 | changeId for CREATE change | Tier: PENDING_APPROVAL -> ACTIVE, ChangeApplier.apply invoked | TS-A01, TS-A04 | MakerCheckerService.approve(orgId, changeId, reviewedBy, comment) | UT |
| BT-44 | shouldRejectChangeWithRequiredComment | US6-AC2, US6-AC5 | changeId, comment="Too low" | Tier: PENDING_APPROVAL -> DRAFT, PendingChange: REJECTED | TS-A02 | MakerCheckerService.reject(orgId, changeId, reviewedBy, comment) | UT |
| BT-45 | shouldRejectWithoutCommentFails | US6-AC2 | changeId, comment=null | 400: "Comment is required when rejecting" | TS-A03 | MakerCheckerService.reject | UT |
| BT-46 | shouldRecordReviewerDetailsOnApproval | US6-AC6 | Approve with reviewedBy="admin-1" | PendingChange has reviewedBy, reviewedAt, comment populated | TS-A06 | MakerCheckerService.approve | UT |
| BT-47 | shouldListPendingChangesForEntityType | US6-AC7 | entityType=TIER, programId=977 | Returns all PENDING_APPROVAL PendingChanges for TIER in program 977 | TS-A07 | MakerCheckerService.listPending(orgId, entityType, programId) | UT |
| BT-48 | shouldApproveVersionedEditAndSwapDocuments | US3-AC8, US6-AC4 | Approve DRAFT with parentId | New doc -> ACTIVE, old doc -> SNAPSHOT | TS-A08, TS-E07 | MakerCheckerService.approve | UT |
| BT-49 | ~~shouldApproveDeleteChangeAndSetStopped~~ | ~~US4-AC3, US6-AC1~~ | ~~Approve DELETE PendingChange~~ | ~~Tier -> STOPPED, SQL status updated~~ | ~~TS-A09~~ | ~~MakerCheckerService.approve~~ | **OBSOLETE** — no MC flow for deletion; TS-A09 removed in Rework #2 |
| BT-50 | shouldRejectApprovalOnNonExistentChangeId | US6-AC1 | Non-existent changeId | 404: "Change not found" | TS-A11 | MakerCheckerService.approve | UT |
| BT-51 | shouldRejectApprovalOnAlreadyProcessedChange | US6-AC1 | changeId already APPROVED | 400: "Change already processed" | TS-A12 | MakerCheckerService.approve | UT |

### 2.7 MakerCheckerService -- Toggle

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-52 | shouldReturnMCEnabledStatus | US7-AC1 | orgId=100, programId=977, entityType=TIER | boolean: true or false | TS-MC01 | MakerCheckerService.isMakerCheckerEnabled(orgId, programId, entityType) | UT |
| BT-53 | shouldCreateActiveTierDirectlyWhenMCDisabled | US7-AC3 | Create tier, MC disabled | status=ACTIVE, SQL synced immediately | TS-MC03 | TierFacade.createTier (calls isMakerCheckerEnabled) | UT |
| BT-54 | shouldCreateDraftTierWhenMCEnabled | US7-AC4 | Create tier, MC enabled | status=DRAFT, no SQL sync | TS-MC04 | TierFacade.createTier (calls isMakerCheckerEnabled) | UT |
| BT-55 | shouldNotAutoActivateExistingDraftsWhenMCToggledOff | US7-AC5 | Toggle MC off, DRAFT tier exists | DRAFT tier stays DRAFT (not auto-activated) | TS-MC05 | MakerCheckerService.isMakerCheckerEnabled | UT |

### 2.8 TierValidationService

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-56 | shouldRejectEmptyTierName | US2-AC2 | name="" | Validation error: "name is required, non-blank" | EC-01 | TierValidationService | UT |
| BT-57 | shouldRejectTierNameExceedingMaxLength | US2-AC2 | name=256 chars | Validation error: "name exceeds max length" | EC-02 | TierValidationService | UT |
| BT-58 | shouldSanitizeSpecialCharactersInName | US2-AC4 | name contains `<script>`, SQL injection attempt | Safely accepted/sanitized, no injection | EC-03 | TierValidationService | UT |
| BT-59 | shouldRejectNegativeThreshold | US2-AC4 | eligibilityThreshold = -100 | Validation error: "threshold must be positive" | EC-05 | TierValidationService | UT |
| BT-60 | shouldAcceptZeroThresholdForBaseTier | US2-AC4 | eligibilityThreshold = 0 for base tier (serialNumber=1) | Accepted (base tier has no threshold requirement) | EC-04 | TierValidationService | UT |
| BT-61 | shouldAcceptDecimalThreshold | US2-AC4 | eligibilityThreshold = 550.5 | Accepted (RM amounts support decimals) | EC-06 | TierValidationService | UT |
| BT-62 | shouldRejectEndDateBeforeStartDate | US2-AC2 | endDate < startDate | Validation error: "endDate must be after startDate" | EC-07 | TierValidationService | UT |
| BT-63 | shouldRejectInvalidColorHex | US2-AC2 | color="red" | Validation error: "color must be a valid hex code" | TS-C10 | TierValidationService | UT |
| BT-64 | shouldRejectColorHexWithoutHashPrefix | US2-AC2 | color="FF5733" | Validation error: "color must be a valid hex code" | EC-11 | TierValidationService | UT |
| BT-65 | shouldRejectProgramIdZero | US2-AC2 | programId=0 | Validation error: "invalid programId" | EC-12 | TierValidationService | UT |
| BT-66 | shouldRejectCreationBeyond50TierCap | US2-AC4 | Program already has 50 tiers | 400: "Maximum 50 tiers per program" | TS-L15, EC-13 | TierValidationService | UT |
| BT-67 | shouldRejectEmptyActivitiesArray | US2-AC2 | eligibilityCriteria.activities = [] | Validation error: "at least one activity required" | EC-10 | TierValidationService | UT |
| BT-68 | shouldEnforceNameUniquenessWithinProgram | US2-AC4 | name="Gold", program already has "Gold" | 409: duplicate name | TS-C06 | TierValidationService | UT |
| BT-69 | shouldValidateSerialNumberImmutabilityOnEdit | US3-AC6 | Edit attempt changing serialNumber | serialNumber field ignored or rejected | TS-E05 | TierValidationService | UT |

### 2.9 TierChangeApplier

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-70 | shouldBuildSlabInfoFromBasicDetails | US6-AC3 | UnifiedTierConfig with basicDetails | SlabInfo with name, description, colorCode, serialNumber, updatedViaNewUI=true | TS-A04 | TierChangeApplier.apply(PendingChange, orgId) | UT |
| BT-71 | shouldBuildUpgradeStrategyInfoWithThresholdCSV | US6-AC3 | UnifiedTierConfig with eligibilityCriteria (threshold=5000) | StrategyInfo type=2 (SLAB_UPGRADE), threshold appended to CSV | TS-A05 | TierChangeApplier.apply | UT |
| BT-72 | shouldBuildDowngradeStrategyInfoFromConfig | US6-AC3 | UnifiedTierConfig with downgradeConfig | StrategyInfo type=5 (SLAB_DOWNGRADE), TierConfiguration JSON updated | TS-A05 | TierChangeApplier.apply | UT |
| BT-73 | shouldMapCSVIndexCorrectlyForSerialNumber | US6-AC3 | Tier with serialNumber=4 in 4-tier program | CSV index = serialNumber - 2 = 2 (0-indexed in CSV, base tier has no entry) | TS-A05 | TierChangeApplier.apply | UT |
| BT-74 | shouldPassOnlyUpgradeAndDowngradeStrategiesToThrift | US6-AC3, US6-AC4 | Full UnifiedTierConfig | Thrift call receives exactly [SLAB_UPGRADE, SLAB_DOWNGRADE] strategies, NOT allocation/expiry | TS-A05 | TierChangeApplier.apply | UT |
| BT-75 | shouldUpdateSqlSlabIdInMongoAfterSync | US6-AC4 | Approved tier, Thrift returns SlabInfo with id=42 | MongoDB doc metadata.sqlSlabId = 42 | TS-A01 | TierChangeApplier.apply | UT |
| BT-76 | shouldSwapVersionsOnEditApproval | US3-AC8, US6-AC4 | PendingChange for UPDATE with parentId | New doc -> ACTIVE, old ACTIVE doc -> SNAPSHOT | TS-A08 | TierChangeApplier.apply | UT |
| BT-77 | shouldPassCriteriaTypeDirectlyToThrift | US6-AC3 | criteriaType=CUMULATIVE_PURCHASES | Thrift current_value_type=CUMULATIVE_PURCHASES (same value, no conversion) | TS-A05 | TierChangeApplier.apply | UT |
| BT-78 | shouldSetUpdatedViaNewUIFlagTrue | US6-AC3 | Any tier sync | SlabInfo.updatedViaNewUI = true, StrategyInfo.updatedViaNewUI = true | TS-A05 | TierChangeApplier.apply | UT |
| BT-79 | ~~shouldApplyDeleteBySettingStatusToStopped~~ | ~~US4-AC2, US4-AC3~~ | ~~PendingChange with changeType=DELETE~~ | ~~MongoDB status -> STOPPED, SQL ProgramSlab status -> STOPPED~~ | ~~TS-A09~~ | ~~TierChangeApplier.apply~~ | **OBSOLETE** — no MC-gated delete flow; deletion sets DELETED directly on DRAFT with no SQL change (Rework #2) |

---

## Section 3: Functional Test Cases (Integration Tests)

### 3.1 API Endpoint Tests (TierController)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-80 | shouldReturn200WithTierListFromEndpoint | US1-AC1 | GET /v3/tiers?programId=977 | 200 OK, ResponseWrapper with TierListResponse containing tiers and summary | TS-L01 | TierController -> TierFacade.listTiers | IT |
| BT-81 | shouldReturn400WhenProgramIdMissing | US1-AC1 | GET /v3/tiers (no programId) | 400 error: "programId is required" | TS-L12 | TierController | IT |
| BT-82 | shouldReturn201OnTierCreation | US2-AC1 | POST /v3/tiers with valid body | 201 Created, UnifiedTierConfig in ResponseWrapper | TS-C01 | TierController -> TierFacade.createTier | IT |
| BT-83 | shouldReturn200OnTierUpdate | US3-AC1 | PUT /v3/tiers/{tierId} with valid body | 200 OK, updated UnifiedTierConfig | TS-E01 | TierController -> TierFacade.updateTier | IT |
| BT-84 | shouldReturn204OnDraftDeletion | US4-AC1 | DELETE /v3/tiers/{draftId} | 204 No Content | TS-D04 | TierController -> TierFacade.deleteTier | IT |
| BT-85 | shouldReturn404OnNonExistentTierDelete | US4-AC1 | DELETE /v3/tiers/nonexistent | 404 Not Found | TS-D08 | TierController -> TierFacade.deleteTier | IT |
| BT-86 | shouldReturn200WithTierDetailIncludingEngineConfig | P75-1 | GET /v3/tiers/{objectId} | 200 OK with full doc including engineConfig section | TS-GD01, TS-GD03 | TierController -> TierFacade | IT |
| BT-87 | shouldReturn404ForNonExistentTierDetail | P75-1 | GET /v3/tiers/nonexistent | 404: "Tier not found" | TS-GD04 | TierController | IT |
| BT-88 | ~~shouldReturnStoppedTiersOnlyWhenIncludeInactiveTrue~~ | ~~US4-AC6~~ | ~~GET /v3/tiers?programId=977&includeInactive=true~~ | ~~STOPPED tiers included; without flag, STOPPED excluded~~ | ~~TS-L13, TS-L14~~ | ~~TierController -> TierFacade.listTiers~~ | **OBSOLETE** — STOPPED status removed; DELETED is terminal and never surfaced in listings (Rework #2) |
| BT-89 | shouldExcludeEngineConfigFromListingResponse | US1-AC2 | GET /v3/tiers?programId=977 | engineConfig field absent or null on each tier in listing | TS-L11 | TierController -> TierFacade.listTiers | IT |

### 3.2 API Endpoint Tests (MakerCheckerController)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-90 | shouldSubmitChangeViaEndpoint | US5-AC1 | POST /v3/maker-checker/submit with {entityType: TIER, entityId, changeType: CREATE} | 200, PendingChange returned | TS-S01 | MakerCheckerController -> MakerCheckerService.submit | IT |
| BT-91 | shouldApproveChangeViaEndpoint | US6-AC1 | POST /v3/maker-checker/{changeId}/approve | 200, tier becomes ACTIVE | TS-A01 | MakerCheckerController -> MakerCheckerService.approve | IT |
| BT-92 | shouldRejectChangeViaEndpoint | US6-AC2 | POST /v3/maker-checker/{changeId}/reject with comment | 200, tier reverts to DRAFT | TS-A02 | MakerCheckerController -> MakerCheckerService.reject | IT |
| BT-93 | shouldListPendingChangesViaEndpoint | US6-AC7 | GET /v3/maker-checker/pending?entityType=TIER&programId=977 | 200, list of PendingChange objects | TS-A07 | MakerCheckerController -> MakerCheckerService.listPending | IT |
| BT-94 | shouldReturnMCConfigViaEndpoint | US7-AC1, P75-2 | GET /v3/maker-checker/config?programId=977&entityType=TIER | 200, makerCheckerEnabled: true/false | TS-MC01 | MakerCheckerController -> MakerCheckerService.isMakerCheckerEnabled | IT |
| BT-95 | shouldReturn400WhenMCConfigMissingProgramId | US7-AC1 | GET /v3/maker-checker/config without programId | 400 error | TS-MC06 | MakerCheckerController | IT |
| BT-96 | shouldReturnChangeDetailViaEndpoint | P75-3 | GET /v3/maker-checker/{changeId} | 200 OK with full PendingChange including payload snapshot | TS-GC01 | MakerCheckerController | IT |
| BT-97 | shouldReturn404ForNonExistentChangeDetail | P75-3 | GET /v3/maker-checker/nonexistent | 404 | TS-GC02 | MakerCheckerController | IT |

### 3.3 MongoDB Persistence Tests

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-98 | shouldPersistUnifiedTierConfigToMongo | US2-AC1 | Create tier via TierFacade | Document found in unified_tier_configs collection with correct fields | TS-C12 | TierRepository (MongoDB) | IT |
| BT-99 | shouldPersistPendingChangeToMongo | US5-AC1 | Submit tier via MakerCheckerService | Document found in pending_changes collection with full payload | TS-S03 | PendingChangeRepository (MongoDB) | IT |
| BT-100 | shouldFilterByOrgIdInMongoQuery | US1-AC1 | List tiers for orgId=100 when orgId=200 also has tiers | Only orgId=100 tiers returned | EC-40 | TierRepository (MongoDB) | IT |
| BT-101 | shouldHandleShardedMongoAccess | US2-AC1 | Create and read tier via sharded EmfMongoDataSourceManager | Correctly routes to shard, data round-trips | -- | TierRepositoryImpl | IT |

### 3.4 Thrift Sync Tests (Mocked Thrift)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-102 | shouldCallCreateSlabAndUpdateStrategiesOnApproval | US6-AC3, US6-AC4 | Approve a CREATE PendingChange | Thrift mock verifies createSlabAndUpdateStrategies called with correct SlabInfo + strategies | TS-A04, TS-A05 | TierChangeApplier.apply -> PointsEngineRulesThriftService | IT |
| BT-103 | shouldRollbackOnThriftSyncFailure | US6-AC3 | Approve, but Thrift call throws exception | 500: "Failed to sync. Approval rolled back." Tier stays PENDING_APPROVAL | TS-A10 | TierChangeApplier.apply | IT |
| BT-104 | shouldCallThriftWithAtomicSingleCall | US6-AC3 | Approve a tier | Exactly ONE Thrift call (not separate slab + strategy calls) | TS-ADR12 | TierChangeApplier.apply | IT |

### 3.5 Full Flow Integration Tests

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-105 | shouldCompleteFullCreateSubmitApproveFlow | US2-AC1, US5-AC1, US6-AC1 | POST /tiers -> POST /submit -> POST /approve | Tier goes DRAFT -> PENDING_APPROVAL -> ACTIVE, SQL slab created | TS-C01, TS-S01, TS-A01 | TierFacade + MakerCheckerService + TierChangeApplier | IT |
| BT-106 | shouldCompleteFullEditSubmitApproveSwapFlow | US3-AC3, US3-AC8, US6-AC4 | PUT /tiers/{activeId} -> POST /submit -> POST /approve | New doc ACTIVE, old doc SNAPSHOT | TS-E02, TS-E07, TS-A08 | TierFacade + MakerCheckerService + TierChangeApplier | IT |
| BT-107 | ~~shouldCompleteFullDeleteSubmitApproveFlow~~ | ~~US4-AC3, US6-AC1~~ | ~~DELETE /tiers/{activeId} -> POST /submit -> POST /approve~~ | ~~Tier -> STOPPED, SQL status -> STOPPED~~ | ~~TS-D02, TS-A09~~ | ~~TierFacade + MakerCheckerService + TierChangeApplier~~ | **OBSOLETE** — no MC-gated delete flow; replaced by BT-32/BT-84 direct DRAFT→DELETED path (Rework #2) |
| BT-108 | shouldCompleteCreateWithMCDisabledDirectToActive | US2-AC6, US7-AC3 | POST /tiers (MC disabled) | Tier immediately ACTIVE, sqlSlabId populated, Thrift called | TS-C02, TS-MC03 | TierFacade + TierChangeApplier | IT |

---

## Section 4: Compliance Test Cases

### 4.1 ADR Compliance

| ID | Test Name | ADR | Verifies | Input | Expected Output | QA Scenario | Layer |
|----|-----------|-----|----------|-------|-----------------|-------------|-------|
| BT-109 | shouldStoreInMongoOnlyNotSQLWhenMCEnabled | ADR-01 | Dual-storage: MongoDB for drafts, SQL only on approval | Create tier (MC on) | MongoDB doc exists, no ProgramSlab row in SQL | TS-ADR01 | IT |
| BT-110 | shouldSyncBothMongoAndSQLOnApproval | ADR-01 | Dual-storage: both stores consistent after approval | Approve tier | MongoDB doc ACTIVE, SQL ProgramSlab created | TS-ADR02 | IT |
| BT-111 | shouldAcceptAnyEntityTypeThroughMCFramework | ADR-02 | Generic MC: entity-agnostic | Submit BENEFIT entity type | PendingChange created for BENEFIT | TS-ADR03 | IT |
| BT-112 | shouldDispatchToCorrectChangeApplierPerEntityType | ADR-02 | Generic MC: strategy dispatch | Approve TIER change | TierChangeApplier invoked (not a generic applier) | TS-ADR04 | UT |
| ~~BT-113~~ | ~~shouldNotBreakExistingFindByProgramQuery~~ | ~~ADR-03~~ | ~~Expand-then-contract: existing DAO unchanged~~ | ~~Call findByProgram() after adding status column~~ | ~~Returns ALL slabs regardless of status~~ | ~~TS-ADR05~~ | ~~IT~~ | **OBSOLETE** — ADR-03 removed (Rework #3: no SQL changes) |
| ~~BT-114~~ | ~~shouldFilterNonActiveInNewFindActiveByProgram~~ | ~~ADR-03~~ | ~~Expand-then-contract: new filtered query~~ | ~~Call findActiveByProgram()~~ | ~~Returns only ACTIVE slabs~~ | ~~TS-ADR06~~ | ~~IT~~ | **OBSOLETE** — ADR-03 removed (Rework #3: no findActiveByProgram()) |
| ~~BT-115~~ | ~~shouldDefaultExistingRowsToActiveOnMigration~~ | ~~ADR-03~~ | ~~Flyway migration default value~~ | ~~Run migration on existing rows~~ | ~~All rows have status='ACTIVE'~~ | ~~TS-ADR07~~ | ~~IT~~ | **OBSOLETE** — ADR-03 removed (Rework #3: no Flyway migration) |
| BT-116 | shouldKeepActiveLiveWhileDraftPending | ADR-04 | Versioned edits: zero downtime | Edit ACTIVE tier | ACTIVE stays in listing, DRAFT is separate doc | TS-ADR08 | UT |
| BT-117 | shouldRevertDraftAndPreserveActiveOnReject | ADR-04 | Versioned edits: rollback | Reject versioned DRAFT | DRAFT reverts, ACTIVE unchanged | TS-ADR09 | UT |
| BT-118 | shouldUseExistingThriftMethodsWithoutIDLChange | ADR-05 | Existing Thrift reuse | Approve tier | createSlabAndUpdateStrategies called via existing Thrift client | TS-ADR10 | IT |
| BT-119 | shouldReturnEmptyForOldProgramWithNoMongoData | ADR-06 | New programs only | List tiers for legacy program (no MongoDB docs) | Empty list from tier API; legacy system continues to serve old programs | TS-ADR11 | UT |
| BT-120 | shouldExecuteStrategiesBeforeSlabInAtomicCall | ADR-07 | Atomic Thrift call: order verified | Approve tier | Thrift call includes both strategies AND slab; engine updates strategies FIRST then creates slab | TS-ADR12 | IT |

### 4.2 Guardrail Compliance

| ID | Test Name | Guardrail | Verifies | Input | Expected Output | QA Scenario | Layer |
|----|-----------|-----------|----------|-------|-----------------|-------------|-------|
| BT-121 | shouldStoreAndReturnDatesInUTC | G-01.7 | Timezone: all dates UTC | Create tier with startDate in IST (+05:30) | Stored as UTC Instant, returned as ISO-8601 UTC | GR-01, EC-50 | IT |
| BT-122 | shouldHandleNonStandardTimezoneOffset | G-01.7 | Timezone: NPT (+05:45) | Create tier with NPT offset date | Correctly converted and stored as UTC | EC-51 | IT |
| BT-123 | shouldFailFastOnNullProgramId | G-02.3 | Null safety: fail fast at entry | POST /v3/tiers with null programId | 400 error, not NPE deep in business logic | GR-02 | UT |
| BT-124 | shouldReturnEmptyListNotNullForEmptyProgram | G-02.3 | Null safety: collections never null | List tiers for program with 0 tiers | Returns [], not null | GR-03 | UT |
| BT-125 | shouldHandleUnknownTierStatusGracefully | G-02.7 | Defensive: default switch case | Filter by unknown status value "ARCHIVED" | 400 error or gracefully ignored, not exception | GR-04 | UT |
| BT-126 | shouldPreventSQLInjectionInTierName | G-03.1 | Security: parameterized queries | name = "'; DROP TABLE program_slabs; --" | Name safely stored, no SQL injection | GR-05 | IT |
| BT-127 | shouldReturnOriginalOnDuplicateIdempotencyKey | G-06.1 | Idempotency: POST dedup | Same Idempotency-Key twice | Second call returns original response, no duplicate | GR-07 | IT |
| BT-128 | shouldIsolateTenantDataCompletely | G-07.4 | Multi-tenancy: cross-tenant isolation | Create as orgId=100, query as orgId=200 | orgId=200 sees empty result | GR-08, EC-40, EC-41 | IT |
| BT-129 | shouldReturn404WhenAccessingOtherOrgTier | G-07.4 | Multi-tenancy: cross-tenant edit | orgId=200 tries to edit orgId=100's tier | 404: tier not found | EC-41 | IT |
| BT-130 | shouldPreventConcurrentApprovalsViLocking | G-10 | Concurrency: @Lockable prevents double-sync | Two concurrent approvals for same tier | One succeeds, other waits or fails; no data corruption | GR-09, EC-21 | IT |
| BT-131 | shouldUseCorrectHTTPStatusCodes | G-06.4 | API design: correct status codes | Create (201), Update (200), Delete-draft (204), Not-found (404), Conflict (409), Bad-request (400) | Correct HTTP status per operation | GR-11 | IT |
| BT-132 | shouldMaintainBackwardCompatibilityOnMigration | G-05.4 | Data integrity: expand-then-contract | Run Flyway migration | Old code with new schema works; status column has DEFAULT | GR-10 | IT |

### 4.3 Risk Mitigation

| ID | Test Name | Risk | Verifies | Input | Expected Output | QA Scenario | Layer |
|----|-----------|------|----------|-------|-----------------|-------------|-------|
| BT-133 | shouldMapCSVIndexCorrectlyFor4thTierIn3TierProgram | R1 (HIGH) | CSV off-by-one: threshold CSV position | Create 4th tier in 3-tier program | threshold CSV has 3 values (positions 0,1,2); new tier threshold at index 2 | R1 scenario | UT |
| BT-134 | shouldExtendAllStrategyCSVsOnNewTierCreation | R1 (HIGH) | CSV extension: allocation + expiry CSVs | Create 5th tier | Thrift auto-extends allocation_values and expiry_time_values each by one position | R1 scenario | IT |
| BT-135 | shouldSerializeConcurrentApprovalsViaLockable | R2 (MEDIUM) | Downgrade race: @Lockable prevents concurrent syncs | Two approvals in parallel for same program | @Lockable key locks on program; sequential execution | R2 scenario | IT |
| BT-136 | shouldPreserveExistingStrategyIdsOnUpdate | R3 (MEDIUM) | Strategy ID collision: fetch-before-update | Edit tier eligibility | Strategy update uses existing strategy ID, not insert-new | R3 scenario | IT |
| BT-137 | shouldUseCoveringIndexForMemberCountQuery | R4 (MEDIUM) | Member count index: query efficiency | Run member count aggregation | Query uses idx_ce_org_program_slab index (verify via explain or mock) | R4 scenario | IT |
| BT-138 | shouldPreventTimezoneDriftOnStoreAndRetrieve | R5 (MEDIUM) | Timezone: UTC storage | Store date as IST, retrieve | No drift: stored as UTC, returned as UTC | R5 scenario | IT |
| BT-139 | shouldDeduplicateViaIdempotencyKey | R6 (LOW) | Idempotency: retry safety | POST same Idempotency-Key twice | No duplicate tier; returns original | R6 scenario | IT |
| BT-140 | shouldCarryTenantContextInCronJob | R7 (LOW) | Cron tenant context: orgId propagation | Member count cron job executes | Job processes per-org, carries orgId in execution context | R7 scenario | UT |
| BT-141 | shouldEnforceOrBlockSelfApproval | R8 (LOW) | MC self-approval: same user submit+approve | requestedBy == reviewedBy | Product decision: either blocked (400) or allowed (documented as accepted risk) | R8 scenario | UT |

---

## Section 5: Coverage Gaps

| # | Gap | Impact | Resolution |
|---|-----|--------|------------|
| 1 | No integration test infrastructure exists for MongoDB + Thrift in intouch-api-v3 | ITs BT-98 through BT-108, BT-120 need embedded MongoDB + Thrift mock | SDET must establish: embedded MongoDB (Flapdoodle or Testcontainers), Mockito-based Thrift service mock |
| 2 | Benefits cross-reference in listing (US1-AC6) | benefitIds returned only; no test for benefit detail resolution | Out of scope (benefits API is separate epic E2). Test BT-04 verifies benefitIds array is correctly returned. |
| 3 | Member count cron job scheduling and execution | No SDET test for periodic refresh trigger and MongoDB update | SDET should add IT for: cron fires -> query executes -> memberStats updated on tier docs. BT-140 covers tenant context only. |
| 4 | MC notification hook beyond no-op | BT-39 only verifies NoOpNotificationHandler does not throw | Real notification implementation deferred. Hook interface test is sufficient for this pipeline. |
| 5 | secondaryCriteriaEnabled + additionalUpgradeCriteria | BA mentions but no detailed scenarios in QA | Add edge-case UT: create tier with secondaryCriteriaEnabled=true, verify additionalCriteria stored correctly. Not a separate BT since it maps to EngineConfig round-trip (BT-26). |
| 6 | SNAPSHOT tier accessibility via detail endpoint | TS-GD05 covers reading SNAPSHOT tiers | Covered by BT-86 (detail endpoint) but no explicit SNAPSHOT-specific BT. SDET can add as sub-case of BT-86. |
| 7 | R8 (self-approval) is a product decision | Test BT-141 describes both outcomes | SDET should implement whichever behavior product decides; currently left as conditional. |

---

## Appendix A: Traceability Matrix (BA AC -> QA -> BT)

| BA AC | QA Scenario(s) | Business Test(s) |
|-------|----------------|------------------|
| US1-AC1 | TS-L01, TS-L02 | BT-01, BT-02, BT-80 |
| US1-AC2 | TS-L03 | BT-03 |
| US1-AC3 | TS-L03 | BT-03 |
| US1-AC4 | TS-L03 | BT-03 |
| US1-AC5 | TS-L03 | BT-03 |
| US1-AC6 | TS-L04 | BT-04 |
| US1-AC7 | TS-L05 | BT-05 |
| US1-AC8 | TS-L06, TS-L07 | BT-06 |
| US1-AC9 | TS-L08, TS-L09 | BT-07, BT-08 |
| US1-AC10 | TS-L10 | BT-01 |
| US1-AC11 | TS-L11 | BT-89 |
| US2-AC1 | TS-C01, TS-C02 | BT-09, BT-10, BT-82 |
| US2-AC2 | TS-C03, TS-C04 | BT-13, BT-14, BT-56-67 |
| US2-AC3 | TS-C05 | BT-12 |
| US2-AC4 | TS-C06, TS-C07, TS-C08 | BT-15, BT-16, BT-11 |
| US2-AC5 | TS-C01 | BT-09 |
| US2-AC6 | TS-C02 | BT-10 |
| US2-AC7 | TS-C08 | BT-11 |
| US2-AC8 | TS-C03, TS-C04 | BT-13, BT-14 |
| US2-AC9 | TS-C09 | BT-17 |
| US3-AC1 | TS-E01 | BT-19, BT-83 |
| US3-AC2 | TS-E01 | BT-19 |
| US3-AC3 | TS-E02 | BT-20, BT-25, BT-28 |
| US3-AC4 | TS-E03 | BT-21 |
| US3-AC5 | TS-E04 | BT-22, BT-26, BT-27 |
| US3-AC6 | TS-E05 | BT-23, BT-69 |
| US3-AC7 | TS-E06 | BT-24 |
| US3-AC8 | TS-E07 | BT-48, BT-76 |
| US4-AC1 | TS-D04 | BT-32, BT-84, BT-85 |
| US4-AC2 | ~~TS-D01~~ | ~~BT-29~~ (OBSOLETE — Rework #2) |
| US4-AC3 | ~~TS-D02~~ | ~~BT-30~~ (OBSOLETE — Rework #2) |
| US4-AC4 | TS-D07 | BT-35 |
| US4-AC5 | ~~TS-D03~~ | ~~BT-31~~ (OBSOLETE — Rework #2) |
| US4-AC6 | ~~TS-D04~~ | ~~BT-88~~ (OBSOLETE — Rework #2) |
| US4-AC7 | ~~TS-D05~~ | ~~BT-33~~ (OBSOLETE — Rework #2) |
| US5-AC1 | TS-S01 | BT-36, BT-90 |
| US5-AC2 | TS-S02 | BT-37 |
| US5-AC3 | TS-S01 | BT-36, BT-40, BT-42 |
| US5-AC4 | TS-S03 | BT-38 |
| US5-AC5 | TS-S04 | BT-39 |
| US6-AC1 | TS-A01 | BT-43, BT-91 |
| US6-AC2 | TS-A02, TS-A03 | BT-44, BT-45, BT-92 |
| US6-AC3 | TS-A04 | BT-43, BT-70-79 |
| US6-AC4 | TS-A05 | BT-43, BT-102 |
| US6-AC5 | TS-A02 | BT-44 |
| US6-AC6 | TS-A06 | BT-46 |
| US6-AC7 | TS-A07 | BT-47, BT-93 |
| US7-AC1 | TS-MC01 | BT-52, BT-94 |
| US7-AC2 | TS-MC02 | BT-52 |
| US7-AC3 | TS-MC03 | BT-53, BT-108 |
| US7-AC4 | TS-MC04 | BT-54 |
| US7-AC5 | TS-MC05 | BT-55 |
| P75-1 | TS-GD01, TS-GD02 | BT-86, BT-87 |
| P75-2 | TS-MC01 | BT-94 |
| P75-3 | TS-GC01 | BT-96, BT-97 |

---

## Appendix B: QA Scenario -> Business Test Mapping

| QA Scenario | Business Test(s) |
|-------------|------------------|
| TS-L01 | BT-01, BT-80 |
| TS-L02 | BT-02 |
| TS-L03 | BT-03 |
| TS-L04 | BT-04 |
| TS-L05 | BT-05 |
| TS-L06 | BT-06 |
| TS-L07 | BT-06 |
| TS-L08 | BT-07 |
| TS-L09 | BT-08 |
| TS-L10 | BT-01 |
| TS-L11 | BT-89 |
| TS-L12 | BT-81 |
| TS-L13 | ~~BT-88~~ (OBSOLETE — Rework #2) |
| TS-L14 | ~~BT-88~~ (OBSOLETE — Rework #2) |
| TS-L15 | BT-66 |
| TS-GD01 | BT-86 |
| TS-GD02 | BT-86 |
| TS-GD03 | BT-86 |
| TS-GD04 | BT-87 |
| TS-GD05 | BT-86 (sub-case) |
| TS-C01 | BT-09, BT-82, BT-105 |
| TS-C02 | BT-10, BT-108 |
| TS-C03 | BT-13 |
| TS-C04 | BT-14 |
| TS-C05 | BT-12 |
| TS-C06 | BT-15, BT-68 |
| TS-C07 | BT-16 |
| TS-C08 | BT-11 |
| TS-C09 | BT-17, BT-18 |
| TS-C10 | BT-63 |
| TS-C11 | BT-62 |
| TS-C12 | BT-98 |
| TS-C13 | BT-109 |
| TS-E01 | BT-19, BT-83 |
| TS-E02 | BT-20, BT-106 |
| TS-E03 | BT-21 |
| TS-E04 | BT-22 |
| TS-E05 | BT-23, BT-69 |
| TS-E06 | BT-24 |
| TS-E07 | BT-48, BT-76, BT-106 |
| TS-E08 | BT-28 |
| TS-E09 | BT-25 |
| TS-E10 | BT-26 |
| TS-D01 | ~~BT-29~~ (OBSOLETE — Rework #2) |
| TS-D02 | ~~BT-30, BT-107~~ (OBSOLETE — Rework #2) |
| TS-D03 | ~~BT-31~~ (OBSOLETE — Rework #2) |
| TS-D04 | BT-32, BT-84 |
| TS-D05 | ~~BT-33~~ (OBSOLETE — Rework #2) |
| TS-D06 | ~~BT-34~~ (OBSOLETE — Rework #2) |
| TS-D07 | BT-35 |
| TS-D08 | BT-85 |
| TS-S01 | BT-36, BT-90, BT-105 |
| TS-S02 | BT-37 |
| TS-S03 | BT-38, BT-99 |
| TS-S04 | BT-39 |
| TS-S05 | BT-40 |
| TS-S06 | BT-41 |
| TS-S07 | BT-42 |
| TS-A01 | BT-43, BT-91, BT-105 |
| TS-A02 | BT-44, BT-92 |
| TS-A03 | BT-45 |
| TS-A04 | BT-43, BT-102 |
| TS-A05 | BT-43, BT-102, BT-104 |
| TS-A06 | BT-46 |
| TS-A07 | BT-47, BT-93 |
| TS-A08 | BT-48, BT-106 |
| TS-A09 | ~~BT-49, BT-107~~ (OBSOLETE — Rework #2) |
| TS-A10 | BT-103 |
| TS-A11 | BT-50 |
| TS-A12 | BT-51 |
| TS-GC01 | BT-96 |
| TS-GC02 | BT-97 |
| TS-GC03 | BT-96 |
| TS-MC01 | BT-52, BT-94 |
| TS-MC02 | BT-52 |
| TS-MC03 | BT-53, BT-108 |
| TS-MC04 | BT-54 |
| TS-MC05 | BT-55 |
| TS-MC06 | BT-95 |
| TS-MC07 | BT-95 |
| EC-01 | BT-56 |
| EC-02 | BT-57 |
| EC-03 | BT-58, BT-126 |
| EC-04 | BT-60 |
| EC-05 | BT-59 |
| EC-06 | BT-61 |
| EC-07 | BT-62 |
| EC-08 | BT-121 (subsumes) |
| EC-09 | BT-04 (benefitIds accepted without validation) |
| EC-10 | BT-67 |
| EC-11 | BT-64 |
| EC-12 | BT-65 |
| EC-13 | BT-66 |
| EC-20 | BT-25, BT-130 |
| EC-21 | BT-130 |
| EC-22 | BT-11 (serialNumber uniqueness) |
| EC-23 | BT-35 (delete blocked during pending) |
| EC-24 | BT-135 |
| EC-30 | BT-40 |
| EC-31 | BT-50 |
| EC-32 | BT-51 |
| EC-33 | BT-27 |
| EC-34 | BT-27 (sub-case for SNAPSHOT delete) |
| EC-35 | BT-40 (DELETED submit blocked) |
| EC-40 | BT-128 |
| EC-41 | BT-129 |
| EC-42 | BT-128 |
| EC-43 | BT-140 |
| EC-50 | BT-121 |
| EC-51 | BT-122 |
| EC-52 | BT-121 (sub-case) |
| EC-53 | BT-121 |
| TS-ADR01 | BT-109 |
| TS-ADR02 | BT-110 |
| TS-ADR03 | BT-111 |
| TS-ADR04 | BT-112 |
| TS-ADR05 | BT-113 |
| TS-ADR06 | BT-114 |
| TS-ADR07 | BT-115 |
| TS-ADR08 | BT-116 |
| TS-ADR09 | BT-117 |
| TS-ADR10 | BT-118 |
| TS-ADR11 | BT-119 |
| TS-ADR12 | BT-120 |
| GR-01 | BT-121, BT-122 |
| GR-02 | BT-123 |
| GR-03 | BT-124 |
| GR-04 | BT-125 |
| GR-05 | BT-126 |
| GR-06 | BT-126 (XSS sub-case) |
| GR-07 | BT-127 |
| GR-08 | BT-128 |
| GR-09 | BT-130 |
| GR-10 | BT-132 |
| GR-11 | BT-131 |
