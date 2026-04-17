# Code Analysis — emf-parent
> Repo: /Users/anujgupta/IdeaProjects/emf-parent
> Generated: Phase 5, 2026-04-18
> LSP: jdtls running (used for symbol navigation; grep used as fallback)

---

## Key Architectural Insights

- **C7**: The Thrift handler → editor (facade) → service → DAO four-layer pattern is the canonical pattern. The closest template for BenefitCategory is `PointsEngineRuleConfigThriftImpl` (handler) → `PointsEngineRuleEditorImpl` (editor/facade) → `PointsEngineRuleService` (service, `@Transactional`) → `PeProgramSlabDao` / `BenefitsDao` (Spring Data JPA + `GenericDao`). All four layers are Spring beans.
- **C7**: `OrgEntityIntegerPKBase` (`com.capillary.commons.data.OrgEntityIntegerPKBase`) is the platform-standard PK base. It is `@MappedSuperclass` providing `int id` (auto-identity) + `int org_id`. Every loyalty entity (`Benefits`, `ProgramSlab`, `PointCategory`, `PartnerProgramTierSyncConfiguration`) uses it via an inner `@Embeddable` PK class. New `BenefitCategory` MUST follow this. PKs are `int(11)` at schema and `int`/`i32` at Java/Thrift.
- **C7**: No `@Filter`, `@FilterDef`, or `@Where` annotation exists anywhere in emf-parent for org_id enforcement. Multi-tenancy is enforced **entirely by convention**: every DAO query manually adds `WHERE pk.orgId = :orgId` (or equivalent). See `BenefitsDao`, `PeProgramSlabDao`, `PointsEngineRuleService.lockProgram`.
- **C7**: JVM default timezone is **NOT configured** in the Dockerfile, any properties file, or any XML config. `user.timezone` is absent from the JVM CMD args. The system default (OS timezone) governs at runtime. Per D-24, all `Date ↔ i64` conversions in the new Thrift handler MUST use `TimeZone.getTimeZone("UTC")` explicitly.
- **C7**: The Thrift service registration mechanism is the `@ExposedCall(thriftName = "pointsengine-rules")` annotation on handler classes; the `ExposedCallAspect` AOP interceptor wraps every public method with request lifecycle management (ThreadLocalCache, RequestStats, MDC, ShardContext). New handlers must carry this annotation.
- **C7**: The platform-standard exception envelope is: catch `Exception` → log → `throw new PointsEngineRuleServiceException(ex.getMessage())` with `setStatusCode(400)` for validation errors, `setStatusCode(500)` for unexpected errors. This is the pattern used by every method in `PointsEngineRuleConfigThriftImpl`.
- **C7**: Audit columns on existing tables are `created_on DATETIME NOT NULL`, `created_by INT`, `auto_update_time TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`. NO existing table has `updated_on` or `updated_by`. These are **net-new columns** in the D-23 hybrid pattern — no existing entity or migration to copy from.
- **C7**: Thrift i64 timestamp naming convention in `emf.thrift` is `*InMillis` suffix (e.g., `createdOnInMillis`, `eventTimeInMillis`, `pointsExpiryDateinMillis`). This directly answers OQ-41 for this repo's view. Note: `thrift-ifaces-pointsengine-rules` uses the bare `createdOn`/`updatedOn` convention (see its analysis) — the two differ. Phase 7 must choose which convention the new IDL follows; recommendation is bare `createdOn` since the new service lives in pointsengine-rules.
- **C6**: The schema home for new tables is the **cc-stack-crm integration-test snapshot** (`integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/`). The actual migration mechanism appears to be direct SQL files in the cc-stack-crm repo's directory (no Flyway V-numbered files found in emf-parent). The emf-parent integration test harness consumes these DDLs.
- **C5**: No existing entity or dispatcher references a `BENEFITS` category type or dispatches on `category_type`. The new `BenefitCategory.categoryType = BENEFITS` enum is net-new with zero platform registration required.

---

## 1. Entities & Persistence

### ProgramSlab Entity (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramSlab.java`

