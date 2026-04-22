---
feature_id: loyaltyExtendedFields
jira: CAP-183124
domain: loyalty.subscription.extended_fields
phase: PRD
date: 2026-04-22
status: DRAFT
confidence_overall: C5

epics:
  - id: EF-EPIC-01
    name: EF Config Registry CRUD
    confidence: C6
    complexity: MEDIUM
    dependencies: []
    stories:
      - id: EF-US-01
        title: Create EF Definition
        complexity: MEDIUM
        acceptance_criteria:
          - "[ ] POST /v3/extendedfields/config creates row in loyalty_extended_fields for caller's org"
          - "[ ] Uniqueness: (org_id, scope, name) — duplicate returns 409 CONFLICT"
          - "[ ] scope must be SUBSCRIPTION_META; invalid scope returns 400"
          - "[ ] data_type must be STRING | NUMBER | BOOLEAN | DATE | ENUM; invalid returns 400"
          - "[ ] data_type=ENUM with null or empty enum_values returns 400"
          - "[ ] data_type=ENUM with valid enum_values persists allowed values list"
          - "[ ] is_active defaults to 1 (active)"
          - "[ ] created_on and last_updated_on populated in UTC"
          - "[ ] Response includes created record with generated id"
          - "[ ] Org cannot exceed MAX_EF_COUNT_PER_ORG (from program_config_key_values, default=10) — 400 if exceeded"

      - id: EF-US-02
        title: Update EF Definition
        complexity: SMALL
        acceptance_criteria:
          - "[ ] PUT /v3/extendedfields/config/{id} updates row for caller's org"
          - "[ ] name, scope, data_type are immutable — attempt to change returns 400"
          - "[ ] is_mandatory and default_value are mutable"
          - "[ ] Non-existent id or wrong org_id returns 404"
          - "[ ] last_updated_on updated on every successful PUT (UTC)"

      - id: EF-US-03
        title: Deactivate EF Definition (Soft Delete)
        complexity: SMALL
        acceptance_criteria:
          - "[ ] DELETE /v3/extendedfields/config/{id} sets is_active=0 (no row deletion)"
          - "[ ] ACTIVE→INACTIVE returns 200/204"
          - "[ ] Already INACTIVE returns 200/204 (idempotent)"
          - "[ ] Never existed returns 404"
          - "[ ] Deactivated field (is_active=0) no longer passes EF validation on new subscription write events"
          - "[ ] Existing subscription programs with that field value are NOT affected (D-18)"

      - id: EF-US-04
        title: List EF Definitions
        complexity: SMALL
        acceptance_criteria:
          - "[ ] GET /v3/extendedfields/config returns all EF configs for caller's org_id"
          - "[ ] Supports query params: scope, includeInactive (boolean, default false), page, size"
          - "[ ] By default only active (is_active=1) records returned"
          - "[ ] includeInactive=true returns both active and inactive records"
          - "[ ] Returns paginated response (page + size) per G-04.2"
          - "[ ] Empty result returns 200 with empty list (not 404)"
          - "[ ] Max 100 records per page"

  - id: EF-EPIC-02
    name: EF Validation on Subscription Programs
    confidence: C5
    complexity: MEDIUM
    dependencies: [EF-EPIC-01]
    stories:
      - id: EF-US-05
        title: Validate EF values on Subscription Create
        complexity: MEDIUM
        acceptance_criteria:
          - "[ ] POST /v3/subscriptions with extendedFields triggers validation"
          - "[ ] Each entry: scope must be SUBSCRIPTION_META"
          - "[ ] Each entry: key must match is_active=1 record in loyalty_extended_fields for (org_id, scope)"
          - "[ ] Each entry: value data type must match registered data_type"
          - "[ ] Each entry: when data_type=ENUM, value must be in registered enum_values list"
          - "[ ] All is_mandatory=true fields for (org_id, SUBSCRIPTION_META) must be present"
          - "[ ] null extendedFields when mandatory fields exist returns 400"
          - "[ ] Valid extendedFields persisted in MongoDB subscription_programs.extendedFields"
          - "[ ] Validation failures return 400 with structured error: {code, message, field}"

      - id: EF-US-06
        title: Validate EF values on Subscription Update
        complexity: MEDIUM
        acceptance_criteria:
          - "[ ] PUT /v3/subscriptions/{id} applies same EF validation rules as EF-US-05 when extendedFields provided"
          - "[ ] null extendedFields on PUT preserves existing values (R-33 null-guard)"
          - "[ ] empty list [] on PUT clears all EF values"
          - "[ ] No validation fired when extendedFields is null on PUT"

  - id: EF-EPIC-03
    name: Model Correction
    confidence: C7
    complexity: SMALL
    dependencies: []
    stories:
      - id: EF-US-07
        title: Rename ExtendedFieldType to scope
        complexity: SMALL
        acceptance_criteria:
          - "[ ] ExtendedFieldType.java deleted from intouch-api-v3"
          - "[ ] SubscriptionProgram.ExtendedField.type renamed to scope (type: String)"
          - "[ ] Tests BT-EF-01 to BT-EF-06 updated to use SUBSCRIPTION_META"
          - "[ ] No other callers of ExtendedFieldType broken (grep confirms)"
          - "[ ] MongoDB JSON field key updated from 'type' to 'scope' in new documents"

