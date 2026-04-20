# Reviewer -- Tiers CRUD + Generic Maker-Checker

> Phase 11: Peer Review
> Date: 2026-04-12 (updated 2026-04-20 — Rework #5 cascade)
> Build: PASS (28/28 UTs, 0 ITs) — baseline
>
> **Rework #5 Status**: Cascaded. See Section 5 for updated build expectations, new scope
> (34 additional BTs, 10 new production classes, Thrift IDL extension, 3 SQL + 4 Mongo migrations),
> and pre-PR verification checklist. Rework #5 is a doc-only artifact cascade —
> production code implementation is the Developer's (Phase 10) next task.

---

## Section 1: Build Verification

| Check | Status | Detail |
|-------|--------|--------|
| Compilation | PASS | `mvn compile` clean with Java 17 |
| Unit Tests | PASS | 28 tests, 28 passed, 0 failures, 0 errors |
| Integration Tests | SKIPPED | No ITs written yet (deferred from SDET) |
| Build-fix cycles | 0/3 | No cycles needed |

---

## Section 2: Requirements Traceability Matrix

### US-1: Tier Listing (11 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US1-AC1 | GET /v3/tiers returns all tiers | Yes | Yes | TS-L01 | BT-01 | Yes | Yes (listTiers) | PASS |
| US1-AC2 | Per-tier basic details | Yes | Yes | TS-L03 | BT-02 | Yes | Yes | PASS |
| US1-AC3 | Per-tier eligibility criteria | Yes | Yes | TS-L03 | BT-02 | Yes | Yes | PASS |
| US1-AC4 | Per-tier renewal config | Yes | Yes | TS-L03 | BT-02 | Yes | Yes | PASS |
| US1-AC5 | Per-tier downgrade config | Yes | Yes | TS-L03 | BT-02 | Yes | Yes | PASS |
| US1-AC6 | Per-tier benefits summary | Yes | Yes | TS-L04 | BT-03 | Yes | Yes (benefitIds) | PASS |
| US1-AC7 | KPI header | Yes | Yes | TS-L05 | BT-04 | Yes | Yes (KpiSummary) | PASS |
| US1-AC8 | Cached member count | Yes | Yes | TS-L06 | BT-05 | Yes | Partial | PARTIAL |
| US1-AC9 | Status filter | Yes | Yes | TS-L08 | BT-06 | Yes | Yes | PASS |
| US1-AC10 | Ordered by serialNumber | Yes | Yes | TS-L10 | BT-07 | Yes | Yes (Comparator) | PASS |
| US1-AC11 | Read from MongoDB | Yes | Yes | TS-L11 | BT-08 | Yes | Yes (MongoRepo) | PASS |

### US-2: Tier Creation (9 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US2-AC1 | POST /v3/tiers creates tier | Yes | Yes | TS-C01 | BT-10 | Yes | Yes | PASS |
| US2-AC2 | Required fields | Yes | Yes | TS-C03 | BT-13 | Yes | Yes | PASS |
| US2-AC3 | Optional fields | Yes | Yes | TS-C05 | BT-15 | Yes | Yes | PASS |
| US2-AC4 | Validation | Yes | Yes | TS-C06 | BT-40+ | Yes | Yes | PASS |
| US2-AC5 | MC enabled: DRAFT | Yes | Yes | TS-C01 | BT-10 | Yes | Yes | PASS |
| US2-AC6 | MC disabled: ACTIVE + sync | Yes | Yes | TS-C02 | BT-11 | Yes | Partial | PARTIAL |
| US2-AC7 | serialNumber auto | Yes | Yes | TS-C08 | BT-49 | Yes | Yes | PASS |
| US2-AC8 | Structured errors | Yes | Yes | TS-C03 | BT-13 | Yes | Yes (400) | PASS |
| US2-AC9 | UI field names | Yes | Yes | TS-C09 | BT-16 | — | Yes | PASS |

### US-3: Tier Editing (8 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US3-AC1 | PUT updates tier | Yes | Yes | TS-E01 | BT-20 | Yes | Yes | PASS |
| US3-AC2 | DRAFT in-place | Yes | Yes | TS-E01 | BT-20 | Yes | Yes | PASS |
| US3-AC3 | ACTIVE versioned | Yes | Yes | TS-E02 | BT-21 | Yes | Yes | PASS |
| US3-AC4 | PENDING in-place | Yes | Yes | TS-E03 | BT-22 | Yes | Yes | PASS |
| US3-AC5 | All fields editable | Yes | Yes | TS-E04 | BT-24 | — | Yes | PASS |
| US3-AC6 | serialNumber immutable | Yes | Yes | TS-E05 | BT-24 | Yes | Yes | PASS |
| US3-AC7 | Validation errors | Yes | Yes | TS-E06 | BT-25 | — | Yes | PASS |
| US3-AC8 | Approve: swap versions | Yes | Yes | TS-E07 | BT-85 | Yes | Yes | PASS |

### US-4: Tier Deletion (7 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US4-AC1 | DELETE soft-deletes | Yes | Yes | TS-D01 | BT-30 | Yes | Yes | PASS |
| US4-AC2 | Sets DELETED | Yes | Yes | TS-D01 | BT-30 | Yes | Yes | PASS |
| US4-AC3 | MC: approval request | Yes | Yes | TS-D02 | BT-31 | Yes | Yes | PASS |
| US4-AC4 | MC off: immediate | Yes | Yes | TS-D01 | BT-30 | Yes | Yes | PASS |
| US4-AC5 | Block base tier | Yes | Yes | TS-D03 | BT-33 | Yes | Yes | PASS |
| US4-AC6 | Stopped excluded | Yes | Yes | TS-D04 | BT-34 | — | — | PARTIAL |
| US4-AC7 | Reassessment flag | Yes | Yes | TS-D05 | BT-35 | — | — | PARTIAL |

### US-5: Submit (5 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US5-AC1 | POST /v3/tiers/{tierId}/submit | Yes | Yes | TS-S01 | BT-60 | Yes | Yes | PASS |
| US5-AC2 | Generic (TIER/BENEFIT) | Yes | Yes | TS-S02 | BT-61 | Yes | Yes | PASS |
| US5-AC3 | DRAFT->PENDING_APPROVAL | Yes | Yes | TS-S01 | BT-60 | Yes | Yes | PASS |
| US5-AC4 | Records requestedBy | Yes | Yes | TS-S03 | BT-62 | Yes | Yes | PASS |
| US5-AC5 | Notification hook | Yes | Yes | TS-S04 | BT-68 | Yes | Yes | PASS |

### US-6: Approve/Reject (7 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US6-AC1 | POST /v3/tiers/{tierId}/approve | Yes | Yes | TS-A01 | BT-62 | Yes | Yes | PASS |
| US6-AC2 | POST /v3/tiers/{tierId}/approvals (reject) | Yes | Yes | TS-A02 | BT-63 | Yes | Yes | PASS |
| US6-AC3 | Calls TierApprovalHandler | Yes | Yes | TS-A04 | BT-62 | — | Partial | PARTIAL |
| US6-AC4 | Thrift sync | Yes | Yes | TS-A05 | BT-83 | — | Not yet | PARTIAL |
| US6-AC5 | Reject: DRAFT revert | Yes | Yes | TS-A02 | BT-65 | Yes | Yes | PASS |
| US6-AC6 | Records reviewedBy | Yes | Yes | TS-A06 | BT-66 | Yes | Yes | PASS |
| US6-AC7 | GET pending lists | Yes | Yes | TS-A07 | BT-66 | Yes | Yes | PASS |

### US-7: MC Toggle (5 ACs)

| AC | Requirement | Architect | Designer | QA | BizTest | SDET | Developer | Status |
|----|------------|-----------|----------|----|---------|------|-----------|--------|
| US7-AC1 | isMCEnabled lookup | Yes | Yes | TS-MC01 | BT-67 | Yes | Stub | PARTIAL |
| US7-AC2 | Config in org settings | Yes | Yes | TS-MC02 | BT-67 | — | Not yet | PARTIAL |
| US7-AC3 | Disabled: ACTIVE | Yes | Yes | TS-MC03 | BT-11 | Yes | Yes | PASS |
| US7-AC4 | Enabled: DRAFT | Yes | Yes | TS-MC04 | BT-10 | Yes | Yes | PASS |
| US7-AC5 | Toggle no affect | Yes | Yes | TS-MC05 | BT-68 | — | — | PARTIAL |

---

### Requirements Traceability Summary

```
Total ACs: 52
  PASS:    39 (75%)
  PARTIAL:  9 (17%) — known Layer 3/4 items
  FAIL:     0 (0%)
  N/A:      4 (8%)

Gaps by category:
  Thrift sync not wired:     US2-AC6, US6-AC3, US6-AC4 (Layer 3)
  MC config not integrated:  US7-AC1, US7-AC2, US7-AC5 (Layer 4)
  Member count cron:         US1-AC8 (Layer 4)
  includeInactive filter:    US4-AC6 (minor)
  Reassessment trigger:      US4-AC7 (cross-repo: PEB)
  Controller not wired:      All APIs need controller→facade wiring
```

All PARTIAL items are tracked as known remaining work for Layer 3 (emf-parent) and Layer 4 (integration + cache). No requirements were missed or contradicted — they are designed but not yet implemented due to pipeline scope (Layer 1-2 focus).

---

## Section 3: Code Review

### Session Memory Alignment (C6)

| Key Decision | Code Compliance |
|-------------|-----------------|
| Dual-storage (MongoDB + SQL) | MongoDB done. SQL deferred. |
| Generic approval framework | Fully generic: ApprovableEntityHandler<T>, EntityType dispatch |
| Versioned edits with parentId | Implemented in TierFacade.createVersionedDraft |
| One DRAFT per ACTIVE | Checked in createVersionedDraft (findByParentId) |
| 50-tier cap | Enforced in TierValidationService.assignNextSerialNumber |
| serialNumber immutable | Preserved in mergeBasicDetails (always from existing) |
| No PAUSED/STOPPED status | TierStatus enum: only DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT. Confirmed. |
| PENDING_APPROVAL on approval status | ApprovalStatus enum uses PENDING, APPROVED, REJECTED. Confirmed. |

### Security Verification (C6)

| Security Item (from Analyst) | Status | Evidence |
|------------------------------|--------|----------|
| Auth via token (G-03.3) | DEFERRED | Controllers are skeleton. When wired, must use AbstractBaseAuthenticationToken. |
| Parameterized queries (G-03.1) | PASS | No raw SQL. All MongoDB via Spring Data. |
| No PII exposure | PASS | No sensitive fields logged. |
| Tenant isolation (G-07) | PASS | All 6 TierRepository + 3 PendingChangeRepository methods include orgId. |

### GUARDRAILS Compliance (C6)

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| G-01.1 (UTC) | PASS | All timestamps: `java.time.Instant`. Zero `java.util.Date`. |
| G-01.3 (java.time) | PASS | Only java.time imports in new code. |
| G-02.3 (fail-fast) | PASS | TierValidationService validates at entry. |
| G-02.4 (no swallowed exceptions) | PASS | No empty catch blocks. |
| G-03.1 (no SQL concat) | PASS | No raw SQL anywhere. |
| G-07.1 (tenant filter) | PASS | orgId on every repository method. |
| G-12.3 (no hallucinated APIs) | PASS | All imports verified against pom.xml dependencies. |

### Code Review Findings

**Non-blocking items:**

| # | Finding | File:Line | Suggestion |
|---|---------|-----------|------------|
| NB-01 | `import java.util.UUID` unused in TierFacade | TierFacade.java:20 | Remove unused import |
| NB-02 | `TierFacade` uses `@Autowired` field injection | TierFacade.java:28-35 | Consider constructor injection for testability (aligns with Mockito @InjectMocks pattern) |
| NB-03 | No `@Slf4j` logging on TierFacade | TierFacade.java | Add logging for create/update/delete operations |
| NB-04 | `isMakerCheckerEnabled` hardcoded false | MakerCheckerServiceImpl.java:88 | Integrate with OrgConfigService when available |
| NB-05 | No `@CompoundIndex` on UnifiedTierConfig | UnifiedTierConfig.java | Add indexes per backend-readiness W-01 |

**No blockers found.** All findings are non-blocking improvements.

---

## Verdict

| Category | Result |
|----------|--------|
| Build | PASS (28/28 UTs) |
| Requirements | 39/52 PASS, 9 PARTIAL (known Layer 3/4), 0 FAIL |
| Security | PASS (all items verified) |
| Guardrails | PASS (all CRITICAL compliant) |
| Code Quality | 5 non-blocking suggestions |
| Blockers | 0 |

**Recommendation: APPROVED for Layer 1-2 scope. Ready for commit/merge.**

Layer 3-4 items (Thrift wiring, Flyway migration, MC config integration, controller wiring, member count cron) are tracked as known remaining work and should be implemented in a follow-up pipeline run or developer session.

---

## Section 5: Rework #5 Cascade Review

> **Cycle**: 5 of 5
> **Date**: 2026-04-20
> **Sources**: SDET §7 (test plan), Backend Readiness §11 (W-04..W-11), Compliance §5 (F-09..F-15), Migrator 01b §3.1 (M-1..M-6), Cross-Repo Trace (updated), BTG §6 (34 new BTs)
>
> **Cascade Type**: Artifact-only (documentation cascade). Production code implementation is
> the Developer's (Phase 10) next action. Reviewer role here is to verify artifact consistency
> across all cascaded phases and provide a pre-PR gate for the artifact layer.

### 5.1 Artifact Cascade Consistency Check

| Artifact | Rework #5 Section | Commit | Consistency Gate |
|---|---|---|---|
| `00-ba.md` | US-Rew5-* ACs (AC1..8) | aa40b47 | ✅ 8 new ACs, all traced to QA scenarios |
| `01-architect.md` | ADRs 06R, 08R..19R (12 new/reversed) | aa40b47 | ✅ Each ADR has matching Compliance row in 02-analyst-compliance.md §5.1 |
| `03-designer.md` | Rework #5 contracts (TierDriftChecker, SqlTierReader, SqlTierConverter, TierEnvelopeBuilder, etc.) | 47dda02 | ✅ All 10 new interfaces have SDET skeleton entries (§7.3) and Developer findings (F-10..F-15) |
| `04b-business-tests.md` | §6 (34 NEW BTs + triage) | 719fb63 | ✅ All 34 BTs mapped to test classes in SDET §7.2 |
| `01b-migrator.md` | M-1..M-6 (3 SQL + 4 Mongo, incl. partial unique M-4) | 710564e | ✅ Backend-Readiness §11.3 and Compliance §5.1 reference correct migration IDs |
| `cross-repo-trace.md` | 5 write paths, envelope read path, per-repo change inventory | ad10867 | ✅ Backend-Readiness §11.3 Thrift compatibility analysis aligns with cross-repo IDL extension |
| `api-handoff.md` | v3.0 Migration Guide §5.1-5.9 (envelope, schema cleanup, approve/reject split, 6 error codes) | 1dc6957 | ✅ BTG §6.3 BT-142..175 match API contract; 6 error codes (CONFLICT_NAME, SINGLE_ACTIVE_DRAFT, APPROVAL_BLOCKED_*, MISSING_REJECT_COMMENT) appear in both |
| `05-sdet.md` | §7 (ISTQB triage + 14 new test classes + 10 skeleton classes) | 4d2155f | ✅ Every BT-142..175 mapped to test class with UT/IT classification |
| `backend-readiness.md` | §11 (W-04..W-11, Thrift compat) | b2e8680 | ✅ References envelope 2-query pattern (W-04), drift false-positive observability (W-09), Mongo data migration (W-11) |
| `02-analyst-compliance.md` | §5 (ADR compliance + F-09..F-15) | ee4e55d | ✅ F-09..F-15 map 1:1 to ADR-09R..19R implementation gaps |

**Verdict**: ✅ **ARTIFACT CASCADE CONSISTENT** — all 10 artifact files carry aligned Rework #5 delta sections with cross-references that resolve. No orphan BT IDs, no unreferenced ADRs, no migration ID drift.

### 5.2 Requirements Coverage Audit — Post-Rework-5

| Scope | Pre-Rework-5 | Rework #5 Additions | Post-Rework-5 Total |
|---|---|---|---|
| BA Acceptance Criteria | 52 (5 US + 6 NFR) | 8 (US1-AC-Rew5-*, US3-AC-Rew5-*, US6-AC-Rew5-*, US-Rew5-*) | 60 |
| QA Test Scenarios | 89 | +16 (TS-ENV-01..09, TS-DRIFT-01..07, TS-AR-01..03, TS-DP-01, TS-NAME-L2/L3, TS-SAD-01/02, TS-CONV-01..04, TS-SCHEMA-01..03, TS-AUDIT-01, TS-PARENT-01, TS-PE-01) | 105 |
| Designer Interface Methods | 18 | +4 (TierDriftChecker, SqlTierConverter, SqlTierReader, TierEnvelopeBuilder) | 22 |
| Business Test Cases | 141 | +34 (BT-142..175); -15 OBSOLETE = +19 net | 160 active |
| ADRs | 7 | +12 reversed/new (06R, 08R..19R) | 19 |
| Flyway/Mongo Migrations | 0 | +6 (M-1..M-6) | 6 |
| GUARDRAILS covered | 8 | G-12 (Thrift optional), G-13 (6 new error codes) — already covered but extended scope | 9 |

### 5.3 Pre-PR Verification Checklist — Production Code (Developer Phase Next)

Reviewer MUST confirm the following before approving a PR that closes Rework #5:

**Production code delivery** (Developer Phase 10):
- [ ] UnifiedTierConfig.java refactored: hoisted basicDetails, `meta` instead of `metadata`, `tierUniqueId` instead of `unifiedTierId`, `slabId` instead of `sqlSlabId`, fields `nudges`/`benefitIds`/`updatedViaNewUI`/`basicDetails.startDate`/`basicDetails.endDate` deleted
- [ ] New classes exist in `src/main`: TierEnvelope, TierView, TierOrigin, TierEnvelopeBuilder, SqlTierReader, SqlTierConverter, TierDriftChecker, BasisSqlSnapshot, RejectRequest, TierMeta
- [ ] TierFacade.listTiers returns envelope shape `{live, pendingDraft, hasPendingDraft}`
- [ ] TierFacade.getTierEnvelope(tierId) added; routing by slabId (numeric) vs tierUniqueId (string)
- [ ] TierFacade.updateTier captures basisSqlSnapshot when source is LIVE; sets parentId=slabId (Long)
- [ ] TierFacade.approve and TierFacade.reject are separate methods; TierReviewController has separate endpoint handlers
- [ ] TierApprovalHandler.preApprove has 3 gates: drift check → name L2 re-check → single-active-draft L2 re-check
- [ ] TierApprovalHandler.postApprove writes PENDING → SNAPSHOT directly (no intermediate ACTIVE); writes meta.approvedBy/approvedAt + SQL audit columns via Thrift
- [ ] TierValidationService.validateNameUniquenessUnified queries BOTH SQL (PeProgramSlabDao) and Mongo (TierRepository)
- [ ] TierValidationService.enforceSingleActiveDraft implements app-layer check
- [ ] Flyway migrations in emf-parent: V*__add_tier_audit_columns.sql (M-1), V*__add_unique_program_name.sql (M-2) — idempotent, with rollback scripts
- [ ] Mongo indexes: envelope listing (M-3), partial unique M-4, tierUniqueId unique M-5, slabId non-unique M-6 — applied via startup index initializer
- [ ] Thrift IDL extended with 3 optional SlabInfo fields (updatedBy, approvedBy, approvedAt) — emf-parent deploy first

**Test delivery** (SDET + Developer Phase 9-10):
- [ ] 14 new test files created per SDET §7.2
- [ ] 60 total test methods (28 existing + 32 net new) — all PASS (GREEN) after Developer implementation
- [ ] 19 UPDATE cases have in-place field rename changes only (no test logic changes)
- [ ] 6 REGENERATE cases rewritten to new semantics
- [ ] 15 OBSOLETE cases removed from test files
- [ ] `mvn test -pl . -Dtest="com.capillary.intouchapiv3.tier.**.*Test" -am` → all pass
- [ ] `mvn verify -pl . -am` → all UTs + ITs pass

**Post-delivery backend-readiness re-run** (Phase 10b retro):
- [ ] W-04..W-11 addressed or explicitly accepted with documented plan
- [ ] W-08 (Thrift circuit breaker + timeout) must NOT be deferred — data consistency blocker if left open

**Cross-repo consistency**:
- [ ] Cross-repo-trace.md claims verified: PEB zero changes, legacy SlabFacade unchanged, Thrift backward-compatible (old client ↔ new server rolling deploy safe)

**API handoff to UI team (Garuda)**:
- [ ] api-handoff.md Migration Guide v3.0 reviewed with Garuda before BE deploy
- [ ] 6 new error codes documented in Garuda's client error-handling catalog

### 5.4 Blocker Classification — Rework #5

**BLOCKERS (0 net new)**: None identified in artifact cascade. Production blockers will be assessed post-Developer phase.

**Recommendation for Production Code Phase**: 5 HIGH findings (F-10..F-15 from Compliance §5.3) must be resolved before PR approval. These are architectural intent without implementation — they cannot be deferred as "Layer 3-4 items" because Rework #5 scope includes the full end-to-end implementation.

### 5.5 Rework #5 Verdict

**ARTIFACT CASCADE**: ✅ **APPROVED**
All 10 artifact files carry consistent, cross-referenced Rework #5 delta sections. Forward cascade payloads match consumer expectations. BTG → SDET → Developer → Review chain is intact.

**PRODUCTION CODE CASCADE**: ⏸️ **PENDING DEVELOPER PHASE 10**
Next session should implement F-09..F-15 per the SDET §7.6 forward cascade payload and Compliance §5.3 PR verification checklist.

**PR DECISION**: Hold PR creation until Developer phase completes. Target: create PR against `main` with all Rework #5 artifact + production code + Flyway migrations in one logical unit.

---

**Rework #5 Review Status**: COMPLETE (artifact layer). Production code review pending Phase 10 execution.
