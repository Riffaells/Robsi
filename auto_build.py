#!/usr/bin/env python3
"""
Robsidian Theme Auto-Builder
Tracks changes in the styles/ directory and automatically rebuilds the theme.
"""

import os
import sys
import time
import shutil
import argparse
from pathlib import Path
from typing import Optional, List
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    from rich.console import Console
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📦 Please install dependencies: pip install watchdog rich")
    sys.exit(1)

console = Console()

class ThemeBuilder:
    def __init__(self, target_dir: Optional[str] = None):
        self.target_dir = target_dir
        self.build_count = 0
        self.styles_dir = Path("styles")

    def find_css_files(self) -> List[Path]:
        """Finds all CSS files and sorts them into the correct build order."""
        if not self.styles_dir.exists():
            console.print(f"[red]❌ Directory {self.styles_dir} not found!")
            return []

        css_files = list(self.styles_dir.rglob("*.css"))

        def get_priority(file_path: Path) -> tuple:
            relative_path = file_path.relative_to(self.styles_dir)
            path_str = str(relative_path).lower()

            if relative_path.name == "variables.css": return (0, path_str)
            if relative_path.name == "base.css": return (1, path_str)
            if "components" in relative_path.parts: return (2, path_str)
            if "plugins" in relative_path.parts: return (3, path_str)
            if "utilities" in relative_path.parts: return (4, path_str)
            if "themes" in relative_path.parts: return (5, path_str)
            if relative_path.name == "settings.css": return (6, path_str)
            return (7, path_str)

        css_files.sort(key=get_priority)
        return css_files

    def build_theme(self) -> bool:
        """Builds the theme from the found CSS files."""
        try:
            console.print("🔨 Building theme...", end=" ")
            css_files = self.find_css_files()

            if not css_files:
                console.print("[red]❌ CSS files not found!")
                return False

            header = f"""/*
Robsi Theme - A modern theme for Obsidian.
By Riffaells - {datetime.now().year}
Built: {datetime.now().isoformat()}
Files included: {len(css_files)}
*/\n\n"""

            with Path("theme.css").open("w", encoding="utf-8") as theme_file:
                theme_file.write(header)
                for i, css_file in enumerate(css_files):
                    try:
                        relative_path = css_file.relative_to(self.styles_dir)
                        content = css_file.read_text(encoding='utf-8')

                        if i > 0:
                            theme_file.write('\n/* ================================================= */\n\n')

                        theme_file.write(f"/* {relative_path} */\n")
                        theme_file.write(content + '\n')
                    except Exception as e:
                        console.print(f"[red]❌ Error reading {css_file}: {e}")
                        return False

            self.build_count += 1
            size = Path("theme.css").stat().st_size / 1024
            timestamp = time.strftime("%H:%M:%S")
            console.print(f"[green]✅ Done ({size:.1f} KB) - {timestamp} [{len(css_files)} files]")

            if self.target_dir:
                self._move_theme_file()

            return True

        except Exception as e:
            console.print(f"[red]❌ Build error: {e}")
            return False

    def _move_theme_file(self):
        """Moves the built theme file to the target directory."""
        try:
            target_path = Path(self.target_dir) / "theme.css"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2("theme.css", target_path)
            console.print(f"📁 Copied to: [cyan]{target_path}")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not copy: {e}")

    def list_files(self):
        """Displays a list of found CSS files in build order."""
        css_files = self.find_css_files()
        console.print(f"\n📋 [bold]Found CSS files: {len(css_files)}[/bold]")
        console.print("   Build order:")
        for i, css_file in enumerate(css_files, 1):
            relative_path = css_file.relative_to(self.styles_dir)
            size = css_file.stat().st_size
            console.print(f"  {i:2d}. [cyan]{relative_path}[/cyan] ({size} bytes)")

class ThemeWatcher(FileSystemEventHandler):
    def __init__(self, builder: ThemeBuilder):
        self.builder = builder
        self.last_build = 0
        self.debounce_time = 1.0

    def on_any_event(self, event):
        if event.is_directory or not event.src_path.endswith('.css') or 'theme.css' in event.src_path:
            return

        current_time = time.time()
        if current_time - self.last_build > self.debounce_time:
            self.last_build = current_time
            file_name = os.path.basename(event.src_path)

            event_colors = {
                "modified": "yellow",
                "created": "green",
                "deleted": "red"
            }
            color = event_colors.get(event.event_type, "white")
            console.print(f"\n📝 Event: [{color}]{event.event_type} - {file_name}[/{color}]")
            self.builder.build_theme()

def main():
    parser = argparse.ArgumentParser(description="Robsidian Theme Auto-Builder")
    parser.add_argument("-t", "--target", help="Target directory for theme.css", type=str)
    parser.add_argument("-l", "--list", help="List found CSS files and exit", action="store_true")
    parser.add_argument("--once", help="Build once and exit (no watching)", action="store_true")
    args = parser.parse_args()

    if not Path("styles").exists():
        console.print("[red]❌ styles/ directory not found!")
        sys.exit(1)

    builder = ThemeBuilder(args.target)

    if args.list:
        builder.list_files()
        return

    console.print("🎨 [bold]Robsi Theme Auto-Builder[/bold]")

    if args.once:
        console.print("🔨 Building once...")
        if args.target:
            console.print(f"📂 Target directory: [cyan]{args.target}")
        console.print()
        success = builder.build_theme()
        if success:
            console.print(f"✅ Build completed successfully!")
        else:
            console.print(f"❌ Build failed!")
            sys.exit(1)
        return

    # Watch mode
    event_handler = ThemeWatcher(builder)
    observer = Observer()
    watching_dir = str(Path("styles").resolve())
    observer.schedule(event_handler, watching_dir, recursive=True)

    console.print(f"👀 Watching: [cyan]{watching_dir}")
    if args.target:
        console.print(f"📂 Target directory: [cyan]{args.target}")

    console.print()
    builder.build_theme()

    observer.start()
    console.print("\n✅ Watching started. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print(f"\n👋 Stopped. Builds performed: [green]{builder.build_count}")

    observer.join()

if __name__ == "__main__":
    main()
