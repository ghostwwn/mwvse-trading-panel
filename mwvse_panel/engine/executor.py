"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Resilient Order Execution Engine
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright

from ..core.config import settings, APP_DIR
from ..core.models import TradeAction, ExecutionResult
from ..core.logger import logger
from .auth import ensure_playwright_browser

class OrderExecutor:
    """Executes trade orders against MarketWatch Virtual Stock Exchange via Playwright."""

    def __init__(self):
        self.user_data_dir = settings.user_data_path
        self.screenshots_dir = APP_DIR / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def execute_trade(
        self,
        ticker: str,
        action: str,
        shares: Optional[int] = None,
        dollar_amount: Optional[float] = None,
        full_port: bool = False,
        order_type: str = "Market",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes a single market or limit order with automatic sizing,
        selector fallbacks, and comprehensive error handling.
        """
        ticker = ticker.upper().strip()
        action = action.lower().strip()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        ensure_playwright_browser()

        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=settings.mw_headless,
                    timeout=settings.browser_timeout_ms
                )
                page = await context.new_page()

                # 1. Navigate to Game Dashboard
                await page.goto(settings.mw_base_url, wait_until="domcontentloaded", timeout=18000)
                await asyncio.sleep(1.0)

                # 2. Search for Ticker
                search_input = page.locator("input#search-input, input[placeholder*='Search'], input[name='search']").first
                await search_input.wait_for(state="visible", timeout=10000)
                await search_input.click()
                await search_input.fill(ticker)
                await asyncio.sleep(1.0)
                await page.keyboard.press("Enter")
                await asyncio.sleep(1.5)

                # Click dropdown result if visible
                first_result = page.locator(".results-item, .search-result, .list--results a").first
                if await first_result.is_visible():
                    await first_result.click()
                    await asyncio.sleep(1.5)

                # 3. Action Selection (BUY, SELL, SHORT, COVER)
                action_selectors = {
                    "buy": ["input#order-buy", "button[data-action='buy']", "label[for='order-buy']"],
                    "sell": ["input#order-sell", "button[data-action='sell']", "label[for='order-sell']"],
                    "short": ["input#order-short", "button[data-action='short']", "label[for='order-short']"],
                    "cover": ["input#order-cover", "button[data-action='cover']", "label[for='order-cover']"]
                }
                
                selected_action = False
                for sel in action_selectors.get(action, []):
                    elem = page.locator(sel).first
                    if await elem.is_visible():
                        await elem.click()
                        selected_action = True
                        break

                if not selected_action:
                    # Fallback text search for action buttons
                    action_btn = page.locator(f"button:has-text('{action.upper()}'), a:has-text('{action.upper()}')").first
                    if await action_btn.is_visible():
                        await action_btn.click()
                        selected_action = True

                await asyncio.sleep(0.8)

                # 4. Read Live Quoted Price from DOM
                price_locator = page.locator(".quote-price, .price, .live-price, .data-price").first
                price_val = 0.0
                if await price_locator.is_visible():
                    p_txt = await price_locator.inner_text()
                    match = re.search(r"[\d,]+(?:\.\d+)?", p_txt)
                    if match:
                        price_val = float(match.group(0).replace(",", ""))

                # 5. Determine Quantity (Shares)
                target_shares = shares or settings.default_shares
                if dollar_amount and price_val > 0:
                    target_shares = max(1, int(dollar_amount / price_val))
                elif full_port:
                    bp_elem = page.locator(".buying-power, .cash-remaining, .balance-val").first
                    if await bp_elem.is_visible():
                        bp_txt = await bp_elem.inner_text()
                        bp_match = re.search(r"[\d,]+(?:\.\d+)?", bp_txt)
                        if bp_match and price_val > 0:
                            bp_num = float(bp_match.group(0).replace(",", ""))
                            target_shares = max(1, int((bp_num * 0.98) / price_val))

                # 6. Enter Quantity
                qty_input = page.locator("input#shares, input#quantity, input[name='shares']").first
                await qty_input.wait_for(state="visible", timeout=8000)
                await qty_input.fill("")
                await qty_input.fill(str(target_shares))
                await asyncio.sleep(0.5)

                # 7. Check for Warnings or Errors before submit
                error_elem = page.locator(".message-error, .alert-danger, .validation-message").first
                if await error_elem.is_visible():
                    err_msg = await error_elem.inner_text()
                    await context.close()
                    return {
                        "status": "ignored",
                        "ticker": ticker,
                        "action": action,
                        "message": f"Pre-submit validation warning: {err_msg.strip()}"
                    }

                # 8. Submit Order
                submit_btn = page.locator("button#submit-order, button[type='submit']:has-text('Submit'), button:has-text('Submit Order')").first
                await submit_btn.click()
                await asyncio.sleep(2.0)

                # 9. Verify Confirmation
                page_text = await page.inner_text("body")
                is_success = "order submitted" in page_text.lower() or "success" in page_text.lower() or "order executed" in page_text.lower()

                if not is_success:
                    # Check for explicit failure
                    fail_elem = page.locator(".alert, .error-summary, .message-error").first
                    fail_txt = await fail_elem.inner_text() if await fail_elem.is_visible() else "Submission response unclear"
                    # Capture screenshot for inspection
                    snap_path = self.screenshots_dir / f"fail_{ticker}_{ts}.png"
                    await page.screenshot(path=str(snap_path))
                    await context.close()
                    return {
                        "status": "error",
                        "ticker": ticker,
                        "action": action,
                        "message": f"MarketWatch rejected order: {fail_txt.strip()}"
                    }

                await context.close()
                return {
                    "status": "success",
                    "ticker": ticker,
                    "action": action,
                    "shares": target_shares,
                    "price": price_val,
                    "message": f"Successfully submitted {action.upper()} {target_shares}x {ticker} to MarketWatch."
                }

            except Exception as e:
                logger.error(f"Order execution failure on {ticker}: {e}")
                return {
                    "status": "error",
                    "ticker": ticker,
                    "action": action,
                    "message": str(e)
                }
