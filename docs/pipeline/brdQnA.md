# BRD Review — Product Expert Analysis

> BRD: Tiers & Benefits — aiRa-Powered Conversational Configuration (v2.0, March 2026)
> Reviewed against: codebase (emf-parent, intouch-api-v3), docs.capillarytech.com (partial — most tier/benefit docs returned 404), docs/product/
> Date: 2026-04-06
> Reviewer: ProductEx (brd-review mode)

---

## Alignment with Current Product

### Confirmed Alignments

- **Tier/Slab terminology** — The codebase consistently uses `Slab` as the internal term for what the BRD calls "Tier". Both exist in the product: `ProgramSlab`, `SlabUpgradeService`, `SlabDowngradeService`, etc. The BRD's use of "Tier" is the UI-facing label; "Slab" is the backend/data model term. These map to the same concept. _(C6 — confirmed from codebase entities)_
- **Tier upgrade/downgrade mechanics** — Upgrade and downgrade are live, implemented features. Evidence: `SlabUpgradeService`, `SlabDowngradeService`, `TierUpgradeHelper`, `TierDowngradeTest`, `TierDowngradeDateCalculator` (multiple strategies: Cyclic, Fixed, FixedCustomerRegistration, SlabUpgradeBased). _(C7 — direct codebase evidence)_
- **Tier renewal** — `RenewSlabInstruction`, `RenewSlabInstructionImpl`, `TierRenewalTest` confirm renewal is an implemented operation. _(C7)_
- **Benefits entity exists** — `Benefits.java` entity with table `benefits`, `BenefitsType` enum (VOUCHER, POINTS), `BenefitTrackingService`, `CustomerBenefitTracking` all exist. _(C7)_
- **Maker-checker pattern exists** — `intouch-api-v3` contains `ApprovalStatus` enum, `RequestManagementController` (`PUT /v3/requests/{entityType}/{entityId}/status`), `PromotionReviewRequest`, maker-checker terminology in multiple test files. The approval workflow is implemented for promotions. _(C6)_
- **Audit trail exists** — `SlabUpgradeAuditLogService`, `SlabDowngradeAuditLogService`, `/audit/logs` endpoint in `ProgramsApi` confirm audit logging is in place. _(C7)_
- **Program-scoped configuration** — `ProgramSlab` is scoped to `programId` + `orgId`, consistent with the BRD's assumption that tiers are per-program. _(C7)_
- **Downgrade-on-return-transaction toggle** — `TierConfiguration.isDowngradeOnReturnEnabled` field exists in the backend DTO. BRD Section 12 asks whether to surface or deprecate it — it is actively used in the backend today. _(C7)_

---

## Conflicts with Current Product

