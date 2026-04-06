# Code Review — Tier CRUD APIs

> Feature: tier-crud
> Ticket: test_branch_v3
> Phase: Reviewer (Phase 11)
> Date: 2026-04-06
> Confidence scale: C1 (speculative) → C7 (verified from source)

---

## Section 1: Build Verification

| Check | Status | Notes |
|-------|--------|-------|
| Compilation (intouch-api-v3) | PASS | Pre-confirmed per prompt |
| Compilation (emf-parent) | PASS | Pre-confirmed per prompt |
| Unit Tests | SKIPPED | No new tests written yet — SDET plan produced (06-sdet.md) |
| Integration Tests | SKIPPED | No new tests written yet — SDET plan produced |

Build-fix cycles used: 0/3

---

## Section 2: Requirements Traceability

### 2a. Requirements Baseline (from 00-ba.md)

| ID | Requirement Summary |
|----|---------------------|
| REQ-01 | GET /tiers — list all active tiers for org's program |
| REQ-02 | GET /tiers response: name, description, color, KPI type, threshold, validity, renewal, downgrade, status, memberCount |
| REQ-03 | Tiers ordered by hierarchy (base first) |
| REQ-04 | Soft-deleted tiers excluded by default; includeInactive=true returns all |
| REQ-05 | Response uses ResponseWrapper format |
| REQ-06 | GET /tiers/{tierId} returns full config |
| REQ-07 | GET /tiers/{tierId} returns 404 for non-existent or soft-deleted tier |
| REQ-08 | POST /tiers creates tier in DRAFT status |
| REQ-09 | Required field validation: name, KPI type, threshold (>0), validity, downgrade target |
| REQ-10 | Optional fields accepted: description, color, upgrade schedule, renewal, upgrade bonus, downgrade-on-return |
| REQ-11 | Field-level errors in ResponseWrapper.errors[] per invalid field |
| REQ-12 | New tier added above highest existing tier only |
| REQ-13 | KPI type must match program's existing KPI type |
| REQ-14 | Threshold must exceed current highest tier's threshold |
| REQ-15 | Tier created in DRAFT if maker-checker enabled |
| REQ-16 | PUT /tiers/{tierId} updates tier configuration |
| REQ-17 | PUT: same field-level validation as create |
| REQ-18 | PUT: cannot change KPI type |
| REQ-19 | PUT on ACTIVE: creates new DRAFT version (copy-on-write) |
| REQ-20 | PUT returns 404 for non-existent/soft-deleted tier |
| REQ-21 | PUT on PENDING_APPROVAL rejected with error |
| REQ-22 | DELETE /tiers/{tierId} sets active=0 |
| REQ-23 | Cannot delete base tier |
| REQ-24 | Cannot delete tier that is downgrade target of another active tier |
| REQ-25 | Soft-deleted tier excluded from default GET |
| REQ-26 | DELETE returns 404 if not found or already soft-deleted |
| REQ-27 | POST /tiers/{tierId}/status SUBMIT_FOR_APPROVAL → DRAFT to PENDING_APPROVAL |
| REQ-28 | Only DRAFT tiers can be submitted |
| REQ-29 | APPROVE transitions PENDING_APPROVAL → ACTIVE |
| REQ-30 | REJECT transitions PENDING_APPROVAL → DRAFT, comment required |
| REQ-31 | Only PENDING_APPROVAL tiers can be approved/rejected |
| REQ-32 | On APPROVE: tier config becomes effective in program |
| REQ-33 | Member count per tier in GET /tiers response |
| REQ-34 | Partner program tier sync check on delete (session-memory line 68, HLD DELETE validations) |
| REQ-35 | KPI type immutability enforced at API level (session-memory PI-1) |

### 2b. Requirements Traceability Matrix

