> Source: /Users/baljeetsingh/Downloads/Tiers_Benefits_PRD_v2_AiLed.docx.pdf
> Format: PDF
> Extracted: 2026-04-01

---

# PRODUCT REQUIREMENTS DOCUMENT — Tiers & Benefits
## aiRa-Powered Conversational Configuration

**Document Owner**: Surabhi Geetey
**Version**: 2.0 (March 2026)
**Status**: Active — In Build (AI-Led Pod)
**Audience**: Engineering Pod — Karan, Anuj, Kiran, Bhavik, Mohit

---

## 1. Executive Summary

The Tiers & Benefits module is the structural backbone of every loyalty program running on the platform. It defines who a member is, what they earn, what they deserve, and when they move. Despite this centrality, the configuration experience today is deeply broken; fragmented across six screens, invisible in its logic, and inaccessible to the people who matter most: the marketers and program managers who design loyalty strategies.

This document defines the complete product requirements for a ground-up rebuild of the Tiers & Benefits configuration experience on the UI, with two parallel investments:
- A modern, high-signal listing and management interface that gives program teams instant visibility into their tier hierarchy, member distribution, and configuration health — without requiring engineering involvement.
- aiRa, Capillary's conversational AI assistant, embedded directly into the configuration flow; making complex loyalty logic feel as simple as describing it in plain English.

---

## 2. Document Philosophy & AI-Led Pod Contract

This PRD is structured to serve the AI-Led Pod model, not a traditional PM-to-Engineering handoff.

### 2.1 What This Document Is
- A deep articulation of the problem space and user intent — the "why" that no ticket can hold.
- A clear vision of the desired experience — the "what" at the product level.
- A set of interface philosophy options — the "how" at a strategic level, for the team to decide together.
- An API-first contract surface — the data layer that both the UI and aiRa will depend on.

### 2.2 What This Document Is Not
- A complete UI spec — the pod uses this to generate solution options using AI, then critiques and refines.
- A list of tickets — tickets are auto-generated from the problem briefs in each section.
- A final answer — the interface philosophy sections explicitly present two models. The pod decides.

**Pod Grooming Instruction**: For each Epic below: (1) Read the Problem Brief aloud. (2) Ask your LLM to generate 2 solution approaches given the constraints. (3) Critique the approaches as a team in 1 session (max 45 min). (4) Generate tickets from the chosen approach. The PM does not write the tickets — the AI does, and the team reviews.

---

## 3. The Problem Statement

### 3.1 The Core Problem

Loyalty tiers are the most consequential configuration in any loyalty program. They determine which members get elevated status, what benefits they receive, how long they keep that status, and what happens when they fall short. Get tiers wrong, and you lose members. Get benefits wrong, and you burn margin.

Today, a program manager at one of Capillary's enterprise customers — let's call her Maya — spends approximately 45 minutes to create a single tier from scratch. Not because the business logic is complicated in her mind — she knows exactly what she wants. It takes 45 minutes because:

| Maya's Intent | What UI Forces Her To Do |
|---|---|
| I want a Gold tier that activates when a member spends $500 in a calendar year. | Navigate to Program Tiers → Advanced Settings → KPI Config → Set threshold → Save → Navigate back → Configure upgrade schedule → Navigate to expiry settings → Set renewal period → Navigate back again. |
| I want Gold members to drop to Silver if they don't requalify — but give them a 30-day grace period. | Open a separate downgrade config screen. Understand cryptic "validate downgrade condition for return transaction" toggle. Hope the grace period field exists. It doesn't. File a support ticket. |
| I want to attach a "Welcome Gift" benefit — 500 bonus points on tier entry. | Exit the Tier config flow entirely. Navigate to V3 Promotions. Create a new promotion. Map it back to the tier manually. Pray the IDs match. |
| I want to see all my tiers side by side to make sure the logic is consistent. | Open 4 browser tabs. Take notes in Excel. Compare mentally. Make a mistake. |

This is not a UX polish problem. This is a structural problem. The current Garuda/cap-loyalty-ui TiersView is a read-only list of tier cards fetched from a single API. There is no comparison, no configuration entry point, no benefit linkage, and no guidance. It is, essentially, a debug view.

### 3.2 Why This Problem Exists

