---
name: datafusion-pr-review
description: Review Apache DataFusion pull requests with a focus on diff analysis, PR discussion accuracy, test coverage, documentation, API consistency, and breaking public API detection. Trigger when the user says "review <PR URL>" or "review https://github.com/apache/datafusion/pull/..." or asks to review a DataFusion PR.
---

# DataFusion PR Review

Follow this workflow to review a DataFusion PR for correctness, tests, documentation, API consistency, and public API changes.

## Collect PR context

- First ask if you should checkout the PR. If yes, check it out with `gh`.
  - Example: `gh co -f https://github.com/apache/datafusion/pull/19722`
- Use `get_gh_content.sh` to fetch the PR description and comments, then verify claims against the diff and code.
  - Example: `bash ~/bin/get_gh_content.sh <PR_URL>`
- Call out inaccuracies or missing details in the PR text.

## Compute the diff

- Generate the PR diff against `apache/main`:

```bash
git diff `git merge-base HEAD apache/main`
```

## Review checklist

Check for and report issues, highest priority first:

1. Tests covering new features and changed behavior.
2. Functions and public APIs documented accurately; comments match behavior.
3. Consistency with existing public APIs and patterns.
4. Changed code covered by tests (new or existing).
5. Breaking public API changes (explicitly call these out).

## Breaking public API changes

Any breaking public API change should be documented in the upgrading guide:

- `https://github.com/apache/datafusion/blob/main/docs/source/library-user-guide/upgrading.md`

Follow the API policy:

- `https://datafusion.apache.org/contributor-guide/api-health.html`

When flagging a breaking change, include an example of the old pattern and the new pattern.

## Output expectations

- Present findings in severity order, with file references and line numbers.
- Explicitly note public API changes and whether they are breaking.
- If no issues are found, state that clearly and mention any residual testing gaps.
