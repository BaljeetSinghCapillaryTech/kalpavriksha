# Gap Analysis — Architecture vs Code (CAP-185145)

> Phase 10c audit · 2026-04-19 · /analyst --compliance

---

## Verdict

**NOT READY (3 known Phase 10b blockers are M-fix pending + 3 new findings: 1 HIGH, 2 MEDIUM)**

---

## Summary

| Metric | Value |
|--------|-------|
| ADRs checked | 13/13 |
| Frozen decisions checked | 28 (D-33..D-60) |
| Guardrails checked | 5 (G-01, G-04, G-05, G-07, G-10) |
| PASS | 42 |
| ACCEPTED-DEVIATION | 5 (D-33/ADR-001, D-38/ADR-012, G-05.2, D-37/ADR-010, D-27a) |
| WARN | 4 |
| FAIL | 0 (Phase 10b B1/B2/B3 tracked separately) |
| New findings HIGH | 1 (HTTP verb mismatch on activate/deactivate) |
| New findings MEDIUM | 2 (mapper package, list default filter) |
| Overall confidence | C6 |

> **Phase 10b blockers B1/B2/B3** are already triaged as [M] Manual fix pending. They are noted in the accepted-deviations section with pointers, not re-raised as new findings.

---

## Per-ADR Scorecard

| ADR | Decision | Verdict | Evidence (file:line) | Severity | Confidence |
|-----|----------|---------|----------------------|----------|------------|
| ADR-001 | D-33 — no `@Version` field | PASS | `BenefitCategory.java:14` (comment), no `@Version` import or field present; `BenefitCategoryComplianceTest.java:27-39` reflection assert GREEN | — | C7 |
| ADR-002 | D-34 — dedicated `PATCH /activate`; cascade mappings do NOT auto-reactivate | WARN — see F-01 | Controller uses `@PostMapping` not `@PatchMapping`; activate service correctly skips mapping reactivation (`PointsEngineRuleService.java:4739-4797`) | HIGH | C7 |
| ADR-003 | D-35 — embedded `slabIds` in parent DTO; server-side `syncSlabMappings`; no separate mapping REST resource | PASS | No `/benefitCategorySlabMappings` endpoint exists; diff-and-apply logic at `PointsEngineRuleService.java:4603-4643`; facade at `BenefitCategoryFacade.java:62-78` | — | C7 |
| ADR-004 | D-36 — `PATCH /deactivate` with cascade soft-delete in same txn | WARN — see F-01 | Verb is `@PostMapping` not `@PatchMapping`; cascade logic correct at `PointsEngineRuleService.java:4801-4828`, same `@Transactional(warehouse)` | HIGH | C7 |
| ADR-005 | 6 methods on `PointsEngineRuleConfigThriftImpl`; `@MDCData(requestId="#serverReqId")`; `@Trace` | PASS | `PointsEngineRuleConfigThriftImpl.java:4265-4349`; all 6 have `@Override @Trace(dispatcher=true) @MDCData(orgId="#orgId", requestId="#serverReqId")`; compliance test BT-084 GREEN | — | C7 |
| ADR-006 | D-39 — asymmetric: `activate` 200+DTO / `deactivate` 204; idempotent both 204 | PASS | Controller `BenefitCategoriesV3Controller.java:109-115` checks `stateChanged` flag → `noContent()` or `ok()`; deactivate always 204 at L122-129 | — | C7 |
| ADR-007 | Data model: `auto_update_time` has `insertable=false, updatable=false`; required columns present | PASS | `BenefitCategory.java:71` `insertable = false, updatable = false`; `BenefitCategorySlabMapping.java:67` same; all columns match ADR-007 schema | — | C7 |
| ADR-008 | Three-boundary timestamp: `java.util.Date` in entity, `i64` in Thrift, ISO-8601 on DTO (D-45 revised) | PASS | Entities use `java.util.Date` + `@Temporal(TIMESTAMP)` (`BenefitCategory.java:56-65`); Thrift IDL uses `i64` (L1058/1060); `BenefitCategoryResponse.java:29,34` uses `@JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX")`; no `timezone="UTC"` (D-45 revised correct) | — | C6 |
| ADR-009 | Error taxonomy: `BC_NAME_TAKEN_ACTIVE`/`BC_NAME_TAKEN_ON_REACTIVATE` → 409; `BC_NOT_FOUND` → 404; `BC_PAGE_SIZE_EXCEEDED` → 400; `BC_BAD_ACTIVE_FILTER` stricken | PASS | `TargetGroupErrorAdvice.java:342-363` implements status-code switch 409/404/400/500; `BC_BAD_ACTIVE_FILTER` not present as constant; stateChanged enum codes absent | — | C6 |
| ADR-010 | D-37 — no `@PreAuthorize` on new code | PASS | Grepped `BenefitCategoriesV3Controller.java` and `BenefitCategoryFacade.java` — zero `@PreAuthorize` occurrences | — | C7 |
| ADR-011 | Offset pagination: `page≥0`, `size` bounded (max 100); list supports `?isActive`; fixed ORDER BY | WARN — see F-03 | DAO query has `ORDER BY c.createdOn DESC, c.pk.id DESC` (`BenefitCategoryDao.java:83`); **service caps at 200 not 100** (`PointsEngineRuleService.java:4695`); controller has no `@Max(100)` on size param | MEDIUM | C7 |
| ADR-012 | D-38 — no advisory lock; SELECT→INSERT race accepted | ACCEPTED-DEVIATION | No `GET_LOCK` in service; pure SELECT→INSERT at `PointsEngineRuleService.java:4503-4511` | — | C7 |
| ADR-013 | Deployment order: thrift-ifaces → cc-stack-crm → emf-parent → intouch-api-v3 | PASS | Branch structure and pom dependencies reflect correct ordering: thrift-ifaces at `1.84-SNAPSHOT-dev`, emf-parent dep at `pom.xml:192`, intouch-api-v3 dep at `pom.xml:231` | — | C5 |

