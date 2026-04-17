# Session Memory — Benefit Category CRUD

> **Purpose**: Shared context across all pipeline phases. Updated INCREMENTALLY after every decision/finding — never batch at phase end.
> **Ticket**: CAP-185145
> **Feature**: Benefit Category CRUD
> **Started**: 2026-04-17
> **Branch**: `aidlc/CAP-185145` (across all 5 repos)

---

## Domain Terminology

_(Populated in Phase 1 — BA Deep-Dive)_

| Term | Definition | Source |
|------|------------|--------|
| Benefit Category | Metadata grouping record scoped to a Program. In MVP: holds name, single categoryType value (`BENEFITS`), tierApplicability, isActive. **No reward values, no trigger event.** | BRD §2 (narrowed by D-06/D-07/D-09) _(BA)_ |
| Benefit Instance | A pure (categoryId, tierId) association marking that a category is configured for a specific tier. **Carries NO value payload in MVP** — downstream systems read category+tier association and apply benefits per their own logic. | BRD §2 (narrowed by D-09) _(BA)_ |
| categoryType | Enum column on BenefitCategory. **MVP**: single value `BENEFITS`. Column retained for future extensibility. 9 types from BRD §3 (WELCOME_GIFT, EARN_POINTS, etc.) are deferred. | BRD §3 (narrowed by D-06) _(BA)_ |
| ~~triggerEvent~~ | ❌ **Not modelled in MVP.** Removed by D-07. Any trigger/event semantics live in the external system that reads the config. | — |
| tierApplicability | Array of tierIds indicating which tiers can have configured instances for this category. At least one required. | BRD §2 _(BA)_ |
| Program | Top-level container. A Program contains one or more Tiers. | BRD §2 _(BA)_ |
| Maker-Checker | Approval workflow: DRAFT → PENDING_APPROVAL → ACTIVE. Category creation and instance changes both go through it. | BRD §5 _(BA)_ |
| Matrix View | Benefits dashboard grid — categories as rows, tiers as columns, configured value or "Not configured" in each cell. | BRD AC-BC10 _(BA)_ |
| aiRa | Capillary's conversational AI assistant — maps natural-language intents to categoryType + prompts for value fields. | BRD §8 _(BA)_ |
| Maya | Primary persona — program manager configuring tiers/benefits. | BRD E1/E2 user stories _(BA)_ |
| Benefits (legacy) | Existing `Benefits` entity in emf-parent — promotions-backed, types VOUCHER/POINTS only. Distinct from the new BenefitCategory/BenefitInstance model. | emf-parent: `Benefits.java`, `benefits.sql` _(ProductEx)_ |
| promotion_id | Mandatory FK on the existing `benefits` table linking every benefit to a V3 Promotion. Planned to be decoupled in the new model. | `benefits.sql` NOT NULL constraint _(ProductEx)_ |

---

## Key Decisions

_(Populated incrementally — every decision made by the user during Q&A, blocker resolution, architecture approval, etc.)_

