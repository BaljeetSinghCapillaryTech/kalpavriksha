# [Feature/Module Name] — Business Requirements Document

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Title**          | [Feature/module name]                      |
| **Document Owner** | [PM name]                                  |
| **Version**        | [x.y]                                      |
| **Status**         | [Draft / In Review / Active — In Build]    |
| **Audience**       | [Engineering Pod name]                     |
| **Date**           | [Date]                                     |
| **Program/Module** | [Which product module this belongs to]     |
| **Jira Epic(s)**   | [Link(s) to Jira epic]                     |

---

## 1. Executive Summary

<!-- One paragraph. What is being built/changed and why. No jargon. -->

[Write here]

---

## 2. Problem Statement

### 2.1 The Core Problem

<!-- What is broken today. Be specific — not "the UX is bad" but "a program manager spends 45 minutes to do X because Y." -->

[Write here]

### 2.2 Who Suffers and How

<!-- For each persona affected, describe: who they are, what they lose (time, confidence, accuracy), and the business consequence. -->

| Persona | Role | Weekly Time Lost | Biggest Frustration | Business Consequence |
|---------|------|-----------------|--------------------|--------------------|
| [Name]  | [Role] | [hours] | [quote or description] | [what the business loses] |

### 2.3 Why Now

<!-- Business urgency. What happens if we don't build this? What opportunity do we miss? -->

[Write here]

---

## 3. Scope Boundaries

### In Scope
<!-- Explicitly list what this BRD covers. -->
- [Item 1]
- [Item 2]

### Out of Scope
<!-- Explicitly list what is excluded and why. -->
| Feature | Reason for Deferral | Planned For |
|---------|--------------------|-----------:|
| [Feature] | [Why not now] | [Phase/quarter] |

### Dependencies
<!-- What must exist before this work can start? -->
| This Story/Epic | Depends On | Why |
|----------------|-----------|-----|
| [Story] | [Dependency] | [Reason] |

---

## 4. Epics & User Stories

<!--
RULES:
1. Every epic has a priority: P0, P0.1, P1, P1.2, P2, etc.
2. Every user story has a priority within its epic
3. Every user story has an ownership tag: [UI], [Backend], [UI + Backend], [AI/ML], [Infra], [Cross-team]
4. Complex stories MUST include concrete examples
5. Every story MUST have acceptance criteria
-->

### Epic 1: [Epic Name] — P[priority]

**Problem Brief**: <!-- 2-3 sentences explaining what's wrong today for this specific area -->

[Write here]

#### E1-US1: [Story Title] — P[x.y] `[UI / Backend / UI + Backend / AI/ML / Infra / Cross-team]`

**As** [persona], **I want** [goal], **so that** [reason].

**Description**:
<!-- Bullet points describing the expected behaviour -->
- [Behaviour 1]
- [Behaviour 2]

**Example** (mandatory for complex stories):
```
Input:
- [Describe the starting state / user action]

Expected Output:
- [Describe what the user sees / system does]

Edge Cases:
- [What if X?]
- [What if Y?]
```

**Acceptance Criteria**:
- [ ] GIVEN [context] WHEN [action] THEN [expected result]
- [ ] GIVEN [context] WHEN [action] THEN [expected result]
- [ ] GIVEN [error condition] WHEN [action] THEN [error handling]

**API Contract** (for `[Backend]` or `[UI + Backend]` stories):
```
[METHOD] /endpoint/path

Request:
{
  "field": "value",
  "field2": 123
}

Response (200):
{
  "result": "value"
}

Validation Rules:
- [field] must be [constraint]

Error Responses:
- 400: [when and why]
- 404: [when and why]
- 409: [when and why]
```

---

#### E1-US2: [Story Title] — P[x.y] `[ownership tag]`

<!-- Repeat the same structure for each user story -->

---

### Epic 2: [Epic Name] — P[priority]

<!-- Repeat the same structure for each epic -->

---

## 5. Success Metrics

| Metric | Baseline Today | Target (timeframe) | Owner |
|--------|---------------|-------------------|-------|
| [Metric name] | [Current value or "unmeasured"] | [Target value + timeframe] | [PM / Engineering / Ops] |

---

## 6. Glossary / Domain Terminology

<!-- Define EVERY product-specific term used in this BRD. The AIDLC pipeline will adopt these exact terms. -->

| Term | Definition | Used In |
|------|-----------|---------|
| [Term] | [What it means in this context] | [Which sections/stories reference it] |

---

## 7. Open Questions

<!-- Be honest about what you don't know yet. Tag each with who needs to answer. -->

| # | Question | Needs Answer From | Priority | Status |
|---|----------|-------------------|----------|--------|
| 1 | [Question] | [Person/team] | [P0 — must resolve before AIDLC / P1 — can proceed without] | [Open / Resolved: answer] |

---

## Pre-Submission Checklist

Before handing this BRD to the engineering pod for AIDLC processing:

### Structure
- [ ] Metadata header complete (program/module, Jira link, owner)
- [ ] Executive summary is 1 paragraph
- [ ] Problem statement includes who suffers and business impact

### Epics & Stories
- [ ] Every epic has a granular priority (P0, P0.1, P1, P1.2, etc.)
- [ ] Every user story has a priority within its epic
- [ ] Every user story has an ownership tag: `[UI]`, `[Backend]`, `[UI + Backend]`, `[AI/ML]`, `[Infra]`, `[Cross-team]`
- [ ] Every complex story has at least one concrete example (input → output)
- [ ] Every story has testable acceptance criteria (Given/When/Then)

### Technical
- [ ] Backend stories have API contract sketches
- [ ] Dependencies between epics/stories are mapped
- [ ] Scope boundaries are explicit (in/out/depends)

### Product Alignment
- [ ] Glossary defines all product-specific terms
- [ ] Open questions are listed with owners
- [ ] Success metrics have baselines and targets
- [ ] All P0 open questions are resolved before submission

### Format
- [ ] BRD saved as PDF, DOCX, or Markdown
- [ ] File accessible for `/workflow brd:<path>` invocation
