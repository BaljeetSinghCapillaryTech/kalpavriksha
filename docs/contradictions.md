# Critic Report -- Subscription-CRUD

> Phase: 2 (Critic + Gap Analysis)
> Date: 2026-04-09
> Approach: Devil's Advocate -- adversarial challenge of every claim in BA and PRD

---

## Contradiction Summary

| # | Severity | Source | Claim Challenged | Verdict |
|---|----------|--------|-----------------|---------|
| C-1 | HIGH | BA/PRD (KD-10) | "v3 enrollment APIs call EMF Thrift directly" -- but intouch-api-v3 has NO Thrift client methods for partner program events | VALID -- gap exists |
| C-2 | MEDIUM | BA-machine | "emf-parent: 0 new files, 0 modifications" at C7 | OVERCLAIMED -- needs C5 |
| C-3 | MEDIUM | BA-machine | "thrifts: 0 new files, 0 modifications" at C7 | CONFIRMED -- Thrift IDL already has events |
| C-4 | HIGH | BA/PRD | "intouch-api-v3: ~10-15 new files, ~3-4 modified" at C6 | UNDERCOUNTED -- missing Thrift client class |
| C-5 | LOW | PRD (AC-7.2) | "On ACTIVE transition, EMF Thrift partnerProgramLinkingEvent is called" | MISLEADING -- partnerProgramLinkingEvent is for ENROLLMENT, not for program config publish |
| C-6 | MEDIUM | BA | RequestManagementController returns UnifiedPromotion type | VALID -- needs generic or new return type |
| C-7 | MEDIUM | PRD (E2-US6) | "ARCHIVE transitions from DRAFT, ACTIVE, or EXPIRED" | NOVEL -- no precedent in UnifiedPromotion pattern |
| C-8 | LOW | BA | StatusChangeRequest has @Pattern regex for PROMOTION actions | VALID -- needs new DTO or generalized pattern |
| C-9 | MEDIUM | PRD (E4-US1) | "Enrollment on PAUSED subscription returns 400" | AMBIGUOUS -- enforcement point unclear |
| C-10 | LOW | PRD (E1-US4) | "PUT on ACTIVE creates new DRAFT (version N+1)" -- follows UnifiedPromotion pattern | CONFIRMED |

---

## Detailed Contradictions

### C-1: Missing Thrift Client for Partner Program Events [HIGH]

**BA/PRD Claim (KD-10)**: "intouch-api-v3 gets NEW v3 subscription CRUD + enrollment APIs that call EMF Thrift DIRECTLY (same pattern as UnifiedPromotion calling PointsEngineRulesThriftService)."

**Challenge**: This claim implies the Thrift client infrastructure already exists. It does not.

**Evidence**:
- `PointsEngineRulesThriftService` uses `PointsEngineRuleService.Iface` (port 9199) -- this is for promotion RULESET CRUD. It has NO partner program methods. [C7 -- grep returned no matches]
- `PointsEngineThriftService` uses `PointsEngineService.Iface` -- also has NO partner program methods. [C7 -- grep returned no matches]
- `EmfPromotionThriftService` uses `EMFService.Iface` -- this interface DOES have `partnerProgramLinkingEvent`, `partnerProgramDeLinkingEvent`, `partnerProgramUpdateEvent`. But `EmfPromotionThriftService` only wraps `issuePromotionToEntityEvent` and `earnPromotionToEntityEvent`. [C7 -- read file]
- The EMF Thrift IDL defines partner program events on `EMFService.Iface` (emf.thrift lines 1798-1810). [C7 -- read file]
- EMF-side handler is `EMFThriftServiceImpl` in the `emf` module (not `pointsengine-emf`), annotated `@ExposedCall(thriftName = "emf")`. [C7 -- read file]

**Impact**: The BA and PRD assume enrollment "just works" via Thrift. In reality, a new Thrift client class (or extension of `EmfPromotionThriftService`) must be created in intouch-api-v3 to call `partnerProgramLinkingEvent`, `partnerProgramDeLinkingEvent`, `partnerProgramUpdateEvent`. This is an additional new file not counted in the BA's cross-repo change estimate.

