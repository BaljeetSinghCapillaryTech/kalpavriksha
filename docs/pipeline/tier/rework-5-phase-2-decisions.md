# Rework #5 — Phase 2 Decisions Log

> Running log of clarifying questions and decisions for Rework #5 Phase 2 (drift detection + dual-path reads + SqlTierReader concrete impl).
>
> Phase split (revised after Q4 follow-up):
> - **Phase 2AB (combined)** — `ThriftSqlTierReader` concrete impl + `TierDriftChecker` + `basisSqlSnapshot` population in `TierFacade.createVersionedDraft` + drift-check wiring in `TierApprovalHandler.preApprove`.
> - **Phase 2C** — `TierFacade.listTiers`/`getTierDetail` refactor to envelope shape, `TierController` return types to `TierEnvelope`, self-heal write-back of Mongo ACTIVE on read mismatch, `KpiSummary.activeTiers` → `liveTiers` rename.

---

## Research Findings (pre-questions)

- `TierMeta.basisSqlSnapshot: Map<String,Object>` is already declared — flexible shape, we choose the contents.
- Thrift `SlabInfo` (read DTO) exposes only 6 fields: `id, programId, serialNumber, name, description, colorCode`. No `lastModifiedBy/On` on reads.
- Thrift `StrategyInfo` carries tier's eligibility/validity/downgrade via `owner == slabId` + `propertyValues` JSON blob.
- No single-slab Thrift read — either filter `getAllSlabs` in memory or extend IDL.
- `TierFacade.listTiers` currently returns flat `List<UnifiedTierConfig>` with `LIVE_STATUSES` filter + inline KPI computation.
- `TierController` returns `UnifiedTierConfig` / `TierListResponse` directly — under Rework #5 must return envelope-shaped results.
- `TierApprovalHandler.publish` already syncs Mongo → SQL via `createOrUpdateSlab`; `postApprove` mirrors SQL ids back to the Mongo ACTIVE doc.

---

## Question 1 — Read strategy

**Q:** How should `TierFacade` read the LIVE side of tiers — pure SQL via Thrift, Mongo ACTIVE as LIVE mirror, or Mongo-first with drift check at approve?

**A (user):** **Option A — pure SQL via Thrift**, with an additional rule: **self-heal Mongo ACTIVE on read** when it differs from SQL.

**Rationale (user):** Tiers can be edited from both old UI (writes direct to SQL, never touches Mongo) and new UI (writes Mongo → publishes to SQL). SQL is therefore the only sole source of truth. Mongo ACTIVE is a projection/cache that can go stale; on read we trust SQL and correct Mongo if mismatched.

**Locked behaviour:**
- Read path always hits SQL via Thrift (`getAllSlabs` + `getAllConfiguredStrategies`).
- Envelope LIVE side = SqlTierRow-derived TierView (SQL-authoritative).
- Mongo ACTIVE doc exists and differs → overwrite Mongo ACTIVE with SQL truth (self-heal).
- Mongo DRAFT / PENDING_APPROVAL docs are **never** self-healed — they are in-flight workflow state, not projections.
- Approve path: re-read SQL, diff against `basisSqlSnapshot`, block with `ConflictException("APPROVAL_BLOCKED_DRIFT", basisDiff)` on mismatch.
- Scenario #5 (LEGACY_SQL_ONLY) is the default case, not an edge case.

---

## Question 2 — `updatedBy`/`updatedAt` on the LIVE side

**Q:** Thrift `SlabInfo` has no `lastModifiedBy/On` on the read contract. How do we populate LIVE-side `TierMeta`?

- (a) Accept null.
- (b) Extend Thrift IDL to add the fields.
- (c) Hybrid — use Mongo ACTIVE's values when Mongo ACTIVE matches SQL; else null.

**A (user):** **(c) Hybrid.**

**Locked behaviour:** If Mongo ACTIVE exists and is in-sync with SQL (no self-heal write happened this read), surface its `updatedBy/At` on the LIVE TierMeta. Otherwise null.

**Caveat 2 (self-heal concurrency) — confirmed OK:** Self-heal write only targets docs with `status == ACTIVE`; never touches DRAFT / PENDING_APPROVAL. Idempotent across concurrent readers. Eventually consistent if old UI writes concurrently.

---

## Question 3 — `basisSqlSnapshot` shape and source

### 3a — Shape of the `Map<String,Object>` contents

- (a) Flat top-level keys + nested config objects.
- (b) Fully flattened (dot-notation keys).
- (c) Wholesale serialization of the entire SqlTierRow.

**A (user):** **(a) Flat top-level keys + nested config objects.**

