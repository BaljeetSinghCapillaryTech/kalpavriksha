# Phase 11 Reviewer — CAP-185145 Benefit Category CRUD

> **Date**: 2026-04-19
> **Reviewer skill version**: SKILL.md (Phase 11)
> **Confidence framework**: C1–C7 (principles.md)

---

## Summary

**Verdict: APPROVED WITH WARNINGS**

**1 blocker · 5 warnings · 4 notes**

Excluded from scope (Manual routing already confirmed):
- B1 (missing `idx_bc_org_program_name` index)
- B2 (`CREATE TABLE` without `IF NOT EXISTS` in cc-stack-crm DDL)
- B3 (`BenefitCategoryResponse.active` serialises as `"active"` not `"isActive"`)
- F-02 (POST verb semantics documentation)
- F-04 (`isActive` default=true inconsistency)

Accepted deviations:
- D-61: F-01 accepted — `/activate` + `/deactivate` use `@PostMapping`
- D-62: F-03 partial — service throws `BC_PAGE_SIZE_EXCEEDED` 400 when `size > 100`; controller has no `@Max(100)` gate

---

## Build Verification

Build verification is NOT re-run per the instruction (last GREEN evidence cited from session-memory).

**Last GREEN evidence** (session-memory.md §Phase 10 M3):

| Suite (intouch-api-v3) | Tests | Result |
|------------------------|-------|--------|
| Unit tests (`BenefitCategory*Test`) | 36 | ALL PASS |
| Integration tests (`BenefitCategory*IT`) | 40 | ALL PASS |
| **Total** | **76** | **GREEN — C7** (44.5s wall clock including Testcontainers boot) |

emf-parent M5 Testcontainers ITs committed (`0fbed773d7`). Local runtime deferred per user directive due to pre-existing AspectJ 1.7 + Java 17 + `nrules.*` dep incompatibility (TD-SDET-05 — pre-dates this feature). CI is the verification gate per D-56.

emf-parent M6 (`5caa9a9362`) replaces silent size clamp with `BC_PAGE_SIZE_EXCEEDED` throw; ITs pass per commit message.

**Build Verification: PASS (via prior phase evidence, C7)**

---

## Requirements Traceability (spot-check)

| BA Requirement | BT Case(s) | Test (file:line) | Code (file:line) | Status |
|---|---|---|---|---|
| AC-BC01' — Category creation (201 + full DTO, 409 dup, 400 invalid tier) | BT-001, BT-004, BT-006..BT-009 | `BenefitCategoryCreateIT.java` | `PointsEngineRuleService.java:4472-4552`, `BenefitCategoriesV3Controller.java:41-49` | PASS |
| AC-BC02 — Name unique per program (case-sensitive D-47) | BT-004, BT-004b | `BenefitCategoryCreateIT.java` | `BenefitCategoryDao.java:43-46` (no LOWER()) | PASS |
| AC-BC03' — Slab mapping enforced (D-35 diff-apply) | BT-029..BT-033, BT-035 | `BenefitCategoryUpdateIT.java` | `PointsEngineRuleService.java:4603-4640` | PASS |
| AC-BC12 — Deactivation cascade in one txn | BT-051..BT-056 | `BenefitCategoryDeactivateIT.java` | `PointsEngineRuleService.java:4803-4831` + `@Transactional(warehouse)` | PASS |
| US-6 — Reactivation path, no auto-reactivate of mappings | BT-042..BT-050 | `BenefitCategoryActivateIT.java` | `PointsEngineRuleService.java:4745-4800`; no cascade to mappings | PASS |
| NFR-6 — Idempotency (activate no-op → 204) | BT-048, BT-055 | `BenefitCategoryActivateIT::bt048`, `BenefitCategoryDeactivateIT::bt055` | `PointsEngineRuleService.java:4762-4768` (stateChanged=false path); deactivate idempotency via 404 guard | PASS |
| NFR-7 — Structured logs with orgId/programId | BT-G07, logging spot-check | `BenefitCategoryGuardrailIT::btG07` | `PointsEngineRuleService.java:4547-4550` — `String.format` with orgId, id, programId, slabCount | PASS |
| D-42 — `?includeInactive=true` audit path | BT-017, BT-018 | `BenefitCategoryGetIT::bt017`, `bt018` | `BenefitCategoryDao.java:31-38` (two DAO methods); `PointsEngineRuleService.java:4657-4680` | PASS |
| D-48 — `?isActive=foo` → 400 VALIDATION_FAILED | BT-022b, BT-038 | `BenefitCategoryListIT::bt038` | `BenefitCategoriesV3Controller.java:135-145` (controller `@ExceptionHandler`) | PASS |
| D-43 — stateChanged sentinel on activate | BT-045, BT-048 | `BenefitCategoryActivateIT::bt045`, `bt048` | `BenefitCategoryResponseMapper.java:52-54`; `PointsEngineRuleService.java:4765-4766` | PASS |

