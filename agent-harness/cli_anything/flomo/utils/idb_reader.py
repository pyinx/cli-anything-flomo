"""IndexedDB reader for flomo local data.

This module reads memo data directly from flomo's local IndexedDB storage,
bypassing the 500-memo API limit.

The flomo desktop app stores data in IndexedDB format backed by LevelDB:
- macOS: ~/Library/Containers/com.flomoapp.m/Data/Library/Application Support/flomo/IndexedDB/

We use dfindexeddb (Google's forensic tool) to parse the IndexedDB files,
which handles the custom comparator (idb_cmp1) and Snappy compression.

Flomo IndexedDB Object Stores:
- Object Store 1: Main memo storage (contains all memos with full metadata)
- Object Store 2: Tag usage statistics
- Object Store 4: File attachments
- Object Store 8: Mon lists (pinned/archived collections)
- Object Store 10: Memo sync cache (subset of memos for quick sync)
- Object Store 12: Tag definitions
"""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


IDB_PATH_MACOS = Path("~/Library/Containers/com.flomoapp.m/Data/Library/Application Support/flomo/IndexedDB/flomo_._0.indexeddb.leveldb").expanduser()

# Object store IDs in flomo's IndexedDB
# Object Store 1 contains the full memo data with all metadata
OBJECT_STORE_MEMOS_MAIN = 1   # Main memo storage (all memos)
OBJECT_STORE_MEMOS_SYNC = 10  # Sync cache (subset for quick sync)
OBJECT_STORE_TAGS = 2         # Tag statistics
OBJECT_STORE_FILES = 4        # File attachments
OBJECT_STORE_MON_LISTS = 8    # Mon lists (pinned/archived)


