"""ORION's small, always-on-top desktop figure and shared command chat.

The Tk UI runs in its own process so it never shares a GUI thread with WebView.
Importing this module does not create windows, threads or network requests.
"""
import argparse
import importlib.util
import json
import math
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class LocalClient:
    def __init__(self, url):
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
                or not parsed.port or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or parsed.username):
            raise ValueError("Yalnız yerli ORION serveri istifadə edilə bilər.")
        self.url = url.rstrip("/")

    def request(self, path, data=None):
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        request = Request(self.url + path, data=body, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=5) as response:
                return json.load(response)
        except HTTPError as error:
            try:
                note = json.loads(error.read()).get("error", "Sorğu qəbul edilmədi.")
            except (ValueError, OSError):
                note = "Sorğu qəbul edilmədi."
            raise ValueError(str(note)) from None
        except (URLError, TimeoutError, OSError):
            raise ConnectionError("ORION serverinə bağlantı yoxdur.") from None


class CompanionProcess:
    def __init__(self, url, directory, enabled=True):
        self.url, self.directory, self.enabled = url, Path(directory), enabled
        self.process = None
        self.lock = threading.Lock()

    def is_running(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    def show(self, *_):
        # An explicit user action can re-enable a panel disabled at startup.
        self.enabled = True
        if self.is_running():
            try:
                if LocalClient(self.url).request("/api/panel/status").get("close_requested"):
                    self.stop()
            except (ValueError, ConnectionError):
                pass
        return self.start()

    def start(self, *_):
        if not self.enabled:
            return False
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return True
            if importlib.util.find_spec("webview") is None:
                print("ORION üst paneli üçün masaüstü modulu lazımdır. INSTALL.bat faylını aç.")
                return False
            executable = Path(sys.executable)
            if sys.platform == "win32" and executable.with_name("pythonw.exe").is_file():
                executable = executable.with_name("pythonw.exe")
            self.directory.mkdir(parents=True, exist_ok=True)
            args = [str(executable), str(Path(__file__).resolve()), "--url", self.url,
                    "--state-file", str(self.directory / "companion-ui.json")]
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
            try:
                LocalClient(self.url).request("/api/panel/control", {"action": "open"})
            except (ValueError, ConnectionError):
                pass
            try:
                with (self.directory / "companion.log").open("ab") as log:
                    self.process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                                    stdout=log, stderr=log, **options)
            except OSError as error:
                print("ORION fiquru açıla bilmədi:", str(error))
                return False
            return True

    def stop(self, *_):
        with self.lock:
            process, self.process = self.process, None
        if process is not None and process.poll() is None:
            try:
                LocalClient(self.url).request("/api/panel/control", {"action": "close"})
                process.wait(timeout=3)
                return
            except (ValueError, ConnectionError, subprocess.TimeoutExpired):
                pass
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


def avatar_image(size=120, blink=False, busy=False):
    """Render the native figure at 3x resolution, then antialias it once."""
    from PIL import Image, ImageDraw, ImageFilter
    scale = 3
    image = Image.new("RGBA", (120 * scale, 132 * scale))
    draw = ImageDraw.Draw(image)
    def box(values):
        return tuple(int(value * scale) for value in values)
    def ellipse(bounds, fill, outline=None, width=1):
        draw.ellipse(box(bounds), fill=fill, outline=outline, width=width * scale)
    shadow = Image.new("RGBA", image.size)
    ImageDraw.Draw(shadow).ellipse(box((25, 112, 96, 122)), fill=(92, 37, 15, 45))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(3 * scale)))
    draw = ImageDraw.Draw(image)
    # Feet, rounded body, antenna and the large orange head.
    ellipse((30, 102, 57, 114), "#dd632d")
    ellipse((65, 102, 92, 114), "#dd632d")
    ellipse((39, 75, 82, 109), "#ff8a42", "#e56629")
    ellipse((45, 79, 72, 98), "#ffb279")
    draw.line(box((60, 13, 60, 26)), fill="#ec7b3e", width=4 * scale)
    ellipse((55, 7, 65, 17), "#ffbe88", "#f88a48")
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).ellipse(box((20, 22, 100, 94)), fill=255)
    sphere = Image.new("RGBA", image.size)
    pixels = sphere.load()
    for y in range(22 * scale, 95 * scale):
        for x in range(20 * scale, 101 * scale):
            light = max(0.0, 1 - math.hypot((x / scale - 43) / 67, (y / scale - 33) / 63))
            pixels[x, y] = (255, int(101 + light * 82), int(32 + light * 77), 255)
    image.paste(sphere, (0, 0), mask)
    draw = ImageDraw.Draw(image)
    draw.arc(box((21, 23, 99, 93)), 193, 275, fill="#ffe3c5", width=2 * scale)
    draw.rounded_rectangle(box((31, 41, 89, 73)), radius=14 * scale, fill="#2b2025")
    eye = "#ffd3a1" if busy else "#fff5e6"
    if blink:
        draw.line(box((41, 56, 49, 56)), fill=eye, width=3 * scale)
        draw.line(box((71, 56, 79, 56)), fill=eye, width=3 * scale)
    else:
        for x in (40, 70):
            draw.rounded_rectangle(box((x, 49, x + 9, 63)), radius=4 * scale, fill=eye)
    draw.arc(box((52, 60, 68, 68)), 15, 165, fill="#e99560", width=scale)
    draw.arc(box((11, 42, 109, 89)), 8, 176, fill="#ffe2c0", width=3 * scale)
    ellipse((88, 78, 96, 86), "#ffb56e" if busy else "#ff8a42", "#fff3dc")
    return image.resize((size, round(size * 132 / 120)), Image.Resampling.LANCZOS)


