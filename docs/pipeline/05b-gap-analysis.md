# Compliance Analysis -- Tier CRUD APIs

> Feature: tier-crud
> Ticket: test_branch_v3
> Phase: Analyst --compliance (Phase 9c)
> Date: 2026-04-06
> Confidence scale: C1 (speculative) -- C7 (verified from source)

---

## Compliance Scorecard

| # | Architectural Decision / Key Decision | Code Compliance | Severity | Evidence |
|---|--------------------------------------|-----------------|----------|----------|
| 1 | ADR-1: MongoDB-First Architecture | COMPLIANT | -- | TierDocument stored in MongoDB, Thrift sync on APPROVE only (TierFacade.java:362-374) |
| 2 | ADR-2: Separate TierController | COMPLIANT | -- | TierController.java is standalone, no modifications to RequestManagementController |
| 3 | ADR-3: Soft Delete with is_active | COMPLIANT | -- | ProgramSlab.java:96-105, PeProgramSlabDao all 3 queries updated |
| 4 | ADR-4: TierStatus Enum | EVOLVED (COMPLIANT) | LOW | LLD specifies 4 values; implementation adds SNAPSHOT (5th). Session memory line 124 documents this decision. |
| 5 | ADR-5: EMF Thrift Boundary | COMPLIANT | -- | TierFacade only calls PointsEngineRulesThriftService, never internal EMF methods |
| 6 | ADR-6: Member Count via Thrift | COMPLIANT | -- | getMemberCountPerSlab Thrift method, PeCustomerEnrollmentDao.countMembersPerSlab |
| 7 | KD: PartnerProgramTierSyncConfiguration check on delete | **VIOLATED** | **HIGH** | TierValidator.validateDelete has NO PartnerProgramTierSyncConfiguration check. Session memory line 68 and HLD Section 4.1 DELETE require it. |
| 8 | KD: R-6 Rollback on Thrift failure (APPROVE) | COMPLIANT | -- | TierFacade.java:392-397 reverts to PENDING_APPROVAL on catch |
| 9 | KD: R-8 Idempotency guard on APPROVE | COMPLIANT | -- | TierFacade.java:342-345 checks slabId != null && status == ACTIVE |
| 10 | KD: @Lockable on create/update/status change | COMPLIANT | -- | @Lockable on createTier (line 47), updateTier (line 146), changeTierStatus (line 298), deleteTier (line 242) |
| 11 | KD: Copy-on-write for PUT on ACTIVE | COMPLIANT | -- | TierFacade.java:162-171 checks for existing DRAFT, creates new if absent |
| 12 | KD: KPI type immutability per program | COMPLIANT | -- | TierValidator.validateKpiTypeConsistency called in both create and update paths |
| 13 | KD: Cache eviction in deactivateSlab | COMPLIANT | -- | PointsEngineRuleConfigThriftImpl.java:4191 calls cacheEvictHelper.evictProgramIdCache |
| 14 | KD: Strategy CSV/JSON update on soft-delete | **VIOLATED** | **HIGH** | deactivateSlab (ThriftImpl:4176-4201) only sets is_active=0 and evicts cache. Does NOT update SLAB_UPGRADE threshold CSV or SLAB_DOWNGRADE JSON. LLD Section 4.4 says "updates SLAB_UPGRADE threshold CSV and SLAB_DOWNGRADE config JSON". Session memory line 141 flags this as a constraint. |
| 15 | KD: Soft-delete via is_active, NOT rewriting strategy CSVs | **CONFLICT** | **MEDIUM** | Session memory contains contradictory decisions: line 108 says "strategy CSV with stale slab entries is harmless -- evaluation skips soft-deleted slabs" (R-1/R-2 RESOLVED). But line 141 says "deactivateSlab must update SLAB_UPGRADE threshold CSV AND SLAB_DOWNGRADE JSON". LLD sides with updating. Implementation does NOT update. See QUESTIONS FOR USER. |
| 16 | KD: APPROVE two-phase commit / WAL pattern | NOT IMPLEMENTED | **MEDIUM** | Session memory line 123 specifies WAL pattern for APPROVE. Implementation uses simple try-catch rollback (TierFacade:362-398), no WAL. The simpler pattern may be acceptable but does not match the documented decision. |
| 17 | Interface: deleteTier signature mismatch | MISMATCH | **MEDIUM** | LLD: `deleteTier(Long orgId, String tierId)`. Implementation: `deleteTier(Long orgId, Integer userId, String tierId)`. Added userId param for audit trail. Sensible addition but deviates from contract. |
| 18 | Interface: TierRequest has extra field programId | MISMATCH | **MEDIUM** | LLD TierRequest (Section 3.8) has no programId field. Implementation adds `@NotNull Integer programId`. HLD API contract (Section 4.1 POST) also has no programId in request body -- it would come from context. Controller passes request.getProgramId() to facade. |
| 19 | G-01: Timestamp compliance | COMPLIANT | -- | TierDocument and TierResponse use Instant. ProgramSlab uses Date (legacy, documented exception). |
| 20 | G-07: Multi-tenancy | COMPLIANT | -- | orgId present in every repository query, every Thrift call, every controller extraction from token |
| 21 | G-02: Null safety | COMPLIANT | -- | Optional for single returns, empty list for collections, null checks throughout |

