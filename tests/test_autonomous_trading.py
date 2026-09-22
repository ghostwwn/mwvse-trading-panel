"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Unit Tests: Autonomous Trading Engine
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
from mwvse_panel.core.models import Holding, PortfolioSnapshot, TradeAction
from mwvse_panel.supervisor.autonomous_engine import AutonomousTradingEngine

def test_autonomous_entry_execution():
    queue = asyncio.Queue()
    engine = AutonomousTradingEngine(queue=queue)

    snapshot = PortfolioSnapshot(
        net_worth=100000.0,
        cash=50000.0,
        buying_power=100000.0,
        rank=1,
        total_players=50,
        holdings=[]
    )

    # Run entry evaluation
    asyncio.run(engine.evaluate_entries(snapshot))

    # A trade should have been queued
    assert not queue.empty()
    queued_order = queue.get_nowait()
    assert queued_order.ticker in engine.scanner.watchlist
    assert queued_order.action in [TradeAction.BUY, TradeAction.SHORT]

def test_capacity_suppression():
    queue = asyncio.Queue()
    engine = AutonomousTradingEngine(queue=queue)

    # 10 holdings = max capacity
    dummy_holdings = [
        Holding(symbol=f"SYM{i}", shares=10, price=10.0, value=100.0, gain_dollar=0.0, gain_percent=0.0)
        for i in range(10)
    ]
    snapshot = PortfolioSnapshot(
        net_worth=100000.0,
        cash=50000.0,
        buying_power=100000.0,
        rank=1,
        total_players=50,
        holdings=dummy_holdings
    )

    asyncio.run(engine.evaluate_entries(snapshot))
    assert queue.empty()  # Suppressed because portfolio is at capacity!

def test_buying_power_safeguard():
    queue = asyncio.Queue()
    engine = AutonomousTradingEngine(queue=queue)

    snapshot = PortfolioSnapshot(
        net_worth=100000.0,
        cash=500.0,
        buying_power=1000.0,  # Below $5,000 threshold
        rank=1,
        total_players=50,
        holdings=[]
    )

    asyncio.run(engine.evaluate_entries(snapshot))
    assert queue.empty()  # Suppressed due to low buying power!

if __name__ == "__main__":
    test_autonomous_entry_execution()
    test_capacity_suppression()
    test_buying_power_safeguard()
    print("All autonomous trading tests passed!")