The current tier configuration was built incrementally by product and engineering, for power users such as internal config teams. Settings were added as features were requested — each living in the most convenient technical location, not the most coherent user location. The result:
- Global tier settings (KPI type, upgrade sequence, validity periods) live in one screen.
- Individual tier config (name, threshold, downgrade target) live in another.
- Renewal and expiry logic is buried three levels deep.
- Benefits are in an entirely separate product with no visual link to tiers.
- Maker-checker approval flows happen over Slack and email — not in the platform.
- There is no simulation. You configure, you publish, and you hope.

The deeper issue: tiers are not isolated objects. Changing a tier threshold cascades — it can demote members, trigger communications, affect point valuations, and break renewal logic. Today, there is no way for Maya to understand this impact before she saves. She is flying blind at 30,000 feet.

### 3.3 Who Suffers and How

**Maya — The Loyalty Program Manager**
- Context: Mid-level ops role at a retail enterprise. Manages 3-4 loyalty programs. Non-technical but highly analytical.
- Weekly time lost: ~4 hours navigating between screens, verifying configs, and handling support escalations caused by config errors.
- Biggest frustration: "I know exactly what I want the tier to do. I just can't find where to tell the system."
- Consequence: Launches are delayed. Programs go live with errors. Maya's confidence in the platform erodes. She starts doing config work in spreadsheets outside Garuda.

**Alex — The Loyalty Platform Admin / Approver**
- Context: Owns platform governance. Responsible for ensuring tier changes don't break live programs. Has sign-off authority.
- Weekly time lost: ~2 hours reviewing config changes via email screenshots and Slack threads. No audit trail. No confidence.
- Biggest frustration: "Someone changed a tier threshold last week and I found out when a customer complained. There's no approval process."
- Consequence: No maker-checker flow means risky changes go live unchecked. Compliance risk. Brand damage.

**Priya — The Data Analyst**
- Context: Tracks loyalty program health. Wants to correlate tier configuration changes with member behavior shifts.
- Weekly time lost: ~3 hours pulling tier data from multiple reports, cross-referencing with config screens.
- Biggest frustration: "I want to know how many members are in each tier right now — but that's in Analytics, and the config is in a completely different place."
- Consequence: Decisions are made on stale data. Config and analytics are disconnected worlds.

### 3.4 The Market Signal

This is not unique to Capillary. Enterprise loyalty platform evaluations in 2025-2026 consistently list unified tier management as a primary capability gap. Salesforce Loyalty Management, Antavo, and Braze all feature centralized tier comparison views. In recent enterprise RFPs, prospects have explicitly cited this gap as a reason to look elsewhere.

But here is what matters more than the competitive signal: Capillary processes millions of tier evaluations per day. The configuration that powers them should be as sophisticated as the computation beneath it. Right now, it is not. This is the gap we are closing.

### 3.5 Why Now

- Garuda (garuda-ui) is our new platform — built clean, with module federation, React 18, and atomic design. This is our one chance to get the architecture right before it hardens.
- The AI-Led Pod model means we can move 2-3x faster than traditional delivery if we get the problem framing right. This PRD is that framing.
- aiRa is production-ready as a side panel. The infrastructure exists. What's missing is the product layer that makes it intelligent about loyalty configuration.
- Enterprise deals are citing this gap. Every quarter we delay is a deal we lose.

---

## 4. Product Vision

By the end of this build, a loyalty program manager should be able to walk into work on Monday morning, open new UI, and within 90 seconds know: which tiers are live, how many members are in each, whether any configuration is at risk, and what they need to do about it — without touching a support ticket, a browser tab, or a spreadsheet.

And when they need to make a change — whether it's raising a tier threshold, adding a new benefit, or restructuring the downgrade logic — they should be able to describe it in plain language and watch it happen. With a preview. With an impact simulation. With an approver notified. All without leaving the screen they're on.

This is not a dashboard. This is a configuration intelligence layer.

**Long term vision statement**: Our vision is to evolve tier management from a configuration exercise into an intelligence-driven decision system. When brands design or modify their tier structures, the platform should guide them with insights on what effective tier programs look like, drawing from historical patterns and proven strategies. They should be able to simulate the potential ROI of new or modified tier structures before launching them, and continuously measure the actual value generated once the program is live. Over time, the system should help brands understand whether their tier setup is driving meaningful business impact and proactively recommend changes when it is not. Configuration management will remain a baseline capability, but the true value will come from enabling smarter decisions that help brands design, test, and optimize tier programs to achieve better outcomes.

