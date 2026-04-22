# Code Analysis: emf-parent — Loyalty Extended Fields CRUD (CAP-183124)

## Module Structure

**Primary Modules in emf-parent:**
- **pointsengine-emf** (recommended for new Service + DAO): Contains Points Engine logic, services, DAOs, and entities for warehouse DB. This is the appropriate module for loyalty-extended-fields CRUD implementation.
- **pointsengine-emf-ut**: Unit tests for pointsengine-emf
- **emf**: Core EMF (Event Management Framework) implementation, services for EMF execution
- **emf-ut**: EMF unit tests
- **emf-all**: Integration and aggregation module
- **integration-test**: Integration tests
- **dvs-emf, milestone-endpoint, promotion-emf-endpoint, referral-endpoint, timeline-endpoint, report**: Specialized endpoints

**Recommendation:** Implement LoyaltyExtendedFieldsService and LoyaltyExtendedFieldsDao in **pointsengine-emf**, alongside the existing ProgramConfigKey/ProgramConfigKeyValue pattern.

---

## JPA / Warehouse DB Patterns

### Entity Pattern (Composite PK with @EmbeddedId)

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramConfigKeyValue.java`

```java
@Entity
@Table(name = "program_config_key_values")
public class ProgramConfigKeyValue implements Serializable {
    @Embeddable
    public static class ProgramConfigKeyValuePK extends OrgEntityIntegerPKBase {
        private static final long serialVersionUID = 3494406664164509945L;

        public ProgramConfigKeyValuePK() {
            super();
        }

        public ProgramConfigKeyValuePK(final int id, final int orgId) {
            super(id, orgId);
        }
    }

    @EmbeddedId
    private ProgramConfigKeyValuePK pk;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumns({ 
        @JoinColumn(name = "program_id", nullable = false, insertable = false, updatable = false),
        @JoinColumn(name = "org_id", nullable = false, insertable = false, updatable = false) 
    })
    private Program program;

    @Basic
    @Column(name = "program_id", nullable = false)
    private int programId;

    @Basic
    @Column(name = "key_id", nullable = false)
    private int keyId;

    @Basic
    @Column(name = "value", nullable = false)
    private String value;

    @Basic
    @Column(name = "updated_by", nullable = false)
    private int updatedBy;

    @Basic
    @Column(name = "updated_on", nullable = false)
    @Temporal(TemporalType.TIMESTAMP)
    private Date updatedOn;

    @Basic
    @Column(name = "is_valid", nullable = false)
    private boolean isValid;
}
```

**Key Takeaways:**
- Composite PK uses `@EmbeddedId` with `ProgramConfigKeyValuePK extends OrgEntityIntegerPKBase`
- `OrgEntityIntegerPKBase` is from external library `com.capillary.commons.data`
- PK has `(id, orgId)` structure
- Include a builder pattern for entity construction (see lines 184-260 in source)
- Standard timestamp and status fields (updated_by, updated_on, is_valid)

---

### DataSource Annotation

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/data/services/EMFServiceManager.java` (lines 48-50)

```java
@Service
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)
public class EMFServiceManager {
    // service implementation
}
```

**Import:**
```java
import com.capillary.shopbook.emf.api.hibernate.DataSourceSpecification;
import com.capillary.shopbook.emf.api.hibernate.DataSourceSpecification.SchemaType;
```

**Pattern:** `@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)` marks class as warehouse DB-aware. Always pair with `@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)`.

---

### Transactional Pattern

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/BulkRedemptionService.java` (lines 49)

```java
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public class BulkRedemptionService {
    // service implementation with database operations
}
```

**Imports:**
```java
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
```

**DAO Pattern:**
```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)
public interface ProgramConfigKeyValueDao extends GenericDao<ProgramConfigKeyValue, ProgramConfigKeyValue.ProgramConfigKeyValuePK> {
    // query methods
}
```

**Pattern:** Services use `Propagation.REQUIRED`, DAOs use `Propagation.SUPPORTS` for query-only operations.

---

## ProgramConfigKeyValue Entity

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramConfigKeyValue.java` (Full code above in JPA section)

