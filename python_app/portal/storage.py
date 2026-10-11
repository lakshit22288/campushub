import logging
from pathlib import PurePath
from urllib.parse import quote
from uuid import uuid4

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
FILE_SIGNATURES = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
}
PROJECT_CONTENT_TYPES = ALLOWED_CONTENT_TYPES | {
    "application/zip",
    "application/x-zip-compressed",
}
PROJECT_FILE_SIGNATURES = {
    **FILE_SIGNATURES,
    "application/zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    "application/x-zip-compressed": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}


class StorageUploadError(Exception):
    pass


def upload_note_file(uploaded_file):
    return _upload_file(uploaded_file, folder="notes")


def upload_announcement_file(uploaded_file):
    return _upload_file(uploaded_file, folder="announcements")


def upload_project_file(uploaded_file):
    return _upload_file(
        uploaded_file,
        folder="projects",
        allowed_content_types=PROJECT_CONTENT_TYPES,
        file_signatures=PROJECT_FILE_SIGNATURES,
        compatible_extensions={
            "application/pdf": {".pdf"},
            "image/png": {".png"},
            "image/jpeg": {".jpg", ".jpeg"},
            "application/zip": {".zip"},
            "application/x-zip-compressed": {".zip"},
        },
    )


def _upload_file(
    uploaded_file,
    *,
    folder,
    allowed_content_types=ALLOWED_CONTENT_TYPES,
    file_signatures=FILE_SIGNATURES,
    compatible_extensions=None,
):
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise StorageUploadError("The file must be 10 MB or smaller.")
    if uploaded_file.content_type not in allowed_content_types:
        if folder == "projects":
            raise StorageUploadError("You can upload ZIP, PDF, PNG, and JPG files only.")
        if folder == "announcements":
            raise StorageUploadError("You can upload PDF, PNG, and JPG notice files only.")
        raise StorageUploadError("You can upload PDF, PNG, and JPG files only.")

    supabase_url = settings.SUPABASE_URL.rstrip("/")
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY
    bucket = settings.SUPABASE_STORAGE_BUCKET
    if not supabase_url or not service_key or not bucket:
        raise StorageUploadError(
            "File uploads are not configured. Ask an administrator to check the Supabase Storage settings."
        )

    extension = PurePath(uploaded_file.name).suffix.lower()
    if compatible_extensions is None:
        compatible_extensions = {
            "application/pdf": {".pdf"},
            "image/png": {".png"},
            "image/jpeg": {".jpg", ".jpeg"},
        }
    if extension not in compatible_extensions[uploaded_file.content_type]:
        if folder == "projects":
            raise StorageUploadError("The file extension must be ZIP, PDF, PNG, or JPG.")
        if folder == "announcements":
            raise StorageUploadError("The notice file extension must be PDF, PNG, or JPG.")
        raise StorageUploadError("The file extension must be PDF, PNG, or JPG.")
    file_data = uploaded_file.read()
    if not any(
        file_data.startswith(signature)
        for signature in file_signatures[uploaded_file.content_type]
    ):
        raise StorageUploadError("The file's actual format does not match its selected type.")
    object_name = f"{folder}/{uuid4().hex}{extension}"
    encoded_bucket = quote(bucket, safe="")
    encoded_object = quote(object_name, safe="/")
    endpoint = f"{supabase_url}/storage/v1/object/{encoded_bucket}/{encoded_object}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": uploaded_file.content_type,
        "x-upsert": "false",
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(endpoint, content=file_data, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as error:
        logger.warning("Supabase Storage upload timed out")
        raise StorageUploadError("The file upload timed out. Please try again.") from error
    except httpx.HTTPStatusError as error:
        logger.error(
            "Supabase Storage rejected a %s file upload with HTTP %s",
            folder,
            error.response.status_code,
        )
        raise StorageUploadError("Supabase Storage rejected the upload. Check the storage bucket and settings.") from error
    except httpx.RequestError as error:
        logger.exception("Could not reach Supabase Storage")
        raise StorageUploadError("Could not connect to Supabase Storage.") from error

    public_url = (
        f"{supabase_url}/storage/v1/object/public/"
        f"{encoded_bucket}/{encoded_object}"
    )
    safe_filename = PurePath(uploaded_file.name).name[:255]
    return public_url, safe_filename