### 4.1 The Desired State in Detail

**For the Listing Experience**
- One screen shows all tiers in a program — not as a list of cards, but as a comparative matrix. Every configuration dimension is visible side by side. Silver vs Gold vs Platinum — the logic is legible at a glance.
- KPI numbers live alongside configuration. Members in tier. Renewal rate. Upgrade velocity. Not in Analytics — right here, in context.
- Status is explicit. Active, Draft, Pending Approval, Stopped — each tier's lifecycle is visible. No guessing.
- Benefits are not in a separate product. They are linked to tiers inline — visible in the same view.

**For the Configuration Experience**
- Creating a tier begins with a conversation. Maya types what she wants. aiRa interprets the intent, confirms the logic, and renders a preview — all before a single form field is touched.
- Editing a tier threshold shows an impact preview: "This change will move an estimated 2,300 members from Gold to Silver at next evaluation. Notify them? Or Is that expected?" — before saving.
- Maker-checker is native. Every config change creates a pending record. Approvers are notified in-platform. The audit trail is automatic.
- Simulation mode lets Maya test a configuration change against historical data before it goes live. The result is a clear member distribution forecast.

**For Benefits**
- Benefits are first-class objects — not promotions attached to a tier as an afterthought. They have their own listing, categories, and lifecycle.
- Linking a benefit to a tier is a single action, not a cross-product navigation odyssey.
- aiRa can suggest benefits based on tier position: "For your Platinum tier, similar programs typically offer free shipping, early access, and a birthday bonus. Want me to set those up?"

---

## 5. Interface Philosophy — Two Models

This is a decision the pod needs to make together. Both options are valid. Both are designed. Here is the honest trade-off analysis.

### Option A: Hybrid Interface — Direct UI + aiRa for Complexity

**Pod Recommendation (Draft)**: This is the recommended starting model. It respects where users are today while introducing aiRa as a superpower — not a requirement. It also de-risks delivery: the direct UI path works without aiRa integration, giving the team parallel build paths.

**How It Works**
Every configuration action has two entry points:
- Direct UI path: For atomic changes — rename a tier, change a color, update a number. These are instant, inline edits. No conversation required. Fast, precise, immediately understandable.
- aiRa path: For structural changes — define eligibility logic, restructure downgrade flow, configure a new benefit category, simulate impact. These require reasoning. aiRa handles them conversationally.

The trigger for "go to aiRa" is the complexity of the intent, not the role of the user. A senior engineer and a junior marketer both use the direct UI for simple edits. Both use aiRa for complex restructuring. The system intelligently routes.

**Example User Journey — Hybrid**

| Step | Action | Interface |
|---|---|---|
| 1 | Maya opens the Tiers listing page | Comparison matrix loads. All tiers visible. KPIs at top. Status badges live. |
| 2 | She notices Gold's member count dropped 18% this month | Inline KPI chip on Gold tier header — no navigation needed. |
| 3 | She wants to understand Gold's renewal logic | Clicks "Renewal" row in the matrix. Expands inline. Boolean logic rendered in human-readable format. |
| 4 | She decides to change the renewal condition from $500 to $400 spend | Clicks the value. Inline edit for the number — direct UI path. |
| 5 | She wants to also add a grace period + notify at-risk members | This is complex. aiRa panel opens. "I want to add a 30-day grace and send a push notification 14 days before expiry." aiRa confirms and previews. |
| 6 | She reviews the impact simulation — 340 members affected | aiRa shows forecast inline in the panel. She approves. |
| 7 | She submits for approval | Maker-checker creates a pending record. Alex gets an in-platform notification. |

**When to Use Direct UI**
- Changing tier name, description, or color
- Updating a single numeric threshold
- Toggling a boolean setting (e.g., "Check expiry daily")
- Viewing/comparing tier configurations
- Filtering and searching benefits

**When aiRa Takes Over**
- Creating a tier from scratch
- Defining or restructuring eligibility logic (AND/OR conditions)
- Configuring downgrade flows and grace periods
- Setting up a new benefit category or linking multiple benefits
- Running impact simulations on proposed changes
- Resolving configuration conflicts flagged by the system

### Option B: Fully Conversational — aiRa as Primary Interface

