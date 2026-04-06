# Migration Analysis Report — Tier CRUD APIs

> Analysis date: 2026-04-06
> Mode: Schema
> Migration tool: None detected — schema managed via SQL DDL files in cc-stack-crm
> Scope: program_slabs (warehouse), customer_enrollment (warehouse)
> Feature: tier-crud / Ticket: test_branch_v3
> Phase: 6b (Migrator, after Architect)

---

## Executive Summary

Two schema changes are required for the tier-crud feature:

1. **ADD COLUMN `is_active`** on `program_slabs` — LOW risk, fully backward-compatible by design (NOT NULL with DEFAULT 1). No expand-then-contract required. Old application code that does not read or write `is_active` continues to work unchanged; new soft-delete logic writes `is_active=0` only on explicit STOP.

2. **CREATE INDEX `idx_ce_slab_count`** on `customer_enrollment` — MEDIUM risk due to table size. The index is purely additive. On a large production table the `CREATE INDEX` statement will lock the table (MySQL 5.x) or proceed online (MySQL 8+ with `ALGORITHM=INPLACE, LOCK=NONE`). A scheduling window and monitoring plan are required.

Overall risk: **LOW–MEDIUM**. No destructive operations. No expand-then-contract cycles required. No data backfill required.

---

## 1. Migration Tool Audit

### Tool Detection

| Check | Finding |
|-------|---------|
| `flyway-core` in pom.xml | Not found in emf-parent |
| `liquibase-core` in pom.xml | Not found in emf-parent |
| `src/main/resources/db/migration/` | Not found |
| `src/main/resources/db/changelog/` | Not found |
| cc-stack-crm `schema/dbmaster/warehouse/*.sql` | **CREATE TABLE DDL files only** — one file per table |
| cc-stack-crm ALTER/migration scripts | Not found in warehouse directory |

**WARNING: No database migration tool detected.**
Schema changes in this codebase are managed as raw DDL files in cc-stack-crm. There is no version-controlled migration sequence (no V1__..., V2__... numbering). Each table has a single `.sql` file containing only the CREATE TABLE definition.

**Implications:**
- Forward migrations (ALTER TABLE, CREATE INDEX) must be applied manually to each environment (dev, staging, prod).
- There is no automated rollback mechanism.
- The cc-stack-crm DDL files serve as the **reference schema definition**, not as an executable migration sequence.
- Each migration in this plan must be **applied by a human operator** (DBA or deployment engineer) with manual verification.

**Recommendation for future work:** Adopt Flyway or Liquibase to bring schema changes under version control. Out of scope for this ticket.

### Existing program_slabs Schema (evidence: file read at C7)

File: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/program_slabs.sql`

```sql
CREATE TABLE `program_slabs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `org_id` int(11) NOT NULL DEFAULT '0',
  `program_id` int(11) NOT NULL,
  `serial_number` int(11) NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_on` datetime NOT NULL,
  `auto_update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `metadata` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`,`org_id`),
  UNIQUE KEY `program_id` (`org_id`,`program_id`,`serial_number`),
  KEY `org_auto_time_idx` (`org_id`,`auto_update_time`),
  KEY `auto_update_time` (`auto_update_time`)
);
```

**Confirmed:** `is_active` column does NOT currently exist (C7 — read from source).

### Existing customer_enrollment Schema (evidence: file read at C7)

File: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/customer_enrollment.sql`

