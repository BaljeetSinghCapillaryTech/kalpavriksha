# Session Memory -- subscription-program-revamp
> Ticket: aidlc/subscription_v1
> Started: 2026-04-14
> Last updated: 2026-04-14 (Phase 0)

## Domain Terminology
| Term | Definition | Source |
|------|-----------|--------|
| Tier | A loyalty program level (e.g., Silver, Gold, Platinum) with eligibility criteria, benefits, and renewal logic | BRD S3 |
| Slab | Internal name for tier in emf-parent codebase (ProgramSlab entity) | Codebase |
| Benefit | A reward or entitlement linked to a tier -- currently implemented as promotions in V3 Promotions | BRD S7.2 |
| Benefit Category | A metadata grouping layer that organizes benefit instances across tier programs (e.g., Welcome Gift, Upgrade Bonus) | BRD Epic 4 |
| Benefit Instance | A configured reward value linked to exactly one Category and one Tier | BRD Epic 4 |
| Subscription Program | A membership program (tier-based or non-tier) with duration, pricing, benefits, and lifecycle states | BRD Epic 3 |
| Tier-Based Subscription | Subscription that locks member into a specific loyalty tier for the subscription duration | BRD E3 |
| Non-Tier Subscription | Subscription that grants benefits without affecting member's loyalty tier | BRD E3 |
| Maker-Checker | Approval workflow where config changes create a pending record reviewed by an approver before going live | BRD E1-US4 |
| aiRa | Capillary's conversational AI assistant embedded in the configuration flow | BRD S5 |
| Context Layer | Structured JSON representing current program state (tiers, benefits, member distribution, change history) for aiRa | BRD S8 |
| Impact Simulation | Forecasting member distribution changes before publishing a config change | BRD E1-US6 |
| Comparison Matrix | Side-by-side tier comparison view (rows = config dimensions, columns = tiers) replacing the flat card list | BRD E1-US1 |
| Program Config | Global tier settings -- KPI type, upgrade sequence, validity periods | BRD S8.1 |
| Garuda | Capillary's new UI platform built on module federation, React 18, atomic design | BRD S3.5 |
| EMF | Entity Management Framework -- core Java service handling tier/slab entities, strategies, Thrift services | CLAUDE.md |
| PEB | Points Engine Backend -- handles tier downgrade calculators | CLAUDE.md |
| Enrollment | A member's subscription linkage record, with states PENDING, ACTIVE, EXPIRED | BRD E3-US4 |

