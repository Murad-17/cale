"""A separate, always-on-top ORION WebView process anchored above other apps.

The dashboard keeps its own GUI process. Only bounded window operations are
exposed to this trusted local panel; AI and update actions use the local API.
"""
import json
import math
import os
import threading
import time
from pathlib import Path

from orion_companion import LocalClient

SIZES = {"home": (680, 212), "chat": (560, 920), "update": (650, 276),
         "notes": (650, 480), "settings": (620, 520), "peek": (284, 48), "greeting": (440, 208), "brain": (700, 740)}
PANEL_RADIUS = 26
ANIMATION_FPS = 60
ANIMATION_SECONDS = .24


def geometry(mode, bounds, center=None, top=None):
    if mode not in SIZES:
        raise ValueError("Panel rejimi düzgün deyil.")
    left, upper, right, bottom = bounds
    width, height = SIZES[mode]
    if mode == "chat":
        height = min(height, bottom - upper - 40)
        if center is None:
            center = right - min(width, right - left - 24) / 2 - 24
        if top is None:
            top = upper + 20
    width, height = min(width, max(280, right - left - 24)), min(height, max(60, bottom - upper - 24))
    center = (left + right) / 2 if center is None else center
    top = upper + 14 if top is None else top
    x = max(left + 12, min(round(center - width / 2), right - width - 12))
    y = upper if mode == "peek" else max(upper + 14, min(round(top), bottom - height - 12))
    return width, height, x, y


def round_windows_window(window, mode="home"):
    if os.name != "nt":
        return False
    from panel_window import apply_surface
    return apply_surface(window, mode)


def _webview_control(native):
    from panel_window import browser_control
    return browser_control(native)


def set_window_bounds(window, width, height, x, y):
    """One GUI operation per frame instead of separate resize/move/clip calls."""
    if os.name == 'nt':
        try:
            from System import Boolean, Func
            native = window.native
            def apply():
                if native.IsDisposed or not native.IsHandleCreated:
                    return False
                # Use pywebview's logical-to-physical scale for its geometry.
                # CSS surface scale is separate and only controls corner masks.
                scale = float(getattr(native, '_scale', 0) or getattr(native, 'DeviceDpi', 96) / 96)
                native.SetBounds(round(x * scale), round(y * scale),
                                 round(width * scale), round(height * scale))
                return True
            applied = bool(native.Invoke(Func[Boolean](apply))) if native.InvokeRequired else apply()
            if applied:
                return
        except Exception:
            pass
    window.resize(width, height)
    window.move(x, y)


