# BRD Standardisation Guide — For Product Management Team

> **Purpose**: This document defines the standard structure, mandatory sections, and quality checklist for every BRD entering the AIDLC (AI Development Lifecycle) pipeline. A well-structured BRD eliminates 60-70% of the back-and-forth questions BA and ProductEx would otherwise need to ask — accelerating the entire workflow.
>
> **Audience**: Product Managers, Program Managers, Pod Leads
>
> **Maintained by**: ProductEx skill
>
> **Last updated**: 2026-04-01

---

## Why Standardisation Matters

The AIDLC pipeline consumes BRDs through two parallel readers:
1. **BA (Business Analyst)** — refines requirements into structured specs, asks clarifying questions one at a time
2. **ProductEx (Product Expert)** — cross-references the BRD against the product registry, official docs, and codebase to surface conflicts, gaps, and product team questions

When a BRD is missing critical sections, both BA and ProductEx generate **avoidable questions** that pause the workflow, require human input, and slow delivery. A standardised BRD front-loads this information so the pipeline moves faster.

---

## BRD Structure — Mandatory Sections

Every BRD entering the AIDLC must contain these sections. Optional sections are marked as such.

### 1. Metadata Header

```markdown
| Field              | Value                                      |
|--------------------|--------------------------------------------|
| **Title**          | [Feature/module name]                      |
| **Document Owner** | [PM name]                                  |
| **Version**        | [x.y]                                      |
| **Status**         | [Draft | In Review | Active — In Build]    |
| **Audience**       | [Engineering Pod name]                     |
| **Date**           | [Date]                                     |
| **Program/Module** | [Which product module this belongs to]     |
| **Jira Epic(s)**   | [Link(s) to Jira epic]                     |
```

**Why**: The pipeline needs to know which product module is affected (for ProductEx to locate the right registry entry) and which Jira epic to track against.

---

### 2. Executive Summary (max 1 paragraph)

What is being built/changed and why. One paragraph. No jargon.

**Anti-pattern** (from Tiers & Benefits BRD): The executive summary was 2 paragraphs + bullet points — fine for a human reader, but buries the core ask. Keep it tight:

> "Rebuild the Tiers & Benefits configuration experience in Garuda — replace the fragmented 6-screen flow with a single comparison matrix for tier management, add a first-class benefits module, integrate aiRa for conversational configuration, and add maker-checker approval workflows."

---

### 3. Problem Statement

- What's broken today and who it hurts
- Why it hurts now (urgency/business trigger)
- What the desired end state looks like

**Good in the Tiers BRD**: Persona-based problem framing (Maya, Alex, Priya) was excellent — keep doing this.

**Missing in the Tiers BRD**: No quantified business impact. "Maya spends 45 minutes" is good, but "this delays X launches per quarter costing $Y" closes the loop.

---

### 4. Epics & User Stories — With Priority and Ownership

This is the most critical section for AIDLC consumption. Every epic and user story **must** have:

#### 4a. Priority Ordering (MANDATORY)

Every epic and every user story within it must have a **granular priority code**:

| Priority | Meaning | AIDLC Impact |
|----------|---------|--------------|
| `P0`     | Must ship — blocks release | AIDLC processes these first |
| `P0.1`   | Must ship — dependency of another P0 | Sequenced before the dependent P0 |
| `P0.2`   | Must ship — lower urgency than P0.1 | Sequenced after P0.1 |
| `P1`     | Should ship — high value but not blocking | AIDLC processes after all P0.x |
| `P1.1`   | Should ship — lower within P1 band | — |
| `P2`     | Nice to have — defer if needed | AIDLC may skip or defer |

**Why**: The AIDLC pipeline processes epics in priority order. Without granular priorities, BA has to ask "which epic comes first?" and "is US-3 more important than US-5?" — slowing Phase 00.

**Anti-pattern (Tiers BRD)**: All 4 epics were marked `P0 Phase 1`. This tells the pipeline nothing about sequencing. Which P0 comes first? Are all user stories within E1 equally urgent?

