# Development Guardrails

> **Scope**: Every AIDLC skill that reads, analyses, designs, or writes code MUST follow these guardrails. This includes Architect, Analyst, Designer, QA, Developer, SDET, and Reviewer.
>
> **Enforcement**: Each skill reads this file at phase start. Violations are raised as blockers.
>
> **Last updated**: 2026-04-01

---

## How Skills Use This File

| Skill | How It Uses Guardrails |
|-------|----------------------|
| **Architect** | Designs solutions that respect these guardrails. Flags when a proposed pattern would violate one. |
| **Analyst** | Checks Architect's solution against guardrails during impact analysis. Raises blockers for violations. |
| **Designer** | Ensures interfaces and abstractions enforce guardrails structurally (e.g., tenant context in method signatures). |
| **QA** | Generates test scenarios for guardrail edge cases (timezone, NPE, concurrency, tenant isolation). |
| **Developer** | Writes code that follows every applicable guardrail. Comments `// GUARDRAIL: G-XX` when a pattern is specifically because of a guardrail. |
| **SDET** | Includes guardrail-specific test automation (e.g., multi-timezone tests, concurrent access tests). |
| **Reviewer** | Verifies guardrail compliance in final review. Blocks merge for violations. Specifically checks G-13: no `IllegalArgumentException`/`IllegalStateException` in REST code, no try-catch in controllers, validator classes exist. |

---

## G-01: Timezone & Date/Time

**Priority**: CRITICAL — This is a recently introduced cross-cutting concern. Every date, time, calendar, scheduling, evaluation, or duration logic MUST follow these rules.

### G-01.1: Store all timestamps in UTC

Every `TIMESTAMP` column in the database and every timestamp field in API request/response must be in UTC.

```java
// BAD
new Date()  // timezone-dependent on JVM default
LocalDateTime.now()  // no timezone info — ambiguous

// GOOD
Instant.now()  // always UTC
ZonedDateTime.now(ZoneId.of("UTC"))
```

**Database**: Use `TIMESTAMP WITH TIME ZONE` (PostgreSQL) or store as UTC epoch millis. Never store local times.

### G-01.2: Convert to local time only at the presentation layer

Business logic, scheduled jobs, evaluations, and batch processes operate in UTC. Conversion to the user's timezone happens in the UI or in the API response serializer — never in business logic.

```java
// BAD — business logic uses local time
if (LocalDateTime.now().getHour() == 0) { runDailyBatch(); }

// GOOD — business logic uses UTC, display converts
Instant evaluationTime = Instant.now();
ZonedDateTime userLocalTime = evaluationTime.atZone(userTimezone); // only for display
```

### G-01.3: Use `java.time` (JSR-310) — never `java.util.Date` or `SimpleDateFormat`

`java.util.Date` is mutable, timezone-unaware, and error-prone. `SimpleDateFormat` is not thread-safe.

```java
// BAD
Date date = new Date();
SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd"); // not thread-safe

// GOOD
Instant instant = Instant.now();
DateTimeFormatter formatter = DateTimeFormatter.ISO_INSTANT; // thread-safe, immutable
```

### G-01.4: Never calculate durations by subtracting local times

A 24-hour period can be 23 or 25 hours in local time due to DST.

```java
// BAD
long hours = ChronoUnit.HOURS.between(startLocal, endLocal);

// GOOD
Duration duration = Duration.between(startInstant, endInstant);
```

### G-01.5: Be explicit about date boundaries

"Today", "this month", "this year" must specify which timezone's boundary.

```sql
-- BAD — depends on DB server timezone
WHERE created_date = CURDATE()

-- GOOD — explicit UTC boundaries
WHERE created_at >= '2026-03-15T00:00:00Z' AND created_at < '2026-03-16T00:00:00Z'
```

### G-01.6: APIs accept and return ISO-8601 with timezone

```json
// BAD
{ "date": "03/15/2026" }

// GOOD
{ "createdAt": "2026-03-15T10:30:00Z" }
```

### G-01.7: Test with non-standard timezone offsets

Always test with: UTC (+00:00), IST (+05:30), NPT (+05:45), and a negative offset with DST (US/Eastern).

### G-01.8: Store user's timezone preference

When context matters, store the user's `ZoneId` (e.g., `Asia/Kolkata`, not `+05:30` — the offset can change with DST for some zones).

