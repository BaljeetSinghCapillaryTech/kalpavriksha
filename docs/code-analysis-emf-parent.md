# Code Analysis -- emf-parent

> Phase: 5 (Codebase Research)
> Repo: /Users/baljeetsingh/IdeaProjects/emf-parent
> Role: Thrift server -- receives createOrUpdatePartnerProgram calls from intouch-api-v3

---

## Key Architectural Insights

1. **emf-parent is the Thrift SERVER.** It receives calls from intouch-api-v3 (the client). The subscription feature does NOT modify emf-parent code -- it only CALLS existing Thrift methods.

2. **createOrUpdatePartnerProgram is fully implemented.** Located in PointsEngineRuleConfigThriftImpl (line 252). It:
   - Gets existing partner program slabs
   - Converts PartnerProgramInfo (Thrift struct) to PartnerProgram entity
   - Calls PointsEngineRuleEditorImpl.createOrUpdatePartnerProgram() to persist
   - Logs audit trails
   - Returns the PartnerProgramInfo with assigned partnerProgramId

3. **PartnerProgram entity** in emf-parent maps to MySQL `partner_programs` table. Fields: id, orgId, loyaltyProgramId, partnerProgramIdentifier, name, type (EXTERNAL/SUPPLEMENTARY), description, isActive, isTierBased, pointsExchangeRatio, expiryDate, backupPartnerProgramId, createdOn.

4. **No changes needed in emf-parent.** The existing Thrift method handles all cases: create new (id=0) and update existing (id>0). The subscription feature only calls this from the v3 API side.

---

## Entities Found

| Entity | Location | Relevance |
|--------|----------|-----------|
| PartnerProgram | points.entity.PartnerProgram | MySQL entity written by createOrUpdatePartnerProgram. NO CHANGES. |
| PartnerProgramSlab | points.entity.PartnerProgramSlab | Tier-based subscription slabs. NO CHANGES. |
| PartnerProgramEnrollment | (enrollment package) | Enrollment records. OUT OF SCOPE (KD-16). |
| PartnerProgramTierSyncConfiguration | points.entity.PartnerProgramTierSyncConfiguration | Tier sync config. NO CHANGES. |
| PartnerProgramCycle | points.entity.PartnerProgramCycle | Membership cycle config. NO CHANGES. |

---

## Services Found

| Service | Location | Relevance |
|---------|----------|-----------|
| PointsEngineRuleConfigThriftImpl | endpoint.impl.external | Server-side Thrift handler. Has createOrUpdatePartnerProgram. NO CHANGES. |
| PointsEngineRuleEditorImpl | endpoint.impl.editor | Business logic for partner program CRUD. NO CHANGES. |
| PePartnerProgramDao | points.dao | MySQL DAO for partner_programs table. NO CHANGES. |
| PartnerProgramImpl | impl.base | PartnerProgram business logic impl. NO CHANGES. |

---

## Verification: "0 Modifications" Claim

**Claim**: emf-parent requires 0 file modifications.

**Evidence**:
- `createOrUpdatePartnerProgram` already exists and is fully functional (PointsEngineRuleConfigThriftImpl.java:252)
- The method accepts a PartnerProgramInfo struct which maps 1:1 to what the subscription feature needs
- The `updatedViaNewUI` flag in PartnerProgramInfo is already supported (line 265-266)
- getAllPartnerPrograms already exists for read-back verification
- createOrUpdateExpiryReminderForPartnerProgram already exists for reminder config
- Enrollment methods (link/delink/update) are OUT OF SCOPE (KD-16)
- No new entity types, no new Thrift methods, no new tables needed

**Confidence**: C7 (read actual Thrift handler code, traced full call path from PartnerProgramInfo to MySQL persistence)

---

## Per-Repo Change Inventory

| New Files | Modified Files | Why | Confidence |
|-----------|---------------|-----|------------|
| 0 | 0 | Existing Thrift methods sufficient. Only called FROM intouch-api-v3. | C7 |
