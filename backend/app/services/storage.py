"""File storage: local disk (dev) or Supabase Storage (production).

Images are private. The API hands out short-lived HMAC-signed URLs
(/api/files/<key>?exp=..&sig=..) so <img> tags work without exposing other
users' files or the storage service key.
"""
import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from ..config import get_settings

settings = get_settings()


class StorageError(RuntimeError):
    pass


def _sign(key: str, exp: int) -> str:
    msg = f"{key}:{exp}".encode()
    return hmac.new(settings.jwt_secret.encode(), msg, hashlib.sha256).hexdigest()[:32]


def signed_url(key: str | None, ttl: int = 3600) -> str | None:
    if not key:
        return None
    exp = int(time.time()) + ttl
    return f"/api/files/{quote(key)}?exp={exp}&sig={_sign(key, exp)}"


def verify_signature(key: str, exp: int, sig: str) -> bool:
    return exp >= time.time() and hmac.compare_digest(_sign(key, exp), sig)


def ensure_bucket() -> None:
    """Create the private Supabase Storage bucket on startup if it doesn't exist."""
    if settings.storage_backend != "supabase":
        return
    headers = {"Authorization": f"Bearer {settings.supabase_service_key}", "apikey": settings.supabase_service_key}
    base = f"{settings.supabase_url}/storage/v1/bucket"
    r = httpx.get(f"{base}/{settings.supabase_bucket}", headers=headers, timeout=15)
    if r.status_code == 200:
        return
    r = httpx.post(base, headers=headers, timeout=15, json={
        "id": settings.supabase_bucket, "name": settings.supabase_bucket, "public": False,
        "file_size_limit": settings.max_upload_mb * 1024 * 1024 * 2,
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"]})
    if r.status_code >= 300 and "already exists" not in r.text.lower():
        raise StorageError(f"Could not create bucket: {r.status_code} {r.text[:200]}")


def save(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    if settings.storage_backend == "supabase":
        url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_bucket}/{key}"
        r = httpx.post(url, content=data, timeout=30, headers={
            "Authorization": f"Bearer {settings.supabase_service_key}", "apikey": settings.supabase_service_key,
            "Content-Type": content_type, "x-upsert": "true"})
        if r.status_code >= 300:
            raise StorageError(f"Supabase upload failed: {r.status_code} {r.text[:200]}")
        return key
    path = Path(settings.upload_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def load(key: str) -> bytes:
    if settings.storage_backend == "supabase":
        url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_bucket}/{key}"
        r = httpx.get(url, timeout=30, headers={"Authorization": f"Bearer {settings.supabase_service_key}",
                                                         "apikey": settings.supabase_service_key})
        if r.status_code != 200:
            raise StorageError("not found")
        return r.content
    path = (Path(settings.upload_dir) / key).resolve()
    if not str(path).startswith(str(Path(settings.upload_dir).resolve())) or not path.exists():
        raise StorageError("not found")
    return path.read_bytes()
