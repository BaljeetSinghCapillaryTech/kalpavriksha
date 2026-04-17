# Code Analysis — thrift-ifaces-pointsengine-rules
> Repo: /Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules
> Generated: Phase 5, 2026-04-18

---

## Key Architectural Insights

1. **Single IDL, single service, no split files.** The entire contract lives in one file: `pointsengine_rules.thrift`. All loyalty CRUD — programs, slabs, promotions, strategies, partner programs, benefits, limits, alternate currencies — is multiplexed through the single `PointsEngineRuleService`. This means all new BenefitCategory methods will be **added to the same service** (no new service file needed in MVP; a new file is possible but breaks the pattern).

2. **The legacy Benefits service pattern is already here.** `BenefitsConfigData` struct + `createOrUpdateBenefits` / `getConfiguredBenefits` / `getBenefitsById` / `getAllConfiguredBenefits` sit at lines 692-1282 of the IDL. This is the **exact template to follow** for the new `BenefitCategory` CRUD methods. Method naming, orgId as explicit parameter, `serverReqId` as last string parameter — all patterns are locked in.

3. **`orgId` is always an explicit `i32` parameter** in every method (with two anomalous `i64` exceptions only in `LimitConfigData` — a newer struct, likely an inconsistency). The dominant platform convention is `i32 orgId`.

4. **`i64` for timestamps, bare field names (no `_millis` suffix).** `createdOn`, `updatedOn`, `modifiedOn`, `startDate`, `endDate` — all typed as `i64`, none with `_millis` suffix. The `BenefitsConfigData` struct is the one outlier: `createdOn` is a `string` (field 11) AND `createdOnInMillis` is an `i64` (field 14) — this is a migration artefact, not the convention.

5. **No backward-compatibility README/CONTRIBUTING.** No explicit policy document. The Thrift expand-then-contract rule (G-05.4) must be self-enforced.

---

## 1. Repo Structure

**Files (non-.git):**
```
/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/
├── pointsengine_rules.thrift   ← SINGLE IDL file, entire loyalty contract
├── pom.xml                     ← Maven build, version 1.84-SNAPSHOT
├── .gitignore                  ← /gen is gitignored
├── .pre-commit-config.yaml     ← gitleaks secret scanning only
└── .github/workflows/
    ├── gitleaks_secret_scan.yml
    ├── pr-title-check.yml      ← enforces CAP-NNNN in PR title
    └── pr-detailing-test-case-check.yml ← enforces Confluence + Sheets links
```

**Structure characterization:** Pure IDL-only. No hand-written Java wrappers. Generated Java lands in `gen/` (gitignored — compiled from IDL by the Thrift compiler during `mvn generate-sources`).

**Build system:** Maven (`maven-antrun-plugin`, version 1.7). Thrift code generation runs in the `generate-sources` phase:
```xml
<exec executable="thrift" failonerror="true">
  <arg value="-r" />
  <arg value="-o" />
  <arg value="${project.build.directory}" />
  <arg value="--gen" />
  <arg value="java" />
  <!-- also generates: php, php:server, js:node, py:new_style,utf8strings -->
  <arg value="pointsengine_rules.thrift" />
</exec>
```
The `<directory>${basedir}/gen</directory>` + `<sourceDirectory>${basedir}/gen</sourceDirectory>` means the **generated Java IS the compiled source** — there is no separate `src/main/java`. A Python post-processor runs on the Node.js output but is skipped by default (`skip.nodejs.postprocessing=true`).

**Namespace:** `com.capillary.shopbook.pointsengine.endpoint.api.external` (Java), `pointsengine_rules` (PHP).

**Languages generated:** Java, PHP, PHP server, Node.js, Python.

---

## 2. Existing IDL Files (Loyalty-Relevant)

There is exactly **one** `.thrift` file in this repo: `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift`

Key loyalty-relevant structs and their line ranges:

| Struct/Enum | Lines | Relevance |
|-------------|-------|-----------|
| `SlabInfo` | 352-361 | The "tier" struct: `i32 id`, `i32 programId`, `i32 serialNumber`. Template for slab-scoped entities. |
| `ProgramInfo` | 431-457 | `i32 id`, program-level container. |
| `BenefitType` enum | 682-685 | `POINTS`, `VOUCHER` — legacy benefit types only. |
| `LinkedProgramType` enum | 687-690 | `PARTNER`, `LOYALTY` |
| `BenefitsConfigData` | 692-707 | The legacy Benefits struct — **direct template** for the new BenefitCategoryDto shape. |
| `PointsCategory` | 544-553 | Points category struct: `i32 id`, `i32 orgId`, `i32 programId`. Another template. |
| `PointsCategoryType` | 537-542 | `REGULAR_POINTS`, `TRACKERS`, etc. Pattern for categoryType enum. |
| `ACCategoryType` | 882-886 | `REGULAR`, `PROMISED`, `EXTERNAL_TRIGGER_BASED` — alternate-currency category type. |
| `AlternateCurrencyData` | 895-908 | Uses `AttributionInfo` (i64 createdOn/updatedOn). |
| `AttributionInfo` | 37-44 | The richest audit struct: `i64 createdOn`, `i64 createdBy`, `i64 updatedOn`, `i64 updatedBy`, `optional i64 publishedOn`, `optional i64 publishedBy`. |
| `CappingConfig` | 770-786 | Has `i64 createdOn`, `i64 updatedOn`, `i32 createdBy`, `i32 updatedBy` inline. |
| `PointsEngineRuleServiceException` | 10-13 | The single exception type in the IDL. |

**Service:** One service — `PointsEngineRuleService` (line 1029), ~60 methods covering all loyalty domain operations.

**File-level imports:** None — this is a self-contained single file.

---

## 3. Recommended Host Service for New Benefit Category Methods

**Recommendation: Add to the existing `PointsEngineRuleService` in `pointsengine_rules.thrift`.**

Confidence: C7 (direct code evidence from the existing `BenefitsConfigData` / `createOrUpdateBenefits` / `getConfiguredBenefits` pattern in the same service at lines 1276-1282).

**Analysis of all options:**

| Option | Assessment |
|--------|------------|
| (a) Separate SlabService | No SlabService exists. Slabs are in the same `PointsEngineRuleService` (`getAllSlabs`, `createOrUpdateSlab`, `createSlabAndUpdateStrategies`). |
| (b) Separate ProgramService | No ProgramService exists. Program methods are in the same service (`getProgram`, `getAllPrograms`, `updateProgram`). |
| (c) Separate BenefitsService | No separate BenefitsService exists. The legacy `Benefits` CRUD (`createOrUpdateBenefits`, `getConfiguredBenefits`, `getBenefitsById`, `getAllConfiguredBenefits`) is already part of `PointsEngineRuleService`. |
| **(d) Add to PointsEngineRuleService (recommended)** | **Pattern-match: every loyalty entity — Slabs, Programs, Promotions, Strategies, PointsCategories, Benefits, TenderCombinations, PartnerPrograms, CappingConfigs, Limits, AlternateCurrencies — is served through one multiplexed service. The existing `BenefitsConfigData` CRUD is the exact template.** |
| (e) New BenefitCategoryService | Possible but breaks the established mono-service pattern. Would require creating a new `.thrift` include chain (or second file). Zero precedent in this repo. |

**Existing `BenefitsConfigData` CRUD method set (the direct template at lines 1276-1282):**
```thrift
BenefitsConfigData createOrUpdateBenefits(1: BenefitsConfigData configData, 2: string serverReqId)
    throws (1 :PointsEngineRuleServiceException ex);

list<BenefitsConfigData> getConfiguredBenefits(1: i32 orgId, 2: i32 programId, 3: LinkedProgramType type, 4: string serverReqId)
    throws (1 :PointsEngineRuleServiceException ex);

BenefitsConfigData getBenefitsById(1: i32 orgId, 2: i32 id, 3: string serverReqId)
    throws (1 :PointsEngineRuleServiceException ex);

list<BenefitsConfigData> getAllConfiguredBenefits(1: i32 orgId, 2: string serverReqId)
    throws (1 :PointsEngineRuleServiceException ex);
```

