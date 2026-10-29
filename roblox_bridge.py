"""
roblox_bridge.py
Orion (router/forge.py ilə eyni səviyyədə) və Roblox Studio Plugin arasında
yerli HTTP körpü. Plugin bu serveri "poll" edir (aralıqlarla soruşur),
növbədə əmr varsa icra edir və nəticəni geri bildirir.

İşə salmaq:  python roblox_bridge.py
Default port: 8787  (dəyişmək istəsəniz aşağıdakı PORT dəyərini redaktə edin)
"""

import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import orion_http as anthropic

import os
PORT = int(os.environ.get("ROBLOX_BRIDGE_PORT", "8787"))
_last_seen = 0.0


class RobloxError(Exception):
    """Roblox tikinti tapşırığı yerinə yetirilə bilmədikdə qaldırılır."""


# Claude-a tikinti planını JSON əmrlər siyahısına çevirtmək üçün təlimat
BUILD_PROMPT = (
    "Sən Roblox Studio üçün tikinti planı hazırlayan köməkçisən. İstifadəçinin "
    "təsvirini oxu və onu JSON əmrlər siyahısına çevir. Yalnız bu əmr tiplərindən "
    "istifadə et:\n\n"
    "- create_part: bir part yaradır (name, shape, size, position, color, "
    "anchored, parent istifadə olunur)\n"
    "- insert_script: bir Lua skripti daxil edir (name, script_type, source, "
    "parent istifadə olunur)\n"
    "- create_ui: ekran interfeysi qurur (name, elements istifadə olunur)\n"
    "- weld: iki mövcud partı fiziki olaraq bir-birinə bağlayır (part_a, part_b "
    "istifadə olunur - hər ikisi bu planın özündə əvvəllər yaradılmış partların "
    "tam yolu olmalıdır, məs. \"Workspace.Masin.Ov\")\n"
    "- insert_mesh: İSTİFADƏÇİNİN ARTIQ ROBLOX-A YÜKLƏDİYİ hazır 3D mesh asset-i "
    "səhnəyə qoyur (asset_id, name, position, size, anchored, parent istifadə "
    "olunur). BU ƏMRİ YALNIZ istifadəçi mesajında konkret bir asset ID və ya "
    "\"rbxassetid://...\" verdikdə istifadə et. Heç vaxt ID uydurma - istifadəçi "
    "\"nəhəng canavar modeli qur\" desə amma ID verməyibsə, bu əmri YARATMA, "
    "əvəzinə cavabında ona deyəcəyin qeydi normal mətndə izah et (ID lazımdır, "
    "əvvəlcə Blender-də model hazırlanıb Roblox-a mesh kimi yüklənməlidir).\n\n"
    "MÜRƏKKƏB TİKİNTİLƏR (çoxlu part, bir-birinə bağlı hissələr):\n"
    "- Eyni tikintiyə aid bütün part/skript/UI-lara EYNİ parent yolunu ver, məs. "
    "\"Workspace.Ev\" və ya \"Workspace.Masin\" - bu, onları məntiqi şəkildə "
    "qruplaşdırır (avtomatik Folder yaradılır).\n"
    "- Hər parta aydın, unikal ad ver (məs. \"Divar1\", \"Dam\", \"Qapi\") ki, "
    "sonra weld əmrində və ya növbəti sorğularda ona istinad etmək mümkün olsun.\n"
    "- Hissələr bir-birinə FİZİKİ bağlı olmalıdırsa (məs. hərəkət edən maşının "
    "təkəri, açılan qapı topsası) və anchored=false planlaşdırılıbsa, mütləq "
    "weld əmri əlavə et. Statik (anchored=true) tikintilərdə weld adətən lazım "
    "deyil, çünki hissələr onsuz da sabit dayanır.\n"
    "- Böyük tikintini məntiqi hissələrə böl və hər hissə üçün ayrı create_part "
    "əmri yaz (məs. ev üçün: döşəmə, 4 divar, dam - 6 ayrı əmr), tək nəhəng bir "
    "part əvəzinə.\n"
    "- Koordinatları elə hesabla ki, hissələr üst-üstə düşməsin və düzgün "
    "birləşsin (məs. divar hündürlüyü/2 qədər döşəmədən yuxarı).\n\n"
    "HƏR əmrdə params-ın BÜTÜN sahələri doldurulmalıdır, hətta həmin əmr tipinə "
    "aid olmayanlar da (onlar sadəcə istifadə edilməyəcək) - dəyər yoxdursa defolt "
    "yaz:\n"
    "- name: mənalı ad (məs. \"QirmiziPlatforma\")\n"
    "- shape: \"block\" (create_part deyilsə \"block\")\n"
    "- size: [x,y,z] ölçü, defolt [4,1,2]\n"
    "- position: [x,y,z] koordinat, defolt [0,5,0]\n"
    "- color: [r,g,b] 0-255 aralığında, defolt [255,255,255]\n"
    "- anchored: true (aid deyilsə true)\n"
    "- parent: yol, defolt \"Workspace\"\n"
    "- script_type: \"Script\" (aid deyilsə \"Script\")\n"
    "- source: Lua kodu, aid deyilsə boş sətir \"\"\n"
    "- elements: create_ui üçün UI element siyahısı, aid deyilsə boş massiv []\n"
    "- part_a, part_b: weld üçün tam yol, aid deyilsə boş sətir \"\"\n"
    "- asset_id: insert_mesh üçün \"rbxassetid://...\" formatında, aid deyilsə "
    "boş sətir \"\"\n\n"
    "elements içindəki hər element üçün də bütün sahələr (type, text, x, y, "
    "width, height) doldurulmalıdır, aid olmayanlar üçün boş/defolt dəyər yaz.\n\n"
    "Əmrlərin sırası vacibdir: weld əmri yalnız istinad etdiyi partlar artıq "
    "planın əvvəlki addımlarında yaradıldıqdan SONRA gəlməlidir."
)

