"""Configuration management for flomo CLI."""

import json
import platform
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Manages flomo CLI configuration and credentials."""

    # Platform-specific flomo config locations
    FLOMO_CONFIG_PATHS = {
        "Darwin": "~/Library/Containers/com.flomoapp.m/Data/Library/Application Support/flomo/config.json",
        "Windows": "%APPDATA%/flomo/config.json",
        "Linux": "~/.config/flomo/config.json",
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Optional path to flomo config.json
        """
        self._config_path = config_path
        self._flomo_config: Optional[Dict[str, Any]] = None

    @property
    def flomo_config_path(self) -> Path:
        """Get the path to flomo's native config.json."""
        if self._config_path:
            return Path(self._config_path).expanduser()

        system = platform.system()
        path_template = self.FLOMO_CONFIG_PATHS.get(system)
        if not path_template:
            raise NotImplementedError(f"Unsupported platform: {system}")

        # Expand environment variables and user home
        path = Path(path_template)
        if "%" in path_template:
            # Windows path with env vars
            import os
            expanded = os.path.expandvars(path_template)
            path = Path(expanded)
        else:
            path = path.expanduser()

        return path

    @property
    def flomo_config(self) -> Dict[str, Any]:
        """Load and cache flomo's native configuration."""
        if self._flomo_config is None:
            config_path = self.flomo_config_path
            if not config_path.exists():
                raise FileNotFoundError(
                    f"flomo config not found at {config_path}. "
                    "Please ensure flomo is installed and you have logged in."
                )

            with open(config_path, "r", encoding="utf-8") as f:
                self._flomo_config = json.load(f)

        return self._flomo_config

    @property
    def user_info(self) -> Dict[str, Any]:
        """Get user information from flomo config."""
        return self.flomo_config.get("user", {})

    @property
    def access_token(self) -> str:
        """Get the access token for API authentication."""
        token = self.user_info.get("access_token")
        if not token:
            raise ValueError("No access_token found in flomo config")
        return token

    @property
    def api_token(self) -> str:
        """Get the API token."""
        return self.user_info.get("api_token", "")

    @property
    def user_id(self) -> int:
        """Get the user ID."""
        return self.user_info.get("id", 0)

    @property
    def username(self) -> str:
        """Get the username."""
        return self.user_info.get("name", "")

    @property
    def user_slug(self) -> str:
        """Get the user's slug (Base64 encoded ID)."""
        return self.user_info.get("slug", "")

    @property
    def is_pro(self) -> bool:
        """Check if user has pro subscription."""
        return self.user_info.get("pro_type") == "pro"

    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status summary."""
        try:
            return {
                "authenticated": True,
                "user_id": self.user_id,
                "username": self.username,
                "is_pro": self.is_pro,
                "config_path": str(self.flomo_config_path),
            }
        except (FileNotFoundError, ValueError) as e:
            return {
                "authenticated": False,
                "error": str(e),
            }