**Key Fields:**
- `pk` (ProgramConfigKeyValuePK): Composite key `(id, orgId)`
- `programId` (int): Links to Program
- `keyId` (int): Foreign key to ProgramConfigKey
- `value` (String): The configuration value
- `updatedBy`, `updatedOn`, `isValid`: Audit fields

**Builder Pattern:** Includes fluent builder (ProgramConfigKeyValueBuilder) for clean entity construction.

---

## ProgramConfigKey Entity

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/ProgramConfigKey.java` (Full code)

```java
@Entity
@Table(name = "program_config_keys")
public class ProgramConfigKey implements Serializable {
    private static final long serialVersionUID = 7481562216409712963L;

    @Id
    @Column(name = "id", nullable = false)
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;

    @Basic
    @Column(name = "name", nullable = false)
    private String name;

    @Basic
    @Column(name = "value_type", nullable = false)
    private ProgramConfigKeyValueType valueType;

    @Basic
    @Column(name = "default_value", nullable = false)
    private String defaultValue;

    @Basic
    @Column(name = "label", nullable = false)
    private String label;

    @Basic
    @Column(name = "added_by", nullable = false)
    private int addedBy;

    @Basic
    @Column(name = "added_on", nullable = false)
    @Temporal(TemporalType.TIMESTAMP)
    private Date addedOn;

    @Basic
    @Column(name = "is_valid", nullable = false)
    private boolean isValid;

    // Getters and setters
    // hashCode() and equals() based on id
}
```

**Key Takeaways:**
- Simple single-column PK with `@GeneratedValue(strategy = GenerationType.IDENTITY)`
- No org_id because it's a system-wide master table
- valueType field uses enum `ProgramConfigKeyValueType`
- Audit fields (added_by, added_on, is_valid)

---

## DAO Patterns

### ProgramConfigKeyValueDao

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/ProgramConfigKeyValueDao.java` (Full code)

```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)
public interface ProgramConfigKeyValueDao extends 
        GenericDao<ProgramConfigKeyValue, ProgramConfigKeyValue.ProgramConfigKeyValuePK> {

    @Query("SELECT pckv FROM ProgramConfigKeyValue pckv WHERE pckv.pk.orgId = :orgId AND pckv.programId = :programId AND pckv.isValid = :isValid")
    List<ProgramConfigKeyValue> findByProgramAndValidity(@Param("orgId") int orgId,
            @Param("programId") int programId, @Param("isValid") boolean isValid);

    @Query("SELECT pckv FROM ProgramConfigKeyValue pckv WHERE pckv.pk.orgId = :orgId AND pckv.programId = :programId AND pckv.keyId = :keyId AND pckv.isValid = :isValid")
    ProgramConfigKeyValue findByKeyIdAndValidity(@Param("orgId") int orgId, @Param("programId") int programId,
            @Param("keyId") int keyId, @Param("isValid") boolean isValid);
}
```

**Key Patterns:**
- Extends `GenericDao<Entity, PK>`
- `@Query` with JPQL
- Always filters by `orgId` (multi-tenancy)
- Always checks `isValid` flag for soft-deletes

---

### HistoricalPointsDao (Advanced Example with Pagination)

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/HistoricalPointsDao.java` (Selected methods)

```java
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)
public interface HistoricalPointsDao extends GenericDao<HistoricalPoints, HistoricalPoints.HistoricalPointsPK> {

    @Query(" SELECT hp FROM HistoricalPoints hp "
           + "WHERE hp.pk.orgId = :org_id "
           + "AND hp.customerId = :customer_id ORDER BY hp.eventDate desc")
    List<HistoricalPoints> findHistoricalPointsByCustomer(@Param("org_id") int orgId,
            @Param("customer_id") int customerId, Pageable pageable);

