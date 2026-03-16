#!/usr/bin/env python3
"""
cli-anything-flomo - CLI harness for flomo

A production-ready CLI for interacting with flomo's API.

Usage:
    cli-anything-flomo [OPTIONS] COMMAND [ARGS]...

Commands:
    auth    Authentication commands
    memo    Memo operations
    tag     Tag operations
    export  Export operations
"""

import json
import sys
from typing import Optional

import click

from cli_anything.flomo.utils.config import Config
from cli_anything.flomo.utils.api import FlomoAPI, FlomoAPIError
from cli_anything.flomo.utils.output import (
    format_output,
    format_memos_list,
    format_memo,
    format_tags,
)
from cli_anything.flomo.core.auth import AuthManager
from cli_anything.flomo.core.memo import MemoManager
from cli_anything.flomo.core.tag import TagManager
from cli_anything.flomo.core.export import ExportManager
from cli_anything.flomo.core.user import UserManager
from cli_anything.flomo.utils.idb_reader import get_idb_reader


def get_api(ctx: click.Context) -> FlomoAPI:
    """Get API client from context or create new one."""
    if "api" not in ctx.obj:
        config = ctx.obj.get("config") or Config()
        ctx.obj["config"] = config
        ctx.obj["api"] = FlomoAPI(config.access_token)
    return ctx.obj["api"]


def handle_error(error: Exception, is_json: bool) -> None:
    """Handle errors consistently."""
    if is_json:
        click.echo(json.dumps({"error": True, "message": str(error)}), err=True)
    else:
        click.secho(f"Error: {error}", fg="red", err=True)
    sys.exit(1)


@click.group()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option("--config", "config_path", type=click.Path(), help="Path to flomo config.json")
@click.pass_context
def cli(ctx: click.Context, output_json: bool, config_path: Optional[str]) -> None:
    """CLI for flomo - A note-taking app CLI harness."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = output_json
    if config_path:
        ctx.obj["config"] = Config(config_path)


# ============ Auth Commands ============

@cli.group()
def auth() -> None:
    """Authentication commands."""
    pass


@auth.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show authentication status."""
    is_json = ctx.obj["json"]
    try:
        config = ctx.obj.get("config") or Config()
        status_data = config.get_auth_status()

        if is_json:
            click.echo(json.dumps(status_data, indent=2))
        else:
            if status_data.get("authenticated"):
                click.secho("✓ Authenticated", fg="green")
                click.echo(f"  User: {status_data.get('username')}")
                click.echo(f"  User ID: {status_data.get('user_id')}")
                click.echo(f"  Pro: {'Yes' if status_data.get('is_pro') else 'No'}")
                click.echo(f"  Config: {status_data.get('config_path')}")
            else:
                click.secho("✗ Not authenticated", fg="red")
                if "error" in status_data:
                    click.echo(f"  Error: {status_data['error']}")
    except Exception as e:
        handle_error(e, is_json)


