# Epic: Tier Category + Subcategory
Owner: Ritwik
Layer: 2 (starts after Maker-Checker + Audit Trail shared modules are available)

## What this epic covers

Tier Intelligence -- complete revamp of tier listing, comparison matrix, creation,
and editing. New UI-facing REST APIs on top of existing ProgramSlab/TierConfiguration.

### User Stories (from BRD E1-US1, E1-US2, E1-US3)
- E1-US1: Tier Listing with Comparison Matrix (all tiers side by side)
- E1-US2: Tier Creation (guided form + aiRa path)
- E1-US3: Tier Editing (inline for simple, aiRa for structural)
- KPI header: total tiers, active tiers, total members, tiers pending approval
- Status badges: Active, Draft, Pending Approval, Stopped
- Focus Mode: clicking tier header highlights that column
- On save with maker-checker: creates Draft, submits to approval queue

## Shared modules
- **BUILDS**: none
- **CONSUMES**: maker-checker-framework (Ritwik -- you built this in your Layer 1 epic)
- **CONSUMES**: audit-trail-framework (Anuj -- available after his Layer 1 merge)

## Build order
1. New DTOs: TierListingResponse, TierComparisonMatrix, TierCreateRequest, TierUpdateRequest
2. New service: TierConfigService (wraps existing ProgramSlab/TierConfiguration with new API surface)
3. Maker-Checker integration: tier create/edit goes through MakerCheckerService.submitForApproval()
4. Audit integration: direct edits call ConfigAuditService.record()
5. REST API: TierController in intouch-api-v3 (GET /tiers, POST /tiers, PUT /tiers/{id})
6. Tests

## Code locations
- Core: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/`
- Existing tier entities: ProgramSlab, TierConfiguration, SlabInfoModel, SlabMetaData
- Existing tier services: SlabUpgradeService, SlabDowngradeService, TierActionImpl
- Existing strategies: TierDowngradeStrategyConfiguration, AbstractTierDowngradeDateCalculator
- API: `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/`
- Existing config: OrgConfigController (DRAFT/LIVE pattern)
