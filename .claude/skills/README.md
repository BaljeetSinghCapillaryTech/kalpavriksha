# Workflow Guide

A set of specialised personas that guide software development from raw requirements through to reviewed, production-ready code. Each skill enforces strict persona boundaries so Claude stays focused on one job at a time.

---

## Quick Start

### From Terminal (recommended — uses the AIDLC agent with Opus 4.6)

```bash
claude --agent aidlc
```

Shows an interactive menu with 4 modes: Full Workflow, Single Phase, Revert, Status. See **[README-AIDLC.md](README-AIDLC.md)** for the complete guide with all commands, flows, and examples.

### From Claude Code / Cowork (uses skills directly)

```
/workflow docs/workflow/TICKET-123/
```
Claude walks you through every phase, pausing for your approval before moving on.

**Run a single skill directly:**
```
/architect
/ba
/debug
/tutor
```

---

## Development Guardrails

**File**: `.claude/skills/GUARDRAILS.md`

12 guardrail categories that every code-touching skill must follow. Read by Architect, Analyst, Designer, QA, Developer, SDET, and Reviewer at phase start.

| ID | Category | Priority | Enforced By |
|----|----------|----------|-------------|
| G-01 | Timezone & Date/Time | CRITICAL | All skills — UTC storage, `java.time`, ISO-8601 |
| G-02 | Null Safety & Defensive Coding | HIGH | Developer, Reviewer |
| G-03 | Security | CRITICAL | Architect (design), Analyst (check), Reviewer (verify) |
| G-04 | Performance | HIGH | Architect, Analyst, Reviewer |
| G-05 | Data Integrity | HIGH | Architect, Developer |
| G-06 | API Design | HIGH | Architect, Designer |
| G-07 | Multi-Tenancy | CRITICAL | All skills — tenant filter on every query |
| G-08 | Observability & Logging | HIGH | Developer, Reviewer |
| G-09 | Backward Compatibility | HIGH | Architect, Analyst |
| G-10 | Concurrency & Thread Safety | HIGH | Developer, QA, SDET |
| G-11 | Testing Requirements | HIGH | QA, Developer, SDET |
| G-12 | AI-Specific (AIDLC) | CRITICAL | All skills — read before write, follow patterns |

**CRITICAL** = Violation is an automatic blocker.
**HIGH** = Flagged in review, must justify if deviating.

---

## Optional Enhancements

The skills work out of the box with no setup. These two tools make them significantly more capable when available.

### LSP (jdtls) — semantic code navigation for Java projects

Without LSP, all phases navigate the codebase using grep and file reads. With LSP running, analytical phases (Architect, Analyst, Designer, QA, SDET, Reviewer) gain precise semantic queries: go-to-definition, find-all-references, incoming call chains, and type information — across the whole codebase, not just the files you've read.

The workflow automatically checks LSP status before starting and falls back to grep if it's not available. No manual setup is needed beyond having the daemon installed.

**Setup:** `~/.jdtls-daemon/jdtls.py` — start it for a project with:
```
python ~/.jdtls-daemon/jdtls.py start <project_root>
```

### Historian MCP — cross-session memory

Without historian, each session starts fresh — session memory only persists what was written to `session-memory.md` in the current workflow. With historian, Claude can search your entire local conversation history before making decisions: prior architectural choices, previously resolved clarification questions, errors you've debugged before, and topics covered in past tutor sessions.

Every historian call is a soft dependency — if it's not installed or returns nothing relevant, the skills proceed normally.

**Setup:**
```
claude mcp add claude-historian-mcp -- npx claude-historian-mcp
```

---

## The Full Workflow

```
[ProductEx BRD Review] ──parallel──▶ ┐
                                      ├─▶ BA Review Gate ─▶ /architect → ...
[BA (00) Q&A] ────────interactive──▶ ┘

/ba  →  /architect  →  /analyst  →  /designer  →  /qa  →  /developer  →  /sdet  →  /reviewer
 00        01             02            03           04        05            06          07
                       (optional)                                         (optional)
[main]  [subagent]    [subagent]    [subagent]  [subagent]  [main]     [subagent]  [subagent]
                 ◄── verify cycle ──►                              ◄── build-fix cycle ──►
              (Architect↔Analyst↔ProductEx                      (Reviewer↔Developer/QA
                    max 3 rounds)                                     max 3 rounds)
```

