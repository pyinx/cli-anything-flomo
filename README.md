# cli-anything-flomo

A production-ready CLI for [flomo](https://flomoapp.com/), a note-taking application. Features full access to all memos via local IndexedDB storage, bypassing the API's 500-memo limit.

## Features

- **Memo Management**: Create, read, update, delete, filter, pin, archive memos
- **Local Data Access**: Read all memos from local IndexedDB (no 500-memo limit!)
- **Rich Text Support**: Preserves bold, italic, underline, highlight, lists, images, links
- **User Profile**: View user info with memo and tag statistics
- **Tag Operations**: List, search tags with hierarchical display
- **Export**: Export to JSON, Markdown, HTML, CSV, and Obsidian formats with rich text preservation
- **JSON Output**: All commands support `--output json` for AI agent consumption
- **Native Auth**: Automatically reads credentials from flomo desktop app

## Installation

### Prerequisites

1. **flomo Desktop App**: Must be installed and logged in (required for authentication)
2. **dfindexeddb**: Required for reading local IndexedDB data

```bash
pip install dfindexeddb
```

### Install CLI

```bash
cd agent-harness
pip install -e .
```

### Verify Installation

```bash
cli-anything-flomo --help
# or
python -m cli_anything.flomo.flomo_cli --help
```

### Authentication

**No manual credential configuration needed!** The CLI automatically reads `access_token` from flomo desktop app's config file.

Requirements:
1. [flomo desktop app](https://flomoapp.com/) installed
2. Logged in to your account in the desktop app

The CLI automatically reads credentials from:
- **macOS**: `~/Library/Containers/com.flomoapp.m/Data/Library/Application Support/flomo/config.json`
- **Windows**: `%APPDATA%/flomo/config.json`
- **Linux**: `~/.config/flomo/config.json`

> ⚠️ **Note**: The CLI requires the flomo desktop app to be installed and logged in. flomo does not provide a standalone API token registration process - all API access requires credentials from the desktop app login.

---

## Usage

### Global Options

```bash
--json         Output in JSON format (for AI agents)
--config PATH  Path to flomo config.json
```

### Data Source Selection

Most list commands support `--source` parameter:

```bash
--source local   # Read from local IndexedDB (default, all memos)
--source api     # Read from API (max 500 memos)
```

**Recommendation**: Use `local` (default) for complete data access.

### Output Format

Most list commands support `--output` parameter:

```bash
--output string  # Human-readable text (default)
--output json    # JSON format for programmatic use
```

---

## Commands Reference

### Authentication

```bash
# Check authentication status
flomo auth status

# Test API connection
flomo auth test
```

### User Operations

```bash
# Show user profile
flomo user profile

# Show user statistics (includes memo count, tag analysis)
flomo user stats
```

**Output includes**:
- Account info (ID, username, email, pro status)
- Memo statistics (total analyzed, unique tags, content length)
- Top 10 most used tags

### Memo Operations

#### List Memos

```bash
# List memos (default: 10, from local IndexedDB)
flomo memo list

# List with options
flomo memo list --limit 20
flomo memo list --full          # Show full content
flomo memo list --source api    # Use API instead of local
flomo memo list -l 50 -f -s api # Combined options
flomo memo list --output json   # JSON output
```

#### Create Memo

```bash
# Create a simple memo
flomo memo create "Hello from CLI"

# Create with tags
flomo memo create "Note with tags" -t work -t important

# Tags are automatically converted to #tag format
flomo memo create "My note" -t "学习笔记/读书"
```

#### Get Memo

```bash
# Get memo by slug
flomo memo get MjI0OTQwNDIx
```

#### Update Memo

```bash
flomo memo update <slug> --content "Updated content"
```

#### Delete Memo

```bash
flomo memo delete <slug>
```

#### Filter by Tag

```bash
# Filter memos by tag (partial match)
flomo memo filter-tag "读书"
flomo memo filter-tag "学习" --limit 20
flomo memo filter-tag "读书" --source api
flomo memo filter-tag "读书" --output json
```

**Note**: `filter-tag` uses partial match. Searching "读书" will match:
- `#学习笔记/读书/原则`
- `#学习笔记/读书/金钱的艺术`

#### Filter by Content

```bash
# Filter memos by content keyword
flomo memo filter-content "AI"
flomo memo filter-content "投资" --limit 30
flomo memo filter-content "AI" --source api
flomo memo filter-content "AI" --output json
```

#### Date-based Queries

```bash
# Today's memos (based on created_at)
flomo memo today

# Recent memos (default: 7 days)
flomo memo recent
flomo memo recent --days 14
flomo memo recent -d 30 -l 50
flomo memo recent --output json

# By date range
flomo memo by-date 2024-01-01 2024-01-31
flomo memo by-date 2024-01-01 2024-01-31 --output json
```

#### Random Memo

```bash
# Get a random memo (for inspiration)
flomo memo random
flomo memo random --source api
flomo memo random --output json
```

#### Statistics

```bash
# Show memo statistics (from local by default)
flomo memo stats
flomo memo stats --source api
flomo memo stats --output json
```

#### Pin Operations

```bash
# List pinned memos
flomo memo pinned

# Pin a memo
flomo memo pin <slug>

# Unpin a memo
flomo memo unpin <slug>
```

#### Archive Operations

```bash
# List archived memos
flomo memo archived

# Archive a memo
flomo memo archive <slug>

# Unarchive a memo
flomo memo unarchive <slug>
```

#### Trash Operations

```bash
# List trashed (deleted) memos
flomo memo trash

# Restore a memo from trash
flomo memo restore <slug>
```

**Note**: Trashed memos are only available via API, not from local storage.

### Tag Operations

#### List Tags

```bash
# List all tags (default: 10, from local IndexedDB)
flomo tag list

# List with options
flomo tag list --limit 50
flomo tag list --output tree    # Show in tree format
flomo tag list --search "读书"  # Filter by keyword
flomo tag list --source api     # Use API instead of local
flomo tag list --output json    # JSON output
```

#### Search Tags

```bash
# Search tags by keyword (partial match, case-insensitive)
flomo tag search "读书"
flomo tag search "学习" --limit 20
flomo tag search "读书" --output json
```

#### Tag Statistics

```bash
flomo tag stats
flomo tag stats --output json
```

### Export Operations

The export command supports multiple formats and data sources:

```bash
# Export to JSON (default)
flomo export run
flomo export run --output memos.json
flomo export run -f json -o memos.json

# Export to Markdown
flomo export run --format markdown --output memos.md
flomo export run -f markdown -o memos.md

# Export to HTML
flomo export run --format html --output memos.html

# Export to CSV
flomo export run --format csv --output memos.csv

# Export to Obsidian format (Markdown with YAML frontmatter)
flomo export run --format obsidian --output notes.md

# Export from API instead of local
flomo export run -f json -o memos.json --source api

# Export to a directory (auto-generates filename)
flomo export run -f markdown -d ~/exports
flomo export run -f obsidian -d ~/notes
```

**Supported Formats**:
- `json`: JSON array of memo objects (preserves original HTML content)
- `markdown`: Human-readable Markdown with rich text converted from HTML
- `html`: Styled HTML page (preserves original formatting)
- `csv`: Spreadsheet-compatible CSV (plain text)
- `obsidian`: Obsidian-compatible Markdown with YAML frontmatter and wiki-style links

**Rich Text Support**:

When exporting to Markdown or Obsidian formats, the following flomo formatting is preserved:

| flomo Format | HTML | Markdown Output |
|--------------|------|-----------------|
| Bold | `<strong>`, `<b>` | `**bold**` |
| Italic | `<em>`, `<i>` | `*italic*` |
| Highlight | `<mark>` | `==highlight==` |
| Underline | `<u>` | `<u>underline</u>` (HTML) |
| Strikethrough | `<s>`, `<del>` | `~~strikethrough~~` |
| Unordered List | `<ul><li>` | `- item` |
| Ordered List | `<ol><li>` | `1. item` |
| Link | `<a href>` | `[text](url)` |
| Image | `<img src>` | `![alt](url)` |
| Code | `<code>` | `` `code` `` |
| Blockquote | `<blockquote>` | `> quote` |
| Bidirectional Link (@) | `<a href="flomo://memo/...">` | `[[note-name]]` (Obsidian) |

**Bidirectional Links Support**:

When exporting to Obsidian format, flomo's @ bidirectional links are automatically converted to Obsidian's wikilink format:

- `@note-name` → `[[note-name]]`
- `<a href="flomo://memo/ABC123">@linked-note</a>` → `[[linked-note]]`
- Links with `data-memo-slug` attributes → `[[slug]]`

This allows seamless integration with Obsidian's note-linking system, enabling you to navigate between linked notes directly in Obsidian.

**Note**: HTML export preserves all original formatting. CSV export strips formatting for plain text.

---

## JSON Output (for AI Agents)

All commands support `--output json` flag for machine-readable output:

```bash
flomo --json memo list
flomo memo list --output json
flomo memo filter-tag "读书" --output json
flomo tag list --output json
flomo memo stats --output json
```

---

## Command Summary

| Command | Default Limit | Default Source | Key Options |
|---------|---------------|----------------|-------------|
| `memo list` | 10 | local | `-f` for full content, `-o json` |
| `memo filter-tag` | 100 | local | Partial match, `-o json` |
| `memo filter-content` | 100 | local | Keyword search, `-o json` |
| `memo today` | 100 | local | Based on created_at |
| `memo recent` | 100 | local | `-d` for days, `-o json` |
| `memo by-date` | 200 | local | Date range query |
| `memo random` | 200 | local | Random selection |
| `memo stats` | 500 | local | Statistics, `-o json` |
| `memo trash` | 10 | api | API only |
| `memo archived` | 200 | api | API only |
| `memo pinned` | - | api | API only |
| `tag list` | 10 | local | `-o tree` for hierarchy |
| `tag search` | 10 | local | Partial match |
| `tag stats` | - | local | Usage statistics |
| `export run` | 500 | local | `-f` for format, `-d` for directory |

---

## Development

### Project Structure

```
agent-harness/
├── FLOMO.md              # Software-specific SOP
├── setup.py              # PyPI package config
├── README.md             # This file
└── cli_anything/         # Namespace package (NO __init__.py)
    └── flomo/            # Sub-package
        ├── __init__.py
        ├── flomo_cli.py  # Main CLI entry point
        ├── core/         # Business logic
        │   ├── auth.py
        │   ├── memo.py
        │   ├── tag.py
        │   ├── user.py
        │   └── export.py
        ├── utils/        # Utilities
        │   ├── api.py    # API client with signing
        │   ├── config.py # Config management
        │   ├── idb_reader.py # IndexedDB reader
        │   └── output.py # Output formatting
        └── tests/
            ├── TEST.md
            ├── test_core.py
            └── test_full_e2e.py
```

### Running Tests

```bash
cd agent-harness
pytest cli_anything/flomo/tests/ -v
```

### Key Implementation Details

1. **API Request Signing**: All API requests include MD5 signature with salt
2. **Pagination**: `get_all_memos()` bypasses 500-memo limit via cursor-based pagination
3. **IndexedDB**: Uses `dfindexeddb` to read local Electron/LevelDB storage
4. **Tag Filtering**: Supports partial match for hierarchical tags (e.g., "读书" matches `#学习笔记/读书/原则`)

## API Reference

The CLI uses flomo's REST API:

- **Base URL**: `https://flomoapp.com/api/v1/`
- **Auth**: Bearer token from native app config
- **Signing**: MD5 hash of sorted params + salt (`dbbc3dd73364b4084c3a69346e0ce2b2`)

## License

MIT License