**Naming conventions observed in service:**
- Create/upsert: `createOrUpdate<Entity>(…)` (dominant pattern: `createOrUpdateSlab`, `createOrUpdateStrategy`, `createOrUpdatePromotion`, `createOrUpdateBenefits`)
- Get by ID: `get<Entity>ById(…)` or `get<Entity>(1:i32 id, …)`
- Get all: `getAll<Entities>(1:i32 orgId, …)` or `getConfigured<Entities>(…)`
- Create-specific: `create<Entity>(…)` for TenderCombination — no update on separate method
- No explicit `delete` methods exist for any entity — consistent with D-13 soft-delete

---

## 4. Timestamp Conventions

**Pattern: All timestamps are `i64`, filed as bare camelCase field names with `On` suffix — never `_millis` suffix.**

Evidence from `.thrift` file:

| Pattern | Example fields | Lines |
|---------|---------------|-------|
| `i64 createdOn` | `AttributionInfo`, `RuleInfoV2`, `RulesetInfoV2`, `CappingConfig` | 38, 270, 295, 781 |
| `i64 updatedOn` | `CappingConfig` | 782 |
| `i64 modifiedOn` | `RuleInfoV2`, `RulesetInfoV2`, `TenderCombination`, `TrackerCondition`, `PointsCategory`, `ChangeInfo` | 275, 298, 476, 529, 551, 765 |
| `i64 publishedOn` | `AttributionInfo` | 42 |
| `i64 startDate`, `i64 endDate` | `PromotionInfo`, `RuleInfoV2`, `RulesetInfoV2`, `LimitPeriodConfigData` | 198-199, 268-269, 293-294 |
| `i64 addedOn` | `ExpiryExtensionConfig` | 670 |
| `i64 expiryDate` | `ExpiryRestrictions`, `PartnerProgramInfo` | 107, 401 |

**The `BenefitsConfigData` anomaly** (lines 703, 706): `createdOn` is `required string` (field 11) alongside `optional i64 createdOnInMillis` (field 14). This was a backwards-compatible field addition — field 14 added later when the team needed millis. It is **explicitly a migration artefact**, not a naming convention.

**Comment convention:** Zero instances of inline comments documenting "epoch millis UTC" or unit. There is no `/* epoch millis */` annotation anywhere. The unit convention is implicit — confirmed by `Date.getTime()` Java pattern and `optInStartDate`/`optInEndDate` field names matching Java `LoyaltyConfigMetaData` usage.

**Summary for OQ-41:** Use bare field name with `On` suffix: `createdOn`, `updatedOn` — not `createdOnMillis`, not `createdOnEpoch`. Type: `i64`. No doc comment required by convention (but one is recommended per D-24 for future maintainers).

---

## 5. ID Type Conventions

**Dominant convention: `i32` for all loyalty-domain IDs.**

Evidence:
- `SlabInfo.id` — `required i32` (line 354) — confirmed from session-memory C7 evidence
- `SlabInfo.programId` — `required i32` (line 355)
- `BenefitsConfigData.orgId` — `required i32` (line 693)
- `BenefitsConfigData.programId` — `required i32` (line 694)
- `BenefitsConfigData.id` — `optional i32` (line 704)
- `PointsCategory.id` — `required i32` (line 545)
- `PointsCategory.orgId` — `required i32` (line 546)
- `PointsCategory.programId` — `required i32` (line 547)
- `ProgramInfo.id` — `required i32` (line 432)

**Anomaly: `LimitConfigData` uses `i64 orgId` and `i64 id`** (lines 942-954). This is an isolated newer struct (Limits feature). All other structs use `i32`. This anomaly is NOT to be followed for BenefitCategory.

**Conclusion for OQ-23 / D-18 cascade:**  
`BenefitCategoryDto` MUST use `i32 id`, `i32 orgId`, `i32 programId`, `i32 slabId` — full parity with `SlabInfo`, `BenefitsConfigData`, `PointsCategory`. Using `i64` would be inconsistent with 95%+ of the IDL and would break join semantics at EMF handler layer. Confidence: C7.

---

## 6. Exception Conventions

**The entire IDL defines exactly ONE exception type:**

```thrift
exception PointsEngineRuleServiceException {
    1: required string errorMessage;
    2: optional i32 statusCode;
}
```
(Lines 10-13)