@auth.command()
@click.pass_context
def test(ctx: click.Context) -> None:
    """Test API connection."""
    is_json = ctx.obj["json"]
    try:
        auth_manager = AuthManager(ctx.obj.get("config"))
        result = auth_manager.test_connection()

        if is_json:
            click.echo(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                click.secho("✓ Connection successful", fg="green")
                click.echo(f"  User: {result.get('user')}")
                click.echo(f"  Memos accessible: {result.get('memo_count', 'unknown')}")
            else:
                click.secho("✗ Connection failed", fg="red")
                click.echo(f"  Error: {result.get('error')}")
    except Exception as e:
        handle_error(e, is_json)


# ============ Memo Commands ============

@cli.group()
def memo() -> None:
    """Memo operations."""
    pass


@memo.command("list")
@click.option("--limit", "-l", default=10, help="Maximum number of memos to display")
@click.option("--full", "-f", is_flag=True, help="Show full content")
@click.option("--output", "-o", type=click.Choice(["string", "json", "csv"]), default="string",
              help="Output format: 'string' (default), 'json', or 'csv'")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB (all memos), 'api' for API (max 500)")
@click.pass_context
def list_memos(ctx: click.Context, limit: int, full: bool, output: str, source: str) -> None:
    """List memos.

    By default, reads from local IndexedDB which has no 500-memo limit.
    Use --source api to read from the API (limited to 500 memos).

    Use --output to specify format: string, json, or csv.
    """
    is_json = ctx.obj["json"]
    memos = []
    actual_source = source

    try:
        if source == "local":
            # Read from local IndexedDB only, no fallback to API
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api to read from API."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter out empty memos
            memos = [m for m in all_memos if m.get('content') and m['content'].strip() not in ('<p></p>', '<p> </p>')][:limit]
            actual_source = "local"
        else:
            # Read from API
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.list_memos(limit=limit)
            actual_source = "api"

        if output == "json" or is_json:
            result = {
                "memos": memos,
                "count": len(memos),
                "source": actual_source,
                "api_limit_warning": actual_source == "api" and len(memos) >= 500
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        elif output == "csv":
            import csv
            import io
            import re

            output_buffer = io.StringIO()
            writer = csv.writer(output_buffer)
            # Write header
            writer.writerow(["slug", "created_at", "tags", "content"])

            for memo in memos:
                content = memo.get("content", "")
                # Strip HTML tags for CSV
                clean_content = re.sub(r"<[^>]+>", "", content).strip()
                tags = ", ".join(memo.get("tags", []))
                writer.writerow([
                    memo.get("slug", ""),
                    memo.get("created_at", ""),
                    tags,
                    clean_content
                ])

            click.echo(output_buffer.getvalue())
        else:
            if not memos:
                click.echo("No memos found.")
            else:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.echo(f"Found {len(memos)} memos{source_note}:\n")
                click.echo(format_memos_list(memos, brief=not full))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.pass_context
def get(ctx: click.Context, slug: str) -> None:
    """Get a specific memo by slug."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        memo_data = memo_manager.get_memo(slug)

        if is_json:
            click.echo(json.dumps(memo_data, indent=2, ensure_ascii=False))
        else:
            click.echo(format_memo(memo_data))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("content")
@click.option("--tag", "-t", multiple=True, help="Tags for the memo")
@click.pass_context
def create(ctx: click.Context, content: str, tag: tuple) -> None:
    """Create a new memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        tags = list(tag) if tag else None
        result = memo_manager.create_memo(content, tags=tags)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho("✓ Memo created", fg="green")
            click.echo(f"  Slug: {result.get('slug')}")
            click.echo(format_memo(result, show_content=True))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.option("--content", "-c", help="New content")
@click.option("--tag", "-t", multiple=True, help="New tags")
@click.pass_context
def update(ctx: click.Context, slug: str, content: Optional[str], tag: tuple) -> None:
    """Update a memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        tags = list(tag) if tag else None
        result = memo_manager.update_memo(slug, content=content, tags=tags)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho("✓ Memo updated", fg="green")
            click.echo(format_memo(result))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.confirmation_option(prompt="Are you sure you want to delete this memo?")
@click.pass_context
def delete(ctx: click.Context, slug: str) -> None:
    """Delete a memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        memo_manager.delete_memo(slug)

        if is_json:
            click.echo(json.dumps({"success": True, "slug": slug}))
        else:
            click.secho(f"✓ Memo {slug} deleted", fg="green")
    except Exception as e:
        handle_error(e, is_json)




# ============ Tag Commands ============

@cli.group()
def tag() -> None:
    """Tag operations."""
    pass


@tag.command("list")
@click.option("--limit", "-l", default=10, help="Max tags to display")
@click.option("--search", default=None, help="Filter tags by keyword")
@click.option("--level", default=None, help="Filter by tag level (e.g., '1' for level 1, '1,2' for levels 1 and 2)")
@click.option("--output", "-o", type=click.Choice(["string", "json", "tree"]), default="string",
              help="Output format: 'string' (default), 'json', or 'tree'")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB (all memos), 'api' for API (max 500)")
@click.pass_context
def list_tags(ctx: click.Context, limit: int, search: Optional[str], level: Optional[str], output: str, source: str) -> None:
    """List all tags.

    By default, reads from local IndexedDB which has no 500-memo limit.
    Use --source api to read from the API (limited to 500 memos).

    Use --search to filter tags by keyword.
    Use --level to filter by tag depth (e.g., '1' for top-level tags, '1,2' for levels 1 and 2).
    Use --output tree to show tags in a tree structure.
    """
    is_json = ctx.obj["json"]
    tags = []
    tag_stats = {}
    memos_scanned = 0
    actual_source = source

    # Parse level filter
    allowed_levels = None
    if level:
        try:
            allowed_levels = set(int(l.strip()) for l in level.split(",") if l.strip().isdigit())
        except ValueError:
            allowed_levels = None

    def get_tag_level(tag: str) -> int:
        """Get the level of a tag (number of slashes + 1)."""
        return tag.count("/") + 1

    try:
        if source == "local":
            # Read from local IndexedDB only, no fallback to API
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api to read from API."), is_json)
                return
            all_tags = reader.get_tags()
            memos_scanned = len(reader.get_memos())

            # Filter by search keyword if provided
            if search:
                search_lower = search.lower().lstrip("#")
                all_tags = {k: v for k, v in all_tags.items() if search_lower in k.lower()}

            # Filter by level if provided
            if allowed_levels:
                all_tags = {k: v for k, v in all_tags.items() if get_tag_level(k) in allowed_levels}

            tags = list(all_tags.keys())
            tag_stats = all_tags
            actual_source = "local"
        else:
            # Read from API
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            tag_manager = TagManager(memo_manager)

            # Get memos to know how many were scanned
            memos = memo_manager.list_memos(limit=limit)
            tags = tag_manager.get_all_tags(limit=limit)
            tag_stats = tag_manager.get_tag_stats()
            memos_scanned = len(memos)
            actual_source = "api"

            # Filter by search keyword if provided
            if search:
                search_lower = search.lower().lstrip("#")
                tags = [t for t in tags if search_lower in t.lower()]
                tag_stats = {k: v for k, v in tag_stats.items() if k in tags}

            # Filter by level if provided
            if allowed_levels:
                tags = [t for t in tags if get_tag_level(t) in allowed_levels]
                tag_stats = {k: v for k, v in tag_stats.items() if k in tags}

        if output == "json" or is_json:
            result = {
                "tags": tags,
                "stats": tag_stats,
                "memos_scanned": memos_scanned,
                "total_tags": len(tags),
                "source": actual_source,
                "level_filter": level,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        elif output == "tree":
            # Build and display tag hierarchy
            tag_tree = {}
            for tag in sorted(tags):
                parts = tag.split("/")
                current = tag_tree
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            def print_tree(tree, indent=0):
                for name, children in sorted(tree.items()):
                    count = tag_stats.get("/".join([name] * (indent + 1)), 0)
                    # Find the full tag path for this node
                    click.echo(f"{'  ' * indent}# {name}")
                    if children:
                        print_tree(children, indent + 1)

            source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
            level_note = f" (level {level})" if level else ""
            click.echo(f"📊 Tag Tree ({len(tags)} tags{source_note}{level_note}):\n")
            print_tree(tag_tree)
        else:
            source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
            level_note = f" (level {level})" if level else ""
            click.echo(f"Total tags: {len(tags)} (scanned {memos_scanned} memos{source_note}{level_note})\n")
            click.echo(format_tags(tags, tag_stats))
    except Exception as e:
        handle_error(e, is_json)


@tag.command()
@click.option("--limit", "-l", default=10, help="Number of top tags to display")
@click.option("--output", "-o", type=click.Choice(["string", "json", "tree"]), default="string",
              help="Output format: 'string' (default), 'json', or 'tree'")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB (all memos), 'api' for API (max 500)")
@click.pass_context
def stats(ctx: click.Context, limit: int, output: str, source: str) -> None:
    """Show tag usage statistics.

    By default, reads from local IndexedDB which has no 500-memo limit.
    Use --source api to read from the API (limited to 500 memos).
    """
    is_json = ctx.obj["json"]
    try:
        all_tags = {}
        memos_scanned = 0
        actual_source = source

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_tags = reader.get_tags()
            memos_scanned = len(reader.get_memos())
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            tag_manager = TagManager(memo_manager)
            memos = memo_manager.list_memos(limit=500)
            all_tags = tag_manager.get_tag_stats()
            memos_scanned = len(memos)
            actual_source = "api"

        # Sort by count and limit
        sorted_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:limit]

        if output == "json" or is_json:
            result = {
                "top_tags": dict(sorted_tags),
                "total_tags": len(all_tags),
                "displayed": len(sorted_tags),
                "memos_scanned": memos_scanned,
                "source": actual_source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
            click.secho(f"📊 Tag Statistics{source_note}", fg="cyan", bold=True)
            click.echo(f"  Total tags: {len(all_tags)}")
            click.echo(f"  Memos scanned: {memos_scanned}")
            click.echo()
            click.echo(f"Top {limit} tags:\n")
            for tag, count in sorted_tags:
                click.echo(f"  #{tag}: {count}")
    except Exception as e:
        handle_error(e, is_json)




@tag.command()
@click.argument("keyword")
@click.option("--limit", "-l", default=10, help="Max tags to display")
@click.option("--output", "-o", type=click.Choice(["string", "json", "tree"]), default="string",
              help="Output format: 'string' (default), 'json', or 'tree'")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB (all memos), 'api' for API (max 500)")
@click.pass_context
def search(ctx: click.Context, keyword: str, limit: int, output: str, source: str) -> None:
    """Search tags by keyword.

    Searches for tags containing the specified keyword (case-insensitive).

    Example:
        flomo tag search "读书"
        flomo tag search "学习" --limit 20
    """
    is_json = ctx.obj["json"]
    try:
        all_tags = {}
        memos_scanned = 0

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_tags = reader.get_tags()
            memos_scanned = len(reader.get_memos())
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            tag_manager = TagManager(memo_manager)
            memos = memo_manager.list_memos(limit=500)
            all_tags = tag_manager.get_tag_stats()
            memos_scanned = len(memos)

        # Search for matching tags
        keyword_lower = keyword.lower().lstrip("#")
        matching_tags = {
            tag: count for tag, count in all_tags.items()
            if keyword_lower in tag.lower()
        }

        # Sort by count and limit
        sorted_tags = sorted(matching_tags.items(), key=lambda x: x[1], reverse=True)[:limit]

        if output == "json" or is_json:
            result = {
                "keyword": keyword,
                "matching_tags": dict(sorted_tags),
                "total_matches": len(matching_tags),
                "displayed": len(sorted_tags),
                "memos_scanned": memos_scanned,
                "source": source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            source_note = f" (from {source})" if source == "api" else " (from local IndexedDB)"
            click.echo(f"Found {len(matching_tags)} tags matching '{keyword}'{source_note}:\n")

            if sorted_tags:
                for tag, count in sorted_tags:
                    click.echo(f"  #{tag}: {count}")
            else:
                click.echo("  No matching tags found.")
    except Exception as e:
        handle_error(e, is_json)


# ============ Export Commands ============

@cli.group()
def export() -> None:
    """Export operations."""
    pass


@export.command()
@click.option("--limit", "-l", default=None, type=int, help="Max memos to export (optional, local source exports all by default)")
@click.option("--format", "-f", "export_format",
              type=click.Choice(["csv", "html", "json", "markdown", "obsidian"]),
              default="json",
              help="Export format: csv, html, json (single file) or markdown, obsidian (multiple files)")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API (max 500)")
@click.option("--dir", "-d", "output_dir", type=click.Path(), required=True,
              help="Output directory (required)")
@click.option("--filename-format", default="{date}_{slug}_{title}",
              help="Filename format for multi-file exports. Variables: {date}, {slug}, {title}, {tags}. Default: {date}_{slug}_{title}")
@click.pass_context
def run(ctx: click.Context, limit: int, export_format: str, source: str,
        output_dir: str, filename_format: str) -> None:
    """Export memos to various formats.

    Export behavior by format:
      - csv, json, html: Single combined file (all memos in one file)
      - markdown, obsidian: Multiple files (one file per memo)

    Formats:
      - json: JSON format with all memo data including images
      - markdown: Markdown with preserved formatting
      - html: HTML with CSS styling
      - csv: CSV spreadsheet format
      - obsidian: Obsidian-compatible Markdown with frontmatter tags

    Filename format variables (for multi-file exports):
      - {date}: Creation date (YYYYMMDD_HHMMSS)
      - {slug}: Memo slug
      - {title}: First 30 chars of content
      - {tags}: First 3 tags joined by underscore

    Examples:
      flomo export run -f markdown -d ~/exports
      flomo export run -f obsidian -d ~/notes --source api
      flomo export run -f json -d ~/backup --filename-format "{date}_{tags}"
    """
    is_json = ctx.obj["json"]
    memos = []
    actual_source = source

    try:
        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api to read from API."), is_json)
                return
            all_memos = reader.get_memos()
            memos = [m for m in all_memos if m.get('content') and m['content'].strip() not in ('<p></p>', '<p> </p>')]
            # Only apply limit if explicitly specified
            if limit is not None:
                memos = memos[:limit]
            actual_source = "local"

            # Warning about potential issues with local data
            if not is_json and memos:
                click.secho(f"⚠ Note: Local IndexedDB contains {len(memos)} memos.", fg="yellow")
                click.secho("  Local data may include deleted memos or be incomplete.", fg="yellow")
                click.secho("  For accurate recent memos, use --source api (max 500).", fg="yellow")
                click.secho("  To sync all data, open flomo desktop app to trigger full sync.", fg="yellow")
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.list_memos(limit=limit)
            actual_source = "api"

            # Warning about API limit
            if not is_json and len(memos) >= 500:
                click.secho(f"⚠ API returned {len(memos)} memos (max limit reached).", fg="yellow")
                click.secho("  Older memos may not be included. Use --source local for more.", fg="yellow")

        # Create output directory
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Determine output file extension
        ext_map = {
            "json": ".json",
            "markdown": ".md",
            "html": ".html",
            "csv": ".csv",
            "obsidian": ".md",
        }
        file_ext = ext_map[export_format]

        # Single-file formats: csv, json, html
        if export_format in ("csv", "json", "html"):
            export_manager = ExportManager(memos)

            if export_format == "csv":
                result = export_manager.to_csv()
                output_path = os.path.join(output_dir, "flomo_export.csv")
            elif export_format == "json":
                result = export_manager.to_json()
                output_path = os.path.join(output_dir, "flomo_export.json")
            else:  # html
                result = export_manager.to_html()
                output_path = os.path.join(output_dir, "flomo_export.html")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)

            if not is_json:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.secho(f"✓ Exported {len(memos)} memos to {output_path}{source_note}", fg="green")
            return

        # Multi-file formats: markdown, obsidian
        import re
        from datetime import datetime

        def generate_filename(memo: dict) -> str:
            """Generate filename based on format template."""
            slug = memo.get('slug', '') or memo.get('decoded_slug', '')
            created_at = memo.get('created_at', '')
            content = memo.get('content', '')
            tags = memo.get('tags', [])

            # Date component
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y%m%d_%H%M%S')
                except:
                    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            else:
                date_str = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Title component (first 30 chars without HTML)
            text_content = re.sub(r'<[^>]+>', '', content).strip()[:30]
            safe_title = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', text_content)
            safe_title = safe_title.strip('_ ') or 'memo'

            # Tags component (first 3 tags)
            tags_str = '_'.join(tags[:3]) if tags else 'untagged'
            tags_str = re.sub(r'[<>:"/\\|?*]', '_', tags_str)[:30]

            # Build filename from format
            filename = filename_format
            filename = filename.replace('{date}', date_str)
            filename = filename.replace('{slug}', slug[:20] if slug else 'noslug')
            filename = filename.replace('{title}', safe_title[:30])
            filename = filename.replace('{tags}', tags_str)

            # Clean up and ensure valid length
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            if len(filename) > 180:
                filename = filename[:180]

            return filename + file_ext

        exported_count = 0
        for memo in memos:
            filename = generate_filename(memo)
            output_path = os.path.join(output_dir, filename)

            # Generate content for single memo
            single_export = ExportManager([memo])

            if export_format == "markdown":
                result = single_export.to_markdown()
            else:  # obsidian
                result = single_export.to_obsidian_with_frontmatter_tags()

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)
            exported_count += 1

        if not is_json:
            source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
            click.secho(f"✓ Exported {exported_count} memos to {output_dir}{source_note}", fg="green")
    except Exception as e:
        handle_error(e, is_json)


# ============ User Commands ============

@cli.group()
def user() -> None:
    """User profile operations."""
    pass


@user.command()
@click.pass_context
def profile(ctx: click.Context) -> None:
    """Show user profile."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        user_manager = UserManager(api)
        profile_data = user_manager.get_profile()

        if is_json:
            click.echo(json.dumps(profile_data, indent=2, ensure_ascii=False))
        else:
            click.secho("User Profile", fg="cyan", bold=True)
            click.echo(f"  ID: {profile_data.get('id')}")
            click.echo(f"  Username: {profile_data.get('name')}")
            click.echo(f"  Email: {profile_data.get('email')}")
            click.echo(f"  Pro: {'Yes' if profile_data.get('pro_type') == 'pro' else 'No'}")
            if profile_data.get("pro_expired_at"):
                click.echo(f"  Pro Expires: {profile_data.get('pro_expired_at')}")
            click.echo(f"  Created: {profile_data.get('created_at')}")
            click.echo(f"  Language: {profile_data.get('language')}")
    except Exception as e:
        handle_error(e, is_json)


@user.command()
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB (all memos), 'api' for API (max 500)")
@click.pass_context
def stats(ctx: click.Context, source: str) -> None:
    """Show user statistics with memo and tag counts."""
    is_json = ctx.obj["json"]
    try:
        total_memos = 0
        total_tags = 0
        actual_source = source

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            total_memos = len(reader.get_memos())
            total_tags = len(reader.get_tags())
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            tag_manager = TagManager(memo_manager)
            memos = memo_manager.list_memos(limit=500)
            total_memos = len(memos)
            total_tags = len(tag_manager.get_tag_stats())
            actual_source = "api"

        result = {
            "total_memos": total_memos,
            "total_tags": total_tags,
            "source": actual_source,
        }

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
            click.secho(f"📊 User Statistics{source_note}", fg="cyan", bold=True)
            click.echo(f"  📝 Total Memos: {total_memos}")
            click.echo(f"  🏷️  Total Tags: {total_tags}")
    except Exception as e:
        handle_error(e, is_json)


# ============ Extended Memo Commands ============

@memo.command()
@click.pass_context
def pinned(ctx: click.Context) -> None:
    """List pinned memos."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        memos = memo_manager.get_pinned_memos()

        if is_json:
            click.echo(json.dumps(memos, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo("No pinned memos.")
            else:
                click.echo(f"Pinned memos ({len(memos)}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.option("--limit", "-l", default=200, help="Max memos to list")
@click.pass_context
def archived(ctx: click.Context, limit: int) -> None:
    """List archived memos."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        memos = memo_manager.get_archived_memos(limit=limit)

        if is_json:
            click.echo(json.dumps(memos, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo("No archived memos.")
            else:
                click.echo(f"Archived memos ({len(memos)}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.option("--limit", "-l", default=10, help="Max memos to list")
@click.pass_context
def trash(ctx: click.Context, limit: int) -> None:
    """List trashed (deleted) memos.

    Note: Trashed memos are only available via API, not from local storage.
    Use 'memo restore <slug>' to restore a trashed memo.
    """
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        memos = memo_manager.get_trash_memos(limit=limit)

        if is_json:
            click.echo(json.dumps(memos, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo("Trash is empty.")
            else:
                click.echo(f"Trashed memos ({len(memos)}):\n")
                click.echo(format_memos_list(memos))
                click.echo("\nTip: Use 'memo restore <slug>' to restore a memo.")
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.pass_context
def pin(ctx: click.Context, slug: str) -> None:
    """Pin a memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        result = memo_manager.pin_memo(slug)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho(f"✓ Pinned memo {slug}", fg="green")
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.pass_context
def unpin(ctx: click.Context, slug: str) -> None:
    """Unpin a memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        result = memo_manager.unpin_memo(slug)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho(f"✓ Unpinned memo {slug}", fg="green")
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.pass_context
def archive(ctx: click.Context, slug: str) -> None:
    """Archive a memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        result = memo_manager.archive_memo(slug)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho(f"✓ Archived memo {slug}", fg="green")
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.pass_context
def unarchive(ctx: click.Context, slug: str) -> None:
    """Unarchive a memo."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        result = memo_manager.unarchive_memo(slug)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho(f"✓ Unarchived memo {slug}", fg="green")
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("slug")
@click.pass_context
def restore(ctx: click.Context, slug: str) -> None:
    """Restore a memo from trash."""
    is_json = ctx.obj["json"]
    try:
        api = get_api(ctx)
        memo_manager = MemoManager(api)
        result = memo_manager.restore_memo(slug)

        if is_json:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.secho(f"✓ Restored memo {slug}", fg="green")
    except Exception as e:
        handle_error(e, is_json)


@memo.command("by-date")
@click.argument("start_date")
@click.argument("end_date")
@click.option("--limit", "-l", default=200, help="Max memos to return")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.option("--output", "-o", type=click.Choice(["string", "json"]), default="string",
              help="Output format: 'string' (default) or 'json'")
@click.pass_context
def by_date(ctx: click.Context, start_date: str, end_date: str, limit: int, source: str, output: str) -> None:
    """Get memos within a date range (YYYY-MM-DD).

    By default, reads from local IndexedDB which has no 500-memo limit.
    Filters memos by created_at date.
    """
    is_json = ctx.obj["json"]
    try:
        memos = []
        actual_source = source

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter by created_at date range
            filtered = [
                m for m in all_memos
                if start_date <= m.get("created_at", "")[:10] <= end_date
            ]
            # Sort by created_at descending
            filtered.sort(key=lambda m: m.get("created_at", ""), reverse=True)
            memos = filtered[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.get_memos_by_date(start_date, end_date, limit=limit)
            actual_source = "api"

        if output == "json" or is_json:
            result = {
                "memos": memos,
                "count": len(memos),
                "start_date": start_date,
                "end_date": end_date,
                "source": actual_source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo(f"No memos found between {start_date} and {end_date}.")
            else:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.echo(f"Memos from {start_date} to {end_date} ({len(memos)}{source_note}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.option("--limit", "-l", default=100, help="Max memos to display")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.pass_context
def today(ctx: click.Context, limit: int, source: str) -> None:
    """Get today's memos (based on created_at date).

    By default, reads from local IndexedDB which has no 500-memo limit.
    """
    is_json = ctx.obj["json"]
    from datetime import date

    try:
        today_str = date.today().strftime("%Y-%m-%d")

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter by created_at date
            filtered = [
                m for m in all_memos
                if m.get("created_at", "").startswith(today_str)
            ]
            memos = filtered[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.get_today_memos(limit=limit)
            actual_source = "api"

        if is_json:
            result = {
                "memos": memos,
                "count": len(memos),
                "date": today_str,
                "source": actual_source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo("No memos created today.")
            else:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.echo(f"Today's memos ({len(memos)}{source_note}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.option("--days", "-d", default=7, help="Number of days to look back")
@click.option("--limit", "-l", default=100, help="Max memos to display")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.option("--output", "-o", type=click.Choice(["string", "json"]), default="string",
              help="Output format: 'string' (default) or 'json'")
@click.pass_context
def recent(ctx: click.Context, days: int, limit: int, source: str, output: str) -> None:
    """Get recent memos (based on created_at date).

    By default, reads from local IndexedDB which has no 500-memo limit.
    """
    is_json = ctx.obj["json"]
    from datetime import date, timedelta

    try:
        end_date = date.today().strftime("%Y-%m-%d")
        start_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter by created_at date range
            filtered = [
                m for m in all_memos
                if start_date <= m.get("created_at", "")[:10] <= end_date
            ]
            # Sort by created_at descending
            filtered.sort(key=lambda m: m.get("created_at", ""), reverse=True)
            memos = filtered[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.get_recent_memos(days=days, limit=limit)
            actual_source = "api"

        if is_json or output == "json":
            result = {
                "memos": memos,
                "count": len(memos),
                "days": days,
                "date_range": f"{start_date} to {end_date}",
                "source": actual_source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo(f"No memos in the last {days} days.")
            else:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.echo(f"Recent memos (last {days} days, {len(memos)}{source_note}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.option("--limit", "-l", default=200, help="Max memos to sample from")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.option("--output", "-o", type=click.Choice(["string", "json"]), default="string",
              help="Output format: 'string' (default) or 'json'")
@click.pass_context
def random(ctx: click.Context, limit: int, source: str, output: str) -> None:
    """Get a random memo for inspiration.

    By default, reads from local IndexedDB which has no 500-memo limit.
    """
    is_json = ctx.obj["json"]
    import random as rand_module

    try:
        memos = []
        actual_source = source

        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter out empty memos
            useful_memos = [
                m for m in all_memos
                if m.get('content') and m['content'].strip() not in ('<p></p>', '<p> </p>')
            ]
            memos = useful_memos[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.list_memos(limit=limit)
            actual_source = "api"

        if not memos:
            if output == "json" or is_json:
                click.echo(json.dumps({"error": "No memos found"}))
            else:
                click.echo("No memos found.")
        else:
            memo_data = rand_module.choice(memos)

            if output == "json" or is_json:
                result = {
                    "memo": memo_data,
                    "source": actual_source,
                    "sampled_from": len(memos),
                }
                click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                source_note = f" (from {actual_source}, sampled {len(memos)} memos)"
                click.secho(f"✨ Random Memo{source_note}", fg="cyan", bold=True)
                click.echo(format_memo(memo_data))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.argument("tag")
@click.option("--limit", "-l", default=100, help="Max memos to display")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.option("--output", "-o", type=click.Choice(["string", "json"]), default="string",
              help="Output format: 'string' (default) or 'json'")
@click.pass_context
def filter_tag(ctx: click.Context, tag: str, limit: int, source: str, output: str) -> None:
    """Filter memos by tag.

    By default, reads from local IndexedDB which has no 500-memo limit.
    Use --source api to read from the API (limited to 500 memos).
    """
    is_json = ctx.obj["json"]
    memos = []
    actual_source = source

    try:
        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter by tag (partial match - tag can be part of a tag path)
            tag_lower = tag.lower().lstrip("#")
            filtered = [
                m for m in all_memos
                if any(tag_lower in t.lower() for t in m.get("tags", []))
            ]
            memos = filtered[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.filter_by_tag(tag, limit=limit)
            actual_source = "api"

        if is_json or output == "json":
            result = {
                "memos": memos,
                "count": len(memos),
                "tag": tag,
                "source": actual_source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo(f"No memos found with tag: #{tag}")
            else:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.echo(f"Memos with #{tag} ({len(memos)}{source_note}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command("filter-content")
@click.argument("keyword")
@click.option("--limit", "-l", default=100, help="Max memos to display")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.option("--output", "-o", type=click.Choice(["string", "json"]), default="string",
              help="Output format: 'string' (default) or 'json'")
@click.pass_context
def filter_content(ctx: click.Context, keyword: str, limit: int, source: str, output: str) -> None:
    """Filter memos by content keyword.

    By default, reads from local IndexedDB which has no 500-memo limit.
    Use --source api to read from the API (limited to 500 memos).
    """
    is_json = ctx.obj["json"]
    memos = []
    actual_source = source

    try:
        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            # Filter by keyword
            keyword_lower = keyword.lower()
            filtered = [
                m for m in all_memos
                if keyword_lower in m.get("content", "").lower()
            ]
            memos = filtered[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.filter_by_content(keyword, limit=limit)
            actual_source = "api"

        if is_json or output == "json":
            result = {
                "memos": memos,
                "count": len(memos),
                "keyword": keyword,
                "source": actual_source,
            }
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not memos:
                click.echo(f"No memos found containing: {keyword}")
            else:
                source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
                click.echo(f"Memos containing '{keyword}' ({len(memos)}{source_note}):\n")
                click.echo(format_memos_list(memos))
    except Exception as e:
        handle_error(e, is_json)


@memo.command()
@click.option("--limit", "-l", default=None, type=int, help="Max memos to analyze (optional, local source uses all by default)")
@click.option("--source", "-s", type=click.Choice(["local", "api"]), default="local",
              help="Data source: 'local' for IndexedDB, 'api' for API")
@click.option("--output", "-o", type=click.Choice(["string", "json"]), default="string",
              help="Output format: 'string' (default) or 'json'")
@click.pass_context
def stats(ctx: click.Context, limit: int, source: str, output: str) -> None:
    """Show memo statistics.

    By default, reads from local IndexedDB which has no 500-memo limit.
    """
    is_json = ctx.obj["json"]
    actual_source = source

    try:
        memos = []
        if source == "local":
            reader = get_idb_reader()
            if not reader.is_available():
                handle_error(Exception("Local IndexedDB not available. Use --source api."), is_json)
                return
            all_memos = reader.get_memos()
            memos = [m for m in all_memos if m.get('content') and m['content'].strip() not in ('<p></p>', '<p> </p>')]
            # Only apply limit if explicitly specified
            if limit is not None:
                memos = memos[:limit]
            actual_source = "local"
        else:
            api = get_api(ctx)
            memo_manager = MemoManager(api)
            memos = memo_manager.list_memos(limit=limit)
            actual_source = "api"

        # Calculate stats
        import re
        from collections import Counter

        total = len(memos)
        all_tags = []
        content_lengths = []
        dates = []
        oldest = None
        newest = None

        for memo in memos:
            # Tags
            tags = memo.get("tags", [])
            all_tags.extend(tags)

            # Content length
            content = memo.get("content", "")
            clean_content = re.sub(r"<[^>]+>", "", content)
            content_lengths.append(len(clean_content))

            # Dates
            created = memo.get("created_at", "")
            if created:
                dates.append(created[:10])
                if oldest is None or created < oldest:
                    oldest = created
                if newest is None or created > newest:
                    newest = created

        tag_counter = Counter(all_tags)
        date_counter = Counter(dates)
        most_productive_day = date_counter.most_common(1)[0] if date_counter else (None, 0)

        stats_data = {
            "total": total,
            "unique_tags": len(tag_counter),
            "most_productive_day": most_productive_day[0],
            "most_productive_day_count": most_productive_day[1],
            "avg_content_length": sum(content_lengths) // len(content_lengths) if content_lengths else 0,
            "oldest_memo": oldest,
            "newest_memo": newest,
            "top_tags": tag_counter.most_common(10),
            "source": actual_source,
        }

        if is_json or output == "json":
            click.echo(json.dumps(stats_data, indent=2, ensure_ascii=False))
        else:
            source_note = f" (from {actual_source})" if actual_source == "api" else " (from local IndexedDB)"
            click.secho(f"📊 Memo Statistics{source_note}", fg="cyan", bold=True)
            click.echo(f"  Total memos: {stats_data.get('total', 0)}")
            click.echo(f"  Unique tags: {stats_data.get('unique_tags', 0)}")

            if stats_data.get('most_productive_day'):
                click.echo(f"  Most productive day: {stats_data['most_productive_day']} ({stats_data['most_productive_day_count']} memos)")

            click.echo(f"  Avg content length: {stats_data.get('avg_content_length', 0)} chars")

            if stats_data.get('oldest_memo'):
                click.echo(f"  Oldest memo: {stats_data['oldest_memo']}")

            if stats_data.get('newest_memo'):
                click.echo(f"  Newest memo: {stats_data['newest_memo']}")

            if stats_data.get('top_tags'):
                click.echo("\n  Top tags:")
                for tag, count in stats_data['top_tags']:
                    click.echo(f"    #{tag}: {count}")
    except Exception as e:
        handle_error(e, is_json)


def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