---

## G-02: Null Safety & Defensive Coding

**Priority**: HIGH — NPEs are the #1 runtime exception in Java. Prevent them structurally.

### G-02.1: Never return null when a collection is expected

```java
// BAD
public List<Item> getItems() { return null; }

// GOOD
public List<Item> getItems() { return Collections.emptyList(); }
```

### G-02.2: Use Optional for single-value returns that might be absent

```java
// BAD
public User findUser(String id) { return null; }

// GOOD
public Optional<User> findUser(String id) { return Optional.empty(); }
```

### G-02.3: Validate arguments at method entry points (fail fast)

```java
// BAD — null propagates deep into business logic, fails with cryptic NPE
processOrder(null, items);

// GOOD — fails immediately with a clear message
public void processOrder(String orderId, List<Item> items) {
    Objects.requireNonNull(orderId, "orderId must not be null");
    Objects.requireNonNull(items, "items must not be null");
    if (items.isEmpty()) throw new IllegalArgumentException("items must not be empty");
}
```

### G-02.4: Never swallow exceptions silently

```java
// BAD — hides the bug
catch (Exception e) { /* ignore */ }

// GOOD — log with context and re-throw or handle
catch (Exception e) {
    log.error("Failed to process order {}", orderId, e);
    throw new ServiceException("Order processing failed", e);
}
```

### G-02.5: Use specific exception types

```java
// BAD
throw new Exception("something went wrong");

// GOOD
throw new InsufficientBalanceException(accountId, requested, available);
```

### G-02.6: Close resources with try-with-resources

```java
// BAD — resource leak
InputStream is = new FileInputStream(f);
is.read();

// GOOD
try (InputStream is = new FileInputStream(f)) {
    is.read();
}
```

### G-02.7: Every switch/when must handle the default case

Enums grow over time. Unhandled cases cause silent bugs.

---

## G-03: Security

**Priority**: CRITICAL — Security guardrails are non-negotiable. Any violation is a blocker.

### G-03.1: Never concatenate user input into SQL

```java
// BAD — SQL injection
"SELECT * FROM users WHERE id = '" + userId + "'"

// GOOD — parameterized query
jdbcTemplate.query("SELECT * FROM users WHERE id = ?", userId)
```

### G-03.2: Validate and sanitize ALL input at the service boundary

Use Bean Validation (`@NotNull`, `@Size`, `@Pattern`) on DTOs. Apply allow-list validation — not deny-list.

```java
// BAD — deny-list (always incomplete)
if (input.contains("<script>")) reject();

// GOOD — allow-list (defines exactly what's acceptable)
@Pattern(regexp = "[a-zA-Z0-9_-]{3,50}") String username;
```

### G-03.3: Enforce authentication AND authorization on every endpoint

Auth checks happen server-side — never trust the frontend alone. Every endpoint must verify:
1. Is this request authenticated? (valid token/session)
2. Is this user authorized for this action? (role/permission check)

### G-03.4: Never store secrets in code or committed config files

Secrets come from Vault, AWS Secrets Manager, K8s secrets, or environment injection — never from `application.yml` in the repo.

### G-03.5: Never log sensitive data

```java
// BAD
log.info("User login: {} password: {}", user, password);

// GOOD
log.info("User authenticated: {}", user);
```

Mask PII, tokens, card numbers, passwords in all logs.

### G-03.6: Hash passwords with bcrypt/scrypt/argon2

Never use MD5, SHA-1, or SHA-256 for passwords — they're fast hashes designed for integrity, not password storage.

### G-03.7: Enforce rate limiting on public-facing endpoints

Especially auth endpoints. Token bucket or sliding window — 5 login attempts per minute per IP minimum.

### G-03.8: Never disable security controls to "make it work"

```java
// ABSOLUTE NO
ssl_verify = false
@PermitAll // on a protected endpoint
csrf().disable() // without justification
```

If security blocks something, fix the root cause — don't disable the control.

### G-03.9: Set security headers

CSP, X-Frame-Options, Strict-Transport-Security, X-Content-Type-Options on all HTTP responses.

### G-03.10: Use TLS everywhere — no plaintext HTTP between services

Even inside the network perimeter (zero trust).

---

## G-04: Performance

