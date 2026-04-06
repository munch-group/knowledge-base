#!/usr/bin/env python3
"""Generate a morning digest from GitHub activity stored in knowledge-base JSON."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import anthropic
import click


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, entries):
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def fmt_date(iso):
    """Format ISO date to short form."""
    if not iso:
        return ""
    return iso[:10]


def build_activity_summary(cards, days=None):
    """Build a structured text summary of per-repo activity for the prompt."""
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
def digest(json_file, days, model):
    """Generate a morning digest from GitHub activity in the knowledge base."""
    entries = load(json_file)
    gh_cards = [e for e in entries if e.get("type") == "github" and (e.get("_ghCommits") or e.get("_ghIssuesRecent"))]

    if not gh_cards:
        click.echo("No GitHub cards with activity data found. Run a GitHub sync in the web app first.")
        sys.exit(1)

    activity = build_activity_summary(gh_cards, days=days)
    if not activity.strip():
        click.echo("No activity found" + (f" in the last {days} days" if days else "") + ".")
        sys.exit(0)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        click.echo("Error: ANTHROPIC_API_KEY environment variable not set.", err=True)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    click.echo("Generating digest…", err=True)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(activity=activity)}],
    )

    markdown = response.content[0].text

    # Print plain text to terminal
    click.echo(markdown)

    # Save to JSON as _digest entry
    digest_entry = {
        "id": "_digest",
        "type": "_digest",
        "date": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "markdown": markdown,
    }
    # Upsert: replace existing _digest or append
    entries = [e for e in entries if e.get("id") != "_digest"]
    entries.append(digest_entry)
    save(json_file, entries)
    click.echo(f"\nDigest saved to {json_file}", err=True)


if __name__ == "__main__":
    digest()
