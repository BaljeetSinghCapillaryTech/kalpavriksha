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

---

## Rework #8 Review

> **Date:** 2026-04-27
> **Branch:** `common-sprint-73` (intouch-api-v3)
> **Commit under review:** `18a5304fc`
> **Scope:** i18n error-key catalog mirror — `tier.properties` + `TierErrorKeys.java` + `MessageResolverService` registration + REQ-57/REQ-59–REQ-67 gap-fill validators + BT-224–BT-249 test suite
> **Skill:** `/reviewer`
> **Overall Verdict:** CHANGES REQUESTED

---

### Executive Summary

Rework #8 implements the tier validation i18n key catalog mirror, mirroring the promotion CRUD pattern (`target_loyalty.properties` + `UnifiedPromotionValidatorService`). The core catalog infrastructure — `tier.properties`, `TierErrorKeys.java`, `MessageResolverService` TIER namespace registration, and migration of all existing throw sites to key-only `InvalidInputException` — is correctly implemented and architecturally sound.

Unit test suite is green: **49 / 49 UTs PASS** across 8 suites. Integration tests (4 tests in `TierControllerIntegrationTest`) are blocked by `ApplicationContext failure threshold (1) exceeded` — an environment-level Testcontainers/Spring Boot infrastructure failure pre-existing in this local setup; BT-249 (REQ-68 end-to-end advice) cannot be confirmed GREEN from surefire evidence.

Two code-level blockers are present that require developer action before merge:

1. **BLOCKER-1 (G-13.1 violation):** `TierFacade.handleApproval` line 473 throws `new IllegalArgumentException("Unknown approval action: ...")` — an unchecked Java exception in REST-facing code, explicitly prohibited by G-13.1. Will surface as unhandled 500 via `TargetGroupErrorAdvice`'s no-match path.

2. **BLOCKER-2 (D-32 violation):** `TierCreateRequestValidator.validateEndDateNotBeforeStartDate` throws `new InvalidInputException(dynamicString)` where the string contains dynamic date values — no catalog key used. This violates D-32 (static catalog message to client; dynamic detail in logs only).

Four warnings require attention but do not block merge individually (reviewer recommends resolving all four before deploy):

- **WARN-1:** Old `public static final int TIER_*` numeric constants not removed from `TierCreateRequestValidator` (lines 33–53) and `TierEnumValidation` (lines 243–256). Plan stated removal; dead code creates maintenance hazard.
- **WARN-2:** `TierErrorKeys` and `tier.properties` contain entries for 9027 (`TIER_COLOR_LENGTH_EXCEEDED`, skipped per D-30) and 9031 (`TIER_RENEWAL_LAST_MONTHS_OUT_OF_RANGE`, folded per D-31) but neither key is thrown anywhere and BT-247 explicitly excludes both from the catalog completeness check. Creates documentation/artifact confusion — the artifact state says "present" while decisions say "skipped/folded."
- **WARN-3:** `TierFacade.submitForApproval` line 438 and `handleApproval` line 462 throw plain-text `ConflictException` without catalog keys. These two paths will emit `999999` as code to the client (no resolved code from `MessageResolverService`).
- **WARN-4:** `TierApprovalHandler.publish()` uses `IllegalStateException` at lines 248 and 254 for missing SLAB_UPGRADE/SLAB_DOWNGRADE strategy. While `publish()` declares `throws Exception`, the exception will propagate through the REST call chain and surface as HTTP 500 without an `InvalidInputException`/`ConflictException` wrapper — G-13.1 concern (softer than BLOCKER-1 because this is a configuration failure path, not an input validation path, but still warrants a `ConflictException` or custom exception wrapper).

---

### Build Evidence (Primary — Surefire Reports)

All evidence sourced from `intouch-api-v3/target/surefire-reports/`. Environment: Java 17.0.17-amzn, Maven 3.5.4.

