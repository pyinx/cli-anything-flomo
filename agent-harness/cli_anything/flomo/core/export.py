"""Export operations for flomo CLI."""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from cli_anything.flomo.utils.html_converter import (
    html_to_markdown,
    html_to_plain_text,
    convert_at_mentions_to_wikilinks,
    extract_bilinks_from_html
)


def _normalize_tag(tag: str) -> str:
    """Normalize a tag by removing # prefix if present.

    Args:
        tag: Tag string, possibly with # prefix.

    Returns:
        Tag string without # prefix.
    """
    if tag.startswith('#'):
        return tag[1:]
    return tag


def _remove_tags_from_content(content: str, tags: List[str]) -> str:
    """Remove tags from memo content.

    Tags in flomo content appear as #tag or #tag/subtag format.
    This removes them from the content since they're already in frontmatter.

    Args:
        content: The memo content (markdown format).
        tags: List of tags to remove (may or may not have # prefix).

    Returns:
        Content with tags removed.
    """
    result = content
    for tag in tags:
        # Normalize tag (remove # prefix if present)
        tag_normalized = tag[1:] if tag.startswith('#') else tag
        # Remove the tag pattern: #tag or #tag/subtag/etc
        # Use word boundary to avoid partial matches
        # Pattern matches #tag optionally followed by /subtag parts
        pattern = r'#' + re.escape(tag_normalized) + r'(?:/[^\s#<>"\']*)?(?=\s|$|<|>|\.|,|!|\?|;|:|\'|")'
        result = re.sub(pattern, '', result)

    # Clean up multiple spaces that may result from tag removal
    result = re.sub(r'  +', ' ', result)
    # Clean up spaces at the beginning of lines
    result = re.sub(r'^\s+$', '', result, flags=re.MULTILINE)
    # Clean up multiple blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    # Strip leading/trailing whitespace
    result = result.strip()

    return result


