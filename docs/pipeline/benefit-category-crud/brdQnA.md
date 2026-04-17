# BRD Review — Product Expert Analysis

> BRD: Garuda Loyalty Platform — Tiers & Benefits PRD v2.0 (Surabhi Geetey, March 2026)
> Focus: Epic 4 — Benefit Categories (BRD lines 1365–2101, plus cross-cutting context)
> Reviewed against: Codebase (emf-parent, intouch-api-v3, cc-stack-crm), docs/product/, docs.capillarytech.com (unavailable — noted below)
> Date: 2026-04-17
> Reviewer: ProductEx skill (Mode 4 — brd-review)

---

## Knowledge Source Status

| Source | Status | Notes |
|--------|--------|-------|
| BRD (brd-raw.md) | [C7] Fully read | Lines 1–2179 read directly |
| emf-parent codebase | [C5] Partial scan | Benefits entity, BenefitsType enum, benefits table schema read |
| intouch-api-v3 codebase | [C4] Structural scan | No BenefitCategory entity found |
| cc-stack-crm | [C3] Limited scan | benefits.sql schema read; no benefit_category table found |
| docs.capillarytech.com | [C1] Unavailable | WebFetch permission denied — gap noted |
| Product Registry | Gap | registry.md does not yet exist — scaffold created alongside this file |

---

## Alignment with Current Product

### Confirmed Alignments

- **Maker-Checker workflow pattern** — BRD §5 describes `DRAFT → PENDING_APPROVAL → ACTIVE`. The existing intouch-api-v3 codebase already has maker-checker scaffolding for subscription programs (evidenced by `AC-S 22/23` and subscription API contract), so this pattern is established. [C5] The Benefit Category CRUD will use the same approval framework.
- **Program-scoped entities** — BRD §2 states `categoryName` is unique per program (not globally). The existing `benefits` table uses `org_id` + `name` as a unique key, confirming per-org scoping is the standing pattern. [C6]
- **Promotion-backed benefits (existing model)** — The current `benefits` table has `promotion_id NOT NULL`, meaning every existing benefit maps to a V3 Promotion. BRD explicitly acknowledges this problem ("benefits today are not a product — they are promotions attached to a tier as an afterthought"). [C7]
- **VOUCHER and POINTS as benefit delivery types** — The existing `BenefitsType` enum `{VOUCHER, POINTS}` and the BRD's "Coupon / Voucher" and "Points" reward types are consistent. [C7]

### Conflicts with Current Product

