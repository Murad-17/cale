"""Detached, transactional source-package installer. No user-data paths are updated.

This file is copied outside the application before it is executed, so it can
replace its own installed copy on Windows. It uses the existing Python runtime.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

MAX_PACKAGE = 100 * 1024 * 1024
MAX_EXPANDED = 200 * 1024 * 1024
ROOT_FILES = {
    "attachments.py", "blender_bridge.py", "blender_runner.py", "config.py",
    "dashboard_bridge.py", "engine.py", "exchange_rates.py", "file_search.py",
    "jobs.py", "main.py", "media_service.py", "orion_companion.py", "orion_http.py",
    "research.py", "roblox_bridge.py", "script_guard.py", "storage.py",
    "voice_service.py", "updater.py", "update_installer.py", "release_tools.py",
    "panel_service.py", "top_panel.py", "panel_window.py", "orion_panel.html", "robot_animator.js",
    "workspace_service.py", "assistant_modes.py", "video_service.py", "orion_big.js", "orion_big.css", "orion_modes.js",
    "orion_premium.css", "orion_premium.js", "orion_fonts.css", "password_meter.css", "password_meter.js",
    "companion_brain.py", "provider_connections.py", "companion_hub.js", "companion_hub.css", "orion_agent_hook.py",
    "orion_dashboard.html", "version.json", "wake_listener.ps1",
    "START.bat", "START_BROWSER.bat", "INSTALL.bat", "ENABLE_AUTOSTART.bat",
    "START_TOP_PANEL.bat",
    "INSTALL_ROBLOX_PLUGIN.bat", "requirements.txt", "requirements-desktop.txt",
}
REQUIRED = {"version.json", "main.py", "orion_dashboard.html", "updater.py", "update_installer.py"}


def allowed_file(name):
    if name in ROOT_FILES:
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9_\-]+\.md", name) or
                re.fullmatch(r"tests/test_[A-Za-z0-9_]+\.py", name) or
                re.fullmatch(r"panel_assets/orion-(idle|happy|wink|focus|shell|entry)\.png", name) or
                re.fullmatch(r"panel_assets/fonts/(Poppins-(Regular|Medium|SemiBold|Bold)\.woff|EuclidCircularA-(Light|Regular|Medium|SemiBold|Bold)(Italic)?\.woff|JetBrainsMono-(Latin|LatinExt)-(Regular|Medium)\.woff|OFL\.txt|JetBrainsMono-OFL\.txt)", name) or
                name == "roblox_plugin/OrionBridge.lua")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(256 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_package(path, expected_version):
    """Validate the entire archive before writing a single application file."""
    if Path(path).stat().st_size > MAX_PACKAGE:
        raise ValueError("Yeniləmə paketi ölçü limitini keçir.")
    files, seen, expanded = [], set(), 0
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 512:
            raise ValueError("Paketdə həddən artıq fayl var.")
        for item in archive.infolist():
            raw = item.filename
            p = PurePosixPath(raw)
            if "\\" in raw or p.is_absolute() or ".." in p.parts or ":" in raw:
                raise ValueError("Paketdə etibarsız fayl yolu var.")
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Yeniləmədə simvolik keçid qəbul edilmir.")
            if item.is_dir():
                continue
            name = raw[6:] if raw.startswith("ORION/") else raw
            if not allowed_file(name) or name.casefold() in seen:
                raise ValueError("Paketdə icazəsiz və ya təkrarlanan fayl var: " + name[:100])
            seen.add(name.casefold())
            expanded += item.file_size
            if expanded > MAX_EXPANDED or item.file_size > 40 * 1024 * 1024:
                raise ValueError("Paketin açılmış ölçüsü limitdən böyükdür.")
            files.append((name, raw))
        names = {name for name, _ in files}
        if not REQUIRED <= names:
            raise ValueError("Yeniləmənin əsas faylları çatışmır.")
        version_entry = next(raw for name, raw in files if name == "version.json")
        if json.loads(archive.read(version_entry)).get("version") != expected_version:
            raise ValueError("Paket versiyası buraxılış məlumatına uyğun deyil.")
    return files


def atomic_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def apply_package(package, target, backup, version, expected_hash):
    """Back up every replaced file, commit version last, roll back any failure."""
    package, target, backup = Path(package), Path(target).resolve(), Path(backup)
    if sha256(package) != expected_hash:
        raise ValueError("Paketin SHA-256 yoxlaması uğursuz oldu.")
    files = inspect_package(package, version)
    # version.json is the commit marker and must be the last file replaced.
    files.sort(key=lambda item: item[0] == "version.json")
    backup.mkdir(parents=True, exist_ok=False)
    stage = backup / "staged"
    stage.mkdir()
    with zipfile.ZipFile(package) as archive:
        for name, raw in files:
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(raw))
    replaced, originals = [], []
    try:
        for name, _ in files:
            dest = target / name
            if not dest.resolve().is_relative_to(target) or dest.is_symlink():
                raise ValueError("Tətbiq fayl yolu etibarlı deyil.")
            old = backup / "original" / name
            if dest.exists():
                if not dest.is_file():
                    raise ValueError("Tətbiq faylı qovluqla əvəz olunub.")
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, old)
                originals.append(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".orion-update-tmp")
            shutil.copy2(stage / name, tmp)
            os.replace(tmp, dest)
            replaced.append(name)
        atomic_json(backup / "restore.json", {"files": replaced, "originals": originals})
    except BaseException:
        for name in reversed(replaced):
            dest, old = target / name, backup / "original" / name
            if name in originals:
                shutil.copy2(old, dest)
            else:
                dest.unlink(missing_ok=True)
        raise
    return replaced


def wait_for_exit(pid, timeout=90):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return True
        try:
            return kernel.WaitForSingleObject(handle, timeout * 1000) == 0
        finally:
            kernel.CloseHandle(handle)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(.25)
    return False


def run_job(job_path):
    job_path = Path(job_path).resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    result = job_path.parent / "install-result.json"
    if not wait_for_exit(int(job["pid"])):
        atomic_json(result, {"ok": False, "error": "ORION bağlanmadı. Yeniləmə tətbiq edilmədi."})
        return 1
    try:
        apply_package(job["package"], job["target"], job["backup"], job["version"], job["sha256"])
    except Exception:
        atomic_json(result, {"ok": False, "error": "Quraşdırma alınmadı. Əvvəlki tətbiq faylları bərpa edildi."})
    else:
        atomic_json(result, {"ok": True, "version": job["version"], "at": time.time()})
    finally:
        Path(job["lock"]).unlink(missing_ok=True)
    # Restart even after rollback, with the same interpreter, arguments and profile.
    try:
        subprocess.Popen(job["restart"], cwd=job["target"], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         close_fds=True, env=os.environ.copy())
    except OSError:
        atomic_json(result, {"ok": False, "error": "Fayllar hazırdır. ORION-u START.bat ilə yenidən aç."})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_job(sys.argv[1]))
