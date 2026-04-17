# Product Requirements Document — Benefit Category CRUD

> **Ticket**: CAP-185145
> **Derived from**: `00-ba.md`, `00-ba-machine.md`
> **Phase**: 1 (PRD — final step of BA skill)
> **Date**: 2026-04-18

---

## 1. Problem Statement

The Garuda Loyalty Platform today ties every "benefit" to a Promotion (`benefits.promotion_id NOT NULL`) with only two types (`VOUCHER`, `POINTS`). Product wants benefits to become a first-class "product" — configurable at program level, grouped into categories, and assignable to tiers independently of promotions.

This ticket delivers the **first, smallest useful slice** of that ambition: a configuration registry for benefit categories and their tier applicability, with clean boundaries so follow-up tickets can layer on trigger semantics, value schemas, maker-checker, aiRa, and the Matrix View UI without rework.

---

## 2. Goals

1. **Config registry**: Admins can CRUD benefit categories and link them to tiers.
2. **Clean boundary**: This system is config-only. It does not compute or apply benefits — that stays with the existing engine (likely EMF tier event forest).
3. **Zero blast radius on legacy**: The existing `Benefits` entity and its tables are untouched.
4. **Extensible shape**: Data model leaves room for trigger semantics, value schemas, and approval workflows to be added later without schema migration of these new tables.
5. **Tenant-safe**: No cross-org data leakage.

## 3. Non-Goals

1. Benefit awarding / application logic.
2. Any of the 9 category types' specific semantics (WELCOME_GIFT, EARN_POINTS, etc.).
3. `triggerEvent` field or derivation.
4. Value payloads on instances (amount, points, voucher templates, JSON configs).
5. Maker-checker approval workflow.
6. aiRa natural-language mapping.
7. Matrix View dashboard UI.
8. Subscription benefit picker.
9. Migrating or modifying the legacy `Benefits` entity.
10. Hard-delete of categories or instances.

---

## 4. Target Users

| Persona | Description | Primary Stories |
|---------|-------------|----------------|
| Maya (Program Manager) | Admin user who configures loyalty programs, tiers, and (now) benefit categories. Lives mostly in the intouch-api-v3 admin console. | US-1 through US-10 |
| **Consumer System** (TBD) | An existing backend service (hypothesis: EMF tier event forest) that READS this config to apply benefits. **Not a human user.** | Read APIs for list/get — exact shape driven by consumer needs (Phase 5 to confirm consumer) |

---

## 5. Epics & User Stories

### Epic E1 — Benefit Category Management

> As a Program Manager, I want to create and manage Benefit Categories in my program so that I have a configurable grouping mechanism for benefits.

| Story | Description | Priority |
|-------|-------------|----------|
| US-1 | Create Benefit Category (name + tierApplicability + categoryType=BENEFITS) | P0 |
| US-2 | List Benefit Categories (filter by isActive) | P0 |
| US-3 | View single Benefit Category details | P0 |
| US-4 | Update Benefit Category (name, tierApplicability) | P0 |
| US-5 | Deactivate Benefit Category (cascade to instances) | P0 |
| US-6 | Reactivate Benefit Category (instances stay inactive) | P1 |

### Epic E2 — Benefit Instance Linking

> As a Program Manager, I want to assign Benefit Categories to specific Tiers (creating "instances") so that downstream benefit-awarding systems know which categories apply to which tiers.

| Story | Description | Priority |
|-------|-------------|----------|
| US-7 | Create Benefit Instance (link category → tier; tier must be in applicability) | P0 |
| US-8 | List Benefit Instances for a given Category | P0 |
| US-9 | Deactivate Benefit Instance | P0 |
| US-10 | Reactivate Benefit Instance (only if parent Category is active) | P1 |

---

## 6. Success Metrics

| Metric | Target | How measured |
|--------|--------|--------------|
| MVP delivery | All P0 stories shipped to prod | Feature behind flag; all acceptance criteria pass |
| Data integrity | 0 orphaned instances (instance under deleted/inactive-and-not-cascaded category) | Cron audit query + observability |
| Tenancy | 0 cross-org data leaks | Automated test suite + security review (Phase 11) |
| Adoption | ≥N categories created per org in first 30 days | Product analytics on create API |
| Consumer integration | Consumer system successfully reads config in first integration test | Phase 5 identifies consumer; Phase 9/10 includes consumer-side read test |