**Correct format**:
```
Epic 1: Tier Intelligence — P0
  E1-US1: Tier Listing with Comparison Matrix — P0.1
  E1-US2: Tier Creation — P0.2
  E1-US3: Tier Editing — P0.3
  E1-US4: Maker-Checker Approval — P0.4
  E1-US5: Change Log — P1
  E1-US6: Simulation Mode — P1.1

Epic 2: Benefits as a Product — P0
  E2-US1: Benefits Listing — P0.1
  E2-US2: Benefit Creation — P0.2
  E2-US3: Custom Fields — P1
```

#### 4b. Ownership Tagging (MANDATORY)

Every user story must be tagged with its **ownership scope** — who builds it:

| Tag | Meaning | Example |
|-----|---------|---------|
| `[UI]` | Frontend/render — owned by UI team | Tier listing page, comparison matrix |
| `[Backend]` | REST APIs, business logic, DB — owned by backend team | Simulation API, approval workflow API |
| `[UI + Backend]` | Full-stack — needs both teams | Tier creation (form UI + POST API) |
| `[AI/ML]` | AI/ML model or integration — owned by AI team | aiRa intent parsing, context layer |
| `[Infra]` | Infrastructure, DevOps, platform | Kafka topic setup, new microservice deployment |
| `[Cross-team]` | Requires coordination across pods | Changes to shared domain models |

**Why**: The AIDLC Architect needs to know who owns the solution space. Without ownership tags, Architect has to infer scope — leading to misallocated solutioning. BA also routes code/backend questions differently than UI questions.

**Anti-pattern (Tiers BRD)**: No ownership tags anywhere. Is the comparison matrix purely UI? Does simulation mode need a new backend service? The BRD doesn't say — forcing BA/Architect to ask.

**Correct format**:
```
E1-US1: Tier Listing with Comparison Matrix — P0.1 [UI]
E1-US6: Simulation Mode — P1.1 [UI + Backend]
  - Simulation UI: render inputs + visualization [UI]
  - /tiers/{tierId}/simulate endpoint [Backend]
E3-US1: aiRa Context Layer API — P0.1 [Backend + AI/ML]
```

#### 4c. Concrete Examples (MANDATORY for complex stories)

Every user story that involves **business logic, calculations, configurations, or conditional flows** must include at least one concrete example showing input → expected output.

**Why**: Without examples, BA cannot write testable acceptance criteria, QA cannot identify edge cases, and Architect cannot validate the solution logic. The AIDLC will pause repeatedly to ask "can you give me an example of how X would work?"

**Anti-pattern (Tiers BRD)**: E1-US6 (Simulation Mode) describes what simulation does at a high level but provides no concrete example:
- What input configuration change does Maya type?
- What does the simulation output actually look like with real numbers?
- How is the "member distribution forecast" calculated — is it a snapshot or a projection over time?

**Correct format**:
```markdown
#### E1-US6: Simulation Mode — P1.1 [UI + Backend]

**Example: Tier threshold change simulation**

Input:
- Program: "RetailRewards" (3 tiers: Silver, Gold, Platinum)
- Proposed change: Lower Gold threshold from $500 → $400 annual spend
- Current member distribution: Silver: 12,000 | Gold: 4,200 | Platinum: 890

Expected Output:
- Projected member distribution at next evaluation:
  Silver: 10,153 (-1,847) | Gold: 6,047 (+1,847) | Platinum: 890 (unchanged)
- Members affected: 1,847 Silver members newly qualify for Gold
- Estimated incremental benefit cost: $42,000/year (based on Gold benefit package value × 1,847)
- Visualization: side-by-side bar chart (Current vs Projected)

Edge cases to address:
- What if proposed threshold creates overlap with Silver threshold?
- What if evaluation schedule hasn't run yet — is simulation based on current data or next-cycle projection?
- What about members in grace period — are they included?
```

---

### 5. Acceptance Criteria (per User Story)

Each user story must have **testable** acceptance criteria in Given/When/Then or checklist format. Not vague descriptions — concrete conditions.