# Növbə və nəticələr - sadə yaddaşda saxlama (proses bitəndə sıfırlanır)
_lock = threading.Lock()
_queue = []          # icra gözləyən əmrlər
_results = {}        # command_id -> nəticə


def queue_command(cmd_type: str, params: dict) -> str:
    """Router/Orion tərəfindən çağırılır. Yeni tikinti əmri əlavə edir."""
    cmd_id = str(uuid.uuid4())
    with _lock:
        _queue.append({"id": cmd_id, "type": cmd_type, "params": params})
    return cmd_id


def wait_for_result(cmd_id: str, timeout: float = 90.0):
    """Əmrin plugin tərəfindən icra olunmasını gözləyir.

    Qeyd: insert_mesh əmri Studio tərəfində (OrionBridgePlugin.lua) yeni yüklənmiş
    mesh asset-lərin Roblox tərəfindən emalını gözləmək üçün bir neçə dəfə təkrar
    cəhd edə bilər (~65 saniyəyə qədər). Timeout bunu tam əhatə etsin deyə 90
    saniyəyə qaldırılıb - əks halda əsl nəticə (uğur və ya konkret xəta) hələ
    yolda olarkən burada vaxtı keçmiş sayılır və itir.
    """
    start = time.time()
    while time.time() - start < timeout:
        with _lock:
            if cmd_id in _results:
                return _results.pop(cmd_id)
        time.sleep(0.25)
    return {
        "status": "timeout",
        "message": (
            f"Studio-dan {timeout:.0f} saniyə ərzində cavab gəlmədi. Roblox "
            "Studio açıqdırmı, plugin qoşulubmu (Output-da "
            "'[OrionBridgePlugin] işə düşdü...' görünürmü) yoxlayın."
        ),
    }


class BridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, code=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Host") not in (f"127.0.0.1:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}") or self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._send_json({"error": "origin"}, 403)
            return
        global _last_seen
        if self.path == "/queue":
            _last_seen = time.time()
            # Plugin bunu çağırır: gözləyən əmrləri götürür və növbəni boşaldır
            with _lock:
                pending = _queue.copy()
                _queue.clear()
            self._send_json({"commands": pending})
        elif self.path == "/status":
            self._send_json({"ok": True, "pending": len(_queue)})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.headers.get("Host") not in (f"127.0.0.1:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}"):
            self._send_json({"error": "host"}, 403)
            return
        origin = self.headers.get("Origin", "")
        if origin and origin not in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"):
            self._send_json({"error": "origin"}, 403)
            return
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._send_json({"error": "content type"}, 415)
            return
        length = int(self.headers.get("Content-Length", 0))
        if length > 1048576:
            self._send_json({"error": "size"}, 413)
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, 400)
            return

        if self.path == "/command":
            cmd_id = queue_command(data.get("type"), data.get("params", {}))
            self._send_json({"id": cmd_id, "status": "queued"})
        elif self.path == "/result":
            cmd_id = data.get("id")
            with _lock:
                _results[cmd_id] = data.get("result", {})
            self._send_json({"status": "received"})
        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        # Konsolu doldurmasın deyə susdurulur; lazım olsa açın
        pass


