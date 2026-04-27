# Validation Rework — Structured Rework Payload

> **Companion to:** `validation-plan.md` (read first)
> **Status:** PROPOSED — awaiting approval before any phase execution.
> **Date:** 2026-04-27
> **Trigger:** manual (user-initiated)
> **Severity:** HIGH
> **Source:** `validation-plan.md` decisions D1=a, D2=a, D3=b, D4=b, D5=a, D6=c
> **Pipeline phases affected (in cascade order):** 7 (Designer) → 8b (Business Test Gen) → 9 (SDET — RED) → 10 (Developer — GREEN) → 11 (Reviewer)

---

## Cascade Overview

```
[Manual rework trigger]
        │
        ▼
┌──────────────────────────┐
│ Phase 7 — Designer        │  ──► 03-designer.md (DTO + validator contract delta)
│ (interface contracts)     │
└──────────────┬───────────┘
               │  cascade
               ▼
┌──────────────────────────┐
│ Phase 8b — Business      │  ──► 04b-business-tests.md (BT-224.. new test cases)
│ Test Gen                 │
└──────────────┬───────────┘
               │  cascade
               ▼
┌──────────────────────────┐
│ Phase 9 — SDET (RED)     │  ──► 05-sdet.md + test code (failing tests + skeletons)
└──────────────┬───────────┘
               │  cascade
               ▼
┌──────────────────────────┐
│ Phase 10 — Developer      │  ──► 06-developer.md + production code (GREEN)
│ (GREEN)                   │
└──────────────┬───────────┘
               │  cascade
               ▼
┌──────────────────────────┐
│ Phase 11 — Reviewer       │  ──► 07-reviewer.md (re-verify gap closure)
└──────────────────────────┘
```

Forward-cascade rule (per pipeline orchestrator agent): each phase produces a **delta log** that feeds the rework payload of the next phase. If at any phase the delta exceeds 50% of the original artifact, the orchestrator switches to **full regeneration** for that phase.

---

## Affected REQ-xx Items

### CHANGED — existing requirements clarified (no scope change)

| REQ | Type | Classification | Description of change |
|---|---|---|---|
| REQ-27 | requirement | CLARIFIED | "rejected 400 InvalidInputException; error code **9013**" — code stays 9013, but emission path migrates from bracket-prefix string `"[9013] ..."` to key `"TIER.ELIGIBILITY_CRITERIA_TYPE"` resolved via `tier.properties`. Wire response unchanged. |
| REQ-28 | requirement | CLARIFIED | "Validation in API (Layer 1 of 3)" — the layer remains the same; the implementation now hybridises bean-validation annotations and the manual validator. |
| REQ-25, REQ-26, REQ-33..REQ-40 (the per-tier write contract) | requirement | CLARIFIED | All references to numeric error codes in these REQs are unchanged in numeric value but are **emitted via the new key catalog**. |

**Verification:** these REQs require no rewording. The change is purely in how the codes are produced inside the validators.

### ADDED — new requirements

