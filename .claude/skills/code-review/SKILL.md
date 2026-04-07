---
name: code-review
description: Java Spring Boot code quality review against best practices. Reviews git diff between two branches for architecture, REST API, JPA, security, testing, and performance patterns. Use when user says /code-review, or as optional add-on after AIDLC Reviewer phase.
argument-hint: <repo-name> <base-branch> <review-branch>
allowed-tools: Read, Grep, Glob, Bash(git *), Bash(curl *), Bash(afplay *), AskUserQuestion
---

# Java Spring Boot Code Review

You are performing a thorough code review based on the git diff between two branches in a GitHub repository.

Parse the three required arguments from `$ARGUMENTS`:
- `$ARGUMENTS[0]` — GitHub repo name (e.g. `org/repo` or just `repo` if under the same org)
- `$ARGUMENTS[1]` — base branch (e.g. `main`)
- `$ARGUMENTS[2]` — branch to review (e.g. `feature/my-feature`)

Run the following to get the diff:
```
git fetch origin
git diff origin/$ARGUMENTS[1]...origin/$ARGUMENTS[2]
```

Use the diff output as the code to review.

## Review Checklist

Evaluate every applicable item below. Skip categories that are not relevant to the changes.

---

### 1. Spring Architecture & Patterns
- [ ] Controllers contain only routing/HTTP concerns — no business logic
- [ ] Business logic lives in `@Service` classes
- [ ] DTOs are used between controller↔service; entities are not exposed in API responses
- [ ] Constructor injection is used instead of `@Autowired` field injection
- [ ] No circular dependencies introduced
- [ ] `@Configuration` classes are well-organized; `@Bean` methods have clear purpose
- [ ] Spring Profiles used for environment-specific config (dev/test/prod)

### 2. REST API Design
- [ ] Endpoint names use nouns, not verbs (e.g. `/orders`, not `/getOrders`)
- [ ] Correct HTTP methods: GET (read), POST (create), PUT/PATCH (update), DELETE (remove)
- [ ] Appropriate HTTP status codes returned (200, 201, 400, 401, 403, 404, 409, 500)
- [ ] Consistent JSON response structure across endpoints
- [ ] Pagination/filtering for collection endpoints
- [ ] API versioning strategy followed (e.g., `/v1/...`)
- [ ] Swagger/OpenAPI annotations updated if applicable

### 3. Transaction Management
- [ ] `@Transactional` is on service methods, not controllers or repositories
- [ ] Rollback strategy is correct — checked exceptions need explicit `rollbackFor`
- [ ] Propagation levels are intentional (default `REQUIRED` vs `REQUIRES_NEW`, etc.)
- [ ] No `@Transactional` on methods called internally within the same bean (proxy bypass)
- [ ] Long transactions avoided; no blocking I/O inside transactions
- [ ] Transaction timeout set where appropriate

### 4. JPA / Database
- [ ] Fetch type is `LAZY` by default; `EAGER` fetch is justified
- [ ] No N+1 query problems — use `JOIN FETCH` or `@EntityGraph` where needed
- [ ] Queries use named parameters or `@Query`, not string concatenation
- [ ] Indexes exist on frequently queried/filtered columns
- [ ] No entity state flushed accidentally outside a transaction
- [ ] Batch inserts/updates used for bulk operations

### 5. Security
- [ ] All endpoints have proper authentication/authorization (`@PreAuthorize`, Spring Security config)
- [ ] User input validated with `@Valid` + Bean Validation (`@NotNull`, `@Size`, `@Pattern`, etc.)
- [ ] No secrets, passwords, or tokens hardcoded or logged
- [ ] HTTPS enforced; no plain HTTP for sensitive data
- [ ] SQL injection prevented — parameterized queries only
- [ ] No stack traces exposed in API error responses
- [ ] Rate limiting considered for public-facing endpoints
- [ ] Sensitive fields excluded from serialization (`@JsonIgnore` / response DTO)

### 6. Exception Handling
- [ ] `@ControllerAdvice` / `@RestControllerAdvice` used for centralized exception handling
- [ ] Domain-specific custom exceptions defined and used
- [ ] Specific exceptions caught (not bare `catch (Exception e)`)
- [ ] `Optional<T>` used instead of returning/accepting `null` in service layer
- [ ] Client-facing error messages are meaningful but do not leak internals
- [ ] Exceptions logged with sufficient context (correlation ID, entity ID, etc.)

