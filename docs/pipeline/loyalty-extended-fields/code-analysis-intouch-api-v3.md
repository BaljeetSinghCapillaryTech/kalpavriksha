# Code Analysis: Loyalty Extended Fields CRUD Feature (CAP-183124)
## intouch-api-v3 Codebase Exploration

---

## Key Architectural Insights

### 1. **Unified Subscription Architecture**
- **Location**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/`
- **Pattern**: Mirrors UnifiedPromotion (Pattern C design) with clear separation of concerns:
  - **Controller** → handles HTTP binding + auth context extraction
  - **Facade** → business logic + repository coordination
  - **ErrorAdvice** → exception-to-HTTP mapping via `@ControllerAdvice`
  - **Repository** → MongoDB persistence with status-qualified queries
  - **PublishService** → SAGA publish to EMF via Thrift
  - **ApprovalHandler** → MakerChecker approval workflow

### 2. **Auth Context Flow**
- All controllers receive `AbstractBaseAuthenticationToken token` (Spring Security parameter injection)
- Extract `IntouchUser user = token.getIntouchUser()` to obtain:
  - `orgId: Long` — multi-tenancy key (extracted from auth, never from request body)
  - `refId: Long` — loyalty program ID (user.getRefId())
  - `entityId: Long` — Capillary system user ID (for audit trail)
  - `tillName: String` — username for audit
- **orgId** sourcing: Always from auth token, NEVER from request body or path params

### 3. **Thrift Integration Pattern**
- **Service Class**: `PointsEngineRulesThriftService` (Spring @Service)
- **Client Initialization**: `RPCService.rpcClient(PointsEngineRuleService.Iface.class, "emf-thrift-service", 9199, 60000)`
  - Host: "emf-thrift-service" (service discovery via hostname)
  - Port: 9199
  - Timeout: 60000ms
- **Exception Handling**: Thrift exceptions wrapped in `EMFThriftException` with request ID tracking
- **Request ID**: Generated via `CapRequestIdUtil.getRequestId()` — enables idempotency & tracing

### 4. **MongoDB-First Pattern with Delayed Thrift**
- **Write Path**: All DRAFT/in-flight operations → MongoDB only (no Thrift)
- **Publish Path**: APPROVE transitions trigger SAGA:
  1. Convert MongoDB entity → Thrift PartnerProgramInfo
  2. Call Thrift via PointsEngineRulesThriftService.createOrUpdatePartnerProgram()
  3. Capture returned MySQL partnerProgramId
  4. Update MongoDB with partnerProgramId on success
  5. On Thrift failure: set status=PUBLISH_FAILED, allow retry via /approve endpoint
- **Status-Qualified Queries**: DRAFT-first pattern (edit fork in-flight) → fallback to ACTIVE/PAUSED

### 5. **State Machine with Approval Workflow**
- **SubscriptionStatus enum**: DRAFT → PENDING_APPROVAL → ACTIVE (or REJECTED → DRAFT, or PUBLISH_FAILED)
  - ARCHIVED = terminal state
  - PAUSED = active but inactive (via isActive=false in Thrift)
- **MakerChecker Integration**: submitForApproval() → handleApproval(APPROVE|REJECT) 
- **Edit Window**: During DRAFT existence, ACTIVE + DRAFT fork coexist (Gap 2, R-27)

---

## Package Structure

```
com.capillary.intouchapiv3.unified.subscription/
├── SubscriptionController.java              (@RestController, /v3/subscriptions)
│   ├── POST   /v3/subscriptions              → createSubscription()
│   ├── GET    /v3/subscriptions              → listSubscriptions() [paginated]
│   ├── GET    /v3/subscriptions/{id}         → getSubscription()
│   ├── PUT    /v3/subscriptions/{id}         → updateSubscription()
│   ├── POST   /v3/subscriptions/{id}/duplicate → duplicateSubscription()
│   ├── PATCH  /v3/subscriptions/{id}/status  → changeStatus()
│   ├── POST   /v3/subscriptions/{id}/benefits/{benefitId}   → linkBenefit()
│   └── DELETE /v3/subscriptions/{id}/benefits/{benefitId}   → delinkBenefit()
├── SubscriptionReviewController.java        (@RestController, approval workflow)
│   ├── POST   /v3/subscriptions/{id}/approve → reviewSubscription() [APPROVE|REJECT]
│   └── GET    /v3/subscriptions/approvals    → listPendingApprovals()
├── SubscriptionFacade.java                  (@Component, business logic + repos)
│   ├── createSubscription()
│   ├── getSubscription()(overloaded with status)
│   ├── updateSubscription()
│   ├── editActiveSubscription() [forks ACTIVE to DRAFT]
│   ├── duplicateSubscription()
│   ├── submitForApproval() → MakerCheckerService
│   ├── handleApproval(APPROVE|REJECT)
│   ├── pauseSubscription(), resumeSubscription(), archiveSubscription()
│   ├── linkBenefit(), delinkBenefit(), getBenefits()
│   ├── listPendingApprovals()
│   ├── changeStatus() [dispatcher]
│   ├── getHeaderStats()
│   └── [resolveMutableSubscription() — DRAFT-first for benefit ops]
├── SubscriptionProgram.java                 (@Document, MongoDB entity)
│   ├── objectId: String (@Id)
│   ├── subscriptionProgramId: String        (UUID, business key)
│   ├── orgId: Long                          (multi-tenancy)
│   ├── programId: Integer                   (loyalty_program_id from EMF)
│   ├── status: SubscriptionStatus
│   ├── parentId: String                     (ACTIVE ObjectId if DRAFT fork)
│   ├── partnerProgramId: Integer            (MySQL partner_programs.id, set on APPROVE)
│   ├── lastModifiedByEntityId: @Transient   (Capillary entity ID for Thrift audit)
│   ├── [name, description, subscriptionType, duration, expiry, settings, tierConfig]
│   ├── benefits: List<BenefitRef>
│   ├── reminders: List<Reminder>            (MongoDB-only, not written via Thrift)
│   ├── extendedFields: List<ExtendedField>  (MongoDB-only, ADR-19)
│   ├── programType: PartnerProgramType      (SUPPLEMENTARY|EXTERNAL)
│   ├── pointsExchangeRatio: Double          (user-provided, ADR-12)
│   ├── syncWithLoyaltyTierOnDowngrade: Boolean (ADR-13)
│   ├── [createdBy, createdAt, updatedBy, updatedAt]
│   ├── [version: Long — optimistic lock]
│   ├── [workflowMetadata: WorkflowMetadata] (submittedBy, submittedAt, reviewedBy, reviewedAt)
│   └── ⚠️ ExtendedField.type: ExtendedFieldType (SCHEDULED FOR DELETION per session memory)
├── SubscriptionProgram.ExtendedField        (nested static class)
│   ├── type: ExtendedFieldType              (CUSTOMER_EXTENDED_FIELD | TXN_EXTENDED_FIELD)
│   ├── key: String                          (currently String, REPLACE with id: Long)
│   └── value: String                        (stored as string, resolved at eval time)
├── SubscriptionErrorAdvice.java             (@ControllerAdvice scoped to SubscriptionController)
│   ├── handleNotFound(SubscriptionNotFoundException) → 404
│   ├── handleInvalidState(InvalidSubscriptionStateException) → 422
│   ├── handleNameConflict(SubscriptionNameConflictException) → 409
│   └── handlePublishFailure(EMFThriftException) → 500 [with PUBLISH_FAILED state msg]
├── SubscriptionPublishService.java          (@Service, SAGA publish)
│   ├── publishToMySQL(SubscriptionProgram, orgId, programId) → int mysqlId
│   │   ├── Idempotency check: if partnerProgramId != null && parentId == null → skip
│   │   ├── Build PartnerProgramInfo (field wiring: pointsExchangeRatio, programType, tierConfig, etc.)
│   │   ├── thriftService.createOrUpdatePartnerProgram(info, programId, orgId.intValue(), lastModifiedBy, lastModifiedOn, serverReqId)
│   │   └── Return PublishResult with externalId (mysqlId)
│   ├── publishIsActive(SubscriptionProgram, orgId, programId, isActive) [PAUSE/RESUME/ARCHIVE]
│   │   ├── Guard: partnerProgramId must be set
│   │   ├── Set info.isActive(boolean)
│   │   └── thriftService.createOrUpdatePartnerProgram(..., isActive flag)
│   └── buildPartnerProgramInfo(SubscriptionProgram, orgId) [private, ADR-12 through ADR-17 field wiring]
├── SubscriptionApprovalHandler.java         (@Component, MakerChecker flow)
│   └── Implements ApprovableEntityHandler<SubscriptionProgram>
├── SubscriptionProgramRepository.java       (Spring Data MongoDB)
│   ├── Custom methods for status-qualified queries:
│   │   ├── findBySubscriptionProgramIdAndOrgIdAndStatus(id, orgId, status) → Optional<SubscriptionProgram>
│   │   ├── findBySubscriptionProgramIdAndOrgIdAndStatusIn(id, orgId, List<status>) → Optional<SubscriptionProgram>
│   │   ├── findByOrgIdAndStatus(orgId, status, Pageable) → Page<SubscriptionProgram>
│   │   ├── findByOrgIdAndStatusIn(orgId, List<status>, Pageable) → Page<SubscriptionProgram>
│   │   ├── findDraftByParentIdAndOrgId(parentId, orgId) → Optional<SubscriptionProgram> [guard against duplicate forks]
│   │   ├── findActiveByOrgIdAndName(orgId, Pattern.quote(name)) → Optional<SubscriptionProgram>
│   │   ├── findActivePartnerProgramIdsByOrgId(orgId) → List<SubscriptionProgram>
│   │   ├── findPendingApprovalByOrgIdAndProgramId(orgId, programId, Pageable) → Page<SubscriptionProgram>
│   │   └── [implicit save(), findById() via Spring Data]
├── enums/
│   ├── SubscriptionStatus                   (DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, PUBLISH_FAILED, ARCHIVED)
│   ├── SubscriptionType                     (FLAT, TIER_BASED)
│   ├── PartnerProgramType                   (SUPPLEMENTARY, EXTERNAL)
│   ├── CycleType                            (WEEKS, MONTHS, YEARS)
│   ├── ReminderChannel                      (SMS, EMAIL, PUSH)
│   ├── MigrateOnExpiry                      (enum for expiry actions)
│   ├── SubscriptionAction                   (enum for state transitions)
│   └── ExtendedFieldType                    (CUSTOMER_EXTENDED_FIELD, TXN_EXTENDED_FIELD) [SCHEDULED FOR DELETION]
├── Exceptions
│   ├── SubscriptionNotFoundException        (extends RuntimeException)
│   ├── InvalidSubscriptionStateException    (extends RuntimeException)
│   └── SubscriptionNameConflictException    (extends RuntimeException)
└── [test/ — SubscriptionRework4FacadeTest.java, SubscriptionFieldValidationTest.java, etc.]
```

---

## Controller Pattern

### **SubscriptionController Wiring**

```java
@RestController
@RequestMapping("/v3/subscriptions")
public class SubscriptionController {

