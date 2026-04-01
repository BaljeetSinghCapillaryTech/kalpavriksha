# 03 — Designer: Tier & Benefit CRUD + Maker-Checker APIs

> Phase: Designer (03)
> Date: 2026-04-01
> Input: 00-ba.md, 01-architect.md, 02-analyst.md, session-memory.md, GUARDRAILS.md
> Output feeds: 04-qa.md

---

## Pattern Decisions

### DAO Pattern
Using `BaseMongoDaoImpl<T extends BaseMongoEntity>` (from `emf/` module, 14+ existing implementations).
Each DAO interface defines `DATABASE_NAME` and `COLLECTION_NAME` as interface constants. Implementations use `@Component("beanName")` and inject `MongoDataSourceManager` via `@Autowired` field injection. Every method takes `Integer orgId` as first parameter (matching `ShardContext.getOrgId()` which returns `int`).

**Discovered from**: `OrgConfigDaoImpl.java`, `UnifiedPromotionDaoImpl.java`, `OrgConfigDao.java`, `UnifiedPromotionDao.java`

### Service Pattern
Using `@Service` annotation with `@Autowired` field injection. No base service class. Services return `ResponseEntity<T>` or domain objects. Located in `RESTEndpoint/Service/impl/` package.

**Discovered from**: `ProgramsApiService.java`, `ValidatorService.java`, `BulkOrgConfigUpdateService.java`

### Controller Pattern
Existing controllers use `@Controller` (Swagger codegen). New hand-written controllers will use `@RestController` per Analyst recommendation — the existing `@Controller` pattern is because those classes implement Swagger-generated interfaces with `@ResponseBody`. New controllers are hand-written and serve JSON directly.

**Discovered from**: `ProgramsApiController.java` (Swagger-generated, `@Controller`), `MilestoneConfigController.java` (hand-written, `@Controller` with `@ResponseBody`), `OrgConfigController.java`

### Validator Pattern
Using `Validator<T, R>` generic interface with `R validate(T request)` method. `PromotionValidator extends Validator<PromotionValidatorRequest, ValidatorResponse>`. Factory class annotated `@Component` returns `List<PromotionValidator>` per `ValidatorTypes` enum. Each validator is a `@Component` injected via `@Autowired` field injection.

**Discovered from**: `Validator.java`, `PromotionValidator.java`, `ValidatorFactory.java`, `ValidatorResponse.java`

### Model/Entity Pattern
MongoDB models extend `BaseMongoEntity` (empty class, `implements Serializable`). Fields use `@BsonProperty` annotations and `@BsonId` for `_id`. No Lombok. Manual getters/setters. Manual builders where needed.

**Discovered from**: `BaseMongoEntity.java`, `UnifiedPromotion.java`

### Exception Pattern
Exceptions extend `RuntimeException` with `@ResponseStatus` annotation. `GlobalExceptionHandler` (`@RestControllerAdvice`) handles specific exception types returning `ResponseEntity`.

**Discovered from**: `RequestValidationException.java`, `GlobalExceptionHandler.java`

### Component Scanning
`AppConfig.java` scans `com.capillary.shopbook.pointsengine.RESTEndpoint` — all new controllers, services, validators under this package will be auto-detected. DAOs in `emf/` module are scanned via `PeConfig.java` which covers `com.capillary.shopbook.springdata.mongodb`.

**Discovered from**: `AppConfig.java`, `PeConfig.java`

### Redis/RedisTemplate
`RedisTemplate<String, Object>` bean named `"redisTemplate"` is exposed by `ApplicationCacheConfig`. Uses `StringRedisSerializer` for keys. Available for `@DistributedLock` via `setIfAbsent(key, value, timeout, unit)`.

**Discovered from**: `ApplicationCacheConfig.java` (line 181-188)

### Test Pattern
JUnit 4 (`@Test`, `@Before`, `@BeforeClass`). Extends `junit.framework.TestCase` in some cases. Mockito (`@Mock`, `@InjectMocks`, `MockitoAnnotations.openMocks(this)`, `MockedStatic`). Test classes in separate `*-ut` module.

**Discovered from**: `ProgramConfigKeysValidatorFactoryTest.java`, `ValidatorFactoryTest.java`

---

## Abstractions

| Type | Purpose | Module |
|------|---------|--------|
| `ConfigBaseDocument` | Abstract base for tier/benefit config documents with shared fields | emf |
| `ConfigStatus` | Enum for document lifecycle states | emf |
| `ConfigAction` | Enum for actions that trigger state transitions | emf |
| `ConfigValidator<T>` | Generic validator interface for config entities | pointsengine-emf |
| `ConfigValidatorRequest` | Base request object carrying entity + context for validation | pointsengine-emf |
| `ConfigValidationResult` | Aggregated field-level validation errors | pointsengine-emf |
| `ConfigStatusTransitionValidator` | EnumMap-based state machine for valid transitions | pointsengine-emf |
| `VersioningHelper` | Shared parentId/version management logic | pointsengine-emf |
| `@DistributedLock` | Annotation for Redis-backed distributed locking | pointsengine-emf |
| `DistributedLockAspect` | AOP aspect implementing the lock | pointsengine-emf |
| `TierConfig` | MongoDB document for tier configuration | emf |
| `BenefitConfig` | MongoDB document for benefit configuration | emf |
| `TierConfigDao` / `TierConfigDaoImpl` | DAO for tier_configs collection | emf |
| `BenefitConfigDao` / `BenefitConfigDaoImpl` | DAO for benefit_configs collection | emf |
| `TierConfigService` | Business logic for tier CRUD + maker-checker | pointsengine-emf |
| `BenefitConfigService` | Business logic for benefit CRUD + maker-checker | pointsengine-emf |
| `TierConfigController` | REST endpoints for /api/v1/tiers | pointsengine-emf |
| `BenefitConfigController` | REST endpoints for /api/v1/benefits | pointsengine-emf |
| `TierValidatorFactory` | Factory producing ordered validator chains for tier operations | pointsengine-emf |
| `BenefitValidatorFactory` | Factory producing ordered validator chains for benefit operations | pointsengine-emf |
| `ConfigConflictException` | Exception for 409 Conflict responses | pointsengine-emf |
| `ConfigValidationException` | Exception for 422 Validation responses | pointsengine-emf |
| `ConfigDiffResult` | Field-level diff between two config documents for US-11 | pointsengine-emf |

---

## Dependency Direction