**BA** and **Developer** run in the main conversation context — they're interactive, ask questions, and make commit decisions. Every other phase runs as an isolated subagent: it reads the artifacts and session memory from disk, does its work, and returns a structured summary.

**Reviewer** runs build verification (compile → unit tests → integration tests) **before** code review. If build/tests fail, the failure is routed to Developer (code bug) or QA (test logic wrong) for resolution — max 3 rounds. After 3 failed rounds, control goes to the human. Only after build passes does Reviewer proceed to the full code review.

**ProductEx BRD Review** runs in parallel with BA as a background subagent — it independently analyses the BRD against the product registry and official docs, producing `brdQnA.md` with questions for the product team. Both outputs are reviewed at the "Review Gate" before proceeding to Architect.

`/debug`, `/tutor`, `/gap-analyser`, `/migrator`, and `/coordinate` are standalone — invoke them at any time, independent of the workflow. Within the workflow, `gap` and `migrate` are available as on-demand commands at pause prompts. `/coordinate` is auto-invoked by `feature-pipeline` at 4 checkpoints when multi-epic mode is enabled.

---

## Invoking the Workflow

```
/workflow <artifacts-path> [skip:analyst] [skip:sdet]
```

| Example | What it does |
|---|---|
| `/workflow docs/workflow/TICKET-123/` | Full workflow, all phases |
| `/workflow docs/workflow/TICKET-123/ skip:analyst` | Skips impact analysis (good for low-risk changes) |
| `/workflow docs/workflow/TICKET-123/ skip:analyst,sdet` | Skips both optional phases (fastest path) |

If you don't provide a path, Claude will ask for one before starting.

### Between phases

After each phase, Claude pauses and shows you what was produced, what was added to session memory, and any blockers raised against prior phases:

```
---
✅ [Phase Name] complete → artifact written to [path/NN-phase.md]
📝 Session memory updated: [what was added]

⚠️  Blockers requiring prior phase revisit: [list or "None"]

Next: [Next Phase Name]
Type `continue` to proceed, `skip` to skip the next phase, or tell me which phase to revisit.
---
```

---

## Skills Reference

### `/ba` — Business Analyst (Phase 00)
**Runs first. Always. ProductEx BRD Review runs in parallel.**

The BA's job is to eliminate ambiguity before any technical work begins. It starts by researching the product registry, current product documentation at `docs.capillarytech.com`, and `brdQnA.md` (from ProductEx's parallel review) — then runs the requirement through three lenses (architectural scope, downstream effects, testability).

Before asking the user anything, BA **consults internally**:
- **Product questions** → spawns ProductEx in `consult` mode. If ProductEx can't answer, the question goes to `brdQnA.md` for the product team — not to the user.
- **Code/backend questions** → spawns Architect in lightweight research mode. If Architect can't answer from the codebase, the **workflow pauses** and the question is escalated to the user directly.
- **Business intent questions** → asked directly to the user, one at a time.

The BA pushes back when:
- Your description contradicts existing documented behaviour
- A requirement is too vague to design or test against
- Earlier answers conflict with later ones

**Produces:**
- `00-ba.md` — problem statement, goals, scope, user stories, acceptance criteria, constraints, assumptions
- `docs/product/<feature>.md` — creates or updates product documentation
- Contributions to `brdQnA.md` — unresolved product questions appended via ProductEx consult

---

### `/architect` — Architect (Phase 01)

The Architect never designs before researching. It works in four deliberate steps:

1. **Research the codebase** — module structure, existing patterns, naming conventions, entry points, and any code in the area being changed
2. **Research real-world patterns** — across architectural patterns (CQRS, event sourcing, saga...), design patterns (strategy, observer, factory...), domain-specific patterns (loyalty systems, CRM, points engines...), and API/integration patterns (idempotency, webhooks, pagination...)
3. **Present options with tradeoffs** — a table of patterns evaluated against your codebase; waits for your direction before designing
4. **Design the solution** — with the chosen approach confirmed

