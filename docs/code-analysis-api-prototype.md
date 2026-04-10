# Code Analysis -- api/prototype

> Phase: 5 (Codebase Research)
> Repo: /Users/baljeetsingh/IdeaProjects/api/prototype
> Role: Customer-facing REST APIs (JAX-RS), Extended Fields mechanism

---

## Key Findings

1. **ExtendedField.EntityType enum** (ExtendedField.java:70-87): Currently has 13 values: CUSTOMER, REGULAR_TRANSACTION, RETURN_TRANSACTION, NOT_INTERESTED_TRANSACTION, NOT_INTERESTED_RETURN_TRANSACTION, REGULAR_LINEITEM, RETURN_LINEITEM, NOT_INTERESTED_LINEITEM, NOT_INTERESTED_RETURN_LINEITEM, LEAD, COMPANY, CARD, USERGROUP2. **No PARTNER_PROGRAM type exists.**

2. **KD-06 requires adding PARTNER_PROGRAM to ExtendedField.EntityType** to support subscription pricing via extended fields. Each EntityType maps to a MongoDB collection name (e.g., CUSTOMER -> "customer_extended_fields"). PARTNER_PROGRAM would map to "partner_program_extended_fields".

3. **However, this is a DEFERRED change.** For this pipeline run, benefit linking uses dummy IDs (KD-08) and pricing is stored as a document field in MongoDB (price.amount, price.currency). The Extended Fields integration (KD-06) is for a future run when real pricing is needed at the enrollment level.

4. **SubscriptionV2Facade** handles COMMUNICATION subscriptions (email/SMS opt-in), NOT partner program subscriptions. Completely different domain. No overlap.

---

## Verification: "0 Modifications" Claim

**Claim**: api/prototype requires 0 file modifications in THIS pipeline run.

**Evidence**:
- ExtendedField.EntityType addition (PARTNER_PROGRAM) was listed in 00-ba-machine.md BUT:
  - KD-06 says pricing uses extended fields mechanism
  - The actual extended field addition is only needed when enrollment-time pricing enforcement is built
  - For this run, price is stored directly in the MongoDB subscription document
  - ExtendedField creation is an api/prototype change that can be done independently
- No other files in api/prototype are affected by subscription CRUD
- SubscriptionV2Facade is communication subscriptions -- no overlap

**Note**: The 00-ba-machine.md listed "Add PARTNER_PROGRAM value" for api/prototype. This is still CORRECT as a future need (KD-06), but NOT needed for this pipeline run's scope. The subscription document stores price directly.

**Confidence**: C6 (verified ExtendedField enum doesn't have it; confirmed pricing is in MongoDB doc for this run)

---

## Per-Repo Change Inventory

| New Files | Modified Files | Why | Confidence |
|-----------|---------------|-----|------------|
| 0 | 0 | Extended field entity type addition deferred to future run. Price stored in MongoDB doc. | C6 |
