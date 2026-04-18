# Backend Readiness — Benefit Category CRUD (CAP-185145)

> Phase 10b audit · 2026-04-19

---

## Verdict

**READY WITH WARNINGS**

---

## Summary

| Metric | Value |
|--------|-------|
| Total checks | 38 |
| PASS | 29 |
| WARN | 6 |
| FAIL | 3 |
| Critical blockers (must fix before Phase 11) | 3 |
| Overall confidence | C6 (code-verified; M5 runtime deferred per user directive) |

---

## Findings per area

### 1. Query Performance

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 1.1 | N+1 on LIST — bulk `findActiveSlabIdsForCategories` in single query | PASS | `PointsEngineRuleService.java:4709-4722` — `categoryIds` collected first, single bulk JPQL call | — | C7 |
| 1.2 | N+1 on GET — `findActiveSlabIdsByCategoryId` single query | PASS | `PointsEngineRuleService.java:4678` | — | C7 |
| 1.3 | **N+1 on CREATE — `saveAndFlush` inside slab loop** | **WARN** | `PointsEngineRuleService.java:4534-4545` — `saveAndFlush(mapping)` called once per slabId in a loop. D-26 scale (≤10 slabs) mitigates in practice, but no `saveAll` batch | WARN | C7 |
| 1.4 | Tenant (org_id) filter present on all DAO queries | PASS | All `@Query` methods in `BenefitCategoryDao.java:31-110` and `BenefitCategorySlabMappingDao.java:27-67` include `WHERE … pk.orgId = :orgId` or `m.pk.orgId = :orgId` | — | C7 |
| 1.5 | Pagination bounds — Spring Data 1.x `new PageRequest(page, size)` | PASS | `PointsEngineRuleService.java:4702-4703` — uses constructor form (fixed by D-59/M3a) | — | C7 |
| 1.6 | Unbounded list queries absent | PASS | `findPage` uses `Pageable`; `findActiveSlabIdsForCategories` is bounded by `categoryIds` from a paginated result | — | C6 |
| 1.7 | Service-side size cap enforced | PASS | `PointsEngineRuleService.java:4695` — `if (size > 200) size = 200;` | — | C7 |

**Index Audit (sub-area 1.8 — detail in Section 8)**

---

### 2. Thrift Backward Compatibility

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 2.1 | All 4 new structs added as net-new (no removal) | PASS | `pointsengine_rules.thrift` diff — `BenefitCategoryDto`, `BenefitCategoryFilter`, `BenefitCategoryListResponse`, `BenefitCategoryType` all appended after existing structs | — | C7 |
| 2.2 | All new struct fields are `optional` except required non-nullable contract fields | PASS | `id`, `createdOn/updatedOn/updatedBy/stateChanged` all `optional`; `orgId/programId/name/categoryType/slabIds/isActive` required — correct for create path | — | C7 |
| 2.3 | No existing field IDs renumbered or removed | PASS | Diff shows only additions to `PointsEngineRuleService` at end of file; zero existing struct/method modification | — | C7 |
| 2.4 | `serverReqId` on all 6 new methods | PASS | `pointsengine_rules.thrift:1397-1433` — all 6 methods carry `string serverReqId` as last parameter | — | C7 |
| 2.5 | `tillId` (not `actorUserId`) naming convention | PASS | IDL uses `i32 tillId`; ThriftImpl handlers use `int tillId, String serverReqId`; salvage S3/S4 confirmed fix (Phase 9) | — | C7 |
| 2.6 | `stateChanged` optional sentinel declared correctly | PASS | `BenefitCategoryDto` field 12: `optional bool stateChanged` — matches D-43 | — | C7 |
| 2.7 | All 6 methods declare `throws (1: PointsEngineRuleServiceException ex)` | PASS | `pointsengine_rules.thrift:1402,1412,1420,1427,1433,1437` | — | C7 |
| 2.8 | **`BenefitCategoryDto` has `required slabIds` and `required isActive`** — callers of existing methods unaffected (no existing methods modified) | PASS | Additive only; no breaking change to any pre-existing Thrift consumer | — | C6 |

