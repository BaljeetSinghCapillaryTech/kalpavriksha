# Tiers – UI Validation Reference

This document captures **every UI-side validation** present in the repo (`cap-loyalty-ui/webapp`) for the Tiers module.
It is organised flow-by-flow (Create Tier → Add/Edit Tier → Advanced Settings) with the exact field, rule, error message, source file and conditional logic for each validation.

---

## Table of Contents

1. [Entry Points & File Map](#1-entry-points--file-map)
2. [Create Tier – Validations](#2-create-tier--validations)
3. [Add / Edit Tier – Validations](#3-add--edit-tier--validations)
    - 3.1 [Primary Information](#31-primary-information)
    - 3.2 [Upgrade Criteria](#32-upgrade-criteria)
    - 3.3 [Secondary (Additional) Upgrade Criteria](#33-secondary-additional-upgrade-criteria)
    - 3.4 [Downgrade Criteria](#34-downgrade-criteria)
    - 3.5 [Renewal Conditions](#35-renewal-conditions)
    - 3.6 [Tier Renewal Validity (Computation Window)](#36-tier-renewal-validity-computation-window)
4. [Advanced Settings – Tiers](#4-advanced-settings--tiers)
5. [Global / Shared Regex & Limits](#5-global--shared-regex--limits)
6. [Save Button – Disable Logic Matrix](#6-save-button--disable-logic-matrix)
7. [Conditional Validation Summary](#7-conditional-validation-summary)

---

## 1. Entry Points & File Map

| Flow | Entry Component | Path |
|---|---|---|
| Create Tier | `CreateTier` | `app/components/organisms/CreateTier/CreateTier.js` |
| Add / Edit Tier | `AddTier` | `app/components/organisms/AddTier/AddTier.js` |
| Primary Info form | `AddTierPrimaryInfo` | `app/components/molecules/AddTierPrimaryInfo/AddTierPrimaryInfo.js` |
| Upgrade block | `UpgradeTierV2` | `app/components/molecules/UpgradeTierV2/UpgradeTierV2.js` |
| Downgrade block | `DowngradeTier` | `app/components/molecules/DowngradeTier/DowngradeTier.js` |
| Upgrade + Downgrade wrapper | `TierUpgradeAndDowngrade` | `app/components/organisms/TierUpgradeAndDowngrade/TierUpgradeAndDowngrade.js` |
| Renewal block | `RenewalTierV2` | `app/components/molecules/RenewalTierV2/RenewalTierV2.js` |
| Color input | `ColorSelector` | `app/components/molecules/ColorSelector/ColorSelector.js` |
| Advanced Settings | `TierAdvancedOption` | `app/components/organisms/TieradvancedOption/TierAdvancedOption.js` |
| Core validation utils | `getSaveDisable`, `colorValidator` | `app/components/organisms/AddTier/utils.js` |
| Shared tier utils | `upgradeSaveDisable`, `downgradSaveDisable`, `validateValueBetweenRange` | `app/utils/tiers.js` |

---

## 2. Create Tier – Validations

Create Tier shows only the **Primary Info** section — it is the minimal form used when first adding a tier. All validations below must pass for the **Save** button to enable.

| # | Field | Rule | Error Message | Source |
|---|---|---|---|---|
| 1 | **Tier Name** | Required (non-empty) | – (button disabled) | `AddTier/utils.js:36–39` |
| 2 | **Tier Name** | Must be unique (case-insensitive) — checked on blur against `allTiersName` | `Tier name cannot have duplicate values.` | `AddTierPrimaryInfo.js:44–50`, `messages.js:24–27` |
| 3 | **Description** | Optional | – | `AddTierPrimaryInfo.js:58–62` |
| 4 | **Color (HEX)** | Required, must match `/^#[0-9A-F]{6}$/i` | – (field invalidated) | `AddTier/utils.js:33` |
| 5 | **Color input length** | Max 7 chars including `#`; spaces not allowed | – | `ColorSelector.js:40–54` |
| 6 | **isValidHexInput flag** | Must be `true` for Save to enable | – | `AddTier/utils.js:36–39` |

**Save disable condition for Create Tier**

```
showSpin || primaryInfoSaveDisable || !colorValidator(color) || !isValidHexInput || isNameDuplicateError
```
Defined in `AddTier/utils.js:79–124`.

---

## 3. Add / Edit Tier – Validations

When editing an existing tier, the form exposes the **full** stack: Primary Info + Upgrade + Downgrade + Renewal + Validity. All items in Section 2 apply, plus the following.

### 3.1 Primary Information

| Field | Rule | Error | Source |
|---|---|---|---|
| Tier Name | Required, must not duplicate other slabs (current tier skipped via `tierIndex`) | `Tier name cannot have duplicate values.` | `AddTier/utils.js:394–398`, `AddTierPrimaryInfo/messages.js:24` |
| Description | Optional | – | `AddTierPrimaryInfo.js:58–62` |
| Color | HEX regex validated | – | `AddTier/utils.js:33` |

---

### 3.2 Upgrade Criteria

| Field | Rule | Error / Behaviour | Source |
|---|---|---|---|
| **Upgrade Type** | Required — one of `POINTS_BASED` / `PURCHASE_BASED` / `TRACKER_VALUE_BASED` | Save disabled while empty | `UpgradeTierV2.js:102–107` |
| **Upgrade Mode** | Required — one of `ABSOLUTE_VALUE` / `ROLLING_VALUE` / `DYNAMIC` (DYNAMIC only when condition is “Any-1”). Options may be disabled via `disabledUpgradeModes`. | Save disabled | `UpgradeTierV2.js:129–143` |
| **Upgrade Value** | Required; numeric; must lie within `thresholdValues.upgrade` min/max; must be ≤ `MAX_INTEGER_LIMIT` (2,147,483,647); validated on blur through `validateValueBetweenRange` | `This field must be between <min> and <max>` (built via `getMinMaxRangeString`) | `UpgradeTierV2.js:194–200`, `utils/tiers.js:201–239`, `App/constants.js:641` |
| **Tracker ID** | Required **only** when `upgradeType === TRACKER_VALUE_BASED` | Save disabled | `utils/tiers.js:215–223` |
| **Tracker Condition ID** | Required **only** when tracker-based | Save disabled | `utils/tiers.js:215–223` |

Key skip logic: in `upgradeSaveDisable`, when `isAdvanceSetting===true`, keys `value`, `timePeriod`, `downgradeTarget` are **not** enforced.

---

### 3.3 Secondary (Additional) Upgrade Criteria

Enforced only when `additionalUpgradeCriteria.secondaryCriteriaEnabled === true`.

| Sub-field | Rule | Error | Source |
|---|---|---|---|
| `trackerId` | Required (non-empty) | Save disabled | `utils/tiers.js:225–231` |
| `trackerConditionId` | Required | Save disabled | `utils/tiers.js:225–231` |
| `upgradeMode` | Required | Save disabled | `utils/tiers.js:225–231` |
| `additionalThresholdValues` | No empty string allowed in the array (skipped when `isAdvanceSetting`) | Save disabled | `utils/tiers.js:232–233` |
| `customCriteriaExpression` | Required **only** when `additionalConditionTrackers === CUSTOM` | Save disabled | `utils/tiers.js:234–235` |

---

### 3.4 Downgrade Criteria

Applied only when `shouldDowngrade === true`.

| Field | Rule | Error | Source |
|---|---|---|---|
| **Downgrade Condition** | Required — `FIXED` / `FIXED_DURATION` / `FIXED_CUSTOMER_REGISTRATION` | Save disabled | `DowngradeTier.js:120–135` |
| **Start Date** (only when `downgradeCondition === FIXED` **and** `dailyDowngradeEnabled === false`) | Must fall on the 1st of a month | `Downgrade allowed only on 1st of every month.` | `TierUpgradeAndDowngrade.js:247–261`, `DowngradeTier/messages.js:16–19` |
| **Time Period / Valid For** | Required; must be a positive integer (`POSITIVE_INTEGER_REGEX`); `maxLength=25` | `This field must be a valid number.` | `DowngradeTier.js:422–441`, `DowngradeTier/messages.js:12–14` |
| Time Period skip rule | Not validated when `downgradeCondition === FIXED_CUSTOMER_REGISTRATION`, **or** `FIXED && isFixedTypeWithoutYear` | – | `utils/tiers.js:254–261` |
| **Downgrade Target** | Required (tier must be selected) when `shouldDowngrade` is on | Save disabled | `AddTier.js:477–498` |

---

### 3.5 Renewal Conditions

Enforced only when `shouldDowngrade && isRenewal`.

| Field | Rule | Error | Source |
|---|---|---|---|
| Checked `renewConditions` (purchase / numVisits / points) | If `checked===true`, the paired `value` must be non-empty | Save disabled | `AddTier/utils.js:62–77` |
| `renewTracker[n]` | Every key (`trackerId`, `trackerConditionId`, `value`) must be non-empty | Save disabled | `AddTier/utils.js:74–77` |
| `expression_relation` | When renewal expression is used, array must have length > 0 and be a valid bracket expression | `Invalid expression for tier renewal conditions.` | `AddTier/utils.js:77`, `RenewalTierV2.js:91–143`, `RenewalTierV2/messages.js:38` |
| **Renewal Period – Fixed-date based** (`renewalLastMonths`) | Integer 1–36 (can’t be 0); maxLength 2 | `Max value: 36` | `DowngradeTier.js:288–320`, `DowngradeTier/messages.js:114–116` |
| **Renewal Period – Custom period** (`customPeriodMonths`) | Integer 1–36 (can’t be 0); maxLength 2 | `Max value: 36` | `DowngradeTier.js:291–378` |
| **Custom Month selection** | Required when Custom Period chosen (from `MONTH_NAMES`) | Save disabled | `DowngradeTier.js:278–399` |

---

### 3.6 Tier Renewal Validity (Computation Window)

Logic in `renewTierValidityDisable` (`AddTier/utils.js:126–148`).

| `renewalWindowType` | Rule |
|---|---|
| `LAST_CALENDAR_YEAR` | No further validation — always valid |
| `CUSTOM_PERIOD` | `computationWindowStartValue − computationWindowEndValue` must be ≤ 35, else Save disabled |
| `FIXED_DATE_BASED` | `computationWindowStartValue` must be > 0 **and** ≤ 36, else Save disabled |
| Any type | `computationWindowStartValue` required and must parse to a valid integer |

---

## 4. Advanced Settings – Tiers

Entry: `TierAdvancedOption.js`. All validations from Sections 3.2, 3.3 and 3.4 apply **with the flag `isAdvanceSetting=true`**, which relaxes three fields:

> In advanced settings the keys `value`, `timePeriod`, `downgradeTarget` are NOT enforced (see `skipKeyInAdvanceSetting` — `utils/tiers.js:196–198`).

### 4.1 Additional Advanced-only Validations

| Field | Rule | Error | Source |
|---|---|---|---|
| **Minimum Duration** (`validityMinDuration`) | Optional; must be a positive integer; cannot be `0`; only relevant when `downgradeCondition === FIXED` | – (inline `POSITIVE_INTEGER` restriction) | `TierUpgradeAndDowngrade.js:500–505` |
| **Check Tier Validity on Daily Basis** (`downgradeDailyBasis`) | Boolean toggle; auto-forced to `true` when `isDowngradeDailyBasisDisabled` is true (i.e. `FIXED_CUSTOMER_REGISTRATION`, or `FIXED && isFixedTypeWithoutYear`) | – | `TierAdvancedOption.js:199–211`, `TierAdvancedOption/messages.js:12–19` |
| **Validate Downgrade on Return Transaction** (`validateDowngradeOnReturn`) | Boolean toggle; no validation | – | `TierAdvancedOption/messages.js:21–28` |
| **Extend Available Points to New Cycle** (`extendAvailPointNewCycle`) | Boolean toggle; no validation | – | `TierAdvancedOption/messages.js:39–41` |
| **Downgrade on Partner Program Expiry** (`downgradeOnPartnerProgramExpiry`) | Boolean toggle; no validation | – | `TierAdvancedOption/messages.js:30–37` |

### 4.2 Save Button – Advanced Settings

```
showSpin
|| upgradeSaveDisable({ isAdvanceSetting: true, upgradeCriteria, additionalUpgradeCriteria })
|| downgradSaveDisable({ isAdvanceSetting: true, shouldDowngrade, downgradeOption, isFixedTypeWithoutYear })
|| (shouldDowngrade && isStartDateError)
```
Source: `TierAdvancedOption.js:123–143`.

---

## 5. Global / Shared Regex & Limits

| Constant | Value | File |
|---|---|---|
| `colorValidator` regex | `/^#[0-9A-F]{6}$/i` | `AddTier/utils.js:33` |
| Color max length | `7` (incl. `#`) | `ColorSelector.js` |
| `MAX_INTEGER_LIMIT` | `2147483647` | `App/constants.js:641` |
| `POSITIVE_INTEGER_REGEX` | `/^(?=.+)(?:[1-9]\d*\|0)?(?:\.\d+)?$/` | `molecules/NumberInput/constants.js:2` |
| `POSITIVE_DECIMAL_REGEX` | `/^\d*(\.\d*)?$/` | `molecules/NumberInput/constants.js:5` |
| `POSITIVE_INTEGER_REGEX_WITH_LEADING_ZERO` | `/^(?=.+)(?:0*[1-9]\d*\|0)?(?:\.\d+)?$/` | `molecules/NumberInput/constants.js:8` |
| Renewal months cap | `36` | `DowngradeTier.js:288–293` |
| Custom-period diff cap | `35` | `AddTier/utils.js:135` |

---

## 6. Save Button – Disable Logic Matrix

Source of truth: `getSaveDisable` — `AddTier/utils.js:79–124`.

| Flow | Save disabled when… |
|---|---|
| **Create Tier** | `showSpin` \| primary info missing \| invalid HEX \| `!isValidHexInput` \| `isNameDuplicateError` |
| **Edit Tier** | Create-tier conditions **+** upgrade incomplete **+** downgrade incomplete **+** renewal invalid **+** tier renewal validity invalid **+** (`shouldDowngrade && isStartDateError`) |
| **Advanced Settings** | `showSpin` \| upgrade incomplete (with `isAdvanceSetting`) \| downgrade incomplete (with `isAdvanceSetting`) \| additional eligibility incomplete \| (`shouldDowngrade && isStartDateError`) |

---

## 7. Conditional Validation Summary

| Validation | Fires only when… |
|---|---|
| Downgrade Target required | `shouldDowngrade === true` |
| Renewal condition values required | `shouldDowngrade && isRenewal` |
| Start Date = 1st-of-month | `downgradeCondition === FIXED && dailyDowngradeEnabled === false` |
| Time Period required | `downgradeCondition !== FIXED_CUSTOMER_REGISTRATION` **and** not (`FIXED && isFixedTypeWithoutYear`) |
| Minimum Duration applies | `downgradeCondition === FIXED` and Min-duration toggle on |
| Tracker ID / Condition required | `upgradeType === TRACKER_VALUE_BASED` |
| Secondary criteria required | `secondaryCriteriaEnabled === true` |
| Custom expression required | `additionalConditionTrackers === CUSTOM` |
| Renewal months limit (36) | `renewalWindowType === FIXED_DATE_BASED` |
| Custom-period diff limit (35) | `renewalWindowType === CUSTOM_PERIOD` |
| Advanced-settings field relaxation | `isAdvanceSetting === true` (skips `value`, `timePeriod`, `downgradeTarget`) |

---

### Notes for QA / Developers

- Field-level errors (e.g., "Max value: 36", duplicate name, start-date rule) render inline beneath the input.
- Most "required" validations do **not** surface a visible error message — they simply keep the **Save** button disabled.
- Numeric validity is enforced with the shared `NumberInput` component; any field using `type="POSITIVE_INTEGER"` will silently block non-integer keystrokes before `onChange` fires.
- Error messages are kept in `messages.js` files inside each component folder; text is internationalised through `react-intl`.
