"""
migrate_cloudinary_private.py
==============================
Script to update existing Cloudinary uploads to 'authenticated' (private) mode.
This ensures raw public CDN URLs for existing files return 401/404 HTTP errors in Incognito.
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLOUDINARY_ENABLED = bool(
    os.getenv("CLOUDINARY_CLOUD_NAME")
    and os.getenv("CLOUDINARY_API_KEY")
    and os.getenv("CLOUDINARY_API_SECRET")
)

def make_existing_files_private():
    if not CLOUDINARY_ENABLED:
        logger.warning("Cloudinary environment variables not set. Skipping Cloudinary migration.")
        return

    import cloudinary
    import cloudinary.api

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

    folders_to_protect = [
        "liceo_uploads/enrollment_docs",
        "liceo_uploads/private_docs",
        "liceo_uploads"
    ]

    for prefix in folders_to_protect:
        try:
            logger.info("Protecting Cloudinary folder prefix: %s ...", prefix)
            result = cloudinary.api.update_resources_access_mode_by_prefix(
                access_mode="authenticated",
                prefix=prefix
            )
            logger.info("Successfully updated prefix %s: %s", prefix, result)
        except Exception as e:
            logger.error("Error updating prefix %s: %s", prefix, e)

if __name__ == "__main__":
    make_existing_files_private()
