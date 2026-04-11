# UI Requirements Extraction -- Tiers & Benefits Prototype

> Source: 8 screenshots from v0.app prototype
> Path: /Users/ritwikranjan/Desktop/Artificial Intelligence/UI/
> Date: 2026-04-11
> Relevance to scope: Tier CRUD (primary), Benefits listing (reference only -- out of scope)

---

## Screen Inventory

| # | Screen | Source Screenshot | In Scope? |
|---|--------|------------------|-----------|
| S-1 | Tier Listing (comparison matrix + KPIs) | Screenshot 12.40.40 | YES -- primary |
| S-2 | Eligibility Criteria section | Screenshot 12.40.58 | YES -- tier config |
| S-3 | Downgrade/Exit + Benefits on-tier | Screenshot 12.41.10 | YES (downgrade) + reference (benefits) |
| S-4 | Benefits Configuration on-tier | Screenshot 12.41.20 | Reference only (benefits out of scope) |
| S-5 | Benefits Listing page | Screenshot 12.42.39 | Reference only |
| S-6 | Benefits Listing expanded | Screenshot 12.42.49 | Reference only |
| S-7 | Add Benefit modal (Step 1) | Screenshot 12.43.02 | Reference only |
| S-8 | Add Benefit modal (Step 2) | Screenshot 12.43.09 | Reference only |

---

## Screen S-1: Tier Listing Page (PRIMARY)

### Page Structure
- **URL**: `/program/tiers`
- **Header**: "Tiers" (h1) + subtitle "Complete tier configuration and hierarchy management"
- **Program Selector**: Dropdown at top left -- "Loyalty Program 2025" (implies multi-program support, API must accept programId)
- **Action Buttons** (top right): "Filter Tiers" (funnel icon) + "Tier Settings" (hamburger icon)

### KPI Summary Cards (4 cards, horizontal row)
| Card | Icon | Value | Label |
|------|------|-------|-------|
| Total Tiers | stacked layers | 4 | Total Tiers |
| Active | checkmark (green) | 4 | Active |
| Scheduled | clock (green) | 0 | Scheduled |
| Total Members | people icon | 2,135 | Total Members |

**API implications:**
- `GET /v3/tiers` response must include: `summary.totalTiers`, `summary.activeTiers`, `summary.scheduledTiers`, `summary.totalMembers`
- "Scheduled" concept needs definition (see Critic C-5)

### Comparison Matrix
- **Layout**: Columns = tiers (Bronze, Silver, Gold), Rows = configuration dimensions
- **Column Headers**: Tier name + color dot (orange=Bronze, grey=Silver, gold=Gold) + edit icon (pencil) + status badge ("Active" green pill)
- **Section grouping**: "Basic Details", "Eligibility Criteria", "Tier Renewal/Retention Criteria", "Downgrade/Exit Criteria", "Benefits"

### Basic Details Section (Row Group 1)

| Row Label | Bronze | Silver | Gold | Field Type |
|-----------|--------|--------|------|------------|
| Name | Bronze | Silver | Gold | text (read-only in matrix, editable inline) |
| Description | Entry level tier with basic benefits | Mid-level tier with enhanced benefits | Premium tier with exclusive benefits | text (may truncate) |
| Duration | Jan 1, 2025 to Indefinite | Jan 1, 2025 to Dec 31, 2025 | Jan 1, 2025 to Dec 31, 2025 | date range (start + end/Indefinite) |
| Members | 1,245 | 667 | 234 | integer (cached count) |

**API fields needed:**
```
basicDetails: {
  name: string,
  description: string,
  duration: {
    startDate: date,
    endDate: date | null  // null = Indefinite
  },
  memberCount: integer  // cached
}
```

**UI-BA GAP #1**: The BA/PRD does not include `duration` (start date / end date) as a tier field. The UI clearly shows it per tier. The existing `ProgramSlab` entity has `createdOn` but NO `startDate` or `endDate`. The `TierConfiguration` has no duration field either. **This is a new field not captured in BA.**

