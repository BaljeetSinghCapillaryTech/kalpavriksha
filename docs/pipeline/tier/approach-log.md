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
