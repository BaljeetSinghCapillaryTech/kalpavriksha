# Session Memory

> Artifacts path: docs/pipeline/
> Workflow started: Phase 0 / 2026-04-06
> Feature: tier-crud
> Ticket: test_branch_v3

---

## Domain Terminology
_Populated by BA from product docs and requirements. Use these terms consistently across all phases._

- **Tier** = UI/BRD-facing term for what the codebase calls **Slab** (backend entity: `ProgramSlab`, table: `program_slabs`). New code should use "Tier" in the API surface but may map to "Slab" internally. _(ProductEx)_
- **Slab** = internal/legacy backend term for Tier. `SlabUpgradeService`, `SlabDowngradeService`, `RenewSlabInstruction` are the current implementations. _(ProductEx)_
- **Benefits** = existing entity (table: `benefits`) with `promotionId` coupling. In BRD context, "Benefits as a Product" implies a new or migrated entity model. Name collision risk — verify before implementation. _(ProductEx)_
- **BenefitsType** = current enum with only `VOUCHER` and `POINTS` values. BRD proposes multiple new types. _(ProductEx)_
- **TierConfiguration** = existing DTO used for downgrade/renewal config, serialized via Gson. Contains `isDowngradeOnReturnEnabled`, `dailyDowngradeEnabled`, `slabConfigs`, `retainPoints`. _(ProductEx)_
- **Maker-checker** = approval workflow currently implemented for Promotions in `intouch-api-v3` (`RequestManagementController`, `ApprovalStatus` enum). Not yet wired for tier/benefit entities. _(ProductEx)_

## Codebase Behaviour
_What was found in the codebase and docs, and how it behaves/is set up. Updated by each phase._

- Tier upgrade: implemented via `SlabUpgradeService` + `UpgradeSlabActionImpl`. _(ProductEx)_
- Tier downgrade: implemented via `SlabDowngradeService` + `DowngradeSlabActionImpl`. Multiple date-calculator strategies exist (Cyclic, Fixed, FixedCustomerRegistration, SlabUpgradeBased). _(ProductEx)_
- Tier renewal: implemented via `RenewSlabInstructionImpl`. _(ProductEx)_
- Audit logs: `/audit/logs` endpoint in `ProgramsApi`. `SlabUpgradeAuditLogService`, `SlabDowngradeAuditLogService` in place. _(ProductEx)_
- Approval/maker-checker: `PUT /v3/requests/{entityType}/{entityId}/status` in `RequestManagementController` (intouch-api-v3). Supports `EntityType` + `PromotionStatus` today. _(ProductEx)_
- `TierConfigController.class` and `BenefitConfigController.class` exist as compiled artifacts in `pointsengine-emf/target/` — NO source code found. This is a blocking risk: prior CRUD implementation may exist in an uncommitted branch. _(ProductEx)_
- `Benefits.java` entity has `promotionId` as non-nullable FK — benefits are promotion-coupled today. _(ProductEx)_
- `BenefitsType` enum: only VOUCHER and POINTS. New types require schema/enum changes. _(ProductEx)_
- `ProgramSlab` entity has no status column — the tier status lifecycle (Active/Draft/Pending/Stopped) is a new concept requiring schema work. _(ProductEx)_
- Partner program tier sync is an active feature: `PartnerProgramTierSyncConfiguration`, `RenewTierBasedOnPartnerProgramActionImpl`, `UpgradeTierBasedOnPartnerProgramActionImpl`. New tier UI must not break these. _(ProductEx)_
- Official Capillary docs (docs.capillarytech.com) returned 404 for all tier/benefit-specific pages attempted. Docs coverage for this feature area is not accessible. _(ProductEx)_

