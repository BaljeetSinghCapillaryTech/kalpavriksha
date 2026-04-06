# Backend Readiness — tier-crud

**Date:** 2026-04-06
**Reviewer:** /backend-readiness skill (Claude)
**Feature:** Tier CRUD REST APIs with maker-checker approval workflow
**Repos in scope:** intouch-api-v3, emf-parent, thrifts, cc-stack-crm

---

## Overall Verdict: NOT READY

**1 BLOCKER** must be fixed before merge. 4 WARNINGS should be addressed. 3 INFO items tracked for future improvement.

---

## Checklist Results

| Area | Status | Findings | Highest Severity |
|------|--------|----------|-----------------|
| Query Performance | WARN | 3 findings | WARNING |
| Thrift Compatibility | PASS | 0 issues | — |
| Cache Invalidation | PASS | 1 observation | INFO |
| Resource Management | WARN | 1 finding | WARNING |
| Error Handling | WARN | 2 findings | WARNING |
| Migration Safety | BLOCKER | 1 finding | BLOCKER |

---

## Detailed Findings

### BLOCKERS (must fix before merge)

---

#### B-1: `is_active` column missing from `program_slabs` DDL in cc-stack-crm
**File:** `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/program_slabs.sql`
**Evidence (C7 — verified from primary source):**
The canonical DDL file contains only these columns: `id`, `org_id`, `program_id`, `serial_number`, `name`, `description`, `created_on`, `auto_update_time`, `metadata`. There is no `is_active` column and no separate ALTER script anywhere in cc-stack-crm.

However, `ProgramSlab.java` (line 96) declares `@Column(name = "is_active", nullable = false)` and the `deactivateSlab` Thrift impl (line 4187) calls `slab.setActive(false)` followed by `peProgramSlabDao.save(slab)`. If `is_active` is absent from the real database schema, every `deactivateSlab` call will fail with a SQL exception, blocking the entire STOP/delete flow.

**Fix required:**
Add an ALTER TABLE (or update the CREATE TABLE) in cc-stack-crm with the `is_active` column:
```sql
ALTER TABLE `program_slabs`
  ADD COLUMN `is_active` tinyint(1) NOT NULL DEFAULT 1
    COMMENT 'Soft-delete flag. 0 = deactivated, 1 = active.';
```
Also add a backfill: `UPDATE program_slabs SET is_active = 1;` (safe — existing rows should all be active).
This is a **non-destructive additive DDL** change (nullable-equivalent via DEFAULT) so expand-then-contract is not required, but the ALTER must run before any EMF deployment that calls `deactivateSlab`.

---

### WARNINGS (should fix before merge)

---

#### W-1: No MongoDB compound indexes declared on `TierDocument`
**File:** `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/TierDocument.java`
**Evidence (C6):** `TierDocument.java` has no `@Indexed`, `@CompoundIndex` or `@Document(indexes=...)` annotations. All seven `TierRepository` queries filter on `{orgId, programId}`, `{tierId, orgId}`, `{_id, orgId}`, `{parentId, orgId, status}`, and `{orgId, programId, serialNumber}`.

Without indexes, every query performs a collection scan. Tiers per org are small today but this is a shared collection (`db.tiers`) across all orgs, so full scans will degrade as data grows.

**Minimum required indexes:**
```java
@CompoundIndexes({
  @CompoundIndex(name = "idx_orgId_programId", def = "{'orgId': 1, 'programId': 1}"),
  @CompoundIndex(name = "idx_tierId_orgId",    def = "{'tierId': 1, 'orgId': 1}", unique = true),
  @CompoundIndex(name = "idx_parentId_orgId_status", def = "{'parentId': 1, 'orgId': 1, 'status': 1}")
})
```

---

#### W-2: `@Lockable` implementation ignores `ttl` and `acquireTime` parameters
**File:** `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/validators/LockManager.java`
**Evidence (C7):** `LockManager.acquireLock` uses `redisCacheManager.getCache(ApiCacheRegions.FIVE_MINUTE_CACHE)` and then `cache.putIfAbsent(key, key)`. It does not read `lockable.ttl()` or `lockable.acquireTime()`.

The `changeTierStatus` method declares `@Lockable(..., ttl = 300000, acquireTime = 5000)` — a 5-minute lock for the APPROVE operation. The actual lock is hardcoded to the FIVE_MINUTE_CACHE region, which may have its own Redis eviction policy. The `acquireTime` parameter is completely ignored — if the lock is held, the method throws `LockManagerException` immediately (no wait/retry).

**Risk:** Two concurrent APPROVE requests for the same tier both arrive within milliseconds. The second throws `LockManagerException` immediately regardless of the configured `acquireTime = 5000ms`. The error surfaces as a 500 to the client.

**Fix:** Either enforce the `ttl` via a TTL-aware Redis SET NX PX command, or document explicitly that `ttl`/`acquireTime` parameters are advisory only and this is accepted behavior.

---

