# Warnings for Auditing

## DO NOT
- DO NOT modify the existing SlabUpgradeAuditLogService or SlabDowngradeAuditLogService -- they are slab-specific and work with the current audit trail. Build a NEW generic ConfigAuditService alongside them.
- DO NOT modify the existing AuditTrailDiffDto or AuditLogTrailDto -- they use AuditLogSlabChangeDto which is slab-specific. Create new generic DTOs.
- DO NOT modify the existing PEAuditTrailHelper -- it handles promotion-specific change detection. Your service is entity-agnostic.
- DO NOT build your own approval workflow -- that is the maker-checker-framework owned by Ritwik.

## COLLISION HOTSPOTS
- `emf.thrift` -- coordinate with Ritwik if both need to add to this file. Use shared `config_management.thrift`.
- `/audit/logs` endpoint already exists in ProgramsApi.java -- use a DIFFERENT path (`/v3/audit/changes`) to avoid collision.
- `AuditTrailConstants.java` -- do NOT modify this. Create new constants for the generic framework.

## INTEGRATION NOTE
- Ritwik's MakerCheckerService will call YOUR ConfigAuditService.record() on every APPROVE action.
- Publish the ConfigAuditService interface + a skeleton implementation EARLY so Ritwik can integrate.
- The interface contract in `/interfaces/config-audit-service.java` is the binding agreement.

## BEFORE MERGING
- Ensure config_audit_log table includes org_id column (tenant isolation guardrail)
- Verify CSV export handles large datasets (streaming, not loading all into memory)
- Run thrift-compat-check.sh if Thrift IDL was modified