**Recommendation**: Add to the implementation plan: create `PartnerProgramThriftService.java` in intouch-api-v3 using `EMFService.Iface` (same client/port as `EmfPromotionThriftService`). Update BA-machine cross-repo count.

---

### C-2: emf-parent "0 modifications" Claim Overclaimed [MEDIUM]

**BA-machine Claim**: "emf-parent: 0 new files, 0 modifications" at C7.

**Challenge**: While the BA correctly identifies that no Java source changes are needed in emf-parent (MongoDB-first architecture avoids this), the confidence level of C7 ("near certain, verified from primary source") is overclaimed.

**Evidence**:
- emf-parent has 216 files referencing PartnerProgram. [C7 -- grep count]
- `EMFThriftServiceImpl` handles partner program events and delegates to `PartnerProgramLinkingHelper`, `PartnerProgramUpdateHelper`. [C7 -- found in files]
- These handlers create enrollment records in MySQL via `PartnerProgramLinkingInstructionExecutor`. [C7 -- found in files]
- The BA claims we "call EMF Thrift to create/update MySQL partner_programs record" on approval. If EMF already handles this correctly for program-level operations, then 0 modifications is correct.
- However, the Thrift event `PartnerProgramLinkingEventData` requires `CustomerPartnerProgramRef` which has `partnerProgramName` (not ID). The subscription would need to have a `name` that maps to the partner_programs table. This interaction path was not verified.

**Recommendation**: Downgrade to C5. The claim is probably correct but the interaction between MongoDB subscription name and MySQL partner_programs lookup was not verified. Phase 5 (codebase research) should trace the full enrollment path.

---

### C-3: thrifts "0 modifications" -- CONFIRMED [LOW]

**BA-machine Claim**: "thrifts: 0 new files, 0 modifications" at C7.

**Evidence**: The Thrift IDL already defines `partnerProgramLinkingEvent`, `partnerProgramDeLinkingEvent`, `partnerProgramUpdateEvent` with their data structures (`PartnerProgramLinkingEventData`, `PartnerProgramDeLinkingEventData`, `PartnerProgramUpdateEventData`). No new Thrift methods needed. [C7 -- verified in emf.thrift lines 1305-1360, 1798-1810]

**Verdict**: Confirmed. C7 is appropriate.

---

### C-4: Cross-Repo File Count Undercounted [HIGH]

**BA-machine Claim**: "intouch-api-v3: ~10-15 new files, ~3-4 modified" at C6.

**Challenge**: The new file count is missing several required files:

1. `PartnerProgramThriftService.java` (or `SubscriptionThriftService.java`) -- new Thrift client for enrollment events [missed in BA]
2. `SubscriptionStatus.java` -- new enum [counted]
3. `SubscriptionAction.java` -- new enum [counted]
4. `UnifiedSubscription.java` -- new document [counted]
5. `SubscriptionMetadata.java` -- nested object (or is it shared with Metadata?) [ambiguous]
6. `SubscriptionRepository.java` + `SubscriptionRepositoryCustom.java` + `SubscriptionRepositoryImpl.java` -- repository pattern requires 3 files following UnifiedPromotion pattern [undercounted as 1]
7. `SubscriptionFacade.java` -- facade [counted]
8. `SubscriptionController.java` -- controller [counted]
9. `SubscriptionStatusTransitionValidator.java` -- validator [counted]
10. `SubscriptionStatusChangeRequest.java` or generalized `StatusChangeRequest` [not counted]
11. Various DTOs for enrollment request/response [not counted]
12. `Reminder.java` -- embedded object [counted]
13. `CustomFieldConfig.java` -- embedded object [counted]

Modified files also undercounted:
1. `EntityType.java` -- add SUBSCRIPTION [counted]
2. `RequestManagementFacade.java` -- add routing [counted]
3. `RequestManagementController.java` -- response type needs generalization [not counted]
4. `EmfMongoConfig.java` -- add SubscriptionRepository to includeFilters [counted]
5. `StatusChangeRequest.java` -- @Pattern regex needs ARCHIVE, SUBMIT_FOR_APPROVAL, RESUME etc. [not counted]

**Recommendation**: Revise to "~15-20 new files, ~5-6 modified files" at C5.

---

