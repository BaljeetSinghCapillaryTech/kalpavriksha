# Impact Analysis — Tier CRUD APIs

> Feature: tier-crud
> Ticket: test_branch_v3
> Phase: Analyst (Phase 6a) — Impact Mode
> Date: 2026-04-06

---

## 1. Change Summary

| Category | What | Repo |
|----------|------|------|
| NEW | TierController, TierFacade, TierDocument, TierRepository, 6 DTOs, TierStatus enum, TierAction enum, TierValidator, error codes | intouch-api-v3 |
| MODIFIED | EmfMongoConfig (add TierRepository to includeFilters) | intouch-api-v3 |
| MODIFIED | ProgramSlab entity (add `isActive` field) | emf-parent |
| MODIFIED | PeProgramSlabDao (add `is_active=1` filter to 3 existing queries + new queries) | emf-parent |
| MODIFIED | PeCustomerEnrollmentDao (add `countMembersBySlab()`) | emf-parent |
| MODIFIED | PointsEngineRuleConfigThriftImpl (add `deactivateSlab()` + `getMemberCountPerSlab()`) | emf-parent |
| MODIFIED | program_slabs DDL (add `is_active` column) | cc-stack-crm |
| MODIFIED | customer_enrollment DDL (add index) | cc-stack-crm |

**Total: ~14 new files, ~6 modified files, across 3 repos.**

---

## 2. Impact Map

### 2.1 intouch-api-v3 — Severity: MEDIUM

| Module / File | Impact Type | Severity | Detail |
|---------------|------------|----------|--------|
| `EmfMongoConfig.java` | Config change | LOW | Add `TierRepository.class` to `includeFilters`. Without this, TierRepository silently uses wrong MongoDB database (primary instead of EMF). **Verified**: `includeFilters` currently lists only `UnifiedPromotionRepository.class`. |
| `com.capillary.intouchapiv3.resources` | New controller | LOW | New `TierController.java`. No changes to existing controllers. Zero impact on `UnifiedPromotionController` or `RequestManagementController`. |
| `com.capillary.intouchapiv3.tier` | New package | LOW | Self-contained feature package. No modification to existing promotion or request-management packages. |
| `PointsEngineRulesThriftService.java` | Call-site addition | MEDIUM | New Thrift method calls (`deactivateSlab`, `getMemberCountPerSlab`). Must verify these methods exist in the Thrift IDL — **the IDL is NOT in emf-parent** (it ships as a compiled jar dependency). If the IDL must be modified, this is a 4th repo. |
| `APIMigrationInterceptor` | No impact | NONE | Runs on `/**` but only redirects if a migration rule matches. No rule exists for `/v3/tiers`. **Verified**: interceptor exits safely if no matching rule found (code-analysis-intouch-api-v3 section 5.2). |
| `HttpSecurityConfig.java` | No change needed | NONE | `requestMatchers("/**").authenticated()` already covers `/v3/tiers/**`. |
| `target_loyalty.properties` | New entries | LOW | New error codes (e.g., `TARGET_LOYALTY.TIER_NOT_FOUND`). Additive only. |

### 2.2 emf-parent — Severity: HIGH

