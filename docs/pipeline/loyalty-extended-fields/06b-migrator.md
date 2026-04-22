# Schema Migration Plan — Loyalty Extended Fields CRUD (CAP-183124)
> Phase: 6b (Migrator)
> Date: 2026-04-22

---

## Convention Baseline (from `custom_fields.sql` — C7)

| Aspect | Observed convention | loyalty_extended_fields deviation |
|--------|---------------------|-----------------------------------|
| PK type | `int(11) NOT NULL AUTO_INCREMENT` | `BIGINT NOT NULL AUTO_INCREMENT` — D-29 (program_id FK), ADR-02 (Long orgId) |
| PK structure | Composite `PRIMARY KEY (id, org_id)` | Single `PRIMARY KEY (id)` + UNIQUE KEY — simpler; org isolation via query filter |
| `org_id` type | `int(11)` | `BIGINT` — ADR-02 (Long orgId, avoids int/Long cast) |
| `created_on` | `datetime NOT NULL` | `TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP` — D-26 / G-01.1 (UTC storage) |
| Auto-update column | `auto_update_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | `updated_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` — cleaner name, matches API field `updated_on` |
| `is_active` nullability | `tinyint(1) NULL DEFAULT '1'` | `TINYINT(1) NOT NULL DEFAULT 1` — D-14 (stricter; no NULL allowed) |
| String collation | `COLLATE utf8mb4_unicode_ci` | Same — followed exactly |
| ENGINE/CHARSET | Not declared (DB default) | Not declared — follow convention |
| Index naming | Descriptive only (e.g. `field_label`, `auto_update_time`) — no `uq_`/`idx_` prefixes | `uq_` prefix for unique keys, `idx_` for non-unique — explicit prefix aids clarity; no conflict with convention (convention has no prefix rule) |
| Table COMMENT | None | None |
| New audit column | N/A | `updated_by VARCHAR(100) COLLATE utf8mb4_unicode_ci NULL` — no precedent; R-CT-06: VARCHAR preferred over int for username audit |

---

## File 1: `schema/dbmaster/warehouse/loyalty_extended_fields.sql`

**Full path**: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/loyalty_extended_fields.sql`

**Status**: Does NOT exist — must be created (C7: confirmed by `ls` of warehouse directory; no `loyalty_*.sql` files present).

```sql


CREATE TABLE `loyalty_extended_fields` (
    `id`            BIGINT        NOT NULL AUTO_INCREMENT,
    `org_id`        BIGINT        NOT NULL,
    `program_id`    BIGINT        NOT NULL,
    `name`          varchar(100)  COLLATE utf8mb4_unicode_ci NOT NULL,
    `scope`         varchar(50)   COLLATE utf8mb4_unicode_ci NOT NULL,
    `data_type`     varchar(30)   COLLATE utf8mb4_unicode_ci NOT NULL,
    `is_mandatory`  tinyint(1)    NOT NULL DEFAULT 0,
    `default_value` varchar(255)  COLLATE utf8mb4_unicode_ci NULL,
    `is_active`     tinyint(1)    NOT NULL DEFAULT 1,
    `created_on`    timestamp     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_on`    timestamp     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `updated_by`    varchar(100)  COLLATE utf8mb4_unicode_ci NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_org_prog_scope_name` (`org_id`, `program_id`, `scope`, `name`),
    KEY `idx_org_prog_scope_active` (`org_id`, `program_id`, `scope`, `is_active`)
);
```

### Convention deviations (intentional, each backed by an ADR or decision)

| Column / aspect | Deviation | Justification |
|-----------------|-----------|---------------|
| `id`, `org_id`, `program_id` | `BIGINT` instead of `int(11)` | D-29 (program_id is a BIGINT FK); ADR-02 (Long orgId to avoid int/Long cast in JPA PK) |
| `created_on` | `TIMESTAMP` instead of `DATETIME` | D-26 / ADR-07 / G-01.1 — UTC-aware storage; `DATETIME` is timezone-naive |
| `updated_on` | `TIMESTAMP` replacing `auto_update_time TIMESTAMP` | ADR-07 — cleaner name consistent with Thrift field `updatedOn` and API response `updated_on` |
| `is_active` nullability | `NOT NULL DEFAULT 1` instead of `NULL DEFAULT '1'` | D-14 — stricter; null active-flag has no business meaning |
| `PRIMARY KEY (id)` | Single-column PK instead of composite `(id, org_id)` | New table design; org isolation enforced via UNIQUE KEY and all queries include `org_id` filter (G-07.1) |
| `updated_by VARCHAR(100)` | New column with no precedent in `custom_fields.sql` | D-26 / R-CT-06 — stores `tillName` (string username); VARCHAR preferred over int for human-readable audit trail |

