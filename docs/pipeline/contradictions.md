# Contradictions & Challenges — Tier CRUD APIs

> Feature: tier-crud
> Phase: Critic Review (post-BA, post-PRD)
> Date: 2026-04-06

---

### Contradiction #1
- **Source**: BA assumption A1, PRD "Modified Entities" section
- **Claim**: "The existing `EntityType` enum in intouch-api-v3 can be extended with `TIER` without breaking existing consumers [C6]"
- **Challenge**: The `EntityType` enum (in `intouch-api-v3/.../orchestration/EntityType.java`) currently has 8 values: PROMOTION, TARGET_GROUP, STREAK, LIMIT, LIABILITY_OWNER_SPLIT, WORKFLOW, JOURNEY, BROADCAST_PROMOTION. These are all **promotion sub-entities** used in the orchestration/rollback pipeline. The enum lives under `unified.promotion.orchestration` package -- it is semantically a promotion orchestration enum, not a general-purpose entity type registry. Adding `TIER` here conflates two unrelated domain concepts (tier management vs. promotion orchestration). Furthermore, the `RequestManagementController.changeStatus()` method returns `ResponseEntity<ResponseWrapper<UnifiedPromotion>>` -- the return type is **hardcoded to UnifiedPromotion**. A TIER status change cannot return a `UnifiedPromotion` object. This is not a simple enum addition; it requires refactoring the controller's return type to a generic wrapper or creating a separate endpoint. The C6 confidence is **inflated** -- this should be C3 at best, since the coupling goes deeper than just adding an enum value.
- **Evidence needed**: (1) Check all switch statements on `EntityType` -- the `RollbackManager` has two switch blocks that would need `default` or `TIER` cases. (2) Verify whether `UnifiedPromotion` can be the return type for tier status changes, or whether this forces a separate controller. (3) Check if any serialization/deserialization of `EntityType` exists in API contracts (e.g., Swagger docs, client SDKs).
- **Severity**: BLOCKER
- **Recommendation**: Downgrade to C3. Design decision needed: either (a) create a separate `TierEntityType` or a new general-purpose `ManagedEntityType` enum, or (b) refactor `RequestManagementController` to return a generic `ResponseWrapper<?>` and route via the facade pattern. Option (b) is more work but more extensible. This must be resolved in the Architecture phase before any implementation.

---

### Contradiction #2
- **Source**: BA claim "Soft delete -- set active=0 in program_slabs", PRD Data Model Changes
- **Claim**: "Adding an `active` column (default 1) to `program_slabs` is backward compatible. Existing rows get active=1."
- **Challenge**: The `PeProgramSlabDao` has 3 query methods: `findByProgram(orgId, programId)`, `findByProgramSlabNumber(orgId, programId, slabNumber)`, and `findNumberOfSlabs(orgId, programId)`. **None of these filter on `active`**. After the migration, soft-deleted tiers will still appear in ALL existing queries. This means: (1) `findByProgram` returns soft-deleted tiers to upgrade/downgrade/renewal logic, (2) `findNumberOfSlabs` counts soft-deleted tiers, producing wrong slab counts used in promotion allocation strategies (see `SimplePromotionServiceImpl`, `RangePromotionServiceImpl`, `KeywordPromotionServiceImpl` which call `getAllSlabs()` and use `.size()` for allocation), (3) `programSlabToEventForestTiers()` in `PointsEngineUtils` converts ALL ProgramSlabs to Tiers without any active check. The claim that adding `active` is backward-compatible is **only true at the schema level** -- it is **not backward-compatible at the query level** without updating every consumer.
- **Evidence needed**: Full audit of all callers of `PeProgramSlabDao.findByProgram()`, `getProgramSlabs()`, `getAllSlabs()`, and `program.getProgramSlabs()`. Count of affected call sites. Verification that adding `WHERE active=1` to these queries does not break any test.
- **Severity**: BLOCKER
- **Recommendation**: This is a hidden cross-cutting concern. Every existing DAO query and service method that loads slabs must be updated to filter `active=1`, OR the soft-delete must use a different mechanism (e.g., a separate `deleted_slabs` table, or JPA `@Where` annotation on the entity). The BA/PRD underestimates the blast radius of this change. Add a dedicated impact analysis task in the Architecture phase.

---

