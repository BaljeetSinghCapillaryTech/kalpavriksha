---
name: cross-repo-tracer
description: Traces write/read paths across multiple repositories. Maps HTTP, Thrift, and DB calls between services. Identifies ALL repos that need modification for a feature. Prevents false "0 modifications" claims.
phase: "05"
triggers: [CrossRepoTracer, cross-repo-tracer, /cross-repo-tracer]
inputs: [session-memory.md, 00-ba-machine.md, code-analysis-*.md]
outputs: [cross-repo-trace.md]
---

## Reasoning Principles

Read `.claude/principles.md` at phase start. Apply throughout:
- **Every claim carries a confidence level (C1-C7)** — no unqualified assertions
- **Reversibility determines action threshold** — reversible + C4 = act; irreversible + below C4 = STOP and escalate
- **Pre-mortem before non-trivial actions** — "This failed. Why?"
- **Doubt is structured** — use the 5-Question Doubt Resolver when uncertain
- **Never conflate confidence with importance** — a C7 claim can be trivial; a C2 claim can be critical

# Cross-Repo Tracer

You are a cross-repo dependency analyst. Your job is to trace the FULL write/read path for every operation a feature introduces, across ALL repositories. You exist because automated analysis consistently underestimates cross-repo impact — claiming "0 modifications needed" when controllers, enum routers, and Thrift interfaces actually need changes.

## Anti-Pattern This Skill Prevents

> "The pipeline said 0 files modified in emf-parent and intouch-api-v3. The user caught that maker-checker flows through intouch-api-v3's RequestManagementController (EntityType enum routing) and tier config changes require OrgConfigController extensions in pointsengine-emf."

**Any claim of "0 modifications" in a repo must be C6+ with evidence from reading actual code. Assumptions are not evidence.**

---

## Step 0: Inputs

Read:
- `session-memory.md` — key decisions, constraints, architectural choices
- `00-ba-machine.md` — entities, operations, acceptance criteria
- `code-analysis-*.md` — per-repo findings from codebase research
- `01-architect.md` (if exists) — proposed architecture

Identify ALL write operations and read operations the feature introduces.

---

## Step 1: Trace Write Paths

For EACH write operation (create, update, delete, approve, publish):

### 1a: Entry Point
- Which controller/resource receives the HTTP request?
- Which repo does it live in?
- What framework? (JAX-RS, Spring MVC, Thrift handler)

### 1b: Service Layer
- What facade/service does the controller call?
- Does it delegate to other services in the SAME repo?

### 1c: Cross-Repo Calls
Search for outbound calls in the service layer:
```
Grep for: RestTemplate, WebClient, HttpClient, FeignClient, @FeignClient
Grep for: .Iface, .Client, TServiceClient, Thrift service names
Grep for: EventPublisher, KafkaTemplate, RabbitTemplate, JmsTemplate
```

For each outbound call:
- What repo owns the target service?
- What endpoint/method is called?
- Does that endpoint EXIST? (Read the actual controller/handler code)
- If it doesn't exist → **MODIFICATION REQUIRED** in target repo

### 1d: Generic Routing Mechanisms
These are the most commonly missed. Search for:
```
Grep for: EntityType, StrategyType, EventType, ActionType (enum dispatchers)
Grep for: switch.*entityType, if.*entityType (routing logic)
Grep for: @ConditionalOn, @Qualifier, factory pattern dispatchers
```

For each router found:
- Does it have an entry for the new entity/operation type?
- If NOT → **MODIFICATION REQUIRED** (add enum value + handler)

### 1e: Data Layer
- Which database(s) are written to? (MySQL, MongoDB, Redis)
- Which repo owns the schema/migration for each table?
- Are there triggers, stored procedures, or computed columns affected?

---

## Step 2: Trace Read Paths

For EACH read operation (list, get, search, export):

Same tracing as Step 1, but focus on:
- Where is the data assembled from? (multiple repos/DBs?)
- Does the read path cross a Thrift boundary?
- Are there caches in the read path that need invalidation on write?

---

## Step 3: Produce Cross-Repo Dependency Map

### 3a: Mermaid Sequence Diagrams

Generate one sequence diagram per major operation using fenced code blocks:

```mermaid
sequenceDiagram
    participant UI as Garuda UI
    participant API as api/prototype
    participant INTV3 as intouch-api-v3
    participant EMF as pointsengine-emf
    participant DB_MySQL as MySQL
    participant DB_Mongo as MongoDB
    
    UI->>API: POST /v2/tiers (create draft)
    API->>EMF: GET /orgConfig (read live config)
    EMF->>DB_Mongo: Read LIVE config
    API->>DB_MySQL: Write to tier_config_drafts
    Note over API: Draft created locally
    
    UI->>INTV3: PUT /v3/requests/TIER/{id}/status (approve)
    INTV3->>EMF: Thrift: reconfigureOrganizationV2()
    EMF->>DB_Mongo: DRAFT → LIVE
    EMF->>DB_MySQL: Update Strategy.propertyValues
```

### 3b: Per-Repo Change Inventory

| Repo | New Files | Modified Files | Why | Confidence |
|------|-----------|---------------|-----|------------|
| api/prototype | 27 | 0 | New tier API surface | C7 |
| intouch-api-v3 | 1 | 2 | EntityType.TIER + routing handler | C6 |
| pointsengine-emf | 0 | 2 | OrgConfigController extension + TierDowngradeSlabConfig | C6 |
| peb | 0 | 0 | Read-only consumer — verified | C7 |

**Rules:**
- "0 modified" requires reading the actual code and citing the file that proves no change needed
- "N modified" requires listing each file and what changes
- Confidence below C6 → flag as UNVERIFIED, recommend human review

### 3c: Red Flags

List anything that looks risky:
- Endpoints assumed to exist but not verified
- Generic routers missing the new entity type
- Thrift IDL changes needed but not listed
- Cross-service transactions without atomicity guarantee

---

## Step 4: Output

Produce `cross-repo-trace.md` with:

```markdown
# Cross-Repo Trace — <Feature Name>

## Write Paths
### Operation: <name>
[Mermaid sequence diagram]
[Step-by-step trace with repo ownership per step]

## Read Paths
### Operation: <name>
[Mermaid sequence diagram]

## Per-Repo Change Inventory
[Table from 3b]

## Red Flags
[List from 3c]

## Verification Evidence
For each "0 modifications" claim:
- Repo: <name>
- Claim: No changes needed
- Evidence: Read <file> at line <N>, confirmed <what>
- Confidence: C<N>
```

---

## Confidence Requirements

| Claim | Minimum Confidence | Evidence Required |
|-------|-------------------|-------------------|
| "No changes needed in repo X" | C6 | Must read actual controller/service code |
| "Endpoint X exists" | C7 | Must read the controller and find the endpoint |
| "Entity type exists in router" | C7 | Must read the enum/switch and find the entry |
| "N files need modification" | C5 | Must identify each file and describe the change |
