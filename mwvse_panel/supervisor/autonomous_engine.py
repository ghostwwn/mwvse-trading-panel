"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Autonomous Trading Engine & Risk Supervisor
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import time
from typing import Dict, List, Optional, Set
from ..core.config import settings
from ..core.models import TradeOrder, TradeAction, OrderType, PortfolioSnapshot
from ..core.logger import logger
from .risk_manager import RiskManager
from .scanner import ConfluenceScanner

class AutonomousTradingEngine:
    """
    Fully automated quantitative trading engine:
    1. Scans watchlist for breakout confluence and technical setups.
    2. Enforces position limits, buying power safeguards, and ticker cooldowns.
    3. Executes automated market entries (Buy/Short).
    4. Actively monitors and liquidates positions upon hitting Take-Profit or Stop-Loss.
    """

    def __init__(self, queue: Optional[asyncio.Queue] = None):
        self.queue = queue or asyncio.Queue()
        self.risk_manager = RiskManager(
            take_profit_pct=settings.take_profit_pct,
            stop_loss_pct=settings.stop_loss_pct
        )
        self.scanner = ConfluenceScanner()
        self.ticker_cooldowns: Dict[str, float] = {}
        self.is_running = False

    async def evaluate_exits(self, snapshot: PortfolioSnapshot):
        """Monitors all open positions and queues liquidations on TP/SL breaches."""
        for holding in snapshot.holdings:
            exit_order = self.risk_manager.evaluate_position(holding)
            if exit_order:
                logger.info(f"🛡️ [AUTO-RISK TRIGGER] Liquidation queued for {holding.symbol} ({exit_order.action.upper()})")
                await self.queue.put(exit_order)

    async def evaluate_entries(self, snapshot: PortfolioSnapshot):
        """Scans for qualifying setups and submits automated entries."""
        now = time.time()
        current_holdings = {h.symbol for h in snapshot.holdings}

        # Check portfolio capacity
        if len(current_holdings) >= settings.max_concurrent_positions:
            return

        # Check buying power
        if snapshot.buying_power < 5000.0:
            logger.info("⚠️ [AUTO-TRADER] Available buying power below threshold. Holding entries.")
            return

        # Run confluence scan
        signals = await self.scanner.scan_market()
        allowed_actions = ["BUY"] if not settings.allow_shorting else ["BUY", "SHORT"]
        qualifying = [
            s for s in signals 
            if s.action in allowed_actions and s.confidence >= settings.min_conviction_threshold
        ]

        for pick in qualifying:
            ticker = pick.target_ticker
            # Skip if already holding
            if ticker in current_holdings:
                continue

            # Skip if on cooldown
            if ticker in self.ticker_cooldowns:
                if (now - self.ticker_cooldowns[ticker]) < settings.ticker_cooldown_seconds:
                    continue

            # Register cooldown & submit entry
            self.ticker_cooldowns[ticker] = now
            act = TradeAction.BUY if pick.action == "BUY" else TradeAction.SHORT

            logger.info(f"🚀 [AUTO-ENTRY TRIGGER] {act.upper()} {ticker} ({pick.confidence}% conviction) — {pick.reason}")

            entry_order = TradeOrder(
                secret=settings.webhook_secret,
                ticker=ticker,
                action=act,
                dollar_amount=settings.allocation_per_trade_dollars,
                order_type=OrderType.MARKET
            )
            await self.queue.put(entry_order)
            break  # Stagger entries: one trade per scan cycle
