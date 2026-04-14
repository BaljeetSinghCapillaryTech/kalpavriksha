# Approach Log -- subscription-program-revamp
> What was decided, why, and what the user provided

## User Inputs
| Input | Value | Why It Matters |
|-------|-------|---------------|
| Feature name | subscription-program-revamp | Covers all 4 epics of Tiers & Benefits PRD v3 |
| Ticket ID | subscription_v1 | Git branch: aidlc/subscription_v1 |
| BRD | Tiers_Benefits_PRD_v3_Full.pdf (47 pages) | Comprehensive PRD with 4 epics, user personas, API contracts, acceptance criteria |
| Primary repos | intouch-api-v3, emf-parent | REST gateway + core loyalty engine |
| Thrift repos | 6 thrift sub-repos under thrifts/ | Cross-service RPC interface definitions |
| DB schema repo | cc-stack-crm (read-only) | Source of truth for MySQL schema, tables, indexes |
| UI prototype | v0.app URL | Client-side rendered, needs Chrome MCP or screenshots |
| Dashboard | enabled | Live HTML dashboard updates after every phase |

## Decisions

### Phase 0: Input Collection

**Q: Is cc-stack-crm relevant to this feature?**
- Context: cc-stack-crm appears to be a DevOps/infrastructure repo (alerts, aurora, cloudflare, kubernetes configs), not a Java application.
- User answer: YES -- it contains all MySQL databases, tables, schema, and indexes for the platform. Source of truth for database structure.
- Decision: Include as read-only reference repo. No feature branch needed.
- Impact: Critical for Phase 5 (codebase research) and Phase 6b (migration planning) to understand current DB schema.

**Q: How to handle thrift-ifaces-pointsengine-rules carry-over modifications?**
- Context: This repo had modified pointsengine_rules.thrift + pom.xml from prior aidlc-demo-v2 branch work.
- Decision: Flagged in session memory for review. Changes carried over to the new feature branch.
- Impact: Must verify these modifications don't conflict with new subscription feature work.

**Q: How to handle kalpavriksha uncommitted changes (.claude/settings.json, knowledge-bank.md)?**
- Context: Pipeline config files, not feature code.
- User answer: Option C -- they carry over to the feature branch, that's fine.
- Decision: Pipeline config changes coexist on the feature branch.

### Phase 1: BA Deep-Dive + PRD Generation

**Q1: Which epics are in scope for this pipeline run?**
- Options: (a) E3 only, (b) E3+E4, (c) All four, (d) Other
- User answer: (a) E3 only -- Subscription Programs
- Decision: KD-04. E1, E2, E4 are out of scope. Separate pipeline runs.
- Impact: Narrowed scope from 4 epics to 1 epic. All architecture and design focuses on subscriptions.

**Q2: Which E3 user stories require backend work?**
- User answer: E3-US1 (Listing), E3-US2 (CRUD+validations+maker-checker), E3-US4 (Lifecycle+enrollment), E3-US5 (API contract) are IN SCOPE. E3-US3 (aiRa) is OUT. Auditing is also OUT.
- Decision: KD-14, KD-15. Backend scope is CRUD + validations + maker-checker + lifecycle. No aiRa, no auditing.
- Impact: Significant reduction in AI/ML complexity. Focus on core CRUD and state machine.

**Q3: Storage architecture for new subscription fields?**
- User answer: (1) Price is an Extended Field, NOT a subscription entity field. (2) Tier-related fields already exist in MySQL -- reuse, don't duplicate to MongoDB. (3) New metadata fields (migrate_on_expiry, group_tag, reminders, custom_fields) go in MongoDB.
- Decision: KD-16, KD-17, KD-18, KD-19. No new MySQL columns. MongoDB for new metadata. Extended Fields for price.
- Impact: No Flyway migrations needed. Dual storage pattern: MongoDB during draft, MySQL on approval.
- Research done: Read partner_program_tier_sync_configuration DDL, UnifiedPromotion MongoDB model, ExtendedField.EntityType enum.

**Q4: Maker-checker design approach?**
- User answer: Option (b) -- same flow pattern as UnifiedPromotion. First assess if extraction is safe. If not, clean-room.
- BA assessment: Clean-room recommended [C5]. UnifiedPromotion's maker-checker has 6+ promotion-specific hooks deeply woven into transitions (journeyEditHandler, communicationApprovalStatus, targetGroupFacade, etc.). Extraction risks regression.
- Decision: KD-21, KD-22. Clean-room implementation in new `makechecker` package. Reusable for Tiers/Benefits later.
- Impact: More initial work than extraction, but zero regression risk to UnifiedPromotion. Cleaner architecture.

**Q5: Custom fields and reminders scope?**
- User answer: (a) All 3 custom field levels in scope (META, LINK, DELINK). (b) Reminders: publish-on-approve pattern -- MongoDB during draft, synced to MySQL supplementary_partner_program_expiry_reminder on approval.
- Decision: KD-23, KD-24, KD-25. Full custom field model. Publish-on-approve is the general pattern for ALL subscription data.
- Impact: This generalised the publish-on-approve pattern beyond just reminders to ALL subscription data.