    @Autowired
    private SubscriptionFacade facade;

    // HTTP Parameter Injection Pattern:
    // - RequestBody: SubscriptionProgram (validated via @Valid)
    // - PathVariable: subscriptionProgramId (business key)
    // - RequestParam: status (defaultValue="ACTIVE"), page, size, etc.
    // - AbstractBaseAuthenticationToken token: Spring Security injects auth context

    @PostMapping
    public ResponseEntity<?> createSubscription(
            @RequestBody SubscriptionProgram request,          // from JSON body
            AbstractBaseAuthenticationToken token) {           // Spring Security injection
        IntouchUser user = token.getIntouchUser();
        // orgId sourced from auth token, NOT from request body
        facade.createSubscription(request, user.getOrgId(), request.getProgramId(), user.getTillName());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/{subscriptionProgramId}")
    public ResponseEntity<?> getSubscription(
            @PathVariable String subscriptionProgramId,        // from URL path
            @RequestParam(defaultValue = "ACTIVE") String status,  // query param with default
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        SubscriptionStatus statusEnum = SubscriptionStatus.valueOf(status);
        // Status-qualified fetch (Gap 2, R-25): prevents non-deterministic selection
        // when ACTIVE + DRAFT fork coexist during edit window
        return ResponseEntity.ok(facade.getSubscription(user.getOrgId(), subscriptionProgramId, statusEnum));
    }

    // Key insights:
    // 1. orgId never appears in @RequestParam or @PathVariable — always from token
    // 2. Status defaults to "ACTIVE" at controller level → passed to facade
    // 3. All operations are program-scoped (programId inferred from SubscriptionProgram.programId in request, or from token.getRefId())
    // 4. Benefit operations use DRAFT-first pattern: resolveMutableSubscription() in facade
}
```

### **SubscriptionReviewController Wiring**

```java
@RestController
@RequestMapping("/v3/subscriptions")
public class SubscriptionReviewController {

