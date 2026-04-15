# Phase 2 — Critic Review
> Feature: subscription-program-revamp
> Date: 2026-04-14
> Critic: Phase 2 subagent

## Severity Legend
- 🔴 BLOCKER — must be resolved before architecture starts
- 🟠 HIGH — should be resolved before design; architect must address
- 🟡 MEDIUM — address in QA/SDET or note as known risk
- 🟢 LOW — suggestion, non-blocking

---

## Findings

### [CRIT-01] SCHEDULED state directly contradicts KD-26 (no scheduler)
**Severity**: 🔴 BLOCKER
**Targets**: KD-26, BA Section 4 (Lifecycle States), PRD EP-03 US-04, BA AC-42, PRD line "Nightly activation job transitions Scheduled -> Active"
**Challenge**: KD-26 explicitly resolves A-06 with "NO nightly scheduler / cron job needed. PENDING → ACTIVE is a MANUAL action only." Yet the BA (AC-42) and PRD (EP-03 lifecycle section) both describe a SCHEDULED program state whose entire purpose is time-triggered activation: "Activation job runs at midnight to transition to Active." These two claims are mutually exclusive. The SCHEDULED state is meaningless without a scheduler.
**Risk if unchallenged**: The architect designs a SCHEDULED state into the MongoDB document model and the state machine, then discovers there is no mechanism to ever exit it (no cron, no event trigger). Programs approved with a future start date stay SCHEDULED forever. Members can never enroll. The state machine is broken on day one.
**What BA/PRD says**: BA Goal #4: "Full state machine (Draft, Pending Approval, **Scheduled**, Active, Paused, Expired, Archived)". BA AC-42: "Scheduled state: subscription with future start date. **Activation job runs at midnight** to transition to Active." PRD: "A **nightly activation job** transitions Scheduled -> Active." Session memory KD-26: "NO nightly scheduler / cron job needed."
**What's missing**: A decision on one of three mutually exclusive paths — (a) keep KD-26 and remove SCHEDULED state entirely, (b) keep SCHEDULED state and build a scheduler (overriding KD-26), or (c) keep SCHEDULED as a display-only label and require a manual API call to activate, acknowledging that time-accuracy is not guaranteed. The same contradiction applies to future-dated enrollment: BA AC-45 says "Activation job runs nightly: transitions PENDING enrollments with membershipStartDate <= today to ACTIVE" — again requiring a scheduler KD-26 eliminated.

---

### [CRIT-02] No rollback/compensation for partial publish-on-approve failure
**Severity**: 🔴 BLOCKER
**Targets**: KD-25, BA Section 6.1 (Dual Storage Pattern), BA AC-38
**Challenge**: The publish-on-approve path writes to multiple MySQL tables in sequence: partner_programs → supplementary_membership_cycle_details → partner_program_tier_sync_configuration → supplementary_partner_program_expiry_reminder. MongoDB status is set to ACTIVE either before or after. MySQL has no distributed transaction with MongoDB. If the MySQL write for partner_programs succeeds but supplementary_membership_cycle_details fails (e.g., constraint violation, timeout), the subscription is ACTIVE in MongoDB but has no duration in MySQL. emf-parent will then serve an enrollment for a program with no cycle definition. The BA does not describe any compensation mechanism, error recovery, or idempotency strategy for partial failure.
**Risk if unchallenged**: Production data inconsistency — a subscription is marked ACTIVE and visible to members (via MongoDB), but emf-parent's enrollment engine reads incomplete MySQL data (missing cycle_details or tier_sync_configuration), causing enrollment failures, incorrect expiry calculations, or silent data corruption. The state divergence is invisible to operators.
**What BA/PRD says**: BA Section 6.1: diagram shows "ON APPROVE → MySQL writes (partner_programs, cycle_details, tier_sync_configuration, expiry_reminders)". AC-38: "On APPROVAL, full subscription state is written from MongoDB to MySQL." No mention of failure handling, retry, or compensation.
**What's missing**: A defined atomicity strategy for the multi-table MySQL write on approval. Options include: (a) all MySQL writes in a single DB transaction with MongoDB status update only on full commit, (b) an outbox/saga pattern for eventual consistency, (c) a reconciliation job that detects and repairs partial writes. Without this, the approval API is a silent data corruption vector under any transient failure.

