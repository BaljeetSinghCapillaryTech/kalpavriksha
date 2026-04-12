# Backend Readiness -- Tiers CRUD + Generic Maker-Checker

> Phase 10b
> Date: 2026-04-12
> Scope: 43 files changed in intouch-api-v3 (37 production + 4 test + 2 controllers)

## Overall Verdict: READY WITH WARNINGS

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

Similarly for `pending_changes`:
```javascript
db.pending_changes.createIndex({ orgId: 1, status: 1, entityType: 1 })
db.pending_changes.createIndex({ orgId: 1, status: 1, entityType: 1, programId: 1 })
```

**1b: N+1 Detection (C7)**: No N+1 patterns found. No DAO calls inside loops.

**1c: Large Result Sets (C6)**:
- `findByOrgIdAndProgramId` returns all tiers for a program — bounded by 50-tier cap. PASS.
- `listPending` returns all pending changes per entity type — could grow. Low risk now (few pending changes expected). INFO.

---

### Step 2: Thrift Compatibility (C7)

**PASS** — No `.thrift` IDL files were modified. Existing Thrift methods are used via wrapper (ADR-05). TierChangeApplier currently throws `UnsupportedOperationException` for CREATE/DELETE flows — Thrift integration deferred until wrapper methods are added to `PointsEngineRulesThriftService`.

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

**W-02: TierChangeApplier Thrift call has no error handling (WARNING, C5)**

File: `TierChangeApplier.java`
- The Thrift service is commented out (`// @Autowired private PointsEngineRulesThriftService thriftService`)
- When implemented, needs: `TTransportException` handling, `TApplicationException` handling, timeout configuration
- The `@Lockable` annotation (per architect ADR-07) is not yet on the `apply()` method
- **Fix (for Developer when Thrift is wired)**: Add `@Lockable(key = "'lock_tier_sync_' + #orgId", ttl = 300000, acquireTime = 5000)` and try-catch for Thrift exceptions

**W-03: Controller skeleton throws UnsupportedOperationException to callers (WARNING, C5)**

Files: `TierController.java`, `MakerCheckerController.java`
- All controller methods still throw `UnsupportedOperationException` — they haven't been wired to the Facade yet
- When wired, need: `@ExceptionHandler` for validation exceptions → 400, state exceptions → 409, not-found → 404
- **Fix**: Wire controllers to facades. Add global `@ControllerAdvice` exception handler or per-controller `@ExceptionHandler`.

---

### Step 6: Flyway Migration Safety (C7)

**PASS** — No Flyway migration scripts exist in intouch-api-v3 for this feature. The `program_slabs` ALTER TABLE migration (ADR-03) is in emf-parent, not yet created. When created:
- Must use `ALTER TABLE program_slabs ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'`
- Must be idempotent
- Must have rollback script

---

## Summary of Findings

### BLOCKERS (0)
None.

### WARNINGS (3)

| # | Finding | File | Fix | Priority |
|---|---------|------|-----|----------|
| W-01 | Missing MongoDB compound indexes | `UnifiedTierConfig.java`, `PendingChange.java` | Add `@CompoundIndex` annotations or startup index initializer | Before production |
| W-02 | Thrift call has no error handling / no @Lockable | `TierChangeApplier.java:20` | Add when Thrift wrapper is wired | Before Thrift integration |
| W-03 | Controllers not wired to facades | `TierController.java`, `MakerCheckerController.java` | Wire REST endpoints to facades, add exception handlers | Before API testing |

### INFO (1)

| # | Finding | Detail |
|---|---------|--------|
| I-01 | `listPending` unbounded | Low risk now (few pending changes). Add pagination if MC volume grows. |

---

## Confidence Assessment

All findings rated C5+ (backed by code evidence from grep/read). No speculative findings.
