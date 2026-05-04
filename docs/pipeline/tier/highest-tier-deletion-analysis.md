# Highest-Tier Soft-Deletion — Feasibility & Impact Analysis

> **Date**: 2026-04-20
> **Author**: Engineering Analysis (AI-assisted)
> **Scope**: emf-parent, intouch-api-v3
> **Status**: Research draft — not yet approved for implementation
> **Confidence**: C5 (evidence from codebase reads; some line numbers are approximate — verify before implementation)

---

## 1. Executive Summary

Soft-deleting (retiring) the **highest serial-number LIVE tier** from a loyalty program is **technically feasible but not currently safe to ship**. The platform has no existing code path to handle it end-to-end. Four independent subsystems each carry a breaking gap:

| Gap | Severity |
|-----|----------|
| No auto-downgrade for members currently on the highest tier | HIGH |
| Strategy CSVs are positional arrays — no reindexing on tier removal | MEDIUM |
| PEB downgrade calculators assume contiguous slab sequences [1..n] | MEDIUM |
| No Thrift RPC to propagate slab deletion from MongoDB → MySQL | MEDIUM |

**Current safe boundary**: DRAFT-only tier deletion already works and is safe. Deleting a LIVE/ACTIVE tier requires 8–12 weeks of new work.

---

## 2. Current Deletion Code Paths

### 2.1 intouch-api-v3 — TierFacade.deleteTier()

The existing REST-tier deletion is **DRAFT-only** and soft-deletes by setting `status = DELETED` in MongoDB. No SQL row is touched.

```
DELETE /v3/tiers/{tierId}
  → TierController.deleteTier()
  → TierFacade.deleteTier()
      if status != DRAFT → 409 "Only DRAFT tiers can be deleted"
      else → tier.status = DELETED, save to MongoDB
```

**Key facts:**
- No maker-checker gate on DRAFT deletion (immediate)
- No SQL (`program_slabs`) row change
- No member reassignment
- No strategy update

### 2.2 emf-parent — PointsEngineRuleService (Thrift backend)

The Thrift service exposes `createOrUpdateSlab(SlabInfo, orgId, ...)` which handles **CREATE and UPDATE only**. There is **no `deleteSlab()` method** anywhere in the Thrift IDL or its implementation (`PointsEngineRuleConfigThriftImpl`).

This means even if the MongoDB tier is marked DELETED, the corresponding `program_slabs` row in MySQL is never touched — it remains ACTIVE in the engine.

### 2.3 Legacy SlabFacade (old UI path)

The legacy `SlabFacade` writes directly to MySQL via Thrift without a MongoDB step. It too has no deletion path — only create/update is exposed. Old-UI-created tiers are entirely invisible to the new deletion flow.

---

## 3. Strategy CSV Impact

### 3.1 How strategies are structured

Upgrade thresholds, allocation values, and expiry values are stored as **positional CSV strings** in MySQL strategy rows:

```
allocation_values = "10,20,30,40"
                     ↑  ↑  ↑  ↑
                  tier1 2  3  4   (index = serialNumber - 1)
```

### 3.2 How a new tier extends the CSV

When a new slab is approved, `updateStrategiesForNewSlab()` in `PointsEngineRuleService` appends `,0` to each CSV for the new position. This is the **only CSV mutation** that exists.

### 3.3 What happens when the highest tier is deleted

**No `updateStrategiesForDeletedSlab()` exists.** If tier 4 (the highest) is deleted:

- The CSV remains `"10,20,30,40"` — a stale 4-element array
- The slab count in the program drops to 3
- Any PEB calculation that reads index `[slabCount - 1]` now reads index `[2]` = `30` instead of nothing, silently returning wrong values
- Downgrade strategy references slab 4 as a target — the target no longer exists

**Risk**: Silent wrong-value calculations; no error thrown at runtime — this is the most dangerous gap because it fails without any alert.

### 3.4 What the fix requires