**Locked schema:**
```json
{
  "name": "Gold",
  "description": "Premium tier",
  "color": "#FFD700",
  "serialNumber": 3,
  "eligibility": { "kpiType": "LIFETIME_POINTS", "threshold": 5000.0 },
  "validity":    { "periodValue": 12 },
  "downgrade":   { "target": "THRESHOLD" }
}
```

**Excluded from snapshot** (not drift-meaningful): `slabId, orgId, programId, updatedBy, updatedAt, memberStats, engineConfig`.

### 3b — Snapshot source at DRAFT creation

- (i) Fresh SQL fetch via Thrift at DRAFT creation.
- (ii) Use the current Mongo ACTIVE doc as snapshot (no extra Thrift call).

**A (user):** **(i) Fresh SQL fetch via Thrift at DRAFT creation.**

**Locked behaviour:** `TierFacade.createVersionedDraft` calls `SqlTierReader.readLiveTierBySlabId(orgId, activeSlabId)` and serializes the result (per 3a schema) into `meta.basisSqlSnapshot`. Guarantees the snapshot represents actual SQL state, not a potentially-stale Mongo ACTIVE projection. Brand-new DRAFTs (no preceding ACTIVE) have `basisSqlSnapshot = null`.

---

## Question 4 — Drift-check scope at approve time

### 4a — Thrift calls at approve time

- (a) One call — `getAllSlabs` + in-memory filter (misses strategy drift).
- (b) Two calls — `getAllSlabs` + `getAllConfiguredStrategies`, filter by slabId.
- (c) Reuse `SqlTierReader.readLiveTierBySlabId` (single abstraction).

**A (user):** **(c) Reuse `SqlTierReader.readLiveTierBySlabId`.**

**Locked behaviour:** `TierApprovalHandler.preApprove` calls `sqlTierReader.readLiveTierBySlabId(orgId, entity.slabId)`, serializes to the Q3a snapshot schema, diffs against `entity.meta.basisSqlSnapshot`. One abstraction, one place to optimize later.

### 4b — Drift semantics

- (a) Strict — any field mismatch blocks.
- (b) Semantic — diff drift-meaningful fields only with whitespace-trim + color-hex case-normalize.
- (c) Field-subset with approver override UI prompt.

**A (user):** **(b) Semantic diff on drift-meaningful fields with normalization.**

**Locked behaviour:**
- Compared fields: `{name, description, color, serialNumber, eligibility, validity, downgrade}` — exactly the snapshot schema from Q3a.
- Normalization before compare: strings trimmed; color hex uppercased (e.g. `#ffd700` == `#FFD700`); nested configs compared by semantic equality (not JSON string equality).
- Mismatch → throw `ConflictException("APPROVAL_BLOCKED_DRIFT", basisDiff)` with `basisDiff: List<{field, basis, current}>` on the exception payload so the UI can render a "what changed" list.
- No approver-override UX in this sprint (scope deferred to Phase 3 if desired).

## Question 4 follow-up — Build order for 2A vs 2B

**Q:** 4a=(c) makes drift detection depend on `SqlTierReader.readLiveTierBySlabId` which has no concrete impl yet. Reader-first / drift-first-with-inline / merge?

- (i) Reader-first — 2B before 2A.
- (ii) Drift-first with inline read — refactor into reader in 2B.
- (iii) Merge 2A+2B into a single sub-phase.

**A (user):** **(iii) Merge 2A+2B.**

**Locked behaviour:** Phase 2 becomes two sub-phases, not three — **2AB** (reader + drift + wiring into approval handler) and **2C** (facade/controller refactor + self-heal). No throwaway inline code.

## Question 5 — Pausing cadence

**Q:** How should the two sub-phases be paced?

- (a) Pause between 2AB and 2C (same rhythm as Phase 1A/1B).
- (b) Pause only at end of Phase 2, run 2AB and 2C back-to-back with clean commits per sub-phase.
- (c) Finer pauses within 2AB (after reader tests green, after drift checker green, after wiring green).

**A (user):** **(a) Pause between 2AB and 2C.**

**Locked behaviour:** Complete Phase 2AB end-to-end (compile clean, all existing + new tests green), write summary, propose commit, stop. Await user approval before starting 2C.

---

## Consolidated Phase 2 Plan

### Phase 2AB — Reader + Drift Detection + Approval Wiring

