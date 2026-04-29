# Sonar Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local JaCoCo-based coverage gate (Phase 10a) to the feature pipeline that warns developers when new-code line coverage is below 90%, generates UT stubs for uncovered methods, and requires no pom.xml changes or CI involvement.

**Architecture:** Three file changes — a new `/sonar-gate` skill that runs JaCoCo via Maven CLI and parses `jacoco.xml` for new-code coverage, a surgical addition to the SDET skill for an end-of-phase traceability check, and a new Phase 10a entry in the pipeline orchestrator. The skill is standalone-invocable and also wired into the pipeline between Developer (Phase 10) and Backend Readiness (Phase 10b).

**Tech Stack:** Markdown (skill authoring), Bash (Maven + git commands Claude runs), Python (jacoco.xml XML parsing), JaCoCo 0.8.11 via Maven CLI plugin invocation.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `.claude/skills/sonar-gate/SKILL.md` | **Create** | Full sonar-gate skill — 7-step execution protocol, remediation loop, artifact output |
| `.claude/skills/sdet/SKILL.md` | **Edit** | Append traceability check section after Stage 2 output requirements |
| `.claude/agents/feature-pipeline.md` | **Edit** | Insert Phase 10a block between Phase 10 and Phase 10b |

---

## Task 1: Create the `/sonar-gate` skill

**Files:**
- Create: `.claude/skills/sonar-gate/SKILL.md`

- [ ] **Step 1: Create the skills directory**

```bash
mkdir -p .claude/skills/sonar-gate
```

Expected: directory created, no output.

- [ ] **Step 2: Write the SKILL.md file**

Write `.claude/skills/sonar-gate/SKILL.md` with exactly this content:

````markdown
---
name: sonar-gate
description: Local coverage gate — Phase 10a. Runs JaCoCo via Maven CLI (no pom.xml change), measures new-code line coverage against main, warns if below 90%, generates UT stubs for uncovered methods. Standalone or pipeline. Use when user says /sonar-gate, [sonar-gate], or SonarGate:.
phase: "10a"
triggers: [sonar-gate, /sonar-gate, SonarGate]
inputs: [git diff vs main, target/site/jacoco/jacoco.xml (generated), session-memory.md (optional)]
outputs: [sonar-gate.md]
---

## Reasoning Principles

Read `.claude/principles.md` at phase start if available. Apply throughout:
- **Every claim carries a confidence level (C1–C7)** — no unqualified assertions
- **Reversibility determines action threshold** — reversible + C4 = act; irreversible + below C4 = STOP and escalate
- **Never make coverage claims without reading the actual jacoco.xml**

# Sonar Gate — Local Coverage Check (Phase 10a)

You are a local coverage enforcement skill. Your job is to measure new-code line coverage on the current branch, warn the developer if it falls below 90%, and help them close the gap before pushing — so CI never fails on coverage.

You run after Developer (Phase 10) and before Backend Readiness (Phase 10b). You can also be invoked standalone at any time.

---

## Invocation Arguments

| Argument | Default | Effect |
|---|---|---|
| `--threshold N` | 90 | Override coverage threshold (e.g. `--threshold 80`) |
| `--file <path>` | all new files | Restrict analysis to a single file |

---

## Step 1 — Identify New/Changed Production Files

Run:

```bash
git diff main --name-only -- 'src/main/java/**.java'
```

This lists Java source files changed on the current branch vs `main`. Test files are excluded because they live under `src/test/`.

**If the list is empty:** Print `✓ PASS — no new production Java files on this branch.` Write a PASS `sonar-gate.md` (see Step 7 format). Exit.

**If `--file` argument was provided:** Replace the full list with just that one file. Verify it exists with `ls <path>`; if not found, print an error and exit.

---

## Step 2 — Run JaCoCo Locally via Maven CLI

Run this command from the project root (no pom.xml modification required):

```bash
mvn org.jacoco:jacoco-maven-plugin:0.8.11:prepare-agent \
    test \
    org.jacoco:jacoco-maven-plugin:0.8.11:report \
    -Dproject.reporting.outputEncoding=UTF-8
```

Maven resolves JaCoCo from your local `.m2` cache or downloads it on first run (internet required on first use only).

**Expected output:** `target/site/jacoco/jacoco.xml` is created.

