"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Foolproof Authentication & Account Attachment Wizard
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import asyncio
import secrets
import re
from pathlib import Path
from playwright.async_api import async_playwright

try:
    from rich.prompt import Prompt, Confirm
    HAS_RICH_PROMPT = True
except ImportError:
    HAS_RICH_PROMPT = False

    class Prompt:
        @staticmethod
        def ask(text, choices=None, default=None):
            prompt_str = f"{text} "
            if default:
                prompt_str += f"[{default}]: "
            else:
                prompt_str += ": "
            ans = input(prompt_str).strip()
            return ans or default

    class Confirm:
        @staticmethod
        def ask(text, default=True):
            d_str = "Y/n" if default else "y/N"
            ans = input(f"{text} [{d_str}]: ").strip().lower()
            if not ans:
                return default
            return ans in ["y", "yes"]

from ..core.config import settings, APP_DIR
from ..core.logger import console, logger

class AuthManager:
    """Manages MarketWatch login sessions, cookies, and interactive setup."""

    def __init__(self):
        self.user_data_dir = settings.user_data_path

    async def verify_session(self) -> bool:
        """Checks whether the saved profile in user_data/ has an active MarketWatch login."""
        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=True,
                    timeout=settings.browser_timeout_ms
                )
                page = await context.new_page()
                await page.goto(f"{settings.mw_base_url}/portfolio", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.5)

                # Check if logged in: looking for sign-in button or user profile indicator
                content = await page.content()
                is_logged_in = "sign in" not in content.lower() or "log out" in content.lower() or "my portfolio" in content.lower()
                await context.close()
                return is_logged_in
            except Exception as e:
                logger.warning(f"Session verification check encountered: {e}")
                return False

    async def run_interactive_login(self, game_slug: str):
        """
        Dummy-proof account attachment wizard:
        Opens a visible browser so the user can log in with Google, Apple, or Email.
        Automatically detects when login succeeds and saves session cookies!
        """
        console.print("\n[bold cyan]🔐 LAUNCHING FOOLPROOF LOGIN WIZARD...[/bold cyan]")
        console.print("[dim]A browser window will open. Simply log in to MarketWatch in that window.[/dim]")
        console.print("[dim]Once you are logged in, this script will automatically save your session and continue.[/dim]\n")

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=False,  # Visible browser for human login
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            target_url = f"https://www.marketwatch.com/games/{game_slug}"
            await page.goto(target_url)

            console.print("[bold yellow]⏳ Waiting for you to log in to MarketWatch...[/bold yellow]")

            # Loop and poll until login is detected
            logged_in = False
            for _ in range(120):  # 4 minutes timeout
                await asyncio.sleep(2)
                try:
                    current_url = page.url
                    # If user is on game page or portfolio page and not on a login redirect
                    if "accounts.marketwatch.com" not in current_url:
                        # Check for user identity element
                        body_text = await page.inner_text("body")
                        if "Log Out" in body_text or "Sign Out" in body_text or "Portfolio" in body_text:
                            logged_in = True
                            break
                except Exception:
                    pass

            if logged_in:
                console.print("\n[bold green]✅ SUCCESS! MarketWatch account successfully attached![/bold green]")
                console.print("[green]Session cookies saved securely in user_data/.[/green]\n")
            else:
                console.print("\n[bold red]⚠️ Login timeout exceeded. You can re-run 'python main.py setup' at any time.[/bold red]\n")

            await context.close()
            return logged_in

def run_setup_wizard():
    """CLI interactive configuration wizard."""
    console.print("\n[bold cyan]═════════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("   ⚡ [bold white]MWVSE TRADING PANEL — QUICK SETUP WIZARD[/bold white]")
    console.print("   [dim green]Engineered by @ghostwwn (https://github.com/ghostwwn)[/dim green]")
    console.print("[bold cyan]═════════════════════════════════════════════════════════════════[/bold cyan]\n")

    # 1. Ask for Game Slug or URL
    raw_game = Prompt.ask(
        "Enter your MarketWatch Game URL or Slug (e.g. https://www.marketwatch.com/games/my-game or my-game)",
        default=settings.mw_game_slug
    )
    # Parse clean slug
    match = re.search(r"/games/([^/?#]+)", raw_game)
    game_slug = match.group(1).strip() if match else re.sub(r"[^a-zA-Z0-9_-]", "", raw_game).strip()

    # 2. Webhook Secret
    default_secret = settings.webhook_secret if settings.webhook_secret != "mwvse_secret_key_change_me" else secrets.token_hex(16)
    webhook_secret = Prompt.ask(
        "Enter your Webhook Secret Token (for TradingView alerts)",
        default=default_secret
    )

    # 3. Strategy Selection
    console.print("\nSelect Autonomous Strategy Preset:")
    console.print("  1. HUNTER   — High-velocity breakout momentum (fastest profit compounding)")
    console.print("  2. SNIPER   — High-conviction tight take-profit/stop-loss scalper")
    console.print("  3. BALANCED — Core position builder with trailing risk guard")
    strategy_choice = Prompt.ask("Choose preset (1, 2, or 3)", default="1")
    strategy_map = {"1": "HUNTER", "2": "SNIPER", "3": "BALANCED"}
    chosen_strategy = strategy_map.get(strategy_choice, "HUNTER")

    # 4. Save to .env
    env_content = f"""# MWVSE Trading Panel Config (Generated by Setup Wizard)
# Engineered by @ghostwwn (https://github.com/ghostwwn)

MW_GAME_SLUG={game_slug}
HOST=127.0.0.1
PORT=8000
WEBHOOK_SECRET={webhook_secret}

AUTOPILOT_STRATEGY={chosen_strategy}
AUTOPILOT_ACTIVE=true
AUTOPILOT_SCAN_INTERVAL=30
AUTOPILOT_HARVEST_INTERVAL=15
MAX_CONCURRENT_POSITIONS=10
DEFAULT_SHARES=25
ALLOW_SHORTING=true

COPY_VAULT_STARTING_CAPITAL=20000.0
COPY_SCAN_INTERVAL_SECONDS=10
"""
    env_path = APP_DIR / ".env"
    with open(env_path, "w") as f:
        f.write(env_content)
    console.print(f"\n✅ Saved configuration to {env_path.name}!\n")

    # 5. Offer 1-click browser login
    do_login = Confirm.ask("Would you like to log into MarketWatch now via browser?", default=True)
    if do_login:
        auth = AuthManager()
        asyncio.run(auth.run_interactive_login(game_slug))

    console.print("🎉 Setup Complete! Run 'python main.py run' or './run.sh' to start trading!\n")