---

## Per-ADR Compliance

### ADR-1: MongoDB-First Architecture
**Status**: COMPLIANT (C7)

Evidence:
- TierDocument.java:30 `@Document(collection = "tiers")` -- MongoDB storage confirmed
- TierFacade.createTier stores to MongoDB with status=DRAFT (line 67)
- TierFacade.approveTier (line 339) calls Thrift createOrUpdateSlab only on APPROVE
- MySQL only written to via Thrift during APPROVE and STOP transitions

### ADR-2: Separate TierController
**Status**: COMPLIANT (C7)

Evidence:
- TierController.java at `resources/TierController.java` -- standalone controller
- No modifications found to RequestManagementController (grep confirmed)
- POST /v3/tiers/{tierId}/status endpoint handles all status changes within TierController

### ADR-3: Soft Delete with is_active Column
**Status**: COMPLIANT (C7)

Evidence:
- ProgramSlab.java:96-97 `@Column(name = "is_active", nullable = false) private boolean isActive = true`
- PeProgramSlabDao.java: all 3 queries (findByProgram, findByProgramSlabNumber, findNumberOfSlabs) have `AND s.isActive = true`
- New findActiveById method added (line 43)

### ADR-4: New TierStatus Enum
**Status**: EVOLVED (C6)

LLD specifies 4 values: DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED.
Implementation has 5: adds SNAPSHOT.

Session memory line 124 documents this evolution: "TierStatus enum updated: DRAFT -> PENDING_APPROVAL -> ACTIVE -> STOPPED, plus SNAPSHOT for superseded ACTIVE versions."

This is a documented, intentional addition for the copy-on-write versioning flow. The APPROVE flow marks the old ACTIVE as SNAPSHOT (TierFacade.java:378-385). This is consistent with the session memory decision but deviates from the LLD spec.

### ADR-5: EMF Thrift Boundary
**Status**: COMPLIANT (C7)

Evidence:
- TierFacade only imports PointsEngineRulesThriftService, never any internal EMF service class
- All MySQL writes go through Thrift: createOrUpdateSlab (approve), deactivateSlab (stop/delete)
- No direct references to BasicProgramCreator or PointsEngineRuleService internals

### ADR-6: Member Count via Cross-Service Query
**Status**: COMPLIANT (C7)

Evidence:
- PeCustomerEnrollmentDao.countMembersPerSlab (lines 69-76) -- batch query with IN clause
- PointsEngineRuleConfigThriftImpl.getMemberCountPerSlab (lines 4212-4246) -- delegates to DAO
- PointsEngineRulesThriftService.getMemberCountPerSlab (lines 474-494) -- Thrift client wrapper
- TierFacade.fetchMemberCountMap (lines 427-445) -- batch call in listTiers

---

## Per-GUARDRAIL Compliance

| Guardrail | Status | Evidence |
|-----------|--------|----------|
| G-01 Timezone | COMPLIANT | TierDocument uses `Instant` (line 106-107). ProgramSlab uses `Date` (legacy, documented). Thrift uses `Instant.now().toEpochMilli()`. |
| G-02 Null Safety | COMPLIANT | Optional for findByTierIdAndOrgId (TierRepository:14-15). Empty list returns (TierFacade:124). Null checks on memberCount (TierFacade:98-101). |
| G-03 Security | COMPLIANT | All endpoints use AbstractBaseAuthenticationToken. orgId extracted from token, never request params. @Valid on request bodies. |
| G-04 Performance | COMPLIANT | Batch Thrift call for member counts (G-04.1). Small tier lists (<10) justified no pagination (G-04.2). |
| G-05 Data Integrity | PARTIAL | deactivateSlab has @Transactional (ThriftImpl:4171). But APPROVE flow has no true transaction -- relies on try-catch rollback pattern. Acceptable for MongoDB (no distributed tx support). |
| G-06 API Design | COMPLIANT | ResponseWrapper on all endpoints. Structured error responses. Correct HTTP status codes (201 for create, 400 for validation, 404 for not found). |
| G-07 Multi-Tenancy | COMPLIANT | orgId in every MongoDB query. orgId in every Thrift call. orgId in every DAO JPQL query. Compound indexes include orgId. |
| G-08 Observability | COMPLIANT | SLF4J logger in TierController and TierFacade. Structured log messages with orgId, tierId. @MDCData on Thrift impl methods. |
| G-09 Backward Compat | COMPLIANT | is_active column DEFAULT 1. New Thrift methods are additive only. No existing struct modified. |
| G-10 Concurrency | COMPLIANT | @Lockable annotations on all mutating operations. Version field incremented on every save. |
| G-12 AI-Specific | COMPLIANT | Follows existing patterns (UnifiedPromotion). No new dependencies introduced. |

