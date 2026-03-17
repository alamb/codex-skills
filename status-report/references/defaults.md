# Status Report Defaults

Use these defaults unless the user asks for a different board, assignee, or filter:

- Organization: `influxdata`
- Project number: `144`
- Assignee: `alamb`
- Matching labels:
  - `team/query`
  - `query`
  - `team/upstream`
  - `upstream`
  - `area/influxql`
  - `Apache Upstream`
- Matching project statuses:
  - `Next`
  - `In Progress`
  - `Blocked/Waiting`
  - `In Review`
- Exclude issues labeled `epic`

The board URL that motivated this skill is:

- `https://github.com/orgs/influxdata/projects/144/views/38`

The collector script uses `gh project item-list --query` with the board-view filter semantics:

- issue or pull request is open
- assigned to the target login
- has at least one of the default labels
- has one of the default project statuses
- does not have the `epic` label

Recent activity is collected with `gh search issues` using:

- `commenter:<login>`
- `author:<login>`
- `reviewed-by:<login>`

This is intentionally broad. After collecting results, match exact item URLs first. Keep anything unmatched in an `other` section and review it manually before drafting updates.

The board query requires a GitHub token with `read:project`.

When presenting results, separate:

- items with matched or clearly related activity and proposed update text
- items with no activity in the selected window
- other recent activity that does not belong to an open board item

Use the item title as the visible identifier in summaries, with the issue URL in parentheses.
