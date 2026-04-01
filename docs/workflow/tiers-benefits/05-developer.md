# 05 — Developer: Tier & Benefit CRUD + Maker-Checker APIs

> Phase: Developer (05)
> Date: 2026-04-02
> Input: 03-designer.md, 04-qa.md, session-memory.md, GUARDRAILS.md
> Output feeds: 06-sdet.md, 07-reviewer.md

---

## Summary

Implemented the full Tier & Benefit CRUD + Maker-Checker API backend across 57 new Java files in emf-parent, following the Designer's (03-designer.md) specifications with 4 deviations resolved during implementation.

## Deviations from Designer

1. **`@NotBlank` → `@NotNull @Size(min=1, max=N)`**: JSR-303 Bean Validation 1.0 does not include `@NotBlank` (added in BV 2.0 / Hibernate Validator 6). Replaced throughout DTOs.

2. **`RedisTemplate.setIfAbsent(key, value, ttl, unit)` → two-step `setIfAbsent` + `expire`**: Spring Data Redis 1.8.23 does not support the 4-arg form (added in 2.1). Uses same pattern as existing `ApplicationCacheManagerImpl`. Small race window between set and expire is acceptable (operational lock, not financial).

3. **`JavaTimeModule` → plain ObjectMapper**: `jackson-datatype-jsr310` not in dependencies. ConfigDiffComputer removes all timestamp system fields before comparison, so time serialization format is irrelevant for diff computation.

4. **SLF4J 3+ arg logging**: SLF4J 1.6.x requires `new Object[]{}` wrapper for 3+ parameterized args. Applied throughout services.

---

## Files Created (57 total)

### Layer 0: Enums & Models (emf module — `springdata.mongodb`)

| # | File | Package |
|---|------|---------|
| 1 | `ConfigStatus.java` | `enums` |
| 2 | `ConfigAction.java` | `enums` |
| 3 | `ConfigBaseDocument.java` | `model.config` |
| 4 | `TierConfig.java` | `model.config` |
| 5 | `TierEligibility.java` | `model.config` |
| 6 | `SecondaryCriterion.java` | `model.config` |
| 7 | `TierValidity.java` | `model.config` |
| 8 | `TierRenewal.java` | `model.config` |
| 9 | `RenewalConditions.java` | `model.config` |
| 10 | `TierDowngrade.java` | `model.config` |
| 11 | `TierUpgrade.java` | `model.config` |
| 12 | `TierNudge.java` | `model.config` |
| 13 | `LinkedBenefit.java` | `model.config` |
| 14 | `BenefitConfig.java` | `model.config` |
| 15 | `LinkedTier.java` | `model.config` |

### Layer 1: DAOs (emf module — `springdata.mongodb.dao`)

| # | File | Notes |
|---|------|-------|
| 16 | `TierConfigDao.java` | Interface with orgId-first signatures |
| 17 | `TierConfigDaoImpl.java` | 4 compound indexes, @PostConstruct |
| 18 | `BenefitConfigDao.java` | Interface |
| 19 | `BenefitConfigDaoImpl.java` | 5 compound indexes including linkedTiers.tierId |

### Layer 2: Infrastructure (pointsengine-emf — `RESTEndpoint`)

| # | File | Notes |
|---|------|-------|
| 20 | `@DistributedLock` | Annotation with key (SpEL), ttl, acquireTime |
| 21 | `DistributedLockAspect` | AOP @Around, RedisTemplate setIfAbsent + expire |
| 22 | `ConfigConflictException` | @ResponseStatus(409) |
| 23 | `ConfigValidationException` | Carries ConfigValidationResult |
| 24 | `ConfigValidator<T>` | Generic interface extends Validator<T,R> |
| 25 | `ConfigValidatorRequest<T>` | Immutable request with entity + context |
| 26 | `ConfigValidationResult` | Field-level errors with merge() |
| 27 | `ConfigStatusTransitionValidator` | EnumMap state machine |
| 28 | `VersioningHelper` | createDraftFromActive, approveNew/Edit, reject |
| 29 | `IdempotencyKeyGuard` | Redis SET NX with 5-min TTL |
| 30 | `ConfigDiffComputer` | Jackson-based field-level diff |
| 31 | `ConfigDiffResult` | FieldDiff(fieldPath, old, new) |

### Layer 3: DTOs (pointsengine-emf — `RESTEndpoint.models`)

| # | File | Notes |
|---|------|-------|
| 32 | `StatusChangeRequest` | action, reason |
| 33 | `ReviewRequest` | approvalStatus, comment |
| 34 | `DraftDetails` | draftId, version, lastModified |
| 35 | `TierConfigRequest` | 8 inner sub-DTOs |
| 36 | `TierConfigResponse` | Full tier + DraftDetails |
| 37 | `TierApprovalResponse` | Config + diff |
| 38 | `BenefitConfigRequest` | 1 inner sub-DTO |
| 39 | `BenefitConfigResponse` | Full benefit + DraftDetails |
| 40 | `BenefitApprovalResponse` | Config + diff |

