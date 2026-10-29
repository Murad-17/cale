# Orion - fayl axtarışı modulu (YALNIZ OXUMA)
# Bu modul heç bir faylı silmir, dəyişmir, köçürmür və yaratmır - yalnız tapır və oxuyur.

import fnmatch
import os
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()

# Yalnız bu istifadəçi qovluqları və disklər axtarılır (mövcud olanlar)
SEARCH_ROOTS = [
    p for p in (
        HOME / "Desktop",
        HOME / "Documents",
        HOME / "Downloads",
        HOME / "Pictures",
        Path("D:/"),
        Path("E:/"),
    )
    if p.exists()
]

if os.environ.get("SEARCH_ROOT"):
    SEARCH_ROOTS = [Path(os.environ["SEARCH_ROOT"]).expanduser()]

# Bu adlı qovluqlara heç vaxt girilmir (sistem, proqram və keş qovluqları)
EXCLUDED_DIRS = {
    "windows", "program files", "program files (x86)", "programdata", "appdata",
    "$recycle.bin", "system volume information", "recovery", "$windows.~bt",
    "$windows.~ws", "windowsapps", "msocache", "perflogs",
    "node_modules", "__pycache__", ".git", ".venv", "venv", ".cache",
}

# Adında bu sözlər olan fayl/qovluqlar tam istisnadır (parol, şifrə, bank məlumatı)
SENSITIVE_WORDS = (
    "password", "passwd", "passwort", "parol", "пароль", "sifre", "credential",
    "secret", "bank", "iban", "creditcard", "kredit", "wallet", "idrsa", "privatekey",
)
SENSITIVE_EXTENSIONS = {".kdbx", ".kdb", ".pem", ".pfx", ".p12", ".key", ".ppk", ".env"}

# Axtarış bu müddətdən uzun çəksə, tapılanlarla dayanır (saniyə)
SEARCH_TIME_LIMIT = 90
MAX_RESULTS = 50

# Fayl oxunanda bu qədər simvoldan çoxu götürülmür
MAX_READ_CHARS = 20000

# Azərbaycan/türk hərflərini latın qarşılığına çeviririk: "Şifrə" -> "sifre"
_LETTERS = str.maketrans("şçğıöüə", "scgioue")


class SensitiveQueryError(Exception):
    """Sorğu parol/bank məlumatı kimi qadağan olunmuş fayllara aiddir."""


def _normalize(text):
    """Müqayisə üçün: kiçik hərf, xüsusi hərflər latınca, boşluq/defis/nöqtə silinir.
    Belə ki, "jarvis-project" = "Jarvis_Project" = "jarvis project"."""
    return "".join(ch for ch in text.casefold().translate(_LETTERS) if ch.isalnum())


def is_sensitive(name):
    """Fayl/qovluq adı parol, şifrə, bank məlumatı ola biləcək kimi görünürsə, True."""
    if name.casefold() == ".env" or name.casefold().startswith((".env.", ".env(")):
        return True
    normalized = _normalize(name)
    if any(word in normalized for word in SENSITIVE_WORDS):
        return True
    return os.path.splitext(name)[1].casefold() in SENSITIVE_EXTENSIONS


def _is_excluded_dir(name):
    return name.casefold() in EXCLUDED_DIRS or name.startswith("$")


def _matches(name, query):
    """Ad sorğuya uyğundursa, True. Sorğuda * və ya ? varsa, şablon kimi yoxlanılır."""
    if "*" in query or "?" in query:
        return fnmatch.fnmatch(name.casefold(), query.casefold())
    return _normalize(query) in _normalize(name)


def search_files(query, kind="any", log=print):
    """İstifadəçi qovluqlarında adı sorğuya uyğun fayl/qovluqları axtarır.
    kind: "file", "folder" və ya "any".
    Qaytarır: (tapılan yolların siyahısı, vaxt limiti bitdimi)."""
    if is_sensitive(query):
        raise SensitiveQueryError(
            "Bu sorğu parol, şifrə və ya bank məlumatı ola biləcək fayllara aiddir - "
            "belə fayllar axtarışdan tam istisna edilib."
        )
    if not _normalize(query.replace("*", "").replace("?", "")):
        return [], False

    results = []
    deadline = time.monotonic() + SEARCH_TIME_LIMIT
    for root in SEARCH_ROOTS:
        log(f"  axtarılır: {root}")
        stack = [root]
        while stack:
            if time.monotonic() > deadline:
                return results, True
            directory = stack.pop()
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if is_sensitive(entry.name):
                            continue
                        try:
                            # Simvolik keçidlərə/junction-lara girmirik - dövrə yaranmasın
                            is_dir = entry.is_dir(follow_symlinks=False) and not getattr(entry, "is_junction", lambda: False)()
                        except OSError:
                            continue
                        if is_dir and _is_excluded_dir(entry.name):
                            continue
                        if _matches(entry.name, query) and kind in ("any", "folder" if is_dir else "file"):
                            results.append(Path(entry.path))
                            if len(results) >= MAX_RESULTS:
                                return results, False
                        if is_dir:
                            stack.append(entry.path)
            except OSError:
                # İcazə olmayan və ya əlçatmaz qovluqları sadəcə keçirik
                continue
    return results, False


def _is_allowed(path):
    """Yol icazəli yerdədirmi: axtarış qovluqlarının içində, sistem və həssas adlar olmadan."""
    path = Path(path).resolve()
    for root in SEARCH_ROOTS:
        root = root.resolve()
        if path == root or root in path.parents:
            parts = path.relative_to(root).parts
            return not any(_is_excluded_dir(p) or is_sensitive(p) for p in parts)
    return False


def describe(path):
    """Tapılan yol üçün bir sətirlik təsvir: yol, növ, ölçü, dəyişmə tarixi."""
    try:
        stat = path.stat()
    except OSError:
        return f"{path}"
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
    if path.is_dir():
        return f"{path}  [qovluq, dəyişib: {modified}]"
    return f"{path}  [{stat.st_size / 1024:.1f} KB, dəyişib: {modified}]"


def read_path(path):
    """Faylın məzmununu və ya qovluğun siyahısını YALNIZ OXUYUR və mətn kimi qaytarır."""
    path = Path(path)
    if not _is_allowed(path):
        return "Bu yol icazəli axtarış qovluqlarından kənardadır və ya həssas addır - oxunmur."

    if path.is_dir():
        try:
            names = sorted(
                (e.name + ("\\" if e.is_dir() else "")) for e in os.scandir(path)
                if not is_sensitive(e.name)
            )
        except OSError as e:
            return f"Qovluq oxuna bilmədi: {e}"
        shown = "\n".join(f"  {n}" for n in names[:100])
        more = f"\n  ... və daha {len(names) - 100} element" if len(names) > 100 else ""
        return f"Qovluğun içindəkilər ({len(names)} element):\n{shown}{more}"

    try:
        with open(path, "rb") as f:  # yalnız oxuma rejimi
            data = f.read(MAX_READ_CHARS * 4)
    except OSError as e:
        return f"Fayl oxuna bilmədi: {e}"
    if b"\x00" in data[:4096]:
        return f"Bu mətn faylı deyil (ikili fayl, {path.suffix or 'uzantısız'}) - məzmunu göstərilmir."
    text = data.decode("utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n... (fayl uzundur, qalan hissə kəsildi)"
    return text