Every single service method in `PointsEngineRuleService` has the same throws clause:
```thrift
throws (1: PointsEngineRuleServiceException ex)
```

**Implications for OQ-36:**
- There is no `InvalidArgumentException`, `ResourceNotFoundException`, `AccessDeniedException`, or typed exception hierarchy in this IDL. All errors are collapsed into `PointsEngineRuleServiceException` with `errorMessage` (string) and optional `statusCode` (i32).
- The `statusCode` field is how the EMF handler communicates error semantics (e.g., 400, 404, 409) back to intouch-api-v3.
- intouch-api-v3 catches `PointsEngineRuleServiceException`, reads `statusCode`, and maps to HTTP status codes for the `ResponseWrapper<T>` envelope.
- No new exception types need to be defined. New BenefitCategory methods MUST throw `PointsEngineRuleServiceException`.

---

## 7. Backward Compatibility Rules

**No README/CONTRIBUTING document found in the repo.** The `.pre-commit-config.yaml` only configures gitleaks (secret scanning). The `.github/workflows/` only enforces PR title format (CAP-NNNN) and Confluence/Sheets links in PR descriptions — no IDL structural checks.

**Observed practices from the IDL itself:**
- Fields are never removed — all historical fields remain in every struct.
- New fields are added as `optional` with increasing field numbers (e.g., `BenefitsConfigData` field 14 `createdOnInMillis` added after field 11 `createdOn`).
- No `@deprecated` markers exist anywhere in the IDL (searched: zero matches).
- The `PromotionInfo` struct has a comment `/* If any changes in PromotionInfo, please keep campaigns team in loop */` — the only cross-team dependency comment in the file.

**Backward-compatibility rule for new BenefitCategory structs (from G-05.4 + observed IDL practice):**
- All new fields in existing structs MUST be `optional`.
- Never change an existing field's type.
- Never reuse a field number.
- New methods added to the service are backward compatible (Thrift service evolution is additive by default).
- Since all new work is in a new struct (`BenefitCategoryDto`, `BenefitCategorySlabMappingDto`) + new methods on the existing service, there is zero backward-compatibility risk to existing clients.

---

## 8. Org Scoping in Thrift

**`orgId` is always an explicit parameter — it is NOT implicit/connection-context.**

Every method that needs org scoping passes `orgId` explicitly, either:
1. **As a standalone method parameter:** `getAllSlabs(1:i32 programId, 2:i32 orgId, 3:string serverReqId)`, `getBenefitsById(1: i32 orgId, 2: i32 id, 3: string serverReqId)`
2. **Embedded in a filter/request struct:** `PromotionsFilter.orgId`, `OrgProgramFilter.orgId`, `AlternateCurrencyFilter.orgId`

No session/connection-level org context exists. Every method is stateless with respect to org.

**Consequence for new BenefitCategory methods:** All new service methods MUST include explicit `i32 orgId` as a parameter (or embedded in a request struct). The `orgId` is injected by intouch-api-v3 from `IntouchUser.orgId` (the authenticated principal) before making the Thrift call.

**Note on parameter ordering:** There is mild inconsistency in the IDL — some methods put `programId` first and `orgId` second (e.g., `getAllSlabs(1:programId, 2:orgId)`), others put `orgId` first (e.g., `getPromotionAndRulesetInfo(1:orgId, 2:programId)`). The `getBenefitsById(1:orgId, 2:id)` pattern puts `orgId` first. For new methods, use the `orgId`-first convention (matches the majority of newer methods).

---

## 9. Enum Patterns

**Existing `BenefitType` enum (lines 682-685):**
```thrift
enum BenefitType {
    POINTS,
    VOUCHER
}
```
This covers the **legacy** Benefits entity. It is NOT a CategoryType enum.

**`PointsCategoryType` enum (lines 537-542):**
```thrift
enum PointsCategoryType {
    REGULAR_POINTS,
    TRACKERS,
    PROMISED_POINTS,
    EXTERNAL_TRIGGER_BASED_POINTS
}
```
This is the closest analogue to a "CategoryType" — used on `PointsCategory` struct.