**New files:**
1. `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/sql/ThriftSqlTierReader.java` — `@Component`; calls `thriftService.getAllSlabs(programId, orgId)` + `thriftService.getAllConfiguredStrategies(programId, orgId)`; groups strategies by `owner == slabId`; JSON-parses `propertyValues` per `strategyTypeId` into `TierEligibilityConfig` / `TierValidityConfig` / `TierDowngradeConfig`; returns `List<SqlTierRow>` or single `SqlTierRow`.
2. `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/drift/TierDriftChecker.java` — pure function. `check(basisSqlSnapshot: Map<String,Object>, current: SqlTierRow) -> DriftResult { boolean drifted; List<FieldDiff> diffs }`. Normalizes strings (trim, color-hex uppercase), compares drift-meaningful fields only.
3. `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/drift/DriftResult.java` + `FieldDiff.java` — data records.
4. New tests: `ThriftSqlTierReaderTest` (fake `PointsEngineRulesThriftService`), `TierDriftCheckerTest` (pure-function unit tests — no collaborators).

**Modified files:**
5. `TierFacade.createVersionedDraft` — add call to `sqlTierReader.readLiveTierBySlabId(orgId, active.getSlabId())`, serialize result to Q3a snapshot map (via a small helper on `TierDriftChecker.buildSnapshot(SqlTierRow) -> Map<String,Object>`), set `draft.meta.basisSqlSnapshot = snapshot`. Brand-new DRAFTs (no prior ACTIVE) remain with `basisSqlSnapshot = null`.
6. `TierApprovalHandler.preApprove` — after existing name-uniqueness check, if `entity.meta.basisSqlSnapshot != null` and `entity.slabId != null` (versioned edit of an ACTIVE): call `sqlTierReader.readLiveTierBySlabId(orgId, slabId)` → `driftChecker.check(basisSnapshot, currentSqlRow)` → if drifted, throw `ConflictException("APPROVAL_BLOCKED_DRIFT")` carrying the `List<FieldDiff>` in the exception payload.
7. Updated tests: `TierFacadeTest` (snapshot population on createVersionedDraft), `TierApprovalHandlerTest` (drift-block and drift-pass cases via fake reader).

**Not in Phase 2AB:**
- `TierFacade.listTiers` / `getTierDetail` refactor — Phase 2C.
- `TierController` return-type change — Phase 2C.
- Mongo ACTIVE self-heal write-back — Phase 2C.
- `KpiSummary.activeTiers` → `liveTiers` rename — Phase 2C.

### Phase 2C — Envelope wiring + self-heal + KPI rename (after pause)

Details locked at start of 2C based on 2AB outcomes.

---

## Status

- All 5 clarifying questions answered. Phase 2AB plan locked.
- Ready to start Phase 2AB on user green-light.

---

## Mid-Phase 2AB — Requirement Change + Strategy-Sync Gap

### Finding (evidence-based, Rule 1)

`TierApprovalHandler.publish` (`/Users/ritwikranjan/Desktop/emf-parent/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/TierApprovalHandler.java:80-110`) calls **only** `thriftService.createOrUpdateSlab` — which writes the `program_slabs` row (name, description, color, serialNumber) but writes **zero strategy rows**.

Evidence:
- SlabInfo Thrift DTO has 6 fields only — no eligibility/validity/downgrade (confirmed: `/Users/ritwikranjan/Desktop/emf-parent/Thrift/thrift-ifaces-pointsengine-rules/gen/gen-java/com/capillary/shopbook/pointsengine/endpoint/api/external/SlabInfo.java:47-52`).
- Grep `createOrUpdateStrategy|StrategyInfo|createSlabAndUpdateStrategies` in `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier` returned zero matches.

Consequence under Option A (SQL is truth): `SqlTierReader` would return new-UI-approved tiers with null eligibility/validity/downgrade — incomplete LIVE reads.

### User requirement change (received mid-phase)

**Message 1:** "Now the sync with the Mongo is Not Needed. When the tier becomes live everything occur through emf-parent sql tables and we will create the entry."

**Message 2 (clarifier):** "Mongo will hold the doc but while fetching we will be using the SQL only. If you think this is really really hard, we can go with this approach which we finalized if you want."

Interpretation: Mongo still **retains** the doc post-approval (write side unchanged). Read side uses SQL only. No self-heal needed (because Mongo ACTIVE is never read as LIVE source). Therefore strategy-sync to SQL is mandatory for complete reads.

### Path selection

- **(1) Escape hatch — split truth** (AI recommendation): SQL for slab-level fields, Mongo ACTIVE for strategy-level fields, self-heal on slab-level mismatch. Avoids engine-internals research.
- **(2) Push through full SQL truth:** research strategyTypeId mapping + propertyValues JSON schema, then implement SAGA strategy sync, then ship Phase 2AB.
- **(3) Other.**

**A (user):** **(2) Push through full SQL truth.**

### Revised Phase 2AB scope (locks in)