| # | Decision | Rationale | Phase | Date |
|---|----------|-----------|-------|------|
| D-01 | Use Superpowers plugin for TDD/brainstorming/parallel-agent workflows | Required by pipeline design | Phase 0 | 2026-04-17 |
| D-02 | Live dashboard enabled | User opted in | Phase 0 | 2026-04-17 |
| D-03 | **Scope**: Category entity CRUD (create, read, update, deactivate, list) + Benefit Instance creation/linking to tiers. aiRa mapping, Matrix View, and Subscription linkage are OUT of scope for this run. | User answered Q1 — "2" | Phase 1 | 2026-04-18 |
| D-04 | **isActive semantics**: `isActive` is a single explicit boolean admin-controlled flag. The BRD §5 prose "a category with no instances is considered Inactive" is treated as descriptive only — NOT a distinct data state. A category with zero instances is still `isActive: true` if created. "Not configured" hints in UI are a presentation concern. | User answered Q2 — "3" | Phase 1 | 2026-04-18 |
| D-05 | **Maker-checker DESCOPED for MVP**. No DRAFT / PENDING_APPROVAL / ACTIVE lifecycle state machine. CRUD operations are immediate — no approval gate. Only `is_active` boolean governs usability. Approval workflow to be added in a later phase/ticket. | User answered Q3 — "4" → "A" | Phase 1 | 2026-04-18 |
| D-06 | **Single categoryType value for MVP**: `BENEFITS`. The 9 types in BRD §3 (WELCOME_GIFT, EARN_POINTS, TIER_BADGE, etc.) are NOT modelled. Column retained as enum (future-proof), populated as BENEFITS for every row today. Multi-type support is future work. | User answered Q4 — "4" → "e" → "keep one enum BENEFITS, drop triggerEvent" | Phase 1 | 2026-04-18 |
| D-07 | **`triggerEvent` field dropped entirely** from both Category and Instance models. No trigger-mapping table from BRD §5.3. No event-derived-from-type logic. | User answered Q4 clarification | Phase 1 | 2026-04-18 |
| D-08 | **Benefit awarding is external** — this system stores config only. An existing system (TBD in Phase 5 — likely EMF tier event forest / TierRenewedHelper etc.) reads this config and applies benefits. No new awarding/calculation logic in MVP. | User answered I-1 → "c" | Phase 1 | 2026-04-18 |
| D-09 | **BenefitInstance carries NO value payload**. Pure (categoryId, tierId) association row + lifecycle metadata (isActive, createdAt, createdBy). No amount, points, voucherTemplateId, text, or JSON config. | User answered I-2 → "e" | Phase 1 | 2026-04-18 |
| D-10 | `categoryType` column kept even though only one value today (YAGNI accepted — future extension without schema change). | User answered I-4 → "a" | Phase 1 | 2026-04-18 |
| D-11 | BRD sections §3 (9 type definitions), §5.3 (trigger mapping), §5.4 (value constraints per type), and parts of AC-BC01 ("correct trigger event derived from categoryType") are **out of scope / deferred** for MVP. BA document will flag these explicitly. | User answered I-3 → "yes" | Phase 1 | 2026-04-18 |
| D-12 | **Strict coexistence with legacy `Benefits` entity.** New `BenefitCategory`/`BenefitInstance` live alongside existing `emf-parent Benefits` in separate tables, packages, service layer. No FK linking them. Glossary in BA doc will spell out the distinction. Unification (if ever) is a future epic. | User answered Q5 — "1" | Phase 1 | 2026-04-18 |
| D-13 | **Soft-delete only for MVP.** No hard-delete endpoint. Removal semantics = `is_active=false` via PATCH. Deactivated categories/instances remain in DB for audit/history. Hard-delete may be added later if operational need emerges. | User answered Q6 — "A2" | Phase 1 | 2026-04-18 |
| D-14 | **Cascade deactivation on category.** When a category's `is_active` flips to false, all child instances' `is_active` flip to false in the same DB transaction. No block-on-active-instances behaviour. Reactivating a category does NOT auto-reactivate instances — those must be re-enabled explicitly (reactivation is a deliberate act per instance). | User answered Q6 — "B1" | Phase 1 | 2026-04-18 |
| D-15 | **Uniqueness**: `categoryName` is unique per-Program, enforced by DB constraint `UNIQUE (program_id, name)`. Tighter boundary than existing `benefits (org_id, name)`. | User confirmed Q7 | Phase 1 | 2026-04-18 |
| D-16 | **Multi-tenancy**: New tables carry both `org_id` (platform-wide tenant isolation) and `program_id` (feature scope). Both indexed. Auth middleware injects org context. | User confirmed Q7 | Phase 1 | 2026-04-18 |

---

## Constraints

_(Populated in Phase 1 and updated as Phase 6/7 add architectural constraints)_