## Codebase Behaviour
| Behaviour | Evidence | Confidence |
|-----------|----------|------------|
| partner_programs MySQL table has: id, org_id, loyalty_program_id, type (EXTERNAL/SUPPLEMENTARY), name, description, is_active, is_tier_based, points_exchange_ratio, expiry_date, backup_partner_program_id | cc-stack-crm/schema/dbmaster/warehouse/partner_programs.sql | C7 _(BA)_ |
| partner_program_tier_sync_configuration maps partner_program_slab_id to loyalty_program_slab_id -- this is how tier linkage works today | cc-stack-crm/schema/dbmaster/warehouse/partner_program_tier_sync_configuration.sql | C7 _(BA)_ |
| supplementary_partner_program_enrollment has membership_start_date, membership_end_date -- supports future-dated enrollments | cc-stack-crm/schema/dbmaster/warehouse/supplementary_partner_program_enrollment.sql | C7 _(BA)_ |
| supplementary_membership_history tracks lifecycle: STARTED, RENEWAL_INITIATED, RENEWED, EXPIRED, REVOKED_BY_MERGE, BACKUP_STARTED, EARLY_EXPIRY | cc-stack-crm/schema/dbmaster/warehouse/supplementary_membership_history.sql | C7 _(BA)_ |
| supplementary_membership_cycle_details stores cycle_type (DAYS/MONTHS) + cycle_value -- this is subscription duration | cc-stack-crm/schema/dbmaster/warehouse/supplementary_membership_cycle_details.sql | C7 _(BA)_ |
| supplementary_partner_program_expiry_reminder stores days_in_expiry_reminder + communication_property_values -- existing reminder infra | cc-stack-crm/schema/dbmaster/warehouse/supplementary_partner_program_expiry_reminder.sql | C7 _(BA)_ |
| UnifiedPromotion is a @Document(collection="unified_promotions") MongoDB model in intouch-api-v3 with: metadata, activities, limits, parentId (versioning), version, comments, workflowMetadata, promotionSchedule | UnifiedPromotion.java in intouch-api-v3 | C7 _(BA)_ |
| UnifiedPromotion maker-checker uses parentId + version for edit-of-ACTIVE: new DRAFT created with parentId pointing to original ACTIVE doc | UnifiedPromotion.java, UnifiedPromotionRepository.java | C7 _(BA)_ |
| UnifiedPromotionRepository extends MongoRepository with status-aware queries (DRAFT, ACTIVE, PAUSED, STOPPED, PENDING_APPROVAL) | UnifiedPromotionRepository.java | C7 _(BA)_ |
| Extended Fields are brand-configurable custom fields with EntityType enum: CUSTOMER, REGULAR_TRANSACTION, RETURN_TRANSACTION, LINEITEM, LEAD, COMPANY, CARD, USERGROUP2 | ExtendedField.java in api/prototype | C7 _(BA)_ |
| Extended Fields are stored in MongoDB collections named by entityType (e.g., customer_extended_fields) with orgId + entityId + extendedFields map | ExtendedFieldsConsts.java | C7 _(BA)_ |
| Extended Fields support datatypes: INTEGER, STRING, DOUBLE, DATETIME, STANDARD_STRING, STANDARD_ENUM, CUSTOM_ENUM, DATE, STRING_SET | ExtendedField.DataType enum | C7 _(BA)_ |
| PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram exists in emf-parent -- takes PartnerProgramInfo, programId, orgId | emf-parent PointsEngineRuleConfigThriftImpl.java:252 | C7 _(BA)_ |
| UnifiedPromotion maker-checker is deeply coupled: journeyEditHandler hooks on PENDING_APPROVAL, communicationApprovalStatus on approval, promotion-specific validators, PromotionDataReconstructor, targetGroupFacade for pause/resume, @Lockable with promotion key | UnifiedPromotionFacade.java -- 6+ promotion-specific hooks in state transitions | C6 _(BA)_ |
| UnifiedPromotion edit-of-ACTIVE pattern: fetches ACTIVE, creates new DRAFT doc with parentId=ACTIVE.objectId, version+1. ACTIVE stays live until DRAFT approved. On approve: old ACTIVE -> SNAPSHOT, DRAFT -> ACTIVE. | UnifiedPromotionFacade.java handleActiveOrPausedUpdate, createVersionedPromotion | C6 _(BA)_ |
| UnifiedPromotion state machine: DRAFT -> PENDING_APPROVAL -> ACTIVE (approve) or DRAFT (reject). ACTIVE -> PAUSED -> ACTIVE (resume). ACTIVE -> STOPPED. | PromotionStatus.java state diagram comment | C7 _(BA)_ |
| StatusChangeRequest uses @Pattern with hardcoded promotion actions: PENDING_APPROVAL, REVOKE, RESUME, PAUSE, STOP | StatusChangeRequest.java | C7 _(BA)_ |

