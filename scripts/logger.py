"""Logging configuration and utilities."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from colorama import init, Fore, Back, Style

# Initialize colorama for Windows support
init(autoreset=True)

# Rich console instance
console = Console()

# Color scheme
class Colors:
    """Terminal color definitions."""
    SUCCESS = Fore.GREEN
    INFO = Fore.BLUE
    WARNING = Fore.YELLOW
    ERROR = Fore.RED
    STAGE = Fore.MAGENTA
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT


def setup_logging(name: str, log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """Set up logging configuration."""
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with Rich
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True
    )
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = log_dir_path / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def create_stage_display():
    """Create the stage display progress tracker."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False
    )


def print_banner():
    """Print the application banner."""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║           VIDEO SUBTITLE GENERATION SYSTEM                 ║
    ║                                                            ║
    ║          Powered by Vertex AI & Google Cloud               ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_stage_header(video_name: str, language: str, job_id: str):
    """Print the stage header information."""
    table = Table(show_header=False, box=None)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    
    table.add_row("📹 Video:", video_name)
    table.add_row("🌐 Language:", language)
    table.add_row("🆔 Job ID:", job_id)
    
    console.print(Panel(table, title="Processing Information", border_style="blue"))


def log_stage(stage_num: int, total_stages: int, stage_name: str, status: str = "PENDING"):
    """Log a stage update."""
    status_symbols = {
        "PENDING": "⏳",
        "IN_PROGRESS": "🔄",
        "COMPLETED": "✅",
        "FAILED": "❌",
        "WARNING": "⚠️",
        "RETRYING": "🔁",
        "SKIPPED": "⏭️"
    }
    
    status_colors = {
        "PENDING": "gray",
        "IN_PROGRESS": "blue",
        "COMPLETED": "green",
        "FAILED": "red",
        "WARNING": "yellow",
        "RETRYING": "orange",
        "SKIPPED": "white"
    }
    
    symbol = status_symbols.get(status, "❓")
    color = status_colors.get(status, "white")
    
    console.print(
        f"{symbol} Stage {stage_num}/{total_stages}: {stage_name} [{status}]",
        style=f"bold {color}"
    )