**If Maven fails:**
- Surface the last 30 lines of Maven output to the developer.
- Print: `✗ BUILD FAILED — cannot compute coverage on a broken build. Fix compilation/test errors first.`
- Do NOT attempt to parse jacoco.xml.
- Exit.

**Verify the report exists:**

```bash
ls target/site/jacoco/jacoco.xml
```

If missing after a successful Maven run, print: `jacoco.xml not generated — JaCoCo may not have instrumented any classes. Check that tests reference the correct source directories.` and exit.

---

## Step 3 — Parse `jacoco.xml` and Filter to New Files

Use this Python snippet to extract per-file coverage from `target/site/jacoco/jacoco.xml`:

```python
import xml.etree.ElementTree as ET, sys, os

new_files = sys.argv[1:]  # passed as space-separated simple filenames (e.g. TierService.java)
tree = ET.parse('target/site/jacoco/jacoco.xml')
root = tree.getroot()

results = []
for pkg in root.findall('package'):
    for sf in pkg.findall('sourcefile'):
        if sf.get('name') in new_files:
            lines = [c for c in sf.findall('counter') if c.get('type') == 'LINE']
            if lines:
                missed = int(lines[0].get('missed', 0))
                covered = int(lines[0].get('covered', 0))
                total = missed + covered
                pct = round(covered / total * 100, 1) if total > 0 else 0.0
                results.append((sf.get('name'), covered, missed, total, pct))

for name, covered, missed, total, pct in results:
    print(f"{name}|{covered}|{missed}|{total}|{pct}")
```

Save this as a temp script and run:

```bash
python3 /tmp/parse_jacoco.py TierService.java TierValidationHelper.java SlabEvaluationStrategy.java
```

Pass only the **simple filename** (basename without path) for each new file — that is what `<sourcefile name="...">` uses in `jacoco.xml`.

**If a new file has no entry in jacoco.xml:** It means the file has 0 test coverage (JaCoCo never saw it). Treat it as `covered=0, missed=<all lines in file>, pct=0%`. Count the file's lines with:

```bash
wc -l < src/main/java/com/capillary/.../MissingClass.java
```

---

## Step 4 — Calculate Aggregate Coverage

```
aggregate_pct = sum(covered) / sum(total) * 100   (across all new files)
```

Round to one decimal place.

**Apply threshold:**
- `aggregate_pct >= threshold` → **PASS** (go to Step 7, write artifact, exit)
- `aggregate_pct < threshold` → **WARNING** (go to Step 5)

---

## Step 5 — Display Coverage Table and Prompt

Print the coverage table:

```
Coverage Report — New Code (branch vs main)
────────────────────────────────────────────────────────────────────────
File                                    Lines   Covered   Coverage
TierService.java                          142        98        69%
TierValidationHelper.java                  38        38       100%
SlabEvaluationStrategy.java                91        52        57%
────────────────────────────────────────────────────────────────────────
Aggregate new-code coverage: 74.3%   Target: 90%   Gap: 15.7%
────────────────────────────────────────────────────────────────────────

⚠  Coverage is below 90%. What do you want to do?
   [1] Improve — generate UT stubs for uncovered methods and loop
   [2] Continue — log warning and proceed to Backend Readiness
```

Wait for developer input. If they type `1` or `improve`: proceed to Step 6. If they type `2` or `continue`: go to Step 7 with WARNING verdict.

---

## Step 6 — Remediation Loop

### 6a — Find uncovered methods

For each under-covered file, parse `jacoco.xml` for methods with any missed lines. Use:

```python
import xml.etree.ElementTree as ET, sys

filename = sys.argv[1]
tree = ET.parse('target/site/jacoco/jacoco.xml')
root = tree.getroot()

for pkg in root.findall('package'):
    for sf in pkg.findall('sourcefile'):
        if sf.get('name') == filename:
            for cls in root.findall(f"package[@name='{pkg.get('name')}']/class"):
                for method in cls.findall('method'):
                    lines = [c for c in method.findall('counter') if c.get('type') == 'LINE']
                    if lines and int(lines[0].get('missed', 0)) > 0:
                        print(f"{cls.get('name')}|{method.get('name')}|{method.get('line')}")
```

### 6b — Determine stub file location

Take the first under-covered file. Find its Java package:

