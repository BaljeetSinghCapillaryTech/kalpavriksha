Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL



PRODUCT REQUIREMENTS DOCUMENT
Garuda Loyalty Platform

Tiers & Benefits
aiRa-Powered Conversational Configuration

Document Owner              Version                      Status                 Audience
Surabhi Geetey              2.0 — New Age                Active — In Build      Engineering Pod
                            March 2026                   AI-Led Pod             Karan · Anuj · Kiran ·
                                                                                Bhavik · Mohit


  How to Use This Document
  This PRD is a living artifact for the AI-Led Pod. It is not a traditional handoff spec. It defines the
  problem space, user intent, interface philosophy, and API contracts. The pod uses this as the
  single source of truth during grooming — AI generates solution options, the team critiques and
  refines, and tickets are auto-generated. If you are reading this as an engineer, start with Section
  3 (Problem Statement) before jumping to epics.




Capillary Technologies | Internal Use OnlyPage 1 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

Table of Contents




Capillary Technologies | Internal Use OnlyPage 2 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

1. Executive Summary
The Tiers & Benefits module is the structural backbone of every loyalty program running on the Garuda
platform. It defines who a member is, what they earn, what they deserve, and when they move. Despite
this centrality, the configuration experience today is deeply broken — fragmented across six screens,
invisible in its logic, and inaccessible to the people who matter most: the marketers and program
managers who design loyalty strategy.

This document defines the complete product requirements for a ground-up rebuild of the Tiers &
Benefits configuration experience in Garuda, with two parallel investments:
   •​ A modern, high-signal listing and management interface that gives program teams instant visibility
      into their tier hierarchy, member distribution, and configuration health — without requiring
      engineering involvement.
   •​ aiRa, Capillary's conversational AI assistant, embedded directly into the configuration flow —
      making complex loyalty logic feel as simple as describing it in plain English.

This is not a dashboard for the Sales Kickoff. This is a permanent, central feature of the Garuda
platform — the way every future customer will configure tiers and benefits. We are building it once, and
building it right.




2. Document Philosophy & AI-Led Pod Contract
This PRD is structured to serve the AI-Led Pod model, not a traditional PM-to-Engineering handoff.
Here is how the pod should use this document:


2.1 What This Document Is
   •​ A deep articulation of the problem space and user intent — the "why" that no ticket can hold.
   •​ A clear vision of the desired experience — the "what" at the product level.
   •​ A set of interface philosophy options — the "how" at a strategic level, for the team to decide
      together.
   •​ An API-first contract surface — the data layer that both the UI and aiRa will depend on.


2.2 What This Document Is Not
   •​ A complete UI spec — the pod uses this to generate solution options using AI, then critiques and
      refines.
   •​ A list of tickets — tickets are auto-generated from the problem briefs in each section.
   •​ A final answer — the interface philosophy sections explicitly present two models. The pod
      decides.


  Pod Grooming Instruction
  For each Epic below: (1) Read the Problem Brief aloud. (2) Ask your LLM to generate 2 solution
  approaches given the constraints. (3) Critique the approaches as a team in 1 session (max 45
  min). (4) Generate tickets from the chosen approach. The PM does not write the tickets — the AI
  does, and the team reviews.


Capillary Technologies | Internal Use OnlyPage 3 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL




Capillary Technologies | Internal Use OnlyPage 4 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

3. The Problem Statement
This section is the most important part of this document. Every product decision flows from it. Read it
carefully.



3.1 The Core Problem
Loyalty tiers are the most consequential configuration in any loyalty program. They determine which
members get elevated status, what benefits they receive, how long they keep that status, and what
happens when they fall short. Get tiers wrong, and you lose members. Get benefits wrong, and you
burn margin.

Today, a program manager at one of Capillary's enterprise customers — let's call her Maya — spends
approximately 45 minutes to create a single tier from scratch. Not because the business logic is
complicated in her mind — she knows exactly what she wants. It takes 45 minutes because:


 Maya's Intent                                      What Garuda Forces Her To Do

                                                    Navigate to Program Tiers → Advanced Settings
 I want a Gold tier that activates when a           → KPI Config → Set threshold → Save →
 member spends $500 in a calendar                   Navigate back → Configure upgrade schedule →
 year.                                              Navigate to expiry settings → Set renewal period
                                                    → Navigate back again.

                                                    Open a separate downgrade config screen.
 I want Gold members to drop to Silver if
                                                    Understand cryptic "validate downgrade condition
 they don't requalify — but give them a
                                                    for return transaction" toggle. Hope the grace
 30-day grace period.
                                                    period field exists. It doesn't. File a support ticket.

                                                    Exit the Tier config flow entirely. Navigate to V3
 I want to attach a "Welcome Gift" benefit
                                                    Promotions. Create a new promotion. Map it back
 — 500 bonus points on tier entry.
                                                    to the tier manually. Pray the IDs match.

 I want to see all my tiers side by side to         Open 4 browser tabs. Take notes in Excel.
 make sure the logic is consistent.                 Compare mentally. Make a mistake.


This is not a UX polish problem. This is a structural problem. The current Garuda/cap-loyalty-ui
TiersView is a read-only list of tier cards fetched from a single API. There is no comparison, no
configuration entry point, no benefit linkage, and no guidance. It is, essentially, a debug view.



3.2 Why This Problem Exists
The current tier configuration was built incrementally by engineering, for engineering. Settings were
added as features were requested — each living in the most convenient technical location, not the most
coherent user location. The result:
   •​ Global tier settings (KPI type, upgrade sequence, validity periods) live in one screen.
   •​ Individual tier config (name, threshold, downgrade target) live in another.
   •​ Renewal and expiry logic is buried three levels deep.

Capillary Technologies | Internal Use OnlyPage 5 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

   •​ Benefits are in an entirely separate product (V3 Promotions) with no visual link to tiers.
   •​ Maker-checker approval flows happen over Slack and email — not in the platform.
   •​ There is no simulation. You configure, you publish, and you hope.

The deeper issue: tiers are not isolated objects. Changing a tier threshold cascades — it can demote
members, trigger communications, affect point valuations, and break renewal logic. Today, there is no
way for Maya to understand this impact before she saves. She is flying blind at 30,000 feet.



3.3 Who Suffers and How


Maya — The Loyalty Program Manager
 Context                           Mid-level ops role at a retail enterprise. Manages 3-4 loyalty
                                   programs. Non-technical but highly analytical.
 Weekly time lost                  ~4 hours navigating between screens, verifying configs, and
                                   handling support escalations caused by config errors.
 Biggest frustration               "I know exactly what I want the tier to do. I just can't find where to
                                   tell the system."
 Consequence                       Launches are delayed. Programs go live with errors. Maya's
                                   confidence in the platform erodes. She starts doing config work in
                                   spreadsheets outside Garuda.



Alex — The Loyalty Platform Admin / Approver
 Context                           Owns platform governance. Responsible for ensuring tier changes
                                   don't break live programs. Has sign-off authority.
 Weekly time lost                  ~2 hours reviewing config changes via email screenshots and
                                   Slack threads. No audit trail. No confidence.
 Biggest frustration               "Someone changed a tier threshold last week and I found out when
                                   a customer complained. There's no approval process."
 Consequence                       No maker-checker flow means risky changes go live unchecked.
                                   Compliance risk. Brand damage.



Priya — The Data Analyst
 Context                           Tracks loyalty program health. Wants to correlate tier configuration
                                   changes with member behavior shifts.
 Weekly time lost                  ~3 hours pulling tier data from multiple reports, cross-referencing
                                   with config screens.
 Biggest frustration               "I want to know how many members are in each tier right now —
                                   but that's in Analytics, and the config is in a completely different
                                   place."



Capillary Technologies | Internal Use OnlyPage 6 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 Consequence                       Decisions are made on stale data. Config and analytics are
                                   disconnected worlds.



3.4 The Market Signal
This is not unique to Capillary. Enterprise loyalty platform evaluations in 2025-2026 consistently list
unified tier management as a primary capability gap. Salesforce Loyalty Management, Antavo, and
Braze all feature centralized tier comparison views. In recent enterprise RFPs, prospects have explicitly
cited this gap as a reason to look elsewhere.

But here is what matters more than the competitive signal: Capillary processes millions of tier
evaluations per day. The configuration that powers them should be as sophisticated as the computation
beneath it. Right now, it is not. This is the gap we are closing.



3.5 Why Now
   •​ Garuda (garuda-ui) is our new platform — built clean, with module federation, React 18, and
      atomic design. This is our one chance to get the architecture right before it hardens.
   •​ The AI-Led Pod model means we can move 2-3x faster than traditional delivery if we get the
      problem framing right. This PRD is that framing.
   •​ aiRa is production-ready as a side panel. The infrastructure exists. What's missing is the product
      layer that makes it intelligent about loyalty configuration.
   •​ Enterprise deals are citing this gap. Every quarter we delay is a deal we lose.




Capillary Technologies | Internal Use OnlyPage 7 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

4. Product Vision
By the end of this build, a loyalty program manager should be able to walk into work on Monday
morning, open Garuda, and within 90 seconds know: which tiers are live, how many members are in
each, whether any configuration is at risk, and what they need to do about it — without touching a
support ticket, a browser tab, or a spreadsheet.

And when they need to make a change — whether it's raising a tier threshold, adding a new benefit, or
restructuring the downgrade logic — they should be able to describe it in plain language and watch it
happen. With a preview. With an impact simulation. With an approver notified. All without leaving the
screen they're on.

This is not a dashboard. This is a configuration intelligence layer.



4.1 The Desired State in Detail
For the Listing Experience
   •​ One screen shows all tiers in a program — not as a list of cards, but as a comparative matrix.
      Every configuration dimension is visible side by side. Silver vs Gold vs Platinum — the logic is
      legible at a glance.
   •​ KPI numbers live alongside configuration. Members in tier. Renewal rate. Upgrade velocity. Not in
      Analytics — right here, in context.
   •​ Status is explicit. Active, Draft, Pending Approval, Stopped — each tier's lifecycle is visible. No
      guessing.
   •​ Benefits are not in a separate product. They are linked to tiers inline — visible in the same view.


For the Configuration Experience
   •​ Creating a tier begins with a conversation. Maya types what she wants. aiRa interprets the intent,
      confirms the logic, and renders a preview — all before a single form field is touched.
   •​ Editing a tier threshold shows an impact preview: "This change will move an estimated 2,300
      members from Gold to Silver at next evaluation. Notify them?" — before saving.
   •​ Maker-checker is native. Every config change creates a pending record. Approvers are notified
      in-platform. The audit trail is automatic.
   •​ Simulation mode lets Maya test a configuration change against historical data before it goes live.
      The result is a clear member distribution forecast.


For Benefits
   •​ Benefits are first-class objects — not promotions attached to a tier as an afterthought. They have
      their own listing, categories, and lifecycle.
   •​ Linking a benefit to a tier is a single action, not a cross-product navigation odyssey.
   •​ aiRa can suggest benefits based on tier position: "For your Platinum tier, similar programs
      typically offer free shipping, early access, and a birthday bonus. Want me to set those up?"




Capillary Technologies | Internal Use OnlyPage 8 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