### Eligibility Criteria Section (Row Group 2)

| Row Label | Bronze | Silver | Gold | Field Type |
|-----------|--------|--------|------|------------|
| Criteria Type | Activity Based | Activity Based | Activity Based | enum (same for all tiers per program) |
| Activities | Any Purchase **OR** | Spending >= RM 550 **AND** Min 2 transactions within a year | Spending >= RM 900 **AND** Min 2 transactions within a year | compound condition with AND/OR |
| Membership Duration | Indefinite | 12 months | 12 months | text/duration |
| Upgrade Schedule | Immediately when eligibility is met | Immediately when eligibility is met | Immediately when eligibility is met | enum/text |
| Nudges/Communications | Welcome email on joining | Upgrade congratulations email | VIP welcome package notification | text |

**API fields needed:**
```
eligibilityCriteria: {
  criteriaType: enum (ACTIVITY_BASED, ...),
  activities: [
    {
      type: string,  // "Spending", "Transactions", "Any Purchase"
      operator: enum (GTE, LTE, EQ),
      value: number | null,
      unit: string | null  // "RM", "transactions"
    }
  ],
  activityRelation: enum (AND, OR),
  membershipDuration: string | null,  // "12 months", "Indefinite"
  upgradeSchedule: string,  // "Immediately when eligibility is met"
  nudges: string | null  // communication description
}
```

**UI-BA GAP #2**: The BA mentions eligibility criteria types (Current Points, Lifetime Points, etc.) but the UI shows "Activity Based" as the criteria type with compound conditions (Spending AND Transactions). The UI's "Activity Based" maps to tracker-based criteria in the codebase. The BA doesn't define the detailed activity condition model (operator, value, unit, relation). **This compound condition structure needs to be in the MongoDB document schema.**

**UI-BA GAP #3**: "Membership Duration" is shown per tier (Indefinite for Bronze, 12 months for Silver/Gold). This is NOT the same as the tier "Duration" in Basic Details. Membership Duration appears to be how long a member stays in the tier before re-evaluation. **The BA does not clearly distinguish between tier validity period and membership duration.**

### Tier Renewal/Retention Criteria Section (Row Group 3)

| Row Label | Bronze | Silver | Gold | Field Type |
|-----------|--------|--------|------|------------|
| Renewal Criteria Type | Same as eligibility | Same as eligibility criteria | Same as eligibility criteria | enum/text |
| Renewal Condition | Any Purchase **OR** | Spending >= RM 550 **AND** Min 2 transactions within a year | Spending >= RM 900 **AND** Min 2 transactions within a year | compound condition (same model as activities) |
| Renewal Schedule | N/A - Base tier | End of month when duration ends | End of month when duration ends | text |
| Nudges/Communications | N/A | Renewal reminder 30 days before expiry | VIP renewal reminder with exclusive preview | text |

**API fields needed:**
```
renewalConfig: {
  renewalCriteriaType: string,  // "Same as eligibility", or custom
  renewalCondition: {
    activities: [...],  // same model as eligibility activities
    activityRelation: enum (AND, OR)
  } | null,
  renewalSchedule: string | null,  // "End of month when duration ends"
  nudges: string | null
}
```

**Observation**: Bronze (base tier) has N/A for renewal schedule and nudges. The API should handle null/N/A gracefully for base tiers.

### Downgrade/Exit Criteria Section (Row Group 4)

| Row Label | Bronze | Silver | Gold | Field Type |
|-----------|--------|--------|------|------------|
| Downgrade To | N/A - Lowest tier | Bronze (one tier below) | Silver (one tier below) | reference to another tier + description |
| Downgrade Schedule | Month-end (yellow pill) | Month-end (yellow pill) | Daily (yellow pill) | enum with color-coded badge |
| Expiry Reminders | Inactivity warning at 18 months | Downgrade warning at 60 days before expiry | Premium retention offer 90 days before expiry | text |