- **Package**: `com.capillary.shopbook.points.entity`
- **Table**: `program_slabs`
- **Base class**: None directly — uses inner `@Embeddable` class `ProgramSlabPK extends OrgEntityIntegerPKBase`
- **PK strategy**: `@EmbeddedId ProgramSlabPK pk` — composite int PK via `OrgEntityIntegerPKBase` (auto-identity `id` + `org_id`)
- **Key fields**:
  - `programId INT NOT NULL` (`@Column name="program_id"`)
  - `name VARCHAR NOT NULL`
  - `description VARCHAR NOT NULL`
  - `serialNumber INT NOT NULL` (`serial_number`)
  - `createdOn Date` + `@Temporal(TemporalType.TIMESTAMP)` (`created_on DATETIME`)
  - `metadata VARCHAR` (optional JSON for colorCode)
  - `auto_update_time` exists at schema level only (not mapped in entity — platform pattern)
- **No is_active column** — `ProgramSlab` has no deactivation field; slabs are never soft-deleted

**Schema DDL** (`program_slabs.sql` line 3-17, C7):
```sql
CREATE TABLE `program_slabs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `org_id` int(11) NOT NULL DEFAULT '0',
  `program_id` int(11) NOT NULL,
  `serial_number` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` mediumtext NOT NULL,
  `created_on` datetime NOT NULL,
  `auto_update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `metadata` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`,`org_id`),
  UNIQUE KEY `program_id` (`org_id`,`program_id`,`serial_number`)
);
```
FK from `benefit_category_slab_mapping.slab_id` → `program_slabs.id` must also carry `org_id` companion column for the composite PK join.

### OrgEntityIntegerPKBase (C7)
**File**: `/Users/anujgupta/IdeaProjects/shopbook-datamodel/src/main/java/com/capillary/commons/data/OrgEntityIntegerPKBase.java`

- **Package**: `com.capillary.commons.data`
- `@MappedSuperclass` providing `int id` (`@GeneratedValue(GenerationType.IDENTITY)`, `@Column(name="id")`) + `int orgId` (`@Column(name="org_id")`)
- **Correct instantiation**: `new XxxPK(orgId)` on INSERT (id=0 triggers auto-generate), `new XxxPK(id, orgId)` on lookup

### Benefits Entity (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/Benefits.java`