A new `removeSlabFromPropertyValues(json, deletedSerialNumber)` method must:
1. Parse the CSV array
2. Remove the entry at index `deletedSerialNumber - 1`
3. Shift all higher-index entries down
4. Write the shortened CSV back via Thrift strategy update

This must cover all strategy types: allocation, expiry, upgrade threshold, downgrade threshold.

---

## 4. Customer Impact

### 4.1 Where member-tier assignments live

Members are assigned to tiers via the `program_slabs` relationship tracked in the points engine (MySQL). When a customer earns enough to be in tier 4, the engine marks them against `slab_id = <id of tier 4 row>`.

### 4.2 What happens to members on the highest tier if it is deleted

The platform has **no automatic downgrade** when a tier is deleted. Three failure modes exist:

| Scenario | What happens | Risk |
|----------|-------------|------|
| Members remain linked to deleted slab row | SQL row still exists (soft-delete), but MongoDB no longer surfaces this tier. Member queries may return no tier or null tier for these members | HIGH |
| PEB tries to compute upgrade gap for a member on tier 4 | Code in `PointsEngineThriftServiceImpl` logs "customer already in highest tier" and skips calculation. After deletion, this member is no longer "in the highest tier" but still linked to slab 4 — creates split-brain state | HIGH |
| Downgrade calculator runs on a member in tier 4 | `LowestTierDowngradeCalculator` looks up slab 4's downgrade config — config still references slab 4 as source — but slab 4 is now DELETED. Depending on null-handling, this could throw or silently no-op | MEDIUM |

**The platform has no guard** that checks member count before allowing a LIVE tier to be deleted. This gap must be closed before any deletion is shipped.

### 4.3 Safe pre-condition: zero members

The only safe deletion scenario today is: **member count on the highest tier = 0 at the time of deletion**. The system should enforce this check. If members are present, the operator must either:

1. Manually wait for members to downgrade naturally via the renewal/downgrade engine
2. Trigger a bulk reassignment (requires new tooling — not available today)

---

## 5. PEB (Points Engine Backend) Assumptions

### 5.1 Contiguous slab assumption

`LowestTierDowngradeCalculator` builds a filter map keyed by `currentSlabNumber`. It assumes slabs form a gap-free sequence `[1, 2, 3, …, n]`. If slab 4 is deleted and slabs 1–3 remain:

- The filter map no longer has an entry for slab 4
- Any customer still linked to slab 4 produces a key-miss → null target → skip or exception
- The fix requires either re-numbering remaining slabs (destructive, risky) or changing the calculator to use slab IDs rather than serial numbers

### 5.2 Serial number reuse risk

