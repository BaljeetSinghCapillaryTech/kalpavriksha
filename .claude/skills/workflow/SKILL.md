---
name: workflow
description: Orchestrates the full multi-phase development workflow. Runs BA → Architect → Analyst (optional) → Designer → QA → Developer → SDET (optional) → Reviewer in sequence, pausing between phases for approval. Use when user says /workflow.
---

# Workflow Orchestrator

Orchestrate the full multi-phase development workflow. Each phase adopts its own persona, reads session memory, writes its artifact and updates session memory, then pauses for approval before the next phase begins.

## Invocation

```
/workflow <artifacts-path> [brd:<path-or-text>] [skip:analyst] [skip:sdet]
```

Examples:
- `/workflow docs/workflow/TICKET-123/` — full workflow, BRD provided as conversation text
- `/workflow docs/workflow/TICKET-123/ brd:downloads/feature-spec.pdf` — BRD from PDF
- `/workflow docs/workflow/TICKET-123/ brd:docs/requirements.docx` — BRD from Word doc
- `/workflow docs/workflow/TICKET-123/ skip:analyst,sdet` — skip optional phases

If no artifacts path is provided, ask the user for one before starting.

### BRD Input Resolution

The workflow needs a BRD (Business Requirements Document) as input for BA and ProductEx. Resolve it in this order:

1. **`brd:` parameter provided with a file path** — detect format by extension:
   - `.pdf` → use the PDF skill to read and extract text
   - `.docx` → use the DOCX skill to read and extract text
   - `.md` or `.txt` → read the file directly
   - Any other extension → attempt to read as plain text; if it fails, ask the user for the correct format

2. **`brd:` parameter not provided** — check conversation context:
   - If the user pasted BRD text in the conversation before invoking `/workflow` → use that text
   - If no BRD text is visible in conversation → prompt the user:

   ```
   📄 No BRD detected. Please provide the requirements in one of these ways:
      1. Paste the BRD text here
      2. Provide a file path: `/workflow <path> brd:path/to/file.pdf`
      3. Provide a file path: `/workflow <path> brd:path/to/file.docx`
   ```

   Do not proceed until the BRD is available.

3. **After extraction** — save the raw BRD content to `<artifacts-path>/brd-raw.md` for traceability. This becomes the single source of truth that BA and ProductEx both reference. If the original was PDF/DOCX, note the source file path at the top:
   ```markdown
   > Source: [original file path]
   > Format: [PDF | DOCX | text]
   > Extracted: [timestamp]

   ---
   [extracted BRD content]
   ```

Do not proceed to Step -1 (LSP init) until BRD input is resolved and `brd-raw.md` is written.

### Knowledge Bank

The knowledge bank file lives at `.claude/skills/knowledge-bank.md` in the repo. It is a permanent file — the human populates it before running the pipeline for each epic/story.

At workflow start, read `.claude/skills/knowledge-bank.md`. If it has content beyond the template comments, note it: "Knowledge bank has content — BA will use it to resolve concerns before asking questions." If it is empty (only template), note: "Knowledge bank is empty — BA will ask all questions directly."

Do not create or overwrite this file. It is the human's responsibility to populate it before running the pipeline.

## Phase Sequence

```
[ProductEx BRD Review] ──parallel──▶ ┐
                                      ├─▶ BA Review Gate ─▶ Architect (01) → ...
[BA (00) Q&A] ────────interactive──▶ ┘

BA (00) → Architect (01) → Analyst (02, optional) → Designer (03) → QA (04) → Developer (05) → SDET (06, optional) → Reviewer (07)
```

---

## Step -1: Initialise LSP (jdtls)

Before anything else, spawn the `lsp-init` subagent to ensure the jdtls daemon is running for the project root.

**Derive the project root**: use the artifacts path to infer the repo root (e.g. if artifacts path is `docs/workflow/TICKET-123/`, the project root is likely the repo root where that path lives — confirm with the user if ambiguous).

Spawn the `lsp-init` subagent:
```
subagent: lsp-init
input: project_root = <derived project root>
```

Wait for the subagent to return `LSP_STATUS: ready | unavailable`.

- If `ready`: all subsequent analytical subagents (Architect, Analyst, Designer, QA, SDET, Reviewer) can use `python ~/.jdtls-daemon/jdtls.py` commands for code traversal.
- If `unavailable`: all phases fall back to grep/file reads for code traversal. Note this in session memory under Constraints: `- LSP unavailable: using grep/file reads for code traversal _(workflow)_`

