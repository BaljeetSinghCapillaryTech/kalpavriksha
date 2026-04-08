# AIDLC — AI Development Lifecycle

> **Complete guide for running the AIDLC pipeline.** Read this if you're new to the system or need a command reference.

The AIDLC is an 8-phase AI-powered software development pipeline. Each phase is handled by a specialised AI agent persona that reads prior outputs, does its work, and hands off to the next phase. The pipeline enforces quality at every step — phases actively challenge each other, and the system handles rework loops automatically.

---

## Table of Contents

- [First-Time Setup](#first-time-setup)
- [Quick Start](#quick-start)
- [Terminal Commands](#terminal-commands)
- [The AIDLC Pipeline](#the-aidlc-pipeline)
- [Mode 1: Full Workflow](#mode-1-full-workflow)
- [Mode 2: Single Phase](#mode-2-single-phase)
- [Mode 3: Revert](#mode-3-revert)
- [Mode 4: Status](#mode-4-status)
- [In-Session Commands](#in-session-commands)
- [BRD Input](#brd-input)
- [Phase Reference](#phase-reference)
- [Git Snapshot & Revert System](#git-snapshot--revert-system)
- [Session Memory](#session-memory)
- [Artifact Files](#artifact-files)
- [Development Guardrails](#development-guardrails)
- [Rework Loops & Circuit Breakers](#rework-loops--circuit-breakers)
- [Optional Enhancements](#optional-enhancements)
- [Troubleshooting](#troubleshooting)
- [File Structure](#file-structure)

---

## First-Time Setup

### New Team Member? Start Here (3 steps)

```bash
# Step 1: Clone the repo
git clone <repo-url> && cd kalpavriksha

# Step 2: Run setup (installs CLI, configures authentication, verifies agent)
./scripts/aidlc-setup.sh

# Step 3: Start AIDLC
claude --agent aidlc
```

That's it. The setup script handles everything interactively — CLI installation, authentication, and verification. Details below if you want to understand what it does or configure manually.

### What the Setup Script Does

```bash
cd /path/to/kalpavriksha
./scripts/aidlc-setup.sh
```

The setup script will (5 steps, fully guided):

1. **Check/install Claude Code CLI** — installs via npm if not found
2. **Configure authentication** — offers 4 options:

   | Method | Best For | What You Need |
   |--------|----------|---------------|
   | **OAuth Login** (recommended) | Individual developers with Claude subscription | Anthropic account (Pro/Team/Enterprise) |
   | **API Key** | Teams sharing a billing account | API key from [console.anthropic.com](https://console.anthropic.com/settings/keys) |
   | **Amazon Bedrock** | Orgs using AWS infrastructure | AWS CLI configured + Bedrock Claude access |
   | **Google Vertex AI** | Orgs using GCP infrastructure | gcloud CLI configured + Vertex AI access |

3. **Verify AIDLC agent** — confirms `.claude/agents/aidlc.md` and all skills are present
4. **Check optional enhancements** — jdtls (LSP), Historian MCP, poppler (PDF support)

### Manual Authentication (if you prefer not to use the script)

**Option A — OAuth (recommended):**
```bash
claude auth login
```
Opens browser for Anthropic account sign-in. Uses your subscription quota.

**Option B — API Key:**
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```
Add to your `~/.zshrc` or `~/.bashrc` to persist across sessions. Get your key from [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

**Option C — Amazon Bedrock:**
```bash
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION="us-east-1"
export AWS_PROFILE="your-profile"    # optional
```

**Option D — Google Vertex AI:**
```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_PROJECT_ID="your-gcp-project"
export CLOUD_ML_REGION="us-east5"
```

### Verify Setup

```bash
claude auth status          # Should show loggedIn: true
claude agents               # Should list: aidlc · opus
```

---

## Quick Start

**Prerequisites:**
- Claude Code CLI installed and authenticated (see [First-Time Setup](#first-time-setup))
- You are inside the project repository directory

**Run the full pipeline:**
```bash
claude --agent aidlc
```

That's it. The agent shows an interactive menu and guides you through everything.

---

## Terminal Commands

### Starting AIDLC

| Command | What It Does |
|---------|-------------|
| `claude --agent aidlc` | **Interactive menu** — shows all 4 modes (Workflow, Single Phase, Revert, Status). Recommended for first-time use. |
| `claude --agent aidlc -p "workflow <artifacts-path>"` | **Full workflow** — starts the 8-phase pipeline directly, skipping the menu. |
| `claude --agent aidlc -p "workflow <artifacts-path> brd:<file>"` | **Full workflow with BRD** — accepts PDF, DOCX, or text file as input. |
| `claude --agent aidlc -p "workflow <path> skip:analyst,sdet"` | **Full workflow, skip optional phases** — fastest path for low-risk changes. |
| `claude --agent aidlc -p "phase <name> <artifacts-path>"` | **Single phase** — jump directly into one phase (ba, architect, designer, etc.). |
| `claude --agent aidlc -p "revert <artifacts-path>"` | **Revert** — shows completed phases and lets you roll back. |
| `claude --agent aidlc -p "status <artifacts-path>"` | **Status** — shows workflow progress dashboard. |
| `claude --agent aidlc --continue` | **Resume** — picks up the last AIDLC session from where it stopped. |

### Examples

```bash
# Start a new workflow for a Jira ticket
claude --agent aidlc -p "workflow docs/workflow/TIER-456/"

# Start with a PDF BRD document
claude --agent aidlc -p "workflow docs/workflow/TIER-456/ brd:~/Downloads/Tiers_PRD.pdf"

# Start with a Word document BRD
claude --agent aidlc -p "workflow docs/workflow/TIER-456/ brd:docs/requirements/feature.docx"

# Skip optional phases for a quick change
claude --agent aidlc -p "workflow docs/workflow/HOTFIX-789/ skip:analyst,sdet"

# Jump directly into Developer phase (after earlier phases are done)
claude --agent aidlc -p "phase developer docs/workflow/TIER-456/"

# Re-run just the Designer phase
claude --agent aidlc -p "phase designer docs/workflow/TIER-456/"

# Check where a workflow stands
claude --agent aidlc -p "status docs/workflow/TIER-456/"

# Roll back to a previous phase
claude --agent aidlc -p "revert docs/workflow/TIER-456/"

# Resume an interrupted session
claude --agent aidlc --continue
```

---

## The AIDLC Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  [ProductEx BRD Review] ──(background)──┐                                │
│                                         ├──► BA Review Gate              │
│  [BA] ──────────(interactive Q&A)──────┘         │                       │
│                                                  ▼                       │
│  Architect ──► Analyst ──► Designer ──► QA ──► Developer ──► SDET ──► Reviewer
│    (01)         (02)        (03)       (04)     (05)        (06)      (07)
│               optional                         interactive  optional      │
│  [subagent]  [subagent]  [subagent] [subagent]  [main]   [subagent] [subagent]
│                                                                          │
│  ◄─────── Rework Loop (automatic, max 2 cycles per phase) ──────────►   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Phase Summary

| # | Phase | What It Does | Interactive? |
|---|-------|-------------|-------------|
| 00 | **BA** | Gathers requirements, asks clarifying questions, produces specs | Yes — Q&A with you |
| 01 | **Architect** | Researches codebase, evaluates patterns, designs solution with ADRs | No — autonomous |
| 02 | **Analyst** | Maps impact, checks security, verifies product requirements | No — autonomous (optional) |
| 03 | **Designer** | Defines interfaces, contracts, ownership, dependency direction | No — autonomous |
| 04 | **QA** | Identifies test scenarios, edge cases, coverage gaps | No — autonomous |
| 05 | **Developer** | Implements using TDD (red-green-refactor), runs builds/tests | Yes — TDD cycles with you |
| 06 | **SDET** | Plans test automation, CI/CD integration, manual test steps | No — autonomous (optional) |
| 07 | **Reviewer** | Final quality gate — checks requirements, security, code quality | No — autonomous |

---

## Mode 1: Full Workflow

Runs all 8 phases in sequence, pausing between each for your approval.

```bash
claude --agent aidlc -p "workflow docs/workflow/TICKET-123/"
```

**What happens:**
1. Creates a git branch `aidlc/TICKET-123` for safe revert
2. Initialises LSP (jdtls) for semantic code navigation
3. Creates `session-memory.md` (shared context across all phases)
4. Runs BA (interactive) + ProductEx BRD Review (background) in parallel
5. After BA completes: shows BA Review Gate with ProductEx findings
6. Runs Architect → Analyst → Designer → QA → Developer → SDET → Reviewer
7. Creates git snapshots after each phase for safe revert
8. Pauses between every phase so you can review, skip, revert, or continue

**Between each phase you'll see:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Architect complete → 01-architect.md
📝 Session memory updated: Codebase Behaviour, Key Decisions
🏷️  Snapshot: aidlc/TICKET-123/phase-01

⚠️  Blockers: None

Next: Analyst (Phase 02)

Commands:
  continue  — proceed to Analyst
  skip      — skip Analyst (optional phase)
  revert    — roll back to a previous phase
  status    — show full workflow progress
  exit      — save state and exit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Mode 2: Single Phase

Jump directly into one specific phase. Useful for re-running a phase or resuming work.

```bash
claude --agent aidlc -p "phase developer docs/workflow/TICKET-123/"
```

**Available phases:** `ba`, `architect`, `analyst`, `designer`, `qa`, `developer`, `sdet`, `reviewer`

The agent automatically:
- Reads `session-memory.md` and all prior artifacts
- Warns if prerequisite artifacts are missing
- Runs the phase following its skill definition
- Creates a git snapshot on completion

---

## Mode 3: Revert

Roll back to any previous phase, with full control over what gets reverted.

```bash
claude --agent aidlc -p "revert docs/workflow/TICKET-123/"
```

**What happens:**

**Step 1 — See completed phases:**
```
Completed phases:
  ✅ [0] BA              → 00-ba.md                    (artifacts only)
  ✅ [1] Architect       → 01-architect.md             (artifacts only)
  ✅ [2] Analyst         → 02-analyst.md               (artifacts only)
  ✅ [3] Designer        → 03-designer.md              (artifacts only)
  ✅ [4] QA              → 04-qa.md                    (artifacts only)
  ✅ [5] Business Test Gen → 04b-business-tests.md       (artifacts only)
  ✅ [6] SDET (RED)      → 05-sdet.md + TEST CODE       (N test files)
  ✅ [7] Developer (GREEN) → 06-developer.md + PROD CODE (12 files changed)
  ⬜ [8] Reviewer        → (pending)

Revert to which phase? (0-5):
```

**Step 2 — Pick a target** (e.g., 3 = Designer):

See exactly what will be affected — artifact files, code changes, session memory entries.

**Step 3 — Choose revert type:**

| Option | What It Does | When To Use |
|--------|-------------|-------------|
| **A — Full revert** | Deletes artifacts + reverts code + cleans session memory. Codebase returns to exact state after the target phase. | You want a clean restart from that phase. |
| **B — Artifacts only** | Deletes artifact files + cleans session memory. Code stays intact. | Developer's code is fine, but you want to re-run QA/SDET. |
| **C — Re-run from here** | Keeps everything. Re-runs phases from the target onward, overwriting artifacts. | You want a different design but don't want to lose existing code. |
| **D — Cancel** | Goes back to the menu. | Changed your mind. |

**Step 4 — Choose what to do next:**
```
What next?
  [1] Continue workflow from QA (Phase 4)
  [2] Re-run Designer (Phase 3) with modifications
  [3] Switch to single-phase mode
  [4] Exit
```

---

## Mode 4: Status

See the full state of a workflow at a glance.

```bash
claude --agent aidlc -p "status docs/workflow/TICKET-123/"
```

**Shows:**
- Which phases are complete, in progress, or pending
- Open blockers
- Rework history (how many times phases were re-run)
- Open questions from session memory
- Git snapshot state
- Guardrails status

---

## In-Session Commands

These work at **any pause point** during a running workflow:

| Command | What It Does |
|---------|-------------|
| `continue` | Proceed to the next phase |
| `skip` | Skip the next phase (only for optional phases: Analyst, SDET) |
| `revert` | Open the revert menu — pick a phase to roll back to |
| `revert to <N>` | Quick revert to phase N (shows impact first, then asks for confirmation) |
| `status` | Show the full workflow progress dashboard |
| `exit` | Save state and exit. Resume later with `claude --agent aidlc --continue` |
| `resolve` | Take manual control of a blocker during a rework cycle |

---

## BRD Input

The pipeline accepts Business Requirements Documents in multiple formats:

| Format | How To Provide |
|--------|---------------|
| **PDF** | `brd:path/to/document.pdf` |
| **Word (DOCX)** | `brd:path/to/document.docx` |
| **Markdown** | `brd:path/to/document.md` |
| **Plain text** | `brd:path/to/document.txt` |
| **Pasted text** | Paste BRD text in the conversation before invoking workflow |

The BRD is extracted, normalised, and saved to `<artifacts-path>/brd-raw.md`. This becomes the single source of truth that BA and ProductEx both reference.

**If no BRD is provided**, the agent will prompt you:
```
📄 No BRD detected. Please provide the requirements in one of these ways:
   1. Paste the BRD text here
   2. Provide a file path: brd:path/to/file.pdf
   3. Provide a file path: brd:path/to/file.docx
```

---

## Phase Reference

### BA — Business Analyst (Phase 00)

**Interactive.** Asks you one question at a time to refine requirements.

- Researches product docs, codebase, and existing documentation before asking anything
- Consults ProductEx (for product questions) and Architect (for code questions) internally
- Escalates to you only for business intent questions or unresolved technical questions
- Pushes back on contradictions, vague requirements, and scope gaps

**Produces:** `00-ba.md` (requirements, user stories, acceptance criteria), `docs/product/<feature>.md`

### Architect (Phase 01)

**Autonomous.** Researches, then designs.

1. Researches the codebase — modules, patterns, naming conventions, entry points
2. Researches real-world patterns — architectural, design, domain-specific, integration
3. Presents options with tradeoffs — a comparison table; waits for your direction
4. Designs the solution with the chosen approach

**Produces:** `01-architect.md` (current state, pattern options, chosen approach, modules, API design, data/persistence, business rules, ADRs)

### Analyst (Phase 02, optional)

**Autonomous.** Maps side effects and verifies product requirements.

- Searches the codebase for callers, callees, and data flows
- Rates each impact by severity
- Consults ProductEx to verify the Architect's solution fulfils requirements
- If issues found: triggers Architect-Analyst-ProductEx verification cycle (max 3 iterations)

**Skip when:** isolated, low-risk change with no cross-cutting concerns.

**Produces:** `02-analyst.md` (change summary, impact map, side effects, security considerations, risks, product verification)

### Designer (Phase 03)

**Autonomous.** Defines interface contracts.

- **Step 0: Codebase Pattern Discovery** — before designing any interface, searches the existing codebase for how the same kind of thing is already done (repositories, services, controllers, models, config, tests)
- Prescribes exact base classes, annotations, packages, and imports for every new type
- Names abstractions, defines method signatures, maps ownership, enforces dependency direction

**Produces:** `03-designer.md` (abstractions, interface signatures with Extends/Annotations/Package/Imports, ownership map, dependency direction)

### QA (Phase 04)

**Autonomous.** Defines what to test.

- Converts every constraint and risk in session memory into a test scenario
- Happy path, boundary conditions, empty/invalid inputs, failure modes
- Identifies existing tests to extend
- Flags coverage gaps
- Generates guardrail edge case scenarios (timezone, NPE, concurrency, tenant isolation)

**Produces:** `04-qa.md` (test scenarios table, edge cases, existing tests to touch, gaps checklist)

### Developer (Phase 05)

**Interactive.** Implements using TDD.

- **Step 0: Verify Designer's Patterns** — spot-checks Designer's prescriptions against the actual codebase before implementing
- Classical TDD: red (write failing test) → green (make it pass) → refactor
- Runs `mvn compile` and `mvn test` directly — no IntelliJ needed
- Uses jdtls for semantic code navigation when available
- Prompts you at logical commit points
- Updates docs as part of implementation

**Produces:** `06-developer.md` (GREEN confirmation, implementation summary, test modifications), actual code changes

### SDET (Phase 06, optional)

**Autonomous.** Plans test automation.

- Cross-references QA's scenarios against Developer's implementation
- Automation vs manual split
- CI and local run commands
- Raises blocker if critical scenarios are missing from implementation

**Skip when:** Developer phase already covers test automation sufficiently.

**Produces:** `05-sdet.md` (test plan, RED confirmation, skeleton inventory, actual test files)

### Reviewer (Phase 07)

**Autonomous.** Final quality gate.

Checks in order:
1. Requirements alignment (against 00-ba.md)
2. Session memory alignment (Key Decisions, Constraints, Risks)
3. Security verification (explicit check for each security concern raised)
4. Documentation (README, API docs, ADRs, changelog)
5. Code quality (naming, structure, complexity)
6. Guardrails compliance (blocks merge on CRITICAL violations)

**Produces:** `07-reviewer.md` (requirements checklist, session memory checklist, security check, docs check, code review findings with Blockers vs Non-blocking)

---

## Git Snapshot & Revert System

The AIDLC agent creates git snapshots at each phase boundary to enable safe revert.

### How It Works

```
main ──●────────────────────────────────────────────────────►
       │
       └── aidlc/TICKET-123 (branch created at workflow start)
            │
            ●  BA complete        → tag: aidlc/TICKET-123/phase-00
            │
            ●  Architect complete → tag: aidlc/TICKET-123/phase-01
            │
            ●  ...each phase...   → tag: aidlc/TICKET-123/phase-NN
            │
            ●  Developer complete → tag: aidlc/TICKET-123/phase-05
            │   (includes code changes committed)
            │
            ●  Reviewer complete  → tag: aidlc/TICKET-123/phase-07
```

### Revert Uses Git Tags

- **Analytical phases** (BA through QA, Reviewer): only produce artifact files. Revert = delete files.
- **Code-writing phases** (Developer, SDET): produce code changes. Revert = `git reset --hard` to the target phase's tag.
- **Session memory**: cleaned programmatically — entries tagged with reverted phases are removed.

### Safety Rules

1. Revert always asks for confirmation before executing
2. Shows file-level impact before any destructive action
3. Logs every revert in the Rework Log section of session memory
4. Never reverts past the branch creation point
5. Git tags are force-updated when a phase is re-run after revert

---

## Session Memory

Every workflow creates `session-memory.md` in the artifacts path. All phases read and write to it — this is the shared context that prevents phases from re-discovering the same things or contradicting earlier decisions.

### Sections

| Section | What It Tracks | Who Writes |
|---------|---------------|------------|
| **Domain Terminology** | Agreed terms — used in all code, names, and docs | BA, ProductEx |
| **Codebase Behaviour** | What exists and how it's set up | BA, Architect, Analyst, Developer, ProductEx |
| **Key Decisions** | Decisions and rationale | Architect, Designer, Developer, Reviewer |
| **Constraints** | Technical, business, regulatory constraints | BA, Architect, Analyst, Designer, Developer, SDET |
| **Risks & Concerns** | Flagged risks, tracked to resolution | Analyst, QA, Developer, Reviewer |
| **Open Questions** | `[ ]` open, `[x]` resolved | Any phase |
| **Rework Log** | Re-run cycles and reverts | Orchestrator |

### How Phases Use It

- **QA** converts every Constraint into a test scenario
- **Architect** checks Codebase Behaviour before proposing new structure
- **Developer** uses Domain Terminology in all variable and method names
- **Reviewer** verifies every Key Decision is reflected in the implementation

---

## Artifact Files

All artifacts are written to the path you provide:

```
docs/workflow/TICKET-123/
├── session-memory.md       ← shared cross-phase memory
├── brd-raw.md              ← extracted BRD (from PDF/DOCX/text)
├── brdQnA.md               ← product questions, conflicts, gaps
├── 00-ba.md                ← requirements, user stories, acceptance criteria
├── 01-architect.md         ← design, patterns, ADRs
├── 02-analyst.md           ← impact map, risks  (optional)
├── 03-designer.md          ← interfaces, contracts, pattern prescriptions
├── 04-qa.md                ← test scenarios, edge cases
├── 04b-business-tests.md   ← business test case listings with traceability
├── 05-sdet.md              ← test plan, RED confirmation, skeleton inventory
├── 06-developer.md         ← GREEN confirmation, implementation summary
└── 07-reviewer.md          ← review findings, blockers
```

---

## Development Guardrails

**File:** `.claude/skills/GUARDRAILS.md`

12 guardrail categories that every code-touching phase must follow. Violations are raised as blockers.

| ID | Category | Priority | Key Rule |
|----|----------|----------|----------|
| G-01 | Timezone & Date/Time | CRITICAL | UTC storage, `java.time` only, ISO-8601 |
| G-02 | Null Safety | HIGH | `Optional` returns, fail-fast, no silent nulls |
| G-03 | Security | CRITICAL | Parameterized queries, no secrets in code |
| G-04 | Performance | HIGH | No N+1 queries, batch operations |
| G-05 | Data Integrity | HIGH | Idempotency, optimistic locking |
| G-06 | API Design | HIGH | Consistent response wrappers, versioning |
| G-07 | Multi-Tenancy | CRITICAL | Tenant filter on EVERY query |
| G-08 | Observability | HIGH | Structured logging, correlation IDs |
| G-09 | Backward Compatibility | HIGH | No breaking changes without migration |
| G-10 | Concurrency | HIGH | Thread safety, proper synchronization |
| G-11 | Testing | HIGH | Unit + integration, no test interdependence |
| G-12 | AI-Specific (AIDLC) | CRITICAL | Read existing code first, follow patterns |

**CRITICAL** = Violation is an automatic merge blocker.
**HIGH** = Flagged in review, must justify if deviating.

---

## Rework Loops & Circuit Breakers

Phases actively challenge each other. When something is wrong upstream, a phase raises a **blocker** rather than working around it.

### How Blockers Work

1. **Phase raises blocker** → identifies the target phase that needs rework
2. **Orchestrator classifies severity** → critical (needs your approval) or trivial (auto-handled)
3. **Target phase re-runs** with blocker details injected into its prompt
4. **Intermediate phases cascade** — all phases between the re-run target and the blocker source also re-run
5. **Circuit breaker** — if the same phase is re-run twice without resolution, the workflow stops and escalates to you

### Critical vs Trivial

| Critical (your approval needed) | Trivial (auto-handled) |
|--------------------------------|----------------------|
| Invalidates a decision you approved | Naming inconsistency |
| Violates codebase patterns | Missing edge case |
| Deviates from BA requirements | Minor interface refinement |
| Security flaw | |
| Tech debt with no mitigation | |

### Circuit Breaker (max 2 cycles)

If a phase has been re-run twice and the blocker persists:
```
🔴 Rework loop unresolved after 2 cycles.

Your options:
  A. Revisit an earlier phase
  B. Accept the deviation with noted risks
  C. Mark as known risk and proceed
  D. Take manual control
```

### Architect-Analyst-ProductEx Verification Cycle

A special cycle between Architect, Analyst, and ProductEx (max 3 iterations):
- Analyst consults ProductEx to verify Architect's solution fulfils requirements
- If issues found → Architect re-runs → Analyst re-verifies
- After 3 cycles without resolution → escalates to you with concrete options

---

## Optional Enhancements

### LSP (jdtls) — Semantic Code Navigation

Without LSP, phases navigate the codebase using grep and file reads. With LSP, they gain:
- Go-to-definition, find-all-references
- Incoming call chains, type hierarchy
- Semantic diagnostics (unresolved symbols)

The workflow automatically checks LSP status and falls back if unavailable.

**Setup:**
```bash
python ~/.jdtls-daemon/jdtls.py start <project_root>
```

### Historian MCP — Cross-Session Memory

Enables searching prior conversation history for architectural decisions, resolved errors, and past tutor sessions.

**Setup:**
```bash
claude mcp add claude-historian-mcp -- npx claude-historian-mcp
```

---

## Troubleshooting

### "Agent not found"

Make sure you're running from inside the project directory (where `.claude/agents/aidlc.md` lives):
```bash
cd /path/to/your/project
claude --agent aidlc
```

### "Session memory not found"

The workflow creates `session-memory.md` at the artifacts path you provide. If resuming, make sure you use the same path:
```bash
claude --agent aidlc -p "status docs/workflow/TICKET-123/"
```

### Build/test errors during Developer phase

The Developer agent runs `mvn compile` and `mvn test` via terminal. If builds fail, it reads the error output and fixes — same TDD cycle, just without IntelliJ. If jdtls is running, it also gets semantic diagnostics for faster error resolution.

### Revert not showing code changes

Code changes are only tracked for Developer (Phase 05) and SDET (Phase 06). Other phases produce only artifact files. If you revert to before Developer, there are no code changes to revert — only artifact files are deleted.

### "Permission denied" errors

If Claude Code asks for tool permissions frequently, you can run with pre-approved edit permissions:
```bash
claude --agent aidlc --permission-mode acceptEdits
```

---

## File Structure

```
.claude/
├── agents/
│   └── aidlc.md                  ← Agent definition (entry point)
│
├── skills/                        ← Phase skill definitions
│   ├── ba/SKILL.md               ← Business Analyst
│   ├── architect/SKILL.md        ← Architect
│   ├── analyst/SKILL.md          ← Impact Analyst
│   ├── designer/SKILL.md         ← Interface Designer
│   ├── qa/SKILL.md               ← QA
│   ├── developer/SKILL.md        ← Developer (TDD)
│   ├── sdet/SKILL.md             ← SDET
│   ├── reviewer/SKILL.md         ← Reviewer
│   ├── productex/SKILL.md        ← Product Expert
│   ├── workflow/SKILL.md         ← Orchestration logic
│   ├── debug/SKILL.md            ← Debugger (standalone)
│   ├── tutor/SKILL.md            ← Codebase Tutor (standalone)
│   ├── GUARDRAILS.md             ← Development guardrails (12 categories)
│   ├── README.md                 ← Skills quick reference
│   └── README-AIDLC.md          ← This file
│
└── settings.json                  ← Project settings

docs/
├── product/
│   ├── registry.md               ← Product knowledge base (ProductEx)
│   ├── brd-standards.md          ← BRD writing standards for PM team
│   └── brd-template.md           ← Blank BRD template
│
└── workflow/
    └── <TICKET-ID>/              ← Per-ticket artifacts
        ├── session-memory.md
        ├── brd-raw.md
        ├── brdQnA.md
        ├── 00-ba.md
        ├── 01-architect.md
        ├── 02-analyst.md
        ├── 03-designer.md
        ├── 04-qa.md
        ├── 04b-business-tests.md
        ├── 05-sdet.md
        ├── 06-developer.md
        └── 07-reviewer.md
```

---

## Standalone Skills (Not Part of Pipeline)

These can be invoked any time, independent of the workflow:

| Command | What It Does |
|---------|-------------|
| `claude --agent aidlc -p "phase debug"` | Root cause analysis — correlates code, logs, terminal output |
| `/tutor` | Codebase teaching mode — explains code without modifying it |
| `/productex discover` | Scan codebase and build product registry |
| `/productex query <question>` | Answer product questions from registry |
| `/productex brd-check <file>` | Validate a BRD against standards |

---

## Tips

- **Use the BA phase even for small changes** — the Q&A reliably surfaces hidden assumptions
- **The Architect's pattern table is the most valuable output** — read the tradeoff analysis carefully before continuing
- **Each phase actively challenges the previous one** — if something is wrong upstream, it raises a blocker
- **Open Questions in session memory are your audit trail** — any unresolved `[ ]` item that reaches the Reviewer is an automatic blocker
- **Revert is safe** — git snapshots mean you can always go back to any phase's exact state
- **You never need IntelliJ during Developer phase** — builds, tests, and code navigation all run inside the agent
