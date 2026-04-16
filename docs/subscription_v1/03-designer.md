# LLD — Subscription Program Revamp (E3)
> Date: 2026-04-14 | Phase: 7 (Designer) | Rework: 2026-04-15 (12 critical gaps — GAP-1 through GAP-11, ADR-18)
> Ticket: aidlc/subscription_v1
> Author: Designer Agent (Claude Sonnet 4.6)

---

## Pattern Decisions

All patterns below are C7 — sourced directly from primary codebase files.

### A. MongoDB Repository Pattern
**Evidence**: `UnifiedPromotionRepository.java` (line 18)
```java
public interface UnifiedPromotionRepository extends MongoRepository<UnifiedPromotion, String>, UnifiedPromotionRepositoryCustom
```
- Extends `MongoRepository<T, String>` where `String` = MongoDB ObjectId
- Annotated `@Repository`
- `@Query` annotations use MongoDB JSON notation: `{'fieldPath': ?0, 'nested.path': ?1}`
- Paginated queries use `Page<T>` + `Pageable` parameters
- Static `default` methods for compound query logic

**Prescription**: `SubscriptionProgramRepository` extends `MongoRepository<SubscriptionProgram, String>` annotated `@Repository`.

### B. MongoDB Document Pattern
**Evidence**: `UnifiedPromotion.java`
- Annotations: `@Data @Builder @NoArgsConstructor @AllArgsConstructor @Document(collection = "...") @IgnoreGenerated`
- No base class (plain POJO)
- `@Id` on `private String objectId` (MongoDB auto-generates ObjectId as String)
- Separate `unifiedPromotionId` UUID field that is the immutable business key (READ_ONLY)
- `@JsonProperty(access = JsonProperty.Access.READ_ONLY)` on the business UUID
- Nested objects as separate classes under `model/` subpackage
- No `@Indexed` on the doc itself — indexes managed externally
- `@Size`, `@Valid`, `@NotNull` on relevant fields
- **No `@Version` anywhere in existing codebase** — OQ-14 resolution: use Spring Data `@Version Long version` for optimistic lock on DRAFT documents

**Prescription**: `SubscriptionProgram` uses same pattern. `@Version` field added as `private Long version` (Spring Data MongoDB `@Version` is supported as of Spring Data MongoDB 3.x; it works with `MongoRepository.save()`).

### C. Controller Pattern
**Evidence**: `UnifiedPromotionController.java`
- `@RestController` at class level
- `@RequestMapping("/v3/promotions")` at class level
- Constructor injection via `@Autowired` on constructor (not field)
- Auth extraction: `AbstractBaseAuthenticationToken token` as method parameter → `token.getIntouchUser()` → `user.getOrgId()`
- Response type: `ResponseEntity<ResponseWrapper<T>>`
- No Swagger annotations used in existing code
- Exception handling: global `@ControllerAdvice` in `TargetGroupErrorAdvice` catches `NotFoundException`, `InvalidInputException`, `ServiceException`, `EMFThriftException`, `ConstraintViolationException`, `MethodArgumentNotValidException`
- HTTP status: 201 for POST (create), 200 for GET/PUT, error codes delegated to `TargetGroupErrorAdvice`

**Prescription**: `SubscriptionController` and `SubscriptionReviewController` follow exact same pattern. Global `TargetGroupErrorAdvice` already handles `NotFoundException` → 200 (with error body) and `InvalidInputException` → 400. New subscription-specific exceptions extend `RuntimeException` and are added to `TargetGroupErrorAdvice`.

### D. Service/Facade Pattern
**Evidence**: `UnifiedPromotionFacade.java` (line 57)
- `@Component` annotation (NOT `@Service`)
- `@Autowired` field injection (all dependencies)
- No base class
- Method-level `private` logger: `LoggerFactory.getLogger()`

**Prescription**: `SubscriptionFacade` uses `@Component` + `@Autowired` field injection. `SubscriptionPublishService` uses `@Service`. `MakerCheckerService` uses `@Service`.

### E. DTO Pattern
**Evidence**: `PromotionReviewRequest.java`
- `@Data @Builder @NoArgsConstructor @AllArgsConstructor`
- `jakarta.validation.constraints.*` for validation
- No `@JsonProperty` unless field name differs from Java convention
- No `@JsonIgnoreProperties` on request DTOs

**Evidence**: `Metadata.java` (nested doc)
- `@JsonIgnoreProperties(ignoreUnknown = true)`
- `@JsonFormat` for date formatting
- `@JsonAlias` for field name aliases
- `@NotBlank`, `@Size`, `@NotNull` validation

**Prescription**: DTOs use `@Data @Builder @NoArgsConstructor @AllArgsConstructor`. Validation via `jakarta.validation`. Jackson annotation `@JsonIgnoreProperties(ignoreUnknown = true)` on request DTOs. No Lombok `@Jacksonized` needed.

### F. PointsEngineRulesThriftService Pattern
**Evidence**: `PointsEngineRulesThriftService.java`
- `@Service @Loggable @Profile("!test")`
- `@Autowired @Lazy private PointsEngineRulesThriftService selfProxy` for cache proxy
- Client via `RPCService.rpcClient(PointsEngineRuleService.Iface.class, "emf-thrift-service", 9199, 60000)`
- Request ID: `CapRequestIdUtil.getRequestId()`
- Exception wrapping: all exceptions caught → throw `new EMFThriftException("...")`
- Import: `com.capillary.shopbook.pointsengine.endpoint.api.external.*`

**Prescription**: New methods in `PointsEngineRulesThriftService` follow the exact pattern: `getClient()` → Thrift call → catch Exception → throw `EMFThriftException`.

### G. Test Pattern
**Evidence**: `UnifiedPromotionControllerTest.java`
- JUnit 5 (`@ExtendWith(MockitoExtension.class)`)
- Mockito: `@InjectMocks`, `@Mock`
- No MockMvc — tests call controller methods directly
- `@BeforeEach` for setup
- `Assertions.assertEquals`, `Assertions.assertNotNull`
- `when(...).thenReturn(...)` + `verify(...)` for mock assertions
- Test method names: `testCreateUnifiedPromotion`, `testGetUnifiedPromotion` (camelCase with test prefix)
- Auth token constructed as anonymous `AbstractBaseAuthenticationToken` subclass

**Prescription**: Subscription tests follow the same pattern — JUnit 5, Mockito `@InjectMocks`/`@Mock`, direct method invocation, same auth-token construction.

### H. emf-parent Patterns
- `PointsEngineEndpointActionUtils`: all methods `public static` — utility class, no instance state
- `PartnerProgramLinkingActionImpl`: plain class, no Spring annotations, constructor-injected `PointsProgramConfig`, implements `PartnerProgramLinkingAction`
- `PointsEngineRuleService.saveSupplementaryPartnerProgramEntity`: conditional logic using `isSet*()` Thrift-generated methods (e.g., `partnerProgramThrift.isSetExpiryDate()`)

---

## Interface Definitions

### intouch-api-v3 — New Files

---

#### 1. `SubscriptionProgram.java` (MongoDB @Document)

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java`

```java
package com.capillary.intouchapiv3.unified.subscription;

import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionStatus;
import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionType;
import com.capillary.intouchapiv3.unified.subscription.enums.CycleType;
import com.capillary.intouchapiv3.unified.subscription.enums.MigrateOnExpiry;
import com.capillary.intouchapiv3.unified.subscription.enums.ReminderChannel;
import com.capillary.intouchapiv3.makechecker.ApprovableEntity;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.mongodb.core.mapping.Document;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "subscription_programs")
@JsonIgnoreProperties(ignoreUnknown = true)
public class SubscriptionProgram implements ApprovableEntity {

    /** MongoDB auto-generated ObjectId — the document primary key */
    @Id
    @JsonProperty("id")
    private String objectId;

    /**
     * Immutable business identifier (UUID). Assigned at creation. Constant across all
     * versions (DRAFT and its ACTIVE replacement share the same subscriptionProgramId
     * only for the initial create; edits-of-ACTIVE produce a NEW UUID for the draft).
     */
    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    private String subscriptionProgramId;

    /** Multi-tenancy key — every query MUST include this (G-07) */
    @NotNull
    private Long orgId;

    /** loyalty_program_id from EMF — 1:1 per KD-13 */
    @NotNull
    private Integer programId;

    /** State machine status */
    @NotNull
    private SubscriptionStatus status;

    /**
     * Spring Data MongoDB optimistic lock field (OQ-14 resolved).
     * Starts at 1. Incremented by MongoRepository.save() automatically.
     * Concurrent save() with stale version throws OptimisticLockingFailureException.
     * Also used as the version counter for parentId pattern (edit-of-ACTIVE).
     */
    @Version
    private Long version;

    /**
     * ObjectId (String) of the ACTIVE document this DRAFT was forked from.
     * Null for first-time creations. Set when PUT on ACTIVE triggers edit-of-ACTIVE flow.
     */
    private String parentId;

    /**
     * Populated post-approval with MySQL partner_programs.id.
     * Null during DRAFT/PENDING_APPROVAL. Used as SAGA idempotency key (RF-6).
     */
    private Integer mysqlPartnerProgramId;

    @NotBlank
    @Size(max = 255)
    private String name;

    @Size(max = 1000)
    private String description;

    @NotNull
    private SubscriptionType subscriptionType;

    @NotNull
    @Valid
    private Duration duration;

    @Valid
    private Expiry expiry;

    @Valid
    private Settings settings;

    @Valid
    private TierConfig tierConfig;

    @Builder.Default
    @Size(max = 500)
    private List<BenefitRef> benefits = new ArrayList<>();

    /** MongoDB-only. Max 5. Not written to MySQL via Thrift (KD-39, ADR-06). */
    @Builder.Default
    @Size(max = 5)
    private List<Reminder> reminders = new ArrayList<>();

    @Valid
    private CustomFields customFields;

    /** Free-text tag for grouped listing view (AC-06) */
    private String groupTag;

    @Valid
    private WorkflowMetadata workflowMetadata;

    /** Rejection comment OR approval note. Max 150 chars (mirrors UnifiedPromotion). */
    @Size(max = 150)
    private String comments;

    private String createdBy;
    private Instant createdAt;
    private String updatedBy;
    private Instant updatedAt;

    // -----------------------------------------------------------------------
    // ApprovableEntity interface implementation
    // -----------------------------------------------------------------------
    @Override public SubscriptionStatus getStatus()         { return status; }
    @Override public void setStatus(Object s)               { this.status = (SubscriptionStatus) s; }
    @Override public Long getVersion()                      { return version; }
    @Override public void setVersion(Long v)                { this.version = v; }
    @Override public String getParentId()                   { return parentId; }
    @Override public void setParentId(String pid)           { this.parentId = pid; }
    @Override public Long getOrgId()                        { return orgId; }

