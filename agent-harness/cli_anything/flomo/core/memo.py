"""Memo operations for flomo CLI."""

import re
from typing import Dict, Any, List, Optional
from cli_anything.flomo.utils.api import FlomoAPI, FlomoAPIError


class MemoManager:
    """Manages memo operations."""

    def __init__(self, api: FlomoAPI):
        """Initialize memo manager.

        Args:
            api: FlomoAPI instance
        """
        self.api = api

    def list_memos(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of memos.

        Args:
            limit: Maximum number of memos

        Returns:
            List of memo objects
        """
        return self.api.get_memos(limit=limit)

    def get_memo(self, slug: str) -> Dict[str, Any]:
        """Get a specific memo.

        Args:
            slug: Memo slug

        Returns:
            Memo object
        """
        return self.api.get_memo(slug)

    def create_memo(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        parent_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new memo.

        Args:
            content: Memo content
            tags: List of tags
            parent_slug: Parent memo for replies

        Returns:
            Created memo object
        """
        return self.api.create_memo(content, tags=tags, parent_slug=parent_slug)

    def update_memo(
        self,
        slug: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update an existing memo.

        Args:
            slug: Memo slug
            content: New content
            tags: New tags

        Returns:
            Updated memo object
        """
        return self.api.update_memo(slug, content=content, tags=tags)

    def delete_memo(self, slug: str) -> bool:
        """Delete a memo.

        Args:
            slug: Memo slug

        Returns:
            True if successful
        """
        return self.api.delete_memo(slug)

    def search_memos(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search memos.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memos
        """
        return self.api.search_memos(query, limit=limit)

    def get_pinned_memos(self) -> List[Dict[str, Any]]:
        """Get pinned memos.

        Returns:
            List of pinned memo objects
        """
        return self.api.get_pinned_memos()

    def get_archived_memos(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get archived memos.

        Args:
            limit: Maximum number of memos

        Returns:
            List of archived memo objects
        """
        return self.api.get_archived_memos(limit=limit)

    def get_trash_memos(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get trashed memos.

        Args:
            limit: Maximum number of memos

        Returns:
            List of trashed memo objects
        """
        return self.api.get_trash_memos(limit=limit)

    def pin_memo(self, slug: str) -> Dict[str, Any]:
        """Pin a memo.

        Args:
            slug: Memo slug

        Returns:
            Updated memo object
        """
        return self.api.pin_memo(slug)

    def unpin_memo(self, slug: str) -> Dict[str, Any]:
        """Unpin a memo.

        Args:
            slug: Memo slug

        Returns:
            Updated memo object
        """
        return self.api.unpin_memo(slug)

    def archive_memo(self, slug: str) -> Dict[str, Any]:
        """Archive a memo.

        Args:
            slug: Memo slug

        Returns:
            Updated memo object
        """
        return self.api.archive_memo(slug)

    def unarchive_memo(self, slug: str) -> Dict[str, Any]:
        """Unarchive a memo.

        Args:
            slug: Memo slug

        Returns:
            Updated memo object
        """
        return self.api.unarchive_memo(slug)

    def restore_memo(self, slug: str) -> Dict[str, Any]:
        """Restore a memo from trash.

        Args:
            slug: Memo slug

        Returns:
            Restored memo object
        """
        return self.api.restore_memo(slug)

    def get_memos_by_date(
        self,
        start_date: str,
        end_date: str,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Get memos within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of memos

        Returns:
            List of memo objects
        """
        return self.api.get_memos_by_date(start_date, end_date, limit=limit)

    def get_today_memos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get memos created today.

        Args:
            limit: Maximum number of memos

        Returns:
            List of today's memos
        """
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        return self.get_memos_by_date(today, today, limit=limit)

    def get_recent_memos(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get memos from recent days.

        Args:
            days: Number of days to look back
            limit: Maximum number of memos

        Returns:
            List of recent memos
        """
        from datetime import date, timedelta
        end_date = date.today().strftime("%Y-%m-%d")
        start_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        return self.get_memos_by_date(start_date, end_date, limit=limit)

    def get_random_memo(self, limit: int = 200) -> Optional[Dict[str, Any]]:
        """Get a random memo for inspiration.

        Args:
            limit: Maximum number of memos to sample from

        Returns:
            Random memo or None if no memos
        """
        import random
        memos = self.list_memos(limit=limit)
        if memos:
            return random.choice(memos)
        return None

    def filter_by_tag(self, tag: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Filter memos by tag (partial match).

        Args:
            tag: Tag to filter by (without #). Supports partial match.
            limit: Maximum number of memos to search

        Returns:
            List of memos with the specified tag
        """
        memos = self.list_memos(limit=limit)
        tag_lower = tag.lower().lstrip("#")
        return [
            m for m in memos
            if any(tag_lower in t.lower() for t in m.get("tags", []))
        ]

    def filter_by_content(self, keyword: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Filter memos by content keyword.

        Args:
            keyword: Keyword to search in content
            limit: Maximum number of memos to search

        Returns:
            List of memos containing the keyword
        """
        memos = self.list_memos(limit=limit)
        keyword_lower = keyword.lower()
        return [
            m for m in memos
            if keyword_lower in m.get("content", "").lower()
        ]

    def get_stats(self, limit: int = 500) -> Dict[str, Any]:
        """Get memo statistics.

        Args:
            limit: Maximum number of memos to analyze

        Returns:
            Dict with statistics
        """
        from datetime import datetime
        memos = self.list_memos(limit=limit)

        if not memos:
            return {"total": 0}

        # Count by date
        date_counts = {}
        tag_counts = {}
        total_content_length = 0

        for memo in memos:
            created_at = memo.get("created_at", "")
            if created_at:
                date_str = created_at.split(" ")[0]
                date_counts[date_str] = date_counts.get(date_str, 0) + 1

            for tag in memo.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            content = memo.get("content", "")
            total_content_length += len(content)

        # Find most productive day
        most_productive_day = max(date_counts.items(), key=lambda x: x[1]) if date_counts else (None, 0)

        # Get oldest and newest
        sorted_memos = sorted(memos, key=lambda m: m.get("created_at", ""))
        oldest = sorted_memos[0].get("created_at", "") if sorted_memos else None
        newest = sorted_memos[-1].get("created_at", "") if sorted_memos else None

        return {
            "total": len(memos),
            "unique_tags": len(tag_counts),
            "most_productive_day": most_productive_day[0],
            "most_productive_day_count": most_productive_day[1],
            "avg_content_length": total_content_length // len(memos) if memos else 0,
            "oldest_memo": oldest,
            "newest_memo": newest,
            "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        }

    @staticmethod
    def extract_tags(content: str) -> List[str]:
        """Extract tags from memo content.

        Args:
            content: Memo content (HTML or plain text)

        Returns:
            List of extracted tags
        """
        # Remove HTML tags first
        clean_content = re.sub(r"<[^>]+>", " ", content)

        # Find all #tags (alphanumeric and Chinese characters)
        tag_pattern = r"#([\w\u4e00-\u9fff/]+)"
        tags = re.findall(tag_pattern, clean_content)

        return list(set(tags))

    @staticmethod
    def get_plain_content(content: str) -> str:
        """Get plain text content without HTML.

        Args:
            content: HTML content

        Returns:
            Plain text
        """
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", content)
        # Clean up whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean
