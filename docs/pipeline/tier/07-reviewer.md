# Phase 11 — Reviewer

> **Date:** 2026-04-23
> **Branch:** `raidlc/ai_tier`
> **Scope:** Rework #6a contract-hardening (8 new error codes 9011-9018) + Rework Cycle 1 wiring/wire-contract fixes
> **Skill:** `/reviewer`
> **Overall Verdict:** APPROVED WITH WARNINGS

---

## Executive Summary

Rework #6a adds 8 new error-code validators (9011–9018) implementing write-narrow/read-wide asymmetry (ADR-21R), Jackson strict-mode gate (ADR-20R), FIXED-family periodType duration requirement (ADR-19R/REQ-56), and distinct error code band (ADR-17R). The feature is **functionally correct at the unit level**: 311+ tier unit tests pass (Java 17.0.17-amzn, Maven 3.5.4). Integration tests require Docker (pre-existing P3 carry-forward) and did not run.

Two warnings must be resolved before deploy:

- **R11-1 (WARNING):** `api-handoff.md` §5.3 / §5.4 / §10.19 documents that sending `"downgrade"` on POST/PUT returns error code **9011**. This is **factually incorrect**: `"downgrade"` is NOT in `CLASS_A_CANONICAL_KEYS`; test BT-197 explicitly confirms the Class A scanner does NOT fire for this key. The rejection mechanism is Jackson strict mode (generic 400), not 9011. Any UI consumer routing on `errors[0].code === 9011` for the downgrade round-trip guard will mis-route.

- **R11-2 (WARNING — ADR-20R fragility, F-10c-4):** The `ObjectMapper` bean at `IntouchApiV3Application.java:94-99` is `new ObjectMapper()` with only `setTimeZone()` — no explicit `configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true)`. Standard Jackson 2.x default is `FAIL_ON_UNKNOWN_PROPERTIES=false`. If this default applies, `"downgrade"` and other unclassified unknown keys are **silently swallowed**, not rejected. The TierCreateRequest javadoc claims "global strict default, verified §6a.1 F1-F2" — but no code-backed evidence was found confirming F1. User decision Q1=c ("verify via test") requires a pre-merge IT or focused UT that sends `{"downgrade": {...}}` end-to-end through `objectMapper.treeToValue()` and asserts a 400 response.

All 8 error validators, the pre/post-binding scan order, the bracket-prefix error extractor, G-07 tenant isolation, and G-13 exception-handling rules are correctly implemented.

---

## Check 1 — Requirements Alignment

Evidence source: `TierEnumValidation.java`, `TierCreateRequestValidator.java`, `TierUpdateRequestValidator.java`, `TierController.java`, `TierCreateRequestValidatorTest.java` (311+ tests, all PASS).

| REQ | Description | Code Location | Status |
|-----|-------------|---------------|--------|
| REQ-23 / ADR-21R | Class A program-level fields rejected on per-tier write | `TierEnumValidation.validateNoClassAProgramLevelField()` — recursive scan, 9011 | PASS |
| ADR-21R §6a.4.3 | Class B schedule fields rejected at root level | `TierEnumValidation.validateNoClassBScheduleField()` — root-only scan, 9012 | PASS |
| REQ-27 / ADR-20R | `downgrade` field removed from write DTO; rejected by Jackson strict-mode | `TierCreateRequest.java` — no `downgrade` field; reliance on Jackson | PASS (but see R11-2 warning) |
| REQ-21 / ADR-19R | `startDate` rejected for SLAB_UPGRADE family | `TierEnumValidation.validateNoStartDateForSlabUpgrade()` — post-binding, 9014 | PASS |
| REQ-56 / ADR-19R | FIXED family requires positive `periodValue` | `TierEnumValidation.validateFixedFamilyRequiresPositivePeriodValue()` — post-binding, 9018 | PASS |
| §6a.4.2 | `eligibilityCriteriaType` rejected on write | `TierEnumValidation.validateNoEligibilityCriteriaTypeOnWrite()` — recursive, 9013 | PASS |
| §6a.4.2 | String `-1` sentinel rejected | `TierEnumValidation.validateNoStringMinusOneSentinel()` — recursive, 9015 | PASS |
| §6a.4.2 | Numeric `-1` sentinel rejected | `TierEnumValidation.validateNoNumericMinusOneSentinel()` — recursive, 9016 | PASS |
| §6a | Renewal criteriaType must be "Same as eligibility" | `TierEnumValidation.validateRenewalCriteriaTypeCanonical()` — post-binding, 9017 | PASS |
| ADR-17R | Error codes 9011-9018 form a distinct band | `TierEnumValidation.java:176-184` — 8 constants declared | PASS |
| ADR-18R | Per-slab canonical form | `TierCreateRequest`, `TierUpdateRequest` — no slab multiplexing | PASS |
| Q11 hard-flip | `downgrade` removed from `TierCreateRequest` and `TierUpdateRequest` | Both DTOs confirmed — no `downgrade` field, no getter/setter | PASS |

**Pre-binding scan order** (TierCreateRequestValidator.java:66-73):
```
9011 → 9012 → 9013 → 9015 → 9016
```
Matches the fail-fast specification from §6a.4.4. PASS.

**Post-binding scan order** (TierCreateRequestValidator.java:82-91):
```
9014 → 9018 → endDate ordering → renewal → 9017
```
Matches Designer LLD. PASS.

**TierUpdateRequestValidator** wires identical pre/post-binding scans. PASS.

**TierController** wiring: `@RequestBody JsonNode rawBody` → `objectMapper.treeToValue()` → rawBody forwarded to facade → validator (lines 97-103, 117-122). PASS.

**FIXED-family membership** (C7 — read from code): `FIXED` and `FIXED_CUSTOMER_REGISTRATION` only. `FIXED_LAST_UPGRADE` is phantom (not a real periodType). Validators correctly enumerate only the 2-member FIXED family. PASS.

---

## Check 2 — Session Memory Alignment

Evidence source: `session-memory.md` (lines 498-506, 741-748), `TierEnumValidation.java:176-184`.

**PASS (with documentation note):**

The Q-OP-1 table in session memory (lines 498-506) shows a DRAFT allocation from the lock phase:
- 9013 = downgrade, 9014 = advancedSettings, 9015 = -1 sentinel, 9016 = startDate/SLAB_UPGRADE

This is **superseded** by the Designer Phase 7 LLD (session-memory lines 741-748), which carries the final allocation:
- 9013 = `eligibilityCriteriaType`, 9014 = `startDate`/SLAB_UPGRADE, 9015 = string `-1`, 9016 = numeric `-1`, 9017 = renewal drift, 9018 = FIXED missing `periodValue`

The **code** and **api-handoff.md** both match the Designer Phase 7 final allocation — not the Q-OP-1 draft. This is correct.

**Action needed:** Session-memory Q-OP-1 table (lines 498-506) is stale documentation. It should be annotated or updated to reference the Designer Phase 7 supersession. This is a documentation artifact only — it does not affect runtime behavior.

**Other session-memory alignments:**
- F1 "Global Jackson is STRICT": session-memory records this as a Designer finding. The code reality is disputed (see R11-2). Session memory should reflect R11-2 as an open item.
- Q11 hard-flip confirmed in session memory: `downgrade` removed from write DTOs. PASS.
- ADR-21R (write-narrow/read-wide): session memory records this correctly. PASS.
- ADR-19R (FIXED family duration requirement): session memory records this correctly. PASS.

---

## Check 3 — Security (GUARDRAILS)

Evidence source: `TierController.java`, `TargetGroupErrorAdvice.java`, `TierEnumValidation.java`.

### G-07 — Multi-tenancy (CRITICAL)

**PASS.** `orgId` is sourced exclusively from `token.getIntouchUser().getOrgId()` (TierController.java:99 POST path, PUT path). No `orgId` in request body accepted. Error responses in `TargetGroupErrorAdvice` log `e.getMessage()` — no tenant-identifying data in error body. Info-level logs in `TierController` include `orgId` for audit — correct usage (audit log, not error response). G-07.5: satisfied.

### G-13 — Exception Handling (HIGH)

**PASS.**

- G-13.1: `InvalidInputException`, `NotFoundException`, `ConflictException` used throughout. No raw Java exceptions thrown in business logic.
- G-13.2: No `try-catch` blocks in `TierController` handlers. Exception routing delegated to `TargetGroupErrorAdvice` and local `@ExceptionHandler` methods.
- G-13.3: Two-layer validation confirmed — pre-binding (raw `JsonNode`) + post-binding (typed DTO).
- G-13.4: Bracket-prefix format `[9011] message` confirmed at `TierEnumValidation.java:176-184`. Extractor regex at `TargetGroupErrorAdvice.java:87-101` strips the prefix and constructs `ApiError(code, strippedMsg)`.

### G-03 — Input Validation (CRITICAL)

**PASS.** All 8 validators enforce whitelisting/sentinel rejection. `validateNoClassAProgramLevelField` and `validateNoEligibilityCriteriaTypeOnWrite` walk the full tree recursively — no bypass via nesting. `validateNoClassBScheduleField` is root-only per ADR-21R specification (schedule/nudges/notificationConfig are root-level only by wire contract).

### G-12 — AI Guardrails (CRITICAL)

Not applicable to this scope.

### G-01 — Timezone (CRITICAL)

Not directly applicable. `validateEndDateNotBeforeStartDate` uses `String.compareTo()` on ISO-8601 dates — no timezone conversion in this comparison. P4 carry-forward applies (see Findings Detail).

---

## Check 4 — Documentation (api-handoff.md)

Evidence source: `api-handoff.md` (all relevant sections), `TierEnumValidation.java:190-199`, `TierCreateRequestValidatorTest.java:140-156 (BT-197)`.

### R11-1 (WARNING) — Incorrect error code for `downgrade` key in api-handoff.md

**FAIL on §5.3 / §5.4 / §10.19.**

**Evidence (C7):**
1. `TierEnumValidation.java:190-199` — `CLASS_A_CANONICAL_KEYS` contains 8 keys: `isActive`, `reminders`, `downgradeConfirmation`, `renewalConfirmation`, `retainPoints`, `dailyDowngradeEnabled`, `isDowngradeOnReturnEnabled`, `isDowngradeOnPartnerProgramExpiryEnabled`. The key `"downgrade"` is NOT in this list.
2. `TierCreateRequestValidatorTest.java:140-156 (BT-197)` — explicitly asserts `assertDoesNotThrow(() -> TierEnumValidation.validateNoClassAProgramLevelField(rawBody))` for a body containing `"downgrade": {...}`. Comment: `"\"downgrade\" is NOT a Class A field — scanner must ignore it (Jackson catches it)."`.

**Inaccurate statements in api-handoff.md:**
- §5.3 request field table: `downgrade.*` row states "Code 9011 (Class A program-level field)" — **WRONG**. The rejection is via Jackson strict-mode (if strict), not code 9011.
- §5.3 prose: "Sending `downgrade` on POST is treated as a Class A program-level field and rejected pre-binding with error code 9011" — **WRONG**.
- §5.4 (PUT): Same inaccurate statement repeated.
- §10.19 table: `downgrade (TierDowngradeConfig) | Rejected — code 9011 (Class A program-level field)` — **WRONG**. Round-trip sentence: "A round-trip of a GET response back to POST/PUT will fail with 9011 unless the `downgrade` key is stripped" — **WRONG** (it will fail with generic 400 if strict-mode is active, or silently succeed if strict-mode is not — see R11-2).

**Impact:** Any UI consumer that routes on `errors[0].code === 9011` to detect the downgrade round-trip case will see a generic 400 (no code field) instead, causing a mis-route or silent pass-through.

**Required fix:** Correct all four occurrences to state: "Sending `downgrade` on POST/PUT is rejected by Jackson strict-mode (generic 400, no error code in the 9011-9018 band). It is NOT caught by the Class A scanner." The round-trip sentence in §10.19 must be corrected to match.

### Other api-handoff.md checks:

- §5.3 error table (9011-9018 band): PASS — the 9011 trigger description correctly lists the 8 CLASS_A_CANONICAL_KEYS members; the parenthetical `(includes the write-narrow downgrade.* rejection)` is the inaccurate addition to be removed.
- §6.7 `TierDowngradeConfig` read-only: PASS — correctly marked as engine-derived, absent on write.
- §10.12 bracket-stripping: PASS — correctly describes that 9011-9018 emit on both `code` field and stripped `message`.
- §10.19 write-narrow/read-wide asymmetry: PASS for the general table structure; FAIL only on the `downgrade` row and round-trip sentence.
- §5.3 `validity.endDate`: PASS — correctly marked as "Never stored. Derived from startDate + periodValue at read time."
- §5.3 `validity.renewal.criteriaType`: PASS — "Must be 'Same as eligibility'" documented; code 9017 on deviation.

---

## Check 5 — Code Quality

### 5.1 — Correctness

All 8 validator methods in `TierEnumValidation.java` are correctly implemented and aligned with their REQ/ADR citations in Javadoc. PASS.

### 5.2 — Error code constants

`TierEnumValidation.java:176-184` declares 8 constants with correct bracket-prefix format:
```java
static final String TIER_CLASS_A_PROGRAM_LEVEL_FIELD = "[9011] ...";
// through
static final String TIER_FIXED_FAMILY_MISSING_PERIOD_VALUE = "[9018] ...";
```
All constants have Javadoc citing REQ-xx/ADR-xR. PASS.

### 5.3 — Javadoc completeness

All 8 public validator methods carry Javadoc with `@throws InvalidInputException` and REQ/ADR citations. TierController `createTier` and `updateTier` have Javadoc explaining rawBody forwarding rationale. PASS.

### 5.4 — Deprecated overloads (F-10c-2)

`TierCreateRequestValidator.validate(TierCreateRequest)` — single-arg form — is annotated `@Deprecated`. Deferred to cleanup ticket per user decision Q2=b. INFO only. No action required in this phase.

### 5.5 — Date comparison (P4 carry-forward)

`TierCreateRequestValidator.validateEndDateNotBeforeStartDate()` (line 115) uses `String.compareTo()` for date ordering. This is safe IFF the wire format guarantees canonical ISO-8601 (`yyyy-MM-ddTHH:mm:ss+00:00`). The wire contract (api-handoff.md §5.3) enforces this format. Risk is LOW. The method is absent from `TierUpdateRequestValidator` (partial-update semantics — no ordering check needed). INFO only.

### 5.6 — No try-catch in controllers

Confirmed: `TierController.java` has no `try-catch` blocks in any `@PostMapping` or `@PutMapping` handler. Exception routing is via `@ExceptionHandler` annotations. PASS.

### 5.7 — rawBody wiring

`TierController.java:97-103`: `objectMapper.treeToValue(rawBody, TierCreateRequest.class)` produces the typed DTO; `rawBody` is forwarded to facade → validator for pre-binding scans. PASS.

`TierController.java:117-122`: Identical pattern for PUT. PASS.

### 5.8 — FIXED family membership

`validateFixedFamilyRequiresPositivePeriodValue` (9018) correctly enumerates 2 FIXED-family members (`FIXED`, `FIXED_CUSTOMER_REGISTRATION`). `FIXED_LAST_UPGRADE` is NOT included — it does not exist as a valid periodType. PASS.

---

## Check 6 — Carry-forward Items

| Item | Description | Status |
|------|-------------|--------|
| **R13 / P11-6a-1** | External consumer residual — staging access-log scan for 9001-9010 usage before cutover | OPEN — pre-deploy gate, not code |
| **P3** | Integration tests (TierControllerIntegrationTest) fail due to Docker unavailability | OPEN — pre-merge gate; requires CI or Docker environment |
| **P4** | `String.compareTo()` date comparison in `validateEndDateNotBeforeStartDate` | INFO — low risk; wire format enforces ISO-8601 |
| **F-10c-4** | ADR-20R fragility — `new ObjectMapper()` does not explicitly set `FAIL_ON_UNKNOWN_PROPERTIES=true` | R11-2 WARNING — see Findings Detail; pre-merge gate |
| **F-10c-2** | Deprecated single-arg overloads in validators | Deferred to cleanup ticket per Q2=b; `@Deprecated` annotation in place |
| **P11-6a-1** | API consumer documentation gap | api-handoff.md updated, but R11-1 correction required |
| **P11-6a-4** | Session memory Q-OP-1 table is stale (superseded by Designer Phase 7) | Documentation drift only — annotate or update Q-OP-1 table |

---

## Findings Detail

### R11-1 (WARNING) — api-handoff.md misattributes `downgrade` rejection to code 9011

**Confidence:** C7 (verified from primary source — code + test).

**Evidence:**
- `TierEnumValidation.java:190-199`: `CLASS_A_CANONICAL_KEYS` = `[isActive, reminders, downgradeConfirmation, renewalConfirmation, retainPoints, dailyDowngradeEnabled, isDowngradeOnReturnEnabled, isDowngradeOnPartnerProgramExpiryEnabled]`. Key `"downgrade"` absent.
- `TierCreateRequestValidatorTest.java:150-155 (BT-197)`: `assertDoesNotThrow(() -> TierEnumValidation.validateNoClassAProgramLevelField(rawBody))` for body `{"programId":1,"name":"Gold","downgrade":{"target":"SINGLE"}}`. Scanner explicitly must NOT fire.
- `api-handoff.md` lines 361, 409, 526, 1494, 1505: Four separate locations claim `downgrade` returns code 9011.

**Impact:** UI consumers who parse `errors[0].code` and branch on 9011 for the "downgrade round-trip" case will receive a generic 400 (or silent pass-through if R11-2 is confirmed) — not 9011.

**Required action (before deploy):** Correct all four api-handoff.md locations. `"downgrade"` is caught by Jackson strict-mode (generic 400 with no code in 9011-9018 band), not by the Class A scanner. Remove the parenthetical from §5.3's 9011 table row: ~~(includes the write-narrow `downgrade.*` rejection)~~.

---

### R11-2 (WARNING) — ADR-20R fragility: ObjectMapper strict-mode not explicitly configured

**Confidence:** C6 (high confidence — code verified; behavior inference from Jackson 2.x spec).

**Evidence:**
- `IntouchApiV3Application.java:94-99`:
  ```java
  @Bean
  public ObjectMapper objectMapper(){
      ObjectMapper objectMapper = new ObjectMapper();
      objectMapper.setTimeZone(TimeZone.getDefault());
      return objectMapper;
  }
  ```
  No `configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true)` call.
- `application.properties`: No `spring.jackson.deserialization.fail-on-unknown-properties=true`.
- Jackson 2.x standard behavior: `new ObjectMapper()` defaults to `FAIL_ON_UNKNOWN_PROPERTIES=false`.
- `TierController.java:97`: `objectMapper.treeToValue(rawBody, TierCreateRequest.class)` uses this bean.
- If `FAIL_ON_UNKNOWN_PROPERTIES=false` (the default), sending `{"downgrade": {...}}` to POST/PUT will be **silently ignored** — the field is dropped without error. ADR-20R's guarantee does not hold.

**Conflicting signal:** 35+ DTOs carry `@JsonIgnoreProperties(ignoreUnknown=true)`. The Designer Phase 7 F1 finding used these opt-outs to infer a strict global. However, the inference is not conclusive: `@JsonIgnoreProperties(ignoreUnknown=true)` is also common on integration-layer DTOs in permissive-global codebases. The annotation is consistent with both hypotheses.

**The test gap:** BT-197 asserts that the Class A scanner does NOT fire for `"downgrade"`. It does NOT verify that `treeToValue()` rejects the key. The unit test uses a standalone `new ObjectMapper()` which also defaults to permissive — so even if someone added an end-to-end assertion, it would test the wrong mapper.

**User decision Q1=c** ("verify via test"): This verification has not been performed. The pre-merge gate is to add a focused UT or IT that:
1. Uses the production `ObjectMapper` bean (injected or replicated with identical config).
2. Calls `objectMapper.treeToValue(rawBodyWithDowngrade, TierCreateRequest.class)`.
3. Asserts that `UnrecognizedPropertyException` (or its wrapper) is thrown.
4. OR — if the ObjectMapper bean is confirmed permissive — the team decides: (a) add `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` to the bean, or (b) add `@JsonIgnoreProperties(ignoreUnknown=false)` to the tier write DTOs, or (c) accept silent-drop behavior and update api-handoff accordingly.

