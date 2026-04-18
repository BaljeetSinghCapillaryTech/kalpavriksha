# 03 — Designer (LLD) — Benefit Category CRUD (CAP-185145)

> **Phase**: 7 (LLD) — Designer
> **Ticket**: CAP-185145
> **Date**: 2026-04-18
> **Inputs (frozen)**: `01-architect.md` (ADR-001..013, post-HLD amendments D-37..D-40), `session-memory.md` (D-01..D-40, C-01..C-34), `code-analysis-emf-parent.md`, `code-analysis-intouch-api-v3.md`, `code-analysis-thrift-ifaces.md`, `cross-repo-trace.md`, `.claude/skills/GUARDRAILS.md`, `.claude/principles.md`.
> **Scope**: Interface signatures only — no implementation bodies. Compile-safe for Phase 9 SDET to generate RED-phase skeletons + tests.
> **Hard constraints honoured**: D-33 (no `@Version`), D-34 (dedicated `/activate`), D-35 (embedded `slabIds` + diff-apply), D-36 (dedicated `/deactivate` + cascade), D-37 (BasicAndKey, no `@PreAuthorize`), D-38 (no advisory lock), D-39 (asymmetric `/activate` → `Optional<DTO>`), D-40 (Aurora version deferred), C-32/C-33/C-34.

---

## 0. How to read this document

- Every type declaration carries: `package`, `base class / interface`, `annotations` (in exact declaration order), imports worth surfacing, and compile-safe method signatures.
- Every signature carries **Confidence (C1–C7)** + **Evidence anchor** (path or exemplar class).
- No method bodies. SDET Phase 9 writes skeleton bodies that throw `UnsupportedOperationException("not impl")` to compile and fail tests RED.
- Whenever a decision is <C5 it is surfaced in §G **Open Questions for User**. C5+ stylistic choices are recorded in §G **Assumptions Made**.

---

## A. Layered Inventory

Full type list, grouped by repo → layer. Types flagged **[NEW]** are created in this phase; **[MODIFIED]** are existing files receiving additions only.

### A.1 `thrift-ifaces-pointsengine-rules` (IDL + generated code)

| # | Type | Status | Path / File | Notes |
|---|------|--------|-------------|-------|
| 1 | `BenefitCategoryType` (enum) | [NEW] | `src/main/thrift/pointsengine_rules.thrift` | enum { BENEFITS = 1 } |
| 2 | `BenefitCategoryDto` (struct) | [NEW] | same | i32 id/orgId/programId/createdBy, string name, list<i32> slabIds, bool isActive, i64 createdOn/updatedOn (D-24 naming). |
| 3 | `BenefitCategoryFilter` (struct) | [NEW] | same | orgId, optional programId, optional isActive. |
| 4 | `BenefitCategoryListResponse` (struct) | [NEW] | same | data + page + size + total. |
| 5 | `PointsEngineRuleService` (service) | [MODIFIED] | same | +6 methods (ADR-005). IDL bump 1.83 → 1.84. |
| 6 | `pom.xml` | [MODIFIED] | root | version 1.83 → 1.84 release. |
| 7 | Generated Java (`PointsEngineRuleService.java`, dto classes) | [auto] | target | Produced by Thrift compile — not hand-edited. |

### A.2 `emf-parent` (points-engine service)

**Entities** (package `com.capillary.emf.pointsengine.benefitcategory` — *proposed; see Q7-03, Q7-04*):

| # | Type | Status | Base / Annotations | Notes |
|---|------|--------|---------------------|-------|
| 8 | `BenefitCategory` | [NEW] | `extends OrgEntityIntegerPKBase` ; `@Entity @Table(name="benefit_categories")` ; `@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)` | Composite PK inner class `BenefitCategoryPK` (int id, int orgId) — inherited-style per `Benefits.java` §code-analysis-emf §3. NO `@Version`. |
| 9 | `BenefitCategory.BenefitCategoryPK` (inner) | [NEW] | `@Embeddable` ; inner `static class` ; `implements Serializable` | Matches `Benefits.BenefitsPK` exemplar (code-analysis-emf §3.1). |
| 10 | `BenefitCategorySlabMapping` | [NEW] | `extends OrgEntityIntegerPKBase` ; `@Entity @Table(name="benefit_category_slab_mapping")` ; `@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)` | Inner `BenefitCategorySlabMappingPK` composite key. |
| 11 | `BenefitCategorySlabMapping.BenefitCategorySlabMappingPK` (inner) | [NEW] | `@Embeddable` ; `implements Serializable` | — |
| 12 | `BenefitCategoryType` (enum, Java side) | [NEW] | `public enum` | Maps 1↔1 with Thrift enum. Values: `BENEFITS`. |

**DAOs** (package `com.capillary.emf.pointsengine.benefitcategory.dao`):

| # | Type | Status | Base | Notes |
|---|------|--------|------|-------|
| 13 | `BenefitCategoryDao` | [NEW] | `interface ... extends GenericDao<BenefitCategory, BenefitCategory.BenefitCategoryPK>` | Spring Data JPA + QueryDslPredicateExecutor (exemplar: `BenefitsDao` code-analysis-emf §4). |
| 14 | `BenefitCategorySlabMappingDao` | [NEW] | `interface ... extends GenericDao<BenefitCategorySlabMapping, BenefitCategorySlabMapping.BenefitCategorySlabMappingPK>` | Exemplar: `PeProgramSlabDao`. |

**Service / Editor / Handler** (existing files modified):

| # | Type | Status | Notes |
|---|------|--------|-------|
| 15 | `PointsEngineRuleService` | [MODIFIED] | +6 `@Transactional(value="warehouse", propagation=Propagation.REQUIRED)` methods. Existing class. |
| 16 | `PointsEngineRuleEditorImpl` | [MODIFIED] | +6 pass-through methods (validation + thin delegation). Existing class. |
| 17 | `PointsEngineRuleConfigThriftImpl` | [MODIFIED] | +6 `@Override @Trace(dispatcher=true) @MDCData(orgId="#orgId", requestId="#serverReqId")` handler methods (ADR-005). |
| 18 | `pom.xml` | [MODIFIED] | thrift-ifaces-pointsengine-rules dep bump 1.83 → 1.84. |
| 19 | `.gitmodules` | [MODIFIED] | cc-stack-crm submodule pointer bump (D-32). |

**DDL snapshots** (mirrored into emf-parent IT resources per D-32):

| # | Path | Status |
|---|------|--------|
| 20 | `emf-parent/integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql` | [NEW] |
| 21 | `emf-parent/integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/benefit_category_slab_mapping.sql` | [NEW] |

### A.3 `intouch-api-v3` (REST gateway)

**DTOs** (package `com.capillary.intouchapiv3.dto.benefitCategory` — *proposed, Q7-04*):

| # | Type | Status | Key annotations |
|---|------|--------|-----------------|
| 22 | `BenefitCategoryCreateRequest` | [NEW] | `@Getter @Setter` (Lombok — D-44) ; `@JsonIgnoreProperties(ignoreUnknown=true)` ; fields carry Bean Validation: `@NotNull` `programId`, `@NotBlank @Size(max=255)` `name`, `@NotNull @Size(min=1) List<@NotNull @Positive Integer> slabIds`. |
| 23 | `BenefitCategoryUpdateRequest` | [NEW] | `@Getter @Setter` (Lombok — D-44) ; `@NotBlank @Size(max=255)` `name`, `@NotNull List<@NotNull @Positive Integer> slabIds` (empty list permitted → clears all mappings). |
| 24 | `BenefitCategoryResponse` | [NEW] | `@Getter @Setter` (Lombok — D-44) ; Jackson `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone="UTC")` on `createdOn` / `updatedOn` (ADR-008 / G-01.6). |
| 25 | `BenefitCategoryListPayload` | [NEW] | `@Getter @Setter` (Lombok — D-44) ; `{ data: List<BenefitCategoryResponse>, page, size, total }` — inside `ResponseWrapper.data` (Q7-05 assumption C5). |

**Controller** (package `com.capillary.intouchapiv3.resources` — *proposed, Q7-04*):

| # | Type | Status | Key annotations |
|---|------|--------|-----------------|
| 26 | `BenefitCategoriesV3Controller` | [NEW] | `@RestController @RequestMapping("/v3/benefitCategories")` ; constructor-injected `BenefitCategoryFacade`, `AbstractBaseAuthenticationToken`. NO `@PreAuthorize` (C-34 / D-37). |

**Facade** (package `com.capillary.intouchapiv3.facade.benefitCategory` — *proposed*):

| # | Type | Status | Notes |
|---|------|--------|-------|
| 27 | `BenefitCategoryFacade` | [NEW] | `@Component` ; constructor-injects Thrift client via `RPCService.rpcClient(PointsEngineRuleService.Iface.class, "emf-thrift-service", 9199, 60000)` + `BenefitCategoryResponseMapper`. Returns `Optional<BenefitCategoryResponse>` on activate (D-39). |

**Mapper** (package `com.capillary.intouchapiv3.facade.benefitCategory.mapper` — D-45 / Q7-15 resolution):

| # | Type | Status | Notes |
|---|------|--------|-------|
| 27a | `BenefitCategoryResponseMapper` | [NEW] | `@Component` ; stateless bidirectional mapper `BenefitCategoryDto ↔ BenefitCategoryResponse`, `BenefitCategoryCreateRequest → BenefitCategoryDto`, `BenefitCategoryUpdateRequest → BenefitCategoryDto`. Unit-testable in isolation (resolves UTC-millis ↔ Date conversion per ADR-008). Exemplar: `intouch-api-v3/.../unified/promotion/mapper/CustomerPromotionResponseMapper.java`. |

**Exception + advice**:

| # | Type | Status | Notes |
|---|------|--------|-------|
| 28 | `ConflictException` | [NEW] | `extends RuntimeException` — package matches existing `NotFoundException` / `InvalidInputException` (D-31). Constructors: `(String code, String message)`. |
| 29 | `TargetGroupErrorAdvice` | [MODIFIED] | +`@ExceptionHandler(ConflictException.class)` returning `ResponseEntity<ResponseWrapper<String>>` with `HttpStatus.CONFLICT` (ADR-009). |
| 30 | `pom.xml` | [MODIFIED] | thrift-ifaces-pointsengine-rules dep bump 1.83 → 1.84. |

