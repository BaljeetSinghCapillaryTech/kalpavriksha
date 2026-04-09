# Warnings for Maker Checker

## DO NOT
- DO NOT modify the existing StatusTransitionValidator.java -- it is promotion-specific and used by UnifiedPromotionFacade. Build a NEW generic validator alongside it.
- DO NOT modify the existing PromotionAction or PromotionStatus enums -- they are promotion-specific. Create NEW entity-agnostic enums (ConfigStatus, ApprovalAction).
- DO NOT modify the existing UnifiedPromotionFacade.java -- it orchestrates promotion approval. Your MakerCheckerService is a separate, generic service.
- DO NOT create your own audit logging -- use the ConfigAuditService interface from the audit-trail-framework module (owned by Anuj).

## COLLISION HOTSPOTS
- `emf.thrift` -- if adding enums/structs to this file, coordinate with Anuj (he may also need to add audit-related structs). Consider using a separate `config_management.thrift` that both import.
- `intouch-api-v3` controller layer -- do NOT create endpoints that conflict with existing `/v3/promotions/{id}/status` or `/v3/requests/{entityId}/status` patterns. Use a new `/v3/approvals/` path.

## BEFORE MERGING
- Run `thrift-compat-check.sh` against the registry IDL to verify no breaking changes
- Ensure all new DB tables include org_id column (tenant isolation guardrail)
- Verify the ConfigAuditService mock is replaced with real implementation (or feature-flagged)