**`ACCategoryType` enum (lines 882-886):**
```thrift
enum ACCategoryType {
    REGULAR,
    PROMISED,
    EXTERNAL_TRIGGER_BASED
}
```
For alternate-currency category types.

**No `EntityType` enum that includes loyalty entity types** — there is a `MappedEntityType` (CONCEPTS, ZONES, CARD_SERIES) and `AuditTrackedClass` (which lists auditable class names including `ProgramSlab`, `Promotion`, `Strategy`, etc.) but neither is an extensible entity-type registry.

**`AuditTrackedClass` enum** (lines 829-848): This enum WILL need a `BenefitCategory` value added to it if BenefitCategory CRUD operations are to be audited via the existing `getAuditLogDetails` service method.

**For new feature — new enum needed:**
```thrift
enum BenefitCategoryType {
    BENEFITS
}
```
This is a **new enum** — nothing equivalent exists. It follows the `PointsCategoryType` pattern (ALL_CAPS values).

---

## 10. Build & Release

**Maven coordinates:** `com.capillary.commons:thrift-ifaces-pointsengine-rules:1.84-SNAPSHOT`

**Parent POM:** `com.capillary:maven-parent:2.0.0`

**Version pattern:** `1.84-SNAPSHOT` → current development. Release tags observed: `v1.75` through `v1.83`. Each release increments the minor version (e.g., `1.83` → `1.84`).

**Release workflow (from git log):**
1. Feature branch created from `main` (e.g., `aidlc/CAP-185145`)
2. PR merged to `main` with CAP-NNNN in title
3. Release branch created (e.g., `release/1.84`) when sprint ships
4. Version bumped in pom.xml (`1.84-SNAPSHOT` → `1.84` → `1.85-SNAPSHOT`)
5. Maven deploy to Artifactory (inferred from `maven-parent` setup — standard Capillary internal Artifactory)

**Downstream consumers needing a version bump after IDL changes:**
- **emf-parent**: Depends on this artifact to implement the service. Needs pom.xml version update to consume new method stubs.
- **intouch-api-v3**: Depends on this artifact to call the service as a client. Needs pom.xml version update (currently on 1.83 per cross-reference).

**Confirmed workflow:** Modify `pointsengine_rules.thrift` → bump version in pom.xml → PR to main → release → downstream repos update their dependency version.

---

## Answers to Phase 4 Residual Questions

**OQ-35: Existing EMF Thrift handler template**
The `BenefitsConfigData` / `createOrUpdateBenefits` / `getConfiguredBenefits` cluster is the direct handler template. The service method signatures follow the `createOrUpdate<Entity>(1:StructType data, 2:string serverReqId)` pattern with `throws (1: PointsEngineRuleServiceException ex)`. The EMF handler for `createOrUpdateBenefits` is the code to copy for BenefitCategory CRUD. Confidence: C7.

**OQ-36: Error envelope Thrift ↔ REST**
The Thrift layer throws `PointsEngineRuleServiceException { errorMessage: string, statusCode: i32 }`. intouch-api-v3 catches this and maps `statusCode` → HTTP status → `ResponseWrapper<T>`. No typed exceptions exist. The `statusCode` field is the discriminator for 400 vs 404 vs 409. Phase 7 Designer must specify: what `statusCode` values the new handler sets for: (a) category not found, (b) duplicate name/mapping (active), (c) deactivation of already-inactive row, (d) slab not found. Confidence: C7 (pattern confirmed; specific codes are a Phase 7 design decision).

**OQ-39: i64 timestamp unit**
Confirmed milliseconds by convention — `Date.getTime()` Java pattern maps zero-cost to `i64`. The `BenefitsConfigData.createdOnInMillis` field (explicit `InMillis` suffix) was added as a migration-era explicit field — confirming the base convention is epoch milliseconds even without the suffix. Confidence: C7.

**OQ-41: Thrift field naming for timestamps**
Convention: bare camelCase with `On` suffix — `createdOn`, `updatedOn`. No `_millis` or `Epoch` suffix. No `_at` suffix. `modifiedOn` is also used for update timestamps in several structs. The `BenefitsConfigData.createdOnInMillis` is an anomaly (migration artefact), not a naming template. **Recommendation for new structs:** use `createdOn` and `updatedOn` (matching `CappingConfig` at lines 781-782, which is the most recently added struct with both fields inline). Confidence: C7.

