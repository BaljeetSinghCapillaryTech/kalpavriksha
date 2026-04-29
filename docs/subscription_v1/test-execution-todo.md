# Subscription Programs — Defect TODO (verified by Baljeet)

Source: dev-env test run on 2026-04-29 against `https://devenv-crm.cc.capillarytech.com` (org 4000019, programId 46).
Confluence report: https://capillarytech.atlassian.net/wiki/spaces/LOYAL/pages/5518884865

These are the items the dev confirmed need fixing. Items marked **future scope** or **by-design** in the run summary are excluded.

---

## TODO

- [ ] **F-1 — Reject 400, not 500, on invalid `?status=` enum**
  Repro: `GET /v3/subscriptions/{id}?status=BOGUS` → currently `500 "Something went wrong, please try after sometime."`
  Fix: bind the query param to the `SubscriptionStatus` enum and let Spring's `MethodArgumentTypeMismatchException` surface as `400 Bad Request` via `SubscriptionErrorAdvice` (or the global advice) with a structured message like `"Invalid status: BOGUS. Allowed: DRAFT, PENDING_APPROVAL, PUBLISH_FAILED, ACTIVE, PAUSED, SNAPSHOT, ARCHIVED"`.
  Tests: T8.

- [ ] **F-2 — Reject 400, not 500, on missing/invalid `approvalStatus`**
  Repro: `POST /v3/subscriptions/{id}/approve` with body `{}` or `{"approvalStatus":"MAYBE"}` → currently `500`.
  Fix: add `@NotNull` + enum binding on the `approvalStatus` request DTO field; let `MethodArgumentNotValidException` map to `400` with field-level error list.
  Tests: T41.

- [ ] **F-3 — Reject 400, not 500, on missing required `name` at create**
  Repro: `POST /v3/subscriptions` without `name` → currently `500`.
  Fix: `@NotBlank @Size(max=255)` on `SubscriptionRequest.name`. Same general pattern as F-1 / F-2 — bean validation at the controller boundary, not deep in the service.
  Tests: T52.

- [ ] **F-4 — Enforce `duration` mandatory for SUPPLEMENTARY at create + update**
  Repro: `POST /v3/subscriptions` with `programType=SUPPLEMENTARY` and no `duration` → currently `201 Created` with `duration=null` persisted.
  Fix: add a class-level validator (or service-layer guard) that requires `duration.cycleType` and `duration.cycleValue` whenever `programType=SUPPLEMENTARY`. Reject with `400 SUBSCRIPTION.DURATION_REQUIRED`. Apply to PUT for DRAFT as well.
  Tests: T56.
  Owner-noted: dev confirmed cycle + duration are mandatory for SUPPLEMENTARY.

- [ ] **F-5 — Reminder validation: array length ≤ 2 AND each `daysBeforeExpiry` ≤ 7**
  Two independent rules, both currently silently accepted:
    1. **Array length**: `reminders.length` must be ≤ **2** (per UI validation). Currently 3+ entries are accepted.
    2. **`daysBeforeExpiry`**: each entry's `daysBeforeExpiry` must be ≤ **7** days (product requirement, raised from the prior cap of 5). Currently any positive integer is accepted (the SUB-1 happy-path I created carried `daysBeforeExpiry=30` and was persisted).
  Fix:
    - `@Size(max=2)` on the `reminders` list → reject with `400 SUBSCRIPTION.TOO_MANY_REMINDERS` ("At most 2 reminders are allowed per subscription").
    - `@Min(1) @Max(7)` on `Reminder.daysBeforeExpiry` → reject with `400 SUBSCRIPTION.REMINDER_DAYS_RANGE` ("`daysBeforeExpiry` must be between 1 and 7").
    - Apply on POST and on PUT (DRAFT, PENDING_APPROVAL).
  Tests:
    - Update T55 expectation: "6 reminders" → "3 reminders" → 400.
    - Add new T55b: `daysBeforeExpiry=8` → 400.
    - Update T4 happy-path body: use ≤2 reminders with `daysBeforeExpiry` in 1–7 range.
  Owner-noted: dev clarified the original "5" in api-handoff was the cap for `daysBeforeExpiry` (not array length); product has now raised it to 7. Array length cap is 2 per UI validation.
  Doc impact:
    - `api-handoff.md` line 164 ("Up to 5 expiry reminders") → "Up to **2** reminders. Each `daysBeforeExpiry` must be between **1 and 7**."
    - Confluence test report rows T4 and T55 need to be revised accordingly.

