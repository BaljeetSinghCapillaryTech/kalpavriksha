# Code Analysis: cc-stack-crm Schema + thrift-ifaces-emf (CAP-183124)

## cc-stack-crm — Warehouse Schema

### Schema Directory Inventory

Total SQL files in `schema/dbmaster/warehouse/`: **117 files**

**Complete list (alphabetical):**

action_context_mapping.sql
action_points_details.sql
action_source_value_details.sql
alternate_currencies.sql
alternate_currencies_to_points_category_mapping.sql
badges_earned_stats.sql
benefits.sql
benefits_awarded_stats.sql
bulk_activity_summary.sql
calculate_kpi_job.sql
capping_config.sql
capping_filter_mapping.sql
card_series_program_mapping.sql
custom_fields.sql
custom_fields_enum_mapping.sql
customer_benefit_tracking.sql
customer_benefit_tracking_log.sql
customer_custom_job.sql
customer_enrollment.sql
customer_points_summary.sql
customer_slab_upgrade_history.sql
customer_tracked_kpi.sql
customer_transactions.sql
customers_downgrade_eligibility.sql
deduction_reversal_mapping.sql
earned_promotions.sql
entity_version.sql
event_log.sql
event_log_metadata.sql
event_sub_types.sql
event_types.sql
expiry_extension_configuration.sql
expiry_extension_log.sql
expiry_reminder_sent_stats_customer_level.sql
expiry_reminder_skip_info.sql
expiry_reminders_sent_stats.sql
gap_kpi_info.sql
global_promotions_to_program_mapping.sql
global_strategies_to_program_mapping.sql
goodwill_points_log.sql
historical_points.sql
historical_points_ledger_custom_fields.sql
issued_promotions.sql
liability_owners.sql
liability_split_ratio.sql
limit_periods.sql
limits.sql
manual_points_adjustment_log.sql
merge_customer_summary.sql
org_participation.sql
partner_program_enrollment.sql
partner_program_slab_history.sql
partner_program_slabs.sql
partner_program_tier_sync_configuration.sql
partner_programs.sql
points_awarded.sql
points_awarded_activity_level_summary.sql
points_awarded_bill_lineitem_promotions.sql
points_awarded_bill_promotions.sql
points_awarded_customer_promotions.sql
points_awarded_lineitems.sql
points_awarded_tender.sql
points_categories.sql
points_deductions.sql
points_expiry_extension_customers.sql
points_expiry_update_log.sql
points_expiry_update_summary.sql
points_ledger.sql
points_ledger_0.sql through points_ledger_9.sql (10 partitioned tables)
points_ledger_bucket_details.sql
points_redemption_summary.sql
points_source_types.sql
points_transfer_summary.sql
program.sql
program_config_key_values.sql
program_config_keys.sql
program_event_mapping.sql
program_slabs.sql
promotion_event_ruleset_mapping.sql
promotion_usage_daily_summary.sql
promotions.sql
promotions_metadata.sql
redeem_earned_promotion_activity_log.sql
redemption_reversal_mapping.sql
returned_bill_details.sql
side_effects_tracking.sql
skipped_vouchers_stats.sql
slab_change_details.sql
source_tracking.sql
strategies.sql
strategy_types.sql
supplementary_membership_cycle_details.sql
supplementary_membership_history.sql
supplementary_partner_program_enrollment.sql
supplementary_partner_program_expiry_reminder.sql
system_rules.sql
system_rules_scope_types.sql
system_rules_scopes.sql
system_rules_scopes_properties.sql
system_rules_scopes_property_values.sql
tender_code.sql
tender_code_attribute.sql
tracker_conditions.sql
voucher_issual_item_code.sql
voucher_issual_item_code_sms_mapping.sql
vouchers_issued.sql
vouchers_redeemed.sql

### custom_fields.sql

**File path:** `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/custom_fields.sql`

