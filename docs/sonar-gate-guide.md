# Sonar Gate — User Guide

**Version:** 1.0
**Date:** 2026-04-29
**Author:** Ritwik Ranjan Pathak

---

## What Is Sonar Gate?

Sonar Gate is a Claude Code skill that checks your new code's test coverage **locally** — before you push to CI. It runs JaCoCo (the same coverage tool SonarQube uses internally) directly on your machine via Maven, then tells you exactly which files and methods are under-covered, and generates test stubs to help you fix it.

The goal is simple: **never have a CI build fail on coverage again.** You catch the gap on your laptop in 2–3 minutes instead of discovering it after a 10-minute CodeBuild run.

---

## Key Features

| Feature | Description |
|---|---|
| **No pom.xml changes** | Runs JaCoCo via Maven CLI plugin invocation — nothing in your project is modified |
| **New code only** | Only measures coverage on files changed vs the base branch — matches SonarQube PR analysis exactly |
| **Line + Condition coverage** | Reports both line coverage and condition (branch) coverage, same columns as SonarQube's Measures view |
| **Auto-detects base branch** | Asks the remote which branch is the default (main, master, or custom) — then confirms with you before running |
| **Multi-module Maven support** | Works on single-module and multi-module projects; finds the correct jacoco.xml automatically |
| **Framework-aware stub generation** | Detects JUnit 4, JUnit 5, or TestNG from your existing tests before generating stubs |
| **Soft gate** | Warns you if coverage is below 90% but lets you decide — improve now or continue to the next phase |
| **Remediation loop** | Generates compilable test stubs for every uncovered method; loops until you hit 90% or choose to continue |
| **Auto-cleanup** | Deletes generated stub file automatically once coverage passes |
| **Standalone + pipeline** | Runs as Phase 10a in the feature pipeline, and also works standalone at any point on any branch |
| **Audit trail** | Always writes sonar-gate.md with per-file breakdown and verdict — available for code reviewers |

---

## How to Run It

### Prerequisites

- Claude Code CLI installed (`claude`)
- Maven installed (`mvn --version` should work)
- You are on a **feature branch** (not main/master) in the repo you want to check
- The project compiles and tests run locally (`mvn test` should not error out before coverage)

---

### Step 1 — Navigate to the repo

Open your terminal and go to the root of the repo you want to check. This must be the directory that contains `pom.xml`.

```
cd /path/to/emf-parent
```

or

```
cd /path/to/intouch-api-v3
```

---

### Step 2 — Make sure you are on the right branch

Check which branch you are on:

```
git branch --show-current
```

If you are not on your feature branch, switch to it:

```
git checkout aidlc/your-feature-branch
```

---

### Step 3 — Open Claude Code

From the same directory:

```
claude
```

---

### Step 4 — Run the skill

Type in the Claude Code chat:

```
/sonar-gate
```

Press Enter.

---

### Step 5 — Confirm the base branch

The skill will detect your default branch and ask you to confirm:

```
Detected base branch: master
Is this correct? Press Enter to confirm, or type a different branch name:
```

- Press **Enter** to accept the detected branch
- Or type a branch name (e.g. `main`, `develop`) if it detected the wrong one

---

### Step 6 — Wait for JaCoCo to run

Maven will download JaCoCo on first use (needs internet once), then run your full test suite. This takes approximately 2–3 minutes depending on the size of your test suite. You will see Maven output scrolling.

---

### Step 7 — Read the report

When done, the skill prints a table:

```
Coverage Report — New Code (branch vs master)
──────────────────────────────────────────────────────────────────────────────────
File                              Line Cov   Uncov Lines   Cond Cov   Uncov Conds
PointsEngineRuleEditorImpl.java      0.0%          12        0.0%            8
PointsEngineRuleConfigThrift.java   93.3%           2       100%             0
PartnerProgramIdempotency.java      100%            0       100%             0
──────────────────────────────────────────────────────────────────────────────────
Aggregate   Line coverage: 66.2%  (target 90%, gap 23.8%)
            Condition coverage: 60.0%  (target 90%, gap 30.0%)
──────────────────────────────────────────────────────────────────────────────────
```

---

### Step 8 — Choose what to do

If coverage is below 90%, the skill asks:

```
⚠  Coverage is below 90%. What do you want to do?
   [1] Improve — generate UT stubs for uncovered methods and loop
   [2] Continue — log warning and proceed
```