---

## Interface Contract Matches

### 3.1 TierStatus enum
**Match**: EVOLVED -- LLD has 4 values, implementation has 5 (SNAPSHOT added). Documented in session memory.

### 3.2 TierAction enum
**Match**: EXACT -- 4 values, fromString method with InvalidInputException. (C7)

### 3.3 EligibilityConfig
**Match**: EXACT -- all fields and annotations match LLD. (C7)

### 3.4 ValidityConfig
**Match**: EXACT -- all fields and annotations match. (C7)

### 3.5 RenewalConfig
**Match**: EXACT -- fields and RenewalCondition nested class match. (C7)

### 3.6 DowngradeConfig
**Match**: EXACT -- all fields including @Builder.Default booleans match. (C7)

### 3.7 UpgradeBonusConfig
**Match**: EXACT (C7)

### 3.8 TierRequest
**Match**: MISMATCH -- Implementation adds `@NotNull Integer programId` field not in LLD. See Finding #F-03.

### 3.9 TierStatusRequest
**Match**: EXACT (C7)

### 3.10 TierResponse
**Match**: EXACT -- all fields present including SNAPSHOT in TierStatus. (C7)

### 3.11 TierDocument
**Match**: EXACT -- implementation adds CompoundIndexes (not in LLD) which is a positive addition. All fields, annotations, and types match. (C7)

### 3.12 TierRepository
**Match**: EVOLVED -- findActiveTiersByOrgIdAndProgramId query adds SNAPSHOT exclusion (`$nin: ['STOPPED', 'SNAPSHOT']`) vs LLD which only excludes STOPPED. Consistent with SNAPSHOT addition. findByOrgIdAndProgramIdAndSerialNumber also adds SNAPSHOT exclusion. (C6)

### 3.13 TierValidator
**Match**: COMPLIANT -- all designed methods implemented. Additional private method `validateSerialNumberUnique` added (good addition, not in LLD). (C6)

### 3.14 TierFacade
**Match**: PARTIAL MISMATCH
- `deleteTier` signature adds `Integer userId` parameter (LLD has 2 params, implementation has 3)
- `createTier` receives programId from request instead of separate param (consistent with TierRequest having programId)
- APPROVE flow matches: idempotency check, SlabInfo build, Thrift call, rollback on failure
- STOP action in changeTierStatus delegates to deleteTier (reasonable)

### 3.15 TierController
**Match**: EXACT -- all 6 endpoints match LLD signatures: GET list, GET by id, POST create, PUT update, DELETE soft-delete, POST status change. HTTP methods, paths, and return types all match. (C7)

### 3.16 EmfMongoConfig
**Match**: EXACT -- TierRepository.class added to includeFilters. Import added. (C7)

### 3.17 PointsEngineRulesThriftService (intouch-api-v3)
**Match**: EXACT -- all 3 methods (createOrUpdateSlab, deactivateSlab, getMemberCountPerSlab) match LLD signatures. (C7)

### 4.1 ProgramSlab entity
**Match**: EXACT -- isActive field with @Basic @Column, getter/setter, default true. (C7)

### 4.2 PeProgramSlabDao
**Match**: EXACT -- all 3 queries updated with `AND s.isActive = true`. findActiveById added. (C7)

### 4.3 PeCustomerEnrollmentDao
**Match**: EXACT -- countMembersPerSlab with @QueryHints readOnly, @Param, batch IN clause. (C7)

### 4.4 PointsEngineRuleConfigThriftImpl
**Match**: PARTIAL MISMATCH
- deactivateSlab: signature EXACT, @Transactional PRESENT (matches LLD R-10). But does NOT update strategy CSV/JSON as LLD requires.
- getMemberCountPerSlab: EXACT match. Delegates to DAO batch query.

