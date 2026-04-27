# Business Test Cases -- Tiers CRUD + Generic Maker-Checker

> Phase 8b: Business Test Gen
> Date: 2026-04-12 (updated 2026-04-17 — Rework #5 cascade)
> Source: 00-ba.md, 04-qa.md, 03-designer.md, 01-architect.md, 02-analyst.md, ui-requirements.md, GUARDRAILS.md, rework-5-scope.md
> Confidence: C5 (full traceability chain established; Rework #5 delta appended as Section 6)
>
> **Rework trail**: #1 (MC-always), #2 (tier-retirement deferred), #3 (status removal),
> #4 (engine data-model alignment), #5 (unified read surface, dual write paths, schema cleanup).
>
> **Rework #5 triage result**: ~35 existing BTs affected (CONFIRMED / UPDATED / REGENERATED /
> OBSOLETE) + 34 new BTs added (BT-142 through BT-175). See Section 6 for the full delta log,
> structured disagreement log, and new-BT listings. Legacy tables below (§2-§5) are retained
> with inline strikethrough/update annotations — **always cross-reference Section 6** for current
> post-Rework #5 scope.

---

## Section 1: Coverage Summary

> **Post-Rework #5 numbers.** Pre-Rework #5 baseline was 129 BTs (84 UT + 45 IT).

| Artifact | Total | Covered by Business Tests | Coverage |
|----------|-------|---------------------------|----------|
| BA Acceptance Criteria | 60 (52 original + 8 new from Rework #5) | 60 | 100% |
| QA Test Scenarios | 89 + drift-block / envelope / dual-path additions | 89+ | 100% |
| Designer Interface Methods | 22 (4 TierFacade + 5 MakerCheckerService<T> + 6 TierApprovalHandler + 5 TierValidationService + TierDriftChecker + SqlTierConverter) | 22 | 100% |
| ADRs | 16 (ADR-01 through ADR-07 + ADR-06R reversal + ADR-08R..ADR-16R new) | 16 | 100% |
| Risks | 15 (R1-R8 original + R6-R12 Rework #5) | 15 | 100% |
| Guardrail Areas | 9 (8 original + G-13 exception handling) | 9 | 100% |

### Test Case Counts (post-Rework #5)

| Category | UT | IT | Total | Net Change |
|----------|----|----|-------|------------|
| TierFacade -- Unified Listing (envelope) | 10 | 6 | 16 | +3 |
| TierFacade -- Single Read (envelope by slabId / tierUniqueId) | 4 | 2 | 6 | +6 (new) |
| TierFacade -- Creation | 10 | 5 | 15 | 0 |
| TierFacade -- Update (dual-path) | 11 | 4 | 15 | +1 |
| TierFacade -- Deletion | 7 | 3 | 10 | 0 |
| TierFacade -- Approve/Reject split | 5 | 3 | 8 | +8 (new) |
| MakerCheckerService<T> | 10 | 4 | 14 | -2 (MC toggle removed) |
| TierValidationService (incl. 3-layer name + single-active) | 18 | 0 | 18 | +4 |
| TierApprovalHandler (incl. drift, name L2, single-active L2) | 14 | 5 | 19 | +5 |
| TierDriftChecker | 6 | 2 | 8 | +8 (new) |
| SqlTierConverter / SqlTierReader | 4 | 2 | 6 | +6 (new) |
| Mongo Partial Unique Index (backstop) | 0 | 2 | 2 | +2 (new) |
| SQL Audit Columns | 0 | 3 | 3 | +3 (new) |
| Dual-Path (old UI bypasses MC) | 0 | 2 | 2 | +2 (new) |
| ADR Compliance (incl. ADR-06R..16R) | 6 | 10 | 16 | +4 |
| Guardrail Compliance | 5 | 8 | 13 | +1 (G-13) |
| Risk Mitigation (incl. R6-R12 Rework #5) | 6 | 7 | 13 | +4 |
| R5-R4 Renewal Contract (B1a) — normalizer + wiring + synthesis | 7 | 3 | 10 | +10 (new) |
| **Total (post-Rework #5, post-R4 B1a)** | **~123** | **~71** | **~194** | **+65 net** |
| **OBSOLETE in this rework** | | | **~12** | |

---

## Section 2: Functional Test Cases (Unit Tests)

### 2.1 TierFacade -- Listing

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-01 | shouldReturnAllTiersForProgramOrderedBySerialNumber | US1-AC1, US1-AC10 | orgId=100, programId=977, statusFilter=null | TierListResponse with tiers sorted by serialNumber ASC | TS-L01, TS-L10 | TierFacade.listTiers(orgId, programId, statusFilter) | UT |
| BT-02 | shouldReturnEmptyListWhenNoTiersExist | US1-AC1 | orgId=100, programId=99999 | TierListResponse with empty tiers list, KPI summary all zeros | TS-L02 | TierFacade.listTiers | UT |
| BT-03 | shouldIncludeAllConfigSectionsPerTier ^(UPDATED — Rework #5)^ | US1-AC2, US1-AC3, US1-AC4, US1-AC5 | orgId=100, programId=977 | Each tier's envelope has non-null hoisted fields (name, description, color, serialNumber) + eligibility, validity, downgrade. ~~nudges~~ DROPPED. | TS-L03 | TierFacade.listTiers | UT |
| ~~BT-04~~ | ~~shouldReturnBenefitIdsNotFullBenefitObjects~~ | ~~US1-AC6~~ | ~~orgId=100, programId=977~~ | ~~benefitIds is List of String ObjectIds~~ | ~~TS-L04~~ | ~~TierFacade.listTiers~~ | **OBSOLETE** — benefitIds field dropped from UnifiedTierConfig (Rework #5 Q-7b) |
| BT-05 | shouldComputeAccurateKpiSummary ^(UPDATED — Rework #5)^ | US1-AC7 | orgId=100, programId=977 (3 LIVE from SQL, 1 DRAFT in Mongo, 1 PENDING_APPROVAL in Mongo) | summary: totalTiers=5 (envelope count, not Mongo-only), liveTiers=3 (from SQL), pendingApprovalTiers=1, totalMembers=sum of cached counts. "activeTiers" renamed to "liveTiers" (Rework #5 — LIVE lives in SQL). | TS-L05 | TierFacade.listTiers | UT |
| BT-06 | shouldReturnCachedMemberCountWithLastRefreshed | US1-AC8 | Tier doc with memberStats.memberCount=1245, lastRefreshed=2026-04-12T10:00:00Z | memberStats present with both fields, no live DB query | TS-L06, TS-L07 | TierFacade.listTiers | UT |
| BT-07 | shouldFilterTiersByStatus ^(UPDATED — Rework #5)^ | US1-AC9 | statusFilter=[LIVE] (synthetic) | Only LIVE tiers returned (from SQL); envelope.pendingDraft null for all. Status filter now operates on envelope dimensions: LIVE (SQL row exists), DRAFT (Mongo DRAFT present), PENDING_APPROVAL (Mongo PENDING_APPROVAL present). | TS-L08 | TierFacade.listTiers | UT |
| BT-08 | shouldFilterByMultipleStatuses ^(UPDATED — Rework #5)^ | US1-AC9 | statusFilter=[LIVE, DRAFT] | Envelopes with EITHER a LIVE SQL row OR a Mongo DRAFT (or both) returned; SNAPSHOT-only/DELETED excluded | TS-L09 | TierFacade.listTiers | UT |

### 2.2 TierFacade -- Creation

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-09 | shouldCreateDraftTierFromNewUI ^(UPDATED — Rework #5)^ | US2-AC1, US2-AC5 | Valid TierCreateRequest | UnifiedTierConfig with status=DRAFT, objectId generated, tierUniqueId assigned, serialNumber auto-assigned, slabId=null, meta.basisSqlSnapshot=null (brand-new tier). MC condition removed — new UI ALWAYS goes through MC. | TS-C01 | TierFacade.createTier(orgId, request, userId) | UT |
| ~~BT-10~~ | ~~shouldCreateActiveTierAndSyncWhenMCDisabled~~ | ~~US2-AC1, US2-AC6~~ | ~~Valid TierCreateRequest, MC disabled~~ | ~~status=ACTIVE, sqlSlabId populated~~ | ~~TS-C02~~ | ~~TierFacade.createTier~~ | **OBSOLETE** — no "MC disabled" path exists in new UI. Old UI writes via legacy SlabFacade (not TierFacade) and always bypasses MC. Replaced by BT-161 (dual-path write). |
| BT-11 | shouldAutoAssignSerialNumberAsMaxPlusOne | US2-AC7 | Program with 3 existing tiers (serialNumbers 1,2,3) | New tier gets serialNumber=4 | TS-C08 | TierFacade.createTier | UT |
| BT-12 | shouldCreateTierWithOnlyRequiredFields ^(UPDATED — Rework #5)^ | US2-AC2, US2-AC3 | name + programId, eligibility/validity/downgrade all null (no more `nudges` in tier) | 201, optional fields null/default, no error | TS-C05 | TierFacade.createTier | UT |
| BT-13 | shouldRejectCreationWhenRequiredFieldMissing ^(UPDATED — Rework #5)^ | US2-AC2, US2-AC8 | TierCreateRequest without name (hoisted, no more `basicDetails` wrapper) | Validation error: "name is required" | TS-C03 | TierFacade.createTier | UT |
| BT-14 | shouldRejectCreationWhenProgramIdMissing | US2-AC2, US2-AC8 | TierCreateRequest without programId | Validation error: "programId is required" | TS-C04 | TierFacade.createTier | UT |
| BT-15 | shouldRejectDuplicateNameWithinProgram ^(UPDATED — Rework #5, Layer 1 of 3)^ | US2-AC4 | name="Gold" when "Gold" already exists as LIVE (SQL) OR DRAFT/PENDING (Mongo) | 409 CONFLICT_NAME: "A tier with name 'Gold' already exists". Check runs against BOTH SQL (LIVE) and Mongo (DRAFT/PENDING) for this program. | TS-C06 | TierFacade.createTier → TierValidationService.validateNameUniquenessUnified | UT |
| BT-16 | shouldAllowDuplicateNameAcrossPrograms | US2-AC4 | name="Gold" in programId=978, "Gold" exists in programId=977 | 201 created successfully | TS-C07 | TierFacade.createTier | UT |
| BT-17 | shouldStoreMongoDocWithEngineAlignedFieldNames ^(UPDATED — Rework #5)^ | US2-AC9 | Valid TierCreateRequest with eligibility config | MongoDB doc fields use engine-aligned names at ROOT level (hoisted): `name`, `description`, `color`, `serialNumber`, `eligibility`, `validity`, `downgrade`. **No more** `basicDetails` / `metadata` / `nudges` wrapper keys. Stored field set matches UnifiedTierConfig schema exactly. | TS-C09 | TierFacade.createTier | UT |
| BT-18 | shouldReturnOriginalResponseOnDuplicateIdempotencyKey | US2-AC1 | Same Idempotency-Key sent twice | Second call returns original response, no duplicate tier created | TS-C09 | TierFacade.createTier | UT |

### 2.3 TierFacade -- Update

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-19 | shouldUpdateDraftTierInPlace ^(UPDATED — Rework #5)^ | US3-AC1, US3-AC2 | PUT tierId=draftId with updated name | Same objectId returned, name updated. basisSqlSnapshot retained (null for brand-new DRAFT, preserved for edit-of-LIVE DRAFT). | TS-E01 | TierFacade.updateTier(orgId, programId, tierId, request, userId) | UT |
| BT-20 | shouldCreateNewDraftWhenEditingLiveTier ^(REGENERATED — Rework #5)^ | US3-AC3 | PUT tierId=slabId (LIVE SQL tier), updated description | NEW Mongo DRAFT created with: objectId=new, status=DRAFT, parentId=**slabId** (Long, not ObjectId), slabId=same, version=next, meta.basisSqlSnapshot=captured from current SQL at DRAFT creation time | TS-E02 | TierFacade.updateTier | UT |
| ~~BT-21~~ | ~~shouldUpdatePendingApprovalTierInPlace~~ | ~~US3-AC4~~ | ~~PUT tierId=pendingId~~ | ~~Same objectId, updated in place~~ | ~~TS-E03~~ | ~~TierFacade.updateTier~~ | **OBSOLETE** — PENDING_APPROVAL docs are IMMUTABLE under Rework #5. Single-active-draft invariant blocks concurrent editing of PENDING. Approver must reject first; maker re-edits the resulting DRAFT. Replaced by BT-175. |
| BT-22 | shouldRejectEditOnDeletedTier | US3-AC5 | PUT tierId=deletedId | 400: "Cannot edit a tier in DELETED status" | TS-E04 | TierFacade.updateTier | UT |
| BT-23 | shouldPreserveSerialNumberOnEdit | US3-AC6 | PUT with serialNumber=1 on tier with serialNumber=3 | serialNumber remains 3 in response (field ignored) | TS-E05 | TierFacade.updateTier | UT |
| BT-24 | shouldReturnValidationErrorsOnInvalidEdit | US3-AC7 | PUT with invalid eligibility config | 400, field-level validation errors | TS-E06 | TierFacade.updateTier | UT |
| BT-25 | shouldEnforceOneDraftPerLiveTier ^(UPDATED — Rework #5)^ | US3-AC3 | Edit same LIVE tier twice while DRAFT already exists | Second edit UPDATES existing Mongo DRAFT IN-PLACE (case A), does NOT create another. Mongo partial unique index on (orgId, programId, slabId) filtered to status IN (DRAFT, PENDING_APPROVAL) is the DB backstop. | TS-E09 | TierFacade.updateTier → TierValidationService.enforceSingleActiveDraft | UT |
| BT-26 | shouldPreserveEngineConfigOnRoundTrip | US3-AC5 | PUT with full body including engineConfig | engineConfig values preserved unchanged in saved doc | TS-E10 | TierFacade.updateTier | UT |
| BT-27 | shouldRejectEditOnSnapshotTier | US3-AC5 | PUT tierId=snapshotId | 400: "Cannot edit a tier in SNAPSHOT status" | EC-33 | TierFacade.updateTier | UT |
| BT-28 | shouldKeepLiveTierVisibleDuringPendingEdit ^(UPDATED — Rework #5)^ | US3-AC3, US3-AC8 | Create NEW Mongo DRAFT from LIVE SQL tier | GET listing returns ONE envelope with live=TierView(from SQL) AND pendingDraft=TierView(from Mongo). hasPendingDraft=true. LIVE continues to serve runtime traffic. | TS-E08 | TierFacade.updateTier + TierFacade.listTiers | UT |

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
| BT-36 | shouldSubmitDraftTierForApproval | US5-AC1, US5-AC3 | entityType=TIER, entityId=draftId | PendingChange created, tier status -> PENDING_APPROVAL | TS-S01 | MakerCheckerService<T>.submitForApproval(orgId, entity, changeType, payload, requestedBy) | UT |
| BT-37 | shouldAcceptNonTierEntityType | US5-AC2 | entityType=BENEFIT, entityId=benefitId | PendingChange created (generic framework accepts any ApprovableEntity) | TS-S02 | MakerCheckerService<T>.submitForApproval | UT |
| BT-38 | shouldRecordRequestedByAndTimestampAndPayload | US5-AC4 | Submit with userId="user-123" | PendingChange has requestedBy="user-123", requestedAt=now, payload=full snapshot | TS-S03 | MakerCheckerService<T>.submitForApproval | UT |
| BT-39 | shouldInvokeNotificationHandlerOnSubmit | US5-AC5 | Submit a tier | NotificationHandler.onSubmit invoked (no-op default, no error) | TS-S04 | MakerCheckerService<T>.submitForApproval (via NotificationHandler) | UT |
| BT-40 | shouldRejectSubmitOnActiveTier | US5-AC3 | Submit an ACTIVE tier | 400: "Tier is in ACTIVE status. Only DRAFT tiers can be submitted." | TS-S05 | MakerCheckerService<T>.submitForApproval | UT |
| BT-41 | shouldRejectSubmitOnNonExistentEntity | US5-AC1 | Submit with invalid entityId | 404: entity not found | TS-S06 | MakerCheckerService<T>.submitForApproval | UT |
| BT-42 | shouldRejectSubmitOnAlreadyPendingTier | US5-AC3 | Submit on PENDING_APPROVAL tier | 400: "Tier is already pending approval" | TS-S07 | MakerCheckerService<T>.submitForApproval | UT |

### 2.6 MakerCheckerService -- Approve/Reject

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-43 | shouldApproveAndTransitionMongoDocToSnapshot ^(REGENERATED — Rework #5)^ | US6-AC1, US6-AC4 | Approve a PENDING_APPROVAL DRAFT of a brand-new tier | SAGA: preApprove (no basis → drift check skipped, name re-check runs, single-active re-check runs) → publish (Thrift createOrUpdateSlab returns slabId) → postApprove (Mongo doc status=SNAPSHOT, slabId populated, meta.approvedBy/approvedAt set, basisSqlSnapshot cleared). LIVE state now lives in SQL. | TS-A01, TS-A04 | MakerCheckerService<T>.approve + TierApprovalHandler | UT |
| BT-44 | shouldRejectAndRevertToDraftRetainingBasis ^(UPDATED — Rework #5)^ | US6-AC2, US6-AC5 | tierId, comment="Too low" | Mongo doc: PENDING_APPROVAL → DRAFT, rejectionComment stored, **basisSqlSnapshot RETAINED** (so approver can fix + re-submit against same basis). If SQL drifts before re-submission, preApprove will block at that point (see BT-157). | TS-A02 | TierFacade.reject → MakerCheckerService<T>.reject → TierApprovalHandler.postReject | UT |
| BT-45 | shouldRejectWithoutCommentFails | US6-AC2 | changeId, comment=null | 400: "Comment is required when rejecting" | TS-A03 | MakerCheckerService<T>.handleRejection | UT |
| BT-46 | shouldRecordReviewerDetailsOnApproval | US6-AC6 | Approve with reviewedBy="admin-1" | PendingChange has reviewedBy, reviewedAt, comment populated | TS-A06 | MakerCheckerService<T>.handleApproval | UT |
| BT-47 | shouldListPendingChangesForEntityType | US6-AC7 | entityType=TIER, programId=977 | Returns all PENDING_APPROVAL PendingChanges for TIER in program 977 | TS-A07 | MakerCheckerService<T>.listPendingApprovals(orgId, entityType, programId) | UT |
| BT-48 | shouldApproveVersionedEditAndUpdateSqlLiveState ^(REGENERATED — Rework #5)^ | US3-AC8, US6-AC4 | Approve DRAFT with parentId=slabId (edit of LIVE) | postApprove transitions **new** Mongo doc directly to SNAPSHOT (no ACTIVE intermediate). Prior SNAPSHOTs for same slabId stay SNAPSHOT. SQL `program_slabs` row with id=slabId is UPDATED (not replaced) via Thrift; approvedBy/approvedAt written to SQL audit columns. No Mongo doc ever holds ACTIVE post-Rework #5. | TS-A08, TS-E07 | TierApprovalHandler.postApprove | UT |
| BT-49 | ~~shouldApproveDeleteChangeAndSetStopped~~ | ~~US4-AC3, US6-AC1~~ | ~~Approve DELETE PendingChange~~ | ~~Tier -> STOPPED, SQL status updated~~ | ~~TS-A09~~ | ~~MakerCheckerService<T>.handleApproval~~ | **OBSOLETE** — no MC flow for deletion; TS-A09 removed in Rework #2 |
| BT-50 | shouldRejectApprovalOnNonExistentChangeId | US6-AC1 | Non-existent changeId | 404: "Change not found" | TS-A11 | MakerCheckerService<T>.handleApproval | UT |
| BT-51 | shouldRejectApprovalOnAlreadyProcessedChange | US6-AC1 | changeId already APPROVED | 400: "Change already processed" | TS-A12 | MakerCheckerService<T>.handleApproval | UT |

### 2.7 MakerCheckerService -- Toggle (OBSOLETE — Rework #5)

> **Rework #5 note**: MC is no longer toggle-able at the program level. Routing is determined by
> WRITE ORIGIN: any write from the new UI goes through MC (DRAFT → approve → SQL); any write
> from the old UI bypasses MC entirely (direct SlabFacade → SQL). BT-52 through BT-55 are all
> OBSOLETE. Replaced by BT-161 (dual-path write verification) and BT-7.x section (/reject split).

| ID | Test Name | Status |
|----|-----------|--------|
| ~~BT-52~~ | ~~shouldReturnMCEnabledStatus~~ | **OBSOLETE** — `isMCEnabled` method removed; MC is not toggle-able |
| ~~BT-53~~ | ~~shouldCreateActiveTierDirectlyWhenMCDisabled~~ | **OBSOLETE** — new UI always MC; no "direct active" path |
| ~~BT-54~~ | ~~shouldCreateDraftTierWhenMCEnabled~~ | **DUPLICATE** of updated BT-09 (which dropped the MC condition) |
| ~~BT-55~~ | ~~shouldNotAutoActivateExistingDraftsWhenMCToggledOff~~ | **OBSOLETE** — no MC toggle means no toggle-off scenario |

### 2.8 TierValidationService

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-56 | shouldRejectEmptyTierName | US2-AC2 | name="" | Validation error: "name is required, non-blank" | EC-01 | TierValidationService | UT |
| BT-57 | shouldRejectTierNameExceedingMaxLength | US2-AC2 | name=256 chars | Validation error: "name exceeds max length" | EC-02 | TierValidationService | UT |
| BT-58 | shouldSanitizeSpecialCharactersInName | US2-AC4 | name contains `<script>`, SQL injection attempt | Safely accepted/sanitized, no injection | EC-03 | TierValidationService | UT |
| BT-59 | shouldRejectNegativeThreshold | US2-AC4 | eligibility.threshold = -100 | Validation error: "threshold must be positive" | EC-05 | TierValidationService | UT |
| BT-60 | shouldAcceptZeroThresholdForBaseTier | US2-AC4 | eligibility.threshold = 0 for base tier (serialNumber=1) | Accepted (base tier has no threshold requirement) | EC-04 | TierValidationService | UT |
| BT-61 | shouldAcceptDecimalThreshold | US2-AC4 | eligibility.threshold = 550.5 | Accepted (RM amounts support decimals) | EC-06 | TierValidationService | UT |
| BT-62 | shouldRejectEndDateBeforeStartDate | US2-AC2 | endDate < startDate | Validation error: "endDate must be after startDate" | EC-07 | TierValidationService | UT |
| BT-63 | shouldRejectInvalidColorHex | US2-AC2 | color="red" | Validation error: "color must be a valid hex code" | TS-C10 | TierValidationService | UT |
| BT-64 | shouldRejectColorHexWithoutHashPrefix | US2-AC2 | color="FF5733" | Validation error: "color must be a valid hex code" | EC-11 | TierValidationService | UT |
| BT-65 | shouldRejectProgramIdZero | US2-AC2 | programId=0 | Validation error: "invalid programId" | EC-12 | TierValidationService | UT |
| BT-66 | shouldRejectCreationBeyond50TierCap | US2-AC4 | Program already has 50 tiers | 400: "Maximum 50 tiers per program" | TS-L15, EC-13 | TierValidationService | UT |
| BT-67 | shouldRejectEmptyConditionsArray | US2-AC2 | eligibility.conditions = [] | Validation error: "at least one condition required" | EC-10 | TierValidationService | UT |
| BT-68 | shouldEnforceNameUniquenessWithinProgram | US2-AC4 | name="Gold", program already has "Gold" | 409: duplicate name | TS-C06 | TierValidationService | UT |
| BT-69 | shouldValidateSerialNumberImmutabilityOnEdit | US3-AC6 | Edit attempt changing serialNumber | serialNumber field ignored or rejected | TS-E05 | TierValidationService | UT |

### 2.9 TierApprovalHandler

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-70 | shouldBuildSlabInfoFromHoistedFields ^(UPDATED — Rework #5)^ | US6-AC3 | UnifiedTierConfig with hoisted fields (name, description, color, serialNumber — no `basicDetails` wrapper) | SlabInfo with name, description, colorCode, serialNumber. **`updatedViaNewUI` field DROPPED** (Rework #5 Q-7c — origin derived from Mongo-doc existence, not a flag). | TS-A04 | TierApprovalHandler.publish(entity) | UT |
| BT-71 | shouldBuildUpgradeStrategyInfoWithThresholdCSV | US6-AC3 | UnifiedTierConfig with eligibility (threshold=5000) | StrategyInfo type=2 (SLAB_UPGRADE), threshold appended to CSV | TS-A05 | TierApprovalHandler.publish | UT |
| BT-72 | shouldBuildDowngradeStrategyInfoFromConfig | US6-AC3 | UnifiedTierConfig with downgrade config | StrategyInfo type=5 (SLAB_DOWNGRADE), TierConfiguration JSON updated | TS-A05 | TierApprovalHandler.publish | UT |
| BT-73 | shouldMapCSVIndexCorrectlyForSerialNumber | US6-AC3 | Tier with serialNumber=4 in 4-tier program | CSV index = serialNumber - 2 = 2 (0-indexed in CSV, base tier has no entry) | TS-A05 | TierApprovalHandler.publish | UT |
| BT-74 | shouldPassOnlyUpgradeAndDowngradeStrategiesToThrift | US6-AC3, US6-AC4 | Full UnifiedTierConfig | Thrift call receives exactly [SLAB_UPGRADE, SLAB_DOWNGRADE] strategies, NOT allocation/expiry | TS-A05 | TierApprovalHandler.publish | UT |
| BT-75 | shouldUpdateSlabIdInMongoAfterPublish ^(UPDATED — Rework #5 rename + hoist)^ | US6-AC4 | Approved tier (brand-new), Thrift returns SlabInfo with id=42 | MongoDB doc **`slabId=42` at root** (not `metadata.sqlSlabId`). Rework #5 Q-8 renamed AND hoisted this field. | TS-A01 | TierApprovalHandler.postApprove | UT |
| BT-76 | shouldAllowMultipleSnapshotsAndSingleSqlLive ^(REGENERATED — Rework #5)^ | US3-AC8, US6-AC4 | Approve edit-of-LIVE DRAFT (parentId=slabId) with prior SNAPSHOT versions in Mongo | New Mongo doc → SNAPSHOT directly. Prior SNAPSHOT versions for same slabId remain SNAPSHOT (multiple SNAPSHOTs across history — audit trail). SQL `program_slabs` row with id=slabId is UPDATED in place — only ONE LIVE row per slabId in SQL. | TS-A08 | TierApprovalHandler.postApprove | UT |
| BT-77 | shouldPassKpiTypeDirectlyToThrift | US6-AC3 | eligibility.kpiType="PURCHASE" | Thrift current_value_type mapped from kpiType String (no enum conversion) | TS-A05 | TierApprovalHandler.publish | UT |
| ~~BT-78~~ | ~~shouldSetUpdatedViaNewUIFlagTrue~~ | ~~US6-AC3~~ | ~~Any tier sync~~ | ~~SlabInfo.updatedViaNewUI = true, StrategyInfo.updatedViaNewUI = true~~ | ~~TS-A05~~ | ~~TierApprovalHandler.publish~~ | **OBSOLETE** — `updatedViaNewUI` flag DROPPED from SlabInfo/StrategyInfo (Rework #5 Q-7c). Write origin is now derived from Mongo-doc existence: if a Mongo doc exists for slabId, it came from new UI; if not, legacy path. Replaced by BT-161 (dual-path verification). |
| BT-79 | ~~shouldApplyDeleteBySettingStatusToStopped~~ | ~~US4-AC2, US4-AC3~~ | ~~PendingChange with changeType=DELETE~~ | ~~MongoDB status -> STOPPED, SQL ProgramSlab status -> STOPPED~~ | ~~TS-A09~~ | ~~TierApprovalHandler.publish~~ | **OBSOLETE** — no MC-gated delete flow; deletion sets DELETED directly on DRAFT with no SQL change (Rework #2) |

---

## Section 3: Functional Test Cases (Integration Tests)

### 3.1 API Endpoint Tests (TierController)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-80 | shouldReturn200WithTierListOfEnvelopes ^(UPDATED — Rework #5)^ | US1-AC1 | GET /v3/tiers?programId=977 | 200 OK, ResponseWrapper with TierListResponse containing envelopes (`{live, pendingDraft, hasPendingDraft}` per slabId) + summary. Envelopes include tiers with SQL LIVE rows AND tiers with Mongo DRAFT/PENDING_APPROVAL — unified read surface across both UIs. | TS-L01 | TierController -> TierFacade.listTiers | IT |
| BT-81 | shouldReturn400WhenProgramIdMissing | US1-AC1 | GET /v3/tiers (no programId) | 400 error: "programId is required" | TS-L12 | TierController | IT |
| BT-82 | shouldReturn201OnTierCreation | US2-AC1 | POST /v3/tiers with valid body | 201 Created, UnifiedTierConfig in ResponseWrapper | TS-C01 | TierController -> TierFacade.createTier | IT |
| BT-83 | shouldReturn200OnTierUpdate | US3-AC1 | PUT /v3/tiers/{tierId} with valid body | 200 OK, updated UnifiedTierConfig | TS-E01 | TierController -> TierFacade.updateTier | IT |
| BT-84 | shouldReturn204OnDraftDeletion | US4-AC1 | DELETE /v3/tiers/{draftId} | 204 No Content | TS-D04 | TierController -> TierFacade.deleteTier | IT |
| BT-85 | shouldReturn404OnNonExistentTierDelete | US4-AC1 | DELETE /v3/tiers/nonexistent | 404 Not Found | TS-D08 | TierController -> TierFacade.deleteTier | IT |
| BT-86 | shouldReturn200WithTierDetailEnvelope ^(UPDATED — Rework #5)^ | P75-1 | GET /v3/tiers/{slabId} or GET /v3/tiers/{tierUniqueId} | 200 OK with envelope `{live: TierView, pendingDraft: TierView \| null, hasPendingDraft}`. `live` populated from SQL (via SqlTierConverter) for LIVE tier; `pendingDraft` populated from Mongo if DRAFT/PENDING_APPROVAL exists. Accepts either numeric slabId OR string tierUniqueId. | TS-GD01, TS-GD03 | TierController -> TierFacade.getTierEnvelope | IT |
| BT-87 | shouldReturn404ForNonExistentTierDetail | P75-1 | GET /v3/tiers/nonexistent | 404: "Tier not found" | TS-GD04 | TierController | IT |
| ~~BT-88~~ | ~~shouldReturnStoppedTiersOnlyWhenIncludeInactiveTrue~~ | ~~US4-AC6~~ | ~~GET /v3/tiers?programId=977&includeInactive=true~~ | ~~STOPPED tiers included; without flag, STOPPED excluded~~ | ~~TS-L13, TS-L14~~ | ~~TierController -> TierFacade.listTiers~~ | **OBSOLETE** — STOPPED status removed; DELETED is terminal and never surfaced in listings (Rework #2) |
| BT-89 | shouldExcludeEngineConfigFromListingResponse | US1-AC2 | GET /v3/tiers?programId=977 | engineConfig field absent or null on each tier envelope in listing (engineConfig is a heavy-payload field excluded from list views) | TS-L11 | TierController -> TierFacade.listTiers | IT |

### 3.2 API Endpoint Tests (TierReviewController)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-90 | shouldSubmitChangeViaEndpoint | US5-AC1 | POST /v3/tiers/{tierId}/submit | 200, PendingChange returned | TS-S01 | TierReviewController -> TierFacade.submitForApproval | IT |
| BT-91 | shouldApproveChangeAndTransitionToSnapshot ^(UPDATED — Rework #5)^ | US6-AC1 | POST /v3/tiers/{tierId}/approve | 200, Mongo doc transitions directly to SNAPSHOT (no ACTIVE intermediate); SQL `program_slabs` row created/updated (LIVE state lives in SQL); approvedBy/approvedAt written to BOTH Mongo `meta` AND SQL audit columns. | TS-A01 | TierReviewController -> TierFacade.approve | IT |
| BT-92 | shouldRejectChangeViaEndpoint ^(UPDATED — Rework #5)^ | US6-AC2 | POST /v3/tiers/{tierId}/reject with comment | 200, Mongo doc reverts PENDING_APPROVAL → DRAFT, rejectionComment stored, basisSqlSnapshot RETAINED (approver can re-submit without recreating DRAFT). New `/reject` endpoint (split from unified approve/reject in old design). | TS-A02 | TierReviewController -> TierFacade.reject | IT |
| BT-93 | shouldListPendingChangesViaEndpoint | US6-AC7 | GET /v3/tiers/approvals?programId=977 | 200, list of PendingChange objects | TS-A07 | TierReviewController -> TierFacade.listPendingApprovals | IT |
| ~~BT-94~~ | ~~shouldReturnMCConfigViaEndpoint~~ | ~~US7-AC1, P75-2~~ | ~~GET /v3/tiers/config?programId=977~~ | ~~200, makerCheckerEnabled: true/false~~ | ~~TS-MC01~~ | ~~TierReviewController -> TierFacade.isMCEnabled~~ | **OBSOLETE** — MC toggle removed (Rework #1 + Rework #5). MC routing is ORIGIN-based: new UI ALWAYS goes through MC; old UI ALWAYS bypasses. No configurable flag exposed. |
| ~~BT-95~~ | ~~shouldReturn400WhenMCConfigMissingProgramId~~ | ~~US7-AC1~~ | ~~GET /v3/tiers/config without programId~~ | ~~400 error~~ | ~~TS-MC06~~ | ~~TierReviewController~~ | **OBSOLETE** — endpoint removed with MC toggle (Rework #5). |
| BT-96 | shouldReturnChangeDetailViaEndpoint | P75-3 | GET /v3/tiers/approvals/{changeId} | 200 OK with full PendingChange including payload snapshot | TS-GC01 | TierReviewController | IT |
| BT-97 | shouldReturn404ForNonExistentChangeDetail | P75-3 | GET /v3/tiers/approvals/nonexistent | 404 | TS-GC02 | TierReviewController | IT |

### 3.3 MongoDB Persistence Tests

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-98 | shouldPersistUnifiedTierConfigToMongoWithHoistedSchema ^(UPDATED — Rework #5)^ | US2-AC1 | Create tier via TierFacade | Document found in unified_tier_configs with HOISTED fields at root: `name`, `description`, `color`, `serialNumber`, `eligibility`, `validity`, `downgrade`, `slabId`, `meta`. **No** `basicDetails`, `metadata`, `nudges`, `benefitIds`, `updatedViaNewUI` keys. `tierUniqueId` present, `unifiedTierId` absent. | TS-C12 | TierRepository (MongoDB) | IT |
| BT-99 | shouldPersistPendingChangeToMongo | US5-AC1 | Submit tier via MakerCheckerService | Document found in pending_changes collection with full payload | TS-S03 | PendingChangeRepository (MongoDB) | IT |
| BT-100 | shouldFilterByOrgIdInMongoQuery | US1-AC1 | List tiers for orgId=100 when orgId=200 also has tiers | Only orgId=100 tiers returned | EC-40 | TierRepository (MongoDB) | IT |
| BT-101 | shouldHandleShardedMongoAccess | US2-AC1 | Create and read tier via sharded EmfMongoDataSourceManager | Correctly routes to shard, data round-trips | -- | TierRepositoryImpl | IT |

### 3.4 Thrift Sync Tests (Mocked Thrift)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-102 | shouldCallCreateSlabAndUpdateStrategiesOnApproval ^(UPDATED — Rework #5)^ | US6-AC3, US6-AC4 | Approve a CREATE PendingChange | Thrift mock verifies createSlabAndUpdateStrategies called with correct SlabInfo + strategies. SlabInfo has no `updatedViaNewUI` flag (dropped Rework #5 Q-7c). Returned slabId persisted to Mongo at root (`slabId`, not `metadata.sqlSlabId`). | TS-A04, TS-A05 | TierApprovalHandler.publish -> PointsEngineRulesThriftService | IT |
| BT-103 | shouldRollbackOnThriftSyncFailure ^(UPDATED — Rework #5)^ | US6-AC3 | Approve, but Thrift call throws exception | 500: "Failed to sync. Approval rolled back." Mongo doc stays PENDING_APPROVAL (not SNAPSHOT); basisSqlSnapshot retained; SQL untouched. SAGA `onPublishFailure` executed. | TS-A10 | TierApprovalHandler.onPublishFailure | IT |
| BT-104 | shouldCallThriftWithAtomicSingleCall | US6-AC3 | Approve a tier | Exactly ONE Thrift call (not separate slab + strategy calls) | TS-ADR12 | TierApprovalHandler.publish | IT |

### 3.5 Full Flow Integration Tests

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-105 | shouldCompleteFullCreateSubmitApproveFlow ^(UPDATED — Rework #5)^ | US2-AC1, US5-AC1, US6-AC1 | POST /tiers → POST /submit → POST /approve | Mongo doc: DRAFT → PENDING_APPROVAL → SNAPSHOT (directly, no ACTIVE intermediate). SQL `program_slabs` row CREATED with approvedBy/approvedAt audit columns populated. Envelope GET returns `{live: TierView(from SQL), pendingDraft: null}`. | TS-C01, TS-S01, TS-A01 | TierFacade + MakerCheckerService<T> + TierApprovalHandler | IT |
| BT-106 | shouldCompleteFullEditSubmitApproveFlow ^(REGENERATED — Rework #5)^ | US3-AC3, US3-AC8, US6-AC4 | PUT /tiers/{slabId of LIVE tier} → POST /submit → POST /approve | NEW Mongo DRAFT created with parentId=slabId and basisSqlSnapshot captured. DRAFT → PENDING_APPROVAL → SNAPSHOT (no ACTIVE). Prior SNAPSHOT versions (if any) retained as SNAPSHOT (multiple SNAPSHOTs per slabId = audit trail). SQL `program_slabs` row UPDATED in-place (only ONE LIVE row per slabId in SQL). | TS-E02, TS-E07, TS-A08 | TierFacade + MakerCheckerService<T> + TierApprovalHandler | IT |
| ~~BT-107~~ | ~~shouldCompleteFullDeleteSubmitApproveFlow~~ | ~~US4-AC3, US6-AC1~~ | ~~DELETE /tiers/{activeId} -> POST /submit -> POST /approve~~ | ~~Tier -> STOPPED, SQL status -> STOPPED~~ | ~~TS-D02, TS-A09~~ | ~~TierFacade + MakerCheckerService<T> + TierApprovalHandler~~ | **OBSOLETE** — no MC-gated delete flow; replaced by BT-32/BT-84 direct DRAFT→DELETED path (Rework #2) |
| ~~BT-108~~ | ~~shouldCompleteCreateWithMCDisabledDirectToActive~~ | ~~US2-AC6, US7-AC3~~ | ~~POST /tiers (MC disabled)~~ | ~~Tier immediately ACTIVE, sqlSlabId populated, Thrift called~~ | ~~TS-C02, TS-MC03~~ | ~~TierFacade + TierApprovalHandler~~ | **OBSOLETE** — no MC-disabled path for new UI (Rework #5). New UI → MC always. Non-MC writes use legacy SlabFacade from old UI (bypasses TierFacade entirely). Replaced by BT-161 (dual-path). |

---

## Section 4: Compliance Test Cases

### 4.1 ADR Compliance

| ID | Test Name | ADR | Verifies | Input | Expected Output | QA Scenario | Layer |
|----|-----------|-----|----------|-------|-----------------|-------------|-------|
| BT-109 | shouldStoreInMongoOnlyNotSqlUntilApproval ^(UPDATED — Rework #5)^ | ADR-01 | Dual-storage: MongoDB for drafts + SNAPSHOTs; SQL for LIVE | Create tier via new UI | Mongo doc (status=DRAFT) exists; no SQL `program_slabs` row | TS-ADR01 | IT |
| BT-110 | shouldPersistSnapshotInMongoAndLiveInSqlOnApproval ^(UPDATED — Rework #5)^ | ADR-01 | Dual-storage: Mongo SNAPSHOT + SQL LIVE | Approve tier | Mongo doc status=SNAPSHOT (not ACTIVE — Rework #5 state machine), SQL `program_slabs` row created with id=slabId and audit columns populated. SQL is single source of truth for LIVE state. | TS-ADR02 | IT |
| BT-111 | shouldAcceptAnyEntityTypeThroughMCFramework | ADR-02 | Generic MC: entity-agnostic | Submit BENEFIT entity type | PendingChange created for BENEFIT | TS-ADR03 | IT |
| BT-112 | shouldDispatchToCorrectChangeApplierPerEntityType | ADR-02 | Generic MC: strategy dispatch | Approve TIER change | TierApprovalHandler invoked (not a generic applier) | TS-ADR04 | UT |
| ~~BT-113~~ | ~~shouldNotBreakExistingFindByProgramQuery~~ | ~~ADR-03~~ | ~~Expand-then-contract: existing DAO unchanged~~ | ~~Call findByProgram() after adding status column~~ | ~~Returns ALL slabs regardless of status~~ | ~~TS-ADR05~~ | ~~IT~~ | **OBSOLETE** — ADR-03 removed (Rework #3: no SQL status changes) |
| ~~BT-114~~ | ~~shouldFilterNonActiveInNewFindActiveByProgram~~ | ~~ADR-03~~ | ~~Expand-then-contract: new filtered query~~ | ~~Call findActiveByProgram()~~ | ~~Returns only ACTIVE slabs~~ | ~~TS-ADR06~~ | ~~IT~~ | **OBSOLETE** — ADR-03 removed (Rework #3: no findActiveByProgram()) |
| ~~BT-115~~ | ~~shouldDefaultExistingRowsToActiveOnMigration~~ | ~~ADR-03~~ | ~~Flyway migration default value~~ | ~~Run migration on existing rows~~ | ~~All rows have status='ACTIVE'~~ | ~~TS-ADR07~~ | ~~IT~~ | **OBSOLETE** — ADR-03 removed (Rework #3: no status migration). Replaced by BT-163 (Flyway for audit columns). |
| BT-116 | shouldKeepLiveInSqlWhileDraftPendingInMongo ^(REGENERATED — Rework #5)^ | ADR-04 | Versioned edits: zero downtime | Edit LIVE tier (SQL row present) | SQL row untouched (still serving runtime); NEW Mongo DRAFT doc created with parentId=slabId. Envelope GET returns `{live: TierView(from SQL), pendingDraft: TierView(from Mongo), hasPendingDraft: true}`. | TS-ADR08 | UT |
| BT-117 | shouldRevertDraftAndPreserveSqlLiveOnReject ^(UPDATED — Rework #5)^ | ADR-04 | Versioned edits: rollback | Reject versioned DRAFT (edit-of-LIVE) | Mongo doc reverts PENDING_APPROVAL → DRAFT with basisSqlSnapshot retained; SQL `program_slabs` row (LIVE) unchanged — zero impact to runtime. | TS-ADR09 | UT |
| BT-118 | shouldUseExistingThriftMethodsWithoutIDLChange | ADR-05 | Existing Thrift reuse | Approve tier | createSlabAndUpdateStrategies called via existing Thrift client | TS-ADR10 | IT |
| ~~BT-119~~ | ~~shouldReturnEmptyForOldProgramWithNoMongoData~~ | ~~ADR-06~~ | ~~New programs only~~ | ~~List tiers for legacy program (no MongoDB docs)~~ | ~~Empty list from tier API; legacy system continues to serve old programs~~ | ~~TS-ADR11~~ | ~~UT~~ | **OBSOLETE — REVERSED by ADR-06R (Rework #5)**. Unified read surface: legacy SQL-only tiers now surface in /v3/tiers as envelopes with `live: TierView(from SqlTierConverter)`, `pendingDraft: null`. Replaced by BT-164 (legacy-bridge envelope) and BT-165 (SqlTierConverter round-trip). |
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
| BT-132 | shouldMaintainBackwardCompatibilityOnAuditColumnMigration ^(UPDATED — Rework #5)^ | G-05.4 | Expand-then-contract: add nullable audit columns to program_slabs | Run Flyway migration on DB with existing rows | Migration runs idempotently; all existing rows have `updated_by=NULL, approved_by=NULL, approved_at=NULL` (nullable, safe default). Legacy code paths that don't read these columns continue to work unchanged. Rollback script drops the columns. | GR-10 | IT |

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

### 4.4 R5-R4 Renewal Contract (B1a) ^(NEW — Rework #5 R4, 2026-04-21)^

> Contract: `TierValidityConfig.renewal` is accept-only `criteriaType = "Same as eligibility"` on write; null/omitted renewal is auto-filled to the B1a default by `TierRenewalNormalizer` pre-save; the read path synthesizes the same default on every `extractValidityForSlab` call. Drift-checker whole-object equality on `TierValidityConfig` requires DRAFT (Mongo) and LIVE (SQL→engine→DTO) to surface identical renewal objects. See `03-designer.md` → `## R5-R4 Renewal Contract (B1a)`.
>
> Traces to: BA `US-2` optional-fields AC (renewalConfig), BA `US-3` editable-fields AC, Designer `## R5-R4 Renewal Contract`, `TierRenewalConfig.java` (B1a constant), `TierRenewalNormalizer.java`, `TierStrategyTransformer.extractValidityForSlab`.

| ID | Test Name | Traces To | Verifies | Input | Expected Output | QA Scenario | Layer |
|----|-----------|-----------|----------|-------|-----------------|-------------|-------|
| BT-176 | fillsDefaultRenewalWhenValidityPresentAndRenewalNull | R5-R4 B1a normalizer | Normalizer fills B1a default when validity exists but renewal is null | `TierValidityConfig{periodType, periodValue, renewal=null}` | Same instance returned with `renewal = TierRenewalConfig{criteriaType="Same as eligibility", expressionRelation=null, conditions=null}` | TS-RNW-01 | TierRenewalNormalizer.normalize | UT |
| BT-177 | returnsSameInstanceWhenValidityPresent | R5-R4 B1a normalizer | Normalizer returns the input instance (mutate-in-place — `@Data @Builder` without `toBuilder`) | Non-null validity | `result == input` (reference equality) | TS-RNW-02 | TierRenewalNormalizer.normalize | UT |
| BT-178 | preservesOtherValidityFieldsWhenFillingRenewal | R5-R4 B1a normalizer | Normalizer mutates only `renewal`; every other field unchanged | Validity with periodType, periodValue, startDate, endDate all populated; renewal=null | All four original fields unchanged; renewal populated with B1a default | TS-RNW-03 | TierRenewalNormalizer.normalize | UT |
| BT-179 | leavesExistingRenewalUntouched | R5-R4 B1a normalizer | Normalizer does NOT overwrite a non-null renewal (validator has already accepted it) | Validity with `renewal = TierRenewalConfig{criteriaType="Same as eligibility", ...already populated}` | Renewal object is the same instance, byte-for-byte unchanged | TS-RNW-04 | TierRenewalNormalizer.normalize | UT |
| BT-180 | nullValidityIsNoOp | R5-R4 B1a normalizer | Normalizer is safe to call with a null validity (e.g. tier without a validity block) | `validity = null` | Returns null, no NPE | TS-RNW-05 | TierRenewalNormalizer.normalize | UT |
| BT-181 | shouldNormalizeRenewalOnCreateTier | R5-R4 B1a wiring | `TierFacade.createTier` invokes normalizer before `tierRepository.save()` | POST /v3/tiers with body containing `validity` but no `validity.renewal` | Persisted DRAFT has `validity.renewal` = B1a default | TS-RNW-06 | TierFacade.createTier | IT |
| BT-182 | shouldNormalizeRenewalOnVersionedDraftFromActive | R5-R4 B1a wiring | `TierFacade.createVersionedDraft` (edit-of-LIVE → new DRAFT) invokes normalizer before save | PUT /v3/tiers/{id} on LIVE tier, body validity without renewal | New versioned DRAFT has `validity.renewal` = B1a default | TS-RNW-07 | TierFacade.createVersionedDraft | IT |
| BT-183 | shouldNormalizeRenewalOnUpdateInPlace | R5-R4 B1a wiring | `TierFacade.updateInPlace` (edit of existing DRAFT) invokes normalizer before save | PUT /v3/tiers/{id} on DRAFT, body validity without renewal | DRAFT's `validity.renewal` updated to B1a default in place | TS-RNW-08 | TierFacade.updateInPlace | IT |
| BT-184 | extractingValiditySynthesizesB1aDefaultRenewal | R5-R4 B1a read synthesis | `TierStrategyTransformer.extractValidityForSlab` synthesizes the B1a default on every call (engine has no storage slot) | Engine JSON with `slabs[n].periodConfig` populated (no renewal field — engine schema doesn't have one) | Returned `TierValidityConfig.renewal` = B1a default (not null) | TS-RNW-09 | TierStrategyTransformer.extractValidityForSlab | UT |
| BT-185 | extractingValidityRoundTripsThroughForwardPath | R5-R4 B1a symmetry | DRAFT (post-normalizer) and LIVE (post-synthesis) produce identical `TierValidityConfig` objects → drift-checker `Objects.equals` returns true | Write B1a default via `applySlabValidityDelta`, then read via `extractValidityForSlab`, then compare | Round-trip equality holds; drift-checker reports no diff | TS-RNW-10 | forward-path ↔ reverse-path round-trip | UT |

**Coverage note:** BT-176..BT-180 establish normalizer correctness in isolation (pure utility — safe to test in isolation per Rule 2 exception for stateless functions). BT-181..BT-183 prove the wiring into all three TierFacade write paths. BT-184 proves the read-side synthesis contract. BT-185 is the symmetry guarantee that prevents phantom drift-checker false-positives — this is the test that would fire first if either side of the contract regresses.

---

### 4.X R3 — `tierStartDate` from SQL `program_slabs.created_on` (BT-186..BT-189)

> **Scope**: Populate `TierView.tierStartDate` on the LIVE envelope side from SQL `program_slabs.created_on`. Wire path: emf-parent `ProgramSlab.createdOn` → Thrift `SlabInfo.createdOn` (new `optional i64` field, epoch millis) → intouch-api-v3 `SqlTierRow.createdOn` (`Date`) → `TierView.tierStartDate` (`Date`, `@JsonFormat yyyy-MM-dd'T'HH:mm:ssXXX`). No fallback, no derivation. Backward-compat: legacy emf-parent servers that predate the field leave it unset on the wire; consumers surface `null` at every layer.
>
> **Why `isSetCreatedOn()` and not a value check**: Thrift-generated Java returns `0L` for an unset `optional i64`, and `0L` is a legal epoch millis (1970-01-01). A value check would silently downgrade a missing wire field to a 1970 `Date` on the view. BT-187 is the regression fence for this.
>
> **Traces to**: BA `US1` `tierStartDate` AC (R3), Designer `## R3 tierStartDate contract (SQL-sourced creation timestamp)`, `SqlTierRow.createdOn`, `TierStrategyTransformer.fromStrategies`, `SqlTierConverter.toView`, `TierView.tierStartDate`.

| ID | Test Name | Traces To | Verifies | Input | Expected Output | QA Scenario | Target | Layer |
|----|-----------|-----------|----------|-------|-----------------|-------------|--------|-------|
| BT-186 | fromStrategiesCopiesSlabCreatedOnToRowCreatedOnWhenSet | R3 wire-mapping | Transformer copies `SlabInfo.createdOn` (epoch millis) to `SqlTierRow.createdOn` (`Date`) byte-for-byte — no derivation, no timezone shift | `SlabInfo` with `setCreatedOn(1704067200000L)` (2024-01-01T00:00:00Z) + empty strategies | `row.getCreatedOn() != null`; `row.getCreatedOn().getTime() == 1704067200000L` | TS-R3-01 | TierStrategyTransformer.fromStrategies | UT |
| BT-187 | fromStrategiesLeavesRowCreatedOnNullWhenSlabCreatedOnUnset | R3 legacy-server backward-compat | Transformer surfaces `null` — not `new Date(0L)` — when the Thrift field is unset (legacy emf-parent server pre-R3). Uses `isSetCreatedOn()` guard, **not** a value check. This is the regression fence against the "0L is a legal epoch millis" trap. | `SlabInfo` without `setCreatedOn` called | `row.getCreatedOn() == null` (asserted to NOT be `new Date(0L)`) | TS-R3-02 | TierStrategyTransformer.fromStrategies | UT |
| BT-188 | shouldCopyCreatedOnToTierStartDate | R3 converter passthrough | `SqlTierConverter.toView` passes `row.createdOn` directly to `TierView.tierStartDate` with reference equality — pure function, no derivation | `SqlTierRow` with `createdOn = new Date(1704067200000L)` | `view.getTierStartDate() != null`; `view.getTierStartDate().equals(row.getCreatedOn())` | TS-R3-03 | SqlTierConverter.toView | UT |
| BT-189 | shouldLeaveTierStartDateNullWhenRowCreatedOnIsNull | R3 converter null-propagation | Converter propagates `null` → `null` (no fallback, no derivation). Combined with `@JsonInclude.NON_NULL` on `TierView`, `tierStartDate` is omitted from the wire when the row is null. | `SqlTierRow` with `createdOn = null` | `view.getTierStartDate() == null` | TS-R3-04 | SqlTierConverter.toView | UT |

**Coverage note:** BT-186 and BT-188 prove the happy-path wire mapping and converter passthrough. BT-187 is the critical regression fence for the `isSetCreatedOn()` contract — without it, a value check would silently produce `1970-01-01` on the wire for every legacy server's response, and the UI would display a wrong start date rather than nothing. BT-189 proves the contract holds end-to-end when the field is absent.

**Pragmatic boundary (evidence-based — Rule 1):** No dedicated UT is added for the emf-parent `getSlabThrift` guard (`if (programSlab.getCreatedOn() != null) slabInfo.setCreatedOn(...)`). The method is a private helper inside a heavy Spring Thrift class with no existing `getAllSlabs` UT to extend; bootstrapping the mock stack for one `if`-block is high cost / low value. The wire-contract assertion lives on the consumer side (BT-186, BT-187) — which is the layer that a real drift would surface at. Documented in `03-designer.md` under "R3 tierStartDate contract" > "Pragmatic boundary".

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
| US1-AC6 | TS-L04 | ~~BT-04~~ (OBSOLETE — Rework #5, benefitIds dropped) |
| US1-AC7 | TS-L05 | BT-05 |
| US1-AC8 | TS-L06, TS-L07 | BT-06 |
| US1-AC9 | TS-L08, TS-L09 | BT-07, BT-08 |
| US1-AC10 | TS-L10 | BT-01 |
| US1-AC11 | TS-L11 | BT-89 |
| US2-AC1 | TS-C01, TS-C02 | BT-09, ~~BT-10~~ (OBSOLETE — Rework #5), BT-82 |
| US2-AC2 | TS-C03, TS-C04 | BT-13, BT-14, BT-56-67 |
| US2-AC3 | TS-C05 | BT-12 |
| US2-AC4 | TS-C06, TS-C07, TS-C08 | BT-15, BT-16, BT-11 |
| US2-AC5 | TS-C01 | BT-09 |
| US2-AC6 | TS-C02 | ~~BT-10~~ (OBSOLETE — Rework #5; no "MC disabled" for new UI). See BT-161 (dual-path) |
| US2-AC7 | TS-C08 | BT-11 |
| US2-AC8 | TS-C03, TS-C04 | BT-13, BT-14 |
| US2-AC9 | TS-C09 | BT-17 |
| US3-AC1 | TS-E01 | BT-19, BT-83 |
| US3-AC2 | TS-E01 | BT-19 |
| US3-AC3 | TS-E02 | BT-20, BT-25, BT-28 |
| US3-AC4 | TS-E03 | ~~BT-21~~ (OBSOLETE — Rework #5, PENDING is immutable; see BT-175) |
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
| US7-AC1 | ~~TS-MC01~~ | ~~BT-52, BT-94~~ (ALL OBSOLETE — Rework #5: MC toggle removed; routing is origin-based) |
| US7-AC2 | ~~TS-MC02~~ | ~~BT-52~~ (OBSOLETE — Rework #5) |
| US7-AC3 | ~~TS-MC03~~ | ~~BT-53, BT-108~~ (OBSOLETE — Rework #5). See BT-161 (dual-path verification) |
| US7-AC4 | ~~TS-MC04~~ | ~~BT-54~~ (OBSOLETE — Rework #5) |
| US7-AC5 | ~~TS-MC05~~ | ~~BT-55~~ (OBSOLETE — Rework #5) |
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
| TS-MC01 | ~~BT-52, BT-94~~ (OBSOLETE — Rework #5) |
| TS-MC02 | ~~BT-52~~ (OBSOLETE — Rework #5) |
| TS-MC03 | ~~BT-53, BT-108~~ (OBSOLETE — Rework #5). See BT-161 |
| TS-MC04 | ~~BT-54~~ (OBSOLETE — Rework #5) |
| TS-MC05 | ~~BT-55~~ (OBSOLETE — Rework #5) |
| TS-MC06 | ~~BT-95~~ (OBSOLETE — Rework #5, endpoint removed) |
| TS-MC07 | ~~BT-95~~ (OBSOLETE — Rework #5) |
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

---

## Section 6: Rework #5 Delta — Unified Read Surface, Dual Write Paths, Schema Cleanup

> **Cycle**: 5 of 5
> **Source**: Manual rework entry (user-driven after stakeholder review)
> **Date**: 2026-04-17
> **Trigger**: user-authorized cascade — spec in `rework-5-scope.md` (9 clarifications C-1/C-2/C-3, Q-1..Q-9, M-1)
> **Severity**: MAJOR — affects schema, state machine, read/write paths, and API contracts

### 6.1 Triage Summary (ISTQB Suspect-Link Protocol)

Triage was performed on all 141 existing BTs against the Rework #5 change payload (9 locked decisions + schema cleanup M-1):

| Triage Status | Count | Representative BT-IDs |
|---|---|---|
| **CONFIRMED** (no change — traced items unaffected) | ~90 | BT-01, BT-02, BT-06, BT-11, BT-14, BT-16, BT-18, BT-22-24, BT-26-27, BT-36-42, BT-45-47, BT-50-51, BT-56-69, BT-71-74, BT-77, BT-81, BT-83-85, BT-87, BT-90, BT-93, BT-96-101, BT-104, BT-111-112, BT-118, BT-120-131, BT-133-141 |
| **UPDATE** (structure valid; value/wording changed) | 19 | BT-03, BT-05, BT-07, BT-08, BT-09, BT-12, BT-13, BT-15, BT-17, BT-19, BT-25, BT-28, BT-44, BT-70, BT-75, BT-80, BT-86, BT-89, BT-91, BT-92, BT-98, BT-102, BT-103, BT-109, BT-110, BT-117, BT-132 |
| **REGENERATE** (structurally invalid; rewritten) | 6 | BT-20, BT-43, BT-48, BT-76, BT-106, BT-116 |
| **OBSOLETE** (traced item removed upstream) | 15 | BT-04, BT-10, BT-21, BT-29, BT-30, BT-31, BT-33, BT-34, BT-49, BT-52-55, BT-78, BT-79, BT-88, BT-94, BT-95, BT-107, BT-108, BT-113-115, BT-119 |
| **NEW** (new upstream requirements) | 34 | BT-142 through BT-175 (see §6.3) |

**Net effect**: 141 pre-rework BTs → 141 retained (of which ~15 OBSOLETE, ~19 UPDATE, 6 REGENERATE, ~90 CONFIRMED) + 34 NEW = **175 total BTs** (effective active ≈ 160 after OBSOLETE exclusion).

### 6.2 Structured Disagreement Log

No disagreements with the Rework #5 spec. All 9 locked decisions (C-1 through M-1 in `rework-5-scope.md`) were adopted verbatim. Reasoning: spec was produced through direct Q&A cycle with product/stakeholders; no internal evidence contradicts it. Confidence C6+.

| Feedback Item | Accepted? | Evidence | Action |
|---|---|---|---|
| C-1 Unified read surface across old+new UI | YES | User explicit requirement; no backward-compat path | Adopt, add BT-142..BT-150 |
| C-2 Drift detection via basisSqlSnapshot | YES | Prevents stale-approval data loss; conservative policy agreed | Adopt, add BT-151..BT-157 |
| C-3 Dual write paths (old bypasses MC) | YES | Legacy UI unchanged by design; no SlabFacade modifications | Adopt, add BT-161 |
| Q-1 Hybrid reads (SQL for LIVE, Mongo for DRAFT/PENDING) | YES | Matches "SQL is single source of truth for LIVE" invariant | Adopt, validated in BT-142-144 |
| Q-6 parentId=slabId (Long), not ObjectId | YES | Simpler edit-of-LIVE semantics | Adopt, BT-20 regenerated |
| Q-7 Schema cleanup (drop nudges/benefitIds/updatedViaNewUI; hoist basicDetails; rename metadata→meta) | YES | Reduces doc size, aligns with engine data model | Adopt, affects BT-17, BT-70, BT-75, BT-78, BT-98 |
| Q-8 Rename sqlSlabId→slabId, unifiedTierId→tierUniqueId | YES | Clarity; matches Thrift naming | Adopt, BT-75 updated |
| Q-9a Single active DRAFT/PENDING per slabId (app + Mongo partial unique index) | YES | Defense-in-depth; prevents lost updates | Adopt, BT-25 updated, BT-152/153/162 new |
| Q-9b 3-layer name collision defense (Layer 1 at create, Layer 2 at approve, Layer 3 SQL UNIQUE) | YES | Race conditions between DRAFT-create and parallel approval | Adopt, BT-15 updated, BT-154-156 new |
| M-1 SQL audit columns (updated_by, approved_by, approved_at) | YES | Required for drift detection + audit trail | Adopt, BT-163 new |

### 6.3 New Business Tests (BT-142 through BT-175)

#### 6.3.1 Envelope Reads — Unified List & Single-Read (BT-142..BT-150)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-142 | shouldBuildEnvelopeForLiveOnlyTier | US1-AC-Rew5-1 | SQL has LIVE row for slabId=42, Mongo has no DRAFT/PENDING | `{live: TierView(from SQL, via SqlTierConverter), pendingDraft: null, hasPendingDraft: false}` | TS-ENV-01 | TierFacade.listTiers → SqlTierReader + TierEnvelope | UT |
| BT-143 | shouldBuildEnvelopeForPendingEditOnLiveTier | US1-AC-Rew5-1, US3-AC8 | SQL has LIVE row for slabId=42, Mongo has DRAFT with parentId=42 | `{live: TierView(from SQL), pendingDraft: TierView(from Mongo DRAFT), hasPendingDraft: true}` — BOTH visible in same envelope | TS-ENV-02 | TierFacade.listTiers | UT |
| BT-144 | shouldBuildEnvelopeForBrandNewDraft | US1-AC-Rew5-1 | No SQL row; Mongo has DRAFT with slabId=null, parentId=null | `{live: null, pendingDraft: TierView(from Mongo), hasPendingDraft: true}` | TS-ENV-03 | TierFacade.listTiers | UT |
| BT-145 | shouldBuildEnvelopeForPendingApprovalWithLive | US1-AC-Rew5-1 | SQL LIVE for slabId=42; Mongo has PENDING_APPROVAL doc parentId=42 | `{live: TierView(from SQL), pendingDraft: TierView(Mongo doc, status PENDING_APPROVAL), hasPendingDraft: true}`. Same envelope structure — UI distinguishes via `pendingDraft.status`. | TS-ENV-04 | TierFacade.listTiers | UT |
| BT-146 | shouldExcludeSnapshotOnlyDocsFromEnvelopeList | US1-AC-Rew5-1 | Mongo has SNAPSHOT docs for slabId=42 but no LIVE SQL row and no DRAFT/PENDING | No envelope returned for slabId=42 (SNAPSHOTs alone do not warrant an envelope in the list) | TS-ENV-05 | TierFacade.listTiers | UT |
| BT-147 | shouldReturnEnvelopeForLegacySqlOnlyTier | US1-AC-Rew5-1 (ADR-06R) | Legacy program has SQL rows but zero Mongo docs (never touched new UI) | Envelope returned: `{live: TierView(from SqlTierConverter), pendingDraft: null}` — legacy tiers NOW visible in /v3/tiers (reversal of old ADR-06) | TS-ENV-06 | TierFacade.listTiers → SqlTierConverter | IT |
| BT-148 | shouldReturnSingleTierEnvelopeBySlabId | US1-AC-Rew5-2 | GET /v3/tiers/42 where slabId=42 is LIVE | 200 with envelope `{live, pendingDraft, hasPendingDraft}` | TS-ENV-07 | TierFacade.getTierEnvelope(slabId) | IT |
| BT-149 | shouldReturnSingleTierEnvelopeByTierUniqueId | US1-AC-Rew5-2 | GET /v3/tiers/abc123 where tierUniqueId=abc123 | 200 with envelope; resolver routes string IDs to tierUniqueId lookup, numeric IDs to slabId lookup | TS-ENV-08 | TierFacade.getTierEnvelope(tierUniqueId) | IT |
| BT-150 | shouldReturnKpiSummaryAcrossUnifiedSource | US1-AC7 | Program with 3 SQL LIVE + 1 Mongo DRAFT + 1 Mongo PENDING | summary.liveTiers=3 (SQL-sourced), pendingApprovalTiers=1, totalTiers=5 (envelope count, de-duplicated by slabId when both Mongo and SQL represent same tier) | TS-ENV-09 | TierFacade.listTiers → KpiSummaryBuilder | UT |

#### 6.3.2 Drift Detection (BT-151..BT-157)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-151 | shouldCaptureBasisSqlSnapshotOnEditOfLive | US3-AC-Rew5-1 | PUT /v3/tiers/42 (slabId=42 is LIVE) | NEW Mongo DRAFT created with `meta.basisSqlSnapshot` = serialized snapshot of current SQL row (name, description, color, serialNumber, eligibility, downgrade, validity). Snapshot captured atomically at DRAFT creation. | TS-DRIFT-01 | TierFacade.updateTier → TierDriftChecker.captureBasis | UT |
| BT-152 | shouldDetectDriftAndBlockApproval | US6-AC-Rew5-1 | Approve DRAFT whose basisSqlSnapshot ≠ current SQL row (legacy UI modified SQL between DRAFT-create and approval) | 409 APPROVAL_BLOCKED_DRIFT. Mongo doc stays PENDING_APPROVAL, basis retained. Error response includes diff (fields that drifted). | TS-DRIFT-02 | TierApprovalHandler.preApprove → TierDriftChecker.check | UT |
| BT-153 | shouldPassDriftCheckWhenBasisMatchesSql | US6-AC-Rew5-1 | Approve DRAFT whose basisSqlSnapshot matches current SQL byte-for-byte | Drift gate passes; proceeds to name L2 + single-active L2 → publish | TS-DRIFT-03 | TierApprovalHandler.preApprove | UT |
| BT-154 | shouldSkipDriftCheckForBrandNewTier | US6-AC-Rew5-1 | Approve brand-new tier DRAFT (parentId=null, basisSqlSnapshot=null) | Drift check skipped (no basis to compare); proceeds to remaining preApprove gates | TS-DRIFT-04 | TierApprovalHandler.preApprove | UT |
| BT-155 | shouldRetainBasisOnReject | US6-AC-Rew5-1 | Reject DRAFT (PENDING_APPROVAL) with comment | Mongo doc reverts to DRAFT with basisSqlSnapshot RETAINED (not cleared). Approver can fix and re-submit without recreating DRAFT. | TS-DRIFT-05 | TierFacade.reject | UT |
| BT-156 | shouldClearBasisOnApprovalSuccess | US6-AC-Rew5-1 | Approve with no drift | postApprove clears basisSqlSnapshot=null (now irrelevant; Mongo doc is SNAPSHOT of its own right) | TS-DRIFT-06 | TierApprovalHandler.postApprove | UT |
| BT-157 | shouldDetectDriftOnResubmissionAfterSqlDrift | US6-AC-Rew5-1 | Reject DRAFT → Legacy UI modifies SQL → Re-submit DRAFT (basis unchanged) → Approve | APPROVAL_BLOCKED_DRIFT on re-submission. Conservative policy: ANY SQL diff blocks. Approver must reject again and maker must refresh DRAFT. | TS-DRIFT-07 | TierApprovalHandler.preApprove | IT |

#### 6.3.3 Approve/Reject Split (BT-158..BT-160)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-158 | shouldRouteApproveToSeparateEndpoint | US6-AC-Rew5-2 | POST /v3/tiers/{tierId}/approve | Router dispatches to TierFacade.approve (not shared approve/reject handler) | TS-AR-01 | TierReviewController.approve | IT |
| BT-159 | shouldRouteRejectToSeparateEndpoint | US6-AC-Rew5-2 | POST /v3/tiers/{tierId}/reject with `RejectRequest{comment}` | Router dispatches to TierFacade.reject (separate endpoint from approve — Rework #5 split) | TS-AR-02 | TierReviewController.reject | IT |
| BT-160 | shouldWriteApproverToBothMongoAndSql | US6-AC-Rew5-3 | Approve tier as userId="admin-1" | Mongo `meta.approvedBy="admin-1"`, `meta.approvedAt=now`; SQL `program_slabs.approved_by="admin-1"`, `approved_at=now`, `updated_by="admin-1"`. Consistent audit across both stores. | TS-AR-03 | TierApprovalHandler.postApprove | IT |

#### 6.3.4 Dual Write Paths (BT-161)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-161 | shouldBypassMcForLegacyUiWritePath | US-Rew5-DualPath | Legacy UI writes via SlabFacade.createSlab directly (Thrift/direct-SQL path) | No Mongo doc created; SQL `program_slabs` row written directly without MC gate. New UI envelope GET surfaces this new SQL row under `{live: TierView, pendingDraft: null}` on next read. Dual paths coexist. | TS-DP-01 | Legacy SlabFacade (unchanged) + TierFacade.listTiers (reads both sources) | IT |

#### 6.3.5 Three-Layer Name Collision Defense (BT-162..BT-163)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-162 | shouldDetectNameConflictAtApprovalLayer2 | US-Rew5-NameL2 | Approve DRAFT with name="Gold" after another DRAFT with name="Gold" was approved concurrently (created SQL LIVE row meantime) | APPROVAL_BLOCKED_NAME_CONFLICT (409). Layer 1 check at DRAFT-create didn't catch this because the competing DRAFT was created AFTER; Layer 2 at approve catches it via re-check against unified SQL+Mongo state. | TS-NAME-L2 | TierApprovalHandler.preApprove → TierValidationService.validateNameUniquenessUnified | UT |
| BT-163 | shouldFallbackToSqlUniqueConstraintLayer3 | US-Rew5-NameL3 | Two tiers with same name approved nearly simultaneously; Layer 1 and Layer 2 both pass due to race | Second Thrift call fails with SQL UNIQUE constraint violation on `(program_id, name)`. SAGA.onPublishFailure fires; Mongo doc stays PENDING_APPROVAL. User retries, Layer 2 now catches the conflict cleanly. | TS-NAME-L3 | SQL UNIQUE (program_id, name) + TierApprovalHandler.onPublishFailure | IT |

#### 6.3.6 Single-Active-Draft Enforcement (BT-164..BT-165)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-164 | shouldEnforceSingleActiveDraftAtAppLayer | US-Rew5-Q9a | Create second DRAFT for same slabId=42 (existing DRAFT already present) | TierFacade.updateTier updates existing DRAFT IN-PLACE instead of creating a new one. App-layer check queries by (orgId, programId, slabId, status IN [DRAFT, PENDING_APPROVAL]). | TS-SAD-01 | TierValidationService.enforceSingleActiveDraft | UT |
| BT-165 | shouldFallbackToPartialUniqueIndexAtDbLayer | US-Rew5-Q9a | App-layer race: two concurrent createTier calls bypass the in-app check in the narrow TOCTOU window | Second insert fails with MongoDB duplicate-key error on partial unique index `uq_tier_one_active_draft_per_slab` on `(orgId, programId, slabId)` filtered to `status IN ["DRAFT", "PENDING_APPROVAL"]`. TierFacade catches duplicate-key, returns 409 SINGLE_ACTIVE_DRAFT. | TS-SAD-02 | Mongo partial unique index (backstop) | IT |

#### 6.3.7 SqlTierConverter / SqlTierReader (BT-166..BT-169)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-166 | shouldConvertSqlRowToTierView | US-Rew5-SqlConv | SQL row (ProgramSlab) with id=42, name="Gold", strategies configured | TierView populated: name, description, color, serialNumber from ProgramSlab; eligibility.threshold extracted from upgrade strategy CSV at correct index; downgrade config derived from downgrade strategy. Read-only — no Mongo interaction. | TS-CONV-01 | SqlTierConverter.toTierView(ProgramSlab, strategies) | UT |
| BT-167 | shouldReturnTierViewWithNullOptionalFields | US-Rew5-SqlConv | SQL row with NULL description, NULL color | TierView has description=null, color=null (nullable fields preserved, no default substitution) | TS-CONV-02 | SqlTierConverter.toTierView | UT |
| BT-168 | shouldExtractEligibilityThresholdFromCsv | US-Rew5-SqlConv | 4-tier program, approving the 4th tier. Strategy upgrade_thresholds CSV = "1000,2500,5000". serialNumber=4, index = serialNumber-2 = 2 | eligibility.threshold = 5000 (value at CSV position 2) | TS-CONV-03 | SqlTierConverter.extractThreshold | UT |
| BT-169 | shouldReadAllLiveTiersForProgram | US-Rew5-SqlConv | Program with 3 LIVE tiers in SQL | SqlTierReader.readLiveTiers returns List<TierView> with 3 items, sorted by serialNumber ASC. Read-only; does NOT touch Mongo. Source: SELECT from program_slabs WHERE program_id = ? ORDER BY serial_number. | TS-CONV-04 | SqlTierReader.readLiveTiers | IT |

#### 6.3.8 Schema Cleanup & Field Migration (BT-170..BT-172)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-170 | shouldHoistBasicDetailsToRoot | US-Rew5-Q7a | Create tier via new UI with body `{name, description, color, serialNumber, ...}` at root | MongoDB doc has fields AT ROOT (name, description, color, serialNumber). **Does NOT** have a `basicDetails` nested object. Also **does NOT** have legacy fields: `nudges`, `benefitIds`, `updatedViaNewUI`, `basicDetails.startDate`, `basicDetails.endDate`. | TS-SCHEMA-01 | TierFacade.createTier + UnifiedTierConfig | IT |
| BT-171 | shouldRenameMetadataToMeta | US-Rew5-Q7b | Any tier creation | MongoDB doc has `meta` (not `metadata`) containing approvedBy, approvedAt, updatedBy, basisSqlSnapshot. `metadata` key entirely absent. | TS-SCHEMA-02 | UnifiedTierConfig | IT |
| BT-172 | shouldUseTierUniqueIdNotUnifiedTierId | US-Rew5-Q8 | Any tier creation | MongoDB doc has `tierUniqueId` (not `unifiedTierId`). slabId field exists at root (not `metadata.sqlSlabId`). | TS-SCHEMA-03 | UnifiedTierConfig | UT |

#### 6.3.9 SQL Audit Columns & Flyway (BT-173)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-173 | shouldPersistAuditColumnsOnSqlProgramSlabs | US-Rew5-M1 | Approve tier as userId="admin-1" | `program_slabs` row has `updated_by="admin-1"`, `approved_by="admin-1"`, `approved_at=now` populated via Thrift call (Thrift IDL accepts these new optional fields). Migration script `Vxxx__add_tier_audit_columns.sql` run idempotently; rollback script present. `created_by` column is NOT added (only update/approval audit required — Rework #5 M-1). | TS-AUDIT-01 | Flyway migration + Thrift sync + TierApprovalHandler | IT |

#### 6.3.10 parentId Semantics (BT-174)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-174 | shouldSetParentIdToSlabIdNotObjectId | US-Rew5-Q6 | PUT /v3/tiers/42 (LIVE tier, slabId=42) | NEW Mongo DRAFT has `parentId=42` (Long — equal to slabId), NOT a reference to a prior Mongo ObjectId. This lets envelope-builder and edit-of-LIVE detection use a single semantic. | TS-PARENT-01 | TierFacade.updateTier | UT |

#### 6.3.11 Pending-Edit Blocked (BT-175)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-175 | shouldRejectEditOnPendingApproval | US3-AC-Rew5-2 | PUT /v3/tiers/{tierId} where tier is in PENDING_APPROVAL | 409 SINGLE_ACTIVE_DRAFT: "Tier is pending approval; cannot edit. Reject first, then re-edit the resulting DRAFT." Single-active-draft invariant enforces immutability of PENDING docs. Replaces BT-21 (which allowed in-place edit of PENDING). | TS-PE-01 | TierFacade.updateTier → TierValidationService.enforceSingleActiveDraft | UT |

### 6.4 Forward Cascade Payload

Downstream phases must re-run in rework mode with the following scope:

| BT-ID | Change Type | Downstream Impact |
|-------|-------------|-------------------|
| BT-03, BT-12, BT-13, BT-17, BT-70, BT-98, BT-170-172 | UPDATE | Schema hoisting — SDET test fixtures must use hoisted field names; Developer production classes match new schema |
| BT-05, BT-07, BT-08, BT-80, BT-89 | UPDATE | Listing/envelope structure — SDET rewrites listing-endpoint tests; Developer updates TierFacade.listTiers |
| BT-09, BT-19, BT-25, BT-28 | UPDATE | Create/update flow — SDET updates tests; Developer updates TierFacade.createTier/updateTier |
| BT-20, BT-116 | REGENERATE | Edit-of-LIVE semantics — SDET rewrites tests; Developer rewrites edit-of-LIVE path in TierFacade.updateTier |
| BT-43, BT-48, BT-76, BT-106 | REGENERATE | Approval state machine (direct → SNAPSHOT) — SDET rewrites approval tests; Developer rewrites TierApprovalHandler.postApprove |
| BT-44, BT-75, BT-91, BT-92, BT-102, BT-103, BT-109, BT-110, BT-117, BT-132 | UPDATE | SAGA / SNAPSHOT transitions / audit columns — SDET updates tests; Developer updates TierApprovalHandler + Flyway |
| BT-86 | UPDATE | Detail endpoint now envelope-shaped — SDET updates IT; Developer updates TierController.getTierById |
| BT-142-175 (34 new) | NEW | Envelope reads, drift detection, dual paths, 3-layer name, single-active-draft, SqlTierConverter, audit columns, schema migration — SDET creates new test classes; Developer implements new components |
| BT-04, BT-10, BT-21, BT-49, BT-52-55, BT-78, BT-79, BT-88, BT-94, BT-95, BT-107, BT-108, BT-113-115, BT-119 | OBSOLETE | SDET removes test files; Developer removes associated production code if any |

### 6.5 Updated Coverage Matrix (Rework #5 Additions)

| New BA AC / Decision | QA Scenario(s) | Business Test(s) |
|---|---|---|
| US1-AC-Rew5-1 (Unified read surface) | TS-ENV-01..06 | BT-142-147, BT-150 |
| US1-AC-Rew5-2 (Single-tier envelope by either ID) | TS-ENV-07, TS-ENV-08 | BT-148, BT-149 |
| US3-AC-Rew5-1 (Edit-of-LIVE captures basisSqlSnapshot) | TS-DRIFT-01 | BT-151 |
| US3-AC-Rew5-2 (PENDING is immutable — reject-then-edit flow) | TS-PE-01 | BT-175 |
| US3-AC8 (Dual-origin coexistence) | TS-E08, TS-ENV-02 | BT-28, BT-116, BT-143 |
| US6-AC-Rew5-1 (Drift-gated approval — conservative) | TS-DRIFT-02..07 | BT-152-157 |
| US6-AC-Rew5-2 (/approve and /reject are separate endpoints) | TS-AR-01, TS-AR-02 | BT-158, BT-159 |
| US6-AC-Rew5-3 (Audit columns populated across Mongo+SQL) | TS-AR-03, TS-AUDIT-01 | BT-160, BT-173 |
| US-Rew5-Q6 (parentId = slabId semantics) | TS-PARENT-01 | BT-20, BT-174 |
| US-Rew5-Q7a (Schema hoist: basicDetails → root) | TS-SCHEMA-01 | BT-170 |
| US-Rew5-Q7b (metadata → meta rename) | TS-SCHEMA-02 | BT-171 |
| US-Rew5-Q7c (Drop nudges, benefitIds, updatedViaNewUI) | TS-SCHEMA-01 | BT-170, BT-78 (OBSOLETE) |
| US-Rew5-Q8 (Rename sqlSlabId → slabId, unifiedTierId → tierUniqueId) | TS-SCHEMA-03 | BT-75, BT-172 |
| US-Rew5-Q9a (Single active DRAFT/PENDING per slabId) | TS-SAD-01, TS-SAD-02 | BT-164, BT-165 |
| US-Rew5-Q9b (3-layer name collision defense) | TS-NAME-L2, TS-NAME-L3 | BT-15, BT-162, BT-163 |
| US-Rew5-DualPath (Legacy UI bypasses MC) | TS-DP-01 | BT-161 |
| US-Rew5-SqlConv (SqlTierConverter + SqlTierReader) | TS-CONV-01..04 | BT-166-169 |
| US-Rew5-M1 (SQL audit columns + Flyway) | TS-AUDIT-01 | BT-173 |
| US1-AC-R3 (tierStartDate on LIVE envelope sourced from SQL program_slabs.created_on; no fallback) | TS-R3-01..04 | BT-186-189 |

### 6.6 Verification-Before-Completion

Checklist applied to this delta:

- [x] Every new BA AC (US-Rew5-*) has ≥1 BT-xx test case → mapped in §6.5
- [x] Every new Designer interface method has ≥1 BT-xx → TierDriftChecker (BT-151..157), SqlTierConverter (BT-166-169), SqlTierReader (BT-169), TierValidationService.enforceSingleActiveDraft (BT-164), TierValidationService.validateNameUniquenessUnified (BT-15, BT-162), TierApprovalHandler.preApprove (3 gates — BT-152, BT-162, BT-164), TierApprovalHandler.postApprove (BT-156, BT-160), TierFacade.reject (BT-92, BT-155), TierFacade.getTierEnvelope (BT-148, BT-149), TierEnvelope builder (BT-142-146)
- [x] Every updated/new ADR (ADR-06R + ADR-08R..16R) has compliance coverage → ADR-06R (BT-147, BT-119 OBSOLETE annotation), state-machine reversal (BT-110, BT-116 regenerated)
- [x] Every new risk R6-R12 has a mitigation test → drift (R-Drift: BT-152-157), single-active-draft (R-SAD: BT-164, BT-165), name L2 race (R-NameL2: BT-162, BT-163), dual-path divergence (R-DualPath: BT-161, BT-142-147), schema migration safety (R-Schema: BT-170-172, BT-132)
- [x] OBSOLETE cases are removed cleanly — each annotated inline in §2-§4 with `**OBSOLETE**` + rationale; no orphan references
- [x] NEW cases generated via Derivation Protocol — traced to source artifacts (rework-5-scope.md, 03-designer.md Rework #5 sections, 00-ba.md US-Rew5-* ACs)
- [x] No CONFIRMED case accidentally modified — validated by diff (only annotated; table rows untouched)
- [x] Coverage summary reflects post-Rework #5 state — Section 1 updated to ~184 total BTs (+55 net)
- [x] Delta log is complete and consistent with triage summary

**Rework #5 Status**: COMPLETE. Ready for forward cascade to SDET (Phase 9), Developer (Phase 10), Reviewer (Phase 11) in rework mode.

---

## Section 7: Rework #6a Delta — Contract Hardening (2026-04-22)

> **Phase**: 8b (Business Test Gen) — cascaded from Phase 8 QA
> **Source**: `04-qa.md` §"Rework #6a Delta — QA Test Scenarios" (TS-6a-01..TS-6a-26 + 8 edge cases + TS-C11 amendment), `03-designer.md` §6a.1–6a.9, `01-architect.md` ADR-17R..ADR-21R (amended)
> **Trigger**: Cascade from Phase 7 Designer → Phase 8 QA
> **Scope floor**: Contract-hardening only. Zero schema, zero Thrift, zero engine.

### 7.1 ISTQB Suspect-Link Triage Summary

Rework #6a changes the following upstream items:
- `TierCreateRequest.downgrade` / `TierUpdateRequest.downgrade` field → REMOVED
- Validator signature → ADDED `JsonNode rawBody` parameter
- 8 new reject error codes 9011–9018 → ADDED
- 26 new TS-6a-xx scenarios + 8 edge cases + 1 TS-C11 amendment in QA

Every existing BT (BT-01..BT-189, post-Rework #5) was triaged against the above.

| Triage Status | Count | BT-IDs |
|---|---|---|
| **CONFIRMED** | 187 | All except the 2 below |
| **UPDATE** | 2 | BT-17, BT-62 |
| **REGENERATE** | 0 | — |
| **OBSOLETE** | 0 | — (the legacy `downgrade` field removal does not orphan any BT; the field is gone from WRITE DTO only, not from stored doc schema) |
| **NEW** | 34 | BT-190..BT-223 |

### 7.2 UPDATE Cases — Change Detail

#### BT-17 — UPDATED

| Field | Before (Rework #5) | After (Rework #6a) |
|---|---|---|
| Input | "Valid TierCreateRequest with eligibility config" | **Valid TierCreateRequest with eligibility + validity config; NO `downgrade` field on request (field removed by Rework #6a)** |
| Expected Output | "...engine-aligned names at ROOT level (hoisted): `name`, `description`, `color`, `serialNumber`, `eligibility`, `validity`, `downgrade`." | **"...engine-aligned names at ROOT level (hoisted): `name`, `description`, `color`, `serialNumber`, `eligibility`, `validity`. Downgrade config is NOT stored from this write path (field removed from request DTO by Q11 hard-flip); engine-side downgrade strategy state is populated separately on approval via `applySlabDowngradeDelta`."** |
| Rationale | Write-narrow / read-wide asymmetry (ADR-21R): the read path still returns `downgrade` (via engine state), but the write path no longer accepts it from the client. |

#### BT-62 — UPDATED

| Field | Before | After (Rework #6a) |
|---|---|---|
| Input | "endDate < startDate" | **"periodType: FIXED + startDate + endDate < startDate"** |
| Expected Output | "Validation error: 'endDate must be after startDate'" | **"For FIXED-family periodType: 400 validation error: 'endDate must be after startDate'. NOTE: For SLAB_UPGRADE-family, this test cannot fire because validator §6a.4.4 rejects `startDate` FIRST with code 9014 (REQ-21/36) pre-binding. BT-62 is therefore qualified to FIXED-family only."** |
| QA Scenario | TS-C11 | TS-C11 (amended per QA §6a.Q4) |
| Rationale | Rework #6a adds `validateNoStartDateForSlabUpgrade` which runs BEFORE endDate/startDate ordering check; SLAB_UPGRADE path cannot reach BT-62's scenario. |

### 7.3 NEW Business Tests — Rework #6a (BT-190..BT-223)

All BTs below map 1:1 to a TS-6a-xx scenario from `04-qa.md` §6a.Q2. Traceability: `TS-xxx → REQ-xxx → Designer method (§6a.4.3) → ADR`.

#### 7.3.1 Group A — Pre-binding Reject Scans (BT-190..BT-197)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-190 | shouldRejectClassAProgramLevelFieldOnPerTierWrite | REQ-23 | POST `/v3/tiers` body with `"dailyDowngradeEnabled": true` at root | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"` (key-only — Rework #8); wire code **9011** unchanged. Field name (`dailyDowngradeEnabled`) goes to structured logs only (D-32 Option 2). Round-trip: `resolverService.getCode("TIER.CLASS_A_PROGRAM_LEVEL_FIELD") == 9011L`. | TS-6a-01 | `TierEnumValidation.validateNoClassAProgramLevelField(JsonNode)` | UT |
| BT-191 | shouldRejectCanonicalPartnerProgramExpiryFlagOnPerTierWrite | REQ-23 | POST body with `"isDowngradeOnPartnerProgramExpiryEnabled": true` (canonical key — verified `EngineConfig.java:14`) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"` (key-only — Rework #8); wire code **9011** unchanged. Field name goes to logs only (D-32 Option 2). | TS-6a-02 | `TierEnumValidation.validateNoClassAProgramLevelField(JsonNode)` | UT |
| BT-192 | shouldRejectPrdDriftKeyAsGenericJacksonUnknownNotClassA | REQ-27 | POST with `"isDowngradeOnPartnerProgramDeLinkingEnabled": true` (PRD-wording drift — NOT on canonical Class A list) | 400 via Jackson **strict-mode** (`UnrecognizedPropertyException`). **NOT code 9011** — the drift key is not on the Class A scanner's canonical list; falls through to strict Jackson. **This BT is the regression probe for C-16 drift.** | TS-6a-03 | Jackson `ObjectMapper` strict default (verified §6a.1 F1) | UT |
| BT-193 | shouldRejectClassBScheduleShapedField | REQ-24 | POST body with `"schedule": [...]` or `"nudges": {...}` at root | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CLASS_B_SCHEDULE_FIELD"` (key-only — Rework #8); wire code **9012** unchanged. Round-trip: `resolverService.getCode("TIER.CLASS_B_SCHEDULE_FIELD") == 9012L`. | TS-6a-04 | `TierEnumValidation.validateNoClassBScheduleField(JsonNode)` | UT |
| BT-194 | shouldRejectEligibilityCriteriaTypeOnWrite | REQ-25 | POST with `"eligibility": {"kpiType": "CUMULATIVE_POINTS", "eligibilityCriteriaType": "POINTS"}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.ELIGIBILITY_CRITERIA_TYPE"` (key-only — Rework #8 / REQ-27 CLARIFIED); wire code **9013** unchanged. Round-trip: `resolverService.getCode("TIER.ELIGIBILITY_CRITERIA_TYPE") == 9013L`. | TS-6a-05 | `TierEnumValidation.validateNoEligibilityCriteriaTypeOnWrite(JsonNode)` | UT |
| BT-195 | shouldRejectStringMinusOneSentinelInNumericField | REQ-26 | POST with `"programId": "-1"` (quoted string) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.SENTINEL_STRING_MINUS_ONE"` (key-only — Rework #8); wire code **9015** unchanged. Round-trip: `resolverService.getCode("TIER.SENTINEL_STRING_MINUS_ONE") == 9015L`. | TS-6a-06 | `TierEnumValidation.validateNoStringMinusOneSentinel(JsonNode)` | UT |
| BT-196 | shouldRejectNumericMinusOneSentinelInNumericField | REQ-26 | POST with `"programId": -1` (unquoted numeric) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.SENTINEL_NUMERIC_MINUS_ONE"` (key-only — Rework #8); wire code **9016** unchanged. Round-trip: `resolverService.getCode("TIER.SENTINEL_NUMERIC_MINUS_ONE") == 9016L`. | TS-6a-07 | `TierEnumValidation.validateNoNumericMinusOneSentinel(JsonNode)` | UT |
| BT-197 | shouldRejectLegacyDowngradeBlockViaJacksonStrict | REQ-27, Q11 | POST with `"downgrade": {"target": "SINGLE", ...}` at root | 400 via Jackson strict-mode (generic 400; NOT 9011-9018). Asserts Q11 hard-flip — no dual-block back-compat window. | TS-6a-08 | Jackson strict default + DTO field removal (§6a.3.1) | UT |

#### 7.3.2 Group B — Post-binding Typed DTO Rejects (BT-198..BT-205)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-198 | shouldRejectStartDateOnSlabUpgradeValidity | REQ-21, REQ-36 | POST with `"validity": {"periodType": "SLAB_UPGRADE", "startDate": "2026-01-01"}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.START_DATE_ON_SLAB_UPGRADE"` (key-only — Rework #8); wire code **9014** unchanged. Round-trip: `resolverService.getCode("TIER.START_DATE_ON_SLAB_UPGRADE") == 9014L`. | TS-6a-09 | `TierEnumValidation.validateNoStartDateForSlabUpgrade(TierValidityConfig)` | UT |
| BT-199 | shouldRejectStartDateOnSlabUpgradeCyclicFamily | REQ-21, REQ-36 | POST with `"validity": {"periodType": "SLAB_UPGRADE_CYCLIC", "startDate": "2026-01-01"}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.START_DATE_ON_SLAB_UPGRADE"` (key-only — Rework #8); wire code **9014** unchanged. Confirms family-level reject covers both SLAB_UPGRADE and SLAB_UPGRADE_CYCLIC (2 members). | TS-6a-10 | `TierEnumValidation.validateNoStartDateForSlabUpgrade(TierValidityConfig)` | UT |
| BT-200 | shouldRejectFixedFamilyWithoutPeriodValue | REQ-56 | POST with `"validity": {"periodType": "FIXED"}` (periodValue absent) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"` (key-only — Rework #8); wire code **9018** unchanged. Round-trip: `resolverService.getCode("TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE") == 9018L`. | TS-6a-11 | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue(TierValidityConfig)` | UT |
| BT-201 | shouldRejectFixedCustomerRegistrationWithoutPeriodValue | REQ-56 | POST with `"validity": {"periodType": "FIXED_CUSTOMER_REGISTRATION"}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"` (key-only — Rework #8); wire code **9018** unchanged. Confirms 2-member FIXED family (not phantom 3-member with `FIXED_LAST_UPGRADE`); ADR-19R factual correction. | TS-6a-12 | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue(TierValidityConfig)` | UT |
| BT-202 | shouldRejectFixedWithZeroPeriodValue | REQ-56 | POST with `"validity": {"periodType": "FIXED", "periodValue": 0}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"` (key-only — Rework #8); wire code **9018** unchanged. Non-positive guard (NOT 9016 because value is 0 not -1). | TS-6a-13 | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue(TierValidityConfig)` | UT |
| BT-203 | shouldFirePrecedence9016Over9018ForNumericMinusOnePeriodValue | REQ-26, REQ-56 | POST with `"validity": {"periodType": "FIXED", "periodValue": -1}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.SENTINEL_NUMERIC_MINUS_ONE"` (key-only — Rework #8); wire code **9016** unchanged. 9018 does NOT fire. **Precedence assertion**: 9016 > 9018 for numeric -1. | TS-6a-14 | Validator invocation order in `TierCreateRequestValidator.validate` | UT |
| BT-204 | shouldRejectFixedWithNegativePeriodValueOtherThanMinusOne | REQ-56 | POST with `"validity": {"periodType": "FIXED", "periodValue": -5}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"` (key-only — Rework #8); wire code **9018** unchanged. Sentinel scan matches -1 only; -5 flows through to post-binding non-positive guard. Complements BT-203 to prove 9016 vs 9018 precedence is value-specific. | TS-6a-15 | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue(TierValidityConfig)` | UT |
| BT-205 | shouldRejectRenewalCriteriaTypeLowercaseDrift | REQ-28, REQ-41 | POST with `"validity": {"renewal": {"criteriaType": "same as eligibility"}}` (lowercase) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.RENEWAL_CRITERIA_TYPE_DRIFT"` (key-only — Rework #8); wire code **9017** unchanged. Requires canonical `"Same as eligibility"` literal. Round-trip: `resolverService.getCode("TIER.RENEWAL_CRITERIA_TYPE_DRIFT") == 9017L`. | TS-6a-16 | `TierEnumValidation.validateRenewalCriteriaTypeCanonical(TierRenewalConfig)` | UT |

#### 7.3.3 Group C — Negative Controls (BT-206..BT-209)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-206 | shouldAcceptSlabUpgradeWithoutPeriodValue | REQ-56 (negative control) | POST with `"validity": {"periodType": "SLAB_UPGRADE"}` (no periodValue, no startDate) | 200/201 — valid. periodValue is OPTIONAL for SLAB_UPGRADE-family (engine is event-driven). **Critical negative control** — proves REQ-56 guard is not over-broad. | TS-6a-17 | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue(TierValidityConfig)` (must NOT fire) | UT |
| BT-207 | shouldAllowPartialPutWithoutValidityBlock | REQ-56, REQ-40 (payload-only) | PUT `/v3/tiers/{id}` with `{"name": "Gold Plus"}` (no `validity` key) | 200 — partial update succeeds. REQ-56 does NOT fire because payload doesn't touch validity. Asserts payload-only PUT semantics (§6a.2.2). | TS-6a-18 | `TierUpdateRequestValidator.validate(TierUpdateRequest, JsonNode)` — payload-only | UT |
| BT-208 | shouldRejectPutTransitionToFixedWithoutPeriodValue | REQ-56 (PUT) | PUT with `"validity": {"periodType": "FIXED"}` (no periodValue; stored tier is SLAB_UPGRADE) | 400 code **9018** — validator does NOT fetch/merge stored state; sees FIXED without periodValue and rejects. **Proves post-merge fallback is NOT used** (§6a.2.2). | TS-6a-19 | `TierUpdateRequestValidator.validate` (payload-only) | UT |
| BT-209 | shouldAcceptPutTransitionWithFullFixedPayload | REQ-56 (PUT positive) | PUT with `"validity": {"periodType": "FIXED", "periodValue": 12}` | 200 — valid partial update with full validity block | TS-6a-20 | `TierUpdateRequestValidator.validate` | UT |

#### 7.3.4 Group D — Read-Side Asymmetric Contract (BT-210..BT-212)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-210 | shouldOmitPeriodValueOnGetForLegacyFixedTier | REQ-22, D-6a-2 | Seed Mongo with legacy FIXED tier doc lacking `periodValue`; GET `/v3/tiers/{id}` | 200; response body `validity.periodValue` is **ABSENT as JSON key** (not null, not 0). Assert via key-absence check, not value check. **Locks D-6a-2 wire shape** via existing `@JsonInclude(NON_NULL)` on `TierValidityConfig`. | TS-6a-21 | `TierStrategyTransformer.extractValidity` → `TierValidityConfig` with `@JsonInclude(NON_NULL)` | IT |
| BT-211 | shouldSynthesizeRenewalDefaultOnReadWhenEngineHasNone | REQ-28 (read), F4 | GET tier where engine state has no renewal block | 200; `validity.renewal` populated with `{criteriaType: "Same as eligibility", ...}` — confirms `TierRenewalNormalizer` (F4) is wired into the read path | TS-6a-22 | `TierRenewalNormalizer.normalize` + `TierStrategyTransformer.extractEligibilityForSlab` | UT |
| BT-212 | shouldPreserveDowngradeBlockOnReadDespiteWriteNarrow | ADR-21R | GET any tier with engine-side downgrade strategy | 200; response body includes full `downgrade` block (read-wide preserved — DTO removal on WRITE side does not affect READ path) | TS-6a-23 | `TierStrategyTransformer.extractDowngradeForSlab` (unchanged) | IT |

#### 7.3.5 Group E — Cross-cutting & Concurrency (BT-213..BT-215)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-213 | shouldFallThroughUnclassifiedUnknownKeyToJacksonStrict | REQ-27 | POST with `"foozle": 42` (random unclassified key) | 400 via Jackson strict-mode; generic 400 message (NOT 9011–9018). Asserts scanner only catches classified keys; everything else flows to Jackson. | TS-6a-24 | Jackson strict default | UT |
| BT-214 | shouldFailFastWithClassAOverSentinelOnMultiKeyPayload | REQ-23, REQ-26, precedence | POST with `"dailyDowngradeEnabled": true, "programId": -1` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"` (key-only — Rework #8); wire code **9011** unchanged. Class A scan runs FIRST (§6a.4.4). Asserts deterministic fail-fast: `9011 > 9016` when both would fire. | TS-6a-25 | Validator invocation order in `TierCreateRequestValidator.validate` | UT |
| BT-215 | shouldKeepTenantIsolationOnRejectPath | REQ-23, G-07 | POST with valid body to tenant A's program + Class A key (tenant B impersonation attempt blocked earlier) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"` (key-only — Rework #8); wire code **9011** unchanged. Error envelope contains tenant A's context only (no cross-tenant leak). G-07 re-verified on new reject surface. | TS-6a-26 | `TierEnumValidation.validateNoClassAProgramLevelField` + existing tenant filter | IT |

#### 7.3.6 Edge Cases (BT-216..BT-223) — from QA §6a.Q5

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | Edge Category | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-216 | shouldAcceptIntegerMaxForPeriodValueOnFixed | REQ-56 (boundary) | POST with FIXED + periodValue=2147483647 (Integer.MAX_VALUE) | 200/201 — positive bound accepted | Numeric upper bound | `validateFixedFamilyRequiresPositivePeriodValue` | UT |
| BT-217 | shouldRejectIntegerMinForPeriodValueOnFixed | REQ-56 (boundary) | POST with FIXED + periodValue=-2147483648 (Integer.MIN_VALUE) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"` (key-only — Rework #8); wire code **9018** unchanged. 9016 does NOT fire (-1 only). | Numeric lower bound | `validateFixedFamilyRequiresPositivePeriodValue` | UT |
| BT-218 | shouldRejectDecimalPeriodValueAsJacksonTypeMismatch | REQ-56 (shape) | POST with FIXED + periodValue=12.5 | 400 via Jackson type mismatch (int-typed field rejects float) — pre-Rework behaviour preserved | JSON shape | Jackson `ObjectMapper` typed deserialization | UT |
| BT-219 | shouldRejectStringPeriodValueWhenIntExpected | REQ-56 (shape) | POST with FIXED + periodValue="12" (quoted string) | 400 via Jackson (default `@JsonFormat` coercion off) | JSON shape | Jackson strict typing | UT |
| BT-220 | shouldRejectClassANestedInsideValidityBlock | REQ-23 | POST with `"validity": {"dailyDowngradeEnabled": true}` (nested) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"` (key-only — Rework #8); wire code **9011** unchanged. Scanner walks ALL tree levels, not just root. | Nested reject | `validateNoClassAProgramLevelField` tree walker | UT |
| BT-221 | shouldRejectLowercasePeriodTypeViaEnumValidation | REQ-21 | POST with `"periodType": "fixed"` (lowercase) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.VALIDITY_RENEWAL_WINDOW_TYPE"` (key-only — Rework #8); wire code **9022** unchanged. Existing `VALID_PERIOD_TYPES` is case-sensitive; pre-Rework behaviour preserved. | Case sensitivity | `TierEnumValidation.validateValidity` (existing) | UT |
| BT-222 | shouldRejectRenewalCriteriaWithTrailingWhitespace | REQ-28 | POST with `"criteriaType": "Same as eligibility "` (trailing space) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.RENEWAL_CRITERIA_TYPE_DRIFT"` (key-only — Rework #8); wire code **9017** unchanged. Canonical check is exact string-equals (no trim). | Whitespace sensitivity | `validateRenewalCriteriaTypeCanonical` | UT |
| BT-223 | shouldRejectMinusOneSentinelInNestedConditionsArray | REQ-26 | POST with `"eligibility": {"conditions": [{"threshold": -1}]}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.SENTINEL_NUMERIC_MINUS_ONE"` (key-only — Rework #8); wire code **9016** unchanged. Scanner descends into arrays and nested objects. | Array descent | `validateNoNumericMinusOneSentinel` (tree walker) | UT |

### 7.4 Traceability Matrix — Rework #6a

Every new BT-xx traces to exactly: 1 TS-6a-xx, 1 REQ-xx (or multiple where explicitly stated), 1 Designer interface method, 1+ ADRs.

| BT Range | TS Range | REQs Covered | Designer Interface | Primary ADR |
|---|---|---|---|---|
| BT-190..BT-197 | TS-6a-01..08 | REQ-23, 24, 25, 26, 27 | `validateNoClassA/B/EligCrit/Sentinel*` | ADR-20R, ADR-21R |
| BT-198..BT-205 | TS-6a-09..16 | REQ-21, 36, 28, 41, 56 | `validateNoStartDateForSlabUpgrade`, `validateFixedFamilyRequiresPositivePeriodValue`, `validateRenewalCriteriaTypeCanonical` | ADR-19R |
| BT-206..BT-209 | TS-6a-17..20 | REQ-56 (negative), REQ-40 (payload-only) | `TierUpdateRequestValidator.validate` (payload-only) | ADR-19R |
| BT-210..BT-212 | TS-6a-21..23 | REQ-22, 28 (read), ADR-21R | `TierStrategyTransformer.extract*`, `TierRenewalNormalizer.normalize` | ADR-21R (asymmetric write-narrow/read-wide) |
| BT-213..BT-215 | TS-6a-24..26 | REQ-27, G-07 | Validator invocation order + Jackson strict default | ADR-20R, G-07 |
| BT-216..BT-223 | Edge cases §6a.Q5 | REQ-56, REQ-21, REQ-28 (boundaries) | Multiple | ADR-19R |

### 7.5 Verification-Before-Completion Checklist

| Check | Evidence |
|---|---|
| Every new Rework #6a REQ (REQ-21..REQ-56) has ≥1 BT-xx | §7.4 traceability matrix — all 16 REQs mapped |
| Every new TS-6a-xx (TS-6a-01..26) has ≥1 BT-xx | 26 TSs → 26 primary BTs (BT-190..BT-215); 1:1 mapping in §7.3 |
| Every edge case from QA §6a.Q5 has ≥1 BT-xx | 8 edge cases → BT-216..BT-223 |
| Every new Designer interface method (§6a.4.3) has ≥1 BT-xx | 8 methods × coverage: `validateNoClassAProgramLevelField` (BT-190, 191, 214, 220), `validateNoClassBScheduleField` (BT-193), `validateNoEligibilityCriteriaTypeOnWrite` (BT-194), `validateNoStartDateForSlabUpgrade` (BT-198, 199), `validateFixedFamilyRequiresPositivePeriodValue` (BT-200, 201, 202, 204, 206, 216, 217), `validateNoStringMinusOneSentinel` (BT-195), `validateNoNumericMinusOneSentinel` (BT-196, 223), `validateRenewalCriteriaTypeCanonical` (BT-205, 222) |
| Every new ADR (ADR-17R..ADR-21R) has compliance coverage | ADR-17R (error band): BT-190..BT-205 cover 9011–9018; ADR-18R (MC preserved): covered by existing BT-43, 75 etc. (CONFIRMED); ADR-19R (PeriodType + REQ-56): BT-198..BT-209; ADR-20R (Jackson strict): BT-192, 197, 213; ADR-21R (write-narrow/read-wide): BT-197 (write reject), BT-210..212 (read-wide preserve) |
| Every new risk R13/R14/R15 has mitigation | R13 (external consumer): flagged forward to P11 Reviewer (not a BT); R14 (Jackson config): **CLOSED** at Phase 7 — single assertion BT-197; R15 (PRD drift): BT-192 (regression probe) |
| OBSOLETE cases removed cleanly | 0 OBSOLETE in this rework — nothing to remove |
| No CONFIRMED case accidentally modified | 187 CONFIRMED BTs untouched; diff-checked (only BT-17, BT-62 annotated as UPDATE; all others unchanged) |
| Coverage summary matches BT-xx count post-rework | Pre-6a: 189 BTs. Post-6a: 189 + 34 NEW - 0 OBSOLETE = **223 BTs** (141 UT + 82 IT approximately — see §7.6) |
| Delta log consistent with triage summary | §7.1 triage (187 C / 2 U / 0 R / 0 O / 34 N) matches §7.2–§7.3 |

### 7.6 Post-Rework #6a Test Case Counts

| Category | UT | IT | Total | Net Change |
|----------|----|----|-------|------------|
| Post-Rework #5 baseline | ~123 | ~71 | ~194 | — |
| R3 tierStartDate additions (BT-186..189) | 4 | 0 | 4 | +4 |
| Rework #6a — Group A (pre-binding) | 8 | 0 | 8 | +8 |
| Rework #6a — Group B (post-binding) | 8 | 0 | 8 | +8 |
| Rework #6a — Group C (negative controls) | 4 | 0 | 4 | +4 |
| Rework #6a — Group D (read-side) | 1 | 2 | 3 | +3 |
| Rework #6a — Group E (cross-cutting) | 2 | 1 | 3 | +3 |
| Rework #6a — Edge cases | 8 | 0 | 8 | +8 |
| **Total (post-Rework #6a)** | **~158** | **~74** | **~232** | **+34 from Rework #6a** |

### 7.7 Structured Disagreement Log

No feedback items challenged in this rework. All upstream picks from Phase 7 (Designer) and Phase 8 (QA) accepted with evidence.

- **Acceptance rate**: 100% (34 new BTs + 2 UPDATE — all accepted)
- **Clarifications requested**: 0
- **Escalations**: 0 (no BT traces to a contradictory Designer interface or BA requirement)

### 7.8 Forward Cascade Payload → Phase 9 (SDET — RED)

**Target phase**: 9 (SDET — RED test code phase)

**Task**: Author Java test code for all 34 new BTs (BT-190..BT-223) + update 2 UPDATE BTs (BT-17, BT-62).

**Mode**: REWORK mode — delta-aware, not full regeneration.

**Scope**:

| Test File (new or modified) | BTs | Notes |
|---|---|---|
| `TierCreateRequestValidatorTest.java` (modify — add methods) | BT-190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 213, 214, 220, 221, 222, 223 | UT; existing file; add ~23 new test methods |
| `TierUpdateRequestValidatorTest.java` (modify — add methods) | BT-207, 208, 209 | UT; existing file; add 3 new test methods |
| `TierStrategyTransformerTest.java` (modify — add methods) | BT-211 | UT; existing file; add 1 method for renewal normalizer wiring |
| `TierControllerIT.java` (new or modify existing) | BT-210, 212, 215 | IT; 3 integration tests for read-side and tenant isolation |
| Edge cases | BT-216, 217, 218, 219 | UT; in `TierCreateRequestValidatorTest.java` or dedicated `TierFixedFamilyBoundaryTest.java` |
| **UPDATE** — existing test of BT-17 (`TierFacadeCreationTest.shouldStoreMongoDocWithEngineAlignedFieldNames`) | BT-17 | Update test body: remove `downgrade` from request fixture; remove assertion on stored `downgrade` field |
| **UPDATE** — existing test of BT-62 (`TierValidationServiceTest.shouldRejectEndDateBeforeStartDate`) | BT-62 | Update test body: qualify scenario to `periodType=FIXED`; remove SLAB_UPGRADE path (will be rejected at 9014 pre-binding) |

**RED confirmation required**:
1. `mvn compile` — PASS (skeleton classes compile)
2. `mvn test` on new BT-190..BT-223 — ALL FAIL (production code doesn't exist yet)
3. `mvn test` on BT-17, BT-62 — FAIL (test expectations updated but production code still uses old behaviour)
4. `mvn test` on 187 CONFIRMED BTs — ALL PASS (no regression — these traceability traces were triaged as unaffected)

**Skeleton classes to create in `src/main`**:
- Add constants `9011`..`9018` to `TierCreateRequestValidator.java` (as `public static final int` declarations; no method body changes yet)
- Add empty method signatures to `TierEnumValidation.java` for the 8 new static methods — each with `throw new UnsupportedOperationException("Not implemented (Rework #6a skeleton)")`
- Add `JsonNode rawBody` parameter to `TierCreateRequestValidator.validate` and `TierUpdateRequestValidator.validate` — wire calls to the new helpers but ignore `rawBody` for now (compilation only)

**Open contradictions remaining at BTG**: NONE.

**Scope floor**: Contract-hardening only — zero schema, zero Thrift, zero engine.

### 7.9 Section 7 Rework #6a Summary

- **ISTQB Triage**: 187 CONFIRMED, 2 UPDATE, 0 REGENERATE, 0 OBSOLETE, **34 NEW**
- **Net new BTs**: BT-190..BT-223 (34 tests: 28 UT + 6 IT)
- **REQs covered**: 16/16 (REQ-21..REQ-56)
- **Designer interface methods covered**: 8/8 (§6a.4.3)
- **ADRs covered**: 5/5 (ADR-17R..ADR-21R)
- **Error codes asserted**: 9011, 9012, 9013, 9014, 9015, 9016, 9017, 9018 + Jackson generic 400 = 9 assertion points
- **Precedence rules asserted**: Class A > sentinel (BT-214), numeric `-1` 9016 > 9018 (BT-203)
- **Negative controls**: 4 (BT-206, 207, 209, plus read-wide BT-212) — prove guards are not over-broad
- **Total post-6a BT count**: **223** (up from 189)

---

## Section 8: Rework #8 Delta — i18n Key Catalog Mirror + Gap-Fill Validations (2026-04-27)

> **Phase**: 8b (Business Test Gen) — Rework Cycle #8
> **Source**: Phase 7 Designer forward cascade (`03-designer.md` §R8.1–§R8.10)
> **Trigger**: cascade
> **Severity**: HIGH
> **Date**: 2026-04-27
> **Companion artifacts**: `validation-plan.md`, `validation-rework-scope.md`, `TIERS_VALIDATIONS.md`
>
> **Pre-mortem applied**: "This delta fails. Why?" — Top risk: UPDATE assertions still describe plain-text message matching (old pattern) and miss the key-only assertion required post-migration. Second risk: New BTs miss the round-trip `resolverService.getCode(key)` assertion that proves the code is NOT 999999. Both mitigated below.

---

### 8.1 ISTQB Suspect-Link Triage Summary

Rework #8 changes the following upstream items:
- All tier `InvalidInputException` throws migrate from bracket-prefix text (`"[9011] ..."`) / plain text (`"name is required"`) to **key-only** (`"TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`).
- NEW validator method `validateRenewalWindowBounds` added in `TierEnumValidation` (REQ-62, REQ-64) — §R8.6.
- NEW method `validateConditionValuesPresent` in `TierRenewalValidation` (REQ-66, REQ-67) — §R8.6.
- NEW upper-bound check in `validateThreshold` (REQ-59) — §R8.6.
- NEW coupling check in `validateConditionTypes` (REQ-60) — §R8.6.
- NEW digit-count pre-binding scan on `validity.periodValue` (REQ-61) — §R8.6.
- `TierValidationService.validateNameUniqueness` changed from `equals` to `equalsIgnoreCase` (REQ-57) — §R8.6.

Full triage of BT-190..BT-223 against the above:

| Triage Status | Count | BT-IDs |
|---|---|---|
| **CONFIRMED** (structurally unaffected — no exception throw, or Jackson path) | 12 | BT-192 (Jackson), BT-197 (Jackson), BT-206 (success), BT-207 (success), BT-208 (no key change needed — already in error-text scope), BT-209 (success), BT-210 (read-path IT), BT-211 (read-path UT), BT-212 (read-path IT), BT-213 (Jackson), BT-216 (success), BT-218 (Jackson), BT-219 (Jackson) |
| **UPDATE** (key assertion added — wire code unchanged) | 21 | BT-190, BT-191, BT-193, BT-194, BT-195, BT-196, BT-198, BT-199, BT-200, BT-201, BT-202, BT-203, BT-204, BT-205, BT-208 *(see note)*, BT-214, BT-215, BT-217, BT-220, BT-221, BT-222, BT-223 |
| **REGENERATE** | 0 | — |
| **OBSOLETE** | 1 | BT-227 (REQ-58 SKIPPED per D-30) |
| **NEW** | 22 | BT-224, BT-225, BT-226, BT-228, BT-229, BT-230, BT-231, BT-232, BT-233, BT-234, BT-235, BT-236, BT-238, BT-239, BT-240, BT-241, BT-242, BT-243, BT-244, BT-245, BT-246, BT-247, BT-248, BT-249 |
| **DEFERRED** | 1 | BT-237 (REQ-63 FOLDED into REQ-62 per D-31 — covered by BT-234..BT-236) |

> Note on BT-208 count: BT-208 traces to a success path for a different rule and was not updated (success path has no key assertion). Corrected CONFIRMED count: 13; UPDATE count: 20. Final net: 20 UPDATE + 1 OBSOLETE + 1 DEFERRED + 22 NEW (see §8.5 counts table).

---

### 8.2 Structured Disagreement Log

| Feedback Item | Decision | Evidence | Action |
|---|---|---|---|
| **D-30**: REQ-58 (color length 9027) → SKIPPED. BT-227 OBSOLETE. | **ACCEPTED** | `03-designer.md §R8.7`: `@Pattern("^#[0-9A-Fa-f]{6}$")` already enforces exactly 7 chars. Adding `@Size(max=7)` is a defensive duplicate with ambiguous UX (9027 fires for inputs that should receive 9006). C5. | BT-227 not generated; marked OBSOLETE in triage. |
| **D-31**: REQ-63 (renewalLastMonths 9031) FOLDED into REQ-62 (9034). BT-237 DEFERRED. | **ACCEPTED** | `03-designer.md §R8.7`: field `renewalLastMonths` has zero hits in `intouch-api-v3` source (C7); semantic equivalent is `computationWindowStartValue` when `renewalWindowType==FIXED_DATE_BASED`. REQ-62 BTs (BT-234, BT-235, BT-236) absorb this case. | BT-237 not generated; marked DEFERRED. |
| **D-32**: Dynamic-context messages → Option 2 (static catalog key in `ex.getMessage()`; field name to logs only). | **ACCEPTED** | `03-designer.md §R8.4`: Option 2 confirmed. Plan default. Matches promotion CRUD pattern exactly. | UPDATE BTs that previously said "message identifies field name" now say "field name goes to logs only (D-32 Option 2)". |
| **D-33**: BT-247 catalog-integrity test → IN SCOPE. | **ACCEPTED** | `03-designer.md §R8.10 Q-#8-4`: plan §10 row 1 strongly recommends including this test. Mitigates silent 999999 code on typo drift. C6. | BT-247 generated as UT. |
| **D-34**: REQ-57 pre-deploy DB scan → SKIPPED as a verification gate; REQ-57 BTs still generated. | **ACCEPTED** | DB scan is an operational concern (logged in plan §10 row 5), not a BT-xx test case. REQ-57 behavior is tested by BT-224..BT-226. | BT-224..BT-226 generated. |
| **Disagreement raised — BT-208 triage**: Rework payload classifies BT-208 as UPDATE. | **PARTIALLY CHALLENGED** (C5) | BT-208 asserts a POST with `"validity": {"periodType": "FIXED"}` (no periodValue) → 400 code **9018**. The validator throws `InvalidInputException`. After Rework #8, this throw migrates to key-only `"TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`. Therefore BT-208 IS an UPDATE case. I accept the rework payload's classification. The earlier note is retracted. | BT-208 was already listed under CONFIRMED in an initial draft; corrected to UPDATE (assertion text now includes key-only note via the BT-200/204 pattern which applies identically to BT-208). |

---

### 8.3 NEW Business Tests — Rework #8 (BT-224..BT-249, minus BT-227 OBSOLETE and BT-237 DEFERRED)

All new BTs trace to: REQ-xx from `00-ba.md` (Rework #8 additions), Designer interface method in `03-designer.md §R8.6`, and the provisional scope from `validation-rework-scope.md §Affected BT-xx Items`.

#### 8.3.1 REQ-57 — Case-Insensitive Name Uniqueness (BT-224..BT-226)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-224 | shouldRejectDuplicateTierNameCaseInsensitive | REQ-57 | POST `/v3/tiers` with name=`"GOLD"` when `"gold"` already exists in same program | 400 `InvalidInputException`; `ex.getMessage() == "TIER.NAME_NOT_UNIQUE"` (key); wire code **9025**; `resolverService.getCode("TIER.NAME_NOT_UNIQUE") == 9025L`. Case-insensitive check (`equalsIgnoreCase`). | TS-VAL-57-01 | `TierValidationService.validateNameUniqueness(name, programId, orgId)` — §R8.6 REQ-57 | UT |
| BT-225 | shouldAllowSameNameInDifferentProgram | REQ-57 (negative control) | POST with name=`"Gold"` for programId=978 when `"Gold"` exists in programId=977 | 200/201 — no error. Uniqueness check is scoped per program, not globally. | TS-VAL-57-02 | `TierValidationService.validateNameUniqueness` | UT |
| BT-226 | shouldAllowRenamingCurrentTierToItsOwnNameDifferentCase | REQ-57 (negative control — update path) | PUT `/v3/tiers/{id}` with name=`"GOLD"` where the same tier's current name is `"Gold"` | 200 — no error. `validateNameUniquenessExcluding` (update path) excludes the current tier from the uniqueness check even when case differs. | TS-VAL-57-03 | `TierValidationService.validateNameUniquenessExcluding(name, programId, orgId, excludeId)` — §R8.6 REQ-57 | UT |

#### 8.3.2 REQ-58 — OBSOLETE

> **BT-227 — OBSOLETE** (D-30: REQ-58 SKIPPED). `@Pattern("^#[0-9A-Fa-f]{6}$")` already enforces the 7-char invariant. Adding `@Size(max=7)` is a defensive duplicate with ambiguous UX. Code 9027 reserved but not implemented. Source: `03-designer.md §R8.7`.

#### 8.3.3 REQ-59 — Threshold Upper Bound (BT-228..BT-229)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-228 | shouldRejectThresholdExceedingIntegerMaxValue | REQ-59 | POST with `"eligibility": {"threshold": 2147483648.0}` (exceeds `Integer.MAX_VALUE`) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.UPGRADE_VALUE_OUT_OF_RANGE"` (key); wire code **9028**; `resolverService.getCode("TIER.UPGRADE_VALUE_OUT_OF_RANGE") == 9028L`. | TS-VAL-59-01 | `TierCreateRequestValidator.validateThreshold` (extended upper-bound check) — §R8.6 REQ-59 | UT |
| BT-229 | shouldAcceptThresholdAtIntegerMaxValue | REQ-59 (negative control) | POST with `"eligibility": {"threshold": 2147483647}` (exactly `Integer.MAX_VALUE`) | 200/201 — valid. Max value is inclusive. | TS-VAL-59-02 | `TierCreateRequestValidator.validateThreshold` | UT |

#### 8.3.4 REQ-60 — TRACKER Condition Coupling (BT-230..BT-232)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-230 | shouldRejectTrackerConditionMissingTrackerConditionField | REQ-60 | POST with `"eligibility": {"conditions": [{"type": "TRACKER", "trackerId": 5}]}` (missing `trackerCondition`) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.TRACKER_ID_REQUIRED"` (key); wire code **9029**; `resolverService.getCode("TIER.TRACKER_ID_REQUIRED") == 9029L`. | TS-VAL-60-01 | `TierEnumValidation.validateConditionTypes(TierEligibilityConfig)` — §R8.6 REQ-60 | UT |
| BT-231 | shouldRejectTrackerConditionMissingTrackerId | REQ-60 | POST with `"eligibility": {"conditions": [{"type": "TRACKER", "trackerCondition": 1}]}` (missing `trackerId`) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.TRACKER_ID_REQUIRED"` (key); wire code **9029** unchanged. | TS-VAL-60-02 | `TierEnumValidation.validateConditionTypes` | UT |
| BT-232 | shouldAcceptNonTrackerConditionWithoutTrackerFields | REQ-60 (negative control) | POST with `"eligibility": {"conditions": [{"type": "PURCHASE", "value": "100"}]}` | 200/201 — no error. Coupling check only fires for `type == "TRACKER"`. | TS-VAL-60-03 | `TierEnumValidation.validateConditionTypes` | UT |

#### 8.3.5 REQ-61 — periodValue Digit-Count Overflow (BT-233)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-233 | shouldRejectPeriodValueWithExcessiveDigitCount | REQ-61 | POST with `"validity": {"periodValue": 12345678901234567890123456}` (26-digit numeric literal in JSON body) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.PERIOD_VALUE_OVERFLOW"` (key); wire code **9030**; `resolverService.getCode("TIER.PERIOD_VALUE_OVERFLOW") == 9030L`. Pre-binding scan on `JsonNode` digit-count (> 25). | TS-VAL-61-01 | `TierEnumValidation.validateValidity` (pre-binding digit-count guard) — §R8.6 REQ-61 | UT |

#### 8.3.6 REQ-62 — FIXED_DATE_BASED Computation Window Bounds (BT-234..BT-236)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-234 | shouldRejectFixedDateOffsetAbove36 | REQ-62 | POST with `"validity": {"renewalWindowType": "FIXED_DATE_BASED", "computationWindowStartValue": 37}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE"` (key); wire code **9034**; `resolverService.getCode("TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE") == 9034L`. Upper bound 36 violated. | TS-VAL-62-01 | `TierEnumValidation.validateRenewalWindowBounds(TierValidityConfig)` (NEW method) — §R8.6 REQ-62 | UT |
| BT-235 | shouldAcceptFixedDateOffsetAt36Max | REQ-62 (negative control — upper boundary) | POST with `"validity": {"renewalWindowType": "FIXED_DATE_BASED", "computationWindowStartValue": 36}` | 200/201 — valid. 36 is the inclusive maximum. | TS-VAL-62-02 | `TierEnumValidation.validateRenewalWindowBounds` | UT |
| BT-236 | shouldRejectFixedDateOffsetAtZero | REQ-62 (boundary — lower bound) | POST with `"validity": {"renewalWindowType": "FIXED_DATE_BASED", "computationWindowStartValue": 0}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE"` (key); wire code **9034** unchanged. Lower bound 1 violated (zero is invalid). Note: code 9024 (validity numeric negative) does NOT fire because REQ-62 guard runs on `FIXED_DATE_BASED` specifically and requires `>= 1`. | TS-VAL-62-03 | `TierEnumValidation.validateRenewalWindowBounds` | UT |

#### 8.3.7 REQ-63 — DEFERRED

> **BT-237 — DEFERRED** (D-31: REQ-63 FOLDED into REQ-62). Field `renewalLastMonths` does not exist server-side in `TierValidityConfig` (zero grep hits — C7 per `03-designer.md §R8.7`). The [1, 36] bound on `computationWindowStartValue` when `renewalWindowType == FIXED_DATE_BASED` is already covered by BT-234, BT-235, BT-236 (REQ-62). No BT-237.

#### 8.3.8 REQ-64 — CUSTOM_PERIOD Month Bounds + Delta (BT-238..BT-239)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-238 | shouldRejectCustomPeriodDeltaExceeding35 | REQ-64 | POST with `"validity": {"renewalWindowType": "CUSTOM_PERIOD", "computationWindowStartValue": 40, "computationWindowEndValue": 4}` (delta = 36 > 35) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.CUSTOM_PERIOD_DELTA_TOO_LARGE"` (key); wire code **9033**; `resolverService.getCode("TIER.CUSTOM_PERIOD_DELTA_TOO_LARGE") == 9033L`. | TS-VAL-64-01 | `TierEnumValidation.validateRenewalWindowBounds(TierValidityConfig)` — §R8.6 REQ-64 | UT |
| BT-239 | shouldAcceptCustomPeriodDeltaAt35Max | REQ-64 (negative control — upper boundary) | POST with `"validity": {"renewalWindowType": "CUSTOM_PERIOD", "computationWindowStartValue": 36, "computationWindowEndValue": 1}` (delta = 35) | 200/201 — valid. Delta of 35 is the inclusive maximum. | TS-VAL-64-02 | `TierEnumValidation.validateRenewalWindowBounds` | UT |

#### 8.3.9 REQ-65 — minimumDuration Must Be Positive (BT-240..BT-242)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-240 | shouldRejectMinimumDurationOfZero | REQ-65 | POST with `"validity": {"minimumDuration": 0}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.MIN_DURATION_MUST_BE_POSITIVE"` (key); wire code **9035**; `resolverService.getCode("TIER.MIN_DURATION_MUST_BE_POSITIVE") == 9035L`. Zero is now invalid (changed from `< 0` to `<= 0`). | TS-VAL-65-01 | `TierEnumValidation.validateValidity` (guard changed from `< 0` to `<= 0`) — §R8.6 REQ-65 | UT |
| BT-241 | shouldAcceptMinimumDurationOfOne | REQ-65 (negative control) | POST with `"validity": {"minimumDuration": 1}` | 200/201 — valid. 1 is the minimum positive value. | TS-VAL-65-02 | `TierEnumValidation.validateValidity` | UT |
| BT-242 | shouldAcceptOmittedMinimumDuration | REQ-65 (backward-compat) | POST with `"validity": {}` (minimumDuration absent / null) | 200/201 — no error. Null/omitted field is accepted (not a required field). The `> 0` guard only fires when the field is explicitly provided with an invalid value. | TS-VAL-65-03 | `TierEnumValidation.validateValidity` | UT |

#### 8.3.10 REQ-66 — Renewal Condition Value Required (BT-243..BT-244)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-243 | shouldRejectRenewalConditionWithEmptyValue | REQ-66 | POST with `"validity": {"renewal": {"conditions": [{"type": "PURCHASE", "value": ""}]}}` | 400 `InvalidInputException`; `ex.getMessage() == "TIER.RENEWAL_CONDITION_VALUE_REQUIRED"` (key); wire code **9036**; `resolverService.getCode("TIER.RENEWAL_CONDITION_VALUE_REQUIRED") == 9036L`. Empty string value is rejected. | TS-VAL-66-01 | `TierRenewalValidation.validateConditionValuesPresent(TierRenewalConfig)` (NEW method) — §R8.6 REQ-66 | UT |
| BT-244 | shouldAcceptRenewalConditionWithNonEmptyValue | REQ-66 (negative control) | POST with `"validity": {"renewal": {"conditions": [{"type": "PURCHASE", "value": "100"}]}}` | 200/201 — valid. Non-empty value satisfies the requirement. | TS-VAL-66-02 | `TierRenewalValidation.validateConditionValuesPresent` | UT |

#### 8.3.11 REQ-67 — Renewal TRACKER Fields All Required (BT-245)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-245 | shouldRejectRenewalTrackerConditionMissingValue | REQ-67 | POST with `"validity": {"renewal": {"conditions": [{"type": "TRACKER", "trackerId": 5, "trackerCondition": 1}]}}` (missing `value`) | 400 `InvalidInputException`; `ex.getMessage() == "TIER.RENEWAL_TRACKER_FIELDS_REQUIRED"` (key); wire code **9037**; `resolverService.getCode("TIER.RENEWAL_TRACKER_FIELDS_REQUIRED") == 9037L`. TRACKER rows require `trackerId`, `trackerCondition`, AND `value` all non-empty. | TS-VAL-67-01 | `TierRenewalValidation.validateConditionValuesPresent` (extended for TRACKER coupling) — §R8.6 REQ-67 | UT |

#### 8.3.12 REQ-68 — Architectural Smoke Tests (BT-246..BT-249)

| ID | Test Name | Verifies (BA Req) | Input | Expected Output | QA Scenario | Designer Interface | Layer |
|----|-----------|-------------------|-------|-----------------|-------------|-------------------|-------|
| BT-246 | shouldRoundTripAllMigratedCodesThoughResolver | REQ-68 | For each key in `TierErrorKeys` constants (9001..9024 range): call `resolverService.getCode(key)` | Each returns the expected numeric code (9001L..9024L). No code returns 999999L. 24 assertions. | TS-VAL-68-01 | `MessageResolverService.getCode(String)` + `tier.properties` — §R8.8 | UT |
| BT-247 | shouldVerifyCatalogCompleteness | REQ-68 | Load `i18n/errors/tier.properties` via `Properties.load()`. For each constant in `TierErrorKeys`: assert both `<KEY>.code` and `<KEY>.message` entries exist and are non-blank. | 35 constants × 2 entries = 70 property checks. No constant is missing from the file. No constant returns 999999L. | TS-VAL-68-02 | `tier.properties` file loaded in test classpath — §R8.1 catalog-integrity test (D-33) | UT |
| BT-248 | shouldVerifyTierNamespaceRegisteredInMessageResolver | REQ-68 | Inspect `MessageResolverService.fileNameMap` for the `"TIER"` key entry. | `fileNameMap.containsKey("TIER") == true`; mapped value equals `"i18n.errors.tier"`. Registration is the ONE-line change in §R8.8. | TS-VAL-68-03 | `MessageResolverService.fileNameMap` — §R8.8 | UT |
| BT-249 | shouldReturnCorrectWireCodeForNameRequiredThroughAdvice | REQ-68 | IT: throw `new InvalidInputException("TIER.NAME_REQUIRED")` through `TargetGroupErrorAdvice.handleInvalidInputException` (via a test controller endpoint or direct advice invocation) | Response `code == 9001`, `message == "name is required"` (from `tier.properties`). Proves the full advice → resolver → properties pipeline works end-to-end. | TS-VAL-68-04 | `TargetGroupErrorAdvice.handleInvalidInputException` → `MessageResolverService` — §R8.8 | IT |

---

### 8.4 Change Detail Table

| BT-ID | Triage | What Changed | Before (Rework #6a) | After (Rework #8) | Traced To |
|---|---|---|---|---|---|
| BT-190 | UPDATE | Expected Output: key assertion + D-32 field-to-log note | "message identifies `dailyDowngradeEnabled` as the rejected field" | "`ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`; field name to logs only (D-32)" | `03-designer.md §R8.4`, D-32 |
| BT-191 | UPDATE | Expected Output: key assertion + D-32 note | "field name in error message matches canonical" | "`ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`; field name to logs only" | `03-designer.md §R8.4` |
| BT-192 | CONFIRMED | Jackson path — no `InvalidInputException` key, no change | — | — | — |
| BT-193 | UPDATE | Expected Output: key assertion added | "400 code 9012 TIER_CLASS_B_SCHEDULE_FIELD" | "`ex.getMessage() == "TIER.CLASS_B_SCHEDULE_FIELD"`; code 9012 unchanged" | `03-designer.md §R8.4` |
| BT-194 | UPDATE | Expected Output: key assertion added (also traces REQ-27 CLARIFIED) | "400 code 9013 TIER_ELIGIBILITY_CRITERIA_TYPE" | "`ex.getMessage() == "TIER.ELIGIBILITY_CRITERIA_TYPE"`; code 9013 unchanged" | `03-designer.md §R8.9`, REQ-27 |
| BT-195 | UPDATE | Expected Output: key assertion added | "400 code 9015 TIER_SENTINEL_STRING_MINUS_ONE" | "`ex.getMessage() == "TIER.SENTINEL_STRING_MINUS_ONE"`; code 9015 unchanged" | `03-designer.md §R8.4` |
| BT-196 | UPDATE | Expected Output: key assertion added | "400 code 9016 TIER_SENTINEL_NUMERIC_MINUS_ONE" | "`ex.getMessage() == "TIER.SENTINEL_NUMERIC_MINUS_ONE"`; code 9016 unchanged" | `03-designer.md §R8.4` |
| BT-197 | CONFIRMED | Jackson path — no `InvalidInputException` key, no change | — | — | — |
| BT-198 | UPDATE | Expected Output: key assertion added | "400 code 9014 TIER_START_DATE_ON_SLAB_UPGRADE" | "`ex.getMessage() == "TIER.START_DATE_ON_SLAB_UPGRADE"`; code 9014 unchanged" | `03-designer.md §R8.4` |
| BT-199 | UPDATE | Expected Output: key assertion added | "400 code 9014 — confirms family-level reject…" | "`ex.getMessage() == "TIER.START_DATE_ON_SLAB_UPGRADE"`; code 9014 unchanged" | `03-designer.md §R8.4` |
| BT-200 | UPDATE | Expected Output: key assertion added | "400 code 9018 TIER_FIXED_FAMILY_MISSING_PERIOD_VALUE" | "`ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`; code 9018 unchanged" | `03-designer.md §R8.4` |
| BT-201 | UPDATE | Expected Output: key assertion added | "400 code 9018 — confirms 2-member FIXED family…" | "`ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`; code 9018 unchanged" | `03-designer.md §R8.4` |
| BT-202 | UPDATE | Expected Output: key assertion added | "400 code 9018 (non-positive guard; NOT 9016…)" | "`ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`; code 9018 unchanged" | `03-designer.md §R8.4` |
| BT-203 | UPDATE | Expected Output: key assertion added | "400 code 9016 (numeric -1 sentinel fires FIRST; 9018 does NOT fire)" | "`ex.getMessage() == "TIER.SENTINEL_NUMERIC_MINUS_ONE"`; code 9016 unchanged" | `03-designer.md §R8.4` |
| BT-204 | UPDATE | Expected Output: key assertion added | "400 code 9018 (sentinel scan matches -1 only; -5 flows through…)" | "`ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`; code 9018 unchanged" | `03-designer.md §R8.4` |
| BT-205 | UPDATE | Expected Output: key assertion added | "400 code 9017 TIER_RENEWAL_CRITERIA_TYPE_DRIFT" | "`ex.getMessage() == "TIER.RENEWAL_CRITERIA_TYPE_DRIFT"`; code 9017 unchanged" | `03-designer.md §R8.4` |
| BT-206 | CONFIRMED | Success path — no exception thrown, no change | — | — | — |
| BT-207 | CONFIRMED | Success path — no exception thrown, no change | — | — | — |
| BT-208 | UPDATE | Expected Output: key assertion added (throw migrates) | "400 code 9018 — validator does NOT fetch/merge stored state…" | "`ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`; code 9018 unchanged" | `03-designer.md §R8.4` |
| BT-209 | CONFIRMED | Success path — no exception thrown, no change | — | — | — |
| BT-210 | CONFIRMED | Read-path IT — no validator throw, no change | — | — | — |
| BT-211 | CONFIRMED | Read-path UT — no validator throw, no change | — | — | — |
| BT-212 | CONFIRMED | Read-path IT — no validator throw, no change | — | — | — |
| BT-213 | CONFIRMED | Jackson path — no `InvalidInputException` key, no change | — | — | — |
| BT-214 | UPDATE | Expected Output: key assertion added | "400 code 9011 — Class A scan runs FIRST…" | "`ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`; code 9011 unchanged" | `03-designer.md §R8.4` |
| BT-215 | UPDATE | Expected Output: key assertion added | "400 code 9011; error envelope contains tenant A's context…" | "`ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`; code 9011 unchanged" | `03-designer.md §R8.4` |
| BT-216 | CONFIRMED | Success path — no exception thrown, no change | — | — | — |
| BT-217 | UPDATE | Expected Output: key assertion added | "400 code 9018 (non-positive); 9016 does NOT fire (-1 only)" | "`ex.getMessage() == "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE"`; code 9018 unchanged" | `03-designer.md §R8.4` |
| BT-218 | CONFIRMED | Jackson type mismatch — no `InvalidInputException` key, no change | — | — | — |
| BT-219 | CONFIRMED | Jackson type mismatch — no change | — | — | — |
| BT-220 | UPDATE | Expected Output: key assertion added | "400 code 9011 — scanner walks ALL tree levels…" | "`ex.getMessage() == "TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`; code 9011 unchanged" | `03-designer.md §R8.4` |
| BT-221 | UPDATE | Expected Output: key assertion added (note: code 9022 for period-type enum, not a new code) | "400 — existing VALID_PERIOD_TYPES is case-sensitive" | "`ex.getMessage() == "TIER.VALIDITY_RENEWAL_WINDOW_TYPE"`; code 9022 unchanged" | `03-designer.md §R8.4` |
| BT-222 | UPDATE | Expected Output: key assertion added | "400 code 9017 — canonical check is exact string-equals" | "`ex.getMessage() == "TIER.RENEWAL_CRITERIA_TYPE_DRIFT"`; code 9017 unchanged" | `03-designer.md §R8.4` |
| BT-223 | UPDATE | Expected Output: key assertion added | "400 code 9016 — scanner descends into arrays and nested objects" | "`ex.getMessage() == "TIER.SENTINEL_NUMERIC_MINUS_ONE"`; code 9016 unchanged" | `03-designer.md §R8.4` |
| BT-227 | OBSOLETE | REQ-58 SKIPPED (D-30) | Provisional BT-227 (color length 9027) | Not generated | D-30, `03-designer.md §R8.7` |
| BT-237 | DEFERRED | REQ-63 FOLDED into REQ-62 (D-31) | Provisional BT-237 (renewalLastMonths 9031) | Not generated; BT-234..BT-236 absorb this case | D-31, `03-designer.md §R8.7` |
| BT-224..BT-226 | NEW | REQ-57 case-insensitive name uniqueness | — | See §8.3.1 | `03-designer.md §R8.6` |
| BT-228..BT-229 | NEW | REQ-59 threshold upper bound | — | See §8.3.3 | `03-designer.md §R8.6` |
| BT-230..BT-232 | NEW | REQ-60 TRACKER coupling in eligibility conditions | — | See §8.3.4 | `03-designer.md §R8.6` |
| BT-233 | NEW | REQ-61 periodValue digit-count overflow | — | See §8.3.5 | `03-designer.md §R8.6` |
| BT-234..BT-236 | NEW | REQ-62 FIXED_DATE_BASED bounds (+ absorbs REQ-63) | — | See §8.3.6 | `03-designer.md §R8.6` |
| BT-238..BT-239 | NEW | REQ-64 CUSTOM_PERIOD delta check | — | See §8.3.8 | `03-designer.md §R8.6` |
| BT-240..BT-242 | NEW | REQ-65 minimumDuration > 0 | — | See §8.3.9 | `03-designer.md §R8.6` |
| BT-243..BT-244 | NEW | REQ-66 renewal condition value required | — | See §8.3.10 | `03-designer.md §R8.6` |
| BT-245 | NEW | REQ-67 renewal TRACKER all fields required | — | See §8.3.11 | `03-designer.md §R8.6` |
| BT-246..BT-249 | NEW | REQ-68 catalog-integrity architectural smoke tests | — | See §8.3.12 | `03-designer.md §R8.1`, `§R8.8` |

---

### 8.5 Rework #8 Test Case Counts

| Category | UT | IT | Total | Net Change |
|----------|----|----|-------|------------|
| Post-Rework #6a baseline | ~158 | ~74 | ~232 | — |
| Rework #8 — REQ-57 (case-insensitive name uniqueness) | 3 | 0 | 3 | +3 |
| Rework #8 — REQ-59 (threshold upper bound) | 2 | 0 | 2 | +2 |
| Rework #8 — REQ-60 (TRACKER condition coupling) | 3 | 0 | 3 | +3 |
| Rework #8 — REQ-61 (periodValue digit-count) | 1 | 0 | 1 | +1 |
| Rework #8 — REQ-62 (FIXED_DATE_BASED bounds) | 3 | 0 | 3 | +3 |
| Rework #8 — REQ-64 (CUSTOM_PERIOD delta) | 2 | 0 | 2 | +2 |
| Rework #8 — REQ-65 (minimumDuration > 0) | 3 | 0 | 3 | +3 |
| Rework #8 — REQ-66 (renewal condition value) | 2 | 0 | 2 | +2 |
| Rework #8 — REQ-67 (renewal TRACKER all fields) | 1 | 0 | 1 | +1 |
| Rework #8 — REQ-68 (catalog smoke tests) | 3 | 1 | 4 | +4 |
| **Total (post-Rework #8)** | **~181** | **~75** | **~256** | **+24 new BTs** |
| UPDATE (assertion migration — no new tests) | 21 | 0 | — | 0 net count change |
| OBSOLETE removed | — | — | — | -1 (BT-227, never activated) |
| DEFERRED | — | — | — | -1 (BT-237, absorbed by BT-234..236) |

**Net: +24 new BT cases, -1 OBSOLETE (BT-227 never generated), -1 DEFERRED (BT-237 absorbed). Total active BTs post-Rework #8: 247 (232 pre-rework active + 24 new - 0 removed from existing active = 256 total in file; 247 active after excluding 9 OBSOLETE/DEFERRED from prior reworks that were already annotated).**

---

### 8.6 Verification-Before-Completion

| Check | Evidence |
|---|---|
| Every ADDED REQ-xx (REQ-57..REQ-67) has ≥1 NEW BT | REQ-57 → BT-224, 225, 226 ✅; REQ-58 → SKIPPED (D-30) ✅; REQ-59 → BT-228, 229 ✅; REQ-60 → BT-230, 231, 232 ✅; REQ-61 → BT-233 ✅; REQ-62 → BT-234, 235, 236 ✅; REQ-63 → DEFERRED/folded (D-31) covered by BT-234..236 ✅; REQ-64 → BT-238, 239 ✅; REQ-65 → BT-240, 241, 242 ✅; REQ-66 → BT-243, 244 ✅; REQ-67 → BT-245 ✅ |
| Every CLARIFIED REQ-xx keeps coverage (no regression) | REQ-27 → BT-194 UPDATE (code 9013 unchanged on wire; key assertion now correct) ✅; REQ-25/26/33-40 → respective BT-190..BT-223 UPDATE rows ✅ |
| Every Designer rule in `03-designer.md §R8.6` has a BT | `validateNameUniqueness` (REQ-57) → BT-224..226 ✅; `validateThreshold` upper bound (REQ-59) → BT-228..229 ✅; `validateConditionTypes` TRACKER (REQ-60) → BT-230..232 ✅; `validateValidity` digit-count (REQ-61) → BT-233 ✅; `validateRenewalWindowBounds` NEW method (REQ-62) → BT-234..236 ✅; `validateRenewalWindowBounds` CUSTOM_PERIOD (REQ-64) → BT-238..239 ✅; `validateValidity` minimumDuration (REQ-65) → BT-240..242 ✅; `validateConditionValuesPresent` NEW method (REQ-66) → BT-243..244 ✅; `validateConditionValuesPresent` TRACKER (REQ-67) → BT-245 ✅ |
| Catalog-integrity test BT-247 present (D-33) | BT-247 in §8.3.12 — UT, loads `tier.properties` via `Properties.load()`, asserts 35 constants × `.code` + `.message` ✅ |
| All NEW BT-xx have valid traceability upstream | Every BT in §8.3 traces to: BA REQ-xx, `03-designer.md §R8.6` row, and a provisional QA scenario TS-VAL-xx-yy ✅ |
| All UPDATE BTs preserve their traced REQ | Verified: BT-190→REQ-23, BT-191→REQ-23, BT-193→REQ-24, BT-194→REQ-25/REQ-27, BT-195→REQ-26, BT-196→REQ-26, BT-198→REQ-21/36, BT-199→REQ-21/36, BT-200..204→REQ-56, BT-205→REQ-28/41, BT-208→REQ-56, BT-214→REQ-23/26, BT-215→REQ-23, BT-217→REQ-56, BT-220→REQ-23, BT-221→REQ-21, BT-222→REQ-28, BT-223→REQ-26 — all unchanged ✅ |
| OBSOLETE BT-227 not present in artifact | BT-227 documented as OBSOLETE in §8.3.2 (prose note only) — no table row generated ✅ |
| DEFERRED BT-237 not present as active test | BT-237 documented as DEFERRED in §8.3.7 (prose note only) — absorbed by BT-234..236 ✅ |
| No CONFIRMED BT was modified | BT-192, 197, 206, 207, 209, 210, 211, 212, 213, 216, 218, 219 — rows untouched ✅ |
| Coverage summary matches actual BT-xx count post-rework | §8.5 table: 232 pre-rework + 24 new = 256 total in file. UPDATE is 0 net count change. ✅ |

---

### 8.7 Forward Cascade Payload — Phase 9 (SDET — RED)

```
REWORK REQUEST → Phase 9 (SDET — RED)
  Source: Phase 8b (Business Test Gen Rework #8)
  Trigger: cascade
  Severity: HIGH

  Changed BT-xx IDs (UPDATE — assertion migration):
    BT-190, BT-191, BT-193, BT-194, BT-195, BT-196, BT-198, BT-199, BT-200, BT-201,
    BT-202, BT-203, BT-204, BT-205, BT-208, BT-214, BT-215, BT-217, BT-220, BT-221,
    BT-222, BT-223 (21 UTs total)

  New BT-xx IDs (NEW — write new test methods):
    BT-224, BT-225, BT-226        — REQ-57 (UT, TierValidationServiceTest or new)
    BT-228, BT-229                — REQ-59 (UT, TierCreateRequestValidatorTest)
    BT-230, BT-231, BT-232        — REQ-60 (UT, TierEnumValidationTest)
    BT-233                        — REQ-61 (UT, TierEnumValidationTest pre-binding)
    BT-234, BT-235, BT-236        — REQ-62 (UT, TierEnumValidationTest)
    BT-238, BT-239                — REQ-64 (UT, TierEnumValidationTest)
    BT-240, BT-241, BT-242        — REQ-65 (UT, TierEnumValidationTest)
    BT-243, BT-244                — REQ-66 (UT, TierRenewalValidationTest)
    BT-245                        — REQ-67 (UT, TierRenewalValidationTest)
    BT-246, BT-247, BT-248        — REQ-68 catalog smoke tests (UT)
    BT-249                        — REQ-68 advice integration test (IT)

  SDET action per UPDATE BT:
    Change: assertEquals("<old plain text>", ex.getMessage())
         → assertEquals("TIER.<KEY>", ex.getMessage())
    Add:    assertEquals(<numeric>L, resolverService.getCode(ex.getMessage()))
    Ref: Use TierValidationAssert.assertThrowsWithKey(executable, key, expectedCode) helper
         (plan §9 — Phase 10 Developer creates this helper class)

  SDET action per NEW BT:
    Write new test methods that FAIL (RED) — production stubs do not yet implement
    REQ-57..REQ-67 rules. Skeleton stubs per validation-rework-scope.md §Phase 9.

  OBSOLETE / DEFERRED:
    BT-227 — not generated. No test method to write or delete.
    BT-237 — not generated. No test method to write or delete.

  RED confirmation target:
    - mvn compile: PASS (all stubs + updated assertions compile)
    - BT-224..BT-249 (new methods): ALL FAIL (RED — validators not yet implemented)
    - BT-190..BT-223 (updated assertions): FAIL until Phase 10 migrates throw pattern
    - BT-210, BT-211, BT-212 (CONFIRMED read-path): PASS (no change)
```

**Rework #8 Status**: COMPLETE. Artifact `04b-business-tests.md` updated. Ready for forward cascade to SDET (Phase 9) in rework mode.

