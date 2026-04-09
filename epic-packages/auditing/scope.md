# Epic: Auditing
Owner: Anuj
Layer: 1 (start immediately -- no upstream dependencies)

## What this epic covers

Build the entity-agnostic Audit Trail Framework as a shared module, plus the
change log listing REST API and CSV export capability.

### User Stories (from BRD E1-US5)
- As Priya, I want to see a complete history of every change made to tier configuration
- Who made the change, when, and what it replaced
- Filterable by: date range, actor, field, approval status
- Export: CSV or PDF for audit/reporting

## Shared modules
- **BUILDS**: audit-trail-framework -- you own this. Publish the interface first.
- **CONSUMES**: none -- this module has no upstream shared dependencies.

## Interface Contract (binding)
See `/interfaces/config-audit-service.java` in the registry for the full ConfigAuditService interface.
See `/interfaces/config_management.thrift` for Thrift IDL (ChangeSource enum, ConfigAuditRecord struct).
See `/interfaces/shared-db-schema.sql` for the config_audit_log table DDL.

## Build order
1. DB migration: Create config_audit_log table (Flyway)
2. Core entity: ConfigAuditEntry JPA entity, ChangeSource enum
3. AuditQueryFilter value object
4. ConfigAuditService implementation (record, getHistory, listChanges, countChanges, exportCsv)
5. REST API: ChangeLogController in intouch-api-v3
   - GET /v3/audit/changes?entityType=TIER&from=...&to=...&actor=...
   - GET /v3/audit/changes/{entityType}/{entityId}/history
   - GET /v3/audit/changes/export?format=csv
6. Tests: Unit tests for service, integration tests for API

## Code locations
- Core (entity, service, DAO): `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/`
  - New package: `services/audit/`
  - New entity in: `entity/` (ConfigAuditEntry, ChangeSource)
- API: `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/`
- Reference: existing `AuditDiffGenerator.java` in intouch-api-v3 (reuse for diff logic)

## Existing patterns to follow
- AuditDiffGenerator.java -- generic JSON diff, reuse directly
- SlabUpgradeAuditLogService.java -- audit log pattern (slab-specific, generalize)
- SlabDowngradeAuditLogService.java -- audit log pattern (slab-specific, generalize)
- AuditTrailDiffDto.java -- DTO with componentType, id, lastUpdatedOn/By, oldValue, newValue
- AuditLogTrailDto.java -- wrapper with publishedOn + list of diffs
- PEAuditTrailHelper.java -- promotion change detection logic (pattern reference)
- TargetGroupAuditLogDao.java -- existing audit DAO in intouch-api-v3 (pattern reference)
- AuditTrailConstants.java -- constants for audit log types
- AuditLogsQueryParamValidator.java -- existing query param validation
