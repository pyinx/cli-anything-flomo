"""Unit tests for flomo CLI core modules."""

import hashlib
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import modules to test
from cli_anything.flomo.utils.config import Config
from cli_anything.flomo.utils.api import FlomoAPI, FlomoAPIError
from cli_anything.flomo.utils.output import (
    format_memo,
    format_memo_brief,
    format_memos_list,
    format_tags,
    format_output,
)
from cli_anything.flomo.core.auth import AuthManager
from cli_anything.flomo.core.memo import MemoManager
from cli_anything.flomo.core.tag import TagManager
from cli_anything.flomo.core.export import ExportManager
from cli_anything.flomo.core.user import UserManager


# ============ Fixtures ============

@pytest.fixture
def sample_memo():
    """Sample memo data."""
    return {
        "slug": "NTQyNTM0Mjk",
        "content": "<p>#test </p><p>Test content</p>",
        "creator_id": 123,
        "source": "web",
        "tags": ["test"],
        "pin": 0,
        "created_at": "2023-01-01 12:00:00",
        "updated_at": "2023-01-01 12:00:00",
        "deleted_at": None,
        "memo_from": "human",
        "linked_count": 0,
        "files": [],
    }


@pytest.fixture
def sample_memos(sample_memo):
    """List of sample memos."""
    return [
        sample_memo,
        {
            "slug": "NTE2NTkyNDA",
            "content": "<p>#work Important note</p>",
            "tags": ["work"],
            "created_at": "2023-01-02 12:00:00",
            "updated_at": "2023-01-02 12:00:00",
        },
    ]


@pytest.fixture
def mock_config():
    """Mock Config with sample data."""
    config = Mock(spec=Config)
    config.access_token = "test_token|123"
    config.api_token = "api_token_123"
    config.user_id = 123
    config.username = "test_user"
    config.user_slug = "MTIz"
    config.is_pro = True
    config.flomo_config_path = Path("/fake/path/config.json")
    # Return proper dict from get_auth_status
    config.get_auth_status.return_value = {
        "authenticated": True,
        "user_id": 123,
        "username": "test_user",
        "is_pro": True,
        "config_path": "/fake/path/config.json",
    }
    return config


# ============ Config Tests ============

class TestConfig:
    """Tests for Config class."""

    @patch("cli_anything.flomo.utils.config.platform.system")
    def test_flomo_config_path_macos(self, mock_system, tmp_path):
        """Test macOS config path detection."""
        mock_system.return_value = "Darwin"

        config = Config()
        # Just check it returns a Path
        assert isinstance(config.flomo_config_path, Path)

    def test_user_info_extraction(self, mock_config):
        """Test user info is extracted correctly."""
        assert mock_config.user_id == 123
        assert mock_config.username == "test_user"
        assert mock_config.is_pro is True


# ============ API Tests ============

class TestFlomoAPI:
    """Tests for FlomoAPI class."""

    def test_init(self):
        """Test API initialization."""
        api = FlomoAPI("test_token")
        assert api.access_token == "test_token"
        assert "Authorization" in api.session.headers

    def test_get_signed_params(self):
        """Test parameter signing."""
        api = FlomoAPI("test_token")
        params = api._get_signed_params()

        # Check required params exist
        assert "timestamp" in params
        assert "sign" in params
        assert "api_key" in params
        assert params["api_key"] == "flomo_web"

        # Verify sign is MD5 hash
        assert len(params["sign"]) == 32

    def test_signature_consistency(self):
        """Test signature generation is consistent."""
        api = FlomoAPI("test_token")

        # Mock timestamp for consistent testing
        with patch("cli_anything.flomo.utils.api.time.time", return_value=1234567890):
            params = api._get_signed_params()

            # Verify signature
            sorted_items = sorted(params.items())
            param_str = "&".join([f"{k}={v}" for k, v in sorted_items if k != "sign"])
            expected_sign = hashlib.md5(
                (param_str + api.SALT).encode("utf-8")
            ).hexdigest()

            assert params["sign"] == expected_sign


# ============ Output Tests ============

