"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Mobile QR Code Camera Pairing Helper
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
import socket
from ..core.logger import console

def get_local_ip() -> str:
    """Discovers the active local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

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

    console.print("\n[bold yellow]💡 Pro Tip:[/bold yellow] [dim]On your phone, tap 'Share' -> 'Add to Home Screen' to run it as a full-screen native app![/dim]\n")
