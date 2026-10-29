"""Small standard-library HTTP transport. Never includes credentials in errors."""
import base64
import json
import re
import urllib.error
import urllib.request
import uuid
from types import SimpleNamespace


class APIError(Exception):
    def __init__(self, message, status=0, *, reason="", request_id=""):
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.request_id = request_id


def credential_in_model(value):
    """A credential pasted into a model field must never enter a public picker."""
    return bool(re.search(r"(?:\bsk-[a-z0-9_-]+|\bkey_[a-z0-9_-]+|\bbearer\s+)", str(value), re.I))


def anthropic_temperature_supported(model):
    # Sampling controls were removed after 4.6; leave modern models at API defaults.
    match = re.match(r"^claude-(?:opus|sonnet|haiku)-(\d+)(?:-(\d+))?", model)
    if match:
        major, minor = int(match[1]), int(match[2] or 0)
        return major < 4 or (major == 4 and minor <= 6)
    return model.startswith("claude-3")


def describe_error(error, url):
    """Translate recognized provider failures without copying their raw response.

    Upstream messages can echo the prompt, uploaded text or a malformed API key.
    Read a bounded JSON document, classify it, and emit only fixed local text,
    an allowlisted error type and a validated request ID.
    """
    status = error.code
    fallback = {400: "Sorğu parametrləri və model uyğunluğunu yoxla", 401: "API açarını yoxla",
                402: "AI xidmətinin ödəniş və balans məlumatını yoxla",
                403: "Bu model və ya xidmət üçün hesab icazəsi yoxdur",
                404: "Model və ya API ünvanı tapılmadı", 413: "Sorğunun ölçüsü xidmət limitini keçir",
                429: "API sorğu limitinə çatılıb"}
    try:
        document = json.loads(error.read(65537))
        detail = document.get("error", {}) if isinstance(document, dict) else {}
        if not isinstance(detail, dict):
            detail = {}
    except (ValueError, OSError, TypeError):
        document, detail = {}, {}
    message = str(detail.get("message", ""))[:16000].casefold()
    error_type = detail.get("type", "")
    code = detail.get("code", "")
    reason, text = "", fallback.get(status, "AI xidməti sorğunu qəbul etmədi")
    if re.search(r"credit balance.*(?:too low|exhausted|insufficient)|insufficient (?:credit|balance)|not enough credits|insufficient_quota|exceeded your current quota", message) or code == "insufficient_quota":
        reason = "credit_balance"
        text = "AI xidmətinin API balansı və ya istifadə kvotası kifayət deyil. Seçilmiş xidmətin Console → Billing bölməsində balansı və limitləri yoxla"
    elif re.search(r"(?:organization|workspace).*spend limit|spending limit|monthly spend cap", message):
        reason = "spend_limit"
        text = "Hesabın və ya iş sahəsinin API xərc limitinə çatılıb. Console → Billing bölməsində limiti yoxla"
    elif "oauth" in message and re.search(r"not supported|not allowed|unsupported", message):
        reason = "credential_type"
        text = "Bu giriş tokeni seçilmiş API ilə uyğun deyil. Console-da yaradılmış API açarını ANTHROPIC_API_KEY sətrinə əlavə et"
    elif re.search(r"(?:invalid|incorrect|malformed|expired|revoked).{0,35}(?:api[ _-]?key|token)|(?:api[ _-]?key|token).{0,35}(?:invalid|incorrect|malformed|expired|revoked)", message):
        reason = "authentication"
        text = "API açarı xidmət tərəfindən qəbul edilmir. .env faylındakı uyğun API_KEY sətrini və açarın aktivliyini yoxla"
    elif "temperature" in message:
        reason = "temperature"
        text = "Seçilmiş model temperature parametrini qəbul etmir. Modelin standart temperaturu istifadə edilməlidir"
    elif re.search(r"web_search|web_fetch|web search|web fetch", message) and re.search(r"not supported|unsupported|disabled|not enabled|not allowed|permission|not available|invalid tool", message):
        reason = "web_tool"
        text = "Bu hesab və ya model veb axtarış/oxuma alətini qəbul etmir. AI imkanları bölməsində interneti söndürüb adi çatı yoxla"
    elif re.search(r"prompt is too long|context length|context window|too many tokens|request too large", message):
        reason = "context_limit"
        text = "Söhbət və faylların ümumi ölçüsü modelin kontekst limitini keçir. Daha qısa mətn və ya daha kiçik faylla yoxla"
    elif "max_tokens" in message or "max_output_tokens" in message:
        reason = "output_limit"
        text = "Cavab token limiti seçilmiş modelə uyğun deyil. AI ayarlarında cavab limitini azalt"
    elif re.search(r"thinking|tool_choice|tool choice", message) and re.search(r"not supported|unsupported|cannot|must|invalid", message):
        reason = "thinking_tool_choice"
        text = "Düşünmə rejimi və məcburi alət seçimi modelə uyğun deyil. Normal araşdırma rejimi ilə yoxla"
    elif re.search(r"text.*(?:empty|non-empty)|(?:empty|non-empty).*text", message):
        reason = "empty_text"
        text = "Model boş mətn bloku qəbul etmir. Fayl mesajlarına qısa mətn əlavə edilməlidir"
    elif "workspace" in message and re.search(r"required|missing|select|header", message):
        reason = "workspace"
        text = "API açarı üçün iş sahəsi seçilməlidir. Console-da bir iş sahəsinə bağlı API açarı yarat"
    elif "model" in message and re.search(r"not found|not exist|invalid model|unknown model|not available|not have access|not supported|unsupported model", message):
        reason = "model"
        text = "Seçilmiş model bu hesabda və ya API ünvanında mövcud deyil. MODEL sətrində API açarı deyil, hesabına açıq olan modelin identifikatoru olmalıdır"
    elif error_type == "billing_error":
        reason = "billing"
        text = "AI xidmətində ödəniş problemi var. Seçilmiş xidmətin Console → Billing bölməsini yoxla"
    text += f" (HTTP {status})."
    if error_type in {"invalid_request_error", "authentication_error", "permission_error", "not_found_error", "rate_limit_error", "billing_error", "api_error", "overloaded_error", "invalid_api_key", "insufficient_quota"}:
        text += " Xidmətin xəta kodu: " + error_type + "."
    request_id = (error.headers or {}).get("request-id", "") or (document.get("request_id", "") if isinstance(document, dict) else "")
    if not isinstance(request_id, str) or not re.fullmatch(r"req_[a-zA-Z0-9_-]{6,100}", request_id) or "sk-" in request_id.casefold() or credential_in_model(request_id):
        request_id = ""
    if request_id:
        text += " Sorğu ID: " + request_id + "."
    return APIError(text, status, reason=reason, request_id=request_id)