class PanelAPI:
    def __init__(self, url, state_file, bounds):
        self._client = LocalClient(url)
        self._state_file = Path(state_file)
        self._bounds = tuple(bounds)
        self._window = None
        self._lock = threading.RLock()
        self._closed = threading.Event()
        self._mode = "home"
        self._animating = False
        self._generation = 0
        self._save_timer = None
        self._compact_position = None

    def _attach(self, window):
        self._window = window

    def surface(self, viewport_width, viewport_height, pixel_ratio=1, shape=None):
        """Match native clipping to the measured CSS viewport after WebView resize."""
        for value in (viewport_width, viewport_height, pixel_ratio):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Pəncərə ölçüsü düzgün deyil.')
        if not 100 <= viewport_width <= 10000 or not 24 <= viewport_height <= 10000 or not .5 <= pixel_ratio <= 5:
            raise ValueError('Pəncərə ölçüsü düzgün deyil.')
        if shape is not None:
            if not isinstance(shape, dict):
                raise ValueError('Panel sərhədi düzgün deyil.')
            for key in ('left', 'top', 'right', 'bottom', 'radius'):
                value = shape.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 128:
                    raise ValueError('Panel sərhədi düzgün deyil.')
            if shape['left']+shape['right'] >= viewport_width or shape['top']+shape['bottom'] >= viewport_height:
                raise ValueError('Panel sərhədi boşdur.')
            background = shape.get('background', '')
            if not isinstance(background, str) or len(background) != 7 or background[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in background[1:]):
                raise ValueError('Panel rəngi düzgün deyil.')
        window = self._window
        if os.name != 'nt' or window is None:
            return {'ok': True, 'native_clip': False}
        if self._animating:
            return {'ok': True, 'native_clip': bool(getattr(window, '_orion_surface_verified', False)), 'pending': True}
        try:
            from System import Boolean, Func
            native = window.native
            def measure():
                control = _webview_control(native) or native
                sx = float(control.ClientSize.Width) / viewport_width
                sy = float(control.ClientSize.Height) / viewport_height
                if not .5 <= sx <= 5 or abs(sx - sy) > .15:
                    return False  # A resize is still in flight; the observer retries.
                window._orion_surface_scale = (sx + sy) / 2
                if shape is not None:
                    window._orion_panel_insets = {k: shape[k] for k in ('left', 'top', 'right', 'bottom', 'radius')}
                    window._orion_shape_mode = self._mode
                    window.background_color = background
                return True
            measured = bool(native.Invoke(Func[Boolean](measure))) if native.InvokeRequired else measure()
            if measured:
                round_windows_window(window, self._mode)
            else:
                return {'ok': True, 'pending': True, 'native_clip': False}
        except Exception:
            round_windows_window(window, self._mode)
        status = getattr(window, '_orion_native_status', {})
        try:
            target = self._state_file.with_name('panel-window-status.json')
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temporary, target)
        except OSError:
            pass
        clipped = bool(getattr(window, '_orion_surface_verified', False))
        interactive = bool(getattr(window, '_orion_input_verified', False))
        backdrop_disabled = status.get('dwm', {}).get('backdrop_disabled')
        return {'ok': clipped and interactive and backdrop_disabled is not False,
                'native_clip': clipped, 'interactive': interactive, 'backdrop_disabled': backdrop_disabled}

    def layout(self, mode, reduced=False, content_height=None):
        if mode not in SIZES or type(reduced) is not bool:
            raise ValueError("Panel ölçüsü düzgün deyil.")
        if content_height is not None and (type(content_height) is not int or mode != "update"):
            raise ValueError("Panel hündürlüyü düzgün deyil.")
        with self._lock:
            window = self._window
            center = window.x + window.width / 2
            top = window.y
            if mode == "chat" and self._mode != "chat":
                if self._compact_position is None:
                    self._compact_position = (center, top)
                center = top = None
            elif mode in ("home", "peek") and self._compact_position:
                center, top = self._compact_position
                self._compact_position = None
            width, height, x, y = geometry(mode, self._bounds, center, top)
            if content_height is not None:
                height = min(max(200, min(380, content_height)), self._bounds[3] - self._bounds[1] - 24)
                y = max(self._bounds[1] + 10, min(y, self._bounds[3] - height - 12))
            if not self._animating and self._mode == mode and window.width == width and window.height == height and window.x == x and window.y == y:
                round_windows_window(window, mode)
                return {"ok": True, "width": width, "height": height}
            self._generation += 1
            generation = self._generation
            start_w, start_h, start_x, start_y = window.width, window.height, window.x, window.y
            self._mode = mode
            self._animating = True
            window._orion_surface_mode = mode
        # Install synchronous native resize masks before starting the motion.
        if os.name == 'nt':
            round_windows_window(window, mode)
        started = time.perf_counter()
        deadline = started
        while True:
            if self._closed.is_set() or generation != self._generation:
                return {"ok": False}
            elapsed = time.perf_counter() - started
            progress = 1 if reduced else min(1, elapsed / ANIMATION_SECONDS)
            t = 1 - (1 - progress) ** 3
            w, h = round(start_w + (width - start_w) * t), round(start_h + (height - start_h) * t)
            px, py = round(start_x + (x - start_x) * t), round(start_y + (y - start_y) * t)
            set_window_bounds(window, w, h, px, py)
            if progress >= 1:
                break
            # Missed deadlines are skipped; a slow frame never stretches a
            # 240ms transition into eleven expensive frames plus eleven sleeps.
            deadline += 1 / ANIMATION_FPS
            now = time.perf_counter()
            if deadline < now:
                deadline += (math.floor((now - deadline) * ANIMATION_FPS) + 1) / ANIMATION_FPS
            self._closed.wait(max(0, min(deadline - now, ANIMATION_SECONDS - (now - started))))
        with self._lock:
            if generation != self._generation:
                return {"ok": False}
            round_windows_window(window, mode)
            self._animating = False
        self._save_position()
        return {"ok": True, "width": width, "height": height}

    def recenter(self):
        width, height, x, y = geometry(self._mode, self._bounds)
        self._window.move(x, y)
        self._save_position()
        return {"ok": True}

    def _save_position(self, *_):
        if self._closed.is_set() or self._animating or self._window is None:
            return
        with self._lock:
            try:
                self._state_file.parent.mkdir(parents=True, exist_ok=True)
                center, top = self._compact_position or (self._window.x + self._window.width / 2, self._window.y)
                value = {"version": 3, "center": center, "top": top, "collapsed": self._mode == "peek"}
                temp = self._state_file.with_suffix(".tmp")
                temp.write_text(json.dumps(value), encoding="utf-8")
                os.replace(temp, self._state_file)
            except OSError:
                pass

    def _moved(self, *_):
        if self._animating:
            return
        if self._save_timer:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(.25, self._settle_position)
        self._save_timer.daemon = True
        self._save_timer.start()

    def _settle_position(self):
        if self._closed.is_set() or self._animating or self._window is None:
            return
        # Native dragging also works when the pointer has left the WebView.
        # Snap only after movement stops; a normal launch at y=14 stays open.
        upper = self._bounds[1]
        action = "dockTop" if self._mode != "peek" and self._window.y <= upper + 6 else (
            "expandDock" if self._mode == "peek" and self._window.y > upper + 40 else None)
        if action:
            try:
                self._window.evaluate_js("window.ORIONPanel && window.ORIONPanel." + action + "()")
            except Exception:
                pass
        self._save_position()

    def close_panel(self):
        self._save_position()
        self._closed.set()
        self._generation += 1
        self._window.destroy()
        return {"ok": True}

    def ready(self):
        round_windows_window(self._window, self._mode)
        return {"native": True, "on_top": True, "mode": self._mode}

    def _resized(self, *_):
        # Native SizeChanged already maintains masks during an animation. The
        # public pywebview event runs on worker threads, so do not enqueue the
        # same expensive GUI work again for every intermediate size.
        if not self._animating and not self._closed.is_set():
            round_windows_window(self._window, self._mode)


