---
name: flomo-cli
description: "Interact with flomo notes using cli-anything-flomo. Use when the user wants to query, create, update, or manage flomo memos and tags. Triggers include - (1) User mentions flomo, (2) User asks to save/write/record notes, (3) User wants to search notes by tag or content, (4) User wants to see recent or specific memos, (5) User wants to manage tags or export data. Works with flomoapp.com desktop app credentials."
---

# flomo-cli

Interact with flomo notes via CLI. Requires flomo desktop app to be installed and logged in.

## Quick Start

```bash
# Check authentication
cli-anything-flomo auth status

# Create a memo
cli-anything-flomo memo create "Your note here" -t tag1 -t tag2

# List recent memos
cli-anything-flomo memo list --limit 20

# Search by tag
cli-anything-flomo memo filter-tag "读书" --output json
```

## Core Workflows

### Creating Memos

```bash
# Simple memo
cli-anything-flomo memo create "Note content"

# With tags (hierarchical supported)
cli-anything-flomo memo create "Reading note" -t "学习笔记/读书/2026"
cli-anything-flomo memo create "Work idea" -t work -t important
```

### Querying Memos

```bash
# List memos (default: local IndexedDB, no 500 limit)
cli-anything-flomo memo list --limit 50 --full

# Filter by tag (partial match)
cli-anything-flomo memo filter-tag "读书"
cli-anything-flomo memo filter-tag "学习" --limit 30

# Filter by content keyword
cli-anything-flomo memo filter-content "AI"

# Date-based queries
cli-anything-flomo memo today
cli-anything-flomo memo recent --days 14
cli-anything-flomo memo by-date 2026-01-01 2026-03-15

# Get specific memo
cli-anything-flomo memo get <slug>

# Random memo for inspiration
cli-anything-flomo memo random
```

### Updating Memos

```bash
# Update content
cli-anything-flomo memo update <slug> --content "New content"

# Pin/unpin
cli-anything-flomo memo pin <slug>
cli-anything-flomo memo unpin <slug>

# Archive/unarchive
cli-anything-flomo memo archive <slug>
cli-anything-flomo memo unarchive <slug>

# Delete
cli-anything-flomo memo delete <slug>

# Restore from trash
cli-anything-flomo memo restore <slug>
```

### Tag Operations

```bash
# List tags
cli-anything-flomo tag list --limit 50
cli-anything-flomo tag list --output tree  # Hierarchical view

# Search tags
cli-anything-flomo tag search "学习"

# Tag statistics
cli-anything-flomo tag stats
```

### User & Statistics

```bash
# User profile
cli-anything-flomo user profile

# User stats
cli-anything-flomo user stats

# Memo statistics
cli-anything-flomo memo stats
```

### Export

```bash
# Export formats: json, markdown, html, csv, obsidian
cli-anything-flomo export run --format markdown --output memos.md
cli-anything-flomo export run --format obsidian --output notes.md
cli-anything-flomo export run --format json --output memos.json
```

## Global Options

| Option | Description |
|--------|-------------|
| `--output json` | JSON output for programmatic use |
| `--source local` | Use local IndexedDB (default, all memos) |
| `--source api` | Use API (max 500 memos) |
| `--config PATH` | Custom config.json path |

## Data Sources

- **local** (default): Reads from IndexedDB, no memo limit
- **api**: Uses flomo API, limited to 500 memos

Always prefer `local` for complete data access.

## JSON Output for AI Agents

All commands support `--output json`:

```bash
cli-anything-flomo memo list --output json
cli-anything-flomo memo filter-tag "读书" --output json
cli-anything-flomo tag list --output json
```

## Common Patterns

### Save a quick note
```bash
cli-anything-flomo memo create "Idea: use AI to summarize notes" -t "想法/2026"
```

### Review recent notes on a topic
```bash
cli-anything-flomo memo filter-tag "读书" --limit 20 --full
```

### Get today's notes
```bash
cli-anything-flomo memo today --output json
```

### Export for backup
```bash
cli-anything-flomo export run --format obsidian -d ~/backup
```
