"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Isolated Strategy Compounding Vault
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.config import settings, APP_DIR
from ..core.models import VaultState
from ..core.logger import logger

class CompoundingVault:
    """
    Manages an isolated pool of capital (e.g. $20k) for copy-trading.
    Compounds realized profits directly back into subsequent copy trade sizes.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or (APP_DIR / "copy_strategy_vault.json")
        self.state = self.load()

    def load(self) -> VaultState:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return VaultState(**data)
            except Exception as e:
                logger.warning(f"Could not load vault state, reinitializing: {e}")
        
        base = settings.copy_vault_starting_capital
        return VaultState(base_capital=base, current_capital=base, total_realized_profit=0.0, open_positions={})

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.state.model_dump(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save vault state: {e}")

    def record_entry(self, symbol: str, action: str, entry_price: float, trader: str, timestamp: str):
        alloc = self.state.current_capital
        self.state.open_positions[symbol] = {
            "action": action,
            "entry_price": entry_price,
            "allocated": alloc,
            "trader": trader,
            "time": timestamp
        }
        self.save()

    def record_exit(self, symbol: str, exit_price: float) -> Optional[float]:
        pos = self.state.open_positions.pop(symbol, None)
        if not pos or exit_price <= 0:
            self.save()
            return None

        entry_p = pos["entry_price"]
        alloc = pos["allocated"]
        is_short = pos["action"] == "short"

        if is_short:
            pnl_pct = (entry_p - exit_price) / entry_p
        else:
            pnl_pct = (exit_price - entry_p) / entry_p

        profit = alloc * pnl_pct
        self.state.current_capital = max(5000.0, self.state.current_capital + profit)
        self.state.total_realized_profit += profit
        self.save()
        return profit