**Anti-pattern (Tiers BRD)**: User stories have bullet-point descriptions of what should happen, but no formal acceptance criteria. For example, E1-US4 (Maker-Checker) says "Approver actions: Approve, Reject, Request Changes" but doesn't specify:
- What happens to the tier config when rejected? Does it revert to the last approved state?
- Is there a timeout on approval? What if the approver never acts?
- Can the submitter withdraw a pending change?

**Correct format**:
```markdown
#### Acceptance Criteria — E1-US4: Maker-Checker

- [ ] GIVEN a tier config change is submitted WHEN maker-checker is enabled for the program THEN a pending record is created with status "Pending Approval"
- [ ] GIVEN a pending change exists WHEN the approver clicks "Approve" THEN the change goes live at the next evaluation cycle (not immediately)
- [ ] GIVEN a pending change exists WHEN the approver clicks "Reject" THEN the change is discarded, status moves to "Rejected", and the submitter is notified with the rejection comment
- [ ] GIVEN a pending change exists WHEN 72 hours pass without action THEN [specify: auto-escalate? auto-reject? notify again?]
- [ ] GIVEN a pending change exists WHEN the submitter wants to withdraw THEN [specify: allowed? creates audit entry?]
```

---

### 6. API Contract Sketch (for Backend-tagged stories)

For any story tagged `[Backend]` or `[UI + Backend]`, provide:
- Endpoint shape (method, path, key request/response fields)
- Validation rules the API must enforce
- Error scenarios

**Good in the Tiers BRD**: Section 10 provides a high-level endpoint table — this is a start. But it lacks request/response shapes, validation rules, and error codes.

**Correct format**:
```markdown
#### POST /tiers/{tierId}/simulate

Request:
{
  "proposedChanges": {
    "eligibilityThreshold": 400,   // changed from 500
    "renewalCondition": "SPEND_400_12M"
  },
  "simulationWindow": "NEXT_EVALUATION"  // or "30_DAYS" / "90_DAYS"
}

Response:
{
  "currentDistribution": { "Silver": 12000, "Gold": 4200, "Platinum": 890 },
  "projectedDistribution": { "Silver": 10153, "Gold": 6047, "Platinum": 890 },
  "affectedMembers": 1847,
  "estimatedCostImpact": { "currency": "USD", "annual": 42000 },
  "warnings": ["Threshold overlap with Silver at $300"]
}

Validation:
- proposedChanges must contain at least one field change
- Threshold cannot be negative or zero
- Threshold cannot be lower than the tier below it

Errors:
- 400: Invalid threshold (overlap, negative)
- 404: Tier not found
- 409: Another simulation is in progress for this tier
```

---

### 7. Scope Boundaries (MANDATORY)

Explicitly state:
- **In scope**: what this BRD covers
- **Out of scope**: what this BRD intentionally excludes and why
- **Dependencies**: what must be built/available before this can start

**Good in the Tiers BRD**: Section 11 (Out of Scope) exists and is well-structured.

**Missing in the Tiers BRD**: No **dependencies** section. Does E1 depend on E4 (APIs) being built first? Does E3 (aiRa) depend on E1 (listing) existing? The BRD doesn't say.

**Correct format**:
```markdown
## Dependencies
| This Story | Depends On | Why |
|------------|-----------|-----|
| E1-US6 (Simulation) | E4-API: POST /tiers/{tierId}/simulate | Simulation UI calls this endpoint |
| E3 (aiRa) | E4-API: GET /program/{id}/context | aiRa needs the context layer API |
| E1-US4 (Maker-Checker) | E4-API: Approval endpoints | Approval workflow is API-driven |
| E2-US2 (Benefit Creation) | E1-US1 (Tier Listing) | Benefit linking needs tiers to exist |
```

---

### 8. Open Questions (MANDATORY)

Any question the PM themselves has that isn't yet answered. Be honest — the AIDLC will surface these anyway. Front-loading them saves time.

**Good in the Tiers BRD**: Section 12 has 6 open questions — excellent practice. Keep doing this.

**Improvement**: Tag each question with who needs to answer it:

```markdown
| # | Question | Needs Answer From | Status |
|---|----------|-------------------|--------|
| 1 | Does the program context API exist? | Backend/Infra (Karan/Anuj) | Open |
| 2 | Simulation — real-time or queued? | Backend (Bhavik/Mohit) | Open |
| 3 | Maker-checker per-role or per-program? | Product (Surabhi) | Open |
```

