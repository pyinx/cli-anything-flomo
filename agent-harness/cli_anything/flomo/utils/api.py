"""API client for flomo with request signing."""

import hashlib
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests


class FlomoAPI:
    """Client for flomo API with proper request signing."""

    BASE_URL = "https://flomoapp.com/api/v1"
    SALT = "dbbc3dd73364b4084c3a69346e0ce2b2"

    def __init__(self, access_token: str):
        """Initialize API client.

        Args:
            access_token: Bearer token from flomo config
        """
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })

    def _get_signed_params(self, extra_params: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Generate signed parameters for API request.

        Args:
            extra_params: Additional parameters to include
            json_data: JSON body data (for PUT/POST requests, included in signature)

        Returns:
            Dict with all required params including signature
        """
        params = {
            "limit": "200",
            "tz": "8:0",
            "timestamp": str(int(time.time())),
            "api_key": "flomo_web",
            "app_version": "5.25.64",
            "platform": "mac",
            "webp": "1",
        }

        if extra_params:
            params.update(extra_params)

        # Sort parameters and create signature string
        sorted_items = sorted(params.items())
        param_str = "&".join([f"{k}={v}" for k, v in sorted_items])

        # For PUT/POST requests, include JSON body in signature
        if json_data:
            # Convert JSON values to strings and add to signature
            for k, v in sorted(json_data.items()):
                if isinstance(v, bool):
                    param_str += f"&{k}={str(v).lower()}"
                elif v is not None:
                    param_str += f"&{k}={v}"

        # Generate MD5 signature
        sign = hashlib.md5((param_str + self.SALT).encode("utf-8")).hexdigest()
        params["sign"] = sign

        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters (will be signed)
            json_data: JSON body for POST/PUT

        Returns:
            API response as dict

        Raises:
            FlomoAPIError: On API errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        signed_params = self._get_signed_params(params, json_data)

        response = self.session.request(
            method=method,
            url=url,
            params=signed_params,
            json=json_data,
        )

        try:
            data = response.json()
        except ValueError:
            raise FlomoAPIError(f"Invalid JSON response: {response.text}")

        if response.status_code >= 400:
            raise FlomoAPIError(
                data.get("message", f"HTTP {response.status_code}"),
                code=response.status_code,
            )

        if data.get("code", 0) != 0:
            raise FlomoAPIError(
                data.get("message", "Unknown error"),
                code=data.get("code"),
            )

        return data

    def get_memos(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get updated memos.

        Args:
            limit: Maximum number of memos to return

        Returns:
            List of memo objects
        """
        data = self._request("GET", "/memo/updated/", params={"limit": str(limit)})
        return data.get("data", [])

    def get_memo(self, slug: str) -> Dict[str, Any]:
        """Get a specific memo by slug.

        Args:
            slug: Memo slug identifier

        Returns:
            Memo object
        """
        data = self._request("GET", f"/memo/{slug}/")
        return data.get("data", {})

    def create_memo(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        parent_slug: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new memo.

        Args:
            content: Memo content (HTML supported)
            tags: List of tags
            parent_slug: Parent memo slug for replies
            files: List of file URLs

        Returns:
            Created memo object
        """
        import time

        # Convert tags to flomo format if provided
        if tags:
            tag_str = " ".join([f"#{tag}" for tag in tags])
            content = f"{tag_str} {content}"

        # flomo uses PUT /memo to create new memos
        json_data = {
            "content": content,
            "created_at": int(time.time()),
            "source": "api",
            "parent_memo_slug": parent_slug,
            "files": files or [],
        }

        data = self._request("PUT", "/memo", json_data=json_data)
        return data.get("data", {})

    def update_memo(
        self,
        slug: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update an existing memo.

        Args:
            slug: Memo slug identifier
            content: New content
            tags: New tags

        Returns:
            Updated memo object
        """
        json_data = {}
        if content is not None:
            # Convert tags to flomo format if provided
            if tags:
                tag_str = " ".join([f"#{tag}" for tag in tags])
                content = f"{tag_str} {content}"
            json_data["content"] = content
        elif tags is not None:
            json_data["tags"] = tags

        data = self._request("PUT", f"/memo/{slug}/", json_data=json_data)
        return data.get("data", {})

    def delete_memo(self, slug: str) -> bool:
        """Delete a memo.

        Args:
            slug: Memo slug identifier

        Returns:
            True if successful
        """
        self._request("DELETE", f"/memo/{slug}/")
        return True

    def search_memos(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search memos.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memos
        """
        data = self._request("GET", "/memo/search/", params={"q": query, "limit": str(limit)})
        return data.get("data", [])

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information.

        Returns:
            User info dict with id, name, email, pro status, etc.
        """
        data = self._request("GET", "/user/me/")
        return data.get("data", {})

    def get_pinned_memos(self) -> List[Dict[str, Any]]:
        """Get pinned (置顶) memos.

        Returns:
            List of pinned memo objects
        """
        data = self._request("GET", "/memo/pinned/")
        return data.get("data", [])

    def get_archived_memos(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get archived memos.

        Args:
            limit: Maximum number of memos

        Returns:
            List of archived memo objects
        """
        data = self._request("GET", "/memo/archived/", params={"limit": str(limit)})
        return data.get("data", [])

    def get_trash_memos(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get trashed (deleted) memos.

        Args:
            limit: Maximum number of memos

        Returns:
            List of trashed memo objects
        """
        data = self._request("GET", "/memo/deleted", params={"limit": str(limit)})
        return data.get("data", [])

    def pin_memo(self, slug: str) -> Dict[str, Any]:
        """Pin a memo.

        Args:
            slug: Memo slug identifier

        Returns:
            Updated memo object
        """
        data = self._request("PUT", f"/memo/{slug}/", json_data={"pin": 1})
        return data.get("data", {})

    def unpin_memo(self, slug: str) -> Dict[str, Any]:
        """Unpin a memo.

        Args:
            slug: Memo slug identifier

        Returns:
            Updated memo object
        """
        data = self._request("PUT", f"/memo/{slug}/", json_data={"pin": 0})
        return data.get("data", {})

    def archive_memo(self, slug: str) -> Dict[str, Any]:
        """Archive a memo.

        Args:
            slug: Memo slug identifier

        Returns:
            Updated memo object
        """
        data = self._request("PUT", f"/memo/{slug}/", json_data={"archived": True})
        return data.get("data", {})

    def unarchive_memo(self, slug: str) -> Dict[str, Any]:
        """Unarchive a memo.

        Args:
            slug: Memo slug identifier

        Returns:
            Updated memo object
        """
        data = self._request("PUT", f"/memo/{slug}/", json_data={"archived": False})
        return data.get("data", {})

    def restore_memo(self, slug: str) -> Dict[str, Any]:
        """Restore a memo from trash.

        Args:
            slug: Memo slug identifier

        Returns:
            Restored memo object
        """
        data = self._request("PUT", f"/memo/{slug}/restore/")
        return data.get("data", {})

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
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": str(limit),
        }
        data = self._request("GET", "/memo/updated/", params=params)
        return data.get("data", [])

    def get_memos_incremental(
        self,
        latest_updated_at: int = 0,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get memos using incremental sync (like flomo desktop app).

        This method mimics the flomo desktop app's sync mechanism,
        using pagination based on updated_at timestamp.

        Args:
            latest_updated_at: Last sync timestamp (Unix seconds, 0 for full sync)
            limit: Maximum memos per request (server limits to 500)

        Returns:
            List of memo objects
        """
        params = {
            "limit": str(limit),
            "latest_updated_at": str(latest_updated_at),
        }
        data = self._request("GET", "/memo/updated/", params=params)
        return data.get("data", [])

    def get_all_memos(self, max_memos: int = 10000) -> List[Dict[str, Any]]:
        """Get ALL memos by paginating through the API.

        This bypasses the 500-memo limit by using incremental sync.
        Uses Unix timestamps (seconds) for pagination, matching flomo desktop.

        Args:
            max_memos: Maximum total memos to fetch (safety limit)

        Returns:
            List of all memo objects
        """
        all_memos = []
        latest_updated_at = 0  # Unix timestamp in seconds
        seen_slugs = set()
        batch_count = 0
        consecutive_empty_batches = 0
        max_consecutive_empty = 3  # Stop after 3 consecutive batches with no new memos

        while len(all_memos) < max_memos:
            batch_count += 1
            batch = self.get_memos_incremental(
                latest_updated_at=latest_updated_at,
                limit=500
            )

            # No memos returned - we've reached the end
            if not batch:
                print(f"  Batch {batch_count}: No memos returned, pagination complete")
                break

            # Track previous count to detect progress
            prev_count = len(all_memos)

            # Deduplicate by slug
            for memo in batch:
                slug = memo.get("slug", "")
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    all_memos.append(memo)

            new_count = len(all_memos) - prev_count
            print(f"  Batch {batch_count}: {len(batch)} memos fetched, {new_count} new (total: {len(all_memos)})")

            # Progress tracking: detect when no new memos are returned
            if new_count == 0:
                consecutive_empty_batches += 1
                print(f"  Warning: No new memos in this batch ({consecutive_empty_batches}/{max_consecutive_empty})")
                if consecutive_empty_batches >= max_consecutive_empty:
                    print(f"  Stopping: {max_consecutive_empty} consecutive batches with no new memos")
                    break
            else:
                consecutive_empty_batches = 0

            # Update pagination cursor from the memo with highest updated_at
            # Find the maximum updated_at in the current batch to advance the cursor
            max_updated_at_in_batch = 0
            for memo in batch:
                updated_at_str = memo.get("updated_at", "")
                if updated_at_str:
                    try:
                        dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        memo_updated_at = int(dt.timestamp())
                        if memo_updated_at > max_updated_at_in_batch:
                            max_updated_at_in_batch = memo_updated_at
                    except (ValueError, TypeError):
                        continue

            # Advance the cursor only if we found a valid timestamp
            if max_updated_at_in_batch > latest_updated_at:
                latest_updated_at = max_updated_at_in_batch
            else:
                # If cursor didn't advance but we got memos, increment by 1 second
                # to avoid fetching the same batch repeatedly
                latest_updated_at += 1

            # If we got less than 500, we've likely reached the end
            if len(batch) < 500:
                print(f"  Pagination complete: received partial batch ({len(batch)} < 500)")
                break

        return all_memos[:max_memos]


class FlomoAPIError(Exception):
    """Exception for flomo API errors."""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.message = message