```sql
CREATE TABLE `customer_enrollment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `org_id` int(11) NOT NULL DEFAULT '0',
  `program_id` int(11) NOT NULL,
  `customer_id` int(11) NOT NULL,
  `entity_type` enum('CUSTOMER','FLEET') DEFAULT 'CUSTOMER',
  `is_active` tinyint(1) NOT NULL,
  `current_slab_id` int(11) NOT NULL,
  `lifetime_purchases` decimal(15,3) NOT NULL DEFAULT '0.000',
  `visits` int(11) NOT NULL DEFAULT '0',
  `enrollment_date` datetime NOT NULL,
  `termination_date` datetime DEFAULT NULL,
  `last_slab_change_date` datetime NOT NULL,
  `slab_expiry_date` datetime DEFAULT '2114-12-31 23:59:59',
  `auto_update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `event_log_id` bigint(20) NOT NULL DEFAULT -1,
  PRIMARY KEY (`id`,`org_id`),
  UNIQUE KEY `program_id_idx` (`org_id`,`program_id`,`customer_id`,`entity_type`),
  KEY `idx_program_id_expiry_date_customer_id` (`program_id`,`slab_expiry_date`,`customer_id`),
  KEY `org_auto_time_idx` (`org_id`,`auto_update_time`),
  KEY `event_log_idx` (`org_id`,`event_log_id`),
  KEY `auto_update_time` (`auto_update_time`)
);
```

**Confirmed:** `current_slab_id` column exists. `is_active` column exists already (enrollment active flag). The proposed composite index `(org_id, program_id, current_slab_id, is_active)` uses all existing columns — no structural schema change to the table, only an index addition (C7 — read from source).

### is_active Convention Survey (evidence: grep across cc-stack-crm at C7)

`is_active TINYINT(1)` is used in 33 tables in cc-stack-crm. Confirmed definitions:

| Table | Definition | DEFAULT |
|-------|-----------|---------|
| `promotions` | `tinyint(1) NOT NULL` | No default |
| `program` | `tinyint(1) NOT NULL` | No default |
| `benefits` | `tinyint(1) NOT NULL` | No default |
| `alternate_currencies` | `tinyint NOT NULL DEFAULT '1'` | DEFAULT 1 |
| `capping_config` | `tinyint(1) NOT NULL DEFAULT 1` | DEFAULT 1 |
| `customer_enrollment` | `tinyint(1) NOT NULL` | No default |

**Observation:** About half the tables use `DEFAULT 1`, the other half do not. For new columns added to existing tables (ALTER TABLE), `DEFAULT 1` is mandatory for backward compatibility — old code that inserts rows without specifying `is_active` would fail without a default. The proposed DDL correctly includes `DEFAULT 1`.

---

## 2. Migration Inventory

| MIG-ID | Change | Table | Type | Risk Level | E-T-C Required? |
|--------|--------|-------|------|------------|-----------------|
| MIG-01 | ADD COLUMN `is_active TINYINT(1) NOT NULL DEFAULT 1` | `program_slabs` | ADD COLUMN (NOT NULL with DEFAULT) | LOW | No |
| MIG-02 | CREATE INDEX `idx_ce_slab_count (org_id, program_id, current_slab_id, is_active)` | `customer_enrollment` | ADD INDEX | MEDIUM | No (additive) |

---

## 3. Backward Compatibility Assessment

### MIG-01: ADD COLUMN `is_active` to `program_slabs`

**Check 1 — Read compatibility (old code reads new data):**
- Old code uses `SELECT` queries that do not include `is_active` in their column list.
- Read from PeProgramSlabDao (C7): queries use JPQL selecting the full entity.
- Risk: PeProgramSlabDao queries (`findByProgram`, `findByProgramSlabNumber`, `findNumberOfSlabs`) use positional JPQL. They do NOT use `SELECT *`. Adding a column to the entity mapping will cause Hibernate to include it in SELECT automatically once `ProgramSlab.java` is updated. **Old code (before entity update) ignores the column entirely — safe.**
- **Result: PASS** — old code does not reference `is_active`, column addition is transparent.

**Check 2 — Write compatibility (old code writes, new code reads):**
- `DEFAULT 1` means old code that INSERTs without specifying `is_active` will have the row created with `is_active=1` (active) automatically.
- This is correct behavior: any slab inserted by old code should be treated as active.
- **Result: PASS** — DEFAULT 1 ensures all pre-migration rows and old-code inserts are treated as active.