### 7. Logging
- [ ] SLF4J used (`private static final Logger log = LoggerFactory.getLogger(...)`)
- [ ] SLF4J placeholder syntax `log.debug("value: {}", val)` — no string concatenation
- [ ] Log levels are appropriate: DEBUG for internals, INFO for key events, WARN/ERROR for problems
- [ ] No passwords, tokens, PII, or sensitive data logged
- [ ] Correlation/request IDs included for traceability in distributed flows

### 8. Testing
- [ ] Unit tests cover the new/changed service logic
- [ ] Test slices used appropriately: `@WebMvcTest` for controllers, `@DataJpaTest` for repositories
- [ ] No unnecessary `@SpringBootTest` for unit-level tests (slow)
- [ ] Mocks used for external dependencies; not mocking the class under test
- [ ] Edge cases and error paths are tested (not just happy path)
- [ ] Tests are independent — no shared mutable state between tests
- [ ] Testcontainers (or real DB) preferred over H2 for repository tests

### 9. Performance
- [ ] No blocking calls on reactive/async threads
- [ ] `@Cacheable` / caching applied where repeated expensive computation occurs
- [ ] No unnecessary data fetched from DB (select only needed columns/fields)
- [ ] Async processing (`@Async`, `CompletableFuture`) used for non-critical long-running tasks
- [ ] Connection pool settings (HikariCP) not degraded
- [ ] Large result sets streamed, not loaded fully into memory

### 10. General Java Quality
- [ ] Naming: PascalCase for classes, camelCase for methods/variables, UPPER_SNAKE_CASE for constants
- [ ] Methods are focused (single responsibility); long methods refactored
- [ ] No dead code, unused imports, or commented-out code blocks
- [ ] DRY — no duplicated logic that should be extracted
- [ ] `final` used for fields/variables that don't change
- [ ] Appropriate collection types chosen (List vs Set vs Map)
- [ ] `pom.xml` / `build.gradle` not bloated with unused dependencies

---

## Sound Effects

**Step 1 — Before doing anything else**, use the `AskUserQuestion` tool with exactly this config:
- question: "Play sound effects after the review findings?"
- header: "Sounds"
- options: [{ label: "Yes", description: "Play FAAAH then Rahul Gandhi Khatam after findings" }, { label: "No", description: "Skip sounds, just show the review" }]

Remember the answer (yes_sound = true if "Yes" was selected).

**Step 2** — Immediately (without waiting for another user message) run the full review and produce all output (Summary, Findings, Praise, Verdict).

**Step 3 — After** the full review output is shown: if yes_sound is true, run these two bash commands SEQUENTIALLY (wait for first to finish before starting second):
```bash
curl -s -L "https://www.myinstants.com/media/sounds/fahhhhhhhhhhhhhh.mp3" -o /tmp/faah.mp3 && afplay /tmp/faah.mp3
curl -s -L "https://www.myinstants.com/media/sounds/tmp8ljn9e7h.mp3" -o /tmp/rahul.mp3 && afplay /tmp/rahul.mp3
```
Always FAAAH first, then Rahul Gandhi Khatam — every time, no alternation.

If no_sound — skip sounds entirely.

## Output Format

Produce a structured review with the following sections:

### Summary
One paragraph: what the change does, overall impression, and verdict — **APPROVE**, **REQUEST CHANGES**, or **COMMENT**.

### Findings

Group findings by severity:

**Critical** (must fix — security, data integrity, correctness)
**Major** (should fix — performance, maintainability, missing tests)
**Minor** (nice to fix — style, naming, small improvements)
**Nit** (optional polish)

For each finding:
- File and line reference (e.g. `UserService.java:42`)
- What the issue is
- Why it matters
- Suggested fix (code snippet if helpful)

### Praise
Call out 1–3 things done well.

### Verdict
Final recommendation: **APPROVE** / **REQUEST CHANGES** / **COMMENT**

---

## AIDLC Pipeline Integration (Optional)

When invoked from the AIDLC pipeline after the `/reviewer` phase:
- Arguments are auto-populated: repo = current repo, base = default branch, review = `aidlc/<ticket>` or `aidlc/<ticket>`
- The diff covers all code changes made during the Developer phase
- Findings feed back into `07-reviewer.md` as a separate "Code Quality Review" appendix
- This is complementary to `/reviewer` — that checks requirements alignment; this checks Java/Spring best practices