The Architect pushes back on BA when:
- Requirements are too ambiguous or contradictory to design against
- A requirement is technically infeasible, or only feasible at unacceptable cost
- A scope boundary is undefined in a way that materially affects module structure

**Produces:** `01-architect.md` — current state summary, pattern options considered, chosen approach, modules, API design, data/persistence, business rules, ADRs, open questions

---

### `/analyst` — Impact Analyst (Phase 02, optional)

Assumes every change has side effects and maps them explicitly. It searches the codebase for callers, callees, and data flows rather than speculating — and rates each finding by severity.

**Two-stage analysis:**
1. **Impact analysis** — maps affected modules, classes, files; identifies side effects (behavioural, performance, integration); surfaces security considerations; rates risks by severity
2. **Product requirements verification** — consults ProductEx in `verify` mode to check whether the Architect's solution actually fulfils the BA's product requirements, respects module boundaries, and doesn't break documented behaviour

If ProductEx finds unfulfilled requirements or product boundary violations, Analyst raises a blocker against Architect with evidence-backed issues and suggested directions. This triggers the **Architect-Analyst-ProductEx verification cycle** (max 3 iterations). Every cycle is visible to the user — they can see what changed, what was resolved, and what remains. After 3 cycles, unresolved issues are escalated to the human for manual resolution.

The Analyst pushes back on the Architect when:
- A security flaw is structural to the proposed architecture — not just a risk to note, but a reason to redesign
- The design creates an unacceptable performance or scalability problem that the architecture itself causes
- A breaking change hasn't been accounted for and would require cross-cutting rework
- **Product requirements are not fulfilled** — backed by evidence from ProductEx verification (docs, registry, BA requirements)

**Skip when:** the change is isolated and low-risk with no cross-cutting concerns.

**Produces:** `02-analyst.md` — change summary, impact map, side effects, security considerations, risks, product requirements verification

---

### `/designer` — Designer (Phase 03)

Defines the interface contracts — what each component exposes, not how it works. The Designer prefers small, focused interfaces and treats naming as part of the design. Uses exact terminology from session memory so that interface names are consistent with the agreed domain language.

- Names abstractions and their single-line purpose
- Defines method signatures (name, params, return type, errors)
- Maps ownership (which module owns which interface)
- Enforces dependency direction (no cycles)

The Designer pushes back when:
- The Architect's module structure creates cyclic dependencies that can't be resolved at the interface level
- A module boundary forces interface design that violates SOLID principles in a brittle or untestable way
- A security risk flagged by the Analyst requires an explicit interface mitigation that wasn't identified

**Produces:** `03-designer.md` — abstractions, interface signatures, ownership map, dependency direction

---

### `/qa` — QA (Phase 04)

