# Session Memory

> Artifacts path: docs/workflow/tiers-benefits/
> Workflow started: 2026-04-01
> Ticket ID: tiers-benefits

---

## Domain Terminology
_Populated by BA from product docs and requirements. Use these terms consistently across all phases._

- **Tier / Slab**: "Tier" is the product/BRD-facing term. "Slab" is the internal codebase term (`ProgramSlab`, `Slab`, `SlabUpgradeMode`, `SlabChangeSource`). These refer to the same concept. The UI should use "tier"; backend code uses "slab". _(ProductEx)_
- **ProgramSlab**: JPA entity stored in `program_slabs` table. Fields include: id, programId, serialNumber, name, description, createdOn, metadata. Belongs to a `Program` via many-to-one. _(ProductEx)_
- **SlabUpgradeMode**: Enum controlling when upgrade evaluation runs relative to event processing: `EAGER` (before awarding), `DYNAMIC` (during), `LAZY` (after). Maps to the BRD's "upgrade schedule" concept. _(ProductEx)_
- **SlabChangeSource**: Enum tracking the cause of a tier change: `RULE, STRATEGY, GROUP_SYNC, MERGE, IMPORT, GROUP_LEAVE, PARTNER_PROGRAM, MANUAL_SLAB_ADJUSTMENT`. Used in audit trail context. _(ProductEx)_
- **Slab Instructions**: EMF processes tier transitions as instruction mnemonics: `SLAB_UPGRADE`, `SLAB_DOWNGRADE`, `SLAB_RENEWAL`. These are first-class platform operations evaluated and committed by the EMF engine. _(ProductEx)_
- **KPI (Tier)**: The eligibility metric used to evaluate tier qualification — e.g., lifetime spend, current points, transaction count. Stored as `thresholdValues` (comma-separated) in `TierConfiguration`. _(ProductEx)_
- **KPI (Dashboard)**: Program health metrics shown in the listing header — e.g., total members, renewal rate, upgrade velocity. These are analytics aggregates, not tier config fields. Not to be confused with Tier KPI. _(ProductEx)_
- **Renewal Condition**: The BRD term for the threshold a member must meet to retain their tier. Maps to "retention metrics" in code: `retentionAmount`, `retentionPoints`, `retentionTracker`, `retentionVisits` in `SlabDowngradeProfileImpl`. _(ProductEx)_
- **Benefits**: In the BRD, benefits are proposed as first-class entities. In the current platform, benefits are delivered through the V3 Promotions engine (`PromotionConfig`, `UnifiedPromotion`). `BenefitsAwardedStats` tracks what was awarded per customer. There is no standalone "benefit" entity. _(ProductEx)_
- **BenefitType**: Enum in `BenefitsAwardedStats`: `REWARDS, COUPONS, BADGES, TIER_UPGRADE, TIER_DOWNGRADE, TIER_RENEWAL, ENROL, OPTIN, PARTNER_PROGRAM, TAG_CUSTOMER, CUSTOMER_LABEL, TIER_UPGRADE_VIA_PARTNER_PROGRAM, TIER_RENEWAL_VIA_PARTNER_PROGRAM`. Note: "Free Shipping" and "Points Multiplier" (BRD terms) are not named types — they are delivery mechanics within `REWARDS` promotions. _(ProductEx)_
- **PromotionConfig**: MongoDB document (collection: moonknight) representing a promotion rule set. Statuses: `DRAFT, LIVE, SNAPSHOT`. Contains ruleset, endpoint, org/context IDs, and timing. This is the current "benefit configuration" object. _(ProductEx)_
- **UnifiedPromotion**: MongoDB document (collection: unified_promotions) introduced in late 2025. Includes approval pattern: `parentId` (points to original on edit), `version` (integer), `comments` (review comment). This is the only maker-checker pattern visible in the codebase today. _(ProductEx)_
- **Maker-Checker (Promotions)**: Implemented in `UnifiedPromotion` via parentId/version/comments pattern. When an ACTIVE promotion is edited, a new document is created with `parentId` referencing the original. **No equivalent exists for tier (slab) configuration changes.** _(ProductEx)_
- **OrgConfiguration**: Interface in EMF API layer holding org-scoped ruleset mappings, endpoint properties, and event-ruleset relationships. Multi-tenancy is enforced via orgId in composite PKs across all core entities. _(ProductEx)_
- **EMF (Event Management Framework)**: The core loyalty evaluation engine. Entry point is `EMFThriftServiceImpl`. Processes events through Evaluation Phase (rule/action evaluation → InstructionSet) and Commit Phase (instruction execution + event notification). _(ProductEx)_
- **MPL (Multi-Program Loyalty)**: Scenario where a customer is enrolled in both a primary and secondary loyalty program. EMF has special logic to prevent duplicate slab instruction execution across programs. BRD does not address MPL. _(ProductEx)_
- **intouch-api-v3**: Referenced in codebase comments and `IntouchApiService`/`IntouchApiClient`. Appears to be the primary API service that writes promotion config to MongoDB, which EMF then reads. New tier/benefit APIs may need to route through or extend this service. _(ProductEx)_

