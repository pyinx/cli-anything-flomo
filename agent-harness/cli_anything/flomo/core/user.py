"""User operations for flomo CLI."""

from typing import Dict, Any
from cli_anything.flomo.utils.api import FlomoAPI, FlomoAPIError


class UserManager:
    """Manages user-related operations."""

    def __init__(self, api: FlomoAPI):
        """Initialize user manager.

        Args:
            api: FlomoAPI instance
        """
        self.api = api

    def get_profile(self) -> Dict[str, Any]:
        """Get current user profile.

        Returns:
            User profile dict with id, name, email, pro status, etc.
        """
        return self.api.get_user_info()

    def is_pro(self) -> bool:
        """Check if user has pro subscription.

        Returns:
            True if user is pro subscriber
        """
        profile = self.get_profile()
        return profile.get("pro_type") == "pro"

    def get_pro_expiry(self) -> str:
        """Get pro subscription expiry date.

        Returns:
            Expiry date string or "N/A"
        """
        profile = self.get_profile()
        return profile.get("pro_expired_at", "N/A")

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get user stats summary with memo and tag statistics.

        Returns:
            Dict with user stats including memo counts
        """
        profile = self.get_profile()

        # Get memo statistics from API
        try:
            # Get total memos count (using limit=1 to minimize data transfer)
            memos = self.api.get_memos(limit=500)

            # Count unique tags
            tag_counts = {}
            total_content_length = 0
            for memo in memos:
                for tag in memo.get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                total_content_length += len(memo.get("content", ""))

            # Get date range
            dates = [m.get("created_at", "") for m in memos if m.get("created_at")]
            oldest = min(dates)[:10] if dates else None
            newest = max(dates)[:10] if dates else None

            memo_stats = {
                "total_memos_analyzed": len(memos),
                "unique_tags": len(tag_counts),
                "total_content_length": total_content_length,
                "avg_content_length": total_content_length // len(memos) if memos else 0,
                "oldest_memo_date": oldest,
                "newest_memo_date": newest,
                "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            }
        except Exception:
            memo_stats = {
                "total_memos_analyzed": "N/A",
                "unique_tags": "N/A",
                "error": "Could not fetch memo statistics",
            }

        return {
            "user_id": profile.get("id"),
            "username": profile.get("name"),
            "email": profile.get("email"),
            "is_pro": profile.get("pro_type") == "pro",
            "pro_expires": profile.get("pro_expired_at"),
            "account_created": profile.get("created_at"),
            "language": profile.get("language"),
            "memo_stats": memo_stats,
        }
