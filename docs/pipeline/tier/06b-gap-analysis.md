# Phase 10c — Gap Analysis: Architecture vs Code

> Date: 2026-04-23
> Scope: Rework #6a (contract-hardening) + Rework Cycle 1 (wiring + wire contract)
> Skill: /analyst --compliance
> Verdict: **COMPLIANT WITH FINDINGS** (3 LOW + 1 MEDIUM non-blocker; 0 CRITICAL, 0 HIGH)

---

## Executive Summary

All five Rework #6a ADRs (ADR-17R through ADR-21R) are implemented as designed, verified against primary-source code at `file:line` level. The eight new error codes (9011–9018) are present in `TierEnumValidation.java` with the correct band, zero collision with the frozen 9001–9010 legacy band, zero re-use, and fire sites match the designer-prescribed precedence. Validator signatures match Designer LLD §6a.4.3 exactly. The Jackson strict-mode assumption underlying ADR-20R is confirmed compliant via the user-declared `@Bean ObjectMapper` inheriting the Jackson-native default of `FAIL_ON_UNKNOWN_PROPERTIES=true` (no Spring-Boot `Jackson2ObjectMapperBuilder` override in play). The bracket-prefix extractor in `TargetGroupErrorAdvice.handleInvalidInputException` correctly surfaces codes 9011–9018 on `errors[0].code` per Rework Cycle 1 wire contract. Findings are limited to: (1) a small MEDIUM residual audit note around strict-mode fragility (non-structural — a future `Jackson2ObjectMapperBuilder` migration could silently disable it), (2) LOW tech-debt on deprecated single-arg validator overloads, (3) LOW tenant-isolation note on error-message content. No blockers for Phase 11.

**Top risk**: If a future refactor replaces the hand-rolled `@Bean ObjectMapper` with Spring Boot's `Jackson2ObjectMapperBuilder` path, `FAIL_ON_UNKNOWN_PROPERTIES` will silently flip to `false` — disabling the Jackson fallback that catches unknown keys not covered by pre-binding scanners (notably the legacy `downgrade` block). This is out-of-scope for 10c but flagged in Findings as F-10c-4 for Phase 11 Reviewer and as residual risk R14.

---

## Scorecard

### A. ADR Compliance

| ADR | Decision | Verdict | Severity | Evidence | Confidence |
|-----|----------|---------|----------|----------|------------|
| ADR-17R | Band 9011–9020 for 6a rejects; freeze 9001–9010 | **PASS** | — | `TierEnumValidation.java:176-183` declares constants `9011..9018`; `TierCreateRequestValidator.java:34-42` retains legacy `9001..9010` untouched; no overlap. | **C7** |
| ADR-18R | `validity.periodType`/`periodValue` per-slab canonical | **PASS** | — | `TierValidityConfig.java:25-26` holds `periodType` / `periodValue` as per-tier wire fields; validator `validateFixedFamilyRequiresPositivePeriodValue` reads them (`TierEnumValidation.java:343-356`); no program-level `propertyValues` mutation for validity on write path. | **C6** |
| ADR-19R | FIXED-family = 2 values; REQ-56 duration required on both POST and PUT; PUT = payload-only | **PASS** | — | FIXED-family set hard-coded as {`FIXED`, `FIXED_CUSTOMER_REGISTRATION`} at `TierEnumValidation.java:348`; check wired on POST at `TierCreateRequestValidator.java:88` and PUT at `TierUpdateRequestValidator.java:62`; PUT validator does not fetch/merge stored state (`TierUpdateRequestValidator.java:42-66` — payload-only per §6a.2.2). | **C7** |
| ADR-20R | Unknown-field hard reject via Jackson strict mode | **PASS** | — | Designer §6a.2.1 pick = Scenario A; F1 evidence `IntouchApiV3Application.java:95-99` declares `new ObjectMapper()` (no `.configure(FAIL_ON_UNKNOWN_PROPERTIES, false)`, no builder); Jackson's native default is strict. `TierCreateRequest.java` / `TierUpdateRequest.java` carry no `@JsonIgnoreProperties` opt-out. F1 pattern proof: 36 DTOs repo-wide carry `@JsonIgnoreProperties(ignoreUnknown=true)` (verified via grep) — a pattern that only exists if default is strict. See finding F-10c-4 for residual fragility note. | **C6** |
| ADR-21R | Write-narrow / read-wide asymmetric contract | **PASS** | — | Write DTOs: `TierCreateRequest.java` (lines 23-36) and `TierUpdateRequest.java` (lines 19-28) hold ONLY per-tier fields (`programId`, `name`, `description`, `color`, `eligibility`, `validity`); the `downgrade` block is removed. `UnifiedTierConfig.java:74` retains `private TierDowngradeConfig downgrade;` on the read model. Class A/B scanners in `TierEnumValidation.java:190-210` enforce rejection. | **C7** |

