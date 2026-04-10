# Code Analysis -- intouch-api-v3

> Phase: 5 (Codebase Research)
> Repo: /Users/baljeetsingh/IdeaProjects/intouch-api-v3
> Role: Primary repo -- all new subscription code goes here

---

## Key Architectural Insights

1. **UnifiedPromotion is the blueprint.** It is a @Document MongoDB entity with objectId (auto), unifiedPromotionId (UUID), Metadata nested object (name, description, orgId, status, dates, createdBy/lastModifiedBy), parentId + version for maker-checker, and comments. The subscription document should follow this structure exactly.

2. **Facade-per-entity pattern.** UnifiedPromotionFacade handles create, get, list, update, changeStatus, and all lifecycle transitions. Each entity type gets its own facade. The subscription needs SubscriptionFacade.

3. **Controller-per-entity.** UnifiedPromotionController is at `/v3/promotions`. Subscription needs SubscriptionController at `/v3/subscriptions`.

4. **Status change routing.** RequestManagementController at `/v3/requests/{entityType}/{entityId}/status` routes via RequestManagementFacade. Currently only PROMOTION is handled. The subscription does NOT use this controller -- it will have its own status change endpoint on SubscriptionController (per KD-16 scope, simpler approach, and because the return type is different).

5. **StatusTransitionValidator** uses EnumMap<CurrentStatus, Set<PromotionAction>>. Subscription needs its own SubscriptionStatusTransitionValidator with different states (DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, EXPIRED, ARCHIVED) and different transitions (e.g., ARCHIVE from DRAFT|ACTIVE|EXPIRED, no STOP state).

6. **EmfMongoConfig** routes repositories to emfMongoTemplate. Currently only UnifiedPromotionRepository is in includeFilters. Must add SubscriptionRepository.

7. **@Profile("!test")** on EmfMongoConfig -- integration tests have their own EmfMongoConfigTest in integrationTests.configuration package.

8. **PointsEngineRulesThriftService** is the Thrift client. Uses `PointsEngineRuleService.Iface`, connects to "emf-thrift-service:9199" with 60s timeout. Has createOrUpdatePromotionV3, publishPeConfig, getAllPrograms, etc. Needs a new `createOrUpdatePartnerProgram` wrapper method.

---

## Entities / Documents Found

| Entity | Type | Location | Relevance |
|--------|------|----------|-----------|
| UnifiedPromotion | @Document(collection="unified_promotions") | unified.promotion.UnifiedPromotion | Blueprint for UnifiedSubscription |
| Metadata | Nested POJO in UnifiedPromotion | unified.promotion.model.Metadata | Blueprint for SubscriptionMetadata |
| PromotionStatus | Enum: DRAFT, ACTIVE, PAUSED, PENDING_APPROVAL, STOPPED, SNAPSHOT, LIVE, UPCOMING, COMPLETED, PUBLISH_FAILED | unified.promotion.enums.PromotionStatus | Need SubscriptionStatus (different values) |
| PromotionAction | Enum: SUBMIT_FOR_APPROVAL, APPROVE, REJECT, PAUSE, STOP, RESUME, REVOKE | unified.promotion.enums.PromotionAction | Need SubscriptionAction (different values) |
| EntityType | Enum in orchestration package | orchestration.EntityType | Needs SUBSCRIPTION added (only if using RequestManagementFacade) |
| StatusChangeRequest | DTO with "promotionStatus" field + @Pattern | unified.promotion.dto.StatusChangeRequest | Need SubscriptionStatusChangeRequest with "action" field |
| ParentDetails | Nested maker-checker version info | unified.promotion.model.ParentDetails | Reusable for subscription |
| DraftDetails | Info about draft version of an active entity | unified.promotion.model.DraftDetails | Reusable for subscription |
| ResponseWrapper<T> | Generic API response wrapper | models.ResponseWrapper | Reusable as-is |

---

## Services Found

| Service | Pattern | Location | Relevance |
|---------|---------|----------|-----------|
| UnifiedPromotionFacade | @Component, Repository + Thrift + Validator deps | unified.promotion.UnifiedPromotionFacade | Blueprint for SubscriptionFacade |
| UnifiedPromotionRepository | MongoRepository<UnifiedPromotion, String> | unified.promotion.UnifiedPromotionRepository | Blueprint for SubscriptionRepository |
| StatusTransitionValidator | @Component, EnumMap-based | validators.StatusTransitionValidator | Blueprint for SubscriptionStatusTransitionValidator |
| UnifiedPromotionValidatorService | @Component, name uniqueness, identifier uniqueness | unified.promotion.validation.UnifiedPromotionValidatorService | Need SubscriptionValidatorService |
| RequestManagementFacade | @Component, EntityType router | facades.RequestManagementFacade | May need SUBSCRIPTION routing (optional) |
| PointsEngineRulesThriftService | @Service @Profile("!test"), Thrift client | services.thrift.PointsEngineRulesThriftService | Add createOrUpdatePartnerProgram wrapper |
| UnifiedPromotionEditOrchestrator | Handles edit-of-active flow | unified.promotion.service.UnifiedPromotionEditOrchestrator | Blueprint for subscription edit flow |

