"""Supabase Storage helpers for private X-ray image objects."""

from __future__ import annotations

import logging
from functools import lru_cache
from uuid import UUID, uuid4

from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base error for storage operations."""


class StorageConfigurationError(StorageError):
    """Raised when Supabase storage settings are missing or invalid."""


class StorageUploadError(StorageError):
    """Raised when an upload to Supabase Storage fails."""


class StorageDeleteError(StorageError):
    """Raised when a delete from Supabase Storage fails."""


class StorageSignedUrlError(StorageError):
    """Raised when creating a signed URL fails."""


class StorageDownloadError(StorageError):
    """Raised when downloading an object from Supabase Storage fails."""


@lru_cache
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the service role key."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageConfigurationError(
            "Supabase storage is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def build_xray_storage_path(
    doctor_id: UUID,
    patient_id: UUID,
    extension: str,
) -> str:
    """Build a stable object path: {doctor_id}/{patient_id}/{uuid}{extension}."""
    normalized_extension = extension.lower()
    if not normalized_extension.startswith("."):
        normalized_extension = f".{normalized_extension}"
    return f"{doctor_id}/{patient_id}/{uuid4()}{normalized_extension}"


def upload_xray_file(
    *,
    doctor_id: UUID,
    patient_id: UUID,
    file_bytes: bytes,
    extension: str,
    content_type: str,
) -> str:
    """Upload an X-ray file to the private bucket and return the storage path."""
    settings = get_settings()
    storage_path = build_xray_storage_path(doctor_id, patient_id, extension)
    bucket = settings.supabase_xray_bucket

    try:
        client = get_supabase_client()
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )
    except StorageConfigurationError:
        raise
    except Exception as exc:
        logger.exception("Failed to upload X-ray file to Supabase Storage")
        raise StorageUploadError("Failed to upload X-ray file to storage") from exc

    return storage_path


def delete_xray_file(storage_path: str) -> None:
    """Delete an X-ray object from the private bucket."""
    if not storage_path or storage_path.startswith(("http://", "https://")):
        raise StorageDeleteError("Invalid storage path")

    settings = get_settings()
    bucket = settings.supabase_xray_bucket

    try:
        client = get_supabase_client()
        client.storage.from_(bucket).remove([storage_path])
    except StorageConfigurationError:
        raise
    except Exception as exc:
        logger.exception("Failed to delete X-ray file from Supabase Storage")
        raise StorageDeleteError("Failed to delete X-ray file from storage") from exc


def download_xray_file(storage_path: str) -> bytes:
    """Download a private X-ray object and return raw bytes."""
    if not storage_path or storage_path.startswith(("http://", "https://")):
        raise StorageDownloadError("Invalid storage path")

    settings = get_settings()
    bucket = settings.supabase_xray_bucket

    try:
        client = get_supabase_client()
        data = client.storage.from_(bucket).download(storage_path)
    except StorageConfigurationError:
        raise
    except Exception as exc:
        logger.exception("Failed to download X-ray file from Supabase Storage")
        raise StorageDownloadError("Failed to download X-ray file from storage") from exc

    if not data:
        raise StorageDownloadError("Downloaded X-ray file is empty")
    return bytes(data)


def create_signed_xray_url(
    storage_path: str,
    *,
    expires_in: int | None = None,
) -> str:
    """Create a temporary signed URL for a private X-ray object."""
    if not storage_path or storage_path.startswith(("http://", "https://")):
        raise StorageSignedUrlError("Invalid storage path")

    settings = get_settings()
    expire_seconds = expires_in or settings.supabase_signed_url_expire_seconds
    bucket = settings.supabase_xray_bucket

    try:
        client = get_supabase_client()
        response = client.storage.from_(bucket).create_signed_url(
            storage_path,
            expire_seconds,
        )
    except StorageConfigurationError:
        raise
    except Exception as exc:
        logger.exception("Failed to create signed URL for X-ray file")
        raise StorageSignedUrlError("Failed to create signed URL") from exc

    signed_url = None
    if isinstance(response, dict):
        signed_url = response.get("signedURL") or response.get("signedUrl")
    else:
        signed_url = getattr(response, "signedURL", None) or getattr(
            response, "signedUrl", None
        )
        if not signed_url and hasattr(response, "model_dump"):
            payload = response.model_dump()
            signed_url = payload.get("signedURL") or payload.get("signedUrl")

    if not signed_url:
        raise StorageSignedUrlError("Failed to create signed URL")
    return str(signed_url)