---

### 9. Success Metrics (MANDATORY)

Quantified targets with baselines, targets, timeframes, and owners.

**Good in the Tiers BRD**: Section 9 is well-structured — baseline, target, owner. Keep this format.

---

### 10. Glossary / Domain Terminology (MANDATORY)

Define every product-specific term used in the BRD. The AIDLC pipeline (specifically BA and ProductEx) will adopt these exact terms. If the BRD uses inconsistent terminology, BA will ask clarifying questions.

**Anti-pattern (Tiers BRD)**: The BRD uses "KPI" to mean different things in different contexts — sometimes it means "tier qualification metric" (spend, transactions), sometimes it means "dashboard metric" (renewal rate, upgrade velocity). No glossary resolves this.

**Correct format**:
```markdown
## Glossary
| Term | Definition | Used In |
|------|-----------|---------|
| KPI (Tier) | The metric used to evaluate tier eligibility — e.g., lifetime spend, current points | Tier configuration, eligibility logic |
| KPI (Dashboard) | Program health metrics displayed in the listing header — e.g., total members, renewal rate | Tier listing page |
| Evaluation Cycle | The scheduled process that checks all members against tier criteria and triggers upgrades/downgrades | Tier renewal, downgrade logic |
| Grace Period | Number of days after a member fails renewal criteria before downgrade executes | Downgrade configuration |
| Maker-Checker | Two-step approval workflow — one person submits, another approves | Config change management |
```

---

## Sections That Are Optional (But Recommended)

| Section | When to Include |
|---------|----------------|
| Interface Philosophy / UX Options | When multiple approaches exist and the pod needs to decide |
| Persona Deep-Dives | When the feature serves distinctly different user types |
| Competitive Analysis / Market Signal | When justifying urgency or differentiation |
| Long-term Vision | When the feature is part of a multi-phase strategy |
| aiRa / AI Integration Details | When the feature involves AI capabilities |

---

## BRD Quality Checklist (Before Submitting to AIDLC)

Use this checklist before handing the BRD to the engineering pod:

### Structure
- [ ] Metadata header with program/module, Jira link, and owner
- [ ] Executive summary is 1 paragraph or less
- [ ] Problem statement includes who suffers and why now

### Epics & Stories
- [ ] Every epic has a granular priority (P0, P0.1, P1, P1.2, etc.) — not just "P0"
- [ ] Every user story has a priority within its epic
- [ ] Every user story has an ownership tag: `[UI]`, `[Backend]`, `[UI + Backend]`, `[AI/ML]`, `[Infra]`, `[Cross-team]`
- [ ] Every complex user story has at least one concrete example (input → expected output)
- [ ] Every user story has testable acceptance criteria (Given/When/Then or checklist)

### Technical
- [ ] Backend-tagged stories have API contract sketches (endpoint, request/response, validations, errors)
- [ ] Dependencies between epics/stories are explicitly mapped
- [ ] Scope boundaries are clear (in-scope, out-of-scope, dependencies)

### Product Alignment
- [ ] Glossary defines all product-specific terms used in the BRD
- [ ] Open questions are listed with the person who needs to answer them
- [ ] Success metrics have baselines, targets, timeframes, and owners

### AIDLC Readiness
- [ ] BRD is in PDF, DOCX, or Markdown format
- [ ] File is accessible at a known path for `/workflow brd:<path>` invocation
- [ ] All P0 open questions are answered before submission (P1/P2 can remain open)

---

## Gap Analysis: Tiers & Benefits PRD v2.0

Below is the specific gap analysis of the Tiers & Benefits BRD against this standard. This shows what ProductEx and BA would have asked — and what a standardised BRD would have front-loaded.

### What the BRD Does Well
1. **Problem framing** — persona-based storytelling (Maya, Alex, Priya) is excellent
2. **User journey examples** — the hybrid interface journey (Section 5) is very clear
3. **Out of scope** — Section 11 is explicit about what's deferred and why
4. **Open questions** — Section 12 honestly lists unknowns
5. **Success metrics** — Section 9 has baselines and targets
6. **API endpoint table** — Section 10.2 provides a high-level contract surface

