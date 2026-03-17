#!/usr/bin/env python3
"""Collect board items and recent GitHub activity for status-report drafting.

This script is intentionally stdlib-only so it can run in a bare Codex
environment without extra Python dependencies.

Workflow:
1. Query the target GitHub Project V2 board with `gh project item-list`.
2. Apply the skill's assignee / label / project-status filters.
3. Query recent GitHub activity for the assignee with `gh search issues`.
4. Match exact item URLs back to board items when possible.
5. Emit JSON for the assistant to turn into a human-readable report.

Typical usage:
    python3 collect_status_report.py --since 2026-03-10 --json
    python3 collect_status_report.py --since-ts 2026-03-17T06:00:00-04:00 --json

Important limitations:
- The active `gh` token must include the `read:project` scope to read the
  Project V2 board. Without that scope, the script cannot enumerate board items.
- "Recent activity" is based on GitHub search qualifiers (`commenter:`,
  `author:`, and `reviewed-by:`), so it is intentionally broad rather than
  exhaustive.
- Matching is conservative. Exact URL matches are automatic; anything else
  should be reviewed manually before being summarized for the user.
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_ORG = "influxdata"
DEFAULT_PROJECT_NUMBER = 144
DEFAULT_ASSIGNEE = "alamb"
DEFAULT_LABELS = [
    "team/query",
    "query",
    "team/upstream",
    "upstream",
    "area/influxql",
    "Apache Upstream",
]
DEFAULT_STATUSES = ["Next", "In Progress", "Blocked/Waiting", "In Review"]


class StatusReportError(RuntimeError):
    """Raised for expected collector failures that should print cleanly."""


def run_gh(args: List[str]) -> str:
    """Run a `gh` command and return stdout."""
    proc = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "gh command failed"
        if "read:project" in stderr or "`project`" in stderr or "read the Project V2" in stderr:
            raise StatusReportError(
                "GitHub token missing required scope `read:project`; "
                "run `gh auth refresh -s read:project` before using board queries."
            )
        raise StatusReportError(stderr)
    return proc.stdout


def run_gh_json(args: List[str], payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run `gh` and parse its JSON response.

    Keep all GitHub access behind this helper so network failures surface in a
    consistent way and the rest of the script can focus on data shaping.
    """
    cmd = args[:]
    if payload:
        for key, value in payload.items():
            flag = "-F" if isinstance(value, int) else "-f"
            cmd.extend([flag, f"{key}={value}"])
    return json.loads(run_gh(cmd))


def build_project_query(assignee: str, labels: List[str], statuses: List[str]) -> str:
    """Build a GitHub Projects filter query matching the board view."""
    label_query = ",".join(f'"{label}"' if " " in label else label for label in labels)
    status_query = ",".join(f'"{status}"' if " " in status else status for status in statuses)
    return (
        f"assignee:{assignee} is:open "
        f"status:{status_query} "
        f"label:{label_query} "
        "-label:epic"
    )


def fetch_project_items(org: str, project_number: int, query: str) -> List[Dict[str, Any]]:
    """Return raw Project V2 items using `gh project item-list`."""
    stdout = run_gh(
        [
            "project",
            "item-list",
            str(project_number),
            "--owner",
            org,
            "--limit",
            "100",
            "--format",
            "json",
            "--query",
            query,
        ]
    )
    data = json.loads(stdout)
    return data if isinstance(data, list) else data.get("items", [])


def extract_status(item: Dict[str, Any]) -> Optional[str]:
    """Extract the board status from a Project V2 item field-values payload."""
    if isinstance(item.get("status"), str):
        return item["status"]
    field_values = item.get("fieldValues") or item.get("field_values") or []
    if isinstance(field_values, dict):
        field_values = field_values.get("nodes", [])
    for node in field_values:
        field = node.get("field") or {}
        if field.get("name") == "Status":
            return node.get("name")
    return None


def extract_labels(data: Any) -> List[str]:
    """Normalize labels from either a list of strings or GraphQL-style nodes."""
    if not data:
        return []
    if isinstance(data, list):
        if data and isinstance(data[0], str):
            return sorted(data)
        return sorted(
            entry["name"]
            for entry in data
            if isinstance(entry, dict) and isinstance(entry.get("name"), str)
        )
    if isinstance(data, dict):
        nodes = data.get("nodes", [])
        return extract_labels(nodes)
    return []