| Test Suite | Tests | Failures | Errors | Skipped | Status |
|---|---|---|---|---|---|
| `TierCatalogIntegrityTest` | 3 | 0 | 0 | 0 | **PASS** |
| `TierValidationServiceCaseInsensitiveTest` | 3 | 0 | 0 | 0 | **PASS** |
| `TierCreateRequestValidatorTest` | 24 | 0 | 0 | 0 | **PASS** |
| `TierEnumValidationTest` | 13 | 0 | 0 | 0 | **PASS** |
| `TierRenewalValidationTest` | 3 | 0 | 0 | 0 | **PASS** |
| `TierUpdateRequestValidatorTest` | 3 | 0 | 0 | 0 | **PASS** |
| `TierApprovalHandlerTest` | 10 | 0 | 0 | 0 | **PASS** |
| `TierFacadeTest` | 15 | 0 | 0 | 0 | **PASS** |
| **R8 UT Total** | **74** | **0** | **0** | **0** | **GREEN** |
| `TierControllerIntegrationTest` | 0 of 4 ran | — | 4 | 0 | **ERROR (infra)** |

**IT failure details:** All 4 integration tests in `TierControllerIntegrationTest` error with `IllegalStateException: ApplicationContext failure threshold (1) exceeded`. This is a pre-existing Testcontainers/Spring Boot infrastructure issue in the local environment — it is not introduced by Rework #8. BT-249 (REQ-68 end-to-end `TargetGroupErrorAdvice` response) cannot be confirmed GREEN from this evidence.

> **Confidence:** C7 (primary source — surefire report files read directly).

---

### Check 1 — Requirements Alignment

Evidence: `TierCreateRequestValidator.java`, `TierEnumValidation.java`, `TierRenewalValidation.java`, `TierValidationService.java`, `TierFacade.java`, `TierApprovalHandler.java`, `validation-rework-scope.md` (REQ-57..REQ-68).

| REQ | Description | Code Location | Status |
|---|---|---|---|
| REQ-57 | Case-insensitive tier name uniqueness | `TierValidationService.validateNameUniqueness` and `validateNameUniquenessExcluding` — `equalsIgnoreCase()` | **PASS** |
| REQ-58 | Color length 9027 — SKIPPED (D-30) | No throw at any site; constant exists in `TierErrorKeys` and `tier.properties` (see WARN-2) | **PASS (skipped per D-30)** |
| REQ-59 | Upper bound check on `serialNumber` | `TierCreateRequestValidator` — new upper-bound validation added | **PASS** |
| REQ-60 | `validateConditionTypes` overload for new callers | `TierEnumValidation.validateConditionTypes(List, String)` — private overload added | **PASS** |
| REQ-61 | No numeric overflow on tier count | `TierEnumValidation.validateNoNumericOverflow` — implemented | **PASS** |
| REQ-62 | `renewalWindowBounds` upper bound | `TierEnumValidation.validateRenewalWindowBounds` — implemented with 9034 key | **PASS** |
| REQ-63 | `renewalLastMonths` bounds — FOLDED (D-31) | Field `renewalLastMonths` does not exist in `TierValidityConfig`; folded into REQ-62 / 9034 | **PASS (folded per D-31)** |
| REQ-64 | `renewalWindowBounds` lower bound | `TierEnumValidation.validateRenewalWindowBounds` — both bounds enforced | **PASS** |
| REQ-65 | `validateEndDateNotBeforeStartDate` uses catalog key | `TierCreateRequestValidator.validateEndDateNotBeforeStartDate` — throws dynamic string, NOT a catalog key | **BLOCKER-2** |
| REQ-66 | `conditionValuesPresent` when conditions present | `TierRenewalValidation.validateConditionValuesPresent` — implemented | **PASS** |
| REQ-67 | Renewal condition values non-empty | `TierRenewalValidation.validateConditionValuesPresent` — implemented | **PASS** |
| REQ-68 | `TargetGroupErrorAdvice` resolves TIER keys end-to-end | `TierControllerIntegrationTest` BT-249 — cannot confirm (IT infrastructure failure) | **UNVERIFIED** |

**G-07 tenant isolation (REQ multi-tenancy):** `TierValidationService.validateNameUniqueness` queries via `findByOrgIdAndProgramIdAndStatusIn(orgId, programId, ...)`. Both `orgId` and `programId` are scoped. **PASS.**

