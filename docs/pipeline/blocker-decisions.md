# Blocker Decisions — Tier CRUD

> Feature: tier-crud
> Phase: 4 — Blocker Resolution
> Date: 2026-04-06

---

## BLOCKER Resolutions

### B-1: EntityType / RequestManagementController coupling
- **Decision**: Separate TierController endpoint for status changes (option a)
- **What**: New `POST /v3/tiers/{tierId}/status` with own `TierStatus` enum. Do NOT touch `RequestManagementController`.
- **Why**: Zero risk to existing promotion flow. Clean separation.

### B-2 + B-3: Soft-delete query leakage + DRAFT tiers in evaluation engine
- **Decision**: MongoDB-first architecture (like UnifiedPromotion)
- **What**: 
  - MongoDB stores full tier documents (config, strategies, status, future benefits)
  - DRAFT / PENDING_APPROVAL tiers live ONLY in MongoDB
  - On APPROVE → sync MongoDB doc to `program_slabs` + strategy tables via EMF Thrift endpoints
  - Evaluation engine only reads MySQL (`program_slabs` + strategies) = only ACTIVE tiers
  - Soft-delete sets `active=0` in `program_slabs`. Only `active` column needed in SQL, no `status` column.
- **Why**: Cleanly separates config management (MongoDB) from operational data (MySQL). Evaluation engine completely unaffected. Future-proof for benefits (E2).

### B-4: "Evaluation logic unaffected" claim
- **Decision**: Auto-resolved by MongoDB architecture
- **What**: DRAFT tiers never enter `program_slabs`, so evaluation engine is genuinely unaffected.

---

## HIGH Issue Resolutions

### H-1: Threshold validation (create vs update)
- **Decision**: Neighbor-ordering validation for updates
- **What**: On update, threshold must satisfy `tier[n-1].threshold < new_threshold < tier[n+1].threshold`. Validation runs against MongoDB docs.

### H-2: Tier creation involves ruleset orchestration
- **Decision**: CRUD writes MongoDB only. On APPROVE, intouch-api-v3 calls EMF Thrift endpoints for ruleset/strategy creation + program_slabs write. Clean service boundary — never call internal EMF methods directly.

### H-3: PartnerProgramTierSyncConfiguration references
- **Decision**: Soft-delete validation must check partner program sync references. Return error with dependency list if any exist.

### H-4: PromotionStatus enum has 10 values
- **Decision**: Create separate `TierStatus` enum with 4 values (DRAFT, PENDING_APPROVAL, ACTIVE, STOPPED). Do not reuse PromotionStatus.

---

## Grooming Question Resolutions

### GQ-1: dailyDowngradeEnabled, retainPoints scope
- **Decision**: Program-level configs, not per-tier. Stored in MongoDB doc as program-level fields.

### GQ-2: Soft-deleted tier members
- **Decision**: User must migrate ALL members out before soft-delete. Validation: cannot delete tier with members. Simulation phase (future) will surface member count to user.

### GQ-3: Member count in GET /tiers
- **Decision**: Include member count per tier in GET response. Cross-service query needed — must verify indexes.

### GQ-4: PUT vs PATCH
- **Decision**: PUT only, no PATCH. Same as UnifiedPromotion.

---

## Architecture Summary (Post-Blockers)

```
CRUD Flow:
  UI/aiRa → intouch-api-v3 (TierController) → MongoDB (tier document)
  
Approval Flow:
  POST /v3/tiers/{id}/status (APPROVE) → intouch-api-v3 → EMF Thrift → program_slabs + strategies (MySQL)

Read Flow:
  GET /v3/tiers → MongoDB (full config, all statuses)
  Evaluation engine → MySQL program_slabs + strategies (ACTIVE only)

Data Stores:
  MongoDB: Full tier document (config, strategies, status, metadata, future benefits)
  MySQL program_slabs: ACTIVE tiers only + active flag for soft-delete
  MySQL strategies: SLAB_UPGRADE, SLAB_DOWNGRADE, etc. (synced on APPROVE)
  cc-stack-crm: Schema DDL files (active column migration)

Repos:
  intouch-api-v3: TierController, TierFacade, DTOs, MongoDB repository
  emf-parent: Thrift endpoints for tier persistence + strategy creation
  cc-stack-crm: ALTER TABLE for active column
```

## Validation Rules (Updated)

### Soft-Delete Validations
1. Cannot delete base tier
2. Cannot delete if tier is downgrade target of another active tier
3. Cannot delete if tier still has members (user must migrate first)
4. Cannot delete if tier is referenced in PartnerProgramTierSyncConfiguration
5. All validation queries must use existing indexes — flag if new indexes needed

### Index Awareness
- All new validation queries must be checked against existing indexes
- If a new query requires a full table scan, flag it and propose an index
