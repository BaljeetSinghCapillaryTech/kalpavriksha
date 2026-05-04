# Critic Review -- Contradictions & Challenges

> Phase 2a: Devil's Advocate review of 00-ba.md and 00-prd.md
> Date: 2026-04-11

---

## Contradiction C-1: Thrift method for tier sync may not exist (BLOCKER)

**Source**: BA Assumption 3, PRD Architecture
**Claim**: "intouch-api-v3 -> Thrift -> emf-parent PointsEngineRuleService.createSlabAndUpdateStrategies()"
**Challenge**: The EMF Thrift service (`emf.thrift`) was searched for slab/tier/config methods. **ZERO relevant methods were found.** The Thrift `EMFService` has methods like `checkOrganizationConfiguration` but NO `createSlab`, `updateSlab`, `configureTier`, or anything that maps to `createSlabAndUpdateStrategies`.

This means `createSlabAndUpdateStrategies` is an **internal** method within emf-parent, NOT exposed via Thrift. The BA's assumption that intouch-api-v3 can call this method via Thrift is **UNVERIFIED (C2)**.

**Evidence**: `grep -n "createSlab\|addSlab\|updateSlab\|configureSlab\|saveSlab\|tierConfig\|slabConfig" emf.thrift` returned zero results. Only `checkOrganizationConfiguration` matched tier-adjacent patterns.

**Impact**: If no Thrift method exists for tier config sync, the entire approval flow (MongoDB -> SQL via Thrift) needs either:
- (a) A NEW Thrift method added to emf.thrift (requires Thrift IDL change + code generation)
- (b) A direct JDBC/JPA call from intouch-api-v3 to emf-parent's database (breaks service boundaries)
- (c) A REST-to-REST call instead of Thrift (different from the promotion pattern)

**Recommendation**: Resolve before Phase 6 (HLD). This is a BLOCKER for architecture.

---

## Contradiction C-2: PartnerProgramSlab impact not addressed

**Source**: BA Scope, PRD Data Model
**Claim**: BA focuses on `ProgramSlab` entity and proposes adding a status column to `program_slabs` table.
**Challenge**: The codebase also has `PartnerProgramSlab` (table: `partner_program_slabs`) which maps partner program tiers to loyalty program tiers. The BA mentions it in Domain Terminology but the PRD has **no user story or acceptance criterion** addressing what happens to partner program slabs when a program slab's status changes.

**Evidence**: `PartnerProgramSlab` has `loyaltyProgramId` and `partnerProgramId` fields, and is used by `PePartnerProgramSlabDao` and `PointsEngineRuleService`.