---

### 3. Cache Invalidation

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 3.1 | `BenefitCategory` write paths (CREATE/UPDATE/ACTIVATE/DEACTIVATE) do not evict any cache | **WARN** | No `cacheEvictHelper` or `applicationCacheManager` calls in the benefit-category section of `PointsEngineRuleService.java:4466-4880`. Other write paths (slab, program) do evict `evictProgramIdCache`. If `InfoLookupService` or any downstream service caches programs/slabs that include category data, stale reads are possible. | WARN | C5 |
| 3.2 | `PointsEngineRulesThriftService.java` benefit category methods not annotated `@Cacheable` (read paths not cached at gateway) | PASS | Methods at lines 433-537 have no `@Cacheable` annotation — consistent with the CRUD nature (mutations go stale immediately if cached) | — | C7 |
| 3.3 | No existing cached method (`getAllPrograms`, `getAllAlternateCurrencies`) is invalidated by category writes | **WARN** | If any program-level cache in `PointsEngineRulesThriftService` incorporates category data in the future, no eviction hook exists. Current scope is new tables only — INFO for now, but risk grows if category data is embedded into program caches | WARN | C4 |

---

### 4. Connection / Resource Management

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 4.1 | Thrift client uses connection pool via `RPCService.rpcClient` (60s timeout) | PASS | `PointsEngineRulesThriftService.java:44` — `RPCService.rpcClient(..., 9199, 60000)` — matches existing convention for all other methods in the file | — | C7 |
| 4.2 | Write transactions bounded by `@Transactional(value="warehouse", propagation=REQUIRED)` | PASS | `PointsEngineRuleService.java:4470-4471, 4555-4556, 4739-4740, 4799-4800` — all mutating methods annotated | — | C7 |
| 4.3 | Read transactions use `propagation=SUPPORTS, readOnly=true` | PASS | GET at `4657-4658`; LIST at `4682-4683` | — | C7 |
| 4.4 | Deactivate cascade (softDelete category + softDelete mappings) in single transaction | PASS | Both `softDeleteIfActive` and `bulkSoftDeleteByCategory` called within `deactivateBenefitCategory` under a single `@Transactional(warehouse, REQUIRED)` scope — ADR-004 / D-36 honoured | — | C7 |
| 4.5 | No raw `DriverManager.getConnection()` or manual streams | PASS | Spring Data JPA + `saveAndFlush` / `@Modifying @Query` pattern only | — | C6 |
| 4.6 | Diff-apply update (slab adds) uses `saveAndFlush` inside loop | **WARN** | `PointsEngineRuleService.java:4625-4637` — one `saveAndFlush` per new slab in update path; same pattern as create. Safe at D-26 scale (≤10 slabs). No resource leak, but flush-per-row at larger scale. | WARN | C7 |

---

