- Never use ExitPlanMode tool. When done planning, just say Plan is ready and wait for user input.

## Project Context

This is a **Java backend loyalty platform** (Capillary). The codebase spans multiple repos:
- **emf-parent** (this repo) — points engine, tier/slab entities, strategies, Thrift services
- **intouch-api-v3** — REST API gateway, maker-checker workflows, Spring MVC
- **peb** — Points Engine Backend, tier downgrade calculators
- **Thrift** — IDL definitions for cross-service RPC
- **api/prototype** — Customer-facing REST APIs, JAX-RS (Jersey)

Tech stack: Java, Spring, Thrift, MySQL, MongoDB, Flyway, JUnit 4, Mockito.

## Architectural Decisions (Standing — Project-Level)

Standing architectural decisions are long-lived choices that apply across all features, epics, and pipeline runs. They predate any single BRD — they are the "Why" of the project.

Per-feature ADRs are produced during pipeline Phase 6 (`/architect`) and live in `01-architect.md`. Standing decisions live here and are checked before any per-feature ADR is created.

| # | Decision | Rationale |
|---|---|---|
| A-01 | *Example: Inter-service protocol choice* | *Why this protocol over alternatives* |
| A-02 | *Example: Data mutation workflow* | *Why this approval flow exists* |

> **How to maintain**: Add a row when a project-level architectural choice is made. These are not feature-specific — they apply to every pipeline run. When `/architect` proposes something that contradicts a standing decision, it must get explicit user approval and document a new ADR explaining the deviation.
>
> **Pipeline integration**: The `/architect` skill reads this section before proposing any architecture. The `/analyst --compliance` skill checks implementation against both standing decisions and per-feature ADRs.

## Feature Pipeline

This repo includes a **feature-pipeline agent** (`.claude/agents/feature-pipeline.md`) that automates BRD-to-production in 13 phases. To use it:

```
claude --agent feature-pipeline
```

### Pipeline Skills (in `.claude/skills/`)

| Skill | Purpose | Phase |
|-------|---------|-------|
| `/ba` | Business analysis + PRD generation (merged) | 1 |
| `/architect` | HLD, ADRs, pattern evaluation | 6 |
| `/analyst` | Impact analysis (`--impact`) + compliance checking (`--compliance`) | 6a, 9c |
| `/designer` | LLD, interface contracts, compile-safe signatures | 7 |
| `/qa` | Test scenarios, edge cases, acceptance criteria | 8 |
| `/developer` | TDD implementation (Chicago/Detroit school) | 9 |
| `/backend-readiness` | Production readiness gate (queries, Thrift, cache, errors) | 9b |
| `/cross-repo-tracer` | Multi-repo write/read path tracing | 5 |
| `/sdet` | Test automation planning | 10 |
| `/reviewer` | Code review against requirements | 11 |
| `/productex` | Product knowledge base, BRD review | 1 (parallel) |
| `/migrator` | Schema migration analysis | 6b, 9d |
| `/debug` | Root cause analysis (standalone) | on-demand |
| `/tutor` | Codebase teaching (standalone, read-only) | on-demand |
| `/api-handoff` | API contract doc for UI team | after 7 or 9 |
| `/code-review` | Java Spring Boot best-practices review (standalone or pipeline add-on) | after Phase 11 (optional) |
| `/confluence-publisher` | Publish artifacts to Confluence (configurable per product) | after every phase |

**Deprecated** (kept for reference): `/prd-generator` (merged into `/ba`), `/gap-analyser` (merged into `/analyst --compliance`)

