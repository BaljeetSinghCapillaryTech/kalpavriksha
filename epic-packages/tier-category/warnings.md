# Warnings for Tier Category + Subcategory

## DO NOT
- DO NOT build your own maker-checker -- use the maker-checker-framework you built in your Layer 1 epic
- DO NOT build your own audit trail -- use the audit-trail-framework owned by Anuj
- DO NOT modify the existing SlabUpgradeService or SlabDowngradeService core logic -- these handle runtime tier evaluation. Your epic adds CONFIG management APIs, not evaluation logic.
- DO NOT modify PEB tier downgrade calculators -- they are runtime, not config

## COLLISION HOTSPOTS
- OrgConfigController.java -- existing draft/live config management. Your new TierController should be SEPARATE (new file, new path). Do not extend OrgConfigController.
- ProgramsApiController.java -- existing /audit/logs endpoint. Avoid path conflicts.
- TierConfiguration.java -- this is the strategy config model. You may need to READ it but be careful about modifying it. Prefer new DTOs that wrap/adapt it.

## IMPORTANT NOTES
- The codebase uses "Slab" terminology internally for what the BRD calls "Tier". Your APIs should use "Tier" in the REST surface but map to "Slab" entities internally.
- ProgramSlab is the core entity. Do NOT create a duplicate "Tier" entity -- adapt ProgramSlab.
- The comparison matrix is a READ-ONLY view -- it aggregates data from ProgramSlab, TierConfiguration, TierDowngradeStrategyConfiguration, and Benefits.
