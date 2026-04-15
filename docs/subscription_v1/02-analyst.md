# Phase 2 — Analyst: BA Codebase Claim Verification
> Feature: subscription-program-revamp
> Date: 2026-04-14

---

## Verification Results

### V-01: EmfMongoConfig supports new collection without config changes
**BA Claim (A-03)**: "MongoDB connection and EmfMongoConfig in intouch-api-v3 can support a new collection" — new `subscription_programs` collection can be added without config changes.
**Evidence**:
- `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/config/EmfMongoConfig.java` lines 27–33: `@EnableMongoRepositories` uses `includeFilters` with `FilterType.ASSIGNABLE_TYPE` specifying only `UnifiedPromotionRepository.class`. This means **only** `UnifiedPromotionRepository` is currently routed to `emfMongoTemplate`.
- A new `SubscriptionProgramRepository` will NOT be auto-picked up by `EmfMongoConfig`. The `includeFilters` list must be updated to include the new repository class, OR the config must be refactored to use a base package scan with an excludeFilter approach.
- `MongoConfig.java` (primary config) also uses explicit `includeFilters` for `ProfileDao` and `TargetAudienceStatusLogDao` only.
**Verdict**: ⚠️ PARTIAL
**Confidence**: C7
**Notes**: The BA claim is functionally true — the MongoDB infrastructure (connection factory, `emfMongoTemplate` bean) is reusable. However the claim that no config changes are needed is **incorrect**. `EmfMongoConfig` must be updated to include the new `SubscriptionProgramRepository` in its `includeFilters` or the config pattern must be refactored. This is a small but mandatory code change.

---