- Same `OrgEntityIntegerPKBase` pattern via inner `BenefitsPK`
- Fields: `name`, `benefit_type ENUM(POINTS,VOUCHER)`, `program_id`, `promotion_id` (NOT NULL — mandatory FK to promotions), `description`, `max_value`, `is_active`, `created_by INT`, `created_on` (stored twice: once as String, once as `Date @Temporal`), `linked_program_type`
- **Thrift-exposed**: referenced by `BenefitsDao` queries used in `PointsEngineRuleService`; fully MySQL-backed
- **No Thrift IDL struct exists** for `Benefits` itself — the existing `BenefitsType` (`VOUCHER/POINTS`) Thrift enum is in `pointsengine.api.external` package, not in `thrift-ifaces-pointsengine-rules` (CROSS-REPO NOTE: see thrift-ifaces analysis — `BenefitsConfigData` struct DOES exist in `pointsengine_rules.thrift` at lines 692-707, contrary to this repo's partial view. The two analyses combined confirm the full picture.)

### PointCategory Entity (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PointCategory.java`

- Same pattern: `OrgEntityIntegerPKBase` via `PointCategoryPK`
- Table: `points_categories`
- Has DB `@UniqueConstraint(columnNames = {"program_id", "name"})` — note this IS a DB unique constraint (D-28 chose NOT to use this for BenefitCategory)
- Fields include `name`, `description`, `programId`, `isActive`, `createdOn`, `createdBy` (int)

### BenefitsAwardedStats — alternate PK variant (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/data/model/BenefitsAwardedStats.java`

- Uses `OrgEntityLongPKBase` (long PK variant) — exists but is **not** the pattern for loyalty CRUD entities
- Has `created_on DATETIME`, `created_by INT`, `last_updated_on DATETIME` — closest existing entity to the D-23 hybrid pattern, though uses `last_updated_on` not `updated_on`

### Flyway / Migration Convention (C5)
No Flyway `V{n}__*.sql` numbered files found in emf-parent itself. Schema DDLs live in `integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/` as flat SQL files (one file per table). The actual production migration home is **cc-stack-crm repo** (confirmed from Phase 2 research). New `benefit_categories.sql` and `benefit_category_slab_mapping.sql` go there.

---

## 2. Thrift Service Handlers

### Handler Registration Mechanism (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/system/ExposedCall.java`

Thrift handlers are Spring `@Service` beans annotated `@ExposedCall(thriftName = "...")`. The `ExposedCallAspect` AOP interceptor wraps every public method:
1. Initializes `RequestStatsContext` and `ThreadLocalCacheManager`
2. Sets `ShardContext.set(orgId)` from `@MDCData(orgId="#orgId")` SpEL expression
3. Clears thread-locals on exit (including `ShardContext.reset()`)

Registered handlers:
- `EMFThriftServiceImpl` — `@ExposedCall(thriftName = "emf")` — handles event evaluation
- `PointsEngineThriftServiceImpl` — `@ExposedCall` — handles points engine operations
- `PointsEngineRuleConfigThriftImpl` — `@ExposedCall(thriftName = "pointsengine-rules")` — handles CRUD config operations (slabs, strategies, promotions)
- `RuleConfigServiceImpl` — `@ExposedCall`
- `EmbeddedStrategyProcessorImpl` — `@ExposedCall`

### Canonical Template: PointsEngineRuleConfigThriftImpl (OQ-35 answer, C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`

**Class signature**:
```java
@Service
@ExposedCall(thriftName = "pointsengine-rules")
public class PointsEngineRuleConfigThriftImpl implements Iface, StrategyProcessor {
```

**Constructor DI**: Has a `@Autowired`-on-fields pattern AND a `public PointsEngineRuleConfigThriftImpl(PointsEngineRuleEditor pointsEngineRuleEditor)` constructor (legacy, also sets `m_pointsEngineRuleEditor`). Field injection is dominant for all other dependencies.

**Canonical method shape** (e.g., `createOrUpdateSlab`):
```java
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public SlabInfo createOrUpdateSlab(SlabInfo slabInfo, int orgId, int lastModifiedBy,
                                   long lastModifiedOn, String serverReqId)
        throws PointsEngineRuleServiceException, TException {
    try {
        // 1. Fetch existing state (for audit/cache eviction)
        ProgramSlab slab = m_pointsEngineRuleEditor.createOrUpdateSlab(orgId, slabInfo);
        // 2. Audit log
        m_pointsEngineRuleEditor.logAuditTrails(oldSlab, slab, lastModifiedBy, updatedViaNewUI);
        // 3. Cache eviction
        cacheEvictHelper.evictProgramIdCache(orgId, slabInfo.getProgramId());
        // 4. Build Thrift response from entity
        return getSlabThrift(slab);
    } catch (ValidationException ex) {
        throw new PointsEngineRuleServiceException(ex.getMessage()).setStatusCode(400);
    } catch (Exception ex) {
        throw new PointsEngineRuleServiceException(ex.getMessage()).setStatusCode(500);
    } finally {
        newRelicUtils.pushRequestContextStats();
    }
}
```

**Key observations**:
- `orgId` is passed as explicit parameter (not from ThreadLocal — though `ShardContext` is set by the `ExposedCallAspect`)
- `lastModifiedBy` is passed as `int` from the caller (intouch-api-v3 injects from `IntouchUser.principal`)
- `lastModifiedOn` is `long` epoch millis (matching D-24 i64 pattern); converted to `Date` via `new Date(lastModifiedOn)` at line 211
- `serverReqId` is a correlation ID string
- `@Trace(dispatcher = true)` is New Relic instrumentation
- No `@Transactional` on the Thrift handler — transaction boundary is in `PointsEngineRuleService`

**Handler is Spring-managed** via `@Service`.

---

## 3. Facade / Service Layer Pattern

### PointsEngineRuleEditorImpl (Editor / Facade Layer, C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/editor/PointsEngineRuleEditorImpl.java`

- Thin delegation layer between Thrift handler and `PointsEngineRuleService`
- `createOrUpdateSlab(orgId, slabInfo)` → `m_pointsEngineRuleService.createOrUpdateSlab(orgId, slabInfo)` (line 1264-1266)
- No `@Transactional` at this layer; transaction is in the service

### PointsEngineRuleService (Service / Transaction Layer, C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/PointsEngineRuleService.java`

**Class signature**:
```java
@Service
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)
public class PointsEngineRuleService {
```

- `@Transactional` is **class-level** with `value = "warehouse"` (named transaction manager) and `Propagation.REQUIRED`
- Individual methods can override (some use `@Transactional(transactionManager = "warehouseTransactionManager", rollbackFor = Exception.class)`)
- **orgId scoping**: explicit parameter threading — `orgId` passed to every method, then to every DAO call
- **Input validation**: done inline (e.g., `if (program == null) throw new RuntimeException(...)`)
- **Cache invalidation**: pushed UP to the Thrift handler layer via `cacheEvictHelper`; service does not evict cache directly (it just saves to DB)
- **SELECT FOR UPDATE locking**: present as `lockProgram(orgId, programId)` — uses a native SQL `SELECT * FROM warehouse.program WHERE id=:id AND org_id=:orgId FOR UPDATE` via `genericQueryDao`. This is the existing advisory-lock-equivalent for preventing concurrent program modifications — and directly applicable to D-29 race mitigation.

---

## 4. DAO / Repository Pattern

### GenericDao (C7)
**File**: `/Users/anujgupta/IdeaProjects/shopbook-datamodel/src/main/java/com/capillary/commons/data/dao/GenericDao.java`

- `interface GenericDao<T, ID> extends JpaRepository<T, ID>, QueryDslPredicateExecutor<T>`
- Provides: `findById(ID)`, `findReferenceById(ID)`, `refresh(T)`, `merge(T)`, `saveAndFlush(T)`, `createNativeQuery(...)`, `createQuery()` (JPAQuery), `createDeleteClause(Predicate)`, `createUpdateClause(Predicate)`
- **Technology**: Spring Data JPA + QueryDSL (Querydsl `JPAQuery`/`JPADeleteClause`)

### PeProgramSlabDao (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeProgramSlabDao.java`

```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)
public interface PeProgramSlabDao extends GenericDao<ProgramSlab, ProgramSlabPK> {
    @Query("SELECT s FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2")
    List<ProgramSlab> findByProgram(int orgId, int programId);
    @Query("SELECT ps FROM ProgramSlab ps WHERE ps.pk.orgId = ?1 AND s.program.pk.id = ?2 and ps.serialNumber = ?3")
    ProgramSlab findByProgramSlabNumber(int orgId, int programId, int programSlabNumber);
    @Query("SELECT COUNT(*) FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2")
    Long findNumberOfSlabs(int orgId, int programId);
}
```

### BenefitsDao (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/BenefitsDao.java`

```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)
public interface BenefitsDao extends GenericDao<Benefits, Benefits.BenefitsPK> {
```

Key methods: `getBenefitConfigForProgram(orgId, programId, type)`, `getBenefitConfigById(orgId, id)`, `getBenefitConfigByName(orgId, programId, type, name)`, `findByPromotions(orgId, promotionIds)`.

**Pattern findings**:
- DAO `@Transactional` is `SUPPORTS` — they participate in the calling service's transaction or run without one
- `is_active` filter is **explicit** in every query where needed (e.g., `findByPromotions` adds `AND bs.isActive=1`) — no `@Where` automatic filter
- org_id is always the first parameter in JPQL `WHERE s.pk.orgId = ?1`

---

## 5. Exception Handling & Error Envelope

### Thrift Exception Type (C7)
**File**: `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/external/PointsEngineThriftExceptionCodes.java`

The single IDL-defined exception for the `PointsEngineRuleService` Thrift interface is `PointsEngineRuleServiceException`. This has a `statusCode` field (`setStatusCode(int)`).

**Standard exception mapping pattern** (C7, confirmed across all handler methods):
```java
} catch (ValidationException ex) {
    PointsEngineRuleServiceException e = new PointsEngineRuleServiceException(ex.getMessage());
    e.setStatusCode(400);
    throw e;
} catch (Exception ex) {
    PointsEngineRuleServiceException e = new PointsEngineRuleServiceException(ex.getMessage());
    e.setStatusCode(500);
    throw e;
}
```

No fine-grained Thrift exception hierarchy per method (e.g., no `NotFoundException` / `ConflictException`). The status code integer carries semantic meaning (400/500).

**New BenefitCategory exception codes needed**: The existing `PointsEngineThriftExceptionCodes` class defines 90xx series. New codes for BenefitCategory should use a new range (e.g., 91xx) to avoid collision.

---

## 6. Multi-Tenancy Enforcement

**C7 — No Hibernate @Filter / @Where**: Grep across the entire emf-parent codebase for `@Filter`, `@FilterDef`, `@Where` returns **zero results** in non-test Java files.

**Actual mechanism**: `ShardContext.set(orgId)` is called in `ExposedCallAspect` at the entry point of every Thrift method (via `@MDCData(orgId = "#orgId")`). This stores `orgId` in a `ThreadLocal`. The `DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)` annotation on `PointsEngineRuleService` routes to the `warehouse` JPA transaction manager. However, `orgId` itself is not auto-injected into DAO queries — every DAO method receives `orgId` as an explicit parameter.

**Evidence**:
- `ExposedCallAspect.java:98`: `ShardContext.set(orgId)` — sets ThreadLocal
- `BenefitsDao.java:23-28`: `WHERE b.pk.orgId = :orgId` — manual filter
- `PeProgramSlabDao.java:26`: `WHERE s.pk.orgId = ?1` — manual filter
- `PointsEngineRuleService.java:417-423`: `lockProgram` uses `WHERE org_id = :orgId` in native SQL

**Implication for new feature (C7)**: New `BenefitCategoryDao` and `BenefitCategorySlabMappingDao` MUST follow this convention. The `orgId` from the Thrift call parameter must be threaded explicitly to every DAO call. There is no framework-level safety net.

---

## 7. Timezone & JVM Default TZ

**C7 — JVM default TZ is NOT configured** in:
- `Dockerfile` (lines 10-31): no `-Duser.timezone` JVM argument
- `emf.properties`: no timezone entry
- `emf-local.properties`: no timezone entry
- `database.config.properties`: no `serverTimezone`
- `warehouse-database.properties`: no `serverTimezone`
- `application.properties` (integration test): no timezone config

**Conclusion**: JVM defaults to OS timezone of the container/host. The base Docker image (`crm/openjdk-base-image:75f1bde-14`) controls the OS timezone — unknown without inspecting that image, but historically Capillary India DCs run IST.

**Risk**: If JVM is IST, any `new Date()` used in timestamp fields will be in IST. For the D-24 pattern, the `Date ↔ i64 millis` conversion in the Thrift handler MUST use `Calendar.getInstance(TimeZone.getTimeZone("UTC"))` or `date.getTime()` directly (which is TZ-neutral — milliseconds since epoch are absolute). The `.getTime()` approach is safe; format-based parsing is not.

**Action for Phase 6 Architect**: ADR must document that `Date.getTime()` (milliseconds since epoch) is used for `i64` conversion — this is TZ-neutral because epoch millis are absolute. The risk is in `SimpleDateFormat`-based parsing, not in `getTime()`.

---

## 8. NFR-1 Baseline (OQ-33)

**No SLA metrics, rate limiters, or perf test harnesses found** for tier/slab list endpoints in emf-parent.

`PointsEngineRuleService.createOrUpdateSlab()` (lines 3655-3699):
- Fetches existing slab from DB
- Creates/updates via `saveAndFlush`
- Calls `updateStrategiesForNewSlab()` for new slabs
- No cache read; no cache write (cache is evicted at handler level)
- No apparent rate limiter

The existing `/benefits` list (`BenefitsDao.getAllBenefitsConfigForOrg`) issues a full table scan with org_id filter — no pagination, no limit. At the D-26 SMALL scale (≤50 rows), this is acceptable but confirms no existing SLA baseline exists.

**Verdict for OQ-33**: No measurable baseline. The 500ms P95 target in PRD §NFR-1 is unvalidated. At D-26 SMALL scale (<10 QPS, ≤50 rows), single-index JPA queries will easily fit under 50ms P95. The 500ms budget is very conservative.

---

## 9. Audit Field Pattern

**C7 — No `@PrePersist`, `@PreUpdate`, `@CreationTimestamp`, `@UpdateTimestamp`** found anywhere in emf-parent non-test Java files.

**Platform convention**: Audit fields are **set manually** in service code before save. Example from `PointsEngineRuleService.createOrUpdateSlab()` (line 3669-3671):
```java
slab = ProgramSlabBuilder
    .programSlab()
    .setPk(new ProgramSlabPK(program.getOrgId()))
    .setCreatedOn(new Date())
    .build();
```

The `created_by` is passed as `lastModifiedBy` parameter from the Thrift call (an `int` representing the user's ID, injected by intouch-api-v3 from `IntouchUser` principal).

**Pattern for `created_by` / `updated_by` (C7)**: Passed as explicit Thrift parameter `int lastModifiedBy` (e.g., `createOrUpdateStrategy(StrategyInfo, int programId, int orgId, int lastModifiedBy, long lastModifiedOn, String serverReqId)`). The intouch-api-v3 layer injects this from the authenticated `IntouchUser.principal` (user ID integer).

**For D-23 hybrid pattern**, the new entity setter code will be:
```java
if (isNew) {
    entity.setCreatedOn(new Date());
    entity.setCreatedBy(lastModifiedBy);
}
entity.setUpdatedOn(new Date());
entity.setUpdatedBy(lastModifiedBy);
// auto_update_time is DB-managed, never set in code
```

No existing entity has `updated_on` / `updated_by` — there is no code to copy from. Must be written from scratch.

---

## 10. Generic Routing Dispatchers

**C7 — No existing type dispatcher requires registration for BenefitCategory.categoryType = 'BENEFITS'**:

- `StrategyType.Type` enum: `POINT_ALLOCATION, SLAB_UPGRADE, POINT_EXPIRY, POINT_REDEMPTION_THRESHOLD, SLAB_DOWNGRADE, POINT_RETURN, EXPIRY_REMINDER, TRACKER, POINT_EXPIRY_EXTENSION` — no BENEFITS entry, no dispatch to add
- `PointsCategoryType` enum: `REGULAR_POINTS, TRACKERS, PROMISED_POINTS, EXTERNAL_TRIGGER_BASED_POINTS, ALTERNATE_CURRENCIES` — no BENEFITS entry, no dispatch to add
- `BenefitsType` enum: `VOUCHER, POINTS` — this is for the legacy entity, not the new feature
- `BenefitsAwardedStats.BenefitType` enum: `REWARDS, COUPONS, BADGES, TIER_UPGRADE, TIER_DOWNGRADE, TIER_RENEWAL, ENROL, OPTIN, PARTNER_PROGRAM, TAG_CUSTOMER, CUSTOMER_LABEL, TIER_UPGRADE_VIA_PARTNER_PROGRAM, TIER_RENEWAL_VIA_PARTNER_PROGRAM` — event outcomes, no BENEFITS_CATEGORY entry, no dispatch to add
- `capillary.api.thrift.EntityType` (imported in `EMFThriftAdapter`): unknown without inspecting that library — LOW risk that BenefitCategory needs to be registered there; it is a config entity, not an event entity

**Conclusion (C6)**: New BenefitCategory feature requires NO registration in any existing dispatcher or enum. It is a standalone config entity in a new namespace.

---

## Answers to Phase 4 Residual Questions

### OQ-33 (NFR baseline)
No existing performance baseline for tier/slab list or benefits list endpoints. No SLA metrics or perf tests found. The 500ms P95 PRD target is unvalidated but easily achievable at D-26 SMALL scale. Recommend: set P95 < 100ms for read (single index scan, ≤50 rows) and P95 < 300ms for write (single INSERT + optional cascade).

### OQ-35 (Thrift handler template)
**Canonical template picked**: `PointsEngineRuleConfigThriftImpl` at `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`

The new BenefitCategory Thrift methods should be **added as new methods on the existing `PointsEngineRuleConfigThriftImpl`** (which implements `PointsEngineRuleService.Iface` and is already `@ExposedCall(thriftName = "pointsengine-rules")`). This aligns with the thrift-ifaces-pointsengine-rules analysis which found BenefitsConfigData CRUD already lives in the same service. No new handler class is needed.

New methods should:
1. Carry `@Override @Trace(dispatcher = true) @MDCData(orgId = "#orgId", requestId = "#serverReqId")` annotations
2. Pattern: try → delegate to editor → cache evict → build Thrift response; catch ValidationException → 400; catch Exception → 500
3. `lastModifiedBy` passed as `int` parameter

### OQ-38 (JVM default TZ)
JVM default TZ is **not configured** in Dockerfile or any config file. The system defaults to the OS timezone of the openjdk-base-image container. Confirm with ops team — almost certainly IST for India DCs. **Mitigation in code**: use `date.getTime()` (epoch ms, TZ-neutral) for `Date → i64` conversion; use `new Date(millis)` for `i64 → Date` reverse. Do NOT use `SimpleDateFormat` without explicit UTC timezone.

### OQ-41 (Thrift field naming for timestamps — emf repo view)
**emf.thrift convention**: `*InMillis` suffix — e.g., `createdOnInMillis`, `eventTimeInMillis`, `joinedOnDateInMillis`, `pointsExpiryDateinMillis`.
**pointsengine-rules.thrift convention** (cross-reference): bare camelCase `createdOn`, `updatedOn` (no suffix).
**Recommendation (Phase 7 to confirm)**: Use bare `createdOn` / `updatedOn` in the new IDL since the new service lives in `pointsengine-rules.thrift`, matching that file's local convention.

### C-25 (G-07 multi-tenancy mechanism)
**Mechanism is by convention, not framework**. No `@Filter`/`@FilterDef`/`@Where`. orgId is passed as a Thrift parameter → set in `ShardContext` ThreadLocal by `ExposedCallAspect` → threaded explicitly as `int orgId` parameter into every DAO method → manually added as `WHERE pk.orgId = :orgId` in every JPQL query. New feature MUST follow this — no automatic protection if a developer forgets to add the orgId filter.

---

## QUESTIONS FOR USER

1. **OQ-38 (HIGH, C4)**: What is the JVM timezone on EMF production containers? The Dockerfile has no `-Duser.timezone`. If the base image (`crm/openjdk-base-image:75f1bde-14`) sets TZ=Asia/Kolkata (IST), any `SimpleDateFormat`-based date parsing without explicit UTC timezone will silently produce wrong timestamps. Please confirm with infra team. Code will use `date.getTime()` (safe), but any log-parsing or date-from-string operations need explicit UTC.

2. **C2 (under-confirmed)**: The `PointsEngineRuleServiceException.setStatusCode(int)` field — is this field present in the Thrift IDL for this exception? The thrift-ifaces analysis CONFIRMS it is — `PointsEngineRuleServiceException { 1: required string errorMessage; 2: optional i32 statusCode; }` at lines 10-13. So `setStatusCode` IS serialized. This resolves the initial concern.

3. **C3 (OQ-34 authz, not fully answered)**: The new Thrift methods will accept `lastModifiedBy` as an `int`. Who validates that the caller is authorized to pass that userId for that org? Is there an existing interceptor in intouch-api-v3 that validates the `IntouchUser.orgId` matches the request `orgId`? Confirm auth guard is in intouch-api-v3 (Phase 6 Architect scope).

---

## ASSUMPTIONS MADE

1. **C6**: The new BenefitCategory methods will be added to the existing `PointsEngineRuleConfigThriftImpl` handler in the `pointsengine-emf` module (not `emf` module), following the pattern of the existing `createOrUpdateBenefits` etc. methods. The emf module handles event evaluation; pointsengine-emf handles loyalty config CRUD.

2. **C6**: Schema migration home is cc-stack-crm repo, not emf-parent Flyway. emf-parent integration tests pull schemas from `cc-stack-crm` snapshot directory. New `benefit_categories.sql` and `benefit_category_slab_mapping.sql` should be created in cc-stack-crm following existing naming (flat SQL files, no Flyway V-numbering).

3. **C5**: The `benefit_categories` and `benefit_category_slab_mapping` entities will NOT need `is_active` filter in an `@Where` clause — consistent with the rest of the codebase. The `is_active` filter will be added explicitly in each DAO query method that needs it (e.g., `findActiveByOrgIdAndProgramId`).

4. **C5**: `int lastModifiedBy` represents the user's numeric ID (from `IntouchUser`), stored as `created_by INT` / `updated_by INT` in the DB — matching the `BenefitsAwardedStats.createdBy` pattern (int, not String/UUID). **Cross-reference conflict**: D-23 states `created_by VARCHAR(...)` in the schema, and thrift-ifaces analysis Q-T-01 recommends `string createdBy` for the IDL. Phase 6 Architect must resolve this inconsistency: use `int` user ID (matches existing EMF pattern) OR `string` username (matches platform audit pattern D-23). Recommend re-reading D-23 carefully in Phase 6.

---

## Files Referenced (canonical list for Phase 6 Architect)

**Entity Layer**:
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramSlab.java` — FK target entity
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/Benefits.java` — legacy audit pattern reference
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PointCategory.java` — best category-entity pattern (has `@UniqueConstraint` we're not copying)
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/PartnerProgramTierSyncConfiguration.java` — junction-table entity pattern
- `/Users/anujgupta/IdeaProjects/shopbook-datamodel/src/main/java/com/capillary/commons/data/OrgEntityIntegerPKBase.java` — PK base class
- `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/data/model/BenefitsAwardedStats.java` — has `created_on`/`created_by`/`last_updated_on` triple (closest to D-23 hybrid)

**DAO Layer**:
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/BenefitsDao.java` — `GenericDao` pattern template
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/PeProgramSlabDao.java` — slab DAO template
- `/Users/anujgupta/IdeaProjects/shopbook-datamodel/src/main/java/com/capillary/commons/data/dao/GenericDao.java` — base DAO interface

**Service / Transaction Layer**:
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/PointsEngineRuleService.java` — `@Transactional(value="warehouse")` + `lockProgram` SELECT FOR UPDATE pattern
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/editor/PointsEngineRuleEditorImpl.java` — editor/facade layer

**Thrift Handler Layer**:
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java` — **canonical template** (OQ-35)
- `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/system/ExposedCall.java` — Thrift registration annotation
- `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/utils/ExposedCallAspect.java` — AOP interceptor (ShardContext, ThreadLocalCache, MDC)
- `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/api/hibernate/ShardContext.java` — ThreadLocal org_id carrier

**Exception Handling**:
- `/Users/anujgupta/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/external/PointsEngineThriftExceptionCodes.java` — error code registry (90xx series; new should use 91xx)
- `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/api/exception/ValidationException.java` — validation exception type

**Cache**:
- `/Users/anujgupta/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/handler/CacheEvictHelper.java` — `@CacheEvict` Spring cache eviction pattern (Redis, ONE_DAY region)

**Schema DDL (integration-test snapshots, actual in cc-stack-crm)**:
- `/Users/anujgupta/IdeaProjects/emf-parent/integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/program_slabs.sql` — FK target DDL
- `/Users/anujgupta/IdeaProjects/emf-parent/integration-test/src/test/resources/cc-stack-crm/schema/dbmaster/warehouse/benefits.sql` — legacy audit column reference

**Thrift IDL**:
- `/Users/anujgupta/IdeaProjects/emf-parent/emf-all/scripts/emf.thrift` — timestamp naming convention (`*InMillis` suffix confirmed for emf.thrift — different from pointsengine_rules.thrift)

**Deployment**:
- `/Users/anujgupta/IdeaProjects/emf-parent/Dockerfile` — confirms no `-Duser.timezone` JVM arg (OQ-38 evidence)