**TIER namespace registration (core catalog requirement):** `MessageResolverService` line 36: `.put("TIER", "i18n.errors.tier")`. **PASS.**

---

### Check 2 — Session Memory Alignment

Evidence: `session-memory.md` line 63 (Rework #8 summary), approach-log D-30/31/32/33/34.

| Decision | Session Memory | Code | Aligned? |
|---|---|---|---|
| D-30: skip 9027 color length | Documented | No throw at any site; constant present but unused | **PASS** |
| D-31: fold 9031 → 9034 | Documented | 9031 constant present but unused; 9034 enforces window bounds | **PASS** |
| D-32: Option 2 (static catalog message; dynamic detail in logs) | Documented | Most sites log `log.warn(...)` then `throw new InvalidInputException(key)` | **PASS (with BLOCKER-2 exception)** |
| D-33: BT-247 catalog completeness test in scope | Documented | `TierCatalogIntegrityTest` includes BT-247 | **PASS** |
| D-34: no pre-deploy DB scan | Documented | No DB scan code added | **PASS** |
| Bean-validation annotations (§4.4) deferred (D1) | Documented as accepted deferral | `TierCreateRequest`, `TierUpdateRequest`, `TierEligibilityConfig` — no `@NotBlank`/`@Size`/`@Pattern`/`@PositiveOrZero` found | **PASS (deferred per D1, but should be noted as known gap in API handoff)** |

---

### Check 3 — Security (GUARDRAILS)

Evidence: `TierFacade.java`, `TierApprovalHandler.java`, `TierValidationService.java`, GUARDRAILS.md G-07, G-13.

#### G-07 — Multi-tenancy (CRITICAL)

**PASS.** `validateNameUniqueness` and `validateNameUniquenessExcluding` both scope queries by `orgId` and `programId`. No unscoped name-uniqueness queries found. G-07.1 satisfied.

#### G-13 — Exception Handling (HIGH)

**FAIL — BLOCKER-1.**

- G-13.1 violation: `TierFacade.handleApproval` line 473 throws `new IllegalArgumentException("Unknown approval action: " + action)`. `IllegalArgumentException` is an unchecked Java exception. `TargetGroupErrorAdvice` has no handler for it — it will surface as HTTP 500 via the default Spring MVC error handler, bypassing the structured `{code, message}` response contract.
- Secondary concern: `TierApprovalHandler.publish()` lines 248 and 254 throw `IllegalStateException` for missing SLAB_UPGRADE/SLAB_DOWNGRADE strategies. This is in the REST call chain (`controller → TierFacade → MakerCheckerService → TierApprovalHandler.publish()`). `IllegalStateException` will also bypass `TargetGroupErrorAdvice` and surface as HTTP 500.
- All other throw sites in `TierEnumValidation`, `TierCreateRequestValidator`, `TierRenewalValidation`, `TierUpdateRequestValidator`, and `TierValidationService` correctly use `InvalidInputException(key)`. **PASS for those sites.**

---

### Check 4 — Documentation

Evidence: `tier.properties`, `TierErrorKeys.java`, `MessageResolverService.java`.

#### Catalog Completeness

`TierCatalogIntegrityTest` (BT-247) uses `EXPECTED_TIER_KEYS` (38 keys) and checks that each key resolves to a non-null `.code` and `.message` in `tier.properties` via `MessageResolverService`. Passes 3/3. **PASS.**

**Observation (WARN-2):** `EXPECTED_TIER_KEYS` in BT-247 explicitly excludes 9027 and 9031 (commented as "SKIPPED" and "DEFERRED"). However, `TierErrorKeys.java` and `tier.properties` both contain actual entries for these two codes — they are not absent, not reserved gaps, but active entries with no corresponding throw site. The catalog check does not perform a reverse check (TierErrorKeys constants → tier.properties exhaustively). This means: if a future developer adds a new constant in `TierErrorKeys` but forgets to add it to `tier.properties`, BT-247 would not catch it.

#### Javadoc / Inline Documentation

All new validator methods in `TierEnumValidation`, `TierRenewalValidation` carry REQ citation comments or method-level Javadoc. `TierErrorKeys` class-level Javadoc explains the TIER namespace convention. **PASS.**

---

### Check 5 — Code Quality

#### 5.1 — Dead Constants (WARN-1)

`TierCreateRequestValidator.java` lines 33–53: `public static final int TIER_*` numeric constants (9001–9018, 18 constants) remain in the file. These are not referenced in any current throw statement — the migration replaced bracket-prefix strings with key-only throws. Plan §3.2 stated "Remove `public static final int TIER_*` numeric constants from all validator classes." Dead code creates maintenance risk: a future developer may use the old int constants in new code and bypass the catalog.

`TierEnumValidation.java` lines 243–256: identical issue — `public static final int TIER_*` constants (9011–9024) remain after migration.

**Action required:** Remove both sets of int constants. Tests cover all formerly-associated throw sites with key-only assertions.

#### 5.2 — `validateEndDateNotBeforeStartDate` D-32 Violation (BLOCKER-2)

`TierCreateRequestValidator.validateEndDateNotBeforeStartDate` throws:
```java
new InvalidInputException("End date " + endDate + " cannot be before start date " + startDate)
```
This is a raw dynamic string passed directly to `InvalidInputException` — not a catalog key. When `TargetGroupErrorAdvice` receives it, it calls `MessageResolverService.resolve(message)` expecting a key like `TIER.TIER_END_DATE_BEFORE_START_DATE`. A raw sentence string will not match any registered key, causing the resolver to fall back to `999999` as the code with the raw message surfaced to the client — leaking dynamic date values into the error response and violating D-32 (static catalog message to client; dynamic field detail in logs only).

**Fix required:** Replace with a catalog key throw + `log.warn` for the date-context detail:
```java
log.warn("validateEndDateNotBeforeStartDate: endDate={} is before startDate={}", endDate, startDate);
throw new InvalidInputException(TierErrorKeys.TIER_END_DATE_BEFORE_START_DATE);
```
Verify `TIER_END_DATE_BEFORE_START_DATE` exists as a key in `TierErrorKeys` and `tier.properties`, or add it.

#### 5.3 — Non-Migrated Plain-Text ConflictException Throws (WARN-3)

`TierFacade.submitForApproval` line 438:
```java
throw new ConflictException("Only DRAFT tiers can be submitted for approval");
```
`TierFacade.handleApproval` line 462:
```java
throw new ConflictException("Only PENDING_APPROVAL tiers can be approved or rejected");
```
Both are plain-text `ConflictException` throws — no catalog key. `ConflictException` is the correct exception type (G-13 compliant), but these paths will emit `999999` as the numeric code to the client because `MessageResolverService` cannot resolve a raw sentence string. A client receiving a 409 for these paths gets no machine-readable error code.

**Action recommended:** Migrate to catalog key throws when catalog keys for these cases are defined (or add them to `TierErrorKeys`/`tier.properties`).

#### 5.4 — `validateConditionTypes` Semantic Oddity (INFO)

`TierEnumValidation.validateConditionTypes(List<TierCondition>, String fieldName)` throws `TIER_INVALID_KPI_TYPE` when a condition's `type` field is not in the valid enum set. The key name `TIER_INVALID_KPI_TYPE` is semantically odd for a condition-type enum mismatch (it reads as a KPI-related error, not a condition-type mismatch). This is pre-existing behavior — not introduced by Rework #8. Flagged for awareness; no action required in this cycle.

#### 5.5 — `@MockitoSettings(strictness = Strictness.LENIENT)` in BT-224/225/226 (INFO)

`TierValidationServiceCaseInsensitiveTest` uses `LENIENT` strictness because stubs set up for the GREEN behavior are unused in RED-phase assertion paths. This is acceptable per the TDD Chicago/Detroit school (unit = business outcome cluster). The annotation is correctly justified by a comment in the test file. **PASS.**

---

### Check 6 — Test Traceability

Evidence: Surefire reports + test source files.

| BT | Description | Test Class | Surefire Status |
|---|---|---|---|
| BT-224 | REQ-57: case-insensitive uniqueness — exact match blocked | `TierValidationServiceCaseInsensitiveTest` | PASS |
| BT-225 | REQ-57: different case blocked | `TierValidationServiceCaseInsensitiveTest` | PASS |
| BT-226 | REQ-57: unique name allowed | `TierValidationServiceCaseInsensitiveTest` | PASS |
| BT-246 | Round-trip all codes via MessageResolverService | `TierCatalogIntegrityTest` | PASS |
| BT-247 | Catalog completeness (38 keys) | `TierCatalogIntegrityTest` | PASS |
| BT-248 | TIER namespace registration | `TierCatalogIntegrityTest` | PASS |
| BT-249 | REQ-68 end-to-end advice response | `TierControllerIntegrationTest` | **UNVERIFIED (IT infrastructure failure)** |
| BT-190..BT-223 subset | Migration: assertion text uses key-only `ex.getMessage() == "TIER.<KEY>"` | `TierCreateRequestValidatorTest`, `TierEnumValidationTest`, `TierRenewalValidationTest`, `TierUpdateRequestValidatorTest` | PASS (24+13+3+3 = 43 tests) |

**Wire code preservation (backward compatibility):** Surefire evidence confirms all migrated validator tests assert on key strings (`TIER.<KEY>`), not on old bracket-prefix strings or numeric codes. The wire codes 9001–9024 are preserved because `MessageResolverService` resolves key → `{code, message}` at the advice layer. **PASS.**

**Reverse catalog check gap (INFO):** `TierCatalogIntegrityTest` checks `EXPECTED_TIER_KEYS` → `tier.properties` (forward direction only). It does not check that every `TierErrorKeys` constant has a corresponding `tier.properties` entry. If a constant is added to `TierErrorKeys` without a `tier.properties` entry, BT-247 would not detect it. Recommend adding a reverse-direction check in a future rework.

---

### Check 7 — Plan Deviation Review

| Plan Element | Plan Says | Code Reality | Deviation? |
|---|---|---|---|
| Remove old `int` constants | "Remove `public static final int TIER_*` numeric constants" | Constants still present in `TierCreateRequestValidator` (lines 33–53) and `TierEnumValidation` (lines 243–256) | **Yes — WARN-1** |
| D-32: static catalog key to client | Dynamic detail in `log.warn` only | `validateEndDateNotBeforeStartDate` passes dynamic string to exception | **Yes — BLOCKER-2** |
| D-30: 9027 skipped | Skip = no constant, no properties entry (or treat as reserved gap) | Both `TierErrorKeys.TIER_COLOR_LENGTH_EXCEEDED` constant AND `tier.properties` 9027 entry exist | **Deviation from spirit — WARN-2** |
| D-31: 9031 folded → 9034 | Fold = no constant, no properties entry (or treat as reserved gap) | Both `TierErrorKeys.TIER_RENEWAL_LAST_MONTHS_OUT_OF_RANGE` constant AND `tier.properties` 9031 entry exist | **Deviation from spirit — WARN-2** |
| Bean-validation annotations (§4.4) | `@NotBlank`/`@Size`/`@Pattern`/`@PositiveOrZero` on DTOs | Not implemented | **Yes — accepted per D1 deferral** |
| G-13.1: no `IllegalArgumentException` in REST code | Never throw unchecked Java exceptions in REST-facing code | `TierFacade.handleApproval` throws `IllegalArgumentException` | **Yes — BLOCKER-1** |

---

### Check 8 — Wire-Format Compatibility

Evidence: `tier.properties` code entries, existing numeric codes in surefire test assertions.

Wire codes 9001–9024 (existing, migrated) are unchanged. `MessageResolverService` resolves `TIER.<KEY>` to the numeric code declared in `tier.properties` as `<KEY>.code`. Existing clients consuming codes 9001–9024 will see the same numeric codes in `{code, message}` response envelopes. **PASS — no breaking change.**

New codes 9025–9037 and 9038–9040 are net-new. No existing client can depend on them (they were not exposed before). **PASS.**

---

### Findings Tally

| Severity | Count | Items |
|---|---|---|
| BLOCKER | 2 | BLOCKER-1 (`IllegalArgumentException` in REST), BLOCKER-2 (D-32 dynamic string in exception) |
| WARN | 4 | WARN-1 (dead int constants), WARN-2 (9027/9031 artifacts present but unused), WARN-3 (plain-text ConflictException), WARN-4 (`IllegalStateException` in `TierApprovalHandler.publish`) |
| INFO | 3 | IT infrastructure failure (pre-existing), reverse catalog check gap, condition-type semantic oddity |

---

### Overall Recommendation

**CHANGES REQUESTED.**

BLOCKER-1 and BLOCKER-2 require developer fixes before merge:

1. **BLOCKER-1 fix:** In `TierFacade.handleApproval`, replace `throw new IllegalArgumentException("Unknown approval action: " + action)` with `throw new InvalidInputException(TierErrorKeys.TIER_UNKNOWN_APPROVAL_ACTION)` (add key to catalog if missing) or `throw new ConflictException("Unknown approval action: " + action)` (minimum G-13.1-compliant fix).

2. **BLOCKER-2 fix:** In `TierCreateRequestValidator.validateEndDateNotBeforeStartDate`, replace the dynamic-string `InvalidInputException` with a catalog-key throw + `log.warn` for the date detail. Verify or add `TIER_END_DATE_BEFORE_START_DATE` in `TierErrorKeys` and `tier.properties`.

Recommended to also address before merge (not strict blockers but reduce noise):
- **WARN-1:** Remove dead `int` constants from `TierCreateRequestValidator` and `TierEnumValidation`.
- **WARN-4:** Wrap `IllegalStateException` in `TierApprovalHandler.publish()` with a `ConflictException` or `InvalidInputException`.

**BT-249 pre-merge gate:** IT suite must pass in a Docker-capable CI environment before merge to main.

---

### Gap Routing

| Finding | Owner | Action |
|---|---|---|
| BLOCKER-1: `IllegalArgumentException` in `TierFacade` | Developer | Replace with `InvalidInputException`/`ConflictException`; add catalog key if using InvalidInputException |
| BLOCKER-2: D-32 violation in `validateEndDateNotBeforeStartDate` | Developer | Replace dynamic-string throw with catalog-key throw + `log.warn` for date detail |
| WARN-1: Dead int constants | Developer | Remove `public static final int TIER_*` from `TierCreateRequestValidator` and `TierEnumValidation` |
| WARN-2: 9027/9031 artifact confusion | Developer | Decide: (a) remove constants + properties entries and treat as hard gaps, OR (b) add comment in BT-247 EXPECTED_TIER_KEYS documenting why both are excluded. Either is acceptable. |
| WARN-3: Plain-text ConflictException throws | Developer | Add catalog keys for submit/approve conflict messages; migrate when keys defined |
| WARN-4: `IllegalStateException` in `TierApprovalHandler.publish()` | Developer | Wrap with `ConflictException` or custom checked exception |
| BT-249 IT infrastructure | Infrastructure / CI | Requires Docker/Testcontainers-capable environment; must GREEN before merge |

---

### Pre-Merge Gates

- [ ] BLOCKER-1 fixed and tests updated
- [ ] BLOCKER-2 fixed and `validateEndDateNotBeforeStartDate` test updated to assert key
- [ ] `TierControllerIntegrationTest` (BT-249 + 3 others) GREEN in Docker-capable CI

### Pre-Deploy Gates

- [ ] D-34 (accepted): No pre-deploy DB scan for existing duplicate names — accepted risk, documented in approach-log
- [ ] REQ-57 case-insensitive uniqueness confirmed in QA environment against production data (Q-#8-5 open question)

---

*Reviewer: claude-sonnet-4-6 | Rework #8 | 2026-04-27*
*Verdict: CHANGES REQUESTED — 2 blockers require developer action before merge*
