# LLD — Tier CRUD APIs (Designer Phase)

> Feature: tier-crud
> Ticket: test_branch_v3
> Phase: Designer (Phase 7)
> Date: 2026-04-06
> Confidence scale: C1 (speculative) → C7 (verified from source)

---

## 0. Pattern Discovery Summary

All patterns discovered by reading actual source files (C7). No assumptions about base classes or annotations.

### Reference Implementation (intouch-api-v3)

| Pattern | Discovered From | Key Finding |
|---------|----------------|-------------|
| Controller | `UnifiedPromotionController.java` | `@RestController`, `@RequestMapping`, constructor injection (`@Autowired`), `ResponseEntity<ResponseWrapper<T>>` return type, `AbstractBaseAuthenticationToken` auth param |
| Facade | `UnifiedPromotionFacade.java` | `@Component` (not `@Service`), `@Autowired` field injection, catches `InvalidInputException` / `NotFoundException` / `ServiceException` |
| MongoDB Document | `UnifiedPromotion.java` | `@Document(collection=...)`, Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, `@Id String objectId`, `@JsonProperty("id")` alias |
| Repository | `UnifiedPromotionRepository.java` | `extends MongoRepository<T, String>`, `@Repository`, `@Query` with MongoDB JSON syntax, `Optional<T>` for single returns, `List<T>` for multi-returns |
| DTO | `PromotionReviewRequest.java` | Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, Bean Validation on fields |
| EMF Config | `EmfMongoConfig.java` | `@Configuration`, `@Profile("!test")`, `@EnableMongoRepositories(... includeFilters = @ComponentScan.Filter(type = FilterType.ASSIGNABLE_TYPE, classes = {...}))` |
| Thrift Client | `PointsEngineRulesThriftService.java` | `@Service`, `@Loggable`, `@Profile("!test")`, `getClient()` returns `PointsEngineRuleService.Iface` from `RPCService.rpcClient(...)`, catches `PointsEngineRuleServiceException` + `TException` + `Exception` |
| Exceptions | `InvalidInputException.java`, `NotFoundException.java` | Simple `RuntimeException` subclasses, string message |
| Test framework | `UnifiedPromotionControllerTest.java` | JUnit 5 (`@ExtendWith(MockitoExtension.class)`), Mockito, `@InjectMocks`, `@Mock` |

### Reference Implementation (emf-parent)

| Pattern | Discovered From | Key Finding |
|---------|----------------|-------------|
| Entity | `ProgramSlab.java` | `@Entity @Table(name=...)`, `@EmbeddedId` composite PK, `javax.persistence.*` imports, `OrgEntityIntegerPKBase` base class for PK, NO Lombok — manual getters/setters |
| DAO | `PeProgramSlabDao.java` | `extends GenericDao<T, PK>` (from `com.capillary.commons.data.dao`), `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`, `@Query` JPQL style |
| Thrift Impl | `PointsEngineRuleConfigThriftImpl.java` | `@Service @ExposedCall(thriftName = "pointsengine-rules")`, `implements Iface`, field injection `@Autowired`, no `@Transactional` at class level, `@Trace(dispatcher = true) @MDCData(...)` on methods |
| Timestamps in entity | `ProgramSlab.java` | Uses `java.util.Date` + `@Temporal(TemporalType.TIMESTAMP)` — LEGACY PATTERN. New fields added to `ProgramSlab` must follow the same `Date` convention for JPA compatibility with existing Hibernate mapping, but the MongoDB document MUST use `Instant` (G-01 compliance) |

### Thrift IDL (thrifts repo)

| Struct/Method | Location | Key Finding |
|---------------|----------|-------------|
| `SlabInfo` | `pointsengine_rules.thrift` line 348 | Fields: `id (i32)`, `programId (i32)`, `serialNumber (i32)`, `name (string)`, `description (string)`, `colorCode (string, optional)`, `updatedViaNewUI (bool, optional)` — NO active field |
| `createOrUpdateSlab` | line 1184 | Signature: `SlabInfo createOrUpdateSlab(1:SlabInfo slabInfo, 2:i32 orgId, 3:i32 lastModifiedBy, 4:i64 lastModifiedOn, 5:string serverReqId)` |
| `getAllSlabs` | line 1061 | Signature: `list<SlabInfo> getAllSlabs(1:i32 programId, 2:i32 orgId, 3:string serverReqId)` |
| `BoolRes` | line 359 | `{ optional bool success; optional PointsEngineRuleServiceException ex; }` |

---

## 1. Pattern Decisions

| Decision | Chosen Pattern | Rejected | Reason |
|----------|---------------|----------|--------|
| MongoDB Repository | `MongoRepository<T, String>` (intouch-api-v3 pattern) | Custom `BaseMongoDaoImpl` | Target module (intouch-api-v3) uses `MongoRepository`. Consistent with `UnifiedPromotionRepository`. |
| Facade injection | `@Autowired` field injection | Constructor injection | Matches existing `UnifiedPromotionFacade` pattern (field injection). G-12 compliance: follow project pattern. |
| Entity timestamps | `java.util.Date` + `@Temporal` | `Instant` | Only for `ProgramSlab` entity (JPA/Hibernate compatibility with existing schema). New `TierDocument` MongoDB fields use `Instant` (G-01). |
| DTO/Document style | Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor` | Records, manual builders | Matches `UnifiedPromotion`, `PromotionReviewRequest`. |
| TierFacade annotation | `@Component` | `@Service` | Matches `UnifiedPromotionFacade`. Spring treats both the same; project uses `@Component` for facade layer. |

---

## 2. Dependency Direction

```
                    ┌────────────────────────────────────────┐
                    │         intouch-api-v3                 │
                    │                                        │
  HTTP Client ──▶   │  TierController                        │
                    │       │                                │
                    │       ▼                                │
                    │  TierFacade ──▶ TierRepository ──▶ MongoDB
                    │       │                                │
                    │       ▼                                │
                    │  PointsEngineRulesThriftService        │
                    └────────────│───────────────────────────┘
                                 │ Thrift RPC
                                 ▼
                    ┌────────────────────────────────────────┐
                    │         emf-parent                     │
                    │                                        │
                    │  PointsEngineRuleConfigThriftImpl       │
                    │       │                                │
                    │       ├──▶ PeProgramSlabDao ──▶ MySQL  │
                    │       ├──▶ PeCustomerEnrollmentDao      │
                    │       └──▶ cacheEvictHelper            │
                    └────────────────────────────────────────┘
