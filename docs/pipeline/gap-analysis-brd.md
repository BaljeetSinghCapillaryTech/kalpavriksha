# Gap Analysis — BRD Compliance Check

> Feature: tier-crud
> Ticket: test_branch_v3
> Phase: Analyst (Compliance Mode)
> Date: 2026-04-06

---

## Verified Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|-------------|---------|----------|
| 1 | "ProgramSlab entity has no status column" | `emf-parent/.../entity/ProgramSlab.java` | **CONFIRMED** | Entity has only: `pk`, `program`, `programId`, `serialNumber`, `name`, `description`, `createdOn`, `metadata`. No `status` or `active` field. Schema SQL confirms columns: `id`, `org_id`, `program_id`, `serial_number`, `name`, `description`, `created_on`, `auto_update_time`, `metadata`. [C7] |
| 2 | "EntityType enum has values PROMOTION, TARGET_GROUP, STREAK, etc." | `intouch-api-v3/.../orchestration/EntityType.java` | **CONFIRMED** | Exact values: `PROMOTION`, `TARGET_GROUP`, `STREAK`, `LIMIT`, `LIABILITY_OWNER_SPLIT`, `WORKFLOW`, `JOURNEY`, `BROADCAST_PROMOTION`. BA listed "etc." which is accurate. [C7] |
| 3 | "RequestManagementController handles PUT /v3/requests/{entityType}/{entityId}/status" | `intouch-api-v3/.../resources/RequestManagementController.java` | **CONFIRMED** | `@PutMapping(value = "/{entityType}/{entityId}/status")` at line 38. Signature: `changeStatus(@PathVariable EntityType entityType, @PathVariable String entityId, @RequestParam PromotionStatus existingStatus, @Valid @RequestBody StatusChangeRequest request, ...)`. [C7] |
| 4 | "RequestManagementFacade.changeStatus() only routes PROMOTION" | `intouch-api-v3/.../facades/RequestManagementFacade.java` | **CONFIRMED** | Line 40: `if (entityType == EntityType.PROMOTION)` routes to `unifiedPromotionFacade.changePromotionStatus()`. Any other entity type throws `InvalidInputException("TARGET_LOYALTY.UNSUPPORTED_TYPE_FOR_STATUS_CHANGE")`. [C7] |
| 5 | "UnifiedPromotionController has POST /v3/unifiedPromotions/{id}/review" | `intouch-api-v3/.../resources/UnifiedPromotionController.java` | **PARTIAL** | The actual endpoint is `@PostMapping(value = "/{unifiedPromotionId}/review")` at line 178 with path variable named `unifiedPromotionId`, not `id`. The BA wrote `POST /v3/unifiedPromotions/{id}/review` which is functionally correct but the path variable name differs. [C6] |
| 6 | "ResponseWrapper has {data, errors, warnings}" | `intouch-api-v3/.../models/ResponseWrapper.java` | **CONFIRMED** | Fields: `T data`, `List<ApiError> errors`, `List<ApiWarning> warnings`. `ApiError` has `Long code` + `String message`. `ApiWarning` has `String message`. [C7] |
| 7 | "TargetGroupErrorAdvice handles MethodArgumentNotValidException" | `intouch-api-v3/.../exceptionResources/TargetGroupErrorAdvice.java` | **CONFIRMED** | `@ExceptionHandler({MethodArgumentNotValidException.class})` at line 103. Extracts field-level errors from `BindingResult`, maps each to `ApiError(code, message)` using `MessageResolverService`. [C7] |
| 8 | "PromotionStatus enum has DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED" | `intouch-api-v3/.../enums/PromotionStatus.java` | **PARTIAL** | Enum has those 4 values PLUS 6 more: `PAUSED`, `SNAPSHOT`, `LIVE`, `UPCOMING`, `COMPLETED`, `PUBLISH_FAILED`. The BA said "PromotionStatus enum values (DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED) are reusable for tiers" — the 4 values exist but the enum is significantly larger. BA's statement that the tier status lifecycle would only use those 4 is a design decision, not a factual claim about the enum contents. [C7] |
| 9 | "program_slabs table exists" | `emf-parent/.../schema/dbmaster/warehouse/program_slabs.sql` | **CONFIRMED** | Full DDL found. Columns: `id` (PK, auto_increment), `org_id`, `program_id`, `serial_number`, `name`, `description`, `created_on`, `auto_update_time`, `metadata`. Unique key on `(org_id, program_id, serial_number)`. [C7] |
| 10 | "SlabUpgradeService, SlabDowngradeService exist" | `emf-parent/.../services/SlabUpgradeService.java`, `emf-parent/.../services/SlabDowngradeService.java` | **CONFIRMED** | Both are `@Service` annotated, `@Transactional`. `SlabUpgradeService` handles slab upgrades, uses `PeCustomerEnrollmentDao`, `CustomerSlabUpgradeHistoryDao`. [C7] |
| 11 | "TierConfiguration DTO has isDowngradeOnReturnEnabled" | `emf-parent/.../dto/TierConfiguration.java` | **CONFIRMED** | Field `m_isDowngradeOnReturnEnabled` (boolean, default false) with getter `getIsDowngradeOnReturnEnabled()`. Also has: `dailyDowngradeEnabled`, `retainPoints`, `m_slabConfigs` (TierDowngradeSlabConfig[]), `m_isActive`, `m_downgradeConfirmationConfig`, `m_reminders`, `m_renewalConfirmationConfig`, `isDowngradeOnPartnerProgramDeLinkingEnabled`, `thresholdValues`, `currentValueType`, `trackerId`, `trackerConditionId`. [C7] |
| 12 | "PartnerProgramTierSyncConfiguration exists" | `emf-parent/.../entity/PartnerProgramTierSyncConfiguration.java` | **CONFIRMED** | JPA entity mapped to `partner_program_tier_sync_configuration` table. Links `loyaltyProgramSlabId` to `partnerProgramSlabId`. Has FK to `PartnerProgram`. [C7] |
| 13 | "UnifiedPromotionFacade exists and orchestrates Thrift calls" | `intouch-api-v3/.../promotion/UnifiedPromotionFacade.java` | **PARTIAL** | The facade exists as `@Component`. It orchestrates via `EntityOrchestrator`, `UnifiedPromotionRepository` (MongoDB), `PointsEngineRulesThriftService`, validation services, etc. It does orchestrate Thrift calls but is primarily a MongoDB + orchestration layer, not purely a Thrift orchestrator. [C6] |
| 14 | "New tier added above highest existing tier" | `emf-parent/.../config/helper/ProgramConfigDataHelper.java`, `ProgramSlab.java` schema | **CONFIRMED** | Tier ordering is managed via `serialNumber` (int) field. The `program_slabs` table has a UNIQUE constraint on `(org_id, program_id, serial_number)`. `ProgramConfigDataHelper.createSlab()` sets `serialNumber` from `SlabInfoModel.getSerialNumber()`. New slabs get the next sequential number. [C6] |
| 15 | "KPI type is set once per program" | `emf-parent/.../strategy/ThresholdBasedSlabUpgradeStrategyImpl.java` | **CONFIRMED** | `current_value_type` is stored as a strategy property for the slab upgrade strategy. The `CurrentValueType` enum has: `CURRENT_POINTS`, `CUMULATIVE_POINTS`, `CUMULATIVE_PURCHASES`, `TRACKER_VALUE_BASED`. This is a program-level strategy property — all tiers in a program share the same upgrade strategy and hence the same `currentValueType`. [C5 — I confirmed the strategy is program-level from `BasicProgramCreator.createSlabUpgradeRuleset()` which creates ONE upgrade ruleset per program] |

