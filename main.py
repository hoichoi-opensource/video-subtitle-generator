#!/usr/bin/env python3
"""
Video Subtitle Generation System
Production-ready application with interactive UI
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from datetime import datetime
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.config import Config
from src.video_processor import VideoProcessor
from src.subtitle_generator import SubtitleGenerator
from src.utils import setup_logging, validate_input_file, format_time, get_file_size

console = Console()

class SubtitleApp:
    def __init__(self, config_path="config.yaml"):
        """Initialize the subtitle generation application."""
        self.config = Config(config_path)
        self.logger = setup_logging(self.config)
        self.video_processor = VideoProcessor(self.config)
        self.subtitle_generator = SubtitleGenerator(self.config)
        
    def display_welcome(self):
        """Display welcome message and application info."""
        console.clear()
        welcome_text = """
[bold cyan]Video Subtitle Generator[/bold cyan]
[dim]Automated subtitle generation and translation system[/dim]

Features:
• Automatic video chunking
• AI-powered subtitle generation
• Multi-language translation (English, Hindi, Bengali)
• Multiple output formats (SRT, VTT)
• Progress tracking and error handling
        """
        console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))
        
    def get_user_input(self):
        """Interactive prompts to get user input."""
        console.print("\n[bold yellow]Let's get started![/bold yellow]\n")
        
        # Get video file path
        while True:
            video_path = Prompt.ask(
                "[cyan]Enter the path to your video file[/cyan]",
                default="",
            )
            
            if not video_path:
                console.print("[red]Please provide a valid file path[/red]")
                continue
                
            video_path = Path(video_path).expanduser().resolve()
            
            if validate_input_file(video_path):
                break
            else:
                console.print(f"[red]File not found or invalid: {video_path}[/red]")
                if not Confirm.ask("Try another file?", default=True):
                    return None
        
        # Get language preferences
        console.print("\n[bold]Language Settings[/bold]")
        
        source_lang = Prompt.ask(
            "Source language (leave empty for auto-detection)",
            default=self.config.get('subtitles.source_language', 'auto')
        )
        
        target_lang = Prompt.ask(
            "Target language for translation",
            default=self.config.get('subtitles.target_language', 'en'),
            choices=['en', 'hi', 'bn']  # Only English, Hindi, Bengali
        )
        
        # If Hindi is selected, ask for translation method
        hindi_method = None
        if target_lang == 'hi':
            hindi_method = Prompt.ask(
                "Hindi translation method",
                default=self.config.get('subtitles.hindi_translation_method', 'direct'),
                choices=['direct', 'via_english']
            )
            # Update config temporarily
            self.config._config['subtitles']['hindi_translation_method'] = hindi_method
        
        # Get output preferences
        console.print("\n[bold]Output Settings[/bold]")
        
        formats = Prompt.ask(
            "Subtitle formats (comma-separated)",
            default=",".join(self.config.get('subtitles.formats', ['srt', 'vtt']))
        ).split(',')
        formats = [f.strip().lower() for f in formats]
        
        burn_subtitles = Confirm.ask(
            "Burn subtitles into video?",
            default=self.config.get('subtitles.burn_subtitles', False)
        )
        
        # Output directory
        output_dir = Prompt.ask(
            "Output directory",
            default=str(Path.home() / "Downloads" / "subtitled_videos")
        )
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            'video_path': video_path,
            'source_language': source_lang,
            'target_language': target_lang,
            'formats': formats,
            'burn_subtitles': burn_subtitles,
            'output_dir': output_dir
        }
    
    def display_summary(self, settings):
        """Display processing summary before starting."""
        table = Table(title="Processing Summary", show_header=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Video File", str(settings['video_path'].name))
        table.add_row("File Size", get_file_size(settings['video_path']))
        table.add_row("Source Language", settings['source_language'])
        table.add_row("Target Language", settings['target_language'])
        table.add_row("Output Formats", ", ".join(settings['formats']))
        table.add_row("Burn Subtitles", "Yes" if settings['burn_subtitles'] else "No")
        table.add_row("Output Directory", str(settings['output_dir']))
        
        console.print("\n", table, "\n")
        
    def process_video(self, settings):
        """Main processing workflow."""
        start_time = datetime.now()
        
        try:
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
            
            # Clean up temporary files
            if self.config.get('processing.cleanup_temp_files', True):
                self.video_processor.cleanup_chunks(chunks)
            
            # Display results
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self.display_results(output_files, processing_time)
            
            return True
            
        except Exception as e:
            console.print(f"\n[red]Error during processing: {str(e)}[/red]")
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
            return False
    
    def display_results(self, output_files, processing_time):
        """Display processing results."""
        console.print("\n[bold green]Processing Complete![/bold green]\n")
        
        table = Table(title="Output Files", show_header=True)
        table.add_column("File Type", style="cyan")
        table.add_column("Path", style="green")
        table.add_column("Size", style="yellow")
        
        for file_path in output_files:
            file_type = file_path.suffix.upper()[1:]
            if file_path.suffix in ['.mp4', '.avi', '.mov']:
                file_type = "Video"
            table.add_row(file_type, str(file_path), get_file_size(file_path))
        
        console.print(table)
        console.print(f"\n[dim]Total processing time: {format_time(processing_time)}[/dim]")
        
        # Download instructions
        console.print("\n[bold yellow]Your files are ready![/bold yellow]")
        console.print(f"Files saved to: [cyan]{output_files[0].parent}[/cyan]")
        
        # Open folder option
        if Confirm.ask("\nOpen output folder?", default=True):
            import subprocess
            import platform
            
            folder = str(output_files[0].parent)
            if platform.system() == 'Windows':
                os.startfile(folder)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', folder])
            else:  # Linux
                subprocess.Popen(['xdg-open', folder])

@click.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--video', '-v', help='Direct path to video file (skip interactive mode)')
@click.option('--lang', '-l', help='Target language: en, hi, bn')
@click.option('--method', '-m', default='direct', help='Hindi translation method: direct or via_english')
def main(config, video, lang, method):
    """Video Subtitle Generator - Production Ready Application
    
    Supports English (en), Hindi (hi), and Bengali (bn) subtitles.
    For Hindi, two methods available: direct translation or via English.
    """
    try:
        app = SubtitleApp(config)
        
        if video:
            # Non-interactive mode
            if not lang:
                console.print("[red]Error: --lang option required in non-interactive mode[/red]")
                console.print("Use: --lang en|hi|bn")
                return
                
            settings = {
                'video_path': Path(video),
                'source_language': app.config.get('subtitles.source_language', 'auto'),
                'target_language': lang,
                'formats': app.config.get('subtitles.formats', ['srt', 'vtt']),
                'burn_subtitles': app.config.get('subtitles.burn_subtitles', False),
                'output_dir': Path.home() / "Downloads" / "subtitled_videos"
            }
            
            # Set Hindi method if applicable
            if lang == 'hi':
                app.config._config['subtitles']['hindi_translation_method'] = method
        else:
            # Interactive mode
            app.display_welcome()
            settings = app.get_user_input()
            
            if not settings:
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                return
            
            app.display_summary(settings)
            
            if not Confirm.ask("\nProceed with these settings?", default=True):
                console.print("\n[yellow]Operation cancelled.[/yellow]")
                return
        
        console.print("\n[bold]Starting processing...[/bold]\n")
        
        success = app.process_video(settings)
        
        if success:
            console.print("\n[bold green]✨ All done! Enjoy your subtitled video! ✨[/bold green]")
        else:
            console.print("\n[bold red]Processing failed. Check the logs for details.[/bold red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {str(e)}[/red]")
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
