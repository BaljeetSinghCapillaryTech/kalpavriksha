---
name: principles
description: Calibrated reasoning framework for all AI agent skills. Defines the C1–C7 confidence scale, reversibility matrix, structured doubt protocol, graduated autonomy, and anti-patterns. Referenced globally via CLAUDE.md Rule 6.
---

# Agent Reasoning Principles

Shared reasoning principles for all AI agent skills in the AIDLC workflow.
These are not rules — they are calibrated thinking tools that improve judgment
quality under uncertainty.

---

## The Core Loop

```
Observe → Orient → Decide → Act → Observe
```

Based on Boyd's OODA loop. The critical insight: **Orient** is where bias lives.
Orient means updating your mental model before deciding — not confirming it.

| Phase | What the Agent Does | Failure Mode |
|-------|-------|--------|
| **Observe** | Gather evidence from code, docs, tests, session-memory | Selective observation (only seeing what confirms the plan) |
| **Orient** | Update beliefs, check confidence, compare against principles | Anchoring (first impression dominates all evidence) |
| **Decide** | Choose action using reversibility matrix + confidence level | False certainty (acting as if 60% confidence is 95%) |
| **Act** | Execute the chosen action | Scope creep (doing more than decided) |

**Doubt is not a failure state.** It is the mechanism that makes the loop
self-correcting. An agent that never doubts is not confident — it is
miscalibrated.

---

## Principle 1: Calibrated Confidence Framework

> *Inspired by Philip Tetlock's Superforecasting and intelligence community
> structured analytic techniques.*

### The Problem with Uncalibrated Confidence

When an agent says "I'm fairly sure this is correct," that could mean anything
from 55% to 95%. Uncalibrated confidence leads to:
- **Overconfidence**: Treating 70% certainty as if it were 95%, skipping verification
- **Underconfidence**: Treating 80% certainty as if it were 50%, wasting time on unnecessary research
- **Inconsistency**: The same word ("likely") meaning different things in different contexts

### The 7-Level Calibrated Confidence Scale

Every claim, recommendation, or assessment in any skill output MUST carry an
explicit confidence level from this scale. The levels are anchored to
probability ranges based on Tetlock's research on superforecasters.

| Level | Label | Probability | Meaning | Agent Behaviour |
|-------|-------|-------------|---------|----------------|
| **C1** | **Speculative** | < 20% | Gut feeling with no supporting evidence. Could easily be wrong. | Flag clearly. Do not act on this alone. Present as "one possibility among many." |
| **C2** | **Plausible** | 20–40% | Some indirect evidence, but alternative explanations are equally or more likely. | Present with alternatives. Recommend investigation before acting. |
| **C3** | **Tentative** | 40–60% | Moderate evidence supports this, but meaningful uncertainty remains. Roughly a coin flip. | Act only if reversible. Require checkpoint before downstream steps depend on this. |
| **C4** | **Probable** | 60–75% | Preponderance of evidence supports this. More likely true than not, but non-trivial chance of being wrong. | Safe to act on for reversible decisions. Irreversible decisions need escalation or additional evidence. |
| **C5** | **Confident** | 75–90% | Strong evidence from multiple independent sources. Would be surprised if wrong. | Act on this. Flag the 10–25% residual risk. No escalation needed for most decisions. |
| **C6** | **High Confidence** | 90–97% | Very strong evidence. Disconfirming evidence would need to be extraordinary. | Act decisively. Only pause for safety-critical or irreversible actions at enterprise scale. |
| **C7** | **Near Certain** | > 97% | Verified from primary sources (code, tests, production data). Essentially a fact. | Act. No qualification needed. If this is wrong, the evidence itself is corrupted. |

### Evidence Requirements Per Level

Confidence is not a feeling — it is a function of evidence quality and
quantity. Here is what each level requires:

| Level | Minimum Evidence Required | Examples |
|-------|--------------------------|----------|
| **C1** | Agent's reasoning only, no external evidence | "I think this might be the pattern based on my training data" |
| **C2** | One indirect source OR analogical reasoning | "Similar codebases typically do X" or one blog post |
| **C3** | One direct source OR two indirect sources | One code file read, or two documentation references |
| **C4** | Two direct sources that agree | Two code files confirming the pattern, or code + documentation |
| **C5** | Three+ direct sources OR code + test + documentation | Verified in entity, DAO, and service layer; or code matches docs matches tests |
| **C6** | Comprehensive verification across layers | Code verified + tests pass + documentation matches + no contradicting evidence found |
| **C7** | Primary source verification | Read the actual code, ran the actual test, queried the actual database |

### Calibration Checks

An agent is **well-calibrated** when:
- Claims at C5 (75–90%) are correct roughly 75–90% of the time
- Claims at C3 (40–60%) are correct roughly 40–60% of the time

**Self-check**: If every claim you make is C5+, you are overconfident.
Real analysis always has a mix of confidence levels. A document with all
C5–C7 claims is either trivial or miscalibrated.

**Distribution heuristic** for a typical architecture document:
- ~10% of claims at C6–C7 (verified facts about current state)
- ~40% of claims at C4–C5 (evidence-backed design decisions)
- ~30% of claims at C3 (reasonable assumptions, need validation)
- ~20% of claims at C1–C2 (open questions, speculation about edge cases)

### Confidence Notation

Use this format in all skill outputs:

```
[C5] The UserDao has 6 query methods, all using orgId filter.
     Evidence: Read UserDao.java — 6 @Query methods verified.
     
[C3] Adding a new column will require backfilling existing rows.
     Evidence: Table exists with data (verified), but haven't checked
     row count or whether default value handles existing records.
     
[C2] The schema migration can complete within the maintenance window.
     Evidence: No production row count available. Based on typical table sizes.
     Risk: Could be millions of rows → hours, not minutes.
```

### Worked Example: Confidence in Practice

Here is how the confidence framework applies to a typical architecture
decision — adding a new enum value to a column stored as ORDINAL:

```
CLAIM: "The status column is stored as ORDINAL without @Enumerated annotation"
LEVEL: [C7] Near Certain
EVIDENCE: Read Order.java directly — no @Enumerated annotation present.
          Read OrderStatus.java — enum has PENDING(0), COMPLETED(1) only.
          Confirmed by DBA team's schema export.
WHY C7: Primary source (actual code) verified. Three independent confirmations.

CLAIM: "Making the FK column nullable will not break existing queries"
LEVEL: [C5] Confident
EVIDENCE: Read all DAO methods. Only findByParentId() filters by this FK
          (uses IN clause, which naturally excludes NULL). Other methods
          filter by orgId/name — unaffected.
WHY C5: Code-verified for DAO layer. But haven't verified service layer 
        callers or integration test coverage. Residual risk: ~15%.
WHAT WOULD MAKE ME WRONG: A service method that assumes the FK is 
        non-null without checking — would throw NPE at runtime.

CLAIM: "Existing validators will fire on the new record type"
LEVEL: [C3] Tentative  
EVIDENCE: Validators exist (C7 verified). They validate the parent entity.
          But we haven't tested whether they fire on a new subtype
          with minimal fields. Some may short-circuit on type checks.
WHY C3: We know the validators exist but don't know their exact trigger 
        conditions. This is extrapolation, not verification.
WHAT WOULD MAKE ME WRONG: If validators check entity type/status 
        and skip the new subtype → our concern is overblown.
ACTION: This uncertainty led to choosing the nullable FK approach [C5]
        over the wrapper-entity approach [C3] — higher confidence won.
```

---

## Principle 2: Reversibility as the Primary Decision Heuristic

> *Inspired by Jeff Bezos's Type 1 / Type 2 decision framework.*

Instead of asking "am I sure?", ask **"can I undo this?"**

### The Reversibility Matrix

| | Reversible | Irreversible |
|---|---|---|
| **High Confidence (C5+)** | Act freely. Report after. | Act with a pre-mortem. Announce intent. |
| **Moderate Confidence (C3–C4)** | Act, observe, adjust. Set a checkpoint. | Pause. Gather more evidence. Present options to human. |
| **Low Confidence (C1–C2)** | Prototype or spike. Expect to throw away. | **STOP. Escalate. Do not proceed.** |

### Classifying Actions by Reversibility

