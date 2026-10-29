"""Opt-in local wake phrase + bounded cloud transcription + spoken commands.
The window may be hidden; the Python/tray process must remain running.
"""
import io
import os
import subprocess
import threading
import wave
from pathlib import Path
import orion_http


class VoiceService:
    def __init__(self, engine):
        self.engine = engine
        self.busy = threading.Lock()
        self.requested = False
        self.process = None
        self.state = "idle"
        self.note = "Səsli komanda gözlənilir."
        self.closed = False

    def status(self):
        return {"state": self.state, "note": self.note, "wake_enabled": self.requested, "platform": os.name, "busy": self.busy.locked()}

    def _stop_wake(self):
        proc, self.process = self.process, None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def configure(self, enabled):
        self.requested = enabled
        if not enabled:
            self._stop_wake()
            if not self.busy.locked():
                self.state, self.note = "idle", "Oyatma sözü söndürülüb."
            return
        if self.busy.locked() or (self.process and self.process.poll() is None):
            return
        if os.name != "nt":
            self.state, self.note = "unavailable", "Arxa plan oyatma sözü bu paketdə Windows üçündür. Brauzer mikrofonundan istifadə et."
            return
        if not os.environ.get("OPENAI_API_KEY"):
            self.state, self.note = "unavailable", "Səsin mətnə çevrilməsi üçün OPENAI_API_KEY əlavə et."
            return
        script = Path(__file__).with_name("wake_listener.ps1")
        try:
            proc = subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.process = proc
            self.state, self.note = "starting", "Windows oyatma sözü hazırlanır."
            def watch():
                try:
                    for line in proc.stdout:
                        line = line.strip()
                        if self.process is not proc:
                            break
                        if line == "READY":
                            self.state, self.note = "listening", "‘Orion’ sözünü gözləyirəm."
                        elif line == "WAKE":
                            self.activate(from_wake=True)
                        elif line.startswith("ERROR:"):
                            self.state, self.note = "unavailable", "Windows nitq tanıması başlamadı. English (US) Speech paketini və mikrofon icazəsini yoxla."
                finally:
                    if self.process is proc and self.requested and not self.closed:
                        self.state, self.note = "unavailable", "Oyatma xidməti dayandı. Ayarda söndürüb yenidən aça bilərsən."
                        self.process = None
            threading.Thread(target=watch, daemon=True).start()
        except OSError:
            self.state, self.note = "unavailable", "Windows PowerShell tapılmadı."

    def submit_transcript(self, text, thread_id=None):
        if thread_id is not None:
            self.engine.companion.require_thread(thread_id)
            return self.engine.submit(text, source='companion_voice', thread_id=thread_id)
        return self.engine.submit(text, source='background_voice')

    def activate(self, from_wake=False, thread_id=None):
        if thread_id is not None:
            self.engine.companion.require_thread(thread_id)
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("Səsli komanda üçün OPENAI_API_KEY tələb olunur.")
        if not self.busy.acquire(blocking=False):
            return {"ok": False, "state": self.state, "note": "Əvvəlki səsli komanda hələ işlənir."}
        if not from_wake:
            self._stop_wake()
        self.state, self.note = "recording", "Dinləyirəm. Danışığını bitirəndə dayanacağam."
        def record():
            try:
                import sounddevice as sd
                import numpy as np
                rate, chunk = 16000, 1024
                frames, voiced, quiet, waited = [], False, 0, 0
                threshold = float(os.environ.get("ORION_VOICE_THRESHOLD", "0.012"))
                if os.name == "nt":
                    import winsound
                    winsound.MessageBeep()
                with sd.InputStream(samplerate=rate, channels=1, dtype="float32", blocksize=chunk) as stream:
                    for _ in range(int(22 * rate / chunk)):
                        audio, _ = stream.read(chunk)
                        level = float(np.sqrt(np.mean(audio ** 2)))
                        frames.append(audio.copy())
                        waited += chunk / rate
                        if level > threshold:
                            voiced, quiet = True, 0
                        elif voiced:
                            quiet += chunk / rate
                        if (voiced and quiet > 1.3) or (not voiced and waited > 8):
                            break
                if not voiced:
                    self.note = "Danışıq eşidilmədi; yenidən cəhd edə bilərsən."
                    self.finish()
                    return
                pcm = (np.clip(np.concatenate(frames), -1, 1) * 32767).astype("int16").tobytes()
                output = io.BytesIO()
                with wave.open(output, "wb") as wav:
                    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(pcm)
                self.state, self.note = "transcribing", "Səs yazıya çevrilir."
                text = self.engine.media.transcribe(output.getvalue(), "audio/wav", self.engine.settings["language"])
                if not text:
                    raise ValueError("Səsdən mətn alınmadı.")
                self.state, self.note = "thinking", "ORION əmri icra edir."
                self.submit_transcript(text, thread_id)
            except ImportError:
                self.state, self.note = "unavailable", "INSTALL.bat ilə masaüstü və səs asılılıqlarını quraşdır."
                self.finish(preserve=True)
            except Exception as error:
                self.state = "error"
                self.note = str(error) if isinstance(error, (ValueError, orion_http.APIError)) else "Mikrofon açıla bilmədi. Cihazı və Windows icazələrini yoxla."
                self.finish(preserve=True)
        threading.Thread(target=record, daemon=True, name="orion-record").start()
        return {"ok": True, **self.status()}

    def speak(self, text):
        self.state, self.note = "speaking", "ORION cavabı səsləndirir."
        try:
            provider = self.engine.settings.get("ttsProvider", "openai")
            if provider not in ("openai", "elevenlabs"):
                provider = "openai"
            data = self.engine.media.speech(text, self.engine.settings["language"], provider)
            if os.name == "nt":
                import winsound
                winsound.PlaySound(data, winsound.SND_MEMORY)
            else:
                import numpy as np
                import sounddevice as sd
                with wave.open(io.BytesIO(data), "rb") as wav:
                    sd.play(np.frombuffer(wav.readframes(wav.getnframes()), dtype="int16"), wav.getframerate())
                    sd.wait()
        except Exception:
            self.note = "Mətn cavabı saxlanıldı, amma səsləndirmə alınmadı."

    def finish(self, preserve=False):
        if self.busy.locked():
            self.busy.release()
        if not preserve:
            self.state, self.note = "idle", "Səsli komanda tamamlandı."
        if self.requested and not self.closed:
            if self.process and self.process.poll() is None:
                try:
                    self.process.stdin.write("DONE\n"); self.process.stdin.flush()
                    if not preserve:
                        self.state, self.note = "listening", "‘Orion’ sözünü gözləyirəm."
                except OSError:
                    self.process = None
            else:
                self.configure(True)

    def close(self):
        self.closed = True
        self.requested = False
        self._stop_wake()
