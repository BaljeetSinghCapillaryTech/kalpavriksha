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

**Print this banner exactly at startup, before any other output:**

```
──────────────────────────────────────────
  Sonar Gate  (Phase 10a)
  Copyright (c) 2026 Capillary Technologies
  Developed by: Ritwik Ranjan Pathak and Claude Bros
──────────────────────────────────────────
```

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

Store the detected result as `BASE_BRANCH`. If neither is found, print:
`Cannot detect default branch — pass it explicitly with --base-branch <name>` and exit.

**`--base-branch` override:** If the user passes `--base-branch develop` (or any name), skip detection and use that directly — no confirmation prompt needed since the user already specified it.

**Always confirm with the user before proceeding** (unless `--base-branch` was explicitly passed):

```
Detected base branch: master
Is this correct? Press Enter to confirm, or type a different branch name:
```

- If the user presses Enter (or says yes/y): proceed with detected branch
- If the user types a branch name (e.g. `develop`): use that instead
- This prevents silently diffing against the wrong branch on repos with unusual setups

### 1b — Show branch commits and choose scope

First, show the developer exactly what is on this branch:

```bash
git log <BASE_BRANCH>..HEAD --oneline
```

Print the result, then ask:

```
Commits on this branch vs <BASE_BRANCH>:
  abc1234  Add EnumTypeResolverImpl change
  def5678  Add UTs for EnumTypeResolverImpl

What scope do you want to check?
  [1] Committed only (default) — matches what CI sees
  [2] All changes including uncommitted — checks your full working state
  [3] From a specific commit — paste a SHA (e.g. abc1234)
```

