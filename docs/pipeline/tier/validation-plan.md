# Tier API — Server-Side Validation Plan

> **Status:** PROPOSED — awaiting approval before any code changes.
> **Date:** 2026-04-27
> **Author:** feature-pipeline orchestrator
> **Reference pattern:** Promotion CRUD validation in `intouch-api-v3` (`UnifiedPromotionController`, `UnifiedPromotionValidatorService`, `MessageResolverService`, `target_loyalty.properties`).
> **Companion file:** `validation-rework-scope.md` — structured Phase 7 / 8b / 9 / 10 rework payload.

---

## 1. Scope

### In scope
1. **Mirror the promotion error-code catalog pattern** for tier APIs (decision D1).
   New file `tier.properties`, namespace `TIER.*`, codes **9001–9099** (decision D2).
2. **Refactor existing tier validators** to throw via the new key-based pattern instead of plain text or the `[9001]` bracket-prefix workaround.
3. **Add the missing server-side validations** identified in the gap analysis between `TIERS_VALIDATIONS.md` (UI) and the current server validators — provided the rule maps to a server-side concept of equal vocabulary.
4. **Hybrid annotation pattern** (decision D3) — bean-validation annotations for simple field rules; manual validator for cross-field and business rules.
5. Tests for every new and migrated code (alignment with existing `TierCreateRequestValidatorTest` style).

### Out of scope (decision D5 = a)
| Item | Reason | Disposition |
|---|---|---|
| Enum vocabulary mismatch — UI says `upgradeType ∈ {POINTS_BASED, PURCHASE_BASED, TRACKER_VALUE_BASED}`, server says `{EAGER, DYNAMIC, LAZY}` | Two different vocabularies; UI likely has a translation layer. Adding server-side validation against UI values would break legitimate engine-vocabulary callers. | Flag to architect/product. Do **not** attempt mapping in this task. |
| Enum vocabulary mismatch — `downgradeCondition`: UI `{FIXED, FIXED_DURATION, FIXED_CUSTOMER_REGISTRATION}` vs server `{FIXED, SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC, FIXED_CUSTOMER_REGISTRATION}` | Same as above — vocabulary fork. | Flag. No change. |
| UI fields that have no server-side counterpart: `upgradeMode` (`ABSOLUTE_VALUE`/`ROLLING_VALUE`/`DYNAMIC`), `secondaryCriteriaEnabled`, `additionalConditionTrackers === CUSTOM` | These fields don't exist in `TierEligibilityConfig` / `TierRenewalConfig`. Adding validation requires adding the fields first — that's a schema change, not validation work. | Flag. No change. |
| "Tier not editable if LIVE with active customers" | Requires reading customer counts (cross-repo, performance-sensitive). Current pattern is status-only. | Flag. No change. |

These are **logged here, not silently dropped.** They warrant a follow-up architect decision.

---

## 2. Architectural Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| D1 | Error-code catalog approach | **Full mirror** (a) — i18n properties, key-based throws, resolver registration | Existing tier state is already inconsistent; ~half the declared codes don't reach the client today. A full migration is cheaper than maintaining hybrid drift. |
| D2 | Namespace and code range | **`TIER.*` keys, new file `tier.properties`, codes 9001–9099** (a) | Clean separation from loyalty namespace; preserves existing 9001–9024 numbers (no client breakage); single resolver-registry line change. |
| D3 | Annotation-driven validation | **Hybrid** (b) — annotations for simple rules; manual validator for cross-field/business rules | Mirrors what promotion actually does (`@NotNull` + `UnifiedPromotionValidatorService`). Avoids hand-written required/length/pattern checks. |
| D4 | Validator class consolidation | **Keep current split** (b) — `TierCreateRequestValidator` / `TierUpdateRequestValidator` / `TierEnumValidation` / `TierRenewalValidation` / `TierValidationService` | The mirror is the contract (codes + keys + response shape), not file count. Current split is by concern and is already coherent. |
| D5 | Scope of out-of-scope items | **Flag, don't fix** (a) | Vocabulary alignment is a separate architectural project. |
| D6 | Plan delivery format | **Plan + rework scope** (c) | Lets the existing pipeline rework machinery (REQ-xx / BT-xx classifications, forward-cascade rules) pick up the work. |

---

## 3. Current-State Evidence

### 3.1 What works today
| Component | File | Status |
|---|---|---|
| Response shape (`ResponseWrapper<ApiError>`) | `models/ResponseWrapper.java` | ✅ Same shape as promotion — no change needed |
| `TargetGroupErrorAdvice.handleInvalidInputException` | `exceptionResources/TargetGroupErrorAdvice.java:80–102` | ✅ Already routes key-only messages through `MessageResolverService` via `error()` helper at lines 250–267 (regex falls through, `error()` looks up `getCode`/`getMessage`). **No advice change required for D1=a.** |
| `MessageResolverService` | `services/internal/MessageResolverService.java` | ✅ Resolves any key whose first dot-segment is registered in `fileNameMap` (lines 30–36) |
| Pre-binding `JsonNode` scans for codes 9011–9018 | `tier/validation/TierEnumValidation.java:309–322, 333–344, 354–373, 440–463, 476–499` | ✅ Throws **with** `[NNNN]` bracket prefix; correctly transmits the numeric code via the regex path at advice line 88–99 |