#### W-3: `createOrUpdateSlab` ThriftImpl fetches all slabs for audit lookup (pre-existing, but now on the hot path)
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`, line 1676
**Evidence (C7):** `createOrUpdateSlab` calls `m_pointsEngineRuleEditor.getAllSlabs(slabInfo.getProgramId())` (full table scan for the program's slabs) then iterates to find the old slab for audit trail purposes. This happens on every APPROVE operation.

This is pre-existing code, not introduced by this feature. However, the feature now places this on the APPROVE path that previously did not call `createOrUpdateSlab`. For programs with many slabs this adds an unnecessary list+scan before the primary `createOrUpdateSlab` call which also fetches the slab internally via `findById`.

**Fix:** Consider using `peProgramSlabDao.findActiveById(slabInfo.getId(), orgId)` directly for the audit lookup instead of loading all slabs. This is a targeted optimization, not a feature blocker, but should be addressed since the feature now owns this path.

---

#### W-4: `deleteTier` is NOT `@Lockable` but can race with `changeTierStatus(STOP)`
**File:** `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/TierFacade.java`, line 242
**Evidence (C6):** `changeTierStatus` with `STOP` action delegates to `deleteTier` (line 313-316). `changeTierStatus` holds the lock `lock_tier_status_{orgId}_{tierId}`. But `deleteTier` is also called directly from `DELETE /v3/tiers/{tierId}` without any lock. A direct DELETE request and a STOP status change can therefore race:
- Both pass the "tier is ACTIVE" check.
- Both call `deactivateSlab` in MySQL.
- Double-deactivation is idempotent (slab already inactive returns an error from EMF), but the second caller will throw `InvalidInputException("Failed to deactivate tier in backend")` — surfaced as 400 to the client.

**Fix:** Add `@Lockable(key = "'lock_tier_delete_' + #orgId + '_' + #tierId", ttl = 10000, acquireTime = 3000)` to `deleteTier`.

---

### INFO (nice to have)

---

#### I-1: `getMemberCountPerSlab` fetches ALL active slabs for the program then queries member count for all of them
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`, lines 4221-4231
**Evidence (C7):** `getMemberCountPerSlab` loads all active `ProgramSlab` records via `peProgramSlabDao.findByProgram(orgId, programId)`, extracts IDs, then calls `peCustomerEnrollmentDao.countMembersPerSlab(orgId, programId, slabIds)`. The caller (`TierFacade.fetchMemberCountMap`) already has the active slab IDs from MongoDB and only needs counts for those. The additional `findByProgram` DB call is redundant on the list path.

This is an INFO item since the count of slabs per program is bounded (design says <10) and the impact is small. No action required, but worth noting for future optimization.

---

#### I-2: `SlabInfo.id` is `required i32` in Thrift IDL — new slab creation sends id=0
**File:** `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift`, line 352
**Evidence (C7):** `struct SlabInfo { 1: required i32 id; ... }`. In `approveTier`, for a brand-new DRAFT tier where `tier.getSlabId() == null`, the facade does NOT call `slabInfo.setId()`. In Java Thrift, unset `required` int fields default to 0. The `createOrUpdateSlab` service logic at line 3655 uses `findById(new ProgramSlabPK(0, orgId))` — which returns null, triggering the "new slab" path as intended.

This works today, but it relies on `id=0` being a sentinel for "new slab". This is implicit contract coupling. If the Thrift layer ever validates required fields as truly required (some Thrift validators do), id=0 on a `required` field may throw. This is tracked as INFO — no immediate fix needed, but adding a comment in `approveTier` and considering making `id` optional in the IDL (additive-safe change) would improve clarity.

---

#### I-3: No test coverage for the R-6 rollback scenario
**Evidence (C5):** No test file visible for the Thrift failure → MongoDB revert path in `approveTier`. The rollback logic (lines 391-397 of `TierFacade.java`) is critical operational behavior. A unit test covering "Thrift throws, MongoDB status reverts to PENDING_APPROVAL" would prevent regression. This is tracked as INFO since test coverage is flagged by the QA/SDET skills, not Backend Readiness — but it's noted here given the criticality of R-6.

---

## Thrift Backward Compatibility Analysis

### New structs added (additive, non-breaking)
- `SlabInfo` — existing struct, no fields removed, new optional field `updatedViaNewUI` (field 7, optional). **PASS.**
- `MemberCountEntry` — new struct, fields 1-2 both required. New struct added additively. **PASS.**
- `MemberCountPerSlabResponse` — new struct, field 1 required list. New struct added additively. **PASS.**

### New service methods added (additive, non-breaking)
- `createOrUpdateSlab` — additive method. Throws `PointsEngineRuleServiceException` declared. **PASS.**
- `deactivateSlab` — additive method. Throws declared. **PASS.**
- `getMemberCountPerSlab` — additive method. Throws declared. **PASS.**

No fields removed, no field IDs changed, no types changed. Old clients that do not call the new methods are unaffected.

**Thrift Compatibility: PASS (C7)**

---

## Cache Invalidation Analysis