    @PostMapping("/{subscriptionProgramId}/approve")
    public ResponseEntity<?> reviewSubscription(
            @PathVariable String subscriptionProgramId,
            @RequestBody Map<String, String> reviewRequest,   // {"approvalStatus": "APPROVE"|"REJECT", "comment": "..."}
            AbstractBaseAuthenticationToken token) throws Exception {
        String action = reviewRequest.get("approvalStatus");  // APPROVE or REJECT
        String comment = reviewRequest.getOrDefault("comment", null);
        // facade.handleApproval() triggers SAGA if action=APPROVE (Thrift publish)
        return ResponseEntity.ok(facade.handleApproval(
                user.getOrgId(), subscriptionProgramId, action, comment, user.getTillName(),
                (int) user.getEntityId()));  // entityId passed for Thrift audit
    }

    @GetMapping("/approvals")
    public ResponseEntity<?> listPendingApprovals(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            AbstractBaseAuthenticationToken token) {
        // Returns PENDING_APPROVAL subscriptions for the reviewer's queue
        return ResponseEntity.ok(facade.listPendingApprovals(
                user.getOrgId(), (int) user.getRefId(), page, size));
    }
}
```

### **Pattern: OrgId from Auth, Program_ID from Request**

In createSubscription:
```
request.getProgramId()  → comes from JSON body (SubscriptionProgram.programId field)
user.getOrgId()         → comes from auth token (never from body/path)
```

In listPendingApprovals:
```
user.getOrgId()         → from auth token
user.getRefId()         → from auth token, used as programId parameter
```

---

## Thrift Call Pattern

### **Service: PointsEngineRulesThriftService**

**Location**: `/src/main/java/com/capillary/intouchapiv3/services/thrift/PointsEngineRulesThriftService.java`

```java
@Service
@Loggable
@Profile("!test")
public class PointsEngineRulesThriftService {

    private Class<PointsEngineRuleService.Iface> getIfaceClass() {
        return PointsEngineRuleService.Iface.class;
    }

    // Client initialization pattern:
    private PointsEngineRuleService.Iface getClient() throws Exception {
        return RPCService.rpcClient(
            getIfaceClass(),           // Interface class (PointsEngineRuleService.Iface)
            "emf-thrift-service",      // Service name (DNS/service discovery)
            9199,                      // Port
            60000                      // Timeout in ms (60 seconds)
        );
    }

    // Typical pattern for calling Thrift:
    public PartnerProgramInfo getPromotion(long orgId, int promotionId, int programId) {
        String serverReqId = CapRequestIdUtil.getRequestId();  // Generate trace ID
        try {
            logger.info("Fetching promotion from EMF. orgId={}, programId={}, promotionId={}", 
                orgId, programId, promotionId);
            // Call Thrift method via client
            return getClient().getPromotion(
                promotionId,              // First param
                programId,                // Second param
                (int) orgId,              // Cast Long to int for Thrift
                serverReqId               // Request ID for idempotency/tracing
            );
        } catch (Exception e) {
            logger.error("Error fetching promotion from EMF. orgId={}, ..., reqId={}", 
                orgId, ..., serverReqId, e);
            throw new EMFThriftException("Error in fetching...");  // Wrap exception
        }
    }
}
```

### **Usage in SubscriptionPublishService: createOrUpdatePartnerProgram()**

```java
public class SubscriptionPublishService {

    @Autowired
    private PointsEngineRulesThriftService thriftService;