---

### [CRIT-03] M:N benefit linkage requires a new MySQL junction table, contradicting KD-19
**Severity**: 🔴 BLOCKER
**Targets**: KD-31, KD-19, BA Section 6.3, session-memory OQ-04
**Challenge**: KD-31 establishes M:N cardinality between benefits and subscription programs, with a "linkage table unique on (subscription_id, benefit_id) pair only." This linkage table does NOT exist in the current MySQL schema. The existing `benefits` table has a single `program_id` column — a 1:1 relationship with one program. There is no junction table in cc-stack-crm. Yet KD-19 explicitly states "NO Flyway migrations for new columns." A new M:N junction table is not a "new column" — it is a new table — but the intent of KD-19 was to avoid all schema changes. The BA and session memory do not acknowledge this conflict or specify where the junction table lives.
**Risk if unchallenged**: Architecture starts with a data model assumption (M:N via junction table) that conflicts with the no-schema-change constraint. Either (a) the architect creates the table and triggers a Flyway migration nobody planned for, or (b) the benefit linkage is implemented as a MongoDB array only (benefits[] in the subscription document), abandoning the "linkage table" claim in KD-31. Either path is valid but they are architecturally different and the choice must be made before design begins.
**What BA/PRD says**: BA MongoDB document schema: `"benefits": [{ "benefitId": "long", "addedOn": "datetime" }]` — stored in MongoDB as an array. Session memory KD-31: "DB linkage table has NO unique constraint on benefit_id alone." KD-19: "NO Flyway migrations." cc-stack-crm `benefits.sql`: `program_id int(11) NOT NULL` — single program column, no junction table exists.
**What's missing**: A clear statement of where the M:N linkage lives. If benefits[] in MongoDB is the linkage, KD-31's reference to a "DB linkage table" is misleading. If a MySQL junction table is required, KD-19 needs an explicit carve-out and Flyway migration must be planned.

---

### [CRIT-04] PAUSED program state: enforcement mechanism does not exist in emf-parent
**Severity**: 🔴 BLOCKER
**Targets**: KD-30, BA AC-39, BA Lifecycle States table, PRD EP-03
**Challenge**: The BA defines PAUSED as: "Existing enrollments maintain benefits, new enrollments blocked." This requires emf-parent's enrollment API to read the subscription's current lifecycle state and reject link attempts when status is PAUSED. The subscription program's lifecycle state (PAUSED, ARCHIVED, DRAFT, etc.) lives only in MongoDB — by KD-32, it is never written to MySQL. The existing `partner_programs.is_active` (MySQL, boolean) is the only active/inactive signal emf-parent knows about. emf-parent has no MongoDB client; it reads partner_programs via Hibernate JPA (confirmed: PartnerProgram.java entity maps `is_active` column). There is no flag, column, or enum in MySQL to represent PAUSED vs ARCHIVED vs ACTIVE as distinct states. The BA does not describe how emf-parent would know a subscription is PAUSED.
**Risk if unchallenged**: PAUSED state is cosmetically implemented in MongoDB and the UI shows "Paused," but emf-parent continues accepting new enrollments because it only reads `is_active=true` from MySQL. The PAUSED state has zero enforcement. Same problem applies to ARCHIVED: if `is_active` is set to false on archive, PAUSED subscriptions must also set `is_active=false` — at which point the two states are indistinguishable to emf-parent.
**What BA/PRD says**: BA: "Pause action: changes Active to Paused. New enrollments blocked, existing retain benefits." KD-32: "Program lifecycle states (DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, ARCHIVED) live in MongoDB only." KD-30: "New enrollments are blocked after ARCHIVE. Needs Phase 5 verification in emf-parent."
**What's missing**: An explicit mechanism for emf-parent to enforce PAUSED and ARCHIVED enrollment blocking. Either (a) a new MySQL column or status enum must be added (contradicting KD-19), (b) intouch-api-v3 must intercept all enrollment API calls and check MongoDB status before forwarding to emf-parent (introducing a new cross-service dependency not described), or (c) emf-parent must gain MongoDB read capability. None of these are designed.