### V-02: UnifiedPromotion collection declaration pattern (@Document annotation-based)
**BA Claim (CB in session-memory)**: "UnifiedPromotion is a `@Document(collection="unified_promotions")` MongoDB model — annotation-based collection declaration."
**Evidence**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/unified/promotion/UnifiedPromotion.java` line 40: `@Document(collection = "unified_promotions")` confirmed.
**Verdict**: ✅ CONFIRMED
**Confidence**: C7
**Notes**: New `SubscriptionProgram` document can follow the identical `@Document(collection = "subscription_programs")` pattern. No manual collection registration needed beyond the EmfMongoConfig update identified in V-01.

---

### V-03: Thrift PartnerProgramInfo struct fields
**BA Claim (KD-07, KD-27)**: `PartnerProgramInfo` Thrift struct handles partner program CRUD. New metadata stays in MongoDB, Thrift writes only existing MySQL-mapped fields.
**Evidence**: `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift` lines 402–417. Actual `PartnerProgramInfo` fields:
1. `partnerProgramId` (i32, required)
2. `partnerProgramName` (string, required)
3. `description` (string, required)
4. `isTierBased` (bool, required)
5. `partnerProgramTiers` (list<PartnerProgramTier>, optional)
6. `programToPartnerProgramPointsRatio` (double, required)
7. `partnerProgramUniqueIdentifier` (string, optional)
8. `partnerProgramType` (PartnerProgramType, required — EXTERNAL|SUPPLEMENTARY)
9. `partnerProgramMembershipCycle` (PartnerProgramMembershipCycle, optional)
10. `isSyncWithLoyaltyTierOnDowngrade` (bool, required)
11. `loyaltySyncTiers` (map<string,string>, optional)
12. `updatedViaNewUI` (bool, optional)
13. `expiryDate` (i64, optional)
14. `backupProgramId` (i32, optional)

**Critical**: `PartnerProgramCycleType` enum in Thrift is `DAYS | MONTHS` only — **no YEARS value exists**.

**Verdict**: ✅ CONFIRMED (struct verified) with one sub-finding (see Notes)
**Confidence**: C7
**Notes**: KD-27 is confirmed — Thrift already has `backupProgramId` and `expiryDate` fields, so the MySQL-relevant fields are coverable. However, the BA's MongoDB document schema specifies `YEARS` as a valid `cycleType` (Section 6.2, `duration.cycleType: "DAYS | MONTHS | YEARS"`), but **both the Thrift IDL and MySQL `supplementary_membership_cycle_details` table only support DAYS and MONTHS**. `YEARS` is not supported downstream. This is a **data contract inconsistency**.

---

### V-04: Thrift createOrUpdatePartnerProgram — MySQL-only write path (no MongoDB reads)
**BA Claim (KD-27)**: "Thrift endpoint reads from MySQL only, not MongoDB. New metadata lives only in MongoDB."
**Evidence**:
- `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram` (line 252–281) calls `m_pointsEngineRuleEditor.getPartnerProgram(...)` (fetches from MySQL via JPA DAO), then `m_pointsEngineRuleEditor.createOrUpdatePartnerProgram(...)`.
- `PointsEngineRuleService.createOrUpdateSupplementaryPartnerProgram` (lines 1750–1766) calls: `saveSupplementaryPartnerProgramEntity` → JPA save to `partner_programs`; `saveSupplementaryPartnerProgramCycle` → JPA save to `supplementary_membership_cycle_details`; `saveSupplementaryPartnerProgramTierSyncConfig` → JPA save to `partner_program_tier_sync_configuration`.
- The impl class does have MongoDB dependencies (`MongoPointsEngineRuleService`, `OrgConfigService`) but these are used for other methods (promotions, org config), not `createOrUpdatePartnerProgram`.
- No MongoDB read/write in the partner program create/update path.
**Verdict**: ✅ CONFIRMED
**Confidence**: C7
**Notes**: KD-27 is fully supported. The Thrift write path is pure MySQL (JPA). MongoDB dependencies in the same class are for unrelated features.

---

### V-05: MySQL write tables for createOrUpdatePartnerProgram (publish-on-approve scope)
**BA Claim (KD-25, AC-38)**: "On APPROVAL, full subscription state is written to MySQL: `partner_programs`, `supplementary_membership_cycle_details`, `partner_program_tier_sync_configuration`, `supplementary_partner_program_expiry_reminder`."
**Evidence**:
- `createOrUpdateSupplementaryPartnerProgram` writes to 3 tables: `partner_programs` (saveSupplementaryPartnerProgramEntity), `supplementary_membership_cycle_details` (saveSupplementaryPartnerProgramCycle), `partner_program_tier_sync_configuration` (saveSupplementaryPartnerProgramTierSyncConfig). Line range 1750–1865 in `PointsEngineRuleService.java`.
- **Expiry reminders are NOT written by `createOrUpdatePartnerProgram`**. They use a separate Thrift method: `createOrUpdateExpiryReminderForPartnerProgram` (lines 286–311 in ThriftImpl). This is a distinct Thrift call for each reminder.
- **CRITICAL CONSTRAINT**: `PointsEngineRuleService.createOrUpdateExpiryReminderForPartnerProgram` enforces a **maximum of 2 expiry reminders** per partner program (line 1642: `if (autoIncId == 0 && allRemindersForPartnerProgram != null && allRemindersForPartnerProgram.size() >= 2)`). The BA's AC-22 specifies **up to 5 reminders** — this contradicts the existing service constraint.
**Verdict**: ⚠️ PARTIAL
**Confidence**: C7
**Notes**: The 4-table write pattern is correct in structure but publish-on-approve requires **two separate Thrift calls** (createOrUpdatePartnerProgram + N×createOrUpdateExpiryReminderForPartnerProgram), not one atomic operation. More critically, the existing service hard-caps reminders at 2, not 5 as the BA specifies. This requires either: (a) a new direct DAO-based write path bypassing the Thrift reminder service, or (b) an update to the `PointsEngineRuleService` reminder limit. This is a **BLOCKER for the BA reminder spec (AC-22)**.

---

### V-06: Enrollment creation — is_active / status check on partner_program
**BA Claim (KD-30)**: "ARCHIVED subscription: existing active enrollments continue to natural expiry. New enrollments blocked after ARCHIVE. Needs Phase 5 verification in emf-parent."
**Evidence**:
- `PartnerProgramLinkingActionImpl.evaluateActionforSupplementaryLinking` (lines 172–253): checks `isCustomerEnrolled(customerProfile)`, checks `isCustomerLinkedToPartnerProgram(...)`, checks `isOneCustomerOneSppSchemeEnabled()`, calls `validatePartnerProgramExpiry(payload, partnerProgram, membershipEndDate, ...)`.
- `validatePartnerProgramExpiry` (lines 1556–1577 of `PointsEngineEndpointActionUtils.java`): checks if `partnerProgramExpiryDate.before(eventDate)` OR `membershipEndDate.before(eventDate)` — throws `PartnerProgramExpiredException` if so.
- **NO `isActive` check on `PartnerProgram`**: The enrollment path does NOT check `partner_programs.is_active`. It only checks expiry date. A program with `is_active=false` (the current "archive" mechanism) would still allow enrollments if expiry date is not set or is in the future.
- The `PartnerProgram` API interface (line 39) has `getPartnerProgramExpiryDate()` but NO `isActive()` method in the interface.
- The `PartnerProgram` entity (`PartnerProgram.java` lines 74–76) has `is_active` field and `isActive()` method, but it is not exposed through the `PartnerProgram` API interface used by the linking action.
**Verdict**: ❌ CONTRADICTED
**Confidence**: C6
**Notes**: KD-30 assumption that existing code "blocks new enrollments when is_active=false" is NOT supported by the code. The enrollment guard only uses expiry date, not `is_active`. Setting `is_active=false` on `partner_programs` does NOT prevent new enrollments in emf-parent. To implement KD-30 (new enrollments blocked post-ARCHIVE), a new active-status check must be added to the enrollment path. This is a **significant gap** the architect must address.

---

### V-07: UnifiedPromotion maker-checker — parentId + version pattern
**BA Claim (CB session-memory)**: "UnifiedPromotion maker-checker uses `parentId` + `version` for edit-of-ACTIVE."
**Evidence**: `UnifiedPromotion.java` lines 77–90: `private String parentId` (JavaDoc: "pointing to the original ACTIVE promotion's objectId"), `private String parentDetails`, `@Builder.Default private Integer version = 1`. Also `getEffectiveStatus()` at line 174: `if (parentId != null) { return "DRAFT_FROM_ACTIVE"; }`.
**Verdict**: ✅ CONFIRMED
**Confidence**: C7

---

### V-08: StatusChangeRequest @Pattern validation is hardcoded to promotion actions
**BA Claim (CB session-memory)**: "`StatusChangeRequest` uses `@Pattern` with hardcoded promotion actions: `PENDING_APPROVAL|REVOKE|RESUME|PAUSE|STOP`."
**Evidence**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/unified/promotion/dto/StatusChangeRequest.java` lines 35–36: `@Pattern(regexp = "PENDING_APPROVAL|REVOKE|RESUME|PAUSE|STOP", message = "COMMON.INVALID_PROMOTION_STATUS")` on field `promotionStatus`.
**Verdict**: ✅ CONFIRMED
**Confidence**: C7
**Notes**: The field is named `promotionStatus` (not a generic `entityStatus`). Cannot be reused as-is for subscription status changes — a new generic DTO is needed as the BA/KD-10 mandates.

