# Gap Analysis -- BRD/PRD Claims vs Codebase Reality

> Phase: 2 (Analyst --compliance mode)
> Date: 2026-04-09
> Method: Every codebase claim in BA and PRD verified against actual source files

---

## Verification Summary

| Category | Total Claims | Confirmed | Contradicted | Partial | Unverified |
|----------|-------------|-----------|--------------|---------|------------|
| Entity/Schema | 8 | 7 | 0 | 1 | 0 |
| Thrift API | 5 | 3 | 1 | 1 | 0 |
| Controller/Routing | 6 | 5 | 1 | 0 | 0 |
| MongoDB Infrastructure | 4 | 4 | 0 | 0 | 0 |
| Cross-Repo Impact | 5 | 3 | 1 | 1 | 0 |
| **TOTAL** | **28** | **22** | **3** | **3** | **0** |

---

## Detailed Verification Table

### Entity and Schema Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|--------------|---------|----------|
| V-01 | "PartnerProgram.java has only is_active boolean, no status enum" | `PartnerProgram.java` in emf-parent | CONFIRMED | No PartnerProgramStatus enum exists anywhere in emf-parent. is_active is the only lifecycle field. [C7] |
| V-02 | "No PARTNER_PROGRAM value in ExtendedField.EntityType" | `ExtendedField.java:70-110` in api/prototype | CONFIRMED | EntityType enum has: CUSTOMER, REGULAR_TRANSACTION, RETURN_TRANSACTION, NOT_INTERESTED_TRANSACTION, REGULAR_LINEITEM, RETURN_LINEITEM, NOT_INTERESTED_LINEITEM, LEAD, COMPANY, CARD, USERGROUP2. No PARTNER_PROGRAM. [C7] |
| V-03 | "UnifiedPromotion has objectId + unifiedPromotionId (UUID)" | `UnifiedPromotion.java` in intouch-api-v3 | CONFIRMED | @Id objectId (Mongo auto), unifiedPromotionId (immutable business UUID). Exact pattern for subscription to follow. [C7] |
| V-04 | "Metadata nested object holds status, orgId, dates, createdBy" | `Metadata.java` in intouch-api-v3 | CONFIRMED | Contains name, description, programId, orgId, startDate, endDate, timezoneName, promotionType, status (PromotionStatus), promoIdentifier, promotionId, createdOn/By, lastModifiedOn/By, version, draftDetails. [C7] |
| V-05 | "PromotionStatus enum has DRAFT, ACTIVE, PAUSED, PENDING_APPROVAL, STOPPED" | `PromotionStatus.java` in intouch-api-v3 | CONFIRMED | Also has SNAPSHOT, LIVE, UPCOMING, COMPLETED, PUBLISH_FAILED. Subscription will need its own enum (SCHEDULED, EXPIRED, ARCHIVED are not in PromotionStatus). [C7] |
| V-06 | "PromotionAction enum has SUBMIT_FOR_APPROVAL, APPROVE, REJECT, PAUSE, STOP, RESUME, REVOKE" | `PromotionAction.java` in intouch-api-v3 | CONFIRMED | Each has actionValue and getNormalizedAction(). Subscription needs its own action enum (ARCHIVE is not in PromotionAction). [C7] |
| V-07 | "PartnerProgramLinkingEventData requires orgID, storeUnitID, loyaltyCustomerDetails, customerPartnerProgramRef" | `emf.thrift:1305-1317` | CONFIRMED | Struct fields: orgID (i32, required), linkingStoreUnitID (i32, required), loyaltyCustomerDetails (UserDetails, required), customerPartnerProgramRef (CustomerPartnerProgramRef, required), eventTimeInMillis (i64, required), uniqueId (string, required), serverReqId (string, required), plus optionals (notes, source, accountId, shouldFetchEventLogs). [C7] |
| V-08 | "CustomerPartnerProgramRef has partnerProgramName" | `emf.thrift:1297-1303` | PARTIAL | Fields: partnerProgramName (required string), partnerMembershipId (optional string), partnerTierName (optional string), partnerTierExpiryDate (optional i64), membershipStartDate (optional i64). Note: uses NAME not ID to identify the program. Subscription enrollment must provide the partner program NAME that matches MySQL. [C6] |