### 5. Error Handling at Boundaries

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 5.1 | All 6 Thrift method calls in `PointsEngineRulesThriftService` catch `PointsEngineRuleServiceException` + `TException` | PASS | Lines 433-537: every method catches both and re-throws `PointsEngineRuleServiceException` (for business) or wraps in `EMFThriftException` (for transport) | — | C7 |
| 5.2 | `BenefitCategoryFacade` wraps checked exception as `BenefitCategoryBusinessException` | PASS | `BenefitCategoryFacade.java:158-179` — preserves `statusCode` and `errorMessage` | — | C7 |
| 5.3 | `TargetGroupErrorAdvice` maps `BenefitCategoryBusinessException` to correct HTTP codes | PASS | `TargetGroupErrorAdvice.java:342-363` — `409 CONFLICT`, `404 NOT_FOUND`, `400 BAD_REQUEST`, `500` default | — | C7 |
| 5.4 | Bean Validation failure → 400 via `MethodArgumentNotValidException` handler | PASS | `TargetGroupErrorAdvice.java:97-108` existing handler; `@Valid` on controller method parameters | — | C7 |
| 5.5 | `MethodArgumentTypeMismatchException` (e.g. `?isActive=foo`) → 400, scoped to controller | PASS | `BenefitCategoriesV3Controller.java:135-145` — controller-scoped `@ExceptionHandler` | — | C7 |
| 5.6 | **`deactivateBenefitCategory` can silently succeed on already-inactive row (no 404)**  | **WARN** | `PointsEngineRuleService.java:4810-4813` uses `findActiveById(...).orElseThrow(404)` before softDelete — but D-27a accepted the 404 divergence. Noting as INFO for reviewer context. | INFO | C7 |
| 5.7 | Error codes BC_NAME_TAKEN_ACTIVE, BC_UNKNOWN_SLAB, BC_NOT_FOUND, BC_INACTIVE_WRITE_FORBIDDEN, BC_NAME_TAKEN_ON_REACTIVATE present in error messages from service | PASS | Service throws string error messages at `statusCode=409/404`; facade's `BenefitCategoryBusinessException` routes by `statusCode`; error codes resolved by `resolverService.getCode()` | — | C5 |
| 5.8 | **`NotFoundException` → HTTP 200 (platform quirk OQ-45) confirmed in advice** | PASS | `TargetGroupErrorAdvice.java:74-77` — `handleNotFoundException` calls `return error(OK, e)` — this is a known platform quirk, not a new defect | — | C7 |
| 5.9 | `ConflictException` → 409 handler present | PASS | `TargetGroupErrorAdvice.java:311-325` | — | C7 |

---

### 6. Flyway Migration Safety

> Source-of-truth DDL is in `cc-stack-crm`; this project uses DDL files not Flyway scripts per platform convention.

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 6.1 | **Production DDL uses `CREATE TABLE` without `IF NOT EXISTS`** | **FAIL** | `cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql:3` and `benefit_category_slab_mapping.sql:3` — bare `CREATE TABLE`. IT harness uses `CREATE TABLE IF NOT EXISTS` (integration-test DDL:5). If migration runs twice (re-deploy, rollback+forward) it will fail with `table already exists`. | HIGH | C7 |
| 6.2 | New columns are nullable or have defaults | PASS | `updated_on NULL`, `updated_by NULL`; `is_active DEFAULT 1`, `category_type DEFAULT 'BENEFITS'`, `auto_update_time` has default | — | C7 |
| 6.3 | No destructive DDL changes in same migration | PASS | Both files are pure `CREATE TABLE` — no `DROP`, `ALTER`, or `RENAME` | — | C7 |
| 6.4 | D-47 case-sensitive collation applied to `name` column | PASS | `benefit_categories.sql:7` — `CHARACTER SET utf8mb4 COLLATE utf8mb4_bin` on `name` column | — | C7 |
| 6.5 | No `FOREIGN KEY` constraints (platform convention G-12.2) | PASS | Both DDL files explicitly note `-- No declared FOREIGN KEYs` | — | C7 |
| 6.6 | **DDL index drift: IT harness has `idx_bc_org_program_name` + `idx_bc_org_active` that are MISSING from production DDL** | **FAIL** | IT DDL: `benefit_categories.sql:19-20` — indexes `idx_bc_org_program_name (org_id, program_id, name)` and `idx_bc_org_active (org_id, is_active)`. Production DDL (`cc-stack-crm:16-17`) only has `idx_bc_org_program` and `idx_bc_org_program_active`. The name-uniqueness query (`findByProgramAndName`, `findActiveByProgramAndName`) will be unindexed on `name` in production. See also Section 8. | HIGH | C7 |

---

### 7. Serialization & Interface Compatibility

