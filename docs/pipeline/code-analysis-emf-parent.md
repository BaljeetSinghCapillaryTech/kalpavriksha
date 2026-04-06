# EMF-Parent Code Analysis: Tier CRUD APIs

**Research date:** 2026-04-06
**Analyst:** Feature-Pipeline Agent (claude-sonnet-4-6)
**Scope:** emf-parent codebase — everything relevant to building Tier CRUD APIs

---

## Key Architectural Insights

1. **ProgramSlab is the sole MySQL tier entity.** Table: `program_slabs`. PK is a composite `(id, org_id)` via `OrgEntityIntegerPKBase`. No separate "tier" table exists — slab = tier throughout the codebase.

2. **Strategies carry all threshold and downgrade config as serialised JSON.** The `strategies` table column `property_values` stores a JSON blob. For SLAB_UPGRADE it contains `{"current_value_type":"CUMULATIVE_PURCHASES","threshold_values":"1000,2000"}`. For SLAB_DOWNGRADE it contains the full `TierConfiguration`/`TierDowngradeStrategyConfiguration` JSON. There is NO dedicated thresholds column — thresholds live inside `property_values`.

3. **PointsEngineRuleConfigThriftImpl is the boundary.** All inbound Thrift calls from intouch-api-v3 land here. It implements `PointsEngineRuleService.Iface` (Thrift-generated, package `com.capillary.shopbook.pointsengine.endpoint.api.external`). It delegates to `PointsEngineRuleEditorImpl → PointsEngineRuleService` (the real service layer).

4. **Two distinct slab Thrift endpoints exist.** `createOrUpdateSlab` (single slab, auto-updates alloc/expiry strategies for new slabs) and `createSlabAndUpdateStrategies` (explicit strategy list passed in). The new Tier CRUD API should use `createOrUpdateSlab` for create/update; the older `createSlabAndUpdateStrategies` is the pre-existing path used when strategy deltas are known.

5. **serialNumber ordering is authoritative for tier rank.** Everywhere in the evaluation engine, slabs are compared and iterated by `serialNumber` (lower = lower tier, higher = higher tier). `getAllSlabs` returns them in serialNumber order via a `TreeMap<Integer, SlabInfo>`.

6. **Renewal and downgrade logic lives in strategy `property_values`, not in a separate table.** `TierConfiguration` (Gson-serialised) captures downgrade rules, period configs, conditions, and renewal configs — all stored as a JSON string in `strategies.property_values` for the SLAB_DOWNGRADE strategy (type id = 5).

7. **No member-count-per-slab DAO query exists in emf-parent.** The `PeCustomerEnrollmentDao` has no `GROUP BY current_slab_id` query. A count query will need to be added or derived via a native query.

8. **SlabInfo Thrift struct lives in a dependency jar.** Package: `com.capillary.shopbook.pointsengine.api.external.SlabInfo` (or `endpoint.api.external` in tests — likely the same generated class under different paths). It is NOT in emf-parent source; it is generated from a Thrift IDL that ships as a jar dependency.

---

## 1. ProgramSlab Entity

### Entity definition
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramSlab.java`

**Table:** `program_slabs`

| JPA field | Column | Type | Notes |
|-----------|--------|------|-------|
| `pk` | `(id, org_id)` | `ProgramSlabPK` (`OrgEntityIntegerPKBase`) | composite EmbeddedId |
| `programId` | `program_id` | `int` | FK to programs |
| `program` | — | `Program` (lazy) | @ManyToOne via (program_id, org_id) |
| `serialNumber` | `serial_number` | `int` | rank/ordering of tier, 1-based |
| `name` | `name` | `String` | tier name |
| `description` | `description` | `String` | tier description |
| `createdOn` | `created_on` | `Date` | timestamp |
| `metadata` | `metadata` | `String` | nullable JSON, currently holds `colorCode` via `SlabMetaData` Gson |

### ProgramSlabPK
```java
@Embeddable
public static class ProgramSlabPK extends OrgEntityIntegerPKBase {
    // Inherits: int id (auto-generated), int orgId
    // Constructors: ProgramSlabPK(orgId) for new, ProgramSlabPK(id, orgId) for lookup
}
```

`OrgEntityIntegerPKBase` is in a commons jar (not in emf-parent source). It provides `id` (auto-generated int) and `orgId`.

### PeProgramSlabDao
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeProgramSlabDao.java`