    @Query(" SELECT hp FROM HistoricalPoints hp "
           + "WHERE hp.pk.orgId = :org_id "
           + "AND hp.customerId = :customer_id "
           + "AND hp.billNumber = :bill_number ")
    List<HistoricalPoints> findHistoricalPointsByBillNumber(@Param("org_id") int orgId,
            @Param("customer_id") int customerId, @Param("bill_number") String billNumber, Pageable pageable);
}
```

**Key Patterns:**
- Pagination via `Pageable` parameter (Spring Data)
- Order By clauses for consistent sorting
- Multiple filter combinations

---

## EMFException (Java)

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/api/exception/ValidationException.java`

```java
package com.capillary.shopbook.emf.api.exception;

public class ValidationException extends RuntimeException {
    public ValidationException(String message) {
        super(message);
    }
}
```

**Thrift Definition (emf.thrift):**
```thrift
exception EMFException {
    1: required i32 statusCode;
    2: required string errorMessage;
    3: required i32 replayErrorCode;
}
```

**Related Exceptions in Java:**
- `com.capillary.shopbook.emf.api.exception.ValidationException`
- `com.capillary.shopbook.emf.api.exception.OverloadedException`
- `com.capillary.shopbook.emf.api.exception.RuleConfigurationException`
- `com.capillary.shopbook.emf.api.exception.EventExecutionException`
- `com.capillary.shopbook.emf.api.exception.InvalidConfigurationException`

**Pattern:** Custom exceptions extend RuntimeException; Thrift exceptions include statusCode, errorMessage, replayErrorCode.

---

## EMFService Implementation

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/external/EMFThriftServiceImpl.java`

### Class Declaration (lines 82-127)

```java
@Service
@ExposedCall(thriftName = "emf")
public class EMFThriftServiceImpl implements Iface {

    private static Logger logger = LoggerFactory.getLogger(EMFThriftServiceImpl.class);
    private static Logger emfEvalLogger = LoggerFactory.getLogger("emfEvalLogger");

    private AtomicInteger requestCounter = new AtomicInteger();

    @Autowired
    private EmfInfoLookupService m_infoLookupService;

    @Autowired
    private ConfigKeyLookupService configKeyLookupService;

    @Autowired
    EventForestLogServiceImpl eventForestLogService;

    @Autowired
    private ExecutionLoggingService m_executionLoggingService;

    @Autowired
    private EmfMongoDbService emfMongoDbService;

    // ... more autowired fields
}
```

### Representative Method Signatures (from emf.thrift lines 1079-1091)

```java
// Thrift interface method (generated from .thrift):
EventEvaluationResult transactionAddEvent(NewBillEvent transactionAddData, boolean isCommit, boolean isReplayed) throws EMFException, TException;

EventEvaluationResult registrationEvent(CustomerRegistrationEvent registrationEvent, boolean isCommit, boolean isReplayed) throws EMFException, TException;

EventEvaluationResult pointsRedemptionEvent(PointsRedemptionEventData pointsRedemptionEventData, boolean isCommit, boolean isReplayed) throws EMFException, TException;
```

### Implementation Pattern (lines 188-220)

```java
@Trace(dispatcher = true)
@MDCData(orgId = "#transactionAddData.orgID", requestId = "#transactionAddData.serverReqId",
        uniqueId = "#transactionAddData.uniqueId")
