# Product Registry

> Last updated: 2026-04-17
> Maintained by: ProductEx skill
> Status: Initial scaffold — populated from Benefit Category CRUD BRD review (CAP-185145)

---

## Product Overview

Capillary's **Garuda Loyalty Platform** is an enterprise loyalty configuration and execution platform serving retail, airline, and financial services brands. It enables program managers to define tier hierarchies, configure benefit rules, manage member lifecycle events, and drive member engagement through promotions and subscriptions. The platform processes millions of tier evaluations per day and is the configuration intelligence layer for loyalty programs running on the Capillary stack.

The platform is being rebuilt ground-up in the Garuda UI (React 18, module federation, atomic design) with an AI assistant (aiRa) embedded for conversational configuration.

---

## Module Catalog

### Tier Management (Tiers Intelligence)

- **Purpose**: Defines tier hierarchies, eligibility criteria, upgrade/downgrade logic, renewal conditions, and validity for loyalty programs
- **Personas**: Maya (program manager — primary), Alex (approver — secondary), Priya (data analyst — tertiary)
- **Microservices**: pointsengine-emf (emf-parent) — tier evaluation, upgrade/downgrade strategies; intouch-api-v3 — REST API gateway for tier CRUD
- **Key Capabilities**:
  - Tier creation, editing, comparison matrix view
  - Eligibility KPI configuration (current points, lifetime points, spend, transaction count)
  - Downgrade logic with configurable grace periods and downgrade target tiers
  - Renewal condition management (spend/points threshold within a cycle)
  - Simulation mode (proposed change vs current member base impact)
  - Maker-checker approval workflow with audit trail
- **Data Owned**: Tier entity, slab/threshold configuration, tier downgrade strategy configuration
- **Integrations**:
  - Depends on: Points Engine (EMF) for evaluation execution, Member module for member-tier assignment
  - Consumed by: Benefits module (tier linkage), Subscriptions module (tier-based subscriptions), aiRa Context Layer
  - External: None
- **API Surface**: REST (intouch-api-v3) — `/tiers`, `/tiers/{id}`, `/tiers/{id}/simulate`, `/tiers/approvals`; Thrift (cross-service tier evaluation events)
- **Official Docs**: Not verified (docs.capillarytech.com unavailable during this review)
- **Doc Coverage**: none (not verified)
- **Status**: active (partially — existing tier config exists; new comparison matrix / simulation mode is planned in PRD v2.0)

---

### Benefits Module

- **Purpose**: First-class benefit management — organises benefit categories, links benefit instances to tiers with tier-specific values, and manages benefit lifecycle independently of promotions
- **Personas**: Maya (program manager), Alex (approver)
- **Microservices**: pointsengine-emf (existing `Benefits` entity — currently promotions-backed); intouch-api-v3 (REST API); EMF event forest (benefit award execution)
- **Key Capabilities**:
  - Benefit Category CRUD (net-new — CAP-185145): metadata grouping by categoryType, tier applicability, trigger event derivation
  - Benefit Instance creation: tier-specific value configuration within a category
  - Benefits listing view: searchable/filterable by category, tier, state
  - Maker-checker for category creation and instance changes
  - Matrix View: benefits x tiers grid with configuration gap indicators
  - aiRa-assisted category mapping from natural language
- **Data Owned**:
  - `benefits` table (existing — VOUCHER/POINTS types, promotion_id mandatory): current production entity
  - `benefit_category` table (planned — net-new, CAP-185145): category metadata layer
  - `benefit_instance` table (planned — net-new, CAP-185145): tier-specific value storage
- **Integrations**:
  - Depends on: Tier Management (tier IDs for instance linkage), V3 Promotions (existing benefits are promotions-backed — planned to decouple), Points Engine EMF (EARN_POINTS / bonus point execution)
  - Consumed by: Subscriptions module (benefit catalog for subscription benefit picker), aiRa Context Layer (benefit catalog in /program/{id}/context)
  - External: Support queue system (PRIORITY_SUPPORT entitlement), Shipping service (FREE_SHIPPING waiver)