---

## File 2: `seed_data/dbmaster/warehouse/program_config_keys.sql`

**Full path**: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/seed_data/dbmaster/warehouse/program_config_keys.sql`

**Current state**: 47 rows (IDs 1–47) in a single `REPLACE INTO` statement (C7 — file read directly).

**Change**: Append one new row at the end of the existing VALUES list. The final entry currently ends at ID 47 (`ROLLING_EXPIRY_INCLUDE_ZERO_POINTS`). Add ID 48 as a new line in the same `REPLACE INTO` statement, or as a separate standalone `REPLACE INTO`:

```sql
REPLACE INTO `program_config_keys` (`id`, `name`, `value_type`, `default_value`, `label`, `added_by`, `added_on`, `is_valid`) VALUES
(48, 'MAX_EF_COUNT_PER_PROGRAM', 'NUMERIC', '10', 'Max Extended Fields Per Program', 0, '2026-04-22 00:00:00', 1);
```

**Format rationale**: All 47 existing entries use the same column list and value format. `added_by=0` is the system account convention (used by all existing rows). `is_valid=1` is required for the key to be picked up by `getAllValidProgramConfigKeys()`. `default_value='10'` per D-15.

**Usage in EMF**: `LoyaltyExtendedFieldServiceImpl.create()` reads `program_config_key_values` for `(orgId, programId, keyId=48)`. If no org/program-specific override exists, the `default_value='10'` from `program_config_keys` applies. Follows existing `ProgramConfigKeyValueValidatorImpl` pattern.

---

## Deployment Notes

- **Schema convention**: cc-stack-crm uses direct `CREATE TABLE` edits — no `ALTER TABLE`, no Flyway, no Liquibase. PR merge deploys schema via the cc-stack-crm pipeline.
- **Deployment order** (R-NEW-01 from Architect):
  1. cc-stack-crm PR merged → `loyalty_extended_fields` table created; `program_config_keys` row ID=48 applied
  2. emf-parent deployed → new Thrift methods #58–60 registered on port 9199
  3. intouch-api-v3 deployed → REST endpoints live, EF validation active
- **Seed data timing**: `program_config_keys` row (ID=48) must be present before the first EF Config create API call reaches EMF. Since cc-stack-crm deploys first, this is satisfied automatically.
- **MongoDB**: No migration needed. `SubscriptionProgram.ExtendedField` model change (`efId` added, `type` deleted) is fully additive — old documents deserialize with `efId=null` (A-03 / ADR-03).
- **Rollback**:
  - Schema: `DROP TABLE loyalty_extended_fields;` — safe, no foreign key references from other tables.
  - Seed: `DELETE FROM program_config_keys WHERE id = 48;`
  - Both rollbacks are independent and can be executed in any order.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Duplicate name race at INSERT (two concurrent creates with same org/program/scope/name) | Low | DB UNIQUE KEY `uq_org_prog_scope_name` is the last-resort guard; service layer checks uniqueness first (EMFException 8002 → HTTP 409) |
| `TIMESTAMP` timezone on MySQL host not set to UTC | Medium | MySQL server must be configured with `default-time-zone='+00:00'`; application sets UTC session context on connection; confirm with DBA before deploy |
| `updated_by VARCHAR(100)` DBA review (INFO-01) | Low | Deviation from `int(11)` convention in older tables is intentional (R-CT-06); confirm with cc-stack-crm DBA team before PR merge |
| `program_config_keys` ID=48 conflict if another team inserts ID=48 concurrently | Very Low | `REPLACE INTO` is idempotent — re-applying the seed is safe; ID=48 is the next sequential ID at time of writing (C7: file read directly) |
| Mandatory EF backward compat (H-8) | High | Out of scope for schema migration; tracked in Risk Register as R-NEW-02; product decision required before mandatory EF enforcement goes live |
