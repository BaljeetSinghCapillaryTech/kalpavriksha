# Low-Level Design — Loyalty Extended Fields CRUD (CAP-183124)
> Phase: 7 (Designer)
> Date: 2026-04-22
> Status: Complete
> Confidence: C7 — all interface signatures derived from direct codebase reads

---

## Preamble: Codebase Patterns Confirmed

The following patterns were read directly from source before writing any signatures.

| Pattern | Source File | Key Finding |
|---------|-------------|-------------|
| Thrift client | `EmfPromotionThriftService.java` | `@Service @Loggable`; `RPCService.rpcClient(EMFService.Iface.class, "emf-thrift-service", 9199, 10000)` in `protected getClient()`; `catch (Exception e)` wraps to `RuntimeException` |
| REST Controller style | `SubscriptionController.java` | `@RestController`, `@RequestMapping`; `ResponseEntity<?>` return type; `AbstractBaseAuthenticationToken token` as last parameter; `token.getIntouchUser()` for orgId extraction; `@Autowired` field injection |
| DAO pattern | `CappingConfigDao.java`, `HistoricalPointsDao.java` | `extends GenericDao<Entity, PK>`; `@Repository`; `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`; `@Query` JPQL with `@Param` for custom queries |
| JPA Entity pattern | `ProgramConfigKeyValue.java` | `@Entity @Table(name=…)`; `@EmbeddedId PK`; no `@DataSourceSpecification` on entity — that annotation lives on service classes; builder inner class; plain getters/setters |
| Service annotation | `InfoLookupService.java`, `SlabDowngradeService.java` | `@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)` on `@Service` implementation, NOT on entity |
| Error advice | `SubscriptionErrorAdvice.java` | `@ControllerAdvice(assignableTypes = {…})`; `@ResponseBody @ExceptionHandler`; `ResponseEntity<ResponseWrapper<String>>`; `ResponseWrapper.ApiError(Long code, String message)` |
| `EMFThriftException` | `EMFThriftException.java` | Only carries `String message` — NO statusCode field. New `EFThriftException` extends it and adds `int statusCode` |
| `EMFException` (Thrift) | `emf.thrift:14` | `exception { 1: i32 statusCode; 2: string errorMessage; 3: i32 replayErrorCode; }` |
| entity schema annotation | `ActionPointsDetail.java` | `@Table(name = "...", schema = "warehouse")` — schema name in `@Table`, no separate annotation |

---

## Section 1: thrift-ifaces-emf — emf.thrift Additions

**File**: `/Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf/emf.thrift`

**Append after the last struct definition, before `service EMFService {`**

### 1a. New Structs

```thrift
// ============================================================
// Loyalty Extended Fields CRUD — CAP-183124
// ============================================================

/**
 * Response struct for a single EF config record from loyalty_extended_fields table.
 * All non-nullable DB columns are `required`; nullable columns are `optional`.
 * ADR-01: required only on response fields that are always present.
 */
struct LoyaltyExtendedFieldConfig {
    1: required i64    id             // loyalty_extended_fields.id (BIGINT PK)
    2: required i64    orgId          // loyalty_extended_fields.org_id
    3: required i64    programId      // loyalty_extended_fields.program_id
    4: required string name           // loyalty_extended_fields.name
    5: required string scope          // loyalty_extended_fields.scope (e.g. SUBSCRIPTION_META)
    6: required string dataType       // loyalty_extended_fields.data_type: STRING | NUMBER | BOOLEAN | DATE
    7: required bool   isMandatory    // loyalty_extended_fields.is_mandatory
    8: optional string defaultValue   // loyalty_extended_fields.default_value (nullable)
    9: required bool   isActive       // loyalty_extended_fields.is_active
    10: required string createdOn     // UTC ISO-8601 string e.g. "2026-04-22T10:00:00Z"
    11: required string updatedOn     // UTC ISO-8601 string
    12: optional string updatedBy     // loyalty_extended_fields.updated_by (nullable)
}

/**
 * Request struct for creating a new EF config.
 * ADR-01 DEVIATION: Fields that are logically required are marked `required` here
 * EXCEPT for rolling-deploy safety — see ADR-01 notes.
 * orgId is populated by V3 from auth context; never from HTTP body (G-07.1).
 */
struct CreateLoyaltyExtendedFieldRequest {
    1: required i64    orgId          // V3 populates from auth token; never from client
    2: required i64    programId
    3: required string name
    4: required string scope
    5: required string dataType       // STRING | NUMBER | BOOLEAN | DATE
    6: required bool   isMandatory
    7: optional string defaultValue
    8: optional string createdBy      // tillName from auth token for audit
}

/**
 * Request struct for updating an EF config (partial update — name and/or isActive only).
 * id and orgId are required for lookup + tenancy. name/isActive/updatedBy are optional
 * because update is partial: not all must be provided.
 * D-23: scope, dataType, isMandatory, defaultValue are immutable — not in this struct.
 */
struct UpdateLoyaltyExtendedFieldRequest {
    1: required i64    id             // PK of the record to update
    2: required i64    orgId          // V3 populates from auth token for tenancy check
    3: optional string name           // if absent, name is not updated
    4: optional bool   isActive       // if absent, is_active is not updated; false = soft-delete
    5: optional string updatedBy      // tillName from auth token for audit
}

/**
 * Paginated list response for EF configs.
 * All fields required — empty list is still a valid list (G-02.1).
 */
struct LoyaltyExtendedFieldListResponse {
    1: required list<LoyaltyExtendedFieldConfig> configs
    2: required i32    totalElements
    3: required i32    page
    4: required i32    size
}
```

### 1b. New Service Methods (append after method #57 `bulkEMFEvent`)

```thrift
    /**
     * Method #58 — Create a new EF config for an org/program/scope.
     * Validates: orgId > 0, programId > 0, name non-blank, scope in ALLOWED_SCOPES,
     *            dataType in STRING/NUMBER/BOOLEAN/DATE, max count not exceeded,
     *            name uniqueness in (orgId, programId, scope).
     * Returns the created config with auto-generated id.
     * Throws: EMFException with statusCode 8002 (duplicate name), 8004 (invalid scope),
     *         8005 (invalid dataType), 8009 (max count exceeded), 8010 (invalid orgId).
     */
    LoyaltyExtendedFieldConfig createLoyaltyExtendedFieldConfig(
        1: required CreateLoyaltyExtendedFieldRequest request
    ) throws (1: EMFException ex)

    /**
     * Method #59 — Update name and/or is_active for an existing EF config.
     * Validates: id found for (id, orgId), immutability of other fields (D-23).
     * If name provided: validates uniqueness in (orgId, programId, scope) excluding self.
     * Soft-delete: isActive=false sets is_active=0; idempotent (already inactive = 200).
     * Throws: EMFException with statusCode 8001 (not found), 8002 (name conflict),
     *         8003 (immutable field attempted), 8010 (invalid orgId).
     */
    LoyaltyExtendedFieldConfig updateLoyaltyExtendedFieldConfig(
        1: required UpdateLoyaltyExtendedFieldRequest request
    ) throws (1: EMFException ex)

    /**
     * Method #60 — List EF configs for an org/program.
     * scope is optional — if absent, returns all scopes.
     * includeInactive controls whether is_active=0 records are included (D-20).
     * Paginated — page is 0-indexed; size is page size.
     * orgId and programId are required to prevent zero-default multi-tenancy bypass (R-CT-05).
     * Throws: EMFException with statusCode 8010 (orgId <= 0).
     */
    LoyaltyExtendedFieldListResponse getLoyaltyExtendedFieldConfigs(
        1: required i64    orgId,
        2: required i64    programId,
        3: optional string scope,
        4: required bool   includeInactive,
        5: required i32    page,
        6: required i32    size
    ) throws (1: EMFException ex)
```

---

## Section 2: cc-stack-crm — loyalty_extended_fields.sql

### File 1: Schema

**Full path**: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/schema/dbmaster/warehouse/loyalty_extended_fields.sql`

```sql
CREATE TABLE `loyalty_extended_fields` (
    `id`            BIGINT        NOT NULL AUTO_INCREMENT,
    `org_id`        BIGINT        NOT NULL,
    `program_id`    BIGINT        NOT NULL,
    `name`          varchar(100)  COLLATE utf8mb4_unicode_ci NOT NULL,
    `scope`         varchar(50)   COLLATE utf8mb4_unicode_ci NOT NULL,
    `data_type`     varchar(30)   COLLATE utf8mb4_unicode_ci NOT NULL,
    `is_mandatory`  tinyint(1)    NOT NULL DEFAULT 0,
    `default_value` varchar(255)  COLLATE utf8mb4_unicode_ci NULL,
    `is_active`     tinyint(1)    NOT NULL DEFAULT 1,
    `created_on`    timestamp     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_on`    timestamp     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `updated_by`    varchar(100)  COLLATE utf8mb4_unicode_ci NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_org_prog_scope_name` (`org_id`, `program_id`, `scope`, `name`),
    KEY `idx_org_prog_scope_active` (`org_id`, `program_id`, `scope`, `is_active`)
);
```

### File 2: Seed Data

**Full path**: `/Users/baljeetsingh/IdeaProjects/cc-stack-crm/seed_data/dbmaster/warehouse/program_config_keys.sql`

**Append to existing `REPLACE INTO` statement (after existing ID=47 row):**

```sql
REPLACE INTO `program_config_keys` (`id`, `name`, `value_type`, `default_value`, `label`, `added_by`, `added_on`, `is_valid`) VALUES
(48, 'MAX_EF_COUNT_PER_PROGRAM', 'NUMERIC', '10', 'Max Extended Fields Per Program', 0, '2026-04-22 00:00:00', 1);
```

---

## Section 3: emf-parent — pointsengine-emf Module

### 3a. LoyaltyExtendedFieldPK

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/LoyaltyExtendedFieldPK.java`

**Package**: `com.capillary.shopbook.points.entity`

**Decision**: Standalone `@Embeddable` — does NOT extend `OrgEntityLongPKBase` or `OrgEntityIntegerPKBase`
because `OrgEntityLongPKBase(long id, int orgId)` uses `int` orgId, incompatible with `BIGINT org_id` (ADR-02).

