---
name: sonar-gate
description: Local coverage gate — Phase 10a. Runs JaCoCo via Maven CLI (no pom.xml change), measures new-code line AND condition coverage against main, warns if below 90%, generates UT stubs for uncovered methods. Detects JUnit 4/5, handles multi-module Maven. Standalone or pipeline. Use when user says /sonar-gate, [sonar-gate], or SonarGate:.
phase: "10a"
triggers: [sonar-gate, /sonar-gate, SonarGate]
inputs: [git diff vs main, jacoco.xml (generated), session-memory.md (optional)]
outputs: [sonar-gate.md]
---

## Reasoning Principles

Read `.claude/principles.md` at phase start if available. Apply throughout:
- **Every claim carries a confidence level (C1–C7)** — never state coverage numbers without reading the actual `jacoco.xml` (C7 required for metric claims)
- **Reversibility determines action threshold** — writing stubs is reversible (C4 sufficient); deleting stubs requires C6 (confirmed PASS)
- **Pre-mortem before acting**: before reporting PASS, ask "could the jacoco.xml be stale or from the wrong module?"

# Sonar Gate — Local Coverage Check (Phase 10a)

You are a local coverage enforcement skill. Your job is to measure **new-code line and condition coverage** on the current branch, warn the developer if either falls below 90%, and help them close the gap before pushing — so CI never fails on coverage.

You run after Developer (Phase 10) and before Backend Readiness (Phase 10b). You can also be invoked standalone at any time on any feature branch.

---

## Invocation Arguments

| Argument | Default | Effect |
|---|---|---|
| `--threshold N` | 90 | Override coverage threshold for both line and condition (e.g. `/sonar-gate --threshold 80`) |
| `--file <path>` | all new files | Restrict analysis to a single changed file |
| `--base-branch <name>` | auto-detected | Override base branch (e.g. `--base-branch master` for repos that use master) |

---

## Step 0 — Detect Project Structure (Multi-Module Guard)

Before running anything, determine whether this is a single-module or multi-module Maven project:

```bash
ls pom.xml && grep -l "<modules>" pom.xml
```

**Single-module** (no `<modules>` in root pom): JaCoCo report will be at `target/site/jacoco/jacoco.xml`.

**Multi-module** (root pom has `<modules>`): Each sub-module produces its own report. Find them all:

```bash
find . -path "*/target/site/jacoco/jacoco.xml" -not -path "*/target/site/jacoco-aggregate/*"
```

Also check for an aggregate report:

```bash
find . -path "*/target/site/jacoco-aggregate/jacoco.xml"
```

**Which report to use:**
- If an aggregate `jacoco-aggregate/jacoco.xml` exists → use it (most complete)
- If not → use per-module reports; merge results across modules when computing totals
- Record the report path(s) — you will need them in Steps 2 and 3

---

## Step 1 — Identify New/Changed Production Files

### 1a — Detect the default branch

Different repos use different default branch names (`main`, `master`, or a custom name). Never assume — detect it:

```bash
# Ask the remote what its HEAD points to (most reliable)
git remote show origin 2>/dev/null | grep "HEAD branch" | awk '{print $NF}'
```

If the remote is unreachable (offline / no remote configured), fall back to local detection:

```bash
# Check which of main/master exists locally
git branch --list main master | tr -d ' *' | head -1
```

Store the result as `BASE_BRANCH` (e.g. `main` or `master`). If neither is found, print:
`Cannot detect default branch — pass it explicitly with --base-branch <name>` and exit.

**`--base-branch` override:** If the user passes `--base-branch develop` (or any name), use that instead of auto-detection. This handles repos with non-standard defaults.

### 1b — List changed production files

```bash
git diff <BASE_BRANCH> --name-only -- '*.java' | grep 'src/main/java'
```

This lists Java source files changed on the current branch vs the detected base. Test files (`src/test/`) are excluded.

**If the list is empty:** Print `✓ PASS — no new production Java files on this branch vs <BASE_BRANCH>.` Write a PASS `sonar-gate.md` (see Step 7 format). Exit.

**If `--file` argument was provided:** Replace the full list with just that one file. Verify it exists:
```bash
ls <path>
```
If not found, print error and exit.

---