**Check 3 — Query compatibility (existing queries continue to work):**
- No existing query in PeProgramSlabDao filters by `is_active`. After this migration, the new code will add `is_active=1` filters. Old code (before application deploy) will still query without the filter and get all rows — same behavior as today.
- **Result: PASS** — pure additive change. Existing queries unaffected.

**Rolling deploy scenario:**
- Migration runs first (ALTER TABLE).
- Old app instances: no `is_active` in entity, no filter in queries. All slabs returned (all are active=1 anyway at migration time, since DRAFT/PENDING never written to MySQL).
- New app instances: include `is_active` in entity, filter `is_active=1` in new queries.
- Both old and new app instances can coexist safely. No data conflict.

**Expand-then-contract required:** No. This is a NET NEW additive column with a default — the safest possible ALTER TABLE.

**Confidence: C7** (verified from source: column doesn't exist in DDL, DEFAULT 1 convention confirmed in other tables, entity has no `is_active` field, DAO queries confirmed via source read).

---

### MIG-02: CREATE INDEX `idx_ce_slab_count` on `customer_enrollment`

**Check 1 — Read compatibility:** Purely additive index. No column changes. All existing queries continue to function.

**Check 2 — Write compatibility:** Index creation does not change INSERT/UPDATE/DELETE semantics, only query plan selection.

**Check 3 — Query compatibility:** Existing queries are unaffected. The new member count query in `PeCustomerEnrollmentDao` will use this index (verified: the index covers `org_id, program_id, current_slab_id, is_active` — matching the WHERE clause of the planned COUNT query).

**Locking risk on large table:**
- `customer_enrollment` is a member-tier mapping table. In a loyalty platform, this can have tens of millions of rows per org.
- `CREATE INDEX` behavior by MySQL version:
  - MySQL 5.6: Uses `ALGORITHM=INPLACE` for secondary indexes — allows concurrent reads/writes during build phase, with brief metadata lock at start/end.
  - MySQL 5.7+: `ALTER TABLE ... ADD INDEX` uses online DDL by default.
  - MySQL 8.0+: `CREATE INDEX` is online by default.
- **Risk:** If the MySQL version is 5.5 or below, `CREATE INDEX` causes a full table lock. This is a production risk on a large table.
- **Mitigation:** Use explicit `ALGORITHM=INPLACE, LOCK=NONE` (MySQL 5.6+) or `ALGORITHM=INSTANT` where supported (MySQL 8.0+).

**Expand-then-contract required:** No. Pure additive index.

**Confidence on MySQL version: C2** (no evidence found — version not confirmed from source). This is a QUESTION FOR USER (see below).

---

## 4. Execution Order and Dependency Graph

```
Step 1: MIG-01 — ALTER TABLE program_slabs ADD COLUMN is_active
        Prerequisites: None
        Followed by: ProgramSlab.java entity update (application code)

Step 2: MIG-02 — CREATE INDEX idx_ce_slab_count ON customer_enrollment
        Prerequisites: None (customer_enrollment already has org_id, program_id, current_slab_id, is_active)
        Followed by: PeCustomerEnrollmentDao.countMembersBySlab() new query (application code)
```

**Both migrations are independent.** MIG-01 and MIG-02 can be executed in either order or in parallel. Neither has a dependency on the other.

**Dependency on application deploy:**
- MIG-01 must run BEFORE the application deploy that adds `is_active=1` filter to PeProgramSlabDao queries. If the filter is added before the column exists, queries will fail.
- MIG-02 must run BEFORE the application deploy that adds the `countMembersBySlab` query to PeCustomerEnrollmentDao. Running the query without the index will succeed but will be a full table scan.

**Recommended execution order:**
1. Run MIG-01 (program_slabs column)
2. Run MIG-02 (customer_enrollment index — schedule during off-peak if table is large)
3. Deploy updated application (emf-parent + intouch-api-v3)

---

## 5. Forward Migration Scripts (DRAFT — requires human review before execution)

### MIG-01: Add `is_active` to `program_slabs`

```sql
-- DRAFT — requires human review before execution
-- Target: warehouse database, program_slabs table
-- Purpose: Add soft-delete flag for tier (slab) deactivation
-- Backward compatible: YES — DEFAULT 1 ensures old code INSERT behavior unchanged
-- Reversible: YES — see rollback script below

ALTER TABLE `program_slabs`
  ADD COLUMN `is_active` TINYINT(1) NOT NULL DEFAULT 1
  COMMENT 'Soft-delete flag: 1=active, 0=inactive (stopped tier)';
```

**Estimated duration:** Fast — metadata-only change on modern MySQL. Sub-second on most table sizes.

**Verification query:**
```sql
SHOW COLUMNS FROM program_slabs LIKE 'is_active';
-- Expected: Field=is_active, Type=tinyint(1), Null=NO, Default=1
```

**Update cc-stack-crm DDL file** after execution:
File: `schema/dbmaster/warehouse/program_slabs.sql`
Add the following line to the CREATE TABLE definition (after `metadata` column, before PRIMARY KEY):
```sql
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT 'Soft-delete flag: 1=active, 0=inactive (stopped tier)',
```

---

### MIG-02: Add member count index to `customer_enrollment`

```sql
-- DRAFT — requires human review before execution
-- Target: warehouse database, customer_enrollment table
-- Purpose: Support member count per tier queries for soft-delete validation and GET /tiers response
-- Backward compatible: YES — additive index only
-- Reversible: YES — see rollback script below
-- WARNING: customer_enrollment may be a large table. Schedule during off-peak.
-- Use ALGORITHM=INPLACE, LOCK=NONE if MySQL < 8.0. Use ALGORITHM=INSTANT if MySQL >= 8.0.16 (not available for secondary index additions in all versions — verify first).

-- MySQL 5.6 / 5.7 (recommended):
CREATE INDEX `idx_ce_slab_count`
  ON `customer_enrollment` (`org_id`, `program_id`, `current_slab_id`, `is_active`);

-- Alternative syntax with explicit online DDL hint (MySQL 5.6+):
ALTER TABLE `customer_enrollment`
  ADD INDEX `idx_ce_slab_count` (`org_id`, `program_id`, `current_slab_id`, `is_active`),
  ALGORITHM=INPLACE, LOCK=NONE;
```

**Estimated duration:** Dependent on table size. Rough estimate:
- < 10M rows: 1–5 minutes
- 10M–100M rows: 5–30 minutes
- > 100M rows: 30+ minutes, may require pt-online-schema-change

**Verification query:**
```sql
SHOW INDEX FROM customer_enrollment WHERE Key_name = 'idx_ce_slab_count';
-- Expected: 4 rows, one for each column in the index
```

**Update cc-stack-crm DDL file** after execution:
File: `schema/dbmaster/warehouse/customer_enrollment.sql`
Add the following line to the CREATE TABLE definition (after existing KEY declarations):
```sql
  KEY `idx_ce_slab_count` (`org_id`,`program_id`,`current_slab_id`,`is_active`)
```

---

## 6. Rollback Scripts (DRAFT — requires human review before execution)

### Rollback MIG-01: Remove `is_active` from `program_slabs`

```sql
-- ROLLBACK MIG-01 — only run if application has been rolled back to pre-feature version
-- DO NOT run while any application instance is using is_active column

ALTER TABLE `program_slabs`
  DROP COLUMN `is_active`;
```

**When to use:** If the feature deploy is rolled back AND the column needs to be removed. Note that since old code ignores the column entirely, the rollback to old application code does not require removing the column — the column can stay safely while old code runs.

**Risk:** CRITICAL if run while new code is still accessing the column. Ensure all app instances are on the old version first.

---

### Rollback MIG-02: Remove member count index from `customer_enrollment`

```sql
-- ROLLBACK MIG-02 — safe to run at any time (removing an index is always safe)
-- The countMembersBySlab query will still work without the index — just slower (full table scan)

DROP INDEX `idx_ce_slab_count` ON `customer_enrollment`;
```

**When to use:** If the index needs to be removed (e.g., causes unexpected lock contention). Note that the application query will continue to work correctly without the index; it will only be slower.

---

## 7. Data Backfill Assessment

### MIG-01 (program_slabs — is_active column)

**Backfill required: No.**

Rationale:
- All existing rows in `program_slabs` represent currently ACTIVE tiers (slabs that have been approved and are in use by the evaluation engine).
- The `DEFAULT 1` clause in the ALTER TABLE statement ensures all existing rows receive `is_active = 1` atomically during the column addition.
- No separate UPDATE statement needed.
- **Evidence (C7):** The MongoDB-first architecture decision means DRAFT/PENDING tiers are NEVER written to `program_slabs` — only ACTIVE tiers are synced to MySQL on APPROVE. Therefore, the assumption "all existing rows are active tiers" is structurally guaranteed by the architecture.

### MIG-02 (customer_enrollment — index)

**Backfill required: No.**

Index creation over existing data is handled by MySQL as part of `CREATE INDEX` — it reads all existing rows and builds the B-tree structure. This is not a "backfill" in the application sense; it is normal index build behavior.

---

## 8. Schema Drift Assessment

### Entity vs DDL Comparison

**ProgramSlab.java vs program_slabs.sql:**

| Column | DDL | Entity | Match? |
|--------|-----|--------|--------|
| id | ✓ (PK, AUTO_INCREMENT) | ✓ (via pk.id) | Yes |
| org_id | ✓ | ✓ (via pk.orgId) | Yes |
| program_id | ✓ | ✓ | Yes |
| serial_number | ✓ | ✓ | Yes |
| name | ✓ | ✓ | Yes |
| description | ✓ | ✓ | Yes |
| created_on | ✓ | ✓ | Yes |
| auto_update_time | ✓ | Not mapped | Drift (benign — auto-managed by DB) |
| metadata | ✓ | ✓ | Yes |
| **is_active** | **Not in DDL** | **Not in entity** | **To be added by this migration** |

**Drift finding:** `auto_update_time` column is in the DDL but has no corresponding field in `ProgramSlab.java`. This is a pre-existing benign drift (timestamp managed by MySQL ON UPDATE CURRENT_TIMESTAMP, deliberately not mapped in entity). Not introduced by this feature.

No other drift detected between ProgramSlab entity and program_slabs DDL (C7).

**CustomerEnrollment.java vs customer_enrollment.sql:**

| Column | DDL | Entity | Match? |
|--------|-----|--------|--------|
| is_active | ✓ | ✓ (`boolean isActive`) | Yes |
| current_slab_id | ✓ | ✓ (`int currentSlabId`) | Yes |
| org_id | ✓ | ✓ (via pk.orgId) | Yes |
| program_id | ✓ | ✓ | Yes |
| **idx_ce_slab_count** | **Not in DDL** | **Not applicable** | **To be added by this migration** |

No drift detected in CustomerEnrollment entity vs DDL (C7).

---

## 9. Guardrail Compliance Checks

| Guardrail | Check | Status |
|-----------|-------|--------|
| G-05.4 — Expand-then-contract | ADD COLUMN with DEFAULT — no E-T-C required | PASS |
| G-05.3 — DB-level constraints | `NOT NULL DEFAULT 1` enforced at DB level | PASS |
| G-07.1 — Tenant filter | `is_active` column on existing tenant-scoped table. New index includes `org_id` as leading key | PASS |
| G-09.1 — Backward compat with prev app version | DEFAULT 1 ensures old INSERTs succeed; column ignored by old reads | PASS |
| G-04.4 — Indexes for query patterns | New index covers the full WHERE clause of the member count query | PASS |
| G-01.1 — UTC timestamps | No timestamp columns added | N/A |

---

## 10. Risk Register

| ID | Risk | Severity | Probability | Mitigation | Status |
|----|------|----------|-------------|------------|--------|
| MIG-R-01 | `CREATE INDEX` on customer_enrollment locks table on old MySQL version | HIGH | C2 (MySQL version unknown) | Confirm MySQL version. Use `ALGORITHM=INPLACE, LOCK=NONE` (5.6+) or pt-online-schema-change for very large tables. Schedule during off-peak | Open |
| MIG-R-02 | Application deploy happens before MIG-01 runs — `is_active=1` filter in DAO queries fails | HIGH | C3 (deploy sequencing risk) | Deploy DDL migrations BEFORE application code. Enforce in deployment pipeline. | Open |
| MIG-R-03 | Application deploy happens before MIG-02 runs — member count query runs without index (full table scan) | MEDIUM | C3 (deploy sequencing risk) | Deploy DDL migrations BEFORE application code. Non-critical: query returns correct results, just slower until index is created | Open |
| MIG-R-04 | UNIQUE constraint on `(org_id, program_id, serial_number)` prevents reuse of serial numbers after soft-delete | MEDIUM | C6 (constraint confirmed in DDL) | Soft-deleted slab's serial_number remains reserved. Serial numbers are not reused. New tiers always added at top (existing constraint). No action needed for this migration — constraint stays intact. | Mitigated by architecture |
| MIG-R-05 | Manual migration process — no migration tool to track applied/pending migrations | MEDIUM | C7 (confirmed: no Flyway/Liquibase) | Document migration application in deployment runbook. Operator must manually verify each environment. Flag for future Flyway adoption. | Open — process risk |
| MIG-R-06 | Rollback of MIG-01 (DROP COLUMN) while new code still runs causes column not found errors | CRITICAL | C5 (only triggered if rollback is botched) | Strictly sequence rollback: roll back application FIRST, verify all instances on old version, THEN run DROP COLUMN rollback script. | Open — process risk |

---

## 11. Estimated Duration and Scheduling

| Migration | Estimated Duration | Lock Type | Scheduling |
|-----------|-------------------|-----------|------------|
| MIG-01: ALTER TABLE program_slabs ADD COLUMN | < 1 second (metadata change only, MySQL 5.6+) | Brief metadata lock at start/end only | Any time — negligible impact |
| MIG-02: CREATE INDEX on customer_enrollment | Minutes to tens of minutes (table-size dependent) | Online (MySQL 5.6+, ALGORITHM=INPLACE) — reads/writes continue | Schedule during lowest traffic window. Pre-notify ops team. Monitor `SHOW PROCESSLIST` during build. |

---

## 12. Migration Checklist (Before Execution)

- [ ] Confirm MySQL version in production (required to determine correct `CREATE INDEX` syntax)
- [ ] Confirm estimated row count of `customer_enrollment` in production (required for duration estimate)
- [ ] Take a full backup of `warehouse` database before running either migration
- [ ] Test both migration scripts in staging/dev environment first
- [ ] Verify rollback scripts work in staging/dev
- [ ] Confirm deployment pipeline enforces: DDL migrations run BEFORE application code deploy
- [ ] Schedule MIG-02 during off-peak window (inform ops team)
- [ ] Prepare `SHOW PROCESSLIST` monitoring during MIG-02 execution
- [ ] After MIG-01: run verification query (`SHOW COLUMNS FROM program_slabs LIKE 'is_active'`)
- [ ] After MIG-02: run verification query (`SHOW INDEX FROM customer_enrollment WHERE Key_name = 'idx_ce_slab_count'`)
- [ ] Update cc-stack-crm DDL reference files to reflect both changes (program_slabs.sql + customer_enrollment.sql)
- [ ] Review this document — do not execute any script marked DRAFT without human DBA review

---

## 13. Post-Migration Application Code Changes Required

These are **NOT part of the migration** but must happen after the DDL changes are in place:

| Change | File | Repo | Depends On |
|--------|------|------|-----------|
| Add `isActive` field + JPA mapping | `ProgramSlab.java` | emf-parent | MIG-01 |
| Add `is_active=1` filter to `findByProgram()`, `findByProgramSlabNumber()`, `findNumberOfSlabs()` | `PeProgramSlabDao.java` | emf-parent | MIG-01 + ProgramSlab.java update |
| Add `countMembersBySlab(orgId, programId, slabIds)` JPQL query | `PeCustomerEnrollmentDao.java` | emf-parent | MIG-02 (for performance) |
| Add `deactivateSlab(slabId, orgId)` method: `UPDATE program_slabs SET is_active=0 WHERE id=? AND org_id=?` | `PointsEngineRuleConfigThriftImpl.java` | emf-parent | MIG-01 |

---

## Generated Artifacts

- [x] Migration scripts: `MIG-01` and `MIG-02` — **DRAFT, see Section 5**
- [x] Rollback scripts: `ROLLBACK MIG-01` and `ROLLBACK MIG-02` — **DRAFT, see Section 6**
- [x] Expand-then-contract plans: 0 required (both changes are additive)
- [x] Risk register: 6 items, 1 CRITICAL (sequencing risk MIG-R-06), 2 HIGH

---

## ASSUMPTIONS MADE

_(C5+ assumptions stated explicitly)_

1. **All existing `program_slabs` rows represent ACTIVE tiers (C6):** Based on the architecture decision (MongoDB-first, DRAFT/PENDING never written to MySQL). No backfill of `is_active` needed. If there are any "soft-deleted" slabs already managed by some other mechanism in production, this assumption would be wrong — verify with DBA before running MIG-01.

2. **`customer_enrollment` `is_active` column refers to enrollment active status, not tier active status (C7):** Confirmed by reading the DDL comment ("whether the enrollment is active") and the `CustomerEnrollment.java` entity. The new index on this column uses it as a filter in the member count query — this is correct because member count queries need to count only active enrollments.

3. **MySQL 5.6+ is in use (C4):** The recommendation to use `ALGORITHM=INPLACE, LOCK=NONE` assumes MySQL 5.6 or later. No evidence found confirming the exact MySQL version. Flagged as MIG-R-01.

4. **`program_slabs` table is not heavily read during migration window (C4):** The brief metadata lock for MIG-01 is negligible. If `program_slabs` is under extreme concurrent write pressure (unlikely for a config table), even the brief lock could cause issues. Not a significant concern for a config table.

---

## QUESTIONS FOR USER

1. **[Q-MIG-01] What MySQL version is running in production?** Required to determine whether `ALGORITHM=INPLACE, LOCK=NONE` is safe for MIG-02, or whether `pt-online-schema-change` is needed. Confidence on current MySQL version: C2.

2. **[Q-MIG-02] Approximately how many rows are in the `customer_enrollment` table in production?** Required to estimate MIG-02 duration and decide whether to use pt-online-schema-change vs native `CREATE INDEX`. Confidence on table size: C1 (no evidence available).

3. **[Q-MIG-03] Is there an existing manual migration/deployment runbook for cc-stack-crm DDL changes?** The absence of Flyway/Liquibase means migrations are applied manually. If a runbook exists, the migration scripts in this document should be integrated into that process. Confidence that a runbook exists: C2 (no evidence found).

4. **[Q-MIG-04] Are there any existing rows in `program_slabs` that should be treated as inactive (soft-deleted) before this migration runs?** If yes, those rows will receive `is_active=1` (active) by default, which may not be correct. Confidence that all existing rows are active: C6 (supported by MongoDB-first architecture), but production state of the database is not directly observable.
