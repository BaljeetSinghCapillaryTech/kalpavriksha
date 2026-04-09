# Epic: Maker Checker
Owner: Ritwik
Layer: 1 (start immediately -- no upstream dependencies)

## What this epic covers

Build the entity-agnostic Maker-Checker Framework as a shared module consumed by all
config-changing epics (Tier Category, Tier Benefits, Supplementary Partner Program).

### User Stories (from BRD E1-US4)
- As Alex, I want to review and approve every tier/benefit config change before it goes live
- Approval queue: dedicated "Pending Approval" view showing all pending changes
- Each pending item shows: diff view (old vs new), who requested, when, impact summary
- Approver actions: Approve (goes live), Reject (mandatory comment), Request Changes (returns to draft)
- Email + in-platform notification to approver on submission
- Audit log: every approval/rejection recorded (via Audit Trail integration)

### From Benefit Categories BRD (Section 5)
- All benefit instance config changes follow DRAFT -> PENDING_APPROVAL -> ACTIVE state machine
- Category creation (new categoryType) requires approval before instances can be created
- A change to an ACTIVE instance does not take effect until new version is approved

## Shared modules
- **BUILDS**: maker-checker-framework -- you own this. Publish the interface first.
- **CONSUMES**: audit-trail-framework -- owned by Anuj. Code against the interface mock until merged.

## Interface Contract (binding)
See `/interfaces/maker-checker-service.java` in the registry for the full MakerCheckerService interface.
See `/interfaces/config-audit-service.java` for the ConfigAuditService interface you call on approve.
See `/interfaces/config_management.thrift` for Thrift IDL.
See `/interfaces/shared-db-schema.sql` for the pending_changes table DDL.

## Build order
1. Thrift IDL: Add ConfigEntityType, ConfigStatus, ApprovalAction enums to Thrift
2. DB migration: Create pending_changes table (Flyway)
3. Core entities: PendingChange JPA entity, ConfigEntityType/ConfigStatus/ApprovalAction enums
4. State machine: StatusTransitionValidator generalization (entity-agnostic)
5. MakerCheckerService implementation (submit, review, list, getDiff)
6. Integration: Call ConfigAuditService.record() on APPROVE (mock during dev, real after Anuj merges)
7. REST API: ApprovalQueueController in intouch-api-v3 (GET /approvals, POST /approvals/{id}/review)
8. Tests: Unit tests for state machine, integration tests for full workflow

## Code locations
- Core (entities, service, DAO): `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/`
  - New package: `services/makerchecker/`
  - New entities in: `entity/` (PendingChange, ConfigEntityType, ConfigStatus, ApprovalAction)
- API: `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/`
  - Reference pattern: `unified/promotion/` (UnifiedPromotionFacade, StatusTransitionValidator)
- Thrift: `Thrift/thrift-ifaces-emf/emf.thrift` (or new config_management.thrift)

## Existing patterns to follow
- StatusTransitionValidator.java -- EnumMap-based state machine (generalize this)
- PromotionAction.java -- action enum with normalization (pattern reference)
- UnifiedPromotionFacade.java -- orchestration pattern (submit -> validate -> persist -> notify)
- AuditDiffGenerator.java -- JSON diff generation (reuse for getDiff)
- StatusChangeRequest.java -- DTO pattern for status change APIs
- PromotionReviewRequest.java -- DTO pattern for review actions
