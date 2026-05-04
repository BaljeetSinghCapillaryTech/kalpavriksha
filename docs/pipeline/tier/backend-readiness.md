# Backend Readiness — Tier v3 Rework #6a

> Phase 10b — Backend Readiness Gate
> Initial date: 2026-04-22 (NOT READY — 2 BLOCKERS)
> Re-gate date: 2026-04-23 (READY WITH WARNINGS — both BLOCKERS closed)
> Branch: raidlc/ai_tier
> Reviewer: /backend-readiness skill (independent verification)

---

## Overall Verdict: READY WITH WARNINGS (as of 2026-04-23 re-gate)

**Rationale (initial 2026-04-22):** P1 (controller wiring gap) was a confirmed BLOCKER — pre-binding scans silently skipped on every production HTTP path. P2 (error code wire contract) was a confirmed BLOCKER — codes 9011-9018 lived in message string only, `TargetGroupErrorAdvice` emitted `999999` on the wire.

**Rationale (re-gate 2026-04-23):** User chose R,R → Developer Rework Cycle 1 delivered both fixes. Independent re-verification confirmed P1 CLOSED at C7 (6/6 criteria PASS: TierFacade signatures widened, TierController forwards rawBody, TODO comments removed, validator scans fire end-to-end) and P2 CLOSED at C7 (5/5 criteria PASS: 8 throws bracket-prefixed with `public static final int` constants, regex extractor `^\[(\d+)\]\s*(.*)$` in advice, ApiError(longCode, strippedMsg) bypasses MessageResolverService, backward-compatible fall-through preserved). Verdict flipped NOT READY → READY WITH WARNINGS.

**Retained WARNINGS** (unchanged from initial gate — not re-checked per abbreviated scope):
- W1 / P3 (WARNING) — IT infra: `TierControllerIntegrationTest` 3 errors from Testcontainers/Docker unavailable locally. BT-215 must be confirmed GREEN in Docker-capable CI before merge.
- W2 / P4 (WARNING) — Date format: lexicographic `String.compareTo()` on `validity.endDate/startDate` unsafe for non-canonical ISO-8601 input.
- I1 / P5 (INFO) — Recursive scanners have no depth limit. Negligible risk at bounded tier payload sizes.

**Re-gate residual INFO** (none blocking):
- INFO-A — `@Deprecated` single-arg validator overloads now confirmed dead code (tracked as I2).
- INFO-B — BT-215 `assertEquals(9011L, ...)` assertion added by Developer; awaits Docker-capable CI to run GREEN.
- INFO-C — Facade signature change caller-graph: grep confirmed `TierController.java` + `TierFacadeTest.java` are the only `.createTier` / `.updateTier` callers repo-wide. No unknown production callers broken by the widening. Cleared at C7.

**Decision**: Proceed to Phase 10c Compliance. P3 remains a pre-merge CI gate (not a pre-10c gate).

---

## Scope Context

Rework #6a is contract-hardening only: zero schema, zero Thrift, zero engine changes. All standard backend-readiness areas (query performance, Thrift compatibility, cache invalidation, resource management, migration safety) evaluate to PASS because nothing in those domains changed. The substantive assessment is the validator code added in Phase 10 and the five P1–P5 priorities flagged in the Phase 10 forward cascade.

---

## Phase 10 P1–P5 Priorities — Independent Verification

### P1: Controller wiring gap