## Key Decisions
_Significant decisions and their rationale. Format: `- [decision]: [rationale] _(phase)_`_
- Scope is E1 (Tier Intelligence) + E4 (API-First Contract), backend only: user confirmed "tier-crud" means tier CRUD APIs only _(BA)_
- E2 (Benefits as Product), E3 (aiRa Config Layer) are OUT of scope: future epics _(BA)_
- aiRa integration is OUT of scope: future phase _(BA)_
- Comparison matrix UI is OUT of scope: backend APIs only, no frontend _(BA)_
- Audit/change log is OUT of scope: future scope _(BA)_
- Simulation mode is OUT of scope: future scope _(BA)_
- Maker-checker approval workflow is IN SCOPE: follow existing UnifiedPromotion maker-checker pattern in intouch-api-v3 _(BA)_
- Backend-only implementation: no Garuda/frontend work in this pipeline _(BA)_
- Tier deletion = soft delete: add `active` column (default 1) to `program_slabs`, set to 0 on delete. GET calls filter to active=1 only. _(BA)_
- Tier insertion between existing tiers: NOT relaxed — new tiers still added at top only (existing constraint kept). _(BA)_
- Stale TierConfigController.class in emf-parent/target: ignore, proceed fresh. Not prior work. _(BA)_
- Controller layer lives in intouch-api-v3 (same pattern as UnifiedPromotion): REST controllers, request/response DTOs, validation _(BA)_
- Thrift definitions + backend service logic lives in emf-parent: Thrift IDL, service implementations, DAO layer, entity persistence _(BA)_
- Architecture follows existing UnifiedPromotion pattern: intouch-api-v3 (REST) → Thrift → emf-parent (service/DAO) _(BA)_
- CRUD operations in scope: GET /tiers (list), GET /tiers/{id} (detail), POST /tiers (create), PUT/PATCH /tiers/{id} (update), DELETE /tiers/{id} (soft delete) _(BA)_
- APIs must return structured field-level validation errors (not generic 500s): future-proofing for aiRa consumption. Same validation in API as would be in UI. _(BA)_
- GET /tiers should return tier config only (no linked benefits info — benefits deferred to E2) _(BA)_
- Maker-checker IN SCOPE: tier create/update goes through approval workflow (same as UnifiedPromotion) _(BA)_
- Tier status lifecycle: DRAFT → PENDING_APPROVAL → ACTIVE → STOPPED. Rejected goes back to DRAFT. No PAUSED/LIVE/UPCOMING. _(BA)_
- Simulation and changelog endpoints: deferred _(BA)_

## Constraints
_Technical, business, and regulatory constraints all phases must respect. Format: `- [constraint] _(phase)_`_
- LSP available: using jdtls for code traversal _(Phase 0)_
- Code repos: emf-parent (multi-module Maven), intouch-api-v3 (Spring MVC REST gateway) _(Phase 0)_
- No UI screenshots provided — no UI extraction phase needed _(Phase 0)_
- BRD covers 4 epics: E1 Tier Intelligence, E2 Benefits as Product, E3 aiRa Config Layer, E4 API-First Contract _(Phase 0)_
- Feature name is "tier-crud" — suggests focus on tier CRUD operations (E1 + E4 scope) _(Phase 0)_
- KPI type is immutable per program — set on first tier, all subsequent must match _(BA)_
- Eligibility threshold must be strictly increasing up the hierarchy _(BA)_
- Base tier cannot be soft-deleted _(BA)_
- Cannot soft-delete a tier that is another active tier's downgrade target _(BA)_
- UnifiedPromotion pattern: controller in intouch-api-v3, Thrift+service in emf-parent, ResponseWrapper for all responses, TargetGroupErrorAdvice for validation errors _(BA)_

## Risks & Concerns
_Flagged risks and concerns. Format: `- [risk] _(phase)_ — Status: open/mitigated`_
- BRD has 6 open questions in Section 12 (all status: Open) — must be resolved during BA phase _(Phase 0)_ — Status: open
- `TierConfigController` and `BenefitConfigController` compiled class files found without source — user confirmed: stale artifacts, proceed fresh _(ProductEx)_ — Status: **mitigated**
- `Benefits.java` entity is promotion-coupled (non-null `promotionId`) — "Benefits as a Product" (E2) requires data model migration _(ProductEx)_ — Status: open (E2 deferred)
- Tier status lifecycle (Active/Draft/Pending/Stopped) not in current `ProgramSlab` schema — requires new columns (active + status). Flyway migration needed. _(ProductEx)_ — Status: open (in scope)
- Maker-checker not wired for tier entity type — `RequestManagementController` works for promotions only today. EntityType.TIER + routing needed. _(ProductEx)_ — Status: open (in scope)
- `BenefitsType` enum only has VOUCHER/POINTS — new types require backward-compatible schema change _(ProductEx)_ — Status: open (E2 deferred)

## Open Questions
_Unresolved questions. Format: `- [ ] [question] _(phase)_` or `- [x] resolved: answer _(phase)_`_
- [x] resolved: Scope is E1 + E4, backend only. No aiRa, no comparison matrix UI, no audit log, no simulation. _(BA)_
- [ ] Does the program context API exist or need to be built? (BRD Section 12, Q1) _(Phase 0)_ — OUT OF SCOPE (aiRa deferred)
- [ ] Is impact simulation real-time or queued? What is SLA? (BRD Section 12, Q2) _(Phase 0)_ — OUT OF SCOPE (simulation deferred)
- [ ] Maker-checker: per-user-role or per-program? Who configures approvers? (BRD Section 12, Q3) _(Phase 0)_ — IN SCOPE: follow UnifiedPromotion pattern
- [ ] Can a benefit be linked to multiple programs or scoped to one? (BRD Section 12, Q4) _(Phase 0)_ — OUT OF SCOPE (benefits deferred)
- [ ] Should aiRa handle multi-turn disambiguation? (BRD Section 12, Q5) _(Phase 0)_ — OUT OF SCOPE (aiRa deferred)
- [x] resolved: `isDowngradeOnReturnEnabled` included as-is in new tier CRUD API — backend logic already exists _(BA)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._