---

## Per-Frozen-Decision Scorecard

| Decision | Summary | Verdict | Evidence (file:line) | Confidence |
|----------|---------|---------|----------------------|------------|
| D-33 | No `@Version` on either entity | ACCEPTED-DEVIATION (ADR-001) | `BenefitCategory.java` — no `@Version` field; compliance test asserts at runtime | C7 |
| D-34 | Dedicated `/activate`; no cascade mapping reactivation | PASS (verb WARN — F-01) | Service `activateBenefitCategory` (L4739) does NOT call `bulkSoftDeleteByCategory`/reactivate mappings — correct | C7 |
| D-35 | `slabIds` embedded; diff-and-apply in `syncSlabMappings` | PASS | `PointsEngineRuleService.java:4603-4643`; toAdd/toSoftDelete logic present; LinkedHashSet dedup in facade mapper | C7 |
| D-36 | `PATCH /deactivate` cascade in same txn | PASS (verb WARN — F-01) | `PointsEngineRuleService.java:4801-4826`; bulk cascade DELETE query; same `@Transactional(warehouse)` boundary confirmed | C7 |
| D-37 | BasicAndKey only, no `@PreAuthorize` | ACCEPTED-DEVIATION (ADR-010) | Zero `@PreAuthorize` on new code | C7 |
| D-38 | Race accepted; no advisory lock | ACCEPTED-DEVIATION (ADR-012) | No `GET_LOCK` call in codebase | C7 |
| D-39 | Asymmetric response — activate 200+DTO, deactivate 204 | PASS | `BenefitCategoriesV3Controller.java:109-129` | C7 |
| D-40 | Aurora version deferred to Phase 12 | PASS (no partial index implemented) | No `CREATE UNIQUE INDEX` in DDL | C7 |
| D-41 | Reuse `PeProgramSlabDao.findByProgram` + in-memory set ops | PASS | `PointsEngineRuleService.java:validateSlabsBelongToProgram` uses existing DAO method | C6 |
| D-42 | `GET /{id}` supports `?includeInactive=true`; default active-only | PASS | `BenefitCategoriesV3Controller.java:74`; facade branches on flag; `BenefitCategoryDao.java:31-38` two methods present | C7 |
| D-43 | `BenefitCategoryDto.stateChanged` optional bool; set only on activate | PASS | IDL `pointsengine_rules.thrift:1062` — `12: optional bool stateChanged`; facade zeros it for non-activate paths `BenefitCategoryFacade.java:48,69,87`; compliance test BT-098 rewritten | C7 |
| D-44 | JPA entities hand-written; REST DTOs use Lombok | PASS | `BenefitCategory.java` — hand-written getters/setters; `BenefitCategoryCreateRequest.java:19-20` — `@Getter @Setter` | C7 |
| D-45 revised | `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` not `timezone="UTC"` | PASS | `BenefitCategoryResponse.java:29,34` — exact pattern used; session-memory TD-SDET-07 confirms the revision | C7 |
| D-46 | `UpdateRequest.slabIds` has `@NotNull` AND `@Size(min=1)` | PASS | `BenefitCategoryUpdateRequest.java:30-32` — both annotations present | C7 |
| D-47 | Case-sensitive name uniqueness via `utf8mb4_bin` | PASS | `benefit_categories.sql:7` — `CHARACTER SET utf8mb4 COLLATE utf8mb4_bin`; DAO JPQL uses `c.name = :name` without LOWER() | C7 |
| D-48 | Invalid `?isActive=foo` → platform `VALIDATION_FAILED` (no bespoke code) | PASS | Controller declares `Boolean isActive`; `MethodArgumentTypeMismatchException` handled by controller-local `@ExceptionHandler` at `BenefitCategoriesV3Controller.java:135-145` → 400 | C7 |
| D-49 | `tillId` source = `user.getEntityId()` | PASS | `BenefitCategoriesV3Controller.java:46,62` — `(int) user.getEntityId()` | C7 |
| D-50 | BT-067 as intouch-api-v3 end-to-end IT with mocked Thrift | PASS | `BenefitCategoryITBase.java` uses `@MockBean` at Thrift boundary | C7 |
| D-51 | `TimezoneRule` BeforeEach/AfterEach capture/restore | PASS | `TimezoneRule.java` exists; used in `BenefitCategoryGuardrailIT.java` | C7 |
| D-52 | `@JsonFormat` pattern locked; UI sign-off deferred to Phase 11 | PASS | Pattern locked in code; Q-SDET-08 in session-memory for Phase 11 | C5 |
| D-53a | 6 methods on `PointsEngineRuleService.Iface` (no sub-interface) | PASS | IDL generates methods on `Iface`; `PointsEngineRuleConfigThriftImpl implements PointsEngineRuleService.Iface` at L113; `PointsEngineRuleEditor.java:519-535` has 6 method signatures | C7 |
| D-54 | Editor interface gets 6 new method declarations | PASS | `PointsEngineRuleEditor.java:518-535` confirms all 6 declared on interface | C7 |
| D-55 | `BenefitCategoryBusinessException` as static inner class on Facade | PASS | `BenefitCategoryFacade.java:167-179` — static inner class; `TargetGroupErrorAdvice.java:342` handles it | C7 |
| D-56 | Controller-scoped `@ExceptionHandler(MethodArgumentTypeMismatchException.class)` → 400 | PASS | `BenefitCategoriesV3Controller.java:135-145` — scoped `@ExceptionHandler` present | C7 |
| D-57 | Facade test file kept GREEN (no rename) | PASS | `BenefitCategoryFacadeRedTest.java` exists; session-memory records GREEN flip | C6 |
| D-58 | intouch-api-v3 IT uses `@MockBean` at Thrift boundary | PASS | `BenefitCategoryITBase.java` uses `@MockBean PointsEngineRulesThriftService` | C7 |
| D-59 | emf-parent runs on Java 8; SLF4J 1.6.4; Spring Data 1.x — all handled | PASS | `PointsEngineRuleService.java` uses `String.format` for multi-arg logs; `new PageRequest(page, size)` at L4702; build success confirmed in session-memory M3a | C7 |
| D-60 | CREATE/UPDATE/ACTIVATE all use all-states name lookup (`findByProgramAndName` not `findActiveByProgramAndName`) | PASS | `PointsEngineRuleService.java:4506` (CREATE), `4591` (UPDATE exceptId), `4767-4778` (ACTIVATE all-states guard) | C7 |
| D-27a | PUT on inactive returns 404 (not 409 as D-27 original) — drift accepted | ACCEPTED-DEVIATION | `PointsEngineRuleService.java` uses `findActiveById` as guard (returns empty → 404); user decision in M4 (session-memory §D-27a) | C6 |