```bash
grep -m1 "^package " src/main/java/com/capillary/path/to/TierService.java
# → package com.capillary.intouchapiv3.services;
```

Convert to path: `com/capillary/intouchapiv3/services` → write stubs to:
`src/test/java/com/capillary/intouchapiv3/services/SonarGateStubs.java`

### 6c — Generate stubs file

Write `SonarGateStubs.java` with one `@Test` stub per uncovered method:

```java
package com.capillary.intouchapiv3.services;

import org.junit.Test;
import static org.junit.Assert.fail;

/**
 * Generated by /sonar-gate — fill in each test, then re-run /sonar-gate.
 * This file is deleted automatically once coverage reaches 90%.
 */
public class SonarGateStubs {

    @Test
    public void test_TierService_applySlabValidity() {
        // TODO: test TierService#applySlabValidity — currently 0% line coverage
        // Arrange

        // Act

        // Assert
        fail("Not yet implemented");
    }

    @Test
    public void test_SlabEvaluationStrategy_evaluate() {
        // TODO: test SlabEvaluationStrategy#evaluate — currently 0% line coverage
        // Arrange

        // Act

        // Assert
        fail("Not yet implemented");
    }
}
```

Print to the developer:

```
Stubs written to: src/test/java/com/capillary/intouchapiv3/services/SonarGateStubs.java

Next steps:
  1. Open SonarGateStubs.java
  2. Fill in each @Test method (replace the fail() with real assertions)
  3. Re-run /sonar-gate when ready

The file will be deleted automatically once you reach 90%.
```

### 6d — Wait for developer to fill in stubs, then re-run

After developer signals ready, go back to **Step 2** (re-run JaCoCo). Display the updated table. If coverage ≥ threshold: delete `SonarGateStubs.java` automatically, then go to Step 7 with PASS. If still below: repeat Steps 5–6.

To delete the stubs file:

```bash
rm src/test/java/com/capillary/intouchapiv3/services/SonarGateStubs.java
```

---

## Step 7 — Write `sonar-gate.md` Artifact

Always write this file regardless of verdict. Place it in the pipeline artifacts path (same directory as `session-memory.md`) or in the project root if running standalone.

```markdown
## Sonar Gate Report

**Branch:** <output of `git branch --show-current`>
**Run date:** <today's date>
**New files analysed:** <count>
**Aggregate new-code coverage:** <X>%
**Threshold:** <N>%
**Verdict:** PASS | WARNING — developer chose to continue

### Per-File Breakdown

| File | Covered Lines | Missed Lines | Total Lines | Coverage |
|---|---|---|---|---|
| TierService.java | 98 | 44 | 142 | 69% |
| TierValidationHelper.java | 38 | 0 | 38 | 100% |
| SlabEvaluationStrategy.java | 52 | 39 | 91 | 57% |

### Uncovered Methods at Exit
*(only present when Verdict is WARNING)*

- TierService#applySlabValidity (line 87)
- SlabEvaluationStrategy#evaluate (line 34)
```

For PASS with no uncovered methods, omit the "Uncovered Methods" section entirely.

---

## Return to Orchestrator

When running as part of the pipeline (spawned by Phase 10a), return:

```
PHASE: Sonar Gate (10a)
STATUS: PASS | WARNING
ARTIFACT: sonar-gate.md

COVERAGE SUMMARY:
- New files analysed: N
- Aggregate new-code coverage: X%
- Threshold: 90%
- Verdict: PASS | WARNING (developer chose to continue)

UNCOVERED METHODS (if WARNING):
- [list or "None"]

NEXT PHASE: Backend Readiness (10b)
```

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| No new Java files on branch | PASS immediately, write sonar-gate.md, exit |
| Maven build fails | Surface error, exit — no coverage report |
| JaCoCo plugin not in `.m2` | Maven downloads on first run (needs internet) |
| New file has 0 tests (not in jacoco.xml) | Treat as 0% coverage, count lines with `wc -l` |
| Branch already merged to main | `git diff main` empty → PASS |
| Coverage exactly at threshold | PASS |
| `session-memory.md` not found | Run standalone without it — optional |
| `--file` path not found | Print error, exit |
````

- [ ] **Step 3: Verify the file was created**

```bash
ls -la .claude/skills/sonar-gate/SKILL.md
```