| # | BRD States | Product Reality | Source | Severity |
|---|---|---|---|---|
| CF-01 | `categoryId` is typed as `String (UUID)` (BRD §2) | All existing loyalty entities (Benefits, PartnerProgramTierSyncConfiguration, etc.) use `int` PKs with composite `org_id` keys | emf-parent: `Benefits.java` line 35 — `@EmbeddedId BenefitsPK` with `int` | **High** — UUID vs int PK is an architectural choice that affects joins, Thrift IDL types, and all downstream queries |
| CF-02 | `triggerEvent` is described as "Derived from categoryType" — i.e., a computed/read-only field on the Category entity | The existing benefits model has no trigger concept on the Benefit entity; triggers live in Promotions / EMF event rules | emf-parent: `BenefitsAwardedStatsService`, `TierRenewedHelper`, `TierUpgradeHelper` — triggers are in the EMF event forest, not in the Benefits entity | **High** — Storing a derived field on the Category entity duplicates EMF event logic; or it means the Category entity is the new source of truth for trigger mapping |
| CF-03 | Benefit Category introduces BADGE, FREE_SHIPPING, PRIORITY_SUPPORT, and EARN_POINTS (multiplier) as `categoryType` values | `BenefitsType` enum in code is `{VOUCHER, POINTS}` only | emf-parent: `BenefitsType.java` | **High** — Four new benefit delivery mechanisms not modelled in current code; PRIORITY_SUPPORT (service entitlement) and FREE_SHIPPING (conditional waiver) have no current data model representation |
| CF-04 | `AC-BC01`: A newly created category is stored with `isActive: true` and appears in listing in `DRAFT` state | BRD §5 (Maker-Checker section) states "Category creation requires approval before instances can be created" — implying a DRAFT state, not ACTIVE, on creation. Also, the model field `isActive` (boolean) conflicts with a state machine having DRAFT/PENDING_APPROVAL/ACTIVE states | BRD §2 data model + BRD §5 + AC-BC01 | **High** — Two orthogonal state representations: a boolean `isActive` AND a lifecycle state enum. Which governs visibility? Which governs instance creation eligibility? |
| CF-05 | BRD header at line 1374 labels the section `Epic: E2 — Benefits as a Product` but the epic ordering in §7 Product Epics labels it `E4 — Benefit Categories` | Epic numbering is inconsistent within the same document | BRD line 498–524 (epic table) vs line 1374 | **Medium** — Ambiguity about whether Benefit Categories are part of Epic 2 or Epic 4; this affects sprint planning and dependency ordering |
| CF-06 | `benefits` table has `promotion_id NOT NULL` (cannot be null) | BRD aims to decouple benefits from promotions — new Benefit Category / Benefit Instance model should not require a promotion | intouch-api-v3: `benefits.sql` line 8 | **High** — Schema migration required to either make `promotion_id` nullable or introduce a new table entirely; existing data integrity constraints would break if new benefit types don't map to promotions |

---

## Open Questions

> Every question has an **Owner** tag. Team tags: `[Product]` `[Design/UI]` `[Backend]` `[Infra]` `[AI/ML]` `[Cross-team]`
> Status: `open` | `resolved: <answer>` | `deferred: <reason>`

### Product Behaviour Questions

| # | Owner | Question | Context | Why It Matters | Status |
|---|---|---|---|---|---|
| PB-01 | [Product] | Is `isActive` (boolean) a UI-visibility toggle independent of the lifecycle state (DRAFT/PENDING_APPROVAL/ACTIVE)? Or does it replace the state machine? | BRD §2 lists `isActive: Boolean` as a field, AND BRD §5 describes a DRAFT→PENDING_APPROVAL→ACTIVE state machine for categories. AC-BC01 says a created category has `isActive: true` in `DRAFT` state — but AC-BC12 says `isActive: false` hides the category from UI. These appear to be two separate axes. | If they're the same thing, the DRAFT state is redundant. If they're different, the data model needs two fields and the rules governing each must be explicit. Missing this → incorrect state transitions implemented. | open |
| PB-02 | [Product] | What is the complete, exhaustive set of `categoryType` enum values for Phase 1? Is the list of 9 types in BRD §3 (WELCOME_GIFT, UPGRADE_BONUS_POINTS, TIER_BADGE, RENEWAL_BONUS, LOYALTY_VOUCHER, EARN_POINTS, BIRTHDAY_BONUS, PRIORITY_SUPPORT, FREE_SHIPPING) final, or can program managers define custom types? | BRD §3 shows 9 example types but uses language like "examples of category types" — not explicitly stating these are the only Phase 1 values. The BRD also mentions "Custom" benefit type in E2-US1 listing filters. | The enum is the backbone of the entire trigger and value-constraint system. If custom types are allowed, the data model is very different (open enum vs closed enum). If it is a closed set of 9, the enum can be hardcoded. | open |
| PB-03 | [Product] | When a category is in `PENDING_APPROVAL` state, can a program manager still create Benefit Instances for it, or must the category be `ACTIVE` first? | BRD §5 states: "Category creation requires approval before instances can be created." AC-BC03 shows instance creation from `DRAFT` state category. This is a direct contradiction within the BRD. | If instances require ACTIVE category, the workflow is sequential (approve category first, then create instances). If instances can be drafted while category is pending, the UX is parallel but approval ordering becomes complex. | open |
| PB-04 | [Product] | What happens to existing Benefit Instances when their parent Category is set to `isActive: false`? Are instances automatically deactivated? Are running benefits paused mid-cycle? | BRD §2 says inactive categories are "hidden from admin UI." BRD AC-BC12 says inactive categories are hidden from pickers. Neither specifies runtime impact on in-flight benefit awards. | If a category is deactivated mid-cycle, members with active BIRTHDAY_BONUS instances (for example) — do they still receive their points on their birthday? Or is the instance also stopped? This is a P0 data integrity question. | open |
| PB-05 | [Product] | For the EARN_POINTS category type, the BRD says "earn rate may be expressed as a multiplier (e.g. 1x, 1.5x, 2x) OR as points-per-currency-unit." Which form does the platform store internally, and how does it interface with the Points Engine (EMF)? | BRD §3.6 specifies two earn rate formats. The EMF points engine (`emf-parent`) currently handles points accrual — how does a Benefit Instance's earn-rate value translate to an EMF promotion rule? | This is the highest-volume benefit type (fires on every qualifying transaction). If the integration path between Benefit Instance and EMF is not specified, backend cannot implement it without making assumptions. This is a P0 blocker for the EARN_POINTS type. | open |