```java
// All methods:
List<ProgramSlab> findByProgram(int orgId, int programId);
ProgramSlab findByProgramSlabNumber(int orgId, int programId, int programSlabNumber); // by serialNumber
Long findNumberOfSlabs(int orgId, int programId);
// + GenericDao standard: findById, saveAndFlush, etc.
```

### How slabs are created today (BasicProgramCreator flow)
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/config/BasicProgramCreator.java`

Call chain during program creation:
1. `createBasicProgram(orgId, basicProgramConfig, createdBy, updatedViaNewUI)` — entry point
2. `createStrategiesJSON()` — builds JSON maps for all strategy types from `SlabInfoModel` list
3. `createProgramConfigurations(updatedViaNewUI)` — calls in sequence:
   - `createProgramSlabs()` — iterates `basicProgramConfig.getSlabs()`, calls `ProgramConfigDataHelper.createSlab(program, slabInfo)` per slab, batch saves via `ProgramCreationService.saveProgramSlabs()`
   - `createStrategies()` — saves `Strategy` entities for POINT_ALLOCATION, SLAB_UPGRADE, POINT_EXPIRY, POINT_REDEMPTION_THRESHOLD, POINT_RETURN
   - `createSlabUpgradeRuleset(...)` — creates `RulesetInfo` linked to `EventType.SlabUpgrade`
   - `createSlabDowngradeRuleset(...)` — creates `RulesetInfo` linked to `EventType.TierDowngradeEvent`
   - `createSlabRenewRuleset(...)` — creates `RulesetInfo` linked to `EventType.TierRenewEvent`

`ProgramConfigDataHelper.createSlab`:
```java
// File: .../impl/config/helper/ProgramConfigDataHelper.java line 128
ProgramSlabBuilder.programSlab()
    .setProgram(program)
    .setPk(new ProgramSlabPK(program.getOrgId()))  // id auto-generated
    .setCreatedOn(new Date())
    .setName(slabInfo.getName())
    .setDescription(slabInfo.getDesc())
    .setSerialNumber(slabInfo.getSerialNumber())
    .setMetadata(slabInfo.isSetMetaData() ? slabInfo.getMetaData().toJson() : null)
    .build();
```

---

## 2. Strategy / Ruleset System

### StrategyType enum
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/StrategyType.java`

**Table:** `strategy_types`

```java
public enum Type {
    POINT_ALLOCATION(1),
    SLAB_UPGRADE(2),
    POINT_EXPIRY(3),
    POINT_REDEMPTION_THRESHOLD(4),
    SLAB_DOWNGRADE(5),
    POINT_RETURN(6),
    EXPIRY_REMINDER(7),
    TRACKER(8),
    POINT_EXPIRY_EXTENSION(9);
}
```