Expected: file exists, size > 0.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/sonar-gate/SKILL.md
git commit -m "feat: add /sonar-gate skill — local JaCoCo coverage gate (Phase 10a)"
```

---

## Task 2: Add Traceability Check to SDET Skill

**Files:**
- Modify: `.claude/skills/sdet/SKILL.md`

The traceability check goes after the Stage 2 output requirements block (after the "Skeleton classes created" bullet, before the "Return to Orchestrator" section). Find the exact anchor text `## Return to Orchestrator` and insert the new section immediately before it.

- [ ] **Step 1: Read the current SDET skill to locate the insertion point**

Read `.claude/skills/sdet/SKILL.md`. Confirm the text `## Return to Orchestrator` exists. The new section goes directly above it.

- [ ] **Step 2: Insert the traceability check section**

Using the Edit tool, replace:

```
## Return to Orchestrator
When running as a subagent (spawned by `/workflow`), after writing `05-sdet.md` and updating `session-memory.md`, return:
```

with:

```
## Traceability Check (End of Stage 2 — Mandatory)

After writing all test code and before returning to the orchestrator, run one final structural check: **does every new class in the skeleton output have at least one UT planned?**

### How to run it

1. Collect all skeleton production classes created in Stage 2 (the classes written to `src/main` with `UnsupportedOperationException` stubs).
2. For each class, search `05-sdet.md` for at least one test entry that references it — by class name or BT-xx trace.
3. Any class with zero planned UTs → add it to a **⚠ Zero-Coverage Risk** section at the bottom of `05-sdet.md`.

### Output format

Append to `05-sdet.md`:

```markdown
## ⚠ Zero-Coverage Risk

The following new classes have no UT planned. They will appear as 0% in /sonar-gate (Phase 10a).
Consider adding at least one UT per class before the Developer phase.

| Class | Skeleton path | Suggested test scope |
|---|---|---|
| TierNotificationService | src/main/java/.../TierNotificationService.java | Happy path + null input |
```

If all classes have at least one UT planned, write instead:

```markdown
## ✓ Traceability Check

All N skeleton classes have at least one UT planned. Zero-coverage risk: none.
```

This check is structural — it does not run any code or measure actual line coverage. Its purpose is to catch obvious gaps (entire classes with no test at all) before the Developer phase starts.

---

## Return to Orchestrator
When running as a subagent (spawned by `/workflow`), after writing `05-sdet.md` and updating `session-memory.md`, return:
```

- [ ] **Step 3: Verify the edit is clean**

Read `.claude/skills/sdet/SKILL.md` around the insertion point (search for "Traceability Check"). Confirm the section appears before "Return to Orchestrator" and the heading levels are consistent with the rest of the file.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/sdet/SKILL.md
git commit -m "feat: add traceability check to SDET skill — zero-coverage risk detection at Phase 9"
```

---

## Task 3: Wire Phase 10a into the Pipeline Orchestrator

**Files:**
- Modify: `.claude/agents/feature-pipeline.md`

Phase 10a goes between the end of Phase 10 (Developer) and the start of Phase 10b (Backend Readiness). The exact insertion point is the `---` separator after Phase 10's final line and before `## Phase 10b: Backend Readiness (Subagent)`.

- [ ] **Step 1: Read the insertion point in feature-pipeline.md**

Read `.claude/agents/feature-pipeline.md` around line 1059–1063. The block to find:

```
---

## Phase 10b: Backend Readiness (Subagent)
```

- [ ] **Step 2: Insert Phase 10a block**

Using the Edit tool, replace:

```
---

## Phase 10b: Backend Readiness (Subagent)
```

with:

```
---

## Phase 10a: Sonar Gate — Local Coverage Check (Subagent)

**Skill**: `/sonar-gate` (`.claude/skills/sonar-gate/SKILL.md`)
**Mode**: Subagent — runs JaCoCo locally, measures new-code coverage, warns if below 90%

1. Spawn subagent:
   ```
   You are running the /sonar-gate skill.
   Read: .claude/skills/sonar-gate/SKILL.md
   Read: session-memory.md (if present in artifacts path)

   Run the full 7-step sonar-gate protocol:
   Step 1: git diff main to identify new production Java files
   Step 2: mvn jacoco prepare-agent + test + report (no pom.xml change)
   Step 3: parse target/site/jacoco/jacoco.xml, filter to new files only
   Step 4: calculate aggregate new-code line coverage %
   Step 5: if < 90% → display per-file table, ask developer: improve or continue?
   Step 6: if improve → generate SonarGateStubs.java, loop until pass or developer continues
   Step 7: always write sonar-gate.md artifact

   Produce: sonar-gate.md with per-file table, verdict (PASS or WARNING), uncovered methods list
   ```
2. Display verdict to user
3. If WARNING and developer chose to continue: note in process-log, proceed to Phase 10b
4. If WARNING and developer chose to improve: loop stays inside Phase 10a until PASS or explicit continue
5. Update process-log, session-memory

---

## Phase 10b: Backend Readiness (Subagent)
```

