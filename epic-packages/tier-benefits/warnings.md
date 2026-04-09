# Warnings for Tier Benefits

## DO NOT
- DO NOT modify the existing Benefits.java entity -- it is used by the current promotion-based benefits system. Build NEW entities (BenefitCategory, BenefitInstance) alongside it.
- DO NOT modify the existing BenefitsType enum -- it only has VOUCHER/POINTS and is used by existing code. Create a new BenefitCategoryType enum.
- DO NOT modify BenefitsDao.java -- it operates on the existing Benefits entity. Create new DAOs.
- DO NOT build your own maker-checker or audit trail -- use the shared frameworks.
- DO NOT modify BenefitTrackingService -- it handles runtime benefit tracking, not config.

## COLLISION HOTSPOTS
- Benefits.java and related files -- your new model coexists with the old one. Do NOT attempt to migrate or replace the existing Benefits entity in this epic.
- BenefitsAwardedStats* files -- runtime stats, do not touch.
- PromotionBenefitsActionDailySummaryDao -- existing promotion benefits, do not touch.

## DATA MODEL NOTE
- The new BenefitCategory/BenefitInstance model is SEPARATE from the existing Benefits/BenefitsType model.
- Eventually they may be unified, but that is a FUTURE migration. For now, they coexist.
- BenefitInstance links to BenefitCategory + Tier (ProgramSlab), NOT to Promotion.

## BEFORE MERGING
- Verify all new tables include org_id (tenant isolation)
- Verify BenefitCategoryType enum covers all 9 types from the spec
- Verify trigger events match the spec (TIER_ENTRY, TIER_UPGRADE, TIER_RENEWAL, etc.)
