"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Rich Console & Logger
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import sys
import logging
from datetime import datetime

try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

if HAS_RICH:
    custom_theme = Theme({
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "gold": "bold #f1c40f",
        "dim": "dim",
    })
    console = Console(theme=custom_theme)

    class RichConsoleHandler(logging.Handler):
        def emit(self, record):
            try:
                msg = self.format(record)
                color = "info"
                if record.levelno >= logging.ERROR:
                    color = "error"
                elif record.levelno >= logging.WARNING:
                    color = "warning"
                now = datetime.now().strftime("%I:%M:%S %p")
                console.print(f"[{color}][{now}] {msg}[/{color}]")
            except Exception:
                self.handleError(record)
else:
    class DummyConsole:
        def print(self, *args, **kwargs):
            clean_args = [str(a) for a in args]
            print(" ".join(clean_args))
    console = DummyConsole()

    class RichConsoleHandler(logging.StreamHandler):
        pass

def get_logger(name: str = "mwvse") -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(logging.INFO)
        handler = RichConsoleHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        log.addHandler(handler)
    return log

logger = get_logger("mwvse")

def print_banner():
    if HAS_RICH:
        banner_text = Text()
        banner_text.append("⚡ MWVSE TRADING PANEL\n", style="bold cyan")
        banner_text.append("Algorithmic Day Trader & Leaderboard Copy Engine\n", style="bold white")
        banner_text.append("Built with precision by @ghostwwn (https://github.com/ghostwwn)\n\n", style="bold green")
        banner_text.append("DISCLAIMER: Independent tool. NOT affiliated with or endorsed by\n", style="dim yellow")
        banner_text.append("MarketWatch, Dow Jones & Company, Inc. Provided AS-IS for education.", style="dim yellow")

        console.print(Panel(
            banner_text,
            border_style="cyan",
            title="[bold yellow]v2.5.0[/bold yellow]",
            subtitle="[dim]MIT License[/dim]",
            padding=(1, 2)
        ))
    else:
        print("=" * 65)
        print("⚡ MWVSE TRADING PANEL v2.5.0 — Engineered by @ghostwwn")
        print("Independent tool. NOT affiliated with MarketWatch or Dow Jones.")
        print("=" * 65)
