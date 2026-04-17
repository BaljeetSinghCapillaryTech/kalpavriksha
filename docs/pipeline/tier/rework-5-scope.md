# Rework #5 — Scoping Document (in progress)

> Rework cycle: **#5**
> Started: 2026-04-17
> Status: **Q&A phase** — decisions accumulate here as they are locked. Artifacts (BA, HLD, LLD, BTG, migrator, api-handoff) are NOT yet updated. Full cascade happens after all 9 rework points are answered.

---

## Locked Decisions So Far

### C-1: ADR-06 reversed — unified read surface
The "new programs only" restriction is dropped. The new `/v3/tiers` API must return **all** tiers — both new-UI-origin (Mongo) and legacy SQL-origin.

### C-2: Drop `nudges` from tier schema
The "Nudges" section is removed from the new tier UI. The `nudges` field is removed from `UnifiedTierConfig`.
- Standalone `Nudges` entity (`com.capillary.shopbook.springdata.mongodb.model.Nudges`, endpoints `/v2/nudges/*`, Thrift methods `createOrUpdateNudges`, `getAllNudges`, `updateNudgeStatus`) is **untouched**.
- `engineConfig.notificationConfig` **stays** — that's the in-tier notification config, not the standalone Nudges entity.

### C-3: Drop `basicDetails.startDate`/`endDate` + UI Duration column
- `basicDetails.startDate`/`endDate` removed from Mongo schema.
- Duration column dropped from the new tier UI.
- `validity.startDate`/`endDate` (program validity window — different semantic) **stays**.

### Q-1a: Read-only SQL→DTO converter on GET
Legacy SQL-only tiers surface through `/v3/tiers` GETs via a read-only converter that reshapes SQL data into the new response DTO. **No write to Mongo** on read. **No bootstrap migration** of legacy tiers into Mongo.

---

## Q-1b — Dual write paths, single MC scope

### The Rule

Maker-checker applies **if-and-only-if** the write originated from the **new UI**. The distinguishing axis is "which UI wrote", not "which UI originally created".

### Write-path matrix

| Write Origin | Target Tier Origin | Write Target | MC? | Mongo doc created? |
|---|---|---|---|---|
| Old UI | Legacy (SQL-only) | SQL direct (existing legacy path) | ❌ | No |
| Old UI | New-UI-origin (SQL ACTIVE + Mongo history) | SQL direct (existing legacy path) | ❌ | No (Mongo history may go stale — see Point 2) |
| New UI | Legacy (SQL-only) | Mongo DRAFT created from SQL snapshot → MC → Thrift → SQL | ✅ | Yes, on Save Draft |
| New UI | New-UI-origin | Mongo DRAFT → MC → Thrift → SQL | ✅ | Yes, on Save Draft |

### Read-path matrix (per Point 3)

**Single source of truth rule: LIVE state is ALWAYS read from SQL — never from Mongo.**

| Read Origin | Tier State Needed | Source Queried | Notes |
|---|---|---|---|
| Old UI | LIVE | SQL `program_slabs` (legacy path, unchanged) | Old UI is blind to Mongo |
| New UI — detail GET | LIVE (`live` field) | SQL `program_slabs` via converter | Covers both legacy + new-UI-origin tiers |
| New UI — detail GET | DRAFT / PENDING (`pendingDraft` field) | Mongo `UnifiedTierConfig`, filtered `status IN [DRAFT, PENDING_APPROVAL]` | `null` if no active draft |
| New UI — list GET | LIVE rows | SQL `program_slabs` (one query) | Returns N rows |
| New UI — list GET | DRAFT/PENDING (for `pendingDraft` per row) | Mongo (one query, in-memory join) | Returns M ≤ N docs; map by `slabId`, attach per SQL row |
| New UI — history view | SNAPSHOT | Mongo `UnifiedTierConfig`, filtered `status = SNAPSHOT` | Audit/history only — not current state |

### Backend read algorithm (detail GET)

```
GET /v3/tiers/42:
  liveRow       = SQL.findOne(program_slabs WHERE id=42 AND org_id=? AND program_id=?)
  pendingDraft  = Mongo.findOne(orgId, programId, slabId=42, status IN [DRAFT, PENDING_APPROVAL])
  return { live: convert(liveRow), pendingDraft: pendingDraft_or_null }
```

