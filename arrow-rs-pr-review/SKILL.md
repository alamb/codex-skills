---
name: arrow-rs-pr-review
description: Review Apache Arrow (arrow-rs) pull requests with a focus on diff analysis, PR discussion accuracy, test and coverage evaluation (including cargo llvm-cov HTML), and public API/breaking change detection. Trigger when the user says "review <PR URL>" or "review https://github.com/apache/arrow-rs/pull/..." or asks to review an arrow-rs PR..
---

# Arrow RS PR Review

Follow this workflow to review an arrow-rs PR for correctness, tests, documentation, API consistency, and coverage.

## Collect PR context

- First ask if you should checkout the PR. If the answer is yes, check it out with `gh`
  - Example: `gh co -f https://github.com/apache/arrow-rs/pull/8930`
- Fetch the merge base via `git fetch apache`
- Use `get_gh_content.sh` to fetch the PR description and comments, then verify claims against the diff and code.
  - Example: `bash ~/bin/get_gh_content.sh <PR_URL>`
- Call out inaccuracies or missing details in the PR text.
- Treat existing PR CI test results as the default evidence for test execution. Avoid rerunning local tests that CI has already validated unless CI is missing, clearly insufficient for the changed behavior, or you need a focused repro to confirm a suspected issue.

## Compute the diff

- Generate the PR diff against `apache/main`:

```bash
git diff `git merge-base HEAD apache/main`
```

## Review checklist

Check for and report issues, highest priority first:

1. Ensure there are tests covering new features and changed behavior.
2. Double check that any newly added tests cover the code in the PR
3. Functions and public APIs documented accurately; comments match behavior.
4. Consistency with existing public APIs and patterns.
6. Breaking public API changes (explicitly call these out).

When evaluating tests, prefer reviewing the tests in the diff, existing nearby tests, and CI test results over rerunning the same test commands locally.


## Ensure tests covering fefatures (cargo llvm-cov)

Only run local `cargo llvm-cov` when you need coverage evidence to answer a concrete review question.

If local coverage is necessary, run:

```bash
cargo llvm-cov --html test -p <crate>
```

To test coverage in multiple crates, you must run a single command such as `cargo llvm-cov --html test -p arrow-data -p arrow-array`

Then review the results:
- Open `target/llvm-cov/html/index.html` and inspect each changed file's HTML report.
- Use “next uncovered line (L)” to find gaps.
- Report uncovered lines that map to new/changed logic or error paths. Include the full file path of the HTML report and line numbers.
- Ignore any “mismatched data” warnings.
- Prefer unit tests near the implementation when coverage is missing.


## Review any newly added tests

Do not routinely rerun newly added tests locally just to duplicate CI. Only do focused local test validation if CI coverage is absent or if you need to confirm that a suspicious new test would actually fail without the code change.

If focused local validation is necessary:
1. Temporarily revert the changes to the code only (do not change tests, such as functions marked with `#[test]` or `#[tokio::test]`)
2. Run only the narrowest relevant tests for the affected crates
3. Ensure that the tests fail
4. Include what tests fail and how they failed as part of the final report


## Final Report (output expectations)

- Present findings in severity order, with file references and line numbers.
- Explicitly note public API changes and whether they are breaking.
- If coverage gaps exist, list them with the HTML report path.
- If no issues are found, state that clearly and mention any residual testing gaps.
- If you did not run local tests or coverage because CI already provided that evidence, say so briefly instead of treating that as a gap.