## Step 2 — Run JaCoCo Locally via Maven CLI

Run from the project root (no pom.xml modification required):

**Single-module:**
```bash
mvn org.jacoco:jacoco-maven-plugin:0.8.11:prepare-agent \
    test \
    org.jacoco:jacoco-maven-plugin:0.8.11:report \
    -Dproject.reporting.outputEncoding=UTF-8
```

**Multi-module (run from root, reports per sub-module):**
```bash
mvn org.jacoco:jacoco-maven-plugin:0.8.11:prepare-agent \
    test \
    org.jacoco:jacoco-maven-plugin:0.8.11:report \
    -Dproject.reporting.outputEncoding=UTF-8 \
    --fail-at-end
```

`--fail-at-end` ensures all modules run even if one has test failures, giving you a complete picture.

Maven resolves JaCoCo from your local `.m2` cache or downloads it on first run (internet required on first use only — subsequent runs are instant).

**If Maven fails:**
- Surface the last 30 lines of Maven output to the developer
- Print: `✗ BUILD FAILED — cannot compute coverage on a broken build. Fix compilation/test errors first.`
- Do NOT attempt to parse any jacoco.xml
- Exit

**Verify report(s) exist** using the path(s) determined in Step 0:
```bash
ls target/site/jacoco/jacoco.xml          # single-module
# or
find . -path "*/target/site/jacoco/jacoco.xml" | head -5   # multi-module
```

If no report found after a successful Maven run: `jacoco.xml not generated — JaCoCo may not have instrumented any classes. Verify that tests are in src/test/java and that they compile.` Exit.

---

## Step 3 — Parse `jacoco.xml` and Filter to New Files

Write the following script to `/tmp/sg_parse.py`, run it, then delete it:

```python
import xml.etree.ElementTree as ET, sys, os

report_path = sys.argv[1]      # e.g. target/site/jacoco/jacoco.xml
new_files   = sys.argv[2:]     # simple basenames e.g. TierService.java

tree = ET.parse(report_path)
root = tree.getroot()

results = []
matched = set()

for pkg in root.findall('package'):
    for sf in pkg.findall('sourcefile'):
        name = sf.get('name')
        if name not in new_files:
            continue
        matched.add(name)

        def counter(typ):
            c = next((x for x in sf.findall('counter') if x.get('type') == typ), None)
            if c is None:
                return 0, 0
            return int(c.get('missed', 0)), int(c.get('covered', 0))

        lm, lc = counter('LINE')
        bm, bc = counter('BRANCH')
        lt = lm + lc
        bt = bm + bc
        lpct = round(lc / lt * 100, 1) if lt > 0 else 0.0
        bpct = round(bc / bt * 100, 1) if bt > 0 else 0.0
        results.append((name, lc, lm, lt, lpct, bc, bm, bt, bpct))

for f in new_files:
    if f not in matched:
        # Not in jacoco.xml — never instrumented (0% coverage)
        results.append((f, 0, -1, -1, 0.0, 0, -1, -1, 0.0))

for r in results:
    print('|'.join(str(x) for x in r))
```

Run:
```bash
python3 /tmp/sg_parse.py target/site/jacoco/jacoco.xml TierService.java TierValidationHelper.java
# cleanup
rm /tmp/sg_parse.py
```

**Output columns per line:**
`filename | line_covered | line_missed | line_total | line_pct | branch_covered | branch_missed | branch_total | branch_pct`

**If a file has `-1` for totals** (absent from jacoco.xml — zero instrumentation):
```bash
wc -l < path/to/TheFile.java
```
Treat as `line_covered=0, line_missed=<line count>, line_pct=0%, branch_pct=0%`.