**Risk level:** HIGH. If permissive behavior is the actual runtime behavior, a client round-tripping a GET response to POST will NOT receive a 400 — the `"downgrade"` block will be silently ignored and the ADR-20R write-narrow guarantee is unenforced.

---

### P11-6a-4 — Session-memory Q-OP-1 table is stale

**Confidence:** C7 (direct read of session-memory lines 498-506 and Designer Phase 7 lines 741-748).

The Q-OP-1 table (lines 498-506) predates the Designer Phase 7 LLD and carries a superseded error code allocation. The code matches Designer Phase 7 (final allocation). No runtime impact, but the stale entry could cause confusion in future pipeline phases. Annotate or update.

---

## Recommendation to Orchestrator

```
PHASE:   11 — Reviewer
STATUS:  APPROVED WITH WARNINGS
BRANCH:  raidlc/ai_tier

ARTIFACT:
  /Users/ritwikranjan/Desktop/Artificial Intelligence/kalpavriksha/docs/pipeline/tier/07-reviewer.md

VERDICT: APPROVED WITH WARNINGS

Build: 311+ tier unit tests PASS (Java 17.0.17-amzn, Maven 3.5.4 -B)
       Integration tests: SKIP — Docker unavailable (pre-existing P3 carry-forward)

FINDINGS SUMMARY:

  R11-1 (WARNING):
    api-handoff.md §5.3 / §5.4 / §10.19 incorrectly states that sending
    "downgrade" on POST/PUT returns error code 9011.
    CLASS_A_CANONICAL_KEYS does NOT include "downgrade" (C7 — code + test BT-197).
    Actual mechanism: Jackson strict-mode → generic 400 (no 9011-9018 code).
    Four specific locations in api-handoff.md must be corrected before UI consumers
    act on this document.

  R11-2 (WARNING — F-10c-4):
    ADR-20R fragility not verified. IntouchApiV3Application.java:94-99 declares
    ObjectMapper as new ObjectMapper() with only setTimeZone(). Jackson 2.x default:
    FAIL_ON_UNKNOWN_PROPERTIES=false. No spring.jackson property override found.
    treeToValue() at TierController.java:97 and :117 uses this bean.
    If default applies: "downgrade" and all unclassified unknowns are silently
    dropped, not rejected. ADR-20R guarantee is unverified.
    User decision Q1=c requires a pre-merge test confirming rejection (or explicit
    configure() call added to the ObjectMapper bean).

  INFO P3:
    TierControllerIntegrationTest fails — Docker unavailable.
    Pre-merge gate: CI must run integration tests before merge to main.

  INFO P4:
    String.compareTo() date comparison — low risk (wire contract enforces ISO-8601).

  INFO F-10c-2:
    Deprecated single-arg overloads in place (@Deprecated), deferred to cleanup ticket.

GAP ROUTING:
  R11-1  → Developer: correct api-handoff.md (4 locations identified above)
           before deploy. No code change required.
  R11-2  → Developer + QA: confirm ObjectMapper strictness end-to-end;
           add explicit configure() call OR scoped @JsonIgnoreProperties(ignoreUnknown=false)
           on tier write DTOs; add BT-197b end-to-end treeToValue test.
  P3     → Infrastructure / CI: Docker required for integration test suite.

PRE-MERGE GATES (must close before merge to main):
  [ ] R11-1: api-handoff.md corrected (4 locations)
  [ ] R11-2: ObjectMapper strict-mode verified via test OR explicit configure() added
  [ ] P3:    TierControllerIntegrationTest GREEN in CI (Docker available)

PRE-DEPLOY GATE (R13 / P11-6a-1):
  [ ] Staging access-log scan for existing consumers using codes 9001-9010
  [ ] Soft-launch guard confirmed

QUESTIONS FOR USER (Q11-1):
  R11-2 decision path — which resolution is preferred?
  (a) Add configure(FAIL_ON_UNKNOWN_PROPERTIES, true) to the ObjectMapper bean
      in IntouchApiV3Application.java — applies globally; verify no regressions
      on the 35+ DTOs that carry @JsonIgnoreProperties(ignoreUnknown=true)
  (b) Add @JsonIgnoreProperties(ignoreUnknown=false) to TierCreateRequest and
      TierUpdateRequest only — scoped to tier write DTOs, no global side effects
  (c) Write BT-197b to call treeToValue() end-to-end and assert UnrecognizedPropertyException;
      run it; accept GREEN result as confirmation that strict-mode IS already active
  (d) Accept permissive behavior for "downgrade" (silent drop) and update api-handoff
      to remove the round-trip warning and 9011 attribution
```

