# Session Memory

> Artifacts path: docs/pipeline/
> Workflow started: Phase 0 / 2026-04-06
> Feature: tier-crud
> Ticket: test_branch_v3

---

## Domain Terminology
_Populated by BA from product docs and requirements. Use these terms consistently across all phases._

## Codebase Behaviour
_What was found in the codebase and docs, and how it behaves/is set up. Updated by each phase._

## Key Decisions
_Significant decisions and their rationale. Format: `- [decision]: [rationale] _(phase)_`_

## Constraints
_Technical, business, and regulatory constraints all phases must respect. Format: `- [constraint] _(phase)_`_
- LSP available: using jdtls for code traversal _(Phase 0)_
- Code repos: emf-parent (multi-module Maven), intouch-api-v3 (Spring MVC REST gateway) _(Phase 0)_
- No UI screenshots provided — no UI extraction phase needed _(Phase 0)_
- BRD covers 4 epics: E1 Tier Intelligence, E2 Benefits as Product, E3 aiRa Config Layer, E4 API-First Contract _(Phase 0)_
- Feature name is "tier-crud" — suggests focus on tier CRUD operations (E1 + E4 scope) _(Phase 0)_

## Risks & Concerns
_Flagged risks and concerns. Format: `- [risk] _(phase)_ — Status: open/mitigated`_
- BRD has 6 open questions in Section 12 (all status: Open) — must be resolved during BA phase _(Phase 0)_ — Status: open

## Open Questions
_Unresolved questions. Format: `- [ ] [question] _(phase)_` or `- [x] resolved: answer _(phase)_`_
- [ ] Feature named "tier-crud" but BRD covers all 4 epics (E1-E4). Is this pipeline scoped to ALL epics or just tier CRUD (E1+E4)? _(Phase 0)_
- [ ] Does the program context API exist or need to be built? (BRD Section 12, Q1) _(Phase 0)_
- [ ] Is impact simulation real-time or queued? What is SLA? (BRD Section 12, Q2) _(Phase 0)_
- [ ] Maker-checker: per-user-role or per-program? Who configures approvers? (BRD Section 12, Q3) _(Phase 0)_
- [ ] Can a benefit be linked to multiple programs or scoped to one? (BRD Section 12, Q4) _(Phase 0)_
- [ ] Should aiRa handle multi-turn disambiguation? (BRD Section 12, Q5) _(Phase 0)_
- [ ] Is "validate on return transaction" toggle surfaced in new UI or deprecated? (BRD Section 12, Q6) _(Phase 0)_

## Rework Log
_Tracks re-run cycles to detect unresolved loops._
