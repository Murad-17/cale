# Orion - Blender modulu: Blender-i arxa planda işə salıb bpy skripti ilə model yaradır
# Nəticə (.blend faylı və onu yaradan .py skripti) Orion\models\ qovluğuna saxlanır.

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

ORION_DIR = Path(__file__).resolve().parent
MODELS_DIR = Path(os.environ.get("ORION_MODELS_DIR", str(ORION_DIR / "models")))
RUNNER = ORION_DIR / "blender_runner.py"

# Blender skripti bu müddətdən çox işləsə, dayandırılır (saniyə)
BLENDER_TIMEOUT = 300

# Skript xəta versə, Claude neçə dəfə yazsın (ilk cəhd + düzəlişlər)
MAX_ATTEMPTS = 2

# Claude-un bpy skripti yazması üçün təlimat
BPY_PROMPT = (
    "Sən {version} üçün bpy (Blender Python) skriptləri yazan köməkçisən. Tapşırığa "
    "əsasən modeli yaradan Python kodu yaz.\n\n"
    "Qaydalar:\n"
    "- Skript Blender-in arxa plan (background) rejimində işləyəcək; səhnə artıq boşdur.\n"
    "- Yalnız modeli yarat: faylı saxlama, render etmə, Blender-dən çıxma, başqa fayllara "
    "yazma, internetə müraciət etmə, os/subprocess istifadə etmə - bunları Orion özü edir.\n"
    "- Ölçü göstərilməyibsə, məqbul standart ölçü seç (məs. kub üçün 2 m). Ölçülər metrlə.\n"
    "- Obyektlərə mənalı ad ver. Rəng istənibsə, material yaradıb obyektə təyin et.\n\n"
    "ÜZVİ/CANLI FORMALAR (canavar, heyvan, insan, əfsanəvi yaradıq və s.):\n"
    "- Sadə primitivləri yan-yana düzmə (məs. bir kürə + bir kub) - bu, keyfiyyətsiz "
    "görünür. Bunun əvəzinə:\n"
    "  1. Metaball (bpy.data.metaballs) istifadə et - bədən hissələrini (gövdə, baş, "
    "ətraflar) üst-üstə düşən metaball elementləri kimi yerləşdir, bunlar avtomatik "
    "hamar birləşir; sonra 'Convert to Mesh' məntiqi ilə adi meshə çevir "
    "(bpy.ops.object.convert(target='MESH')).\n"
    "  2. Və ya əsas forma üçün UV Sphere/Cube götür, Subdivision Surface modifikatoru "
    "əlavə et (yüksək hamarlıq üçün), sonra Sculpt-ə bənzər effekt üçün Vertex qrupları "
    "və Proportional Editing ilə forma ver, ya da sadə Displace modifikatoru (Noise "
    "texture ilə) əlavə et ki, üzvi görünsün.\n"
    "  3. Simmetrik formalar (heyvan bədəni, üz) üçün Mirror modifikatorundan istifadə "
    "et - yarısını modelləşdir, digər yarısı avtomatik yaransın.\n"
    "  4. Bütün hissələri son nəticədə Shade Smooth et "
    "(bpy.ops.object.shade_smooth()) ki, sərt kənarlar görünməsin.\n"
    "- Roblox-a aparılacaqsa, ÜMUMI POLİQON SAYINI mötədil saxla (mümkünsə 5.000-15.000 "
    "üçbucaq aralığında) - performans üçün vacibdir; Subdivision Surface səviyyəsini "
    "1-2-dən artırma.\n"
    "- Stil hədəfi 'stilizə/low-poly oyun modeli'dir, fotorealistik heykəltəraşlıq deyil - "
    "sadə, təmiz formalar, düz rənglər (material) kifayətdir.\n\n"
    "Cavab sahələri:\n"
    "- name: fayl adı üçün qısa ingiliscə ad (məs. 'cube', 'wooden_table')\n"
    "- script: tam işlək bpy kodu\n"
    "- summary: nə yaradıldığını bir cümlə ilə, Azərbaycan dilində"
)

