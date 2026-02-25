import logging
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)

class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = False
    addressing_style = 'path'
    
    def _save(self, name, content):
        """Override to add logging for debugging upload issues."""
        logger.info(f"[Supabase S3] Uploading file: {name}")
        try:
            result = super()._save(name, content)
            logger.info(f"[Supabase S3] Successfully uploaded: {result}")
            return result
        except Exception as e:
            logger.error(f"[Supabase S3] FAILED to upload {name}: {e}", exc_info=True)
            raise