| # | BRD States | Product Reality | Source | Severity |
|---|---|---|---|---|
| 1 | Benefits are "first-class objects" not tied to promotions. BRD proposes standalone benefits with their own listing, creation, categories, lifecycle. | `Benefits.java` entity has a `promotionId` field (non-null). Today's `Benefits` are coupled to a promotion ID at the data model level — they are not standalone. "Benefits as a Product" (E2) requires either a schema migration or a new entity. | `Benefits.java` line 48–51 | **High** |
| 2 | Benefit types supported: Points Multiplier, Flat Points Award, Coupon Issuance, Badge Award, Free Shipping, Custom | Current `BenefitsType` enum has only two values: `VOUCHER` and `POINTS`. Free Shipping, Badge Award, Points Multiplier (vs flat), and Custom type do not exist in the current type system. | `BenefitsType.java` | **High** |
| 3 | Benefit can be "linked to multiple tiers with different parameter values per tier (e.g., Gold gets 2x, Platinum gets 3x)" | No evidence of per-tier parameter values on benefits in the current entity model. `Benefits.java` has no tier linkage fields. Tier-benefit linkage relationship table is not visible in source (may exist in MongoDB as `BenefitConfig`, but `LinkedBenefit.class` exists without visible source). | `Benefits.java`, compiled `LinkedBenefit.class` | **High** |
| 4 | BRD proposes a "program context API" (`GET /program/{programId}/context`) that returns full tier/benefit state, member distribution, and change history for aiRa | No such endpoint or service exists in the scanned codebase. `SimulateTransactionAddTest` exists but tests EMF transaction simulation, not tier impact simulation. | Codebase scan (no match for `/program/{programId}/context`) | **High** |
| 5 | BRD proposes `/tiers/{tierId}/simulate` — impact simulation as a backend API call | No simulation endpoint found in the current API surface. Simulation logic for tier impact does not appear to exist as a standalone service. | Codebase scan | **High** |
| 6 | Maker-checker for Tiers specifically — "every tier config change creates a pending record" | Current maker-checker (approval flow) in `intouch-api-v3` is implemented for **promotions** only (`RequestManagementController` uses `EntityType`, `UnifiedPromotion`). No evidence of this being wired for tier CRUD operations. | `RequestManagementController.java`, `ApprovalStatus.java` | **High** |
| 7 | BRD treats Benefits as having their own maker-checker (E2 scope includes "maker-checker, state lifecycle") | Same as #6 — approval flow exists only for promotions. No benefit-specific approval pathway was found. | `intouch-api-v3` approval code | **Medium** |
| 8 | BRD proposes tier status model: Active, Draft, Pending Approval, Stopped | Current `ProgramSlab` entity has no `status` column — it uses `serialNumber` and `name`. Status lifecycle for tiers does not exist in the current data model. | `ProgramSlab.java` | **High** |
| 9 | Benefits categories: Earning, Redemption, Coupon, Badge, Communication, Custom | No category field exists on `Benefits.java`. The concept of benefit categories is not represented in the current schema. | `Benefits.java` | **Medium** |
| 10 | `TierConfiguration.isDowngradeOnReturnEnabled` (BRD asks if it should be "surfaced or deprecated") | This flag is actively wired in `TierConfiguration.java` and is serialized as `isDowngradeOnReturnEnabled`. Deprecating it has downstream impact on existing configured programs. | `TierConfiguration.java` line 29 | **Medium** |
| 11 | BRD proposes `dailyDowngradeEnabled` as an inferred config | `TierConfiguration.dailyDowngradeEnabled` already exists as a field — this is not a new concept but an existing backend capability the BRD doesn't acknowledge. | `TierConfiguration.java` line 31 | **Low** |
| 12 | The BRD's proposed REST paths (`/tiers`, `/benefits`) are new resource-centric APIs | Current tier/benefit API surface is organized as `/programConfig/{org_id}/programs/{program_id}` and `/programs/{program_id}/promotions/...`. The BRD's API shape represents a significant API contract redesign, not an incremental addition. | `ProgramsApi.java` endpoint mapping | **Medium** |

---

## Open Questions

> Every question MUST have an **Owner** tag indicating which team or agent is responsible for answering it.
>
> Team tags: `[Product]` `[Design/UI]` `[Backend]` `[Infra]` `[AI/ML]` `[Cross-team]`
> Agent tags: `[BA]` `[Architect]` `[Analyst]` `[ProductEx]`
> Status: `open` | `resolved: <answer>` | `deferred: <reason>`

### Product Behaviour Questions