**Important Context**: This model is more ambitious and more differentiated. It positions Capillary as a pioneer in conversational loyalty configuration. However, it carries higher delivery risk and requires more robust aiRa context-building before the UX feels trustworthy. Recommended for Phase 2 consideration once the Hybrid model establishes trust.

**How It Works**
The listing page becomes a read-only intelligence layer — a tier health dashboard. All configuration — from the simplest color change to the most complex eligibility restructure — happens through aiRa. There is no form. There is no field. There is a conversation.

aiRa has deep context: it knows the current program, all tier configurations, historical member behavior, benefit catalog, and common patterns from similar programs in the Capillary network. It makes suggestions, catches errors, warns about downstream impact, and proposes what Maya hasn't thought of yet.

**Example User Journey — Fully Conversational**

| Role | Action |
|---|---|
| Maya says | "I want to add a Platinum tier above Gold. Entry at $1,000 lifetime spend. 2-year validity. Upgrade bonus of 1,000 points on entry. Auto-renew if they hit $800 in the renewal year." |
| aiRa does | Parses intent. Confirms program context (currency: INR or USD? KPI: Lifetime spend = Lifetime Purchase value). Checks if $1,000 threshold is reachable given current member distribution. Generates a preview. Flags — "No downgrade target defined — what happens if a Platinum member misses renewal?" Waits for confirmation before creating. |
| Maya says | "Drop them to Gold with a 30-day grace." |
| aiRa does | Updates preview. Adds grace period. Estimates ~240 members will enter Platinum in first 3 months based on current Gold member spend patterns. Shows draft config for review. Submits for approval with one click. |

**Key Dependency**: Option B requires a robust aiRa Context Layer — a structured representation of the current program's loyalty configuration, member segments, benefit catalog, and historical evaluation data. Without this, aiRa's responses will be generic and untrustworthy. The Context Layer is defined in Section 8.

---

## 6. User Personas — In Depth

### 6.1 Maya — Loyalty Program Manager (Primary)

| Attribute | Detail |
|---|---|
| Who she is | She has run loyalty programs for 3-4 years. She knows the business logic cold — engagement windows, tier thresholds, member psychology. She is not a developer. She does not want to be. |
| What she needs from New Program UI | Speed and confidence. She needs to know that what she configures is what will happen — no surprises at the next evaluation cycle. She needs to find settings without a treasure hunt. She needs to see impact before she commits. |
| Her relationship with aiRa | Skeptical at first. Will adopt if aiRa saves her time on the first interaction. Will advocate internally once she trusts it. Will abandon it if it hallucinates a config she didn't intend. |
| Success looks like | Maya creates a new tier in under 15 minutes, including benefit linkage and maker-checker submission. She does it without reading documentation. |
| Failure looks like | Maya creates the tier but makes an error in the downgrade logic. The error isn't caught until 2,000 members are incorrectly demoted. She files a support ticket and loses confidence in the platform. |

### 6.2 Alex — Loyalty Platform Admin / Approver (Secondary)

| Attribute | Detail |
|---|---|
| Who he is | Owns the governance layer. He approves changes before they go live. He is technical enough to understand config logic but his job is risk management, not configuration. |
| What he needs from New Program UI | A clear, auditable record of what changed, who changed it, and what the downstream impact is. He does not want to receive a Slack message with a screenshot. He wants to click "Approve" or "Reject" inside the platform. |
| His relationship with aiRa | aiRa should surface the impact summary in his approval view — he should not have to re-derive it. "Maya changed Gold renewal threshold from $500 to $400. Estimated 1,200 members who would have been downgraded will now retain Gold. Total liability increase: ~$8,000 in benefit cost." That is what he needs to approve intelligently. |
| Success looks like | Approval cycle time drops from 2+ days (Slack/email) to under 2 hours in-platform. |

### 6.3 Priya — Data Analyst (Tertiary)

| Attribute | Detail |
|---|---|
| Who she is | She tracks program health. She wants to correlate config changes with behavioral outcomes. She is the person who will tell the CMO whether the tier restructure worked. |
| What she needs from New Program UI | Configuration history linked to KPI snapshots. Not just "what is the config now" — "what was it on October 15th, and what happened to member upgrade rates in the 30 days after." |
| Her relationship with aiRa | She will ask aiRa questions in natural language: "Which tier has the highest renewal rate?" "Show me how member distribution changed after we lowered the Gold threshold in Q3." This requires the Context Layer to have historical data. |