class ExportManager:
    """Manages export operations."""

    def __init__(self, memos: List[Dict[str, Any]]):
        """Initialize export manager.

        Args:
            memos: List of memo objects to export
        """
        self.memos = memos

    def to_json(self, indent: int = 2) -> str:
        """Export memos to JSON format.

        Args:
            indent: JSON indentation

        Returns:
            JSON string
        """
        return json.dumps(self.memos, indent=indent, ensure_ascii=False)

    def to_markdown(self, include_metadata: bool = True) -> str:
        """Export memos to Markdown format.

        Converts flomo's HTML content to proper Markdown, preserving:
        - Bold, italic, underline
        - Highlights (using ==text== syntax)
        - Lists (ordered and unordered)
        - Images and links

        Args:
            include_metadata: Include creation date and tags

        Returns:
            Markdown string
        """
        lines = ["# flomo Export\n\n"]
        lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Total memos: {len(self.memos)}\n\n")
        lines.append("---\n\n")

        for memo in self.memos:
            content = memo.get("content", "")
            # Convert HTML to Markdown (preserves formatting)
            markdown_content = html_to_markdown(content)

            if include_metadata:
                created = memo.get("created_at", "")
                tags = memo.get("tags", [])

                lines.append(f"**Created:** {created}\n\n")
                if tags:
                    lines.append(f"**Tags:** {' '.join(['#' + t for t in tags])}\n\n")

            lines.append(f"{markdown_content}\n\n")
            lines.append("---\n\n")

        return "".join(lines)

    def to_html(self, include_styles: bool = True) -> str:
        """Export memos to HTML format.

        Args:
            include_styles: Include CSS styles

        Returns:
            HTML string
        """
        lines = ["<!DOCTYPE html>", "<html lang='zh-CN'>", "<head>", "<meta charset='UTF-8'>", "<title>flomo Export</title>"]

        if include_styles:
            lines.append("""
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    background: #f5f5f5;
}
.memo {
    background: white;
    padding: 20px;
    margin-bottom: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.memo-meta {
    color: #666;
    font-size: 0.9em;
    margin-bottom: 10px;
}
.memo-content {
    line-height: 1.6;
}
.memo-content ul, .memo-content ol {
    margin: 10px 0;
    padding-left: 20px;
}
.memo-content li {
    margin: 5px 0;
}
.memo-content mark {
    background-color: #fff3cd;
    padding: 2px 4px;
    border-radius: 2px;
}
.memo-content u {
    text-decoration: underline;
}
.memo-content img {
    max-width: 100%;
    border-radius: 4px;
    margin: 10px 0;
}
.memo-content a {
    color: #1976d2;
    text-decoration: none;
}
.memo-content a:hover {
    text-decoration: underline;
}
.tag {
    background: #e3f2fd;
    color: #1976d2;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85em;
}
</style>
""")

        lines.extend(["</head>", "<body>", "<h1>flomo Export</h1>"])
        lines.append(f"<p>Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        lines.append(f"<p>Total memos: {len(self.memos)}</p>")

        for memo in self.memos:
            content = memo.get("content", "")
            created = memo.get("created_at", "")
            tags = memo.get("tags", [])

            lines.append("<div class='memo'>")
            lines.append("<div class='memo-meta'>")
            lines.append(f"<span>{created}</span>")
            if tags:
                tags_html = " ".join([f"<span class='tag'>#{tag}</span>" for tag in tags])
                lines.append(f" {tags_html}")
            lines.append("</div>")
            lines.append(f"<div class='memo-content'>{content}</div>")
            lines.append("</div>")

        lines.extend(["</body>", "</html>"])

        return "\n".join(lines)

    def to_csv(self) -> str:
        """Export memos to CSV format.

        Returns:
            CSV string
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["slug", "created_at", "updated_at", "tags", "content"])

        for memo in self.memos:
            # Convert to plain text for CSV
            content = html_to_plain_text(memo.get("content", ""))
            content = content.replace("\n", " ").strip()
            tags = "|".join(memo.get("tags", []))

            writer.writerow([
                memo.get("slug", ""),
                memo.get("created_at", ""),
                memo.get("updated_at", ""),
                tags,
                content,
            ])

        return output.getvalue()

    def to_obsidian(self, include_metadata: bool = True) -> str:
        """Export memos to Obsidian-compatible Markdown format.

        Creates one file per memo with YAML frontmatter for tags and dates.
        This format is optimized for Obsidian's linking and search features.

        Converts flomo's HTML content to proper Markdown, preserving:
        - Bold, italic, underline (as HTML tags)
        - Highlights (using ==text== syntax)
        - Lists (ordered and unordered)
        - Images and links
        - Wiki-style links for tags
        - Bidirectional links (@ mentions) converted to [[wikilink]] format

        Args:
            include_metadata: Include YAML frontmatter with metadata

        Returns:
            Obsidian-compatible Markdown string (combined for single-file export)
        """
        lines = ["# flomo Export (Obsidian Format)\n\n"]
        lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Total memos: {len(self.memos)}\n\n")
        lines.append("---\n\n")

        for i, memo in enumerate(self.memos, 1):
            content = memo.get("content", "")
            # Convert HTML to Markdown with bidirectional link support
            # This handles HTML links (flomo://) that contain @ mentions
            markdown_content = html_to_markdown(
                content,
                convert_bilinks_to_wikilinks=True
            )

            # Also convert any remaining plain @ mentions in text
            # (these are @ mentions that weren't inside HTML links)
            markdown_content = convert_at_mentions_to_wikilinks(markdown_content)

            created = memo.get("created_at", "")
            tags = memo.get("tags", [])  # Keep original tags
            slug = memo.get("slug", "")
            # Support both 'file_ids' (old format) and 'files' (new format with full info)
            files = memo.get("files") or []
            # Extract file IDs for backward compatibility
            file_ids = []
            if files:
                for f in files:
                    if isinstance(f, dict) and 'id' in f:
                        file_ids.append(f['id'])
                    elif isinstance(f, (int, str)):
                        file_ids.append(f)
            # Also check legacy file_ids field
            if not file_ids and memo.get("file_ids"):
                file_ids = memo["file_ids"]

            if include_metadata:
                # YAML frontmatter
                lines.append("---\n")
                lines.append(f"slug: {slug}\n")
                lines.append(f"created: {created}\n")
                if tags:
                    # Obsidian expects inline array format: tags: ['#tag1', '#tag2']
                    # Ensure tags have # prefix
                    tags_with_prefix = [t if t.startswith('#') else f'#{t}' for t in tags]
                    tags_yaml = ", ".join([f"'{t}'" for t in tags_with_prefix])
                    lines.append(f"tags: [{tags_yaml}]\n")

                # Add bidirectional links to frontmatter if present
                bilinks = extract_bilinks_from_html(content)
                if bilinks:
                    bilink_slugs = [bl[2] for bl in bilinks]  # Extract slugs
                    bilinks_yaml = ", ".join([f'"{s}"' for s in bilink_slugs])
                    lines.append(f"links: [{bilinks_yaml}]\n")

                # Add image IDs to frontmatter
                if file_ids:
                    files_yaml = ", ".join([f'"{fid}"' for fid in file_ids])
                    lines.append(f"images: [{files_yaml}]\n")

                lines.append("---\n\n")

            # Title based on first line or slug
            first_line = markdown_content.split("\n")[0][:50] if markdown_content else f"Memo {i}"
            # Remove markdown formatting from title
            first_line_clean = re.sub(r'[*=_~`#\[\]]', '', first_line).strip()
            lines.append(f"## {first_line_clean}\n\n")

            # Remove tags from content since they're already in frontmatter
            content_clean = _remove_tags_from_content(markdown_content, tags)

            lines.append(f"{content_clean}\n\n")

            lines.append("---\n\n")

        return "".join(lines)

    def to_obsidian_with_frontmatter_tags(self) -> str:
        """Export single memo to Obsidian format with tags in frontmatter.

        This is used for per-memo file export where tags should be in
        Obsidian's frontmatter tags field for proper tag indexing.

        Returns:
            Obsidian-compatible Markdown string for single memo
        """
        if len(self.memos) != 1:
            # Fallback to regular obsidian format for multiple memos
            return self.to_obsidian()

        memo = self.memos[0]
        content = memo.get("content", "")
        markdown_content = html_to_markdown(
            content,
            convert_bilinks_to_wikilinks=True
        )
        markdown_content = convert_at_mentions_to_wikilinks(markdown_content)

        created = memo.get("created_at", "")
        tags = memo.get("tags", [])  # Keep original tags
        slug = memo.get("slug", "")
        # Support both 'file_ids' (old format) and 'files' (new format with full info)
        files = memo.get("files") or []
        # Extract file IDs for backward compatibility
        file_ids = []
        if files:
            for f in files:
                if isinstance(f, dict) and 'id' in f:
                    file_ids.append(f['id'])
                elif isinstance(f, (int, str)):
                    file_ids.append(f)
        # Also check legacy file_ids field
        if not file_ids and memo.get("file_ids"):
            file_ids = memo["file_ids"]

        lines = []

        # YAML frontmatter with Obsidian-style tags
        lines.append("---\n")
        lines.append(f"slug: {slug}\n")
        lines.append(f"created: {created}\n")

        # Obsidian expects inline array format: tags: ['#tag1', '#tag2']
        if tags:
            # Ensure tags have # prefix
            tags_with_prefix = [t if t.startswith('#') else f'#{t}' for t in tags]
            tags_yaml = ", ".join([f"'{t}'" for t in tags_with_prefix])
            lines.append(f"tags: [{tags_yaml}]\n")

        # Add bidirectional links to frontmatter if present
        bilinks = extract_bilinks_from_html(content)
        if bilinks:
            bilink_slugs = [bl[2] for bl in bilinks]
            bilinks_yaml = "\n".join([f"  - {s}" for s in bilink_slugs])
            lines.append(f"links:\n{bilinks_yaml}\n")

        # Add image IDs to frontmatter
        if file_ids:
            files_yaml = "\n".join([f"  - {f}" for f in file_ids])
            lines.append(f"images:\n{files_yaml}\n")

        lines.append("---\n\n")

        # Remove tags from content since they're already in frontmatter
        content_clean = _remove_tags_from_content(markdown_content, tags)

        lines.append(f"{content_clean}\n")

        return "".join(lines)