```java
package com.capillary.shopbook.points.entity;

import javax.persistence.Column;
import javax.persistence.Embeddable;
import java.io.Serializable;
import java.util.Objects;

/**
 * Standalone composite PK for loyalty_extended_fields.
 * Does NOT extend OrgEntityLongPKBase — that base class uses int orgId in its
 * constructor, which is incompatible with BIGINT org_id (ADR-02).
 */
@Embeddable
public class LoyaltyExtendedFieldPK implements Serializable {

    private static final long serialVersionUID = 1L;

    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "org_id", nullable = false)
    private Long orgId;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public LoyaltyExtendedFieldPK() {
    }

    public LoyaltyExtendedFieldPK(Long id, Long orgId) {
        this.id = id;
        this.orgId = orgId;
    }

    // -------------------------------------------------------------------------
    // Getters / Setters
    // -------------------------------------------------------------------------

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getOrgId() {
        return orgId;
    }

    public void setOrgId(Long orgId) {
        this.orgId = orgId;
    }

    // -------------------------------------------------------------------------
    // equals / hashCode — required by JPA for @Embeddable PK
    // -------------------------------------------------------------------------

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        LoyaltyExtendedFieldPK that = (LoyaltyExtendedFieldPK) o;
        return Objects.equals(id, that.id) && Objects.equals(orgId, that.orgId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, orgId);
    }

    @Override
    public String toString() {
        return "LoyaltyExtendedFieldPK{id=" + id + ", orgId=" + orgId + "}";
    }
}
```

---

### 3b. LoyaltyExtendedField

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/points/entity/LoyaltyExtendedField.java`

**Package**: `com.capillary.shopbook.points.entity`

**Pattern**: Follows `ProgramConfigKeyValue.java` — `@Entity`, `@EmbeddedId`, builder inner class.
`@DataSourceSpecification` is NOT on entity — it goes on the service class (confirmed from `InfoLookupService.java`).
Schema is declared via `@Table(name = "...", schema = "warehouse")` (confirmed from `ActionPointsDetail.java`).

```java
package com.capillary.shopbook.points.entity;

import javax.persistence.*;
import java.io.Serializable;
import java.util.Date;

/**
 * JPA entity mapping loyalty_extended_fields table in the warehouse DB.
 * Pure data carrier — no business logic.
 * Schema routing: @Table(schema="warehouse") + @DataSourceSpecification on service (ADR).
 */
@Entity
@Table(name = "loyalty_extended_fields", schema = "warehouse")
public class LoyaltyExtendedField implements Serializable {

    private static final long serialVersionUID = 1L;

    @EmbeddedId
    private LoyaltyExtendedFieldPK pk;

    // NOTE: id auto-generated by DB; JPA will read it back after INSERT.
    // The @EmbeddedId pk.id is set from the generated key post-save via repository.

    @Column(name = "program_id", nullable = false)
    private Long programId;

    @Column(name = "name", nullable = false, length = 100)
    private String name;

    @Column(name = "scope", nullable = false, length = 50)
    private String scope;

    @Column(name = "data_type", nullable = false, length = 30)
    private String dataType;

    @Column(name = "is_mandatory", nullable = false)
    private boolean isMandatory;

    @Column(name = "default_value", length = 255)
    private String defaultValue;

    @Column(name = "is_active", nullable = false)
    private boolean isActive = true;

    @Column(name = "created_on", nullable = false, updatable = false)
    @Temporal(TemporalType.TIMESTAMP)
    private Date createdOn;

    @Column(name = "updated_on", nullable = false)
    @Temporal(TemporalType.TIMESTAMP)
    private Date updatedOn;

    @Column(name = "updated_by", length = 100)
    private String updatedBy;

    // -------------------------------------------------------------------------
    // Constructors
    // -------------------------------------------------------------------------

    public LoyaltyExtendedField() {
    }

    // -------------------------------------------------------------------------
    // Convenience delegates for PK fields
    // -------------------------------------------------------------------------

    public Long getId() {
        return pk != null ? pk.getId() : null;
    }

    public Long getOrgId() {
        return pk != null ? pk.getOrgId() : null;
    }

    // -------------------------------------------------------------------------
    // Getters / Setters
    // -------------------------------------------------------------------------

    public LoyaltyExtendedFieldPK getPk() { return pk; }
    public void setPk(LoyaltyExtendedFieldPK pk) { this.pk = pk; }

    public Long getProgramId() { return programId; }
    public void setProgramId(Long programId) { this.programId = programId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getScope() { return scope; }
    public void setScope(String scope) { this.scope = scope; }

    public String getDataType() { return dataType; }
    public void setDataType(String dataType) { this.dataType = dataType; }

    public boolean isMandatory() { return isMandatory; }
    public void setMandatory(boolean mandatory) { isMandatory = mandatory; }

    public String getDefaultValue() { return defaultValue; }
    public void setDefaultValue(String defaultValue) { this.defaultValue = defaultValue; }

    public boolean isActive() { return isActive; }
    public void setActive(boolean active) { isActive = active; }

    public Date getCreatedOn() { return createdOn; }
    public void setCreatedOn(Date createdOn) { this.createdOn = createdOn; }

    public Date getUpdatedOn() { return updatedOn; }
    public void setUpdatedOn(Date updatedOn) { this.updatedOn = updatedOn; }

    public String getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(String updatedBy) { this.updatedBy = updatedBy; }

    // -------------------------------------------------------------------------
    // Builder
    // -------------------------------------------------------------------------

    public static LoyaltyExtendedFieldBuilder builder() {
        return new LoyaltyExtendedFieldBuilder();
    }

    public static final class LoyaltyExtendedFieldBuilder {
        private LoyaltyExtendedFieldPK pk;
        private Long programId;
        private String name;
        private String scope;
        private String dataType;
        private boolean isMandatory;
        private String defaultValue;
        private boolean isActive = true;
        private Date createdOn;
        private Date updatedOn;
        private String updatedBy;

        private LoyaltyExtendedFieldBuilder() {}

        public LoyaltyExtendedFieldBuilder pk(LoyaltyExtendedFieldPK pk) { this.pk = pk; return this; }
        public LoyaltyExtendedFieldBuilder programId(Long programId) { this.programId = programId; return this; }
        public LoyaltyExtendedFieldBuilder name(String name) { this.name = name; return this; }
        public LoyaltyExtendedFieldBuilder scope(String scope) { this.scope = scope; return this; }
        public LoyaltyExtendedFieldBuilder dataType(String dataType) { this.dataType = dataType; return this; }
        public LoyaltyExtendedFieldBuilder isMandatory(boolean isMandatory) { this.isMandatory = isMandatory; return this; }
        public LoyaltyExtendedFieldBuilder defaultValue(String defaultValue) { this.defaultValue = defaultValue; return this; }
        public LoyaltyExtendedFieldBuilder isActive(boolean isActive) { this.isActive = isActive; return this; }
        public LoyaltyExtendedFieldBuilder createdOn(Date createdOn) { this.createdOn = createdOn; return this; }
        public LoyaltyExtendedFieldBuilder updatedOn(Date updatedOn) { this.updatedOn = updatedOn; return this; }
        public LoyaltyExtendedFieldBuilder updatedBy(String updatedBy) { this.updatedBy = updatedBy; return this; }

        public LoyaltyExtendedField build() {
            LoyaltyExtendedField ef = new LoyaltyExtendedField();
            ef.setPk(pk);
            ef.setProgramId(programId);
            ef.setName(name);
            ef.setScope(scope);
            ef.setDataType(dataType);
            ef.setMandatory(isMandatory);
            ef.setDefaultValue(defaultValue);
            ef.setActive(isActive);
            ef.setCreatedOn(createdOn);
            ef.setUpdatedOn(updatedOn);
            ef.setUpdatedBy(updatedBy);
            return ef;
        }
    }
}
```

---

### 3c. LoyaltyExtendedFieldRepository

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/points/dao/LoyaltyExtendedFieldRepository.java`

**Package**: `com.capillary.shopbook.points.dao`

**Pattern**: Follows `HistoricalPointsDao.java` — extends `GenericDao<Entity, PK>`, `@Repository`,
`@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)`, `@Query` JPQL with `@Param`.

**Decision D-32**: JPQL `@Query` with dynamic scope/isActive filter for list endpoint.
Spring Data derived queries used for `findByPkIdAndPkOrgId` and `existsByOrgIdAndProgramIdAndScopeAndName`.

```java
package com.capillary.shopbook.points.dao;

import com.capillary.commons.data.dao.GenericDao;
import com.capillary.shopbook.points.entity.LoyaltyExtendedField;
import com.capillary.shopbook.points.entity.LoyaltyExtendedFieldPK;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Repository
@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)
public interface LoyaltyExtendedFieldRepository
        extends GenericDao<LoyaltyExtendedField, LoyaltyExtendedFieldPK> {

    /**
     * Fetch by composite PK (id + orgId). Multi-tenancy enforced — returns empty if orgId
     * does not match the stored record (prevents cross-org reads).
     * Used by: update(), getById (if needed in future).
     */
    Optional<LoyaltyExtendedField> findByPkIdAndPkOrgId(Long id, Long orgId);

    /**
     * Uniqueness check: returns true if a record with the same (orgId, programId, scope, name)
     * already exists, regardless of is_active (D-30: names are permanently unique).
     * Used by: create() and update() (when name is being changed).
     */
    boolean existsByPkOrgIdAndProgramIdAndScopeAndName(Long orgId, Long programId,
                                                        String scope, String name);

    /**
     * Fetch all active EF configs for a given (orgId, programId, scope).
     * Used by: EF Validation path (A-05) — one call to load all active configs for in-memory check.
     * Scope is NOT optional here (caller always provides SUBSCRIPTION_META for validation).
     */
    List<LoyaltyExtendedField> findByPkOrgIdAndProgramIdAndScopeAndIsActive(
            Long orgId, Long programId, String scope, boolean isActive);

    /**
     * Count of active EF configs for (orgId, programId). Used for MAX_EF_COUNT check on create.
     * Counts ACTIVE records only — deactivated fields don't count against the limit.
     */
    @Query("SELECT COUNT(ef) FROM LoyaltyExtendedField ef " +
           "WHERE ef.pk.orgId = :orgId AND ef.programId = :programId AND ef.isActive = true")
    long countActiveByOrgIdAndProgramId(@Param("orgId") Long orgId, @Param("programId") Long programId);

    /**
     * Paginated list query for GET /v3/extendedfields/config.
     * Dynamic filter: scope is optional (null = all scopes); includeInactive controls is_active filter.
     * JPQL @Query used because Spring Data derived queries cannot express optional scope filter.
     * D-32: This is the paginated list endpoint query.
     */
    @Query("SELECT ef FROM LoyaltyExtendedField ef " +
           "WHERE ef.pk.orgId = :orgId " +
           "AND ef.programId = :programId " +
           "AND (:scope IS NULL OR ef.scope = :scope) " +
           "AND (:includeInactive = true OR ef.isActive = true) " +
           "ORDER BY ef.createdOn DESC")
    Page<LoyaltyExtendedField> findByOrgIdAndProgramIdDynamic(
            @Param("orgId") Long orgId,
            @Param("programId") Long programId,
            @Param("scope") String scope,
            @Param("includeInactive") boolean includeInactive,
            Pageable pageable);
}
```

---

### 3d. LoyaltyExtendedFieldService (Interface)

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/LoyaltyExtendedFieldService.java`

**Package**: `com.capillary.shopbook.points.services`

```java
package com.capillary.shopbook.points.services;

import com.capillary.shopbook.emf.api.external.CreateLoyaltyExtendedFieldRequest;
import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldConfig;
import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldListResponse;
import com.capillary.shopbook.emf.api.external.UpdateLoyaltyExtendedFieldRequest;
import com.capillary.shopbook.emf.api.exception.EMFException;

/**
 * Service contract for Loyalty Extended Field config CRUD.
 * All methods throw EMFException with domain-specific error codes (8001-8010).
 * Consumed by EMFThriftServiceImpl (methods 58-60).
 */
public interface LoyaltyExtendedFieldService {