---

## 7. Product Epics & Scope

| Epic | Name | Description | Priority | Phase |
|---|---|---|---|---|
| E1 | Tier Intelligence | Complete revamp of tier listing, comparison matrix, creation, editing, maker-checker, change logs, and simulation mode | P0 | 1 |
| E2 | Benefits as a Product | Standalone benefits module: listing, creation, categories, custom fields, tier linkage, maker-checker, state lifecycle | P0 | 1 |
| E3 | aiRa Configuration Layer | Conversational assistant with deep context layer for tier/benefit creation, impact simulation, and generative UI | P0 | 1 |
| E4 | API-First Contract | Self-reliant APIs for all create/edit operations — validations in API, not UI. Powers both direct UI and aiRa flows | P0 | 1 |

### 7.1 Epic 1 — Tier Intelligence

**Problem Brief — E1**: Today's TiersView.js renders a flat list of TierDetailsCard components. There is no comparison, no configuration entry, no KPI data, no status visibility, and no action surface. A program manager who wants to understand their full tier structure must open multiple screens. We need to replace this with a configuration intelligence layer that makes the full tier hierarchy legible, comparable, and actionable from a single surface.

**E1-US1: Tier Listing with Comparison Matrix**
As Maya, I want to see all tiers in my program displayed side by side so I can immediately understand the structure, identify gaps, and spot inconsistencies.
- The listing page renders a comparative matrix — rows are configuration dimensions, columns are tiers.
- Configuration dimensions visible in the matrix: Basic Info (name, description, color, status), Eligibility Criteria (KPI, threshold, upgrade type, schedule), Validity & Renewal (period, renewal condition, renewal schedule, renewal duration), Downgrade Logic (downgrade-to tier, schedule, grace period), Benefits (linked benefits grouped by category, count).
- KPI header: Total tiers, Active tiers, Total members across all tiers, Tiers pending approval.
- Status badges per tier: Active (green), Draft (grey), Pending Approval (amber), Stopped (red).
- Focus Mode: clicking a tier header highlights that column across all rows. Non-focused columns dim. Focus persists on scroll.
- aiRa button in header: "Configure with aiRa" launches the aiRa panel with tier context preloaded.

**E1-US2: Tier Creation**
As Maya, I want to create a new tier — either through a guided form flow or through aiRa — without needing to understand the underlying data model.
- Entry point: "+ Add Tier" button in page header.
- Two paths presented on click: "Start with aiRa (Recommended)" and "Manual Configuration".
- aiRa path: Opens side panel with context: "I can see your program currently has Silver, Gold, Platinum. What tier would you like to add?" Walks through intent collection → config preview → impact estimate → approval submission.
- Manual path: Stepper form (Global Settings → Tier Config → Eligibility → Renewal → Downgrade → Benefits → Review). Each step has inline help text generated from the current program context.
- Required fields: Name, Eligibility KPI type, Eligibility threshold, Validity period, Downgrade target (or "None" for base tier).
- Optional fields: Description, Color, Upgrade schedule, Renewal condition, Renewal schedule, Nudge/communication config, Upgrade bonus.
- On save: if maker-checker is enabled for the program, creates a Draft. Submits to approval queue. Notifies approver.

**E1-US3: Tier Editing**
As Maya, I want to edit any aspect of an existing tier — inline for simple changes, or via aiRa for structural changes — with full impact visibility before I commit.
- Inline edit (direct UI path): clicking any value in the matrix that is a simple field (name, description, color, a single numeric threshold) enables inline editing without leaving the matrix.
- Structural edit (aiRa path): clicking the aiRa icon on a tier, or attempting to edit a field that has downstream dependencies (e.g., eligibility threshold, downgrade target), opens aiRa with context.
- Impact preview: any change to eligibility threshold, renewal condition, or downgrade logic triggers an impact estimate: "~2,300 members currently in Gold would be affected. 1,100 would maintain status. 1,200 would be queued for downgrade at next evaluation."
- Dirty state: unsaved changes are visually flagged. Navigating away prompts confirmation.