def run(url, state_file):
    import webview
    client = LocalClient(url)  # Reject non-local application URLs before creating a window.
    screen = webview.screens[0]
    bounds = (screen.x, screen.y, screen.x + screen.width, screen.y + screen.height)
    center = top = None
    initial_mode = "home"
    try:
        saved = json.loads(Path(state_file).read_text(encoding="utf-8"))
        if saved.get("version") in (2, 3):
            center, top = float(saved["center"]), float(saved["top"])
            if not math.isfinite(center) or not math.isfinite(top):
                center = top = None
            if saved.get("collapsed") is True:
                initial_mode = "peek"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    width, height, x, y = geometry(initial_mode, bounds, center, top)
    api = PanelAPI(url, state_file, bounds)
    api._mode = initial_mode
    background = "#f5f3f6"
    try:
        background = client.request("/api/panel/appearance")["background"]
    except (ValueError, KeyError, ConnectionError):
        pass
    if os.name == 'nt':
        # An opaque initial surface avoids both transparency regressions and
        # stale inherited alpha=0 configuration before WebView2's first paint.
        os.environ['WEBVIEW2_DEFAULT_BACKGROUND_COLOR'] = 'FF'+background[1:].upper()
    window = webview.create_window(
        "ORION — Üst chatbot paneli", url.rstrip("/") + "/panel", js_api=api,
        width=width, height=height, x=x, y=y, min_size=(160, 34),
        frameless=True, easy_drag=False, on_top=True, resizable=False,
        shadow=os.name != "nt", background_color=background, text_select=True,
        transparent=os.name != "nt", zoomable=False, focus=True,
    )
    api._attach(window)
    # BrowserForm enables a system Mica backdrop during construction. Remove
    # it synchronously before the first visible frame, then retain the normal
    # post-load/resize masks for CSS geometry and DPI changes.
    window.events.before_show += lambda: round_windows_window(window, api._mode)
    window.events.shown += lambda: round_windows_window(window, api._mode)
    window.events.loaded += lambda: round_windows_window(window, api._mode)
    window.events.resized += api._resized
    window.events.moved += api._moved
    window.events.closed += api._closed.set
    try:
        webview.start(private_mode=False, storage_path=str(Path(state_file).parent / "top-panel-webview"))
    finally:
        api._closed.set()
        if api._save_timer:
            api._save_timer.cancel()