---

## Per-GUARDRAIL Scorecard

| Guardrail | Description | Verdict | Evidence (file:line) | Confidence |
|-----------|-------------|---------|----------------------|------------|
| G-01 | Timezone — `java.time`, UTC, ISO-8601 | PASS (with deviation) | Entities use `java.util.Date` (platform convention per ADR-008 G-12.2 resolution); DTO uses `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` at `BenefitCategoryResponse.java:29,34`; mapper converts millis↔Date correctly. G-01.3 technically violated internally per ADR-008 trade-off; accepted. | C6 |
| G-04 | Pagination: always bounded; no N+1 | PASS with WARN | Pagination present; bulk slab fetch `findActiveSlabIdsForCategories` at `BenefitCategorySlabMappingDao.java:38` avoids N+1; **size cap is 200 in service vs 100 in design** (F-03 below) | C7 |
| G-05 | Data integrity: transactions, constraints | PASS (G-05.2 accepted deviation) | Cascade deactivate in same `@Transactional(warehouse)` (`PointsEngineRuleService.java:4801`); G-05.2 `@Version` — ACCEPTED-DEVIATION per D-33/ADR-001 | C7 |
| G-07 | Multi-tenancy: `orgId` in every query | PASS | All `@Query` in `BenefitCategoryDao.java` and `BenefitCategorySlabMappingDao.java` include `:orgId` filter; facade propagates `orgId` from `IntouchUser.getOrgId()` on every call; IT `BenefitCategoryGuardrailIT` asserts tenant isolation | C7 |
| G-10 | Concurrency — no advisory lock; last-write-wins | ACCEPTED-DEVIATION | No `GET_LOCK`; accepted per D-33/D-38; last-write-wins confirmed; revisit triggers logged in ADR-001/ADR-012 | C7 |

