---
feature_id: loyaltyExtendedFields
jira: CAP-183124
domain: loyalty.subscription.extended_fields
phase: BA
date: 2026-04-22
confidence_overall: C5

epics:
  - id: EF-EPIC-01
    name: EF Config Registry CRUD
    stories: [EF-US-01, EF-US-02, EF-US-03, EF-US-04]
    confidence: C6
  - id: EF-EPIC-02
    name: EF Validation on Subscription Programs
    stories: [EF-US-05, EF-US-06]
    confidence: C5
  - id: EF-EPIC-03
    name: Model Correction
    stories: [EF-US-07]
    confidence: C7

dependencies:
  - "thrift-ifaces-emf: new structs + EMFService methods required before emf-parent implementation"
  - "cc-stack-crm schema merged before emf-parent DAO can be tested end-to-end"
  - "EF-US-07 (model fix) should be done first — tests BT-EF-01 to BT-EF-06 reference wrong enum"

codebase_sources:
  intouch_api_v3:
    path: /Users/baljeetsingh/IdeaProjects/intouch-api-v3
    key_files:
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionProgram.java
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionFacade.java
      - src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java
      - src/test/java/com/capillary/intouchapiv3/unified/subscription/SubscriptionExtendedFieldsTest.java
    db: target_loyalty (no warehouse access)

  emf_parent:
    path: /Users/baljeetsingh/IdeaProjects/emf-parent
    key_files:
      - emf/src/main/resources/warehouse-database.properties
    db: warehouse (existing access)
    new_files_needed:
      - service: LoyaltyExtendedFieldService (business logic)
      - dao: LoyaltyExtendedFieldDao (warehouse DB)
      - entity: LoyaltyExtendedField (JPA/JDBC entity)

  thrift_ifaces_emf:
    path: /Users/baljeetsingh/IdeaProjects/thrifts/thrift-ifaces-emf
    key_files:
      - emf.thrift
    changes:
      - new_structs: [LoyaltyExtendedFieldConfig, LoyaltyExtendedFieldRequest, LoyaltyExtendedFieldListResponse]
      - new_service_methods: [createLoyaltyExtendedFieldConfig, updateLoyaltyExtendedFieldConfig, deleteLoyaltyExtendedFieldConfig, getLoyaltyExtendedFieldConfigs]

  cc_stack_crm:
    path: /Users/baljeetsingh/IdeaProjects/cc-stack-crm
    schema_path: schema/dbmaster/warehouse/
    new_files:
      - loyalty_extended_fields.sql

entities:
  loyalty_extended_fields:
    db: warehouse
    table: loyalty_extended_fields
    columns:
      id: "BIGINT PK AI"
      org_id: "BIGINT NOT NULL"
      name: "VARCHAR(100) NOT NULL"
      scope: "VARCHAR(50) NOT NULL — app-validated: SUBSCRIPTION_META (extensible)"
      data_type: "VARCHAR(30) NOT NULL — STRING | NUMBER | BOOLEAN | DATE"
      is_mandatory: "BOOLEAN NOT NULL DEFAULT FALSE"
      default_value: "VARCHAR(255) NULL"
      status: "VARCHAR(20) NOT NULL DEFAULT ACTIVE — ACTIVE | INACTIVE"
      created_on: "DATETIME NOT NULL"
      last_updated_on: "DATETIME NOT NULL"
    indexes:
      - unique: [org_id, scope, name]
      - lookup: [org_id, scope, status]

  SubscriptionProgram_ExtendedField:
    db: MongoDB
    collection: subscription_programs
    embedded_in: SubscriptionProgram.extendedFields
    fields:
      scope: "String — was 'type: ExtendedFieldType'; rename required"
      key: "String — maps to loyalty_extended_fields.name"
      value: "String — stored as string; type validated at write time"

apis:
  - method: POST
    path: /v3/extendedfields/config
    layer: V3 + EMF (Thrift)
    story: EF-US-01
    request_fields: [name, scope, data_type, is_mandatory, default_value]
    response: LoyaltyExtendedFieldConfig (with id)
    errors: [400 invalid scope/data_type, 409 duplicate]

  - method: PUT
    path: /v3/extendedfields/config/{id}
    layer: V3 + EMF (Thrift)
    story: EF-US-02
    request_fields: [is_mandatory, default_value]
    immutable_fields: [name, scope, data_type]
    errors: [400 invalid fields, 404 not found]

  - method: DELETE
    path: /v3/extendedfields/config/{id}
    layer: V3 + EMF (Thrift)
    story: EF-US-03
    behaviour: soft-delete (status=INACTIVE)
    errors: [404 not found]

  - method: GET
    path: /v3/extendedfields/config
    layer: V3 + EMF (Thrift)
    story: EF-US-04
    query_params: [scope, status, page, size]
    response: paginated list of LoyaltyExtendedFieldConfig
    errors: [400 invalid filters]

validation_rules:
  trigger: "POST /v3/subscriptions OR PUT /v3/subscriptions/{id} with extendedFields present"
  rules:
    - "scope must be SUBSCRIPTION_META"
    - "key must exist in loyalty_extended_fields (org_id + scope + status=ACTIVE)"
    - "value data type must match loyalty_extended_fields.data_type"
    - "all is_mandatory=true fields for (org_id, scope) must be present"
  null_guard: "null extendedFields on PUT preserves existing values (R-33)"
  empty_list: "empty list [] on PUT clears all EF values"

model_fix:
  file: src/main/java/com/capillary/intouchapiv3/unified/subscription/enums/ExtendedFieldType.java
  action: DELETE entire file
  field_rename:
    from: "SubscriptionProgram.ExtendedField.type (ExtendedFieldType)"
    to: "SubscriptionProgram.ExtendedField.scope (String)"
  tests_to_update: [BT-EF-01, BT-EF-02, BT-EF-03, BT-EF-04, BT-EF-05, BT-EF-06]
  old_values: [CUSTOMER_EXTENDED_FIELD, TXN_EXTENDED_FIELD]
  new_values: [SUBSCRIPTION_META]

open_questions:
  - id: OQ-01
    question: "status column: VARCHAR(ACTIVE/INACTIVE) or is_active tinyint?"
    owner: Architect
  - id: OQ-02
    question: "Org-level max EF count storage: program_config_key_values or separate table?"
    owner: Architect
  - id: OQ-03
    question: "Validation error response format"
    owner: Designer
  - id: OQ-04
    question: "DELETE idempotency: 200 or 409 when already INACTIVE?"
    owner: Architect

guardrails_applicable: [G-01, G-02, G-03, G-04, G-05, G-06, G-07, G-08, G-09, G-11, G-12]
critical_guardrails: [G-03, G-07]
---