**New upfront research (blocks coding):**
1. `strategyTypeId` → tier concept mapping: which id is eligibility, validity, downgrade?
2. `propertyValues` JSON schema per tier strategy type — what keys does the engine expect on read-back?
3. Does the engine key strategies to a slab via `StrategyInfo.owner == slabId`, or via a join table? What field holds the linkage?
4. Existing callers of `createOrUpdateStrategy` for tiers (any reference impl to mirror)?

**Add to Phase 2AB (after research):**
- Extend `TierApprovalHandler.publish` to also create/update eligibility/validity/downgrade strategy rows — preferably via `createSlabAndUpdateStrategies` (atomic) if we can pre-create strategies, else via separate `createOrUpdateStrategy` calls.
- New helper: `TierStrategyTransformer` (or similar) — converts `TierEligibilityConfig`/`ValidityConfig`/`DowngradeConfig` → `StrategyInfo` rows with correct strategyTypeId and serialized propertyValues JSON.
- `ThriftSqlTierReader` reverse transformer: parse `StrategyInfo.propertyValues` JSON → `TierEligibilityConfig`/etc.
- Tests for both transformers (pure-function unit tests, round-trip).

**Deferred self-heal:** Not needed — Mongo ACTIVE is never read as LIVE under the user's clarified model.

**Revised Phase 2C scope:** Envelope wiring + `TierController` return types + KpiSummary rename. Drop self-heal. Mongo ACTIVE is retained post-approval as audit history; reads bypass it entirely.

---

## Correction — Research Outcome (evidence-based)

### Research complete. Prior "strategy-sync gap" framing was overstated.

After doing the engine-internals research, the key facts and a correction to my earlier framing:

**Fact 1 — StrategyType enum (C7, verified from code)**
`emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/StrategyType.java:36-49`:
```
POINT_ALLOCATION(1), SLAB_UPGRADE(2), POINT_EXPIRY(3), POINT_REDEMPTION_THRESHOLD(4),
SLAB_DOWNGRADE(5), POINT_RETURN(6), EXPIRY_REMINDER(7), TRACKER(8), POINT_EXPIRY_EXTENSION(9)
```
Tier-relevant types: **SLAB_UPGRADE(2)** (eligibility/thresholds) and **SLAB_DOWNGRADE(5)** (downgrade + validity).
There is **no separate VALIDITY type** — validity is modeled inside SLAB_DOWNGRADE's per-slab `periodConfig`.

**Fact 2 — Strategy is program-level, NOT slab-level (C7, verified from code)**
`emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/Strategy.java:68-70`:
```java
public enum StrategyOwner { LOYALTY, CAMPAIGN }
```
`Strategy.owner` is a `LOYALTY / CAMPAIGN` tag, **NOT** a slabId. One SLAB_UPGRADE strategy exists per program and holds thresholds for ALL slabs in a CSV. One SLAB_DOWNGRADE strategy exists per program and holds a `slabs[]` array with one entry per slab.

**Fact 3 — SLAB_UPGRADE JSON schema (C7, verified from code)**
`ThresholdBasedSlabUpgradeStrategyImpl.java:89-122` — private static class `ThresholdSlabUpgradeValues`:
- `threshold_values: String` — CSV of per-slab thresholds (e.g. `"5000,10000"` for a 3-slab program)
- `current_value_type: String` — CUMULATIVE_POINTS / CURRENT_POINTS / CUMULATIVE_PURCHASES / TRACKER_VALUE_BASED
- `tracker_id: String`, `tracker_condition_id: String` — only for TRACKER_VALUE_BASED
- `additional_upgrade_criteria: ArrayList<AdditionalUpgradeCriteria>` — beyond-default criteria
- `expression_relation: ArrayList<ArrayList<Integer>>`, `custom_expression: String`
- Plus ~25 comms fields (sms_template, email_body, weChatTemplate, mobilePush…) — **not in intouch-api-v3 DRAFT model**; must be PRESERVED on read-modify-write.

**Fact 4 — SLAB_DOWNGRADE JSON schema (C7, verified from code)**
`TierDowngradeStrategyConfiguration.java:13-38`:
- `isActive: boolean`, `dailyDowngradeEnabled: boolean`, `retainPoints: boolean`
- `isDowngradeOnReturnEnabled: boolean`, `isDowngradeOnPartnerProgramExpiryEnabled: boolean`
- `slabs: TierDowngradeSlabConfig[]` — per-slab entries keyed by `slabNumber`
- `downgradeConfirmation`, `renewalConfirmation`, `reminders[]` — comms configs (program-level)

`getTierDowngradeSlabConfig(slabNumber)` — finds per-slab config by iterating `slabs[]` looking for `slabNumber` match.