| REQ | Type | Classification | Description |
|---|---|---|---|
| REQ-57 | requirement | ADDED | Tier name uniqueness within a program is **case-insensitive**. Source: `TIERS_VALIDATIONS.md` §2 row 2 ("checked on blur against `allTiersName`"). Maps to error code **9025** (`TIER.NAME_NOT_UNIQUE`). |
| REQ-58 | requirement | ADDED *(optional — see plan §11.1)* | `color` field length must not exceed 7 characters. Defensive duplicate of `@Pattern` `^#[0-9A-Fa-f]{6}$`. Maps to **9027** (`TIER.COLOR_LENGTH_EXCEEDED`). **Decision deferred to user.** |
| REQ-59 | requirement | ADDED | `eligibility.threshold` upper bound: must not exceed `Integer.MAX_VALUE` (2,147,483,647). Source: UI §3.2 row 3. Maps to **9028** (`TIER.UPGRADE_VALUE_OUT_OF_RANGE`). |
| REQ-60 | requirement | ADDED | When a `TierCondition.type == "TRACKER"`, both `trackerId` and `trackerCondition` are required. Source: UI §3.2 rows 4–5. Maps to **9029** (`TIER.TRACKER_ID_REQUIRED`). |
| REQ-61 | requirement | ADDED | `validity.periodValue` numeric value must be within representable bounds (digit-count ≤ 25; effectively constrained to `Integer` range). Source: UI §3.4 row 3 (`maxLength=25`). Maps to **9030** (`TIER.PERIOD_VALUE_OVERFLOW`). |
| REQ-62 | requirement | ADDED | When `validity.renewalWindowType == FIXED_DATE_BASED`, `computationWindowStartValue` must be in [1, 36] inclusive. Source: UI §3.6. Maps to **9034** (`TIER.FIXED_DATE_OFFSET_OUT_OF_RANGE`). |
| REQ-63 | requirement | ADDED | When `validity.renewalWindowType == FIXED_DATE_BASED`, `renewalLastMonths` must be in [1, 36] inclusive. Source: UI §3.5 row 4. Maps to **9031** (`TIER.RENEWAL_LAST_MONTHS_OUT_OF_RANGE`). Note: `renewalLastMonths` is currently not a wire field — Designer must decide whether to add it or fold the rule into another field (open clarification). |
| REQ-64 | requirement | ADDED | When `validity.renewalWindowType == CUSTOM_PERIOD`, `customPeriodMonths` must be in [1, 36] inclusive **and** `computationWindowStartValue − computationWindowEndValue ≤ 35`. Source: UI §3.5 row 5 + §3.6. Maps to **9032** + **9033**. |
| REQ-65 | requirement | ADDED | `validity.minimumDuration` must be **strictly greater than 0** (today the server allows 0). Source: UI §4.1 row 1. Maps to **9035** (`TIER.MIN_DURATION_MUST_BE_POSITIVE`). |
| REQ-66 | requirement | ADDED | A renewal condition row that is "checked" (i.e. present in `renewal.conditions[]`) must have a non-empty `value`. Source: UI §3.5 row 1. Maps to **9036** (`TIER.RENEWAL_CONDITION_VALUE_REQUIRED`). |
| REQ-67 | requirement | ADDED | A renewal condition with `type == "TRACKER"` must have all three of `trackerId`, `trackerCondition`, `value` non-empty. Source: UI §3.5 row 2. Maps to **9037** (`TIER.RENEWAL_TRACKER_FIELDS_REQUIRED`). |
| REQ-68 | requirement | ADDED *(architectural)* | All tier validation error responses must source their numeric `code` field and human-readable `message` field from `tier.properties` via `MessageResolverService`, mirroring the promotion CRUD pattern (`UnifiedPromotionValidatorService` + `target_loyalty.properties`). Validator code throws `InvalidInputException(key)` only — no inline numeric codes, no bracket-prefix workaround. |

### REMOVED — none

No requirement is removed by this rework.

### Out-of-scope items (NOT added — flagged for follow-up)

These were considered and **explicitly excluded** per `validation-plan.md` §1 (decision D5=a):