| Module / File | Impact Type | Severity | Detail |
|---------------|------------|----------|--------|
| `ProgramSlab.java` entity | Schema change | HIGH | Add `isActive` field (`@Column(name="is_active")`). Every consumer of ProgramSlab may see this new field. |
| `PeProgramSlabDao.java` | Query modification | HIGH | **3 existing JPQL queries must be updated** to add `AND s.isActive = 1` (or `true`): `findByProgram`, `findByProgramSlabNumber`, `findNumberOfSlabs`. Without this, soft-deleted slabs appear in evaluation engine results. |
| `InfoLookupService.getProgramSlabs()` | Indirect impact | HIGH | Calls `PeProgramSlabDao.findByProgram()`. If the DAO query is updated, this transparently excludes soft-deleted slabs. But **cache invalidation is critical** — `InfoLookupService` is a cache layer. After soft-delete, the cache key for `getProgramSlabs(programId)` must be evicted. Evidence: `cacheEvictHelper.evictProgramIdCache(orgId, programId)` is called in `createOrUpdateSlab` (line 1686). The new `deactivateSlab` method MUST also call this. |
| `PointsEngineRuleConfigThriftImpl.java` | New methods | MEDIUM | Add `deactivateSlab()` and `getMemberCountPerSlab()`. Existing methods untouched. |
| `PeCustomerEnrollmentDao.java` | New query | LOW | Add `countMembersBySlab()` — new method, no change to existing queries. |
| `SlabUpgradeService` / `SlabDowngradeService` / `RenewSlabInstructionImpl` | Indirect impact | MEDIUM | These read slabs from MySQL via `InfoLookupService.getProgramSlabs()` or `getProgramSlabById()`. If `is_active` filter is properly applied at the DAO layer, these services correctly skip soft-deleted slabs. But `getProgramSlabById()` uses `findById()` (generic DAO) which does NOT have a JPQL `is_active` filter — it does a PK lookup. **A soft-deleted slab can still be loaded by ID.** This matters for downgrade target resolution and partner sync. |
| `PointsProgramConfigImpl` | Indirect impact | MEDIUM | Calls `InfoLookupService.getProgramSlabs(programId)` at line 826 for tier config display. Will transparently exclude soft-deleted slabs if DAO is updated. |
| `ThresholdBasedSlabUpgradeStrategyImpl` | Indirect impact | HIGH | Reads `threshold_values` CSV from SLAB_UPGRADE strategy. The CSV contains N-1 thresholds for N slabs. **If a slab is soft-deleted, the threshold CSV still has N-1 entries but MySQL only returns N-1 slabs (one deactivated). This creates a mismatch**: the threshold array and the active slab list are out of sync. See Risk R-3. |
| `SlabDowngradeStrategyImpl` | Indirect impact | MEDIUM | Reads `TierDowngradeStrategyConfiguration` JSON which contains per-slab configs keyed by `slabNumber`. If a slab is soft-deleted, its config entry still exists in the JSON. Evaluation engine may attempt to downgrade to a soft-deleted slab. See Risk R-4. |

### 2.3 cc-stack-crm — Severity: LOW

| Module / File | Impact Type | Severity | Detail |
|---------------|------------|----------|--------|
| `schema/dbmaster/warehouse/program_slabs.sql` | DDL modification | LOW | Add `is_active TINYINT(1) NOT NULL DEFAULT 1`. Existing rows default to 1 (active). Backward-compatible. |
| `schema/dbmaster/warehouse/customer_enrollment.sql` | Index addition | LOW | Add composite index `(org_id, program_id, current_slab_id, is_active)`. Non-blocking on reads, but creation on a large table takes time. |

### 2.4 Thrift IDL Repo — Severity: HIGH (potentially a 4th repo)

| Module | Impact Type | Severity | Detail |
|--------|------------|----------|--------|
| `PointsEngineRuleService.thrift` | IDL modification | HIGH | Two new methods needed: `deactivateSlab` and `getMemberCountPerSlab`. The IDL is **not in emf-parent** (ships as a compiled jar). This is a 4th repository that must be modified, compiled, and the jar updated as a dependency. |

---

## 3. Side Effects

### 3.1 Behavioral Side Effects

| # | Side Effect | Severity | Evidence |
|---|------------|----------|----------|
| SE-1 | **Existing slab queries return fewer results after soft-delete.** `findByProgram()` currently returns ALL slabs for a program. After adding `is_active=1` filter, soft-deleted slabs disappear from list endpoints AND from the evaluation engine's slab set. | HIGH | `PeProgramSlabDao.findByProgram()` at line 26 has no `is_active` filter today. `InfoLookupService.getProgramSlabs()` at line 3144 delegates to this. |
| SE-2 | **Cache must be invalidated on soft-delete.** `InfoLookupService` caches program slabs. If `deactivateSlab` does not call `cacheEvictHelper.evictProgramIdCache()`, stale slab data persists in cache until TTL expiry or next `createOrUpdateSlab` call. | HIGH | `cacheEvictHelper.evictProgramIdCache(orgId, programId)` is called in `createOrUpdateSlab` at line 1686. No such call exists for a delete path (none exists today). |
| SE-3 | **`getProgramSlabById()` bypasses `is_active` filter.** This method uses `findById()` (generic DAO PK lookup), not a custom JPQL query. A soft-deleted slab can still be loaded by direct ID. Downstream consumers that use `getProgramSlabById()` (e.g., downgrade target resolution, slab upgrade instruction executor) may load and operate on soft-deleted slabs. | MEDIUM | `InfoLookupService.getProgramSlabById()` at line 1983: `getPeProgramSlabDao().findById(new ProgramSlabPK(id, orgId))`. |
| SE-4 | **MongoDB `tiers` collection is new.** No existing data or queries affected. Clean namespace. | NONE | — |
| SE-5 | **`serial_number` UNIQUE constraint survives soft-delete.** After soft-deleting slab with serialNumber=2, the constraint `UNIQUE(org_id, program_id, serial_number)` still holds the row. A new slab with serialNumber=2 cannot be created while the soft-deleted row exists. | MEDIUM | `program_slabs` has UNIQUE on `(org_id, program_id, serial_number)` per code-analysis-emf-parent section 1. |

