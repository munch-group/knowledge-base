"""Shared helpers for generating per-repo digests with fingerprint-based caching."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone


DIGEST_SCHEMA_VERSION = 2


SYSTEM_PROMPT = """\
You are a research assistant helping a scientist stay on top of one of their GitHub projects. \
Given recent activity for a single repository, write a short briefing entry summarizing what the work is about and where it stands. \
Be specific - mention commit messages, issue titles. \
Issue labels like "bug", "enhancement", "documentation" indicate the issue type. \
Use this to characterize work (e.g. "2 open bugs", "a feature request for X"). \
Format as markdown. Output exactly the bolded project name on its own line with two trailing spaces, \
then the summary prose on the next line (no blank line between them). Do not output anything else. \
Do NOT mention when anything happened. Do not use absolute dates, relative time phrases ("today", "yesterday", "last week", "two days ago", "about a month ago", "8 months ago", "recently", "recent"), or any other reference to modification times. \
The recency of the work is conveyed separately and must not appear in your prose. Describe only what the work is and its current state. \
Do not use long dashes (em dashes). Use periods or commas instead."""


USER_PROMPT_TEMPLATE = """\
Here is recent activity for a single GitHub project. Write the briefing entry for it.

{activity}"""


def fmt_date(iso):
    if not iso:
        return ""
    return iso[:10]


def filter_card_activity(card, days=None):
    """Return (commits, issues) after applying the --days cutoff. Empty lists if nothing qualifies."""
    commits = card.get("_ghCommits", []) or []
    issues = card.get("_ghIssuesRecent", []) or []
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        commits = [c for c in commits if (c.get("date", "") >= cutoff)]
        issues = [i for i in issues if (i.get("date", "") >= cutoff)]
    return commits, issues


def build_activity_for_card(card, commits, issues):
    """Render the activity block for a single card. Dates are omitted: the digest prose
    must not reference recency (bucketing is done at assembly time from mtimes)."""
    lines = [f"### {card.get('title', card.get('_ghFullName', '?'))}"]
    lines.append(f"URL: {card.get('source', '')}")
    if card.get("content"):
        lines.append(f"Description: {card['content']}")

    if commits:
        lines.append("\nRecent commits:")
        for c in commits:
            lines.append(f"  - [{c['sha']}] {c['msg']}")

    open_issues = [i for i in issues if i.get("state") == "open"]
    closed_issues = [i for i in issues if i.get("state") == "closed"]

    if closed_issues:
        lines.append("\nRecently closed issues:")
        for i in closed_issues:
            labels = ", ".join(i.get("labels", []))
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"  - #{i['number']} {i['title']}{label_str}")

    if open_issues:
        lines.append("\nOpen issues:")
        for i in open_issues:
            labels = ", ".join(i.get("labels", []))
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"  - #{i['number']} {i['title']}{label_str}")

    return "\n".join(lines)


def fingerprint_card(card, commits, issues, days):
    """Stable hash of the inputs the model sees, so unchanged repos can skip regeneration."""
    payload = {
        "v": DIGEST_SCHEMA_VERSION,
        "days": days,
        "commits": [c.get("sha", "") for c in commits],
        "issues": [
            (i.get("number"), i.get("state"), i.get("date"))
            for i in issues
        ],
        "title": card.get("title", ""),
        "source": card.get("source", ""),
        "content": card.get("content", ""),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()


def _summarize_one(card, activity_block, client, model):
    """Call Claude for a single repo. Returns markdown string."""
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(activity=activity_block)}],
    )
    return response.content[0].text.strip()


def _placeholder(card):
    title = card.get("title", card.get("_ghFullName", "?"))
    return f"**{title}**  \n(summary unavailable)"


def refresh_digests(cards, client, model, days=None, max_workers=5, log=None):
    """Ensure each card with activity has an up-to-date `_ghDigest`.

    Returns (ordered_markdown_blocks, stats_dict). `ordered_markdown_blocks` is the list of
    per-repo digest entries in the same order cards were given, already filtered to those with
    activity passing `--days`. Cards are mutated in place: stale `_ghDigest` fields are refreshed.
    """
    log = log or (lambda msg: None)

    active = []
    for card in cards:
        commits, issues = filter_card_activity(card, days=days)
        if not commits and not issues:
            continue
        fp = fingerprint_card(card, commits, issues, days)
        cached = card.get("_ghDigest") or {}
        needs_refresh = cached.get("fingerprint") != fp
        active.append((card, commits, issues, fp, needs_refresh))

    stale = [entry for entry in active if entry[4]]
    log(f"{len(stale)}/{len(active)} repos need re-summarization ({len(active) - len(stale)} cached).")

    if stale:
        def work(entry):
            card, commits, issues, fp, _ = entry
            activity_block = build_activity_for_card(card, commits, issues)
            try:
                md = _summarize_one(card, activity_block, client, model)
            except Exception as e:
                log(f"  Failed {card.get('id', '?')}: {e}")
                prior = (card.get("_ghDigest") or {}).get("markdown")
                md = prior if prior else _placeholder(card)
                return card, fp, md, False
            return card, fp, md, True

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(work, e) for e in stale]
            done = 0
            for fut in as_completed(futures):
                card, fp, md, ok = fut.result()
                done += 1
                if ok:
                    card["_ghDigest"] = {
                        "markdown": md,
                        "fingerprint": fp,
                        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    }
                if done % 10 == 0:
                    log(f"  summarized {done}/{len(stale)}…")

    blocks = []
    for card, commits, issues, _fp, _needs in active:
        digest = card.get("_ghDigest") or {}
        md = digest.get("markdown") or _placeholder(card)
        blocks.append({
            "markdown": md,
            "mtime": card_mtime(card, commits, issues),
        })

    stats = {
        "active": len(active),
        "refreshed": len(stale),
        "cached": len(active) - len(stale),
    }
    return blocks, stats


BUCKETS = [
    ("Past week", 7),
    ("Past month", 30),
    ("Past quarter", 90),
    ("Past year", 365),
    ("Older", None),
]


def card_mtime(card, commits, issues):
    """Latest ISO-8601 timestamp across commits, issues, and the card's own `date` field."""
    candidates = [c.get("date", "") for c in commits]
    candidates += [i.get("date", "") for i in issues]
    candidates.append(card.get("date", "") or "")
    return max((d for d in candidates if d), default="")