---

### [CRIT-05] YEARS as cycle_type is unsupported by MySQL schema
**Severity**: 🟠 HIGH
**Targets**: BA AC-09, BA Section 6.2 (MongoDB document duration.cycleType), KD-19
**Challenge**: The BA MongoDB document schema specifies `cycleType: "DAYS | MONTHS | YEARS"` and AC-09 confirms "Duration (required: numeric + unit DAYS/MONTHS/YEARS)." However, the MySQL `supplementary_membership_cycle_details` table has `cycle_type enum('DAYS','MONTHS')` — YEARS is not in the enum. On approval (publish-on-approve), the system will attempt to write cycle_type='YEARS' to a column whose enum does not include it. MySQL will either silently coerce the value to empty string (strict mode off) or raise a Data Truncation error (strict mode on), causing the entire approval to fail. KD-19 says no Flyway migrations.
**Risk if unchallenged**: Any subscription configured with yearly duration can never be approved — the MySQL write fails. Program managers create subscriptions with YEARS duration, submit for approval, approval fails with a cryptic DB error. Annual membership programs (the most commercially significant type) are broken at launch.
**What BA/PRD says**: BA AC-09: "Duration (required: numeric + unit DAYS/MONTHS/YEARS)". BA Section 6.2 MongoDB schema: `"cycleType": "DAYS | MONTHS | YEARS"`. cc-stack-crm `supplementary_membership_cycle_details.sql`: `cycle_type enum('DAYS','MONTHS')` — no YEARS value.
**What's missing**: Either (a) an explicit Flyway migration to add YEARS to the cycle_type enum (overriding KD-19 for this specific case), or (b) a decision to exclude YEARS from the BA scope, or (c) a workaround (e.g., store 12 months instead of 1 year). This is a concrete schema conflict backed by C7 evidence.

---

### [CRIT-06] partner_programs.name has a 50-character hard limit not documented in BA
**Severity**: 🟠 HIGH
**Targets**: BA AC-09, BA Section 6.3, KD-25
**Challenge**: The MySQL `partner_programs` table enforces `name varchar(50)` with a UNIQUE KEY on `(org_id, name)`. The BA does not document this constraint anywhere. The subscription creation API (POST /v3/subscriptions) will accept any name string and save it to MongoDB. On approval, the MySQL write will fail silently or with an error if the name exceeds 50 characters or if a name collision exists at the org level. Program managers will be able to create, save, and submit a subscription for approval that then fails irreversibly at the MySQL publish step.
**Risk if unchallenged**: Approval failures are non-obvious and non-actionable — the error originates in MySQL during the publish step, not during initial creation. A program manager spends days in DRAFT/review only to discover the name is 51 characters. The UNIQUE constraint also means two subscriptions in the same org cannot share the same name — but the BA says duplicate creates a "(Copy)" name, which could conflict if a "(Copy)" already exists.
**What BA/PRD says**: BA AC-09: "Name (required)" with no length constraint mentioned. BA AC-12: "Duplicate action pre-populates form with cloned data, name appended with '(Copy)'". cc-stack-crm `partner_programs.sql`: `name varchar(50)`, `UNIQUE KEY partner_program_name_idx (org_id, name)`.
**What's missing**: Name validation in the API layer that enforces the 50-character limit and uniqueness check against MySQL before saving to MongoDB (or at latest before approval submission), so failures surface early with actionable error messages.

---

