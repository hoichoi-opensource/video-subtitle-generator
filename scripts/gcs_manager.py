"""Google Cloud Storage management module."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from google.cloud import storage
from google.oauth2 import service_account
from tqdm import tqdm

from .logger import setup_logging, console
from .config import get_config
from .utils import ensure_directory


class GCSManager:
    """Handle Google Cloud Storage operations."""
    
    def __init__(self, logger_name: str = "gcs_manager"):
        self.logger = setup_logging(logger_name)
        self.config = get_config()
        self.client = None
        self.bucket = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize GCS client with credentials."""
        try:
            credentials_path = self.config.google_cloud["credentials_path"]
            
            if not Path(credentials_path).exists():
                raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            
            self.client = storage.Client(
                project=self.config.google_cloud["project_id"],
                credentials=credentials
            )
            
            # Get or create bucket
            bucket_name = self.config.google_cloud["bucket_name"]
            try:
                self.bucket = self.client.get_bucket(bucket_name)
                self.logger.info(f"Connected to bucket: {bucket_name}")
            except Exception:
                self.logger.info(f"Creating bucket: {bucket_name}")
                self.bucket = self.client.create_bucket(
                    bucket_name,
                    location=self.config.google_cloud["location"]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to initialize GCS client: {str(e)}")
            raise
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test GCS connection."""
        try:
            # Try to list buckets
            list(self.client.list_buckets(max_results=1))
            return True, "GCS connection successful"
        except Exception as e:
            return False, f"GCS connection failed: {str(e)}"
    
    def create_job_folder(self, job_id: str) -> str:
        """Create a folder for the job in GCS."""
        folder_path = f"jobs/{job_id}/"
        # Create a placeholder file to establish the folder
        blob = self.bucket.blob(f"{folder_path}.folder")
        blob.upload_from_string("")
        self.logger.info(f"Created job folder: {folder_path}")
        return folder_path
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback=None
    ) -> str:
        """Upload a file to GCS with progress tracking."""
        file_size = Path(local_path).stat().st_size
        
        blob = self.bucket.blob(remote_path)
        
        # Upload with progress tracking
        with open(local_path, 'rb') as f:
            with tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                desc=f"Uploading {Path(local_path).name}"
            ) as pbar:
                def update_progress(bytes_uploaded):
                    pbar.update(bytes_uploaded - pbar.n)
                    if progress_callback:
                        progress_callback(bytes_uploaded, file_size)
                
                blob.upload_from_file(
                    f,
                    rewind=True,
                    size=file_size,
                    progress_callback=update_progress if file_size > 5 * 1024 * 1024 else None
                )
        
        self.logger.info(f"Uploaded: {local_path} -> gs://{self.bucket.name}/{remote_path}")
        return f"gs://{self.bucket.name}/{remote_path}"
    
    def upload_chunks(
        self,
        chunks: List[Dict[str, Any]],
        job_id: str,
        progress_callback=None
    ) -> List[str]:
        """Upload video chunks to GCS."""
        remote_paths = []
        
        for i, chunk in enumerate(chunks):
            local_path = chunk['path']
            remote_path = f"jobs/{job_id}/chunks/{chunk['filename']}"
            
            try:
                gcs_path = self.upload_file(local_path, remote_path)
                remote_paths.append(gcs_path)
                
                if progress_callback:
                    progress_callback(i + 1, len(chunks))
                    
            except Exception as e:
                self.logger.error(f"Failed to upload chunk {chunk['filename']}: {str(e)}")
                raise
        
        return remote_paths
    
    def download_file(
        self,
        remote_path: str,
        local_path: str,
        progress_callback=None
    ) -> str:
        """Download a file from GCS."""
        blob = self.bucket.blob(remote_path)
        
        if not blob.exists():
            raise FileNotFoundError(f"File not found in GCS: {remote_path}")
        
        # Ensure local directory exists
        ensure_directory(Path(local_path).parent)
        
        # Download with progress tracking
        file_size = blob.size
        
        with open(local_path, 'wb') as f:
            with tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                desc=f"Downloading {Path(local_path).name}"
            ) as pbar:
                def update_progress(bytes_downloaded):
                    pbar.update(bytes_downloaded - pbar.n)
                    if progress_callback:
                        progress_callback(bytes_downloaded, file_size)
                
                blob.download_to_file(
                    f,
                    progress_callback=update_progress if file_size > 5 * 1024 * 1024 else None
                )
        
        self.logger.info(f"Downloaded: gs://{self.bucket.name}/{remote_path} -> {local_path}")
        return local_path
    
    def list_job_files(self, job_id: str, prefix: str = "") -> List[str]:
        """List files in a job folder."""
        job_prefix = f"jobs/{job_id}/{prefix}"
        blobs = self.bucket.list_blobs(prefix=job_prefix)
        
        files = []
        for blob in blobs:
            if not blob.name.endswith('.folder'):
                files.append(blob.name)
        
        return files
    
    def cleanup_job(self, job_id: str, older_than_days: int = 7):
        """Clean up old job files from GCS."""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        job_prefix = f"jobs/{job_id}/"
        
        blobs = self.bucket.list_blobs(prefix=job_prefix)
        deleted_count = 0
        
        for blob in blobs:
            if blob.time_created < cutoff_date:
                blob.delete()
                deleted_count += 1
        
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} files from job: {job_id}")
    
    def get_signed_url(self, remote_path: str, expiration_hours: int = 24) -> str:
        """Generate a signed URL for temporary access."""
        blob = self.bucket.blob(remote_path)
        
        url = blob.generate_signed_url(
            expiration=timedelta(hours=expiration_hours),
            method='GET'
        )
        
        return url