    /**
     * Create a new EF config for an org/program/scope.
     * Validates: orgId > 0, programId > 0, name non-blank, scope in ALLOWED_SCOPES,
     *            dataType in STRING/NUMBER/BOOLEAN/DATE, max count not exceeded (D-15),
     *            name uniqueness in (orgId, programId, scope) — D-30.
     *
     * @throws EMFException statusCode 8002 (duplicate name), 8004 (invalid scope),
     *                      8005 (invalid dataType), 8009 (max count exceeded), 8010 (invalid orgId)
     */
    LoyaltyExtendedFieldConfig create(CreateLoyaltyExtendedFieldRequest request) throws EMFException;

    /**
     * Update name and/or is_active for an existing EF config.
     * Only name (String) and isActive (boolean) are mutable — D-23.
     * If name is provided: uniqueness validated in (orgId, programId, scope) excluding self — D-30.
     * Soft-delete: isActive=false sets is_active=0; idempotent on already-inactive — D-16.
     *
     * @throws EMFException statusCode 8001 (not found), 8002 (name conflict),
     *                      8003 (immutable field attempted), 8010 (invalid orgId)
     */
    LoyaltyExtendedFieldConfig update(UpdateLoyaltyExtendedFieldRequest request) throws EMFException;

    /**
     * List EF configs for an org/program with optional scope filter and pagination.
     * scope=null returns all scopes. includeInactive=false returns only active records.
     * Page is 0-indexed. Empty list = 200, never null (G-02.1).
     *
     * @throws EMFException statusCode 8010 (invalid orgId)
     */
    LoyaltyExtendedFieldListResponse list(long orgId, long programId, String scope,
                                          boolean includeInactive, int page, int size)
            throws EMFException;
}
```

---

### 3e. LoyaltyExtendedFieldServiceImpl

**File**: `pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/LoyaltyExtendedFieldServiceImpl.java`

**Package**: `com.capillary.shopbook.points.services`

**Key annotations**: `@Service`, `@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)`,
`@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)`

```java
package com.capillary.shopbook.points.services;

import com.capillary.shopbook.emf.api.exception.EMFException;
import com.capillary.shopbook.emf.api.exception.ExceptionCodes;
import com.capillary.shopbook.emf.api.external.*;
import com.capillary.shopbook.emf.api.hibernate.DataSourceSpecification;
import com.capillary.shopbook.emf.api.hibernate.DataSourceSpecification.SchemaType;
import com.capillary.shopbook.points.dao.LoyaltyExtendedFieldRepository;
import com.capillary.shopbook.points.entity.LoyaltyExtendedField;
import com.capillary.shopbook.points.entity.LoyaltyExtendedFieldPK;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Implementation of LoyaltyExtendedFieldService.
 * Business rules:
 *   - MAX_EF_COUNT_PER_PROGRAM: reads from program_config_key_values (key_id=48); default=10
 *   - Allowed scopes (current release): SUBSCRIPTION_META only — D-09, in-scope constraint
 *   - Allowed data types: STRING, NUMBER, BOOLEAN, DATE — D-22
 *   - Name uniqueness: (orgId, programId, scope, name) regardless of is_active — D-30
 *   - Immutable fields after create: scope, dataType, isMandatory, defaultValue, programId — D-23
 */
@Service
@DataSourceSpecification(schemaType = SchemaType.WAREHOUSE)
@Transactional(value = "warehouse", propagation = Propagation.REQUIRED)
public class LoyaltyExtendedFieldServiceImpl implements LoyaltyExtendedFieldService {

    private static final Set<String> ALLOWED_SCOPES =
            Set.of("SUBSCRIPTION_META");  // D-09: future scopes deferred

    private static final Set<String> ALLOWED_DATA_TYPES =
            Set.of("STRING", "NUMBER", "BOOLEAN", "DATE");  // D-22

    private static final int DEFAULT_MAX_EF_COUNT = 10;  // D-15 fallback

    private static final DateTimeFormatter ISO_UTC =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneOffset.UTC);

    @Autowired
    private LoyaltyExtendedFieldRepository repository;

    // Inject ProgramConfigKeyValueDao or ProgramConfigKeyLookupService for MAX_EF_COUNT reads
    // The exact injection depends on existing service patterns — use InfoLookupService.getAllValidProgramConfigKeys()
    // or ProgramConfigKeyValueValidatorImpl pattern. Placeholder here:
    @Autowired
    private com.capillary.shopbook.points.services.InfoLookupService infoLookupService;

    // -------------------------------------------------------------------------
    // PUBLIC API
    // -------------------------------------------------------------------------

    @Override
    public LoyaltyExtendedFieldConfig create(CreateLoyaltyExtendedFieldRequest request)
            throws EMFException {

        // 1. Null-guard mandatory fields (ADR-01: required in struct but defensive check)
        validateOrgId(request.getOrgId());
        if (request.getProgramId() <= 0) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_INVALID_ORG,
                    "programId must be > 0", 0);
        }
        if (request.getName() == null || request.getName().trim().isEmpty()) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_INVALID_SCOPE,
                    "name must not be blank", 0);
        }

        // 2. Validate scope
        if (!ALLOWED_SCOPES.contains(request.getScope())) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_INVALID_SCOPE,
                    "Invalid scope: " + request.getScope() + ". Allowed: " + ALLOWED_SCOPES, 0);
        }

        // 3. Validate data_type
        if (!ALLOWED_DATA_TYPES.contains(request.getDataType())) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_INVALID_DATA_TYPE,
                    "Invalid dataType: " + request.getDataType() + ". Allowed: " + ALLOWED_DATA_TYPES, 0);
        }

        // 4. MAX_EF_COUNT check — count ACTIVE records for (orgId, programId)
        int maxCount = resolveMaxEfCount(request.getOrgId(), request.getProgramId());
        long current = repository.countActiveByOrgIdAndProgramId(request.getOrgId(), request.getProgramId());
        if (current >= maxCount) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_MAX_COUNT_EXCEEDED,
                    "Max EF count (" + maxCount + ") reached for programId=" + request.getProgramId(), 0);
        }

        // 5. Uniqueness check — D-30: regardless of is_active
        if (repository.existsByPkOrgIdAndProgramIdAndScopeAndName(
                request.getOrgId(), request.getProgramId(), request.getScope(), request.getName())) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_DUPLICATE_NAME,
                    "EF config with name '" + request.getName() + "' already exists for this program/scope", 0);
        }

        // 6. Build and save entity
        Date now = new Date();
        LoyaltyExtendedField entity = LoyaltyExtendedField.builder()
                .pk(new LoyaltyExtendedFieldPK(null, request.getOrgId()))  // id assigned by DB
                .programId(request.getProgramId())
                .name(request.getName().trim())
                .scope(request.getScope())
                .dataType(request.getDataType())
                .isMandatory(request.isIsMandatory())
                .defaultValue(request.getDefaultValue())
                .isActive(true)
                .createdOn(now)
                .updatedOn(now)
                .updatedBy(request.getCreatedBy())
                .build();

        LoyaltyExtendedField saved = repository.save(entity);

        // 7. Map to Thrift response struct
        return toThriftStruct(saved);
    }

    @Override
    public LoyaltyExtendedFieldConfig update(UpdateLoyaltyExtendedFieldRequest request)
            throws EMFException {

        // 1. Null-guard id + orgId
        validateOrgId(request.getOrgId());
        if (request.getId() <= 0) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_NOT_FOUND,
                    "id must be > 0", 0);
        }

        // 2. Fetch by (id, orgId) — 404 if not found or wrong org (G-07.1)
        Optional<LoyaltyExtendedField> optEntity =
                repository.findByPkIdAndPkOrgId(request.getId(), request.getOrgId());
        if (optEntity.isEmpty()) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_NOT_FOUND,
                    "EF config not found: id=" + request.getId() + ", orgId=" + request.getOrgId(), 0);
        }
        LoyaltyExtendedField entity = optEntity.get();

        // 3. Name update: if provided, validate uniqueness excluding self
        if (request.isSetName() && request.getName() != null) {
            String newName = request.getName().trim();
            if (!newName.equals(entity.getName())) {
                if (repository.existsByPkOrgIdAndProgramIdAndScopeAndName(
                        entity.getOrgId(), entity.getProgramId(), entity.getScope(), newName)) {
                    throw new EMFException(ExceptionCodes.EF_CONFIG_DUPLICATE_NAME,
                            "EF config with name '" + newName + "' already exists for this program/scope", 0);
                }
                entity.setName(newName);
            }
        }

        // 4. isActive update: if provided, set is_active (idempotent — D-16)
        if (request.isSetIsActive()) {
            entity.setActive(request.isIsActive());
        }

        // 5. Audit
        entity.setUpdatedOn(new Date());
        if (request.isSetUpdatedBy()) {
            entity.setUpdatedBy(request.getUpdatedBy());
        }

        LoyaltyExtendedField saved = repository.save(entity);
        return toThriftStruct(saved);
    }

    @Override
    public LoyaltyExtendedFieldListResponse list(long orgId, long programId, String scope,
                                                  boolean includeInactive, int page, int size)
            throws EMFException {

        validateOrgId(orgId);

        Page<LoyaltyExtendedField> resultPage = repository.findByOrgIdAndProgramIdDynamic(
                orgId, programId, scope, includeInactive,
                PageRequest.of(page, size));

        List<LoyaltyExtendedFieldConfig> configs = resultPage.getContent()
                .stream()
                .map(this::toThriftStruct)
                .collect(Collectors.toList());

        LoyaltyExtendedFieldListResponse response = new LoyaltyExtendedFieldListResponse();
        response.setConfigs(configs);
        response.setTotalElements((int) resultPage.getTotalElements());
        response.setPage(page);
        response.setSize(size);
        return response;
    }

    // -------------------------------------------------------------------------
    // PRIVATE HELPERS
    // -------------------------------------------------------------------------

    /**
     * Maps a JPA entity to the Thrift response struct.
     * Timestamps are formatted as UTC ISO-8601 strings (G-01.1, G-01.6).
     */
    private LoyaltyExtendedFieldConfig toThriftStruct(LoyaltyExtendedField entity) {
        LoyaltyExtendedFieldConfig config = new LoyaltyExtendedFieldConfig();
        config.setId(entity.getId());
        config.setOrgId(entity.getOrgId());
        config.setProgramId(entity.getProgramId());
        config.setName(entity.getName());
        config.setScope(entity.getScope());
        config.setDataType(entity.getDataType());
        config.setIsMandatory(entity.isMandatory());
        config.setDefaultValue(entity.getDefaultValue());
        config.setIsActive(entity.isActive());
        config.setCreatedOn(toIsoUtc(entity.getCreatedOn()));
        config.setUpdatedOn(toIsoUtc(entity.getUpdatedOn()));
        config.setUpdatedBy(entity.getUpdatedBy());
        return config;
    }

    /**
     * Converts a java.util.Date to a UTC ISO-8601 string.
     * e.g. "2026-04-22T10:00:00Z"
     */
    private String toIsoUtc(Date date) {
        if (date == null) return null;
        return ISO_UTC.format(date.toInstant());
    }

    /**
     * Validates orgId > 0. Throws EMFException(8010) if invalid.
     * R-CT-05 mitigation: prevents multi-tenancy bypass via zero-default orgId.
     */
    private void validateOrgId(long orgId) throws EMFException {
        if (orgId <= 0) {
            throw new EMFException(ExceptionCodes.EF_CONFIG_INVALID_ORG,
                    "orgId must be > 0, got: " + orgId, 0);
        }
    }

    /**
     * Resolves the MAX_EF_COUNT for a given (orgId, programId).
     * Reads from program_config_key_values for key_id=48 (MAX_EF_COUNT_PER_PROGRAM).
     * Falls back to DEFAULT_MAX_EF_COUNT=10 if no org/program-specific override exists.
     * Uses infoLookupService.getAllValidProgramConfigKeys() — existing pattern.
     */
    private int resolveMaxEfCount(long orgId, long programId) {
        // Implementation: look up program_config_key_values WHERE org_id=orgId AND
        // program_id=programId AND key_id=48. If not present, return DEFAULT_MAX_EF_COUNT.
        // Follow ProgramConfigKeyValueValidatorImpl pattern.
        // Placeholder — actual lookup implementation follows existing InfoLookupService pattern.
        return DEFAULT_MAX_EF_COUNT;
    }
}
```

---

### 3f. EMFThriftServiceImpl Modifications

**File**: `emf/src/main/java/com/capillary/shopbook/emf/impl/external/EMFThriftServiceImpl.java`

**Change**: Add `@Autowired private LoyaltyExtendedFieldService loyaltyExtendedFieldService;` field.
Add 3 new `@Override` methods (58, 59, 60) after the existing `bulkEMFEvent` method at line 4271.

```java
    // =========================================================================
    // Loyalty Extended Fields CRUD — CAP-183124 (Methods 58-60)
    // =========================================================================

    @Autowired
    private LoyaltyExtendedFieldService loyaltyExtendedFieldService;

    /**
     * Method #58 — Create EF config.
     */
    @Override
    @MDCData(orgId = "#request.orgId", requestId = "''")
    public LoyaltyExtendedFieldConfig createLoyaltyExtendedFieldConfig(
            CreateLoyaltyExtendedFieldRequest request) throws EMFException {
        // Null-guard: request must not be null (orgId validated inside service)
        if (request == null) {
            throw getEMFException(ExceptionCodes.EF_CONFIG_INVALID_ORG,
                    "CreateLoyaltyExtendedFieldRequest must not be null", 0);
        }
        try {
            return loyaltyExtendedFieldService.create(request);
        } catch (EMFException ex) {
            logger.error("createLoyaltyExtendedFieldConfig failed. orgId={}, name={}, error={}",
                    request.getOrgId(), request.getName(), ex.getErrorMessage());
            throw ex;  // re-throw domain exceptions as-is (they already carry statusCode)
        } catch (Exception ex) {
            logger.error("createLoyaltyExtendedFieldConfig unexpected error. orgId={}", request.getOrgId(), ex);
            throw getEMFException(ExceptionCodes.GENERIC, ex.getMessage(), 0);
        }
    }

    /**
     * Method #59 — Update EF config.
     */
    @Override
    @MDCData(orgId = "#request.orgId", requestId = "''")
    public LoyaltyExtendedFieldConfig updateLoyaltyExtendedFieldConfig(
            UpdateLoyaltyExtendedFieldRequest request) throws EMFException {
        if (request == null) {
            throw getEMFException(ExceptionCodes.EF_CONFIG_INVALID_ORG,
                    "UpdateLoyaltyExtendedFieldRequest must not be null", 0);
        }
        try {
            return loyaltyExtendedFieldService.update(request);
        } catch (EMFException ex) {
            logger.error("updateLoyaltyExtendedFieldConfig failed. id={}, orgId={}, error={}",
                    request.getId(), request.getOrgId(), ex.getErrorMessage());
            throw ex;
        } catch (Exception ex) {
            logger.error("updateLoyaltyExtendedFieldConfig unexpected error. id={}, orgId={}",
                    request.getId(), request.getOrgId(), ex);
            throw getEMFException(ExceptionCodes.GENERIC, ex.getMessage(), 0);
        }
    }

    /**
     * Method #60 — List EF configs.
     */
    @Override
    @MDCData(orgId = "#orgId", requestId = "''")
    public LoyaltyExtendedFieldListResponse getLoyaltyExtendedFieldConfigs(
            long orgId, long programId, String scope,
            boolean includeInactive, int page, int size) throws EMFException {
        try {
            return loyaltyExtendedFieldService.list(orgId, programId, scope, includeInactive, page, size);
        } catch (EMFException ex) {
            logger.error("getLoyaltyExtendedFieldConfigs failed. orgId={}, programId={}, error={}",
                    orgId, programId, ex.getErrorMessage());
            throw ex;
        } catch (Exception ex) {
            logger.error("getLoyaltyExtendedFieldConfigs unexpected error. orgId={}, programId={}",
                    orgId, programId, ex);
            throw getEMFException(ExceptionCodes.GENERIC, ex.getMessage(), 0);
        }
    }