| # | Check | Verdict | Evidence (file:line) | Severity | Confidence |
|---|-------|---------|----------------------|----------|------------|
| 7.1 | `BenefitCategoryResponse` uses `@JsonFormat(pattern="yyyy-MM-dd'T'HH:mm:ssXXX")` on Date fields | PASS | `BenefitCategoryResponse.java:29,34` — D-45 revised ISO-8601 format. Note: Q-SDET-08 UI confirmation pending. | — | C7 |
| 7.2 | `BenefitCategoryResponse.stateChanged` is `Boolean` (boxed) — Jackson serializes `null` correctly with default config | PASS | `BenefitCategoryResponse.java:43` — `private Boolean stateChanged;` — Jackson omits `null` fields by default or serializes as `null`; controller sets to `null` for non-activate paths | — | C6 |
| 7.3 | `BenefitCategory` entity and inner `BenefitCategoryPK` implement `Serializable` with explicit `serialVersionUID` | PASS | `BenefitCategory.java:18,25` — `implements Serializable`, `serialVersionUID = -185145001L` and `-185145002L` | — | C7 |
| 7.4 | `BenefitCategorySlabMapping` entity implements `Serializable` | PASS | Verified in diff (Phase 9 SDET skeleton); consistent with `Benefits.java` exemplar | — | C6 |
| 7.5 | `BenefitCategoryResponseMapper` is stateless `@Component` — no JPA proxy leakage | PASS | `BenefitCategoryResponseMapper.java:19-122` — maps field-by-field; no entity reference retained beyond mapper invocation | — | C7 |
| 7.6 | DTOs (`BenefitCategoryCreateRequest`, `UpdateRequest`, `Response`, `ListPayload`) do NOT implement `Serializable` — divergence from some existing DTOs | WARN | `TargetGroup.java:17` implements `Serializable`; benefit category DTOs do not. No current `@Cacheable` on these paths, so no runtime risk now. If these paths are ever cached, `NotSerializableException` will occur. | WARN | C6 |
| 7.7 | Lombok `@Getter @Setter` on DTOs (D-44 — not `@Data`/`@EqualsAndHashCode`) — no equals/hashCode contract conflict | PASS | `BenefitCategoryCreateRequest.java:20-21`, `BenefitCategoryUpdateRequest.java:19-20`, `BenefitCategoryResponse.java:17-18` | — | C7 |
| 7.8 | **`BenefitCategoryResponse.isActive` field named `active` (Lombok getter = `isActive()`)** — Jackson may serialize as `active` or `isActive` depending on `MapperFeature.USE_GETTERS_AS_SETTERS` and version | **FAIL** | `BenefitCategoryResponse.java:27` — field `private boolean active;` generates `isActive()` getter via Lombok. Jackson 2.x maps `isActive()` → JSON key `active`. However, Thrift DTO side uses `isActive` (field name). The mapper sets `resp.setActive(thriftDto.isIsActive())` at `BenefitCategoryResponseMapper.java:40`. The JSON output will be `"active": true/false` not `"isActive": true/false`. This is a breaking discrepancy with the API spec in `03-designer.md §B.1` which references `isActive`. If the UI or consumers expect `isActive`, they will break. | HIGH | C7 |

---

### 8. Database Index Audit

**Database type**: MySQL 5.7 / Aurora MySQL  
**Index creation pattern**: DDL files in `cc-stack-crm` repository  

#### benefit_categories table — production DDL indexes

```
idx_bc_org_program           (org_id, program_id)
idx_bc_org_program_active    (org_id, program_id, is_active)
PRIMARY KEY                  (id, org_id)
```