### Design & UX Questions

| # | Owner | Question | Context | Why It Matters | Status |
|---|---|---|---|---|---|
| DU-01 | [Design/UI] | The Matrix View (AC-BC10) shows "categories as rows, tiers as columns." What is the defined sort order for rows (categories)? Is it: creation date, alphabetical, by categoryType, by frequency of use? | AC-BC10 and AC-BC11 describe the matrix grid structure but specify no ordering for rows. | Sort order affects every screenshot mockup and the default user experience. If unspecified, UI team will invent one that may not match PM expectations. | open |
| DU-02 | [Design/UI] | For the "Configuration Gap" indicator (AC-BC10 — "red indicator" on unconfigured cells), what exact UX action does clicking a red-indicator cell trigger? Does it open an inline form, navigate to a creation flow, or open aiRa? | AC-BC10 mentions a "red indicator" for Configuration Gap cells but does not specify the click behaviour. The BRD describes two paths (direct UI vs aiRa) for creation — which applies here? | Determines whether the Matrix View is read-only or an entry point for configuration. Significant UX and backend scope difference. | open |
| DU-03 | [Design/UI] | The BRD does not specify a Delete / Archive flow for Benefit Categories. Is a category deletable once it has been used (i.e., has historical instances)? If not, is there a soft-delete/archive state beyond `isActive: false`? | BRD §2 defines `isActive` as a deactivation mechanism. The Matrix View and listing show "inactive" categories via a toggle. No delete endpoint or flow is specified for categories. | Standard CRUD scope question. For the "D" in Benefit Category CRUD: is physical delete allowed, or only soft deactivation? The title of this epic ("Benefit Category CRUD") implies a Delete operation. If it is omitted, it is a gap that will surface in QA. | open |

### Backend & Technical Questions