class CompanionApp:
    def __init__(self, url, state_file):
        import tkinter as tk
        from tkinter import scrolledtext
        from PIL import ImageTk
        self.tk, self.client, self.state_file = tk, LocalClient(url), Path(state_file)
        self.root = tk.Tk()
        self.root.title("ORION — ekran köməkçisi")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#f5f3f6")
        if sys.platform == "win32":
            self.root.attributes("-transparentcolor", "#f5f3f6")
        self.root.geometry("120x148")
        self.images = [ImageTk.PhotoImage(avatar_image(blink=blink, busy=busy))
                       for blink, busy in ((False, False), (True, False), (False, True))]
        self.canvas = tk.Canvas(self.root, width=120, height=148, bg="#f5f3f6",
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.figure = self.canvas.create_image(60, 64, image=self.images[0])
        self.canvas.create_text(60, 137, text="ORION", fill="#78452e", font=("Segoe UI", 9, "bold"))
        self.drag = None
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.move)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="Kiçik çatı aç", command=self.open_chat)
        self.menu.add_command(label="Əsas paneli aç", command=self.show_dashboard)
        self.menu.add_separator()
        self.menu.add_command(label="Fiquru gizlət", command=self.quit)
        self.canvas.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.chat = tk.Toplevel(self.root)
        self.chat.withdraw()
        self.chat.overrideredirect(True)
        self.chat.attributes("-topmost", True)
        self.chat.configure(bg="#e5d4c8")
        self.chat.protocol("WM_DELETE_WINDOW", self.close_chat)
        frame = tk.Frame(self.chat, bg="#fffaf7")
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(frame, bg="#fff0e5", padx=12, pady=9)
        header.pack(fill="x")
        title = tk.Label(header, text="ORION  ·  sürətli komanda", bg="#fff0e5",
                         fg="#61351f", font=("Segoe UI", 11, "bold"))
        title.pack(side="left")
        tk.Button(header, text="×", command=self.close_chat, bg="#fff0e5", fg="#673e2e",
                  relief="flat", bd=0, width=3, font=("Segoe UI", 14)).pack(side="right")
        tk.Button(header, text="↗", command=self.show_dashboard, bg="#fff0e5", fg="#673e2e",
                  relief="flat", bd=0, width=3, font=("Segoe UI", 13)).pack(side="right")
        header.bind("<ButtonPress-1>", self.chat_press)
        header.bind("<B1-Motion>", self.chat_move)
        title.bind("<ButtonPress-1>", self.chat_press)
        title.bind("<B1-Motion>", self.chat_move)
        self.messages = scrolledtext.ScrolledText(frame, wrap="word", bd=0, padx=14, pady=12,
                                                 bg="#fffaf7", fg="#332b30", height=13,
                                                 font=("Segoe UI", 10), state="disabled")
        self.messages.pack(fill="both", expand=True)
        self.messages.tag_configure("user", foreground="#ac4a24", font=("Segoe UI", 10, "bold"))
        self.messages.tag_configure("orion", foreground="#322b30", font=("Segoe UI", 10, "bold"))
        self.messages.tag_configure("notice", foreground="#926e5c")
        self.status = tk.StringVar(value="Serverə qoşulur…")
        tk.Label(frame, textvariable=self.status, bg="#fffaf7", fg="#866c5e", anchor="w",
                 font=("Segoe UI", 9), padx=13, pady=5).pack(fill="x")
        composer = tk.Frame(frame, bg="#fffaf7", padx=10, pady=10)
        composer.pack(fill="x")
        self.entry = tk.Entry(composer, font=("Segoe UI", 11), bg="white", fg="#322b30",
                              relief="solid", bd=1, insertbackground="#e56c35")
        self.entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.entry.bind("<Return>", self.send)
        self.entry.bind("<Escape>", lambda _: self.close_chat())
        self.entry.bind("<KeyRelease>", self.save_draft, add="+")
        try:
            draft = json.loads(self.state_file.with_name("companion-draft.json").read_text(encoding="utf-8"))
            if isinstance(draft.get("text"), str):
                self.entry.insert(0, draft["text"][:20000])
        except (OSError, ValueError):
            pass
        self.send_button = tk.Button(composer, text="Göndər", command=self.send,
                                     bg="#e96f37", fg="white", activebackground="#cc5727",
                                     relief="flat", bd=0, padx=10, pady=9, font=("Segoe UI", 10))
        self.send_button.pack(side="right", padx=(7, 0))
        self.chat.bind("<Escape>", lambda _: self.close_chat())
        self.events = queue.Queue()
        self.cursor, self.pending_job, self.pending_reply = None, None, None
        self.seen, self.failures, self.polling, self.sending = set(), 0, False, False
        self.closed, self.chat_drag = False, None
        left, top, right, bottom = self.bounds()
        x, y = right - 144, bottom - 175
        try:
            saved = json.loads(self.state_file.read_text(encoding="utf-8"))
            x, y = int(saved["x"]), int(saved["y"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self.place(x, y)
        self.root.after(100, self.drain)
        self.root.after(150, self.poll)
        self.root.after(5200, self.blink)

    def bounds(self):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right, rect.bottom
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def place(self, x, y):
        left, top, right, bottom = self.bounds()
        x, y = max(left, min(x, right - 120)), max(top, min(y, bottom - 148))
        self.root.geometry(f"+{x}+{y}")

    def press(self, event):
        self.drag = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y(), False)

    def move(self, event):
        if self.drag:
            x, y, start_x, start_y, moved = self.drag
            moved = moved or abs(event.x_root - x) + abs(event.y_root - y) > 6
            self.drag = (x, y, start_x, start_y, moved)
            if moved:
                self.place(start_x + event.x_root - x, start_y + event.y_root - y)

    def release(self, _):
        moved = self.drag and self.drag[-1]
        self.drag = None
        if moved:
            self.save_position()
            if self.chat.winfo_viewable():
                self.position_chat()
        elif self.chat.winfo_viewable():
            self.close_chat()
        else:
            self.open_chat()

    def save_position(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps({"x": self.root.winfo_x(), "y": self.root.winfo_y()}), encoding="utf-8")
        except OSError:
            pass

    def position_chat(self):
        left, top, right, bottom = self.bounds()
        width, height = min(370, right - left - 16), min(440, bottom - top - 18)
        x = max(left + 8, min(self.root.winfo_x() + 120 - width, right - width - 8))
        y = max(top + 8, min(self.root.winfo_y() - height - 10, bottom - height - 8))
        self.chat.geometry(f"{width}x{height}+{x}+{y}")

    def open_chat(self):
        self.position_chat()
        self.chat.deiconify()
        self.chat.lift()
        self.chat.focus_force()
        self.entry.focus_set()

    def close_chat(self):
        self.save_draft()
        self.chat.withdraw()

    def save_draft(self, _=None):
        if not hasattr(self, "state_file"):
            return
        try:
            path = self.state_file.with_name("companion-draft.json")
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"text": self.entry.get()[:20000]}, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            self.status.set("Qaralama saxlanılmadı. Yenidən başlatmazdan əvvəl komandanı göndər.")

    def chat_press(self, event):
        self.chat_drag = (event.x_root - self.chat.winfo_x(), event.y_root - self.chat.winfo_y())

    def chat_move(self, event):
        if self.chat_drag:
            self.chat.geometry(f"+{event.x_root - self.chat_drag[0]}+{event.y_root - self.chat_drag[1]}")

    def append(self, role, text):
        self.messages.configure(state="normal")
        label = "Sən" if role == "user" else "ORION" if role == "orion" else "Qeyd"
        self.messages.insert("end", label + "\n", role)
        self.messages.insert("end", str(text) + "\n\n")
        self.messages.configure(state="disabled")
        self.messages.see("end")

    def background(self, kind, fn):
        def work():
            try:
                self.events.put((kind, fn(), None))
            except Exception as error:
                self.events.put((kind, None, str(error)))
        threading.Thread(target=work, daemon=True, name="orion-companion-io").start()

    def poll(self, reschedule=True):
        if self.closed:
            return
        if not self.polling:
            self.polling = True
            cursor, job_id = self.cursor, self.pending_job
            def fetch():
                start = cursor
                if start is None:
                    start = max(0, int(self.client.request("/api/messages/head")["next_id"]) - 30)
                messages = self.client.request(f"/api/messages?since={start}").get("messages", [])
                jobs = self.client.request("/api/jobs").get("jobs", []) if job_id else []
                return {"messages": messages, "cursor": max([start] + [int(m["id"]) + 1 for m in messages]), "job": next((j for j in jobs if j["id"] == job_id), None)}
            self.background("poll", fetch)
        if reschedule:
            self.root.after(1200 if self.pending_job else 3000, self.poll)

    def send(self, _=None):
        text = self.entry.get().strip()
        if self.sending or self.pending_job or not text:
            return
        if len(text) > 20000:
            self.status.set("Komanda 20 000 simvoldan uzun ola bilməz.")
            return
        self.sending = True
        self.send_button.configure(state="disabled")
        self.status.set("Komanda göndərilir…")
        self.background("send", lambda: {"accepted": self.client.request("/api/send", {"text": text}), "draft": text})

    def show_dashboard(self):
        self.background("show", lambda: self.client.request("/api/desktop/show", {}))

    def drain(self):
        if self.closed:
            return
        while True:
            try:
                kind, data, error = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "poll":
                self.polling = False
                if error:
                    self.failures += 1
                    self.status.set(error)
                    if self.failures >= 8:
                        self.quit()
                        return
                    continue
                self.failures = 0
                self.cursor = data["cursor"]
                for message in data["messages"]:
                    if message["id"] in self.seen:
                        continue
                    self.seen.add(message["id"])
                    if message["sender"] in ("user", "orion"):
                        self.append(message["sender"], message["text"])
                job = data.get("job")
                if job and job["status"] in ("completed", "failed", "interrupted"):
                    self.pending_job = None
                    self.send_button.configure(state="normal")
                    self.canvas.itemconfigure(self.figure, image=self.images[0])
                    if job["status"] != "completed":
                        self.status.set("Komanda tamamlanmadı. Cavabı yoxla.")
                    else:
                        self.status.set("Hazırdır · yeni komanda yaza bilərsən")
                elif not self.pending_job and not self.sending:
                    self.status.set("Hazırdır · Enter ilə göndər")
            elif kind == "send":
                self.sending = False
                if error:
                    self.send_button.configure(state="normal")
                    self.status.set(error)
                    self.append("notice", error)
                else:
                    self.pending_job = data["accepted"]["job_id"]
                    if self.entry.get().strip() == data["draft"]:
                        self.entry.delete(0, "end")
                        self.save_draft()
                    self.canvas.itemconfigure(self.figure, image=self.images[2])
                    self.status.set("ORION komandanı icra edir…")
                    if not self.polling:
                        self.poll(reschedule=False)
            elif kind == "show":
                if error:
                    self.status.set(error)
                else:
                    self.close_chat()
        self.root.after(100, self.drain)

    def blink(self):
        if self.closed:
            return
        if not self.pending_job:
            self.canvas.itemconfigure(self.figure, image=self.images[1])
            self.root.after(130, lambda: None if self.closed else self.canvas.itemconfigure(self.figure, image=self.images[2] if self.pending_job else self.images[0]))
        self.root.after(6200, self.blink)

    def quit(self):
        if not self.closed:
            self.save_draft()
            self.save_position()
            self.closed = True
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="ORION ekranın yuxarısındakı chatbot paneli")
    parser.add_argument("--url", required=True)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--legacy-figure", action="store_true", help="Əvvəlki ekran fiqurunu aç")
    args = parser.parse_args()
    if args.legacy_figure:
        CompanionApp(args.url, args.state_file).run()
    else:
        from top_panel import run
        run(args.url, args.state_file)


if __name__ == "__main__":
    main()