### 3.2 Performance Side Effects

| # | Side Effect | Severity | Evidence |
|---|------------|----------|----------|
| PE-1 | **GET /tiers makes 2 calls: MongoDB + Thrift (for member count).** Every list request crosses a service boundary. If the program has many tiers, the member count Thrift call adds latency. | MEDIUM | HLD section 7.4 sequence diagram shows MongoDB read + Thrift RPC for member count. |
| PE-2 | **`customer_enrollment` member count query on large table.** Without the proposed index, a `GROUP BY current_slab_id` query scans many rows. With the index `(org_id, program_id, current_slab_id, is_active)`, this becomes an index-only scan. | LOW (with index) / HIGH (without) | `customer_enrollment` is a high-volume table (one row per enrolled member per program). |
| PE-3 | **Index creation on `customer_enrollment` may lock table.** MySQL InnoDB `CREATE INDEX` on a large table uses an online DDL algorithm by default (no full lock), but may still cause temporary I/O spikes. | MEDIUM | Table has one row per enrolled customer per program — could be millions of rows. |

### 3.3 Integration Side Effects

| # | Side Effect | Severity | Evidence |
|---|------------|----------|----------|
| IE-1 | **Partner program tier sync is unaffected by CRUD operations** — but soft-delete MUST validate against `PartnerProgramTierSyncConfiguration`. HLD includes this validation (section 4, DELETE endpoint). | LOW (if validation implemented) | `PartnerProgramTierSyncConfiguration.loyaltyProgramSlabId` is an FK to `program_slabs.id`. Soft-deleting a slab that has a partner sync mapping would create a dangling reference. |
| IE-2 | **No downstream service consumes tier CRUD events.** The HLD does not propose publishing events (e.g., Kafka) for tier create/update/delete. This is acceptable for Phase 1 but limits future event-driven integration. | LOW | No event publishing mentioned in HLD. |
| IE-3 | **Thrift IDL change requires coordinated deployment.** emf-parent must be deployed with the new Thrift methods BEFORE intouch-api-v3 calls them. If intouch-api-v3 deploys first, Thrift calls fail with `TApplicationException` (unknown method). | MEDIUM | Standard Thrift backward compatibility concern. New methods are additive but caller must deploy second. |

---

## 4. Security Considerations

| # | Concern | Severity | Assessment |
|---|---------|----------|------------|
| SEC-1 | **Authentication** | OK | All `/v3/**` endpoints are protected by `requestMatchers("/**").authenticated()` in `HttpSecurityConfig`. `TierController` inherits this automatically. `AbstractBaseAuthenticationToken` provides `orgId` for tenant scoping. (C7 — verified in code-analysis-intouch-api-v3 section 5.3) |
| SEC-2 | **Multi-tenant isolation (MongoDB)** | OK | `EmfMongoTenantResolver` routes to the correct shard based on `OrgContext.getOrgId()`. All MongoDB queries include `orgId` in the query predicate (see `UnifiedPromotionRepository` patterns). TierRepository must follow the same pattern. (C6) |
| SEC-3 | **Multi-tenant isolation (MySQL)** | OK | `ProgramSlab` uses composite PK `(id, orgId)` via `OrgEntityIntegerPKBase`. All DAO queries include `orgId`. New queries must also include `orgId`. (C7 — verified in `PeProgramSlabDao` JPQL) |
| SEC-4 | **Authorization (role-based)** | NEEDS ATTENTION | The HLD does not specify which roles can perform which tier operations (create, approve, delete). The existing promotion flow relies on the UI to restrict which users can approve. **No server-side role check beyond authentication is evident.** This follows the current pattern but should be flagged for future hardening. (C5 — inferred from `UnifiedPromotionController` which also lacks explicit role checks) |
| SEC-5 | **Input validation / injection** | OK IF IMPLEMENTED | Bean Validation (`@Valid`, `@NotBlank`, `@Size`, `@Pattern`) on DTOs prevents basic injection. JPQL parameterized queries prevent SQL injection. MongoDB queries via Spring Data are parameterized. The HLD specifies Bean Validation. (C6) |
| SEC-6 | **PII exposure** | LOW RISK | TierResponse contains program config (names, thresholds, descriptions). No customer PII is exposed in tier CRUD responses. `memberCount` is an aggregate — no individual member data leaks. (C6) |
| SEC-7 | **Logging of sensitive data** | OK | Tier configuration data (names, thresholds, colors) is not PII. No password/token/card data flows through tier CRUD. Standard structured logging is sufficient. (C6) |