| ID | Requirement | Architect | Designer | QA | Developer | SDET | Status |
|----|-------------|-----------|----------|----|-----------|------|--------|
| REQ-01 | GET /tiers list | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-02 | Response fields incl. memberCount | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-03 | Tiers ordered by hierarchy | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-04 | includeInactive query param | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-05 | ResponseWrapper format | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-06 | GET /tiers/{tierId} | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-07 | 404 for missing/deleted tier | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-08 | POST creates DRAFT | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-09 | Required field validation | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-10 | Optional fields accepted | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-11 | Field-level errors in errors[] | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-12 | New tier above highest only | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-13 | KPI type matches program | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-14 | Threshold > current highest | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-15 | DRAFT if maker-checker enabled | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-16 | PUT updates tier | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-17 | PUT field-level validation | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-18 | Cannot change KPI type | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-19 | PUT on ACTIVE: copy-on-write DRAFT | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-20 | PUT 404 for missing/deleted | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-21 | PUT blocked on PENDING_APPROVAL | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-22 | DELETE sets active=0 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-23 | Cannot delete base tier | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-24 | Cannot delete if downgrade target | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-25 | Deleted tier excluded from GET | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-26 | DELETE 404 for missing | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-27 | SUBMIT_FOR_APPROVAL transition | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-28 | Only DRAFT can be submitted | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-29 | APPROVE transition | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-30 | REJECT with comment | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-31 | Only PENDING_APPROVAL approvable | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-32 | APPROVE makes tier effective | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-33 | Member count in GET response | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| REQ-34 | Partner sync check on delete | ✅ | ✅ | ✅ | PARTIAL | PARTIAL | **PARTIAL** |
| REQ-35 | KPI type immutability enforced | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |

### 2c. REQ-34 Partial Coverage Detail

**Requirement**: Cannot soft-delete a tier that is referenced in PartnerProgramTierSyncConfiguration (session-memory line 68, HLD DELETE validations, `05b-gap-analysis.md` F-01).

**Coverage evidence (C7):**
- `TierValidator.validateDelete` (line 53-84): NO check for partner sync config. Grep confirmed zero `partnerProgram` references in this file.
- `PointsEngineRuleConfigThriftImpl.deactivateSlab` (lines 4192-4197): check IS present — `partnerProgramTierSyncConfigurationDao.countByLoyaltyProgramSlabId(orgId, slabId)` throws a `PointsEngineRuleServiceException` if count > 0.

**Assessment**: The F-01 fix was moved from the API validation layer (`TierValidator`) to the EMF Thrift layer (`deactivateSlab`). This is architecturally acceptable — the constraint is enforced at the service boundary. However, two concerns remain:

1. **The error surfaces as a `PointsEngineRuleServiceException` thrown at the Thrift boundary**, which `TierFacade.deleteTier` (line 277) catches generically and re-wraps as `InvalidInputException("Failed to deactivate tier in backend: ...")`. This loses the specific error message "Cannot deactivate slab X — it is referenced in Y partner program tier sync configuration(s). Remove partner sync mappings first." The client receives a vague "Failed to deactivate tier in backend" instead of an actionable message. (C7 — verified from `TierFacade.java:277-279`)

2. **The pre-condition is not checked before calling Thrift** — the API will make a round-trip to EMF only to fail there. For DRAFT/PENDING tiers (slabId=null), the Thrift call is skipped entirely (line 270), meaning the partner sync check is also skipped. This is correct behaviour for MongoDB-only tiers, but could be surprising if a DRAFT has been previously ACTIVE and had its ACTIVE version checked via a different code path.

**Status**: PARTIAL — constraint is enforced at the right layer but error message propagation is lossy.

### 2d. Unresolved BRD Questions Affecting Scope

From `brdQnA.md` and session-memory open questions:

| Question | Phase | Affects Requirements | Impact on Implementation |
|----------|-------|---------------------|------------------------|
| Should `deactivateSlab` update SLAB_UPGRADE threshold CSV and SLAB_DOWNGRADE JSON? (F-02) | Analyst/Designer | REQ-22 | Contradictory decisions in session memory (line 108 vs 141). Implementation does NOT update CSVs. Resolution needed. |
| Is WAL pattern required for APPROVE two-phase commit? (F-05) | QA→User | REQ-29, REQ-32 | Implementation uses simple try-catch rollback; WAL not implemented. Simpler pattern has a gap — Thrift success + MongoDB save failure is unhandled (reverse direction). |
| Where does `programId` come from — request body or query param? (F-03) | Designer→User | REQ-08, REQ-16 | `TierRequest` adds `programId` not in LLD/HLD. API contract mismatch vs documented spec. |
| When `getMemberCountPerSlab` Thrift fails during GET /tiers: 500 or `memberCount=null`? | SDET→User | REQ-33, REQ-02 | Implementation returns `null` (degraded mode). Formally unresolved in session memory. |
| Does POST /tiers support idempotency keys (`X-Idempotency-Key`)? | SDET→User | REQ-08 | No idempotency key — uses edit lock pattern. Accepted behavior, but explicitly not resolved. |

