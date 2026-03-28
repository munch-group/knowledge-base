#!/usr/bin/env python3
"""Command-line tool for batch operations on knowledge-base JSON files."""

import json
import re
import sys
from datetime import datetime, timezone

import click


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, entries):
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


VALID_TYPES = [
    "fact", "idea", "hypothesis", "quote", "reference",
    "observation", "connection", "person",
]


@click.group()
def cli():
    """Batch operations on a knowledge-base JSON file."""
    pass


# ── Tags ────────────────────────────────────────────────────


@cli.command("rename-tag")
@click.argument("file", type=click.Path(exists=True))
@click.argument("old")
@click.argument("new")
def rename_tag(file, old, new):
    """Rename a tag across all entries.  OLD → NEW"""
    entries = load(file)
    n = 0
    for e in entries:
        tags = e.get("tags", [])
        if old in tags:
            tags = [new if t == old else t for t in tags]
            # deduplicate while preserving order
            seen = set()
            e["tags"] = [t for t in tags if not (t in seen or seen.add(t))]
            n += 1
    save(file, entries)
    click.echo(f"Renamed tag '{old}' → '{new}' in {n} entries.")


@cli.command("delete-tag")
@click.argument("file", type=click.Path(exists=True))
@click.argument("tag")
def delete_tag(file, tag):
    """Remove a tag from all entries."""
    entries = load(file)
    n = 0
    for e in entries:
        tags = e.get("tags", [])
        if tag in tags:
            e["tags"] = [t for t in tags if t != tag]
            n += 1
    save(file, entries)
    click.echo(f"Removed tag '{tag}' from {n} entries.")


@cli.command("add-tag")
@click.argument("file", type=click.Path(exists=True))
@click.argument("tag")
@click.option("--where-tag", help="Only add to entries that already have this tag.")
@click.option("--where-type", help="Only add to entries of this type.")
@click.option("--where-gene", help="Only add to entries containing this gene.")
def add_tag(file, tag, where_tag, where_type, where_gene):
    """Add a tag to entries (optionally filtered)."""
    entries = load(file)
    n = 0
    for e in entries:
        if where_tag and where_tag not in e.get("tags", []):
            continue
        if where_type and e.get("type") != where_type:
            continue
        if where_gene and where_gene.upper() not in [g.upper() for g in e.get("genes", [])]:
            continue
        tags = e.get("tags", [])
        if tag not in tags:
            tags.append(tag)
            e["tags"] = tags
            n += 1
    save(file, entries)
    click.echo(f"Added tag '{tag}' to {n} entries.")


@cli.command("list-tags")
@click.argument("file", type=click.Path(exists=True))
@click.option("--sort", "sort_by", type=click.Choice(["name", "count"]), default="count",
              help="Sort by name or count (default: count).")
def list_tags(file, sort_by):
    """List all tags with usage counts."""
    entries = load(file)
    counts = {}
    for e in entries:
        for t in e.get("tags", []):
            counts[t] = counts.get(t, 0) + 1
    if sort_by == "count":
        items = sorted(counts.items(), key=lambda x: -x[1])
    else:
        items = sorted(counts.items())
    for tag, count in items:
        click.echo(f"  {count:4d}  {tag}")
    click.echo(f"\n{len(items)} unique tags across {len(entries)} entries.")


# ── Genes ───────────────────────────────────────────────────


@cli.command("rename-gene")
@click.argument("file", type=click.Path(exists=True))
@click.argument("old")
@click.argument("new")
def rename_gene(file, old, new):
    """Rename a gene across all entries.  OLD → NEW"""
    entries = load(file)
    n = 0
    for e in entries:
        genes = e.get("genes", [])
        matched = [i for i, g in enumerate(genes) if g.upper() == old.upper()]
        if matched:
            for i in matched:
                genes[i] = new
            seen = set()
            e["genes"] = [g for g in genes if not (g.upper() in seen or seen.add(g.upper()))]
            n += 1
    save(file, entries)
    click.echo(f"Renamed gene '{old}' → '{new}' in {n} entries.")