### Strategy entity
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/Strategy.java`

**Table:** `strategies` — UNIQUE constraint on `(program_id, strategy_type_id, name)`

| Field | Column | Notes |
|-------|--------|-------|
| `pk (id, orgId)` | composite EmbeddedId | `StrategyPK extends OrgEntityIntegerPKBase` |
| `programId` | `program_id` | FK to programs |
| `name` | `name` | strategy name string (e.g. `"CUMULATIVE_PURCHASES500-1000"`) |
| `description` | `description` | |
| `strategyType` | `strategy_type_id` | FK to `strategy_types.id`; EAGER fetch |
| `propertyValues` | `property_values` | nullable; JSON blob with all config |
| `createdOn` | `created_on` | |
| `owner` | `owner` | `LOYALTY` or `CAMPAIGN` enum |

### How SLAB_UPGRADE strategy works

**JSON format for `property_values`** (from `BasicProgramCreatorHelper.createSlabUpgradeStrategy`):
```json
{
  "current_value_type": "CUMULATIVE_PURCHASES",
  "threshold_values": "500,1000,2000"
}
```
- `threshold_values` is a comma-separated list of N-1 thresholds (for N slabs)
- First slab always maps to threshold -1 (skipped in the CSV)

The evaluation class `ThresholdBasedSlabUpgradeStrategyImpl` (file: `.../impl/strategy/ThresholdBasedSlabUpgradeStrategyImpl.java`) deserialises these via an inner `ThresholdSlabUpgradeValues` struct. The full JSON can also carry: `tracker_id`, `tracker_condition_id`, `additional_upgrade_criteria`, SMS/email templates per slab index.

The `Program` entity holds `slab_upgrade_stategy_id` (FK to strategies.id) and `slab_upgrade_rule_identifier` (name of the upgrade ruleset, e.g. `"Slab_Upgrade_Rule_Start"`).

### How SLAB_DOWNGRADE strategy works

**Table:** stored in `strategies` with `strategy_type_id = 5`

`property_values` JSON is deserialised by `SlabDowngradeStrategyImpl` into `TierDowngradeStrategyConfiguration` (Gson). The JSON schema mirrors `TierConfiguration` (see section 4):
```json
{
  "isActive": true,
  "slabs": [
    {
      "slabNumber": 2,
      "shouldDowngrade": true,
      "downgradeTarget": "LOWEST",
      "periodConfig": { ... },
      "conditions": { "always": false, "purchase": 500, "numVisits": 3, "points": 0, "tracker": [] },
      "id": 101,
      "name": "Gold",
      "colorCode": "#FFFF00"
    }
  ],
  "downgradeConfirmation": { ... },
  "reminders": [ ... ],
  "renewalConfirmation": { ... },
  "retainPoints": false,
  "isDowngradeOnReturnEnabled": false,
  "dailyDowngradeEnabled": false
}
```

`TierDowngradeTarget` can be: `SINGLE`, `THRESHOLD`, or `LOWEST`

### How renewal rulesets work

`createSlabRenewRuleset` in `BasicProgramCreator` creates a `RulesetInfo` bound to `EventType.TierRenewEvent`. At runtime, `RenewSlabInstructionImpl` carries:
- `m_slabDowngradeStrategyId` — which strategy to use for renewal period
- `m_tierExpiryDate` — when the renewal expires
- `m_shouldExtendPoints` — whether points expiry extends on renewal
- `m_currentSlabNumber` — slab being renewed
- `m_slabChangeSource` — source (RULE or STRATEGY)

### Where thresholds are stored

| Type | Table | Column | Format |
|------|-------|--------|--------|
| SLAB_UPGRADE thresholds | `strategies` | `property_values` | `{"current_value_type":"CUMULATIVE_PURCHASES","threshold_values":"500,1000"}` |
| SLAB_DOWNGRADE conditions | `strategies` | `property_values` | JSON (TierConfiguration blob) |
| Renewal period | `strategies` | `property_values` | Same downgrade strategy JSON, includes `periodConfig` |

### BasicProgramCreator.createSlabUpgradeRuleset() — full chain

```
createSlabUpgradeRuleset(slabUpgradeRulesetName, updatedViaNewUI)
  → creates RulesetInfo (contextType="program", contextId=programId)
  → adds RuleInfo (via createBasicRuleInfo)
  → adds RulesetFilterInfo (LoyaltyTypeFilter + EventSourceFilter)
  → calls m_peRuleEditorImpl.getBaseRuleEditor().addNewRuleset(rulesetInfoEntity, EventType.SlabUpgrade.getStaticEventInfo(), ...)
```

The chain: strategy → ruleset → rule → action:
- **Strategy** (`strategies` table): holds JSON thresholds, read by `ThresholdBasedSlabUpgradeStrategyImpl`
- **Ruleset** (`ruleset_info` table): named e.g. `"Slab_Upgrade_Rule_Start"`, linked to `EventType.SlabUpgrade`
- **Rule** (`rule_info` table): one default rule per ruleset
- **Action** (action tables): at minimum an `AllocatePoints` action via `BillAwardPointsActionImpl`

---

## 3. Thrift Service Layer

### Thrift IDL
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/emf-all/scripts/emf.thrift`

This file defines the base `EMFService` and event structs. The `PointsEngineRuleService` Thrift IDL is **NOT present** in this repo — it is in a separate Thrift repo and compiled to the `PointsEngineRuleService.java` that ships as a jar dependency (package `com.capillary.shopbook.pointsengine.endpoint.api.external`).