**E1-US4: Maker-Checker Approval Workflow**
As Alex, I want to review and approve every tier configuration change before it goes live — inside the platform, with full context, and a clear audit trail.
- Approval queue: a dedicated "Pending Approval" view shows all pending changes across Tiers and Benefits.
- Each pending item shows: what changed (diff view — old value vs new value), who requested it, when, and the aiRa-generated impact summary.
- Approver actions: Approve (change goes live immediately or at next evaluation cycle), Reject (with mandatory comment), Request Changes (returns to draft with comment).
- Email + in-platform notification to approver on submission.
- Audit log: every approval/rejection is recorded with timestamp, actor, and comment.

**E1-US5: Change Log**
As Priya, I want to see a complete history of every change made to tier configuration, who made it, when, and what it replaced.
- Change log accessible from tier header in the matrix (timeline icon).
- Each entry: timestamp, actor, field changed, old value → new value, approval status.
- Filterable by: date range, actor, field, approval status.
- Export: CSV or PDF for audit/reporting.

**E1-US6: Simulation Mode**
As Maya, I want to test a proposed tier configuration change against my current member base before publishing — so I can see the impact without risking a live program.
- Simulation entry: "Simulate" button in page header, or "Preview Impact" in aiRa panel.
- Simulation inputs: proposed changes to any tier config dimension.
- Simulation output: member distribution forecast — how many members in each tier before and after the change, at next evaluation.
- Visualization: bar chart showing current vs projected distribution per tier.
- Drill-down: export list of affected member IDs (with PII masking for non-admin roles).

### 7.2 Epic 2 — Benefits as a Product

**Problem Brief — E2**: Benefits today are not a product — they are promotions attached to a tier as an afterthought. There is no unified view of all benefits linked to a program. There is no lifecycle management for a benefit independent of the promotion it is backed by. There is no way to see "what does a Gold member get" without navigating to V3 Promotions and manually filtering. We need Benefits to be a first-class module in Garuda.

**E2-US1: Benefits Listing**
As Maya, I want to see all benefits configured for my program — organized by category, linked tier, and lifecycle state — from a single view.
- Benefits tab alongside Tiers in the page navigation.
- Listing: searchable, filterable table. Columns: Benefit Name, Category, Type, Linked Tier(s), Trigger Event, State (Active/Draft/Stopped), Last Modified.
- Category filters: Earning, Redemption, Coupon, Badge, Communication, Custom.
- Tier filter: filter benefits by which tier they are linked to.
- State filter: Active, Draft, Pending Approval, Stopped.
- Inline actions on hover: Edit, Duplicate, Deactivate, View Change Log.

**E2-US2: Benefit Creation**
As Maya, I want to create a new benefit and link it to one or more tiers — either through a form or through aiRa.
- Benefit types supported: Points Multiplier, Flat Points Award, Coupon Issuance, Badge Award, Free Shipping, Custom (via custom fields).
- Trigger events: Tier Upgrade, Tier Renewal, Transaction, Birthday, Manual.
- Tier linkage: multi-select — a benefit can be linked to multiple tiers with different parameter values per tier (e.g., Gold gets 2x multiplier, Platinum gets 3x).
- aiRa path: "I want to give Platinum members 3x points on every purchase" → aiRa maps this to a Points Multiplier benefit, confirms trigger, confirms tier, generates preview, submits.

**E2-US3: Custom Fields for Benefits**
As a program admin, I want to define custom attributes for a benefit that are specific to our business — so I can capture information that the standard benefit model does not support.
- Custom field types: Text, Number, Date, Dropdown (single/multi), Boolean, File URL.
- Custom fields are defined at the org level and are available across all benefits in the program.
- Custom field values per benefit are displayed in the benefit listing and detail view.
- aiRa is aware of custom field definitions and can ask for their values during benefit creation.

---

## 8. aiRa Integration — Detailed Design

### 8.1 What aiRa Needs to Know (The Context Layer)

aiRa is only as intelligent as the context it has. A generic LLM does not know your program. aiRa needs a structured context layer that gives it real-time awareness of the current program state. This is the most critical engineering investment in Epic 3.

| Context Dimension | What aiRa Knows |
|---|---|
| Program Config | Program ID, KPI type (current/lifetime points, spend, transactions), currency, evaluation schedule, global tier settings. |
| Current Tier Structure | All tier names, thresholds, upgrade types, validity periods, renewal conditions, downgrade targets, linked benefits. Full graph of tier relationships. |
| Member Distribution | Count of members in each tier. Upgrade/downgrade velocity (% moving up or down per month). Members at risk of downgrade (within 10% of renewal threshold). |
| Benefit Catalog | All benefits in the program: type, category, linked tiers, trigger events, active state. |
| Change History | Last 6 months of configuration changes. Correlated with KPI shifts (e.g., "After Gold threshold was lowered in Q3, upgrade rate increased 18%"). |
| Industry Patterns | Anonymized patterns from similar programs in the Capillary network. Used for benchmarking and suggestions ("Programs like yours typically set Platinum at 3x the Gold threshold"). |

