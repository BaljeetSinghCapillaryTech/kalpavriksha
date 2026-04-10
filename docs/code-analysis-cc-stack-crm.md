# Code Analysis -- cc-stack-crm

> Phase: 5 (Codebase Research)
> Repo: /Users/baljeetsingh/IdeaProjects/cc-stack-crm
> Role: DB schema definitions -- partner_programs table schema reference

---

## Key Findings

1. **partner_programs table** (schema/dbmaster/warehouse/partner_programs.sql):
   - Columns: id (auto-increment), org_id, loyalty_program_id, partner_program_identifier, name (unique per org), type (EXTERNAL/SUPPLEMENTARY), description, is_active, is_tier_based, points_exchange_ratio, expiry_date, backup_partner_program_id, created_on, auto_update_time
   - PK: (id, org_id)
   - Unique key: (org_id, name)
   - Indexes: auto_update_time, (org_id, auto_update_time)

2. **No schema changes needed.** KD-07 mandates MongoDB-first architecture. The partner_programs MySQL table is only written to on ACTIVE transition via Thrift. No new columns, no new tables, no Flyway migrations.

3. **partner_programs.name UNIQUE constraint per org** -- the subscription name in MongoDB must match what is sent to createOrUpdatePartnerProgram. The PartnerProgramInfo.partnerProgramName maps to this column.

---

## Verification: "0 Modifications" Claim

**Evidence**: KD-07 explicitly states "NO schema changes to partner_programs table". Subscription config lives in MongoDB. MySQL is only the Thrift write-back target with existing schema.

**Confidence**: C7 (read actual SQL schema, verified against KD-07)

---

## Per-Repo Change Inventory

| New Files | Modified Files | Why | Confidence |
|-----------|---------------|-----|------------|
| 0 | 0 | No MySQL schema changes per KD-07. Subscription config in MongoDB. | C7 |