---

## Controllers Found

| Controller | Path | Methods | Relevance |
|-----------|------|---------|-----------|
| UnifiedPromotionController | /v3/promotions | POST, GET, PUT, DELETE, GET /list, + enrollment + stats | Blueprint for SubscriptionController |
| RequestManagementController | /v3/requests/{entityType}/{entityId}/status | PUT (status change) | Returns UnifiedPromotion -- cannot reuse for subscriptions (different return type) |

---

## Key Patterns to Follow

### Create Flow
1. Controller receives @Valid @RequestBody + AbstractBaseAuthenticationToken
2. Extracts orgId from token.getIntouchUser()
3. Facade generates UUID for unifiedPromotionId
4. Sets metadata.orgId, createdOn, lastModifiedOn, default status = DRAFT
5. Validates (name uniqueness, field constraints)
6. Saves to MongoDB repository
7. Returns saved document with generated IDs

### Status Change Flow
1. Facade fetches document by unifiedPromotionId + orgId + existingStatus
2. StatusTransitionValidator.validateTransition(currentStatus, action)
3. Switch on normalizedAction:
   - SUBMIT_FOR_APPROVAL -> PENDING_APPROVAL (save)
   - APPROVE -> handleApproveAction (publish to EMF Thrift, then ACTIVE)
   - REJECT -> DRAFT (save)
   - PAUSE -> PAUSED (deactivate in EMF, save)
   - STOP -> STOPPED (deactivate in EMF, save)
4. For subscription: APPROVE publishes via `createOrUpdatePartnerProgram` (not promotion publish)

### Edit-of-Active Flow (Maker-Checker Versioning)
1. PUT on ACTIVE subscription: createVersionedPromotion()
2. Creates new DRAFT document with version N+1, parentId = ACTIVE doc objectId
3. If DRAFT already exists for that unifiedPromotionId, update existing DRAFT
4. ACTIVE remains unchanged until new DRAFT is approved
5. On APPROVE of the DRAFT: old ACTIVE -> SNAPSHOT, new DRAFT -> ACTIVE

### Test Infrastructure (Integration Tests)
- AbstractContainerTest: @SpringBootTest with Testcontainers (MongoDB, MySQL, Redis, RabbitMQ)
- EmfMongoConfigTest in integrationTests.configuration package (test profile)
- RequestManagementControllerTest extends AbstractContainerTest
- Uses RestTemplate with @LocalServerPort for HTTP-level testing
- @MockBean for external services (ZionAuthenticationService, PointsEngineThriftService)
- PodamFactory for test data generation
- JUnit 5 (@Test, @BeforeEach)

---

## Files That Need Modification (C6+)

| File | Change | Confidence | Evidence |
|------|--------|------------|---------|
| EmfMongoConfig.java | Add SubscriptionRepository.class to includeFilters | C7 | Read line 32: only UnifiedPromotionRepository.class listed |
| EntityType.java | Add SUBSCRIPTION value | C6 | Only if using RequestManagementFacade routing; if separate controller, not needed |
| PointsEngineRulesThriftService.java | Add createOrUpdatePartnerProgram() wrapper method | C7 | No partner program methods exist; verified by reading all methods |

## New Files Needed (C6+)

| File | Purpose | Confidence |
|------|---------|------------|
| UnifiedSubscription.java | @Document entity | C7 |
| SubscriptionMetadata.java | Nested metadata for subscription | C7 |
| SubscriptionStatus.java | Enum: DRAFT, PENDING_APPROVAL, ACTIVE, PAUSED, EXPIRED, ARCHIVED | C7 |
| SubscriptionAction.java | Enum: SUBMIT_FOR_APPROVAL, APPROVE, REJECT, PAUSE, RESUME, ARCHIVE | C7 |
| SubscriptionRepository.java | MongoRepository interface | C7 |
| SubscriptionFacade.java | Business logic facade | C7 |
| SubscriptionController.java | REST controller at /v3/subscriptions | C7 |
| SubscriptionStatusTransitionValidator.java | EnumMap-based transition validator | C7 |
| SubscriptionValidatorService.java | Name uniqueness, field validations | C7 |
| SubscriptionStatusChangeRequest.java | DTO with "action" field | C7 |
| SubscriptionThriftPublisher.java | Maps UnifiedSubscription to PartnerProgramInfo for Thrift call | C6 |

---

## Confidence: C7 (verified from reading actual code across all key files)
