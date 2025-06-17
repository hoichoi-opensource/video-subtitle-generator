# Updated process_video method in main.py

def process_video(self, settings):
    """Main processing workflow."""
    start_time = datetime.now()
    
    try:
        # Set up GCS job folder for this video
        self.subtitle_generator.set_job_prefix(settings['video_path'])
        
        # Phase 1: Video Analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Analyzing video...", total=None)
            video_info = self.video_processor.analyze_video(settings['video_path'])
            progress.update(task, completed=True)
        
        console.print(f"[green]✓[/green] Video analyzed: {format_time(video_info['duration'])} duration")
        
        # Phase 2: Chunking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Splitting video into chunks...", total=100)
            chunks = self.video_processor.create_chunks(
                settings['video_path'],
                progress_callback=lambda p: progress.update(task, completed=p)
            )
        
        console.print(f"[green]✓[/green] Created {len(chunks)} chunks")
        
        # Phase 3: Subtitle Generation
        console.print("\n[bold]Generating subtitles...[/bold]")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(
                "[cyan]Processing chunks...", 
                total=len(chunks)
            )
            
            subtitles = self.subtitle_generator.process_chunks(
                chunks,
                source_lang=settings['source_language'],
                target_lang=settings['target_language'],
                progress_callback=lambda: progress.advance(task)
            )
        
        console.print(f"[green]✓[/green] Generated subtitles for all chunks")
        
        # Phase 4: Merging and Output
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Merging subtitles...", total=None)
            
            # Merge subtitles
            merged_subtitles = self.subtitle_generator.merge_subtitles(subtitles)
            
            # Save subtitle files
            output_files = []
            for format in settings['formats']:
                output_path = settings['output_dir'] / f"{settings['video_path'].stem}_subtitles.{format}"
                self.subtitle_generator.save_subtitles(merged_subtitles, output_path, format)
                output_files.append(output_path)
            
            progress.update(task, completed=True)
        
        console.print(f"[green]✓[/green] Saved subtitle files")
        
        # Phase 5: Video Processing (if burn_subtitles is True)
        if settings['burn_subtitles']:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("[cyan]Creating subtitled video...", total=100)
                
                output_video = settings['output_dir'] / f"{settings['video_path'].stem}_subtitled.mp4"
                self.video_processor.burn_subtitles(
                    settings['video_path'],
                    output_files[0],  # Use first subtitle file
                    output_video,
                    progress_callback=lambda p: progress.update(task, completed=p)
                )
                output_files.append(output_video)
            
            console.print(f"[green]✓[/green] Created subtitled video")
        
        # Clean up local temporary files
        if self.config.get('processing.cleanup_temp_files', True):
            self.video_processor.cleanup_chunks(chunks)
        
        # Mark job as complete in GCS and cleanup chunks
        # The cleanup_chunks parameter determines if GCS chunks should be deleted
        cleanup_gcs = self.config.get('processing.cleanup_gcs_chunks', True)
        self.subtitle_generator.complete_job(cleanup_chunks=cleanup_gcs)
        
        # Display results
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        self.display_results(output_files, processing_time)
        
        # Display GCS information if available
        if self.subtitle_generator.bucket and self.subtitle_generator.current_job_prefix:
            console.print(f"\n[cyan]GCS Job Folder:[/cyan] {self.subtitle_generator.current_job_prefix}")
            console.print(f"[dim]View in Console: https://console.cloud.google.com/storage/browser/{self.subtitle_generator.bucket_name}/{self.subtitle_generator.current_job_prefix}[/dim]")
            if cleanup_gcs:
                console.print(f"[dim]Note: Video chunks have been deleted from GCS to save storage.[/dim]")
        
        return True
        
    except Exception as e:
        console.print(f"\n[red]Error during processing: {str(e)}[/red]")
        self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
        return False