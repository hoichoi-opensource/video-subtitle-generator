"""Main processing script for video subtitle generation."""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from .logger import setup_logging, console, print_banner, print_stage_header, log_stage, create_stage_display
from .config import get_config, reload_config
from .utils import (
    validate_video_file, get_video_info, generate_job_id, 
    ensure_directory, clean_filename, check_disk_space,
    save_job_metadata, load_job_metadata, estimate_processing_time,
    format_eta, format_duration
)
from .video_processor import VideoProcessor
from .gcs_manager import GCSManager
from .subtitle_generator import SubtitleGenerator


class VideoSubtitleProcessor:
    """Main processor for video subtitle generation."""
    
    def __init__(self):
        self.logger = setup_logging("main_processor")
        self.config = get_config()
        self.video_processor = VideoProcessor()
        self.gcs_manager = None
        self.subtitle_generator = SubtitleGenerator()
        self.stages = [
            "Validating Input File",
            "Analyzing Video",
            "Creating Video Chunks",
            "Connecting to Google Cloud",
            "Uploading Chunks to GCS",
            "Initializing Vertex AI",
            "Generating Subtitles",
            "Downloading Subtitles",
            "Merging Subtitles",
            "Finalizing Output"
        ]
        self.current_stage = 0
        self.total_stages = len(self.stages)
    
    def process_video(
        self,
        video_path: str,
        language: str = "en",
        output_dir: Optional[str] = None,
        job_id: Optional[str] = None,
        resume_from_stage: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a video file to generate subtitles."""
        start_time = datetime.now()
        
        # Print banner
        print_banner()
        
        # Generate job ID if not provided
        video_name = clean_filename(Path(video_path).name)
        if not job_id:
            job_id = generate_job_id(video_name, language)
        
        # Print stage header
        language_info = self.config.get_language_by_code(language)
        print_stage_header(video_name, f"{language_info['flag']} {language_info['name']}", job_id)
        
        # Set up output directory
        if not output_dir:
            output_dir = Path(self.config.paths["output_dir"]) / video_name / language
        ensure_directory(output_dir)
        
        # Initialize job metadata
        job_metadata = {
            "job_id": job_id,
            "video_name": video_name,
            "video_path": video_path,
            "language": language,
            "start_time": start_time.isoformat(),
            "stages_completed": [],
            "output_dir": str(output_dir)
        }
        
        # Resume logic
        if resume_from_stage:
            self.current_stage = resume_from_stage - 1
            # Load existing metadata
            existing_metadata = load_job_metadata(job_id, output_dir)
            if existing_metadata:
                job_metadata.update(existing_metadata)
        
        # Create stage progress display
        progress = create_stage_display()
        
        try:
            # Process each stage
            for stage_num in range(self.current_stage, self.total_stages):
                stage_name = self.stages[stage_num]
                
                # Update stage display
                log_stage(stage_num + 1, self.total_stages, stage_name, "IN_PROGRESS")
                
                # Execute stage
                stage_result = self._execute_stage(
                    stage_num + 1,
                    stage_name,
                    job_metadata,
                    progress
                )
                
                # Update metadata
                job_metadata["stages_completed"].append({
                    "stage": stage_num + 1,
                    "name": stage_name,
                    "completed_at": datetime.now().isoformat(),
                    "result": stage_result
                })
                
                # Save metadata after each stage
                save_job_metadata(job_id, job_metadata, output_dir)
                
                # Update stage display
                log_stage(stage_num + 1, self.total_stages, stage_name, "COMPLETED")
            
            # Calculate total time
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            job_metadata["end_time"] = end_time.isoformat()
            job_metadata["total_time"] = total_time
            job_metadata["status"] = "COMPLETED"
            
            # Final save
            save_job_metadata(job_id, job_metadata, output_dir)
            
            # Print completion message
            console.print(f"\n✅ [bold green]Processing completed successfully![/bold green]")
            console.print(f"📁 Output directory: {output_dir}")
            console.print(f"⏱️  Total time: {format_duration(total_time)}")
            
            return job_metadata
            
        except Exception as e:
            # Log error
            self.logger.error(f"Processing failed: {str(e)}")
            
            # Update metadata
            job_metadata["status"] = "FAILED"
            job_metadata["error"] = str(e)
            job_metadata["failed_at_stage"] = self.current_stage + 1
            
            # Save metadata
            save_job_metadata(job_id, job_metadata, output_dir)
            
            # Print error message
            console.print(f"\n❌ [bold red]Processing failed at stage {self.current_stage + 1}![/bold red]")
            console.print(f"Error: {str(e)}")
            console.print(f"\nYou can resume from this stage using: --resume {job_id} --stage {self.current_stage + 1}")
            
            raise
    
    def _execute_stage(
        self,
        stage_num: int,
        stage_name: str,
        job_metadata: Dict[str, Any],
        progress
    ) -> Dict[str, Any]:
        """Execute a specific processing stage."""
        result = {}
        
        if stage_num == 1:  # Validating Input File
            is_valid, message = validate_video_file(job_metadata["video_path"])
            if not is_valid:
                raise ValueError(f"Invalid video file: {message}")
            result["validation"] = message
            
        elif stage_num == 2:  # Analyzing Video
            video_info = get_video_info(job_metadata["video_path"])
            job_metadata["video_info"] = video_info
            
            # Check disk space
            is_ok, message = check_disk_space(self.config.paths["temp_dir"])
            if not is_ok:
                raise ValueError(message)
            
            result["video_info"] = video_info
            result["disk_check"] = message
            
        elif stage_num == 3:  # Creating Video Chunks
            chunk_dir = Path(job_metadata["output_dir"]) / "chunks"
            chunks = self.video_processor.create_chunks(
                job_metadata["video_path"],
                str(chunk_dir)
            )
            job_metadata["chunks"] = chunks
            result["num_chunks"] = len(chunks)
            
        elif stage_num == 4:  # Connecting to Google Cloud
            self.gcs_manager = GCSManager()
            is_connected, message = self.gcs_manager.test_connection()
            if not is_connected:
                raise ConnectionError(message)
            result["connection"] = message
            
        elif stage_num == 5:  # Uploading Chunks to GCS
            job_folder = self.gcs_manager.create_job_folder(job_metadata["job_id"])
            gcs_paths = self.gcs_manager.upload_chunks(
                job_metadata["chunks"],
                job_metadata["job_id"]
            )
            job_metadata["gcs_paths"] = gcs_paths
            result["uploaded_chunks"] = len(gcs_paths)
            
        elif stage_num == 6:  # Initializing Vertex AI
            # Already initialized in __init__
            result["model"] = self.config.vertex_ai["model"]
            
        elif stage_num == 7:  # Generating Subtitles
            subtitle_dir = Path(job_metadata["output_dir"]) / "subtitles"
            subtitle_files = self.subtitle_generator.generate_subtitles_for_chunks(
                job_metadata["chunks"],
                job_metadata["gcs_paths"],
                str(subtitle_dir),
                job_metadata["language"],
                job_metadata["job_id"]
            )
            job_metadata["subtitle_files"] = subtitle_files
            result["generated_subtitles"] = len(subtitle_files)
            
        elif stage_num == 8:  # Downloading Subtitles
            # Subtitles are already local in our case
            result["subtitle_count"] = len(job_metadata["subtitle_files"])
            
        elif stage_num == 9:  # Merging Subtitles
            final_dir = Path(job_metadata["output_dir"]) / "final"
            ensure_directory(final_dir)
            
            merged_subtitle = final_dir / f"{job_metadata['video_name']}_{job_metadata['language']}_subtitled.srt"
            
            self.video_processor.merge_subtitles(
                job_metadata["subtitle_files"],
                str(merged_subtitle),
                {"chunks": job_metadata["chunks"]}
            )
            
            job_metadata["final_subtitle"] = str(merged_subtitle)
            result["merged_file"] = str(merged_subtitle)
            
        elif stage_num == 10:  # Finalizing Output
            # Clean up chunks if configured
            if not self.config.output["keep_chunks"]:
                chunk_dir = Path(job_metadata["output_dir"]) / "chunks"
                self.video_processor.clean_chunks(str(chunk_dir))
            
            # Generate additional formats if configured
            if "vtt" in self.config.output["subtitle_formats"]:
                vtt_file = str(job_metadata["final_subtitle"]).replace('.srt', '.vtt')
                self.subtitle_generator.convert_to_vtt(
                    job_metadata["final_subtitle"],
                    vtt_file
                )
                job_metadata["vtt_file"] = vtt_file
            
            # Burn subtitles if configured
            if self.config.output["burn_subtitles"]:
                final_video = str(job_metadata["final_subtitle"]).replace('.srt', '.mp4')
                self.video_processor.burn_subtitles(
                    job_metadata["video_path"],
                    job_metadata["final_subtitle"],
                    final_video
                )
                job_metadata["final_video"] = final_video
            
            result["finalized"] = True
        
        return result
    
    def batch_process(
        self,
        input_dir: str,
        language: str = "en",
        parallel: bool = False
    ) -> List[Dict[str, Any]]:
        """Process multiple videos in a directory."""
        input_path = Path(input_dir)
        
        # Find all video files
        video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(input_path.glob(f"*{ext}"))
        
        if not video_files:
            console.print(f"❌ No video files found in: {input_dir}")
            return []
        
        console.print(f"Found {len(video_files)} video files to process")
        
        results = []
        
        for i, video_file in enumerate(video_files, 1):
            console.print(f"\n[bold cyan]Processing video {i}/{len(video_files)}: {video_file.name}[/bold cyan]")
            
            try:
                result = self.process_video(
                    str(video_file),
                    language=language
                )
                results.append(result)
            except Exception as e:
                console.print(f"❌ Failed to process {video_file.name}: {str(e)}")
                results.append({
                    "video_name": video_file.name,
                    "status": "FAILED",
                    "error": str(e)
                })
        
        # Print summary
        successful = sum(1 for r in results if r.get("status") == "COMPLETED")
        failed = len(results) - successful
        
        console.print(f"\n[bold]Batch Processing Summary:[/bold]")
        console.print(f"✅ Successful: {successful}")
        console.print(f"❌ Failed: {failed}")
        console.print(f"📊 Total: {len(results)}")
        
        return results
    
    def check_status(self, job_id: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Check the status of a processing job."""
        if not output_dir:
            # Try to find the job in output directory
            output_path = Path(self.config.paths["output_dir"])
            for video_dir in output_path.iterdir():
                if video_dir.is_dir():
                    for lang_dir in video_dir.iterdir():
                        if lang_dir.is_dir():
                            metadata = load_job_metadata(job_id, str(lang_dir))
                            if metadata:
                                return metadata
        else:
            metadata = load_job_metadata(job_id, output_dir)
            if metadata:
                return metadata
        
        return {"error": f"Job not found: {job_id}"}
    
    def cleanup(self, older_than_days: int = 7):
        """Clean up old temporary files and jobs."""
        console.print(f"🧹 Cleaning up files older than {older_than_days} days...")
        
        # Clean temp directory
        temp_path = Path(self.config.paths["temp_dir"])
        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
        
        cleaned_count = 0
        for item in temp_path.iterdir():
            if item.stat().st_mtime < cutoff_time:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                cleaned_count += 1
        
        console.print(f"✅ Cleaned {cleaned_count} items from temp directory")
        
        # Clean old GCS jobs if configured
        if self.gcs_manager:
            # List and clean old jobs
            console.print("🌐 Cleaning old GCS jobs...")
            # Implementation depends on GCS structure
        
        console.print("✅ Cleanup completed")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Video Subtitle Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process a single video")
    process_parser.add_argument("video", help="Path to video file")
    process_parser.add_argument("-l", "--language", default="en", help="Language code (en, hi, bn)")
    process_parser.add_argument("-o", "--output", help="Output directory")
    process_parser.add_argument("--resume", help="Resume from job ID")
    process_parser.add_argument("--stage", type=int, help="Stage number to resume from")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Process multiple videos")
    batch_parser.add_argument("directory", help="Directory containing videos")
    batch_parser.add_argument("-l", "--language", default="en", help="Language code")
    batch_parser.add_argument("--parallel", action="store_true", help="Process in parallel")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("job_id", help="Job ID to check")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean temporary files")
    cleanup_parser.add_argument("--days", type=int, default=7, help="Clean files older than N days")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize processor
    processor = VideoSubtitleProcessor()
    
    try:
        if args.command == "process":
            processor.process_video(
                args.video,
                language=args.language,
                output_dir=args.output,
                job_id=args.resume,
                resume_from_stage=args.stage
            )
        
        elif args.command == "batch":
            processor.batch_process(
                args.directory,
                language=args.language,
                parallel=args.parallel
            )
        
        elif args.command == "status":
            status = processor.check_status(args.job_id)
            console.print(json.dumps(status, indent=2))
        
        elif args.command == "cleanup":
            processor.cleanup(older_than_days=args.days)
    
    except KeyboardInterrupt:
        console.print("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Error: {str(e)}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()