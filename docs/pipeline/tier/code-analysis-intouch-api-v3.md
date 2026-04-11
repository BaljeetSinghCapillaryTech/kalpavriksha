# Code Analysis -- intouch-api-v3

> Phase 5: Codebase Research
> Date: 2026-04-11

---

## Key Architectural Insights

1. **UnifiedPromotion is the exact pattern to follow.** It uses MongoDB (@Document), Spring Data MongoRepository, sharded access via EmfMongoDataSourceManager, versioned editing (parentId), StatusTransitionValidator, EntityOrchestrator for SQL sync, @Lockable for concurrency, and ResponseWrapper<T> for API responses.

2. **The controller/facade/repository layering is consistent.** UnifiedPromotionController -> UnifiedPromotionFacade -> UnifiedPromotionRepository (MongoRepository + Custom). The tier system should follow the same layering.

3. **Authentication uses AbstractBaseAuthenticationToken -> IntouchUser.** Every controller method receives this token and extracts orgId from it. All queries are scoped by orgId.

4. **PointsEngineRulesThriftService is the Thrift client for emf-parent.** It calls `PointsEngineRuleService.Iface` via `RPCService.rpcClient()` on host "emf-thrift-service" port 9199. Slab methods exist in the Thrift IDL but are NOT currently wrapped in this class.

## Pattern Inventory

### Controller Pattern (UnifiedPromotionController)
- `@RestController` + `@RequestMapping("/v3/promotions")`
- Jackson serialization (not Gson)
- `@Valid @RequestBody` for input validation
- `AbstractBaseAuthenticationToken token` for auth
- `ResponseWrapper<T>` envelope for all responses
- `HttpServletRequest request` passed to facade for request context

### Facade Pattern (UnifiedPromotionFacade)
- `@Component` (not @Service)
- Autowires: repository, orchestrator, validator, edit orchestrator, various services
- Handles business logic: status transitions, versioning, orchestration
- Uses `StatusTransitionValidator.validateTransition(currentStatus, action)` for state machine
- Uses `@Lockable` for concurrent edit protection (distributed lock, TTL 300s, acquire 5s)

### Repository Pattern (UnifiedPromotionRepository)
- Extends `MongoRepository<UnifiedPromotion, String>` + custom interface
- Custom queries via `@Query` with MongoDB query syntax
- Sharded MongoDB access via `EmfMongoDataSourceManager`
- Index creation in `@PostConstruct` using direct MongoDB driver
- Key queries: findByObjectIdAndOrgId, findByUnifiedPromotionIdAndStatus, findDraftByParentId, findDraftsByUnifiedPromotionIdAndOrgId

### Edit Pattern (UnifiedPromotionEditOrchestrator)
- `@Component` + `@Lockable` on main method
- Uses `UnifiedPromotionChangeDetector.detectChanges(active, draft)` to diff
- Multiple EditHandlers for different change types (metadata, activity, milestone, action, limit, workflow)
- Rollback factory + retry utility for failure handling
- Calls PointsEngineRulesThriftService for backend sync

### Status Transition Rules (StatusTransitionValidator)
```
DRAFT -> SUBMIT_FOR_APPROVAL
PENDING_APPROVAL -> APPROVE | REJECT
ACTIVE -> PAUSE | STOP
PAUSED -> APPROVE (resume) | STOP
STOPPED -> (terminal, no transitions)
```

## Files Relevant to Tier CRUD (Reference/Pattern)

| File | Purpose | Tier Equivalent |
|------|---------|----------------|
| UnifiedPromotionController.java | REST endpoints | TierController.java |
| UnifiedPromotionFacade.java | Business logic | TierFacade.java |
| UnifiedPromotion.java | MongoDB @Document | UnifiedTierConfig.java |
| UnifiedPromotionRepository.java | MongoRepository | TierRepository.java |
| UnifiedPromotionRepositoryImpl.java | Custom MongoDB ops | TierRepositoryImpl.java |
| UnifiedPromotionRepositoryCustom.java | Custom interface | TierRepositoryCustom.java |
| EntityOrchestrator.java | SQL sync on approval | TierChangeApplier.java |
| UnifiedPromotionEditOrchestrator.java | Edit flow | (simpler for tiers) |
| StatusTransitionValidator.java | State machine | Reuse or extend |
| PromotionStatus.java | Status enum | TierStatus.java |
| Lockable.java | Distributed lock | Reuse as-is |
| ResponseWrapper.java | API response envelope | Reuse as-is |
| EmfMongoDataSourceManager.java | Sharded MongoDB | Reuse as-is |
| PointsEngineRulesThriftService.java | Thrift client | Add slab wrapper methods |
