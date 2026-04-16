# Cross-Repo Trace -- Tiers CRUD

> Phase 5: Cross-repo write/read path tracing
> Date: 2026-04-11

---

## Write Path: Tier Creation (MC enabled)

```mermaid
sequenceDiagram
    participant UI as Garuda UI
    participant TC as TierController<br/>(intouch-api-v3)
    participant TF as TierFacade<br/>(intouch-api-v3)
    participant TR as TierRepository<br/>(MongoDB)
    participant MCS as MakerCheckerService<br/>(makechecker package)
    
    UI->>TC: POST /v3/tiers {tierConfig}
    TC->>TF: createTier(orgId, tierConfig)
    TF->>TF: validate(tierConfig)
    TF->>TF: isMakerCheckerEnabled(orgId, programId, TIER)
    alt MC enabled
        TF->>TR: save(UnifiedTierConfig{status=DRAFT})
        TR-->>TF: saved doc with _id
        TF-->>TC: TierConfig{status=DRAFT}
    else MC disabled
        TF->>TR: save(UnifiedTierConfig{status=ACTIVE})
        TF->>TF: syncToSQL(tierConfig)
        Note over TF: calls TierApprovalHandler
        TF-->>TC: TierConfig{status=ACTIVE}
    end
    TC-->>UI: ResponseWrapper<TierConfig>
```

## Write Path: Tier Approval (MC approve)

```mermaid
sequenceDiagram
    participant UI as Garuda UI
    participant TRC as TierReviewController<br/>(intouch-api-v3)
    participant MCS as MakerCheckerService<br/>(makechecker package)
    participant TAH as TierApprovalHandler<br/>(intouch-api-v3)
    participant PERTS as PointsEngineRules<br/>ThriftService
    participant EMF as PointsEngineRule<br/>Service (emf-parent)
    participant DB as MySQL<br/>(program_slabs + strategies)
    
    UI->>MCC: POST /v3/maker-checker/{id}/approve
    MCC->>MCS: approve(changeId, reviewedBy)
    MCS->>MCS: validate status transition (PENDING_APPROVAL->ACTIVE)
    MCS->>TAH: publish(pendingChange)
    TAH->>TAH: extract SlabInfo + StrategyInfo from MongoDB doc
    TAH->>PERTS: createSlabAndUpdateStrategies(programId, orgId, slabInfo, strategyInfos)
    PERTS->>EMF: Thrift RPC (port 9199)
    EMF->>DB: INSERT/UPDATE program_slabs
    EMF->>DB: INSERT/UPDATE strategies
    EMF-->>PERTS: SlabInfo (created)
    PERTS-->>TAH: SlabInfo
    TAH->>TAH: update MongoDB doc status PENDING->ACTIVE
    TAH->>TAH: if versioned edit: old doc -> SNAPSHOT
    TAH-->>MCS: success
    MCS-->>MCC: PendingChange{status=APPROVED}
    MCC-->>UI: ResponseWrapper<PendingChange>
```

## Read Path: Tier Listing

```mermaid
sequenceDiagram
    participant UI as Garuda UI
    participant TC as TierController<br/>(intouch-api-v3)
    participant TF as TierFacade<br/>(intouch-api-v3)
    participant TR as TierRepository<br/>(MongoDB)
    participant CACHE as MemberCountCache
    
    UI->>TC: GET /v3/tiers?programId=123
    TC->>TF: listTiers(orgId, programId, statusFilter)
    TF->>TR: findByOrgIdAndProgramId(orgId, programId, statusFilter)
    TR-->>TF: list<UnifiedTierConfig>
    TF->>CACHE: getMemberCounts(orgId, programId)
    CACHE-->>TF: Map<slabId, count>
    TF->>TF: assemble response (config + counts + KPI summary)
    TF-->>TC: TierListResponse
    TC-->>UI: ResponseWrapper<TierListResponse>
```

## Member Count Cache Refresh Path

```mermaid
sequenceDiagram
    participant CRON as Scheduled Job<br/>(every 10 min)
    participant EMF as emf-parent
    participant DB as MySQL<br/>(customer_enrollment)
    participant MONGO as MongoDB<br/>(tier stats)
    
    CRON->>DB: SELECT current_slab_id, COUNT(*)<br/>FROM customer_enrollment<br/>WHERE org_id=? AND program_id=?<br/>AND is_active=true<br/>GROUP BY current_slab_id
    DB-->>CRON: [{slabId: 1, count: 1245}, ...]
    CRON->>MONGO: upsert tier member stats
    MONGO-->>CRON: saved
```

## Per-Repo Change Inventory

### intouch-api-v3 (PRIMARY -- most new code)

