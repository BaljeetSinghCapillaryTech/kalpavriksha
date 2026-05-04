# Tier Management -- Scope Questions for Product & Tech Lead

> **Date:** 2026-04-15
> **Author:** Engineering (Pipeline Run: raidlc/ai_tier)
> **Status:** OPEN -- Awaiting product/tech alignment
> **Context:** These questions surfaced during implementation of Tiers CRUD (Phases 7-12). They fall outside the current pipeline's decision authority and need explicit sign-off before proceeding.

---

## How to Read This Document

Each question is categorized by:
- **Area**: Which part of the system it affects
- **Severity**: BLOCKER (cannot proceed), HIGH (affects architecture), MEDIUM (affects scope), LOW (nice-to-have clarity)
- **Who Decides**: Product Team, Tech Lead, or Both
- **Current Assumption**: What we've assumed in the absence of an answer (so work isn't blocked unnecessarily)

---

## Category A: Tier Lifecycle & State Management

### Q1. Deletion is DRAFT-only -- Confirm?

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Who Decides** | Product + Tech Lead |
| **Area** | Tier Lifecycle |

**Context:** Deleting an ACTIVE tier corrupts customer data -- members in that tier lose their slab assignment, CSV strategy indices break for all higher tiers, and downstream systems (PEB, points engine) throw `IndexOutOfBoundsException` on ~50 call sites ([non-sequential-tier-impact-analysis.md](non-sequential-tier-impact-analysis.md)).

**Question:** Can we confirm that tier deletion is ONLY allowed in DRAFT state? For ACTIVE tiers, the only option should be STOP (soft-delete), which:
- Prevents new members from entering
- Keeps existing members until they naturally upgrade/downgrade
- Preserves historical data and CSV index integrity

**Current Assumption:** Yes -- DRAFT = hard delete, ACTIVE = soft-stop only.

**Follow-up:** What is the UX for STOP? Is there a confirmation dialog explaining the impact? Should we show member count before allowing stop?

---

### Q2. Multiple Drafts -- What Happens When One Goes Live?

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Who Decides** | Product + Tech Lead |
| **Area** | Tier Lifecycle, Maker-Checker |

**Context:** Suppose a program has tiers SILVER, GOLD, PLATINUM. GOLD and PLATINUM are both in DRAFT state.

**Question:** If PLATINUM is submitted and approved (becomes ACTIVE), what happens to the GOLD draft?

**Options:**
| Option | Behavior | Risk |
|--------|----------|------|
| A. Auto-invalidate | GOLD draft is auto-rejected with a system comment ("Invalidated: PLATINUM activation changed tier structure") | Least risk, but user loses draft work |
| B. Keep as-is | GOLD draft remains DRAFT, user can still submit it later | Risk: GOLD draft may reference stale serial numbers or outdated tier ordering |
| C. Force sequential activation | Enforce that lower tiers must go live before higher tiers (GOLD before PLATINUM) | Most restrictive, but safest for CSV index integrity |

**Current Assumption (from GQ-3):** One DRAFT per ACTIVE parent. But this question is about *brand new* tiers (no ACTIVE parent), where multiple can coexist in DRAFT.

**What we need:** An explicit rule for this scenario.

---

### Q3. "Scheduled" vs "Pending Approval" -- No Future Activation Date

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Who Decides** | Product |
| **Area** | UI / KPI Cards |

**Context:** The UI mockup shows `| Total Tiers: 4 | Active: 4 | Scheduled: 0 | Total Members: 2,135 |`. Unlike promotions, tiers have no `goLiveDate` / future activation date concept.

**Resolution (already applied):** Replaced "Scheduled" with "Pending Approval" count (decision C-5 in [blocker-decisions.md](blocker-decisions.md)).

**Question for Product:**
1. Is "Pending Approval" the right replacement, or do we want a different metric?
2. Do we need a `tierScheduler` for future-dated tier activation? (If yes, this is a separate epic -- not in current scope.)
3. If a `tierScheduler` is needed later, should we reserve the field in the MongoDB schema now (e.g., `scheduledGoLiveDate: null`)?

---

## Category B: Data & Statistics

### Q4. New `tier_stats` Table -- Temporal Granularity

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Who Decides** | Tech Lead |
| **Area** | Database Design, Reporting |

**Context:** We need member count per tier for the listing page KPI cards. Current approach is a cron job that runs `GROUP BY current_slab_id` on `customer_enrollment` and caches counts in MongoDB.

