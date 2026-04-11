# Approach Log -- Tiers CRUD
> What was decided, why, and what the user provided

## User Inputs
| Input | Value | Why It Matters |
|-------|-------|----------------|
| Feature name | Tiers CRUD | Scopes the pipeline to tier CRUD operations (subset of full Tiers & Benefits BRD) |
| Ticket ID | raidlc/ai_tier | Branch naming across all repos |
| Artifacts path | docs/pipeline/tier/ | All pipeline outputs stored here |
| BRD | Tiers_Benefits_PRD_v2_AiLed New.docx | Full PRD covering E1 (Tiers), E2 (Benefits), E3 (aiRa), E4 (API-First) |
| Primary repo | emf-parent | Core entities, strategies, Thrift services |
| Additional repos | intouch-api-v3, peb, Thrift | REST gateway, tier downgrade, IDL definitions |
| UI design | v0.app URL (screenshots pending) | Tier management UI reference |
| Dashboard | yes | Live HTML dashboard for progress tracking |
| Multi-epic | yes (registry: BaljeetSinghCapillaryTech/kalpavriksha, epic: tier-management) | Coordination with other developers on the same BRD |

## Decisions Made During Phase 0
| # | Question | Options Presented | Chosen | Reasoning |
|---|----------|-------------------|--------|-----------|
| D-01 | gh CLI not installed | (a) Install now (b) Local-only registry (c) Skip coordination | (a) Install | User wants full multi-epic coordination |
| D-02 | Repo path discrepancy (two emf-parent locations) | Clarify which is canonical | Both confirmed same repos | Desktop/emf-parent is workspace folder containing sibling repos; AI/emf-parent is the actual git repo |
| D-03 | Ticket ID format confirmation | raidlc/ai_tier as branch name | Confirmed | Multi-epic convention (raidlc/ prefix) |
| D-04 | v0.app URL unreadable | Ask for screenshots | User will provide | Client-side rendered URLs can't be fetched |
| D-05 | jdtls not found at ~/.jdtls-daemon/ | (a) Install jdtls (b) Proceed without LSP | (a) Install | Found at project-level paths; binary needed via brew |
| D-06 | Thrift not a git repo | Treat as read-only reference | Confirmed | Directory of .thrift IDL files, no branching needed |
| D-07 | kalpavriksha has uncommitted changes on epic-division | (a) Stash (b) Commit first (c) Carry forward | (b) Commit | Clean commit history before switching branches |

## Decisions Made During Phase 1 (BA)
| # | Question | Options Presented | Chosen | Reasoning |
|---|----------|-------------------|--------|-----------|
| D-08 | Scope: which user stories? | (a) Strict tier-category (b) Full E1 (c) Custom | Hybrid: E1-US1/US2/US3 + Deletion + generic MC framework | Focused delivery with extensible architecture. MC framework is Layer 1 shared module. |
| D-09 | Tier deletion strategy | (a) Soft-delete with status (b) Hide from UI only (c) True delete | (a) Soft-delete with status column on program_slabs | Enables tier lifecycle (DRAFT/ACTIVE/STOPPED). Required for maker-checker flow. All existing queries need status filter. |
| D-10 | Data storage for tier config | (a) Aggregate from existing (b) Normalize new tables (c) Hybrid | Dual-storage: MongoDB draft + SQL live (same as unified promotions) | Follows existing UnifiedPromotion pattern. MongoDB for draft/pending, SQL for engine-readable entities. Thrift sync on approval. |
| D-11 | Member counts in listing | (a) Include live (b) Exclude (c) Include cached | (c) Cached counts, included in response | customer_enrollment is hot table, no existing count-by-slab query. 5-15 min refresh sufficient for UI. |
| D-12 | Maker-checker framework design | (a) Full generic framework (b) Tier-specific with extension points | (a) Full generic framework | Layer 1 shared module. PendingChange entity, MakerCheckerService interface, ChangeApplier strategy. Tiers first consumer. |
| D-13 | Tier editing approach | (a) Versioned edits (b) In-place with MC (c) Hybrid by field type | (a) Versioned edits with parentId (same as unified promotions) | Full rollback capability. Consistent with existing codebase pattern. ACTIVE stays live until new version approved. |
| D-14 | API hosting | intouch-api-v3 vs emf-parent vs other | intouch-api-v3 (REST + MongoDB) -> Thrift -> emf-parent (SQL) | Same architecture as unified promotions. intouch-api-v3 has MongoDB access and existing approval patterns. |
| D-15 | MC toggle granularity | (a) Per-program (b) Per-program + per-entity-type (c) Per-program + per-role | (b) Per-program + per-entity-type | Generic framework needs entity-type granularity. Different entities may have different risk profiles. |
