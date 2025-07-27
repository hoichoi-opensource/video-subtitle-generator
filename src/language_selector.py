"""
Language Selector
Handles language selection for subtitle generation
"""

from typing import List, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from .config_manager import ConfigManager

console = Console()

class LanguageSelector:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.available_languages = config.get_available_languages()
        
    def select_languages(self) -> Tuple[List[str], bool]:
        """Interactive language selection"""
        console.print("\n[bold cyan]Select Subtitle Languages[/bold cyan]")
        
        # Display available languages
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Code", style="cyan", width=6)
        table.add_column("Language", style="white")
        table.add_column("Method", style="yellow")
        table.add_column("Default", style="green")
        
        for lang_code, lang_info in self.available_languages.items():
            method = lang_info.get('method', 'direct')
            if lang_code == 'hin':
                method = 'dual (translation + direct)'
            
            default = "✓" if lang_info.get('default', False) else ""
            
            table.add_row(
                lang_code,
                lang_info['name'],
                method,
                default
            )
            
        console.print(table)
        
        # Get default languages
        default_langs = [code for code, info in self.available_languages.items() 
                        if info.get('default', False)]
        
        # Prompt for language selection
        console.print("\n[yellow]Enter language codes separated by commas[/yellow]")
        console.print(f"[dim]Default: {', '.join(default_langs)}[/dim]")
        
        selected = Prompt.ask(
            "Languages",
            default=",".join(default_langs)
        )
        
        # Parse selection
        selected_langs = [lang.strip().lower() for lang in selected.split(',')]
        
        # Validate selection
        valid_langs = []
        for lang in selected_langs:
            if lang in self.available_languages:
                valid_langs.append(lang)
            else:
                console.print(f"[red]Warning: Unknown language code '{lang}' - skipping[/red]")
                
        if not valid_langs:
            console.print("[yellow]No valid languages selected, using defaults[/yellow]")
            valid_langs = default_langs
            
        # Ask about SDH
        enable_sdh = Confirm.ask(
            "\n[cyan]Generate SDH subtitles?[/cyan] (includes sound effects, music descriptions)",
            default=False
        )
        
        # Display summary
        console.print("\n[green]Selected languages:[/green]")
        for lang in valid_langs:
            lang_name = self.available_languages[lang]['name']
            console.print(f"  • {lang_name} ({lang})")
            
        if enable_sdh:
            console.print("\n[green]SDH subtitles will be generated[/green]")
            
        return valid_langs, enable_sdh
        
    def get_language_name(self, code: str) -> str:
        """Get language name from code"""
        return self.available_languages.get(code, {}).get('name', code.upper())