## Key Decisions
| # | Decision | Rationale | Phase | Date |
|---|----------|-----------|-------|------|
| KD-01 | cc-stack-crm is included as read-only DB schema reference repo | Contains all MySQL databases, tables, schema, and indexes -- source of truth for database structure | Phase 0 | 2026-04-14 |
| KD-02 | thrift-ifaces-pointsengine-rules has carry-over modifications from prior work | Modified pointsengine_rules.thrift + pom.xml from aidlc-demo-v2 branch. Must review for conflicts. | Phase 0 | 2026-04-14 |
| KD-03 | ~~Feature named "subscription-program-revamp" covering BRD Epics E1-E4~~ SUPERSEDED by KD-04 | ~~Full scope of Tiers & Benefits PRD v3~~ | Phase 0 | 2026-04-14 |
| KD-04 | Scope: E3 (Subscription Programs) ONLY. E1, E2, E4 are OUT OF SCOPE for this pipeline run. | User decision -- focused delivery on subscription programs first. Other epics will be separate pipeline runs. | Phase 1 (BA) | 2026-04-14 |
| KD-05 | REST APIs + CRUD + Maker-Checker in intouch-api-v3 | Knowledge Bank #1 | Phase 1 (BA) | 2026-04-14 |
| KD-06 | Thrift calls (existing + new) in emf-parent | Knowledge Bank #2 | Phase 1 (BA) | 2026-04-14 |
| KD-07 | Subscription Programs ARE partner programs (existing entity). Existing Thrift: PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram | Knowledge Bank #3 | Phase 1 (BA) | 2026-04-14 |
| KD-08 | CRUD + validations + maker-checker + auditing ONLY. Simulation is FUTURE SCOPE. | Knowledge Bank #4 | Phase 1 (BA) | 2026-04-14 |
| KD-09 | Maker-checker authorization (per user level) handled by UI, not backend | Knowledge Bank #5 | Phase 1 (BA) | 2026-04-14 |
| KD-10 | Maker-checker must be GENERIC (reusable for Tiers, Benefits later). Current UnifiedPromotion maker-checker is too coupled. | Knowledge Bank #6 | Phase 1 (BA) | 2026-04-14 |
| KD-11 | MongoDB for subscription program metadata + MySQL for final data in existing tables (warehouse.partner_programs etc.) | Knowledge Bank #7, follows UnifiedPromotion pattern | Phase 1 (BA) | 2026-04-14 |
| KD-12 | Benefits stored as benefit_id references/mappings on subscription programs | Knowledge Bank #9 | Phase 1 (BA) | 2026-04-14 |
| KD-13 | Subscription Program to Program is 1-1 mapping (a subscription can only belong to one program) | Knowledge Bank #10 | Phase 1 (BA) | 2026-04-14 |
| KD-14 | E3 user story scope: E3-US1 (Listing), E3-US2 (CRUD+validations+maker-checker), E3-US4 (Lifecycle+enrollment), E3-US5 (API contract) are IN SCOPE. E3-US3 (aiRa) is OUT OF SCOPE -- future. | User decision | Phase 1 (BA) | 2026-04-14 |
| KD-15 | Auditing is OUT OF SCOPE -- future scope, same as simulation | User decision | Phase 1 (BA) | 2026-04-14 |
| KD-16 | Price is NOT a first-class subscription field. It is an Extended Field created by brands and attached to subscriptions. Research api/prototype for extended fields model. | User decision -- do NOT model price on subscription entity | Phase 1 (BA) | 2026-04-14 |
| KD-17 | Tier-related fields (linked_tier_id, tier_downgrade_on_exit, downgrade_target) already exist in MySQL via partner_program_tier_sync_configuration + partner_program_slabs. Reuse/extend existing columns -- do NOT duplicate to MongoDB. | User decision + evidence from cc-stack-crm DDLs | Phase 1 (BA) | 2026-04-14 |
| KD-18 | New metadata fields (migrate_on_expiry, restrict_to_one_active, group_tag, reminders, custom_fields) go in MongoDB subscription document. Follow UnifiedPromotion pattern in intouch-api-v3. | User decision -- no new MySQL columns for new fields | Phase 1 (BA) | 2026-04-14 |
| KD-19 | NO Flyway migrations for new columns. Only reuse/extend existing MySQL schema. New metadata in MongoDB only. | Derived from KD-17 + KD-18 | Phase 1 (BA) | 2026-04-14 |
| KD-20 | Extended Fields EntityType enum in api/prototype does NOT currently include SUBSCRIPTION or PARTNER_PROGRAM. A new EntityType may need to be added for subscription extended fields. | ExtendedField.java EntityType enum -- only has CUSTOMER, TRANSACTION, LINEITEM, LEAD, COMPANY, CARD, USERGROUP2 | Phase 1 (BA) | 2026-04-14 |
| KD-21 | Maker-checker approach: Option (b) -- extract reusable flow pattern from UnifiedPromotion, or clean-room if extraction risks regression | User decision | Phase 1 (BA) | 2026-04-14 |
| KD-22 | Maker-checker extraction assessment: RECOMMEND CLEAN-ROOM IMPLEMENTATION [C5]. UnifiedPromotion's maker-checker is deeply coupled to promotion-specific concerns: (1) journeyEditHandler hooks on PENDING_APPROVAL transition, (2) communicationApprovalStatus on approval, (3) promotion-specific validatorService.validatePromotionUpdate, (4) PromotionDataReconstructor for approval, (5) targetGroupFacade for pause/resume, (6) @Lockable with promotion-specific key pattern. The state machine PATTERN (DRAFT->PENDING_APPROVAL->ACTIVE, parentId/version for edit-of-active, setStatusAndSave) is reusable, but the implementation has 6+ promotion-specific hooks woven into every transition. Extracting safely would require refactoring UnifiedPromotionFacade (500+ lines), creating an abstract base, and ensuring zero regression on live promotions -- high risk for a feature branch. Clean-room: implement the same pattern (parentId, version, status enum, state transitions) in a new generic package with pluggable hooks, without touching UnifiedPromotion code. | Code analysis of UnifiedPromotionFacade.java -- reviewUnifiedPromotion, changePromotionStatus, updateUnifiedPromotion, handleActiveOrPausedUpdate, createVersionedPromotion methods | Phase 1 (BA) | 2026-04-14 |
| KD-23 | Custom Fields: ALL 3 levels in scope -- META (program metadata), LINK (captured at enrollment), DELINK (captured at unenrollment). Full 3-level custom field model required. | User decision | Phase 1 (BA) | 2026-04-14 |
| KD-24 | Reminders: Publish-on-approve pattern. During DRAFT/PENDING_APPROVAL, reminders live in MongoDB only. On APPROVAL, reminders are synced/written to MySQL supplementary_partner_program_expiry_reminder. No direct MySQL writes during CRUD/DRAFT phase. | User decision -- MongoDB is source of truth during pending lifecycle, MySQL is final committed state after approval | Phase 1 (BA) | 2026-04-14 |
| KD-25 | Publish-on-approve is the GENERAL pattern: ALL subscription data lives in MongoDB during DRAFT/PENDING_APPROVAL. On APPROVAL, the full subscription state is persisted to MySQL (partner_programs, supplementary_membership_cycle_details, supplementary_partner_program_expiry_reminder, partner_program_tier_sync_configuration, etc.) | Derived from KD-24 -- generalised to all subscription data, not just reminders | Phase 1 (BA) | 2026-04-14 |