**Fact 5 — HLD already architected this (C7, verified from artifact)**
`docs/pipeline/tier/01-architect.md:508-527`:
```
3. Build SLAB_UPGRADE StrategyInfo (type 2):
   - Read current threshold_values CSV
   - Append new tier's threshold at end
   - Preserve current_value_type, expression_relation

4. Build SLAB_DOWNGRADE StrategyInfo (type 5):
   - Parse current TierConfiguration JSON
   - Add new slab entry to slabs[] array

5. Call Thrift: createSlabAndUpdateStrategies(...)
   a. Updates SLAB_UPGRADE strategy (new threshold)
   b. Updates SLAB_DOWNGRADE strategy (new slab entry)
   c. Creates ProgramSlab record
   d. updateStrategiesForNewSlab() auto-extends POINT_ALLOCATION + POINT_EXPIRY CSVs
```

UPDATE flow at line 553-566:
```
3. If eligibility changed: replace threshold at CSV position (serialNumber - 2)
4. If downgrade config changed: find slab entry by slabNumber, update it
5. Call createSlabAndUpdateStrategies with SlabInfo + modified strategies
```

### Correction

My mid-phase framing of a "strategy-sync gap" was **overstated**. The gap isn't architectural — the HLD already fully specifies the read-modify-write algorithm for both CREATE and UPDATE paths. The actual gap is purely implementation: `TierApprovalHandler.publish` today only calls `createOrUpdateSlab` instead of `createSlabAndUpdateStrategies`. Filling that gap is a finite coding task, not a research-heavy re-architecting.

User's **A=2 (push through full SQL truth)** choice is consistent with and mandated by the already-approved HLD. No scope drift.

### Research blockers — status

| # | Research item | Answer | Evidence |
|---|---------------|--------|----------|
| 1 | strategyTypeId mapping | SLAB_UPGRADE=2 (eligibility+upgrade), SLAB_DOWNGRADE=5 (downgrade+validity), no separate VALIDITY type | `StrategyType.java:36-49` + HLD §7.1 |
| 2 | propertyValues schema per type | `ThresholdSlabUpgradeValues` (CSV thresholds) + `TierDowngradeStrategyConfiguration` (slabs[] JSON) | `ThresholdBasedSlabUpgradeStrategyImpl.java:89-122` + `TierDowngradeStrategyConfiguration.java` |
| 3 | Strategy-to-slab linkage | Program-level strategies; per-slab values embedded INSIDE propertyValues (threshold CSV position = serialNumber-2; slabs[].slabNumber for downgrade). `owner` is LOYALTY/CAMPAIGN tag. | `Strategy.java:68-70` + HLD §7.1-7.2 |
| 4 | Reference impls | Old UI flow (`PointsEngineRuleConfigThriftImpl.createSlabAndUpdateStrategies:397-438`) is the write-side reference; engine does the heavy lifting | Code read above |

All 4 blockers resolved. Ready to proceed.

---

## Phase 2AB — Final Locked Plan

### New files
1. `tier/sql/ThriftSqlTierReader.java` — `@Component` implementing `SqlTierReader`. Calls `thriftService.getAllSlabs` + `getAllConfiguredStrategies`. Uses `TierStrategyTransformer.fromStrategies(...)` to hydrate eligibility/validity/downgrade on each `SqlTierRow`.
2. `tier/strategy/TierStrategyTransformer.java` — pure functions:
   - `fromStrategies(SlabInfo slab, List<StrategyInfo> programStrategies) → SqlTierRow` — derive eligibility/validity/downgrade for ONE slab from program-level strategies (reverse path; used by ThriftSqlTierReader).
   - `applySlabUpgradeDelta(String currentCsv, int slabIndex, int newThreshold, boolean isAppend) → String` — update threshold at `serialNumber - 2` (UPDATE) or append (CREATE).
   - `applySlabDowngradeDelta(String currentJson, int slabNumber, TierDowngradeConfig newCfg, boolean isAppend) → String` — update or append `slabs[]` entry.
   - Tests: round-trip + boundary cases (empty CSV, missing slab entry, malformed JSON).
3. `tier/drift/TierDriftChecker.java` + `DriftResult.java` + `FieldDiff.java` — pure function drift detector. Compares `basisSqlSnapshot` (Q3a schema) against a current `SqlTierRow`. Normalizes strings (trim, color hex uppercase).
4. Tests: `ThriftSqlTierReaderTest`, `TierStrategyTransformerTest`, `TierDriftCheckerTest` (all pure-unit tests with fakes at the Thrift boundary).