**Question:** If we have 10,000 customers at 11:00 AM and 10,100 at 1:30 PM, does showing the difference make sense? Specifically:

1. **Do we need a `tier_stats` table at all?** The current design caches counts directly in the MongoDB tier document (`memberStats.memberCount`, `memberStats.lastRefreshed`). A separate table adds complexity.
2. **If yes, what granularity?** Snapshot every N minutes? Daily rollup? Hourly?
3. **Is "last refreshed at X" timestamp sufficient?** (Current assumption: yes -- show count + "as of 12:05 PM")
4. **Do we need trend data?** (e.g., "+100 members in last 24h") -- this would require historical storage.

**Current Assumption:** No separate table. Cached count in MongoDB with "last refreshed" timestamp, updated every 5-15 minutes by cron. No trend data in v1.

---

## Category C: UI / UX Decisions

### Q5. "Save as Draft" on Every Page of the Wizard?

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Who Decides** | Product |
| **Area** | UI Flow |

**Context:** The tier creation wizard has 3 steps: General, Eligibility, Validity & Renewal. The question is whether every step should have a "Save as Draft" button.

**Options:**
| Option | Behavior | UX Impact |
|--------|----------|-----------|
| A. Every page | User can save incomplete tier at any step | More flexibility, but creates potentially invalid drafts (e.g., tier with name but no eligibility criteria) |
| B. Last page only | Draft is saved only after completing all steps | Cleaner data, but user loses work if they navigate away mid-wizard |
| C. Auto-save + explicit save | Auto-save to localStorage/session on every step, explicit "Save as Draft" only on last page | Best of both -- no data loss, no invalid drafts in DB |

**Question:** Which option does the product team prefer? If Option A, do we need validation rules for what constitutes a "valid draft" vs just "any partial data"?

---

### Q6. Tier Reordering is Not Allowed -- Confirm?

| Field | Value |
|-------|-------|
| **Severity** | BLOCKER (if someone asks for it) |
| **Who Decides** | Tech Lead + Product |
| **Area** | Tier Settings, Data Integrity |

**Context:** The entire points engine relies on `serialNumber` as an array index into CSV strategy strings. ~50 call sites across 15 production files use `serialNumber - 1` or `serialNumber - 2` to index into strategy arrays. Reordering tiers would make serial numbers non-contiguous, causing `IndexOutOfBoundsException` across every core loyalty flow.

Full impact analysis: [non-sequential-tier-impact-analysis.md](non-sequential-tier-impact-analysis.md)

**Decision:** Tier reordering MUST NOT be offered in the UI. Serial numbers are:
- Auto-assigned on creation (max existing + 1)
- Immutable after assignment
- Never reused after deletion (gap is permanent)

**Question:** Can we get explicit sign-off that the "Tier Settings" page will NOT include a drag-and-drop reorder feature? This is a hard technical constraint, not a scope decision.

---

### Q7. Program Creation -- Where Does It Live?

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Who Decides** | Product |
| **Area** | Navigation / Information Architecture |

**Context:** If the first page (landing) shows Tiers, Subscriptions, and Benefits as tabs/sections, the question is where "Program Creation" fits.

**Options:**
| Option | Description |
|--------|-------------|
| A. Separate top-level page | Program creation is its own page; tiers/subscriptions/benefits are sub-pages within a program |
| B. Inline on landing page | "Create Program" is a CTA on the landing page, creating a program is a prerequisite before adding tiers |
| C. Wizard step 0 | Before the tier wizard, user selects or creates a program |
| D. Already exists | Program creation already exists elsewhere in the admin UI; tier page just selects an existing program |

**Question:** Is program creation in scope for this epic, or does it already exist? If it exists, do we just need a program selector dropdown on the tier listing page?

---

## Category D: Business Rules & Criteria

### Q8. Supported Criteria Types -- Only Three?

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Who Decides** | Product + Tech Lead |
| **Area** | Eligibility, Renewal, Downgrade |

**Context:** The current codebase (`CriteriaType` enum in emf-parent) supports these criteria types for tier eligibility, renewal, and downgrade:

| # | Criteria Type | Description |
|---|---------------|-------------|
| 1 | `CURRENT_POINTS` | Customer's current available (unspent) points balance |
| 2 | `CUMULATIVE_POINTS` | Total points ever earned (lifetime) |
| 3 | `CUMULATIVE_PURCHASES` | Total purchase amount (lifetime spending) |

