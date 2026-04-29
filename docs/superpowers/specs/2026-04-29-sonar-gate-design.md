# SonarGate — Local Coverage Gate Design

**Date:** 2026-04-29  
**Author:** Ritwik Ranjan  
**Status:** Approved — ready for implementation

---

## The Problem

When a developer finishes writing code and pushes a branch, CI runs SonarQube. If new code coverage is below 90%, the build fails. The developer then has to go back, write more tests, push again, wait for CI again — a frustrating round-trip that breaks flow.

The pipeline has no way to warn you about this *before* you push. There's no coverage check between "Developer writes code" and "push to CI". This design fixes that.

---

## What We're Building

Two things:

1. **`/sonar-gate` — a new skill** that runs JaCoCo locally (no pom.xml change, no CI needed), checks coverage on your new/changed files, warns you if you're below 90%, and helps you fix it by generating test stubs.

2. **A small enhancement to the `/sdet` skill** — a lightweight traceability check that catches obviously untested new classes *before* the Developer phase even starts. Saves an extra loop later.

---

## How It Fits in the Pipeline

```
Phase 9  — SDET          (enhanced: traceability check on new skeletons)
Phase 10 — Developer     (unchanged: makes tests GREEN)
Phase 10a — Sonar Gate   ← NEW
Phase 10b — Backend Readiness
Phase 10c — Analyst Compliance
Phase 11  — Reviewer
```

Phase 10a is a **soft gate** — it warns, not blocks. The developer decides whether to fix coverage now or continue.

---

## The `/sonar-gate` Skill — How It Works

### Step 1 — Find your new files

The skill runs:
```bash
git diff main --name-only -- 'src/main/**.java'
```
This gives the list of production Java files you've added or changed on your branch. Test files are excluded — we only care about production code that needs to be covered.

### Step 2 — Run JaCoCo locally

```bash
mvn org.jacoco:jacoco-maven-plugin:prepare-agent \
    test \
    org.jacoco:jacoco-maven-plugin:report
```

This runs your tests and generates a coverage report at `target/site/jacoco/jacoco.xml`. No changes to `pom.xml`. No CI. No pushing. Maven resolves the JaCoCo version from the local Maven repository or downloads the latest stable release. The skill will default to `0.8.11` but accepts a configurable override via `JACOCO_VERSION` env var if the project needs a specific version.

### Step 3 — Parse and filter

The skill reads `jacoco.xml`, filters it down to only your new/changed files from Step 1, and calculates:
- Line coverage per file (covered lines ÷ total lines)
- Aggregate coverage across all new files

### Step 4 — Evaluate

- **≥ 90%** → PASS. Writes `sonar-gate.md` with the coverage table and exits cleanly.
- **< 90%** → WARNING. Shows you the per-file breakdown and asks what you want to do.

### Step 5 — Interactive choice (when WARNING)

```
Coverage on new code: 73% (target: 90%)

File                                          Covered   Missed   %
TierUpgradeService.java                       42        18       70%
SlabValidityCalculator.java                   28        4        87%
TierBenefitMappingValidator.java              0         31       0%

Do you want to improve coverage now, or continue to the next phase?
  [1] Improve now — I'll generate test stubs for uncovered methods
  [2] Continue — log the warning and move on
```

### Step 6 — Remediation loop (if developer chooses "Improve")

For each under-covered file, the skill reads the uncovered methods from `jacoco.xml` and generates UT stubs:

```java
// Generated stub — fill in the test logic
@Test
void validateTierBenefitMapping_whenMappingIsNull_shouldThrow() {
    // Arrange
    
    // Act
    
    // Assert
}
```

The developer fills in the logic, saves, and the skill re-runs JaCoCo from Step 2. This loop repeats until coverage hits 90% or the developer chooses to continue.

---

## Standalone Usage (Outside the Pipeline)

You don't need to be mid-pipeline to use this. If you've finished all your coding and just want to check coverage before pushing, run:

```
/sonar-gate
```

That's it. The skill will find your new files, run JaCoCo, show you coverage, and offer to generate stubs if needed. No pipeline state required. Works on any branch, any time.

---

## SDET Phase Enhancement

At the end of the SDET phase (Phase 9), after writing all tests, the skill runs a traceability check:

- For every new class in the Developer skeleton output, is there at least one UT that references it?
- For every new public method, is there at least one test case that calls it?

If a class or method has zero test references → the SDET phase flags it immediately (before any JaCoCo run). This is a structural check, not a metric check — it catches obvious gaps early and saves the extra loop at Phase 10a.

---

## Output Artifact — `sonar-gate.md`

Every run produces `sonar-gate.md` in the artifacts path (or current directory for standalone runs).

```markdown
## Sonar Gate Report — <branch-name> — <date>

| File | Covered Lines | Missed Lines | Coverage % | Status |
|------|--------------|-------------|------------|--------|
| TierUpgradeService.java | 42 | 18 | 70% | WARN |
| SlabValidityCalculator.java | 28 | 4 | 87% | WARN |
| TierBenefitMappingValidator.java | 0 | 31 | 0% | WARN |

**Aggregate new-code coverage: 73%**  
**Target: 90%**  
**Verdict: WARNING — developer chose to continue**

Uncovered methods at time of exit:
- TierBenefitMappingValidator#validate (TierBenefitMappingValidator.java:14)
- TierBenefitMappingValidator#validateMapping (TierBenefitMappingValidator.java:38)
```

---

## New Files

| File | Action |
|------|--------|
| `.claude/skills/sonar-gate/SKILL.md` | Create new skill |
| `.claude/skills/sdet/SKILL.md` | Edit — add traceability check subsection |
| `docs/pipeline/tier/sonar-gate.md` | Created per run (artifact) |

The pipeline agent definition (`.claude/agents/feature-pipeline.md`) also needs a Phase 10a entry pointing to the new skill.

---

## Edge Cases

| Case | Behaviour |
|------|-----------|
| No new Java files on branch | Skill exits immediately with PASS (nothing to check) |
| `mvn` not available in PATH | Skill surfaces a clear error: "Maven not found. Ensure mvn is on PATH." |
| Tests fail during JaCoCo run | Skill surfaces failure output and stops — fix tests first |
| jacoco.xml missing after mvn run | Skill checks for file, surfaces error if absent |
| Developer repeatedly chooses "Continue" below 90% | Verdict in sonar-gate.md says WARNING — visible to Reviewer in Phase 11 |
| Standalone run on a branch with no `session-memory.md` | Skill works fine — session-memory is optional context |

---

## Confidence Levels (per principles.md)

- JaCoCo CLI invocation without pom.xml: **C6** — documented Maven plugin invocation syntax, confirmed by SonarQube log showing JaCoCo already in the project's plugin registry
- 90% threshold on new code lines: **C7** — confirmed by user
- Soft gate (warn + choice): **C7** — confirmed by user
- Standalone invocability: **C6** — skill design is self-contained, no hard pipeline state dependencies