class IndexedDBReader:
    """Reads memo data from flomo's local IndexedDB using dfindexeddb."""

    def __init__(self, idb_path: Optional[Path] = None):
        """Initialize the IndexedDB reader.

        Args:
            idb_path: Path to the IndexedDB directory. Defaults to macOS path.
        """
        self.idb_path = idb_path or IDB_PATH_MACOS
        self._cache: Optional[List[Dict]] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 60.0  # Cache for 60 seconds

        # Store slug versions for deduplication
        self._slug_versions: Dict[str, List[Dict[str, Any]]] = {}

    def is_available(self) -> bool:
        """Check if IndexedDB is available for reading.

        Returns:
            True if the IndexedDB directory exists and is readable.
        """
        return self.idb_path.exists() and self.idb_path.is_dir()

    def _check_dfindexeddb(self) -> bool:
        """Check if dfindexeddb is installed.

        Returns:
            True if dfindexeddb is available.
        """
        return shutil.which('dfindexeddb') is not None

    def has_useful_data(self, min_memos: int = 10) -> bool:
        """Check if IndexedDB has useful memo data.

        Args:
            min_memos: Minimum number of useful memos required.

        Returns:
            True if there are enough memos with actual content.
        """
        try:
            memos = self.get_memos()
            # Filter out empty memos
            useful_memos = [
                m for m in memos
                if m.get('content') and m['content'].strip() not in ('<p></p>', '<p> </p>')
            ]
            return len(useful_memos) >= min_memos
        except Exception:
            return False

    def get_memos(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all memos from IndexedDB.

        Args:
            use_cache: Whether to use cached data if available.

        Returns:
            List of memo dictionaries.
        """
        # Check cache
        if use_cache and self._cache is not None:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._cache

        # Read from IndexedDB
        memos = self._read_from_idb()

        # Update cache
        self._cache = memos
        self._cache_time = time.time()

        return memos

    def _is_deleted(self, deleted_at: Any) -> bool:
        """Check if a memo is deleted based on deleted_at field.

        In Object Store 1, deleted_at can be:
        - None or missing: not deleted
        - {'__type__': 'Null'}: not deleted
        - String timestamp like '2025-07-20 22:55:16': DELETED
        - Numeric timestamp: DELETED

        Args:
            deleted_at: The deleted_at field value.

        Returns:
            True if the memo is deleted.
        """
        if deleted_at is None:
            return False
        if isinstance(deleted_at, dict):
            # Check if it's a Null type
            if deleted_at.get('__type__') == 'Null':
                return False
            # Other dict types with value mean deleted
            return deleted_at.get('value') is not None
        # String timestamps or numeric values mean deleted
        if isinstance(deleted_at, (str, int, float)):
            # Empty string is not deleted
            if isinstance(deleted_at, str) and not deleted_at.strip():
                return False
            return True
        return False

    def _extract_files_from_jsarray(self, files_field: Any) -> List[Dict[str, Any]]:
        """Extract file information from JSArray structure.

        Object Store 1 files field has format:
        {'__type__': 'JSArray', 'values': [{...}, {...}], 'properties': {}}

        Each file in values has:
        - id: file ID
        - type: 'image', etc.
        - name: filename
        - path: file path
        - url: full URL
        - thumbnail_url: thumbnail URL

        Args:
            files_field: The files field from Object Store 1.

        Returns:
            List of file info dicts with id, type, url, etc.
        """
        if not isinstance(files_field, dict):
            return []

        if files_field.get('__type__') != 'JSArray':
            return []

        # Files are in the 'values' array
        values = files_field.get('values', [])
        if not values:
            return []

        files = []
        for file_info in values:
            if isinstance(file_info, dict):
                files.append(file_info)

        return files

    def _extract_tags_from_jsarray(self, tags_field: Any) -> List[str]:
        """Extract tags from JSArray structure.

        Object Store 1 tags field has format:
        {'__type__': 'JSArray', 'values': [...], 'properties': {'0': 'tag1', '1': 'tag2', ...}}

        Args:
            tags_field: The tags field from Object Store 1.

        Returns:
            List of tag strings.
        """
        if not isinstance(tags_field, dict):
            return []

        if tags_field.get('__type__') != 'JSArray':
            return []

        properties = tags_field.get('properties', {})
        if not properties:
            return []

        tags = []
        # Properties are indexed as strings '0', '1', '2', etc.
        i = 0
        while str(i) in properties:
            tag = properties[str(i)]
            if isinstance(tag, str) and tag:
                # Strip # prefix if present (flomo may store tags with # prefix)
                if tag.startswith('#'):
                    tag = tag[1:]
                if tag:  # Only add non-empty tags after stripping
                    tags.append(tag)
            i += 1

        return tags

    def _read_from_idb(self) -> List[Dict[str, Any]]:
        """Read memos from IndexedDB using dfindexeddb.

        Reads from Object Store 1 (main storage) which contains all memos
        with full metadata including deleted_at for filtering.

        Returns:
            List of memo dictionaries (excludes deleted memos).
        """
        if not self._check_dfindexeddb():
            raise RuntimeError(
                "dfindexeddb is not installed. Install it with: pip install dfindexeddb"
            )

        # Clear previous slug versions
        self._slug_versions = {}

        # Run dfindexeddb to parse the IndexedDB
        result = subprocess.run(
            [
                'dfindexeddb', 'db',
                '-s', str(self.idb_path),
                '--format', 'chrome',
                '-o', 'jsonl'
            ],
            capture_output=True,
            text=True,
            timeout=300  # Increased timeout for larger dataset
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to read IndexedDB: {result.stderr}")

        # Parse the JSONL output
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Only process Object Store 1 (main memo storage with full metadata)
            if obj.get('object_store_id') != OBJECT_STORE_MEMOS_MAIN:
                continue

            # Extract memo data from nested value structure
            val = obj.get('value')
            if not isinstance(val, dict):
                continue

            inner_val = val.get('value')
            if not isinstance(inner_val, dict):
                continue

            slug = inner_val.get('slug')
            content = inner_val.get('content', '')

            if not slug:
                continue

            # Skip deleted memos - check deleted_at field
            deleted_at = inner_val.get('deleted_at')
            if self._is_deleted(deleted_at):
                continue

            # Skip empty content
            if not content or content.strip() in ('<p></p>', '<p> </p>'):
                continue

            # Get timestamp - created_at_long is in SECONDS (not milliseconds)
            timestamp = inner_val.get('created_at_long')
            if timestamp:
                # Convert seconds to milliseconds for consistency
                timestamp = timestamp * 1000
            else:
                timestamp = inner_val.get('timestamp', 0)

            # Get tags from Object Store 1 tags field (JSArray structure)
            tags_field = inner_val.get('tags')
            if tags_field:
                tags = self._extract_tags_from_jsarray(tags_field)
            else:
                tags = self._extract_tags_from_content(content)

            # Collect all versions for each slug
            if slug not in self._slug_versions:
                self._slug_versions[slug] = []

            # Extract files from JSArray structure
            files_field = inner_val.get('files')
            if files_field:
                files = self._extract_files_from_jsarray(files_field)
            else:
                files = []

            self._slug_versions[slug].append({
                'timestamp': timestamp,
                'content': content,
                'created_at': None,
                'decoded_slug': None,
                'tags': tags,
                'pin': inner_val.get('pin', False),
                'files': files,
            })

            # Decode slug from base64
            try:
                decoded_slug = base64.b64decode(slug).decode('utf-8')
                self._slug_versions[slug][-1]['decoded_slug'] = decoded_slug
            except Exception:
                pass

            # Convert timestamp to datetime
            if timestamp:
                try:
                    dt = datetime.fromtimestamp(timestamp / 1000)
                    self._slug_versions[slug][-1]['created_at'] = dt.isoformat()
                except Exception:
                    pass

        # After collecting all versions, keep the latest one for each slug
        memos = []
        for slug, versions in sorted(self._slug_versions.items()):
            # Sort by timestamp descending (newest first)
            versions_sorted = sorted(versions, key=lambda x: -x['timestamp'])
            latest = versions_sorted[0]  # Take the newest version
            memos.append({
                'slug': slug,
                'decoded_slug': latest['decoded_slug'],
                'content': latest['content'],
                'created_at': latest['created_at'],
                'timestamp': latest['timestamp'],
                'tags': latest['tags'],
                'source': 'local',
                'pin': latest.get('pin', False),
                'files': latest.get('files', []),
            })

        return memos

    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extract hashtags from memo content.

        Args:
            content: HTML content of the memo.

        Returns:
            List of tag strings (without # prefix).
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)
        # Find hashtags - match #tag and #tag/subtag patterns
        # The regex captures the tag WITHOUT the # prefix
        tag_matches = re.findall(r'#([^\s#<>"\']+(?:/[^\s#<>"\']+)*)', text)
        return list(set(tag_matches))
    def get_tags(self) -> Dict[str, int]:
        """Get all tags and their usage counts from IndexedDB.

        Returns:
            Dictionary mapping tag names to usage counts.
        """
        memos = self.get_memos()
        tag_counter = Counter()
        for memo in memos:
            # Get tags extracted from content
            tags = memo.get('tags', [])
            for tag in tags:
                tag_counter[tag] += 1
        return dict(tag_counter)
    def search_memos(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search memos by content.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of matching memos.
        """
        memos = self.get_memos()
        query_lower = query.lower()
        results = []
        for memo in memos:
            content = memo.get('content', '').lower()
            if query_lower in content:
                results.append(memo)
                if len(results) >= limit:
                    break
        return results
    def get_memo_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get a specific memo by slug.

        Args:
            slug: Memo slug identifier.

        Returns:
            Memo dictionary or None if not found.
        """
        memos = self.get_memos()
        for memo in memos:
            if memo.get('slug') == slug or memo.get('decoded_slug') == slug:
                return memo
        return None
    def clear_cache(self) -> None:
        """Clear the memo cache."""
        self._cache = None
        self._cache_time = 0


# Singleton instance
_reader: Optional[IndexedDBReader] = None


def get_idb_reader() -> IndexedDBReader:
    """Get the singleton IndexedDB reader instance.

    Returns:
        IndexedDBReader instance.
    """
    global _reader
    if _reader is None:
        _reader = IndexedDBReader()
    return _reader