---

## 5. Risk Register

| # | Risk | Severity | Likelihood | Impact | Mitigation | Status |
|---|------|----------|-----------|--------|------------|--------|
| R-1 | **Threshold CSV / slab list mismatch after soft-delete.** `ThresholdBasedSlabUpgradeStrategyImpl` reads `threshold_values` CSV (N-1 entries for N slabs) and correlates by index to the slab list. Soft-deleting a slab reduces the slab list by 1 but does NOT update the CSV. Array index mapping breaks — customers may be upgraded to wrong tiers. | **CRITICAL** | HIGH | HIGH | On soft-delete, the SLAB_UPGRADE strategy `property_values` must be updated to remove the corresponding threshold entry. The `deactivateSlab` Thrift method must handle this. | open |
| R-2 | **Downgrade config references soft-deleted slab.** `TierDowngradeStrategyConfiguration` JSON contains per-slab configs keyed by `slabNumber`. Soft-deleting a slab leaves its config entry in the JSON. The downgrade engine may compute a downgrade target of a non-existent slab. | **HIGH** | MEDIUM | HIGH | On soft-delete, update SLAB_DOWNGRADE strategy `property_values` to remove the slab's config entry. Alternatively, the downgrade engine should skip `is_active=0` slabs during target resolution. | open |
| R-3 | **Cache stale after soft-delete.** `InfoLookupService` caches `getProgramSlabs(programId)` results. Without explicit eviction on soft-delete, evaluation engine continues to see the deleted slab until cache TTL expires. | **HIGH** | HIGH | MEDIUM | `deactivateSlab` must call `cacheEvictHelper.evictProgramIdCache(orgId, programId)`. | open |
| R-4 | **`getProgramSlabById()` loads soft-deleted slabs.** Uses generic `findById()` PK lookup — no `is_active` filter. Downstream callers (upgrade instruction executor, downgrade action) may load and operate on soft-deleted slabs. | **MEDIUM** | LOW | HIGH | Either: (a) override `findById` in `PeProgramSlabDao` to include `is_active=1`, or (b) add a separate `findActiveById()` method and migrate callers. Option (b) is safer — does not change existing generic DAO behavior. | open |
| R-5 | **Thrift IDL in a 4th repo.** New methods `deactivateSlab` and `getMemberCountPerSlab` require IDL changes. The IDL is not in emf-parent or intouch-api-v3 — it's in a separate Thrift repo compiled to a jar. This adds deployment complexity and a dependency chain. | **HIGH** | HIGH | MEDIUM | Identify the Thrift IDL repo. Plan IDL change, jar publish, and dependency update in emf-parent before implementation. | open |
| R-6 | **MongoDB-MySQL divergence on failure.** If Thrift call fails during APPROVE (after MongoDB is updated), MongoDB says ACTIVE but MySQL has no slab row. | **HIGH** | LOW | HIGH | HLD section 9 proposes retry + rollback (revert MongoDB to PENDING_APPROVAL on Thrift failure). Must be implemented with proper error handling, not just documented. | open |
| R-7 | **`serial_number` UNIQUE constraint blocks slab reuse after soft-delete.** A soft-deleted slab retains its `serial_number` row. Creating a new slab with the same `serial_number` fails with constraint violation. | **MEDIUM** | MEDIUM | LOW | Either: (a) include `is_active` in the UNIQUE constraint (`org_id, program_id, serial_number, is_active`), or (b) accept that serial numbers are never reused (append-only ordering). Option (b) is simpler but leaves gaps in the tier hierarchy display. | open |
| R-8 | **No idempotency on APPROVE.** If the APPROVE request is retried (network timeout), and the first call succeeded (Thrift wrote to MySQL), the retry may create a duplicate slab or fail with a constraint error. | **MEDIUM** | LOW | MEDIUM | APPROVE should be idempotent: check if MySQL slab already exists for this tier before calling Thrift. | open |
| R-9 | **`customer_enrollment` index creation on production.** Large table (millions of rows). Online DDL may cause I/O spikes. | **MEDIUM** | MEDIUM | LOW | Schedule index creation during off-peak hours. Use `ALGORITHM=INPLACE` (InnoDB default for index creation). | open |
| R-10 | **No `@Transactional` on Thrift impl for slab operations.** Grep found no `@Transactional` on `PointsEngineRuleConfigThriftImpl`. If `deactivateSlab` involves multiple DAO writes (program_slabs + strategies), partial failure may leave data inconsistent. | **MEDIUM** | LOW | HIGH | Verify transaction management on the `deactivateSlab` implementation. May need `@Transactional("warehouse")` at the service layer. | open |