5. Interface Philosophy — Two Models
This is a decision the pod needs to make together. Both options are valid. Both are designed. Here is
the honest trade-off analysis.



Option A: Hybrid Interface — Direct UI + aiRa for Complexity
  Pod Recommendation (Draft)
  This is the recommended starting model. It respects where users are today while introducing
  aiRa as a superpower — not a requirement. It also de-risks delivery: the direct UI path works
  without aiRa integration, giving the team parallel build paths.



How It Works
Every configuration action has two entry points:
     •​ Direct UI path: For atomic changes — rename a tier, change a color, update a number. These are
        instant, inline edits. No conversation required. Fast, precise, immediately understandable.
     •​ aiRa path: For structural changes — define eligibility logic, restructure downgrade flow, configure
        a new benefit category, simulate impact. These require reasoning. aiRa handles them
        conversationally.

The trigger for "go to aiRa" is the complexity of the intent, not the role of the user. A senior engineer and
a junior marketer both use the direct UI for simple edits. Both use aiRa for complex restructuring. The
system intelligently routes.


Example User Journey — Hybrid
 Step       Action                            Interface

            Maya opens the Tiers              Comparison matrix loads. All tiers visible. KPIs at top.
 1
            listing page                      Status badges live.

            She notices Gold's
                                              Inline KPI chip on Gold tier header — no navigation
 2          member count dropped
                                              needed.
            18% this month

            She wants to understand           Clicks "Renewal" row in the matrix. Expands inline.
 3
            Gold's renewal logic              Boolean logic rendered in human-readable format.

            She decides to change
                                              Clicks the value. Inline edit for the number — direct UI
 4          the renewal condition
                                              path.
            from $500 to $400 spend

            She wants to also add a           This is complex. aiRa panel opens. "I want to add a
 5          grace period + notify             30-day grace and send a push notification 14 days
            at-risk members                   before expiry." aiRa confirms and previews.




Capillary Technologies | Internal Use OnlyPage 9 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 Step        Action                           Interface

             She reviews the impact
 6           simulation — 340                 aiRa shows forecast inline in the panel. She approves.
             members affected

                                              Maker-checker creates a pending record. Alex gets an
 7           She submits for approval
                                              in-platform notification.



When to Use Direct UI
     •​ Changing tier name, description, or color
     •​ Updating a single numeric threshold
     •​ Toggling a boolean setting (e.g., "Check expiry daily")
     •​ Viewing/comparing tier configurations
     •​ Filtering and searching benefits


When aiRa Takes Over
     •​ Creating a tier from scratch
     •​ Defining or restructuring eligibility logic (AND/OR conditions)
     •​ Configuring downgrade flows and grace periods
     •​ Setting up a new benefit category or linking multiple benefits
     •​ Running impact simulations on proposed changes
     •​ Resolving configuration conflicts flagged by the system



Option B: Fully Conversational — aiRa as Primary Interface
  Important Context
  This model is more ambitious and more differentiated. It positions Capillary as a pioneer in
  conversational loyalty configuration. However, it carries higher delivery risk and requires more
  robust aiRa context-building before the UX feels trustworthy. Recommended for Phase 2
  consideration once the Hybrid model establishes trust.



How It Works
The listing page becomes a read-only intelligence layer — a tier health dashboard. All configuration —
from the simplest color change to the most complex eligibility restructure — happens through aiRa.
There is no form. There is no field. There is a conversation.

aiRa has deep context: it knows the current program, all tier configurations, historical member behavior,
benefit catalog, and common patterns from similar programs in the Capillary network. It makes
suggestions, catches errors, warns about downstream impact, and proposes what Maya hasn't thought
of yet.


Example User Journey — Fully Conversational

Capillary Technologies | Internal Use OnlyPage 10 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 Maya says                    "I want to add a Platinum tier above Gold. Entry at $1,000 lifetime
                              spend. 2-year validity. Upgrade bonus of 1,000 points on entry.
                              Auto-renew if they hit $800 in the renewal year."
 aiRa does                    Parses intent. Confirms program context (currency: INR or USD? KPI:
                              Lifetime spend = Lifetime Purchase value). Checks if $1,000 threshold
                              is reachable given current member distribution. Generates a preview.
                              Flags: "No downgrade target defined — what happens if a Platinum
                              member misses renewal?" Waits for confirmation before creating.
 Maya says                    "Drop them to Gold with a 30-day grace."
 aiRa does                    Updates preview. Adds grace period. Estimates ~240 members will
                              enter Platinum in first 3 months based on current Gold member spend
                              patterns. Shows draft config for review. Submits for approval with one
                              click.



Key Dependency
Option B requires a robust aiRa Context Layer — a structured representation of the current program's
loyalty configuration, member segments, benefit catalog, and historical evaluation data. Without this,
aiRa's responses will be generic and untrustworthy. The Context Layer is defined in Section 8.




Capillary Technologies | Internal Use OnlyPage 11 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

6. User Personas — In Depth
6.1 Maya — Loyalty Program Manager (Primary)
 Who she is                        She has run loyalty programs for 3-4 years. She knows the
                                   business logic cold — engagement windows, tier thresholds,
                                   member psychology. She is not a developer. She does not want to
                                   be.
 What she needs from               Speed and confidence. She needs to know that what she
 Garuda                            configures is what will happen — no surprises at the next
                                   evaluation cycle. She needs to find settings without a treasure hunt.
                                   She needs to see impact before she commits.
 Her relationship with             Skeptical at first. Will adopt if aiRa saves her time on the first
 aiRa                              interaction. Will advocate internally once she trusts it. Will abandon
                                   it if it hallucinates a config she didn't intend.
 Success looks like                Maya creates a new tier in under 15 minutes, including benefit
                                   linkage and maker-checker submission. She does it without reading
                                   documentation.
 Failure looks like                Maya creates the tier but makes an error in the downgrade logic.
                                   The error isn't caught until 2,000 members are incorrectly demoted.
                                   She files a support ticket and loses confidence in the platform.



6.2 Alex — Loyalty Platform Admin / Approver (Secondary)
 Who he is                         Owns the governance layer. He approves changes before they go
                                   live. He is technical enough to understand config logic but his job is
                                   risk management, not configuration.
 What he needs from                A clear, auditable record of what changed, who changed it, and
 Garuda                            what the downstream impact is. He does not want to receive a
                                   Slack message with a screenshot. He wants to click "Approve" or
                                   "Reject" inside the platform.
 His relationship with             aiRa should surface the impact summary in his approval view — he
 aiRa                              should not have to re-derive it. "Maya changed Gold renewal
                                   threshold from $500 to $400. Estimated 1,200 members who would
                                   have been downgraded will now retain Gold. Total liability increase:
                                   ~$8,000 in benefit cost." That is what he needs to approve
                                   intelligently.
 Success looks like                Approval cycle time drops from 2+ days (Slack/email) to under 2
                                   hours in-platform.



6.3 Priya — Data Analyst (Tertiary)
 Who she is                        She tracks program health. She wants to correlate config changes
                                   with behavioral outcomes. She is the person who will tell the CMO
                                   whether the tier restructure worked.


Capillary Technologies | Internal Use OnlyPage 12 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 What she needs from               Configuration history linked to KPI snapshots. Not just "what is the
 Garuda                            config now" — "what was it on October 15th, and what happened to
                                   member upgrade rates in the 30 days after."
 Her relationship with             She will ask aiRa questions in natural language: "Which tier has the
 aiRa                              highest renewal rate?" "Show me how member distribution
                                   changed after we lowered the Gold threshold in Q3." This requires
                                   the Context Layer to have historical data.




Capillary Technologies | Internal Use OnlyPage 13 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

7. Product Epics & Scope
                                                                                         Priorit   Pha
 Epic           Name                         Description
                                                                                         y         se

                                             Complete revamp of tier listing,
                                             comparison matrix, creation, editing,
 E1             Tier Intelligence                                                        P0        1
                                             maker-checker, change logs, and
                                             simulation mode

                                             Standalone benefits module: listing,
                Benefits as a
 E2                                          creation, categories, custom fields, tier   P0        1
                Product
                                             linkage, maker-checker, state lifecycle

                                             Conversational assistant with deep
                aiRa Configuration
 E3                                          context layer for tier/benefit creation,    P0        1
                Layer
                                             impact simulation, and generative UI

                                             Self-reliant APIs for all create/edit
 E4             API-First Contract           operations — validations in API, not UI.    P0        1
                                             Powers both direct UI and aiRa flows



7.1 Epic 1 — Tier Intelligence
Problem Brief (for AI-Led Grooming)
  Problem Brief — E1
  Today's TiersView.js renders a flat list of TierDetailsCard components. There is no comparison,
  no configuration entry, no KPI data, no status visibility, and no action surface. A program
  manager who wants to understand their full tier structure must open multiple screens. We need
  to replace this with a configuration intelligence layer that makes the full tier hierarchy legible,
  comparable, and actionable from a single surface.



E1-US1: Tier Listing with Comparison Matrix
As Maya, I want to see all tiers in my program displayed side by side so I can immediately understand
the structure, identify gaps, and spot inconsistencies.
   •​ The listing page renders a comparative matrix — rows are configuration dimensions, columns are
      tiers.
   •​ Configuration dimensions visible in the matrix: Basic Info (name, description, color, status),
      Eligibility Criteria (KPI, threshold, upgrade type, schedule), Validity & Renewal (period, renewal
      condition, renewal schedule, renewal duration), Downgrade Logic (downgrade-to tier, schedule,
      grace period), Benefits (linked benefits grouped by category, count).
   •​ KPI header: Total tiers, Active tiers, Total members across all tiers, Tiers pending approval.
   •​ Status badges per tier: Active (green), Draft (grey), Pending Approval (amber), Stopped (red).
   •​ Focus Mode: clicking a tier header highlights that column across all rows. Non-focused columns
      dim. Focus persists on scroll.
   •​ aiRa button in header: "Configure with aiRa" launches the aiRa panel with tier context preloaded.



Capillary Technologies | Internal Use OnlyPage 14 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

E1-US2: Tier Creation
As Maya, I want to create a new tier — either through a guided form flow or through aiRa — without
needing to understand the underlying data model.
   •​ Entry point: "+ Add Tier" button in page header.
   •​ Two paths presented on click: "Start with aiRa (Recommended)" and "Manual Configuration".
   •​ aiRa path: Opens side panel with context: "I can see your program currently has Silver, Gold,
      Platinum. What tier would you like to add?" Walks through intent collection → config preview →
      impact estimate → approval submission.
   •​ Manual path: Stepper form (Global Settings → Tier Config → Eligibility → Renewal → Downgrade
      → Benefits → Review). Each step has inline help text generated from the current program
      context.
   •​ Required fields: Name, Eligibility KPI type, Eligibility threshold, Validity period, Downgrade target
      (or "None" for base tier).
   •​ Optional fields: Description, Color, Upgrade schedule, Renewal condition, Renewal schedule,
      Nudge/communication config, Upgrade bonus.
   •​ On save: if maker-checker is enabled for the program, creates a Draft. Submits to approval
      queue. Notifies approver.