### PointsEngineRuleConfigThriftImpl — slab operations
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`

**Class:** `public class PointsEngineRuleConfigThriftImpl implements PointsEngineRuleService.Iface, StrategyProcessor`

Slab-specific Thrift methods:

| Method | Signature | Notes |
|--------|-----------|-------|
| `createSlabAndUpdateStrategies` | `SlabInfo createSlabAndUpdateStrategies(int programId, int orgId, SlabInfo slabInfo, List<StrategyInfo> strategyInfos, int lastModifiedBy, long lastModifiedOn, String serverReqId)` | Legacy path: caller provides explicit strategy updates + slab |
| `createOrUpdateSlab` | `SlabInfo createOrUpdateSlab(SlabInfo slabInfo, int orgId, int lastModifiedBy, long lastModifiedOn, String serverReqId)` | New path: auto-extends strategies when new slab; used by new UI |
| `getAllSlabs` | `List<SlabInfo> getAllSlabs(int programId, int orgId, String serverReqId)` | Returns slabs ordered by serialNumber (TreeMap) |

Helper mapping method:
```java
// line 2178 — maps ProgramSlab entity to SlabInfo Thrift struct
private SlabInfo getSlabThrift(ProgramSlab programSlab) {
    SlabInfo slabInfo = new SlabInfo();
    slabInfo.setId(programSlab.getId());
    slabInfo.setProgramId(programSlab.getProgram().getId());
    slabInfo.setSerialNumber(programSlab.getSerialNumber());
    slabInfo.setName(programSlab.getName());
    slabInfo.setDescription(programSlab.getDescription());
    if (programSlab.getMetadata() != null) {
        SlabMetaData slabMetaData = SlabMetaData.getSlabMetaData(programSlab.getMetadata());
        slabInfo.setColorCode(slabMetaData.getColorCode());
    }
    return slabInfo;
}
```

### How the Thrift service maps to internal service classes

```
PointsEngineRuleConfigThriftImpl (Thrift boundary, @Service)
  ↓ delegates to
PointsEngineRuleEditorImpl (@Service, implements PointsEngineRuleEditor)
  ↓ delegates to
PointsEngineRuleService (@Service, the core service)
  ↓ uses
PeProgramSlabDao (Spring Data JPA, @Transactional("warehouse"))
PeStrategyDao
PeCustomerEnrollmentDao
InfoLookupService (cache layer)
```

---

## 4. TierConfiguration DTO

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/dto/TierConfiguration.java`

**Serialization:** Gson with `@SerializedName` annotations.

Full field list:

| Field | Java type | `@SerializedName` | Notes |
|-------|-----------|-------------------|-------|
| `m_isActive` | `boolean` | `"isActive"` | Is downgrade active? |
| `m_slabConfigs` | `TierDowngradeSlabConfig[]` | `"slabs"` | Per-slab downgrade config |
| `m_downgradeConfirmationConfig` | `TierDowngradeAlertConfig` | `"downgradeConfirmation"` | Notification config |
| `m_reminders` | `TierDowngradeAlertConfig[]` | `"reminders"` | Reminder notification array |
| `m_renewalConfirmationConfig` | `TierDowngradeAlertConfig` | `"renewalConfirmation"` | Renewal notification |
| `retainPoints` | `boolean` | `"retainPoints"` | |
| `m_isDowngradeOnReturnEnabled` | `boolean` | `"isDowngradeOnReturnEnabled"` | |
| `dailyDowngradeEnabled` | `boolean` | `"dailyDowngradeEnabled"` | |
| `isDowngradeOnPartnerProgramDeLinkingEnabled` | `boolean` | `"isDowngradeOnPartnerProgramExpiryEnabled"` | |
| `thresholdValues` | `String` | `"threshold_values"` | **Upgrade** thresholds CSV |
| `currentValueType` | `String` | `"current_value_type"` | e.g. `"CUMULATIVE_PURCHASES"` |
| `trackerId` | `int` | `"tracker_id"` | |
| `trackerConditionId` | `int` | `"tracker_condition_id"` | |

`TierConfiguration` is a **dual-purpose DTO**: it carries SLAB_UPGRADE config (threshold fields) AND SLAB_DOWNGRADE config (slabs, reminders, etc.). It is used in audit log trails via `AuditLogTrailDetailsDto.propertyValue`.