---

## New Thrift Surface (Proposed for Phase 6 Architect)

### New Enum
```thrift
enum BenefitCategoryType {
    BENEFITS
}
```

### New Structs
```thrift
struct BenefitCategoryDto {
    1: required i32 id;
    2: required i32 orgId;
    3: required i32 programId;
    4: required string name;
    5: required BenefitCategoryType categoryType;
    6: required bool isActive;
    7: required i64 createdOn;
    8: required string createdBy;
    9: optional i64 updatedOn;
    10: optional string updatedBy;
}

struct BenefitCategorySlabMappingDto {
    1: required i32 id;
    2: required i32 orgId;
    3: required i32 benefitCategoryId;
    4: required i32 slabId;
    5: required bool isActive;
    6: required i64 createdOn;
    7: required string createdBy;
    8: optional i64 updatedOn;
    9: optional string updatedBy;
}

struct BenefitCategoryFilter {
    1: required i32 orgId;
    2: required i32 programId;
    3: optional bool includeInactive;
}
```

**Note on `createdBy`/`updatedBy` type:** The IDL has inconsistency — `AttributionInfo` uses `i64 createdBy` (user ID), while `BenefitsConfigData` uses `i32 createdBy` (line 702) and `LiabilityOwnerInfo` uses `i32 createdBy`. D-23 specifies `created_by VARCHAR(...)` in the DB, implying a string username/email. For the Thrift struct, recommend `string createdBy` to carry the username string from `IntouchUser` — matches the purpose (audit trail requires human-readable identity, not a raw user ID that requires a second lookup). **CROSS-REFERENCE CONFLICT WITH emf-parent**: emf-parent's `Benefits.createdBy` is `int` (user ID), not string. Phase 6 Architect MUST resolve: use `int` (match EMF pattern) or `string` (match D-23 DB schema) — this is a meaningful inconsistency.

### New Service Methods (to append to `PointsEngineRuleService`)
```thrift
/* Benefit Category CRUD — CAP-185145 */

BenefitCategoryDto createBenefitCategory(
    1: BenefitCategoryDto benefitCategory,
    2: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategoryDto getBenefitCategoryById(
    1: i32 orgId,
    2: i32 id,
    3: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

list<BenefitCategoryDto> getBenefitCategoriesByProgram(
    1: BenefitCategoryFilter filter,
    2: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategoryDto updateBenefitCategory(
    1: BenefitCategoryDto benefitCategory,
    2: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategoryDto deactivateBenefitCategory(
    1: i32 orgId,
    2: i32 id,
    3: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

/* Slab Mapping CRUD */

BenefitCategorySlabMappingDto createBenefitCategorySlabMapping(
    1: BenefitCategorySlabMappingDto mapping,
    2: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

list<BenefitCategorySlabMappingDto> getMappingsByCategory(
    1: i32 orgId,
    2: i32 benefitCategoryId,
    3: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);

BenefitCategorySlabMappingDto deactivateBenefitCategorySlabMapping(
    1: i32 orgId,
    2: i32 id,
    3: string serverReqId
) throws (1: PointsEngineRuleServiceException ex);
```

**Note on naming:** The IDL has two patterns — `createOrUpdate<Entity>` (upsert, dominant) and separate `create` + `update` (TenderCombination only). Since BenefitCategory has distinct create vs update semantics (create generates a new PK, update patches an existing row), and D-27's terminal-deactivation makes upsert semantically ambiguous, separate `create`/`update`/`deactivate` methods are cleaner and match the newer `AlternateCurrencyData` direction. However, `createOrUpdateBenefitCategory` is also defensible for simplicity. Phase 7 Designer to decide.

### New Exception Types
None required. All methods MUST use the existing `PointsEngineRuleServiceException`. The `statusCode` field carries HTTP-analogue codes:
- `statusCode = 400` → bad request (invalid programId, invalid slabId, etc.)
- `statusCode = 404` → category/mapping not found
- `statusCode = 409` → duplicate active name/mapping, or attempt to reactivate terminal row