---

## Findings

| # | Finding | Severity | File:Line | Action |
|---|---------|----------|-----------|--------|
| F-01 | **PartnerProgramTierSyncConfiguration check missing from delete validation.** HLD Section 4.1 DELETE explicitly lists "Cannot delete if referenced in PartnerProgramTierSyncConfiguration" as a validation. Session memory line 68 confirms this. TierValidator.validateDelete does not check this. | **HIGH** | TierValidator.java:53-84 | Add PartnerProgramTierSyncConfiguration reference check. Requires querying partner sync config (may need additional Thrift method or repository). |
| F-02 | **deactivateSlab does NOT update SLAB_UPGRADE threshold CSV or SLAB_DOWNGRADE JSON.** LLD Section 4.4 Javadoc states the method "updates SLAB_UPGRADE threshold CSV and SLAB_DOWNGRADE config JSON". Implementation only sets is_active=0 and evicts cache. Session memory has contradictory decisions (line 108 vs line 141). | **HIGH** | PointsEngineRuleConfigThriftImpl.java:4176-4201 | Resolve session memory contradiction. If strategy updates are needed, implement CSV rebuild and JSON cleanup. If not (per R-1/R-2 resolution), update LLD to match. |
| F-03 | **TierRequest adds undocumented `programId` field.** LLD Section 3.8 TierRequest does not include programId. HLD API contract POST /v3/tiers body does not include programId. Implementation requires it with @NotNull. This changes the API contract. | **MEDIUM** | TierRequest.java:22-23 | Decide: should programId come from request body (current) or from a query param / path segment? Update HLD and LLD to match. |
| F-04 | **deleteTier signature adds userId parameter not in LLD.** LLD: `deleteTier(Long orgId, String tierId)`. Implementation: `deleteTier(Long orgId, Integer userId, String tierId)`. Added for audit trail (setLastModifiedBy). Reasonable addition but undocumented. | **MEDIUM** | TierFacade.java:243 | Update LLD to reflect the userId parameter. |
| F-05 | **APPROVE WAL pattern not implemented.** Session memory line 123 documents "APPROVE two-phase commit: use write-ahead log (WAL) pattern." Implementation uses simpler try-catch rollback. The simpler approach may be acceptable but contradicts the documented decision. | **MEDIUM** | TierFacade.java:339-398 | Evaluate whether the simple rollback is sufficient or if WAL is needed for production reliability. Update session memory if simple rollback is the accepted approach. |
| F-06 | **STOP action in changeTierStatus reuses deleteTier, returns stale TierResponse.** When action=STOP, changeTierStatus calls `deleteTier(orgId, userId, tierId)` then yields `toResponse(tier, null)`. But `tier` is the object BEFORE deleteTier modified it (status still ACTIVE in the local variable). The `tier` object is not refreshed after deleteTier updates it in the database. | **HIGH** | TierFacade.java:314-317 | After deleteTier, reload the tier from MongoDB or return the updated status. Currently returns stale ACTIVE status instead of STOPPED. |
| F-07 | **TierStatus SNAPSHOT added without LLD update.** LLD enum spec has 4 values. Implementation has 5. Session memory documents the addition but LLD was not updated. | **LOW** | TierStatus.java:8 | Update LLD Section 3.1 to include SNAPSHOT. |
| F-08 | **MongoDB compound indexes added beyond LLD spec.** TierDocument has @CompoundIndexes with 3 indexes not specified in LLD. These are positive additions for query performance but undocumented. | **LOW** | TierDocument.java:31-35 | Document in LLD or HLD data model section. |
| F-09 | **listTiers SNAPSHOT filtering inconsistency.** When includeInactive=true, listTiers filters out SNAPSHOT from the result (line 118). But includeInactive=true semantically should include all statuses. SNAPSHOT exclusion is a separate concern from active/inactive. | **LOW** | TierFacade.java:116-118 | Consider whether SNAPSHOT should be visible when includeInactive=true, or add a separate parameter. |
| F-10 | **@Transactional on deactivateSlab uses rollbackFor=Exception.class.** The LLD specifies `@Transactional("warehouse")` without rollbackFor. Implementation uses `@Transactional(value = "warehouse", rollbackFor = Exception.class)`. This is MORE protective (better), not a violation, but differs from spec. | **LOW** | PointsEngineRuleConfigThriftImpl.java:4171 | No action needed -- improvement over spec. |