### Thrift API Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|--------------|---------|----------|
| V-09 | "Thrift IDL already has partnerProgramLinkingEvent, partnerProgramDeLinkingEvent, partnerProgramUpdateEvent" | `emf.thrift:1798-1810` in thrifts repo | CONFIRMED | All three methods defined on the EMFService interface. Return EventEvaluationResult. Take event data + isCommit + isReplayed params. [C7] |
| V-10 | "v3 enrollment APIs call EMF Thrift directly (same pattern as UnifiedPromotion)" | PointsEngineRulesThriftService.java, PointsEngineThriftService.java, EmfPromotionThriftService.java in intouch-api-v3 | CONTRADICTED | UnifiedPromotion uses `PointsEngineRulesThriftService` (PointsEngineRuleService.Iface) for promotion RULESET publishing. Partner program events are on a DIFFERENT interface (`EMFService.Iface`). `EmfPromotionThriftService` uses the correct interface but only wraps promotion issue/earn events, NOT partner program events. A NEW Thrift client class must be created. [C7] |
| V-11 | "EMF Thrift handlers for partner program events exist in emf-parent" | `EMFThriftServiceImpl.java` in emf/src/main/java | CONFIRMED | `EMFThriftServiceImpl` implements Iface, annotated `@ExposedCall(thriftName = "emf")`. Delegates to `PartnerProgramLinkingHelper.java`, `PartnerProgramUpdateHelper.java`. [C7] |
| V-12 | "No changes needed to Thrift IDL (thrifts repo)" | `emf.thrift` in thrifts repo | CONFIRMED | All required Thrift structs and methods already exist. [C7] |
| V-13 | "PartnerProgramUpdateEventData includes PartnerProgramTierUpdateInfo" | `emf.thrift:1326-1346` | PARTIAL | The update event is specifically for TIER updates (upgrade, renew, downgrade, membership_renewal_initiation). It includes `PartnerProgramTierUpdateInfo` with `partnerTierUpdateType`, `updatedTierName`, `updatedTierExpiryDate`. This is NOT a general-purpose update -- it's tier-specific. For non-tier subscription updates (like changing benefit IDs or reminders), this Thrift event is NOT applicable. [C7] |

### Controller and Routing Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|--------------|---------|----------|
| V-14 | "RequestManagementController at /v3/requests/{entityType}/{entityId}/status" | `RequestManagementController.java` in intouch-api-v3 | CONFIRMED | @RestController @RequestMapping("/v3/requests"), @PutMapping("/{entityType}/{entityId}/status"). Takes EntityType path var, PromotionStatus query param, StatusChangeRequest body. [C7] |
| V-15 | "RequestManagementFacade currently only routes PROMOTION" | `RequestManagementFacade.java` in intouch-api-v3 | CONFIRMED | `if (entityType == EntityType.PROMOTION)` -> route to UnifiedPromotionFacade. Else throws InvalidInputException("TARGET_LOYALTY.UNSUPPORTED_TYPE_FOR_STATUS_CHANGE"). [C7] |
| V-16 | "EntityType enum has PROMOTION, TARGET_GROUP, STREAK, LIMIT, LIABILITY_OWNER_SPLIT, WORKFLOW, JOURNEY, BROADCAST_PROMOTION" | `EntityType.java` (orchestration package) in intouch-api-v3 | CONFIRMED | Exactly these 8 values. Adding SUBSCRIPTION is a simple enum addition. [C7] |
| V-17 | "No partner program REST APIs in intouch-api-v3" | Grep of all controllers in intouch-api-v3 | CONFIRMED | Zero matches for "partnerProgram" or "partner_program" in any controller, facade, or service file under intouch-api-v3/src/main/java. [C7] |
| V-18 | "StatusTransitionValidator uses EnumMap<CurrentStatus, Set<PromotionAction>>" | `StatusTransitionValidator.java` in intouch-api-v3 | CONFIRMED | Exactly as described. DRAFT->SUBMIT_FOR_APPROVAL, PENDING_APPROVAL->APPROVE/REJECT, ACTIVE->PAUSE/STOP, PAUSED->APPROVE/STOP, STOPPED->(empty). [C7] |
| V-19 | "RequestManagementController response type is generic for subscriptions" | `RequestManagementController.java` in intouch-api-v3 | CONTRADICTED | Return type is `ResponseEntity<ResponseWrapper<UnifiedPromotion>>` -- hardcoded to UnifiedPromotion. SubscriptionFacade would return UnifiedSubscription, not UnifiedPromotion. Either generalize the return type or create a separate endpoint. [C7] |

