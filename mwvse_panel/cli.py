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
from .engine.executor import OrderExecutor
from .supervisor.autonomous_engine import AutonomousTradingEngine
from .ui.tui import run_tui
from .ui.mobile_pairing import print_mobile_qr

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

def cmd_mobile(args):
    """Launch Mobile Trading Station accessible from iPhone/Android with QR Code pairing."""
    print_banner()
    port = args.port or settings.port
    print_mobile_qr(port=port)
    console.print("[dim]Starting network listener on 0.0.0.0... Press Ctrl+C to terminate.[/dim]\n")
    uvicorn.run("mwvse_panel.ui.web.app:app", host="0.0.0.0", port=port)

def cmd_terminal(args):
    """Launch the interactive Rich Terminal TUI."""
    print_banner()
    run_tui()

async def auto_loop():
    scraper = MarketWatchScraper()
    executor = OrderExecutor()
    queue = asyncio.Queue()
    auto_engine = AutonomousTradingEngine(queue=queue)

    console.print("[bold green]🤖 Autonomous Algorithmic Engine Active![/bold green]")
    console.print(f"[dim]Strategy: {settings.autopilot_strategy} | Max Positions: {settings.max_concurrent_positions}[/dim]\n")

    async def worker():
        while True:
            order = await queue.get()
            try:
                action = order.action.value if hasattr(order.action, "value") else str(order.action)
                console.print(f"⚡ [AUTO-EXECUTE] Submitting {action.upper()} {order.ticker} to MarketWatch...")
                res = await executor.execute_trade(
                    ticker=order.ticker,
                    action=action,
                    shares=order.shares,
                    dollar_amount=order.dollar_amount,
                    full_port=order.full_port,
                    order_type="Market"
                )
                console.print(f"   [{res.get('status').upper()}] {res.get('message')}")
            except Exception as e:
                console.print(f"   [bold red]Execution error: {e}[/bold red]")
            finally:
                queue.task_done()

    asyncio.create_task(worker())

    while True:
        try:
            snapshot = await scraper.fetch_portfolio()
            await auto_engine.evaluate_exits(snapshot)
            await auto_engine.evaluate_entries(snapshot)
        except Exception as e:
            console.print(f"[yellow]Auto loop cycle warning: {e}[/yellow]")
        await asyncio.sleep(settings.autopilot_scan_interval)

def cmd_auto(args):
    """Launch the standalone Autonomous Trading Engine."""
    print_banner()
    try:
        asyncio.run(auto_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping autonomous trading engine.[/yellow]\n")

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
        console.print(f"   • Strategy Preset: [bold green]{settings.autopilot_strategy}[/bold green]")
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
        description="⚡ MWVSE Trading Panel — Algorithmic day trading, autonomous execution, and risk supervisor. Built by @ghostwwn."
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

    # mobile
    p_mob = subparsers.add_parser("mobile", help="Launch Mobile Web Station on Wi-Fi with QR code pairing")
    p_mob.add_argument("--port", type=int, default=None, help="Port (default: 8000)")
    p_mob.set_defaults(func=cmd_mobile)

    # terminal
    p_term = subparsers.add_parser("terminal", help="Launch interactive Rich Terminal TUI")
    p_term.set_defaults(func=cmd_terminal)

    # auto
    p_auto = subparsers.add_parser("auto", help="Launch standalone Autonomous Trading Engine")
    p_auto.set_defaults(func=cmd_auto)

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
