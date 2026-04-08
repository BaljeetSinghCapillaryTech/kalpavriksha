# Multi-Epic Coordination — How to Use

A practical guide with examples. For architecture details, see the [design spec](superpowers/specs/2026-04-08-multi-developer-epic-coordination-design.md).

---

## Quick Start

Everything runs through one command:

```bash
claude --agent feature-pipeline
```

- **Architect?** Pick Mode [5] to decompose the BRD and assign epics.
- **Developer?** Pick Mode [1], select multi-epic, identify yourself, start building.

---

## Example: Loyalty Platform BRD with 3 Developers

### The BRD

A loyalty platform overhaul with 4 epics:
- **Tier Management** — tier CRUD, upgrade/downgrade strategies
- **Benefits Management** — benefit rules, reward mapping
- **Campaigns** — campaign engine, targeting
- **Rewards** — points earning/burning rules

Two shared modules are needed by multiple epics:
- **Maker-checker** — needed by Tier + Benefits
- **Audit trail** — needed by all 4

Three developers:
- **Anuj** — Tech Lead
- **Baljeet** — SDE 2
- **Ritwik** — SDE 1

---

### Step 1: Tech Lead Decomposes the BRD (Once)

Anuj is the tech lead. He runs Mode [5]:

```
$ claude --agent feature-pipeline

Select a mode:
  [1] Full Pipeline
  [2] Resume
  [3] Jump to Phase
  [4] Status
  [5] Decompose BRD (Architect Mode)

> 5
```

The pipeline asks for inputs:

```
> BRD: ~/Downloads/loyalty-v3-brd.pdf
> Epics: tier-management, benefits-management, campaigns, rewards
> Repos: emf-parent, intouch-api-v3, peb, thrift
> Registry: capillary/shared-modules-registry → "create"
> Team members: Anuj (tech lead, architect), Baljeet (SDE 2, knows benefits domain), Ritwik (SDE 1, learning)
```

The decomposer analyses the BRD, identifies shared modules, designs Thrift IDL, and suggests assignments:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUGGESTED EPIC ASSIGNMENT

SHARED MODULES IDENTIFIED (2):
  maker-checker  — needed by: Tier, Benefits
  audit-trail    — needed by: all 4 epics

SUGGESTED ASSIGNMENT:

  Developer   │ Epic(s)              │ Builds (shared)  │ Layer
  ────────────┼──────────────────────┼──────────────────┼──────
  @anuj       │ tier-management      │ maker-checker    │ 1
  @baljeet    │ benefits-management  │ audit-trail      │ 1
  @ritwik     │ campaigns, rewards   │ (none)           │ 2

WHY THIS ASSIGNMENT:
  • Anuj (tech lead) gets Tier + maker-checker — shared modules need
    careful IDL design, best handled by the most experienced developer.
    Defines the interface that everyone else consumes.
  • Baljeet (SDE 2) gets Benefits + audit-trail — he knows the benefits
    domain and is experienced enough to own a shared module.
    Builds in parallel with Anuj (both Layer 1).
  • Ritwik (SDE 1) gets Campaigns + Rewards — Layer 2, consuming both 
    shared modules that are already merged. Simpler scope, good for 
    learning the codebase. AI agent handles the heavy lifting.