### [CRIT-07] KD-28 (Extended Fields for price) references an EntityType that is undefined
**Severity**: 🟠 HIGH
**Targets**: KD-28, BA Section 6.4, BA AC-09
**Challenge**: KD-28 states "reuse the existing EntityType already in EMF" for price as an Extended Field, naming it "Subscription" only at the intouch-api-v3 controller layer. However, the Extended Fields system in api/prototype uses a hardcoded `EntityType` enum (CUSTOMER, REGULAR_TRANSACTION, RETURN_TRANSACTION, LINEITEM, LEAD, COMPANY, CARD, USERGROUP2). None of these map semantically or functionally to a subscription program entity. KD-28 says "no changes to api/prototype" — but it does not name WHICH existing EntityType should be reused, nor does it explain how the Extended Fields storage and retrieval system (which keys data by orgId + entityId + entityType) would correctly scope price fields to subscription programs rather than, say, customers.
**Risk if unchallenged**: The architect must choose an arbitrary existing EntityType (e.g., COMPANY or CARD) to represent subscription programs, creating semantic confusion, potential data collisions across orgs, and incorrect Extended Fields queries returning unrelated entity data. Alternatively, the architect discovers that no existing EntityType is suitable and the decision to avoid api/prototype changes breaks down.
**What BA/PRD says**: BA Section 6.4: "The EntityType enum may need a new value (e.g., PARTNER_PROGRAM or SUBSCRIPTION)." Session memory KD-28: "Reuse existing EMF entity type. Name it 'Subscription' at controller layer only." The BA section 6.4 and KD-28 directly contradict each other on whether a new EntityType is needed.
**What's missing**: The specific existing EntityType to reuse, with evidence that its storage, retrieval, and scoping semantics are compatible with subscription program extended fields. If no compatible type exists, this decision must be revisited.

---

### [CRIT-08] Benefit update propagation semantics are undefined for M:N linkage
**Severity**: 🟠 HIGH
**Targets**: KD-31, BA Section 3 (Benefits), BA Step 3 UI
**Challenge**: With M:N cardinality, a benefit can be linked to multiple subscription programs simultaneously. The BA does not specify what happens when a benefit's configuration changes (e.g., its promotion changes, its max_value changes, it is deactivated). Do all linked subscription programs inherit the change immediately? Or is the linkage a snapshot of the benefit at link time? This has significant commercial implications: if a brand deactivates a benefit, do all subscription programs that reference it silently lose that benefit? If they do not inherit changes, how does a program manager know their subscription's benefits are stale?
**Risk if unchallenged**: In production, a benefit referenced by three subscription programs is updated by a different team. One of the subscriptions is mid-approval cycle (PENDING_APPROVAL). The approved version references the old benefit config, but by the time it goes ACTIVE, the benefit has changed. Members enroll expecting benefit A but receive benefit B. No alert is raised because the subscription's benefit list only stores benefit_ids, not snapshots.
**What BA/PRD says**: BA MongoDB document: `"benefits": [{ "benefitId": "long", "addedOn": "datetime" }]` — ID reference only, no snapshot. BA AC-18–21: benefit linkage described as adding/removing from a list. No mention of what happens when the benefit itself changes.
**What's missing**: An explicit propagation rule: live reference (changes propagate immediately) vs. copy-on-link (snapshot at link time). This must be decided before the data model is finalized.

---

### [CRIT-09] State machine is missing REJECTION handling and PENDING_APPROVAL re-edit semantics
**Severity**: 🟠 HIGH
**Targets**: BA US-03 AC-34, BA Lifecycle States table, PRD EP-02 state machine diagram
**Challenge**: AC-34 says "On REJECT: DRAFT status reverts to DRAFT (not deleted). Comments preserved." The state machine diagram shows PENDING_APPROVAL → Draft (on rejection). Two gaps: (1) After rejection, the PRD state machine shows Draft can transition to ARCHIVED — but can a rejected subscription also be directly archived, or must it re-enter PENDING_APPROVAL first? (2) For edit-of-ACTIVE scenarios (versioned DRAFT with parentId pointing to ACTIVE), what happens on rejection? The ACTIVE version should remain live — that is described. But does the rejected DRAFT get deleted, stay as DRAFT, or become SNAPSHOT? If it stays as DRAFT with parentId still set, can it be re-submitted for approval? Can the original ACTIVE be edited again while the rejected DRAFT is still in DRAFT state? The BA is silent on concurrent draft handling.
**Risk if unchallenged**: In production: an approver rejects a change to an ACTIVE subscription. The maker edits the rejected DRAFT and re-submits. Meanwhile the original ACTIVE is still live. A second approver approves a different DRAFT (from a different edit session). Two DRAFTs with the same parentId now exist, both trying to replace the same ACTIVE. The system has no defined behavior for this race condition.
**What BA/PRD says**: AC-34: "On REJECT: DRAFT status reverts to DRAFT (not deleted). Comments preserved." AC-32: "Edit-of-ACTIVE: creates new DRAFT doc with parentId + version increment." The PRD state machine shows only one DRAFT at a time conceptually but does not enforce it.
**What's missing**: (a) Explicit rule: at most one PENDING_APPROVAL or DRAFT (with a given parentId) allowed at a time? (b) What happens to a rejected versioned DRAFT — is it editable and re-submittable? (c) What happens when two concurrent edits of the same ACTIVE subscription race to approval?