---

## 6. GUARDRAILS Compliance Check

### CRITICAL Guardrails

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| **G-01 Timezone** | COMPLIANT | HLD uses `DateTime` in TierResponse (createdOn, lastModifiedOn). Must use `Instant` or `ZonedDateTime` (not `java.util.Date`). The existing `ProgramSlab.createdOn` uses `java.util.Date` — new code must NOT propagate this to the API surface. Convert to ISO-8601 in the response serializer. **Action for Designer**: specify `Instant` for all new timestamp fields in DTOs and MongoDB document. |
| **G-03 Security** | COMPLIANT WITH CAVEATS | Auth is enforced globally. Bean Validation on DTOs. Parameterized queries. **Caveat**: No explicit role-based authorization for tier operations (SEC-4). Current pattern relies on UI-level role enforcement. Acceptable for Phase 1 if documented. |
| **G-07 Multi-Tenancy** | COMPLIANT | MongoDB uses `EmfMongoTenantResolver` with `OrgContext.getOrgId()`. All MongoDB queries include `orgId`. MySQL queries include `orgId` in PK and WHERE clauses. New queries MUST maintain this pattern. |
| **G-12 AI-Specific** | COMPLIANT | HLD follows existing `UnifiedPromotion` patterns exactly. No new dependencies introduced. No new frameworks. |

### HIGH Guardrails

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| **G-02 Null Safety** | NEEDS ATTENTION | `TierResponse.slabId` is nullable (null for DRAFT/PENDING). `memberCount` is nullable. These must use `Optional<Integer>` or be documented as nullable in the DTO with explicit null handling. |
| **G-04 Performance** | NEEDS ATTENTION | GET /tiers makes 2 calls (MongoDB + Thrift). Member count query needs index. See PE-1, PE-2. |
| **G-05 Data Integrity** | NEEDS ATTENTION | Two sources of truth (MongoDB + MySQL). Divergence risk on APPROVE failure (R-6). No `@Transactional` evidence on Thrift boundary (R-10). Soft-delete leaves strategy JSON stale (R-1, R-2). |
| **G-06 API Design** | COMPLIANT | Structured error responses via `ResponseWrapper`. Proper HTTP status codes. ISO-8601 dates specified. Pagination not specified for GET /tiers — **should be added if program can have many tiers** (though typically programs have < 10 tiers, so acceptable). |
| **G-09 Backward Compatibility** | COMPLIANT | `is_active` column defaults to 1 — existing rows unaffected. New DAO queries add a filter that excludes `is_active=0` rows — but since no rows have `is_active=0` before the feature launches, no behavioral change occurs. Strategy JSON changes on soft-delete are a concern (R-1, R-2) but do not affect existing tiers until a deletion actually occurs. |
| **G-10 Concurrency** | NEEDS ATTENTION | The APPROVE flow reads MongoDB, calls Thrift, then updates MongoDB. If two users simultaneously approve the same tier, race condition may create duplicate MySQL slabs. **Recommend optimistic locking** via the `version` field in MongoDB document. |
| **G-11 Testing** | NEEDS ATTENTION | HLD mentions integration tests (step 17) but does not specify: timezone tests (G-01.7), tenant isolation tests (G-07.4), concurrent access tests (G-10), idempotency tests (G-06.1). QA phase must address these. |