### 8.2 aiRa Capability Catalog

**Capability 1: Intent-Driven Tier Creation**
Maya: "Create a Diamond tier above Platinum. Entry at 10,000 lifetime points. 18-month validity. Downgrade to Platinum if they miss renewal."
aiRa: Parses intent → Maps to API fields → Checks if 10,000 is a sensible threshold given current Platinum threshold and member distribution → Generates preview → Flags missing fields (renewal condition not specified) → Confirms → Creates draft → Submits for approval.

**Capability 2: Impact Simulation**
Maya: "What happens if I lower the Silver threshold from $300 to $200?"
aiRa: Runs simulation against current member base → Returns: "1,847 members currently in Bronze will qualify for Silver. Silver member count increases from 4,200 to 6,047. Estimated incremental benefit cost: $42,000/year at current redemption rates. Downgrade impact: none."

**Capability 3: Configuration Validation**
aiRa proactively flags configuration issues:
- "Your Silver downgrade target is currently set to Bronze, but Bronze is your base tier with no downgrade. Members who fall below Bronze will exit the program. Is that intended?"
- "The renewal condition for Gold (Spend $400) is higher than the upgrade condition for Silver (Spend $300). Members upgrading from Silver to Gold will face a harder renewal condition immediately. This is unusual — do you want to review?"
- "No expiry communication is configured for Platinum. Members won't be warned before their tier expires."

**Capability 4: Benefit Recommendation**
When Maya is creating a new tier or reviewing an existing one, aiRa can suggest benefits based on tier position and industry patterns:
"For your Platinum tier, programs of similar scale typically offer: (1) Free standard shipping on all orders, (2) Early access to new collections (48-hour window), (3) Birthday bonus — 500 points. Want me to set up any of these?"

**Capability 5: Natural Language Queries**
Priya: "Which tier has the lowest renewal rate?"
aiRa: Queries context layer → "Gold has the lowest renewal rate at 61%. Silver is at 74%, Platinum at 88%. Gold's renewal threshold ($500 spend in 12 months) may be set too high relative to typical member spend patterns."

### 8.3 aiRa UI/UX Patterns

**Side Panel Architecture**
- aiRa lives in a slide-in side panel (420px wide) that overlays the listing page without replacing it. The listing page stays visible — Maya can refer to it while talking to aiRa.
- Panel header shows aiRa's name, status, and current context ("Viewing: Gold Tier | Demoground Program").
- Context bar below header shows what aiRa knows about the current scope — a blue ribbon: "I can see your full tier structure and current member distribution."

**Generative UI — Inline Rich Components**
aiRa does not just return text. It generates interactive components inline in the chat:
- Config chips: clickable options for discrete choices ("Which KPI should this tier use? [Current Points] [Lifetime Points] [Lifetime Spend] [Transaction Count]")
- Preview tables: structured preview of the configuration aiRa is about to create — rendered as a mini table in the chat.
- Impact bars: horizontal bar charts showing member distribution before/after a proposed change.
- Action buttons: "Save as Draft", "Submit for Approval", "Modify", "Discard" — all inline in the conversation.

**Quick Reply Chips**
After each aiRa message, a row of quick-reply chips gives Maya one-click shortcuts to common responses: "Looks good", "Change something", "Show impact", "Add a benefit", "Not now".

---

## 9. Success Metrics

These metrics define what "done" means. The pod should review them monthly after launch and use them to prioritize the next iteration.