---

## 7. Acceptance Criteria Summary

| AC | Covers Story | Status |
|----|-------------|--------|
| AC-BC01' | US-1 | In scope (reinterpreted — no DRAFT / no trigger derivation) |
| AC-BC02 | US-1 (uniqueness rule) | In scope |
| AC-BC03' | US-7 | In scope (reinterpreted — no value fields) |
| AC-BC12 | US-5 | In scope |
| AC-BC07, AC-BC08 | — | Out of scope (maker-checker descoped) |
| AC-BC09, AC-BC10, AC-BC11, AC-BC13 | — | Out of scope |
| AC-BC04, AC-BC05, AC-BC06 | — | Missing in BRD (OQ-4, unknown intent) |

Detailed AC text is in `00-ba.md` §5.

---

## 8. Constraints & Assumptions

**Technical constraints:**
- Java / Spring / Thrift / MySQL stack (existing platform)
- Must not add FKs or columns to existing `Benefits` table (D-12 / C-14)
- Must be tenant-scoped (org_id + program_id) and query-safe (D-16 / C-19)

**Product assumptions:**
- 9 category types are deferred, not abandoned. A follow-up ticket will widen the enum and add per-type schemas.
- Maker-checker is deferred, not abandoned. A follow-up ticket will re-introduce the approval workflow.
- The consumer of this config is an existing system (hypothesis: EMF tier event forest). Phase 5 research will confirm before Phase 6 API freeze.

---

## 9. Dependencies

| Dependency | Type | Owner | Risk if missing |
|-----------|------|-------|-----------------|
| Consumer identification (OQ-15) | Internal — Phase 5 research | Engineering | HIGH — API shape cannot be frozen without consumer |
| Existing Tier table (tier_id FK target) | Platform existing | Platform team | LOW — Tier table exists and is stable |
| Existing auth / tenancy middleware | Platform existing | Platform team | LOW — used by other features |
| UI design for admin console (from v0.app URL) | External — Phase 3 | Design | MEDIUM — v0.app client-side rendered; Chrome MCP unavailable this session; may need screenshots |

---

## 10. Release Plan

Single MVP release behind a feature flag.

**Phase 1 — internal validation**: APIs wired, admin console shows category list + create form for a controlled org.
**Phase 2 — limited rollout**: 2–3 pilot orgs validate category creation and consumer integration.
**Phase 3 — general availability**: All orgs on the new model.

No database migration required beyond creating two new tables (`benefit_category`, `benefit_instance`). Legacy `Benefits` table unchanged.

---

## 11. Out-of-Scope Items & Follow-up Tickets

Items deferred from this MVP that product will need to sequence as separate tickets:

| Follow-up | Scope |
|-----------|-------|
| FU-1 | Widen `category_type` enum to include the 9 types from BRD §3. Add per-type behaviour. |
| FU-2 | Add `trigger_event` column + mapping table (BRD §5.3). Wire to event-dispatch layer. |
| FU-3 | Add value-payload fields to Instance (per-type schemas — BRD §5.4). |
| FU-4 | Re-introduce maker-checker approval workflow. |
| FU-5 | aiRa integration (BRD §8) — natural-language intent → categoryType + value form. |
| FU-6 | Matrix View UI (AC-BC10, AC-BC11). |
| FU-7 | Subscription benefit picker (AC-BC13). |
| FU-8 | Possible unification or migration of legacy `Benefits` entity into the new model (strategic — may never happen). |

---

## 12. Open Product Questions

| # | Question | Owner | Blocking? |
|---|----------|-------|-----------|
| OQ-4 | Are AC-BC04, AC-BC05, AC-BC06 intentional gaps or missing content? | Product | No |
| OQ-12 | Does CAP-185145 roll up to Epic E2 or E4? | Product | No |
| OQ-15 | Which existing system consumes this config? | Engineering (Phase 5) | Yes — for Phase 6 |

---

_End of PRD. See `00-ba.md` for full acceptance criteria detail, data model, and user stories. See `00-prd-machine.md` for structured metadata._