**Impact**: ~~Stopping a ProgramSlab could break PartnerProgramSlab references.~~ **REDUCED (Rework #2)**: Only DRAFT tiers can be deleted, and DRAFT tiers have no SQL record yet — so they cannot have PartnerProgramSlab references. This concern now only applies to future tier retirement (out of scope). For creation (US-2), new tiers start as DRAFT and won't have partner slab mappings until approved and synced to SQL.

**Recommendation**: ~~Add acceptance criterion to US-4.~~ **Updated**: No action needed for current scope. Document as a concern for future tier retirement epic. PartnerProgramSlab validation will be needed when ACTIVE tier stopping is implemented.

---

## ~~Contradiction C-3: PeProgramSlabDao usage is widespread -- "all queries need status filter" is high risk~~ — RESOLVED (Rework #3: Entire concern eliminated)

**Source**: BA Decision KD-02
**Claim**: "All existing slab queries must be updated to filter by status"
**Challenge**: `PeProgramSlabDao` is used in **7+ service classes** across emf-parent.

**Resolution (Rework #3)**: This contradiction is now moot. No SQL changes are needed:
- SQL `program_slabs` only contains ACTIVE tiers (synced via Thrift on approval)
- No ACTIVE tier can be deleted (DRAFT-only deletion in MongoDB)
- SlabInfo Thrift has no status field
- Therefore: no status column, no findActiveByProgram(), no Flyway migration, no blast radius
- PeProgramSlabDao is completely untouched. Zero regression risk.

~~**Recommendation**: Consider the expand-then-contract approach...~~
**Recommendation**: No action needed. Deferred to future tier retirement epic (when ACTIVE tiers may need stopping/archival).

---

## Contradiction C-4: "Threshold > previous tier's threshold" validation may be too simplistic

**Source**: PRD E1-US2 AC-4
**Claim**: "Validates: threshold > previous tier's threshold"
**Challenge**: Thresholds in `ThresholdBasedSlabUpgradeStrategyImpl` are stored as a CSV string (`threshold_values`) -- a comma-separated list of values per slab. The threshold is NOT stored per ProgramSlab but in the strategy config. Also, eligibility can involve tracker-based criteria with AND/OR conditions, not just a single numeric threshold.

**Evidence**: `this.propertiesMap.get("threshold_values")` -> CSV split -> per-slab thresholds. This is a STRATEGY-level property, not a slab-level property.

**Impact**: The validation "threshold > previous tier" assumes a simple numeric comparison, but the actual system supports complex criteria (purchase AND visits, tracker-based conditions). The validation logic will be more nuanced.

**Recommendation**: Reframe AC-4 as: "Validates that the tier's eligibility configuration is consistent with the program's tier hierarchy (e.g., higher tiers require higher thresholds)." Exact validation rules to be determined in Phase 6 (HLD).

---

## Contradiction C-5: "Scheduled" KPI has no backing concept

**Source**: PRD E1-US1 AC-7
**Claim**: "Response includes KPI summary: totalTiers, activeTiers, scheduledTiers, totalMembers"
**Challenge**: The PRD defines tier statuses as DRAFT, PENDING_APPROVAL, ACTIVE, DELETED, SNAPSHOT (Rework #2 removed PAUSED and STOPPED). None of these is "Scheduled." The UI prototype shows "Scheduled: 0" in the KPI cards, but the BA/PRD do not define when a tier is "scheduled" vs "draft."

**Evidence**: The PromotionStatus enum has UPCOMING as a derived status ("State for UI: [ACTIVE] -> [LIVE, UPCOMING, COMPLETED]"). For tiers, there's no concept of "start date" that would make a tier "scheduled."

**Impact**: Either drop "Scheduled" from the KPI summary, or define what it means for tiers (e.g., a PENDING_APPROVAL tier is "scheduled" to go live).

**Recommendation**: Replace "scheduledTiers" with "pendingApprovalTiers" in the KPI summary, or define a start date concept for tiers.

---

## Contradiction C-6: MC framework scope may conflict with registry decomposition

**Source**: BA Decision KD-05, Registry epic-assignment.json
**Claim**: BA says "build full generic maker-checker framework as Layer 1 shared module."
**Challenge**: The registry's `epic-assignment.json` assigns Ritwik TWO epics: `maker-checker` (Layer 1) AND `tier-category` (Layer 2). These are treated as SEPARATE epics with separate pipeline runs. This pipeline run is for "Tiers CRUD" (mapped to `tier-category`). Building the full MC framework in this pipeline run effectively merges two epics into one.

**Evidence**: `"developer": "ritwik", "epics": ["maker-checker", "tier-category"]`

**Impact**: Not necessarily wrong (same developer owns both), but it means this pipeline run is larger than a single epic. The MC framework should ideally have its own BA/PRD/tests, not be a sub-section of the tier CRUD pipeline.

**Recommendation**: Acceptable to build both in one pipeline run since the same developer owns both, but track MC framework and Tier CRUD as separate deliverables within this run. Ensure tests for MC framework are entity-agnostic (not tier-specific).

---

## Summary

| # | Severity | Contradiction | Status |
|---|----------|--------------|--------|
| C-1 | BLOCKER | Thrift method for tier sync may not exist | Open -- needs resolution |
| C-2 | ~~HIGH~~ LOW | PartnerProgramSlab impact — reduced (DRAFT-only deletion, no SQL refs) | Deferred to future tier retirement epic |
| C-3 | HIGH | PeProgramSlabDao blast radius understated | Open -- needs migration strategy |
| C-4 | MEDIUM | Threshold validation oversimplified | Open -- refine in HLD |
| C-5 | LOW | "Scheduled" KPI undefined | Open -- clarify naming |
| C-6 | LOW | MC framework scope vs registry decomposition | Accepted -- same developer |

---

## Rework Delta — Cycle 6a Critic Review (2026-04-22)

**Trigger**: Cascade from Phase 1 BA rework
**Reviewed REQs**: 18 (7 UPDATE + 11 NEW) + 1 OBSOLETE closure
**Model**: opus

### Existing Contradictions Triage

| # | Prior Claim | Status | Rationale |
|---|---|---|---|
| C-1 | Thrift `createSlabAndUpdateStrategies` not exposed | OPEN (unchanged) | Not touched by 6a (Q13 says no engine / no Thrift IDL change). The concern predates 6a. 6a assumes the Thrift call path already resolves — Q15 note says `createSlabAndUpdateStrategies` is "reused" for advanced-settings writes, implying it already works for intouch-api-v3 → emf-parent, which contradicts C-1's premise. **Q15 vs C-1 is itself a contradiction.** This should be either hard-closed with code evidence or kept OPEN — do not leave silently reconciled. |
| C-2 | PartnerProgramSlab impact | OPEN (unchanged) | 6a is wire-only, does not touch PartnerProgramSlab. Remains deferred to tier-retirement epic. |
| C-3 | PeProgramSlabDao blast radius | OPEN (unchanged) | 6a is wire-only, Rework #3 already resolved the SQL status-column question. Still open per prior triage. |
| C-4 | Threshold validation oversimplified | OPEN (unchanged) | 6a narrows `eligibility.threshold` to per-tier but does not define validation. Q20/Q24 split makes this *more* relevant, not less — see C-8 (NEW) below. |
| C-5 | "Scheduled" KPI undefined | UPDATED | REQ-11 still lists "scheduled tiers" in KPI header. 6a envelope adds `status` discriminator (`LIVE | PENDING_APPROVAL | DRAFT`) — none map to "scheduled". Still unresolved; Critic re-flags. |
| C-6 | MC framework vs registry decomp | OPEN (unchanged) | Not affected by 6a. |

### New Contradictions (from Rework Delta)

- **C-7 (NEW)**: Q-locks referenced but never defined in session-memory (Q18, Q19, Q21)
  - **Source**: `rework_6a_q_lock_coverage` (YAML in 00-ba-machine.md), BA `Scope` bullet list, Q24 supersession note
  - **Claim**: The BA cites Q18 as the basis for REQ-34 (Class B rejection), Q19 as the basis for "remove compound group-condition support from the wire entirely" (in Q14 6a scope line 437), and Q21 as "subsumed by Q24". The machine YAML lists Q-lock coverage for Q18, but no Q21.
  - **Challenge**: `grep` over `session-memory.md` finds no `**Q18 locked**`, no `**Q19 locked**`, no `**Q21 locked**` block. Only Q1, Q2, Q3, Q4, Q5c, Q7, Q8, Q9, Q10a, Q10b, Q10c, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q20, Q22, Q23, Q24, Q25, Q26 are explicitly locked with C-level + evidence. Q18/Q19/Q21 appear as orphan citations. A downstream agent (Designer, QA) cannot audit what Q18 actually decided — the lock is a phantom. Q19's description ("compound group-condition support") is especially dangerous: no REQ covers it, no AC rejects it, and yet the 6a scope claims it is being removed. Either Q19 is dead and the scope line is stale, or Q19 decided something real and the BA silently under-delivered.
  - **Evidence needed**: Session-memory Q18/Q19/Q21 lock text with C-level. If missing, either add the locks or remove the citations.
  - **Confidence assessment**: Implied by BA at C5 (treated as canonical). Actually backed by C1 (citation without a locked decision).
  - **Severity**: BLOCKER
  - **Recommendation**: Escalate to Phase 4 blocker resolution. Fix session-memory or rescind REQ-34 / "compound group" scope claim.

- **C-8 (NEW)**: `validity.periodType` / `validity.periodValue` are both per-tier write fields AND program-level read-wide hoist fields — contract asymmetry collapses
  - **Source**: REQ-20 (read-wide hoist), REQ-26 (write accepts), REQ-49 (PUT accepts)
  - **Claim**: REQ-20 lists `validity.periodType` and `validity.periodValue` as program-level fields hoisted read-wide onto the flattened envelope. REQ-26 / REQ-49 accept `validity.periodType` and `validity.periodValue` on per-tier POST/PUT. Q20 classifies `validity` shape as program-level. Q24 says program-level fields are rejected on per-tier write with 400.
  - **Challenge**: This is the exact Rework #5 schedule-asymmetry bug re-created. If `validity.periodType` is program-level per Q20, it MUST appear in REQ-34's Class B reject list — it does not. If it is per-tier, it MUST NOT be in REQ-20's read-wide hoist — it is. One of Q20, REQ-26, or REQ-34 is wrong. The machine YAML says Q10c keeps per-tier `renewal.*` per-tier — but `validity.*` is neither `renewal.*` nor Class B eligibility. The storage classification note in Q20 is silent on `validity`. A skeptic says: "You replaced the `downgrade` asymmetry with a `validity` asymmetry."
  - **Evidence needed**: (a) Is `TierDowngradePeriodConfig.periodType` per-tier or program-level in the engine? (b) Does Q10b's advanced-settings payload (deferred to 6b) include `validity.periodType`? If yes → reject on per-tier write. If no → keep per-tier write, drop from REQ-20 hoist.
  - **Confidence assessment**: BA implies this contract at C5. Actual consistency is C3 at best — a code-verification check would likely overturn one of the three REQs.
  - **Severity**: BLOCKER
  - **Recommendation**: Resolve before Designer. Either add `validity.periodType`/`periodValue` to REQ-34 reject list, or drop them from REQ-20 hoist. Pick one.

- **C-9 (NEW) — RESOLVED Phase 4 Q-OP-1 (2026-04-22)**: Error-code range 9001-9010 is ten slots, but REQ-40 says 9001-9009 is "pre-existing Rework #4 reject range" — leaving ONE slot for SEVEN new rejects (REQ-27/33/34/35/36/37/38)
  - **Source**: REQ-40, machine YAML `rework_6a_error_codes` (line 243-252), BA §Scope
  - **Claim**: REQ-40 text: "Error codes 9001-9010 cover the Q-lock rejects (REQ-33..REQ-38, REQ-27); 9001-9009 cover the pre-existing Rework #4 reject range." Machine YAML says range is "9001-9010 (extended from Rework #4's 9001-9009 by one slot; reuses same range for new rejects)."
  - **Challenge**: Either (a) new rejects share error codes with pre-existing ones (same code, different meaning — a silent contract break for existing API consumers parsing error codes), or (b) 6a needs codes 9010 through 9017 (one per new reject: REQ-27, REQ-33, REQ-34, REQ-35, REQ-36, REQ-37, REQ-38) but only 9010 is allocated. The YAML phrase "reuses same range for new rejects" explicitly says the same code is reused — which means a client that was programmed to handle error code 9003 from Rework #4 will now receive 9003 with an entirely different field-level meaning from 6a. This is the exact "silent contract break" that Q11 hard-flip tried to prevent.
  - **Evidence needed**: Phase 4 needs to allocate distinct codes per reject. Or document which specific Rework #4 codes are safe to reuse.
  - **Confidence assessment**: BA implies C5 (codes are a small, settled detail). Actually C3 — the YAML language is ambiguous and the math doesn't work.
  - **Severity**: HIGH
  - **Recommendation**: Revise REQ-40 to allocate one code per new reject (9010..9016 minimum). Designer and QA will need per-code test cases.
  - **Resolution (Phase 4 Q-OP-1 — Option (b) Allocate 9011-9020)**: Rework #6a rebanded to **9011-9020**. Legacy 9001-9010 preserved for Rework #4 validator (no silent contract break). Per-REQ allocations: 9011 REQ-33, 9012 REQ-34, 9013 REQ-27, 9014 REQ-37, 9015 REQ-35, 9016 REQ-36, 9017 REQ-38; 9018-9020 reserved. REQ-40 rewritten with full banding block. All downstream artifacts (00-ba.md, 00-ba-machine.md, 00-prd.md, 00-prd-machine.md) cascaded. Evidence base: `TierUpdateRequestValidator.java` javadoc confirms 9001-9010 is pre-existing Rework #4 range; no overlap with new band.

- **C-10 (NEW)**: REQ-19 (GET filter) and REQ-35 (POST reject) both specify **string** `"-1"` match — numeric `-1` is a silent gap
  - **Source**: REQ-19, REQ-35
  - **Challenge**: Both REQs say "`value == "-1"` (string-match, not numeric)". The engine sentinel is `BigDecimal.valueOf(-1)` per Q9 commentary — a numeric value. If the wire serializes the condition value as a JSON number (not quoted string), REQ-19/REQ-35 MISS IT — filter doesn't fire, reject doesn't fire, dead-wire sentinel bleeds through. A skeptic says: "You picked string-match to match the Java-side string condition field, but if the wire schema ever carries it as a number, your defence is paper." What does the current `TierStrategyTransformer.extractConditions` at lines 819-847 actually produce — string or number? BA claims to know (the Q9 note references that file) but neither REQ pins the wire type to a schema.
  - **Evidence needed**: Schema of `eligibility.conditions[].value` and `renewal.conditions[].value` on the wire — string or number? Is Jackson configured to coerce `-1` (number) to `"-1"` (string) during deserialization?
  - **Confidence assessment**: BA implies C6 (direct read of the file). Actually C4 — BA hasn't named the wire type or the Jackson config.
  - **Severity**: HIGH
  - **Recommendation**: Designer must pin down the wire type. If it could ever be numeric, upgrade REQ-19/REQ-35 to match both string and numeric `-1`.

- **C-11 (NEW)**: Legacy `downgrade` field "400 unknown field" rejection assumes Jackson `FAIL_ON_UNKNOWN_PROPERTIES=true` — not verified
  - **Source**: REQ-27, REQ-49 (Q11 hard flip)
  - **Challenge**: Spring Boot's default Jackson config is `FAIL_ON_UNKNOWN_PROPERTIES=false`. If the tier controller DTOs don't explicitly enable it (via `@JsonIgnoreProperties(ignoreUnknown=false)` or the Jackson feature), sending `{"downgrade": {...}}` in the POST body will be **silently ignored**, not rejected. The BA treats "rejected 400" as a given. A skeptic says: "Q11 calls itself a hard flip but it's a soft flip unless the deserializer is configured to reject." The Q11 mitigation is described as "grepping src/test for JSON-body literal 'downgrade'" — that verifies NO existing test sends it, not that a NEW request carrying it will 400.
  - **Evidence needed**: Check the tier wire DTO annotations and the global Jackson `ObjectMapper` config in intouch-api-v3. If `FAIL_ON_UNKNOWN_PROPERTIES=false`, REQ-27/REQ-49 need an explicit validator that scans for `downgrade` (or any `*unknown*` field), not just reliance on deserializer failure.
  - **Confidence assessment**: BA implies C5. Actually C3 — no config evidence cited.
  - **Severity**: HIGH
  - **Recommendation**: Designer must specify the rejection mechanism explicitly. If deserializer-based, verify config. If validator-based, add a named validator.

- **C-12 (NEW) — PARTIALLY RESOLVED Phase 4 Q-OP-2 (2026-04-22)**: REQ-21 / REQ-22 / REQ-36 silently exclude two of four `PeriodType` enum values
  - **Source**: REQ-21, REQ-22, REQ-36; Q16 cites four PeriodType values
  - **Challenge**: Q16 explicitly names the engine enum: `FIXED | SLAB_UPGRADE | SLAB_UPGRADE_CYCLIC | FIXED_CUSTOMER_REGISTRATION`. REQ-21 covers only `SLAB_UPGRADE` (drop `validity.startDate`); REQ-22 covers only `FIXED` (compute end-date). What happens for `SLAB_UPGRADE_CYCLIC` and `FIXED_CUSTOMER_REGISTRATION`? Silent passthrough? Is `validity.startDate` returned on wire for those? Is it rejected on write? REQ-36 says "SLAB_UPGRADE-type tiers" — and nothing about the cyclic variant. A downstream QA engineer has no test cases for those two enum values.
  - **Evidence needed**: (a) Are `SLAB_UPGRADE_CYCLIC` and `FIXED_CUSTOMER_REGISTRATION` in scope for v3? (b) If yes, what is the expected wire behaviour? (c) If no, the REQ texts should explicitly reject those enum values.
  - **Confidence assessment**: BA implies C5 by omission. Actually C2 — no coverage statement.
  - **Severity**: HIGH
  - **Recommendation**: Clarify scope with product. If all four are in scope, REQ-21/22/36 need per-enum behaviour. If only two, the other two must be explicit rejects.
  - **Resolution (Phase 4 Q-OP-2 — Option (c) Scope lock with duration caveat)**: 6a handles `SLAB_UPGRADE` explicitly (REQ-21 drop + REQ-36 startDate reject); `FIXED_CUSTOMER_REGISTRATION`, `FIXED_LAST_UPGRADE`, and `SLAB_UPGRADE_CYCLIC` are pass-through from Rework #5 behaviour (no new explicit wire-level handling). **User-added caveat**: `validity.periodValue` is REQUIRED when `validity.periodType` is FIXED-family; captured as REQ-56 with error code 9018. REQ-22 amended to be null-safe for legacy tiers. The enum-scope silent gap is explicitly scoped OUT of 6a (documented in 00-ba.md §Phase 4 Blocker Resolutions); the duration-required-for-FIXED constraint prevents new FIXED tiers from being saved without durations going forward. **Remaining**: per-enum wire behaviour for `SLAB_UPGRADE_CYCLIC` / `FIXED_CUSTOMER_REGISTRATION` / `FIXED_LAST_UPGRADE` reads still undocumented — deferred to future rework. Partial resolution by design; Designer + QA will surface any actual code-path blockers in Phase 7/8.

- **C-13 (NEW)**: REQ-38 cites `TierRenewalNormalizer` auto-fill as mechanism — no evidence the normalizer exists
  - **Source**: REQ-38
  - **Claim**: "Null or omitted `renewal` is auto-filled to the B1a default by `TierRenewalNormalizer` before persistence."
  - **Challenge**: No evidence cited that `TierRenewalNormalizer` exists in the intouch-api-v3 codebase today. If it does not exist, REQ-38 is silently asserting a to-be-built component as if it were already there — naming a phantom class lets Designer + SDET assume the mechanism is free when actually it needs to be designed and tested. Q26 lock (line 480) never mentions `TierRenewalNormalizer` by name — it only says "the engine has no storage slot for an independent renewal rule" and "renewal is implicit". The normalizer name is a BA invention, unverified.
  - **Evidence needed**: (a) Does `TierRenewalNormalizer` exist? (b) If not, is creating it in scope for 6a? The scope section says "wire-layer only in intouch-api-v3" — a normalizer is wire-layer, so probably in scope, but it needs to be an explicit REQ, not a casual mention.
  - **Confidence assessment**: BA implies C5. Actually C2 — named class with no evidence.
  - **Severity**: MEDIUM
  - **Recommendation**: Either cite evidence (file path) or rename to "a renewal-normalization step (to be designed)" and ensure Designer phase produces the interface.

- **C-14 (NEW)**: REQ-02 list-endpoint element shape is under-specified — ambiguity on read-wide hoist per element
  - **Source**: REQ-02, REQ-20
  - **Challenge**: REQ-02 says the list endpoint returns "an array of the same flattened envelopes — each element is `{ ...tier fields at root, status, pendingDraft: {...} | null }`". REQ-20 says `GET /v3/tiers/{tierId}` hoists program-level fields read-wide. The list REQ is silent on whether each list element ALSO hoists the program-level fields. Two possibilities, both problematic:
    - (a) **Yes, each element hoists**: Payload explodes — for 50 tiers, 12 program-level fields × 50 = 600 duplicated values. UI likely pre-fills advanced-settings from any one element, so 49 copies are wasted bandwidth.
    - (b) **No, only detail endpoint hoists**: UI must round-trip to `GET /v3/tiers/{tierId}` for any one tier to get program-level state — defeats the "paint both screens from one call" Q24 motivation.
  - A skeptic says: "You specified the shape twice and the two specifications contradict in a way neither BA sentence resolves."
  - **Evidence needed**: Explicit product decision. If (a), confirm scale (50 tiers × 12 fields is ~600 extra values — measurable but small). If (b), accept that advanced-settings screen needs its own GET.
  - **Confidence assessment**: BA implies C5 by omission. Actually C2 — specification gap.
  - **Severity**: MEDIUM
  - **Recommendation**: Product/UX decides. Designer should codify a one-line choice in the interface contract.

- **C-15 (NEW)**: REQ-55 is not a new requirement — it is a consequence of existing drift detection
  - **Source**: REQ-55
  - **Challenge**: REQ-55 text: "When old UI edits a tier that has a pending new-UI DRAFT, the SQL UPDATE succeeds (legacy path is unaffected). The Mongo DRAFT's `basisSqlSnapshot` now lags SQL; this is detected at approval time (see US-6 drift check)." This is **not a new acceptance criterion** — it is a derivation. US-6 already covers drift detection; REQ-47 already captures `basisSqlSnapshot`; REQ-54 already says old UI writes bypass MC. REQ-55 adds zero testable behaviour beyond the composition of pre-existing REQs. Labeling it NEW inflates the 11-new count and dilutes auditability. A skeptic says: "You counted a derived theorem as a new axiom."
  - **Evidence needed**: None — this is a classification issue, not a contract issue.
  - **Confidence assessment**: BA implies C5. Actually C4 — the CLAIM is true but the CLASSIFICATION as NEW is wrong.
  - **Severity**: LOW
  - **Recommendation**: Reclassify REQ-55 as CONFIRMED (implicit in US-6), or keep it NEW but move it under US-3 as an explanatory note rather than a testable AC.

- **C-16 (NEW)**: REQ-33 rejects `isDowngradeOnPartnerProgramDeLinkingEnabled` but the engine field name drifts from the wire (Q13 caveat)
  - **Source**: REQ-33, Q13 residual caveat, Q20 Class A list
  - **Challenge**: Q13 explicitly notes: "Residual caveat: `isDowngradeOnPartnerProgramDeLinkingEnabled` schema drift (JSON key 'Expiry' vs Java field 'DeLinking') noted as future cleanup, out of Q10b scope." The reject validator in REQ-33 must choose which key to scan for. If it rejects on the Java name only, the wire (using "Expiry"?) slips through. If it rejects on the JSON key, the Java-side callers that set the field directly are fine but the wire reject logic is coupled to a legacy key name. REQ-33 is silent on which name the validator matches. A skeptic says: "You shipped a reject rule that cannot identify the field it's rejecting."
  - **Evidence needed**: Inspect the DTO `@JsonProperty` for this field in intouch-api-v3 tier controller. Decide reject key.
  - **Confidence assessment**: BA implies C5 (field is listed). Actually C3 — name ambiguity.
  - **Severity**: MEDIUM
  - **Recommendation**: Designer must name the exact key to match. QA must have a test fixture using that exact key.

- **C-17 (NEW)** — **RESOLVED (Phase 4 Q-OP-3, 2026-04-22, C5 → C6 for audited surface)**: Q11 hard-flip residual-risk mitigation is *internal only* — external consumer audit missing
  - **Resolution**: Codebase audit across 16 repos (search terms `v3/tiers`, `TierController`, `TierReviewController`, `api_gateway.*tier`, `POST.*tier`, `PUT.*tier`, `CreateTier`, `UpdateTier`) found **zero internal backend consumers**. All `/v3/tiers` references are internal to `intouch-api-v3` itself (7 files — 2 controllers, 2 validators, 2 transformers, 1 test). False positives (PHP form fields, partner-program Thrift, promotion endpoints, SQL seeds, documentation copies) triaged out. Confidence upgraded C5 → C6 for surveyed surface. Residual C5 risks (external SaaS customers, third-party integrations, separate QA repos, nginx rewrites, operator scripts) flagged forward to Phase 11 Reviewer for deploy access-log scan. Evidence artifact: `q-op-3-consumer-audit.md`.
  - **Source**: Q11 session-memory note; REQ-27, REQ-49
  - **Challenge**: Q11 note (line 427): "Residual risk: unverified external caller surface — mitigated by grepping intouch-api-v3 `src/test` for JSON-body literal `"downgrade"` before flip to scope internal blast radius." This mitigates *internal* blast radius (no test fixtures broken). It explicitly does NOT audit external consumers of the `/v3/tiers` endpoint. The BA says v3 is "pre-GA for the new UI (the only real consumer, which Capillary controls)" — but does the same test-grep cover external integrators? No. Zero consumer audit was performed. A skeptic says: "You confirmed your own tests don't send `downgrade`; you didn't confirm your customers' tests don't send `downgrade`."
  - **Evidence needed**: List of external consumers of `POST|PUT /v3/tiers` (per API gateway logs / access logs / client registry). If there are any, they need notification or a compatibility shim.
  - **Confidence assessment**: BA implies C5 (Q11 locked). Actually C3 — a key piece of the "no back-compat window" argument is unverified.
  - **Severity**: HIGH
  - **Recommendation**: Phase 4 blocker check — confirm with product that no external consumers exist before Q11 commits the hard flip.

### Cross-REQ Consistency Findings

| REQ pair | Relationship | Finding |
|---|---|---|
| REQ-20 vs REQ-26 | Read-wide vs per-tier write | `validity.periodType`/`periodValue` in BOTH — see C-8 (BLOCKER) |
| REQ-19 vs REQ-35 | Read filter vs write reject | Agree on string-match but both blind to numeric `-1` — see C-10 |
| REQ-38 vs REQ-26 | Renewal auto-fill vs renewal optional | REQ-26 says renewal fields are optional; REQ-38 says null is auto-filled. Consistent on intent, but relies on phantom `TierRenewalNormalizer` — see C-13 |
| REQ-07 vs REQ-20 | `renewal.downgradeTo` per-tier vs eligibility hoist | Agree — renewal is per-tier (Q10c), eligibility is program-level. No conflict. |
| REQ-33 vs REQ-34 | Class A vs Class B reject | Disjoint lists; together cover Q24's full rejected-field list except for one ambiguity (`isDowngradeOnPartnerProgramDeLinkingEnabled` — see C-16) |
| REQ-27 vs REQ-49 | POST vs PUT downgrade reject | Parity confirmed. Both depend on Jackson config — see C-11 |
| REQ-02 vs REQ-20 | List envelope vs detail hoist | Shape ambiguity — see C-14 |
| REQ-21 vs REQ-22 vs REQ-36 | PeriodType coverage | Cover 2 of 4 enum values — see C-12 |
| REQ-40 vs REQ-33..REQ-38 | Error code range | 10 slots shared with pre-existing 9 — see C-9 |

### Q-Lock Coverage Stress Test

| Q-lock | Covered? | Scope-creep? | Under-delivery? | Notes |
|---|---|---|---|---|
| Q1 (envelope flatten) | Yes — REQ-02 | No | No | Clean. |
| Q2 (live.* hoist to root) | Yes — REQ-02 | No | No | Clean. |
| Q3 (downgrade → renewal rename) | Yes — REQ-07/26/27/49 | No | No | Covered across read + write. |
| Q4 (pendingDraft reserved) | Yes — REQ-02 | No | **Possibly** | Q4 says "reserved for forward-compat dual-block". REQ-02 says it is "null when absent" — agreement. But the LIST endpoint shape is under-specified — see C-14. |
| Q5c (multi-tracker defensive reject) | Yes — REQ-34 | No | No | Subsumed by Q24. |
| Q7 (drop `validity.startDate` for SLAB_UPGRADE) | Yes — REQ-21/26/36 | No | **Yes** — C-12 | Cyclic + fixed-customer-registration uncovered. |
| Q8 (compute FIXED end-date) | Yes — REQ-22 | No | No | Clean. |
| Q9 (-1 sentinel read+write lockstep) | Yes — REQ-19/35 | No | **Yes** — C-10 | Numeric `-1` gap. |
| Q10c (renewal per-tier) | Yes — REQ-26/49 | No | No | Clean. |
| Q11 (hard flip) | Yes — REQ-27 | No | **Yes** — C-17 | Residual risk on external consumers unverified. C-11 adds rejection-mechanism ambiguity. |
| Q13 (intouch-api-v3 only) | Invariant — no REQ | — | No | C-16 residual caveat affects REQ-33. |
| Q16 (periodType) | Yes — REQ-20 | No | No | Clean. |
| Q17 (Class A reject) | Yes — REQ-33 | No | **Yes** — C-16 | `isDowngradeOnPartnerProgramDeLinkingEnabled` key-name ambiguity. |
| Q18 (Class B reject) | Yes — REQ-34 | — | — | **Phantom lock** — see C-7. |
| Q19 (compound group-condition removal) | **NO** — no REQ | — | **Yes** | C-7 BLOCKER — cited but neither locked nor covered. |
| Q20 (engine storage classification) | Yes — REQ-20/26 | **Yes** — C-8 | — | `validity.*` omission from Q20 classification is exploited in REQ-26. |
| Q21 (subsumed by Q24) | — | — | — | **Phantom lock** — see C-7. Since it is claimed "subsumed by Q24", this might be benign, but should be confirmed. |
| Q22 (no nested advancedSettings) | Yes — REQ-37 | No | No | Clean. |
| Q24 (asymmetric contract) | Yes — REQ-20/33/34 | No | **Possibly** — C-8 | Valdity fields slip through. |
| Q26 (criteriaType + doc rename) | Yes — REQ-07/38 | No | No — but see C-13 (normalizer claim unverified) | — |
| FU-01 CANCELLED | Yes — defensive reject REQ-34 stands | No | No | Clean. Engine supports multi-tracker; 6a reject is correct posture. |

### Assumption Inventory (Unstated)

1. **A-01**: Jackson `ObjectMapper` in intouch-api-v3 is configured to reject unknown fields (needed for REQ-27/REQ-49 Q11 hard-flip). **Unverified.** → C-11
2. **A-02**: `eligibility.conditions[].value` and `renewal.conditions[].value` are serialized as strings on the wire (needed for REQ-19/REQ-35 `"-1"` string-match). **Unverified.** → C-10
3. **A-03**: `TierRenewalNormalizer` class exists or will be built and is in scope for 6a (REQ-38). **Unverified class name.** → C-13
4. **A-04**: `PeriodType` values other than `SLAB_UPGRADE` and `FIXED` are either out of scope for v3 or covered by implicit passthrough. **Unstated.** → C-12
5. **A-05**: `isDowngradeOnPartnerProgramDeLinkingEnabled` reject rule matches the wire JSON key, not the Java field name (or both). **Unstated.** → C-16
6. **A-06**: No external consumers of `POST|PUT /v3/tiers` carry the legacy `downgrade` field. **Unverified beyond internal tests.** → C-17
7. **A-07**: List endpoint element shape — either each element hoists the full program-level block (payload inflation) or only the detail endpoint hoists (extra round-trip for advanced-settings screen). **Unspecified.** → C-14
8. **A-08**: Q18, Q19, Q21 have valid locked decisions somewhere not yet captured in session-memory. **Evidence absent.** → C-7
9. **A-09**: `validity.periodType` / `validity.periodValue` are per-tier fields on the wire despite `validity` being classified program-level in Q20. **Self-contradictory without explicit carve-out.** → C-8
10. **A-10**: Error codes can be reused across Rework #4 rejects and 6a rejects without breaking client error-code consumers. **Silent contract risk.** → C-9

### Summary for Forward Cascade

- **New contradictions**: 11 (C-7 through C-17)
  - BLOCKER: 2 (C-7 phantom Q-locks, C-8 validity asymmetry)
  - HIGH: 5 (C-9 error code collision, C-10 numeric sentinel, C-11 Jackson config, C-12 PeriodType coverage, C-17 external consumer audit)
  - MEDIUM: 3 (C-13 normalizer class, C-14 list hoist shape, C-16 key-name drift)
  - LOW: 1 (C-15 REQ-55 classification)
- **Existing contradictions closed**: 0 (6a is scope-narrow; none of C-1..C-6 are resolved by it)
- **Existing contradictions still open**: 6 (C-1..C-6 all unchanged; C-1 should be re-examined given Q15's `createSlabAndUpdateStrategies` "reuse" note, which is itself a cross-contradiction with C-1)
- **BA soundness verdict**: **WEAK**
  - Two BLOCKERs before Designer can proceed (C-7, C-8). Five HIGH severity consistency gaps. Phantom Q-lock citations undermine the audit trail the rework delta was supposed to produce.
  - On the positive side: the rename sweep (Q3) and the read-wide/write-narrow Q24 principle are internally consistent at the surface level; the 11-new / 7-update triage is mechanically correct; the machine YAML coverage map is thorough.
  - But the specifics (error codes, PeriodType coverage, validity classification, normalizer existence, Jackson config) show the BA was written by paraphrasing decisions rather than reading evidence. The Rework #5 schedule-asymmetry pattern — shape-splitting a field across read and write without pinning storage — is partially re-created in `validity.*`.
- **Recommendations for Blocker Resolution (Phase 4)**:
  1. Resolve C-7: produce Q18/Q19/Q21 lock text, or remove the citations (BLOCKER).
  2. Resolve C-8: decide whether `validity.periodType` is program-level or per-tier; adjust REQ-20 or REQ-34 accordingly (BLOCKER).
  3. Resolve C-9: allocate distinct error codes per new reject (HIGH).
  4. Resolve C-17: confirm no external consumers of the legacy `downgrade` field before Q11 flip (HIGH).
  5. Surface C-10, C-11, C-12, C-13 to Designer as specific interface-contract questions.
  6. Product/UX call on C-14 (list endpoint hoist shape).

