#!/usr/bin/env python3
"""Sync GitHub activity and generate a morning digest for the knowledge base."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import anthropic
import click
import urllib.request


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, entries):
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def gh_get(url, token):
    """Make a GitHub API GET request."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def sync_card(card, token):
    """Fetch commits and issues for a single GitHub card. Returns updated card fields."""
    fn = card["_ghFullName"]
    commits_raw = gh_get(f"https://api.github.com/repos/{fn}/commits?per_page=10", token) or []
    issues_raw = gh_get(f"https://api.github.com/repos/{fn}/issues?state=all&sort=updated&direction=desc&per_page=10", token) or []
    latest_raw = gh_get(f"https://api.github.com/repos/{fn}/issues?state=open&per_page=1&sort=created&direction=desc", token) or []

    gh_commits = [
        {"sha": c["sha"][:7], "msg": c["commit"]["message"].split("\n")[0], "date": c["commit"]["author"]["date"]}
        for c in commits_raw if isinstance(c, dict) and "sha" in c
    ]
    issues_no_prs = [i for i in issues_raw if isinstance(i, dict) and not i.get("pull_request")]
    gh_issues = [
        {
            "number": i["number"], "title": i["title"], "state": i["state"],
            "date": i["updated_at"],
            "labels": [l["name"] for l in (i.get("labels") or [])],
            "url": i["html_url"],
        }
        for i in issues_no_prs
    ]
    latest_real = [i for i in latest_raw if isinstance(i, dict) and not i.get("pull_request")]
    latest_issue_date = latest_real[0]["created_at"] if latest_real else None

    return card["id"], gh_commits, gh_issues, latest_issue_date


def fmt_date(iso):
    if not iso:
        return ""
    return iso[:10]


def build_activity_summary(cards, days=None):
    cutoff = None
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    sections = []
    for card in cards:
        commits = card.get("_ghCommits", [])
        issues = card.get("_ghIssuesRecent", [])
        if not commits and not issues:
            continue
        if cutoff:
            commits = [c for c in commits if (c.get("date", "") >= cutoff)]
            issues = [i for i in issues if (i.get("date", "") >= cutoff)]
            if not commits and not issues:
                continue

        lines = [f"### {card.get('title', card.get('_ghFullName', '?'))}"]
        lines.append(f"URL: {card.get('source', '')}")
        if card.get("content"):
            lines.append(f"Description: {card['content']}")
        if commits:
            lines.append("\nRecent commits:")
            for c in commits:
                lines.append(f"  - [{c['sha']}] {c['msg']} ({fmt_date(c['date'])})")

        open_issues = [i for i in issues if i.get("state") == "open"]
        closed_issues = [i for i in issues if i.get("state") == "closed"]
        if closed_issues:
            lines.append("\nRecently closed issues:")
            for i in closed_issues:
                labels = ", ".join(i.get("labels", []))
                label_str = f" [{labels}]" if labels else ""
                lines.append(f"  - #{i['number']} {i['title']}{label_str} ({fmt_date(i['date'])})")
        if open_issues:
            lines.append("\nOpen issues:")
            for i in open_issues:
                labels = ", ".join(i.get("labels", []))
                label_str = f" [{labels}]" if labels else ""
                lines.append(f"  - #{i['number']} {i['title']}{label_str} ({fmt_date(i['date'])})")

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


SYSTEM_PROMPT = """\
You are a research assistant helping a scientist stay on top of their GitHub projects. \
Given activity data from multiple repositories, write a concise morning briefing. \
For each active project, summarize where they left it and what needs attention next. \
Be specific - mention commit messages, issue titles. \
Issue labels like "bug", "enhancement", "documentation" indicate the issue type. \
Use this to characterize work (e.g. "2 open bugs", "a feature request for X"). \
Keep it scannable. \
Format as markdown. Use **bold** for project names on their own line with two trailing spaces for a line break, \
then the summary prose on the next line (no blank line between them). \
Express all dates as relative time in prose (e.g. "two days ago", "about a month ago"), never as absolute dates or abbreviated parenthetical timestamps. \
Do not use long dashes (em dashes). Use periods or commas instead. \
Skip projects with no meaningful activity."""

USER_PROMPT_TEMPLATE = """\
Here is my recent GitHub activity across all projects. \
Write a "Where am I" digest I can read in a few minutes.

{activity}"""


@click.command()
@click.argument("json_file", type=click.Path(exists=True))
@click.option("--days", type=int, default=None, help="Only include activity from the last N days")
@click.option("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
@click.option("--sync-only", is_flag=True, help="Only sync GitHub data, skip digest generation")
def main(json_file, days, model, sync_only):
    """Sync GitHub activity and generate a morning digest."""
    gh_token = os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        click.echo("Error: GITHUB_TOKEN environment variable not set.", err=True)
        sys.exit(1)

    entries = load(json_file)
    gh_cards = [e for e in entries if e.get("type") == "github" and e.get("_ghFullName")]

    if not gh_cards:
        click.echo("No GitHub cards found in JSON. Run a GitHub sync in the web app first to create them.")
        sys.exit(1)

    # Step 1: Sync GitHub activity
    click.echo(f"Syncing {len(gh_cards)} repos…", err=True)
    card_map = {c["id"]: c for c in gh_cards}
    mtime_updated = 0

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(sync_card, card, gh_token): card["id"] for card in gh_cards}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                card_id, commits, issues, latest_date = future.result()
                card = card_map[card_id]
                card["_ghCommits"] = commits
                card["_ghIssuesRecent"] = issues
                if latest_date and latest_date > (card.get("date") or ""):
                    card["date"] = latest_date
                    mtime_updated += 1
            except Exception as e:
                click.echo(f"  Failed {futures[future]}: {e}", err=True)
            if done % 20 == 0:
                click.echo(f"  {done}/{len(gh_cards)}…", err=True)

    save(json_file, entries)
    click.echo(f"Synced {len(gh_cards)} repos ({mtime_updated} dates updated from issues)", err=True)

    if sync_only:
        return

    # Step 2: Generate digest
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        click.echo("Error: ANTHROPIC_API_KEY environment variable not set.", err=True)
        sys.exit(1)

    activity = build_activity_summary(gh_cards, days=days)
    if not activity.strip():
        click.echo("No activity found" + (f" in the last {days} days" if days else "") + ".")
        return

    client = anthropic.Anthropic(api_key=api_key)
    click.echo("Generating digest…", err=True)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(activity=activity)}],
    )

    markdown = response.content[0].text
    click.echo(markdown)

    # Save digest to JSON
    digest_entry = {
        "id": "_digest",
        "type": "_digest",
        "date": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "markdown": markdown,
    }
    entries = load(json_file)  # reload in case web app saved in the meantime
    entries = [e for e in entries if e.get("id") != "_digest"]
    entries.append(digest_entry)
    save(json_file, entries)
    click.echo(f"\nDigest saved to {json_file}", err=True)


if __name__ == "__main__":
    main()
