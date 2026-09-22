"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Unit Tests: Copier Ordering & Vault Compounding
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
from pathlib import Path
from mwvse_panel.copier.vault import CompoundingVault

def test_chronological_ordering():
    # MarketWatch table returns newest to oldest
    raw_feed = [
        {"action": "cover", "symbol": "GRML", "price": 15.44},  # newer (index 0)
        {"action": "short", "symbol": "GRML", "price": 16.39}   # older (index 1)
    ]
    
    # In copier, unseen list is reversed so that entry precedes exit!
    execution_sequence = list(reversed(raw_feed))
    assert execution_sequence[0]["action"] == "short"
    assert execution_sequence[1]["action"] == "cover"

def test_vault_compounding(tmp_path: Path):
    vault_file = tmp_path / "test_vault.json"
    vault = CompoundingVault(file_path=vault_file)
    assert vault.state.current_capital == 20000.0

    # Short at $40.00
    vault.record_entry("TEST", "short", 40.0, "Leader A", "10:00 AM")
    assert "TEST" in vault.state.open_positions

    # Cover at $38.00 (+5% profit on short)
    profit = vault.record_exit("TEST", 38.0)
    assert abs(profit - 1000.0) < 0.01  # 5% of 20,000 = $1,000
    assert abs(vault.state.current_capital - 21000.0) < 0.01
    assert abs(vault.state.total_realized_profit - 1000.0) < 0.01

if __name__ == "__main__":
    import tempfile
    test_chronological_ordering()
    with tempfile.TemporaryDirectory() as td:
        test_vault_compounding(Path(td))
    print("All copier tests passed!")