All 10 in-scope requirements: **PASS**. No gaps found.

---

## Session Memory Alignment (spot-check)

| Decision | Where honoured | Status |
|---|---|---|
| D-28 + D-60 — name uniqueness across ALL states (incl. inactive) | `PointsEngineRuleService.java:4503-4511` uses `findByProgramAndName` (not `findActiveByProgramAndName`) | PASS |
| D-35 — slabIds embedded; server-side diff-apply | `PointsEngineRuleService.java:4603-4640`; 3-step diff (current-active, INSERT, soft-DELETE) | PASS |
| D-36 / ADR-004 — cascade deactivation in same txn | `PointsEngineRuleService.java:4803-4831` both calls under single `@Transactional(warehouse, REQUIRED)` | PASS |
| D-39 — asymmetric activate 200+DTO vs deactivate 204 | `BenefitCategoriesV3Controller.java:104-128` — activate returns 200/204; deactivate always 204 | PASS |
| D-41 — reuse `PeProgramSlabDao.findByProgram` + in-memory Set | `PointsEngineRuleService.java:4838-4851` | PASS |
| D-44 — JPA entities hand-written, DTOs use Lombok @Getter @Setter | `BenefitCategory.java:76-104` (hand-written); `BenefitCategoryCreateRequest.java:19-20` (@Getter @Setter) | PASS |
| D-45 revised — `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` | `BenefitCategoryResponse.java:29,34` | PASS |
| D-47 — case-sensitive name uniqueness (no LOWER()) | `BenefitCategoryDao.java:43-46` — `AND c.name = :name` (no LOWER) | PASS |
| D-62 / F-03 partial — size > 100 throws 400 at service | `PointsEngineRuleService.java:4695-4698` | PASS |
| C-25 — orgId explicit on every DAO method | `BenefitCategoryDao.java` all 9 methods take `@Param("orgId")` as first explicit param | PASS |
| C-28 — G-07.1 tenant isolation by convention | All DAO `@Query` include `WHERE … orgId = :orgId` — `BenefitCategoryDao.java:31-110`, `BenefitCategorySlabMappingDao.java:27-67` | PASS |

All 11 spot-checked decisions: **PASS**. No drift found.

---

## Findings

### R-01: `BenefitCategoryUpdateRequest.slabIds` `@NotNull` but null still possible if JSON key absent
- **Severity**: BLOCKER
- **Category**: Requirements / Code Quality
- **Confidence**: C6
- **Evidence**: `BenefitCategoryUpdateRequest.java:30` — `@NotNull(message="BENEFIT_CATEGORY.SLAB_IDS_REQUIRED") @Size(min=1)` on `slabIds`; however the class has `@JsonIgnoreProperties(ignoreUnknown=true)` (line 20) and Jackson's default behaviour is to leave absent fields as `null`. The `@NotNull` annotation fires only if Spring MVC `@Valid` is active AND Bean Validation is applied. Controller `BenefitCategoriesV3Controller.java:57` passes `@Valid @RequestBody BenefitCategoryUpdateRequest request` — the `@Valid` annotation is present, so Bean Validation does fire.

  **Revised assessment**: This is NOT a blocker. `@Valid` is on line 57 of the controller, which correctly triggers Bean Validation including `@NotNull`. The prior concern evaporates on reading the controller.

  **Downgrade to NOTE** — see R-04.

> **Auto-correction**: R-01 downgraded after evidence review; replaced below with an actual blocker.

---

### R-01: D-60 name-uniqueness semantics diverge between CREATE and ACTIVATE paths