# Roblox Open Cloud Assets API - FBX faylını avtomatik Roblox-a yükləmək üçün.
# Aktiv olması üçün ROBLOX_API_KEY və ROBLOX_CREATOR_ID mühit dəyişənləri lazımdır.
# Hər ikisi yoxdursa, yükləmə sakitcə keçilir (xəta atmır) - FBX faylı əl ilə
# Studio-nun Asset Manager-i ilə yüklənə bilər.
ROBLOX_ASSETS_URL = "https://apis.roblox.com/assets/v1/assets"
ROBLOX_OPERATIONS_URL = "https://apis.roblox.com/assets/v1/operations/{}"


class BlenderError(Exception):
    """Blender tapılmadıqda və ya model yaradıla bilmədikdə."""


def find_blender():
    """blender.exe-nin yolunu qaytarır. BLENDER_PATH mühit dəyişəni təyin olunubsa, onu,
    yoxsa "Program Files"-dakı ən yeni versiyanı götürür."""
    env_path = os.environ.get("BLENDER_PATH")
    if env_path:
        if Path(env_path).is_file():
            return Path(env_path)
        raise BlenderError(f"BLENDER_PATH-da göstərilən fayl tapılmadı: {env_path}")

    candidates = []
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            candidates += Path(base, "Blender Foundation").glob("Blender */blender.exe")
    if candidates:
        # "Blender 5.2" qovluq adından versiyanı çıxarıb ən yenisini seçirik
        def version(path):
            return tuple(int(n) for n in re.findall(r"\d+", path.parent.name))
        return max(candidates, key=version)

    on_path = shutil.which("blender")
    if on_path:
        return Path(on_path)
    raise BlenderError("Blender tapılmadı. BLENDER_PATH mühit dəyişənində blender.exe-nin yolunu göstərin.")