| # | Constraint | Source | Why |
|---|------------|--------|-----|
| C-01 | Java / Spring / Thrift / MySQL stack (existing) | Project context | Platform standard |
| C-02 | 5 repos involved: emf-parent, intouch-api-v3, cc-stack-crm, thrift-ifaces-pointsengine-rules, kalpavriksha | User input | Feature spans these |
| C-03 | Category is metadata only — holds NO reward values. Instances carry values. | BRD §2 | Shapes data model — category table has no amount/points columns |
| C-04 | categoryName must be unique per Program (not global) | BRD §2 + AC-BC02 | Enforcement level: likely DB constraint + service validation |
| ~~C-05~~ | ~~Maker-Checker: new Category → PENDING_APPROVAL~~ | ~~BRD §5 + AC-BC07~~ | ❌ **REMOVED by D-05** — maker-checker descoped from MVP |
| ~~C-06~~ | ~~Dual "inactive" semantics~~ | — | ❌ **REMOVED by D-04** — single is_active flag only |
| C-08 | Data model: single `is_active` boolean flag. NO lifecycle state column. NO approval_request table. | D-05 | Simplifies MVP; add back when maker-checker returns |
| C-09 | All CRUD operations on Categories and Instances are IMMEDIATE (no approval gate) | D-05 | API responds with final state; no pending/approval intermediate |
| ~~C-07~~ | ~~Instance creation must have all required value fields populated before activation~~ | — | ❌ **REMOVED by D-09** — instances carry no value payload |
| C-10 | BenefitInstance schema: `(id PK, category_id FK, tier_id FK, is_active, created_at, created_by, updated_at, updated_by)`. No value/amount/points/text/JSON columns. | D-09 | Pure association + lifecycle only |
| C-11 | BenefitCategory schema: `(id PK, program_id FK, name, category_type ENUM('BENEFITS'), tier_applicability JSON or link table, is_active, created_at, created_by, updated_at, updated_by)`. No trigger_event column. | D-06, D-07, D-10 | Trigger field explicitly absent |
| C-12 | Benefit awarding logic is OUT OF SCOPE. This feature produces config only; an external reader (identified in Phase 5) applies the benefits. | D-08 | Establishes clean boundary — no event handlers, calculators, or strategy classes in this feature |
| C-13 | BRD §3 (9 category types), §5.3 (trigger mapping), §5.4 (value constraints per type), AC-BC01 trigger-derivation requirement are DEFERRED. Must be explicitly called out in the BA doc as "not in scope — see future ticket". | D-11 | Prevents silent scope creep during design/dev |
| C-14 | New entities must NOT add FKs or columns to the existing `Benefits` table in emf-parent. Zero schema changes to legacy. New tables live in their own namespace (package + table prefix TBD). | D-12 | Strict coexistence — zero blast radius on legacy |
| C-15 | API MUST NOT expose a DELETE verb for categories or instances in MVP. Removal is via PATCH `{is_active: false}` only. | D-13 | Soft-delete semantics enforced at API layer |
| C-16 | Deactivation flow MUST be transactional. Flipping category `is_active=false` and cascading all child instances to `is_active=false` happens in a single DB transaction. Failure at any step rolls back the whole operation. | D-14 | Consistency requirement — no half-deactivated state |
| C-17 | Reactivation of a category does NOT auto-reactivate its instances. Instance reactivation is a separate, explicit, per-instance action. | D-14 | Prevents accidental re-enablement of benefits the admin may have deliberately turned off |
| C-18 | DB constraint: `UNIQUE (program_id, name)` on benefit_category table. Service-layer pre-check returns 409 before hitting DB for friendlier error. | D-15 | Two-layer uniqueness enforcement |
| C-19 | Both `benefit_category` and `benefit_instance` tables carry `org_id BIGINT NOT NULL` + `program_id BIGINT NOT NULL`. Tenant-isolated queries always scope by `org_id` from auth context. | D-16 | Tenancy + feature scope |

---

## Codebase Behaviour

_(Populated in Phase 5 — Codebase Research. One row per repo.)_

| Repo | Key Findings | Files/Patterns | Confidence |
|------|--------------|----------------|------------|
| emf-parent | No `BenefitCategory` or `BenefitInstance` entity exists. Existing `Benefits` entity uses int PK + org_id composite. `BenefitsType` enum is `{VOUCHER, POINTS}` only. EMF handles tier events via event forest (TierRenewedHelper, TierUpgradeHelper). | `pointsengine-emf/src/.../Benefits.java`, `BenefitsType.java`, `TierRenewedHelper.java`, `TierUpgradeHelper.java` | C6 _(ProductEx)_ |
| intouch-api-v3 | `benefits.sql` schema: `promotion_id NOT NULL` — all existing benefits are promotions-backed. No `benefit_category` table found. `partner_program_tier_sync_configuration.sql` found — confirms subscription/tier sync pattern exists. | `src/test/resources/.../benefits.sql`, `partner_program_tier_sync_configuration.sql`, `customer_benefit_tracking.sql` | C6 _(ProductEx)_ |

---

## Open Questions

_(Populated incrementally. Resolved questions move to Key Decisions.)_