### 2e. Requirements Traceability Summary

```
Requirements Traceability Review
   Total requirements: 35
   PASS: 34
   FAIL: 0
   PARTIAL: 1 (REQ-34 — partner sync error message propagation)

   Gaps by phase:
     Architect: 0 gaps
     Designer:  0 gaps
     QA:        0 gaps
     Developer: 1 PARTIAL (REQ-34 error message quality)

   Unresolved BRD questions affecting scope: 5 (F-02, F-03, F-05, getMemberCount degradation, idempotency key)
```

---

## Section 3: Code Review

### 3a. Session Memory Alignment

| Decision / Constraint | Verified In Code | Status |
|----------------------|-----------------|--------|
| ADR-1: MongoDB-first, Thrift sync on APPROVE | TierDocument.java:30, TierFacade.java:362-374 | COMPLIANT (C7) |
| ADR-2: Separate TierController, no RequestManagementController modification | TierController.java standalone; no grep hits on RequestManagementController | COMPLIANT (C7) |
| ADR-3: `is_active` soft delete | ProgramSlab.java:96-97, PeProgramSlabDao all 3 queries | COMPLIANT (C7) |
| ADR-4: New `TierStatus` enum (not reusing PromotionStatus) | TierStatus.java:1-9 | COMPLIANT (C7) |
| ADR-5: Thrift boundary (no direct EMF internals) | TierFacade only imports PointsEngineRulesThriftService | COMPLIANT (C7) |
| ADR-6: Member count via cross-service Thrift | getMemberCountPerSlab in Thrift + DAO | COMPLIANT (C7) |
| R-3: Cache eviction on deactivate | ThriftImpl:4204 calls evictProgramIdCache | COMPLIANT (C7) |
| R-6: Rollback on Thrift failure (APPROVE) | TierFacade.java:392-400: revert to PENDING_APPROVAL | COMPLIANT (C7) |
| R-8: Idempotency on APPROVE | TierFacade.java:342-345: slabId != null + ACTIVE check | COMPLIANT (C7) |
| R-10: @Transactional on deactivateSlab | ThriftImpl:4174 @Transactional(value = "warehouse", rollbackFor = Exception.class) | COMPLIANT (C7) |
| PI-1: KPI type immutability | TierValidator.validateKpiTypeConsistency called in create + update | COMPLIANT (C7) |
| F-06: Stale STOP response fix | TierFacade.java:316-318 reloads from MongoDB after deleteTier | COMPLIANT (C7) |
| G-01: Instant for timestamps | TierDocument:106-107, TierResponse:42-43 use Instant. ProgramSlab uses Date (legacy exception documented). | COMPLIANT (C7) |
| G-07: orgId in all queries | TierRepository every @Query includes orgId param. JPQL in DAOs include orgId. | COMPLIANT (C7) |
| Copy-on-write for PUT on ACTIVE | TierFacade.java:162-171: checks for existing DRAFT, creates new if absent | COMPLIANT (C7) |
| Version field for optimistic locking | TierDocument:59 @Builder.Default version=1. Incremented on every save. | COMPLIANT (C7) |
| SNAPSHOT for superseded ACTIVE versions | TierFacade.java:378-385: marks parent as SNAPSHOT on APPROVE | COMPLIANT (C7) |
| MongoDB compound indexes | TierDocument:31-35 @CompoundIndexes (resolved W-1 from backend-readiness) | COMPLIANT (C7) |
| @Lockable on all mutating operations | @Lockable on createTier, updateTier, deleteTier, changeTierStatus | COMPLIANT (C7) |
| TierRepository registered in EmfMongoConfig | Gap analysis 3.16: EXACT match (verified from code) | COMPLIANT (C6) |

**Deviation from session memory — tracked as non-blocker:**