### What's Missing (Would Cause AIDLC Questions)

| # | Gap | Impact on AIDLC | Section Fix |
|---|-----|-----------------|-------------|
| 1 | **All epics are P0 Phase 1 with no sub-prioritisation** | BA asks: "Which epic should Architect solution first? Are E1-US5 and E1-US6 truly P0?" | §4a: Priority Ordering |
| 2 | **No ownership tags on any user story** | Architect asks: "Is simulation mode UI-only? Does the comparison matrix need new APIs?" | §4b: Ownership Tagging |
| 3 | **No concrete examples for simulation mode** | BA asks: "What does the simulation output look like? What numbers does Maya see?" QA asks: "What are the edge cases?" | §4c: Concrete Examples |
| 4 | **No acceptance criteria on any user story** | QA cannot write test scenarios. BA must derive acceptance criteria from bullet-point descriptions, asking "Is this complete?" for each story | §5: Acceptance Criteria |
| 5 | **API contracts are high-level only — no request/response shapes** | Architect must infer field names, validation rules, and error codes. Backend team has no contract to build against | §6: API Contract Sketch |
| 6 | **No dependency map between epics** | Architect asks: "Can E1 start without E4? Does E3 depend on E1?" Leads to incorrect parallelisation | §7: Dependencies |
| 7 | **"KPI" used with two different meanings** | ProductEx flags terminology conflict. BA asks for clarification — is it the tier metric or the dashboard metric? | §10: Glossary |
| 8 | **Maker-checker timeout/withdrawal not specified** | BA asks: "What if the approver never acts? Can the submitter cancel?" — these are predictable questions the BRD should answer | §5: Acceptance Criteria |
| 9 | **Simulation SLA undefined** | Is it real-time or queued? What's the acceptable wait time? This is listed in Open Questions but should be resolved before AIDLC submission | §8: Open Questions (resolve P0 questions first) |
| 10 | **No mention of multi-tenancy or data isolation** | ProductEx flags cross-cutting concern gap — is tier config scoped per-org? Per-program? How does tenant isolation work for the new APIs? | §10: Glossary + Cross-cutting in scope boundaries |
| 11 | **aiRa context layer data freshness not specified** | "Real-time awareness" is stated but not defined. Is member distribution live? Cached? What's the staleness tolerance? | §4c: Concrete Examples |
| 12 | **Benefit-to-tier linkage cardinality unclear** | Can one benefit be linked to multiple programs? This is in Open Questions but is a P0 blocker for data model design | §8: Open Questions (resolve before submission) |
| 13 | **No error/failure scenarios for any user story** | What happens when simulation fails? When aiRa can't parse intent? When maker-checker API is down? | §5: Acceptance Criteria (include failure paths) |
| 14 | **Interface Philosophy decision (Option A vs B) not made** | BRD presents two options and says "the pod decides" — but Architect needs to know which one to solution. This decision should happen before AIDLC, or the BRD should clearly state "Option A for Phase 1" | §3: Scope Boundaries |

### Estimated AIDLC Time Saved with Standardised BRD

With the gaps above filled before AIDLC submission:
- **BA Phase**: ~8-12 fewer questions to ask the human (40-60 min saved)
- **ProductEx BRD Review**: ~6 fewer items in brdQnA.md (reduces review gate friction)
- **Architect Phase**: Clearer scope → fewer assumption-based decisions → fewer Analyst blockers
- **Verification Cycles**: Fewer Architect-Analyst-ProductEx loops (potentially saves 1-2 full cycles)

---

## BRD File Format for AIDLC

The BRD can be submitted in any of these formats:
- **PDF** (`.pdf`) — extracted automatically
- **Word** (`.docx`) — extracted automatically
- **Markdown** (`.md` / `.txt`) — read directly

Invoke the workflow:
```
/workflow docs/workflow/TICKET-123/ brd:path/to/your-brd.pdf
```

---

## Template

A blank BRD template following this standard is available at: `docs/product/brd-template.md`
