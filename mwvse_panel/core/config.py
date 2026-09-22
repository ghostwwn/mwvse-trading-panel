"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Core Configuration
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
from pathlib import Path
import os
import re
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = None
    HAS_PYDANTIC_SETTINGS = False

from pydantic import Field, field_validator
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent.parent.parent
USER_DATA_DIR = APP_DIR / "user_data"
LOGS_DIR = APP_DIR / "logs"

# Ensure .env is loaded
if (APP_DIR / ".env").exists():
    load_dotenv(APP_DIR / ".env")

class Settings(BaseSettings):
    if HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=str(APP_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore"
        )

    # 1. Game Identity
    mw_game_slug: str = Field(
        default_factory=lambda: os.getenv("MW_GAME_SLUG", "bayonne-high-school-fall-2026-stock-market-game"),
        alias="MW_GAME_SLUG"
    )
    mw_game_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("MW_GAME_URL"),
        alias="MW_GAME_URL"
    )

    # 2. Server & Webhooks
    host: str = Field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"), alias="HOST")
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")), alias="PORT")
    webhook_secret: str = Field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", "mwvse_secret_key_change_me"), alias="WEBHOOK_SECRET")

    # 3. Autonomous Supervisor
    autopilot_strategy: str = Field(default_factory=lambda: os.getenv("AUTOPILOT_STRATEGY", "HUNTER"), alias="AUTOPILOT_STRATEGY")
    autopilot_active: bool = Field(default_factory=lambda: os.getenv("AUTOPILOT_ACTIVE", "true").lower() == "true", alias="AUTOPILOT_ACTIVE")
    autopilot_scan_interval: int = Field(default_factory=lambda: int(os.getenv("AUTOPILOT_SCAN_INTERVAL", "30")), alias="AUTOPILOT_SCAN_INTERVAL")
    autopilot_harvest_interval: int = Field(default_factory=lambda: int(os.getenv("AUTOPILOT_HARVEST_INTERVAL", "15")), alias="AUTOPILOT_HARVEST_INTERVAL")
    max_concurrent_positions: int = Field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_POSITIONS", "10")), alias="MAX_CONCURRENT_POSITIONS")
    default_shares: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_SHARES", "25")), alias="DEFAULT_SHARES")
    allow_shorting: bool = Field(default_factory=lambda: os.getenv("ALLOW_SHORTING", "true").lower() == "true", alias="ALLOW_SHORTING")
    min_conviction_threshold: int = Field(default_factory=lambda: int(os.getenv("MIN_CONVICTION_THRESHOLD", "75")), alias="MIN_CONVICTION_THRESHOLD")
    ticker_cooldown_seconds: int = Field(default_factory=lambda: int(os.getenv("TICKER_COOLDOWN_SECONDS", "600")), alias="TICKER_COOLDOWN_SECONDS")

    # 4. Compounding Copy Trader
    copy_vault_starting_capital: float = Field(default_factory=lambda: float(os.getenv("COPY_VAULT_STARTING_CAPITAL", "20000.0")), alias="COPY_VAULT_STARTING_CAPITAL")
    copy_scan_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("COPY_SCAN_INTERVAL_SECONDS", "10")), alias="COPY_SCAN_INTERVAL_SECONDS")

    # 5. Playwright & MarketWatch Auth
    mw_email: Optional[str] = Field(default_factory=lambda: os.getenv("MW_EMAIL"), alias="MW_EMAIL")
    mw_password: Optional[str] = Field(default_factory=lambda: os.getenv("MW_PASSWORD"), alias="MW_PASSWORD")
    mw_headless: bool = Field(default_factory=lambda: os.getenv("MW_HEADLESS", "true").lower() == "true", alias="MW_HEADLESS")
    browser_timeout_ms: int = Field(default_factory=lambda: int(os.getenv("BROWSER_TIMEOUT_MS", "25000")), alias="BROWSER_TIMEOUT_MS")

    @field_validator("mw_game_slug", mode="before")
    @classmethod
    def parse_slug_from_input(cls, v: str) -> str:
        if not v:
            return "bayonne-high-school-fall-2026-stock-market-game"
        # If user pasted a full URL, e.g. https://www.marketwatch.com/games/my-game/portfolio?pub=xyz
        match = re.search(r"/games/([^/?#]+)", v)
        if match:
            return match.group(1).strip()
        # Clean slug
        clean = re.sub(r"[^a-zA-Z0-9_-]", "", v).strip()
        return clean or "bayonne-high-school-fall-2026-stock-market-game"

    @property
    def mw_base_url(self) -> str:
        return f"https://www.marketwatch.com/games/{self.mw_game_slug}"

    @property
    def user_data_path(self) -> Path:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return USER_DATA_DIR

settings = Settings()