| # | Table | Query Method | WHERE Fields | Index Exists? | Severity | Confidence |
|---|-------|-------------|--------------|---------------|----------|------------|
| 8.1 | benefit_categories | `findByOrgIdAndId` | `org_id, id` | PARTIAL — PK(`id, org_id`) covers this (reverse order but MySQL can still use it via full-index scan) | WARN | C6 |
| 8.2 | benefit_categories | `findActiveById` | `org_id, id, is_active` | PARTIAL — same as 8.1 | WARN | C6 |
| 8.3 | benefit_categories | **`findByProgramAndName`** | **`org_id, program_id, name`** | **MISSING** — `idx_bc_org_program` covers `(org_id, program_id)` but NOT `name`. Full index scan on `name` within the program partition. This is a **hot path**: called on every CREATE and UPDATE to enforce D-60 name uniqueness. | **BLOCKER** | C7 |
| 8.4 | benefit_categories | **`findActiveByProgramAndName`** | **`org_id, program_id, name, is_active`** | **MISSING** — same gap as 8.3 | **BLOCKER** | C7 |
| 8.5 | benefit_categories | `findByProgramAndNameExceptId` | `org_id, program_id, name, id` | **MISSING** — covered by 8.3 recommendation | BLOCKER | C7 |
| 8.6 | benefit_categories | `findActiveByProgramAndNameExceptId` | `org_id, program_id, name, is_active, id` | **MISSING** — covered by 8.3 recommendation | BLOCKER | C7 |
| 8.7 | benefit_categories | `findPage` (list) | `org_id, program_id, is_active` | PASS — `idx_bc_org_program_active(org_id, program_id, is_active)` covers | — | C7 |
| 8.8 | benefit_categories | `softDeleteIfActive` (@Modifying) | `org_id, id, is_active` | PARTIAL — PK covers `(id, org_id)` | WARN | C6 |
| 8.9 | benefit_categories | `activateIfInactive` (@Modifying) | `org_id, id, is_active` | PARTIAL — same | WARN | C6 |

#### benefit_category_slab_mapping table — production DDL indexes

```
idx_bcsm_org_cat_active      (org_id, benefit_category_id, is_active)
idx_bcsm_org_slab_active     (org_id, slab_id, is_active)
PRIMARY KEY                  (id, org_id)
```

| # | Table | Query Method | WHERE Fields | Index Exists? | Severity | Confidence |
|---|-------|-------------|--------------|---------------|----------|------------|
| 8.10 | benefit_category_slab_mapping | `findActiveSlabIdsByCategoryId` | `org_id, benefit_category_id, is_active` | PASS — `idx_bcsm_org_cat_active` covers | — | C7 |
| 8.11 | benefit_category_slab_mapping | `findActiveSlabIdsForCategories` | `org_id, benefit_category_id IN :ids, is_active` | PASS — `idx_bcsm_org_cat_active` covers | — | C7 |
| 8.12 | benefit_category_slab_mapping | `findActiveByCategoryId` | `org_id, benefit_category_id, is_active` | PASS — same index | — | C7 |
| 8.13 | benefit_category_slab_mapping | `bulkSoftDeleteByCategory` (@Modifying) | `org_id, benefit_category_id, is_active` | PASS — `idx_bcsm_org_cat_active` | — | C7 |
| 8.14 | benefit_category_slab_mapping | `bulkSoftDeleteByCategoryAndSlabs` (@Modifying) | `org_id, benefit_category_id, slab_id IN :ids, is_active` | PASS — `idx_bcsm_org_cat_active` leading prefix covers | — | C6 |

**DDL Drift (production vs IT harness) — benefit_categories:**

| Index | Production DDL | IT DDL | Gap |
|-------|---------------|--------|-----|
| `idx_bc_org_program` | YES | YES | none |
| `idx_bc_org_program_active` | YES | NO | IT missing — test may not exercise production index path |
| `idx_bc_org_program_name` | **NO** | YES | **Production missing — BLOCKER** |
| `idx_bc_org_active` | **NO** | YES | Production missing — WARN |

**Recommended fix for production DDL (`cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql`):**