**Priority**: HIGH

### G-04.1: Eliminate N+1 queries

```java
// BAD — triggers a query per order
for (Order o : orders) { o.getItems(); }

// GOOD — fetch in bulk
@EntityGraph(attributePaths = "items")
// or: JOIN FETCH / WHERE id IN (:ids)
```

### G-04.2: Always paginate list endpoints

Never return unbounded collections. Use cursor-based pagination for large, frequently-changing datasets.

```java
// BAD
SELECT * FROM events

// GOOD
SELECT * FROM events WHERE id > :lastSeenId ORDER BY id LIMIT 20
```

### G-04.3: Set timeouts on every external call

HTTP, DB, cache, queue — every outbound call needs a connect timeout and read timeout. Add circuit breakers for critical dependencies.

```java
// BAD — no timeout, hangs forever if service is down
restTemplate.getForObject(url, Response.class);

// GOOD
restTemplate.setRequestFactory(factory); // factory with connectTimeout=2s, readTimeout=5s
```

### G-04.4: Add indexes for query patterns

Every `WHERE` clause and `JOIN` condition in a production query path must have a supporting index. Verify with `EXPLAIN`.

### G-04.5: Stream or batch large datasets — never load all into memory

```java
// BAD — OOM on large table
List<Row> all = repo.findAll();

// GOOD
Stream<Row> stream = repo.streamAll(); // with fetchSize hint
```

### G-04.6: Cache with explicit TTL and size limits

```java
// BAD — unbounded, no expiration
private Map<String, Object> cache = new HashMap<>();

// GOOD
Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofMinutes(5))
    .build();
```

---

## G-05: Data Integrity

**Priority**: HIGH

### G-05.1: Wrap multi-step mutations in a database transaction

```java
// BAD — partial write on crash
debit(accountA, amount);
credit(accountB, amount);  // crash here = money disappears

// GOOD
@Transactional
public void transfer(Account a, Account b, BigDecimal amount) {
    debit(a, amount);
    credit(b, amount);
}
```

### G-05.2: Use optimistic locking for concurrent updates

```java
// GOOD — JPA version field
@Version
private Long version;
// UPDATE ... SET version = 6 WHERE id = 1 AND version = 5
```

### G-05.3: Enforce constraints at the database level

`NOT NULL`, `UNIQUE`, `CHECK`, and foreign keys — not just in application code. The app is not the only writer.

### G-05.4: Make database migrations backward-compatible

Use expand-then-contract: add new column → backfill → deploy code using both → drop old column. Never rename or remove columns in a single deploy.

### G-05.5: Prefer soft deletes

```java
// BAD
DELETE FROM users WHERE id = ?

// GOOD
UPDATE users SET deleted_at = NOW() WHERE id = ?
```

---

## G-06: API Design

**Priority**: HIGH

### G-06.1: All write operations must be idempotent

Use idempotency keys for `POST` endpoints. Retries must not create duplicates.

### G-06.2: Never remove or rename fields in existing API versions

Only add. Deprecate old fields in docs. Remove in the next major version.

### G-06.3: Return structured error responses

```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Account balance too low",
    "field": "amount",
    "details": { "available": 50, "requested": 100 }
  }
}
```

### G-06.4: Use correct HTTP status codes

- `200` for success, not for errors in the body
- `404` for not found, `409` for conflicts, `422` for validation, `429` for rate limit
- `500` only for unexpected server errors

### G-06.5: Version APIs from day one

`/api/v1/resource` with migration period for breaking changes.

### G-06.6: Accept and return ISO-8601 dates with timezone

See G-01.6.

---

## G-07: Multi-Tenancy

**Priority**: CRITICAL — Capillary is a multi-tenant SaaS platform. Tenant data isolation is non-negotiable.

### G-07.1: Every database query must include a tenant filter

Enforced at the framework level (Hibernate filters, RLS, or query interceptor) — not by individual developers remembering.

```sql
-- BAD — developer forgot tenant filter
SELECT * FROM tiers WHERE program_id = ?

-- GOOD — tenant filter applied automatically
SELECT * FROM tiers WHERE program_id = ? AND org_id = :currentTenantId
```

### G-07.2: Tenant context set at request boundary, propagated automatically

Extract from JWT/header in a filter. Store in `ThreadLocal`/`RequestScope`. Auto-apply to all queries.

