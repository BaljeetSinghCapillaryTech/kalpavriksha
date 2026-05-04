# Highest Tier Soft Deletion — Impact Analysis

**Date**: 2026-04-20  
**Scope**: `emf-parent` (points engine, strategies, entities) + `intouch-api-v3` (REST API layer)  
**Type**: Soft deletion (logical delete via `isDeleted` flag — row remains in DB)  
**Author**: Research Analysis  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Tier Semantics — What is the "Highest Tier"?](#2-tier-semantics--what-is-the-highest-tier)
3. [Current State — Entity & Schema](#3-current-state--entity--schema)
4. [Current State — No Delete API Exists](#4-current-state--no-delete-api-exists)
5. [Impact on Strategies](#5-impact-on-strategies)
6. [Impact on Customers Currently on the Highest Tier](#6-impact-on-customers-currently-on-the-highest-tier)
7. [Impact on Historical Data & Reporting](#7-impact-on-historical-data--reporting)
8. [Impact on Caches & Thrift Integration](#8-impact-on-caches--thrift-integration)
9. [Foreign Key & Referential Integrity](#9-foreign-key--referential-integrity)
10. [Risks — Severity Ranked](#10-risks--severity-ranked)
11. [Required Changes to Implement Soft Deletion](#11-required-changes-to-implement-soft-deletion)
12. [Step-by-Step Process to Delete the Highest Tier](#12-step-by-step-process-to-delete-the-highest-tier)
13. [Strategy Deep Dive — Exact Breakage vs. Safe Paths](#13-strategy-deep-dive--exact-breakage-vs-safe-paths)
14. [Supplementary Program Impact — Full Breakage Analysis](#14-supplementary-program-impact--full-breakage-analysis)
15. [Open Questions](#15-open-questions)

---

## 1. Executive Summary

**Current State**: There is **no tier deletion capability** in the system today — no API endpoint, no service method, no soft-delete field on the `program_slabs` table. Tiers can only be created and updated.

**Feasibility**: Soft deletion of the highest tier is implementable but **non-trivial**. It requires:
- A new DB column (`is_deleted`) with a Flyway migration
- A new API endpoint with a maker-checker flow
- Pre-deletion validation guards (customers on tier, strategy references)
- Query-level filtering across emf-parent strategy and enrollment services
- Cache invalidation

**Highest Risk**: Customers who are currently on the highest tier will be in an **orphaned state** if deletion proceeds without a migration/reassignment plan. Downgrade strategies that reference the highest tier by its slab ID (stored as JSON in the `strategy` entity) will also produce NPEs or silent failures.

**Confidence levels** follow the C1–C7 scale (C7 = verified from source code; C1 = speculative).

---

## 2. Tier Semantics — What is the "Highest Tier"?

**C7 — Verified from source:**

Tiers are ordered by the `serial_number` column in the `program_slabs` table.

| serialNumber | Position in Hierarchy |
|---|---|
| 1 | **Lowest / base tier** (e.g., Bronze) |
| 2 | Mid tier (e.g., Silver) |
| N (max) | **Highest tier** (e.g., Platinum) |

**Evidence:**
- `SlabDowngradeStrategyImpl.java:111`: `if (slabNumber <= 1 || slabConfig == null || !slabConfig.shouldDowngrade())` → slab with serialNumber=1 gets a 100-year expiry (no downgrade possible from the base tier).
- `TierFacade.java:69`: `tiers.sort((a, b) -> Integer.compare(a.getSerialNumber(), b.getSerialNumber()))` → ascending sort, slab 1 appears first.

**Definition**: "Highest tier" = the `ProgramSlab` row with the **maximum `serial_number`** for a given `(org_id, program_id)`.

---

## 3. Current State — Entity & Schema

### 3.1 ProgramSlab Entity

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramSlab.java`  
**DB Table**: `program_slabs`

| Column | Java Field | Nullable | Notes |
|---|---|---|---|
| `id` (PK) | `pk.id` | NO | Composite PK |
| `org_id` (PK) | `pk.orgId` | NO | Composite PK |
| `program_id` | `programId` | NO | FK to programs |
| `serial_number` | `serialNumber` | NO | **Defines tier order; max = highest** |
| `name` | `name` | NO | Tier name |
| `description` | `description` | NO | |
| `created_on` | `createdOn` | NO | Timestamp |
| `metadata` | `metadata` | YES | Optional JSON |

**C7 Finding**: There is **NO `is_deleted`, `deleted`, `active`, or `status` field** in `ProgramSlab`. Soft deletion does not exist today.

### 3.2 PartnerProgramSlab Entity

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PartnerProgramSlab.java`  
**DB Table**: `partner_program_slabs`

Same observation — **no soft-delete field exists**.

---

## 4. Current State — No Delete API Exists

**C7 — Verified from source:**

`TierFacade.java` (`api/prototype`) contains these methods:
- `listTiers(orgId, programId)`
- `createTier(orgId, actorId, request)`
- `updateTier(orgId, actorId, tierId, request)`
- `listDrafts(orgId, programId)`
- `publishDraft(orgId, publisherId, programId)`
- `discardDraft(orgId, programId)`
- `getChangeLog(...)`

**`deleteTier()` does not exist.** There is no delete endpoint, no soft-delete flag, and no application-level delete guard anywhere in `emf-parent` or `intouch-api-v3`.

---

## 5. Impact on Strategies

### 5.1 How Strategies Reference Tiers

Tier downgrade strategies store tier references as **serialised JSON** in the `strategy` entity's `property_values` column. The structure is controlled by `TierDowngradeStrategyConfiguration` and `TierDowngradeSlabConfig`.

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/TierDowngradeSlabConfig.java`

Each `TierDowngradeSlabConfig` stores **two references** to a tier:

| Field | Type | Purpose |
|---|---|---|
| `m_slabNumber` | `int` | Tier's serial number (position-based reference) |
| `m_id` | `int` | Tier's database ID (direct PK reference) — used when `downgradeTarget=SINGLE` |
| `m_name` | `String` | Cached tier name |
| `m_downgradeTarget` | enum | `SINGLE` / `THRESHOLD` / `LOWEST` |

### 5.2 Strategy Risks on Highest Tier Deletion

#### Risk A — Strategies with `SINGLE` downgrade target pointing to highest tier (C5)

If a lower tier's downgrade config has `downgradeTarget=SINGLE` and its `m_id` points to the highest tier (customers who don't meet downgrade criteria stay at the highest tier), soft-deleting that tier will cause:
- The strategy lookup by `m_id` to return a deleted slab
- Depending on null-check quality in the consuming code, this causes either **silent wrong behaviour** or **NPE**

**Evidence**: `TierDowngradeSlabConfig.java:97-103` — `getSlabId()` returns `m_id`; calling code in `SlabDowngradeStrategyImpl` uses this to look up the target slab. No null-check found for the case where the slab is soft-deleted.

#### Risk B — Highest tier itself has no downgrade config (C6)

`SlabDowngradeStrategyImpl.java:111`: `if (slabNumber <= 1 || slabConfig == null || !slabConfig.shouldDowngrade())` — the highest-slab has `shouldDowngrade=false` by design. So the downgrade strategy itself won't be computing an expiry for the highest tier. However, lower tiers' configs that **reference** the highest tier as a downgrade target are affected.

#### Risk C — Strategy JSON becomes stale (C6)

The `m_name` field in `TierDowngradeSlabConfig` caches the slab name. After soft-deleting the highest tier, the strategy JSON still shows the old name. This is a data consistency issue for UI display.

#### Risk D — `TierDowngradeStrategyConfiguration` array out of sync (C4)

The `TierDowngradeStrategyConfiguration` maintains an array of `TierDowngradeSlabConfig[]` indexed by slab position. If the highest tier is soft-deleted and the array is not updated, the strategy configuration becomes inconsistent with the live tier list.

---

## 6. Impact on Customers Currently on the Highest Tier

### 6.1 Customer-Tier Relationship

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/CustomerSlabUpgradeHistoryInfo.java`  
**DB Table**: `customer_slab_upgrade_history`

| Column | Notes |
|---|---|
| `customer_id` | FK to customer |
| `program_id` | FK to program |
| `from_slab_id` | **FK to `program_slabs.id`** |
| `to_slab_id` | **FK to `program_slabs.id`** |

With soft delete (row not physically removed), FK constraints are satisfied. However:

### 6.2 Customer Impact Scenarios

#### Scenario A — Active customers on highest tier (C6 — HIGH RISK)

If customers currently enrolled at the highest tier exist when it is soft-deleted:
- Their current tier assignment points to a deleted slab
- **No fallback logic exists** in the codebase to re-assign them to a new "next highest" tier
- Upgrade/downgrade scheduler jobs will query their tier by ID, get a soft-deleted row, and either:
  - Skip the customer (if filtered with `WHERE is_deleted = false`)
  - Throw an error (if the query returns the deleted row but downstream code fails)
- Customer-facing APIs that return "current tier" will return a deleted tier record

**Evidence gap (C3)**: The exact `CustomerEnrollment` entity structure (which stores the live tier per customer) could not be fully read. The risk assessment is based on the history table and general pattern.

#### Scenario B — Upgrade path broken (C5)

Customers in lower tiers upgrading toward the highest tier: if upgrade strategies store the "eligible-to" slab ID as the highest tier, after soft-deletion the upgrade target no longer exists in the active tier set. Customers who meet the upgrade criteria will either stay in their current tier (silent failure) or throw an exception.

#### Scenario C — Downgrade job behavior (C5)

The downgrade scheduler calls `getSlabExpiryDate(...)` per customer. If the customer is on the deleted tier and the query filters for `is_deleted = false`, the slab config won't be found (`slabConfig == null`), and the guard at line 111 will return 100-years expiry — meaning the customer **never gets downgraded**. This is silent incorrect behaviour.

---

## 7. Impact on Historical Data & Reporting

### 7.1 Tier Change History

**Table**: `customer_slab_upgrade_history`  
**Columns**: `from_slab_id`, `to_slab_id` — both FK to `program_slabs.id`

With soft delete (row preserved), historical records remain valid. However:
- Reports that join `customer_slab_upgrade_history` with `program_slabs` and filter `WHERE is_deleted = false` will exclude historical entries that reference the deleted tier.
- **This will make historical reports appear as if the tier never existed**, breaking trend analysis.

**Recommendation**: Reports should **not** filter `is_deleted` on historical join queries. Only active-tier queries (real-time eligibility, upgrade/downgrade decisions) should apply the filter.

### 7.2 Audit / Change Log

**File**: `TierFacade.java` — `tierChangeLogService.recordChanges(...)` is called on publish. The deletion action must also be recorded in the changelog to maintain audit trail.

---

## 8. Impact on Caches & Thrift Integration

### 8.1 Redis Caches

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/InfoLookupService.java` (lines 139, 145, 151)

Tier data is cached in Redis under `PROGRAMS` and related cache buckets via `@Cacheable`. After soft-deleting the highest tier:
- The cache still holds the stale (non-deleted) tier data
- Any eligibility or upgrade decision made before cache TTL expires will use the deleted tier
- **Cache eviction must be triggered immediately on soft delete**

TTL is `ONE_HOUR` — meaning up to 1 hour of stale tier data in Redis without explicit eviction.

### 8.2 Thrift Service Integration

**File**: `emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/external/EMFThriftServiceImpl.java`

External services communicate tier data over Thrift. If those services cache tier configurations independently, they will not automatically receive the soft-delete signal. A Thrift-level cache invalidation or notification event must be considered.

**C3 (Tentative)**: The exact Thrift calls that carry tier data were not fully traced. This requires cross-repo tracing to fully enumerate.

---

## 9. Foreign Key & Referential Integrity

| Table | FK Column | References | Soft Delete Impact |
|---|---|---|---|
| `customer_slab_upgrade_history` | `from_slab_id`, `to_slab_id` | `program_slabs.id` | FK satisfied (row stays); historical queries may be affected by filter |
| `strategy` (property_values JSON) | `m_id` in JSON | `program_slabs.id` (logical) | No DB-level FK; stale JSON reference; NPE risk in strategy execution |
| `customer_enrollment` (inferred) | `slab_id` (likely) | `program_slabs.id` | Customers on deleted tier become orphaned in enrollment state |
| `partner_program_slabs` | Potentially references `program_slabs` | To be verified | Needs cross-repo trace |

---

## 10. Risks — Severity Ranked

| # | Risk | Severity | Likelihood | Evidence Confidence |
|---|---|---|---|---|
| R1 | Customers currently on highest tier have no tier reassignment logic — they remain on a deleted tier | **CRITICAL** | High if org has customers at top tier | C5 |
| R2 | Downgrade strategies with `SINGLE` target pointing to deleted tier cause NPE or silent wrong behavior | **CRITICAL** | High if any strategy uses SINGLE mode targeting highest tier | C5 |
| R3 | Upgrade scheduler silently fails to upgrade customers toward deleted target tier | **HIGH** | High if highest tier is an upgrade target | C5 |
| R4 | Redis cache serves stale (non-deleted) tier data for up to 1 hour after deletion | **HIGH** | Near certain without explicit eviction | C6 |
| R5 | Strategy JSON (`TierDowngradeSlabConfig.m_id`) becomes stale — no automated cleanup | **HIGH** | Certain; JSON is not updated on tier deletion | C7 |
| R6 | Historical reports filtering `is_deleted=false` lose all entries referencing deleted tier | **MEDIUM** | Depends on reporting query design | C4 |
| R7 | `partner_program_slabs` impact not fully traced — unknown dependencies | **MEDIUM** | Unknown | C3 |
| R8 | No audit trail for deletion event if change log service is not called | **MEDIUM** | Certain without explicit instrumentation | C6 |
| R9 | Thrift-connected services cache tier data independently — no invalidation signal | **MEDIUM** | C3 (not fully traced) | C3 |
| R10 | UI displays deleted tier in dropdowns (downgrade target picker) if filter not applied | **LOW** | High without filter in API response | C5 |
| R11 | `PartnerProgramTierSyncConfiguration.loyalty_program_slab_id` becomes an orphaned reference — Thrift sync map returns empty string for loyalty tier name | **CRITICAL** | Certain if any supplementary program maps to the highest tier | C7 |
| R12 | Strategy JSON retains the deleted tier's entry forever — strategy engine silently runs downgrade logic against a deleted tier's config for any customer still enrolled on it | **HIGH** | Certain without explicit strategy JSON cleanup before deletion | C7 |
| R13 | Audit log records `m_id` referencing a non-existent active slab — audit trail queries joining program_slabs return broken/missing tier info | **MEDIUM** | Certain | C7 |

---

## 11. Required Changes to Implement Soft Deletion

### 11.1 Database Changes (Flyway Migration Required)

```sql
-- V<next>.sql
ALTER TABLE program_slabs
  ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE partner_program_slabs
  ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX idx_program_slabs_active
  ON program_slabs (org_id, program_id, is_deleted);
```

### 11.2 Entity Changes

**File**: `ProgramSlab.java`  
Add field:
```java
@Basic
@Column(name = "is_deleted", nullable = false)
private boolean isDeleted;
```

Same for `PartnerProgramSlab.java`.

### 11.3 Repository/DAO Changes

All queries in `PeProgramSlabDao` (or equivalent) that fetch active tiers must add:
```java
WHERE is_deleted = false
```

**Caution**: Historical/reporting queries must NOT add this filter — they must see all tiers including deleted ones to preserve audit integrity.

### 11.4 New API Endpoint (intouch-api-v3)

Add `DELETE /v1/programs/{programId}/tiers/{tierId}` with maker-checker flow:

1. **Pre-deletion validations** (all must pass before draft is created):
   - No customers currently enrolled on this tier
   - No active strategy has `downgradeTarget=SINGLE` with `m_id` pointing to this tier
   - This tier is not the only tier in the program (minimum 1 tier must remain)
   - This tier is the highest tier (if the product requirement is specifically for highest-tier deletion only)

2. **Draft creation**: Create a `PENDING_DELETION` draft in OrgConfig MongoDB

3. **Maker-checker publish**: On `publishDraft()`, execute the soft delete and call `tierChangeLogService.recordChanges()`

4. **Post-deletion actions**:
   - Evict Redis cache (`@CacheEvict` on org_id + program_id)
   - Trigger Thrift invalidation if applicable
   - Update strategy JSON if `m_name` references the deleted tier (or leave for lazy read)

### 11.5 Strategy Validation Update

**File**: `TierUpdateRequestValidator.java` (intouch-api-v3)  
Add validation: reject strategy updates where `downgradeTarget=SINGLE` and `m_id` refers to a soft-deleted slab.

**File**: `publishDraft()` in `TierFacade.java`  
Add pre-publish check: reject if the draft references a soft-deleted tier in any strategy field.

### 11.6 Cache Eviction

Add `@CacheEvict` on the soft-delete service method:
- Evict `PROGRAMS` cache keyed by `(orgId, programId)`
- Evict any per-tier cache entries

---

## 12. Step-by-Step Process to Delete the Highest Tier

This is the **recommended safe sequence** to follow when an operator wants to soft-delete the highest tier.

### Step 1 — Pre-flight Checks (Before Raising a Delete Request)

- [ ] Confirm the tier to be deleted is indeed the highest (max `serial_number`) for the program
- [ ] Query `customer_enrollment` — confirm **zero active customers** are currently on this tier, or define a reassignment plan
- [ ] Query `strategy` JSON — confirm **no active strategy** has `downgradeTarget=SINGLE` with `m_id` pointing to this tier
- [ ] Confirm at least one other tier will remain in the program after deletion
- [ ] Document the reason for deletion in the change request ticket

### Step 2 — Customer Reassignment (If Customers Exist on This Tier)

Before raising the delete request:
- Manually run a downgrade operation to move all customers from the highest tier to the next-highest tier
- Confirm via `customer_slab_upgrade_history` that zero customers remain on the target tier
- This is a **manual data operation** — there is no automated reassignment logic today

### Step 3 — Strategy Cleanup

Before raising the delete request:
- Update any downgrade strategy that has `SINGLE` target referencing the highest tier — change the `downgradeTarget` to `THRESHOLD` or `LOWEST`
- **Remove the deleted tier's slab entry from the `TierDowngradeStrategyConfiguration.slabs[]` JSON** — publish the updated strategy
- Publish the updated strategy through the existing maker-checker flow
- Confirm the strategy JSON no longer references the tier's `slabNumber` or `m_id`

### Step 3a — Supplementary Program Cleanup

Before raising the delete request:
- Query: `SELECT * FROM partner_program_tier_sync_configuration WHERE loyalty_program_slab_id = <tierId> AND loyalty_program_id = <programId>`
- For each row returned:
  - If the supplementary program has a replacement tier: update `loyalty_program_slab_id` to point to the new highest tier
  - If not: delete those sync configuration rows
- Verify by calling the Thrift endpoint for each affected partner program — confirm `loyaltySyncTiers` returns no empty strings
- Document the change in the delete request ticket

### Step 4 — Raise Delete Request (Maker Flow)

- Call the delete API: `DELETE /v1/programs/{programId}/tiers/{tierId}`
- System creates a `PENDING_DELETION` draft
- The draft must include: reason, actor ID, timestamp

### Step 5 — Checker Approves

- Second authorised user calls `publishDraft()` on the pending deletion
- System runs server-side pre-deletion validations (customers check, strategy check)
- If validations pass: `is_deleted = TRUE` is set on the `program_slabs` row
- Changelog entry is recorded
- Redis cache is evicted

### Step 6 — Post-Deletion Verification

- [ ] Call `listTiers(orgId, programId)` — confirm the deleted tier no longer appears
- [ ] Run the downgrade scheduler job for the program — confirm no errors for any customer
- [ ] Check Redis cache TTL — confirm stale entries are not served (or wait for TTL)
- [ ] Verify `customer_slab_upgrade_history` historical queries still return complete history
- [ ] Check Thrift-connected services if applicable

### Step 7 — Monitoring

- Monitor upgrade/downgrade job error logs for 24–48 hours after deletion
- Monitor customer tier API responses for any reference to the deleted tier
- Check for any NPE in strategy execution logs

---

## 13. Open Questions

| # | Question | Why It Matters | Owner |
|---|---|---|---|
| Q1 | What is the exact schema and FK definition of `customer_enrollment`? Specifically, does it have a direct `slab_id` column? | Determines orphan risk for live customers | Backend / DB |
| Q2 | Are there Thrift services that independently cache tier data by slab ID? | Determines if Thrift invalidation is needed | Arch / Backend |
| Q3 | Is `partner_program_slabs` impacted — are partner tiers linked to program tiers by ID? | Determines if partner tier deletion cascades | Backend |
| Q4 | What is the product requirement — is deletion only allowed for the highest tier, or any tier? | Determines scope of validation guards | Product |
| Q5 | Should deletion be reversible (soft-delete with restore capability) or one-way? | Affects schema design — `is_deleted` vs `deleted_at` timestamp | Product / Backend |
| Q6 | What should happen to customers on the deleted tier — auto-reassign to next-highest, or require manual reassignment before deletion is allowed? | Determines if a migration job is needed | Product |
| Q7 | Does the change log service (`tierChangeLogService`) support a `DELETE` action type, or does it need to be extended? | Determines audit trail completeness | Backend |

---

## 13. Strategy Deep Dive — Exact Breakage vs. Safe Paths

This section provides a precise, evidence-backed breakdown of what will and will not break in the strategy layer when the highest tier is soft-deleted.

### 13.1 How Strategy JSON is Stored and Loaded

**Storage**: `Strategy.property_values` is a plain `TEXT` column (not a MySQL `JSON` type). It contains a Gson-serialised `TierDowngradeStrategyConfiguration`.

**Loading**: `SlabDowngradeStrategyImpl.java:97–98`
```java
Gson gson = new GsonBuilder().setDateFormat(CONFIG_DATE_CONFIG).create();
return gson.fromJson(slabDowngradeStrategy.getPropertyValues(), TierDowngradeStrategyConfiguration.class);
```
No DB lookup. No slab-ID validation during deserialisation. The JSON parses successfully regardless of whether the referenced slab IDs still exist.

### 13.2 What Fields Are Stored Per Slab in the Strategy JSON

Each entry in the `slabs[]` array of the JSON corresponds to one `TierDowngradeSlabConfig`:

| JSON Key | Java Field | Type | Purpose |
|---|---|---|---|
| `"slabNumber"` | `m_slabNumber` | `int` | Tier serial number — used for **in-memory lookup during execution** |
| `"id"` | `m_id` | `int` | Tier DB ID — used **only for audit logging** |
| `"name"` | `m_name` | `String` | Snapshot of tier name — **never auto-synced** |
| `"description"` | `m_description` | `String` | Snapshot — stale if tier is renamed |
| `"colorCode"` | `m_colorCode` | `String` | Snapshot — stale if tier color changes |
| `"shouldDowngrade"` | `m_shouldDowngrade` | `boolean` | Whether downgrade applies to this slab |
| `"downgradeTarget"` | `m_downgradeTarget` | `enum` | `SINGLE` / `THRESHOLD` / `LOWEST` |

**C7 Key Finding**: No FK constraint exists from the `strategy` table to `program_slabs`. The `"id"` field in strategy JSON is a **logical reference only** — the database will never prevent it becoming stale.

### 13.3 Execution Path — Does a Slab Lookup Happen?

**No DB lookup happens during strategy execution.** C7 — verified.

`SlabDowngradeStrategyImpl.java:195–196`:
```java
public TierDowngradeSlabConfig getTierDowngradeSlabConfig(int slabNumber) {
    return m_strategyConfig.getTierDowngradeSlabConfig(slabNumber);
}
```

This returns from `m_strategyConfig` — the in-memory deserialised JSON object. The strategy engine never hits the DB during `getSlabExpiryDate(...)`.

**What this means**: Downgrade execution for existing customers will **not throw a NullPointerException** due to the slab being soft-deleted. The strategy engine operates on its cached JSON configuration.

### 13.4 What DOES Break in Strategies

#### Break 1 — Audit Trail Corruption (C7 — CERTAIN)

`SlabDowngradeAuditLogService` reads `slabConfig.getSlabId()` (`m_id`) to record audit entries. After the tier is soft-deleted, the audit log continues recording a slab ID that no longer exists as an active tier. Any audit query joining `program_slabs` by ID with `is_deleted=false` will show a broken or empty tier reference in the audit history.

#### Break 2 — Strategy Config Never Cleaned Up (C7 — CERTAIN)

The strategy JSON retains a full `TierDowngradeSlabConfig` entry for the deleted tier's `slabNumber` forever. No cleanup mechanism exists. This means:
- If a customer is on the deleted tier and the downgrade job runs, it will find the config for that `slabNumber` in the JSON and execute against it
- The deleted tier's `shouldDowngrade`, `downgradeTarget`, and `periodConfig` remain active in the strategy engine
- **This is functionally dangerous**: the strategy will compute a downgrade expiry for a tier that has been deleted, silently treating it as if it still exists

#### Break 3 — Stale Snapshot Fields (C7 — CERTAIN)

`m_name`, `m_description`, and `m_colorCode` in the JSON will forever reflect the values at the time the strategy was last published. If the tier was renamed before deletion, the strategy still shows the old name. This is a pre-existing issue compounded by deletion.

#### Break 4 — SINGLE-target downgrade target becomes logically invalid (C5)

If a lower tier's `downgradeTarget=SINGLE` and its `m_id` refers to the highest tier, the intent was "downgrade this customer to the highest tier in certain conditions." After the highest tier is deleted, this is business-logic nonsense. The execution won't NPE (because `m_id` is not DB-looked up), but the business outcome is wrong — customers may be "downgraded" to a tier that no longer exists.

### 13.5 What is SAFE in Strategies

- Gson deserialisation of strategy JSON: **safe** (no slab validation)
- `getSlabExpiryDate(slabNumber)`: **safe** (in-memory lookup, no DB call)
- Calculation of downgrade dates for tiers other than the deleted one: **safe**
- Strategy JSON for non-deleted tiers: **unaffected**

### 13.6 How to Safely Handle Strategy on Deletion

Before soft-deleting the highest tier, the following **mandatory steps** are required:

1. **Remove the deleted slab entry from the strategy JSON** — update `TierDowngradeStrategyConfiguration.slabs[]` to remove the entry for the deleted slab's `slabNumber`
2. **Update any `SINGLE`-target configs** that have `m_id` pointing to the deleted tier — change `downgradeTarget` to `THRESHOLD` or `LOWEST` as appropriate
3. Re-publish the strategy through the maker-checker flow
4. Only after the strategy is updated and published should the tier deletion draft be raised

---

## 14. Supplementary Program Impact — Full Breakage Analysis

### 14.1 Architecture: How Supplementary Programs Link to Loyalty Tiers

Supplementary (partner) programs use a three-table chain to sync tiers with the loyalty program:

```
PartnerProgram (partner_program)
    └── PartnerProgramTierSyncConfiguration (partner_program_tier_sync_configuration)
            ├── loyalty_program_slab_id  ← refers to program_slabs.id
            └── partner_program_slab_id  ← refers to partner_program_slabs.id
    └── PartnerProgramSlab (partner_program_slabs)
```

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PartnerProgramTierSyncConfiguration.java`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` (PK) | int | NO | |
| `org_id` (PK) | int | NO | |
| `loyalty_program_id` | int | NO | |
| `partner_program_id` | int | NO | |
| `loyalty_program_slab_id` | int | NO | **Direct reference to `program_slabs.id`** |
| `partner_program_slab_id` | int | NO | Reference to `partner_program_slabs.id` |
| `created_on` | TIMESTAMP | NO | |

**C7 Finding**: `loyalty_program_slab_id` stores the loyalty tier's DB ID. There is **no FK constraint** at the database level — so soft-deleting the loyalty tier will not cause a DB error, but will create a silent orphan reference.

### 14.2 The Exact Breakage: Thrift Tier Sync Map

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java:2135–2154`

```java
Map<String, String> map = new HashMap<>();
for (PartnerProgramTierSyncConfiguration tierSyncConfiguration :
        partnerProgramEntity.getLoyaltyPartnerProgramSyncTiers()) {

    String partnerProgramSlab = "non_tier";
    String loyaltyProgramSlab = "";                   // ← initialised as empty string

    if (tierSyncConfiguration.getPartnerProgramSlabId() > -1) {
        for (PartnerProgramSlab partnerSlab : partnerProgramEntity.getPartnerProgramSlabs()) {
            if (partnerSlab.getId() == tierSyncConfiguration.getPartnerProgramSlabId())
                partnerProgramSlab = partnerSlab.getName();
        }
    }

    List<ProgramSlab> slabs = partnerProgramEntity.getLoyaltyProgram().getProgramSlabs();
    for (ProgramSlab slab : slabs) {
        if (slab.getId() == tierSyncConfiguration.getLoyaltyProgramSlabId()) {  // ← Line 2147
            loyaltyProgramSlab = slab.getName();                                // ← Line 2148
        }
    }

    map.put(partnerProgramSlab, loyaltyProgramSlab);   // ← Line 2151
}
partnerProgram.setLoyaltySyncTiers(map);               // ← propagated via Thrift
```

**Exact breakage chain** when highest tier is soft-deleted and `getProgramSlabs()` filters by `is_deleted=false`:

1. Loop at line 2146 iterates over active slabs only (deleted tier excluded)
2. `slab.getId() == tierSyncConfiguration.getLoyaltyProgramSlabId()` → **never matches** for the deleted tier
3. `loyaltyProgramSlab` stays as `""` (empty string)
4. `map.put(partnerProgramSlab, "")` — the partner tier maps to an **empty loyalty tier name**
5. `partnerProgram.setLoyaltySyncTiers(map)` sends this corrupted map over Thrift
6. **Any consumer of this Thrift response gets `"partnerTierName" → ""` in the sync map instead of `"partnerTierName" → "Platinum"`**

This is **silent data corruption** — no exception is thrown, no error is logged, the caller just receives wrong data.

### 14.3 Impact on Customers in Supplementary Programs

**Supplementary enrollment entity**: `SupplementaryPartnerProgramEnrollment`  
The enrollment itself does NOT store a tier reference — it only stores `customerId`, `partnerProgramId`, `isLinked`, and membership dates.

Tier resolution is done **lazily via the sync configuration** at read time. This means:

- Customers enrolled in the supplementary program with the highest loyalty tier:
  - Their supplementary enrollment record is **not directly broken**
  - BUT when the system resolves "what partner tier should this customer be on?" — it uses `PartnerProgramTierSyncConfiguration` keyed by `loyalty_program_slab_id`
  - After the highest loyalty tier is deleted, the sync config row for it becomes an orphan
  - Resolution returns empty/null tier mapping → customer's supplementary tier cannot be determined

### 14.4 PartnerProgramSlab — No Soft Delete Either

**File**: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PartnerProgramSlab.java`

`PartnerProgramSlab` also has **no `is_deleted` field** — identical situation to `ProgramSlab`. Both entities need the column added if a complete soft-delete story is to be implemented.

### 14.5 No Tier Change Event Listeners

No event-driven propagation was found (no `TierChangeEvent`, no `@EventListener` for tier updates). The supplementary program tier sync is resolved lazily on read, not reactively on tier state changes. This means:

- There is no mechanism to automatically update `PartnerProgramTierSyncConfiguration` when a tier is deleted
- The orphaned `loyalty_program_slab_id` rows must be **manually cleaned up before deletion**

### 14.6 How to Safely Handle Supplementary Programs on Deletion

Before soft-deleting the highest tier, these steps are **mandatory**:

1. **Query `partner_program_tier_sync_configuration`** for all rows where `loyalty_program_slab_id = <deleted tier's ID>`. Get the count.
2. If any rows exist:
   - Decide: should these sync configurations be remapped to the new highest tier, or removed entirely?
   - If the supplementary program has its own tier structure, remap `loyalty_program_slab_id` to the new highest tier's ID
   - If not, remove those sync configuration rows
3. Perform the update/delete of `partner_program_tier_sync_configuration` rows in a transaction
4. Verify: re-run the Thrift call for the affected partner programs and confirm no empty strings in `loyaltySyncTiers`
5. Only then proceed with the tier deletion draft

### 14.7 Risk Summary for Supplementary Programs

| Component | What Breaks | Type | Severity |
|---|---|---|---|
| `partner_program_tier_sync_configuration.loyalty_program_slab_id` | Becomes orphaned reference | Silent data corruption | **CRITICAL** |
| `PointsEngineRuleConfigThriftImpl:2147–2151` | Returns `""` for loyalty tier name in sync map | Silent wrong data in Thrift response | **CRITICAL** |
| Customer tier resolution in supplementary program | Cannot determine which partner tier a customer belongs to | Functional breakage | **HIGH** |
| `PartnerProgramSlab` entity | No soft-delete field — parallel gap to `ProgramSlab` | Schema gap | **HIGH** |
| Supplementary enrollment records | Not directly broken (no tier FK) | No impact on rows | **LOW** |

---

---

## 16. Automatic Cascade Cleanup — Strategy JSON

### 16.1 Why Automatic Cleanup is Safe

**C7 — Verified from source:**

`SlabDowngradeStrategyImpl` has no `@Component`, `@Service`, or Spring annotation. It is a **plain Java class** constructed fresh every time it is needed:

```java
// SlabDowngradeStrategyImpl.java:35
public SlabDowngradeStrategyImpl(Strategy slabDowngradeStrategy) {
    m_strategyConfig = deserialize(slabDowngradeStrategy);   // loads JSON on construction
    ...
}
```

This means: **there is no long-lived singleton holding a stale in-memory copy of the strategy JSON.** Every event that evaluates the downgrade strategy constructs a new `SlabDowngradeStrategyImpl` from the current `Strategy.property_values` in the DB.

**Consequence**: if we update `strategy.property_values` in the DB as part of the tier deletion, **all events processed after that point will automatically get the cleaned JSON**. No restart, no cache flush, no separate job required.

### 16.2 The Concern: Strategy is Used on ALL Events

The user's concern is valid — the tier downgrade strategy fires on every transaction event where a customer's tier is evaluated. The `getSlabExpiryDate(slabNumber)` method is called per customer per event. This means:

- Any change to the strategy JSON has **immediate, program-wide effect** on the next event
- We are not patching a rarely-called admin path — we are touching a hot execution path
- The cleanup must be correct and tested before the deletion is published

**However, the failure mode if the entry is cleanly removed is safe** (see Section 13.3): when `slabConfig == null` for a given `slabNumber`, the guard at `SlabDowngradeStrategyImpl.java:111` returns a 100-year expiry. This means the customer is simply **not downgraded** — a benign, conservative failure.

### 16.3 Two Options for Handling the Deleted Slab Entry

#### Option A — Remove the slab entry entirely from the JSON array (Recommended)

Remove the `TierDowngradeSlabConfig` array entry for the deleted tier's `slabNumber` from `property_values`.

**What happens to in-flight events after removal:**
- `getTierDowngradeSlabConfig(deletedSlabNumber)` returns `null`
- Guard fires: `if (slabNumber <= 1 || slabConfig == null || ...)` → returns 100-year expiry
- Customer is not downgraded from their current tier during this event — **safe and conservative**
- Once all customers have been properly moved off the deleted tier (via the downgrade step), no customer will ever present `slabNumber = deletedSlabNumber` again → the removed entry is truly dead

**Risk**: If any customer is still on the deleted tier when the JSON cleanup runs, they get a 100-year expiry indefinitely. This is why **customer reassignment must happen before deletion**, not after.

#### Option B — Mark the slab entry as `shouldDowngrade=false` in JSON

Set `m_shouldDowngrade = false` for the deleted slab's entry without removing it.

**What happens:** same 100-year expiry behaviour. The slab entry remains in the JSON as a "frozen" config. Less clean than Option A — the ghost entry persists forever and can confuse future maintainers.

**Recommendation**: Use **Option A**. It is cleaner, permanent, and the failure mode is safe.

### 16.4 How to Implement the Automatic Strategy JSON Cascade

As part of `publishDraft()` in the tier deletion flow, add a cascade step:

```
Step: cascade strategy JSON cleanup (pseudocode)
------------------------------------------------------
1. Find all Strategy entities for (orgId, programId) where strategyType = TIER_DOWNGRADE
2. For each strategy:
   a. Deserialise property_values → TierDowngradeStrategyConfiguration
   b. Filter slabs[] array: remove entry where slabNumber == deletedTier.serialNumber
   c. Re-serialise → update strategy.property_values in DB
   d. Log the change (system-level audit entry: "slab entry removed due to tier deletion")
3. No maker-checker required for this cascade — it is a system-enforced consistency action
   triggered by the deletion, not a standalone strategy configuration change
```

**Important**: This cascade must happen **atomically with the soft-delete** — in the same transaction or an immediately following one with rollback on failure.

### 16.5 What About SINGLE-Target Downgrade Configs?

If any other slab's config has `downgradeTarget = SINGLE` AND `m_id` pointing to the deleted tier, the cascade must also handle that:

```
For each TierDowngradeSlabConfig in the cleaned slabs[] array:
  If config.downgradeTarget == SINGLE AND config.m_id == deletedTier.id:
    → Set downgradeTarget = LOWEST  (or THRESHOLD, per product decision)
    → Log the forced change
```

This ensures no surviving slab entry points to the deleted tier as a downgrade destination.

### 16.6 Safe Sequence with Automation

The revised pre-deletion sequence becomes:

1. Move all customers off the highest tier (via tier downgrade job)
2. **Automated in `publishDraft()`**:
   - Remove deleted slab entry from strategy JSON (Section 16.4)
   - Fix SINGLE-target refs pointing to deleted tier (Section 16.5)
   - Remap/delete `partner_program_tier_sync_configuration` rows (Section 17.4)
   - Set `is_deleted = true` on `program_slabs` row
   - Evict Redis cache
   - Record audit changelog entry
3. Verify post-deletion (downgrade job runs clean, Thrift call returns no empty strings)

---

## 17. Automatic Cascade Cleanup — Supplementary Programs

### 17.1 Why Automatic Cleanup is Feasible

Unlike the strategy JSON (which is opaque text), `partner_program_tier_sync_configuration` is a normal relational table with discrete rows. The cleanup is a straightforward DB operation that can be executed inside a transaction.

There are two choices for what to do with the orphaned rows:

### 17.2 Option A — Remap to New Highest Tier (Recommended)

Update `loyalty_program_slab_id` in every affected row to point to the new highest tier (the tier with the next-highest `serial_number` after deletion).

**What happens in the Thrift call after remapping (`PointsEngineRuleConfigThriftImpl.java:2147`):**
```java
// Before deletion: loyalty_program_slab_id = <deleted tier ID>  →  loyaltyProgramSlab = ""
// After remap:     loyalty_program_slab_id = <new highest tier ID>  →  loyaltyProgramSlab = "Gold"
```

The `for (ProgramSlab slab : slabs)` loop finds the remapped slab ID in the active list → `loyaltyProgramSlab` gets the correct name → `map.put(partnerTier, "Gold")` is correct.

**Trade-off**: Remapping assumes the supplementary program's tier mapping should roll down to the next tier. This is a product assumption — confirm with the product owner.

### 17.3 Option B — Delete the Sync Configuration Rows

Delete `partner_program_tier_sync_configuration` rows where `loyalty_program_slab_id = <deleted tier ID>`.

**What happens in the Thrift call after deletion:**
- `getLoyaltyPartnerProgramSyncTiers()` no longer returns a config entry for the deleted tier
- The loop simply has one fewer iteration
- `loyaltySyncTiers` map will be smaller — no entry for the partner tier that previously mapped to the deleted loyalty tier

**Trade-off**: The supplementary program loses the tier mapping entirely. Customers who were on the partner tier corresponding to the deleted loyalty tier will have an incomplete sync configuration. The supplementary program admin will need to reconfigure the mapping.

### 17.4 How to Implement the Automatic Supplementary Cascade

As part of `publishDraft()` in the tier deletion flow:

```
Step: cascade supplementary program cleanup (pseudocode)
------------------------------------------------------
1. Find new highest tier:
   SELECT * FROM program_slabs
   WHERE org_id = ? AND program_id = ? AND is_deleted = false
   ORDER BY serial_number DESC LIMIT 1
   → this is the new top tier after the deletion

2. Find affected sync config rows:
   SELECT * FROM partner_program_tier_sync_configuration
   WHERE loyalty_program_slab_id = <deleted tier ID>

3. For each row:
   Option A (Remap):
     UPDATE partner_program_tier_sync_configuration
     SET loyalty_program_slab_id = <new highest tier ID>
     WHERE id = <row id> AND org_id = <orgId>

   Option B (Delete):
     DELETE FROM partner_program_tier_sync_configuration
     WHERE loyalty_program_slab_id = <deleted tier ID>

4. Log: "N sync configuration rows updated/deleted due to tier deletion of tier <tierId>"
```

### 17.5 Verification After Cascade

After the cascade runs, the Thrift call that was broken (Section 14.2) should be verified:
- Call the Thrift endpoint for each affected partner program
- Confirm `loyaltySyncTiers` map has no empty-string values
- Confirm the remapped loyalty tier name appears correctly

### 17.6 Risk Summary — Automated vs Manual

| Concern | Manual Approach | Automated Cascade |
|---|---|---|
| Strategy JSON cleanup | High risk — developer must remember to do it and republish via UI | Low risk — done atomically in `publishDraft()` |
| Supplementary sync config | High risk — requires raw SQL, easy to miss programs | Low risk — query scoped to deleted tier ID, transactional |
| Maker-checker bypass for strategy | N/A — manual update goes through maker-checker | Yes — system-level cascade bypasses normal flow; needs explicit audit logging |
| In-flight event safety | Unknown — depends on timing | Defined — first event after deletion gets safe fallback (100-yr expiry) |
| Rollback on failure | Manual rollback complex | Transactional rollback automatic |

**Recommendation**: Implement automated cascade for both. Document that the strategy JSON update is a system-enforced consistency action (not a user-driven config change) in the audit log.

---

## 15. Open Questions

| # | Question | Why It Matters | Owner |
|---|---|---|---|
| Q1 | What is the exact schema and FK definition of `customer_enrollment`? Specifically, does it have a direct `slab_id` column? | Determines orphan risk for live customers | Backend / DB |
| Q2 | Does `InfoLookupService.getProgramSlabs()` currently apply any active-tier filter? If yes, what condition? | Determines whether the Thrift breakage (Section 14.2) is immediate on deployment or only after adding the `is_deleted` filter | Backend |
| Q3 | Is `partner_program_slabs` also being considered for soft-delete, or only `program_slabs`? | Determines scope of Flyway migration | Product / Backend |
| Q4 | What is the product requirement — is deletion only allowed for the highest tier, or any tier? | Determines scope of validation guards | Product |
| Q5 | Should deletion be reversible (soft-delete with restore capability) or one-way? | Affects schema design — `is_deleted` vs `deleted_at` timestamp | Product / Backend |
| Q6 | What should happen to customers on the deleted tier — auto-reassign to next-highest, or require manual reassignment before deletion is allowed? | Determines if a migration job is needed | Product |
| Q7 | Does the change log service (`tierChangeLogService`) support a `DELETE` action type, or does it need to be extended? | Determines audit trail completeness | Backend |
| Q8 | For supplementary programs: should `PartnerProgramTierSyncConfiguration` rows for the deleted tier be **remapped** to the new highest tier, or **deleted**? | Determines the pre-deletion data cleanup procedure for supplementary programs | Product |
| Q9 | Are there multiple supplementary/partner programs per loyalty program, and do they all have their own tier sync configurations referencing the highest tier? | Determines the scope of `partner_program_tier_sync_configuration` cleanup required | Backend / DB |
| Q10 | For the automated strategy JSON cascade: should the `SINGLE`-target configs be remapped to `LOWEST` or `THRESHOLD` when the target tier is deleted? Who decides the fallback mode? | Determines what value to write in the auto-cascade for `downgradeTarget` when fixing dangling SINGLE refs | Product |
| Q11 | For the automated supplementary cascade: should the sync config rows be **remapped to the new highest tier** (Option A) or **deleted** (Option B)? This is a product decision — remapping assumes the supplementary program's tier structure should roll down; deleting forces admin to reconfigure. | Core product decision for supplementary program integrity after highest-tier deletion | Product |

---

*Analysis produced from code evidence in `emf-parent` and `api/prototype (intouch-api-v3)` as of 2026-04-20.*  
*All claims are confidence-rated per the C1–C7 scale. Claims below C5 are flagged explicitly.*