### C-5: Confusion Between Program Config Publish and Enrollment Events [HIGH]

**PRD Claim (AC-7.2)**: "On ACTIVE transition, EMF Thrift `partnerProgramLinkingEvent` is called to create/update MySQL partner_programs record."

**Challenge**: `partnerProgramLinkingEvent` is for CUSTOMER ENROLLMENT (linking a customer to a partner program), NOT for creating/updating the program configuration itself.

**Evidence from Thrift IDL**:
```
PartnerProgramLinkingEventData {
  orgID, linkingStoreUnitID, loyaltyCustomerDetails,
  customerPartnerProgramRef, eventTimeInMillis, ...
}
```
This struct contains `loyaltyCustomerDetails` (customer info) and `customerPartnerProgramRef` (membership ID, tier, etc.). It's an enrollment event, not a config event.

The partner_programs MySQL table (program configuration) must already exist BEFORE enrollment can happen. The question is: who creates the partner_programs row?

Looking at `PartnerProgramLinkingInstructionExecutor` in emf-parent -- it handles the enrollment, but expects the program to already exist.

**Impact**: There may be a chicken-and-egg problem. When a subscription is approved, we need to:
1. First: Ensure the partner_programs MySQL record exists (program config)
2. Then: Allow enrollment via `partnerProgramLinkingEvent`

The current api/prototype v2 flow likely handles program creation separately. The BA needs to clarify: does approving a subscription automatically create the MySQL partner_programs record? Or must it be created via a separate Thrift call (e.g., a program management API in EMF)?

**Recommendation**: This is a BLOCKER for Phase 4. Must resolve how partner_programs MySQL records are created before enrollment can work.

---

### C-6: RequestManagementController Returns UnifiedPromotion Type [MEDIUM]

**BA Claim**: "Extend RequestManagementFacade routing for SUBSCRIPTION."

**Evidence**: `RequestManagementController.changeStatus()` returns `ResponseEntity<ResponseWrapper<UnifiedPromotion>>` -- the return type is hardcoded to `UnifiedPromotion`. [C7 -- read file]

Additionally, `RequestManagementFacade.changeStatus()` also returns `UnifiedPromotion`. [C7 -- read file]

**Impact**: Either:
(a) Generalize the return type to a common interface/superclass (breaking change risk)
(b) Create a separate subscription status endpoint (cleaner but duplicates URL pattern)
(c) Return a generic `Object` and use ResponseWrapper (ugly, loses type safety)

**Recommendation**: Option (b) is safest -- create `/v3/requests/SUBSCRIPTION/{id}/status` as a separate method in a new `SubscriptionRequestController` that returns `UnifiedSubscription`. The routing is already separated by `EntityType` path variable, so the controller can dispatch to different methods.

---

### C-7: ARCHIVE Transition Has No Precedent [MEDIUM]

**PRD Claim (E2-US6)**: "ARCHIVE transitions from DRAFT, ACTIVE, or EXPIRED to ARCHIVED. Terminal state."

**Challenge**: The UnifiedPromotion pattern has STOPPED as its terminal state, with transitions ACTIVE->STOP and PAUSED->STOP. There is no ARCHIVE concept. The subscription adds:
- DRAFT -> ARCHIVED (new)
- ACTIVE -> ARCHIVED (new -- similar to STOP)
- EXPIRED -> ARCHIVED (new -- EXPIRED itself is a new state)

The StatusTransitionValidator pattern supports this -- just add entries to the EnumMap. But SCHEDULED and EXPIRED states are also new concepts not present in promotions (promotions use `getEffectiveStatus()` which derives status from dates, not stored as an enum value).

**Recommendation**: Clarify during Phase 4: should SCHEDULED be a stored status or a derived status (like UPCOMING in promotions)? This affects the state machine significantly.

---

### C-8: StatusChangeRequest DTO is Promotion-Specific [LOW]

**Evidence**: `StatusChangeRequest.java` has:
```java
@Pattern(regexp = "PENDING_APPROVAL|REVOKE|RESUME|PAUSE|STOP",
         message = "COMMON.INVALID_PROMOTION_STATUS")
private String promotionStatus;
```