| # | Owner | Question | Context | Why It Matters | Status |
|---|---|---|---|---|---|
| PB-1 | [Product] | Is "Benefits as a Product" (E2) truly separate from Promotions, or is a Benefit always backed by a Promotion in the platform's data model? | `Benefits.java` has a non-null `promotionId` foreign key today. The BRD wants benefits to be independent. | If benefits remain promotion-backed, E2 requires a schema migration + new service design. If they are to be truly standalone, existing benefits data must be migrated. This is a foundational architectural decision. | open |
| PB-2 | [Product] | When a tier configuration change is submitted and enters "Pending Approval" state, does the live program continue to use the old tier config until approval? Or is it frozen? | BRD says maker-checker is native for every config change (E1-US4), but doesn't specify what happens during the approval window. | Directly affects member evaluation outcomes during the approval gap. | open |
| PB-3 | [Product] | Can a benefit be linked to tiers across different programs, or is the benefit always scoped to a single program? | BRD Section 12 Q4 is open on this. `Benefits.java` has a `programId` field implying single-program scope today. | Affects whether multi-program benefit reuse is a Phase 1 or Phase 2 concern. | open |
| PB-4 | [Product] | What happens to member tier status during a tier restructure (e.g., threshold change)? Are affected members re-evaluated immediately or at the next evaluation cycle? | BRD mentions "estimated 2,300 members from Gold to Silver at next evaluation" — but doesn't specify when actual re-evaluation happens post-approval. | Critical for impact simulation accuracy and for the notification design. | open |
| PB-5 | [Product] | Is the "30-day grace period" for downgrade the same as the existing `TierDowngradePeriodConfig` / `TierDowngradeConditionConfig` mechanism? | These classes exist in the codebase. The BRD presents grace period as a new UI-level concept. | If grace period is already a backend config, it is a UI-exposure problem, not a backend build. Scope changes significantly. | open |
| PB-6 | [Product] | Should the `isDowngradeOnReturnEnabled` toggle (currently `TierConfiguration.isDowngradeOnReturnEnabled`) be surfaced as a visible field in the new tier editing UI, or hidden/deprecated? | BRD Section 12 Q6 is open. The field is live in `TierConfiguration.java`. | Deprecating it can silently change behavior for programs that have it enabled. Must be an explicit product decision, not an assumption. | open |
| PB-7 | [Product] | What is the intended tier status lifecycle state machine? The BRD lists Active, Draft, Pending Approval, Stopped — but does not define valid transitions (e.g., can an Active tier move to Draft? Can a Stopped tier be reactivated?). | `ProgramSlab` has no status column today — this is entirely new. | The status machine must be defined before backend design can begin. Gaps in transition logic will cause UX dead-ends. | open |

### Design & UX Questions

| # | Owner | Question | Context | Why It Matters | Status |
|---|---|---|---|---|---|
| DX-1 | [Design/UI] | When a tier is in "Pending Approval" state, what can the original requester do? Can they withdraw the request? Can they make further changes? | BRD defines the approver flow (approve/reject/request changes) but not the requester's experience after submission. | Affects the "Request Changes" flow — does rejection return to draft, or does the requester need to create a new change request? | open |
| DX-2 | [Design/UI] | The BRD proposes Option A (hybrid) as the pod recommendation. Is Option B (fully conversational) definitively deferred, or is the team still deciding? Section 2 says the pod decides. | BRD Section 5 and Out-of-Scope Section 11 suggest Option B is Phase 2, but framing is ambiguous. | If Option B is still under discussion, the API contract design (especially the `/aira/intent` endpoint) may need to be more flexible. | open |
| DX-3 | [Design/UI] | The comparison matrix lists "Color" as a configuration dimension for each tier. Where is tier color stored today? | No color field exists in `ProgramSlab.java` or any visible tier entity. | If color is a new field, it requires a schema addition. If it currently lives in `metadata` (JSON blob on `ProgramSlab`), the UI must extract it. | open |

### Backend & Technical Questions