Do not proceed to Step 0 until LSP status is known.

---

## Step 0: Initialise Session Memory

Before starting BA, create `session-memory.md` in the artifacts path with this template:

```markdown
# Session Memory

> Artifacts path: [path]
> Workflow started: [phase/timestamp]

---

## Domain Terminology
_Populated by BA from product docs and requirements. Use these terms consistently across all phases._

## Codebase Behaviour
_What was found in the codebase and docs, and how it behaves/is set up. Updated by each phase._

## Key Decisions
_Significant decisions and their rationale. Format: `- [decision]: [rationale] _(phase)_`_

## Constraints
_Technical, business, and regulatory constraints all phases must respect. Format: `- [constraint] _(phase)_`_

## Risks & Concerns
_Flagged risks and concerns. Format: `- [risk] _(phase)_ — Status: open/mitigated`_

## Open Questions
_Unresolved questions. Format: `- [ ] [question] _(phase)_` or `- [x] resolved: answer _(phase)_`_

## Rework Log
_Tracks re-run cycles to detect unresolved loops. Format: `- [Phase N] cycle [N]/2 — raised by [Phase X] — severity: trivial|critical — issue: [brief] — resolved: yes|no`_
```

If `session-memory.md` already exists at the path (resuming a workflow), read it and continue — do not overwrite.

Also read `.claude/skills/knowledge-bank.md` to check if the human has populated it for this epic.

---

## How to Run Each Phase

Phases fall into two categories with different execution modes:

### Interactive Phases (run in main context)

**BA (Phase 00)** and **Developer (Phase 05)** run in the main conversation context — never spawned as subagents.

- Adopt the persona as defined in the skill file
- Read `session-memory.md` and all prior artifacts
- Actively use session memory to shape output
- Produce output, write artifact, update session memory
- Show phase summary and pause for user approval

**BA is Q&A-driven**: ask one question at a time. Do not show the phase summary prompt until BA has completed its full Q&A and written `00-ba.md`. Wait for the user's answer after each question before asking the next.

#### Phase 00: Parallel Execution — BA + ProductEx BRD Review

When Phase 00 starts, two things happen simultaneously:

**1. Spawn ProductEx BRD Review as a background subagent:**

```
Agent tool:
  subagent_type: general-purpose
  run_in_background: true
  prompt: |
    You are ProductEx running in brd-review mode.

    Artifacts path: <artifacts-path>
    Session memory: <artifacts-path>/session-memory.md
    BRD file: <artifacts-path>/brd-raw.md

    Read the BRD from brd-raw.md (already extracted and saved by the orchestrator).
    Follow ProductEx brd-review mode exactly as defined in the skill.
    Read the product registry, official docs, and docs/product/ files.
    Analyse the BRD against all knowledge sources.
    Write your output to <artifacts-path>/brdQnA.md
    Update session-memory.md with findings.
    Return the structured summary.
```

**2. Start BA interactively in the main context** — BA reads `brd-raw.md` as its primary input, then proceeds with Step 1 (research) and Step 2 (analysis) while ProductEx works in the background.

BA will internally consult ProductEx (consult mode) and Architect (research-only mode) during its Step 3. See the BA skill for the full consultation protocol.

**Human Escalation during BA Phase:**
When BA's internal consultation with Architect returns `unresolved`, the workflow **pauses** and shows the user the question with full context. The user must respond before the AIDLC can resume. See BA skill Step 3b for the exact escalation format.

#### BA Phase Completion — Review Gate

After BA finishes its Q&A and writes `00-ba.md`, check if ProductEx BRD Review has completed:

- **If complete**: Read `brdQnA.md` and present it alongside the BA phase summary:
  ```
  ---
  ✅ BA complete → artifact written to [path/00-ba.md]
  📝 Session memory updated: [what was added]

  📋 ProductEx BRD Review complete → [path/brdQnA.md]
     - [count] questions for product team
     - [count] conflicts with current product
     - [count] blocking gaps

  ⚠️  Blocking product gaps that need resolution before proceeding:
     [list blocking gaps from brdQnA.md — or "None"]

  Next: Architect (01)
  Type `continue` to proceed, or address the blocking gaps first.
  ---
  ```