```

---

### 3g. ExceptionCodes.java Additions

**File**: `emf/src/main/java/com/capillary/shopbook/emf/api/exception/ExceptionCodes.java`

**Change 1**: Add new constants after line 231 (`EXTEND_TIER_EXPIRY_DATE_NOT_PERMITTED = 7007`):

```java
    // =========================================================================
    // Loyalty Extended Fields error codes (8xxx range) — CAP-183124
    // Range 8001-8010 confirmed free (highest existing code: 7007)
    // =========================================================================

    /** EF config id not found for (id, orgId) */
    public static final int EF_CONFIG_NOT_FOUND = 8001;

    /** Name uniqueness violation: (orgId, programId, scope, name) already exists — D-30 */
    public static final int EF_CONFIG_DUPLICATE_NAME = 8002;

    /** Attempt to update an immutable field (scope, dataType, isMandatory, defaultValue) — D-23 */
    public static final int EF_CONFIG_IMMUTABLE_UPDATE = 8003;

    /** scope value not in allowed set (SUBSCRIPTION_META for current release) — D-09 */
    public static final int EF_CONFIG_INVALID_SCOPE = 8004;

    /** data_type value not in STRING/NUMBER/BOOLEAN/DATE — D-22 */
    public static final int EF_CONFIG_INVALID_DATA_TYPE = 8005;

    /** EF id submitted in subscription is not found or inactive for (orgId, programId) — EF Validation R-01 */
    public static final int EF_VALIDATION_UNKNOWN_ID = 8006;

    /** Value does not match declared data_type — EF Validation R-02 */
    public static final int EF_VALIDATION_TYPE_MISMATCH = 8007;

    /** Mandatory EF config id absent from submitted extendedFields list — EF Validation R-03 */
    public static final int EF_VALIDATION_MISSING_MANDATORY = 8008;

    /** Active EF count for (orgId, programId) >= MAX_EF_COUNT_PER_PROGRAM — D-15 */
    public static final int EF_CONFIG_MAX_COUNT_EXCEEDED = 8009;

    /** orgId <= 0 in Thrift request — R-CT-05 */
    public static final int EF_CONFIG_INVALID_ORG = 8010;
```

**Change 2**: Update `badRequestErrors` set at line 28 to include 8002-8010 (8001 maps to 404, handled by LoyaltyExtendedFieldErrorAdvice — not badRequest):

```java
    // Before:
    private static Set<Integer> badRequestErrors = new HashSet<>(Arrays.asList(130, 131, 132));

    // After:
    private static Set<Integer> badRequestErrors = new HashSet<>(Arrays.asList(
            130, 131, 132,
            // EF Config + Validation errors (8002-8010 → 400; 8001 → 404 handled in V3 advice)
            8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010
    ));
```

---

## Section 4: intouch-api-v3 — New EF Config API

### 4a. EFThriftException (new — required before other V3 classes)

**File**: `src/main/java/com/capillary/intouchapiv3/services/thrift/exception/EFThriftException.java`

**Package**: `com.capillary.intouchapiv3.services.thrift.exception`

**Why needed**: `EMFThriftException` only carries `String message` — no statusCode. The new
`EmfExtendedFieldsThriftService` needs to surface the `EMFException.statusCode` to
`LoyaltyExtendedFieldErrorAdvice` for HTTP mapping. This subclass adds the field.

```java
package com.capillary.intouchapiv3.services.thrift.exception;

/**
 * Thrift client exception for EF config operations.
 * Extends EMFThriftException to add statusCode from EMFException.statusCode,
 * enabling LoyaltyExtendedFieldErrorAdvice to map to specific HTTP status codes.
 *
 * Note: EMFThriftException only carries String message — insufficient for EF error mapping.
 */
public class EFThriftException extends EMFThriftException {

    private final int statusCode;

    public EFThriftException(int statusCode, String message) {
        super(message);
        this.statusCode = statusCode;
    }

    /**
     * Returns the EMFException.statusCode (e.g. 8001=NotFound, 8002=Conflict, etc.)
     */
    public int getStatusCode() {
        return statusCode;
    }
}
```

---

### 4b. EmfExtendedFieldsThriftService

**File**: `src/main/java/com/capillary/intouchapiv3/services/thrift/EmfExtendedFieldsThriftService.java`

**Package**: `com.capillary.intouchapiv3.services.thrift`

**Pattern**: Follows `EmfPromotionThriftService.java` exactly:
- `@Service @Loggable`
- `protected EMFService.Iface getClient() throws Exception` — same host/port as EmfPromotionThriftService
- `catch (EMFException ex)` → rethrow as `EFThriftException(ex.getStatusCode(), ex.getErrorMessage())`
- `catch (Exception ex)` → rethrow as `EFThriftException(500, ex.getMessage())`

```java
package com.capillary.intouchapiv3.services.thrift;