- **Severity**: BLOCKER
- **Category**: Requirements / Session Memory
- **Confidence**: C6
- **Evidence**:
  - CREATE path (`PointsEngineRuleService.java:4503-4511`) uses `findByProgramAndName` — blocks if ANY row (active OR inactive) exists with this name. Correct per D-60.
  - ACTIVATE path (`PointsEngineRuleService.java:4771-4782`) uses `findByProgramAndNameExceptId` — blocks if ANY row (active OR inactive) OTHER THAN self exists with this name. Correct per D-34(e) + D-60.
  - UPDATE path (`PointsEngineRuleService.java:4588-4598`) uses `findByProgramAndNameExceptId` — blocks on ANY state excluding self. Correct per D-60.
  - **BUT**: `BenefitCategoryDao.java:51-55` defines `findActiveByProgramAndNameExceptId` — this is used nowhere in the production service code (grep returns 0 usages). This is dead code that is actively misleading: it checks only ACTIVE rows, which contradicts D-60's "across ALL states" requirement if ever called. A future developer could reasonably reach for it and introduce a regression.
- **Claim**: Dead DAO method `findActiveByProgramAndNameExceptId` contradicts D-60 semantics if called. Its presence creates a maintenance hazard.
- **Recommendation**: Either add a Javadoc `@deprecated DO NOT USE — violates D-60` comment, or remove it if no test uses it. A quick grep confirms it is not exercised by any test.
- **Suggested routing**: [R] Developer — add `@deprecated` comment or remove method.

---

### R-02: `BenefitCategoryCreateRequest` contains an unused `@Max` import

- **Severity**: WARNING
- **Category**: Code Quality
- **Confidence**: C7
- **Evidence**: `BenefitCategoryCreateRequest.java:7` — `import jakarta.validation.constraints.Max;` — this annotation is imported but not used on any field in the file. The `programId` field has `@Min(1)` only, with no `@Max`.
- **Claim**: Unused import; may cause compiler warnings in strict lint configurations; suggests a vestige of a removed field constraint.
- **Recommendation**: Remove the unused `import jakarta.validation.constraints.Max;` line.
- **Suggested routing**: [R] Developer — one-line cleanup.

---

### R-03: `slab not in program` returns HTTP 400, but D-28 / ADR-009 documented 409 for slab validation failures

- **Severity**: WARNING
- **Category**: Requirements / Code Quality
- **Confidence**: C5
- **Evidence**:
  - `PointsEngineRuleService.java:4846-4848` — `validateSlabsBelongToProgram` throws with `setStatusCode(400)` for an unknown/cross-program slab.
  - ADR-009 (session-memory.md §Per-Feature ADRs): error codes `BC_UNKNOWN_SLAB` and `BC_CROSS_PROGRAM_SLAB` both listed as → 409.
  - Designer `§E` (session-memory.md §Designer Phase 7): same mapping — `BC_CROSS_PROGRAM_SLAB → 409`, `BC_UNKNOWN_SLAB → 409`.
  - `TargetGroupErrorAdvice.java:347-351`: the `BenefitCategoryBusinessException` handler maps `statusCode=400` → `BAD_REQUEST` correctly, so the HTTP status produced is 400 when service throws `setStatusCode(400)`.
- **Claim**: The service emits HTTP 400 for slab-not-in-program, but ADR-009 + Designer §E specified 409. This is a semantic deviation: 400 means "bad request payload"; 409 means "business conflict". The distinction matters for API consumers who need to distinguish validation failures from conflict conditions.
- **Recommendation**: Align with ADR-009 — change `validateSlabsBelongToProgram`'s `setStatusCode(400)` to `setStatusCode(409)` for cross-program and unknown-slab cases. Alternatively, raise a follow-up D-63 deviation log if the team intentionally chose 400.
- **Suggested routing**: [R] Developer — or accept as deviation with explicit D-63 log.

---

### R-04: `BenefitCategoryUpdateRequest.slabIds` is `@NotNull` with no optional-update path (NOTE)

- **Severity**: NOTE
- **Category**: Code Quality
- **Confidence**: C6
- **Evidence**: `BenefitCategoryUpdateRequest.java:30-32` — `@NotNull @Size(min=1)` on `slabIds`; the class Javadoc says "All fields optional — only non-null fields are applied". But `slabIds` is annotated `@NotNull`, so clients MUST always send `slabIds` on a PUT even if they only want to rename the category.
- **Claim**: This is a deliberate D-46 decision (session-memory.md §Phase 8 Question Resolutions), not a bug. Documenting as NOTE for API consumer awareness. The `/api-handoff` doc should explicitly state "slabIds is required on every PUT even for name-only updates".
- **Suggested routing**: [A] Accept — D-46 is a confirmed product decision. Flag for `/api-handoff` doc update.