```
TierConfigController ──> TierConfigService ──> TierConfigDao
       │                       │                     │
       │                       │                     v
       │                       │              ConfigBaseDocument / TierConfig
       │                       │
       │                       ├──> TierValidatorFactory ──> [tier validators]
       │                       │                                    │
       │                       │                                    v
       │                       │                             BenefitConfigDao  (NOT BenefitConfigService)
       │                       │
       │                       ├──> ConfigStatusTransitionValidator
       │                       ├──> VersioningHelper
       │                       └──> @DistributedLock (AOP)
       │
       v
BenefitConfigController ──> BenefitConfigService ──> BenefitConfigDao
                                   │                        │
                                   │                        v
                                   │                 ConfigBaseDocument / BenefitConfig
                                   │
                                   ├──> BenefitValidatorFactory ──> [benefit validators]
                                   │                                       │
                                   │                                       v
                                   │                                TierConfigDao  (NOT TierConfigService)
                                   │
                                   ├──> ConfigStatusTransitionValidator
                                   ├──> VersioningHelper
                                   └──> @DistributedLock (AOP)
```

**Circular dependency resolution**: `TierConfigService` validates linked benefits via `BenefitConfigDao` (not `BenefitConfigService`). `BenefitConfigService` validates linked tiers via `TierConfigDao` (not `TierConfigService`). The cross-entity dependency is at the DAO level only. No service-to-service injection.

---

## Interface Definitions

### 1. ConfigBaseDocument (abstract class)

- **Extends**: `BaseMongoEntity`
- **Annotations**: None (base class, no `@Document`)
- **Package**: `com.capillary.shopbook.springdata.mongodb.model.config`
- **Discovered from**: `BaseMongoEntity.java`, `UnifiedPromotion.java`
- **Imports**: `org.bson.codecs.pojo.annotations.BsonId`, `org.bson.codecs.pojo.annotations.BsonProperty`, `org.bson.types.ObjectId`, `java.time.Instant`
- **Maven dependency**: `org.mongodb:bson` — already in module pom.xml (used by all existing Mongo models)

```java
public abstract class ConfigBaseDocument extends BaseMongoEntity {

    // GUARDRAIL G-07: orgId is Integer to match ShardContext.getOrgId() (int)
    @BsonId
    private ObjectId id;

    @BsonProperty("entityId")
    private String entityId;         // Immutable business ID (UUID), persists across versions

    @BsonProperty("orgId")
    private Integer orgId;           // GUARDRAIL G-07: Integer, not Long — matches ShardContext

    @BsonProperty("programId")
    private Long programId;

    @BsonProperty("parentId")
    private String parentId;         // ObjectId.toHexString() of active parent (null for new entities)

    @BsonProperty("version")
    private Integer version;         // Starts at 1, incremented on edit of ACTIVE

    @BsonProperty("status")
    private String status;           // ConfigStatus.name()

    @BsonProperty("comments")
    private String comments;         // Review comment, max 150 chars

    @BsonProperty("createdOn")
    private Instant createdOn;       // GUARDRAIL G-01: Instant (UTC)

    @BsonProperty("createdBy")
    private String createdBy;

    @BsonProperty("lastModifiedOn")
    private Instant lastModifiedOn;  // GUARDRAIL G-01: Instant (UTC)

    @BsonProperty("lastModifiedBy")
    private String lastModifiedBy;

    // Getters and setters (manual, no Lombok — per G-12.2)
}
```

### 2. TierConfig

- **Extends**: `ConfigBaseDocument`
- **Annotations**: None (BSON POJO codec, no Spring Data `@Document` — following `UnifiedPromotion` pattern)
- **Package**: `com.capillary.shopbook.springdata.mongodb.model.config`
- **Discovered from**: `UnifiedPromotion.java` (extends `BaseMongoEntity`, uses `@BsonProperty`)
- **Imports**: `org.bson.codecs.pojo.annotations.BsonProperty`, `java.math.BigDecimal`, `java.time.Instant`, `java.util.List`, `java.util.Map`
- **Maven dependency**: already in module pom.xml

```java
public class TierConfig extends ConfigBaseDocument {

    @BsonProperty("name")
    private String name;

    @BsonProperty("description")
    private String description;

    @BsonProperty("color")
    private String color;                    // Hex color code

    @BsonProperty("serialNumber")
    private Integer serialNumber;            // Tier rank in hierarchy

    @BsonProperty("eligibility")
    private TierEligibility eligibility;

    @BsonProperty("validity")
    private TierValidity validity;

    @BsonProperty("renewal")
    private TierRenewal renewal;

    @BsonProperty("downgrade")
    private TierDowngrade downgrade;

    @BsonProperty("upgrade")
    private TierUpgrade upgrade;

    @BsonProperty("nudge")
    private TierNudge nudge;

    @BsonProperty("linkedBenefits")
    private List<LinkedBenefit> linkedBenefits;

    // Getters and setters
}
```

**Embedded types** (all in `com.capillary.shopbook.springdata.mongodb.model.config`):

```java
public class TierEligibility {
    private String kpiType;              // CURRENT_POINTS, LIFETIME_POINTS, LIFETIME_PURCHASES, TRACKER_VALUE
    private BigDecimal threshold;
    private List<SecondaryCriterion> secondaryCriteria;
}

public class SecondaryCriterion {
    private String kpiType;
    private BigDecimal threshold;
}

public class TierValidity {
    private String type;                 // FIXED_DURATION, REGISTRATION_DATE, FIXED_DATE
    private Integer periodInDays;
    private Instant fixedDate;           // GUARDRAIL G-01
}

public class TierRenewal {
    private RenewalConditions conditions;
    private String schedule;             // ANNUAL, SEMI_ANNUAL
    private Integer durationInDays;
}

public class RenewalConditions {
    private BigDecimal retentionAmount;
    private BigDecimal retentionPoints;
    private BigDecimal retentionTracker;
    private Integer retentionVisits;
}

public class TierDowngrade {
    private String targetTierId;         // tierId of target, or "NONE"
    private String schedule;
    private Integer gracePeriodInDays;
    private Boolean validateOnReturnTransaction;
}

public class TierUpgrade {
    private String mode;                 // EAGER, DYNAMIC, LAZY
    private BigDecimal bonusPoints;
}

public class TierNudge {
    private Boolean enabled;
    private List<Integer> reminderBeforeDays;
    private Map<String, String> templateReferences;  // channel -> templateId
}

public class LinkedBenefit {
    private String benefitId;
    private Map<String, Object> parameters;
}
```

### 3. BenefitConfig

- **Extends**: `ConfigBaseDocument`
- **Annotations**: None (BSON POJO codec)
- **Package**: `com.capillary.shopbook.springdata.mongodb.model.config`
- **Discovered from**: `UnifiedPromotion.java`
- **Imports**: same as TierConfig
- **Maven dependency**: already in module pom.xml