**Multi-module:** Run the parser once per jacoco.xml, merge results by filename. If a file appears in multiple reports (shouldn't happen, but guard for it), use the report from the module whose source path matches.

---

## Step 4 — Calculate Aggregate Coverage

```
line_agg  = sum(line_covered)  / sum(line_total)  * 100
cond_agg  = sum(branch_covered) / sum(branch_total) * 100
```

Round both to one decimal place. If `branch_total == 0` across all files (no conditional logic), set `cond_agg = 100%` — no branches to miss.

**Apply threshold** (default 90):

```
line_pass = line_agg  >= threshold
cond_pass = cond_agg  >= threshold  (skip if branch_total == 0)

if line_pass AND cond_pass → PASS → Step 7
if either fails             → WARNING → Step 5
```

Both must pass — this matches how SonarQube's quality gate works.

---

## Step 5 — Display Coverage Table and Prompt Developer

Print the full table matching SonarQube's Measures view:

```
Coverage Report — New Code (branch vs main)
──────────────────────────────────────────────────────────────────────────────────
File                              Line Cov   Uncov Lines   Cond Cov   Uncov Conds
PointsEngineRuleEditorImpl.java      0.0%          12        0.0%            8
PointsEngineRuleConfigThrift.java   93.3%           2       100%             0
PartnerProgramIdempotency.java      100%            0       100%             0
──────────────────────────────────────────────────────────────────────────────────
Aggregate   Line coverage: 66.2%  (target 90%, gap 23.8%)
            Condition coverage: 60.0%  (target 90%, gap 30.0%)
──────────────────────────────────────────────────────────────────────────────────

⚠  Coverage is below 90%. What do you want to do?
   [1] Improve — generate UT stubs for uncovered methods and loop
   [2] Continue — log warning and proceed to Backend Readiness
```

Highlight which metric(s) are failing so the developer knows what to target.

Wait for input:
- `1` / `improve` → Step 6
- `2` / `continue` → Step 7 with WARNING

---

## Step 6 — Remediation Loop

### 6a — Detect test framework

Before generating stubs, find the test framework the project uses — do not assume JUnit 4:

```bash
# Check for JUnit 5
grep -r "org.junit.jupiter" src/test --include="*.java" -l | head -1

# Check for JUnit 4
grep -r "org.junit.Test" src/test --include="*.java" -l | head -1

# Check for TestNG
grep -r "org.testng" src/test --include="*.java" -l | head -1
```

Use whichever is found. If JUnit 5: use `@Test` from `org.junit.jupiter.api.Test` and `Assertions.fail()`. If JUnit 4: use `@Test` from `org.junit.Test` and `Assert.fail()`. If none found: default to JUnit 4.

### 6b — Find uncovered methods

Write to `/tmp/sg_methods.py`, run, then delete:

```python
import xml.etree.ElementTree as ET, sys, os

report_path = sys.argv[1]
filename    = sys.argv[2]   # simple basename

tree = ET.parse(report_path)
root = tree.getroot()

for pkg in root.findall('package'):
    pkg_name = pkg.get('name')
    for sf in pkg.findall('sourcefile'):
        if sf.get('name') != filename:
            continue
        for cls in root.findall(f"package[@name='{pkg_name}']/class"):
            cls_simple = os.path.basename(cls.get('name', ''))
            for method in cls.findall('method'):
                lc = next((c for c in method.findall('counter') if c.get('type') == 'LINE'), None)
                if lc is not None and int(lc.get('missed', 0)) > 0:
                    print(f"{cls_simple}|{method.get('name')}|{method.get('line', '?')}")
```

```bash
python3 /tmp/sg_methods.py target/site/jacoco/jacoco.xml PointsEngineRuleEditorImpl.java
rm /tmp/sg_methods.py
```

### 6c — Determine stub file location

```bash
# Find the actual source file (handles multi-module)
find . -name "PointsEngineRuleEditorImpl.java" -path "*/src/main/*" | head -1

# Read its package
grep -m1 "^package " <found-path>
# → package com.capillary.shopbook.pointsengine.endpoint.impl.editor;
```

Convert package to test path: `com.capillary.shopbook.pointsengine.endpoint.impl.editor`
→ find the corresponding `src/test/java` root in the same module, then:
`src/test/java/com/capillary/shopbook/pointsengine/endpoint/impl/editor/SonarGateStubs.java`

### 6d — Write `SonarGateStubs.java`

**JUnit 5 variant:**
```java
package com.capillary.shopbook.pointsengine.endpoint.impl.editor;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.fail;

/**
 * Generated by /sonar-gate on <date>.
 * Fill in each @Test method, then re-run /sonar-gate.
 * Deleted automatically once coverage reaches 90%.
 */
class SonarGateStubs {

    @Test
    void test_PointsEngineRuleEditorImpl_getRulesByOrg() {
        // TODO: test PointsEngineRuleEditorImpl#getRulesByOrg — 0% line coverage
        // Arrange

        // Act

        // Assert
        fail("Not yet implemented");
    }
}
```

**JUnit 4 variant:**
```java
package com.capillary.shopbook.pointsengine.endpoint.impl.editor;

import org.junit.Test;
import static org.junit.Assert.fail;

/**
 * Generated by /sonar-gate on <date>.
 * Fill in each @Test method, then re-run /sonar-gate.
 * Deleted automatically once coverage reaches 90%.
 */
public class SonarGateStubs {

    @Test
    public void test_PointsEngineRuleEditorImpl_getRulesByOrg() {
        // TODO: test PointsEngineRuleEditorImpl#getRulesByOrg — 0% line coverage
        // Arrange

        // Act

        // Assert
        fail("Not yet implemented");
    }
}
```

After writing:
```
Stubs written → src/test/java/.../SonarGateStubs.java
Framework detected: JUnit 4 | JUnit 5

Next steps:
  1. Open SonarGateStubs.java
  2. Fill in each @Test method (replace fail() with real assertions)
  3. Tell me when ready — I'll re-run coverage automatically

The file is deleted once you hit 90% on both line and condition coverage.
```

### 6e — Re-run on developer signal

Return to **Step 2**. Show the updated table (both line and condition).

- If both `line_agg >= threshold` AND `cond_agg >= threshold`:
  ```bash
  rm src/test/java/.../SonarGateStubs.java
  ```
  Go to Step 7 with PASS.
- If still failing: repeat Steps 5–6.

---

## Step 7 — Write `sonar-gate.md` Artifact

**Always write this, regardless of verdict.** Place in pipeline artifacts directory (same folder as `session-memory.md`), or project root if standalone.

```markdown
## Sonar Gate Report

**Branch:** <git branch --show-current>
**Run date:** <YYYY-MM-DD>
**Module(s) analysed:** <single | list of sub-modules>
**New files analysed:** <N>
**Threshold:** <N>%

### Aggregate New-Code Coverage

| Metric | Coverage | Target | Gap | Status |
|---|---|---|---|---|
| Line Coverage | 66.2% | 90% | 23.8% | ⚠ WARNING |
| Condition Coverage | 60.0% | 90% | 30.0% | ⚠ WARNING |

**Verdict:** PASS | WARNING — developer chose to continue

### Per-File Breakdown

| File | Line Cov | Uncov Lines | Cond Cov | Uncov Conds |
|---|---|---|---|---|
| PointsEngineRuleEditorImpl.java | 0.0% | 12 | 0.0% | 8 |
| PointsEngineRuleConfigThrift.java | 93.3% | 2 | 100% | 0 |
| PartnerProgramIdempotency.java | 100% | 0 | 100% | 0 |

### Uncovered Methods at Exit
*(omit this section entirely on PASS)*

- PointsEngineRuleEditorImpl#getRulesByOrg (line 34)
- PointsEngineRuleEditorImpl#deleteRule (line 67)
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
- Line coverage (new code): X%     [PASS | WARNING]
- Condition coverage (new code): X% [PASS | WARNING]
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
| Maven build fails | Surface last 30 lines, exit — no coverage report |
| JaCoCo plugin not in `.m2` | Maven downloads on first run — needs internet once |
| File absent from jacoco.xml (0 tests) | 0% line and condition, count lines with `wc -l` |
| No conditional logic in new files | `branch_total = 0` → condition coverage = 100%, skip check |
| Branch already merged to base branch | `git diff <BASE_BRANCH>` empty → PASS |
| Coverage exactly at threshold | PASS |
| Multi-module project | Find jacoco.xml per module or aggregate report (Step 0) |
| Aggregate report missing in multi-module | Merge per-module reports manually |
| JUnit version not detected | Default to JUnit 4 for stub generation |
| `session-memory.md` not found | Run standalone without it — optional input |
| `--file` path not found | Print error and exit |
| `/tmp` scripts left behind | Always `rm /tmp/sg_parse.py` and `/tmp/sg_methods.py` after use |