---

## Missing Gaps

Things the BA/PRD did not mention but that code reveals are important for tier CRUD implementation.

### Gap 1: ProgramSlab has NO `active` column today — schema migration is non-trivial

The BA correctly identified that `active` needs to be added. However, the `program_slabs` table has a UNIQUE constraint on `(org_id, program_id, serial_number)`. Adding `active` without modifying this constraint means soft-deleted tiers still "occupy" their serial number slot. If a tier at serial_number=3 is soft-deleted and a new tier is created, the serial_number assignment logic needs to account for gaps.

**Severity**: HIGH — Affects migration design and API ordering logic.

### Gap 2: TierConfiguration has more fields than BA lists

`TierConfiguration` DTO contains fields the BA didn't enumerate that are relevant to tier CRUD:
- `m_isActive` (boolean) — an existing active flag at the DTO level (not in the DB schema though)
- `isDowngradeOnPartnerProgramDeLinkingEnabled` — partner program delinking behavior
- `m_downgradeConfirmationConfig` and `m_renewalConfirmationConfig` — alert configurations
- `m_reminders` — reminder alert configurations
- `thresholdValues` (CSV string), `currentValueType`, `trackerId`, `trackerConditionId` — upgrade strategy fields

The tier CRUD API should expose or at least acknowledge these fields.

