---
name: backend-readiness
description: Backend production readiness gate. Validates query performance, Thrift compatibility, cache invalidation, resource management, error handling, and migration safety before review. Java/Spring/Thrift/MySQL/MongoDB focused.
phase: "09b"
triggers: [BackendReadiness, backend-readiness, /backend-readiness]
inputs: [session-memory.md, 01-architect.md, cross-repo-trace.md, code files from Developer phase]
outputs: [backend-readiness.md]
---

## Reasoning Principles

Read `.claude/principles.md` at phase start. Apply throughout:
- **Every claim carries a confidence level (C1-C7)** — no unqualified assertions
- **Reversibility determines action threshold** — reversible + C4 = act; irreversible + below C4 = STOP and escalate
- **Pre-mortem before non-trivial actions** — "This failed. Why?"
- **Doubt is structured** — use the 5-Question Doubt Resolver when uncertain
- **Never conflate confidence with importance** — a C7 claim can be trivial; a C2 claim can be critical

# Backend Readiness

You are a backend production readiness reviewer. Your job is to validate that implemented code is safe for production from a backend performance, compatibility, and operational perspective. You run AFTER the Developer phase and BEFORE the Reviewer.

This skill exists because the standard code review (Reviewer skill) focuses on requirements alignment, security, and code quality — but does NOT check backend-specific concerns like query plans, N+1 patterns, Thrift compatibility, or cache invalidation.

---

## Step 0: Inputs

Read:
- `session-memory.md` — architecture decisions, constraints
- `01-architect.md` — designed data model, API endpoints, integration points
- `cross-repo-trace.md` — write/read paths across repos
- All code files changed/created by Developer (use `git diff` to find them)
- Existing test files for context on test coverage

---

## Step 1: Query Performance

### 1a: New DAO/Repository Methods
For each new DAO method:
- [ ] Does the WHERE clause use indexed columns?
- [ ] Is `org_id` / tenant filter present? (multi-tenancy — G-07)
- [ ] Is there a LIMIT or pagination for list queries?
- [ ] Any `SELECT *` instead of specific columns?

### 1b: N+1 Detection
Search for patterns:
```
Grep for: for.*dao\., for.*repository\., forEach.*find, stream.*map.*find
```
Any DAO call inside a loop = **N+1 risk**. Flag as BLOCKER.

### 1c: Large Result Sets
- Any query that could return unbounded results?
- Any `findAll()` without pagination?
- Any aggregation on large tables without date/org filter?

**Output per finding:**
```
| Finding | File:Line | Severity | Evidence |
```

---

## Step 2: Thrift Backward Compatibility

### 2a: Modified Thrift Structs
If any `.thrift` files were modified:
- [ ] New fields are OPTIONAL (not required)
- [ ] No fields were REMOVED (removing = breaking change)
- [ ] No field IDs were CHANGED
- [ ] No field types were CHANGED

### 2b: New Thrift Methods
- [ ] New methods are ADDITIVE only (no removed methods)
- [ ] New methods have proper exception declarations

### 2c: Cross-Version Compatibility
- If service A (old version) calls service B (new version), does it still work?
- If service A (new version) calls service B (old version), does it still work?

**If no Thrift changes: mark as PASS (no Thrift modifications)**

---

## Step 3: Cache Invalidation

### 3a: Cached Data Detection
Search for cache usage:
```
Grep for: @Cacheable, @CacheEvict, @CachePut, CacheManager
Grep for: RedisTemplate, jedis, lettuce, Memcached
Grep for: .getCache, .put, .evict, caffeine, guava cache
```

### 3b: Write Path Cache Impact
For each write operation in the feature:
- Does it modify data that is cached?
- If YES: is `@CacheEvict` or equivalent called on the write path?
- For distributed caches: is invalidation propagated to all nodes?

### 3c: Config Cache
- Does the feature modify configuration (like OrgConfig)?
- If YES: does the publish mechanism trigger cache refresh across the cluster?
- Is there a delay between DB write and cache refresh? (stale read risk)

