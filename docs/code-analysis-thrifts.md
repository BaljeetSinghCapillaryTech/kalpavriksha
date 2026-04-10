# Code Analysis -- thrifts

> Phase: 5 (Codebase Research)
> Repo: /Users/baljeetsingh/IdeaProjects/thrifts
> Role: Thrift IDL definitions -- defines the contract between intouch-api-v3 and emf-parent

---

## Key Findings

1. **Two Thrift interfaces relevant to partner programs**:
   - `PointsEngineRuleService.Iface` (thrift-ifaces-pointsengine-rules/pointsengine_rules.thrift) -- PROGRAM CONFIG
   - `EMFService.Iface` (thrift-ifaces-emf/emf.thrift) -- ENROLLMENT EVENTS

2. **Only PointsEngineRuleService is in scope** (per KD-16: enrollment out of scope).

3. **PartnerProgramInfo struct** (pointsengine_rules.thrift:402-417):
   - partnerProgramId (i32)
   - partnerProgramName (string)
   - description (string)
   - isTierBased (bool)
   - partnerProgramTiers (list<PartnerProgramTierInfo>, optional)
   - programToPartnerProgramPointsRatio (double)
   - partnerProgramUniqueIdentifier (string, optional)
   - partnerProgramType (EXTERNAL/SUPPLEMENTARY)
   - partnerProgramMembershipCycle (cycleType: DAYS/MONTHS + cycleValue: int, optional)
   - isSyncWithLoyaltyTierOnDowngrade (bool)
   - loyaltySyncTiers (map<i32, list<i32>>, optional)
   - updatedViaNewUI (bool, optional)
   - expiryDate (i64, optional)
   - backupProgramId (i32, optional)

4. **ExpiryReminderForPartnerProgramInfo** (pointsengine_rules.thrift:419-425):
   - partnerProgramId (i32)
   - partnerProgramName (string)
   - daysBeforeExpiryReminder (list<i32>)
   - communicationPropertyValues (map<string, string>, optional)

5. **No Thrift IDL changes needed.** All structs and methods exist. The subscription feature calls existing methods.

---

## Verification: "0 Modifications" Claim

**Claim**: thrifts repo requires 0 file modifications.

**Evidence**:
- createOrUpdatePartnerProgram method signature verified at pointsengine_rules.thrift:1269
- PartnerProgramInfo struct has all fields needed for subscription activation
- ExpiryReminderForPartnerProgramInfo supports reminder config
- getAllPartnerPrograms at line 1263 supports read-back
- No new structs, no new methods, no new services needed

**Confidence**: C7 (read actual Thrift IDL files)

---

## Per-Repo Change Inventory

| New Files | Modified Files | Why | Confidence |
|-----------|---------------|-----|------------|
| 0 | 0 | All needed Thrift structs and methods already exist | C7 |