**Question:**
1. Are these the ONLY three criteria types we expose in the new UI? (The engine also has `LIFETIME_POINTS`, `LIFETIME_PURCHASES`, `TRACKER_VALUE` -- are these synonyms or distinct?)
2. The BRD mentions "spending" in eligibility criteria -- confirm this maps to `CUMULATIVE_PURCHASES`?
3. Is `TRACKER_VALUE` (custom tracker-based metrics) needed in v1, or deferred?
4. **Key constraint:** A program uses ONE criteria type for ALL its tiers. The UI should enforce this (dropdown disabled after first tier is created). Confirm?

---

### Q9. Group Conditions in Upgrade Eligibility -- What Are They?

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Who Decides** | Product |
| **Area** | Eligibility Criteria |

**Context:** The UI mockup references "Group Conditions" in the qualifying conditions for tier upgrade. Our current model supports:

```
activities: [
  { type: "Spending", operator: "GTE", value: 550, unit: "RM" },
  { type: "Transactions", operator: "GTE", value: 2, unit: "count" }
]
activityRelation: "AND" | "OR"
```

This is a flat list with a single AND/OR operator connecting all conditions.

**Question:**
1. Does "Group Conditions" mean **nested groups** with mixed AND/OR? Example:
   ```
   (Spending >= 550 AND Transactions >= 2) OR (Points >= 1000)
   ```
   This would require a tree structure, not a flat list.
2. Or does it mean **grouping by activity type**? (e.g., all spending conditions in one group, all point conditions in another)
3. What is the maximum nesting depth? (1 level = current flat model, 2+ levels = significant schema change)

**Impact:** If nested groups are needed, the MongoDB schema, validation logic, and Thrift sync all need redesign. This is a scope-expanding decision.

**Current Assumption:** Flat list with single AND/OR relation (no nesting). If groups are needed, it's a separate epic.

---

### Q10. What Does "Downgrade Schedule" Mean?

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Who Decides** | Product |
| **Area** | Downgrade Config |

**Context:** We have two enum values defined:

| Value | Behavior |
|-------|----------|
| `MONTH_END` | Evaluate downgrade eligibility at end of month (batch job) |
| `DAILY` | Evaluate downgrade eligibility every day (continuous) |