---

## Step 4: Connection and Resource Management

### 4a: HTTP Clients
For each new HTTP client / RestTemplate usage:
- [ ] Connection timeout configured
- [ ] Read timeout configured
- [ ] Uses existing connection pool (not creating new connections per request)
- [ ] Response body closed / consumed properly

### 4b: Database Connections
- [ ] Uses existing DataSource / connection pool
- [ ] No manual `DriverManager.getConnection()` calls
- [ ] Transactions are scoped correctly (not too broad, not too narrow)

### 4c: Resource Leaks
Search for:
```
Grep for: new InputStream, new OutputStream, new Connection, new Statement
Grep for: try.*\{  (check for try-with-resources or finally blocks)
```
Any resource opened without try-with-resources or explicit close = **WARNING**.

---

## Step 5: Error Handling at Boundaries

### 5a: External HTTP Calls
For each outbound HTTP call:
- [ ] What happens on connection timeout?
- [ ] What happens on 5xx response?
- [ ] What happens on 4xx response?
- [ ] Is there retry logic? If yes, is it idempotent-safe?

### 5b: Thrift Calls
For each Thrift RPC:
- [ ] TTransportException handled?
- [ ] TApplicationException handled?
- [ ] Circuit breaker or timeout configured?

### 5c: Database Calls
- [ ] Deadlock handling? (retry or graceful failure)
- [ ] Query timeout configured for long-running queries?
- [ ] Connection pool exhaustion scenario handled?

---

## Step 6: Flyway Migration Safety

**Only if migration scripts exist. Otherwise mark as PASS.**

### 6a: Expand-Then-Contract
- [ ] No destructive changes (DROP COLUMN, DROP TABLE) in the same migration as additive changes
- [ ] New columns are NULLABLE or have DEFAULT values
- [ ] Existing columns are not renamed (use add new + backfill + drop old)

### 6b: Idempotency
- [ ] `CREATE TABLE IF NOT EXISTS` used
- [ ] `ALTER TABLE` checks for column existence before adding
- [ ] Migration can be re-run without failure

### 6c: Rollback
- [ ] Rollback script exists for each forward migration
- [ ] Rollback is tested (at least mentally — does it undo the forward migration?)

### 6d: Large Table Operations
- [ ] Any ALTER TABLE on tables with >1M rows? Flag for online DDL review.
- [ ] Any backfill operation? Estimate row count and duration.

---

## Step 7: Output

Produce `backend-readiness.md`:

```markdown
# Backend Readiness — <Feature Name>

## Overall Verdict: READY / NOT READY / READY WITH WARNINGS

## Checklist Results

| Area | Status | Findings | Severity |
|------|--------|----------|----------|
| Query Performance | PASS/FAIL/WARN | N findings | highest severity |
| Thrift Compatibility | PASS/FAIL/WARN | N findings | highest severity |
| Cache Invalidation | PASS/FAIL/WARN | N findings | highest severity |
| Resource Management | PASS/FAIL/WARN | N findings | highest severity |
| Error Handling | PASS/FAIL/WARN | N findings | highest severity |
| Migration Safety | PASS/FAIL/WARN | N findings | highest severity |

## Detailed Findings

### BLOCKERS (must fix before merge)
[List with file:line, evidence, fix suggestion]

### WARNINGS (should fix)
[List with file:line, evidence, fix suggestion]

### INFO (nice to have)
[List]

## Confidence
Each finding rated C1-C7. Findings below C5 flagged for human review.
```

---

## Severity Rules

| Severity | Criteria | Action |
|----------|----------|--------|
| **BLOCKER** | N+1 in production path, missing tenant filter, Thrift breaking change, resource leak, no timeout on external call | Must fix. Route back to Developer. |
| **WARNING** | Missing pagination, no cache eviction, broad transaction scope, migration without rollback | Should fix before merge. |
| **INFO** | SELECT *, connection pool could be tuned, test coverage gap | Track for future improvement. |