@cli.command("delete-gene")
@click.argument("file", type=click.Path(exists=True))
@click.argument("gene")
def delete_gene(file, gene):
    """Remove a gene from all entries."""
    entries = load(file)
    n = 0
    for e in entries:
        genes = e.get("genes", [])
        if any(g.upper() == gene.upper() for g in genes):
            e["genes"] = [g for g in genes if g.upper() != gene.upper()]
            n += 1
    save(file, entries)
    click.echo(f"Removed gene '{gene}' from {n} entries.")


@cli.command("list-genes")
@click.argument("file", type=click.Path(exists=True))
@click.option("--sort", "sort_by", type=click.Choice(["name", "count"]), default="count")
def list_genes(file, sort_by):
    """List all genes with usage counts."""
    entries = load(file)
    counts = {}
    for e in entries:
        for g in e.get("genes", []):
            key = g.upper()
            counts[key] = counts.get(key, 0) + 1
    if sort_by == "count":
        items = sorted(counts.items(), key=lambda x: -x[1])
    else:
        items = sorted(counts.items())
    for gene, count in items:
        click.echo(f"  {count:4d}  {gene}")
    click.echo(f"\n{len(items)} unique genes across {len(entries)} entries.")


# ── Types ───────────────────────────────────────────────────


@cli.command("rename-type")
@click.argument("file", type=click.Path(exists=True))
@click.argument("old")
@click.argument("new")
def rename_type(file, old, new):
    """Rename a type across all entries.  OLD → NEW"""
    entries = load(file)
    n = sum(1 for e in entries if e.get("type") == old)
    for e in entries:
        if e.get("type") == old:
            e["type"] = new
    save(file, entries)
    click.echo(f"Renamed type '{old}' → '{new}' in {n} entries.")


@cli.command("list-types")
@click.argument("file", type=click.Path(exists=True))
def list_types(file):
    """List all types with usage counts."""
    entries = load(file)
    counts = {}
    for e in entries:
        t = e.get("type", "")
        counts[t] = counts.get(t, 0) + 1
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        click.echo(f"  {c:4d}  {t}")


# ── Remove entries ──────────────────────────────────────────


@cli.command("remove-by-tag")
@click.argument("file", type=click.Path(exists=True))
@click.argument("tag")
@click.option("--dry-run", is_flag=True, help="Show what would be removed without changing the file.")
def remove_by_tag(file, tag, dry_run):
    """Remove all entries that have TAG."""
    entries = load(file)
    keep, drop = [], []
    for e in entries:
        (drop if tag in e.get("tags", []) else keep).append(e)
    if dry_run:
        for e in drop:
            click.echo(f"  would remove: [{e.get('type')}] {e.get('title') or e.get('id')}")
        click.echo(f"\n{len(drop)} entries would be removed ({len(keep)} kept).")
    else:
        save(file, keep)
        click.echo(f"Removed {len(drop)} entries with tag '{tag}' ({len(keep)} kept).")


@cli.command("remove-by-type")
@click.argument("file", type=click.Path(exists=True))
@click.argument("type_name")
@click.option("--dry-run", is_flag=True)
def remove_by_type(file, type_name, dry_run):
    """Remove all entries of TYPE_NAME."""
    entries = load(file)
    keep, drop = [], []
    for e in entries:
        (drop if e.get("type") == type_name else keep).append(e)
    if dry_run:
        for e in drop:
            click.echo(f"  would remove: {e.get('title') or e.get('id')}")
        click.echo(f"\n{len(drop)} entries would be removed ({len(keep)} kept).")
    else:
        save(file, keep)
        click.echo(f"Removed {len(drop)} entries of type '{type_name}' ({len(keep)} kept).")


@cli.command("remove-by-id")
@click.argument("file", type=click.Path(exists=True))
@click.argument("ids", nargs=-1, required=True)
def remove_by_id(file, ids):
    """Remove entries by one or more IDs."""
    entries = load(file)
    id_set = set(ids)
    keep = [e for e in entries if e["id"] not in id_set]
    removed = len(entries) - len(keep)
    save(file, keep)
    click.echo(f"Removed {removed} entries ({len(keep)} kept).")