```java
public class BenefitConfig extends ConfigBaseDocument {

    @BsonProperty("name")
    private String name;

    @BsonProperty("type")
    private String type;                 // POINTS_MULTIPLIER, FLAT_POINTS_AWARD, COUPON_ISSUANCE,
                                         // BADGE_AWARD, FREE_SHIPPING, CUSTOM

    @BsonProperty("category")
    private String category;             // EARNING, REDEMPTION, COUPON, BADGE, COMMUNICATION, CUSTOM

    @BsonProperty("triggerEvent")
    private String triggerEvent;         // TIER_UPGRADE, TIER_RENEWAL, TRANSACTION, BIRTHDAY, MANUAL

    @BsonProperty("description")
    private String description;

    @BsonProperty("parameters")
    private Map<String, Object> parameters;  // Type-specific params

    @BsonProperty("linkedTiers")
    private List<LinkedTier> linkedTiers;

    // Getters and setters
}
```

**Embedded type**:
```java
public class LinkedTier {
    private String tierId;
    private Map<String, Object> parameters;  // Per-tier parameter overrides
}
```

### 4. ConfigStatus (enum)

- **Extends**: none
- **Package**: `com.capillary.shopbook.springdata.mongodb.enums`
- **Discovered from**: `PromotionStatus` enum pattern referenced in `UnifiedPromotion` / session-memory
- **Maven dependency**: none needed

```java
public enum ConfigStatus {
    DRAFT,
    PENDING_APPROVAL,
    ACTIVE,
    PAUSED,
    STOPPED,
    SNAPSHOT;

    public boolean isTerminal() {
        return this == STOPPED || this == SNAPSHOT;
    }

    public boolean isEditable() {
        return this == DRAFT;
    }
}
```

### 5. ConfigAction (enum)

- **Package**: `com.capillary.shopbook.springdata.mongodb.enums`
- **Discovered from**: `PromotionAction` enum pattern referenced in session-memory

```java
public enum ConfigAction {
    SUBMIT_FOR_APPROVAL,
    APPROVE,
    REJECT,
    PAUSE,
    STOP,
    RESUME;
}
```

### 6. TierConfigDao (interface)

- **Extends**: none (DAO interfaces in this codebase do not extend a common interface)
- **Annotations**: none
- **Package**: `com.capillary.shopbook.springdata.mongodb.dao`
- **Discovered from**: `OrgConfigDao.java`, `UnifiedPromotionDao.java`
- **Imports**: `org.bson.conversions.Bson`, `com.mongodb.client.result.UpdateResult`, `java.util.List`, `java.util.Optional`
- **Maven dependency**: already in module pom.xml

```java
public interface TierConfigDao {

    String DATABASE_NAME = "emf";
    String COLLECTION_NAME = "tier_configs";

    void save(Integer orgId, TierConfig tierConfig);

    TierConfig replace(Integer orgId, TierConfig tierConfig);

    List<TierConfig> find(Integer orgId, Bson filter);

    List<TierConfig> find(Integer orgId, Bson filter, Bson sort, Integer limit);

    // GUARDRAIL G-02.2: Optional for single-value return
    Optional<TierConfig> findOne(Integer orgId, Bson filter);

    List<TierConfig> find(Integer orgId, Bson filter, Integer offset, Integer limit, Bson sort);

    UpdateResult update(Integer orgId, Bson filter, List<Bson> updates);

    long count(Integer orgId, Bson filter);
}
```

### 7. TierConfigDaoImpl

- **Extends**: `BaseMongoDaoImpl<TierConfig>`
- **Implements**: `TierConfigDao`
- **Annotations**: `@Component("tierConfigDao")`
- **Package**: `com.capillary.shopbook.springdata.mongodb.dao.impl`
- **Discovered from**: `OrgConfigDaoImpl.java`, `UnifiedPromotionDaoImpl.java`
- **Imports**: `com.capillary.shopbook.springdata.mongodb.core.MongoDataSourceManager`, `com.capillary.shopbook.springdata.mongodb.core.MongoTemplate`, `com.mongodb.client.model.Filters`, `com.mongodb.client.model.IndexOptions`, `com.mongodb.client.model.Indexes`, `org.bson.BsonDocument`, `org.bson.BsonInt32`
- **Maven dependency**: already in module pom.xml

```java
@Component("tierConfigDao")
public class TierConfigDaoImpl extends BaseMongoDaoImpl<TierConfig> implements TierConfigDao {

    private final Logger logger = LoggerFactory.getLogger(this.getClass());

    @Autowired
    MongoDataSourceManager mongoDbConfiguration;

    @PostConstruct
    public void setUp();                      // Creates indexes on all shards

    @Override
    protected MongoDataSourceManager getDataSourceManager();

    @Override
    protected String getDatabase();           // returns DATABASE_NAME

    @Override
    protected String getCollection();         // returns COLLECTION_NAME

    @Override
    public void save(Integer orgId, TierConfig tierConfig);

    @Override
    public TierConfig replace(Integer orgId, TierConfig tierConfig);

    @Override
    public List<TierConfig> find(Integer orgId, Bson filter);

    @Override
    public List<TierConfig> find(Integer orgId, Bson filter, Bson sort, Integer limit);

    @Override
    public Optional<TierConfig> findOne(Integer orgId, Bson filter);  // G-02.2

    @Override
    public List<TierConfig> find(Integer orgId, Bson filter, Integer offset, Integer limit, Bson sort);

    @Override
    public UpdateResult update(Integer orgId, Bson filter, List<Bson> updates);

    @Override
    public long count(Integer orgId, Bson filter);
}
```

**Indexes created in `setUp()`**:
1. `{ orgId: 1, programId: 1, entityId: 1, status: 1 }` — primary query
2. `{ orgId: 1, programId: 1, status: 1, serialNumber: 1 }` — list by rank
3. `{ orgId: 1, entityId: 1, status: 1 }` — lookup by tierId
4. `{ orgId: 1, programId: 1, name: 1, status: 1 }` — uniqueness

### 8. BenefitConfigDao (interface)

- **Extends**: none
- **Package**: `com.capillary.shopbook.springdata.mongodb.dao`
- **Discovered from**: `OrgConfigDao.java`, `UnifiedPromotionDao.java`
- **Maven dependency**: already in module pom.xml

```java
public interface BenefitConfigDao {

    String DATABASE_NAME = "emf";
    String COLLECTION_NAME = "benefit_configs";

    void save(Integer orgId, BenefitConfig benefitConfig);

    BenefitConfig replace(Integer orgId, BenefitConfig benefitConfig);

    List<BenefitConfig> find(Integer orgId, Bson filter);

    List<BenefitConfig> find(Integer orgId, Bson filter, Bson sort, Integer limit);

    Optional<BenefitConfig> findOne(Integer orgId, Bson filter);  // G-02.2

    List<BenefitConfig> find(Integer orgId, Bson filter, Integer offset, Integer limit, Bson sort);

    UpdateResult update(Integer orgId, Bson filter, List<Bson> updates);

    long count(Integer orgId, Bson filter);
}
```

