"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — FastAPI Server & Webhook Handler
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ...core.config import settings
from ...core.models import TradeOrder, PortfolioSnapshot
from ...core.logger import logger, console
from ...engine.executor import OrderExecutor
from ...engine.scraper import MarketWatchScraper
from ...supervisor.risk_manager import RiskManager
from ...supervisor.scanner import ConfluenceScanner

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DASHBOARD_FILE = TEMPLATES_DIR / "dashboard.html"

app = FastAPI(
    title="MWVSE Trading Panel",
    description="Algorithmic trading panel, position supervisor, and copy-trading engine for MarketWatch VSE. Built by @ghostwwn.",
    version="2.5.0"
)

# Global runtime state
trade_queue: asyncio.Queue = asyncio.Queue()
executor = OrderExecutor()
scraper = MarketWatchScraper()
risk_manager = RiskManager()
scanner = ConfluenceScanner()

cached_portfolio = PortfolioSnapshot()
recent_logs: List[Dict[str, str]] = []

def add_log(msg: str):
    now = time.strftime("%I:%M:%S %p")
    recent_logs.append({"time": now, "message": msg})
    if len(recent_logs) > 100:
        recent_logs.pop(0)

async def portfolio_sync_daemon():
    global cached_portfolio
    while True:
        try:
            snapshot = await scraper.fetch_portfolio()
            if snapshot.net_worth > 0:
                cached_portfolio = snapshot
        except Exception as e:
            logger.warning(f"Daemon sync warning: {e}")
        await asyncio.sleep(15)

async def order_queue_worker():
    while True:
        order = await trade_queue.get()
        try:
            action = order.action.value if hasattr(order.action, "value") else str(order.action)
            res = await executor.execute_trade(
                ticker=order.ticker,
                action=action,
                shares=order.shares,
                dollar_amount=order.dollar_amount,
                full_port=order.full_port,
                order_type=order.order_type.value if hasattr(order.order_type, "value") else "Market"
            )
            status = res.get("status", "unknown").upper()
            msg = res.get("message", "")
            add_log(f"[{status}] {action.upper()} {order.ticker} -> {msg}")
            # Refresh portfolio immediately
            asyncio.create_task(scraper.fetch_portfolio())
        except Exception as e:
            logger.error(f"Execution error on {order.ticker}: {e}")
            add_log(f"[ERROR] {order.ticker}: {e}")
        finally:
            trade_queue.task_done()

async def autonomous_supervisor_loop():
    while True:
        await asyncio.sleep(settings.autopilot_harvest_interval)
        if not settings.autopilot_active:
            continue

        # 1. Harvest Take-Profit & Stop-Loss
        for h in cached_portfolio.holdings:
            exit_order = risk_manager.evaluate_position(h)
            if exit_order:
                add_log(f"🛡️ [RISK TRIGGER] Liquidation queued for {h.symbol} ({exit_order.action.upper()})")
                await trade_queue.put(exit_order)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(order_queue_worker())
    asyncio.create_task(portfolio_sync_daemon())
    asyncio.create_task(autonomous_supervisor_loop())
    add_log("⚡ MWVSE Workstation online. Autonomous engine armed.")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    if DASHBOARD_FILE.exists():
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>MWVSE Panel Dashboard</h1><p>Dashboard HTML not found.</p>")

@app.get("/api/portfolio")
async def get_portfolio():
    return cached_portfolio.model_dump()

@app.get("/api/logs")
async def get_logs():
    return {"logs": recent_logs}

@app.post("/webhook")
async def handle_webhook(order: TradeOrder):
    # Authenticate secret (or internal client token)
    if order.secret != settings.webhook_secret and order.secret != "client_internal_auth":
        raise HTTPException(status_code=403, detail="Invalid webhook secret token.")

    await trade_queue.put(order)
    action = order.action.value if hasattr(order.action, "value") else str(order.action)
    add_log(f"⚡ [WEBHOOK QUEUED] {action.upper()} {order.ticker}")
    return {
        "status": "queued",
        "ticker": order.ticker,
        "action": action,
        "message": f"Queued {action.upper()} {order.ticker} for execution."
    }
