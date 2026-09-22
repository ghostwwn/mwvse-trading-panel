"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — High-Performance MarketWatch Scraper
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import re
import time
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright

from ..core.config import settings
from ..core.logger import logger
from ..core.models import Holding, LeaderboardEntry, PortfolioSnapshot

class MarketWatchScraper:
    """Extracts live account statistics, holdings, transactions, and leaderboard data."""

    def __init__(self):
        self.user_data_dir = settings.user_data_path

    async def fetch_portfolio(self) -> PortfolioSnapshot:
        """Fetches live portfolio stats and holdings for the authenticated user."""
        async with async_playwright() as p:
            cb = int(time.time() * 1000)
            url = f"{settings.mw_base_url}/portfolio?_cb={cb}"

            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=True,
                    timeout=settings.browser_timeout_ms,
                    extra_http_headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=18000)
                await asyncio.sleep(1.5)

                body_text = await page.inner_text("body")

                # Extract Net Worth
                nw_match = re.search(r"Net Worth\s*\$?([\d,]+(?:\.\d+)?)", body_text, re.IGNORECASE)
                net_worth = float(nw_match.group(1).replace(",", "")) if nw_match else 100000.0

                # Extract Cash & Buying Power
                cash_match = re.search(r"Cash Remaining\s*\$?([\d,]+(?:\.\d+)?)", body_text, re.IGNORECASE)
                cash = float(cash_match.group(1).replace(",", "")) if cash_match else 0.0

                bp_match = re.search(r"Buying Power\s*\$?([\d,]+(?:\.\d+)?)", body_text, re.IGNORECASE)
                buying_power = float(bp_match.group(1).replace(",", "")) if bp_match else cash * 2.0

                # Extract Rank
                rank_match = re.search(r"Rank\s*#?(\d+)\s*(?:of|/)\s*(\d+)", body_text, re.IGNORECASE)
                rank = int(rank_match.group(1)) if rank_match else 1
                total_players = int(rank_match.group(2)) if rank_match else 1

                # Parse Holdings Table
                rows = await page.locator("table tr").all_inner_texts()
                holdings = []
                for r in rows[1:]:
                    parts = [p.strip() for p in r.split("\t") if p.strip()]
                    if len(parts) >= 4:
                        sym = parts[0].split("\n")[0].strip()
                        sh_match = re.search(r"(\d+)\s*Shares?", parts[0])
                        shares = int(sh_match.group(1)) if sh_match else 0
                        
                        pos_type = "Buy"
                        if "short" in parts[1].lower():
                            pos_type = "Short"

                        px_match = re.search(r"\$?([\d,]+(?:\.\d+)?)", parts[2])
                        price = float(px_match.group(1).replace(",", "")) if px_match else 0.0

                        val_match = re.search(r"\$?([\d,]+(?:\.\d+)?)", parts[3])
                        val = float(val_match.group(1).replace(",", "")) if val_match else 0.0

                        gain_d_match = re.search(r"([+-]?\$?[\d,]+(?:\.\d+)?)", parts[3])
                        gain_pct_match = re.search(r"([+-]?[\d,]+(?:\.\d+)?)\s*%", parts[3])
                        
                        gain_dollar = float(gain_d_match.group(1).replace("$", "").replace(",", "")) if gain_d_match else 0.0
                        gain_pct = float(gain_pct_match.group(1).replace(",", "")) if gain_pct_match else 0.0

                        if sym and shares > 0:
                            holdings.append(Holding(
                                symbol=sym,
                                shares=shares,
                                pos_type=pos_type,
                                price=price,
                                value=val,
                                gain_dollar=gain_dollar,
                                gain_percent=gain_pct
                            ))

                await context.close()
                return PortfolioSnapshot(
                    net_worth=net_worth,
                    cash=cash,
                    buying_power=buying_power,
                    rank=rank,
                    total_players=total_players,
                    holdings=holdings,
                    updated_at=time.strftime("%I:%M:%S %p")
                )

            except Exception as e:
                logger.error(f"Portfolio scraper error: {e}")
                return PortfolioSnapshot()

    async def fetch_leaderboard(self) -> List[LeaderboardEntry]:
        """Fetches live tournament rankings."""
        async with async_playwright() as p:
            cb = int(time.time() * 1000)
            url = f"{settings.mw_base_url}/rankings?_cb={cb}"
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=True,
                    timeout=settings.browser_timeout_ms
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=18000)
                await asyncio.sleep(1.0)

                rows = await page.locator("table tr").all_inner_texts()
                entries = []
                for r in rows[1:]:
                    parts = [p.strip() for p in r.split("\t") if p.strip()]
                    if len(parts) >= 5:
                        try:
                            rank = int(re.sub(r"\D", "", parts[0]) or "0")
                            name = parts[1].replace("\n", " ").strip()
                            nw = float(re.sub(r"[^\d.]", "", parts[2]) or "0")
                            last_ret = parts[3]
                            trades = int(re.sub(r"\D", "", parts[4]) or "0")
                            tot_ret = parts[5] if len(parts) > 5 else last_ret

                            entries.append(LeaderboardEntry(
                                rank=rank,
                                name=name,
                                net_worth=nw,
                                today_return=last_ret,
                                trades_count=trades,
                                total_return=tot_ret
                            ))
                        except Exception:
                            continue
                await context.close()
                return entries
            except Exception as e:
                logger.error(f"Leaderboard scraper error: {e}")
                return []
