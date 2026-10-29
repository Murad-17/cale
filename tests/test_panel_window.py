"""Exercise real mask/style logic against an in-memory Win32 API model.

The model implements region containment and OS region ownership instead of
returning success unconditionally. A physical Windows desktop is not present.
"""
import copy
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from panel_window import Win32, INPUT_FLAGS, apply_surface


class Event:
    def __init__(self): self.handlers=[]
    def __iadd__(self, callback): self.handlers.append(callback); return self
    def fire(self):
        for callback in self.handlers: callback()


class WindowsModel:
    def __init__(self, scale=1, inset=0):
        self.scale, self.inset = scale, inset
        self.width,self.height=round(680*scale),round(212*scale)
        self.left,self.top=620,14
        self.styles={1:INPUT_FLAGS|8,2:0x20}
        self.enabled={1:False,2:False}
        self.pool,self.owned,self.region={},set(),None
        self.next=100
        self.user,self.gdi,self.dwm=Mock(),Mock(),Mock()
        # Bundled pywebview enables DWMSBT_MAINWINDOW on dark Windows themes,
        # independently of transparent=False and shadow=False. This DWM layer
        # is separate from the region-clipped client content.
        self.backdrop_supported=True
        self.dwm_attributes={38:2}
        self.dwm.DwmSetWindowAttribute.side_effect=self.set_dwm
        self.dwm.DwmGetWindowAttribute.side_effect=self.get_dwm
        self.dwm.DwmExtendFrameIntoClientArea.return_value=0
        self.user.GetWindowLongPtrW.side_effect=lambda hwnd,index:self.styles[hwnd]
        self.user.SetWindowLongPtrW.side_effect=self.style
        self.user.EnableWindow.side_effect=lambda hwnd,value:self.enabled.__setitem__(hwnd,value)
        self.user.GetWindowRect.side_effect=self.outer
        self.user.GetClientRect.side_effect=self.client
        self.user.ClientToScreen.side_effect=self.origin
        self.user.SetWindowRgn.side_effect=self.assign
        self.user.GetWindowRgn.side_effect=self.copy_region
        self.user.WindowFromPoint.side_effect=self.hit
        self.user.GetAncestor.side_effect=lambda hwnd,flag:1 if hwnd in (1,2) else hwnd
        self.gdi.CreateRoundRectRgn.side_effect=self.rounded
        self.gdi.CreateRectRgn.side_effect=self.rectangle
        self.gdi.CombineRgn.side_effect=self.union
        self.gdi.PtInRegion.side_effect=lambda region,x,y:self.contains(self.pool[region],x,y)
        self.gdi.DeleteObject.side_effect=self.delete

    def dll(self, name, **_):return {'user32':self.user,'gdi32':self.gdi,'dwmapi':self.dwm}[name]
    def set_dwm(self, hwnd, attribute, argument, size):
        if attribute==38 and not self.backdrop_supported:return -2147024809
        self.dwm_attributes[attribute]=argument._obj.value;return 0
    def get_dwm(self, hwnd, attribute, argument, size):
        if attribute==38 and not self.backdrop_supported:return -2147024809
        argument._obj.value=self.dwm_attributes.get(attribute,0);return 0
    def style(self, hwnd, index, value):
        before=self.styles[hwnd];self.styles[hwnd]=value;return before
    def outer(self, hwnd, pointer):
        r=pointer._obj;r.left,r.top=self.left,self.top
        r.right,r.bottom=self.left+self.width+2*self.inset,self.top+self.height+2*self.inset;return 1
    def client(self, hwnd, pointer):
        r=pointer._obj;r.left=r.top=0;r.right,r.bottom=self.width,self.height;return 1
    def origin(self, hwnd, pointer):
        p=pointer._obj;p.x,p.y=self.left+self.inset,self.top+self.inset;return 1
    def allocate(self, shape):
        self.next+=1;self.pool[self.next]=shape;return self.next
    def rounded(self,l,t,r,b,dx,dy):return self.allocate(('round',l,t,r,b,dx/2))
    def rectangle(self,l,t,r,b):return self.allocate(('rect',l,t,r,b))
    def union(self,target,a,b,operation):
        self.pool[target]=('union',copy.deepcopy(self.pool[a]),copy.deepcopy(self.pool[b]));return 3
    def delete(self, region):
        assert region not in self.owned,'Windows owns an assigned region'
        self.pool.pop(region);return 1
    def assign(self, hwnd, region, redraw):
        if self.region:self.owned.remove(self.region);self.pool.pop(self.region)
        self.region=region;self.owned.add(region);return 1
    def copy_region(self, hwnd, target):
        if self.region is None:return 0
        self.pool[target]=copy.deepcopy(self.pool[self.region]);return 3
    def contains(self, shape, x, y):
        if shape[0]=='union':return self.contains(shape[1],x,y) or self.contains(shape[2],x,y)
        _,l,t,r,b,*extra=shape
        if not l<=x<r or not t<=y<b:return False
        if not extra:return True
        radius=extra[0];px,py=x+.5,y+.5
        cx=max(l+radius,min(r-radius,px));cy=max(t+radius,min(b-radius,py))
        return (px-cx)**2+(py-cy)**2<=radius**2
    def hit(self, point):
        if self.styles[1]&INPUT_FLAGS or not self.enabled[1] or self.region is None:return 999
        return 2 if self.contains(self.pool[self.region],point.x-self.left,point.y-self.top) else 999