### Write paths and cache impact
| Operation | Cache Eviction | Evidence |
|-----------|---------------|----------|
| APPROVE → `createOrUpdateSlab` | `cacheEvictHelper.evictProgramIdCache(orgId, programId)` called at ThriftImpl line 1692 | C7 |
| STOP → `deactivateSlab` | `cacheEvictHelper.evictProgramIdCache(orgId, programId)` called at ThriftImpl line 4191 | C7 |
| MongoDB-only operations (CREATE DRAFT, UPDATE DRAFT, REJECT) | No cache impact — MySQL unchanged | C7 |

Cache eviction is correctly placed in the EMF ThriftImpl, not in intouch-api-v3. This matches the architecture decision (R-3). **Cache Invalidation: PASS.**

Note: The `@Cacheable` annotations on `getAllAlternateCurrencies`, `getAllPrograms`, and `getProgramInfoById` in `PointsEngineRulesThriftService` are unaffected by this feature (they cache read-only program data, not slab data). No action needed.

---

## Connection and Resource Management

No new HTTP clients, `DriverManager.getConnection()`, or manual resource allocation introduced in this feature. The feature uses:
- **MongoDB:** Spring Data `MongoRepository` — uses existing pooled connection. PASS.
- **MySQL (emf-parent):** Spring Data JPA with `@Transactional("warehouse")` — uses existing pooled DataSource. PASS.
- **Thrift:** `RPCService.rpcClient()` — uses existing connection pooling. PASS.

`@Transactional(value = "warehouse", rollbackFor = Exception.class)` is correctly applied to `deactivateSlab` (line 4171). `createOrUpdateSlab` inherits the class-level `@Transactional` from `PointsEngineRuleService` (confirmed via service call chain). PASS.

---

## Migration Safety

This feature uses **manual SQL in cc-stack-crm** (no Flyway). One blocker found (see B-1).

Additional DDL items:
- The `color_code` field is stored in the existing `metadata` JSON column (handled via `SlabMetaData` builder at line 3677) — no new column needed. PASS.
- No DROP, RENAME, or destructive operations. PASS.
- No rollback script exists for the `is_active` column addition — the rollback would be `ALTER TABLE program_slabs DROP COLUMN is_active`. This should be documented alongside the forward ALTER. **WARNING** (captured under W-1 implicitly; no separate warning added since B-1 captures the full picture).

---

## Confidence Summary

| Finding | Confidence | Basis |
|---------|-----------|-------|
| B-1: `is_active` missing from DDL | C7 | Read `program_slabs.sql` directly; grep confirmed no other ALTER scripts |
| W-1: No MongoDB indexes | C7 | Read `TierDocument.java` — no index annotations present |
| W-2: `@Lockable` ignores ttl/acquireTime | C7 | Read `LockManager.java` lines 58-68; parameters not used |
| W-3: getAllSlabs in createOrUpdateSlab | C7 | Read ThriftImpl lines 1676-1684 |
| W-4: `deleteTier` not `@Lockable` | C6 | Read `TierFacade.java`; no `@Lockable` on method signature |
| I-1: Redundant findByProgram in getMemberCountPerSlab | C7 | Read ThriftImpl lines 4221-4231 |
| I-2: SlabInfo.id=0 for new slabs | C7 | Read IDL line 352 + `approveTier` lines 347-365 |
| I-3: No R-6 rollback test | C5 | No test file found for this path; absence of evidence only |
| Thrift backward compat: PASS | C7 | Read full IDL diff, all new fields/methods confirmed additive |
| Cache eviction: PASS | C7 | Read ThriftImpl lines 1692, 4191 |

---

## Questions for User

**Q1 (confidence C3 — below C5, escalating):**
Is there a live `program_slabs` database on any environment that already has an `is_active` column (e.g., applied via a hotfix or a separate migration not tracked in cc-stack-crm)? If yes, the B-1 blocker is a DDL tracking gap rather than a missing column, and the fix is to update the canonical SQL file to match reality. Evidence: the `ProgramSlab.java` entity and `deactivateSlab` impl look production-ready; it's possible the column exists in prod but the cc-stack-crm file was simply never updated.

**Q2 (C4):**
The `@Lockable` implementation uses `FIVE_MINUTE_CACHE` regardless of the `ttl` parameter. Is this intentional (i.e., all locks in intouch-api-v3 use a fixed 5-minute TTL as a safety ceiling)? If yes, W-2 should be documented as an accepted constraint rather than a defect.

---

## Assumptions Made

- **A1 (C6):** The cc-stack-crm `program_slabs.sql` file is the authoritative DDL source. If DDL is managed elsewhere (e.g., Liquibase outside this repo, or a separate migration tool), B-1 may not apply.
- **A2 (C6):** `RPCService.rpcClient()` uses an existing connection pool configured at the service startup level. This is consistent with all other callers of `getClient()` in the same file.
- **A3 (C5):** MongoDB `tiers` collection does not yet exist in production (new feature), so index creation via `@CompoundIndex` will execute on first application startup without impacting existing data.