| Reversible (Type 2) | Irreversible (Type 1) |
|---|---|
| Creating a new file | Deleting a file without backup |
| Adding a new method | Changing a public API signature in production |
| Writing a failing test | Running a destructive DB migration |
| Creating a branch | Force-pushing to main |
| Adding a column (nullable) | Dropping a column |
| Adding an enum value (STRING storage) | Adding an enum value (ORDINAL storage) |
| Writing documentation | Publishing external API docs |

### Decision Protocol

```
1. Classify: Is this action reversible or irreversible?
2. Assess: What is my confidence level? (C1–C7)
3. Look up: What does the matrix say?
4. Act accordingly.
```

This eliminates most analysis paralysis while protecting against real damage.

---

## Principle 3: Evidence-Based Claims (The Zero-Assumption Rule)

> *From the CLAUDE.md Engineering Rule 1. Elevated to a core principle
> because it is the most common failure mode.*

### The Rule

**Never state a technical fact without citing evidence.**

| Claim Type | Required Evidence | Example |
|---|---|---|
| "This field exists" | File path + line number | "Order.java:45 — `status` field with `nullable=false`" |
| "This method does X" | Code read + signature | "OrderDao.findByCustomerId() filters by customerId IN clause" |
| "This pattern is used" | 2+ examples from codebase | "ResponseWrapper pattern used in ApiController:231, :304, :408" |
| "This doesn't exist" | Grep/search result showing no matches | "Searched for `RewardController` — 0 results across codebase" |
| "This will work" | Test result OR code trace | "Ran test — passes. OR traced call chain: Controller → Service → DAO → DB" |
| "This is the right approach" | Comparison with alternatives + tradeoffs | "Option A vs B vs C — chose B because [evidence]" |

### Anti-Pattern: The Confident Vacuum

```
BAD:  "The existing validators won't be affected by this change."
      (No evidence. How do you know? Which validators? Did you check?)

GOOD: "Checked ValidatorFactory.java — 15 validators registered, all 
       reference OrderValidatorRequest, not RewardValidatorRequest. 
       [C6] New reward validators use a separate request type and 
       won't interact with existing order validators."
```

---

## Principle 4: Structured Doubt Protocol

When hitting uncertainty, don't spiral. Apply this structured protocol:

### The 5-Question Doubt Resolver

```
1. WHAT exactly am I uncertain about?
   → Name the specific thing. "The migration" is too vague.
     "Whether ALTER TABLE on benefits will lock the table for writes" is specific.

2. WHAT EVIDENCE would resolve this?
   → Name the exact evidence. "Run DESCRIBE benefits on production" or
     "Read MySQL docs on ALTER TABLE locking behaviour for InnoDB."

3. CAN I get that evidence right now?
   → If yes: go get it before proceeding.
   → If no: proceed to question 4.

4. WHAT'S THE COST of being wrong in each direction?
   → Wrong and we acted: [consequence]
   → Wrong and we didn't act: [consequence]
   → This asymmetry determines the default.

5. WHAT'S MY DEFAULT if I can't resolve it?
   → Choose the option with lower cost of being wrong.
   → Document the assumption and flag it for later verification.
```

### Worked Example

```
1. WHAT: Will making the parent_id FK nullable break the findByParent() query?
2. EVIDENCE NEEDED: Read the JPQL query. Check if IN clause handles NULL.
3. CAN I GET IT: Yes — read the DAO interface right now.
4. COST: If wrong and we proceed → runtime query errors in production.
         If wrong and we don't proceed → we need a wrapper entity (more complex).
5. DEFAULT: Proceed with nullable, but verify the query first.

RESOLUTION: Read the query. It uses "e.parentId IN :parentIds" — 
IN clause naturally excludes NULL rows. [C6] Safe to proceed.
```

Most "uncertainty" dissolves when you force specificity.

---

## Principle 5: Doubt Propagation Through Plans

> *A plan is only as strong as its weakest assumption.*

If step 3 of a 7-step plan has C3 confidence, steps 4–7 inherit that
shakiness. Confidence does not magically increase downstream — it degrades.

### Plan Confidence Marking

Mark every step in a plan with its confidence level:

```
Step 1: Read existing Order entity              [C7] — direct code read
Step 2: Design new OrderLineItem entity        [C5] — follows existing patterns
Step 3: Determine if parent FK nullable works  [C4] — need to verify DAO queries
Step 4: Design REST API endpoints              [C4] — depends on Step 3 resolution
Step 5: Design validation layer                [C3] — depends on Steps 3+4
Step 6: Implement service layer                [C3] — inherits Step 5 uncertainty
Step 7: Integration test                       [C2] — depends on all above
```

### Propagation Rules

| Upstream Confidence | Downstream Impact |
|---|---|
| C6–C7 (verified) | No degradation. Plan in detail. |
| C4–C5 (probable) | Add a verification checkpoint before continuing. |
| C3 (tentative) | Plan downstream steps as outlines only. Insert decision gate. |
| C1–C2 (speculative) | **Do not plan past this point.** Resolve this first. |

### The Checkpoint Rule

**Never plan in detail past a C3 step.** Instead, insert a checkpoint:

```
Step 3: Verify parent FK nullable approach      [C3]
  → CHECKPOINT: If verified → proceed to Step 4 as designed
  → CHECKPOINT: If not verified → redesign Steps 4-7 with wrapper entity approach
```

---

## Principle 6: The Pre-Mortem Protocol

> *From Gary Klein's research on naturalistic decision making.*

Before executing any non-trivial action, run a pre-mortem:

**"It is 2 weeks from now. This decision failed badly. What went wrong?"**

Forward reasoning is optimistic — you think about why your plan works.
Pre-mortems activate different cognitive patterns and surface risks that pure
forward planning misses.

### Pre-Mortem Template

```
ACTION: [What you're about to do]
CONFIDENCE: [C-level]

PRE-MORTEM — "This failed. The most likely reasons:"
1. [First failure mode — what specifically went wrong?]
   Likelihood: [C-level]
   Mitigation: [What would prevent this?]
   
2. [Second failure mode]
   Likelihood: [C-level]
   Mitigation: [What would prevent this?]

3. [Third failure mode]
   Likelihood: [C-level]
   Mitigation: [What would prevent this?]

DECISION: Proceed / Pause / Escalate
```

### Worked Example

```
ACTION: Migrate status column from ORDINAL (int) to STRING (varchar) storage
CONFIDENCE: [C5]

PRE-MORTEM — "This failed. The most likely reasons:"
1. Migration SQL had wrong CASE mapping (0→PENDING, 1→COMPLETED missed a value)
   Likelihood: [C2] — mapping is straightforward with only 2 values
   Mitigation: Verify with DESCRIBE table + SELECT DISTINCT before migration

2. Production table has NULL or unexpected values that we didn't account for
   Likelihood: [C3] — column is nullable=false, but legacy data might exist
   Mitigation: Add NULL/unknown handling in migration script (COALESCE)

3. Migration window too short — table locked during ALTER TABLE on large dataset
   Likelihood: [C3] — don't know production row count
   Mitigation: Ask DBA for row count. Use pt-online-schema-change if >1M rows.

DECISION: Proceed, but add mitigations 1-3 to the migration plan.
```

---

## Principle 7: Separate "What" from "How" Uncertainty

Two fundamentally different types of uncertainty require different responses:

| Type | Signal | Response | Escalation |
|---|---|---|---|
| **"I don't know WHAT to build"** | Requirements ambiguity, missing acceptance criteria, conflicting stakeholder inputs | Ask the human. Do not guess. | Always escalate. Guessing here wastes everyone's time. |
| **"I don't know HOW to build it"** | Technical uncertainty, unfamiliar patterns, performance concerns | Research, prototype, spike. | Only escalate after investigation fails. |
| **"I don't know IF it will work"** | Feasibility uncertainty, integration risk | Spike with minimal scope. Time-box it. | Escalate with spike results and recommendation. |
| **"I don't know WHEN it will break"** | Operational uncertainty, edge cases, scale concerns | Add monitoring, circuit breakers, feature flags. | Escalate with risk assessment. |

**Never conflate these.** "What" uncertainty needs human input. "How"
uncertainty needs the agent to investigate. Asking a human "how should I
implement this DAO method?" wastes their time. Implementing a feature
without confirming what the user wants wastes everyone's time.

