# 01 — Architect (HLD) — Benefit Category CRUD (CAP-185145)

> **Phase**: 6 (HLD) — Architect
> **Ticket**: CAP-185145
> **Date**: 2026-04-18
> **Inputs**: `session-memory.md` (D-01..D-36), `00-ba.md`, `00-prd.md`, `gap-analysis-brd.md`, `cross-repo-trace.md`, `code-analysis-*.md` (4 repos), `.claude/skills/GUARDRAILS.md`, `.claude/CLAUDE.md § Standing ADRs`.
> **Frozen inputs**: D-33, D-34, D-35, D-36 reproduced verbatim as ADR-001..ADR-004 below — not re-debated.

---

## 1. Executive Summary

This feature introduces a **config-only, Program-scoped metadata service** for benefit categories and their applicability to tier slabs. It creates two net-new MySQL tables — `benefit_categories` and `benefit_category_slab_mapping` — owned by `emf-parent`, exposed as CRUD over Thrift via the existing `PointsEngineRuleService`, and fronted by `intouch-api-v3` as a thin REST facade. The new `BenefitCategory` entity coexists strictly with the legacy `Benefits` entity — no FKs, no shared tables, no migration of legacy data (D-12 / C-14).

The shape of the solution is the established 4-layer Capillary pattern: `REST Controller → Facade → Thrift Client → EMF Thrift Handler → Editor → Service (@Transactional) → DAO`. There are five endpoints on `/v3/benefitCategories` (POST, PUT, GET by id, GET list, PATCH `/activate`, PATCH `/deactivate`) mapped to four new methods on the existing `pointsengine-rules` Thrift service plus two struct field additions.

The four frozen ADRs (ADR-001..004) are structurally load-bearing: (a) **ADR-001** removes optimistic locking and simplifies the DTO contract + DDL — every downstream design (Designer, QA, SDET) inherits a "no `@Version`, no `If-Match`" posture; (b) **ADR-002** introduces a dedicated reactivation verb, which re-words D-27 and splits idempotency contracts cleanly; (c) **ADR-003** chooses an embedded-`slabIds` parent DTO with server-side diff-and-apply, meaning the junction table has ZERO REST surface and fan-out is reduced; (d) **ADR-004** mirrors (b) for deactivation with cascade-in-transaction (C-16). The net effect: five REST endpoints, four Thrift methods, one facade, two DAOs, two DDL files, one new exception class — a small, focused cross-repo fan-out where the read path is identical to the write path (D-19).

---

## 2. Frozen ADRs (verbatim — ADR-001..004)

### ADR-001 — No optimistic locking on `BenefitCategory` (from D-33)

