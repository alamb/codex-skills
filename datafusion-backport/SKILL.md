---
name: datafusion-backport
description: Backport a merged Apache DataFusion PR commit onto a maintenance branch (for example apache/branch-52), including safe cherry-pick conflict resolution, required verification (`cargo test --profile=ci --test sqllogictests` and `nice cargo nextest run`), and a ready-to-run `gh pr create` command. Use when a user asks to backport a DataFusion PR or commit.
---

# DataFusion Backport

Use this workflow to backport one commit from a merged PR onto a release branch.

## Inputs

Collect these inputs first:

- Target branch (for example `apache/branch-52`).
- PR URL (for example `https://github.com/apache/datafusion/pull/20192`).
- Optional explicit commit SHA to backport (if not provided, derive it from PR metadata).

## Preflight

1. Ensure the worktree is clean before starting.
2. Fetch latest remote refs.
3. Confirm the PR is merged and gather metadata.

Use:

```bash
git status --porcelain
git fetch apache
gh pr view <pr-url> --json number,title,state,mergedAt,mergeCommit,commits,author,url
```

If `git status --porcelain` is non-empty, stop and ask the user before proceeding.

If the PR is not merged, stop and ask the user how to proceed.

## Determine commit to cherry-pick

1. If the user provided a commit SHA, use it.
2. Otherwise use `mergeCommit.oid` from `gh pr view`.
3. If `mergeCommit` is null or ambiguous, ask the user to confirm the exact commit to backport.
4. Keep scope limited to the requested change; do not add unrelated commits.

## Create backport branch

1. Check out the target branch.
2. Create a new backport branch.

Naming convention:

- `<github-handle>/backport_<pr_number>`

Example for user `alamb`:

```bash
git checkout apache/branch-52
git checkout -b alamb/backport_1234
```

## Cherry-pick

Run:

```bash
git cherry-pick <commit>
```

If cherry-pick succeeds, continue to required verification.

If conflicts occur, continue to conflict resolution.

## Resolve conflicts

1. Identify conflicted files.
2. Remove conflict markers.
3. Preserve intended PR behavior while adapting to target-branch APIs.
4. Prefer minimal, targeted edits over broad rewrites.
5. Stage resolved files.
6. Continue cherry-pick.

Use:

```bash
git status --short
git diff --name-only --diff-filter=U
rg -n "^(<<<<<<<|=======|>>>>>>>)" <conflicted-files>
git add <resolved-files>
git cherry-pick --continue
```

If `git cherry-pick --continue` reports more conflicts, repeat this section until complete.

## Run required verification

Run these commands:

```bash
nice ./ci/scripts/rust_fmt.sh
nice ./ci/scripts/rust_clippy.sh
nice cargo test --profile=ci --test sqllogictests
nice cargo nextest run
```

If failures occur, fix regressions introduced by the backport and rerun until passing, or report a blocker clearly.

## Report outcome

Report:

- Target branch.
- Backport branch.
- PR URL and PR number.
- Cherry-picked commit SHA.
- Conflict files and concise resolution summary (or "no conflicts").
- Verification commands run and pass/fail status.

## Propose pull request command

Provide a concrete `gh` command to create the backport PR:

```bash
gh pr create \
  --repo apache/datafusion \
  --base <target-branch> \
  --head <github-handle>:<github-handle>/backport_<pr_number> \
  --title "[branch-XX] <original-pr-title> (#<original-pr-number>)" \
  --body-file <path-to-pr-body.md>
```

Important:

- When the backport branch name includes a slash such as `<github-handle>/backport_<pr_number>`, `gh pr create` must use `--head <owner>:<branch>` rather than `--head <branch>`.
- Without the `owner:` prefix, GitHub CLI may interpret the branch name incorrectly and fail with errors such as `Head sha can't be blank`, `Base sha can't be blank`, `No commits between ...`, or `Head ref must be a branch`.

Title format must prefix the original PR title with the target branch, for example:

- `[branch-52] fix: validate inter-file ordering in eq_properties() (#20329)`

Use this body pattern:

```markdown
- Part of <tracking-issue-url>
- Closes <backport-issue-url> on <branch-name>

This PR:
- Backports <original-pr-url> from @<author> to the <branch-name> line
```

Here are some other examples:
- https://github.com/apache/datafusion/pull/20792
- https://github.com/apache/datafusion/pull/20883
- https://github.com/apache/datafusion/pull/20879

## Update tracking issue

If the user provided a release or tracking issue (for example `#20855`), update that issue after the backport PR has been created.

Workflow:

1. Read the current issue body.
2. Replace the relevant `TODO` entry for the backported issue with the created backport PR URL.
3. Preserve all unrelated text and checklist items exactly.
4. Leave unrelated `TODO` entries unchanged.

Use:

```bash
gh issue view <tracking-issue-number> --repo apache/datafusion --json body
gh issue edit <tracking-issue-number> --repo apache/datafusion --body-file <updated-body.md>
```

Example replacement:

- Before: `https://github.com/apache/datafusion/issues/20267 / @alamb / TODO`
- After: `https://github.com/apache/datafusion/issues/20267 / @alamb / https://github.com/apache/datafusion/pull/20877`

Do not update the tracking issue until the backport PR URL is known.


## Guardrails

- Avoid destructive git commands unless explicitly requested.
- Do not revert unrelated user changes.
- Keep backport scope limited to requested PR behavior.