`TierDowngradeSlabConfig` (per-slab within `"slabs"` array) has: `slabNumber`, `shouldDowngrade`, `downgradeTarget` (SINGLE|THRESHOLD|LOWEST), `periodConfig`, `conditions` (purchase/numVisits/points/tracker/expression), `id`, `name`, `description`, `colorCode`.

**Where consumed:**
- `SlabUpgradeAuditLogService` — reads `TierConfiguration.getThresholdValues()` + `getCurrentValueType()`
- `SlabDowngradeAuditLogService` — reads `TierConfiguration.getSlabConfigs()` for downgrade conditions
- `AuditLogTrailDetailsDto` — wraps a `TierConfiguration` in the `property_value` field

---

## 5. Evaluation Engine (read-only understanding)

### SlabUpgradeService
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/SlabUpgradeService.java`

- Entry: `upgradeSlab(SlabChangeInfo slabChangeInfo, boolean shouldRenewSlab)`
- Loads `CustomerEnrollment` via `PeCustomerEnrollmentDao.findByProgramIdAndCustomerId`
- Checks `isActive()`
- Sets `customerEnrollment.setCurrentSlab(toSlab)` — `toSlab` comes from `SlabChangeInfo.getToSlab()`
- Calls `PointsExpiryService` for point expiry on upgrade
- Creates `CustomerSlabUpgradeHistoryInfo` record

**How next tier is determined:** The calling action (`BillAwardPointsActionImpl` or similar) evaluates `ThresholdBasedSlabUpgradeStrategyImpl.getNextSlab(currentSlab, lifetimePurchase)`. The strategy reads `threshold_values` CSV from its `property_values`, finds which threshold bucket the customer's lifetime purchase falls in, and returns the target `Slab` object (from `PointsProgramConfig.getSlabBySerial(n)`). `serialNumber` is the key for tier ordering.

### SlabDowngradeService
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/SlabDowngradeService.java`

- Entry: `downgradeSlab(SlabChangeInfo slabChangeInfo)`
- Guard: if `customerEnrollment.getCurrentSlab().getSerialNumber() <= toSlab.getSerialNumber()` — skip (already at or below target)
- Creates `CustomerSlabUpgradeHistoryInfo` with type `DOWNGRADE`
- Calls `PointsExpiryService` if needed

**Downgrade target determination:** `SlabDowngradeStrategyImpl` reads `TierDowngradeStrategyConfiguration` JSON. For each slab, `TierDowngradeSlabConfig.downgradeTarget` (SINGLE=go down one, THRESHOLD=to the slab that meets threshold, LOWEST=slab 1).

### RenewSlabInstructionImpl
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/instructions/RenewSlabInstructionImpl.java`

- Constructor captures: `pointsProgramConfig`, `slabDowngradeStrategyId`, `renewedOn`, `sourceType`, `sourceId`, `notes`, `tierExpiryDate`, `shouldExtendPoints`, `slabChangeSource`, `currentSlabNumber`, `evaluatedEntity`
- At `execute()` time (called by rule engine), it invokes `SlabUpgradeService.upgradeSlab(..., shouldRenewSlab=true)` or `SlabDowngradeService.downgradeSlab(...)` depending on context
- The `m_slabDowngradeStrategyId` is used to look up the SLAB_DOWNGRADE strategy that defines the renewal period

### serialNumber ordering
`getAllSlabs()` in `PointsEngineRuleConfigThriftImpl` line 491:
```java
TreeMap<Integer, SlabInfo> slabInfos = new TreeMap<>();
for (ProgramSlab ps : programSlabs) {
    slabInfos.put(slabInfo.getSerialNumber(), slabInfo);
}
// Returns as ordered list — serialNumber 1 = lowest tier
```
In downgrade logic: `currentSlab.getSerialNumber() <= toSlab.getSerialNumber()` guards against erroneous upgrades. In upgrade: thresholds array index = serialNumber - 2 (skipping slab 1's -1 threshold).

---

## 6. Member Count Queries

### CustomerEnrollment entity
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/CustomerEnrollment.java`

**Table:** `customer_enrollment` — UNIQUE on `(program_id, customer_id)`