**Status**: Accepted (user-decided — pre-HLD commit #1). Frozen.

**Context**. Concurrent admin writes on the same `BenefitCategory` row (e.g., two admins renaming or re-slabbing the category at once) can silently overwrite each other unless the write path carries a version token. The platform-standard guardrail G-10 (concurrency) recommends JPA `@Version` + client-supplied `version` on every update. At the scale declared in D-26 (SMALL — ≤50 categories per program, ≤20 slab-mappings per category, <1 QPS sustained writes, typically one admin editor at a time), the `@Version` infrastructure adds DTO surface + DDL column + client round-trip ceremony for a race window that is functionally unreachable.

**Decision**. No optimistic locking on `BenefitCategory`.
- No `@Version` entity column
- No `version` field in Create/Update request DTO
- No `version BIGINT` column in DDL
- Last-write-wins for all concurrent admin writes on the same row

**Consequences**.
- *Positive*: simpler DTO + DDL + facade contract; no client-side version management; no stale-version 409 path; -1 Thrift field; -1 DB column.
- *Negative*: A second concurrent write silently overwrites the first. No feedback to admin that their view was stale.
- *Accepted risk*: A correctness race exists in principle. At D-26 scale the race window is small and the data it affects is low-harm (config-only, soft-delete available, observable in audit columns).
- *Guardrail posture*: G-10 marked as **accepted deviation**, documented here.
- **Revisit-triggers** (monitor post-GA):
  - Admin-write QPS on `benefit_categories` crosses 10/sec per tenant over a 1-hour window
  - Multi-editor Admin UI ships (simultaneous browser tabs with save actions)
  - Any incident tagged "concurrent-write-conflict" on this surface
  - Migration of this entity to MongoDB (where optimistic concurrency shape differs)

**Flow — Last-Write-Wins Posture (no lock)**

```mermaid
sequenceDiagram
    autonumber
    participant A1 as Admin #1
    participant A2 as Admin #2
    participant REST as intouch-api-v3
    participant EMF as EMF Service
    participant DB as MySQL

    A1->>REST: PUT /v3/benefitCategories/42 (name=X, slabIds=[1,2])
    A2->>REST: PUT /v3/benefitCategories/42 (name=Y, slabIds=[1,3])
    REST->>EMF: updateBenefitCategory(orgId, id=42, name=X, slabIds=[1,2])
    REST->>EMF: updateBenefitCategory(orgId, id=42, name=Y, slabIds=[1,3])
    EMF->>DB: UPDATE ... WHERE id=42 AND org_id=?
    DB-->>EMF: OK (name=X written)
    EMF->>DB: UPDATE ... WHERE id=42 AND org_id=?
    DB-->>EMF: OK (name=Y overwrites X — LAST WRITE WINS)
    EMF-->>REST: 200 (both calls succeed)
    REST-->>A1: 200 — unaware write was overwritten
    REST-->>A2: 200
    Note over DB: No @Version check. No 409. No rollback. Admin #1's change lost silently.<br/>Revisit if admin QPS > 10/sec per tenant OR multi-editor Admin UI.
```

---

### ADR-002 — Reactivation via dedicated `PATCH /v3/benefitCategories/{id}/activate` endpoint (from D-34)

**Status**: Accepted (user-decided — pre-HLD commit #2). Frozen.

**Context**. D-27 originally stated "deactivation is terminal — any mutation on an inactive row returns 409." During rework, US-6 (reactivate a soft-deleted category) was recognised as a P1 admin workflow: mis-deactivations happen, and POST-a-new-row is not an acceptable recovery path when admins want to preserve the original `id` for audit traceability. A dedicated verb avoids bending PUT or PATCH `{is_active: true}` semantics and makes the idempotency + name-conflict contract explicit.

**Decision**. Introduce a dedicated reactivation endpoint:
- **REST**: `PATCH /v3/benefitCategories/{id}/activate`
- **Behaviour**:
  - Flips `is_active=false → true` on the `benefit_categories` row
  - **Does NOT auto-reactivate cascaded slab-mappings** — admin must re-apply `slabIds` via subsequent PUT (or via the create/update DTO's `slabIds` diff-apply)
  - Returns `204 No Content` on success (may alternatively return the category DTO — ADR-006 below pins this to `204` for symmetry with `/deactivate`)
  - Returns `404 Not Found` if category does not exist in the caller's org
  - Returns `409 Conflict` if a DIFFERENT active category in the same program now owns that name (D-28 uniqueness-among-active applies at reactivation)
  - Idempotency on already-active: returns `204 No Content` (no-op) — pinned in ADR-006
- **Thrift IDL**: +1 method `activateBenefitCategory(i32 orgId, i32 categoryId, i32 actorUserId) throws (1: PointsEngineRuleServiceException ex)`.
- **D-27 rewording**: PUT and DELETE on inactive categories still return `409`; **reactivation via the dedicated `PATCH /activate` is the only allowed state-change on an inactive category**. Soft-delete stays terminal for PUT/DELETE; only `/activate` can flip the bit back.

**Consequences**.
- *Positive*: preserves `id` for audit trace; clean idempotency and conflict contracts; symmetric with ADR-004; Thrift method is orgId+id+actor — tiny surface.
- *Negative*: +1 Thrift method; admin must do TWO operations to restore full state (activate, then PUT to re-slab).
- *Accepted risk*: reactivation-name-collision is an observable 409 — admin must rename the conflicting active category first.

**Flow — Reactivation**

```mermaid
sequenceDiagram
    autonumber
    participant Admin
    participant REST as intouch-api-v3
    participant Facade as BenefitCategoryFacade
    participant Thrift as EMF Thrift Handler
    participant Svc as PointsEngineRuleService
    participant DAO as BenefitCategoryDao
    participant DB as MySQL

    Admin->>REST: PATCH /v3/benefitCategories/42/activate
    REST->>Facade: activate(orgId=100, id=42, actor=7)
    Facade->>Thrift: activateBenefitCategory(orgId, 42, 7)
    Thrift->>Svc: activate(orgId, 42, actor)
    Svc->>DAO: findById(orgId, 42)
    alt Not found
        DAO-->>Svc: empty
        Svc-->>Thrift: throw PointsEngineRuleServiceException(404)
        Thrift-->>Facade: Exception(status=404)
        Facade-->>REST: throw NotFoundException
        REST-->>Admin: 200 + error envelope (platform quirk, see ADR-009)
    else Already active
        DAO-->>Svc: row { is_active=true }
        Svc-->>Thrift: OK (no-op)
        Thrift-->>REST: success
        REST-->>Admin: 204 No Content (idempotent)
    else Inactive — check name conflict
        DAO-->>Svc: row { is_active=false, name=X }
        Svc->>DAO: findActiveByProgramAndName(orgId, programId, X)
        alt Active conflict exists
            DAO-->>Svc: conflicting row
            Svc-->>Thrift: throw PointsEngineRuleServiceException(409, "NAME_TAKEN")
            Thrift-->>Facade: Exception(status=409)
            Facade-->>REST: throw ConflictException
            REST-->>Admin: 409 Conflict + error envelope
        else No conflict
            DAO-->>Svc: empty
            Svc->>DAO: UPDATE benefit_categories SET is_active=true, updated_on, updated_by WHERE id=42 AND org_id=100
            Note over DB: Slab mappings DO NOT auto-reactivate (ADR-002 clause).
            DAO-->>Svc: 1 row updated
            Svc-->>Thrift: OK
            Thrift-->>REST: success
            REST-->>Admin: 204 No Content
        end
    end
```

---

### ADR-003 — REST surface granularity: `slabIds` embedded in parent DTO; server-side diff-and-apply (from D-35)

**Status**: Accepted (user-decided — pre-HLD commit #3). Frozen.

**Context**. The BenefitCategory ↔ ProgramSlab relationship is a classic many-to-many junction. The REST surface has three shapes to choose from: (a) a separate `/benefitCategorySlabMappings` sub-resource with its own POST/DELETE; (b) `slabIds` embedded in the parent DTO, server diffs desired vs. current state; (c) an explicit `add/remove` command sub-path. Option (b) matches Maya's mental model (a category has a set of applicable tiers — not a set of mapping objects) and eliminates cross-resource consistency headaches at the REST layer.

**Decision**. Embed `slabIds: List<Integer>` in the parent `BenefitCategory` DTO. Server-side `syncSlabMappings(categoryId, newIdSet)` performs the diff-and-apply on every Create and Update. The junction table `benefit_category_slab_mapping` is **not exposed** as a REST sub-resource.

- **Endpoint count on `/v3/benefitCategories`**: **5** (POST, PUT, GET by id, GET list, PATCH `/{id}/activate`, PATCH `/{id}/deactivate`). (6 paths total when counting both PATCH sub-paths.)
- **Validation**:
  - **Layer 1 — Bean Validation on DTO**: `@NotNull @Size(min=1)` on Create; `@NotNull` only on Update (`min=1` enforced at facade). `List<@Positive Integer> slabIds` element constraint.
  - **Layer 2 — Facade**: silent dedup via `LinkedHashSet<>(slabIds)`; cross-check every incoming slabId exists in `program_slabs` for the same `(orgId, programId)`. Any non-existent or wrong-program slabId → HTTP 409 `CROSS_PROGRAM_SLAB` / `UNKNOWN_SLAB`.
- **Diff-and-apply semantics**:
  - `incoming = LinkedHashSet<Integer> slabIds`
  - `current = { m.slabId : m in mappings WHERE categoryId=? AND org_id=? AND is_active=true }`
  - `toAdd = incoming \ current` → INSERT new mapping rows (`is_active=true`, fresh audit columns)
  - `toSoftDelete = current \ incoming` → bulk UPDATE `is_active=false, updated_on=NOW(), updated_by=actor`
  - `toKeep = incoming ∩ current` → no writes
- **Re-add semantics**: re-adding a previously unmapped slabId INSERTs a NEW mapping row (does NOT reactivate the soft-deleted row). Old deactivated rows remain as audit history; only the newest `is_active=true` row per `(category_id, slab_id, org_id)` is authoritative.
- **Cascade-deactivate symmetry** (D-06 / C-16 preserved): on `PATCH /{id}/deactivate`, ALL active mappings for that category soft-delete in the same transaction (single bulk UPDATE). On `PATCH /{id}/activate`, mappings do **not** auto-reactivate.
- **Thrift IDL impact**: +0 mapping-specific methods. `createBenefitCategory` and `updateBenefitCategory` structs gain `list<i32> slabIds`.

**Consequences**.
- *Positive*: Maya-aligned UX; one transactional boundary per write; zero cross-resource consistency risk; smaller cross-repo fan-out (no new controller, no new handler methods, no new Thrift methods beyond ADR-002/004).
- *Negative*: Full `slabIds` on every PUT even for name-only changes (extra bytes on wire); diff-and-apply logic requires a read-before-write inside the txn.
- *Accepted risk* — concurrent re-slab of the same category: no optimistic lock (ADR-001), so the last PUT's `slabIds` wins for the whole set. Logged; not mitigated.

**Flow — Update with Diff-and-Apply**

```mermaid
sequenceDiagram
    autonumber
    participant Admin
    participant REST as intouch-api-v3
    participant Svc as PointsEngineRuleService<br/>@Transactional(warehouse)
    participant CatDao as BenefitCategoryDao
    participant MapDao as BenefitCategorySlabMappingDao
    participant SlabDao as PeProgramSlabDao

    Admin->>REST: PUT /v3/benefitCategories/42 { name:"VIP", slabIds:[1,3,5] }
    REST->>Svc: update(orgId=100, id=42, {name, slabIds=[1,3,5]})
    Svc->>CatDao: findActiveById(orgId, 42)
    CatDao-->>Svc: cat (is_active=true)
    Svc->>Svc: silent dedup: slabIds = LinkedHashSet{1,3,5}
    Svc->>SlabDao: findExistingSlabIds(orgId, programId=cat.programId, [1,3,5])
    SlabDao-->>Svc: [1,3,5] all found
    Svc->>CatDao: findActiveByProgramAndNameExceptId(orgId, programId, "VIP", 42)
    CatDao-->>Svc: empty (no conflict)
    Svc->>MapDao: findActiveSlabIds(orgId, categoryId=42)
    MapDao-->>Svc: [1,2,3]  (current)
    Svc->>Svc: toAdd = [5], toSoftDelete = [2], toKeep = [1,3]
    Svc->>CatDao: UPDATE name, updated_on, updated_by
    Svc->>MapDao: INSERT (category_id=42, slab_id=5, org_id=100, is_active=true, audit...)
    Svc->>MapDao: UPDATE benefit_category_slab_mapping SET is_active=false WHERE category_id=42 AND slab_id=2 AND org_id=100 AND is_active=true
    Svc-->>REST: BenefitCategoryDto { id:42, name:"VIP", slabIds:[1,3,5], isActive:true, ... }
    REST-->>Admin: 200 + ResponseWrapper(dto)
    Note over Svc: All operations in one @Transactional(warehouse). Failure rolls back all writes.
```

---

### ADR-004 — Deactivation verb: `PATCH /v3/benefitCategories/{id}/deactivate` with cascade (from D-36)

**Status**: Accepted (user-decided — pre-HLD commit #4). Frozen.

**Context**. Soft-delete semantics (D-13) are not accurately conveyed by `DELETE` — the row survives with `is_active=false`. A `PUT {isActive:false}` bends PUT semantics and is asymmetric with ADR-002's `PATCH /activate`. Admins and downstream consumers benefit from a verb that is unambiguous about what the operation does.

**Decision**. Introduce a dedicated deactivation endpoint:
- **REST**: `PATCH /v3/benefitCategories/{id}/deactivate`
- **Behaviour**:
  - Flips `is_active=true → false` on the category row
  - Cascades to all `is_active=true` `benefit_category_slab_mapping` rows for that category — bulk `UPDATE ... SET is_active=false, updated_on=NOW(), updated_by=actor WHERE category_id=? AND org_id=? AND is_active=true` in the same transaction (D-06 / C-16)
  - Returns `204 No Content` on success
  - Returns `404 Not Found` if category does not exist in the caller's org
  - Idempotency on already-deactivated: returns `204 No Content` (no-op) — pinned in ADR-006
- **Thrift IDL**: +1 method `deactivateBenefitCategory(i32 orgId, i32 categoryId, i32 actorUserId) throws (1: PointsEngineRuleServiceException ex)`.
- **D-27 alignment**: fully preserved — PUT on inactive still returns 409; DELETE verb is not exposed (C-15); reactivation is ADR-002's dedicated verb; deactivation is ADR-004's dedicated verb.
- **Rejected alternatives**:
  - `DELETE /{id}` — misleading for soft-delete; creates "why is the row still there?" bugs downstream.
  - `PUT {isActive:false}` — bends PUT; asymmetric with ADR-002.

**Consequences**.
- *Positive*: explicit verb; symmetric with ADR-002; clear cascade contract; single-txn cascade is safe at D-26 scale (max 20 mappings per category).
- *Negative*: +1 Thrift method; cascade is a bulk UPDATE that locks row-range in the mapping table for the duration of the txn (benign at this scale).
- *Accepted risk*: none identified at D-26 scale.

**Flow — Deactivate with Cascade**

```mermaid
sequenceDiagram
    autonumber
    participant Admin
    participant REST as intouch-api-v3
    participant Svc as PointsEngineRuleService<br/>@Transactional(warehouse)
    participant CatDao as BenefitCategoryDao
    participant MapDao as BenefitCategorySlabMappingDao
    participant DB as MySQL

    Admin->>REST: PATCH /v3/benefitCategories/42/deactivate
    REST->>Svc: deactivate(orgId=100, id=42, actor=7)
    Svc->>CatDao: findById(orgId, 42)
    alt Not found
        CatDao-->>Svc: empty
        Svc-->>REST: PointsEngineRuleServiceException(404)
        REST-->>Admin: 200 + error envelope (platform quirk)
    else Already inactive
        CatDao-->>Svc: row { is_active=false }
        Svc-->>REST: no-op
        REST-->>Admin: 204 No Content (idempotent)
    else Active — cascade
        CatDao-->>Svc: row { is_active=true }
        Svc->>CatDao: UPDATE benefit_categories SET is_active=false, updated_on=NOW(), updated_by=7 WHERE id=42 AND org_id=100 AND is_active=true
        Note over Svc,DB: SAME TRANSACTION
        Svc->>MapDao: UPDATE benefit_category_slab_mapping SET is_active=false, updated_on=NOW(), updated_by=7 WHERE category_id=42 AND org_id=100 AND is_active=true
        DB-->>Svc: 1 cat + N mapping rows updated
        Svc-->>REST: OK
        REST-->>Admin: 204 No Content
    end
```

---

## 3. Additional ADRs (ADR-005 onwards)

### ADR-005 — Thrift handler assignment: extend `PointsEngineRuleConfigThriftImpl`

**Context**. The four new Thrift methods (`createBenefitCategory`, `updateBenefitCategory`, `getBenefitCategory`, `listBenefitCategories`, `activateBenefitCategory`, `deactivateBenefitCategory`) need a home in `emf-parent`. Options: (a) add them to the existing `PointsEngineRuleConfigThriftImpl` class (currently ~60 methods), (b) create a new `BenefitCategoryThriftImpl` handler also annotated `@ExposedCall(thriftName = "pointsengine-rules")`.

**Evidence** (C7): `code-analysis-emf-parent.md` §2 — `PointsEngineRuleConfigThriftImpl` is the canonical CRUD template, already implements `PointsEngineRuleService.Iface` which means adding methods to the IDL means adding them to this class regardless. It already has the `BenefitsConfigData` CRUD methods for the legacy `Benefits` entity (`code-analysis-thrift-ifaces.md` lines 692-707, 1276-1282).

**Decision**. Add the 6 new handler methods to the existing `PointsEngineRuleConfigThriftImpl`. No new handler class.

**Consequences**.
- *Positive*: zero new Spring bean, zero new `@ExposedCall` registration, consistent with existing pattern, no `Iface` split.
- *Negative*: class grows from ~60 to ~66 methods; maintainability cost is real but linear.
- *Accepted*: Designer may extract helper classes for complex validation but the Thrift `@Override` handler methods stay on `PointsEngineRuleConfigThriftImpl`.

**Confidence**: C7 — evidence-verified from code-analysis + existing IDL pattern.

---

### ADR-006 — Response codes for `/activate` and `/deactivate` (AMENDED by D-39)

> **STATUS: AMENDED post-HLD by user decision D-39 (Phase 6 gate Q3)**. Original proposal was symmetric 204 on both verbs; amendment introduces a deliberate asymmetry on the happy path.

**Context**. ADR-002 and ADR-004 leave both the happy-path response body and the idempotency response code unpinned. Two dimensions to decide:
1. Happy activation body — 204 No Content vs 200 + DTO
2. Idempotency responses on "already in target state"

**Decision** (post-amendment).

| Case | Verb | Response |
|------|------|----------|
| Happy activate (was inactive → is active) | `PATCH /{id}/activate` | **200 OK + `BenefitCategoryResponse` DTO** (D-39 — UX win, saves GET round-trip) |
| Happy deactivate (was active → is inactive) | `PATCH /{id}/deactivate` | **204 No Content** (nothing useful to return — admin typically moves on) |
| Idempotent already-active | `PATCH /{id}/activate` | **204 No Content** (no state change, no DTO to return) |
| Idempotent already-inactive | `PATCH /{id}/deactivate` | **204 No Content** |

**Rationale for the asymmetry** (D-39).
- Activation typically precedes further admin edits — returning the DTO avoids a mandatory second GET.
- Deactivation is typically terminal within the admin session — no meaningful post-state to show.
- Both idempotency paths collapse to 204 since there is no state change to convey.

**Rejected**. (a) Fully symmetric 204 on both — original ADR-006 default; rejected by user in D-39 because client UX benefits from DTO on activate. (b) 409 on idempotency — would require new error codes (`ALREADY_ACTIVE`, `ALREADY_INACTIVE`) for a benign case; violates G-06.1 REST idempotency norm.

**Consequences**.
- *Positive*: client convenience on activate; REST-idiomatic on idempotency; robot-safe on retries.
- *Negative*: asymmetry must be documented in API docs and client SDK; integration tests assert both shapes.
- *Thrift IDL impact*: `activateBenefitCategory` returns `BenefitCategory` struct (same shape as `getBenefitCategory`) on state change, null/void on idempotent no-op — Designer encodes this via an optional return field. `deactivateBenefitCategory` remains `void`.
- *Facade impact*: `BenefitCategoryFacade.activate()` returns `Optional<BenefitCategoryResponse>` — empty on idempotent no-op, populated on state change; controller maps empty → 204, populated → 200 + body.
- *Accepted*: logged residual; server logs (structured, per G-08.2) capture "did state actually change" for audit.

**Confidence**: C6 — user decision (D-39); asymmetry trade-off explicitly acknowledged.

---

### ADR-007 — Data model: column types, audit pattern, soft-delete, NO `version`

**Context**. Sessions memory pins most fields via D-21..D-30; this ADR consolidates them into a single authoritative schema.

**Decision**. Schemas as follows.

**`benefit_categories`**:

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | `INT(11)` | NO | AUTO_INCREMENT | Part of composite PK (D-30 / `OrgEntityIntegerPKBase`) |
| `org_id` | `INT(11)` | NO | 0 | Part of composite PK; tenant isolation |
| `program_id` | `INT(11)` | NO | — | FK logical → `program_slabs.program_id`; indexed |
| `name` | `VARCHAR(255)` | NO | — | App-level uniqueness among active rows (D-28) |
| `category_type` | `ENUM('BENEFITS')` | NO | 'BENEFITS' | Single MVP value (D-06/D-10) |
| `is_active` | `TINYINT(1)` | NO | 1 | Soft-delete flag |
| `created_on` | `DATETIME` | NO | — | App-set UTC (D-24) |
| `created_by` | `INT(11)` | NO | — | Actor user id (D-30) |
| `updated_on` | `DATETIME` | YES | NULL | App-set UTC; null until first update |
| `updated_by` | `INT(11)` | YES | NULL | Actor user id on last update |
| `auto_update_time` | `TIMESTAMP` | NO | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | DB-managed safety net |

**Indexes**: `PRIMARY KEY (id, org_id)`; `KEY idx_bc_org_program (org_id, program_id)`; `KEY idx_bc_org_program_active (org_id, program_id, is_active)` (supports uniqueness check + list filtering).

**`benefit_category_slab_mapping`**:

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | `INT(11)` | NO | AUTO_INCREMENT | Composite PK |
| `org_id` | `INT(11)` | NO | 0 | Composite PK; tenant isolation |
| `benefit_category_id` | `INT(11)` | NO | — | Logical FK → `benefit_categories.id` (same org_id) |
| `slab_id` | `INT(11)` | NO | — | Logical FK → `program_slabs.id` (same org_id) |
| `is_active` | `TINYINT(1)` | NO | 1 | Soft-delete flag |
| `created_on` | `DATETIME` | NO | — | App-set UTC |
| `created_by` | `INT(11)` | NO | — | Actor user id |
| `updated_on` | `DATETIME` | YES | NULL | App-set UTC |
| `updated_by` | `INT(11)` | YES | NULL | Actor user id |
| `auto_update_time` | `TIMESTAMP` | NO | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | DB-managed safety net |

**Indexes**: `PRIMARY KEY (id, org_id)`; `KEY idx_bcsm_org_cat_active (org_id, benefit_category_id, is_active)` (supports cascade lookup + current-mappings read); `KEY idx_bcsm_org_slab_active (org_id, slab_id, is_active)` (supports "which categories apply to slab X" consumer query — D-21).

**Explicit call-out — NO `version` column on either table** (per ADR-001 / D-33). Last-write-wins.

**No FK declarations at DB level**. Cross-table integrity is enforced at the app layer (cross-check `slab_id` against `program_slabs` in the facade). Platform convention (`benefits.sql`, `program_slabs.sql`, `points_categories.sql` from code-analysis-cc-stack-crm.md) uses logical FKs only — composite PKs (id, org_id) across tables make declared FOREIGN KEYs awkward. Matches platform pattern (G-12.2).

**No DB-level UNIQUE constraint on `(org_id, program_id, name)`** — uniqueness enforced at application layer on active rows only (D-28/C-18'). **Post-D-38**: no advisory lock either; the SELECT→INSERT race is **accepted** at D-26 SMALL scale per the D-33 philosophy. See amended ADR-012 for revisit-triggers and future-remediation options (partial unique index requires Aurora ≥ 8.0.13 — deferred to Phase 12 per D-40).

**Confidence**: C7 — derived from D-21, D-22, D-23 (as amended by D-30), D-28, D-33; cross-referenced against `program_slabs.sql`, `points_categories.sql`, `Benefits.java`.

---

### ADR-008 — Timestamp representation: three-boundary pattern (carry-forward of D-24)

**Context**. G-01 (CRITICAL) mandates UTC timestamps via `java.time`; G-12.2 (CRITICAL) mandates following existing platform patterns. Existing platform uses `java.util.Date` + `@Temporal(TIMESTAMP)` + `DATETIME`. Resolving the tension at a single layer is impossible — every choice violates one guardrail.

**Decision** (D-24 / C-23' carried forward — restated for architect visibility):
- **EMF entity + MySQL**: `java.util.Date` + `@Temporal(TemporalType.TIMESTAMP)` + `DATETIME` column (pattern-match `Benefits`, `ProgramSlab`, `Promotions`). Audit columns written via `new Date()` set explicitly to UTC.
- **Thrift IDL**: `i64 createdOn` / `optional i64 updatedOn` — epoch **milliseconds** (matches `Date.getTime()` and JS convention). Field name: bare `createdOn`/`updatedOn` (pointsengine_rules.thrift convention, NOT the `*InMillis` convention used by `emf.thrift`).
- **REST (intouch-api-v3)**: ISO-8601 UTC strings — `"yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"` — via Jackson `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone="UTC")` on DTO fields. G-01.6-compliant external contract.

**Conversion ownership**:
- EMF Thrift handler owns `Date ↔ i64`. MUST use explicit UTC TimeZone (`TimeZone.getTimeZone("UTC")` or `Instant`-based conversion): `entity.createdOn.getTime()` is already UTC-millis; construction from millis uses `new Date(millis)`.
- intouch-api-v3 owns `i64 ↔ ISO-8601 UTC string` via Jackson config on `BenefitCategoryResponse` DTO fields.

**Guardrail posture**:
- G-01 (CRITICAL): compliant at external REST contract (G-01.6), violated internally in favour of G-12.2 parity. Multi-TZ integration test required (G-01.7, G-11.7) — Phase 9 SDET scope.
- G-12.2 (CRITICAL): compliant — matches `Benefits.java`, `ProgramSlab.java`.

**Residual risk**: JVM default timezone in production (OQ-38). Mitigation: Designer Phase 7 prescribes forced UTC in all Date/long conversions; SDET Phase 9 tests in UTC + IST + US/Eastern.

**Confidence**: C6 — frozen from Phase 4 D-24; evidence in code-analysis-emf-parent.md §1.

---

### ADR-009 — Error contract and HTTP code mapping

**Context**. The existing intouch-api-v3 exception → HTTP mapping in `TargetGroupErrorAdvice` has no `409 Conflict` handler; `NotFoundException` maps to `200 OK` with an error envelope (platform quirk, OQ-45); all validation errors map to `400`.

**Evidence** (C7): `code-analysis-intouch-api-v3.md` §3 and §6, `TargetGroupErrorAdvice.java`.

**Decision** (D-31 / RF-2 resolved — restated):
- **NEW class** `com.capillary.intouchapiv3.exceptionResources.ConflictException` (or equivalent package per existing convention).
- **NEW `@ExceptionHandler(ConflictException.class)`** in `TargetGroupErrorAdvice` returning `ResponseEntity<ResponseWrapper<String>>` with `HttpStatus.CONFLICT (409)` + populated `ApiError{code, message}`.
- **Thrift boundary contract**: EMF throws `PointsEngineRuleServiceException` with `setStatusCode(409)` for D-27 (PUT/DELETE on inactive), D-28 (active-duplicate POST), and ADR-003 facade-side cross-program `slab_id` rejections, and ADR-002 reactivation-name-collision.
- **Facade `BenefitCategoryFacade`** catches `EMFThriftException` / `PointsEngineRuleServiceException`, checks `statusCode == 409`, rethrows `ConflictException`. Other status codes rethrow as current `NotFoundException`, `InvalidInputException`, etc. per existing patterns.

**HTTP code table** for the 6 endpoints:

| HTTP | When |
|------|------|
| 200 OK | GET by id (success), GET list (success), PUT (success) |
| 201 Created | POST (success) |
| 204 No Content | PATCH /activate (success OR idempotent no-op); PATCH /deactivate (success OR idempotent no-op) |
| 400 Bad Request | Bean Validation failure (@NotNull / @Size / @Pattern), `InvalidInputException` from facade (body parse errors, malformed slabId list) |
| 200 + error body | `NotFoundException` — platform quirk (OQ-45); GET by id not-found returns `200 + ResponseWrapper{data=null, errors=[{code=NOT_FOUND, message=...}]}` per existing `TargetGroupErrorAdvice` pattern; MUST be called out in `/api-handoff` |
| 409 Conflict | `ConflictException`: `NAME_TAKEN_ACTIVE` (D-28 create/update duplicate), `NAME_TAKEN_ON_REACTIVATE` (ADR-002 clause e), `STATE_CONFLICT_INACTIVE` (D-27 PUT on inactive), `CROSS_PROGRAM_SLAB` (ADR-003 slabId not in program), `UNKNOWN_SLAB` (ADR-003 slabId not in program_slabs at all) |
| 500 Internal Server Error | any unmapped `Throwable` — matches existing `TargetGroupErrorAdvice` |

**Error codes** (facade-emitted, surfaced as `ApiError{code, message}`):
- `BC_NAME_REQUIRED` (400) — missing name
- `BC_NAME_LENGTH` (400) — name exceeds VARCHAR(255)
- `BC_SLAB_IDS_REQUIRED` (400) — empty or null on Create
- `BC_NAME_TAKEN_ACTIVE` (409) — active name duplicate in program
- `BC_CROSS_PROGRAM_SLAB` (409) — slabId belongs to a different program
- `BC_UNKNOWN_SLAB` (409) — slabId does not exist for org
- `BC_INACTIVE_WRITE_FORBIDDEN` (409) — PUT/DELETE on is_active=false row
- `BC_NAME_TAKEN_ON_REACTIVATE` (409) — reactivation name collision
- `BC_NOT_FOUND` (200 + error body, platform quirk) — id not found

**Confidence**: C7 — D-31 frozen; codes derived from ADR-001..004 semantics.

---

### ADR-010 — Authorization model (CONFIRMED by D-37)

> **STATUS: CONFIRMED by user decision D-37 (Phase 6 gate Q1)** — no admin-only gate in MVP; BasicAndKey is the write-auth pattern.

**Context**. OQ-34 / RF-4: writes on benefit categories — admin-only, or any authenticated caller? Existing intouch-api-v3 has KeyOnly (GET-only), BasicAndKey (writes), IntegrationsClient (OAuth) auth flows. Only `/v3/admin/authenticate` uses `@PreAuthorize("hasRole('ADMIN_USER')")`.

**Evidence** (C7): `code-analysis-intouch-api-v3.md` §5 auth flows.

**Decision** (confirmed C6 post-D-37):
- GET endpoints (`GET by id`, `GET list`): accept `KeyOnly` OR `BasicAndKey` auth. Any authenticated client with a valid key/basic token in the caller's org can read — matches platform convention for read endpoints.
- Write endpoints (`POST`, `PUT`, `PATCH /activate`, `PATCH /deactivate`): require `BasicAndKey` auth. **No `@PreAuthorize('ADMIN_USER')`** gate in MVP — matches legacy `/benefits`, `UnifiedPromotionController`, `TargetGroupController`. Admin-only enforcement is a deferred concern (separate epic); if ever needed, a one-line `@PreAuthorize` per endpoint suffices.
- **Tenant isolation** (G-07.1 / G-07.2): `orgId` extracted from `IntouchUser.getOrgId()` in controller, passed as method arg to facade → Thrift client → `@MDCData(orgId = "#orgId")` on handler → `ShardContext.set(orgId)` ThreadLocal. All DAO queries take `orgId` as an explicit method parameter (platform convention — NO `@Filter`/`@Where`).
- **Cross-tenant IT** (G-07.4): Phase 9 SDET MUST add an integration test that creates a category as org A and asserts a GET as org B returns `NOT_FOUND` (not 200 with the row). C-25 / OQ-34 satisfied.

**Confidence**: C6 post-D-37 — user confirmed the platform-default; no admin-role gate in MVP.

---

### ADR-011 — Pagination strategy on `GET /v3/benefitCategories`

**Context**. G-04.2 mandates bounded list endpoints. D-26 caps at ≤50 categories per program — offset pagination is safe at this scale.

**Decision**.
- Query params: `?programId=...&isActive=true|false|all&page=0&size=50`
- `page`: 0-indexed; default `0`
- `size`: default `50`; max `100` (enforced at controller; exceeding → HTTP 400 `BC_PAGE_SIZE_EXCEEDED`)
- `isActive=all` returns active + inactive; default `active` only
- Response body carries `{data: List<BenefitCategoryResponse>, page, size, total}` inside `ResponseWrapper.data` as a wrapper object.
- Sort: fixed `ORDER BY created_on DESC, id DESC` for deterministic pagination.

**Rejected** — cursor pagination: unnecessary at ≤50 rows per program; introduces complexity without benefit.

**Confidence**: C5 — simple offset fits D-26 envelope; deferred to Phase 7 Designer to finalize wrapper shape.

---

### ADR-012 — Uniqueness-among-active enforcement: app-level check ONLY; race ACCEPTED at D-26 scale (AMENDED by D-38)

> **STATUS: AMENDED post-HLD by user decision D-38 (Phase 6 gate Q2)**. Original proposal mandated a MySQL `GET_LOCK` advisory lock around the check-then-insert. User chose option B (accept the race at D-26 SMALL scale) for consistency with the D-33 philosophy. Advisory lock and `BC_NAME_LOCK_TIMEOUT` error code are STRICKEN from MVP.

**Context**. D-28 chose app-level uniqueness (no DB UNIQUE) → OQ-42 flagged the concurrent-POST race. At D-26 scale (<1 QPS writes), the race window is small; the decision is whether to mitigate or accept.

**Decision** (post-amendment, C6):
- **Primary enforcement**: Facade-side check — `SELECT 1 FROM benefit_categories WHERE org_id=? AND program_id=? AND name=? AND is_active=true` before INSERT / before UPDATE (exclude self for UPDATE). If non-empty → throw `ConflictException(BC_NAME_TAKEN_ACTIVE)`.
- **Race mitigation**: NONE in MVP. The `SELECT check → INSERT` race is **accepted** per D-38.
  - Rationale: D-26 admin-write QPS <1/s → collision probability is vanishingly small; advisory-lock ceremony (`GET_LOCK` + 2s timeout + new error code `BC_NAME_LOCK_TIMEOUT`) adds MySQL-level complexity and a new failure mode for a race that is unlikely to materialize; consistent with D-33 philosophy (accept small-scale risk if ceremony > probable harm).
- **Revisit triggers** (logged for monitoring): (a) admin write QPS exceeds 5/sec sustained; (b) ≥1 real duplicate-name incident reported in production logs; (c) product requirement change mandates strict uniqueness guarantee.
- **Future remediation options** (NOT IMPLEMENTED in MVP — kept as ADR notes for Phase 12 runbook):
  - **Option A**: `CREATE UNIQUE INDEX uniq_bc_active ON benefit_categories (org_id, program_id, name) WHERE is_active = 1` — partial unique index. Requires **Aurora MySQL ≥ 8.0.13** (D-40 — version confirmation deferred to Phase 12 deployment runbook).
  - **Option B**: `GET_LOCK(CONCAT('bc_uniq_', :orgId, '_', :programId, '_', MD5(:name)), 2)` advisory lock — works on any MySQL version. Adds `BC_NAME_LOCK_TIMEOUT` error code.
  - Deployment runbook (Phase 12) MUST document the version-check + decision gate.

**Rejected**. (a) Advisory lock in MVP — user chose B in D-38; ceremony > probable harm at D-26 scale. (b) Partial unique index in MVP — conditional on Aurora version; deferred (D-40).

**Consequences**.
- *Positive*: zero MySQL-level ceremony; facade path is a simple check-then-INSERT; no new error code.
- *Negative*: accepted deviation from G-10.5. If a real collision occurs in production, two rows with the same `(org_id, program_id, name, is_active=true)` can coexist until detected; admin-side remediation would be manual.
- *Accepted*: deviation logged with revisit-triggers; R-03 (uniqueness race) risk-register severity lowered to MEDIUM with explicit accepted-flag (mirror of R-01 LWW treatment).

**Confidence**: C6 post-D-38 — user decision; internally consistent with D-33.

**Guardrail posture**: G-10.5 — **accepted deviation** (was "mitigated via advisory lock" in original ADR; amended to "accepted at D-26 scale" per D-38).

---

### ADR-013 — Deployment sequencing

**Context**. Four repos touched: thrift-ifaces-pointsengine-rules (IDL), emf-parent (handler + service + DAO + DDL), intouch-api-v3 (facade + controller + DTOs), cc-stack-crm (DDL submodule). Wrong release order causes `TApplicationException: unknown method` (RF-1).

**Evidence** (C7): D-32 submodule workflow; `cross-repo-trace.md` §7 / RF-1.

**Decision** (release sequence, strict):

1. **cc-stack-crm** — PR with `benefit_categories.sql` + `benefit_category_slab_mapping.sql`; merge to `master`.
2. **thrift-ifaces-pointsengine-rules** — bump `pom.xml` to `1.84` release, tag `v1.84`; publish to internal Maven repo.
3. **emf-parent**
   a. Bump `.gitmodules` submodule pointer to cc-stack-crm post-merge commit.
   b. Bump `pom.xml` dep `thrift-ifaces-pointsengine-rules:1.84`.
   c. Add entity + DAO + service + handler code.
   d. Deploy to production FIRST.
4. **intouch-api-v3**
   a. Bump `pom.xml` dep `thrift-ifaces-pointsengine-rules:1.84`.
   b. Add `ConflictException`, `BenefitCategoryFacade`, `BenefitCategoryController`, DTOs.
   c. Deploy to production AFTER emf-parent.
5. **Production Aurora DDL application** — Facets Cloud auto-sync vs manual DBA script (OQ-46 / Q-CRM-1 remainder) — Phase 12 Blueprint deployment runbook finalizes.

**Rollback**: each step has a clean rollback (revert commit, redeploy previous version). intouch-api-v3 can be rolled back without affecting emf-parent; emf-parent rollback requires thrift-ifaces downgrade only if the IDL is breaking (no breaking methods in this release — all additions).

**Feature flags**: NOT required — endpoints are purely additive; zero existing endpoint is modified; worst case if deploy is broken, the endpoints simply return errors.

**Confidence**: C7 — standard Capillary deployment order; RF-1 explicit.

---

## 4. System Context Diagram

Shows the end-to-end request path from external Client to MySQL, including tenant context extraction and schema ownership.

```mermaid
flowchart LR
    Client[External Capillary Client<br/>HTTP + Basic/Key/OAuth]
    subgraph IntouchApiV3["intouch-api-v3 (Spring MVC)"]
        REST[BenefitCategoryController<br/>@RestController<br/>/v3/benefitCategories]
        Auth[AuthN Filter<br/>IntouchUser.orgId extracted<br/>from token/cookie]
        Facade[BenefitCategoryFacade]
        ThriftClient[PointsEngineRulesThriftService<br/>RPCService.rpcClient<br/>host=emf-thrift-service<br/>port=9199<br/>timeout=60s]
        Advice[TargetGroupErrorAdvice<br/>+ConflictException->409]
    end
    subgraph EmfParent["emf-parent (Spring + Thrift)"]
        Handler[PointsEngineRuleConfigThriftImpl<br/>@ExposedCall pointsengine-rules<br/>@Trace @MDCData orgId=#orgId]
        Aspect[ExposedCallAspect<br/>ShardContext.set orgId]
        Editor[PointsEngineRuleEditorImpl]
        Service[PointsEngineRuleService<br/>@Transactional warehouse]
        CatDao[BenefitCategoryDao]
        MapDao[BenefitCategorySlabMappingDao]
        SlabDao[PeProgramSlabDao]
    end
    subgraph Data["cc-stack-crm schema / MySQL warehouse"]
        T1[(benefit_categories)]
        T2[(benefit_category_slab_mapping)]
        T3[(program_slabs)]
    end
    ThriftIDL[(thrift-ifaces-pointsengine-rules<br/>pointsengine_rules.thrift v1.84)]

    Client -->|HTTPS /v3/benefitCategories| Auth
    Auth --> REST
    REST --> Facade
    Facade --> ThriftClient
    ThriftClient -->|Thrift binary over 9199| Handler
    Handler --> Aspect
    Aspect --> Editor
    Editor --> Service
    Service --> CatDao
    Service --> MapDao
    Service --> SlabDao
    CatDao --> T1
    MapDao --> T2
    SlabDao --> T3
    Advice -.-> REST
    ThriftIDL -.IDL dep.-> Handler
    ThriftIDL -.IDL dep.-> ThriftClient
```

**Tenant context**: extracted by `AuthN Filter` from request (Basic auth / clientKey / OAuth) into `IntouchUser.orgId`; passed as explicit method arg down to the Thrift call; picked up by `@MDCData(orgId = "#orgId")` on the handler, which sets `ShardContext.set(orgId)` ThreadLocal (G-07.2).

---

## 5. Write Path Sequence Diagrams

### 5.1 Create flow

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Ctrl as BenefitCategoryController
    participant Fac as BenefitCategoryFacade
    participant TS as PointsEngineRulesThriftService<br/>(Thrift client)
    participant Hdl as PointsEngineRuleConfigThriftImpl
    participant Ed as PointsEngineRuleEditorImpl
    participant Svc as PointsEngineRuleService<br/>@Transactional(warehouse)
    participant CatDao as BenefitCategoryDao
    participant MapDao as BenefitCategorySlabMappingDao
    participant SlabDao as PeProgramSlabDao

    Client->>Ctrl: POST /v3/benefitCategories { programId, name, slabIds:[1,2,3] }
    Ctrl->>Ctrl: Bean Validation (@NotBlank name, @NotNull @Size(min=1) slabIds, @Positive)
    Ctrl->>Ctrl: Extract orgId from IntouchUser
    Ctrl->>Fac: create(orgId, programId, name, slabIds, actor)
    Fac->>Fac: Convert to Thrift struct BenefitCategoryDto
    Fac->>TS: createBenefitCategory(orgId, dto)
    TS->>Hdl: RPC
    Hdl->>Ed: create(orgId, dto)
    Ed->>Svc: create(orgId, dto, actor)
    Svc->>CatDao: findActiveByProgramAndName(orgId, programId, name)
    Note right of Svc: No advisory lock (D-38<br/>race accepted at D-26 scale)
    CatDao-->>Svc: empty
    Svc->>Svc: dedup slabIds via LinkedHashSet
    Svc->>SlabDao: findExistingSlabIds(orgId, programId, slabIds)
    SlabDao-->>Svc: [1,2,3] all present
    Svc->>CatDao: INSERT benefit_categories (org_id, program_id, name, category_type='BENEFITS', is_active=1, created_on=UTC, created_by=actor)
    CatDao-->>Svc: newId=42
    Svc->>MapDao: INSERT benefit_category_slab_mapping for each slabId (org_id, benefit_category_id=42, slab_id, is_active=1, audit)
    Svc-->>Ed: BenefitCategoryDto { id:42, ... }
    Ed-->>Hdl: dto
    Hdl-->>TS: dto
    TS-->>Fac: dto
    Fac-->>Ctrl: Response { id:42, ..., createdOn=ISO-8601 UTC }
    Ctrl-->>Client: 201 Created + ResponseWrapper(dto)
```

### 5.2 Update flow (diff-and-apply) — see ADR-003 diagram

(See ADR-003 section above for full sequence.)

### 5.3 Activate flow — see ADR-002 diagram

(See ADR-002 section above for full sequence.)

### 5.4 Deactivate flow (cascade) — see ADR-004 diagram

(See ADR-004 section above for full sequence.)

---

## 6. Read Path Sequence Diagrams

### 6.1 GET by id

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Ctrl as BenefitCategoryController
    participant Fac as BenefitCategoryFacade
    participant TS as Thrift client
    participant Hdl as Thrift handler
    participant Svc as PointsEngineRuleService
    participant CatDao as BenefitCategoryDao
    participant MapDao as BenefitCategorySlabMappingDao

    Client->>Ctrl: GET /v3/benefitCategories/42
    Ctrl->>Fac: get(orgId=100, id=42)
    Fac->>TS: getBenefitCategory(orgId, 42)
    TS->>Hdl: RPC
    Hdl->>Svc: get(orgId, 42)
    Svc->>CatDao: findById(orgId, 42)
    alt Not found
        CatDao-->>Svc: empty
        Svc-->>Hdl: throw PointsEngineRuleServiceException(404, NOT_FOUND)
        Hdl-->>TS: Exception(status=404)
        TS-->>Fac: EMFThriftException
        Fac-->>Ctrl: throw NotFoundException
        Ctrl-->>Client: 200 + ResponseWrapper(errors=[NOT_FOUND]) (platform quirk)
    else Found
        CatDao-->>Svc: cat
        Svc->>MapDao: findActiveSlabIds(orgId, 42)
        MapDao-->>Svc: [1,3,5]
        Svc-->>Hdl: BenefitCategoryDto { id:42, slabIds:[1,3,5], ... }
        Hdl-->>Client: 200 + ResponseWrapper(dto)
    end
```

### 6.2 GET list (paginated)

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Ctrl as BenefitCategoryController
    participant Fac as BenefitCategoryFacade
    participant TS as Thrift client
    participant Hdl as Thrift handler
    participant Svc as PointsEngineRuleService
    participant CatDao as BenefitCategoryDao
    participant MapDao as BenefitCategorySlabMappingDao

    Client->>Ctrl: GET /v3/benefitCategories?programId=5&isActive=true&page=0&size=50
    Ctrl->>Ctrl: Bean Validation (page>=0, size<=100)
    Ctrl->>Fac: list(orgId=100, filter={programId:5, isActive:true}, page, size)
    Fac->>TS: listBenefitCategories(orgId, filter, page, size)
    TS->>Hdl: RPC
    Hdl->>Svc: list(orgId, filter, page, size)
    Svc->>CatDao: findPaged(orgId, programId, isActive, page, size) ORDER BY created_on DESC, id DESC
    CatDao-->>Svc: [cat1, cat2, ...]
    Svc->>CatDao: countByFilter(orgId, programId, isActive)
    CatDao-->>Svc: total=17
    Svc->>MapDao: findActiveSlabIdsForCategories(orgId, [cat1.id, cat2.id, ...])
    Note over Svc,MapDao: Single bulk query — NO N+1 (G-04.1)
    MapDao-->>Svc: map {catId -> List<slabId>}
    Svc-->>Hdl: { data:[dto1, dto2, ...], page:0, size:50, total:17 }
    Hdl-->>Ctrl: 200 + ResponseWrapper(listPayload)
    Ctrl-->>Client: 200
```

---

## 7. Data Model

### 7.1 DDL — `benefit_categories`

```sql
CREATE TABLE `benefit_categories` (
  `id`                INT(11)        NOT NULL AUTO_INCREMENT,
  `org_id`            INT(11)        NOT NULL DEFAULT '0',
  `program_id`        INT(11)        NOT NULL,
  `name`              VARCHAR(255)   NOT NULL,
  `category_type`     ENUM('BENEFITS') NOT NULL DEFAULT 'BENEFITS',
  `is_active`         TINYINT(1)     NOT NULL DEFAULT 1,
  `created_on`        DATETIME       NOT NULL,
  `created_by`        INT(11)        NOT NULL,
  `updated_on`        DATETIME       DEFAULT NULL,
  `updated_by`        INT(11)        DEFAULT NULL,
  `auto_update_time`  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`, `org_id`),
  KEY `idx_bc_org_program` (`org_id`, `program_id`),
  KEY `idx_bc_org_program_active` (`org_id`, `program_id`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- NO `version` column (ADR-001).
-- NO DB UNIQUE on (org_id, program_id, name) — app-level (D-28 + ADR-012).
-- No declared FOREIGN KEY — logical FK to program_slabs.id (app enforces + platform convention).
```

### 7.2 DDL — `benefit_category_slab_mapping`

```sql
CREATE TABLE `benefit_category_slab_mapping` (
  `id`                   INT(11)      NOT NULL AUTO_INCREMENT,
  `org_id`               INT(11)      NOT NULL DEFAULT '0',
  `benefit_category_id`  INT(11)      NOT NULL,
  `slab_id`              INT(11)      NOT NULL,
  `is_active`            TINYINT(1)   NOT NULL DEFAULT 1,
  `created_on`           DATETIME     NOT NULL,
  `created_by`           INT(11)      NOT NULL,
  `updated_on`           DATETIME     DEFAULT NULL,
  `updated_by`           INT(11)      DEFAULT NULL,
  `auto_update_time`     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`, `org_id`),
  KEY `idx_bcsm_org_cat_active` (`org_id`, `benefit_category_id`, `is_active`),
  KEY `idx_bcsm_org_slab_active` (`org_id`, `slab_id`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- NO `version` column (ADR-001).
-- No declared FOREIGN KEY — logical FK (platform convention).
```

### 7.3 ER Diagram

```mermaid
erDiagram
    BENEFIT_CATEGORIES ||--o{ BENEFIT_CATEGORY_SLAB_MAPPING : "has active mappings (logical FK on benefit_category_id+org_id)"
    PROGRAM_SLABS ||--o{ BENEFIT_CATEGORY_SLAB_MAPPING : "is referenced by (logical FK on slab_id+org_id)"
    BENEFIT_CATEGORIES {
        INT id PK
        INT org_id PK
        INT program_id "logical FK -> program_slabs.program_id"
        VARCHAR name "app-unique among active (org_id,program_id,name)"
        ENUM category_type "single value BENEFITS"
        TINYINT is_active "soft-delete flag"
        DATETIME created_on
        INT created_by
        DATETIME updated_on "nullable"
        INT updated_by "nullable"
        TIMESTAMP auto_update_time "DB managed"
    }
    BENEFIT_CATEGORY_SLAB_MAPPING {
        INT id PK
        INT org_id PK
        INT benefit_category_id "logical FK -> benefit_categories.id"
        INT slab_id "logical FK -> program_slabs.id"
        TINYINT is_active "soft-delete flag"
        DATETIME created_on
        INT created_by
        DATETIME updated_on "nullable"
        INT updated_by "nullable"
        TIMESTAMP auto_update_time "DB managed"
    }
    PROGRAM_SLABS {
        INT id PK "existing table - unchanged"
        INT org_id PK
        INT program_id
        VARCHAR name
    }
```

**Explicit call-outs**:
- NO `version` column on either new table (ADR-001).
- NO declared FOREIGN KEYs — logical FKs only (platform convention, G-12.2).
- NO `tier_applicability` column on `benefit_categories` — junction table is the source of truth (D-21).
- NO `trigger_event` column (D-07).

---

## 8. API Contract Summary Table

Base path: `/v3/benefitCategories`. All requests/responses wrapped in `ResponseWrapper<T>{data, errors, warnings}`.

| # | Method | Path | Request Body | Success Response | Error Codes |
|---|--------|------|--------------|------------------|-------------|
| 1 | POST | `/v3/benefitCategories` | `{programId, name, slabIds:[int]}` | 201 Created + BenefitCategoryResponse | 400 (`BC_NAME_REQUIRED`, `BC_NAME_LENGTH`, `BC_SLAB_IDS_REQUIRED`), 409 (`BC_NAME_TAKEN_ACTIVE`, `BC_CROSS_PROGRAM_SLAB`, `BC_UNKNOWN_SLAB`), 500 |
| 2 | PUT | `/v3/benefitCategories/{id}` | `{name, slabIds:[int]}` | 200 OK + BenefitCategoryResponse | 400, 409 (`BC_NAME_TAKEN_ACTIVE`, `BC_CROSS_PROGRAM_SLAB`, `BC_UNKNOWN_SLAB`, `BC_INACTIVE_WRITE_FORBIDDEN`), 200+error (`BC_NOT_FOUND`), 500 |
| 3 | GET | `/v3/benefitCategories/{id}` | — | 200 OK + BenefitCategoryResponse | 200+error (`BC_NOT_FOUND` platform quirk), 500 |
| 4 | GET | `/v3/benefitCategories?programId=&isActive=&page=&size=` | — | 200 OK + `{data:[], page, size, total}` | 400 (`BC_PAGE_SIZE_EXCEEDED`), 500 |
| 5 | PATCH | `/v3/benefitCategories/{id}/activate` | — | **200 OK + BenefitCategoryResponse** (D-39 — on state change) / **204 No Content** (on idempotent already-active) | 200+error (`BC_NOT_FOUND`), 409 (`BC_NAME_TAKEN_ON_REACTIVATE`), 500 |
| 6 | PATCH | `/v3/benefitCategories/{id}/deactivate` | — | 204 No Content (on state change OR idempotent already-inactive — per ADR-006) | 200+error (`BC_NOT_FOUND`), 500 |

**DTO: `BenefitCategoryResponse`** (JSON):
```json
{
  "id": 42,
  "orgId": 100,
  "programId": 5,
  "name": "VIP Perks",
  "categoryType": "BENEFITS",
  "slabIds": [1, 3, 5],
  "isActive": true,
  "createdOn": "2026-04-18T10:30:00.000Z",
  "createdBy": 7,
  "updatedOn": "2026-04-18T11:45:00.000Z",
  "updatedBy": 7
}
```

**DTO: `BenefitCategoryRequest` (POST/PUT)**:
```json
{
  "programId": 5,         // POST only; PUT omits (URL path carries id)
  "name": "VIP Perks",
  "slabIds": [1, 3, 5]
}
```

---

## 9. Thrift IDL Delta

Target file: `pointsengine_rules.thrift` in `thrift-ifaces-pointsengine-rules` repo. Version bump `1.83 → 1.84`. All new additions — zero breaking changes (G-09.5 compliant).

**New enum**:
```thrift
enum BenefitCategoryType {
  BENEFITS = 1
}
```

**New structs**:
```thrift
struct BenefitCategoryDto {
  1: optional i32 id,                     // absent on Create, present on responses
  2: required i32 orgId,
  3: required i32 programId,
  4: required string name,
  5: required BenefitCategoryType categoryType = BenefitCategoryType.BENEFITS,
  6: required list<i32> slabIds,
  7: required bool isActive,
  8: required i64 createdOn,              // epoch millis UTC
  9: required i32 createdBy,
  10: optional i64 updatedOn,
  11: optional i32 updatedBy
}

struct BenefitCategoryFilter {
  1: required i32 orgId,
  2: optional i32 programId,
  3: optional bool isActive               // null = active only; true/false explicit
}

struct BenefitCategoryListResponse {
  1: required list<BenefitCategoryDto> data,
  2: required i32 page,
  3: required i32 size,
  4: required i64 total
}
```

**New methods on existing `PointsEngineRuleService`** (add to service block; 4 methods):
```thrift
BenefitCategoryDto createBenefitCategory(
    1: required i32 orgId,
    2: required BenefitCategoryDto dto,
    3: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategoryDto updateBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: required BenefitCategoryDto dto,    // name + slabIds only; others ignored
    4: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategoryDto getBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategoryListResponse listBenefitCategories(
    1: required BenefitCategoryFilter filter,
    2: required i32 page,
    3: required i32 size
) throws (1: PointsEngineRuleServiceException ex);

void activateBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);

void deactivateBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);
```

**Method count**: 6 (4 CRUD + 2 state-transition). ADR-003 absorbed mapping CRUD into parent struct → 0 mapping-specific methods. Consistent with the `BenefitsConfigData` CRUD pattern at lines 1276-1282 of the existing IDL.

**Exception reuse**: The existing `PointsEngineRuleServiceException { 1: required string errorMessage; 2: optional i32 statusCode; }` carries HTTP-analogue status codes (400/404/409/500). No new exception struct.

---

## 10. Cross-Repo Change Map

| Repo | New Files | Modified Files | Why |
|------|-----------|----------------|-----|
| **thrift-ifaces-pointsengine-rules** | 0 | 2: `pointsengine_rules.thrift` (structs + 6 methods), `pom.xml` (1.84-SNAPSHOT → 1.84 release) | Single-IDL, single-service repo; add to existing `PointsEngineRuleService` (no new service). |
| **emf-parent** | 6+: `BenefitCategory.java`, `BenefitCategoryPK.java` (inner `@Embeddable`), `BenefitCategorySlabMapping.java`, `BenefitCategorySlabMappingPK.java`, `BenefitCategoryDao.java`, `BenefitCategorySlabMappingDao.java`, plus 2 new DDL snapshots in `integration-test/.../cc-stack-crm/schema/dbmaster/warehouse/` | 3: `PointsEngineRuleConfigThriftImpl.java` (+6 `@Override @Trace @MDCData` handler methods, ADR-005), `PointsEngineRuleEditorImpl.java` (+6 delegation methods), `PointsEngineRuleService.java` (+6 `@Transactional` service methods incl. `syncSlabMappings`, cascade), `pom.xml` (thrift dep bump 1.83 → 1.84), `.gitmodules` pointer bump (D-32) | Owns entity + handler + transactional boundary + cascade logic (C-16). |
| **intouch-api-v3** | 7+: `BenefitCategoryController.java`, `BenefitCategoryFacade.java`, `PointsEngineRuleThriftService.java` (if not extending existing — likely reuse `PointsEngineRulesThriftService`), `BenefitCategoryRequest.java`, `BenefitCategoryResponse.java`, `BenefitCategoryListResponse.java`, `ConflictException.java` (D-31) | 2: `TargetGroupErrorAdvice.java` (add `@ExceptionHandler(ConflictException.class)` → 409), `pom.xml` (thrift dep bump 1.83 → 1.84) | Thin REST facade; `RPCService.rpcClient("emf-thrift-service", 9199, 60000)`; Bean Validation; Jackson UTC ISO-8601. |
| **cc-stack-crm** | 2: `schema/dbmaster/warehouse/benefit_categories.sql`, `schema/dbmaster/warehouse/benefit_category_slab_mapping.sql` | 0 for MVP | DDL home. No Java; no pom.xml; no dispatcher registrations. `org_mirroring_meta` / `cdc_source_table_info` deferred (Q-CRM-1/2). |
| **kalpavriksha** | 0 | 0 | Docs-only repo. |

**Summary**: 4 active repos, 15+ new files, 7 modified files.

---

## 11. Risk Register

| # | Risk | Severity | Likelihood | Mitigation | Owner | Revisit Trigger |
|---|------|----------|------------|------------|-------|-----------------|
| R-01 | Last-write-wins silently loses an admin's edit (ADR-001 / G-10 accepted deviation) | M | L (at D-26 scale) | None — accepted. Audit columns record who last wrote. | Product / Tech Lead | admin QPS >10/sec per tenant; multi-editor Admin UI ships; any "concurrent-write-conflict" incident |
| R-02 | Thrift IDL deployment out of order (`TApplicationException: unknown method`) | CRITICAL | L | ADR-013 strict sequence; release coordination in Phase 12 Blueprint | Release Eng | post each deploy |
| R-03 | App-level name uniqueness check races (OQ-42 / ADR-012) — **accepted deviation per D-38** | **M (was HIGH; lowered per D-38 accepted-deviation)** | L (at D-26 scale) | **None — accepted.** No advisory lock, no partial unique index. Rationale: D-26 scale makes collision improbable; consistent with D-33 philosophy. Future remediation (advisory lock OR partial unique index) documented in ADR-012 for post-GA revisit. | Product / Tech Lead | admin QPS >5/sec sustained; ≥1 duplicate-active-row incident observed in prod logs |
| R-04 | JVM default TZ in production not UTC → `Date ↔ i64` drifts (OQ-38) | H | M | ADR-008 forces UTC in conversion; Phase 9 multi-TZ IT (UTC + IST + US/Eastern, G-11.7) | Designer / SDET / Ops | Phase 5 ops confirmation of prod TZ |
| R-05 | Cross-tenant leak (G-07.1 by-convention enforcement) | CRITICAL | L (convention-enforced) | ADR-010 explicit `orgId` arg on every DAO method; Phase 9 cross-tenant IT (G-11.8) | Designer / SDET | Any bug tagged "cross-tenant data leak" |
| R-06 | Cascade-deactivate transaction locks mapping rows during bulk UPDATE (ADR-004) | L | L (D-26: max 20 mappings per cat) | Single-shot bulk UPDATE completes in ms at this scale; `@Transactional(warehouse)` rollback on failure | Service layer | Scale exceeds D-26 envelope |
| R-07 | 409 Conflict new path in intouch-api-v3 (new `ConflictException`) integrates cleanly with existing `TargetGroupErrorAdvice` | L | L | Compile-time / test-time verification; follows existing `InvalidInputException` / `NotFoundException` pattern | Designer / Developer | n/a |
| R-08 | `NotFoundException → HTTP 200` platform quirk surprises API consumers (OQ-45) | L | M | Explicit call-out in `/api-handoff` doc; API consumers instructed to check `errors[]` array | API handoff | Product opts to fix platform quirk in a separate ticket |
| R-09 | Production Aurora DDL apply mechanism ambiguous (Q-CRM-1 / A-CRM-4) | M | L | Deferred to Phase 12 Blueprint deployment runbook; dev/IT flow proven via D-32 submodule | Ops / Release Eng | Phase 12 runbook definition |
| R-10 | `BenefitCategory` name collision risk with legacy `Benefits` in code-reading / future refactoring | L | M | Separate package + separate table prefix (`benefit_categories` vs `benefits`); glossary entry in api-handoff | Designer / Reviewer | n/a |
| R-11 | Client-facing naming: `slabIds` exposed in API JSON while BRD says "tier" | L | H | Glossary entry in `/api-handoff` mapping "slab" = "tier" for Client comprehension (D-22) | API handoff | Product requests rename — would be a contract change |
| R-12 | No cache on day 1 (OQ-30 deferred by D-26) | L | L (<10 QPS read) | Add caching only on post-GA telemetry evidence | Ops | Read QPS exceeds 10/sec per tenant |

**Summary** (post-D-38 amendment): 2 CRITICAL, **2 HIGH** (was 3 — R-03 lowered), **5 MEDIUM** (was 4), 3 LOW. 12 total risks. Two explicit accepted deviations with revisit-triggers: R-01 (LWW) and R-03 (uniqueness race).

---

## 12. Open Questions for Phase 7 (Designer)

Decisions deliberately kept out of HLD and passed to Designer:

1. **Q7-01** — Name normalization rules (OQ-43): `trim()` yes/no, case sensitivity for the app-level uniqueness check (`LOWER(name)` vs raw), max length (`VARCHAR(255)` declared above is the upper bound — Designer may choose `120`), empty string vs NULL handling, Unicode NFC normalization for emoji/accents. Platform convention in `benefits.name` or `promotions.name` is the reference.
2. **Q7-02** — Advisory-lock key hashing format: `md5(name)` chosen above because raw `name` could exceed MySQL lock-name length; Designer validates MySQL 5.7/8.0 lock-name limits and picks final format.
3. **Q7-03** — Exact facade class name: `BenefitCategoryFacade` proposed; Designer confirms against existing naming convention (some facades are `*Service`, some `*Facade`).
4. **Q7-04** — Exact controller package path: proposed `com.capillary.intouchapiv3.resources.BenefitCategoryController`; Designer confirms under the existing `/resources` or `/controllers` convention.
5. **Q7-05** — GET list response wrapper shape: pagination fields (`page, size, total`) inside `ResponseWrapper.data` as a wrapper object, OR outside as separate `ResponseWrapper` fields? Pattern-match against existing `MilestoneController` / `TargetGroupController` list endpoints.
6. **Q7-06** — Thrift field naming convention: bare `createdOn` (pointsengine_rules.thrift convention) vs `createdOnInMillis` (emf.thrift convention). Recommendation: bare, since new methods live in pointsengine_rules.thrift.
7. **Q7-07** — Activate-flow response body: ADR-002 defaults to `204 No Content` (ADR-006 pin); if product prefers the updated DTO, Designer can return `200 + dto` — minor contract tweak.
8. **Q7-08** — Cross-tenant IT fixture strategy (G-07.4 / G-11.8): Testcontainers with two orgs pre-seeded, or in-memory H2 with org switching? Follow Phase 9 SDET approach once chosen.
9. **Q7-09** — MySQL version confirmation (ADR-012): is Aurora MySQL ≥ 8.0.13 for partial unique index fallback?
10. **Q7-10** — Exact audit-column write strategy: manual `new Date()` in service code (platform pattern per `PointsEngineRuleService.createOrUpdateSlab` line 3669-3671) vs JPA `@PrePersist`/`@PreUpdate` lifecycle hooks. Platform pattern preferred.

---

## 13. Constraints that Propagate to Phase 7

Non-negotiables Phase 7 MUST honour:

1. **ADR-001 (from D-33)**: NO `@Version` on entity, NO `version` on DTO, NO DDL `version` column. Last-write-wins.
2. **ADR-002 (from D-34)**: Dedicated `PATCH /{id}/activate` endpoint. Does NOT auto-reactivate mappings. 409 on name-collision at reactivation. `activateBenefitCategory` Thrift method.
3. **ADR-003 (from D-35)**: `slabIds: List<Integer>` embedded in parent DTO. Server-side diff-and-apply. NO separate mapping REST resource. 5 endpoints on `/v3/benefitCategories` (6 paths with sub-paths). `list<i32> slabIds` in create/update Thrift structs.
4. **ADR-004 (from D-36)**: Dedicated `PATCH /{id}/deactivate` endpoint. Cascade to mappings in same transaction. `deactivateBenefitCategory` Thrift method.
5. **D-13 / C-15**: NO `DELETE` verb. Removal via PATCH `/deactivate` only.
6. **D-18 / D-19**: READ and WRITE paths go through the same Thrift chain. Transaction boundary in EMF `PointsEngineRuleService @Transactional(warehouse)`.
7. **D-22**: FK column is `slab_id`. Entity class = `BenefitCategory`. Junction entity = `BenefitCategorySlabMapping`.
8. **D-23 (as amended by D-30)**: Audit columns `created_on`, `created_by` (INT), `updated_on` (nullable), `updated_by` (nullable INT), `auto_update_time` (DB-managed). `_on` suffix, INT for actor ids.
9. **D-24 / ADR-008**: Three-boundary timestamp pattern. `Date`+`DATETIME` (EMF), `i64` millis (Thrift), ISO-8601 UTC (REST). Explicit UTC TimeZone in `Date ↔ i64` conversion.
10. **D-26**: Scale envelope SMALL (≤50 cat/prog, ≤20 slab/cat, ≤1000 rows per cascade, <10 QPS read, <1 QPS write).
11. **D-27** (as reworded by ADR-002): PUT on inactive = 409; reactivation via `/activate` ONLY.
12. **D-28 / ADR-012 (amended by D-38)**: App-level uniqueness among active rows. NO advisory lock, NO DB UNIQUE, NO partial unique index in MVP. Race accepted at D-26 scale with revisit-triggers.
13. **D-30**: `createdBy` / `updatedBy` = INT / `INT(11)` / `i32`.
14. **D-31 / ADR-009**: `ConflictException → 409`; `PointsEngineRuleServiceException.statusCode` is the Thrift-side carrier.
15. **G-07.1 / C-25**: Every DAO method takes `orgId` as an explicit parameter; `ShardContext.set(orgId)` in handler; cross-tenant IT required (Phase 9).
16. **G-04.1**: GET list must use bulk `findActiveSlabIdsForCategories(orgId, List<Integer>)` — NO N+1 on mapping fetch.
17. **G-06.3**: All error responses use the `ResponseWrapper{data, errors, warnings}` envelope (existing platform pattern — do NOT introduce a new envelope).
18. **ADR-013**: Deployment order cc-stack-crm → thrift-ifaces → emf-parent → intouch-api-v3.

---

## 14. Guardrail Compliance Matrix (G-01..G-12)

| ID | Priority | Status | Notes |
|----|----------|--------|-------|
| G-01 | CRITICAL | **partial — compliant at external contract; internal deviation accepted (G-12.2 parity)** | ADR-008 three-boundary pattern. External REST returns ISO-8601 UTC (G-01.6 ✓). Internal `java.util.Date`+`DATETIME` matches platform (G-12.2 ✓). Multi-TZ IT required (G-01.7 / R-04). |
| G-02 | HIGH | compliant | Bean Validation at REST (`@NotBlank`, `@Size`, `@Positive`); facade fails fast with `Objects.requireNonNull`; `ConflictException`/`InvalidInputException` are specific exception types (G-02.5). |
| G-03 | CRITICAL | compliant | Parameterized JPA queries (G-03.1); Bean Validation allow-list on DTO (G-03.2); AuthN via existing `BasicAndKey`/`KeyOnly` flows (G-03.3); no secrets committed (G-03.4); no PII in logs (G-03.5 — orgId + actorUserId only). |
| G-04 | HIGH | compliant | No N+1 (ADR GET list bulk fetch, G-04.1); paginated list (G-04.2, ADR-011); Thrift client timeout 60000ms (G-04.3); DB indexes on every WHERE clause (G-04.4 — ADR-007 idx_bc*, idx_bcsm*); single-txn cascade is bulk UPDATE (G-04.5); no cache day-1 (OQ-30 deferred, G-04.6 n/a). |
| G-05 | HIGH | **partial — G-05.2 accepted deviation** | G-05.1 wrapped in `@Transactional(warehouse)` ✓; **G-05.2 optimistic lock accepted deviation (ADR-001 / R-01)**; G-05.3 DB-level NOT NULL + TINYINT + DATETIME constraints ✓ (UNIQUE at app-level per D-28); G-05.4 migrations additive only (expand — never contract, no existing table touched); G-05.5 soft-delete everywhere ✓. |
| G-06 | HIGH | compliant | G-06.1 POST idempotency handled via app-level uniqueness check (ADR-012) — duplicate POST returns 409; `/activate`/`/deactivate` idempotent 204 (ADR-006); G-06.2 additive API ✓; G-06.3 structured errors via `ResponseWrapper.errors` ✓; G-06.4 correct codes (ADR-009); G-06.5 `/v3/` prefix ✓; G-06.6 ISO-8601 UTC ✓. |
| G-07 | CRITICAL | **mitigated-how** | G-07.1: platform uses convention (no `@Filter`) — mitigated by making `orgId` mandatory method arg on every DAO; cross-tenant IT required (G-07.4 / R-05 / Phase 9 SDET). G-07.2: `ShardContext.set(orgId)` via `@MDCData`. G-07.5: MDC includes `orgId` on every log line (via `@MDCData`). |
| G-08 | HIGH | compliant | G-08.1 SLF4J parameterized logs; G-08.2 MDC-propagated `requestId` + `orgId` via `@MDCData`; G-08.4 ERROR only for surprise states (unexpected exceptions); DEBUG for diff-and-apply details; G-08.6 New Relic via `@Trace(dispatcher=true)`. |
| G-09 | HIGH | compliant | All changes additive (G-09.1 ✓); G-09.5 Thrift structs add fields only, methods only — never remove/rename existing (IDL minor version bump 1.83 → 1.84). |
| G-10 | HIGH | **accepted-deviation (ADR-001) on G-10 (concurrency / optimistic lock); ALSO accepted-deviation (ADR-012 post-D-38) on G-10.5 (uniqueness race)** | R-01 documented; revisit-triggers explicit. G-10.5 — advisory lock rejected by user choice; race accepted at D-26 scale per D-38 with revisit-triggers logged (admin QPS >5/sec sustained OR ≥1 real duplicate incident). |
| G-11 | HIGH | compliant (pushed to Phase 8 QA / Phase 9 SDET) | G-11.7 multi-TZ tests; G-11.8 cross-tenant test; G-11.4 idempotency tests on `/activate` + `/deactivate`; G-11.5 concurrent-POST uniqueness test (ADR-012). Testcontainers for IT (G-11.3) per emf-parent IT convention. |
| G-12 | CRITICAL | compliant | G-12.1 all patterns cross-referenced to `code-analysis-*.md` evidence; G-12.2 follows platform `java.util.Date` + `OrgEntityIntegerPKBase` + `@ExposedCall` + `ResponseWrapper` patterns; G-12.3 method calls verified against code-analysis; G-12.4 simplest solution (no Strategy/Factory for 6 endpoints); G-12.5 zero refactor of surrounding code; G-12.6 no security controls disabled; G-12.10 reuses existing exception hierarchy (`InvalidInputException`, `NotFoundException`, new `ConflictException`). |

---

## 15. Summary

Five endpoints, four Thrift methods, two DDL files, one new exception class, one config-only feature. Architecture follows the canonical Capillary 4-layer pattern with zero structural novelty. The four frozen ADRs define the shape; ADR-005..013 fill in the remaining decisions with evidence-backed confidence. Transaction boundary, cascade, diff-and-apply, and idempotency are all pinned. Remaining Phase-7 choices are stylistic/naming — not structural. Ready for Designer.


---

## 16. Post-HLD Amendments (user decisions on Phase 6 gate Qs)

After the initial HLD was produced, 4 user-sign-off questions were posed (Q1..Q4 in the summary block). User answered **Q1:B, Q2:B, Q3:B, Q4:C** on 2026-04-18, producing decisions D-37..D-40. The affected ADRs have been amended in-place above; this section summarises the delta.

### D-37 (Q1: Authorization) — CONFIRMED ADR-010 default
- **User choice**: B (BasicAndKey; no admin-only gate in MVP)
- **Impact on ADR-010**: No change to decision; confidence upgraded from C5 to C6 with user confirmation.
- **Phase 7 impact**: `BenefitCategoriesV3Controller` uses `BasicAndKey` on writes, `KeyOnly OR BasicAndKey` on reads. No `@PreAuthorize` annotation.
- **Phase 8 impact**: No role-based authz scenarios; orgId-scoping IT (cross-tenant) covers tenant enforcement.

### D-38 (Q2: Uniqueness race mitigation) — OVERRIDES ADR-012 default
- **User choice**: B (Accept the race at D-26 scale; no advisory lock)
- **Impact on ADR-012**: STRICKEN — MySQL `GET_LOCK` advisory lock removed from MVP; `BC_NAME_LOCK_TIMEOUT` error code removed. Replaced with app-layer check only. Future remediation (advisory lock OR partial unique index subject to Aurora version D-40) documented as post-GA options, not implemented.
- **Impact on Create flow Mermaid (§5.1)**: `GET_LOCK` and `RELEASE_LOCK` steps removed; annotated note added explaining D-38 acceptance.
- **Impact on API table (§8)**: `BC_NAME_LOCK_TIMEOUT` stripped from POST error codes.
- **Impact on Data Model (§7)**: Prose amended — "Designer may still consider advisory lock" clause removed.
- **Impact on Risk Register**: R-03 severity lowered from HIGH to MEDIUM with explicit accepted-deviation flag (mirror of R-01 LWW treatment). Summary: 2 CRITICAL / 2 HIGH / 5 MEDIUM / 3 LOW.
- **Impact on Guardrail Matrix**: G-10.5 changed from "mitigated via advisory lock" to "accepted deviation with revisit-triggers".
- **Phase 7 impact**: `BenefitCategoryFacade.create()` does `dao.findActiveByNameAndOrgAndProgram()` → if exists, throw `ConflictException(BC_NAME_TAKEN_ACTIVE)`; else proceed to INSERT. No `GET_LOCK` call.
- **Phase 8 impact**: No advisory-lock timeout scenarios; explicit note in test plan that the SELECT→INSERT race is accepted per D-38 and not asserted.
- **Revisit-triggers**: (a) admin QPS >5/sec sustained; (b) ≥1 real duplicate-name incident in production logs; (c) product requires strict uniqueness guarantee.

### D-39 (Q3: `/activate` response body) — OVERRIDES ADR-006 symmetric 204
- **User choice**: B (200 OK + `BenefitCategoryResponse` DTO on happy activate)
- **Impact on ADR-006**: AMENDED — asymmetric on happy path:
  - Happy activate: **200 OK + DTO** (D-39 — UX win, saves GET round-trip)
  - Happy deactivate: **204 No Content** (nothing useful to return)
  - Idempotent already-active `/activate`: 204 (no state change, no DTO)
  - Idempotent already-inactive `/deactivate`: 204
- **Impact on API table (§8)**: Row 5 (`PATCH /activate`) response updated to "200 OK + BenefitCategoryResponse (on state change) / 204 No Content (on idempotent already-active)". Row 6 (`PATCH /deactivate`) unchanged (204 on both state change and idempotent).
- **Thrift IDL impact**: `activateBenefitCategory` returns `BenefitCategory` struct (same shape as `getBenefitCategory`) on state change, optional/null on idempotent no-op. `deactivateBenefitCategory` remains `void`.
- **Facade impact**: `BenefitCategoryFacade.activate()` returns `Optional<BenefitCategoryResponse>` — empty on idempotent no-op, populated on state change; controller maps empty → 204, populated → 200 + body.
- **Phase 8 impact**: Assert 200 + DTO on happy activation; 204 on idempotent already-active; 204 on happy/idempotent deactivation.

### D-40 (Q4: Aurora MySQL version) — DEFERRED to Phase 12
- **User choice**: C (Don't know; defer confirmation to Phase 12 Blueprint deployment runbook)
- **Impact on ADR-012**: Non-blocking because D-38 removed the advisory-lock vs partial-unique-index decision from the critical path. The ADR-012 "Future Remediation" note documents that the partial unique index option requires Aurora ≥ 8.0.13 — to be confirmed in Phase 12.
- **Phase 7 impact**: None. MVP does not use either mechanism.
- **Phase 12 obligation**: Deployment runbook includes a step "confirm Aurora MySQL version ≥ 8.0.13 to preserve the partial-unique-index remediation option; if < 8.0.13, only `GET_LOCK` is available as a post-GA fallback".

### Constraint Updates (C-27..C-31 already captured in session-memory; new constraints from gate decisions below)

- **C-32**: No advisory lock on benefit-category create/update in MVP (D-38).
- **C-33**: Asymmetric response on activate (200+DTO) vs deactivate (204) — Phase 7 must encode this in Thrift IDL + Facade signature (D-39).
- **C-34**: No `@PreAuthorize('ADMIN_USER')` in MVP on benefit-category endpoints (D-37).

Phase 7 Designer inputs now fully frozen. Ready to spawn.