**Questions for Product:**
1. Is this correct? Does "downgrade schedule" simply mean "how often do we check if a member should be downgraded"?
2. Is there a third option needed? (e.g., `ON_RENEWAL_DATE` -- check only when the member's tier validity period expires)
3. What is the relationship between `downgradeSchedule` and `membershipDuration`? Example: if membership duration is 12 months and schedule is MONTH_END, does the system only check at the 12th month-end, or every month-end throughout the 12 months?
4. Does the schedule affect when the downgrade *happens* or when it's *evaluated*? (Could a member be flagged for downgrade in January but only actually moved in March?)

---

### Q11. No Nudges/Communications in Tier Creation -- Confirm?

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Who Decides** | Product |
| **Area** | Notifications |

**Context:** The BRD mentions nudges for upgrade, renewal reminders, and expiry warnings. However, the current system configures communications through a separate "Activities" module, not through tier creation.

**Current State:**
- MongoDB schema has `nudges` text field (free-text description) and `notificationConfig` object (engine config with SMS/email/WeChat/push templates)
- New tiers created via UI will have empty `notificationConfig`
- Notification setup happens separately in the Activities module

**Question:**
1. Confirm: The tier creation wizard will NOT have a "Configure Notifications" step?
2. Should the UI show a hint/link saying "Configure notifications for this tier in Activities"?
3. For the `nudges` free-text field in the schema -- is this for internal notes ("send upgrade email") or does it serve a functional purpose?

---

## Category E: Architecture & Technical

### Q12. Base Tier (serialNumber=1) -- Special Rules?

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Who Decides** | Tech Lead |
| **Area** | Business Rules |

**Context:** The base tier (lowest, serialNumber=1) has special behavior in the engine:
- No upgrade threshold (everyone starts here)
- Cannot be downgraded TO below it
- No eligibility criteria (automatic enrollment)
- CSV index for upgrade strategy starts at serialNumber=2 (the first upgradeable tier)

**Questions:**
1. Can the base tier be edited? (Name, description, benefits -- yes. Eligibility criteria -- not applicable.)
2. Can the base tier be stopped/deleted? (This would leave members with no tier.)
3. Should the UI enforce that at least one tier (base) always exists per program?
4. Is the base tier always created automatically when a program is created, or does the user create it manually?

---

### Q13. Rollback Strategy -- What If Thrift Sync Fails?

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Who Decides** | Tech Lead |
| **Area** | Data Consistency |

**Context:** The approval flow is: MongoDB status -> ACTIVE, then Thrift call syncs to MySQL. If the Thrift call fails:
- MongoDB says ACTIVE
- MySQL doesn't have the tier
- System is in inconsistent state

**Options:**
| Option | Behavior |
|--------|----------|
| A. Compensating transaction | On Thrift failure, revert MongoDB status back to PENDING_APPROVAL |
| B. Retry queue | Mark as SYNC_PENDING, background job retries |
| C. Manual intervention | Alert admin, provide "Retry Sync" button |

**Current Assumption (from ADR-07):** Single atomic Thrift call. But "atomic" only applies within the Thrift call itself -- the MongoDB + Thrift combination is NOT atomic.

**Question:** Which failure strategy does the tech lead prefer?

---

### Q14. Max Tier Count Per Program?

| Field | Value |
|-------|-------|
| **Severity** | LOW |
| **Who Decides** | Product + Tech Lead |
| **Area** | Validation |

**Context:** Decision GQ-1 caps tiers at 50 per program (no pagination needed). Typical programs have 3-7 tiers.

**Questions:**
1. Is 50 the right cap, or should it be lower (e.g., 20)?
2. Should the cap be configurable per org, or hardcoded?
3. Does the cap include STOPPED tiers, or only ACTIVE + DRAFT?

---

### Q15. Existing Programs -- Bootstrap or Ignore?

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Who Decides** | Product + Tech Lead |
| **Area** | Migration Strategy |

**Context:** Decision GQ-2 says "New system for new programs only. Old programs keep current system." But:

1. When an admin opens the tier listing page for an **existing** program, what do they see? Empty state? Error? A read-only view pulled from MySQL?
2. If existing programs are invisible to the new UI, how does the admin manage them? (Continue using the old system forever?)
3. Is there a future migration path planned? If yes, should we design the schema to accommodate it (e.g., `metadata.migratedFromLegacy: true`)?

**Current Assumption:** Existing programs are managed through the old UI. New tier CRUD UI only shows programs created after this feature goes live. No bootstrap sync.

---

## Summary Matrix

| # | Question | Severity | Who Decides | Current Assumption |
|---|----------|----------|-------------|-------------------|
| Q1 | DRAFT-only deletion | HIGH | Product + Tech | Yes, ACTIVE = soft-stop only |
| Q2 | Multiple drafts, one goes live | HIGH | Product + Tech | Undefined -- needs rule |
| Q3 | "Scheduled" KPI replacement | MEDIUM | Product | Replaced with "Pending Approval" |
| Q4 | `tier_stats` table granularity | MEDIUM | Tech Lead | No separate table, cached in MongoDB |
| Q5 | Save as Draft on every page | LOW | Product | Last page only (Option B) |
| Q6 | Tier reordering blocked | BLOCKER | Tech + Product | Confirmed blocked (hard constraint) |
| Q7 | Program creation location | MEDIUM | Product | Assumed to exist elsewhere |
| Q8 | Only 3 criteria types in v1 | MEDIUM | Product + Tech | Yes, 3 only. TRACKER_VALUE deferred |
| Q9 | Group conditions = nested AND/OR? | HIGH | Product | Flat list only. Nesting = separate epic |
| Q10 | Downgrade schedule meaning | MEDIUM | Product | Frequency of downgrade evaluation |
| Q11 | No nudges in tier creation | LOW | Product | Correct, configured via Activities |
| Q12 | Base tier special rules | HIGH | Tech Lead | Cannot be deleted, auto-created |
| Q13 | Thrift sync failure rollback | HIGH | Tech Lead | Compensating transaction (Option A) |
| Q14 | Max tier count | LOW | Product + Tech | 50, hardcoded, excludes STOPPED |
| Q15 | Existing program visibility | MEDIUM | Product + Tech | Invisible to new UI |

---

## Action Items

- [ ] Product team reviews Q1, Q2, Q3, Q5, Q7, Q8, Q9, Q10, Q11, Q14
- [ ] Tech lead reviews Q2, Q4, Q6, Q12, Q13, Q14, Q15
- [ ] Schedule 30-min alignment call to resolve HIGH items (Q1, Q2, Q9, Q12, Q13)
- [ ] Update [session-memory.md](session-memory.md) and [pipeline-state.json](pipeline-state.json) with decisions

---

> **Note:** Questions Q1-Q11 originated from the implementation team. Questions Q12-Q15 were added based on gaps identified during codebase analysis and pipeline execution (Phases 1-12).