### 3.2 What's broken today (the asymmetry)
| Component | File:Line | Problem | Effect on client |
|---|---|---|---|
| `TierCreateRequestValidator.validateCoreFields` | lines 137, 140, 143, 146 | Throws plain text (`"name is required"`) — no key, no bracket prefix | Client receives `code: 999999`, message: `"name is required"` |
| `TierCreateRequestValidator.validateThreshold` | line 157 | Same — plain text `"threshold must be positive"` | `code: 999999` |
| `TierEnumValidation` enum-list throws (codes 9004, 9009) | lines 108, 113, 118, 144 | Plain text (`"kpiType must be one of: …"`) — declared constants 9004/9009 are dead code | `code: 999999` |
| `TierRenewalValidation.validate` | line 43 (per agent inventory) | Plain text — declared constant `9010` is dead code | `code: 999999` |
| `TierEnumValidation.validateNoStartDateForSlabUpgrade` (9014), `validateFixedFamilyRequiresPositivePeriodValue` (9018), `validateRenewalCriteriaTypeCanonical` (9017), `validateRenewalDowngradeTo` (9019), multi-tracker (9020), expression DNF (9021), window-type (9022), coupling (9023), negative-guard (9024) | various | Need verification on a per-throw basis — agent inventory says some use bracket-prefix and some don't | Mixed |

**Net result:** the visible `code` field in tier error responses is `999999` for many failures today. Fixing this is part of D1.

### 3.3 Tests already in place
- `TierCreateRequestValidatorTest` — covers BT-190 (Class A), BT-195 (string `-1`), BT-197b (Jackson strict-mode rejection), BT-198 (SLAB_UPGRADE startDate)
- `TierUpdateRequestValidatorTest` — BT-197b PUT variant
- `TierRenewalValidationTest` — 51 tests on enum, DNF grammar, multi-tracker
- `TierStrategyTransformerTest` — 97 tests on serialisation round-trips

These tests assert on `InvalidInputException` thrown — most do **not** assert on the resolved client-visible `code`. After migration, asserting code resolution is recommended (one extra line per test using a thin helper).

---

## 4. Target Architecture

### 4.1 New artifacts

| File | Purpose | Action |
|---|---|---|
| `intouch-api-v3/src/main/resources/i18n/errors/tier.properties` | Tier error code + message catalog (key → code, key → message) | **Create** |
| `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/validation/TierErrorKeys.java` | String constants for every key (e.g. `public static final String TIER_NAME_REQUIRED = "TIER.NAME_REQUIRED";`) — prevents typo drift between code and properties | **Create** |

### 4.2 Modified artifacts (one-line / minimal changes)

| File | Change |
|---|---|
| `services/internal/MessageResolverService.java:30–36` | Add `.put("TIER", "i18n.errors.tier")` to `fileNameMap` |

### 4.3 Modified artifacts (validator refactors)

| File | Change |
|---|---|
| `tier/validation/TierCreateRequestValidator.java` | Remove `public static final int TIER_*` numeric constants. All throws migrate to `throw new InvalidInputException(TierErrorKeys.TIER_NAME_REQUIRED)`. Bracket-prefix throws in `TierEnumValidation` migrate to key-only throws too. |
| `tier/validation/TierUpdateRequestValidator.java` | Same pattern. Note: name-blank-on-null (currently `"name cannot be blank"`) gets its own key `TIER.NAME_BLANK` if it carries a different code, OR shares `TIER.NAME_REQUIRED` if semantics overlap. **Plan default: share key.** |
| `tier/validation/TierEnumValidation.java` | Migrate all 14 throw sites (lines 108, 113, 118, 144, 152, 175, 187, 203, 219, 313, 339, 365, 392, 420, 454, 490, 516, 540, 576, 615) — drop bracket prefixes, use keys. |
| `tier/validation/TierRenewalValidation.java` | Same — line 43 throw migrates. |
| `tier/TierValidationService.java` | Migrate uniqueness throw (line 54) to `TIER.NAME_NOT_UNIQUE` key (currently `ConflictException` — KEEP `ConflictException`, just change message to a key). Migrate tier-cap throw (line 108). |
| `tier/TierFacade.java` | Status-transition throws (lines 242, 268) — migrate. |
| `tier/TierApprovalHandler.java` | preApprove + validateForSubmission throws — migrate. |

### 4.4 DTO annotation additions (D3 = hybrid — applied surgically)