| # | Question | Asked By | Status |
|---|----------|----------|--------|
| OQ-1 | What's in scope for this feature? CRUD of Category entity only, or also Instance creation, aiRa mapping, Matrix View, Subscription linkage? | BA Phase 1 | ✅ resolved — D-03: (a) + (b), i.e., Category CRUD + Instance linking |
| OQ-2 | BRD has THREE axes around "state" of a category: (A) isActive boolean §2, (B) DRAFT/PENDING_APPROVAL/ACTIVE lifecycle §5+AC-BC01, (C) "no instances = Inactive" functional §5 prose. | BA Phase 1 | ✅ partial: axis C resolved by D-04 (ignore prose). Axis A vs B still open → Q3. |
| OQ-3 | Are the 9 categoryTypes a fixed (closed) enum or open/extensible? → **ProductEx PB-02**. | BA Phase 1 | ✅ resolved by D-06 — neither; single value `BENEFITS` for MVP, rest deferred |
| OQ-4 | AC-BC04, AC-BC05, AC-BC06 missing from BRD numbering. Intentional gap or content missing? | BA Phase 1 | open — defer to final review |
| OQ-5 | Does "delete" exist for categories? BRD has isActive=false (soft-delete) but no hard-delete spec. → **ProductEx MS-01** (overlaps DU-03). | BA Phase 1 | ✅ resolved by D-13 — soft-delete only, no DELETE verb in MVP |
| OQ-6 | categoryName uniqueness per-Program or per-Organization? | BA Phase 1 | ✅ resolved by D-15 — per-Program (program_id, name) |
| OQ-7 | Category UPDATE maker-checked, or only CREATE + instance changes? | BA Phase 1 | ✅ resolved by D-05 — no maker-checker in MVP |
| OQ-8 | When category is PENDING_APPROVAL, can instances be drafted? BRD §5 vs AC-BC03 appear to contradict. → **ProductEx PB-03**. | BA Phase 1 | ✅ resolved by D-05 — moot, no PENDING_APPROVAL state |
| OQ-13 | Maker-checker timeout behaviour (72hr auto-reject, withdrawable, notifications). → **ProductEx MS-02**. | BA Phase 1 | ✅ resolved by D-05 — deferred to when maker-checker returns |
| OQ-9 | What happens to running instances when parent category is deactivated (mid-cycle)? → **ProductEx PB-04**. | BA Phase 1 | ✅ resolved by D-14 — cascade deactivate in same txn |
| OQ-10 | EARN_POINTS — multiplier vs points-per-currency — how does it flow to EMF Points Engine? → **ProductEx PB-05**. | BA Phase 1 | ✅ resolved by D-08, D-09 — moot; instance carries no value, awarding is external |
| OQ-15 | **Which existing system READS this config and applies benefits?** Candidates: EMF tier event forest (TierRenewedHelper, TierUpgradeHelper), peb (Points Engine Backend), intouch-api-v3 workflows, or a new consumer TBD. Must be confirmed in Phase 5 research — affects API schema (they're the consumer) and integration contract. | D-08 | open — Phase 5 must confirm |
| OQ-11 | Naming collision: new "Benefit Category" vs existing emf-parent `Benefits` entity. → **ProductEx DT-01**. | BA Phase 1 | ✅ resolved by D-12 — strict coexistence, separate packages/tables, glossary clarification |
| OQ-12 | BRD-internal Epic numbering conflict: E2 (Benefits as a Product) vs E4 (Benefit Categories). Which Jira epic does CAP-185145 belong to? → **ProductEx DT-02**. | BA Phase 1 | open — low risk for engineering, ask for record |
| OQ-14 | Multi-tenancy — orgId vs programId boundary. Existing pattern is orgId per ProductEx C6. | BA Phase 1 | ✅ resolved by D-16 — both on new tables; scoped queries via auth context |

---

## Standing Architectural Decisions (Project-Level)

_(Pulled from CLAUDE.md — Architectural Decisions table. Do not duplicate here; reference only.)_

See: `.claude/CLAUDE.md` → "Architectural Decisions (Standing — Project-Level)"

---

## Per-Feature ADRs

_(Populated in Phase 6 — Architect. Each row links to the full ADR in `01-architect.md`.)_

| ADR | Title | Status | Phase |
|-----|-------|--------|-------|

---

## Risk Register

_(Populated in Phase 6a — Impact Analysis.)_

| # | Risk | Severity | Mitigation | Phase |
|---|------|----------|------------|-------|

---

## Guardrails Referenced

_(As phases reference specific guardrails from `.claude/skills/GUARDRAILS.md`.)_

| Guardrail | Phase Referenced | Context |
|-----------|------------------|---------|

---

## Cross-Repo Coordination

_(Populated in Phase 5 — Cross-Repo Tracer. Who writes where and why.)_

| Repo | New Files | Modified Files | Reason | Confidence |
|------|-----------|----------------|--------|------------|