**Severity**: MEDIUM — May affect the completeness of TierRequest/TierResponse DTOs.

### Gap 3: APIMigrationInterceptor applies to ALL paths (`/**`)

`WebConfig.java` registers `APIMigrationInterceptor` with `addPathPatterns("/**")`. This interceptor handles API migration/redirection (JSVT migration). New `/v3/tiers` endpoints will automatically be intercepted. The interceptor checks org-level migration rules and can redirect requests.

**Severity**: MEDIUM — New tier endpoints must be compatible with the migration interceptor. May need explicit handling or exclusion rules.

### Gap 4: `PeProgramSlabDao` already has CRUD-like query methods

The DAO interface at `emf-parent/.../dao/PeProgramSlabDao.java` provides:
- `findByProgram(int orgId, int programId)` — returns `List<ProgramSlab>`
- `findByProgramSlabNumber(int orgId, int programId, int programSlabNumber)` — returns single slab
- `findNumberOfSlabs(int orgId, int programId)` — count

These can be reused for GET operations. The DAO extends `GenericDao` which likely provides `save()`, `delete()`, etc.

**Severity**: LOW — Good news. Existing DAO can be leveraged.

### Gap 5: PromotionStatus enum has 10 values, not 4

The BA says tier status lifecycle uses "DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED". But the actual `PromotionStatus` enum has 10 values including `PAUSED`, `SNAPSHOT`, `LIVE`, `UPCOMING`, `COMPLETED`, `PUBLISH_FAILED`. The PRD proposes creating a new `TierStatus` enum, which is the right call. But if `RequestManagementController` currently takes `@RequestParam PromotionStatus existingStatus`, reusing it for tiers would require either:
- A new `TierStatus` enum + separate endpoint, or
- A shared `EntityStatus` abstraction, or
- Accepting `PromotionStatus` values for tiers (confusing naming)

**Severity**: HIGH — Architectural decision needed.

### Gap 6: `RequestManagementController.changeStatus()` return type is `ResponseWrapper<UnifiedPromotion>`

The controller returns `ResponseWrapper<UnifiedPromotion>` specifically. To support tier status changes through the same controller, the return type must be generalized (e.g., `ResponseWrapper<?>` or `ResponseWrapper<Object>`) or a separate endpoint must be created for tiers.

**Severity**: HIGH — Cannot reuse the exact same endpoint method for both promotions and tiers without signature changes.

### Gap 7: Composite Primary Key pattern

`ProgramSlab` uses an `@EmbeddedId` composite key (`ProgramSlabPK` with `id` + `orgId`). This is a multi-tenancy pattern where org_id is part of the PK. All tier CRUD operations MUST include orgId. The BA mentions org-scoping but doesn't explicitly address the composite PK pattern in the entity design.

**Severity**: MEDIUM — Implementation detail but affects DAO/service signatures.

### Gap 8: No Flyway migration framework found

