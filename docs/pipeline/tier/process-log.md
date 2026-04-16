# Process Log -- Tiers CRUD
> Started: 2026-04-11
> Ticket: raidlc/ai_tier
> Pipeline: feature-pipeline v1.0

## Inputs Provided
- BRD: /Users/ritwikranjan/Desktop/Artificial Intelligence/Tiers_Benefits_PRD_v2_AiLed New.docx (extracted to brd-raw.md)
- Code repos:
  - emf-parent: /Users/ritwikranjan/Desktop/Artificial Intelligence/emf-parent
  - intouch-api-v3: /Users/ritwikranjan/Desktop/emf-parent/intouch-api-v3
  - peb: /Users/ritwikranjan/Desktop/emf-parent/peb
  - Thrift (read-only): /Users/ritwikranjan/Desktop/emf-parent/Thrift
- UI: v0.app URL provided but client-side rendered; user will provide screenshots
- Dashboard: enabled
- Multi-epic: yes (registry: BaljeetSinghCapillaryTech/kalpavriksha, epic: tier-management)

## Phase Log

### Phase 0: Input Collection
- Time: 2026-04-11
- BRD validated: DOCX file (48KB, 559 lines extracted)
- Repos validated: 4 repos confirmed accessible
- Git branches created: raidlc/ai_tier across emf-parent, intouch-api-v3, peb, kalpavriksha
- Thrift: confirmed as read-only IDL directory (not a git repo)
- gh CLI: installed (v2.89.0) and authenticated (RitwikRanjanPathak)
- Registry repo: accessible (BaljeetSinghCapillaryTech/kalpavriksha, default branch: main)
- jdtls: installation in progress via brew
- Dashboard: created (live-dashboard.html)
- All inputs validated

### Phase 1: BA Deep-Dive + PRD Generation
- Time: 2026-04-11
- BRD read: 559 lines, 4 epics (E1 Tier Intelligence, E2 Benefits, E3 aiRa, E4 API-First)
- Product docs fetched: docs.capillarytech.com (tier creation, downgrade/renewal, strategies)
- Codebase research: ProgramSlab entity, TierConfiguration DTO, SlabUpgradeMode enum, TierDowngradeSlabConfig, PeProgramSlabDao, PeCustomerEnrollmentDao, UnifiedPromotion (MongoDB pattern), PromotionStatus lifecycle, EntityOrchestrator
- LSP (jdtls) used: symbol search for ProgramSlab (25 results), Slab (45 results), TierConfig (15 results), CustomerEnrollment (11 results), SlabUpgradeStrategy (6 results)
- Key finding: ZERO tier REST APIs exist in intouch-api-v3. All tier operations go through Thrift.
- Key finding: maker-checker exists only for promotions (UnifiedPromotionFacade). No tier MC.
- Key finding: UnifiedPromotion pattern = MongoDB draft -> EntityOrchestrator -> SQL sync on approval. THIS is the pattern for tiers.
- Questions asked: 8 (all human concerns, resolved)
- 8 key decisions recorded (D-08 through D-15)
- UI screenshots reviewed: 8 screenshots from v0.app prototype covering tier listing, eligibility, downgrade, benefits, benefit listing, benefit creation
- ProductEx: NOT run in parallel this session (skipped to avoid context pressure)
- Artifacts: 00-ba.md, 00-ba-machine.md, 00-prd.md, 00-prd-machine.md
- Session memory: 22 domain terms, 8 codebase findings, 16 key decisions, 6 constraints, 3 risks