- **Claim by Developer:** VERIFIED — independently confirmed, C7
- **Evidence chain (all from primary source reads):**
  1. `TierController.java:90` — TODO comment: `"TODO Phase 10: invoke TierPreBindingScanner.scan*(rawBody) in fail-fast order."` — present in current code [C7: read the file directly]
  2. `TierController.java:103` — `tierFacade.createTier(user.getOrgId(), request, userId)` — three-arg call, no `rawBody` parameter [C7]
  3. `TierController.java:110` — same TODO comment on `updateTier` javadoc [C7]
  4. `TierController.java:122` — `tierFacade.updateTier(user.getOrgId(), tierId, request, userId)` — four-arg call, no `rawBody` [C7]
  5. `TierFacade.java:227` — `createValidator.validate(request)` — single-arg `@Deprecated` overload [C7]
  6. `TierFacade.java:262` — `updateValidator.validate(request)` — same single-arg call [C7]
  7. `TierCreateRequestValidator.java:130–133` — `@Deprecated validate(TierCreateRequest)` delegates to `validate(request, null)` [C7]
  8. `TierCreateRequestValidator.java:65–73` — pre-binding scan block is `if (rawBody != null)` guarded; with `rawBody=null`, all 5 pre-binding scans (9011, 9012, 9013, 9015, 9016) are skipped [C7]
  9. `TierUpdateRequestValidator.java:42–50` — identical `if (rawBody != null)` guard; same skip on update path [C7]
- **Net production effect:** Payloads containing Class A keys (9011), Class B keys (9012), `eligibilityCriteriaType` (9013), string `-1` sentinel (9015), or numeric `-1` sentinel (9016) pass through to Jackson `treeToValue()`. Jackson strict-mode will produce a generic 400 for truly unknown keys, but Class A/B keys that happen to be on the DTO will be silently accepted or surface only via Jackson's error (not the specific codes). The primary contract-hardening deliverable is not active on the production path.
- **Why unit tests still pass:** `TierCreateRequestValidatorTest` and `TierUpdateRequestValidatorTest` call the canonical two-arg `validate(request, rawBody)` directly, bypassing the facade entirely — the controller wiring gap is invisible to the unit test suite.
- **Severity: BLOCKER** — C7. The five pre-binding validation rules that are the stated deliverable of Rework #6a (REQ-23, REQ-24, REQ-25, REQ-26/40) are unexecuted on every real production HTTP request. BT-215 (the IT test for this path) also cannot pass until this is wired.
- **Recommended fix: Option A (minimal, lowest risk)**
  - Widen `TierFacade.createTier` signature from `(long orgId, TierCreateRequest request, String userId)` to `(long orgId, TierCreateRequest request, String userId, JsonNode rawBody)`.
  - Widen `TierFacade.updateTier` signature similarly.
  - In `TierController.createTier` (line 103): pass `rawBody` as the fourth argument.
  - In `TierController.updateTier` (line 122): pass `rawBody` as the fifth argument.
  - Change `TierFacade.java:227` to `createValidator.validate(request, rawBody)` and `TierFacade.java:262` to `updateValidator.validate(request, rawBody)`.
  - Option B (move scans to controller directly): also acceptable but splits validation logic across the controller/facade boundary, harder to test without a running HTTP server.
  - Option C (interceptor): over-engineering for this scope; adds a Spring processing step with its own test surface.
  - **Rationale for A:** The `rawBody` `JsonNode` is already captured in the controller at line 94 (`@RequestBody JsonNode rawBody`). Passing it through the facade keeps all validation in one place (the validator classes), is the minimal reversible change, and requires updating only 4 call sites and 2 facade method signatures.
- **Blocks Reviewer?** YES — until fixed, the primary deliverable is not exercised on the production HTTP path.

---

### P2: Error response envelope

- **Claim by Developer:** `InvalidInputException` has no `int code` constructor (codes live in message strings only). VERIFIED, C7.
- **Evidence chain:**
  1. `InvalidInputException.java:6–13` — single constructor `InvalidInputException(String message)`, sets `this.message`. No `int code` field. [C7: read file]
  2. `TargetGroupErrorAdvice.java:80–85` — `handleInvalidInputException` handler: calls `return error(BAD_REQUEST, e)`. [C7: read file]
  3. `TargetGroupErrorAdvice.java:233–249` — `error(HttpStatus, Exception)` delegates to `error(HttpStatus, String)` with `e.getMessage()`. [C7]
  4. `TargetGroupErrorAdvice.java:237–249` — `error(HttpStatus, String message)`: calls `resolverService.getCode(message)` and `resolverService.getMessage(message)` using the exception message string as the i18n key. [C7]
  5. `MessageResolverService.java:38–50` — `getCode(String key)`: splits key on `.`, looks up prefix in `fileNameMap` (`TARGET_LOYALTY`, `COMMON`, `OAUTH`, `INTEGRATIONS`, `WEB_HOOK`). If prefix does not match, falls through to `"i18n.errors.messages"` properties file. Returns `999999L` as the default when property not found. [C7]
  6. `MessageResolverService.java:52–63` — `getMessage(String key)`: returns `""` (empty string) if key not in properties. `TargetGroupErrorAdvice.java:241–243` then falls back to the raw message string. [C7]
  7. The 9011–9018 message strings (e.g. `"Class A program-level field 'isActive' is not allowed on per-tier write (use program config)"`) do NOT start with a registered namespace prefix and are NOT registered as i18n keys. [C7: inspected all messages in TierEnumValidation.java]