| Type | File | Why |
|------|------|-----|
| NEW | resources/TierController.java | REST endpoints for tier CRUD |
| NEW | resources/TierReviewController.java | REST endpoints for tier approval workflow |
| NEW | tier/TierFacade.java | Tier business logic + approval integration |
| NEW | tier/UnifiedTierConfig.java | MongoDB @Document for tier config |
| NEW | tier/TierRepository.java | MongoRepository interface |
| NEW | tier/TierRepositoryImpl.java | Custom MongoDB queries + sharded access |
| NEW | tier/TierRepositoryCustom.java | Custom query interface |
| NEW | tier/TierApprovalHandler.java | ApprovableEntityHandler<Tier> impl: MongoDB -> Thrift -> SQL |
| NEW | tier/TierValidationService.java | Field-level validation |
| NEW | tier/model/*.java | BasicDetails, EligibilityCriteria, RenewalConfig, DowngradeConfig, etc. |
| NEW | tier/enums/TierStatus.java | DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT |
| NEW | tier/dto/TierCreateRequest.java | Create request DTO |
| NEW | tier/dto/TierUpdateRequest.java | Update request DTO |
| NEW | tier/dto/TierListResponse.java | List response with KPI summary |
| NEW | makechecker/MakerCheckerService.java | Generic approval service interface |
| NEW | makechecker/MakerCheckerServiceImpl.java | Approval implementation |
| NEW | makechecker/ApprovableEntityHandler.java | Strategy interface for domain-specific sync |
| NEW | makechecker/ApprovalRecord.java | MongoDB @Document for approval tracking |
| NEW | makechecker/ApprovalRepository.java | MongoRepository for approvals |
| NEW | makechecker/enums/EntityType.java | TIER, BENEFIT, SUBSCRIPTION, etc. |
| NEW | makechecker/enums/ApprovalStatus.java | PENDING, APPROVED, REJECTED |
| NEW | makechecker/dto/ApprovalRequest.java | Approval request DTO |
| NEW | makechecker/dto/ApprovalDecision.java | Approval/rejection decision DTO |
| NEW | makechecker/NotificationHandler.java | Hook interface for notifications |
| MODIFIED | services/thrift/PointsEngineRulesThriftService.java | Add wrapper methods for slab Thrift calls |

**Total: ~25 new files, 1 modified file**

### emf-parent (MINIMAL changes)

| Type | File | Why |
|------|------|-----|
| ~~MODIFIED~~ | ~~points/entity/ProgramSlab.java~~ | ~~Add status field~~ — NOT NEEDED (Rework #3) |
| ~~MODIFIED~~ | ~~points/dao/PeProgramSlabDao.java~~ | ~~Add findActiveByProgram() method~~ — NOT NEEDED (Rework #3) |
| ~~NEW~~ | ~~Flyway migration V__add_program_slab_status.sql~~ | ~~ALTER TABLE + INDEX~~ — NOT NEEDED (Rework #3) |

**Total: 0 files — No emf-parent entity/DAO changes needed. SQL only contains ACTIVE tiers, no status column.**

### Thrift (NO changes needed)

The existing `pointsengine_rules.thrift` already has:
- `createSlabAndUpdateStrategies` (create + config sync)
- `getAllSlabs` (read all slabs)
- `createOrUpdateSlab` (upsert slab)

**No Thrift IDL change required for basic CRUD.** May need a new method for status-only updates (setting STOPPED) if `createOrUpdateSlab` doesn't support it -- to be verified in HLD.

### peb (NO changes in this pipeline run)

PEB reads program_slabs for tier downgrade/reassessment. Since we're using expand-then-contract (existing `findByProgram()` unchanged), PEB is unaffected. PEB will continue to see all slabs including STOPPED ones, which is correct for historical evaluation.

**0 modifications needed.** (C6 -- verified: PEB uses its own DAO calls that don't filter by status, and the new status column defaults to ACTIVE for existing rows.)

## Cross-Repo Dependency Map

```mermaid
graph LR
    subgraph "intouch-api-v3"
        TC[TierController] --> TF[TierFacade]
        TF --> TR[TierRepo<br/>MongoDB]
        TF --> MCS[MakerCheckerService]
        MCS --> TAH[TierApprovalHandler]
        TRC[TierReviewController] --> MCS
    end
    
    subgraph "emf-parent"
        TAH[TierApprovalHandler] -->|"Thrift: createSlabAndUpdateStrategies<br/>port 9199"| PERS[PointsEngineRuleService]
        PERS --> PSD[PeProgramSlabDao]
        PERS --> STR[Strategy]
        PSD --> SQL[(MySQL<br/>program_slabs)]
        STR --> SQL
    end
    
    subgraph "peb (unchanged)"
        TDB[TierDowngradeBatch] -.->|reads| SQL
        TRS[TierReassessment] -.->|reads| SQL
    end
    
    subgraph "Thrift IDL (unchanged)"
        IDL[pointsengine_rules.thrift<br/>SlabInfo, StrategyInfo<br/>createSlabAndUpdateStrategies]
    end
```