```

**Dependency rules:**
- `TierController` → `TierFacade` (1:1)
- `TierFacade` → `TierRepository` (MongoDB reads/writes)
- `TierFacade` → `PointsEngineRulesThriftService` (Thrift calls for approve/deactivate/memberCount)
- `PointsEngineRuleConfigThriftImpl` → `PeProgramSlabDao`, `PeCustomerEnrollmentDao` (MySQL)
- No reverse dependencies. No cycles.

---

## 3. intouch-api-v3 Types

---

### 3.1 TierStatus (enum)

- **Package**: `com.capillary.intouchapiv3.tier.enums`
- **Extends**: `java.lang.Enum`
- **Annotations**: none
- **Discovered from**: `PromotionStatus.java` (same enum pattern — simple enum, no annotations)
- **Imports**: none
- **Maven dependency**: already in module (Java built-in)

```java
package com.capillary.intouchapiv3.tier.enums;

public enum TierStatus {
    DRAFT,
    PENDING_APPROVAL,
    ACTIVE,
    STOPPED
}
```

---

### 3.2 TierAction (enum)

- **Package**: `com.capillary.intouchapiv3.tier.enums`
- **Extends**: `java.lang.Enum`
- **Annotations**: none
- **Discovered from**: `PromotionAction.java` (enum with `fromString()` and validation)
- **Imports**: `com.capillary.intouchapiv3.models.exceptions.InvalidInputException`
- **Maven dependency**: already in module

```java
package com.capillary.intouchapiv3.tier.enums;

import com.capillary.intouchapiv3.models.exceptions.InvalidInputException;
import java.util.Arrays;

public enum TierAction {
    SUBMIT_FOR_APPROVAL,
    APPROVE,
    REJECT,
    STOP;

    /**
     * Parse a string to TierAction. Throws InvalidInputException (not NPE) on invalid input.
     * GUARDRAIL: G-02.3 — fail fast with descriptive error
     */
    public static TierAction fromString(String action) throws InvalidInputException;
}
```

**State machine (enforced in TierFacade, not in enum):**
```
DRAFT        + SUBMIT_FOR_APPROVAL → PENDING_APPROVAL
PENDING_APPROVAL + APPROVE         → ACTIVE  (triggers Thrift sync)
PENDING_APPROVAL + REJECT          → DRAFT
ACTIVE       + STOP                → STOPPED (triggers Thrift deactivate)
```

---

### 3.3 EligibilityConfig (embedded DTO / MongoDB sub-document)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Extends**: none
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, `@JsonIgnoreProperties(ignoreUnknown = true)`
- **Discovered from**: `UnifiedPromotion.model.*` nested models pattern
- **Imports**: `lombok.*`, `jakarta.validation.constraints.*`, `com.fasterxml.jackson.annotation.JsonIgnoreProperties`
- **Maven dependency**: Lombok and Jackson already in module pom.xml

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class EligibilityConfig {

    @NotBlank(message = "currentValueType is required")
    private String currentValueType;   // e.g. CUMULATIVE_PURCHASES, CURRENT_POINTS

    @NotNull(message = "thresholdValue is required")
    @DecimalMin(value = "0.0", inclusive = false, message = "thresholdValue must be > 0")
    private Double thresholdValue;

    private Integer trackerId;         // required when currentValueType=TRACKER_VALUE_BASED
    private Integer trackerConditionId;
}
```

---

### 3.4 ValidityConfig (embedded DTO / MongoDB sub-document)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- **Discovered from**: same nested model pattern

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ValidityConfig {

    @NotBlank(message = "periodType is required")
    private String periodType;     // e.g. MONTHS, YEARS, DAYS

    @NotNull(message = "periodValue is required")
    @Min(value = 1, message = "periodValue must be >= 1")
    private Integer periodValue;
}
```

---

### 3.5 RenewalConfig (embedded DTO / MongoDB sub-document)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenewalConfig {

    private List<RenewalCondition> conditions;        // nullable if no conditions
    private String conditionOperator;                 // ANY | ALL | CUSTOM
    private String customExpression;                  // required when conditionOperator=CUSTOM
    private String extensionType;                     // BY_MONTH | BY_VALIDITY_PERIOD | FROM_FIXED_DATE
}
```

**Nested:**
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RenewalCondition {
    private String conditionType;
    private Double thresholdValue;
    private String timeUnit;
}
```

---

### 3.6 DowngradeConfig (embedded DTO / MongoDB sub-document)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DowngradeConfig {

    private String targetType;                                  // SINGLE_BELOW | THRESHOLD_BASED | LOWEST
    private Integer targetSlabId;                               // optional: specific downgrade target
    private Integer gracePeriodDays;
    @Builder.Default
    private Boolean isDowngradeOnReturnEnabled = false;
    @Builder.Default
    private Boolean isDowngradeOnPartnerProgramDeLinkingEnabled = false;
    private Object confirmationConfig;                          // TierConfiguration.downgradeConfirmationConfig
    private Object reminders;                                   // TierConfiguration.reminders
}
```

---

### 3.7 UpgradeBonusConfig (embedded DTO / MongoDB sub-document)

- **Package**: `com.capillary.intouchapiv3.tier.dto`

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpgradeBonusConfig {
    private Integer points;   // nullable; no bonus if null/0
}
```

---

### 3.8 TierRequest (input DTO — create and update)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, `@JsonIgnoreProperties(ignoreUnknown = true)`
- **Discovered from**: `UnifiedPromotion.java` (uses `@Valid` on nested objects), `PromotionReviewRequest.java`
- **Imports**: `jakarta.validation.Valid`, `jakarta.validation.constraints.*`, `lombok.*`

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class TierRequest {

    @NotBlank(message = "name is required")
    @Size(max = 100, message = "name cannot exceed 100 characters")
    private String name;

    @Size(max = 500, message = "description cannot exceed 500 characters")
    private String description;

    @Pattern(regexp = "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", message = "colorCode must be a valid hex color")
    private String colorCode;

    @NotNull(message = "serialNumber is required")
    @Min(value = 1, message = "serialNumber must be >= 1")
    private Integer serialNumber;

    @NotNull(message = "eligibility is required")
    @Valid
    private EligibilityConfig eligibility;

    @Valid
    private ValidityConfig validity;

    @Valid
    private RenewalConfig renewal;

    @Valid
    private DowngradeConfig downgrade;

    @Valid
    private UpgradeBonusConfig upgradeBonus;

    @Size(max = 30, message = "metadata cannot exceed 30 characters")
    private String metadata;    // maps to program_slabs.metadata (SlabMetaData JSON containing colorCode)
}
```

---

