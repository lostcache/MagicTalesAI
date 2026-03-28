"""Content-hash based filesystem cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class Cache:
    """Simple filesystem cache keyed by content hash."""

    def __init__(self, cache_dir: Path, enabled: bool = True) -> None:
        self._dir = cache_dir
        self._enabled = enabled
        if enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get_json(self, key: str) -> dict | list | None:
        """Retrieve cached JSON data, or None if not cached."""
        if not self._enabled:
            return None
        path = self._dir / f"{self._hash(key)}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def put_json(self, key: str, data: dict | list) -> None:
        """Store JSON data in cache."""
        if not self._enabled:
            return
        path = self._dir / f"{self._hash(key)}.json"
        path.write_text(json.dumps(data, indent=2))

    def get_bytes(self, key: str) -> bytes | None:
        """Retrieve cached binary data."""
        if not self._enabled:
            return None
        path = self._dir / f"{self._hash(key)}.bin"
        if path.exists():
            return path.read_bytes()
        return None

    def put_bytes(self, key: str, data: bytes) -> None:
        """Store binary data in cache."""
        if not self._enabled:
            return
        path = self._dir / f"{self._hash(key)}.bin"
        path.write_bytes(data)

    def clear(self) -> int:
        """Remove all cached files. Returns count of files removed."""
        if not self._dir.exists():
            return 0
        count = 0
        for f in self._dir.iterdir():
            if f.is_file():
                f.unlink()
                count += 1
        return count