---

## Appendix — Build Evidence

```
Environment:
  JAVA_HOME=/Users/ritwikranjan/.sdkman/candidates/java/17.0.17-amzn
  Maven 3.5.4

Command:
  mvn -B test -Dtest="TierCreateRequestValidatorTest,TierUpdateRequestValidatorTest,
      TierEnumValidationTest,TierControllerTest,TierFacadeTest,TierServiceTest,
      TierMapperTest,TierRepositoryTest"

Result:
  311+ tests, all PASS (17 tier test suites)
  BUILD SUCCESS

Integration tests:
  TierControllerIntegrationTest — not run (Docker/Testcontainers unavailable locally)
  UserMergeIntegrationTest — FAIL (Docker/Testcontainers, pre-existing, unrelated to Rework #6a)
```

---

## Phase 11 Closure — 2026-04-23 (same day)

**User decisions (Q11 gate):**
- **R11-1 routing:** `[M] Manual` — docs-only edit of `api-handoff.md` (7 misattribution locations corrected; `downgrade` rejection correctly attributed to Jackson strict-mode, not code 9011).
- **Q11-1 (R11-2) resolution:** `(b+c)` — tier-scoped hardening + empirical regression cover.

### R11-1 — Closed at C7

**What was fixed:** `api-handoff.md` claimed `downgrade` is rejected with code 9011 at 7 documentation locations. This was incorrect — `downgrade` is **not** in `CLASS_A_CANONICAL_KEYS`, so the 9011 pre-binding scanner never targets it. The actual rejection mechanism is Jackson strict-mode (`UnrecognizedPropertyException` → generic HTTP 400).

**Locations corrected** (7 misattributions):

| # | Line | Section | Fix |
|---|------|---------|-----|
| 1 | L361 | §5.3 write-narrow callout | Rewrote to attribute rejection to Jackson strict-mode + explained nested-Class-A-key 9011 nuance |
| 2 | L389 | §5.3 evidence footer | Enumerated the 8 actual Class A keys; explicitly noted `downgrade` is NOT in that set |
| 3 | L409 | §5.3 field-validation table | Split into 2 rows: bare `downgrade` key (Jackson 400) vs nested Class A keys (9011) |
| 4 | L527 | §5.3 9011–9018 scanner table | Added clarifying note distinguishing bare `downgrade` from nested Class A keys |
| 5 | L570 | §5.4 PUT body narrative | Corrected PUT-parity narrative to match the Jackson-strict mechanism |
| 6 | L1205 | §6.7 `TierDowngradeConfig` | Clarified the two-layer rejection model (Jackson strict + recursive 9011 scan) |
| 7 | L1495 | §10.19 asymmetry table | Corrected the `downgrade` row to state Jackson strict-mode generic 400 |
| 8 | L1506 | §10.19 round-trip warning | Fixed round-trip guidance — Jackson 400, not 9011 |

**Correctly-attributed references preserved** (not edited):
- L547 — JSON error body example with `dailyDowngradeEnabled` triggering 9011 (accurate — Class A orchestration flag, not bare `downgrade`)
- L1441 — bracket-prefix extraction example (correct)
- L1499 — Class A program-level keys row (correct — those keys DO trigger 9011)

**Evidence:**
- `TierEnumValidation.java:190–199` — `CLASS_A_CANONICAL_KEYS` contains 8 keys, none being `downgrade`
- `TierCreateRequestValidatorTest.java:140` — BT-197 test name + comment explicitly documents the correct behaviour: *"'downgrade' is NOT a Class A field — Jackson catches it via FAIL_ON_UNKNOWN_PROPERTIES"*

### R11-2 — Closed at C7 via (b+c) implementation

**(b) Tier-scoped annotation added:**