---

## New Findings

### F-01 — HIGH: `/activate` and `/deactivate` use `@PostMapping` instead of `@PatchMapping`

**ADR reference**: ADR-002 (D-34) and ADR-004 (D-36).

**Design**: `PATCH /v3/benefitCategories/{id}/activate` and `PATCH /v3/benefitCategories/{id}/deactivate` — explicitly stated in `03-designer.md §B.5` (`@PatchMapping("/{id}/activate")`) and `§B.6` (`@PatchMapping("/{id}/deactivate")`); `01-architect.md` ADR-002 and ADR-004 REST verb is `PATCH`.

**Code**: `BenefitCategoriesV3Controller.java:104` uses `@PostMapping(path = "/{id}/activate")`; L122 uses `@PostMapping(path = "/{id}/deactivate")`.

**Impact**: REST clients calling the correct `PATCH` verb will receive HTTP 405 Method Not Allowed instead of the expected response. This is a **breaking contract violation** — the API handoff document will document `PATCH` but the server only accepts `POST`. The behavior itself (state transitions, response bodies) is correct; only the HTTP method binding is wrong.

**Phase 10b reference**: Not previously tracked in B1/B2/B3 — this is a new finding.

**Severity**: HIGH — interface contract mismatch; API handoff integrity broken.

**Confidence**: C7 — direct read of annotation at `BenefitCategoriesV3Controller.java:104,122` vs designer spec at `03-designer.md:405,456`.

**Fix**: Change `@PostMapping` to `@PatchMapping` on both endpoints. One-line change per method.

---

### F-02 — MEDIUM: `BenefitCategoryResponseMapper` is in wrong package

**ADR reference**: D-45 / C-36.