class TestOutputFormatting:
    """Tests for output formatting functions."""

    def test_format_memo(self, sample_memo):
        """Test memo formatting."""
        result = format_memo(sample_memo)

        assert "Slug: NTQyNTM0Mjk" in result
        assert "Created: 2023-01-01 12:00:00" in result
        assert "Tags: test" in result

    def test_format_memo_brief(self, sample_memo):
        """Test brief memo formatting."""
        result = format_memo_brief(sample_memo, max_length=80)

        assert "NTQyNTM0Mjk" in result
        assert "2023-01-01" in result

    def test_format_memos_list_empty(self):
        """Test empty memo list."""
        result = format_memos_list([])
        assert "No memos found" in result

    def test_format_memos_list(self, sample_memos):
        """Test memo list formatting."""
        result = format_memos_list(sample_memos, brief=True)

        assert "NTQyNTM0Mjk" in result
        assert "NTE2NTkyNDA" in result

    def test_format_tags(self):
        """Test tag formatting."""
        tags = ["test", "work", "personal"]
        counts = {"test": 5, "work": 3, "personal": 1}

        result = format_tags(tags, counts)

        assert "#test (5)" in result
        assert "#work (3)" in result
        assert "#personal (1)" in result

    def test_format_tags_empty(self):
        """Test empty tag list."""
        result = format_tags([])
        assert "No tags found" in result

    def test_format_output_json(self):
        """Test JSON output formatting."""
        data = {"key": "value"}
        result = format_output(data, is_json=True)

        assert json.loads(result) == data

    def test_format_output_with_formatter(self):
        """Test output formatting with custom formatter."""
        data = ["a", "b", "c"]
        formatter = lambda x: ", ".join(x)
        result = format_output(data, is_json=False, formatter=formatter)

        assert result == "a, b, c"


# ============ Auth Tests ============

class TestAuthManager:
    """Tests for AuthManager class."""

    def test_is_authenticated_true(self, mock_config):
        """Test authentication check when authenticated."""
        auth = AuthManager(config=mock_config)
        assert auth.is_authenticated() is True

    def test_get_status(self, mock_config):
        """Test getting auth status."""
        auth = AuthManager(config=mock_config)
        status = auth.get_status()

        assert status["authenticated"] is True
        assert status["username"] == "test_user"

    @patch("cli_anything.flomo.core.auth.FlomoAPI")
    def test_test_connection_success(self, mock_api_class, mock_config):
        """Test successful connection test."""
        mock_api = Mock()
        mock_api.get_memos.return_value = [{"slug": "test"}]
        mock_api_class.return_value = mock_api

        auth = AuthManager(config=mock_config)
        result = auth.test_connection()

        assert result["success"] is True
        assert result["memo_count"] == 1


# ============ Memo Tests ============

class TestMemoManager:
    """Tests for MemoManager class."""

    def test_extract_tags(self):
        """Test tag extraction from content."""
        content = "<p>#test This is a #work memo #个人</p>"
        tags = MemoManager.extract_tags(content)

        assert "test" in tags
        assert "work" in tags
        assert "个人" in tags

    def test_get_plain_content(self):
        """Test HTML stripping."""
        content = "<p>Hello <b>world</b></p>"
        result = MemoManager.get_plain_content(content)

        assert "<p>" not in result
        assert "<b>" not in result
        assert "Hello world" in result

    def test_list_memos(self, sample_memos):
        """Test listing memos."""
        mock_api = Mock()
        mock_api.get_memos.return_value = sample_memos

        manager = MemoManager(mock_api)
        result = manager.list_memos(limit=10)

        assert len(result) == 2
        mock_api.get_memos.assert_called_once_with(limit=10)


# ============ Tag Tests ============

class TestTagManager:
    """Tests for TagManager class."""

    def test_get_all_tags(self, sample_memos):
        """Test getting all tags."""
        mock_memo_manager = Mock()
        mock_memo_manager.list_memos.return_value = sample_memos

        tag_manager = TagManager(mock_memo_manager)
        tags = tag_manager.get_all_tags()

        assert "test" in tags
        assert "work" in tags

    def test_get_tag_stats(self, sample_memos):
        """Test getting tag statistics."""
        mock_memo_manager = Mock()
        mock_memo_manager.list_memos.return_value = sample_memos

        tag_manager = TagManager(mock_memo_manager)
        stats = tag_manager.get_tag_stats()

        assert stats["test"] == 1
        assert stats["work"] == 1

    def test_get_top_tags(self, sample_memos):
        """Test getting top tags."""
        mock_memo_manager = Mock()
        mock_memo_manager.list_memos.return_value = sample_memos

        tag_manager = TagManager(mock_memo_manager)
        top = tag_manager.get_top_tags(n=5)

        assert len(top) <= 5
        # Check sorted by count descending
        if len(top) > 1:
            assert top[0][1] >= top[1][1]


# ============ Export Tests ============

class TestExportManager:
    """Tests for ExportManager class."""

    def test_to_json(self, sample_memos):
        """Test JSON export."""
        exporter = ExportManager(sample_memos)
        result = exporter.to_json()

        # Should be valid JSON
        data = json.loads(result)
        assert len(data) == 2

    def test_to_markdown(self, sample_memos):
        """Test Markdown export."""
        exporter = ExportManager(sample_memos)
        result = exporter.to_markdown()

        assert "# flomo Export" in result
        assert "Exported:" in result
        assert "---" in result

    def test_to_html(self, sample_memos):
        """Test HTML export."""
        exporter = ExportManager(sample_memos)
        result = exporter.to_html()

        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "</html>" in result

    def test_to_csv(self, sample_memos):
        """Test CSV export."""
        exporter = ExportManager(sample_memos)
        result = exporter.to_csv()

        assert "slug,created_at" in result
        assert "NTQyNTM0Mjk" in result