---

## Suggested ArchUnit Rules

For CRITICAL and HIGH findings:

```java
// F-01: Ensure delete validation checks partner sync
@ArchTest
static final ArchRule deleteValidationMustCheckPartnerSync =
    methods().that().areDeclaredIn(TierValidator.class).and().haveName("validateDelete")
        .should().callMethod(/* PartnerProgramTierSyncConfiguration lookup */);

// F-02: Ensure deactivateSlab updates strategies (if decided)
@ArchTest
static final ArchRule deactivateSlabMustUpdateStrategies =
    methods().that().haveName("deactivateSlab")
        .and().areDeclaredIn(PointsEngineRuleConfigThriftImpl.class)
        .should().callMethodWhere(target().name().matches(".*[Ss]trateg.*"));

// F-06: Ensure status change returns fresh data
// (This is better caught by an integration test than ArchUnit)
```

---

## QUESTIONS FOR USER

1. **Strategy CSV/JSON update on soft-delete (F-02, C3):** Session memory contains contradictory decisions. Line 108 (R-1/R-2 RESOLVED) says "strategy CSV with stale slab entries is harmless -- evaluation skips soft-deleted slabs. No need to update strategy JSON on soft-delete." But line 141 (Constraint) says "deactivateSlab must update SLAB_UPGRADE threshold CSV AND SLAB_DOWNGRADE JSON -- cannot just set is_active=0 in isolation." The LLD sides with updating. The implementation does NOT update. **Which decision should prevail?** If the evaluation engine truly filters by is_active=1 at the DAO level, then stale CSV entries are indeed harmless and the simpler approach is correct.

2. **programId in TierRequest (F-03, C4):** The LLD does not include programId in TierRequest. The implementation makes it required. Where should programId come from? Options: (a) request body (current), (b) query parameter on POST endpoint, (c) derived from auth context. The HLD API contract does not specify. This affects the API contract surface.

3. **PartnerProgramTierSyncConfiguration check (F-01, C3):** The validation is documented as required in HLD and session memory, but is missing from the code. To implement it, we need access to the partner sync config data. Is this data accessible from intouch-api-v3 (via a repository or Thrift call), or does it require a new Thrift method in emf-parent?

4. **WAL pattern for APPROVE (F-05, C3):** Session memory line 123 specifies a WAL pattern. The implementation uses simple try-catch rollback. Given that MongoDB does not support distributed transactions with MySQL, is the simpler pattern acceptable for production? The risk is: if the Thrift call succeeds but the MongoDB save fails, the MySQL slab exists but MongoDB still says PENDING_APPROVAL. The current implementation does NOT handle this reverse failure case.

---

## ASSUMPTIONS MADE

- **A-01 (C6):** The SNAPSHOT status addition (not in LLD) was an intentional evolution based on session memory line 124 and the copy-on-write versioning requirement. Evidence: session memory explicitly documents this, and the implementation correctly uses it in the approve flow.

- **A-02 (C5):** The @CompoundIndexes on TierDocument were added by the developer as a performance improvement. This is a positive deviation from the LLD. Evidence: the indexes match the query patterns defined in TierRepository.

- **A-03 (C6):** The `userId` parameter added to `deleteTier` is needed for setting `lastModifiedBy` on the stopped tier document. The LLD omitted it but the implementation correctly uses it for audit trail. Evidence: TierFacade.java:284 sets `tier.setLastModifiedBy(userId)`.

- **A-04 (C5):** The `programId` in TierRequest was added because the controller needs to pass it to the facade without extracting it from a separate parameter. The alternative (query param) would also work but this approach keeps the request self-contained.

---

## Summary

**Overall compliance: HIGH with 3 actionable findings.**

The implementation faithfully follows the HLD and LLD for the core architecture: MongoDB-first pattern, separate TierController, Thrift boundary, soft-delete, status lifecycle, @Lockable concurrency, and all guardrails. The code quality is consistent with the UnifiedPromotion reference implementation.

**3 HIGH-severity findings require action before production:**
1. F-01: Missing PartnerProgramTierSyncConfiguration validation on delete
2. F-02: Strategy CSV/JSON not updated in deactivateSlab (pending contradiction resolution)
3. F-06: STOP action returns stale TierResponse (bug)

**3 MEDIUM-severity findings need LLD/decision alignment:**
4. F-03: Undocumented programId in TierRequest
5. F-04: deleteTier signature adds userId
6. F-05: WAL pattern not implemented (simpler rollback used)

**4 LOW-severity findings are documentation gaps or style preferences.**