**API fields needed:**
```
downgradeConfig: {
  downgradeTo: {
    tierId: integer | null,  // null for base tier
    tierName: string,
    description: string  // "one tier below", "Lowest tier"
  },
  downgradeSchedule: enum (MONTH_END, DAILY),
  expiryReminders: string | null
}
```

**UI-BA GAP #4**: The UI shows "Daily" for Gold's downgrade schedule with a different colored badge (lighter/yellow vs the others). The `TierConfiguration` has `dailyDowngradeEnabled` boolean, and `TierDowngradePeriodConfig` likely controls the schedule. The PRD mentions downgrade schedule as a field but doesn't detail the MONTH_END vs DAILY distinction. **The API enum must include both values.**

### Benefits Configuration Section (Row Group 5 -- on Tier page)

| Benefit | Bronze | Silver | Gold | Type |
|---------|--------|--------|------|------|
| Welcome Gift | RM 10 voucher | RM 25 voucher | RM 50 voucher | voucher (currency amount) |
| Upgrade Bonus Points | -- | 500 points | 1,000 points | points (integer) |
| Tier Badge | Bronze badge | Silver badge | Gold badge | badge (text) |
| Renewal Bonus | -- | 250 points | 500 points | points |
| Loyalty Voucher | -- | -- | RM 30 voucher | voucher |
| Earn Points | 1 pt/RM | 1.5 pt/RM | 2 pt/RM | rate (decimal + unit) |
| Birthday Bonus | 100 points | 200 points | 500 points | points |
| Priority Support | -- | -- | Priority queue | text |
| Free Shipping | -- | Orders > RM 100 | Orders > RM 50 | conditional (threshold) |
| VIP Events | -- | -- | -- | text |
| Exclusive Comms | Monthly | Bi-weekly | Weekly | frequency enum |

**"Manage benefits" link** at top right navigates to the standalone Benefits listing page.

**API fields needed for tier listing (benefits summary):**
```
benefits: [
  {
    benefitName: string,
    category: string,  // inferred from grouping
    valuePerTier: {
      [tierId]: string | null  // "RM 10 voucher", "500 points", "--"
    }
  }
]
```

**UI-BA GAP #5**: The benefits section on the tier page is a COMPARISON view -- benefit rows with values per tier column. This is different from the standalone benefits listing (S-5/S-6). The tier listing API needs to return benefits as a matrix-compatible structure, not a flat list per tier. **The PRD says "linked benefits summary (benefitName, value per tier)" but doesn't specify the matrix format.** The API response must be structured so the UI can render it as rows (benefits) x columns (tiers).

---

## Screen S-5/S-6: Benefits Listing Page (REFERENCE)

Out of scope for this pipeline but important for understanding the benefits data model.

### Page Structure
- **URL**: likely `/program/benefits`
- **Header**: "Benefits" + "+ Add Benefit" button (top right)
- **Program Selector**: Same as tier page
- **KPI Cards**: Total Benefits (67), Active (67), Scheduled (0), Categories (11)
- **Search bar** + **Status filter** + **Category filter** + **Table/Grouped toggle**

### Benefits Table Columns
| Column | Example | Type |
|--------|---------|------|
| Benefit Name | RM 10 voucher | text (with colored dot per tier association) |
| Duration | Jan 1, 2025 - Dec 31, 2025 | date range |
| Last Modified | Dec 15, 2024 | date |
| Status | Active (green badge) | enum |

### Grouping
Benefits are grouped by **Category** with expand/collapse:
- Welcome Gift (7 benefits): RM 10, RM 25, RM 50, RM 100, RM 500, RM 1,000, RM 2,000 vouchers
- Upgrade Bonus Points (6 benefits): 500, 1,000, (and more) points

**Data model implication**: Benefits have a `category` field. Each benefit has a duration, last modified date, and status. Multiple benefits can share a category. The colored dots on benefit names appear to indicate which tier(s) the benefit is linked to.

---

## Screen S-7/S-8: Add Benefit Modal (REFERENCE)

