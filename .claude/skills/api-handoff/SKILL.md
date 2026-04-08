---
name: api-handoff
description: Generates a UI-team-ready API contract document from AIDLC artifacts. Extracts endpoints, request/response shapes, error codes, auth requirements, and integration notes. Standalone utility — invoke after Designer or Developer phase. Use when user says APIHandoff:, [APIHandoff], or /api-handoff.
---

## Reasoning Principles

Read `.claude/principles.md` at phase start. Apply throughout:
- **Every claim carries a confidence level (C1-C7)** — no unqualified assertions
- **Reversibility determines action threshold** — reversible + C4 = act; irreversible + below C4 = STOP and escalate
- **Pre-mortem before non-trivial actions** — "This failed. Why?"
- **Doubt is structured** — use the 5-Question Doubt Resolver when uncertain
- **Never conflate confidence with importance** — a C7 claim can be trivial; a C2 claim can be critical

# API Handoff (UI Team Contract Document)

When invoked, adopt only this persona. Do not write production code, tests, or modify any AIDLC artifact.

## Purpose

Extract API contracts from AIDLC phase artifacts and produce a single, self-contained document that a frontend/UI team can use to start their integration work — without needing to read backend design docs, architect decisions, or session memory.

## When to Use

- After **Designer** (Phase 03) — contracts are defined but not yet implemented; UI team can start early
- After **Developer** (Phase 05) — contracts are implemented; UI team gets the final version
- Standalone — anytime the user wants to generate or refresh the API handoff doc

## Invocation

```
/api-handoff <artifacts-path>
```

If no artifacts path is provided, ask the user for one.

---

## Step 1: Discover API Surface

Read the following artifacts in order (later artifacts override earlier ones where they conflict):

1. **`01-architect.md`** — API design approach, endpoint granularity, sync/async decisions, module boundaries
2. **`03-designer.md`** — Interface signatures, controller definitions, request/response types, error types, package ownership
3. **`06-developer.md`** (if exists) — Actual implementation notes, any deviations from design
4. **`00-ba.md`** — User stories and acceptance criteria (to map endpoints back to features the UI cares about)
5. **`session-memory.md`** — Constraints and key decisions that affect API behaviour (auth, tenancy, pagination, rate limits)

For each artifact, extract:
- Every endpoint or API-facing interface (controllers, REST endpoints, GraphQL queries/mutations, gRPC services)
- Request parameters, headers, and body shapes
- Response shapes (success and error)
- Authentication and authorization requirements
- Any pagination, filtering, or sorting patterns
- Rate limits, timeouts, or retry guidance if mentioned

If `06-developer.md` exists and shows deviations from `03-designer.md`, use the Developer version as the source of truth and note the deviation.

---

## Step 2: Scan Codebase for Implemented Contracts (Optional)

If the Developer phase has completed (code exists), optionally scan the codebase to verify and enrich the contracts:

- Search for controller classes mentioned in `03-designer.md`
- Extract actual `@RequestMapping`, `@GetMapping`, `@PostMapping` etc. annotations for exact URL paths
- Read request/response DTOs or models for exact field names, types, and validation annotations
- Check for any response wrappers, error handlers, or interceptors that affect the API shape

This step is optional — skip if invoked before Developer phase. When skipped, note at the top of the output: "Generated from design artifacts — implementation may differ slightly."

---

## Step 2b: Discover Existing API Patterns from Codebase

Before writing any contract, learn how THIS project structures its APIs. Search the codebase for:

- **Response wrapper**: Does the project wrap all responses in a standard envelope (e.g., `{ "data": ..., "errors": [...] }`)? Search for response wrapper classes, `@ControllerAdvice`, or common response DTOs.
- **Error format**: How does the project structure error responses? Search for global exception handlers, error DTOs, or error response builders. Document the exact shape — frontend teams build one error handler around this.
- **Pagination pattern**: Does the project use cursor-based or offset-based pagination? What are the field names (`page`, `size`, `totalCount`, `hasMore`, `nextCursor`)? Search for existing paginated endpoints.
- **Naming convention**: Are field names camelCase or snake_case in JSON responses? Check existing DTOs or Jackson/Gson config.
- **Auth pattern**: How do existing controllers enforce auth? Header names, token format, tenant context extraction.

Document what you find as a "Project API Conventions" block at the top of the output. All endpoints in the contract must follow these conventions — do not invent a different style.

---

## Step 3: Produce the API Contract Document

Write `api-handoff.md` to the artifacts path. Structure it for a frontend developer who has zero context about the backend.

### Document Structure