### A.4 `cc-stack-crm` (DDL submodule)

| # | Path | Status |
|---|------|--------|
| 31 | `schema/dbmaster/warehouse/benefit_categories.sql` | [NEW] |
| 32 | `schema/dbmaster/warehouse/benefit_category_slab_mapping.sql` | [NEW] |

### A.5 Summary counts

- **NEW**: 15 Java types + 4 DTO + 1 Mapper (D-45) + 2 DDL + 1 exception + 4 thrift structs/enum = **27 top-level new artifacts**.
- **MODIFIED**: 3 emf-parent Java files + 1 IDL file + 2 pom.xml files + 1 .gitmodules + 1 Advice class = **8 modified artifacts**.

---

## B. Cross-Boundary Contracts (6 operations)

Each operation is traced from HTTP to DAO with exact method signatures on each boundary. Confidence/evidence in brackets.

### B.1 Create — `POST /v3/benefitCategories`

**HTTP**

```http
POST /v3/benefitCategories
Content-Type: application/json
Authorization: BasicAndKey ...
X-Request-Id: <uuid>

{ "programId": 5, "name": "VIP Perks", "slabIds": [1, 3, 5] }
```

Success: `201 Created` + `ResponseWrapper<BenefitCategoryResponse>`.

**Controller → Facade**

```java
// BenefitCategoriesV3Controller
@PostMapping
public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> create(
    @Valid @RequestBody BenefitCategoryCreateRequest request,
    AbstractBaseAuthenticationToken user          // Spring-resolved; user.getOrgId() (long), user.getUserId() (int)
);
// C6 — matches BenefitsV3Controller / TargetGroupController shape per code-analysis-intouch §1.
```

```java
// BenefitCategoryFacade
public BenefitCategoryResponse create(
    int orgId, int actorUserId, BenefitCategoryCreateRequest request
) throws ConflictException, InvalidInputException, EMFThriftException;
// C6 — facade owns Thrift client call + exception translation (D-31 / ADR-009).
```

**Facade → Thrift (IDL method)**

```thrift
BenefitCategoryDto createBenefitCategory(
    1: required i32 orgId,
    2: required BenefitCategoryDto dto,          // id absent; slabIds populated
    3: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);
// C7 — verbatim from 01-architect.md §9.
```

**Thrift Handler → Editor → Service (emf-parent)**

```java
// PointsEngineRuleConfigThriftImpl
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public BenefitCategoryDto createBenefitCategory(int orgId, BenefitCategoryDto dto, int actorUserId)
    throws PointsEngineRuleServiceException, TException;
// C7 — exact shape of PointsEngineRuleConfigThriftImpl.createOrUpdateBenefit (code-analysis-emf §2).

// PointsEngineRuleEditorImpl
public BenefitCategoryDto createBenefitCategory(int orgId, BenefitCategoryDto dto, int actorUserId)
    throws PointsEngineRuleServiceException;
// C6 — thin delegate; validates enum mapping, forwards to service.

// PointsEngineRuleService
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public BenefitCategoryDto createBenefitCategory(int orgId, BenefitCategoryDto dto, int actorUserId)
    throws PointsEngineRuleServiceException;
// C6 — @Transactional(warehouse) matches existing service methods (code-analysis-emf §5).
```

**Service → DAO**

```java
// BenefitCategoryDao
List<BenefitCategory> findActiveByProgramAndName(int orgId, int programId, String name);
// C5 — custom @Query (Spring Data); app-level uniqueness check (D-28 / ADR-012 post-D-38).

BenefitCategory save(BenefitCategory entity);     // inherited from JpaRepository
// C7 — JpaRepository standard.

// BenefitCategorySlabMappingDao
List<BenefitCategorySlabMapping> saveAll(Iterable<BenefitCategorySlabMapping> mappings);
// C7 — JpaRepository standard.

// PeProgramSlabDao (existing — REUSED AS-IS per D-41; NO modification)
List<ProgramSlab> findByProgram(int orgId, int programId);
// C7 — method exists in PeProgramSlabDao:27. Returns ALL ProgramSlab rows for (orgId, programId).
// Service layer does slab-existence validation in-memory via Set operations:
//   Set<Integer> existingIds = programSlabDao.findByProgram(orgId, programId)
//       .stream().map(ps -> ps.getPk().getId()).collect(toSet());
//   Set<Integer> missing = new HashSet<>(candidateSlabIds);
//   missing.removeAll(existingIds);        // → unknown slabs
//   if (!missing.isEmpty()) throw BC_UNKNOWN_SLAB(missing);
// Cross-program check: if a slab belongs to a DIFFERENT program (program_id ≠ request.programId),
// the slab won't appear in findByProgram results → same path as BC_UNKNOWN_SLAB → unified error.
// Rationale: D-26 SMALL-scale envelope (≤10 slabs typical per program, hard cap small) makes
// in-memory filtering negligible; avoids cross-repo DAO modification. Revisit if any program
// ever carries >100 slabs. (See D-41.)
```

**Error semantics**

- Bean Validation failure → `HandlerMethodArgumentNotValid` → `TargetGroupErrorAdvice` → 400 `BC_NAME_REQUIRED`/`BC_NAME_LENGTH`/`BC_SLAB_IDS_REQUIRED`.
- Active-name duplicate → service throws `PointsEngineRuleServiceException(errorMessage="BC_NAME_TAKEN_ACTIVE", statusCode=409)` → facade translates → `ConflictException`.
- Unknown slabId / cross-program slabId → 409 `BC_UNKNOWN_SLAB` / `BC_CROSS_PROGRAM_SLAB`.

### B.2 Update — `PUT /v3/benefitCategories/{id}`

**Controller**

```java
@PutMapping("/{id}")
public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> update(
    @PathVariable("id") int id,
    @Valid @RequestBody BenefitCategoryUpdateRequest request,
    AbstractBaseAuthenticationToken user
);
// C6.
```

**Facade**

```java
public BenefitCategoryResponse update(
    int orgId, int actorUserId, int categoryId, BenefitCategoryUpdateRequest request
) throws ConflictException, NotFoundException, InvalidInputException, EMFThriftException;
// C6.
```

**Thrift**

```thrift
BenefitCategoryDto updateBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: required BenefitCategoryDto dto,
    4: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);
// C7 — §9.
```

**Service → DAO** (diff-and-apply per ADR-003)

```java
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public BenefitCategoryDto updateBenefitCategory(int orgId, int categoryId, BenefitCategoryDto dto, int actorUserId)
    throws PointsEngineRuleServiceException;
// Steps (pseudo, not to be in Designer): load-active-or-throw-409-inactive, name uniqueness check excl self, slab-validity check, diff-apply slab mappings, update category row.

// Additional DAO methods required on BenefitCategoryDao
Optional<BenefitCategory> findActiveById(int orgId, int id);                                    // C5
List<BenefitCategory> findActiveByProgramAndNameExceptId(int orgId, int programId,
                                                         String name, int excludeId);           // C5

// BenefitCategorySlabMappingDao
List<BenefitCategorySlabMapping> findActiveByCategoryId(int orgId, int benefitCategoryId);      // C5
@Modifying @Query("UPDATE BenefitCategorySlabMapping m SET m.isActive=false, m.updatedOn=:now, m.updatedBy=:actor "
                + "WHERE m.orgId=:orgId AND m.benefitCategoryId=:catId AND m.slabId IN :slabIds AND m.isActive=true")
int bulkSoftDeleteByCategoryAndSlabs(int orgId, int catId, List<Integer> slabIds, Date now, int actor);
// C5 — matches BenefitsDao bulk update patterns.
```

### B.3 Get by id — `GET /v3/benefitCategories/{id}` (AMENDED by D-42 — `?includeInactive=true` audit flag)

```java
@GetMapping("/{id}")
public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> get(
    @PathVariable("id") int id,
    @RequestParam(name = "includeInactive", defaultValue = "false") boolean includeInactive,
    AbstractBaseAuthenticationToken user
);
// C6. Authorizes KeyOnly OR BasicAndKey (ADR-010 / D-37) — via existing auth filter chain.
// AMENDED per D-42: includeInactive=false (default) returns 404 on soft-deleted rows — strict
// admin view; includeInactive=true returns the row even if is_active=false (audit access).

// Facade
public BenefitCategoryResponse get(int orgId, int id, boolean includeInactive)
    throws NotFoundException, EMFThriftException;
// C6. Branches DAO lookup on includeInactive flag.
```

**Thrift** (no IDL change — filter flag lives inside the request struct)

```thrift
BenefitCategoryDto getBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: optional bool includeInactive = false    // D-42 — audit-inclusive read
) throws (1: PointsEngineRuleServiceException ex);
```

**Service → DAO**

```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS, readOnly = true)
public BenefitCategoryDto getBenefitCategory(int orgId, int categoryId, boolean includeInactive)
    throws PointsEngineRuleServiceException;
// C5 — readOnly=true appropriate for pure read (pattern: PointsEngineRuleService.getSlabsByProgramId code-analysis-emf §5).
// Branches on includeInactive: true → findByOrgIdAndId (any state); false → findActiveByOrgIdAndId.

// BenefitCategoryDao — TWO methods per D-42
Optional<BenefitCategory> findByOrgIdAndId(int orgId, int id);
// C6 — returns row regardless of is_active; used when includeInactive=true (audit path).

Optional<BenefitCategory> findActiveByOrgIdAndId(int orgId, int id);
// C6 — returns row only if is_active=true; used when includeInactive=false (default GET);
//      ALSO used by all mutation paths (update, activate→load-for-reactivation, deactivate) —
//      aligns with D-27 (writes on inactive forbidden) + D-28 (uniqueness among active).

// BenefitCategorySlabMappingDao
List<Integer> findActiveSlabIdsByCategoryId(int orgId, int benefitCategoryId);
// C5 — @Query("SELECT m.slabId FROM ...").
```

