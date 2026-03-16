"""Tag operations for flomo CLI."""

from typing import Dict, List, Tuple
from collections import Counter
from cli_anything.flomo.core.memo import MemoManager


class TagManager:
    """Manages tag operations."""

    def __init__(self, memo_manager: MemoManager):
        """Initialize tag manager.

        Args:
            memo_manager: MemoManager instance
        """
        self.memo_manager = memo_manager
        self._tag_cache: Dict[str, int] = {}

    def get_all_tags(self, limit: int = 500) -> List[str]:
        """Get all unique tags from memos.

        Args:
            limit: Maximum memos to scan

        Returns:
            List of unique tag names
        """
        memos = self.memo_manager.list_memos(limit=limit)
        tag_counter = Counter()

        for memo in memos:
            tags = memo.get("tags", [])
            for tag in tags:
                tag_counter[tag] += 1

        self._tag_cache = dict(tag_counter)
        return list(tag_counter.keys())

    def get_tag_stats(self, limit: int = 500) -> Dict[str, int]:
        """Get tag usage statistics.

        Args:
            limit: Maximum memos to scan

        Returns:
            Dict mapping tag name to usage count
        """
        if not self._tag_cache:
            self.get_all_tags(limit=limit)
        return self._tag_cache

    def get_top_tags(self, n: int = 10, limit: int = 500) -> List[Tuple[str, int]]:
        """Get top N most used tags.

        Args:
            n: Number of top tags to return
            limit: Maximum memos to scan

        Returns:
            List of (tag, count) tuples
        """
        stats = self.get_tag_stats(limit=limit)
        sorted_tags = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags[:n]

    def find_memos_by_tag(self, tag: str, limit: int = 50) -> List[Dict]:
        """Find memos with a specific tag.

        Args:
            tag: Tag to search for
            limit: Maximum memos to return

        Returns:
            List of matching memos
        """
        memos = self.memo_manager.list_memos(limit=500)
        matching = []

        # Normalize tag (remove # prefix if present)
        tag = tag.lstrip("#")

        for memo in memos:
            if tag in memo.get("tags", []):
                matching.append(memo)
                if len(matching) >= limit:
                    break

        return matching
