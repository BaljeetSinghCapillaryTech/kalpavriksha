# Grooming Questions -- Subscription-CRUD

> Phase: 4 (Blocker Resolution)
> Date: 2026-04-09
> Sources: 00-ba.md (open questions), 00-prd.md, contradictions.md (C-1 through C-10), gap-analysis-brd.md (GAP-1 through GAP-6)

---

## Summary

| Classification | Count | Resolved |
|---------------|-------|----------|
| BLOCKER | 2 | 2 |
| SCOPE | 3 | 3 |
| FEASIBILITY | 2 | 2 |
| PRIORITY | 2 | 2 |
| **Total** | **9** | **9** |

---

## BLOCKER Questions

### BQ-1: Partner Program MySQL Creation Path (GAP-1)

**Source**: gap-analysis-brd.md GAP-1 (BLOCKER), contradictions.md C-1 (HIGH)
**Why it matters**: Without knowing HOW to create the MySQL partner_programs record on ACTIVE transition, the architecture cannot be designed.

**Resolution**: RESOLVED in Phase 2 (user clarification before Phase 4 formal start).
- `createOrUpdatePartnerProgram(PartnerProgramInfo, programId, orgId, lastModifiedBy, lastModifiedOn, serverReqId)` on `PointsEngineRuleService.Iface`
- Existing `PointsEngineRulesThriftService` in intouch-api-v3 uses this interface -- needs wrapper method added
- Enrollment is a SEPARATE concern via `EMFService.Iface` methods
- See KD-10 (revised) and session-memory codebase behaviours for full Thrift interface mapping

### BQ-2: SCHEDULED -- Stored Status or Derived from Dates? (C-7, OQ-related)

**Source**: contradictions.md C-7, 00-ba.md state machine analysis
**Why it matters**: Determines whether we need a scheduled job to transition SCHEDULED -> ACTIVE, or if the state machine has 7 stored states vs 6+1.

**Options presented**:
- (a) Stored: SCHEDULED as a persisted MongoDB status. Requires scheduled job to flip to ACTIVE when startDate arrives.
- (b) Derived: Store ACTIVE in MongoDB. At read time, if startDate > now, return SCHEDULED to callers. No scheduled job needed.

**Resolution**: **(b) Derived** -- follows UnifiedPromotion UPCOMING pattern (getEffectiveStatus()). State machine has 6 stored states (DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, EXPIRED, ARCHIVED) + 1 derived (SCHEDULED).
**Decision**: KD-11

---

## SCOPE Questions

### SQ-1: Can Same Benefit ID Be Linked to Multiple Subscriptions?

**Source**: 00-ba.md OQ-04, KD-08 implications
**Why it matters**: Affects validation logic in benefit linking endpoints and data model constraints.

**Resolution**: **Yes** -- benefits are shared, reusable entities. Same ID can appear in multiple subscriptions AND other entity types (tiers, etc.). No uniqueness constraint. No validation in this run (dummy objects).
**Decision**: KD-12

### SQ-2: Maker-Checker Approver Authorization

**Source**: 00-ba.md OQ-03, contradictions.md C-9
**Why it matters**: Determines whether backend needs permission enforcement or just exposes transition APIs.

**Resolution**: **UI-layer only** -- backend does NOT enforce approver roles/permissions. Status transition APIs are open to any authenticated caller. No SUBSCRIPTION_APPROVE permission check.
**Decision**: KD-13

### SQ-3: Enrollment Thrift Wrapping Scope -- CRITICAL SCOPE CHANGE

**Source**: 00-prd.md Epic 4 (E4-US1 through E4-US4), 00-ba.md enrollment analysis
**Why it matters**: Determines whether v3 API surface includes enrollment operations or only subscription config management.

**Resolution**: **Do NOT wrap enrollment Thrift calls.** v3 only calls `createOrUpdatePartnerProgram` on ACTIVE transition. Enrollment (link/delink/renew) stays on existing v2 paths. **This REMOVES Epic 4 (Enrollment Operations) from scope entirely.** E4-US1 through E4-US4 are OUT OF SCOPE.
**Decision**: KD-16

---

## FEASIBILITY Questions

### FQ-1: PENDING Enrollments When Subscription PAUSED

**Source**: 00-ba.md OQ-07 (implicit), contradictions.md C-9 enrollment edge cases
**Why it matters**: Affects whether PAUSE transition needs to interact with enrollment records.

**Resolution**: **Honor existing** -- PENDING enrollments remain when subscription PAUSED. Only new enrollment attempts blocked. No enrollment record modification on PAUSE.
**Decision**: KD-14

### FQ-2: restrictToOneActivePerMember Enforcement

**Source**: 00-ba.md BRD constraint reference
**Why it matters**: Determines whether v3 API needs to pre-check member enrollment limits before calling Thrift.

**Resolution**: **Delegate to EMF Thrift** -- v3 does NOT pre-check. EMF owns enrollment logic, has ENABLE_PARTNER_PROGRAM_LINKING config. Avoid duplicating validation.
**Decision**: KD-15

---

## PRIORITY / ARCHITECTURE Questions

### PQ-1: RequestManagementController Return Type (GAP-4, C-6)

**Source**: gap-analysis-brd.md GAP-4, contradictions.md C-6
**Why it matters**: Current controller returns `ResponseEntity<ResponseWrapper<UnifiedPromotion>>` -- hardcoded. Subscription returns UnifiedSubscription.

**Resolution**: Create **separate SubscriptionController** with own status change handler. Do not modify existing RequestManagementController.
**Decision**: D-16 (approach-log)

### PQ-2: StatusChangeRequest DTO (GAP-3, C-8)

**Source**: gap-analysis-brd.md GAP-3, contradictions.md C-8
**Why it matters**: Current DTO has field name "promotionStatus" with promotion-specific regex.

**Resolution**: Create **SubscriptionStatusChangeRequest** with field name "action" instead of "promotionStatus".
**Decision**: D-17 (approach-log)

---

## Questions Resolved as N/A (Due to Scope Change)

| # | Original Question | Why N/A |
|---|------------------|---------|
| GAP-6 | Thrift PartnerProgramLinkingEventData requires storeUnitID | Enrollment Thrift calls out of scope (KD-16) |
| GAP-2 | PartnerProgramUpdateEvent is tier-specific only | Enrollment update out of scope (KD-16) |

---

*All 9 questions resolved. No open blockers remain for Phase 5+.*