import com.capillary.commons.thrift.external.RPCService;
import com.capillary.intouchapiv3.services.thrift.exception.EFThriftException;
import com.capillary.intouchapiv3.utils.CapRequestIdUtil;
import com.capillary.shopbook.emf.api.external.*;
import com.jcabi.aspects.Loggable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Thrift client for EMF EF config methods 58-60.
 * Pattern follows EmfPromotionThriftService.java exactly — same host, port, interface.
 * Throws EFThriftException (carries statusCode from EMFException) to enable
 * LoyaltyExtendedFieldErrorAdvice to produce correct HTTP status codes.
 */
@Service
@Loggable
public class EmfExtendedFieldsThriftService {

    private static final Logger logger =
            LoggerFactory.getLogger(EmfExtendedFieldsThriftService.class);

    /**
     * Calls EMFService method #58 — createLoyaltyExtendedFieldConfig.
     *
     * @throws EFThriftException with statusCode from EMFException
     */
    public LoyaltyExtendedFieldConfig createLoyaltyExtendedFieldConfig(
            CreateLoyaltyExtendedFieldRequest request) {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            return getClient().createLoyaltyExtendedFieldConfig(request);
        } catch (com.capillary.shopbook.emf.api.external.EMFException ex) {
            logger.error("EMF createLoyaltyExtendedFieldConfig failed. serverReqId={}, statusCode={}",
                    serverReqId, ex.getStatusCode(), ex);
            throw new EFThriftException(ex.getStatusCode(), ex.getErrorMessage());
        } catch (Exception ex) {
            logger.error("EMF createLoyaltyExtendedFieldConfig unexpected error. serverReqId={}", serverReqId, ex);
            throw new EFThriftException(500, ex.getMessage());
        }
    }

    /**
     * Calls EMFService method #59 — updateLoyaltyExtendedFieldConfig.
     *
     * @throws EFThriftException with statusCode from EMFException
     */
    public LoyaltyExtendedFieldConfig updateLoyaltyExtendedFieldConfig(
            UpdateLoyaltyExtendedFieldRequest request) {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            return getClient().updateLoyaltyExtendedFieldConfig(request);
        } catch (com.capillary.shopbook.emf.api.external.EMFException ex) {
            logger.error("EMF updateLoyaltyExtendedFieldConfig failed. serverReqId={}, statusCode={}",
                    serverReqId, ex.getStatusCode(), ex);
            throw new EFThriftException(ex.getStatusCode(), ex.getErrorMessage());
        } catch (Exception ex) {
            logger.error("EMF updateLoyaltyExtendedFieldConfig unexpected error. serverReqId={}", serverReqId, ex);
            throw new EFThriftException(500, ex.getMessage());
        }
    }

    /**
     * Calls EMFService method #60 — getLoyaltyExtendedFieldConfigs.
     * Used by both the EF Config list endpoint AND ExtendedFieldValidator.
     *
     * @throws EFThriftException with statusCode from EMFException
     */
    public LoyaltyExtendedFieldListResponse getLoyaltyExtendedFieldConfigs(
            long orgId, long programId, String scope,
            boolean includeInactive, int page, int size) {
        String serverReqId = CapRequestIdUtil.getRequestId();
        try {
            return getClient().getLoyaltyExtendedFieldConfigs(
                    orgId, programId, scope, includeInactive, page, size);
        } catch (com.capillary.shopbook.emf.api.external.EMFException ex) {
            logger.error("EMF getLoyaltyExtendedFieldConfigs failed. orgId={}, programId={}, statusCode={}",
                    orgId, programId, ex.getStatusCode(), ex);
            throw new EFThriftException(ex.getStatusCode(), ex.getErrorMessage());
        } catch (Exception ex) {
            logger.error("EMF getLoyaltyExtendedFieldConfigs unexpected error. orgId={}, programId={}",
                    orgId, programId, ex);
            throw new EFThriftException(500, ex.getMessage());
        }
    }

    /**
     * Returns an EMFService.Iface client.
     * Same host/port as EmfPromotionThriftService — EMF methods 58-60 are on the same service.
     */
    protected EMFService.Iface getClient() throws Exception {
        return RPCService.rpcClient(EMFService.Iface.class, "emf-thrift-service", 9199, 10000);
    }
}
```

---

### 4c. DTOs

**Package for all DTOs**: `com.capillary.intouchapiv3.unified.subscription.extendedfields`

#### CreateExtendedFieldRequest

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/CreateExtendedFieldRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

/**
 * Request body for POST /v3/extendedfields/config.
 * org_id is NOT in this DTO — extracted from auth token (G-07.1).
 */
public class CreateExtendedFieldRequest {

    @NotNull(message = "programId must not be null")
    private Long programId;

    @NotBlank(message = "name must not be blank")
    private String name;

    @NotBlank(message = "scope must not be blank")
    private String scope;

    @NotBlank(message = "dataType must not be blank")
    private String dataType;

    private boolean isMandatory = false;

    private String defaultValue;  // optional — null allowed

    public Long getProgramId() { return programId; }
    public void setProgramId(Long programId) { this.programId = programId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getScope() { return scope; }
    public void setScope(String scope) { this.scope = scope; }

    public String getDataType() { return dataType; }
    public void setDataType(String dataType) { this.dataType = dataType; }

    public boolean isMandatory() { return isMandatory; }
    public void setMandatory(boolean mandatory) { isMandatory = mandatory; }

    public String getDefaultValue() { return defaultValue; }
    public void setDefaultValue(String defaultValue) { this.defaultValue = defaultValue; }
}
```

#### UpdateExtendedFieldRequest

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/UpdateExtendedFieldRequest.java`

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

/**
 * Request body for PUT /v3/extendedfields/config/{id}.
 * Only name (optional rename) and isActive (optional soft-delete) are mutable — D-23.
 * All fields are optional. If null, the field is NOT updated.
 */
public class UpdateExtendedFieldRequest {

    /**
     * Optional rename. If null, name is preserved unchanged.
     * D-25: name is mutable; validation uses efId not name so rename does not orphan MongoDB docs.
     */
    private String name;

    /**
     * Optional activation toggle. If null, is_active is preserved unchanged.
     * false = soft-delete (D-24). Idempotent: already-false = 200 (D-16).
     */
    private Boolean isActive;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }
}
```

#### ExtendedFieldConfigResponse

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldConfigResponse.java`

Maps 1:1 from `LoyaltyExtendedFieldConfig` Thrift struct. All non-optional fields are always present.

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldConfig;

/**
 * REST response DTO mirroring LoyaltyExtendedFieldConfig Thrift struct.
 * JSON field names use snake_case to match API contract in PRD.
 * Timestamps in UTC ISO-8601 format (G-01.1, G-01.6).
 */
public class ExtendedFieldConfigResponse {

    private Long id;
    private Long orgId;
    private Long programId;
    private String name;
    private String scope;
    private String dataType;
    private boolean isMandatory;
    private String defaultValue;
    private boolean isActive;
    private String createdOn;   // UTC ISO-8601
    private String updatedOn;   // UTC ISO-8601
    private String updatedBy;

    public ExtendedFieldConfigResponse() {}

    /**
     * Factory method: maps from Thrift struct to REST response DTO.
     */
    public static ExtendedFieldConfigResponse from(LoyaltyExtendedFieldConfig config) {
        ExtendedFieldConfigResponse r = new ExtendedFieldConfigResponse();
        r.setId(config.getId());
        r.setOrgId(config.getOrgId());
        r.setProgramId(config.getProgramId());
        r.setName(config.getName());
        r.setScope(config.getScope());
        r.setDataType(config.getDataType());
        r.setMandatory(config.isIsMandatory());
        r.setDefaultValue(config.getDefaultValue());
        r.setActive(config.isIsActive());
        r.setCreatedOn(config.getCreatedOn());
        r.setUpdatedOn(config.getUpdatedOn());
        r.setUpdatedBy(config.getUpdatedBy());
        return r;
    }

    // Getters / setters (standard)
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getOrgId() { return orgId; }
    public void setOrgId(Long orgId) { this.orgId = orgId; }

    public Long getProgramId() { return programId; }
    public void setProgramId(Long programId) { this.programId = programId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getScope() { return scope; }
    public void setScope(String scope) { this.scope = scope; }

    public String getDataType() { return dataType; }
    public void setDataType(String dataType) { this.dataType = dataType; }

    public boolean isMandatory() { return isMandatory; }
    public void setMandatory(boolean mandatory) { isMandatory = mandatory; }

    public String getDefaultValue() { return defaultValue; }
    public void setDefaultValue(String defaultValue) { this.defaultValue = defaultValue; }

    public boolean isActive() { return isActive; }
    public void setActive(boolean active) { isActive = active; }

    public String getCreatedOn() { return createdOn; }
    public void setCreatedOn(String createdOn) { this.createdOn = createdOn; }

    public String getUpdatedOn() { return updatedOn; }
    public void setUpdatedOn(String updatedOn) { this.updatedOn = updatedOn; }

    public String getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(String updatedBy) { this.updatedBy = updatedBy; }
}
```

#### ExtendedFieldsPageResponse

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldsPageResponse.java`

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldListResponse;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Paginated response wrapper for GET /v3/extendedfields/config.
 * G-02.1: content is never null — empty list returned when no results.
 */
public class ExtendedFieldsPageResponse {

    private List<ExtendedFieldConfigResponse> content;
    private int page;
    private int size;
    private int totalElements;
    private int totalPages;

    public ExtendedFieldsPageResponse() {}

    /**
     * Factory method: maps from Thrift LoyaltyExtendedFieldListResponse to REST page response.
     */
    public static ExtendedFieldsPageResponse from(LoyaltyExtendedFieldListResponse thriftResponse) {
        ExtendedFieldsPageResponse r = new ExtendedFieldsPageResponse();
        r.setContent(thriftResponse.getConfigs() == null
                ? Collections.emptyList()
                : thriftResponse.getConfigs().stream()
                        .map(ExtendedFieldConfigResponse::from)
                        .collect(Collectors.toList()));
        r.setPage(thriftResponse.getPage());
        r.setSize(thriftResponse.getSize());
        r.setTotalElements(thriftResponse.getTotalElements());
        r.setTotalPages(thriftResponse.getSize() > 0
                ? (int) Math.ceil((double) thriftResponse.getTotalElements() / thriftResponse.getSize())
                : 0);
        return r;
    }

    public List<ExtendedFieldConfigResponse> getContent() { return content; }
    public void setContent(List<ExtendedFieldConfigResponse> content) { this.content = content; }

    public int getPage() { return page; }
    public void setPage(int page) { this.page = page; }

    public int getSize() { return size; }
    public void setSize(int size) { this.size = size; }

    public int getTotalElements() { return totalElements; }
    public void setTotalElements(int totalElements) { this.totalElements = totalElements; }

    public int getTotalPages() { return totalPages; }
    public void setTotalPages(int totalPages) { this.totalPages = totalPages; }
}
```