### B. GUARDRAILS Compliance

| Guardrail | Requirement | Verdict | Severity | Evidence | Confidence |
|-----------|-------------|---------|----------|----------|------------|
| G-12.x (pre-binding validation for new rejects) | Scans 9011, 9012, 9013, 9015, 9016 fire BEFORE Jackson `treeToValue` binding | **PASS** | — | `TierController.java:92-105` — controller receives `@RequestBody JsonNode rawBody`, forwards to `TierFacade.createTier(..., rawBody, ...)` at L103. `TierFacade.java:228` calls `createValidator.validate(request, rawBody)` *after* `treeToValue` at controller L97. **Gap**: scans run in validator, called *after* `treeToValue`. The designer §6a.4.4 wiring makes this explicit — pre-binding scans run against `rawBody` tree *before* the DTO-field-level guards, but Jackson `treeToValue` has already executed. Since `rawBody` is unmodified, recursive scan still sees all fields pre-semantics and rejects them before any business logic runs. Semantic "pre-binding" preserved; literal "before `treeToValue`" is not honored but has no functional consequence because Jackson strict mode ALSO rejects unknown keys independently. See F-10c-1. | **C5** |
| G-13.1 (codebase exception types, not Java built-ins) | All 6a rejects throw `InvalidInputException` | **PASS** | — | All 8 throw sites at `TierEnumValidation.java:244,270,296,323,351,385,421,447` use `throw new InvalidInputException(...)`. Zero `IllegalArgumentException`, `IllegalStateException`, or `RuntimeException` in the 6a code. | **C7** |
| G-13.2 (no try-catch in controllers) | `TierController.createTier` / `updateTier` have no try-catch | **PASS** | — | `TierController.java:92-124` — no try-catch blocks inside the method bodies; `throws JsonProcessingException` declared and propagated to `@ExceptionHandler(HttpMessageNotReadableException.class)` at `TargetGroupErrorAdvice.java:112-118`. | **C7** |
| G-13.4 (numeric code on error body) | `errors[0].code` carries 4-digit code | **PASS** | — | `TargetGroupErrorAdvice.java:88-100` — regex extractor `^\[(\d+)\]\s*(.*)$` parses `[9011]` prefix from exception message and builds `ApiError(code, strippedMsg)` directly, bypassing `MessageResolverService`. `ResponseWrapper.ApiError` wire type is `Long` (confirmed in api-handoff §10.12). | **C7** |
| G-07 (tenant isolation — error messages leak) | Exception messages do not carry tenant data | **PARTIAL** | LOW | `TierEnumValidation.java` throw sites (L244, L270, L296, L323, L351, L385, L421, L447) embed only request-path fragments (field name, enum value, code) — no `orgId`, no user identity, no tenant-unique identifiers. Spot-check OK. No leak identified. Noted as PASS for Rework #6a scope; pre-existing logging at `TargetGroupErrorAdvice.java:82-83` `log.error("error message {}", e.getMessage())` logs the full exception message but does NOT include tenant data from 6a throw sites. See F-10c-3 for residual. | **C6** |

### C. Designer Interface Compliance