- [ ] **Step 3: Update the pipeline skills table in CLAUDE.md**

Read `.claude/CLAUDE.md`. Find the pipeline skills table. Add a row for `/sonar-gate` between `/developer` and `/backend-readiness`:

Find:
```
| `/developer` | Production code implementation — GREEN phase (makes tests pass, refactors) | 10 |
| `/backend-readiness` | Production readiness gate (queries, Thrift, cache, errors) | 10b |
```

Replace with:
```
| `/developer` | Production code implementation — GREEN phase (makes tests pass, refactors) | 10 |
| `/sonar-gate` | Local coverage gate — runs JaCoCo via Maven CLI, warns if new-code coverage < 90%, generates UT stubs | 10a |
| `/backend-readiness` | Production readiness gate (queries, Thrift, cache, errors) | 10b |
```

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/feature-pipeline.md .claude/CLAUDE.md
git commit -m "feat: wire /sonar-gate as Phase 10a in pipeline orchestrator"
```

---

## Task 4: Smoke Test the Skill End-to-End

This task verifies the skill is wired correctly and the Maven command works on the local machine.

- [ ] **Step 1: Check Maven is available**

```bash
mvn --version
```

Expected output contains `Apache Maven 3.x.x`.

- [ ] **Step 2: Check git diff works**

From any feature branch (or create a temp file to simulate a new file):

```bash
git diff main --name-only -- 'src/main/java/**.java'
```

Expected: list of Java files changed vs main (may be empty if on main — that's fine for smoke test).

- [ ] **Step 3: Dry-run Maven JaCoCo invocation**

From any project root that has a `pom.xml`:

```bash
mvn org.jacoco:jacoco-maven-plugin:0.8.11:help -Ddetail=false 2>&1 | head -20
```

Expected: Maven resolves the plugin and prints help text. This confirms the plugin can be resolved without pom.xml changes.

- [ ] **Step 4: Verify skill file is valid markdown**

```bash
head -10 .claude/skills/sonar-gate/SKILL.md
```

Expected: frontmatter block starting with `---` and containing `name: sonar-gate`.

- [ ] **Step 5: Verify pipeline wiring**

```bash
grep -n "sonar-gate\|Phase 10a" .claude/agents/feature-pipeline.md | head -10
```

Expected: at least one match showing `## Phase 10a: Sonar Gate`.

- [ ] **Step 6: Commit smoke test confirmation**

No code change — just record that smoke test passed in a commit message if you changed anything, otherwise skip.

---

## Self-Review Checklist

**Spec coverage:**
- [x] New `/sonar-gate` skill with all 7 steps → Task 1
- [x] SDET traceability check → Task 2
- [x] Phase 10a in pipeline orchestrator → Task 3 Step 2
- [x] CLAUDE.md skills table updated → Task 3 Step 3
- [x] Standalone invocation (`--threshold`, `--file`) → covered in SKILL.md frontmatter/invocation section
- [x] Soft gate (warn + ask, not hard block) → Step 5 in SKILL.md
- [x] Remediation loop (generate stubs → loop → delete stubs on pass) → Step 6 in SKILL.md
- [x] `sonar-gate.md` always written → Step 7 in SKILL.md
- [x] All edge cases (no new files, Maven fail, 0% file, branch merged) → Edge Cases table in SKILL.md

**Placeholder scan:** No TBD, TODO, or "fill in details" anywhere in this plan. All steps have exact commands, exact file content, or exact edit instructions.

**Type consistency:** `SonarGateStubs.java`, `sonar-gate.md`, `SKILL.md` — naming is consistent across all three tasks.
