# Epic: Simulation
Owner: Baljeet
Layer: 3 (starts after Tier Category CRUD is complete)

## What this epic covers

Simulation Mode -- test proposed tier configuration changes against the current
member base before publishing. AIRA-based (AI/analytics integration).

### User Stories (from BRD E1-US6)
- As Maya, I want to test a proposed tier config change against my current member base
- Simulation inputs: proposed changes to any tier config dimension
- Simulation output: member distribution forecast (before and after)
- Visualization: bar chart showing current vs projected distribution per tier
- Drill-down: export list of affected member IDs (PII masked for non-admin)

## Shared modules
- **BUILDS**: none
- **CONSUMES**: none (reads tier config from Tier Category APIs, reads member data from PEB)

## Dependencies
- Tier Category epic must be complete (needs tier CRUD APIs to have config to simulate against)
- AIRA platform integration (AI/analytics)
- PEB (Points Engine Backend) member distribution data access

## Build order
1. BA/PRD: Define simulation algorithm scope, AIRA integration patterns
2. Simulation engine: Accept proposed config, compute member distribution delta
3. PEB integration: Read current member distribution per tier
4. REST API: POST /tiers/{tierId}/simulate
5. Export: Affected member list with PII masking
6. Tests

## Code locations
- Core: `emf-parent/pointsengine-emf/` (simulation engine)
- PEB: `/Users/ritwikranjan/Desktop/emf-parent/peb/` (member data, tier evaluation logic)
  - Reference: TierDowngradeHandler, tier downgrade calculators
  - Reference: TierReassessmentData
- API: `intouch-api-v3/` or emf-parent REST layer

## NOTE
This is a Layer 3 epic. Start the BA phase when ready, but do not begin code
implementation until Tier Category (Ritwik) has merged basic tier CRUD APIs.