```sql
KEY `idx_bc_org_program_name` (`org_id`, `program_id`, `name`),
```
This covers `findByProgramAndName`, `findActiveByProgramAndName`, `findByProgramAndNameExceptId`, `findActiveByProgramAndNameExceptId` (all D-60 hot-path queries). The `name` column uses `utf8mb4_bin` so index lookups will be binary-exact (consistent with D-47 case sensitivity).

---

## Blockers (must fix before Phase 11)

| # | ID | Finding | File:Line | Fix |
|---|----|---------|-----------|-----|
| B1 | 8.3-8.6 | **Missing `idx_bc_org_program_name` index on `benefit_categories` production DDL** — `findByProgramAndName` / `findByProgramAndNameExceptId` (D-60 name uniqueness, hot path on every CREATE/UPDATE/ACTIVATE) will table-scan the `name` column on a potentially large partition. | `cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql:16` | Add `KEY idx_bc_org_program_name (org_id, program_id, name)` |
| B2 | 6.1 | **`CREATE TABLE` without `IF NOT EXISTS` in production DDL** — re-deploying the migration will error on `table already exists`. | `cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql:3`, `benefit_category_slab_mapping.sql:3` | Change to `CREATE TABLE IF NOT EXISTS` |
| B3 | 7.8 | **`BenefitCategoryResponse.active` field serializes as JSON key `"active"` not `"isActive"`** — breaks API contract (designer §B.1, `03-designer.md` uses `isActive`) and any UI or consumer that has already integrated from the API handoff doc. | `BenefitCategoryResponse.java:27` | Either rename field to `isActive` (Lombok generates `isIsActive()` — awkward) **or** add `@JsonProperty("isActive")` on the `active` field. Preferred: rename the Java field to `isActive` and use hand-written getter `isIsActive()` per the `BenefitCategory` entity exemplar (line 89) **or** use `@JsonProperty("isActive") private boolean active;`. |

---

## Warnings (should fix)

| # | ID | Finding | File:Line | Severity |
|---|----|---------|-----------|----------|
| W1 | 1.3 / 4.6 | `saveAndFlush` in slab loop on CREATE (`4534-4545`) and UPDATE (`4625-4637`) paths — one DB flush per slab. Safe at D-26 scale (≤10 slabs) but not batch-optimized. Should use `saveAll(mappings)` or mark entities and flush once. | `PointsEngineRuleService.java:4534` | WARN |
| W2 | 3.1 | No cache eviction for `BenefitCategory` writes. If downstream services ever cache program/category structures, writes will produce stale reads. Recommend adding a comment/TODO near the write methods pointing to the eviction pattern used by sibling operations. | `PointsEngineRuleService.java:4466` | WARN |
| W3 | 7.6 | `BenefitCategoryCreateRequest`, `UpdateRequest`, `Response`, `ListPayload` do not implement `Serializable`. No runtime risk today (no `@Cacheable` on these paths) but diverges from `TargetGroup` DTO convention. | `BenefitCategoryCreateRequest.java`, `BenefitCategoryResponse.java` | WARN |
| W4 | 6.6 | IT DDL has `idx_bc_org_active (org_id, is_active)` missing from production DDL. The `findPage` query with `isActive` filter but no `programId` would benefit from this. | `cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql` | WARN |
| W5 | HTTP verb | Designer spec (`03-designer.md §B.5/B.6`) specifies `@PatchMapping` for activate/deactivate; implementation uses `@PostMapping`. This is not strictly wrong (both are idempotent-capable) but diverges from the contract doc; UI team may have spec'd `PATCH`. | `BenefitCategoriesV3Controller.java:104,122` | WARN |
| W6 | UpdateRequest.name | `BenefitCategoryUpdateRequest.name` has `@Size(max=255)` but NO `@NotBlank`. A request with `name: ""` passes validation and reaches the service. Service rejects it at `4583-4587` (`trim().isEmpty()` check with 400), so functional correctness is preserved — but Bean Validation is the idiomatic guard and there's no Bean Validation error code for this. | `BenefitCategoryUpdateRequest.java:23` | WARN |