### Modified files
5. `TierFacade.createVersionedDraft` — call `sqlTierReader.readLiveTierBySlabId(orgId, active.slabId)`, serialize to Q3a snapshot map via `TierDriftChecker.buildSnapshot(SqlTierRow)`, set `draft.meta.basisSqlSnapshot = snapshot`. Brand-new DRAFTs keep `basisSqlSnapshot = null`.
6. `TierApprovalHandler.preApprove` — after name-uniqueness: if `entity.meta.basisSqlSnapshot != null && entity.slabId != null`: call reader → diff → throw `ConflictException("APPROVAL_BLOCKED_DRIFT")` with `List<FieldDiff>` payload.
7. `TierApprovalHandler.publish` — replace single `createOrUpdateSlab` with the HLD §7.1/7.2 flow:
   - Fetch current program strategies via Thrift.
   - Build/modify SLAB_UPGRADE + SLAB_DOWNGRADE `StrategyInfo` via `TierStrategyTransformer.applySlabUpgradeDelta` / `applySlabDowngradeDelta`.
   - Call `thriftService.createSlabAndUpdateStrategies(programId, orgId, slabInfo, [upgradeStrategy, downgradeStrategy], userId, now, serverReqId)`.
   - Preserve all non-tier fields (sms/email/weChat, `current_value_type`, `expression_relation`, `downgradeConfirmation`/`reminders`) — read-modify-write, never overwrite wholesale.
8. `TierFacadeTest` + `TierApprovalHandlerTest` — new scenarios: snapshot populated on createVersionedDraft; drift-block and drift-pass cases; publish writes both slab + strategies (verify via fake thrift service recording calls).

### Explicitly NOT in Phase 2AB
- Listing endpoint / controller return-type refactor to `TierEnvelope` — **Phase 2C**
- `KpiSummary.activeTiers` → `liveTiers` rename — **Phase 2C**
- Mongo self-heal writes — **dropped** (not needed under user-clarified read model)
- Engine-side changes to `PointsEngineRuleConfigThriftImpl` — **out of scope**; we only call the existing atomic API

### Risks / open questions (flagged for user sign-off)
- **R1 — Cross-tier race in SLAB_UPGRADE CSV**: two concurrent approvals for different tiers both do read-modify-write on the same program's `threshold_values`. Last-write-wins could lose the other tier's threshold. [C4]
  Mitigation options: (a) accept — maker-checker rare enough in practice; (b) add distributed lock at program level in `TierApprovalHandler`; (c) optimistic concurrency via fetch-compare-retry. **Recommend (a) with a TODO for (b) if drift emerges.**
- **R2 — Preservation of comms fields**: the engine's SLAB_UPGRADE propertyValues has sms/email/weChat/mobilePush per-slab arrays that intouch-api-v3's DRAFT never touches. Transformer MUST read-modify-write — never construct a fresh propertyValues from DRAFT alone. [C6]
- **R3 — Schema coverage**: `TierEligibilityConfig.threshold: Double` → `threshold_values` CSV expects int. Need explicit cast + precision policy (round? truncate? reject fractional?). **Recommend: round to nearest int with a TRACE log, since engine CSV is int-only.** [C5]
- **R4 — Program-level boolean conflict resolution (raised mid-coding, resolved 2026-04-20)**: The engine's `TierDowngradeStrategyConfiguration` stores `isDowngradeOnReturnEnabled` and `dailyDowngradeEnabled` as **program-level top-level fields** (one per program). Intouch-api-v3's per-tier `TierDowngradeConfig` carries these as **per-tier fields** (`reevaluateOnReturn`, `dailyEnabled`). If tier A (reevaluateOnReturn=true) and tier B (reevaluateOnReturn=false) are both published to the same program, only one program-level value can persist. HLD §3 (01-architect.md:266–289) maps the fields but doesn't specify conflict resolution. [C5]
  Options considered: (a) last-writer-wins — whichever tier publishes most recently sets the program-level flag; (b) first-write-wins — transformer only sets if absent in currentJson; (c) explicit policy enum per call-site; (d) defer — ignore in transformer, handle upstream.
  **User chose (a) last-writer-wins.** Rationale: matches existing production semantics (pre-rework, multi-tier edits via legacy endpoints had the same behaviour); per-tier DTO implies the tier "owns" its view of these flags; lowest-surprise default. Documented in javadoc on `TierStrategyTransformer.applyProgramLevelBooleans`. [C6]
  **Residual risk**: UI may expect per-tier independence; if in future a per-tier override becomes a product requirement, this will need re-engineering at the engine schema level (not a transformer concern). Call-sites should log the overwrite so forensic trails exist.

### Ready to code

All research closed. Plan locked. Awaiting user green-light to start Phase 2AB implementation (TDD, pure-function-first, test-red-then-green-then-refactor).

---

## Question 6 — Scope of `extractEligibilityForSlab` (raised mid-coding, resolved 2026-04-20)