## Codebase Behaviour
_What was found in the codebase and docs, and how it behaves/is set up. Updated by each phase._

- **Tier config data model**: Tiers live in two JPA entities: `Program` (table: `program`) and `ProgramSlab` (table: `program_slabs`). `Program` holds upgrade strategy ID, upgrade mode, upgrade rule identifier, point category, and currency config. `ProgramSlab` holds per-tier data: serialNumber, name, description, metadata. _(ProductEx)_
- **Tier evaluation lifecycle**: Tiers are evaluated at event processing time (Thrift call to EMF). The EMF Evaluation Phase runs rulesets (named with prefixes `Slab_Upgrade_Rule_Start`, `Slab_Downgrade_Rule_Start`, `Slab_Renew_Rule_Start`) and generates `SLAB_UPGRADE`, `SLAB_DOWNGRADE`, or `SLAB_RENEWAL` instructions. The Commit Phase executes these instructions and triggers downstream Kafka events. _(ProductEx)_
- **Tier events are Kafka-published**: `TierUpgradeHelper` publishes `TierUpgraded` events; `TierRenewedHelper` publishes `TierRenewed` events. Downstream communications/notifications subscribe to these Kafka topics. _(ProductEx)_
- **Downgrade logic**: `SlabDowngradeService` executes downgrade on customer enrollment. `SlabDowngradeProfileImpl` carries: previous/current slab number and name, change reason, dates (slabValidUpto vs slabExpiryDate are distinguished — slabValidUpto is the strategy-configured end date, slabExpiryDate is the actual customer expiry date), retention metrics (amount/points/tracker/visits). _(ProductEx)_
- **Audit trail for tier changes**: `SlabUpgradeAuditLogService` and `SlabDowngradeAuditLogService` exist, producing `AuditTrailDiffDto` objects with per-slab threshold change data. These are customer-level slab change records — not program-level config audit logs. A program-level config change audit (who changed Gold threshold from $500 to $400 and when) does not appear to exist separately. _(ProductEx)_
- **Benefits tracking**: `BenefitsAwardedStats` entity (table: `benefits_awarded_stats`, orgId-scoped) records each benefit awarded: benefitType, benefitId, customerId, eventLogId, sourceType (ACTION), contextType (PROGRAM or PROMOTION), contextIdentifier, activityId. This is an awards ledger, not a benefit catalog. _(ProductEx)_
- **Simulation infrastructure**: `EMFThriftServiceImpl.simulateRulesBasedOnDateRange` performs synchronous rule replay over historical bills (max 5,000). This is a rule accuracy simulator, not a member distribution projector. The BRD's simulation requirement (how many members move tiers if threshold changes) requires a new analytical computation against enrollment tables. _(ProductEx)_
- **Promotion maker-checker**: `UnifiedPromotion` supports versioned drafts via `parentId` + `version`. When an ACTIVE promotion is edited, a new draft document is created (new ObjectId) with parentId pointing to the original. `comments` stores reviewer notes. No timeout logic, no approver assignment mechanism visible. _(ProductEx)_
- **Multi-tenancy**: All core entities use `orgId` as part of composite PKs (e.g., `BenefitsAwardedStatsPK extends OrgEntityLongPKBase`). Tenant isolation is enforced at the data layer. New APIs must propagate orgId correctly. _(ProductEx)_
- **No product registry exists**: `docs/product/registry.md` does not exist. This review was performed without a registry baseline. Registry should be bootstrapped after this workflow cycle. _(ProductEx)_
- **No aiRa/LLM integration in codebase**: No files referencing aiRa, LLM, intent parsing, or NLP were found. The aiRa side panel mentioned in the BRD as "production-ready" (Section 3.5) is not visible in this repository. It may live in the Garuda frontend repo or a separate service repo not present in this workspace. _(ProductEx)_

## Key Decisions
_Significant decisions and their rationale. Format: `- [decision]: [rationale] _(phase)_`_

- Scope limited to Tier CRUD + Benefit CRUD + Maker-Checker APIs (backend only): BRD covers 4 epics but this iteration focuses on the API foundation. Audit trail, simulation, aiRa, and frontend are parked. _(BA)_
- Benefits are first-class entities (new MongoDB documents), NOT a facade over V3 Promotions: cleaner data model, avoids inheriting V3 limitations. Integration with EMF evaluation is a subsequent concern. _(BA)_
- Maker-checker follows UnifiedPromotion pattern from intouch-api-v3: DRAFT → PENDING_APPROVAL → ACTIVE lifecycle, parentId versioning, distributed locking. Reference impl in UnifiedPromotionFacade.java. _(BA)_
- Maker-checker config flag defaults to true (always on), hardcoded for now: can be made DB-configurable per-program later. _(BA)_
- Authorization for maker-checker handled at UI layer, not backend: API provides mechanics (create/approve/reject) without role enforcement. _(BA)_
- MongoDB storage for tier and benefit configs: new data path alongside legacy MySQL strategy tables. No dual writes to legacy in this iteration. _(BA)_
- Benefit scoped to one program: a benefit belongs to exactly one program, cannot be shared across programs. _(BA)_
- "Validate downgrade on return transaction" toggle included: surfaced as a boolean field on tier downgrade config, not deprecated. _(BA)_
- All tier config fields from BRD in scope: eligibility, validity, renewal, downgrade, upgrade mode/bonus, nudge/communication, color, etc. _(BA)_
- API uses "tier" terminology externally, "slab" internally where interfacing with existing EMF components. _(BA)_
- Tier and benefit APIs built in emf-parent (kalpavriksha repo), not intouch-api-v3. _(BA)_