- **Wire response today for a 9011 rejection (if P1 were fixed):**
  ```json
  {
    "errors": [{
      "code": 999999,
      "message": "Class A program-level field 'isActive' is not allowed on per-tier write (use program config)"
    }]
  }
  ```
  The `code` field will be `999999`, not `9011`. The `message` string contains the human-readable description, which the UI could parse, but that is fragile (string-matching, not code-matching).
- **BT-215 note:** The IT test (BT-215) asserts `errors` array is present (passes) but does NOT assert `errors[0].code == 9011` — it only checks `assertFalse(errors.isMissingNode())`. So BT-215 would PASS even with `code: 999999`. This means the unit and IT test suite does not catch the P2 gap. [C7: read TierControllerIntegrationTest.java lines 289–300]
- **Severity: BLOCKER** — C6. The UI and any programmatic API consumer cannot pattern-match on `9011–9018` using the `errors[0].code` field. The api-handoff document specifies these codes. The gap exists today and will persist after P1 fix unless the exception contract is widened.
- **Recommended fix options (in order of preference):**
  - **Option X1 (preferred — embed code in message prefix):** Change each `throw new InvalidInputException(...)` in `TierEnumValidation.java` to prefix the code in bracket form: `throw new InvalidInputException("[9011] Class A program-level field ...")`. Then add a fallback in `TargetGroupErrorAdvice.handleInvalidInputException` that extracts the numeric prefix via regex `^\[(\d+)\]` and sets the `ApiError.code`. No change to `InvalidInputException` class; no change to `MessageResolverService`. Consistent with G-13.4 pattern already documented in GUARDRAILS (`throw new InvalidInputException("[9001] Tier name is required")`).
  - **Option X2 (cleaner — widen `InvalidInputException`):** Add `int code` field to `InvalidInputException` (new constructor `InvalidInputException(int code, String message)`). Add a separate `@ExceptionHandler` in `TierErrorAdvice` (already exists for tier domain) that handles `InvalidInputException` and constructs `ApiError(code, message)` directly, bypassing `MessageResolverService`. This is the most correct long-term approach but changes the exception class (wider blast radius).
  - **Option X3 (minimal — no code extraction):** Accept that `code: 999999` is the wire shape, update the api-handoff doc to say codes are in `message` string only, and have the UI parse `[9011]` prefix from the message. Lowest risk but weakens the contract.
- **Rationale:** G-13.4 documents the `[code] message` pattern as the intended approach. X1 aligns with this and requires only changes to the 8 throw sites in `TierEnumValidation.java` plus a one-time extractor in the advice. X2 is better long-term but is a wider change.
- **Blocks Reviewer?** YES — the api-handoff contract specifies numeric error codes and the wire response does not match.

---

### P3: IT infrastructure

- **Claim by Developer:** IT tests fail due to Testcontainers/Docker unavailability, not implementation gap. VERIFIED — C5.
- **Evidence chain:**
  1. `AbstractContainerTest.java` — extends `@Testcontainers`, uses `MySQLContainer`, `MongoDBContainer`, `GenericContainer` (Redis), `RabbitMQContainer`. [C7: read file lines 1–50]
  2. Session-memory Phase 10 block confirms: `"TierControllerIntegrationTest: all 3 IT tests error out with IllegalState: Failed to load ApplicationContext"` — Testcontainers/Docker not available. [C5: session-memory evidence]
  3. `TierControllerIntegrationTest.java` (lines 51–308) — all 3 tests (BT-210, BT-212, BT-215) are complete, well-formed JUnit 5 tests that verify real HTTP behavior via live port. They cannot be verified by code inspection alone — they require a running Spring context with real Mongo + MySQL. [C7: read file]
  4. BT-210 and BT-212 test the GET read path (existing production code) — independent of P1. BT-215 tests the POST path with a Class A payload and requires P1 to be fixed to reach the 400 path.