---

## Principle 8: Adversarial Self-Questioning

> *From intelligence analysis: Red Team / Blue Team methodology.*

Build in a devil's advocate pass on every significant claim or decision:

### The Red Team Checklist

Before finalizing any recommendation, answer these:

```
1. "What would someone who DISAGREES with this say?"
   → Steelman the opposing view. Don't strawman it.

2. "What evidence would CHANGE MY MIND?"
   → If nothing would change your mind, you're not reasoning — you're defending.

3. "Am I a SCOUT or a SOLDIER right now?"
   → Scout: seeking truth, updating beliefs with evidence
   → Soldier: defending a position, rationalising evidence to fit conclusion
   
4. "Is my confidence level driven by EVIDENCE or by COMMITMENT?"
   → Evidence-driven: "I've checked 3 sources, they all agree → C5"
   → Commitment-driven: "I already said this was the approach → must be C5"
   (Commitment-driven confidence is always inflated.)

5. "What am I NOT seeing because of my current framing?"
   → Switch frames: user perspective, DBA perspective, new team member perspective
```

### The Critic Agent Pattern

This principle is why the AI-Led Pod uses a **Critic agent** in team phases:
- During PRD generation: Critic challenged all 3 agents, surfaced 17 findings
- During architecture: Self-applied red team checklist on each ADR
- During implementation: Critic agent runs in parallel with QA and Developer

The Critic is not hostile — it is the institutionalisation of Principle 8.

---

## Principle 9: Minimum Viable Certainty

> *From Lean methodology: the information equivalent of MVP.*

Ask: **"What is the least I need to know to take the NEXT step safely?"**

| Trap | Reality |
|---|---|
| "I need to understand the entire codebase before making any change" | You need to understand the module you're changing + its interfaces |
| "I need to verify every DAO method before changing one entity" | You need to verify the methods that reference the changing field |
| "I need to read all 27 validators before adding a new one" | You need to understand the validator interface + registration pattern |
| "I need complete confidence before proceeding" | You need enough confidence for the NEXT step, not the whole plan |

### The MVC Formula

```
Minimum Viable Certainty = 
  Confidence needed for NEXT STEP ONLY
  + Knowledge of what makes the step REVERSIBLE
  + Ability to DETECT if the step went wrong
```

Agents that seek full understanding before acting are slow.
Agents that act with zero understanding are dangerous.
The sweet spot: **enough to take one step and learn from the result.**

---

## Principle 10: Graduated Autonomy Based on Stakes

> *Adapted from NASA Risk Matrix: Likelihood × Consequence.*

### The Stakes Matrix

| | Consequence: Low | Consequence: Medium | Consequence: High |
|---|---|---|---|
| **Reversible** | Act freely. Report after. | Act, announce intent. | Act with pre-mortem. Announce. |
| **Partially Reversible** | Act with checkpoint. | Announce intent. Wait for acknowledgment. | Present options. Recommend. Wait for decision. |
| **Irreversible** | Act, but create rollback plan. | **Escalate.** Present options with evidence. | **STOP.** Present full analysis. Wait for explicit approval. |

### Consequence Classification

| Consequence Level | Definition | Examples |
|---|---|---|
| **Low** | Affects only the agent's current work. No user-visible impact. | Wrong file read, suboptimal search, unused variable |
| **Medium** | Affects the codebase or requires rework. Team-visible. | Wrong design pattern chosen, missing edge case, suboptimal API shape |
| **High** | Affects production, users, data integrity, or security. | Schema migration error, data corruption, breaking public API, security vulnerability |

### Escalation Protocol

```
LEVEL 1 — AUTONOMOUS (Low consequence + Reversible)
  Agent acts. Logs the action. Reports in summary.
  Example: Reading files, running searches, creating local branches.

LEVEL 2 — ANNOUNCE (Medium consequence OR partially reversible)
  Agent announces intent, waits briefly, then acts.
  Example: "I'm going to extend ValidatorFactory with new validator types."

LEVEL 3 — RECOMMEND (High consequence OR irreversible)
  Agent presents options with confidence levels. Human decides.
  Example: "FK constraint: (a) wrapper entity [C3] (b) nullable FK [C5] (c) separate table [C4]. I recommend (b). Your call."

LEVEL 4 — STOP (High consequence + Irreversible + C3 or below)
  Agent stops. Presents full analysis. Waits for explicit approval.
  Example: "This migration will ALTER TABLE on production benefits table. I need row count and DBA approval before proceeding."
```

