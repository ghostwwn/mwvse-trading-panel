"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Interactive Rich Terminal TUI
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import time
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from ..core.config import settings
from ..engine.scraper import MarketWatchScraper

console = Console()

def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=4),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="stats", size=38),
        Layout(name="positions", ratio=1),
    )
    return layout

def render_header() -> Panel:
    title = Text()
    title.append("⚡ MWVSE TRADING PANEL ", style="bold cyan")
    title.append("v2.5.0 ", style="bold yellow")
    title.append("• Engineered by @ghostwwn ", style="bold green")
    title.append("(https://github.com/ghostwwn)", style="dim")
    
    sub = Text("Independent algorithmic trading engine • Not affiliated with MarketWatch or Dow Jones", style="dim italic")
    return Panel(Align.center(Group(title, sub)), border_style="cyan", box=box.ROUNDED)

def render_stats(snapshot) -> Panel:
    tbl = Table(show_header=False, box=None, padding=(0, 1))
    tbl.add_column("Key", style="bold white")
    tbl.add_column("Val", style="cyan")

    tbl.add_row("Net Worth", f"[bold white]${snapshot.net_worth:,.2f}[/bold white]")
    tbl.add_row("Cash", f"${snapshot.cash:,.2f}")
    tbl.add_row("Buying Power", f"[bold green]${snapshot.buying_power:,.2f}[/bold green]")
    tbl.add_row("Tournament Rank", f"[bold yellow]#{snapshot.rank}[/bold yellow] / {snapshot.total_players}")
    tbl.add_row("Holdings Count", f"{len(snapshot.holdings)} active")
    tbl.add_row("Last Updated", f"[dim]{snapshot.updated_at}[/dim]")

    return Panel(tbl, title="[bold cyan]💼 Wallet Metrics[/bold cyan]", border_style="cyan", box=box.ROUNDED)

def render_positions(holdings) -> Panel:
    tbl = Table(box=box.SIMPLE_HEAVY, expand=True)
    tbl.add_column("Symbol", style="bold white")
    tbl.add_column("Type", style="bold cyan")
    tbl.add_column("Shares", justify="right")
    tbl.add_column("Price", justify="right")
    tbl.add_column("Position Value", justify="right")
    tbl.add_column("P&L ($)", justify="right")
    tbl.add_column("P&L (%)", justify="right")

    if not holdings:
        tbl.add_row("[dim]No open positions[/dim]", "-", "-", "-", "-", "-", "-")
    else:
        for h in holdings:
            pnl_style = "bold green" if h.gain_dollar >= 0 else "bold red"
            sign = "+" if h.gain_dollar >= 0 else ""
            tbl.add_row(
                h.symbol,
                f"[{ 'red' if h.pos_type.lower() == 'short' else 'green' }]{h.pos_type.upper()}[/]",
                f"{h.shares:,}",
                f"${h.price:,.2f}",
                f"${h.value:,.2f}",
                f"[{pnl_style}]{sign}${h.gain_dollar:,.2f}[/{pnl_style}]",
                f"[{pnl_style}]{sign}{h.gain_percent:.2f}%[/{pnl_style}]"
            )

    return Panel(tbl, title="[bold green]📊 Active Open Positions[/bold green]", border_style="green", box=box.ROUNDED)

def render_footer() -> Panel:
    txt = Text("Press Ctrl+C to exit • Web Station running at http://127.0.0.1:8000/ • Built by @ghostwwn", style="dim")
    return Panel(Align.center(txt), border_style="dim", box=box.ROUNDED)

async def tui_loop():
    scraper = MarketWatchScraper()
    layout = make_layout()

    with Live(layout, refresh_per_second=2, screen=True) as live:
        while True:
            snapshot = await scraper.fetch_portfolio()
            layout["header"].update(render_header())
            layout["stats"].update(render_stats(snapshot))
            layout["positions"].update(render_positions(snapshot.holdings))
            layout["footer"].update(render_footer())
            await asyncio.sleep(5)

def run_tui():
    """Entry point to launch the rich terminal TUI."""
    try:
        asyncio.run(tui_loop())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Exiting MWVSE Terminal. Goodbye![/bold yellow]\n")
