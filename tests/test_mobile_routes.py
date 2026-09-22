"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Unit Tests: Mobile Routes & PWA Delivery
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from mwvse_panel.ui.web.app import app

client = TestClient(app)

def test_mobile_page_delivery():
    response = client.get("/mobile")
    assert response.status_code == 200
    assert "MWVSE Mobile" in response.text
    assert "apple-mobile-web-app-capable" in response.text
    assert "bottom-nav" in response.text

def test_manifest_delivery():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = response.json()
    assert data.get("display") == "standalone"
    assert data.get("short_name") == "MWVSE"

def test_user_agent_mobile_routing():
    # iPhone User-Agent
    headers = {"user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert "MWVSE Mobile" in response.text

def test_user_agent_desktop_routing():
    # Desktop Chrome User-Agent
    headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert "Trading Workstation" in response.text

if __name__ == "__main__":
    test_mobile_page_delivery()
    test_manifest_delivery()
    test_user_agent_mobile_routing()
    test_user_agent_desktop_routing()
    print("All mobile route tests passed!")