| Metric | Baseline Today | Target (6 months) | Owner |
|---|---|---|---|
| Time to create a tier (end-to-end) | ~45 minutes | < 15 min with aiRa; < 25 min manual | PM + Analytics |
| Time to create a benefit | ~30 minutes | < 10 min with aiRa; < 20 min manual | PM + Analytics |
| Config error rate (wrong downgrade target, missing renewal, etc.) | High / unmeasured | < 5% of submitted configs flagged as erroneous | Engineering (aiRa validation) |
| Maker-checker cycle time | Manual — 2+ days via email/Slack | < 2 hours in-platform | PM + Product Ops |
| % of marketers using aiRa for tier creation | N/A (new) | > 60% within 90 days of launch | PM |
| Tier comparison view — time to answer "What is Gold's renewal condition?" | ~3-4 minutes (multiple screens) | < 30 seconds from listing page | PM + UX |
| Support tickets related to tier config confusion | Unmeasured (significant) | Reduce by 50% within 6 months | Product Ops + Support |
| Simulation use before config publish | N/A | > 40% of structural changes previewed via simulation | PM |

---

## 10. API-First Contract

All APIs must be self-reliant. Validation logic lives in the API — not in frontend form logic. This ensures that both the direct UI and aiRa call the same endpoints and receive the same validation feedback. Third-party integrations and future conversational interfaces work out of the box.

### 10.1 Core API Requirements
- Every create/edit API must return a structured validation error object (not a 500) when invalid config is submitted. Errors must be field-level, human-readable, and actionable.
- Impact estimation is an API endpoint, not a frontend calculation. aiRa calls it; the simulation UI calls it; they get the same result.
- Approval workflow events (submit, approve, reject) are API-driven, not UI state.
- The Context Layer for aiRa is served via a dedicated program context API — a structured JSON that represents the full current state of the program's tier/benefit configuration, member distribution, and change history.

### 10.2 Key Endpoints (High Level)

| Endpoint | Method | Purpose |
|---|---|---|
| /tiers | GET | List all tiers for a program with full config, KPIs, and linked benefits |
| /tiers | POST | Create a new tier. Full validation in API. Returns diff preview before confirming. |
| /tiers/{tierId} | PUT/PATCH | Update tier config. If maker-checker enabled, creates a pending record instead of updating live. |
| /tiers/{tierId}/simulate | POST | Simulate impact of proposed config change on current member base. |
| /tiers/approvals | GET/POST | List pending approval items; approve or reject a pending change. |
| /benefits | GET/POST | List all benefits; create a new benefit. |
| /benefits/{benefitId}/link | POST | Link a benefit to one or more tiers with tier-specific parameters. |
| /program/{programId}/context | GET | aiRa Context Layer API — returns full program state for AI consumption. |
| /aira/intent | POST | Accepts natural language intent string; returns structured config object + clarification questions. |

**AI-Led Pod Instruction — API Design Session**: Before writing any frontend code, the pod should run a dedicated API design session. Feed this PRD + the current loyalty codebase to the LLM. Ask it to generate the full OpenAPI spec for all endpoints above. Review as a team. Lock the contract. Then frontend and backend can build in parallel against the same contract.

---

## 11. Out of Scope — Phase 1

| Feature | Rationale for Deferral |
|---|---|
| Milestone / streak-based tier events | Requires separate data model. Planned for Phase 2 alongside Group Activities. |
| Benefits for coalition / subscription programs | Different entitlement model. Tracked separately. |
| Fully conversational interface (Option B) as primary | Deferred to Phase 2. Hybrid (Option A) ships first to build trust and gather usage data for aiRa. |
| Real-time member streaming | Daily snapshots sufficient for Phase 1. Live streaming requires significant infra investment. |
| Custom fields for Promotions | Tracked as a separate workstream. |
| Mobile / responsive layout | Desktop-first for now. Enterprise loyalty admins work on desktop. |

---

## 12. Open Questions for the Pod

| Question | Owner | Status |
|---|---|---|
| Does the program context API exist, or does it need to be built? What is the latency at p99? | Karan / Anuj | Open |
| Impact simulation — is this calculated in real-time or queued? What is the acceptable SLA for a simulation result? | Bhavik / Mohit | Open |
| Maker-checker: is this per-user-role or per-program? Who configures who the approvers are? | Surabhi | Open |
| Can a benefit be linked to multiple programs, or is it always scoped to one? | Anuj / Kiran | Open |
| Should aiRa handle multi-turn disambiguation (ask clarifying questions across multiple turns), or is each interaction single-turn? | aiRa Team | Open |
| Is the downgrade "validate on return transaction" toggle going to be surfaced in the new UI, or deprecated? | Surabhi | Open |

---

*End of Document*
*Garuda Loyalty Platform — Tiers & Benefits PRD v2.0 — Capillary Technologies*
