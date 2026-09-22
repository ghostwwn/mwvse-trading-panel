"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Mobile QR Code Camera Pairing Helper
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import socket
import platform
import subprocess
from ..core.logger import console

def get_local_ip() -> str:
    """Discovers the active physical local LAN IP address (Wi-Fi/Ethernet), ignoring VPN tunnels."""
    # 1. macOS specific: query physical adapters (en0 is Wi-Fi, en1/en2/en3 are Ethernet/Hotspot)
    if platform.system() == "Darwin":
        for iface in ["en0", "en1", "en2", "en3", "en4"]:
            try:
                out = subprocess.check_output(["ipconfig", "getifaddr", iface], text=True, stderr=subprocess.DEVNULL).strip()
                if out and not out.startswith("127.") and not out.startswith("172.16.0."):
                    return out
            except Exception:
                pass

    # 2. Cross-platform socket discovery (filtering out virtual VPN/tunnel adapters)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127.") and not ip.startswith("172.16.0."):
            return ip
    except Exception:
        pass

    # 3. Hostname fallback
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("172.16.0."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"

def print_mobile_qr(port: int = 8000):
    """Prints a clean ASCII QR Code and clickable LAN link for instant iPhone/Android pairing."""
    ip = get_local_ip()
    mobile_url = f"http://{ip}:{port}/mobile"

    console.print("\n[bold cyan]📱 MWVSE MOBILE STATION READY[/bold cyan]")
    console.print(f"[bold white]Mobile URL:[/bold white] [bold green]{mobile_url}[/bold green]")
    console.print("[dim]Point your iPhone or Android camera at the QR code below to connect instantly:[/dim]\n")

    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(mobile_url)
        qr.print_ascii(invert=True)
    except Exception:
        console.print(f"[yellow]Open on your phone:[/yellow] [bold underline cyan]{mobile_url}[/bold underline cyan]")

    console.print(f"\n[bold green]Direct Wi-Fi Link:[/bold green] [bold underline]{mobile_url}[/bold underline]")
    console.print("[bold yellow]💡 Pro Tip:[/bold yellow] [dim]Make sure your phone is connected to the same Wi-Fi.[/dim]")
    console.print("[dim]On your iPhone, tap 'Share' (square with arrow) -> 'Add to Home Screen' to install as a native PWA app![/dim]\n")