```sql
CREATE TABLE `custom_fields` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `org_id` int(11) NOT NULL,
    `field_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Name of the custom field',
    `field_type` enum('PROMOTION','REDEMPTION_PURPOSE') COLLATE utf8mb4_unicode_ci NOT NULL,
    `value_type` enum('DOUBLE','STRING','STRING_LIST','DATE_TIME','ENUM') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'type of value to be stored against the custom field',
    `created_on` datetime NOT NULL,
    `created_by` int(11) NOT NULL DEFAULT -1,
    `auto_update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_active` tinyint(1) NULL DEFAULT '1' ,
    PRIMARY KEY (`id`,`org_id`),
    KEY `field_label` (`org_id`,`field_type`,`field_name`),
    KEY `auto_update_time` (`auto_update_time`)
);
```

**Key observations:**
- **Composite PK:** `(id, org_id)` — multi-tenancy pattern with org isolation
- **is_active:** `tinyint(1) NULL DEFAULT '1'` — nullable boolean, defaults to active
- **created_on:** `datetime NOT NULL` — creation timestamp
- **auto_update_time:** `timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` — auto-managed update tracking
- **field_type enum:** restricted to `PROMOTION` or `REDEMPTION_PURPOSE` (only 2 types)
- **value_type enum:** 5 types — `DOUBLE`, `STRING`, `STRING_LIST`, `DATE_TIME`, `ENUM`

### program_config_key_values.sql

**File path:** `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/program_config_key_values.sql`

```sql
CREATE TABLE `program_config_key_values` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key_id` int(11) NOT NULL,
  `org_id` int(11) NOT NULL,
  `program_id` int(11) NOT NULL,
  `value` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `updated_by` int(11) NOT NULL COMMENT 'user who updated the key',
  `updated_on` datetime NOT NULL COMMENT 'time when the key is updated',
  `is_valid` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`,`org_id`),
  KEY `keys_names` (`org_id`,`key_id`,`program_id`,`is_valid`),
  KEY `program_id` (`org_id`,`program_id`)
) ;
```

**Key observations:**
- **Composite PK:** `(id, org_id)` — consistent multi-tenancy pattern
- **program_id present:** YES — links to `program_config_keys` via `key_id`
- **No explicit FK:** Foreign key to `program_config_keys` not defined in CREATE TABLE (may be managed at application layer)
- **Composite indexes:** Optimized for lookups by `org_id + key_id + program_id + is_valid`
- **value field:** `mediumtext` — flexible storage for configuration values (JSON, lists, etc.)
- **is_valid:** `tinyint(1) NOT NULL` — hard constraint (not nullable)
- **updated_on:** `datetime NOT NULL` — audit timestamp

### program_config_keys.sql

**File path:** `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/program_config_keys.sql`

```sql
CREATE TABLE `program_config_keys` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `value_type` enum('STRING','NUMERIC','BOOL','LIST','MAP','RANGE') COLLATE utf8mb4_unicode_ci NOT NULL,
  `default_value` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `label` varchar(250) COLLATE utf8mb4_unicode_ci NOT NULL,
  `added_by` int(11) NOT NULL,
  `added_on` datetime NOT NULL,
  `is_valid` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `key_name` (`name`)
) ;
```

**Key observations:**
- **Global key registry:** No `org_id` column — this is global across all organizations
- **Composite PK:** Single column `id` — simple surrogate key
- **value_type enum:** 6 types — `STRING`, `NUMERIC`, `BOOL`, `LIST`, `MAP`, `RANGE` (broader than `custom_fields`)
- **default_value:** `mediumtext NOT NULL` — flexible default configuration
- **Index on name:** `KEY key_name (name)` — lookup optimization for name-based queries
- **added_on:** `datetime NOT NULL` — creation audit timestamp
- **is_valid:** `tinyint(1) NOT NULL` — hard constraint

---

## thrift-ifaces-emf — emf.thrift

### File Header / Namespaces

**File path:** `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf/emf.thrift`

```thrift
#!thrift -java -php -phps

/**
* This file contains all the event management related classes and definitions.
*/

namespace java com.capillary.shopbook.emf.api.external