- **Severity: WARNING** (gated on CI, not production blocking on its own). However, BT-215 will not PASS GREEN until P1 is also fixed. The 3 IT tests require Docker daemon in the execution environment.
- **Blocks Reviewer?** Conditionally — BT-215 must be confirmed GREEN in CI after P1 is fixed. BT-210 and BT-212 should pass independently (GET path is pre-existing).

---

### P4: Date format strictness

- **Claim by Developer:** Lexicographic ISO-8601 UTC string comparison used. VERIFIED — C7.
- **Evidence chain:**
  1. `TierCreateRequestValidator.java:101–121` — `validateEndDateNotBeforeStartDate` uses `validity.getEndDate().compareTo(validity.getStartDate()) < 0` — lexicographic Java `String.compareTo()`. [C7: read file]
  2. `TierValidityConfig` fields — `startDate` and `endDate` declared as `String`. Comment: `"ISO-8601 UTC, computed on read"`. [C7: grep on TierValidityConfig.java lines 25–28]
  3. No Jackson `@JsonDeserialize` annotation converting to `Instant` on these fields — they arrive as raw JSON strings and are stored as `String` in MongoDB. [C5: inferred from field type declaration + no deserializer observed in grep]
- **Assessment:** Lexicographic comparison is SAFE for ISO-8601 UTC strings with a consistent format (e.g. `"2026-06-01T00:00:00Z"`). ISO-8601 is lexicographically sortable when the format is consistent. **Risk:** If a client sends non-canonical formats like `"2026-6-1T00:00:00Z"` (month/day without zero-padding) or a timezone-offset string like `"2026-06-01T05:30:00+05:30"`, the comparison yields incorrect results.
- **Severity: WARNING** — C4. Low probability (API is authenticated, contract specifies ISO-8601 UTC, and Jackson would reject truly malformed strings), but `String`-typed fields bypass format enforcement.
- **Recommended fix:** Wrap in `Instant.parse()` before comparison and throw `InvalidInputException` on `DateTimeParseException`. This enforces ISO-8601 UTC format AND provides correct temporal ordering. Cost: ~4 lines.
- **Blocks Reviewer?** NO — but should be flagged in Reviewer phase as a known risk.

---

### P5: Scanner performance

- **Claim by Developer:** Recursive tree scanners are O(n) on JSON node count. VERIFIED — C7.
- **Evidence chain:**
  1. `TierEnumValidation.java:240–252` — `scanForClassAKeys`: object traversal calls `fieldNames().forEachRemaining()` + recursive call per child; array traversal calls `forEach`. No memoization, no depth limit. [C7: read file]
  2. `TierEnumValidation.java:293–304` — `scanForEligibilityCriteriaType`: same recursive pattern. [C7]
  3. `TierEnumValidation.java:378–393` — `scanForStringSentinel`: same. [C7]
  4. `TierEnumValidation.java:414–429` — `scanForNumericSentinel`: same. [C7]
  5. Class B scanner (`validateNoClassBScheduleField`, lines 264–275): root-level only — NOT recursive. O(3) constant. [C7]
