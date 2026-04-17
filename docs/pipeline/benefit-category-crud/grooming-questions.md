# Grooming Questions — Benefit Category CRUD

> **Phase**: 4 (Grooming + Blocker Resolution)
> **Ticket**: CAP-185145
> **Generated**: 2026-04-18
> **Purpose**: Consolidated list of all questions raised by Phase 1 (BA + ProductEx) and Phase 2 (Critic + Gap Analyser) — with resolutions, Phase owners, and current status.

---

## Question Classification

- **BLOCKER** — must be resolved before Phase 6 (Architect). 12 items, all resolved.
- **SCOPE** — affects what is in/out of MVP. 4 items, all resolved in Phase 1.
- **FEASIBILITY** — affects whether something is achievable. 3 items, all resolved in Phase 2/4.
- **PRIORITY** — affects ordering. 0 items.
- **NON-BLOCKING** — Phase 5/7/9 or follow-up tickets can address. 14 items open.

---

## BLOCKERS (12 of 12 resolved ✅)

| OQ# | Question | Resolved by | Verdict |
|-----|----------|-------------|---------|
| OQ-16 | Which existing system reads this config and applies benefits? | D-18 | External Client via intouch-api-v3 REST → EMF Thrift → MySQL |
| OQ-17 | Ship as internal plumbing only? Or public API with/without UI? | D-20 | API-only MVP, public Client API, no admin UI |
| OQ-19 | BenefitInstance redundant with tier_applicability? | D-21 | Rename to `benefit_category_slab_mapping` explicit junction table; drop `tier_applicability` field |
| OQ-24 | `tier_id` or `slab_id` for FK column? Entity naming collision? | D-22 | `slab_id`; entity `BenefitCategory` retained (C-14 mitigation) |
| OQ-25 | Audit columns — new 4-col vs existing pattern? | D-23 | Hybrid: `created_on` + `created_by` + `updated_on` + `updated_by` + `auto_update_time` |
| OQ-26 🔴 | Timestamps — Date vs Instant (G-01 vs G-12.2)? | D-24 | Three-boundary: Date+DATETIME (EMF) / i64 millis (Thrift) / ISO-8601 UTC (REST) |
| OQ-18 | MC descope — sign-off + defensive column? | D-25 | No sign-off, no column. YAGNI. Accept future migration cost. |
| OQ-20 | Scale envelope (cascade, QPS, replica)? | D-26 | SMALL: ≤50 cat, ≤20 slab/cat, ≤1k cascade, <10 QPS read, <1 QPS write, primary reads |
| OQ-21 | Cascade on reactivate? | D-27 | No reactivation at all. Deactivation terminal. PATCH `{is_active: true}` → 409. |
| OQ-22 | POST on existing-but-inactive (cat, slab) — reactivate or 409? | D-28 | New row with new PK; inactive rows don't block POST; 409 only if active duplicate |
| OQ-29 | Name reuse after soft-delete — block or free? | D-28 + D-29 | Free. App-layer validates active-rows-only; inactive rows accumulate as history |
| OQ-30 | Cache on day 1 or defer? | D-26 trivial | Defer. <10 QPS reads makes cache unnecessary. |

---

## SCOPE Questions (4 of 4 resolved — Phase 1)

| OQ# | Question | Resolved by | Verdict |
|-----|----------|-------------|---------|
| OQ-1 | Scope: Category CRUD only, or +Instance linking, +aiRa, +Matrix? | D-03 | Category CRUD + Instance linking only |
| OQ-2 | Three axes of "state" — which to model? | D-04 + D-05 | Only `is_active` boolean. Lifecycle state machine descoped. Prose "no instances = inactive" treated as descriptive. |
| OQ-3 | categoryType: closed enum vs open config? | D-06 | Single value `BENEFITS` for MVP; column retained for extensibility |
| OQ-11 | Naming: new "Benefit Category" vs legacy `Benefits` entity? | D-12 | Strict coexistence — separate tables, packages, no FK link |

---

## FEASIBILITY Questions (3 of 3 resolved — Phase 2/4)

| OQ# | Question | Resolved by | Verdict |
|-----|----------|-------------|---------|
| OQ-14 | Multi-tenancy: org_id vs program_id? | D-16 | Both on new tables; scoped queries via `IntouchUser.orgId` |
| OQ-23 | PK type: int+OrgEntityIntegerPKBase vs long standalone? | D-18 cascades | Int via OrgEntityIntegerPKBase; Thrift i32 parity forces this |
| OQ-27 | MySQL vs MongoDB? | D-18/D-19 cascades | MySQL. Thrift-exposed loyalty entities all MySQL. `UnifiedPromotion` MongoDB tied to its MC (descoped). |

---

## NON-BLOCKING Open Questions (14 open, for Phase 5/7/9 or follow-up)

| OQ# | Question | Severity | Owner | Status |
|-----|----------|----------|-------|--------|
| OQ-4 | BRD AC-BC04/05/06 numbering gap | LOW | Product follow-up | open |
| OQ-12 | Jira epic mapping (E2 vs E4) | LOW | Product follow-up | open |
| OQ-15 | Consumer identity | (was BLOCKER) | Phase 5 | ✅ subsumed by D-18 |
| OQ-28 | tier_applicability JSON vs junction | HIGH | (was BLOCKER) | ✅ resolved by D-21 |
| OQ-31 | Legacy `Benefits.promotion_id` — if future consumer needs vouchers | MEDIUM | Phase 5 / follow-up | open |
| OQ-32 | Actually chase AC-BC04/05/06 content | LOW | Product follow-up | open |
| OQ-33 | NFR-1 500ms P95 baseline | LOW | Phase 5 vs legacy `/benefits` | open |
| OQ-34 | Authz at Client boundary — Client writes? | HIGH | Phase 6 Architect | open |
| OQ-35 | Existing EMF Thrift handler template identification | HIGH | Phase 5 research | open |
| OQ-36 | Error envelope Thrift ↔ REST mapping | MEDIUM | Phase 7 Designer | open |
| OQ-37 | Validation layer placement (REST vs Thrift handler vs both) | MEDIUM | Phase 7 Designer | open |
| OQ-38 | JVM default TZ in production (UTC vs IST) | HIGH | Phase 5 ops-config check | open |
| OQ-39 | Thrift i64 timestamp unit (ms defaulted) | LOW | Phase 7 confirm | open (default recorded) |
| OQ-40 | ISO-8601 format pin | LOW | Phase 7 confirm | open (default recorded) |
| OQ-41 | Thrift field naming for timestamps | LOW | Phase 5/7 | open |
| OQ-42 | Race-condition mitigation on app-level uniqueness | HIGH-principle / LOW-scale | Phase 7 Designer | open (advisory lock recommended) |
| OQ-43 | String normalization for category name | LOW | Phase 7 Designer | open |

---

## Phase 4 Completion Verdict

All 12 blockers resolved. All SCOPE and FEASIBILITY questions closed. 14 non-blocking OQs surfaced with clear Phase 5/7/9 ownership.

**Pipeline is ready to proceed to Phase 5: Codebase Research + Cross-Repo Tracing.**

Phase 5 will read: session-memory.md, 00-ba-machine.md, 00-prd-machine.md, contradictions.md, gap-analysis-brd.md, blocker-decisions.md, grooming-questions.md — and explore all 5 code repos in parallel subagents, then run cross-repo tracer.