| # | Owner | Question | Context | Why It Matters | Status |
|---|---|---|---|---|---|
| BT-1 | [Backend] | `TierConfigController` and `BenefitConfigController` exist only as compiled `.class` files — no Java source was found in `pointsengine-emf/src/main`. Are these controllers in a different branch, or were the source files deleted? | Compiled class files present at `target/classes/...` but no `.java` source counterparts found. | This is a blocking gap for the Architect. If these controllers already implement tier/benefit CRUD, significant design and implementation work may already exist. Must be confirmed before Phase 6. | open |
| BT-2 | [Backend] | `BenefitConfigService.class` and `BenefitConfigRequest.class` (with `LinkedTierRequest` inner class) exist in compiled form. Do these implement the benefit-tier linkage the BRD requires, or are they partial/different implementations? | These are compiled artifacts. Source is absent. | Prevents accurate impact analysis. The Architect cannot design without knowing what already exists. | open |
| BT-3 | [Backend] | Does the program context API (`GET /program/{programId}/context`) need to be built from scratch, or does an internal aggregation service already exist that could be adapted? | BRD Section 12 Q1 flags this as open. No such API found in the codebase. | This is the foundational dependency for all aiRa capabilities (E3). If it doesn't exist, it is a significant backend build, not just an API exposure task. | open |
| BT-4 | [Backend] | Impact simulation (`/tiers/{tierId}/simulate`) — what data source will it run against? Is there a member-tier snapshot available in MySQL/MongoDB, or does it require a separate data pipeline? | BRD Section 12 Q2 asks about real-time vs queued. `SimulateTransactionAddTest` in EMF tests transaction simulation, not member distribution simulation. | Determines whether simulation is a synchronous API call or an async job with polling. Affects UX significantly. | open |
| BT-5 | [Backend] | The BRD proposes new API paths (`/tiers`, `/benefits`, `/tiers/approvals`). What service/module will own these endpoints? Will they live in `intouch-api-v3` (current REST gateway), `pointsengine-emf` (current program config service), or a new service? | Current tier config lives at `/programConfig/{org_id}/programs/{program_id}` in `pointsengine-emf`. The BRD proposes a cleaner resource-centric surface. | Service ownership must be decided before API contracts can be written. Cross-service routing (if in `intouch-api-v3`) or direct access (if in `pointsengine-emf`) has different auth/tenancy implications. | open |
| BT-6 | [Backend] | The `Benefits` entity has `benefit_type` as an enum (VOUCHER, POINTS only). Adding new types (Points Multiplier, Coupon Issuance, Badge Award, Free Shipping, Custom) requires either enum expansion or a type system redesign. Is this a backward-compatible change? | `BenefitsType.java` has only VOUCHER and POINTS. Existing data uses these values. | If programs already have configured benefits with type VOUCHER or POINTS, renaming or restructuring the type system risks data integrity. | open |
| BT-7 | [Backend] | Maker-checker for tiers: does the existing `RequestManagementController` (`PUT /v3/requests/{entityType}/{entityId}/status`) support extensible entity types, or is it hardcoded for promotions only? | `EntityType` enum is used in the controller. Its values determine whether new entity types (TIER, BENEFIT) can be added without a new workflow service. | If `EntityType` is extensible, the approval workflow reuse is feasible. If not, E1-US4 requires a new approval service. | open |
| BT-8 | [Backend] | The `isDowngradeOnPartnerProgramExpiryEnabled` field in `TierConfiguration` suggests partner-program tier sync is an active feature. Does the new tier management UI need to surface partner program tier sync configuration? | BRD is entirely silent on partner program integration for tiers. `PartnerProgramTierSyncConfiguration`, `RenewTierBasedOnPartnerProgramActionImpl`, `UpgradeTierBasedOnPartnerProgramActionImpl` are in the codebase. | If ignored, the new UI will be unable to manage all existing tier configurations for programs using partner program sync. | open |

### Missing Specifications

