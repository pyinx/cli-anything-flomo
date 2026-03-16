"""Authentication management for flomo CLI."""

from typing import Dict, Any
from cli_anything.flomo.utils.config import Config
from cli_anything.flomo.utils.api import FlomoAPI, FlomoAPIError


class AuthManager:
    """Manages authentication for flomo CLI."""

    def __init__(self, config: Config = None):
        """Initialize auth manager.

        Args:
            config: Config instance (creates new one if None)
        """
        self.config = config or Config()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated.

        Returns:
            True if valid credentials exist
        """
        try:
            status = self.config.get_auth_status()
            return status.get("authenticated", False)
        except (FileNotFoundError, ValueError):
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get authentication status.

        Returns:
            Status dict with authentication info
        """
        return self.config.get_auth_status()

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection with current credentials.

        Returns:
            Dict with success status and any error message
        """
        if not self.is_authenticated():
            return {
                "success": False,
                "error": "Not authenticated. Please login to flomo app first.",
            }

        try:
            api = FlomoAPI(self.config.access_token)
            memos = api.get_memos(limit=1)
            return {
                "success": True,
                "memo_count": len(memos),
                "user": self.config.username,
            }
        except FlomoAPIError as e:
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
            }
