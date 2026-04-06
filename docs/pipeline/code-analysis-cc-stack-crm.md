# Schema Analysis: cc-stack-crm — Tier/Slab Tables

**Source repo**: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/`
**Date**: 2026-04-06
**Purpose**: Research for adding `active` column to `program_slabs` and supporting member-count queries.

---

## 1. `program_slabs` — Current DDL

File: `schema/dbmaster/warehouse/program_slabs.sql`

```sql
CREATE TABLE `program_slabs` (
  `id`              int(11) NOT NULL AUTO_INCREMENT COMMENT 'auto generated slab id',
  `org_id`          int(11) NOT NULL DEFAULT '0',
  `program_id`      int(11) NOT NULL COMMENT 'program to which the slab belongs to',
  `serial_number`   int(11) NOT NULL COMMENT 'Indicates the slab number in the sequence',
  `name`            varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'name of the slab',
  `description`     mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_on`      datetime NOT NULL,
  `auto_update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `metadata`        varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`,`org_id`),
  UNIQUE KEY `program_id` (`org_id`,`program_id`,`serial_number`),
  KEY `org_auto_time_idx` (`org_id`,`auto_update_time`),
  KEY `auto_update_time` (`auto_update_time`)
);
```

**Observations:**
- No `active` / `is_active` / `status` column currently.
- No explicit FK constraints defined in DDL (cc-stack-crm uses CREATE TABLE DDLs without FOREIGN KEY clauses).
- `serial_number` provides ordering; no concept of "enabled" state.

---

## 2. Related Tables

### 2a. `partner_program_slabs` — Partner tier definition

File: `schema/dbmaster/warehouse/partner_program_slabs.sql`

```sql
CREATE TABLE `partner_program_slabs` (
  `id`                 int(11) NOT NULL AUTO_INCREMENT,
  `org_id`             int(11) NOT NULL,
  `loyalty_program_id` int(11) NOT NULL,
  `partner_program_id` int(11) NOT NULL,
  `serial_number`      smallint(6) NOT NULL,
  `name`               varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_on`         datetime NOT NULL,
  `auto_update_time`   timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`,`org_id`),
  UNIQUE KEY `partner_program_id` (`org_id`,`loyalty_program_id`,`partner_program_id`,`serial_number`),
  UNIQUE KEY `partner_program_id_name` (`org_id`,`loyalty_program_id`,`partner_program_id`,`name`),
  KEY `auto_time_idx` (`auto_update_time`)
);
```

**Observation**: Also has no `is_active` column. Mirrors the gap in `program_slabs`.

### 2b. `partner_program_tier_sync_configuration` — Tier sync mapping

References both `partner_program_slab_id` and `loyalty_program_slab_id` (implicit FK to `program_slabs.id`).

```sql
CREATE TABLE partner_program_tier_sync_configuration (
  id                    INT NOT NULL AUTO_INCREMENT,
  org_id                INT NOT NULL,
  loyalty_program_id    INT NOT NULL,
  partner_program_id    INT NOT NULL,
  partner_program_slab_id INT NOT NULL,   -- FK → partner_program_slabs.id
  loyalty_program_slab_id INT NOT NULL,   -- FK → program_slabs.id
  created_on            DATETIME NOT NULL,
  auto_update_time      timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id,org_id)
);
```

### 2c. Strategy tables

File: `schema/dbmaster/warehouse/strategies.sql`

Stores slab upgrade strategies. References `program_id` but **not** `program_slabs.id` directly. No FK to `program_slabs`.

**No strategy table has a direct column referencing `program_slabs.id`.**

EMF rule/ruleset tables live in `schema/dbmaster/emf/` (ruleset_info.sql, rule_info.sql) — these reference promotion/event rulesets, not slab IDs directly.

---

## 3. Member-Tier Mapping (Member Count Source)

### Primary table: `customer_enrollment`

File: `schema/dbmaster/warehouse/customer_enrollment.sql`

```sql
CREATE TABLE `customer_enrollment` (
  `id`                   bigint(20) NOT NULL AUTO_INCREMENT,
  `org_id`               int(11) NOT NULL DEFAULT '0',
  `program_id`           int(11) NOT NULL,
  `customer_id`          int(11) NOT NULL,
  `entity_type`          enum('CUSTOMER','FLEET') DEFAULT 'CUSTOMER',
  `is_active`            tinyint(1) NOT NULL COMMENT 'whether the enrollment is active',
  `current_slab_id`      int(11) NOT NULL COMMENT 'slab under which the customer currently belongs',
  `lifetime_purchases`   decimal(15,3) NOT NULL DEFAULT '0.000',
  `visits`               int(11) NOT NULL DEFAULT '0',
  `enrollment_date`      datetime NOT NULL,
  `termination_date`     datetime DEFAULT NULL,
  `last_slab_change_date` datetime NOT NULL,
  `slab_expiry_date`     datetime DEFAULT '2114-12-31 23:59:59',
  `auto_update_time`     timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `event_log_id`         bigint(20) NOT NULL DEFAULT -1,
  PRIMARY KEY (`id`,`org_id`),
  UNIQUE KEY `program_id_idx` (`org_id`,`program_id`,`customer_id`,`entity_type`),
  KEY `idx_program_id_expiry_date_customer_id` (`program_id`,`slab_expiry_date`,`customer_id`),
  KEY `org_auto_time_idx` (`org_id`,`auto_update_time`),
  KEY `event_log_idx` (`org_id`,`event_log_id`),
  KEY `auto_update_time` (`auto_update_time`)
);
```

**Key points for member-count queries:**
- `current_slab_id` is the join column to `program_slabs.id` — this is the live tier assignment.
- `is_active` already exists here; filter on `is_active = 1` to count active members.
- **Index gap**: There is NO index on `(org_id, current_slab_id)` or `(org_id, program_id, current_slab_id)`. The only index that touches `current_slab_id` is via the UNIQUE key which includes `customer_id` — that won't help for aggregation by slab.
- **Recommended index for member count**: `(org_id, program_id, current_slab_id, is_active)` — needed for efficient `COUNT(*) GROUP BY current_slab_id`.

### Secondary table: `customer_slab_upgrade_history`

Stores historical slab transitions. Columns: `from_slab_id`, `to_slab_id`. Used for audit/history, not live tier state. No index on `from_slab_id` or `to_slab_id` alone.

### Partner member-tier mapping: `partner_program_enrollment`

```sql
`current_slab_id` int(11) NOT NULL  -- FK → partner_program_slabs.id
`is_active`       tinyint(1) DEFAULT 1
KEY `slab_expiry` (`current_slab_id`,`current_slab_expiry_date`)
```

Has `is_active` and an index starting with `current_slab_id`. Suitable for partner-slab member counts.

---

## 4. Tables Referencing `program_slabs` (Implicit FKs)

| Table | Column | Relationship |
|-------|--------|--------------|
| `customer_enrollment` | `current_slab_id` | Live member → slab assignment |
| `customer_slab_upgrade_history` | `from_slab_id`, `to_slab_id` | Historical slab transitions |
| `customers_downgrade_eligibility` | `current_slab_id` | Downgrade evaluation queue |
| `slab_change_details` | (via customer_slab_upgrade_history_id) | Audit trail |
| `partner_program_tier_sync_configuration` | `loyalty_program_slab_id` | Tier sync mapping |

---

## 5. Schema Patterns

### 5a. Soft-delete / active column convention

The dominant pattern across this codebase is:

```sql
`is_active` tinyint(1) NOT NULL DEFAULT 1
```

Examples observed:
| Table | Column definition |
|-------|------------------|
| `program` | `is_active tinyint(1) NOT NULL` (no default — required at INSERT) |
| `promotions` | `is_active tinyint(1) NOT NULL` |
| `partner_programs` | `is_active tinyint(1) NOT NULL` |
| `partner_program_enrollment` | `is_active tinyint(1) DEFAULT 1` |
| `customer_enrollment` | `is_active tinyint(1) NOT NULL` |
| `limits` | `is_active tinyint(1) NOT NULL DEFAULT 1` |
| `capping_config` | `is_active tinyint(1) NOT NULL DEFAULT 1` |
| `liability_split_ratio` | `is_active tinyint(1) NOT NULL` |
| `global_strategies_to_program_mapping` | `is_active tinyint(1) NOT NULL DEFAULT '1'` |
| `promotion_event_ruleset_mapping` | `is_active tinyint(1) NOT NULL DEFAULT '1'` (explicitly noted as "used for soft delete") |
| `alternate_currencies` | `is_active tinyint NOT NULL DEFAULT '1'` |

Two outliers use plain `active` (no `is_` prefix):
- `tender_code`: `active tinyint(1) NOT NULL`
- `customer_tracked_kpi`: `active tinyint(1) DEFAULT '1'`

**Conclusion**: Column to add should be `is_active tinyint(1) NOT NULL DEFAULT 1` to match the dominant convention.

### 5b. Migration pattern — CREATE TABLE only, no ALTER scripts

There are **zero ALTER TABLE statements** in any `.sql` file under `schema/dbmaster/`. The schema repo contains only `CREATE TABLE` DDLs — it is a snapshot/baseline, not a migration script repo. Flyway or a separate migration mechanism must be used for live ALTER operations (not stored in this repo).

This means:
- The `.sql` file in cc-stack-crm needs to be updated to add the column to the baseline.
- A separate migration script (Flyway V__.sql) must be created in the application repo (emf-parent) to ALTER the live table.

### 5c. Column naming conventions

- Timestamps: `created_on datetime`, `auto_update_time timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`
- Boolean flags: `is_active tinyint(1)` (not BOOLEAN, not BIT)
- IDs: `int(11)` for most, `bigint(20)` for high-volume tables (enrollment, points_ledger)
- Composite PKs always include `org_id`: `PRIMARY KEY (id, org_id)` — sharding key pattern
- Comments are consistently provided on most columns

---

## 6. Proposed Column Addition

### DDL change for `program_slabs.sql`

```sql
`is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT 'Soft-delete flag: 1=active, 0=inactive'
```

Position: After `metadata` column, before the closing of column definitions.

### Index recommendation

For the member count query `SELECT current_slab_id, COUNT(*) FROM customer_enrollment WHERE org_id=? AND program_id=? AND is_active=1 GROUP BY current_slab_id`:

```sql
KEY `idx_program_slab_active` (`org_id`, `program_id`, `current_slab_id`, `is_active`)
```

This index does not exist on `customer_enrollment` today and would need to be added alongside the feature.

### Migration script (Flyway, to go in emf-parent)

```sql
ALTER TABLE program_slabs
  ADD COLUMN `is_active` tinyint(1) NOT NULL DEFAULT 1
    COMMENT 'Soft-delete flag: 1=active, 0=inactive'
  AFTER `metadata`;
```

The `DEFAULT 1` ensures all existing rows are treated as active — safe for online schema change (no backfill needed).

---

## 7. Summary of Gaps and Risks

| Item | Finding | Risk |
|------|---------|------|
| No `is_active` on `program_slabs` | Confirmed — column is absent | Migration needed |
| No `is_active` on `partner_program_slabs` | Confirmed — same gap | May need parallel change |
| No index on `customer_enrollment(org_id, program_id, current_slab_id)` | Confirmed — missing | Member count queries will full-scan; index needed |
| No FK constraints in DDL | Confirmed — referential integrity is application-enforced | Soft-delete in `program_slabs` must be handled carefully; `customer_enrollment.current_slab_id` can still point to inactive slabs |
| Schema repo has no ALTER scripts | Confirmed — baseline DDL only | Flyway migration must live in emf-parent, not cc-stack-crm |