### 3.9 TierStatusRequest (status change input DTO)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- **Discovered from**: `PromotionReviewRequest.java`

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TierStatusRequest {

    @NotBlank(message = "action is required")
    private String action;    // SUBMIT_FOR_APPROVAL | APPROVE | REJECT | STOP

    @Size(max = 500, message = "comment cannot exceed 500 characters")
    private String comment;   // required when action=REJECT
}
```

---

### 3.10 TierResponse (output DTO)

- **Package**: `com.capillary.intouchapiv3.tier.dto`
- **Annotations**: Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, `@JsonIgnoreProperties(ignoreUnknown = true)`
- **Discovered from**: `UnifiedPromotion.java` response pattern; timestamp fields use `Instant` (G-01 compliance — NOT `java.util.Date`)
- **Imports**: `java.time.Instant`

```java
package com.capillary.intouchapiv3.tier.dto;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class TierResponse {

    private String tierId;           // UUID, immutable identifier
    private String objectId;         // MongoDB _id
    private Integer slabId;          // MySQL program_slabs.id; null for DRAFT/PENDING_APPROVAL
    private String name;
    private String description;
    private String colorCode;
    private Integer serialNumber;
    private TierStatus status;       // DRAFT | PENDING_APPROVAL | ACTIVE | STOPPED

    private EligibilityConfig eligibility;
    private ValidityConfig validity;
    private RenewalConfig renewal;
    private DowngradeConfig downgrade;
    private UpgradeBonusConfig upgradeBonus;

    private String metadata;         // max 30 chars
    private Long memberCount;        // null for DRAFT/PENDING_APPROVAL; from customer_enrollment via Thrift

    private Integer programId;
    private Long orgId;              // GUARDRAIL: G-07 — always present for tenant isolation
    private String parentId;         // null or objectId of ACTIVE version this DRAFT modifies

    // GUARDRAIL: G-01 — Instant not Date
    private Instant createdOn;
    private Instant lastModifiedOn;
    private Integer createdBy;
    private Integer lastModifiedBy;
    private Integer version;
}
```

---

### 3.11 TierDocument (MongoDB document)

- **Package**: `com.capillary.intouchapiv3.tier`
- **Extends**: none (same as `UnifiedPromotion` — no base class)
- **Annotations**: `@Document(collection = "tiers")`, Lombok `@Data @Builder @NoArgsConstructor @AllArgsConstructor`, `@IgnoreGenerated` (custom Capillary annotation for code coverage exclusion)
- **Discovered from**: `UnifiedPromotion.java` — exact same pattern. Uses `@Id String objectId`, separate immutable `tierId` field (UUID), Lombok for builders.
- **Imports**: `org.springframework.data.annotation.Id`, `org.springframework.data.mongodb.core.mapping.Document`, `com.capillary.intouchapiv3.annotations.IgnoreGenerated`, `java.time.Instant`
- **Maven dependency**: `spring-data-mongodb` already in module pom.xml (via spring-boot-starter-data-mongodb)

```java
package com.capillary.intouchapiv3.tier;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "tiers")
@IgnoreGenerated
public class TierDocument {

    @Id
    @JsonProperty("id")
    private String objectId;           // MongoDB _id, auto-generated

    /**
     * Immutable tier identifier (UUID). Set on creation, never changed.
     * GUARDRAIL: G-02 — read-only after creation
     */
    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    private String tierId;             // UUID

    /**
     * MongoDB objectId of the ACTIVE version this DRAFT modifies.
     * Null for new tiers.
     */
    private String parentId;

    private Integer slabId;            // null until APPROVE; set from MySQL program_slabs.id

    @Builder.Default
    private Integer version = 1;       // GUARDRAIL: G-10 — optimistic locking via version field

    // --- Core fields ---
    @NotNull
    private Long orgId;                // GUARDRAIL: G-07 — all documents scoped to org

    @NotNull
    private Integer programId;

    @NotBlank
    @Size(max = 100)
    private String name;

    @Size(max = 500)
    private String description;

    private String colorCode;

    @NotNull
    private Integer serialNumber;

    @NotNull
    private TierStatus status;         // DRAFT | PENDING_APPROVAL | ACTIVE | STOPPED

    private String metadata;           // max 30 chars (SlabMetaData JSON)

    // --- Strategy configs (full doc stored here, synced to MySQL strategies on APPROVE) ---
    @Valid
    private EligibilityConfig eligibility;

    @Valid
    private ValidityConfig validity;

    @Valid
    private RenewalConfig renewal;

    @Valid
    private DowngradeConfig downgrade;

    @Valid
    private UpgradeBonusConfig upgradeBonus;

    // --- Audit ---
    private Integer createdBy;
    private Integer lastModifiedBy;

    // GUARDRAIL: G-01 — Instant not Date
    private Instant createdOn;
    private Instant lastModifiedOn;

    private String comments;           // populated on REJECT
}
```

**Note (C6):** `UnifiedPromotion` stores `Date` for `startDate`/`endDate` but this is promotion-specific. `TierDocument` is new code and must comply with G-01 by using `Instant`. The existing `Metadata.java` timestamp pattern (using `Date`) is NOT replicated here.

---

### 3.12 TierRepository (MongoDB repository)

- **Package**: `com.capillary.intouchapiv3.tier`
- **Extends**: `MongoRepository<TierDocument, String>`
- **Annotations**: `@Repository`
- **Discovered from**: `UnifiedPromotionRepository.java` — exact same pattern: `extends MongoRepository<T, String>`, `@Query` with MongoDB JSON predicate syntax, `Optional<T>` for single results, `List<T>` for collections.
- **Imports**: `org.springframework.data.mongodb.repository.MongoRepository`, `org.springframework.data.mongodb.repository.Query`, `org.springframework.stereotype.Repository`, `java.util.Optional`, `java.util.List`
- **Maven dependency**: `spring-data-mongodb` already in module

```java
package com.capillary.intouchapiv3.tier;

@Repository
public interface TierRepository extends MongoRepository<TierDocument, String> {

    // Find by immutable tierId + orgId (G-07: always scope to org)
    @Query("{'tierId': ?0, 'orgId': ?1}")
    Optional<TierDocument> findByTierIdAndOrgId(String tierId, Long orgId);

    // List all tiers for a program (GUARDRAIL: G-07 — both orgId + programId required)
    @Query("{'orgId': ?0, 'programId': ?1}")
    List<TierDocument> findByOrgIdAndProgramId(Long orgId, Integer programId);

    // List active tiers only (excludes STOPPED)
    @Query("{'orgId': ?0, 'programId': ?1, 'status': {$nin: ['STOPPED']}}")
    List<TierDocument> findActiveTiersByOrgIdAndProgramId(Long orgId, Integer programId);

    // Find by MongoDB objectId + orgId (for direct ID lookup)
    @Query("{'_id': ?0, 'orgId': ?1}")
    Optional<TierDocument> findByObjectIdAndOrgId(String objectId, Long orgId);