---

## Accepted Deviations (not flagged as FAIL)

| Decision | Area | Note |
|----------|------|------|
| D-33 — no `@Version` | Concurrency | Accepted LWW; ADR-001 documents revisit triggers. |
| D-38 — app-level name uniqueness, no DB UNIQUE constraint | Uniqueness race | Accepted at D-26 scale; ADR-012. |
| D-27a — UPDATE on inactive row returns 404 (not 409) | Error mapping | Accepted per M4 Decision 2b; `BT-032` annotated with javadoc pointer. |
| M5 runtime IT verification deferred | Test coverage | User-directed; 10 Testcontainers ITs committed; runtime verification pending local run. |
| OQ-45 platform quirk — `NotFoundException` → HTTP 200 | Error boundary | Pre-existing platform behaviour, not introduced by this feature. |

---

## Assumptions Made

| # | Assumption | Confidence |
|---|-----------|-----------|
| A1 | `@DataSourceSpecification` is not required on entity classes (only service classes) — confirmed by `Benefits.java` exemplar having no such annotation, consistent with `BenefitCategory.java` and `BenefitCategorySlabMapping.java` | C7 |
| A2 | Production DDL files in `cc-stack-crm` are the authoritative Flyway/DDL migration source; the project does not use Flyway versioned scripts for new tables at this stage (no `V*.sql` pattern observed) | C6 |
| A3 | Jackson is configured with default serialization for the `intouch-api-v3` service; no global `@JsonProperty("active")` override exists that would remap the field name automatically | C5 |
| A4 | D-26 scale guarantee (≤10 slabs per category) holds for foreseeable production use cases, making the `saveAndFlush` loop a tolerable trade-off | C5 |
| A5 | The `BenefitCategoryFilter.activeOnly` field in Thrift correctly maps to the `isActive` parameter in `listBenefitCategories` (verified at `PointsEngineRuleService.java:4699`) | C7 |

---

## Questions for User

| # | Question | Risk if unanswered | Confidence |
|---|---------|-------------------|-----------|
| Q1 | **B3 — `active` vs `isActive` JSON field name**: Has the API handoff doc or any UI contract committed to the key `"isActive"` or `"active"`? This determines whether B3 is a breaking change or acceptable naming. | UI integration break | C4 on current impact |
| Q2 | **B1 — Index addition**: Should `idx_bc_org_program_name` be added to the production DDL in this ticket (blocking Phase 11) or tracked as a follow-up P1? Given it is a hot-path query on every CREATE/UPDATE/ACTIVATE, recommendation is to fix before merge. | Production query performance | C7 on necessity |
| Q3 | **W5 — HTTP verb**: Did the API handoff doc spec `PATCH` or `POST` for activate/deactivate? If UI has already spec'd `PATCH`, changing controller mapping is a one-line fix. | Potential client 405 | C4 |
| Q4 | **Q-SDET-08 (inherited)** — Has the UI team confirmed `yyyy-MM-dd'T'HH:mm:ssXXX` as the date format (D-45 revised)? | Date parsing discrepancy | C4 |

---

## Recommendation

**NOT READY** for Phase 11 (Reviewer) as-is due to 3 blockers.

Route back to Phase 10 (Developer) for:
1. **B1** — Add `idx_bc_org_program_name` to `cc-stack-crm/schema/dbmaster/warehouse/benefit_categories.sql`
2. **B2** — Add `IF NOT EXISTS` to both production DDL `CREATE TABLE` statements
3. **B3** — Fix `BenefitCategoryResponse.active` JSON field name to `isActive` via `@JsonProperty("isActive")`

Once B1–B3 are resolved, re-run Phase 10b (or accept residual risk on W1–W6 with user sign-off). After fix, proceed to Phase 10c (Compliance) → Phase 11 (Reviewer).