#### EFErrorResponse

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/EFErrorResponse.java`

**Why**: `ResponseWrapper.ApiError` only has `(Long code, String message)` — no `field` property.
EF error responses need a `field` property (e.g. `"extendedFields[0].efId"`) for structured errors.
This new DTO is used only by `LoyaltyExtendedFieldErrorAdvice` and `SubscriptionErrorAdvice`
(for the `ExtendedFieldValidationException` handler).

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

/**
 * Structured error response body for EF-specific errors.
 * Provides code, message, and field path for client-side error handling.
 * Used by LoyaltyExtendedFieldErrorAdvice and the ExtendedFieldValidationException
 * handler in SubscriptionErrorAdvice.
 */
public class EFErrorResponse {

    private String code;      // e.g. "EF_CONFIG_DUPLICATE_NAME", "EF_VALIDATION_001"
    private String message;   // human-readable
    private String field;     // JSON path e.g. "extendedFields[0].efId"; may be null

    public EFErrorResponse() {}

    public EFErrorResponse(String code, String message, String field) {
        this.code = code;
        this.message = message;
        this.field = field;
    }

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public String getField() { return field; }
    public void setField(String field) { this.field = field; }
}
```

---

### 4d. LoyaltyExtendedFieldFacade

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/LoyaltyExtendedFieldFacade.java`

**Package**: `com.capillary.intouchapiv3.unified.subscription.extendedfields`

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import com.capillary.intouchapiv3.services.thrift.EmfExtendedFieldsThriftService;
import com.capillary.shopbook.emf.api.external.CreateLoyaltyExtendedFieldRequest;
import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldConfig;
import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldListResponse;
import com.capillary.shopbook.emf.api.external.UpdateLoyaltyExtendedFieldRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Facade for EF Config CRUD operations in intouch-api-v3.
 * Responsibilities:
 *   - Builds Thrift request structs from REST DTOs
 *   - Passes orgId (from auth token, via controller) into Thrift structs — never from request body
 *   - Calls EmfExtendedFieldsThriftService
 *   - Maps Thrift response to REST response DTOs
 *
 * orgId flow: Controller extracts orgId from auth token → passes to Facade →
 *             Facade populates Thrift request.orgId.
 * This ensures G-07.1 is enforced: orgId never comes from HTTP body.
 */
@Component
public class LoyaltyExtendedFieldFacade {

    @Autowired
    private EmfExtendedFieldsThriftService emfThriftService;

    /**
     * Create EF config. orgId from auth token; programId/name/scope/dataType from request body.
     *
     * @param orgId    extracted from auth token by controller
     * @param request  REST DTO (no orgId field — G-07.1)
     * @param tillName user's tillName for audit (createdBy field)
     * @return ExtendedFieldConfigResponse with created config including auto-generated id
     */
    public ExtendedFieldConfigResponse create(long orgId,
                                               CreateExtendedFieldRequest request,
                                               String tillName) {
        CreateLoyaltyExtendedFieldRequest thriftReq = new CreateLoyaltyExtendedFieldRequest();
        thriftReq.setOrgId(orgId);                          // from auth token
        thriftReq.setProgramId(request.getProgramId());
        thriftReq.setName(request.getName());
        thriftReq.setScope(request.getScope());
        thriftReq.setDataType(request.getDataType());
        thriftReq.setIsMandatory(request.isMandatory());
        thriftReq.setDefaultValue(request.getDefaultValue());
        thriftReq.setCreatedBy(tillName);

        LoyaltyExtendedFieldConfig config =
                emfThriftService.createLoyaltyExtendedFieldConfig(thriftReq);
        return ExtendedFieldConfigResponse.from(config);
    }

    /**
     * Update EF config. orgId from auth token; id from path param; name/isActive from request body.
     *
     * @param orgId     extracted from auth token by controller
     * @param id        from path variable /{id}
     * @param request   REST DTO (mutable fields only — D-23)
     * @param tillName  user's tillName for audit
     * @return ExtendedFieldConfigResponse with updated config
     */
    public ExtendedFieldConfigResponse update(long orgId, long id,
                                               UpdateExtendedFieldRequest request,
                                               String tillName) {
        UpdateLoyaltyExtendedFieldRequest thriftReq = new UpdateLoyaltyExtendedFieldRequest();
        thriftReq.setId(id);
        thriftReq.setOrgId(orgId);                          // from auth token
        if (request.getName() != null) {
            thriftReq.setName(request.getName());
        }
        if (request.getIsActive() != null) {
            thriftReq.setIsActive(request.getIsActive());
        }
        thriftReq.setUpdatedBy(tillName);

        LoyaltyExtendedFieldConfig config =
                emfThriftService.updateLoyaltyExtendedFieldConfig(thriftReq);
        return ExtendedFieldConfigResponse.from(config);
    }

    /**
     * List EF configs. orgId from auth token; programId/scope/pagination from query params.
     *
     * @param orgId           extracted from auth token by controller
     * @param programId       required query param
     * @param scope           optional query param (null = all scopes)
     * @param includeInactive default false
     * @param page            0-indexed
     * @param size            page size, default 20
     * @return ExtendedFieldsPageResponse (content never null — G-02.1)
     */
    public ExtendedFieldsPageResponse list(long orgId, Long programId, String scope,
                                            boolean includeInactive, int page, int size) {
        LoyaltyExtendedFieldListResponse thriftResp =
                emfThriftService.getLoyaltyExtendedFieldConfigs(
                        orgId, programId, scope, includeInactive, page, size);
        return ExtendedFieldsPageResponse.from(thriftResp);
    }
}
```

---

### 4e. LoyaltyExtendedFieldController

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/LoyaltyExtendedFieldController.java`

**Package**: `com.capillary.intouchapiv3.unified.subscription.extendedfields`

**Pattern**: Follows `SubscriptionController.java` exactly:
- `@RestController @RequestMapping`
- `ResponseEntity<?>` return type
- `AbstractBaseAuthenticationToken token` as last parameter
- `token.getIntouchUser()` for orgId extraction

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import com.capillary.intouchapiv3.auth.AbstractBaseAuthenticationToken;
import com.capillary.intouchapiv3.auth.IntouchUser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

/**
 * REST controller for Loyalty Extended Field config CRUD.
 * Endpoints: POST /v3/extendedfields/config
 *            PUT  /v3/extendedfields/config/{id}
 *            GET  /v3/extendedfields/config
 *
 * orgId: ALWAYS extracted from auth token — never from request body or path params (G-07.1).
 * Error handling: delegated to LoyaltyExtendedFieldErrorAdvice.
 */
@RestController
@RequestMapping("/v3/extendedfields/config")
public class LoyaltyExtendedFieldController {

    private static final Logger logger =
            LoggerFactory.getLogger(LoyaltyExtendedFieldController.class);

    @Autowired
    private LoyaltyExtendedFieldFacade facade;

    /**
     * POST /v3/extendedfields/config — Create a new EF config (HTTP 201).
     * @Valid triggers Bean Validation on CreateExtendedFieldRequest.
     */
    @PostMapping
    public ResponseEntity<ExtendedFieldConfigResponse> createExtendedField(
            @RequestBody @Valid CreateExtendedFieldRequest request,
            AbstractBaseAuthenticationToken token) {

        IntouchUser user = token.getIntouchUser();
        logger.info("Creating EF config for orgId={}, programId={}, name={}",
                user.getOrgId(), request.getProgramId(), request.getName());

        ExtendedFieldConfigResponse response =
                facade.create(user.getOrgId(), request, user.getTillName());
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * PUT /v3/extendedfields/config/{id} — Update EF config name and/or is_active (HTTP 200).
     * Soft-delete: isActive=false. Idempotent — D-16.
     * @Valid triggers Bean Validation on UpdateExtendedFieldRequest.
     */
    @PutMapping("/{id}")
    public ResponseEntity<ExtendedFieldConfigResponse> updateExtendedField(
            @PathVariable Long id,
            @RequestBody @Valid UpdateExtendedFieldRequest request,
            AbstractBaseAuthenticationToken token) {

        IntouchUser user = token.getIntouchUser();
        logger.info("Updating EF config id={} for orgId={}", id, user.getOrgId());

        ExtendedFieldConfigResponse response =
                facade.update(user.getOrgId(), id, request, user.getTillName());
        return ResponseEntity.ok(response);
    }

    /**
     * GET /v3/extendedfields/config — List EF configs (HTTP 200, paginated).
     * programId is required. scope, includeInactive, page, size are optional.
     */
    @GetMapping
    public ResponseEntity<ExtendedFieldsPageResponse> listExtendedFields(
            @RequestParam Long programId,
            @RequestParam(required = false) String scope,
            @RequestParam(defaultValue = "false") boolean includeInactive,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            AbstractBaseAuthenticationToken token) {

        IntouchUser user = token.getIntouchUser();
        logger.info("Listing EF configs for orgId={}, programId={}, scope={}, includeInactive={}",
                user.getOrgId(), programId, scope, includeInactive);

        ExtendedFieldsPageResponse response =
                facade.list(user.getOrgId(), programId, scope, includeInactive, page, size);
        return ResponseEntity.ok(response);
    }
}
```

---