### 9. BenefitConfigDaoImpl

- **Extends**: `BaseMongoDaoImpl<BenefitConfig>`
- **Implements**: `BenefitConfigDao`
- **Annotations**: `@Component("benefitConfigDao")`
- **Package**: `com.capillary.shopbook.springdata.mongodb.dao.impl`
- **Discovered from**: `OrgConfigDaoImpl.java`, `UnifiedPromotionDaoImpl.java`
- **Maven dependency**: already in module pom.xml

Same structural pattern as `TierConfigDaoImpl`.

**Indexes created in `setUp()`**:
1. `{ orgId: 1, programId: 1, entityId: 1, status: 1 }` — primary query
2. `{ orgId: 1, programId: 1, status: 1 }` — list for program
3. `{ orgId: 1, programId: 1, name: 1, status: 1 }` — uniqueness
4. `{ orgId: 1, programId: 1, type: 1, status: 1 }` — filter by type
5. `{ orgId: 1, "linkedTiers.tierId": 1 }` — find benefits for a tier

### 10. ConfigValidator (generic interface)

- **Extends**: `Validator<ConfigValidatorRequest<T>, ConfigValidationResult>` (extends the existing generic `Validator<T, R>` interface)
- **Annotations**: none (interface)
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.Interfaces`
- **Discovered from**: `Validator.java`, `PromotionValidator.java`
- **Maven dependency**: none needed

```java
public interface ConfigValidator<T extends ConfigBaseDocument>
        extends Validator<ConfigValidatorRequest<T>, ConfigValidationResult> {

    @Override
    ConfigValidationResult validate(ConfigValidatorRequest<T> request);
}
```

### 11. ConfigValidatorRequest

- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.models`
- **Discovered from**: `PromotionValidatorRequest.java` (carries promotion + context)

```java
public class ConfigValidatorRequest<T extends ConfigBaseDocument> {

    private final T entity;                  // The config being validated
    private final T existingEntity;          // Current active version (null for creates)
    private final Integer orgId;             // GUARDRAIL G-07: always present
    private final Long programId;
    private final ConfigAction action;       // CREATE, UPDATE, STATUS_CHANGE, REVIEW

    public ConfigValidatorRequest(T entity, T existingEntity,
                                  Integer orgId, Long programId, ConfigAction action);

    // Getters only (immutable)
}
```

### 12. ConfigValidationResult

- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.models`
- **Discovered from**: `ValidatorResponse.java` (status + responseCode + responseMessage). Extended with field-level detail per BA requirements.

```java
public class ConfigValidationResult {

    private boolean valid;
    private List<FieldError> errors;         // GUARDRAIL G-06.3: structured errors

    public ConfigValidationResult();

    public boolean isValid();

    public List<FieldError> getErrors();     // GUARDRAIL G-02.1: never null, returns empty list

    public void addError(String field, String code, String message);

    public void merge(ConfigValidationResult other);

    public static ConfigValidationResult success();

    public static ConfigValidationResult failure(String field, String code, String message);

    // --- Inner class ---
    public static class FieldError {
        private final String field;
        private final String code;
        private final String message;

        public FieldError(String field, String code, String message);

        // Getters only
    }
}
```

### 13. ConfigStatusTransitionValidator

- **Annotations**: `@Component`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.config`
- **Discovered from**: `StatusTransitionValidator` in intouch-api-v3 (EnumMap pattern, session-memory)
- **Maven dependency**: none needed

```java
@Component
public class ConfigStatusTransitionValidator {

    // Initialized in constructor or static block
    private final EnumMap<ConfigStatus, Set<ConfigAction>> allowedTransitions;

    /**
     * State machine:
     *   DRAFT           -> SUBMIT_FOR_APPROVAL
     *   PENDING_APPROVAL -> APPROVE, REJECT
     *   ACTIVE          -> PAUSE, STOP
     *   PAUSED          -> RESUME, STOP
     *   STOPPED         -> (none — terminal)
     *   SNAPSHOT        -> (none — terminal)
     */

    public boolean isAllowed(ConfigStatus currentStatus, ConfigAction action);

    public ConfigStatus getTargetStatus(ConfigStatus currentStatus, ConfigAction action);

    // Returns ACTIVE for APPROVE/RESUME, DRAFT for REJECT,
    // PENDING_APPROVAL for SUBMIT_FOR_APPROVAL, PAUSED for PAUSE, STOPPED for STOP
}
```

### 14. VersioningHelper

- **Annotations**: `@Component`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
- **Discovered from**: `UnifiedPromotionFacade` approval flow (session-memory)

```java
@Component
public class VersioningHelper {

    /**
     * Create a new draft from an active entity (edit-of-active scenario).
     * Sets parentId = active._id.toHexString(), version = active.version + 1, status = DRAFT.
     * Returns the new draft entity — does NOT persist.
     */
    <T extends ConfigBaseDocument> T createDraftFromActive(T active, T updatedFields);

    /**
     * Apply approval to a new entity (parentId is null).
     * Transitions PENDING_APPROVAL -> ACTIVE.
     * Returns updated entity — does NOT persist.
     */
    <T extends ConfigBaseDocument> T approveNew(T pendingEntity, String comment);

    /**
     * Apply approval to an edit (parentId is not null).
     * Returns a pair: parent updated to SNAPSHOT, draft updated to ACTIVE.
     * Does NOT persist — caller handles saves.
     */
    <T extends ConfigBaseDocument> ApprovalResult<T> approveEdit(T parent, T draft, String comment);

    /**
     * Apply rejection. PENDING_APPROVAL -> DRAFT. Retains parentId and version.
     */
    <T extends ConfigBaseDocument> T reject(T pendingEntity, String comment);

    // --- Inner class ---
    public static class ApprovalResult<T> {
        private final T archivedParent;   // status = SNAPSHOT
        private final T activatedDraft;   // status = ACTIVE (or PAUSED if parent was PAUSED)

        public ApprovalResult(T archivedParent, T activatedDraft);
        // Getters
    }
}
```

### 15. @DistributedLock (annotation)

- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.annotations`
- **Discovered from**: `@Lockable` in intouch-api-v3 (session-memory)
- **Maven dependency**: none needed (standard Spring AOP)

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface DistributedLock {

    /**
     * SpEL expression for the lock key.
     * Example: "'lock_tier_status_' + #orgId + '_' + #tierId"
     */
    String key();

    /** Lock TTL in milliseconds. Default 300,000 (5 minutes). */
    long ttl() default 300_000;

    /** Max time to wait for lock acquisition in milliseconds. Default 5,000. */
    long acquireTime() default 5_000;
}
```