### AuditTrackedClass amendment
If BenefitCategory mutations are to appear in the existing audit log:
```thrift
enum AuditTrackedClass {
    // ... existing values ...
    BenefitCategory   // ADD — CAP-185145
}
```
This is optional for MVP but recommended for consistency.

---

## QUESTIONS FOR USER (confidence < C5)

**Q-T-01 (C4):** `createdBy` type in Thrift: use `string` (username from `IntouchUser`) or `i32` (userId)? The `BenefitsConfigData.createdBy` is `i32` (line 702), but `AttributionInfo.createdBy` is `i64` (line 39), and D-23 specifies `VARCHAR(...)` in the DB for the platform audit pattern. Recommendation: `string` for human-readable audit trail at the API boundary. Need confirmation before Phase 7 writes the IDL. **THIS MUST BE RESOLVED IN PHASE 6.**

**Q-T-02 (C3):** Should `AuditTrackedClass` be extended with `BenefitCategory`? This would enable the existing `getAuditLogDetails` service method to serve BenefitCategory audit history without new plumbing. However, it depends on whether EMF's `AuditService` is wired to any entity or only to specific JPA-annotated ones. Phase 7 Designer + emf-parent research (Phase 5 continuation) should clarify.

**Q-T-03 (C4):** Field numbering gap: `BenefitCategorySlabMappingDto` does not include `programId` directly (it's derivable via `benefitCategoryId → benefitCategory.programId`). Is `programId` needed as a denormalized field on `BenefitCategorySlabMappingDto` for Consumer query performance, or is the join tolerable? At D-26 SMALL scale, join is fine. Confirm.

---

## ASSUMPTIONS MADE (C5+ — to verify in Phase 7)

**A-T-01 (C6):** The new methods will be appended to the existing `PointsEngineRuleService` in `pointsengine_rules.thrift`. No new `.thrift` file is needed. Evidence: zero precedent for a second file in this repo; all loyalty entities share the single service.

**A-T-02 (C7):** `i32` for all IDs (`id`, `orgId`, `programId`, `slabId`) in the new structs. Evidence: `SlabInfo`, `BenefitsConfigData`, `PointsCategory` all use `i32`. The `LimitConfigData` `i64` anomaly is intentionally NOT followed.

**A-T-03 (C7):** `i64` timestamps named `createdOn` and `updatedOn` (bare, no `_millis` suffix). Unit: epoch milliseconds. Evidence: `CappingConfig` (lines 781-782) is the canonical recent inline pattern.

**A-T-04 (C7):** Only exception type: `PointsEngineRuleServiceException`. No new exceptions. `statusCode` i32 field carries HTTP-analogue codes.

**A-T-05 (C6):** Version bump required. Downstream emf-parent + intouch-api-v3 must update their `thrift-ifaces-pointsengine-rules` dependency version in their pom.xml files after this IDL change is released. This is a mandatory cross-repo coordination step (D-18, Cross-Repo Coordination table).

**A-T-06 (C5):** The repo does NOT validate backward compatibility of IDL changes in CI (no Buf, no schema registry check). The expand-then-contract discipline (G-05.4) is entirely engineer-enforced. New methods are safe to add. New `optional` fields on existing structs are safe. No field removal or renaming is ever safe.

---

## Files Referenced

- `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift` — the single IDL source; all findings derive from this file
- `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/pom.xml` — build config, version, Maven deploy setup
- `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/.gitignore` — confirms `gen/` is not committed
- `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/.pre-commit-config.yaml` — only gitleaks; no IDL compatibility check
- `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/.github/workflows/pr-title-check.yml` — PR gate: CAP-NNNN title required
- `/Users/anujgupta/IdeaProjects/thrift-ifaces-pointsengine-rules/.github/workflows/pr-detailing-test-case-check.yml` — PR gate: Confluence + Google Sheets links required

---

**Phase 5 thrift-ifaces research complete.** The single `pointsengine_rules.thrift` IDL was fully read and analyzed; all 10 research areas are answered at C6-C7 confidence; OQ-35, OQ-36, OQ-39, and OQ-41 are resolved; and a concrete proposed Thrift surface (structs, enum, 8 service methods) conforming to the established IDL conventions is ready for Phase 6 Architect review.
