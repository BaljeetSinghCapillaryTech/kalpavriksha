# Warnings for Supplementary Partner Program Tiers

## DO NOT
- DO NOT modify existing PartnerProgramImpl core logic -- it handles runtime partner program operations. Add CONFIG management alongside it.
- DO NOT modify Thrift event handling (partnerProgramLinkingEvent, etc.) -- those are runtime events. Your epic adds config management APIs.
- DO NOT build your own maker-checker or audit trail -- use the shared frameworks.

## COLLISION HOTSPOTS
- PartnerProgramImpl.java -- heavily used by runtime. READ it for understanding but modify with extreme care.
- emf.thrift PartnerProgramTierUpdateInfo -- if extending, ensure backward compatibility (add optional fields only).

## COORDINATION
- Ritwik is building Tier Category in parallel (also Layer 2). Follow the same patterns he uses for tier CRUD to keep the API surface consistent.
- Use ConfigEntityType.SUPPLEMENTARY_PARTNER_PROGRAM in all MakerCheckerService and ConfigAuditService calls.

## BEFORE MERGING
- Verify new REST endpoints don't conflict with existing Thrift service paths
- Ensure PartnerProgramType.SUPPLEMENTARY filtering works correctly
- Run integration tests with maker-checker and audit trail