### 16. DistributedLockAspect

- **Annotations**: `@Aspect`, `@Component`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.annotations`
- **Discovered from**: `@Lockable` AOP pattern in intouch-api-v3 (session-memory). Uses `RedisTemplate` per Analyst recommendation (NOT `RedisCacheManager` get/putIfAbsent).
- **Imports**: `org.aspectj.lang.ProceedingJoinPoint`, `org.aspectj.lang.annotation.Around`, `org.aspectj.lang.annotation.Aspect`, `org.springframework.data.redis.core.RedisTemplate`
- **Maven dependency**: `spring-data-redis` — already in module (used by `ApplicationCacheConfig`)

```java
@Aspect
@Component
public class DistributedLockAspect {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    /**
     * Around advice for @DistributedLock.
     * Uses RedisTemplate.opsForValue().setIfAbsent(key, value, ttl, TimeUnit.MILLISECONDS)
     * for atomic lock acquisition (SET NX PX pattern).
     *
     * On failure to acquire: throws ConfigConflictException("Resource is locked by another operation").
     * On completion: deletes the lock key in a finally block.
     *
     * GUARDRAIL G-10.2: No I/O inside lock — lock wraps the business method call only.
     */
    @Around("@annotation(distributedLock)")
    public Object around(ProceedingJoinPoint joinPoint, DistributedLock distributedLock)
            throws Throwable;
}
```

### 17. ConfigConflictException

- **Extends**: `RuntimeException`
- **Annotations**: `@ResponseStatus(HttpStatus.CONFLICT)`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Exceptions`
- **Discovered from**: `RequestValidationException.java`
- **Maven dependency**: none needed

```java
@ResponseStatus(HttpStatus.CONFLICT)
public class ConfigConflictException extends RuntimeException {

    private final String errorCode;

    public ConfigConflictException(String message, String errorCode);

    public String getErrorCode();
}
```

### 18. ConfigValidationException

- **Extends**: `RuntimeException`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Exceptions`
- **Discovered from**: `RequestValidationException.java`
- **Maven dependency**: none needed

```java
public class ConfigValidationException extends RuntimeException {

    private final ConfigValidationResult validationResult;

    public ConfigValidationException(ConfigValidationResult validationResult);

    public ConfigValidationResult getValidationResult();
}
```

### 19. GlobalExceptionHandler Extensions

Extend existing `GlobalExceptionHandler` with two new handlers:

```java
// Added to existing GlobalExceptionHandler.java

@ExceptionHandler(ConfigConflictException.class)
public ResponseEntity<Map<String, Object>> handleConfigConflict(ConfigConflictException ex) {
    // Returns 409 with { "status": { "success": false, "code": 409, "message": "..." },
    //                     "errorCode": "INVALID_TRANSITION" | "CONFLICT" }
}

@ExceptionHandler(ConfigValidationException.class)
public ResponseEntity<Map<String, Object>> handleConfigValidation(ConfigValidationException ex) {
    // Returns 422 with { "status": { "success": false, "code": 422, "message": "Validation failed" },
    //                     "errors": [ { "field": "...", "code": "...", "message": "..." } ] }
}
```

### 20. Request/Response DTOs

**Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.models.tier`, `.benefit`, `.config`

#### StatusChangeRequest
```java
public class StatusChangeRequest {
    @NotNull
    private String status;           // Target ConfigStatus name
    private String reason;           // Optional comment

    // Getters, setters
}
```

#### ReviewRequest
```java
public class ReviewRequest {
    @NotNull
    private String approvalStatus;   // "APPROVE" or "REJECT"

    @Size(max = 150)
    private String comment;          // Mandatory on REJECT, optional on APPROVE

    // Getters, setters
}
```

#### TierConfigRequest
```java
public class TierConfigRequest {
    @NotNull private Long programId;
    @NotBlank @Size(max = 200) private String name;
    private String description;
    @Pattern(regexp = "^#[0-9a-fA-F]{6}$") private String color;
    @NotNull private Integer serialNumber;
    @NotNull @Valid private TierEligibilityRequest eligibility;
    @NotNull @Valid private TierValidityRequest validity;
    @Valid private TierRenewalRequest renewal;
    @NotNull @Valid private TierDowngradeRequest downgrade;
    @Valid private TierUpgradeRequest upgrade;
    @Valid private TierNudgeRequest nudge;
    private List<@Valid LinkedBenefitRequest> linkedBenefits;

    // Getters, setters
}
```

Sub-DTOs (`TierEligibilityRequest`, `TierValidityRequest`, etc.) mirror the embedded model types with Bean Validation annotations for layer-1 validation.

#### TierConfigResponse
```java
public class TierConfigResponse {
    private String id;               // ObjectId as hex string
    private String tierId;           // entityId (immutable UUID)
    private Integer orgId;
    private Long programId;
    private String name;
    private String description;
    private String color;
    private Integer serialNumber;
    private String status;
    private Integer version;
    private String parentId;
    private String comments;
    private TierEligibility eligibility;
    private TierValidity validity;
    private TierRenewal renewal;
    private TierDowngrade downgrade;
    private TierUpgrade upgrade;
    private TierNudge nudge;
    private List<LinkedBenefit> linkedBenefits;
    private Instant createdOn;       // GUARDRAIL G-01.6: ISO-8601 UTC
    private String createdBy;
    private Instant lastModifiedOn;
    private String lastModifiedBy;

    // Draft enrichment (for includeDraftDetails=true on ACTIVE tiers)
    private DraftDetails draftDetails;

    // Getters, setters
}
```

#### DraftDetails
```java
public class DraftDetails {
    private String draftId;          // ObjectId of the DRAFT document
    private Integer draftVersion;
    private String lastModifiedBy;
    private Instant lastModifiedOn;

    // Getters, setters
}
```

#### BenefitConfigRequest / BenefitConfigResponse
Follow the same pattern as tier DTOs, with benefit-specific fields (type, category, triggerEvent, parameters, linkedTiers).

### 21. TierConfigService

- **Annotations**: `@Service`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
- **Discovered from**: `ProgramsApiService.java`
- **Imports**: `com.capillary.shopbook.emf.api.hibernate.ShardContext`