# ============ User Manager Tests ============

class TestUserManager:
    """Tests for UserManager class."""

    def test_get_profile(self):
        """Test getting user profile."""
        mock_api = Mock()
        mock_api.get_user_info.return_value = {
            "id": 123,
            "name": "test_user",
            "email": "test@example.com",
            "pro_type": "pro",
        }

        manager = UserManager(mock_api)
        profile = manager.get_profile()

        assert profile["id"] == 123
        assert profile["name"] == "test_user"

    def test_is_pro_true(self):
        """Test pro check when user is pro."""
        mock_api = Mock()
        mock_api.get_user_info.return_value = {"pro_type": "pro"}

        manager = UserManager(mock_api)
        assert manager.is_pro() is True

    def test_is_pro_false(self):
        """Test pro check when user is not pro."""
        mock_api = Mock()
        mock_api.get_user_info.return_value = {"pro_type": "free"}

        manager = UserManager(mock_api)
        assert manager.is_pro() is False

    def test_get_stats_summary(self):
        """Test getting stats summary."""
        mock_api = Mock()
        mock_api.get_user_info.return_value = {
            "id": 123,
            "name": "test_user",
            "email": "test@example.com",
            "pro_type": "pro",
            "pro_expired_at": "2025-12-31",
            "language": "zh",
            "created_at": "2023-01-01",
            "access": ["feature1"],
        }

        manager = UserManager(mock_api)
        summary = manager.get_stats_summary()

        assert summary["user_id"] == 123
        assert summary["is_pro"] is True
        assert summary["language"] == "zh"


# ============ Extended Memo Manager Tests ============

class TestMemoManagerExtended:
    """Tests for extended MemoManager methods."""

    def test_get_pinned_memos(self):
        """Test getting pinned memos."""
        mock_api = Mock()
        mock_api.get_pinned_memos.return_value = [{"slug": "pinned1"}]

        manager = MemoManager(mock_api)
        result = manager.get_pinned_memos()

        assert len(result) == 1
        assert result[0]["slug"] == "pinned1"

    def test_get_archived_memos(self):
        """Test getting archived memos."""
        mock_api = Mock()
        mock_api.get_archived_memos.return_value = [{"slug": "archived1"}]

        manager = MemoManager(mock_api)
        result = manager.get_archived_memos(limit=100)

        assert len(result) == 1
        mock_api.get_archived_memos.assert_called_once_with(limit=100)

    def test_pin_memo(self):
        """Test pinning a memo."""
        mock_api = Mock()
        mock_api.pin_memo.return_value = {"slug": "test", "pin": 1}

        manager = MemoManager(mock_api)
        result = manager.pin_memo("test")

        assert result["pin"] == 1
        mock_api.pin_memo.assert_called_once_with("test")

    def test_unpin_memo(self):
        """Test unpinning a memo."""
        mock_api = Mock()
        mock_api.unpin_memo.return_value = {"slug": "test", "pin": 0}

        manager = MemoManager(mock_api)
        result = manager.unpin_memo("test")

        assert result["pin"] == 0

    def test_archive_memo(self):
        """Test archiving a memo."""
        mock_api = Mock()
        mock_api.archive_memo.return_value = {"slug": "test", "archived": True}

        manager = MemoManager(mock_api)
        result = manager.archive_memo("test")

        assert result["archived"] is True

    def test_unarchive_memo(self):
        """Test unarchiving a memo."""
        mock_api = Mock()
        mock_api.unarchive_memo.return_value = {"slug": "test", "archived": False}

        manager = MemoManager(mock_api)
        result = manager.unarchive_memo("test")

        assert result["archived"] is False

    def test_restore_memo(self):
        """Test restoring a memo from trash."""
        mock_api = Mock()
        mock_api.restore_memo.return_value = {"slug": "test", "deleted_at": None}

        manager = MemoManager(mock_api)
        result = manager.restore_memo("test")

        mock_api.restore_memo.assert_called_once_with("test")

    def test_get_memos_by_date(self):
        """Test getting memos by date range."""
        mock_api = Mock()
        mock_api.get_memos_by_date.return_value = [{"slug": "date1"}]

        manager = MemoManager(mock_api)
        result = manager.get_memos_by_date("2023-01-01", "2023-01-31", limit=100)

        assert len(result) == 1
        mock_api.get_memos_by_date.assert_called_once_with("2023-01-01", "2023-01-31", limit=100)


