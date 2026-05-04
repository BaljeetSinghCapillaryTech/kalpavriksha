# Architecture -- Tiers CRUD + Generic Maker-Checker Framework

> Phase 6: HLD
> Feature: Tiers CRUD
> Ticket: raidlc/ai_tier
> Date: 2026-04-11 (last major update: Rework #6a Phase 4 cascade, 2026-04-22)
> Confidence: C6 (verified patterns, 29 decisions locked + 19 Rework #5 decisions + 7 Phase 2AB decisions + 5 Rework #6a Phase 4 decisions, production payload analyzed, 198/198 intouch-api-v3 tests GREEN)
> Rework trail: Rework #3 (no SQL status column) → Rework #5 (unified read surface, dual write paths, schema cleanup) → Phase 2AB (atomic publish — split-brain closure; see §7.5 and ADR-07) → **Rework #6a (contract hardening — error-code rebanding, unknown-field hard flip, validity classification lock, PeriodType scope lock + conditional duration, external-consumer audit; see §6.5, §11 R13-R15, ADR-17R..ADR-21R)**. See `rework-5-scope.md`, `contradictions.md`, `q-op-3-consumer-audit.md`.

---

## 1. Current State Summary

### What Exists
- **ProgramSlab** entity (MySQL `program_slabs`): minimal -- id, orgId, programId, serialNumber, name, description, metadata JSON, createdOn. No status, no inline config.
- **Strategy** entities (MySQL `strategies`): 9 types storing tier behavior as JSON `propertyValues`. Key types: SLAB_UPGRADE(2) stores upgrade thresholds as CSV, SLAB_DOWNGRADE(5) stores TierConfiguration JSON with per-slab downgrade/renewal configs.
- **Thrift service** (`pointsengine_rules.thrift`): `createSlabAndUpdateStrategies`, `getAllSlabs`, `createOrUpdateSlab` methods exist. Called via `PointsEngineRulesThriftService` in intouch-api-v3.
- **UnifiedPromotion** pattern in intouch-api-v3: MongoDB draft storage, versioned editing (parentId), StatusTransitionValidator, EntityOrchestrator, @Lockable distributed lock, ResponseWrapper envelope.
- **Zero tier REST APIs** exist in intouch-api-v3. All tier operations go through internal Thrift calls.

### What We're Building
New tier CRUD REST APIs in intouch-api-v3, following the UnifiedPromotion pattern (MongoDB draft + SQL live), with a generic maker-checker framework that tiers are the first consumer of.

### Rework #5 Context (added 2026-04-17)
The legacy tier edit/create endpoints in intouch-api-v3 (pre-dating this feature) continue to exist and continue to write directly to SQL without MC. The new `/v3/tiers` APIs coexist with them. The key design change from Rework #5:

- **Unified read surface**: `/v3/tiers` GETs return all tiers — legacy SQL-origin AND new-UI-origin — via a read-only SQL→DTO converter for legacy data (no backfill into Mongo).
- **Dual write paths, single MC scope**: MC applies if-and-only-if the write originated from the new UI. Old UI writes are MC-free.
- **SQL as LIVE source of truth**: For every LIVE read, SQL is the sole source. Mongo holds in-flight (DRAFT/PENDING_APPROVAL) and audit-only (SNAPSHOT) docs.
- **Drift detection**: DRAFTs capture `meta.basisSqlSnapshot` at creation. `preApprove` re-reads SQL and blocks on drift.
- **Envelope response**: GETs return `{ live: ..., pendingDraft: ... | null }` per tier. Single round-trip.
- **SNAPSHOTs are audit-only**: Write-once-at-approval. Never reconciled with later legacy edits. UI surfaces a caveat on drift.

### Rework #6a Context (added 2026-04-22)

Rework #6a is a **contract-hardening rework** — zero new endpoints, zero schema migrations, zero new storage. It tightens the existing `/v3/tiers` wire contract agreed in Rework #5 against 5 silent failure modes surfaced by the Critic (contradictions C-7..C-17) and resolved in Phase 4 (Q-OP-1..Q-OP-3, C-7 Hybrid, C-8 Option A).

Five locked decisions:

| # | Decision | Phase 4 lock | Resolves | ADR |
|---|---|---|---|---|
| 1 | Phantom Q-locks cleared — Q9 re-locked on error code **9015**; Q18/Q19/Q21 citations removed from BA (either subsumed by Q24 or downgraded to forward guards) | C-7 Hybrid | Phantom Q-lock audit-trail drift | Captured in §6.5 contract table (no new ADR — doc-only) |
| 2 | Validity storage classification — per-tier `validity.periodType` + `validity.periodValue` are **canonical in per-slab engine storage** (`TierDowngradeSlabConfig[]` indexed by `slabNumber`, field `periodConfig`). Program-level `SlabUpgradeStrategy.propertyValues` carries only the 4 Class A booleans. | C-8 Option A | Program-level / per-tier ambiguity on `validity.*` | **ADR-18R** |
| 3 | Error-code rebanding — Rework #6a rejects occupy distinct band **9011-9020**; legacy band 9001-9010 untouched. Per-REQ distinct codes (no reuse). | Q-OP-1 Option (b) | C-9 silent contract break between Rework #4 validators and new rejects | **ADR-17R** |
| 4 | `PeriodType` enum scope lock — 6a handles `SLAB_UPGRADE`-family explicitly only. Engine enum has 4 values (NOT 5 — `FIXED_LAST_UPGRADE` was PRD-wording phantom; corrected Phase 7 §6a.6). `FIXED`, `FIXED_CUSTOMER_REGISTRATION` (FIXED family — 2 values), `SLAB_UPGRADE_CYCLIC` pass-through. **FIXED family requires `periodValue` on wire** — REQ-56 (new), code **9018**. Read-side null-safe for legacy FIXED tiers missing `periodValue`. | Q-OP-2 Option (c) + user caveat | C-12 (partial — scope locked, forward guard added) | **ADR-19R** |
| 5 | Unknown-field hard flip — Jackson `FAIL_ON_UNKNOWN_PROPERTIES=true` on the v3 tier DTOs; zero back-compat window; legacy `downgrade` field now returns `400 InvalidInputException` at deserialization time. External consumer audit: **zero internal backend callers** across 16 repos (evidence: `q-op-3-consumer-audit.md`). | Q-OP-3 Option (a) + Q11 | C-17 (partial — audited surface C5 → C6; residual C5 flagged to Phase 11) | **ADR-20R** + **ADR-21R** (write-narrow/read-wide) |

**What this rework does NOT change** (explicit scope floor):
- No new endpoints, no new Mongo collections, no Flyway migrations.
- No change to the MC state machine, the SAGA approve flow, or the atomic-publish pattern from Phase 2AB (ADR-07).
- No change to `basicDetails` hoisting, envelope response shape, or dual write paths from Rework #5.
- No change to per-slab engine storage schema — the per-slab `TierDowngradeSlabConfig[].periodConfig` already carries `periodType`/`periodValue`; ADR-18R documents this classification, it doesn't create it.

**What this rework defers to Designer (Phase 7)**:
- Exact merge semantics for PUT when `periodType` transitions SLAB_UPGRADE-family → FIXED-family without `periodValue` in the payload (payload-only check vs payload+stored doc check).
- Exact wire shape for read-side null safety on legacy FIXED tiers (omit-field vs explicit null vs 0).
- Exact error-message text and field-path hint for each 9011-9018 code (C-11 Jackson-config verification also lives here).

---

## 2. Pattern Evaluation

| Pattern | Fit | Tradeoff | Decision |
|---------|-----|----------|----------|
| Dual-storage (MongoDB + SQL) | HIGH (existing UnifiedPromotion) | Sync complexity vs draft isolation | Adopted (D-10) |
| Strategy pattern (ChangeApplier) | HIGH (existing EntityOrchestrator) | Interface overhead vs extensibility | Adopted (D-12) |
| Versioned documents (parentId) | HIGH (existing UnifiedPromotion) | Doc proliferation vs rollback safety | Adopted (D-13) |
| Expand-then-contract migration | HIGH (GUARDRAILS G-05.4) | Two-phase vs zero regression | Adopted (D-18) |
| Spring Data MongoRepository + Custom | HIGH (existing pattern) | Limitations on complex queries vs consistency | Adopted |
| Cron-based member count cache | MEDIUM | 10-min staleness vs simplicity | Adopted (D-29) |
| **Read-only SQL→DTO converter** (Rework #5) | HIGH | Extra code path vs zero migration risk | Adopted (KD-09) |
| **Envelope response shape** (Rework #5) | HIGH | Response size vs single round-trip | Adopted (KD-11) |
| **Basis SQL snapshot + drift check** (Rework #5) | HIGH | Extra storage + read vs silent overwrite | Adopted (KD-12) |
| **Mongo partial unique index** (Rework #5) | HIGH | Index maintenance vs race-safety | Adopted (KD-14) |
| **Dual write paths** (Rework #5) | HIGH | Two code paths vs legacy regression | Adopted (KD-10) — old UI direct-SQL, new UI MC path |

---

## 3. System Architecture

**Dual write paths (Rework #5):** Old UI writes continue via legacy direct-SQL endpoints (left path, MC-free). New UI writes go through the MC pipeline (right path, Mongo DRAFT → MC → Thrift → SQL). GETs on `/v3/tiers` merge both sources via the SQL→DTO converter + Mongo pendingDraft join.

```mermaid
graph TB
    subgraph "UIs"
        OLD_UI[Old UI<br/>Garuda legacy]
        NEW_UI[New UI<br/>Garuda new tier screens]
    end

    subgraph "intouch-api-v3 — Legacy path (pre-existing, unchanged)"
        LEGACY[Legacy tier endpoints<br/>direct SQL write<br/>NO MC, NO Mongo]
    end

    subgraph "intouch-api-v3 — New path (this pipeline)"
        TC[TierController<br/>/v3/tiers GET POST PUT DELETE]
        TRC[TierReviewController<br/>/v3/tiers/{tierId}/submit<br/>/v3/tiers/{tierId}/approve<br/>/v3/tiers/{tierId}/reject]
        TF[TierFacade<br/>createDraft / editDraft<br/>submitForApproval<br/>handleApproval<br/>listTiers / getTier]
        SCONV[SqlTierConverter<br/>read-only<br/>SQL program_slabs -> DTO]
        TR[TierRepository<br/>MongoDB<br/>partial unique index]
        TVS[TierValidationService<br/>name uniqueness 3 layers<br/>parentId LIVE check<br/>single-active-DRAFT check]
        MCS[MakerCheckerService&lt;T&gt;<br/>Generic Baljeet]
        TAH["TierApprovalHandler<br/>implements ApprovableEntityHandler<br/>preApprove: drift check + name re-check<br/>publish: Thrift<br/>postApprove: Mongo -> SNAPSHOT"]
        PERTS[PointsEngineRules<br/>ThriftService]
    end

    subgraph "makechecker/ (Baljeet - Generic)"
        MCS_impl["MakerCheckerService&lt;T&gt;<br/>SAGA<br/>preApprove -> publish -> postApprove<br/>onPublishFailure rollback"]
        AEH["ApprovableEntityHandler&lt;T&gt;<br/>validateForSubmission<br/>preApprove drift-check<br/>publish Thrift<br/>postApprove SNAPSHOT<br/>onPublishFailure / postReject"]
    end

    subgraph "MongoDB (EMF Cluster)"
        UTC[("unified_tier_configs<br/>implements ApprovableEntity<br/>status: DRAFT / PENDING_APPROVAL / SNAPSHOT<br/>meta.basisSqlSnapshot<br/>INDEX 1: orgId,programId,status<br/>INDEX 2 PARTIAL UNIQUE: orgId,programId,slabId<br/>where status IN DRAFT,PENDING_APPROVAL")]
    end

    subgraph "emf-parent (Thrift: port 9199)"
        PERS[PointsEngineRuleService]
        PSD[PeProgramSlabDao]
        SD[StrategyDao]
        ILS[InfoLookupService]
    end

    subgraph "MySQL — SINGLE SOURCE OF TRUTH for LIVE"
        PS[("program_slabs<br/>+ updatedBy, approvedBy, approvedAt<br/>UNIQUE program_id,name")]
        ST[(strategies)]
        CE[(customer_enrollment)]
    end

    subgraph "peb (unchanged)"
        TDB[TierDowngradeBatch]
        TRS[TierReassessment]
    end

    OLD_UI -->|REST legacy| LEGACY
    LEGACY -->|direct write<br/>sets updatedBy only| PS

    NEW_UI -->|REST /v3/tiers| TC
    NEW_UI -->|REST /v3/tiers/.../submit<br/>/approve /reject| TRC
    TC --> TF
    TRC --> TF
    TF -->|LIVE reads| SCONV
    SCONV -->|Thrift getAllSlabs| PERTS
    TF -->|DRAFT/PENDING reads<br/>+ writes| TR
    TF --> TVS
    TF --> MCS
    MCS --> MCS_impl
    MCS_impl --> TAH
    MCS_impl --> TR
    TAH --> AEH
    TAH -->|drift-check re-read SQL| PERTS
    TAH -->|publish write SQL| PERTS
    TR --> UTC
    PERTS -->|Thrift RPC| PERS
    PERS --> PSD
    PERS --> SD
    PERS --> ILS
    PSD --> PS
    SD --> ST
    TDB -.->|reads| PS
    TRS -.->|reads| PS
    ILS -.->|reads| CE
```

### Envelope read flow (list or detail GET on `/v3/tiers`)

```mermaid
sequenceDiagram
    participant UI as New UI
    participant TC as TierController
    participant TF as TierFacade
    participant SC as SqlTierConverter
    participant TR as TierRepository
    participant T as Thrift
    participant EMF as emf-parent
    participant SQL as MySQL program_slabs
    participant M as MongoDB unified_tier_configs

    UI->>TC: GET /v3/tiers?programId=7
    TC->>TF: listTiers(orgId, 7)
    TF->>T: getAllSlabs(orgId, 7)
    T->>EMF: Thrift RPC
    EMF->>SQL: SELECT * FROM program_slabs WHERE org_id=? AND program_id=7
    SQL-->>EMF: N rows
    EMF-->>T: List<SlabInfo>
    T-->>TF: liveRows (N)
    TF->>SC: convert(liveRows) -> List<TierDto>
    TF->>TR: findActiveDrafts(orgId, 7)
    TR->>M: find({orgId,programId:7,status IN [DRAFT,PENDING_APPROVAL]})<br/>uses Index 1
    M-->>TR: M docs (M<=N)
    TR-->>TF: List<UnifiedTierConfig>
    TF->>TF: draftMap = Map.by(slabId)<br/>in-memory join
    TF-->>TC: List<Envelope{live, pendingDraft}>
    TC-->>UI: ResponseWrapper
```

**Two DB hits per list page.** LIVE always from SQL. Mongo read bound to DRAFT/PENDING only. No N+1.

---

## 4. Module Breakdown

### 4.1 Tier Module (intouch-api-v3)

| Component | Responsibility |
|-----------|---------------|
| `TierController` | REST endpoints: GET /v3/tiers, POST, PUT, DELETE. Auth via AbstractBaseAuthenticationToken. **Returns envelope `{live, pendingDraft}` per tier (Rework #5).** |
| `TierReviewController` | REST endpoints: POST /v3/tiers/{tierId}/submit, POST /v3/tiers/{tierId}/approve, POST /v3/tiers/{tierId}/reject, GET /v3/tiers/approvals. |
| `TierFacade` | Business logic: createDraft, editDraft, submitForApproval, handleApproval, listTiers (envelope assembly), getTier (envelope). Orchestrates SQL→DTO converter + Mongo draft join. Captures `meta.basisSqlSnapshot` at DRAFT creation. |
| `SqlTierConverter` | **NEW (Rework #5).** Read-only converter that reshapes SQL `program_slabs` + strategies into the new response DTO. Used only on GETs — no write path uses it. |
| `UnifiedTierConfig` | MongoDB @Document. Implements `ApprovableEntity`. **Rework #5**: `basicDetails`/`metadata` hoisted to root; `nudges`, `benefitIds`, `updatedViaNewUI`, `basicDetails.startDate/endDate` dropped; `unifiedTierId` → `tierUniqueId`; `metadata.sqlSlabId` → root-level `slabId`; `meta.basisSqlSnapshot` added. |
| `TierRepository` | Spring Data MongoRepository + custom impl for sharded access. **Rework #5**: two compound indexes (see §5.3). Partial unique index on `(orgId, programId, slabId)` where `status IN [DRAFT, PENDING_APPROVAL]` enforces single-active-draft per tier. |
| `TierValidationService` | Field-level validation: name uniqueness (3 layers — Rework #5), threshold ordering, required fields, parentId LIVE check, single-active-draft pre-check. |
| `TierApprovalHandler` | Implements `ApprovableEntityHandler<UnifiedTierConfig>`. **Rework #5**: `preApprove` re-reads current SQL state and compares against `meta.basisSqlSnapshot` — blocks on any drift with a clear user-facing message. Also re-checks name uniqueness at approval time. `publish` calls Thrift `createSlabAndUpdateStrategies` to write SQL. `postApprove` transitions Mongo doc to SNAPSHOT with `meta.approvedAt`/`meta.approvedBy`. |
| `TierStatus` | Enum: DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT. No PAUSED or STOPPED (Rework #2). **Rework #5 clarifies**: ACTIVE is emitted on the read side (as the `live` envelope field derived from SQL). The Mongo doc itself transitions directly PENDING_APPROVAL → SNAPSHOT on approval — an ACTIVE Mongo doc is rare/ephemeral in practice and never read as LIVE state. |

### 4.2 Maker-Checker Module (makechecker/ -- Baljeet's Generic Package, Pre-Existing)

| Component | Responsibility |
|-----------|---------------|
| `MakerCheckerService<T>` | Generic state machine: submitForApproval(entity, handler, save), approve(entity, comment, reviewedBy, handler, save), reject(entity, comment, reviewedBy, handler, save). Implements SAGA pattern in approve(). |
| `ApprovableEntity` | Interface: getStatus(), setStatus(Object), getVersion(), setVersion(Long), transitionToPending(), transitionToRejected(String). |
| `ApprovableEntityHandler<T>` | Strategy interface: validateForSubmission(T), preApprove(T), publish(T) -> PublishResult, postApprove(T, result), onPublishFailure(T, error), postReject(T, comment). |
| `PublishResult` | Return type from publish(): contains version, external IDs, or other confirmation data. |

### 4.3 emf-parent Changes

> **Rework #3**: ProgramSlab status field, findActiveByProgram() REMOVED.
> **Rework #5**: SQL `program_slabs` gets three audit columns. Flyway migration IS needed (details in `01b-migrator.md`).

| Component | Change |
|-----------|--------|
| ~~`ProgramSlab` status field~~ | NOT NEEDED (Rework #3) |
| ~~`PeProgramSlabDao.findActiveByProgram()`~~ | NOT NEEDED (Rework #3) |
| `ProgramSlab` entity | **Rework #5**: Add `updatedBy`, `approvedBy`, `approvedAt` fields. `createdBy` explicitly NOT added. |
| `PeProgramSlabDao` | **Rework #5**: No new query methods. Existing queries are backward-compatible (new columns are nullable). Legacy write path sets `updatedBy` only (approvedBy/approvedAt untouched = NULL). MC-push path sets all three. |
| `PointsEngineRulesThriftService` | Add wrapper methods for `createSlabAndUpdateStrategies`, `getAllSlabs`, `createOrUpdateSlab`. **Rework #5**: `createSlabAndUpdateStrategies` signature extended to carry `updatedBy`, `approvedBy`, `approvedAt`. Thrift IDL field additions are optional-typed for backward compatibility (G-05 / Thrift optional-fields-only rule). |
| **Flyway migration (Rework #5)** | `ALTER TABLE program_slabs ADD COLUMN updatedBy VARCHAR(255) NULL, ADD COLUMN approvedBy VARCHAR(255) NULL, ADD COLUMN approvedAt DATETIME NULL;` — see `01b-migrator.md` for details. |

---

## 5. MongoDB Document Schema

### 5.1 UnifiedTierConfig (post-Rework #5)

```json
{
  "_id": "ObjectId",
  "tierUniqueId": "string (ex unifiedTierId — format: ut-<programId>-<seq>, e.g. ut-977-004). Immutable, survives versions.",
  "slabId": "int | null (ex metadata.sqlSlabId — = program_slabs.id after MC approval; null while new-tier is still DRAFT/PENDING_APPROVAL with no SQL row)",
  "orgId": "long",
  "programId": "int",
  "status": "DRAFT | PENDING_APPROVAL | SNAPSHOT | DELETED",
  "parentId": "int | null (parent tier's slabId — FK to program_slabs.id. Must reference a LIVE tier. A DRAFT cannot be a parent.)",
  "version": "int (auto-increment per tierUniqueId)",

  "_comment_hoisted_basicDetails": "Rework #5: basicDetails wrapper removed; fields at root",
  "name": "string",
  "description": "string",
  "color": "string (#hex)",
  "serialNumber": "int (auto-assigned, immutable — set on MC approval from SQL)",

  "_comment_dropped_basicDetails_validity": "Rework #5: basicDetails.startDate / basicDetails.endDate DROPPED (UI Duration column removed). The program-level validity.startDate/endDate still exists below.",

  "eligibility": {
    "kpiType": "string (PURCHASE, VISITS, POINTS, TRACKER, etc.)",
    "threshold": "number | null",
    "upgradeType": "string (IMMEDIATE, SCHEDULED, etc.)",
    "expressionRelation": "string | null (AND, OR)",
    "conditions": [
      {
        "type": "string (PURCHASE, VISITS, POINTS, TRACKER)",
        "value": "string",
        "trackerName": "string | null"
      }
    ]
  },

  "validity": {
    "_comment": "Program-level validity window — DIFFERENT semantic from the dropped basicDetails.startDate/endDate",
    "periodType": "string (FIXED, ROLLING, etc.)",
    "periodValue": "int | null",
    "startDate": "date | null",
    "endDate": "date | null",
    "renewal": {
      "criteriaType": "string (SAME_AS_ELIGIBILITY, CUSTOM, etc.)",
      "expressionRelation": "string | null (AND, OR)",
      "conditions": "[same model as eligibility.conditions]"
    }
  },

  "downgrade": {
    "target": "string (PREVIOUS, LOWEST, SPECIFIC, etc.)",
    "reevaluateOnReturn": "boolean",
    "dailyEnabled": "boolean",
    "conditions": "[same model as eligibility.conditions]"
  },

  "_comment_dropped_nudges": "Rework #5: `nudges` field DROPPED. Standalone Nudges entity (sibling) with its own endpoints is untouched.",
  "_comment_dropped_benefitIds": "Rework #5: `benefitIds` DROPPED. Tiers have no knowledge of benefits; Benefits epic owns the tier<->benefit link.",
  "_comment_dropped_schedule": "Rework #5: `renewal.schedule` DROPPED. Display-only text — engine's TierStrategyTransformer strips the `renewal` block when writing strategy JSON, so SQL LIVE side cannot reconstruct it; including it produced spurious diffs on every BOTH envelope.",

  "memberStats": {
    "_comment": "Populated by member-count cache cron. Not part of MC snapshot.",
    "memberCount": "int (cached)",
    "lastRefreshed": "date"
  },

  "engineConfig": {
    "_comment": "Hidden engine configs preserved for round-trip fidelity",
    "retainPoints": "boolean",
    "isDowngradeOnReturnEnabled": "boolean",
    "isDowngradeOnPartnerProgramExpiryEnabled": "boolean",
    "isAdvanceSetting": "boolean",
    "addDefaultCommunication": "boolean",
    "slabUpgradeMode": "string (EAGER | DYNAMIC | LAZY) -- program-level upgrade mode",
    "periodConfig": {
      "type": "FIXED | SLAB_UPGRADE | SLAB_UPGRADE_CYCLIC | FIXED_CUSTOMER_REGISTRATION",
      "value": "int",
      "unit": "NUM_MONTHS",
      "startDate": "date | null",
      "computationWindowStartValue": "int | null",
      "computationWindowEndValue": "int | null",
      "minimumDuration": "int"
    },
    "downgradeEngineConfig": {
      "_comment": "Engine-level downgrade settings not surfaced in UI downgradeConfig",
      "isActive": "boolean",
      "conditionAlways": "boolean",
      "conditionValues": {
        "purchase": "string",
        "numVisits": "string",
        "points": "string",
        "trackerCount": "[int]"
      },
      "renewalOrderString": "string"
    },
    "expressionRelation": "[[int]] | null",
    "customExpression": "string | null",
    "isFixedTypeWithoutYear": "boolean",
    "renewalWindowType": "string",
    "notificationConfig": {
      "_comment": "Per-channel notification config — in-tier notifications only. NOT the same as the standalone Nudges entity.",
      "sms": { "template": "string", "senderId": "string", "domain": "string" },
      "email": { "subject": "string", "body": "string", "templateId": "long", "senderId": "string" },
      "weChat": { "template": "string", "originalId": "string", "brandId": "string" },
      "mobilePush": { "androidBlob": "string", "iosBlob": "string", "accountId": "string" }
    }
  },

  "_comment_hoisted_metadata": "Rework #5: metadata wrapper removed. Fields hoisted to root (below). updatedViaNewUI DROPPED. createdBy NOT carried (not added to SQL either).",
  "createdAt": "date",
  "updatedBy": "string",
  "updatedAt": "date",
  "comments": "string | null (MC approval/rejection comment)",

  "meta": {
    "_comment": "Approval + drift-detection metadata. Distinct from the now-dropped `metadata` wrapper.",
    "basisSqlSnapshot": {
      "_comment": "Rework #5: Captured at DRAFT creation on an edit of a LIVE tier. Snapshot of SQL fields governed by MC. `null` for new-tier DRAFTs. Used by TierApprovalHandler.preApprove for drift detection.",
      "slabFields": {
        "name": "string",
        "description": "string",
        "colorCode": "string",
        "serialNumber": "int"
      },
      "strategyFields": {
        "upgradeThreshold": "string",
        "downgradeConfig": "object (serialized TierConfiguration slice for this slab)"
      },
      "capturedAt": "date"
    },
    "approvedAt": "date | null (set on MC approval — postApprove)",
    "approvedBy": "string | null (set on MC approval)"
  }
}
```

### 5.2 Status Lifecycle on UnifiedTierConfig (post-Rework #5)

Status lives on the entity itself (no separate `PendingChange` collection). Transitions:

- **Create new tier** (via new UI): insert with `status = DRAFT`, `slabId = null`, `basisSqlSnapshot = null`.
- **Edit LIVE tier** (via new UI): insert a new doc with `status = DRAFT`, `slabId = <existing program_slabs.id>`, `basisSqlSnapshot = <current SQL snapshot>`. The LIVE SQL row is unchanged.
- `transitionToPending()`: DRAFT → PENDING_APPROVAL (called by `MakerCheckerService.submitForApproval`).
- `transitionToRejected(comment)`: PENDING_APPROVAL → DRAFT, stores comment.
- **Approve** (via `MakerCheckerService.approve` → SAGA):
  1. `preApprove`: drift check (basisSqlSnapshot vs current SQL) + name re-check. Block on drift/collision.
  2. `publish`: Thrift → SQL write (updates existing row for edit; inserts for new tier, sets slabId). Sets `updatedBy`/`approvedBy`/`approvedAt` on SQL row.
  3. `postApprove`: **Rework #5**: Mongo doc transitions PENDING_APPROVAL → **SNAPSHOT** (audit-only). Sets `meta.approvedAt` / `meta.approvedBy`. The doc is NEVER read as LIVE state — it is purely audit.
  4. `onPublishFailure`: Mongo stays PENDING_APPROVAL (SAGA rollback on external failure); rethrow exception.
- **Delete DRAFT**: `status = DELETED`. Terminal. Only reachable from DRAFT.

**Note on ACTIVE status on Mongo docs (Rework #5 clarification):** The enum retains `ACTIVE` for backward compatibility, but the Mongo doc rarely holds this state. On approval, the doc goes directly PENDING_APPROVAL → SNAPSHOT. The `live` field in every API response envelope is derived from SQL via `SqlTierConverter` — not from a Mongo ACTIVE doc. If any Mongo doc does carry ACTIVE status (e.g. from legacy data paths), it is NOT read by the listing/detail endpoints; those endpoints only query `status IN [DRAFT, PENDING_APPROVAL]` in Mongo.

### 5.3 Indexes (Rework #5)

```
Index 1:  { orgId: 1, programId: 1, status: 1 }
          - Covers: list with status filter, approval queue, history view by status

Index 2:  { orgId: 1, programId: 1, slabId: 1 } PARTIAL UNIQUE
          partialFilterExpression: { status: { $in: ["DRAFT", "PENDING_APPROVAL"] } }
          - Covers: "does tier X have a pending change?" per-row lookup on list
          - Enforces: at most one DRAFT/PENDING_APPROVAL per (orgId, programId, slabId)
          - For new tiers with slabId=null: MongoDB treats null values as non-conflicting — multiple concurrent new-tier DRAFTs coexist (each gets its own slabId on MC approval)
```

Default `_id` index also used for direct approval/reject actions.

---

## 6. API Design

### 6.1 Tier CRUD (new UI — Rework #5)

| Method | Path | Purpose | Auth | MC Behavior |
|--------|------|---------|------|-------------|
| GET | `/v3/tiers?programId={id}&status={filter}&includeDeleted={bool}` | List tiers (envelope per tier: `{live, pendingDraft}`). Includes legacy SQL-origin tiers. | IntouchUser | Read-only — SQL for live + Mongo for pendingDraft |
| GET | `/v3/tiers/{slabId}` | Get single tier (envelope `{live, pendingDraft}`). `slabId` = `program_slabs.id`. | IntouchUser | Read-only |
| POST | `/v3/tiers` | Create tier via MC path (new-tier DRAFT). Name collision rejected at Layer 1. | IntouchUser | Creates as DRAFT (slabId=null). MC required. |
| PUT | `/v3/tiers/{slabId}` | Edit LIVE tier — creates a new Mongo DRAFT with `basisSqlSnapshot` captured. Blocked if another active DRAFT/PENDING exists for this slabId. | IntouchUser | Creates new DRAFT doc. MC required. |
| DELETE | `/v3/tiers/{tierDocId}` | Delete DRAFT tier (→ DELETED). No MC. 409 if not DRAFT. | IntouchUser | DRAFT only. |

### 6.2 Tier Approval

| Method | Path | Purpose | Auth | Body |
|--------|------|---------|------|------|
| POST | `/v3/tiers/{tierDocId}/submit` | Submit DRAFT → PENDING_APPROVAL | IntouchUser | `{}` |
| POST | `/v3/tiers/{tierDocId}/approve` | Approve: preApprove drift-check → publish Thrift → postApprove SNAPSHOT. Blocked on drift or name collision. | IntouchUser (approver) | `{ "comment": "..." }` |
| POST | `/v3/tiers/{tierDocId}/reject` | Reject: PENDING_APPROVAL → DRAFT, comment required | IntouchUser (approver) | `{ "comment": "Required reason" }` |
| GET | `/v3/tiers/approvals?programId={id}` | List pending approval tiers (org-wide or program-scoped) | IntouchUser | N/A |

### 6.3 Old UI — Legacy Endpoints (unchanged — Rework #5)

The old UI continues to use its existing (pre-Rework) tier create/edit/list endpoints. These:
- Write directly to SQL `program_slabs` + strategies via the existing Thrift methods.
- Never touch Mongo `unified_tier_configs`.
- Are never gated by MC.
- Set `updatedBy` on the SQL row; leave `approvedBy`/`approvedAt` NULL (Rework #5 audit columns).

The SQL `UNIQUE(program_id, name)` constraint is the final backstop for cross-UI name collisions.

### 6.4 Response Envelope

All responses use `ResponseWrapper<T>`:
```json
{
  "data": { ... },
  "errors": [ { "code": 123, "message": "..." } ],
  "warnings": [ { "message": "..." } ]
}
```

**GET tier response shape (Rework #5 — envelope):**
```json
{
  "data": {
    "live": {
      "slabId": 42,
      "name": "Gold",
      "description": "...",
      "serialNumber": 2,
      "status": "ACTIVE",
      "updatedBy": "alice",
      "approvedBy": "bob",
      "approvedAt": "2026-04-15T10:00:00Z",
      "...": "other fields from SQL via SqlTierConverter"
    },
    "pendingDraft": null
    /* OR, if a DRAFT/PENDING_APPROVAL exists for this slabId: */
    /*
    "pendingDraft": {
      "_id": "<mongoId>",
      "status": "PENDING_APPROVAL",
      "updatedBy": "alice",
      "updatedAt": "2026-04-16T14:00:00Z",
      "proposedChanges": { ... full UnifiedTierConfig minus audit internals ... },
      "meta": { "approvedAt": null, "approvedBy": null }
    }
    */
  }
}
```

**List GET response shape:** array of envelopes, one per LIVE SQL row.

### 6.5 Rework #6a Contract Hardening (added 2026-04-22)

The v3 tier write endpoints (`POST /v3/tiers`, `PUT /v3/tiers/{tierDocId}`) harden their accept/reject contract per the 5 Phase 4 decisions. The table below is the **authoritative error-code allocation** for 6a — the legacy 9001-9010 band continues to be emitted by Rework #4/#5 validators unchanged.

**Write-narrow / read-wide asymmetric contract (Q24)**: per-tier POST/PUT accepts only per-tier fields; any program-level field in the payload is rejected with a per-code 400. GET `/v3/tiers` continues to emit the full hoisted envelope (legacy + new) with no field rejections.

**Rework #6a reject matrix** (band 9011-9020):

| Code | REQ | Reject condition | Q-lock | Class |
|---|---|---|---|---|
| 9011 | REQ-33 | Class A program-level field on per-tier write: `reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled` | Q24 subsumes Q17; Q-OP-1 | Program-level |
| 9012 | REQ-34 | Class B program-level eligibility field on per-tier write: `kpiType`, `upgradeType`, `trackerId`, `trackerConditionId`, `additionalCriteria[]`, `expressionRelation` | Q24 subsumes Q18; Q-OP-1 | Program-level |
| 9013 | REQ-37 | `eligibilityCriteriaType` on per-tier POST/PUT — no longer required; program-level | Q24 subsumes Q25; Q-OP-1 | Program-level |
| 9014 | REQ-36 | `validity.startDate` on per-tier write when `periodType` is `SLAB_UPGRADE` family (event-driven; no fixed start date meaningful) | Q7; Q-OP-1 | Per-tier consistency |
| 9015 | REQ-35 | `-1` sentinel (string `"-1"`) in `eligibility.conditions[].value` or `renewal.conditions[].value` on per-tier write — GET filters them out, POST/PUT rejects symmetrically | Q9 (re-locked Phase 4 C-7 Hybrid); Q-OP-1 | Per-tier lockstep |
| 9016 | REQ-35 (extension) | Numeric `-1` in same fields — covers the C-10 numeric-vs-string gap (Designer confirms wire type; see C-10 open for Phase 7) | Q9; Q-OP-1 | Per-tier lockstep |
| 9017 | REQ-38 | `renewal.criteriaType` value other than `"Same as eligibility"`; `renewal.conditions[]` or `renewal.expressionRelation` non-empty | Q26 (B1a lock preserved); Q-OP-1 | Per-tier |
| **9018** | **REQ-56 (NEW)** | **FIXED-family `validity.periodType` (`FIXED`, `FIXED_CUSTOMER_REGISTRATION` — 2 values; `FIXED_LAST_UPGRADE` was phantom, corrected Phase 7 §6a.6) without `validity.periodValue` present + non-null + positive integer** | **Q-OP-2 scope lock + user-imposed conditional-duration caveat** | **Per-tier** |
| 9019-9020 | — | Reserved for Rework #6b or forward extensions | — | — |

**Unknown-field hard reject (Q11 + Q-OP-3, ADR-20R)**: any wire field not in the accepted contract (including the legacy `downgrade` block after Q3's `downgrade → renewal` rename) is rejected at Jackson deserialization time with `400 InvalidInputException`. The exact error-code assignment for Jackson-driven rejects is Designer's call (C-11 open) — if the config is absent from `intouch-api-v3`'s global `ObjectMapper`, an explicit scanning validator is required to enforce the same semantics.

**Read-side invariants preserved** (no change to §6.4 envelope):
- GET filters `-1` sentinels from `eligibility.conditions[].value` and `renewal.conditions[].value` (symmetric with write reject 9015).
- GET continues to hoist program-level fields (Class A + Class B) into the envelope from the joined strategy read — no field omission, no field rejection on reads.
- GET is **null-safe for legacy FIXED tiers with missing `periodValue`** — computed end-date is omitted rather than returned as null/0. Exact wire-shape decision deferred to Designer (Phase 7).

**Contradiction resolution mapping**:
- C-7 (phantom Q-locks) → Hybrid: Q9 re-locked on 9015; Q18/Q19/Q21 citations removed from BA.
- C-8 (validity asymmetry) → Option A: per-slab canonical (ADR-18R).
- C-9 (error code collision) → fully resolved by distinct 9011-9020 band (ADR-17R).
- C-12 (PeriodType coverage) → partial: scope locked, forward guard REQ-56 added (ADR-19R). Remaining non-SLAB_UPGRADE reads (3 enum values) stay pass-through.
- C-17 (external consumer audit) → partial: internal audit clean, external residual flagged to Phase 11 (ADR-21R note).
- Open for Designer: C-10 (numeric `-1` wire type), C-11 (Jackson config verification), C-13 (normalizer class existence), C-14 (list hoist shape), C-16 (Class A key-name drift).

---

## 7. TierApprovalHandler Design (Rework #5)

### 7.0 preApprove — Drift Check + Name Re-check (Rework #5)

```
TierApprovalHandler.preApprove(UnifiedTierConfig doc):

  1. Name collision re-check (Layer 2):
     - Load SQL program_slabs WHERE org_id=? AND program_id=? AND name=?
     - If a row exists with id != doc.slabId (or any row exists for new-tier drafts where slabId=null):
         throw ApprovalBlockedException(
           "Name '<X>' no longer available — conflicts with existing tier. Rename or cancel this DRAFT.")

  2. Drift check (ONLY for edits of LIVE tiers — doc.slabId != null):
     - currentSql = Thrift.getSlab(orgId, programId, slabId)    // single-slab read via getAllSlabs
     - basis     = doc.meta.basisSqlSnapshot
     - if basis == null:
         // new-tier DRAFT — no basis to check, proceed
         return
     - drifted = compareConservative(currentSql, basis)
         // conservative: any difference in slabFields or strategyFields counts as drift
     - if drifted:
         throw ApprovalBlockedException(
           "This DRAFT is based on a state that no longer matches the live tier.
            SQL changed since this DRAFT was created — <fieldDiff>.
            Cancel or recreate this DRAFT to proceed.")

  3. All checks pass — return. publish() will now proceed.
```

### 7.1 CREATE Flow (new tier — Rework #5 adjusted)

```
TierApprovalHandler.publish(UnifiedTierConfig doc):
  // Precondition: preApprove already ran — name unique, no drift (or basis == null for new tier).

  1. Fetch current strategies: getAllConfiguredStrategies(programId, orgId)

  2. Build SlabInfo:
     name, description, colorCode, serialNumber (= max(existing)+1),
     updatedBy = doc.updatedBy,
     approvedBy = reviewer userId (from MC context),
     approvedAt = now
     // NOTE: updatedViaNewUI field is DROPPED per Rework #5.

  3. Build SLAB_UPGRADE StrategyInfo (type 2):
     - Read current threshold_values CSV
     - Append new tier's threshold at end
     - Preserve current_value_type, expression_relation

  4. Build SLAB_DOWNGRADE StrategyInfo (type 5):
     - Parse current TierConfiguration JSON
     - Add new slab entry to slabs[] array
     - Set shouldDowngrade, downgradeTarget, periodConfig, conditions

  5. Call Thrift: createSlabAndUpdateStrategies(
       programId, orgId, slabInfo,
       [upgradeStrategy, downgradeStrategy],
       updatedBy, approvedBy, approvedAt, serverReqId)

     Execution order (verified from code):
     a. Updates SLAB_UPGRADE strategy (new threshold)
     b. Updates SLAB_DOWNGRADE strategy (new slab entry)
     c. Creates ProgramSlab record (with audit columns populated — Rework #5)
     d. updateStrategiesForNewSlab() auto-extends
        POINT_ALLOCATION + POINT_EXPIRY CSVs

  6. Return PublishResult with sqlSlabId (from Thrift response)

  // postApprove:
  // - doc.slabId = result.slabId
  // - doc.meta.approvedAt = now
  // - doc.meta.approvedBy = reviewer
  // - doc.status = SNAPSHOT  (Rework #5: no ACTIVE intermediate)
```

### 7.2 UPDATE Flow (edit of LIVE tier — Rework #5)

```
TierApprovalHandler.publish(UnifiedTierConfig draft):
  // Precondition: preApprove ran — drift check passed (basisSqlSnapshot matches current SQL).
  // draft.slabId points to the LIVE program_slabs.id. No parentId concept needed — SQL IS the parent.

  1. Use draft.slabId to identify the SQL row to update.

  2. Build SlabInfo with changes (name, description, color, serialNumber unchanged):
     - updatedBy = draft.updatedBy
     - approvedBy = reviewer userId
     - approvedAt = now

  3. If eligibility (upgrade threshold) changed:
     - Fetch SLAB_UPGRADE strategy
     - Replace threshold at CSV position (serialNumber - 2)
     - Build updated StrategyInfo

  4. If downgrade config changed:
     - Fetch SLAB_DOWNGRADE strategy (TierConfiguration JSON)
     - Find slab entry by slabNumber, update it
     - Build updated StrategyInfo

  5. Call createSlabAndUpdateStrategies with SlabInfo + modified strategies
     (The Thrift method handles both CREATE (new slab) and UPDATE (by slabId) in one atomic call.)

  6. Return PublishResult (slabId unchanged for edits)

  // postApprove (Rework #5):
  // - draft.meta.approvedAt = now
  // - draft.meta.approvedBy = reviewer
  // - draft.status = SNAPSHOT                         // The approved doc becomes audit-only
  // - Any prior SNAPSHOT for this slabId is NOT altered — they accumulate as history.
  // - The LIVE state is now the updated SQL row; it is read via SqlTierConverter on GETs.
```

**Note on versioning (Rework #5 simplification):** The earlier design had "old doc → SNAPSHOT, new doc → ACTIVE" per versioned edit. Post-Rework #5: there is no "ACTIVE Mongo doc" for LIVE state — SQL is always LIVE. The newly approved draft goes straight to SNAPSHOT as an audit record. Multiple SNAPSHOT docs accumulate per tier over time, each tagged with its `meta.approvedAt` / `meta.approvedBy`.

### 7.3 DELETE (DRAFT Only → DELETED) Flow

```
TierFacade.deleteTier(tierId):
  1. Load UnifiedTierConfig from MongoDB
  
  2. Guard: if status != DRAFT → 409 Conflict
     "Only DRAFT tiers can be deleted"
     (ACTIVE/PENDING_APPROVAL → 409 "Tier retirement not supported in this version")
  
  3. Set status to DELETED in MongoDB doc
     (soft-delete — document stays for audit trail)
  
  4. No Thrift call needed — DRAFT tiers have no SQL record
  
  5. No member reassessment — DRAFT tiers have no members
  
  NOTE: This does NOT go through TierApprovalHandler or MC.
  DRAFT deletion is a simple MongoDB status update.
  Tier retirement (stopping ACTIVE tiers) is deferred to a future epic.
```

### 7.4 MakerCheckerService SAGA Pattern (Approval — Rework #5)

```
MakerCheckerService<T>.approve(tierConfig, comment, reviewedBy, handler, save):
  1. Call handler.preApprove(tierConfig)
     — Rework #5: drift check (basisSqlSnapshot vs current SQL) + name re-check.
     — Throws ApprovalBlockedException on drift OR name collision.
     — Approver sees a clear user-facing message. Mongo doc stays PENDING_APPROVAL.

  2. Call handler.publish(tierConfig) — THRIFT CALL (external, may fail)
     Returns PublishResult

  3. On success: Call handler.postApprove(tierConfig, result)
     - Rework #5: status = SNAPSHOT (audit-only). No ACTIVE intermediate.
     - Set meta.approvedAt, meta.approvedBy.
     - For new-tier creates: set slabId = result.slabId.
     - Call save callback (tierRepository.save)

  4. On failure (Thrift exception, SQL UNIQUE violation, etc.):
     - Call handler.onPublishFailure(tierConfig, exception)
     - Rethrow exception (SAGA rollback)
     - tierConfig stays PENDING_APPROVAL in MongoDB
     - Approver sees error — SQL UNIQUE(program_id, name) collision is translated into a well-formed 409
```

### 7.5 Phase 2AB — Complete Atomic Publish Flow (Rework #5 follow-up, 2026-04-20)

**Problem closed**: §7.1 / §7.2 originally described `publish()` as "fetch current strategies, build new StrategyInfos, call `createSlabAndUpdateStrategies`." In code this was implemented as **two** engine round-trips — first `createOrUpdateSlab` to persist the slab row, then a separate strategy update — which left a split-brain window: if the second call failed, the `program_slabs` row existed without its corresponding SLAB_UPGRADE threshold / SLAB_DOWNGRADE entry, and engine reads would return an inconsistent tier.

Phase 2AB closes the hole. `publish()` now performs a **read-modify-write** on the two program-level strategies in memory, then submits `slabInfo + [SLAB_UPGRADE, SLAB_DOWNGRADE]` in a **single** `createSlabAndUpdateStrategies` Thrift transaction. No intermediate state is ever persisted.

**Commits**: `2a616290f` (Thrift wrapper added to intouch-api-v3) · `d5c226c6a` (transformer helpers `applySlabUpgradeDeltaJson` + `findStrategyByType`) · `59b4ae423` (handler rewrite to atomic flow). Evidence: 198/198 intouch-api-v3 tests GREEN under Java 17.

#### 7.5.1 End-to-End Sequence

```mermaid
sequenceDiagram
    autonumber
    participant UI as Garuda UI (approver)
    participant RC as TierReviewController
    participant F  as TierFacade
    participant MC as MakerCheckerService
    participant H  as TierApprovalHandler
    participant T  as PointsEngineRulesThriftService
    participant E  as emf-parent PointsEngineRuleService
    participant DB as MySQL (program_slabs + strategies)

    UI->>RC: POST /v3/tiers/{tierId}/approve
    RC->>F:  approve(tierId, reviewer, comment)
    F->>MC: approve(doc, comment, reviewer, handler, save)

    Note over MC,H: Phase 1 — preApprove (drift + name re-check)
    MC->>H:  preApprove(doc)
    H->>T:   getSlab(orgId, programId, slabId) [only for LIVE edits]
    T-->>H:  current SQL snapshot
    H->>H:   compareConservative(currentSql, doc.meta.basisSqlSnapshot)
    alt drift OR name collision
        H-->>MC: throw ApprovalBlockedException
        MC-->>UI: 409 (clear message, doc stays PENDING_APPROVAL)
    end

    Note over MC,H: Phase 2 — publish (ATOMIC read-modify-write)
    MC->>H:  publish(doc)
    H->>H:   buildSlabInfo(doc)
    H->>H:   resolveSlabIdAndDiscriminate(doc, slabInfo) → isCreate?
    H->>T:   getAllConfiguredStrategies(programId, orgId)
    T->>E:   Thrift getAllConfiguredStrategies
    E->>DB:  SELECT * FROM strategies WHERE program_id=? AND org_id=?
    DB-->>E: rows
    E-->>T:  List&lt;StrategyInfo&gt;
    T-->>H:  List&lt;StrategyInfo&gt;
    H->>H:   findStrategyByType(SLAB_UPGRADE) + findStrategyByType(SLAB_DOWNGRADE)<br/>[throws IllegalStateException if either missing or duplicated]
    H->>H:   upgradeCopy = upgrade.deepCopy(); downgradeCopy = downgrade.deepCopy()
    H->>H:   applyUpgradeDelta(doc, upgradeCopy, slabNumber, isCreate)<br/>[skip for slab 1; CREATE non-first requires eligibility.threshold]
    H->>H:   applyDowngradeDelta(doc, downgradeCopy, slabNumber, isCreate)<br/>[null-safe; mutates TierConfiguration.slabs[] keyed by slabNumber]
    H->>T:   createSlabAndUpdateStrategies(slabInfo,<br/>[upgradeCopy, downgradeCopy], programId, orgId, userId, now)
    T->>E:   Thrift createSlabAndUpdateStrategies (single call)
    Note over E,DB: ─── Single engine transaction ───
    E->>DB:  UPDATE strategies SET property_values=? WHERE id=upgrade.id
    E->>DB:  UPDATE strategies SET property_values=? WHERE id=downgrade.id
    E->>DB:  INSERT/UPDATE program_slabs (id = slabInfo.id or new)
    E->>DB:  updateStrategiesForNewSlab()<br/>[auto-extends POINT_ALLOCATION, POINT_EXPIRY CSVs]
    DB-->>E: commit
    E-->>T:  SlabInfo (with id)
    T-->>H:  SlabInfo
    H-->>MC: PublishResult(externalId=slabId, source="program_slabs")

    Note over MC,H: Phase 3 — postApprove (Mongo audit)
    MC->>H:  postApprove(doc, publishResult)
    H->>H:   doc.slabId = publishResult.externalId<br/>doc.meta.approvedAt = now<br/>doc.meta.approvedBy = reviewer<br/>doc.meta.basisSqlSnapshot = null<br/>doc.status = SNAPSHOT
    H-->>MC: (void)
    MC->>MC: save(doc)
    MC-->>F:  ApprovalResult
    F-->>RC:  200 OK
    RC-->>UI: 200 (envelope: live=freshly committed SQL, pendingDraft=null)

    Note over MC: On any Thrift failure → onPublishFailure → doc stays PENDING_APPROVAL (SAGA)
```

#### 7.5.2 CREATE vs UPDATE Discriminator

`resolveSlabIdAndDiscriminate(doc, slabInfo)` decides whether the atomic Thrift call targets a new or existing `program_slabs.id`:

```mermaid
flowchart TD
    A[doc arrives at publish] --> B{doc.slabId != null?}
    B -- yes --> U1[UPDATE: slabInfo.id = doc.slabId<br/>isCreate = false]
    B -- no --> C{doc.parentId != null?}
    C -- no --> CR1[CREATE: slabInfo.id = null<br/>isCreate = true<br/>engine auto-assigns id]
    C -- yes --> D[Thrift: resolve parent slabId<br/>from parent tierUniqueId]
    D -- resolves --> U2[UPDATE: slabInfo.id = parent.slabId<br/>isCreate = false]
    D -- not found --> CR2[CREATE: treat as new<br/>isCreate = true]

    U1 --> E[Proceed to delta-apply on strategies]
    U2 --> E
    CR1 --> F{slabNumber == 1?}
    CR2 --> F
    F -- yes --> G[applyUpgradeDelta: SKIP<br/>CSV semantics: N slabs → N-1 thresholds<br/>slab 1 has no inbound threshold]
    F -- no --> H{eligibility.threshold present?}
    H -- no --> I[throw IllegalStateException<br/>CREATE non-first slab requires threshold]
    H -- yes --> J[applyUpgradeDelta: APPEND threshold<br/>isAppend=true]
    E --> K[applyUpgradeDelta: REPLACE CSV position<br/>slabIndex = serialNumber - 2<br/>null-safe: skip if threshold unchanged]
    G --> L[applyDowngradeDelta — null-safe,<br/>find slab by slabNumber, update fields]
    I --> X[Reject — 400/409]
    J --> L
    K --> L
    L --> M[createSlabAndUpdateStrategies<br/>— single atomic Thrift —]
```

#### 7.5.3 Invariants Preserved by the Atomic Call

| Invariant | Before Phase 2AB | After Phase 2AB |
|---|---|---|
| `program_slabs` row present ⟺ SLAB_UPGRADE CSV entry present at position `serialNumber-2` | **Violated** on second-call failure | Always holds — engine commits all in one tx |
| `program_slabs` row present ⟺ SLAB_DOWNGRADE JSON has entry for `slabNumber` | **Violated** on second-call failure | Always holds |
| Strategy `id` preserved across updates | Held | Held (deep-copy retains id; engine updates by id) |
| Non-owned program-level keys preserved (`current_value_type`, `expression_relation`, reminders, comms) | Held | Held (read-modify-write on original JSON; no replacement) |
| Only one SLAB_UPGRADE / SLAB_DOWNGRADE per program | Held by query contract | Enforced by `findStrategyByType` — throws on duplicate |
| Missing program-level strategy is visible | Silent success on first call | `IllegalStateException` with clear message before any write |

#### 7.5.4 Design Decisions Q-P1…Q-P7 (Resolved in Phase 2AB)

| # | Question | Decision |
|---|---|---|
| Q-P1 | Should `publish()` write slab first or strategies first? | Neither — pass all three into one atomic call (`createSlabAndUpdateStrategies`). |
| Q-P2 | Should `findStrategyByType` tolerate duplicates (pick first)? | No — throw `IllegalStateException`. Duplicate program-level strategies are data corruption and must surface. |
| Q-P3 | Deep-copy `StrategyInfo` before mutating? | Yes — defensive. Thrift clients MAY cache. Mutation of a cached object would contaminate subsequent reads. |
| Q-P4a | UPDATE of non-first slab where `eligibility.threshold` was not changed — is it legal? | Yes — null-safe. `applyUpgradeDelta` treats `null` threshold as "no change" and leaves CSV position untouched. |
| Q-P4b | CREATE of non-first slab without `eligibility.threshold` — legal? | No — throw. CSV semantics require a threshold value; slab cannot be inserted into the upgrade chain without it. |
| Q-P5 | When slab is `serialNumber=1`, what happens to upgrade delta? | Skip entirely. CSV has N-1 entries for N slabs; slab 1 has no inbound threshold. |
| Q-P6 | Should downgrade delta be null-safe like upgrade? | Yes — if `downgrade` config absent in doc, leave TierConfiguration.slabs entry as-is on UPDATE (don't wipe it). |
| Q-P7 | How is `userId` sourced for audit columns? | Parsed from `doc.meta.approvedBy` (MC reviewer). Fallback to `doc.updatedBy`. Hard-coded `0` placeholder pending #Q-P7 user-id resolver — tracked as TODO. |

---

## 8. Status State Machine (Rework #5)

The state machine below describes Mongo `UnifiedTierConfig.status`. **Note that LIVE state is not a Mongo status — LIVE tier state lives in SQL `program_slabs` and is derived on read via `SqlTierConverter`. The Mongo `status` enum is for draft lifecycle and audit.**

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Create (new UI, new tier)<br/>slabId=null<br/>basisSqlSnapshot=null
    [*] --> DRAFT : Edit (new UI, existing LIVE tier)<br/>slabId=<SQL id><br/>basisSqlSnapshot=<SQL snapshot>
    DRAFT --> PENDING_APPROVAL : Submit
    DRAFT --> DELETED : Delete (immediate)
    PENDING_APPROVAL --> SNAPSHOT : Approve<br/>(preApprove drift-check + name re-check pass<br/>→ Thrift publish → SQL updated/inserted<br/>→ meta.approvedAt/By set)
    PENDING_APPROVAL --> DRAFT : Reject (comment required)
    PENDING_APPROVAL --> PENDING_APPROVAL : Approve BLOCKED (drift or name collision)
    DELETED --> [*] : Terminal (audit trail preserved)
    SNAPSHOT --> [*] : Terminal (audit record, never reconciled)

    note right of SNAPSHOT : Write-once-at-approval.<br/>NOT reconciled with later legacy edits.<br/>History view surfaces drift caveat.
    note left of DRAFT : Single active DRAFT/PENDING per slabId<br/>enforced by app check + Mongo partial unique index.<br/>For new tiers (slabId=null), multiple co-exist.
    note right of DELETED : Only reachable from DRAFT.<br/>No PAUSED or STOPPED states.
```

**Legacy (old UI) write path is NOT shown** in this state machine because it does not interact with Mongo — it writes directly to SQL `program_slabs` with `updatedBy` set, leaving the Mongo doc (if any) undisturbed. Rework #5 explicitly supports this: when old UI edits a tier that has a pending new-UI DRAFT, the SQL UPDATE succeeds and the drift is caught by `preApprove` when the approver tries to approve.

---

## 9. Architecture Decision Records (ADRs)

### ADR-01: Dual-Storage (MongoDB + SQL)
**Decision**: Tier configurations stored in MongoDB during draft lifecycle, synced to SQL on approval.
**Context**: The existing engine (emf-parent, peb) reads from SQL. The new UI/API needs draft/approval workflows.
**Alternatives**: (a) SQL-only with draft table (tight coupling), (b) MongoDB-only (breaks engine), (c) CQRS with event sourcing (over-engineering).
**Rationale**: Follows UnifiedPromotion pattern. MongoDB provides flexible document storage for rich config. SQL provides the stable, indexed storage the engine needs. Sync is explicit via Thrift on approval.
**Per**: Decision D-10, verified against UnifiedPromotion.java.

### ADR-02: Generic Maker-Checker Framework (Baljeet's makechecker/ Package)
**Decision**: Use Baljeet's pre-existing generic `makechecker/` package (ApprovableEntity + ApprovableEntityHandler). TierApprovalHandler implements the handler interface.
**Context**: Tiers need approval workflow. Benefits, subscriptions will need it later. Baljeet built the reusable framework.
**Alternatives**: (a) Tier-specific MC (faster, inconsistent), (b) Copy UnifiedPromotion MC pattern (outdated).
**Rationale**: Baljeet's package is battle-tested and extensible. No PendingChange collection — status lives on the entity itself. SAGA pattern in MakerCheckerService.approve() handles Thrift publish failures gracefully.
**Per**: Decision D-12, team coordination with Baljeet on makechecker/ ownership.

### ~~ADR-03: Expand-Then-Contract Migration~~ — NOT NEEDED (Rework #3)
~~**Decision**: Add `status` column to `program_slabs` with DEFAULT 'ACTIVE'. Add new `findActiveByProgram()` DAO method. Do NOT modify existing `findByProgram()`.~~
~~**Context**: PeProgramSlabDao used in 7+ services. Modifying existing queries risks regression in core engine.~~
~~**Alternatives**: (a) Modify all existing queries (high blast radius), (b) Database view (added complexity).~~
~~**Rationale**: Zero regression risk. Existing engine callers see all slabs (correct for serial number ordering). New APIs use the filtered method. Per GUARDRAILS G-05.4.~~
~~**Per**: Decision D-18, Critic C-3.~~
**Rework #3**: ADR-03 removed from scope. SQL `program_slabs` only contains ACTIVE tiers (synced via Thrift on approval). No ACTIVE tier can be deleted (DRAFT-only deletion in MongoDB). SlabInfo Thrift has no status field. Therefore: no status column, no findActiveByProgram(), no Flyway migration, zero emf-parent entity/DAO changes. Deferred to future tier retirement epic.

### ADR-04: Versioned Edits with parentId
**Decision**: Editing an ACTIVE tier creates a new DRAFT document with parentId pointing to the ACTIVE. ACTIVE stays live until new version approved.
**Context**: Tier config changes are high-risk. Need rollback capability and zero-downtime editing.
**Alternatives**: (a) In-place edit with MC (no rollback), (b) Immediate snapshot (downtime gap during approval).
**Rationale**: Zero downtime. Full version history. Consistent with UnifiedPromotion pattern.
**Per**: Decision D-13, D-24 (Flow A confirmed).

### ADR-05: Existing Thrift Methods (No IDL Change)
**Decision**: Use existing `createSlabAndUpdateStrategies`, `getAllSlabs`, `createOrUpdateSlab` from `pointsengine_rules.thrift`. TierApprovalHandler calls these via `PointsEngineRulesThriftService` wrappers.
**Context**: Phase 2 Critic flagged missing Thrift methods (C-1). Phase 5 research found they already exist in a different Thrift file.
**Alternatives**: (a) New Thrift method (unnecessary), (b) Direct DB access (breaks service boundary), (c) REST endpoint on emf-parent (inconsistent).
**Rationale**: Methods exist. Only need Java wrappers in PointsEngineRulesThriftService. Lowest scope, lowest risk.
**Per**: Phase 5 critical finding, revised C-1. TierApprovalHandler.publish() invokes these via wrappers.

### ~~ADR-06: New Programs Only~~ — REVERSED (Rework #5)
~~**Decision**: The new tier CRUD system (MongoDB draft -> SQL live) applies to new programs only. Existing programs continue using the current system.~~

**Rework #5 reversal (ADR-06R):** The new `/v3/tiers` APIs serve **ALL tiers** — both legacy SQL-origin tiers and new-UI-origin tiers, across all programs (old and new).

**Mechanism**:
- Legacy tiers surface through a **read-only SQL→DTO converter** (`SqlTierConverter`) on GETs. No backfill, no bootstrap migration into Mongo.
- Writes follow the **dual-path rule** (see ADR-08R): old UI → legacy direct-SQL (no MC), new UI → Mongo DRAFT → MC → Thrift → SQL.
- Both UIs see both types of tiers on reads. Both UIs can edit tiers of either origin.

**Rationale**: Single UI experience. No backfill migration risk (reads are stateless). Preserves backward compatibility with all legacy data.

**Per**: Rework #5 KD-09 (user decision, 2026-04-17). Replaces D-23.

### ADR-08R: Dual Write Paths, Single MC Scope (Rework #5 — NEW)
**Decision**: Maker-checker applies **if-and-only-if** the write originated from the **new UI**. The legacy direct-SQL write path (old UI) continues to exist and is never gated by MC.

**Write-path matrix:**
| Write Origin | Target Tier | Write Path | MC? | Mongo? |
|---|---|---|---|---|
| Old UI | Legacy SQL-only | Legacy direct-SQL | No | No |
| Old UI | New-UI-origin (has SNAPSHOT history) | Legacy direct-SQL | No | No (SNAPSHOT not reconciled) |
| New UI | Legacy SQL-only | Mongo DRAFT (basis from SQL) → MC → Thrift → SQL | Yes | Yes |
| New UI | New-UI-origin | Mongo DRAFT → MC → Thrift → SQL | Yes | Yes |

**Context**: Legacy endpoints have existed for years; migrating all callers to the new MC-gated path is out of scope and high-risk.

**Alternatives**: (a) Force MC on all writes (breaks legacy clients), (b) Retire legacy endpoints (out of scope for this pipeline), (c) Mirror legacy writes into Mongo (complex, error-prone, no clear value).

**Rationale**: MC is a new-UI feature. Legacy path preserved untouched.

**Per**: Rework #5 KD-10.

### ADR-09R: Envelope Response Shape (Rework #5 — NEW)
**Decision**: `/v3/tiers` GETs return `{ live: ..., pendingDraft: ... | null }` per tier. `live` always sourced from SQL; `pendingDraft` from Mongo filtered by `status IN [DRAFT, PENDING_APPROVAL]`.

**Alternatives**: (a) Separate endpoints for live vs pending (more round-trips, more client logic), (b) Return only `live` with a `hasPendingDraft` flag (extra round-trip to fetch draft details).

**Rationale**: Single round-trip for approval review (highest-value screen). Bounded scale (~50 tiers/program, ≤1 active DRAFT per tier) keeps payload small. Two DB hits per list page, no N+1.

**Per**: Rework #5 KD-11.

### ADR-10R: Drift Detection Before Approval (Rework #5 — NEW)
**Decision**: Every Mongo DRAFT captures `meta.basisSqlSnapshot` at creation. `TierApprovalHandler.preApprove` re-reads current SQL state and compares against the basis; any drift blocks approval with a clear user-facing message.

**Drift policy**: Conservative — any difference in SQL slab or strategy fields counts as drift. Revisit if operational friction emerges.

**Alternatives**: (a) Silent overwrite (data loss risk when old UI edits mid-MC), (b) Auto-rebase on current SQL (surprising UX, can change what approver is approving), (c) Merge diff (complex, error-prone).

**Rationale**: Makes MC a meaningful gate even when concurrent legacy writes exist. "Cancel or recreate" is explicit and auditable.

**Per**: Rework #5 KD-12.

### ADR-11R: SNAPSHOT Audit-Only Semantics (Rework #5 — NEW)
**Decision**: Mongo SNAPSHOT docs are write-once-at-approval audit records. They carry `meta.approvedAt` and `meta.approvedBy`. They are NEVER reconciled with later legacy edits. The new-UI history view surfaces a caveat when SQL `updated_at` > latest SNAPSHOT's `approvedAt`.

**Alternatives**: (a) Keep SNAPSHOT in sync with SQL (requires listening to legacy writes — high complexity, cross-cutting concern), (b) Reconcile on read (read-time inconsistency, complex algorithm), (c) Auto-invalidate SNAPSHOTs on legacy edit (loses audit trail).

**Rationale**: SNAPSHOT is an audit record of "what was approved", not a mirror of current state. Current state lives in SQL. UI reconciles visually via a label. Cheap to implement, clear to reason about.

**Per**: Rework #5 KD-13.

### ADR-12R: Single Active DRAFT per Tier (Rework #5 — NEW)
**Decision**: At most one DRAFT or PENDING_APPROVAL document exists per `(orgId, programId, slabId)`. Enforced by:
1. App-level pre-check in `TierFacade.createDraft` / `editDraft` — returns friendly business error on collision.
2. Mongo partial unique index on `(orgId, programId, slabId)` where `status IN [DRAFT, PENDING_APPROVAL]` — catches races.

For new-tier DRAFTs (`slabId=null`), MongoDB's unique index treats null as non-conflicting — multiple concurrent new-tier DRAFTs coexist, each getting its own `slabId` on MC approval.

**Rationale**: Prevents concurrent conflicting DRAFTs. App check provides good UX; DB index is the race-safe backstop. Reuses the Q-3c Index 2 fields.

**Per**: Rework #5 KD-14.

### ADR-13R: Name Collision Defense — 3 Layers (Rework #5 — NEW)
**Decision**: Name uniqueness is defended in three layers:
1. **At DRAFT creation** (`TierValidationService`): check against `(SQL program_slabs for program)` ∪ `(active Mongo DRAFTs for program)`. Reject early.
2. **At approval time** (`TierApprovalHandler.preApprove`): re-check against current SQL. Block with user-facing message if a collision appeared (e.g., via old UI legacy create).
3. **SQL UNIQUE(program_id, name)** on `program_slabs`: final backstop. If Thrift INSERT still fails, SAGA rolls back and surfaces a well-formed error.

**Alternatives**: (a) App-only check (race-unsafe), (b) DB-only check (bad UX — user sees cryptic constraint violation).

**Rationale**: Good UX + race-safety. Mutually reinforcing defenses.

**Per**: Rework #5 KD-15.

### ADR-14R: SQL program_slabs Audit Columns (Rework #5 — NEW)
**Decision**: `program_slabs` gains three columns via Flyway: `updatedBy`, `approvedBy`, `approvedAt`. `createdBy` is explicitly NOT added (per user instruction).

- Legacy write path sets only `updatedBy` (leaves `approvedBy`/`approvedAt` as-is → NULL for rows never touched by MC).
- MC push path sets all three.

**Alternatives**: (a) Add all 4 (createdBy, updatedBy, approvedBy, approvedAt) — rejected per user, (b) Add only updatedBy (loses approval audit), (c) No audit columns (loses traceability entirely).

**Rationale**: Minimal audit enrichment; backward-compatible (all nullable); supports both legacy and MC flows without forcing legacy backfill.

**Per**: Rework #5 KD-18 (explicit user decision).

### ADR-15R: Schema Cleanup + Renames (Rework #5 — NEW)
**Decision**: 
- Hoist `basicDetails` + `metadata` fields to root of `UnifiedTierConfig` (remove both wrappers).
- Drop `nudges`, `benefitIds`, `updatedViaNewUI`, `basicDetails.startDate`, `basicDetails.endDate`.
- Rename `unifiedTierId` → `tierUniqueId` (pure rename; same format).
- Rename `metadata.sqlSlabId` → root-level `slabId`.

**Rationale**: Reduce schema noise; align with UI intent. Tiers have no knowledge of benefits (Benefits epic owns link). Nudges is a sibling entity. Shorter, clearer names.

**Per**: Rework #5 KD-16 + KD-17.

### ADR-16R: parentId = SQL slabId, Must Be LIVE (Rework #5 — NEW)
**Decision**: `UnifiedTierConfig.parentId` references the parent tier's `program_slabs.id` (not a Mongo doc id). The parent MUST be LIVE — a DRAFT tier cannot be a parent.

**Validation**: Enforced at DRAFT creation/edit in `TierValidationService`:
- Parent row must exist in `program_slabs` with same `orgId`/`programId`.
- Self-reference rejected.
- Cycle prevention flagged for LLD (Designer's call whether to enforce strictly).

**Alternatives**: (a) parentId = Mongo doc id (cross-store correlation, doesn't work for legacy parents), (b) parentId = tierUniqueId (string FK, indirection).

**Rationale**: Works uniformly for legacy and new-UI-origin parents. No cross-store correlation. Parent data reads straight from SQL.

**Per**: Rework #5 KD-19 / Q-6.

### ADR-07: TierApprovalHandler — Single Atomic Thrift Call with In-Handler Read-Modify-Write (Phase 2AB — rewritten 2026-04-20)

**Decision**: `TierApprovalHandler.publish()` executes the entire SQL-side mutation in a **single atomic `createSlabAndUpdateStrategies` Thrift call**. The handler performs a read-modify-write on SLAB_UPGRADE + SLAB_DOWNGRADE program-level strategies **in memory** (fetch → deep-copy → apply delta) and submits `slabInfo + [upgradeCopy, downgradeCopy]` together. Points strategies (allocation, redemption, expiry) are NOT passed — the engine's `updateStrategiesForNewSlab()` auto-extends them inside the same transaction. See §7.5 for the end-to-end sequence.

**Context**: The prior implementation split this into two engine round-trips (`createOrUpdateSlab` first, then a separate strategy update). On any failure of the second call, the `program_slabs` row existed without the corresponding SLAB_UPGRADE CSV entry or SLAB_DOWNGRADE JSON entry — engine reads would return an inconsistent tier (split-brain). No SAGA compensation was safe because the engine already exposed the half-written slab to live reads.

**Alternatives considered**:
- **(a) Multiple separate Thrift calls with compensating deletes**: Rejected. The compensating delete itself can fail; leaves a window where concurrent reads see the bad state.
- **(b) Distributed transaction across Thrift calls**: Rejected. Thrift does not support cross-call transactions; would require 2PC between intouch-api-v3 and emf-parent.
- **(c) Push all logic to engine side (pass doc; engine derives strategies)**: Rejected. Would leak UnifiedTierConfig Mongo schema into the engine's IDL and entangle the engine with MC concerns.
- **(d) Pass raw strategies unchanged and let engine diff**: Rejected. Engine has no knowledge of which `slabNumber` this submission targets; the CSV index / JSON-key math is the handler's responsibility.

**Rationale**: The engine's `createSlabAndUpdateStrategies` already commits slab row + passed strategies + CSV auto-extension in one transaction. By doing the CSV/JSON delta in the handler (with deep-copy + null-safe + duplicate-strategy detection via `findStrategyByType`) and submitting the finished strategies into that single call, the split-brain window is closed entirely. `deepCopy` is defensive (Thrift clients may cache). `IllegalStateException` on missing/duplicate program-level strategies surfaces data corruption before any write.

**Verified execution order inside the engine transaction**:
1. `UPDATE strategies SET property_values = ? WHERE id = upgrade.id`
2. `UPDATE strategies SET property_values = ? WHERE id = downgrade.id`
3. `INSERT` / `UPDATE program_slabs` (id = `slabInfo.id` if set, else auto-assigned)
4. `updateStrategiesForNewSlab()` auto-extends POINT_ALLOCATION + POINT_EXPIRY CSVs
5. `COMMIT` — all-or-nothing

**Evidence**: Phase 2AB commits `2a616290f` (Thrift wrapper in `PointsEngineRulesThriftService`), `d5c226c6a` (transformer helpers `applySlabUpgradeDeltaJson` + public `findStrategyByType`), `59b4ae423` (handler `publish()` rewrite + extracted helpers `resolveSlabIdAndDiscriminate`, `applyUpgradeDelta`, `applyDowngradeDelta`). 198/198 tests GREEN in intouch-api-v3 under Java 17.

**Per**: Phase 5 deep dive (original atomic-call choice), Phase 2AB rewrite (handler-side read-modify-write pattern — 2026-04-20).

---

### ADR-17R: Distinct Error-Code Band 9011-9020 for Rework #6a Rejects (Rework #6a — NEW, 2026-04-22)

**Decision**: Every Rework #6a reject on `POST /v3/tiers` / `PUT /v3/tiers/{tierDocId}` emits a **distinct error code in the 9011-9020 band**. The legacy 9001-9010 band (Rework #4/#5 validators) is **frozen** — no codes re-used, no codes removed. See §6.5 for the per-code allocation table.

**Context**: The BA originally defined 7 new rejects (REQ-33..REQ-38, REQ-40) sharing the 9001-9010 range with pre-existing Rework #4 validator codes. `TierCreateRequestValidator.java` and `TierUpdateRequestValidator.java` javadoc both state range 9001-9010 is shared. Reusing codes for semantically distinct rejects creates diagnostic ambiguity for any error-code-consuming client (UI toast, downstream integrators, logs); collisions between the legacy 9004 ("name taken") and a new 9004-coded reject (e.g., "Class A field present") would be a silent contract break.

**Alternatives considered**:
- **(a) Reuse 9001-9010 with overload**: Rejected. Same code meaning two different things based on request shape — clients cannot localize or branch safely.
- **(b) Extend by one decade (9011-9020)**: Adopted. Preserves per-reject diagnostic clarity, leaves slots for Rework #6b and future rejects, no client-side parser changes needed.
- **(c) Move to 9100+ for a clean band**: Rejected. Unnecessary distance from the nearby legacy band; harder to pattern-match in logs.

**Rationale**: Nine new codes (9011-9018 allocated, 9019-9020 reserved) cover every 6a reject with unique semantics. Legacy clients continue to receive unchanged codes for unchanged rejects; new clients receive unambiguous codes for new rejects. No Flyway, no Thrift IDL change — purely a constants update in intouch-api-v3.

**Per**: Phase 4 Q-OP-1 Option (b), 2026-04-22. Resolves contradictions.md C-9.

---

### ADR-18R: Per-Slab Canonical for `validity.periodType` / `validity.periodValue` (Rework #6a — NEW, 2026-04-22)

**Decision**: `validity.periodType` and `validity.periodValue` are **canonical in per-slab engine storage** — specifically `TierDowngradeSlabConfig[]` indexed by `slabNumber`, field `periodConfig` (with `periodType` and `periodValue` sub-fields). Per-tier POST/PUT accepts these fields, writes them per-slab. Program-level `SlabUpgradeStrategy.propertyValues` carries only the 4 Class A booleans (`reevaluateOnReturn`, `dailyEnabled`, `retainPoints`, `isDowngradeOnPartnerProgramDeLinkingEnabled`) — **no validity data**.

**Context**: Q20 (engine storage classification) classified `validity.*` as program-level by omission — the BA list of program-level fields did not include `validity.*`, which was then exploited in REQ-26 as evidence the fields were per-tier. This created a silent asymmetry: REQ-20/26 treated them as per-tier while REQ-34's Class B reject list also called out eligibility fields but left `validity.*` unspecified. The Critic flagged this as C-8 BLOCKER.

**Alternatives considered (Phase 4)**:
- **(A) Per-slab canonical — adopted**: The engine already stores per-tier duration in `TierDowngradeSlabConfig[]` (verified in `pointsengine-emf` + engine-transformer code paths). Program-level `propertyValues` has no slot for `periodType`/`periodValue`. Writing them per-slab matches the storage that already exists.
- **(B) Program-level canonical**: Rejected — would require a schema migration (add `periodType`/`periodValue` to `SlabUpgradeStrategy.propertyValues`), re-evaluate Q20's classification, and contradict REQ-20/26 which have been on the wire since Rework #5.
- **(C) Dual-write to both storages with one marked as source of truth**: Rejected — introduces drift risk and a reconciliation code path nobody needs.

**Rationale**: Option A closes C-8 with zero schema migration, zero engine code change, and zero change to the wire contract. REQ-34's Class B list is narrowed in 6a to exclude `validity.*` (which was never meant to be there — the BA list was incomplete, not wrong). Designer's LLD (Phase 7) captures the exact `TierDowngradeSlabConfig` field access pattern; Developer (Phase 10) adds no new fields, only reads/writes existing ones.

**Evidence**: `TierDowngradeSlabConfig.java` (per-slab config entity with `periodConfig` sub-object), `SlabUpgradeStrategy.propertyValues` Map inspection (4 booleans only), `TierDowngradeStrategyConfiguration.java` (program-level, no validity fields). `intouch-api-v3` `TierStrategyTransformer.applySlabUpgradeDelta` and `extractEligibilityForSlab` already flow per-slab data; the Designer confirms the exact method already handles the per-tier `validity.*` write path.

**Per**: Phase 4 C-8 Option A, 2026-04-22. Resolves contradictions.md C-8 (BLOCKER).

---

### ADR-19R: `PeriodType` Enum Scope Lock + FIXED-Family Conditional Duration Requirement (Rework #6a — NEW, 2026-04-22)

**Decision** *(amended Phase 7 §6a.6 — `FIXED_LAST_UPGRADE` was PRD-wording phantom; engine enum has 4 values, verified `peb/.../TierDowngradePeriodConfig.java:17-18`)*:
1. Rework #6a explicitly handles `PeriodType.SLAB_UPGRADE`-family only (REQ-21 drop of `validity.startDate`, REQ-36 start-date reject on write for both `SLAB_UPGRADE` and `SLAB_UPGRADE_CYCLIC`). The other 2 enum values — `FIXED`, `FIXED_CUSTOMER_REGISTRATION` — are subject to the REQ-56 FIXED-family guard (point 2 below); their read-side behaviour is pass-through unchanged from Rework #5.
2. **REQ-56 (new)**: any FIXED-family `periodType` (`FIXED`, `FIXED_CUSTOMER_REGISTRATION` — 2 values, NOT 3) on per-tier POST/PUT REQUIRES `validity.periodValue` present, non-null, and a positive integer. Missing/null/non-positive is rejected with **400 InvalidInputException, error code 9018**. SLAB_UPGRADE-family (`SLAB_UPGRADE`, `SLAB_UPGRADE_CYCLIC`) does not require `periodValue` — engine is event-driven, no fixed duration.
3. **REQ-22 (amended)**: read-side duration computation is null-safe for legacy FIXED tiers whose stored `periodValue` is absent (pre-6a) — computed end-date is omitted rather than returned as null/0.

**Context**: `PeriodType` has 4 enum values in the engine; BA coverage only explicitly handled `SLAB_UPGRADE` (REQ-21, REQ-36). Critic raised C-12 — the other 3 values are silently untouched on both wire and engine path, creating an enum-scope blind spot. A pure scope-lock alone (option c) would leave FIXED tiers writable without durations, so the user added the conditional-duration caveat: writes MUST carry duration for FIXED family, reads MUST tolerate legacy FIXED tiers that lack it.

**Alternatives considered (Phase 4)**:
- **(a) Full coverage — add explicit handling for all 4 enum values**: Rejected. Cyclic and fixed-customer-registration are ~zero-adoption in production programs; wire validation for them is speculative work.
- **(b) Implicit passthrough — document all 4 as out of scope**: Rejected. Leaves FIXED family exposed to save-without-duration silently.
- **(c) Scope lock with conditional duration — adopted**: SLAB_UPGRADE is the only actively-handled case; FIXED family is allowed but duration is required (forward guard); the 2 other SLAB_UPGRADE_CYCLIC + 2 non-FIXED enum value are untouched.

**Rationale**: Option (c) + user caveat is the minimal-surface fix that prevents the C-12 gap from widening without forcing coverage work that no user has requested. Per-enum read-behaviour for the 3 unhandled values is a forward question if it ever surfaces as an actual code-path issue.

**Deferred to Designer (Phase 7)** — now **RESOLVED** (see `03-designer.md` §6a.2):
- PUT merge semantics: **payload-only** (§6a.2.2). Matches existing validator shape, deterministic 400s, no stored-state dependency.
- Read-side wire shape: **omit** (§6a.2.3, D-6a-2). `TierValidityConfig` already annotated `@JsonInclude(NON_NULL)`; null/0 forbidden by forward guard.

**Per**: Phase 4 Q-OP-2 Option (c) + user-imposed conditional-duration caveat, 2026-04-22. Resolves contradictions.md C-12 (partial — forward guard added; 3 non-SLAB_UPGRADE enum reads remain pass-through).

---

### ADR-20R: Unknown-Field Hard Reject via Jackson `FAIL_ON_UNKNOWN_PROPERTIES` (Rework #6a — NEW, 2026-04-22)

**Decision**: All v3 tier wire DTOs on `POST /v3/tiers` / `PUT /v3/tiers/{tierDocId}` reject unknown fields at deserialization time. The legacy `downgrade` block (renamed to `renewal` in Q3) is rejected by this mechanism — zero back-compat window, zero dual-block tolerance. The rejection is returned as `400 InvalidInputException` from the Spring MVC exception handler.

**Context**: Q11 locked the hard-flip decision (no back-compat window for the `downgrade → renewal` rename). Critic raised C-11 — the BA assumed Jackson `FAIL_ON_UNKNOWN_PROPERTIES=true` was already configured on the intouch-api-v3 global `ObjectMapper`, but the assumption was unverified (A-01). If the config is actually default (`FAIL_ON_UNKNOWN_PROPERTIES=false`), unknown fields are silently ignored and REQ-27/REQ-49 become a no-op.

**Alternatives considered**:
- **(a) Rely on global Jackson config (`FAIL_ON_UNKNOWN_PROPERTIES=true`)**: Adopted **conditionally** — Designer (Phase 7) must verify the setting on the intouch-api-v3 global `ObjectMapper` before this ADR commits. If verified, no code change.
- **(b) Explicit scanning validator in `TierCreateRequestValidator` / `TierUpdateRequestValidator`**: Fallback if (a) verification fails. Walk the parsed JSON tree; any field not in the accepted contract triggers 400.
- **(c) Per-DTO `@JsonIgnoreProperties(ignoreUnknown = false)` annotation**: Alternative fallback; explicit at the DTO level but has to be applied to every DTO (easy to miss one).

**Rationale**: Option (a) is cleanest — a single global config covers every endpoint consistently. Options (b) and (c) are the Phase 7 fallbacks if the global config turns out to be permissive; QA and SDET write tests asserting the reject either way, so a silent regression is impossible regardless of which implementation Designer picks.

**Residual risks** (flagged to Phase 11 Reviewer via C-17):
- External consumer audit scoped to 16 repos in the workspace confirmed zero internal backend callers (`q-op-3-consumer-audit.md`). External SaaS customers, third-party integrations, separate automation repos, nginx rewrites, and operator scripts remain unaudited.
- Mitigation recommendations for deploy prep: (i) access-log scan at staging gateway for non-UI user agents; (ii) publish 9011-9020 band in `api-handoff.md` ≥30 days before cutover; (iii) optional soft-launch that logs (not rejects) unknown fields in staging for 2 weeks.

**Per**: Phase 4 Q11 (locked earlier) + Q-OP-3 Option (a) audit, 2026-04-22. Resolves contradictions.md C-11 (partial — Designer verification pending) + C-17 (partial — internal audited, external residual flagged).

---

### ADR-21R: Write-Narrow / Read-Wide Asymmetric Tier Contract (Rework #6a — NEW, 2026-04-22)

**Decision**: `/v3/tiers` has an **asymmetric** contract:
- **Write (POST, PUT, delete-draft, submit, approve, reject)**: accepts **per-tier fields only**. Program-level fields (Class A: 4 booleans; Class B: 6 eligibility fields) are rejected with per-code 400 (9011, 9012, 9013). Advanced-settings (program-level singleton) lives on a separate surface (6b forthcoming).
- **Read (GET list, GET detail)**: emits the **full hoisted envelope** — per-tier fields AND program-level fields joined from strategy reads. No field rejection, no field filtering (except `-1` sentinel symmetry per 9015). The UI's advanced-settings screen reads this envelope too.

**Context**: Q24 ratified this asymmetry after Q17/Q18/Q19/Q21/Q25 were subsumed into it. The write-narrow stance enforces the Rework #5 MC scope boundary: per-tier writes are the only place where draft-versus-live matters; program-level configuration is a distinct lifecycle that doesn't need MC today and shouldn't be entangled with tier DRAFT/PENDING_APPROVAL status. The read-wide stance preserves the single-round-trip envelope that Rework #5 adopted (ADR-09R) — the UI's tier-list screen still fetches one GET per program, no N+1.

**Alternatives considered**:
- **(a) Symmetric contract (write everything, read everything)**: Rejected. Pulls program-level write-path into the tier MC scope and couples two independent configurations. Would require MC for advanced-settings too, which user rejected (Q25).
- **(b) Separate endpoints for per-tier and program-level writes, no hoisting on reads**: Rejected. Doubles client-side complexity (2 GETs per tier screen), loses the envelope round-trip win from Rework #5.
- **(c) Asymmetric — adopted**: Write-narrow via per-code rejects (9011/9012/9013); read-wide via unchanged envelope.

**Rationale**: Asymmetry is the correct compromise between MC scope purity (write-narrow) and UI performance (read-wide). Per-code write rejects are diagnostic; the same fields emitted on GET come from the program-level strategy read via `SqlTierConverter` and `TierStrategyTransformer.extractEligibilityForSlab`. No engine change, no new storage.

**Per**: Phase 4 lock on Q24 (ratified pre-Phase 4), 2026-04-22. Documents the asymmetry explicitly for Designer and SDET (no wire-contract change itself — this ADR is the audit-trail anchor for the asymmetric expectation).

---

## 10. Implementation Plan (Completed)

### Layer 1: Generic Maker-Checker Framework (makechecker/ - Baljeet's Package)
- COMPLETED: Pre-existing in Baljeet's package
- `ApprovableEntity` interface (getStatus, setStatus, getVersion, setVersion, transitionToPending, transitionToRejected)
- `ApprovableEntityHandler<T>` interface (validateForSubmission, preApprove, publish, postApprove, onPublishFailure, postReject)
- `MakerCheckerService<T>` (submitForApproval, approve with SAGA, reject)
- Status transitions managed on entity itself (no PendingChange collection)

### Layer 2: Tier CRUD (intouch-api-v3)
- COMPLETED: All tier-specific implementation
1. `TierStatus` enum: DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT
2. `UnifiedTierConfig` MongoDB @Document implementing `ApprovableEntity`
3. `TierRepository` + `TierRepositoryImpl` (sharded MongoDB)
4. `TierValidationService`
5. `TierFacade` -- submitForApproval(), handleApproval(), creation, editing, deletion logic
6. `TierController` -- GET/POST/PUT/DELETE endpoints
7. `TierReviewController` -- POST /v3/tiers/{tierId}/submit, POST /v3/tiers/{tierId}/approve, GET /v3/tiers/approvals
8. `TierApprovalHandler` implements `ApprovableEntityHandler<UnifiedTierConfig>` -- MongoDB -> Thrift conversion (Section 7)

### Layer 3: emf-parent Changes (Rework #5 — additive)
- `ProgramSlab` entity: add `updatedBy`, `approvedBy`, `approvedAt` fields (nullable). `createdBy` NOT added.
- `PointsEngineRulesThriftService`: wrapper methods for slab Thrift calls (already exist); signature enriched with optional audit fields.
- **Flyway migration**: `ALTER TABLE program_slabs ADD COLUMN updatedBy VARCHAR(255) NULL, ADD COLUMN approvedBy VARCHAR(255) NULL, ADD COLUMN approvedAt DATETIME NULL;` — details in `01b-migrator.md`.
- Backward-compatible: legacy code paths continue to work (new columns NULL for rows never touched by MC).

### Layer 4: Integration + Cache (Completed)
- COMPLETED: Member count cache job (cron every 10 min)
- COMPLETED: End-to-end testing: create tier -> submit -> approve -> verify SQL

---

## 11. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| R1: CSV index off-by-one | HIGH | Unit test with 3,4,5+ slabs. serialNumber-2 = CSV index. |
| R2: Downgrade strategy monolith | MEDIUM | @Lockable on TierApprovalHandler methods. |
| R3: Strategy ID preservation | MEDIUM | Always fetch existing strategy ID before update. |
| R4: CSV positions on soft-delete | LOW | Never remove positions. Document in code comments. |
| R5: Legacy API in separate service | LOW | Listing reads SQL via Thrift converter + Mongo (Rework #5 — unified surface). |
| **R6: Drift false-positive rate (Rework #5)** | MEDIUM | Conservative drift policy may reject approvals on unrelated field changes. Mitigation: surface clear message to approver with field-level diff; allow easy "recreate DRAFT". Revisit policy if friction emerges. |
| **R7: SNAPSHOT proliferation (Rework #5)** | LOW | SNAPSHOT docs accumulate per tier over time. Mitigation: retention/purging deferred to future; bounded in practice (few edits per tier per quarter). |
| **R8: SNAPSHOT drift vs SQL (Rework #5)** | LOW | Mongo SNAPSHOT not reconciled with later legacy SQL edits. UI history view surfaces caveat label when detected. Accept as design choice. |
| **R9: Cross-UI name race (Rework #5)** | MEDIUM | 3-layer defense: app check at DRAFT creation + re-check at approval + SQL UNIQUE. Catches old-UI vs new-UI race. |
| **R10: SQL audit column backfill on legacy rows (Rework #5)** | LOW | Columns are nullable. Legacy pre-rework rows have NULL updatedBy/approvedBy/approvedAt — expected. No backfill needed. |
| **R11: New-tier DRAFT partial unique index edge case (Rework #5)** | LOW | MongoDB treats null `slabId` as non-conflicting, so multiple new-tier DRAFTs can coexist. This is correct (each gets its own slabId on approval). Documented in §5.3. |
| **R12: Stale `basisSqlSnapshot` for long-lived DRAFTs (Rework #5)** | MEDIUM | DRAFTs can sit for days. A legacy edit during that time will cause drift-block on approval. Mitigation: clear "recreate DRAFT" path in UX; consider TTL on DRAFTs in a future rework. |
| **R13: Unaudited external consumers of `/v3/tiers` (Rework #6a — C-17 residual)** | MEDIUM | Codebase audit across 16 repos confirmed zero internal backend callers (`q-op-3-consumer-audit.md`), but external SaaS customers, partner integrations, separate QA/automation repos, nginx rewrites, and operator scripts remain outside audit reach. A client still submitting a `downgrade` block or an unknown field will break on cutover. **Mitigation (Phase 11 Reviewer ask)**: access-log scan at staging gateway for 30 days; publish 9011-9020 band in `api-handoff.md` ≥30 days ahead of cutover; optional soft-launch that logs (doesn't reject) unknown fields in staging for 2 weeks. |
| **R14: Jackson `FAIL_ON_UNKNOWN_PROPERTIES` not globally configured (Rework #6a — C-11 open)** | MEDIUM | ADR-20R relies on the intouch-api-v3 global `ObjectMapper` rejecting unknown fields. If the setting is actually permissive, REQ-27/REQ-49 become silent no-ops. **Mitigation**: Designer (Phase 7) verifies the config as the first step of LLD; if permissive, fallback (b) explicit scanning validator or fallback (c) per-DTO `@JsonIgnoreProperties(ignoreUnknown=false)`. SDET writes tests that assert rejection either way, so a silent regression is impossible. |
| **R15: PeriodType pass-through rot for 3 non-SLAB_UPGRADE values (Rework #6a — C-12 residual)** | LOW | `FIXED_CUSTOMER_REGISTRATION`, `FIXED_LAST_UPGRADE`, `SLAB_UPGRADE_CYCLIC` reads are pass-through from Rework #5. If a legacy tier with one of these values surfaces a read-path defect later, it will not be covered by 6a test cases. **Mitigation**: REQ-22 amendment (null-safety on legacy FIXED reads) is the only live safety net; REQ-56 forward guard (FIXED-family requires duration on write) prevents new tiers from being saved without durations. The 3 enum values remain pass-through — if a defect surfaces later, a follow-up rework explicitly covers them. |

---

## 12. Done Criteria (Rework #5 — updated)

- [x] `GET /v3/tiers?programId={id}` returns **ALL tiers** (legacy SQL-origin + new-UI-origin) as envelope `{live, pendingDraft}` per tier (Rework #5)
- [x] `GET /v3/tiers/{slabId}` returns single-tier envelope `{live, pendingDraft}` (Rework #5)
- [x] `SqlTierConverter` implemented — read-only; not used on any write path (Rework #5)
- [x] `POST /v3/tiers` creates a new-tier DRAFT (slabId=null). Name collision rejected at Layer 1. (Rework #5)
- [x] `PUT /v3/tiers/{slabId}` creates a new DRAFT with `meta.basisSqlSnapshot` captured from current SQL. Blocked if another active DRAFT exists (partial unique index). (Rework #5)
- [x] `DELETE /v3/tiers/{tierDocId}` deletes DRAFT tier (→ DELETED). 409 if not DRAFT.
- [x] `POST /v3/tiers/{tierDocId}/submit` — DRAFT → PENDING_APPROVAL (idempotent for same doc)
- [x] `POST /v3/tiers/{tierDocId}/approve` — full SAGA: preApprove drift-check + name re-check → publish Thrift → postApprove SNAPSHOT. Block with clear message on drift/collision. (Rework #5)
- [x] `POST /v3/tiers/{tierDocId}/reject` — PENDING_APPROVAL → DRAFT, comment required
- [x] `GET /v3/tiers/approvals?programId={id}` — list pending approval tiers
- [x] Old UI legacy endpoints untouched — continue to write directly to SQL, set `updatedBy` only, no MC (Rework #5)
- [x] Generic MC framework: Baljeet's `makechecker/` package (ApprovableEntity + ApprovableEntityHandler + SAGA)
- [x] MC toggle per-program + per-entity-type applies to new-UI writes only (Rework #5)
- [x] TierApprovalHandler syncs MongoDB → SQL via Thrift with drift check in `preApprove` (Rework #5)
- [x] **Flyway migration applied**: `ALTER TABLE program_slabs ADD updatedBy, approvedBy, approvedAt` (Rework #5)
- [x] `program_slabs.createdBy` explicitly NOT added (Rework #5 user decision)
- [x] Thrift `createSlabAndUpdateStrategies` extended with optional `updatedBy`/`approvedBy`/`approvedAt` fields (backward-compatible via optional-typed additions)
- [x] `UnifiedTierConfig` schema: `basicDetails` + `metadata` hoisted to root; `nudges`, `benefitIds`, `updatedViaNewUI`, `basicDetails.startDate/endDate` dropped; `unifiedTierId` → `tierUniqueId`; `metadata.sqlSlabId` → root `slabId` (Rework #5)
- [x] `meta.basisSqlSnapshot` captured at DRAFT creation for LIVE-tier edits (Rework #5)
- [x] Mongo Index 1 `(orgId, programId, status)` + Index 2 PARTIAL UNIQUE `(orgId, programId, slabId)` where `status IN [DRAFT, PENDING_APPROVAL]` (Rework #5)
- [x] Name collision: 3-layer defense (app at DRAFT creation, re-check at approval, SQL UNIQUE backstop) (Rework #5)
- [x] Single active DRAFT/PENDING_APPROVAL per tier enforced app-level + DB partial unique (Rework #5)
- [x] `parentId` = parent's `program_slabs.id`; parent must be LIVE; self-reference rejected (Rework #5)
- [x] All tests pass (unit + integration) — including new BTs for dual-path, drift, envelope, single-active-draft, name collision
- [x] serialNumber immutability enforced (400 on change attempt)
- [x] Member count cache refreshes every 10 min
- [x] Deleted old makerchecker/ package (17 files)
- [x] Removed MakerCheckerController, MakerCheckerFacade, MakerCheckerServiceImpl, PendingChange collection, ChangeApplier interface
- [x] ~~PartnerProgramSlab block validation~~ Deferred to future tier retirement epic (Rework #2)

### Rework #6a Done Criteria (added 2026-04-22 — to be executed by Designer → Developer cascade)

- [ ] **ADR-17R**: Per-code rejects 9011, 9012, 9013, 9014, 9015, 9016, 9017, 9018 allocated in constants file; no code in 9001-9010 reused or reassigned; `api-handoff.md` error-code block matches this allocation 1:1.
- [ ] **ADR-18R**: Designer LLD confirms `TierDowngradeSlabConfig[].periodConfig.{periodType, periodValue}` is the read/write target for per-tier `validity.*` fields; no new schema field added; `TierStrategyTransformer.applySlabUpgradeDelta` and `extractEligibilityForSlab` exercise this path in tests.
- [ ] **ADR-19R**: REQ-56 validator active on both POST and PUT — FIXED-family `periodType` (`FIXED`, `FIXED_CUSTOMER_REGISTRATION` — 2 values, corrected Phase 7 §6a.6) without `periodValue` rejected 400/9018; PUT merge semantics = **payload-only** (Designer locked §6a.2.2); SLAB_UPGRADE-family `periodValue` remains optional. Read-side = **omit** legacy FIXED tiers' missing periodValue (Designer locked §6a.2.3, D-6a-2).
- [ ] **ADR-20R**: Designer verifies `FAIL_ON_UNKNOWN_PROPERTIES=true` on the intouch-api-v3 global `ObjectMapper` configuration. If verified, no code change. If not, fallback (b) explicit scanning validator or fallback (c) per-DTO annotation. Legacy `downgrade` block is rejected at deserialization with `400 InvalidInputException`.
- [ ] **ADR-21R**: Write-narrow / read-wide asymmetry documented; advanced-settings (program-level singleton) confirmed OUT of 6a scope (folds into 6b).
- [ ] Q-OP-3 residual-risk flag carried to Phase 11 Reviewer: access-log scan ask + soft-launch recommendation + band announcement ≥30 days before cutover.
- [ ] All BA REQ-22 + REQ-56 + per-code rejects covered by Business Test Cases (Phase 8b) with traceability back to this document's §6.5 matrix.