class Control:
    def __init__(self, owner, hwnd):
        self.owner,self.hwnd=owner,hwnd
        self.Region=Mock();self.Enabled=False;self.IsDisposed=False;self.IsHandleCreated=True
        self.SizeChanged,self.HandleCreated,self.DpiChanged=Event(),Event(),Event()
    @property
    def Handle(self):
        assert self.owner.inside,'native controls must be accessed on their GUI thread'
        return self.hwnd


class Native(Control):
    InvokeRequired=True
    def __init__(self, model):
        self.inside=False;self.model=model;self.invocations=0
        super().__init__(self,1)
        self.webview=Control(self,2)
        self.TransparencyKey='old-key';self.AllowTransparency=True;self.Opacity=.5
        self.dark=True
    def update_title_bar_theme(self):
        # Same side effect as the shipped BrowserForm method. Framework theme
        # notifications call this again after the HWND has already been masked.
        self.model.dwm_attributes[20]=int(self.dark)
        self.model.dwm_attributes[38]=2 if self.dark else 1
    @property
    def DeviceDpi(self):
        assert self.inside;return 96  # Deliberately differs from measured CSS scale.
    def Invoke(self, callback):
        self.invocations+=1;self.inside=True
        try:return callback()
        finally:self.inside=False
    def resize(self,w,h):
        def apply():
            self.model.width,self.model.height=w,h
            self.SizeChanged.fire();self.webview.SizeChanged.fire()
        self.Invoke(apply)


class Func:
    def __class_getitem__(cls,item):return lambda callback:callback


MODULES={'System':SimpleNamespace(Boolean=bool,Func=Func),
         'System.Drawing':SimpleNamespace(Color=SimpleNamespace(Empty='empty'),ColorTranslator=SimpleNamespace(FromHtml=lambda value:value))}