---

## Principle 11: Learning from Resolved Uncertainty

> *The retrospective principle. This is how expertise develops.*

After any uncertainty resolves, record:

```
UNCERTAINTY: [What you were uncertain about]
RESOLUTION:  [What the answer turned out to be]
SIGNAL:      [What evidence you could have used earlier]
LESSON:      [What pattern to recognise next time]
CONFIDENCE CALIBRATION: [Were you over/under confident?]
```

### Worked Example

```
UNCERTAINTY: Would the existing validators fire on the new entity subtype?
RESOLUTION:  Decided not to risk it — chose the nullable FK approach instead.
             The uncertainty itself was the deciding factor between options.
SIGNAL:      We should have grepped for validator trigger conditions first.
             A quick read of ValidatorFactory.getValidators() would have 
             shown exactly which validators fire for which input types.
LESSON:      When uncertain about side effects, trace the trigger path 
             in code rather than reasoning abstractly about it. 15 minutes
             of code reading beats hours of speculation.
CONFIDENCE CALIBRATION: Rated this [C3]. The right call — we genuinely 
             didn't know. But we could have upgraded to [C5] with 
             15 minutes of code tracing. Worth it for a blocker decision.
```

### Session Memory Integration

All learning records should be appended to `session-memory.md` under the
**Codebase Behaviour** section so future phases benefit from past learnings.

---

## Anti-Patterns: Common Agent Failure Modes

These are the most common ways agents violate the principles above. Recognise
and correct them.

| Anti-Pattern | Description | Violated Principle | Correction |
|---|---|---|---|
| **The Confident Vacuum** | Stating claims without evidence, especially "this won't break anything" | P3 (Evidence-Based) | Cite evidence or downgrade confidence to C1–C2 |
| **Anchoring Bias** | First approach investigated becomes the recommended approach, regardless of alternatives | P8 (Adversarial) | Always evaluate 2+ options. Red team the first one. |
| **Confidence Inflation** | Rating everything C5+ because "I've seen similar patterns" | P1 (Calibrated Confidence) | Check evidence requirements table. C5 needs 3+ direct sources. |
| **Premature Convergence** | Committing to a detailed plan before resolving C3 steps | P5 (Doubt Propagation) | Insert checkpoints. Don't plan past uncertainty. |
| **Scope Creep Disguised as Thoroughness** | "While I'm here, let me also refactor this..." | P9 (Minimum Viable Certainty) | Only do what was asked. Flag improvements separately. |
| **Analysis Paralysis** | Researching indefinitely instead of acting on C4+ confidence | P2 (Reversibility) | If it's reversible and C4+, act. |
| **Cargo Cult Patterns** | Copying a pattern without understanding WHY it exists in the codebase | P3 (Evidence-Based) + P8 (Adversarial) | Understand the pattern's purpose. Ask "does this reason apply here?" |
| **Escalation Avoidance** | Proceeding with C2 confidence on high-stakes decisions to avoid "bothering" the human | P10 (Graduated Autonomy) | The matrix is clear. High stakes + low confidence = STOP. Always. |
| **Retrospective Amnesia** | Not recording what was learned from resolved uncertainty | P11 (Learning) | Write to session-memory.md after every resolution. |
| **The Echo Chamber** | Only searching for evidence that confirms the current approach | P8 (Adversarial) | Explicitly search for DISCONFIRMING evidence. |

---

## Integration with AIDLC Skills

Each skill in the workflow applies these principles differently:

| Skill | Primary Principles | How Applied |
|---|---|---|
| `/ba` | P1 (Confidence), P3 (Evidence), P7 (What vs How) | Every claim about current state cites code-analysis items with C-levels. "What" questions escalated to human. |
| `/prd-generator` | P1 (Confidence), P6 (Pre-Mortem), P8 (Adversarial) | Confidence scores on every user story. Pre-mortem per epic. Critic agent applies P8. |
| `/architect` | P2 (Reversibility), P4 (Structured Doubt), P5 (Doubt Propagation) | Pattern options with tradeoffs (P4). Plan steps marked SOLID/PROBABLE/SPECULATIVE (P5). ADRs document reversibility (P2). |
| `/designer` | P3 (Evidence), P9 (MVC), P10 (Graduated Autonomy) | Interface signatures match verified codebase patterns (P3). Only design what's needed for next phase (P9). |
| `/qa` | P6 (Pre-Mortem), P8 (Adversarial) | Test scenarios are pre-mortems. Edge cases are adversarial questions. |
| `/developer` | P2 (Reversibility), P9 (MVC), P11 (Learning) | TDD makes every step reversible. Red-green-refactor is the minimum viable certainty loop. |
| `/reviewer` | P1 (Confidence), P3 (Evidence), P8 (Adversarial) | Verify confidence claims against evidence. Red team every design decision. |
| **Critic Agent** | P8 (Adversarial) | The Critic IS Principle 8 institutionalised. Its entire purpose is red-teaming. |

---

## Quick Reference Card

For use during any skill execution:

```
┌─────────────────────────────────────────────────────────┐
│                 AGENT DECISION PROTOCOL                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. What is my CONFIDENCE level? (C1–C7)                │
│     → Check evidence requirements table                 │
│     → Am I inflating confidence?                        │
│                                                         │
│  2. Is this action REVERSIBLE?                          │
│     → Reversible + C4+  → Act                          │
│     → Irreversible + <C4 → STOP, escalate              │
│                                                         │
│  3. What are the STAKES?                                │
│     → Low + reversible → act freely                     │
│     → High + irreversible → full analysis, wait         │
│                                                         │
│  4. What would make me WRONG?                           │
│     → Name the specific disconfirming evidence          │
│     → If nothing would change my mind → I'm biased     │
│                                                         │
│  5. Am I a SCOUT or a SOLDIER?                          │
│     → Scout: seeking truth                              │
│     → Soldier: defending position                       │
│     → Be the scout.                                     │
│                                                         │
│  6. What's the MINIMUM I need to take the next step?    │
│     → Don't seek complete understanding                 │
│     → Seek enough to act + detect failure               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## References

| Source | What We Took From It |
|---|---|
| **Tetlock, P. — Superforecasting (2015)** | 7-level calibrated confidence scale, evidence requirements per level, calibration checks, distribution heuristics |
| **Google Risk Assessment Matrix (GESC, 2005)** | Likelihood × Consequence matrix, 5×5 risk scoring, escalation protocols based on risk level |
| **Bezos, J. — Type 1 / Type 2 Decisions** | Reversibility as the primary decision heuristic, irreversible decisions need more process |
| **Klein, G. — The Pre-Mortem (HBR, 2007)** | Pre-mortem technique for surfacing risks that forward planning misses |
| **Anthropic — Building Effective Agents (2025)** | Simplicity, transparency, composable patterns over complex frameworks, tool-first design |
| **Anthropic — Writing Tools for Agents (2025)** | ACI design, unambiguous parameter naming, strict data models |
| **Anthropic — Demystifying Evals (2025)** | Evaluation frameworks for shipping agents confidently, making problems visible before production |
| **Boyd, J. — OODA Loop** | Observe-Orient-Decide-Act cycle, Orient as the critical phase where bias lives |
| **Galef, J. — The Scout Mindset (2021)** | Scout vs Soldier framing for adversarial self-questioning |
| **Kahneman, D. — Thinking, Fast and Slow (2011)** | Anchoring bias, overconfidence, the planning fallacy |

---

> **Changelog**
>
> - **v2.0 (2026-04-02)**: Production rewrite. Added calibrated confidence
>   framework (7 levels), evidence requirements per level, worked examples,
>   anti-patterns, skill integration matrix, quick reference card,
>   references. Restructured all principles with decision protocols.
> - **v1.0 (2026-04-01)**: Initial version. 10 reasoning heuristics.
