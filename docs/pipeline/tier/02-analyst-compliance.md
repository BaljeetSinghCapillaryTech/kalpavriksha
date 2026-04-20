# Compliance Analysis -- Tiers CRUD (Architecture vs Code)

> Phase 10c: Analyst --compliance
> Date: 2026-04-12 (updated 2026-04-20 — Rework #5 cascade)
> Intent: 01-architect.md, 03-designer.md, session-memory.md
> Reality: 39 production files in intouch-api-v3 (baseline) + Rework #5 requires 10 new production files + field renames across UnifiedTierConfig
>
> **Rework #5 Status**: Cascaded. See Section 5 for ADR-06R..16R compliance assessment
> (reversed and new ADRs), plus new findings F-09..F-15.

---

## Compliance Scorecard

| # | Architectural Decision / Contract | Compliance | Severity | Evidence |
|---|-----------------------------------|------------|----------|----------|
| ADR-01 | Dual-Storage (MongoDB + SQL) | PARTIAL | MEDIUM | MongoDB done (UnifiedTierConfig, PendingChange). SQL sync not yet wired (TierApprovalHandler throws for CREATE/DELETE). |
| ADR-02 | Generic MC Framework | COMPLIANT | — | ApprovableEntityHandler<T> interface, MakerCheckerService, PendingChange, EntityType enum all generic. |
| ~~ADR-03~~ | ~~Expand-Then-Contract Migration~~ | ~~NOT STARTED~~ — NOT NEEDED (Rework #3) | ~~HIGH~~ | ~~No Flyway migration script yet. ProgramSlab.status field not added to emf-parent.~~ Removed from scope — SQL only contains ACTIVE tiers. |
| ADR-04 | Versioned Edits with parentId | COMPLIANT | — | TierFacade.createVersionedDraft sets parentId, version+1. Version swap in TierApprovalHandler (new→ACTIVE, old→SNAPSHOT). |
| ADR-05 | Existing Thrift (No IDL Change) | PARTIAL | MEDIUM | TierApprovalHandler has comment for Thrift service but not wired. Wrapper methods not added to PointsEngineRulesThriftService. |
| ADR-06 | New Programs Only | COMPLIANT | — | No bootstrap sync code. New tier CRUD operates on MongoDB only. |
| ADR-07 | Atomic Thrift Call | NOT STARTED | MEDIUM | TierApprovalHandler doesn't call Thrift yet. When wired, must use single createSlabAndUpdateStrategies call. |

---

## Per-ADR Compliance Detail

### ADR-01: Dual-Storage — PARTIAL (C6)
- **MongoDB**: `UnifiedTierConfig` @Document(collection="unified_tier_configs") — COMPLIANT
- **MongoDB**: `PendingChange` @Document(collection="pending_changes") — COMPLIANT
- **SQL sync**: `TierApprovalHandler.publish()` throws `UnsupportedOperationException` for CREATE/DELETE — NOT YET IMPLEMENTED
- **Evidence**: `TierApprovalHandler.java:45` — `"Thrift sync not implemented — requires PointsEngineRulesThriftService wrapper (ADR-05)"`

### ADR-02: Generic MC — COMPLIANT (C7)
- `ApprovableEntityHandler<T>` generic interface with `EntityType getEntityType()` dispatch
- `MakerCheckerService` interface accepts any `EntityType`
- `PendingChange` stores `entityType` and `payload` (Object)
- `EntityType` enum: TIER, BENEFIT, SUBSCRIPTION — extensible

### ADR-03: Expand-Then-Contract — NOT NEEDED (Rework #3)
- ~~No Flyway migration V*.sql file found in emf-parent~~
- ~~`ProgramSlab.java` in emf-parent not modified (no `status` field added)~~
- ~~`PeProgramSlabDao.findActiveByProgram()` not added~~
- **Rework #3**: ADR-03 removed from scope entirely. SQL only contains ACTIVE tiers (synced via Thrift on approval). No ACTIVE tier can be deleted (DRAFT-only deletion). SlabInfo Thrift has no status field. ProgramSlab status column, findActiveByProgram(), and Flyway migration all unnecessary.

### ADR-04: Versioned Edits — COMPLIANT (C7)
- `TierFacade.updateTier()` — ACTIVE → `createVersionedDraft()` with parentId and version+1
- `TierFacade.createVersionedDraft()` — checks for existing DRAFT (one DRAFT per ACTIVE)
- `TierApprovalHandler.publish()` — UPDATE with parentId → old=SNAPSHOT, new=ACTIVE

### ADR-05: Existing Thrift — PARTIAL (C6)
- Comment in `TierApprovalHandler.java:18`: `// @Autowired private PointsEngineRulesThriftService thriftService;`
- Wrapper methods not yet added to `PointsEngineRulesThriftService` in intouch-api-v3
- **Expected** — Thrift wiring is Layer 3/4 work

### ADR-06: New Programs Only — COMPLIANT (C7)
- No bootstrap/sync code for existing programs. Clean separation.

### ADR-07: Atomic Thrift — NOT STARTED (C7)
- `@Lockable` not on `TierApprovalHandler.publish()` — flagged in backend-readiness W-02

---

## Interface Contract Compliance

| Interface (Designer) | Implementation | Match | Gap |
|---------------------|----------------|-------|-----|
| `TierFacade.listTiers(orgId, programId, statusFilter)` | Implemented | EXACT | — |
| `TierFacade.createTier(orgId, request, userId)` | Implemented | EXACT | — |
| `TierFacade.updateTier(orgId, tierId, request, userId)` | Implemented | EXACT | — |
| `TierFacade.deleteTier(orgId, tierId, userId)` | Implemented | EXACT | — |
| `TierFacade` dep: `StatusTransitionValidator` | NOT USED | MISMATCH | Designer prescribed StatusTransitionValidator; code uses switch statement instead. Low severity — behavior is correct. |
| `MakerCheckerService.submit(...)` | Implemented | EXACT | — |
| `MakerCheckerService.approve(...)` | Implemented | EXACT | — |
| `MakerCheckerService.reject(...)` | Implemented | EXACT | — |
| `MakerCheckerService.listPending(...)` | Implemented | EXACT | — |
| `MakerCheckerService.isMakerCheckerEnabled(...)` | Implemented (stub: returns false) | PARTIAL | Hardcoded false. Needs OrgConfig integration. |
| `ApprovableEntityHandler<T>.publish(change, orgId)` | Implemented (UPDATE only) | PARTIAL | CREATE/DELETE throw UnsupportedOperationException |
| `ApprovableEntityHandler<T>.getEntityType()` | Implemented | EXACT | — |
| `NotificationHandler` | Implemented (NoOp) | EXACT | — |
| `TierValidationService` | Implemented | EXACT | — |
| `TierRepository` (MongoRepository) | Implemented | EXACT | — |
| `PendingChangeRepository` | Implemented | EXACT | — |

---

## GUARDRAILS Compliance

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| G-01.1 (UTC storage) | COMPLIANT | All timestamps use `java.time.Instant`. Zero `java.util.Date` in new code. |
| G-01.3 (java.time) | COMPLIANT | Only `Instant` and `java.time` imports found. |
| G-02.3 (fail-fast validation) | COMPLIANT | `TierValidationService.validateCreate()` checks null at entry. |
| G-03.1 (no SQL concat) | COMPLIANT | No raw SQL in new code. All MongoDB via Spring Data repository. |
| G-03.3 (auth on endpoints) | NOT VERIFIED | Controllers are skeleton — auth wiring deferred. When wired, must use `AbstractBaseAuthenticationToken`. |
| G-05.4 (expand-then-contract) | NOT STARTED | Flyway migration not created yet. |
| G-06.1 (idempotency) | PARTIAL | `TierController` accepts `Idempotency-Key` header but logic not implemented. |
| G-07.1 (tenant filter) | COMPLIANT | All 6 TierRepository methods include `orgId` as first parameter. All 3 PendingChangeRepository methods include `orgId`. |
| G-07.4 (test isolation) | NOT TESTED | No tenant isolation IT exists yet. |

---

## TierStatus Enum Compliance

| Designer | Code | Match |
|----------|------|-------|
| DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, STOPPED, DELETED, SNAPSHOT | DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED, DELETED, SNAPSHOT | MISMATCH — `PAUSED` removed per user directive (Phase 7.5). Designer doc not updated. |

**Action**: Update `03-designer.md` Section 4 to remove PAUSED from TierStatus enum (already removed from api-handoff, architect, session-memory).

---

## Findings Summary

| # | Finding | Severity | Category | Action |
|---|---------|----------|----------|--------|
| F-01 | TierApprovalHandler: Thrift sync not wired (CREATE/DELETE) | MEDIUM | ADR-01, ADR-05, ADR-07 | Developer Layer 3: add wrapper methods, wire Thrift, add @Lockable |
| ~~F-02~~ | ~~Flyway migration not created (program_slabs.status)~~ | ~~HIGH~~ | ~~ADR-03~~ | ~~Developer Layer 3: create V*.sql in emf-parent~~ — NOT NEEDED (Rework #3) |
| F-03 | isMakerCheckerEnabled hardcoded false | MEDIUM | Interface contract | Developer: integrate with OrgConfig service |
| F-04 | StatusTransitionValidator not used | LOW | Interface contract | Code uses switch instead. Behavior correct. Refactor optional. |
| F-05 | Controllers not wired to facades | MEDIUM | Not functional | Developer: wire REST → Facade, add exception handlers |
| F-06 | PAUSED still in designer TierStatus | LOW | Doc drift | Update 03-designer.md |
| F-07 | Idempotency-Key header accepted but not implemented | LOW | G-06.1 | Developer Layer 4: implement dedup logic |
| F-08 | No MongoDB compound indexes defined | MEDIUM | Performance | Developer: add @CompoundIndex or startup initializer |

### Verdict: No CRITICAL findings. ~~1 HIGH (migration)~~ 0 HIGH (Rework #3 removed migration), 4 MEDIUM, 3 LOW.

The HIGH finding (F-02) is expected — emf-parent changes are Layer 3, and the pipeline is currently at Layer 1-2 (intouch-api-v3 only). Layer 3 items are tracked as known remaining work.

---

## Section 5: Rework #5 Compliance Analysis

> **Cycle**: 5 of 5
> **Source**: 01-architect.md (new ADR-06R + ADR-08R..16R), 03-designer.md (Rework #5 sections), 01b-migrator.md (M-1..M-6), rework-5-scope.md
> **Date**: 2026-04-20
> **Trigger**: user-authorized cascade

### 5.1 Reversed and New ADRs — Compliance State

| ADR | Intent | Compliance | Severity | Evidence |
|---|---|---|---|---|
| **ADR-06R** (reversed) | Legacy-SQL-only tiers MUST appear in /v3/tiers envelope | PENDING (new) | HIGH | Requires new `SqlTierReader` + `SqlTierConverter` + `TierEnvelopeBuilder` — no current production code. Skeleton in SDET §7.3. |
| **ADR-08R** (state machine reversal) | PENDING_APPROVAL → SNAPSHOT direct (no intermediate ACTIVE) | PENDING (new) | HIGH | `TierApprovalHandler.postApprove` must skip ACTIVE state and write directly to SNAPSHOT. Current code uses old ACTIVE→SNAPSHOT two-step. |
| **ADR-09R** (parentId semantics) | parentId = slabId (Long), not Mongo ObjectId | PENDING (new) | MEDIUM | `TierFacade.updateTier` must set parentId=slabId on edit-of-LIVE. Current code uses ObjectId reference. |
| **ADR-10R** (schema hoist) | `basicDetails.*` hoisted to root of UnifiedTierConfig | PENDING (new) | MEDIUM | UnifiedTierConfig.java class structure change; data migration needed (W-11 from backend-readiness). |
| **ADR-11R** (metadata rename) | Mongo field `metadata` → `meta` | PENDING (new) | LOW | Pure rename; Lombok @Field annotation. |
| **ADR-12R** (ID renames) | `unifiedTierId` → `tierUniqueId`; `sqlSlabId` → `slabId` | PENDING (new) | LOW | Field renames across UnifiedTierConfig, TierRepository method names, DTOs. |
| **ADR-13R** (dropped fields) | Remove `nudges`, `benefitIds`, `updatedViaNewUI`, `basicDetails.startDate/endDate` | PENDING (new) | LOW | Delete fields + their getters/setters; no other references found in code. |
| **ADR-14R** (drift detection) | basisSqlSnapshot captured at DRAFT-of-LIVE; conservative policy (any diff blocks) | PENDING (new) | HIGH | New `TierDriftChecker` class + `meta.basisSqlSnapshot` field; integration in TierApprovalHandler.preApprove. |
| **ADR-15R** (approve/reject split) | Separate `/approve` and `/reject` endpoints with distinct request bodies | PENDING (new) | MEDIUM | TierReviewController needs `.approve()` and `.reject(RejectRequest)` as distinct handler methods. |
| **ADR-16R** (dual write paths) | Legacy SlabFacade write path UNCHANGED (no MC gate) | COMPLIANT (C7) | — | Legacy SlabFacade source tree untouched — verified by cross-repo-trace.md §3.5. New-UI path is additive. |
| **ADR-17R** (3-layer name defense) | Layer 1 (create), Layer 2 (approve re-check), Layer 3 (SQL UNIQUE constraint) | PENDING (new) | HIGH | Requires: `TierValidationService.validateNameUniquenessUnified` (Layer 1+2) checking BOTH SQL LIVE and Mongo DRAFT/PENDING; SQL unique constraint via M-2 migration. |
| **ADR-18R** (single-active-draft) | One DRAFT/PENDING per slabId: app-layer + Mongo partial unique index (M-4) | PENDING (new) | HIGH | `TierValidationService.enforceSingleActiveDraft` + `uq_tier_one_active_draft_per_slab` Mongo index. |
| **ADR-19R** (SQL audit columns) | `program_slabs.updated_by/approved_by/approved_at` populated via Thrift | PENDING (new) | MEDIUM | Requires emf-parent migration V*__add_tier_audit_columns.sql + Thrift IDL extension (3 optional fields) + PE persistence logic. |

### 5.2 GUARDRAILS Compliance Check — Rework #5

| Guardrail | Rework #5 Context | Status |
|---|---|---|
| G-01 (Timezones) | basisSqlSnapshot captures `approved_at` timestamps; all server-side UTC | COMPLIANT (assuming Java `Instant` used, verified in Developer phase) |
| G-03 (Idempotency) | /approve, /reject endpoints must be idempotent — second call on already-approved returns 200 with current state, not duplicate side effects | PENDING (new requirement for Rework #5 endpoint split) |
| G-05.3 (DB-level constraints) | SQL UNIQUE (program_id, name) via M-2; Mongo partial unique index via M-4 | COMPLIANT (by migration design) |
| G-05.4 (Expand-then-contract) | M-1 adds nullable audit columns; M-2 adds constraint (pre-flight dupe scan required). No destructive DDL in cycle 1. | COMPLIANT — see migrator 01b §3.1 |
| G-07 (Tenant isolation) | All new Repository queries start with orgId: `SqlTierReader.readLiveTiers(orgId, programId)`, `TierRepository.findByOrgIdAndSlabIdAndStatusIn(...)` | COMPLIANT (by Designer interface contract) |
| G-10 (Concurrent access) | 3-layer name defense + single-active-draft backstop address race conditions | COMPLIANT — defense-in-depth |
| G-12 (Backward compatibility) | Thrift SlabInfo extensions are `optional` (field IDs 11-13 additive); old clients ignore unknown fields | COMPLIANT (C7 — Apache Thrift spec) |
| G-13 (Exception handling) | 6 new error codes (CONFLICT_NAME, SINGLE_ACTIVE_DRAFT, APPROVAL_BLOCKED_DRIFT, APPROVAL_BLOCKED_NAME_CONFLICT, APPROVAL_BLOCKED_SINGLE_ACTIVE, MISSING_REJECT_COMMENT) — must map to ConflictException or dedicated exception types | PENDING — Developer to add exception handlers per Rework #5 patterns in prior commit `fb2ab3b` |

### 5.3 New Findings — F-09 through F-15

| # | Finding | Severity | Category | Action |
|---|---|---|---|---|
| F-09 | UnifiedTierConfig schema doesn't match Rework #5 (basicDetails still nested; metadata not renamed; old field names) | MEDIUM | ADR-10R..13R | Developer: refactor UnifiedTierConfig; delete BasicDetails.java; rename TierMetadata.java → TierMeta.java; data migration script or drop-and-recreate |
| F-10 | No SqlTierReader / SqlTierConverter / TierEnvelopeBuilder classes in src/main | HIGH | ADR-06R | Developer: implement new classes per SDET §7.3 skeletons |
| F-11 | TierApprovalHandler lacks drift check in preApprove | HIGH | ADR-14R | Developer: inject TierDriftChecker; call `.check(doc.meta.basisSqlSnapshot, currentSqlRow)` — block on any diff |
| F-12 | TierReviewController has single approve/reject handler, not split | MEDIUM | ADR-15R | Developer: split into `.approve(tierId)` and `.reject(tierId, RejectRequest)` with distinct endpoints |
| F-13 | TierFacade.updateTier does not capture basisSqlSnapshot on edit-of-LIVE | HIGH | ADR-14R | Developer: on updateTier where target is LIVE (SQL row exists + no Mongo DRAFT), capture SQL snapshot into new Mongo DRAFT's meta |
| F-14 | TierValidationService lacks validateNameUniquenessUnified (checks Mongo only) | HIGH | ADR-17R | Developer: query both SQL (PeProgramSlabDao.findByProgramIdAndName) AND Mongo (TierRepository.existsByOrgIdAndProgramIdAndName) — Layer 1 at create; Layer 2 re-check in TierApprovalHandler.preApprove |
| F-15 | No TierValidationService.enforceSingleActiveDraft method | HIGH | ADR-18R | Developer: add method; integrate with TierFacade.createTier + updateTier |

### 5.4 Updated Findings Summary

**BLOCKERS (0 net new)**: None.

**HIGH (5 new, net 5)**: F-10 (envelope builder classes), F-11 (drift check missing), F-13 (basis capture missing), F-14 (unified name validation), F-15 (single-active-draft enforcement) — all are new Rework #5 requirements, not regressions.

**MEDIUM (3 new + 4 baseline = 7 total)**: F-09 (schema), F-12 (endpoint split), F-01/F-03/F-05/F-08 (baseline), F-07 (baseline).

**LOW (3 baseline)**: F-04, F-06, F-07.

### 5.5 Compliance Verdict Post-Rework-5

**PRE-DEVELOPER**: NOT COMPLIANT with Rework #5 ADRs (ADR-06R..19R). Production code is at baseline state; Rework #5 ADRs are architectural intent without implementation.

**POST-DEVELOPER (expected)**: COMPLIANT once Developer phase (10) implements F-09..F-15 per SDET §7.6 forward cascade payload and produces GREEN test state. Re-run compliance analysis after Developer delivery.

**Forward Cascade Payload — to Reviewer (Phase 11)**: This compliance gap report must feed Phase 11 review scope. Reviewer verifies that:
1. All 5 HIGH findings have been resolved in production code
2. All 7 MEDIUM findings have known remediation plans (not necessarily implemented pre-PR)
3. GUARDRAILS G-03, G-13 have concrete exception-handling implementations in code
4. Data migration strategy (W-11) is documented and signed off by ops