class WindowTests(unittest.TestCase):
    def test_successful_window_mask_also_removes_the_separate_mica_backdrop(self):
        model=WindowsModel();native=Native(model)
        window=SimpleNamespace(native=native,background_color='#100d1c')
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertTrue(apply_surface(window,'home'))
        self.assertEqual(model.dwm_attributes[38],1)
        self.assertEqual(window._orion_native_status['dwm']['backdrop_initial'],2)
        self.assertEqual(window._orion_native_status['dwm']['backdrop_current'],1)
        self.assertTrue(window._orion_native_status['dwm']['backdrop_disabled'])
        margins=model.dwm.DwmExtendFrameIntoClientArea.call_args.args[1]._obj
        self.assertEqual([getattr(margins,k) for k in ('left','right','top','bottom')],[0,0,0,0])

    def test_windows_theme_refresh_cannot_restore_mica_behind_the_rounded_panel(self):
        model=WindowsModel();native=Native(model)
        window=SimpleNamespace(native=native,background_color='#100d1c')
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertTrue(apply_surface(window,'home'))
            for dark in (False,True,True,False,True):
                native.dark=dark
                native.Invoke(native.update_title_bar_theme)
                self.assertEqual(model.dwm_attributes[20],int(dark))
                self.assertEqual(model.dwm_attributes[38],1)
                self.assertTrue(window._orion_native_status['dwm']['backdrop_disabled'])
            # Geometry changes keep the mask current without DWM calls on each
            # animation frame. The settled call and theme events reassert it.
            calls=model.dwm.DwmSetWindowAttribute.call_count
            native.resize(680,240);native.resize(680,260)
            self.assertEqual(model.dwm.DwmSetWindowAttribute.call_count,calls)
            self.assertTrue(window._orion_native_status['clip'])
            self.assertTrue(window._orion_native_status['interactive'])

    def test_windows_10_without_system_backdrop_api_keeps_rounded_clickable_host(self):
        model=WindowsModel();model.backdrop_supported=False;native=Native(model)
        window=SimpleNamespace(native=native,background_color='#100d1c')
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertTrue(apply_surface(window,'home'))
        self.assertTrue(window._orion_native_status['clip'])
        self.assertTrue(window._orion_native_status['interactive'])
        self.assertFalse(window._orion_native_status['dwm']['backdrop_supported'])
        self.assertIsNone(window._orion_native_status['dwm']['backdrop_disabled'])

    def test_rejected_backdrop_change_is_not_reported_as_a_clean_surface(self):
        model=WindowsModel();native=Native(model)
        def reject(hwnd, attribute, argument, size):
            return -2147024891 if attribute==38 else model.set_dwm(hwnd,attribute,argument,size)
        model.dwm.DwmSetWindowAttribute.side_effect=reject
        window=SimpleNamespace(native=native,background_color='#100d1c')
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertFalse(apply_surface(window,'home'))
        status=window._orion_native_status
        self.assertTrue(status['clip']);self.assertTrue(status['interactive'])
        self.assertFalse(status['surface_clean'])
        self.assertEqual(status['dwm']['backdrop_current'],2)
        self.assertFalse(status['dwm']['backdrop_disabled'])

    def test_native_region_removes_every_gray_corner_and_center_receives_input(self):
        for scale in (1,1.25,1.5,2):
            with self.subTest(scale=scale):
                model=WindowsModel(scale,inset=8);native=Native(model)
                window=SimpleNamespace(native=native,background_color='#100d1c',_orion_surface_scale=scale)
                with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
                    self.assertTrue(apply_surface(window,'home'))
                status=window._orion_native_status
                self.assertTrue(status['clip']);self.assertTrue(status['interactive']);self.assertTrue(status['pointer_owner'])
                self.assertEqual(status['bounds'],[8,8,8+model.width,8+model.height])
                self.assertEqual(native.TransparencyKey,'empty');self.assertFalse(native.AllowTransparency)
                self.assertEqual(native.Opacity,1)
                self.assertEqual(native.BackColor,'#100d1c');self.assertEqual(native.webview.DefaultBackgroundColor,'#100d1c')
                self.assertIsNone(native.Region);self.assertIsNone(native.webview.Region)
                self.assertEqual(model.styles[1],8)  # Always-on-top preserved.
                self.assertEqual(model.styles[2],0)
                self.assertTrue(all(model.enabled.values()))
                self.assertFalse(model.contains(model.pool[model.region],8,8+model.height-1))
                self.assertFalse(model.contains(model.pool[model.region],0,0))  # Frame outside WebView excluded.

    def test_synchronous_expand_and_collapse_keep_mask_without_layered_input(self):
        model=WindowsModel();native=Native(model)
        window=SimpleNamespace(native=native,background_color='#100d1c')
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertTrue(apply_surface(window,'home'))
            window._orion_surface_mode='peek'
            native.resize(188,34)
            self.assertTrue(model.contains(model.pool[model.region],0,0))
            self.assertFalse(model.contains(model.pool[model.region],0,33))
            window._orion_surface_mode='home'
            native.resize(680,212)
            self.assertFalse(model.contains(model.pool[model.region],0,211))
            self.assertFalse(model.contains(model.pool[model.region],679,211))
            self.assertTrue(window._orion_native_status['pointer_owner'])
            # Two native/control resize events share one region per geometry.
            self.assertEqual(model.user.SetWindowRgn.call_count,3)
            self.assertEqual(len(model.owned),1)
            # A measured 15px tab radius must not survive expansion while the
            # next browser measurement is still pending.
            window._orion_panel_insets={'radius':15};window._orion_shape_mode='peek'
            self.assertTrue(apply_surface(window,'home'))
            self.assertFalse(model.contains(model.pool[model.region],10,1))

    def test_css_insets_exclude_host_padding_and_background_changes_stay_opaque(self):
        model=WindowsModel(scale=1.5,inset=4);native=Native(model)
        shape={'left':2,'top':3,'right':4,'bottom':5,'radius':26}
        window=SimpleNamespace(native=native,background_color='#100d1c',_orion_surface_scale=1.5,_orion_panel_insets=shape)
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertTrue(apply_surface(window,'home'))
            self.assertEqual(window._orion_native_status['bounds'],[7,8,1018,314])
            window.background_color='#f5f3f6';self.assertTrue(apply_surface(window,'home'))
            self.assertEqual(native.webview.DefaultBackgroundColor,'#f5f3f6')
            self.assertFalse(native.AllowTransparency)

    def test_failed_mask_is_reported_and_untransferred_region_is_freed(self):
        model=WindowsModel();native=Native(model)
        model.user.SetWindowRgn.side_effect=lambda *_:0
        window=SimpleNamespace(native=native,background_color='#100d1c')
        with patch.dict(sys.modules,MODULES),patch('panel_window.ctypes.WinDLL',create=True,side_effect=model.dll):
            self.assertFalse(apply_surface(window,'home'))
        self.assertFalse(window._orion_native_status['clip'])
        self.assertEqual(model.pool,{})
        self.assertEqual(model.styles[1]&INPUT_FLAGS,0)  # Input still repaired if a mask fails.


if __name__=='__main__':unittest.main()
