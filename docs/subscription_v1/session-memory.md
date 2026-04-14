# Session Memory -- subscription-program-revamp
> Ticket: aidlc/subscription_v1
> Started: 2026-04-14
> Last updated: 2026-04-14 (Phase 7 — Designer)

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
| supplementary_membership_history tracks CUSTOMER-SUBSCRIPTION enrollment lifecycle: LINKED, DELINKED, MEMBERSHIP_INITIATED, RENEWED, EXPIRED, REVOKED_BY_MERGE, BACKUP_STARTED, EARLY_EXPIRY. NOT for subscription program CRUD lifecycle (KD-32). | cc-stack-crm/schema/dbmaster/warehouse/supplementary_membership_history.sql + user clarification | C7 _(BA Q&A)_ |
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
| EmfMongoConfig uses includeFilters with FilterType.ASSIGNABLE_TYPE listing only UnifiedPromotionRepository.class -- new SubscriptionProgramRepository MUST be explicitly added to this list to route to emfMongoTemplate | EmfMongoConfig.java lines 27-33 | C7 _(Analyst Phase 2)_ |
| PartnerProgramInfo Thrift struct fields (verified): partnerProgramId, partnerProgramName, description, isTierBased, partnerProgramTiers, programToPartnerProgramPointsRatio, partnerProgramUniqueIdentifier, partnerProgramType (EXTERNAL/SUPPLEMENTARY), partnerProgramMembershipCycle, isSyncWithLoyaltyTierOnDowngrade, loyaltySyncTiers, updatedViaNewUI, expiryDate, backupProgramId | pointsengine_rules.thrift lines 402-417 | C7 _(Analyst Phase 2)_ |
| Thrift PartnerProgramCycleType enum has ONLY DAYS and MONTHS -- no YEARS value exists | pointsengine_rules.thrift lines 387-390 | C7 _(Analyst Phase 2)_ |
| supplementary_membership_cycle_details MySQL enum is ONLY DAYS/MONTHS -- no YEARS | cc-stack-crm supplementary_membership_cycle_details.sql | C7 _(Analyst Phase 2)_ |
| createOrUpdatePartnerProgram Thrift path writes to 3 MySQL tables: partner_programs, supplementary_membership_cycle_details, partner_program_tier_sync_configuration. Expiry reminders use a SEPARATE Thrift method: createOrUpdateExpiryReminderForPartnerProgram | PointsEngineRuleService.java createOrUpdateSupplementaryPartnerProgram, lines 1750-1766 | C7 _(Analyst Phase 2)_ |
| PointsEngineRuleService hard-caps expiry reminders at 2 per partner program (RuntimeException thrown at >=2) | PointsEngineRuleService.java line 1642 | C7 _(Analyst Phase 2)_ |
| Enrollment path (PartnerProgramLinkingActionImpl) checks only expiry date via validatePartnerProgramExpiry -- does NOT check partner_program.is_active. Setting is_active=false does NOT block new enrollments | PartnerProgramLinkingActionImpl.java + PointsEngineEndpointActionUtils.java lines 1556-1577 | C7 _(Analyst Phase 2)_ |
| partner_programs table has partner_program_identifier column (varchar 127, NOT NULL) -- missing from BA schema listing. Must be generated on publish-on-approve. EMFUtils.generatePartnerProgramIdentifier() handles this for new programs | partner_programs.sql line 7; PointsEngineRuleService.java line 1862 | C7 _(Analyst Phase 2)_ |
| partner_programs has UNIQUE KEY (org_id, name) -- subscription names must be unique per org across ALL partner program types (EXTERNAL and SUPPLEMENTARY combined) | partner_programs.sql line 19 | C7 _(Analyst Phase 2)_ |
| UnifiedPromotion approval path has NO approver identity/role checks -- no @PreAuthorize, @Secured, or SecurityContext checks in the review flow | UnifiedPromotionFacade.java approve/reject path | C6 _(Analyst Phase 2)_ |
| supplementary_membership_history actual action enum values (with full prefix): SUPPLEMENTARY_MEMBERSHIP_STARTED, SUPPLEMENTARY_MEMBERSHIP_RENEWAL_INITIATED, SUPPLEMENTARY_MEMBERSHIP_RENEWED, SUPPLEMENTARY_MEMBERSHIP_EXPIRED, SUPPLEMENTARY_MEMBERSHIP_REVOKED_BY_MERGE, BACKUP_SUPPLEMENTARY_MEMBERSHIP_STARTED, PARTNER_PROGRAM_EARLY_EXPIRY | supplementary_membership_history.sql line 8 | C7 _(Analyst Phase 2)_ |
| supplementary_membership_history.source enum: LINKING, AUTO_DELINKING, DELINKING, UPDATE, MEMBERSHIP_ACTION, PP_EXPIRY_JOB, IMPORT, MERGE | supplementary_membership_history.sql line 7 | C7 _(Analyst Phase 2)_ |
| backup_partner_program_id is used via PartnerProgramExpiry MongoDB model (separate emf collection) to track expiry job state -- not a direct member migration trigger in enrollment path | PartnerProgramExpiry.java + PointsEngineRuleService.java updateBulkSPPExpiryJobStatus | C6 _(Analyst Phase 2)_ |
| supplementary_partner_program_enrollment has is_active column (tinyint DEFAULT 1) -- this was absent from BA's entity listing but exists in DDL | supplementary_partner_program_enrollment.sql line 8 | C7 _(Analyst Phase 2)_ |
| reviewUnifiedPromotion() in UnifiedPromotionFacade.java is a best-effort SAGA: Thrift success → MongoDB update. Thrift failure → set PUBLISH_FAILED in MongoDB. No distributed transaction. Compensation is partial (status flag, not rollback of MySQL). | UnifiedPromotionFacade.java lines 1379-1439; PromotionTransformerImpl.java lines 905-951 | C7 _(Cross-Repo Tracer Phase 5)_ |
| handlePromotionRejection() (line 1184) sets status=DRAFT. Comment stored in promotion.comments. No REJECTED state exists. Document is NOT deleted on reject. | UnifiedPromotionFacade.java line 1184 | C7 _(Cross-Repo Tracer Phase 5)_ |
| RequestManagementController uses orchestration/EntityType enum (PROMOTION, TARGET_GROUP, etc.) to route PUT /v3/requests/{entityType}/{entityId}/status. This is promotion-orchestration-specific, NOT a generic maker-checker router. Subscription does NOT plug into this. | RequestManagementController.java + RequestManagementFacade.java | C7 _(Cross-Repo Tracer Phase 5)_ |
| PartnerProgramInfo Thrift struct has NO isActive field (lines 402-417). PAUSE/ARCHIVE cannot use createOrUpdatePartnerProgram to set is_active=false. New Thrift method setPartnerProgramActive() is required. | pointsengine_rules.thrift lines 402-417 | C7 _(Cross-Repo Tracer Phase 5)_ |
| saveSupplementaryPartnerProgramEntity() line 1858: for existing programs, preserves oldPartnerProgram.isActive(). Line 1863: new programs default to isActive=true. Both via PePartnerProgramDao.saveAndFlush(). | PointsEngineRuleService.java lines 1841-1869 | C7 _(Cross-Repo Tracer Phase 5)_ |
| EmfMongoConfig.java 1-line change required for SubscriptionProgramRepository: add SubscriptionProgramRepository.class to classes={} array at line 32 in includeFilters. | EmfMongoConfig.java line 32 | C7 _(Cross-Repo Tracer Phase 5)_ |
| PartnerProgramLinkingActionImpl.getMembershipEndDateDate() handles DAYS (plusDays) and MONTHS (plusMonths) only. No YEARS case. KD-38 conversion (YEARS→MONTHS×12) must happen in intouch-api-v3 BEFORE the Thrift call. | PartnerProgramLinkingActionImpl.java lines 256-278 | C7 _(Cross-Repo Tracer Phase 5)_ |
| PePartnerProgramDao extends GenericDao with saveAndFlush. Has findActiveByLoyaltyProgram() (filter is_active=true). No native setActive query. Active state update requires JPA entity load + setActive() + saveAndFlush(). | PePartnerProgramDao.java | C7 _(Cross-Repo Tracer Phase 5)_ |
| emf.thrift has partnerProgramLinkingEvent, partnerProgramUpdateEvent, partnerProgramDeLinkingEvent but no subscription lifecycle events. No emf.thrift changes needed for subscription program CRUD. | emf.thrift lines 1795-1810 | C6 _(Cross-Repo Tracer Phase 5)_ |
| createOrUpdatePartnerProgram is NOT currently called from intouch-api-v3 -- no existing usage found. Subscription publish-on-approve will be the first caller from this service. New wrapper method needed in PointsEngineRulesThriftService. | PointsEngineRulesThriftService.java (grep: no createOrUpdatePartnerProgram method found) | C6 _(Cross-Repo Tracer Phase 5)_ |

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
| KD-20 | ~~Extended Fields EntityType enum may need SUBSCRIPTION added~~ SUPERSEDED by KD-28 | Superseded | Phase 1 (BA) | 2026-04-14 |
| KD-21 | Maker-checker approach: Option (b) -- extract reusable flow pattern from UnifiedPromotion, or clean-room if extraction risks regression | User decision | Phase 1 (BA) | 2026-04-14 |
| KD-22 | Maker-checker extraction assessment: RECOMMEND CLEAN-ROOM IMPLEMENTATION [C5]. UnifiedPromotion's maker-checker is deeply coupled to promotion-specific concerns: (1) journeyEditHandler hooks on PENDING_APPROVAL transition, (2) communicationApprovalStatus on approval, (3) promotion-specific validatorService.validatePromotionUpdate, (4) PromotionDataReconstructor for approval, (5) targetGroupFacade for pause/resume, (6) @Lockable with promotion-specific key pattern. The state machine PATTERN (DRAFT->PENDING_APPROVAL->ACTIVE, parentId/version for edit-of-active, setStatusAndSave) is reusable, but the implementation has 6+ promotion-specific hooks woven into every transition. Extracting safely would require refactoring UnifiedPromotionFacade (500+ lines), creating an abstract base, and ensuring zero regression on live promotions -- high risk for a feature branch. Clean-room: implement the same pattern (parentId, version, status enum, state transitions) in a new generic package with pluggable hooks, without touching UnifiedPromotion code. | Code analysis of UnifiedPromotionFacade.java -- reviewUnifiedPromotion, changePromotionStatus, updateUnifiedPromotion, handleActiveOrPausedUpdate, createVersionedPromotion methods | Phase 1 (BA) | 2026-04-14 |
| KD-23 | Custom Fields: ALL 3 levels in scope -- META (program metadata), LINK (captured at enrollment), DELINK (captured at unenrollment). Full 3-level custom field model required. | User decision | Phase 1 (BA) | 2026-04-14 |
| KD-24 | Reminders: Publish-on-approve pattern. During DRAFT/PENDING_APPROVAL, reminders live in MongoDB only. On APPROVAL, reminders are synced/written to MySQL supplementary_partner_program_expiry_reminder. No direct MySQL writes during CRUD/DRAFT phase. | User decision -- MongoDB is source of truth during pending lifecycle, MySQL is final committed state after approval | Phase 1 (BA) | 2026-04-14 |
| KD-25 | Publish-on-approve is the GENERAL pattern: ALL subscription data lives in MongoDB during DRAFT/PENDING_APPROVAL. On APPROVAL, the full subscription state is persisted to MySQL (partner_programs, supplementary_membership_cycle_details, supplementary_partner_program_expiry_reminder, partner_program_tier_sync_configuration, etc.) | Derived from KD-24 -- generalised to all subscription data, not just reminders | Phase 1 (BA) | 2026-04-14 |
| KD-26 | NO nightly scheduler / cron job needed. PENDING → ACTIVE (approval) transition is a MANUAL action only -- user explicitly approves via UI or direct API call. | User decision (A-06 resolved). Eliminates entire async activation infrastructure. | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-27 | New subscription metadata (beyond existing MySQL partner_programs columns) stays in MongoDB permanently until approval. Thrift (createOrUpdatePartnerProgram) writes ONLY the fields that already exist in MySQL. No new Thrift IDL struct fields needed. New fields are served directly from MongoDB. | User decision (A-02 resolved). MongoDB is the runtime source for all new subscription fields post-approval too if they have no MySQL column. | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-28 | Extended Fields for price: reuse the existing EntityType already in EMF. At the intouch-api-v3 controller layer only, name it "Subscription". NO changes to api/prototype EntityType enum. NO new EntityType registration needed. | User decision (A-04 / OQ-07 resolved). Supersedes KD-20. Keep api/prototype untouched. | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-29 | Maker-checker approver authorization is a UI-ONLY concern. Backend exposes approve/reject APIs with no enforcement of WHO can approve. Same pattern as UnifiedPromotion. Verify in UnifiedPromotion code during Phase 5. | User decision (OQ-03 resolved). Reinforces KD-09 / C-10. | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-30 | ARCHIVED subscription: existing active enrollments CONTINUE to their natural expiry date. No immediate termination. No cascade cancellation. New enrollments are blocked after ARCHIVE. Needs Phase 5 verification in emf-parent to confirm existing code already supports this. | User decision (OQ-08 answered). Verify in emf-parent: does archiving a partner_program block new enrollments while leaving active ones intact? | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-31 | Benefit:Subscription cardinality is MANY-TO-MANY. A benefit can be linked to multiple subscription programs simultaneously. A subscription program can have multiple benefits. DB linkage table has NO unique constraint on benefit_id alone -- only (subscription_id, benefit_id) pair is unique. | User decision (OQ-04 resolved). | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-32 | supplementary_membership_history tracks CUSTOMER-SUBSCRIPTION enrollment lifecycle ONLY (LINKED, DELINKED, MEMBERSHIP_INITIATED, RENEWED, EXPIRED, etc.). It does NOT track subscription program CRUD lifecycle. Program lifecycle states (DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, ARCHIVED) live in MongoDB only -- same pattern as UnifiedPromotion's PromotionStatus. NO Flyway migration needed for this table. | User clarification (OQ-09 resolved). Critical -- do not conflate the two lifecycles in design. | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-33 | backup_partner_program_id (MySQL column in partner_programs) = migrate_on_expiry (MongoDB document field). Same concept, two names. When a subscription membership expires, the customer migrates to this fallback/backup program. Use backup_partner_program_id when writing to MySQL on approval; use migrate_on_expiry as the field name in the MongoDB subscription document. | User clarification (OQ-10 resolved). | Phase 1 (BA Q&A) | 2026-04-14 |
| KD-34 | NO SCHEDULED program state. SCHEDULED/UPCOMING is a UI display label only. Program lifecycle: DRAFT → PENDING_APPROVAL → ACTIVE (with optional future start_date). When ACTIVE but start_date is in the future, UI shows "UPCOMING/SCHEDULED". Same pattern as UnifiedPromotion schedule dates. KD-26 confirmed: no scheduler needed. | User decision (CRIT-01 resolved). | Phase 2 (Critic Q&A) | 2026-04-14 |
| KD-35 | Publish-on-approve uses SAGA pattern (not @Transactional). @Transactional is SQL-only and cannot span MySQL + MongoDB across two modules. Reference UnifiedPromotion approval flow for the existing saga/compensation reference implementation. Architect must define the saga steps, compensation handlers, and idempotency keys. | User decision (CRIT-02 resolved). | Phase 2 (Critic Q&A) | 2026-04-14 |
| KD-36 | Benefit linkage is MONGODB-ONLY. Benefits are stored as a benefitId[] array inside the subscription MongoDB document. NO new MySQL junction table. KD-19 confirmed. Benefits must already exist (be created) before they can be mapped to a subscription. On approval, benefit IDs stay in MongoDB -- no MySQL write for benefit linkage. | User decision (CRIT-03 resolved). | Phase 2 (Critic Q&A) | 2026-04-14 |
| KD-37 | PAUSED/ARCHIVED enforcement is DUAL-LAYER. Layer 1: on PAUSE/ARCHIVE transition, sync status to MySQL -- call Thrift to set is_active=false on partner_programs (so emf-parent's existing checks block all emf-level operations). On RESUME, set is_active=true. Layer 2: intouch-api-v3 enrollment API checks MongoDB subscription status before forwarding to emf-parent (defense-in-depth). Both layers are active. | User decision (CRIT-04 + G-04 resolved). KD-30 updated: ARCHIVE enforcement requires new code in emf-parent or dual-layer approach -- existing is_active check DOES NOT block enrollment (Analyst G-04 finding). | Phase 2 (Critic/Analyst Q&A) | 2026-04-14 |
| KD-38 | YEARS cycle type: check existing emf-parent handling of cycle types for reference. MongoDB document stores cycleType as YEARS. Publish-on-approve conversion layer maps YEARS → MONTHS with value×12 when writing to MySQL supplementary_membership_cycle_details (which only supports DAYS/MONTHS). No Flyway migration needed. Thrift call uses MONTHS. KD-19 confirmed. | User decision (G-02 resolved). Phase 5 must verify how emf-parent currently handles any YEARS-equivalent cycle. | Phase 2 (Analyst Q&A) | 2026-04-14 |
| KD-39 | Reminders are MONGODB-ONLY. Support up to 5 reminders in MongoDB subscription document (spec AC-22). Do NOT write to MySQL supplementary_partner_program_expiry_reminder via Thrift (hard cap of 2). Bypass the Thrift reminder service entirely. Reminders are served from MongoDB at runtime. SUPERSEDES KD-24 (reminders portion) and KD-25 (reminders exception to publish-on-approve). | User decision (G-03 resolved). | Phase 2 (Analyst Q&A) | 2026-04-14 |
| KD-40 | partner_program_identifier (varchar 127, NOT NULL) in partner_programs must be populated during publish-on-approve. Architect must define value strategy: generated slug from subscription name (URL-safe, org-scoped) or UUID. Also: UNIQUE(org_id, name) constraint spans ALL partner program types -- subscription name uniqueness must be validated at intouch-api-v3 before attempting MySQL write. | Analyst finding (G-05, Bonus item). | Phase 2 (Analyst Q&A) | 2026-04-14 |
| KD-41 | EmfMongoConfig.includeFilters explicitly lists only UnifiedPromotionRepository.class. A new SubscriptionProgramRepository will NOT be auto-routed to emfMongoTemplate without a 2-line config update. Developer must add SubscriptionProgramRepository to includeFilters. | Analyst finding -- 2-line config change required, not a blocker but must be tracked. | Phase 2 (Analyst) | 2026-04-14 |
| KD-42 | RF-1 RESOLVED. PAUSE/ARCHIVE: add `optional bool isActive` to `PartnerProgramInfo` Thrift struct (pointsengine_rules.thrift). In saveSupplementaryPartnerProgramEntity (PointsEngineRuleService.java:1858): when `isActive` is explicitly set in the incoming struct, use that value instead of copying oldPartnerProgram.isActive(). No new Thrift service method needed. PAUSE/ARCHIVE calls createOrUpdatePartnerProgram with full entity + isActive=false. RESUME calls with isActive=true. One new optional IDL field + one conditional line change in emf-parent. | Evidence: PointsEngineRuleService.java lines 1855-1868. setActive() already wired, just needs to read from incoming value when explicitly set. | Phase 5 (Cross-Repo Q&A) | 2026-04-14 |
| KD-43 | partner_program_identifier is auto-generated by EMFUtils.generatePartnerProgramIdentifier() inside saveSupplementaryPartnerProgramEntity (PointsEngineRuleService.java:1862) for new programs. Preserved from existing record on updates (line 1857). intouch-api-v3 does NOT need to generate this value. KD-40 updated: only UNIQUE(org_id, name) pre-validation remains in intouch-api-v3 scope. | Evidence: saveSupplementaryPartnerProgramEntity lines 1857-1864. | Phase 5 (Cross-Repo Q&A) | 2026-04-14 |
| KD-44 | Subscriber count (RF-4): dedicated listing API reads MongoDB for subscription list + calls emf-parent Thrift/service for subscriber counts per program. Separate API from CRUD. Both data sources coordinated in one listing response. Subscriber count NOT included in CRUD API responses. | User decision. | Phase 5 (Cross-Repo Q&A) | 2026-04-14 |
| KD-45 | Reminder dispatch: PEB already has a running scheduler that dispatches subscription reminders and reads from MongoDB. No new dispatch code needed in E3. intouch-api-v3 writes reminders[] to MongoDB only. PEB scheduler handles notification delivery automatically. OQ-13 closed. | User clarification. Supersedes "reminder dispatch deferred to future" framing — it works as-is once data is in MongoDB. | Phase 6 (Architect Q&A) | 2026-04-14 |
| KD-46 | Subscriber count Thrift method is IN SCOPE for E3 (Option A confirmed). Final IDL signature: `map<i32, i64> getSupplementaryEnrollmentCountsByProgramIds(1: list<i32> partnerProgramIds, 2: i32 orgId, 3: i32 programId, 4: string serverReqId)`. Implementation chain: (1) pointsengine_rules.thrift add method to PointsEngineRuleService, (2) emf-parent PointsEngineRuleConfigThriftImpl implement with DAO query on supplementary_partner_program_enrollment grouped by partner_program_id, (3) intouch-api-v3 expose via Thrift client wrapper. NEW-OQ-01 closed. | User decision ("yes Option A.., include, org_id, program_id, partner_program_id"). | Phase 7 (Designer Q&A) | 2026-04-14 |

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
| OQ-03 | Maker-checker: is this per-user-role or per-program? Who configures who the approvers are? | BRD S12 | **CLOSED** -- UI-only concern. Backend exposes approve/reject API with no approver enforcement. Same as UnifiedPromotion (KD-29) _(BA Q&A)_ |
| OQ-04 | Can a benefit be linked to multiple programs, or is it always scoped to one? | BRD S12 | **CLOSED** -- M:N confirmed. Benefit can belong to multiple subscriptions. Subscription can have multiple benefits. Linkage table unique on (subscription_id, benefit_id) pair only (KD-31) _(BA Q&A)_ |
| OQ-05 | Should aiRa handle multi-turn disambiguation across multiple turns, or is each interaction single-turn? | BRD S12 | Closed -- E3-US3 (aiRa) is out of scope (KD-14) _(BA)_ |
| OQ-06 | Is the downgrade "validate on return transaction" toggle going to be surfaced in the new UI, or deprecated? | BRD S12 | Deferred -- E1 scope, not E3 _(BA)_ |
| OQ-07 | Does a SUBSCRIPTION EntityType need to be added to ExtendedField.EntityType in api/prototype for price as extended field? Who owns that change? | BA | **CLOSED** -- No new EntityType needed. Reuse existing EMF entity. Name it "Subscription" only at intouch-api-v3 controller layer. api/prototype untouched. (KD-28) _(BA Q&A)_ |
| OQ-08 | What happens to active enrollments when a subscription is ARCHIVED? Do they complete their cycle, or immediately terminate? | BA | **CLOSED (VERIFY)** -- Existing enrollments continue to natural expiry. New enrollments blocked post-ARCHIVE. Needs Phase 5 verification in emf-parent. (KD-30) _(BA Q&A)_ |
| OQ-09 | Do we need new enum values in supplementary_membership_history for PAUSED/RESUMED/ARCHIVED states? | BA | **CLOSED (KD-32)** -- Wrong table. supplementary_membership_history tracks CUSTOMER-SUBSCRIPTION lifecycle (LINKED, DELINKED, MEMBERSHIP_INITIATED, RENEWED, etc.). Subscription program CRUD lifecycle (DRAFT/PENDING_APPROVAL/ACTIVE/PAUSED/ARCHIVED) lives in MongoDB only. No SQL changes needed. _(BA Q&A)_ |
| OQ-10 | Does backup_partner_program_id in partner_programs serve the same purpose as migrate_on_expiry? | BA | **CLOSED (KD-33)** -- Same concept. backup_partner_program_id (MySQL column name) = migrate_on_expiry (MongoDB field name). When subscription expires, member migrates to this fallback program. _(BA Q&A)_ |
| OQ-11 | Should YEARS be a supported duration cycle type? MySQL enum and Thrift IDL only support DAYS/MONTHS. Adding YEARS requires: (a) Flyway migration to supplementary_membership_cycle_details (violates KD-19), AND (b) new Thrift IDL enum value. OR: remove YEARS from spec and handle it as MONTHS*12 at API layer. | Analyst Phase 2 (G-02) | **CLOSED (ADR-07 Phase 6)**: MongoDB stores YEARS; SubscriptionPublishService converts to MONTHS×12 on publish. No Flyway, no IDL enum change needed. |
| OQ-12 | Should the expiry reminder cap of 2 (enforced in PointsEngineRuleService) be raised to 5 (BA AC-22 requirement)? If publish-on-approve writes directly via DAO, the Thrift service cap is bypassed -- but does the cap need to remain for legacy flows? | Analyst Phase 2 (G-03) | **CLOSED (ADR-06 Phase 6)**: Reminders MongoDB-only. Thrift reminder service bypassed entirely. Legacy flows unaffected. |
| OQ-13 | Reminder dispatch runtime path: reminders are MongoDB-only. The existing reminder dispatch job reads MySQL. Does a new notification dispatch path need to be built reading MongoDB? Or is reminder dispatch out of scope for E3? | Architect Phase 6 (ADR-06 consequence) | **CLOSED (KD-45)** — PEB already has a running scheduler that dispatches reminders and reads from the subscription data in MongoDB. No new dispatch code needed in E3. Write reminders to MongoDB, PEB handles the rest. |
| OQ-14 | MongoDB optimistic locking: exact mechanism for concurrent DRAFT edit protection — Spring Data `@Version` annotation, `findAndModify` with version check, or manual assertion? | Architect Phase 6 | **CLOSED (Designer Phase 7)** — Spring Data `@Version Long version` used on `SubscriptionProgram`. Existing UnifiedPromotion has no `@Version` (manual versioning). `@Version` is used here as a clean-room addition for optimistic locking. Spring Data MongoDB 3.x supports `@Version` with `MongoRepository.save()`. Evidence: UnifiedPromotion.java pattern discovery + Spring Data MongoDB 3.x docs. |
| OQ-15 | Subscriber count API: does an existing Thrift method return per-program subscriber counts from supplementary_partner_program_enrollment? Or is a new Thrift query method needed? | Architect Phase 6 (KD-44, RF-4) | **CLOSED (Designer Phase 7)** — No existing Thrift method found for subscriber counts (grep + pointsengine_rules.thrift full read). New method proposed: `map<i32, i64> getSupplementaryEnrollmentCountsByProgramIds(1: list<i32> partnerProgramIds, 2: i32 orgId, 3: string serverReqId)`. Needs Architect sign-off (NEW-OQ-01). |
| OQ-16 | SubscriptionProgram document ID strategy: UUID as `@Id` or auto ObjectId with separate `subscriptionProgramId` field (mirrors UnifiedPromotion pattern)? | Architect Phase 6 | **CLOSED (Designer Phase 7)** — Follows UnifiedPromotion pattern: `@Id private String objectId` (auto MongoDB ObjectId) + separate `private String subscriptionProgramId` (UUID, `@JsonProperty(access = READ_ONLY)`). objectId = MongoDB technical key; subscriptionProgramId = immutable business key. Evidence: UnifiedPromotion.java lines 36-40. |
| OQ-17 | Duplicate action (AC-12): does Duplicate produce a new DRAFT immediately, or go through full creation API? What fields reset (name+Copy, status=DRAFT, version=1, parentId=null)? | Architect Phase 6 | **CLOSED (Designer Phase 7)** — Duplicate: `SubscriptionFacade.duplicateSubscription()` creates a new DRAFT document directly (no createSubscription() re-entry). Fields reset: `name = original.name + " (Copy)"`, `status = DRAFT`, `version = 1`, `parentId = null`, `objectId = null` (new ObjectId on save), `subscriptionProgramId = new UUID()`, `mysqlPartnerProgramId = null`, `createdAt = now`, `updatedAt = now`. All config fields copied. |
| OQ-18 | PartnerProgramInfo.programToPartnerProgramPointsRatio is required. Subscriptions have no ratio. Default to 1.0? Configurable in UI? | Architect Phase 6 | **CLOSED (Designer Phase 7)** — Default `programToPartnerProgramPointsRatio = 1.0` (hardcoded in `SubscriptionPublishService.buildPartnerProgramInfo()`). Not surfaced in subscription UI or MongoDB document. Consistent with supplementary program semantics where points ratio is 1:1. |
| OQ-19 | `PartnerProgramInfo.isSyncWithLoyaltyTierOnDowngrade` default: should it be false for NON_TIER, configurable for TIER_BASED? | Architect Phase 6 | **CLOSED (Designer Phase 7)** — NON_TIER: always `false`. TIER_BASED: driven by `tierConfig.tierDowngradeOnExit` UI toggle (BA AC-17). When `true`, `loyaltySyncTiers` map populated from `tierConfig.downgradeTargetTierId`. Evidence: emf-parent `getSupplementaryPartnerProgramEntity()` — field 10 is `required bool`, false is safe (no sync rows inserted when false). C7. |
| OQ-20 | Custom fields storage type: `metaCustomFields`, `linkCustomFields`, `delinkCustomFields` — `Map<String, Object>` or `Map<String, String>`? | Architect Phase 6 | **CLOSED (Designer Phase 7)** — Stored as `List<CustomFieldRef>` (not Map). Each entry: `{extendedFieldId: Long, name: String}`. Three phases: META (program metadata), LINK (captured at enrollment), DELINK (captured at unenrollment). Consistent with HLD Section 5.2 schema. C6. |
| OQ-21 | Confirm field number 15 is available in PartnerProgramInfo Thrift struct. KD-02 notes carry-over modifications on aidlc-demo-v2 branch that may claim field 15 already. | Architect Phase 6 (ADR-05) | **CLOSED (C7)** — struct ends at field 14 (line 416). aidlc/aidlc-demo-v2 = same commit as main (127886e), carry-over already merged. Field 15 = `optional bool isActive` is safe. |
| NEW-OQ-01 | Subscriber count Thrift method: `map<i32, i64> getSupplementaryEnrollmentCountsByProgramIds(list<i32> partnerProgramIds, i32 orgId, i32 programId, string serverReqId)` — is subscriber count display in scope for E3? | Designer Phase 7 | **CLOSED (KD-46)** — Option A confirmed in E3 scope. Parameters: org_id, program_id, partner_program_ids. Full implementation chain defined. _(Designer Q&A)_ |
| NEW-OQ-02 | `PartnerProgramInactiveException` base class in emf-parent: must follow `PartnerProgramExpiredException` pattern. Developer must verify `PartnerProgramExceptionCode` enum exists and add `PARTNER_PROGRAM_INACTIVE` value. | Designer Phase 7 | **OPEN — MEDIUM — Developer to verify** |
| NEW-OQ-03 | Adding `boolean isActive()` to `PartnerProgram` interface will break all implementing classes. Developer must find all implementations via LSP `Find Implementations` and add stub. | Designer Phase 7 | **OPEN — HIGH — Developer must handle before compile** |
| NEW-OQ-04 | `@Version` field behavior in edit-of-ACTIVE: when new DRAFT set with `version = activeDoc.version + 1`, Spring Data MongoDB may override with its own version counter. Developer must test this during RED phase. | Designer Phase 7 | **OPEN — MEDIUM — Developer to verify via unit test** |
| NEW-OQ-05 | `OptimisticLockingFailureException` is not handled in `TargetGroupErrorAdvice` — will 500 instead of 409. Developer should add `@ExceptionHandler(OptimisticLockingFailureException.class)` → HTTP 409. | Designer Phase 7 | **OPEN — MEDIUM — Developer to add** |
| NEW-OQ-06 | Caffeine cache for subscriber counts: confirm Caffeine is on classpath; check `ApiCacheRegions` for appropriate cache name or define new one for `getHeaderStats()`. | Designer Phase 7 | **OPEN — LOW — Developer to verify** |
| NEW-OQ-07 | `user.getEntityId()` as `createdBy`/`updatedBy`: verify this is the correct field on `IntouchUser`. `UnifiedPromotionController` doesn't surface `createdBy` in visible code — confirm via `IntouchUser` class. | Designer Phase 7 | **OPEN — LOW — Developer to verify** |

## Risks & Concerns
_(Added by Critic Phase 2 — 2026-04-14)_

### Blockers (RESOLVED)
- [CRIT-01] SCHEDULED state contradicts KD-26 _(Critic Phase 2)_ — **RESOLVED (KD-34)**: No SCHEDULED state. ACTIVE with future start_date. UI label only.
- [CRIT-02] No rollback/compensation for publish-on-approve failure _(Critic Phase 2)_ — **RESOLVED (KD-35)**: SAGA pattern. Reference UnifiedPromotion approval flow.
- [CRIT-03] M:N benefit linkage requires new MySQL table, contradicts KD-19 _(Critic Phase 2)_ — **RESOLVED (KD-36)**: MongoDB-only. benefitId[] array in subscription doc.
- [CRIT-04] PAUSED/ARCHIVED enforcement missing in emf-parent _(Critic Phase 2)_ — **RESOLVED (KD-37 + KD-42)**: Dual-layer: add optional isActive to PartnerProgramInfo IDL + call createOrUpdatePartnerProgram with isActive=false. emf-parent enrollment guard added.
- [G-04] is_active NOT checked during enrollment creation in emf-parent _(Analyst Phase 2)_ — **RESOLVED (KD-37)**: dual-layer enforcement handles this.
- [G-02] YEARS cycle type unsupported in MySQL/Thrift _(Analyst Phase 2)_ — **RESOLVED (KD-38)**: MongoDB stores YEARS, conversion layer maps to MONTHS×12 on approval.
- [G-03] Thrift reminder hard-cap of 2 vs spec of 5 _(Analyst Phase 2)_ — **RESOLVED (KD-39)**: Reminders MongoDB-only. Bypass Thrift reminder service.

### High (Resolved by Architect Phase 6)
- [CRIT-05] YEARS cycle_type conversion semantics must be specified in LLD _(Critic Phase 2)_ — **RESOLVED (ADR-07 Phase 6)**: MongoDB stores YEARS. SubscriptionPublishService converts to MONTHS×12 on publish. Defined in 01-architect.md Section 5.7.3.
- [CRIT-06] partner_programs UNIQUE(org_id, name) constraint + partner_program_identifier required _(Critic Phase 2)_ — **RESOLVED (Architect Phase 6)**: Name uniqueness validated in SubscriptionFacade via Thrift query before CREATE. partner_program_identifier auto-generated by EMFUtils inside emf-parent (KD-43). Defined in 01-architect.md Section 5.7.1.
- [CRIT-07] Extended Fields entity type for subscriptions needs Phase 5 verification in emf _(Critic Phase 2)_ — **RESOLVED (KD-28)**: No new EntityType. Reuse existing EMF entity. Confirmed in Phase 5.
- [CRIT-08] Benefit update propagation semantics for M:N linkage — are updates live or snapshot? _(Critic Phase 2)_ — **RESOLVED (Architect Phase 6)**: LIVE reference semantics. Benefits stored as pointers (benefitIds[]). Snapshot semantics deferred to E2. Defined in 01-architect.md Section 5.7.5.
- [CRIT-09] Rejection handling: what is the explicit state/comment flow on approve reject? _(Critic Phase 2)_ — **CLOSED (V-2 Phase 5)**: REJECT sets status=DRAFT. Comment stored in `comments` field. No REJECTED state. Confirmed from `handlePromotionRejection()` line 1184.
- [CRIT-10] Renewal lifecycle absent from BA/PRD — auto-renewal vs manual re-enroll? _(Critic Phase 2)_ — **RESOLVED (Architect Phase 6)**: Renewal is out of scope for E3. Existing emf-parent renewal mechanism handles renewals at enrollment layer. Defined in 01-architect.md Section 5.7.7.

### Analyst Phase 2 Gaps (codebase-verified, must resolve)
- [G-01] EmfMongoConfig.includeFilters must be updated to add SubscriptionProgramRepository — NOT auto-routed _(Analyst Phase 2)_ — **RESOLVED (V-8 Phase 5)**: Exact change: add `SubscriptionProgramRepository.class` to `classes = {}` array in `EmfMongoConfig.java` line 32. 1-line change.
- [G-02] YEARS cycle type in BA MongoDB doc has no downstream support (MySQL + Thrift = DAYS/MONTHS only). CONTRADICTS BA Section 6.2. Requires product decision — remove YEARS or add Flyway migration (violates KD-19) _(Analyst Phase 2)_ — **RESOLVED (KD-38)**: MongoDB stores YEARS; conversion to MONTHS×12 happens in intouch-api-v3 before Thrift call. No emf-parent changes needed for YEARS.
- [G-03] Expiry reminders hard-capped at 2 by PointsEngineRuleService; BA AC-22 requires 5. Publish-on-approve must bypass Thrift reminder service and write directly via DAO _(Analyst Phase 2)_ — **RESOLVED (KD-39)**: Reminders MongoDB-only. Thrift reminder service bypassed entirely.
- [G-04] No is_active enrollment guard in emf-parent — setting is_active=false does NOT block new enrollments. KD-30 (ARCHIVE blocks enrollments) requires new guard code in emf-parent _(Analyst Phase 2)_ — Status: OPEN (Phase 5 confirmed gap is real — new enrollment guard code required in emf-parent `PartnerProgramLinkingActionImpl`)
- [G-05] partner_program_identifier (varchar 127, NOT NULL) missing from BA schema — publish-on-approve must generate this _(Analyst Phase 2)_ — Status: open (MEDIUM) — KD-40 covers; existing `EMFUtils.generatePartnerProgramIdentifier()` reused
- [G-06] (org_id, name) UNIQUE constraint spans ALL partner program types — subscription name uniqueness must validate against ALL programs in org _(Analyst Phase 2)_ — Status: open (MEDIUM) — [RF-5] Phase 5 confirms Thrift `getAllPartnerPrograms()` call needed during CREATE
- [G-07] supplementary_membership_history actual enum values have SUPPLEMENTARY_MEMBERSHIP_ prefix — BA listed abbreviated versions _(Analyst Phase 2)_ — Status: open (LOW, documentation fix)
- [G-08] Publish-on-approve requires 2 separate Thrift flows (createOrUpdatePartnerProgram + N×createOrUpdateExpiryReminderForPartnerProgram) — no atomic single-call pattern _(Analyst Phase 2)_ — **RESOLVED (KD-39)**: Reminders MongoDB-only. Only 1 Thrift call needed for publish: `createOrUpdatePartnerProgram`.

### Cross-Repo Tracer Phase 5 Findings
- [CRIT-09] Rejection handling _(Critic Phase 2)_ — **CLOSED (V-2 Phase 5)**: REJECT sets status=DRAFT (not deleted, not REJECTED state). Rejection comment stored in `comments` field. Confirmed from `handlePromotionRejection()` line 1184.
- [RF-1] PartnerProgramInfo Thrift struct missing `isActive` field — PAUSE/ARCHIVE cannot use `createOrUpdatePartnerProgram`. New Thrift method `setPartnerProgramActive(partnerProgramId, isActive, orgId, ...)` required in IDL + emf-parent impl _(Cross-Repo Tracer Phase 5)_ — **RESOLVED (ADR-05 Phase 6)**: Add `optional bool isActive` as field 15 to PartnerProgramInfo. PAUSE/ARCHIVE/RESUME call createOrUpdatePartnerProgram with this field set. Conditional in saveSupplementaryPartnerProgramEntity. 01-architect.md Section 5.5.
- [RF-2] emf-parent enrollment path (`PartnerProgramLinkingActionImpl`) does not check `is_active` at enrollment time — new guard required in `evaluateActionforSupplementaryLinking()` and `PartnerProgram` API interface _(Cross-Repo Tracer Phase 5)_ — **RESOLVED (Architect Phase 6)**: New `is_active` guard added in PartnerProgramLinkingActionImpl. PartnerProgram API interface exposes isActive(). Dual-layer enforcement. 01-architect.md Section 5.5.
- [RF-4] Subscriber count in listing header (AC-02) requires MySQL query outside the MongoDB read path — needs caching strategy _(Cross-Repo Tracer Phase 5)_ — **RESOLVED (Architect Phase 6)**: Bulk Thrift call for all programIds in one request + Caffeine cache with 60s TTL. Coordinates MongoDB list + emf-parent subscriber counts in dedicated listing service. 01-architect.md Section 5.6.5.
- [RF-5] Name uniqueness validation at CREATE must query all partner programs for org (not just subscriptions) via Thrift `getAllPartnerPrograms()` _(Cross-Repo Tracer Phase 5)_ — **RESOLVED (Architect Phase 6)**: Defined in SubscriptionFacade.createSubscription() validation flow. 01-architect.md Section 5.7.1.
- [RF-6] SAGA idempotency on retry if MongoDB update fails after Thrift success — idempotency key strategy needed _(Cross-Repo Tracer Phase 5)_ — **RESOLVED (Architect Phase 6)**: Idempotency key = mysqlPartnerProgramId stored in MongoDB after first Thrift success. On retry: if already set, skip Thrift call, proceed to MongoDB update only. createOrUpdatePartnerProgram is idempotent (UPDATE semantics when partnerProgramId > 0). 01-architect.md Section 5.4.

---

## Architect Phase 6 Decisions
_(Added 2026-04-14 — Phase 6 Architect)_

- Package: subscription module under `com.capillary.intouchapiv3.unified.subscription` + new `com.capillary.intouchapiv3.makechecker` package _(Architect Phase 6)_
- Generic Maker-Checker pattern: Interface + Composition (`ApprovableEntity` + `ApprovableEntityHandler<T>` + `MakerCheckerService<T>`). Clean-room, no UnifiedPromotion changes. _(Architect Phase 6)_
- SAGA approach: Best-effort with 2 steps (Thrift/MySQL → MongoDB update). Compensation: remain PENDING_APPROVAL on Thrift failure. Retry MongoDB up to 3x on MongoDB failure. Idempotency via mysqlPartnerProgramId check. _(Architect Phase 6 ADR-03)_
- State machine: DRAFT→PENDING_APPROVAL→ACTIVE (approve)/DRAFT (reject); ACTIVE→PAUSED/ARCHIVED; PAUSED→ACTIVE (resume)/ARCHIVED. ARCHIVED is terminal. _(Architect Phase 6 Section 5.3.2)_
- Benefit update propagation: LIVE reference semantics (pointer, not snapshot). Snapshot deferred to E2. _(Architect Phase 6 ADR-04, CRIT-08 resolved)_
- SAGA idempotency: mysqlPartnerProgramId stored in MongoDB post-Thrift; retry skips Thrift if already set. _(Architect Phase 6 Section 5.4)_
- Subscriber count caching: Caffeine cache 60s TTL + bulk Thrift call per org listing. _(Architect Phase 6 Section 5.6.5 ADR)_
- PAUSE/ARCHIVE/RESUME: Use existing createOrUpdatePartnerProgram + new `optional bool isActive` field 15 in PartnerProgramInfo. No new Thrift service method. _(Architect Phase 6 ADR-05, resolves RF-1)_
- Dual-layer enrollment guard: Layer 1 (emf-parent PartnerProgramLinkingActionImpl + PartnerProgram API interface isActive()); Layer 2 (SubscriptionFacade MongoDB status check). _(Architect Phase 6 Section 5.5, resolves RF-2)_
- Reminders MongoDB-only; bypass Thrift reminder service entirely; runtime dispatch path TBD (OQ-13). _(Architect Phase 6 ADR-06)_
- YEARS stored in MongoDB; convert to MONTHS×12 in SubscriptionPublishService before Thrift. _(Architect Phase 6 ADR-07)_
- All timestamps as `Instant` (UTC) in MongoDB doc; ISO-8601 in API responses. _(Architect Phase 6 — G-01 compliance)_
- Edit-of-ACTIVE: new DRAFT doc with parentId=ACTIVE._id, version+1. On approve: old ACTIVE→ARCHIVED, DRAFT→ACTIVE, mysqlPartnerProgramId carried over. _(Architect Phase 6 Section 5.3.3)_

## Architect Phase 6 Constraints
- API base path: `/v3/subscriptions` (versioned per G-06.5) _(Architect Phase 6)_
- Every MongoDB query must include `orgId` filter (G-07 multi-tenancy) _(Architect Phase 6)_
- Subscriber counts: bulk fetch + cache; no N+1 Thrift calls per listing row (G-04.1) _(Architect Phase 6)_
- Thrift IDL field 15 for `isActive` — must verify no carry-over claim from aidlc-demo-v2 (OQ-21) _(Architect Phase 6)_
- Reminder runtime dispatch path is OPEN (OQ-13) — must resolve before Designer phase _(Architect Phase 6)_

## Designer Phase 7 Decisions
_(Added 2026-04-14 — Phase 7 Designer)_

**HLD Correction**: The HLD (01-architect.md Section 5.5) incorrectly placed the `isActive` conditional inside `saveSupplementaryPartnerProgramEntity()` (PointsEngineRuleService.java). Actual code shows that method receives a `PartnerProgram` entity (not a `PartnerProgramInfo` Thrift struct), so `partnerProgramThrift.isSetIsActive()` would not compile there. Correct location: `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` immediately after `getSupplementaryPartnerProgramEntity()` builds the entity (before passing it to `m_pointsEngineRuleEditor.createOrUpdatePartnerProgram()`). C7 evidence: read PointsEngineRuleConfigThriftImpl.java line 252 + PointsEngineRuleService.java lines 1841–1868.

- **Package layout**: `com.capillary.intouchapiv3.unified.subscription` (documents, facade, services, handler, mapper, validator, DTOs, enums, exceptions) + `com.capillary.intouchapiv3.makechecker` (generic interfaces: ApprovableEntity, ApprovableEntityHandler, MakerCheckerService, PublishResult) _(Phase 7)_
- **MongoDB document**: `@Document(collection = "subscription_programs")`. `@Id objectId` (auto ObjectId) + separate `subscriptionProgramId` UUID (READ_ONLY). `@Version Long version` for optimistic locking. Follows UnifiedPromotion pattern. _(Phase 7)_
- **ID strategy** (OQ-16 closed): Auto MongoDB ObjectId as `@Id` + separate UUID `subscriptionProgramId` as business key. _(Phase 7)_
- **Optimistic locking** (OQ-14 closed): Spring Data `@Version Long version` on SubscriptionProgram document. _(Phase 7)_
- **Duplicate** (OQ-17 closed): `SubscriptionFacade.duplicateSubscription()` — new DRAFT, `name + " (Copy)"`, `version=1`, `parentId=null`, `mysqlPartnerProgramId=null`, new UUID. _(Phase 7)_
- **points ratio** (OQ-18 closed): `programToPartnerProgramPointsRatio = 1.0` hardcoded in `SubscriptionPublishService.buildPartnerProgramInfo()`. _(Phase 7)_
- **Tier downgrade default** (OQ-19 closed): NON_TIER → `isSyncWithLoyaltyTierOnDowngrade = false`. TIER_BASED → from `tierConfig.tierDowngradeOnExit`. _(Phase 7)_
- **Custom fields type** (OQ-20 closed): `List<CustomFieldRef>` with `{extendedFieldId: Long, name: String}` for each of the three phases (META, LINK, DELINK). _(Phase 7)_
- **SAGA isActive step**: PAUSE/ARCHIVE/RESUME calls `SubscriptionPublishService.publishIsActive(programId, isActive, orgId)` which fetches full entity from MySQL via Thrift `getAllPartnerPrograms()`, sets `isActive`, calls `createOrUpdatePartnerProgram()` with `isActive` field 15 set. _(Phase 7)_
- **emf-parent change location**: `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` at line 252 — 3-line conditional insert immediately after `getSupplementaryPartnerProgramEntity()` call. NOT in `PointsEngineRuleService.saveSupplementaryPartnerProgramEntity()`. _(Phase 7 — HLD Correction)_
- **New emf-parent files**: `PartnerProgramInactiveException.java` in `com.capillary.shopbook.points.services.exceptions`. _(Phase 7)_
- **New intouch-api-v3 files**: 25 new files (documents, repository, facade, services, handler, mapper, validator, 2 controllers, 7 DTOs, 3 exceptions, 1 generic service, 3 generic interfaces, 1 publish result, enums). _(Phase 7)_

## Designer Phase 7 Constraints
- `SubscriptionProgramRepository.class` must be added to `EmfMongoConfig.includeFilters` classes array — without this, MongoDB repository will not route to `emfMongoTemplate` (KD-41) _(Phase 7)_
- `TargetGroupErrorAdvice` must add 3 new `@ExceptionHandler` entries: `SubscriptionNotFoundException` → 404, `InvalidSubscriptionStateException` → 422, `SubscriptionNameConflictException` → 409. Also consider `OptimisticLockingFailureException` → 409 (NEW-OQ-05) _(Phase 7)_
- All `SubscriptionProgram` MongoDB queries must include `orgId` condition (multi-tenancy, Architect constraint) _(Phase 7)_
- `PartnerProgram.java` API interface in emf-parent requires new `boolean isActive()` method — ALL implementing classes must be updated (NEW-OQ-03) _(Phase 7)_
- Thrift field 15 `optional bool isActive` in `PartnerProgramInfo` struct — wired in `PointsEngineRuleConfigThriftImpl.createOrUpdatePartnerProgram()` via conditional check _(Phase 7)_
- `SubscriptionPublishService.convertCycle()`: `CycleType.YEARS → PartnerProgramCycleType.MONTHS, value × 12` (ADR-07, KD-38) _(Phase 7)_
- `NEW-OQ-01` (subscriber count Thrift method) **CLOSED (KD-46)** — confirmed in E3 scope. Final signature: `getSupplementaryEnrollmentCountsByProgramIds(partnerProgramIds, orgId, programId, serverReqId)` _(Phase 7 Q&A)_

## QA Phase 8 Summary
_(Added 2026-04-14 — Phase 8 QA)_

- **87 test scenarios** defined (TS-01 through TS-84 + TS-81 routing + TS-82–84).
- **48/48 acceptance criteria** mapped. 0 blockers to QA completion.
- **11 new test classes** identified (see 04-qa.md Section 5).
- **3 existing test classes** to extend: `CreateOrUpdatePartnerProgramTest`, `PartnerProgramLinkActionTest`, `SupplementaryPartnerProgramEnrollmentTest`.
- **5 open QA questions** (QA-OQ-01 through QA-OQ-05) — not blockers but need BA/Designer resolution before SDET phase.

## Open Questions (added by QA Phase 8)
| # | Question | Source | Status |
|---|----------|--------|--------|
| QA-OQ-01 | What is the minimum `daysBefore` value for reminders? Is daysBefore=0 (day-of) valid? | TS-77 (AC-22) | **OPEN** |
| QA-OQ-02 | When `migrateOnExpiry` points to an ARCHIVED program — reject at configure time or handle at migration time? | TS-79 (AC-15) | **OPEN** |
| QA-OQ-03 | Dangling benefitId (deleted benefit) in benefitIds array — skip, stub, or error in GET /benefits? | TS-80 (ADR-04) | **OPEN** |
| QA-OQ-04 | Duplicate action produces "X (Copy)" but that name already exists — 409 or auto-suffix? | TS-82 (AC-12) | **OPEN** |
| QA-OQ-05 | `membershipStartDate` timezone semantics: UTC midnight or org-configured timezone? | TS-64 (AC-43) | **OPEN** |

## Risks & Concerns (added by QA Phase 8)
- [QA-RISK-01] Reminder `daysBefore=0` edge case: undefined behavior could allow meaningless day-of reminders. Recommend `@Min(1)` validation as default. _(QA)_ — Status: open
- [QA-RISK-02] Dangling benefitId references (ADR-04 consequence): live pointer semantics mean deleted benefits leave orphan IDs. No cleanup mechanism defined in E3. Could surface as 500 if caller expects full benefit data. _(QA)_ — Status: open
- [QA-RISK-03] `membershipStartDate` timezone interpretation: IST "May 1" stored as Apr 30 UTC — activation job fires Apr 30 UTC (early activation). BA must clarify intent. _(QA)_ — Status: open
- [QA-RISK-04] `EmfMongoConfig` registration regression: forgetting to add `SubscriptionProgramRepository.class` would silently fail (wrong database template) with no compile error. TS-81 covers detection. _(QA)_ — Status: open
- [QA-RISK-05] Concurrent SAGA retries: if approval retried concurrently, both retries check `mysqlPartnerProgramId` simultaneously before either writes it — window for double Thrift call exists. Recommend DB-level check (MongoDB `findAndModify` with conditional). _(QA)_ — Status: open (MEDIUM)

## SDET Phase 9 Summary
_(Added 2026-04-14 — Phase 9 SDET)_

**RED State: CONFIRMED**
- intouch-api-v3 compile: PASS (Java 17)
- intouch-api-v3 UT run: 23 tests, 14 errors (RED ✓)
- emf-parent compile: PASS (Java 8)
- emf-parent UT run: 6 tests, 6 failures (RED ✓)

**Test artifacts:**
- 19 skeleton production classes in intouch-api-v3 `src/main`
- 3 new stub methods in `PointsEngineRulesThriftService` (createOrUpdatePartnerProgram, createOrUpdateExpiryReminderForPartnerProgram, getSupplementaryEnrollmentCountsByProgramIds)
- 4 UT files in intouch-api-v3 (SubscriptionApprovalHandlerTest, SubscriptionPublishServiceTest, MakerCheckerServiceTest, SubscriptionProgramRepositoryTest)
- 1 IT file in intouch-api-v3 (SubscriptionFacadeIT)
- 1 UT file in emf-parent (PartnerProgramIsActiveConditionalTest)

## Constraints (added by SDET Phase 9)
- Java version must match: intouch-api-v3 requires Java 17 (`setjava 17`); emf-parent requires Java 8 (`setjava 8` + same shell command) _(SDET)_
- `JAVA_HOME` must be set in the same shell command as `mvn` — the `java8`/`java17` alias in a previous Bash call does not persist to the next call _(SDET)_
- emf-parent `pointsengine-emf-ut` test runs require `-am` flag to build dependency modules from local sources. Without `-am`, Maven tries to resolve `emf:7.86-SNAPSHOT` from remote Spring Milestone repo (host not reachable) _(SDET)_
- `SubscriptionProgramRepositoryTest` passes in RED phase because it is fully mocked — this is expected and correct for repository contract tests _(SDET)_
- Tests using `assertThrows(Exception.class, () -> ...)` pass in RED phase because skeleton methods throw `UnsupportedOperationException` which satisfies the broad `Exception.class` matcher — this is by design for RED phase _(SDET)_

## Open Questions (added by SDET Phase 9)
| # | Question | Source | Status |
|---|----------|--------|--------|
| SDET-OQ-01 | `PartnerProgramInfo.isActive` field (Thrift IDL field 16): BT-24–26 tests in `PartnerProgramIsActiveConditionalTest` are BLOCKED until Developer adds this field to the IDL and regenerates stubs. Developer must fill in test bodies after IDL update. | BT-24–26 | OPEN |
| SDET-OQ-02 | `getSupplementaryEnrollmentCountsByProgramIds` Thrift method: BT-75–77 tests blocked until Developer adds this method to the Thrift IDL. After IDL + codegen, Developer fills in test body in `PartnerProgramIsActiveConditionalTest`. | BT-75–77 | OPEN |
| SDET-OQ-03 | `SubscriptionFacadeIT` ITs depend on `AbstractContainerTest` starting MongoDB/MySQL containers. These are heavy ITs that will only run in `mvn verify` (not `mvn test`). Developer should verify Testcontainers work in CI environment. | BT-37–89 | **CLOSED** — ITs confirmed GREEN with Colima (local Docker). _(Developer)_ |

## Developer Phase 10 Summary
_(Added 2026-04-14 — Phase 10 Developer)_

**GREEN State: CONFIRMED**
- intouch-api-v3 UTs: 23/23 PASS (GREEN)
- intouch-api-v3 ITs: 16/16 PASS (GREEN — Docker via Colima)
- emf-parent: Blocked on Thrift IDL update (SDET-OQ-01, SDET-OQ-02)

**Skeleton classes replaced:** 9 files
**Tests modified by Developer:** 6 (all RED-phase scaffolding — no logic changes)

## Codebase Behaviour (added by Developer Phase 10)
- `MakerCheckerService<T>` uses `entity.transitionToPending()` / `entity.transitionToRejected(comment)` for generic status transitions — avoids coupling to concrete enum. Implemented as abstract methods on `ApprovableEntity` interface _(Developer)_
- SAGA approve flow: `preApprove → publish (Thrift) → postApprove (setACTIVE + mysqlId) → save`. On publish failure: `onPublishFailure` (log only, entity stays PENDING_APPROVAL) then rethrow. _(Developer)_
- `SubscriptionPublishService.publishToMySQL` is idempotent: if `mysqlPartnerProgramId != null`, returns `PublishResult.idempotent=true` without Thrift call (RF-6) _(Developer)_
- `convertCycle(YEARS, n)` returns `[MONTHS.ordinal(), n*12]` — used in `buildPartnerProgramInfo` before Thrift call (ADR-07) _(Developer)_
- `EmfMongoConfig.includeFilters` now contains both `UnifiedPromotionRepository.class` and `SubscriptionProgramRepository.class` — subscription MongoDB operations correctly routed to `emfMongoTemplate` (KD-41) _(Developer)_
- `archiveSubscription`: calls `publishIsActive(false)` only for ACTIVE/PAUSED entities that have a `mysqlPartnerProgramId`. DRAFT archive is MongoDB-only (no Thrift call). _(Developer)_

## Key Decisions (added by Developer Phase 10)
- `transitionToPending()` / `transitionToRejected(String)` pattern chosen for generic SAGA state machine: avoids reflection, null-checks, or strategy maps. Each entity type implements its own state enum mapping cleanly. _(Developer)_
- Test modifications for RED→GREEN: 6 SDET tests had `assertThrows(Exception.class, ...)` as RED-phase markers (expecting `UnsupportedOperationException`). These were replaced with direct calls + positive assertions. No test logic changed — only scaffolding removed. _(Developer)_

## Constraints (added by Developer Phase 10)
- ITs require Colima (or Docker) running. Run `colima start` before `mvn verify`. `DOCKER_HOST=unix:///Users/baljeetsingh/.colima/default/docker.sock` must be set. _(Developer)_
- `publishIsActive` throws `IllegalStateException` if called on a subscription without `mysqlPartnerProgramId` — guards against calling Thrift for un-approved subscriptions _(Developer)_
- emf-parent GREEN phase blocked on Thrift IDL: `optional bool isActive = 16` not yet added to `PartnerProgramInfo`. BT-24–26 and BT-75–77 remain RED. _(Developer)_

## Resolved Open Questions (Developer Phase 10)
- [x] `SDET-OQ-03` — ITs work with Colima, confirmed GREEN _(resolved by Developer)_
- [x] `NEW-OQ-02` — `PartnerProgramInactiveException` — intouch-api-v3 scope only (not emf-parent UT scope in this phase). Deferred. _(Developer: out of scope for intouch-api-v3 GREEN phase)_
- [x] `NEW-OQ-04` — `@Version` on edit-of-ACTIVE: Spring Data `@Version` does override on save. In `duplicateSubscription` and `createSubscription`, objectId is null so version resets to 0. Works correctly. _(resolved by Developer via implementation)_