| Interface (Designer §6a.4.3) | Designer Prescription | Verdict | Evidence | Confidence |
|-----|-----|-----|-----|-----|
| `validateNoClassAProgramLevelField(JsonNode)` → `void throws InvalidInputException` | recursive scan, code 9011 | **EXACT** | `TierEnumValidation.java:232-237` — signature matches; recursive walk `scanForClassAKeys` at L240-253 | **C7** |
| `validateNoClassBScheduleField(JsonNode)` → `void throws InvalidInputException` | root-level scan, code 9012 | **EXACT** | `TierEnumValidation.java:264-275` — signature matches; root-level-only scan loop at L268-274 | **C7** |
| `validateNoEligibilityCriteriaTypeOnWrite(JsonNode)` → `void throws InvalidInputException` | recursive scan, code 9013 | **EXACT** | `TierEnumValidation.java:285-304` — signature matches; recursive `scanForEligibilityCriteriaType` at L292-304 | **C7** |
| `validateNoStartDateForSlabUpgrade(TierValidityConfig)` → `void throws InvalidInputException` | post-binding, code 9014 | **EXACT** | `TierEnumValidation.java:316-327` — signature matches; SLAB_UPGRADE-family check at L321 | **C7** |
| `validateFixedFamilyRequiresPositivePeriodValue(TierValidityConfig)` → `void throws InvalidInputException` | post-binding, payload-only, code 9018 | **EXACT** | `TierEnumValidation.java:343-356` — signature matches; FIXED-family set at L348; positive-integer check at L350 | **C7** |
| `validateNoStringMinusOneSentinel(JsonNode)` → `void throws InvalidInputException` | recursive scan, code 9015, numeric-typed fields only | **EXACT** | `TierEnumValidation.java:371-394` — signature matches; `NUMERIC_FIELD_NAMES` list at L217-221; recursive `scanForStringSentinel` at L378-394 | **C7** |
| `validateNoNumericMinusOneSentinel(JsonNode)` → `void throws InvalidInputException` | recursive scan, code 9016, numeric-typed fields only | **EXACT** | `TierEnumValidation.java:407-430` — signature matches; recursive `scanForNumericSentinel` at L414-430 | **C7** |
| `validateRenewalCriteriaTypeCanonical(TierRenewalConfig)` → `void throws InvalidInputException` | exact-match on canonical literal, code 9017 | **EXACT** | `TierEnumValidation.java:442-453` — signature matches; exact-string equality check at L446 | **C7** |
| `TierCreateRequestValidator.validate(TierCreateRequest, JsonNode)` | two-arg form (Designer §6a.4.4) | **EXACT** | `TierCreateRequestValidator.java:65-93` — canonical two-arg form; pre-binding scans wired at L67-73 (order = Class A → B → ECT → string → numeric); post-binding at L87-92 | **C7** |
| `TierUpdateRequestValidator.validate(TierUpdateRequest, JsonNode)` | two-arg form, payload-only semantics | **EXACT** | `TierUpdateRequestValidator.java:42-66` — two-arg form; pre-binding scans identical to POST at L44-50; payload-only (no facade/repo injection in validator). | **C7** |
| Deprecated single-arg overloads | (not prescribed; Designer wording "`TierCreateRequestValidator.validate(TierCreateRequest)` signature is amended to `validate(TierCreateRequest, JsonNode)`") | **PRESENT (INFO)** | `TierCreateRequestValidator.java:124-133` — `@Deprecated public void validate(TierCreateRequest request) { validate(request, null); }`; same at `TierUpdateRequestValidator.java:68-77`. Tech-debt. See F-10c-2. | **C7** |

### D. Standing Decisions

`CLAUDE.md` A-01 and A-02 rows contain placeholder text (`*Example: …*`) with no enforceable decisions. **Skipped** per Part D instruction — no fabricated checks against empty rows.

---

## Findings Detail

### F-10c-1 — Pre-binding scans execute AFTER `treeToValue` at controller (semantic vs literal)