### MongoDB Infrastructure Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|--------------|---------|----------|
| V-20 | "EmfMongoConfig routes UnifiedPromotionRepository to emfMongoTemplate" | `EmfMongoConfig.java` in intouch-api-v3 | CONFIRMED | @EnableMongoRepositories with includeFilters routing UnifiedPromotionRepository.class to emfMongoTemplate. SubscriptionRepository must be added to includeFilters. [C7] |
| V-21 | "Multi-tenant per-org MongoDB via EmfMongoTenantResolver" | `EmfMongoConfig.java` in intouch-api-v3 | CONFIRMED | emfMongoDatabaseFactory creates EmfMongoTenantResolver(orgContext, emfMongoDataSourceManager). [C7] |
| V-22 | "emfMongoTemplate is separate from primary mongoTemplate" | `EmfMongoConfig.java` comments | CONFIRMED | "Other MongoDB repositories are routed by MongoConfig.java to use the primary mongoTemplate." @Profile("!test") annotation present. [C7] |
| V-23 | "UnifiedPromotionRepository extends MongoRepository with @Query methods" | `UnifiedPromotionRepository.java` in intouch-api-v3 | CONFIRMED | extends MongoRepository<UnifiedPromotion, String>, UnifiedPromotionRepositoryCustom. Has @Query methods for findByObjectIdAndOrgId, findAllByUnifiedPromotionIdAndOrgIdWithAllowedStatuses, etc. [C7] |

### Cross-Repo Impact Claims

| # | BA/PRD Claim | File Checked | Verdict | Evidence |
|---|-------------|--------------|---------|----------|
| V-24 | "api/prototype: 1 modification (ExtendedField.EntityType add PARTNER_PROGRAM)" | `ExtendedField.java` in api/prototype | CONFIRMED | Simple enum value addition. Low risk. [C7] |
| V-25 | "emf-parent: 0 modifications" | EMFThriftServiceImpl.java, PartnerProgramLinkingInstructionExecutor.java, PointsEngineThriftServiceImpl.java | PARTIAL | Java source likely unchanged (handlers already exist). But need to verify the interaction: when a new partner program is created via Thrift, does EMF auto-insert into partner_programs table? Or must the program pre-exist? The enrollment instruction executor assumes the program exists. [C5] |
| V-26 | "cc-stack-crm: 0 modifications" | Database schema context | CONFIRMED | MongoDB-first architecture means no DDL changes. partner_programs table not modified. [C7] |
| V-27 | "thrifts: 0 modifications" | emf.thrift in thrifts repo | CONFIRMED | All required Thrift structs and service methods already defined. [C7] |
| V-28 | "intouch-api-v3: ~10-15 new, ~3-4 modified" | Full analysis of required changes | CONTRADICTED | Missing: PartnerProgramThriftService (new), SubscriptionStatusChangeRequest DTO (new), repository implementation files (3 vs 1 counted). Modified count misses: RequestManagementController (return type), StatusChangeRequest (or separate DTO). Revised estimate: ~15-20 new, ~5-6 modified. [C5] |

---

## Gaps Not Mentioned in BA/PRD

### GAP-1: Partner Program MySQL Record Creation Path [RESOLVED]

**Original concern**: The BA/PRD assumes enrollment works via EMF Thrift but never describes how partner_programs MySQL records are created.

