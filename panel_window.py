"""Opaque, interactive WinForms host with one authoritative native outline.

WebView2 paints with DirectComposition. A Form color key can therefore make its
whole input surface click-through even while Chromium remains visible. Never
use layered/color-key transparency here: exclude only the rounded corners with
the outer HWND region, mapped from the actual WebView client coordinates.

The shipped pywebview BrowserForm also enables a *separate* Windows Mica
backdrop on dark system themes. A successful HWND mask does not establish
that this DWM material is off. Explicitly disable and read back that backdrop,
including after the framework's system-theme refresh.
"""
import ctypes
from ctypes import wintypes

REVISION = 'no-system-backdrop-20261023'
INPUT_FLAGS = 0x80000 | 0x20 | 0x08000000  # layered, transparent, no-activate


class Margins(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int) for name in ('left', 'right', 'top', 'bottom')]


def handle(control):
    value = control.Handle
    return int(value.ToInt64()) if hasattr(value, 'ToInt64') else int(value)


def browser_control(native):
    return getattr(native, 'webview', None) or getattr(getattr(native, 'browser', None), 'webview', None)


class Win32:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.gdi = ctypes.WinDLL('gdi32', use_last_error=True)
        self.get_style = getattr(self.user, 'GetWindowLongPtrW', self.user.GetWindowLongW)
        self.set_style = getattr(self.user, 'SetWindowLongPtrW', self.user.SetWindowLongW)
        self.get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        self.get_style.restype = ctypes.c_ssize_t
        self.set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self.set_style.restype = ctypes.c_ssize_t
        self.user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
        self.user.GetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN]
        self.user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user.EnableWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
        self.user.WindowFromPoint.argtypes = [wintypes.POINT]
        self.user.WindowFromPoint.restype = wintypes.HWND
        self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user.GetAncestor.restype = wintypes.HWND
        self.gdi.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
        self.gdi.CreateRoundRectRgn.restype = wintypes.HRGN
        self.gdi.CreateRectRgn.argtypes = [ctypes.c_int] * 4
        self.gdi.CreateRectRgn.restype = wintypes.HRGN
        self.gdi.CombineRgn.argtypes = [wintypes.HRGN, wintypes.HRGN, wintypes.HRGN, ctypes.c_int]
        self.gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        self.gdi.PtInRegion.argtypes = [wintypes.HRGN, ctypes.c_int, ctypes.c_int]
        self.gdi.PtInRegion.restype = wintypes.BOOL
        self.framed = {}

    def interactive(self, root, child):
        for hwnd in set((root, child)):
            before = int(self.get_style(hwnd, -20)) & 0xffffffff
            after = before & ~INPUT_FLAGS
            if after != before:
                self.set_style(hwnd, -20, after)
                # Do not activate, move, resize or change always-on-top order.
                self.user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x37)
            self.user.EnableWindow(hwnd, True)
            if int(self.get_style(hwnd, -20)) & INPUT_FLAGS:
                return False
        return True

    def remove_frame(self, root, force=False):
        if root in self.framed and not force:
            return self.framed[root]
        status = dict(self.framed.get(root, {}))
        status.update(backdrop_supported=False, backdrop_current=None, backdrop_disabled=None)
        try:
            dwm = ctypes.WinDLL('dwmapi', use_last_error=True)
            setter, getter = dwm.DwmSetWindowAttribute, dwm.DwmGetWindowAttribute
            for fn in (setter, getter):
                fn.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
                fn.restype = ctypes.c_int32  # HRESULT is 32-bit, including on Win64.
            before = wintypes.DWORD()
            before_hr = int(getter(root, 38, ctypes.byref(before), ctypes.sizeof(before)))
            if before_hr == 0:
                status.setdefault('backdrop_initial', int(before.value))
            # DWMWA_SYSTEMBACKDROP_TYPE=38, DWMSBT_NONE=1 is essential here.
            # BrowserForm.update_title_bar_theme otherwise paints Mica across
            # the entire rectangle, even with a verified rounded HWND region.
            results = {}
            for attribute, value in ((38, 1), (2, 1), (33, 1), (34, 0xfffffffe)):
                argument = wintypes.DWORD(value)
                results[str(attribute)] = int(setter(root, attribute, ctypes.byref(argument), ctypes.sizeof(argument)))
            status['set_hresult'] = results
            after = wintypes.DWORD()
            read_hr = int(getter(root, 38, ctypes.byref(after), ctypes.sizeof(after)))
            status['read_hresult'] = read_hr
            status['backdrop_supported'] = read_hr == 0
            if read_hr == 0:
                status['backdrop_current'] = int(after.value)
                status['backdrop_disabled'] = after.value == 1
            # Remove any inherited glass-frame extension as well. The panel
            # draws its own surface and border and needs no DWM frame inset.
            extend = dwm.DwmExtendFrameIntoClientArea
            extend.argtypes = [wintypes.HWND, ctypes.POINTER(Margins)]
            extend.restype = ctypes.c_int32
            margins = Margins(0, 0, 0, 0)
            status['extend_hresult'] = int(extend(root, ctypes.byref(margins)))
        except (AttributeError, OSError) as error:
            # Windows 10 lacks system-backdrop attributes. A missing optional
            # DWM API must never prevent the interactive native region.
            status['error'] = type(error).__name__+': '+str(error)[:250]
        self.framed[root] = status
        return status

    def bounds(self, root, child, insets, scale):
        outer, client, origin = wintypes.RECT(), wintypes.RECT(), wintypes.POINT()
        if not (self.user.GetWindowRect(root, ctypes.byref(outer))
                and self.user.GetClientRect(child, ctypes.byref(client))
                and self.user.ClientToScreen(child, ctypes.byref(origin))):
            raise OSError('Pəncərənin real sərhədi oxunmadı.')
        x, y = origin.x-outer.left, origin.y-outer.top
        l, t = x+round(insets.get('left', 0)*scale), y+round(insets.get('top', 0)*scale)
        r = x+client.right-round(insets.get('right', 0)*scale)
        b = y+client.bottom-round(insets.get('bottom', 0)*scale)
        # Bound the mask to this window even during a monitor/DPI transition.
        l, t = max(0, l), max(0, t)
        r, b = min(outer.right-outer.left, r), min(outer.bottom-outer.top, b)
        if r-l < 4 or b-t < 4:
            raise ValueError('Pəncərə sərhədi boşdur.')
        return l, t, r, b

    def clip(self, root, bounds, radius, peek=False):
        l, t, r, b = bounds
        diameter = min(max(2, round(2*radius)), r-l, b-t)
        region = self.gdi.CreateRoundRectRgn(l, t, r, b, diameter, diameter)
        if not region:
            return False
        if peek:
            upper = self.gdi.CreateRectRgn(l, t, r, t+diameter//2+1)
            if not upper:
                self.gdi.DeleteObject(region)
                return False
            combined = self.gdi.CombineRgn(region, region, upper, 2)
            self.gdi.DeleteObject(upper)
            if not combined:
                self.gdi.DeleteObject(region)
                return False
        if not self.user.SetWindowRgn(root, region, True):
            self.gdi.DeleteObject(region)
            return False
        # The OS owns region now. Verify a different copy, including every
        # corner and the center where real buttons receive mouse input.
        copy = self.gdi.CreateRectRgn(0, 0, 0, 0)
        if not copy:
            return False
        try:
            if self.user.GetWindowRgn(root, copy) <= 0:
                return False
            points = [(l, b-1, False), (r-1, b-1, False),
                      (l, t, peek), (r-1, t, peek),
                      ((l+r)//2, (t+b)//2, True)]
            return all(bool(self.gdi.PtInRegion(copy, x, y)) == expected for x, y, expected in points)
        finally:
            self.gdi.DeleteObject(copy)

    def pointer_owner(self, root, bounds):
        rect = wintypes.RECT()
        if not self.user.GetWindowRect(root, ctypes.byref(rect)):
            return None
        l, t, r, b = bounds
        point = wintypes.POINT(rect.left+(l+r)//2, rect.top+(t+b)//2)
        hit = self.user.WindowFromPoint(point)
        return bool(hit and (hit == root or self.user.GetAncestor(hit, 2) == root))


class Surface:
    def __init__(self, window):
        self.window = window
        self.win32 = Win32()
        self.busy = False
        self.configured = None
        self.background = None
        self.stamp = None
        self.hooks = []
        self.theme_hook = None
        self.theme_hook_error = None

    def guard_system_theme(self, native):
        if self.theme_hook is not None:
            return
        original = getattr(native, 'update_title_bar_theme', None)
        if not callable(original):
            return
        def update(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            finally:
                if not native.IsDisposed and native.IsHandleCreated:
                    status = self.win32.remove_frame(handle(native), force=True)
                    # Preserve the actual DWM read-back after system theme
                    # changes, without changing focus, geometry or input.
                    if hasattr(self.window, '_orion_native_status'):
                        self.window._orion_native_status['dwm'] = status
        try:
            # BrowserForm is a Python subclass; its system-theme event calls
            # this Python method. Scope the override to this panel instance.
            native.update_title_bar_theme = update
            self.theme_hook = update
        except (AttributeError, TypeError) as error:
            self.theme_hook_error = str(error)[:250]

    def apply(self, mode, force=False):
        if self.busy:
            return False
        self.busy = True
        window, native = self.window, self.window.native
        try:
            if native.IsDisposed or not native.IsHandleCreated:
                return False
            from System.Drawing import Color, ColorTranslator
            browser = browser_control(native)
            root, child = handle(native), handle(browser) if browser is not None else handle(native)
            controls = (root, child)
            if self.configured != controls:
                # Clear the previous color key before disabling layered mode.
                native.TransparencyKey = Color.Empty
                native.AllowTransparency = False
                native.Opacity = 1.0
                for control in (native, browser):
                    if control is None:
                        continue
                    previous = control.Region
                    control.Region = None
                    if previous is not None:
                        previous.Dispose()
                    control.Enabled = True
                if browser is not None:
                    browser.TabStop = True
                root, child = handle(native), handle(browser) if browser is not None else handle(native)
                self.configured, self.stamp = (root, child), None
                self.background = None
            background = getattr(window, 'background_color', '#100d1c')
            if self.background != background:
                color = ColorTranslator.FromHtml(background)  # Opaque, no key.
                native.BackColor = color
                if browser is not None:
                    browser.DefaultBackgroundColor = color
                self.background = background
            self.guard_system_theme(native)
            if not self.hooks:
                def changed(*_):
                    self.apply(getattr(window, '_orion_surface_mode', mode))
                def recreated(*_):
                    self.configured = self.background = self.stamp = None
                    window._orion_surface_scale = None
                    changed()
                for control in (native, browser):
                    if control is None:
                        continue
                    for name, callback in (('SizeChanged', changed), ('HandleCreated', recreated), ('DpiChanged', recreated)):
                        if hasattr(control, name):
                            event = getattr(control, name)
                            event += callback
                            setattr(control, name, event)
                            self.hooks.append((control, name, callback))
            interactive = self.win32.interactive(root, child)
            dwm_status = self.win32.remove_frame(root, force=force)
            scale = getattr(window, '_orion_surface_scale', None) or max(.5, float(getattr(native, 'DeviceDpi', 96))/96)
            insets = getattr(window, '_orion_panel_insets', {})
            bounds = self.win32.bounds(root, child, insets, scale)
            measured_radius = insets.get('radius', 26) if getattr(window, '_orion_shape_mode', mode) == mode else 26
            radius = (15 if mode == 'peek' else measured_radius)*scale
            stamp = (root, bounds, radius, mode)
            if force or stamp != self.stamp:
                window._orion_surface_verified = self.win32.clip(root, bounds, radius, mode == 'peek')
                self.stamp = stamp if window._orion_surface_verified else None
            window._orion_input_verified = interactive
            # WindowFromPoint may consult the Chromium child process. Check it
            # after a settled layout, not on every intermediate animation size.
            pointer_owner = (self.win32.pointer_owner(root, bounds) if force else
                             getattr(window, '_orion_native_status', {}).get('pointer_owner'))
            window._orion_native_status = {'revision': REVISION, 'mode': mode, 'clip': bool(getattr(window, '_orion_surface_verified', False)),
                                            'interactive': interactive, 'bounds': list(bounds), 'scale': scale, 'color_key': False,
                                            'pointer_owner': pointer_owner, 'dwm': dwm_status,
                                            'system_theme_guard': self.theme_hook is not None}
            if self.theme_hook_error:
                window._orion_native_status['system_theme_guard_error'] = self.theme_hook_error
            clean = dwm_status.get('backdrop_disabled') is not False
            window._orion_native_status['surface_clean'] = bool(window._orion_surface_verified and clean)
            return bool(window._orion_surface_verified and interactive and clean)
        except Exception as error:
            window._orion_surface_verified = False
            window._orion_native_status = {'revision': REVISION, 'mode': mode, 'clip': False,
                                            'error': type(error).__name__+': '+str(error)[:400]}
            return False
        finally:
            self.busy = False


def apply_surface(window, mode):
    """Run all WinForms access and native shaping on the owning GUI thread."""
    try:
        from System import Boolean, Func
        native = window.native
        window._orion_surface_mode = mode
        def apply():
            surface = getattr(window, '_orion_native_surface', None)
            if surface is None:
                surface = window._orion_native_surface = Surface(window)
            return surface.apply(mode, force=True)
        return bool(native.Invoke(Func[Boolean](apply))) if native.InvokeRequired else bool(apply())
    except Exception as error:
        window._orion_surface_verified = False
        window._orion_native_status = {'revision': REVISION, 'mode': mode, 'clip': False,
                                        'error': type(error).__name__+': '+str(error)[:400]}
        return False
