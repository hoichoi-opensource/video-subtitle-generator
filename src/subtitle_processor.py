#!/usr/bin/env python3
"""
Video Subtitle Processor - Main Application Logic
Handles the complete subtitle generation pipeline
"""

import os
import sys
import time
import json
import shutil
import click
from pathlib import Path
from typing import Optional, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

from config_manager import ConfigManager
from state_manager import StateManager, JobState, ProcessingStage
from language_selector import LanguageSelector
from video_chunker import VideoChunker
from gcs_handler import GCSHandler
from ai_generator import AIGenerator
from subtitle_merger import SubtitleMerger
from quality_analyzer import QualityAnalyzer
from utils import ensure_directory_exists, validate_video_file

console = Console()

class SubtitleProcessor:
    def __init__(self):
        self.config = ConfigManager()
        self.state_manager = StateManager()
        self.language_selector = LanguageSelector(self.config)
        self.video_chunker = VideoChunker(self.config)
        self.gcs_handler = GCSHandler(self.config)
        self.ai_generator = AIGenerator(self.config)
        self.subtitle_merger = SubtitleMerger(self.config)
        self.quality_analyzer = QualityAnalyzer(self.config)
        
        # Ensure all required directories exist
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensure all required directories exist with proper permissions"""
        directories = [
            self.config.get('app.output_dir', 'output'),
            self.config.get('app.temp_dir', 'temp'),
            self.config.get('app.jobs_dir', 'jobs'),
            'input',
            'chunks',
            'subtitles',
            'logs'
        ]
        
        for directory in directories:
            ensure_directory_exists(directory)
            
        console.print("[green]✓ All directories initialized[/green]")
        
    def display_banner(self):
        """Display application banner"""
        banner = Panel(
            "[bold blue]🎬 VIDEO SUBTITLE GENERATOR v1.0 🎬[/bold blue]\n" +
            "[italic]Powered by Google Gemini AI[/italic]",
            style="blue",
            expand=False
        )
        console.print(banner, justify="center")
        
    def main_menu(self):
        """Display main menu and handle selection"""
        self.display_banner()
        
        # Show input folder status
        input_dir = Path("input")
        video_files = []
        supported_formats = self.config.get('system.supported_video_formats', ['mp4', 'avi', 'mkv', 'mov', 'webm'])
        for ext in supported_formats:
            video_files.extend(input_dir.glob(f"*.{ext}"))
            video_files.extend(input_dir.glob(f"*.{ext.upper()}"))
        
        if video_files:
            console.print(f"\n[green]✅ Found {len(video_files)} video file(s) in input folder[/green]")
        else:
            console.print(f"\n[yellow]📁 No videos in input folder ({input_dir.absolute()})[/yellow]")
        
        table = Table(show_header=False, box=None)
        table.add_row("[bold]1[/bold]", "Process Single Video" + (" [dim](select from input folder)[/dim]" if video_files else ""))
        table.add_row("[bold]2[/bold]", "Batch Process Videos")
        table.add_row("[bold]3[/bold]", "Resume Previous Job")
        table.add_row("[bold]4[/bold]", "View Job History")
        table.add_row("[bold]5[/bold]", "Exit")
        
        console.print("\n[bold]Select an option:[/bold]")
        console.print(table)
        
        choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "3", "4", "5"], default="1")
        
        if choice == "1":
            self.process_single_video()
        elif choice == "2":
            self.batch_process_videos()
        elif choice == "3":
            self.resume_job()
        elif choice == "4":
            self.view_job_history()
        elif choice == "5":
            console.print("\n[green]Thank you for using Video Subtitle Generator![/green]")
            sys.exit(0)
            
    def process_single_video(self, video_path: Optional[str] = None):
        """Process a single video file"""
        if not video_path:
            # Interactive mode - prompt for video
            input_dir = Path("input")
            input_dir.mkdir(exist_ok=True)
            
            console.print(f"\n[dim]Checking for videos in: {input_dir.absolute()}[/dim]")
            
            # List available videos in input directory
            video_files = []
            supported_formats = self.config.get('system.supported_video_formats', ['mp4', 'avi', 'mkv', 'mov', 'webm'])
            
            for ext in supported_formats:
                video_files.extend(input_dir.glob(f"*.{ext}"))
                video_files.extend(input_dir.glob(f"*.{ext.upper()}"))
            
            console.print(f"[dim]Found {len(video_files)} video files[/dim]")
            
            if video_files:
                console.print("\n[cyan]Available videos in input folder:[/cyan]")
                for i, vf in enumerate(video_files, 1):
                    file_size = vf.stat().st_size / (1024**2)  # Size in MB
                    console.print(f"  [{i}] {vf.name} ({file_size:.1f} MB)")
                console.print(f"  [0] Enter custom path")
                
                choice = Prompt.ask("\nSelect video or enter 0 for custom path", default="1")
                if choice.isdigit() and 1 <= int(choice) <= len(video_files):
                    video_path = str(video_files[int(choice) - 1])
                    console.print(f"[green]Selected: {Path(video_path).name}[/green]")
                else:
                    video_path = Prompt.ask("Enter video path")
            else:
                console.print(f"\n[yellow]No video files found in input folder.[/yellow]")
                console.print(f"[yellow]Supported formats: {', '.join(supported_formats)}[/yellow]")
                console.print(f"[yellow]Please add video files to: {input_dir.absolute()}[/yellow]")
                video_path = Prompt.ask("📹 Or enter video path directly")
        
        # Resolve path
        video_path = Path(video_path).resolve()
        
        # Validate video
        if not video_path.exists():
            console.print(f"[red]❌ Video file not found: {video_path}[/red]")
            return
            
        if not validate_video_file(str(video_path)):
            console.print(f"[red]❌ Invalid video file: {video_path}[/red]")
            return
            
        console.print(f"\n[green]✅ Video loaded:[/green] {video_path.name}")
        
        # Language selection
        selected_languages, enable_sdh = self.language_selector.select_languages()
        
        # Create job
        job = self.state_manager.create_job(
            video_path=str(video_path),
            languages=selected_languages,
            enable_sdh=enable_sdh
        )
        
        # Display processing summary
        console.print(Panel(
            f"[bold]PROCESSING SUMMARY[/bold]\n\n" +
            f"📹 Video: {video_path.name}\n" +
            f"📁 Size: {video_path.stat().st_size / (1024**2):.1f} MB\n" +
            f"🎤 Source Audio: Bengali\n" +
            f"📝 Target Languages: {', '.join([l.upper() for l in selected_languages])}\n" +
            f"📄 Formats: {'Regular CC + SDH' if enable_sdh else 'Regular CC only'}\n" +
            f"🆔 Job ID: {job.job_id}",
            style="blue"
        ))
        
        if Confirm.ask("\nStart processing?", default=True):
            self.process_job(job)
        else:
            console.print("[yellow]Processing cancelled[/yellow]")
            
    def process_job(self, job: JobState):
        """Process a job through all stages"""
        stages = [
            (ProcessingStage.VALIDATING, "Validating Input File", self.validate_input),
            (ProcessingStage.ANALYZING, "Analyzing Video", self.analyze_video),
            (ProcessingStage.CHUNKING, "Creating Video Chunks", self.create_chunks),
            (ProcessingStage.CONNECTING, "Connecting to Google Cloud", self.connect_gcs),
            (ProcessingStage.UPLOADING, "Uploading Chunks to GCS", self.upload_chunks),
            (ProcessingStage.INITIALIZING, "Initializing Vertex AI", self.initialize_ai),
            (ProcessingStage.GENERATING, "Generating Subtitles", self.generate_subtitles),
            (ProcessingStage.DOWNLOADING, "Downloading Subtitles", self.download_subtitles),
            (ProcessingStage.MERGING, "Merging Subtitles", self.merge_subtitles),
            (ProcessingStage.FINALIZING, "Finalizing Output", self.finalize_output)
        ]
        
        console.print(Panel("[bold]PROCESSING PIPELINE[/bold]", style="blue"))
        
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            overall_task = progress.add_task("[cyan]Overall Progress", total=len(stages))
            
            for stage, description, handler in stages:
                # Skip completed stages when resuming
                if job.current_stage.value >= stage.value and stage != ProcessingStage.FAILED:
                    progress.update(overall_task, advance=1)
                    console.print(f"[dim]✓ {description} (already completed)[/dim]")
                    continue
                    
                stage_task = progress.add_task(f"[yellow]{description}[/yellow]", total=100)
                
                try:
                    # Update job stage
                    job.current_stage = stage
                    job.metadata['current_stage_name'] = description
                    self.state_manager.save_job(job)
                    
                    # Execute stage
                    handler(job, lambda p: progress.update(stage_task, completed=p))
                    
                    # Mark stage complete
                    progress.update(stage_task, completed=100)
                    console.print(f"[green]✅[/green] {description}")
                    progress.update(overall_task, advance=1)
                    
                except Exception as e:
                    console.print(f"[red]❌ Error in {description}: {str(e)}[/red]")
                    job.current_stage = ProcessingStage.FAILED
                    job.error = str(e)
                    self.state_manager.save_job(job)
                    
                    if not self.handle_error(job, stage, str(e)):
                        return
                        
        # Job completed successfully
        if job.current_stage != ProcessingStage.FAILED:
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            output_dir = Path(self.config.get('app.output_dir', 'output')) / job.video_name
            output_files = list(output_dir.glob("*.srt")) + list(output_dir.glob("*.vtt"))
            
            console.print(Panel(
                "[bold green]✅ PROCESSING COMPLETE![/bold green]\n\n" +
                f"⏱️  Time taken: {minutes}m {seconds}s\n" +
                f"📁 Output directory: {output_dir}\n" +
                f"📄 Files generated: {len(output_files)}\n\n" +
                "[bold]Generated files:[/bold]\n" +
                "\n".join([f"  • {f.name}" for f in sorted(output_files)]),
                style="green"
            ))
            
            job.current_stage = ProcessingStage.COMPLETED
            job.completed_at = time.time()
            self.state_manager.save_job(job)
            
    def validate_input(self, job: JobState, progress_callback):
        """Stage 1: Validate input file"""
        video_path = Path(job.video_path)
        
        progress_callback(20)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        progress_callback(40)
        
        # Check format
        if video_path.suffix.lower()[1:] not in self.config.get('system.supported_video_formats'):
            raise ValueError(f"Unsupported video format: {video_path.suffix}")
            
        progress_callback(60)
        
        # Check file size
        file_size_gb = video_path.stat().st_size / (1024**3)
        if file_size_gb > 10:
            console.print(f"[yellow]⚠️  Large file detected: {file_size_gb:.1f}GB[/yellow]")
            
        progress_callback(80)
        
        # Validate with ffmpeg
        if not validate_video_file(str(video_path)):
            raise ValueError("Invalid or corrupted video file")
            
        progress_callback(100)
        
    def analyze_video(self, job: JobState, progress_callback):
        """Stage 2: Analyze video"""
        progress_callback(10)
        
        video_info = self.video_chunker.analyze_video(job.video_path)
        
        progress_callback(60)
        
        job.metadata['video_info'] = video_info
        job.metadata['total_chunks'] = video_info['total_chunks']
        self.state_manager.save_job(job)
        
        console.print(f"  Duration: {video_info['duration_str']}")
        console.print(f"  Resolution: {video_info.get('width', 'N/A')}x{video_info.get('height', 'N/A')}")
        console.print(f"  Chunks needed: {video_info['total_chunks']}")
        
        progress_callback(100)
        
    def create_chunks(self, job: JobState, progress_callback):
        """Stage 3: Create video chunks"""
        chunks = self.video_chunker.split_video(
            job.video_path,
            job.job_id,
            progress_callback
        )
        
        job.metadata['chunks'] = chunks
        job.metadata['chunks_created'] = len(chunks)
        self.state_manager.save_job(job)
        
        console.print(f"  Created {len(chunks)} chunks")
        
    def connect_gcs(self, job: JobState, progress_callback):
        """Stage 4: Connect to GCS"""
        progress_callback(20)
        
        try:
            self.gcs_handler.initialize()
            progress_callback(50)
            
            bucket_name = self.gcs_handler.create_job_bucket(job.job_id)
            job.metadata['bucket_name'] = bucket_name
            self.state_manager.save_job(job)
            
            console.print(f"  Bucket: {bucket_name}")
            progress_callback(100)
            
        except Exception as e:
            self._handle_gcs_error(e)
            raise
            
    def upload_chunks(self, job: JobState, progress_callback):
        """Stage 5: Upload chunks to GCS"""
        chunks = job.metadata['chunks']
        bucket_name = job.metadata['bucket_name']
        
        uploaded = self.gcs_handler.upload_chunks(
            chunks,
            bucket_name,
            progress_callback
        )
        
        job.metadata['uploaded_chunks'] = uploaded
        job.metadata['chunks_uploaded'] = len(uploaded)
        self.state_manager.save_job(job)
        
        console.print(f"  Uploaded {len(uploaded)} chunks to GCS")
        
    def initialize_ai(self, job: JobState, progress_callback):
        """Stage 6: Initialize Vertex AI"""
        progress_callback(30)
        
        try:
            self.ai_generator.initialize()
            progress_callback(100)
            console.print(f"  Model: {self.config.get('vertex_ai.default_model')}")
        except Exception as e:
            self._handle_ai_error(e)
            raise
            
    def generate_subtitles(self, job: JobState, progress_callback):
        """Stage 7: Generate subtitles"""
        chunks = job.metadata['uploaded_chunks']
        languages = job.languages
        bucket_name = job.metadata['bucket_name']
        
        # Pass job metadata to AI generator
        self.ai_generator.config.config['current_job'] = {
            'enable_sdh': job.enable_sdh,
            'video_name': job.video_name
        }
        
        console.print(f"  Generating subtitles for {len(languages)} languages...")
        
        subtitles = self.ai_generator.generate_subtitles(
            chunks,
            languages,
            bucket_name,
            progress_callback
        )
        
        job.metadata['generated_subtitles'] = subtitles
        job.metadata['subtitles_generated'] = len(subtitles)
        self.state_manager.save_job(job)
        
        console.print(f"  Generated {len(subtitles)} subtitle files")
        
    def download_subtitles(self, job: JobState, progress_callback):
        """Stage 8: Download subtitles from GCS"""
        subtitles = job.metadata.get('generated_subtitles', [])
        bucket_name = job.metadata['bucket_name']
        
        if not subtitles:
            raise RuntimeError("No subtitles found to download")
            
        local_subtitles = self.gcs_handler.download_subtitles(
            subtitles,
            bucket_name,
            job.job_id,
            progress_callback
        )
        
        if not local_subtitles:
            raise RuntimeError("Failed to download any subtitles")
            
        job.metadata['local_subtitles'] = local_subtitles
        job.metadata['subtitles_downloaded'] = len(local_subtitles)
        self.state_manager.save_job(job)
        
        console.print(f"  Downloaded {len(local_subtitles)} subtitle files")
        
    def merge_subtitles(self, job: JobState, progress_callback):
        """Stage 9: Merge subtitle chunks"""
        local_subtitles = job.metadata.get('local_subtitles', [])
        
        if not local_subtitles:
            raise RuntimeError("No local subtitles found to merge")
            
        merged_files = self.subtitle_merger.merge_subtitles(
            local_subtitles,
            job.job_id,
            job.video_path,
            progress_callback
        )
        
        if not merged_files:
            raise RuntimeError("Failed to create any output files")
            
        job.metadata['merged_files'] = merged_files
        job.output_dir = str(Path(self.config.get('app.output_dir', 'output')) / job.video_name)
        self.state_manager.save_job(job)
        
        console.print(f"  Created {len(merged_files)} output files")
        
    def finalize_output(self, job: JobState, progress_callback):
        """Stage 10: Finalize output and cleanup"""
        progress_callback(20)
        
        # Verify output files
        output_dir = Path(job.output_dir)
        if not output_dir.exists():
            raise RuntimeError(f"Output directory not found: {output_dir}")
            
        output_files = list(output_dir.glob("*.srt")) + list(output_dir.glob("*.vtt"))
        if not output_files:
            raise RuntimeError("No output files found")
            
        progress_callback(50)
        
        # Clean up temporary files
        if not self.config.get('processing.keep_temp_files', False):
            self._cleanup_temp_files(job)
            
        progress_callback(80)
        
        # Clean up GCS if configured
        if not self.config.get('processing.keep_gcs_data', False):
            try:
                self.gcs_handler.cleanup_job_data(
                    job.metadata['bucket_name'],
                    job.metadata.get('uploaded_chunks', [])
                )
            except:
                pass  # Don't fail if cleanup fails
                
        job.metadata['output_files'] = [str(f) for f in output_files]
        self.state_manager.save_job(job)
        
        progress_callback(100)
        
    def _cleanup_temp_files(self, job: JobState):
        """Clean up temporary files"""
        # Clean up chunks
        chunks_dir = Path(self.config.get('app.temp_dir', 'temp')) / job.job_id
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir, ignore_errors=True)
            
        # Clean up temporary subtitles
        temp_subs_dir = Path(self.config.get('app.temp_dir', 'temp')) / job.job_id / 'subtitles'
        if temp_subs_dir.exists():
            shutil.rmtree(temp_subs_dir, ignore_errors=True)
            
    def _handle_gcs_error(self, error: Exception):
        """Handle GCS-specific errors with helpful messages"""
        error_str = str(error).lower()
        
        if "service account file not found" in error_str:
            console.print("\n[red]⚠️  Service Account Authentication Failed[/red]")
            console.print("[yellow]Please ensure your service account JSON file exists at the configured path[/yellow]")
            console.print("[yellow]Check config/config.yaml for the 'service_account_path' setting[/yellow]")
        elif "storage.buckets.create" in error_str:
            console.print("\n[red]⚠️  Permission Error[/red]")
            console.print("[yellow]Your service account lacks the required permissions[/yellow]")
            console.print("[yellow]Grant 'Storage Admin' role to your service account[/yellow]")
        elif "could not automatically determine credentials" in error_str:
            console.print("\n[red]⚠️  No Credentials Found[/red]")
            console.print("[yellow]Run: gcloud auth application-default login[/yellow]")
            
    def _handle_ai_error(self, error: Exception):
        """Handle AI-specific errors with helpful messages"""
        error_str = str(error).lower()
        
        if "quota" in error_str:
            console.print("\n[red]⚠️  Vertex AI Quota Exceeded[/red]")
            console.print("[yellow]Check your quota in GCP Console[/yellow]")
            console.print("[yellow]Consider reducing parallel workers in config[/yellow]")
        elif "permission" in error_str:
            console.print("\n[red]⚠️  Vertex AI Permission Error[/red]")
            console.print("[yellow]Grant 'Vertex AI User' role to your service account[/yellow]")
            
    def handle_error(self, job: JobState, stage: ProcessingStage, error: str) -> bool:
        """Handle errors during processing"""
        console.print(Panel(
            f"[red]❌ ERROR OCCURRED[/red]\n\n" +
            f"Stage: {stage.name}\n" +
            f"Error: {error}",
            style="red"
        ))
        
        table = Table(show_header=False, box=None)
        table.add_row("[bold]1[/bold]", "Retry this stage")
        table.add_row("[bold]2[/bold]", "Skip this stage (not recommended)")
        table.add_row("[bold]3[/bold]", "Save progress and exit")
        table.add_row("[bold]4[/bold]", "Abort job")
        
        console.print("\n[bold]How would you like to proceed?[/bold]")
        console.print(table)
        
        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4"], default="1")
        
        if choice == "1":
            console.print("[yellow]Retrying stage...[/yellow]")
            job.error = None
            return True
        elif choice == "2":
            console.print("[yellow]⚠️  Skipping stage (may cause issues)[/yellow]")
            return True
        elif choice == "3":
            console.print(f"\n[green]Progress saved![/green]")
            console.print(f"Resume with: ./subtitle-gen --resume {job.job_id}")
            return False
        else:
            job.current_stage = ProcessingStage.FAILED
            self.state_manager.save_job(job)
            console.print("[red]Job aborted[/red]")
            return False
            
    def batch_process_videos(self):
        """Process multiple videos in batch"""
        batch_dir = Prompt.ask("\nEnter directory path containing videos", default="input")
        
        if not os.path.exists(batch_dir):
            console.print(f"[red]Directory not found: {batch_dir}[/red]")
            return
            
        # Find all video files
        video_files = []
        for ext in self.config.get('system.supported_video_formats', []):
            video_files.extend(Path(batch_dir).glob(f"*.{ext}"))
            video_files.extend(Path(batch_dir).glob(f"*.{ext.upper()}"))
            
        if not video_files:
            console.print(f"[yellow]No video files found in {batch_dir}[/yellow]")
            return
            
        console.print(f"\n[green]Found {len(video_files)} video files:[/green]")
        for vf in video_files[:5]:  # Show first 5
            console.print(f"  • {vf.name}")
        if len(video_files) > 5:
            console.print(f"  ... and {len(video_files) - 5} more")
            
        # Language selection (same for all videos)
        console.print("\n[cyan]Select languages for all videos:[/cyan]")
        selected_languages, enable_sdh = self.language_selector.select_languages()
        
        if not Confirm.ask(f"\nProcess {len(video_files)} videos?", default=True):
            return
            
        # Process each video
        successful = 0
        failed = 0
        
        for i, video_path in enumerate(video_files, 1):
            console.print(f"\n{'='*60}")
            console.print(f"[cyan]Processing video {i}/{len(video_files)}: {video_path.name}[/cyan]")
            console.print(f"{'='*60}")
            
            try:
                job = self.state_manager.create_job(
                    video_path=str(video_path),
                    languages=selected_languages,
                    enable_sdh=enable_sdh
                )
                
                self.process_job(job)
                successful += 1
                
            except Exception as e:
                console.print(f"[red]Failed to process {video_path.name}: {str(e)}[/red]")
                failed += 1
                
                if not Confirm.ask("Continue with next video?", default=True):
                    break
                    
        # Summary
        console.print(Panel(
            f"[bold]BATCH PROCESSING COMPLETE[/bold]\n\n" +
            f"✅ Successful: {successful}\n" +
            f"❌ Failed: {failed}\n" +
            f"📁 Total: {len(video_files)}",
            style="blue"
        ))
        
    def resume_job(self):
        """Resume a previous job"""
        jobs = self.state_manager.list_jobs()
        
        # Filter incomplete jobs
        incomplete_jobs = [j for j in jobs if j.current_stage != ProcessingStage.COMPLETED]
        
        if not incomplete_jobs:
            console.print("[yellow]No incomplete jobs found[/yellow]")
            return
            
        # Display jobs table
        table = Table(title="Incomplete Jobs")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Job ID", style="cyan")
        table.add_column("Video", style="magenta")
        table.add_column("Stage", style="yellow")
        table.add_column("Created", style="green")
        
        for i, job in enumerate(incomplete_jobs, 1):
            stage_name = job.metadata.get('current_stage_name', job.current_stage.name)
            created_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(job.created_at))
            
            table.add_row(
                str(i),
                job.job_id[:12] + "...",
                Path(job.video_path).name[:30],
                stage_name,
                created_time
            )
            
        console.print(table)
        
        # Select job
        choice = Prompt.ask("\nSelect job number to resume (0 to cancel)")
        
        if choice == "0":
            return
            
        try:
            job_index = int(choice) - 1
            if 0 <= job_index < len(incomplete_jobs):
                job = incomplete_jobs[job_index]
                console.print(f"\n[green]Resuming job: {job.job_id}[/green]")
                self.process_job(job)
            else:
                console.print("[red]Invalid selection[/red]")
        except ValueError:
            console.print("[red]Invalid input[/red]")
            
    def view_job_history(self):
        """View job history"""
        jobs = self.state_manager.list_jobs()
        
        if not jobs:
            console.print("[yellow]No jobs found[/yellow]")
            return
            
        # Display jobs table
        table = Table(title="Job History")
        table.add_column("Job ID", style="cyan")
        table.add_column("Video", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Languages", style="blue")
        table.add_column("Created", style="green")
        table.add_column("Duration", style="white")
        
        for job in jobs[:20]:  # Show last 20 jobs
            # Status
            if job.current_stage == ProcessingStage.COMPLETED:
                status = "[green]Completed[/green]"
            elif job.current_stage == ProcessingStage.FAILED:
                status = "[red]Failed[/red]"
            else:
                status = "[yellow]In Progress[/yellow]"
                
            # Duration
            if job.completed_at:
                duration = int(job.completed_at - job.created_at)
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}m {seconds}s"
            else:
                duration_str = "-"
                
            # Languages
            langs = ", ".join([l.upper() for l in job.languages])
            
            table.add_row(
                job.job_id[:12] + "...",
                Path(job.video_path).name[:25],
                status,
                langs,
                time.strftime("%Y-%m-%d %H:%M", time.localtime(job.created_at)),
                duration_str
            )
            
        console.print(table)
        
        if len(jobs) > 20:
            console.print(f"\n[dim]Showing latest 20 jobs out of {len(jobs)} total[/dim]")
            
@click.command()
@click.option('--video', '-v', help='Process a single video file')
@click.option('--batch', '-b', help='Process all videos in a directory')
@click.option('--resume', '-r', help='Resume a previous job by ID')
@click.option('--languages', '-l', help='Comma-separated language codes (eng,hin,ben)')
@click.option('--sdh', is_flag=True, help='Generate SDH subtitles')
@click.option('--output', '-o', help='Custom output directory')
def main(video, batch, resume, languages, sdh, output):
    """Video Subtitle Generator - Generate multi-language subtitles using AI"""
    
    processor = SubtitleProcessor()
    
    # Override output directory if specified
    if output:
        processor.config.config['app']['output_dir'] = output
        ensure_directory_exists(output)
    
    try:
        if video:
            # Direct video processing
            processor.process_single_video(video)
            
        elif batch:
            # Batch processing
            processor.batch_process_videos()
            
        elif resume:
            # Resume specific job
            job = processor.state_manager.load_job(resume)
            if job:
                console.print(f"[green]Resuming job: {job.job_id}[/green]")
                processor.process_job(job)
            else:
                console.print(f"[red]Job not found: {resume}[/red]")
                
        else:
            # Interactive mode
            while True:
                try:
                    processor.main_menu()
                except KeyboardInterrupt:
                    console.print("\n[yellow]Operation cancelled[/yellow]")
                    if Confirm.ask("Return to main menu?", default=True):
                        continue
                    else:
                        break
                except Exception as e:
                    console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
                    if Confirm.ask("Continue?", default=True):
                        continue
                    else:
                        break
                        
    except KeyboardInterrupt:
        console.print("\n[yellow]Application terminated by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {str(e)}[/red]")
        import traceback
        if console.is_terminal:
            traceback.print_exc()
        sys.exit(1)
        
if __name__ == "__main__":
    main()