```java
@Service
public class TierConfigService {

    @Autowired
    private TierConfigDao tierConfigDao;

    @Autowired
    private BenefitConfigDao benefitConfigDao;    // DAO-level, NOT BenefitConfigService

    @Autowired
    private TierValidatorFactory tierValidatorFactory;

    @Autowired
    private ConfigStatusTransitionValidator statusTransitionValidator;

    @Autowired
    private VersioningHelper versioningHelper;

    /**
     * List tiers for a program.
     * @param programId required
     * @param status optional filter
     * @param includeDraftDetails optional enrichment flag
     * @param offset pagination offset (default 0)
     * @param limit pagination limit (default 20, max 100)
     * @return List<TierConfigResponse>, never null (G-02.1)
     */
    public List<TierConfigResponse> listTiers(Long programId, String status,
                                               Boolean includeDraftDetails,
                                               Integer offset, Integer limit);

    /**
     * Create a new tier config.
     * @return created TierConfigResponse with generated tierId, version=1, status=DRAFT
     * @throws ConfigValidationException on validation failure (422)
     */
    public TierConfigResponse createTier(TierConfigRequest request);

    /**
     * Update an existing tier config.
     * - DRAFT: updates in-place
     * - ACTIVE (maker-checker on): creates new DRAFT with parentId
     * - ACTIVE with existing DRAFT: updates existing DRAFT in-place
     * @throws ConfigConflictException if PENDING_APPROVAL, STOPPED, or SNAPSHOT (409)
     * @throws ConfigValidationException on validation failure (422)
     */
    public TierConfigResponse updateTier(String tierId, TierConfigRequest request);

    /**
     * Change tier status (submit, pause, stop, resume).
     * Protected by @DistributedLock.
     * @throws ConfigConflictException on invalid transition (409)
     */
    @DistributedLock(key = "'lock_tier_status_' + #orgId + '_' + #tierId",
                     ttl = 300_000, acquireTime = 5_000)
    public TierConfigResponse changeStatus(String tierId, StatusChangeRequest request);

    /**
     * Review (approve/reject) a tier.
     * Protected by @DistributedLock.
     * @throws ConfigConflictException if not PENDING_APPROVAL (409)
     * @throws ConfigValidationException if reject without comment (422)
     */
    @DistributedLock(key = "'lock_tier_status_' + #orgId + '_' + #tierId",
                     ttl = 300_000, acquireTime = 5_000)
    public TierConfigResponse reviewTier(String tierId, ReviewRequest request);

    /**
     * List pending approvals for a program.
     * Includes full config + diff against parent for edits.
     * @return List<TierApprovalResponse>, never null (G-02.1)
     */
    public List<TierApprovalResponse> listPendingApprovals(Long programId);
}
```

### 22. BenefitConfigService

- **Annotations**: `@Service`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl`
- **Discovered from**: `ProgramsApiService.java`

Same structural pattern as `TierConfigService` with benefit-specific logic. Injects `TierConfigDao` (NOT `TierConfigService`) for linked tier validation.

```java
@Service
public class BenefitConfigService {

    @Autowired
    private BenefitConfigDao benefitConfigDao;

    @Autowired
    private TierConfigDao tierConfigDao;          // DAO-level, NOT TierConfigService

    @Autowired
    private BenefitValidatorFactory benefitValidatorFactory;

    @Autowired
    private ConfigStatusTransitionValidator statusTransitionValidator;

    @Autowired
    private VersioningHelper versioningHelper;

    public List<BenefitConfigResponse> listBenefits(Long programId, String status,
                                                     String type, String category,
                                                     String triggerEvent, String linkedTierId,
                                                     Boolean includeDraftDetails,
                                                     Integer offset, Integer limit);

    public BenefitConfigResponse createBenefit(BenefitConfigRequest request);

    public BenefitConfigResponse updateBenefit(String benefitId, BenefitConfigRequest request);

    @DistributedLock(key = "'lock_benefit_status_' + #orgId + '_' + #benefitId",
                     ttl = 300_000, acquireTime = 5_000)
    public BenefitConfigResponse changeStatus(String benefitId, StatusChangeRequest request);

    @DistributedLock(key = "'lock_benefit_status_' + #orgId + '_' + #benefitId",
                     ttl = 300_000, acquireTime = 5_000)
    public BenefitConfigResponse reviewBenefit(String benefitId, ReviewRequest request);

    public List<BenefitApprovalResponse> listPendingApprovals(Long programId);
}
```

### 23. TierConfigController

- **Annotations**: `@RestController`, `@RequestMapping("/api/v1/tiers")`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.controller.impl`
- **Discovered from**: `MilestoneConfigController.java` (hand-written controller), `OrgConfigController.java`
- **Imports**: `javax.validation.Valid`, `org.springframework.web.bind.annotation.*`, `org.springframework.http.ResponseEntity`, `com.capillary.shopbook.emf.api.hibernate.ShardContext`
- **Maven dependency**: already in module pom.xml

```java
@RestController
@RequestMapping("/api/v1/tiers")
public class TierConfigController {

    @Autowired
    private TierConfigService tierConfigService;

    @GetMapping
    public ResponseEntity<List<TierConfigResponse>> listTiers(
            @RequestParam Long programId,
            @RequestParam(required = false) String status,
            @RequestParam(required = false, defaultValue = "false") Boolean includeDraftDetails,
            @RequestParam(required = false, defaultValue = "0") Integer offset,
            @RequestParam(required = false, defaultValue = "20") Integer limit);

    @PostMapping
    public ResponseEntity<TierConfigResponse> createTier(
            @Valid @RequestBody TierConfigRequest request);

    @PutMapping("/{tierId}")
    public ResponseEntity<TierConfigResponse> updateTier(
            @PathVariable String tierId,
            @Valid @RequestBody TierConfigRequest request);

    @PutMapping("/{tierId}/status")
    public ResponseEntity<TierConfigResponse> changeStatus(
            @PathVariable String tierId,
            @Valid @RequestBody StatusChangeRequest request);

    @PostMapping("/{tierId}/review")
    public ResponseEntity<TierConfigResponse> reviewTier(
            @PathVariable String tierId,
            @Valid @RequestBody ReviewRequest request);

    @GetMapping("/approvals")
    public ResponseEntity<List<TierApprovalResponse>> listPendingApprovals(
            @RequestParam Long programId);
}
```

### 24. BenefitConfigController

- **Annotations**: `@RestController`, `@RequestMapping("/api/v1/benefits")`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.controller.impl`
- Same structural pattern as `TierConfigController`.

```java
@RestController
@RequestMapping("/api/v1/benefits")
public class BenefitConfigController {

    @Autowired
    private BenefitConfigService benefitConfigService;

    @GetMapping
    public ResponseEntity<List<BenefitConfigResponse>> listBenefits(
            @RequestParam Long programId,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String triggerEvent,
            @RequestParam(required = false) String linkedTierId,
            @RequestParam(required = false, defaultValue = "false") Boolean includeDraftDetails,
            @RequestParam(required = false, defaultValue = "0") Integer offset,
            @RequestParam(required = false, defaultValue = "20") Integer limit);