def _bucket_for(mtime_iso, now=None):
    if not mtime_iso:
        return "Older"
    now = now or datetime.now(timezone.utc)
    try:
        mt = datetime.fromisoformat(mtime_iso.replace("Z", "+00:00"))
    except ValueError:
        return "Older"
    if mt.tzinfo is None:
        mt = mt.replace(tzinfo=timezone.utc)
    age_days = (now - mt).total_seconds() / 86400.0
    for name, limit in BUCKETS:
        if limit is None or age_days <= limit:
            return name
    return "Older"


def assemble_markdown(blocks, now=None):
    """Group per-repo digest entries under recency section headings.

    `blocks` is a list of {"markdown": str, "mtime": iso str} dicts. Sections appear in the
    order defined by BUCKETS; empty sections are omitted. Within a section, newer repos come first.
    """
    if not blocks:
        return ""
    # Backward-compat: allow raw markdown strings (ungrouped).
    if isinstance(blocks[0], str):
        return "\n\n".join(b.strip() for b in blocks if b and b.strip())

    grouped = {name: [] for name, _ in BUCKETS}
    for b in blocks:
        md = (b.get("markdown") or "").strip()
        if not md:
            continue
        grouped[_bucket_for(b.get("mtime", ""), now=now)].append((b.get("mtime", ""), md))

    out = []
    for name, _ in BUCKETS:
        entries = grouped[name]
        if not entries:
            continue
        entries.sort(key=lambda x: x[0], reverse=True)
        out.append(f"### {name}")
        out.extend(md for _, md in entries)
    return "\n\n".join(out)
