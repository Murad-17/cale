"""CBAR official dated XML bulletins. No API key, invented rates or fixed USD peg."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

_cache = {}
_lock = threading.Lock()


def today():
    return datetime.now(timezone(timedelta(hours=4))).date()


def parse(raw, expected):
    if len(raw) > 1024 * 1024 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Məzənnə sənədinin quruluşu düzgün deyil.")
    try:
        root = ET.fromstring(raw)
        published = datetime.strptime(root.attrib["Date"], "%d.%m.%Y").date()
        if published != expected:
            raise ValueError("Mənbənin tarixini təsdiqləmək olmadı.")
        rates = {"AZN": Decimal(1)}
        for item in root.findall(".//Valute"):
            code = item.attrib.get("Code", "").upper()
            nominal = Decimal(item.findtext("Nominal", "").replace(",", "."))
            value = Decimal(item.findtext("Value", "").replace(",", "."))
            if not re.fullmatch(r"[A-Z]{3}", code) or not nominal.is_finite() or not value.is_finite() or nominal <= 0 or value <= 0:
                raise ValueError("Mənbədə məzənnə düzgün deyil.")
            rates[code] = value / nominal
        if len(rates) < 2:
            raise ValueError("Mənbədə məzənnələr yoxdur.")
        return rates
    except (ET.ParseError, KeyError, InvalidOperation, TypeError):
        raise ValueError("Rəsmi məzənnə sənədi oxunmadı.") from None


def bulletin(requested):
    cache_key = requested.isoformat()
    with _lock:
        cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 600:
        return cached[1]
    deadline = time.monotonic() + 25
    # Non-working days use the last preceding published bulletin, with its actual date.
    for back in range(15):
        if time.monotonic() > deadline:
            break
        date = requested - timedelta(days=back)
        url = "https://www.cbar.az/currencies/" + date.strftime("%d.%m.%Y") + ".xml"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ORION/1.1", "Accept": "application/xml,text/xml"})
            with urllib.request.urlopen(req, timeout=min(7, max(1, deadline-time.monotonic()))) as response:
                # Fixed official endpoint only; do not accept redirects to unrelated hosts.
                from urllib.parse import urlsplit
                if urlsplit(response.url).hostname not in ("cbar.az", "www.cbar.az"):
                    raise ValueError("Məzənnə ünvanı rəsmi domenə aid deyil.")
                raw = response.read(1024 * 1024 + 1)
            rates = parse(raw, date)
            result = (rates, date, url)
            with _lock:
                _cache[cache_key] = (time.monotonic(), result)
                while len(_cache) > 32:
                    del _cache[next(iter(_cache))]
            return result
        except urllib.error.HTTPError as error:
            if error.code in (404, 410):
                continue
            raise ValueError("Mərkəzi Bank məzənnə sorğusunu qəbul etmədi (HTTP " + str(error.code) + ").") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ValueError("Mərkəzi Banka bağlantı alınmadı. İnterneti yoxla və yenidən soruş.") from None
        except ValueError:
            # Some unavailable bulletin URLs return an HTML page with status 200.
            continue
    raise ValueError("Bu tarix üçün rəsmi bülleteni təsdiqləmək olmadı. Kurs uydurulmadı; veb axtarışla yoxla.")


def convert(source, target, amount=1, date=""):
    source, target = str(source).upper().strip(), str(target).upper().strip()
    if not all(re.fullmatch(r"[A-Z]{3}", c) for c in (source, target)):
        raise ValueError("Valyutanı AZN, USD, EUR, TRY kimi üçhərfli kodla yaz.")
    try:
        value = Decimal(str(amount))
        requested = datetime.strptime(date, "%Y-%m-%d").date() if date else today()
    except (InvalidOperation, ValueError):
        raise ValueError("Məbləğ və ya tarix düzgün deyil. Tarix: YYYY-MM-DD.") from None
    if not value.is_finite() or value < 0 or value > Decimal("1e15") or requested > today() or requested.year < 2000:
        raise ValueError("Məbləğ və ya tarix icazəli aralıqda deyil. Gələcək məzənnə məlum deyil.")
    rates, published, url = bulletin(requested)
    if source not in rates or target not in rates:
        raise ValueError("Valyuta rəsmi bülletendə tapılmadı: " + ", ".join(c for c in (source, target) if c not in rates))
    rate = rates[source] / rates[target]
    return {"source_currency": source, "target_currency": target, "amount": str(value),
            "rate": str(rate.quantize(Decimal(".00000001"))),
            "converted": str((value * rate).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)),
            "requested_date": requested.isoformat(), "published_date": published.isoformat(),
            "checked_at": datetime.now(timezone(timedelta(hours=4))).isoformat(timespec="seconds"),
            "source": "Azərbaycan Respublikasının Mərkəzi Bankı", "url": url,
            "note": "Rəsmi bülleten kursudur. Bankın nağd alış/satış kursu və komissiyası fərqlənə bilər."}