Defines *what* to test — QA does not plan automation (that's SDET). It converts every constraint and risk in session memory into a test scenario, then goes further: happy path, boundary conditions, empty and invalid inputs, failure modes, and gaps that aren't covered yet.

- Happy path, boundary, empty, invalid, and failure scenarios
- Every constraint in session memory becomes a potential test scenario
- Identifies existing tests to extend
- Flags coverage gaps

The QA phase pushes back when:
- An interface makes a required scenario structurally untestable — no way to inject a test double, no observable outcome, no mechanism to simulate a required failure mode
- An acceptance criterion from BA is too vague to translate into a concrete, testable scenario

**Produces:** `04-qa.md` — test scenarios table, edge cases, existing tests to touch, gaps checklist

---

### `/developer` — Developer (Phase 05)

Implements using classical TDD (Chicago/Detroit school):
- A "unit" is a group of classes delivering a business outcome, not an individual class
- Utility classes are tested in isolation
- Mocks only at true external boundaries (HTTP, DB, filesystem)
- Red → green → refactor, every cycle

Before writing a single line of code, Developer reads all session memory: constraints, risks, and any open questions that could affect the implementation. Uses exact domain terminology from session memory in all code and variable names.

If anything blocks implementation — a QA scenario that's impossible to implement against the current interfaces, a missing interface, a constraint that conflicts with what QA expects — Developer surfaces it to you before proceeding rather than silently working around it.

Prompts you at logical commit points with a suggested commit message. Rebases from main and runs tests before committing. Also updates relevant docs (README, API docs, changelog) as part of each implementation step.

**Produces:** `05-developer.md` — what was implemented, which tests drive each behaviour, terminal output summary

---

### `/sdet` — SDET (Phase 06, optional)

Operationalises what QA defined into a working test suite and CI plan. SDET's first task is to cross-reference QA's scenarios against what Developer actually built — if critical scenarios are absent from the implementation, it raises a blocker rather than planning automation around the gap.

- Automation vs manual split
- Which runner/framework, where tests live
- Manual test steps (numbered, with expected results)
- CI and local run commands

**Skip when:** the Developer phase already covers test automation sufficiently for the change.

**Produces:** `06-sdet.md` — test plan, automation details, manual steps, CI/local run instructions

---

### `/reviewer` — Reviewer (Phase 07)

The final gate before merge. The Reviewer reads the **full session memory** as the authoritative record of everything that was agreed, then verifies the implementation against it — not against what it thinks should have been built.

**Step 0 — Build & Test Verification** (before any code review):

```
mvn compile  ──► FAIL? ──► BLOCKER → Developer
    │ PASS
mvn test     ──► FAIL? ──► test logic wrong? → QA
    │ PASS           └──► code bug? → Developer
mvn verify   ──► FAIL? ──► BLOCKER → Developer
    │ PASS
Proceed to code review
```

If build/tests fail, the Reviewer routes the failure to **Developer** (code bug, compilation, dependency) or **QA** (test logic wrong vs `04-qa.md` spec). This cycles up to **3 rounds**. After 3 failed rounds, the human gets control with full error context. Only after the build is green does the Reviewer proceed to code review.

Then checks six things in order:
- **Build verification** — compilation, unit tests, integration tests (all must pass)
- **Requirements alignment** — does the implementation satisfy every acceptance criterion in `00-ba.md`?
- **Session memory alignment** — are Key Decisions reflected in the code? Are Constraints respected? Are Risks addressed?
- **Security verification** — for each security consideration raised during the workflow, is there code evidence it was addressed? This is an explicit check, not inferred from "constraints were respected"
- **Documentation** — are README, API docs, ADRs, and changelog updated where the change requires it?
- **Code quality** — naming, structure, complexity, duplication

Findings are split cleanly: **Blockers** (must fix before merge) and **Non-blocking** (nice to have). A blocker is raised when build/tests fail, an acceptance criterion is unmet, a decision contradicted, a constraint violated, a risk unmitigated, or a security concern left unaddressed. Everything else is non-blocking.

**Produces:** `07-reviewer.md` — requirements checklist, session memory checklist, security check, docs check, code review findings

---

### `/productex` — Product Expert (Standalone + Workflow-Integrated)

Builds and maintains a structured product knowledge base — the **product registry** (`docs/product/registry.md`). The registry maps your product's modules, microservices, integrations, domain model, and cross-cutting concerns into a single queryable reference. Draws from both the codebase and official documentation at `docs.capillarytech.com`.

**User-invokable modes:**
- **`discover`** — scan the codebase + official docs and build/update the registry. Asks one question at a time to confirm findings
- **`query <question>`** — answer a product question from the registry ("which service handles X?", "what depends on module Y?")
- **`map <module>`** — deep-dive into a specific module: internal structure, API endpoints, data owned, events, integration details
- **`brief <feature-area>`** — produce a focused product brief showing relevant modules, current behaviour, integration context, and domain entities

**Workflow-internal modes** (triggered automatically, not invoked manually):
- **`brd-review`** — runs in parallel with BA at Phase 00. Independently analyses the BRD against registry + docs + codebase. Produces `brdQnA.md` with questions for the product team, conflicts, and missing specs.
- **`consult`** — triggered by BA during Q&A when it encounters a product question. Returns an answer or marks the question as unresolved in `brdQnA.md`.
- **`verify`** — triggered by Analyst to verify whether the Architect's solution fulfils product requirements. Returns `approved` or `changes_needed` with evidence-backed issues. Powers the Architect-Analyst-ProductEx verification cycle.

**How other phases use it:**
- **BA** actively consults ProductEx as a subagent for product questions. Unresolved questions go to `brdQnA.md`, not to the user.
- **Analyst** reads the registry for blast radius, then consults ProductEx in `verify` mode to check the Architect's solution against product requirements. If issues are found, triggers the Architect rework cycle (max 3 iterations).

**Produces:** `docs/product/registry.md` + `brdQnA.md` (during workflow)

---

### `/gap-analyser` (or `/gap`) — Gap Analyser (Standalone + On-Demand in Workflow)

Compares **what was designed** against **what was built**. Works in two modes:

- **Pipeline mode** — reads AIDLC artifacts (01-architect.md, 03-designer.md) as the source of architectural intent, compares against the code written during Developer phase
- **Standalone mode** — reads ADRs, design docs, or infers architecture from the codebase itself

**Analyses five dimensions:**
1. **Structural compliance** — do designed modules exist as actual packages?
2. **Dependency direction** — do dependencies flow correctly (no layer violations, no cycles)?
3. **API contract drift** — do implemented endpoints match designed contracts?
4. **ADR compliance** — does code respect specific architectural decisions?
5. **Guardrail compliance** — checks CRITICAL guardrails (G-01, G-03, G-07, G-12) against code

**Key output:**
- **Scorecard** — severity-ranked findings (Critical/High/Medium/Low) with evidence (file:line, rule source) and per-dimension scores (0-10)
- **ArchUnit test classes** — structural rules encoded as JUnit tests for CI enforcement. Uses ArchUnit's freeze mechanism to baseline existing violations.
- **Remediation steps** — not just "this is wrong" but what to change and which phase to route to

**Produces:** `05b-gap-analyser.md` (pipeline) or `gap-analysis-report.md` (standalone)

---

### `/migrator` (or `/migrate`) — Migrator (Standalone + On-Demand in Workflow)

Analyses migration needs — primarily database schema, secondarily framework/pattern transitions. Does not execute migrations; produces plans for human review.

**Three modes:**

1. **`schema`** (primary focus) — database schema migration analysis:
   - Detects migration tool (Flyway/Liquibase/Atlas)
   - Audits existing migrations (naming, sequencing, responsibility)
   - Classifies proposed changes by risk (ADD TABLE=LOW, RENAME COLUMN=CRITICAL)
   - Checks backward compatibility (old + new code running simultaneously during rolling deploy)
   - Enforces expand-then-contract for non-additive changes
   - Detects schema drift (entity classes vs migration scripts)

2. **`framework`** — framework/library version upgrade analysis:
   - Breaking API changes, dependency conflicts, config changes
   - Produces ordered migration checklist with risk levels

3. **`pattern`** — architectural pattern transition analysis:
   - Component mapping (keep/modify/replace/new/remove)
   - Phased transition plan (foundation → dual-run → cutover → cleanup)
   - Strangler fig boundaries

**Key guardrails enforced:** G-05.4 (expand-then-contract mandatory), G-07.1 (new tables must include tenant column), G-09.1 (backward-compatible schema changes).

**Produces:** `01b-migrator.md` or `05c-migrator.md` (pipeline) or `migration-analysis-report.md` (standalone)

---

### `/coordinate` — Epic Coordinator (Pipeline-Integrated + Standalone)

Manages cross-epic coordination when multiple developers work on different epics from the same BRD. Auto-invoked by `feature-pipeline` at 4 checkpoints when multi-epic mode is enabled. Also used by `epic-decomposer` for registry publishing.

**Four checkpoints:**
1. **`registry-scan`** (post-Phase 1) — scan registry for shared modules, check intents, prompt claims, inject constraints
2. **`interface-check`** (post-Phase 6) — cross-reference HLD against registry, block duplicates, publish interfaces
3. **`final-sync`** (pre-Phase 9) — sync dependency statuses, swap mocks for real code, detect collisions
4. **`duplication-check`** (post-Phase 11) — scan for accidental overlap, update module status

**Key features:**
- Shared modules registry (GitHub repo) as source of truth
- Module claims via atomic `git push` / PR
- Thrift IDL compatibility checking
- Staleness detection (7d warn / 14d issue / 30d auto-release)
- Handoff briefings on module re-claim
- Graduated severity: BLOCK / WARN / INFO / AUTO-FIX

**Related agents:**
- `epic-decomposer` — architect runs once to identify shared modules and publish epic packages
- `epic-coordinator` — agent wrapper that invokes this skill at each checkpoint

---

### `/debug` — Debugger (Standalone)

Invoke any time — not part of the linear flow. Works evidence-first:

1. Correlates code, logs, and terminal output
2. Forms a hypothesis
3. Identifies the relevant code location
4. Suggests steps to verify
5. Proposes a fix

If a workflow is active, reads session memory to narrow the search space immediately (Codebase Behaviour, Constraints, Risks). For performance issues: measures first, then narrows to hotspots.

---

## Session Memory

Every workflow run creates a shared `session-memory.md` in your artifacts path. Each phase reads it before starting and writes to it when done. This is what prevents phases from re-discovering the same things or contradicting decisions made earlier in the workflow.

### Sections

| Section | What it tracks | Who writes |
|---|---|---|
| **Domain Terminology** | Agreed terms — used consistently in all code, names, and docs | BA, ProductEx |
| **Codebase Behaviour** | What exists and how it's set up | BA, Architect, Analyst, Developer, Debug, ProductEx |
| **Key Decisions** | Decisions and their rationale | Architect, Designer, Developer, Reviewer |
| **Constraints** | Technical, business, regulatory — all phases must respect these | BA, Architect, Analyst, Designer, Developer, SDET |
| **Risks & Concerns** | Flagged risks, tracked to resolution | Analyst, QA, Developer, Reviewer, Debug |
| **Open Questions** | Unresolved items — `[ ]` open, `[x]` resolved | Any phase |
| **Rework Log** | Tracks re-run cycles to detect unresolved loops | Orchestrator |

### How phases use it actively

The session memory isn't just read for background context — phases actively use it to shape their work:
- **QA** converts every Constraint into a test scenario
- **Architect** checks Codebase Behaviour before proposing new structure
- **Developer** uses Domain Terminology in all variable and method names
- **Reviewer** verifies every Key Decision is reflected in the implementation

---

## Artifact Files

All artifacts are written to the path you provide when starting the workflow:

```
docs/workflow/TICKET-123/
├── session-memory.md       ← shared cross-phase memory
├── brdQnA.md              ← product questions, conflicts, gaps (ProductEx + BA)
├── 00-ba.md                ← requirements, user stories, acceptance criteria
├── 01-architect.md         ← design, patterns, ADRs
├── 02-analyst.md           ← impact map, risks  (optional)
├── 03-designer.md          ← interfaces, contracts
├── 04-qa.md                ← test scenarios, edge cases
├── 05-developer.md         ← implementation summary
├── 05b-gap-analyser.md     ← architecture-code scorecard + ArchUnit rules  (on-demand)
├── 05c-migrator.md         ← migration analysis report  (on-demand, or 01b after Architect)
├── 06-sdet.md              ← test plan, CI instructions  (optional)
└── 07-reviewer.md          ← review findings, blockers

docs/product/
└── <feature-name>.md       ← product documentation (created/updated by BA)
```

---

## Navigating the Workflow

### Skipping a phase

Type `skip` when prompted between phases.

### Looping back

At any pause prompt, name a phase to return to it:
> "Go back to Architect — the Analyst found a circular dependency in the proposed module structure"

Claude re-runs that phase with updated context, then cascades forward through all intermediate phases before returning to where you were.

### Resuming a paused workflow

Start a new session and run the same command:
```
/workflow docs/workflow/TICKET-123/
```
Claude detects that `session-memory.md` and prior artifacts already exist and picks up where you left off.

---

## Automatic Rework Loop

Phases don't just consume prior phase output — they actively verify it. When something is wrong upstream, a phase raises a blocker rather than silently working around it. The workflow then handles the rework automatically where it can, and escalates to you where it can't.

### How blockers are classified

The orchestrator — not the phase that raised the blocker — decides whether it's **critical** or **trivial**:

| Critical — always requires your approval | Trivial — handled automatically |
|---|---|
| Invalidates a decision you previously approved | Naming inconsistency |
| Violates existing architectural patterns in the codebase | Missing edge case in one phase |
| Violates established design approaches from this workflow | Minor interface refinement |
| Deviates from requirements defined by BA | Anything not matching a critical criterion |
| Security flaw | |
| Tech debt introduced with no mitigation plan | |

### What happens

| Blocker target | Trivial | Critical |
|---|---|---|
| **Analytical phase** (Architect–SDET) | Notify → re-run automatically → cascade | Pause → your approval → re-run → pause again before cascade |
| **Developer** | Notify → resume in main context → cascade | Pause → your approval → resume |
| **BA** | BA asks you a targeted clarifying question (always) | BA asks you a targeted clarifying question (always) |

BA blockers always come to you — that's BA's native mode. Any gap in requirements needs a human answer; there's no automatic path for it.

### Cascade rules

When a phase is re-run, all downstream phases between it and the one that raised the blocker are also re-run in order before returning to the source:

| Re-run target | Cascades through |
|---|---|
| Architect (01) | Analyst (if not skipped) → Designer → QA |
| Analyst (02) | Designer → QA |
| Designer (03) | QA |
| QA (04) | _(Developer re-engages directly)_ |
| Developer (05) | SDET (if not skipped) |
| BA (00) | Architect → Analyst (if not skipped) → Designer → QA |

### Circuit breaker

If the same phase has been re-run twice without resolving the blocker, the workflow stops and puts the decision back to you. You'll see exactly what's conflicting, why it won't resolve automatically, and a set of concrete options: revisit an earlier phase, accept the deviation, mark it as a known risk, or something else.

The workflow never spins indefinitely.

---

## `/tutor` — Codebase Tutor (Standalone)

A patient, adaptive teaching mode — completely separate from the development workflow. It reads the codebase and explains it to you, but **never modifies it**.

```
/tutor                     — start or continue a session
/tutor <topic>             — jump straight into a topic
/tutor curriculum          — build a learning path for the whole codebase
/tutor notes               — show the session index (tutor-notes.md)
/tutor lessons             — list all saved lesson files
```

At the start of each session, the tutor calibrates to your level: `novice`, `familiar`, or `author`. It teaches using the **Feynman method** — plain language first, no jargon without explanation — then shifts to **Socratic questioning** once you've shown you understand a concept.

**Four modes to choose from:**
1. **Give me a topic** — name a class, file, or concept and the tutor will teach it
2. **Surprise me** — the tutor picks something interesting from the codebase
3. **I have a question** — start from something that's confusing or unclear
4. **Build a curriculum** — a structured learning path across the whole codebase

When the tutor notices a code smell, unusual pattern, or interesting tradeoff while reading, it surfaces it as a teaching moment — framed as curiosity, never criticism.

**Progress is saved across sessions:**
```
tutor-notes.md                                ← index: topics covered, open threads, curriculum
lessons/
  tutor-lesson-2026-03-10-event-sourcing.md   ← one detailed file per session
  tutor-lesson-2026-03-15-service-layer.md
```

After each lesson is written to disk, the tutor prompts you to `/clear` so the next session starts with a clean context. The index (`tutor-notes.md`) is read at the start of every session to resume continuity.

---

## Tips

- **Use the BA phase even for small changes** — the one-at-a-time Q&A reliably surfaces assumptions you didn't know you had
- **The Architect's pattern table is the most valuable output** — take time to read the tradeoff analysis before continuing; that's where the real design thinking happens
- **Each phase actively challenges the one before it** — if something is wrong upstream, phases are expected to raise it, not work around it
- **Open Questions in session memory are your audit trail** — any unresolved `[ ]` item that reaches the Reviewer is an automatic blocker
- **Debug reads session memory** — if a bug appears mid-workflow, `/debug` already knows the codebase context and the constraints in play
- **Product docs accumulate** — over time, `docs/product/` becomes a living spec of the system, updated by every BA phase