---

### [CRIT-10] Renewal lifecycle is entirely absent from the BA/PRD
**Severity**: 🟠 HIGH
**Targets**: BA US-04 (E3-US4), BA Section 1.2 (supplementary_membership_history has RENEWED action), PRD EP-03
**Challenge**: The BA describes ACTIVE state as "Members can enroll, renew, redeem benefits" in the lifecycle table. The supplementary_membership_history table (confirmed in Codebase Behaviour, C7) has an action value of RENEWED. Yet no user story, acceptance criterion, or API describes renewal behavior: Does renewal happen automatically at membership_end_date? Does the customer manually re-enroll? Is there a grace period? What happens to benefits between expiry and renewal? If the subscription program is PAUSED at renewal time, does the renewal proceed? None of this is specified.
**Risk if unchallenged**: The enrollment API is built for initial link only. When the first batch of subscriptions approach their membership_end_date, there is no renewal path — members fall off unexpectedly. Customer experience is broken and a hotfix is required post-launch.
**What BA/PRD says**: BA lifecycle table: ACTIVE state description mentions "renew" in passing. supplementary_membership_history action enum includes RENEWED (C7 evidence). No user story covers renewal. No API endpoint for renewal is listed in US-05.
**What's missing**: A renewal user story (US-04 addendum or separate story) covering: automatic vs manual renewal, grace period, benefit continuity during the gap, and what state a lapsed but renewable enrollment occupies.

---

### [CRIT-11] Reminder delivery mechanism is unspecified — BA describes storage, not sending
**Severity**: 🟡 MEDIUM
**Targets**: BA US-02 AC-22–23, BA Section 1.2 (supplementary_partner_program_expiry_reminder), KD-24
**Challenge**: The BA and PRD describe creating reminders (days before expiry + channel), storing them in MongoDB, and syncing to MySQL on approval. The `supplementary_partner_program_expiry_reminder.communication_property_values` field exists in MySQL. But neither the BA nor the PRD describes WHO reads this table and sends the actual reminder. Does emf-parent fire it? Does a notification service poll the table? Is there an existing job that processes this table today? The BA treats reminder storage as the complete implementation, ignoring the delivery side entirely.
**Risk if unchallenged**: Reminders are stored correctly but never sent. Program managers configure 7-day and 30-day reminders; they are never delivered. Customer renewal rates are lower than expected and the issue is traced back to non-functional reminder delivery 3 months post-launch.
**What BA/PRD says**: BA AC-22: "Up to 5 reminders with: days before expiry (numeric) + channel (SMS/Email/Push)." KD-24: "Reminders synced to MySQL on approval." No mention of a sending service, trigger mechanism, or existing notification infrastructure.
**What's missing**: Identification of the service responsible for reading supplementary_partner_program_expiry_reminder and dispatching notifications. If this service exists today, reference it. If it does not, it is an undiscovered dependency that must be built or planned.

---