    @PostMapping
    public ResponseEntity<BenefitConfigResponse> createBenefit(
            @Valid @RequestBody BenefitConfigRequest request);

    @PutMapping("/{benefitId}")
    public ResponseEntity<BenefitConfigResponse> updateBenefit(
            @PathVariable String benefitId,
            @Valid @RequestBody BenefitConfigRequest request);

    @PutMapping("/{benefitId}/status")
    public ResponseEntity<BenefitConfigResponse> changeStatus(
            @PathVariable String benefitId,
            @Valid @RequestBody StatusChangeRequest request);

    @PostMapping("/{benefitId}/review")
    public ResponseEntity<BenefitConfigResponse> reviewBenefit(
            @PathVariable String benefitId,
            @Valid @RequestBody ReviewRequest request);

    @GetMapping("/approvals")
    public ResponseEntity<List<BenefitApprovalResponse>> listPendingApprovals(
            @RequestParam Long programId);
}
```

### 25. TierValidatorFactory

- **Annotations**: `@Component`
- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.factory`
- **Discovered from**: `ValidatorFactory.java` (exact pattern: `@Component`, `@Autowired` field injection, `switch` on enum, returns `List`)

```java
@Component
public class TierValidatorFactory {

    @Autowired TierNameUniquenessValidator tierNameUniquenessValidator;
    @Autowired EligibilityThresholdValidator eligibilityThresholdValidator;
    @Autowired DowngradeTargetValidator downgradeTargetValidator;
    @Autowired SerialNumberValidator serialNumberValidator;
    @Autowired LinkedBenefitValidator linkedBenefitValidator;
    @Autowired StatusEditableValidator statusEditableValidator;

    public List<ConfigValidator<TierConfig>> getValidators(TierValidatorTypes validatorType) {
        List<ConfigValidator<TierConfig>> validators = new ArrayList<>();
        switch (validatorType) {
            case CREATE_TIER:
                validators.add(tierNameUniquenessValidator);
                validators.add(eligibilityThresholdValidator);
                validators.add(downgradeTargetValidator);
                validators.add(serialNumberValidator);
                validators.add(linkedBenefitValidator);
                break;
            case UPDATE_TIER:
                validators.add(statusEditableValidator);
                validators.add(tierNameUniquenessValidator);
                validators.add(eligibilityThresholdValidator);
                validators.add(downgradeTargetValidator);
                validators.add(serialNumberValidator);
                validators.add(linkedBenefitValidator);
                break;
            default:
                // GUARDRAIL G-02.7: handle default case
                break;
        }
        return validators;
    }
}
```

### 26. TierValidatorTypes (enum)

- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.factory`
- **Discovered from**: `ValidatorTypes.java`

```java
public enum TierValidatorTypes {
    CREATE_TIER,
    UPDATE_TIER;
}
```

### 27. BenefitValidatorFactory

Same pattern as `TierValidatorFactory`. Individual validators:

- `BenefitNameUniquenessValidator` — queries `BenefitConfigDao` for name+program+non-SNAPSHOT
- `BenefitTypeParameterValidator` — validates type-specific parameters (e.g., POINTS_MULTIPLIER needs `multiplier` > 0)
- `LinkedTierValidator` — queries `TierConfigDao` for linked tier existence in same program
- `StatusEditableValidator` — shared, rejects PENDING_APPROVAL/STOPPED/SNAPSHOT

### 28. Individual Validators (signatures)

All validators implement `ConfigValidator<TierConfig>` or `ConfigValidator<BenefitConfig>` and are `@Component` annotated.

#### TierNameUniquenessValidator
```java
@Component
public class TierNameUniquenessValidator implements ConfigValidator<TierConfig> {
    @Autowired private TierConfigDao tierConfigDao;

    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<TierConfig> request);
    // Queries: { orgId, programId, name, status: { $nin: ["SNAPSHOT"] } }
    // Returns: FieldError("name", "DUPLICATE_NAME", "...") if duplicate found
}
```

#### EligibilityThresholdValidator
```java
@Component
public class EligibilityThresholdValidator implements ConfigValidator<TierConfig> {
    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<TierConfig> request);
    // Checks: threshold > 0, kpiType is valid enum value
}
```

#### DowngradeTargetValidator
```java
@Component
public class DowngradeTargetValidator implements ConfigValidator<TierConfig> {
    @Autowired private TierConfigDao tierConfigDao;

    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<TierConfig> request);
    // Checks: targetTierId == "NONE" (valid) OR exists in same program
}
```

#### SerialNumberValidator
```java
@Component
public class SerialNumberValidator implements ConfigValidator<TierConfig> {
    @Autowired private TierConfigDao tierConfigDao;

    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<TierConfig> request);
    // Checks: no gaps or conflicts in serial number sequence
}
```

#### LinkedBenefitValidator
```java
@Component
public class LinkedBenefitValidator implements ConfigValidator<TierConfig> {
    @Autowired private BenefitConfigDao benefitConfigDao;   // DAO, not service

    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<TierConfig> request);
    // Checks: each benefitId in linkedBenefits exists in same program with ACTIVE or DRAFT status
}
```

#### StatusEditableValidator (shared)
```java
@Component
public class StatusEditableValidator<T extends ConfigBaseDocument> implements ConfigValidator<T> {
    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<T> request);
    // Checks: entity.status is DRAFT (editable). Returns CONFLICT error otherwise.
}
```

#### BenefitTypeParameterValidator
```java
@Component
public class BenefitTypeParameterValidator implements ConfigValidator<BenefitConfig> {
    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<BenefitConfig> request);
    // Switch on type:
    //   POINTS_MULTIPLIER: requires "multiplier" > 0
    //   FLAT_POINTS_AWARD: requires "points" > 0
    //   COUPON_ISSUANCE: requires "couponTemplateId" non-blank
    //   BADGE_AWARD: requires "badgeId" non-blank
    //   FREE_SHIPPING: no extra params required
    //   CUSTOM: no validation (flexible)
    //   default: GUARDRAIL G-02.7
}
```

#### LinkedTierValidator
```java
@Component
public class LinkedTierValidator implements ConfigValidator<BenefitConfig> {
    @Autowired private TierConfigDao tierConfigDao;    // DAO, not service

    @Override
    public ConfigValidationResult validate(ConfigValidatorRequest<BenefitConfig> request);
    // Checks: each tierId in linkedTiers exists in same program
}
```

---

## US-11 Diff Computation Design

The Analyst flagged that the diff response shape for approval listings (US-11) was unspecified. Here is the design.

### ConfigDiffResult

- **Package**: `com.capillary.shopbook.pointsengine.RESTEndpoint.models.config`

```java
public class ConfigDiffResult {