### Phase 2: Critic + Gap Analysis
- Time: 2026-04-11
- Critic (Devil's Advocate): 6 contradictions found (1 BLOCKER, 2 HIGH, 2 MEDIUM, 1 LOW)
  - C-1 BLOCKER: No Thrift method for tier config sync
  - C-2 HIGH: PartnerProgramSlab impact not addressed
  - C-3 HIGH: PeProgramSlabDao blast radius (7+ services)
  - C-4 MEDIUM: Threshold validation oversimplified
  - C-5 LOW: "Scheduled" KPI undefined
  - C-6 LOW: MC framework scope vs registry decomposition
- Analyst (Compliance): 14 claims verified (all C6-C7), 6 gaps found
  - G-1 BLOCKER: Same as C-1 (no Thrift method)
  - G-2-G-6: Partner slab impact, DAO blast radius, strategy CSV thresholds, sharded MongoDB, edit flow complexity
- All 14 BA codebase claims CONFIRMED against actual code with file-level evidence
- Artifacts: contradictions.md, gap-analysis-brd.md

### Phase 3: UI Requirements Extraction
- Time: 2026-04-11
- Screenshots analyzed: 8 (4 in scope for tiers, 4 reference for benefits)
- Screens: Tier listing matrix, eligibility criteria, downgrade/exit, benefits-on-tier, benefits listing, benefit creation
- Fields extracted: 21 per-tier fields + 4 KPI summary fields
- 6 UI-BA gaps found:
  - GAP-1 HIGH: Tier "Duration" (startDate/endDate) missing from BA/PRD
  - GAP-2 MEDIUM: Activity condition compound model (operator/value/unit/relation) not defined
  - GAP-3 MEDIUM: "Membership Duration" vs "Duration" are different concepts, BA conflates them
  - GAP-4 LOW: Downgrade Schedule enum values (MONTH_END/DAILY) not specified in PRD
  - GAP-5 LOW: Benefits comparison matrix format not defined in PRD response shape
  - GAP-6 LOW: Variable tier count support needed (UI shows 7 possible tiers)
- Component hierarchy extracted: TiersPage -> ProgramSelector -> KpiSummaryBar -> ComparisonMatrix (5 sections)
- User flows: 4 flows documented (view, edit, navigate to benefits, filter)
- Artifact: ui-requirements.md

### Phase 4: Grooming Questions + Blocker Resolution
- Time: 2026-04-11
- Items compiled: 25 (from BA, Critic, Analyst, UI, three-way gap analysis)
- Classification: 1 BLOCKER, 3 HIGH, 6 MEDIUM, 15 SCOPE/FEASIBILITY
- BLOCKER resolved: New Thrift method configureTier() for tier config sync
- HIGHs resolved: PartnerProgramSlab block (409), expand-then-contract migration, tier Duration field
- Three-way gap analysis: 11 codebase gaps (A-1 to A-11), 4 UI gaps (B-1 to B-4), 4 BRD gaps (C-1 to C-4)
- User overrides: 3 (GQ-2: no bootstrap sync, GQ-3: Flow A confirmed, GQ-4: benefitIds only)
- Decisions recorded: D-16 through D-29 (14 new decisions)
- Total decisions in pipeline: 29
- All 25 items resolved. 0 remaining open.
- Artifacts: blocker-decisions.md, grooming-questions.md

### Phase 5: Codebase Research + Cross-Repo Tracing
- Time: 2026-04-11
- Repos researched: intouch-api-v3 (deep), emf-parent (deep), Thrift IDL (deep), peb (verified no changes)
- CRITICAL FINDING: Blocker C-1 REVISED. Thrift methods for slab CRUD ALREADY EXIST in pointsengine_rules.thrift (not emf.thrift). createSlabAndUpdateStrategies, getAllSlabs, createOrUpdateSlab all present. PointsEngineRulesThriftService in intouch-api-v3 just needs wrapper methods added. NO new Thrift IDL change needed.
- LSP (jdtls) used: symbol searches for CurrentValueType (1 result), UpgradeCriteria (4 results)
- Files analyzed in depth: UnifiedPromotionEditOrchestrator (edit/rollback pattern), StatusTransitionValidator (state machine), EmfMongoDataSourceManager (sharded interface), UnifiedPromotionRepository (MongoRepository + custom queries), UnifiedPromotionController (REST pattern), PointsEngineRulesThriftService (Thrift client), ResponseWrapper (API envelope), Lockable (distributed lock), TierDowngradePeriodConfig (PeriodType, computation window), AdditionalUpgradeCriteria (secondary upgrade criteria)
- Cross-repo trace: 4 sequence diagrams (create, approve, list, cache refresh)
- Change inventory: ~25 new files + 1 modified in intouch-api-v3. 1 new + 2 modified in emf-parent. 0 in Thrift IDL. 0 in peb.
- Artifacts: code-analysis-intouch-api-v3.md, code-analysis-emf-parent.md, cross-repo-trace.md
- LATE ADDITION: Production payload analysis from /loyalty/api/v1/strategy/tier-strategy/977
  - P-1 CRITICAL: Points strategy layer (allocations, redemptions, expirys) not in BA/PRD. Per-slab CSV values.
  - P-2: CSV-per-slab pattern -- new slab requires extending every strategy CSV
  - P-3: Upgrade section confirmed matches our model
  - P-4: Downgrade has isFixedTypeWithoutYear, renewalWindowType (different naming)
  - P-5: isAdvanceSetting, addDefaultCommunication -- new flags
  - P-6: updatedViaNewUI flag must be set on all new strategies

### Phase 6: HLD (Architect)
- Time: 2026-04-11
- Pattern evaluation: 6 patterns assessed, all HIGH fit with existing codebase
- 7 ADRs documented (ADR-01 through ADR-07)
- System architecture: 12 components across 3 repos
- MongoDB document schema: UnifiedTierConfig (8 sections, ~50 fields) + PendingChange (generic)
- API design: 8 endpoints (4 tier CRUD + 4 MC)
- TierChangeApplier: CREATE flow validated, UPDATE flow designed, STOP flow designed
- Status state machine: 7 states, 8 transitions
- Implementation plan: 4 layers with dependency ordering
- 5 risks catalogued with mitigations
- 12 done criteria
- Artifact: 01-architect.md

### Phase 6a: Impact Analysis
- Time: 2026-04-11
- Blast radius mapped: 2 direct changes (ProgramSlab, PeProgramSlabDao), 7 indirect modules checked (all SAFE)
- Security: COMPLIANT with G-03. Auth, parameterized queries, no PII.
- Performance: Listing <200ms. Member count cache needs new index on customer_enrollment.
- Backward compatibility: FULL. Expand-then-contract, existing methods unchanged, no Thrift IDL change.
- GUARDRAILS compliance: 3 attention items (G-01 timezone, G-06.1 idempotency, G-07.3 cron tenant)
- 8 risks catalogued (0 blocker, 2 high, 3 medium, 3 low)
- No blockers raised against Architect design
- Artifact: 02-analyst.md

### Phase 6b: Migration Planning
- Time: 2026-04-11
- Finding: emf-parent has NO Flyway/Liquibase. Migrations are standalone SQL scripts.
- ~~3 migrations planned:~~
  - ~~M-1: ALTER TABLE program_slabs ADD COLUMN status (FAST, <1s)~~ — NOT NEEDED (Rework #3)
  - ~~M-2: CREATE INDEX idx_program_slabs_org_program_status (FAST, <1s)~~ — NOT NEEDED (Rework #3)
  - M-3: CREATE INDEX idx_ce_org_program_slab_active on customer_enrollment (SLOW, 5-30 min, maintenance window, ALGORITHM=INPLACE)
- ~~All backward-compatible. All have rollback scripts.~~
- ~~Execution order: M-1+M-2 -> Deploy code -> M-3 -> Enable cache cron~~
- ~~No data migration needed (existing rows default to ACTIVE)~~
- **Rework #3**: M-1 and M-2 removed — SQL only contains ACTIVE tiers, no status column needed. M-3 (customer_enrollment index) may still be needed for member count cache.
- Artifact: 01b-migrator.md

### Phase 7: LLD (Designer) + API Handoff
- Time: 2026-04-11
- Designer (03-designer.md):
  - Package structure: 30+ classes across tier/ and makerchecker/ packages
  - Key interfaces: ChangeApplier<T> (strategy), MakerCheckerService, NotificationHandler (hook)
  - MongoDB documents: UnifiedTierConfig, PendingChange with full field definitions
  - 7 enums: TierStatus, EntityType, ChangeType, ChangeStatus, CriteriaType, ActivityRelation, DowngradeSchedule
  - Status transition rules defined as Map<TierStatus, Set<TierAction>>
  - 3 Thrift wrapper methods specified for PointsEngineRulesThriftService
  - ~~emf-parent changes: ProgramSlab +status field, PeProgramSlabDao +findActiveByProgram()~~ — NOT NEEDED (Rework #3)
- API Handoff (api-handoff.md):
  - 8 endpoints with complete URL, method, headers, query params
  - Full request body examples with realistic tier data (Bronze/Silver/Gold/Platinum)
  - Full response body examples (~300 lines of JSON across all endpoints)
  - Error response examples: 400 (validation), 409 (conflict/partner slabs/base tier), 500 (sync failure)
  - 2 complete end-to-end flow examples (Create+Submit+Approve, Versioned Edit)
  - Field reference tables (operators, statuses with badge colors, downgrade schedules)
  - 8 important notes for UI team
- Artifacts: 03-designer.md, api-handoff.md

### Phase 8: QA
- Time: 2026-04-11
- 65 test scenarios across 7 categories
- Breakdown: 41 P0 (must-pass), 22 P1, 2 P2
- Categories: Listing (12), Creation (10), Editing (9), Deletion (6), Maker-Checker (11), MC Toggle (5), Cross-Cutting (12)
- Cross-cutting covers: multi-tenancy isolation (G-07), concurrency (@Lockable), backward compatibility, CSV index correctness (R1 HIGH risk)
- Test data requirements: 2+ programs, 7+ tier states, 4+ strategy types
- Artifact: 04-qa.md
