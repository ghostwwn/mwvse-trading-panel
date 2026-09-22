"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Unit Tests: Risk Supervisor
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
from mwvse_panel.core.models import Holding, TradeAction
from mwvse_panel.supervisor.risk_manager import RiskManager

def test_long_take_profit():
    rm = RiskManager(take_profit_pct=2.5, stop_loss_pct=-2.0)
    pos = Holding(
        symbol="TSLA",
        shares=50,
        pos_type="Buy",
        price=350.0,
        value=17500.0,
        gain_dollar=600.0,
        gain_percent=3.55  # Exceeds 3.0% threshold for large positions
    )
    order = rm.evaluate_position(pos)
    assert order is not None
    assert order.action == TradeAction.SELL
    assert order.ticker == "TSLA"

def test_long_stop_loss():
    rm = RiskManager(take_profit_pct=2.5, stop_loss_pct=-2.0)
    pos = Holding(
        symbol="INTC",
        shares=100,
        pos_type="Buy",
        price=30.0,
        value=3000.0,
        gain_dollar=-100.0,
        gain_percent=-3.33  # Worse than -2.0% stop-loss
    )
    order = rm.evaluate_position(pos)
    assert order is not None
    assert order.action == TradeAction.SELL
    assert order.ticker == "INTC"

def test_short_take_profit():
    rm = RiskManager(take_profit_pct=2.5, stop_loss_pct=-2.0)
    pos = Holding(
        symbol="MEME",
        shares=1000,
        pos_type="Short",
        price=5.0,
        value=5000.0,
        gain_dollar=200.0,
        gain_percent=4.0
    )
    order = rm.evaluate_position(pos)
    assert order is not None
    assert order.action == TradeAction.COVER

if __name__ == "__main__":
    test_long_take_profit()
    test_long_stop_loss()
    test_short_take_profit()
    print("All risk supervisor tests passed!")
