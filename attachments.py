"""Bounded attachment intake; private files are served only by opaque IDs."""
import base64
import binascii
import io
import mimetypes
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree

MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 25 * 1024 * 1024
IMAGES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css", ".lua", ".xml", ".log"}


def intake(directory, files, max_image_size=MAX_FILE):
    if not isinstance(files, list) or len(files) > 5:
        raise ValueError("Bir mesajda ən çox 5 fayl qəbul olunur.")
    prepared, total = [], 0
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Fayl formatı düzgün deyil.")
        name = str(item.get("name", "fayl")).replace("\\", "/").split("/")[-1][:180]
        encoded = item.get("data", "")
        if not isinstance(encoded, str) or len(encoded) > MAX_FILE * 4 // 3 + 8:
            raise ValueError("Fayl 20 MB limitini keçir.")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("Faylın base64 məzmunu düzgün deyil.") from None
        total += len(raw)
        if not raw or len(raw) > MAX_FILE or total > MAX_TOTAL:
            raise ValueError("Fayllar üçün 20 MB / cəmi 25 MB limiti keçilib və ya fayl boşdur.")
        if item.get("size") is not None and item["size"] != len(raw):
            raise ValueError("Fayl ölçüsü göndərilən məzmunla uyğun gəlmir.")
        mime = str(item.get("type") or mimetypes.guess_type(name)[0] or "application/octet-stream")
        if mime in IMAGES and len(raw) > max_image_size:
            raise ValueError("Bu modeldə şəkil üçün 5 MB-dan kiçik fayl seç.")
        suffix = Path(name).suffix.lower()
        text = None
        if suffix in TEXT_SUFFIXES or mime.startswith("text/"):
            text = raw[:120000].decode("utf-8", errors="replace")
        elif suffix == ".docx":
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    info = archive.getinfo("word/document.xml")
                    if info.file_size > 4 * 1024 * 1024:
                        raise ValueError("DOCX məzmunu çox böyükdür.")
                    root = ElementTree.fromstring(archive.read(info))
                    text = " ".join(root.itertext())[:120000]
            except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
                raise ValueError("DOCX sənədi oxuna bilmədi.") from None
        elif mime not in IMAGES and mime != "application/pdf" and suffix != ".pdf":
            raise ValueError(f"{name}: məzmun analizi üçün şəkil, PDF, DOCX və ya mətn/kod faylı seç.")
        if suffix == ".pdf":
            mime = "application/pdf"
        if mime == "application/pdf" and not raw.startswith(b"%PDF-"):
            raise ValueError("PDF faylının məzmunu düzgün deyil.")
        prepared.append(({"id": uuid.uuid4().hex, "name": name, "type": mime, "size": len(raw), "text": text}, raw))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    saved = []
    try:
        for meta, raw in prepared:
            path = directory / meta["id"]
            path.write_bytes(raw)
            saved.append(path)
    except OSError:
        for path in saved:
            path.unlink(missing_ok=True)
        raise
    return [meta for meta, _ in prepared]


def content(directory, items, provider):
    parts = []
    for item in items:
        if item.get("text") is not None:
            text = f"[Əlavə edilmiş məlumat: {item['name']}]\n{item['text']}\n[Məlumatın sonu]"
            parts.append({"type": "text" if provider == "anthropic" else "input_text", "text": text})
            continue
        path = Path(directory) / item["id"]
        if not path.is_file():
            continue
        data = base64.b64encode(path.read_bytes()).decode()
        if provider == "anthropic":
            parts.append({"type": "document" if item["type"] == "application/pdf" else "image", "source": {"type": "base64", "media_type": item["type"], "data": data}})
        elif item["type"] == "application/pdf":
            parts.append({"type": "input_file", "filename": item["name"], "file_data": "data:application/pdf;base64," + data})
        else:
            parts.append({"type": "input_image", "image_url": f"data:{item['type']};base64,{data}"})
    return parts