public EventEvaluationResult transactionAddEvent(NewBillEvent transactionAddData, boolean isCommit,
                                                 boolean isReplayed) throws EMFException, TException {
    EventManagerImpl.instance().getStatistics().incrementTxnAddEventRequests();

    long requestStartTime = System.currentTimeMillis();
    Event event = null;
    EventType eventType = EventType.TransactionAdd;
    boolean success = true;
    try {
        int orgId = transactionAddData.orgID;
        long customerId = transactionAddData.customerID;
        int storeUnitID = transactionAddData.getStoreUnitID();

        event = initializeTransactionAddEvent(transactionAddData, orgId, (int) customerId, storeUnitID, eventType,
                isReplayed, isCommit);
        event.setServerReqId(transactionAddData.getServerReqId());
        com.capillary.shopbook.emf.api.system.EventEvaluationResult ev = handleTransactionAddEvent(
                transactionAddData, event, isCommit);

        return processEventEvaluationResult(ev, isCommit, transactionAddData.shouldFetchEventLogs);
    } catch (Throwable t) {
        success = EMFUtils.isEventSuccessful(t);
        return handleFailedEvent(EventType.TransactionAdd, event, isCommit, t);
    } finally {
        long requestEndTime = System.currentTimeMillis();
        EventManagerImpl
                .instance()
                .getStatistics()
                .timeForRequest(eventType, requestEndTime - requestStartTime, success);
    }
}
```

### Thrift Service Methods (from emf.thrift lines 1042+)

```thrift
service EMFService {
    EventEvaluationResult newBillEvent (1: NewBillEvent newBillEvent, 2: bool isCommit, 3: bool isReplayed) throws (1 :EMFException ex);
    
    EventEvaluationResult registrationEvent (1: CustomerRegistrationEvent registrationEvent, 2: bool isCommit, 3: bool isReplayed) throws (1 :EMFException ex);
    
    EventEvaluationResult pointsRedemptionEvent (1: PointsRedemptionEventData pointsRedemptionEventData, 2: bool isCommit, 3: bool isReplayed) throws (1 :EMFException ex);
    
    EventEvaluationResult voucherRedemptionEvent (1: VoucherRedemptionEventData voucherRedemptionEventData, 2: bool isCommit, 3: bool isReplayed) throws (1 :EMFException ex);
    
    boolean isRunning(1: string serverRequestId) throws (1: TException ex);
    
    boolean isAlive() throws (1: TException ex);
}
```

**Delegation Pattern:**
- Thrift impl calls helper methods (initializeTransactionAddEvent, handleTransactionAddEvent)
- Services are injected with @Autowired
- MDCData annotations for logging context
- @Trace from NewRelic for monitoring

---

## Service Layer Patterns (Validation, Uniqueness)

### Validation Service Example

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/RESTEndpoint/validators/impl/ProgramConfigKeyValueValidatorImpl.java`

```java
@Component
public class ProgramConfigKeyValueValidatorImpl implements ProgramConfigKeyValueValidator {
    @Autowired
    @Qualifier("infoLookupService")
    private InfoLookupService m_infoLookupService;

    @Override
    public ValidatorResponse validate(ProgramConfigKeyValueRequest request) {
        ValidatorResponse response = new ValidatorResponse();

        Map<String, String> pckMap = request.getProgramConfigs();
        List<ProgramConfigKey> programConfigKeys = m_infoLookupService.getAllValidProgramConfigKeys();
        Map<String, ProgramConfigKey> programConfigNameToIdMap = programConfigKeys.stream()
                .collect(Collectors.toMap(ProgramConfigKey::getName, Function.identity()));

        List<String> invalidConfigValues = new ArrayList<>();
        for (String requestKey : pckMap.keySet()) {
            ProgramConfigKey programConfigKey = programConfigNameToIdMap.get(requestKey);
            ProgramConfigKeyValueType valueType = programConfigKey.getValueType();

            String requestValue = pckMap.get(requestKey);
            try {
                switch (valueType) {
                    case NUMERIC:
                        Integer.parseInt(requestValue);
                        break;
                    case BOOL:
                        if (!requestValue.equals("0") && !requestValue.equals("1")) {
                            invalidConfigValues.add(requestKey);
                        }
                        break;
                    case STRING:
                        if (requestKey.equalsIgnoreCase("PROMOTION_RANKING_STACKING_STRATEGY")) {
                            PromotionRankingStackingStrategyDto dto;
                            dto = new ObjectMapper().readValue(requestValue, PromotionRankingStackingStrategyDto.class);
                            if (!PromotionRankingStackingStrategyUtil.isValid(dto)) {
                                invalidConfigValues.add(requestKey);
                            }
                        }
                        break;
                    default:
                        log.warn("no validation done for value type {}", valueType);
                        break;
                }
            } catch (Exception ex) {
                log.info("exception occurred while validating", ex);
                invalidConfigValues.add(requestKey);
            }
        }
        if (!invalidConfigValues.isEmpty()) {
            response.setResponseMessage(ResponseMessage.INVALID_PROGRAM_CONFIG_VALUES + String.join(", ", invalidConfigValues));
            response.setStatus(false);
            response.setResponseCode(400);
            return response;
        }
        return response;
    }
}
```

