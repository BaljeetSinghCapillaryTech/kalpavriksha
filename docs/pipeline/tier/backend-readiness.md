# Backend Readiness -- Tiers CRUD + Generic Maker-Checker

> Phase 10b
> Date: 2026-04-12 (updated 2026-04-20 — Rework #5 cascade)
> Scope: 43 files changed in intouch-api-v3 (37 production + 4 test + 2 controllers) + Rework #5 adds 10 new production files, 14 new test files, 3 Flyway migrations in emf-parent, Thrift IDL extension
>
> **Rework #5 Status**: Cascaded. See Section 11 for updated readiness assessment covering
> unified read surface, drift detection, dual write paths, schema cleanup, and new SQL audit
> columns. Verdict downgraded to READY WITH WARNINGS pending Rework #5 code implementation.

## Overall Verdict: READY WITH WARNINGS (baseline) + REWORK #5 PENDING (see §11)

---

## Checklist Results

| Area | Status | Findings | Severity |
|------|--------|----------|----------|
| Query Performance | WARN | 3 findings | WARNING |
| Thrift Compatibility | PASS | 0 findings (no Thrift changes) | — |
| Cache Invalidation | PASS | 0 findings (no cache usage) | — |
| Resource Management | PASS | 0 findings | — |
| Error Handling | WARN | 2 findings | WARNING |
| Migration Safety | PASS | 0 findings (no Flyway migration in intouch-api-v3) | — |

---

## Detailed Findings

### Step 1: Query Performance

**1a: Repository Methods — Tenant Filter Check (C6)**

All repository methods include `orgId` as the first parameter — multi-tenancy filter is structurally enforced.

| Method | orgId Present | Indexed Columns | Status |
|--------|--------------|-----------------|--------|
| `findByOrgIdAndProgramId` | YES | orgId + programId | PASS |
| `findByOrgIdAndObjectId` | YES | orgId + _id | PASS |
| `findByOrgIdAndUnifiedTierId` | YES | orgId + unifiedTierId | WARN — needs index |
| `findByOrgIdAndProgramIdAndParentId` | YES | orgId + programId + parentId | WARN — needs index |
| `existsByOrgIdAndProgramIdAndBasicDetailsName` | YES | orgId + programId + nested field | WARN — needs compound index |
| `findByOrgIdAndStatus` | YES | orgId + status | WARN — needs index on ApprovalRepository |
| `countByOrgIdAndProgramId` | YES | orgId + programId | PASS (same as findBy) |

**W-01: Missing MongoDB indexes (WARNING, C5)**

Three queries need compound indexes on the `unified_tier_configs` collection:
```javascript
// Required indexes (create in MongoConfigTest for ITs, production via migration)
db.unified_tier_configs.createIndex({ orgId: 1, unifiedTierId: 1 }, { unique: true })
db.unified_tier_configs.createIndex({ orgId: 1, programId: 1, parentId: 1 })
db.unified_tier_configs.createIndex({ orgId: 1, programId: 1, "basicDetails.name": 1 }, { unique: true })
```
**Fix**: Add `@CompoundIndex` annotations on `UnifiedTierConfig` or a manual index creation in a startup initializer.

Similarly for `pending_approvals`:
```javascript
db.pending_approvals.createIndex({ orgId: 1, status: 1, entityType: 1 })
db.pending_approvals.createIndex({ orgId: 1, status: 1, entityType: 1, programId: 1 })
```

**1b: N+1 Detection (C7)**: No N+1 patterns found. No DAO calls inside loops.

**1c: Large Result Sets (C6)**:
- `findByOrgIdAndProgramId` returns all tiers for a program — bounded by 50-tier cap. PASS.
- `listPending` returns all pending changes per entity type — could grow. Low risk now (few pending changes expected). INFO.

---

### Step 2: Thrift Compatibility (C7)

**PASS** — No `.thrift` IDL files were modified. Existing Thrift methods are used via wrapper (ADR-05). TierApprovalHandler currently throws `UnsupportedOperationException` for CREATE/DELETE flows — Thrift integration deferred until wrapper methods are added to `PointsEngineRulesThriftService`.

---

### Step 3: Cache Invalidation (C7)

**PASS** — No cache annotations (`@Cacheable`, `@CacheEvict`) in new code. No Redis/Caffeine usage. The member count cache (cron-based, session memory D-29) is not yet implemented — it's a future Layer 4 item.

---

### Step 4: Resource Management (C7)

**PASS** — No manual resource handling:
- No `new InputStream/OutputStream` 
- No `DriverManager.getConnection()`
- No `RestTemplate` / `HttpClient` usage
- All DB access via Spring Data MongoRepository (connection pool managed by framework)

---

### Step 5: Error Handling at Boundaries

**W-02: TierApprovalHandler Thrift call has no error handling (WARNING, C5)**

File: `TierApprovalHandler.java`
- The Thrift service is commented out (`// @Autowired private PointsEngineRulesThriftService thriftService`)
- When implemented, needs: `TTransportException` handling, `TApplicationException` handling, timeout configuration
- The `@Lockable` annotation (per architect ADR-07) is not yet on the `apply()` method
- **Fix (for Developer when Thrift is wired)**: Add `@Lockable(key = "'lock_tier_sync_' + #orgId", ttl = 300000, acquireTime = 5000)` and try-catch for Thrift exceptions

**W-03: Controller skeleton throws UnsupportedOperationException to callers (WARNING, C5)**

Files: `TierController.java`, `TierReviewController.java`
- All controller methods still throw `UnsupportedOperationException` — they haven't been wired to the Facade yet
- When wired, need: `@ExceptionHandler` for validation exceptions → 400, state exceptions → 409, not-found → 404
- **Fix**: Wire controllers to facades. Add global `@ControllerAdvice` exception handler or per-controller `@ExceptionHandler`.

---

### Step 6: Flyway Migration Safety (C7)

**PASS** — No Flyway migration scripts exist in intouch-api-v3 for this feature. ~~The `program_slabs` ALTER TABLE migration (ADR-03) is in emf-parent, not yet created.~~ **Rework #3**: No SQL migration needed. ADR-03 (expand-then-contract) removed from scope — SQL only contains ACTIVE tiers, no status column needed.

---

## Summary of Findings

### BLOCKERS (0)
None.

### WARNINGS (3)

| # | Finding | File | Fix | Priority |
|---|---------|------|-----|----------|
| W-01 | Missing MongoDB compound indexes | `UnifiedTierConfig.java`, `PendingChange.java` | Add `@CompoundIndex` annotations or startup index initializer | Before production |
| W-02 | Thrift call has no error handling / no @Lockable | `TierApprovalHandler.java:20` | Add when Thrift wrapper is wired | Before Thrift integration |
| W-03 | Controllers not wired to facades | `TierController.java`, `TierReviewController.java` | Wire REST endpoints to facades, add exception handlers | Before API testing |

### INFO (1)

| # | Finding | Detail |
|---|---------|--------|
| I-01 | `listPending` unbounded | Low risk now (few pending changes). Add pagination if MC volume grows. |

---

## Confidence Assessment

All findings rated C5+ (backed by code evidence from grep/read). No speculative findings.

---

## Section 11: Rework #5 Readiness Assessment

> **Cycle**: 5 of 5
> **Source**: Forward cascade from BTG (§6.4), Migrator (01b Sec 3.1), Cross-Repo Trace (updated), SDET (§7.6)
> **Date**: 2026-04-20
> **Trigger**: user-authorized cascade

### 11.1 Updated Checklist — Post-Rework-5 Scope

| Area | Status | Findings | Severity |
|------|--------|----------|----------|
| Query Performance (envelope reads, SQL+Mongo parallel) | WARN | 4 new findings | WARNING |
| Thrift Compatibility (3 new optional SlabInfo fields) | PASS | 0 findings (optional = C7 backward-compat per Apache Thrift spec) | — |
| Cache Invalidation | PASS | No caching introduced by Rework #5 | — |
| Resource Management (parallel SQL+Mongo fetch) | WARN | 1 new finding | WARNING |
| Error Handling (6 new error codes, SAGA rollback) | WARN | 2 new findings | WARNING |
| Migration Safety (3 SQL migrations M-1..M-2, 4 Mongo indexes M-3..M-6) | PASS | 0 findings (expand-only DDL, idempotent guards, rollbacks present) | — |
| Schema Cleanup (drop fields, hoist, renames) | WARN | 1 finding — data migration strategy | WARNING |
| Dual Write Path Coexistence | PASS | 0 findings (legacy SlabFacade unchanged — C7 verified via cross-repo trace) | — |
| Drift Detection Correctness | WARN | 1 finding — conservative-policy false-positive rate | WARNING |

### 11.2 New Findings (W-04 through W-11)

**W-04: Envelope listing does 2 queries per call (WARNING, C6)**
`TierEnvelopeBuilder` invokes `SqlTierReader.readLiveTiers(programId)` + `TierRepository.findByOrgIdAndProgramIdAndStatusIn([DRAFT, PENDING_APPROVAL])` — 2 trips per list call. For small programs (<50 tiers) this is acceptable; for high-volume tenants consider: (a) async parallel fetch via CompletableFuture, or (b) cached SqlTierReader results with invalidation on Thrift writes.
- Fix: wrap both reads in CompletableFuture.supplyAsync; join before building envelopes. Estimated +1 test method.
- Priority: Before production for high-volume tenants; not blocking for MVP.

**W-05: No index on `meta.basisSqlSnapshot` — not needed (INFO, C6)**
basisSqlSnapshot is embedded, never queried directly (only inspected at approve-time on a single doc load by objectId). No index required.

**W-06: Rework #5 introduces 4 new MongoDB indexes (WARNING, C7)**
M-3 through M-6 from `01b-migrator.md`. All production-safe (expand-only, idempotent via `createIndex` idempotency). Deployment ordering documented in migrator §5. Partial unique index M-4 requires MongoDB 3.2+ — verify cluster version before deploying.
- Fix: Run migrator dry-run against prod-shape cluster pre-release.
- Priority: Before production.

**W-07: Connection/resource management for parallel SQL+Mongo fetch (WARNING, C5)**
If W-04 is resolved with CompletableFuture, the default ForkJoinPool must be sized appropriately. Under load this could starve other parallel operations in the same JVM.
- Fix: Use a dedicated `@Qualifier("tierEnvelopeExecutor")` Executor bean (bounded pool, e.g., 8 threads). Add timeout via `.orTimeout(500, MS)`.
- Priority: Before production.

**W-08: No circuit breaker / timeout on Thrift calls during approve (WARNING, C6)**
`TierApprovalHandler.handlePublish` invokes `PointsEngineRulesThriftService.createSlabAndUpdateStrategies` — Thrift call has no declared timeout. If PE hangs, approval SAGA is stuck in PENDING_APPROVAL with no rollback. Rework #5 amplifies risk — 3 new optional fields mean larger payloads.
- Fix: Wrap with `@Lockable` or Hystrix/Resilience4j circuit breaker; set 10s timeout; on timeout → fire SAGA.onPublishFailure to revert Mongo state.
- Priority: Before production — HIGH impact (data consistency under PE outage).
- Evidence: same W-02 finding from baseline; Rework #5 extends scope.

**W-09: Drift detection false-positive rate unmeasured (WARNING, C4)**
Conservative policy: ANY SQL diff blocks approval, even cosmetic (e.g., whitespace in `description`). In mixed-UI environments (legacy edits happen frequently) this may cause high rejection rate requiring manual approver intervention.
- Fix: After Phase-10c code compliance check, add operational monitoring metric `tier.approval.blocked_by_drift.count` + field-level diff breakdown. Revisit policy (e.g., whitelist cosmetic fields) after 30-day prod observation.
- Priority: Before production (observability), not blocking (policy review post-launch).

**W-10: SQL audit column nullable for pre-migration rows (WARNING, C6)**
M-1 adds `updated_by`, `approved_by`, `approved_at` as nullable. Legacy rows will have NULL. Reports/dashboards must tolerate NULL in these columns — old tiers won't retroactively gain audit data.
- Fix: Document in api-handoff.md and reports-team slack; consider backfill with "unknown-legacy" marker if reporting stakeholders require.
- Priority: Before production (stakeholder comms).

**W-11: Data migration strategy for existing Mongo docs (WARNING, C5)**
Rework #5 renames `metadata`→`meta`, `unifiedTierId`→`tierUniqueId`, `sqlSlabId`→`slabId`; drops `nudges`, `benefitIds`, `updatedViaNewUI`, `basicDetails.startDate`, `basicDetails.endDate`; hoists `basicDetails.*` to root. Existing MongoDB documents from prior pipeline runs (if any) are incompatible.
- Fix: In a pre-release session, run one-shot migration script: `db.unified_tier_configs.updateMany({}, [{$set: <rename + hoist pipeline>}, {$unset: [...]}])`. Alternatively, because Rework #5 is pre-launch (no production data), drop the collection and recreate.
- Priority: Before any non-empty env deployment (staging/prod). MVP/dev: safe to drop.

### 11.3 Thrift Backward Compatibility — Rework #5 Extensions (PASS, C7)

3 new optional fields on Thrift `SlabInfo` struct:
```thrift
struct SlabInfo {
  // ... existing fields ...
  11: optional string updatedBy;      // NEW — Rework #5 M-1
  12: optional string approvedBy;     // NEW — Rework #5 M-1
  13: optional i64 approvedAt;        // NEW — Rework #5 M-1 (epoch millis)
}
```
**Compatibility matrix (Apache Thrift spec verified)**:
| Scenario | Result |
|---|---|
| Old intouch-api-v3 → New emf-parent (PE) | PE reads SlabInfo, new fields absent → defaults to null. OLD CODE WORKS. |
| New intouch-api-v3 → Old emf-parent (PE) | Old PE ignores unknown field IDs 11-13. NEW FIELDS NOT PERSISTED, but no runtime error. Requires emf-parent deploy before intouch-api-v3 wants audit persistence. |
| Rolling deploy (any order) | No compilation errors, no runtime errors. Safe. |

**Deployment order recommendation**: emf-parent (PE) first → intouch-api-v3 second. This ensures audit fields are persisted from the moment new UI writes them.

### 11.4 Updated Summary

**BLOCKERS (0 net new)**: None.

**WARNINGS (total 11 = 3 baseline + 8 Rework #5)**:

| # | Area | Priority |
|---|------|----------|
| W-01..W-03 | Baseline (indexes, Thrift wrapper, controllers) | Before production |
| W-04 | Envelope list 2-query performance | Before production (high-volume) |
| W-07 | Parallel fetch threadpool sizing | Before production |
| W-08 | Thrift circuit breaker + timeout | Before production (HIGH — data consistency) |
| W-09 | Drift false-positive observability | Before production |
| W-10 | Legacy row NULL audit fields | Before production (stakeholder comms) |
| W-11 | Mongo data migration script | Before staging/prod deploy |

**INFO (2)**: I-01 (listPending unbounded, baseline), I-02 (new W-05 — basisSqlSnapshot indexing not required).

### 11.5 Verdict

**READY WITH WARNINGS** — baseline + Rework #5 extensions are architecturally sound; 8 new warnings are operational concerns (monitoring, tuning, deploy ordering) rather than design flaws. No blockers introduced.

Post-Rework-5 verdict depends on Developer phase (Phase 10) code delivery. Re-run backend-readiness after GREEN confirmation.