Key fields relevant to tier membership:
| Field | Column | Notes |
|-------|--------|-------|
| `pk (id, orgId)` | composite | `CustomerEnrollmentPK extends OrgEntityLongPKBase` |
| `programId` | `program_id` | |
| `customerId` | `customer_id` | |
| `isActive` | `is_active` | |
| `currentSlab` | (lazy @ManyToOne) | join on `(current_slab_id, org_id)` |
| `currentSlabId` | `current_slab_id` | FK to `program_slabs.id` |
| `lifetimePurchases` | `lifetime_purchases` | BigDecimal, used for upgrade threshold |
| `visits` | `visits` | int |
| `enrollmentDate` | `enrollment_date` | |
| `lastSlabChangeDate` | `last_slab_change_date` | |
| `slabExpiryDate` | `slab_expiry_date` | |

### PeCustomerEnrollmentDao
**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeCustomerEnrollmentDao.java`

**No member-count-per-slab query exists.** The existing queries are:
```java
CustomerEnrollment findByProgramIdAndCustomerId(orgId, programId, customerId)
List<CustomerEnrollment> findByProgramIdAndCustomerId(orgId, programIds, customerId) // bulk
long getCustomerEnrolledCount(orgId, programId, customerId) // 0 or 1 per customer
List<Integer> getProgramsInWhichCustomerEnrolled(orgId, progIds, customerId)
List<CustomerEnrollment> getProgramsInWhichCustomerisEnrolled(orgId, progIds, customerId)
```

**IMPACT:** To return `memberCount` per tier in the Tier CRUD API response, a new JPQL query must be added to `PeCustomerEnrollmentDao`:
```java
@Query("SELECT ce.currentSlabId, COUNT(ce.pk.id) FROM CustomerEnrollment ce "
     + "WHERE ce.pk.orgId = :orgId AND ce.programId = :programId AND ce.isActive = true "
     + "GROUP BY ce.currentSlabId")
List<Object[]> countMembersPerSlab(@Param("orgId") int orgId, @Param("programId") int programId);
```
(This is a design recommendation — not yet implemented in the codebase. Confidence: C6 — the entity clearly supports this query.)

---

## 7. PartnerProgramTierSyncConfiguration

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PartnerProgramTierSyncConfiguration.java`

**Table:** `partner_program_tier_sync_configuration`

| Field | Column | Type | Notes |
|-------|--------|------|-------|
| `pk (id, orgId)` | composite EmbeddedId | `PartnerProgramTierSyncConfigurationPK` | |
| `loyaltyProgramId` | `loyalty_program_id` | `int` | FK to programs |
| `partnerProgramId` | `partner_program_id` | `int` | FK to partner_programs |
| `partnerProgramSlabId` | `partner_program_slab_id` | `int` | default -1; FK to partner slab |
| `loyaltyProgramSlabId` | `loyalty_program_slab_id` | `int` | FK to `program_slabs.id` |
| `createdOn` | `created_on` | `Date` | |
| `partnerProgram` | — | `PartnerProgram` (lazy) | @ManyToOne via (partner_program_id, org_id) |
| `partnerProgramSlabName` | — | `String` | @Transient — not persisted |

**Relationship to loyalty slabs:** `loyaltyProgramSlabId` is a direct foreign key reference to `program_slabs.id`. When a loyalty slab is **renamed or deleted**, this table must be checked for dangling mappings. This table maps a partner program's tier to a loyalty program's tier (1:1 per partner slab).

---

## 8. SlabInfo Thrift Struct Fields (reconstructed from usage)

The `SlabInfo` struct (package `com.capillary.shopbook.pointsengine.api.external` or `.endpoint.api.external`) is generated from a Thrift IDL in a dependency. Based on all setters observed across the codebase:

| Field | Type | Source evidence |
|-------|------|-----------------|
| `id` | `int` | `setId(programSlab.getId())` — Thrift impl line 2181 |
| `programId` | `int` | `setProgramId(RULE_CONFIG_PROGRAM_ID)` — integration test |
| `name` | `String` | `setName("slab1")` — SlabFixture |
| `description` | `String` | `setDescription(test_string)` — integration test (note: `setDesc` and `setDescription` both exist; `setDesc` used in fixtures, `setDescription` in tests — possibly aliases) |
| `serialNumber` | `int` | `setSerialNumber(i)` |
| `colorCode` | `String` | `setColorCode("#0000FF")` |
| `updatedViaNewUI` | `boolean` | `setUpdatedViaNewUI(false)` |
| `expiryUnit` | `String` | `setExpiryUnit("NUM_MONTHS")` — SlabFixture (used for `BasicProgram` creation only, not for createOrUpdateSlab) |
| `upgradeOnLifeTimePurchase` | `int` | `setUpgradeOnLifeTimePurchase(1000*i)` — SlabFixture (BasicProgram path) |
| `expiryValue` | `int` | `setExpiryValue(12)` — SlabFixture (BasicProgram path) |

Fields in `createOrUpdateSlab` path (relevant for Tier CRUD): `id`, `programId`, `name`, `description`, `serialNumber`, `colorCode`, `updatedViaNewUI`.

---

## QUESTIONS FOR USER

These items could not be determined with C5+ confidence from source code alone:

1. **SlabInfo Thrift IDL source**: The `PointsEngineRuleService.thrift` file is not in this repo. The exact IDL struct for `SlabInfo` and the complete `Iface` definition are compiled into a jar dependency. Where is the Thrift IDL repo? Can I access it to get the authoritative field list and service interface?

2. **`setDesc` vs `setDescription` on SlabInfo**: `SlabFixture` uses `setDesc("slab1")` while the integration test uses `setDescription(test_string)`. These may be the same field (`desc` = Thrift field, `description` = alias from `isSetDescription()`) but I cannot confirm without the IDL. Which setter maps to `program_slabs.description`?

3. **Member count requirement**: The BRD/session-memory says the Tier CRUD API should return member count per tier. No such query exists in `PeCustomerEnrollmentDao`. Should this count query be added in emf-parent (as a new DAO method + Thrift endpoint), or should intouch-api-v3 query it via a separate DB call? This is an architectural decision.

4. **Delete slab Thrift method**: No `deleteSlab` method was found in `PointsEngineRuleConfigThriftImpl`. Is slab deletion in scope? If yes, it requires: (a) a new Thrift method, (b) updating strategy `property_values` JSON to shrink threshold/expiry arrays, (c) migrating enrolled members away from the deleted slab. This is non-trivial.

5. **serialNumber reassignment on delete**: If slab serial 2 is deleted from a 3-slab program, should slab 3 become slab 2? The evaluation engine depends on contiguous serialNumbers for threshold array indexing. This is a gap — no existing code handles renumbering.

6. **`PartnerProgramTierSyncConfiguration` on slab rename/delete**: Should the Tier CRUD delete/update operation fail if a `PartnerProgramTierSyncConfiguration` record references the slab? Or silently nullify? No business rule is evident in the code.

---

## ASSUMPTIONS MADE

These are stated at C5+ confidence based on direct code evidence:

- **A1 (C7):** `program_slabs.serial_number` is the canonical tier rank. Higher number = higher tier. This is evident from all evaluation code that uses `serialNumber` for ordering and threshold indexing.

- **A2 (C6):** The `createOrUpdateSlab` Thrift method is the correct endpoint for the new Tier CRUD API's create/update path (not `createSlabAndUpdateStrategies`, which is legacy and requires the caller to compute strategy deltas).

- **A3 (C6):** `strategies.property_values` stores SLAB_UPGRADE thresholds as a CSV in `{"threshold_values":"500,1000"}`. Adding a new slab requires appending a new threshold value; removing a slab requires removing one value. The existing `updateStrategiesForNewSlab` method (in `PointsEngineRuleService`, line 3709) handles the add-slab case by appending `0` to allocation/expiry strategy arrays, but does NOT update the `threshold_values` CSV in the SLAB_UPGRADE strategy — that remains a gap for the create-tier case.

- **A4 (C6):** `TierConfiguration` is Gson-serialised (not Jackson). `@SerializedName` annotations are present. The `Strategy.propertyValues` column stores the raw JSON string.

- **A5 (C5):** No `deleteSlab` Thrift method exists in the current codebase. This must be added as a new method in the Thrift service. (C5 not C7 because the Thrift IDL itself is not readable — there could theoretically be a defined but unimplemented stub.)
