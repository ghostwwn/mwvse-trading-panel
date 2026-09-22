"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Leaderboard Copy-Trading Engine
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import re
import time
import urllib.request
import json
from typing import List, Dict, Set, Any
from playwright.async_api import async_playwright

from ..core.config import settings
from ..core.logger import logger, console
from .vault import CompoundingVault

DEFAULT_TARGETS = [
    {"name": "Orlando Ramos", "pub_id": "bUZqgsGFVdPr"},
    {"name": "Motaz Mohamed", "pub_id": "mwpKQ7MhHT4n"}
]

class LeaderCopyEngine:
    """
    Monitors tournament leaders in real time and automatically mirrors
    their trades with sub-second execution and isolated compounding vault sizing.
    """

    def __init__(self, targets: List[Dict[str, str]] = None):
        self.targets = targets or DEFAULT_TARGETS
        self.vault = CompoundingVault()
        self.seen_signatures: Set[str] = set()
        self.webhook_url = f"http://{settings.host}:{settings.port}/webhook"

    async def get_target_transactions(self, page, target: Dict[str, str]) -> List[Dict[str, Any]]:
        cb = int(time.time() * 1000)
        url = f"{settings.mw_base_url}/transactions?pub={target['pub_id']}&_cb={cb}"

        for attempt in range(3):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.0)
                rows = await page.locator("table tr").all_inner_texts()
                transactions = []
                for r in rows[1:]:
                    parts = [p.strip() for p in r.split("\t") if p.strip()]
                    if len(parts) >= 6:
                        sym, order_time, tx_time, tx_type, amount, price = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                        p_num = float(re.sub(r"[^\d.]", "", price) or "0")
                        cleaned_amt = int(re.sub(r"[^\d]", "", amount) or 0)
                        transactions.append({
                            "trader": target["name"],
                            "symbol": sym,
                            "order_time": order_time,
                            "tx_time": tx_time,
                            "type": tx_type.lower(),
                            "shares": cleaned_amt,
                            "price_str": price,
                            "price_num": p_num
                        })
                return transactions
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2.0)
                    continue
                logger.warning(f"Error reading transactions for {target['name']}: {e}")
                return []

    def dispatch_trade(self, ticker: str, action: str, dollar_amount: float, trader: str):
        payload = {
            "secret": settings.webhook_secret,
            "ticker": ticker,
            "action": action,
            "dollar_amount": dollar_amount,
            "order_type": "Market"
        }
        logger.info(f"⚡ [STRATEGY VAULT] Mirroring {trader}: {action.upper()} {ticker} (${dollar_amount:,.2f})")
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"✅ [COPY DISPATCH] Result for {ticker}: {data.get('message')}")
        except Exception as e:
            logger.error(f"Failed to dispatch mirror trade to webhook: {e}")

    async def run(self):
        logger.info(f"🚀 [COPY ENGINE ONLINE] Dedicated Vault: ${self.vault.state.current_capital:,.2f}")
        logger.info(f"[*] Tracking {len(self.targets)} tournament leaders. Profit compounding armed.")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                extra_http_headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
            )
            page = await context.new_page()

            # 1. Seed initial existing transactions so we only mirror NEW executions
            for target in self.targets:
                initial = await self.get_target_transactions(page, target)
                for tx in initial:
                    sig = f"{tx['trader']}_{tx['symbol']}_{tx['tx_time']}_{tx['type']}_{tx['shares']}"
                    self.seen_signatures.add(sig)
                logger.info(f"[*] Indexed {len(initial)} baseline transactions for {target['name']}.")

            # 2. Main Scan Loop
            scan_count = 0
            while True:
                await asyncio.sleep(settings.copy_scan_interval_seconds)
                scan_count += 1

                for target in self.targets:
                    txs = await self.get_target_transactions(page, target)
                    unseen = []
                    for tx in txs:
                        sig = f"{tx['trader']}_{tx['symbol']}_{tx['tx_time']}_{tx['type']}_{tx['shares']}"
                        if sig not in self.seen_signatures:
                            unseen.append((sig, tx))

                    # Chronological execution: oldest new transaction executes first
                    unseen.reverse()

                    for sig, tx in unseen:
                        self.seen_signatures.add(sig)
                        sym = tx["symbol"]
                        act = tx["type"]
                        px = tx["price_num"]

                        logger.info(f"🚨 [LEADER TRADE] {tx['trader']} executed: {act.upper()} {tx['shares']}x {sym} @ {tx['price_str']}")

                        if act in ["buy", "short"]:
                            alloc = self.vault.state.current_capital
                            self.vault.record_entry(sym, act, px, tx["trader"], tx["tx_time"])
                            self.dispatch_trade(sym, act, alloc, tx["trader"])

                        elif act in ["sell", "cover"]:
                            profit = self.vault.record_exit(sym, px)
                            if profit is not None:
                                sign = "+" if profit >= 0 else "-"
                                logger.info(f"💰 [VAULT COMPOUNDED] Trade realized {sign}${abs(profit):,.2f}! Next copy size: ${self.vault.state.current_capital:,.2f}")
                            
                            self.dispatch_trade(sym, act, self.vault.state.current_capital, tx["trader"])