    // Find PENDING_APPROVAL tiers for a program (used in APPROVE idempotency check)
    @Query("{'orgId': ?0, 'programId': ?1, 'status': 'PENDING_APPROVAL'}")
    List<TierDocument> findPendingApprovalByOrgIdAndProgramId(Long orgId, Integer programId);

    // Check if a tier with given serialNumber already exists (for insertion validation)
    @Query("{'orgId': ?0, 'programId': ?1, 'serialNumber': ?2, 'status': {$nin: ['STOPPED']}}")
    Optional<TierDocument> findByOrgIdAndProgramIdAndSerialNumber(Long orgId, Integer programId, Integer serialNumber);

    // Find DRAFT of an ACTIVE tier (for PUT on ACTIVE tier — creates new draft)
    @Query("{'parentId': ?0, 'orgId': ?1, 'status': 'DRAFT'}")
    Optional<TierDocument> findDraftByParentIdAndOrgId(String parentId, Long orgId);
}
```

---

### 3.13 TierValidator (custom business validation)

- **Package**: `com.capillary.intouchapiv3.tier.validation`
- **Extends**: none
- **Annotations**: `@Component`
- **Discovered from**: `UnifiedPromotionValidatorService.java` (validator as `@Component`, injected into facade)
- **Imports**: `org.springframework.stereotype.Component`, `com.capillary.intouchapiv3.models.exceptions.InvalidInputException`, `java.util.List`

```java
package com.capillary.intouchapiv3.tier.validation;

@Component
public class TierValidator {

    /**
     * Validate a new tier request: threshold ordering, KPI type immutability.
     * Called in TierFacade.createTier() and TierFacade.updateTier().
     * GUARDRAIL: G-02.3 — fail fast with descriptive errors
     * GUARDRAIL: G-07 — orgId required for existing-tier lookups
     *
     * @throws InvalidInputException if any business rule is violated (includes field + rule name)
     */
    public void validateCreate(TierRequest request,
                               List<TierDocument> existingTiers,
                               Long orgId,
                               Integer programId) throws InvalidInputException;

    /**
     * Validate an update request (PUT): same rules as create but excludes self from threshold check.
     */
    public void validateUpdate(String tierId,
                               TierRequest request,
                               List<TierDocument> existingTiers,
                               Long orgId,
                               Integer programId) throws InvalidInputException;

    /**
     * Validate soft-delete pre-conditions.
     * Checks: not base tier, no members, not downgrade target, no partner sync reference.
     * GUARDRAIL: G-02.3 — fail fast with descriptive error per violated rule
     */
    public void validateDelete(TierDocument tier,
                               Long memberCount,
                               List<TierDocument> allActiveTiers) throws InvalidInputException;

    /**
     * Validate status transition.
     * GUARDRAIL: G-02.7 — all TierStatus cases handled
     */
    public void validateStatusTransition(TierStatus currentStatus,
                                         TierAction action) throws InvalidInputException;

    /**
     * Validate REJECT requires a comment.
     */
    public void validateRejectComment(TierAction action, String comment) throws InvalidInputException;

    /**
     * Validate KPI type immutability: if existing tiers exist for the program,
     * new tier's currentValueType must match.
     * PI-1 requirement.
     */
    public void validateKpiTypeConsistency(String newCurrentValueType,
                                           List<TierDocument> existingTiers) throws InvalidInputException;

    /**
     * Validate threshold ordering: new tier's thresholdValue must be strictly
     * greater than previous tier and strictly less than next tier (by serialNumber).
     */
    public void validateThresholdOrdering(Integer serialNumber,
                                          Double thresholdValue,
                                          List<TierDocument> existingTiers,
                                          String excludeTierId) throws InvalidInputException;
}
```

---

### 3.14 TierFacade (business orchestration)

- **Package**: `com.capillary.intouchapiv3.tier`
- **Extends**: none
- **Annotations**: `@Component`
- **Discovered from**: `UnifiedPromotionFacade.java` — `@Component`, field `@Autowired` injection, catches `InvalidInputException` / `NotFoundException` / `ServiceException`, delegates to repository + Thrift service
- **Imports**: `org.springframework.stereotype.Component`, `org.springframework.beans.factory.annotation.Autowired`, `com.capillary.intouchapiv3.models.exceptions.*`, `com.capillary.intouchapiv3.services.thrift.PointsEngineRulesThriftService`, `com.capillary.shopbook.pointsengine.endpoint.api.external.*`, `java.time.Instant`, `java.util.*`
- **Maven dependency**: all already in module (spring-context, thrift stubs via pointsengine jar)

```java
package com.capillary.intouchapiv3.tier;

@Component
public class TierFacade {

    @Autowired
    private TierRepository tierRepository;

    @Autowired
    private PointsEngineRulesThriftService pointsEngineRulesThriftService;

    @Autowired
    private TierValidator tierValidator;

    // ─── CREATE ────────────────────────────────────────────────────────────────

    /**
     * Creates a new tier in DRAFT status in MongoDB.
     * Validates: Bean Validation already applied at controller (@Valid).
     * Additional business rules: threshold ordering, KPI type immutability.
     * GUARDRAIL: G-07 — orgId flows through all MongoDB queries
     * GUARDRAIL: G-01 — uses Instant.now() for createdOn / lastModifiedOn
     *
     * @param orgId   tenant scope (from AbstractBaseAuthenticationToken)
     * @param userId  authenticated user (for audit)
     * @param request tier configuration
     * @return TierResponse with status=DRAFT, slabId=null, memberCount=null
     * @throws InvalidInputException on threshold/KPI validation failure
     */
    public TierResponse createTier(Long orgId, Integer userId, TierRequest request)
            throws InvalidInputException;

    // ─── READ ──────────────────────────────────────────────────────────────────

    /**
     * Get single tier by tierId.
     * For ACTIVE tiers: fetches memberCount via Thrift.
     * GUARDRAIL: G-02.2 — returns Optional internally, throws NotFoundException if absent
     *
     * @throws NotFoundException if tierId not found for orgId (G-07)
     */
    public TierResponse getTier(Long orgId, String tierId) throws NotFoundException;

    /**
     * List tiers for a program.
     * Fetches tiers from MongoDB, then fetches memberCount map via single Thrift call
     * (getMemberCountPerSlab) and merges. GUARDRAIL: G-04.1 — single batch Thrift call
     * not N+1.
     * GUARDRAIL: G-02.1 — returns empty list, never null
     */
    public List<TierResponse> listTiers(Long orgId, Integer programId,
                                        boolean includeInactive);

    // ─── UPDATE ────────────────────────────────────────────────────────────────