    public PublishResult publishToMySQL(SubscriptionProgram subscription, Long orgId, Integer programId) 
            throws Exception {
        
        // Step 1: Check idempotency (RF-6)
        if (subscription.getPartnerProgramId() != null && subscription.getParentId() == null) {
            // Already published (first-time retry scenario) — skip Thrift
            return PublishResult.builder()
                .externalId(subscription.getPartnerProgramId())
                .idempotent(true)
                .build();
        }

        // Step 2: Build Thrift struct
        PartnerProgramInfo info = buildPartnerProgramInfo(subscription, orgId);

        // Step 3: Prepare audit context
        String serverReqId = "sub-approve-" + subscription.getSubscriptionProgramId();
        long lastModifiedOn = System.currentTimeMillis();
        int lastModifiedBy = subscription.getLastModifiedByEntityId() != null
            ? subscription.getLastModifiedByEntityId() : 0;

        // Step 4: Call Thrift
        logger.info("Publishing subscription to MySQL via Thrift. orgId={}, subscriptionProgramId={}, "
            + "lastModifiedBy={}, serverReqId={}", 
            orgId, subscription.getSubscriptionProgramId(), lastModifiedBy, serverReqId);

        int mysqlId = thriftService.createOrUpdatePartnerProgram(
            info,                          // PartnerProgramInfo struct
            programId,                     // loyalty_program_id (int)
            orgId.intValue(),              // org_id cast to int
            lastModifiedBy,                // Capillary entity ID (for audit trail)
            lastModifiedOn,                // Timestamp in ms
            serverReqId                    // Unique idempotency key
        );

        // Step 5: Return result (mysqlId captured)
        logger.info("Subscription published to MySQL. orgId={}, subscriptionProgramId={}, mysqlId={}",
            orgId, subscription.getSubscriptionProgramId(), mysqlId);

        return PublishResult.builder()
            .externalId(mysqlId)
            .idempotent(false)
            .build();
    }
}
```

### **PartnerProgramInfo Field Wiring (ADR-12 through ADR-17)**

```java
PartnerProgramInfo buildPartnerProgramInfo(SubscriptionProgram subscription, Long orgId) {
    PartnerProgramInfo info = new PartnerProgramInfo();
    
    // ... set basic fields (name, description, etc.)
    
    // Field 5: partnerProgramTiers (ADR-16, KD-55)
    if (subscription.getTierConfig() != null && subscription.getTierConfig().getTiers() != null) {
        List<PartnerProgramTier> tiers = subscription.getTierConfig().getTiers()
            .stream()
            .map(t -> {
                PartnerProgramTier tier = new PartnerProgramTier();
                tier.setTierNumber(t.getTierNumber());
                tier.setTierName(t.getTierName());
                return tier;
            })
            .collect(Collectors.toList());
        info.setPartnerProgramTiers(tiers);
    }

    // Field 6: pointsRatio (ADR-12, KD-51) — from entity, not hardcoded
    if (subscription.getPointsExchangeRatio() != null) {
        info.setPointsRatio(subscription.getPointsExchangeRatio());
    }

    // Field 8: partnerProgramType (ADR-14, KD-53) — SUPPLEMENTARY or EXTERNAL
    if (subscription.getProgramType() != null) {
        info.setPartnerProgramType(
            subscription.getProgramType().name()
        );
    }

    // Field 9: membershipCycle (ADR-14) — only for SUPPLEMENTARY
    if (PartnerProgramType.SUPPLEMENTARY.equals(subscription.getProgramType()) 
        && subscription.getDuration() != null) {
        PartnerProgramMembershipCycle cycle = new PartnerProgramMembershipCycle();
        cycle.setCycleType(PartnerProgramCycleType.valueOf(subscription.getDuration().getCycleType().name()));
        cycle.setCycleValue(subscription.getDuration().getCycleValue());
        info.setPartnerProgramMembershipCycle(cycle);
    }

    // Field 10: isSyncWithLoyaltyTierOnDowngrade (ADR-13, KD-52)
    if (subscription.getSyncWithLoyaltyTierOnDowngrade() != null) {
        info.setIsSyncWithLoyaltyTierOnDowngrade(subscription.getSyncWithLoyaltyTierOnDowngrade());
    }

    // Field 11: loyaltySyncTiers (ADR-17, KD-56) — only when sync=true
    if (subscription.getSyncWithLoyaltyTierOnDowngrade() != null 
        && subscription.getSyncWithLoyaltyTierOnDowngrade() 
        && subscription.getTierConfig() != null 
        && subscription.getTierConfig().getLoyaltySyncTiers() != null) {
        info.setLoyaltySyncTiers(subscription.getTierConfig().getLoyaltySyncTiers());
    }

    // ... other fields
    
    return info;
}
```

### **Exception Handling for Thrift Calls**

```java
@ResponseBody
@ExceptionHandler(EMFThriftException.class)
public ResponseEntity<ResponseWrapper<String>> handlePublishFailure(EMFThriftException e) {
    log.error("Subscription SAGA publish failed — entity set to PUBLISH_FAILED. Retry via approve endpoint. cause={}",
        e.getMessage());
    return body(INTERNAL_SERVER_ERROR,
        "Publish failed — subscription moved to PUBLISH_FAILED status. " +
        "Retry the approve action once the downstream service recovers.");
}
```

---

## Auth / OrgId Sourcing

### **Authentication Flow**

1. **Entry Point**: Spring Security filter chain injects `AbstractBaseAuthenticationToken token`
2. **Token Types**: 
   - `BasicAndKeyAuthenticationToken` (API key + basic auth)
   - `KeyOnlyAuthenticationToken` (API key only)
   - `IntegrationsClientAuthenticationToken` (service-to-service)

3. **Extraction Pattern** (in every controller):
```java
IntouchUser user = token.getIntouchUser();

// Accessor methods (from IntouchUser):
long orgId = user.getOrgId();                   // Multi-tenancy key
long refId = user.getRefId();                   // Loyalty program ID
long entityId = user.getEntityId();             // Capillary user entity ID
String tillName = user.getTillName();           // Username for audit
long entityOrgId = user.getEntityOrgId();       // Entity org mapping
String entityType = user.getEntityType();       // Type of entity
```

### **OrgId Location Rules**

| Source | Rule |
|--------|------|
| **Auth Token (ALWAYS)** | `user.getOrgId()` — extracted from `IntouchUser` |
| **Request Body** | NO — orgId never in request JSON |
| **Path Parameter** | NO — orgId never in `/v3/subscriptions/{id}` |
| **Query Parameter** | NO — orgId never in `?org_id=123` |
| **Implicit Scope** | All repository queries: `findByOrgIdAndStatus()` etc. (G-07) |

### **Example: createSubscription()**

```java
@PostMapping
public ResponseEntity<?> createSubscription(
        @RequestBody SubscriptionProgram request,    // JSON: {"programId": 5, "name": "...", ...}
        AbstractBaseAuthenticationToken token) {     // Auth context (orgId=100)

    IntouchUser user = token.getIntouchUser();  // orgId=100 from token
    
    // request.getProgramId() may be present in JSON, but programId is STORED in entity
    // orgId ALWAYS comes from user.getOrgId() — NEVER from request
    SubscriptionProgram created = facade.createSubscription(
        request, 
        user.getOrgId(),              // orgId=100 (from auth token)
        request.getProgramId(),       // programId (from request body)
        user.getTillName()            // username from auth
    );
    
    return ResponseEntity.status(HttpStatus.CREATED).body(created);
}
```

### **IntouchUser Structure**

**File**: `/src/main/java/com/capillary/intouchapiv3/auth/IntouchUser.java`

```java
@Builder
@Getter
@ToString
public class IntouchUser implements Principal, Serializable {
    private long entityId;              // Capillary user entity ID (for audit)
    private long entityOrgId;           // Entity org mapping
    private String entityType;          // Entity type discriminator
    private long orgId;                 // Multi-tenancy key (ALWAYS used for scoping)
    private String tillName;            // Username
    private String accessToken;         // JWT or API key
    private long refId;                 // Loyalty program ID (sometimes used as programId)
    private String clientKey;           // Client identifier
    private boolean isKeyBased;         // Whether authenticated via API key
}
```

---

## Error Handling Pattern

### **SubscriptionErrorAdvice**

**File**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionErrorAdvice.java`

```java
@ControllerAdvice(assignableTypes = {SubscriptionController.class, SubscriptionReviewController.class})
@Slf4j
public class SubscriptionErrorAdvice {

    // Scoped to subscription controllers only (avoids non-deterministic Spring advisor selection)
    // Without scope, TargetGroupErrorAdvice (global) might intercept first (has catch-all Throwable)

    @ResponseBody
    @ExceptionHandler(SubscriptionNotFoundException.class)
    public ResponseEntity<ResponseWrapper<String>> handleNotFound(SubscriptionNotFoundException e) {
        log.warn("Subscription not found: {}", e.getMessage());
        return body(NOT_FOUND, e.getMessage());  // 404
    }

    @ResponseBody
    @ExceptionHandler(InvalidSubscriptionStateException.class)
    public ResponseEntity<ResponseWrapper<String>> handleInvalidState(InvalidSubscriptionStateException e) {
        log.warn("Invalid subscription state: {}", e.getMessage());
        return body(UNPROCESSABLE_ENTITY, e.getMessage());  // 422
    }

    @ResponseBody
    @ExceptionHandler(SubscriptionNameConflictException.class)
    public ResponseEntity<ResponseWrapper<String>> handleNameConflict(SubscriptionNameConflictException e) {
        log.warn("Subscription name conflict: {}", e.getMessage());
        return body(CONFLICT, e.getMessage());  // 409
    }

    @ResponseBody
    @ExceptionHandler(EMFThriftException.class)
    public ResponseEntity<ResponseWrapper<String>> handlePublishFailure(EMFThriftException e) {
        log.error("Subscription SAGA publish failed — entity set to PUBLISH_FAILED. Retry via approve endpoint. cause={}",
            e.getMessage());
        return body(INTERNAL_SERVER_ERROR,
            "Publish failed — subscription moved to PUBLISH_FAILED status. " +
            "Retry the approve action once the downstream service recovers.");  // 500
    }

    private ResponseEntity<ResponseWrapper<String>> body(
            org.springframework.http.HttpStatus status, 
            String message) {
        ResponseWrapper.ApiError error = new ResponseWrapper.ApiError(null, message);
        ResponseWrapper<String> wrapper = new ResponseWrapper<>(null, List.of(error), null);
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(wrapper);
    }
}
```

### **Global Exception Handler: TargetGroupErrorAdvice**

**File**: `/src/main/java/com/capillary/intouchapiv3/exceptionResources/TargetGroupErrorAdvice.java`

```java
@ControllerAdvice  // Global — applies to all controllers
@Slf4j
public class TargetGroupErrorAdvice {

    // Handles:
    // - BadCredentialsException → 401
    // - InvalidInputException → 400
    // - NotFoundException → 200 (OK with null data)
    // - EMFThriftException → caught here if not scoped by SubscriptionErrorAdvice
    // - ConstraintViolationException (validation) → 400
    // - DataIntegrityViolationException → 500
    // - Generic Throwable → 500

    @ExceptionHandler({EMFThriftException.class})
    public ResponseEntity<ResponseWrapper<String>> handleEMFThriftException(EMFThriftException e) {
        log.error("EMF Thrift exception: {}", e.getMessage());
        return error(INTERNAL_SERVER_ERROR, e);
    }
}
```

### **Subscription-Specific Exceptions**

1. **SubscriptionNotFoundException** — extends RuntimeException
   - Thrown when subscription not found by id/org/status
   - HTTP: 404 NOT_FOUND

2. **InvalidSubscriptionStateException** — extends RuntimeException
   - Thrown for state transition violations (e.g., PAUSE on non-ACTIVE)
   - HTTP: 422 UNPROCESSABLE_ENTITY

3. **SubscriptionNameConflictException** — extends RuntimeException
   - Thrown on name uniqueness violation (case-insensitive)
   - HTTP: 409 CONFLICT

4. **EMFThriftException** — from services.thrift.exception package
   - Wraps Thrift call failures (Thrift timeout, network, remote error)
   - HTTP: 500 INTERNAL_SERVER_ERROR
   - Triggers SAGA compensation (entity set to PUBLISH_FAILED)

---

## EF-Relevant Current State

### **SubscriptionProgram.ExtendedField (Current Model)**

**File**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java`, lines 293-301

```java
/** ADR-19: one entry per extended field configured on this subscription program. */
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public static class ExtendedField {
    @NotNull
    private ExtendedFieldType type;        // CUSTOMER_EXTENDED_FIELD or TXN_EXTENDED_FIELD
    @NotBlank
    private String key;                    // Field name/key (CURRENTLY STRING)
    private String value;                  // Field value (stored as string; type resolved at eval time)
}
```

**List Container** (line 133-136):
```java
/** ADR-19: Extended Fields — MongoDB-only, replaces CustomFields. Per G-02: defaults to empty list, never null. */
@Builder.Default
@Valid
private List<ExtendedField> extendedFields = new ArrayList<>();
```

### **Usages of extendedFields in SubscriptionFacade**

| Line | Method | Usage |
|------|--------|-------|
| 102 | createSubscription() | `.extendedFields(request.getExtendedFields() != null ? request.getExtendedFields() : List.of())` |
| 289 | updateSubscription() → updateDraft | `if (request.getExtendedFields() != null) existing.setExtendedFields(request.getExtendedFields());` |
| 343 | editActiveSubscription() → forkDraft | `.extendedFields(active.getExtendedFields() != null ? active.getExtendedFields() : List.of())` |
| 385 | duplicateSubscription() | `.extendedFields(source.getExtendedFields() != null ? source.getExtendedFields() : List.of())` |

**Exact Signatures**:

```java
// Line 102: createSubscription() builder call
.extendedFields(request.getExtendedFields() != null ? request.getExtendedFields() : List.of())

// Line 289: updateSubscription() setter call
if (request.getExtendedFields() != null) existing.setExtendedFields(request.getExtendedFields());

// Line 343: editActiveSubscription() builder call
.extendedFields(active.getExtendedFields() != null ? active.getExtendedFields() : List.of())

// Line 385: duplicateSubscription() builder call
.extendedFields(source.getExtendedFields() != null ? source.getExtendedFields() : List.of())
```

### **ExtendedFieldType Enum (SCHEDULED FOR DELETION)**

**File**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java`

```java
/**
 * Discriminator for extended field source type on a subscription program.
 * CUSTOMER_EXTENDED_FIELD: resolved from customer profile extended fields at evaluation time.
 * TXN_EXTENDED_FIELD:      resolved from transaction extended fields at evaluation time.
 *
 * ADR-19, KD-62.
 * Evaluation-time mapping: CUSTOMER_EXTENDED_FIELD → CustomFieldMapping.Type.CUSTOMER_EXTENDED_FIELDS;
 *                          TXN_EXTENDED_FIELD      → CustomFieldMapping.Type.TXN_EXT_FIELDS  (EF-OQ-01, deferred)
 */
public enum ExtendedFieldType {
    CUSTOMER_EXTENDED_FIELD,
    TXN_EXTENDED_FIELD
}
```

**Per Session Memory**: This enum must be DELETED (type discriminator moved to EF config endpoint).

### **Current Limitations**

1. **No dedicated CRUD endpoints** for extended fields
   - EF config bundled in subscription CRUD (create/update)
   - No GET /v3/extendedfields/config/{id} endpoint
   - No PUT /v3/extendedfields/config/{id} endpoint
2. **type field hardcoded in ExtendedField** 
   - Needs to be deleted; type inferred from EF config endpoint
3. **key is String** 
   - Per session memory, replace with `id: Long`
4. **MongoDB-only storage**
   - No Thrift write path (correct per ADR-19, but new EF config endpoint will need EMF integration)

---

## Files to Modify / Create (with Reasons)

### **1. DELETE**

#### **ExtendedFieldType.java**
- **Reason**: Type discrimination moves to EMF extended fields config API
- **Impact**: Remove from SubscriptionProgram.ExtendedField; remove import from SubscriptionProgram.java

### **2. MODIFY**

#### **SubscriptionProgram.java**
- **Changes**:
  - Add `import com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldConfig;` (new DTO)
  - Modify ExtendedField nested class:
    ```java
    @Data @Builder @NoArgsConstructor @AllArgsConstructor
    public static class ExtendedField {
        // DELETE: @NotNull private ExtendedFieldType type;
        
        @NotNull
        private Long id;               // NEW: id instead of key:String
        
        private String value;          // unchanged
        
        // Evaluation-time mapping handled by EMF config endpoint
    }
    ```
  - Keep `List<ExtendedField> extendedFields` field definition unchanged
  
#### **SubscriptionFacade.java**
- **No changes to logic** — extendedFields handling (lines 102, 289, 343, 385) remains same
- Setter methods remain unchanged: `facade.updateSubscription(..., request.getExtendedFields())` etc.

#### **SubscriptionErrorAdvice.java**
- **Add handler** for new extended fields exceptions:
  ```java
  @ExceptionHandler(EMFExtendedFieldsException.class)
  public ResponseEntity<ResponseWrapper<String>> handleEMFExtendedFieldsException(EMFExtendedFieldsException e) {
      log.error("Extended fields config error from EMF: {}", e.getMessage());
      return body(INTERNAL_SERVER_ERROR, "Failed to sync extended fields configuration with EMF. " +
          "Please try again or contact support.");
  }
  ```

### **3. CREATE**

#### **ExtendedFieldsController.java** 
**Location**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldsController.java`

```java
@RestController
@RequestMapping("/v3/extendedfields/config")
public class ExtendedFieldsController {