Not-found: service throws `PointsEngineRuleServiceException(errorMessage="BC_NOT_FOUND", statusCode=404)` → facade throws `NotFoundException` → controller-advice returns 200 + error envelope (platform quirk OQ-45).

### B.4 List — `GET /v3/benefitCategories?programId=&isActive=&page=&size=`

```java
@GetMapping
public ResponseEntity<ResponseWrapper<BenefitCategoryListPayload>> list(
    @RequestParam(value = "programId", required = false) Integer programId,
    @RequestParam(value = "isActive", required = false, defaultValue = "true") String isActive,  // "true"|"false"|"all"
    @RequestParam(value = "page", required = false, defaultValue = "0") @Min(0) int page,
    @RequestParam(value = "size", required = false, defaultValue = "50") @Min(1) @Max(100) int size,
    AbstractBaseAuthenticationToken user
);
// C5 — shape confirmed against code-analysis-intouch §1 list endpoints. Q7-05 on wrapper placement.

// Facade
public BenefitCategoryListPayload list(
    int orgId, Integer programId, String isActiveFilter, int page, int size
) throws InvalidInputException, EMFThriftException;
// C6.
```

**Thrift**

```thrift
BenefitCategoryListResponse listBenefitCategories(
    1: required BenefitCategoryFilter filter,
    2: required i32 page,
    3: required i32 size
) throws (1: PointsEngineRuleServiceException ex);
```

**Service → DAO**

```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS, readOnly = true)
public BenefitCategoryListResponse listBenefitCategories(
    BenefitCategoryFilter filter, int page, int size
) throws PointsEngineRuleServiceException;
// C5.

// BenefitCategoryDao
Page<BenefitCategory> findPage(int orgId, Integer programId, Boolean isActive, Pageable pageable);
// C5 — custom @Query; Pageable enforces ORDER BY created_on DESC, id DESC (ADR-011).

long countByFilter(int orgId, Integer programId, Boolean isActive);
// C6.

// BenefitCategorySlabMappingDao
@Query("SELECT new com.capillary.emf.pointsengine.benefitcategory.dao.CategorySlabTuple("
     + "m.benefitCategoryId, m.slabId) "
     + "FROM BenefitCategorySlabMapping m "
     + "WHERE m.orgId=:orgId AND m.benefitCategoryId IN :categoryIds AND m.isActive=true")
List<CategorySlabTuple> findActiveSlabIdsForCategories(int orgId, List<Integer> categoryIds);
// C5 — single bulk query (G-04.1, NO N+1). Returns projection records; service groups by categoryId.
// CategorySlabTuple is a simple DTO record {int categoryId; int slabId;} in the same dao package.
```

### B.5 Activate — `PATCH /v3/benefitCategories/{id}/activate`

**Asymmetric response per D-39 / ADR-006 amended**: happy state-change → **200 + DTO**; idempotent already-active → **204**.

```java
// Controller
@PatchMapping("/{id}/activate")
public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> activate(
    @PathVariable("id") int id,
    AbstractBaseAuthenticationToken user
);
// Returns:
//   204 No Content                                      → when facade returns Optional.empty()
//   200 OK + ResponseWrapper<BenefitCategoryResponse>  → when facade returns populated Optional
// C6 — D-39 explicit asymmetric contract.

// Facade
public Optional<BenefitCategoryResponse> activate(int orgId, int actorUserId, int categoryId)
    throws ConflictException, NotFoundException, EMFThriftException;
// C7 — D-39 verbatim: "empty on idempotent no-op, populated on state change".
```

**Thrift**

```thrift
BenefitCategoryDto activateBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);
// C6 — D-39 amended ADR-006: returns full BenefitCategoryDto on state change.
// Idempotent no-op: EMF returns a struct with a sentinel isActive=true AND updatedOn==createdOn
//   (i.e. no change was applied). Facade maps this shape → Optional.empty().
//   Alternative: EMF returns NULL on no-op. Thrift "optional return" is not a language primitive —
//   Java client sees the struct as non-null. See Q7-13 for the chosen sentinel vs. "throw a special code" option.
```

> **Design note on no-op signalling** (Q7-13): two viable options. (a) EMF returns the DTO with an in-band flag (e.g., echoing back but flipping a new field `stateChanged: bool`). (b) EMF throws `PointsEngineRuleServiceException(statusCode=304, errorMessage="ALREADY_ACTIVE")` on no-op and facade catches → `Optional.empty()`. Option (b) is cleaner (no new struct field, no sentinel); however, HTTP 304 is not idiomatic on PATCH. **Assumption (C5)**: add field `12: optional bool stateChanged = true` to `BenefitCategoryDto` — on idempotent no-op server returns struct with `stateChanged=false`. This preserves the single-return-type Thrift method. **Escalated to Q7-13 for user confirmation.**

**Service → DAO**

```java
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public BenefitCategoryDto activateBenefitCategory(int orgId, int categoryId, int actorUserId)
    throws PointsEngineRuleServiceException;
// C6.

// BenefitCategoryDao (additional methods)
Optional<BenefitCategory> findByOrgIdAndId(int orgId, int id);            // same as B.3
List<BenefitCategory> findActiveByProgramAndName(int orgId, int programId, String name);  // same as B.1 — reactivation conflict check
BenefitCategory save(BenefitCategory entity);
```

### B.6 Deactivate — `PATCH /v3/benefitCategories/{id}/deactivate`

```java
// Controller
@PatchMapping("/{id}/deactivate")
public ResponseEntity<Void> deactivate(
    @PathVariable("id") int id,
    AbstractBaseAuthenticationToken user
);
// Returns 204 No Content on state change AND on idempotent already-inactive (ADR-006 unchanged).
// C7.

// Facade
public void deactivate(int orgId, int actorUserId, int categoryId)
    throws NotFoundException, EMFThriftException;
// C7 — void per D-39/ADR-006.
```

**Thrift**

```thrift
void deactivateBenefitCategory(
    1: required i32 orgId,
    2: required i32 categoryId,
    3: required i32 actorUserId
) throws (1: PointsEngineRuleServiceException ex);
// C7 — §9.
```

**Service → DAO** (cascade in same txn — ADR-004)

```java
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public void deactivateBenefitCategory(int orgId, int categoryId, int actorUserId)
    throws PointsEngineRuleServiceException;
// C7.

// BenefitCategoryDao
@Modifying @Query("UPDATE BenefitCategory c SET c.isActive=false, c.updatedOn=:now, c.updatedBy=:actor "
                + "WHERE c.orgId=:orgId AND c.id=:id AND c.isActive=true")
int softDeleteIfActive(int orgId, int id, Date now, int actor);
// C6 — @Modifying pattern exists in PeProgramSlabDao (code-analysis-emf §4).

// BenefitCategorySlabMappingDao
@Modifying @Query("UPDATE BenefitCategorySlabMapping m SET m.isActive=false, m.updatedOn=:now, m.updatedBy=:actor "
                + "WHERE m.orgId=:orgId AND m.benefitCategoryId=:catId AND m.isActive=true")
int bulkSoftDeleteByCategory(int orgId, int catId, Date now, int actor);
// C6 — cascade same-txn (D-06 / C-16).
```

---

## C. Data Model DDL (authoritative — reflects D-38: no DB UNIQUE, no advisory lock infra)

### C.1 `benefit_categories.sql`