`assignNextSerialNumber()` in `TierValidationService` computes `max(existing) + 1`. If tier 4 is deleted and a new tier is later created, it receives serial number 4 again. This creates a collision between:
- Historical strategy CSVs that had data at index 3 (slab 4's old slot)
- Old SNAPSHOT MongoDB docs that reference the original tier 4

Serial numbers must be treated as non-reusable identifiers once a tier has been LIVE. There is no guard for this today.

### 5.3 No "top-tier" abstraction

There is no `getHighestTier()` or `getTopSlab()` method in the codebase. The system is implicitly top-tier-aware only through `serialNumber == max(serialNumbers)` comparisons and CSV array length. This makes refactoring safe in the sense that there is no single class to update, but also means the assumption is scattered across multiple places.

---

## 6. Existing Guards (Current State)

| Guard | Strength | Location |
|-------|----------|----------|
| `deleteTier()` blocks non-DRAFT deletion (409) | Strong | `TierFacade.deleteTier()` |
| Maker-checker blocks unapproved SQL writes | Strong | `TierApprovalHandler` |
| No member count check before deletion | **MISSING** | Should be in `TierValidationService` |
| No strategy CSV consistency check before deletion | **MISSING** | Should be in `TierApprovalHandler.preApprove()` |
| No Thrift deleteSlab RPC | **MISSING** | Needs new Thrift method |
| No serial number reuse prevention | **MISSING** | Should be in `TierValidationService.assignNextSerialNumber()` |

---

## 7. Required Changes to Enable Highest-Tier Soft-Deletion

### Phase 1 — Pre-flight Validations (Block unsafe operations)

**1a. Member count gate** — `TierValidationService`
- Before any LIVE tier deletion is allowed, query member count assigned to that slab
- If count > 0, return 409 with count and instructions
- This is a hard block — no override

**1b. Strategy CSV consistency check** — `TierApprovalHandler.preApprove()`
- Verify CSV array length == current slab count before proceeding
- If mismatch, block and alert

**1c. Serial number retirement** — `TierValidationService`
- Track retired serial numbers per program
- Block re-use of a retired serial number

### Phase 2 — SQL Sync via New Thrift RPC

**2a. New Thrift IDL method**: `deleteSlab(SlabInfo, orgId, lastModifiedBy, lastModifiedOn)`
- Soft-deletes the `program_slabs` row (add `is_deleted` flag or `status` column via Flyway migration)
- Returns confirmation

**2b. Flyway migration**: Add `status VARCHAR(20) DEFAULT 'ACTIVE'` (or `is_deleted BIT(1) DEFAULT 0`) to `program_slabs`
- All existing rows default to ACTIVE / not-deleted
- All queries that currently read from `program_slabs` must filter `status != 'DELETED'`

### Phase 3 — Strategy CSV Reindexing

**3a. New method**: `updateStrategiesForDeletedSlab(orgId, programId, deletedSerialNumber)`
- Parse every strategy's CSV
- Remove entry at `deletedSerialNumber - 1`
- Compact remaining entries
- Persist via Thrift strategy update

**3b. Execution order**: Strategy CSV update must complete **before** the slab is marked deleted in MySQL. If the Thrift strategy update fails, the deletion is rolled back.

### Phase 4 — Maker-Checker Integration

**4a. New change type**: `RETIRE` (distinct from `DELETE` which is DRAFT-only)
- RETIRE goes through the full maker-checker approval flow
- Checker must explicitly confirm: "0 members on this tier" before approval
- Approval triggers: validate → strategy update → Thrift deleteSlab → MongoDB DELETED

**4b. New handler**: `TierRetirementHandler implements ApprovableEntityHandler<UnifiedTierConfig>`
- `preApprove()`: re-check member count (race condition window) + drift check
- `publish()`: Thrift strategy update → Thrift deleteSlab
- `postApprove()`: set MongoDB status to DELETED, archive as SNAPSHOT for audit trail
- `onPublishFailure()`: leave MongoDB in PENDING_APPROVAL, surface error to maker

### Phase 5 — PEB Downgrade Calculator Refactor (Medium-term)

- Refactor `LowestTierDowngradeCalculator` to key filter map on slab ID (Long) instead of `currentSlabNumber` (int)
- Eliminates the contiguous-sequence assumption
- Required for long-term safety but not a blocker for initial roll-out if member count = 0 is enforced

### Phase 6 — API Surface

**New endpoint**: `POST /v3/tiers/{tierId}/retire`
- Accepts retirement request body: `{ "reason": "...", "effectiveDate": "..." }`
- Submits into maker-checker flow (RETIRE change type)
- Returns 202 Accepted + change ID

**Existing `DELETE /v3/tiers/{tierId}`** remains DRAFT-only and unchanged.

---

## 8. Risk Matrix

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| Members orphaned (linked to deleted slab, no tier in queries) | HIGH | HIGH | Mandatory zero-member pre-flight check; block deletion if count > 0 |
| Strategy CSV positional mismatch → silent wrong calculations | HIGH | HIGH | Implement CSV reindexing before marking slab deleted; add CSV length == slab count assertion |
| PEB downgrade calculator key-miss for deleted slab → null target | MEDIUM | MEDIUM | Zero-member check prevents any customer being in deleted slab at retirement time |
| Serial number reuse after deletion → CSV slot collision | MEDIUM | MEDIUM | Retire serial numbers in a `retired_serial_numbers` set per program |
| Thrift deleteSlab fails midway → MySQL and MongoDB out of sync | MEDIUM | LOW | Idempotent SAGA in TierRetirementHandler; compensating transaction reverts MongoDB to PENDING_APPROVAL |
| Reviewer approves while member count just went non-zero (race) | MEDIUM | LOW | Re-check member count inside `preApprove()` (within the lock boundary) |
| Legacy SlabFacade re-creates deleted tier in SQL via old UI | MEDIUM | LOW | Old UI bypasses MC entirely; log a warning if SlabFacade creates a slab whose serial number is in the retired set |
| Flyway migration adds `status` column → existing queries break | LOW | LOW | Expand-then-contract: column is nullable with DEFAULT 'ACTIVE'; all existing reads unaffected until filtered queries are added |

---

## 9. Step-by-Step Process to Delete the Highest Tier (When Safe)

Once all Phase 1–4 changes are shipped, the operator process is:

1. **Confirm zero members** — run `GET /v3/tiers/{tierId}/member-count`. Block if > 0. Wait for natural downgrade cycle or contact support for bulk reassignment.

2. **Initiate retirement** — call `POST /v3/tiers/{tierId}/retire` with reason and effective date. This creates a PENDING_APPROVAL change of type RETIRE.

3. **Maker-checker review** — a second approver reviews the change in the approvals dashboard (`GET /v3/tiers/approvals`). The reviewer sees the member count (must still be 0 at approval time), current strategy CSV snapshot, and the slab being retired.

4. **Approve** — `POST /v3/tiers/{tierId}/approve`. The SAGA executes:
   a. Re-validate member count (race guard)
   b. Update strategy CSVs (remove highest slab entry)
   c. Call Thrift `deleteSlab()` → MySQL `program_slabs.status = DELETED`
   d. Set MongoDB tier status to DELETED (SNAPSHOT archived for audit)

5. **Verify** — `GET /v3/tiers?programId=...` should return n-1 tiers. The envelope for the deleted tier should no longer appear. Strategy CSV lengths should equal new slab count.

6. **Monitor** — watch PEB downgrade job logs for 24–48 hours. Any member-tier mismatches will surface in the downgrade calculator logs.

---

## 10. Effort Estimate

| Work Item | Effort | Risk |
|-----------|--------|------|
| Phase 1 — Pre-flight validations (member count gate, CSV check, serial number retirement) | 1 week | LOW |
| Phase 2 — Flyway migration + new Thrift `deleteSlab` RPC | 1 week | MEDIUM |
| Phase 3 — Strategy CSV reindexing (`updateStrategiesForDeletedSlab`) | 1 week | MEDIUM |
| Phase 4 — `TierRetirementHandler` + `RETIRE` change type + new REST endpoint | 1.5 weeks | MEDIUM |
| Phase 5 — PEB downgrade calculator refactor (slab ID keys) | 2 weeks | HIGH |
| Testing (unit, integration, PEB regression, canary) | 2 weeks | — |
| **Total** | **~8–10 weeks** | — |

Phase 5 (PEB refactor) can be deferred if zero-member enforcement is strict at the time of deletion — members cannot be in a deleted tier by construction. It becomes required only if serial number reuse or non-contiguous sequences are later introduced.

---

## 11. Verdict

| Question | Answer |
|----------|--------|
| Can the highest tier be soft-deleted today? | No — blocked at application layer (409) |
| Is it safe to ship highest-tier deletion without new code? | No — 4 independent gaps each carry MEDIUM–HIGH risk |
| What is the minimum viable scope to ship safely? | Phases 1–4 (member gate + Thrift RPC + CSV reindex + RETIRE flow) |
| Is a Flyway migration required? | Yes — `program_slabs` needs a `status` or `is_deleted` column |
| Does PEB need changes for an initial release? | No, if zero-member enforcement is strict |
| What is the total effort? | 8–10 weeks |
