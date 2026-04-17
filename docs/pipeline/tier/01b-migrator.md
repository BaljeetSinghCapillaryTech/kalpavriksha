# Migration Planning — Tiers CRUD (Rework #5 scope)

> Phase 6b: Schema migration analysis
> Date: 2026-04-11 (rewritten 2026-04-17 — Rework #5)
> Source: 01-architect.md, 02-analyst.md, 03-designer.md, rework-5-scope.md (M-1, Q-9a)
>
> **Rework history (this file)**:
> - **Rework #3 (2026-04-16)**: Original M-1 (SQL status column) + M-2 (status index) REMOVED
>   from scope. No status column on `program_slabs`. Every SQL row is implicitly LIVE.
> - **Rework #5 (2026-04-17)**: New migrations required —
>   - SQL audit columns on `program_slabs` (updated_by, approved_by, approved_at) — M-1 Rew5 spec
>   - Mongo partial unique index for single-active-draft invariant — Q-9a
>   - Mongo listing index for unified read surface (envelope builder) — C-1
>   - SQL UNIQUE constraint on (program_id, name) — 3-layer name defense Layer 3 — Q-9b
> - **DEFERRED**: M-3 (customer_enrollment index) — evaluate when implementing member count cron.

---

## Migration Tool

**Finding (unchanged from Rework #3)**: `emf-parent` does NOT use Flyway or Liquibase. No migration framework in `pom.xml`. Schema changes are applied via manual SQL scripts through the deployment pipeline or JPA auto-DDL.

**Recommendation**: Create SQL migration scripts as standalone `.sql` files in `scripts/migrations/`. Mongo index scripts go into `scripts/migrations/mongo/` as `.js` files executable via `mongo` shell or Spring `@EventListener(ApplicationReadyEvent.class)` bootstrapping.

---

## Migration Inventory (post-Rework #5)

| # | Store | Target | Change | Type | Risk | Priority |
|---|-------|--------|--------|------|------|----------|
| M-1 | SQL | program_slabs | ADD COLUMNS updated_by, approved_by, approved_at | ALTER TABLE | LOW (nullable, expand-only) | P0 — required for audit trail + drift detection |
| M-2 | SQL | program_slabs | ADD UNIQUE (program_id, name) | ALTER TABLE | LOW-MED (must backfill-check for existing dupes first) | P0 — 3-layer name defense Layer 3 |
| M-3 | Mongo | unified_tier_configs | CREATE INDEX (orgId, programId, status) | createIndex | LOW (additive, background) | P0 — envelope listing query |
| M-4 | Mongo | unified_tier_configs | CREATE PARTIAL UNIQUE INDEX (orgId, programId, slabId) where status IN [DRAFT, PENDING_APPROVAL] and slabId exists | createIndex | LOW (partial, additive) | P0 — single-active-draft backstop (Q-9a) |
| M-5 | Mongo | unified_tier_configs | CREATE INDEX (tierUniqueId) unique | createIndex | LOW | P0 — single-tier lookup by tierUniqueId |
| M-6 | Mongo | unified_tier_configs | CREATE INDEX (slabId) | createIndex | LOW | P1 — parentId resolution + single-tier lookup by slabId |
| M-7 (deferred) | SQL | customer_enrollment | ADD INDEX (org_id, program_id, current_slab_id, is_active) | CREATE INDEX | MEDIUM (large table) | P2 — required only when member-count cron is enabled |

---

## M-1: SQL audit columns on program_slabs (Rework #5 M-1)

### Forward Migration

```sql
-- M-1 FORWARD: Add audit columns to program_slabs
-- Purpose: capture who updated/approved a tier + when (Rework #5 M-1)
-- These columns are NULLABLE — legacy rows will simply have NULL audit data
-- Expand-only: no existing column renamed or removed (GUARDRAILS G-05.4)

ALTER TABLE program_slabs
    ADD COLUMN updated_by  VARCHAR(255) NULL,
    ADD COLUMN approved_by VARCHAR(255) NULL,
    ADD COLUMN approved_at TIMESTAMP NULL;
```

**Note (Rework #5 M-1)**: `created_by` is NOT added — only update/approval audit is required. If a creator audit is needed later, it is a separate additive migration.

### Idempotent form

```sql
-- Safe to re-run
SET @updated_by_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'program_slabs'
      AND COLUMN_NAME = 'updated_by');
SET @sql1 = IF(@updated_by_exists = 0,
    'ALTER TABLE program_slabs ADD COLUMN updated_by VARCHAR(255) NULL',
    'SELECT ''updated_by already exists''');
PREPARE s FROM @sql1; EXECUTE s; DEALLOCATE PREPARE s;

SET @approved_by_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'program_slabs'
      AND COLUMN_NAME = 'approved_by');
SET @sql2 = IF(@approved_by_exists = 0,
    'ALTER TABLE program_slabs ADD COLUMN approved_by VARCHAR(255) NULL',
    'SELECT ''approved_by already exists''');
PREPARE s FROM @sql2; EXECUTE s; DEALLOCATE PREPARE s;

SET @approved_at_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'program_slabs'
      AND COLUMN_NAME = 'approved_at');
SET @sql3 = IF(@approved_at_exists = 0,
    'ALTER TABLE program_slabs ADD COLUMN approved_at TIMESTAMP NULL',
    'SELECT ''approved_at already exists''');
PREPARE s FROM @sql3; EXECUTE s; DEALLOCATE PREPARE s;
```

### Backward Compatible?

YES.
- All three columns are NULLABLE — existing rows get NULL.
- Legacy code paths (SlabFacade → PeProgramSlabDao direct SQL) that do not reference these columns continue to work unchanged.
- Thrift IDL: the three fields are added as `optional` in SlabInfo — Thrift IDL compatibility preserved (unset optionals serialize to absent).
- Old clients (pre-Rework #5 callers of the Thrift service) simply don't populate these fields.

### Rollback

```sql
-- M-1 ROLLBACK: Remove audit columns
-- CAUTION: Run only if no production code depends on these columns
ALTER TABLE program_slabs
    DROP COLUMN updated_by,
    DROP COLUMN approved_by,
    DROP COLUMN approved_at;
```

### Risk Assessment

- **Data loss on rollback**: Yes, historic audit data would be lost. Rollback only if code has never written these columns.
- **Table lock duration**: MySQL 8.0+ executes `ADD COLUMN NULL` as INSTANT DDL (metadata-only, no table copy). MySQL 5.7 may require a table copy (~seconds for this small table).
- **Table size**: `program_slabs` is small (typically hundreds to low thousands of rows); migration completes in seconds regardless of MySQL version.

---

## M-2: SQL UNIQUE constraint on (program_id, name) — 3-layer name defense Layer 3

### Pre-flight check (backfill)

Before applying the constraint, detect any existing duplicate names:

```sql
-- Pre-flight: identify duplicate (program_id, name) pairs
SELECT program_id, name, COUNT(*) AS cnt
FROM program_slabs
GROUP BY program_id, name
HAVING cnt > 1;
```

If any rows returned → duplicates exist. Resolution before applying M-2:
1. If duplicates are true dupes (not just case variance): rename one of them (`name` + ` (duplicate)`) or delete via product-confirmed cleanup.
2. Re-run the pre-flight until it returns zero rows.

### Forward Migration

```sql
-- M-2 FORWARD: Enforce tier name uniqueness within a program at DB layer
-- Serves as 3-layer name collision defense Layer 3 (backstop for app-layer races)

ALTER TABLE program_slabs
    ADD CONSTRAINT uq_program_slabs_program_name UNIQUE (program_id, name);
```

### Backward Compatible?

CONDITIONAL. If the pre-flight check passes, YES — constraint is additive and enforced only on future writes. If duplicates exist, the ALTER will fail with a constraint-violation error and no schema change occurs. Pre-flight + cleanup is mandatory.

### Rollback

```sql
-- M-2 ROLLBACK: Drop unique constraint
ALTER TABLE program_slabs
    DROP INDEX uq_program_slabs_program_name;
```

### Risk Assessment

- **Data integrity**: Protects against future duplicate-name bugs. High value.
- **Pre-flight failures**: If duplicates exist, deployment pipeline must block and require human intervention (product decides which row to rename/remove).
- **Write-path impact**: Any future INSERT/UPDATE that would create a duplicate name within a program will fail with SQL error. App-layer Layer 1 (at DRAFT creation) and Layer 2 (at approval) catch 99% of cases; Layer 3 is the last-resort backstop.

---

## M-3: Mongo listing index (orgId, programId, status)

### Forward Migration

```javascript
// M-3 FORWARD: Covering index for envelope-listing queries
// Target query:
//   db.unified_tier_configs.find({ orgId, programId, status: { $in: [...] } })
// Used by: TierFacade.listTiers → envelope builder (Mongo side)

db.unified_tier_configs.createIndex(
  { orgId: 1, programId: 1, status: 1 },
  {
    name: "idx_utc_org_program_status",
    background: true
  }
);
```

### Backward Compatible?

YES. Additive. Does not change query semantics.

### Rollback

```javascript
db.unified_tier_configs.dropIndex("idx_utc_org_program_status");
```

### Risk Assessment

- **Build time**: `unified_tier_configs` is small at launch (zero rows initially for most orgs); trivial. Over time this collection grows with SNAPSHOTs — index build remains fast because MongoDB builds indexes in the background without blocking writes.
- **Write overhead**: Minor. Each insert/update touches one additional B-tree.

---

## M-4: Mongo partial unique index — single-active-draft backstop (Rework #5 Q-9a)

### Forward Migration

```javascript
// M-4 FORWARD: Partial unique index enforcing at most one DRAFT or PENDING_APPROVAL
// doc per (orgId, programId, slabId). Ensures the single-active-draft invariant
// even under concurrent write races that bypass app-layer checks.
//
// The filter requires BOTH:
//   - status IN ["DRAFT", "PENDING_APPROVAL"]
//   - slabId exists (guards against null-collision for brand-new DRAFTs)
//
// Brand-new DRAFTs (slabId=null, parentId=null) are NOT covered by this index;
// they have a different uniqueness key (tierUniqueId, enforced via M-5).

db.unified_tier_configs.createIndex(
  { orgId: 1, programId: 1, slabId: 1 },
  {
    name: "uq_tier_one_active_draft_per_slab",
    unique: true,
    partialFilterExpression: {
      status: { $in: ["DRAFT", "PENDING_APPROVAL"] },
      slabId: { $exists: true, $ne: null }
    },
    background: true
  }
);
```

### Backward Compatible?

CONDITIONAL. If any existing data already violates the invariant (two DRAFTs or two PENDING_APPROVAL docs for the same slabId), the index build will fail. Pre-flight detection:

```javascript
// Pre-flight: find slabIds with multiple active docs
db.unified_tier_configs.aggregate([
  { $match: { slabId: { $exists: true, $ne: null }, status: { $in: ["DRAFT", "PENDING_APPROVAL"] } } },
  { $group: { _id: { orgId: "$orgId", programId: "$programId", slabId: "$slabId" }, count: { $sum: 1 } } },
  { $match: { count: { $gt: 1 } } }
]);
```

If any rows returned → resolve (delete or reject extra DRAFTs) before applying M-4. Since this is a brand-new invariant post-Rework #5, pre-flight should pass on greenfield deployments.

### Rollback

```javascript
db.unified_tier_configs.dropIndex("uq_tier_one_active_draft_per_slab");
```

### Risk Assessment

- **Partial index safety**: Mongo partial unique indexes with a non-trivial filter are well-supported (MongoDB 3.2+).
- **Null collision caveat**: Without `slabId: { $exists: true, $ne: null }` in the filter, MongoDB would treat multiple docs with slabId=null as colliding on the unique key. The filter above prevents this for brand-new DRAFTs which legitimately have null slabId.
- **Write overhead**: Minor.

---

## M-5: Mongo unique index on tierUniqueId

### Forward Migration

```javascript
// M-5 FORWARD: Enforce tierUniqueId uniqueness globally across the collection
// Used by:
//   - Single-tier lookups via tierUniqueId (string external ID)
//   - Integration with downstream systems referencing the tier by its unique ID

db.unified_tier_configs.createIndex(
  { tierUniqueId: 1 },
  {
    name: "uq_utc_tier_unique_id",
    unique: true,
    background: true,
    partialFilterExpression: { tierUniqueId: { $exists: true, $ne: null } }
  }
);
```

### Backward Compatible?

YES (partial filter excludes null/missing — docs without tierUniqueId don't collide).

### Rollback

```javascript
db.unified_tier_configs.dropIndex("uq_utc_tier_unique_id");
```

### Risk Assessment

- tierUniqueId is a UUID-shaped string generated at DRAFT creation. No collisions expected in practice, but the unique index backstops the generator against cosmic-ray / bug scenarios.

---

## M-6: Mongo index on slabId (non-unique)

### Forward Migration

```javascript
// M-6 FORWARD: Non-unique index on slabId for envelope builder and parentId resolution
// The partial unique index M-4 covers (orgId, programId, slabId) for ACTIVE statuses,
// but an additional non-unique index on slabId alone supports SNAPSHOT history queries
// (which are not covered by M-4's filter) and cross-program audit lookups.

db.unified_tier_configs.createIndex(
  { slabId: 1 },
  {
    name: "idx_utc_slab_id",
    background: true,
    partialFilterExpression: { slabId: { $exists: true, $ne: null } }
  }
);
```

### Backward Compatible?
YES.

### Rollback

```javascript
db.unified_tier_configs.dropIndex("idx_utc_slab_id");
```

---

## M-7 (deferred): customer_enrollment index — for member count cron

Retained from Rework #3 scope. Evaluate when the member-count cron is implemented. Unchanged:

```sql
-- M-7 (deferred) — for member count aggregation
-- Only needed when GROUP BY current_slab_id becomes hot path
ALTER TABLE customer_enrollment
    ADD INDEX idx_ce_org_program_slab_active (org_id, program_id, current_slab_id, is_active),
    ALGORITHM=INPLACE, LOCK=NONE;
```

---

## Execution Order

```mermaid
flowchart LR
    subgraph SQL_preflight["SQL pre-flight (blocking)"]
      PF1[Check for duplicate<br/>program_id,name pairs]
    end
    subgraph Mongo_preflight["Mongo pre-flight (blocking)"]
      PF2[Check for multi-active<br/>docs per slabId]
    end
    subgraph SQL_migrations["SQL migrations"]
      M1[M-1: Add audit columns<br/>program_slabs<br/>FAST]
      M2[M-2: UNIQUE name constraint<br/>program_slabs]
    end
    subgraph Mongo_migrations["Mongo migrations"]
      M3[M-3: (orgId,programId,status)]
      M4[M-4: Partial UNIQUE on<br/>single-active-draft]
      M5[M-5: UNIQUE tierUniqueId]
      M6[M-6: slabId index]
    end
    subgraph Deploy
      D[Deploy emf-parent<br/>+ intouch-api-v3]
    end
    subgraph Deferred
      M7[M-7 deferred:<br/>customer_enrollment index]
    end

    PF1 --> M1 --> M2
    PF2 --> M3 --> M4 --> M5 --> M6
    M2 --> D
    M6 --> D
    D --> M7

    style M1 fill:#10b981,color:#fff
    style M2 fill:#10b981,color:#fff
    style M3 fill:#10b981,color:#fff
    style M4 fill:#10b981,color:#fff
    style M5 fill:#10b981,color:#fff
    style M6 fill:#10b981,color:#fff
    style D fill:#00d4ff,color:#000
    style M7 fill:#f59e0b,color:#000
    style PF1 fill:#ef4444,color:#fff
    style PF2 fill:#ef4444,color:#fff
```

**Execution sequence**:

1. **SQL pre-flight** — run duplicate-name detection. Must return zero rows before M-2.
2. **Mongo pre-flight** — run multi-active-doc detection. Must return zero rows before M-4. (On greenfield Rework #5 deployments this always passes.)
3. **SQL migrations M-1 → M-2** — take seconds on the small `program_slabs` table.
4. **Mongo migrations M-3 → M-6** — background builds, non-blocking.
5. **Deploy `emf-parent` + `intouch-api-v3`** — new code reads/writes using these schema elements.
6. **M-7 (deferred)** — when member count cron is implemented.

All six migrations (M-1..M-6) are safe to run before the deploy in either order (SQL block and Mongo block can run in parallel), as long as their respective pre-flights have passed.

---

## Estimated Duration

| Migration | Target size | Duration (MySQL 8 / MongoDB 5) | Blocks writes? |
|-----------|-------------|--------------------------------|----------------|
| M-1 | program_slabs (~low thousands) | < 1 second (INSTANT DDL) | No |
| M-2 | program_slabs | < 1 second (constraint check) | No |
| M-3 | unified_tier_configs (initially empty → growing) | < 1 second at launch | No (background) |
| M-4 | unified_tier_configs | < 1 second at launch | No (background) |
| M-5 | unified_tier_configs | < 1 second at launch | No (background) |
| M-6 | unified_tier_configs | < 1 second at launch | No (background) |
| M-7 (deferred) | customer_enrollment (~10M+ rows) | 5-30 min (INPLACE / LOCK=NONE) | No |

---

## Thrift IDL changes (downstream of M-1)

Since M-1 introduces three new `program_slabs` columns that must be populated from the MC flow, the Thrift `SlabInfo` struct must also carry these fields:

```thrift
struct SlabInfo {
  // ... existing fields ...
  10: optional string updatedBy;
  11: optional string approvedBy;
  12: optional i64    approvedAt;   // epoch millis UTC
}
```

**Backward compatibility**: All three fields are `optional`, so existing clients (pre-Rework #5 callers of `createSlabAndUpdateStrategies`) serialize without these fields and the server simply leaves the SQL columns NULL. No IDL-breaking change.

The Thrift server code (points engine) unpacks these optionals and writes to SQL via the generated SlabInfo DAO.

---

## Idempotency Summary

| Migration | Idempotent? | How |
|-----------|-------------|-----|
| M-1 | YES | INFORMATION_SCHEMA check before ADD COLUMN |
| M-2 | CONDITIONAL | Pre-flight removes duplicates first; constraint is idempotent on re-run (IF NOT EXISTS via catalog check) |
| M-3..M-6 | YES | MongoDB's `createIndex` is idempotent when name+spec match; collision detection if spec differs |

---

## Summary

- **6 migrations** required for Rework #5 (2 SQL + 4 Mongo)
- **1 migration deferred** (customer_enrollment index — evaluate when cron lands)
- **All backward-compatible** with conditional pre-flight for M-2 (SQL UNIQUE) and M-4 (Mongo partial unique)
- **All have rollback scripts** (DROP COLUMN, DROP CONSTRAINT, dropIndex)
- **No data migration required** — audit columns default to NULL, Mongo indexes are new
- **Thrift IDL extension**: 3 new optional fields on SlabInfo — fully backward-compatible
- **emf-parent still has no Flyway/Liquibase** — scripts are standalone and applied via deployment pipeline
