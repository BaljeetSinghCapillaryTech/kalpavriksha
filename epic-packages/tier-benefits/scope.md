# Epic: Tier Benefits
Owner: Baljeet
Layer: 2 (starts after Maker-Checker + Audit Trail shared modules are available)

## What this epic covers

Benefits as a Product -- standalone benefits module with benefit categories,
benefit instances per tier, custom fields, tier linkage, and state lifecycle.
This is largely greenfield -- no BenefitCategory concept exists in the codebase.

### User Stories (from BRD E2-US1, E2-US2, E2-US3 + Benefit Categories Spec)
- E2-US1: Benefits Listing (searchable, filterable table)
- E2-US2: Benefit Creation (form + aiRa, link to tiers)
- E2-US3: Custom Fields for Benefits
- Benefit Categories Spec: 9 category types, trigger events, tier applicability, matrix view

### Benefit Category Types (from brd-benefit-categories.md)
1. Welcome Gift (trigger: TIER_ENTRY, one-time)
2. Upgrade Bonus Points (trigger: TIER_UPGRADE, one-time)
3. Tier Badge (trigger: TIER_ENTRY, persistent)
4. Renewal Bonus (trigger: TIER_RENEWAL, recurring)
5. Loyalty Voucher (trigger: PERIODIC/SCHEDULED, recurring)
6. Earn Points (trigger: TRANSACTION, ongoing multiplier)
7. Birthday Bonus (trigger: BIRTHDAY, annual)
8. Priority Support (trigger: TIER_ACTIVE, entitlement)
9. Free Shipping (trigger: TRANSACTION, conditional entitlement)

## Shared modules
- **BUILDS**: none
- **CONSUMES**: maker-checker-framework (owned by Ritwik)
- **CONSUMES**: audit-trail-framework (owned by Anuj)

## Build order
1. New entities: BenefitCategory, BenefitInstance, BenefitCategoryType enum, TriggerEvent enum
2. New entities: CustomFieldDefinition, CustomFieldValue
3. DB migrations: benefit_categories, benefit_instances, custom_field_definitions, custom_field_values
4. BenefitCategoryService, BenefitInstanceService
5. Maker-Checker integration: category/instance create/edit via MakerCheckerService
6. Audit integration: changes via ConfigAuditService
7. REST API: BenefitsController in intouch-api-v3
   - GET /benefits (listing with filters)
   - POST /benefits/categories (create category)
   - POST /benefits/instances (create instance linked to category + tier)
   - GET /benefits/matrix (categories x tiers grid)
8. Tests

## Code locations
- Core: `emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/`
  - New packages: `entity/benefits/`, `services/benefits/`, `dao/benefits/`
- API: `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/`
- Reference existing: Benefits.java, BenefitsType.java, BenefitsDao.java (for pattern, not extension)

## Existing codebase context
- Benefits.java has: name, type (VOUCHER/POINTS only), programId, promotionId, description, maxValue, isActive
- BenefitsType enum has only VOUCHER and POINTS -- far too limited for 9 category types
- Benefits are currently promotion-backed (promotionId FK) -- new model is category-backed
- BenefitsLinkedProgramType exists -- may be relevant for tier linkage
- BenefitTrackingService exists -- runtime tracking, not config management