def request(url, method="GET", payload=None, headers=None, raw=None, timeout=120):
    headers = dict(headers or {})
    if payload is not None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=raw, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            mime = response.headers.get("Content-Type", "application/octet-stream")
            return json.loads(data) if "json" in mime else data
    except urllib.error.HTTPError as error:
        raise describe_error(error, url) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise APIError("AI xidmətinə bağlantı alınmadı və ya vaxt bitdi.") from None


def multipart(fields, files):
    boundary = "orion-" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode(), str(value).encode(), b"\r\n"])
    for name, (filename, data, mime) in files.items():
        filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
        if hasattr(data, "read"):
            data = data.read()
        chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {mime}\r\n\r\n".encode(), data, b"\r\n"])
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), "multipart/form-data; boundary=" + boundary


class AnthropicClient:
    """Compatibility adapter for the user's existing Blender/Roblox modules."""
    def __init__(self, key=None):
        import os
        self.key = key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.messages = self

    def create(self, **kwargs):
        import os
        if not self.key:
            raise APIError("Blender və Roblox üçün ANTHROPIC_API_KEY tələb olunur.")
        headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01"}
        if os.environ.get('ANTHROPIC_WORKSPACE_ID'):
            headers['anthropic-workspace-id'] = os.environ['ANTHROPIC_WORKSPACE_ID']
        data = request(os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/") + "/messages", "POST", kwargs, headers, timeout=180)
        return SimpleNamespace(content=[SimpleNamespace(**b) for b in data.get("content", [])], stop_reason=data.get("stop_reason"))