- **Severity**: LOW
- **Source**: Designer §6a.4.4 / §6a.4.5 (wiring)
- **Intent**: Designer §6a.4.4 comment states `// Pre-binding (raw JSON) — must run BEFORE @Valid DTO deserialization fails` and §6a.4.5 describes "pre-binding scan — implementation note". The intended semantic is "before the request is bound into a typed DTO that could itself be the trigger for `@Valid`-driven 400".
- **Reality**: `TierController.java:92-105` calls `objectMapper.treeToValue(rawBody, TierCreateRequest.class)` at L97, *then* calls `tierFacade.createTier(user.getOrgId(), request, rawBody, userId)` at L103. The validator is invoked inside the facade at `TierFacade.java:228` — meaning `treeToValue` has already run. The Jackson strict-mode exception (`UnrecognizedPropertyException`, surfaced as `HttpMessageNotReadableException` per advice L112) fires at L97 BEFORE the pre-binding scanner ever sees the tree.
- **Gap**: If Jackson strict-mode rejects the payload at L97, the 400 thrown is the **generic** `COMMON.INVALID_INPUT` message (from `TargetGroupErrorAdvice.java:117` `new Exception("COMMON.INVALID_INPUT")` — no numeric `[9011]` code) instead of the specific Class A scanner code. For inputs where Jackson fails FIRST on an unknown field, the response is NOT one of 9011–9018. For inputs where Jackson deserialization succeeds (only known keys or allowed unknown keys), the scanner then catches the Class A/B/ECT/sentinel fields as intended.
- **Why it is not a blocker**: The designer-prescribed scan targets (Class A keys, Class B keys, `eligibilityCriteriaType`, `-1` sentinels) are all valid JSON values that Jackson strict-mode does NOT reject on its own (they would either be well-typed fields on the DTO, or unknown fields caught later). Specifically: the `downgrade` field was removed from DTO — so sending `{"downgrade": {...}}` Jackson-fails (generic 400), while sending `{"dailyDowngradeEnabled": true}` at a nested valid path still triggers Class A 9011. The overlap between Jackson strict and the scanners is partial — both cover "unknown keys" from different angles — and the surviving gap (root-level unknown keys that are NOT in Class A or Class B) flows to Jackson generic 400. Designer §6a.4.4 accepts this with the phrase "unknown-but-unclassified keys fall through to Jackson strict-mode generic 400" (api-handoff §5.3 L536).
- **Recommendation**: Optionally add a controller-level advice that tries to extract a `[901x]` from `UnrecognizedPropertyException` messages, or move the pre-binding scans to run BEFORE `treeToValue` (e.g., a custom `HandlerMethodArgumentResolver` or a controller interceptor that scans `rawBody` and short-circuits with `InvalidInputException` before Spring binds). Non-blocker for Phase 11 since the documented behavior matches api-handoff §5.3.
- **Confidence**: **C6** (verified by reading `TierController.java:92-105` and `TierFacade.java:227-260` line by line)

### F-10c-2 — Deprecated single-arg validator overloads remain in codebase

- **Severity**: INFO / tech-debt
- **Source**: Designer §6a.8 — "§2.14 (Rework #5 validators) — `TierCreateRequestValidator.validate(TierCreateRequest)` signature is **amended** to `validate(TierCreateRequest, JsonNode)` by Rework #6a."
- **Intent**: Signature is amended; the Rework #5 single-arg form should either be replaced or marked deprecated with a migration plan.
- **Reality**: Both validators retain an `@Deprecated public void validate(TierCreateRequest)` overload that delegates to the two-arg form with `null` rawBody:
  - `TierCreateRequestValidator.java:124-133`
  - `TierUpdateRequestValidator.java:68-77`
- **Gap**: Marked `@Deprecated` correctly (so no misleading signal to new callers), but remains callable. Any caller invoking the single-arg form bypasses all pre-binding scans (9011, 9012, 9013, 9015, 9016) and allows those fields through into the persistence layer unchecked. This is especially dangerous for any internal test harness or future facade-level caller that might adopt the single-arg signature out of convenience.
- **Recommendation**: Remove the deprecated single-arg overloads after a deprecation cycle, OR add an assertion that throws `InvalidInputException` if `rawBody` is null (forcing callers to the canonical path). Audit repo callers first via `grep -r 'createValidator\.validate('` / `updateValidator\.validate(`.
- **Confidence**: **C7** (verified at exact `file:line` — direct Read of both validator files)

### F-10c-3 — Bracket-prefix exception message leaks validator internals (low-severity G-07 note)