---

### R-05: UTC timezone not explicitly set on `Date` conversions in `BenefitCategoryResponseMapper` (G-01)

- **Severity**: WARNING
- **Category**: Security / Guardrails
- **Confidence**: C5
- **Evidence**:
  - `BenefitCategoryResponseMapper.java:41-47` — `new Date(thriftDto.getCreatedOn())` converts Thrift `i64` epoch millis → `java.util.Date`.
  - `java.util.Date` stores epoch millis internally; `new Date(millis)` is UTC-correct. Jackson then serialises it via `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` on `BenefitCategoryResponse.java:29`.
  - `@JsonFormat` without an explicit `timezone` attribute uses Jackson's `ObjectMapper` default timezone, which is the JVM default timezone. If the JVM default is IST (+05:30), the output will be `2026-04-18T15:30:45+05:30` — not UTC.
  - OQ-38 (session-memory.md §Open Questions) flags this: "JVM default timezone in production — is it UTC or IST? … If IST, EMF Thrift handler MUST explicitly force UTC."
  - D-24 / C-31 states: "All `Date ↔ i64` conversions … MUST use explicit UTC TimeZone." The mapper is a conversion boundary.
- **Claim**: The `@JsonFormat` pattern `yyyy-MM-dd'T'HH:mm:ssXXX` will produce timezone-offset-local strings, not necessarily UTC, depending on JVM TZ. If production JVM is IST, API consumers get IST-offset timestamps. G-01.6 requires ISO-8601 with timezone (satisfied by the pattern), but G-01.1 requires UTC storage and G-01.2 says conversion to local happens only at the presentation layer. If the intent is UTC output, add `timezone = "UTC"` to both `@JsonFormat` annotations.
- **Recommendation**: Add `timezone = "UTC"` on `@JsonFormat(pattern="...", timezone="UTC")` to both `createdOn` and `updatedOn` in `BenefitCategoryResponse.java`, OR wait for Q-SDET-08 UI team sign-off (D-52) and adjust once the UI team confirms the expected format.
- **Suggested routing**: [M] Manual — requires OQ-38 production JVM TZ confirmation + Q-SDET-08 UI sign-off (both deferred per D-52). Not a regression but a risk if JVM is non-UTC.

---

### R-06: `java.util.Date` used in response DTO violates G-01.3 literal

- **Severity**: WARNING (accepted deviation — informational)
- **Category**: Guardrails
- **Confidence**: C7
- **Evidence**: `BenefitCategoryResponse.java:8,29,34` — `import java.util.Date`; fields typed `private Date createdOn / updatedOn`.
- **Claim**: G-01.3 prohibits `java.util.Date`. However, this is an **accepted deviation** per D-24 (three-boundary pattern) and C-23' — `java.util.Date` is used internally in emf-parent entities (`BenefitCategory.java:57-64`) and in the REST DTO for Jackson serialisation. The pattern-match to `Benefits.java` (P-01) and the explicit `@JsonFormat` mitigation are documented.
- **Recommendation**: Document in the existing ADR-008 comment that the DTO also carries `Date` for Jackson compatibility, and that G-01.3 is accepted within this boundary per D-24.
- **Suggested routing**: [A] Accept — already covered by D-24 / ADR-008. Informational only.

---

### R-07: `BT-022b` (`?isActive=foo` → VALIDATION_FAILED) maps to HTTP 400 in test but platform OQ-45 quirk sends `NotFoundException` → HTTP 200

- **Severity**: NOTE
- **Category**: Requirements
- **Confidence**: C5
- **Evidence**:
  - `BenefitCategoryListIT::bt038_listBenefitCategories_isActiveUnparsable_returns400` (line 134-139) correctly asserts HTTP 400 for `?isActive=foo`.
  - This path is handled by the **controller-scoped** `@ExceptionHandler(MethodArgumentTypeMismatchException.class)` at `BenefitCategoriesV3Controller.java:135-145`, which returns `ResponseEntity.status(HttpStatus.BAD_REQUEST)` — NOT routed to `TargetGroupErrorAdvice`.
  - The OQ-45 `NotFoundException → HTTP 200` quirk does NOT apply here because `MethodArgumentTypeMismatchException` is caught before `NotFoundException` could ever be thrown.
- **Claim**: Correct — no issue. The 400 assertion in BT-038 is accurate. Documenting as NOTE for future maintainers who might be confused by the layering.
- **Suggested routing**: [A] Accept — correct implementation.