| File | Change |
|------|--------|
| `TierCreateRequest.java` | Added `import com.fasterxml.jackson.annotation.JsonIgnoreProperties;` + type-level `@JsonIgnoreProperties(ignoreUnknown = false)`. Javadoc expanded to document the Phase 11 R11-2 (b+c) rationale — tier-scoped, immune to Spring Boot global property flips. |
| `TierUpdateRequest.java` | Same annotation + same Javadoc extension. |

**Why local-not-global:** Option (a) would have hardened the global ObjectMapper bean — maximum blast radius across every DTO in intouch-api-v3. Option (b) scopes the guarantee to the tier write contract only. Spring Boot's `spring.jackson.deserialization.fail-on-unknown-properties` global flag cannot override a type-level `@JsonIgnoreProperties` annotation. ADR-20R + ADR-21R (write-narrow asymmetry) now survive any future property-level environment change.

**(c) Empirical regression cover added** — 4 new tests (BT-197b suite):

| Test ID | File | Test Method | Assertion |
|---------|------|-------------|-----------|
| BT-197b (POST) | `TierCreateRequestValidatorTest.java` | `shouldRejectLegacyDowngradeBlockAtJacksonBindingLayer` | `objectMapper.treeToValue({"programId":1,"name":"Gold","downgrade":{...}}, TierCreateRequest.class)` → `UnrecognizedPropertyException` with `propertyName = "downgrade"` |
| BT-197b-control (POST) | `TierCreateRequestValidatorTest.java` | `shouldAcceptKnownFieldsAtJacksonBindingLayer` | Well-formed payload binds without error (happy-path negative control) |
| BT-197b (PUT) | `TierUpdateRequestValidatorTest.java` | `shouldRejectLegacyDowngradeBlockAtJacksonBindingLayerOnPut` | Same assertion for PUT partial-update DTO |
| BT-197b-control (PUT) | `TierUpdateRequestValidatorTest.java` | `shouldAcceptKnownFieldsAtJacksonBindingLayerOnPut` | Partial PUT binds without error |

**Key design property:** BT-197b targets the **Jackson binding layer**, not the validator layer. BT-197 (pre-existing) asserts that the 9011 scanner does NOT claim ownership of `downgrade` (negative control for the scanner). BT-197b asserts what DOES reject it (the annotation). Together they pin the contract from both sides.

**Additional assertion (`ex.getPropertyName() == "downgrade"`)**: guards against the test passing for the wrong reason (e.g., an unrelated unknown key in the fixture).

### Verification Evidence (C7)

```
Test command:
  JAVA_HOME=~/.sdkman/candidates/java/17.0.17-amzn mvn test \
    -f intouch-api-v3/pom.xml \
    -Dtest='TierCreateRequestValidatorTest,TierUpdateRequestValidatorTest'

Result:
  TierCreateRequestValidatorTest — 30 tests, 0 failures, 0 errors, 0 skipped (was 28, +2 BT-197b)
  TierUpdateRequestValidatorTest —  7 tests, 0 failures, 0 errors, 0 skipped (was 5, +2 BT-197b)
  Total: 37 tests PASS
  BUILD SUCCESS

Full tier-package regression sweep:
  mvn test -Dtest='com.capillary.intouchapiv3.tier.**'
  Tests run: 354, Failures: 0, Errors: 0, Skipped: 0
  BUILD SUCCESS
  → no regression from the @JsonIgnoreProperties annotation
```

**Result:** R11-1 + R11-2 both CLOSED at C7.

### Phase 11 Final Verdict — **APPROVED**

Upgraded from "APPROVED WITH WARNINGS" to **APPROVED** after both warnings closed.

**Remaining pre-merge CI gates** (tracked, not Phase 11 blockers):
- P3 / W1: `TierControllerIntegrationTest` must GREEN in Docker-capable CI
- P4 / W2: Date-format consistency on read path
- P5 / I1: Scanner performance guard (INFO — post-merge acceptable)

**Remaining pre-deploy gate:**
- R13 / P11-6a-1: Staging access-log scan for legacy codes 9001–9010 consumers

---

*Reviewer: claude-sonnet-4-6 | Phase 11 | 2026-04-23*
*Closure: orchestrator + developer | 2026-04-23 (same day) | Rework #6a Cycle 1 CLOSED*