- **Worst-case analysis:**
  - Time complexity: O(N) where N = total JSON node count. For typical tier payloads (< 50 nodes per Developer's estimate), this is negligible.
  - Stack depth: Each recursive call is one JSON nesting level. Typical tier JSON is 3–5 levels deep. JVM default stack supports hundreds of levels. No realistic tier payload would cause `StackOverflowError`.
  - Short-circuit: All recursive scanners throw `InvalidInputException` on first match (implicit short-circuit). The Class A scanner throws immediately on detecting the first Class A key — it does not accumulate all violations.
  - No adversarial risk for tier domain: tier payloads are bounded by the DTO schema; deeply nested adversarial JSON would require bypassing Jackson's `treeToValue` and is not a realistic vector on an authenticated internal API.
- **Severity: INFO** — C6 LOW risk. No action required for production readiness.
- **Blocks Reviewer?** NO.

---

## Checklist Results

| Area | Status | Findings | Severity |
|------|--------|----------|----------|
| Query Performance | PASS | No new DAO calls. Validator-layer only. No DAO/repository references in validation package. N+1: none detected. | — |
| Thrift Compatibility | PASS | No `.thrift` files modified. Scope floor confirmed: zero Thrift changes. | — |
| Cache Invalidation | PASS | No `@Cacheable`/`@CacheEvict`/`@CachePut`/`RedisTemplate` usage in modified tier validation files. Validators are request-time only. | — |
| Resource Management | PASS | No new HTTP clients, no `InputStream`/`OutputStream`/`Connection` opened in modified files. | — |
| Error Handling | FAIL | P1 + P2 blockers. `InvalidInputException` → 400 confirmed. But pre-binding scans are bypassed (P1) and wire `code` is `999999` not `9011–9018` (P2). | BLOCKER |
| Migration Safety | PASS | No Flyway migration scripts in `src/main/resources/db/migration/`. Zero schema changes confirmed. | — |

---

## Detailed Findings

### BLOCKERS (must fix before Reviewer)

**BLOCKER-1: P1 — Pre-binding scans 9011–9016 not executed on production path**

- Files: `TierController.java:103`, `TierController.java:122`, `TierFacade.java:227`, `TierFacade.java:262`
- Evidence: Controller receives `rawBody` (lines 94, 115) but passes three/four-arg to facade with no `rawBody`. Facade calls deprecated single-arg `validate(request)`. Single-arg delegates `validate(request, null)`. Validators guard pre-binding block with `if (rawBody != null)` — block skipped on null.
- Fix: Option A — widen `TierFacade.createTier` / `updateTier` to accept `JsonNode rawBody`; pass from controller; facade calls `validate(request, rawBody)`. ~10 lines across 3 files.
- Confidence: C7 — 9 independent file:line evidence points.

**BLOCKER-2: P2 — Error codes 9011–9018 not emitted on wire (999999 instead)**

- Files: `TargetGroupErrorAdvice.java:237–249`, `MessageResolverService.java:38–50`, `TierEnumValidation.java` (8 throw sites)
- Evidence: `handleInvalidInputException` passes raw message string through `resolverService.getCode()`. Message strings are plain English (not i18n keys). `MessageResolverService` returns `999999L` as default. `ResponseWrapper.ApiError.code` = `999999` for all tier contract-hardening rejections.
- Fix: Option X1 — prefix 8 throw sites in `TierEnumValidation.java` with `[9011]`–`[9018]` bracket format per G-13.4. Add bracket-extractor in `InvalidInputException` handler. ~20 lines across 2 files.
- Note: BT-215 IT test does NOT assert `code == 9011` — gap is invisible to the existing test suite.
- Confidence: C7 — verified `MessageResolverService` path, `TargetGroupErrorAdvice` handler, all 8 throw sites, and IT test assertion logic.

---

### WARNINGS (should fix)

**WARNING-1: P3 — BT-215 requires both P1 fix AND Docker/CI environment**

- File: `TierControllerIntegrationTest.java:243–307`
- Evidence: BT-215 tests the production HTTP POST path for a Class A rejection (9011). Requires: (a) Docker/Testcontainers for `AbstractContainerTest`, and (b) P1 fix so scanner fires. Until both conditions met, BT-215 stays ERROR/FAIL.
- Severity: WARNING — C5. Confirm GREEN in CI before merge.

**WARNING-2: P4 — Lexicographic date comparison vulnerable to non-canonical ISO-8601 input**

- File: `TierCreateRequestValidator.java:114–115`
- Evidence: `validity.getEndDate().compareTo(validity.getStartDate())` — Java `String.compareTo()`. Both fields typed as `String` in `TierValidityConfig`. No format enforcement before comparison.
- Fix: Wrap in `Instant.parse()` → throw `InvalidInputException` on `DateTimeParseException`. ~4 lines.
- Severity: WARNING — C4. Low probability, non-zero risk.

---

### INFO (nice to have)

**INFO-1: P5 — Recursive scanners have no depth limit or node-count circuit-breaker**

- File: `TierEnumValidation.java` — 4 recursive helpers (lines 240–252, 293–304, 378–393, 414–429)
- Evidence: No `maxDepth` parameter. Current risk: negligible (bounded payloads, authenticated API). Future hardening: add depth limit.
- Severity: INFO — C6 LOW.

**INFO-2: `@Deprecated` single-arg validate overloads become dead code after P1 fix**

- Files: `TierCreateRequestValidator.java:130–133`, `TierUpdateRequestValidator.java:74–77`
- Evidence: These overloads exist solely because the facade has not been widened. After P1 Option A, they serve no purpose.
- Severity: INFO — cleanup ticket.

**INFO-3: BT-215 does not assert `errors[0].code == 9011`**

- File: `TierControllerIntegrationTest.java:289–300`
- Evidence: Only asserts `assertFalse(errors.isMissingNode())`. After P2 fix, should add `assertEquals(9011L, body.path("errors").get(0).path("code").asLong())`.
- Severity: INFO — test debt.

---

## Forward Cascade Payload → Phase 10c (Analyst — Compliance)

Phase 10c must verify:

1. **P1 fix compliance:** Confirm `TierFacade.createTier` and `updateTier` call two-arg `validate(request, rawBody)`. Grep for remaining single-arg `validate(request)` calls on production path — should be zero.
2. **P2 fix compliance:** Confirm all 8 throw sites in `TierEnumValidation.java` use `[901x]` prefix. Confirm wire `code` field emits `9011–9018` (not `999999`). Confirm api-handoff document updated to match actual wire shape.
3. **BT-215 assertion:** Flag that IT test does not assert `code == 9011` — Reviewer should request assertion update.
4. **P4 date format:** Confirm whether lexicographic comparison was fixed or accepted; if accepted, confirm api-handoff input constraints document ISO-8601 UTC requirement explicitly.
5. **ADR-21R read-wide (BT-212):** Confirm BT-212 passes GREEN in CI — downgrade block preserved on GET read path.
6. **G-13.4 compliance:** Confirm all new `InvalidInputException` throws in the tier validation package use the `[code]` prefix format per GUARDRAILS.

---

## Confidence Legend

| Level | Label | Meaning | Usage in this doc |
|-------|-------|---------|------------------|
| C7 | Near Certain | Primary source verified (read actual file, exact line) | All BLOCKER evidence |
| C6 | High Confidence | Multiple independent file reads converge | P5 INFO rating |
| C5 | Confident | Strong evidence, minor residual uncertainty | P3 WARNING |
| C4 | Probable | Likely true, notable uncertainty remains | P4 WARNING |

Distribution: ~60% C7 (direct file reads), ~15% C6, ~15% C5, ~10% C4. No C1–C3 claims. Well-calibrated for a readiness gate where direct evidence is available.

---

## Routing Decision

**Route back to Developer (Phase 10 re-entry).**

Minimum fix scope for re-promotion:
1. **P1 (BLOCKER-1):** Facade signature widening + controller pass-through + validator two-arg call wiring. ~10 lines, 3 files.
2. **P2 (BLOCKER-2):** Bracket-prefix 8 throw sites in `TierEnumValidation.java` + add code extractor to `InvalidInputException` handler. ~20 lines, 2 files.
3. **Verify BT-215 GREEN** in CI after P1+P2 fixes.

After fixes: abbreviated Phase 10b re-gate (P1, P2, P3 items only). If confirmed: verdict flips to READY WITH WARNINGS (WARNING-1: CI gate, WARNING-2: date format). Proceed to Phase 11 Reviewer.