**Pattern:**
- Validator as @Component, injected into service/controller
- Validates input data before persistence
- Returns ValidatorResponse with status, message, code
- Type-specific validation logic (numeric, boolean, string)
- Null-safe collection transformations with streams

### Service Layer Pattern (Transaction + Validation)

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/BulkRedemptionService.java` (lines 49-100)

```java
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public class BulkRedemptionService {
    @Autowired
    @Qualifier("infoLookupService")
    InfoLookupService infoLookupService;

    @Autowired
    protected GenericQueryDao genericQueryDao;

    @Autowired
    private PeCustomerPointsSummaryDao peCustomerPointsSummaryDao;

    @Autowired
    private PointsRedemptionSummaryDao prsDao;

    // Business logic with DAO delegation and validation
    public void redeemPoints(int orgId, int customerId, int programId, BigDecimal points) {
        // Validate sufficiency of points
        CustomerPointsSummary summary = peCustomerPointsSummaryDao.findById(new CustomerPointsSummaryPK(customerId, orgId));
        if (summary.getAvailablePoints().compareTo(points) < 0) {
            throw new InsufficientPointsInCategoryException("Not enough points");
        }
        // Then call DAO to update
        prsDao.saveAndFlush(redemptionRecord);
    }
}
```

**Pattern:**
- Service performs business validation before DAO calls
- DAO calls are delegated to dedicated repositories
- Validation throws domain-specific exceptions
- Transactional boundaries are at service level

---

## Test Patterns

### Unit Test Base Class (Mockito)

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf-ut/src/test/java/com/capillary/shopbook/pointsengine/endpoint/impl/base/PartnerProgramBaseTest.java`

```java
public class PartnerProgramBaseTest {
    public int orgId = 1;
    public int loyaltyProgramId = 1;
    public int customerId = 280084207;
    public int partnerProgramId = 1;

    @Mock
    public PointsProgramConfig pointsProgramConfig;

    @Mock
    public CustomerProfile customerProfile;

    @Mock
    Event event;

    @Mock
    public Payload payload;

    @Before
    public void setUp() throws Exception {
        PackageID packageIDForCustomer = new LongID(280084207L);
        when(payload.getEvent()).thenReturn(event);
        when(event.getEventVariable(EventType.CURRENT_CUSTOMER)).thenReturn(eventVariableInfo);
        when(payload.resolve(EventType.CURRENT_CUSTOMER)).thenReturn(customerProfile);
        // ...
    }
}
```

**Annotations:**
- `@Mock` for Mockito dependencies
- `@Before` (JUnit 4) for setUp
- `when(...).thenReturn(...)` for mocking behavior

### Unit Test with MockitoJUnitRunner

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf-ut/src/test/java/com/capillary/shopbook/pointsengine/services/PointsUnlockServiceTest.java`

```java
@RunWith(MockitoJUnitRunner.class)
public class PointsUnlockServiceTest {
    @Mock
    private TransactionPointUnlockService transactionPointUnlockService;

    @Mock
    private Map<String, IPointsUnlock> map;

    @InjectMocks
    private PointsUnlockService pointsUnlockService;

    @Before
    public void setUp() throws Exception {
        String defaultTimeZone = new DateTime().getZone().getID();
        // Mock setup
    }