def run_blender_script(script_code, base_path):
    """bpy skriptini Blender-də arxa planda işlədir; <base_path>.blend və (mümkünsə)
    <base_path>.fbx fayllarını saxlayır. Qaytarır: yaradılmış obyektlərin siyahısı.
    Xəta olarsa BlenderError atır."""
    from script_guard import validate_script
    try:
        validate_script(script_code)
    except (ValueError, SyntaxError) as error:
        raise BlenderError(str(error)) from error
    blender = find_blender()
    script_path = base_path.with_suffix(".py")
    blend_path = base_path.with_suffix(".blend")
    fbx_path = base_path.with_suffix(".fbx")
    script_path.write_text(script_code, encoding="utf-8")

    try:
        result = subprocess.run(
            [
                str(blender), "--background", "--factory-startup",
                "--python-exit-code", "1",  # skript xəta versə, Blender xəta kodu ilə çıxsın
                "--python", str(RUNNER), "--",
                str(script_path), str(blend_path), str(fbx_path),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=BLENDER_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise BlenderError(f"Blender {BLENDER_TIMEOUT} saniyədən çox işlədi və dayandırıldı.")

    output = result.stdout + result.stderr
    if result.returncode != 0 or not blend_path.exists():
        # Xətanın son sətirləri (Python traceback) - Claude düzəliş üçün bunu görəcək
        tail = "\n".join(output.strip().splitlines()[-25:])
        raise BlenderError(f"Blender skripti xəta verdi:\n{tail}")

    for line in output.splitlines():
        if line.startswith("ORION_RESULT:"):
            return json.loads(line[len("ORION_RESULT:"):])
    return []


def upload_to_roblox(fbx_path, display_name):
    """FBX faylını Roblox Open Cloud Assets API ilə yükləyir və "rbxassetid://..."
    formatında asset ID qaytarır. ROBLOX_API_KEY / ROBLOX_CREATOR_ID mühit
    dəyişənləri təyin olunmayıbsa, ya da yükləmə hər hansı səbəbdən alınmasa,
    xəta atmadan None qaytarır - bu, əsas modelləşdirmə axınını pozmamalıdır."""
    api_key = os.environ.get("ROBLOX_API_KEY")
    creator_id = os.environ.get("ROBLOX_CREATOR_ID")
    if not api_key or not creator_id or not fbx_path.exists():
        return None

    try:
        import requests
    except ImportError:
        return None

    request_payload = {
        "assetType": "Model",
        "displayName": display_name,
        "description": "Orion tərəfindən avtomatik yaradılıb",
        "creationContext": {"creator": {"userId": creator_id}},
    }
    try:
        with open(fbx_path, "rb") as f:
            resp = requests.post(
                ROBLOX_ASSETS_URL,
                headers={"x-api-key": api_key},
                data={"request": json.dumps(request_payload)},
                files={"fileContent": (fbx_path.name, f, "model/fbx")},
                timeout=60,
            )
        resp.raise_for_status()
        operation_id = resp.json()["operationId"]

        # Yükləmə asinxrondur - operation tamamlanana qədər gözləyirik
        for _ in range(30):
            time.sleep(2)
            op_resp = requests.get(
                ROBLOX_OPERATIONS_URL.format(operation_id),
                headers={"x-api-key": api_key},
                timeout=30,
            )
            op_resp.raise_for_status()
            op_data = op_resp.json()
            if op_data.get("done"):
                asset_id = op_data["response"]["assetId"]
                return f"rbxassetid://{asset_id}"
        return None
    except Exception:
        return None


def generate_bpy_script(client, model, task, version, failed_script=None, error=None):
    """Claude-dan tapşırıq üçün bpy skripti istəyir: {"name", "script", "summary"}."""
    content = f"Tapşırıq: {task}"
    if failed_script:
        content += (
            f"\n\nƏvvəlki skript xəta verdi. Səhvi düzəlt.\n\nSkript:\n{failed_script}"
            f"\n\nXəta:\n{error}"
        )
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=BPY_PROMPT.format(version=version),
        messages=[{"role": "user", "content": content}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "script": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["name", "script", "summary"],
                    "additionalProperties": False,
                },
            },
        },
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise BlenderError("Claude bpy skriptini yaza bilmədi.")
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def create_model(client, model, task, log=print):
    """Tapşırığa görə Blender-də model yaradır, mümkünsə Roblox-a da avtomatik yükləyir.
    Qaytarır: (blend_faylı, fbx_faylı və ya None, roblox_asset_id və ya None,
    obyektlər, qısa_təsvir). Alınmasa BlenderError atır."""
    blender = find_blender()
    version = blender.parent.name  # məs. "Blender 5.2"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    failed_script = error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        log("[Blender] Claude bpy skripti yazır..." if attempt == 1
            else f"[Blender] Skript xəta verdi, Claude düzəldir (cəhd {attempt})...")
        result = generate_bpy_script(client, model, task, version, failed_script, error)

        name = re.sub(r"[^A-Za-z0-9_-]", "_", result["name"])[:40].strip("_") or "model"
        base_path = MODELS_DIR / f"{name}_{datetime.now():%Y%m%d_%H%M%S}"
        log(f"[Blender] {version} arxa planda işə salınır...")
        try:
            objects = run_blender_script(result["script"], base_path)
        except BlenderError as e:
            failed_script, error = result["script"], str(e)
            base_path.with_suffix(".py").unlink(missing_ok=True)
            continue

        blend_path = base_path.with_suffix(".blend")
        fbx_path = base_path.with_suffix(".fbx")
        fbx_path = fbx_path if fbx_path.exists() else None

        asset_id = None
        if fbx_path:
            log("[Blender] FBX ixrac edildi, Roblox-a avtomatik yükləmə cəhd olunur...")
            asset_id = upload_to_roblox(fbx_path, name)
            if asset_id:
                log(f"[Blender] Roblox-a yükləndi: {asset_id}")
            else:
                log("[Blender] Avtomatik yükləmə keçildi (API açarı yoxdur və ya alınmadı) "
                    "- FBX faylını əl ilə yükləyə bilərsiniz.")

        return blend_path, fbx_path, asset_id, objects, result["summary"]

    raise BlenderError(error)