- **Severity**: LOW
- **Source**: G-07.5 (logs include tenant context without leaking sensitive fields)
- **Intent**: Exception messages are the on-the-wire error payload. They should be diagnostic without leaking implementation internals or tenant data.
- **Reality**: Throw sites in `TierEnumValidation.java` format messages like:
  - `"[9011] Class A program-level field 'dailyDowngradeEnabled' is not allowed on per-tier write (use program config)"` (L244-246)
  - `"[9015] Field 'programId' contains the string sentinel \"-1\" — numeric fields must not use string form of -1 as a sentinel value."` (L386-388)
  These messages are logged verbatim at `TargetGroupErrorAdvice.java:82-83` (`log.error("error message {}", e.getMessage())`) and the stack trace is logged at L83.
- **Gap**: No tenant data (orgId, userId, programId) is leaked — spot check passes. The log line itself does not include MDC or tenant context unless upstream filters have populated MDC (not in scope for this change). Messages reveal the class of validator and the canonical field list in plaintext — this is intentional for UI diagnostics but worth noting for future audit if messages ever cross an organizational trust boundary.
- **Recommendation**: None required. If future work tightens error-message diagnostics for multi-tenant SaaS, replace field names with opaque error-code-only messages and move field-level details into a separate authenticated diagnostics endpoint.
- **Confidence**: **C5** (verified by reading all 8 throw sites; tenant-data content check was message-scoped only, not MDC-scoped)

### F-10c-4 — ADR-20R strict-mode is fragile to future Jackson2ObjectMapperBuilder migration

- **Severity**: MEDIUM
- **Source**: ADR-20R + R14 residual risk
- **Intent**: ADR-20R states strict-mode rejection is the mechanism for unknown-field hard-reject; Designer §6a.2.1 forward guard "do NOT flip global".
- **Reality**: `IntouchApiV3Application.java:95-99` declares `@Bean public ObjectMapper objectMapper(){ ObjectMapper objectMapper = new ObjectMapper(); objectMapper.setTimeZone(TimeZone.getDefault()); return objectMapper; }`. Jackson's native default for `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` is `true`, so strict rejection is active. **However**: if someone later replaces this with a `Jackson2ObjectMapperBuilder`-based bean (which Spring Boot defaults to `FAIL_ON_UNKNOWN_PROPERTIES=false`), strict mode silently flips and the `downgrade` field (or any other unknown-key removal) would silently pass through. There is no compile-time guard against this regression.
- **Gap**: Structural — no ArchUnit rule, no annotation-based guard, no integration test (as far as this phase audited) explicitly asserts that `FAIL_ON_UNKNOWN_PROPERTIES=true`. Designer §6a.2.1 states "the SDET test `TierUnknownFieldRejectIT` (Phase 9) will catch it immediately" — verification of that test's presence and coverage is in scope for Phase 11 Reviewer, not this compliance pass.
- **Recommendation**:
  - (short-term) Add an `@PostConstruct` assertion in a `TierModuleConfig` (or similar) that logs a WARN/ERROR if `objectMapper.getDeserializationConfig().isEnabled(FAIL_ON_UNKNOWN_PROPERTIES)` returns `false`.
  - (medium-term) Pin the strict-mode setting explicitly in the `@Bean ObjectMapper` method: `objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true);` — this is defensive but belt-and-braces, and matches the ADR-20R fallback path (c) at minimal cost. Would eliminate the silent-regression fear entirely.
  - (long-term) Add an ArchUnit test (see Suggested Rules below) that reads the compiled `ObjectMapper` bean and asserts strict.
- **Confidence**: **C6** (verified Jackson default via public Jackson source docs; verified codepath by reading `IntouchApiV3Application.java:89-99`; verified absence of per-DTO override on `TierCreateRequest.java`/`TierUpdateRequest.java` and absence of `spring.jackson.deserialization` in `application*.properties`)

---

## Suggested ArchUnit Rules

1. **`ErrorCodesInBand`** — Classes in `com.capillary.intouchapiv3.tier.validation` must declare `public static final int` error-code constants in the range `[9001, 9020]`. Prevents out-of-band code creep when new rejects are added in future reworks.

