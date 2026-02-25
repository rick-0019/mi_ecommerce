import logging
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = True  # Skip exists() check entirely — avoids HeadObject 403

    def exists(self, name):
        """
        Override exists() to avoid HeadObject calls that Supabase S3 rejects with 403.
        Django uses this to check if a file already exists before saving.
        Returning False means it will always proceed to upload.
        """
        return False

    def _save(self, name, content):
        """Override to add logging for debugging upload issues."""
        logger.info(f"[Supabase S3] Uploading file: {name} to bucket: {self.bucket_name}")
        try:
            result = super()._save(name, content)
            logger.info(f"[Supabase S3] Successfully uploaded: {result}")
            return result
        except Exception as e:
            logger.error(f"[Supabase S3] FAILED to upload {name}: {e}", exc_info=True)
            raise

    def url(self, name):
        """
        Override url() to return the Supabase public URL directly.
        Must include self.location ('media') to match the actual storage path.
        File in bucket: productos/media/productos/fotos/file.jpg
        Public URL: https://<ref>.supabase.co/storage/v1/object/public/productos/media/productos/fotos/file.jpg
        """
        from django.conf import settings
        return f"{settings.MEDIA_URL}{self.location}/{name}"