| # | Owner | Question | Context | Why It Matters | Status |
|---|---|---|---|---|---|
| BE-01 | [Backend] | What primary key type should `benefit_category` use — `int` (auto-increment + org_id composite, matching all existing loyalty entities) or `String UUID` (as specified in BRD §2 `categoryId: String (UUID)`)? | BRD §2 explicitly specifies UUID. Every existing entity in `emf-parent` and `pointsengine-emf` uses `int` PKs with `org_id` composite keys (verified: `Benefits.java`, `PartnerProgramTierSyncConfiguration.java`). Thrift IDL types in `thrift-ifaces-pointsengine-rules` likely encode IDs as `i32` or `i64`. | Choosing UUID when the rest of the platform uses int creates join complexity, Thrift type mismatches, and potential index performance degradation at scale. Choosing int means the BRD's `categoryId: String (UUID)` field shape is wrong for the API contract. This must be resolved before schema migration is written. | open |
| BE-02 | [Backend] | How does a Benefit Instance (specifically for PRIORITY_SUPPORT and FREE_SHIPPING types) interface with the external systems that enforce those entitlements (support queue, shipping service)? Does the platform emit an event? Poll? Or is the entitlement checked in real-time at the point of service? | BRD §3.8 (Priority Support) and §3.9 (Free Shipping) describe entitlements that require real-time enforcement by external systems. The current `benefits` model only tracks VOUCHER and POINTS — no entitlement-check pattern exists. | If the platform only stores the entitlement record and external systems must poll/query it, the API surface is different (read endpoint for entitlement state). If the platform emits an event on tier entry, the event schema and publishing mechanism must be defined. This is not specified in the BRD. | open |
| BE-03 | [Backend] | The `triggerEvent` field on a Benefit Category is described as "Derived from categoryType." Is this a computed property (not stored, derived at read time from the categoryType→triggerEvent mapping table) or a stored column that is set at creation and immutable? | BRD §2 lists `triggerEvent` as a data model field. But it says "Derived from categoryType" — implying it should not need separate storage. The EMF event forest (emf-parent) processes tier events and fires promotions. If `triggerEvent` is stored on the Category, it must stay in sync with EMF's event definitions. | If stored: adds a migration column and a consistency risk (what if categoryType→triggerEvent mapping changes?). If computed: it is a documentation field only and the API read response derives it. This directly shapes the DB schema and the Flyway migration scope. | open |
| BE-04 | [Backend] | The `tierApplicability` field is typed as `Array<TierId>`. Where is this persisted — as a JSON column, a `VARCHAR` delimited list, or a separate junction table (`benefit_category_tier_applicability`)? | BRD §2 specifies the field type but not the storage strategy. The existing platform does not appear to have a junction table for this (no `benefit_category` table found in any repo scanned). | The storage choice affects queryability (can you efficiently query "which categories apply to tier X?"), the Flyway migration design, and the ORM mapping. A junction table is the relational-correct choice but adds a second migration file. A JSON column is faster to build but harder to index. | open |
| BE-05 | [Backend] | The `benefits` table has `promotion_id NOT NULL` (schema verified in `intouch-api-v3` test resources). When new Benefit Instances are created via the Benefit Category model, will they still require a backing promotion in V3 Promotions? Or is this the point where the platform decouples benefits from promotions? | BRD §3 problem brief states: "benefits today are promotions attached to a tier as an afterthought... We need Benefits to be a first-class module." This implies decoupling. But the existing `benefits` table enforces `promotion_id NOT NULL`. | If the new `benefit_instance` table is separate from the old `benefits` table, a migration strategy for existing data must be defined. If the same table is extended, the `promotion_id` constraint must be relaxed — a backwards-incompatible schema change affecting all existing queries. | open |

### Missing Specifications