**Design**: D-45 mandates mapper in `com.capillary.intouchapiv3.facade.benefitCategory.mapper` subpackage (exemplar: `CustomerPromotionResponseMapper`). `session-memory.md §Designer Phase 7 — Q7-15` explicitly resolved: "dedicated `BenefitCategoryResponseMapper` in `com.capillary.intouchapiv3.facade.benefitCategory.mapper`".

**Code**: mapper lives at `com.capillary.intouchapiv3.models.dtos.benefitcategory.BenefitCategoryResponseMapper` (`src/main/java/com/capillary/intouchapiv3/models/dtos/benefitcategory/BenefitCategoryResponseMapper.java`).

**Impact**: Architectural boundary — mapper has access to both Thrift and REST types but is co-located with DTOs rather than the facade layer. No runtime bug. Violates the layered boundary prescribed in D-45: mapper belongs with the facade (consumer of both Thrift DTOs and REST DTOs), not in the DTO model package.

**Severity**: MEDIUM — package placement; no functional gap.

**Confidence**: C7 — direct file path vs D-45 spec.

---

### F-03 — MEDIUM: List endpoint `size` cap is 200 in service; design specifies 100 with `BC_PAGE_SIZE_EXCEEDED`

**ADR reference**: ADR-011.

**Design**: `ADR-011` — `max 100` enforced at controller; exceeding → HTTP 400 `BC_PAGE_SIZE_EXCEEDED`. `03-designer.md:351` — `@Max(100) int size`. `04b-business-tests.md` lists `BC_PAGE_SIZE_EXCEEDED` as a covered error code.

**Code**:
- Controller (`BenefitCategoriesV3Controller.java:92`): `@RequestParam(name = "size", defaultValue = "20") int size` — no `@Max(100)` annotation.
- Service (`PointsEngineRuleService.java:4695`): `if (size > 200) size = 200` — silently clamps at 200, does not throw.
- No `BC_PAGE_SIZE_EXCEEDED` error thrown anywhere.

**Impact**: Callers can request up to 200 rows without any error; the design-mandated 400 guard is missing. The D-26 SMALL-scale cap of ≤50 categories per program means this is unlikely to matter in practice, but the ADR-011 contract is not enforced.

**Severity**: MEDIUM — contract mismatch on validation boundary; no security impact.

**Confidence**: C7 — direct read of `PointsEngineRuleService.java:4695` vs ADR-011 text.

---

### F-04 — WARN: List endpoint default filter (`isActive` unset) returns ALL categories instead of active-only

**ADR reference**: ADR-011.

**Design**: ADR-011 — `isActive=all` returns active+inactive; **default = active only**.

**Code**:
- Controller (`BenefitCategoriesV3Controller.java:90`): `@RequestParam(name = "isActive", required = false) Boolean isActive` — when not provided, `isActive = null`.
- Facade (`BenefitCategoryFacade.java:108`): `if (isActive != null) filter.setActiveOnly(isActive)` — null → `activeOnly` not set.
- Service (`PointsEngineRuleService.java:4699`): `Boolean isActive = (filter.isSetActiveOnly() && filter.isActiveOnly()) ? Boolean.TRUE : null` — returns `null` (all states) when not set.
- DAO (`BenefitCategoryDao.java:80`): `(:isActive IS NULL OR c.isActive = :isActive)` — null means no filter → returns inactive AND active rows.

**Impact**: When a client calls `GET /v3/benefitCategories` without `?isActive=...`, the design says return active-only, but the implementation returns all. Functional default behavior gap. Note: passing `?isActive=true` works correctly; only the no-param default is wrong.

**Note on D-48**: D-48's decision to use `Boolean` (not `String "true|false|all"`) for `?isActive` changed the default mechanism. The Designer's original `defaultValue="true"` (String → "true") was replaced by `required=false Boolean` (null). The null-branch was not hooked to the active-only default path.

**Severity**: WARN — behavioral gap; no security impact; D-26 scale means most callers likely pass `?isActive=true` explicitly, but the default contract is wrong.