### [CRIT-12] Subscriber count in listing requires cross-store query with undefined performance contract
**Severity**: 🟡 MEDIUM
**Targets**: BA AC-01, PRD US-01 (listing), PRD NFR-01 (< 500ms at p95)
**Challenge**: The listing API (GET /v3/subscriptions) must return subscriber_count per subscription. Subscriber counts are in MySQL (supplementary_partner_program_enrollment). Subscription program metadata is in MongoDB. For a paginated listing of N subscriptions, the system needs N MySQL COUNT queries (or a JOIN) after reading MongoDB data. The BA does not specify whether subscriber counts are live queries or cached/materialized. NFR-01 sets a 500ms p95 target. For an org with 50 active subscriptions each having millions of enrollments, live COUNT(*) queries on every listing page load will not meet this SLA.
**Risk if unchallenged**: The listing API meets NFR-01 in dev/staging (low data) and misses it in production. The first high-volume brand to use the new UI reports 3–5s page loads. A caching or materialization layer must be retrofitted post-launch under time pressure.
**What BA/PRD says**: PRD US-01: "Subscriber count derived from supplementary_partner_program_enrollment." NFR-01: "< 500ms at p95 for 100 subscriptions." PRD Grooming Question GQ-08 (unresolved in the PRD): "Is this a live query against enrollment table, or a cached/materialized count? What is the acceptable staleness?"
**What's missing**: GQ-08 was listed in the PRD but never answered. The architect needs a decision: live query (with index strategy + timeout budget) vs. a materialized/cached count (with acceptable staleness defined). This affects the data model and the API contract.

---

### [CRIT-13] Edit-of-ACTIVE creates a versioned DRAFT but MySQL already has the old config
**Severity**: 🟡 MEDIUM
**Targets**: KD-25, BA AC-30, AC-32, AC-33, BA Section 6.1
**Challenge**: When an ACTIVE subscription is edited (maker-checker), a new DRAFT document is created in MongoDB with parentId pointing to the ACTIVE. The ACTIVE doc stays live — and MySQL has the previously approved config. On approval of the DRAFT: ACTIVE → SNAPSHOT, DRAFT → ACTIVE, and MySQL is updated. But between edit and approval, if a MySQL-reading service (emf-parent) queries `partner_programs`, it reads the OLD config. This is correct and expected. However, if a program manager changes tier linkage during the pending edit (e.g., changes linkedTierId), the ACTIVE MySQL record still references the OLD tier. For a tier-based subscription, emf-parent uses `partner_program_tier_sync_configuration` for enrollment and benefit calculation. Any member who enrolls between edit and approval gets the old tier. Is this acceptable? The BA says yes (ACTIVE stays live), but this is implicit — it is never explicitly acknowledged as a known limitation.
**Risk if unchallenged**: A program manager changes the linked tier from Gold to Platinum and submits for approval. During the approval window (could be days), members continue enrolling into the Gold tier. After approval, existing enrollments are grandfathered on Gold while new ones go to Platinum. This is silently inconsistent. No warning is shown to the program manager at submission time.
**What BA/PRD says**: BA AC-30: "Edit of ACTIVE subscription: creates a pending version. Live version remains active until approved." This is intentional, but the BA never explicitly states the consequence for members enrolling during the approval window.
**What's missing**: An explicit acknowledgment (as an accepted risk or a UI warning) that enrollments during the approval window use the old config. If this is not acceptable for tier-change edits, a partial-lock mechanism (block new enrollments during pending approval of tier-related fields) should be considered.

---

### [CRIT-14] Generic maker-checker "pluggable hooks" interface is under-specified for safety
**Severity**: 🟡 MEDIUM
**Targets**: KD-22, BA US-03 AC-37, PRD EP-02
**Challenge**: The BA defines `MakerCheckerHooks<T>` with `onPreApprove`, `onPostApprove`, `onPreReject`, `onPostReject`, `onPublish`. The onPublish hook is described as where the subscription writes to MySQL. But if onPublish (the MySQL write) is invoked as a hook from within the GenericMakerCheckerService, and it fails, what is the state of the GenericMakerCheckerService? Has the MongoDB status already been set to ACTIVE before the hook is called? If yes, this re-creates CRIT-02 at the framework level. If the hook runs BEFORE the status is set, what happens if the hook succeeds but the subsequent status update fails? The ordering and failure semantics of the hook chain are not defined.
**Risk if unchallenged**: The generic framework is implemented with one hook ordering assumption, the subscription implementation assumes a different ordering, and the system has a race condition or inconsistency window in production that is only discovered under load.
**What BA/PRD says**: PRD EP-02: "On approve: calls entity's onPublish hook (subscription writes to MySQL)." No sequencing specification for hook invocation relative to MongoDB status updates.
**What's missing**: Explicit hook execution sequence with defined failure behavior: (a) What order: pre-hook → status update → post-hook, or pre-hook → post-hook → status update? (b) If a hook throws, does the framework retry, rollback, or leave in a partial state? (c) Is the hook invoked within the same MongoDB session/transaction context as the status update?

