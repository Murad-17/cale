"""Unified ORION entry point. Importing this module never starts input loops."""
import argparse
import os
import signal
import threading
import time
import webbrowser
from pathlib import Path
import config


def desktop(engine, server, url, companion=None):
    if companion and getattr(engine, "panel", None):
        engine.panel.controller = companion
    try:
        import webview
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        print("Masaüstü modulu qurulmayıb. Brauzer rejimi açılır; INSTALL.bat ilə desktop modullarını quraşdıra bilərsən.")
        webbrowser.open(url)
        engine.desktop_show = lambda: webbrowser.open(url)
        if companion:
            companion.start()
        return False
    icon_image = Image.new("RGBA", (64, 64), (7, 5, 15, 255))
    draw = ImageDraw.Draw(icon_image)
    draw.ellipse((13, 13, 51, 51), outline=(255, 151, 83), width=4)
    draw.arc((4, 22, 60, 43), 0, 340, fill=(244, 110, 46), width=3)
    window = webview.create_window("ORION — Şəxsi iş sahən", url, width=1380, height=900, min_size=(360, 600), hidden=getattr(engine, "panel_only", False))
    if getattr(engine, 'workspace', None):
        engine.workspace.opener = lambda key, relative: webview.create_window(
            'ORION — Ayrıca tab', url.rstrip('/') + relative,
            width=460, height=580, min_size=(320, 240), on_top=True, resizable=True)
    quitting = threading.Event()
    def show(*_):
        window.show()
        try:
            window.restore()
        except AttributeError:
            pass
    def listen(*_):
        try:
            engine.voice.activate()
        except ValueError:
            show()
    def quit_app(*_):
        quitting.set()
        if getattr(engine, 'workspace', None):
            engine.workspace.close_all()
        if getattr(engine, "exit_requested", None):
            engine.exit_requested.set()
        if companion:
            companion.stop()
        tray.stop()
        window.destroy()
    if getattr(engine, "updater", None):
        engine.updater.shutdown = quit_app
    engine.desktop_show = show
    menu = [pystray.MenuItem("ORION-u aç", show, default=True)]
    if companion:
        menu.extend([pystray.MenuItem("Üst chatbot panelini göstər", lambda *_: engine.panel.control("show")),
                     pystray.MenuItem("Üst chatbot panelini gizlət", companion.stop)])
    menu.extend([pystray.MenuItem("Səsli komanda ver", listen), pystray.MenuItem("Tam çıxış", quit_app)])
    tray = pystray.Icon("ORION", icon_image, "ORION arxa planda işləyir", menu=pystray.Menu(*menu))
    def closing():
        if not quitting.is_set():
            window.hide()
            return False
    window.events.closing += closing
    threading.Thread(target=tray.run, daemon=True).start()
    if companion:
        if getattr(engine, "updater", None):
            engine.updater.expect_top_panel()
        companion.start()
    try:
        webview.start(private_mode=False, storage_path=str(engine.store.directory / "webview"))
    finally:
        if companion:
            companion.stop()
        tray.stop()
    return True


def run():
    config.load_env()
    from engine import Engine
    from dashboard_bridge import start
    from voice_service import VoiceService
    parser = argparse.ArgumentParser(description="ORION şəxsi AI iş sahəsi")
    parser.add_argument("--browser", action="store_true", help="Brauzerdə aç")
    parser.add_argument("--desktop", action="store_true", help="Pəncərə və sistem paneli rejimi")
    parser.add_argument("--console", action="store_true", help="Terminaldan yazılı komanda ver")
    parser.add_argument("--no-companion", action="store_true", help="Ekran fiqurunu açma")
    parser.add_argument("--panel-only", action="store_true", help="Əsas pəncərəni gizli saxlayıb yalnız üst paneli aç")
    parser.add_argument("--port", type=int, default=int(os.environ.get("BRIDGE_PORT", "8765")))
    args = parser.parse_args()
    engine = Engine()
    engine.panel_only = args.panel_only
    import sys
    engine.updater.restart = [sys.executable, str(config.ROOT / "main.py"), *sys.argv[1:]]
    engine.updater.shutdown = engine.exit_requested.set if not args.console else None
    engine.voice = VoiceService(engine)
    try:
        server = start(args.port, engine)
    except OSError:
        print(f"{args.port} portu istifadədədir. Əvvəlki ORION serverini bağla və ya BRIDGE_PORT-u dəyiş.")
        engine.close()
        return 1
    engine.start_services()
    engine.voice.configure(bool(engine.settings.get("wakeEnabled")))
    url = f"http://127.0.0.1:{args.port}/"
    from orion_companion import CompanionProcess
    companion = CompanionProcess(url, engine.store.directory, enabled=not args.no_companion)
    engine.panel.controller = companion
    if companion.enabled:
        engine.updater.expect_top_panel()
    print("ORION hazırdır: " + url)
    print("Pəncərəni bağlamaq desktop rejimində ORION-u sistem panelində saxlayır. Tam çıxış üçün tray menyusunu istifadə et.")
    try:
        if args.console:
            while True:
                text = input("Sən: ").strip()
                if text.casefold() in ("cix", "çıx", "exit"):
                    break
                if text:
                    try:
                        result = engine.submit(text)
                        while True:
                            job = next(j for j in engine.store.jobs() if j["id"] == result["job_id"])
                            if job["status"] in ("completed", "failed"):
                                print("ORION:", job["result"].get("reply", job["result"].get("error")))
                                break
                            time.sleep(.2)
                    except Exception as error:
                        print("Xəta:", str(error))
        elif not args.browser and desktop(engine, server, url, companion):
            pass
        else:
            if args.browser:
                engine.desktop_show = lambda: webbrowser.open(url)
                webbrowser.open(url)
                companion.start()
            while not engine.exit_requested.is_set():
                time.sleep(.5)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        companion.stop()
        engine.close()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