    @Test
    public void shouldUnlockPointsForTransactionAddEvent() throws PointsUnlockException {
        PointsUnlockParams params = new PointsUnlockParams();
        params.setEventName(EventType.TransactionAdd.name());

        ArrayList<PointsUnlockResponse> unlockResponses = new ArrayList<>();
        when(transactionPointUnlockService.unlockPoints(any(), anyList())).thenReturn(unlockResponses);

        List<PointsUnlockResponse> result = pointsUnlockService.unlockPoints(params, manualPointConversionEventLogId);

        assertEquals(1, result.size());
        verify(transactionPointUnlockService).unlockPoints(any(), anyList());
    }
}
```

### Integration Test Base Class

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/integration-test/src/test/java/com/capillary/shopbook/test/emf/events/EventsBaseIntegrationTest.java`

```java
@ContextConfiguration(classes = {IntegrationStarterConfig.class})
@RunWith(SpringJUnit4ClassRunner.class)
public class EventsBaseIntegrationTest extends BaseIntegrationTest {
    public int ORG_ID = 100;
    public int PROGRAM_ID = 200;

    @Autowired
    protected TrackerRulesetEditorHelper trackerRulesetEditorHelper;

    @Autowired
    protected PeCustomerEnrollmentDao customerEnrollmentDao;

    // Helper methods for test setup (triggerCustomerAdd, triggerNewBill, etc.)
    protected void printAwardInstructionsSummary(EventEvaluationResult eventEvaluationResult) {
        if (eventEvaluationResult == null || eventEvaluationResult.getInstructions() == null) {
            System.out.println("EventEvaluationResult: no instructions");
            return;
        }
        // Print logic
    }
}
```

### Integration Test Implementation

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/integration-test/src/test/java/com/capillary/shopbook/test/pointsengine/GetPointsBalanceForEntityTest.java`

```java
@ContextConfiguration(classes = {IntegrationStarterConfig.class})
@RunWith(SpringJUnit4ClassRunner.class)
public class GetPointsBalanceForEntityTest extends EventsBaseIntegrationTest {

    @Test
    @Ignore
    public void getMainAndDelayedPointsBalanceForSingleProgramEntityTest() throws Exception {
        OrgConfigurationFixture orgConfigurationFixture = orgConfigManager.getOrgConfiguration(TestOrg.ORG_100);
        ProgramFixture programFixture = orgConfigurationFixture.getDefaultProgramFixture();
        IntegrationTestMock.isMocked = true;

        // Trigger events and assert results
        Map<Integer, EventEvaluationResult> result = triggerCustomerAdd(programFixture, false, false);
        Integer customerId = new ArrayList<>(result.keySet()).get(0);
        CustomerEnrollment customer1 = getCustomerEnrollment(programFixture, customerId);
        result = triggerNewBill(programFixture, false, false, customerId);

        // Assertions
        EntityPointsBalance pointsBalance = pointsEngineRpcClient.getPointsBalanceForEntity(customerFilter, "dummy1");
        assertNotNull(pointsBalance);
        assertEquals(customer1.getCustomerId(), pointsBalance.getEntityId());
    }
}
```

**Annotations:**
- `@ContextConfiguration(classes = {...})` for Spring test context
- `@RunWith(SpringJUnit4ClassRunner.class)` for Spring test runner
- `@Autowired` for injecting DAOs, services, fixtures
- `@Ignore` for temporarily disabled tests
- Base class (EventsBaseIntegrationTest) provides helper methods

---

## Existing Extended Field Classes

### ExtendedFieldData (DTO Wrapper)

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/emf/src/main/java/com/capillary/shopbook/emf/impl/data/commons/dto/ExtendedFieldData.java`

```java
package com.capillary.shopbook.emf.impl.data.commons.dto;

import com.capillary.shopbook.emf.api.external.ExtendedFieldsData;

public class ExtendedFieldData {
    private ExtendedFieldsData m_extendedFieldsData;

    public ExtendedFieldData(ExtendedFieldsData extendedFieldsData) {
        this.m_extendedFieldsData = extendedFieldsData;
    }

    public String getName() {
        return m_extendedFieldsData.getName();
    }

    public String getValue() {
        return m_extendedFieldsData.getValue();
    }

    public String getPreviousValue() {
        return m_extendedFieldsData.getPreviousValue();
    }

    public boolean isSetPreviousValue() {
        return m_extendedFieldsData.isSetPreviousValue();
    }
}
```

