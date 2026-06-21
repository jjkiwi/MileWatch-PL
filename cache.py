import hashlib
import time
from pathlib import Path

CACHE_DIR = Path("cache")


def _cache_path(url: str) -> Path:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.cache"


def get_cached(url: str, max_age_seconds: int) -> str | None:
    path = _cache_path(url)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > max_age_seconds:
        return None
    return path.read_text(encoding="utf-8")


def save_cache(url: str, content: str) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    _cache_path(url).write_text(content, encoding="utf-8")