### Contradiction #3
- **Source**: BA claim "Tier status lifecycle: DRAFT -> PENDING_APPROVAL -> ACTIVE -> STOPPED", PRD Data Model Changes (status column)
- **Claim**: "Adding a `status` column (default 'ACTIVE') to `program_slabs` is backward compatible. Existing rows get status='ACTIVE'."
- **Challenge**: Same problem as #2 but worse. The `ProgramSlab` entity (verified in `ProgramSlab.java`) has **no status field at all**. Every piece of code that reads ProgramSlab today assumes all slabs are implicitly active and usable. After this change, a tier in DRAFT status should NOT participate in upgrade/downgrade evaluation, but `SlabUpgradeService`, `SlabDowngradeService`, `PointsEngineSlabUpgradeInstructionExecutorImpl`, `PointsEngineSlabDowngradeInstructionExecutorImpl`, and `RenewSlabInstructionImpl` all load slabs without any status filter. A DRAFT tier with serialNumber=3 would appear in the upgrade path. This directly contradicts the PRD NFR: "Existing tier evaluation logic must continue working unchanged."
- **Evidence needed**: Trace the full upgrade evaluation path: how does `SlabUpgradeService` determine the next tier? Does it use `serialNumber` ordering on all slabs? If yes, a DRAFT slab injected into that sequence would corrupt evaluations.
- **Severity**: BLOCKER
- **Recommendation**: The claim that "CRUD is separate from evaluation" (A4, rated C6) is dangerously wrong if DRAFT/STOPPED slabs are visible to the evaluation engine. Either: (a) the evaluation engine must be updated to filter `WHERE status='ACTIVE'` (contradicts "existing logic unchanged"), or (b) DRAFT tiers must be stored in a **separate staging table** until approved, then moved to `program_slabs` on approval. Option (b) is cleaner but more complex. This is an architectural fork that must be resolved before LLD.

---

### Contradiction #4
- **Source**: PRD Validation Rules, BA US-3 acceptance criteria
- **Claim**: "Threshold must be higher than the current highest tier's threshold" (for create). "Same field-level validation as create" (for update, US-4).
- **Challenge**: The threshold validation rule is specified for **create** (new tier added at top). But for **update** (US-4), the rule "same validation as create" would mean: "updated threshold must be higher than the current highest tier." But what if you are updating the HIGHEST tier's threshold downward? Or updating a MIDDLE tier's threshold? The validation rule for updates needs to be: `tier[n-1].threshold < updated_threshold < tier[n+1].threshold` (between neighbors), not simply "higher than highest." The BA/PRD does not distinguish create validation from update validation for thresholds. Additionally, ProgramSlab has no `threshold` field at all -- thresholds appear to be stored elsewhere (likely in strategy/rule configuration, not in the `program_slabs` table). Where is the threshold actually stored?
- **Evidence needed**: (1) Find where tier eligibility thresholds are stored in the schema (is it in `program_slabs`, in a strategy table, or in Thrift config?). (2) Define the exact update validation rule for thresholds when updating a non-top tier.
- **Severity**: HIGH
- **Recommendation**: Separate create and update validation rules for thresholds. For update: threshold must maintain ordering relative to adjacent tiers. Investigate where thresholds are actually stored -- if they are in strategy config rather than `program_slabs`, the CRUD API cannot validate them without loading strategy data, adding a cross-concern dependency.

---

### Contradiction #5
- **Source**: BA US-4, PRD
- **Claim**: "If tier is in PENDING_APPROVAL status, update is rejected with error (must approve/reject first)"
- **Challenge**: This creates a **deadlock scenario**. Consider: (1) User creates tier, submits for approval (PENDING_APPROVAL). (2) Approver reviews and finds a typo in the name. (3) Approver must REJECT to allow the maker to fix it. (4) Maker fixes, resubmits. This is a 4-step round-trip for a typo. The alternative -- allowing edits to PENDING_APPROVAL entities -- is what most maker-checker systems do (the edit resets status to DRAFT). The UnifiedPromotion pattern needs to be checked: does it allow edits during PENDING_APPROVAL, or does it also require reject-first? If it requires reject-first, that is a known UX pain point being replicated.
- **Evidence needed**: Check UnifiedPromotion behavior: can a PENDING_APPROVAL promotion be edited? If yes, the tier API should match. If no, document this as a known limitation.
- **Severity**: MEDIUM
- **Recommendation**: Consider allowing edits to PENDING_APPROVAL tiers that auto-reset status to DRAFT (with notification to approver that the submission was withdrawn). At minimum, document the reject-first workflow explicitly in the API contract with clear error messages.