### Backend read algorithm (list GET)

```
GET /v3/tiers?programId=7:
  liveRows   = SQL.find(program_slabs WHERE program_id=7 AND org_id=? AND is_active=true)       // N rows
  drafts     = Mongo.find(orgId, programId=7, status IN [DRAFT, PENDING_APPROVAL])              // M ≤ N docs
  draftMap   = Map by slabId (or tierUniqueId for new-tier DRAFTs with null slabId)
  return liveRows.map(row => ({ live: convert(row), pendingDraft: draftMap.get(row.id) ?? null }))
```

**Two DB hits per list page.** No N+1. Mongo index used: Index 1 `(orgId, programId, status)` from Q-3c.

### Why a tier's doc can exist in Mongo with non-DRAFT status — and why it's irrelevant to LIVE reads

After MC approval, the Mongo doc transitions:
- `PENDING_APPROVAL` → `SNAPSHOT` (preserved as audit record).
- SQL ACTIVE row is the post-approval LIVE state.

The Mongo SNAPSHOT doc exists, but the read path **never reads it as current state** — it's only read by the history view. The `live` field in every API response comes from SQL alone.

### Q-1b-i — Name-collision handling on concurrent create

**Decision: (a) Best-effort validation + SQL unique constraint backstop.**

Layers of defense (in order):
1. **At DRAFT creation** (new UI `POST /v3/tiers`): check name uniqueness against (SQL tiers for that program) ∪ (existing Mongo DRAFTs for that program). Reject early with a friendly error if a collision is already visible.
2. **At approval time** (just before Thrift call): re-check uniqueness. A tier may have been created via old UI in the meantime. If the re-check fails, the approval is blocked with: *"Name '&lt;X&gt;' no longer available — conflicts with existing tier. Please rename or cancel this DRAFT."*
3. **SQL unique constraint** `UNIQUE (program_id, name)` on `program_slabs`: final backstop. If a race slips through both checks, the Thrift INSERT fails and the MC service surfaces a well-formed error to the approver.

### Q-1b-ii — When the Mongo DRAFT is created

**Decision: (a) On Save Draft, not on view.**

- Opening a legacy tier in the new UI just reads via the SQL→DTO converter. **No Mongo doc.**
- Viewing a legacy tier by multiple users simultaneously does NOT create multiple drafts.
- The DRAFT doc is created the moment the user explicitly clicks **Save Draft** (or **Submit for Approval**).
- This keeps Mongo clean and makes Point 9's "single active DRAFT per tier" enforceable (a unique index can key on `(programId, slabId, status IN [DRAFT, PENDING_APPROVAL])` without being defeated by stray view-time docs).

---

## Worked Examples

### Example 1 — Legacy tier edited via new UI (happy path)

**Before:**
- SQL `program_slabs`: `{id:42, program_id:7, name:"Gold", threshold:1000}`
- Mongo `UnifiedTierConfig`: *no doc for slabId 42*

**Flow:**

1. User opens new UI, selects program 7, lists tiers.
   → New UI calls `GET /v3/tiers?programId=7`.
   → Backend reads SQL `program_slabs` for program 7, runs SQL→DTO converter, returns ACTIVE tiers including "Gold".
   → **No Mongo write.**

2. User clicks Edit on "Gold", changes threshold 1000 → 1200, clicks **Save Draft**.
   → New UI calls `POST /v3/tiers/42/draft` with the edited payload.
   → Backend:
     - Reads SQL tier 42 → snapshots into a DTO.
     - Applies user's edits on top.
     - Runs uniqueness check at DRAFT creation (Layer 1): name "Gold" still unique in program 7 ✓.
     - Creates `UnifiedTierConfig` doc in Mongo: `{_id:<newMongoId>, slabId:42, programId:7, status:DRAFT, basicDetails:{name:"Gold", ...}, engineConfig:{thresholds:[{slabId:42, value:1200}]}, ...}`.

3. User clicks **Submit for Approval**.
   → Mongo doc status flips `DRAFT → PENDING_APPROVAL`.