---

## GUARDRAILS Compliance

| Guardrail | Status | Evidence |
|---|---|---|
| **G-01 — Timezone (CRITICAL)** | WARN | D-24 three-boundary pattern accepted; `@JsonFormat(pattern=..., timezone NOT specified)` on response DTO (R-05). JVM TZ confirmation (OQ-38) deferred to Phase 12. G-01.7 multi-TZ tests present: `BenefitCategoryGuardrailIT::btG01b` (UTC / IST / PST via `TimezoneRule`). |
| **G-03 — Security (CRITICAL)** | PASS | Bean Validation on all `@RequestBody` DTOs: `@NotNull`, `@NotBlank`, `@Size`, `@Min` applied on `BenefitCategoryCreateRequest.java` and `BenefitCategoryUpdateRequest.java`. No SQL string concatenation — all JPQL via `@Query` with named `@Param`. No PII logged (orgId + categoryId + programId only in logs). |
| **G-07 — Multi-Tenancy (CRITICAL)** | PASS | Every DAO query includes explicit `orgId` WHERE clause (`BenefitCategoryDao.java:31-110`, `BenefitCategorySlabMappingDao.java:27-67`). Tenant isolation IT: `BenefitCategoryGuardrailIT::btG07` asserts orgId propagates to Thrift filter on all 6 endpoints. |
| **G-12 — AI-Specific (CRITICAL)** | PASS | All patterns verified against existing codebase exemplars (Benefits.java P-01, BenefitsDao P-02, TargetGroupController P-05). No hallucinated APIs — `javap` verification of Thrift IDL done (D-53a). No new dependencies introduced without approval (`1.84-SNAPSHOT-dev` was explicitly user-approved). |
| G-02 — Null Safety (HIGH) | PASS | `dto == null` guards at service entry (`PointsEngineRuleService.java:4479`). Optional usage on DAO lookups with `.orElseThrow()` chains. `findByOrgIdAndId` returns `Optional<BenefitCategory>`. |
| G-04 — Performance (HIGH) | PASS | N+1 addressed: bulk `findActiveSlabIdsForCategories` (session-memory §backend-readiness 1.1). `saveAndFlush` in slab loop is a W1 accepted warning (≤10 slabs per D-26). Pagination enforced with `BC_PAGE_SIZE_EXCEEDED`. |
| G-05 — Data Integrity (HIGH) | PASS | Cascade deactivation is `@Transactional(warehouse, REQUIRED)` — C-29 / ADR-004. No optimistic lock accepted per ADR-001 / D-33. |
| G-06 — API Design (HIGH) | PASS (partial) | Structured error responses via `ResponseWrapper.ApiError`. HTTP 201 for create, 200/204 for activate, 204 for deactivate. R-03 flags a 400 vs 409 semantic deviation for slab errors. |
| G-08 — Observability (HIGH) | PASS | Structured logs with `orgId`, `id`, `programId`, `slabCount` at INFO level (`PointsEngineRuleService.java:4547-4550`). SLF4J 1.6.4 workaround (3+ args via `String.format`) used correctly per D-59. |
| G-09 — Backward Compatibility (HIGH) | PASS | All Thrift structs additive only; no existing field IDs changed (`backend-readiness.md §2`). No legacy table modified. |
| G-10 — Concurrency (HIGH) | PASS (deviation accepted) | No `@Version` per D-33 / ADR-001 — last-write-wins. Race on name-create accepted per D-38. BT-G10 tests LWW behaviour explicitly. |
| G-11 — Testing (HIGH) | PASS | 76 tests (36 UT + 40 IT) GREEN. Testcontainers real MySQL for ITs. Tenant isolation test present (G-11.8). Timezone multi-TZ test present (G-11.7). Idempotency tested (BT-048, BT-055). |

---

## Code Quality Highlights

### Positives

1. **Pattern fidelity** — Entity, DAO, service, ThriftImpl, and controller all follow the exemplars precisely (P-01 through P-17). The `BenefitCategory.java` entity mirrors `Benefits.java` down to the `@Embeddable` PK inner class and hand-written getters. This preserves future developer orientation.

2. **Error boundary clarity** — `BenefitCategoryBusinessException` inner class wrapping the checked `PointsEngineRuleServiceException` is a clean design. The exception carries `statusCode` and `errorMessage` verbatim; the `TargetGroupErrorAdvice` switch reads these without reflection gymnastics (`TargetGroupErrorAdvice.java:345-357`).