| Topic | Reason for exclusion |
|---|---|
| UI vocabulary for `upgradeType` (`POINTS_BASED`/`PURCHASE_BASED`/`TRACKER_VALUE_BASED`) | Server uses `EAGER`/`DYNAMIC`/`LAZY`. UI translation layer not investigated. Architect/product decision needed. |
| UI vocabulary for `downgradeCondition` (`FIXED`/`FIXED_DURATION`/`FIXED_CUSTOMER_REGISTRATION`) | Server uses different enum set. Same issue. |
| UI fields `upgradeMode`, `secondaryCriteriaEnabled`, `additionalConditionTrackers === CUSTOM` | Schema changes required (fields don't exist server-side). |
| "Tier not editable if LIVE with active customers" | Cross-repo customer-count query needed. Performance and architectural decision required. |
| Downgrade `startDate` on 1st-of-month rule | Depends on resolving downgrade-condition vocabulary first. |

---

## Affected BT-xx Items

### CONFIRMED — existing test cases unaffected by structural change

The migration of error-code emission (REQ-68) does NOT structurally invalidate existing BT-xx cases that assert on `InvalidInputException` thrown — those still throw, just with a different message argument. However, **assertions that match on message text** (e.g. `assertEquals("name is required", ex.getMessage())`) become invalid. Triage required per BT-xx.

| BT range | Triage needed | Reason |
|---|---|---|
| BT-190..BT-197 (Class A/B/sentinel scans) | UPDATE | Today throws `"[9011] Class A program-level field 'X' is not allowed..."`; after migration throws `"TIER.CLASS_A_PROGRAM_LEVEL_FIELD"`. Test must update message-text assertion → key assertion. **Code 9011 client-visible value unchanged.** |
| BT-198..BT-205 (SLAB_UPGRADE startDate, FIXED periodValue, renewal canonical) | UPDATE | Same — message text changes, code stays. |
| BT-206..BT-209 (PUT payload-only) | UPDATE | Same. |
| BT-210..BT-212 (transformer/normalizer paths) | CONFIRMED | These are read-path tests — not affected by validation throw migration. |
| BT-213..BT-215 (validator invocation order + Jackson strict) | UPDATE | One assertion in BT-213 may match message text — verify. |
| BT-216..BT-223 (edge cases) | UPDATE | Several match on message substrings — verify each. |

**Estimated triage:** ~20 BT-xx cases need UPDATE (text → key); ~5 unaffected (CONFIRMED).

### NEW — new test cases for new requirements

Numbering continues from BT-223 (highest existing). New range: **BT-224..BT-249** (26 cases provisionally allocated; final count set by Phase 8b).

| BT-ID (provisional) | Targets REQ | Validation | Test type |
|---|---|---|---|
| BT-224 | REQ-57 | Tier name `"GOLD"` collides with existing `"gold"` in same program → 400 code 9025 | UT |
| BT-225 | REQ-57 | Negative control: tier name `"Gold"` allowed in different program → no error | UT |
| BT-226 | REQ-57 | Update path: rename current tier to its own existing name with different case → no error (excludes self) | UT |
| BT-227 | REQ-58 *(only if REQ-58 confirmed)* | Color length > 7 (e.g. `#FF00FFx`) → 400 code 9027 OR 9006 (ambiguity — Designer decides) | UT |
| BT-228 | REQ-59 | `eligibility.threshold = 2147483648.0` → 400 code 9028 | UT |
| BT-229 | REQ-59 | Negative control: `threshold = 2147483647` (max) → no error | UT |
| BT-230 | REQ-60 | Condition `{type: "TRACKER", trackerId: 5}` (missing trackerCondition) → 400 code 9029 | UT |
| BT-231 | REQ-60 | Condition `{type: "TRACKER", trackerCondition: 1}` (missing trackerId) → 400 code 9029 | UT |
| BT-232 | REQ-60 | Negative control: `{type: "PURCHASE", value: "100"}` no tracker fields needed → no error | UT |
| BT-233 | REQ-61 | `validity.periodValue` with 26-digit numeric input → 400 code 9030 | UT |
| BT-234 | REQ-62 | `renewalWindowType=FIXED_DATE_BASED, computationWindowStartValue=37` → 400 code 9034 | UT |
| BT-235 | REQ-62 | Negative control: `computationWindowStartValue=36` (max) → no error | UT |
| BT-236 | REQ-62 | `renewalWindowType=FIXED_DATE_BASED, computationWindowStartValue=0` → 400 code 9034 | UT |
| BT-237 | REQ-63 | Designer must clarify wire-field name for `renewalLastMonths` first; test deferred until contract resolved | UT (deferred) |
| BT-238 | REQ-64 | `renewalWindowType=CUSTOM_PERIOD, computationWindowStartValue=40, computationWindowEndValue=4` → delta 36 > 35 → 400 code 9033 | UT |
| BT-239 | REQ-64 | Negative control: delta = 35 → no error | UT |
| BT-240 | REQ-65 | `validity.minimumDuration=0` → 400 code 9035 | UT |
| BT-241 | REQ-65 | Negative control: `minimumDuration=1` → no error | UT |
| BT-242 | REQ-65 | Backward-compat: `minimumDuration=null` (omitted) → no error | UT |
| BT-243 | REQ-66 | `renewal.conditions = [{type: "PURCHASE", value: ""}]` → 400 code 9036 | UT |
| BT-244 | REQ-66 | Negative control: `{type: "PURCHASE", value: "100"}` → no error | UT |
| BT-245 | REQ-67 | `renewal.conditions = [{type: "TRACKER", trackerId: 5, trackerCondition: 1}]` (missing value) → 400 code 9037 | UT |
| BT-246 | REQ-68 | All migrated codes (9001..9024) round-trip through `MessageResolverService.getCode()` and return the expected numeric code | UT (architectural smoke test) |
| BT-247 | REQ-68 | `tier.properties` consistency: every `TierErrorKeys` constant has both `.code` and `.message` entries (loaded via `Properties.load()`) | UT (catalog-completeness test) |
| BT-248 | REQ-68 | `MessageResolverService.fileNameMap` contains the `TIER` namespace | UT (registration smoke test) |
| BT-249 | REQ-68 | `TargetGroupErrorAdvice.handleInvalidInputException` returns `code=9001` for a thrown `InvalidInputException("TIER.NAME_REQUIRED")` (integration test through advice) | IT |

**Net:** 26 provisional NEW cases. Phase 8b will refine the count when it produces `04b-business-tests.md` updates.

### OBSOLETE — none

No BT-xx case is invalidated outright by this rework. All existing cases either remain valid (CONFIRMED) or need their assertion updated (UPDATE).

---

## Phase 7 (Designer) — Rework Payload

```
REWORK REQUEST:
  Target phase: Phase 7 — Designer
  Source: Manual (validation-plan.md sign-off)
  Trigger: manual
  Severity: HIGH

  Affected items:
  | ID      | Type        | Classification | Description |
  |---------|-------------|---------------|-------------|
  | REQ-27  | requirement | CLARIFIED      | Code 9013 emission path changes (key-based) |
  | REQ-57  | requirement | ADDED          | Case-insensitive name uniqueness |
  | REQ-58  | requirement | ADDED          | Color length ≤ 7 (optional, defer if user agrees) |
  | REQ-59  | requirement | ADDED          | Threshold ≤ Integer.MAX_VALUE |
  | REQ-60  | requirement | ADDED          | TRACKER condition trackerId + trackerCondition coupling |
  | REQ-61  | requirement | ADDED          | periodValue digit-count bound |
  | REQ-62  | requirement | ADDED          | FIXED_DATE_BASED window 1..36 |
  | REQ-63  | requirement | ADDED          | renewalLastMonths 1..36 (wire-field design open) |
  | REQ-64  | requirement | ADDED          | CUSTOM_PERIOD month bounds + delta ≤ 35 |
  | REQ-65  | requirement | ADDED          | minimumDuration > 0 |
  | REQ-66  | requirement | ADDED          | Renewal condition value required when checked |
  | REQ-67  | requirement | ADDED          | Renewal TRACKER fields all required |
  | REQ-68  | requirement | ADDED          | All errors source from i18n key catalog (architectural mirror) |

  Context: Mirror promotion validation pattern (UnifiedPromotionValidatorService + target_loyalty.properties).
           See validation-plan.md for the full architecture and decision rationale (D1..D6).
```

### Designer deliverable updates

`03-designer.md` must add or revise the following sections:

1. **Validator contract** — refresh the existing `TierCreateRequestValidator` / `TierUpdateRequestValidator` interface tables to:
   - Replace `int TIER_NAME_REQUIRED = 9001` declarations with `String TIER_NAME_REQUIRED = "TIER.NAME_REQUIRED"` (typed string constants from `TierErrorKeys`).
   - Document the throw pattern: `throw new InvalidInputException(TierErrorKeys.TIER_NAME_REQUIRED);`
   - Document the post-`treeToValue` invocation of `jakarta.validation.Validator.validate(request)` inside the validator (controller stays raw `JsonNode`).

2. **DTO contract** — refresh `TierCreateRequest`, `TierUpdateRequest`, `TierEligibilityConfig` field tables to add the bean-validation annotations from `validation-plan.md` §4.4:
   - `name` → `@NotBlank(message="TIER.NAME_REQUIRED") @Size(max=100, message="TIER.NAME_TOO_LONG")`
   - `description` → `@Size(max=500, message="TIER.DESCRIPTION_TOO_LONG")`
   - `color` → `@Pattern(regexp="^#[0-9A-Fa-f]{6}$", message="TIER.INVALID_COLOR_CODE")`
   - `threshold` → `@PositiveOrZero(message="TIER.THRESHOLD_MUST_BE_POSITIVE")`

3. **New section: "Error code catalog (`tier.properties`)"** — paste the full key/code table from `validation-plan.md` §5 and §6.

4. **New section: "TierErrorKeys constants class"** — paste the constants from `validation-plan.md` §7.

5. **New section: "MessageResolverService registration"** — note the one-line addition to `fileNameMap`.

6. **New section: "Validation rule additions (REQ-57..REQ-67)"** — for each new REQ, document:
   - The validator method that owns it (existing or new)
   - The error key it throws
   - The trigger phase (pre-binding scan / post-binding / business rule)
   - Test coverage pointer

7. **Open clarification for Designer to resolve:** REQ-63 implies a wire field `renewalLastMonths` that may not exist in `TierValidityConfig`. Designer must either:
   - Add it as a new wire field (with annotations + persistence considerations), OR
   - Fold the rule into an existing field (e.g. `computationWindowStartValue` when `renewalWindowType == FIXED_DATE_BASED`), OR
   - Defer REQ-63 to a separate rework with vocabulary-alignment work.

### Phase 7 expected output
- Updated `03-designer.md` (delta-only, not full rewrite — delta is well under 50%)
- Phase 7 delta log appended: which validator methods change, which DTO annotations are added, which new methods are introduced for REQ-57..REQ-67
- `FORWARD CASCADE PAYLOAD` for Phase 8b listing the same affected items

---

## Phase 8b (Business Test Gen) — Rework Payload

```
REWORK REQUEST:
  Target phase: Phase 8b — Business Test Generation
  Source: Phase 7 (Designer cascade)
  Trigger: cascade
  Severity: HIGH

  Affected items:
  | ID      | Type        | Classification | Description |
  |---------|-------------|---------------|-------------|
  | REQ-57..REQ-68 | requirement | ADDED   | New rules need BT-xx coverage |
  | BT-190..BT-223 (subset) | test-case | UPDATE | Message-text assertions → key assertions |
  | (none)  | test-case   | OBSOLETE       | No tests are removed |
  | BT-224..BT-249 (provisional) | test-case | NEW | Per REQ-57..REQ-68 + architectural smoke tests |

  Context: Cascade from Phase 7 — generate BT-xx coverage for new REQs and update existing BT-xx whose
           assertions match on plain message text (which has changed to key strings).
```

### Business Test Gen deliverable updates

`04b-business-tests.md` must:

1. **Append a Rework Delta section** following the pipeline's rework-delta-log format (per orchestrator agent definition):
   - Triage summary (CONFIRMED / UPDATE / REGENERATE / OBSOLETE / NEW counts)
   - Change detail per BT-xx
   - Structured-disagreement log (if any feedback items challenged)

2. **Apply per-test triage:**
   - **CONFIRMED:** BT-210, BT-211, BT-212 (read-path tests, untouched)
   - **UPDATE:** BT-190..BT-209, BT-213..BT-223 — change message-text assertions to key assertions; final code value unchanged
   - **NEW:** BT-224..BT-249 (per the table in this scope file) — Phase 8b finalises numbering & wording

3. **Architectural smoke tests (BT-246..BT-249)** — these are catalog-integrity tests, not feature tests; they protect against drift between `TierErrorKeys` constants and `tier.properties` entries.

### Phase 8b expected output
- Updated `04b-business-tests.md`
- Delta log appended
- `FORWARD CASCADE PAYLOAD` for Phase 9 listing affected BT-xx IDs and change classifications

---

## Phase 9 (SDET — RED) — Rework Payload

```
REWORK REQUEST:
  Target phase: Phase 9 — SDET (RED)
  Source: Phase 8b (BTG cascade)
  Trigger: cascade
  Severity: HIGH

  Affected items:
  | ID      | Type        | Classification | Description |
  |---------|-------------|---------------|-------------|
  | BT-190..BT-223 (UPDATE subset) | test-case | UPDATE | Update existing test methods' assertions |
  | BT-224..BT-249 | test-case | NEW          | Write new test methods + skeleton stubs |

  Context: Migrate existing test assertions and add new test methods.
           At end of phase, build must compile and the new tests must FAIL (RED).
           Existing tests must continue to pass after the assertion-update — they
           are testing the same behaviour, just asserting on the new key string.
```

### SDET deliverable updates

1. **Update existing test methods** in `TierCreateRequestValidatorTest`, `TierUpdateRequestValidatorTest`, `TierEnumValidationTest`, `TierRenewalValidationTest`:
   - Change `assertEquals("name is required", ex.getMessage())` → `assertEquals("TIER.NAME_REQUIRED", ex.getMessage())`
   - Add round-trip assertion through `MessageResolverService.getCode(ex.getMessage())` → expected numeric code
   - Plan §9 helper `TierValidationAssert.assertThrowsWithKey(executable, key, expectedCode)` is recommended.

2. **Write new test methods** for BT-224..BT-249 — these will FAIL initially (production validators don't yet implement the new rules).

3. **Skeleton production-class stubs** — for any new validator helper methods Designer specified (e.g. `validateThresholdUpperBound`, `validateRenewalConditionsAndPairings`), add empty stubs in `TierEnumValidation` / `TierRenewalValidation` that throw `UnsupportedOperationException` so build compiles but tests fail.

4. **Confirm RED** — `mvn test -pl intouch-api-v3` must compile (PASS) and the new tests must fail (RED expected).

5. **`tier.properties` consistency test (BT-247)** — write this test now even though the file doesn't exist yet; it will fail until Phase 10 creates the file. That's the RED state — correct.

### Phase 9 expected output
- Updated `05-sdet.md` with RED confirmation
- Modified test files committed
- New test files committed (failing)
- Skeleton stubs committed
- `mvn compile` PASSES, `mvn test` shows expected RED for new tests

---

## Phase 10 (Developer — GREEN) — Rework Payload

```
REWORK REQUEST:
  Target phase: Phase 10 — Developer (GREEN)
  Source: Phase 9 (SDET cascade)
  Trigger: cascade
  Severity: HIGH

  Affected items:
  | (Production-code work — see deliverable updates below) |

  Context: Implement the production code that turns RED tests GREEN.
           Migration of existing throws is part of this phase too — the
           test-assertion changes from Phase 9 will fail until the throws
           themselves are migrated.
```

### Developer deliverable updates

In dependency order:

1. **Create `tier.properties`** — full content from `validation-plan.md` §6.
2. **Create `TierErrorKeys.java`** — full content from `validation-plan.md` §7.
3. **Register `TIER` namespace** in `MessageResolverService.fileNameMap` (one-line add).
4. **Migrate existing throws** in:
   - `TierCreateRequestValidator.java` — `validateCoreFields`, `validateThreshold`
   - `TierUpdateRequestValidator.java` — same
   - `TierEnumValidation.java` — all 14 throw sites
   - `TierRenewalValidation.java` — line 43 throw
   - `TierValidationService.java` — lines 54, 108
   - `TierFacade.java` — lines 242, 268
   - `TierApprovalHandler.java` — lines 71, 73, 110
5. **Add bean-validation annotations** to DTOs:
   - `TierCreateRequest` — `@NotBlank`/`@Size`/`@Pattern` per plan §4.4
   - `TierUpdateRequest` — `@Size`/`@Pattern` (no `@NotBlank` on update)
   - `TierEligibilityConfig` — `@PositiveOrZero` on `threshold`
6. **Inject `jakarta.validation.Validator`** into `TierCreateRequestValidator` and `TierUpdateRequestValidator`; invoke `validator.validate(request)` after the `treeToValue` call (i.e. inside `validate(request, rawBody)` near the top of post-binding section).
7. **Implement new validations** for REQ-57..REQ-67:
   - REQ-57 — change `TierValidationService.validateNameUniqueness` and `validateNameUniquenessExcluding` from `equals` to `equalsIgnoreCase` (or normalise lowercase before compare). **Watch the case-insensitive risk in plan §10 — add a one-off DB scan to QA env.**
   - REQ-59 — add upper-bound check in `TierCreateRequestValidator.validateThreshold` (`> Integer.MAX_VALUE`)
   - REQ-60 — add coupling check inside `TierEnumValidation.validateConditionTypes`
   - REQ-61 — add digit-count guard in `TierEnumValidation.validateValidity`
   - REQ-62 — tighten 9024 case for `FIXED_DATE_BASED` (require ≤ 36 in addition to ≥ 0)
   - REQ-64 — add delta check (start − end ≤ 35) when `renewalWindowType == CUSTOM_PERIOD`
   - REQ-65 — change `minimumDuration` guard from `< 0` to `<= 0` (i.e. emit error when `minimumDuration == 0`)
   - REQ-66, REQ-67 — add new methods in `TierRenewalValidation`
8. **Resolve REQ-63 open question with Designer** before implementing — wire-field design pending.
9. **Run full build + tests** — must be GREEN. Verify catalog-integrity tests (BT-246..BT-249) pass.

### Phase 10 expected output
- Updated `06-developer.md` with GREEN confirmation
- Production code committed in small commits (one per logical unit — file creation, registration, per-validator migration, per new REQ implementation)
- All tests pass

---

## Phase 11 (Reviewer) — Rework Payload

```
REWORK REQUEST:
  Target phase: Phase 11 — Reviewer
  Source: Phase 10 (Developer cascade)
  Trigger: cascade
  Severity: HIGH

  Context: Re-verify the gap-closure work against TIERS_VALIDATIONS.md (UI source of truth)
           and validation-plan.md (architectural target). Confirm out-of-scope items remain
           flagged but unaddressed (this is intentional per D5=a).
```

### Reviewer deliverable

`07-reviewer.md` must add a new section **"Validation rework verification"** with:

| Check | Result |
|---|---|
| All 24 existing codes (9001–9024) round-trip through resolver and emit correct numeric value | ✅ / ❌ + evidence |
| All 13 new codes (9025–9037) emit correct numeric value | ✅ / ❌ + evidence |
| `tier.properties` and `TierErrorKeys` are mutually consistent (catalog-integrity test passes) | ✅ / ❌ |
| Out-of-scope items remain unimplemented and clearly flagged in `validation-plan.md` §1 and `validation-rework-scope.md` "Out-of-scope items" section | ✅ / ❌ |
| Wire-format response shape unchanged (no breaking change to existing consumers) | ✅ / ❌ |
| Bean-validation annotations on DTOs do not produce duplicate errors when manual validator also runs | ✅ / ❌ — **explicit dedup verification required** |
| Case-insensitive uniqueness (REQ-57) does not regress against existing draft data — QA env scan completed | ✅ / ❌ |
| Designer's REQ-63 resolution applied | ✅ / ❌ |

---

## Estimated Rework Depth

Per the orchestrator agent's definitions:

| Phase | Depth | Rationale |
|---|---|---|
| Phase 7 (Designer) | **MODERATE** | Adds 11 REQs, clarifies a few existing ones, refreshes 4–5 contract tables. Delta well under 50% of `03-designer.md`. |
| Phase 8b (BTG) | **MODERATE** | 26 NEW BT-xx, ~25 UPDATE BT-xx, 0 OBSOLETE. Delta around 25–35% of `04b-business-tests.md`. |
| Phase 9 (SDET — RED) | **MODERATE** | ~25 test-method updates + 26 new test methods + 5–10 skeleton stubs. |
| Phase 10 (Developer — GREEN) | **MODERATE-DEEP** | New file (`tier.properties` + `TierErrorKeys`), 1 line in resolver, ~30 throw migrations across 7 files, 12 new validation rule implementations, 7 DTO annotation additions. |
| Phase 11 (Reviewer) | **SHALLOW** | Verification-only pass. |

**Aggregate:** MODERATE (no full regeneration triggered).

---

## Approval & Execution Order

After user approval of this scope file:

1. Pipeline orchestrator logs the rework in `pipeline-state.json`:
   ```json
   {
     "from": "manual",
     "to": "7",
     "trigger": "manual",
     "reason": "UI-parity validation gap closure + i18n key catalog migration",
     "scope": ["REQ-27","REQ-57","REQ-58","REQ-59","REQ-60","REQ-61","REQ-62","REQ-63","REQ-64","REQ-65","REQ-66","REQ-67","REQ-68"],
     "severity": "HIGH",
     "resolved": false,
     "cascade_phases": ["8b","9","10","11"]
   }
   ```
2. Phase 7 runs in rework mode using the payload above.
3. Forward cascade fires automatically on each phase completion.
4. User pause prompts between phases per pipeline rules.

**No code changes happen until Phase 7 is invoked.**
