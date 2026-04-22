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
          - "[ ] data_type must be STRING | NUMBER | BOOLEAN | DATE; invalid returns 400"
          - "[ ] status defaults to ACTIVE"
          - "[ ] created_on and last_updated_on populated in UTC"
          - "[ ] Response includes created record with generated id"

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
          - "[ ] DELETE /v3/extendedfields/config/{id} sets status=INACTIVE (no row deletion)"
          - "[ ] Non-existent id or wrong org_id returns 404"
          - "[ ] Deactivated field no longer passes validation when consumed"
          - "[ ] Idempotency behaviour TBD by Architect (OQ-04)"

      - id: EF-US-04
        title: List EF Definitions
        complexity: SMALL
        acceptance_criteria:
          - "[ ] GET /v3/extendedfields/config returns all EF configs for caller's org_id"
          - "[ ] Supports query params: scope, status, page, size"
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
          - "[ ] Each entry: key must match ACTIVE record in loyalty_extended_fields for (org_id, scope)"
          - "[ ] Each entry: value data type must match registered data_type"
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
          `status`           VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE',
          `created_on`       DATETIME      NOT NULL,
          `last_updated_on`  DATETIME      NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_org_scope_name` (`org_id`, `scope`, `name`),
          KEY `idx_org_scope_status` (`org_id`, `scope`, `status`)
        );
      open_question: "OQ-01 — status column: VARCHAR(ACTIVE/INACTIVE) per BRD vs is_active tinyint per cc-stack-crm convention"

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
        - "5: required string dataType"
        - "6: required bool isMandatory"
        - "7: optional string defaultValue"
        - "8: required string status"
        - "9: required string createdOn"
        - "10: required string lastUpdatedOn"

    - name: CreateLoyaltyExtendedFieldRequest
      fields:
        - "1: required i64 orgId"
        - "2: required string name"
        - "3: required string scope"
        - "4: required string dataType"
        - "5: required bool isMandatory"
        - "6: optional string defaultValue"

    - name: UpdateLoyaltyExtendedFieldRequest
      fields:
        - "1: required i64 id"
        - "2: required i64 orgId"
        - "3: optional bool isMandatory"
        - "4: optional string defaultValue"

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
      - signature: "LoyaltyExtendedFieldListResponse getLoyaltyExtendedFieldConfigs(1: i64 orgId, 2: optional string scope, 3: optional string status, 4: i32 page, 5: i32 size) throws (1: EMFException ex)"
        story: EF-US-04

apis:
  - method: POST
    path: /v3/extendedfields/config
    story: EF-US-01
    request:
      name: string (required)
      scope: string (required, validated: SUBSCRIPTION_META)
      data_type: string (required, validated: STRING|NUMBER|BOOLEAN|DATE)
      is_mandatory: boolean (required)
      default_value: string (optional)
    response_201:
      id: long
      org_id: long
      name: string
      scope: string
      data_type: string
      is_mandatory: boolean
      default_value: string
      status: string
      created_on: string (UTC ISO-8601)
      last_updated_on: string (UTC ISO-8601)
    errors:
      400: invalid scope or data_type
      409: (org_id, scope, name) already exists

  - method: PUT
    path: /v3/extendedfields/config/{id}
    story: EF-US-02
    request:
      is_mandatory: boolean (optional)
      default_value: string (optional)
    immutable_fields: [name, scope, data_type]
    response_200: LoyaltyExtendedFieldConfig (updated)
    errors:
      400: attempt to change immutable fields
      404: id not found for caller's org_id

  - method: DELETE
    path: /v3/extendedfields/config/{id}
    story: EF-US-03
    response_200:
      id: long
      status: INACTIVE
    errors:
      404: id not found for caller's org_id

  - method: GET
    path: /v3/extendedfields/config
    story: EF-US-04
    query_params:
      scope: string (optional)
      status: string (optional)
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
    - "R-02: key must exist in loyalty_extended_fields for (org_id, scope=SUBSCRIPTION_META, status=ACTIVE) (400 if not)"
    - "R-03: value data type must match loyalty_extended_fields.data_type (400 if mismatch)"
    - "R-04: all is_mandatory=true fields for (org_id, SUBSCRIPTION_META) must be present (400 if missing)"
  null_guard: "null extendedFields on PUT → preserve existing values (R-33)"
  empty_list: "empty list [] on PUT → clear all EF values"

allowed_values:
  scope: [SUBSCRIPTION_META]
  data_type: [STRING, NUMBER, BOOLEAN, DATE]
  status: [ACTIVE, INACTIVE]

open_questions:
  - id: OQ-01
    question: "status column type: VARCHAR(ACTIVE/INACTIVE) vs is_active tinyint per cc-stack-crm convention?"
    owner: Architect
    phase: 4
  - id: OQ-02
    question: "Org-level max EF count storage: program_config_key_values or separate table?"
    owner: Architect
    phase: 4
  - id: OQ-03
    question: "Validation error response format: {code, message, field} or existing V3 error envelope?"
    owner: Designer
    phase: 7
  - id: OQ-04
    question: "DELETE idempotency: 200 or 409 when field is already INACTIVE?"
    owner: Architect
    phase: 4
  - id: OQ-05
    question: "When EF config deactivated: should existing subscription programs with that field's value be affected?"
    owner: Architect
    phase: 4

guardrails_applicable: [G-01, G-02, G-03, G-04, G-05, G-06, G-07, G-08, G-09, G-11, G-12]
critical_guardrails:
  G-01: "UTC timestamps — created_on + last_updated_on"
  G-02: "Null safety — empty list not null for list responses"
  G-03: "Security — all endpoints require org-level auth"
  G-07: "Multi-tenancy — every DB query includes org_id filter"
  G-07.1: "Tenancy — org_id from auth context, never from request body"
  G-09.5: "Thrift backward compat — new fields must be optional"
---