```markdown
# API Contract — [Feature Name]

> Generated from AIDLC artifacts at [artifacts-path]
> Source phases: [list which artifacts were read]
> Date: [timestamp]
> Status: [Design phase — not yet implemented | Implemented — verified against code]

---

## Overview

[1-2 sentences: what this feature does from the user/UI perspective.
Derived from BA user stories — written for a frontend developer, not a backend architect.]

## Base URL and Versioning

- Base path: [e.g., /api/v1/loyalty/tiers]
- Versioning strategy: [path-based / header-based / query param]
- Content-Type: [application/json / etc.]

## Authentication

- Auth mechanism: [Bearer token / API key / OAuth2 / session-based]
- Required headers: [e.g., Authorization: Bearer <token>, X-Tenant-Id: <id>]
- Tenant context: [how multi-tenancy is handled — header, path param, token claim]

---

## Resources

Organize by domain resource (e.g., "Tiers", "Benefits", "Members"), not by raw endpoint list.
Each resource section groups all operations the UI can perform on that entity.

### [Resource Name — e.g., Tiers]

#### [HTTP Method] [Path]

**Purpose**: [what this endpoint does — one sentence, UI-perspective]

**Maps to**: [BA user story or acceptance criterion, e.g., "AC-3: Admin can create a new tier"]

**Request**:

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| [name]    | path / query / header / body | [type] | yes/no | [what it is] |

**Request Body** (if applicable):
```json
{
  "field": "type — description",
  "nested": {
    "field": "type — description"
  }
}
```

**Response — Success** (HTTP [status code]):
```json
{
  "field": "type — description"
}
```

**Response — Error Cases**:

| HTTP Status | Error Code | When | Response Body |
|-------------|------------|------|---------------|
| 400         | [code]     | [condition] | [shape] |
| 404         | [code]     | [condition] | [shape] |
| 409         | [code]     | [condition] | [shape] |

**Notes**: [any UI-relevant behaviour — caching, idempotency, async polling, etc.]

---

## Common Patterns

### Error Response Format
[Document the standard error response shape used across all endpoints]

### Pagination
[If any endpoints are paginated — document the pattern: cursor vs offset, page size limits, response envelope]

### Filtering and Sorting
[If applicable — query param conventions, supported fields]

### Async Operations
[If any endpoints return 202 Accepted — document the polling/callback pattern]

---

## Enums and Constants

[List all enum values the UI needs to know about — status codes, type values, category names, etc. These are critical for frontend dropdowns, validation, and display logic.]

| Enum | Values | Used In |
|------|--------|---------|
| [name] | [value1, value2, ...] | [which endpoints/fields] |

---

## Integration Notes

- [Any sequencing requirements — e.g., "must create tier before adding benefits"]
- [Rate limits or throttling the UI should handle]
- [Optimistic locking / ETags if applicable]
- [WebSocket or SSE endpoints for real-time updates]
- [File upload patterns if applicable]
- [Any known limitations or upcoming changes]

---

## Feature-to-Endpoint Map

| Feature / User Story | Endpoint(s) | Notes |
|----------------------|-------------|-------|
| [from BA]            | [METHOD /path] | [any UI-specific note] |
```

---

## Output Quality Rules

- **Write for the frontend developer, not the backend architect.** Use UI-centric language ("the user sees...", "the form submits...", "the list loads...") not backend language ("the service processes...", "the repository queries...").
- **Include example values in JSON bodies** — not just types. Use realistic dummy data so the UI team can build mocks immediately. Example: `"tierName": "Gold"` not `"tierName": "string"`.
- **Never omit error cases.** Frontend teams need to handle every possible error. If the design artifacts don't specify error codes, infer them from the endpoint type (CRUD → standard 400/404/409/500) and note: "Error codes inferred — verify with backend."
- **Flag unknowns explicitly.** If something is not specified in the artifacts, write `[TBD — not specified in design]` — never guess silently.
- **Keep it self-contained.** The UI team should NOT need to read `01-architect.md` or `03-designer.md`. Everything they need is in this document.

---

## Step 4: Generate OpenAPI Spec (Optional)

If the user requests it (or if the contract has 3+ endpoints), also generate `api-handoff.openapi.yaml` — an OpenAPI 3.1 spec alongside the markdown document.

This enables the UI team to:
- Import into Postman or Insomnia for testing
- Run a mock server (e.g., Prism: `prism mock api-handoff.openapi.yaml`) to start frontend development before the backend is ready
- Auto-generate TypeScript types or API client code

The YAML spec should mirror the markdown document exactly — same endpoints, same request/response shapes, same examples. Include `example` values on every field so mock servers return realistic data.

If generating the YAML is not feasible (too many unknowns, or design-phase only with incomplete details), skip and note: "OpenAPI spec not generated — too many TBD fields. Re-run after Developer phase."

---

## Return to Orchestrator

If invoked as part of the workflow or by a parent agent, return:

```
PHASE: API Handoff
STATUS: complete
ARTIFACT: api-handoff.md

SUMMARY:
- [N] endpoints documented across [M] resources
- Source: [which artifacts were read]
- Status: [design-only | code-verified]
- OpenAPI spec: [generated | skipped — reason]
- Unknowns: [count of TBD items, or "None"]
```

## Constraints
- Do not write production code, tests, or modify any existing AIDLC artifact.
- Do not invent endpoints or fields not present in the source artifacts or codebase — extract only.
- Flag all unknowns as `[TBD]` rather than assuming.
- Always include example JSON values — types alone are not enough for frontend teams.
- If both design artifacts and code exist, code is the source of truth.
