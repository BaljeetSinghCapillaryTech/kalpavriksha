# Approach Log -- Subscription-CRUD
> What was decided, why, and what the user provided

## User Inputs
| Input | Value | Why It Matters |
|-------|-------|----------------|
| Feature name | Tier-CRUD | Identifies this pipeline run |
| Ticket ID | aidlc-demo-v2 | Git branch naming: aidlc/aidlc-demo-v2 |
| Artifacts path | docs/ | Where all pipeline outputs are stored |
| BRD | Tiers_Benefits_PRD_v3_Full.pdf (47 pages) | Source of truth for requirements -- covers 4 epics across tiers, benefits, subscriptions, and benefit categories |
| Primary repo | emf-parent | Multi-module Maven project containing tier/slab entities, strategies, Thrift services |
| Additional repos | intouch-api-v3, cc-stack-crm, thrifts | REST gateway, DB schema, and Thrift IDL definitions respectively |
| UI source | v0.app URL | Client-side rendered prototype for tiers listing page |
| Dashboard | Yes | Live HTML dashboard updates after every phase |

## Decisions Made

### Phase 0
| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| D-01 | Should cc-stack-crm be included as a code repo? | Yes -- keep it | User confirmed it contains DB schema, tables, and indexes that should be read by every code agent |
| D-02 | What is the scope for this pipeline run? | E3 (Subscription Programs) is PRIMARY. Subscriptions CRUD, maker-checker, subscription-benefits linking with dummy benefit objects. E1, E2, E4 are OUT OF SCOPE. | User corrected initial scope (was E1+E4+E2 parts). Subscriptions are the focus. Benefits use dummy objects since real benefit categories are not yet built. |

### Phase 1 (BA Q&A)
| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| D-03 | Which user stories are in scope? | E3-US2 (CRUD), E3-US4 (Lifecycle), E3-US5 (API Contract) + maker-checker. OUT: E3-US1 (Listing UI), E3-US3 (aiRa). Full REST API layer. Benefit linking uses dummy objects. | Backend-focused run; no UI rendering, no AI assistant integration |
| D-04 | Which tier-linking model? BRD's direct tier-linking vs codebase's slab hierarchy? | Keep codebase model: own slab hierarchy via partner_program_slabs, synced to loyalty tiers via PartnerProgramTierSyncConfiguration. | Backward compatibility with existing partner program infra; avoid breaking enrolled members |
| D-05 | How to handle subscription pricing? New DB columns vs Extended Fields? | Use existing Extended Fields mechanism from api/prototype. Create 'price' named extended field for SUPPLEMENTARY programs. Requires adding PARTNER_PROGRAM to ExtendedField.EntityType enum. | Reuse existing infra; no schema migration needed for partner_programs table; pricing is metadata; extended fields already have validation + audit trail + REST API |
| D-06 | How to implement lifecycle state machine (7 states) + maker-checker? Options: (a) add status column to MySQL partner_programs, (b) replace is_active with status, (c) separate state table, (d) MongoDB following UnifiedPromotion pattern. | **(d) MongoDB-first** -- all subscription config, lifecycle, maker-checker, benefit linking in MongoDB (intouch-api-v3). MySQL only updated on Active transition via EMF Thrift. New UnifiedSubscription document, SubscriptionRepository, extend EntityType + RequestManagementFacade, SubscriptionStatusTransitionValidator. | User rejected all MySQL-based options. Follows proven UnifiedPromotion pattern: no schema migration risk, flexible document model, maker-checker versioning (edit ACTIVE creates DRAFT with parentId), multi-tenant MongoDB already configured. This is an ADR-worthy decision (KD-07). |
| D-07 | How to represent benefit links in the subscription MongoDB document? Options: (a) embedded array with benefit snapshots, (b) separate subscription_benefits collection, (c) hybrid. | **None of the above.** Store only `benefitIds: ["id1", "id2"]` -- plain array of foreign key references. No embedded metadata, no snapshots, no separate collection. Benefits will be a first-class entity (future E2/E4 run) with own CRUD, maker-checker, audit trail, mappable to tiers/subscriptions/other entities. Dummy IDs used for this run. | User decision: benefits are NOT a subscription sub-entity. Clean separation of concerns. Future-proof for Benefits-as-a-Product epic. ADR-worthy (KD-08). |
| D-08 | Include reminders and custom fields in this run? Options: (a) include both as config storage, (b) custom fields only, (c) defer both. | **(a) Include both** -- store reminder config (embedded array, max 5, daysBefore + channel) and custom field config (embedded object with meta/link/delink/pause/resume arrays of field IDs) in the MongoDB document. Config storage ONLY -- no reminder triggering, no custom field enforcement at enrollment. | Keeps API contract complete per BRD E3-US5. Trivial document fields. No external system integration needed for config storage. Triggering and enforcement are future enhancements. (KD-09) |
| D-09 | Enrollment API boundary: delegate to existing v2 Thrift paths, or build new v3 APIs in intouch-api-v3, or proxy? | **New v3 APIs in intouch-api-v3 calling EMF Thrift directly** (not proxying api/prototype). api/prototype v2 linking APIs remain untouched for existing callers. v3 controller is the unified surface for subscription config + enrollment. MongoDB: config/lifecycle/maker-checker. MySQL (via Thrift): enrollment records/activation writes. | User decision: follows UnifiedPromotion pattern (v3 calls Thrift directly). Clean boundary: v3 = new surface, v2 = legacy. Enrollment data stays in MySQL because EMF owns it. (KD-10) |