4. Approver approves in new UI.
   → `MakerCheckerService.approve` → `TierApprovalHandler.publish`.
   → Uniqueness re-check at approval (Layer 2): name "Gold" still unique in SQL ✓.
   → Thrift call: `createSlabAndUpdateStrategies(programId=7, slabInfo{id:42, threshold:1200}, strategyInfos)`.
   → SQL UPDATE: `program_slabs.threshold = 1200 WHERE id=42`.
   → Mongo doc status flips `PENDING_APPROVAL → SNAPSHOT` (retention) or `ACTIVE` depending on retention policy (Q-6 territory).

**Invariants:** SQL is truth for LIVE reads; Mongo held the proposed change during MC; no Mongo doc existed while the tier was idle.

---

### Example 2 — Concurrent edit: old UI changes tier mid-MC (Point 2 preview)

**Before:**
- SQL: `{id:42, name:"Gold", threshold:1000}`
- Mongo: `{slabId:42, status:PENDING_APPROVAL, proposed threshold:1200, basis:{threshold:1000}}`

**Flow:**

1. User A submitted a DRAFT via new UI (now PENDING_APPROVAL). Proposed threshold 1200 (basis captured as 1000 at draft time).
2. User B opens old UI, edits tier 42 threshold 1000 → 1500, clicks Save.
   → Legacy endpoint: SQL UPDATE threshold=1500. No MC.
   → SQL now: `{id:42, threshold:1500}`. Mongo PENDING DRAFT still says `proposed:1200, basis:1000`.
3. Approver opens new UI to review User A's pending DRAFT.

**Open question:** What does the approver see, and what happens on approve?
- Option A: Approver sees both the proposed change AND a "tier state has drifted since this DRAFT was created" warning. Approve is allowed but overwrites B's 1500 with A's 1200.
- Option B: Stale DRAFTs are auto-invalidated. Approver sees "This DRAFT is stale because the tier was modified outside MC on 2026-04-17 by User B. Recreate DRAFT to proceed."
- Option C: Hybrid — block approval, require explicit "rebase DRAFT on current SQL" action.

**This is Point 2 — deferred to Q-2.**

---

### Example 3 — Creation name collision, approval blocked at Layer 2

**Before:**
- SQL program 7: no tier named "Platinum".
- Mongo: no DRAFT for "Platinum".

**Flow:**

1. User A (new UI) creates DRAFT "Platinum" in program 7.
   → Layer 1 uniqueness check passes → Mongo DRAFT created.
2. User A submits → PENDING_APPROVAL.
3. User B (old UI) creates a tier named "Platinum" in program 7 via legacy endpoint.
   → Legacy endpoint: SQL INSERT → `{id:55, program_id:7, name:"Platinum"}`. No MC.
4. Approver tries to approve User A's DRAFT.
   → Layer 2 uniqueness re-check: "Platinum" now exists in SQL → **approval blocked**.
   → Approver sees: *"Name 'Platinum' no longer available — conflicts with existing tier (SQL id=55). Rename or cancel this DRAFT."*
   → User A must rename the DRAFT or cancel.

**Even if Layer 2 were skipped**, Layer 3 (SQL `UNIQUE(program_id, name)`) would reject the Thrift INSERT with a DB exception, which the MC service translates into the same user-facing error.

---

### Example 4 — Legacy tier edited via old UI (unchanged legacy flow)

**Before:**
- SQL: `{id:42, name:"Gold", threshold:1000}`
- Mongo: no doc.

**Flow:**

1. User opens old UI, edits tier 42 threshold 1000 → 1100, clicks Save.
   → Legacy endpoint: SQL UPDATE threshold=1100. **No MC. No Mongo write.**
2. Anyone listing tiers via old UI or new UI sees threshold=1100 (SQL is the read source for LIVE).

**Invariant:** Legacy path is untouched. New UI's list shows the updated value because it reads LIVE from SQL via the converter.

---

### Example 5 — New-UI-origin tier edited via old UI (edge case)

**Before (tier 55 was created by new UI + approved earlier):**
- SQL: `{id:55, name:"Silver", threshold:500}` (ACTIVE after earlier MC approval)
- Mongo: SNAPSHOT doc for slabId 55 holding the historical DRAFT that was approved.

**Flow:**

1. User opens old UI, edits tier 55 threshold 500 → 600, clicks Save.
   → Legacy endpoint: SQL UPDATE threshold=600. No MC. No Mongo write.
2. SQL now has 600. Mongo SNAPSHOT still shows threshold=500 from the earlier approved version.

