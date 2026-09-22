"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Unit Tests: Config & Data Models
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
from mwvse_panel.core.config import Settings
from mwvse_panel.core.models import TradeOrder, TradeAction, OrderType, Holding, PortfolioSnapshot

def test_slug_extraction_from_full_url():
    url = "https://www.marketwatch.com/games/bayonne-high-school-fall-2026-stock-market-game/portfolio?pub=xyz"
    s = Settings(MW_GAME_SLUG=url)
    assert s.mw_game_slug == "bayonne-high-school-fall-2026-stock-market-game"
    assert s.mw_base_url == "https://www.marketwatch.com/games/bayonne-high-school-fall-2026-stock-market-game"

def test_slug_extraction_from_plain_name():
    s = Settings(MW_GAME_SLUG="my-awesome-trading-game")
    assert s.mw_game_slug == "my-awesome-trading-game"

def test_trade_order_validation():
    order = TradeOrder(
        secret="test_secret",
        ticker="TSLA",
        action=TradeAction.BUY,
        shares=50
    )
    assert order.ticker == "TSLA"
    assert order.action == TradeAction.BUY
    assert order.shares == 50
    assert order.order_type == OrderType.MARKET

def test_holding_model():
    h = Holding(
        symbol="NVDA",
        shares=100,
        pos_type="Buy",
        price=220.0,
        value=22000.0,
        gain_dollar=500.0,
        gain_percent=2.32
    )
    assert h.symbol == "NVDA"
    assert h.gain_dollar == 500.0

if __name__ == "__main__":
    test_slug_extraction_from_full_url()
    test_slug_extraction_from_plain_name()
    test_trade_order_validation()
    test_holding_model()
    print("All config and models tests passed!")
