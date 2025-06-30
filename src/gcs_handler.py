"""
Google Cloud Storage Handler
Manages GCS operations for chunks and subtitles
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound, Forbidden
from google.oauth2 import service_account
from config_manager import ConfigManager
from utils import ensure_directory_exists
from rich.console import Console

# Production imports
from .exceptions import (
    CloudStorageError, AuthenticationError, ValidationError,
    ResourceError, NetworkError
)
from .retry_handler import with_retry, rate_limiters
from .logger import get_logger, log_performance

console = Console()
logger = get_logger(__name__)

class GCSHandler:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.client = None
        self.project_id = config.get('gcp.project_id')
        self.location = config.get('gcp.location', 'us-central1')
        self.bucket_mode = config.get('gcp.bucket_mode', 'create_new')
        self.existing_bucket = config.get('gcp.existing_bucket_name', '')
        
    @log_performance('gcs_init')
    def initialize(self) -> None:
        """Initialize GCS client"""
        auth_method = self.config.get('gcp.auth_method', 'adc')
        logger.info(f"Initializing GCS client with {auth_method} authentication")
        
        try:
            if auth_method == 'service_account':
                # Use service account
                service_account_path = self.config.get('gcp.service_account_path', './service-account.json')
                
                if not Path(service_account_path).exists():
                    raise FileNotFoundError(f"Service account file not found: {service_account_path}")
                    
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                self.client = storage.Client(
                    project=self.project_id,
                    credentials=credentials
                )
            else:
                # Use Application Default Credentials
                self.client = storage.Client(project=self.project_id)
                
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {str(e)}")
            if "authentication" in str(e).lower() or "credentials" in str(e).lower():
                raise AuthenticationError(
                    f"GCS authentication failed: {str(e)}",
                    context={'auth_method': auth_method, 'project_id': self.project_id}
                )
            else:
                raise CloudStorageError(
                    f"Failed to initialize GCS client: {str(e)}",
                    context={'auth_method': auth_method, 'project_id': self.project_id}
                )
            
    @with_retry('storage', circuit_breaker_key='gcs')
    @log_performance('create_job_bucket')
    def create_job_bucket(self, job_id: str) -> str:
        """Create or get bucket for job"""
        if not job_id:
            raise ValidationError("Job ID is required for bucket creation")
        
        logger.info(f"Creating/getting bucket for job {job_id}")""
        if self.bucket_mode == 'use_existing' and self.existing_bucket:
            # Use existing bucket
            bucket_name = self.existing_bucket
            
            # Verify bucket exists and is accessible
            try:
                bucket = self.client.bucket(bucket_name)
                if not bucket.exists():
                    raise CloudStorageError(
                        f"Bucket {bucket_name} does not exist",
                        context={'bucket_name': bucket_name, 'job_id': job_id}
                    )
                logger.info(f"Using existing bucket: {bucket_name}")
            except NotFound:
                raise CloudStorageError(
                    f"Bucket {bucket_name} not found",
                    context={'bucket_name': bucket_name, 'job_id': job_id}
                )
            except Forbidden:
                raise AuthenticationError(
                    f"Access denied to bucket {bucket_name}",
                    context={'bucket_name': bucket_name, 'job_id': job_id}
                )
            except Exception as e:
                raise CloudStorageError(
                    f"Cannot access bucket {bucket_name}: {str(e)}",
                    context={'bucket_name': bucket_name, 'job_id': job_id, 'error': str(e)}
                )
        else:
            # Create new bucket
            bucket_name = f"subtitle-gen-{self.project_id}-{int(time.time())}"
            
            try:
                bucket = self.client.bucket(bucket_name)
                bucket.location = self.location
                bucket.storage_class = 'STANDARD'
                
                # Create bucket
                bucket = self.client.create_bucket(bucket, location=self.location)
                
                # Set lifecycle rule to delete objects after 7 days
                bucket.add_lifecycle_delete_rule(age=7)
                bucket.patch()
                
            except Exception as e:
                if "already exists" in str(e):
                    # Bucket already exists, use it
                    pass
                else:
                    raise RuntimeError(f"Failed to create bucket: {str(e)}")
                    
        return bucket_name
        
    def upload_chunks(self, chunks: List[str], bucket_name: str, 
                     progress_callback: Optional[Callable[[int], None]] = None) -> List[Dict[str, str]]:
        """Upload video chunks to GCS"""
        bucket = self.client.bucket(bucket_name)
        uploaded_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk_path in enumerate(chunks):
            chunk_file = Path(chunk_path)
            
            if not chunk_file.exists():
                raise FileNotFoundError(f"Chunk file not found: {chunk_path}")
                
            # GCS object name
            blob_name = f"chunks/{chunk_file.name}"
            
            try:
                # Upload chunk
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(chunk_file))
                
                uploaded_chunks.append({
                    'local': str(chunk_file),
                    'gcs': f"gs://{bucket_name}/{blob_name}",
                    'blob_name': blob_name,
                    'chunk': chunk_file.name
                })
                
            except Exception as e:
                raise RuntimeError(f"Failed to upload chunk {chunk_file.name}: {str(e)}")
                
            # Update progress
            if progress_callback:
                progress = int((i + 1) / total_chunks * 100)
                progress_callback(progress)
                
        return uploaded_chunks
        
    def download_subtitles(self, subtitles: List[Dict[str, str]], bucket_name: str, 
                          job_id: str, progress_callback: Optional[Callable[[int], None]] = None) -> List[Dict[str, str]]:
        """Download subtitles from GCS"""
        bucket = self.client.bucket(bucket_name)
        
        # Create local subtitles directory
        local_dir = Path(self.config.get('app.temp_dir', 'temp')) / job_id / 'subtitles'
        ensure_directory_exists(str(local_dir))
        
        local_subtitles = []
        total_files = len(subtitles)
        
        for i, subtitle in enumerate(subtitles):
            blob_name = subtitle.get('blob_name', '')
            
            if not blob_name:
                continue
                
            # Local file path
            filename = Path(blob_name).name
            local_path = local_dir / filename
            
            try:
                # Download subtitle
                blob = bucket.blob(blob_name)
                content = blob.download_as_text()
                
                # Save locally
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                # Verify file was saved
                if local_path.exists() and local_path.stat().st_size > 0:
                    local_subtitles.append({
                        'local': str(local_path),
                        'gcs': subtitle.get('gcs', ''),
                        'blob_name': blob_name,
                        'language': subtitle.get('language', ''),
                        'chunk': subtitle.get('chunk', ''),
                        'sdh': subtitle.get('sdh', False),
                        'content': content  # Keep content in memory for merging
                    })
                else:
                    print(f"Warning: Failed to save subtitle file: {local_path}")
                    
            except Exception as e:
                print(f"Error downloading subtitle {blob_name}: {str(e)}")
                continue
                
            # Update progress
            if progress_callback:
                progress = int((i + 1) / total_files * 100)
                progress_callback(progress)
                
        return local_subtitles
        
    def upload_file(self, local_path: str, bucket_name: str, blob_name: str) -> str:
        """Upload a single file to GCS"""
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.upload_from_filename(local_path)
        
        return f"gs://{bucket_name}/{blob_name}"
        
    def download_file(self, bucket_name: str, blob_name: str, local_path: str) -> str:
        """Download a single file from GCS"""
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Ensure directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        blob.download_to_filename(local_path)
        
        return local_path
        
    def list_blobs(self, bucket_name: str, prefix: Optional[str] = None) -> List[str]:
        """List blobs in bucket"""
        bucket = self.client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        return [blob.name for blob in blobs]
        
    def delete_blob(self, bucket_name: str, blob_name: str) -> None:
        """Delete a blob from bucket"""
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        
    def cleanup_job_data(self, bucket_name: str, chunks: List[Dict[str, str]]) -> None:
        """Clean up job data from GCS"""
        bucket = self.client.bucket(bucket_name)
        
        # Delete chunks
        for chunk in chunks:
            blob_name = chunk.get('blob_name', '')
            if blob_name:
                try:
                    blob = bucket.blob(blob_name)
                    blob.delete()
                except:
                    pass
                    
        # Delete subtitles folder
        try:
            blobs = bucket.list_blobs(prefix='subtitles/')
            for blob in blobs:
                blob.delete()
        except:
            pass
            
    def cleanup_chunks(self, bucket_name: str, chunks: List[Dict[str, str]]) -> None:
        """Clean up chunk files from GCS"""
        self.cleanup_job_data(bucket_name, chunks)