---

## 7. Product Requirements Verification

### Requirements Fulfilment Table

Based on `00-ba-machine.md` user stories and the product registry:

| Requirement | HLD Coverage | Status | Evidence |
|-------------|-------------|--------|----------|
| US-1: List tiers for a program | GET /v3/tiers endpoint | FULFILLED | HLD section 4.1 |
| US-2: Get single tier detail | GET /v3/tiers/{tierId} | FULFILLED | HLD section 4.1 |
| US-3: Create new tier | POST /v3/tiers → DRAFT in MongoDB | FULFILLED | HLD section 4.1, sequence diagram 7.1 |
| US-4: Update tier configuration | PUT /v3/tiers/{tierId} | FULFILLED | HLD section 4.1 |
| US-5: Soft delete tier | DELETE /v3/tiers/{tierId} with validations | FULFILLED | HLD section 4.1, sequence diagram 7.3 |
| US-6: Submit for approval | POST /v3/tiers/{tierId}/status | FULFILLED | HLD section 4.2 |
| US-7: Approve/Reject tier | POST /v3/tiers/{tierId}/status | FULFILLED | HLD section 4.2 |
| KPI type immutable per program | Validation needed | PARTIALLY FULFILLED | Not explicitly mentioned in HLD validations — must be enforced at create time |
| Threshold strictly increasing | Validation in TierFacade | FULFILLED | HLD mentions "Validate threshold ordering" |
| Base tier cannot be deleted | Validation in DELETE flow | FULFILLED | HLD section 4.1 DELETE validations |
| Member count per tier | Via Thrift to customer_enrollment | FULFILLED | HLD ADR-6, sequence diagram 7.4 |
| Field-level validation errors | Bean Validation + ResponseWrapper | FULFILLED | HLD section 4.1 POST response 400 |

### Product Boundary Check

| Check | Result |
|-------|--------|
| Does the HLD respect module boundaries from the product registry? | YES — Tier CRUD stays within Tiers module. Benefits module untouched (E2 deferred). Promotions module untouched (separate TierController, no RequestManagementController modification). |
| Does the HLD introduce domain model conflicts? | NO — `TierDocument` is a new MongoDB entity. `TierStatus` is a new enum (does not reuse `PromotionStatus`). `ProgramSlab` entity is extended but not replaced. |
| Does the HLD break documented product behavior? | **RISK** — Soft-delete may break evaluation if strategy JSON is not updated (R-1, R-2). This is not a blocker on the HLD itself but on the implementation of `deactivateSlab`. |

### Product-Level Issues

| # | Issue | Source | Impact | Direction |
|---|-------|--------|--------|-----------|
| PI-1 | KPI type immutability not explicitly validated in HLD | BA requirement: "KPI type is immutable per program — set on first tier, all subsequent must match" | If omitted, a program could end up with mixed KPI types, breaking the evaluation engine | Add validation in TierFacade.createTier(): fetch existing tiers for the program, if any exist, verify new tier's `currentValueType` matches. |
| PI-2 | Partner program tier sync not documented in APPROVE flow | Product registry: `PartnerProgramTierSyncConfiguration` maps partner slabs to loyalty slabs | If a tier is approved and then partner sync references it, the sync mapping must use the MySQL `slabId` (set on APPROVE). This is correctly handled since `slabId` is stored in MongoDB on APPROVE. | No change needed — just verify in implementation. |

---

## 8. Verified vs Assumed Impacts

### Verified (C6+)

- [x] `PeProgramSlabDao` has exactly 3 JPQL queries that must be updated for `is_active` filter (file: PeProgramSlabDao.java lines 26, 29, 32)
- [x] `InfoLookupService.getProgramSlabs()` calls `findByProgram()` — will transparently benefit from DAO filter update (file: InfoLookupService.java line 3144)
- [x] `cacheEvictHelper.evictProgramIdCache()` is called in `createOrUpdateSlab` — must also be called in `deactivateSlab` (file: PointsEngineRuleConfigThriftImpl.java line 1686)
- [x] `EmfMongoConfig.includeFilters` must include `TierRepository.class` (file: EmfMongoConfig.java)
- [x] `HttpSecurityConfig` covers `/v3/tiers/**` automatically
- [x] `APIMigrationInterceptor` has zero impact on `/v3/tiers`
- [x] `program_slabs` has no `is_active` column today
- [x] `customer_enrollment` has no member-count-per-slab query or supporting index
- [x] No `deactivateSlab` Thrift method exists today