### G-07.3: Background jobs must carry tenant context

`ThreadLocal` is lost when work moves to a different thread. Serialize tenant ID into message/task payload. Restore before processing.

### G-07.4: Test tenant isolation explicitly

Integration test: create data as tenant A, query as tenant B, assert empty/forbidden.

### G-07.5: Logs and metrics must include tenant/org ID

"500 errors increased" → "500 errors increased for org 12345" — the difference between debugging for minutes vs hours.

### G-07.6: Rate limits and resource quotas must be per-tenant

One noisy tenant must not degrade service for others.

---

## G-08: Observability & Logging

**Priority**: HIGH

### G-08.1: Use structured logging (key-value or JSON)

```java
// BAD
log.info("User " + userId + " placed order " + orderId);

// GOOD
log.info("Order placed", kv("userId", userId), kv("orderId", orderId));
// or SLF4J: log.info("Order placed userId={} orderId={}", userId, orderId);
```

### G-08.2: Include trace/correlation IDs in every log line

Propagate via OpenTelemetry / MDC. Without trace IDs, debugging across microservices is impossible.

### G-08.3: Log the "why" not just the "what"

```java
// BAD
log.error("Order rejected");

// GOOD
log.error("Order rejected: inventory insufficient for SKU-1234, requested=5 available=2",
    kv("orderId", orderId), kv("sku", sku));
```

### G-08.4: Log at correct levels

| Level | When |
|-------|------|
| `ERROR` | Action needed — something is broken and needs attention |
| `WARN` | Concerning but not broken — potential issue |
| `INFO` | Business events — order placed, user authenticated, batch completed |
| `DEBUG` | Development details — query params, intermediate state |

### G-08.5: Never log PII in plaintext

Mask card numbers, passwords, tokens, SSN, email (show first/last chars).

### G-08.6: Emit RED metrics for every service

**R**ate (requests/sec), **E**rrors (error rate), **D**uration (latency histograms at p50, p95, p99).

---

## G-09: Backward Compatibility

**Priority**: HIGH

### G-09.1: Database schema changes must be backward-compatible with the previous app version

Old code and new code run simultaneously during rolling deploys.

### G-09.2: Deprecate before removing — minimum one release cycle

```java
@Deprecated(since = "2.3", forRemoval = true)
public void oldMethod() { ... }
```

### G-09.3: New config properties must have sensible defaults

Existing deployments that don't set the new config must continue to work.

### G-09.4: Use feature flags for risky changes

```java
if (featureFlags.isEnabled("new-payment-flow", orgId)) {
    newPaymentFlow();
} else {
    legacyPaymentFlow();
}
```

### G-09.5: Serialization format changes must be backward-compatible

Kafka/queue messages produced by old code must be consumable by new code and vice versa. Never reuse Protobuf field numbers. Add optional fields only.

---

## G-10: Concurrency & Thread Safety

**Priority**: HIGH

### G-10.1: Prefer immutable shared state

```java
// BAD — mutable shared state
private Map<String, Object> cache = new HashMap<>(); // accessed from multiple threads

// GOOD
private final ConcurrentHashMap<String, Object> cache = new ConcurrentHashMap<>();
// or immutable snapshot: Collections.unmodifiableMap(...)
```

### G-10.2: Keep critical sections minimal — no I/O inside locks

```java
// BAD — holds lock during HTTP call
synchronized(this) {
    result = httpClient.call(url);  // seconds of blocking
    cache.put(key, result);
}

// GOOD
result = httpClient.call(url);  // no lock
synchronized(this) {
    cache.put(key, result);  // lock only for the mutation
}
```

### G-10.3: Acquire locks in consistent global order

If locking multiple resources, always lock in the same order (e.g., lower ID first) to prevent deadlocks.

### G-10.4: Use bounded queues for thread pools

```java
// BAD — unbounded queue, OOM under load
new ThreadPoolExecutor(10, 10, 0, SECONDS, new LinkedBlockingQueue<>());

// GOOD
new ThreadPoolExecutor(10, 10, 0, SECONDS, new LinkedBlockingQueue<>(1000),
    new CallerRunsPolicy());
```

### G-10.5: Handle InterruptedException correctly

