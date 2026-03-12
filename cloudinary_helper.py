"""
cloudinary_helper.py
====================
Central helper for uploading files to Cloudinary.

Environment variables required (set in Railway):
  CLOUDINARY_CLOUD_NAME
  CLOUDINARY_API_KEY
  CLOUDINARY_API_SECRET

If these are NOT set, falls back to local file storage (for development).
"""

import os
import uuid
import logging

logger = logging.getLogger(__name__)

# ── Check if Cloudinary is configured ──────────────────────────────────────
CLOUDINARY_ENABLED = bool(
    os.getenv("CLOUDINARY_CLOUD_NAME")
    and os.getenv("CLOUDINARY_API_KEY")
    and os.getenv("CLOUDINARY_API_SECRET")
)

if CLOUDINARY_ENABLED:
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )
    logger.info("Cloudinary configured — uploads will go to cloud.")
else:
    logger.warning(
        "Cloudinary env vars not set — falling back to LOCAL file storage. "
        "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET "
        "for production use."
    )


# ── Local fallback folder ───────────────────────────────────────────────────
LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(LOCAL_UPLOAD_FOLDER, exist_ok=True)


def upload_file(file_storage, folder: str = "liceo_uploads") -> str:
    """
    Upload a Werkzeug FileStorage object.

    - If Cloudinary env vars are set  → uploads to Cloudinary, returns HTTPS URL.
    - Otherwise                       → saves locally, returns '/uploads/<filename>'.

    Args:
        file_storage: Werkzeug FileStorage (from request.files)
        folder:       Cloudinary folder name (ignored for local storage)

    Returns:
        str: Public URL of the uploaded file.

    Raises:
        Exception if upload fails.
    """
    if CLOUDINARY_ENABLED:
        return _upload_to_cloudinary(file_storage, folder)
    else:
        return _upload_local(file_storage)


def upload_file_to_subfolder(file_storage, subfolder: str) -> str:
    """
    Convenience wrapper — uploads to 'liceo_uploads/<subfolder>'.
    """
    return upload_file(file_storage, folder=f"liceo_uploads/{subfolder}")


# ── Internal: Cloudinary ────────────────────────────────────────────────────
def _upload_to_cloudinary(file_storage, folder: str) -> str:
    # Check if file is a PDF
    is_pdf = file_storage.filename.lower().endswith('.pdf') if file_storage.filename else False
    
    result = cloudinary.uploader.upload(
        file_storage,
        folder=folder,
        resource_type="raw" if is_pdf else "auto",   # explicitly use raw for PDFs to allow public access without 401
        use_filename=False,
        unique_filename=True,
    )
    url = result.get("secure_url")
    if not url:
        raise Exception("Cloudinary upload succeeded but returned no URL.")
        
    # As a fallback for any auto-assigned image/upload URLs that are actually PDFs
    if url.endswith('.pdf') and '/image/upload/' in url:
        url = url.replace('/image/upload/', '/raw/upload/')
        
    logger.info("Uploaded to Cloudinary: %s", url)
    return url


# ── Internal: Local fallback ────────────────────────────────────────────────
def _upload_local(file_storage) -> str:
    from werkzeug.utils import secure_filename

    original = secure_filename(file_storage.filename or "file")
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else "bin"
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(LOCAL_UPLOAD_FOLDER, unique_name)
    file_storage.save(file_path)
    logger.info("Saved locally: %s", file_path)
    return f"/uploads/{unique_name}"


def upload_announcement_photo(file_storage) -> str:
    """Upload an announcement photo. Returns public URL."""
    return upload_file(file_storage, folder="liceo_uploads/announcements")


def upload_enrollment_document(file_storage) -> str:
    """Upload an enrollment document (PDF/image). Returns public URL."""
    return upload_file(file_storage, folder="liceo_uploads/enrollment_docs")