### Thrift ExtendedFieldsData References

**File:** `/Users/baljeetsingh/IdeaProjects/emf-parent/emf-all/scripts/emf.thrift` (lines 174, 201, 234)

```thrift
struct UserDetails {
    // ...
    6: optional map<string,string> extendedFieldsData;
    7: optional list<string> labels;
}

struct LineItem {
    // ...
    2: required map<string,string> extendedFieldsData;
    // ...
}

struct NewBillEvent {
    // ...
    23: optional map<string,string> extendedFieldsData;
    24: optional list<LineItem> lineItems;
}
```

### Existing Extended Field Extractors

**Files:**
- `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/CustomerExtendedFieldExtractor.java`
- `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/LineItemExtendedFieldExtractor.java`
- `/Users/baljeetsingh/IdeaProjects/emf-parent/pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/TransactionExtendedFieldExtractor.java`

**Usage:** These classes extract extended field data from events; loyalty_extended_fields will follow similar extraction pattern.

---

## Key Facts for Feature Implementation

### Module & Package Placement
- **Module:** `pointsengine-emf`
- **Package:** `com.capillary.shopbook.points`
- **Subpackages:**
  - `entity`: LoyaltyExtendedField.java
  - `dao`: LoyaltyExtendedFieldDao.java
  - `services`: LoyaltyExtendedFieldService.java
  - `dto`: LoyaltyExtendedFieldRequest.java, LoyaltyExtendedFieldResponse.java (if needed)

### Database Table Structure
- **Table Name:** `loyalty_extended_fields`
- **Columns (inferred from pattern):**
  - `id` (INT, auto-increment): Composite PK
  - `org_id` (INT): Composite PK, multi-tenancy
  - `loyalty_program_id` (INT): FK to loyalty/program
  - `field_name` (VARCHAR): Extended field name/key
  - `field_value` (VARCHAR/TEXT): Extended field value
  - `field_type` (VARCHAR): Type hint (string, numeric, date, etc.)
  - `updated_by` (INT): Audit
  - `updated_on` (TIMESTAMP): Audit
  - `is_valid` (BOOLEAN): Soft-delete flag
  - **Indexes:** (id, org_id), (org_id, loyalty_program_id)

### JPA Entity Implementation
- Create `LoyaltyExtendedField` class extending patterns from `ProgramConfigKeyValue`
- Use composite PK: `LoyaltyExtendedFieldPK extends OrgEntityIntegerPKBase` with `(id, orgId)`
- Use `@EmbeddedId` annotation
- Include builder pattern for entity construction
- Add audit fields (updated_by, updated_on, is_valid)

### DAO Implementation
- Extend `GenericDao<LoyaltyExtendedField, LoyaltyExtendedFieldPK>`
- Implement `@Query` methods with `orgId` and program filters
- Support pagination via `Pageable`
- Methods:
  - `findByLoyaltyProgramId(orgId, programId, pageable)`
  - `findByFieldName(orgId, programId, fieldName)`
  - `findByProgramAndValidity(orgId, programId, isValid)`
  - `findAll(orgId, pageable)` (inherited from GenericDao)
- Use `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`

### Service Implementation
- Create `LoyaltyExtendedFieldService` in `pointsengine-emf` service package
- Use `@Service` + `@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)`
- Consider `@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)` if cross-schema operations
- Implement CRUD methods:
  - `create(LoyaltyExtendedField)` — validate uniqueness (org_id, program_id, field_name) before insert
  - `read(id, orgId)` — fetch single record
  - `update(LoyaltyExtendedField)` — update and validate
  - `delete(id, orgId)` — soft-delete (set is_valid = false)
  - `findByProgram(orgId, programId, pageable)`
