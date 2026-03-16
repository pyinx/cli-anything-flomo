"""E2E tests for flomo CLI - Tests the installed CLI via subprocess."""

import json
import os
import subprocess
import pytest
from datetime import datetime


class TestCLISubprocess:
    """Test CLI via subprocess to verify installed command works."""

    @staticmethod
    def _resolve_cli(cmd: str) -> str:
        """Resolve CLI command - respects CLI_ANYTHING_FORCE_INSTALLED."""
        if os.environ.get("CLI_ANYTHING_FORCE_INSTALLED"):
            return cmd
        # Fallback to module execution
        return "python3 -m cli_anything.flomo.flomo_cli"

    def test_help(self):
        """Test --help command."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f"{cli} --help",
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        assert "CLI for flomo" in result.stdout

    def test_auth_status(self):
        """Test auth status command."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f"{cli} auth status",
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        # Should show authenticated or not authenticated
        output = result.stdout.lower()
        assert "authenticated" in output or "✓" in result.stdout

    def test_auth_status_json(self):
        """Test auth status command with JSON output."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} --json auth status',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert "authenticated" in data

    def test_memo_list(self):
        """Test memo list command."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} memo list --limit 5',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        # Should show memos or "No memos found"
        assert len(result.stdout) > 0

    def test_memo_list_json(self):
        """Test memo list command with JSON output."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} --json memo list --limit 2',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        # Can be either a list (old format) or object with memos key (new format)
        if isinstance(data, dict):
            assert "memos" in data
            assert isinstance(data["memos"], list)
        else:
            assert isinstance(data, list)

    def test_tag_list(self):
        """Test tag list command."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} tag list',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        # Should show tags or "No tags found"
        assert len(result.stdout) > 0
        # Should show memos scanned count
        assert "scanned" in result.stdout

    def test_tag_list_search(self):
        """Test tag list with search filter."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} tag list --search 关键词',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_tag_list_tree(self):
        """Test tag list with tree view."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} tag list -o tree --limit 50',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_tag_stats(self):
        """Test tag stats command."""
        cli = self._resolve_cli("cli-anything-flomo")
        result = subprocess.run(
            f'{cli} tag stats --limit 5',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0

    def test_export_json(self, tmp_path):
        """Test export json command."""
        cli = self._resolve_cli("cli-anything-flomo")
        output_dir = tmp_path / "exports"
        result = subprocess.run(
            f'{cli} export run -f json -d "{output_dir}" --limit 5',
            capture_output=True,
            text=True,
            shell=True,
        )
        assert result.returncode == 0
        # Check that files were created
        files = list(output_dir.glob("*.json"))
        assert len(files) > 0


class TestCLICRUD:
    """Test CRUD operations with cleanup."""

    @staticmethod
    def _resolve_cli(cmd: str) -> str:
        """Resolve CLI command."""
        if os.environ.get("CLI_ANYTHING_FORCE_INSTALLED"):
            return cmd
        return "python3 -m cli_anything.flomo.flomo_cli"

    @pytest.fixture(autouse=True)
    def cleanup_test_memos(self):
        """Cleanup any test memos created during tests."""
        created_slugs = []
        yield created_slugs

        # Cleanup: delete any created memos
        cli = self._resolve_cli("cli-anything-flomo")
        for slug in created_slugs:
            try:
                subprocess.run(
                    f'{cli} memo delete {slug} --yes',
                    capture_output=True,
                    shell=True,
                    timeout=10,
                )
            except Exception:
                pass  # Ignore cleanup errors

    def test_create_and_delete_memo(self, cleanup_test_memos):
        """Test creating and deleting a memo."""
        cli = self._resolve_cli("cli-anything-flomo")

        # Create memo
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        content = f"CLI test memo {timestamp} #cli_test_automatic"

        result = subprocess.run(
            f'{cli} --json memo create "{content}"',
            capture_output=True,
            text=True,
            shell=True,
        )

        if result.returncode != 0:
            pytest.skip("Memo creation failed - may need auth")

        data = json.loads(result.stdout)
        slug = data.get("slug")

        if slug:
            cleanup_test_memos.append(slug)

            # Verify memo exists
            assert slug is not None

            # Delete memo
            delete_result = subprocess.run(
                f'{cli} memo delete {slug} --yes',
                capture_output=True,
                text=True,
                shell=True,
            )
            assert delete_result.returncode == 0

            # Clear from cleanup since we deleted it
            cleanup_test_memos.clear()

    def test_search_memos(self):
        """Test memo search."""
        cli = self._resolve_cli("cli-anything-flomo")

        result = subprocess.run(
            f'{cli} --json memo filter-content test --limit 5',
            capture_output=True,
            text=True,
            shell=True,
        )

        # Search should return valid JSON (either results or error)
        # The API may return "没有找到 memo" which is valid
        output = result.stdout or result.stderr
        data = json.loads(output)
        # Should be a list (results) or dict with memos key
        assert isinstance(data, (list, dict))


class TestCLIExport:
    """Test export commands."""

    @staticmethod
    def _resolve_cli(cmd: str) -> str:
        """Resolve CLI command."""
        if os.environ.get("CLI_ANYTHING_FORCE_INSTALLED"):
            return cmd
        return "python3 -m cli_anything.flomo.flomo_cli"

    def test_export_markdown(self, tmp_path):
        """Test exporting to Markdown files."""
        cli = self._resolve_cli("cli-anything-flomo")
        output_dir = tmp_path / "exports"

        result = subprocess.run(
            f'{cli} export run -f markdown -d "{output_dir}" --limit 5',
            capture_output=True,
            text=True,
            shell=True,
        )

        assert result.returncode == 0
        assert output_dir.exists()
        # Check that files were created
        files = list(output_dir.glob("*.md"))
        assert len(files) > 0

    def test_export_html(self, tmp_path):
        """Test exporting to HTML files."""
        cli = self._resolve_cli("cli-anything-flomo")
        output_dir = tmp_path / "exports"

        result = subprocess.run(
            f'{cli} export run -f html -d "{output_dir}" --limit 5',
            capture_output=True,
            text=True,
            shell=True,
        )

        assert result.returncode == 0
        assert output_dir.exists()
        # Check that files were created
        files = list(output_dir.glob("*.html"))
        assert len(files) > 0
