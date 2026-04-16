# Critic Review -- Contradictions & Challenges

> Phase 2a: Devil's Advocate review of 00-ba.md and 00-prd.md
> Date: 2026-04-11

---

## Contradiction C-1: Thrift method for tier sync may not exist (BLOCKER)

**Source**: BA Assumption 3, PRD Architecture
**Claim**: "intouch-api-v3 -> Thrift -> emf-parent PointsEngineRuleService.createSlabAndUpdateStrategies()"
**Challenge**: The EMF Thrift service (`emf.thrift`) was searched for slab/tier/config methods. **ZERO relevant methods were found.** The Thrift `EMFService` has methods like `checkOrganizationConfiguration` but NO `createSlab`, `updateSlab`, `configureTier`, or anything that maps to `createSlabAndUpdateStrategies`.

This means `createSlabAndUpdateStrategies` is an **internal** method within emf-parent, NOT exposed via Thrift. The BA's assumption that intouch-api-v3 can call this method via Thrift is **UNVERIFIED (C2)**.

**Evidence**: `grep -n "createSlab\|addSlab\|updateSlab\|configureSlab\|saveSlab\|tierConfig\|slabConfig" emf.thrift` returned zero results. Only `checkOrganizationConfiguration` matched tier-adjacent patterns.

**Impact**: If no Thrift method exists for tier config sync, the entire approval flow (MongoDB -> SQL via Thrift) needs either:
- (a) A NEW Thrift method added to emf.thrift (requires Thrift IDL change + code generation)
- (b) A direct JDBC/JPA call from intouch-api-v3 to emf-parent's database (breaks service boundaries)
- (c) A REST-to-REST call instead of Thrift (different from the promotion pattern)

**Recommendation**: Resolve before Phase 6 (HLD). This is a BLOCKER for architecture.

---

## Contradiction C-2: PartnerProgramSlab impact not addressed

**Source**: BA Scope, PRD Data Model
**Claim**: BA focuses on `ProgramSlab` entity and proposes adding a status column to `program_slabs` table.
**Challenge**: The codebase also has `PartnerProgramSlab` (table: `partner_program_slabs`) which maps partner program tiers to loyalty program tiers. The BA mentions it in Domain Terminology but the PRD has **no user story or acceptance criterion** addressing what happens to partner program slabs when a program slab's status changes.

**Evidence**: `PartnerProgramSlab` has `loyaltyProgramId` and `partnerProgramId` fields, and is used by `PePartnerProgramSlabDao` and `PointsEngineRuleService`.