---

### Contradiction #6
- **Source**: BA assumption A4, PRD NFR "Backward compatibility"
- **Claim**: "Existing tier evaluation logic (upgrade/downgrade/renewal) continues to work unchanged -- the new APIs only manage configuration, not evaluation execution [C6]"
- **Challenge**: This claim is rated C6 (90-97%) but is supported by **zero evidence** from actual code tracing. It is a classic "Confident Vacuum" anti-pattern (principles.md). The evaluation logic loads slabs from `PeProgramSlabDao.findByProgram()` which will now include DRAFT and STOPPED slabs. The `SlabUpgradeService` uses `serialNumber` to determine tier ordering. A DRAFT tier with serialNumber=4 (highest) would appear as a valid upgrade target. The `PartnerProgramTierSyncConfiguration` maps partner program slabs to loyalty program slabs by ID -- a soft-deleted or DRAFT slab referenced in a sync config would cause sync failures. Evidence from code: `PointsEngineRuleService` lines 1715-1743 iterate `partnerProgram.getLoyaltyPartnerProgramSyncTiers()` and save `PartnerProgramTierSyncConfiguration` referencing slab IDs. If those slabs become inactive, the sync breaks silently.
- **Evidence needed**: Full call-chain trace from `SlabUpgradeService.upgradeSlab()` through to the DAO query, confirming whether it filters by any status/active field. Same for downgrade and renewal paths. Check `PartnerProgramTierSyncConfiguration` foreign key integrity with soft-deleted slabs.
- **Severity**: BLOCKER
- **Recommendation**: Downgrade from C6 to C2. This claim MUST be verified by code tracing before proceeding to Architecture. If evaluation logic is affected, the scope of this feature expands significantly -- every upgrade/downgrade/renewal code path needs modification, which contradicts the "backend only, CRUD layer" scoping.

---

### Contradiction #7
- **Source**: BA scope, PRD "Maker-Checker (reusing existing infrastructure)"
- **Claim**: "Maker-checker uses existing `RequestManagementController` with TIER entity type added. Follows same review pattern as `UnifiedPromotionController.reviewPromotion()`"
- **Challenge**: The `RequestManagementController.changeStatus()` method signature returns `ResponseEntity<ResponseWrapper<UnifiedPromotion>>`. It takes `PromotionStatus existingStatus` as a query param and delegates to `RequestManagementFacade` which **only handles `EntityType.PROMOTION`** (verified: the `if` block checks `entityType == EntityType.PROMOTION`, else throws `InvalidInputException`). "Reusing existing infrastructure" means modifying: (1) the controller's return type generics, (2) the facade's routing logic, (3) potentially the `StatusChangeRequest` DTO which has `getPromotionStatus()` (promotion-specific naming), (4) the `PromotionAction.fromString()` call which is promotion-specific. This is not "reusing" -- this is **refactoring** existing code to be generic. The effort estimate is understated.
- **Evidence needed**: Full diff of changes needed in `RequestManagementController`, `RequestManagementFacade`, `StatusChangeRequest`, and `PromotionAction` to support tier entity type. Assess whether this refactoring risks breaking existing promotion maker-checker flow.
- **Severity**: HIGH
- **Recommendation**: Either (a) create a completely separate `TierRequestManagementController` that does not touch the promotion code path (safer, more isolated), or (b) refactor the existing controller to be truly generic (riskier, but better long-term). Document this as an explicit ADR in the Architecture phase. The PRD's casual "reusing existing infrastructure" masks significant refactoring work.

---