Out of scope but reveals the benefit creation data model.

### Step 1: Benefit Details
| Field | Type | Required | Example |
|-------|------|----------|---------|
| Name | text input | Yes | "Enter benefit name" |
| Description | textarea | No | "Enter benefit description" |
| Category | dropdown | Yes | "Select a category" |
| Linked Tiers | multi-select chips | Yes | Bronze, Silver, Gold (selected by default) |
| Type | radio | Yes | Activity based / Broadcast |
| Is opt-in required? | toggle | No | false (default) |

**Linked Tiers options shown**: Bronze, Silver, Gold, Platinum, Diamond, Prestige, Black

**UI-BA GAP #6**: The tier chip selector shows 7 possible tiers: Bronze, Silver, Gold, Platinum, Diamond, Prestige, Black. But the tier listing page only shows 3 tiers (Bronze, Silver, Gold). This suggests the full program may have more tiers than visible in the current view, OR the chip list is a static UI component showing all possible tier levels. **The API must support programs with varying numbers of tiers (not hardcoded to 3).**

### Step 2: Activities to be Rewarded
| Field | Type | Example |
|-------|------|---------|
| Activity type | radio | Single / Milestone-based / Streak-based |
| Select an action | dropdown | "Select an action" |

---

## Component Hierarchy

```
TiersPage
  ProgramSelector (dropdown)
  KpiSummaryBar
    KpiCard (totalTiers)
    KpiCard (activeTiers)
    KpiCard (scheduledTiers)
    KpiCard (totalMembers)
  TiersSectionHeader ("Tiers" + "Filter Tiers" + "Tier Settings")
  ComparisonMatrix
    MatrixHeader
      TierColumnHeader[] (name, color dot, edit icon, status badge)
    MatrixSection ("Basic Details")
      MatrixRow[] (Name, Description, Duration, Members)
    MatrixSection ("Eligibility Criteria")
      MatrixRow[] (Criteria Type, Activities, Membership Duration, Upgrade Schedule, Nudges)
    MatrixSection ("Tier Renewal/Retention Criteria")
      MatrixRow[] (Renewal Criteria Type, Renewal Condition, Renewal Schedule, Nudges)
    MatrixSection ("Downgrade/Exit Criteria")
      MatrixRow[] (Downgrade To, Downgrade Schedule, Expiry Reminders)
    MatrixSection ("Benefits")
      BenefitsComparisonHeader
      BenefitRow[] (benefit name, value per tier)
      ManageBenefitsLink
```

---

## Field Inventory (All Fields the API Must Return)

### Per-Tier Fields

| # | Field Name (UI Label) | API Field Name | Type | Section | Required? | In BA/PRD? |
|---|----------------------|---------------|------|---------|-----------|------------|
| F-1 | Name | basicDetails.name | string | Basic Details | Yes | Yes |
| F-2 | Description | basicDetails.description | string | Basic Details | No | Yes |
| F-3 | Color (dot) | basicDetails.color | string (hex) | Column Header | No | Yes |
| F-4 | Status (badge) | status | enum | Column Header | Yes | Yes |
| F-5 | Duration | basicDetails.duration | {startDate, endDate} | Basic Details | **MISSING** | **NO** |
| F-6 | Members | basicDetails.memberCount | integer | Basic Details | No (cached) | Yes |
| F-7 | Criteria Type | eligibilityCriteria.criteriaType | enum | Eligibility | Yes | Yes |
| F-8 | Activities | eligibilityCriteria.activities[] | compound | Eligibility | Yes | Partial |
| F-9 | Activity Relation | eligibilityCriteria.activityRelation | enum (AND/OR) | Eligibility | Yes | **NO** |
| F-10 | Membership Duration | eligibilityCriteria.membershipDuration | string | Eligibility | No | **NO** |
| F-11 | Upgrade Schedule | eligibilityCriteria.upgradeSchedule | string | Eligibility | No | Yes |
| F-12 | Nudges/Communications | eligibilityCriteria.nudges | string | Eligibility | No | Yes |
| F-13 | Renewal Criteria Type | renewalConfig.renewalCriteriaType | string | Renewal | No | Yes |
| F-14 | Renewal Condition | renewalConfig.renewalCondition | compound | Renewal | No | Yes |
| F-15 | Renewal Schedule | renewalConfig.renewalSchedule | string | Renewal | No | Yes |
| F-16 | Renewal Nudges | renewalConfig.nudges | string | Renewal | No | Yes |
| F-17 | Downgrade To | downgradeConfig.downgradeTo | {tierId, tierName} | Downgrade | No | Yes |
| F-18 | Downgrade Schedule | downgradeConfig.downgradeSchedule | enum (MONTH_END/DAILY) | Downgrade | No | Partial |
| F-19 | Expiry Reminders | downgradeConfig.expiryReminders | string | Downgrade | No | Yes |
| F-20 | Edit icon (per tier) | -- | UI action | Column Header | -- | Implied |
| F-21 | Benefits per tier | benefits[] | array of {name, value} | Benefits | No | Yes |