**Impact**: ~~Stopping a ProgramSlab could break PartnerProgramSlab references.~~ **REDUCED (Rework #2)**: Only DRAFT tiers can be deleted, and DRAFT tiers have no SQL record yet — so they cannot have PartnerProgramSlab references. This concern now only applies to future tier retirement (out of scope). For creation (US-2), new tiers start as DRAFT and won't have partner slab mappings until approved and synced to SQL.

**Recommendation**: ~~Add acceptance criterion to US-4.~~ **Updated**: No action needed for current scope. Document as a concern for future tier retirement epic. PartnerProgramSlab validation will be needed when ACTIVE tier stopping is implemented.

---

## ~~Contradiction C-3: PeProgramSlabDao usage is widespread -- "all queries need status filter" is high risk~~ — RESOLVED (Rework #3: Entire concern eliminated)

**Source**: BA Decision KD-02
**Claim**: "All existing slab queries must be updated to filter by status"
**Challenge**: `PeProgramSlabDao` is used in **7+ service classes** across emf-parent.

**Resolution (Rework #3)**: This contradiction is now moot. No SQL changes are needed:
- SQL `program_slabs` only contains ACTIVE tiers (synced via Thrift on approval)
- No ACTIVE tier can be deleted (DRAFT-only deletion in MongoDB)
- SlabInfo Thrift has no status field
- Therefore: no status column, no findActiveByProgram(), no Flyway migration, no blast radius
- PeProgramSlabDao is completely untouched. Zero regression risk.

~~**Recommendation**: Consider the expand-then-contract approach...~~
**Recommendation**: No action needed. Deferred to future tier retirement epic (when ACTIVE tiers may need stopping/archival).

---

## Contradiction C-4: "Threshold > previous tier's threshold" validation may be too simplistic

**Source**: PRD E1-US2 AC-4
**Claim**: "Validates: threshold > previous tier's threshold"
**Challenge**: Thresholds in `ThresholdBasedSlabUpgradeStrategyImpl` are stored as a CSV string (`threshold_values`) -- a comma-separated list of values per slab. The threshold is NOT stored per ProgramSlab but in the strategy config. Also, eligibility can involve tracker-based criteria with AND/OR conditions, not just a single numeric threshold.

**Evidence**: `this.propertiesMap.get("threshold_values")` -> CSV split -> per-slab thresholds. This is a STRATEGY-level property, not a slab-level property.

**Impact**: The validation "threshold > previous tier" assumes a simple numeric comparison, but the actual system supports complex criteria (purchase AND visits, tracker-based conditions). The validation logic will be more nuanced.

**Recommendation**: Reframe AC-4 as: "Validates that the tier's eligibility configuration is consistent with the program's tier hierarchy (e.g., higher tiers require higher thresholds)." Exact validation rules to be determined in Phase 6 (HLD).

---

## Contradiction C-5: "Scheduled" KPI has no backing concept

**Source**: PRD E1-US1 AC-7
**Claim**: "Response includes KPI summary: totalTiers, activeTiers, scheduledTiers, totalMembers"
**Challenge**: The PRD defines tier statuses as DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT (Rework #2 removed PAUSED and STOPPED). None of these is "Scheduled." The UI prototype shows "Scheduled: 0" in the KPI cards, but the BA/PRD do not define when a tier is "scheduled" vs "draft."

**Evidence**: The PromotionStatus enum has UPCOMING as a derived status ("State for UI: [ACTIVE] -> [LIVE, UPCOMING, COMPLETED]"). For tiers, there's no concept of "start date" that would make a tier "scheduled."

**Impact**: Either drop "Scheduled" from the KPI summary, or define what it means for tiers (e.g., a PENDING_APPROVAL tier is "scheduled" to go live).

**Recommendation**: Replace "scheduledTiers" with "pendingApprovalTiers" in the KPI summary, or define a start date concept for tiers.

---

## Contradiction C-6: MC framework scope may conflict with registry decomposition

**Source**: BA Decision KD-05, Registry epic-assignment.json
**Claim**: BA says "build full generic maker-checker framework as Layer 1 shared module."
**Challenge**: The registry's `epic-assignment.json` assigns Ritwik TWO epics: `maker-checker` (Layer 1) AND `tier-category` (Layer 2). These are treated as SEPARATE epics with separate pipeline runs. This pipeline run is for "Tiers CRUD" (mapped to `tier-category`). Building the full MC framework in this pipeline run effectively merges two epics into one.

**Evidence**: `"developer": "ritwik", "epics": ["maker-checker", "tier-category"]`

**Impact**: Not necessarily wrong (same developer owns both), but it means this pipeline run is larger than a single epic. The MC framework should ideally have its own BA/PRD/tests, not be a sub-section of the tier CRUD pipeline.

**Recommendation**: Acceptable to build both in one pipeline run since the same developer owns both, but track MC framework and Tier CRUD as separate deliverables within this run. Ensure tests for MC framework are entity-agnostic (not tier-specific).

---

## Summary

| # | Severity | Contradiction | Status |
|---|----------|--------------|--------|
| C-1 | BLOCKER | Thrift method for tier sync may not exist | Open -- needs resolution |
| C-2 | ~~HIGH~~ LOW | PartnerProgramSlab impact — reduced (DRAFT-only deletion, no SQL refs) | Deferred to future tier retirement epic |
| C-3 | HIGH | PeProgramSlabDao blast radius understated | Open -- needs migration strategy |
| C-4 | MEDIUM | Threshold validation oversimplified | Open -- refine in HLD |
| C-5 | LOW | "Scheduled" KPI undefined | Open -- clarify naming |
| C-6 | LOW | MC framework scope vs registry decomposition | Accepted -- same developer |
