"""Output formatting utilities for flomo CLI."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


def format_memo(memo: Dict[str, Any], show_content: bool = True) -> str:
    """Format a single memo for display.

    Args:
        memo: Memo object from API
        show_content: Whether to show full content

    Returns:
        Formatted string
    """
    lines = []

    # Slug and date
    slug = memo.get("slug", "N/A")
    created_at = memo.get("created_at", "")
    lines.append(f"Slug: {slug}")
    lines.append(f"Created: {created_at}")

    # Tags
    tags = memo.get("tags", [])
    if tags:
        lines.append(f"Tags: {', '.join(tags)}")

    # Content
    if show_content:
        content = memo.get("content", "")
        # Strip HTML tags for display
        clean_content = re.sub(r"<[^>]+>", "", content)
        lines.append(f"\n{clean_content}")

    return "\n".join(lines)


def format_memo_brief(memo: Dict[str, Any], max_length: int = 80) -> str:
    """Format a memo for brief (one-line) display.

    Args:
        memo: Memo object from API
        max_length: Maximum line length

    Returns:
        Formatted string
    """
    content = memo.get("content", "")
    # Strip HTML tags
    clean_content = re.sub(r"<[^>]+>", "", content)
    clean_content = clean_content.replace("\n", " ").strip()

    if len(clean_content) > max_length:
        clean_content = clean_content[:max_length - 3] + "..."

    tags = memo.get("tags", [])
    tag_str = " ".join([f"#{tag}" for tag in tags])

    slug = memo.get("slug", "N/A")
    date = memo.get("created_at", "")[:10] if memo.get("created_at") else "N/A"

    return f"{date} [{slug}] {clean_content} {tag_str}"


def format_memos_list(memos: List[Dict[str, Any]], brief: bool = True) -> str:
    """Format a list of memos for display.

    Args:
        memos: List of memo objects
        brief: Use brief format

    Returns:
        Formatted string
    """
    if not memos:
        return "No memos found."

    lines = []
    for memo in memos:
        if brief:
            lines.append(format_memo_brief(memo))
        else:
            lines.append(format_memo(memo))
            lines.append("-" * 40)

    return "\n".join(lines)


def format_tags(tags: List[str], counts: Optional[Dict[str, int]] = None) -> str:
    """Format tags for display.

    Args:
        tags: List of tag names
        counts: Optional tag usage counts

    Returns:
        Formatted string
    """
    if not tags:
        return "No tags found."

    lines = []
    for tag in sorted(tags):
        if counts and tag in counts:
            lines.append(f"  #{tag} ({counts[tag]})")
        else:
            lines.append(f"  #{tag}")

    return "\n".join(lines)


def format_output(data: Any, is_json: bool, formatter=None) -> str:
    """Format output based on json flag.

    Args:
        data: Data to format
        is_json: Output as JSON
        formatter: Optional formatter function for non-JSON output

    Returns:
        Formatted string
    """
    if is_json:
        return json.dumps(data, indent=2, ensure_ascii=False)
    elif formatter:
        return formatter(data)
    else:
        return str(data)