# ── Search / Replace ────────────────────────────────────────


@cli.command("replace")
@click.argument("file", type=click.Path(exists=True))
@click.argument("pattern")
@click.argument("replacement")
@click.option("--field", multiple=True, default=("content", "title"),
              help="Fields to search (default: content, title). Repeat for multiple.")
@click.option("--regex", "use_regex", is_flag=True, help="Treat PATTERN as a regex.")
@click.option("--dry-run", is_flag=True)
def replace(file, pattern, replacement, field, use_regex, dry_run):
    """Search/replace text across entries."""
    entries = load(file)
    n = 0
    for e in entries:
        changed = False
        for f in field:
            val = e.get(f, "")
            if not isinstance(val, str):
                continue
            if use_regex:
                new_val = re.sub(pattern, replacement, val)
            else:
                new_val = val.replace(pattern, replacement)
            if new_val != val:
                if dry_run:
                    click.echo(f"  [{e.get('id')}] {f}: '{pattern}' found")
                else:
                    e[f] = new_val
                changed = True
        if changed:
            n += 1
    if not dry_run:
        save(file, entries)
    click.echo(f"{'Would modify' if dry_run else 'Modified'} {n} entries.")


@cli.command("grep")
@click.argument("file", type=click.Path(exists=True))
@click.argument("pattern")
@click.option("--field", multiple=True, default=("content", "title", "tags", "genes"),
              help="Fields to search.")
