# Product Registry

> Last updated: 2026-04-06
> Maintained by: ProductEx skill
> Source: Initial build from codebase scan (emf-parent, intouch-api-v3) + BRD review. Official docs at docs.capillarytech.com returned 404 for all specific feature pages attempted during initial scan.

---

## Product Overview

Capillary is an enterprise loyalty platform that enables brands to run points-based, tier-based, and behavioral loyalty programs for millions of members. It exposes functionality via a REST API gateway (intouch-api-v3), an internal points/rules engine (emf-parent / pointsengine-emf), and a Thrift-based RPC layer for cross-service communication. The configuration UI (Garuda) is being rebuilt as a React 18 module-federation application.

---

## Module Catalog

### Tiers (Slabs) Module
- **Purpose**: Defines member grading levels within a loyalty program. Controls who qualifies for each tier, how they move between tiers, and when/how tier status expires.
- **Personas**: Loyalty Program Manager (configuration), Platform Admin (approval/governance), Points Engine (runtime evaluation)
- **Microservices**: `pointsengine-emf` (owns tier configuration and runtime evaluation), `emf` (Thrift service layer)
- **Key Capabilities**:
  - Tier creation and configuration (threshold, KPI type, validity, schedule)
  - Tier upgrade evaluation (threshold-based, transaction-triggered)
  - Tier downgrade calculation (multiple strategies: Cyclic, Fixed, FixedCustomerRegistration, SlabUpgradeBased)
  - Tier renewal
  - Partner-program-based tier upgrade/renew (`RenewTierBasedOnPartnerProgramActionImpl`, `UpgradeTierBasedOnPartnerProgramActionImpl`)
  - Audit log for slab changes (`SlabUpgradeAuditLogService`, `SlabDowngradeAuditLogService`)
  - Downgrade-on-return-transaction toggle (`isDowngradeOnReturnEnabled`)
  - Daily downgrade (`dailyDowngradeEnabled`)
  - Partner program de-linking downgrade (`isDowngradeOnPartnerProgramExpiryEnabled`)
  - Tier-change window tracking (`TierChangeWindowStartDateComputer`)
- **Data Owned**:
  - `program_slabs` table (MySQL): `ProgramSlab` entity — id, orgId, programId, serialNumber, name, description, createdOn, metadata
  - `TierConfiguration` DTO (serialized to JSON, stored in org config system)
  - `CustomerSlabUpgradeHistoryInfo` (upgrade history)
  - `SlabChangeDetailsEntity` (change details)
- **Integrations**:
  - Depends on: Program module (programId scoping), EMF event system (tier events published via `TierUpgradeHelper`, `TierRenewedHelper`)
  - Consumed by: Points promotions (tier-based rules), Benefits module, Communication actions
  - External: Partner program sync via `PartnerProgramTierSyncConfiguration`
- **API Surface**:
  - `/programConfig/{org_id}/programs/{program_id}` — GET/POST for program configuration (includes tier config)
  - `/audit/logs` — audit trail for config changes
  - `TierConfigController.class` exists (compiled, no source found) — possible CRUD API exists
- **Official Docs**: https://docs.capillarytech.com/ (Loyalty+ > Strategies > Tiers section referenced in nav, but individual pages returned 404 during scan)
- **Doc Coverage**: partial (nav links visible, page content not accessible)
- **Status**: active

---

### Benefits Module
- **Purpose**: Defines rewards/incentives linked to tier membership. Currently promotion-coupled.
- **Personas**: Loyalty Program Manager (configuration), Points Engine (runtime award)
- **Microservices**: `pointsengine-emf` (entity and service layer), `emf` (BenefitConfig in MongoDB)
- **Key Capabilities**:
  - Benefit definition (type: VOUCHER or POINTS today)
  - Benefit tracking per customer (`CustomerBenefitTracking`, `CustomerBenefitTrackingLog`)
  - Avail benefit instruction (`AvailBenefitInstruction`)
  - Benefits awarded stats (daily summary, message queue, MongoDB fail-safe)
  - Tier-linked benefit config (`LinkedBenefit` model in MongoDB — compiled only)
  - `BenefitConfigService.class` and `BenefitConfigController.class` exist (compiled, no source)
- **Data Owned**:
  - `benefits` table (MySQL): `Benefits` entity — id, orgId, name, benefit_type (VOUCHER/POINTS), programId, **promotionId (non-nullable)**, description, maxValue, isActive, createdBy, createdOn, linked_program_type
  - `BenefitsAwardedStats` (MySQL)
  - `BenefitConfig` (MongoDB) — config document, structure not visible (compiled only)
  - `CustomerBenefitTracking` + `CustomerBenefitTrackingLog` (MySQL)
  - `PromotionBenefitsActionDailySummary` (MySQL)
- **Integrations**:
  - Depends on: Promotions module (current `promotionId` coupling), Program module, Tier module (LinkBenefit)
  - Consumed by: Communication actions, Analytics, Points Engine runtime
  - External: None identified
- **API Surface**:
  - `BenefitConfigController.class` exists (compiled, no source)
- **Official Docs**: Not found (benefits not prominently documented in accessible pages)
- **Doc Coverage**: none (from accessible docs)
- **Status**: active (partial — source code for CRUD controller missing from scanned branch)

> **WARNING**: `BenefitConfigController.class` and `TierConfigController.class` exist in `target/classes` but have no corresponding `.java` source files in `pointsengine-emf/src/main`. This may indicate prior implementation work exists on a different branch.

---