    /**
     * Update tier configuration (PUT — full replace).
     * Only DRAFT tiers can be updated directly.
     * ACTIVE tiers: creates a new DRAFT with parentId set to the ACTIVE tier's objectId.
     * GUARDRAIL: G-10 — version check on MongoDB document before save
     *
     * @throws NotFoundException    if tierId not found
     * @throws InvalidInputException if tier is in STOPPED status (cannot update)
     */
    public TierResponse updateTier(Long orgId, Integer userId, String tierId,
                                   TierRequest request)
            throws NotFoundException, InvalidInputException;

    // ─── DELETE ────────────────────────────────────────────────────────────────

    /**
     * Soft-delete a tier. Validates all pre-conditions before calling Thrift.
     * For ACTIVE tiers: calls deactivateSlab Thrift method (sets is_active=0 in MySQL).
     * For DRAFT tiers: removes from MongoDB only.
     * GUARDRAIL: G-07 — Thrift call includes orgId
     * GUARDRAIL: R-3 (cache eviction) — handled by deactivateSlab Thrift impl
     *
     * @throws NotFoundException     if tierId not found
     * @throws InvalidInputException if any validation fails (returns structured error per rule):
     *                                - TIER_IS_BASE_TIER
     *                                - TIER_HAS_MEMBERS (includes count)
     *                                - TIER_IS_DOWNGRADE_TARGET
     *                                - TIER_HAS_PARTNER_SYNC_REFERENCE
     */
    public void deleteTier(Long orgId, String tierId)
            throws NotFoundException, InvalidInputException;

    // ─── STATUS CHANGE ─────────────────────────────────────────────────────────

    /**
     * Handle status transition for a tier.
     * Delegates to action-specific private methods.
     * GUARDRAIL: G-10 — APPROVE checks version field to detect concurrent approval
     *
     * @throws NotFoundException     if tierId not found
     * @throws InvalidInputException on invalid transition or business rule failure
     */
    public TierResponse changeTierStatus(Long orgId, Integer userId, String tierId,
                                          TierStatusRequest request)
            throws NotFoundException, InvalidInputException;

    // ─── APPROVE (internal — called by changeTierStatus) ──────────────────────

    /**
     * APPROVE flow:
     * 1. Reload TierDocument, verify status=PENDING_APPROVAL, check version (optimistic lock).
     * 2. Build SlabInfo from TierDocument.
     * 3. Call Thrift: createOrUpdateSlab(slabInfo, orgId, userId, Instant.now().toEpochMilli(), serverReqId).
     * 4. On Thrift success: set status=ACTIVE, store slabId, update lastModifiedOn, save to MongoDB.
     * 5. On Thrift failure: revert MongoDB status to PENDING_APPROVAL, throw ServiceException.
     *    R-6: MongoDB rollback on Thrift failure.
     * 6. R-8 Idempotency: if slabId already set on document, return existing TierResponse (already approved).
     *
     * GUARDRAIL: G-01 — Instant.now().toEpochMilli() for Thrift lastModifiedOn (long)
     * GUARDRAIL: G-05.1 — "transactional-like" with explicit rollback on failure
     */
    private TierResponse approveTier(TierDocument tier, Long orgId, Integer userId)
            throws InvalidInputException;

    // ─── MAPPING ───────────────────────────────────────────────────────────────

    /**
     * Converts TierDocument to TierResponse.
     * Accepts optional memberCount (null for DRAFT/PENDING_APPROVAL).
     * GUARDRAIL: G-02.1 — returns empty collections, not null
     */
    private TierResponse toResponse(TierDocument doc, Long memberCount);
}
```

---

### 3.15 TierController (REST endpoints)

- **Package**: `com.capillary.intouchapiv3.resources`
- **Extends**: none
- **Annotations**: `@RestController`, `@RequestMapping("/v3/tiers")`
- **Discovered from**: `UnifiedPromotionController.java` — exact same structure: constructor injection with `@Autowired`, `AbstractBaseAuthenticationToken token` param on each method, `ResponseEntity<ResponseWrapper<T>>` return types, SLF4J logger
- **Imports**: `com.capillary.intouchapiv3.auth.AbstractBaseAuthenticationToken`, `com.capillary.intouchapiv3.auth.IntouchUser`, `com.capillary.intouchapiv3.models.ResponseWrapper`, `org.springframework.web.bind.annotation.*`, `org.springframework.http.*`, `jakarta.validation.Valid`, `jakarta.servlet.http.HttpServletRequest`
- **Maven dependency**: all already in module

```java
package com.capillary.intouchapiv3.resources;

@RestController
@RequestMapping("/v3/tiers")
public class TierController {

    private static final Logger logger = LoggerFactory.getLogger(TierController.class);

    private final TierFacade tierFacade;

    @Autowired
    public TierController(TierFacade tierFacade) {
        this.tierFacade = tierFacade;
    }

    /**
     * List tiers for a program.
     * GUARDRAIL: G-07 — orgId from token, programId from query param
     * GUARDRAIL: G-04.2 — tiers list is small (<10) for a program; pagination not required
     *           but programId is REQUIRED to avoid full-scan.
     */
    @GetMapping(produces = "application/json")
    public ResponseEntity<ResponseWrapper<List<TierResponse>>> listTiers(
            @RequestParam Integer programId,
            @RequestParam(required = false, defaultValue = "false") boolean includeInactive,
            AbstractBaseAuthenticationToken token);

    /**
     * Get single tier by tierId.
     */
    @GetMapping(value = "/{tierId}", produces = "application/json")
    public ResponseEntity<ResponseWrapper<TierResponse>> getTier(
            @PathVariable String tierId,
            AbstractBaseAuthenticationToken token);

    /**
     * Create a new tier in DRAFT status.
     * Bean Validation applied via @Valid.
     */
    @PostMapping(produces = "application/json")
    public ResponseEntity<ResponseWrapper<TierResponse>> createTier(
            @Valid @RequestBody TierRequest request,
            AbstractBaseAuthenticationToken token);

    /**
     * Update a tier (PUT — full replace).
     */
    @PutMapping(value = "/{tierId}", produces = "application/json")
    public ResponseEntity<ResponseWrapper<TierResponse>> updateTier(
            @PathVariable String tierId,
            @Valid @RequestBody TierRequest request,
            AbstractBaseAuthenticationToken token);

    /**
     * Soft-delete a tier.
     */
    @DeleteMapping(value = "/{tierId}", produces = "application/json")
    public ResponseEntity<ResponseWrapper<Void>> deleteTier(
            @PathVariable String tierId,
            AbstractBaseAuthenticationToken token);

