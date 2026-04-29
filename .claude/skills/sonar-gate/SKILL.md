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
| `--threshold N` | 90 | Override coverage threshold (e.g. `/sonar-gate --threshold 80`) |
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

Write this Python snippet to `/tmp/parse_jacoco.py` and run it:

```python
import xml.etree.ElementTree as ET, sys

new_files = sys.argv[1:]  # simple filenames e.g. TierService.java
tree = ET.parse('target/site/jacoco/jacoco.xml')
root = tree.getroot()

results = []
matched = set()

for pkg in root.findall('package'):
    for sf in pkg.findall('sourcefile'):
        if sf.get('name') in new_files:
            matched.add(sf.get('name'))
            lines = [c for c in sf.findall('counter') if c.get('type') == 'LINE']
            if lines:
                missed = int(lines[0].get('missed', 0))
                covered = int(lines[0].get('covered', 0))
                total = missed + covered
                pct = round(covered / total * 100, 1) if total > 0 else 0.0
                results.append((sf.get('name'), covered, missed, total, pct))
            else:
                results.append((sf.get('name'), 0, 0, 0, 0.0))

# Files in new_files but not in jacoco.xml = 0% coverage
for f in new_files:
    if f not in matched:
        results.append((f, 0, -1, -1, 0.0))  # -1 signals "count lines separately"

for name, covered, missed, total, pct in results:
    print(f"{name}|{covered}|{missed}|{total}|{pct}")
```

Run:

```bash
python3 /tmp/parse_jacoco.py TierService.java TierValidationHelper.java
```

Pass only the **simple filename** (basename, no path) for each new file — that matches `<sourcefile name="...">` in `jacoco.xml`.

**If a file has `-1` for missed/total** (not in jacoco.xml at all — zero tests): count its lines with:

```bash
wc -l < path/to/TheFile.java
```

Treat it as `covered=0, missed=<line count>, pct=0%`.

---

## Step 4 — Calculate Aggregate Coverage

```
aggregate_pct = sum(covered_lines across all new files)
              / sum(total_lines across all new files) * 100
```

Round to one decimal place.

**Apply threshold** (default 90, or value from `--threshold`):
- `aggregate_pct >= threshold` → **PASS** → go to Step 7, write artifact, exit
- `aggregate_pct < threshold` → **WARNING** → go to Step 5

---

## Step 5 — Display Coverage Table and Prompt Developer

Print the table — pad columns for readability:

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

Wait for developer input:
- `1` or `improve` (case-insensitive) → Step 6
- `2` or `continue` → Step 7 with WARNING verdict

---

## Step 6 — Remediation Loop

### 6a — Find uncovered methods

Write this to `/tmp/find_uncovered.py`:

```python
import xml.etree.ElementTree as ET, sys, os

filename = sys.argv[1]   # simple filename e.g. TierService.java
tree = ET.parse('target/site/jacoco/jacoco.xml')
root = tree.getroot()

for pkg in root.findall('package'):
    pkg_name = pkg.get('name')
    for sf in pkg.findall('sourcefile'):
        if sf.get('name') == filename:
            for cls in root.findall(f"package[@name='{pkg_name}']/class"):
                cls_simple = os.path.basename(cls.get('name', ''))
                for method in cls.findall('method'):
                    lines = [c for c in method.findall('counter') if c.get('type') == 'LINE']
                    if lines and int(lines[0].get('missed', 0)) > 0:
                        print(f"{cls_simple}|{method.get('name')}|{method.get('line', '?')}")
```

Run for each under-covered file:

```bash
python3 /tmp/find_uncovered.py TierService.java
```

### 6b — Determine stub file location

Get the package of the first under-covered file:

```bash
grep -m1 "^package " src/main/java/com/capillary/path/to/TierService.java
# → package com.capillary.intouchapiv3.services;
```

Convert package to path: `com.capillary.intouchapiv3.services` → `com/capillary/intouchapiv3/services`

Stubs file: `src/test/java/com/capillary/intouchapiv3/services/SonarGateStubs.java`

### 6c — Write `SonarGateStubs.java`

Generate one `@Test` stub per uncovered method from the results of 6a. Use JUnit 4 (`org.junit.Test`) to match the project's test framework:

```java
package com.capillary.intouchapiv3.services;

import org.junit.Test;
import static org.junit.Assert.fail;

/**
 * Generated by /sonar-gate on <date>.
 * Fill in each test method, then re-run /sonar-gate.
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

After writing, print:

```
Stubs written → src/test/java/com/capillary/intouchapiv3/services/SonarGateStubs.java

Next steps:
  1. Open SonarGateStubs.java
  2. Fill in each @Test method (replace fail() with real assertions)
  3. Tell me when ready — I'll re-run coverage automatically

The file will be deleted once you reach 90%.
```

### 6d — Re-run on developer signal

When developer signals ready, return to **Step 2** (re-run JaCoCo). Show updated table.

- If `aggregate_pct >= threshold`: delete stubs automatically:
  ```bash
  rm src/test/java/com/capillary/intouchapiv3/services/SonarGateStubs.java
  ```
  Then go to Step 7 with PASS.
- If still below: repeat Steps 5–6.

---

## Step 7 — Write `sonar-gate.md` Artifact

**Always write this regardless of verdict.** Place it in the pipeline artifacts directory (same folder as `session-memory.md`) or project root if standalone.

```markdown
## Sonar Gate Report

**Branch:** <git branch --show-current>
**Run date:** <YYYY-MM-DD>
**New files analysed:** <N>
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
*(omit this section entirely on PASS)*

- TierService#applySlabValidity (line 87)
- SlabEvaluationStrategy#evaluate (line 34)
```

---

## Return to Orchestrator

When running as a pipeline subagent (spawned by Phase 10a), return:

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
| Maven build fails | Surface last 30 lines of error, exit — no coverage report |
| JaCoCo plugin not in `.m2` | Maven downloads on first run — needs internet once |
| New file has 0 tests (absent from jacoco.xml) | Treat as 0% coverage, count lines with `wc -l` |
| Branch already merged to main | `git diff main` empty → PASS |
| Coverage exactly at threshold | PASS |
| `session-memory.md` not found | Run standalone without it — optional input |
| `--file` path not found | Print error and exit |
| Multiple under-covered files, different packages | Write all stubs to the package of the *most* under-covered file |