### Pipeline Rules
- **Session memory** (`session-memory.md`) is the shared context across all phases. Updated incrementally after every decision — never batch at phase end.
- **Live dashboard** (`live-dashboard.html`) is an HTML file that updates after every phase. Dark theme, sidebar nav, Mermaid diagrams, Q&A history, API contracts.
- **Cross-repo claims** of "0 modifications needed" require C6+ evidence from reading actual code. The `/cross-repo-tracer` skill enforces this.
- **Mermaid diagrams** in `.md` files use fenced code blocks (` ```mermaid `). HTML `<div class="mermaid">` is only for the live dashboard and blueprint.
- **Git snapshots** after every phase: `aidlc/<ticket>/phase-NN` tags.
- **No file copying** — read BRD, code repos, UI screenshots from original locations. Only extract text to `brd-raw.md` for binary formats (PDF/DOCX).

### Superpowers Plugin (required)

The pipeline uses the **Superpowers** plugin for advanced workflows. Install it:
```
claude install-plugin superpowers
```

Key superpowers used: `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `verification-before-completion`, `dispatching-parallel-agents`, `subagent-driven-development`.

### For New Teammates

1. Clone the repo — `.claude/` directory comes with it (skills, agents, CLAUDE.md, principles.md)
2. Install Superpowers: `claude install-plugin superpowers`
3. (Optional) Start jdtls for LSP-based code traversal
4. Run: `claude --agent feature-pipeline`

## Engineering Rules

### Rule 1 - Evidence-Based Claims
When analyzing test results, code changes, or any technical findings:
1. Never make assumptions or claims without supporting evidence.
2. Always present actual data, numbers, and facts first.
3. If you claim something is "working fine" or "working correctly", provide specific evidence and cite where it came from (test output, file line, diff, etc.).
4. When comparing before/after states, show the actual differences with concrete data.
5. If you don't have evidence, say "I don't have evidence for this claim" rather than making assumptions.
6. Always ask "What evidence do I have for this conclusion?" before stating any technical assessment.

### Rule 2 - TDD (Chicago/Detroit School)
1. Any new change should be guided by a failing test first.
2. Treat the "unit" as a collection of classes that deliver a business outcome, not individual components - this keeps tests resilient to internal refactoring. Exception: pure utility classes (formatters, calculators, pure functions with no collaborators) can and should be tested in isolation.
3. Use judgment in untested codebases - prefer test-first where practical.
4. Use mocks sparingly: only at true external boundaries (e.g. HTTP, DB, filesystem). Avoid mocks that couple tests to implementation details and dictate the implementation.
5. Where no overarching integration-style tests exist, proactively add tests that provide refactoring cover for the future.
6. Flag tests that appear redundant (without recommending removal - let the user decide).

### Rule 3 - Small Commits
1. Make small, meaningful changes and commit frequently.
2. When a logical commit point is reached, prompt the user and suggest a commit message - wait for approval before proceeding.
3. Before committing anything: rebase from main and run the tests.

### Rule 4 - Clarifying Questions
1. Before any implementation - even small changes - always ask clarifying questions to ensure the best possible choices are made.
2. Do not proceed with writing code until intent is confirmed.

### Rule 5 - LSP-First Code Traversal
1. At the start of every session, check if jdtls (Java Language Server) is available locally.
2. When opening any repo, initialise it with the LSP service before doing any code traversal.
3. All code traversal (find references, go to definition, find implementations, symbol search) must use the LSP server — do not load files into context as a substitute for LSP navigation.
4. If the LSP service is unavailable, ask the user: "jdtls doesn't appear to be running. Can you start it so I can use LSP for code traversal? If not, I'll fall back to grep/file reads." Only proceed with grep/file reads after the user confirms they cannot start it.

### Rule 6 - Calibrated Confidence & Reasoning Principles
The full reasoning framework is defined in `.claude/principles.md`. All skills and all phases of work MUST apply it. Key rules:

1. **Every claim carries a confidence level** using the C1–C7 calibrated scale:
   - C1 (< 20%) Speculative — flag, do not act alone
   - C2 (20–40%) Plausible — present alternatives, investigate first
   - C3 (40–60%) Tentative — act only if reversible, add checkpoint
   - C4 (60–75%) Probable — safe for reversible decisions, escalate if irreversible
   - C5 (75–90%) Confident — act, flag residual risk
   - C6 (90–97%) High Confidence — act decisively
   - C7 (> 97%) Near Certain — verified fact from primary source

2. **Confidence must be backed by evidence**, not feeling. See `.claude/principles.md` Principle 1 for evidence requirements per level.

3. **Reversibility determines action threshold**: Reversible + C4 = act. Irreversible + below C4 = STOP and escalate. See `.claude/principles.md` Principle 2.

4. **Doubt is structured, not vague**: When uncertain, apply the 5-Question Doubt Resolver from `.claude/principles.md` Principle 4.

5. **Pre-mortem before non-trivial actions**: "This failed. Why?" See `.claude/principles.md` Principle 6.

6. **Graduated autonomy**: Low stakes + reversible = act freely. High stakes + irreversible = present options, wait for human. See `.claude/principles.md` Principle 10.

7. **Anti-patterns to avoid**: Confident Vacuum (claims without evidence), Anchoring Bias (first approach wins), Confidence Inflation (everything rated C5+), Escalation Avoidance (proceeding on C2 to avoid "bothering" the human). See `.claude/principles.md` Anti-Patterns section.

> Read `.claude/principles.md` for the complete framework with worked examples, decision protocols, and the quick reference card.