**Confidence**: C6 — code trace is clear; could be intentional if the team decided null = no filter is acceptable (but D-48 doesn't say that explicitly).

---

## Critical Gaps (FAIL — blocking Phase 11)

None newly found. B1/B2/B3 from Phase 10b are the existing blockers (see below).

---

## High Gaps (HIGH — should fix before Phase 11)

| # | Finding | Fix Required |
|---|---------|-------------|
| F-01 | `/activate` and `/deactivate` use `@PostMapping` instead of `@PatchMapping` | Change `@PostMapping` → `@PatchMapping` on both endpoints in `BenefitCategoriesV3Controller.java:104,122` |

---

## Medium/Warn Gaps (MEDIUM/WARN — document or fix)

| # | Finding | Recommendation |
|---|---------|---------------|
| F-02 | Mapper in wrong package (`models/dtos/benefitcategory` vs `facade/benefitCategory/mapper`) | Move `BenefitCategoryResponseMapper.java` to the specified package; update imports in `BenefitCategoryFacade.java` |
| F-03 | Size cap is 200 not 100; no `BC_PAGE_SIZE_EXCEEDED` thrown | Add `@Max(100)` to controller param; add size-guard in facade or service throwing appropriate exception |
| F-04 | Default `isActive` (absent param) returns all categories; design says active-only | Set `defaultValue = "true"` on `@RequestParam` OR add null-check in facade: `if (isActive == null) filter.setActiveOnly(true)` |

---

## Phase 10b Tracked Blockers (M-fix pending — not re-raised)

| Blocker | Description | Tracked in |
|---------|-------------|-----------|
| B1 | Missing `idx_bc_org_program_name` index on `benefit_categories` production DDL | `backend-readiness.md §Blockers` |
| B2 | `CREATE TABLE` without `IF NOT EXISTS` in both production DDL files | `backend-readiness.md §Blockers` |
| B3 | `BenefitCategoryResponse.active` JSON key must be `isActive` (via `@JsonProperty`) | `backend-readiness.md §Blockers` |

---

## Accepted Deviations (documented, non-blocking)

| ADR / Decision | Deviation | Rationale | Revisit trigger |
|----------------|-----------|-----------|-----------------|
| ADR-001 / D-33 | No `@Version` on entities; last-write-wins | D-26 SMALL scale (<1 QPS writes, single admin) makes race window functionally unreachable | Admin-write QPS > 10/s, multi-editor UI ships, or "concurrent-write-conflict" incident |
| ADR-012 / D-38 | No advisory lock; SELECT→INSERT uniqueness race accepted | D-26 scale; advisory lock ceremony > probable harm | ≥1 real duplicate incident; admin write QPS > 5/s |
| D-37 / ADR-010 | No `@PreAuthorize`; BasicAndKey only | Platform convention for write endpoints; admin gate deferred to separate epic | Admin-only UX requirement raised |
| G-05.2 | No `@Version` / optimistic locking (see ADR-001/D-33) | Same as ADR-001 | Same as ADR-001 |
| ADR-008 / G-01.3 | `java.util.Date` in entities + Thrift (not `java.time`) | G-12.2 platform pattern match: `Benefits.java`, `ProgramSlab.java`; external REST contract IS ISO-8601 per G-01.6 | Platform-wide migration to `java.time` |
| D-27a | PUT on inactive returns 404 not 409 (drift from D-27 original) | `findActiveById` guard returns empty for both missing AND inactive rows; two-step lookup has no user benefit; user accepted in M4 | If admin tooling needs explicit "forbidden on inactive" error |

---

## Suggested ArchUnit Rules for CI Enforcement

```java
// Rule 1 — ADR-001: No @Version on benefit-category entities
@ArchTest
public static final ArchRule no_version_on_benefit_category =
    noFields().that().areDeclaredInClassesThat()
        .resideInAPackage("..benefitcategory..")
        .should().beAnnotatedWith(javax.persistence.Version.class)
        .because("ADR-001 / D-33: benefit-category entities must not use optimistic locking");

// Rule 2 — G-07: All JPQL on DAO classes in benefitcategory.dao package must carry :orgId
@ArchTest
public static final ArchRule all_benefit_category_dao_jpql_must_carry_orgId =
    methods().that().areDeclaredInClassesThat()
        .resideInAPackage("..benefitcategory.dao..")
        .and().areAnnotatedWith(org.springframework.data.jpa.repository.Query.class)
        .should(haveQueryContainingOrgIdParam())
        .because("G-07.1: every DAO query on benefit-category tables must include tenant orgId filter");

// Rule 3 — ADR-010: No @PreAuthorize on BenefitCategory controller or facade
@ArchTest
public static final ArchRule no_preauthorize_on_benefit_category_code =
    noMethods().that().areDeclaredInClassesThat()
        .haveSimpleNameContaining("BenefitCategory")
        .should().beAnnotatedWith(
            org.springframework.security.access.prepost.PreAuthorize.class)
        .because("ADR-010 / D-37: BasicAndKey auth only; no @PreAuthorize in MVP");

// Rule 4 — D-45: Mapper must live in facade layer, not models/dtos
@ArchTest
public static final ArchRule mapper_in_facade_package =
    classes().that().haveSimpleNameEndingWith("Mapper")
        .and().resideInAPackage("..benefitcategory..")
        .should().resideInAPackage("..facade..")
        .because("D-45: BenefitCategoryResponseMapper belongs in facade layer, not models/dtos");
```

---

## Assumptions Made

1. **C5** — The `@PostMapping` vs `@PatchMapping` finding (F-01) was not previously identified in Phase 10b backend-readiness or session-memory; it is a new finding. Confidence that this is an actual contract violation (not intentional) is C7 — PATCH is explicitly called out in both ADR-002, ADR-004, and Designer §B.5/B.6.

2. **C6** — The list-endpoint default filter behavior (F-04) is a real behavioral drift. It is possible the team intentionally changed the default to "no filter" when switching from `String isActive` to `Boolean isActive` (D-48 migration), but D-48 only specifies handling of invalid values — it does not change the default.

3. **C5** — ADR-013 deployment ordering has not been verified against actual CI pipeline configuration; the pom dependency ordering is correct but the actual Jenkins deploy sequence is assumed to match.

---

## Questions for User

| # | Question | Impact | Confidence before answer |
|---|---------|--------|--------------------------|
| Q1 | **F-01 fix scope**: Should the `@PostMapping → @PatchMapping` fix be applied in this ticket before Phase 11, or is the current `@PostMapping` intentional (e.g., some API clients or gateway already hardcoded to POST)? | HIGH — blocks API contract purity | C4 on intent |
| Q2 | **F-04 default behavior**: Is `?isActive` absent → return ALL categories an acceptable default (user-facing API change), or must it default to active-only per ADR-011? | MEDIUM — functional default gap | C4 on intent |
| Q3 | **F-03 size cap**: Should `BC_PAGE_SIZE_EXCEEDED` be implemented (reject >100 with 400) before Phase 11, or is the silent 200-cap acceptable given D-26 scale? | LOW-MEDIUM — contract enforcement | C5 on importance |

---

## Recommendation

**NOT READY for Phase 11** as-is. Required before merge:

1. **[HIGH — F-01]** Fix `@PostMapping` → `@PatchMapping` on `/activate` and `/deactivate` in `BenefitCategoriesV3Controller.java:104,122`. Single-line change per endpoint; update corresponding ITs (`BenefitCategoryActivateIT` and `BenefitCategoryDeactivateIT`) to use `PATCH` verb.
2. **[M-fix — B1]** Add `idx_bc_org_program_name` index to `cc-stack-crm` production DDL (tracked from Phase 10b).
3. **[M-fix — B2]** Add `IF NOT EXISTS` to both production `CREATE TABLE` statements.
4. **[M-fix — B3]** Fix `BenefitCategoryResponse.active` JSON serialization to `"isActive"` via `@JsonProperty`.

Once F-01 + B1/B2/B3 are resolved, proceed to Phase 11 (Reviewer). F-02 (mapper package), F-03 (size cap), and F-04 (default filter) are MEDIUM/WARN — defer to a follow-up if time-pressed, but document as known technical debt.
