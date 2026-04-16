# Blocker Decisions -- Tiers CRUD

> Phase 4: Grooming Questions + Blocker Resolution
> Date: 2026-04-11

---

## BLOCKER #1: No Thrift method for tier config sync

**Source**: Critic C-1 / Analyst G-1
**Severity**: BLOCKER — RESOLVED
**Finding**: Thrift methods for slab CRUD already exist in pointsengine_rules.thrift (createSlabAndUpdateStrategies, getAllSlabs, createOrUpdateSlab)
**Decision**: Use existing Thrift methods. PointsEngineRulesThriftService just needs wrapper methods added.
**Rationale**: No new Thrift IDL change required. Existing service boundary preserved.
**Impact**: Zero impact on Thrift. Minor wrapper method additions in intouch-api-v3.

## HIGH #1: PartnerProgramSlab cascade on tier deletion → DEFERRED

**Source**: Critic C-2
**Severity**: HIGH → NOT APPLICABLE (Rework #2)
**Analysis**: Only DRAFT tiers can be deleted; DRAFTs have no SQL record / no PartnerProgramSlab refs
**Decision (Rework #2)**: No action needed for current scope. DRAFT tiers exist only in MongoDB — they have no ProgramSlab SQL record and therefore no PartnerProgramSlab references.
**Deferred To**: Future tier retirement epic (when ACTIVE tier stopping is implemented, this guard will be needed).
**Handoff Note**: When tier retirement is built, add: (1) block stop if PartnerProgramSlabs reference the slab (409), or (2) cascade stop to partner slabs.

## HIGH #2: PeProgramSlabDao blast radius → NOT NEEDED (Rework #3)

**Source**: Critic C-3
**Severity**: HIGH → N/A (Rework #3)
**Analysis**: SQL only contains ACTIVE tiers (synced via Thrift on approval). No ACTIVE tier can be deleted (DRAFT-only deletion). No PAUSED/STOPPED states exist.
**Decision (Rework #3)**: **No changes to ProgramSlab or PeProgramSlabDao needed.**
Every row in program_slabs is always active — a status column has zero use.
**Deferred To**: Future tier retirement epic (when ACTIVE tier stopping is implemented, this migration will be needed).

## SCOPE #1: Tier Duration missing from BA/PRD

**Source**: UI-BA GAP-1
**Severity**: HIGH (UI field with no API backing)
**Decision**: Add startDate/endDate to MongoDB tier document
**Details**: Maps to membership validity period. endDate=null means Indefinite. On Thrift sync, maps to TierDowngradePeriodConfig.startDate and strategy period value.

## SCOPE #2: isDowngradeOnReturnEnabled toggle

**Source**: Three-way gap A-2 / BRD Open Question
**Severity**: MEDIUM
**Decision**: Preserve in MongoDB doc as hidden config. Don't surface in new UI. Pass through on Thrift sync unchanged.
**Rationale**: Existing behavior toggle. Surfacing/deprecating is a product decision beyond tier CRUD scope.

## SCOPE #3: Notification templates complexity

**Source**: Three-way gap A-7
**Severity**: MEDIUM
**Decision**: Store BOTH nudges text (UI) AND notificationConfig object (engine) in MongoDB doc. They coexist independently.
**Details**: New tiers start with empty notificationConfig. Existing tiers populated from strategy config on bootstrap. UI reads/writes the text field. Thrift sync reads the config object.

---

## Grooming Decisions (non-blocking)

| # | Question | Decision | Rationale |
|---|---------|----------|-----------|
| GQ-1 | Pagination for tier listing? | No pagination. Full list. Max 50 cap. | Programs have 3-7 tiers typically. Pagination is unnecessary overhead. |
| GQ-2 | Bootstrap sync for existing programs? | NO. New system for new programs only. | User override. Old programs keep current system. No migration. |
| GQ-3 | Multiple drafts per ACTIVE tier? | Update existing DRAFT in place. One DRAFT per ACTIVE parent. Flow A: ACTIVE stays live until approval. | Zero downtime. Same as unified promotions. |
| GQ-4 | Benefits in listing: full config or refs? | benefitIds only. UI fetches details separately. | User override. Keeps tier API decoupled from benefits data source. |
| GQ-5 | MC notification: real or hook? | Hook interface only (NotificationHandler). No-op default. | Keeps MC framework focused. Real notification is separate concern. |
| GQ-6 | PendingChange: snapshot or diff? | Full snapshot. | Simpler, approver sees full state, ChangeApplier needs full config. |
| C-5 | "Scheduled" KPI undefined | Replace with "Pending Approval" count. | No goLiveDate concept for tiers. pendingApprovalTiers is the closest meaningful metric. |

---

## All Open Questions -- Final Status

| # | Question | Status | Resolution |
|---|---------|--------|------------|
| Blocker #1 | Thrift sync method | RESOLVED | Use existing createSlabAndUpdateStrategies. No IDL change needed. |
| C-2 | PartnerProgramSlab cascade | DEFERRED | Not needed for DRAFT-only deletion. Deferred to future tier retirement epic. |
| C-3 | DAO blast radius | NOT NEEDED (Rework #3) | No SQL changes at all. SQL only contains ACTIVE tiers. |
| C-4 | Threshold validation | DEFERRED | To HLD (Phase 6) |
| C-5 | "Scheduled" KPI | RESOLVED | Replace with "Pending Approval" |
| GAP-1 | Tier Duration | RESOLVED | startDate/endDate on MongoDB doc |
| A-2 | Downgrade on return toggle | RESOLVED | Preserve hidden, pass through |
| A-7 | Notification templates | RESOLVED | Dual storage (nudges text + config object) |
| A-1,A-3-A-11 | Hidden engine configs | RESOLVED | All preserved in MongoDB doc |
| GQ-1 through GQ-6 | Grooming questions | ALL RESOLVED | See table above |
| BA open questions | Remaining 4 | ALL RESOLVED | Cache refresh, notification hook, benefits refs, Thrift signature |
| G-5 | Sharded MongoDB | NOTED | For HLD -- follow UnifiedPromotionRepository pattern |
| G-6 | Edit flow complexity | NOTED | For Phase 5 -- study UnifiedPromotionEditOrchestrator |