### Assumed (C4-C5)

- [ ] **A-1 (C5):** `ThresholdBasedSlabUpgradeStrategyImpl` correlates threshold CSV entries to slab list by index position. Soft-deleting a slab without updating the CSV breaks this mapping. Evidence: code-analysis-emf-parent section 2 describes CSV as "N-1 thresholds for N slabs". Not directly verified by reading the strategy implementation line-by-line.
- [ ] **A-2 (C4):** `createOrUpdateSlab` Thrift method handles strategy updates (SLAB_UPGRADE, SLAB_DOWNGRADE) automatically for new slabs. Whether it also handles strategy updates for slab updates (e.g., threshold change) is uncertain. The code-analysis states "auto-extends strategies for new slabs" but does not confirm update behavior.
- [ ] **A-3 (C5):** The Thrift IDL repo is separate from emf-parent and intouch-api-v3. This assumption is based on the absence of `.thrift` IDL files for `PointsEngineRuleService` in both repos.
- [ ] **A-4 (C4):** No `@Transactional` annotation on `PointsEngineRuleConfigThriftImpl` for slab operations. Transaction management may be at the service layer (`PointsEngineRuleService`) instead, but this was not verified.

---

## QUESTIONS FOR USER

1. **R-1 / R-2 — Strategy JSON update on soft-delete (C3):** When a slab is soft-deleted, should the `deactivateSlab` Thrift method also update the SLAB_UPGRADE `threshold_values` CSV and the SLAB_DOWNGRADE `TierDowngradeStrategyConfiguration` JSON to remove the deleted slab's entries? Without this, the evaluation engine may malfunction. The HLD does not specify this.

2. **R-5 — Thrift IDL repo (C4):** Where is the Thrift IDL repository for `PointsEngineRuleService`? Is it accessible? New methods `deactivateSlab` and `getMemberCountPerSlab` must be added to the IDL before implementation can proceed.

3. **A-2 — Strategy updates on tier edit (C4):** When an existing tier's threshold is changed via PUT → APPROVE, does `createOrUpdateSlab` automatically update the SLAB_UPGRADE strategy `threshold_values` CSV? Or must the caller explicitly call a separate strategy update method?

4. **R-7 — Serial number reuse (C4):** After soft-deleting a slab, should the serial numbers of higher-ranked slabs be renumbered to fill the gap? The evaluation engine uses contiguous serial numbers for threshold array indexing.

5. **PI-1 — KPI type validation (C5):** Confirm that the KPI type immutability constraint (all tiers in a program must share the same `currentValueType`) should be enforced at the API level during tier creation.

## ASSUMPTIONS MADE

- **A-1 (C6):** The MongoDB `tiers` collection uses the EMF Mongo namespace (`emfMongoTemplate`), not the primary Mongo. Evidence: all EMF configuration data (UnifiedPromotions) uses EMF Mongo; tiers are an EMF concept.
- **A-2 (C6):** `EmfMongoConfig.includeFilters` is the sole mechanism to route a repository to `emfMongoTemplate`. Without explicit inclusion, Spring Boot's primary `mongoTemplate` is used. Evidence: code-analysis-intouch-api-v3 section 2.2.
- **A-3 (C6):** Authentication via `AbstractBaseAuthenticationToken` works for `TierController` without additional configuration. Evidence: all 6 existing controllers use this pattern.
- **A-4 (C5):** The `deactivateSlab` method must include cache eviction. Evidence: `createOrUpdateSlab` calls `cacheEvictHelper.evictProgramIdCache()` (line 1686), and the same cache is populated by `InfoLookupService.getProgramSlabs()` which calls `findByProgram()`.
- **A-5 (C5):** Programs typically have fewer than 10 tiers, so pagination for GET /tiers is not critical. Evidence: Capillary loyalty programs in practice have 3-7 tiers. However, no hard limit is enforced in the schema.

---

*Phase 6a complete. Impact analysis covers 3 repos + potential 4th (Thrift IDL). 10 risks identified, 2 CRITICAL (R-1 strategy mismatch, R-3 cache staleness). No architectural blockers raised — all risks are addressable at implementation time if the Designer and Developer phases account for them.*