def extract_assignees(data: Any) -> List[str]:
    """Normalize assignees from either a list of strings or objects."""
    if not data:
        return []
    if isinstance(data, list):
        if data and isinstance(data[0], str):
            return sorted(data)
        return sorted(
            entry["login"]
            for entry in data
            if isinstance(entry, dict) and isinstance(entry.get("login"), str)
        )
    if isinstance(data, dict):
        nodes = data.get("nodes", [])
        return extract_assignees(nodes)
    return []


def normalize_item(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Flatten the GraphQL project-item shape into a smaller Python dict."""
    content = raw.get("content") if isinstance(raw.get("content"), dict) else raw
    if not content:
        return None
    repo = None
    repository = content.get("repository")
    if isinstance(repository, dict):
        repo = repository.get("nameWithOwner") or repository.get("name")
    elif isinstance(repository, str):
        repo = repository
    return {
        "project_item_id": raw.get("id"),
        "type": content.get("__typename") or content.get("type"),
        "repo": repo,
        "number": content.get("number"),
        "title": content.get("title"),
        "url": content.get("url"),
        "state": content.get("state", "OPEN"),
        "status": extract_status(raw),
        "labels": extract_labels(content.get("labels") or raw.get("labels")),
        "assignees": extract_assignees(content.get("assignees") or raw.get("assignees")),
    }


def keep_item(
    item: Dict[str, Any],
    assignee: str,
    statuses: List[str],
    labels: List[str],
) -> bool:
    """Apply the status-report skill's default board filter semantics."""
    if item["state"] != "OPEN":
        return False
    if assignee not in item["assignees"]:
        return False
    if item["status"] not in statuses:
        return False
    if "epic" in item["labels"]:
        return False
    return any(label in item["labels"] for label in labels)


def search_activity(args: List[str]) -> List[Dict[str, Any]]:
    """Search issues/PRs with `gh search issues`."""
    return run_gh_json(
        [
            "search",
            "issues",
            "--include-prs",
            "--limit",
            "100",
            "--json",
            "title,url,repository,state,updatedAt,isPullRequest",
            *args,
        ]
    )


def fetch_recent_activity(org: str, assignee: str, since: str) -> List[Dict[str, Any]]:
    """Collect broad recent activity signals for the assignee.

    The returned objects represent issues or pull requests touched by the user.
    Multiple search sources can map to the same URL, so the result is deduped
    and annotated with the matching sources.
    """
    queries = {
        "commenter": ["--owner", org, "--commenter", assignee, "--updated", f">={since}", "--sort", "updated"],
        "author": ["--owner", org, "--author", assignee, "--updated", f">={since}", "--sort", "updated"],
        "reviewed-by": ["reviewed-by:" + assignee, "--owner", org, "--updated", f">={since}", "--sort", "updated"],
    }
    merged: Dict[str, Dict[str, Any]] = {}
    for source, query_args in queries.items():
        for item in search_activity(query_args):
            item_url = item.get("url") or item.get("html_url")
            if not item_url:
                continue
            entry = merged.setdefault(
                item_url,
                {
                    "url": item_url,
                    "title": item["title"],
                    "repo": item["repository"]["nameWithOwner"] if isinstance(item.get("repository"), dict) else item.get("repo"),
                    "state": item["state"],
                    "updated_at": item.get("updated_at") or item["updatedAt"],
                    "sources": [],
                    "is_pull_request": item.get("is_pull_request") or item.get("isPullRequest", False),
                },
            )
            entry["sources"].append(source)
    return sorted(merged.values(), key=lambda item: item["updated_at"], reverse=True)


def match_activity(open_items: List[Dict[str, Any]], recent_activity: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Match recent activity back to board items using conservative rules."""
    open_by_url = {item["url"]: item for item in open_items}
    open_by_key = {(item["repo"], item["number"]): item for item in open_items}
    matched: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    other: List[Dict[str, Any]] = []

    for activity in recent_activity:
        target = open_by_url.get(activity["url"])
        match_reason = None
        if target:
            match_reason = "exact-url"
        else:
            path = activity["url"].split("/")
            if len(path) >= 2:
                try:
                    repo = "/".join(path[-4:-2])
                    number = int(path[-1])
                    target = open_by_key.get((repo, number))
                    if target:
                        match_reason = "repo-number"
                except ValueError:
                    target = None
        activity["matched_item_url"] = target["url"] if target else None
        activity["match_reason"] = match_reason
        if target:
            matched[target["url"]].append(activity)
        else:
            other.append(activity)
    return {"matched": matched, "other": other}


def parse_since_ts(value: str) -> datetime:
    """Parse an ISO-8601 cutoff timestamp."""
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as err:
        raise StatusReportError(f"invalid --since-ts value {value!r}: {err}") from err
    if parsed.tzinfo is None:
        raise StatusReportError("--since-ts must include a timezone offset")
    return parsed


def activity_timestamp(item: Dict[str, Any]) -> datetime:
    """Parse a normalized activity timestamp into an aware datetime."""
    return datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))


def filter_recent_activity(recent_activity: List[Dict[str, Any]], since_ts: Optional[datetime]) -> List[Dict[str, Any]]:
    """Apply a precise client-side timestamp cutoff when requested."""
    if since_ts is None:
        return recent_activity
    return [item for item in recent_activity if activity_timestamp(item) >= since_ts]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect board items and recent GitHub activity for status updates.",
        epilog=(
            "Example: python3 collect_status_report.py --since 2026-03-10 --json\n"
            "Example: python3 collect_status_report.py --since-ts 2026-03-17T06:00:00-04:00 --json\n"
            "Defaults target the InfluxData project 144 workflow for assignee alamb."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--org", default=DEFAULT_ORG)
    parser.add_argument("--project-number", type=int, default=DEFAULT_PROJECT_NUMBER)
    parser.add_argument("--assignee", default=DEFAULT_ASSIGNEE)
    parser.add_argument("--since", help="Inclusive YYYY-MM-DD activity cutoff")
    parser.add_argument("--since-ts", help="Inclusive ISO-8601 timestamp cutoff with timezone")
    parser.add_argument("--label", action="append", dest="labels", default=None)
    parser.add_argument("--status", action="append", dest="statuses", default=None)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    if not args.since and not args.since_ts:
        parser.error("one of --since or --since-ts is required")
    return args


def main() -> int:
    """Execute the collector and print JSON or a compact text summary."""
    args = parse_args()
    labels = args.labels or list(DEFAULT_LABELS)
    statuses = args.statuses or list(DEFAULT_STATUSES)
    since_ts = parse_since_ts(args.since_ts) if args.since_ts else None
    coarse_since = args.since or (since_ts.date().isoformat() if since_ts else None)

    try:
        project_query = build_project_query(args.assignee, labels, statuses)
        normalized = [normalize_item(item) for item in fetch_project_items(args.org, args.project_number, project_query)]
        open_items = sorted(
            [
                item
                for item in normalized
                if item and keep_item(item, args.assignee, statuses, labels)
            ],
            key=lambda item: (item["repo"], item["number"]),
        )
        recent_activity = fetch_recent_activity(args.org, args.assignee, coarse_since)
        recent_activity = filter_recent_activity(recent_activity, since_ts)
        matched = match_activity(open_items, recent_activity)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "org": args.org,
            "project_number": args.project_number,
            "assignee": args.assignee,
            "since": coarse_since,
            "since_ts": args.since_ts,
            "labels": labels,
            "statuses": statuses,
            "open_items": open_items,
            "recent_activity": recent_activity,
            "matched_activity": matched["matched"],
            "other_activity": matched["other"],
        }

        if args.json:
            json.dump(report, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
            return 0

        print(f"Open items for {args.assignee}: {len(open_items)}")
        for item in open_items:
            print(f"- [{item['status']}] {item['repo']}#{item['number']}: {item['title']}")
            print(f"  {item['url']}")
            item_activity = matched["matched"].get(item["url"], [])
            if item_activity:
                for activity in item_activity[:5]:
                    sources = ", ".join(sorted(set(activity["sources"])))
                    print(f"  activity: {activity['updated_at']} [{sources}] {activity['url']}")
            else:
                print("  activity: none matched by exact URL")

        if matched["other"]:
            print("")
            print("Other recent activity:")
            for activity in matched["other"][:20]:
                sources = ", ".join(sorted(set(activity["sources"])))
                print(f"- {activity['updated_at']} [{sources}] {activity['title']}")
                print(f"  {activity['url']}")
        return 0
    except StatusReportError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