### Contradiction #8
- **Source**: PRD Data Model Changes, BA constraints
- **Claim**: "ProgramSlab entity gets `active` and `status` columns. ProgramSlab entity has fields: pk, program, programId, serialNumber, name, description, createdOn, metadata."
- **Challenge**: The `ProgramSlab` entity is extremely lean -- it has only 7 fields (pk, program, programId, serialNumber, name, description, createdOn, metadata). The BA/PRD propose that the CRUD API exposes: eligibility KPI type, eligibility threshold, validity period, renewal conditions, downgrade target, downgrade-on-return flag, upgrade schedule, upgrade bonus, color. **None of these fields exist on `ProgramSlab`**. They are spread across strategy tables, `TierConfiguration` DTO (serialized in metadata?), and other entities. The CRUD API as specified requires aggregating data from multiple sources to present a "full tier configuration" -- this is not a simple CRUD over `program_slabs`, it is an **aggregate API** spanning multiple tables/services.
- **Evidence needed**: Map each field in the `TierResponse` DTO to its actual storage location. Identify which fields come from `program_slabs`, which from strategy tables, which from `TierConfiguration` JSON in metadata, and which from other entities entirely.
- **Severity**: HIGH
- **Recommendation**: The PRD should explicitly document the data mapping. The complexity of "Create Tier" is not Medium -- it is High, because creating a tier via the API means writing to multiple tables/strategies atomically. This affects the Thrift service design (one Thrift call must orchestrate writes to multiple DAOs) and the Architecture phase significantly.

---

### Contradiction #9
- **Source**: BA US-5, PRD validation rules
- **Claim**: "Soft-deleted tier's members need to be addressed -- either migrated or left in place. Decision: leave in place, mark for re-evaluation at next cycle."
- **Challenge**: "Leave in place" means customers remain enrolled in a tier that no longer exists in the API response (GET /tiers excludes it). This creates a phantom state: the tier is invisible to API consumers but still affects member records. What happens during the next upgrade/downgrade evaluation cycle? If the evaluation engine loads all slabs (including active=0), the member stays. If it filters active=1, the member's current slab ID points to a nonexistent tier -- how does the downgrade logic handle that? `SlabDowngradeService` determines the downgrade target based on the current slab and the program's slab hierarchy. A member in a deleted slab would have no valid position in the hierarchy. This is not an edge case -- it is a guaranteed runtime scenario.
- **Evidence needed**: Trace what happens in `SlabDowngradeService` and `DowngradeSlabActionImpl` when a customer's current slab is not in the loaded slab list. Does it throw an exception? Default to base tier? Skip the customer?
- **Severity**: HIGH
- **Recommendation**: "Leave in place" is not a valid decision without understanding the downstream behavior. Either: (a) force-migrate members to the downgrade target before soft-deleting, or (b) explicitly handle the "member in deleted tier" case in evaluation logic. This must be resolved before implementation, not deferred to "next cycle."

---

### Contradiction #10
- **Source**: BA US-1, PRD API Endpoints
- **Claim**: "GET /tiers returns all active tiers for the authenticated org's program. Tiers ordered by hierarchy (base tier first, highest tier last)."
- **Challenge**: The endpoint path is `GET /v3/tiers` but there is no program ID in the path. How does the API know which program's tiers to return? The `PeProgramSlabDao.findByProgram()` requires both `orgId` AND `programId`. The orgId comes from authentication context, but programId must come from somewhere -- query parameter? Path variable? The PRD does not specify this. If an org has multiple programs (which is common), the API is ambiguous. The UnifiedPromotion pattern uses promotion IDs directly, not program scoping, so this is a new pattern.
- **Evidence needed**: Clarify API contract: is programId a required query parameter (`GET /v3/tiers?programId=123`), a path variable (`GET /v3/programs/{programId}/tiers`), or derived from some default program selection?
- **Severity**: MEDIUM
- **Recommendation**: Add `programId` as a required query parameter or restructure to `GET /v3/programs/{programId}/tiers`. Document explicitly in the API contract. This affects all 5 CRUD endpoints.

---