Searched for Flyway config in emf-parent (XML, YAML) — no results. The schema is managed via SQL scripts in `integration-test/.../schema/`. The BA/PRD assumes Flyway migrations. The actual migration mechanism needs to be clarified.

**Severity**: MEDIUM — Migration approach may differ from what BA/PRD assumes.

### Gap 9: `PointsEngineRuleConfigThriftImpl` handles slab-related Thrift operations

The existing `PointsEngineRuleConfigThriftImpl` (implements Thrift `Iface`) already processes slab/tier configuration as part of program rule configuration. It uses `TierConfiguration` data. New tier CRUD Thrift services may need to either extend this class or be a separate service that coordinates with it.

**Severity**: MEDIUM — Existing Thrift infrastructure for tier config already exists; the BA proposes a new `TierCrudService` but should clarify the relationship with existing services.

### Gap 10: `BasicProgramCreator` handles slab creation during program setup

Slab creation today happens through `BasicProgramCreator.createRulesets()` which creates slabs along with upgrade/downgrade/renewal rulesets. The new tier CRUD API may need to also create/update these rulesets, or at minimum be aware of them.

**Severity**: HIGH — Creating a tier is not just inserting a `ProgramSlab` row. It involves creating associated strategies and rulesets for upgrade/downgrade/renewal. The BA does not address this orchestration.

### Gap 11: `metadata` field in ProgramSlab

`ProgramSlab` has a `metadata` VARCHAR(30) column that the BA/PRD does not mention. This field is populated from `SlabInfoModel.getMetaData().toJson()`. If metadata is tier-specific configuration, the CRUD API should expose it.

**Severity**: LOW — May just need to be passed through.

### Gap 12: `PartnerProgramTierSyncConfiguration` maps partner slabs to loyalty slabs

This entity links `partnerProgramSlabId` to `loyaltyProgramSlabId`. Soft-deleting a loyalty tier must check whether it is referenced as a `loyaltyProgramSlabId` in this table. The BA mentions checking downgrade targets but does NOT mention partner program sync references.

**Severity**: HIGH — Soft delete validation is incomplete. Must check `partner_program_tier_sync_configuration` references too.

---

## GUARDRAILS Compliance

| Guardrail | Status | Notes |
|-----------|--------|-------|
| **G-01: Timezone** | N/A for tier CRUD | Tier entities use `created_on` (DATETIME in MySQL, not TIMESTAMP). New columns should follow G-01.1 (store UTC). Existing `ProgramSlab.createdOn` uses `java.util.Date` which violates G-01.3 — but changing this is out of scope (existing code). |
| **G-02: Null Safety** | ATTENTION | `ProgramSlab.getDescription()` is NOT NULL in schema. `metadata` is nullable. New DTO design must handle nullable fields correctly. |
| **G-03: Security** | ATTENTION | New endpoints must have auth + authz. `RequestManagementController` already takes `AbstractBaseAuthenticationToken`. Follow same pattern. |
| **G-04: Performance** | ATTENTION | **G-04.2 (pagination)**: GET /tiers should support pagination. BA says "up to 20 tiers" but doesn't mention pagination. Since tier count per program is bounded (typically <20), pagination may be optional but should be documented. |
| **G-05: Data Integrity** | ATTENTION | **G-05.3**: Soft delete `active` column needs DB-level DEFAULT constraint. **G-05.4**: Migration must be backward-compatible (expand-then-contract). BA correctly notes this. **G-05.2**: Concurrent tier updates need optimistic locking — ProgramSlab has no `@Version` field. |
| **G-06: API Design** | OK | BA proposes `ResponseWrapper<T>` format, field-level errors. Aligns with G-06.3. **G-06.1 (idempotency)**: POST /tiers should have idempotency key — not mentioned in BA. |
| **G-07: Multi-Tenancy** | ATTENTION | Composite PK includes `orgId`. All queries in `PeProgramSlabDao` include `orgId` filter. New queries must follow same pattern. BA does not explicitly call out the composite PK multi-tenancy pattern. |
| **G-09: Backward Compatibility** | OK | Adding `active` and `status` columns with defaults (1 and 'ACTIVE') is backward-compatible. Existing code that doesn't set these columns will get defaults. |
| **G-12: AI-Specific** | ATTENTION | **G-12.1**: Must use existing `PeProgramSlabDao`, `ResponseWrapper`, `TargetGroupErrorAdvice` patterns. **G-12.2**: Must follow existing composite PK pattern, builder pattern (`ProgramSlabBuilder`). **G-12.4**: No speculative abstractions. |

