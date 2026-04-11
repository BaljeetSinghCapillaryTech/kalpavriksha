# Grooming Questions -- Tiers CRUD

> Phase 4: All questions compiled from Phase 1-3, resolved interactively
> Date: 2026-04-11

---

## Questions from Phase 2 (Critic)

| # | Source | Question | Classification | Resolution |
|---|--------|---------|---------------|------------|
| C-1 | Critic | No Thrift method for tier sync | BLOCKER | New Thrift method configureTier() |
| C-2 | Critic | PartnerProgramSlab cascade on stop | SCOPE | Block (409) if references exist |
| C-3 | Critic | PeProgramSlabDao blast radius | FEASIBILITY | Expand-then-contract migration |
| C-4 | Critic | Threshold validation oversimplified | FEASIBILITY | Deferred to HLD |
| C-5 | Critic | "Scheduled" KPI undefined | SCOPE | Replace with "Pending Approval" |
| C-6 | Critic | MC framework scope vs registry | SCOPE | Accepted -- same developer |

## Questions from Phase 3 (UI)

| # | Source | Question | Classification | Resolution |
|---|--------|---------|---------------|------------|
| GAP-1 | UI | Tier Duration missing | SCOPE | Add startDate/endDate to MongoDB doc |
| GAP-2 | UI | Activity condition model | FEASIBILITY | Deferred to HLD -- compound condition structure |
| GAP-3 | UI | Membership Duration vs Duration | SCOPE | Different concepts. Both in MongoDB doc. |
| GAP-4 | UI | Downgrade Schedule enum | SCOPE | MONTH_END and DAILY enum values |
| GAP-5 | UI | Benefits matrix format | SCOPE | benefitIds only -- user override |
| GAP-6 | UI | Variable tier count | FEASIBILITY | API supports any count, max 50 cap |

## Questions from Three-Way Gap Analysis

| # | Source | Question | Classification | Resolution |
|---|--------|---------|---------------|------------|
| A-2 | Codebase | isDowngradeOnReturnEnabled | SCOPE | Preserve hidden, pass through |
| A-7 | Codebase | Notification templates | SCOPE | Dual storage (nudges + config) |
| A-1-A-11 | Codebase | All hidden engine configs | SCOPE | Preserved in MongoDB doc |

## Grooming Questions from PRD

| # | Question | Classification | Resolution |
|---|---------|---------------|------------|
| GQ-1 | Pagination for tier listing? | FEASIBILITY | No pagination. Max 50 cap. |
| GQ-2 | Bootstrap sync for existing programs? | SCOPE | NO. New programs only. User override. |
| GQ-3 | Multiple drafts per ACTIVE tier? | SCOPE | One DRAFT per ACTIVE. Flow A (ACTIVE stays live). |
| GQ-4 | Benefits linkage format? | SCOPE | benefitIds only. User override. |
| GQ-5 | MC notification mechanism? | FEASIBILITY | Hook interface only. |
| GQ-6 | PendingChange snapshot or diff? | FEASIBILITY | Full snapshot. |

## Open Questions from BA

| # | Question | Classification | Resolution |
|---|---------|---------------|------------|
| BA-1 | Thrift method signature | FEASIBILITY | Deferred to HLD. Method name: configureTier() |
| BA-2 | Member count cache refresh | FEASIBILITY | Cron job every 10 min. GROUP BY query. |
| BA-3 | MC notification | FEASIBILITY | Hook interface (resolved by GQ-5) |
| BA-4 | Benefits linkage | SCOPE | benefitIds only (resolved by GQ-4) |

---

**Summary**: 25 items compiled. 25 resolved (0 remaining open).
- 1 BLOCKER resolved
- 3 HIGH resolved
- 6 MEDIUM resolved/deferred
- 15 LOW/SCOPE/FEASIBILITY resolved
