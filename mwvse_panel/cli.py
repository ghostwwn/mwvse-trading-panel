"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Command-Line Interface
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import argparse
import asyncio
import subprocess
import sys
import uvicorn

from .core.config import settings, APP_DIR
from .core.logger import console, print_banner
from .engine.auth import run_setup_wizard, AuthManager
from .engine.scraper import MarketWatchScraper
from .copier.copy_engine import LeaderCopyEngine
from .ui.tui import run_tui

def cmd_setup(args):
    """Run interactive setup wizard."""
    run_setup_wizard()

def cmd_run(args):
    """Launch the Web Trading Station & Autonomous Engine."""
    print_banner()
    host = args.host or settings.host
    port = args.port or settings.port
    console.print(f"[bold cyan]🌐 Starting Web Trading Station at http://{host}:{port}/[/bold cyan]")
    console.print("[dim]Press Ctrl+C to terminate.[/dim]\n")
    uvicorn.run("mwvse_panel.ui.web.app:app", host=host, port=port, reload=args.reload)

def cmd_terminal(args):
    """Launch the interactive Rich Terminal TUI."""
    print_banner()
    run_tui()

def cmd_copy(args):
    """Launch the standalone Leaderboard Copy-Trading Engine."""
    print_banner()
    engine = LeaderCopyEngine()
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping copy-trader daemon.[/yellow]\n")

def cmd_status(args):
    """Print an instant snapshot of your account net worth, buying power, and active positions."""
    print_banner()
    console.print("[dim]Fetching live account metrics from MarketWatch...[/dim]")
    scraper = MarketWatchScraper()
    snap = asyncio.run(scraper.fetch_portfolio())

    try:
        from rich.table import Table
        tbl = Table(title="💼 Current Account Status", border_style="cyan")
        tbl.add_column("Metric", style="bold white")
        tbl.add_column("Value", style="cyan")

        tbl.add_row("Net Worth", f"${snap.net_worth:,.2f}")
        tbl.add_row("Cash Remaining", f"${snap.cash:,.2f}")
        tbl.add_row("Buying Power", f"${snap.buying_power:,.2f}")
        tbl.add_row("Tournament Standing", f"#{snap.rank} of {snap.total_players}")
        tbl.add_row("Active Positions", str(len(snap.holdings)))
        console.print(tbl)

        if snap.holdings:
            ptbl = Table(title="📊 Open Positions", border_style="green")
            ptbl.add_column("Symbol", style="bold white")
            ptbl.add_column("Type")
            ptbl.add_column("Shares", justify="right")
            ptbl.add_column("Price", justify="right")
            ptbl.add_column("Value", justify="right")
            ptbl.add_column("Gain ($)", justify="right")
            ptbl.add_column("Gain (%)", justify="right")

            for h in snap.holdings:
                pnl_style = "bold green" if h.gain_dollar >= 0 else "bold red"
                sign = "+" if h.gain_dollar >= 0 else ""
                ptbl.add_row(
                    h.symbol,
                    h.pos_type.upper(),
                    str(h.shares),
                    f"${h.price:,.2f}",
                    f"${h.value:,.2f}",
                    f"[{pnl_style}]{sign}${h.gain_dollar:,.2f}[/{pnl_style}]",
                    f"[{pnl_style}]{sign}{h.gain_percent:.2f}%[/{pnl_style}]"
                )
            console.print(ptbl)
    except Exception:
        print(f"Net Worth: ${snap.net_worth:,.2f} | Buying Power: ${snap.buying_power:,.2f} | Rank: #{snap.rank}")

def cmd_doctor(args):
    """Diagnose environment, configuration, and Playwright browser installation."""
    print_banner()
    console.print("[bold cyan]🩺 RUNNING ENVIRONMENT HEALTH CHECK...[/bold cyan]\n")

    # 1. Python version
    py_ver = sys.version.split()[0]
    console.print(f"🐍 Python Version: [bold green]{py_ver}[/bold green] (3.10+ supported)")

    # 2. Config file
    env_file = APP_DIR / ".env"
    if env_file.exists():
        console.print(f"⚙️ Config File: [bold green]Found ({env_file.name})[/bold green]")
        console.print(f"   • Game Slug: [cyan]{settings.mw_game_slug}[/cyan]")
        console.print(f"   • Webhook Secret: [dim]{settings.webhook_secret[:4]}***[/dim]")
    else:
        console.print("⚙️ Config File: [bold yellow]Missing (.env)[/bold yellow] — Run 'python main.py setup' to generate it!")

    # 3. Playwright Chromium check
    console.print("\n🌐 Checking Playwright Chromium...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        console.print("   • Chromium Engine: [bold green]INSTALLED & READY[/bold green]")
    except Exception as e:
        console.print(f"   • Chromium Engine: [bold red]NOT FOUND or ERROR ({e})[/bold red]")
        console.print("   [yellow]Attempting auto-install of Playwright Chromium...[/yellow]")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        console.print("   [bold green]✅ Chromium installed successfully![/bold green]")

    # 4. MarketWatch Authentication Profile
    auth = AuthManager()
    console.print("\n🔐 Checking MarketWatch Authentication Profile...")
    is_auth = asyncio.run(auth.verify_session())
    if is_auth:
        console.print("   • MarketWatch Session: [bold green]AUTHENTICATED & ACTIVE[/bold green]")
    else:
        console.print("   • MarketWatch Session: [bold yellow]NOT LOGGED IN[/bold yellow]")
        console.print("   [dim]Run 'python main.py setup' to attach your MarketWatch account in 1-click.[/dim]")

    console.print("\n[bold green]Health check complete.[/bold green]\n")

def app():
    parser = argparse.ArgumentParser(
        prog="mwvse",
        description="⚡ MWVSE Trading Panel — Algorithmic day trading, position supervisor, and copy-trader. Built by @ghostwwn."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # setup
    p_setup = subparsers.add_parser("setup", help="Run interactive account attachment & setup wizard")
    p_setup.set_defaults(func=cmd_setup)

    # run
    p_run = subparsers.add_parser("run", help="Launch Web Station & autonomous engine")
    p_run.add_argument("--host", default=None, help="Host address (default: 127.0.0.1)")
    p_run.add_argument("--port", type=int, default=None, help="Port (default: 8000)")
    p_run.add_argument("--reload", action="store_true", help="Enable auto-reload")
    p_run.set_defaults(func=cmd_run)

    # terminal
    p_term = subparsers.add_parser("terminal", help="Launch interactive Rich Terminal TUI")
    p_term.set_defaults(func=cmd_terminal)

    # copy
    p_copy = subparsers.add_parser("copy", help="Launch Leaderboard Copy-Trading Engine")
    p_copy.set_defaults(func=cmd_copy)

    # status
    p_stat = subparsers.add_parser("status", help="Print account balance and position snapshot")
    p_stat.set_defaults(func=cmd_status)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run system diagnostics and verify browser installation")
    p_doc.set_defaults(func=cmd_doctor)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    app()