def start_bridge_server():
    """Bridge serverini arxa fonda (ayrı thread-də) başladır. main.py bunu import
    edib bir dəfə çağırmalıdır - ayrıca terminal açmağa ehtiyac qalmır. Server
    artıq işə düşübsə (məs. əl ilə ayrıca başladılıbsa), sadəcə xəbərdarlıq edir."""
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), BridgeHandler)
    except OSError:
        print(f"[roblox_bridge] {PORT} portu artıq istifadədədir - mövcud serverdən istifadə olunur.")
        return None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[roblox_bridge] {PORT} portunda arxa fonda başladı.")
    return server


def build_from_description(client, model, description):
    """İstifadəçinin təsvirini Claude ilə JSON əmrlər planına çevirir, hər əmri
    bridge növbəsinə qoyur, Studio plugin-in icra etməsini gözləyir və
    nəticələrin siyahısını qaytarır: [{"type": ..., "status": ..., ...}, ...].
    Studio açıq deyilsə və ya plugin qoşulmayıbsa, əmrlər timeout ilə qayıdır."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=BUILD_PROMPT,
            messages=[{"role": "user", "content": description}],
            output_config={
                "effort": "medium",
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "commands": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["create_part", "insert_script", "create_ui", "weld", "insert_mesh"],
                                        },
                                        "params": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "shape": {
                                                    "type": "string",
                                                    "enum": ["block", "ball", "cylinder"],
                                                },
                                                "size": {
                                                    "type": "array",
                                                    "items": {"type": "number"},
                                                },
                                                "position": {
                                                    "type": "array",
                                                    "items": {"type": "number"},
                                                },
                                                "color": {
                                                    "type": "array",
                                                    "items": {"type": "number"},
                                                },
                                                "anchored": {"type": "boolean"},
                                                "parent": {"type": "string"},
                                                "script_type": {
                                                    "type": "string",
                                                    "enum": ["Script", "LocalScript", "ModuleScript"],
                                                },
                                                "source": {"type": "string"},
                                                "elements": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "type": {
                                                                "type": "string",
                                                                "enum": ["TextButton", "TextLabel", "Frame"],
                                                            },
                                                            "text": {"type": "string"},
                                                            "x": {"type": "number"},
                                                            "y": {"type": "number"},
                                                            "width": {"type": "number"},
                                                            "height": {"type": "number"},
                                                        },
                                                        "required": [
                                                            "type", "text", "x", "y", "width", "height",
                                                        ],
                                                        "additionalProperties": False,
                                                    },
                                                },
                                                "part_a": {"type": "string"},
                                                "part_b": {"type": "string"},
                                                "asset_id": {"type": "string"},
                                            },
                                            "required": [
                                                "name", "shape", "size", "position", "color",
                                                "anchored", "parent", "script_type", "source", "elements",
                                                "part_a", "part_b", "asset_id",
                                            ],
                                            "additionalProperties": False,
                                        },
                                    },
                                    "required": ["type", "params"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["commands"],
                        "additionalProperties": False,
                    },
                },
            },
        )
    except anthropic.APIError as e:
        raise RobloxError(f"tikinti planı hazırlana bilmədi: {e}") from e

    if response.stop_reason in ("refusal", "max_tokens"):
        raise RobloxError("Claude tikinti planı vermədi")

    text = next(block.text for block in response.content if block.type == "text")
    commands = json.loads(text)["commands"]
    if not commands:
        raise RobloxError("tapşırıqda tikinti əmri tapılmadı")

    results = []
    for cmd in commands:
        cmd_id = queue_command(cmd["type"], cmd.get("params", {}))
        result = wait_for_result(cmd_id)
        result["type"] = cmd["type"]
        results.append(result)
    return results


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), BridgeHandler)
    print(f"[roblox_bridge] {PORT} portunda dinləyir...")
    print("[roblox_bridge] Studio plugin bu serverə qoşulmağa hazır olmalıdır.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[roblox_bridge] Dayandırıldı.")