**Choose [1] Improve:** The skill generates a file called `SonarGateStubs.java` in your test directory with one stub method for every uncovered method. Open that file, fill in the test logic, then tell the skill you are ready. It re-runs JaCoCo automatically and shows the updated report. Repeat until you reach 90%.

**Choose [2] Continue:** The skill logs a warning in `sonar-gate.md` and exits. You can run `/sonar-gate` again at any time.

---

### Step 9 — When coverage passes

Once both line and condition coverage hit 90%, the skill:

1. Deletes `SonarGateStubs.java` automatically
2. Prints a PASS confirmation
3. Writes `sonar-gate.md` with the final report

You are now safe to push — CI will not fail on coverage.

---

## Command Options

| Command | What it does |
|---|---|
| `/sonar-gate` | Standard run — auto-detects base branch, checks all new files |
| `/sonar-gate --threshold 80` | Lower the pass threshold to 80% instead of 90% |
| `/sonar-gate --file src/main/java/.../TierService.java` | Check a single file only |
| `/sonar-gate --base-branch master` | Skip branch detection and confirmation, use master directly |
| `/sonar-gate --base-branch develop` | Use develop as the base (useful for non-standard repo setups) |

---

## Understanding the Report

| Column | Meaning |
|---|---|
| **Line Cov** | Percentage of lines in the file that are executed by at least one test |
| **Uncov Lines** | Number of lines with zero test execution |
| **Cond Cov** | Percentage of branch conditions (if/else, ternary, switch) covered |
| **Uncov Conds** | Number of branch conditions never evaluated by any test |
| **Aggregate** | Combined metric across all new/changed files — this is what the gate checks against the 90% threshold |

**Both Line Coverage and Condition Coverage must reach 90% to pass.** This matches SonarQube's quality gate configuration.

---

## Where to Find the Output Files

| File | Location | Purpose |
|---|---|---|
| `sonar-gate.md` | Pipeline artifacts directory, or project root if standalone | Audit trail — per-file breakdown, verdict, uncovered methods |
| `SonarGateStubs.java` | `src/test/java/<same package as uncovered class>/` | Generated test stubs — deleted automatically on PASS |

---

## Frequently Asked Questions

**Q: Does this modify my pom.xml?**
No. JaCoCo is invoked via Maven's CLI plugin syntax. Your pom.xml is never touched.

**Q: Will it work on emf-parent (multi-module)?**
Yes. The skill detects multi-module projects at startup and finds the correct jacoco.xml for each sub-module automatically.

**Q: What if my tests fail during the JaCoCo run?**
The skill surfaces the last 30 lines of Maven output and stops. Fix the failing tests first, then re-run `/sonar-gate`.

**Q: The stub file uses JUnit 4 but my project uses JUnit 5 — will it work?**
The skill detects your test framework from existing test files before generating stubs. It will use whichever framework your project already uses.

**Q: I ran it and got PASS immediately with no report. Why?**
This means no production Java files changed on your branch vs the base branch. Either you are on the wrong branch, or the base branch was detected incorrectly. Run `git diff master --name-only -- '*.java'` to verify.

**Q: Can I run this without being in the pipeline?**
Yes. Just be on your feature branch, open Claude Code in the repo root, and type `/sonar-gate`. It works completely standalone.

**Q: How is "new code" defined?**
New code = files that differ between your current branch and the base branch (`git diff <base-branch>`). This is the same definition SonarQube uses for PR analysis, so the number you see locally will closely match what CI reports.

---

## Where It Fits in the Pipeline

```
Phase 9  — SDET        Writes failing tests (RED phase)
Phase 10 — Developer   Writes production code (GREEN phase)
Phase 10a — Sonar Gate Checks coverage on new code ← THIS SKILL
Phase 10b — Backend Readiness
Phase 10c — Analyst
Phase 11  — Reviewer
```

---

## Quick Reference Card

```
1. cd /path/to/repo
2. git checkout your-feature-branch
3. claude
4. /sonar-gate
5. Confirm base branch (Enter to accept)
6. Wait ~2-3 min for Maven
7. Read the report
8. [1] Improve → fill in SonarGateStubs.java → re-run
   [2] Continue → warning logged, proceed
9. Push once you see PASS
```