### KPI Summary Fields

| # | Field Name | API Field Name | Type | In BA/PRD? |
|---|-----------|---------------|------|------------|
| K-1 | Total Tiers | summary.totalTiers | integer | Yes |
| K-2 | Active | summary.activeTiers | integer | Yes |
| K-3 | Scheduled | summary.scheduledTiers | integer | Partial (see C-5) |
| K-4 | Total Members | summary.totalMembers | integer | Yes |

---

## UI-BA Gap Summary

| # | Gap | Severity | Description |
|---|-----|----------|-------------|
| GAP-1 | Tier Duration missing from BA/PRD | HIGH | UI shows start date + end date (or Indefinite) per tier. BA/PRD has no `duration` field. ProgramSlab has `createdOn` but no `startDate`/`endDate`. This is likely tied to the tier validity period from the slab upgrade strategy. |
| GAP-2 | Activity condition model not defined | MEDIUM | UI shows compound conditions ("Spending >= RM 550 AND Min 2 transactions"). BA mentions eligibility criteria types but not the detailed condition structure (operator, value, unit, relation). |
| GAP-3 | Membership Duration vs Duration confusion | MEDIUM | UI has both "Duration" (Basic Details -- date range) and "Membership Duration" (Eligibility -- "12 months"/"Indefinite"). These appear to be different concepts. BA/PRD does not distinguish them. |
| GAP-4 | Downgrade Schedule enum values | LOW | UI shows MONTH_END and DAILY as distinct options with different badge colors. PRD mentions downgrade schedule but doesn't specify the enum values. |
| GAP-5 | Benefits matrix format | LOW | Benefits on tier page are a cross-tier comparison matrix (rows = benefits, columns = tiers). PRD says "linked benefits summary" but doesn't specify the matrix-friendly response format. |
| GAP-6 | Variable tier count | LOW | Benefit creation shows 7 possible tiers. API must support variable tier counts per program, not assume a fixed number. |

---

## User Flows

### Flow 1: View Tier Configuration
1. User selects program from dropdown
2. Page loads KPI summary cards + comparison matrix
3. Matrix shows all tiers (columns) with all config dimensions (rows)
4. User scrolls vertically through sections: Basic Details -> Eligibility -> Renewal -> Downgrade -> Benefits

### Flow 2: Edit a Tier (implied by edit icon)
1. User clicks pencil icon on a tier column header
2. Expected: opens tier detail/edit view or inline editing (BRD says inline for simple fields, aiRa for structural)
3. **No dedicated tier edit form is shown in the screenshots** -- the creation/edit flow is not captured

### Flow 3: Navigate to Benefits
1. User clicks "Manage benefits" link in the Benefits section
2. Navigates to standalone Benefits listing page (S-5)

### Flow 4: Filter Tiers
1. User clicks "Filter Tiers" button
2. Expected: filter panel or dropdown (not shown in screenshots)
3. API must support: status filter, potentially name search
