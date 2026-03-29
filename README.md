# Knowledge Base

A single-file browser app for managing a local JSON knowledge base with Claude memory sync support. Works in Chrome and Edge using the File System Access API.

## Getting started

1. Open `knowledge-base.html` in **Google Chrome** or **Microsoft Edge** (other browsers don't support the File System Access API).
2. Click **Connect file** and select your `knowledge-base.json` file (or create a new empty JSON file containing `[]`).
3. The app remembers your file handle between sessions via IndexedDB, so next time it will reconnect automatically.

## Adding and editing entries

Press the **+ Add** button (or **Cmd+N** / **Ctrl+N**) to create a new entry. Each entry has:

- **Type** — one of: Fact, Idea, Hypothesis, Quote/Para, Reference, Observation, Connection, Person
- **Title** — a short heading for the card
- **Content** — the main body text (supports Markdown, rendered when expanded)
- **Tags** — comma-separated labels for categorisation
- **Genes** — comma-separated gene names (displayed as chips, searchable with `@` syntax)
- **Source** — an optional reference or URL

Press **Save** (or **Cmd+Enter**) to save. The entry is written to your local JSON file immediately.

Click any card to expand it and see the full content. Click the **Edit** button inside an expanded card to modify it. Use the **Delete** button to remove an entry.

## Searching

Type in the search bar to filter entries. The search supports several syntaxes:

| Syntax | Meaning | Example |
|--------|---------|---------|
| free text | matches title, content, tags, genes, source | `tau protein` |
| `#tag` | filter by tag | `#neurodegeneration` |
| `@GENE` | filter by gene | `@MAPT` |
| space between tokens | AND (all must match) | `@MAPT #tau` |
| comma within `@` or `#` | OR (any may match) | `@MAPT,HDAC6` |

**Examples:**

- `@MAPT @HDAC6` — entries that mention **both** MAPT and HDAC6
- `@MAPT,HDAC6` — entries that mention **either** MAPT or HDAC6
- `#review,todo tau` — entries tagged "review" or "todo" that also contain "tau"

You can also click gene chips or tag chips on any card to filter by that gene or tag. Click the back arrow (shown in the page header) to clear filters and return to the full view.

## Sorting

The sidebar has a **Sort** section with three options:

- **Modified** — sort by modification date (default, most recent first)
- **Synced** — sort by sync status (unsynced entries first)
- **Type** — sort alphabetically by entry type

Click an option again to reverse the sort direction.

## Filtering by type and tag

The sidebar also shows **Type** and **Tags** sections. Click any type or tag to filter the view to matching entries. Active filters combine with sorting and search.

## Syncing with Claude's memory

Each entry has a coloured sync status icon: green (synced) or red (unsynced). Editing an entry marks it as unsynced.

There are three sync actions:

1. **Per-entry sync** — Click the sync status icon on any card (or the Sync button in the edit form). This copies a prompt to your clipboard that you can paste into any Claude conversation to update that single entry in Claude's memory.

2. **Sync all** — Click the **Sync all** button in the toolbar. This copies a full-replace prompt covering all entries. Best used when the knowledge base is small or you want a complete refresh.

3. **Cleanup** — Click the **Cleanup** button in the toolbar. This copies a lightweight prompt listing only entry IDs, asking Claude to delete any memory entries that no longer exist locally. Useful for removing stale entries without re-syncing everything.

After pasting a sync prompt into Claude, the corresponding entries are marked as synced.

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| **Cmd+N** (Mac) / **Ctrl+N** (Windows) | Open the Add Entry form |
| **Cmd+Enter** (Mac) | Save the current entry |

## File format

The JSON file is a flat array of entry objects:

```json
[
  {
    "id": "unique-id",
    "type": "fact",
    "title": "Entry title",
    "content": "Markdown content...",
    "tags": ["tag1", "tag2"],
    "genes": ["MAPT", "HDAC6"],
    "source": "https://example.com",
    "date": "2026-03-28T12:00:00.000Z",
    "synced": true
  }
]
```

Valid types: `fact`, `idea`, `hypothesis`, `quote`, `reference`, `observation`, `connection`, `person`.

## Command-line tool (kb-manage.py)

`kb-manage.py` is a Python CLI for batch operations on knowledge-base JSON files. It requires the `click` library (`pip install click`).

```
python3 kb-manage.py COMMAND [ARGS] [OPTIONS]
```

### Tags

```bash
kb-manage.py list-tags data.json                        # list all tags with counts
kb-manage.py list-tags data.json --sort name             # sort alphabetically
kb-manage.py rename-tag data.json "old-name" "new-name"  # rename across all entries
kb-manage.py delete-tag data.json "unwanted"             # remove from all entries
kb-manage.py add-tag data.json "new-tag"                 # add to all entries
kb-manage.py add-tag data.json "reviewed" --where-type fact   # add only to facts
kb-manage.py add-tag data.json "tau" --where-gene MAPT        # add where gene matches
```

### Genes

```bash
kb-manage.py list-genes data.json                        # list all genes with counts
kb-manage.py rename-gene data.json "HDAC6" "HDAC6A"     # rename (case-insensitive match)
kb-manage.py delete-gene data.json "BRCA1"               # remove from all entries
```

### Types

```bash
kb-manage.py list-types data.json                        # list types with counts
kb-manage.py rename-type data.json "quote" "quote_para"  # rename a type
kb-manage.py set-type data.json hypothesis --where-tag speculative  # bulk change type
```

### Removing entries

All removal commands support `--dry-run` to preview without modifying the file.

```bash
kb-manage.py remove-by-tag data.json "deprecated" --dry-run  # preview
kb-manage.py remove-by-tag data.json "deprecated"            # remove for real
kb-manage.py remove-by-type data.json "person"               # remove all of a type
kb-manage.py remove-by-id data.json abc123 def456            # remove specific entries
```

### Search and replace

```bash
kb-manage.py grep data.json "MAPT" -i                    # search (case-insensitive)
kb-manage.py grep data.json "tau" --field content         # search specific field
kb-manage.py replace data.json "BDMI" "BDM incompatibility"          # literal replace
kb-manage.py replace data.json "chr(\d+)" "chromosome \1" --regex    # regex replace
kb-manage.py replace data.json "old text" "new text" --dry-run       # preview changes
```

### Merging and importing files

```bash
kb-manage.py merge target.json source.json               # merge by ID (skip duplicates)
kb-manage.py merge target.json source.json --overwrite   # merge (overwrite duplicates)
kb-manage.py import target.json source.json              # append all (new IDs assigned)
```

### Bulk operations

```bash
kb-manage.py set-synced data.json false                  # mark all as unsynced
kb-manage.py set-synced data.json true --where-tag reviewed  # mark filtered as synced
kb-manage.py touch data.json                             # update all dates to now
kb-manage.py touch data.json --where-tag active          # touch filtered entries
```

### Quality and diagnostics

```bash
kb-manage.py stats data.json       # summary: counts, types, tags, genes, content lengths
kb-manage.py validate data.json    # check for missing fields and unknown types
kb-manage.py clean data.json       # normalize: add missing fields, trim whitespace, dedup tags
kb-manage.py dedup data.json       # remove duplicates by title
kb-manage.py dedup data.json --by content --dry-run  # preview content-based dedup
```

## Web clipper bookmarklet

You can clip selected text from any web page directly into the knowledge base using a browser bookmarklet. It captures your text selection, page URL, and page title to your clipboard. Then switch to the KB tab and press Cmd+V to open the add form pre-filled.

### Setup

Create a new bookmark in Chrome/Edge and paste the following as the URL:

```
javascript:void(function(){var s=window.getSelection().toString().trim();var c=JSON.stringify({_kb_clip:true,content:s||'',source:location.href,title:document.title});navigator.clipboard.writeText(c).then(function(){var b=document.createElement('div');b.textContent='Clipped to KB!';b.style.cssText='position:fixed;top:20px;right:20px;background:#333;color:#fff;padding:8px 16px;border-radius:6px;z-index:999999;font:14px sans-serif';document.body.appendChild(b);setTimeout(function(){b.remove()},1500)})})()
```

Name it something like "Clip to KB".

### Usage

1. Highlight text on any web page.
2. Click the "Clip to KB" bookmark. A brief "Clipped to KB!" toast confirms the copy.
3. Switch to the knowledge base tab.
4. Press **Cmd+V** (or **Ctrl+V**). The add form opens with Content, Source, and Title pre-filled.
5. Choose a type, add tags/genes, and save.

Note: the paste shortcut only triggers the clip import when no input field is focused. If you're already editing a form field, the paste behaves normally.

## Requirements

- Google Chrome or Microsoft Edge (File System Access API required)
- `kb-manage.py` requires Python 3 and `click` (`pip install click`)