The current tier pattern uses **raw `JsonNode`** for pre-binding scans before treating it as a typed DTO. We **keep** the raw-body path (it's the only way Class A/B/sentinel scans work). But for typed-DTO field rules we add bean annotations so Spring's standard validation runs first.

| DTO field | Add annotation | Replaces manual check |
|---|---|---|
| `TierCreateRequest.programId` | (already has `@NotNull`) | — |
| `TierCreateRequest.name` | `@NotBlank(message = "TIER.NAME_REQUIRED")`, `@Size(max = 100, message = "TIER.NAME_TOO_LONG")` | `validateCoreFields` lines 136–141 |
| `TierCreateRequest.description` | `@Size(max = 500, message = "TIER.DESCRIPTION_TOO_LONG")` | `validateCoreFields` lines 142–144 |
| `TierCreateRequest.color` | `@Pattern(regexp = "^#[0-9A-Fa-f]{6}$", message = "TIER.INVALID_COLOR_CODE")` | `validateCoreFields` lines 145–147 |
| `TierUpdateRequest.name` | `@Size(max = 100, message = "TIER.NAME_TOO_LONG")` (no `@NotBlank` — partial update) | partial replacement |
| `TierUpdateRequest.description`, `.color` | same as Create | same |
| `TierEligibilityConfig.threshold` | `@PositiveOrZero(message = "TIER.THRESHOLD_MUST_BE_POSITIVE")` | `validateThreshold` lines 155–157 |

**Trigger requirement (D3):** add `@Valid` to `TierController.createTier` and `updateTier` so `MethodArgumentNotValidException` fires. Today the controllers receive raw `JsonNode` — that path stays for pre-binding scans, but after `objectMapper.treeToValue(rawBody, TierCreateRequest.class)` in the controller (lines 100, 120) the typed DTO must be **manually validated via `Validator.validate(dto)`** since `@Valid` only fires when Spring binds the parameter directly. Plan: inject a `jakarta.validation.Validator` into `TierCreateRequestValidator` and call `validator.validate(request)` at the top of post-binding validation; surface `ConstraintViolationException` (already handled at advice lines 269–290).

### 4.5 Throw pattern (target)

```java
// Before
throw new InvalidInputException("name is required");                                  // → code 999999
throw new InvalidInputException("[" + TIER_CLASS_A_PROGRAM_LEVEL_FIELD + "] Class A …"); // → code 9011

// After (uniform)
throw new InvalidInputException(TierErrorKeys.TIER_NAME_REQUIRED);             // → code 9001 from tier.properties
throw new InvalidInputException(TierErrorKeys.TIER_CLASS_A_PROGRAM_LEVEL_FIELD); // → code 9011 from tier.properties
```

For throws that need a **dynamic message** (e.g. "Class A field 'X' is not allowed"), two options:

1. **Format in code:** `throw new InvalidInputException(TierErrorKeys.TIER_CLASS_A_PROGRAM_LEVEL_FIELD + ":" + fieldName);` — advice splits on `:` to extract key vs context. **Not recommended** — adds parsing logic.
2. **Static message + log context:** properties file has the canonical message; the dynamic field name goes into the log only. Client gets `code: 9011, message: "Class A program-level field is not allowed on per-tier write — see field name in server logs"`. **Recommended** — keeps i18n catalog stable.
3. **MessageFormat placeholders:** properties file has `TIER.CLASS_A_PROGRAM_LEVEL_FIELD.message=Class A program-level field ''{0}'' is not allowed on per-tier write` and code throws via a small helper that resolves + substitutes. Promotion does **not** do this today; would require a new `InvalidInputException` constructor or helper. **Defer to follow-up.**

**Plan default: Option 2** — preserves i18n purity and matches promotion exactly. Field-name context goes into structured logs (existing `log.error` calls in advice line 82–83 already capture).

---

## 5. Error Code Catalog — Full Inventory

Codes 9001–9099 reserved for tier. Existing 9001–9024 preserved (number-stable migration). New codes 9025–9099 added for gap-fill validations.

### 5.1 Migrated codes (existing — number preserved, throw pattern changed)

| Code | Key | Message (canonical) | Trigger | Source location after migration |
|---|---|---|---|---|
| 9001 | `TIER.NAME_REQUIRED` | `name is required` | post-binding (DTO `@NotBlank`) | `TierCreateRequest.java` field annotation |
| 9002 | `TIER.NAME_TOO_LONG` | `name must not exceed 100 characters` | post-binding (DTO `@Size`) | `TierCreateRequest.java`, `TierUpdateRequest.java` |
| 9003 | `TIER.PROGRAM_ID_REQUIRED` | `programId is required` | post-binding (DTO `@NotNull`) | `TierCreateRequest.java` |
| 9004 | `TIER.INVALID_KPI_TYPE` | `kpiType must be one of the supported values` | post-binding (manual, enum validation) | `TierEnumValidation.validateEligibility` |
| 9005 | `TIER.THRESHOLD_MUST_BE_POSITIVE` | `threshold must be a positive value` | post-binding (DTO `@PositiveOrZero`) | `TierEligibilityConfig.java` |
| 9006 | `TIER.INVALID_COLOR_CODE` | `color must be hex format #RRGGBB` | post-binding (DTO `@Pattern`) | `TierCreateRequest.java`, `TierUpdateRequest.java` |
| 9008 | `TIER.DESCRIPTION_TOO_LONG` | `description must not exceed 500 characters` | post-binding (DTO `@Size`) | `TierCreateRequest.java`, `TierUpdateRequest.java` |
| 9009 | `TIER.INVALID_UPGRADE_TYPE` | `upgradeType must be one of the supported values` | post-binding (manual, enum) | `TierEnumValidation.validateEligibility` |
| 9010 | `TIER.INVALID_RENEWAL_CRITERIA` | `renewal.criteriaType is invalid` | post-binding (manual) | `TierRenewalValidation.validate` |
| 9011 | `TIER.CLASS_A_PROGRAM_LEVEL_FIELD` | `program-level field is not allowed on per-tier write — use program config` | pre-binding scan | `TierEnumValidation.scanForClassAKeys` |
| 9012 | `TIER.CLASS_B_SCHEDULE_FIELD` | `schedule-shaped field is not allowed on per-tier write` | pre-binding scan | `TierEnumValidation.validateNoClassBScheduleField` |
| 9013 | `TIER.ELIGIBILITY_CRITERIA_TYPE` | `eligibilityCriteriaType is a read-only field and must not appear on write requests` | pre-binding scan | `TierEnumValidation.validateNoEligibilityCriteriaTypeOnWrite` |
| 9014 | `TIER.START_DATE_ON_SLAB_UPGRADE` | `validity.startDate is not permitted when periodType is in the SLAB_UPGRADE family` | post-binding | `TierEnumValidation.validateNoStartDateForSlabUpgrade` |
| 9015 | `TIER.SENTINEL_STRING_MINUS_ONE` | `numeric field contains the string sentinel "-1"` | pre-binding scan | `TierEnumValidation.validateNoStringMinusOneSentinel` |
| 9016 | `TIER.SENTINEL_NUMERIC_MINUS_ONE` | `numeric field contains the sentinel value -1 — use a valid positive value or omit the field` | pre-binding scan | `TierEnumValidation.validateNoNumericMinusOneSentinel` |
| 9017 | `TIER.RENEWAL_CRITERIA_TYPE_DRIFT` | `renewal.criteriaType must be exactly "Same as eligibility"` | post-binding | `TierEnumValidation.validateRenewalCriteriaTypeCanonical` |
| 9018 | `TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE` | `validity.periodValue must be a positive integer when periodType is in the FIXED family` | post-binding | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue` |
| 9019 | `TIER.RENEWAL_DOWNGRADE_TO_INVALID` | `renewal.downgradeTo must be one of: SINGLE, THRESHOLD, LOWEST` | post-binding | `TierEnumValidation.validateRenewalDowngradeTo` |
| 9020 | `TIER.RENEWAL_MULTI_TRACKER` | `renewal.conditions[] may contain at most one TRACKER entry` | post-binding | `TierEnumValidation.validateRenewalConditionsAndExpression` |
| 9021 | `TIER.RENEWAL_EXPRESSION_INVALID` | `renewal.expressionRelation is not a valid DNF expression` | post-binding | `TierEnumValidation.validateRenewalExpressionRelation` |
| 9022 | `TIER.VALIDITY_RENEWAL_WINDOW_TYPE` | `validity.renewalWindowType must be one of: FIXED_DATE_BASED, LAST_CALENDAR_YEAR, CUSTOM_PERIOD` | post-binding | `TierEnumValidation.validateValidity` |
| 9023 | `TIER.VALIDITY_COMPUTATION_WINDOW_ORPHAN` | `validity.computationWindowStartValue / computationWindowEndValue require validity.renewalWindowType` | post-binding | `TierEnumValidation.validateValidity` |
| 9024 | `TIER.VALIDITY_NUMERIC_NEGATIVE` | `validity numeric fields must be greater than or equal to 0` | post-binding | `TierEnumValidation.validateValidity` |

### 5.2 New codes — gap-fill (additive, server-side enforcement of UI rules where vocabulary aligns)

| Code | Key | Message | UI rule covered | Trigger | Where to throw |
|---|---|---|---|---|---|
| 9025 | `TIER.NAME_NOT_UNIQUE` | `tier name must be unique within the program (case-insensitive)` | UI §2 row 2; UI §3.1 | post-binding business rule | `TierValidationService.validateNameUniqueness` — change to `equalsIgnoreCase` (today is `equals`) |
| 9026 | `TIER.NAME_BLANK_ON_UPDATE` | `tier name cannot be blank on update` | UI §3.1 | post-binding | `TierUpdateRequestValidator.validateCoreFields` (when name is non-null but blank) |
| 9027 | `TIER.COLOR_LENGTH_EXCEEDED` | `color field must not exceed 7 characters` | UI §2 row 5; UI §5 (Color max length 7) | post-binding (DTO `@Size(max=7)`) | `TierCreateRequest.java`, `TierUpdateRequest.java`. **Note:** the existing `@Pattern ^#[0-9A-Fa-f]{6}$` already enforces exactly 7 — this is a defensive duplicate. **Recommendation: skip 9027** unless the UI distinguishes "too long" from "wrong format" in its error UX. **Defer to your call.** |
| 9028 | `TIER.UPGRADE_VALUE_OUT_OF_RANGE` | `eligibility.threshold must be ≤ Integer.MAX_VALUE (2,147,483,647)` | UI §3.2 row 3 | post-binding | `TierCreateRequestValidator.validateThreshold` — add upper bound check |
| 9029 | `TIER.TRACKER_ID_REQUIRED` | `tracker condition requires both trackerId and trackerCondition when type is TRACKER` | UI §3.2 row 4–5 (Tracker ID + condition) | post-binding | `TierEnumValidation.validateConditionTypes` — add coupling check on each `TierCondition` where `type == "TRACKER"` |
| 9030 | `TIER.PERIOD_VALUE_OVERFLOW` | `validity.periodValue numeric value is out of bounds (max 25 digits)` | UI §3.4 row 3 (maxLength 25) | post-binding | `TierEnumValidation.validateValidity` — add digit-count check |
| 9031 | `TIER.RENEWAL_LAST_MONTHS_OUT_OF_RANGE` | `renewalLastMonths must be between 1 and 36 inclusive` | UI §3.5 row 4 | post-binding | `TierEnumValidation.validateValidity` — guard when `renewalWindowType == FIXED_DATE_BASED` |
| 9032 | `TIER.CUSTOM_PERIOD_MONTHS_OUT_OF_RANGE` | `customPeriodMonths must be between 1 and 36 inclusive` | UI §3.5 row 5 | post-binding | `TierEnumValidation.validateValidity` — guard when `renewalWindowType == CUSTOM_PERIOD` |
| 9033 | `TIER.CUSTOM_PERIOD_DELTA_TOO_LARGE` | `computationWindowStartValue − computationWindowEndValue must be ≤ 35` | UI §3.6 (CUSTOM_PERIOD row) | post-binding | `TierEnumValidation.validateValidity` — guard when `renewalWindowType == CUSTOM_PERIOD` |
| 9034 | `TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE` | `computationWindowStartValue must be between 1 and 36 inclusive when renewalWindowType is FIXED_DATE_BASED` | UI §3.6 (FIXED_DATE_BASED row) | post-binding | `TierEnumValidation.validateValidity` — tighten existing `>= 0` (9024) for FIXED_DATE_BASED case |
| 9035 | `TIER.MIN_DURATION_MUST_BE_POSITIVE` | `validity.minimumDuration must be greater than 0` | UI §4.1 row 1 | post-binding | `TierEnumValidation.validateValidity` — change from `>= 0` to `> 0` for `minimumDuration` |
| 9036 | `TIER.RENEWAL_CONDITION_VALUE_REQUIRED` | `renewal condition value is required when condition is checked` | UI §3.5 row 1 | post-binding | `TierRenewalValidation` — add per-condition value-non-empty check |
| 9037 | `TIER.RENEWAL_TRACKER_FIELDS_REQUIRED` | `renewal tracker conditions require trackerId, trackerCondition, and value to be non-empty` | UI §3.5 row 2 | post-binding | `TierRenewalValidation` — coupling check on `type == TRACKER` rows in `renewal.conditions[]` |

**Net additions: 12 new codes (9025–9037), or 11 if 9027 is deferred.**

### 5.3 Codes deferred to follow-up architect review

Per D5=a (out of scope):

- **`TIER.UPGRADE_TYPE_VOCABULARY_MISMATCH`** — UI vocabulary vs server vocabulary (no server change in this task).
- **`TIER.DOWNGRADE_CONDITION_VOCABULARY_MISMATCH`** — same.
- **`TIER.UPGRADE_MODE_*`** — field doesn't exist server-side.
- **`TIER.SECONDARY_CRITERIA_*`** — flag doesn't exist server-side.
- **`TIER.LIVE_TIER_HAS_ACTIVE_CUSTOMERS`** — requires customer-count query.
- **`TIER.DOWNGRADE_START_DATE_FIRST_OF_MONTH`** — depends on resolving downgrade-condition vocabulary first.

---

## 6. `tier.properties` — file content (proposed)

```properties
# Tier API error code & message catalog
# Range: 9001-9099
# Format: TIER.<KEY>.code = <number>
#         TIER.<KEY>.message = <text>

# 9001-9010 — core field validation
TIER.NAME_REQUIRED.code=9001
TIER.NAME_REQUIRED.message=name is required
TIER.NAME_TOO_LONG.code=9002
TIER.NAME_TOO_LONG.message=name must not exceed 100 characters
TIER.PROGRAM_ID_REQUIRED.code=9003
TIER.PROGRAM_ID_REQUIRED.message=programId is required
TIER.INVALID_KPI_TYPE.code=9004
TIER.INVALID_KPI_TYPE.message=kpiType must be one of the supported values
TIER.THRESHOLD_MUST_BE_POSITIVE.code=9005
TIER.THRESHOLD_MUST_BE_POSITIVE.message=threshold must be a positive value
TIER.INVALID_COLOR_CODE.code=9006
TIER.INVALID_COLOR_CODE.message=color must be hex format #RRGGBB
TIER.DESCRIPTION_TOO_LONG.code=9008
TIER.DESCRIPTION_TOO_LONG.message=description must not exceed 500 characters
TIER.INVALID_UPGRADE_TYPE.code=9009
TIER.INVALID_UPGRADE_TYPE.message=upgradeType must be one of the supported values
TIER.INVALID_RENEWAL_CRITERIA.code=9010
TIER.INVALID_RENEWAL_CRITERIA.message=renewal.criteriaType is invalid

# 9011-9018 — contract-hardening reject band (pre-binding scans)
TIER.CLASS_A_PROGRAM_LEVEL_FIELD.code=9011
TIER.CLASS_A_PROGRAM_LEVEL_FIELD.message=program-level field is not allowed on per-tier write — use program config
TIER.CLASS_B_SCHEDULE_FIELD.code=9012
TIER.CLASS_B_SCHEDULE_FIELD.message=schedule-shaped field is not allowed on per-tier write
TIER.ELIGIBILITY_CRITERIA_TYPE.code=9013
TIER.ELIGIBILITY_CRITERIA_TYPE.message=eligibilityCriteriaType is a read-only field and must not appear on write requests
TIER.START_DATE_ON_SLAB_UPGRADE.code=9014
TIER.START_DATE_ON_SLAB_UPGRADE.message=validity.startDate is not permitted when periodType is in the SLAB_UPGRADE family
TIER.SENTINEL_STRING_MINUS_ONE.code=9015
TIER.SENTINEL_STRING_MINUS_ONE.message=numeric field contains the string sentinel "-1"
TIER.SENTINEL_NUMERIC_MINUS_ONE.code=9016
TIER.SENTINEL_NUMERIC_MINUS_ONE.message=numeric field contains the sentinel value -1 — use a valid positive value or omit the field
TIER.RENEWAL_CRITERIA_TYPE_DRIFT.code=9017
TIER.RENEWAL_CRITERIA_TYPE_DRIFT.message=renewal.criteriaType must be exactly "Same as eligibility"
TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE.code=9018
TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE.message=validity.periodValue must be a positive integer when periodType is in the FIXED family

# 9019-9024 — renewal & validity
TIER.RENEWAL_DOWNGRADE_TO_INVALID.code=9019
TIER.RENEWAL_DOWNGRADE_TO_INVALID.message=renewal.downgradeTo must be one of: SINGLE, THRESHOLD, LOWEST
TIER.RENEWAL_MULTI_TRACKER.code=9020
TIER.RENEWAL_MULTI_TRACKER.message=renewal.conditions[] may contain at most one TRACKER entry
TIER.RENEWAL_EXPRESSION_INVALID.code=9021
TIER.RENEWAL_EXPRESSION_INVALID.message=renewal.expressionRelation is not a valid DNF expression
TIER.VALIDITY_RENEWAL_WINDOW_TYPE.code=9022
TIER.VALIDITY_RENEWAL_WINDOW_TYPE.message=validity.renewalWindowType must be one of: FIXED_DATE_BASED, LAST_CALENDAR_YEAR, CUSTOM_PERIOD
TIER.VALIDITY_COMPUTATION_WINDOW_ORPHAN.code=9023
TIER.VALIDITY_COMPUTATION_WINDOW_ORPHAN.message=validity.computationWindowStartValue / computationWindowEndValue require validity.renewalWindowType
TIER.VALIDITY_NUMERIC_NEGATIVE.code=9024
TIER.VALIDITY_NUMERIC_NEGATIVE.message=validity numeric fields must be greater than or equal to 0

# 9025-9037 — gap-fill validations (UI parity)
TIER.NAME_NOT_UNIQUE.code=9025
TIER.NAME_NOT_UNIQUE.message=tier name must be unique within the program (case-insensitive)
TIER.NAME_BLANK_ON_UPDATE.code=9026
TIER.NAME_BLANK_ON_UPDATE.message=tier name cannot be blank on update
TIER.COLOR_LENGTH_EXCEEDED.code=9027
TIER.COLOR_LENGTH_EXCEEDED.message=color field must not exceed 7 characters
TIER.UPGRADE_VALUE_OUT_OF_RANGE.code=9028
TIER.UPGRADE_VALUE_OUT_OF_RANGE.message=eligibility.threshold must be ≤ Integer.MAX_VALUE (2,147,483,647)
TIER.TRACKER_ID_REQUIRED.code=9029
TIER.TRACKER_ID_REQUIRED.message=tracker condition requires both trackerId and trackerCondition when type is TRACKER
TIER.PERIOD_VALUE_OVERFLOW.code=9030
TIER.PERIOD_VALUE_OVERFLOW.message=validity.periodValue numeric value is out of bounds
TIER.RENEWAL_LAST_MONTHS_OUT_OF_RANGE.code=9031
TIER.RENEWAL_LAST_MONTHS_OUT_OF_RANGE.message=renewalLastMonths must be between 1 and 36 inclusive
TIER.CUSTOM_PERIOD_MONTHS_OUT_OF_RANGE.code=9032
TIER.CUSTOM_PERIOD_MONTHS_OUT_OF_RANGE.message=customPeriodMonths must be between 1 and 36 inclusive
TIER.CUSTOM_PERIOD_DELTA_TOO_LARGE.code=9033
TIER.CUSTOM_PERIOD_DELTA_TOO_LARGE.message=computationWindowStartValue − computationWindowEndValue must be ≤ 35
TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE.code=9034
TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE.message=computationWindowStartValue must be between 1 and 36 inclusive when renewalWindowType is FIXED_DATE_BASED
TIER.MIN_DURATION_MUST_BE_POSITIVE.code=9035
TIER.MIN_DURATION_MUST_BE_POSITIVE.message=validity.minimumDuration must be greater than 0
TIER.RENEWAL_CONDITION_VALUE_REQUIRED.code=9036
TIER.RENEWAL_CONDITION_VALUE_REQUIRED.message=renewal condition value is required when condition is checked
TIER.RENEWAL_TRACKER_FIELDS_REQUIRED.code=9037
TIER.RENEWAL_TRACKER_FIELDS_REQUIRED.message=renewal tracker conditions require trackerId, trackerCondition, and value to be non-empty
```

(9007 is intentionally omitted — never declared in source. Stays available.)

---

## 7. `TierErrorKeys.java` — proposed constants class

Mirrors the design of `target_loyalty.properties` keys but in Java for typo-safe references.

```java
package com.capillary.intouchapiv3.tier.validation;

/** String constants for every key in tier.properties. Single source of truth on the Java side. */
public final class TierErrorKeys {
    private TierErrorKeys() {}

    // Core field
    public static final String TIER_NAME_REQUIRED              = "TIER.NAME_REQUIRED";
    public static final String TIER_NAME_TOO_LONG              = "TIER.NAME_TOO_LONG";
    public static final String TIER_PROGRAM_ID_REQUIRED        = "TIER.PROGRAM_ID_REQUIRED";
    public static final String TIER_INVALID_KPI_TYPE           = "TIER.INVALID_KPI_TYPE";
    public static final String TIER_THRESHOLD_MUST_BE_POSITIVE = "TIER.THRESHOLD_MUST_BE_POSITIVE";
    public static final String TIER_INVALID_COLOR_CODE         = "TIER.INVALID_COLOR_CODE";
    public static final String TIER_DESCRIPTION_TOO_LONG       = "TIER.DESCRIPTION_TOO_LONG";
    public static final String TIER_INVALID_UPGRADE_TYPE       = "TIER.INVALID_UPGRADE_TYPE";
    public static final String TIER_INVALID_RENEWAL_CRITERIA   = "TIER.INVALID_RENEWAL_CRITERIA";

    // Contract-hardening reject band (pre-binding)
    public static final String TIER_CLASS_A_PROGRAM_LEVEL_FIELD     = "TIER.CLASS_A_PROGRAM_LEVEL_FIELD";
    public static final String TIER_CLASS_B_SCHEDULE_FIELD          = "TIER.CLASS_B_SCHEDULE_FIELD";
    public static final String TIER_ELIGIBILITY_CRITERIA_TYPE       = "TIER.ELIGIBILITY_CRITERIA_TYPE";
    public static final String TIER_START_DATE_ON_SLAB_UPGRADE      = "TIER.START_DATE_ON_SLAB_UPGRADE";
    public static final String TIER_SENTINEL_STRING_MINUS_ONE       = "TIER.SENTINEL_STRING_MINUS_ONE";
    public static final String TIER_SENTINEL_NUMERIC_MINUS_ONE      = "TIER.SENTINEL_NUMERIC_MINUS_ONE";
    public static final String TIER_RENEWAL_CRITERIA_TYPE_DRIFT     = "TIER.RENEWAL_CRITERIA_TYPE_DRIFT";
    public static final String TIER_FIXED_FAMILY_MISSING_PERIOD_VALUE = "TIER.FIXED_FAMILY_MISSING_PERIOD_VALUE";

    // Renewal & validity
    public static final String TIER_RENEWAL_DOWNGRADE_TO_INVALID    = "TIER.RENEWAL_DOWNGRADE_TO_INVALID";
    public static final String TIER_RENEWAL_MULTI_TRACKER           = "TIER.RENEWAL_MULTI_TRACKER";
    public static final String TIER_RENEWAL_EXPRESSION_INVALID      = "TIER.RENEWAL_EXPRESSION_INVALID";
    public static final String TIER_VALIDITY_RENEWAL_WINDOW_TYPE    = "TIER.VALIDITY_RENEWAL_WINDOW_TYPE";
    public static final String TIER_VALIDITY_COMPUTATION_WINDOW_ORPHAN = "TIER.VALIDITY_COMPUTATION_WINDOW_ORPHAN";
    public static final String TIER_VALIDITY_NUMERIC_NEGATIVE       = "TIER.VALIDITY_NUMERIC_NEGATIVE";

    // Gap-fill (new)
    public static final String TIER_NAME_NOT_UNIQUE                  = "TIER.NAME_NOT_UNIQUE";
    public static final String TIER_NAME_BLANK_ON_UPDATE             = "TIER.NAME_BLANK_ON_UPDATE";
    public static final String TIER_COLOR_LENGTH_EXCEEDED            = "TIER.COLOR_LENGTH_EXCEEDED";
    public static final String TIER_UPGRADE_VALUE_OUT_OF_RANGE       = "TIER.UPGRADE_VALUE_OUT_OF_RANGE";
    public static final String TIER_TRACKER_ID_REQUIRED              = "TIER.TRACKER_ID_REQUIRED";
    public static final String TIER_PERIOD_VALUE_OVERFLOW            = "TIER.PERIOD_VALUE_OVERFLOW";
    public static final String TIER_RENEWAL_LAST_MONTHS_OUT_OF_RANGE = "TIER.RENEWAL_LAST_MONTHS_OUT_OF_RANGE";
    public static final String TIER_CUSTOM_PERIOD_MONTHS_OUT_OF_RANGE = "TIER.CUSTOM_PERIOD_MONTHS_OUT_OF_RANGE";
    public static final String TIER_CUSTOM_PERIOD_DELTA_TOO_LARGE    = "TIER.CUSTOM_PERIOD_DELTA_TOO_LARGE";
    public static final String TIER_FIXED_DATE_OFFSET_OUT_OF_RANGE   = "TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE";
    public static final String TIER_MIN_DURATION_MUST_BE_POSITIVE    = "TIER.MIN_DURATION_MUST_BE_POSITIVE";
    public static final String TIER_RENEWAL_CONDITION_VALUE_REQUIRED = "TIER.RENEWAL_CONDITION_VALUE_REQUIRED";
    public static final String TIER_RENEWAL_TRACKER_FIELDS_REQUIRED  = "TIER.RENEWAL_TRACKER_FIELDS_REQUIRED";
}
```

---

## 8. File-touch inventory

### 8.1 Created (2 files)
- `intouch-api-v3/src/main/resources/i18n/errors/tier.properties`
- `intouch-api-v3/src/main/java/com/capillary/intouchapiv3/tier/validation/TierErrorKeys.java`

### 8.2 Modified — production (≈11 files)
- `services/internal/MessageResolverService.java` — register `TIER` namespace
- `tier/dto/TierCreateRequest.java` — add `@NotBlank`/`@Size`/`@Pattern` annotations
- `tier/dto/TierUpdateRequest.java` — add `@Size`/`@Pattern` annotations
- `tier/model/TierEligibilityConfig.java` — add `@PositiveOrZero` on `threshold`
- `tier/validation/TierCreateRequestValidator.java` — drop numeric constants, migrate throws, invoke `Validator.validate(request)`
- `tier/validation/TierUpdateRequestValidator.java` — same
- `tier/validation/TierEnumValidation.java` — migrate ~20 throw sites; tighten `9024` for `minimumDuration` (> 0); add new throws for 9028, 9029, 9030, 9031, 9032, 9033, 9034
- `tier/validation/TierRenewalValidation.java` — migrate throw at line 43; add 9036, 9037
- `tier/TierValidationService.java` — change `equals` → `equalsIgnoreCase` for name uniqueness; migrate throws
- `tier/TierFacade.java` — migrate status-transition throws (lines 242, 268)
- `tier/TierApprovalHandler.java` — migrate throws (lines 71, 73, 110)
- `resources/TierController.java` — keep raw `JsonNode` path; no `@Valid` (because raw-body pattern remains); validator becomes responsible for invoking `jakarta.validation.Validator` post-`treeToValue`. Document this in the validator class javadoc.

### 8.3 Modified — tests (≈5 files)
- `tier/validation/TierCreateRequestValidatorTest` — assert resolved client-visible code for each rule (not just the exception type)
- `tier/validation/TierUpdateRequestValidatorTest` — same
- `tier/validation/TierEnumValidationTest` (or equivalent) — same; add tests for 9028–9037 cases
- `tier/validation/TierRenewalValidationTest` — same; add tests for 9036, 9037
- `tier/TierValidationServiceTest` (if exists) — case-insensitive uniqueness test

### 8.4 New tests (per new code 9025–9037)
13 new test methods, one per new rule. Sit in the same files as the validator they cover.

---

## 9. Test plan — assertion pattern (proposed)

```java
// Before (today)
assertThrows(InvalidInputException.class, () -> validator.validate(request, rawBody));

// After (mirrors promotion pattern + asserts client-visible code)
InvalidInputException ex = assertThrows(InvalidInputException.class,
        () -> validator.validate(request, rawBody));
assertEquals("TIER.NAME_REQUIRED", ex.getMessage());     // key, not text
// Round-trip the resolver to confirm code mapping
assertEquals(9001L, resolverService.getCode(ex.getMessage()));
assertEquals("name is required", resolverService.getMessage(ex.getMessage()));
```

A shared test helper `TierValidationAssert.assertThrowsWithKey(executable, key, expectedCode)` would keep tests tight. Plan: add as part of the test refactor.

---

## 10. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A throw uses a key that's not in `tier.properties` → resolver returns code `999999` silently | Medium (typo on either side) | Errors lose their numeric code in production | (a) Use `TierErrorKeys` constants in throws — Java compile-time safety. (b) Add a unit test that loads `tier.properties` and asserts every constant in `TierErrorKeys` has both `.code` and `.message` entries. **Recommended: include this test.** |
| Existing client integrations rely on the plain text message (e.g. UI matches on substring "name is required") | Low | UI error display regression | The migration preserves message text for the migrated codes; the **only** observable change is the `code` field flipping from `999999` → `9001`. UI clients matching on `code` benefit; clients matching on text are unaffected. |
| Mixed-locale risk — `target_loyalty-fr.properties` exists; if a Tier French translation isn't provided, French clients see English | Low | Cosmetic | Out of scope for this task. Note in follow-up. |
| `@Valid`-style annotations not firing because controller still uses raw `JsonNode` | High if not addressed | Annotations dead | Plan §4.4 explicitly addresses — validator invokes `Validator.validate(request)` post-`treeToValue`. **Crucial: confirm with reviewer.** |
| Case-insensitive uniqueness change in `TierValidationService.validateNameUniqueness` could break existing draft tiers if two of them differ only in case | Low (rare in practice) | Existing valid drafts become "non-unique" on next update | Run a one-off DB query in QA env first to detect collisions before deploy. List in test plan. |
| Some throws emit dynamic context (e.g. field name in Class A) — Option 2 in §4.5 drops that context from the client message | Medium | Less helpful client errors | Server log keeps the context (advice line 82–83). UX team may want richer messages — defer to Option 3 (MessageFormat) follow-up if needed. |

---

## 11. Open clarifications (none blocking — but flagged)

1. **9027 (color length 7 chars)** — keep as defensive duplicate or skip given `@Pattern` already enforces it? Plan default: **skip** unless UX wants distinct error.
2. **Dynamic-context messages** — Option 2 (static message + log context) vs Option 3 (MessageFormat). Plan default: **Option 2** (matches promotion).
3. **Test assertion helper** — add `TierValidationAssert` helper or inline the round-trip per test? Plan default: **add helper**.

---

## 12. Approval gate

Sign-off required on:
- Code allocations 9025–9037 (new)
- Out-of-scope list (§1)
- Migration approach for codes that today emit `999999` (§3.2)
- Properties-file content (§6)
- File-touch inventory (§8)

Once approved → proceed to `validation-rework-scope.md` execution: Phase 7 Designer rework (DTO + validator contract update), then Phase 8b (BTG — generate BT-xx test cases), then Phase 9 (SDET — RED), then Phase 10 (Developer — GREEN).
