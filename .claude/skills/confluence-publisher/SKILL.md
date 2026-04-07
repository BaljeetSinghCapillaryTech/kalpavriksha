---
name: confluence-publisher
description: Publishes AIDLC/feature-pipeline artifacts (.md, .html, .yml, .yaml) to Confluence. Creates a run folder per pipeline run, publishes each artifact as a child page, updates on re-publish. Use when any pipeline phase completes and produces artifacts, or when user says /confluence-publisher.
---

# Confluence Publisher

Publishes pipeline artifacts to a Confluence space so the team has a living, browsable record of every pipeline run — without needing access to the repo or local files.

## Confluence Target Configuration

Each product configures its own target. The invoking pipeline (feature-pipeline or workflow) passes these values. If any are missing, ask the user.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `cloud_id` | Atlassian cloud instance ID | `69031ea7-8347-4ec3-a63d-9c7289f8dc4f` |
| `space_id` | Confluence space ID | `1264386327` |
| `parent_folder_id` | Folder/page ID under which run folders are created | `5434343427` |

### Known Product Configs

| Product | Space | Parent Folder ID | Folder Name |
|---------|-------|-------------------|-------------|
| Tiers & Benefits | LOYAL (`1264386327`) | `5434343427` | "Tiers and Benefits AI-Led" |

To add a new product: add a row above and reference it from your pipeline's `pipeline-state.json` under the `confluence` key.

---

## Protocol

### Step 1: Create Run Folder Page (once per pipeline run)

At pipeline start (Phase 0 / Input Collection), create a single page that acts as the run folder:

```
Title format:  <ticket> — <feature-name> (<YYYY-MM-DD HH:mm>)
Example:       CAP-12345 — Benefits as a Product (2026-04-07 15:30)
```

```
mcp__atlassian__createConfluencePage(
  cloudId      = <cloud_id>,
  spaceId      = <space_id>,
  parentId     = <parent_folder_id>,
  title        = "<ticket> — <feature-name> (<YYYY-MM-DD HH:mm>)",
  body         = "# <feature-name>\n\n| Field | Value |\n|---|---|\n| Ticket | <ticket> |\n| Branch | raidlc/<ticket> |\n| Repos | <code_repos comma-separated> |\n| Started | <timestamp> |\n| Pipeline | feature-pipeline v1.0 |",
  contentFormat = "markdown"
)
```

Store the result in `pipeline-state.json`:
```json
"confluence": {
  "cloud_id": "<cloud_id>",
  "space_id": "<space_id>",
  "parent_folder_id": "<parent_folder_id>",
  "run_page_id": "<created-page-id>",
  "artifact_pages": {}
}
```

### Step 2: Publish Artifacts After Each Phase

After every phase that produces `.md`, `.html`, `.yml`, or `.yaml` files, publish each artifact as a child page under the run page.

```
For each new/updated artifact file in <artifacts-path>:

  title = "Phase <NN> — <phase-name> | <filename>"
  body  = <file contents>

  If artifact_pages[filename] does NOT exist (first publish):
    mcp__atlassian__createConfluencePage(
      cloudId       = <cloud_id>,
      spaceId       = <space_id>,
      parentId      = <run_page_id>,
      title         = title,
      body          = body,
      contentFormat = "markdown"    # for .md files
    )
    → Store page ID: artifact_pages[filename] = <new-page-id>

  If artifact_pages[filename] ALREADY exists (re-publish / update):
    mcp__atlassian__updateConfluencePage(
      cloudId       = <cloud_id>,
      pageId        = artifact_pages[filename],
      title         = title,
      body          = body,
      contentFormat = "markdown"
    )
```

### Handling .yml / .yaml files

YAML files (API contracts, config specs) are published as markdown with the content wrapped in a fenced code block:
```
body = "```yaml\n" + <file-contents> + "\n```"
contentFormat = "markdown"
```

### Handling .html files

HTML files (live-dashboard.html, blueprint) contain raw HTML with Mermaid diagrams and styling. Confluence doesn't render raw HTML natively.

For `.html` artifacts:
- Publish with `contentFormat = "markdown"` wrapping the content in a code block so it is at least readable
- Add a note at the top: `> Full interactive version: open the .html file locally from the repo artifacts path.`

### Step 3: Update pipeline-state.json

After every publish/update, persist the mapping so resumes and re-runs don't create duplicates:

```json
"confluence": {
  "cloud_id": "69031ea7-...",
  "space_id": "1264386327",
  "parent_folder_id": "5434343427",
  "run_page_id": "5432410130",
  "artifact_pages": {
    "session-memory.md": "5432410200",
    "00-ba.md": "5432410300",
    "00-prd.md": "5432410400",
    "01-architect.md": "5432410500",
    "live-dashboard.html": "5432410600"
  }
}
```

---

## When This Skill Runs

The pipeline orchestrator invokes this skill at two points:

1. **Phase 0 (Input Collection)** — Step 1: create the run folder page
2. **After every subsequent phase** — Step 2: publish/update that phase's artifacts

The skill is idempotent — calling it again for the same artifact updates rather than duplicates.

## On Resume

When resuming a pipeline run:
- Read `confluence.run_page_id` from `pipeline-state.json`
- Verify it still exists (call `getConfluencePage`). If deleted, re-create and update state.
- Continue publishing new phase artifacts as child pages under the existing run page.

## Error Handling

- If Confluence API returns 401/403: tell user "Confluence auth failed — check your Atlassian MCP token. Skipping publish, artifacts are still saved locally."
- If API returns 404 on the parent folder: tell user "Parent folder <id> not found. Provide the correct Confluence folder ID."
- Never block the pipeline on Confluence failures — local artifacts are the source of truth. Log the failure and continue.
