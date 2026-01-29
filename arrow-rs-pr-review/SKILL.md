---
name: arrow-rs-pr-review
description: Review Apache Arrow (arrow-rs) pull requests with a focus on diff analysis, PR discussion accuracy, test and coverage evaluation (including cargo llvm-cov HTML), and public API/breaking change detection. Trigger when the user says "review <PR URL>" or "review https://github.com/apache/arrow-rs/pull/..." or asks to review an arrow-rs PR..
---

# Arrow RS PR Review

Follow this workflow to review an arrow-rs PR for correctness, tests, documentation, API consistency, and coverage.

## Collect PR context

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

## Coverage review (cargo llvm-cov)

- Run:

```bash
cargo llvm-cov --html test -p <crate>
```

- Open `target/llvm-cov/html/index.html` and inspect each changed file's HTML report.
- Use “next uncovered line (L)” to find gaps.
- Report uncovered lines that map to new/changed logic or error paths. Include the HTML report path and line numbers.
- Ignore any “mismatched data” warnings.
- Prefer unit tests near the implementation when coverage is missing.

## Output expectations

- Present findings in severity order, with file references and line numbers.
- Explicitly note public API changes and whether they are breaking.
- If coverage gaps exist, list them with the HTML report path.
- If no issues are found, state that clearly and mention any residual testing gaps.
