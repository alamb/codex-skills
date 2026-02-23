---
name: datafusion-backport
description: Backport a specific Apache DataFusion PR commit to a release branch (for example apache/branch-52) by cherry-picking the commit, resolving conflicts safely, running required verification (`cargo test --profile=ci --test sqllogictests` and `nice cargo nextest run`), and reporting final status. Use when a user asks to backport a DataFusion PR or commit onto a maintenance branch.
---

# DataFusion Backport

Use this workflow to backport one commit from a PR onto a release branch.

## Gather relevant data

* Backport branch: The user must tell you what branch to backport to. For example, to backport to 52, you use the apache/branch-52 branch
* PR being backported. The user must tell you the PR to backport. For example, https://github.com/apache/datafusion/pull/20192
* The commit can be found using `gh pr view https://github.com/apache/datafusion/pull/20192 --json number,state,mergedAt,mergeCommit,commits`


## Create a new branch for the backport

Create a new branch named `alamb/backport_XXXX` for the backport where `XXXX` is the PR number we are backporting. For example, to create a branch for backporting PR 1234 use commands like

```
git checkout apache/branch-52
git checkout -b alamb/backport_1234
```


## Cherry-pick

- Run `git cherry-pick <commit>`.
- If cherry-pick succeeds, proceed to verification.
- If conflicts occur, continue with conflict resolution.

## Resolve conflicts

- Identify conflicts via `git status --short`.
- Locate conflict markers via:
  `rg -n "^(<<<<<<<|=======|>>>>>>>)" <conflicted-files>`.
- Preserve intended PR behavior while adapting to target-branch APIs.
- Prefer minimal, targeted edits over broad rewrites.
- Ensure no conflict markers remain.


## Run required verification

- Run `cargo test --profile=ci --test sqllogictests`.
- Run `nice cargo nextest run`.
- If failures occur, fix regressions and rerun.

## Complete cherry-pick

- Stage resolved files with `git add <files>`.
- Run `git cherry-pick --continue`.


## 7. Report outcome

- Include:
  - cherry-picked commit
  - conflict files and resolutions

Propose a `gh` command to create a pull request that has:
- The title of the backport PR with the original PR title prefixed with the target branch (for example `[branch-52] ORIGINAL PR TITLE`)


This is a good example:
PR: https://github.com/apache/datafusion/pull/20509
Title: [branch-52] fix: validate inter-file ordering in eq_properties() (#20329)
Body:
```
- Part of https://github.com/apache/datafusion/issues/20287
- Closes https://github.com/apache/datafusion/issues/20508 on branch-52

This PR:
- Backports https://github.com/apache/datafusion/pull/20329 from @adriangb to the branch-52 line
```




## Guardrails

- Avoid destructive git commands unless explicitly requested.
- Do not revert unrelated user changes.
- Keep backport scope limited to requested PR behavior.