SEQUENCING:
  Day 1: Anuj + Baljeet start simultaneously (Layer 1)
  Day 2: Shared modules merged → Ritwik starts (Layer 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Is this good?
  [A] Proceed
  [B] I want to adjust assignments
  [C] Suggest a different approach — tell me your constraints

> A
```

The decomposer publishes everything:

```
Decomposition complete!
  Registry: capillary/shared-modules-registry (populated)
  Branches created:
    kalpavriksha:   raidlc/CAP-123/epic-division
    emf-parent:     raidlc/CAP-123
    intouch-api-v3: raidlc/CAP-123
    thrift:         raidlc/CAP-123

  What would you like to do?
    [A] Switch to Mode 1 — start your epic now
    [B] Exit — other developers will start later

> A
```

---

### Step 2: Anuj Starts His Epic (Layer 1, Tech Lead)

The pipeline transitions to Mode [1] with registry pre-filled:

```
> Feature name: Tier Management
> Ticket ID: CAP-123
> Artifacts path: docs/workflow/tier/
> BRD: ~/Downloads/loyalty-v3-brd.pdf
> Code: emf-parent, intouch-api-v3, thrift
> Multi-epic: yes (already set)
> Registry: capillary/shared-modules-registry (already set)
```

Pre-flight runs:

```
Step 2: Finding epic division branch...
  Found: raidlc/CAP-123/epic-division
  Reading epic-assignment.json...

Step 3: Who are you?
  [1] Anuj (@anuj)
  [2] Baljeet (@baljeet)
  [3] Ritwik (@ritwik)
  
> 1

  Your assignment:
    Epics: tier-management
    Builds: maker-checker (you own this — publish IDL first)
    Consumes: audit-trail (owned by @baljeet — use IDL mocks until merged)
    Layer: 1 (start immediately)

Step 4: Checking out raidlc/CAP-123 in code repos...
  ✓ emf-parent: branch exists, pulled latest
  ✓ intouch-api-v3: branch exists, pulled latest
  ✓ thrift: branch exists, pulled latest

Step 5: Loading epic package...
  ✓ Constraints loaded into session memory

Starting pipeline for tier-management...
```

The pipeline runs all 14 phases. After Phase 1 (BA), the coordinator checks in:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 COORDINATOR — Post-Phase 1 (Registry Scan)

  ✅ maker-checker: YOU ARE BUILDING THIS
     Interface will be published at Phase 6.
  
  ⏳ audit-trail: owned by @baljeet (status: not-started)
     Will code against IDL mocks when available.
  
  📢 @baljeet is also working (benefits-management, started 10 min ago)
  📢 @ritwik is Layer 2 — will start after shared modules merge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

After Phase 6 (Architect), the coordinator publishes the maker-checker IDL:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 COORDINATOR — Post-Phase 6 (Interface Check)

  ✅ Published maker-checker IDL to registry:
     interfaces/maker-checker/MakerCheckerService.thrift
  
  ✅ No conflicts with registry modules.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

During Phase 9 (Developer), the background watch checks every 30 minutes:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 COORDINATOR WATCH (background check)
  ✅ audit-trail: now in-progress (Baljeet published IDL)
  ✅ No new collisions detected
  Next check in 30 minutes.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Anuj finishes. The pipeline pushes to `raidlc/CAP-123`:

```
git pull --rebase origin raidlc/CAP-123  ← gets Baljeet's latest commits
git push origin raidlc/CAP-123           ← pushes Anuj's work
```

---

### Step 3: Baljeet Starts His Epic (Layer 1, Simultaneously)

On a different machine, at the same time as Anuj:

```
$ claude --agent feature-pipeline

> Mode: 1
> Feature name: Benefits Management
> Ticket ID: CAP-123
> Multi-epic: yes
> Registry: capillary/shared-modules-registry
```

Pre-flight:

```
Step 2: Finding epic division branch...
  Found: raidlc/CAP-123/epic-division

Step 3: Who are you?
  [1] Anuj (@anuj) — status: in-progress
  [2] Baljeet (@baljeet) — status: not-started
  [3] Ritwik (@ritwik) — status: not-started

> 2

  Your assignment:
    Epics: benefits-management
    Builds: audit-trail (you own this)
    Consumes: maker-checker (owned by @anuj — use IDL mocks)
    Layer: 1 (start immediately)

Step 4: Checking out raidlc/CAP-123...
  ✓ emf-parent: pulled latest (includes Anuj's commits)
```

Baljeet's coordinator at Phase 1:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 COORDINATOR — Post-Phase 1 (Registry Scan)

  ⏳ maker-checker: owned by @anuj (status: in-progress)
     Interface: interfaces/maker-checker/MakerCheckerService.thrift
     → Generating mocks from IDL. DO NOT REBUILD.
  
  ✅ audit-trail: YOU ARE BUILDING THIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Before Phase 9, the coordinator syncs:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 COORDINATOR — Pre-Phase 9 (Final Sync)

  🎉 maker-checker: MERGED to main by @anuj!
     Switching from IDL mocks to real implementation.
     Run: git pull origin main in emf-parent
  
  ✅ No branch collisions detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Baljeet pushes — rebase picks up Anuj's work automatically:

```
git pull --rebase origin raidlc/CAP-123  ← clean, no conflicts
git push origin raidlc/CAP-123           ← Baljeet's work on top of Anuj's
```

---

### Step 4: Ritwik Starts His Epics (Layer 2, After Shared Modules Merge)

Next day. Both shared modules are merged. Ritwik (SDE 1) starts his work — the AI agent handles the heavy lifting, and all dependencies are already available on main.

```
$ claude --agent feature-pipeline

> Mode: 1
> Multi-epic: yes

Step 3: Who are you?
  [1] Anuj (@anuj) — status: completed
  [2] Baljeet (@baljeet) — status: completed
  [3] Ritwik (@ritwik) — status: not-started

> 3

  Your assignment:
    Epics: campaigns, rewards (2 epics, sequential)
    Builds: (none)
    Consumes: maker-checker (MERGED ✅), audit-trail (MERGED ✅)
    Layer: 2

  Which epic first?
    [1] campaigns
    [2] rewards
  
> 1
```

Ritwik's coordinator at Phase 1:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 COORDINATOR — Post-Phase 1 (Registry Scan)

  ✅ maker-checker: MERGED — using real implementation
  ✅ audit-trail: MERGED — using real implementation
  ✅ All dependencies available. No mocks needed.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Zero coordination overhead — everything Ritwik needs is already on main. The AI agent guides him through implementation even though he's newer to the codebase.

After campaigns, Ritwik runs the pipeline again for rewards:

```
$ claude --agent feature-pipeline
> Mode: 1
> Multi-epic: yes
> Who are you? Ritwik
> Which epic? rewards

(Same flow — all dependencies already merged)
```

---

### Step 5: Final PR

All work is on `raidlc/CAP-123`. One PR to main:

```
$ gh pr create --base main --head raidlc/CAP-123 \
    --title "CAP-123: Loyalty Platform v3 — Tier, Benefits, Campaigns, Rewards" \
    --body "4 epics, 3 developers, 2 shared modules, 1 branch."
```

---

## Example: Adjusting Assignments

The architect doesn't like the suggested assignment:

```
Is this good?
  [A] Proceed
  [B] I want to adjust assignments
  [C] Suggest a different approach

> C

What constraints should I consider?
> Anuj should handle both shared modules since he's tech lead and knows Thrift.
  Ritwik is SDE 1, give him simple consuming epics with good learning scope.
  Baljeet can take benefits since he knows the domain well.

Re-running assignment...

UPDATED ASSIGNMENT:
  @anuj    → tier-management, campaigns   │ builds both shared modules │ Layer 1, 2
  @baljeet → benefits-management          │ consumes both              │ Layer 2
  @ritwik  → rewards                      │ consumes both              │ Layer 2

Is this better? [A] Proceed / [B] Adjust / [C] Different constraints
> A
```

---

## Example: Conflict During Push

Anuj and Baljeet both modified `pom.xml`:

```
$ git push origin raidlc/CAP-123
! [rejected] raidlc/CAP-123 -> raidlc/CAP-123 (non-fast-forward)

Pipeline handles it:
  git pull --rebase origin raidlc/CAP-123
  
  CONFLICT in pom.xml
  
  "Conflict detected during rebase.
   Files: pom.xml
   
   [1] Resolve now — show diffs, fix interactively
   [2] Stash changes — pull theirs, re-apply yours manually
   [3] Ask for help — pause and coordinate with the other developer"
  
  > 1
  (shows diff, developer resolves, continues)
  
  git rebase --continue
  git push origin raidlc/CAP-123  ← succeeds
```

---

## Example: Shared Module Gets Reverted

Anuj's maker-checker had a bug and was reverted on main. Baljeet is mid-Phase 9:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 COORDINATOR WATCH — URGENT

  Module 'maker-checker' was REVERTED on main.
  PR #342 reverted by PR #345.
  Your code depends on it. Action needed:
  
  [1] Pause and switch to fallback (use v1.0 interface)
  [2] Continue — Anuj will re-merge soon
  [3] Stop Phase 9
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example: Rework Changes a Shared Module

Anuj is at Phase 11 (Reviewer). Reviewer finds a design flaw in maker-checker and routes back to Phase 6 (Architect). The rework changes the IDL:

```
Phase 6 re-runs → architect adds bulkApprove() to maker-checker IDL.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 COORDINATOR — Rework Sync

  IDL changed for maker-checker:
    + bulkApprove(requestIds, approverId) → BulkResult
  
  Compatibility: ✅ Non-breaking (method added, none removed)
  Published updated IDL to registry.
  
  Notified consumers:
    GitHub issue created: "@baljeet @ritwik — maker-checker IDL updated.
    New method: bulkApprove(). Your code still works. Consider adopting."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example: No Architect — Self-Coordinating

Small team, no one runs Mode [5]. Everyone starts independently:

```
Dev A starts:
  Mode [1] → multi-epic: yes → no epic-division found
  > [B] Continue without division
  
  Phase 1 (BA) completes.
  Coordinator: "maker-checker needed by your epic. Not in registry. Claim it? [Y]"
  Dev A claims maker-checker.

Dev B starts 30 minutes later:
  Mode [1] → multi-epic: yes → no epic-division found
  > [B] Continue without division
  
  Phase 1 (BA) completes.
  Coordinator: "maker-checker ALREADY CLAIMED by @dev-a.
               DO NOT REBUILD. Code against IDL at interfaces/maker-checker/"
```

Works, but less optimal than Mode [5] — no upfront sequencing, no pattern checklist, no pre-created branches.

---

## Commands Reference

| Command | Who | What |
|---------|-----|------|
| `feature-pipeline` → Mode [5] | Architect | Decompose BRD, assign epics, create branches |
| `feature-pipeline` → Mode [1] + multi-epic | Developer | Run assigned epic with coordination |
| `feature-pipeline` → Mode [1] standalone | Developer | Run without coordination (single epic) |
| `feature-pipeline` → Mode [2] | Developer | Resume from where you left off |
| `feature-pipeline` → Mode [4] | Anyone | Check pipeline status |

---

## Checklist

### Architect (run once)
- [ ] Prepare BRD (PDF/DOCX/MD)
- [ ] List all epic names
- [ ] Know code repo paths
- [ ] Know team members and their strengths
- [ ] Run Mode [5]
- [ ] Review suggested assignment
- [ ] Confirm or adjust
- [ ] Share the ticket ID with the team

### Developer (run per epic)
- [ ] Know the ticket ID (from architect)
- [ ] Know the registry repo URL
- [ ] Run Mode [1] with multi-epic: yes
- [ ] Identify yourself in the team list
- [ ] Follow the pipeline — coordinator handles the rest
- [ ] `git pull --rebase` before every push (pipeline does this automatically)
- [ ] After completing: run again for next epic if you have multiple

### After All Epics Complete
- [ ] Create one PR: `raidlc/<ticket>` → main
- [ ] All work from all developers is in the same branch
- [ ] Review and merge