    @Autowired
    private ExtendedFieldsFacade facade;

    // POST /v3/extendedfields/config — Create new extended field config (program-scoped)
    @PostMapping
    public ResponseEntity<?> createExtendedField(
            @RequestBody ExtendedFieldConfigRequest request,
            @RequestParam Integer programId,  // loyalty program ID
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        ExtendedFieldConfig created = facade.createExtendedField(
            user.getOrgId(), programId, request, user.getTillName());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    // GET /v3/extendedfields/config?programId=5 — List EF configs for program
    @GetMapping
    public ResponseEntity<?> listExtendedFields(
            @RequestParam Integer programId,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        List<ExtendedFieldConfig> configs = facade.listExtendedFields(user.getOrgId(), programId);
        return ResponseEntity.ok(configs);
    }

    // PUT /v3/extendedfields/config/{fieldId} — Update EF config (program-scoped)
    @PutMapping("/{fieldId}")
    public ResponseEntity<?> updateExtendedField(
            @PathVariable Long fieldId,
            @RequestBody ExtendedFieldConfigRequest request,
            @RequestParam Integer programId,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        ExtendedFieldConfig updated = facade.updateExtendedField(
            user.getOrgId(), fieldId, programId, request, user.getTillName());
        return ResponseEntity.ok(updated);
    }

    // DELETE /v3/extendedfields/config/{fieldId} — Delete EF config
    @DeleteMapping("/{fieldId}")
    public ResponseEntity<?> deleteExtendedField(
            @PathVariable Long fieldId,
            @RequestParam Integer programId,
            AbstractBaseAuthenticationToken token) {
        IntouchUser user = token.getIntouchUser();
        facade.deleteExtendedField(user.getOrgId(), fieldId, programId);
        return ResponseEntity.noContent().build();
    }
}
```

**Design Rationale**:
- Scoped to `/v3/extendedfields/config` (new resource)
- Mirrors SubscriptionController pattern (controller → facade → repository + Thrift)
- programId as query parameter (not path param) — consistent with other V3 endpoints
- orgId from auth token (never in request)

#### **ExtendedFieldsFacade.java**
**Location**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldsFacade.java`

```java
@Component
public class ExtendedFieldsFacade {

    @Autowired
    private ExtendedFieldsRepository repository;

    @Autowired
    private PointsEngineRulesThriftService thriftService;

    /**
     * Create a new extended field config in MongoDB + sync with EMF via Thrift.
     * orgId sourced from auth; programId from request parameter.
     */
    public ExtendedFieldConfig createExtendedField(
            Long orgId, Integer programId, ExtendedFieldConfigRequest request, String createdBy) 
            throws Exception {
        
        // Validation: field name uniqueness within program+org
        repository.findByOrgIdAndProgramIdAndKey(orgId, programId, request.getKey())
            .ifPresent(existing -> {
                throw new InvalidInputException(
                    "Extended field key '" + request.getKey() + "' already exists for this program");
            });

        // Create MongoDB document
        Date now = new Date();
        ExtendedFieldConfig config = ExtendedFieldConfig.builder()
            .id(null)  // MongoDB auto-generates _id
            .orgId(orgId)
            .programId(programId)
            .key(request.getKey())
            .type(request.getType())  // CUSTOMER_EXTENDED_FIELD or TXN_EXTENDED_FIELD
            .description(request.getDescription())
            .required(request.isRequired())
            .createdBy(createdBy)
            .createdAt(now)
            .updatedBy(createdBy)
            .updatedAt(now)
            .build();

        ExtendedFieldConfig saved = repository.save(config);

        // Sync with EMF via Thrift
        try {
            thriftService.createExtendedFieldConfig(
                orgId.intValue(), programId, saved.getId(), request);
        } catch (Exception e) {
            // On Thrift failure, delete MongoDB doc to maintain consistency
            repository.deleteById(saved.getId());
            throw new EMFExtendedFieldsException(
                "Failed to sync extended field config with EMF: " + e.getMessage(), e);
        }

        return saved;
    }

    /**
     * List all extended field configs for a program (program-scoped).
     */
    public List<ExtendedFieldConfig> listExtendedFields(Long orgId, Integer programId) {
        return repository.findByOrgIdAndProgramId(orgId, programId);
    }

    /**
     * Update an extended field config (MongoDB + Thrift).
     */
    public ExtendedFieldConfig updateExtendedField(
            Long orgId, Long fieldId, Integer programId, 
            ExtendedFieldConfigRequest request, String updatedBy) 
            throws Exception {
        
        ExtendedFieldConfig existing = repository.findById(fieldId)
            .orElseThrow(() -> new NotFoundException("Extended field not found: " + fieldId));

        // Guard: cross-org/cross-program access
        if (!orgId.equals(existing.getOrgId()) || !programId.equals(existing.getProgramId())) {
            throw new AccessDeniedException("Cannot update extended field outside scoped org/program");
        }

        // Update mutable fields
        existing.setKey(request.getKey());
        existing.setType(request.getType());
        existing.setDescription(request.getDescription());
        existing.setRequired(request.isRequired());
        existing.setUpdatedBy(updatedBy);
        existing.setUpdatedAt(new Date());

        ExtendedFieldConfig updated = repository.save(existing);

        // Sync with EMF via Thrift
        try {
            thriftService.updateExtendedFieldConfig(
                orgId.intValue(), programId, fieldId, request);
        } catch (Exception e) {
            // Rollback MongoDB update on Thrift failure
            repository.save(existing);  // Restore previous state
            throw new EMFExtendedFieldsException(
                "Failed to sync extended field update with EMF: " + e.getMessage(), e);
        }

        return updated;
    }

    /**
     * Delete an extended field config (MongoDB + Thrift).
     */
    public void deleteExtendedField(Long orgId, Long fieldId, Integer programId) 
            throws Exception {
        
        ExtendedFieldConfig existing = repository.findById(fieldId)
            .orElseThrow(() -> new NotFoundException("Extended field not found: " + fieldId));

        if (!orgId.equals(existing.getOrgId()) || !programId.equals(existing.getProgramId())) {
            throw new AccessDeniedException("Cannot delete extended field outside scoped org/program");
        }

        // Delete from EMF via Thrift first
        try {
            thriftService.deleteExtendedFieldConfig(orgId.intValue(), programId, fieldId);
        } catch (Exception e) {
            throw new EMFExtendedFieldsException(
                "Failed to delete extended field config from EMF: " + e.getMessage(), e);
        }

        // Delete from MongoDB
        repository.deleteById(fieldId);
    }
}
```

#### **ExtendedFieldConfig.java** (MongoDB Entity)
**Location**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldConfig.java`

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "extended_fields_config")
public class ExtendedFieldConfig {

    @Id
    @JsonProperty("id")
    private Long id;

    @NotNull
    private Long orgId;

    @NotNull
    private Integer programId;           // loyalty_program_id

    @NotBlank
    @Size(max = 100)
    private String key;                  // Field name (unique per program)

    @NotNull
    @JsonProperty("type")
    private String type;                 // CUSTOMER_EXTENDED_FIELD or TXN_EXTENDED_FIELD

    private String description;

    private boolean required;

    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    private String createdBy;

    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX", timezone = "UTC")
    private Date createdAt;

    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    private String updatedBy;

    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ssXXX", timezone = "UTC")
    private Date updatedAt;
}
```

#### **ExtendedFieldsRepository.java**
**Location**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldsRepository.java`

```java
@Repository
public interface ExtendedFieldsRepository extends MongoRepository<ExtendedFieldConfig, Long> {