@click.option("-i", "--ignore-case", is_flag=True)
def grep(file, pattern, field, ignore_case):
    """Search entries for PATTERN and print matches."""
    entries = load(file)
    flags = re.IGNORECASE if ignore_case else 0
    rx = re.compile(pattern, flags)
    n = 0
    for e in entries:
        matched_fields = []
        for f in field:
            val = e.get(f, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            if not isinstance(val, str):
                continue
            if rx.search(val):
                matched_fields.append(f)
        if matched_fields:
            title = e.get("title") or e.get("content", "")[:60]
            click.echo(f"  {e['id']}  [{e.get('type')}] {title}")
            click.echo(f"           matched in: {', '.join(matched_fields)}")
            n += 1
    click.echo(f"\n{n} entries matched.")


# ── Merge / Import ──────────────────────────────────────────


@cli.command("merge")
@click.argument("target", type=click.Path(exists=True))
@click.argument("source", type=click.Path(exists=True))
@click.option("--overwrite", is_flag=True,
              help="If an ID exists in both, overwrite with SOURCE version.")
def merge(target, source, overwrite):
    """Merge SOURCE entries into TARGET file."""
    t_entries = load(target)
    s_entries = load(source)
    t_ids = {e["id"]: i for i, e in enumerate(t_entries)}
    added, updated = 0, 0
    for se in s_entries:
        if se["id"] in t_ids:
            if overwrite:
                t_entries[t_ids[se["id"]]] = se
                updated += 1
        else:
            t_entries.append(se)
            added += 1
    save(target, t_entries)
    click.echo(f"Merged: {added} added, {updated} updated. Total: {len(t_entries)}.")


@cli.command("import")
@click.argument("target", type=click.Path(exists=True))
@click.argument("source", type=click.Path(exists=True))
def import_file(target, source):
    """Append all entries from SOURCE into TARGET (new IDs assigned to avoid collisions)."""
    import random
    import string
    t_entries = load(target)
    s_entries = load(source)
    existing_ids = {e["id"] for e in t_entries}
    n = 0
    for se in s_entries:
        while se["id"] in existing_ids:
            se["id"] = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        existing_ids.add(se["id"])
        t_entries.append(se)
        n += 1
    save(target, t_entries)
    click.echo(f"Imported {n} entries into {target}. Total: {len(t_entries)}.")


# ── Bulk field operations ───────────────────────────────────


@cli.command("set-synced")
@click.argument("file", type=click.Path(exists=True))
@click.argument("value", type=click.Choice(["true", "false"]))
@click.option("--where-tag", help="Only affect entries with this tag.")
@click.option("--where-type", help="Only affect entries of this type.")
def set_synced(file, value, where_tag, where_type):
    """Set the synced flag on all (or filtered) entries."""
    entries = load(file)
    val = value == "true"
    n = 0
    for e in entries:
        if where_tag and where_tag not in e.get("tags", []):
            continue
        if where_type and e.get("type") != where_type:
            continue
        if e.get("synced") != val:
            e["synced"] = val
            n += 1
    save(file, entries)
    click.echo(f"Set synced={val} on {n} entries.")


@cli.command("set-type")
@click.argument("file", type=click.Path(exists=True))
@click.argument("new_type")
@click.option("--where-tag", help="Only affect entries with this tag.")
@click.option("--where-type", help="Only affect entries currently of this type.")
def set_type(file, new_type, where_tag, where_type):
    """Change the type of filtered entries."""
    entries = load(file)
    n = 0
    for e in entries:
        if where_tag and where_tag not in e.get("tags", []):
            continue
        if where_type and e.get("type") != where_type:
            continue
        if e.get("type") != new_type:
            e["type"] = new_type
            n += 1
    save(file, entries)
    click.echo(f"Set type='{new_type}' on {n} entries.")


@cli.command("touch")
@click.argument("file", type=click.Path(exists=True))
@click.option("--where-tag", help="Only touch entries with this tag.")
def touch(file, where_tag):
    """Update the date field to now (marks entries as recently modified)."""
    entries = load(file)
    stamp = now_iso()
    n = 0
    for e in entries:
        if where_tag and where_tag not in e.get("tags", []):
            continue
        e["date"] = stamp
        n += 1
    save(file, entries)
    click.echo(f"Touched {n} entries.")


# ── Stats ───────────────────────────────────────────────────


@cli.command("stats")
@click.argument("file", type=click.Path(exists=True))
def stats(file):
    """Print summary statistics for the knowledge base."""
    entries = load(file)
    click.echo(f"Entries:  {len(entries)}")
    # types
    types = {}
    for e in entries:
        t = e.get("type", "?")
        types[t] = types.get(t, 0) + 1
    click.echo("Types:")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        click.echo(f"  {c:4d}  {t}")
    # synced
    synced = sum(1 for e in entries if e.get("synced"))
    click.echo(f"Synced:   {synced}/{len(entries)}")
    # tags
    all_tags = set()
    for e in entries:
        all_tags.update(e.get("tags", []))
    click.echo(f"Tags:     {len(all_tags)} unique")
    # genes
    all_genes = set()
    for e in entries:
        all_genes.update(g.upper() for g in e.get("genes", []))
    click.echo(f"Genes:    {len(all_genes)} unique")
    # content
    lengths = [len(e.get("content", "")) for e in entries]
    if lengths:
        click.echo(f"Content:  {min(lengths)}-{max(lengths)} chars (avg {sum(lengths)//len(lengths)})")
    over = sum(1 for l in lengths if l > 1000)
    if over:
        click.echo(f"          {over} entries over 1000 chars")


# ── Deduplicate ─────────────────────────────────────────────


@cli.command("dedup")
@click.argument("file", type=click.Path(exists=True))
@click.option("--by", "by_field", type=click.Choice(["title", "content", "id"]),
              default="title", help="Field to detect duplicates on.")
@click.option("--dry-run", is_flag=True)
def dedup(file, by_field, dry_run):
    """Remove duplicate entries based on a field."""
    entries = load(file)
    seen = set()
    keep, drop = [], []
    for e in entries:
        key = e.get(by_field, "")
        if isinstance(key, str):
            key = key.strip().lower()
        if key and key in seen:
            drop.append(e)
        else:
            if key:
                seen.add(key)
            keep.append(e)
    if dry_run:
        for e in drop:
            click.echo(f"  would remove: [{e.get('type')}] {e.get('title') or e.get('id')}")
        click.echo(f"\n{len(drop)} duplicates found ({len(keep)} would be kept).")
    else:
        save(file, keep)
        click.echo(f"Removed {len(drop)} duplicates ({len(keep)} kept).")


# ── Validate / Clean ────────────────────────────────────────


@cli.command("validate")
@click.argument("file", type=click.Path(exists=True))
def validate(file):
    """Check entries for schema issues."""
    entries = load(file)
    required = {"id", "type", "content", "title", "tags", "date", "synced"}
    issues = 0
    for i, e in enumerate(entries):
        missing = required - set(e.keys())
        if missing:
            click.echo(f"  entry {i} ({e.get('id','?')}): missing fields: {missing}")
            issues += 1
        if e.get("type") and e["type"] not in VALID_TYPES:
            click.echo(f"  entry {i} ({e.get('id','?')}): unknown type '{e['type']}'")
            issues += 1
        if not e.get("id"):
            click.echo(f"  entry {i}: missing id")
            issues += 1
        if not isinstance(e.get("tags", []), list):
            click.echo(f"  entry {i} ({e.get('id','?')}): tags is not a list")
            issues += 1
        if not isinstance(e.get("genes", []), list):
            click.echo(f"  entry {i} ({e.get('id','?')}): genes is not a list")
            issues += 1
    if issues == 0:
        click.echo(f"All {len(entries)} entries valid.")
    else:
        click.echo(f"\n{issues} issues found in {len(entries)} entries.")


@cli.command("clean")
@click.argument("file", type=click.Path(exists=True))
def clean(file):
    """Normalize entries: ensure all required fields, trim whitespace, sort tags/genes."""
    entries = load(file)
    n = 0
    for e in entries:
        changed = False
        # ensure fields
        for f, default in [("title", ""), ("tags", []), ("genes", []),
                           ("source", ""), ("synced", False)]:
            if f not in e:
                e[f] = default
                changed = True
        # trim strings
        for f in ("title", "content", "source"):
            if isinstance(e.get(f), str) and e[f] != e[f].strip():
                e[f] = e[f].strip()
                changed = True
        # sort and deduplicate tags/genes
        for f in ("tags", "genes"):
            if isinstance(e.get(f), list):
                orig = e[f]
                seen = set()
                deduped = [x for x in orig if not (x in seen or seen.add(x))]
                if deduped != orig:
                    e[f] = deduped
                    changed = True
        if changed:
            n += 1
    save(file, entries)
    click.echo(f"Cleaned {n} entries.")


# ── Prune images ────────────────────────────────────────────


@cli.command("prune-images")
@click.argument("file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without removing files.")
def prune_images(file, dry_run):
    """Delete images in the images/ subfolder that are not referenced by any entry."""
    from pathlib import Path

    entries = load(file)
    base = Path(file).parent
    img_dir = base / "images"

    if not img_dir.is_dir():
        click.echo("No images/ subfolder found.")
        return

    # Collect all image references from content and source fields
    referenced = set()
    for e in entries:
        for field in ("content", "source"):
            text = e.get(field, "")
            if not isinstance(text, str):
                continue
            # Match markdown images: ![...](images/filename)
            for m in re.finditer(r'!\[[^\]]*\]\(images/([^)]+)\)', text):
                referenced.add(m.group(1))
            # Match bare images/ paths (e.g. in HTML img tags)
            for m in re.finditer(r'images/([^\s"\'<>)]+)', text):
                referenced.add(m.group(1))

    # Scan actual files
    on_disk = set()
    for p in img_dir.iterdir():
        if p.is_file():
            on_disk.add(p.name)

    orphaned = on_disk - referenced
    kept = on_disk - orphaned

    if not orphaned:
        click.echo(f"No orphaned images. All {len(on_disk)} images are referenced.")
        return

    for name in sorted(orphaned):
        if dry_run:
            click.echo(f"  would delete: images/{name}")
        else:
            (img_dir / name).unlink()
            click.echo(f"  deleted: images/{name}")

    total_label = "Would delete" if dry_run else "Deleted"
    click.echo(f"\n{total_label} {len(orphaned)} orphaned images ({len(kept)} kept).")


if __name__ == "__main__":
    cli()