    /**
     * Status change (submit for approval, approve, reject, stop).
     * GUARDRAIL: G-03.3 — auth enforced by HttpSecurityConfig globally
     */
    @PostMapping(value = "/{tierId}/status", produces = "application/json")
    public ResponseEntity<ResponseWrapper<TierResponse>> changeTierStatus(
            @PathVariable String tierId,
            @Valid @RequestBody TierStatusRequest request,
            AbstractBaseAuthenticationToken token);
}
```

**Error handling pattern (from UnifiedPromotionController):**
- `InvalidInputException` → `400 BAD_REQUEST` with `ResponseWrapper` containing `errors[{code, message}]`
- `NotFoundException` → `404 NOT_FOUND`
- Unexpected exceptions → `500 INTERNAL_SERVER_ERROR`
- All handled in controller catch blocks following the `enrol()` method pattern in `UnifiedPromotionController.java`

---

### 3.16 EmfMongoConfig modification

- **File**: `com.capillary.intouchapiv3.config.EmfMongoConfig`
- **Modification**: Add `TierRepository.class` to `includeFilters`
- **Discovered from**: `EmfMongoConfig.java` line 32 — `classes = {UnifiedPromotionRepository.class}`
- **CRITICAL**: Without this modification, `TierRepository` uses the primary `mongoTemplate` (wrong database), not `emfMongoTemplate`. Verified C7.

```java
// BEFORE:
includeFilters = @ComponentScan.Filter(
    type = FilterType.ASSIGNABLE_TYPE,
    classes = {UnifiedPromotionRepository.class}
)

// AFTER:
includeFilters = @ComponentScan.Filter(
    type = FilterType.ASSIGNABLE_TYPE,
    classes = {
        UnifiedPromotionRepository.class,
        TierRepository.class               // ADD THIS
    }
)
```

**Additional import to add:**
```java
import com.capillary.intouchapiv3.tier.TierRepository;
```

---

### 3.17 PointsEngineRulesThriftService additions (intouch-api-v3)

- **File**: `com.capillary.intouchapiv3.services.thrift.PointsEngineRulesThriftService`
- **Modification**: Add two new methods following the exact pattern of `createOrUpdateSlab` and existing methods

```java
/**
 * Creates or updates a slab in MySQL via EMF Thrift.
 * Called during APPROVE flow.
 * GUARDRAIL: G-01 — lastModifiedOn is epoch millis (long) from Instant
 *
 * @throws EMFThriftException wrapping PointsEngineRuleServiceException or TException
 */
public SlabInfo createOrUpdateSlab(SlabInfo slabInfo,
                                   int orgId,
                                   int lastModifiedBy,
                                   long lastModifiedOn,
                                   String serverReqId) throws Exception;

/**
 * Deactivates a slab: sets is_active=0, evicts cache, updates strategy JSON/CSV.
 * Called during STOP (soft-delete) flow.
 * GUARDRAIL: R-3 — cache eviction done in EMF impl, not here
 *
 * @param slabId  MySQL program_slabs.id
 * @throws EMFThriftException wrapping downstream exception
 */
public BoolRes deactivateSlab(int slabId, int programId, int orgId,
                               int lastModifiedBy,
                               long lastModifiedOn,
                               String serverReqId) throws Exception;

/**
 * Returns member count per slab for a program.
 * Single batch call from listTiers() — avoids N+1 (GUARDRAIL: G-04.1).
 *
 * @return Map<Integer slabId, Long memberCount>; empty map if no slabs
 * GUARDRAIL: G-02.1 — never null, returns empty map
 */
public Map<Integer, Long> getMemberCountPerSlab(int programId, int orgId,
                                                 String serverReqId) throws Exception;
```

**Note on Thrift IDL:** These methods do NOT yet exist in the Thrift IDL. They must be added to `pointsengine_rules.thrift` before generating stubs. See Section 5 (Thrift IDL changes).

---

## 4. emf-parent Types

---

### 4.1 ProgramSlab entity — field addition

- **File**: `com.capillary.shopbook.points.entity.ProgramSlab`
- **Modification**: Add `isActive` field with JPA mapping
- **Discovered from**: `ProgramSlab.java` — uses `@Basic @Column`, manual getter/setter (NO Lombok), `javax.persistence.*` imports
- **GUARDRAIL**: G-09.1 — column has `DEFAULT 1` in DDL (MIG-01), old code ignores field, safe to add

```java
// Add after the metadata field (line 93 in current ProgramSlab.java):

@Basic
@Column(name = "is_active", nullable = false)
private boolean isActive = true;   // GUARDRAIL: G-09.3 — default true for new inserts

public boolean isActive() {
    return isActive;
}

public void setActive(boolean isActive) {
    this.isActive = isActive;
}
```

**Imports to add:** none (uses `@Basic @Column` already imported)

---

### 4.2 PeProgramSlabDao — query additions and modifications

- **File**: `com.capillary.shopbook.points.dao.PeProgramSlabDao`
- **Package**: `com.capillary.shopbook.points.dao`
- **Extends**: `GenericDao<ProgramSlab, ProgramSlabPK>` (from `com.capillary.commons.data.dao`)
- **Annotations**: `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`
- **Discovered from**: `PeProgramSlabDao.java` — JPQL `@Query`, `?1 ?2 ?3` positional params

**3 existing queries to MODIFY** (add `AND s.isActive = true`):

```java
// BEFORE:
@Query("SELECT s FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2")
List<ProgramSlab> findByProgram(int orgId, int programId);

// AFTER: (GUARDRAIL: G-05 — soft-delete filter at DAO layer)
@Query("SELECT s FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2 AND s.isActive = true")
List<ProgramSlab> findByProgram(int orgId, int programId);

// BEFORE:
@Query("SELECT ps FROM ProgramSlab ps WHERE ps.pk.orgId = ?1 AND ps.program.pk.id = ?2 and ps.serialNumber = ?3")
ProgramSlab findByProgramSlabNumber(int orgId, int programId, int programSlabNumber);

// AFTER:
@Query("SELECT ps FROM ProgramSlab ps WHERE ps.pk.orgId = ?1 AND ps.program.pk.id = ?2 AND ps.serialNumber = ?3 AND ps.isActive = true")
ProgramSlab findByProgramSlabNumber(int orgId, int programId, int programSlabNumber);

// BEFORE:
@Query("SELECT COUNT(*) FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2")
Long findNumberOfSlabs(int orgId, int programId);

// AFTER:
@Query("SELECT COUNT(*) FROM ProgramSlab s WHERE s.pk.orgId = ?1 AND s.program.pk.id = ?2 AND s.isActive = true")
Long findNumberOfSlabs(int orgId, int programId);
```

**1 new query to ADD** (R-4 resolution — safe `findActiveById` without overriding generic `findById`):

```java
/**
 * Find a ProgramSlab by composite PK, only if is_active = true.
 * NEVER overrides generic findById(). Added as a separate method.
 * R-4 resolution from session memory.
 * GUARDRAIL: G-07 — orgId in PK
 */