---

### V-09: No generic status-change infrastructure exists
**BA Claim (KD-10, KD-21, KD-22)**: No reusable maker-checker infrastructure; UnifiedPromotion's is promotion-specific; clean-room recommended.
**Evidence**: Confirmed from `StatusChangeRequest.java` (promotion-specific field name and regex), `UnifiedPromotionFacade.java` contains promotion-specific hooks (journeyEditHandler, communicationApprovalStatus, promotionDataReconstructor references confirmed by grep). No `GenericMakerChecker`, `AbstractWorkflowEntity`, or similar generic classes found in the codebase.
**Verdict**: ✅ CONFIRMED
**Confidence**: C6
**Notes**: KD-22 recommendation for clean-room implementation is validated.

---

### V-10: Maker-checker approver authorization — NO backend enforcement in UnifiedPromotion
**BA Claim (KD-29)**: "Maker-checker approver authorization is UI-ONLY. Backend exposes approve/reject API with no enforcement of WHO can approve."
**Evidence**: `UnifiedPromotionFacade.java` approve path (grep output lines 1405–1419): validates only `ApprovalStatus` enum value (`APPROVE`/`REJECT`). No `@PreAuthorize`, `@Secured`, `SecurityContext.hasRole()`, or approver identity checks found in the approve path.
**Verdict**: ✅ CONFIRMED
**Confidence**: C6

---

### V-11: supplementary_membership_history enum values
**BA Claim (KD-32, CB session-memory)**: "supplementary_membership_history tracks CUSTOMER-SUBSCRIPTION enrollment lifecycle: LINKED, DELINKED, MEMBERSHIP_INITIATED, RENEWED, EXPIRED, REVOKED_BY_MERGE, BACKUP_STARTED, EARLY_EXPIRY."
**Evidence**: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/supplementary_membership_history.sql` line 8:
- `action` enum: `SUPPLEMENTARY_MEMBERSHIP_STARTED`, `SUPPLEMENTARY_MEMBERSHIP_RENEWAL_INITIATED`, `SUPPLEMENTARY_MEMBERSHIP_RENEWED`, `SUPPLEMENTARY_MEMBERSHIP_EXPIRED`, `SUPPLEMENTARY_MEMBERSHIP_REVOKED_BY_MERGE`, `BACKUP_SUPPLEMENTARY_MEMBERSHIP_STARTED`, `PARTNER_PROGRAM_EARLY_EXPIRY`
- `source` enum: `LINKING`, `AUTO_DELINKING`, `DELINKING`, `UPDATE`, `MEMBERSHIP_ACTION`, `PP_EXPIRY_JOB`, `IMPORT`, `MERGE`

**Verdict**: ⚠️ PARTIAL
**Confidence**: C7
**Notes**: The BA listed the enum values without their `SUPPLEMENTARY_MEMBERSHIP_` prefix (e.g., "STARTED" vs actual "SUPPLEMENTARY_MEMBERSHIP_STARTED"; "RENEWAL_INITIATED" vs actual "SUPPLEMENTARY_MEMBERSHIP_RENEWAL_INITIATED"; "BACKUP_STARTED" vs "BACKUP_SUPPLEMENTARY_MEMBERSHIP_STARTED"; "EARLY_EXPIRY" vs "PARTNER_PROGRAM_EARLY_EXPIRY"). The actual enum values are more verbose. The BA also omitted the `source` enum entirely (LINKING, AUTO_DELINKING, etc.). The interpretation (KD-32) is correct — this table tracks enrollment lifecycle, NOT program lifecycle — but the exact column values need the full prefixed names when any code references them.

---

### V-12: backup_partner_program_id — column existence and behavior (KD-33)
**BA Claim (KD-33)**: "`backup_partner_program_id` exists in MySQL `partner_programs`, maps to `migrate_on_expiry` in MongoDB. Used when subscription expires to migrate member to fallback program."
**Evidence**:
- `cc-stack-crm/schema/dbmaster/warehouse/partner_programs.sql` line 15: `backup_partner_program_id int(11) DEFAULT NULL COMMENT 'backup partner program after partner program expiry'` — confirmed, nullable INT.
- `PartnerProgram.java` (entity) lines 106–108: `@Column(name = "backup_partner_program_id") private Integer backupPartnerProgramId` — mapped.
- `PointsEngineRuleService.java` lines 1780–1795: `updateBulkSPPExpiryJobStatus` uses `backupPartnerProgramId` when creating a `PartnerProgramExpiry` record (a MongoDB document in `emf` module) — this is the **expiry job tracking mechanism**, not a direct member migration trigger in the linking path.
- `PartnerProgramExpiry.java` in `emf/src/main/java/.../model/PartnerProgramExpiry.java`: MongoDB model with fields `orgId`, `programId`, `partnerProgramId`, `backupPartnerProgramId`, `status`, `initialExpiryDate`, `expiryDate`.
**Verdict**: ✅ CONFIRMED
**Confidence**: C6
**Notes**: `backup_partner_program_id` exists and is actively used. The migration mechanism works via an expiry job that reads a `PartnerProgramExpiry` MongoDB document (separate from the new subscription MongoDB collection). The publish-on-approve step must set `backup_partner_program_id` in MySQL correctly — the Thrift struct already has `backupProgramId` (field 14) for this. The KD-33 mapping is correct.

---

### V-13: partner_programs MySQL schema — BA field list accuracy (A-01)
**BA Claim (A-01, Section 1.2)**: "`partner_programs` has: id, org_id, loyalty_program_id, type (EXTERNAL/SUPPLEMENTARY), name, description, is_active, is_tier_based, points_exchange_ratio, expiry_date, backup_partner_program_id."
**Evidence**: Actual DDL (`partner_programs.sql`):
```
id, org_id, loyalty_program_id, partner_program_identifier (varchar 127, NOT NULL — MISSING FROM BA LIST),
name (varchar 50, NOT NULL), type, description, is_active, is_tier_based, points_exchange_ratio,
expiry_date, backup_partner_program_id, created_on, auto_update_time
```
**Critical**: `partner_program_identifier` is a **required NOT NULL column** (`varchar(127) NOT NULL`) that the BA did not list. The publish-on-approve path must generate and supply this value. The `PointsEngineRuleService.saveSupplementaryPartnerProgramEntity` generates it via `EMFUtils.generatePartnerProgramIdentifier()` for new programs (line 1862). Also: `description` column in MySQL has no NOT NULL constraint visible in DDL — but `PartnerProgram` entity maps it as nullable (no `nullable = false`).
**Unique constraint**: `UNIQUE KEY partner_program_name_idx (org_id, name)` — subscription names must be unique per org, across ALL partner programs (external and supplementary). This was not called out in the BA.
**Verdict**: ⚠️ PARTIAL
**Confidence**: C7
**Notes**: Missing field `partner_program_identifier` from BA schema listing is a gap. The publish-on-approve logic must ensure this is generated. The `(org_id, name)` uniqueness constraint spans ALL program types — creating a subscription with the same name as an existing external partner program in the same org will fail with a DB constraint violation.

---

### V-14: Duration YEARS support in MongoDB document vs. downstream systems
**BA Claim (Section 6.2)**: MongoDB document `duration.cycleType` supports `"DAYS | MONTHS | YEARS"`.
**Evidence**:
- `supplementary_membership_cycle_details` DDL: `cycle_type enum('DAYS','MONTHS')` — no YEARS.
- Thrift `PartnerProgramCycleType` enum: `DAYS`, `MONTHS` only — no YEARS.
- `PointsEngineRuleConfigThriftImpl.getSupplementaryPartnerProgramEntity` (lines 1988–1995): switch on cycleType only handles `DAYS` and `MONTHS` — YEARS case would fall through with `cycleType = null`.
**Verdict**: ❌ CONTRADICTED
**Confidence**: C7
**Notes**: YEARS as a cycle type cannot be published to MySQL or processed by Thrift. MongoDB can store it during DRAFT phase, but publish-on-approve would either fail or silently drop the YEARS value. The BA must either: (a) remove YEARS from the spec, or (b) add YEARS to the Thrift IDL enum AND add a Flyway migration to `supplementary_membership_cycle_details` (contradicting KD-19's no-Flyway-migration policy). This requires product decision — **architecture blocker**.

---

### V-15: Expiry reminder limit — 2 max vs. BA claim of 5
**BA Claim (AC-22)**: "Up to 5 reminders with: days before expiry (numeric) + channel (SMS/Email/Push)."
**Evidence**: `PointsEngineRuleService.createOrUpdateExpiryReminderForPartnerProgram` line 1642:
```java
if (autoIncId == 0 && allRemindersForPartnerProgram != null && allRemindersForPartnerProgram.size() >= 2) {
    throw new RuntimeException("only 2 expiry reminders can be configured per partner program");
}
```
**Verdict**: ❌ CONTRADICTED
**Confidence**: C7
**Notes**: The existing Thrift-backed service caps reminders at **2 per program**. The BA requires 5. Since KD-24/25 says publish-on-approve will sync reminders to MySQL, the publish path must either: (a) bypass the Thrift reminder service and write directly to DAO, or (b) remove the 2-reminder cap (a behavior change to existing functionality). Direct DAO writes during publish-on-approve would be cleaner and avoid the Thrift cap, but must be explicitly designed. This is an **architecture blocker for reminder design**.

---

## Gaps Found

| # | Gap | Severity | Resolution |
|---|-----|----------|------------|
| G-01 | `EmfMongoConfig.includeFilters` must be updated to route new `SubscriptionProgramRepository` to `emfMongoTemplate` — it is NOT auto-routed | LOW | Architect/Designer: add new repo class to EmfMongoConfig includeFilters. 2-line change. |
| G-02 | YEARS cycle type in BA MongoDB document spec has no downstream support (MySQL enum and Thrift IDL are DAYS/MONTHS only) | HIGH | Product/Architect: remove YEARS from spec OR add Flyway migration + Thrift IDL change (contradicts KD-19). Requires explicit product decision. |
| G-03 | Expiry reminders capped at 2 by `PointsEngineRuleService` — BA spec requires 5 | HIGH | Architect: publish-on-approve must write reminders via direct DAO (bypassing Thrift reminder service), not via `createOrUpdateExpiryReminderForPartnerProgram`. Design the publish path explicitly. |
| G-04 | No `is_active` check in enrollment path — setting a program inactive does NOT block new enrollments; only expiry date does | HIGH | Architect/KD-30: must add `is_active` guard to emf-parent enrollment path OR design a different archival mechanism (e.g., set far-past expiry date on archive). |
| G-05 | `partner_program_identifier` (varchar 127, NOT NULL) is missing from BA schema listing — publish-on-approve must generate this value | MEDIUM | Designer: ensure `subscriptionProgramId` or a generated identifier is mapped to this column during publish. Existing `EMFUtils.generatePartnerProgramIdentifier()` can be reused. |
| G-06 | `(org_id, name)` UNIQUE constraint on `partner_programs` spans ALL partner program types (external + supplementary) — subscription name uniqueness must be validated at org level, not just within subscriptions | MEDIUM | Designer/BA: API must validate name uniqueness against ALL partner programs for the org, not just other subscriptions. |
| G-07 | BA's `supplementary_membership_history` enum values listed without proper prefixes — actual values are `SUPPLEMENTARY_MEMBERSHIP_STARTED`, `SUPPLEMENTARY_MEMBERSHIP_RENEWAL_INITIATED`, etc. | LOW | BA: update session-memory and BA doc with correct enum values. Does not affect design but affects any code referencing these enums. |
| G-08 | `supplementary_membership_history.source` enum (LINKING, AUTO_DELINKING, DELINKING, UPDATE, MEMBERSHIP_ACTION, PP_EXPIRY_JOB, IMPORT, MERGE) was not documented by BA | LOW | Phase 5/Designer: document if new sources are needed for enrollment flow. Current values appear sufficient (LINKING, DELINKING, UPDATE). |
| G-09 | Publish-on-approve requires two separate Thrift flows: (1) `createOrUpdatePartnerProgram` for core + cycle + tier sync, (2) N calls to `createOrUpdateExpiryReminderForPartnerProgram` for reminders — no atomic single-call pattern exists | MEDIUM | Architect: design publish-on-approve as a service method that directly orchestrates DAO writes atomically, rather than chaining Thrift calls. See G-03. |

---

## Summary

- **14 claims verified**: 7 confirmed, 4 partial, 3 contradicted
- **Top findings**:
  1. **YEARS cycle type is a hard blocker** — BA document specifies DAYS/MONTHS/YEARS but MySQL and Thrift only support DAYS/MONTHS. YEARS cannot be published to MySQL without a schema migration, contradicting KD-19.
  2. **Expiry reminder cap of 2 (not 5)** — existing service hard-codes a 2-reminder maximum. BA AC-22 requires 5. The publish-on-approve path must bypass the Thrift reminder service and write directly to DAO.
  3. **No is_active enrollment guard** — the enrollment code path in emf-parent does NOT check `is_active` on the partner program. Setting `is_active=false` (the expected ARCHIVE mechanism) does NOT block new enrollments. KD-30 cannot be achieved without a new enrollment guard in emf-parent.
  4. **EmfMongoConfig requires explicit update** — new `SubscriptionProgramRepository` must be added to `EmfMongoConfig.includeFilters`. This is minimal but mandatory.
  5. **`partner_program_identifier` NOT NULL column** was absent from BA schema listing — the publish-on-approve step must generate and supply this value.