- **SNAPSHOT status** (5th enum value not in ADR-4 spec): Intentional evolution. Session memory line 124 documents it. `05b-gap-analysis.md` confirms it is a documented decision. No action required.
- **WAL pattern not implemented** (session memory line 123 specifies WAL for APPROVE): Implementation uses simple try-catch rollback. This leaves a gap: if `createOrUpdateSlab` Thrift succeeds but the subsequent `tierRepository.save(tier)` fails (e.g., MongoDB transient error), the MySQL slab row exists but MongoDB still shows PENDING_APPROVAL. See BLOCKERS — this is a code-level concern, not yet confirmed as a formal blocker (F-05 is an open question per the user).

### 3b. Security Verification

| Security Consideration | Expected (from Analyst/Session Memory) | Verified in Code | Status |
|-----------------------|---------------------------------------|-----------------|--------|
| orgId extracted from auth token, never from request params | G-03: orgId from AbstractBaseAuthenticationToken | `user.getOrgId()` in every controller method. programId from request body (not orgId). | PASS (C7) |
| @Valid on all request bodies | G-03.2: Bean Validation at service boundary | `@Valid @RequestBody` in createTier, updateTier, changeTierStatus | PASS (C7) |
| No SQL concatenation | G-03.1: No string-based query construction | All DAOs use JPQL `@Query` with positional parameters. No string concat. | PASS (C7) |
| Auth enforcement on all endpoints | G-03.3: Auth checks server-side | `AbstractBaseAuthenticationToken` param in every controller method; `token.getIntouchUser()` enforces auth at Spring MVC binding level | PASS (C6) |
| Sensitive data not logged | G-03.5 / G-08.5 | Logs contain orgId, tierId, programId — no sensitive customer or tier config data logged in plaintext | PASS (C6) |
| No secrets in code | G-03.4 | No hardcoded credentials. Thrift connection via RPCService. MongoDB via existing pooled connection. | PASS (C7) |

**Note (C5):** No explicit rate limiting configured for the new tier endpoints. The existing platform-level rate limiting (if any) at the load balancer / gateway level would apply, but no per-endpoint or per-org quota check is visible in the controller. This is consistent with existing endpoints in the codebase (e.g., UnifiedPromotionController) — not a new gap introduced by this feature. Flagged as informational.

### 3c. Guardrails Compliance

#### CRITICAL Guardrails

**G-01: Timezone & Date/Time** — PASS

- `TierDocument.java:106-107`: `private Instant createdOn;` and `private Instant lastModifiedOn;` — G-01.3 compliant.
- `TierResponse.java:42-43`: `private Instant createdOn; private Instant lastModifiedOn;` — G-01.6 compliant (ISO-8601 on serialization).
- `ProgramSlab.java`: uses `java.util.Date + @Temporal` — legacy pattern, documented exception (session memory Designer additions), **not a violation**.
- `TierFacade.java:58`: `Instant now = Instant.now();` — correct.
- `PointsEngineRulesThriftService.createOrUpdateSlab`: `Instant.now().toEpochMilli()` — correct epoch millis for Thrift.
- No `new Date()`, `LocalDateTime.now()`, or `SimpleDateFormat` found in new code. G-01.3: **PASS**.

**G-03: Security** — PASS WITH ONE FLAG

- G-03.1 (no SQL concatenation): All new JPQL queries use `?1`, `?2` positional params or `@Param` named params. No string concatenation. **PASS**.
- G-03.3 (auth on every endpoint): `AbstractBaseAuthenticationToken` on all 6 controller methods. **PASS**.
- **G-03 FLAG (HIGH):** `TierController.java:68`: In the catch-all `Exception` handler for `listTiers`, the error log includes `user.getOrgId()` and `programId`. If `token.getIntouchUser()` itself throws (e.g., token parse failure), the log line `user.getOrgId()` will throw an NPE before the error can be logged. This NPE would surface as a 500 with no useful error message. The pattern is consistent with the existing codebase (UnifiedPromotionController has the same structure), so this is a pre-existing concern — flagged as non-blocking.

**G-07: Multi-Tenancy** — PASS

Every MongoDB `@Query` in `TierRepository` includes `orgId`. Every JPQL query in `PeProgramSlabDao`, `PeCustomerEnrollmentDao`, `PartnerProgramTierSyncConfigurationDao` includes `orgId` or `pk.orgId`. Every Thrift call passes `orgId.intValue()`. **PASS (C7)**.

**G-12: AI-Specific Coding Guardrails** — PASS WITH ONE FLAG

