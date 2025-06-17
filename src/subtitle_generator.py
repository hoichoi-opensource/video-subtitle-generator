# Add these methods to subtitle_generator.py

def cleanup_gcs_chunks(self):
    """Delete chunks from GCS after successful processing."""
    if not self.bucket or not self.current_job_prefix:
        return
    
    try:
        # List all chunks in the job folder
        chunks_prefix = f"{self.current_job_prefix}/chunks/"
        blobs = self.bucket.list_blobs(prefix=chunks_prefix)
        
        deleted_count = 0
        for blob in blobs:
            try:
                blob.delete()
                deleted_count += 1
                self.logger.debug(f"Deleted GCS chunk: {blob.name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete GCS blob {blob.name}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"Deleted {deleted_count} chunks from GCS")
            
            # Update job summary to indicate chunks were cleaned
            summary_blob = self.bucket.blob(f"{self.current_job_prefix}/job_summary.txt")
            try:
                # Download existing summary
                existing_summary = summary_blob.download_as_text()
                
                # Append cleanup info
                updated_summary = existing_summary + f"\n\nCleanup:\n- Deleted {deleted_count} chunks at {datetime.now().isoformat()}\n"
                
                # Re-upload
                summary_blob.upload_from_string(updated_summary)
            except Exception as e:
                self.logger.debug(f"Could not update job summary: {e}")
                
    except Exception as e:
        self.logger.warning(f"Failed to cleanup GCS chunks: {e}")

def complete_job(self, cleanup_chunks=True):
    """Mark the job as complete in GCS and optionally cleanup chunks."""
    if not self.bucket or not self.current_job_prefix:
        return
    
    try:
        # Clean up chunks first if requested
        if cleanup_chunks:
            self.cleanup_gcs_chunks()
        
        # Create a completion marker
        marker_blob = self.bucket.blob(f"{self.current_job_prefix}/_job_completed.txt")
        marker_blob.upload_from_string(f"Job completed at {datetime.now().isoformat()}")
        
        # Create a summary file
        summary_blob = self.bucket.blob(f"{self.current_job_prefix}/job_summary.txt")
        summary_content = f"""Job Summary
===========
Job Folder: {self.current_job_prefix}
Started: Check _job_started.txt
Completed: {datetime.now().isoformat()}
Bucket: {self.bucket_name}

Contents:
- subtitles/: Generated subtitle files
- chunks/: Video chunks ({"deleted after processing" if cleanup_chunks else "preserved"})

Note: Chunks were {"automatically deleted to save storage" if cleanup_chunks else "preserved"}.
"""
        summary_blob.upload_from_string(summary_content)
        
        self.logger.info(f"Job completed in GCS: {self.current_job_prefix}")
        
    except Exception as e:
        self.logger.warning(f"Failed to mark job complete in GCS: {e}")