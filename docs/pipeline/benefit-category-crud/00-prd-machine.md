---
feature: Benefit Category CRUD
ticket: CAP-185145
phase: 1
artifact: prd
derived_from: [00-ba.md, 00-ba-machine.md]
date: 2026-04-18

problem_statement: >
  Capillary wants benefits to become a first-class "product" — configurable at program level, grouped
  into categories, assignable to tiers independently of promotions. This ticket delivers the first
  thin slice: a config registry with clean boundaries for future extension.

goals:
  - Config registry for admins (Category + Instance CRUD)
  - Clean boundary — config only, no awarding logic
  - Zero blast radius on legacy Benefits entity
  - Extensible shape (room for trigger semantics, value schemas, approval later)
  - Tenant-safe (org-scoped queries)

non_goals:
  - Benefit awarding / application logic
  - 9 category types' specific semantics
  - triggerEvent field or derivation
  - Value payloads on instances
  - Maker-checker approval workflow
  - aiRa natural-language mapping
  - Matrix View UI
  - Subscription picker
  - Migrating legacy Benefits
  - Hard-delete

personas:
  - id: maya
    name: Maya — Program Manager
    type: human
    primary_stories: [US-1, US-2, US-3, US-4, US-5, US-6, US-7, US-8, US-9, US-10]
  - id: consumer_system
    name: Consumer System (TBD — likely EMF tier event forest)
    type: system
    primary_stories: [US-2, US-3, US-8]
    notes: "Reads config to apply benefits. Identity confirmed in Phase 5."

epics:
  - id: E1
    name: Benefit Category Management
    stories: [US-1, US-2, US-3, US-4, US-5, US-6]
  - id: E2
    name: Benefit Instance Linking
    stories: [US-7, US-8, US-9, US-10]

success_metrics:
  - {metric: "MVP delivery", target: "All P0 stories shipped behind feature flag", measurement: "Feature flag + AC pass"}
  - {metric: "Data integrity", target: "0 orphaned instances", measurement: "Cron audit + observability"}
  - {metric: "Tenancy", target: "0 cross-org leaks", measurement: "Automated test suite + Phase 11 security review"}
  - {metric: "Adoption", target: "TBD (product defines)", measurement: "Create API analytics"}
  - {metric: "Consumer integration", target: "Consumer reads config in first integration test", measurement: "Phase 9/10 integration test"}

dependencies:
  - {id: DEP-1, name: "Consumer identification (OQ-15)", owner: "Engineering — Phase 5", risk: high, blocks: "phase-6-api-freeze"}
  - {id: DEP-2, name: "Existing Tier table", owner: "Platform", risk: low}
  - {id: DEP-3, name: "Auth/tenancy middleware", owner: "Platform", risk: low}
  - {id: DEP-4, name: "UI designs from v0.app", owner: "Design — Phase 3", risk: medium, note: "v0.app client-side rendered, may need screenshots"}

release_plan:
  mode: "Single MVP release behind feature flag"
  phases:
    - {name: "Internal validation", description: "APIs + console for controlled org"}
    - {name: "Limited rollout", description: "2-3 pilot orgs"}
    - {name: "General availability", description: "All orgs"}

follow_up_tickets:
  - {id: FU-1, scope: "Widen category_type enum + per-type behaviour (9 types)"}
  - {id: FU-2, scope: "trigger_event column + mapping + event dispatch"}
  - {id: FU-3, scope: "Per-type value schemas on Instance"}
  - {id: FU-4, scope: "Re-introduce maker-checker workflow"}
  - {id: FU-5, scope: "aiRa integration"}
  - {id: FU-6, scope: "Matrix View UI"}
  - {id: FU-7, scope: "Subscription benefit picker"}
  - {id: FU-8, scope: "Legacy Benefits unification/migration (strategic — may never happen)"}

open_questions:
  - {id: OQ-4, owner: product, blocking: false}
  - {id: OQ-12, owner: product, blocking: false}
  - {id: OQ-15, owner: "engineering - phase-5", blocking: true, unblocks: "phase-6"}

ready_for_phase: 2
---