## Constraints
| # | Constraint | Source |
|---|-----------|--------|
| C-01 | API-first contract: validation logic lives in API, not frontend. Both UI and aiRa call same endpoints. | BRD S10 |
| C-02 | Hybrid Interface (Option A recommended): Direct UI for simple edits + aiRa for structural changes | BRD S5 |
| C-03 | Maker-checker is native to the platform. Every config change creates a pending record. | BRD E1-US4 |
| C-04 | Benefits are first-class objects (not promotions). Own listing, categories, lifecycle. | BRD E2 |
| C-05 | Two subscription models must be supported: Tier-Based and Non-Tier | BRD E3 |
| C-06 | All benefit instance config changes follow DRAFT -> PENDING_APPROVAL -> ACTIVE state machine | BRD Epic 4 S5 |
| C-07 | Phase 1 scope excludes: milestone/streak tiers, fully conversational interface (Option B), real-time member streaming, custom fields for Promotions | BRD S11 |
| C-08 | This pipeline run covers E3 (Subscription Programs) ONLY. E1 (Tier Intelligence), E2 (Benefits as Product), E4 (Benefit Categories) are out of scope. | KD-04, User decision _(BA)_ |
| C-09 | Simulation is future scope -- not part of this implementation | KB #4 _(BA)_ |
| C-10 | Maker-checker authorization is a UI concern, not backend | KB #5 _(BA)_ |
| C-11 | E3-US3 (aiRa-Assisted Creation) is out of scope for this pipeline run | User decision, KD-14 _(BA)_ |
| C-12 | Auditing is out of scope for this pipeline run | User decision, KD-15 _(BA)_ |

## Open Questions
| # | Question | Source | Status |
|---|----------|--------|--------|
| OQ-01 | Does the program context API exist, or does it need to be built? What is the latency at p99? | BRD S12 | Deferred -- E3 context API needs subscription data only _(BA)_ |
| OQ-02 | Impact simulation -- is this calculated in real-time or queued? What is the acceptable SLA? | BRD S12 | Closed -- simulation is future scope (KB #4, KD-08) _(BA)_ |
| OQ-03 | Maker-checker: is this per-user-role or per-program? Who configures who the approvers are? | BRD S12 | Open -- still relevant for E3 maker-checker _(BA)_ |
| OQ-04 | Can a benefit be linked to multiple programs, or is it always scoped to one? | BRD S12 | Open -- relevant for subscription-benefit linkage _(BA)_ |
| OQ-05 | Should aiRa handle multi-turn disambiguation across multiple turns, or is each interaction single-turn? | BRD S12 | Closed -- E3-US3 (aiRa) is out of scope (KD-14) _(BA)_ |
| OQ-06 | Is the downgrade "validate on return transaction" toggle going to be surfaced in the new UI, or deprecated? | BRD S12 | Deferred -- E1 scope, not E3 _(BA)_ |