class TestMemoManagerQualityOfLife:
    """Tests for quality-of-life MemoManager methods."""

    def test_get_today_memos(self):
        """Test getting today's memos."""
        mock_api = Mock()
        mock_api.get_memos_by_date.return_value = [
            {"slug": "today1", "content": "test"}
        ]

        manager = MemoManager(mock_api)
        result = manager.get_today_memos(limit=50)

        assert len(result) == 1
        # Verify it was called with today's date
        call_args = mock_api.get_memos_by_date.call_args
        assert call_args[0][0] == call_args[0][1]  # start_date == end_date
        assert call_args[1]["limit"] == 50

    def test_get_recent_memos(self):
        """Test getting recent memos."""
        mock_api = Mock()
        mock_api.get_memos_by_date.return_value = [
            {"slug": "recent1", "content": "test"}
        ]

        manager = MemoManager(mock_api)
        result = manager.get_recent_memos(days=7, limit=100)

        assert len(result) == 1
        mock_api.get_memos_by_date.assert_called_once()
        call_args = mock_api.get_memos_by_date.call_args
        assert call_args[1]["limit"] == 100

    def test_get_random_memo(self):
        """Test getting a random memo."""
        mock_api = Mock()
        mock_api.get_memos.return_value = [
            {"slug": "memo1", "content": "test1"},
            {"slug": "memo2", "content": "test2"},
            {"slug": "memo3", "content": "test3"},
        ]

        manager = MemoManager(mock_api)
        result = manager.get_random_memo(limit=50)

        assert result is not None
        assert result["slug"] in ["memo1", "memo2", "memo3"]
        mock_api.get_memos.assert_called_once_with(limit=50)

    def test_get_random_memo_empty(self):
        """Test getting a random memo when no memos exist."""
        mock_api = Mock()
        mock_api.get_memos.return_value = []

        manager = MemoManager(mock_api)
        result = manager.get_random_memo()

        assert result is None

    def test_filter_by_tag(self):
        """Test filtering memos by tag."""
        mock_api = Mock()
        mock_api.get_memos.return_value = [
            {"slug": "memo1", "tags": ["work", "important"]},
            {"slug": "memo2", "tags": ["personal"]},
            {"slug": "memo3", "tags": ["WORK", "urgent"]},  # Test case insensitivity
        ]

        manager = MemoManager(mock_api)
        result = manager.filter_by_tag("work")

        assert len(result) == 2
        slugs = [m["slug"] for m in result]
        assert "memo1" in slugs
        assert "memo3" in slugs
        assert "memo2" not in slugs

    def test_filter_by_tag_with_hash(self):
        """Test filtering by tag with # prefix."""
        mock_api = Mock()
        mock_api.get_memos.return_value = [
            {"slug": "memo1", "tags": ["work"]},
        ]

        manager = MemoManager(mock_api)
        result = manager.filter_by_tag("#work")

        assert len(result) == 1

    def test_filter_by_content(self):
        """Test filtering memos by content keyword."""
        mock_api = Mock()
        mock_api.get_memos.return_value = [
            {"slug": "memo1", "content": "This is a TEST memo"},
            {"slug": "memo2", "content": "Another memo"},
            {"slug": "memo3", "content": "test again"},
        ]

        manager = MemoManager(mock_api)
        result = manager.filter_by_content("test")

        assert len(result) == 2
        slugs = [m["slug"] for m in result]
        assert "memo1" in slugs
        assert "memo3" in slugs
        assert "memo2" not in slugs

    def test_get_stats(self):
        """Test getting memo statistics."""
        mock_api = Mock()
        mock_api.get_memos.return_value = [
            {
                "slug": "memo1",
                "content": "Test content",
                "tags": ["work"],
                "created_at": "2023-01-15 10:00:00",
            },
            {
                "slug": "memo2",
                "content": "Another test",
                "tags": ["work", "personal"],
                "created_at": "2023-01-15 14:00:00",
            },
            {
                "slug": "memo3",
                "content": "Third one",
                "tags": ["personal"],
                "created_at": "2023-01-20 09:00:00",
            },
        ]

        manager = MemoManager(mock_api)
        stats = manager.get_stats(limit=100)

        assert stats["total"] == 3
        assert stats["unique_tags"] == 2
        assert stats["most_productive_day"] == "2023-01-15"
        assert stats["most_productive_day_count"] == 2
        assert stats["oldest_memo"] == "2023-01-15 10:00:00"
        assert stats["newest_memo"] == "2023-01-20 09:00:00"
        assert len(stats["top_tags"]) <= 5

    def test_get_stats_empty(self):
        """Test getting stats when no memos exist."""
        mock_api = Mock()
        mock_api.get_memos.return_value = []

        manager = MemoManager(mock_api)
        stats = manager.get_stats()

        assert stats["total"] == 0