namespace php emf
```

**Key observations:**
- **Languages:** Java and PHP support declared
- **Java namespace:** `com.capillary.shopbook.emf.api.external` — external API package
- **PHP namespace:** `emf` — minimal PHP namespace

### EMFException struct

**Full definition:**

```thrift
/**
* This is an exception which contains the error code and message providing information about the event manager response.
*/
exception EMFException {
1: required i32 statusCode;
2: required string errorMessage;
3: required i32 replayErrorCode;
4: optional bool notReplayable;
}
```

**Key observations:**
- **4 fields** (3 required, 1 optional)
- **statusCode:** Required i32 — HTTP-style error codes
- **errorMessage:** Required string — human-readable error text
- **replayErrorCode:** Required i32 — specific replay failure tracking
- **notReplayable:** Optional bool — flag for non-replayable errors

### ExtendedFieldsData / ExtendedField structs

**Full definitions found in thrift:**

```thrift
struct ExtendedFieldsData {
    1: required string name;
    2: required string value;
    3: optional string previousValue;
}

struct CustomFieldsData {
   1: required i32 assocID;
   2: required string customFieldName;
   3: optional string customFieldType;
   4: optional string previousCustomFieldValue;
   5: optional string customFieldValue;
}
```

**Key observations:**
- **ExtendedFieldsData:** 3 fields — name, value, previousValue (for change tracking)
- **CustomFieldsData:** 5 fields — association ID, field name, type, and old/new values
- **No separate "ExtendedField" struct** — only `ExtendedFieldsData` exists
- **Used in multiple event data structures:**
  - `CardDetails` (field 11: `optional map<string, string> extendedFieldsData`)
  - `UserDetails` (field 6: `optional map<string,string> extendedFieldsData`)
  - `LineItem` (field 2: `required map<string,string> extendedFieldsData`)
  - `FleetGroup` (field 10: `optional map<string,string> extendedFieldsData`)
  - `UserEntityReference` (field 5: `optional map<string,string> extendedFieldsData`)
  - `NewBillEvent` (field 23: `optional map<string,string> extendedFieldsData`)
  - `ReturnBillLineitemsEventData` (field 21: `optional map<string,string> extendedFieldsData`)
  - `ReturnBillAmountEventData` (field 21: `optional map<string,string> extendedFieldsData`)
  - `TransactionUpdateEventData` (field 15: `optional map<string,string> extendedFieldsData` and field 21: `optional list<ExtendedFieldsData> extFieldsData`)

### EMFService — Last 10+ Methods (method signature overview)

**Methods 48-57 (last methods before service closure):**

```thrift
    EventEvaluationResult tierDowngradeEvent(1: TierChangeEventData tierChangeEventData,
                   2: bool isCommit, 3: bool isReplayed) throws (1: EMFException ex);

    EventEvaluationResult tierRenewEvent(1: TierChangeEventData tierChangeEventData,
                  2: bool isCommit, 3: bool isReplayed) throws (1: EMFException ex);

    EventEvaluationResult bulkEMFEvent(1: BulkEMFEventData bulkEMFEventData, 2: bool isCommit, 3: bool isReplayed) throws (1: EMFException ex);
}
```

**Complete sequence of last 15 methods (numbered ~43-57):**

1. `partnerProgramLinkingEvent`
2. `partnerProgramUpdateEvent`
3. `partnerProgramDeLinkingEvent`
4. `reassessTier`
5. `getCustomerLoyaltyEvents`
6. `userGroup2CreateEvent`
7. `returnTargetCompletedEvent`
8. `issuePromotionToEntityEvent`
9. `earnPromotionToEntityEvent`
10. `simulateTransactionAddEvent`
11. `revokeEarnPromotionEvent`
12. `revokeIssuePromotionEvent`
13. `manualCurrencyAllocationEvent`
14. `tierDowngradeEvent`
15. `tierRenewEvent`
16. `bulkEMFEvent`

### EMFService — Total Method Count

**Total EMFService methods: 57**

**Breakdown by category:**
- **Lifecycle methods:** 2 (isRunning, isAlive)
- **Organization methods:** 3 (isOrganizationEnabled, disableOrganization, checkOrganizationConfiguration)
- **Event handler methods:** ~48 (main event processing)
- **Generic event query methods:** 2 (getAllGenericEvents, isGenericEvent)
- **Side effects query methods:** 1 (getSideEffectsForCustomer)
- **Evaluation log search:** 1 (searchEvaluationLog)

**Method numbering:** If new Loyalty Extended Fields CRUD methods are added, they would start at **method 58, 59, 60, etc.**

### Other .thrift files

**File path:** `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf/`

```
emf.thrift (main)
bin/emf.thrift (binary/compiled version)
```

**Only 2 thrift files exist** — the main source and a bin directory copy.

---

## loyalty_*.sql files

**Status:** **None found** — No tables matching pattern `loyalty_*.sql` exist in the warehouse schema.

**Implication:** The Loyalty Extended Fields table must be created from scratch as part of CAP-183124.

---

## subscription*.sql files

**Status:** **No subscription*.sql files found** in the warehouse schema.

**Related tables that exist:**
- `supplementary_membership_cycle_details.sql`
- `supplementary_membership_history.sql`
- `supplementary_partner_program_enrollment.sql`
- `supplementary_partner_program_expiry_reminder.sql`

(These are supplementary/partner-related, not generic subscription tables.)

---

## Key Facts for Feature Implementation

1. **Database Schema Patterns:**
   - Multi-tenancy enforced via composite PKs: `(id, org_id)` for transactional tables
   - Global registries use single-column PKs (e.g., `program_config_keys`)
   - Timestamp fields use both `datetime` (audit) and `timestamp` (auto-update) patterns
   - Boolean flags stored as `tinyint(1)` with proper NOT NULL constraints

2. **Configuration Architecture:**
   - `program_config_keys` is the global key registry (no org_id)
   - `program_config_key_values` maps keys to values per program (org_id, program_id, key_id)
   - `value_type` enums differ between tables (5 types in custom_fields vs 6 in program_config_keys)
   - Values stored as `mediumtext` for flexibility (JSON, lists, maps)

3. **Extended Fields in Thrift:**
   - `ExtendedFieldsData` struct exists (3 fields: name, value, previousValue) for change tracking
   - Extended fields used as `map<string, string>` in 9+ event data structures
   - Also supports structured list: `list<ExtendedFieldsData>` in TransactionUpdateEventData
   - No separate "ExtendedField" singular struct — always map or list of ExtendedFieldsData

4. **EMFService Expansion Capacity:**
   - Current: 57 methods (well-established, mature interface)
   - Next method IDs available: 58, 59, 60, etc.
   - Pattern: Event handlers return `EventEvaluationResult` (or other types) and throw `EMFException`
   - Standard signature: `EventEvaluationResult methodName(1: EventData data, 2: bool isCommit, 3: bool isReplayed) throws (1: EMFException ex)`

5. **Loyalty Extended Fields Implementation Considerations:**
   - **Table schema:** Should follow existing pattern with composite PK `(id, org_id)` + indexes on frequent access paths
   - **Timestamp fields:** Use both `datetime` (created_on/updated_on) and `timestamp` (auto_update_time) for audit
   - **Active flag:** Pattern is `is_active tinyint(1) NULL DEFAULT '1'` or `tinyint(1) NOT NULL`
   - **Thrift integration:** Add new extended field structs and update event data structures to include loyalty-specific extended fields
   - **EMFService methods:** Will need CRUD operations (create, read, update, delete) which would map to new thrift method IDs 58+
   - **Custom vs Extended distinction:** Custom fields = transactional/promotion-related; Extended = flexible metadata (confirm with BA)

6. **Schema Files Already Present That May Be Relevant:**
   - `custom_fields.sql` — existing custom field infrastructure (PROMOTION, REDEMPTION_PURPOSE types)
   - `custom_fields_enum_mapping.sql` — enumeration values for custom fields
   - `program_config_keys.sql` + `program_config_key_values.sql` — configuration management system
   - No existing `loyalty_*.sql` files — greenfield opportunity

7. **Gaps/Unknowns Requiring Design Clarification:**
   - Relationship between loyalty extended fields and existing custom_fields
   - Whether loyalty extended fields are org-scoped or global
   - Whether loyalty extended fields are linked to specific programs
   - Whether values are scalar (string/number) or structured (JSON/map)
   - Whether historical tracking of extended field changes is required (previousValue pattern)
   - Thrift method signatures for CRUD operations (method names, parameters, return types)

