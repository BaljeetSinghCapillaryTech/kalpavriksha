# Warnings for Simulation

## DO NOT
- DO NOT modify existing tier evaluation logic in PEB -- simulation should READ member data and COMPUTE projections, not change how evaluations work
- DO NOT modify tier downgrade calculators -- they are runtime logic
- DO NOT start code implementation before Tier Category CRUD APIs are available

## DEPENDENCIES
- Tier Category epic (Ritwik) must have basic GET /tiers API available before simulation can read current tier config
- PEB member distribution data must be accessible (verify data access path during BA phase)
- AIRA integration patterns need to be defined during BA phase

## BEFORE MERGING
- Verify simulation does NOT modify any live data (read-only + compute)
- Verify PII masking works correctly for non-admin roles
- Performance: simulation on large member bases may need async processing