```java
// BAD — swallows interrupt
catch (InterruptedException e) { /* ignore */ }

// GOOD — restores interrupt flag
catch (InterruptedException e) {
    Thread.currentThread().interrupt();
    throw new RuntimeException("Thread interrupted", e);
}
```

---

## G-11: Testing Requirements

**Priority**: HIGH

### G-11.1: Every bug fix must include a regression test

A test that fails before the fix and passes after — proving the fix works and preventing regression.

### G-11.2: Test edge cases — nulls, empty, boundaries, zero, negative, max

```java
// Not just the happy path
testCalculateDiscount(100);

// Also:
testCalculateDiscount(0);
testCalculateDiscount(-1);
testCalculateDiscount(Integer.MAX_VALUE);
testCalculateDiscount(null);
```

### G-11.3: Integration tests must use real databases

Use Testcontainers — not mocked repositories. Mocked repos don't catch SQL errors, constraint violations, or query bugs.

### G-11.4: Test idempotency

Call the same write operation twice. Assert no side effects on the second call.

### G-11.5: Test concurrent access

```java
ExecutorService pool = Executors.newFixedThreadPool(10);
CountDownLatch latch = new CountDownLatch(1);
// Fire 10 threads simultaneously at the same resource
// Assert no data corruption, no duplicate writes
```

### G-11.6: Test failure scenarios

What happens when DB is down? Cache unreachable? Downstream API returns 500? Timeout? Test it.

### G-11.7: Test timezone logic with 3+ zones

UTC, IST (+05:30), US/Eastern (DST). See G-01.7.

### G-11.8: Test tenant isolation

Create data as org A. Query as org B. Assert empty/forbidden.

---

## G-12: AI-Specific Coding Guardrails (AIDLC)

**Priority**: CRITICAL — These guardrails apply when AI agents (including AIDLC skills) generate or modify code.

### G-12.1: Read existing code before writing new code

AI must search for existing utilities, patterns, naming conventions, and abstractions before generating anything. Never create a new `DateUtils.java` when one already exists.

### G-12.2: Follow the project's existing patterns — not "best practice" from training data

If the project uses manual builders, don't introduce Lombok `@Builder`. If the project uses `Result<T>`, don't introduce try-catch. Consistency > theoretical perfection.

### G-12.3: Verify every import, method call, and dependency version exists

AI hallucinates APIs. Every generated method call must be verified against the actual codebase and dependency versions.

### G-12.4: Generate the simplest solution that meets the requirement

No speculative abstractions. No Strategy+Factory+Abstract for a single implementation. YAGNI applies.

### G-12.5: Never silently change existing behaviour

When adding a feature, do not refactor surrounding code, change method signatures, or "improve" things that weren't requested.

### G-12.6: Never disable security controls

No `ssl_verify=false`, no `@PermitAll` on protected endpoints, no `csrf().disable()` without explicit justification.

### G-12.7: AI-generated tests must test behaviour, not implementation

```java
// BAD — tests nothing real
when(repo.findById(1)).thenReturn(user);
service.getUser(1);
verify(repo).findById(1); // proves mock was called, not that logic works

// GOOD — tests actual behavior
Response response = testClient.get("/users/1");
assertThat(response.status()).isEqualTo(200);
assertThat(response.body().name()).isEqualTo("Maya");
```

### G-12.8: All AI-generated changes must pass existing tests before commit

Run the full test suite. If existing tests break, the AI introduced a regression.

### G-12.9: Do not introduce new dependencies without explicit approval

Each dependency is a security surface, license risk, and maintenance burden.

### G-12.10: Respect existing error handling patterns

If the project uses exceptions, don't introduce `Either<L,R>`. If the project uses `Result<T>`, don't throw exceptions.

---

## G-13: Exception Handling & Error Codes (intouch-api-v3)

**Priority**: HIGH — Using wrong exception types bypasses the global error handler, forcing manual try-catch in controllers and breaking consistency.

### G-13.1: Use codebase exception types — never Java built-ins for HTTP-facing code

intouch-api-v3 has a global `@ControllerAdvice` (`TargetGroupErrorAdvice`) that maps specific exception types to HTTP status codes. Use these — NOT `IllegalArgumentException`, `IllegalStateException`, or generic `RuntimeException`:

| Exception Class | HTTP Status | When to Use |
|---|---|---|
| `InvalidInputException` | 400 Bad Request | Validation failures (field-level or business-rule) |
| `NotFoundException` | 404 Not Found | Entity not found by ID |
| `ConflictException` | 409 Conflict | State conflict (duplicate name, wrong status for operation) |
| `EMFThriftException` | 500 Internal | Thrift sync failures |
| `OperationFailedException` | 500 Internal | Other internal failures |

```java
// BAD — not caught by @ControllerAdvice, forces manual try-catch
throw new IllegalArgumentException("Tier not found: " + tierId);
throw new IllegalStateException("Cannot delete ACTIVE tier");

// GOOD — caught by TargetGroupErrorAdvice, mapped to correct HTTP status
throw new NotFoundException("Tier not found: " + tierId);
throw new ConflictException("Cannot delete ACTIVE tier — only DRAFT tiers can be deleted");
```

### G-13.2: Controllers must NOT contain try-catch blocks

Controllers delegate to facades/services. Exception-to-HTTP mapping is handled by `TargetGroupErrorAdvice`. Manual try-catch in controllers breaks this pattern and leads to inconsistent error responses.

```java
// BAD — manual exception handling in controller
@PostMapping
public ResponseEntity<?> createTier(@RequestBody TierCreateRequest request, ...) {
    try {
        return ResponseEntity.ok(tierFacade.createTier(...));
    } catch (IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(e.getMessage());
    }
}

// GOOD — clean delegation, @ControllerAdvice handles exceptions
@PostMapping
public ResponseEntity<ResponseWrapper<UnifiedTierConfig>> createTier(
        @Valid @RequestBody TierCreateRequest request, ...) {
    UnifiedTierConfig created = tierFacade.createTier(...);
    return new ResponseEntity<>(new ResponseWrapper<>(created, null, null), HttpStatus.CREATED);
}
```

### G-13.3: Two-layer validation pattern

Validation has two layers — both are required:

**Layer 1 — Field-level (Controller entry):** Jakarta Bean Validation annotations on DTOs + dedicated validator classes that throw `InvalidInputException` with error codes.
```java
// On DTO fields:
@NotBlank(message = "TIER.NAME_REQUIRED")
@Size(max = 100, message = "TIER.NAME_TOO_LONG")
private String name;

// In validator class:
public void validate(TierCreateRequest request) {
    if (name == null || name.isBlank()) throw new InvalidInputException("[9001] Tier name is required");
}
```

**Layer 2 — Business-rule (Facade/Service):** Rules that need DB access (uniqueness, caps, status checks) live in `@Service` classes that throw `ConflictException` or `InvalidInputException`.
```java
// In TierValidationService:
public void validateNameUniqueness(String name, int programId, long orgId) {
    if (tierRepository.existsByName(orgId, programId, name, LIVE_STATUSES))
        throw new ConflictException("A tier with name '" + name + "' already exists");
}
```

### G-13.4: Use error code ranges per domain

Assign numeric error code ranges to each domain module. Codes are included in the exception message for programmatic client parsing.

| Range | Domain |
|-------|--------|
| 9001-9009 | Tier validation |
| 9010-9019 | Maker-checker |
| 9020-9029 | (reserved for benefits) |

```java
throw new InvalidInputException("[9001] Tier name is required");
throw new InvalidInputException("[9005] End date must be after start date");
```

---

## Quick Reference — Guardrail IDs

| ID | Name | Priority |
|----|------|----------|
| G-01 | Timezone & Date/Time | CRITICAL |
| G-02 | Null Safety & Defensive Coding | HIGH |
| G-03 | Security | CRITICAL |
| G-04 | Performance | HIGH |
| G-05 | Data Integrity | HIGH |
| G-06 | API Design | HIGH |
| G-07 | Multi-Tenancy | CRITICAL |
| G-08 | Observability & Logging | HIGH |
| G-09 | Backward Compatibility | HIGH |
| G-10 | Concurrency & Thread Safety | HIGH |
| G-11 | Testing Requirements | HIGH |
| G-12 | AI-Specific (AIDLC) | CRITICAL |
| G-13 | Exception Handling & Error Codes | HIGH |

**CRITICAL** = Violation is an automatic blocker — cannot proceed without fixing.
**HIGH** = Violation is flagged in review — must justify if deviating.