---

## QUESTIONS FOR USER

These items are below C5 confidence and require clarification before proceeding:

1. **[C3] Migration mechanism**: The BA/PRD assumes Flyway migrations, but I found no Flyway configuration in emf-parent. Schema SQL files exist in `integration-test/.../schema/`. What is the actual migration mechanism used in production? This affects how we deliver the `active` and `status` column additions.

2. **[C4] Ruleset orchestration on tier creation**: Creating a tier today (via `BasicProgramCreator`) involves creating slab upgrade/downgrade/renewal rulesets with strategies. Does the new tier CRUD API need to also create/update these rulesets, or is it purely a `ProgramSlab` row insert with the expectation that rulesets are managed separately?

3. **[C4] PromotionStatus reuse vs. new TierStatus**: The `RequestManagementController` is typed to return `ResponseWrapper<UnifiedPromotion>` and takes `@RequestParam PromotionStatus existingStatus`. Reusing this endpoint for tiers requires either generalizing these types or creating a parallel endpoint. Which approach is preferred?

4. **[C3] `metadata` field**: `ProgramSlab.metadata` is a VARCHAR(30) column. What does it store? Should the tier CRUD API expose it in TierRequest/TierResponse?

5. **[C4] Partner program tier sync on soft delete**: `PartnerProgramTierSyncConfiguration` links partner slabs to loyalty slabs. Should soft delete validation also check this table, or is partner program sync handled separately?

---

## ASSUMPTIONS MADE

1. **[C5]** The `serialNumber` field in `ProgramSlab` determines tier hierarchy ordering (lower = base, higher = top). Evidence: the UNIQUE constraint on `(org_id, program_id, serial_number)` and the `toString()` output `getName() + "[Serial:" + getSerialNumber() + "]"`.

2. **[C5]** `GenericDao` (parent of `PeProgramSlabDao`) provides standard CRUD operations (`save`, `findById`, `delete`). Evidence: this is a standard Spring Data JPA pattern and the DAO extends it.

3. **[C6]** The `current_value_type` (KPI type) is set at the program level, not per-tier. Evidence: `BasicProgramCreator.createSlabUpgradeRuleset()` creates ONE upgrade strategy per program, and `ThresholdBasedSlabUpgradeStrategyImpl` stores `current_value_type` as a program-level strategy property.

4. **[C5]** Adding `TIER` to `EntityType` enum is backward-compatible because the enum is used as a `@PathVariable` in `RequestManagementController` — existing API callers passing `PROMOTION` will continue to work. New `TIER` value only activates when explicitly passed.

---

## Summary

- **15 claims verified**: 11 CONFIRMED, 4 PARTIAL
- **0 CONTRADICTED**
- **12 gaps found** (3 HIGH severity, 5 MEDIUM, 4 LOW)
- **5 questions for user** (below C5 confidence)
- **4 assumptions made** (C5-C6)

The BA/PRD is fundamentally accurate in its codebase analysis. The main risks are:
1. **Tier creation is more than a row insert** — rulesets/strategies are tightly coupled (Gap 10)
2. **RequestManagementController cannot be reused as-is** — return type and param types are promotion-specific (Gaps 5, 6)
3. **Soft delete validation is incomplete** — must also check `PartnerProgramTierSyncConfiguration` references (Gap 12)
4. **Schema migration mechanism is unclear** — no Flyway found (Gap 8)