- [ ] **F-6 — APPROVE on a non-eligible status should return 422, not 404**
  Repro: APPROVE a sub that is in `DRAFT` or `ACTIVE` (not `PENDING_APPROVAL` / `PUBLISH_FAILED`) → currently `404 "Subscription not found"`.
  Root cause: the approve handler resolves the doc by status filter (`{id, orgId, status IN (PENDING_APPROVAL, PUBLISH_FAILED)}`); when no row matches it throws `SubscriptionNotFoundException`, which the advice maps to 404.
  Fix: split the lookup — first find the doc by `{id, orgId}` (any non-terminal status); if found but status is not eligible, throw `InvalidSubscriptionStateException` → `422`. If truly missing, keep `404`.
  Tests: T40.
  Owner-noted: dev confirmed status code update is acceptable.

- [ ] **F-7 — APPROVE comment must overwrite the prior REJECT comment**
  Repro:
    1. Create DRAFT, submit, REJECT with `{"comment":"Reject test"}` → status DRAFT, `comments="Reject test"` ✓
    2. Re-submit (no comment) → PENDING_APPROVAL
    3. APPROVE with `{"comment":"Approved for test"}` → status ACTIVE
    4. `GET /v3/subscriptions/{id}` → `comments="Reject test"` ❌ (should be `"Approved for test"`)
  Spec reference: api-handoff.md line 686 — "previous failure reason in `comments` is overwritten on success." The contract intends overwrite for `PUBLISH_FAILED → ACTIVE`; the same should apply for `PENDING_APPROVAL → ACTIVE`.
  Fix: in the APPROVE service, set `doc.comments = request.comment` unconditionally on success (and the `workflowMetadata.reviewedBy` / `reviewedAt` fields too — please verify these are being populated; my GET response did not show them).
  Verify also: REJECT after a prior APPROVE comment — symmetric overwrite expected.
  Tests: T38 (passed for fresh DRAFT → REJECT) but the audit-trail integrity is broken on subsequent transitions.

---

## Already verified as expected behavior / future scope (no action)

- T26–T32, T21, T50, T65 — PAUSE / RESUME / ARCHIVE are future scope. Approver-side cleanup currently requires manual MongoDB intervention.
- T3, T24 — EXTERNAL programs not supported for now.
- T54 — `cycleValue=0` is supported (cycle/duration mandatory but value=0 allowed).
- T10 — default GET listing returns all non-SNAPSHOT statuses (dissolves into a single listing call).
- T15 — `headerStats` dissolved into the listing API; aggregate counts surfaced inside listing response.
- T59 — only `DAYS` and `MONTHS` are supported `cycleType` values.
- T20 — second PUT updates the same forked DRAFT iteratively (n times) by design.
- T13 — sort behavior aligned with `UnifiedPromotionController`.
- T35 — SNAPSHOT is read-only audit (bin data); query-param-driven mutation rightly ignored.

---

## Cleanup needed in dev env

The validation gaps (F-4, F-5) and PUT semantics created leftover DRAFTs that can't be archived:

- `BadCycle` (DRAFT, subId=`3269d201...`)
- `NoDuration` (DRAFT, subId=`984e939c...`)
- `TooManyReminders` (DRAFT, subId=`7c867f2a...`)
- `TestSub-Lifecycle-*` family (one ACTIVE + one SNAPSHOT + one DRAFT fork "Try modify snapshot", subId=`ce1cebe8...`, partnerProgramId=121)
- `TestSub-Lifecycle-Updated (Copy)` x2 (subIds=`c5bfa082...` and `16d04b63...`)
- `Concurrent A/B` — same as `c5bfa082...` (overwritten by T22 PUTs)
- `YearsTest-*` — only attempted, never created (T59 rejected at create)

These can be removed via direct MongoDB delete (`db.subscriptionProgram.deleteMany({...})`) until ARCHIVE is implemented.
