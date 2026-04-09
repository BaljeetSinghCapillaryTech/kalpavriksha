# Epic: Supplementary Partner Program Tiers
Owner: Anuj
Layer: 2 (starts after Audit Trail shared module is complete -- Anuj's own Layer 1 epic)

## What this epic covers

UI-facing config APIs for supplementary partner program tier management.
Extends existing PartnerProgram/PartnerProgramSlab codebase with REST APIs,
maker-checker integration, and audit trail integration.

NOTE: No dedicated BRD exists for this epic. Anuj will define scope during
the BA phase based on existing codebase patterns and product knowledge.

## Shared modules
- **BUILDS**: none
- **CONSUMES**: maker-checker-framework (owned by Ritwik)
- **CONSUMES**: audit-trail-framework (Anuj -- you built this in your Layer 1 epic)

## Build order
1. BA/PRD: Define scope based on existing PartnerProgram codebase + product knowledge
2. New DTOs: PartnerProgramTierListResponse, PartnerProgramTierCreateRequest, etc.
3. New service: PartnerProgramTierConfigService
4. Maker-Checker integration: config changes via MakerCheckerService
5. Audit integration: changes via ConfigAuditService (your own framework)
6. REST API: PartnerProgramTierController in intouch-api-v3
7. Tests

## Code locations
- Core: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/`
  - Existing: `impl/base/PartnerProgramImpl.java`, `impl/base/PartnerProgramSlabImpl.java`
  - Existing: `api/base/PartnerProgram.java`, `api/base/PartnerProgramSlab.java`
  - Existing: `event/profiles/PartnerProgramUpdateProfileImpl.java`
- Thrift: `Thrift/thrift-ifaces-emf/emf.thrift`
  - Existing: PartnerProgramTierUpdateInfo, PartnerTierUpdateType, PartnerProgramUpdateEventData
  - Existing: partnerProgramLinkingEvent, partnerProgramUpdateEvent, partnerProgramDeLinkingEvent
- API: `intouch-api-v3/` (currently NO partner program tier endpoints -- Thrift only)

## Existing codebase context
- PartnerProgramImpl.java handles SUPPLEMENTARY type with PartnerProgramCycle
- PartnerProgramSlabImpl has id, serialNumber, name
- PartnerProgramType.SUPPLEMENTARY enum value exists
- Thrift has linking/update/delinking events
- No REST API surface exists in intouch-api-v3 for this -- only Thrift services
- ConfigEntityType.SUPPLEMENTARY_PARTNER_PROGRAM already in shared interface design