| # | Owner | Missing Area | Current Product Behaviour | Recommendation | Status |
|---|---|---|---|---|---|
| MS-1 | [Product] | Multi-program tier configuration — BRD assumes one program at a time, but `Benefits.linkedProgramType` (`BenefitsLinkedProgramType` enum) and partner-program sync suggest benefits/tiers can span program types. | Tier and benefit entities are scoped to a `programId`. Multi-program handling is a separate concern. | BRD should specify whether the new UI supports multi-program programs (coalition, subscription) explicitly, or defers this to Phase 2. | open |
| MS-2 | [Product] | Notification / communication config for tier events — BRD mentions "nudge/communication config" and "expiry communication" as optional tier fields and capability 3 of aiRa, but does not specify how this integrates with Engage+ or the existing communication action system. | Communication actions (`PeEmailActionCreator`, `PeSMSActionCreator`, `PeMessageActionCreator`) already exist in the promotion/rule system. | The BRD must specify whether tier event notifications reuse the existing communication action framework or introduce a new dedicated notification model. | open |
| MS-3 | [Product] | Role-based access for maker-checker — BRD (Section 12 Q3) acknowledges this is undefined. The current `RequestManagementController` uses `IntouchUser` from `AbstractBaseAuthenticationToken` but doesn't show role-gating. | Approval flow exists but approver role configuration is not defined. | BRD must specify: who can be configured as an approver, is it per-org or per-program, and what RBAC role maps to "approver". | open |
| MS-4 | [Backend] | Error handling contract — BRD states "every create/edit API must return a structured validation error object (field-level, human-readable)" but does not define the error response schema. | Current `RequestValidationException`, `InvalidProgramException` etc. exist but error shape varies. | The error response schema must be standardized and specified in the BRD before implementation begins. | open |
| MS-5 | [Product] | Simulation data freshness — BRD mentions "against historical data" and "daily snapshots sufficient for Phase 1" in Out-of-Scope, but the member distribution shown in the simulation is expected to be current. If snapshots are daily, a simulation run at 11pm may use data that is 23 hours stale. | No member snapshot service was found in the codebase. | BRD must specify the acceptable staleness window for simulation data and how users will be informed of data freshness. | open |
| MS-6 | [Infra] | aiRa context API latency — BRD Section 12 Q1 asks about p99 latency for the context API. The aiRa panel loads when a user clicks "Configure with aiRa" — if the context API is slow, the panel appears unresponsive. | No context API exists today. | A latency SLA must be defined for the context API before architecture is finalized. A cold-start vs cached response strategy is needed. | open |

### Domain & Terminology Questions

| # | Owner | BRD Term | Established Term | Clarification Needed | Status |
|---|---|---|---|---|---|
| DT-1 | [Product] | "Tier" | "Slab" (backend/codebase), "Tier" (docs/UI) | The codebase universally uses "Slab" internally (`ProgramSlab`, `SlabUpgradeService`, `TierDowngradeSlabConfig`). The BRD uses "Tier" exclusively. Engineers must know that Tier = Slab in the domain model to avoid naming confusion in new code. Recommend establishing "Tier" as the canonical UI term and "Slab" as the legacy internal term, with new code using "Tier". | open |
| DT-2 | [Product] | "Benefits" | "Benefits" (existing entity, promotion-backed) | BRD uses "Benefits" to mean a new standalone entity. The codebase already has a `Benefits` entity (table: `benefits`) that is promotion-coupled. Name collision risk. The new entity needs a distinct name or the existing entity needs a migration plan. | open |
| DT-3 | [Product] | "Upgrade bonus" (optional tier field in BRD) | `UpgradeSlabAction`, `UpgradeTierBasedOnPartnerProgramAction` | Is "upgrade bonus" the same as the existing `UpgradeSlabAction`? If so, this is a UI-exposure task. If it means points awarded specifically upon tier upgrade entry (not the upgrade trigger itself), it may need new action logic. | open |
| DT-4 | [Product] | "Renewal condition" | Not clear — `RenewSlabInstruction` exists but the condition definition mechanism is not visible | The BRD uses "renewal condition" as a field in both tier config and simulation. How is a renewal condition currently defined in the backend? Is it a rule/expression or a simple threshold? | open |
| DT-5 | [AI/ML] | "aiRa" | Not in codebase — no aiRa-related code found in scanned repos | Is the aiRa integration layer (`/aira/intent` endpoint, context layer) a new microservice, or an extension of an existing LLM gateway? The BRD assumes it exists as a "production-ready side panel" but provides no backend evidence. | open |
| DT-6 | [Product] | "Industry Patterns" (aiRa capability) | Not in codebase | BRD states aiRa will use "anonymized patterns from similar programs in the Capillary network". Where is this data stored? Is there a benchmark data service? This is not described anywhere in the platform documentation found. | open |