- G-12.3 (verify all imports and method calls exist): All method calls verified against actual source files at C7 evidence level. `SlabInfo.setId()`, `SlabInfo.setProgramId()` etc. verified against Thrift IDL. `cacheEvictHelper.evictProgramIdCache` verified against ThriftImpl.
- **G-12 FLAG:** `TierFacade.java:352`: `SlabInfo.setId()` — when `tier.getSlabId() == null` (new DRAFT), `slabInfo.setId()` is never called. In Thrift-generated Java, an unset `required i32` field defaults to `0`. The `createOrUpdateSlab` Thrift implementation uses `id=0` as the sentinel for "new slab" (backend-readiness.md I-2). This is implicit contract coupling and was documented as INFO in backend-readiness. No immediate breakage but fragile. Non-blocking.

#### HIGH Guardrails

| Guardrail | Status | Evidence |
|-----------|--------|---------|
| G-02: Null Safety | PASS | Optional for single returns; empty list for collections; null checks on memberCount; memberCount null OK for DRAFT. |
| G-04: Performance | PASS | Batch Thrift call for member counts (`fetchMemberCountMap` collects all slabIds, single call). Tier list bounded (<10 per program — justified pagination skip). |
| G-05: Data Integrity | PARTIAL | `deactivateSlab` has `@Transactional("warehouse")`. APPROVE flow has no distributed transaction (MongoDB + MySQL). Try-catch rollback is a best-effort pattern. MongoDB save failure after Thrift success leaves data divergent — see BLOCKERS. |
| G-06: API Design | PASS | ResponseWrapper on all endpoints. Correct HTTP codes (201 for create, 400 for validation, 404 for not found, 200 for status changes). |
| G-08: Observability | PASS | SLF4J logger in TierController and TierFacade with orgId in every log line. @MDCData(orgId) on Thrift impl methods. |
| G-09: Backward Compat | PASS | `is_active` column DEFAULT 1 (no existing rows affected). New Thrift methods additive only. No structs modified destructively. |
| G-10: Concurrency | PASS | @Lockable on all 4 mutating operations. Version field incremented on every save. |
| G-11: Testing | WARN | No new tests written yet. SDET plan exists in `06-sdet.md` with 26 test methods (11 UTs + 15 ITs). Non-blocking given the plan exists and deferred by user decision. |

### 3d. Documentation Check

| Item | Expected | Status |
|------|---------|--------|
| ADRs (6 ADRs) | Documented in 01-architect.md | PASS — all 6 ADRs present |
| LLD interface contracts | 03-designer.md | PASS — all interfaces documented |
| API contract (HLD) | 01-architect.md Section 4 | PASS — all 6 endpoints documented |
| API handoff doc | api-handoff phase (not produced) | NOT APPLICABLE — not requested in this pipeline |
| Session memory | Updated incrementally across phases | PASS — session memory is complete and current |
| SDET plan | 06-sdet.md | PASS — 26 test methods planned |

**Note:** The LLD (`03-designer.md`) has two minor mismatches with the implementation (TierRequest.programId field, deleteTier userId param) that were already identified in `05b-gap-analysis.md` as F-03 and F-04. These are documentation alignment gaps rather than code bugs. The LLD should be updated to reflect the final implementation. Flagged as non-blocking.

---

## Blockers

### BLOCKER-1: Lossy error message on partner sync delete validation (REQ-34)

**Location:** `TierFacade.java:272-279`

**Finding (C7):**
When `deactivateSlab` throws a `PointsEngineRuleServiceException` because the slab is referenced in partner sync config, the exception is caught generically:

```java
} catch (Exception e) {
    logger.error("deleteTier: Thrift deactivateSlab failed for tierId={}", tierId, e);
    throw new InvalidInputException("Failed to deactivate tier in backend: " + e.getMessage());
}
```

The `PointsEngineRuleServiceException` message from the Thrift impl is:
> "Cannot deactivate slab X — it is referenced in Y partner program tier sync configuration(s). Remove partner sync mappings first."

This specific message IS preserved via `e.getMessage()` in the re-throw. However, the controller wraps it in a generic `ApiError(400L, e.getMessage())`, so the client does receive the full message. On re-verification this is actually propagated correctly end-to-end.

