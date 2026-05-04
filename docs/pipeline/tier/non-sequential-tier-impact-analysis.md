# Impact Analysis: Non-Sequential Tier Serial Numbers

> **Date:** 2026-04-14
> **Scope:** emf-parent (pointsengine) + peb (Points Engine Backend)
> **Change Under Analysis:** Allow tier `serial_number` values to be non-contiguous (e.g., 1, 2, 4 instead of 1, 2, 3) while keeping the same number of strategies mapped positionally.
> **Confidence:** C7 (Near Certain) -- verified by reading production source code across both repos.
> **Verdict:** **UNSAFE without code changes.** ~50 call sites across 15 production files will break.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Root Cause: The Architectural Assumption](#2-root-cause-the-architectural-assumption)
3. [emf-parent Breakage Analysis](#3-emf-parent-breakage-analysis)
   - 3.1 [PointAllocationStrategyImpl -- Point Earning Rate](#31-pointallocationstrategyimpl----point-earning-rate)
   - 3.2 [SlabUpgradeStrategyImpl -- Upgrade Threshold Check](#32-slabupgradestrategyimpl----upgrade-threshold-check)
   - 3.3 [PointsMaximizerImpl -- Transaction Point Optimization](#33-pointsmaximizerimpl----transaction-point-optimization)
   - 3.4 [PointsReturnService -- Refund Downgrade Check](#34-pointsreturnservice----refund-downgrade-check)
   - 3.5 [ThresholdBasedSlabUpgradeStrategyImpl -- Upgrade Notifications](#35-thresholdbasedslabupgradestrategyimpl----upgrade-notifications)
   - 3.6 [PointExpiryStrategyImpl -- Point Expiry Dates](#36-pointexpirystrategyimpl----point-expiry-dates)
   - 3.7 [PointRedemptionThresholdStrategyImpl -- Redemption Rules](#37-pointredemptionthresholdstrategyimpl----redemption-rules)
   - 3.8 [UnifiedCalculationEngine -- Unified Earn Calculation](#38-unifiedcalculationengine----unified-earn-calculation)
   - 3.9 [SlabUpgradeInstructionExecutor -- Previous Slab Lookup](#39-slabupgradeinstructionexecutor----previous-slab-lookup)
   - 3.10 [ProgramImpl / PointsEngineEndpointPropertiesImpl -- Next Slab Navigation](#310-programimpl--pointsengineendpointpropertiesimpl----next-slab-navigation)
4. [peb Breakage Analysis](#4-peb-breakage-analysis)
   - 4.1 [SlabUpgradeStrategy -- Threshold Access](#41-slabupgradestrategy----threshold-access)
   - 4.2 [PointsAllocationStrategy -- Point Allocation](#42-pointsallocationstrategy----point-allocation)
   - 4.3 [PointsExpiryStrategy -- Expiry Dates](#43-pointsexpirystrategy----expiry-dates)
   - 4.4 [PointsAndExpiryDateCalculatorImpl -- Bulk Allocation Min/Max](#44-pointsandexpirydatecalculatorimpl----bulk-allocation-minmax)
   - 4.5 [SingleTierDowngradeCalculator -- Wrong Downgrade Target](#45-singletierdowngradecalculator----wrong-downgrade-target)
   - 4.6 [AllocationServiceHelper -- Bulk Upgrade SQL](#46-allocationservicehelper----bulk-upgrade-sql)
   - 4.7 [GapToUpgrade Calculators (5 classes)](#47-gaptoupgrade-calculators-5-classes)
   - 4.8 [BulkRequestHandler -- Next Slab Check](#48-bulkrequesthandler----next-slab-check)
5. [Full Call Chain Traces (Entry Point to Breakage)](#5-full-call-chain-traces)
6. [SQL Queries Affected](#6-sql-queries-affected)
7. [Thrift / RPC Boundaries](#7-thrift--rpc-boundaries)
8. [Configuration and JSON Parsing](#8-configuration-and-json-parsing)
9. [Tests That Assume Sequential Numbering](#9-tests-that-assume-sequential-numbering)
10. [Safe Areas (No Change Required)](#10-safe-areas)
11. [Summary: Every Affected User Flow](#11-summary-every-affected-user-flow)
12. [Master Breakage Table](#12-master-breakage-table)
13. [Fix Approach](#13-fix-approach)

---

## 1. Executive Summary

The loyalty platform stores tier strategies (upgrade thresholds, point allocation rates, expiry configs, redemption rules, notification templates) as **comma-separated values** in the database. These CSV strings are parsed into `ArrayList` objects at runtime.

**The fundamental problem:** Every access to these lists uses `serialNumber - 1` (or `serialNumber - 2`) as the array index. This only works when tier serial numbers form a contiguous 1-based sequence (1, 2, 3, ..., N).

If tier serial numbers become non-sequential (e.g., 1, 2, 4):
- **Tier 4** would compute index `4 - 1 = 3`
- **But the list only has 3 entries** (indices 0, 1, 2)
- Result: `IndexOutOfBoundsException` on every affected flow

This pattern is embedded in **15 production Java files** across **~50 call sites** in both `emf-parent` and `peb`, affecting **every core loyalty flow**: point earning, redemption, expiry, tier upgrade, tier downgrade, points maximization, return/refund processing, and upgrade notifications.

---

## 2. Root Cause: The Architectural Assumption

### How It Works Today

```
DB: program_slabs table
+----+---------------+------+
| id | serial_number | name |
+----+---------------+------+
|  1 |             1 | Base |
|  2 |             2 | Silver |
|  3 |             3 | Gold |
+----+---------------+------+

Strategy CSV: "10,20,30" (allocation rates per slab)
Parsed into: ArrayList [10, 20, 30]  (indices 0, 1, 2)

Access pattern: list.get(serialNumber - 1)
  Slab 1 -> list.get(0) = 10  OK
  Slab 2 -> list.get(1) = 20  OK
  Slab 3 -> list.get(2) = 30  OK
```

### What Breaks With Non-Sequential (1, 2, 4)

```
DB: program_slabs table
+----+---------------+------+
| id | serial_number | name |
+----+---------------+------+
|  1 |             1 | Base |
|  2 |             2 | Silver |
|  4 |             4 | Gold |
+----+---------------+------+

Strategy CSV: "10,20,30" (still 3 values for 3 slabs)
Parsed into: ArrayList [10, 20, 30]  (indices 0, 1, 2)

Access pattern: list.get(serialNumber - 1)
  Slab 1 -> list.get(0) = 10  OK
  Slab 2 -> list.get(1) = 20  OK
  Slab 4 -> list.get(3) = ???  IndexOutOfBoundsException!
```

### The Two Conflated Concepts

| Concept | Description | Example (1,2,4) |
|---------|-------------|------------------|
| **Tier Serial Number** | The identifier assigned to a tier in the DB | 1, 2, 4 |
| **Positional Index** | The 0-based position in the CSV/ArrayList | 0, 1, 2 |

The codebase assumes `serial_number = positional_index + 1`, which only holds when serials are contiguous starting at 1.

---

## 3. emf-parent Breakage Analysis

**Repo path:** `/Users/ritwikranjan/Desktop/Artificial Intelligence/emf-parent`
**Module:** `pointsengine-emf`

### 3.1 PointAllocationStrategyImpl -- Point Earning Rate

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/strategy/PointAllocationStrategyImpl.java`

**User-facing flow:** Determines how many points to award per rupee of spend for a given tier. Called on **every transaction**.

#### Constructor -- CSV Parsing (Lines 117-138)

```java
valuesList = new ArrayList<BigDecimal>();
if (this.propertiesMap.containsKey("allocation_values")) {
    String allocationValuesCsv = (String) this.propertiesMap.get("allocation_values");
    for (String s : StringUtils.split(allocationValuesCsv, ',')) {
        valuesList.add(toBigDecimal(s));
    }
}
if (valuesList.size() != numSlabsInProgram && !(fromJson.allocation_type.equals("ROUND_UP"))) {
    throw new ParseConfigException("PointAllocationStrategy " + getName()
        + " : allocation_values must have " + numSlabsInProgram + " values. Provided : "
        + valuesList.size(), null);
}
```

Validation uses `numSlabsInProgram` (count of slabs), not serial numbers. **Validation is safe.**

#### Broken Access Methods (Lines 297-303)

```java
@Override
public BigDecimal getValue(Slab s) {
    return valuesList.get(s.getSerialNumber() - 1);  // Line 298
}

@Override
public BigDecimal getValue(int slabSerial) {
    return valuesList.get(slabSerial - 1);            // Line 303
}
```

| Slab Serial | Index Computed | List Size | Result |
|------------|---------------|-----------|--------|
| 1 | 0 | 3 | OK |
| 2 | 1 | 3 | OK |
| 4 | **3** | 3 | **IndexOutOfBoundsException** |

**Failure mode:** `IndexOutOfBoundsException` -- customers in the highest tier cannot earn points.

---

### 3.2 SlabUpgradeStrategyImpl -- Upgrade Threshold Check

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/strategy/SlabUpgradeStrategyImpl.java`

**User-facing flow:** Determines (a) how many points remain before a customer upgrades, and (b) which tier a customer should be in based on cumulative value.

#### 3.2.1 findValueAllowedBeforeSlabUpgrade (Line 372)

```java
public BigDecimal findValueAllowedBeforeSlabUpgrade(Payload payload, Slab currentSlab,
        UpgradeCriteria upgradeCriteria, EvaluatedEntity evaluatedEntity) {
    // ... gets currentValue based on type ...

    /*
     * If there are 3 slabs S1,S2,S3 and the thresholds are 5000 for S1->S2 and 10000 S2->S3
     * Then the current slab's serial number will give the threshold for it
     */
    int thresholdForCurrentSlab = upgradeCriteria.getThresholds()
        .get(currentSlab.getSerialNumber() - 1);  // <-- BREAKS
}
```

**Note the code comment itself documents the sequential assumption:** *"the current slab's serial number will give the threshold for it"* -- only true when serials are sequential.

Thresholds list has `numSlabs - 1` entries (2 entries for 3 slabs). Slab 4: `get(3)` on a 2-element list.

**Failure mode:** `IndexOutOfBoundsException` -- dynamic slab upgrade logic crashes.

#### 3.2.2 getSlabForEagerOrLazy (Lines 428-448)

```java
public Slab getSlabForEagerOrLazy(Payload payload, UpgradeCriteria upgradeCriteria,
        EvaluatedEntity evaluatedEntity) {
    BigDecimal currentValue = getCurrentValueForUpgradeType(...);
    List<Integer> thresholds = upgradeCriteria.getThresholds();
    Slab toSlab = getInitialToSlab(payload, evaluatedEntity);
    for (int i = thresholds.size() - 1; i >= 0; i--) {
        if (isGreaterThanEqual(currentValue, toBigDecimal(thresholds.get(i)))) {
            // If there are 3 slabs, there will be 2 thresholds
            // with index 0,1. Slab serial will be 1,2,3
            toSlab = m_pointsProgramConfig.getSlabByNumber(i + 2);  // <-- BREAKS
            break;
        }
    }
    return toSlab;
}
```

The `i + 2` formula maps threshold index to slab serial: index 0 -> slab 2, index 1 -> slab 3. With tiers (1,2,4), there is no slab 3.

`getSlabBySerial(3)` does a linear scan and returns **null**. The null propagates downstream causing `NullPointerException`.

**Failure mode:** `NullPointerException` -- eager/lazy tier upgrade evaluation crashes.

---

### 3.3 PointsMaximizerImpl -- Transaction Point Optimization

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/config/PointsMaximizerImpl.java`

**User-facing flow:** Reorders line items within a single transaction to maximize points when a dynamic slab upgrade is possible mid-transaction (e.g., a customer hits Gold tier partway through a bill).

#### Threshold Delta Preparation (Lines 417-424)

```java
List<BigDecimal> thresholds = new ArrayList<>();
for (Integer threshold : thresholdList) {
    thresholds.add(toBigDecimal(threshold));
}
for (int i = thresholds.size() - 1; i > 0; i--) {
    thresholds.set(i, thresholds.get(i).subtract(thresholds.get(i-1)));
}
```

Converts cumulative thresholds to incremental deltas. Thresholds list has `numSlabs - 1` entries.

#### Core Recursion -- 8 Broken Call Sites (Lines 484-559)

```java
// Line 434: Initial call with slab.getSerialNumber()
findAllocationOrder(lineItemAmounts, thresholds, ..., l, slab.getSerialNumber(), ...);

// Line 484: Compare threshold to line item
if (isGreaterThanEqual(thresholds.get(currentSlabSerial-1), lineItems.get(l % lineItems.size()))) {

// Line 519: Reduce remaining threshold
thresholds.set(currentSlabSerial - 1, subtract(thresholds.get(currentSlabSerial - 1), t));

// Line 523: Check if threshold depleted
int st = isEqual(thresholds.get(currentSlabSerial - 1), ...) ? currentSlabSerial + 1 : currentSlabSerial;

// Line 539: Restore threshold (backtrack)
thresholds.set(currentSlabSerial - 1, add(thresholds.get(currentSlabSerial - 1), t));

// Lines 546-547: Alternate path
BigDecimal t = min(thresholds.get(currentSlabSerial - 1), billValue);
thresholds.set(currentSlabSerial - 1, subtract(thresholds.get(currentSlabSerial - 1), t));

// Line 555: Recursive call to NEXT slab -- assumes contiguous serials!
findAllocationOrder(lineItems, thresholds, ..., l, currentSlabSerial + 1, ...);

// Line 559: Restore on backtrack
thresholds.set(currentSlabSerial - 1, add(t, thresholds.get(currentSlabSerial - 1)));
```

**Two distinct bugs:**
1. `thresholds.get(currentSlabSerial - 1)` -- uses serial as index. Slab 4 -> `get(3)` -> `IndexOutOfBoundsException`.
2. `currentSlabSerial + 1` at line 555 -- assumes the next slab after 2 is 3. But with tiers (1,2,4), the next slab is 4 (not 3). Serial 3 has no threshold entry, causing another `IndexOutOfBoundsException` in the recursive call.

**Failure mode:** `IndexOutOfBoundsException` -- points maximization crashes, potentially blocking the entire transaction.

---

### 3.4 PointsReturnService -- Refund Downgrade Check

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/points/services/PointsReturnService.java`

**User-facing flow:** After a return/refund, checks whether the customer's cumulative value has dropped below the upgrade threshold, triggering a tier downgrade.

#### isCustomerToBeDowngraded (Lines 1087-1124)

```java
protected boolean isCustomerToBeDowngraded(Program program, ProgramSlab slab,
        Strategy upgradeStrategy, LoyaltyEntity loyaltyEntity,
        BigDecimal returnAmount, BigDecimal currentPoints, BigDecimal lifetimePoints) {

    if (slab.getSerialNumber() == 1) {
        return false;  // Can't downgrade from base slab -- SAFE
    }

    // ... builds upgrade strategy and criteria list ...

    for (UpgradeCriteria uc : upgradeCriteriaList) {
        BigDecimal currentValue = BigDecimal.ZERO;
        // ... switch on currentValueType ...

        int thresholdForPreviousSlab = uc.getThresholds()
            .get(slab.getSerialNumber() - 2);  // Line 1117 -- BREAKS
        BigDecimal allowed = subtract(toBigDecimal(thresholdForPreviousSlab), currentValue);
        shouldDowngrade &= isGreaterThan(allowed, BigDecimal.ZERO);
    }
    return shouldDowngrade;
}
```

**Why `-2`:** The thresholds list has N-1 entries for N slabs. `threshold[0]` = boundary for slab 1->2, `threshold[1]` = boundary for slab 2->3. To get the threshold that qualified a customer for their current slab, the formula is `threshold[serialNumber - 2]`. For slab 3: `threshold[1]` = the 2->3 boundary. Correct for sequential.

**With non-sequential (1,2,4):** Slab 4 -> `threshold[4-2]` = `threshold[2]`. But there are only 2 thresholds (indices 0,1).

**Failure mode:** `IndexOutOfBoundsException` -- return/refund processing crashes, potentially blocking refunds for top-tier customers.

---

### 3.5 ThresholdBasedSlabUpgradeStrategyImpl -- Upgrade Notifications

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/strategy/ThresholdBasedSlabUpgradeStrategyImpl.java`

**User-facing flow:** SMS/email/push notification templates sent to customers when they upgrade to a new tier.

#### 3.5.1 List-Based Template Getters (8 methods, Lines 810-901) -- BREAKS

```java
public String getSmsTemplate(Slab slab) {
    return smsTemplateList.get(slab.getSerialNumber() - 2);          // Line 810
}
public String getShortenUrlCheck(Slab slab) {
    return shortenUrlCheckList.get(slab.getSerialNumber() - 2);      // Line 822
}
public String getSmsSenderId(Slab slab) {
    return smsSenderIdList.get(slab.getSerialNumber() - 2);          // Line 841
}
public String getSmsDomain(Slab slab) {
    return smsDomainList.get(slab.getSerialNumber() - 2);            // Line 853
}
public String getSmsCDMASenderId(Slab slab) {
    return smsCDMASenderIdList.get(slab.getSerialNumber() - 2);      // Line 865
}
public String getEmailSenderId(Slab slab) {
    return emailSenderIdList.get(slab.getSerialNumber() - 2);        // Line 877
}
public String getEmailSenderLabel(Slab slab) {
    return emailSenderLabelList.get(slab.getSerialNumber() - 2);     // Line 889
}
public String getEmailDomain(Slab slab) {
    return emailDomainList.get(slab.getSerialNumber() - 2);          // Line 901
}
```

Template lists have `numSlabs - 1` entries (no notification for base slab). Upgrade to slab 4: `get(4-2)` = `get(2)`. Lists have 2 entries (indices 0,1).

**Failure mode:** `IndexOutOfBoundsException` -- upgrade notification sending crashes. Customer doesn't receive SMS/email.

#### 3.5.2 Map-Based Template Getters (11 methods, Lines 919-1043) -- SAFE (but may return null)

```java
// These use Map<Integer, String> keyed by sequential index starting at 2
slabIndexToEmailSubject.get(slab.getSerialNumber());     // Line 919
slabIndexToEmailBody.get(slab.getSerialNumber());        // Line 936
slabIndexTotemplateId.get(slab.getSerialNumber());       // Line 942
// ... 8 more similar methods ...
```

**However**, these maps are populated with sequential keys starting at 2:
```java
int slabIndex = 2;
slabIndexToEmailSubject.put(slabIndex++, emailSubject);   // Keys: 2, 3, 4, ...
```

With tiers (1,2,4), the map would have keys {2, 3} (for 2 upgrade targets). Looking up key `4` returns `null`. No crash, but **missing notification content**.

---

### 3.6 PointExpiryStrategyImpl -- Point Expiry Dates

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/strategy/PointExpiryStrategyImpl.java`

**User-facing flow:** Determines when awarded points expire based on the customer's tier at time of award.

#### Bounds Check That Also Breaks (Lines 231-232)

```java
if (expiryTimeUnits.size() < currentSlab.getSerialNumber()
    || expiryTimeValues.size() < currentSlab.getSerialNumber()) {
    throw new IllegalStateException("Unable to find time unit / value for Slab " + serialNumber);
}
```

With 3 entries and slab serial 4: `3 < 4` = true -> throws `IllegalStateException` before reaching the index access.

#### SLAB_BASED Expiry Access (Lines 248-254)

```java
switch (expiryType) {
    case SLAB_BASED:
        timeUnit = expiryTimeUnits.get(currentSlab.getSerialNumber() - 1);          // Line 248
        if (timeUnit == ExpiryTimeUnit.FIXED_DATE) {
            timeUnitValue = (DateTime) expiryTimeValues.get(currentSlab.getSerialNumber() - 1);   // 250
        } else if (timeUnit == ExpiryTimeUnit.FIXED_DATE_WITHOUT_YEAR) {
            timeUnitValue = (String) expiryTimeValues.get(currentSlab.getSerialNumber() - 1);     // 252
        } else {
            timeUnitValue = (Integer) expiryTimeValues.get(currentSlab.getSerialNumber() - 1);    // 254
        }
        break;
    case SLAB_INDEPENDENT:
        timeUnit = expiryTimeUnits.get(0);  // Always index 0 -- SAFE
```

#### Additional Accessors (Lines 714, 719)

```java
public ExpiryTimeUnit getExpiryTimeUnit(Slab s) {
    return expiryTimeUnits.get(s.getSerialNumber() - 1);      // Line 714
}
public int getExpiryValue(Slab s) {
    return (Integer) expiryTimeValues.get(s.getSerialNumber() - 1);  // Line 719
}
```

**Failure mode:** `IllegalStateException` or `IndexOutOfBoundsException` -- points awarded to top-tier customers have no expiry date, or the flow crashes entirely.

**Note:** `SLAB_INDEPENDENT` mode is **safe** -- always uses index 0.

---

### 3.7 PointRedemptionThresholdStrategyImpl -- Redemption Rules

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/impl/strategy/PointRedemptionThresholdStrategyImpl.java`

**User-facing flow:** Governs minimum/maximum points redeemable and divisibility rules -- all per-tier.

#### Six Broken Getters (Lines 178-203)

```java
public BigDecimal getMinCurrentPoints(Slab s) {
    return this.minCurrentPointsList.get(s.getSerialNumber() - 1);       // Line 178
}
public BigDecimal getMinCumulativePoints(Slab s) {
    return this.minCumulativePointsList.get(s.getSerialNumber() - 1);    // Line 183
}
public BigDecimal getMinCumulativePurchase(Slab s) {
    return this.minCumulativePurchaseList.get(s.getSerialNumber() - 1);  // Line 188
}
public BigDecimal getMinPointsRedeem(Slab s) {
    return this.minPointsRedeemList.get(s.getSerialNumber() - 1);       // Line 193
}
public BigDecimal getMaxPointsRedeem(Slab s) {
    return this.maxPointsRedeemList.get(s.getSerialNumber() - 1);       // Line 198
}
public BigDecimal getRedeemDivisibility(Slab s) {
    return this.redeemDivisibilityList.get(s.getSerialNumber() - 1);    // Line 203
}
```

All 6 lists are validated to have exactly `numSlabsInProgram` entries in the constructor.

**Failure mode:** `IndexOutOfBoundsException` -- point redemption blocked for top-tier customers.

---

### 3.8 UnifiedCalculationEngine -- Unified Earn Calculation

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/calculation/UnifiedCalculationEngine.java`

```java
protected static BigDecimal resolveSlabValueOrDefault(List<BigDecimal> slabValues, int slabSerial) {
    if (slabValues != null && slabSerial > 0 && slabSerial <= slabValues.size()) {
        BigDecimal v = slabValues.get(slabSerial - 1);
        return v == null ? BigDecimal.ZERO : v;
    }
    return BigDecimal.ZERO;  // Falls through here for slab 4 with 3-entry list
}
```

Has bounds check -- won't crash. But slab 4 with a 3-entry list: `4 <= 3` is false, so it returns `BigDecimal.ZERO`.

**Failure mode:** **Silent correctness bug** -- top-tier customers earn 0 points instead of their configured rate. No error logged.

---

### 3.9 SlabUpgradeInstructionExecutor -- Previous Slab Lookup

**File:** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/instructions/executors/PointsEngineSlabUpgradeInstructionExecutorImpl.java`

```java
int prevSlabNumber = toSlab.getSerialNumber() - 1;  // Line 144
```

Used as a **slab number** (not list index). Passed to `SlabChangeInfo.setPrevSlabNumber()`. With tiers (1,2,4), upgrading to slab 4 sets `prevSlabNumber = 3`. Slab 3 doesn't exist.

**Failure mode:** Incorrect audit data in slab change history. Downstream code looking up slab 3 gets `null`.

---

### 3.10 ProgramImpl / PointsEngineEndpointPropertiesImpl -- Next Slab Navigation

**File (ProgramImpl):** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/base/ProgramImpl.java` (Line 215)
**File (Properties):** `pointsengine-emf/src/main/java/com/capillary/shopbook/pointsengine/endpoint/impl/config/PointsEngineEndpointPropertiesImpl.java` (Line 458)

```java
public Slab getNextSlab(Slab currentSlab) {
    return this.getSlabBySerial(currentSlab.getSerialNumber() + 1);
}
```

`getSlabBySerial` does a linear scan (safe -- no index math). But `serial + 1` produces 3 for slab 2, and slab 3 doesn't exist. Returns `null`.

**Failure mode:** `null` returned for "next slab" -- callers may `NullPointerException` or silently skip upgrades.

---

## 4. peb Breakage Analysis

**Repo path:** `/Users/ritwikranjan/Desktop/emf-parent/peb`

### 4.1 SlabUpgradeStrategy -- Threshold Access

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/data/model/custom/SlabUpgradeStrategy.java`

#### getThresholdValue (Lines 69-74)

```java
public int getThresholdValue(int fromSlabNumber) {
    if (fromSlabNumber - 1 > m_thresholdValues.size()) {  // Off-by-one: should be >=
        return -1;
    }
    return m_thresholdValues.get(fromSlabNumber - 1);      // Line 73 -- BREAKS
}
```

**Pre-existing bug:** The bounds check uses `>` instead of `>=`. For `fromSlabNumber = 3` and list size 2: `3-1 = 2 > 2` is false, so it falls through to `get(2)` which is also out of bounds.

#### getExpectedSlabNumber (Lines 76-82) -- Pre-existing bug + Sequential Assumption

```java
public int getExpectedSlabNumber(BigDecimal pointsValue) {
    int i = 0;
    while (i < m_thresholdValues.size() || m_thresholdValues.get(i) < pointsValue.doubleValue()) {
        i++;
    }
    return i + 1;  // Returns position-based number, not actual serial
}
```

**Two bugs:** (1) `||` should be `&&` -- as written, it will `IndexOutOfBoundsException` when `i` exceeds list size. (2) Returns `i + 1` which assumes sequential serials. With tiers (1,2,4), the highest tier should return 4, but this returns 3.

---

### 4.2 PointsAllocationStrategy -- Point Allocation

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/data/model/custom/PointsAllocationStrategy.java`

```java
public BigDecimal getPointsValueForSlabNumber(int slabSerial) {
    return m_allocationValues.get(slabSerial - 1);    // Line 138 -- BREAKS
}
```

**Failure mode:** `IndexOutOfBoundsException` during bulk point allocation for top-tier customers.

---

### 4.3 PointsExpiryStrategy -- Expiry Dates

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/data/model/custom/PointsExpiryStrategy.java`

#### getExpiryDate -- SLAB_BASED (Lines 197-203)

```java
case SLAB_BASED:
    timeUnit = m_expiryTimeUnits.get(slabSerialNumber - 1);                      // Line 197
    if (timeUnit == ExpiryTimeUnit.FIXED_DATE) {
        timeUnitValue = (DateTime) m_expiryTimeValues.get(slabSerialNumber - 1);  // Line 199
    } else if (timeUnit == ExpiryTimeUnit.FIXED_DATE_WITHOUT_YEAR) {
        timeUnitValue = (String) m_expiryTimeValues.get(slabSerialNumber - 1);    // Line 201
    } else {
        timeUnitValue = (Integer) m_expiryTimeValues.get(slabSerialNumber - 1);   // Line 203
    }
```

#### getPointsExpiryInfo -- Same pattern (Lines 338-342)

```java
case SLAB_BASED:
    timeUnit = m_expiryTimeUnits.get(slabSerialNumber - 1);                      // Line 338
    // ... same pattern on lines 340, 342
```

**Failure mode:** `IndexOutOfBoundsException` -- point expiry dates cannot be calculated for top-tier customers. `SLAB_INDEPENDENT` mode is **safe** (always index 0).

**Callers:**
- `ExpiryServiceImpl.getExpiryDate()` (line 432) -- during bulk allocation
- `TierDowngradeServiceImpl.getPointExpiryDates()` (line 1223) -- during tier downgrade
- `TierDowngradeServiceImpl.getPointsExpiryInfo()` (line 966) -- during tier downgrade retain-points

---

### 4.4 PointsAndExpiryDateCalculatorImpl -- Bulk Allocation Min/Max

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/system/allocation/PointsAndExpiryDateCalculatorImpl.java`

```java
BigDecimal pointsToAllocate = m_allocationStrategy.getPointsValueForSlabNumber(m_slabNumber);
BigDecimal minPointsToAllocate = m_allocationStrategy.getMinCriteriaValues().get(m_slabNumber - 1);  // Line 207
BigDecimal maxPointsToAllocate = m_allocationStrategy.getMaxCriteriaValues().get(m_slabNumber - 1);  // Line 208
```

**Failure mode:** `IndexOutOfBoundsException` -- min/max allocation criteria lookup crashes for top-tier.

---

### 4.5 SingleTierDowngradeCalculator -- Wrong Downgrade Target

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/system/tierdowngrade/SingleTierDowngradeCalculator.java`

```java
@Override
protected void processFiltersAndSetTargetSlab() {
    int currentSlabNumber = getSlabNumber();
    if (currentSlabNumber == 1) {
        return;  // Can't downgrade from base -- SAFE
    }
    DowngradeFilter filter = m_filterMap.get(currentSlabNumber);  // Map lookup -- SAFE

    if (filter.isAlways()) {
        m_tierDowngradeService.updateTierDowngradeTargetSlab(
            m_tierDowngradeTable, currentSlabNumber, 0,
            BigDecimal.ZERO, BigDecimal.ZERO, baseTrackedValueMap,
            currentSlabNumber - 1, null);  // Line 46 -- BREAKS: target = 4-1 = 3
    } else {
        // Renew or downgrade paths...
        m_tierDowngradeService.updateTierDowngradeTargetSlab(
            ..., currentSlabNumber - 1, null);  // Line 57 -- BREAKS: same
    }
}
```

With tiers (1,2,4), downgrading from slab 4: target = `4 - 1 = 3`. **Slab 3 doesn't exist.** The target slab number 3 is written to the `tier_downgrade` temp table. Downstream code tries to look up `ProgramSlab` with serial 3 and gets `null` or throws.

**Failure mode:** Wrong downgrade target written to DB -- customer may not be downgraded, or downgrade fails entirely.

**Note:** `LowestTierDowngradeCalculator` hardcodes target to `1` (safe). `ThresholdTierDowngradeCalculator` uses a reassessment table (safe).

---

### 4.6 AllocationServiceHelper -- Bulk Upgrade SQL

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/services/helper/AllocationServiceHelper.java`

#### updateTargetSlabNumberInTempTable (Lines 507-523)

```java
for (int i = slabs.size() - 1; i > 0; i--) {
    int threshold = getNextSlabUpgradeThreshold(orgId, programId, i, slabUpgradeStrategy);
    // ...
    int slabId = slabs.get(i).getId();
    String updateTargetSlab = SqlUtil.formatQuery("UPDATE %s"
        + " SET target_slab_number = %s+1, "   // <-- i+1 as slab number
        + " target_slab_id = %s "
        + " WHERE ROUND(%s + points_to_allocate, 3) > %s "
        + " AND target_slab_number < 0 ",
        tempTableName, i, slabId, thresholdCheck, threshold);
}
```

**Two bugs:**
1. `slabs.get(i)` -- uses list index, but `getProgramSlabs()` query has **no ORDER BY**, so the list order is non-deterministic.
2. `target_slab_number = i+1` -- uses list index as slab serial. With tiers (1,2,4), index 2 maps to slab 4 but sets `target_slab_number = 3`.

#### Upgrade Detection SQL (Lines 463-476)

```java
String insertIntoUpgradeHistory = SqlUtil.formatQuery(
    "INSERT INTO customer_slab_upgrade_history ..."
    + " WHERE temp.target_slab_number > temp.slab_number");  // <-- Sequential assumption

String updateCustomerEnrollment = SqlUtil.formatQuery(
    "UPDATE customer_enrollment ce, {tempTable} temp "
    + " SET ce.current_slab_id = temp.target_slab_id ..."
    + " WHERE temp.target_slab_number > temp.slab_number");  // <-- Sequential assumption
```

The SQL `target_slab_number > slab_number` assumes higher serial = higher tier. This is actually **still correct** with non-sequential numbering IF the numbering preserves order (1 < 2 < 4). But combined with bug #2 above (wrong target_slab_number), the comparison gives wrong results.

**Failure mode:** Wrong `target_slab_number` written to temp table -> incorrect upgrade decisions -> customers may not get upgraded or get upgraded to non-existent tier.

---

### 4.7 GapToUpgrade Calculators (5 classes)

All five calculators call `slabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)`, creating a **double subtraction**:

| File | Line | Code |
|------|------|------|
| `AbstractGapToUpgradeCalculator.java` | 116-117 | `slabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)` |
| `LifetimePointsGapToUpgradeCalculator.java` | 84 | `slabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)` |
| `CurrentPointsGapToUpgradeCalculator.java` | 84-85 | `slabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)` |
| `LifetimePurchaseGapToUpgradeCalculator.java` | 99 | `slabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)` |
| `TrackedValueGapToUpgradeCalculator.java` | 117, 149 | `slabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)` |

The call passes `targetSlabNumber - 1`, then `getThresholdValue` does another `- 1` internally. So the actual index is `targetSlabNumber - 2`. Target 4: index `4-2 = 2`. Only 2 thresholds (indices 0,1).

**Entry point:** `RecalculateGapMessageProcessor` (queue consumer) -> `TrackCustomerKpiServiceImpl` -> `GapToUpgradeCalculatorBuilder.build()`.

**Failure mode:** `IndexOutOfBoundsException` -- gap-to-upgrade information unavailable for the highest tier.

---

### 4.8 BulkRequestHandler -- Next Slab Check

**File:** `peb/src/main/java/com/capillary/shopbook/peb/impl/system/BulkRequestHandler.java`

```java
int targetSlabNumber = slab.getSerialNumber() + 1;       // Line 2604
if (targetSlabNumber > slabs.size()) {                    // Line 2605
```

**Two bugs:**
1. `serial + 1` doesn't yield the next slab for non-sequential (slab 2 + 1 = 3, but next slab is 4).
2. Comparing serial number against list size is apples-to-oranges with non-sequential numbering.

**Failure mode:** Incorrect boundary check -- may skip gap-to-upgrade calculation or attempt it for non-existent tier.

---

## 5. Full Call Chain Traces

### 5.1 Point Earning (Every Transaction)

```
EMF Rule Engine (event: TransactionAdd)
  -> PointAwardStrategyImpl.awardPoints()
    -> PointAllocationStrategyImpl.getValue(currentSlab)        // Line 298 -- BREAKS
    -> PointExpiryStrategyImpl.getExpiryDate(serial, ...)       // Line 248 -- BREAKS
```

Also via Thrift:
```
PointsEngineThriftServiceImpl (line 4710)
  -> allocationStrategy.getValue(pointsProgramConfig.getSlabByNumber(slabSerial))
    -> PointAllocationStrategyImpl.getValue(slab)               // Line 298 -- BREAKS
```

### 5.2 Tier Upgrade (Event-Driven)

```
EMF Rule Engine (event: TransactionAdd/Registration)
  -> UpgradeSlabActionImpl.execute()
    -> SlabUpgradeStrategyImpl.getSlabForEagerOrLazy()          // Line 443 -- BREAKS (null slab)
    -> SlabUpgradeStrategyImpl.findValueAllowedBeforeSlabUpgrade()  // Line 372 -- BREAKS
    -> ThresholdBasedSlabUpgradeStrategyImpl.getSmsTemplate()   // Line 810 -- BREAKS (notification)
```

### 5.3 Points Maximization (Transaction Unrolling)

```
EMF Rule Engine (bill unrolling)
  -> UnrollerImpl
    -> PointsMaximizerImpl.findOptimalLineItemOrder()
      -> findAllocationOrder(lineItems, thresholds, ..., slab.getSerialNumber())  // BREAKS (8 sites)
```

### 5.4 Return/Refund (Downgrade Check)

```
ReturnBillAmountEventData / ReturnBillLineitemsEventData
  -> PointsReturnService.processDowngradeOnReturn()
    -> isCustomerToBeDowngraded()                               // Line 1117 -- BREAKS
```

### 5.5 Point Redemption

```
PointsRedemptionEventData
  -> BasicProgramCreator (config building)
    -> PointRedemptionThresholdStrategyImpl.getMinCurrentPoints()  // Line 178 -- BREAKS
    -> PointRedemptionThresholdStrategyImpl.getMaxPointsRedeem()   // Line 198 -- BREAKS
```

### 5.6 Tier Downgrade (Scheduled Job)

```
ScheduledJobs (cron)
  -> TierDowngradeHandler.generateTierDowngradeInputDataAndBatchTasks()
    -> CalculatorType.getCalculatorBuilder().build()
      -> SingleTierDowngradeCalculator.processFiltersAndSetTargetSlab()  // Lines 46,57 -- WRONG TARGET
```

### 5.7 Bulk Allocation (Batch)

```
PebThriftServiceImpl.bulkAllocatePoints()
  -> BulkRequestHandler.bulkAllocatePoints()
    -> AllocationServiceImpl.bulkAwardPoints()
      -> AllocationServiceHelper.updateTargetSlabNumberInTempTable()  // Lines 507-523 -- WRONG SQL
      -> PointsAllocationStrategy.getPointsValueForSlabNumber()      // Line 138 -- BREAKS
      -> PointsExpiryStrategy.getExpiryDate()                        // Line 197 -- BREAKS
```

### 5.8 Gap-to-Upgrade (Queue Consumer)

```
RecalculateGapMessageProcessor (queue)
  -> TrackCustomerKpiServiceImpl
    -> GapToUpgradeCalculatorBuilder.build()
      -> *GapToUpgradeCalculator.getGapToUpgrade()
        -> SlabUpgradeStrategy.getThresholdValue(targetSlabNumber - 1)  // Line 73 -- BREAKS
```

---

## 6. SQL Queries Affected

### 6.1 Bulk Upgrade -- Wrong target_slab_number

**File:** `AllocationServiceHelper.java:507-523`
```sql
UPDATE {tempTable}
SET target_slab_number = {i}+1,    -- i is list index, NOT serial number
    target_slab_id = {slabId}
WHERE ROUND({thresholdCheck} + points_to_allocate, 3) > {threshold}
AND target_slab_number < 0
```

### 6.2 Upgrade Detection -- Sequential Comparison

**File:** `AllocationServiceHelper.java:463-476`
```sql
INSERT INTO customer_slab_upgrade_history (...)
SELECT ... FROM {tempTable} temp
WHERE temp.target_slab_number > temp.slab_number
-- Correct IF serial ordering preserved, but target_slab_number may be wrong (see 6.1)
```

### 6.3 Tier Downgrade Temp Table -- Receives Wrong Target

**File:** `TierDowngradeTempTablesDaoImpl.java:89`
```sql
CREATE TABLE IF NOT EXISTS {table} (
  customer_id BIGINT(20) PRIMARY KEY,
  current_slab_number INT(11) DEFAULT 0,
  target_slab_number INT(11) DEFAULT -1,    -- Receives value from Java: currentSlabNumber - 1
  ...
)
```

The SQL itself is safe -- it stores whatever Java passes. The bug is in the Java code (`SingleTierDowngradeCalculator`) that computes the wrong target.

### 6.4 Slab Fetch -- No ORDER BY (Risk)

**File:** `ProgramSlabDaoImpl.java:79-83`
```sql
SELECT * FROM program_slabs
WHERE program_id = :programId AND org_id = :orgId
-- NO ORDER BY serial_number!
```

Any code that does `slabs.get(i)` where `i` is a loop counter is at risk because the list order is non-deterministic.

---

## 7. Thrift / RPC Boundaries

### 7.1 LoyaltyProgramEnrollment (emf.thrift, Line 184)

```thrift
struct LoyaltyProgramEnrollment {
    1: required i32 tierNumberAtEnrollment;
    2: required i64 tierExpiryDateInMillis;
    3: required list<PointsBalance> pointsBalances;
}
```

The `tierNumberAtEnrollment` field passes the actual serial number across service boundaries. External consumers may assume sequential numbering. **Not a crash risk, but a contract/documentation concern.**

### 7.2 TierReassessmentData (emf.thrift, Line 1039)

```thrift
struct TierReassessmentData {
    15: optional i32 fromSlab;
}
```

Pass-through value. **Safe.**

### 7.3 EBillInstructionImpl (Line 87)

```java
paramsMap.put("slab_number", slabNumber);
```

Slab number serialized into JSON params for cross-service event instructions. Downstream consumers may parse this assuming sequential. **Low risk -- depends on consumer code.**

---

## 8. Configuration and JSON Parsing

### 8.1 Strategy CSV Parsing (Common Pattern)

All strategy constructors follow the same pattern:

```java
// 1. Parse CSV into flat ArrayList
for (String s : StringUtils.split(csvString, ',')) {
    valuesList.add(parse(s));
}

// 2. Validate count against number of slabs
if (valuesList.size() != expectedSize) {
    throw new ParseConfigException(...);
}
```

The CSV validation uses **slab count**, not serial numbers. This is safe -- it just checks "do we have the right number of values?" Regardless of serial numbering, 3 slabs produce 3 (or 2) CSV values.

### 8.2 Map Initialization in ThresholdBasedSlabUpgradeStrategyImpl

```java
int slabIndex = 2;  // Start at 2 (no notification for base slab)
for (String emailSubject : ...) {
    slabIndexToEmailSubject.put(slabIndex++, emailSubject);  // Keys: 2, 3, 4, ...
}
```

With 3 slabs, the map has keys {2, 3}. With non-sequential tiers (1,2,4), the upgrade targets are slabs 2 and 4. Looking up key 4 returns `null` (key 3 was inserted for the non-existent slab 3).

### 8.3 TierDowngradeSlabConfig (JSON, Safe)

```java
@SerializedName("slabNumber")
private int m_slabNumber;
```

Stores actual serial number. No arithmetic. **Safe.**

---

## 9. Tests That Assume Sequential Numbering

### 9.1 emf-parent Tests

| Test File | Lines | What It Does |
|-----------|-------|-------------|
| `SlabUpgradeStrategyImplTest.java` | 383-389 | Creates `Slab(1, 1, "silver")`, sets thresholds `[10, 20, 30]` for sequential 3-slab setup |
| `UpgradeSlabActionImplTest.java` | 732-924 | Mocks `strategy.getSlabForEagerOrLazy()` -- doesn't test the index math |
| `ThresholdBasedSlabUpgradeStrategyImplTest.java` | 35-36 | `new ThresholdBasedSlabUpgradeStrategyImpl(strategy, 3, LAZY)` -- 3 sequential slabs |
| `PointsReturnServiceTest.java` | 4776-5356 | Mocks `isCustomerToBeDowngraded()` away -- doesn't test the index math |
| `PromotionLimitAwarePointsAwardStrategyTest.java` | 270-1315 | Always creates `new Slab(1, 1, "slab")` -- serial 1 only |
| `PointAwardStrategyImplTest.java` | 1170-1507 | `allocationPercentage.get(currentSlab.getSerialNumber() - 1)` -- encodes sequential assumption in test setup |
| `ProgramConfigHandler.java` (test util) | 63 | Reads `serial_number` from XML -- will need non-sequential test data |
| `ProgramConfigGeneratorThrift.java` (test util) | 176 | Sets `serial_number` attribute -- will need non-sequential test data |

### 9.2 peb Tests

| Test File | Lines | What It Does |
|-----------|-------|-------------|
| `PointsAndExpiryDateCalculatorImplTest.java` | 282-890 | `allocationStrategies.get(slabNumber - 1)` in mock setup -- sequential assumption |
| `PEBTestBase.java` | 1845, 2065 | `slabNumberToSlab.get(slabNumber + 1)` and `slabNumber - 1` in test utilities |
| Correction test suite (20+ files) | Various | `src/test/java/.../correction/tierdowngrade/` -- all set up sequential slabs |
| `AllocationServiceHelperTest.java` | Various | Tests allocation helper with sequential slabs |
| `TrackedValueGapToUpgradeCalculatorTest.java` | Various | Tests gap calculator with sequential slabs |

---

## 10. Safe Areas (No Change Required)

### 10.1 Slab Lookup by Serial Number

```java
// ProgramImpl.java:222-228 (emf-parent)
public Slab getSlabBySerial(int serial) {
    for (ProgramSlab ps : m_program.getProgramSlabs()) {
        if (ps.getSerialNumber() == serial)
            return new Slab(ps.getId(), ps.getSerialNumber(), ps.getName(), ps.getDescription());
    }
    return null;
}
```

Linear scan matching by value -- works with any numbering. **Safe.**

### 10.2 Tier Downgrade Config Lookup

```java
// TierDowngradeStrategyConfiguration.java:108-115 (emf-parent)
public TierDowngradeSlabConfig getTierDowngradeSlabConfig(int slabNumber) {
    for (TierDowngradeSlabConfig config : getSlabConfigs()) {
        if (config.getSlabNumber() == slabNumber) { return config; }
    }
    return null;
}
```

Direct match by serial number. **Safe.**

### 10.3 Downgrade Filter Map

```java
// AbstractTierDowngradeCalculator.java (peb)
protected Map<Integer, DowngradeFilter> m_filterMap = new TreeMap<>(Collections.reverseOrder());
// Keys are actual serial numbers from config
m_filterMap.put(slabConfig.getSlabNumber(), downgradeFilter);
```

Map keyed by actual serial number. **Safe.**

### 10.4 LowestTierDowngradeCalculator

```java
// Hardcodes target to 1 -- base slab is always serial 1
m_tierDowngradeService.updateTierDowngradeTargetSlab(..., 1, null);
```

**Safe** -- no arithmetic on serial numbers.

### 10.5 ThresholdTierDowngradeCalculator

Uses `m_tierReassessmentTable` for determining target -- reads reassessed slab from a separate calculation, not from `N-1` arithmetic. **Safe.**

### 10.6 Map-Based Notification Lookups

```java
// ThresholdBasedSlabUpgradeStrategyImpl.java lines 919-1043
slabIndexToEmailSubject.get(slab.getSerialNumber());  // Map.get() returns null, no crash
```

**Safe from crashes** -- but will return `null` for non-sequential serials if the map was populated with sequential keys.

### 10.7 Base Slab Checks (`== 1`)

Multiple places check `serialNumber == 1` to identify the base tier. This is **safe** as long as the base tier always remains serial 1.

### 10.8 SQL Queries Using Actual Serial Numbers

Most SQL writes/reads pass the serial number through from Java without doing arithmetic:
```sql
WHERE current_slab_number = :currentSlabNumber
SET target_slab_number = :targetSlabNumber
```
These are safe -- the bug is in Java computing the wrong value to pass.

---

## 11. Summary: Every Affected User Flow

| # | User Flow | Where It Breaks | Failure Mode | Severity |
|---|-----------|----------------|--------------|----------|
| 1 | **Point earning** (every transaction) | PointAllocationStrategyImpl:298, UnifiedCalculationEngine:174 | IndexOutOfBounds / silent 0 points | **Critical** |
| 2 | **Tier upgrade check** (eager/lazy) | SlabUpgradeStrategyImpl:372, 443 | IndexOutOfBounds / NullPointer | **Critical** |
| 3 | **Points maximization** (bill optimization) | PointsMaximizerImpl:484-559 (8 sites) | IndexOutOfBounds | **Critical** |
| 4 | **Point expiry** (SLAB_BASED) | PointExpiryStrategyImpl:248-254, 714, 719 | IllegalStateException / IndexOutOfBounds | **Critical** |
| 5 | **Point redemption** (min/max/divisibility) | PointRedemptionThresholdStrategyImpl:178-203 | IndexOutOfBounds | **Critical** |
| 6 | **Return/refund downgrade** | PointsReturnService:1117 | IndexOutOfBounds | **Critical** |
| 7 | **Upgrade notifications** (SMS/email) | ThresholdBasedSlabUpgradeStrategyImpl:810-901 | IndexOutOfBounds | **High** |
| 8 | **Single-step tier downgrade** (scheduled) | SingleTierDowngradeCalculator:46, 57 | Wrong target tier (ghost tier 3) | **High** |
| 9 | **Bulk allocation upgrade** (batch) | AllocationServiceHelper:507-523 | Wrong target_slab_number in SQL | **High** |
| 10 | **Gap-to-upgrade** (5 calculators) | 5 GapToUpgrade classes | IndexOutOfBounds | **Medium** |
| 11 | **Next slab navigation** | ProgramImpl:215, EndpointProperties:458 | Null (slab not found) | **Medium** |
| 12 | **Previous slab lookup** | SlabUpgradeInstructionExecutor:144 | Incorrect audit data | **Low** |
| 13 | **Bulk point allocation** (peb) | PointsAllocationStrategy:138, PointsAndExpiryDateCalculatorImpl:207-208 | IndexOutOfBounds | **Critical** |
| 14 | **Bulk expiry calculation** (peb) | PointsExpiryStrategy:197-203, 338-342 | IndexOutOfBounds | **Critical** |
| 15 | **Next slab check** (peb bulk) | BulkRequestHandler:2604-2605 | Wrong boundary check | **Medium** |

---

## 12. Master Breakage Table

### emf-parent (pointsengine)

| # | File | Line(s) | Pattern | Failure Mode |
|---|------|---------|---------|-------------|
| E1 | `PointAllocationStrategyImpl.java` | 298, 303 | `valuesList.get(serial - 1)` | IndexOutOfBounds |
| E2 | `SlabUpgradeStrategyImpl.java` | 372 | `thresholds.get(serial - 1)` | IndexOutOfBounds |
| E3 | `SlabUpgradeStrategyImpl.java` | 443 | `getSlabByNumber(i + 2)` | Null (slab not found) |
| E4 | `PointsMaximizerImpl.java` | 484, 519, 523, 539, 546, 547, 559 | `thresholds.get(serial - 1)` | IndexOutOfBounds |
| E5 | `PointsMaximizerImpl.java` | 555 | `currentSlabSerial + 1` (recursive) | Wrong serial -> IndexOutOfBounds |
| E6 | `PointsReturnService.java` | 1117 | `thresholds.get(serial - 2)` | IndexOutOfBounds |
| E7 | `ThresholdBasedSlabUpgradeStrategyImpl.java` | 810, 822, 841, 853, 865, 877, 889, 901 | `list.get(serial - 2)` | IndexOutOfBounds |
| E8 | `PointExpiryStrategyImpl.java` | 231-232 | `size < serial` bounds check | IllegalStateException |
| E9 | `PointExpiryStrategyImpl.java` | 248, 250, 252, 254, 714, 719 | `list.get(serial - 1)` | IndexOutOfBounds |
| E10 | `PointRedemptionThresholdStrategyImpl.java` | 178, 183, 188, 193, 198, 203 | `list.get(serial - 1)` | IndexOutOfBounds |
| E11 | `UnifiedCalculationEngine.java` | 174 | `list.get(serial - 1)` (bounds-checked) | Silent 0 (wrong result) |
| E12 | `PointsEngineSlabUpgradeInstructionExecutorImpl.java` | 144 | `serial - 1` as previous slab | Wrong audit data |
| E13 | `ProgramImpl.java` | 215 | `getSlabBySerial(serial + 1)` | Null (slab not found) |
| E14 | `PointsEngineEndpointPropertiesImpl.java` | 458 | `getSlabBySerial(serial + 1)` | Null (slab not found) |

### peb

| # | File | Line(s) | Pattern | Failure Mode |
|---|------|---------|---------|-------------|
| P1 | `SlabUpgradeStrategy.java` | 73 | `m_thresholdValues.get(fromSlabNumber - 1)` | IndexOutOfBounds |
| P2 | `SlabUpgradeStrategy.java` | 76-82 | `return i + 1` as serial | Wrong serial |
| P3 | `PointsAllocationStrategy.java` | 138 | `m_allocationValues.get(slabSerial - 1)` | IndexOutOfBounds |
| P4 | `PointsExpiryStrategy.java` | 197, 199, 201, 203 | `m_expiryTimeUnits.get(serial - 1)` | IndexOutOfBounds |
| P5 | `PointsExpiryStrategy.java` | 338, 340, 342 | `m_expiryTimeUnits.get(serial - 1)` (getPointsExpiryInfo) | IndexOutOfBounds |
| P6 | `PointsAndExpiryDateCalculatorImpl.java` | 207, 208, 212, 213 | `list.get(m_slabNumber - 1)` | IndexOutOfBounds |
| P7 | `SingleTierDowngradeCalculator.java` | 46, 57, 68 | `currentSlabNumber - 1` as target | Wrong target tier |
| P8 | `AllocationServiceHelper.java` | 507-523 | `target_slab_number = i+1` (list index as serial) | Wrong SQL target |
| P9 | `AllocationServiceHelper.java` | 463-476 | `target_slab_number > slab_number` | Incorrect comparison (w/ P8) |
| P10 | `AbstractGapToUpgradeCalculator.java` | 116-117 | `getThresholdValue(targetSlabNumber - 1)` | IndexOutOfBounds |
| P11 | `LifetimePointsGapToUpgradeCalculator.java` | 84 | `getThresholdValue(targetSlabNumber - 1)` | IndexOutOfBounds |
| P12 | `CurrentPointsGapToUpgradeCalculator.java` | 84-85 | `getThresholdValue(targetSlabNumber - 1)` | IndexOutOfBounds |
| P13 | `LifetimePurchaseGapToUpgradeCalculator.java` | 99 | `getThresholdValue(targetSlabNumber - 1)` | IndexOutOfBounds |
| P14 | `TrackedValueGapToUpgradeCalculator.java` | 117, 149 | `getThresholdValue(targetSlabNumber - 1)` | IndexOutOfBounds |
| P15 | `BulkRequestHandler.java` | 2604-2605 | `serial + 1 > slabs.size()` | Wrong boundary check |
| P16 | `ProgramSlabDaoImpl.java` | 79-83 | `SELECT * ... (no ORDER BY)` | Non-deterministic list order |

**Total: 30 distinct entries, ~50+ individual call sites, 15 production Java files.**

---

## 13. Fix Approach

### Option A: Serial-to-Index Mapping (Minimal Change)

Introduce a utility that translates actual tier serial numbers to their positional index in the sorted slab list:

```java
public class SlabIndexResolver {
    private final Map<Integer, Integer> serialToIndex;  // {1->0, 2->1, 4->2}
    private final Map<Integer, Integer> indexToSerial;  // {0->1, 1->2, 2->4}

    public SlabIndexResolver(List<ProgramSlab> slabs) {
        // Sort by serial number, then build bidirectional map
        List<ProgramSlab> sorted = slabs.stream()
            .sorted(Comparator.comparingInt(ProgramSlab::getSerialNumber))
            .collect(Collectors.toList());
        this.serialToIndex = new HashMap<>();
        this.indexToSerial = new HashMap<>();
        for (int i = 0; i < sorted.size(); i++) {
            serialToIndex.put(sorted.get(i).getSerialNumber(), i);
            indexToSerial.put(i, sorted.get(i).getSerialNumber());
        }
    }

    /** Convert serial number to 0-based list index */
    public int toIndex(int serialNumber) {
        return serialToIndex.get(serialNumber);
    }

    /** Convert 0-based list index to serial number */
    public int toSerial(int index) {
        return indexToSerial.get(index);
    }

    /** Get the serial number of the previous slab (by rank, not by arithmetic) */
    public int previousSerial(int serialNumber) {
        int idx = serialToIndex.get(serialNumber);
        return idx > 0 ? indexToSerial.get(idx - 1) : -1;
    }

    /** Get the serial number of the next slab (by rank, not by arithmetic) */
    public int nextSerial(int serialNumber) {
        int idx = serialToIndex.get(serialNumber);
        return idx < indexToSerial.size() - 1 ? indexToSerial.get(idx + 1) : -1;
    }
}
```

Then replace every `serialNumber - 1` with `resolver.toIndex(serialNumber)` and every `serialNumber + 1` / `serialNumber - 1` (used as slab number) with `resolver.nextSerial(serialNumber)` / `resolver.previousSerial(serialNumber)`.

### Option B: Renumber on Tier Creation (Zero Code Change)

Enforce at the API/admin layer that serial numbers are always reassigned as contiguous 1-based integers when a tier is created, modified, or deleted. This preserves the existing invariant.

### Option C: Dual Representation

Store both the "display order" (which can be non-sequential and user-controlled) and a "system index" (which is always 1-based contiguous and used for strategy mapping). Map between them at the API boundary.

### Recommendation

**Option A** is the most flexible but requires changes to 15 files. **Option B** is the safest (zero code change) but constrains the feature. The choice depends on the business requirement driving non-sequential numbering.

---

## Pre-Existing Bugs Discovered

During this analysis, two pre-existing bugs were found:

1. **`SlabUpgradeStrategy.getThresholdValue()` (peb, line 70):** Bounds check uses `>` instead of `>=`, allowing an off-by-one `IndexOutOfBoundsException`.

2. **`SlabUpgradeStrategy.getExpectedSlabNumber()` (peb, line 78):** While loop condition uses `||` instead of `&&`, causing guaranteed `ArrayIndexOutOfBoundsException` when any customer's points exceed all thresholds.

3. **`ProgramSlabDaoImpl.getProgramSlabsForProgram()` (peb, lines 79-83):** No `ORDER BY serial_number` -- list order is non-deterministic. Any code using list index as a serial number proxy is fragile even with sequential numbering.