    // -----------------------------------------------------------------------
    // Nested value objects (inner static classes — mirrors UnifiedPromotion model/)
    // -----------------------------------------------------------------------

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class Duration {
        @NotNull
        private CycleType cycleType;
        @NotNull @Positive
        private Integer cycleValue;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class Expiry {
        /** UTC Instant. Overrides individual enrollment duration when set. */
        private Instant programExpiryDate;
        private MigrateOnExpiry migrateOnExpiry;
        /** MySQL partner_programs.backup_partner_program_id */
        private Integer migrationTargetProgramId;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class Settings {
        /** EMF ENABLE_PARTNER_PROGRAM_LINKING setting */
        private Boolean restrictToOneActivePerMember;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class TierConfig {
        /** Required when subscriptionType=TIER_BASED */
        private Integer linkedTierId;
        private Boolean tierDowngradeOnExit;
        /** Required when tierDowngradeOnExit=true */
        private Integer downgradeTargetTierId;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class BenefitRef {
        @NotNull
        private Long benefitId;
        private Instant addedOn;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class Reminder {
        @NotNull @Positive
        private Integer daysBeforeExpiry;
        @NotNull
        private ReminderChannel channel;
        /** Key-value pairs for communication template variables */
        private Map<String, String> communicationProperties;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class CustomFields {
        @Builder.Default
        private List<CustomFieldRef> meta    = new ArrayList<>();
        @Builder.Default
        private List<CustomFieldRef> link    = new ArrayList<>();
        @Builder.Default
        private List<CustomFieldRef> delink  = new ArrayList<>();
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class CustomFieldRef {
        private Long extendedFieldId;
        private String name;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class WorkflowMetadata {
        private String submittedBy;
        private Instant submittedAt;
        private String reviewedBy;
        private Instant reviewedAt;
    }
}
```

**Enum files** (each in `com/capillary/intouchapiv3/unified/subscription/enums/`):

```java
// SubscriptionStatus.java
package com.capillary.intouchapiv3.unified.subscription.enums;
public enum SubscriptionStatus {
    DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, ARCHIVED
}

// SubscriptionType.java
package com.capillary.intouchapiv3.unified.subscription.enums;
public enum SubscriptionType {
    TIER_BASED, NON_TIER
}

// CycleType.java
package com.capillary.intouchapiv3.unified.subscription.enums;
public enum CycleType {
    DAYS, MONTHS, YEARS
}

// MigrateOnExpiry.java
package com.capillary.intouchapiv3.unified.subscription.enums;
public enum MigrateOnExpiry {
    NONE, MIGRATE_TO_PROGRAM
}

// ReminderChannel.java
package com.capillary.intouchapiv3.unified.subscription.enums;
public enum ReminderChannel {
    SMS, EMAIL, PUSH
}

// SubscriptionAction.java  (for status-change endpoint)
package com.capillary.intouchapiv3.unified.subscription.enums;
public enum SubscriptionAction {
    SUBMIT_FOR_APPROVAL, PAUSE, RESUME, ARCHIVE, DUPLICATE
}
```

**Key imports for consumers**:
- `org.springframework.data.annotation.Id` (Spring Data Commons — already in pom)
- `org.springframework.data.annotation.Version` (Spring Data Commons — already in pom)
- `org.springframework.data.mongodb.core.mapping.Document` (Spring Data MongoDB — already in pom)
- `java.time.Instant` (JDK 11)
- Lombok: already in pom
- `jakarta.validation.constraints.*`: already in pom (`jakarta.validation:jakarta.validation-api`)

**Maven status**: All dependencies already in pom.xml (Spring Data MongoDB, Lombok, Jakarta Validation). No new dependencies.

---

#### 2. `SubscriptionProgramRepository.java`

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionProgramRepository.java`

```java
package com.capillary.intouchapiv3.unified.subscription;

import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repository for SubscriptionProgram MongoDB documents.
 * Routed to EMF MongoDB via EmfMongoConfig.includeFilters (KD-41).
 */
@Repository
public interface SubscriptionProgramRepository extends MongoRepository<SubscriptionProgram, String> {

    /**
     * GET single subscription by immutable business ID + org (G-07).
     * Used by SubscriptionFacade.getSubscription().
     */
    @Query("{'subscriptionProgramId': ?0, 'orgId': ?1}")
    Optional<SubscriptionProgram> findBySubscriptionProgramIdAndOrgId(
            String subscriptionProgramId, Long orgId);

    /**
     * List subscriptions for an org + optional status filter (paginated).
     * Used by SubscriptionFacade.listSubscriptions().
     */
    @Query("{'orgId': ?0, 'status': ?1}")
    Page<SubscriptionProgram> findByOrgIdAndStatus(
            Long orgId, SubscriptionStatus status, Pageable pageable);

    /**
     * List subscriptions for an org across multiple statuses.
     * Used when status filter is multi-select (AC-03).
     */
    @Query("{'orgId': ?0, 'status': { $in: ?1 }}")
    Page<SubscriptionProgram> findByOrgIdAndStatusIn(
            Long orgId, List<SubscriptionStatus> statuses, Pageable pageable);

    /**
     * List all subscriptions for an org (no status filter).
     */
    @Query("{'orgId': ?0}")
    Page<SubscriptionProgram> findByOrgId(Long orgId, Pageable pageable);

    /**
     * Find the pending DRAFT edit that was forked from a given ACTIVE doc.
     * Used to detect in-flight edits before allowing a second edit.
     * parentId = ACTIVE doc's objectId (_id).
     */
    @Query("{'parentId': ?0, 'orgId': ?1, 'status': 'DRAFT'}")
    Optional<SubscriptionProgram> findDraftByParentIdAndOrgId(String parentId, Long orgId);

    /**
     * Find PENDING_APPROVAL docs for the approval queue (AC-36).
     */
    @Query("{'orgId': ?0, 'programId': ?1, 'status': 'PENDING_APPROVAL'}")
    Page<SubscriptionProgram> findPendingApprovalByOrgIdAndProgramId(
            Long orgId, Integer programId, Pageable pageable);

    /**
     * Find by mysqlPartnerProgramId for SAGA idempotency check (RF-6).
     * If mysqlPartnerProgramId is already set, skip Thrift call on retry.
     */
    @Query("{'mysqlPartnerProgramId': ?0, 'orgId': ?1}")
    Optional<SubscriptionProgram> findByMysqlPartnerProgramIdAndOrgId(
            Integer mysqlPartnerProgramId, Long orgId);

    /**
     * Check name uniqueness within MongoDB scope (partial pre-check before MySQL check).
     * Full uniqueness check requires getAllPartnerPrograms() Thrift call (KD-40).
     */
    @Query("{'orgId': ?0, 'name': ?1, 'status': { $in: ['DRAFT', 'PENDING_APPROVAL', 'ACTIVE', 'PAUSED'] }}")
    Optional<SubscriptionProgram> findActiveByOrgIdAndName(Long orgId, String name);

    /**
     * List subscriptions by orgId + programId + groupTag (grouped view, AC-06).
     */
    @Query("{'orgId': ?0, 'programId': ?1, 'groupTag': ?2}")
    Page<SubscriptionProgram> findByOrgIdAndProgramIdAndGroupTag(
            Long orgId, Integer programId, String groupTag, Pageable pageable);

    /**
     * Fetch all ACTIVE mysqlPartnerProgramIds for an org — used for bulk subscriber-count
     * Thrift call (Architect KD-44, RF-4: eliminate N+1).
     */
    @Query(value = "{'orgId': ?0, 'status': 'ACTIVE', 'mysqlPartnerProgramId': { $ne: null }}", fields = "{'mysqlPartnerProgramId': 1}")
    List<SubscriptionProgram> findActiveMysqlPartnerProgramIdsByOrgId(Long orgId);
}
```

**Maven status**: No new dependencies.

---

#### 3. `ApprovableEntity.java` (marker interface)

**File**: `com/capillary/intouchapiv3/makechecker/ApprovableEntity.java`

```java
package com.capillary.intouchapiv3.makechecker;

/**
 * Marker interface for any entity that participates in maker-checker approval flow.
 * Subscriptions are the first consumer. Tiers and Benefits will implement this in
 * future pipeline runs (ADR-02: clean-room generic maker-checker).
 *
 * Note: setStatus() takes Object to avoid generic method in interface (which would
 * require bounded wildcards throughout). Each impl casts to its own enum type.
 */
public interface ApprovableEntity {

    Object getStatus();

    void setStatus(Object status);

    Long getVersion();

    void setVersion(Long version);

    String getParentId();

    void setParentId(String parentId);

    Long getOrgId();

    String getComments();

    void setComments(String comments);
}
```

---

#### 4. `ApprovableEntityHandler.java` (pluggable hook interface)

**File**: `com/capillary/intouchapiv3/makechecker/ApprovableEntityHandler.java`

```java
package com.capillary.intouchapiv3.makechecker;

/**
 * Entity-specific hook interface for maker-checker operations.
 * Subscriptions implement SubscriptionApprovalHandler.
 * Future entities (Tiers, Benefits) provide their own implementations (ADR-02).
 *
 * @param <T> The ApprovableEntity type this handler manages
 */
public interface ApprovableEntityHandler<T extends ApprovableEntity> {

    /**
     * Entity-specific validation before DRAFT → PENDING_APPROVAL transition.
     * Checks required fields, business rules (e.g., TIER_BASED requires linkedTierId).
     *
     * @throws com.capillary.intouchapiv3.models.exceptions.InvalidInputException if validation fails
     */
    void validateForSubmission(T entity);

    /**
     * Last-minute validation before PENDING_APPROVAL → ACTIVE (called during approve).
     * Re-checks name uniqueness against MySQL via Thrift (KD-40, RF-5).
     * May re-check any condition that could have changed since submission.
     *
     * @throws com.capillary.intouchapiv3.models.exceptions.InvalidInputException if pre-approve fails
     */
    void preApprove(T entity);

    /**
     * Performs the side effect (SAGA Step 1): Thrift/MySQL write.
     * For subscriptions: calls createOrUpdatePartnerProgram via PointsEngineRulesThriftService.
     * Returns the publish result for use in postApprove.
     *
     * @return PublishResult — contains mysqlPartnerProgramId for subscriptions
     * @throws Exception propagated from Thrift on failure — caller handles SAGA compensation
     */
    PublishResult publish(T entity) throws Exception;

    /**
     * Post-publish MongoDB update (SAGA Step 2).
     * For subscriptions: sets status=ACTIVE, stores mysqlPartnerProgramId, updates workflowMetadata.
     */
    void postApprove(T entity, PublishResult publishResult);

    /**
     * Called when publish() throws. Sets status=PUBLISH_FAILED or logs for monitoring.
     * For subscriptions: doc remains PENDING_APPROVAL.
     */
    void onPublishFailure(T entity, Exception e);

    /**
     * Optional: called before rejection to validate that rejection is allowed.
     * Default: no-op. Override if rejection requires guards.
     */
    default void preReject(T entity) {}

    /**
     * Called after rejection. Sets status=DRAFT, stores rejection comment.
     */
    void postReject(T entity, String comment);
}
```

---

#### 5. `PublishResult.java`

**File**: `com/capillary/intouchapiv3/makechecker/PublishResult.java`

```java
package com.capillary.intouchapiv3.makechecker;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Result of an ApprovableEntityHandler.publish() call.
 * Generic enough for any entity. Subscription populates mysqlPartnerProgramId.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PublishResult {
    /** MySQL primary key of the written record (e.g., partner_programs.id) */
    private Integer externalId;
    /** Human-readable source system (e.g., "partner_programs") */
    private String source;
    /** Whether publish was idempotent (retry scenario where MySQL already had the record) */
    private boolean idempotent;
}
```

---

#### 6. `MakerCheckerService.java` (generic state machine)

**File**: `com/capillary/intouchapiv3/makechecker/MakerCheckerService.java`

```java
package com.capillary.intouchapiv3.makechecker;

import com.capillary.intouchapiv3.models.exceptions.InvalidInputException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Generic maker-checker state machine. Holds all generic state transitions.
 * Entity-specific logic is delegated to ApprovableEntityHandler<T>.
 *
 * @param <T> The ApprovableEntity type managed by this service instance
 */
@Service
public class MakerCheckerService<T extends ApprovableEntity> {

    private static final Logger logger = LoggerFactory.getLogger(MakerCheckerService.class);

    /**
     * Transition DRAFT → PENDING_APPROVAL.
     * Validates via handler.validateForSubmission(). Updates status. Saves via save callback.
     *
     * @param entity   Entity in DRAFT status
     * @param handler  Entity-specific hook
     * @param save     Callback to persist the entity (e.g., repository.save())
     * @return Updated entity with status=PENDING_APPROVAL
     * @throws InvalidInputException if handler.validateForSubmission() fails
     */
    public T submitForApproval(T entity, ApprovableEntityHandler<T> handler,
                               EntitySaveCallback<T> save);

    /**
     * Transition PENDING_APPROVAL → ACTIVE (on approval) via SAGA.
     *
     * SAGA Steps:
     * 1. handler.preApprove(entity) — re-validate
     * 2. handler.publish(entity) — Thrift/MySQL write (compensation on failure: handler.onPublishFailure)
     * 3. handler.postApprove(entity, result) — MongoDB update
     * 4. save.apply(entity)
     *
     * @param entity         Entity in PENDING_APPROVAL status
     * @param comment        Approval comment (stored in entity.comments)
     * @param handler        Entity-specific hook
     * @param save           Callback to persist the entity
     * @param reviewedBy     User ID of the approver
     * @return Updated entity with status=ACTIVE
     * @throws InvalidInputException if preApprove fails
     * @throws Exception if publish() throws (SAGA compensation triggered)
     */
    public T approve(T entity, String comment, String reviewedBy,
                     ApprovableEntityHandler<T> handler, EntitySaveCallback<T> save) throws Exception;

    /**
     * Transition PENDING_APPROVAL → DRAFT (on rejection).
     *
     * @param entity    Entity in PENDING_APPROVAL status
     * @param comment   Rejection comment (required, stored in entity.comments)
     * @param reviewedBy User ID of the rejector
     * @param handler   Entity-specific hook
     * @param save      Callback to persist the entity
     * @return Updated entity with status=DRAFT
     */
    public T reject(T entity, String comment, String reviewedBy,
                    ApprovableEntityHandler<T> handler, EntitySaveCallback<T> save);

    // -----------------------------------------------------------------------
    // Functional callback type
    // -----------------------------------------------------------------------

    /**
     * Functional interface for entity persistence callback.
     * Avoids hard coupling MakerCheckerService to a specific repository type.
     */
    @FunctionalInterface
    public interface EntitySaveCallback<T> {
        T save(T entity);
    }
}
```

---

#### 7. `SubscriptionFacade.java`

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionFacade.java`

```java
package com.capillary.intouchapiv3.unified.subscription;

import com.capillary.intouchapiv3.makechecker.MakerCheckerService;
import com.capillary.intouchapiv3.models.exceptions.InvalidInputException;
import com.capillary.intouchapiv3.models.exceptions.NotFoundException;
import com.capillary.intouchapiv3.services.thrift.PointsEngineRulesThriftService;
import com.capillary.intouchapiv3.unified.subscription.dto.*;
import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionAction;
import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Component;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Orchestration facade for subscription program operations.
 * Coordinates: MongoDB read/write, maker-checker state machine, Thrift calls (via PublishService).
 * Pattern: @Component + @Autowired field injection (matches UnifiedPromotionFacade).
 */
@Component
public class SubscriptionFacade {

    private static final Logger logger = LoggerFactory.getLogger(SubscriptionFacade.class);

    @Autowired
    private SubscriptionProgramRepository subscriptionRepository;

    @Autowired
    private MakerCheckerService<SubscriptionProgram> makerCheckerService;

    @Autowired
    private SubscriptionApprovalHandler approvalHandler;

    @Autowired
    private SubscriptionPublishService publishService;

    @Autowired
    private SubscriptionStatusValidator statusValidator;

    @Autowired
    private SubscriptionMapper subscriptionMapper;

    @Autowired
    private PointsEngineRulesThriftService thriftService;

    // -----------------------------------------------------------------------
    // CRUD
    // -----------------------------------------------------------------------

    /**
     * Create a new subscription in DRAFT status (WP-1).
     * Validates name uniqueness via Thrift getAllPartnerPrograms (KD-40, RF-5).
     * Sets subscriptionProgramId=UUID, status=DRAFT, version=1, orgId=caller orgId.
     * No MySQL write. No Thrift write.
     *
     * @return Created SubscriptionResponse (status=DRAFT)
     * @throws InvalidInputException if name conflicts (SUBSCRIPTION_NAME_CONFLICT)
     */
    public SubscriptionResponse createSubscription(Long orgId, Integer programId,
                                                   SubscriptionRequest request,
                                                   String createdBy) throws Exception;

    /**
     * Update a subscription (WP-2).
     * DRAFT/PENDING_APPROVAL: in-place update.
     * ACTIVE: creates new DRAFT doc with parentId=ACTIVE.objectId, version=ACTIVE.version+1.
     *
     * @return Updated or newly-created DRAFT SubscriptionResponse
     * @throws NotFoundException if subscriptionProgramId not found for orgId
     * @throws InvalidInputException if update is attempted on ARCHIVED/PAUSED status
     */
    public SubscriptionResponse updateSubscription(Long orgId, String subscriptionProgramId,
                                                   SubscriptionRequest request,
                                                   String updatedBy) throws Exception;

    /**
     * Get a single subscription (RP-12).
     *
     * @return SubscriptionResponse
     * @throws NotFoundException if not found for (subscriptionProgramId, orgId)
     */
    public SubscriptionResponse getSubscription(Long orgId, String subscriptionProgramId);

    /**
     * List subscriptions with optional filters (RP-11, AC-01, AC-03).
     * Subscriber counts fetched in bulk via Thrift (KD-44) and merged into response.
     *
     * @return Page of SubscriptionListItem
     */
    public Page<SubscriptionListItem> listSubscriptions(Long orgId, Integer programId,
                                                        SubscriptionListRequest request,
                                                        Pageable pageable) throws Exception;

    /**
     * Duplicate a subscription (AC-12, OQ-17 resolved).
     * Produces a new DRAFT immediately. Name set to original + " (Copy)".
     * Fields reset: status=DRAFT, version=1, parentId=null, mysqlPartnerProgramId=null,
     * subscriptionProgramId=new UUID.
     * No maker-checker. No MySQL write. MongoDB-only.
     *
     * @return New DRAFT SubscriptionResponse
     * @throws NotFoundException if source subscription not found
     */
    public SubscriptionResponse duplicateSubscription(Long orgId, String subscriptionProgramId,
                                                      String createdBy) throws Exception;

    // -----------------------------------------------------------------------
    // Lifecycle state transitions (via StatusChangeRequest)
    // -----------------------------------------------------------------------

    /**
     * Change subscription status (WP-3, WP-6, WP-7, WP-8).
     * Delegates to specific handler based on action:
     *   SUBMIT_FOR_APPROVAL → submitForApproval()
     *   PAUSE              → pauseSubscription()
     *   RESUME             → resumeSubscription()
     *   ARCHIVE            → archiveSubscription()
     *
     * @return Updated SubscriptionResponse
     * @throws InvalidInputException if action is not valid for current status
     */
    public SubscriptionResponse changeStatus(Long orgId, String subscriptionProgramId,
                                             StatusChangeRequest request,
                                             String requestedBy) throws Exception;

    /**
     * Submit for approval (DRAFT → PENDING_APPROVAL, WP-3).
     * Delegates to MakerCheckerService.submitForApproval().
     */
    public SubscriptionResponse submitForApproval(Long orgId, String subscriptionProgramId,
                                                  String submittedBy);

    /**
     * Approve or reject a PENDING_APPROVAL subscription (WP-4, WP-5).
     * APPROVE: triggers SAGA via MakerCheckerService.approve().
     * REJECT: transitions to DRAFT via MakerCheckerService.reject().
     *
     * @return Updated SubscriptionResponse
     * @throws NotFoundException if subscription not found in PENDING_APPROVAL status
     * @throws Exception on SAGA Thrift failure (returns 502 to caller)
     */
    public SubscriptionResponse handleApproval(Long orgId, String subscriptionProgramId,
                                               ApprovalRequest request,
                                               String reviewedBy) throws Exception;

    /**
     * Pause (ACTIVE → PAUSED, WP-6).
     * Calls createOrUpdatePartnerProgram with isActive=false (ADR-05, KD-42).
     * On Thrift success: updates MongoDB status=PAUSED.
     * On Thrift failure: remains ACTIVE, propagates exception.
     */
    public SubscriptionResponse pauseSubscription(Long orgId, String subscriptionProgramId,
                                                  String requestedBy) throws Exception;

    /**
     * Resume (PAUSED → ACTIVE, WP-7).
     * Calls createOrUpdatePartnerProgram with isActive=true (ADR-05, KD-42).
     */
    public SubscriptionResponse resumeSubscription(Long orgId, String subscriptionProgramId,
                                                   String requestedBy) throws Exception;

    /**
     * Archive (ACTIVE or PAUSED → ARCHIVED, WP-8).
     * Calls createOrUpdatePartnerProgram with isActive=false.
     * DRAFT archive: MongoDB-only, no Thrift call (mysqlPartnerProgramId is null).
     * Existing enrollments unaffected (KD-30).
     */
    public SubscriptionResponse archiveSubscription(Long orgId, String subscriptionProgramId,
                                                    String requestedBy) throws Exception;

    // -----------------------------------------------------------------------
    // Benefit linkage (WP-9, WP-10, RP-benefit)
    // -----------------------------------------------------------------------

    /**
     * Link a benefit to a subscription (WP-9, AC-21). MongoDB-only (KD-36).
     *
     * @throws NotFoundException if subscription not found
     * @throws InvalidInputException if benefitId already linked or subscription is ARCHIVED
     */
    public SubscriptionResponse linkBenefit(Long orgId, String subscriptionProgramId,
                                            Long benefitId, String updatedBy);

    /**
     * Delink a benefit from a subscription (WP-10, AC-21). MongoDB-only.
     *
     * @throws NotFoundException if subscription or benefitId not found
     */
    public SubscriptionResponse delinkBenefit(Long orgId, String subscriptionProgramId,
                                              Long benefitId, String updatedBy);

    /**
     * Get benefits linked to a subscription (AC-07).
     */
    public List<SubscriptionProgram.BenefitRef> getBenefits(Long orgId,
                                                             String subscriptionProgramId);

    // -----------------------------------------------------------------------
    // Listing header stats (AC-02)
    // -----------------------------------------------------------------------

    /**
     * Aggregate subscription counts by status + total subscriber count.
     * MongoDB aggregate for status counts + bulk Thrift call for subscriber counts (KD-44).
     * Subscriber counts cached with Caffeine 60s TTL (Architect Section 5.6.5).
     */
    public SubscriptionListResponse.HeaderStats getHeaderStats(Long orgId, Integer programId) throws Exception;
}
```

**Note on `List<...>` return type**: The full import is `java.util.List`.

---

#### 8. `SubscriptionPublishService.java` (SAGA publish)

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionPublishService.java`

```java
package com.capillary.intouchapiv3.unified.subscription;

import com.capillary.intouchapiv3.makechecker.PublishResult;
import com.capillary.intouchapiv3.services.thrift.PointsEngineRulesThriftService;
import com.capillary.shopbook.pointsengine.endpoint.api.external.PartnerProgramInfo;
import com.capillary.shopbook.pointsengine.endpoint.api.external.PartnerProgramMembershipCycle;
import com.capillary.shopbook.pointsengine.endpoint.api.external.PartnerProgramType;
import com.capillary.shopbook.pointsengine.endpoint.api.external.PartnerProgramCycleType;
import com.capillary.intouchapiv3.unified.subscription.enums.CycleType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * SAGA Step 1: Publish subscription to MySQL via Thrift.
 * Called by SubscriptionApprovalHandler.publish() and by SubscriptionFacade for
 * PAUSE/RESUME/ARCHIVE lifecycle operations.
 *
 * Key invariants:
 * - YEARS cycleType → converts to MONTHS × 12 before Thrift call (ADR-07, KD-38)
 * - programToPartnerProgramPointsRatio defaults to 1.0 (OQ-18 resolved)
 * - isSyncWithLoyaltyTierOnDowngrade defaults to false for NON_TIER (OQ-19 resolved)
 * - partner_program_identifier is generated by EMFUtils inside emf-parent (KD-43)
 * - Reminders NOT written via Thrift (KD-39, ADR-06)
 * - UNIQUE(org_id, name) pre-validated before Thrift call (KD-40, RF-5)
 */
@Service
public class SubscriptionPublishService {

    private static final Logger logger = LoggerFactory.getLogger(SubscriptionPublishService.class);

    private static final double DEFAULT_POINTS_RATIO    = 1.0;
    private static final int    MONTHS_PER_YEAR         = 12;
    private static final int    MAX_RETRY_MONGODB       = 3;

    @Autowired
    private PointsEngineRulesThriftService thriftService;

    /**
     * Publish subscription config to MySQL via Thrift.
     * SAGA Step 1 — called during APPROVE flow.
     *
     * Idempotency (RF-6): if subscription.mysqlPartnerProgramId is already set
     * (partial retry scenario), skips Thrift call and returns existing id directly.
     *
     * @param subscription  The PENDING_APPROVAL SubscriptionProgram document
     * @param orgId         Multi-tenancy key
     * @param lastModifiedBy userId (for Thrift audit logging)
     * @return PublishResult containing mysqlPartnerProgramId
     * @throws Exception propagated from Thrift — caller (MakerCheckerService) handles SAGA compensation
     */
    public PublishResult publishToMySQL(SubscriptionProgram subscription, Long orgId,
                                        int lastModifiedBy) throws Exception;

    /**
     * Publish isActive=false/true for PAUSE/ARCHIVE/RESUME.
     * Builds full PartnerProgramInfo from existing subscription + overrides isActive field 15.
     * Reuses createOrUpdatePartnerProgram (ADR-05, KD-42).
     *
     * @param subscription   The current SubscriptionProgram document (must have mysqlPartnerProgramId)
     * @param orgId          Multi-tenancy key
     * @param isActive       false for PAUSE/ARCHIVE, true for RESUME
     * @param lastModifiedBy userId
     * @throws IllegalStateException if mysqlPartnerProgramId is null (program was never published)
     * @throws Exception propagated from Thrift
     */
    public void publishIsActive(SubscriptionProgram subscription, Long orgId,
                                boolean isActive, int lastModifiedBy) throws Exception;

    /**
     * Build the PartnerProgramInfo Thrift struct from a MongoDB SubscriptionProgram document.
     * Applies YEARS → MONTHS×12 conversion (ADR-07).
     * Sets default programToPartnerProgramPointsRatio = 1.0 (OQ-18).
     * Sets isSyncWithLoyaltyTierOnDowngrade from tierConfig (OQ-19).
     *
     * Package-private for testability.
     *
     * @param subscription  MongoDB doc to transform
     * @param orgId         Org for audit
     * @return Thrift struct ready for createOrUpdatePartnerProgram
     */
    PartnerProgramInfo buildPartnerProgramInfo(SubscriptionProgram subscription, Long orgId);

    /**
     * Convert CycleType.YEARS → Thrift MONTHS with value×12.
     * CycleType.DAYS and CycleType.MONTHS pass through unchanged.
     * Package-private for unit testing.
     */
    PartnerProgramMembershipCycle convertCycle(CycleType cycleType, Integer cycleValue);
}
```

---

#### 9. `SubscriptionApprovalHandler.java` (entity hook — implements ApprovableEntityHandler)

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionApprovalHandler.java`

```java
package com.capillary.intouchapiv3.unified.subscription;

import com.capillary.intouchapiv3.makechecker.ApprovableEntityHandler;
import com.capillary.intouchapiv3.makechecker.PublishResult;
import com.capillary.intouchapiv3.models.exceptions.InvalidInputException;
import com.capillary.intouchapiv3.services.thrift.PointsEngineRulesThriftService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Subscription-specific hook for MakerCheckerService.
 * Plugged in as the ApprovableEntityHandler<SubscriptionProgram>.
 */
@Component
public class SubscriptionApprovalHandler implements ApprovableEntityHandler<SubscriptionProgram> {

    private static final Logger logger = LoggerFactory.getLogger(SubscriptionApprovalHandler.class);

    @Autowired
    private SubscriptionPublishService publishService;

    @Autowired
    private PointsEngineRulesThriftService thriftService;

    @Autowired
    private SubscriptionStatusValidator statusValidator;

    /**
     * Pre-submission checks (DRAFT → PENDING_APPROVAL).
     * Validates: name required, duration required, TIER_BASED requires linkedTierId,
     * tierDowngradeOnExit=true requires downgradeTargetTierId.
     *
     * @throws InvalidInputException on validation failure
     */
    @Override
    public void validateForSubmission(SubscriptionProgram entity);

    /**
     * Pre-approval check: re-validates name uniqueness against MySQL via Thrift
     * getAllPartnerPrograms(). Throws if conflict found (KD-40, RF-5).
     *
     * @throws InvalidInputException if name conflicts with existing MySQL partner program
     */
    @Override
    public void preApprove(SubscriptionProgram entity);

    /**
     * SAGA Step 1: Thrift/MySQL write via SubscriptionPublishService.publishToMySQL().
     *
     * @return PublishResult with mysqlPartnerProgramId
     * @throws Exception on Thrift failure — caller triggers onPublishFailure()
     */
    @Override
    public PublishResult publish(SubscriptionProgram entity) throws Exception;

    /**
     * SAGA Step 2: Update MongoDB doc post-publish.
     * Sets: status=ACTIVE, mysqlPartnerProgramId=result.externalId,
     * workflowMetadata.reviewedAt=Instant.now(), workflowMetadata.reviewedBy.
     *
     * Note: If this is an edit-of-ACTIVE (parentId != null):
     *   1. Load old ACTIVE doc by parentId (objectId)
     *   2. Set old ACTIVE doc status=ARCHIVED
     *   3. Copy mysqlPartnerProgramId from old ACTIVE to new entity (if result.idempotent)
     *   4. Update new entity: status=ACTIVE
     * Both docs saved by MakerCheckerService via save callback.
     */
    @Override
    public void postApprove(SubscriptionProgram entity, PublishResult publishResult);

    /**
     * Called on Thrift failure. Logs critical error with orgId+subscriptionProgramId (G-08).
     * Entity remains PENDING_APPROVAL — NO status update.
     */
    @Override
    public void onPublishFailure(SubscriptionProgram entity, Exception e);

    /**
     * Set status=DRAFT, store comment in entity.comments.
     */
    @Override
    public void postReject(SubscriptionProgram entity, String comment);
}
```

---

#### 10. `SubscriptionController.java` (CRUD + lifecycle)

**File**: `com/capillary/intouchapiv3/resources/SubscriptionController.java`

```java
package com.capillary.intouchapiv3.resources;

import com.capillary.intouchapiv3.auth.AbstractBaseAuthenticationToken;
import com.capillary.intouchapiv3.auth.IntouchUser;
import com.capillary.intouchapiv3.models.ResponseWrapper;
import com.capillary.intouchapiv3.unified.subscription.SubscriptionFacade;
import com.capillary.intouchapiv3.unified.subscription.dto.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.List;

/**
 * REST controller for subscription program CRUD and lifecycle management.
 * Base path: /v3/subscriptions (G-06.5: versioned from day one).
 * Auth extraction: AbstractBaseAuthenticationToken token → token.getIntouchUser().getOrgId()
 * Response wrapping: ResponseEntity<ResponseWrapper<T>> (matches UnifiedPromotionController pattern).
 * Error handling: global TargetGroupErrorAdvice handles all RuntimeExceptions.
 */
@RestController
@RequestMapping("/v3/subscriptions")
public class SubscriptionController {

    private static final Logger logger = LoggerFactory.getLogger(SubscriptionController.class);

    private final SubscriptionFacade subscriptionFacade;

    @Autowired
    public SubscriptionController(SubscriptionFacade subscriptionFacade) {
        this.subscriptionFacade = subscriptionFacade;
    }

    // -----------------------------------------------------------------------
    // POST /v3/subscriptions — Create (WP-1)
    // -----------------------------------------------------------------------
    @PostMapping(produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> createSubscription(
            @Valid @RequestBody SubscriptionRequest request,
            AbstractBaseAuthenticationToken token,
            HttpServletRequest httpRequest) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Creating subscription for org: {}, program: {}", user.getOrgId(), request.getProgramId());
        SubscriptionResponse response = subscriptionFacade.createSubscription(
                user.getOrgId(), request.getProgramId(), request, user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.CREATED);
    }

    // -----------------------------------------------------------------------
    // GET /v3/subscriptions/{subscriptionProgramId} — Get single (RP-12)
    // -----------------------------------------------------------------------
    @GetMapping(value = "/{subscriptionProgramId}", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> getSubscription(
            @PathVariable String subscriptionProgramId,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        logger.info("Fetching subscription: {} for org: {}", subscriptionProgramId, user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.getSubscription(
                user.getOrgId(), subscriptionProgramId);
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }

    // -----------------------------------------------------------------------
    // PUT /v3/subscriptions/{subscriptionProgramId} — Update (WP-2)
    // -----------------------------------------------------------------------
    @PutMapping(value = "/{subscriptionProgramId}", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> updateSubscription(
            @PathVariable String subscriptionProgramId,
            @Valid @RequestBody SubscriptionRequest request,
            AbstractBaseAuthenticationToken token,
            HttpServletRequest httpRequest) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Updating subscription: {} for org: {}", subscriptionProgramId, user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.updateSubscription(
                user.getOrgId(), subscriptionProgramId, request, user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }

    // -----------------------------------------------------------------------
    // GET /v3/subscriptions — List (RP-11)
    // -----------------------------------------------------------------------
    @GetMapping(produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionListResponse>> listSubscriptions(
            @RequestParam Integer programId,
            @RequestParam(required = false) List<String> status,
            @RequestParam(required = false) String groupTag,
            @RequestParam(required = false) String search,
            @RequestParam(defaultValue = "subscribers") String sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            AbstractBaseAuthenticationToken token) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Listing subscriptions for org: {}, program: {}", user.getOrgId(), programId);
        SubscriptionListRequest listRequest = SubscriptionListRequest.builder()
                .statuses(status).groupTag(groupTag).search(search).sort(sort).build();
        Page<SubscriptionListItem> items = subscriptionFacade.listSubscriptions(
                user.getOrgId(), programId, listRequest,
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, sort)));
        SubscriptionListResponse.HeaderStats stats = subscriptionFacade.getHeaderStats(
                user.getOrgId(), programId);
        SubscriptionListResponse response = SubscriptionListResponse.builder()
                .items(items).headerStats(stats).build();
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }

    // -----------------------------------------------------------------------
    // PUT /v3/subscriptions/{subscriptionProgramId}/status — Lifecycle (WP-3,6,7,8)
    // -----------------------------------------------------------------------
    @PutMapping(value = "/{subscriptionProgramId}/status", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> changeStatus(
            @PathVariable String subscriptionProgramId,
            @Valid @RequestBody StatusChangeRequest request,
            AbstractBaseAuthenticationToken token) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Changing status of subscription: {} action: {} org: {}",
                subscriptionProgramId, request.getAction(), user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.changeStatus(
                user.getOrgId(), subscriptionProgramId, request, user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }

    // -----------------------------------------------------------------------
    // POST /v3/subscriptions/{subscriptionProgramId}/duplicate — Duplicate (AC-12)
    // -----------------------------------------------------------------------
    @PostMapping(value = "/{subscriptionProgramId}/duplicate", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> duplicateSubscription(
            @PathVariable String subscriptionProgramId,
            AbstractBaseAuthenticationToken token) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Duplicating subscription: {} org: {}", subscriptionProgramId, user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.duplicateSubscription(
                user.getOrgId(), subscriptionProgramId, user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.CREATED);
    }

    // -----------------------------------------------------------------------
    // GET /v3/subscriptions/{subscriptionProgramId}/benefits — List benefits (AC-07)
    // -----------------------------------------------------------------------
    @GetMapping(value = "/{subscriptionProgramId}/benefits", produces = "application/json")
    public ResponseEntity<ResponseWrapper<List<SubscriptionProgram.BenefitRef>>> getBenefits(
            @PathVariable String subscriptionProgramId,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        List<SubscriptionProgram.BenefitRef> benefits = subscriptionFacade.getBenefits(
                user.getOrgId(), subscriptionProgramId);
        return new ResponseEntity<>(new ResponseWrapper<>(benefits, null, null), HttpStatus.OK);
    }

    // -----------------------------------------------------------------------
    // POST /v3/subscriptions/{subscriptionProgramId}/benefits — Link benefit (WP-9)
    // -----------------------------------------------------------------------
    @PostMapping(value = "/{subscriptionProgramId}/benefits", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> linkBenefit(
            @PathVariable String subscriptionProgramId,
            @Valid @RequestBody BenefitLinkRequest request,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        logger.info("Linking benefit: {} to subscription: {} org: {}",
                request.getBenefitId(), subscriptionProgramId, user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.linkBenefit(
                user.getOrgId(), subscriptionProgramId, request.getBenefitId(), user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }

    // -----------------------------------------------------------------------
    // DELETE /v3/subscriptions/{subscriptionProgramId}/benefits/{benefitId} — Delink (WP-10)
    // -----------------------------------------------------------------------
    @DeleteMapping(value = "/{subscriptionProgramId}/benefits/{benefitId}", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> delinkBenefit(
            @PathVariable String subscriptionProgramId,
            @PathVariable Long benefitId,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        logger.info("Delinking benefit: {} from subscription: {} org: {}",
                benefitId, subscriptionProgramId, user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.delinkBenefit(
                user.getOrgId(), subscriptionProgramId, benefitId, user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }
}
```

---

#### 11. `SubscriptionReviewController.java` (approval)

**File**: `com/capillary/intouchapiv3/resources/SubscriptionReviewController.java`

```java
package com.capillary.intouchapiv3.resources;

import com.capillary.intouchapiv3.auth.AbstractBaseAuthenticationToken;
import com.capillary.intouchapiv3.auth.IntouchUser;
import com.capillary.intouchapiv3.models.ResponseWrapper;
import com.capillary.intouchapiv3.unified.subscription.SubscriptionFacade;
import com.capillary.intouchapiv3.unified.subscription.dto.ApprovalRequest;
import com.capillary.intouchapiv3.unified.subscription.dto.SubscriptionListResponse;
import com.capillary.intouchapiv3.unified.subscription.dto.SubscriptionResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;

/**
 * REST controller for subscription approval workflow.
 * Approval endpoints are separate from CRUD to match the AC-35/AC-36 spec
 * and provide a clean authorization boundary (approver role vs creator role).
 */
@RestController
@RequestMapping("/v3/subscriptions")
public class SubscriptionReviewController {

    private static final Logger logger = LoggerFactory.getLogger(SubscriptionReviewController.class);

    private final SubscriptionFacade subscriptionFacade;

    @Autowired
    public SubscriptionReviewController(SubscriptionFacade subscriptionFacade) {
        this.subscriptionFacade = subscriptionFacade;
    }

    /**
     * GET /v3/subscriptions/approvals — List PENDING_APPROVAL subscriptions (AC-36).
     */
    @GetMapping(value = "/approvals", produces = "application/json")
    public ResponseEntity<ResponseWrapper<Page<SubscriptionListItem>>> listPendingApprovals(
            @RequestParam Integer programId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            AbstractBaseAuthenticationToken token) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Listing pending approvals for org: {}, program: {}", user.getOrgId(), programId);
        Page<SubscriptionListItem> items = subscriptionFacade.listSubscriptions(
                user.getOrgId(), programId,
                SubscriptionListRequest.builder()
                        .statuses(List.of("PENDING_APPROVAL")).build(),
                PageRequest.of(page, size));
        return new ResponseEntity<>(new ResponseWrapper<>(items, null, null), HttpStatus.OK);
    }

    /**
     * POST /v3/subscriptions/{subscriptionProgramId}/approve — Approve or reject (AC-35, WP-4, WP-5).
     *
     * Request body: ApprovalRequest { approvalStatus: "APPROVE"|"REJECT", comment: "..." }
     * Response: Updated SubscriptionResponse
     */
    @PostMapping(value = "/{subscriptionProgramId}/approve", produces = "application/json")
    public ResponseEntity<ResponseWrapper<SubscriptionResponse>> reviewSubscription(
            @PathVariable String subscriptionProgramId,
            @Valid @RequestBody ApprovalRequest request,
            AbstractBaseAuthenticationToken token) throws Exception {
        IntouchUser user = token.getIntouchUser();
        logger.info("Reviewing subscription: {} action: {} org: {}",
                subscriptionProgramId, request.getApprovalStatus(), user.getOrgId());
        SubscriptionResponse response = subscriptionFacade.handleApproval(
                user.getOrgId(), subscriptionProgramId, request, user.getEntityId());
        return new ResponseEntity<>(new ResponseWrapper<>(response, null, null), HttpStatus.OK);
    }
}
```

---

#### 12. DTOs

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/SubscriptionRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import com.capillary.intouchapiv3.unified.subscription.SubscriptionProgram;
import com.capillary.intouchapiv3.unified.subscription.enums.*;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.List;

/**
 * Request DTO for create and update subscription operations.
 * Validation annotations enforced by @Valid in controller.
 * Global error handling: TargetGroupErrorAdvice.handleMethodArgumentNotValidException()
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class SubscriptionRequest {

    /** Required for create. Ignored on update (path param is authoritative). */
    private Integer programId;

    @NotBlank(message = "SUBSCRIPTION.NAME_REQUIRED")
    @Size(max = 255, message = "SUBSCRIPTION.NAME_TOO_LONG")
    private String name;

    @Size(max = 1000, message = "SUBSCRIPTION.DESCRIPTION_TOO_LONG")
    private String description;

    @NotNull(message = "SUBSCRIPTION.SUBSCRIPTION_TYPE_REQUIRED")
    private SubscriptionType subscriptionType;

    @NotNull(message = "SUBSCRIPTION.DURATION_REQUIRED")
    @Valid
    private DurationDto duration;

    @Valid
    private ExpiryDto expiry;

    @Valid
    private SettingsDto settings;

    /** Required when subscriptionType=TIER_BASED */
    @Valid
    private TierConfigDto tierConfig;

    @Size(max = 5, message = "SUBSCRIPTION.TOO_MANY_REMINDERS")
    @Valid
    private List<ReminderDto> reminders;

    @Valid
    private CustomFieldsDto customFields;

    private String groupTag;

    // -----------------------------------------------------------------------
    // Nested DTOs (avoid coupling request to domain inner classes)
    // -----------------------------------------------------------------------

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class DurationDto {
        @NotNull(message = "SUBSCRIPTION.CYCLE_TYPE_REQUIRED")
        private CycleType cycleType;
        @NotNull @Positive(message = "SUBSCRIPTION.CYCLE_VALUE_POSITIVE")
        private Integer cycleValue;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ExpiryDto {
        private Instant programExpiryDate;
        private MigrateOnExpiry migrateOnExpiry;
        private Integer migrationTargetProgramId;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class SettingsDto {
        private Boolean restrictToOneActivePerMember;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TierConfigDto {
        private Integer linkedTierId;
        private Boolean tierDowngradeOnExit;
        private Integer downgradeTargetTierId;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ReminderDto {
        @NotNull @Positive
        private Integer daysBeforeExpiry;
        @NotNull
        private ReminderChannel channel;
        private java.util.Map<String, String> communicationProperties;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class CustomFieldsDto {
        private List<CustomFieldRefDto> meta;
        private List<CustomFieldRefDto> link;
        private List<CustomFieldRefDto> delink;
    }

    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class CustomFieldRefDto {
        private Long extendedFieldId;
        private String name;
    }
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/SubscriptionResponse.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import com.capillary.intouchapiv3.unified.subscription.SubscriptionProgram;
import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionStatus;
import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionType;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.*;
import java.time.Instant;

/**
 * Response DTO for single subscription GET, POST, PUT.
 * @JsonInclude(NON_NULL) suppresses null fields for cleaner API output.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SubscriptionResponse {
    private String objectId;
    private String subscriptionProgramId;
    private Long orgId;
    private Integer programId;
    private SubscriptionStatus status;
    private Long version;
    private String parentId;
    private Integer mysqlPartnerProgramId;
    private String name;
    private String description;
    private SubscriptionType subscriptionType;
    private SubscriptionProgram.Duration duration;
    private SubscriptionProgram.Expiry expiry;
    private SubscriptionProgram.Settings settings;
    private SubscriptionProgram.TierConfig tierConfig;
    private java.util.List<SubscriptionProgram.BenefitRef> benefits;
    private java.util.List<SubscriptionProgram.Reminder> reminders;
    private SubscriptionProgram.CustomFields customFields;
    private String groupTag;
    private SubscriptionProgram.WorkflowMetadata workflowMetadata;
    private String comments;
    private String createdBy;
    private Instant createdAt;
    private String updatedBy;
    private Instant updatedAt;
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/SubscriptionListItem.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionStatus;
import lombok.*;
import java.time.Instant;

/** Lightweight item for listing endpoint (AC-01). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubscriptionListItem {
    private String subscriptionProgramId;
    private String name;
    private String description;
    private SubscriptionStatus status;
    private Integer benefitsCount;
    private Long subscriberCount;  // from MySQL via bulk Thrift (KD-44)
    private String groupTag;
    private Instant updatedAt;
    private String updatedBy;
    private Integer mysqlPartnerProgramId;
    private Long version;
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/SubscriptionListResponse.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import lombok.*;
import org.springframework.data.domain.Page;
import java.util.Map;

/** Wraps listing page + header stats (AC-02). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubscriptionListResponse {
    private Page<SubscriptionListItem> items;
    private HeaderStats headerStats;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HeaderStats {
        private Long totalSubscriptions;
        private Long activeCount;
        private Long pendingApprovalCount;
        private Long draftCount;
        private Long pausedCount;
        private Long archivedCount;
        private Long totalSubscribers;
    }
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/SubscriptionListRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import lombok.*;
import java.util.List;

/** Query parameters for list endpoint. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SubscriptionListRequest {
    private List<String> statuses;
    private String groupTag;
    private String search;
    private String sort;
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/ApprovalRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Request body for POST /subscriptions/{id}/approve (AC-35). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApprovalRequest {

    @NotBlank(message = "SUBSCRIPTION.APPROVAL_STATUS_REQUIRED")
    private String approvalStatus; // "APPROVE" or "REJECT"

    @Size(max = 150, message = "SUBSCRIPTION.COMMENT_TOO_LONG")
    private String comment;
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/StatusChangeRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import com.capillary.intouchapiv3.unified.subscription.enums.SubscriptionAction;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** Request body for PUT /subscriptions/{id}/status (lifecycle transitions). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class StatusChangeRequest {

    @NotNull(message = "SUBSCRIPTION.ACTION_REQUIRED")
    private SubscriptionAction action;

    @Size(max = 150, message = "SUBSCRIPTION.COMMENT_TOO_LONG")
    private String comment;
}
```

**File**: `com/capillary/intouchapiv3/unified/subscription/dto/BenefitLinkRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;

import jakarta.validation.constraints.NotNull;

/** Request body for POST /subscriptions/{id}/benefits. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class BenefitLinkRequest {

    @NotNull(message = "SUBSCRIPTION.BENEFIT_ID_REQUIRED")
    private Long benefitId;
}
```

---

#### 13. Exception Classes

All extend `RuntimeException` so `TargetGroupErrorAdvice` catches them via its generic handler. Add specific `@ExceptionHandler` entries to `TargetGroupErrorAdvice` for 409 (conflict) and 422 (unprocessable).

**Files** in `com/capillary/intouchapiv3/unified/subscription/exception/`:

```java
// SubscriptionNotFoundException.java
public class SubscriptionNotFoundException extends RuntimeException {
    public SubscriptionNotFoundException(String message) { super(message); }
}

// InvalidSubscriptionStateException.java
public class InvalidSubscriptionStateException extends RuntimeException {
    public InvalidSubscriptionStateException(String message) { super(message); }
}

// SubscriptionNameConflictException.java  — maps to 409
public class SubscriptionNameConflictException extends RuntimeException {
    public SubscriptionNameConflictException(String message) { super(message); }
}
```

**Required addition to `TargetGroupErrorAdvice.java`** (3 new `@ExceptionHandler` methods):

```java
@ResponseBody
@ExceptionHandler({SubscriptionNotFoundException.class})
public ResponseEntity<ResponseWrapper<String>> handleSubscriptionNotFoundException(
        SubscriptionNotFoundException e) {
    return error(HttpStatus.NOT_FOUND, e);
}

@ResponseBody
@ExceptionHandler({InvalidSubscriptionStateException.class})
public ResponseEntity<ResponseWrapper<String>> handleInvalidSubscriptionStateException(
        InvalidSubscriptionStateException e) {
    return error(HttpStatus.UNPROCESSABLE_ENTITY, e);
}

@ResponseBody
@ExceptionHandler({SubscriptionNameConflictException.class})
public ResponseEntity<ResponseWrapper<String>> handleSubscriptionNameConflictException(
        SubscriptionNameConflictException e) {
    return error(HttpStatus.CONFLICT, e);
}
```

---

### intouch-api-v3 — Modified Files

---

#### 14. `EmfMongoConfig.java` — Exact 1-line diff

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/config/EmfMongoConfig.java`

**Before** (line 32):
```java
        classes = {UnifiedPromotionRepository.class}  // Route to EMF MongoDB
```

**After**:
```java
        classes = {UnifiedPromotionRepository.class, SubscriptionProgramRepository.class}  // Route to EMF MongoDB
```

**Additional import to add** at line 9 (after the `UnifiedPromotionRepository` import):
```java
import com.capillary.intouchapiv3.unified.subscription.SubscriptionProgramRepository;
```

---

#### 15. `PointsEngineRulesThriftService.java` — 2 new methods

**File**: `/Users/baljeetsingh/IdeaProjects/intouch-api-v3/src/main/java/com/capillary/intouchapiv3/services/thrift/PointsEngineRulesThriftService.java`

Add these two methods at the end of the class (before closing brace). The import `com.capillary.shopbook.pointsengine.endpoint.api.external.PartnerProgramInfo` is already available via the wildcard `import com.capillary.shopbook.pointsengine.endpoint.api.external.*;`.

```java
/**
 * Create or update a supplementary partner program (subscription) in MySQL via Thrift.
 * Called by SubscriptionPublishService.publishToMySQL() during the APPROVE SAGA (WP-4).
 * Also called for PAUSE/RESUME/ARCHIVE with isActive field set (ADR-05, KD-42).
 *
 * Idempotency: createOrUpdatePartnerProgram uses UPDATE semantics when
 * partnerProgramInfo.partnerProgramId > 0 (emf-parent line 1857).
 *
 * @param partnerProgramInfo  Fully populated Thrift struct (incl. optional isActive for lifecycle ops)
 * @param programId           loyalty_program_id
 * @param orgId               Tenant identifier
 * @param lastModifiedBy      User ID for audit trail
 * @return PartnerProgramInfo with partnerProgramId populated (MySQL partner_programs.id)
 * @throws EMFThriftException wrapping any Thrift or communication error
 */
public PartnerProgramInfo createOrUpdatePartnerProgram(
        PartnerProgramInfo partnerProgramInfo,
        int programId,
        int orgId,
        int lastModifiedBy) throws Exception {

    String serverReqId = CapRequestIdUtil.getRequestId();
    try {
        logger.info("createOrUpdatePartnerProgram: orgId={}, programId={}, partnerProgramId={}, serverReqId={}",
                orgId, programId, partnerProgramInfo.getPartnerProgramId(), serverReqId);

        PartnerProgramInfo response = getClient().createOrUpdatePartnerProgram(
                partnerProgramInfo,
                programId,
                orgId,
                lastModifiedBy,
                System.currentTimeMillis(),
                serverReqId);

        logger.info("createOrUpdatePartnerProgram success: returned partnerProgramId={}",
                response.getPartnerProgramId());
        return response;

    } catch (Exception e) {
        logger.error("Error in createOrUpdatePartnerProgram. orgId={}, programId={}, serverReqId={}",
                orgId, programId, serverReqId, e);
        throw new EMFThriftException("Error in createOrUpdatePartnerProgram: " + e);
    }
}

/**
 * Fetch all partner programs for an org+program for name uniqueness pre-validation (KD-40, RF-5).
 * Called by SubscriptionApprovalHandler.preApprove() and SubscriptionFacade.createSubscription()
 * before CREATE to check UNIQUE(org_id, name) constraint across ALL partner program types.
 *
 * @param programId  loyalty_program_id
 * @param orgId      Tenant identifier
 * @return List of PartnerProgramInfo for the org
 * @throws EMFThriftException wrapping any Thrift or communication error
 */
public List<PartnerProgramInfo> getAllPartnerPrograms(int programId, int orgId) throws Exception {
    String serverReqId = CapRequestIdUtil.getRequestId();
    try {
        logger.info("getAllPartnerPrograms: orgId={}, programId={}, serverReqId={}", orgId, programId, serverReqId);
        List<PartnerProgramInfo> programs = getClient().getAllPartnerPrograms(programId, orgId, serverReqId);
        logger.info("getAllPartnerPrograms: returned {} programs for org={}", programs.size(), orgId);
        return programs;
    } catch (Exception e) {
        logger.error("Error in getAllPartnerPrograms. orgId={}, programId={}, serverReqId={}",
                orgId, programId, serverReqId, e);
        throw new EMFThriftException("Error in getAllPartnerPrograms: " + e);
    }
}
```

**Note**: `List` import is already present (`java.util.List`). `PartnerProgramInfo` is already imported via the wildcard. `CapRequestIdUtil`, `EMFThriftException`, `logger` are already in scope.

---

### thrift-ifaces-pointsengine-rules — Modified File

---

#### 16. `pointsengine_rules.thrift` — Exact IDL diff

**File**: `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift`

**Before** (lines 402–417):
```thrift
struct PartnerProgramInfo{
        1: required i32 partnerProgramId;
        2: required string partnerProgramName;
        3: required string description;
        4: required bool isTierBased;
        5: optional list<PartnerProgramTier> partnerProgramTiers;
        6: required double programToPartnerProgramPointsRatio;
	7: optional string partnerProgramUniqueIdentifier;
	8: required PartnerProgramType partnerProgramType;
	9: optional PartnerProgramMembershipCycle partnerProgramMembershipCycle;
        10: required bool isSyncWithLoyaltyTierOnDowngrade;
        11: optional map <string, string> loyaltySyncTiers;
	12: optional bool updatedViaNewUI;
	13: optional i64 expiryDate;
	14: optional i32 backupProgramId;
}
```

**After** (add field 15):
```thrift
struct PartnerProgramInfo{
        1: required i32 partnerProgramId;
        2: required string partnerProgramName;
        3: required string description;
        4: required bool isTierBased;
        5: optional list<PartnerProgramTier> partnerProgramTiers;
        6: required double programToPartnerProgramPointsRatio;
	7: optional string partnerProgramUniqueIdentifier;
	8: required PartnerProgramType partnerProgramType;
	9: optional PartnerProgramMembershipCycle partnerProgramMembershipCycle;
        10: required bool isSyncWithLoyaltyTierOnDowngrade;
        11: optional map <string, string> loyaltySyncTiers;
	12: optional bool updatedViaNewUI;
	13: optional i64 expiryDate;
	14: optional i32 backupProgramId;
        15: optional bool isActive;  // KD-42: explicit isActive override for PAUSE/RESUME/ARCHIVE operations. When set: overrides existing is_active in saveSupplementaryPartnerProgramEntity. Field 15 confirmed available (OQ-21, C7).
}
```

**Backward compatibility**: `optional` field with no default. Existing callers that do not set field 15 are unaffected — Thrift-generated `isSetIsActive()` returns false, so emf-parent's conditional (`if (partnerProgramThrift.isSetIsActive())`) skips the override.

**Regeneration required**: Run Thrift compiler to regenerate Java stubs. The generated class `PartnerProgramInfo.java` will gain `isActive`, `setIsActive(boolean)`, `isSetIsActive()`, `isIsActive()` methods automatically.

---

### emf-parent — Modified Files

---

#### 17. `PointsEngineRuleService.java` — Exact change in `saveSupplementaryPartnerProgramEntity`

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/PointsEngineRuleService.java`

**Context** (lines 1855–1868 — confirmed from codebase read):
```java
if (oldPartnerProgram != null) {
    newPartnerProgram.setPk(new PartnerProgram.PartnerProgramPK(oldPartnerProgram.getId(), orgId));
    newPartnerProgram.setPartnerProgramIdentifier(oldPartnerProgram.getPartnerProgramIdentifier());
    newPartnerProgram.setActive(oldPartnerProgram.isActive());  // line 1858
    newPartnerProgram.setCreatedOn(oldPartnerProgram.getCreatedOn());
} else {
```

**After** (insert after line 1858):
```java
if (oldPartnerProgram != null) {
    newPartnerProgram.setPk(new PartnerProgram.PartnerProgramPK(oldPartnerProgram.getId(), orgId));
    newPartnerProgram.setPartnerProgramIdentifier(oldPartnerProgram.getPartnerProgramIdentifier());
    newPartnerProgram.setActive(oldPartnerProgram.isActive());  // line 1858 — default: preserve existing
    // KD-42: If isActive is explicitly set in the incoming Thrift struct, use that value
    // (PAUSE sets isActive=false, RESUME sets isActive=true, ARCHIVE sets isActive=false)
    if (partnerProgramThrift.isSetIsActive()) {
        newPartnerProgram.setActive(partnerProgramThrift.isIsActive());
    }
    newPartnerProgram.setCreatedOn(oldPartnerProgram.getCreatedOn());
} else {
```

**Method signature** (unchanged): `private PartnerProgram saveSupplementaryPartnerProgramEntity(int orgId, PartnerProgram partnerProgram, PartnerProgram oldPartnerProgram)`

**Parameter `partnerProgramThrift`**: This method receives the entity, not the Thrift struct directly. The Thrift struct is converted to entity in `getSupplementaryPartnerProgramEntity()` before this method is called. Therefore, the `isActive` field from Thrift must be passed through the entity conversion layer.

**Correction to HLD**: The `saveSupplementaryPartnerProgramEntity` receives a `PartnerProgram` entity (not `PartnerProgramInfo` Thrift struct). The isActive conditional must be applied in `getSupplementaryPartnerProgramEntity()` or in `createOrUpdatePartnerProgram()` in `PointsEngineRuleConfigThriftImpl.java` BEFORE the entity reaches `saveSupplementaryPartnerProgramEntity`. See item 19 below.

---

#### 18. `PointsEngineRuleConfigThriftImpl.java` — Map new `isActive` field

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`

**Location**: In `createOrUpdatePartnerProgram()` handler (line 252+), after `getPartnerProgramEntity()` builds the entity, add:

```java
// KD-42: If isActive is explicitly set in the incoming Thrift struct (PAUSE/ARCHIVE/RESUME ops),
// apply it to the entity BEFORE saveSupplementaryPartnerProgramEntity is called.
// The entity builder does not carry isActive from PartnerProgramInfo; this wires the new field.
if (partnerProgramInfo.isSetIsActive()) {
    partnerProgramEntity.setActive(partnerProgramInfo.isIsActive());
}
```

**Exact position** (after line 259 `getPartnerProgramEntity(...)`):

```java
// Before (lines 256–263):
List<PartnerProgramSlab> partnerProgramSlabs = m_pointsEngineRuleEditor.getPartnerProgramSlabs(orgId,
        programId, partnerProgramInfo.getPartnerProgramId());
com.capillary.shopbook.points.entity.PartnerProgram partnerProgramEntity = getPartnerProgramEntity(
        partnerProgramInfo, orgId, programId, partnerProgramSlabs);
PartnerProgram oldPartnerProgram = m_pointsEngineRuleEditor.getPartnerProgram(
        partnerProgramInfo.getPartnerProgramId(), orgId);
partnerProgramEntity = m_pointsEngineRuleEditor.createOrUpdatePartnerProgram(orgId, partnerProgramEntity,
        oldPartnerProgram);
```

```java
// After:
List<PartnerProgramSlab> partnerProgramSlabs = m_pointsEngineRuleEditor.getPartnerProgramSlabs(orgId,
        programId, partnerProgramInfo.getPartnerProgramId());
com.capillary.shopbook.points.entity.PartnerProgram partnerProgramEntity = getPartnerProgramEntity(
        partnerProgramInfo, orgId, programId, partnerProgramSlabs);
// KD-42: Wire optional isActive override from Thrift struct to entity
if (partnerProgramInfo.isSetIsActive()) {
    partnerProgramEntity.setActive(partnerProgramInfo.isIsActive());
}
PartnerProgram oldPartnerProgram = m_pointsEngineRuleEditor.getPartnerProgram(
        partnerProgramInfo.getPartnerProgramId(), orgId);
partnerProgramEntity = m_pointsEngineRuleEditor.createOrUpdatePartnerProgram(orgId, partnerProgramEntity,
        oldPartnerProgram);
```

**Note**: `partnerProgramEntity` type is `com.capillary.shopbook.points.entity.PartnerProgram`. It has a `setActive(boolean)` method (from JPA entity). `partnerProgramInfo.isSetIsActive()` is the Thrift-generated isset check for optional field 15.

---

#### 19. `PointsEngineEndpointActionUtils.java` — New `is_active` enrollment guard

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/utils/PointsEngineEndpointActionUtils.java`

Add a new `public static` method (following the existing pattern for `validatePartnerProgramExpiry`):

```java
/**
 * KD-37 / RF-2: Block new enrollments if the partner program is PAUSED or ARCHIVED.
 * Called from PartnerProgramLinkingActionImpl.evaluateActionforSupplementaryLinking()
 * immediately after validatePartnerProgramExpiry().
 *
 * Evidence: PartnerProgram API interface (pointsengine.api.base.PartnerProgram) does NOT currently
 * expose isActive(). See item 20 for the required interface change.
 *
 * @param partnerProgram  The partner program entity from m_pointsProgramConfig
 * @throws PartnerProgramInactiveException if is_active = false in MySQL partner_programs table
 */
public static void validatePartnerProgramIsActive(
        com.capillary.shopbook.pointsengine.api.base.PartnerProgram partnerProgram,
        long customerId,
        String partnerProgramName) throws com.capillary.shopbook.points.services.exceptions.PartnerProgramInactiveException {

    if (!partnerProgram.isActive()) {
        String message = String.format(
                "Cannot enroll customer %d to partner program %s as it is inactive (PAUSED or ARCHIVED).",
                customerId, partnerProgramName);
        logger.info(message);
        throw new com.capillary.shopbook.points.services.exceptions.PartnerProgramInactiveException(
                message, null);
    }
}
```

**Exception class**: `PartnerProgramInactiveException` — new class to be created in `com.capillary.shopbook.points.services.exceptions` package, following the pattern of existing exceptions in that package (`PartnerProgramExpiredException`).

```java
// com/capillary/shopbook/points/services/exceptions/PartnerProgramInactiveException.java
package com.capillary.shopbook.points.services.exceptions;

public class PartnerProgramInactiveException extends PartnerProgramException {
    public PartnerProgramInactiveException(String message, Throwable cause) {
        super(PartnerProgramExceptionCode.PARTNER_PROGRAM_INACTIVE, message, cause);
    }
}
```

**Note on exception code**: A new `PARTNER_PROGRAM_INACTIVE` enum value must be added to `PartnerProgramExceptionCode` (if it exists as an enum). If `PartnerProgramExpiredException` is the right base, mirror its constructor pattern exactly.

---

#### 20. `PartnerProgramLinkingActionImpl.java` — Call the new guard

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/action/PartnerProgramLinkingActionImpl.java`

**Location**: In `evaluateActionforSupplementaryLinking()`, after the call to `PointsEngineEndpointActionUtils.validatePartnerProgramExpiry()` (line 228).

**Before** (line 228):
```java
PointsEngineEndpointActionUtils.validatePartnerProgramExpiry(payload, partnerProgram, membershipEndDate, customerId, partnerProgramName);
```

**After**:
```java
PointsEngineEndpointActionUtils.validatePartnerProgramExpiry(payload, partnerProgram, membershipEndDate, customerId, partnerProgramName);
// KD-37 / RF-2: Block enrollment if program is inactive (PAUSED or ARCHIVED)
PointsEngineEndpointActionUtils.validatePartnerProgramIsActive(partnerProgram, customerId, partnerProgramName);
```

**Prerequisite**: `PartnerProgram` API interface (`com.capillary.shopbook.pointsengine.api.base.PartnerProgram`) must expose `boolean isActive()`. Currently the interface does NOT have this method (C6 — confirmed from interface read, which only lists: `getID()`, `getLoyaltyProgramId()`, `getName()`, `getDescription()`, `getPartnerProgramIdentifier()`, `isTierBased()`, etc.). See item 21.

---

#### 21. `PartnerProgram.java` (API interface) — Add `isActive()` method

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/api/base/PartnerProgram.java`

**Current interface** (39 lines — fully read):
```java
public interface PartnerProgram extends Serializable {
    int getID();
    int getLoyaltyProgramId();
    String getName();
    String getDescription();
    String getPartnerProgramIdentifier();
    boolean isTierBased();
    List<PartnerProgramSlab> getPartnerProgramSlabs();
    PartnerProgramSlab getSlabByNumber(int serialNumber);
    PartnerProgramSlab getSlabByName(String name);
    PartnerProgramType getPartnerProgramType();
    PartnerProgramCycle getPartnerProgramCycle();
    Optional<Date> getPartnerProgramExpiryDate();
}
```

**Add** (after `getPartnerProgramExpiryDate()`):
```java
    /**
     * KD-37 / RF-2: Whether the partner program is currently active in MySQL.
     * Returns true if partner_programs.is_active = true.
     * Implementing class: com.capillary.shopbook.points.entity.PartnerProgram (JPA entity with isActive field).
     */
    boolean isActive();
```

**Impact**: All implementations of `PartnerProgram` interface must add `isActive()`. Search for all classes that implement `PartnerProgram` in emf-parent. The primary implementation is the JPA entity `com.capillary.shopbook.points.entity.PartnerProgram` which already has `setActive(boolean)` / `isActive()` via JPA field mapping. Any mock/stub implementations in test code must also be updated.

---

## Open Questions Resolved

### OQ-14 — MongoDB Optimistic Locking (RESOLVED)

**Question**: Exact mechanism for concurrent DRAFT edit protection — Spring Data `@Version`, `findAndModify`, or manual assertion?

**Resolution**: Use Spring Data MongoDB `@Version Long version` on `SubscriptionProgram`.

**Evidence**:
- `UnifiedPromotion.java` uses `private Integer version = 1` without `@Version` — it manages versioning manually for the parentId pattern.
- Spring Data MongoDB does support `@Version` annotation (Spring Data MongoDB 3.x+). When `@Version` is present, `MongoRepository.save()` includes the version in the WHERE clause of the update query. If the document was modified concurrently, `save()` throws `OptimisticLockingFailureException` (a `RuntimeException`).
- Decision: Use `@Version Long version` on `SubscriptionProgram`. This serves dual purpose: (a) Spring Data optimistic lock for concurrent DRAFT edits, and (b) version counter for parentId pattern (edit-of-ACTIVE increments version on copy).
- **Caution**: For the edit-of-ACTIVE flow, the new DRAFT document gets `version = null` initially (Spring Data will set it to 0 or 1 on first save). Set it explicitly to `activeDoc.version + 1` before saving. `@Version` field must be `Long` (not `Integer`) — Spring Data MongoDB requires `Long` or `long` for `@Version`.
- `OptimisticLockingFailureException` must be added to `TargetGroupErrorAdvice` → HTTP 409.

**Confidence**: C6 (Spring Data MongoDB documentation; no existing `@Version` usage in codebase to reference directly).

### OQ-15 — Subscriber Count API (RESOLVED)

**Question**: Does an existing Thrift method return per-program subscriber counts from `supplementary_partner_program_enrollment`?

**Evidence searched**:
- Searched `pointsengine_rules.thrift` for: `supplementary.*enrollment`, `enrollmentCount`, `countBy`, `getActiveCount`, `partnerProgram.*count`, `subscriberCount` — no matches.
- Found: `getMemberCountPerSlab(programId, orgId, serverReqId)` → returns `MemberCountPerSlabResponse` (slab-level member counts for tier slabs, not supplementary enrollment counts).
- Found: `getAllPartnerPrograms(programId, orgId, serverReqId)` → returns full `PartnerProgramInfo` list.
- **No existing Thrift method returns subscriber counts per supplementary partner program**.

**Resolution**: No existing Thrift method satisfies the subscriber-count requirement. Two options:
1. **Option A (recommended)**: Add a new Thrift method `getSupplementaryEnrollmentCountsByProgramIds(list<i32> partnerProgramIds, i32 orgId, string serverReqId) → map<i32, i64>` in the IDL. This is a bulk count query against `supplementary_partner_program_enrollment` table.
2. **Option B (fallback)**: Direct JDBC query in intouch-api-v3 if emf-parent Thrift change is out of scope for E3.

**Decision**: **Option A** — add a new Thrift method. This is the correct architectural approach (data ownership in emf-parent). Document as a new open question for the Architect to confirm scope.

**Impact**: This requires:
- New IDL method in `pointsengine_rules.thrift` (field number TBD — see current end of service)
- New implementation in `PointsEngineRuleConfigThriftImpl`
- New wrapper in `PointsEngineRulesThriftService`

**Confidence**: C7 (exhaustive Thrift IDL search confirmed no existing method).

### OQ-16 — Document ID Strategy (RESOLVED)

**Question**: UUID as `@Id` or auto ObjectId with separate `subscriptionProgramId` field?

**Evidence**: `UnifiedPromotion.java` uses:
- `@Id private String objectId` — MongoDB auto-generates ObjectId (26-char hex string)
- `private String unifiedPromotionId` — separate immutable UUID (business identifier)

**Resolution**: Follow the exact UnifiedPromotion pattern.
- `@Id private String objectId` — auto-generated MongoDB ObjectId. This is the document key used internally (parentId references this).
- `private String subscriptionProgramId` — UUID assigned at creation, immutable. This is the public-facing identifier used in API paths (e.g., `/v3/subscriptions/{subscriptionProgramId}`). Annotated `@JsonProperty(access = JsonProperty.Access.READ_ONLY)`.

**Confidence**: C7 (direct codebase evidence from UnifiedPromotion pattern).

### OQ-17 — Duplicate Action (RESOLVED)

**Question**: Does Duplicate produce a new DRAFT immediately? What fields reset?

**Resolution**: Duplicate produces a new DRAFT immediately via the creation path (no maker-checker submission required for the duplicate itself). Field mapping:
- `subscriptionProgramId` = new UUID
- `name` = `<original_name> (Copy)`
- `status` = `DRAFT`
- `version` = `1` (Spring Data will set to 0; set explicitly to 1 before save for consistency)
- `parentId` = `null` (this is a clean fork, not an edit-of-ACTIVE)
- `mysqlPartnerProgramId` = `null` (new program, not yet published to MySQL)
- `objectId` = null (MongoDB auto-generates on save)
- `workflowMetadata` = new empty (submittedBy=null, submittedAt=null, reviewedBy=null, reviewedAt=null)
- `comments` = null
- `createdBy` = current user
- `createdAt` = Instant.now()
- All other fields (duration, expiry, settings, tierConfig, benefits, reminders, customFields, groupTag, description) = copied from source.

**No MySQL write. No Thrift call. MongoDB-only.**

**Confidence**: C6 (derived from UnifiedPromotion pattern and BA AC-12 spec).

### OQ-18 — `programToPartnerProgramPointsRatio` default (RESOLVED)

**Question**: Required field in Thrift. Subscriptions have no ratio. Default to 1.0?

**Evidence**: `PartnerProgramInfo` field 6: `required double programToPartnerProgramPointsRatio`. In `getSupplementaryPartnerProgramEntity()` (emf-parent line 2054): `setPointsExchangeRatio(CalculationUtils.toBigDecimal(partnerProgramThrift.getProgramToPartnerProgramPointsRatio()))`. The ratio IS stored in MySQL. Setting 1.0 means "no exchange" (1 point = 1 point), which is semantically correct for subscriptions (no points-to-subscription-currency conversion).

**Resolution**: Default to `1.0` for all subscriptions. Not configurable in UI (E3 scope). `SubscriptionPublishService.buildPartnerProgramInfo()` sets `partnerProgramInfo.setProgramToPartnerProgramPointsRatio(1.0)` unconditionally.

**Confidence**: C6.

### OQ-19 — `isSyncWithLoyaltyTierOnDowngrade` default (RESOLVED)

**Question**: Required bool in Thrift. Default to false for NON_TIER, configurable for TIER_BASED?

**Evidence**: `PartnerProgramInfo` field 10: `required bool isSyncWithLoyaltyTierOnDowngrade`. In `getSupplementaryPartnerProgramEntity()`: only processed if `isIsSyncWithLoyaltyTierOnDowngrade()` is true (loyaltySyncTiers map populated). Setting false is safe — no sync configured, no `partner_program_tier_sync_configuration` rows inserted.

**Resolution**:
- `subscriptionType = NON_TIER`: always `isSyncWithLoyaltyTierOnDowngrade = false`.
- `subscriptionType = TIER_BASED`: `isSyncWithLoyaltyTierOnDowngrade = tierConfig.tierDowngradeOnExit` (the UI toggle drives this — BA AC-17).
- When `isSyncWithLoyaltyTierOnDowngrade = true`: `loyaltySyncTiers` map must be populated from `tierConfig.downgradeTargetTierId`.

**Confidence**: C7 (read emf-parent `getSupplementaryPartnerProgramEntity()` directly).

### OQ-20 — Custom fields storage type (RESOLVED)

**Question**: `metaCustomFields`, `linkCustomFields`, `delinkCustomFields` stored as `Map<String, Object>` or `Map<String, String>`?

**Resolution**: Stored as `List<CustomFieldRef>` (not Map). Each entry is `{extendedFieldId: Long, name: String}` — this is a reference list, not a key-value store. The `CustomFields` object has three lists: `meta`, `link`, `delink`. Each list element identifies which extended field is configured for that phase.

This is consistent with the HLD schema (Section 5.2) which shows `[{ "extendedFieldId": "Long", "name": "String" }]` arrays, not maps.

**Confidence**: C6 (derived from HLD schema + BA AC-24 spec).

---

## AC Traceability

| BA Acceptance Criteria | Interface that satisfies it |
|------------------------|----------------------------|
| AC-01: GET /subscriptions paginated list | `SubscriptionController.listSubscriptions()` + `SubscriptionFacade.listSubscriptions()` + `SubscriptionProgramRepository.findByOrgIdAndStatusIn()` |
| AC-02: Header stats (total, active, subscribers) | `SubscriptionFacade.getHeaderStats()` + `SubscriptionListResponse.HeaderStats` |
| AC-03: Multi-select status filter | `SubscriptionListRequest.statuses` + `findByOrgIdAndStatusIn()` |
| AC-04: Free-text search | `SubscriptionListRequest.search` → MongoDB text query in `SubscriptionFacade` |
| AC-05: Sorting (subscribers, lastModified, name) | `Pageable` with `Sort` in `SubscriptionController.listSubscriptions()` |
| AC-06: Grouped view by groupTag | `SubscriptionProgramRepository.findByOrgIdAndProgramIdAndGroupTag()` |
| AC-07: Benefits modal | `SubscriptionController.getBenefits()` |
| AC-08: Row actions (Duplicate, Archive) | `SubscriptionController.duplicateSubscription()` + `changeStatus(action=ARCHIVE)` |
| AC-09: Name/Description/Duration fields | `SubscriptionRequest` DTO fields + `@NotBlank`, `@Positive` validation |
| AC-10: Subscription type toggle | `SubscriptionRequest.subscriptionType` (TIER_BASED/NON_TIER enum) |
| AC-11: Required field validation | `@Valid @RequestBody` + `jakarta.validation` annotations on `SubscriptionRequest` |
| AC-12: Duplicate action | `SubscriptionController.duplicateSubscription()` + `SubscriptionFacade.duplicateSubscription()` |
| AC-13: Program expiry date | `SubscriptionRequest.ExpiryDto.programExpiryDate` (Instant) |
| AC-14: Restrict to one active per member | `SubscriptionRequest.SettingsDto.restrictToOneActivePerMember` |
| AC-15: Migrate on expiry | `SubscriptionRequest.ExpiryDto.migrateOnExpiry` + `migrationTargetProgramId` |
| AC-16: Linked Tier selector | `SubscriptionRequest.TierConfigDto.linkedTierId` |
| AC-17: Tier Downgrade on Exit | `SubscriptionRequest.TierConfigDto.tierDowngradeOnExit` + `downgradeTargetTierId` |
| AC-18/AC-19/AC-20/AC-21: Benefits management | `SubscriptionController.linkBenefit()` + `delinkBenefit()` + `SubscriptionFacade.linkBenefit/delinkBenefit()` |
| AC-22: Up to 5 reminders | `@Size(max = 5)` on `SubscriptionRequest.reminders` |
| AC-23: Reminder timeline (UI concern) | `SubscriptionProgram.reminders` stored in MongoDB — UI renders |
| AC-24/AC-25/AC-26: Custom fields | `SubscriptionRequest.CustomFieldsDto` with meta/link/delink lists |
| AC-27: Save as Draft | `SubscriptionController.createSubscription()` → sets status=DRAFT |
| AC-28: Submit for Approval | `SubscriptionController.changeStatus(action=SUBMIT_FOR_APPROVAL)` → `SubscriptionFacade.submitForApproval()` |
| AC-29: Cancel (UI concern) | No backend change |
| AC-30: Edit of ACTIVE | `SubscriptionFacade.updateSubscription()` — creates new DRAFT with parentId |
| AC-31: State machine transitions | `MakerCheckerService.submitForApproval()` / `approve()` / `reject()` |
| AC-32: Edit-of-ACTIVE versioning | `SubscriptionFacade.updateSubscription()` — parentId+version logic |
| AC-33: Old ACTIVE → ARCHIVED on approve | `SubscriptionApprovalHandler.postApprove()` — archives parent doc |
| AC-34: Reject preserves DRAFT + comment | `MakerCheckerService.reject()` → `postReject()` → status=DRAFT + comments |
| AC-35: Review endpoint | `SubscriptionReviewController.reviewSubscription()` |
| AC-36: List pending approvals | `SubscriptionReviewController.listPendingApprovals()` |
| AC-37: Generic maker-checker | `MakerCheckerService<T extends ApprovableEntity>` + `ApprovableEntityHandler<T>` |
| AC-38: Publish-on-approve | `SubscriptionPublishService.publishToMySQL()` via SAGA |
| AC-39: Pause action | `SubscriptionController.changeStatus(PAUSE)` → `SubscriptionFacade.pauseSubscription()` → `SubscriptionPublishService.publishIsActive(false)` |
| AC-40: Resume action | `changeStatus(RESUME)` → `resumeSubscription()` → `publishIsActive(true)` |
| AC-41: Archive action | `changeStatus(ARCHIVE)` → `archiveSubscription()` → `publishIsActive(false)` |
| AC-42: Scheduled state | Out of scope for E3 (per HLD — no SCHEDULED state, KD-26/KD-34) |
| AC-43 to AC-47: Future-dated enrollment | emf-parent existing enrollment path — no change in E3 |
| AC-48: Tier downgrade on exit | Driven by `isSyncWithLoyaltyTierOnDowngrade` Thrift field (OQ-19 resolved) |

---

## Open Questions for QA / Developer

### NEW-OQ-01: Subscriber Count Thrift Method (CLOSED — KD-46)
No existing Thrift method returns per-supplementary-program subscriber counts (OQ-15 resolved: no match found). A new Thrift method is required. **Confirmed in scope for E3. User-approved parameters: org_id, program_id, partner_program_ids.**

```thrift
// Add to pointsengine_rules.thrift service (PointsEngineRuleService):
map<i32, i64> getSupplementaryEnrollmentCountsByProgramIds(
    1: list<i32> partnerProgramIds,
    2: i32 orgId,
    3: i32 programId,
    4: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);
```

**Implementation chain (all in E3 scope)**:
- `pointsengine_rules.thrift`: Add method above to `PointsEngineRuleService` service block
- `emf-parent PointsEngineRuleConfigThriftImpl`: Implement method — DAO query on `supplementary_partner_program_enrollment` filtered by `orgId`, `loyalty_program_id = programId`, `partner_program_id IN (partnerProgramIds)`, grouped by `partner_program_id`, returning `COUNT(*)` per id
- `intouch-api-v3 PointsEngineRulesThriftService` (or equivalent Thrift client wrapper): Expose the new method to `SubscriptionFacade`

The Developer must verify this is in scope for E3 or if subscriber-count display will be deferred / sourced differently.

### NEW-OQ-02: `PartnerProgramInactiveException` base class
`PartnerProgramInactiveException` must follow the existing `PartnerProgramExpiredException` pattern exactly. Developer must verify `PartnerProgramExceptionCode` enum exists and add `PARTNER_PROGRAM_INACTIVE` value, or use a different construction pattern.

### NEW-OQ-03: `PartnerProgram` interface implementations
Adding `boolean isActive()` to `PartnerProgram` API interface will break all implementing classes. Developer must find all implementations (via IDE/LSP `Find Implementations`) and add the method. The primary JPA entity implementation already has the field.

### NEW-OQ-04: `@Version` and edit-of-ACTIVE version management
When creating a DRAFT from an ACTIVE doc (edit-of-ACTIVE), the new DRAFT's `version` field must be set to `activeDoc.version + 1` before calling `repository.save()`. However, `@Version` fields are managed by Spring Data — if the field is set explicitly, Spring Data will use it as the initial version for the new document. The Developer must test this behavior to confirm Spring Data MongoDB does not override an explicitly-set version.

### NEW-OQ-05: `TargetGroupErrorAdvice` — `OptimisticLockingFailureException` handler
`OptimisticLockingFailureException` (Spring Data) is not handled in `TargetGroupErrorAdvice`. This will fall through to the generic 500 handler. Developer should add a specific handler mapping it to HTTP 409.

### NEW-OQ-06: Caffeine cache for subscriber counts
Architect specified 60s TTL Caffeine cache for subscriber counts (Section 5.6.5). `SubscriptionFacade.getHeaderStats()` needs a `@Cacheable` or manual cache. Confirm Caffeine is on the classpath (it likely is via Spring Boot Cache autoconfigure). Developer to check `ApiCacheRegions` for an appropriate cache name or define a new one.

### NEW-OQ-07: `user.getEntityId()` as createdBy/updatedBy
The controller passes `user.getEntityId()` as the `createdBy` parameter. Developer must verify this is the appropriate field for "user identifier" in the `IntouchUser` class. `UnifiedPromotionController` does not surface a `createdBy` field directly in visible code — verify via `IntouchUser` class.

---

## Summary of New Files

### intouch-api-v3 — New files (20 total)

| File | Package |
|------|---------|
| `SubscriptionProgram.java` | `unified.subscription` |
| `SubscriptionProgramRepository.java` | `unified.subscription` |
| `SubscriptionFacade.java` | `unified.subscription` |
| `SubscriptionPublishService.java` | `unified.subscription` |
| `SubscriptionApprovalHandler.java` | `unified.subscription` |
| `SubscriptionStatusValidator.java` | `unified.subscription` |
| `SubscriptionMapper.java` | `unified.subscription` |
| `SubscriptionController.java` | `resources` |
| `SubscriptionReviewController.java` | `resources` |
| `SubscriptionRequest.java` | `unified.subscription.dto` |
| `SubscriptionResponse.java` | `unified.subscription.dto` |
| `SubscriptionListResponse.java` | `unified.subscription.dto` |
| `SubscriptionListItem.java` | `unified.subscription.dto` |
| `SubscriptionListRequest.java` | `unified.subscription.dto` |
| `ApprovalRequest.java` | `unified.subscription.dto` |
| `StatusChangeRequest.java` | `unified.subscription.dto` |
| `BenefitLinkRequest.java` | `unified.subscription.dto` |
| `ApprovableEntity.java` | `makechecker` |
| `ApprovableEntityHandler.java` | `makechecker` |
| `MakerCheckerService.java` | `makechecker` |
| `PublishResult.java` | `makechecker` |
| `SubscriptionNotFoundException.java` | `unified.subscription.exception` |
| `InvalidSubscriptionStateException.java` | `unified.subscription.exception` |
| `SubscriptionNameConflictException.java` | `unified.subscription.exception` |
| Enums: `SubscriptionStatus`, `SubscriptionType`, `CycleType`, `MigrateOnExpiry`, `ReminderChannel`, `SubscriptionAction` | `unified.subscription.enums` |

### intouch-api-v3 — Modified files (2)
- `EmfMongoConfig.java` — 1 line + 1 import
- `PointsEngineRulesThriftService.java` — 2 new methods (~60 lines total)
- `TargetGroupErrorAdvice.java` — 3 new `@ExceptionHandler` methods

### thrift-ifaces-pointsengine-rules — Modified (1)
- `pointsengine_rules.thrift` — 1 new field (line 415: `15: optional bool isActive`)

### emf-parent — Modified (4 files)
- `PointsEngineRuleConfigThriftImpl.java` — 3-line conditional insert in `createOrUpdatePartnerProgram()`
- `PointsEngineEndpointActionUtils.java` — 1 new `public static` method (~18 lines)
- `PartnerProgramLinkingActionImpl.java` — 2-line insert in `evaluateActionforSupplementaryLinking()`
- `PartnerProgram.java` (interface) — 1 new method `boolean isActive()`

### emf-parent — New files (1)
- `PartnerProgramInactiveException.java` — in `com.capillary.shopbook.points.services.exceptions`

---

---

## Phase 7 Rework — 12 Critical Gaps (2026-04-15)

> This section is ADDITIVE. All content above remains valid except where explicitly superseded below.
> References: ADR-08 through ADR-18 in 01-architect.md; KD-47 through KD-58 in session-memory.md.

---

### R-1: Updated SubscriptionProgram Field Contracts (GAP-1, GAP-2, ADR-08, ADR-09, ADR-18)

The following fields in `SubscriptionProgram.java` have WRONG validation constraints in the existing code and in section "1. SubscriptionProgram.java" above. The actual file currently has:
- `name`: `@NotBlank @Size(max=255)` — **WRONG**
- `description`: `@Size(max=1000)` only, optional — **WRONG**
- `subscriptionProgramId` Javadoc comment — **WRONG**

**Required changes (Developer must apply):**

#### R-1.1 name field — corrected constraint

```java
// BEFORE (current file, line 80-82):
@NotBlank
@Size(max = 255)
private String name;

// AFTER (ADR-08 — KD-47):
@NotBlank(message = "SUBSCRIPTION.NAME_REQUIRED")
@Size(max = 50, message = "SUBSCRIPTION.NAME_TOO_LONG")
@Pattern(regexp = "^[a-zA-Z0-9_\\-: ]*$", message = "only alphabets, spaces, numerals, _, -, : are allowed")
private String name;
```

#### R-1.2 description field — corrected constraint

```java
// BEFORE (current file, line 84-85):
@Size(max = 1000)
private String description;

// AFTER (ADR-09 — KD-48):
@NotBlank(message = "SUBSCRIPTION.DESCRIPTION_REQUIRED")
@Size(max = 100, message = "SUBSCRIPTION.DESCRIPTION_TOO_LONG")
@Pattern(regexp = "^[a-zA-Z0-9_\\-: ,.\\s]*$", message = "only alphabets, numerals, space, _, -, :, comma, dot max 100 chars")
private String description;
```

**Rationale**: MySQL `partner_programs.description` is NOT NULL — allowing null/blank at API layer was a latent SAGA failure risk on approval.

#### R-1.3 subscriptionProgramId Javadoc — corrected comment

```java
// BEFORE (current file, lines 42-47 — WRONG):
/**
 * Immutable business identifier (UUID). Assigned at creation. Constant across
 * versions only for initial creates. Edits-of-ACTIVE produce a new UUID for the draft.
 */
@JsonProperty(access = JsonProperty.Access.READ_ONLY)
private String subscriptionProgramId;

// AFTER (ADR-18 — KD-58):
/**
 * Immutable business identifier (UUID, no dashes). Generated once at CREATE.
 * COPIED to all subsequent versions: DRAFT edits, edit-of-ACTIVE forks.
 * Only DUPLICATE action generates a new UUID.
 * Used as the primary key in all REST API paths (ADR-18).
 */
@JsonProperty(access = JsonProperty.Access.READ_ONLY)
private String subscriptionProgramId;
```

#### R-1.4 New fields on SubscriptionProgram (GAP-5, GAP-6, GAP-7 — ADR-12, ADR-13, ADR-14)

Add these three new fields to the `SubscriptionProgram` class, after the `subscriptionType` field:

```java
/**
 * Points exchange ratio between loyalty program and this partner program.
 * Thrift field 6 (programToPartnerProgramPointsRatio). Required. No default (ADR-12).
 * Replaces hardcoded DEFAULT_POINTS_RATIO = 1.0 in SubscriptionPublishService.
 */
@NotNull
@Positive
private Double pointsExchangeRatio;

/**
 * Partner program type — SUPPLEMENTARY (subscription) or EXTERNAL (coalition).
 * Thrift field 8 (partnerProgramType). Required (ADR-14).
 * Duration is REQUIRED when SUPPLEMENTARY; FORBIDDEN when EXTERNAL (cross-field validation
 * enforced in SubscriptionApprovalHandler.validateForSubmission()).
 */
@NotNull
private PartnerProgramType programType;

/**
 * Whether loyalty tier sync on downgrade is enabled.
 * Thrift field 10 (isSyncWithLoyaltyTierOnDowngrade). Required (ADR-13).
 * Direct user input — NOT derived from subscriptionType or tierDowngradeOnExit.
 * Cross-field: when true, tierConfig.loyaltySyncTiers must be non-empty.
 */
@NotNull
private Boolean syncWithLoyaltyTierOnDowngrade;
```

**Import to add**: `import com.capillary.intouchapiv3.unified.subscription.enums.PartnerProgramType;`

#### R-1.5 Updated TierConfig nested class (GAP-9, GAP-10 — ADR-16, ADR-17)

The existing `TierConfig` class is missing two fields. Replace the TierConfig class definition with:

```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public static class TierConfig {
    /** Required when subscriptionType=TIER_BASED */
    private Integer linkedTierId;
    private Boolean tierDowngradeOnExit;
    /** Required when tierDowngradeOnExit=true */
    private Integer downgradeTargetTierId;

    /**
     * Ordered list of tiers for this partner program.
     * Thrift field 5 (partnerProgramTiers). Required when TIER_BASED; empty when NON_TIER.
     * Each entry: {tierNumber (serial_number in partner_program_slabs), tierName}.
     * Cross-field validation: TIER_BASED requires non-empty list (ADR-16).
     */
    @Builder.Default
    private List<ProgramTier> tiers = new ArrayList<>();

    /**
     * Maps partner tier name to loyalty tier name for sync-on-downgrade.
     * Thrift field 11 (loyaltySyncTiers). Required when syncWithLoyaltyTierOnDowngrade=true (ADR-17).
     * Stored in MySQL via partner_program_tier_sync_configuration (PointsEngineRuleService maps
     * names to IDs via slab lookup).
     */
    private Map<String, String> loyaltySyncTiers;
}
```

#### R-1.6 New nested class ProgramTier (ADR-16)

Add inside `SubscriptionProgram`, after the `TierConfig` class:

```java
/**
 * A single tier entry in a partner program tier list.
 * Maps to partner_program_slabs (serial_number → tierNumber, name → tierName).
 * Wired to Thrift field 5 partnerProgramTiers (ADR-16).
 */
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public static class ProgramTier {
    @NotNull
    private Integer tierNumber;
    @NotBlank
    private String tierName;
}
```

#### Updated field summary table for SubscriptionProgram

| Field | Type | Constraints | ADR | Previous (Wrong) |
|-------|------|-------------|-----|-----------------|
| `name` | `String` | `@NotBlank @Size(max=50) @Pattern(^[a-zA-Z0-9_\-: ]*$)` | ADR-08 | `@NotBlank @Size(max=255)` — FIXED |
| `description` | `String` | `@NotBlank @Size(max=100) @Pattern(^[a-zA-Z0-9_\-: ,.\s]*$)` | ADR-09 | `@Size(max=1000)` optional — FIXED |
| `pointsExchangeRatio` | `Double` | `@NotNull @Positive` | ADR-12 | Missing — ADDED |
| `programType` | `PartnerProgramType` | `@NotNull` (SUPPLEMENTARY\|EXTERNAL) | ADR-14 | Missing (was hardcoded SUPPLEMENTARY) — ADDED |
| `syncWithLoyaltyTierOnDowngrade` | `Boolean` | `@NotNull` | ADR-13 | Missing (was derived incorrectly) — ADDED |
| `subscriptionProgramId` | `String` | `@JsonProperty(READ_ONLY)` — Javadoc corrected | ADR-18 | Wrong comment — FIXED |
| `TierConfig.tiers` | `List<ProgramTier>` | `@Builder.Default` empty list | ADR-16 | Missing — ADDED |
| `TierConfig.loyaltySyncTiers` | `Map<String,String>` | — | ADR-17 | Missing — ADDED |

---

### R-2: New Enum — PartnerProgramType (GAP-7, ADR-14)

**File**: `com/capillary/intouchapiv3/unified/subscription/enums/PartnerProgramType.java`

```java
package com.capillary.intouchapiv3.unified.subscription.enums;

/**
 * Partner program type for subscription programs (ADR-14).
 * SUPPLEMENTARY: time-boxed subscription with duration (cycle type + value required).
 * EXTERNAL: coalition/external program — duration field FORBIDDEN.
 *
 * Maps to Thrift PartnerProgramType enum in pointsengine_rules.thrift:
 *   EXTERNAL = 1, SUPPLEMENTARY = 2
 * Maps to MySQL partner_programs.type enum (EXTERNAL | SUPPLEMENTARY).
 */
public enum PartnerProgramType {
    SUPPLEMENTARY,
    EXTERNAL
}
```

**Note on enum file to add to Summary of New Files** (section at end of original doc):
- `PartnerProgramType.java` — `unified.subscription.enums`

---

### R-3: Remove YEARS from CycleType enum (GAP-3, ADR-10)

**File**: `com/capillary/intouchapiv3/unified/subscription/enums/CycleType.java`

**Current file (confirmed by reading actual file)**:
```java
public enum CycleType {
    DAYS, MONTHS, YEARS
}
```

**YEARS must be removed (Option A — ADR-10 preferred):**

```java
package com.capillary.intouchapiv3.unified.subscription.enums;

/**
 * Duration cycle type for subscription programs.
 * Only DAYS and MONTHS are valid at the API boundary (ADR-10, KD-49).
 *
 * YEARS is NOT supported:
 * - Thrift PartnerProgramCycleType has only DAYS and MONTHS (C7 — session-memory line 50)
 * - MySQL supplementary_membership_cycle_details enum is only DAYS/MONTHS (C7)
 * - UI schema (createOrUpdatePartnerProgram.schema.js) has no YEARS option
 * - ADR-07 (store YEARS, convert on publish) is SUPERSEDED by ADR-10
 *
 * Note: SubscriptionPublishService.convertCycle() previously handled YEARS→MONTHS×12.
 * That method is now simplified — no YEARS case needed. Remove MONTHS_PER_YEAR constant.
 */
public enum CycleType {
    DAYS, MONTHS
}
```

**Side effect**: `SubscriptionPublishService.convertCycle()` had a branch for `CycleType.YEARS`. That branch must be removed. The `MONTHS_PER_YEAR = 12` constant must be removed. See R-5 below for the updated `buildPartnerProgramInfo()` spec.

---

### R-4: Case-Insensitive Name Uniqueness in Repository (GAP-4, ADR-11)

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionProgramRepository.java`

Replace the existing `findActiveByOrgIdAndName` query method with:

```java
/**
 * Check name uniqueness within MongoDB scope — CASE INSENSITIVE (ADR-11, KD-50).
 *
 * IMPORTANT: Callers MUST pass Pattern.quote(name) to escape regex metacharacters.
 * If the subscription name contains characters like +, *, ., (, ) they would be
 * interpreted as regex operators without quoting. Example caller pattern:
 *   repository.findActiveByOrgIdAndName(orgId, Pattern.quote(name))
 *
 * Why $regex: MySQL UNIQUE KEY (org_id, name) is case-insensitive by default.
 * Storing "GoldCard" and "goldcard" as separate MongoDB docs would pass MongoDB uniqueness
 * but fail on MySQL publish (DUPLICATE KEY error). The $regex/$options:'i' prevents this.
 * Full cross-system uniqueness check happens in preApprove() via Thrift getAllPartnerPrograms().
 *
 * Statuses covered: DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED (not ARCHIVED).
 */
@Query("{'orgId': ?0, 'name': {$regex: ?1, $options: 'i'}, 'status': { $in: ['DRAFT', 'PENDING_APPROVAL', 'ACTIVE', 'PAUSED'] }}")
Optional<SubscriptionProgram> findActiveByOrgIdAndName(Long orgId, String name);
```

**Import required in callers**: `java.util.regex.Pattern`

**Caller update in SubscriptionFacade.createSubscription()** — the existing call:
```java
repository.findActiveByOrgIdAndName(orgId, request.getName())
```
must become:
```java
repository.findActiveByOrgIdAndName(orgId, Pattern.quote(request.getName()))
```

**Caller update in SubscriptionApprovalHandler.preApprove()** — similarly:
```java
repository.findActiveByOrgIdAndName(entity.getOrgId(), entity.getName())
```
must become:
```java
repository.findActiveByOrgIdAndName(entity.getOrgId(), Pattern.quote(entity.getName()))
```

---

### R-5: Updated SubscriptionPublishService.buildPartnerProgramInfo() Specification (GAP-5 through GAP-10, ADR-12 through ADR-17)

The existing `SubscriptionPublishService.java` (read from actual file) has multiple wrong hardcoded values:
- `DEFAULT_POINTS_RATIO = 1.0` hardcoded — **WRONG** (remove)
- `partnerProgramType = SUPPLEMENTARY` hardcoded — **WRONG** (use field)
- `isSyncWithLoyaltyTierOnDowngrade` derived from `TIER_BASED && tierDowngradeOnExit` — **WRONG** (use direct field)
- YEARS conversion still present — **REMOVE** (ADR-10)
- `partnerProgramTiers` not wired — **MISSING**
- `loyaltySyncTiers` not wired — **MISSING**

**Full corrected `buildPartnerProgramInfo()` specification:**

```java
/**
 * Build the PartnerProgramInfo Thrift struct from a MongoDB SubscriptionProgram document.
 *
 * Rework 2026-04-15 (ADR-10 through ADR-17):
 * - YEARS conversion REMOVED (ADR-10: YEARS rejected at API boundary; MongoDB stores DAYS/MONTHS directly)
 * - DEFAULT_POINTS_RATIO removed; uses program.getPointsExchangeRatio() (ADR-12)
 * - partnerProgramType from program.getProgramType(), NOT hardcoded SUPPLEMENTARY (ADR-14)
 * - isSyncWithLoyaltyTierOnDowngrade from program.getSyncWithLoyaltyTierOnDowngrade() (ADR-13)
 * - partnerProgramTiers wired from tierConfig.tiers (ADR-16)
 * - loyaltySyncTiers wired from tierConfig.loyaltySyncTiers (ADR-17)
 * - duration conditional: only set for SUPPLEMENTARY; null/unset for EXTERNAL (ADR-14)
 * - Reminders NOT written via Thrift (KD-39, ADR-06)
 * - partner_program_identifier auto-generated by EMFUtils in emf-parent (KD-43)
 * - SAGA idempotency: partnerProgramId set when mysqlPartnerProgramId is already known (RF-6)
 *
 * Package-private for unit testability.
 */
PartnerProgramInfo buildPartnerProgramInfo(SubscriptionProgram program, Long orgId) {
    PartnerProgramInfo info = new PartnerProgramInfo();

    // Field 2: name
    info.partnerProgramName = program.getName();

    // Field 3: description — now required (ADR-09), no null default needed
    info.description = program.getDescription();

    // Field 4: isTierBased
    boolean isTierBased = SubscriptionType.TIER_BASED.equals(program.getSubscriptionType());
    info.isTierBased = isTierBased;

    // Field 5: partnerProgramTiers — wired from tierConfig.tiers (ADR-16)
    if (isTierBased && program.getTierConfig() != null
            && program.getTierConfig().getTiers() != null) {
        info.partnerProgramTiers = program.getTierConfig().getTiers().stream()
                .map(t -> {
                    PartnerProgramTier ppt = new PartnerProgramTier();
                    ppt.tierNumber = t.getTierNumber();
                    ppt.tierName   = t.getTierName();
                    return ppt;
                })
                .collect(java.util.stream.Collectors.toList());
    } else {
        info.partnerProgramTiers = java.util.Collections.emptyList();
    }

    // Field 6: programToPartnerProgramPointsRatio — from model, NOT hardcoded (ADR-12)
    info.programToPartnerProgramPointsRatio = program.getPointsExchangeRatio();

    // Field 7: partnerProgramUniqueIdentifier — DO NOT SET; auto-generated by EMFUtils (KD-43)

    // Field 8: partnerProgramType — from model, NOT hardcoded SUPPLEMENTARY (ADR-14)
    info.partnerProgramType = PartnerProgramType.valueOf(program.getProgramType().name());

    // Field 9: partnerProgramMembershipCycle — conditional on programType (ADR-14)
    // SUPPLEMENTARY: duration required; set the cycle. EXTERNAL: do NOT set (null/unset).
    if (com.capillary.intouchapiv3.unified.subscription.enums.PartnerProgramType.SUPPLEMENTARY
            .equals(program.getProgramType())
            && program.getDuration() != null) {
        PartnerProgramMembershipCycle cycle = new PartnerProgramMembershipCycle();
        // No YEARS conversion needed post-ADR-10; cycleType in MongoDB is already DAYS or MONTHS
        cycle.cycleType = PartnerProgramCycleType.findByValue(
                program.getDuration().getCycleType().ordinal());
        cycle.cycleValue = program.getDuration().getCycleValue();
        info.partnerProgramMembershipCycle = cycle;
    }
    // For EXTERNAL: info.partnerProgramMembershipCycle remains unset (null)

    // Field 10: isSyncWithLoyaltyTierOnDowngrade — direct user field, NOT derived (ADR-13)
    info.isSyncWithLoyaltyTierOnDowngrade = Boolean.TRUE.equals(
            program.getSyncWithLoyaltyTierOnDowngrade());

    // Field 11: loyaltySyncTiers — from tierConfig.loyaltySyncTiers (ADR-17)
    if (Boolean.TRUE.equals(program.getSyncWithLoyaltyTierOnDowngrade())
            && program.getTierConfig() != null
            && program.getTierConfig().getLoyaltySyncTiers() != null) {
        info.loyaltySyncTiers = program.getTierConfig().getLoyaltySyncTiers();
    }

    // Field 12: updatedViaNewUI — always true for new UI flows
    info.updatedViaNewUI = true;

    // Field 13: expiryDate — null if no expiry (epoch millis, G-01.1)
    if (program.getExpiry() != null && program.getExpiry().getProgramExpiryDate() != null) {
        info.expiryDate = program.getExpiry().getProgramExpiryDate().toEpochMilli();
    }

    // Field 14: backupProgramId — MySQL backup_partner_program_id (KD-33)
    if (program.getExpiry() != null && program.getExpiry().getMigrationTargetProgramId() != null) {
        info.backupProgramId = program.getExpiry().getMigrationTargetProgramId();
    }

    // Field 1: partnerProgramId — set only when updating an existing MySQL record (SAGA idempotency, RF-6)
    if (program.getMysqlPartnerProgramId() != null) {
        info.partnerProgramId = program.getMysqlPartnerProgramId();
    }

    return info;
}
```

**Constants to REMOVE from SubscriptionPublishService:**
- `static final double DEFAULT_POINTS_RATIO = 1.0;` — REMOVE (ADR-12)
- `static final int MONTHS_PER_YEAR = 12;` — REMOVE (ADR-10, no YEARS conversion)

**Method to REMOVE from SubscriptionPublishService:**
- `int[] convertCycle(CycleType cycleType, int cycleValue)` — REMOVE (ADR-10, no longer needed)
  - If a simpler passthrough is still needed for test isolation, it can be retained but simplified to remove the YEARS branch entirely.

**New import required in SubscriptionPublishService:**
```java
import com.capillary.shopbook.pointsengine.endpoint.api.external.PartnerProgramTier;
import java.util.Collections;
import java.util.stream.Collectors;
```

#### Complete 15-Field Thrift Mapping Table

| Thrift Field # | Field Name | Source | Mapping Expression | Notes |
|---|---|---|---|---|
| 1 | `partnerProgramId` | `mysqlPartnerProgramId` | Set when non-null (UPDATE semantics) | Null = INSERT new record |
| 2 | `partnerProgramName` | `name` | `program.getName()` | ADR-08: max 50, regex validated |
| 3 | `description` | `description` | `program.getDescription()` | ADR-09: required, max 100, no null default |
| 4 | `isTierBased` | `subscriptionType` | `subscriptionType == TIER_BASED` | Boolean derivation |
| 5 | `partnerProgramTiers` | `tierConfig.tiers` | Map `List<ProgramTier>` → `List<PartnerProgramTier>` when TIER_BASED; empty list when NON_TIER | **Was never wired (GAP-9/ADR-16)** |
| 6 | `programToPartnerProgramPointsRatio` | `pointsExchangeRatio` | `program.getPointsExchangeRatio()` | **Was hardcoded 1.0 (GAP-5/ADR-12)** |
| 7 | `partnerProgramUniqueIdentifier` | N/A | Do NOT set | Auto-generated by EMFUtils in emf-parent (KD-43) |
| 8 | `partnerProgramType` | `programType` | `PartnerProgramType.valueOf(program.getProgramType().name())` | **Was hardcoded SUPPLEMENTARY (GAP-7/ADR-14)** |
| 9 | `partnerProgramMembershipCycle` | `duration` | When SUPPLEMENTARY: set `{cycleType, cycleValue}`. When EXTERNAL: DO NOT SET (null) | Conditional on programType (ADR-14). No YEARS conversion (ADR-10) |
| 10 | `isSyncWithLoyaltyTierOnDowngrade` | `syncWithLoyaltyTierOnDowngrade` | `Boolean.TRUE.equals(program.getSyncWithLoyaltyTierOnDowngrade())` | **Was derived wrongly from TIER_BASED&&tierDowngradeOnExit (GAP-6/ADR-13)** |
| 11 | `loyaltySyncTiers` | `tierConfig.loyaltySyncTiers` | When sync=true: `program.getTierConfig().getLoyaltySyncTiers()`. Else: DO NOT SET | **Was never wired (GAP-10/ADR-17)** |
| 12 | `updatedViaNewUI` | Hardcoded `true` | `info.updatedViaNewUI = true` | Always true for new UI flows |
| 13 | `expiryDate` | `expiry.programExpiryDate` | `.toEpochMilli()` when non-null | i64 UTC epoch millis (G-01.1) |
| 14 | `backupProgramId` | `expiry.migrationTargetProgramId` | Set when non-null | MySQL backup_partner_program_id (KD-33) |
| 15 | `isActive` | Runtime lifecycle flag | Set only in `publishIsActive()` calls; NOT set in initial publish | `optional bool` — when unset, emf-parent preserves existing value |

---

### R-6: Updated SubscriptionApprovalHandler.validateForSubmission() — Cross-Field Validations (GAP-8, ADR-14 through ADR-17)

The existing `validateForSubmission()` (confirmed from actual file read) currently validates:
- `name` not blank
- `duration` not null
- `duration.cycleValue` positive
- `TIER_BASED` requires `linkedTierId`
- `tierDowngradeOnExit=true` requires `downgradeTargetTierId`

**Required additions (add in order, after existing checks):**

```java
// ADR-12: pointsExchangeRatio required and positive
if (entity.getPointsExchangeRatio() == null || entity.getPointsExchangeRatio() <= 0) {
    throw new InvalidInputException("pointsExchangeRatio must be positive and non-null");
}

// ADR-14: programType is required
if (entity.getProgramType() == null) {
    throw new InvalidInputException("programType is required (SUPPLEMENTARY or EXTERNAL)");
}

// ADR-14: SUPPLEMENTARY requires duration; EXTERNAL must NOT have duration
if (PartnerProgramType.SUPPLEMENTARY.equals(entity.getProgramType())) {
    if (entity.getDuration() == null) {
        throw new InvalidInputException("duration required for SUPPLEMENTARY programs");
    }
} else if (PartnerProgramType.EXTERNAL.equals(entity.getProgramType())) {
    // Clear duration for EXTERNAL — should not be set, but be tolerant on input
    entity.setDuration(null);
}

// ADR-15: When migration enabled, migrationTargetProgramId must be > 0
if (entity.getExpiry() != null
        && entity.getExpiry().getMigrateOnExpiry() != null
        && !MigrateOnExpiry.NONE.equals(entity.getExpiry().getMigrateOnExpiry())
        && entity.getExpiry().getProgramExpiryDate() != null) {
    Integer targetId = entity.getExpiry().getMigrationTargetProgramId();
    if (targetId == null || targetId <= 0) {
        throw new InvalidInputException(
                "migrationTargetProgramId must be > 0 when migration is enabled");
    }
}

// ADR-16: When TIER_BASED, tiers list must not be empty
if (SubscriptionType.TIER_BASED.equals(entity.getSubscriptionType())) {
    if (entity.getTierConfig() == null
            || entity.getTierConfig().getTiers() == null
            || entity.getTierConfig().getTiers().isEmpty()) {
        throw new InvalidInputException(
                "TIER_BASED subscription requires non-empty tierConfig.tiers list");
    }
}

// ADR-17: When syncWithLoyaltyTierOnDowngrade=true, loyaltySyncTiers must not be empty
if (Boolean.TRUE.equals(entity.getSyncWithLoyaltyTierOnDowngrade())) {
    if (entity.getTierConfig() == null
            || entity.getTierConfig().getLoyaltySyncTiers() == null
            || entity.getTierConfig().getLoyaltySyncTiers().isEmpty()) {
        throw new InvalidInputException(
                "loyaltySyncTiers required when syncWithLoyaltyTierOnDowngrade=true");
    }
}
```

**Imports required** in `SubscriptionApprovalHandler.java`:
```java
import com.capillary.intouchapiv3.unified.subscription.enums.MigrateOnExpiry;
import com.capillary.intouchapiv3.unified.subscription.enums.PartnerProgramType;
```

**Complete validation order in validateForSubmission() (final spec):**

| # | Validation | Error Message | ADR |
|---|------------|--------------|-----|
| 1 | `name` not blank | "Subscription name is required" | existing |
| 2 | `duration` not null (when SUPPLEMENTARY) | "Subscription duration is required" | existing + ADR-14 |
| 3 | `duration.cycleValue` positive | "cycleValue must be a positive integer" | existing |
| 4 | TIER_BASED requires `linkedTierId` | "TIER_BASED subscription requires linkedTierId" | existing |
| 5 | `tierDowngradeOnExit=true` requires `downgradeTargetTierId` | "tierDowngradeOnExit=true requires downgradeTargetTierId" | existing |
| 6 | `pointsExchangeRatio` not null and positive | "pointsExchangeRatio must be positive and non-null" | ADR-12 |
| 7 | `programType` not null | "programType is required (SUPPLEMENTARY or EXTERNAL)" | ADR-14 |
| 8 | SUPPLEMENTARY requires duration; EXTERNAL clears duration | "duration required for SUPPLEMENTARY programs" | ADR-14 |
| 9 | Migration: `migrationTargetProgramId` > 0 when enabled | "migrationTargetProgramId must be > 0 when migration is enabled" | ADR-15 |
| 10 | TIER_BASED requires non-empty `tierConfig.tiers` | "TIER_BASED subscription requires non-empty tierConfig.tiers list" | ADR-16 |
| 11 | `syncWithLoyaltyTierOnDowngrade=true` requires non-empty `loyaltySyncTiers` | "loyaltySyncTiers required when syncWithLoyaltyTierOnDowngrade=true" | ADR-17 |

---

### R-7: Missing SubscriptionFacade Methods — updateSubscription and editActiveSubscription (GAP-11, ADR-18)

The existing `SubscriptionFacade.java` (confirmed from actual file read) is MISSING these two methods. The `PUT /v3/subscriptions/{id}` controller endpoint calls `subscriptionFacade.updateSubscription()` which throws `UnsupportedOperationException` (skeleton state). Both methods must be implemented.

Note on the existing SubscriptionFacade: the actual implementation file contains methods (`createSubscription`, `getSubscription`, `listSubscriptions`, `duplicateSubscription`, `submitForApproval`, etc.) but NOT `updateSubscription` or `editActiveSubscription`.

The designer-phase LLD specification (section 7 above) has a partial `updateSubscription` signature but it is merged into one method. **ADR-18 requires splitting** this into two methods:

#### R-7.1 `updateSubscription()` — Edit a DRAFT in place

```java
/**
 * Edit an existing DRAFT subscription (AC-15, AC-16, ADR-18).
 * subscriptionProgramId is PRESERVED — not regenerated.
 * Only DRAFT status documents may be edited via this path.
 * Updates the same MongoDB document in place (no new document created).
 *
 * Name uniqueness: if name changes, check case-insensitive uniqueness via
 * repository.findActiveByOrgIdAndName(orgId, Pattern.quote(newName)).
 * Callers must pass Pattern.quote(name) — see R-4 above.
 *
 * Mutable fields: name, description, subscriptionType, programType,
 *   pointsExchangeRatio, syncWithLoyaltyTierOnDowngrade, duration, expiry,
 *   settings, tierConfig, benefits, reminders, customFields, groupTag.
 * Immutable fields (never changed): subscriptionProgramId, orgId, programId,
 *   status, parentId, version (managed by @Version), objectId, mysqlPartnerProgramId.
 *
 * @throws InvalidSubscriptionStateException if status != DRAFT
 * @throws SubscriptionNotFoundException if subscription not found
 * @throws SubscriptionNameConflictException if new name conflicts with another active subscription
 */
public SubscriptionProgram updateSubscription(Long orgId, String subscriptionProgramId,
                                               SubscriptionProgram request, String updatedBy) {
    SubscriptionProgram existing = getSubscription(orgId, subscriptionProgramId);

    if (!SubscriptionStatus.DRAFT.equals(existing.getStatus())) {
        throw new InvalidSubscriptionStateException("updateSubscription", existing.getStatus());
    }

    // Name change: check case-insensitive uniqueness if name changed
    if (!existing.getName().equalsIgnoreCase(request.getName())) {
        repository.findActiveByOrgIdAndName(orgId, java.util.regex.Pattern.quote(request.getName()))
            .ifPresent(conflict -> {
                if (!conflict.getObjectId().equals(existing.getObjectId())) {
                    throw new SubscriptionNameConflictException(request.getName(), orgId);
                }
            });
    }

    // Update mutable fields only; all immutable fields untouched
    existing.setName(request.getName());
    existing.setDescription(request.getDescription());
    existing.setSubscriptionType(request.getSubscriptionType());
    existing.setProgramType(request.getProgramType());
    existing.setPointsExchangeRatio(request.getPointsExchangeRatio());
    existing.setSyncWithLoyaltyTierOnDowngrade(request.getSyncWithLoyaltyTierOnDowngrade());
    existing.setDuration(request.getDuration());
    existing.setExpiry(request.getExpiry());
    existing.setSettings(request.getSettings());
    existing.setTierConfig(request.getTierConfig());
    existing.setBenefits(request.getBenefits() != null ? request.getBenefits() : List.of());
    existing.setReminders(request.getReminders() != null ? request.getReminders() : List.of());
    existing.setCustomFields(request.getCustomFields());
    existing.setGroupTag(request.getGroupTag());
    existing.setUpdatedBy(updatedBy);
    existing.setUpdatedAt(Instant.now()); // ADR-G-01: UTC

    // subscriptionProgramId, orgId, programId, status, parentId, version, objectId — NOT changed
    return repository.save(existing);
}
```

#### R-7.2 `editActiveSubscription()` — Fork new DRAFT from ACTIVE (edit-of-ACTIVE pattern)

```java
/**
 * Fork a new DRAFT from an ACTIVE subscription to begin an edit cycle (AC-17, ADR-01, ADR-18).
 *
 * ADR-18: subscriptionProgramId is COPIED from the ACTIVE parent — NOT a new UUID.
 * The ACTIVE subscription remains live and unchanged until the DRAFT is approved.
 * On approval: old ACTIVE → ARCHIVED, DRAFT → ACTIVE (via SubscriptionApprovalHandler.postApprove).
 *
 * parentId = ACTIVE document's objectId (MongoDB _id, for locating the old doc at approval time).
 * version = activeDoc.version + 1 (set explicitly before save).
 *
 * Name: copied from request (if provided) or from ACTIVE document.
 * All other config fields: from request (if provided) or from ACTIVE document (null-safe copy).
 *
 * @throws InvalidSubscriptionStateException if source is not ACTIVE
 * @throws SubscriptionNotFoundException if subscription not found
 * @throws IllegalStateException if a DRAFT already exists for this subscriptionProgramId
 */
public SubscriptionProgram editActiveSubscription(Long orgId, String subscriptionProgramId,
                                                   SubscriptionProgram request, String updatedBy) {
    SubscriptionProgram active = getSubscription(orgId, subscriptionProgramId);

    if (!SubscriptionStatus.ACTIVE.equals(active.getStatus())) {
        throw new InvalidSubscriptionStateException("editActiveSubscription", active.getStatus());
    }

    // Guard: no existing DRAFT for this subscription (parentId = active.objectId)
    repository.findDraftByParentIdAndOrgId(active.getObjectId(), orgId)
        .ifPresent(existing -> {
            throw new IllegalStateException(
                "A DRAFT already exists for subscription: " + subscriptionProgramId);
        });

    SubscriptionProgram draft = SubscriptionProgram.builder()
        // ADR-18: COPY subscriptionProgramId — do NOT generate new UUID
        .subscriptionProgramId(active.getSubscriptionProgramId())
        .orgId(orgId)
        .programId(active.getProgramId())
        .status(SubscriptionStatus.DRAFT)
        // parentId links to ACTIVE doc's MongoDB ObjectId (for postApprove archiving)
        .parentId(active.getObjectId())
        // version incremented (NOTE: @Version may override; Developer to verify NEW-OQ-04)
        // Fields from request if provided, else from ACTIVE document (null-safe)
        .name(request.getName() != null ? request.getName() : active.getName())
        .description(request.getDescription() != null ? request.getDescription() : active.getDescription())
        .subscriptionType(request.getSubscriptionType() != null ? request.getSubscriptionType() : active.getSubscriptionType())
        .programType(request.getProgramType() != null ? request.getProgramType() : active.getProgramType())
        .pointsExchangeRatio(request.getPointsExchangeRatio() != null ? request.getPointsExchangeRatio() : active.getPointsExchangeRatio())
        .syncWithLoyaltyTierOnDowngrade(request.getSyncWithLoyaltyTierOnDowngrade() != null ? request.getSyncWithLoyaltyTierOnDowngrade() : active.getSyncWithLoyaltyTierOnDowngrade())
        .duration(request.getDuration() != null ? request.getDuration() : active.getDuration())
        .expiry(request.getExpiry() != null ? request.getExpiry() : active.getExpiry())
        .settings(request.getSettings() != null ? request.getSettings() : active.getSettings())
        .tierConfig(request.getTierConfig() != null ? request.getTierConfig() : active.getTierConfig())
        .benefits(active.getBenefits() != null ? active.getBenefits() : List.of())
        .reminders(active.getReminders() != null ? active.getReminders() : List.of())
        .customFields(active.getCustomFields())
        .groupTag(active.getGroupTag())
        // mysqlPartnerProgramId NOT set — new DRAFT is unpublished until approved
        // objectId NOT set — MongoDB auto-generates new ObjectId on save
        .createdBy(updatedBy)
        .createdAt(Instant.now())
        .updatedBy(updatedBy)
        .updatedAt(Instant.now())
        .build();

    return repository.save(draft);
}
```

**Note**: The controller at `PUT /v3/subscriptions/{subscriptionProgramId}` must route to the correct method based on the current document status:
- Status = DRAFT → call `updateSubscription()`
- Status = ACTIVE → call `editActiveSubscription()`
- Status = PAUSED/PENDING_APPROVAL/ARCHIVED → throw `InvalidSubscriptionStateException`

This routing logic belongs in `SubscriptionFacade` as a unified `updateOrFork()` coordinator, or the controller can call `updateSubscription()` and let it check status and delegate to `editActiveSubscription()` internally. The Designer recommends routing in Facade:

```java
/**
 * Unified update entry point — routes to updateSubscription or editActiveSubscription
 * based on current document status. Called by SubscriptionController.updateSubscription().
 */
public SubscriptionProgram updateOrForkSubscription(Long orgId, String subscriptionProgramId,
                                                     SubscriptionProgram request, String updatedBy) {
    SubscriptionProgram existing = getSubscription(orgId, subscriptionProgramId);
    if (SubscriptionStatus.DRAFT.equals(existing.getStatus())) {
        return updateSubscription(orgId, subscriptionProgramId, request, updatedBy);
    } else if (SubscriptionStatus.ACTIVE.equals(existing.getStatus())) {
        return editActiveSubscription(orgId, subscriptionProgramId, request, updatedBy);
    } else {
        throw new InvalidSubscriptionStateException("update", existing.getStatus());
    }
}
```

#### Updated Interface Contracts Table — SubscriptionFacade

The following methods are now specified (additions to the original section 7 above):

| Method | Signature | Status (DRAFT) | Status (ACTIVE) | ADR |
|--------|-----------|----------------|-----------------|-----|
| `updateSubscription` | `(Long orgId, String subscriptionProgramId, SubscriptionProgram request, String updatedBy) → SubscriptionProgram` | Updates in place, preserves subscriptionProgramId | Throws InvalidSubscriptionStateException | ADR-18 |
| `editActiveSubscription` | `(Long orgId, String subscriptionProgramId, SubscriptionProgram request, String updatedBy) → SubscriptionProgram` | Throws InvalidSubscriptionStateException | Forks new DRAFT, copies subscriptionProgramId | ADR-18, ADR-01 |
| `updateOrForkSubscription` | `(Long orgId, String subscriptionProgramId, SubscriptionProgram request, String updatedBy) → SubscriptionProgram` | Routes to updateSubscription | Routes to editActiveSubscription | ADR-18 |

---

### R-8: subscriptionProgramId Lifecycle (ADR-18, KD-58)

This section documents the generate/copy/new-UUID lifecycle of `subscriptionProgramId` across all operations.

| Operation | subscriptionProgramId | Rationale |
|-----------|----------------------|-----------|
| **CREATE** (POST /v3/subscriptions) | **NEW UUID** generated once | First creation — `UUID.randomUUID().toString()` |
| **DRAFT edit** (PUT on DRAFT doc) | **COPIED** — same UUID, same document | In-place update via `updateSubscription()`; ID never changes |
| **Edit-of-ACTIVE** (PUT on ACTIVE doc) | **COPIED** from ACTIVE parent | `draft.subscriptionProgramId = active.getSubscriptionProgramId()` per ADR-18 |
| **DUPLICATE** (POST /duplicate) | **NEW UUID** | Explicitly a new independent program with new identity |
| **APPROVE** (DRAFT → ACTIVE) | **PRESERVED** — same UUID | The DRAFT document (with copied ID) is promoted to ACTIVE status |
| **REJECT** (PENDING_APPROVAL → DRAFT) | **PRESERVED** | Document status reverts, ID unchanged |
| **PAUSE / RESUME / ARCHIVE** | **PRESERVED** | Status-only changes; document not replaced |

**Evidence (C7)**: UnifiedPromotion pattern confirmed in `UnifiedPromotionFacade.java` lines 309, 744, 803 — `unifiedPromotionId` is copied from parent on edit-of-ACTIVE, never regenerated.

**Wrong comment in SubscriptionProgram.java lines 42-47**: The Javadoc said "Edits-of-ACTIVE produce a new UUID." This is **incorrect**. The correct Javadoc is in R-1.3 above. Developer must apply R-1.3.

---

### R-9: Updated SubscriptionRequest DTO — New Fields Required (GAP-1, GAP-2, GAP-5, GAP-7, ADR-08 through ADR-14)

The existing `SubscriptionRequest.java` in section 12 above has wrong constraints and is missing fields. The corrected DTO fields:

```java
// Name — corrected (ADR-08)
@NotBlank(message = "SUBSCRIPTION.NAME_REQUIRED")
@Size(max = 50, message = "SUBSCRIPTION.NAME_TOO_LONG")
@Pattern(regexp = "^[a-zA-Z0-9_\\-: ]*$", message = "SUBSCRIPTION.NAME_INVALID_CHARS")
private String name;

// Description — now required (ADR-09)
@NotBlank(message = "SUBSCRIPTION.DESCRIPTION_REQUIRED")
@Size(max = 100, message = "SUBSCRIPTION.DESCRIPTION_TOO_LONG")
@Pattern(regexp = "^[a-zA-Z0-9_\\-: ,.\\s]*$", message = "SUBSCRIPTION.DESCRIPTION_INVALID_CHARS")
private String description;

// programType — new required field (ADR-14)
@NotNull(message = "SUBSCRIPTION.PROGRAM_TYPE_REQUIRED")
private PartnerProgramType programType;

// pointsExchangeRatio — new required field (ADR-12)
@NotNull(message = "SUBSCRIPTION.POINTS_RATIO_REQUIRED")
@Positive(message = "SUBSCRIPTION.POINTS_RATIO_POSITIVE")
private Double pointsExchangeRatio;

// syncWithLoyaltyTierOnDowngrade — new required field (ADR-13)
@NotNull(message = "SUBSCRIPTION.SYNC_DOWNGRADE_REQUIRED")
private Boolean syncWithLoyaltyTierOnDowngrade;
```

**duration** — remove `@NotNull` at DTO level (it's conditional on programType); enforce in `validateForSubmission()` instead:
```java
// BEFORE: @NotNull @Valid
@Valid
private DurationDto duration;  // Required for SUPPLEMENTARY, forbidden for EXTERNAL
```

**Updated TierConfigDto** — add `tiers` and `loyaltySyncTiers`:
```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public static class TierConfigDto {
    private Integer linkedTierId;
    private Boolean tierDowngradeOnExit;
    private Integer downgradeTargetTierId;

    /** Tier list — required when subscriptionType=TIER_BASED (ADR-16) */
    @Valid
    private List<ProgramTierDto> tiers;

    /** Loyalty sync map — required when syncWithLoyaltyTierOnDowngrade=true (ADR-17) */
    private java.util.Map<String, String> loyaltySyncTiers;
}

@Data @Builder @NoArgsConstructor @AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public static class ProgramTierDto {
    @NotNull
    private Integer tierNumber;
    @NotBlank
    private String tierName;
}
```

**New import in SubscriptionRequest.java**:
```java
import com.capillary.intouchapiv3.unified.subscription.enums.PartnerProgramType;
```

---

### R-10: Updated SubscriptionResponse DTO — New Fields

Add the three new fields to `SubscriptionResponse.java` so the API returns the full model:

```java
private PartnerProgramType programType;            // ADR-14
private Double pointsExchangeRatio;                // ADR-12
private Boolean syncWithLoyaltyTierOnDowngrade;    // ADR-13
```

**Import**: `import com.capillary.intouchapiv3.unified.subscription.enums.PartnerProgramType;`

---

### R-11: Updated File Summary (additions to section "Summary of New Files")

The following are ADDITIONS to the existing Summary of New Files section:

#### intouch-api-v3 — New enum files (additions)
| File | Package | Notes |
|------|---------|-------|
| `PartnerProgramType.java` | `unified.subscription.enums` | New — ADR-14. Values: SUPPLEMENTARY, EXTERNAL |

#### intouch-api-v3 — Modified files (additions to existing 2-item list)
| File | Change | Notes |
|------|--------|-------|
| `SubscriptionProgram.java` | Fix `name` and `description` constraints; fix `subscriptionProgramId` Javadoc; add `pointsExchangeRatio`, `programType`, `syncWithLoyaltyTierOnDowngrade` fields; add `tiers` and `loyaltySyncTiers` to TierConfig; add `ProgramTier` inner class | R-1 above |
| `CycleType.java` | Remove `YEARS` value | R-3 above (ADR-10) |
| `SubscriptionProgramRepository.java` | Change `findActiveByOrgIdAndName` to `$regex/$options:'i'` | R-4 above (ADR-11) |
| `SubscriptionPublishService.java` | Rewrite `buildPartnerProgramInfo()`; remove `DEFAULT_POINTS_RATIO`, `MONTHS_PER_YEAR`, `convertCycle()`; wire all 15 Thrift fields | R-5 above |
| `SubscriptionApprovalHandler.java` | Add 6 new cross-field validations to `validateForSubmission()` | R-6 above |
| `SubscriptionFacade.java` | Add `updateSubscription()`, `editActiveSubscription()`, `updateOrForkSubscription()` | R-7 above (ADR-18) |
| `SubscriptionRequest.java` | Fix `name`/`description` constraints; add `programType`, `pointsExchangeRatio`, `syncWithLoyaltyTierOnDowngrade`; update `TierConfigDto`; add `ProgramTierDto` | R-9 above |
| `SubscriptionResponse.java` | Add `programType`, `pointsExchangeRatio`, `syncWithLoyaltyTierOnDowngrade` | R-10 above |

---

### R-12: preApprove() — Pattern.quote() Usage

The `SubscriptionApprovalHandler.preApprove()` method calls `repository.findActiveByOrgIdAndName()`. After the ADR-11 change (R-4), the query parameter must be regex-escaped:

```java
@Override
public void preApprove(SubscriptionProgram entity) {
    // MongoDB pre-check (ADR-11): reject if another non-ARCHIVED doc with same name exists
    // Pattern.quote() escapes regex metacharacters in the name (ADR-11 requirement)
    repository.findActiveByOrgIdAndName(
            entity.getOrgId(),
            java.util.regex.Pattern.quote(entity.getName()))
        .ifPresent(existing -> {
            if (!existing.getObjectId().equals(entity.getObjectId())) {
                throw new SubscriptionNameConflictException(
                        entity.getName(), entity.getOrgId());
            }
        });
    // Full Thrift getAllPartnerPrograms check (KD-40, RF-5) — still pending implementation
}
```

---

## Rework Summary (Phase 7 — 2026-04-15)

| Gap # | File(s) Changed | What Changed | ADR |
|-------|----------------|-------------|-----|
| GAP-1 | `SubscriptionProgram.java`, `SubscriptionRequest.java` | `name` constraint: max 50 + regex (was max 255, no regex) | ADR-08 |
| GAP-2 | `SubscriptionProgram.java`, `SubscriptionRequest.java` | `description` now required, max 100 + regex (was optional, max 1000) | ADR-09 |
| GAP-3 | `CycleType.java` | Remove `YEARS` enum value — only DAYS and MONTHS | ADR-10 |
| GAP-4 | `SubscriptionProgramRepository.java`, `SubscriptionFacade.java`, `SubscriptionApprovalHandler.java` | `findActiveByOrgIdAndName` uses `$regex/$options:'i'`; callers pass `Pattern.quote(name)` | ADR-11 |
| GAP-5 | `SubscriptionProgram.java`, `SubscriptionPublishService.java`, `SubscriptionRequest.java`, `SubscriptionResponse.java` | `pointsExchangeRatio` new required field; `DEFAULT_POINTS_RATIO` removed from service | ADR-12 |
| GAP-6 | `SubscriptionProgram.java`, `SubscriptionPublishService.java`, `SubscriptionRequest.java`, `SubscriptionResponse.java` | `syncWithLoyaltyTierOnDowngrade` new required direct field; derived logic removed | ADR-13 |
| GAP-7 | `SubscriptionProgram.java`, `SubscriptionPublishService.java`, `SubscriptionRequest.java`, `SubscriptionResponse.java`, `PartnerProgramType.java` (NEW) | `programType` new required field; hardcoded SUPPLEMENTARY removed | ADR-14 |
| GAP-8 | `SubscriptionApprovalHandler.java` | 6 new cross-field validations in `validateForSubmission()` | ADR-14, ADR-15, ADR-16, ADR-17, ADR-12 |
| GAP-9 | `SubscriptionProgram.java`, `SubscriptionPublishService.java`, `SubscriptionRequest.java` | `TierConfig.tiers` new field; `ProgramTier` new inner class; wired to Thrift field 5 | ADR-16 |
| GAP-10 | `SubscriptionProgram.java`, `SubscriptionPublishService.java`, `SubscriptionRequest.java` | `TierConfig.loyaltySyncTiers` new field; wired to Thrift field 11 | ADR-17 |
| GAP-11 / ADR-18 | `SubscriptionFacade.java` | `updateSubscription()` and `editActiveSubscription()` methods specified with correct ADR-18 ID lifecycle | ADR-18 |
| ADR-18 (comment) | `SubscriptionProgram.java` | `subscriptionProgramId` Javadoc corrected — was "Edits-of-ACTIVE produce new UUID" | ADR-18 |

---

## Rework 2 — PUBLISH_FAILED State + Pattern A Idempotency Key (2026-04-16)

> **Scope**: Two changes driven by SAGA reliability analysis:
> 1. **PUBLISH_FAILED status** — give the maker-checker a dedicated failure state instead of silently leaving entities in PENDING_APPROVAL when the Thrift publish fails. Enables operator visibility, retry, and send-back-to-draft.
> 2. **Pattern A — Stable idempotency key** — intouch-api-v3 passes a stable `serverReqId` per subscription approval; emf-parent caches `serverReqId → partnerProgramId` in Redis (ONE_HOUR). Handles timeout-after-commit split-brain: on retry the Thrift call returns the cached MySQL ID without re-inserting.

---

### R-13: `SubscriptionStatus` — Add `PUBLISH_FAILED`

**File**: `com/capillary/intouchapiv3/unified/subscription/enums/SubscriptionStatus.java`

```java
public enum SubscriptionStatus {
    DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, ARCHIVED,
    /**
     * Publish (Thrift/MySQL write) was attempted but failed.
     * Entity may be retried (→ PENDING_APPROVAL again or directly re-approved)
     * or rejected back to DRAFT by the operator.
     */
    PUBLISH_FAILED
}
```

**Discovered from**: `UnifiedPromotion.PromotionStatus.PUBLISH_FAILED` in `pointsengine-emf` — exact precedent for the same SAGA failure pattern.

---

### R-14: `ApprovableEntity` — Add `transitionToPublishFailed(String reason)`

**File**: `com/capillary/intouchapiv3/makechecker/ApprovableEntity.java`

Add one method:

```java
/**
 * Called by MakerCheckerService when publish() throws.
 * Implementations set status=PUBLISH_FAILED and store the failure reason.
 *
 * @param reason Error message / exception message from the failed publish attempt.
 *               Stored in entity.comments for operator visibility.
 */
void transitionToPublishFailed(String reason);
```

No other changes to the interface.

---

### R-15: `SubscriptionProgram` — Implement `transitionToPublishFailed()`

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java`

Add after `transitionToRejected()` (line 186):

```java
@Override
public void transitionToPublishFailed(String reason) {
    this.status = SubscriptionStatus.PUBLISH_FAILED;
    this.comments = reason;
}
```

No other changes to this class.

---

### R-16: `MakerCheckerService.approve()` — Persist PUBLISH_FAILED after `onPublishFailure`

**File**: `com/capillary/intouchapiv3/makechecker/MakerCheckerService.java`

Current catch block (lines 64–69):
```java
} catch (Exception e) {
    logger.error("SAGA publish failed. orgId={}, entityStatus={}",
            entity.getOrgId(), entity.getStatus(), e);
    handler.onPublishFailure(entity, e);
    throw e;
}
```

**Replace with**:
```java
} catch (Exception e) {
    logger.error("SAGA publish failed. orgId={}, entityStatus={}",
            entity.getOrgId(), entity.getStatus(), e);
    handler.onPublishFailure(entity, e);   // sets status=PUBLISH_FAILED
    try {
        save.save(entity);                 // best-effort: persist PUBLISH_FAILED to MongoDB
    } catch (Exception saveEx) {
        logger.error("Failed to persist PUBLISH_FAILED status. Entity may still appear PENDING_APPROVAL. orgId={}",
                entity.getOrgId(), saveEx);
    }
    throw e;                               // always rethrow original publish exception
}
```

**Why**: Without this save, the Thrift failure leaves the entity silently in PENDING_APPROVAL with no indication in MongoDB that the publish was attempted and failed. The save is `best-effort` (wrapped in try-catch) because the entity state persistence should not replace or mask the original publish exception.

---

### R-17: `SubscriptionApprovalHandler.onPublishFailure()` — Call `transitionToPublishFailed()`

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionApprovalHandler.java`

Current implementation:
```java
@Override
public void onPublishFailure(SubscriptionProgram entity, Exception e) {
    logger.error("SAGA publish failed. Entity remains PENDING_APPROVAL. orgId={}, subscriptionProgramId={}",
            entity.getOrgId(), entity.getSubscriptionProgramId(), e);
    // Intentionally do NOT change entity status — SAGA compensation = leave as-is
}
```

**Replace with**:
```java
@Override
public void onPublishFailure(SubscriptionProgram entity, Exception e) {
    logger.error("SAGA publish failed. Setting PUBLISH_FAILED. orgId={}, subscriptionProgramId={}",
            entity.getOrgId(), entity.getSubscriptionProgramId(), e);
    // Transition to PUBLISH_FAILED — MakerCheckerService will save (R-16)
    entity.transitionToPublishFailed(e.getMessage());
}
```

**Why**: The previous "intentionally leave as-is" comment was correct for a no-save world, but with R-16 the save IS happening. The handler must set the status so the save persists PUBLISH_FAILED instead of PENDING_APPROVAL.

---

### R-18: `SubscriptionFacade.handleApproval()` — Extend Guard to Allow `PUBLISH_FAILED`

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionFacade.java`

Current guard (line 324):
```java
if (!SubscriptionStatus.PENDING_APPROVAL.equals(entity.getStatus())) {
    throw new InvalidSubscriptionStateException("handleApproval", entity.getStatus());
}
```

**Replace with**:
```java
// Allow both PENDING_APPROVAL (normal flow) and PUBLISH_FAILED (retry/reject-to-draft)
if (!SubscriptionStatus.PENDING_APPROVAL.equals(entity.getStatus())
        && !SubscriptionStatus.PUBLISH_FAILED.equals(entity.getStatus())) {
    throw new InvalidSubscriptionStateException("handleApproval", entity.getStatus());
}
```

**Why**:
- `PUBLISH_FAILED → APPROVE`: operator retries the publish (e.g., after emf-parent recovers)
- `PUBLISH_FAILED → REJECT`: operator sends the subscription back to DRAFT so the maker can fix config

Both transitions start from `PUBLISH_FAILED` and must be allowed by the facade guard. The state machine logic (APPROVE → sets ACTIVE, REJECT → sets DRAFT) is unchanged — only the guard entry condition is widened.

---

### R-19: `SubscriptionPublishService.publishToMySQL()` — Stable `serverReqId` (Pattern A)

**File**: `com/capillary/intouchapiv3/unified/subscription/SubscriptionPublishService.java`

Current (line 74):
```java
String serverReqId = CapRequestIdUtil.getRequestId();
```

**Replace with**:
```java
// Pattern A: stable idempotency key — same subscriptionProgramId always gets the same key.
// On Thrift timeout + retry, emf-parent's Redis cache returns the previously-committed
// partnerProgramId instead of re-inserting (preventing duplicate MySQL rows).
String serverReqId = "sub-approve-" + subscription.getSubscriptionProgramId();
```

**Guard in `PointsEngineRulesThriftService.createOrUpdatePartnerProgram()`** (line 472–474):
```java
if (serverReqId == null || serverReqId.isEmpty()) {
    serverReqId = CapRequestIdUtil.getRequestId();
}
```
This guard already exists and is safe — it falls back to a random ID only if serverReqId is null/blank, which will never be the case for subscription approvals.

**No other changes to `SubscriptionPublishService`**.

---

### R-20: `PartnerProgramIdempotencyService` — New Service in emf-parent (Pattern A)

**File**: `com/capillary/shopbook/pointsengine/endpoint/impl/external/PartnerProgramIdempotencyService.java`  
**Module**: `emf-parent/pointsengine-emf`

**Discovered from**:
- `ExpiryExtensionConfigurationHelper.java` — uses `applicationCacheManager.get(key, CacheName.ONE_HOUR)` + `.put(key, value, CacheName.ONE_HOUR)` — exact pattern to follow
- `LimitsHelper.java` — uses `cacheManager = "redisCacheManager"` with `ApplicationCacheConfig.CacheName.ONE_DAY`

```java
package com.capillary.shopbook.pointsengine.endpoint.impl.external;

import com.capillary.shopbook.emf.cache.ApplicationCacheManager;
import com.capillary.shopbook.root.config.ApplicationCacheConfig.CacheName;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * Redis-backed idempotency cache for partner program create/update operations.
 *
 * Pattern A (SAGA reliability): each subscription approval generates a stable
 * serverReqId ("sub-approve-" + subscriptionProgramId). If the Thrift call commits
 * to MySQL but the response times out, intouch-api-v3 retries with the same serverReqId.
 * This service detects the retry and returns the previously-committed partnerProgramId
 * without re-executing the write — preventing duplicate partner_programs rows.
 *
 * TTL: ONE_HOUR. Sufficient for transient timeout recovery; does not survive
 * long-term outages (reconciliation job handles those separately).
 */
@Service
public class PartnerProgramIdempotencyService {

    private static final Logger logger = LoggerFactory.getLogger(PartnerProgramIdempotencyService.class);
    private static final String KEY_PREFIX = "pp-create-idempotency:";

    @Autowired
    private ApplicationCacheManager applicationCacheManager;

    /**
     * Returns the previously-committed partnerProgramId for this serverReqId, or null
     * if this is the first attempt.
     *
     * @param serverReqId Stable per-approval key (e.g., "sub-approve-{subscriptionProgramId}")
     * @return Cached MySQL partnerProgramId, or null on first attempt
     */
    public Integer getCachedPartnerProgramId(String serverReqId) {
        return (Integer) applicationCacheManager.get(KEY_PREFIX + serverReqId, CacheName.ONE_HOUR);
    }

    /**
     * Stores the committed partnerProgramId for this serverReqId (ONE_HOUR TTL).
     * Called immediately after a successful MySQL write.
     *
     * @param serverReqId      Stable per-approval key
     * @param partnerProgramId The MySQL ID that was committed
     */
    public void cachePartnerProgramId(String serverReqId, int partnerProgramId) {
        logger.info("Caching idempotency result. serverReqId={}, partnerProgramId={}", serverReqId, partnerProgramId);
        applicationCacheManager.put(KEY_PREFIX + serverReqId, partnerProgramId, CacheName.ONE_HOUR);
    }
}
```

**Annotations**: `@Service` — consistent with `ExpiryExtensionConfigurationHelper` using `@Component`; `@Service` is semantically correct for a service class.

**Maven status**: `ApplicationCacheManager` and `ApplicationCacheConfig.CacheName` already on the classpath in `pointsengine-emf` (verified: `ExpiryExtensionConfigurationHelper` in same module uses both). No new dependencies.

**Imports**:
- `com.capillary.shopbook.emf.cache.ApplicationCacheManager` (from `emf` module — already available)
- `com.capillary.shopbook.root.config.ApplicationCacheConfig.CacheName` (from `emf` root — already available)

---

### R-21: `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` — Idempotency Check (Pattern A)

**File**: `com/capillary/shopbook/pointsengine/endpoint/impl/external/PointsEngineRuleConfigThriftImpl.java`  
**Module**: `emf-parent/pointsengine-emf`

Add one `@Autowired` field (alongside existing `@Autowired` fields at lines 126–184):

```java
@Autowired
private PartnerProgramIdempotencyService partnerProgramIdempotencyService;
```

Modify `createOrUpdatePartnerProgram()` method body (lines 252–281).

**Before** (current implementation):
```java
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public PartnerProgramInfo createOrUpdatePartnerProgram(PartnerProgramInfo partnerProgramInfo, int programId,
                                                       int orgId, int lastModifiedBy, long lastModifiedOn, String serverReqId)
        throws PointsEngineRuleServiceException, TException {
    try {
        List<PartnerProgramSlab> partnerProgramSlabs = m_pointsEngineRuleEditor.getPartnerProgramSlabs(orgId,
                programId, partnerProgramInfo.getPartnerProgramId());
        com.capillary.shopbook.points.entity.PartnerProgram partnerProgramEntity = getPartnerProgramEntity(
                partnerProgramInfo, orgId, programId, partnerProgramSlabs);
        PartnerProgram oldPartnerProgram = m_pointsEngineRuleEditor.getPartnerProgram(
                partnerProgramInfo.getPartnerProgramId(), orgId);
        partnerProgramEntity = m_pointsEngineRuleEditor.createOrUpdatePartnerProgram(orgId, partnerProgramEntity,
                oldPartnerProgram);

        boolean updatedViaNewUI = partnerProgramInfo.isSetUpdatedViaNewUI()
                && partnerProgramInfo.isUpdatedViaNewUI();
        logger.info("updated via new UI: {}", updatedViaNewUI);
        m_pointsEngineRuleEditor.logAuditTrails(oldPartnerProgram, partnerProgramEntity, lastModifiedBy,
                updatedViaNewUI);

        partnerProgramInfo.setPartnerProgramId(partnerProgramEntity.getId());

        logger.info("Returning partner program with id: {}", partnerProgramInfo.getPartnerProgramId());
        return partnerProgramInfo;
    } catch (Exception ex) {
        logger.error("Error in creating/updating partner program for program: " + programId, ex);
        throw new PointsEngineRuleServiceException(ex.getMessage());
    } finally {
        newRelicUtils.pushRequestContextStats();
    }
}
```

**After** (with Pattern A idempotency check added at top of try block):
```java
@Override
@Trace(dispatcher = true)
@MDCData(orgId = "#orgId", requestId = "#serverReqId")
public PartnerProgramInfo createOrUpdatePartnerProgram(PartnerProgramInfo partnerProgramInfo, int programId,
                                                       int orgId, int lastModifiedBy, long lastModifiedOn, String serverReqId)
        throws PointsEngineRuleServiceException, TException {
    try {
        // Pattern A: idempotency check — skip re-execution if this serverReqId was already committed
        if (serverReqId != null && !serverReqId.isEmpty()) {
            Integer cachedId = partnerProgramIdempotencyService.getCachedPartnerProgramId(serverReqId);
            if (cachedId != null) {
                logger.info("Idempotent createOrUpdatePartnerProgram: returning cached result. serverReqId={}, cachedId={}",
                        serverReqId, cachedId);
                partnerProgramInfo.setPartnerProgramId(cachedId);
                return partnerProgramInfo;
            }
        }

        List<PartnerProgramSlab> partnerProgramSlabs = m_pointsEngineRuleEditor.getPartnerProgramSlabs(orgId,
                programId, partnerProgramInfo.getPartnerProgramId());
        com.capillary.shopbook.points.entity.PartnerProgram partnerProgramEntity = getPartnerProgramEntity(
                partnerProgramInfo, orgId, programId, partnerProgramSlabs);
        PartnerProgram oldPartnerProgram = m_pointsEngineRuleEditor.getPartnerProgram(
                partnerProgramInfo.getPartnerProgramId(), orgId);
        partnerProgramEntity = m_pointsEngineRuleEditor.createOrUpdatePartnerProgram(orgId, partnerProgramEntity,
                oldPartnerProgram);

        boolean updatedViaNewUI = partnerProgramInfo.isSetUpdatedViaNewUI()
                && partnerProgramInfo.isUpdatedViaNewUI();
        logger.info("updated via new UI: {}", updatedViaNewUI);
        m_pointsEngineRuleEditor.logAuditTrails(oldPartnerProgram, partnerProgramEntity, lastModifiedBy,
                updatedViaNewUI);

        partnerProgramInfo.setPartnerProgramId(partnerProgramEntity.getId());

        // Pattern A: cache the committed ID so retries can skip re-execution
        if (serverReqId != null && !serverReqId.isEmpty()) {
            partnerProgramIdempotencyService.cachePartnerProgramId(serverReqId, partnerProgramEntity.getId());
        }

        logger.info("Returning partner program with id: {}", partnerProgramInfo.getPartnerProgramId());
        return partnerProgramInfo;
    } catch (Exception ex) {
        logger.error("Error in creating/updating partner program for program: " + programId, ex);
        throw new PointsEngineRuleServiceException(ex.getMessage());
    } finally {
        newRelicUtils.pushRequestContextStats();
    }
}
```

**Minimal change principle**: Only 8 lines added — idempotency check at method entry and cache write after successful commit. All existing logic is preserved unchanged.

---

## Rework 2 Summary (2026-04-16)

| Change # | File(s) | What Changed | Why |
|----------|---------|-------------|-----|
| R-13 | `SubscriptionStatus.java` | Add `PUBLISH_FAILED` enum value | Explicit failure state for SAGA publish errors |
| R-14 | `ApprovableEntity.java` | Add `transitionToPublishFailed(String reason)` | Interface contract for generic failure transition |
| R-15 | `SubscriptionProgram.java` | Implement `transitionToPublishFailed()` | Set status=PUBLISH_FAILED + store error in comments |
| R-16 | `MakerCheckerService.java` | `approve()` catch block: save entity after `onPublishFailure` (best-effort) | Persist PUBLISH_FAILED to MongoDB before rethrowing |
| R-17 | `SubscriptionApprovalHandler.java` | `onPublishFailure()`: call `entity.transitionToPublishFailed(e.getMessage())` | Set the failure status (MakerCheckerService will save) |
| R-18 | `SubscriptionFacade.java` | `handleApproval()` guard: also allow `PUBLISH_FAILED` as starting state | Enable retry (approve) and send-back-to-draft (reject) from failure state |
| R-19 | `SubscriptionPublishService.java` | Stable `serverReqId = "sub-approve-" + subscriptionProgramId` | Pattern A: same key on retry → emf-parent Redis cache hit → no double-insert |
| R-20 | `PartnerProgramIdempotencyService.java` (NEW, emf-parent) | New `@Service` wrapping `applicationCacheManager.get/put` for idempotency | Isolated, testable idempotency logic; follows `ExpiryExtensionConfigurationHelper` pattern |
| R-21 | `PointsEngineRuleConfigThriftImpl.java` (emf-parent) | Add idempotency check at `createOrUpdatePartnerProgram()` entry + cache write after commit | Pattern A SAGA completion — prevents double-insert on timeout-after-commit retries |