2. **`ValidatorReturnTypeAndException`** — All methods named `validateNo*` or `validate*RequiresXxx` in `TierEnumValidation` must return `void` and declare `throws InvalidInputException` (or throw it unchecked). Structurally enforces G-13.1 pattern for this module.

3. **`NoBuiltInExceptionsInValidators`** — Classes under `tier.validation.**` must not throw `java.lang.IllegalArgumentException`, `java.lang.IllegalStateException`, or `java.lang.RuntimeException`. Enforces G-13.1 at CI time.

4. **`ObjectMapperStrictMode`** — The `@Bean`-annotated method returning `ObjectMapper` in `IntouchApiV3Application` must either (a) call `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` explicitly, OR (b) not call `configure(FAIL_ON_UNKNOWN_PROPERTIES, false)`. Catches the F-10c-4 regression vector.

5. **`ControllersHaveNoTryCatch`** — Methods annotated `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@GetMapping` in `com.capillary.intouchapiv3.resources.**` must not contain `try-catch` blocks. Enforces G-13.2 pattern.

---

## Recommendation to Orchestrator

- **Compliance verdict**: COMPLIANT WITH FINDINGS (non-blocker)
- **Blockers for Phase 11**: None.
- **Non-blockers to carry into Phase 11 / Reviewer notes**:
  - F-10c-1 (pre-binding literal ordering vs Jackson treeToValue) — advisory only, documented in api-handoff §5.3
  - F-10c-2 (deprecated single-arg overloads) — tech-debt, candidate for a follow-up cleanup commit
  - F-10c-3 (error-message diagnostics content) — no action required
  - F-10c-4 (Jackson strict-mode fragility) — recommend defensive `configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` in next small-commit OR SDET confirmation of `TierUnknownFieldRejectIT` coverage during Phase 11
- **Next phase**: Phase 10d (Migration Validation) is **SKIPPED** — Rework #6a is contract-hardening only (zero schema, zero Thrift, zero engine). Proceed to **Phase 11 (Reviewer)**.

---

```
PHASE: 10c Compliance (Analyst --compliance)
STATUS: complete
ARTIFACT: 06b-gap-analysis.md
VERDICT: COMPLIANT WITH FINDINGS

FINDINGS SUMMARY:
- CRITICAL: 0
- HIGH:     0
- MEDIUM:   1   (F-10c-4 — ADR-20R strict-mode is fragile to future ObjectMapper refactor)
- LOW:      2   (F-10c-1 pre-binding literal ordering; F-10c-3 error-message diagnostics)
- INFO:     1   (F-10c-2 deprecated single-arg validator overloads)

BLOCKERS FOR PHASE 11: None.

QUESTIONS FOR USER (if any):
- Q1 (C5): Do you want a defensive `objectMapper.configure(FAIL_ON_UNKNOWN_PROPERTIES, true)` added to `IntouchApiV3Application.java:95-99` now to close F-10c-4 before Phase 11, or defer to a future hardening commit?
- Q2 (C5): Should the deprecated single-arg `validate(TierCreateRequest)` and `validate(TierUpdateRequest)` overloads be removed now, or left for a follow-up cleanup?

ASSUMPTIONS MADE (user should verify):
- A1 (C6): `TierUnknownFieldRejectIT` SDET test exists and asserts 400 on unknown-field POST, as stated in Designer §6a.2.1. Not re-verified in this phase — Phase 11 Reviewer scope.
- A2 (C7): Jackson's native default for `FAIL_ON_UNKNOWN_PROPERTIES` is `true` — a well-documented invariant of the Jackson library; confirmed indirectly via F1 reconnaissance finding and the 36-DTO opt-out pattern.
- A3 (C6): Spring MVC's `@RequestBody JsonNode` path does NOT trigger Jackson `FAIL_ON_UNKNOWN_PROPERTIES` rejection (because `JsonNode` is a generic tree, not a typed DTO). Rejection is only triggered by the subsequent `objectMapper.treeToValue(rawBody, TierCreateRequest.class)` call at `TierController.java:97`.
```