## Constraints
_Technical, business, and regulatory constraints all phases must respect. Format: `- [constraint] _(phase)_`_

- LSP unavailable: using grep/file reads for code traversal _(workflow)_
- No product registry exists (docs/product/registry.md absent) — ProductEx analysis is based entirely on codebase inspection _(ProductEx)_
- docs.capillarytech.com was not accessible (WebFetch blocked) — official documentation could not be cross-referenced _(ProductEx)_
- All new REST APIs must enforce orgId-scoped multi-tenancy consistent with existing composite PK pattern _(ProductEx)_
- EMF evaluation pipeline is Thrift-based; new REST APIs must not create dual write paths that bypass or conflict with the existing evaluation contract _(ProductEx)_
- intouch-api-v3 appears to be the authority for writing promotion/benefit config to MongoDB; new benefit APIs should clarify their relationship to this service _(ProductEx)_

## Risks & Concerns
_Flagged risks and concerns. Format: `- [risk] _(phase)_ — Status: open/mitigated`_

- **Benefits-as-Product entity model conflict**: Creating a first-class benefit entity that exists alongside V3 Promotions creates dual maintenance risk and potential for orphaned benefit configs in the old promotions store. _(ProductEx)_ — Status: open
- **Tier config write path unclear**: No REST API for writing to `program_slabs` or strategy tables is visible. If new APIs bypass intouch-api-v3, the EMF evaluation pipeline may not pick up changes correctly. _(ProductEx)_ — Status: open
- **Program context API is net-new**: The aiRa Context Layer API does not exist. It is also the hardest API to build (requires cross-store data aggregation). If this is treated as a simple task, E3 (aiRa) will be perpetually blocked. _(ProductEx)_ — Status: open
- **Validate-downgrade-on-return-transaction deprecation**: Removing this toggle without a migration plan could silently break programs that rely on the behaviour. _(ProductEx)_ — Status: open
- **MPL (Multi-Program Loyalty) not addressed in BRD**: EMF has active MPL handling. Changes to the tier config API must not break MPL de-duplication logic. _(ProductEx)_ — Status: open

## Open Questions
_Unresolved questions. Format: `- [ ] [question] _(phase)_` or `- [x] resolved: answer _(phase)_`_

- [x] resolved: Program context API parked — aiRa not in scope for this iteration _(BA)_
- [x] resolved: Benefits are first-class entities (new standalone MongoDB documents), not a facade over V3 Promotions _(BA)_
- [x] resolved: Interface philosophy not relevant — backend only, no frontend in this iteration _(BA)_
- [x] resolved: Pending tier changes use MongoDB documents with UnifiedPromotion-style parentId/version pattern. Tier config writes owned by emf-parent. _(BA)_
- [ ] How is orgId threaded through and validated in the new REST APIs? Existing pattern uses composite PKs. New APIs need to extract from JWT/header. _(BA)_ — owner: Architect
- [x] resolved: Benefit scoped to one program only. A program can have multiple benefits. _(BA)_
- [x] resolved: Maker-checker auth at UI layer. Config flag at program level, defaults true. _(BA)_
- [x] resolved: Simulation parked for this iteration _(BA)_
- [x] resolved: aiRa parked for this iteration _(BA)_
- [x] resolved: "Validate downgrade on return transaction" toggle included as a boolean field, not deprecated _(BA)_
- [ ] What happens to members in a tier when it is STOPPED? Retain until next evaluation or immediate downgrade? _(BA)_
- [ ] Upgrade bonus — is it a numeric points field or a reference to a benefit entity? Modelled as numeric for now. _(BA)_
- [ ] Nudge/communication config — exact field structure needs product team clarification before Architect designs schema. _(BA)_
- [ ] How does new MongoDB tier config sync with legacy MySQL strategy tables consumed by EMF? Critical for subsequent iteration. _(BA)_
- [ ] Member distribution data lives in customer_enrollment + program_slabs. DB constraints/indexes in cc-stack-crm. Relevant for future simulation feature. _(BA)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops. Format: `- [Phase N] cycle [N]/2 — raised by [Phase X] — severity: trivial|critical — issue: [brief] — resolved: yes|no`_