**Re-assessment (C6):** The message IS passed through `e.getMessage()`. The original concern about "Failed to deactivate tier in backend: " prefix IS present but the actionable partner sync message follows after the colon. The client response body will contain: `{"errors": [{"code": 400, "message": "Failed to deactivate tier in backend: Cannot deactivate slab X — it is referenced in Y partner program tier sync configuration(s). Remove partner sync mappings first."}]}`.

This is not ideal UX but not a correctness blocker. **DEMOTED TO NON-BLOCKING** — see Non-Blocking findings.

### BLOCKER-1 (revised): APPROVE reverse failure gap — MongoDB save failure after Thrift success

**Location:** `TierFacade.java:362-400`

**Finding (C7 — code verified, gap identified):**

The APPROVE flow (F-05) has the following sequence:
1. Call `createOrUpdateSlab` Thrift → MySQL slab written.
2. On success: `tier.setSlabId(result.getId()); tier.setStatus(TierStatus.ACTIVE);`
3. Call `tierRepository.save(tier)` → MongoDB document updated.

If Step 3 fails (MongoDB transient error, connection issue, or network partition), the flow throws an exception. The catch block at line 394 reverts the MongoDB status to `PENDING_APPROVAL`. But the MySQL slab row ALREADY EXISTS (Step 1 succeeded). The rollback sets `tier.setStatus(TierStatus.PENDING_APPROVAL)` and calls `tierRepository.save(tier)` — but if MongoDB is unavailable, this save also fails, leaving:

- MySQL: slab row with `is_active=1` (fully active in evaluation engine)
- MongoDB: `tier.status = PENDING_APPROVAL` (or could be stuck in indeterminate state if even the rollback save failed)

A retry of APPROVE will call `createOrUpdateSlab` again (because `slabId == null` at the MongoDB read), potentially creating a DUPLICATE slab row in MySQL. The idempotency check at line 342 only guards the case where `slabId != null AND status == ACTIVE` — it does NOT protect against the case where Thrift created the slab but MongoDB never recorded the slabId.

**Session memory reference:** Lines 123 (WAL pattern documented), line 203 (open question: "Is the simple try-catch rollback on APPROVE accepted for production?"). This question was raised in SDET phase and remains formally unresolved.

**Severity assessment:** This is a data integrity concern (G-05 — multi-step mutation without true atomicity). The risk is low in practice (MongoDB transient errors are rare), but the failure mode is silent: a stale PENDING_APPROVAL tier and a ghost MySQL slab. Idempotent retry makes it worse.

**Decision required:** This blocker requires a user decision (open question from SDET phase). Two options:
- A. Accept the simple rollback pattern (document the known gap). Mark F-05 as deferred.
- B. Implement the WAL pattern before merge.

**BLOCKER status: CONDITIONAL — requires user to resolve the open question from SDET (session-memory line 203) before this can be cleared.**

---

### BLOCKER-2: `is_active` column DDL not in cc-stack-crm schema (B-1 from backend-readiness, deferred)

**Location:** `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/program_slabs.sql`

**Finding (C7 — from backend-readiness.md B-1):**
The `is_active` column is present in `ProgramSlab.java` (line 96) and used in all 3 updated DAO queries plus `deactivateSlab`. However, the canonical DDL file in `cc-stack-crm` does NOT include this column. The feature prompt states "DDL (is_active column) deferred pending lead approval — accepted risk."

This is a known deferred risk. The code cannot function (STOP/DELETE flow will throw SQL exceptions) without the DDL being applied to the database. **This is an operational blocker — the code is correct, but it will fail at runtime without the DDL.**

Per the prompt this is accepted risk. Documenting here for completeness and to ensure it appears in the merge checklist.

**BLOCKER status: OPERATIONAL — code is correct. DDL must be applied before any STOP/DELETE operation is invoked in any environment. Must not merge to production without cc-stack-crm DDL change applied first.**

---

## Non-Blocking Findings

### NB-1: Partner sync error message has "Failed to deactivate tier in backend: " prefix

**Location:** `TierFacade.java:279`

The client receives `"Failed to deactivate tier in backend: Cannot deactivate slab X — it is referenced in Y partner program tier sync configuration(s)..."`. The `"Failed to deactivate tier in backend: "` prefix is redundant noise and makes the message harder to parse programmatically.

