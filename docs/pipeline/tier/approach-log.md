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
| D-09 | Tier deletion strategy | (a) Soft-delete with status (b) Hide from UI only (c) True delete | ~~(a) Soft-delete with status column on program_slabs~~ **SUPERSEDED (Rework #3)**: DRAFT-only deletion in MongoDB (set DELETED). No SQL status column — SQL only has ACTIVE tiers. | ~~Enables tier lifecycle (DRAFT/ACTIVE/STOPPED).~~ MongoDB owns lifecycle. SQL unaffected. |
| D-10 | Data storage for tier config | (a) Aggregate from existing (b) Normalize new tables (c) Hybrid | Dual-storage: MongoDB draft + SQL live (same as unified promotions) | Follows existing UnifiedPromotion pattern. MongoDB for draft/pending, SQL for engine-readable entities. Thrift sync on approval. |
| D-11 | Member counts in listing | (a) Include live (b) Exclude (c) Include cached | (c) Cached counts, included in response | customer_enrollment is hot table, no existing count-by-slab query. 5-15 min refresh sufficient for UI. |
| D-12 | Approval framework design | (a) Full generic framework (b) Tier-specific with extension points | (a) Full generic framework | Layer 1 shared module. ApprovalRecord entity, MakerCheckerService interface, ApprovableEntityHandler strategy. Tiers first consumer. |
| D-13 | Tier editing approach | (a) Versioned edits (b) In-place with MC (c) Hybrid by field type | (a) Versioned edits with parentId (same as unified promotions) | Full rollback capability. Consistent with existing codebase pattern. ACTIVE stays live until new version approved. |
| D-14 | API hosting | intouch-api-v3 vs emf-parent vs other | intouch-api-v3 (REST + MongoDB) -> Thrift -> emf-parent (SQL) | Same architecture as unified promotions. intouch-api-v3 has MongoDB access and existing approval patterns. |
| D-15 | MC toggle granularity | (a) Per-program (b) Per-program + per-entity-type (c) Per-program + per-role | (b) Per-program + per-entity-type | Generic framework needs entity-type granularity. Different entities may have different risk profiles. |

## Decisions Made During Phase 4 (Blocker Resolution)
| # | Question | Options Presented | Chosen | Reasoning |
|---|----------|-------------------|--------|-----------|
| D-16 | BLOCKER: Thrift sync method missing | (a) New Thrift method (b) Direct DB (c) REST (d) Shared lib | (a) Use existing createSlabAndUpdateStrategies | Thrift methods already exist in pointsengine_rules.thrift. Just add wrapper methods. No IDL change needed. |
| D-17 | PartnerProgramSlab cascade on deletion | (a) Block (b) Cascade (c) Warn (d) Defer | (d) Defer | Not applicable for DRAFT-only deletion (DRAFTs have no SQL record). Deferred to future tier retirement epic. |
| D-18 | PeProgramSlabDao impact | No changes needed | ~~Expand-then-contract.~~ **SUPERSEDED (Rework #3)**: No SQL changes. SQL only has ACTIVE tiers. No findActiveByProgram(). No Flyway migration. | Risk eliminated entirely — no emf-parent entity/DAO changes. |
| D-19 | Tier Duration field | (a) Add to MongoDB (b) Derive from strategy (c) Defer | (a) Add startDate/endDate to MongoDB doc | UI requires it. Maps to membership validity period. |
| D-20 | isDowngradeOnReturnEnabled | (a) Preserve hidden (b) Surface (c) Deprecate | (a) Preserve hidden, pass through | Existing toggle. Product decision to surface/deprecate is out of scope. |
| D-21 | Notification templates | (a) Store both (b) Detail only (c) Text only | (a) Store both nudges text + notificationConfig | UI needs text. Engine needs config. Coexist independently. |
| D-22 | Pagination | No pagination. Max 50 cap. | Accepted | Programs have 3-7 tiers. Pagination is overhead. |
| D-23 | Bootstrap sync for existing programs | (a) Auto-bootstrap (b) New programs only | (b) New programs only (user override) | No migration. Old programs keep current system. |
| D-24 | Edit flow (ACTIVE stays live?) | Flow A (ACTIVE stays live) vs Flow B (ACTIVE -> SNAPSHOT immediately) | Flow A (ACTIVE stays live until approval) | Zero downtime. Same as unified promotions. Live traffic always served. |
| D-25 | Benefits in listing | (a) Summary (b) Full config (c) IDs only | (c) benefitIds only (user override) | Keeps tier API decoupled from benefits. UI fetches separately. |
| D-26 | Approval notification | Hook interface only (NotificationHandler) | Accepted | Keeps framework focused. Real notifications are separate concern. |
| D-27 | ApprovalRecord format | (a) Full snapshot (b) Diff | (a) Full snapshot | Simpler. Approver sees full state. TierApprovalHandler needs full config. |
| D-28 | "Scheduled" KPI | (a) Replace with "Pending Approval" (b) Add goLiveDate (c) Return 0 | (a) Replace with pendingApprovalTiers | No scheduled concept for tiers. Pending Approval is meaningful. |
| D-29 | Member count cache | Cron every 10 min | Accepted | Predictable load. GROUP BY query on customer_enrollment. |

## Decisions Made During Rework #8 (Validation Catalog Mirror)
| # | Question | Options Presented | Chosen | Reasoning |
|---|----------|-------------------|--------|-----------|
| D-30 | REQ-58 (color length code 9027) | (a) Skip — defensive duplicate of `@Pattern` (b) Add — distinct error for "wrong length" vs "wrong format" | (a) Skip | Auto-defaulted at C5+. `@Pattern("^#[0-9A-Fa-f]{6}$")` already enforces exactly 7 chars. Code 9027 reserved as documented gap; reversible — additive if UX needs it later. |
| D-31 | REQ-63 (renewalLastMonths code 9031) | (a) Add new wire field (b) Fold into REQ-62 (c) Defer | (b) Fold into REQ-62 (code 9034) | Auto-defaulted at C6+. Designer evidence: zero hits for `renewalLastMonths` across `intouch-api-v3` source; semantic equivalent is `computationWindowStartValue` when `renewalWindowType == FIXED_DATE_BASED`. Reversible — additive if product disagrees. |
| D-32 | Dynamic-context messages in errors | (a) Option 2 — static catalog message + log context (b) Option 3 — MessageFormat placeholders | (a) Option 2 | Auto-defaulted at C5+. Plan default; mirrors promotion exactly. Reversible — Option 3 is an additive engineering follow-up. Trade-off: cleaner i18n catalog vs. less rich client errors (field-name detail still in server logs). |
| D-33 | BT-247 catalog-integrity test (loads `tier.properties`, asserts every `TierErrorKeys` constant has both `.code` and `.message`) | (a) Implement now (Phase 9) (b) Defer to hardening sprint | (a) Implement now | Auto-defaulted at C6+. Plan §10 strongly recommends — it's the safety net against `999999L` regressions when keys drift from properties. |
| D-34 | REQ-57 case-insensitive uniqueness — pre-deploy DB scan | (a) Run scan in QA env / read-only prod (b) Skip — accept low-probability risk | **(b) Skip — ACCEPTED RISK** | User-decided. Risk: if two existing draft tiers in production differ only by case, the next update operation on either of them will fail with `code 9025`. One-shot data hazard. Logged here as accepted. Mitigation if it surfaces: rename one of the colliding drafts via direct DB update or via a one-off support task. |

## Decisions Made During Phase 11 (Reviewer Findings) and Follow-Up Work
| # | Question | Options Presented | Chosen | Reasoning |
|---|----------|-------------------|--------|-----------|
| D-35 | Cross-tier consistency — scope and trigger | (a) preApprove only (b) draft-time create+update (c) both (d) submit-only | **(c) Both** — Scenario B + Trigger C | User-decided: lightweight but working. Two rules in scope: (1) condition `type` ↔ program `currentValueType` compatibility (code 9043 `TIER.PROGRAM_KPI_TYPE_MISMATCH`), (2) threshold monotonicity (code 9044 `TIER.THRESHOLD_NOT_MONOTONIC`). VISITS condition allowed cross-criterion. periodType compat + first-tier bootstrap deferred. New `TierProgramConsistencyValidator` wired into `TierFacade.createTier` (after `assignNextSerialNumber`), `TierFacade.updateTier`, and `TierApprovalHandler.preApprove`. 12 unit tests added. |
| D-36 | Phase 11 BLOCKER-1 — `TierFacade.handleApproval:473` `IllegalArgumentException` for unknown action | (R) Re-run, fix (M) Manual (A) Accept | **(R) Fix** | User-decided. New key `TIER.UNKNOWN_APPROVAL_ACTION = 9041`. Replaced with `InvalidInputException(key)` + `log.warn` carrying the action. G-13.1 violation fixed; HTTP 500 → HTTP 400 with structured code. |
| D-37 | Phase 11 BLOCKER-2 — `validateEndDateNotBeforeStartDate` dynamic-string throw | (R) Re-run, fix (M) Manual (A) Accept | **(R) Fix** | User-decided. New key `TIER.END_DATE_BEFORE_START_DATE = 9042`. Replaced with key-based throw + `log.warn` carrying the dates. D-32 Option 2 pattern restored; client now sees code 9042 instead of 999999. |
| D-38 | Phase 11 WARN-1 — dead `int` constants in `TierCreateRequestValidator` (33–53) and `TierEnumValidation` (243–256) | (R) Remove (A) Accept | **(R) Remove** | User-decided. 19+14 = 33 dead `public static final int TIER_*` constants deleted after grep-confirming zero external references. Eliminates two-pattern coexistence risk for future devs. |
| D-39 | Phase 11 WARN-2 — ghost entries 9027/9031 in `tier.properties` + `TierErrorKeys` despite D-30/D-31 SKIPPED/FOLDED | (R) Remove cleanly (A) Annotate | **(R) Remove cleanly + tombstone comment** | User-decided ("correct the document also"). Removed `.code` + `.message` + constants for 9027 and 9031. Replaced with one-line tombstone comments at the location: `// 9027 — removed (D-30: REQ-58 @Pattern already enforces 7-char invariant)` and similar for 9031. Tombstones prevent silent number-gap confusion without reactivating the keys. |
| D-40 | Phase 11 WARN-3 — plain-text `ConflictException` throws in `TierFacade.submitForApproval:438` and `handleApproval:462` | (R) Migrate to keys (A) Accept 999999 | **(R) Migrate** | User-decided ("correct the 999999 codes"). New keys `TIER.SUBMIT_REQUIRES_DRAFT_STATUS = 9045` and `TIER.APPROVE_REQUIRES_PENDING_STATUS = 9046`. Status-transition errors now emit real codes; client can branch on numeric code. |
| D-41 | Phase 11 WARN-4 — `IllegalStateException` in `TierApprovalHandler.publish:248,254` for missing strategies | (R) Migrate (A) Accept | **(A) Accept — KEEP AS-IS** | User-decided ("this we can keep ot"). Configuration-failure path; rare; HTTP 500 acceptable. Could be revisited if a "first-tier-in-new-program" UX requirement emerges. |