| # | Owner | Missing Area | Current Product Behaviour | Recommendation | Status |
|---|---|---|---|---|---|
| MS-01 | [Product] | **Delete / Archive operation for Benefit Category** — The BRD describes Create, Read, Update, and activation/deactivation. It does not specify whether a category can be deleted, what happens to its instances on deletion, and whether soft delete (archive) is a separate state from `isActive: false`. | The existing `benefits` table has no delete-related fields or audit trail for deletion. `is_active` is the only deactivation mechanism. | Explicitly specify: (a) whether DELETE is in scope for Phase 1, (b) whether archive is a distinct state from inactive, (c) what happens to linked Benefit Instances on category deletion/archival. | open |
| MS-02 | [Product] | **Maker-Checker timeout and withdrawal** — BRD §5 and AC-BC07/BC08 specify the PENDING_APPROVAL state but do not define: (a) timeout after which an unapproved category/instance expires, (b) whether the submitter can withdraw a pending item, (c) what notification triggers on timeout. | Existing BRD standards doc (`brd-standards.md`) explicitly flags this gap for the Tiers epic. The same gap is present here. | Add acceptance criteria: GIVEN a category is in PENDING_APPROVAL WHEN 72 hours pass without approver action THEN [specify: auto-reject? escalate? notify?]. | open |
| MS-03 | [Backend] | **API endpoint shape for Benefit Category CRUD** — The BRD §10.2 endpoint table lists `/benefits` (GET/POST) but does not specify a `/benefit-categories` endpoint, nor request/response schemas, error codes, or validation rules for category operations. | The existing `/benefits` endpoint in the API contract table maps to the old benefits model (promotions-backed). | Specify dedicated endpoints: POST /benefit-categories, GET /benefit-categories, GET /benefit-categories/{id}, PUT /benefit-categories/{id}, PATCH /benefit-categories/{id}/deactivate. Include request/response shapes and error codes per brd-standards.md §6. | open |
| MS-04 | [Cross-team] | **aiRa category mapping — confidence and fallback** — AC-BC09 specifies that aiRa correctly identifies `categoryType = BIRTHDAY_BONUS` from natural language. It does not specify what happens when aiRa's confidence in the mapping is below threshold: does it ask a clarifying question, present options, or refuse? | AC-S27 (subscription flow) shows aiRa flagging unrecognised benefits and offering `[Create Category]` / `[Skip]` options — a useful pattern. The category-specific AC does not include the equivalent. | Specify the low-confidence fallback for aiRa→categoryType mapping (mirrors AC-S27 pattern). Also specify: what is the minimum set of fields aiRa must collect before it can present a category creation preview? | open |
| MS-05 | [Product] | **Benefit Instance value schema per categoryType** — The BRD defines 9 category types, each with different value fields (e.g., BIRTHDAY_BONUS has `pointsAwarded` + `awardsWindowDays`; FREE_SHIPPING has `minimumOrderValue`). These per-type schemas are described in prose in §3 but never given as a formal structured table of required vs optional fields per type. | No existing schema definition for per-type value fields exists in code (no `BenefitCategory` entity found in any scanned repo). | For each of the 9 categoryTypes: produce a table of fields, types, constraints, and optionality. This is the backend team's data contract for building the instance value storage schema. Without it, BA cannot write testable ACs for instance creation. | open |

### Domain & Terminology Questions

| # | Owner | BRD Term | Established Term | Clarification Needed | Status |
|---|---|---|---|---|---|
| DT-01 | [Product] | "Benefit Category" (BRD §2) | `Benefits` (existing `benefits` table, `Benefits.java` entity) | Are Benefit Categories and Benefits two different things in the new model? BRD §2 says "a benefit category is a top-level classification record" that is the parent to "benefit instances." The old `Benefits` entity appears to map to what the BRD calls a "Benefit Instance." If so, the term "Benefits" in existing code will collide with the new "Benefit Category" concept — risking team confusion and incorrect code reuse. | open |
| DT-02 | [Product] | "Epic 4 — Benefit Categories" vs "Epic E2 — Benefits as a Product" | Consistent epic numbering | BRD line 498–524 (§7 epic table) labels the standalone benefits module as "E2 — Benefits as a Product." BRD line 1374 (header of the Benefit Category spec section) labels it "Epic: E2 — Benefits as a Product." But the section title at line 1365 says "Epic 4 — Benefit Categories." The Jira ticket is CAP-185145 — what epic does this map to in Jira? This creates sprint allocation ambiguity. | open |
| DT-03 | [Backend] | "Benefit Instance" | No established code term found | The BRD introduces "Benefit Instance" as the entity that links a Category to a Tier and carries the reward value. No Java class, table, or Thrift struct named `BenefitInstance` was found in any scanned repo. This is a net-new entity with no code equivalent. The closest existing entity is `Benefits` (which is promotions-backed). The team must agree: is `BenefitInstance` the new name for a new table, or is it an extension of the existing `benefits` table? | open |

### Cross-Cutting Concern Gaps