    Optional<ExtendedFieldConfig> findByOrgIdAndProgramIdAndKey(Long orgId, Integer programId, String key);

    List<ExtendedFieldConfig> findByOrgIdAndProgramId(Long orgId, Integer programId);

    // For programId uniqueness checks across all orgs (admin audit)
    List<ExtendedFieldConfig> findByProgramId(Integer programId);
}
```

#### **ExtendedFieldsErrorAdvice.java**
**Location**: `/src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldsErrorAdvice.java`

```java
@ControllerAdvice(assignableTypes = {ExtendedFieldsController.class})
@Slf4j
public class ExtendedFieldsErrorAdvice {

    @ResponseBody
    @ExceptionHandler(EMFExtendedFieldsException.class)
    public ResponseEntity<ResponseWrapper<String>> handleEMFException(EMFExtendedFieldsException e) {
        log.error("Extended fields EMF sync failed: {}", e.getMessage());
        return body(INTERNAL_SERVER_ERROR, 
            "Failed to sync extended fields with EMF. Please retry or contact support.");
    }

    @ResponseBody
    @ExceptionHandler(InvalidInputException.class)
    public ResponseEntity<ResponseWrapper<String>> handleInvalidInput(InvalidInputException e) {
        log.warn("Invalid extended field config: {}", e.getMessage());
        return body(BAD_REQUEST, e.getMessage());
    }