**Suggestion:** Detect `PointsEngineRuleServiceException` specifically and re-throw with a clean, structured message. Or add a dedicated error code (e.g., `TIER_HAS_PARTNER_SYNC_REFERENCE`) to `ResponseWrapper.ApiError` for machine-readable client handling.

---

### NB-2: `TierRequest.programId` undocumented in LLD and HLD API contract

**Location:** `TierRequest.java:22-23` vs `03-designer.md` Section 3.8 and `01-architect.md` Section 4.1

The implementation adds `@NotNull Integer programId` to `TierRequest`. Neither the LLD interface contract nor the HLD POST body schema includes this field. This changes the API contract that UI teams and external consumers would depend on.

**Suggestion:** Update `01-architect.md` Section 4.1 POST body and `03-designer.md` Section 3.8 TierRequest to add `programId`. Alternatively, consider whether `programId` should be a query parameter on the endpoint (more REST-idiomatic for scoping) — requires a decision.

---

### NB-3: `deleteTier` signature has undocumented `userId` parameter

**Location:** `TierFacade.java:243` vs `03-designer.md` Section 3.14

LLD specifies `deleteTier(Long orgId, String tierId)`. Implementation is `deleteTier(Long orgId, Integer userId, String tierId)`. The addition is correct (needed for `setLastModifiedBy`).

**Suggestion:** Update LLD Section 3.14 to reflect the final signature.

---

### NB-4: `listTiers(includeInactive=true)` filters out SNAPSHOT status inconsistently

**Location:** `TierFacade.java:115-120`

When `includeInactive=true`, the code fetches all tiers then filters out SNAPSHOT. SNAPSHOT is a system-internal status (not a user-facing lifecycle state). The client cannot influence this via any parameter — SNAPSHOT documents are always hidden. This is reasonable behavior but undocumented.

**Suggestion:** Add a comment explaining that SNAPSHOT is an internal versioning state and is always excluded from API responses regardless of `includeInactive` flag. Consider whether `05b-gap-analysis.md` F-09 finding should generate a new query param (e.g., `includeSnapshots=true`) for potential debugging use.

---

### NB-5: Concurrent direct DELETE and STOP status change can race

**Location:** `TierFacade.java:242` (`deleteTier` method)

From `backend-readiness.md W-4`: `deleteTier` itself has `@Lockable(key = "'lock_tier_delete_'...")`. `changeTierStatus(STOP)` holds lock `'lock_tier_status_'...`. These are DIFFERENT lock keys. A concurrent direct `DELETE /v3/tiers/{id}` and a `POST /v3/tiers/{id}/status` with action=STOP can both pass validation simultaneously.

The double-deactivation is idempotent at the MySQL level (second call throws `PointsEngineRuleServiceException` which surfaces as 400). No data corruption results. This is a usability issue (unexpected 400 for one of two concurrent callers) rather than a correctness issue.

**Suggestion (backend-readiness W-4):** Unify the lock key for delete and STOP to `'lock_tier_stop_' + orgId + '_' + tierId`, or document that STOP and DELETE are semantically equivalent and concurrent calls are acceptable behavior.

---

### NB-6: F-05 WAL gap — Thrift success, MongoDB save failure leaves divergent state

Already documented as BLOCKER-1 with conditional status. Repeating here as non-blocking finding under the assumption the user accepts the simpler pattern (open question from SDET session-memory line 203).

If user accepts: Add a comment in `approveTier` explaining the known gap and mitigation strategy (e.g., "A background reconciliation job could detect MySQL slabs with no matching ACTIVE MongoDB document and clean them up"). Mark the session-memory question as resolved with the accepted risk.

---

### NB-7: `SlabInfo.id` = 0 implicit sentinel for new slab creation

**Location:** `TierFacade.java:351-354`

From `backend-readiness.md I-2`: When `tier.getSlabId() == null`, `slabInfo.setId()` is never called. Thrift Java sets `id=0` implicitly. The `createOrUpdateSlab` EMF impl interprets `id=0` as "create new slab". This is implicit coupling that could break if the Thrift layer ever enforces `required` field validation strictly.

**Suggestion:** Add an explicit `slabInfo.setId(0);` with a comment explaining the sentinel contract, OR change `id` in the Thrift IDL from `required` to `optional` (additive-safe).

---

### NB-8: `getMemberCountPerSlab` Thrift failure degradation behavior unresolved