### Cross-Cutting Concern Gaps

| # | Owner | Concern | What BRD Should Address | Status |
|---|---|---|---|---|
| CCG-1 | [Cross-team] | Multi-tenancy (org isolation) | Every BRD API endpoint must be scoped to `orgId`. Current tier/benefit entities use an `OrgEntityIntegerPKBase` composite key (`orgId` + `id`). The BRD's proposed API paths (`/tiers`, `/benefits`) do not show `orgId` scoping. The API contract must specify how org context is passed (header? path parameter? auth token?). | open |
| CCG-2 | [Cross-team] | Audit trail for benefit changes | BRD specifies audit trail for tier changes (E1-US5) but does not specify audit requirements for benefit configuration changes. Is there an equivalent changelog for benefits? | open |
| CCG-3 | [Infra] | PII masking in simulation export | BRD mentions "export list of affected member IDs with PII masking for non-admin roles" (E1-US6). No PII masking service was found in the scanned codebase. This is a cross-cutting concern requiring a dedicated implementation or integration with an existing masking service. | open |
| CCG-4 | [Backend] | Cache invalidation on tier config change | Tier configuration is very likely cached (the platform processes "millions of tier evaluations per day" per BRD). Any config change via the new APIs must trigger cache invalidation. The BRD does not address this. | open |
| CCG-5 | [Cross-team] | Backward compatibility of existing tier API consumers | The new APIs (`/tiers`, `/benefits`) will coexist with or replace the existing `/programConfig` and `/programs/.../promotions` APIs. Existing consumers (internal services, customer-facing APIs, Thrift callers) must not break. BRD does not address migration or deprecation of the old API surface. | open |
| CCG-6 | [Infra] | Impact simulation data pipeline | Simulation requires member-tier distribution data. This data either needs a dedicated aggregation job (batch, scheduled) or a live query against the `customer_slab_upgrade_history` (or equivalent) table. The BRD defers "real-time streaming" to Phase 2 but doesn't specify the Phase 1 snapshot strategy. | open |

---

## Summary

- **Total questions**: 31 (7 Product Behaviour, 3 Design/UI, 8 Backend/Technical, 6 Missing Specifications, 6 Domain/Terminology, 6 Cross-Cutting)
- **High severity conflicts**: 6 (Benefits entity coupling to promotions, BenefitsType enum gap, benefit-tier linkage model, missing context API, missing simulation API, maker-checker not wired for tiers)
- **Blocking gaps** (cannot proceed without answers): 4
  - BT-1/BT-2: Source code for TierConfigController and BenefitConfigController not found — may represent significant prior work
  - PB-1: Whether Benefits are or must become independent of Promotions (foundational data model question)
  - BT-5: Which microservice owns the new `/tiers` and `/benefits` endpoints

### Questions by Owner

| Owner | Open | Resolved | Blocking |
|-------|------|----------|----------|
| [Product] | 13 | 0 | 1 (PB-1) |
| [Design/UI] | 3 | 0 | 0 |
| [Backend] | 8 | 0 | 3 (BT-1, BT-2, BT-5) |
| [Infra] | 2 | 0 | 0 |
| [AI/ML] | 1 | 0 | 0 |
| [Cross-team] | 4 | 0 | 0 |

**Recommendation**: Pause for product team + backend team input on the 4 blocking gaps before Architect phase. The missing source code for `TierConfigController` and `BenefitConfigController` is the most urgent issue — if significant tier/benefit CRUD work already exists but wasn't committed to `feature-pipeline`, the Architect will design on a false premise.