@Query("SELECT s FROM ProgramSlab s WHERE s.pk.id = ?1 AND s.pk.orgId = ?2 AND s.isActive = true")
Optional<ProgramSlab> findActiveById(int id, int orgId);
```

**Imports to add:** `java.util.Optional`

---

### 4.3 PeCustomerEnrollmentDao — new query

- **File**: `com.capillary.shopbook.points.dao.PeCustomerEnrollmentDao`
- **Discovered from**: `PeCustomerEnrollmentDao.java` — same `@Query`, `@Param`, `GenericDao` pattern
- **Annotations**: same `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`

```java
/**
 * Count active enrolled members per slab, for a given set of slabIds in one query.
 * Supports both: (a) member count in GET /tiers response, and
 *                (b) soft-delete pre-condition validation (count must be 0).
 *
 * Uses index: idx_ce_slab_count (org_id, program_id, current_slab_id, is_active) — MIG-02.
 * GUARDRAIL: G-07 — orgId and programId always in WHERE
 * GUARDRAIL: G-04.1 — batch query (IN clause) prevents N+1
 * GUARDRAIL: G-04.4 — backed by idx_ce_slab_count index (MIG-02)
 *
 * @return Map<Integer slabId, Long memberCount>
 */
@Query("SELECT ce.currentSlabId, COUNT(ce.pk.id) FROM CustomerEnrollment ce "
     + "WHERE ce.pk.orgId = :orgId AND ce.program.pk.id = :programId "
     + "AND ce.currentSlabId IN :slabIds AND ce.isActive = true "
     + "GROUP BY ce.currentSlabId")
@QueryHints({@QueryHint(name = "org.hibernate.readOnly", value = "true")})
List<Object[]> countMembersPerSlab(@Param("orgId") int orgId,
                                   @Param("programId") int programId,
                                   @Param("slabIds") List<Integer> slabIds);
```

**Note:** Returns `List<Object[]>` where `[0]=slabId (Integer)` and `[1]=count (Long)`. Caller maps to `Map<Integer, Long>`.

**Imports to add:** `javax.persistence.QueryHint`, `org.springframework.data.jpa.repository.QueryHints`, `org.springframework.data.repository.query.Param` (already imported), `java.util.List`

---

### 4.4 PointsEngineRuleConfigThriftImpl — new methods

- **File**: `com.capillary.shopbook.pointsengine.endpoint.impl.external.PointsEngineRuleConfigThriftImpl`
- **Annotations**: `@Service @ExposedCall(thriftName = "pointsengine-rules")`, implements `Iface`
- **Discovered from**: `PointsEngineRuleConfigThriftImpl.java` — method pattern: `@Override @Trace(dispatcher = true) @MDCData(...)`, `try/catch` wraps to `PointsEngineRuleServiceException`, cache evict after mutation

```java
/**
 * Deactivates a slab: sets is_active=0 in program_slabs, evicts cache,
 * updates SLAB_UPGRADE threshold CSV and SLAB_DOWNGRADE config JSON.
 *
 * GUARDRAIL: G-05 — strategy JSON update prevents R-1/R-2 evaluation engine mismatch
 * GUARDRAIL: R-3 — cache eviction via cacheEvictHelper.evictProgramIdCache()
 * GUARDRAIL: G-10 — R-10 resolution: must be @Transactional to protect multi-step write
 *
 * @param slabId  MySQL program_slabs.id
 * @param programId  for strategy lookup and cache eviction
 * @param orgId  tenant scope
 * @throws PointsEngineRuleServiceException on validation/persistence failure
 * @throws TException on Thrift framework error
 */
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
@Transactional("warehouse")   // R-10 resolution: multi-step write must be transactional
public BoolRes deactivateSlab(int slabId, int programId, int orgId,
                               int lastModifiedBy, long lastModifiedOn,
                               String serverReqId)
        throws PointsEngineRuleServiceException, TException;

/**
 * Returns member count per slab for a program (batch).
 * Delegates to PeCustomerEnrollmentDao.countMembersPerSlab().
 * GUARDRAIL: G-04.1 — single DB query, not per-slab N+1
 * GUARDRAIL: G-02.1 — returns empty map, not null
 *
 * @return BoolRes with encoded JSON payload, or separate struct (see Thrift IDL note below)
 */
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public MemberCountPerSlabResponse getMemberCountPerSlab(int programId, int orgId,
                                                         String serverReqId)
        throws PointsEngineRuleServiceException, TException;
```

**Transaction annotation note (R-10, C4):** `createOrUpdateSlab` at line 1666 has no `@Transactional`. The new `deactivateSlab` involves at minimum 2 writes (UPDATE `program_slabs`, UPDATE `strategies`). Adding `@Transactional("warehouse")` is required. Verify with developer that `"warehouse"` is the correct transaction manager name — this matches `PeProgramSlabDao`'s `@Transactional(value = "warehouse", ...)`.

**Imports to add:**
```java
import org.springframework.transaction.annotation.Transactional;
```

---

## 5. Thrift IDL Changes (thrifts repo)

**File**: `thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift`

### 5.1 New struct: MemberCountEntry

```thrift
/**
 * A single slab-to-member-count mapping entry.
 */
struct MemberCountEntry {
    1: required i32 slabId;
    2: required i64 memberCount;
}
```

### 5.2 New struct: MemberCountPerSlabResponse

```thrift
/**
 * Response for getMemberCountPerSlab.
 * Returns member counts for all slabs of a program in a single response.
 */
struct MemberCountPerSlabResponse {
    1: required list<MemberCountEntry> entries;
}
```

### 5.3 New methods in PointsEngineRuleService

Add after `createOrUpdateSlab` (line 1184):

```thrift
/**
 * Deactivates a slab: sets is_active=0 in program_slabs,
 * updates SLAB_UPGRADE CSV and SLAB_DOWNGRADE JSON, evicts cache.
 * R-1/R-2/R-3 mitigation from analyst findings.
 */
BoolRes deactivateSlab(1:i32 slabId, 2:i32 programId, 3:i32 orgId,
                       4:i32 lastModifiedBy, 5:i64 lastModifiedOn, 6:string serverReqId)
    throws (1: PointsEngineRuleServiceException ex);

/**
 * Returns member count per slab for all active slabs of a program.
 * Backed by customer_enrollment composite index (idx_ce_slab_count).
 */
MemberCountPerSlabResponse getMemberCountPerSlab(1:i32 programId, 2:i32 orgId,
                                                  3:string serverReqId)
    throws (1: PointsEngineRuleServiceException ex);