**Tension:** The Mongo SNAPSHOT no longer matches SQL. This is fine for LIVE reads (SQL wins per Point 3), but the "history" view via Mongo becomes misleading — it reads as "last approved value: 500" when current SQL is 600.

**This is a facet of Point 2 (drift) and also touches audit/history semantics — flag for Q-2 and possibly Q-6 (parentId/history semantics).**

---

## Open Items Flagged by Q-1b (resolved below in Q-2)

| Ref | Flagged From | Resolution |
|---|---|---|
| Point 2 | Example 2 | See Q-2a below — stale-detect + block |
| Point 2 | Example 5 | See Q-2b below — SNAPSHOT audit-only, timestamped |
| Point 6 + Q-6 | Example 5 | SNAPSHOT = "last approved via MC at timestamp T", not guaranteed == current SQL |

---

## Q-2 — Data mismatch when old UI edits a new-UI-origin tier

### Q-2a — Drift mid-MC (while a DRAFT is PENDING_APPROVAL)

**Decision: (b) Stale detection + block at approval.**

**Mechanism:**
1. When a DRAFT is created in Mongo, capture a **basis snapshot** of the SQL tier state at that moment. Store as `meta.basisSqlSnapshot` (or equivalent) inside `UnifiedTierConfig`. Contains the SQL-level view of the tier: slab fields + strategy fields that MC governs.
2. At approval time (in `TierApprovalHandler.preApprove` or `publish`), re-read current SQL tier state.
3. Compare current SQL state against `meta.basisSqlSnapshot`.
4. If any drift detected → **block approval**. Approver sees:
   > *"This DRAFT is based on a state that no longer matches the live tier. SQL changed since this DRAFT was created — by &lt;user or 'external system'&gt; at &lt;timestamp&gt;. Cancel or recreate this DRAFT to proceed."*
5. DRAFT must be cancelled (Mongo status → DISCARDED) or the user must recreate a fresh DRAFT on top of current SQL.

**Consequence for UX:** The new UI must surface the drift reason clearly. No silent overwrite. MC remains a meaningful review gate.

**Consequence for LLD:** `UnifiedTierConfig` gains a `meta.basisSqlSnapshot` field (or similar). `TierApprovalHandler.preApprove` gains a drift-check step. Flag for Designer.