dependencies:
  - "thrift-ifaces-emf: new structs + EMFService methods required before emf-parent implementation"
  - "cc-stack-crm schema merged before emf-parent DAO can be tested end-to-end"
  - "EF-US-07 (model fix) should be done first — tests BT-EF-01 to BT-EF-06 reference wrong enum"

codebase_sources:
  intouch_api_v3:
    path: /Users/baljeetsingh/IdeaProjects/intouch-api-v3
    branch: aidlc/loyaltyExtendedFields
    modified_files:
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionFacade.java
      - src/test/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionExtendedFieldsTest.java
    deleted_files:
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java
    new_files:
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldController.java
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldFacade.java
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/extendedfields/ExtendedFieldValidator.java

  emf_parent:
    path: /Users/baljeetsingh/IdeaProjects/emf-parent
    branch: aidlc/loyaltyExtendedFields
    new_files:
      - emf/src/main/java/.../loyaltyextendedfield/LoyaltyExtendedFieldService.java
      - emf/src/main/java/.../loyaltyextendedfield/LoyaltyExtendedFieldServiceImpl.java
      - emf/src/main/java/.../loyaltyextendedfield/LoyaltyExtendedFieldDao.java
      - emf/src/main/java/.../loyaltyextendedfield/LoyaltyExtendedFieldDaoImpl.java
      - emf/src/main/java/.../loyaltyextendedfield/LoyaltyExtendedField.java

  thrift_ifaces_emf:
    path: /Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf
    branch: aidlc/loyaltyExtendedFields
    modified_files:
      - emf.thrift

  cc_stack_crm:
    path: /Users/baljeetsingh/IdeaProjects/cc-stack-crm
    branch: aidlc/loyaltyExtendedFields
    new_files:
      - schema/dbmaster/warehouse/loyalty_extended_fields.sql