### Contradiction #11
- **Source**: BA assumption A2
- **Claim**: "The `PromotionStatus` enum values (DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED) are reusable for tiers, or a new `TierStatus` enum with the same values is created [C5]"
- **Challenge**: The existing `PromotionStatus` enum is in `intouch-api-v3/.../enums/PromotionStatus.java` AND separately in `emf-parent/.../enums/PromotionStatus.java`. The `StatusChangeRequest` DTO uses `getPromotionStatus()` which returns promotion-specific status strings. If we reuse `PromotionStatus` for tiers, we inherit promotion-specific values that may not apply (e.g., if PromotionStatus has values like SCHEDULED, EXPIRED that don't apply to tiers). If we create `TierStatus`, we duplicate the status machine and need separate handling in the request management flow. Neither option is clean. The C5 rating defers this to Architecture but the decision has cascading impact on every subsequent phase.
- **Evidence needed**: Read the full `PromotionStatus` enum to see all values (not just the 4 mentioned in BA). Check if any status values are promotion-specific.
- **Severity**: MEDIUM
- **Recommendation**: Read the actual `PromotionStatus` enum values before deciding. If it contains promotion-specific states, create a separate `TierStatus` enum. If it is truly generic (only DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED), consider renaming it to `ManagedEntityStatus` and sharing it.

---

### Contradiction #12
- **Source**: PRD NFR "Performance: GET /tiers should respond < 200ms for programs with up to 20 tiers"
- **Claim**: Tier list is a simple query with good performance characteristics.
- **Challenge**: Per Contradiction #8, GET /tiers is NOT a simple query on `program_slabs`. It requires aggregating data from multiple sources (program_slabs + strategies + TierConfiguration JSON + potentially partner program sync config). If each tier requires loading its upgrade strategy, downgrade strategy, renewal strategy, and parsed JSON configuration, this is N+1 territory for 20 tiers. Without explicit caching or eager loading, 200ms may not be achievable.
- **Evidence needed**: Prototype the data aggregation path. Count the number of DB queries needed per tier to assemble a full `TierResponse`.
- **Severity**: LOW
- **Recommendation**: Flag for Architecture phase. Consider whether GET /tiers returns a summary (just program_slabs fields) vs. GET /tiers/{id} returns full detail. Lazy-load strategies only on detail view.

---

### Contradiction #13
- **Source**: BA "Stale TierConfigController.class in emf-parent/target: ignore, proceed fresh"
- **Claim**: "TierConfigController.class found as compiled artifact without source code. Decision: stale artifacts, proceed fresh."
- **Challenge**: The session memory records this was confirmed by the user, which is fine. However, the existence of compiled controller classes without source suggests either: (a) someone previously attempted this feature and abandoned it (incomplete work exists somewhere), or (b) these are generated artifacts from a code generation tool. If (a), there may be partially-implemented Thrift definitions, DAO changes, or DB migrations in other branches that could conflict with or duplicate this work. The "proceed fresh" decision is valid but the **risk of discovering conflicts later** is not mitigated.
- **Evidence needed**: Check git history for any tier-crud related branches. Check if Thrift IDL files contain any tier CRUD service definitions. Check Flyway migrations for any `active` or `status` column additions to `program_slabs`.
- **Severity**: LOW
- **Recommendation**: Quick git branch search and Flyway migration scan before starting implementation. 10 minutes of prevention avoids days of conflict resolution.

---

## Summary

| Severity | Count | Contradictions |
|----------|-------|----------------|
| **BLOCKER** | 4 | #1, #2, #3, #6 |
| **HIGH** | 4 | #4, #7, #8, #9 |
| **MEDIUM** | 3 | #5, #10, #11 |
| **LOW** | 2 | #12, #13 |

### Pre-Mortem: "This feature launched and failed. Why?"

1. **Most likely failure**: DRAFT/STOPPED tiers leaked into the upgrade evaluation engine, causing customers to be upgraded to non-active tiers. Silent data corruption affecting thousands of customers before anyone noticed. Root cause: `PeProgramSlabDao.findByProgram()` was not updated to filter by status/active, and nobody traced the evaluation code path end-to-end.

2. **Second most likely**: The `RequestManagementController` refactoring to support TIER entity type introduced a regression in the existing promotion maker-checker flow. A subtle type mismatch or routing error caused promotion approvals to fail in production for 2 hours.

3. **Third most likely**: The CRUD API launched but GET /tiers returned incomplete data (missing strategies, thresholds, renewal conditions) because the team underestimated the data aggregation complexity. The API was technically "working" but useless for the stated goal of "full tier configuration at a glance."

4. **Sleeper failure**: A customer in a soft-deleted tier triggered a downgrade evaluation. The downgrade service threw a NullPointerException because the customer's slab was not in the loaded slab list. The error was swallowed by a catch-all handler, and the customer silently stayed in the deleted tier forever.
