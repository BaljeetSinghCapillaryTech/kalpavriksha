# Code Analysis -- emf-parent

> Phase 5: Codebase Research
> Date: 2026-04-11

---

## Key Architectural Insights

1. **ProgramSlab is minimal by design.** The entity stores identity (id, orgId, programId, serialNumber) and display (name, description, metadata JSON). All tier logic (eligibility, downgrade, renewal) lives in Strategy objects, NOT on the slab entity.

2. **Strategy pattern is the core abstraction.** Tier behavior is configured via Strategy entities with JSON `propertyValues`. The `ThresholdBasedSlabUpgradeStrategyImpl` parses threshold_values CSV, currentValueType, trackerId from strategy properties. Downgrade config is also a strategy.

3. **Thrift methods for slab CRUD already exist** in pointsengine_rules.thrift (PointsEngineRuleService), NOT in emf.thrift (EMFService). This is a critical finding -- the Blocker C-1 was based on searching the wrong Thrift file.

4. **Slab creation is atomic: slab + strategies.** `createSlabAndUpdateStrategies` creates the ProgramSlab AND updates all associated strategies in one call. This is what the TierApprovalHandler will call on MC approval.

## Entity Model

### ProgramSlab (table: program_slabs)
| Field | Type | Notes |
|-------|------|-------|
| pk.id | int | Auto-generated |
| pk.orgId | int | Tenant isolation |
| programId | int | FK to Program |
| serialNumber | int | Tier ordering (1 = base) |
| name | String | Required |
| description | String | Required |
| metadata | String | JSON (contains SlabMetaData with colorCode) |
| createdOn | Date | Timestamp |
| **status** | **String** | **NEW -- to be added via Flyway. DEFAULT 'ACTIVE'** |

### SlabInfo (Thrift struct -- pointsengine_rules.thrift)
| Field | Type | Notes |
|-------|------|-------|
| id | i32 | Slab ID |
| programId | i32 | Program ID |
| serialNumber | i32 | Tier ordering |
| name | string | Required |
| description | string | Required |
| colorCode | string | Optional |
| updatedViaNewUI | bool | Optional flag |

### StrategyInfo (Thrift struct)
| Field | Type | Notes |
|-------|------|-------|
| id | i32 | Strategy ID |
| programId | i32 | Program ID |
| name | string | Strategy name |
| description | string | Description |
| strategyTypeId | i32 | Type discriminator |
| propertyValues | string | JSON blob with ALL config |
| owner | string | Owner identifier |
| updatedViaNewUI | bool | Optional flag |

### TierConfiguration (DTO -- parsed from StrategyInfo.propertyValues)
| Field | Type | Notes |
|-------|------|-------|
| isActive | boolean | Active flag |
| slabs[] | TierDowngradeSlabConfig[] | Per-slab downgrade config |
| downgradeConfirmation | TierDowngradeAlertConfig | Alert on downgrade |
| reminders[] | TierDowngradeAlertConfig[] | Reminder configs |
| renewalConfirmation | TierDowngradeAlertConfig | Alert on renewal |
| retainPoints | boolean | Keep points on downgrade |
| isDowngradeOnReturnEnabled | boolean | Downgrade on return txn |
| dailyDowngradeEnabled | boolean | Daily vs month-end |
| isDowngradeOnPartnerProgramExpiryEnabled | boolean | Partner program linkage |
| thresholdValues | String | CSV of upgrade thresholds |
| currentValueType | String | Eligibility criteria type |
| trackerId | int | Tracker ID for tracker-based |
| trackerConditionId | int | Tracker condition ID |

### TierDowngradePeriodConfig
| Field | Type | Notes |
|-------|------|-------|
| type | PeriodType enum | FIXED, SLAB_UPGRADE, SLAB_UPGRADE_CYCLIC, FIXED_CUSTOMER_REGISTRATION |
| value | int | Period length |
| unit | PeriodUnit enum | NUM_MONTHS |
| startDate | Date | Period start |
| computationWindowStartValue | Integer | Window start offset |
| computationWindowEndValue | Integer | Window end offset |
| minimumDuration | int | Min duration before evaluation |

### Program Entity (tier-related fields)
| Field | Column | Notes |
|-------|--------|-------|
| programSlabs | - | @OneToMany relationship |
| slabUpgradePointCategoryID | slab_upgrade_point_category_id | Point category for upgrade |
| slabUpgradeStrategy | slab_upgrade_stategy_id | Strategy ID |
| slabUpgradeMode | slab_upgrade_mode | SlabUpgradeMode enum |
| slabUpgradeRuleIdentifier | slab_upgrade_rule_identifier | Ruleset name |

## Thrift Methods Available (pointsengine_rules.thrift)

| Method | Params | Returns | Notes |
|--------|--------|---------|-------|
| `getAllSlabs` | programId, orgId, serverReqId | list\<SlabInfo\> | READ: all slabs for a program |
| `createSlabAndUpdateStrategies` | programId, orgId, SlabInfo, list\<StrategyInfo\>, lastModifiedBy, lastModifiedOn, serverReqId | SlabInfo | WRITE: create slab + update strategies atomically |
| `createOrUpdateSlab` | SlabInfo, orgId, lastModifiedBy, lastModifiedOn, serverReqId | SlabInfo | WRITE: create or update slab only (no strategies) |

## Files to MODIFY

| File | Change | Why |
|------|--------|-----|
| ~~ProgramSlab.java~~ | ~~Add `status` field + getter/setter~~ | ~~Soft-delete lifecycle~~ — NOT NEEDED (Rework #3) |
| ~~PeProgramSlabDao.java~~ | ~~Add `findActiveByProgram()` method~~ | ~~Status-filtered queries~~ — NOT NEEDED (Rework #3) |
| ~~Flyway migration (NEW)~~ | ~~ALTER TABLE program_slabs ADD COLUMN status~~ | ~~Schema change~~ — NOT NEEDED (Rework #3) |

## Files to READ (patterns to follow)

| File | What to Learn |
|------|--------------|
| PointsEngineRuleService.java:2304 | createSlabAndUpdateStrategies implementation |
| PointsEngineRuleService.java:3662 | createOrUpdateSlab implementation |
| InfoLookupService.java | How slab data is cached and looked up |
| BasicProgramCreator.java | How slabs + rulesets are created together during program setup |
| ThresholdBasedSlabUpgradeStrategyImpl.java | How upgrade thresholds are parsed from strategy properties |
