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
    note: "3 stories (was 4) — EF-US-03 (Deactivate) merged into EF-US-02 (PUT); no separate DELETE endpoint (D-24)"
    stories:
      - id: EF-US-01
        title: Create EF Definition
        complexity: MEDIUM
        acceptance_criteria:
          - "[ ] POST /v3/extendedfields/config creates row in loyalty_extended_fields for caller's org + program"
          - "[ ] program_id required in request body"
          - "[ ] Uniqueness: (org_id, program_id, scope, name) — duplicate returns 409 regardless of is_active (D-30)"
          - "[ ] scope must be SUBSCRIPTION_META; invalid scope returns 400"
          - "[ ] data_type must be STRING | NUMBER | BOOLEAN | DATE; invalid returns 400"
          - "[ ] is_active defaults to 1; created_on and updated_on populated (TIMESTAMP UTC)"
          - "[ ] Response includes created record with generated id"
          - "[ ] Program cannot exceed MAX_EF_COUNT (from program_config_key_values, default=10) — 400 if exceeded"

      - id: EF-US-02
        title: Update EF Definition (including soft-delete)
        complexity: SMALL
        acceptance_criteria:
          - "[ ] PUT /v3/extendedfields/config/{id} updates row for caller's org"
          - "[ ] Only name and is_active are mutable (D-23)"
          - "[ ] scope, data_type, is_mandatory, default_value, program_id are immutable"
          - "[ ] Name change: re-validates uniqueness (org_id, program_id, scope, new_name); 409 if conflict"
          - "[ ] is_active=false performs soft-delete (D-24); idempotent — 200 if already inactive"
          - "[ ] Non-existent id or wrong org_id returns 404"
          - "[ ] updated_on auto-updated by MySQL; updated_by set from auth context"
          - "[ ] Deactivated field no longer valid for new subscription writes; existing values unaffected (D-18)"

      - id: EF-US-03
        title: List EF Definitions
        complexity: SMALL
        acceptance_criteria:
          - "[ ] GET /v3/extendedfields/config requires program_id query param"
          - "[ ] Returns EF configs for caller's org_id + program_id"
          - "[ ] Supports query params: scope, includeInactive (default false), page, size"
          - "[ ] Default: only active (is_active=1) records"
          - "[ ] includeInactive=true returns all records"
          - "[ ] Paginated; empty returns 200 with empty list; max 100/page"

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
          - "[ ] Each entry: value data type must match registered data_type (STRING/NUMBER/BOOLEAN/DATE)"
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
          `program_id`       BIGINT        NOT NULL,
          `name`             VARCHAR(100)  NOT NULL,
          `scope`            VARCHAR(50)   NOT NULL,
          `data_type`        VARCHAR(30)   NOT NULL,
          `is_mandatory`     TINYINT(1)    NOT NULL DEFAULT 0,
          `default_value`    VARCHAR(255)  NULL,
          `is_active`        TINYINT(1)    NOT NULL DEFAULT 1,
          `created_on`       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
          `updated_on`       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          `updated_by`       VARCHAR(100)  NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_org_prog_scope_name` (`org_id`, `program_id`, `scope`, `name`),
          KEY `idx_org_prog_scope_active` (`org_id`, `program_id`, `scope`, `is_active`)
        );
      decisions:
        - "D-14: is_active TINYINT(1)"
        - "D-22: ENUM out of scope"
        - "D-26: TIMESTAMP for UTC audit; updated_by added"
        - "D-29: program_id added — EF configs are program-scoped"
        - "D-30: uniqueness enforced regardless of is_active"

  modified_models:
    - entity: SubscriptionProgram.ExtendedField
      db: MongoDB
      collection: subscription_programs
      changes:
        - field: type (ExtendedFieldType)
          action: DELETE_FIELD   # D-27: deleted entirely, not renamed
          reason: "scope always SUBSCRIPTION_META for subscription programs; validated server-side"
        - field: key (String)
          action: REPLACE
          new_field: id
          type_after: Long
          reason: "D-28: validation by id, not name; name is display-only"
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
        - "3: required i64 programId"
        - "4: required string name"
        - "5: required string scope"
        - "6: required string dataType"    # STRING | NUMBER | BOOLEAN | DATE
        - "7: required bool isMandatory"
        - "8: optional string defaultValue"
        - "9: required bool isActive"
        - "10: required string createdOn"
        - "11: required string updatedOn"
        - "12: optional string updatedBy"

    - name: CreateLoyaltyExtendedFieldRequest
      fields:
        - "1: required i64 orgId"          # from auth context
        - "2: required i64 programId"
        - "3: required string name"
        - "4: required string scope"
        - "5: required string dataType"
        - "6: required bool isMandatory"
        - "7: optional string defaultValue"
        - "8: optional string createdBy"

    - name: UpdateLoyaltyExtendedFieldRequest
      fields:
        - "1: required i64 id"
        - "2: required i64 orgId"          # from auth context
        - "3: optional string name"
        - "4: optional bool isActive"
        - "5: optional string updatedBy"

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
      - signature: "LoyaltyExtendedFieldListResponse getLoyaltyExtendedFieldConfigs(1: i64 orgId, 2: required i64 programId, 3: optional string scope, 4: bool includeInactive, 5: i32 page, 6: i32 size) throws (1: EMFException ex)"
        story: EF-US-03

apis:
  - method: POST
    path: /v3/extendedfields/config
    story: EF-US-01
    request:
      program_id: long (required)
      name: string (required)
      scope: string (required, validated: SUBSCRIPTION_META)
      data_type: string (required, validated: STRING|NUMBER|BOOLEAN|DATE)
      is_mandatory: boolean (required)
      default_value: string (optional)
    note: "org_id from auth context only — not in request body (G-07.1)"
    response_201:
      id: long
      org_id: long
      program_id: long
      name: string
      scope: string
      data_type: string
      is_mandatory: boolean
      default_value: string
      is_active: boolean
      created_on: string (UTC ISO-8601)
      updated_on: string (UTC ISO-8601)
      updated_by: string
    errors:
      400: invalid scope or data_type
      409: (org_id, program_id, scope, name) already exists (D-30 — regardless of is_active)

  - method: PUT
    path: /v3/extendedfields/config/{id}
    story: EF-US-02
    note: "Handles update AND soft-delete — no separate DELETE endpoint (D-24)"
    request:
      name: string (optional — display rename only; uniqueness re-validated)
      is_active: boolean (optional — false = soft-delete; idempotent)
    immutable_fields: [scope, data_type, is_mandatory, default_value, program_id]
    response_200: LoyaltyExtendedFieldConfig (updated)
    errors:
      404: id not found for caller's org_id
      409: new name conflicts with existing record for (org_id, program_id, scope)

  - method: GET
    path: /v3/extendedfields/config
    story: EF-US-03
    query_params:
      program_id: long (required)
      scope: string (optional)
      includeInactive: boolean (default false)
      page: int (default 0)
      size: int (default 20, max 100)
    response_200:
      content: list<LoyaltyExtendedFieldConfig>
      page: int
      size: int
      totalElements: int
    errors:
      400: invalid filter values

validation_rules:
  trigger: "POST /v3/subscriptions OR PUT /v3/subscriptions/{id} with extendedFields present"
  rules:
    - "R-01: each extendedField.id must exist in loyalty_extended_fields for (org_id, program_id, is_active=1) — 400 if not (D-28)"
    - "R-02: value data type must match loyalty_extended_fields.data_type — 400 if mismatch"
    - "R-03: all is_mandatory=true fields for (org_id, program_id, SUBSCRIPTION_META) must be present — 400 if missing; does NOT apply when extendedFields is empty list []"
  null_guard: "null extendedFields on PUT → preserve existing values (R-33)"
  empty_list: "empty list [] on PUT → clear all EF values (destructive — needs product sign-off)"
  deactivation: "Deactivated EF (is_active=0) does NOT affect existing subscription program values; new writes blocked (D-18)"
  no_scope_in_request: "Scope not passed in subscription EF payload — always SUBSCRIPTION_META, validated server-side (D-27)"

allowed_values:
  scope: [SUBSCRIPTION_META]
  data_type: [STRING, NUMBER, BOOLEAN, DATE]   # ENUM removed — out of scope (D-22)
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
    question: "ENUM allowed values storage?"
    status: RESOLVED
    resolution: "ENUM data type removed from scope entirely — D-22"

guardrails_applicable: [G-01, G-02, G-03, G-04, G-05, G-06, G-07, G-08, G-09, G-11, G-12]
critical_guardrails:
  G-01: "UTC timestamps — created_on + last_updated_on"
  G-02: "Null safety — empty list not null for list responses"
  G-03: "Security — all endpoints require org-level auth"
  G-07: "Multi-tenancy — every DB query includes org_id filter"
  G-07.1: "Tenancy — org_id from auth context, never from request body"
  G-09.5: "Thrift backward compat — new fields must be optional"
---