**Q:** The reverse path for SLAB_UPGRADE needs an extractor. `TierEligibilityConfig` carries `kpiType`, `threshold`, `upgradeType`, `expressionRelation`, `conditions`. Only `threshold` is per-slab (CSV at `serialNumber - 2`); the rest are program-level in the engine (`current_value_type`, `expression_relation`, trackers). Which should the extractor populate?

Options considered:
- (a) **Minimal — drift-check sufficient**: `threshold` + `kpiType` only. Matches what the drift checker actually compares. Per-tier edits can't mutate the program-level fields anyway, so surfacing them into the DTO invites spurious "drift" signals on unrelated program changes.
- (b) **Symmetric with `extractDowngradeForSlab`**: populate `upgradeType`, `expressionRelation` too. Future-proof if the workflow ever allows program-level edits through the per-tier path.
- (c) **Inline in composite `fromStrategies`**: skip the narrow helper; map directly when assembling SqlTierRow.

**A (user): (a) Minimal.** Scope matches the one real consumer (drift check). Slab-1 → `threshold=null` (no inbound threshold; it's the entry tier). Out-of-range `serialNumber` → `IndexOutOfBoundsException` (caller bug — drift between slab entity and strategy CSV). Absent `current_value_type` → `kpiType=null` (defensive, not a crash). [C6]

**Residual:** if a future driving test requires `upgradeType`/`expressionRelation`/`conditions` on the LIVE view, extend symmetric with the downgrade reverse path — don't pre-emptively widen scope now.

**Implemented:** `TierStrategyTransformer.extractEligibilityForSlab(String engineJson, int serialNumber) → TierEligibilityConfig`, 6 unit tests covering slab-1-null / slab-2-first / middle-slab / absent-kpi / round-trip / out-of-range.

---

## Question 7 — Backend validation parity vs TIERS_VALIDATIONS.md (raised mid-coding, resolved 2026-04-20)

**Q:** `docs/pipeline/tier/TIERS_VALIDATIONS.md` catalogs 40+ UI-side validations across 6 flows (Primary Info, Upgrade, Secondary Upgrade, Downgrade, Renewal, Validity). Existing backend validators (`TierCreateRequestValidator`, `TierUpdateRequestValidator`, `TierValidationService`) cover ~8 of them. Should Phase 2AB absorb the full parity work?

**A (user): Defer to Phase 2C.** Finish Phase 2AB first (SqlTierReader + DriftChecker + publish wiring). Then cut a dedicated phase scoped to the **HIGH-priority gaps only**, not full parity — some UI rules are pure UX (save-button-disabled) and don't need backend enforcement.

**HIGH-priority gap list (Phase 2C scope):**
| Rule | §in .md | Reason |
|---|---|---|
| `upgradeMode` enum (`ABSOLUTE_VALUE` / `ROLLING_VALUE` / `DYNAMIC`) | 3.2 | Business-critical — mis-mode produces wrong tier assignment. |
| `upgradeValue ≤ 2,147,483,647` | 3.2 | DB int overflow risk. |
| `trackerId` / `trackerConditionId` required when `upgradeType=TRACKER_VALUE_BASED` | 3.2 | Conditional required — silent null breaks runtime evaluation. |
| Secondary criteria conditionals when `secondaryCriteriaEnabled=true` | 3.3 | Conditional required. |
| `downgradeCondition` enum (`FIXED` / `FIXED_DURATION` / `FIXED_CUSTOMER_REGISTRATION`) | 3.4 | Business-critical. |
| `timePeriod` positive integer | 3.4 | Runtime error on negative/zero. |
| `downgradeTarget` required when `shouldDowngrade=true` | 3.4 | Conditional required. |

**Not absorbed into Phase 2C** (UI-only or low-priority):
- Field-name-length cap beyond UI display (backend already enforces 100-char max).
- "Save button disabled while blank" rules (backend 400 on null already covers).
- Renewal-period month caps (1..36) — add if product confirms regulation.
- Expression-relation bracket-expression validity — complex, add if drift from real payloads emerges.
- Start-date = 1st-of-month (§3.4) — UX ergonomic, not a data-integrity constraint.

**Additional design questions deferred to Phase 2C kickoff**:
- Single-error (current: fail-fast with `InvalidInputException`) vs multi-error response shape (breaking API change).
- Run at `createVersionedDraft` AND `submitForApproval`? (Current recommendation: both. Skip `preApprove` — field validation redundant with drift check.)
- kpiType/upgradeType whitelist cleanup in `TierCreateRequestValidator` — the existing whitelist mixes condition types (`PURCHASE/VISITS/POINTS/TRACKER`) with KPI types (`CURRENT_POINTS/LIFETIME_POINTS`); need to split. Also `upgradeType` whitelist (`EAGER/DYNAMIC/LAZY/IMMEDIATE/SCHEDULED`) doesn't match UI (`POINTS_BASED/PURCHASE_BASED/TRACKER_VALUE_BASED`) — field-naming mismatch to reconcile.

**Residual:** a gap-report mapping every rule in TIERS_VALIDATIONS.md → existing backend enforcement (if any) → Phase 2C action (enforce / document as UI-only / punt) should be the first deliverable of Phase 2C.

## Question V1–V5 — Validity mapping: intouch `TierValidityConfig` ↔ engine `slabs[n].periodConfig` (raised mid-coding, resolved 2026-04-20)

**Context.** After the periodConfig-wipe bug fix (step 4.5), `applySlabValidityDelta` is the next forward-path helper. The mapping is asymmetric — five decisions were needed before any code.

**Shape mismatch (evidence):**

| Intouch `TierValidityConfig` | Engine `slabs[n].periodConfig` | Source |
|---|---|---|
| `periodType` String | `type` enum (FIXED / SLAB_UPGRADE / SLAB_UPGRADE_CYCLIC / FIXED_CUSTOMER_REGISTRATION) | `TierValidityConfig.java:17-23`, `TierDowngradePeriodConfig.java:20-22` |
| `periodValue` Integer (months) | `value` int + `unit` enum NUM_MONTHS | same |
| `startDate` ISO-8601 String | `startDate` Date (Gson → millis) | same |
| `endDate` ISO-8601 String | — | no engine counterpart |
| `renewal` TierRenewalConfig | — | no engine counterpart on periodConfig |
| — | `computationWindowStartValue`, `computationWindowEndValue`, `minimumDuration` | engine-only |

**Decisions:**

- **Q-V1 — UPDATE preservation.** Chose (a): preserve engine-only fields (`computationWindowStartValue`, `computationWindowEndValue`, `minimumDuration`) on UPDATE. Same read-modify-write policy as `overlayDowngradeFields`. Intouch owns only `type`, `value`, `unit`, `startDate`; every other key on an existing `periodConfig` JsonObject is left untouched. Matches Decision R2.
- **Q-V2 — `endDate`.** Chose (a): drop on write, recompute on read. `endDate = startDate + periodValue months` is derived; storing it would cause drift. Transformer ignores `cfg.endDate` on write and `extractValidityForSlab` reconstructs it on read from the engine's `startDate` + `value`.
- **Q-V3 — Renewal.** Chose (d): defer to Phase 2C. `applySlabValidityDelta` ignores `cfg.renewal` entirely. Engine-side renewal plumbing is unconfirmed — safer to punt than to guess a field location.
- **Q-V4 — `startDate` format on the engine JSON.** Chose (a): parse ISO-8601 string to `java.util.Date`, write as `{"startDate": <timestamp_millis>}` to match Gson's default Date serialization. This matches what the engine's Gson reader expects on deserialization.
- **Q-V5 — `minimumDuration` default on APPEND.** Chose (a): omit from output JSON. Engine-side Gson will deserialize absence as 0 (primitive int default). No need for intouch to write a field it does not own.

**Implication.** `applySlabValidityDelta(currentJson, slabNumber, validityCfg, isAppend)` only writes `type`, `value`, `unit`, `startDate` into `slabs[n].periodConfig`. On UPDATE, every other key on an existing `periodConfig` survives. If `validityCfg == null`, the existing `periodConfig` is left entirely untouched (no-op). If `validityCfg.startDate == null`, no `startDate` key is written (engine can fall back to its own default).

## Question V6 — `endDate` on the reverse path (resolved 2026-04-20)

**Context.** Q-V2 said `endDate` is derived on read (engine has no such field). `extractValidityForSlab` needs to decide: compute it, or leave it null?

**Options:**
- (a) Transformer returns `endDate=null`. Downstream callers compute if needed.
- (b) Transformer computes `endDate = startDate + periodValue months` using calendar math.

**Decision: (a) — leave `endDate=null` in the reverse view.**

**Rationale.**
- Keeps the transformer a pure translator over JSON. No calendar math, no timezone choices, no leap-year / month-end edge cases.
- Engine mechanically has no `endDate`, so the reverse "gives back what the engine has" is the most faithful interpretation.
- Downstream consumers that need `endDate` (UI, API response layer) can compute it using a shared utility — consistent across callers, testable in isolation.
- Reversible: the transformer can add computation later without breaking existing callers (they'd just start seeing populated values where they had null).

**Scope note.** This means `extractValidityForSlab` populates only `periodType`, `periodValue`, and `startDate` (as ISO-8601 UTC String). `endDate` and `renewal` are always `null` in the returned DTO.