**Location:** `TierFacade.java:417-428`, `TierFacade.java:430-448`

Implementation returns `null` for memberCount on Thrift failure (graceful degradation). Session-memory open question (line 205) asks whether this should be `null` or HTTP 500. The SDET plan (IT-10) assumes `null` (degraded mode). No formal resolution in session memory.

**Suggestion:** Resolve the open question formally in session memory. If `null` is accepted, document the degradation contract in the API spec (UI needs to handle `memberCount: null` gracefully).

---

## Questions for User

The following items require explicit decisions before the review can be fully closed. These are the same open questions surfaced in SDET that have not been resolved:

1. **[BLOCKER-conditional] WAL pattern for APPROVE (F-05):** Is the simple try-catch rollback accepted for production? The known gap is: if `createOrUpdateSlab` Thrift succeeds but `tierRepository.save(tier)` fails, a ghost MySQL slab is created with no matching ACTIVE MongoDB document. Options:
   - A. Accept as deferred risk (document + add reconciliation job later). This is reversible — add WAL before any high-volume usage.
   - B. Implement WAL before merge. Routes BLOCKER-1 to Developer.

2. **[Non-blocking] `programId` source (F-03):** Should `programId` come from the request body (current), a query parameter, or some other mechanism? This affects the API contract doc for UI teams. Update HLD and LLD to match whichever approach is accepted.

3. **[Non-blocking] Strategy CSV/JSON update on soft-delete (F-02):** Session memory has contradictory entries. Line 108 says "strategy CSV with stale slab entries is harmless — evaluation skips soft-deleted slabs." Line 141 says "deactivateSlab must update SLAB_UPGRADE threshold CSV AND SLAB_DOWNGRADE JSON." LLD sides with updating, implementation does not. Which decision prevails? If line 108 (no update needed), close F-02 and update LLD. If line 141 (update needed), route to Developer.

4. **[Non-blocking] `getMemberCountPerSlab` Thrift failure behavior:** Is returning `memberCount: null` on Thrift failure accepted? If yes, update session-memory and document in API spec. If HTTP 500 is preferred, route to Developer.

---

## Assumptions Made

- **A-01 (C7):** F-01 (partner sync check) is considered resolved at the Thrift layer (`deactivateSlab` lines 4192-4197) per the reviewer prompt statement "F-01 (partner sync check) fixed in deactivateSlab." The check exists in the implementation. The error message propagation concern is flagged as non-blocking (NB-1).
- **A-02 (C7):** F-06 (stale STOP response) is resolved. TierFacade.java:316-318 reloads from MongoDB after `deleteTier`. Evidence verified.
- **A-03 (C6):** The BLOCKER-2 DDL gap is accepted risk per the reviewer prompt ("DDL deferred pending lead approval — accepted risk"). Documented as operational blocker requiring pre-deployment action.
- **A-04 (C5):** The `@Lockable` annotation behavior (ignores `ttl`/`acquireTime` per backend-readiness W-2) is a pre-existing platform behavior. Not introduced by this feature. Flagged in non-blocking findings but not raised as a new blocker.

---

## Summary

| Category | Count | Severity |
|----------|-------|---------|
| Requirements PASS | 34/35 | — |
| Requirements PARTIAL | 1 (REQ-34) | Non-blocking after re-assessment |
| BLOCKERS — Code | 1 (conditional) | BLOCKER-1: WAL gap requires user decision |
| BLOCKERS — Operational | 1 | BLOCKER-2: is_active DDL must deploy before code |
| Non-blocking findings | 8 | NB-1 through NB-8 |
| Guardrail CRITICAL violations | 0 | — |
| Guardrail HIGH flags | 2 (G-05 partial, G-11 no tests yet) | Non-blocking |
| Open questions for user | 4 | Decision required |

**Overall verdict: CONDITIONAL PASS**

The implementation is architecturally sound and covers 34 of 35 requirements. All CRITICAL guardrails pass. Two items require resolution before this is fully clear for merge:

1. **BLOCKER-1 (conditional):** The user must decide whether the simple APPROVE rollback pattern is accepted or if WAL is required. Route to Developer if WAL is needed.
2. **BLOCKER-2 (operational):** The `is_active` DDL in cc-stack-crm must be applied to every environment before any deployment that enables the STOP/DELETE flow.

All other findings are non-blocking improvements.
