"""Object storage for photo bytes.

Two backends behind one tiny surface: S3 (the real path, configurable so MinIO /
Garage / SeaweedFS / R2 are all just env vars) and a local directory, which is
what the test suite uses so it never needs a running object store and never
leaves objects behind.

Deliberately not a service layer: it only moves bytes. Every rule (size, type,
resize, dedupe, ownership) lives in ``app.services.photos``.
"""

from __future__ import annotations

import os
from pathlib import Path

_CONTENT_TYPES = {".jpg": "image/jpeg"}


class LocalStorage:
    """Filesystem backend. Keys are relative paths; the root is created lazily."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        # Refuse anything that could escape the root: keys come from hashes, but
        # the check is cheap and this is the only place file paths are built.
        target = (self.root / key).resolve()
        if not str(target).startswith(str(self.root.resolve())):
            raise ValueError("非法的对象键")
        return target

    def put(self, key: str, data: bytes) -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    """S3-compatible backend. Path-style addressing works on every self-hosted
    implementation; virtual-host style does not."""

    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = os.getenv("S3_BUCKET", "model-archive-photos")
        self._client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY") or None,
            aws_secret_access_key=os.getenv("S3_SECRET_KEY") or None,
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )
        self._ready = False

    def _ensure_bucket(self) -> None:
        if self._ready:
            return
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)
        self._ready = True

    def put(self, key: str, data: bytes) -> None:
        self._ensure_bucket()
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=_CONTENT_TYPES.get(Path(key).suffix, "application/octet-stream"),
            CacheControl="public, max-age=604800, immutable",
        )

    def get(self, key: str) -> bytes:
        self._ensure_bucket()
        return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self._ensure_bucket()
        self._client.delete_object(Bucket=self.bucket, Key=key)


_storage: LocalStorage | S3Storage | None = None


def get_storage() -> LocalStorage | S3Storage:
    global _storage
    if _storage is None:
        backend = os.getenv("PHOTO_STORAGE", "s3").lower()
        if backend == "fs":
            _storage = LocalStorage(os.getenv("PHOTO_LOCAL_ROOT", ".tmp/photos"))
        elif backend == "s3":
            _storage = S3Storage()
        else:
            raise RuntimeError(f"PHOTO_STORAGE 必须是 s3 或 fs，当前是 {backend}")
    return _storage