- **API Surface**: REST — `/benefits` (existing), `/benefit-categories` (planned), `/benefit-instances` (planned)
- **Official Docs**: Not verified (docs.capillarytech.com unavailable during this review)
- **Doc Coverage**: none (not verified)
- **Status**: active (partially — existing benefits model is promotions-backed; new category/instance model is planned in PRD v2.0 / CAP-185145)

---

### Subscription Programs

- **Purpose**: Manages paid and free subscription programs that grant members tier access or standalone benefits for a defined duration
- **Personas**: Maya (program manager), Alex (approver)
- **Microservices**: intouch-api-v3 (subscription CRUD, enrollment management); pointsengine-emf (partner program / tier sync)
- **Key Capabilities**:
  - Tier-Based and Non-Tier subscription models
  - Subscription lifecycle: Draft → Pending Approval → Scheduled → Active → Paused → Expired → Archived
  - Future-dated enrollment (PENDING state with membershipStartDate)
  - Pricing management with per-enrollment effectivePrice capture
  - Benefit linkage within subscription creation flow
  - Tier Downgrade on Exit configuration
  - aiRa-assisted subscription creation
- **Data Owned**: Subscription program records, enrollment records (PENDING/ACTIVE/EXPIRED states), effectivePrice per enrollment
- **Integrations**:
  - Depends on: Tier Management (linked tier for Tier-Based subscriptions), Benefits Module (benefit catalog for subscription benefits step), Points Engine EMF (partner program APIs: linkCustomer, deLinkCustomer, customerPartnerProgramUpdate)
  - Consumed by: aiRa Context Layer (subscription state in /program/{id}/context)
  - External: None
- **API Surface**: REST — `POST/GET v2/partnerProgram/linkCustomer`, `POST v2/partnerProgram/deLinkCustomer`, `GET v2/partnerProgram/customerActivityHistories`, `/subscriptions`, `/subscriptions/{id}`, `/subscriptions/{id}/benefits`, `/subscriptions/{id}/simulate`, `/subscriptions/approvals`
- **Official Docs**: Not verified
- **Doc Coverage**: none (not verified)
- **Status**: active (partially — existing partner program APIs exist; new listing/creation UI and enrollment PENDING state are planned in PRD v2.0)

---

### aiRa Configuration Layer

- **Purpose**: Conversational AI assistant embedded in Garuda for intent-driven tier/benefit/subscription configuration, impact simulation queries, and natural language config validation
- **Personas**: Maya (primary user of conversational path), Alex (impact summary in approval view)
- **Microservices**: Dedicated aiRa service (external to emf-parent / intouch-api-v3); Context Layer API (`/program/{id}/context`) served by intouch-api-v3
- **Key Capabilities**:
  - Intent parsing → structured config object generation
  - Program context awareness (tiers, benefits, member distribution, change history)
  - Proactive configuration validation (flag inconsistencies before save)
  - Benefit and tier recommendations based on industry patterns
  - Natural language queries against program state
  - Generative UI (config chips, preview tables, impact bars, action buttons)
- **Data Owned**: None — reads from Context Layer; no direct DB ownership
- **Integrations**:
  - Depends on: `/program/{id}/context` API (program state), all CRUD APIs (tier, benefit category, subscription), `/tiers/{id}/simulate` (impact simulation)
  - Consumed by: None (terminal consumer)
  - External: LLM inference (Anthropic or similar)
- **API Surface**: `POST /aira/intent` (intent parsing); `GET /program/{id}/context` (context layer — also used directly by the UI)
- **Official Docs**: Not verified
- **Doc Coverage**: none (not verified)
- **Status**: active (aiRa side panel infrastructure exists; loyalty-specific context layer is planned in PRD v2.0)

---

## Integration Map

