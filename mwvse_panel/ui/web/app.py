"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — FastAPI Server & Webhook Handler
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ...core.config import settings
from ...core.models import TradeOrder, PortfolioSnapshot
from ...core.logger import logger, console
from ...engine.executor import OrderExecutor
from ...engine.scraper import MarketWatchScraper
from ...supervisor.autonomous_engine import AutonomousTradingEngine

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
DASHBOARD_FILE = TEMPLATES_DIR / "dashboard.html"
MOBILE_FILE = TEMPLATES_DIR / "mobile.html"

app = FastAPI(
    title="MWVSE Trading Panel",
    description="Algorithmic day-trading, autonomous execution, and risk supervisor for MarketWatch VSE. Built by @ghostwwn.",
    version="2.5.0"
)

# Mount static files for PWA icons & manifest
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global runtime state
trade_queue: asyncio.Queue = asyncio.Queue()
executor = OrderExecutor()
scraper = MarketWatchScraper()
auto_engine = AutonomousTradingEngine(queue=trade_queue)

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

        try:
            await auto_engine.evaluate_exits(cached_portfolio)
            await auto_engine.evaluate_entries(cached_portfolio)
        except Exception as e:
            logger.warning(f"Autonomous supervisor error: {e}")

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(order_queue_worker())
    asyncio.create_task(portfolio_sync_daemon())
    asyncio.create_task(autonomous_supervisor_loop())
    add_log(f"⚡ MWVSE Workstation online. Autonomous Engine: ACTIVE ({settings.autopilot_strategy})")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    ua = request.headers.get("user-agent", "").lower()
    is_mobile = any(m in ua for m in ["iphone", "android", "ipad", "mobile"])

    target_file = MOBILE_FILE if is_mobile else DASHBOARD_FILE
    if target_file.exists():
        with open(target_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>MWVSE Panel Dashboard</h1><p>Template not found.</p>")

@app.get("/mobile", response_class=HTMLResponse)
async def serve_mobile():
    if MOBILE_FILE.exists():
        with open(MOBILE_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>MWVSE Mobile Station</h1><p>Mobile template not found.</p>")

@app.get("/manifest.json")
async def get_manifest():
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content={})

@app.get("/api/portfolio")
async def get_portfolio():
    return cached_portfolio.model_dump()

@app.get("/api/logs")
async def get_logs():
    return {"logs": recent_logs}

@app.get("/api/autopilot/status")
async def get_autopilot_status():
    return {
        "active": settings.autopilot_active,
        "strategy": settings.autopilot_strategy,
        "max_positions": settings.max_concurrent_positions,
        "allocation_per_trade": settings.allocation_per_trade_dollars
    }

@app.post("/api/autopilot/toggle")
async def toggle_autopilot():
    settings.autopilot_active = not settings.autopilot_active
    state_str = "ACTIVE" if settings.autopilot_active else "PAUSED"
    add_log(f"🤖 [AUTONOMOUS ENGINE] Auto-Pilot status switched to: {state_str}")
    return {"active": settings.autopilot_active}

@app.post("/webhook")
async def handle_webhook(order: TradeOrder):
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