    @ResponseBody
    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ResponseWrapper<String>> handleNotFound(NotFoundException e) {
        log.warn("Extended field config not found: {}", e.getMessage());
        return body(NOT_FOUND, e.getMessage());
    }

    @ResponseBody
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ResponseWrapper<String>> handleAccessDenied(AccessDeniedException e) {
        log.warn("Access denied for extended field: {}", e.getMessage());
        return body(FORBIDDEN, "Access denied.");
    }

    private ResponseEntity<ResponseWrapper<String>> body(HttpStatus status, String message) {
        ResponseWrapper.ApiError error = new ResponseWrapper.ApiError(null, message);
        ResponseWrapper<String> wrapper = new ResponseWrapper<>(null, List.of(error), null);
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(wrapper);
    }
}
```

#### **Thrift Service Extensions**
**Modifications to**: `/src/main/java/com/capillary/intouchapiv3/services/thrift/PointsEngineRulesThriftService.java`

```java
public class PointsEngineRulesThriftService {

    /**
     * Create extended field config in EMF via Thrift.
     */
    public Long createExtendedFieldConfig(int orgId, int programId, Long fieldId, 
            ExtendedFieldConfigRequest request) throws Exception {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            ExtendedFieldConfigInfo info = buildExtendedFieldConfigInfo(fieldId, request);
            long createdId = getClient().createExtendedFieldConfig(
                orgId, programId, info, serverReqId);
            logger.info("Created extended field config in EMF. orgId={}, programId={}, fieldId={}", 
                orgId, programId, fieldId);
            return createdId;
        } catch (Exception e) {
            logger.error("Error creating extended field config in EMF. serverReqId={}", serverReqId, e);
            throw new EMFThriftException("Failed to create EF config in EMF: " + e.getMessage(), e);
        }
    }