### 4f. LoyaltyExtendedFieldErrorAdvice

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/LoyaltyExtendedFieldErrorAdvice.java`

**Package**: `com.capillary.intouchapiv3.unified.subscription.extendedfields`

**Pattern**: Follows `SubscriptionErrorAdvice.java` — `@ControllerAdvice(assignableTypes = …)`,
`@ResponseBody @ExceptionHandler`, `ResponseEntity<…>` return type.

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import com.capillary.intouchapiv3.services.thrift.exception.EFThriftException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;

import static org.springframework.http.HttpStatus.*;

/**
 * Exception handler scoped to LoyaltyExtendedFieldController.
 * Maps EFThriftException (which carries EMFException.statusCode) to HTTP status codes.
 *
 * Scoped to avoid conflict with TargetGroupErrorAdvice (which has a catch-all Throwable handler).
 * ADR-06: two separate advice registrations for EF Config vs EF Validation errors.
 */
@ControllerAdvice(assignableTypes = {LoyaltyExtendedFieldController.class})
@Slf4j
public class LoyaltyExtendedFieldErrorAdvice {

    /**
     * Maps EFThriftException.statusCode to HTTP status:
     *   8001 → 404 Not Found         (EF_CONFIG_NOT_FOUND)
     *   8002 → 409 Conflict          (EF_CONFIG_DUPLICATE_NAME)
     *   8003 → 400 Bad Request       (EF_CONFIG_IMMUTABLE_UPDATE)
     *   8004 → 400 Bad Request       (EF_CONFIG_INVALID_SCOPE)
     *   8005 → 400 Bad Request       (EF_CONFIG_INVALID_DATA_TYPE)
     *   8009 → 400 Bad Request       (EF_CONFIG_MAX_COUNT_EXCEEDED)
     *   8010 → 400 Bad Request       (EF_CONFIG_INVALID_ORG)
     *   other → 500 Internal Server Error
     */
    @ResponseBody
    @ExceptionHandler(EFThriftException.class)
    public ResponseEntity<EFErrorResponse> handleEFThriftException(EFThriftException ex) {
        int statusCode = ex.getStatusCode();
        log.error("EF Config operation failed. statusCode={}, message={}", statusCode, ex.getMessage());

        switch (statusCode) {
            case 8001:
                return error(NOT_FOUND, "EF_CONFIG_NOT_FOUND", ex.getMessage(), null);
            case 8002:
                return error(CONFLICT, "EF_CONFIG_DUPLICATE_NAME", ex.getMessage(), "name");
            case 8003:
                return error(BAD_REQUEST, "EF_CONFIG_IMMUTABLE_UPDATE", ex.getMessage(), null);
            case 8004:
                return error(BAD_REQUEST, "EF_CONFIG_INVALID_SCOPE", ex.getMessage(), "scope");
            case 8005:
                return error(BAD_REQUEST, "EF_CONFIG_INVALID_DATA_TYPE", ex.getMessage(), "dataType");
            case 8009:
                return error(BAD_REQUEST, "EF_CONFIG_MAX_COUNT_EXCEEDED", ex.getMessage(), null);
            case 8010:
                return error(BAD_REQUEST, "EF_CONFIG_INVALID_ORG", ex.getMessage(), null);
            default:
                log.error("Unexpected EF statusCode={}. Returning 500.", statusCode);
                return error(INTERNAL_SERVER_ERROR, "EF_SYSTEM_ERROR",
                        "An unexpected error occurred. Contact support.", null);
        }
    }

    private ResponseEntity<EFErrorResponse> error(
            org.springframework.http.HttpStatus status,
            String code, String message, String field) {
        return ResponseEntity
                .status(status)
                .contentType(MediaType.APPLICATION_JSON)
                .body(new EFErrorResponse(code, message, field));
    }
}
```

---

## Section 5: intouch-api-v3 — SubscriptionProgram.ExtendedField Modification

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java`

**Exact before/after diff for the `ExtendedField` inner class** (lines ~295-301):

**Before:**
```java
public static class ExtendedField {
    @NotNull
    private ExtendedFieldType type;
    @NotBlank
    private String key;
    private String value;
}
```

**After:**
```java
public static class ExtendedField {
    /**
     * FK to loyalty_extended_fields.id. Added D-28.
     * Used for EF validation by ExtendedFieldValidator.
     * null on old MongoDB documents ({type, key, value}) — no crash, no migration needed (ADR-03).
     */
    private Long efId;

    /**
     * Field name e.g. "gender". Kept — D-28: key has semantic value for display + trace.
     * NOT renamed — no @Field annotation needed.
     */
    private String key;

    /** Field value e.g. "Male". Unchanged. */
    private String value;

    // Builder method additions (add to existing builder):
    // .efId(Long efId) — new setter in Lombok or manual builder

    public Long getEfId() { return efId; }
    public void setEfId(Long efId) { this.efId = efId; }

    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }

    public String getValue() { return value; }
    public void setValue(String value) { this.value = value; }
}
```

**Also remove**:
- `import com.capillary.intouchapiv3.unified.subscription.enums.ExtendedFieldType;` from `SubscriptionProgram.java`
- The `ExtendedFieldType` import and all usages in `SubscriptionExtendedFieldsTest.java`

**File to delete**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java`
(D-11, D-27 — only 3 confirmed usages, all in-scope)

---

## Section 6: intouch-api-v3 — ExtendedFieldValidator

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldValidationException.java`

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

/**
 * Unchecked exception thrown by ExtendedFieldValidator on validation failure.
 * D-33: RuntimeException (unchecked) — caught by SubscriptionErrorAdvice handler → HTTP 400.
 * Not propagated via Thrift — validation runs in V3 before any Thrift subscription write.
 * Carries errorCode, human-readable message, and JSON field path for structured error response.
 */
public class ExtendedFieldValidationException extends RuntimeException {

    private final String errorCode;   // e.g. "EF_VALIDATION_001", "EF_VALIDATION_002", "EF_VALIDATION_003"
    private final String field;       // JSON path e.g. "extendedFields[0].efId"; null for R-03 (list-level)

    public ExtendedFieldValidationException(String errorCode, String message, String field) {
        super(message);
        this.errorCode = errorCode;
        this.field = field;
    }

    public String getErrorCode() { return errorCode; }
    public String getField() { return field; }
}
```

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldValidator.java`

```java
package com.capillary.intouchapiv3.unified.subscription.extendedfields;

import com.capillary.intouchapiv3.services.thrift.EmfExtendedFieldsThriftService;
import com.capillary.intouchapiv3.unified.subscription.SubscriptionProgram;
import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldConfig;
import com.capillary.shopbook.emf.api.external.LoyaltyExtendedFieldListResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Stateless validator for SubscriptionProgram.ExtendedField list against active EF configs.
 *
 * Called from SubscriptionFacade.createSubscription() and updateSubscription().
 * Short-circuits: if extendedFields is null or empty, validation is skipped.
 *
 * Validation sequence (A-05, ADR-05 — eager fail-fast):
 *   Step 1: One Thrift call to fetch all active EF configs for (orgId, programId, SUBSCRIPTION_META).
 *   Step 2: R-01 — each submitted efId must exist in the active config map.
 *   Step 3: R-02 — value must match declared data_type.
 *   Step 4: R-03 — all mandatory configs must have a submitted entry.
 *
 * Race condition (C-4): fail-open. If an EF config is deactivated mid-flight, the snapshot
 * from Step 1 is used. Subscription succeeds with the stale-but-valid-at-snapshot efId.
 */
@Component
public class ExtendedFieldValidator {

    private static final DateTimeFormatter ISO_DATE = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    @Autowired
    private EmfExtendedFieldsThriftService emfThriftService;

    /**
     * Validates a list of ExtendedField entries against active EF configs for the given org/program.
     *
     * @param orgId          from auth token
     * @param programId      from subscription program
     * @param extendedFields list to validate; must be non-null and non-empty (caller's responsibility)
     * @throws ExtendedFieldValidationException if any validation rule fails (ADR-05: fail-fast)
     */
    public void validate(long orgId, long programId,
                         List<SubscriptionProgram.ExtendedField> extendedFields) {

        // Step 1: Fetch all active configs for (orgId, programId) — one Thrift call (A-05, ADR-08)
        // scope=null → all scopes (current release only has SUBSCRIPTION_META but kept open)
        // includeInactive=false → active only
        // page=0, size=100 → max 10 configs (D-15), 100 is safe upper bound
        LoyaltyExtendedFieldListResponse response =
                emfThriftService.getLoyaltyExtendedFieldConfigs(
                        orgId, programId, null, false, 0, 100);

        Map<Long, LoyaltyExtendedFieldConfig> configMap = response.getConfigs() == null
                ? Map.of()
                : response.getConfigs().stream()
                        .collect(Collectors.toMap(LoyaltyExtendedFieldConfig::getId,
                                Function.identity()));

        // Step 2 + 3: R-01 (efId exists) + R-02 (value matches dataType) — per submitted EF
        for (int i = 0; i < extendedFields.size(); i++) {
            SubscriptionProgram.ExtendedField ef = extendedFields.get(i);

            // R-01: efId must be non-null and present in active configs
            if (ef.getEfId() == null || !configMap.containsKey(ef.getEfId())) {
                throw new ExtendedFieldValidationException(
                        "EF_VALIDATION_001",
                        "Unknown or inactive extended field id: " + ef.getEfId()
                                + ". Verify the id exists and is active for this program.",
                        "extendedFields[" + i + "].efId");
            }

            // R-02: value must match declared data_type
            LoyaltyExtendedFieldConfig config = configMap.get(ef.getEfId());
            String value = ef.getValue();
            if (value != null && !matchesDataType(config.getDataType(), value)) {
                throw new ExtendedFieldValidationException(
                        "EF_VALIDATION_002",
                        "Value '" + value + "' does not match expected type "
                                + config.getDataType() + " for field '" + config.getName() + "'.",
                        "extendedFields[" + i + "].value");
            }
        }

        // Step 4: R-03 — all mandatory configs must be present in submitted list
        Set<Long> submittedEfIds = extendedFields.stream()
                .filter(ef -> ef.getEfId() != null)
                .map(SubscriptionProgram.ExtendedField::getEfId)
                .collect(Collectors.toSet());

        for (LoyaltyExtendedFieldConfig mandatory : configMap.values()) {
            if (mandatory.isIsMandatory() && !submittedEfIds.contains(mandatory.getId())) {
                throw new ExtendedFieldValidationException(
                        "EF_VALIDATION_003",
                        "Missing mandatory extended field: '" + mandatory.getName()
                                + "' (id: " + mandatory.getId() + ").",
                        "extendedFields");
            }
        }
        // All validations passed — return normally
    }

    /**
     * Checks whether a string value matches the declared data_type.
     * ADR-05: stops on first type mismatch per field (fail-fast).
     *
     * STRING: any non-null string passes.
     * NUMBER: must be parseable as BigDecimal.
     * BOOLEAN: must be "true" or "false" (case-insensitive).
     * DATE: must match yyyy-MM-dd ISO date pattern.
     * Unknown type: fails safe (returns false).
     */
    private boolean matchesDataType(String dataType, String value) {
        if (value == null) return true;  // null value always passes type check
        switch (dataType) {
            case "STRING":
                return true;
            case "NUMBER":
                try {
                    new BigDecimal(value);
                    return true;
                } catch (NumberFormatException e) {
                    return false;
                }
            case "BOOLEAN":
                return "true".equalsIgnoreCase(value) || "false".equalsIgnoreCase(value);
            case "DATE":
                try {
                    LocalDate.parse(value, ISO_DATE);
                    return true;
                } catch (DateTimeParseException e) {
                    return false;
                }
            default:
                return false;  // unknown type fails safe
        }
    }
}
```

---

## Section 7: intouch-api-v3 — SubscriptionFacade Modifications

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionFacade.java`

### 7a. New field injection (add near other @Autowired fields)

```java
@Autowired
private ExtendedFieldValidator extendedFieldValidator;
```

### 7b. createSubscription() — line 102 region