```

### 5.4 Backward compatibility (C7)

Both new methods are **additive only** — no existing struct or method is modified. The `SlabInfo` struct does NOT need an `active` field added (soft-delete is handled in MySQL via `is_active` column, not surfaced in `SlabInfo`). Existing callers of `createOrUpdateSlab`, `getAllSlabs`, `createSlabAndUpdateStrategies` are unaffected.

---

## 6. cc-stack-crm (DDL Reference)

Reference only — see `01b-migrator.md` for full scripts. No new types.

```sql
-- MIG-01: program_slabs.sql — add is_active column
`is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT 'Soft-delete flag: 1=active, 0=inactive (stopped tier)',

-- MIG-02: customer_enrollment.sql — add member count index
KEY `idx_ce_slab_count` (`org_id`,`program_id`,`current_slab_id`,`is_active`)
```

---

## 7. Guardrail Enforcement Summary

| Guardrail | Where Enforced | How |
|-----------|---------------|-----|
| G-01 (Instant not Date) | `TierDocument`, `TierResponse` | Field types: `Instant createdOn`, `Instant lastModifiedOn`. Thrift `lastModifiedOn` param: `Instant.now().toEpochMilli()` → `long` |
| G-02 (Null safety) | `TierRepository`, `TierFacade`, `TierValidator` | `Optional<T>` for nullable single returns; `List` returns empty list not null; `Objects.requireNonNull` at entry |
| G-03 (Security) | `TierController` | `AbstractBaseAuthenticationToken` enforced by `HttpSecurityConfig`; orgId from token (not request param) |
| G-05 (Data integrity) | `TierFacade.approveTier()` | Explicit rollback to PENDING_APPROVAL on Thrift failure; version field check before approve |
| G-06 (API design) | `TierController`, `TierResponse` | `ResponseWrapper<T>` for all responses; `InvalidInputException` maps to 400; `NotFoundException` maps to 404 |
| G-07 (Multi-tenancy) | ALL layers | `orgId` flows from token → facade → repository query → Thrift param → DAO JPQL. Every MongoDB query includes `orgId`. Every JPQL query includes `orgId`. |
| G-10 (Concurrency) | `TierDocument.version` | Version field incremented on each save; APPROVE reads version before write; concurrent APPROVE returns 409/error |
| R-3 (Cache eviction) | `PointsEngineRuleConfigThriftImpl.deactivateSlab()` | `cacheEvictHelper.evictProgramIdCache(orgId, programId)` — same pattern as `createOrUpdateSlab` line 1686 |
| R-6 (Rollback on failure) | `TierFacade.approveTier()` | If Thrift fails: revert MongoDB status to PENDING_APPROVAL before propagating error |
| R-8 (Idempotency) | `TierFacade.approveTier()` | If `slabId` already set on document: return existing TierResponse without re-calling Thrift |
| R-10 (Transaction) | `PointsEngineRuleConfigThriftImpl.deactivateSlab()` | `@Transactional("warehouse")` annotation |
| PI-1 (KPI immutability) | `TierValidator.validateKpiTypeConsistency()` | Called in `TierFacade.createTier()` |

---

## 8. Open Questions for Developer / QA

1. **Q-D1 (C4):** `PeCustomerEnrollmentDao.countMembersPerSlab()` returns `List<Object[]>` for JPQL `GROUP BY`. Confirm whether the `GenericDao` base class (from `com.capillary.commons.data.dao`) supports this return type, or whether a `@Query` with `nativeQuery = true` is preferred instead. _Affects: PeCustomerEnrollmentDao signature._

2. **Q-D2 (C3):** `deactivateSlab` must update the SLAB_UPGRADE threshold CSV. The exact logic for rebuilding the CSV after removing one slab entry needs to be verified against `ThresholdBasedSlabUpgradeStrategyImpl` to confirm the CSV rebuild algorithm. R-1 mitigation depends on getting this correct. _Affects: PointsEngineRuleConfigThriftImpl.deactivateSlab() implementation._

3. **Q-D3 (C4):** Does `PointsEngineRuleEditor.createOrUpdateSlab()` (the internal editor, not the Thrift impl) automatically update the SLAB_UPGRADE strategy threshold CSV when a slab's threshold changes on update? If yes, the APPROVE flow (which calls `createOrUpdateSlab` Thrift) handles this transparently. If no, additional strategy update calls are needed in `deactivateSlab`. _Session memory A-2 — unresolved._

4. **Q-D4 (C3):** `@Transactional("warehouse")` on `deactivateSlab` — verify the transaction manager name. The PeProgramSlabDao annotation uses `value = "warehouse"`. Confirm this matches the JPA transaction manager bean name in emf-parent Spring config.

5. **Q-D5 (C4):** The `TierFacade.updateTier()` method for ACTIVE tiers: should it create a new DRAFT copy (as described) or should it update in-place to PENDING_APPROVAL? The HLD says PUT only, but doesn't specify whether ACTIVE tiers get a copy-on-write pattern. Following UnifiedPromotion's `parentId` pattern would create a DRAFT copy with `parentId` pointing to the ACTIVE. Confirm this is the intended behavior for UPDATE on ACTIVE tier.

---

## 9. Assumptions Made

- **A-D1 (C6):** `TierRepository` uses the EMF MongoDB namespace — registered in `EmfMongoConfig.includeFilters`. Evidence: `UnifiedPromotionRepository` uses the same registration pattern and also stores loyalty config data.
- **A-D2 (C6):** `AbstractBaseAuthenticationToken.getIntouchUser().getOrgId()` returns `Long` (not `int`). Evidence: `UnifiedPromotionFacade` and `UnifiedPromotionController` use `user.getOrgId()` typed as `Long` throughout.
- **A-D3 (C6):** `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)` on `PeProgramSlabDao` means the DAO participates in but does NOT open transactions. Transaction must be opened at the service/Thrift-impl layer. Evidence: all DAO interfaces in `com.capillary.shopbook.points.dao` use the same `SUPPORTS` propagation.
- **A-D4 (C5):** `BoolRes` (existing Thrift struct: `{optional bool success; optional PointsEngineRuleServiceException ex}`) is appropriate as the return type for `deactivateSlab`. Evidence: `BoolRes` is used for `publishPeConfig` and other one-way commands.
- **A-D5 (C5):** `programId` must be passed to `deactivateSlab` (in addition to `slabId`) because `cacheEvictHelper.evictProgramIdCache(orgId, programId)` requires both. Evidence: `createOrUpdateSlab` at line 1686 uses `slabInfo.getProgramId()` for the eviction call.

---

*Phase 7 complete. 3 new enums, 8 new DTOs, 1 MongoDB document, 1 MongoDB repository, 1 facade, 1 controller, 1 validator, 2 Thrift IDL structs, 2 new Thrift methods, and 4 emf-parent modifications fully specified.*