E1-US3: Tier Editing
As Maya, I want to edit any aspect of an existing tier — inline for simple changes, or via aiRa for
structural changes — with full impact visibility before I commit.
   •​ Inline edit (direct UI path): clicking any value in the matrix that is a simple field (name, description,
      color, a single numeric threshold) enables inline editing without leaving the matrix.
   •​ Structural edit (aiRa path): clicking the aiRa icon on a tier, or attempting to edit a field that has
      downstream dependencies (e.g., eligibility threshold, downgrade target), opens aiRa with context.
   •​ Impact preview: any change to eligibility threshold, renewal condition, or downgrade logic triggers
      an impact estimate: "~2,300 members currently in Gold would be affected. 1,100 would maintain
      status. 1,200 would be queued for downgrade at next evaluation."
   •​ Dirty state: unsaved changes are visually flagged. Navigating away prompts confirmation.


E1-US4: Maker-Checker Approval Workflow
As Alex, I want to review and approve every tier configuration change before it goes live — inside the
platform, with full context, and a clear audit trail.
   •​ Approval queue: a dedicated "Pending Approval" view shows all pending changes across Tiers
      and Benefits.
   •​ Each pending item shows: what changed (diff view — old value vs new value), who requested it,
      when, and the aiRa-generated impact summary.
   •​ Approver actions: Approve (change goes live immediately or at next evaluation cycle), Reject
      (with mandatory comment), Request Changes (returns to draft with comment).
   •​ Email + in-platform notification to approver on submission.
   •​ Audit log: every approval/rejection is recorded with timestamp, actor, and comment.


E1-US5: Change Log
As Priya, I want to see a complete history of every change made to tier configuration, who made it,
when, and what it replaced.
   •​ Change log accessible from tier header in the matrix (timeline icon).
   •​ Each entry: timestamp, actor, field changed, old value → new value, approval status.
Capillary Technologies | Internal Use OnlyPage 15 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

   •​ Filterable by: date range, actor, field, approval status.
   •​ Export: CSV or PDF for audit/reporting.


E1-US6: Simulation Mode
As Maya, I want to test a proposed tier configuration change against my current member base before
publishing — so I can see the impact without risking a live program.
   •​ Simulation entry: "Simulate" button in page header, or "Preview Impact" in aiRa panel.
   •​ Simulation inputs: proposed changes to any tier config dimension.
   •​ Simulation output: member distribution forecast — how many members in each tier before and
      after the change, at next evaluation.
   •​ Visualization: bar chart showing current vs projected distribution per tier.
   •​ Drill-down: export list of affected member IDs (with PII masking for non-admin roles).



7.2 Epic 2 — Benefits as a Product
Problem Brief (for AI-Led Grooming)
  Problem Brief — E2
  Benefits today are not a product — they are promotions attached to a tier as an afterthought.
  There is no unified view of all benefits linked to a program. There is no lifecycle management for
  a benefit independent of the promotion it is backed by. There is no way to see "what does a Gold
  member get" without navigating to V3 Promotions and manually filtering. We need Benefits to be
  a first-class module in Garuda.



E2-US1: Benefits Listing
As Maya, I want to see all benefits configured for my program — organized by category, linked tier, and
lifecycle state — from a single view.
   •​ Benefits tab alongside Tiers in the page navigation.
   •​ Listing: searchable, filterable table. Columns: Benefit Name, Category, Type, Linked Tier(s),
      Trigger Event, State (Active/Draft/Stopped), Last Modified.
   •​ Category filters: Earning, Redemption, Coupon, Badge, Communication, Custom.
   •​ Tier filter: filter benefits by which tier they are linked to.
   •​ State filter: Active, Draft, Pending Approval, Stopped.
   •​ Inline actions on hover: Edit, Duplicate, Deactivate, View Change Log.


E2-US2: Benefit Creation
As Maya, I want to create a new benefit and link it to one or more tiers — either through a form or
through aiRa.
   •​ Benefit types supported: Points Multiplier, Flat Points Award, Coupon Issuance, Badge Award,
      Free Shipping, Custom (via custom fields).
   •​ Trigger events: Tier Upgrade, Tier Renewal, Transaction, Birthday, Manual.
   •​ Tier linkage: multi-select — a benefit can be linked to multiple tiers with different parameter values
      per tier (e.g., Gold gets 2x multiplier, Platinum gets 3x).
   •​ aiRa path: "I want to give Platinum members 3x points on every purchase" → aiRa maps this to a
      Points Multiplier benefit, confirms trigger, confirms tier, generates preview, submits.

Capillary Technologies | Internal Use OnlyPage 16 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL



E2-US3: Custom Fields for Benefits
As a program admin, I want to define custom attributes for a benefit that are specific to our business —
so I can capture information that the standard benefit model does not support.
   •​ Custom field types: Text, Number, Date, Dropdown (single/multi), Boolean, File URL.
   •​ Custom fields are defined at the org level and are available across all benefits in the program.
   •​ Custom field values per benefit are displayed in the benefit listing and detail view.
   •​ aiRa is aware of custom field definitions and can ask for their values during benefit creation.




Capillary Technologies | Internal Use OnlyPage 17 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

