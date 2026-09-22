"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Autonomous Risk Supervisor (TP/SL Guardian)
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
from typing import List, Optional
from ..core.config import settings
from ..core.models import Holding, TradeOrder, TradeAction, OrderType
from ..core.logger import logger

class RiskManager:
    """Monitors live positions and triggers automatic Take-Profit and Stop-Loss exits."""

    def __init__(
        self,
        take_profit_pct: float = 2.5,
        stop_loss_pct: float = -2.0,
        large_pos_threshold: float = 15000.0
    ):
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.large_pos_threshold = large_pos_threshold

    def evaluate_position(self, holding: Holding) -> Optional[TradeOrder]:
        """Evaluates whether an open holding qualifies for Take-Profit or Stop-Loss liquidation."""
        pnl_pct = holding.gain_percent
        is_short = holding.pos_type.lower() == "short"

        # Adaptive scaling: larger positions give slightly more room to weather midday noise
        tp_target = self.take_profit_pct
        sl_cutoff = self.stop_loss_pct
        if holding.value >= self.large_pos_threshold:
            tp_target = 3.0
            sl_cutoff = -2.5

        # 1. Take-Profit Harvest
        if pnl_pct >= tp_target:
            action = TradeAction.COVER if is_short else TradeAction.SELL
            logger.info(f"🎯 [TAKE-PROFIT] {holding.symbol} hit target (+{pnl_pct:.2f}% | +${holding.gain_dollar:,.2f})! Liquidating via {action.upper()}.")
            return TradeOrder(
                secret=settings.webhook_secret,
                ticker=holding.symbol,
                action=action,
                shares=holding.shares,
                order_type=OrderType.MARKET
            )

        # 2. Stop-Loss Capital Protection
        if pnl_pct <= sl_cutoff:
            action = TradeAction.COVER if is_short else TradeAction.SELL
            logger.warning(f"🛑 [STOP-LOSS] {holding.symbol} hit cutoff ({pnl_pct:.2f}% | -${abs(holding.gain_dollar):,.2f})! Liquidating via {action.upper()} to protect capital.")
            return TradeOrder(
                secret=settings.webhook_secret,
                ticker=holding.symbol,
                action=action,
                shares=holding.shares,
                order_type=OrderType.MARKET
            )

        return None