### Layer 4: Validators (pointsengine-emf — `RESTEndpoint.validators`)

| # | File | Notes |
|---|------|-------|
| 41 | `StatusEditableValidator` | Shared, rejects non-editable statuses |
| 42 | `TierNameUniquenessValidator` | Queries TierConfigDao |
| 43 | `EligibilityThresholdValidator` | KPI type + threshold validation |
| 44 | `DowngradeTargetValidator` | Cross-entity via TierConfigDao |
| 45 | `SerialNumberValidator` | Uniqueness within program |
| 46 | `LinkedBenefitValidator` | Cross-entity via BenefitConfigDao |
| 47 | `TierValidatorTypes` | Enum: CREATE_TIER, UPDATE_TIER |
| 48 | `TierValidatorFactory` | Ordered chains per type |
| 49 | `BenefitNameUniquenessValidator` | Queries BenefitConfigDao |
| 50 | `BenefitTypeParameterValidator` | Type-specific param checks |
| 51 | `LinkedTierValidator` | Cross-entity via TierConfigDao |
| 52 | `BenefitValidatorTypes` | Enum: CREATE_BENEFIT, UPDATE_BENEFIT |
| 53 | `BenefitValidatorFactory` | Ordered chains per type |

### Layer 5: Services (pointsengine-emf — `RESTEndpoint.Service.impl`)

| # | File | Notes |
|---|------|-------|
| 54 | `TierConfigService` | Full CRUD + maker-checker lifecycle |
| 55 | `BenefitConfigService` | Full CRUD + maker-checker lifecycle |

### Layer 6: Controllers (pointsengine-emf — `RESTEndpoint.controller.impl`)

| # | File | Notes |
|---|------|-------|
| 56 | `TierConfigController` | @RestController, /api/v1/tiers |
| 57 | `BenefitConfigController` | @RestController, /api/v1/benefits |

### Modified File

| File | Change |
|------|--------|
| `GlobalExceptionHandler.java` | Added handlers for ConfigConflictException (409) and ConfigValidationException (422) |

---

## API Endpoints

### Tier APIs (`/api/v1/tiers`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tiers?programId=&status=&includeDraftDetails=&offset=&limit=` | List tiers (US-1) |
| POST | `/api/v1/tiers` | Create tier (US-2) |
| PUT | `/api/v1/tiers/{tierId}` | Update tier (US-3) |
| PUT | `/api/v1/tiers/{tierId}/status` | Change status — submit/pause/stop/resume (US-7, US-10) |
| POST | `/api/v1/tiers/{tierId}/review` | Approve/reject (US-8, US-9) |
| GET | `/api/v1/tiers/approvals?programId=` | List pending approvals with diff (US-11) |

### Benefit APIs (`/api/v1/benefits`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/benefits?programId=&status=&type=&category=&triggerEvent=&linkedTierId=&includeDraftDetails=&offset=&limit=` | List benefits (US-4) |
| POST | `/api/v1/benefits` | Create benefit (US-5) |
| PUT | `/api/v1/benefits/{benefitId}` | Update benefit (US-6) |
| PUT | `/api/v1/benefits/{benefitId}/status` | Change status (US-7, US-10) |
| POST | `/api/v1/benefits/{benefitId}/review` | Approve/reject (US-8, US-9) |
| GET | `/api/v1/benefits/approvals?programId=` | List pending approvals with diff (US-11) |

---

## Guardrail Compliance

| Guardrail | How Addressed |
|-----------|---------------|
| G-01 (UTC) | All timestamps use `Instant.now()`, model fields are `Instant` |
| G-02 (Null safety) | `Optional` returns on findOne, `Objects.requireNonNull` in VersioningHelper, empty list returns never null |
| G-03 (Security) | No secrets in code, input validated via Bean Validation + ValidatorFactory |
| G-04 (Performance) | Paginated list endpoints with max 100 cap, compound indexes on all query patterns |
| G-06 (API design) | Structured error responses (ConfigValidationResult), idempotency via X-Idempotency-Key, /api/v1 versioning |
| G-07 (Multi-tenancy) | Every DAO query includes orgId filter, orgId from ShardContext (ThreadLocal), Integer type |
| G-08 (Logging) | Structured SLF4J logging on all state changes with orgId, entityId |
| G-10 (Concurrency) | @DistributedLock on status change/review, InterruptedException correctly handled |
| G-12 (AI-specific) | Verified all patterns against codebase, followed existing conventions, no new dependencies |

---

## Compilation Status

All new code compiles cleanly against `mvn compile -pl pointsengine-emf -am`. Pre-existing compilation errors in `PointsEngineRuleConfigThriftImpl.java` and `InfoLookupService.java` are unrelated.

## What's Not Included (Deferred)

- Unit tests (SDET phase)
- Maker-checker flag=false path (always-on for this iteration)
- Audit trail logging
- Custom fields for benefits
- Integration with EMF evaluation pipeline
