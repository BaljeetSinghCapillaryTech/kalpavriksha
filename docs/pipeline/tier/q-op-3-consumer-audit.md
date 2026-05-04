# Q-OP-3 Consumer Audit — `POST/PUT /v3/tiers` Internal Caller Sweep

> **Phase 4 blocker**: Q-OP-3 (external consumer impact of Rework #6a contract changes)
> **Decision option picked**: (a) Audit codebase for internal callers
> **Date**: 2026-04-22
> **Auditor**: Rework #6a Phase 4
> **Resolves**: **C-17** (external consumer audit missing) — brings "new UI is the only consumer" from C5 → C6 for the repos surveyed. Residual C5 external-consumer risk flagged forward to Phase 11.

---

## 1. Why this audit exists

The Rework #6a v3 tier write contract introduces:
- Hard rejects on unknown fields (Jackson `FAIL_ON_UNKNOWN_PROPERTIES`, Q11)
- Distinct error code band **9011–9020** for per-REQ rejects (Q-OP-1)
- New conditional-duration reject (REQ-56, code 9018, Q-OP-2)
- Write-narrow / read-wide asymmetric schema (Q24)

Anyone still submitting legacy-shaped payloads (e.g., `downgrade` field, flat periodType without `periodValue` where the new guard requires one) would start getting 400s after cutover. The original BA claim at `00-ba.md §2.4 Constraints` asserted "the new UI is the only consumer." That claim was held at **C5** (confident but residual risk). Q-OP-3 exists to raise that to **C6** by auditing the codebase for internal backend callers.

---

## 2. Search scope

Workspace: `/Users/ritwikranjan/Desktop/emf-parent/` (15 sibling repos) + `/Users/ritwikranjan/Desktop/Artificial Intelligence/emf-parent` + `/Users/ritwikranjan/Desktop/Artificial Intelligence/kalpavriksha`.

Repos swept:
| # | Repo | Tech | Hits | Verdict |
|---|---|---|---|---|
| 1 | `intouch-api-v3` | Java / Spring | 7 files | **Producer** (all internal to the endpoint module) |
| 2 | `emf-parent` | Java / Points engine | 0 | Clean |
| 3 | `peb` | Java / Points-Engine Backend | 0 | Clean |
| 4 | `Thrift` | IDL | 0 on tier CRUD (only `PartnerProgramTierUpdate` — unrelated partner-program domain) | Clean |
| 5 | `rule-engine` | Java | 0 | Clean |
| 6 | `cd-cheetah-apps-points-core` | PHP widgets | 2 hits, all `$_POST['tier_upgrade_strategy_home__...']` form fields (HTML form POST, NOT REST HTTP) | Clean |
| 7 | `cd-cheetah-apps-points-core-master` | PHP | 0 | Clean |
| 8 | `cd-cheetah-etl` | ETL | 0 | Clean |
| 9 | `cd-libcheetah` | PHP lib | 0 | Clean |
| 10 | `cc-stack-crm` | Java + SQL seeds | 1 false positive in `nifi_template_data.sql` (zero matches on precise regex) | Clean |
| 11 | `campaigns_auto` | Python | `/api_gateway/loyalty/v1/*` hits are for **promotion** endpoints only — `exportPromotion`, `createPromotionV2`, etc. No tier endpoints. | Clean |
| 12 | `crm-mcp-servers` | MCP | 0 | Clean |
| 13 | `event-notification` | Java | 0 | Clean |
| 14 | `emf-async-executor` | Java | 0 | Clean |
| 15 | `cap-intouch-ui-appserver-wrapper` | Wrapper | 0 | Clean |
| 16 | `shopbook-datamodel` | Data | 0 | Clean |
| 17 | `Artificial Intelligence/emf-parent` (second copy) | Java | 4 hits — all in `.claude/skills/*` and `.claude/agents/aidlc.md` (documentation) | **Docs only**, not code consumers |
| 18 | `Artificial Intelligence/kalpavriksha` | This pipeline artifact folder | 30 hits — all pipeline docs | **Docs only**, not code consumers |

**Search terms used:**
- `v3/tiers` (literal)
- `/v3/tiers` with quote boundaries
- `TierController`, `TierReviewController`
- `api_gateway.*tier`, `api_gateway/loyalty/v1/tiers`
- `POST.*tier`, `PUT.*tier` (broad pass — hits manually triaged)
- `CreateTier`, `UpdateTier`, `tier.*create`, `tier.*update` (Thrift IDL pass)

---

## 3. What was found inside `intouch-api-v3` (the producer)

7 files — all are either the endpoint itself or internal support for the endpoint. **No internal caller**:

| File | Role | Consumer? |
|---|---|---|
| `resources/TierController.java` | `@RequestMapping("/v3/tiers")` — the endpoint handler | No — producer |
| `resources/TierReviewController.java` | `@RequestMapping("/v3/tiers")` — submit/approve endpoints | No — producer |
| `tier/validation/TierCreateRequestValidator.java` | Validates POST payload (internal to the resource) | No — validator |
| `tier/validation/TierUpdateRequestValidator.java` | Validates PUT payload (internal to the resource) | No — validator |
| `tier/strategy/TierStrategyTransformer.java` | Serializes tier to response on GET (internal to the resource) | No — transformer |
| `tier/model/TierDateFormat.java` | Date format contract (internal) | No — internal type |
| `tier/strategy/TierStrategyTransformerTest.java` | Test fixture referencing endpoint in doc comments | No — test |

---

## 4. Residual risk (the C5 → C6 delta)

Audit raises confidence from **C5 → C6** for the repos surveyed. It does **not** reach **C7** because these channels were not inspected:

| Channel | Why it's outside audit reach | Risk level |
|---|---|---|
| External SaaS customer integrations (direct Capillary API usage) | Lives outside the codebase — exists only in production traffic logs | **MEDIUM** — could break silently on cutover |
| Third-party automation / data-sync tools built by integration partners | Not in any owned repo | MEDIUM |
| QA / performance / regression automation in separate test repos (not in this workspace) | Not pulled locally | LOW — owned internally, can be scanned on demand |
| nginx `api_gateway` rewrite rules (if any) that expose tier write paths via a different route | Config, not code — lives in deploy tooling | LOW — searched via `api_gateway.*tier` and found only promotion endpoints |
| Internal cURL scripts / ops runbooks (operator-run hot-fixes) | Not typically checked into these repos | LOW — operator-mediated |

**Mitigation recommendation for Phase 11 (Reviewer) and deploy prep:**
1. **Access-log scan** at staging gateway for non-UI user agents hitting `POST /v3/tiers*` or `PUT /v3/tiers/{id}` over the last 30 days. If the scan returns only the new UI's user agent, residual risk drops to C7.
2. **Error-code band announcement** — publish the 9011–9020 band assignment in the API handoff doc (already done in `api-handoff.md`) at least 30 days before cutover. Any consumer that parses error codes will see the new codes but not a breaking change (the old 9001–9010 band is still emitted for legacy validator paths).
3. **Unknown-field rejection soft-launch** — optional: in staging, log (not reject) unknown fields for two weeks before flipping to hard reject in production. This surfaces any hidden consumer submitting extra keys.

---

## 5. Verdict

- **Internal backend consumers of `POST /v3/tiers` / `PUT /v3/tiers/{tierId}`: 0 found** across 16 repos swept.
- **Assumption** "the new UI is the only consumer" is upgraded from **C5 → C6** for the audited surface.
- **Residual C5 risk** exists for external integrations, production traffic, and automation repos outside this workspace — mitigated by the Phase 11 access-log scan recommendation and by the soft-launch option above.
- **No changes required** to BA/PRD/Architect/Designer artifacts as a result of this audit. The contract holds as-is.

---

## 6. Traceability

| Artifact | Field/Section | Status |
|---|---|---|
| `contradictions.md` | C-17 (external consumer risk) | **C5 → C6** after this audit |
| `00-ba.md` §2.4 Constraints ("new UI is the only consumer") | Evidence citation | Add reference to this file |
| `pipeline-state.json` `rework_cycles[4].execution_state.phase_4_blocker_resolutions.Q-OP-3_*` | Resolution log | To be added after this artifact |
| `session-memory.md` — Q-OP-3 lock block | Incremental decision log | To be added after this artifact |
| `07-reviewer.md` (Phase 11, forthcoming) | Residual risk flag (external consumer) | Forward flag for deploy access-log scan |

---

**Owner of residual risk:** Deployment / Platform team (access-log scan) + QA (soft-launch monitoring).
**Blocker status:** Q-OP-3 **RESOLVED** (Phase 4 closure).