```sql
-- cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql
CREATE TABLE `benefit_categories` (
  `id`                INT(11)            NOT NULL AUTO_INCREMENT,
  `org_id`            INT(11)            NOT NULL DEFAULT '0',
  `program_id`        INT(11)            NOT NULL,
  `name`              VARCHAR(255)       NOT NULL,
  `category_type`     ENUM('BENEFITS')   NOT NULL DEFAULT 'BENEFITS',
  `is_active`         TINYINT(1)         NOT NULL DEFAULT 1,
  `created_on`        DATETIME           NOT NULL,
  `created_by`        INT(11)            NOT NULL,
  `updated_on`        DATETIME                    DEFAULT NULL,
  `updated_by`        INT(11)                     DEFAULT NULL,
  `auto_update_time`  TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`, `org_id`),
  KEY `idx_bc_org_program` (`org_id`, `program_id`),
  KEY `idx_bc_org_program_active` (`org_id`, `program_id`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- NO `version` column (ADR-001 / D-33).
-- NO UNIQUE (org_id, program_id, name) — app-level check only (D-28 / D-38).
-- No declared FOREIGN KEYs — platform convention (G-12.2).
```

### C.2 `benefit_category_slab_mapping.sql`

```sql
CREATE TABLE `benefit_category_slab_mapping` (
  `id`                   INT(11)    NOT NULL AUTO_INCREMENT,
  `org_id`               INT(11)    NOT NULL DEFAULT '0',
  `benefit_category_id`  INT(11)    NOT NULL,
  `slab_id`              INT(11)    NOT NULL,
  `is_active`            TINYINT(1) NOT NULL DEFAULT 1,
  `created_on`           DATETIME   NOT NULL,
  `created_by`           INT(11)    NOT NULL,
  `updated_on`           DATETIME            DEFAULT NULL,
  `updated_by`           INT(11)             DEFAULT NULL,
  `auto_update_time`     TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`, `org_id`),
  KEY `idx_bcsm_org_cat_active`   (`org_id`, `benefit_category_id`, `is_active`),
  KEY `idx_bcsm_org_slab_active`  (`org_id`, `slab_id`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- NO `version` column.
-- No declared FOREIGN KEYs.
```

### C.3 JPA column mapping rules (for entity annotations in §F)

| Java field | Column | JPA | Rationale |
|------------|--------|-----|-----------|
| `int id` | `id` (PK, AI) | `@Id @GeneratedValue(strategy=GenerationType.IDENTITY) @Column(name="id")` | Matches `Benefits.id`. |
| `int orgId` | `org_id` (PK) | `@Id @Column(name="org_id")` | Composite PK via `@Embeddable`. |
| `int programId` | `program_id` | `@Column(name="program_id", nullable=false)` | — |
| `String name` | `name` | `@Column(name="name", length=255, nullable=false)` | — |
| `BenefitCategoryType categoryType` | `category_type` | `@Column(name="category_type", nullable=false) @Enumerated(EnumType.STRING)` | Matches platform ENUM handling. |
| `boolean isActive` | `is_active` | `@Column(name="is_active", nullable=false)` | — |
| `Date createdOn` | `created_on` | `@Temporal(TemporalType.TIMESTAMP) @Column(name="created_on", nullable=false)` | ADR-008; manual `new Date()` in service (Q7-10 assumption C5 → platform pattern). |
| `int createdBy` | `created_by` | `@Column(name="created_by", nullable=false)` | D-30. |
| `Date updatedOn` | `updated_on` | `@Temporal(TemporalType.TIMESTAMP) @Column(name="updated_on")` | Nullable. |
| `Integer updatedBy` | `updated_by` | `@Column(name="updated_by")` | Nullable `Integer`. |
| `Date autoUpdateTime` | `auto_update_time` | `@Temporal(TemporalType.TIMESTAMP) @Column(name="auto_update_time", insertable=false, updatable=false)` | DB-managed; read-only from app. |

Evidence anchor: `code-analysis-emf-parent.md` §3 (`Benefits.java`) — identical column/annotation layout.

---

## D. Patterns Prescribed (from codebase discovery)

Every pattern named here has a concrete exemplar in the existing codebase. Phase 9 SDET mirrors these patterns verbatim.

| # | Pattern | Exemplar (evidence anchor) | Designer prescription |
|---|---------|---------------------------|-----------------------|
| P-01 | Composite-PK entity via `OrgEntityIntegerPKBase` + inner `@Embeddable` PK | `Benefits.java` + `Benefits.BenefitsPK` (code-analysis-emf §3.1) | BenefitCategory + BenefitCategorySlabMapping both follow this shape. |
| P-02 | DAO = `interface ... extends GenericDao<T, PK>` (= Spring Data JPA + QueryDSL) | `BenefitsDao.java` (code-analysis-emf §4) | Both new DAOs follow this contract; custom finders as `@Query` methods. |
| P-03 | `@ExposedCall(thriftName="pointsengine-rules")` AOP-registered handler | `PointsEngineRuleConfigThriftImpl` (code-analysis-emf §2) | Add methods to existing class (ADR-005); do NOT annotate handler methods individually. |
| P-04 | `@Trace(dispatcher=true) @MDCData(orgId="#orgId", requestId="#serverReqId")` on every handler method | `PointsEngineRuleConfigThriftImpl.createOrUpdateBenefit` (code-analysis-emf §2) | Six new handler methods receive this pair. |
| P-05 | Service `@Transactional(value="warehouse", propagation=Propagation.REQUIRED)` | `PointsEngineRuleService.createOrUpdateSlab` (code-analysis-emf §5) | Six new service methods; `readOnly=true` variant on GET + list. |
| P-06 | Audit columns written manually via `new Date()` in service code (not `@PrePersist`) | `PointsEngineRuleService.createOrUpdateSlab` line 3669-3671 (code-analysis-emf §5) | Assumption C5 (Q7-10): adopt platform pattern — service injects `now = new Date()`; no JPA lifecycle hooks. |
| P-07 | Cascade soft-delete via bulk `UPDATE ... SET is_active=false` in same `@Transactional(warehouse)` | `PointsEngineRuleService.deactivateSlab` cascade pattern | `deactivateBenefitCategory` cascades to mappings. |
| P-08 | Thrift client via `RPCService.rpcClient(Iface.class, "emf-thrift-service", 9199, 60000)` | `PointsEngineRulesThriftService` factory method (code-analysis-intouch §2) | `BenefitCategoryFacade` reuses the same factory; NO new Thrift client class unless a new service is introduced (none is). |
| P-09 | `ResponseWrapper<T>{data, errors, warnings}` envelope on every REST response | `TargetGroupController` (code-analysis-intouch §1) | All 6 endpoints wrap. 204 paths return `ResponseEntity<Void>` without wrapper (consistent with existing 204 endpoints). |
| P-10 | Jackson UTC ISO-8601 via `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone="UTC")` on DTO Date fields | code-analysis-intouch §4 DTOs | `BenefitCategoryResponse.createdOn` / `updatedOn`. |
| P-11 | `@ControllerAdvice` exception → HTTP status map with explicit envelope | `TargetGroupErrorAdvice` (code-analysis-intouch §6) | Add `@ExceptionHandler(ConflictException.class) → 409`. Do NOT touch existing handlers. |
| P-12 | Bean Validation at controller via `@Valid @RequestBody`; element constraints on `List<@Positive Integer>` | code-analysis-intouch §5 | All validation defined on Request DTOs, not inside facade. |
| P-13 | Tenant isolation via explicit `orgId` arg on every DAO method (no `@Filter`/`@Where`) | `BenefitsDao`, `PeProgramSlabDao` | Every signature in §B carries `orgId` as first arg or as part of filter record. |
| P-14 | `PointsEngineRuleServiceException{errorMessage, statusCode}` single exception type for all Thrift errors | code-analysis-thrift-ifaces §3 | All 6 methods throw this exception; facade translates by `statusCode` (D-31). |
| P-15 | Three-boundary timestamp: `Date`/`DATETIME` (EMF) · `i64` epoch ms (Thrift) · ISO-8601 UTC string (REST) | D-24 / ADR-008 | Enforced in every Thrift handler + Jackson config. Unit tests must use UTC explicitly. |
| P-16 | Asymmetric response on `/activate` vs `/deactivate` (D-39) | No prior exemplar — novel shape | Controller branches on `Optional.isPresent()`; facade returns `Optional<T>`; Thrift returns struct with `stateChanged` field (assumption C5, Q7-13). |
| P-17 | Diff-and-apply on list-typed child collection (junction table) | No direct exemplar; inspired by `PeProgramSlabEditor` refresh logic | Compute `toAdd / toSoftDelete / toKeep` via `LinkedHashSet` set ops; deterministic order. |

---

## E. Error Mapping (authoritative — mirrors ADR-009)

| Wire | Exception (EMF throws) | Exception (intouch receives) | HTTP code on REST | Error code |
|------|------------------------|------------------------------|-------------------|------------|
| any 400-style | `PointsEngineRuleServiceException(statusCode=400)` | `InvalidInputException` | 400 | `BC_NAME_REQUIRED` / `BC_NAME_LENGTH` / `BC_SLAB_IDS_REQUIRED` |
| not-found | `PointsEngineRuleServiceException(statusCode=404)` | `NotFoundException` | **200 + error envelope** (platform quirk OQ-45) | `BC_NOT_FOUND` |
| conflict | `PointsEngineRuleServiceException(statusCode=409)` | `ConflictException` | 409 | `BC_NAME_TAKEN_ACTIVE` · `BC_CROSS_PROGRAM_SLAB` · `BC_UNKNOWN_SLAB` · `BC_INACTIVE_WRITE_FORBIDDEN` · `BC_NAME_TAKEN_ON_REACTIVATE` |
| bad filter | `IllegalArgumentException` in controller layer | `InvalidInputException` | 400 | `BC_PAGE_SIZE_EXCEEDED` |
| unmapped Throwable | — | unhandled (falls through) | 500 | `INTERNAL_ERROR` |

**Facade translation rule** (exact if-ladder in Phase 10 GREEN — pinned here for SDET RED):

```java
try { ... RPCService.rpcClient(...).createBenefitCategory(...); }
catch (PointsEngineRuleServiceException e) {
    int status = e.isSetStatusCode() ? e.getStatusCode() : 500;
    switch (status) {
        case 400: throw new InvalidInputException(e.getErrorMessage());
        case 404: throw new NotFoundException(e.getErrorMessage());
        case 409: throw new ConflictException(e.getErrorMessage(), e.getErrorMessage());   // code+message assumption (C5)
        default:  throw new EMFThriftException(e.getErrorMessage());
    }
}
```

No new exception class besides `ConflictException`. `EMFThriftException` already exists (code-analysis-intouch §7).

---

## F. Compile-Safe Signatures (authoritative — for SDET RED)

> SDET Phase 9 imports these exact signatures. Bodies: `throw new UnsupportedOperationException("not impl yet");` until Phase 10.

### F.1 Entities (Java)

```java
// emf-parent
package com.capillary.emf.pointsengine.benefitcategory;

import com.capillary.data.common.entities.OrgEntityIntegerPKBase;
import com.capillary.data.common.datasource.DataSourceSpecification;
import com.capillary.data.common.datasource.SchemaType;
import javax.persistence.*;
import java.io.Serializable;
import java.util.Date;

@Entity
@Table(name = "benefit_categories")
@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)
public class BenefitCategory extends OrgEntityIntegerPKBase {

    @EmbeddedId
    private BenefitCategoryPK pk;

    @Column(name = "program_id", nullable = false) private int programId;
    @Column(name = "name", length = 255, nullable = false) private String name;
    @Enumerated(EnumType.STRING)
    @Column(name = "category_type", nullable = false) private BenefitCategoryType categoryType;
    @Column(name = "is_active", nullable = false) private boolean isActive;
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "created_on", nullable = false) private Date createdOn;
    @Column(name = "created_by", nullable = false) private int createdBy;
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "updated_on") private Date updatedOn;
    @Column(name = "updated_by") private Integer updatedBy;
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "auto_update_time", insertable = false, updatable = false) private Date autoUpdateTime;

    // getters + setters omitted (Lombok @Data or hand-written per existing convention — Q7-14)

    @Embeddable
    public static class BenefitCategoryPK implements Serializable {
        @Column(name = "id") private int id;
        @Column(name = "org_id") private int orgId;
        // equals + hashCode per Benefits.BenefitsPK pattern
    }
}
// Confidence: C6 — exact mirror of code-analysis-emf §3.1.
```

```java
package com.capillary.emf.pointsengine.benefitcategory;

@Entity
@Table(name = "benefit_category_slab_mapping")
@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)
public class BenefitCategorySlabMapping extends OrgEntityIntegerPKBase {

    @EmbeddedId
    private BenefitCategorySlabMappingPK pk;

    @Column(name = "benefit_category_id", nullable = false) private int benefitCategoryId;
    @Column(name = "slab_id", nullable = false) private int slabId;
    @Column(name = "is_active", nullable = false) private boolean isActive;
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "created_on", nullable = false) private Date createdOn;
    @Column(name = "created_by", nullable = false) private int createdBy;
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "updated_on") private Date updatedOn;
    @Column(name = "updated_by") private Integer updatedBy;
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "auto_update_time", insertable = false, updatable = false) private Date autoUpdateTime;

    @Embeddable
    public static class BenefitCategorySlabMappingPK implements Serializable {
        @Column(name = "id") private int id;
        @Column(name = "org_id") private int orgId;
    }
}
// Confidence: C6.
```

```java
package com.capillary.emf.pointsengine.benefitcategory;

public enum BenefitCategoryType { BENEFITS }
// Confidence: C7.
```

### F.2 DAOs (Java interfaces only)

```java
package com.capillary.emf.pointsengine.benefitcategory.dao;

import com.capillary.data.common.dao.GenericDao;
import com.capillary.emf.pointsengine.benefitcategory.BenefitCategory;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.*;

public interface BenefitCategoryDao
        extends GenericDao<BenefitCategory, BenefitCategory.BenefitCategoryPK> {

    @Query("SELECT c FROM BenefitCategory c WHERE c.pk.orgId=:orgId AND c.pk.id=:id")
    Optional<BenefitCategory> findByOrgIdAndId(@Param("orgId") int orgId, @Param("id") int id);

    @Query("SELECT c FROM BenefitCategory c WHERE c.pk.orgId=:orgId AND c.pk.id=:id AND c.isActive=true")
    Optional<BenefitCategory> findActiveById(@Param("orgId") int orgId, @Param("id") int id);

    @Query("SELECT c FROM BenefitCategory c WHERE c.pk.orgId=:orgId AND c.programId=:programId "
         + "AND c.name=:name AND c.isActive=true")
    List<BenefitCategory> findActiveByProgramAndName(
            @Param("orgId") int orgId, @Param("programId") int programId, @Param("name") String name);

    @Query("SELECT c FROM BenefitCategory c WHERE c.pk.orgId=:orgId AND c.programId=:programId "
         + "AND c.name=:name AND c.isActive=true AND c.pk.id<>:excludeId")
    List<BenefitCategory> findActiveByProgramAndNameExceptId(
            @Param("orgId") int orgId, @Param("programId") int programId,
            @Param("name") String name, @Param("excludeId") int excludeId);

    @Query(value = "SELECT c FROM BenefitCategory c WHERE c.pk.orgId=:orgId "
                 + "AND (:programId IS NULL OR c.programId=:programId) "
                 + "AND (:isActive IS NULL OR c.isActive=:isActive) "
                 + "ORDER BY c.createdOn DESC, c.pk.id DESC",
           countQuery = "SELECT COUNT(c) FROM BenefitCategory c WHERE c.pk.orgId=:orgId "
                      + "AND (:programId IS NULL OR c.programId=:programId) "
                      + "AND (:isActive IS NULL OR c.isActive=:isActive)")
    org.springframework.data.domain.Page<BenefitCategory> findPage(
            @Param("orgId") int orgId,
            @Param("programId") Integer programId,
            @Param("isActive") Boolean isActive,
            org.springframework.data.domain.Pageable pageable);

    @Modifying
    @Query("UPDATE BenefitCategory c SET c.isActive=false, c.updatedOn=:now, c.updatedBy=:actor "
         + "WHERE c.pk.orgId=:orgId AND c.pk.id=:id AND c.isActive=true")
    int softDeleteIfActive(@Param("orgId") int orgId, @Param("id") int id,
                           @Param("now") Date now, @Param("actor") int actor);

    @Modifying
    @Query("UPDATE BenefitCategory c SET c.isActive=true, c.updatedOn=:now, c.updatedBy=:actor "
         + "WHERE c.pk.orgId=:orgId AND c.pk.id=:id AND c.isActive=false")
    int activateIfInactive(@Param("orgId") int orgId, @Param("id") int id,
                           @Param("now") Date now, @Param("actor") int actor);
}
// Confidence: C5 — query structure derived from BenefitsDao + PeProgramSlabDao (code-analysis-emf §4).
```

```java
package com.capillary.emf.pointsengine.benefitcategory.dao;

import com.capillary.data.common.dao.GenericDao;
import com.capillary.emf.pointsengine.benefitcategory.BenefitCategorySlabMapping;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.*;

public interface BenefitCategorySlabMappingDao
        extends GenericDao<BenefitCategorySlabMapping, BenefitCategorySlabMapping.BenefitCategorySlabMappingPK> {

    @Query("SELECT m.slabId FROM BenefitCategorySlabMapping m "
         + "WHERE m.pk.orgId=:orgId AND m.benefitCategoryId=:catId AND m.isActive=true")
    List<Integer> findActiveSlabIdsByCategoryId(@Param("orgId") int orgId, @Param("catId") int catId);

    @Query("SELECT new com.capillary.emf.pointsengine.benefitcategory.dao.CategorySlabTuple("
         + "m.benefitCategoryId, m.slabId) "
         + "FROM BenefitCategorySlabMapping m "
         + "WHERE m.pk.orgId=:orgId AND m.benefitCategoryId IN :categoryIds AND m.isActive=true")
    List<CategorySlabTuple> findActiveSlabIdsForCategories(
            @Param("orgId") int orgId, @Param("categoryIds") List<Integer> categoryIds);

    @Query("SELECT m FROM BenefitCategorySlabMapping m WHERE m.pk.orgId=:orgId "
         + "AND m.benefitCategoryId=:catId AND m.isActive=true")
    List<BenefitCategorySlabMapping> findActiveByCategoryId(
            @Param("orgId") int orgId, @Param("catId") int catId);

    @Modifying
    @Query("UPDATE BenefitCategorySlabMapping m SET m.isActive=false, m.updatedOn=:now, m.updatedBy=:actor "
         + "WHERE m.pk.orgId=:orgId AND m.benefitCategoryId=:catId AND m.isActive=true")
    int bulkSoftDeleteByCategory(@Param("orgId") int orgId, @Param("catId") int catId,
                                 @Param("now") Date now, @Param("actor") int actor);

    @Modifying
    @Query("UPDATE BenefitCategorySlabMapping m SET m.isActive=false, m.updatedOn=:now, m.updatedBy=:actor "
         + "WHERE m.pk.orgId=:orgId AND m.benefitCategoryId=:catId "
         + "AND m.slabId IN :slabIds AND m.isActive=true")
    int bulkSoftDeleteByCategoryAndSlabs(@Param("orgId") int orgId, @Param("catId") int catId,
                                         @Param("slabIds") List<Integer> slabIds,
                                         @Param("now") Date now, @Param("actor") int actor);
}

// Supporting projection record (plain class to stay JPA-friendly on Java 17 — record is also acceptable)
public class CategorySlabTuple {
    private final int categoryId;
    private final int slabId;
    public CategorySlabTuple(int categoryId, int slabId) { this.categoryId = categoryId; this.slabId = slabId; }
    public int getCategoryId() { return categoryId; } public int getSlabId() { return slabId; }
}
// Confidence: C5.
```

### F.3 Service additions on `PointsEngineRuleService`

```java
// emf-parent — additions to existing class
package com.capillary.emf.pointsengine.service;

import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.annotation.Propagation;
import com.capillary.pointsengine.rules.thrift.*;    // generated Thrift types

public interface PointsEngineRuleServiceBenefitCategoryFacet {    // documentation view only — actual class is concrete

    @Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
    BenefitCategoryDto createBenefitCategory(int orgId, BenefitCategoryDto dto, int actorUserId)
            throws PointsEngineRuleServiceException;

    @Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
    BenefitCategoryDto updateBenefitCategory(int orgId, int categoryId, BenefitCategoryDto dto, int actorUserId)
            throws PointsEngineRuleServiceException;

    @Transactional(value = "warehouse", propagation = Propagation.SUPPORTS, readOnly = true)
    BenefitCategoryDto getBenefitCategory(int orgId, int categoryId, boolean includeInactive)   // D-42
            throws PointsEngineRuleServiceException;

    @Transactional(value = "warehouse", propagation = Propagation.SUPPORTS, readOnly = true)
    BenefitCategoryListResponse listBenefitCategories(BenefitCategoryFilter filter, int page, int size)
            throws PointsEngineRuleServiceException;

    @Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
    BenefitCategoryDto activateBenefitCategory(int orgId, int categoryId, int actorUserId)
            throws PointsEngineRuleServiceException;

    @Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
    void deactivateBenefitCategory(int orgId, int categoryId, int actorUserId)
            throws PointsEngineRuleServiceException;
}
// Confidence: C6 — exact mirror of existing createOrUpdateSlab etc. (code-analysis-emf §5).
```

### F.4 Editor additions on `PointsEngineRuleEditorImpl`

Same 6 signatures as §F.3, **without** `@Transactional` (editor is a pass-through validator; txn lives on service). Confidence: C5.

### F.5 Thrift handler additions on `PointsEngineRuleConfigThriftImpl`

```java
// emf-parent — additions to existing class
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public BenefitCategoryDto createBenefitCategory(int orgId, BenefitCategoryDto dto, int actorUserId)
        throws PointsEngineRuleServiceException, TException;

@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public BenefitCategoryDto updateBenefitCategory(int orgId, int categoryId,
                                                BenefitCategoryDto dto, int actorUserId)
        throws PointsEngineRuleServiceException, TException;

@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public BenefitCategoryDto getBenefitCategory(int orgId, int categoryId, boolean includeInactive)   // D-42
        throws PointsEngineRuleServiceException, TException;

@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#filter.orgId", requestId = "#serverReqId")
public BenefitCategoryListResponse listBenefitCategories(BenefitCategoryFilter filter, int page, int size)
        throws PointsEngineRuleServiceException, TException;

@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public BenefitCategoryDto activateBenefitCategory(int orgId, int categoryId, int actorUserId)
        throws PointsEngineRuleServiceException, TException;

@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public void deactivateBenefitCategory(int orgId, int categoryId, int actorUserId)
        throws PointsEngineRuleServiceException, TException;
// Confidence: C6 — SpEL path `#filter.orgId` on list confirmed against `@MDCData` usage in code-analysis-emf §2;
// all other methods take orgId as first arg → `#orgId`.
```

### F.6 Facade

```java
// intouch-api-v3
package com.capillary.intouchapiv3.facade.benefitCategory;

import com.capillary.intouchapiv3.dto.benefitCategory.*;
import com.capillary.intouchapiv3.exceptionResources.*;
import org.springframework.stereotype.Component;
import java.util.Optional;

@Component
public class BenefitCategoryFacade {

    // Constructor-injects Thrift client + dedicated BenefitCategoryResponseMapper (D-45 / Q7-15).
    // Mapper lives in com.capillary.intouchapiv3.facade.benefitCategory.mapper — see §F.6a below.
    public BenefitCategoryFacade(/* RPCService wiring + BenefitCategoryResponseMapper */) {}

    public BenefitCategoryResponse create(int orgId, int actorUserId, BenefitCategoryCreateRequest request)
            throws ConflictException, InvalidInputException, EMFThriftException;

    public BenefitCategoryResponse update(int orgId, int actorUserId, int categoryId, BenefitCategoryUpdateRequest request)
            throws ConflictException, NotFoundException, InvalidInputException, EMFThriftException;

    public BenefitCategoryResponse get(int orgId, int categoryId, boolean includeInactive)   // D-42
            throws NotFoundException, EMFThriftException;

    public BenefitCategoryListPayload list(int orgId, Integer programId, String isActiveFilter, int page, int size)
            throws InvalidInputException, EMFThriftException;

    public Optional<BenefitCategoryResponse> activate(int orgId, int actorUserId, int categoryId)
            throws ConflictException, NotFoundException, EMFThriftException;   // D-39 Optional return

    public void deactivate(int orgId, int actorUserId, int categoryId)
            throws NotFoundException, EMFThriftException;
}
// Confidence: C6 — signature set pinned by ADR-006 amendment + D-39.
```

### F.6a Mapper (D-45 / Q7-15 resolution — dedicated `mapper/` subpackage)

```java
// intouch-api-v3
package com.capillary.intouchapiv3.facade.benefitCategory.mapper;

import com.capillary.intouchapiv3.dto.benefitCategory.*;
import com.capillary.pointsengine.rules.thrift.*;   // generated from IDL
import org.springframework.stereotype.Component;
import java.util.Date;

@Component
public class BenefitCategoryResponseMapper {

    // Thrift DTO → REST response DTO (millis i64 → Date @JsonFormat UTC per ADR-008).
    public BenefitCategoryResponse toResponse(BenefitCategoryDto dto);

    // REST create request → Thrift DTO (id unset; server fills).
    public BenefitCategoryDto toCreateDto(int orgId, BenefitCategoryCreateRequest request);

    // REST update request → Thrift DTO (id=categoryId from path; programId unchanged — carried in loaded entity).
    public BenefitCategoryDto toUpdateDto(int orgId, int categoryId, BenefitCategoryUpdateRequest request);

    // List: converts Thrift list response → REST list payload.
    public BenefitCategoryListPayload toListPayload(BenefitCategoryListResponse thriftResp);

    // Helper: Thrift millis → java.util.Date (UTC); null/0L → null.
    static Date millisToDate(long millis);

    // Helper: java.util.Date → Thrift i64 millis; null → 0L.
    static long dateToMillis(Date d);
}
// Confidence: C6 — dedicated mapper pattern confirmed via
//   intouch-api-v3/.../unified/promotion/mapper/CustomerPromotionResponseMapper.java (exemplar).
// Stateless; SDET unit-tests directly (no Spring context).
```

### F.7 Controller

```java
// intouch-api-v3
package com.capillary.intouchapiv3.resources;

import com.capillary.intouchapiv3.facade.benefitCategory.BenefitCategoryFacade;
import com.capillary.intouchapiv3.dto.benefitCategory.*;
import com.capillary.intouchapiv3.authentication.AbstractBaseAuthenticationToken;
import com.capillary.intouchapiv3.model.ResponseWrapper;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.validation.annotation.Validated;
import javax.validation.Valid;
import javax.validation.constraints.*;
import java.util.Optional;

@RestController
@RequestMapping("/v3/benefitCategories")
@Validated   // for @Min/@Max on @RequestParam
public class BenefitCategoriesV3Controller {

    private final BenefitCategoryFacade facade;

    public BenefitCategoriesV3Controller(BenefitCategoryFacade facade) { this.facade = facade; }

    @PostMapping
    public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> create(
            @Valid @RequestBody BenefitCategoryCreateRequest request,
            AbstractBaseAuthenticationToken user);

    @PutMapping("/{id}")
    public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> update(
            @PathVariable("id") int id,
            @Valid @RequestBody BenefitCategoryUpdateRequest request,
            AbstractBaseAuthenticationToken user);

    @GetMapping("/{id}")
    public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> get(
            @PathVariable("id") int id,
            @RequestParam(name = "includeInactive", defaultValue = "false") boolean includeInactive,   // D-42
            AbstractBaseAuthenticationToken user);

    @GetMapping
    public ResponseEntity<ResponseWrapper<BenefitCategoryListPayload>> list(
            @RequestParam(value = "programId", required = false) Integer programId,
            @RequestParam(value = "isActive", required = false, defaultValue = "true") String isActive,
            @RequestParam(value = "page",     required = false, defaultValue = "0")    @Min(0) int page,
            @RequestParam(value = "size",     required = false, defaultValue = "50")   @Min(1) @Max(100) int size,
            AbstractBaseAuthenticationToken user);

    @PatchMapping("/{id}/activate")
    public ResponseEntity<ResponseWrapper<BenefitCategoryResponse>> activate(
            @PathVariable("id") int id,
            AbstractBaseAuthenticationToken user);
    // Impl returns 204 No Content if facade.activate(...) → Optional.empty (idempotent);
    // 200 OK + wrapper if populated (state change). D-39.

    @PatchMapping("/{id}/deactivate")
    public ResponseEntity<Void> deactivate(
            @PathVariable("id") int id,
            AbstractBaseAuthenticationToken user);
    // Always 204 per ADR-006 unchanged on deactivate.
}
// Confidence: C6.
```

### F.8 DTOs

```java
// intouch-api-v3
package com.capillary.intouchapiv3.dto.benefitCategory;

import com.fasterxml.jackson.annotation.*;
import javax.validation.constraints.*;
import lombok.Getter;
import lombok.Setter;
import java.util.Date;
import java.util.List;

// D-44 (Q7-14=A) — DTO split convention: intouch-api-v3 DTOs use Lombok (305 precedent files);
// emf-parent JPA entities remain hand-written (P-01 Benefits.java pattern preserved).

@Getter @Setter
@JsonIgnoreProperties(ignoreUnknown = true)
public class BenefitCategoryCreateRequest {
    @NotNull @Positive                      private Integer programId;
    @NotBlank @Size(max = 255)              private String name;
    @NotNull @Size(min = 1)                 private List<@NotNull @Positive Integer> slabIds;
}

@Getter @Setter
@JsonIgnoreProperties(ignoreUnknown = true)
public class BenefitCategoryUpdateRequest {
    @NotBlank @Size(max = 255)              private String name;
    @NotNull                                private List<@NotNull @Positive Integer> slabIds;
    // Empty list permissible → clears all mappings.
}

@Getter @Setter
public class BenefitCategoryResponse {
    private int id;
    private int orgId;
    private int programId;
    private String name;
    private String categoryType;
    private List<Integer> slabIds;
    private boolean isActive;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")
    private Date createdOn;
    private int createdBy;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", timezone = "UTC")
    private Date updatedOn;
    private Integer updatedBy;
}

@Getter @Setter
public class BenefitCategoryListPayload {
    private List<BenefitCategoryResponse> data;
    private int page;
    private int size;
    private long total;
}
// Confidence: C6 — mirrors code-analysis-intouch §4 DTO patterns; Lombok usage pattern
//   verified via grep (305 files in intouch-api-v3 use @Getter/@Setter). D-44 / Q7-14=A.
```

### F.9 Exception + Advice delta

```java
// intouch-api-v3
package com.capillary.intouchapiv3.exceptionResources;

public class ConflictException extends RuntimeException {
    private final String code;
    public ConflictException(String code, String message) { super(message); this.code = code; }
    public String getCode() { return code; }
}
// Confidence: C7 — D-31.
```

```java
// TargetGroupErrorAdvice — addition
@ExceptionHandler(ConflictException.class)
public ResponseEntity<ResponseWrapper<String>> handleConflict(ConflictException ex) {
    ResponseWrapper<String> body = new ResponseWrapper<>();
    body.addError(new ApiError(409L, ex.getMessage()));   // signature per code-analysis-intouch §6
    return new ResponseEntity<>(body, HttpStatus.CONFLICT);
}
// Confidence: C6 — body-construction pattern lifted from existing InvalidInputException handler.
```

### F.10 Thrift IDL (final authoritative)

```thrift
// thrift-ifaces-pointsengine-rules / src/main/thrift/pointsengine_rules.thrift
// Version: 1.84 (bump from 1.83). All additions — zero breaking changes (G-09.5).

enum BenefitCategoryType {
  BENEFITS = 1
}

struct BenefitCategoryDto {
  1:  optional i32 id,
  2:  required i32 orgId,
  3:  required i32 programId,
  4:  required string name,
  5:  required BenefitCategoryType categoryType = BenefitCategoryType.BENEFITS,
  6:  required list<i32> slabIds,
  7:  required bool isActive,
  8:  required i64 createdOn,            // epoch millis UTC (ADR-008)
  9:  required i32 createdBy,
  10: optional i64 updatedOn,
  11: optional i32 updatedBy,
  12: optional bool stateChanged = true  // Q7-13 assumption C5: used by activate idempotency signalling
}

struct BenefitCategoryFilter {
  1: required i32 orgId,
  2: optional i32 programId,
  3: optional bool isActive
}

struct BenefitCategoryListResponse {
  1: required list<BenefitCategoryDto> data,
  2: required i32 page,
  3: required i32 size,
  4: required i64 total
}

// service PointsEngineRuleService { ... existing ~60 methods ...

  BenefitCategoryDto createBenefitCategory(
      1: required i32 orgId,
      2: required BenefitCategoryDto dto,
      3: required i32 actorUserId
  ) throws (1: PointsEngineRuleServiceException ex);

  BenefitCategoryDto updateBenefitCategory(
      1: required i32 orgId,
      2: required i32 categoryId,
      3: required BenefitCategoryDto dto,
      4: required i32 actorUserId
  ) throws (1: PointsEngineRuleServiceException ex);

  BenefitCategoryDto getBenefitCategory(
      1: required i32 orgId,
      2: required i32 categoryId,
      3: optional bool includeInactive = false         // D-42 — audit-inclusive read (Q7-12=A)
  ) throws (1: PointsEngineRuleServiceException ex);

  BenefitCategoryListResponse listBenefitCategories(
      1: required BenefitCategoryFilter filter,
      2: required i32 page,
      3: required i32 size
  ) throws (1: PointsEngineRuleServiceException ex);

  BenefitCategoryDto activateBenefitCategory(
      1: required i32 orgId,
      2: required i32 categoryId,
      3: required i32 actorUserId
  ) throws (1: PointsEngineRuleServiceException ex);
  // D-39 amendment: returns full DTO on state change; stateChanged=false on idempotent no-op (Q7-13 C5).

  void deactivateBenefitCategory(
      1: required i32 orgId,
      2: required i32 categoryId,
      3: required i32 actorUserId
  ) throws (1: PointsEngineRuleServiceException ex);

// } end service
```

---

## G. Open Questions for User + Assumptions Made

### G.1 QUESTIONS FOR USER — ALL RESOLVED (2026-04-18)

All 5 Designer open questions were resolved by the user as `Q7:C, Q12:A, Q13:A, Q14:A, Q15:A`.
Resolutions are recorded as **D-41..D-45** in `session-memory.md` and as amendments in §18 below.

| # | Question (summary) | User answer | Recorded as | Status |
|---|--------------------|-------------|-------------|--------|
| Q7-11 | Add batch-existence method on `PeProgramSlabDao` vs reuse existing `findByProgram` + in-memory Set ops? | **C** — reuse existing `findByProgram` (no cross-repo DAO modification) | **D-41** | ✅ RESOLVED |
| Q7-12 | GET /{id} active-only vs active+inactive vs explicit opt-in? | **A** — default active-only; `?includeInactive=true` opt-in for audit access | **D-42** | ✅ RESOLVED (overrides Designer recommendation B) |
| Q7-13 | How does EMF signal "no state change" on activate? | **A** — `stateChanged: bool` field on `BenefitCategoryDto` (Thrift field 12); facade detects `stateChanged=false` → `Optional.empty()` | **D-43** | ✅ RESOLVED |
| Q7-14 | Hand-written vs Lombok for DTO/entity boilerplate? | **A** — split: JPA entities hand-written (`Benefits.java` P-01 pattern); DTOs use `@Getter @Setter` (305 Lombok files in intouch-api-v3) | **D-44** | ✅ RESOLVED |
| Q7-15 | Dedicated mapper class vs inline static? | **A** — dedicated `BenefitCategoryResponseMapper` in `com.capillary.intouchapiv3.facade.benefitCategory.mapper` subpackage (matches `CustomerPromotionResponseMapper` exemplar) | **D-45** | ✅ RESOLVED |

### G.2 ASSUMPTIONS MADE (C5 — documented; user may override)

| # | Assumption | Confidence | Rationale / evidence anchor |
|---|------------|------------|-----------------------------|
| A7-01 | Facade class name is `BenefitCategoryFacade` (vs `*Service`). | C5 | Resolves Q7-03 in architect doc. Platform has both naming conventions; `*Facade` chosen for consistency with controller → facade → Thrift layered split. |
| A7-02 | Controller package: `com.capillary.intouchapiv3.resources`. | C5 | Resolves Q7-04. Matches `TargetGroupController` / `MilestoneController` placement (code-analysis-intouch §1). |
| A7-03 | GET list wrapper shape: pagination fields live INSIDE `ResponseWrapper.data` as `BenefitCategoryListPayload{data, page, size, total}`. | C5 | Resolves Q7-05. Matches `TargetGroupV3Controller` list response shape (code-analysis-intouch §1). Alternative (pagination as top-level ResponseWrapper fields) would require a new envelope subclass — unnecessary ceremony. |
| A7-04 | Thrift timestamp fields named bare `createdOn` / `updatedOn` (no `InMillis` suffix). | C5 | Resolves Q7-06. pointsengine_rules.thrift convention (code-analysis-thrift-ifaces §3); existing BenefitsConfigData uses bare names. |
| A7-05 | Audit columns written manually via `new Date()` inside service code (no `@PrePersist`). | C5 | Resolves Q7-10. Platform pattern in `PointsEngineRuleService.createOrUpdateSlab` (code-analysis-emf §5 line 3669-3671). |
| A7-06 | Name normalization: `trim()` applied at facade entry; case-sensitive uniqueness (LOWER is NOT applied); no Unicode NFC normalization. `VARCHAR(255)` is the authoritative max length (declared in DDL). | C5 | Resolves Q7-01. Matches `Benefits.name` observed behavior (no LOWER wrapping in active queries — code-analysis-emf §3). Downgrade to <C5 and ask user if product has a stated case-insensitive policy. |
| A7-07 | `isActive` query-param accepts strings "true" / "false" / "all"; controller maps to `Boolean isActive` (null for "all"). Unrecognized value → 400 `BC_BAD_ACTIVE_FILTER`. | C5 | ADR-011 pattern; explicit "all" sentinel avoids three-state boolean in @RequestParam. |
| A7-08 | Tenant `orgId` extracted via `AbstractBaseAuthenticationToken user` argument; cast from `long` to `int` at controller boundary with overflow guard (`Math.toIntExact`). | C5 | `IntouchUser.getOrgId()` returns `long` (code-analysis-intouch §5); Thrift uses `i32`. Collision is improbable (orgIds fit in int in practice) but overflow guard documented. |
| A7-09 | HTTP 304 **NOT** used for `/activate` idempotent no-op — 204 used per ADR-006 amended. | C5 | ADR-006 explicitly pins 204 on idempotent no-op; 304 would be non-idiomatic on PATCH. |
| A7-10 | Thrift method `listBenefitCategories` takes `BenefitCategoryFilter` (no separate `orgId` arg) — orgId travels inside the filter struct. `@MDCData(orgId="#filter.orgId")` SpEL expression. | C5 | Matches §9 IDL + SpEL path-traversal support in `@MDCData` (code-analysis-emf §2 aspect section). |
| A7-11 | `benefit_category_id` (not `category_id`) is the FK column name on the mapping table — matches the proposed JPA field name and the §7.2 DDL. | C5 | ADR-007 DDL §7.2 line 744 pins the column name. |
| A7-12 | `ConflictException` carries both `code` (machine-readable, e.g., `BC_NAME_TAKEN_ACTIVE`) and `message` (human-readable). Advice surfaces `code` as `ApiError.code`, `message` as `ApiError.message`. | C5 | Matches existing `InvalidInputException` pattern from code-analysis-intouch §6. |
| ~~A7-13~~ | ~~`PeProgramSlabDao` — if the batch-existence method does not exist (Q7-11), Phase 7 Designer considers adding it to that DAO an [MODIFIED] change on emf-parent.~~ | ~~C5~~ | **SUPERSEDED by D-41** (Q7-11=C): no DAO modification; reuse existing `findByProgram(orgId, programId)` + in-memory Set ops. See §18.1 below. |

### G.3 RED-phase readiness

**Verdict**: `true` — every signature is compile-safe, and all 5 Designer open questions have been resolved
by user (D-41..D-45, 2026-04-18). SDET Phase 9 can import types, create skeleton classes with method bodies
throwing `UnsupportedOperationException`, and write tests that fail RED.

**Resolution-driven amendments now baked into §A..§F**:
- Q7-11=C → D-41: no cross-repo DAO modification; `PeProgramSlabDao.findByProgram` reused with in-memory Set ops (see §18.1).
- Q7-12=A → D-42: GET /{id} signature takes `boolean includeInactive`; DAO split into `findByOrgIdAndId` + `findActiveByOrgIdAndId` (see §B.3, §F.6, §F.7, §F.10).
- Q7-13=A → D-43: `BenefitCategoryDto` Thrift field 12 `stateChanged: bool` retained; facade returns `Optional.empty()` when `stateChanged=false` (§B.5, §F.10).
- Q7-14=A → D-44: DTOs carry `@Getter @Setter` Lombok; entities stay hand-written (§A.3 rows 22-25, §F.8).
- Q7-15=A → D-45: dedicated `BenefitCategoryResponseMapper` in `facade.benefitCategory.mapper` subpackage (§A.3 row 27a, §F.6a).

**Conditions that would flip readiness to `false`** (none currently triggered):
- User overrides A7-04 (Thrift timestamp naming) — would trigger IDL rewrite.
- User overrides A7-03 (list wrapper shape) — would trigger DTO rewrite + controller return-type change.

**Phase 9 SDET receives**:
- The 6 operations with exact method signatures across 5 layers.
- DAO queries specified in JPQL (for `@DataJpaTest` repository tests).
- Entity column mapping for DDL-integration tests.
- Error mapping table for `@ExceptionHandler` + Thrift-exception tests.
- Pattern exemplars with evidence anchors for mirror-style testing.
- The dedicated `BenefitCategoryResponseMapper` contract — SDET writes pure-unit mapping tests.

---

## 17. Appendix — Evidence Anchors Quick Reference

| Topic | Source |
|-------|--------|
| `OrgEntityIntegerPKBase` + `@Embeddable` PK pattern | `code-analysis-emf-parent.md` §3.1 (`Benefits.java`) |
| `GenericDao<T, PK>` + Spring Data + QueryDSL | `code-analysis-emf-parent.md` §4 (`BenefitsDao.java`) |
| `@ExposedCall(thriftName="pointsengine-rules")` registration | `code-analysis-emf-parent.md` §2 |
| `@Trace(dispatcher=true) @MDCData` on handler | `code-analysis-emf-parent.md` §2 |
| Service `@Transactional(value="warehouse")` | `code-analysis-emf-parent.md` §5 |
| Manual `new Date()` in service (Q7-10 basis) | `code-analysis-emf-parent.md` §5, line 3669-3671 |
| Thrift client `RPCService.rpcClient(..., 9199, 60000)` | `code-analysis-intouch-api-v3.md` §2 |
| `ResponseWrapper<T>` + `ApiError{code, message}` | `code-analysis-intouch-api-v3.md` §4 + §6 |
| `TargetGroupErrorAdvice` exception map | `code-analysis-intouch-api-v3.md` §6 |
| Jackson UTC `@JsonFormat` on DTO Date fields | `code-analysis-intouch-api-v3.md` §4 |
| `AbstractBaseAuthenticationToken` + `user.getOrgId()` long | `code-analysis-intouch-api-v3.md` §5 |
| `BenefitsConfigData` Thrift CRUD template (BenefitCategory structural twin) | `code-analysis-thrift-ifaces.md` lines 1276-1282 |
| `PointsEngineRuleServiceException{errorMessage, statusCode}` | `code-analysis-thrift-ifaces.md` §3 |
| Pointsengine-rules timestamp naming convention (bare `createdOn`) | `code-analysis-thrift-ifaces.md` §3 |
| Three-boundary timestamp decision | `01-architect.md` ADR-008; `session-memory.md` D-24 |
| No `@Version` / LWW posture | `01-architect.md` ADR-001; `session-memory.md` D-33 |
| No advisory lock / app-level uniqueness only | `01-architect.md` ADR-012 amended; `session-memory.md` D-38 |
| Asymmetric activate response | `01-architect.md` ADR-006 amended; `session-memory.md` D-39 |
| No `@PreAuthorize` on MVP endpoints | `01-architect.md` ADR-010; `session-memory.md` D-37 |

---

## 18. Post-LLD Amendments — Designer Question Resolutions (2026-04-18)

> **Context**: User resolved all 5 Designer open questions (Q7-11..Q7-15) after the initial LLD
> was produced. This section is the authoritative delta from §A..§G. The preceding sections
> have been amended in-place to reflect these decisions. Any divergence between earlier
> sections and §18 is a bug — §18 wins.
>
> **User inputs (2026-04-18)**: `Q7:C, Q12:A, Q13:A, Q14:A, Q15:A`.

### 18.1 D-41 — `PeProgramSlabDao` reuse (Q7-11=C)

**Decision**: NO modification to `PeProgramSlabDao`. Reuse existing method:

```java
// Existing method — PeProgramSlabDao:27 (VERIFIED C7 via Read)
@Query("SELECT s FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2")
List<ProgramSlab> findByProgram(int orgId, int programId);
```

Service-layer validation for "all request slabIds exist AND belong to request.programId" runs in-memory:

```java
Set<Integer> existingIds = programSlabDao.findByProgram(orgId, programId)
    .stream()
    .map(ps -> ps.getPk().getId())
    .collect(toSet());

Set<Integer> missing = new HashSet<>(requestSlabIds);
missing.removeAll(existingIds);
if (!missing.isEmpty()) {
    throw new PointsEngineRuleServiceException(
        "BC_UNKNOWN_SLAB", 400, "Unknown slab ids: " + missing);
}
// Cross-program check: if a slab belongs to a DIFFERENT program,
// it won't appear in findByProgram(orgId, programId) → same path as BC_UNKNOWN_SLAB (unified error).
```

**Rationale**:
- D-26 scale envelope (SMALL: ≤10 slabs typical per program, hard cap small) makes in-memory filtering negligible.
- Avoids cross-repo DAO modification and the associated ripple (unit tests, QueryDSL, migration risk).
- If any future program ever carries > 100 slabs, revisit with a JPQL `IN (:candidateIds)` variant.

**Effect on artifacts**: A7-13 in §G.2 is struck (superseded). §A.2 DAO row 14 unchanged
(no new method on `PeProgramSlabDao`). §B.1 create-slab-validation pseudocode (lines ~200-220)
amended to use `findByProgram` + Set ops — see in-line.

### 18.2 D-42 — GET /{id} `?includeInactive=true` audit flag (Q7-12=A — **OVERRIDES Designer recommendation B**)

**Decision**: GET /{id} defaults to active-only (404 on soft-deleted rows), with explicit
`?includeInactive=true` opt-in for audit/support access.

**Designer's original recommendation was B** ("active-only-always, no query param") on YAGNI grounds.
**User overrides** to A, preferring a richer API surface that supports audit access without requiring a
follow-up endpoint later.

**Contract delta**:

| Layer | Signature change |
|-------|------------------|
| REST Controller | `get(int id, @RequestParam(name="includeInactive", defaultValue="false") boolean includeInactive, user)` — §F.7 |
| Facade | `get(int orgId, int id, boolean includeInactive)` — §F.6 |
| Thrift IDL | `getBenefitCategory(orgId, categoryId, 3: optional bool includeInactive=false)` — §F.10 |
| Service | `getBenefitCategory(int orgId, int categoryId, boolean includeInactive)` — §F.3 |
| DAO | **TWO** methods: `findByOrgIdAndId(int,int)` (any state) + `findActiveByOrgIdAndId(int,int)` (active only) — §B.3 |

**Routing rule**:
- Default path (`includeInactive=false`) → `findActiveByOrgIdAndId` → 404 on is_active=false rows.
- Audit path (`includeInactive=true`) → `findByOrgIdAndId` → 200 on any row.
- **All mutation paths** (update, activate→load-for-reactivation, deactivate→load-if-active) use
  `findActiveByOrgIdAndId` unconditionally (aligns with D-27 "writes on inactive forbidden").

### 18.3 D-43 — `stateChanged` signalling on activate no-op (Q7-13=A)

**Decision**: `BenefitCategoryDto` Thrift struct field 12 `optional bool stateChanged = true` is retained.
On idempotent no-op, EMF returns the DTO with `stateChanged=false`; facade detects this and returns
`Optional.empty()` → controller emits 204. On actual state change, `stateChanged` is absent or true, DTO
is populated → 200 + wrapper.

**Rationale**: Least-invasive option. No new exception code (b was rejected: HTTP 304 is not idiomatic on
PATCH). No null-return (c was rejected: violates Thrift `required` return semantics). The extra field
lives only on this DTO and defaults true, so unused by other Thrift consumers.

**Artifact status**: §F.10 IDL already contains `12: optional bool stateChanged = true`; §B.5
already describes this sentinel. No further amendment needed — this is pinned as authoritative.

### 18.4 D-44 — DTO/Entity boilerplate split (Q7-14=A)

**Decision** (split convention):

| Artifact | Convention | Rationale |
|----------|------------|-----------|
| emf-parent JPA entities (`BenefitCategory`, `BenefitCategorySlabMapping`, inner PK classes) | **Hand-written** getters/setters/equals/hashCode | Matches `Benefits.java` P-01 exemplar. JPA providers can be sensitive to Lombok on `@Embeddable` PK classes; hand-written preserves equality/hash contract explicitly. |
| intouch-api-v3 DTOs (`BenefitCategoryCreateRequest`, `BenefitCategoryUpdateRequest`, `BenefitCategoryResponse`, `BenefitCategoryListPayload`) | `@Getter @Setter` (Lombok) | Evidence: `grep -r "@Getter\|@Setter" intouch-api-v3` → 305 files use Lombok. Fresh DTOs should follow established platform convention. |

**Effect on artifacts**: §A.3 rows 22-25 show `@Getter @Setter` annotation. §F.8 DTO class bodies
rewritten with Lombok annotations, getters/setters comments dropped. emf-parent entities unchanged.

### 18.5 D-45 — Dedicated mapper in `mapper/` subpackage (Q7-15=A)

**Decision**: Single dedicated mapper class `BenefitCategoryResponseMapper` in
`com.capillary.intouchapiv3.facade.benefitCategory.mapper` subpackage. `@Component`, stateless,
SDET-unit-testable in isolation.

**Evidence**: Exemplar verified at
`intouch-api-v3/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/facade/unified/promotion/mapper/CustomerPromotionResponseMapper.java`
— established platform pattern.

**Scope** (method signatures in §F.6a):
- Thrift DTO ↔ REST response DTO (Date ↔ i64 millis UTC per ADR-008).
- REST request DTOs → Thrift DTOs for write operations.
- List response unwrap/rewrap.
- Two static helpers (`millisToDate`, `dateToMillis`).

**Effect on artifacts**: §A.3 new row 27a. §F.6 Facade constructor injects the mapper. §F.6a new section
defines the mapper contract.

### 18.6 New Constraint: C-39

**C-39 (NEW)**: `GET /v3/benefitCategories/{id}` MUST support `?includeInactive=true` audit query
parameter. When absent or `false`, soft-deleted categories return 404. When `true`, soft-deleted
categories return 200 with `isActive=false` in the response. The audit path is read-only and does
**not** bypass tenant `orgId` scoping (G-07). (Source: D-42.)

### 18.7 Summary of decisions added

| Decision | Source question | User answer | Match with Designer recommendation? |
|----------|-----------------|-------------|-------------------------------------|
| D-41 | Q7-11 | C (reuse `findByProgram` + in-memory Set ops) | Match |
| D-42 | Q7-12 | A (`?includeInactive=true` audit flag) | **Override** (Designer recommended B — active-only always) |
| D-43 | Q7-13 | A (`stateChanged` field) | Match |
| D-44 | Q7-14 | A (split: entities hand-written, DTOs Lombok) | Match |
| D-45 | Q7-15 | A (dedicated `mapper/` subpackage) | Match |

### 18.8 RED-phase readiness after §18

**Readiness**: `true`. Every amendment in §18 preserves compile-safety. SDET Phase 9 can proceed.

---

**End of Designer (Phase 7) — CAP-185145.**