    private List<FieldDiff> changes;     // GUARDRAIL G-02.1: never null

    public ConfigDiffResult();

    public List<FieldDiff> getChanges();

    public boolean hasChanges();

    // --- Inner class ---
    public static class FieldDiff {
        private final String fieldPath;   // Dot-notation path, e.g. "eligibility.threshold"
        private final Object oldValue;    // Value from parent (ACTIVE)
        private final Object newValue;    // Value from draft (PENDING_APPROVAL)

        public FieldDiff(String fieldPath, Object oldValue, Object newValue);
        // Getters only
    }
}
```

### Diff Computation Strategy

Implemented as a `@Component` utility:

```java
@Component
public class ConfigDiffComputer {

    /**
     * Computes field-level diff between a parent config and a draft config.
     * Uses reflection-free approach: serializes both to Map<String, Object> via
     * the BSON codec, then recursively compares keys.
     *
     * @param parent the current ACTIVE version
     * @param draft the PENDING_APPROVAL version
     * @return ConfigDiffResult with all changed fields
     */
    public <T extends ConfigBaseDocument> ConfigDiffResult computeDiff(T parent, T draft);
}
```

**Algorithm**: Convert both documents to flat `Map<String, Object>` (using BSON codec or Jackson), then walk keys. For each key present in either map, if values differ, add a `FieldDiff`. Skip metadata fields (`_id`, `parentId`, `version`, `status`, `comments`, `createdOn`, `createdBy`, `lastModifiedOn`, `lastModifiedBy`).

### TierApprovalResponse / BenefitApprovalResponse

```java
public class TierApprovalResponse {
    private TierConfigResponse pendingConfig;    // Full PENDING_APPROVAL document
    private TierConfigResponse parentConfig;     // Full ACTIVE parent (null for new tiers)
    private ConfigDiffResult diff;               // Field-level changes (null for new tiers)
    private String submittedBy;
    private Instant submittedOn;
    private String submissionReason;

    // Getters, setters
}
```

`BenefitApprovalResponse` follows the same pattern.

---

## Idempotency Key Design

Per Analyst recommendation (R-05), using Redis with TTL:

```java
@Component
public class IdempotencyKeyGuard {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String PREFIX = "idempotency:config:";
    private static final long TTL_MINUTES = 5;

    /**
     * Check if a request with this idempotency key has already been processed.
     * @param key the X-Idempotency-Key header value
     * @return Optional.empty() if key is new; Optional.of(cachedResponse) if already processed
     */
    public Optional<Object> checkAndMark(String key);

    /**
     * Store the response for a completed request.
     * @param key the X-Idempotency-Key header value
     * @param response the response to cache
     */
    public void markCompleted(String key, Object response);
}
```

Used in `TierConfigService.createTier()` and `BenefitConfigService.createBenefit()` — the two POST endpoints where duplicate creation is the risk. The controller extracts `X-Idempotency-Key` from the request header and passes it to the service.

---

## Ownership Summary

| Package | Module | Owns |
|---------|--------|------|
| `com.capillary.shopbook.springdata.mongodb.model.config` | emf | `ConfigBaseDocument`, `TierConfig`, `BenefitConfig`, embedded types |
| `com.capillary.shopbook.springdata.mongodb.enums` | emf | `ConfigStatus`, `ConfigAction` |
| `com.capillary.shopbook.springdata.mongodb.dao` | emf | `TierConfigDao`, `BenefitConfigDao` interfaces |
| `com.capillary.shopbook.springdata.mongodb.dao.impl` | emf | `TierConfigDaoImpl`, `BenefitConfigDaoImpl` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.controller.impl` | pointsengine-emf | `TierConfigController`, `BenefitConfigController` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.Service.impl` | pointsengine-emf | `TierConfigService`, `BenefitConfigService`, `VersioningHelper`, `ConfigDiffComputer`, `IdempotencyKeyGuard` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.models.tier` | pointsengine-emf | Tier request/response DTOs |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.models.benefit` | pointsengine-emf | Benefit request/response DTOs |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.models.config` | pointsengine-emf | Shared DTOs: `StatusChangeRequest`, `ReviewRequest`, `DraftDetails`, `ConfigDiffResult`, `TierApprovalResponse`, `BenefitApprovalResponse` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.Interfaces` | pointsengine-emf | `ConfigValidator<T>` interface |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.models` | pointsengine-emf | `ConfigValidatorRequest`, `ConfigValidationResult` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.factory` | pointsengine-emf | `TierValidatorFactory`, `BenefitValidatorFactory`, `TierValidatorTypes`, `BenefitValidatorTypes` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.config` | pointsengine-emf | `ConfigStatusTransitionValidator`, `StatusEditableValidator` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.tier` | pointsengine-emf | Tier-specific validators |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.validators.impl.benefit` | pointsengine-emf | Benefit-specific validators |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.annotations` | pointsengine-emf | `@DistributedLock`, `DistributedLockAspect` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.Exceptions` | pointsengine-emf | `ConfigConflictException`, `ConfigValidationException` |
| `com.capillary.shopbook.pointsengine.RESTEndpoint.Exceptions.handler` | pointsengine-emf | Extended `GlobalExceptionHandler` |

---

## Guardrail Enforcement Summary

| Guardrail | How Enforced Structurally |
|-----------|--------------------------|
| G-01 (Timezone) | `ConfigBaseDocument` uses `Instant` for all timestamps. DTOs use `Instant`. No `Date` or `LocalDateTime`. |
| G-02.1 (No null collections) | All list-returning methods documented to return empty list, never null. `ConfigValidationResult.getErrors()` returns `Collections.emptyList()` when no errors. |
| G-02.2 (Optional for nullable) | DAO `findOne()` returns `Optional<T>`. |
| G-02.7 (Default in switch) | All enum switches include `default:` case. |
| G-03.2 (Input validation) | Two-layer: Bean Validation (`@Valid`) on DTOs + `ConfigValidator` factory chains. |
| G-06.1 (Idempotent writes) | `IdempotencyKeyGuard` with Redis SET NX + 5-min TTL on POST endpoints. |
| G-06.3 (Structured errors) | `ConfigValidationResult.FieldError` with field/code/message. |
| G-06.4 (HTTP status codes) | 200 success, 409 conflict, 422 validation, 500 unexpected. |
| G-07 (Multi-tenancy) | `orgId` is `Integer` in `ConfigBaseDocument` (matches `ShardContext.getOrgId()` int). All DAO methods take `Integer orgId`. Controllers extract from `ShardContext`, never from request body. |
| G-10 (Concurrency) | `@DistributedLock` with atomic Redis SET NX PX on status change methods. |
| G-12.2 (Follow existing patterns) | Every type follows codebase patterns documented in Pattern Decisions section. |