    /**
     * Update extended field config in EMF via Thrift.
     */
    public void updateExtendedFieldConfig(int orgId, int programId, Long fieldId, 
            ExtendedFieldConfigRequest request) throws Exception {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            ExtendedFieldConfigInfo info = buildExtendedFieldConfigInfo(fieldId, request);
            getClient().updateExtendedFieldConfig(orgId, programId, fieldId, info, serverReqId);
            logger.info("Updated extended field config in EMF. orgId={}, programId={}, fieldId={}", 
                orgId, programId, fieldId);
        } catch (Exception e) {
            logger.error("Error updating extended field config in EMF. serverReqId={}", serverReqId, e);
            throw new EMFThriftException("Failed to update EF config in EMF: " + e.getMessage(), e);
        }
    }

    /**
     * Delete extended field config from EMF via Thrift.
     */
    public void deleteExtendedFieldConfig(int orgId, int programId, Long fieldId) throws Exception {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            getClient().deleteExtendedFieldConfig(orgId, programId, fieldId, serverReqId);
            logger.info("Deleted extended field config from EMF. orgId={}, programId={}, fieldId={}", 
                orgId, programId, fieldId);
        } catch (Exception e) {
            logger.error("Error deleting extended field config from EMF. serverReqId={}", serverReqId, e);
            throw new EMFThriftException("Failed to delete EF config from EMF: " + e.getMessage(), e);
        }
    }
}
```

#### **Test Files**
- **ExtendedFieldsControllerTest.java** — Spring Boot integration test for endpoints
- **ExtendedFieldsFacadeTest.java** — Unit test for facade logic + Thrift mocking
- **ExtendedFieldsRepositoryTest.java** — Unit test for repository queries

---

## Summary: New Package Structure Post-Implementation

```
com.capillary.intouchapiv3.unified.subscription/
├── [existing subscription files...]
└── extendedfields/                           [NEW PACKAGE]
    ├── ExtendedFieldsController.java         [NEW]
    ├── ExtendedFieldsFacade.java             [NEW]
    ├── ExtendedFieldsRepository.java         [NEW]
    ├── ExtendedFieldsErrorAdvice.java        [NEW]
    ├── ExtendedFieldConfig.java              [NEW MongoDB entity]
    ├── ExtendedFieldConfigRequest.java       [NEW DTO for request/response]
    ├── EMFExtendedFieldsException.java       [NEW custom exception]
    ├── [test classes...]
    └── README.md                              [NEW design documentation]
```

---

## Implementation Checklist

- [ ] **Phase 1: Model Changes**
  - [ ] Delete `ExtendedFieldType.java`
  - [ ] Modify `SubscriptionProgram.ExtendedField` — remove `type`, add `id: Long`
  - [ ] Verify existing usages (lines 102, 289, 343, 385 in SubscriptionFacade still work)

- [ ] **Phase 2: New Endpoints**
  - [ ] Create `ExtendedFieldsController.java`
  - [ ] Implement POST/PUT/GET/DELETE handlers
  - [ ] Integrate orgId from auth token (never from request)
  - [ ] Test program_id parameter handling

- [ ] **Phase 3: Facade + Repository**
  - [ ] Create `ExtendedFieldsFacade.java`
  - [ ] Create `ExtendedFieldsRepository.java`
  - [ ] Implement Thrift call pattern (matching SubscriptionPublishService style)
  - [ ] Add idempotency guards for Thrift calls

- [ ] **Phase 4: Thrift Integration**
  - [ ] Extend `PointsEngineRulesThriftService` with EF config methods
  - [ ] Test Thrift client initialization + error handling
  - [ ] Wrap exceptions in `EMFExtendedFieldsException`

- [ ] **Phase 5: Error Handling**
  - [ ] Create `ExtendedFieldsErrorAdvice.java`
  - [ ] Add EMF exception handler to main `SubscriptionErrorAdvice.java`
  - [ ] Test HTTP status codes (201, 200, 404, 409, 500)

- [ ] **Phase 6: Testing**
  - [ ] Unit tests for ExtendedFieldsFacade (Thrift mocked)
  - [ ] Repository tests for uniqueness queries
  - [ ] Integration tests for controller endpoints
  - [ ] Cross-org/cross-program isolation tests

---