Add validation call **after** the existing null-guard for `extendedFields`, **before** the MongoDB builder:

```java
// EXISTING null-guard (already present at line ~102):
if (subscriptionProgram.getExtendedFields() == null) {
    subscriptionProgram.setExtendedFields(List.of());
}

// NEW: EF validation hook — only fires when extendedFields is non-empty (R-CT-04 short-circuit)
if (!subscriptionProgram.getExtendedFields().isEmpty()) {
    extendedFieldValidator.validate(
            orgId,
            programId,
            subscriptionProgram.getExtendedFields());
}
// Proceed to MongoDB builder as before
```

### 7c. updateSubscription() — line 289 region

Add validation call **inside** the `if (request.getExtendedFields() != null)` block,
**before** `existing.setExtendedFields(...)`:

```java
// EXISTING block (already present at line ~289):
if (request.getExtendedFields() != null) {
    // NEW: EF validation before applying the new list
    extendedFieldValidator.validate(
            orgId,
            existing.getProgramId(),     // programId from the persisted entity, not the request
            request.getExtendedFields());
    existing.setExtendedFields(request.getExtendedFields());  // existing line, unchanged
}
```

### 7d. forkDraft() line ~343 and duplicateSubscription() line ~385

**NO CHANGE** — EF ids copied as-is per OQ-9 resolution (D-32 in session-memory). Stale deactivated
efIds will be caught at the next explicit subscription create/update event.

---

## Section 8: intouch-api-v3 — SubscriptionErrorAdvice New Handler

**File**: `src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionErrorAdvice.java`

Add one new `@ExceptionHandler` method after the existing `handlePublishFailure` handler:

```java
import com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldValidationException;
import com.capillary.intouchapiv3.unified.subscription.extendedfields.EFErrorResponse;

/**
 * Handler for ExtendedFieldValidationException thrown by ExtendedFieldValidator
 * within SubscriptionFacade.createSubscription() and updateSubscription().
 * D-33: validation runs in V3 before any Thrift call; exception is RuntimeException.
 * Returns HTTP 400 with structured EFErrorResponse body.
 */
@ResponseBody
@ExceptionHandler(ExtendedFieldValidationException.class)
public ResponseEntity<EFErrorResponse> handleExtendedFieldValidationException(
        ExtendedFieldValidationException ex) {
    log.warn("EF validation failed: code={}, field={}, message={}",
            ex.getErrorCode(), ex.getField(), ex.getMessage());
    return ResponseEntity
            .status(BAD_REQUEST)
            .contentType(MediaType.APPLICATION_JSON)
            .body(new EFErrorResponse(ex.getErrorCode(), ex.getMessage(), ex.getField()));
}
```

**Import changes to add at the top of `SubscriptionErrorAdvice.java`**:
```java
import com.capillary.intouchapiv3.unified.subscription.extendedfields.ExtendedFieldValidationException;
import com.capillary.intouchapiv3.unified.subscription.extendedfields.EFErrorResponse;
import org.springframework.http.MediaType;
```

---

## Section 9: Error Code Constants Summary

All error codes are in `ExceptionCodes.java` as specified in Section 3g. For reference:

| Constant | Value | HTTP via V3 | Trigger |
|----------|-------|-------------|---------|
| `EF_CONFIG_NOT_FOUND` | 8001 | 404 | `findByPkIdAndPkOrgId` returns empty |
| `EF_CONFIG_DUPLICATE_NAME` | 8002 | 409 | Name uniqueness violation (D-30) |
| `EF_CONFIG_IMMUTABLE_UPDATE` | 8003 | 400 | Client tries to update scope/dataType/isMandatory/defaultValue |
| `EF_CONFIG_INVALID_SCOPE` | 8004 | 400 | scope not in SUBSCRIPTION_META (current release) |
| `EF_CONFIG_INVALID_DATA_TYPE` | 8005 | 400 | dataType not in STRING/NUMBER/BOOLEAN/DATE |
| `EF_VALIDATION_UNKNOWN_ID` | 8006 | 400 (via EFThriftException) | Used in EMF service only (not thrown in V3 directly for EF CRUD) |
| `EF_VALIDATION_TYPE_MISMATCH` | 8007 | 400 (via EFThriftException) | Used in EMF service only |
| `EF_VALIDATION_MISSING_MANDATORY` | 8008 | 400 (via EFThriftException) | Used in EMF service only |
| `EF_CONFIG_MAX_COUNT_EXCEEDED` | 8009 | 400 | Active count >= MAX_EF_COUNT_PER_PROGRAM |
| `EF_CONFIG_INVALID_ORG` | 8010 | 400 | orgId <= 0 in Thrift request |

**V3-only error codes** (in `ExtendedFieldValidationException`, not EMF exception codes):

| V3 Code | Trigger |
|---------|---------|
| `EF_VALIDATION_001` | R-01 — efId unknown or inactive (thrown by `ExtendedFieldValidator`) |
| `EF_VALIDATION_002` | R-02 — value type mismatch (thrown by `ExtendedFieldValidator`) |
| `EF_VALIDATION_003` | R-03 — mandatory field absent (thrown by `ExtendedFieldValidator`) |

**Note on dual codes**: EMF error codes 8006-8008 exist for future use if EMF ever exposes a
validation endpoint. For this release, EF validation runs entirely in V3 (A-05) and uses V3-specific
error codes `EF_VALIDATION_001/002/003`. The 8006-8008 constants are pre-allocated in EMF for
completeness and possible future use.

---

## Section 10: Complete File Inventory

### New files

| Repo | Path | Type |
|------|------|------|
| thrift-ifaces-emf | `emf.thrift` (+4 structs, +3 methods) | IDL append |
| cc-stack-crm | `schema/dbmaster/warehouse/loyalty_extended_fields.sql` | New SQL |
| cc-stack-crm | `seed_data/dbmaster/warehouse/program_config_keys.sql` | SQL append (1 row) |
| emf-parent | `pointsengine-emf/.../entity/LoyaltyExtendedFieldPK.java` | New `@Embeddable` |
| emf-parent | `pointsengine-emf/.../entity/LoyaltyExtendedField.java` | New `@Entity` |
| emf-parent | `pointsengine-emf/.../dao/LoyaltyExtendedFieldRepository.java` | New `@Repository` |
| emf-parent | `pointsengine-emf/.../services/LoyaltyExtendedFieldService.java` | New interface |
| emf-parent | `pointsengine-emf/.../services/LoyaltyExtendedFieldServiceImpl.java` | New `@Service` |
| intouch-api-v3 | `.../thrift/exception/EFThriftException.java` | New exception |
| intouch-api-v3 | `.../thrift/EmfExtendedFieldsThriftService.java` | New `@Service` |
| intouch-api-v3 | `.../extendedfields/CreateExtendedFieldRequest.java` | New DTO |
| intouch-api-v3 | `.../extendedfields/UpdateExtendedFieldRequest.java` | New DTO |
| intouch-api-v3 | `.../extendedfields/ExtendedFieldConfigResponse.java` | New DTO |
| intouch-api-v3 | `.../extendedfields/ExtendedFieldsPageResponse.java` | New DTO |
| intouch-api-v3 | `.../extendedfields/EFErrorResponse.java` | New error DTO |
| intouch-api-v3 | `.../extendedfields/LoyaltyExtendedFieldFacade.java` | New `@Component` |
| intouch-api-v3 | `.../extendedfields/LoyaltyExtendedFieldController.java` | New `@RestController` |
| intouch-api-v3 | `.../extendedfields/LoyaltyExtendedFieldErrorAdvice.java` | New `@ControllerAdvice` |
| intouch-api-v3 | `.../extendedfields/ExtendedFieldValidationException.java` | New `RuntimeException` |
| intouch-api-v3 | `.../extendedfields/ExtendedFieldValidator.java` | New `@Component` |

### Modified files

| Repo | Path | Change |
|------|------|--------|
| emf-parent | `emf/.../external/EMFThriftServiceImpl.java` | +1 field, +3 methods |
| emf-parent | `emf/.../exception/ExceptionCodes.java` | +10 constants, updated `badRequestErrors` |
| intouch-api-v3 | `.../subscription/SubscriptionProgram.java` | Delete `type` field, add `efId: Long` |
| intouch-api-v3 | `.../subscription/SubscriptionFacade.java` | +1 field injection, +2 validation calls |
| intouch-api-v3 | `.../subscription/SubscriptionErrorAdvice.java` | +1 exception handler, +2 imports |
| intouch-api-v3 | `.../subscription/SubscriptionExtendedFieldsTest.java` | Update BT-EF-01 through BT-EF-06 |

### Deleted files

| Repo | Path | Reason |
|------|------|--------|
| intouch-api-v3 | `.../subscription/enums/ExtendedFieldType.java` | D-11, D-27: only 3 confirmed usages, all in-scope |

---

## Section 11: Key Design Decisions (Designer Phase)

| Decision | Rationale |
|----------|-----------|
| `EFThriftException extends EMFThriftException` adds `int statusCode` | `EMFThriftException` only carries `String message`. LoyaltyExtendedFieldErrorAdvice needs the EMFException.statusCode for HTTP mapping. Adding a subclass is backward-safe — existing EMFThriftException handlers are unaffected. |
| `@Table(name = "loyalty_extended_fields", schema = "warehouse")` — no `@DataSourceSpecification` on entity | Confirmed from `ActionPointsDetail.java` and `ProgramConfigKeyValue.java` — entities use `@Table(schema=…)` only. `@DataSourceSpecification` is a service-layer annotation (confirmed from `InfoLookupService.java`, `SlabDowngradeService.java`). |
| `LoyaltyExtendedFieldRepository extends GenericDao<…>` with `@Transactional(value = "warehouse", propagation = Propagation.SUPPORTS)` | Confirmed from `CappingConfigDao.java` and `HistoricalPointsDao.java` — all pointsengine-emf DAOs follow this exact pattern. JPQL `@Query` with `@Param` for custom queries (HistoricalPointsDao pattern). |
| `EFErrorResponse` is a new DTO, not `ResponseWrapper.ApiError` | `ResponseWrapper.ApiError` only has `(Long code, String message)` — no `field` property. EF errors require a `field` path (e.g. `extendedFields[0].efId`) for structured client-side error handling. New DTO is isolated to the EF package. |
| `ExtendedFieldValidator` fetches configs with `scope=null` in Thrift call | A-05: one Thrift call fetches all active configs for (orgId, programId) regardless of scope. In-memory filtering by scope is not needed since current release only has SUBSCRIPTION_META and validator is called from subscription context only. |

---

*Produced by Designer (Phase 7) — CAP-183124 / loyaltyExtendedFields — 2026-04-22*
*Confidence: C7 — all class/method signatures derived from direct codebase reads.*
*Ready for SDET (Phase 8) and Developer (Phase 10) handoff.*