- **If blocking gaps exist in brdQnA.md**: Do NOT proceed to Architect until the user resolves them or explicitly chooses to proceed with gaps noted as risks.

- **If still running**: Wait for it to complete before showing the phase summary. Notify the user: "Waiting for ProductEx BRD review to complete..."

### Reviewer Requirements Gap Handling

When Reviewer returns blockers with `TARGET: [Phase Name]` from the Requirements Traceability review, the orchestrator presents the human with a choice for **each** gap (or grouped by target phase):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Reviewer found requirements gaps in artifact(s):

[For each target phase with gaps:]
  🔴 [Phase Name] ([NN-artifact.md]) — [count] gap(s):
     • REQ-[ID]: [requirement] — [what's missing]
     • REQ-[ID]: [requirement] — [what's missing]

Options:
  [A] Rerun from [earliest affected phase]
      Re-runs [Phase] → all downstream phases → Reviewer.
      Fixes cascade automatically through the pipeline.

  [B] Verify manually
      Mark gaps as acknowledged. You review and fix them yourself.
      Reviewer proceeds to code review with gaps noted as known issues.

  [C] Accept as known risk
      Log gaps in session memory as accepted risks and proceed to merge.

Enter choice (A/B/C) [per phase, or a single choice for all]:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Option A — Rerun from phase:**
- Follow the existing Rework Loop / Cascade Rules (inject the requirements gap as a BLOCKER into the target phase's prompt)
- After the cascade completes, Reviewer re-runs its full flow (build → traceability → code review)
- Track in Rework Log: `- [Phase N] requirements gap — raised by Reviewer — REQ-[IDs] — resolved: yes|no`

**Option B — Verify manually:**
- Human fixes the issue themselves (edits artifacts, code, or both)
- When the human says `continue`, Reviewer re-runs the full flow to verify
- If gaps persist, show the prompt again

**Option C — Accept as known risk:**
- Log each gap in session memory under `## Risks & Concerns`: `- [risk] REQ-[ID] gap in [Phase]: [description] _(Reviewer)_ — Status: accepted`
- Reviewer proceeds to code review, noting accepted gaps in the review output

Do not proceed to code review until the human makes a decision for all requirements gaps.

---

### Analytical Phases (spawn as subagents)

**Architect (01), Analyst (02), Designer (03), QA (04), SDET (06), Reviewer (07)** run as isolated subagents via the Agent tool. Each subagent starts with clean context and reads artifacts + session memory as its sole source of truth.

Spawn each analytical phase like this:

```
Agent tool:
  subagent_type: general-purpose
  prompt: |
    You are running as the [Phase Name] phase in a multi-phase development workflow.

    Artifacts path: <artifacts-path>
    Session memory: <artifacts-path>/session-memory.md

    Follow the [Phase Name] skill exactly as defined. Your tasks:
    1. Read session-memory.md and all prior artifacts in the artifacts path
    2. Perform the full [phase name] analysis/design
    3. Write your output to <artifacts-path>/[NN-phase.md]
    4. Append your findings to session-memory.md as specified in your skill
    5. Return the structured summary in the exact format below

    Return format (must be exact):
    PHASE: [Phase Name]
    STATUS: complete | blocked
    ARTIFACT: [NN-phase.md]

    SUMMARY:
    - [summary line 1]
    - [summary line 2]
    ...

    BLOCKERS:
    - TARGET: [phase name that needs rework] | ISSUE: [what specifically needs to change]
    (use "None" if no blockers)

    SESSION MEMORY UPDATES:
    - [what was added to which sections]
```

**After the subagent returns**, extract the structured summary and display the phase summary prompt to the user. Do not proceed until the user approves.

## Git Snapshot Protocol

Create lightweight git tags after each phase to enable safe revert. This is critical for the revert system.

### At Workflow Start

Create a dedicated branch from current HEAD:
```bash
git checkout -b aidlc/<ticket-id>
```
Derive `<ticket-id>` from the artifacts path (e.g., `docs/workflow/TICKET-123/` → `TICKET-123`). If the branch already exists (resuming), check it out without creating.

### After Each Phase Completes

1. **Stage and commit artifact files:**
   ```bash
   git add <artifacts-path>/*.md
   git commit -m "aidlc: <phase-name> phase complete"
   ```

2. **For code-writing phases (Developer, SDET)** — also stage code changes:
   ```bash
   git add -A
   git commit -m "aidlc: <phase-name> phase complete — <brief summary>"
   ```

3. **Create/update tag:**
   ```bash
   git tag -f aidlc/<ticket-id>/phase-<NN>
   ```
   Where NN = 00 (BA), 01 (Architect), 02 (Analyst), 03 (Designer), 04 (QA), 05 (Developer), 06 (SDET), 07 (Reviewer).

---

## Pausing and Approval

After each phase (except during BA Q&A), output exactly this prompt:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ [Phase Name] complete → artifact written to [path/NN-phase.md]
📝 Session memory updated: [brief list of what was added]
🏷️  Snapshot: aidlc/<ticket-id>/phase-<NN>

⚠️  Blockers: [list or "None"]

Next: [Next Phase Name] (Phase NN)

Commands:
  continue    — proceed to next phase
  skip        — skip next phase (if optional)
  api-handoff — generate API contract doc for UI team (available after Designer or Developer)
  revert      — roll back to a previous phase
  status      — show full workflow progress
  exit        — save state and exit (resume later)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Do not proceed until the user responds. Handle each command as described below.

### API Handoff Command

When the user types `api-handoff` at any pause prompt (typically after Designer or Developer):

1. Spawn the API Handoff skill as a subagent:
   ```
   Agent tool:
     subagent_type: general-purpose
     prompt: |
       You are running the API Handoff skill.
       Artifacts path: <artifacts-path>
       Follow the api-handoff skill exactly as defined in .claude/skills/api-handoff/SKILL.md.
       Read the skill file first, then execute all steps.
       Write output to <artifacts-path>/api-handoff.md
       Return the structured summary.
   ```
2. Display the result and return to the same pause prompt (do not advance to the next phase).

## Architect-Analyst-ProductEx Verification Cycle

When Analyst (Phase 02) is not skipped, a dedicated verification cycle runs between Architect, Analyst, and ProductEx. This cycle ensures the Architect's solution fulfils product requirements before proceeding to Designer.

### How the Cycle Works

```
Architect (01) → Analyst (02) + ProductEx verify
                      │
                      ├─ ProductEx approved → proceed to Designer (03)
                      │
                      └─ ProductEx changes_needed → Analyst raises BLOCKER → Architect re-runs
                            │
                            └─ cycle repeats (max 3 times)
```

**Cycle 1** (initial run):
1. Architect produces `01-architect.md` (normal Phase 01 execution)
2. Pause for user approval
3. Analyst runs as subagent — performs impact analysis, then consults ProductEx in `verify` mode
4. **All conversations are visible to the user** — after Analyst returns, show the full summary including ProductEx's verification result

**If Analyst returns `STATUS: complete` (no blockers)**:
- ProductEx approved the solution
- Show phase summary with ProductEx verification results
- Proceed to Designer after user approval

**If Analyst returns `STATUS: blocked` with product requirement issues**:
- Show the user the full details:

```
---
⚠️ Analyst complete but raised blockers against Architect's solution.

📋 Impact Analysis findings:
   [list Analyst's own impact findings]

📋 Product Requirements Verification (ProductEx):
   - Requirements fulfilled: [X/Y]
   - Issues found: [count]
   [list each issue with evidence and suggested direction]

🔄 Verification cycle: [1/3 | 2/3 | 3/3]

This will trigger Architect to re-run and address these issues.
Type `continue` to proceed with the rework cycle, or `resolve` to handle manually.
---
```

- Wait for user approval
- Re-run Architect with the blocker details appended to its prompt (including ProductEx's evidence and suggested directions)
- After Architect re-runs, re-run Analyst (which re-consults ProductEx)
- This is **one cycle**

### Cycle Limit: 3

The Architect-Analyst-ProductEx verification cycle can repeat **at most 3 times**. Track in session memory:

```
## Verification Cycle Log
- Cycle 1/3: [issue summary] — resolved: yes|no
- Cycle 2/3: [issue summary] — resolved: yes|no
- Cycle 3/3: [issue summary] — resolved: yes|no
```

### After 3 Cycles — Human Escalation

If after 3 cycles ProductEx still returns `changes_needed`, the workflow **stops** and escalates to the human:

```
🔴 Architect-Analyst-ProductEx verification cycle exhausted (3/3 cycles).

The solution and product requirements could not be fully reconciled after 3 iterations.

Resolved in previous cycles:
  [list issues that were resolved and in which cycle]

Still unresolved:
  [list each remaining issue with full evidence chain from ProductEx]

Open product questions (from brdQnA.md):
  [list any unresolved questions that may be contributing to the impasse]

Your options:
  A. Manually adjust the Architect's solution — tell me what to change in 01-architect.md
  B. Accept the current solution with noted gaps — mark unresolved issues as known risks
  C. Revisit BA requirements — if the product requirements themselves need refinement
  D. Consult the product team — take the unresolved items offline for product team input

What would you like to do?
```

Do not proceed to Designer until the user makes a decision. Implement their choice, then continue.

### Visibility Rule

**Every cycle is visible to the user.** After each Architect re-run and each Analyst re-run, show the phase summary with:
- What Architect changed in this cycle
- What Analyst + ProductEx found in this cycle
- What was resolved vs what remains
- Current cycle count (e.g. "Cycle 2/3")

The user can intervene at any pause point by typing `resolve` to take manual control.

---

## Handling Blockers — Rework Loop

When a phase returns a BLOCKER with a TARGET, follow this process:

---

### Step 1: Check the Circuit Breaker First

Before doing anything else, read the `## Rework Log` in session memory. If the TARGET phase has already been re-run **2 times** for the same issue → skip to **Circuit Breaker** below. Do not re-run a third time.

---

### Step 2: Classify Severity

The **orchestrator** classifies the blocker — not the phase that raised it. A blocker is **critical** if it meets any of:

1. Invalidates a decision previously approved by the user (check `## Key Decisions` in session memory)
2. Violates existing architectural patterns found in the codebase
3. Violates known design approaches established earlier in the workflow
4. Deviates from requirements defined by BA
5. Introduces a security flaw
6. Introduces potential tech debt with no mitigation plan

If none of the above apply → **trivial**.

---

### Step 3: Handle by Target Type

#### TARGET = BA

BA resolves blockers by asking the human — not by being re-run as a subagent. Always human in the loop regardless of severity.

```
⚠️ [Phase X] raised a blocker that requires BA clarification:
Issue: [description]
BA will ask you a clarifying question now.
```

BA then re-engages with one targeted question. Once resolved, workflow resumes from the phase immediately after BA (Architect), re-running all phases forward to the one that raised the blocker.

---

#### TARGET = Developer (interactive phase)

Developer resumes in main context with the blocker injected as additional input. Apply severity handling:

- **Trivial**: notify ("⚠️ Trivial blocker — Developer resuming with fix: [issue brief]"), resume Developer in main context, then cascade forward.
- **Critical**: pause, show user the issue and which criterion it violates, wait for approval, then resume Developer.

---

#### TARGET = Analytical Phase (Architect, Analyst, Designer, QA, SDET)

**Trivial blocker:**
```
⚠️ Trivial blocker → re-running [Phase N] automatically.
Issue: [brief description]
Cascading forward after re-run: [list of phases to re-run in order]
```
- Re-run Phase N subagent with the blocker appended to its prompt
- Cascade: re-run each phase from N+1 to current-1 in order (notify at each step, don't wait)
- Re-run the phase that raised the blocker

**Critical blocker:**
```
🚨 Critical blocker — [Phase N] needs rework before we can continue.
Issue: [description]
Criterion: [which of the 6 criteria above]

Awaiting your approval to re-run [Phase N].
```
- Wait for user approval
- Re-run Phase N subagent with the blocker appended to its prompt
- Pause: "Phase N updated. Ready to cascade forward through: [list of intermediate phases]. Type `continue` to proceed."
- Wait for approval, then cascade forward with normal approval gates at each phase

---

### Cascade Rules

When Phase N is re-run, these intermediate phases must also be re-run in order before returning to the phase that raised the blocker:

| Re-run target | Cascade through before returning to blocker source |
|---|---|
| Architect (01) | Analyst (if not skipped) → Designer → QA |
| Analyst (02) | Designer → QA |
| Designer (03) | QA |
| QA (04) | _(none — Developer re-engages directly)_ |
| Developer (05) | SDET (if not skipped) |
| SDET (06) | _(none — Reviewer re-runs directly)_ |
| BA (00) | Architect → Analyst (if not skipped) → Designer → QA |

---

### After Each Re-run: Update Rework Log

Append to `## Rework Log` in session memory:
```
- [Phase N] cycle [1 or 2]/2 — raised by [Phase X] — severity: trivial|critical — issue: [brief] — resolved: yes|no
```

---

### Circuit Breaker (2 cycles exhausted)

If Phase N has been re-run twice and the blocker persists, stop and escalate:

```
🔴 Rework loop unresolved after 2 cycles for [Phase N].

The conflict:
  [Phase X] requires: [what it needs]
  [Phase N] produces: [what it currently outputs]
  These are incompatible because: [reason]

Your options:
  A. Revisit [an earlier phase] — [what would need to change and the implication]
  B. Accept the deviation — [risk or consequence of proceeding as-is]
  C. Mark as known risk in session memory and proceed
  D. [other option if the conflict suggests one]

What would you like to do?
```

Do not proceed until the user makes a decision. Implement their choice, then continue the workflow.

## In-Session Commands

These commands are available at every pause prompt. The orchestrator must handle all of them.

### `continue`
Proceed to the next phase. Standard flow.

### `skip`
Skip the next phase. Only allowed for optional phases (Analyst, SDET). If the user tries to skip a non-optional phase, refuse:
```
⚠️  [Phase Name] is not optional. Type `continue` to proceed or `revert` to roll back.
```

### `revert`
Open the revert flow. See **Revert Protocol** below.

### `revert to <N>`
Quick revert to phase N. Skip the phase selection step and go directly to the impact display + revert type choice.

### `status`
Show the full workflow progress dashboard:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 AIDLC Workflow Status

Artifacts path: [path]
Git branch: aidlc/[ticket-id]
Started: [timestamp from session-memory.md]

Phase Progress:
  ✅ [0] BA              → 00-ba.md
  ✅ [1] Architect       → 01-architect.md
  ✅ [2] Analyst         → 02-analyst.md
  🔄 [3] Designer        → (in progress)
  ⬜ [4] QA              → (pending)
  ⬜ [5] Developer       → (pending)
  ⬜ [6] SDET            → (pending)
  ⬜ [7] Reviewer        → (pending)

Open Blockers: [list or "None"]

Rework History: [list or "None"]

Open Questions:
  [list from session-memory.md or "None"]

Git Snapshots:
  [list existing tags]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

After showing status, return to the pause prompt.

### `exit`
Save state and exit. The user can resume later. Session memory and artifacts persist on disk. Git tags preserve snapshot state. To resume:
- Within Claude Code: `/workflow <same-artifacts-path>` (detects existing session-memory.md)
- From terminal: `claude --agent aidlc --continue`

### `resolve`
Take manual control of a blocker. Only relevant during rework cycles. See Handling Blockers section.

---

## Revert Protocol

When the user types `revert` (or `revert to <N>`) at any pause point:

### Step 1: Scan Workflow State

Read the artifacts path and determine completed phases:
- Check which artifact files exist (00-ba.md through 07-reviewer.md)
- Check git tags (`git tag -l "aidlc/<ticket-id>/phase-*"`)
- Read session-memory.md for phase entries
- For code-writing phases (Developer, SDET): use `git diff` between consecutive tags to count changed files

Display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 REVERT — Scanning workflow state...

Artifacts path: [path]
Git branch: aidlc/[ticket-id]

Completed phases:
──────────────────
✅ [0] BA              → 00-ba.md                      (artifacts only)
✅ [1] Architect       → 01-architect.md               (artifacts only)
✅ [2] Analyst         → 02-analyst.md                 (artifacts only)
✅ [3] Designer        → 03-designer.md                (artifacts only)
✅ [4] QA              → 04-qa.md                      (artifacts only)
✅ [5] Developer       → 05-developer.md + CODE CHANGES (N files)
⬜ [6] SDET            → (pending)
⬜ [7] Reviewer        → (pending)

Revert to which phase? (enter 0-5, or 'cancel'):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If the user said `revert to <N>`, skip this step and go to Step 2 directly.

### Step 2: Show Impact

After the user picks a target phase (e.g., 3 = Designer), show exactly what will be affected:

- **Artifacts to delete**: list artifact files from phases after the target
- **Code changes to revert**: use `git diff` between the target tag and HEAD to list changed source files (not artifact files)
- **Session memory entries to remove**: entries tagged with phases after the target (identified by `_(PhaseName)_` suffix)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVERT TARGET: Designer (Phase 3)

This will discard everything AFTER Designer:

  ARTIFACTS to delete:
    • [path]/04-qa.md
    • [path]/05-developer.md

  CODE CHANGES to revert (from Developer phase):
    • src/.../TierServiceImpl.java           (modified)
    • src/.../TierController.java            (modified)
    • src/.../TierBenefit.java               (new file)
    • ... +N more files

  SESSION MEMORY: entries from QA, Developer will be removed

Options:
  [A] Full revert
      Delete artifacts + revert code + clean session memory.
      Restores codebase to exact state after Designer completed.

  [B] Artifacts only
      Delete artifact files + clean session memory.
      Keep code changes intact.

  [C] Re-run from here
      Keep everything. Re-run from Designer onward, overwriting artifacts.

  [D] Cancel — go back

Enter choice (A/B/C/D):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 3: Execute Revert

**Option A — Full revert:**
```bash
git reset --hard aidlc/<ticket-id>/phase-<NN>
```
Then programmatically clean session-memory.md: remove all entries tagged with phases after the target. Add to Rework Log: `- Revert to [Phase N] — full revert — requested by user — [timestamp]`

**Option B — Artifacts only:**
```bash
rm <artifacts-path>/04-qa.md <artifacts-path>/05-developer.md ...
```
Clean session-memory.md the same way. Code files are left untouched. Add to Rework Log: `- Revert to [Phase N] — artifacts only — requested by user — [timestamp]`

**Option C — Re-run from here:**
Do not delete or revert anything. The workflow will re-run from the target phase, and each phase will overwrite its own artifact. Add to Rework Log: `- Re-run from [Phase N] — requested by user — [timestamp]`

### Step 4: After Revert — Next Steps

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Reverted to [Phase Name] (Phase N)
   [Summary of what was reverted]

What next?
  [1] Continue workflow from [Next Phase] (Phase N+1)
  [2] Re-run [Phase Name] (Phase N) with modifications
  [3] Exit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Wait for user choice, then proceed accordingly.

### Revert Safety Rules

1. **Always confirm before executing** — never auto-revert
2. **Always show file-level impact** — user must see exactly what changes before confirming
3. **Git tags are force-updated** (`-f`) when a phase is re-run after revert
4. **Session memory cleanup is surgical** — only remove entries identified by the `_(PhaseName)_` suffix for reverted phases
5. **Rework Log is always preserved** — reverts are logged, never cleaned
6. **Never revert past the branch creation point** — the aidlc branch start is the hard floor

---

## Optional Phases

- **Analyst** (`02-analyst.md`): Skipped if `skip:analyst` provided. If skipped, Designer proceeds using only Architect output.
- **SDET** (`06-sdet.md`): Skipped if `skip:sdet` provided. If skipped, Reviewer proceeds using Developer output directly.

## Artifact Files

| Phase | Artifact | Session Memory Sections Written |
|---|---|---|
| Orchestrator (pre-phase) | `brd-raw.md` | _(none — raw input only)_ |
| ProductEx BRD Review | `brdQnA.md` | Domain Terminology, Codebase Behaviour |
| BA | `00-ba.md` + `docs/product/<feature>.md` | Terminology, Codebase Behaviour, Constraints, Key Decisions, Open Questions |
| Architect | `01-architect.md` | Codebase Behaviour, Key Decisions, Constraints, Open Questions |
| Analyst | `02-analyst.md` | Codebase Behaviour, Risks & Concerns, Constraints, Open Questions |
| Designer | `03-designer.md` | Key Decisions, Constraints, Open Questions |
| QA | `04-qa.md` | Risks & Concerns, Open Questions |
| Developer | `05-developer.md` | Codebase Behaviour, Key Decisions, Constraints, Risks & Concerns |
| SDET | `06-sdet.md` | Constraints, Open Questions |
| Reviewer | `07-reviewer.md` | Risks & Concerns, Open Questions, Key Decisions |

## Constraints

- Never skip a non-optional phase without explicit user instruction
- Never run the next phase without user approval
- Always initialise or read session memory before the first phase
- Always write artifact and update session memory before pausing
- Each phase must read all prior artifacts and session memory before producing output
- Maintain persona boundaries: do not let one phase do another phase's work
- BA must complete its full Q&A before the workflow advances to Architect