**Resolution**: User confirmed and code verified -- `PointsEngineRuleService.createOrUpdatePartnerProgram(PartnerProgramInfo, programId, orgId, lastModifiedBy, lastModifiedOn, serverReqId)` in pointsengine_rules.thrift:1269 is the correct method. It:
- Creates or updates the `partner_programs` MySQL row
- Takes `PartnerProgramInfo` struct with all config fields (name, description, isTierBased, tiers, membershipCycle, type, expiryDate, etc.)
- Is on `PointsEngineRuleService.Iface` -- the same interface `PointsEngineRulesThriftService` in intouch-api-v3 already uses
- Currently called by the v2 UI via api/prototype -- we are migrating this call to the new v3 REST API

**Correct flow**:
1. Subscription ACTIVE transition -> call `createOrUpdatePartnerProgram` -> writes to MySQL partner_programs
2. Member enrollment -> call `partnerProgramLinkingEvent` (separate concern, assumes program exists)

**Also found**: `createOrUpdateExpiryReminderForPartnerProgram` and `getAllExpiryReminderConfiguredPartnerPrograms` -- Thrift natively supports reminder config per partner program.

### GAP-2: PartnerProgramUpdateEvent is Tier-Specific [WARNING]

The `PartnerProgramUpdateEventData` struct requires `PartnerProgramTierUpdateInfo` with `partnerTierUpdateType` (UPGRADE/RENEW/DOWNGRADE/MEMBERSHIP_RENEWAL_INITIATION). This is NOT a general-purpose update event -- it only handles tier changes within a partner program.

For non-tier subscription operations (pause, resume, update benefit links), there is no corresponding Thrift event. The PRD's E4-US3 (Update Enrollment) claims `partnerProgramUpdateEvent` handles tier changes -- this is correct for TIER_BASED subscriptions, but NON_TIER subscriptions have no Thrift update mechanism.

### GAP-3: StatusChangeRequest.promotionStatus Field Name [INFO]

The field is named `promotionStatus` and the @Pattern regex allows only promotion-specific values. Subscriptions need different action values. Either:
- Create SubscriptionStatusChangeRequest (cleanest)
- Generalize to `action` field (breaking change for promotions)
- Accept the awkward field name and loosen the regex (technical debt)

### GAP-4: RequestManagementController.changeStatus Return Type [WARNING]

Returns `ResponseEntity<ResponseWrapper<UnifiedPromotion>>`. If subscriptions route through the same controller method, the return type must be generalized or a separate method/controller is needed.

### GAP-5: @Profile("!test") on EmfMongoConfig [INFO]

EmfMongoConfig is annotated `@Profile("!test")`. Integration tests will need a test-specific MongoDB config for SubscriptionRepository. This follows the existing pattern (presumably there's a test config already) but should be verified during Phase 5.

### GAP-6: Thrift Event Data Requires storeUnitID [WARNING]

`PartnerProgramLinkingEventData` requires `linkingStoreUnitID` (i32, required). The v3 subscription enrollment API may not have a store context (it's an admin API, not a POS API). Need to determine: can storeUnitID be a default/sentinel value for admin-initiated enrollments?

---

## GUARDRAILS Compliance Check

The following guardrails were checked against the proposed architecture:

| Guardrail | Status | Notes |
|-----------|--------|-------|
| G-01 (Multi-timezone) | N/A | Subscription dates stored as UTC in MongoDB. Not yet relevant until implementation. |
| G-03 (Backward compat) | PASS | No changes to existing v2 APIs, Thrift IDL, or MySQL schema. |
| G-05 (Schema changes) | PASS | MongoDB-first architecture avoids MySQL DDL. |
| G-07 (Tenant isolation) | PASS | EmfMongoTenantResolver provides per-org DB. All queries include orgId. |
| G-10 (Concurrency) | WARN | Maker-checker versioning (parentId) could race if two admins edit simultaneously. UnifiedPromotion has the same risk. |
| G-12 (API contract) | PASS | PRD defines structured field-level errors, not 500s. Pagination follows existing pattern. |

---

*Generated by Analyst --compliance (Phase 2) -- Subscription-CRUD Pipeline*