### Promotions / Points Engine Module
- **Purpose**: Rule-based engine that evaluates loyalty events (transactions, registrations) and executes actions (award points, upgrade tier, avail benefits, send communications).
- **Personas**: Loyalty Program Manager (config via UI), Points Engine (runtime), Thrift callers
- **Microservices**: `pointsengine-emf`, `emf`
- **Key Capabilities**:
  - Promotion CRUD (`/programs/{program_id}/promotions/add/{promotion_type}`, etc.)
  - Rule engine (JNODE-based expression evaluation)
  - Action types: AwardPoints, UpgradeSlab, DowngradeSlab, RenewSlab, AvailBenefit, AwardVoucher, SendCommunication, TagCustomer, TrackerAction, etc.
  - Capping (points/source-value/tracker/tender)
  - Promotion identifier validation
  - Audit logs
- **Data Owned**: Promotions, org config, rule definitions (MySQL + potentially MongoDB)
- **Integrations**:
  - Depends on: Program module, Tier module, Benefits module
  - Consumed by: intouch-api-v3 gateway, EMF Thrift service
- **API Surface**: REST at `/programs/{program_id}/promotions/...`, `/programConfig/...`, `/audit/logs`
- **Official Docs**: Partially documented at docs.capillarytech.com
- **Doc Coverage**: partial
- **Status**: active

---

### Approval / Maker-Checker Module
- **Purpose**: Governs config change approval workflows — changes go to "pending" state and require an approver's action before going live.
- **Personas**: Loyalty Platform Admin/Approver (approval actions), Program Manager (submitter)
- **Microservices**: `intouch-api-v3`
- **Key Capabilities**:
  - Status change for promotion entities (`PUT /v3/requests/{entityType}/{entityId}/status`)
  - `ApprovalStatus` enum: APPROVE, REJECT
  - Journey-based approval (`JourneyApproveResponse`, `JourneyWaitForApprovalResponse`)
  - `PromotionReviewRequest` DTO with comments
  - Status transition validation (`StatusTransitionValidatorTest`)
- **Data Owned**: Approval state is part of `UnifiedPromotion` document in MongoDB (`unified_promotions` collection)
- **Integrations**:
  - Depends on: Unified Promotion system, Journey service
  - Consumed by: UI (Garuda), intouch-api-v3 itself
- **API Surface**: `PUT /v3/requests/{entityType}/{entityId}/status`
- **Official Docs**: Not found
- **Doc Coverage**: none
- **Status**: active — currently scoped to promotion entities only

---

### Unified Promotion Module
- **Purpose**: Central document model for promotions with full lifecycle management (create, draft, review, activate, deactivate) stored in MongoDB.
- **Microservices**: `intouch-api-v3`
- **Key Capabilities**: CRUD (`/v3/promotions`), enrollment, status management, review/approval, stats, journey integration
- **Data Owned**: `unified_promotions` collection (MongoDB)
- **API Surface**: `/v3/promotions/*`, `/v3/requests/{entityType}/{entityId}/status`
- **Status**: active

---

## Integration Map

| Source Module | Target Module | Integration Style | Purpose |
|---|---|---|---|
| pointsengine-emf | EMF (Thrift) | Thrift RPC | Tier/slab operations, points processing |
| intouch-api-v3 | pointsengine-emf | sync REST | Program config, promotion management |
| intouch-api-v3 | Journey service | sync REST | Approval workflow orchestration |
| Tier module | EMF event system | async event | Publish tier upgrade/renewal events |
| Tier module | Communication actions | indirect (rule engine) | Trigger notifications on tier events |
| Benefits module | Promotions module | shared DB (promotionId FK) | Benefits are promotion-coupled today |

---

## Domain Model

| Entity | Owning Module | Description | Key Relationships |
|---|---|---|---|
| ProgramSlab | Tiers | A tier within a loyalty program. Internal name: Slab. | belongs to Program (programId + orgId) |
| TierConfiguration | Tiers | JSON config for downgrade/renewal rules | linked to org config system, not directly to ProgramSlab |
| Benefits | Benefits | A reward/incentive. Currently promotion-coupled. | belongs to Program; non-nullable promotionId FK |
| BenefitConfig | Benefits | MongoDB config document for benefit configuration | linked to Benefits entity |
| LinkedBenefit | Benefits | Links a benefit to tiers (MongoDB) | child of BenefitConfig |
| CustomerBenefitTracking | Benefits | Tracks per-customer benefit usage | links Customer, Benefit |
| UnifiedPromotion | Promotions | Full promotion document with lifecycle | MongoDB document; has status, activities, parentId |
| CustomerSlabUpgradeHistoryInfo | Tiers | History of tier upgrades per customer | links Customer, Slab |
| SlabChangeDetailsEntity | Tiers | Details of a specific slab change event | links to audit system |

---

## Cross-Cutting Concerns

- **Multi-tenancy**: All entities use composite PK (`OrgEntityIntegerPKBase`): id + orgId. API calls must carry org context.
- **Audit trail**: `/audit/logs` endpoint + `SlabUpgradeAuditLogService`/`SlabDowngradeAuditLogService` for tier. `UnifiedPromotion` carries change history.
- **Authentication**: `AbstractBaseAuthenticationToken` / `IntouchUser` provides orgId + role. Used in intouch-api-v3.
- **Approval flow**: `RequestManagementController` in intouch-api-v3 — currently promotion-scoped only.

---

## Doc/Code Drift Log

| Module | What Docs Say | What Code Does | Severity | Resolved? |
|---|---|---|---|---|
| Tiers | Docs reference tier configuration pages but all specific pages returned 404 | Code has full implementation (upgrade/downgrade/renewal/audit) | medium | No — docs likely exist but are inaccessible to the scan |
| Benefits | Docs not found for benefits | Code has `Benefits` entity coupled to promotions | medium | No |
| Maker-checker | Not documented in accessible pages | Implemented for promotions in intouch-api-v3, not for tiers/benefits | low | No |