3. **D-43 stateChanged sentinel** — the activate no-op path is correct and tested end-to-end. `stateChanged=false` on the Thrift DTO travels up through the mapper, through the facade's Optional check, and the controller correctly emits 204 with no body (`BenefitCategoriesV3Controller.java:112-114`). The null-clearing on non-activate paths (`BenefitCategoryFacade.java:48,69,87`) prevents `stateChanged` from leaking into unrelated responses.

4. **Controller-scoped `MethodArgumentTypeMismatchException` handler** — surgical fix (`BenefitCategoriesV3Controller.java:135-145`) avoids the global advice misrouting `?isActive=foo` to 500. Well-contained; does not affect other controllers.

5. **Comprehensive IT guardrail coverage** — `BenefitCategoryGuardrailIT.java` covers UTC/IST/PST timezone invariant, tenant-isolation orgId propagation, and LWW concurrency in a single file with clear BT annotations.

### Improvement Suggestions

1. **R-01** (dead DAO method) — annotate or remove `findActiveByProgramAndNameExceptId` with `@deprecated DO NOT USE — D-60 requires cross-all-states check; use findByProgramAndNameExceptId`.

2. **R-02** (unused import) — remove `import jakarta.validation.constraints.Max` from `BenefitCategoryCreateRequest.java`.

3. **R-03** (slab error HTTP 400 vs ADR-009 409) — align `validateSlabsBelongToProgram` status code with the agreed ADR-009 error contract.

4. **Logging consistency** — `PointsEngineRuleService.java:4799` uses SLF4J 2-arg directly (`logger.info("...{}{}", orgId, id)`) while 3+-arg calls correctly use `String.format`. The 2-arg case is fine for SLF4J 1.6.4 (2-arg is in scope). No issue.

---

## Summary Recommendation

**Verdict: APPROVED WITH WARNINGS**

The feature is functionally complete, well-tested (76 tests GREEN), and aligned with all 10 in-scope requirements. Session memory decisions D-01..D-62 are honoured. Critical guardrails G-03, G-07, and G-12 pass cleanly.

**One blocker requires resolution before merge**:
- **R-01**: Dead DAO method `findActiveByProgramAndNameExceptId` contradicts D-60 if called; add `@deprecated` comment or remove.

**Five warnings that should be addressed soon**:
- **R-02**: Remove unused `@Max` import in `BenefitCategoryCreateRequest`.
- **R-03**: Slab validation throws HTTP 400 but ADR-009 specifies 409 for `BC_UNKNOWN_SLAB` / `BC_CROSS_PROGRAM_SLAB`.
- **R-05**: `@JsonFormat` on response DTO lacks `timezone="UTC"` — risk if JVM default is not UTC (OQ-38 open). Pending UI team D-52 sign-off.
- **R-06**: `java.util.Date` in response DTO is G-01.3 deviation — accepted per D-24, should be noted in ADR-008.
- **W5 / F-02** (from backend-readiness, not re-flagged): `@PostMapping` vs `@PatchMapping` for activate/deactivate — confirmed as D-61 accepted deviation.

**Open question to confirm before prod deploy**:
- Q-SDET-08: UI team confirmation on `yyyy-MM-dd'T'HH:mm:ssXXX` date format (D-52 code-side locked, pending external sign-off).
- OQ-38: Production JVM default timezone confirmation for R-05 risk assessment.

**Next step**: Route R-01 and R-02 and R-03 to Developer for resolution, then re-review these three items. All other items are non-blocking.

---

## Unresolved BRD Questions (impact check)

| Question | Status | Impact on This Feature |
|---|---|---|
| OQ-4: AC-BC04/05/06 missing in BRD | Open | No impact — those ACs are absent from the implemented scope |
| OQ-12: Epic numbering E2 vs E4 | Open | No engineering impact |
| OQ-38: JVM default TZ in prod | Open | R-05 risk — affects ISO-8601 offset in API responses |
| Q-SDET-08: UI team D-45 format confirmation | Open | R-05 risk — affects date format contract |
| Q-BT-01: BT-067 emf-parent Thrift+MySQL IT | Deferred (D-58 / tracked follow-up) | Not blocking merge; separate IT harness |
| Q-BT-02: Timezone isolation | Resolved by D-51 (`TimezoneRule`) | RESOLVED |