**Follow-up detail (Designer's call):** What constitutes "drift"?
- **Conservative:** full-tier equality (any SQL change at all, even unrelated fields, blocks approval).
- **Permissive:** only compare fields that the DRAFT proposes to change (drift in unrelated fields is tolerated).
- **Recommendation:** start conservative (block on any drift) — simpler, safer, and drift-via-legacy should be rare in practice. Revisit if operational friction emerges.

### Q-2b — Drift post-MC (SNAPSHOT semantics when old UI edits later)

**Decision: (z) Audit-only, possibly stale, timestamped.**

**Mongo SNAPSHOT contract:**
- A SNAPSHOT document holds the tier state **at the moment it was approved via MC**. Nothing more.
- SNAPSHOT is **not** maintained as current state. If the tier is later edited via old UI (legacy SQL direct), the SNAPSHOT is **not** updated.
- SNAPSHOT carries `meta.approvedAt` (timestamp) and `meta.approvedBy` (user).
- New UI's "history / version log" view must label each SNAPSHOT row as *"Approved via new UI on &lt;approvedAt&gt; by &lt;approvedBy&gt;. May differ from current state if edited via old UI after this date."*
- Current state is read from SQL; SNAPSHOT is purely historical audit.

**Consequence for UX:** New UI history screens must show a caveat when there are legacy edits after the last MC approval (detectable by comparing last SNAPSHOT's `approvedAt` against current SQL `updated_at`).

**Consequence for LLD:** SNAPSHOT is write-once-at-approval, read-only thereafter. No reconciliation loop needed. Legacy endpoints remain completely untouched.

### Worked example — Q-2a in action

**Before:**
- SQL `program_slabs`: `{id:42, name:"Gold", threshold:1000, updated_at: T0}`
- Mongo DRAFT: `{slabId:42, status:PENDING_APPROVAL, proposed_threshold:1200, meta.basisSqlSnapshot:{threshold:1000, updated_at:T0}, meta.draftedAt:T1}`

**Flow:**
1. Old UI user edits tier 42 threshold 1000 → 1500 at time T2 via legacy path.
   → SQL: `{id:42, threshold:1500, updated_at:T2}`. No Mongo touch.
2. Approver opens new UI, reviews DRAFT for tier 42 at time T3, clicks Approve.
   → `preApprove`: re-read current SQL tier 42 → `{threshold:1500, updated_at:T2}`.
   → Compare against `meta.basisSqlSnapshot` `{threshold:1000, updated_at:T0}` → **drift detected** (T2 > T0, threshold 1500 ≠ 1000).
   → Approval blocked. Mongo DRAFT stays PENDING_APPROVAL.
   → Approver sees: *"This DRAFT is based on a state that no longer matches the live tier. SQL changed since this DRAFT was created — threshold is now 1500 (was 1000 at draft time). Cancel or recreate this DRAFT."*
3. User A must cancel the DRAFT or create a fresh one on top of SQL's current 1500.

### Worked example — Q-2b in action

**Before:**
- SQL: `{id:55, name:"Silver", threshold:500, updated_at: T0}`
- Mongo SNAPSHOT: `{slabId:55, status:SNAPSHOT, threshold:500, meta.approvedAt:T0, meta.approvedBy:"alice"}`

**Flow:**
1. Old UI user edits tier 55 threshold 500 → 600 at time T1 via legacy path.
   → SQL: `{id:55, threshold:600, updated_at:T1}`. Mongo SNAPSHOT untouched.
2. Someone opens new UI's history view for tier 55.
   → Shows:
     - Row: *"Approved via new UI on &lt;T0&gt; by alice. Threshold: 500. ⚠ Tier has been edited via old UI after this date (current SQL: 600, updated at T1). This snapshot reflects the approval state only."*
   → Current live state: threshold 600 (from SQL).

**Invariant:** Mongo SNAPSHOT is audit-truth for MC approvals. SQL is truth for current live state. The UI reconciles them visually, not via data reconciliation.

---

## Q-3 — Hybrid reads: SQL for LIVE, Mongo for DRAFT/PENDING

### Q-3a — "LIVE promotions" → "LIVE tiers" (typo confirmation)

**Decision:** typo. Point 3 reads as "LIVE **tiers**" throughout. No cross-entity concern with promotions.

### Q-3b — `GET /v3/tiers/{id}` response shape when both SQL ACTIVE and Mongo DRAFT/PENDING exist

**Decision: (b) Envelope — always return both states in a single response.**

```
GET /v3/tiers/42
→ {
    live: { id:42, name:"Gold", threshold:1000, status:"ACTIVE", ... },
    pendingDraft: { status:"PENDING_APPROVAL", threshold:1200, draftedBy:"alice" }  // null if none
  }

GET /v3/tiers?programId=7
→ [
    { live: {...}, pendingDraft: {...} },
    { live: {...}, pendingDraft: null },
    ...
  ]
```

**Rationale:**
- Single round-trip for approval review (the highest-value screen).
- Conceptual model: one tier = one response, possibly with a pending change alongside.
- Scale is bounded (max ~50 tiers per program, max 1 active DRAFT per tier) → envelope overhead is small and predictable.

**Consequences:**
- Approver UI reads `live` vs `pendingDraft` side-by-side from one response.
- Editor re-opens a DRAFT by reading the same endpoint; uses `pendingDraft` if present, else `live` as starting point.
- List endpoint returns envelope per row — clients render `live` + badge from `pendingDraft !== null`.

### Q-3c — Mongo compound index shape on `UnifiedTierConfig`

**Decision: two compound indexes (tenancy-led).**

```
Index 1: { orgId: 1, programId: 1, status: 1 }
Index 2: { orgId: 1, programId: 1, slabId: 1 }
```

**What each covers:**
- Index 1 → tier list filter by status, approval queue reads, history lookups.
- Index 2 → "does tier X have a DRAFT?" (used on every tier detail GET to populate `pendingDraft`), AND forms the base for Point 9's unique partial index.

**Point 9 preview:** Index 2's field tuple is directly reusable for the uniqueness constraint on "single active DRAFT per tier" — either as a unique partial index upgrade on Index 2 itself, or as a third index with identical fields plus a `partialFilterExpression`. Either way, Q-3c's shape is compatible.

**Write overhead:** 2 indexes on a collection with max ~5,000 hot docs (before SNAPSHOT retention) is negligible.

**Query profile documented for Designer:**
| # | Query | Index used |
|---|---|---|
| Q1 | Tier list with hasPendingDraft badge | Index 1 + Index 2 per row |
| Q2 | Tier detail, populate `pendingDraft` envelope | Index 2 |
| Q3 | Approval queue (org-wide) | Index 1 |
| Q4 | Approval action by `_id` | Default `_id` index |
| Q5 | History view per tier | Index 2 |
| Q6 | Uniqueness check on DRAFT creation (Point 9) | Index 2 (upgraded to unique partial) |

---

## Q-7 — Schema cleanup (multi-part)

### Q-7a — Drop `nudges`
Already locked in **C-2**. `nudges` field removed from `UnifiedTierConfig`. Standalone `Nudges` entity (sibling, own endpoints) untouched.

### Q-7b — Drop `benefitIds`
**Decision: drop.** Tiers have no knowledge of benefits. If Benefits feature needs a tier↔benefit link, it lives on the Benefit side.

### Q-7c — Drop `updatedViaNewUI` from Mongo
**Decision: drop.** Not required. Simplifies the schema. Any "was this via MC?" audit info is conveyed by the presence of SNAPSHOT history and the new `approvedBy`/`approvedAt` SQL columns.

### Q-7e — Rename `unifiedTierId` → `tierUniqueId`
**Decision: mechanical rename.** Field `unifiedTierId` (format e.g. `"ut-977-004"` — prefix + program id + sequence) is renamed to `tierUniqueId` throughout:
- Mongo field name (`@Field` annotation if present)
- Java field (`private String tierUniqueId`)
- Getters/setters
- JSON property on the wire
- All references in DTOs, Facade, Controller, tests, artifacts

**Functionality unchanged** — same ID, same format, same generation strategy. Pure rename.

### Q-7f (implicit) — Drop `basicDetails.startDate`/`endDate` + UI Duration column
Already locked in **C-3**.

### Q-7d — `metadata` + `basicDetails` merge direction
**Decision: (c) hoist to root.** Both wrappers are eliminated. All their fields move to top-level `UnifiedTierConfig`, consistent with how `engineConfig`, `validity`, `parentId`, `status`, `tierUniqueId` already sit at root.

**Resulting shape (illustrative — subject to cleanup during Q-8):**
```
UnifiedTierConfig {
  _id,
  tierUniqueId,           // ex Q-7e rename
  slabId,                 // ex metadata.sqlSlabId, renamed per Q-8
  orgId, programId,
  name, description, icon, colorHex,   // ex basicDetails.*
  updatedAt, updatedBy,                 // hoisted from metadata
  version,                              // hoisted from metadata
  status,
  engineConfig: { ... },
  validity: { ... },
  parentId,
  ...
}
```

**Dropped during hoist:**
- `basicDetails.startDate`, `basicDetails.endDate` (per C-3)
- `metadata.updatedViaNewUI` (per Q-7c)
- `metadata.createdBy` (not in Mongo — note: `createdBy` is also being excluded from SQL per user's earlier decision, so this stays dropped in Mongo too)
- `basicDetails` wrapper, `metadata` wrapper themselves (per Q-7d)
- `nudges` (per C-2)
- `benefitIds` (per Q-7b)

---

## SQL `program_slabs` — new audit columns

As part of this rework, `program_slabs` gains three columns (Flyway migration required):

| Column | Type | Semantic | Legacy-write behaviour |
|---|---|---|---|
| `updatedBy` | VARCHAR | User who performed the last mutation | Set on every update from either UI |
| `approvedBy` | VARCHAR | User who approved the last MC-flow change | Set only when new-UI MC pushes to SQL; NULL for legacy direct writes |
| `approvedAt` | DATETIME | Timestamp of last MC approval | Set only via MC push; NULL or unchanged for legacy direct writes |

**NOT added:** `createdBy` (explicitly excluded per user).

**Implications:**
- Legacy path sets only `updatedBy` on the row; `approvedBy`/`approvedAt` remain whatever they were (NULL for rows never touched by MC).
- MC push path (Thrift `createSlabAndUpdateStrategies`) sets all three.
- Columns to be added in a Flyway migration inside the tier rework set — details handled by `/migrator` in Phase 6b.

---

## Q-8 — Rename `sqlSlabId` → `slabId`

**Decision: mechanical rename.** After Q-7d hoist, this field sits at root.

```
Before: UnifiedTierConfig.metadata.sqlSlabId   (nested under metadata)
After:  UnifiedTierConfig.slabId               (root-level)
```

**Rename scope:** Mongo field, Java field, getters/setters, JSON property, all DTOs, Facade, Controller, Thrift mappings, tests, artifacts.

**Null semantics (unchanged):**
| Status | `slabId` |
|---|---|
| DRAFT (new tier) | `null` |
| PENDING_APPROVAL (new tier) | `null` |
| DRAFT / PENDING_APPROVAL (edit of existing LIVE tier) | populated (= existing `program_slabs.id`) |
| After MC approval → SQL pushed | populated |
| SNAPSHOT | populated (reflects SQL id at time of approval) |

---

## Q-9 — Single active DRAFT/PENDING per tier

### Q-9a — Scope
**Decision: (a) Per tier.** Each tier can have at most one active DRAFT or PENDING_APPROVAL document. Different tiers in the same program can independently have their own drafts. Editing tier A is not blocked by tier B being in review.

### Q-9b — Enforcement mechanism
**Decision: (c) Both — app-level check + DB partial unique index.**

**App-level (in `TierFacade.createDraft` or `submitForApproval`):**
1. Before insert, query: `findOne({orgId, programId, slabId, status IN [DRAFT, PENDING_APPROVAL]})`.
2. If found → return a friendly business error: *"Tier '<name>' already has a pending change (status: <DRAFT|PENDING_APPROVAL>) created by <user> on <date>. Please review or cancel it before making new changes."*

**DB-level backstop (Mongo partial unique index):**
```
db.UnifiedTierConfig.createIndex(
  { orgId: 1, programId: 1, slabId: 1 },
  { unique: true, partialFilterExpression: { status: { $in: ["DRAFT", "PENDING_APPROVAL"] } } }
)
```
Enforced by MongoDB. Catches any race-condition where two concurrent requests slip past the app-level check. Returns `DuplicateKeyException` which the Facade translates into the same user-facing error.

**Coverage notes:**
- For NEW tiers (DRAFT with `slabId = null`), MongoDB's unique index treats `null` values as non-conflicting — multiple concurrent NEW-tier DRAFTs with null slabId co-exist. This is correct: each will get its own `slabId` on MC approval. No false collisions.
- For existing tiers (DRAFT with `slabId` populated), the partial unique index strictly enforces "at most one active DRAFT/PENDING_APPROVAL per existing slab".

**Reuses Q-3c Index 2 fields** — this is the same `(orgId, programId, slabId)` tuple upgraded to a unique partial index. Write cost is comparable to the plain Index 2.

---

## Q-6 — `parentId` semantics

**Decision: (a) `parentId` = parent's `slabId`** (i.e. foreign key to `program_slabs.id`).

**Rules:**
- A tier's parent is identified by the parent's SQL `slabId`.
- Works uniformly for legacy parents (SQL-only) and new-UI-origin parents (both have `slabId` once LIVE).
- **A DRAFT tier cannot be a parent.** To be a parent, a tier must be LIVE in SQL (i.e. have a non-null `slabId`). This is enforced at validation time when a DRAFT's `parentId` is set.
- No bootstrap migration needed — respects Q-1a.
- No cross-store correlation needed (e.g. no joining Mongo for parent lookup) — parent data reads straight from SQL.

**Validation rules for `parentId`:**
1. At DRAFT creation / edit: if `parentId` is set, verify that `program_slabs` has a row with that id, same `orgId`, same `programId`. Else reject with: *"Parent tier not found in program."*
2. Self-reference prevented: a tier's `parentId` cannot equal its own `slabId`.
3. Cycle prevention (if tier chains are allowed): if A's parent is B and B's parent is C, a DRAFT cannot set C's parent to A. May defer to Designer — flag for LLD.

---

## M-1 — Doc format

**Decision: (b) Markdown only.** Scoping doc lives as `rework-5-scope.md`. No `.docx` generation.

---

## Q&A phase — COMPLETE

All 9 rework points and the doc format are now locked. Scoping is signed off.

Next step: **artifact cascade** — propagate these decisions into BA, HLD, LLD, BTG, migrator plan, and api-handoff. Execution triggered by user "go".