The field name is `promotionStatus` and the regex validates only promotion actions. Subscription actions include ARCHIVE, SUBMIT_FOR_APPROVAL (different from PENDING_APPROVAL for backward compat). The error message says "INVALID_PROMOTION_STATUS".

**Impact**: Either:
(a) Create `SubscriptionStatusChangeRequest` with subscription-specific field name and regex
(b) Generalize `StatusChangeRequest` to use `action` instead of `promotionStatus`

**Recommendation**: Option (a) -- separate DTO avoids backward compatibility risk with existing promotion status change API.

---

### C-9: Enrollment Pause Enforcement Point Unclear [MEDIUM]

**PRD Claim (E4-US1, AC-15.4)**: "Enrollment on PAUSED subscription returns 400 'Subscription is paused, new enrollments not permitted'."

**Challenge**: Where is this enforced?
- In the subscription facade (MongoDB side)? Then the facade must read subscription status before calling Thrift.
- In EMF Thrift (MySQL side)? EMF doesn't know about subscription statuses in MongoDB.

The BA architecture says MongoDB owns lifecycle state. So the v3 enrollment API must:
1. Read subscription status from MongoDB
2. Validate status allows enrollment
3. Call EMF Thrift for actual enrollment

This 2-step process introduces a race condition: subscription could be paused between step 1 and step 3.

**Recommendation**: Accept the race condition as low risk (admin action, not concurrent). Document in risks. Enforce in the facade with a clear pre-check.

---

### C-10: UnifiedPromotion Versioning Pattern Confirmation [LOW]

**PRD Claim (E1-US4)**: "PUT on ACTIVE creates new DRAFT (version N+1, parentId -> ACTIVE)."

**Evidence**: `UnifiedPromotionFacade.determineUpdateStrategyFromList()`:
- DRAFT -> update in place
- ACTIVE/PAUSED -> `createVersionedPromotion()` which clears objectId, sets parentId, increments version, sets status to DRAFT

This exactly matches the subscription PRD claim. [C7 -- verified in source]

**Verdict**: Confirmed. Pattern is well-established and directly replicable.

---

## Confidence Adjustments

| Claim | Original | Adjusted | Reason |
|-------|----------|----------|--------|
| emf-parent: 0 modifications | C7 | C5 | Enrollment path via Thrift not fully traced |
| intouch-api-v3: ~10-15 new files | C6 | C5 | Missing Thrift client class, DTOs, repository expansion |
| "Call EMF Thrift directly" (KD-10) | implicit C7 | C5 | Thrift client doesn't exist yet, must be created |
| thrifts: 0 modifications | C7 | C7 | Confirmed -- IDL already has events |
| api/prototype: 1 modification | C7 | C7 | Confirmed -- ExtendedField.EntityType enum addition |
| cc-stack-crm: 0 modifications | C7 | C7 | Confirmed -- MongoDB-first avoids schema changes |

---

## Questions for User

**Q1 [C3]**: How are `partner_programs` MySQL records created? The enrollment Thrift events assume the program already exists in MySQL. When a subscription transitions to ACTIVE, what creates the MySQL record?
- Option (a): The approval flow calls a separate EMF API to upsert the program config
- Option (b): The first enrollment call creates it lazily
- Option (c): The partner_programs record must be pre-provisioned out-of-band

**Q2 [C4]**: Should SCHEDULED be a stored status or a derived status? Promotions derive UPCOMING from dates but store ACTIVE. Subscriptions could follow either pattern.
- Option (a): Stored status -- simpler, explicit, but requires a scheduled job to transition to ACTIVE
- Option (b): Derived status -- store ACTIVE, derive SCHEDULED at read time from start date. Avoids scheduled job but requires date logic.

## Assumptions Made

**A1 [C5]**: The `EMFService.Iface` connection (port 9199, "emf-thrift-service") is the correct endpoint for partner program Thrift calls from intouch-api-v3, same as `EmfPromotionThriftService` uses.

**A2 [C6]**: The enrollment Thrift events return `EventEvaluationResult` which is sufficient as a response for the v3 enrollment API (no additional data needed from MySQL after enrollment).

---

*Generated by Critic (Phase 2) -- Subscription-CRUD Pipeline*
