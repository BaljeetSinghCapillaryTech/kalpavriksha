# Blocker Decisions -- Subscription-CRUD

> Phase: 4 (Blocker Resolution)
> Date: 2026-04-09
> Evidence trail for all decisions that block or constrain downstream phases

---

## Decision Registry

### BD-01: MySQL Creation Path via createOrUpdatePartnerProgram

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-10 (revised) |
| Classification | BLOCKER |
| Source | GAP-1, C-1 |
| Question | How does the subscription get into MySQL partner_programs table? |
| Decision | Call `PointsEngineRuleService.createOrUpdatePartnerProgram()` via existing `PointsEngineRulesThriftService` on ACTIVE transition |
| Evidence | pointsengine_rules.thrift:1269 (method signature), PointsEngineRulesThriftService.java (uses correct interface), PartnerProgramFixture.java (shows invocation pattern) |
| Confidence | C7 (verified from primary source) |
| Impact | Defines the write-back mechanism from MongoDB to MySQL. Only `createOrUpdatePartnerProgram` needed -- no enrollment Thrift wrapping. |

### BD-02: SCHEDULED as Derived Status

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-11 |
| Classification | BLOCKER |
| Source | C-7, state machine design |
| Question | Is SCHEDULED a persisted status or derived at read time? |
| Decision | Derived. Store ACTIVE in MongoDB. If startDate > now, return SCHEDULED to callers. |
| Evidence | UnifiedPromotion UPCOMING pattern in getEffectiveStatus() |
| Confidence | C6 (pattern established, but subscription may have nuances) |
| Impact | State machine has 6 stored states + 1 derived. No scheduled job infrastructure. Simplifies implementation. |

### BD-03: Benefits Shared Across Entities

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-12 |
| Classification | SCOPE |
| Source | OQ-04, KD-08 |
| Question | Can the same benefit ID be linked to multiple subscriptions? |
| Decision | Yes. No uniqueness constraint. Benefits are a cross-cutting shared resource. |
| Evidence | User explicit decision. Aligns with KD-08 (benefits as first-class entity). |
| Confidence | C7 (direct user instruction) |
| Impact | No UNIQUE index on benefitIds. No cross-subscription validation. Simplifies linking logic. |

### BD-04: Maker-Checker Auth at UI Layer

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-13 |
| Classification | SCOPE |
| Source | OQ-03, C-9 |
| Question | Does backend enforce approver authorization? |
| Decision | No. UI-layer handles roles/permissions. Backend trusts authenticated callers. |
| Evidence | UnifiedPromotion does the same -- no permission check in UnifiedPromotionFacade.changePromotionStatus() |
| Confidence | C7 (consistent with existing pattern + user confirmation) |
| Impact | No PermissionChecker in SubscriptionFacade. No SUBSCRIPTION_APPROVE authority. Simplifies auth model. |

### BD-05: PENDING Enrollments Honored on PAUSE

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-14 |
| Classification | FEASIBILITY |
| Source | Enrollment edge case analysis |
| Question | What happens to PENDING enrollments when subscription is PAUSED? |
| Decision | PENDING enrollments remain. Only new enrollment attempts blocked. |
| Evidence | User explicit decision. PAUSE affects future enrollment flow, not existing records. |
| Confidence | C7 (direct user instruction) |
| Impact | PAUSE transition only updates MongoDB status. No enrollment record modification. |

### BD-06: EMF Owns Enrollment Constraints

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-15 |
| Classification | FEASIBILITY |
| Source | BRD constraint analysis |
| Question | Does v3 pre-check restrictToOneActivePerMember? |
| Decision | No. Delegate to EMF Thrift which owns enrollment logic and data. |
| Evidence | EMF has ENABLE_PARTNER_PROGRAM_LINKING org config. PartnerProgramLinkingHelper validates. |
| Confidence | C6 (verified EMF has the check, but edge cases possible) |
| Impact | v3 API is thin wrapper for activation. No enrollment pre-validation. |

### BD-07: Epic 4 Removed from Scope -- CRITICAL

| Attribute | Value |
|-----------|-------|
| Decision ID | KD-16 |
| Classification | SCOPE (critical scope reduction) |
| Source | User Q5 response |
| Question | Should v3 wrap enrollment Thrift calls? |
| Decision | **NO.** v3 only calls `createOrUpdatePartnerProgram`. Enrollment stays on existing v2 paths. E4-US1 through E4-US4 are OUT OF SCOPE. |
| Evidence | User explicit instruction: "Do not modify or wrap the existing EMF Thrift methods for enrollment" |
| Confidence | C7 (direct user instruction, non-negotiable) |
| Impact | **Removes Epic 4 (4 user stories, 9 acceptance criteria) from PRD.** Significant reduction: 16 -> 12 user stories, 54 -> 45 acceptance criteria. Enrollment NFR removed. No EmfPromotionThriftService wrapper methods needed. |

---

## Scope Impact Summary

| Metric | Before Phase 4 | After Phase 4 | Delta |
|--------|----------------|---------------|-------|
| Epics in scope | 5 | 4 | -1 (E4 removed) |
| User stories | 16 | 12 | -4 |
| Acceptance criteria | 54 | ~45 | -9 |
| Thrift methods to wrap | 4 (create + link + delink + update) | 1 (createOrUpdatePartnerProgram) | -3 |
| External repos modified | 2+ | 1 (intouch-api-v3) + 0 enrollment changes | Reduced |

---

*All blockers resolved. PRD updated to reflect scope changes.*