schema:
  new_tables:
    - name: loyalty_extended_fields
      db: warehouse
      ddl: |
        CREATE TABLE `loyalty_extended_fields` (
          `id`               BIGINT        NOT NULL AUTO_INCREMENT,
          `org_id`           BIGINT        NOT NULL,
          `name`             VARCHAR(100)  NOT NULL,
          `scope`            VARCHAR(50)   NOT NULL,
          `data_type`        VARCHAR(30)   NOT NULL,
          `is_mandatory`     TINYINT(1)    NOT NULL DEFAULT 0,
          `default_value`    VARCHAR(255)  NULL,
          `enum_values`      VARCHAR(1000) NULL,
          `is_active`        TINYINT(1)    NOT NULL DEFAULT 1,
          `created_on`       DATETIME      NOT NULL,
          `last_updated_on`  DATETIME      NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_org_scope_name` (`org_id`, `scope`, `name`),
          KEY `idx_org_scope_active` (`org_id`, `scope`, `is_active`)
        );
      decisions:
        - "D-14: is_active TINYINT(1) — cc-stack-crm convention, BRD status VARCHAR overridden"
        - "D-21 OPEN: enum_values as VARCHAR column (shown) vs child table loyalty_extended_field_enum_values — Architect to decide"

  modified_models:
    - entity: SubscriptionProgram.ExtendedField
      db: MongoDB
      collection: subscription_programs
      changes:
        - field: type
          action: RENAME
          new_name: scope
          type_before: "ExtendedFieldType (enum)"
          type_after: "String"
        - field: ExtendedFieldType
          action: DELETE_CLASS
          file: src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java

thrift:
  file: /Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf/emf.thrift
  new_structs:
    - name: LoyaltyExtendedFieldConfig
      fields:
        - "1: required i64 id"
        - "2: required i64 orgId"
        - "3: required string name"
        - "4: required string scope"
        - "5: required string dataType"           # STRING | NUMBER | BOOLEAN | DATE | ENUM
        - "6: required bool isMandatory"
        - "7: optional string defaultValue"
        - "8: optional list<string> enumValues"   # populated when dataType=ENUM
        - "9: required bool isActive"
        - "10: required string createdOn"
        - "11: required string lastUpdatedOn"

    - name: CreateLoyaltyExtendedFieldRequest
      fields:
        - "1: required i64 orgId"
        - "2: required string name"
        - "3: required string scope"
        - "4: required string dataType"
        - "5: required bool isMandatory"
        - "6: optional string defaultValue"
        - "7: optional list<string> enumValues"   # required when dataType=ENUM

    - name: UpdateLoyaltyExtendedFieldRequest
      fields:
        - "1: required i64 id"
        - "2: required i64 orgId"
        - "3: optional bool isMandatory"
        - "4: optional string defaultValue"
        - "5: optional list<string> enumValues"   # updatable for ENUM type

    - name: LoyaltyExtendedFieldListResponse
      fields:
        - "1: required list<LoyaltyExtendedFieldConfig> configs"
        - "2: required i32 totalElements"
        - "3: required i32 page"
        - "4: required i32 size"

  new_service_methods:
    service: EMFService
    methods:
      - signature: "LoyaltyExtendedFieldConfig createLoyaltyExtendedFieldConfig(1: CreateLoyaltyExtendedFieldRequest request) throws (1: EMFException ex)"
        story: EF-US-01
      - signature: "LoyaltyExtendedFieldConfig updateLoyaltyExtendedFieldConfig(1: UpdateLoyaltyExtendedFieldRequest request) throws (1: EMFException ex)"
        story: EF-US-02
      - signature: "LoyaltyExtendedFieldConfig deleteLoyaltyExtendedFieldConfig(1: i64 id, 2: i64 orgId) throws (1: EMFException ex)"
        story: EF-US-03
      - signature: "LoyaltyExtendedFieldListResponse getLoyaltyExtendedFieldConfigs(1: i64 orgId, 2: optional string scope, 3: bool includeInactive, 4: i32 page, 5: i32 size) throws (1: EMFException ex)"
        story: EF-US-04

apis:
  - method: POST
    path: /v3/extendedfields/config
    story: EF-US-01
    request:
      name: string (required)
      scope: string (required, validated: SUBSCRIPTION_META)
      data_type: string (required, validated: STRING|NUMBER|BOOLEAN|DATE|ENUM)
      is_mandatory: boolean (required)
      default_value: string (optional)
      enum_values: list<string> (required when data_type=ENUM; null otherwise)
    response_201:
      id: long
      org_id: long
      name: string
      scope: string
      data_type: string
      is_mandatory: boolean
      default_value: string
      enum_values: list<string> (null if not ENUM)
      is_active: boolean
      created_on: string (UTC ISO-8601)
      last_updated_on: string (UTC ISO-8601)
    errors:
      400: invalid scope or data_type
      400: data_type=ENUM but enum_values null or empty
      409: (org_id, scope, name) already exists

  - method: PUT
    path: /v3/extendedfields/config/{id}
    story: EF-US-02
    request:
      is_mandatory: boolean (optional)
      default_value: string (optional)
      enum_values: list<string> (optional, updatable for ENUM type)
    immutable_fields: [name, scope, data_type]
    response_200: LoyaltyExtendedFieldConfig (updated)
    errors:
      400: attempt to change immutable fields
      404: id not found for caller's org_id

  - method: DELETE
    path: /v3/extendedfields/config/{id}
    story: EF-US-03
    behaviour:
      - "ACTIVE → INACTIVE: 200/204 (idempotent)"
      - "already INACTIVE: 200/204 (idempotent)"
      - "never existed: 404"
    response_200:
      id: long
      is_active: false
    errors:
      404: id never existed for caller's org_id

  - method: GET
    path: /v3/extendedfields/config
    story: EF-US-04
    query_params:
      scope: string (optional)
      includeInactive: boolean (default false)
      page: int (default 0)
      size: int (default 20, max 100)
    response_200:
      content: list<LoyaltyExtendedFieldConfig>
      page: int
      size: int
      totalElements: int
      totalPages: int
    errors:
      400: invalid filter values

validation_rules:
  trigger: "POST /v3/subscriptions OR PUT /v3/subscriptions/{id} with extendedFields present"
  rules:
    - "R-01: scope must be SUBSCRIPTION_META (400 if not)"
    - "R-02: key must exist in loyalty_extended_fields for (org_id, scope=SUBSCRIPTION_META, is_active=1) (400 if not)"
    - "R-03: value data type must match loyalty_extended_fields.data_type (400 if mismatch)"
    - "R-03a: when data_type=ENUM, value must be one of the registered enum_values (400 if not in allowed list)"
    - "R-04: all is_mandatory=true fields for (org_id, SUBSCRIPTION_META) must be present (400 if missing)"
  null_guard: "null extendedFields on PUT → preserve existing values (R-33)"
  empty_list: "empty list [] on PUT → clear all EF values"
  deactivation: "Deactivated EF config (is_active=0) does NOT affect existing subscription program values — only new write events are blocked (D-18)"

allowed_values:
  scope: [SUBSCRIPTION_META]
  data_type: [STRING, NUMBER, BOOLEAN, DATE, ENUM]
  is_active: [0, 1]  # 1=active, 0=inactive

org_config:
  key: MAX_EF_COUNT_PER_ORG          # key name TBD — Architect to confirm exact key
  table: program_config_key_values
  default_value: 10

open_questions:
  - id: OQ-01
    question: "status column type: VARCHAR(ACTIVE/INACTIVE) vs is_active tinyint?"
    status: RESOLVED
    resolution: "is_active TINYINT(1) — D-14"
  - id: OQ-02
    question: "Org-level max EF count storage?"
    status: RESOLVED
    resolution: "program_config_key_values, default=10 — D-15"
  - id: OQ-03
    question: "Validation error response format: {code, message, field} or existing V3 error envelope?"
    status: OPEN
    owner: Designer
    phase: 7
  - id: OQ-04
    question: "DELETE idempotency?"
    status: RESOLVED
    resolution: "Idempotent — 200/204 for both ACTIVE→INACTIVE and already-INACTIVE; 404 for never-existed — D-16"
  - id: OQ-05
    question: "Deactivated EF impact on existing subscription programs?"
    status: RESOLVED
    resolution: "No impact on existing values; new events only validate against active fields — D-18"
  - id: OQ-06
    question: "ENUM allowed values storage: enum_values VARCHAR column on loyalty_extended_fields OR child table loyalty_extended_field_enum_values?"
    status: OPEN
    owner: Architect
    phase: 6

guardrails_applicable: [G-01, G-02, G-03, G-04, G-05, G-06, G-07, G-08, G-09, G-11, G-12]
critical_guardrails:
  G-01: "UTC timestamps — created_on + last_updated_on"
  G-02: "Null safety — empty list not null for list responses"
  G-03: "Security — all endpoints require org-level auth"
  G-07: "Multi-tenancy — every DB query includes org_id filter"
  G-07.1: "Tenancy — org_id from auth context, never from request body"
  G-09.5: "Thrift backward compat — new fields must be optional"
---
