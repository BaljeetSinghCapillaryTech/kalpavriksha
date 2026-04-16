# Compliance Analysis -- Tiers CRUD (Architecture vs Code)

> Phase 10c: Analyst --compliance
> Date: 2026-04-12
> Intent: 01-architect.md, 03-designer.md, session-memory.md
> Reality: 39 production files in intouch-api-v3

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