| # | Owner | Concern | What BRD Should Address | Status |
|---|---|---|---|---|
| CC-01 | [Cross-team] | **Multi-tenancy / org scoping** — Benefit Categories must be isolated per org/program. The BRD specifies `categoryName` unique per program but does not explicitly state the tenancy model: is a category scoped to an `orgId`? A `programId`? Or both? | BRD §2 data model should specify which field enforces tenant isolation. Existing code uses `orgId` as the primary tenancy boundary (all entities have `org_id`). The BRD's `tierApplicability` references tiers by ID — are tier IDs globally unique or org-scoped? | open |
| CC-02 | [Backend] | **Audit trail** — BRD §2 lists `createdAt / updatedAt` as audit fields. The maker-checker flow implies a richer audit need: who created, who submitted for approval, who approved/rejected, at what timestamp, with what comment. The BRD does not specify whether a dedicated `benefit_category_audit_log` table is needed or whether the existing change-log pattern (E1-US5 covers tier change log) applies. | Specify whether category/instance mutations are captured in the same change-log infrastructure as tier mutations (E1-US5), or whether a separate audit mechanism is needed for benefits. | open |
| CC-03 | [Infra] | **Caching strategy for the aiRa Context Layer** — The `/program/{id}/context` API (BRD §10.2) must include benefit categories and their instances. The BRD's Out of Scope section defers "real-time member streaming" to Phase 2 but says "daily snapshots sufficient." It does not specify the cache TTL or staleness policy for benefit catalog data in the context layer. If a new category is approved and activated, how quickly is it visible to aiRa? | Specify: TTL for benefit catalog data in `/program/{id}/context`, invalidation trigger on category activation/deactivation, and acceptable staleness window. | open |

---

## Summary

- **Total questions**: 17
- **High severity conflicts**: 4 (CF-01, CF-03, CF-04, CF-06)
- **Blocking gaps** (cannot proceed without answers): 4 (PB-01, PB-02, BE-01, BE-05)

### Questions by Owner

| Owner | Open | Resolved | Blocking |
|-------|------|----------|----------|
| [Product] | 8 | 0 | 3 (PB-01, PB-02, DU-03) |
| [Design/UI] | 3 | 0 | 0 |
| [Backend] | 5 | 0 | 3 (BE-01, BE-02, BE-05) |
| [Infra] | 1 | 0 | 0 |
| [AI/ML] | 0 | 0 | 0 |
| [Cross-team] | 2 | 0 | 0 |

- **Recommendation**: **Pause for product team input first on PB-01, PB-02, and BE-01 before BA Q&A proceeds.** These three questions determine the data model shape (state machine vs boolean, closed vs open enum, int vs UUID PK) — all downstream design decisions depend on them. CF-06 (promotion_id NOT NULL) is a schema archaeology question that backend must resolve independently. The remaining questions are refinements that BA can elicit during Q&A without blocking architecture.

---

## Confidence Summary

| Finding | Confidence | Evidence |
|---------|-----------|---------|
| No `BenefitCategory` entity exists in any scanned repo | [C5] Confident | Glob search across emf-parent and intouch-api-v3 returned no matches; `benefits` table schema found — no category concept |
| Existing `BenefitsType` enum is `{VOUCHER, POINTS}` only | [C7] Near Certain | Direct read of `BenefitsType.java` — 2 values confirmed |
| Existing `benefits` table has `promotion_id NOT NULL` | [C7] Near Certain | Direct read of `benefits.sql` schema |
| All existing loyalty entities use `int` + `org_id` PKs | [C6] High Confidence | Verified in `Benefits.java`, `PartnerProgramTierSyncConfiguration.java` |
| docs.capillarytech.com content for benefits | [C1] Speculative | WebFetch permission denied — could not verify documented behaviour |
| BRD epic numbering conflict (E2 vs E4) | [C7] Near Certain | Direct read of BRD lines 498–524 vs 1374 |