| Source Module | Target Module | Integration Style | Purpose |
|---|---|---|---|
| Tier Management | Points Engine EMF | Thrift / async events | Tier evaluation execution, upgrade/downgrade triggers |
| Benefits Module | Tier Management | Sync REST | Tier ID lookup for benefit instance linkage |
| Benefits Module | Points Engine EMF | Async event / promotion rule | EARN_POINTS and bonus point benefit execution |
| Benefits Module | V3 Promotions | Sync (existing) | Existing benefits are promotion-backed (planned to decouple) |
| Subscriptions | Points Engine EMF | Sync REST | Partner program link/delink APIs for enrollment lifecycle |
| Subscriptions | Tier Management | Sync REST | Tier lookup for Tier-Based subscription linked tier |
| Subscriptions | Benefits Module | Sync REST | Benefit catalog read for subscription benefits step |
| aiRa Context Layer | All modules | Sync REST (read) | Aggregates program state for aiRa intelligence |
| aiRa | All CRUD APIs | Sync REST (write) | Creates/updates tiers, categories, subscriptions via standard APIs |

---

## Domain Model

| Entity | Owning Module | Description | Key Relationships |
|---|---|---|---|
| Program | Platform Core | Top-level loyalty program container | Parent of: Tier, BenefitCategory, Subscription |
| Tier | Tier Management | A ranked status level within a program | Belongs to: Program; Linked to: BenefitInstance, Subscription (tier-based) |
| BenefitCategory | Benefits Module | Metadata grouping for benefits — no reward values | Belongs to: Program; Parent of: BenefitInstance; Has: categoryType, tierApplicability |
| BenefitInstance | Benefits Module | Tier-specific configured value for a category | Belongs to: BenefitCategory + Tier; Carries: reward value, trigger configuration |
| Benefits (legacy) | Benefits Module | Existing promotions-backed benefit entity | Belongs to: Program; Links to: promotion_id (V3 Promotions) |
| Subscription | Subscriptions | A membership program granting tier or benefit access | Belongs to: Program; Optional link to: Tier; Links to: BenefitInstance |
| Enrollment | Subscriptions | Member's participation in a subscription | Belongs to: Subscription + Member; Has: effectivePrice, state, membershipStartDate |

---

## Cross-Cutting Concerns

- **Multi-tenancy (orgId)**: All entities are scoped by `org_id`. Every query filters by org_id. Existing entities use composite PKs `(id, org_id)`. New Benefit Category entity should follow this pattern.
- **Maker-Checker**: Two-step approval workflow (DRAFT → PENDING_APPROVAL → ACTIVE) applies to Tier config changes, Benefit Category creation, Benefit Instance changes, and Subscription program changes. Approval queue surfaced in intouch-api-v3.
- **Audit Trail**: `created_by`, `created_on`, `auto_update_time` are standard fields on all mutable entities. A richer change log (old value → new value, actor, approver) is introduced by Tier Change Log (E1-US5) — Benefits module should use the same mechanism.
- **API Validation**: All create/edit APIs must return structured field-level validation errors (not 500). Validation logic lives in the API, not in frontend form logic. This is a stated PRD principle (§10.1).

---

## Doc/Code Drift Log

| Module | What Docs Say | What Code Does | Severity | Resolved? |
|---|---|---|---|---|
| Benefits Module | BRD v2.0: Benefits are a first-class module with categoryType-driven trigger logic and no mandatory promotion link | Code: `benefits` table has `promotion_id NOT NULL`; `BenefitsType` enum is `{VOUCHER, POINTS}` only | High | No — this is the planned migration target |
| Benefits Module | BRD v2.0: `categoryId` typed as `String (UUID)` | Code: all existing entities use `int` PKs with `org_id` composite | High | No — pending decision (see BE-01 in brdQnA.md) |
| Benefits Module | BRD v2.0: BADGE, FREE_SHIPPING, PRIORITY_SUPPORT, EARN_POINTS multiplier as benefit delivery types | Code: no implementation found for these types | High | No — net-new capabilities planned in CAP-185145 |
| docs.capillarytech.com | Not verified — WebFetch unavailable | N/A | N/A | No — gap to be resolved in future ProductEx run |
