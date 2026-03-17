---
name: status-report
description: Prepare board-driven GitHub status updates by gathering assigned project items, collecting recent GitHub activity, matching activity back to open work, and drafting concise update summaries with links. Use when the user asks for a weekly status report, board update, project update draft, or comment-ready status summary for GitHub issues and pull requests, especially for the InfluxData upstream/query board workflow.
---

# Status Report

Use this skill to turn a GitHub board view plus a recent-activity window into draft issue updates and optional comment text.

Prefer the bundled collector script for the data-gathering step. The script uses `gh project item-list` and `gh search issues` directly so the workflow stays aligned with the GitHub CLI.

## Defaults

Read [defaults.md](./references/defaults.md) if the user does not restate the board settings. The default workflow targets:

- org `influxdata`
- project `144`
- assignee `alamb`
- labels `team/query`, `query`, `team/upstream`, `upstream`, `area/influxql`, `Apache Upstream`
- statuses `Next`, `In Progress`, `Blocked/Waiting`, `In Review`
- exclude label `epic`

## Workflow

1. Establish the activity window.
2. Gather open assigned items from the board.
3. Gather recent GitHub activity for the same user.
4. Match activity to board items when the URL clearly corresponds.
5. Keep unmatched activity in `Other`.
6. Draft per-item update text with links.
7. Ask whether to post the comments.

## Step 1: Establish the timeline

- If the user gives an explicit anchor such as "since Friday", convert it to an absolute date before proceeding.
- If the last-update boundary is not clear, ask a single direct question before drafting summaries.
- If the user wants a first pass immediately, state the assumption clearly and use a short window such as the last 7 days.

## Step 2: Collect the raw data

Run:

```bash
python3 /Users/andrewlamb/.codex/skills/status-report/scripts/collect_status_report.py --since YYYY-MM-DD --json
```

Override defaults only when needed:

```bash
python3 /Users/andrewlamb/.codex/skills/status-report/scripts/collect_status_report.py \
  --org influxdata \
  --project-number 144 \
  --assignee alamb \
  --since YYYY-MM-DD \
  --status "In Progress" \
  --label "Apache Upstream" \
  --json
```

The script returns:

- `open_items`
- `recent_activity`
- `matched_activity`
- `other_activity`

Before using the board query, verify auth with:

```bash
gh auth status
```

The board step requires the `read:project` scope. If it is missing, refresh auth with:

```bash
gh auth refresh -s read:project
```

## Step 3: Match and interpret the activity

- Treat exact URL matches as strong matches.
- Treat unmatched results as suggestions, not proof. Only associate them manually when the relationship is obvious from the title, repository, or linked PR/issue context.
- Do not draft a proposed update for an item that has no matched or clearly related activity in the selected time window.
- If an item has no matched activity, list it separately as `No activity in window` rather than proposing text for the issue.
- If the user needs stronger matching, inspect the relevant issue or PR directly before drafting the update.

## Step 4: Present the list to the user

Present:

- each open item using its issue title as the primary label, followed by the URL
- an `Other` section for recent activity not matched to an open item
- a `No activity in window` section for open board items without usable evidence
- a short note about the activity window used

Use this display format in the final report:

- `<issue title> (<issue url>):`

Prefer the human-readable title over `repo#number` in user-facing summaries.

Keep the presentation compact. The user is usually scanning for whether each item has a plausible update.

## Step 5: Draft the update text

For each open item, draft:

- one concise status sentence
- one evidence sentence with the most relevant link or links
- one blocker or next-step sentence if warranted

Favor factual language over narrative. Good update patterns:

- "Reviewed X and pushed follow-up changes in Y."
- "No direct activity this window; next step is Z."
- "Blocked waiting on review in Y."

Only draft update text when there is supporting activity. Do not imply progress that the data does not show.

## Step 6: Ask before posting comments

After showing the proposed updates, ask whether the user wants comments posted to the relevant issues or PRs.

If the user says yes:

- use the drafted text as a starting point
- let the user review significant ambiguity first
- post only to the issues or PRs the user confirms