- Inject validators and perform validation before DAO calls

### Thrift Service Methods (EMFService)
- Extend `emf.thrift` with new service methods:
  - `createLoyaltyExtendedField(orgId, programId, fieldName, fieldValue, fieldType, userId) throws EMFException`
  - `readLoyaltyExtendedField(id, orgId) throws EMFException`
  - `updateLoyaltyExtendedField(id, orgId, fieldValue, userId) throws EMFException`
  - `deleteLoyaltyExtendedField(id, orgId) throws EMFException`
  - `listLoyaltyExtendedFields(orgId, programId, offset, limit) throws EMFException`
  - Return types: custom Thrift structs (LoyaltyExtendedFieldData, LoyaltyExtendedFieldList)
- Implement in `EMFThriftServiceImpl` following existing patterns (MDCData, @Trace, exception handling)

### Validation Patterns
- **Uniqueness:** Before CREATE, check DAO for existing (org_id, program_id, field_name)
- **Type Validation:** Validate field_value matches field_type (numeric, date, etc.)
- **Nullability:** field_name and field_value must be non-null
- **Throw:** `ValidationException` with descriptive message
- Create `LoyaltyExtendedFieldValidator` component if complex rules

### Exception Handling
- Use existing exception hierarchy (ValidationException, InvalidConfigurationException)
- Thrift: throw EMFException with statusCode, errorMessage, replayErrorCode
- Map application exceptions to EMFException in EMFThriftServiceImpl

### Testing
- **Unit Tests:** Extend MockitoJUnitRunner base, mock DAO and service dependencies
- **Integration Tests:** Extend EventsBaseIntegrationTest, use Spring test context, autowire DAOs
- Test fixtures:
  - Create fixtures for LoyaltyExtendedField test data
  - Use TestOrg (test organization IDs)
  - Follow GetPointsBalanceForEntityTest pattern
- Coverage:
  - CRUD operations (create, read, update, delete)
  - Uniqueness validation
  - Type validation
  - Pagination
  - Multi-tenancy (org_id filtering)

### Transaction Boundaries
- Service layer: `@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)`
- DAO layer: `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`
- **Rollback strategy:** `rollbackFor = Exception.class` (uncommon; use specific exceptions)

### Configuration & Lookup Services
- Follow `InfoLookupService` pattern for master data lookups
- Cache loyalty programs via `@Cacheable` if performance-critical
- Use `ConfigKeyLookupService` pattern for configuration lookups

### Build & Packaging
- POM location: `pointsengine-emf/pom.xml` (module descriptor)
- Build target: JAR within `emf-parent` parent POM
- Dependencies: Already included (JPA, Spring Data, Hibernate, Lombok for entity builders)

---

## Development Checklist

1. ✓ Understand module structure (pointsengine-emf is the home)
2. ✓ Study ProgramConfigKey/ProgramConfigKeyValue pattern for composite PKs
3. ✓ Understand warehouse DB transactional boundaries (@Transactional, @DataSourceSpecification)
4. ✓ Study DAO @Query patterns with orgId filtering and pagination
5. ✓ Study EMFThriftServiceImpl method signatures and delegation patterns
6. ✓ Create JPA entity with composite PK (@EmbeddedId) and builder
7. ✓ Implement DAO extending GenericDao with @Query methods
8. ✓ Implement Service layer with validation and DAO delegation
9. ✓ Add Thrift methods to emf.thrift and implement in EMFThriftServiceImpl
10. ✓ Create validators following ProgramConfigKeyValueValidatorImpl pattern
11. ✓ Write unit tests with @RunWith(MockitoJUnitRunner.class)
12. ✓ Write integration tests extending EventsBaseIntegrationTest
13. ✓ Ensure multi-tenancy (org_id filters everywhere)
14. ✓ Handle soft-deletes (is_valid flag)
15. ✓ Follow audit trail (updated_by, updated_on)