- **1 / Enter:** use `<BASE_BRANCH>..HEAD` — committed changes only (matches CI, recommended)
- **2:** use `<BASE_BRANCH>` — includes staged and unstaged working-tree edits (useful when you're mid-development and want to check before committing)
- **3 / A commit SHA:** use `<SHA>..HEAD` — only commits from that point forward (useful when the branch has unrelated earlier commits)

Store the resolved diff expression as `DIFF_RANGE`.

Then list the changed production files AND capture their changed line numbers — both are needed to match SonarQube's "new code" definition exactly:

```bash
# List changed files (basenames used later for jacoco.xml lookup)
git diff <DIFF_RANGE> --name-only -- '*.java' | grep 'src/main/java'
```

For each changed file, extract the new line numbers from the diff hunks:

```bash
git diff <DIFF_RANGE> -- <file_path>
```

Parse **only the added/modified lines** (`+` lines) from the diff — not the hunk range, which also includes context lines. Context lines (shown for readability but unchanged) must be excluded or you over-count. Write this to `/tmp/sg_lines.py`, run it, then delete it:

```python
import subprocess, sys, re, json

diff_range = sys.argv[1]   # e.g. "main..HEAD" or "main"
file_path  = sys.argv[2]   # relative path e.g. "emf/src/main/java/.../Foo.java"

result = subprocess.run(
    ['git', 'diff', diff_range, '--', file_path],
    capture_output=True, text=True
)

changed_lines = set()
new_line_nr = 0   # tracks current line number in the new (right-hand) file

for line in result.stdout.split('\n'):
    if line.startswith('@@'):
        # @@ -old_start,old_count +new_start,new_count @@
        # Reset counter to new_start for this hunk
        m = re.search(r'\+(\d+)', line)
        if m:
            new_line_nr = int(m.group(1))
    elif line.startswith('+++') or line.startswith('---'):
        pass   # file header lines, skip
    elif line.startswith('+'):
        # Truly added/modified line — add to changed set
        changed_lines.add(new_line_nr)
        new_line_nr += 1
    elif line.startswith('-'):
        # Deleted line — exists only in old file, do NOT increment new_line_nr
        pass
    elif line.startswith(' '):
        # Context line — unchanged, present in both files; increment but do NOT add
        new_line_nr += 1

print(json.dumps(sorted(changed_lines)))
```

```bash
python3 /tmp/sg_lines.py <DIFF_RANGE> <file_path>
rm /tmp/sg_lines.py
# Output: [45, 46, 78, 79, 80, ...]  ← only truly added/modified lines, no context
```

Store the result as `CHANGED_LINES[filename]` — a map of basename → set of changed line numbers.

**SonarQube's "new code" definition:** Only lines that are new or modified in the diff count toward the coverage metric. Lines that existed before and are unchanged do not count — even if they are in the same file.

**If the list is empty:** Print `✓ PASS — no new production Java files in the selected scope.` Write a PASS `sonar-gate.md` (see Step 7 format). Exit.

**If `--file` argument was provided:** Replace the full list with just that one file. Verify it exists:
```bash
ls <path>
```
If not found, print error and exit.

---

## Step 2 — Run JaCoCo

### 2a — Detect whether JaCoCo is already configured in pom.xml

**Running our own `prepare-agent` on top of an existing JaCoCo plugin creates two agents on the same JVM — this causes a forked-VM crash (exit code 134). Always check first.**

```bash
# Check root pom and any module poms that contain the changed files
grep -rl "jacoco-maven-plugin" . --include="pom.xml" | head -5
```

If any `pom.xml` already has `jacoco-maven-plugin`:
- **Do NOT pass `prepare-agent` on the CLI** — the pom already wires the agent
- Note the existing JaCoCo version from the pom for reference (it may differ from 0.8.11)

### 2b — Determine which module(s) to run

For multi-module projects, running from the root compiles all modules and runs all tests. If unrelated modules have failing tests, the whole build can fail before JaCoCo finishes. To avoid that:

1. Identify which module(s) contain the changed files:
   ```bash
   # e.g. changed file is emf/src/main/java/.../Foo.java → source module is emf/
   ```

2. Check if tests for those files live in a **separate test module** (common pattern: `emf/` has source, `emf-ut/` has tests):
   ```bash
   git log <BASE_BRANCH>..HEAD --name-only | grep "src/test" | head -10
   ```
   If tests are in a sibling module (e.g. `emf-ut/`), you must run from that test module.

3. **Critical — install the source module first if source and test modules are separate.**

   When `emf-ut` depends on `emf` as a Maven artifact, running `mvn test` in `emf-ut/` directly resolves `emf` from your local `.m2` cache — picking up the **old snapshot**, not your local changes. Your code changes will be invisible to the tests.

   Always install the source module to `.m2` before running the test module:
   ```bash
   mvn install -f <source-module>/pom.xml -DskipTests -q
   ```
   e.g.
   ```bash
   mvn install -f emf/pom.xml -DskipTests -q
   ```
   This takes ~10–15 seconds and ensures the test module sees your latest changes. Skip this only if you ran the full reactor build (`mvn install` from root) recently.

### 2c — Run the appropriate command

**Case A — JaCoCo already in pom.xml, run from the test module:**
```bash
cd <test-module-dir>
mvn test -Dproject.reporting.outputEncoding=UTF-8
```
The pom's `prepare-agent` binding fires automatically during the `test` lifecycle.

**Case B — JaCoCo already in pom.xml, run from root:**
```bash
mvn test -Dproject.reporting.outputEncoding=UTF-8 --fail-at-end
```

**Case C — No JaCoCo in any pom.xml (single-module):**
```bash
mvn org.jacoco:jacoco-maven-plugin:0.8.11:prepare-agent \
    test \
    org.jacoco:jacoco-maven-plugin:0.8.11:report \
    -Dproject.reporting.outputEncoding=UTF-8
```

**Case D — No JaCoCo in any pom.xml (multi-module, run from root):**
```bash
mvn org.jacoco:jacoco-maven-plugin:0.8.11:prepare-agent \
    test \
    org.jacoco:jacoco-maven-plugin:0.8.11:report \
    -Dproject.reporting.outputEncoding=UTF-8 \
    --fail-at-end
```

`--fail-at-end` ensures all modules run even if one has test failures.

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

**If `jacoco.xml` is missing but a `jacoco.exec` file exists — cross-module report pattern:**

This happens when the test module (`emf-ut/`) has no production classes of its own. JaCoCo ran and collected execution data into `<test-module>/target/jacoco.exec`, but cannot generate the XML report because it can't find classes to map coverage onto.

Fix: generate the report manually, pointing `dataFile` at the exec file and running from the source module directory (which has `target/classes/`):

```bash
# Step 1: confirm the exec file exists in the test module
ls <test-module>/target/jacoco.exec

# Step 2: detect the JaCoCo version already in the pom (use that version, not 0.8.11)
grep -A2 "jacoco-maven-plugin" <test-module>/pom.xml | grep "<version>"
# e.g. → 0.8.13

# Step 3: generate the report from the source module, pointing at the exec file
cd <source-module>           # e.g. cd emf/
mvn org.jacoco:jacoco-maven-plugin:<VERSION>:report \
    -Djacoco.dataFile=$(pwd)/../<test-module>/target/jacoco.exec \
    -Dproject.reporting.outputEncoding=UTF-8 2>&1 | tail -5
```

e.g. for emf-parent:
```bash
cd emf/
mvn org.jacoco:jacoco-maven-plugin:0.8.13:report \
    -Djacoco.dataFile=$(pwd)/../emf-ut/target/jacoco.exec \
    -Dproject.reporting.outputEncoding=UTF-8 2>&1 | tail -5
```

This generates `emf/target/site/jacoco/jacoco.xml` — use that path in Step 3.

If `jacoco.exec` also missing after a successful test run: `JaCoCo agent did not fire — check that the pom's prepare-agent binding is active and that tests are not all @Ignored.` Exit.

---

## Step 3 — Parse `jacoco.xml` Filtering to Changed Lines Only

**This is the key step that matches SonarQube's "new code" definition.**
SonarQube does NOT measure coverage of the whole file — it measures coverage of only the lines that changed in the diff. A line that existed before and is unchanged does not count, even if it is uncovered.

jacoco.xml has per-line data: `<line nr="N" mi="M" ci="C" mb="B" cb="B"/>` where:
- `nr` = line number, `mi` = missed instructions, `ci` = covered instructions
- `mb` = missed branches, `cb` = covered branches
- A line is "covered" if `ci > 0`. A line is "a branch line" if `mb + cb > 0`.

Write the following script to `/tmp/sg_parse.py`, run it, then delete it:

```python
import xml.etree.ElementTree as ET, sys, os, json

report_path   = sys.argv[1]   # e.g. target/site/jacoco/jacoco.xml
changed_lines_json = sys.argv[2]  # JSON: {"Foo.java": [10,11,12,...], "Bar.java": [...]}

tree = ET.parse(report_path)
root = tree.getroot()

changed_map = json.loads(changed_lines_json)  # basename -> list of ints
results = []
matched = set()

for pkg in root.findall('package'):
    for sf in pkg.findall('sourcefile'):
        name = sf.get('name')
        if name not in changed_map:
            continue
        matched.add(name)
        changed_set = set(changed_map[name])

        lc = lm = bc = bm = 0
        for line in sf.findall('line'):
            nr = int(line.get('nr', 0))
            if nr not in changed_set:
                continue   # skip unchanged lines — this is what SonarQube does
            ci = int(line.get('ci', 0))
            mi = int(line.get('mi', 0))
            cb = int(line.get('cb', 0))
            mb = int(line.get('mb', 0))
            # Line covered = at least one instruction was executed
            if ci > 0:
                lc += 1
            else:
                lm += 1
            bc += cb
            bm += mb

        lt = lc + lm
        bt = bc + bm
        lpct = round(lc / lt * 100, 1) if lt > 0 else 100.0
        bpct = round(bc / bt * 100, 1) if bt > 0 else 100.0
        # SonarQube combined "coverage" = (covered_lines + covered_conditions) / (total_lines + total_conditions)
        combined = round((lc + bc) / (lt + bt) * 100, 1) if (lt + bt) > 0 else 100.0
        results.append((name, lc, lm, lt, lpct, bc, bm, bt, bpct, combined))

for f in changed_map:
    if f not in matched:
        results.append((f, 0, -1, -1, 0.0, 0, -1, -1, 0.0, 0.0))

for r in results:
    print('|'.join(str(x) for x in r))
```

Run — pass the `CHANGED_LINES` map as JSON:
```bash
python3 /tmp/sg_parse.py target/site/jacoco/jacoco.xml \
  '{"EnumTypeResolverImpl.java": [45, 46, 47, 78, 79]}'
rm /tmp/sg_parse.py
```

**Output columns per line:**
`filename | line_covered | line_missed | line_total | line_pct | branch_covered | branch_missed | branch_total | branch_pct | combined_pct`

**If a file has `-1` for totals** (absent from jacoco.xml — zero instrumentation):
- Use `line_covered=0, line_missed=<count of changed lines>, line_pct=0%, branch_pct=0%, combined_pct=0%`

**Multi-module:** Run the parser once per jacoco.xml, merge results by filename. If a file appears in multiple reports, use the report from the module whose source path matches.

---

## Step 4 — Calculate Aggregate Coverage

Use the **SonarQube combined formula** — this is what SonarQube reports as "Coverage on New Code" and what the quality gate checks:

```
combined_agg = (sum(line_covered) + sum(branch_covered)) /
               (sum(line_total)   + sum(branch_total))   * 100
```

Also compute separately for display:
```
line_agg = sum(line_covered) / sum(line_total)   * 100
cond_agg = sum(branch_covered) / sum(branch_total) * 100
```

Round all to one decimal place.

- If `branch_total == 0` across all files: `cond_agg = 100%`, and combined = line_agg
- These numbers are based only on changed lines (filtered in Step 3) — this matches SonarQube exactly

**Apply threshold** (default 90) against the combined metric:

```
pass = combined_agg >= threshold

if pass  → PASS → Step 7
if fails → WARNING → Step 5
```

The combined metric is what SonarQube's quality gate uses (not separate line and condition gates). If the user wants stricter checking, both individual metrics are still displayed.

---

## Step 5 — Display Coverage Table and Prompt Developer

Print the full table matching SonarQube's Measures view (changed lines only):

```
Coverage Report — New Code only (changed lines vs <BASE_BRANCH>)
──────────────────────────────────────────────────────────────────────────────────────────────
File                              New Lines   Line Cov   Uncov   Cond Cov   Uncov   Combined
EnumTypeResolverImpl.java                10      100%        0      85.7%       2      91.7%
PointsEngineRuleConfigThrift.java         4       75%        1      100%        0      83.3%
──────────────────────────────────────────────────────────────────────────────────────────────
Aggregate (new code)
  Line coverage:     100%   (10 lines, 0 uncovered)
  Condition coverage: 85.7% (14 conditions, 2 uncovered)
  Combined coverage:  91.7% (target 90%, gap -1.7% → PASS)
──────────────────────────────────────────────────────────────────────────────────────────────

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

**IMPORTANT:** Write ONLY what is in the template below. Do NOT include raw JaCoCo line data, per-line coverage details, XML output, parser output, or any other debug information. The report is for humans — keep it clean.

Copy this template exactly, substituting the `<placeholders>`:

```markdown
# Sonar Gate Report

| | |
|---|---|
| **Branch** | `<git branch --show-current>` |
| **Run date** | <YYYY-MM-DD> |
| **Base branch** | `<BASE_BRANCH>` |
| **Scope** | <"Committed changes only" or "All changes including uncommitted"> |
| **Module(s)** | <e.g. "emf (source) + emf-ut (tests)" or "single-module"> |
| **Files analysed** | <N> new/changed production Java file(s) |
| **Threshold** | <N>% |

---

## Coverage on New Code

| Metric | New Lines | Coverage | Target | Gap | Verdict |
|---|---|---|---|---|---|
| Line Coverage | <N> lines | <X.X>% | <threshold>% | <+/->X.X% | ✓ PASS / ⚠ BELOW |
| Condition Coverage | <N> conditions | <X.X>% | <threshold>% | <+/->X.X% | ✓ PASS / ⚠ BELOW |
| **Combined (gate)** | — | **<X.X>%** | **<threshold>%** | **<+/->X.X%** | **✓ PASS / ⚠ BELOW** |

> Combined = (covered lines + covered conditions) / (total lines + total conditions) — matches SonarQube's quality gate formula.

---

## Per-File Breakdown

| File | New Lines | Line Cov | Uncov Lines | Cond Cov | Uncov Conds | Combined |
|---|---|---|---|---|---|---|
| EnumTypeResolverImpl.java | 10 | 100% | 0 | 85.7% | 2 | 91.7% |

---

## Verdict

**✓ PASS** — Combined coverage on new code is X.X%, above the X% threshold.

*or*

**⚠ WARNING** — Combined coverage on new code is X.X%, below the X% threshold. Developer chose to continue.

---

## Uncovered Methods
*(omit this section entirely if verdict is PASS)*

| File | Method | Line |
|---|---|---|
| PointsEngineRuleEditorImpl.java | `getRulesByOrg` | 34 |
| PointsEngineRuleEditorImpl.java | `deleteRule` | 67 |
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
| JaCoCo already in pom.xml | Use `mvn test` only — do NOT add `prepare-agent` CLI arg (causes dual-agent crash, exit code 134) |
| Tests in separate module from source | `mvn install -f <source-module>/pom.xml -DskipTests -q` first, then run from test module — skipping install means tests run against stale `.m2` snapshot |
| jacoco.xml missing but jacoco.exec exists | Test module has no production classes — generate report from source module with `-Djacoco.dataFile=<test-module>/target/jacoco.exec` |
| Scope = uncommitted (option 2) | Use `git diff <BASE_BRANCH>` not `git diff <BASE_BRANCH>..HEAD` — includes staged + unstaged edits |
| `session-memory.md` not found | Run standalone without it — optional input |
| `--file` path not found | Print error and exit |
| `/tmp` scripts left behind | Always `rm /tmp/sg_parse.py` and `/tmp/sg_methods.py` after use |