---

### [CRIT-15] Duplicate subscription allows name collision with existing ACTIVE subscription
**Severity**: 🟢 LOW
**Targets**: BA AC-12, CRIT-06 related
**Challenge**: The Duplicate action appends "(Copy)" to the original name. If the original subscription is named "Premium Annual" (15 chars), the copy is "Premium Annual (Copy)" (21 chars) — fine. But if the original is "Premium Annual Membership Gold" (30 chars), the copy is "Premium Annual Membership Gold (Copy)" (37 chars). Not fine if the original was renamed to its (Copy) variant already and another copy is made: "Premium Annual Membership Gold (Copy) (Copy)" — which at 44 chars still fits in 50 chars, but a 10-char original would break on the third copy. More critically, if a copy is archived and a new duplicate is created, the "(Copy)" name conflicts with the archived copy. MySQL UNIQUE KEY `(org_id, name)` will reject it.
**Risk if unchallenged**: Duplicate action fails silently at the MySQL unique constraint on approval for common naming patterns. Low risk but predictable failure mode.
**What BA/PRD says**: BA AC-12: "name appended with '(Copy)'." No collision or length handling specified.
**What's missing**: A collision-resolution strategy for duplicate naming (e.g., "(Copy 2)", "(Copy 3)") and a pre-validation that the generated name fits the 50-char constraint before saving.

---

## Summary

| # | Title | Severity | Target |
|---|-------|----------|--------|
| CRIT-01 | SCHEDULED state contradicts KD-26 (no scheduler) | 🔴 BLOCKER | KD-26, BA AC-42, PRD EP-03 |
| CRIT-02 | No rollback/compensation for partial publish-on-approve failure | 🔴 BLOCKER | KD-25, BA AC-38 |
| CRIT-03 | M:N benefit linkage requires a new MySQL junction table, contradicting KD-19 | 🔴 BLOCKER | KD-31, KD-19, BA S6.3 |
| CRIT-04 | PAUSED state enforcement mechanism does not exist in emf-parent | 🔴 BLOCKER | KD-30, KD-32, BA AC-39 |
| CRIT-05 | YEARS cycle_type unsupported by MySQL supplementary_membership_cycle_details enum | 🟠 HIGH | BA AC-09, KD-19 |
| CRIT-06 | partner_programs.name 50-char limit and uniqueness constraint undocumented in BA | 🟠 HIGH | BA AC-09, KD-25 |
| CRIT-07 | KD-28 Extended Fields entity type is unnamed and potentially incompatible | 🟠 HIGH | KD-28, BA S6.4 |
| CRIT-08 | Benefit update propagation semantics undefined for M:N linkage | 🟠 HIGH | KD-31, BA Step 3 |
| CRIT-09 | Rejection handling and concurrent DRAFT semantics unspecified | 🟠 HIGH | BA AC-34, PRD EP-02 |
| CRIT-10 | Renewal lifecycle entirely absent from BA and PRD | 🟠 HIGH | BA US-04, PRD EP-03 |
| CRIT-11 | Reminder delivery mechanism unspecified — BA covers storage only | 🟡 MEDIUM | BA AC-22, KD-24 |
| CRIT-12 | Subscriber count requires cross-store query with undefined performance contract | 🟡 MEDIUM | PRD NFR-01, PRD GQ-08 |
| CRIT-13 | Edit-of-ACTIVE: members enrolling during approval window get old config silently | 🟡 MEDIUM | KD-25, BA AC-30 |
| CRIT-14 | Generic maker-checker hook execution order and failure semantics undefined | 🟡 MEDIUM | KD-22, PRD EP-02 |
| CRIT-15 | Duplicate subscription allows name collision at MySQL uniqueness constraint | 🟢 LOW | BA AC-12 |
