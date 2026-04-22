# Critic Review — Contradictions & Challenges
> Feature: Loyalty Extended Fields CRUD (CAP-183124)
> Phase: 2 — Critic
> Date: 2026-04-22
> Reviewer: Critic (Devil's Advocate)

---

## Summary Counts

| Severity | Count |
|----------|-------|
| CRITICAL | 7 |
| HIGH     | 9 |
| MEDIUM   | 8 |
| LOW      | 4 |
| **Total** | **28** |

---

## CRITICAL Findings

---

### Contradiction #1
**Source**: 00-prd.md § New Thrift Structs; 00-prd-machine.md § thrift.new_structs  
**Claim**: `LoyaltyExtendedFieldConfig` has fields `1: required i64 id`, `2: required i64 orgId`, `3: required string name`, `4: required string scope`, `5: required string dataType`, `6: required bool isMandatory`, `8: required bool isActive`, `9: required string createdOn`, `10: required string lastUpdatedOn`. Most non-optional fields are declared `required`.  
**Challenge**: In Apache Thrift, marking fields as `required` on a struct that is used as a **response** breaks forward/backward compatibility permanently. If a future version needs to add a field that was previously required, or if an older client receives a response that is missing a required field (e.g., due to a conditional serialisation path), the Thrift deserialiser will **throw a `TProtocolException`** rather than silently ignoring it. The PRD itself acknowledges this problem in the Non-Functional Requirements table (G-09.5: "New Thrift fields must be `optional` for backward compatibility"), yet the Thrift struct definitions directly below violate this very rule. Required fields in Thrift are a known footgun: the Thrift documentation explicitly recommends against `required` for most fields. This is not a style issue — it is a **binary compatibility break** waiting to happen the first time any field needs to be removed or any client version skew exists between V3 and EMF.  
**Risk Level**: CRITICAL  
**Evidence needed**: Check the existing `ExtendedFieldsData` struct and all other structs in `emf.thrift` — are they consistently `optional`? If yes, this contradiction is confirmed by the project's own existing pattern.  
**Recommendation**: Change all fields in `LoyaltyExtendedFieldConfig`, `CreateLoyaltyExtendedFieldRequest`, and `LoyaltyExtendedFieldListResponse` to `optional`. Mark only `id` and `orgId` as `required` if the team agrees those can never be absent. The rule G-09.5 already says this; the struct definitions must comply. Architect must enforce this before any Thrift IDL is committed.

---

### Contradiction #2
**Source**: 00-ba.md § EF-US-07; 00-prd.md § Data Model (Modified); 00-prd-machine.md § schema.modified_models  
**Claim**: "MongoDB field name in documents updated (`type` → `scope`) or migration handled." The acceptance criteria for EF-US-07 says: "MongoDB JSON field key updated from 'type' to 'scope' in new documents."  
**Challenge**: There is a critical split between "new documents" and "existing documents." If the Java field is renamed from `type` to `scope` (and the JSON key follows), all **existing MongoDB documents** in `subscription_programs` that have `extendedFields[].type` as the field name will **silently fail to deserialise** into the new Java model. Spring Data MongoDB will populate `scope` as `null` for all existing documents that use the old `type` key. The BA says "MongoDB field name in documents updated (`type` → `scope`) or migration handled" — the word "or" is doing enormous work here. There is no migration strategy defined. The BA defers this to the Architect but does not flag it as a blocking open question. The PRD machine says only "new documents" are affected. This is wrong — all existing `subscription_programs` documents with `extendedFields` populated will have `scope = null` after the rename. How many such documents exist in production? Nobody knows — there is no count cited.  
**Risk Level**: CRITICAL  
**Evidence needed**: (1) Count of MongoDB `subscription_programs` documents where `extendedFields` array is non-empty. (2) Confirmation of whether a `@Field("type")` annotation can preserve backward compatibility without touching existing data. (3) Explicit go/no-go decision on whether a MongoDB migration script is required.  
**Recommendation**: Either (a) annotate the Java field with `@Field("type")` to keep the MongoDB key as `type` while the Java name becomes `scope` — deferring the MongoDB migration to a separate task, OR (b) write a MongoDB migration script that updates all existing documents before the code is deployed. Option (a) is safer for zero-downtime. This must be a blocking decision, not an "Architect to decide later" note.

---

### Contradiction #3
**Source**: 00-ba.md § Assumptions A-06; 00-prd.md § Data Model; 00-prd-machine.md § schema.modified_models  
**Claim**: A-06 states "Existing `SubscriptionProgram.extendedFields` MongoDB field name stays as `extendedFields` — only the Java field `type` is renamed to `scope`; the JSON key is updated to `scope`."  
**Challenge**: A-06 contains an internal contradiction. It says the "MongoDB field name stays as `extendedFields`" (the array-level key is preserved) but then says "the JSON key is updated to `scope`" (meaning the inner element-level key `type` changes to `scope`). These are two different things and both are stated in the same assumption. However, the second part — "JSON key is updated to `scope`" — directly contradicts the claim that "existing documents" are safe. If the JSON key changes from `type` to `scope` in new documents, the system will have two different schemas coexisting in the same MongoDB collection indefinitely: old documents with `extendedFields[].type`, new documents with `extendedFields[].scope`. No read path is specified for how this mixed-schema collection is handled. Any query or deserialisation that processes `extendedFields` will produce inconsistent results depending on when the document was written.  
**Risk Level**: CRITICAL  
**Evidence needed**: Actual MongoDB document samples from `subscription_programs` that have non-empty `extendedFields`. Confirmation of whether `@Field` annotation is already present or absent in the existing `SubscriptionProgram.ExtendedField` inner class.  
**Recommendation**: Decide explicitly: use `@Field("type")` annotation to maintain MongoDB key as `type` in ALL documents (no migration needed, no dual-schema problem) while the Java field becomes `scope`. This is the simplest and safest path. Document this as a standing decision and do not leave it as an assumption.

---

### Contradiction #4
**Source**: 00-ba.md § EF-US-05; 00-prd.md § Validation flow; 00-prd-machine.md § validation_rules  
**Claim**: "All mandatory `ACTIVE` EF definitions for `(org_id, SUBSCRIPTION_META)` must be present → else `400`." And the prd-machine lists this as R-04.  
**Challenge**: There is a race condition that is not addressed anywhere. The EF validation at subscription create/update time performs a live DB lookup: it fetches all active mandatory EF definitions for `(org_id, SUBSCRIPTION_META)` and then checks whether the submitted `extendedFields` contains all of them. What happens if an EF definition is deactivated **between** the time the validation lookup runs and the time the MongoDB write completes? Or, conversely, what if a new mandatory EF is **activated** mid-request? The validation is point-in-time; the enforcement is also point-in-time but at a different point. More critically: what if two concurrent subscription create requests run simultaneously, one of which deactivates an EF (via PUT is_active=false) exactly as the other is mid-validation? The deactivated EF was active when the validation lookup ran but INACTIVE when the data is written. This produces a MongoDB document containing a value for a field that is now inactive. Decision D-18 says "existing values are unaffected by deactivation" — but this scenario creates a NEW value for an inactive field, not an existing one. The validation correctness guarantee breaks under concurrent write.  
**Risk Level**: CRITICAL  
**Evidence needed**: Confirmation of whether EF config changes (deactivate) and subscription creates can be concurrent in production. Confirmation of whether any transactional/locking mechanism exists across the MySQL config write and MongoDB subscription write.  
**Recommendation**: The validation_rules must specify the consistency model explicitly. Options: (a) Accept eventual consistency — document as a known limitation, (b) Use a short-lived cache with TTL to reduce (but not eliminate) the window, (c) Re-validate after MongoDB write. At minimum, this must be an explicit design decision, not a silent gap.

---

### Contradiction #5
**Source**: 00-prd.md § API Contracts (PUT endpoint); 00-ba.md § EF-US-02; 00-prd-machine.md § apis (PUT)  
**Claim**: The PUT `is_mandatory` is listed as immutable after creation (D-23). BA EF-US-02 says "`name` and `scope` are immutable after creation (cannot be changed via PUT)". But then D-23 and prd-machine say "`name` (String) and `is_active` (boolean) are mutable — D-23", and that `is_mandatory` and `default_value` are immutable.  
**Challenge**: The BA (EF-US-02) says `name` is **immutable**. The session-memory D-23 and D-25 say `name` is **mutable**. The prd-machine (EF-US-02 ACs) says `name` is mutable and re-validates uniqueness. The 00-prd.md PUT contract says name is mutable (it's in the request body). This is a **direct contradiction between BA and PRD/session-memory for a core business rule**. The BA was written first; the PRD overrides it via D-25. But the BA was not updated to reflect D-25. Any developer reading EF-US-02 in 00-ba.md will implement a different behaviour (immutable name) than the PRD demands (mutable name). This will cause a silent implementation defect.  
**Risk Level**: CRITICAL  
**Evidence needed**: Confirmation of which document is authoritative when BA and PRD contradict on the same acceptance criterion.  
**Recommendation**: Update BA EF-US-02 acceptance criteria immediately to reflect D-25 (name is mutable). Add an explicit note: "D-25 overrides original BA assumption — name is mutable, scope and data_type are not." Establish a rule: BA must always be updated when PRD grooming decisions contradict it.

---

### Contradiction #6
**Source**: 00-prd.md § Grooming Questions GQ-02; 00-prd-machine.md § org_config; 00-ba.md § Scope item 7  
**Claim**: "Org-level max EF count stored in `program_config_key_values` table with default value = 10." GQ-02 resolved. D-15 confirmed at C7.  
**Challenge**: No evidence is presented that `program_config_key_values` supports per-org string config values suitable for a numeric limit. What is the schema of `program_config_key_values`? Is there a row per org? Is there a default fallback row? Is the value stored as VARCHAR that must be parsed to int? Who writes the default row — deployment script, application code, or manual DB seed? Who reads it — V3 or EMF? The prd-machine says "key name TBD — Architect to confirm exact key." A decision marked C7 (Near Certain / verified fact) with "key name TBD" is self-contradictory. C7 requires primary source verification. If the key name is unknown, the confidence cannot be C7. Additionally, who enforces the org-level max? If EMF enforces it, EMF must query `program_config_key_values` for every create call — which DB does that table live in? If V3 enforces it, V3 must call EMF just to get the limit, then call EMF again to create. The enforcement location is not specified.  
**Risk Level**: CRITICAL  
**Evidence needed**: (1) Schema of `program_config_key_values` — column names, data types, indexing. (2) Confirm which service (V3 or EMF) reads this table. (3) Confirm the exact key name and whether a default row needs to be seeded. (4) Confirm whether the limit is checked at EMF (preferred, avoids double Thrift calls) or V3.  
**Recommendation**: Downgrade D-15 from C7 to C3 until the `program_config_key_values` schema is read from actual source code. The "key name TBD" admission alone disqualifies C7. Architect must resolve this as a blocking question in Phase 6.

---

### Contradiction #7
**Source**: 00-prd.md § API Contracts (POST, 409 error); 00-prd-machine.md § validation_rules  
**Claim**: POST 409 error: "`(org_id, scope, name)` already exists and `is_active=1`." The uniqueness key in the DB is `UNIQUE KEY uq_org_scope_name (org_id, scope, name)`.  
**Challenge**: The 409 condition in the API contract ("already exists and is_active=1") does NOT match the DB uniqueness constraint ("already exists" period, regardless of is_active). The DB unique key `uq_org_scope_name` on `(org_id, scope, name)` will raise a duplicate key error for ANY duplicate combination — including one where the existing row is INACTIVE. This means: if an org creates an EF named "discount_pct", then deactivates it (is_active=0), then tries to create a new "discount_pct" in the same scope — the DB will reject it with a unique key violation, but the API contract says this should only return 409 when `is_active=1`. The result: a `DataIntegrityViolationException` from the DAO layer that propagates as a 500, not a clean 409. The API promise is "you can reuse a name after deactivating" (implied by the `is_active=1` condition on 409), but the DB schema prohibits this. This is a schema design defect.  
**Risk Level**: CRITICAL  
**Evidence needed**: Confirm whether the intended behaviour is: (a) names are permanently unique even after deactivation, OR (b) names can be reused after deactivation. If (b), the unique constraint must be changed to a partial unique index on `(org_id, scope, name) WHERE is_active=1` — MySQL does not support partial indexes; this would require application-level uniqueness enforcement only, not DB-level.  
**Recommendation**: Decide explicitly: if names must be permanently unique (simpler, safer), update the 409 condition to remove the `is_active=1` qualifier. If names can be reused after deactivation, the unique key must be dropped from the schema and replaced with application-level enforcement only (with careful transaction handling). The current design is inconsistent between schema and API contract.

---

## HIGH Findings

---

### Contradiction #8
**Source**: 00-ba.md § EF-US-05 (Validate EF on Subscription Create)  
**Claim**: "If `extendedFields` is `null` or omitted AND mandatory fields exist → `400`"  
**Challenge**: This rule creates a **breaking change** for all existing subscription create callers. Prior to this feature, `extendedFields` was not validated at all (BA: "anything persisted without validation"). Any existing integration that does not pass `extendedFields` at all will now receive a 400 if ANY mandatory EF is configured. The moment an org admin creates a mandatory EF definition, ALL existing subscription create calls from integrations that don't know about EF will break. There is no transition/migration plan for existing callers. The BA does not address this backward compatibility concern at all.  
**Risk Level**: HIGH  
**Evidence needed**: (1) How many orgs currently use `POST /v3/subscriptions` in production. (2) Whether those callers pass `extendedFields` at all. (3) Whether there is a grace period / dual-mode behaviour planned.  
**Recommendation**: Add a backward compatibility story. At minimum: mandatory EF enforcement should only trigger for orgs that have at least one mandatory EF defined. If no mandatory EFs exist for the org, null/omitted `extendedFields` must be accepted without error. Document this explicitly as a validation rule (R-05 or similar). This is not currently specified.

---

### Contradiction #9
**Source**: 00-ba.md Constraints; session-memory.md Constraints  
**Claim**: "V3 → EMF communication via Thrift (new methods in `EMFService`). EMF owns warehouse DAO; V3 has no direct warehouse DB access." Marked as "Architecture constraint (verified)."  
**Challenge**: There is no primary source evidence presented in any artifact for this claim at C7. The session-memory says "Confirmed — emf-parent has `warehouse-database.properties` → warehouse DB access exists. V3 has NO warehouse access (connects to `target_loyalty` only)" with citation `(BA)`. But `(BA)` is not a primary source — it is a self-reference within the artifacts being reviewed. Was `warehouse-database.properties` actually read? Was the V3 database configuration actually read? The C7 confidence rating requires "verified fact from primary source." If this is wrong (e.g., V3 actually can reach the warehouse DB), the entire architecture decision to route all config calls through Thrift is unnecessary overhead.  
**Risk Level**: HIGH  
**Evidence needed**: Read `/Users/baljeetsingh/IdeaProjects/emf-parent/` for `warehouse-database.properties` or equivalent. Read V3 data source configuration to confirm it does NOT include warehouse. Only then is C7 justified.  
**Recommendation**: The Architect must read both configuration files in Phase 6 before confirming this constraint. If V3 does have warehouse access, the Thrift routing for a simple admin config CRUD may be reconsidered (though keeping it via EMF is still sound from a separation-of-concerns standpoint, the constraint must not be stated as fact without evidence).

---

### Contradiction #10
**Source**: 00-prd.md § Non-Functional Requirements ("Backward compat: New Thrift fields must be `optional`"); 00-prd-machine.md § thrift.new_structs  
**Claim**: G-09.5 is listed as a critical guardrail: "New Thrift fields must be `optional` for backward compatibility."  
**Challenge**: G-09.5 applies to **new fields added to existing structs** — it is the standard rule for evolving existing Thrift contracts. However, it is being applied as justification for the new structs being defined here. The new structs (`LoyaltyExtendedFieldConfig`, `CreateLoyaltyExtendedFieldRequest`, etc.) are entirely new — they don't break existing clients if all their fields are `required`. The REAL problem (Contradiction #1) is that `required` fields in response structs break future evolution. The document conflates two different backward compatibility concerns: (a) new fields in existing structs (G-09.5 applies), and (b) required vs optional fields in new structs (a different design concern). G-09.5 is being cited correctly but for the wrong reason — and the actual problem (required fields making future evolution impossible) is not named.  
**Risk Level**: HIGH  
**Evidence needed**: Review the existing EMF Thrift IDL to confirm the house style for new structs in this codebase.  
**Recommendation**: Clarify G-09.5 applies to new fields in EXISTING structs. Separately, add a new guardrail or design decision: "All response structs must use `optional` fields to allow future evolution." This is a separate concern from G-09.5.

---

### Contradiction #11
**Source**: 00-ba.md § EF-US-06; 00-prd-machine.md § validation_rules (empty_list rule)  
**Claim**: "If `extendedFields` is an empty list `[]` on PUT → clear all EF values (explicit intent to remove)"  
**Challenge**: Clearing all EF values when a PUT sends `[]` creates a dangerous footgun. If a caller accidentally sends `extendedFields: []` (e.g., due to a bug in their serialisation layer where null becomes empty array), all EF values for that subscription program are silently wiped. This is a **destructive, irreversible operation** (MongoDB document updated, old values gone). There is no confirmation step, no audit log (deferred), no recoverability mechanism. Furthermore, the acceptance criteria for EF-US-06 also says "No validation fired when `extendedFields` is null on PUT" — meaning `null` is safe (preserves values) but `[]` is destructive. This is a subtle and unintuitive distinction that callers are likely to get wrong.  
**Risk Level**: HIGH  
**Evidence needed**: Confirm whether the existing R-33 null-guard behaviour in `SubscriptionFacade` distinguishes between null and empty list consistently across all existing fields (not just EF).  
**Recommendation**: Either (a) treat `[]` and `null` identically (both preserve existing values) and require an explicit "clearExtendedFields: true" flag to wipe, OR (b) add a warning in the API contract with a prominent note about the destructive nature of `[]`. The current specification is valid but dangerous and needs explicit confirmation from the product owner.

---

### Contradiction #12
**Source**: 00-prd-machine.md § validation_rules R-03a  
**Claim**: "R-03a: when `data_type=ENUM`, value must be one of the registered `enum_values` (400 if not in allowed list)"  
**Challenge**: D-22 explicitly removes ENUM as a supported data type: "ENUM data type is **out of scope**. Allowed data_type values: STRING / NUMBER / BOOLEAN / DATE only." Yet R-03a in the prd-machine validation_rules still references `data_type=ENUM` and `enum_values`. This is a zombie rule — a leftover from before D-22 was made. The prd-machine was not fully updated. If a developer implements R-03a, they will implement ENUM validation for a data type that is not allowed. If they skip it, the inconsistency will cause confusion.  
**Risk Level**: HIGH  
**Evidence needed**: None needed — D-22 and R-03a directly contradict each other in the same document.  
**Recommendation**: Delete R-03a from prd-machine.md entirely. Add a comment next to D-22: "R-03a was removed when ENUM was descoped." The `allowed_values.data_type` list in prd-machine also correctly excludes ENUM, confirming R-03a is an orphaned rule.

---

### Contradiction #13
**Source**: session-memory.md § PRD Structure (table); 00-prd-machine.md § epics  
**Claim**: Session-memory PRD Structure table lists four stories for EF-EPIC-01: "EF-US-01, EF-US-02, EF-US-03, EF-US-04." But prd-machine lists only three stories: EF-US-01, EF-US-02, EF-US-03 — with a note "3 stories (was 4) — EF-US-03 (Deactivate) merged into EF-US-02 (PUT); no separate DELETE endpoint (D-24)."  
**Challenge**: The session-memory table still shows EF-US-04 as a story. After D-24, EF-US-03 was merged into EF-US-02, and the old EF-US-04 (List) became EF-US-03. The numbering is inconsistent across documents: BA uses EF-US-04 for List, prd-machine uses EF-US-03 for List (after merge). Tests, acceptance criteria references, and the session-memory table use the old numbering. Any developer who cross-references BA EF-US-03 (Deactivate) will find it as a standalone story with a separate DELETE endpoint — which was explicitly removed by D-24. This creates a real risk of implementing a DELETE endpoint that should not exist.  
**Risk Level**: HIGH  
**Evidence needed**: None — the numbering inconsistency is visible across the documents.  
**Recommendation**: Renumber the BA stories to match the final prd-machine numbering, or add a clear "SUPERSEDED by D-24" banner to BA EF-US-03. The session-memory PRD Structure table must be updated to reflect 3 stories, not 4.

---

### Contradiction #14
**Source**: 00-ba.md EF-US-07 acceptance criteria; 00-prd-machine.md § schema.modified_models  
**Claim**: EF-US-07 AC: "No other callers of `ExtendedFieldType` broken (grep confirms no other usages)." Session-memory D-13: "Tests BT-EF-01 to BT-EF-06 reference CUSTOMER_EXTENDED_FIELD/TXN_EXTENDED_FIELD — these must be updated."  
**Challenge**: D-13 explicitly says existing tests reference the wrong enum. But EF-US-07 says "grep confirms no other usages." If the tests use `ExtendedFieldType.CUSTOMER_EXTENDED_FIELD`, then there ARE other usages — the tests themselves. "Grep confirms no other usages" is not established yet (it's a future acceptance criterion, not a completed verification). More importantly, the existing `ExtendedFieldType` enum values (`CUSTOMER_EXTENDED_FIELD`, `TXN_EXTENDED_FIELD`) suggest the enum was used for a functional purpose: mapping to CDP EF entity types at evaluation time. If the enum was wired into any evaluation/resolution logic (not just tests), deleting it will break that logic. The BA says the enum "misrepresents the concept" but does not verify whether any resolution logic depends on the enum values.  
**Risk Level**: HIGH  
**Evidence needed**: Full grep of `ExtendedFieldType`, `CUSTOMER_EXTENDED_FIELD`, `TXN_EXTENDED_FIELD` across both intouch-api-v3 and emf-parent repos. Session-memory says the enum was used "as discriminator for evaluation-time resolution mapping to CDP EFs" — if that mapping still exists, deleting the enum without replacing the resolution logic will cause silent functional failures.  
**Recommendation**: Before EF-US-07 is implemented, run a cross-repo grep for `ExtendedFieldType` (including serialised form — check if any JSON/BSON mappings use the enum name as a string). Only after confirming zero functional usages (beyond tests) should the deletion proceed. This is an active investigation prerequisite, not an acceptance criterion.

---

### Contradiction #15
**Source**: 00-prd.md § API Contracts (PUT request body); 00-ba.md § EF-US-02 AC  
**Claim**: PUT request body can include `name: "new_field_name"` (optional rename). If omitted, name is unchanged.  
**Challenge**: There is no specification for what happens when name is sent as `null` versus not sent at all in the PUT request body. In JSON, `{"name": null}` is different from `{}` (field absent). In Java Spring with `@RequestBody`, if `name` is a `String` field in the DTO, a null JSON value will deserialise to Java `null`, and a missing field will also deserialise to `null`. The application cannot distinguish between "caller explicitly set name to null" and "caller did not include name." If a caller sends `{"name": null}`, should the name be cleared (resulting in a null name in DB, violating NOT NULL constraint) or ignored (treated as not-sent)? This is an under-specified edge case that will cause a NullPointerException or constraint violation if not handled.  
**Risk Level**: HIGH  
**Evidence needed**: Confirm how other PUT endpoints in intouch-api-v3 handle partial updates (PATCH-style PUT) — do they use `Optional<String>` fields, `@JsonIgnoreProperties`, or other patterns to distinguish null-as-absent from null-as-explicit?  
**Recommendation**: Specify explicitly: "If `name` is absent from PUT body, name is unchanged. If `name` is present but null, return 400 (name cannot be null)." Use `Optional<String>` or a separate patch DTO pattern. This must be specified before the Designer phase.

---

### Contradiction #16
**Source**: 00-ba.md § EF-US-05; 00-prd-machine.md § validation_rules  
**Claim**: EF Validation performs: "key must match an `ACTIVE` EF definition in `loyalty_extended_fields` for `(org_id, scope)`."  
**Challenge**: The validation lookup requires a DB query to `loyalty_extended_fields` on EVERY subscription create/update call. There is no caching (D-17: deferred). For orgs with high subscription create throughput, this adds a synchronous MySQL round-trip to every subscription write. In a high-frequency scenario, this becomes a bottleneck. More critically: if the `loyalty_extended_fields` table or the `program_config_key_values` table is unavailable (DB timeout, connection pool exhaustion), ALL subscription creates will fail with 500, even for orgs with zero EF configuration. The fail-open vs fail-closed behaviour under DB failure is not specified anywhere.  
**Risk Level**: HIGH  
**Evidence needed**: Confirmation of current subscription create throughput (requests/second) per org. Confirmation of whether the validation DB call should be fail-open (proceed if registry lookup fails) or fail-closed (reject if registry lookup fails).  
**Recommendation**: Add a fail-open/fail-closed decision as an explicit requirement. For a first release without caching, recommend fail-open with an error log (if the EF registry is unreachable, subscription create proceeds without EF validation). This is safer than making subscription reliability dependent on the EF registry DB health.

---

## MEDIUM Findings

---

### Contradiction #17
**Source**: 00-ba.md § Constraints; session-memory.md Constraints  
**Claim**: "`scope` column is `VARCHAR` (not MySQL ENUM) — future scope values will grow too large for DB ENUM. Application-level scope validation enforces allowed values."  
**Challenge**: The claim "future scope values will grow too large for DB ENUM" is not a coherent reason to avoid MySQL ENUM. MySQL ENUM supports 65,535 distinct values. The real reason to avoid MySQL ENUM is maintenance friction (ALTER TABLE required to add values). This is a C4-level rationale at best, presented without evidence as a settled decision. More importantly, "application-level scope validation enforces allowed values" — but where exactly? In V3 before the Thrift call? In EMF? If V3 validates, an attacker or misconfigured EMF client can bypass V3 and call EMF Thrift directly with an invalid scope. If EMF validates, which class/method holds the allowed scope list? This enforcement location is unspecified.  
**Risk Level**: MEDIUM  
**Evidence needed**: Identify the exact class in the call chain that will enforce the scope allowlist. Confirm whether EMF enforces it independently of V3.  
**Recommendation**: Specify the enforcement location: EMF service layer should enforce scope validity, not just V3. V3 is a convenience guard; EMF is the authoritative guard. Add this to the design constraints explicitly.

---

### Contradiction #18
**Source**: 00-prd.md § Non-Functional Requirements (Performance)  
**Claim**: "Validation caching deferred — implement based on actual usage data."  
**Challenge**: This decision assumes that "actual usage data" will be collected and acted upon. However, no telemetry/metrics story exists in the PRD. Without instrumentation (latency of EF validation, per-org EF lookup frequency), there will be no "actual usage data" to decide when to add caching. Deferred optimisations without instrumentation prerequisites commonly remain deferred indefinitely.  
**Risk Level**: MEDIUM  
**Evidence needed**: Confirm whether existing subscription create endpoints have latency metrics instrumented. If not, caching will never be added in practice.  
**Recommendation**: Add an NFR or acceptance criterion for EF-US-05: "EF validation lookup latency is instrumented (Micrometer/Prometheus timer) on every call." This provides the evidence needed to trigger the deferred caching decision.

---

### Contradiction #19
**Source**: 00-prd-machine.md § apis (GET); 00-ba.md EF-US-04  
**Claim**: GET supports `?scope=SUBSCRIPTION_META` as a filter. Scope is the only filter besides `includeInactive` and pagination.  
**Challenge**: There is no filter on `name`. Orgs could accumulate many EF definitions across multiple scopes over time. When an EF name is mutable (D-25), finding a field by name requires scanning all pages of results. There is also no GET-by-ID endpoint specified anywhere. The CRUD API has POST, PUT, GET-list — but no GET `/v3/extendedfields/config/{id}`. This means V3 cannot retrieve a specific field's current state to display in an admin UI without scanning the list. Also, PUT `/v3/extendedfields/config/{id}` returns the updated resource (200 with body) — but there is no way to independently fetch that resource before editing it (no GET-by-ID). Idempotency of PUT also requires knowing current state.  
**Risk Level**: MEDIUM  
**Evidence needed**: Confirm whether any UI or caller needs to fetch a single EF config by ID.  
**Recommendation**: Add GET `/v3/extendedfields/config/{id}` as a story (or at minimum as an AC on EF-US-04). Without it, the admin API surface is incomplete. Add `?name=` filter for searchability.

---

### Contradiction #20
**Source**: 00-prd.md § API Contracts (POST 409 error message)  
**Claim**: POST returns "Error 409: `(org_id, scope, name)` already exists and `is_active=1`"  
**Challenge**: The error message leaks internal DB semantics (`is_active=1`) directly into the API response. API error messages should describe the business problem, not the DB column state. The caller should receive something like "A field with this name already exists for this scope in your org." The internal `is_active=1` qualifier is an implementation detail and is confusing to an external caller (who doesn't know your DB schema). Furthermore, as noted in Contradiction #7, this message implies that a name can be reused after deactivation — which the DB schema actually prevents.  
**Risk Level**: MEDIUM  
**Evidence needed**: None — this is a design choice that should be reviewed.  
**Recommendation**: Update error message to business language: "409: Extended field with name '{name}' already exists for scope '{scope}' in your org." Remove `is_active=1` qualifier. This also forces resolution of the fundamental schema question from Contradiction #7.

---

### Contradiction #21
**Source**: 00-ba.md § EF-US-03 (Deactivate) AC; 00-prd.md § Grooming Questions GQ-03 resolution  
**Claim**: BA EF-US-03 AC: "Already inactive → `409 CONFLICT` or idempotent success (Architect to decide)." GQ-03 resolved as: "Idempotent: ACTIVE→INACTIVE = 200/204; already-INACTIVE = 200/204." But there is no separate DELETE endpoint per D-24 — deactivation is via `PUT is_active=false`.  
**Challenge**: The BA EF-US-03 acceptance criteria explicitly say "409 or idempotent (Architect to decide)" — but the Architect has already decided (GQ-03: idempotent). The BA was not updated. Additionally, the 200/204 ambiguity ("200/204") is never resolved — which status code is returned? 204 No Content would mean the updated resource is not returned, which contradicts the PUT contract that says "Response 200: updated LoyaltyExtendedFieldConfig." A consistent soft-delete via PUT should return 200 with the updated resource, not 204. The 204 option should be removed.  
**Risk Level**: MEDIUM  
**Evidence needed**: Confirm the existing V3 pattern for soft-delete operations — do they return 200 with body or 204 No Content?  
**Recommendation**: Resolve the 200/204 ambiguity: standardise on 200 with the updated `LoyaltyExtendedFieldConfig` body (consistent with the PUT contract specification). Update BA EF-US-03 to reflect GQ-03 resolution.

---

### Contradiction #22
**Source**: 00-prd-machine.md § validation_rules (trigger); 00-ba.md EF-US-05/06  
**Claim**: Validation trigger: "POST /v3/subscriptions OR PUT /v3/subscriptions/{id} with `extendedFields` present."  
**Challenge**: What does "with `extendedFields` present" mean exactly? The PRD specifies different behaviours for null vs absent vs empty. If the trigger is "extendedFields present in JSON body," does that mean only when the JSON key appears in the body (regardless of value), or when the value is non-null? In Java Spring with Jackson, "extendedFields not in body" and "extendedFields: null in body" both produce `null` in the DTO. If the trigger condition is "non-null extendedFields" in Java, then the trigger logic is: `if (extendedFields != null) { validate }`. But then `extendedFields: []` (empty list) also triggers validation — which then fails the mandatory fields check (R-04: mandatory fields must be present). Yet the spec says `[]` should "clear all EF values" — implying no mandatory field enforcement for the empty list case. There is a missing condition: "if extendedFields is empty list [] → skip R-04 validation, proceed directly to clear."  
**Risk Level**: MEDIUM  
**Evidence needed**: Walk through the validation flowchart for the `extendedFields: []` case. In the prd.md Mermaid flowchart: empty list goes to "Clear all EF values" (branch D), bypassing the validation steps. But R-04 (mandatory fields check) is only in the "has entries" branch (E). This is consistent — but R-04 must be explicitly skipped for the empty list case in the code, not just the diagram.  
**Recommendation**: Add a validation rule explicitly: "R-04 does NOT apply when extendedFields is an empty list ([]). Mandatory field enforcement only applies when extendedFields contains one or more entries." This prevents a future developer from inadvertently applying R-04 to the empty list case.

---

### Contradiction #23
**Source**: 00-ba.md § EF-US-05; 00-prd-machine.md § validation_rules  
**Claim**: "value data type must match the registered `data_type`" (R-03).  
**Challenge**: The spec says values are always stored as String in MongoDB (A-03). Data type validation is application-level. But what exactly does "value data type must match" mean for a String input? For `data_type=NUMBER`, is the validation: (a) the string must be parseable as a number, (b) the string must represent an integer (not a decimal), (c) any numeric format is accepted? For `data_type=DATE`, what date format is accepted — ISO-8601 only? Any parseable date? For `data_type=BOOLEAN`, is "true"/"false" accepted, or "1"/"0", or "TRUE"/"FALSE"? These are not specified. An implementer will make different assumptions than a caller. This is a validation gap that will cause production incidents when callers send "True" instead of "true" or "1.5" instead of "1".  
**Risk Level**: MEDIUM  
**Evidence needed**: Check whether the existing `ExtendedFieldsData` struct in EMF Thrift has any type validation logic that can be reused.  
**Recommendation**: Add explicit format specifications for each data_type. Minimum: NUMBER (parseable as Java Double.parseDouble, scientific notation acceptable), BOOLEAN (case-insensitive "true"/"false" only), DATE (ISO-8601 only: `yyyy-MM-dd`). Add these as sub-rules under R-03 in prd-machine.

---

### Contradiction #24
**Source**: 00-prd.md § Data Model (`created_on DATETIME NOT NULL`); session-memory.md Constraints (cc-stack-crm convention uses `auto_update_time`)  
**Claim**: Schema uses `last_updated_on DATETIME NOT NULL`. Session-memory says the cc-stack-crm convention (from `custom_fields.sql` pattern) uses `auto_update_time` for the update timestamp.  
**Challenge**: The session-memory explicitly cites the `custom_fields.sql` pattern as the cc-stack-crm convention — and mentions `auto_update_time` as the audit field name. The PRD schema uses `last_updated_on`. If the convention is `auto_update_time`, the new table deviates from convention. Is `auto_update_time` an `ON UPDATE CURRENT_TIMESTAMP` auto-managed column, or is it application-managed? If `auto_update_time` is auto-managed by MySQL, the application doesn't need to set it — it just works. If `last_updated_on` is application-managed, the application must explicitly set it on every UPDATE, which is an easy source of bugs (forgetting to set it). The schema should follow the convention.  
**Risk Level**: MEDIUM  
**Evidence needed**: Read `cc-stack-crm/schema/dbmaster/warehouse/custom_fields.sql` to confirm the exact column name and DDL for the update timestamp. Confirm whether it uses `ON UPDATE CURRENT_TIMESTAMP`.  
**Recommendation**: Architect must read `custom_fields.sql` in Phase 6 and confirm whether `last_updated_on` or `auto_update_time` (with `ON UPDATE CURRENT_TIMESTAMP`) is the correct convention. If the existing convention is `auto_update_time ON UPDATE CURRENT_TIMESTAMP`, update the schema DDL accordingly.

---

## LOW Findings

---

### Contradiction #25
**Source**: 00-prd.md § API Contracts (GET response)  
**Claim**: GET response includes `totalPages: int` in the pagination envelope.  
**Challenge**: `totalPages` requires knowing the total count of rows matching the query before returning results. For large orgs with many EF definitions (say, 10,000+), a `COUNT(*)` on every paginated GET call is a performance concern. Most paginated APIs in V3 — does the existing subscription list API include `totalPages`? If so, is it a full COUNT query or approximated? If the existing pattern does not use `totalPages`, adding it here sets a precedent that's inconsistent with the rest of the platform. More importantly, totalPages is redundant if you have `totalElements` and `size`.  
**Risk Level**: LOW  
**Evidence needed**: Check whether existing V3 list/pagination endpoints include `totalPages` in their responses.  
**Recommendation**: Confirm platform-wide pagination standard. If existing APIs omit `totalPages`, omit it here too. If they include it, confirm whether it's a full COUNT or estimated.

---

### Contradiction #26
**Source**: 00-prd.md § API Contracts (POST request); 00-prd-machine.md § apis (POST request)  
**Claim**: POST request has `is_mandatory: boolean (required)`.  
**Challenge**: If `is_mandatory` has a sensible default (false — not mandatory), why is it required in the POST body? Requiring a field with an obvious default forces callers to always send it, cluttering the API. Defaults in the DB schema (`is_mandatory TINYINT(1) NOT NULL DEFAULT 0`) suggest the application should also default it. Additionally, the PRD machine marks it as `required` for the POST request, but in the Thrift `CreateLoyaltyExtendedFieldRequest` struct it is `5: required bool isMandatory`. A caller who omits `is_mandatory` from the JSON body will get a deserialisation error rather than having it default to false. This is a minor but real API usability issue.  
**Risk Level**: LOW  
**Evidence needed**: Check how existing V3 POST endpoints handle boolean fields with defaults.  
**Recommendation**: Change `is_mandatory` to optional in the API contract with a default of `false`. Update the Thrift struct to `5: optional bool isMandatory` with a default value annotation.

---

### Contradiction #27
**Source**: 00-prd.md § New Thrift Structs (getLoyaltyExtendedFieldConfigs signature)  
**Claim**: `getLoyaltyExtendedFieldConfigs(1: i64 orgId, 2: optional string scope, 3: bool includeInactive, 4: i32 page, 5: i32 size)`  
**Challenge**: Parameter 3 is `bool includeInactive` with no `optional` or default. In Thrift, a bare `bool` parameter with no default is serialised as 0 (false) if not provided. However, positional parameters in Thrift service methods that are not `optional` will cause issues with older-generated client code if this method is ever evolved. More importantly, as a service method parameter (not a struct field), there is no `required`/`optional` distinction — but having 5 positional parameters for a list/filter call is awkward; a filter struct would be more extensible.  
**Risk Level**: LOW  
**Evidence needed**: Check existing `EMFService` method signatures for pattern consistency (how are filter parameters handled in existing methods?).  
**Recommendation**: Wrap filter parameters in a `GetLoyaltyExtendedFieldRequest` struct for forward compatibility. This allows adding new filter params (e.g., `name`, `data_type`) without adding new method parameters.

---

### Contradiction #28
**Source**: 00-ba.md § Diagrams (ER diagram); 00-prd.md § Data Model  
**Claim**: ER diagram shows `loyalty_extended_fields ||--o{ SubscriptionProgram_ExtendedField : "governs via (org_id + scope + name=key)"`. This implies `name` in `loyalty_extended_fields` maps to `key` in `SubscriptionProgram.ExtendedField`.  
**Challenge**: If `name` is now mutable (D-25), the governing relationship breaks for existing subscription program documents. An org admin renames an EF from "discount_pct" to "renewal_discount_pct". All existing `subscription_programs` MongoDB documents that have `{key: "discount_pct"}` are now orphaned — they reference a key that no longer exists in `loyalty_extended_fields`. The registry says the field is called "renewal_discount_pct"; the existing subscription programs say "discount_pct". These are the same field, but validation will reject "discount_pct" as an unknown key. This is a **referential integrity violation** that arises from making the lookup key (name) mutable while not migrating existing references.  
**Risk Level**: HIGH (upgrading from preliminary LOW assessment)  
**Evidence needed**: Confirm whether any migration strategy exists for existing subscription program documents when an EF name is renamed. Confirm how the validation R-02 handles the historical name.  
**Recommendation**: This is a strong argument for making `name` **immutable** (reverting D-25). If name must be mutable, the system needs either: (a) a surrogate key reference (store `loyalty_extended_fields.id` in the subscription program doc, not the name), OR (b) a migration job that updates all existing subscription program documents when a name is changed. Both are significantly more complex than stated. D-25 (name is mutable) should be escalated to CRITICAL scope decision requiring explicit product sign-off.

---

## Cross-Cutting Concerns Not Addressed in Any Artifact

**CCC-01 — Authentication scope**: All EF Config CRUD endpoints require "org-level authentication" (G-03). But what role within the org? Can any authenticated user of an org create/delete EF definitions? Or is it restricted to org admin? The BA says "org admin" but no enforcement mechanism (role check) is specified in any acceptance criterion.

**CCC-02 — Audit trail gap**: Audit Log is deferred (D-04). But renaming an EF (D-25 mutable name) and deactivating an EF are consequential administrative actions that affect all subscription create/update calls for that org. Without an audit trail, there is no way to diagnose "why did subscription creates start failing?" if an EF was quietly deactivated. The deferral of audit logging should be revisited given D-25.

**CCC-03 — Multi-region/multi-DC**: No mention of how the `loyalty_extended_fields` table and `program_config_key_values` are replicated. If EMF reads from a replica with replication lag, a newly created EF definition may not be visible to validation lookups for seconds. This is an especially acute problem immediately after an EF is created and the caller immediately tries to use it in a subscription create.

**CCC-04 — Thrift exception mapping**: `EMFException` is thrown by all new service methods. What error codes does `EMFException` carry? How does V3 map `EMFException` error codes to HTTP status codes (400, 404, 409)? This mapping is not specified anywhere. Without it, V3 will receive an `EMFException` and either propagate it as 500 or need a brittle string-matching on the exception message.

---

*End of Critic Review — 28 contradictions + 4 cross-cutting concerns identified.*