8. aiRa Integration — Detailed Design
8.1 What aiRa Needs to Know (The Context Layer)
aiRa is only as intelligent as the context it has. A generic LLM does not know your program. aiRa needs
a structured context layer that gives it real-time awareness of the current program state. This is the
most critical engineering investment in Epic 3.


 Context Dimension                 What aiRa Knows

                                   Program ID, KPI type (current/lifetime points, spend,
 Program Config
                                   transactions), currency, evaluation schedule, global tier settings.

                                   All tier names, thresholds, upgrade types, validity periods,
 Current Tier Structure            renewal conditions, downgrade targets, linked benefits. Full
                                   graph of tier relationships.

                                   Count of members in each tier. Upgrade/downgrade velocity (%
 Member Distribution               moving up or down per month). Members at risk of downgrade
                                   (within 10% of renewal threshold).

                                   All benefits in the program: type, category, linked tiers, trigger
 Benefit Catalog
                                   events, active state.

                                   Last 6 months of configuration changes. Correlated with KPI
 Change History                    shifts (e.g., "After Gold threshold was lowered in Q3, upgrade
                                   rate increased 18%").

                                   Anonymized patterns from similar programs in the Capillary
 Industry Patterns                 network. Used for benchmarking and suggestions ("Programs
                                   like yours typically set Platinum at 3x the Gold threshold").



8.2 aiRa Capability Catalog
Capability 1: Intent-Driven Tier Creation
Maya: "Create a Diamond tier above Platinum. Entry at 10,000 lifetime points. 18-month validity.
Downgrade to Platinum if they miss renewal."
aiRa: Parses intent → Maps to API fields → Checks if 10,000 is a sensible threshold given current
Platinum threshold and member distribution → Generates preview → Flags missing fields (renewal
condition not specified) → Confirms → Creates draft → Submits for approval.


Capability 2: Impact Simulation
Maya: "What happens if I lower the Silver threshold from $300 to $200?"
aiRa: Runs simulation against current member base → Returns: "1,847 members currently in Bronze
will qualify for Silver. Silver member count increases from 4,200 to 6,047. Estimated incremental benefit
cost: $42,000/year at current redemption rates. Downgrade impact: none."




Capillary Technologies | Internal Use OnlyPage 18 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

Capability 3: Configuration Validation
aiRa proactively flags configuration issues:
   •​ "Your Silver downgrade target is currently set to Bronze, but Bronze is your base tier with no
      downgrade. Members who fall below Bronze will exit the program. Is that intended?"
   •​ "The renewal condition for Gold (Spend $400) is higher than the upgrade condition for Silver
      (Spend $300). Members upgrading from Silver to Gold will face a harder renewal condition
      immediately. This is unusual — do you want to review?"
   •​ "No expiry communication is configured for Platinum. Members won't be warned before their tier
      expires."


Capability 4: Benefit Recommendation
When Maya is creating a new tier or reviewing an existing one, aiRa can suggest benefits based on tier
position and industry patterns:
"For your Platinum tier, programs of similar scale typically offer: (1) Free standard shipping on all
orders, (2) Early access to new collections (48-hour window), (3) Birthday bonus — 500 points. Want
me to set up any of these?"


Capability 5: Natural Language Queries
Priya: "Which tier has the lowest renewal rate?"
aiRa: Queries context layer → "Gold has the lowest renewal rate at 61%. Silver is at 74%, Platinum at
88%. Gold's renewal threshold ($500 spend in 12 months) may be set too high relative to typical
member spend patterns."



8.3 aiRa UI/UX Patterns
Side Panel Architecture
   •​ aiRa lives in a slide-in side panel (420px wide) that overlays the listing page without replacing it.
      The listing page stays visible — Maya can refer to it while talking to aiRa.
   •​ Panel header shows aiRa's name, status, and current context ("Viewing: Gold Tier | Demoground
      Program").
   •​ Context bar below header shows what aiRa knows about the current scope — a blue ribbon: "I
      can see your full tier structure and current member distribution."


Generative UI — Inline Rich Components
aiRa does not just return text. It generates interactive components inline in the chat:
   •​ Config chips: clickable options for discrete choices ("Which KPI should this tier use? [Current
      Points] [Lifetime Points] [Lifetime Spend] [Transaction Count]")
   •​ Preview tables: structured preview of the configuration aiRa is about to create — rendered as a
      mini table in the chat.
   •​ Impact bars: horizontal bar charts showing member distribution before/after a proposed change.
   •​ Action buttons: "Save as Draft", "Submit for Approval", "Modify", "Discard" — all inline in the
      conversation.




Capillary Technologies | Internal Use OnlyPage 19 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

Quick Reply Chips
After each aiRa message, a row of quick-reply chips gives Maya one-click shortcuts to common
responses: "Looks good", "Change something", "Show impact", "Add a benefit", "Not now".




Capillary Technologies | Internal Use OnlyPage 20 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

9. Success Metrics
These metrics define what "done" means. The pod should review them monthly after launch and use
them to prioritize the next iteration.


 Metric                              Baseline Today       Target (6 months)         Owner

 Time to create a tier               ~45 minutes          < 15 min with aiRa;       PM + Analytics
 (end-to-end)                                             < 25 min manual
 Time to create a benefit            ~30 minutes          < 10 min with aiRa;       PM + Analytics
                                                          < 20 min manual
 Config error rate (wrong            High / unmeasured    < 5% of submitted         Engineering (aiRa
 downgrade target, missing                                configs flagged as        validation)
 renewal, etc.)                                           erroneous
 Maker-checker cycle time            Manual — 2+ days     < 2 hours                 PM + Product Ops
                                     via email/Slack      in-platform
 % of marketers using aiRa           N/A (new)            > 60% within 90           PM
 for tier creation                                        days of launch
 Tier comparison view —              ~3-4 minutes         < 30 seconds from         PM + UX
 time to answer "What is             (multiple screens)   listing page
 Gold's renewal condition?"
 Support tickets related to          Unmeasured           Reduce by 50%             Product Ops +
 tier config confusion               (significant)        within 6 months           Support
 Simulation use before               N/A                  > 40% of structural       PM
 config publish                                           changes previewed
                                                          via simulation




10. API-First Contract
All APIs must be self-reliant. Validation logic lives in the API — not in frontend form logic. This ensures
that both the direct UI and aiRa call the same endpoints and receive the same validation feedback.
Third-party integrations and future conversational interfaces work out of the box.



10.1 Core API Requirements
   •​ Every create/edit API must return a structured validation error object (not a 500) when invalid
      config is submitted. Errors must be field-level, human-readable, and actionable.
   •​ Impact estimation is an API endpoint, not a frontend calculation. aiRa calls it; the simulation UI
      calls it; they get the same result.
   •​ Approval workflow events (submit, approve, reject) are API-driven, not UI state.
   •​ The Context Layer for aiRa is served via a dedicated program context API — a structured JSON
      that represents the full current state of the program's tier/benefit configuration, member
      distribution, and change history.



Capillary Technologies | Internal Use OnlyPage 21 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

10.2 Key Endpoints (High Level)
 Endpoint                   Method        Purpose

                                          List all tiers for a program with full config, KPIs, and linked
 /tiers                     GET
                                          benefits

                                          Create a new tier. Full validation in API. Returns diff
 /tiers                     POST
                                          preview before confirming.

                            PUT/PAT       Update tier config. If maker-checker enabled, creates a
 /tiers/{tierId}
                            CH            pending record instead of updating live.

 /tiers/{tierId}/simulat                  Simulate impact of proposed config change on current
                            POST
 e                                        member base.

                            GET/PO        List pending approval items; approve or reject a pending
 /tiers/approvals
                            ST            change.

                            GET/PO
 /benefits                                List all benefits; create a new benefit.
                            ST

 /benefits/{benefitId}                    Link a benefit to one or more tiers with tier-specific
                            POST
 /link                                    parameters.

 /program/{programI                       aiRa Context Layer API — returns full program state for AI
                            GET
 d}/context                               consumption.

                                          Accepts natural language intent string; returns structured
 /aira/intent               POST
                                          config object + clarification questions.


  AI-Led Pod Instruction — API Design Session
  Before writing any frontend code, the pod should run a dedicated API design session. Feed this
  PRD + the current loyalty codebase to the LLM. Ask it to generate the full OpenAPI spec for all
  endpoints above. Review as a team. Lock the contract. Then frontend and backend can build in
  parallel against the same contract.




11. Out of Scope — Phase 1
 Feature                                     Rationale for Deferral

 Milestone / streak-based tier               Requires separate data model. Planned for Phase 2
 events                                      alongside Group Activities.

 Fully conversational interface              Deferred to Phase 2. Hybrid (Option A) ships first to
 (Option B) as primary                       build trust and gather usage data for aiRa.

                                             Daily snapshots sufficient for Phase 1. Live streaming
 Real-time member streaming
                                             requires significant infra investment.


Capillary Technologies | Internal Use OnlyPage 22 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 Feature                                     Rationale for Deferral

 Custom fields for Promotions                Tracked as a separate workstream.




12. Open Questions for the Pod

 Question                                                 Owner                     Status

 Does the program context API exist, or does it
                                                          Karan / Anuj              Open
 need to be built? What is the latency at p99?

 Impact simulation — is this calculated in
 real-time or queued? What is the acceptable              Bhavik / Mohit            Open
 SLA for a simulation result?

 Maker-checker: is this per-user-role or
 per-program? Who configures who the                      Surabhi / Swati           Open
 approvers are?

 Can a benefit be linked to multiple programs,
                                                          Anuj / Kiran              Open
 or is it always scoped to one?

 Should aiRa handle multi-turn disambiguation
 (ask clarifying questions across multiple                aiRa Team                 Open
 turns), or is each interaction single-turn?

 Is the downgrade "validate on return
 transaction" toggle going to be surfaced in the          Surabhi                   Open
 new UI, or deprecated?




Capillary Technologies | Internal Use OnlyPage 23 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

Epic 3 — Subscription Programs

  Problem Brief — E3
  Subscription programs exist in Capillary today but are configured through a fragmented,
  low-fidelity interface. There is no unified listing view, no comparison across subscription plans,
  no meaningful benefit-to-subscription linkage visible to program managers, and no AI assistance
  for configuration. Benefits attached to a subscription are invisible at setup time — the marketer
  must navigate to a separate promotions module to link them. With paid subscriptions now live
  and multi-tier subscription logic emerging, the configuration surface must be rebuilt to match the
  quality standard of the Tiers module. This epic delivers a first-class Subscriptions module inside
  the Garuda platform — a listing view, a creation and editing flow (both manual and
  aiRa-assisted), and direct benefit linkage within the subscription context.




E3 — Overview: What We Are Building
The Subscriptions module adds a dedicated track inside the program configuration UI. It sits alongside
the Tiers and Benefits tabs and gives program managers a single, coherent interface to:
    •​   View all subscription programs across active, draft, and scheduled states
    •​   Create and edit subscription programs through either a guided manual form or an aiRa-assisted
         conversational flow
    •​   Attach benefits directly to a subscription at creation time — with linked tier awareness when the
         subscription is tier-based
    •​   Manage pricing for paid plans, with enrollment-level price capture
    •​   Set program-level expiry, reminder communications, and custom metadata fields


Two subscription models are supported and must be accounted for in every screen, flow, and API:

 Model                   Description                      Tier Behavior              Examples
 Tier-Based              Membership that grants or        Activates a designated     Premium Monthly
 Subscription            locks the member into a          tier on enrollment. Tier   → Gold tier. Black
                         specific loyalty tier for the    is protected during        Elite → Elite tier.
                         duration of the subscription.    active subscription. On
                                                          expiry or cancellation,
                                                          tier may downgrade per
                                                          configured rule.​
                                                          ​
                                                          Subscription can be
                                                          linked to an existing
                                                          tier, or can have a
                                                          separate new tier
 Non-Tier                Membership that grants           No tier link. Benefits     Student Pass → 2
 Subscription            access to a set of benefits      are standalone             benefits, no tier.
                         without affecting the member's   entitlements configured    Car Wash VIP →
                         loyalty tier.                    directly on the            wash credits, no
                                                          subscription.              tier change.




Capillary Technologies | Internal Use OnlyPage 24 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

E3-US1 — Subscription Listing View
As a program manager, I want to see all subscription programs for my loyalty program from a
single listing view, so I can assess their status, subscriber counts, pricing, and benefits at a
glance.


LISTING PAGE — HEADER STATISTICS
The listing page displays four summary stat cards in the page header (matching the prototype
screenshots):
    •​    Total Subscriptions — total count of all subscription programs regardless of state
    •​    Active — count of programs with Status = Active (shown in green)
    •​    Scheduled — count of programs with Status = Scheduled (shown in blue)
    •​    Total Subscribers — aggregate subscriber count across all active subscriptions


LISTING TABLE — COLUMNS

 Column                Description               Sortabl   Notes
                                                 e
 Subscription          Program name +            Yes       Click name to open detail / edit view
                       truncated description
                       (2 lines max)
 Status                Pill badge: Active        Yes       Filter by status via Status filter chip
                       (green), Draft (gray),
                       Scheduled (blue),
                       Paused (amber),
                       Expired (red)
 Price                 Formatted as              No        Blank if no price set
                       currency/period (e.g.,
                       RM 50/month, RM
                       500/year, Free)
 Benefits              Gift icon + count chip    No        See benefits modal spec below
                       (e.g., 'View (4)').
                       Clicking opens
                       Benefits modal.
 Subscribers           Count of active           Yes       Sortable descending by default
                       enrolled members
 Last Modified         Date of last              Yes       Format: Mon DD, YYYY
 date and              configuration change
 Modified by
 Row Actions           Three-dot menu: Edit,     No        Deactivate only for Active subscriptions
                       Duplicate, Deactivate
                       / Archive, View
                       Change Log



FILTER & VIEW CONTROLS
    •​    Status filter chip: multi-select — Active, Draft, Scheduled, Paused, Expired. The prototype
          shows 'Status 1' indicating one filter is applied; chip count updates accordingly.

Capillary Technologies | Internal Use OnlyPage 25 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

    •​   Group filter chip: filter by subscription group tag. Group tags are admin-defined.
    •​   Search bar: free-text search across subscription name and description.
    •​   View toggle: Table (default) and Grouped views. Grouped view organises subscriptions by their
         Group tag.
    •​   '+ Add Subscription' button: primary CTA in top-right corner. Opens the create flow.


BENEFITS MODAL (LINKED TO SUBSCRIPTION)
When the user clicks the 'View (N)' chip in the Benefits column, a modal appears showing all benefits
linked to that subscription. This mirrors the screenshot showing 'Premium Monthly Benefits'.
    •​   Modal header: gift icon + '{Subscription Name} Benefits'
    •​   Subtitle: 'Benefits included with this subscription'
    •​   If subscription is tier-based: display a tier indicator pill at the top (e.g., Linked Tier: Gold —
         shown as a gold dot + tier name, as per prototype screenshot 4)
    •​   Benefit list: each benefit on its own card row with a green active dot indicator and benefit name
    •​   Modal is read-only from the listing view. To edit benefits, the user must enter the edit flow.



E3-US2 — Create & Edit Subscription Flow
As a program manager, I want to create or edit a subscription program through either a guided
form or through aiRa, so that I can configure the program efficiently regardless of whether I
know the exact settings upfront.


  Design Principle
  The create and edit flow mirrors the aiRa-first philosophy of the Tiers module. Two paths are
  always available: (1) Manual form — step-by-step guided configuration for users who know what
  they want. (2) aiRa path — conversational creation for users who describe intent in natural
  language. Both paths produce the same output: a structured subscription program record
  submitted for approval or saved as draft.



ENTRY POINTS
    •​   Click '+ Add Subscription' from listing page → opens Create flow (blank form)
    •​   Click subscription name in listing → opens detail view with 'Edit' button in header
    •​   Row actions three-dot menu → 'Edit' → opens Edit flow (pre-populated form)
    •​   Row actions three-dot menu → 'Duplicate' → opens Create flow pre-populated with cloned data,
         name appended with ' (Copy)'


STEP 1 — PROGRAM BASICS (ACCORDION: ALWAYS OPEN FIRST)
Corresponds to the first accordion panel in the prototype, rendered in the slide-in panel. Fields:
    •​   Name (required): text input. 'Program name helps in uniquely identifying the subscription
         program'
    •​   Description (optional): multi-line text input. 'Write a few words explaining what the program is
         about'
    •​   Duration (required): numeric value + unit dropdown (Days / Months / Years). 'Select the duration
         of this program'

Capillary Technologies | Internal Use OnlyPage 26 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

    •​   Subscription Type toggle (new — not in old prototype): Tier-Based | Non-Tier. Default: Non-Tier.
         Changing this toggle shows/hides the tier configuration in Step 3.
    •​   Price (optional): decimal amount + currency dropdown (ISO 4217). Label: 'Subscription price per
         cycle'. If left blank, program is treated as free.
    •​   'Next' CTA advances to Step 2. Validation: Name and Duration required before advancing.


STEP 2 — EXPIRY & ADDITIONAL INFORMATION (ACCORDION: COLLAPSED UNTIL STEP 1 COMPLETE)
Corresponds to 'Expiry and additional information' accordion section in prototype.
    •​   Program-level expiry date (optional): date picker. Overrides individual enrollment duration when
         set.
    •​   Restrict to one active program per member (toggle): when ON, member cannot hold more than
         one subscription simultaneously. Powered by EMF ENABLE_PARTNER_PROGRAM_LINKING
         setting.
    •​   Migrate on expiry: dropdown — 'No migration' | 'Migrate to program…' (select target program)
    •​   If Tier-Based: Linked Tier selector — dropdown of available tiers in the program. Required when
         Tier-Based is selected.
    •​   If Tier-Based: Tier downgrade on exit toggle — when ON, member's tier downgrades on
         subscription expiry or cancellation. Requires a downgrade target tier to be selected.


STEP 3 — BENEFITS (ACCORDION: + ICON UNTIL OPENED)
This section replaces the old 'No promotions selected' placeholder. Benefits are configured directly
within the subscription create/edit flow.
    •​   Section header: '+ Benefits' with count badge once benefits are added (e.g., 'Benefits (4)')
    •​   If Non-Tier Subscription: shows a flat list of available benefit templates. Program manager
         selects which benefits to include. Each selected benefit shows a configuration chip for its key
         value (e.g., '15% off all purchases').
    •​   If Tier-Based Subscription: benefit selection is pre-filtered by the linked tier's configured benefit
         categories. The tier's benefits appear as selectable cards. Program manager can add, remove,
         or override values for this subscription context.
    •​   'Add Benefit' button: opens a benefit picker panel (inline search + category filter)
    •​   Linked benefits appear in a card list showing: benefit name, category type icon, configured
         value summary, active state dot
    •​   For each benefit card: 'Remove' action (trash icon) and 'Edit value' action (pencil icon)


STEP 4 — REMINDERS (ACCORDION: + ICON UNTIL OPENED)
    •​   Up to 5 reminder notifications before expiry
    •​   Each reminder: Days before expiry (numeric) + Channel selector (SMS / Email / Push)
    •​   '+ Add Reminder' link. 'Remove' icon per row.
    •​   Preview: timeline visualization showing when reminders fire relative to expiry date


STEP 5 — CUSTOM FIELDS (ACCORDION: + ICON UNTIL OPENED)
Custom fields added to a subscription program are stored at three levels:
    •​   META level — program metadata (static program-level attributes)
    •​   LINK level — captured at member enrollment time

Capillary Technologies | Internal Use OnlyPage 27 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

    •​   DELINK level — captured when a member is unenrolled
         ◦​ PAUSE and RESUME level fields are also supported for programs with pause-enabled
    •​   Custom field picker: multi-select from org-level defined custom fields. Filtered by field type
         compatibility.
    •​   aiRa can prompt for custom field values during conversational creation if field definitions are
         available.


FORM FOOTER — ACTIONS
    •​   Save as Draft: saves without submitting for approval. Subscription appears in listing with Draft
         status.
    •​   Submit for Approval: if maker-checker is enabled, routes to approval queue. Status = Pending
         Approval.
    •​   Cancel: discards unsaved changes with confirmation dialog ('Discard changes?').
    •​   For Edit flow: 'Save Changes' CTA. If maker-checker enabled, creates a pending version — live
         version remains active until approved.



E3-US3 — aiRa-Assisted Subscription Creation & Editing
As a program manager, I want to describe the subscription I want in plain language and have
aiRa configure it for me — asking clarifying questions where needed — so I can launch a new
subscription faster than filling in a form.


AIRA ENTRY POINT FOR SUBSCRIPTIONS
    •​   The aiRa panel (420px side panel) is accessible from the Subscriptions listing page via the aiRa
         button in the top navigation, or via the 'Create with aiRa' option in the '+ Add Subscription'
         button dropdown.
    •​   aiRa context bar shows: 'Viewing: Subscriptions | [Program Name]'
    •​   aiRa is aware of: all existing subscription programs, available tiers in the program, configured
         benefit categories, org-level custom field definitions.


AIRA SUBSCRIPTION CAPABILITIES

Capability S1 — Intent-Driven Subscription Creation
Example: 'Create a monthly premium subscription for RM 50 that links to the Gold tier and gives
members 15% off all purchases, free shipping, and early access to sales.'
aiRa: Parses intent → Identifies: duration (monthly), price (RM 50), tier link (Gold), 3 benefits → Maps
benefits to configured categories where possible → Flags: 'Early Access to Sales is not a configured
benefit category in this program. Should I create it, or skip it?' → Generates preview chip showing full
configuration → Offers: Save as Draft | Submit for Approval | Modify.


Capability S2 — Subscription Configuration Validation
aiRa proactively flags configuration issues during creation:
    •​   'This subscription links to Gold tier. Gold tier currently has a downgrade path to Silver. If you
         want tier-exit downgrade to also trigger on subscription cancellation, you should enable the Tier
         Downgrade on Exit toggle.'

Capillary Technologies | Internal Use OnlyPage 28 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

    •​   'No renewal reminder is configured. Members will not receive a notification before their
         subscription expires. Do you want to add one?'
    •​   'A price has been set but no currency has been selected. Please specify the currency.'


Capability S3 — Benefit Recommendation for Subscriptions
When the program manager is creating a subscription without specifying benefits, aiRa can suggest
based on the tier and program context:
'For a Gold-tier monthly subscription at this price point, programs of similar scale typically offer: (1) 15%
discount on all purchases, (2) Free standard shipping, (3) Birthday bonus points. Want me to add any of
these?'


Capability S4 — Pricing Scenario Simulation
'What happens if I increase the Premium Monthly price from RM 50 to RM 65?' → aiRa: 'Currently
1,245 members are enrolled at RM 50. A price increase will not retroactively affect existing enrollments
— they will retain their effectivePrice of RM 50 unless you choose to migrate all subscribers to the new
price. New enrollments from the update date will carry RM 65. Do you want to migrate existing
subscribers?'


Capability S5 — Natural Language Subscription Queries
    •​   'Which subscription has the most subscribers?' → aiRa queries listing data and returns ranked
         summary.
    •​   'What benefits does the Black Elite subscription include?' → aiRa reads linked benefits and
         summarizes.
    •​   'Are there any subscriptions without a renewal reminder configured?' → aiRa scans all active
         subscriptions and flags gaps.


AIRA GENERATIVE UI — SUBSCRIPTION-SPECIFIC COMPONENTS
    •​   Subscription preview card: inline mini-card showing name, duration, price, linked tier (if any),
         and benefit count — rendered in the chat before confirmation
    •​   Benefit selection chips: clickable options for suggested benefits ('Add 15% Discount', 'Add Free
         Shipping', 'Skip')
    •​   Tier link selector: dropdown chip inline in chat if multiple tiers are available ('Which tier? [Gold]
         [Platinum] [Silver]')
    •​   Price confirmation pill: 'Set price to RM 50/month?' with [Confirm] and [Change] chips
    •​   Quick replies: 'Looks good', 'Add a benefit', 'Change price', 'Remove tier link', 'Save as draft',
         'Submit for approval'



E3-US4 — Subscription Lifecycle Management (Platform Config)
As a program admin, I want to manage the lifecycle states of subscription programs from the
configuration UI — including pausing, reactivating, and scheduling programs.


SUPPORTED LIFECYCLE STATES



Capillary Technologies | Internal Use OnlyPage 29 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 State              Description                       Transitions To           Visible To
 Draft              Configuration saved but not       Active, Archived         Admin only
                    yet published. No members
                    can enroll.
 Pending            Submitted for                     Active (on approval),    Admin + Approver
 Approval           maker-checker review.             Draft (on rejection)
 Scheduled          Approved but start date is in     Active (on start date)   All admins
                    the future.
 Active             Live. Members can enroll,         Paused, Expired,         All admins
                    renew, redeem benefits.           Archived
 Paused             Temporarily suspended.            Active                   All admins
                    Existing enrollments
                    maintain benefits; new
                    enrollments blocked.
 Expired            Past program-level expiry         Archived                 All admins
                    date. New enrollments
                    blocked. Existing
                    enrollments complete their
                    cycle.
 Archived           Permanently deactivated.          None                     Admin (read-only)
                    Read-only history preserved.



FUTURE-DATED ENROLLMENT (PENDING START DATE)
The platform supports queued/pending enrollments where a member's subscription start date is in the
future (e.g., renewal scheduled for next month). This maps to the PENDING state on the enrollment
record.
    •​    Program managers can view PENDING enrollment count per subscription in the listing row
          (future: Subscribers column sub-count).
    •​    A PENDING enrollment does not activate benefits until the membershipStartDate is reached.
    •​    Reschedule behavior: calling the link API again with a new future date cancels the old
          PENDING and creates a new one atomically.
    •​    The listing view shows a 'Scheduled' state indicator for subscriptions that have a future start
          date but no active enrollments yet.



E3-US5 — API Contract for Subscriptions

 Endpoint                            Meth      Purpose
                                     od
 POST                                POST      Enroll member. Supports future membershipStartDate for
 v2/partnerProgram/linkCustom                  PENDING state. Past dates rejected (400).
 er
 POST                                POST      Unenroll member. Can target PENDING or ACTIVE
 v2/partnerProgram/deLinkCust                  enrollment via updateType enum.
 omer


Capillary Technologies | Internal Use OnlyPage 30 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 Endpoint                            Meth      Purpose
                                     od
 POST                                POST      Update tier for tier-based subscription. Pause/resume
 v2/partnerProgram/customerP                   actions.
 artnerProgramUpdate
 GET                                 GET       Member's subscription history, benefit usage, lifecycle
 v2/partnerProgram/customerA                   events.
 ctivityHistories
 /subscriptions                      GET       List all subscription programs for a program with status,
                                               subscribers, benefits, pricing.
 /subscriptions                      POST      Create a new subscription program. Returns validation diff
                                               before confirming.
 /subscriptions/{id}                 PUT/      Edit subscription config. If maker-checker on, creates
                                     PATC      pending version.
                                     H
 /subscriptions/{id}/benefits        GET/      List or link benefits to a subscription program.
                                     POST
 /subscriptions/{id}/simulate        POST      Simulate price change or enrollment impact on current
                                               subscriber base.
 /subscriptions/approvals            GET/      Maker-checker: list pending subscription changes; approve
                                     POST      or reject.
 /program/{id}/context               GET       aiRa Context Layer — now includes subscription programs
                                               + subscriber counts.




Capillary Technologies | Internal Use OnlyPage 31 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

Epic 4 — Benefit Categories

BENEFITS AS A PRODUCT



Benefit Categories
Specification for the metadata grouping layer that organises benefit instances across tier programs

 Version: v2.0   Epic: E2 — Benefits as a Product   Status: Draft   Date: April 2026




1. Purpose & Scope
This document specifies the Benefit Category model for the Loyalty Platform. It defines what a benefit category
is, how categories relate to benefit instances and tiers, the functional requirements for each supported category
type, and the configuration rules that govern how values are set per tier.
Benefit categories are a metadata layer ,they do not hold reward values themselves. Instead, they provide a
standardised grouping structure that allows the platform to organise, filter, and display benefit instances in a
consistent way across all tier programs.

      In Scope

        • Definition of the benefit category model
        • Category types and their functional behaviour
        • Tier applicability and configuration rules
        • aiRa interaction patterns with categories




2. Data Model — Benefit Category
A benefit category is a top-level classification record. It contains no reward values itself; it acts as a parent to one
or more benefit instances, each of which is linked to a specific tier and carries the actual configured value.

Entity relationship: A Program contains one or more Tiers. A Benefit Category can have many Benefit
Instances. Each Benefit Instance is linked to exactly one Category and one Tier, and carries the reward
value applicable to that tier. When a trigger event fires for a member in a given tier, the platform looks up
the matching Benefit Instance and issues the reward.



      Field                          Type                            Constraint            Description


Capillary Technologies | Internal Use OnlyPage 32 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

     categoryId                   String (UUID)               System-generated               Unique identifier for the
                                                                                             category

     categoryName                 String                      Required, unique per           Display name (e.g.
                                                              program                        "Welcome Gift")

     categoryType                 Enum                        Required                       Functional type —
                                                                                             determines trigger and
                                                                                             value constraints

     description                  String                      Optional                       Free-text description
                                                                                             shown in admin UI

     triggerEvent                 Enum                        Derived from                   Event that causes
                                                              categoryType                   instances to fire (e.g.
                                                                                             TIER_ENTRY)

     tierApplicability            Array<TierId>               At least one tier required     Which tiers can have
                                                                                             configured instances

     isActive                     Boolean                     Default: true                  Inactive categories are
                                                                                             hidden from admin UI

     createdAt / updatedAt        Timestamp                   System-managed                 Audit fields




3. Examples of Category Types


     3.1 Welcome Gift                                                                      One-time · Coupon / Voucher

     TRIGGER TIER_ENTRY (first-time only)                     TIER APPLICABILITY Applicable to any tier that a member
                                                              can enter for the first time

     Attribute                                                Specification



     Configuration Rules                                      1. Issued once per member per tier — not re-issued
                                                              on subsequent entries after a downgrade​
                                                              2. Voucher amount is configurable per tier and may
                                                              differ across tiers​
                                                              3. Voucher validity window is set at the instance level

     Example: A program configures a higher voucher
     amount for its top tier than for its base tier, making
     tier attainment feel immediately rewarding.




Capillary Technologies | Internal Use OnlyPage 33 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL


     3.2 Upgrade Bonus Points                                                                         One-time · Points

     TRIGGER TIER_UPGRADE                                      TIER APPLICABILITY Not applicable to the lowest (entry)
                                                               tier; applies on any upward tier transition

     Attribute                                                 Specification



     Configuration Rules                                       1. Fires only on upward transitions (e.g. Bronze →
                                                               Silver); does not fire on re-entry after downgrade​
                                                               2. Point value is configurable per target tier — higher
                                                               tiers typically award more points​
                                                               3. Predefined instance value sets (e.g. 500, 1 000, 2
                                                               500 …) may be configured to guide setup

     Example: A member reaches a qualifying spend
     threshold and upgrades tiers. They immediately
     receive a bonus points reward that encourages
     them to return and redeem.




     3.3 Tier Badge                                                                            Persistent · Display asset

     TRIGGER TIER_ENTRY                                        TIER APPLICABILITY All tiers

     Attribute                                                 Specification



     Configuration Rules                                       1. Badge is awarded on each tier entry — including
                                                               re-entry after a downgrade​
                                                               2. Badges do not expire and are not removed when a
                                                               member downgrades​
                                                               3. Badge label and asset are configurable per tier

     Example: A member who achieved the top tier
     retains their badge as a visible status marker, even if
     they later drop to a lower tier.




     3.4 Renewal Bonus                                                                                Recurring · Points

     TRIGGER TIER_RENEWAL (successful requalification)         TIER APPLICABILITY Excludes the entry tier; applies to
                                                               tiers with a renewal/requalification mechanic

     Attribute                                                 Specification




Capillary Technologies | Internal Use OnlyPage 34 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

     Configuration Rules                                  1. Fires once per renewal cycle on successful tier
                                                          retention​
                                                          2. Does not fire if the member downgrades at the
                                                          renewal window​
                                                          3. Points are issued immediately after the renewal
                                                          event is confirmed

     Example: A member meets their renewal spend
     threshold just before period end and receives a
     points bonus, making the renewal moment feel
     rewarding rather than neutral.




     3.5 Loyalty Voucher                                                              Recurring · Coupon / Voucher

     TRIGGER PERIODIC / SCHEDULED                         TIER APPLICABILITY Typically restricted to higher tiers;
                                                          configuration determines which tiers receive it

     Attribute                                            Specification



     Configuration Rules                                  1. Issued on a configured schedule (not triggered by
                                                          member activity)​
                                                          2. Voucher amount and frequency are configurable
                                                          per tier​
                                                          3. Tiers without an active instance do not receive the
                                                          voucher

     Example: A loyalty program issues a periodic
     voucher exclusively to its top tier, creating a
     financial incentive to maintain that status.




     3.6 Earn Points                                                                     Ongoing multiplier · Points

     TRIGGER TRANSACTION (qualifying purchase)            TIER APPLICABILITY All tiers — the baseline earn rate for
                                                          the program

     Attribute                                            Specification



     Configuration Rules                                  1. Applied to every qualifying transaction while the
                                                          member holds the tier​
                                                          2. Higher tiers should have earn rates equal to or
                                                          greater than lower tiers​
                                                          3. Earn rate may be expressed as a multiplier (e.g. 1x,



Capillary Technologies | Internal Use OnlyPage 35 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

                                                           1.5x, 2x) or as points-per-currency-unit​
                                                           4. Minimum transaction value threshold is optional

     Example: A top-tier member earns points at twice
     the rate of a base-tier member on the same
     purchase — making higher tiers more valuable for
     frequent buyers.




     3.7 Birthday Bonus                                                                               Annual · Points

     TRIGGER BIRTHDAY (member date of birth)               TIER APPLICABILITY All tiers; point value scales with tier
                                                           level

     Attribute                                             Specification



     Configuration Rules                                   1. Fires once per calendar year on or around the
                                                           member's birthday​
                                                           2. awardsWindowDays allows the bonus to be issued
                                                           N days before/after the birthday date​
                                                           3. Points are non-transferable and subject to the
                                                           standard expiry policy

     Example: Top-tier members receive a meaningfully
     larger birthday bonus than base-tier members,
     reinforcing the emotional value of higher status.




     3.8 Priority Support                                                                Entitlement · Service access

     TRIGGER TIER_ACTIVE (persistent while tier is held)   TIER APPLICABILITY Typically restricted to premium tiers

     Attribute                                             Specification



     Configuration Rules                                   1. Entitlement is active as long as the member holds
                                                           the qualifying tier​
                                                           2. Entitlement is revoked immediately if the member
                                                           downgrades out of scope​
                                                           3. queuePriority value determines relative priority
                                                           within the support system

     Example: A premium-tier member contacting
     support is routed to a priority queue, receiving
     faster resolution than a standard-tier member.



Capillary Technologies | Internal Use OnlyPage 36 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL


     3.9 Free Shipping                                                         Conditional entitlement · Shipping waiver

     TRIGGER TRANSACTION (qualifying order above               TIER APPLICABILITY Excludes the entry tier; higher tiers
     threshold)                                                have a lower qualifying threshold

     Attribute                                                 Specification



     Configuration Rules                                       1. Shipping fee is waived when the order value meets
                                                               or exceeds minimumOrderValue​
                                                               2. Higher tiers should have a lower
                                                               minimumOrderValue than lower tiers​
                                                               3. Applies to standard shipping by default; express
                                                               shipping requires explicit configuration

     Example: A higher-tier member has a lower order
     threshold to qualify for free shipping, meaning
     more of their day-to-day purchases qualify.




5. Configuration Rules & Constraints
The following rules apply across all benefit category types when configuring instances.

Instance Completeness
  • A benefit instance must have all required value fields populated before it can be activated.
  • A category with no instances created is considered Inactive.

Maker-Checker
  • All benefit instance configuration changes follow the DRAFT → PENDING_APPROVAL → ACTIVE state machine.
  • Category creation (new categoryType) requires approval before instances can be created.
  • A change to an ACTIVE instance does not take effect until the new version is approved.




6. Acceptance Criteria
The following criteria must be met for the benefit category feature to be considered complete.

     ID                                    Criterion                               Description

     AC-01                                 Category Creation                       A program manager can create a
                                                                                   new benefit category by selecting a
                                                                                   categoryType and providing a
                                                                                   name.

Capillary Technologies | Internal Use OnlyPage 37 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

     AC-02                                 Instance Linking                For each created category, benefit
                                                                           instances can be created and linked
                                                                           to specific tiers with the relevant
                                                                           value fields populated.

     AC-03                                 aiRa Category Mapping           Given a natural-language
                                                                           description of a desired benefit
                                                                           (e.g. "give top-tier members bonus
                                                                           points on their birthday"), aiRa
                                                                           correctly identifies the
                                                                           categoryType and prompts for the
                                                                           required value fields.

     AC-04                                 Matrix View                     The Benefits dashboard shows a
                                                                           matrix view with all categories as
                                                                           rows, tiers as columns, and the
                                                                           configured value (or "Not
                                                                           configured") in each cell.




Capillary Technologies | Internal Use OnlyPage 38 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

Master Acceptance Criteria & Test Cases

  How to Use This Section
  This section contains all acceptance criteria and test cases for Epic 3 (Subscriptions) and Epic 4
  (Benefit Categories), supplementing the existing criteria for Epic 1 (Tiers) and Epic 2 (Benefits).
  Each row is a testable assertion that maps to a specific user story. Engineers should treat each
  AC row as a unit of work to be validated before marking a story as Done. QA should use the test
  cases as a regression suite after each deployment.




E3 — Subscriptions: Acceptance Criteria


E3-US1 — Subscription Listing View
 AC ID     Area            Given                   When                 Then
 AC-S      Listing —       A program with 20       The                  Header stat cards show: Total=20,
 01        Stats           subscriptions (16       subscriptions        Active=16 (green), Scheduled=2
                           active, 2               listing page loads   (blue), Total Subscribers=15,649
                           scheduled, 2 draft)
                           and 15,649 total
                           subscribers
 AC-S      Listing —       Active                  The listing page     All columns render: Subscription,
 02        Table           subscriptions exist     renders              Status, Price, Benefits,
                           with name, price,                            Subscribers, Group, Last Modified,
                           benefits, and                                Actions
                           subscriber counts
 AC-S      Listing —       Multiple                User applies         Only Active subscriptions are
 03        Status filter   subscriptions with      Status filter =      shown. Filter chip displays 'Status
                           different statuses      Active               1'. Total count updates to show
                                                                        filtered count.
 AC-S      Listing —       Subscriptions           User types           Only 'Premium Monthly' and
 04        Search          named 'Premium          'Premium' in         'Premium Annual' appear. Search
                           Monthly' and            search bar           is case-insensitive.
                           'Student Pass'
 AC-S      Listing —       Subscriptions with      User clicks          Subscriptions are visually grouped
 05        Grouped         groups: Premium,        'Grouped' toggle     by Group tag with group headers.
           View            Elite, Special                               Table toggle shows 'Table' as
                                                                        de-selected.
 AC-S      Benefits        Premium Monthly         User clicks 'View    Modal opens showing: 'Premium
 06        Modal           subscription with 4     (4)' chip in         Monthly Benefits' header, 'Linked
                           linked benefits and     Benefits column      Tier: Gold' pill (gold dot), and all 4
                           linked to Gold tier                          benefit names listed as cards with
                                                                        green active dots.
 AC-S      Benefits        Student Pass with       User clicks 'View    Modal opens. No tier indicator
 07        Modal —         2 benefits and no       (2)' chip            shown. Two benefit cards
           Non-Tier        tier link                                    displayed.



Capillary Technologies | Internal Use OnlyPage 39 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 AC ID     Area            Given                    When                  Then
 AC-S      Row Actions     An active                User selects          Edit flow opens pre-populated with
 08        — Edit          subscription             'Edit' from           the subscription's current
                                                    three-dot menu        configuration. All fields editable.
 AC-S      Row Actions     Any subscription         User selects          Create flow opens pre-populated
 09        — Duplicate                              'Duplicate' from      with cloned data. Name is
                                                    three-dot menu        appended with ' (Copy)'. Program
                                                                          is saved as Draft until explicitly
                                                                          published.
 AC-S      Sorting         Subscriptions with       User clicks           List sorts descending by
 10                        different subscriber     Subscribers           subscriber count. Second click
                           counts                   column header         sorts ascending. Sort indicator
                                                                          arrow displayed.



E3-US2 — Create & Edit Flow
 AC ID     Area               Given                  When                  Then
 AC-S      Create —           User is on             User clicks '+        Create flow slides in. Step 1
 11        Entry              subscriptions          Add Subscription'     accordion is open. Steps 2-5 are
                              listing page                                 collapsed and show + icon.
 AC-S      Step 1 —           Create flow is         User clicks 'Next'    Inline validation errors appear on
 12        Validation         open                   without filling       Name and Duration fields. Next is
                                                     Name or               blocked.
                                                     Duration
 AC-S      Step 1 — Type      User selects           Step 2 accordion      Linked Tier selector is NOT
 13        Toggle:            'Non-Tier'             is opened             shown. Tier Downgrade on Exit
           Non-Tier           subscription type                            toggle is NOT shown.
 AC-S      Step 1 — Type      User selects           Step 2 accordion      Linked Tier selector appears
 14        Toggle:            'Tier-Based'           is opened             (required field). Tier Downgrade
           Tier-Based         subscription type                            on Exit toggle appears. Tier
                                                                           dropdown is populated with
                                                                           program's active tiers.
 AC-S      Step 1 —           User leaves price      Form is saved         Subscription is saved with no
 15        Pricing: Free      field blank                                  price. Price column shows 'Free'
                                                                           in listing.
 AC-S      Step 1 —           User enters RM         Form is saved         Price stored as {amount: 50,
 16        Pricing: Paid      50 and selects                               currency: 'MYR'}. Price column
                              MYR currency                                 shows 'RM 50/month' (or per
                                                                           configured duration unit).
 AC-S      Step 3 —           Non-Tier               User opens            Flat list of available benefit
 17        Benefits:          subscription in        Benefits              templates shown. No tier filter
           Non-Tier           create flow            accordion             applied.
 AC-S      Step 3 —           Tier-Based             User opens            Benefit list is pre-filtered to Gold
 18        Benefits:          subscription linked    Benefits              tier's configured benefit
           Tier-Based         to Gold tier           accordion             categories. Gold tier badge
                                                                           shown.
 AC-S      Step 3 — Add       Benefits accordion     User clicks 'Add      Benefit card added to list with
 19        Benefit            is open                Benefit' and          green dot indicator, benefit name,

Capillary Technologies | Internal Use OnlyPage 40 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 AC ID     Area               Given                  When                 Then
                                                     selects '15% Off     and category type. Count badge
                                                     All Purchases'       on accordion header increments.
 AC-S      Step 4 —           Reminders              User adds 7 days     Reminder row appears with '7
 20        Reminders          accordion is open      before expiry via    days before expiry' and 'Email'
                                                     Email                channel. Timeline visualization
                                                                          updates.
 AC-S      Save as Draft      Complete Step 1        User clicks 'Save    Subscription saved with
 21                           form filled            as Draft'            Status=Draft. Appears in listing
                                                                          with gray 'Draft' badge. No
                                                                          approval required.
 AC-S      Submit for         Maker-checker is       User clicks          Subscription status set to
 22        Approval           enabled for            'Submit for          Pending Approval. Approver
                              program                Approval'            receives notification. Live listing is
                                                                          unchanged until approval.
 AC-S      Edit —             Active                 Admin edits          A pending version is created. Live
 23        Maker-Checke       subscription.          subscription and     version remains Active until
           r                  Maker-checker          clicks 'Save         approver approves. Status in
                              enabled.               Changes'             listing shows 'Pending Approval'
                                                                          sub-label.
 AC-S      Cancel —           Create flow is         User clicks          Confirmation dialog: 'Discard
 24        Confirmation       open with              'Cancel'             changes? Your unsaved changes
                              unsaved changes                             will be lost.' [Discard] [Keep
                                                                          Editing] buttons shown.



E3-US3 — aiRa Subscription Creation
 AC ID     Area               Given                   When                 Then
 AC-S      aiRa Context       User opens aiRa         aiRa panel loads     Context bar shows: 'Viewing:
 25                           panel on                                     Subscriptions | [Program Name]'.
                              Subscriptions page                           aiRa is aware of existing
                                                                           subscriptions, available tiers, and
                                                                           configured benefits.
 AC-S      Intent Parsing     User types: 'Create     User submits         aiRa extracts: duration=monthly,
 26        — Full             a monthly premium       message              price=RM 50, tier=Gold,
                              subscription for RM                          benefits=[15% discount, free
                              50 that links to                             shipping]. Preview card renders
                              Gold tier and gives                          with all fields. Confirmation chips
                              members 15% off                              shown.
                              all purchases and
                              free shipping'
 AC-S      Intent Parsing     User mentions a         aiRa receives the    aiRa flags the unrecognized
 27        — Ambiguous        benefit not in the      intent               benefit: 'Early Access to Sales is
           benefit            configured catalog                           not a configured benefit category.
                                                                           Should I create it, or skip it?' Offers
                                                                           [Create Category] and [Skip] chips.
 AC-S      Validation         User creates a paid     aiRa attempts to     aiRa flags: 'A price has been set
 28        Warning            subscription            map to API fields    but no currency selected. Please



Capillary Technologies | Internal Use OnlyPage 41 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 AC ID     Area               Given                   When                 Then
                              without specifying                           specify the currency.' Chip options
                              currency                                     for available currencies shown.
 AC-S      Benefit            User asks aiRa to       aiRa generates       aiRa recommends 3 relevant
 29        Recommendati       create a Gold tier      configuration        benefits based on tier and industry
           on                 subscription                                 patterns. Offers [Add] chips per
                              without specifying                           benefit and [Skip All] option.
                              benefits
 AC-S      Pricing            Active subscription     User asks 'What      aiRa returns: current subscriber
 30        Simulation         with 1,245              happens if I raise   count, statement that existing
                              subscribers at RM       the price to RM      enrollments retain RM 50
                              50                      65?'                 effectivePrice, new enrollments will
                                                                           be RM 65, and offers [Migrate All
                                                                           Subscribers] / [Keep Old Price for
                                                                           Existing] options.
 AC-S      Natural            Multiple active         User asks 'Which     aiRa returns ranked list sorted by
 31        Language           subscriptions           subscription has     subscriber count from listing data.
           Query                                      the most             Response includes plan name and
                                                      subscribers?'        count.
 AC-S      Quick Replies      aiRa has generated      Preview card is      Quick reply chips render: 'Looks
 32                           a subscription          rendered in chat     good', 'Add a benefit', 'Change
                              preview                                      price', 'Remove tier link', 'Save as
                                                                           draft', 'Submit for approval'.



E3-US4 — Lifecycle Management & Future-Dated Enrollment
 AC ID     Area               Given                   When                 Then
 AC-S      Pause              An Active               Admin selects        Subscription status changes to
 33                           subscription            'Pause' action       Paused. New enrollments blocked.
                                                                           Existing enrollments retain
                                                                           benefits. Status badge shows
                                                                           amber 'Paused'.
 AC-S      Resume             A Paused                Admin selects        Subscription status returns to
 34                           subscription            'Resume' action      Active. New enrollments permitted.
                                                                           Existing paused members resume
                                                                           benefit access.
 AC-S      Future-Dated       Member with active      Link API called      Enrollment created in PENDING
 35        Enrollment         subscription ending     with                 state. Benefits not active until 1
                              31 Mar                  membershipStart      Apr.
                                                      Date = 1 Apr         SUBSCRIPTION_ENROLLMENT_
                                                      (future date)        QUEUED event fired.
 AC-S      Past Date          No active               Link API called      400 ERR_INVALID_DATE
 36        Rejection          subscription            with                 returned. Enrollment not created.
                                                      membershipStart
                                                      Date in the past
 AC-S      Reschedule         PENDING                 Link API called      Old PENDING (1 Apr) cancelled
 37        PENDING            enrollment exists       again with           atomically. New PENDING (15
                              for 1 Apr               membershipStart      Apr) created.
                                                      Date = 15 Apr        SUBSCRIPTION_ENROLLMENT_


Capillary Technologies | Internal Use OnlyPage 42 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 AC ID     Area               Given                   When                 Then
                                                                           DEQUEUED fired for old,
                                                                           SUBSCRIPTION_ENROLLMENT_
                                                                           QUEUED fired for new.
 AC-S      PENDING            PENDING                 Activation job       PENDING transitions to ACTIVE.
 38        Activation         enrollment with         runs at midnight     Benefits become available.
                              membershipStartD                             SUBSCRIPTION_ENROLLMENT_
                              ate = today                                  STARTED event fired.
 AC-S      Delink             PENDING                 deLinkCustomer       PENDING enrollment is cancelled.
 39        PENDING            enrollment exists       called on that       SUBSCRIPTION_ENROLLMENT_
                                                      enrollment           DEQUEUED fired. Active
                                                                           enrollment (if any) is unaffected.
 AC-S      Tier               Tier-Based              Member's             Member's tier changes from Gold
 40        Downgrade on       subscription linked     subscription         to Silver. TIER_DOWNGRADE
           Exit               to Gold tier. Tier      expires              event fired. Enrollment record
                              Downgrade on Exit                            shows Expired status.
                              = ON. Downgrade
                              target = Silver.



E3-US5 — Subscription API Contract
 AC ID     Area               Given                   When                 Then
 AC-S      Create API         Required fields         POST                 400 with structured field-level
 41        Validation         missing (no name)       /subscriptions       error: {field: 'name', error:
                                                      called               'REQUIRED', message:
                                                                           'Subscription name is required'}
 AC-S      Maker-Checke       Maker-checker           PUT                  Response: 200 with pending
 42        r                  enabled. Admin          /subscriptions/{id   version ID. GET /subscriptions/{id}
                              PATCHes an active       } called             still returns the active version. GET
                              subscription.                                /subscriptions/approvals lists the
                                                                           pending change.
 AC-S      Benefits API       Subscription exists.    POST                 Benefits linked to subscription.
 43                           Benefits configured     /subscriptions/{id   GET /subscriptions/{id}/benefits
                              in system.              }/benefits called    returns updated list. Benefits count
                                                      with benefit IDs     in listing view increments.
 AC-S      Simulate API       500 active              POST                 Response includes: current
 44                           subscribers at          /subscriptions/{id   subscriber count, impact of
                              current price           }/simulate called    keeping vs migrating price,
                                                      with proposed        effectivePrice breakdown. No side
                                                      price change         effects — simulate does not save
                                                                           changes.
 AC-S      Context API        Program has 3           GET                  Response includes subscriptions
 45        Update             active subscriptions    /program/{id}/con    array with plan name, status,
                                                      text called          subscriber count, linked tier (if
                                                                           any), benefits linked. aiRa can use
                                                                           this for recommendations.
 AC-S      Event:             Link API called with    PENDING              SUBSCRIPTION_ENROLLMENT_
 46        QUEUED             future                  enrollment           QUEUED webhook fires with:
                                                      created              member_id, program_id,


Capillary Technologies | Internal Use OnlyPage 43 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 AC ID     Area               Given                   When               Then
                              membershipStartD                           membershipStartDate,
                              ate                                        membershipEndDate, state:
                                                                         PENDING
 AC-S      Event:             PENDING                 Activation job     SUBSCRIPTION_ENROLLMENT_
 47        STARTED            enrollment reaches      runs               STARTED webhook fires with:
                              membershipStartD                           member_id, program_id,
                              ate                                        membershipStartDate,
                                                                         membershipEndDate, state:
                                                                         ACTIVE, activationTimestamp
 AC-S      Pricing —          Plan price = RM         GET                Enrollment record includes
 48        effectivePrice     50. Member              customerActivity   effectivePrice: {amount: 50,
                              enrolls.                Histories called   currency: 'MYR'}. If plan price later
                                                      for that member    updated to RM 65, member's
                                                                         record still shows 50 unless explicit
                                                                         migration done.




E4 — Benefit Categories: Acceptance Criteria

 AC ID     Area               Given                   When               Then
 AC-B      Category           A valid                 Create benefit     Category is stored with isActive:
 C01       Creation           categoryType and        category call is   true. Appears in Benefits listing in
                              name are provided       made               DRAFT state with the correct
                                                                         trigger event derived from
                                                                         categoryType.
 AC-B      Category —         'Welcome Gift'          Admin tries to     Error returned:
 C02       Unique Name        category already        create another     DUPLICATE_CATEGORY_NAME.
                              exists in the           category named     Existing category is not affected.
                              program                 'Welcome Gift'
 AC-B      Instance           A category exists in    Admin creates a    Instance appears linked to
 C03       Linking            DRAFT state             benefit instance   category and tier. Category moves
                                                      and links it to    to ACTIVE once instance is
                                                      Silver tier with   approved.
                                                      configured value
                                                      fields
 AC-B      Maker-Checke       Maker-checker is        Admin submits a    Category status =
 C07       r — Category       enabled for the         new benefit        PENDING_APPROVAL. Existing
           Creation           program                 category           active categories unaffected.
                                                                         Approver sees the new category in
                                                                         approval queue.
 AC-B      Maker-Checke       An ACTIVE benefit       Admin saves the    A new version (750 pts) is created
 C08       r — Instance       instance for            edit               in PENDING_APPROVAL. The live
           Change             Birthday Bonus on                          instance (500 pts) remains
                              Gold tier (500 pts)                        ACTIVE until approved.
                              is edited to 750 pts
 AC-B      aiRa —             User types: 'Give       aiRa processes     aiRa correctly identifies
 C09       Category           top-tier members        intent             categoryType =
           Mapping                                                       BIRTHDAY_BONUS, prompts for:


Capillary Technologies | Internal Use OnlyPage 44 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 AC ID     Area                 Given                   When                Then
                                bonus points on                             tier applicability, pointsAwarded
                                their birthday'                             per tier, awardsWindowDays.
 AC-B      Matrix View —        Program has 3 tiers     Admin opens         A grid renders: categories as rows,
 C10       Display              and 5 benefit           Benefits            tiers as columns. Each cell shows
                                categories              dashboard matrix    the configured value or 'Not
                                configured              view                configured'. Configuration Gap
                                                                            cells show a red indicator.
 AC-B      Matrix View —        A category exists       Admin views         All cells for that category row show
 C11       All Not              but no instances        matrix              'Not configured'. Category row is
           Configured           have been created                           visually distinct (e.g., dashed
                                for any tier                                border or gray text).
 AC-B      Inactive             A category has          Admin opens         Inactive category is hidden from
 C12       Category             isActive set to false   Benefits listing    the benefits listing and matrix. It
                                                                            does not appear as a selectable
                                                                            option in tier or subscription benefit
                                                                            pickers. Accessible via 'Show
                                                                            inactive' toggle.
 AC-B      Subscription         A Free Shipping         Admin creates a     Free Shipping appears as a
 C13       Benefit              benefit category is     Gold-tier linked    selectable benefit in the
           Linkage              configured for Gold     subscription and    subscription benefits step,
                                tier                    opens Benefits      pre-filtered by Gold tier.
                                                        step




Cross-Epic Test Cases — Subscriptions + Benefits + Tiers Integration

 TC ID     Scenario               Prerequisites           Steps                    Expected Result
 TC-IN     Tier-Based             Gold tier exists.       1. Create Premium        Member's tier = Gold.
 T01       Subscription: Full     Earn Points benefit     Monthly (Tier-Based,     Transaction earns 2x points
           End-to-End             category                Gold). 2. Member         per Earn Points category.
                                  configured for Gold     enrolls. 3. Member       Subscription listing shows
                                  (2x multiplier).        makes a transaction.     +1 subscriber.
                                  Premium Monthly
                                  subscription linked
                                  to Gold.
 TC-IN     Tier Downgrade         Black Elite             1. Member enrolled in    Member's tier downgraded
 T02       on Subscription        subscription linked     Black Elite. 2. Admin    from Elite to Gold. Event log
           Cancellation           to Elite tier. Tier     cancels member's         shows:
                                  Downgrade on Exit       subscription via         SUBSCRIPTION_ENDED
                                  = ON. Downgrade         deLinkCustomer. 3.       → TIER_DOWNGRADE.
                                  target = Gold.          Check member's tier.
 TC-IN     aiRa Creates           Welcome Gift            1. User asks aiRa:       aiRa flags: 'Welcome Gift
 T03       Subscription with      category exists but     'Create a Gold-tier      category has no configured
           Benefit Category       has no instance for     subscription with a      instance for Gold tier. I can
           Gap                    Gold tier.              welcome gift of 500      create one with 500 points,
                                                          bonus points'. 2. aiRa   or skip the welcome gift.
                                                          attempts to link         Which do you prefer?'.
                                                          Welcome Gift.            [Create Instance] [Skip]
                                                                                   chips shown.

Capillary Technologies | Internal Use OnlyPage 45 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 TC ID     Scenario             Prerequisites             Steps                    Expected Result
 TC-IN     Maker-Checker:       Premium Annual            1. Admin edits           Listing shows Premium
 T04       Subscription Edit    subscription Active.      duration from 12         Annual still Active with
           Blocked Until        Maker-checker             months to 11 months.     original 12-month duration.
           Approved             enabled.                  2. Submits for           Sub-label 'Pending
                                                          approval. 3. Check       Approval' visible. After
                                                          listing before           approval, duration updates
                                                          approval.                to 11 months.
 TC-IN     Benefit Matrix       3 benefit categories      1. Open Benefits         Matrix shows all 3
 T05       reflects             configured for Gold       Matrix view. 2. Check    categories for Gold tier.
           Subscription-Link    tier. Premium             Gold tier column. 3.     Subscription detail shows
           ed Benefits          Monthly                   Check Premium            only 2 benefits linked. The
                                subscription links to     Monthly subscription     third category is available
                                Gold with 2 of the 3      detail.                  but not selected for this
                                categories                                         subscription.
                                selected.
 TC-IN     Future-Dated         Premium Monthly           1. Member attempts       28 Mar: Benefit available —
 T06       Subscription +       subscription.             to redeem Free           current ACTIVE enrollment
           Benefit              Member's current          Shipping on 28 Mar       is valid. 2 Apr: Benefit NOT
           Entitlement          cycle ends 31 Mar.        (still ACTIVE            available — PENDING
           Timing               Renewal queued            enrollment). 2.          enrollment has not yet
                                for 1 Apr                 Member attempts to       activated. Activation must
                                (PENDING).                redeem on 2 Apr          wait for
                                                          (PENDING                 membershipStartDate = 1
                                                          enrollment not yet       Apr.
                                                          started).
 TC-IN     Non-Tier             Student Pass              1. Member enrolls in     Member's loyalty tier is
 T07       Subscription:        subscription              Student Pass. 2.         UNCHANGED. Member has
           Benefits Without     (Non-Tier). Two           Check member's tier.     entitlements for 10%
           Tier                 benefits: 10%             3. Check benefit         Discount and Free Shipping
                                Discount, Free            entitlements.            from the subscription.
                                Shipping.                                          These are subscription-level
                                                                                   benefits, not tier-level.
 TC-IN     aiRa                 Gold tier renewal         1. Admin asks aiRa to    aiRa flags: 'Gold requires
 T08       Configuration        condition = spend         review the Gold          RM 400 for renewal but
           Validation:          RM 400. Silver            subscription             Silver only requires RM 300
           Renewal              upgrade threshold         configuration.           to upgrade. Members
           Threshold            = RM 300.                                          upgrading to Gold face a
                                Premium Monthly                                    harder renewal condition
                                subscription linked                                immediately. This is unusual
                                to Gold.                                           — do you want to review?'
 TC-IN     Price Increase —     Premium Monthly           1. Admin updates         New enrollment:
 T09       Existing             at RM 50. 1,245           plan price to RM 65.     effectivePrice = RM 65.
           Subscribers          active subscribers        2. Selects 'Keep         Existing 1,245 enrollments:
           Retain Old Price     at RM 50.                 existing subscribers     effectivePrice = RM 50.
                                                          on old price'. 3.        GET
                                                          Check new                customerActivityHistories
                                                          enrollment. 4. Check     confirms per-enrollment
                                                          existing enrollment.     price retained.
 TC-IN     Duplicate            Premium Annual            1. Admin duplicates      Create flow opens
 T10       Subscription         subscription with 5       Premium Annual via       pre-populated with all 5
           retains Benefits     linked benefits.          row actions. 2. Create   benefits. Name shows
                                                          flow opens.              'Premium Annual (Copy)'.


Capillary Technologies | Internal Use OnlyPage 46 of 47
Garuda Loyalty Platform | Tiers & Benefits | aiRa-Powered Experience CONFIDENTIAL

 TC ID     Scenario             Prerequisites             Steps                    Expected Result
                                                                                   All Step 1-5 values are
                                                                                   pre-filled and editable.



                                                   End of Document
       Garuda Loyalty Platform — Tiers & Benefits PRD v2.0 — Subscriptions, Benefit Categories, Acceptance Criteria

                                                   End of Document
                      Garuda Loyalty Platform — Tiers & Benefits PRD v2.0 — Capillary Technologies




Capillary Technologies | Internal Use OnlyPage 47 of 47
